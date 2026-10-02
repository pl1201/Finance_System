"""Đối chiếu dữ liệu ``data/`` với nguồn NGOÀI (độc lập với HistData/Dukascopy).

* ``fxcm``: EURUSD H1 của broker FXCM (``candledata.fxcorporate.com``, công khai, giờ UTC, BID) —
  2018–2025. So lợi suất theo giờ ở các độ lệch −2..+2 giờ (đúng giờ → khớp nhất ở 0), chênh giá,
  nến D1 theo hai mốc (17:00 NY và 00:00 UTC), và việc broker có báo giá các ngày 24–25/12, 01/01.
* ``yahoo``: nến 60 phút của Yahoo Finance cho vàng COMEX ``GC=F`` (hợp đồng tương lai CME — khác
  giá giao ngay một khoản chênh kỳ hạn, nên chỉ so lợi suất/giờ) và ``EURUSD=X``. Yahoo chỉ cho nến
  60 phút trong ~730 ngày gần nhất. Lợi suất từng nến Yahoo được so với giá M1 của ta lấy đúng mốc
  đầu/cuối nến đó. Kèm: giờ nến cuối của GC=F trong các ngày lễ (kiểm lịch phiên CME).

Kết quả: ``data/compare_external.json``; tóm tắt trong docs/du_lieu_thi_truong.md §8.

    python -m marketdata.compare all
"""
from __future__ import annotations

import csv
import gzip
import http.client
import json
import math
import os
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import DATA_DIR  # noqa: E402
from .session_calendar import SessionCalendar  # noqa: E402

MARKET = DATA_DIR
RAW = os.path.join(MARKET, "raw")
OUT = os.path.join(MARKET, "compare_external.json")
NY = ZoneInfo("America/New_York")
EU = ZoneInfo("Europe/Paris")
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def mismatch(t: datetime) -> bool:
    """Tuần Mỹ–Âu lệch lịch đổi giờ — nơi quy đổi giờ sai lộ ra."""
    return bool(t.astimezone(NY).dst()) != bool(t.astimezone(EU).dst())


def corr(xs, ys):
    n = len(xs)
    if n < 30:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if not sx or not sy:
        return None
    return round(sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy), 4)


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None


def load_ours(pair: str, tf: str):
    """{epoch giờ mở: (o,h,l,c)} từ file đã dựng; M1 ghép các năm."""
    paths = ([os.path.join(MARKET, pair, "M1", "%s_M1_%d.csv" % (pair, y)) for y in range(2018, 2026)]
             if tf == "M1" else [os.path.join(MARKET, pair, "%s_%s_2018_2025.csv" % (pair, tf))])
    out = {}
    for p in paths:
        with open(p, encoding="ascii") as f:
            next(f)
            for line in f:
                t, o, h, lo, c = line.split(",")[:5]
                e = int(datetime.strptime(t, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp())
                out[e] = (float(o), float(h), float(lo), float(c))
    return out


# ---------------------------------------------------------------- FXCM
def fetch_fxcm(sym="EURUSD", tf="H1"):
    d = os.path.join(RAW, "fxcm")
    os.makedirs(d, exist_ok=True)
    conn = http.client.HTTPSConnection("candledata.fxcorporate.com", timeout=60)
    rows = {}
    for y in range(2018, 2026):
        for w in range(1, 54):
            path = os.path.join(d, "%s_%s_%d_%02d.csv.gz" % (sym, tf, y, w))
            if not os.path.exists(path):
                for attempt in range(4):
                    try:
                        conn.request("GET", "/%s/%s/%d/%d.csv.gz" % (tf, sym, y, w), headers=HDR)
                        r = conn.getresponse()
                        data = r.read()
                        break
                    except (http.client.HTTPException, OSError):
                        conn.close()
                        conn = http.client.HTTPSConnection("candledata.fxcorporate.com", timeout=60)
                        time.sleep(2 * (attempt + 1))
                else:
                    raise RuntimeError("không tải được FXCM %d tuần %d" % (y, w))
                with open(path, "wb") as f:
                    f.write(data if r.status == 200 else b"")
            raw = open(path, "rb").read()
            if not raw:
                continue
            text = gzip.decompress(raw).decode("utf-8", "replace").lstrip("﻿")
            for row in csv.DictReader(text.splitlines()):
                t = datetime.strptime(row["DateTime"][:19], "%m/%d/%Y %H:%M:%S").replace(tzinfo=timezone.utc)
                rows[int(t.timestamp())] = (float(row["BidOpen"]), float(row["BidHigh"]),
                                            float(row["BidLow"]), float(row["BidClose"]))
    return rows


def daily(h1, alignment):
    """Gộp H1 → D1 theo mốc 17:00 NY (``ny_1700``) hoặc 00:00 UTC."""
    out = {}
    for e in sorted(h1):
        t = datetime.fromtimestamp(e, timezone.utc)
        key = ((t.astimezone(NY) + timedelta(hours=7)).date() if alignment == "ny_1700" else t.date())
        o, h, lo, c = h1[e]
        if key not in out:
            out[key] = [o, h, lo, c]
        else:
            b = out[key]
            b[1], b[2], b[3] = max(b[1], h), min(b[2], lo), c
    return out


def compare_fxcm():
    ref = fetch_fxcm()
    ours = load_ours("EURUSD", "H1")
    res = {"nguon": "FXCM candledata H1 EURUSD BID (giờ UTC)", "so_nen_fxcm": len(ref), "so_nen_ta": len(ours)}

    def rets(s):
        return {e: math.log(s[e][3] / s[e - 3600][3]) for e in s if e - 3600 in s}

    ro, rr = rets(ours), rets(ref)
    by = defaultdict(dict)
    for lag in (-2, -1, 0, 1, 2):
        groups = defaultdict(lambda: ([], []))
        for e, x in ro.items():
            y = rr.get(e + lag * 3600)
            if y is None:
                continue
            t = datetime.fromtimestamp(e, timezone.utc)
            for g in ("tat_ca", "tuan_lech_lich" if mismatch(t) else "tuan_binh_thuong", str(t.year)):
                groups[g][0].append(x)
                groups[g][1].append(y)
        for g, (xs, ys) in groups.items():
            by[g]["lech_%+dh" % lag] = corr(xs, ys)
            if lag == 0:
                by[g]["n"] = len(xs)
    res["tuong_quan_loi_suat_H1"] = dict(by)
    diffs = [abs(ours[e][3] - ref[e][3]) * 1e4 for e in ours if e in ref]
    res["chenh_close_H1_pip"] = {"trung_vi": round(q(diffs, .5), 2), "p90": round(q(diffs, .9), 2),
                                 "p99": round(q(diffs, .99), 2), "n": len(diffs)}
    od = load_ours("EURUSD", "D1")
    od = {(datetime.fromtimestamp(e, timezone.utc).astimezone(NY) + timedelta(hours=7)).date(): v
          for e, v in od.items()}
    for al in ("ny_1700", "utc"):
        rd = daily(ref, al)
        dd = [abs(od[k][3] - rd[k][3]) * 1e4 for k in od if k in rd]
        res["D1_close_chenh_pip_" + al] = {"trung_vi": round(q(dd, .5), 2), "p90": round(q(dd, .9), 2), "n": len(dd)}
    hol = defaultdict(int)
    for e in ref:
        loc = datetime.fromtimestamp(e, timezone.utc).astimezone(NY)
        td = (loc + timedelta(hours=7)).date()
        if (td.month, td.day) in ((12, 25), (1, 1)) and td.weekday() < 5:
            hol["%s (ngày giao dịch %s)" % (loc.strftime("%Y-%m-%d"), td.isoformat())] += 1
    res["fxcm_co_bao_gia_ngay_25_12_01_01 (số nến H1)"] = dict(sorted(hol.items()))
    return res


# ---------------------------------------------------------------- Yahoo
def yahoo(sym, interval, p1, p2, prepost=True):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/%s?interval=%s&period1=%d&period2=%d%s"
           % (sym, interval, p1, p2, "&includePrePost=true" if prepost else ""))
    d = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=HDR), timeout=60))
    r = d["chart"]["result"][0]
    qd = r["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(r.get("timestamp") or []):
        o, c, v = qd["open"][i], qd["close"][i], qd["volume"][i]
        if o is None or c is None:
            continue
        out.append((t, o, c, v or 0))
    return out


def compare_yahoo():
    now = int(datetime.now(timezone.utc).timestamp())
    p1 = now - 728 * 86400
    p2 = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
    res = {"khoang": [datetime.fromtimestamp(p1, timezone.utc).date().isoformat(), "2025-12-31"]}
    cache = os.path.join(RAW, "yahoo")
    os.makedirs(cache, exist_ok=True)
    for sym, pair in (("GC=F", "XAUUSD"), ("EURUSD=X", "EURUSD")):
        path = os.path.join(cache, "%s_60m.json" % sym.replace("=", "_"))
        if os.path.exists(path):
            bars = json.load(open(path))
        else:
            bars = yahoo(sym, "60m", p1, p2)
            json.dump(bars, open(path, "w"))
        m1 = load_ours(pair, "M1")

        def price_at(e):
            """Close M1 của phút ngay trước mốc e (giá tại thời điểm e)."""
            for k in range(1, 4):
                v = m1.get(e - 60 * k)
                if v:
                    return v[3]
            return None

        by = defaultdict(dict)
        for lag in (-2, -1, 0, 1, 2):
            groups = defaultdict(lambda: ([], []))
            for i, (t, o, c, v) in enumerate(bars):
                if i + 1 >= len(bars):
                    break
                end = bars[i + 1][0] if bars[i + 1][0] - t <= 3600 else t + 3600
                a, b = price_at(t + lag * 3600), price_at(end + lag * 3600)
                if not a or not b or not o or o <= 0 or c <= 0:
                    continue
                tt = datetime.fromtimestamp(t, timezone.utc)
                for g in ("tat_ca", "tuan_lech_lich" if mismatch(tt) else "tuan_binh_thuong"):
                    groups[g][0].append(math.log(b / a))
                    groups[g][1].append(math.log(c / o))
            for g, (xs, ys) in groups.items():
                by[g]["lech_%+dh" % lag] = corr(xs, ys)
                if lag == 0:
                    by[g]["n"] = len(xs)
        res[sym] = {"so_nen_yahoo": len(bars), "tuong_quan_loi_suat": dict(by)}

    # giờ nến cuối của GC=F trong các ngày lễ / đóng sớm theo lịch CME
    cal = SessionCalendar.for_symbol("XAUUSD")
    gc = json.load(open(os.path.join(cache, "GC_F_60m.json")))
    xau = load_ours("XAUUSD", "M1")
    hol = []
    for i, s in enumerate(cal.sessions):
        if s.kind != "early_close" or s.open.timestamp() < p1 or i + 1 >= len(cal.sessions):
            continue
        lo, hi = s.open.timestamp(), cal.sessions[i + 1].open.timestamp()  # tới lúc phiên sau mở
        ybars = [b for b in gc if lo <= b[0] < hi and b[3] > 0]
        ours = [e for e in xau if lo <= e < hi]
        hol.append({"ngay": s.trading_day.isoformat(),
                    "lich_dong_NY": s.close.astimezone(NY).strftime("%H:%M"),
                    "gc_nen_cuoi_mo_luc_NY": (datetime.fromtimestamp(max(b[0] for b in ybars), timezone.utc)
                                              .astimezone(NY).strftime("%H:%M")) if ybars else None,
                    "du_lieu_ta_phut_cuoi_NY": (datetime.fromtimestamp(max(ours), timezone.utc)
                                                .astimezone(NY).strftime("%H:%M")) if ours else None})
    res["gio_dong_ngay_le_GC=F"] = hol
    return res


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    if what in ("fxcm", "all"):
        res["fxcm_eurusd"] = compare_fxcm()
        print(json.dumps(res["fxcm_eurusd"], ensure_ascii=False, indent=1))
    if what in ("yahoo", "all"):
        res["yahoo"] = compare_yahoo()
        print(json.dumps(res["yahoo"], ensure_ascii=False, indent=1))
    res["tao_luc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
