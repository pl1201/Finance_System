"""Tải M1 HistData.com (XAUUSD, EURUSD) và dựng M1/M5/M15/H1/H4/D1 theo UTC.

Các bước, chạy lại được:

    python -m marketdata.histdata download
    python -m marketdata.histdata build --fill-dukascopy
    python -m marketdata.histdata verify

* ``download``: mỗi (cặp, năm) lấy token từ trang tải của HistData rồi POST ``/get.php``; lưu
  nguyên file zip vào ``data/raw/histdata/`` (bỏ qua nếu đã có và mở được).
* ``build``: đọc zip, quy đổi giờ gốc → UTC theo ``--tz-rule``, kiểm tra OHLC, bỏ trùng, rồi gộp:
  M5/M15/H1 theo bội số UTC; H4/D1 theo ``--h4d1-alignment`` (mặc định ``ny_1700``: ngày giao dịch
  bắt đầu 17:00 New York). Ghi CSV ``time,open,high,low,close,volume,m1_count`` (time = giờ MỞ nến,
  UTC), ``manifest.json`` (sha256, số dòng, quy ước) và ``quality.json``.

Múi giờ gốc của HistData: trang web ghi «EST không đổi giờ mùa hè», nhưng giờ nghỉ phiên và giờ
đóng/mở tuần trong dữ liệu cho thấy (``--tz-rule histdata``, mặc định):

* tới hết 2018: giờ gốc = giờ New York (có đổi giờ mùa hè);
* từ 2019: giờ gốc = giờ server châu Âu − 7 giờ (UTC−5 mùa đông, UTC−4 khi châu Âu theo giờ mùa hè).

Hai cách chỉ khác nhau trong các tuần Mỹ–Âu lệch lịch đổi giờ (~3 tuần/năm). Kiểm chứng bằng
Dukascopy: ``python -m marketdata.dukascopy`` rồi ``python -m marketdata.histdata verify`` — xem
``docs/du_lieu_thi_truong.md``. Volume của HistData luôn bằng 0.
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from . import DATA_DIR  # noqa: E402

OUT = DATA_DIR
RAW = os.path.join(OUT, "raw", "histdata")
PAGE = "https://www.histdata.com/download-free-forex-historical-data/?/ascii/1-minute-bar-quotes/{pair}/{year}"
GET = "https://www.histdata.com/get.php"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
NY = ZoneInfo("America/New_York")
EU_SERVER = ZoneInfo("Europe/Athens")  # UTC+2 / UTC+3 theo lịch đổi giờ châu Âu
TF_MIN = {"M5": 5, "M15": 15, "H1": 60}


# ---------------------------------------------------------------- download
def zip_ok(path: str) -> bool:
    try:
        with zipfile.ZipFile(path) as z:
            return any(n.lower().endswith(".csv") for n in z.namelist())
    except (zipfile.BadZipFile, OSError):
        return False


def download(pairs, years) -> None:
    os.makedirs(RAW, exist_ok=True)
    for pair in pairs:
        for year in years:
            name = "HISTDATA_COM_ASCII_%s_M1_%d.zip" % (pair, year)
            path = os.path.join(RAW, name)
            if os.path.exists(path) and zip_ok(path):
                print("đã có", name)
                continue
            page = PAGE.format(pair=pair.lower(), year=year)
            for attempt in range(5):
                try:
                    html = urllib.request.urlopen(
                        urllib.request.Request(page, headers=HDR), timeout=60).read().decode("utf-8", "replace")
                    form = re.search(r'<form id="file_down".*?</form>', html, re.S)
                    if not form:
                        raise RuntimeError("không thấy form tải (năm chưa có file cả năm?)")
                    fields = dict(re.findall(r'name="(\w+)" id="\w+" value="([^"]*)"', form.group(0)))
                    req = urllib.request.Request(
                        GET, data=urllib.parse.urlencode(fields).encode(),
                        headers=dict(HDR, Referer=page))
                    data = urllib.request.urlopen(req, timeout=300).read()
                    with open(path, "wb") as f:
                        f.write(data)
                    if not zip_ok(path):
                        os.remove(path)
                        raise RuntimeError("file tải về không phải zip hợp lệ (%d byte)" % len(data))
                    print("tải xong %s (%.1f MB)" % (name, len(data) / 1e6), flush=True)
                    break
                except Exception as e:  # noqa: BLE001
                    print("  lỗi %s lần %d: %s" % (name, attempt + 1, str(e)[:100]), flush=True)
                    time.sleep(5 * (attempt + 1))
            else:
                print("BỎ QUA %s sau 5 lần thử" % name)
            time.sleep(2)


# ---------------------------------------------------------------- quy đổi giờ
#: Từ ngày này giờ gốc HistData bám lịch đổi giờ châu Âu; trước đó bám New York. Hai quy tắc chỉ
#: khác nhau trong các tuần Mỹ–Âu lệch lịch; mốc thật nằm giữa 04/11/2018 và 10/03/2019
#: (docs/du_lieu_thi_truong.md §3).
HISTDATA_EU_FROM = date(2019, 1, 1)


def offset_for(rule: str, raw_day: date) -> int:
    """Số giây cộng vào giờ gốc để ra UTC, cho một ngày giờ gốc (đổi giờ chỉ xảy ra khi đóng cửa)."""
    noon = datetime(raw_day.year, raw_day.month, raw_day.day, 12)
    if rule == "histdata":
        rule = "eu_server" if raw_day >= HISTDATA_EU_FROM else "ny"
    if rule == "est":
        return 5 * 3600
    if rule == "ny":
        return -int(noon.replace(tzinfo=NY).utcoffset().total_seconds())
    if rule == "eu_server":
        server = noon + timedelta(hours=7)
        return 7 * 3600 - int(server.replace(tzinfo=EU_SERVER).utcoffset().total_seconds())
    raise ValueError(rule)


def read_pair(pair: str, years, rule: str):
    """Trả list (epoch_utc, o, h, l, c) đã sắp xếp, bỏ trùng; kèm thống kê lỗi."""
    rows, stats = {}, Counter()
    off_cache: dict = {}
    for year in years:
        path = os.path.join(RAW, "HISTDATA_COM_ASCII_%s_M1_%d.zip" % (pair, year))
        if not zip_ok(path):
            stats["thieu_file_%d" % year] += 1
            continue
        with zipfile.ZipFile(path) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".csv"))
            text = z.read(name).decode("ascii")
        for line in text.splitlines():
            if not line.strip():
                continue
            parts = line.split(";")
            ts = parts[0]
            o, h, lo, c = (float(x) for x in parts[1:5])
            dkey = ts[:8]
            if dkey not in off_cache:
                d = date(int(ts[:4]), int(ts[4:6]), int(ts[6:8]))
                off_cache[dkey] = (calendar.timegm(d.timetuple()), offset_for(rule, d))
            base, off = off_cache[dkey]
            epoch = base + int(ts[9:11]) * 3600 + int(ts[11:13]) * 60 + int(ts[13:15]) + off
            stats["dong_goc"] += 1
            if not (h >= max(o, c) and lo <= min(o, c) and lo > 0):
                stats["ohlc_sai_bo"] += 1
                continue
            if epoch in rows:
                stats["trung_thoi_diem"] += 1
                if rows[epoch] != (o, h, lo, c):
                    stats["trung_thoi_diem_khac_gia"] += 1
                continue
            rows[epoch] = (o, h, lo, c)
    return sorted((k,) + v for k, v in rows.items()), stats


# ---------------------------------------------------------------- lấp giờ mất từ Dukascopy
def calendar_for(pair: str):
    from .session_calendar import SessionCalendar
    return SessionCalendar.for_symbol(pair)


def fillable_windows(m1, pair: str):
    """Khoảng trống có ≥ 50 phút thiếu nằm TRONG phiên theo lịch khai báo (calendars/), dài tối
    đa 24 giờ: [đầu, cuối) theo epoch. Chỉ những phút trong phiên mới được lấp."""
    cal = calendar_for(pair)
    step = timedelta(minutes=1)
    out = []
    for i in range(1, len(m1)):
        g = m1[i][0] - m1[i - 1][0] - 60
        if 50 * 60 <= g <= 24 * 3600:
            s = m1[i - 1][0] + 60
            kind, miss = cal.classify_gap(datetime.fromtimestamp(s, timezone.utc),
                                          datetime.fromtimestamp(m1[i][0], timezone.utc), step)
            if miss >= 50:
                out.append((s, m1[i][0]))
    return out


def fill_from_dukascopy(pair: str, m1, nd: int):
    """Lấp phút thiếu trong các khoảng trống ``fillable_windows`` bằng M1 BID Dukascopy đã lưu đệm.

    Chỉ dùng một ngày Dukascopy khi ≥ 95% (và ≥ 50) phút trùng nhau có close bằng nhau đến từng
    điểm giá — tức cùng luồng giá (docs/du_lieu_thi_truong.md §4). Nến «phẳng» volume 0 của Dukascopy
    (thị trường đóng, vd ngày lễ) không được dùng. Không nội suy, không lấp ngoài các khoảng đó."""
    from . import dukascopy as cd
    tol = 0.5 * 10 ** -nd
    hd_close = {r[0]: r[4] for r in m1}
    day_cache: dict = {}

    def day_data(d: date):
        if d not in day_cache:
            path = os.path.join(cd.CACHE, pair, "%s_BID_m1.bi5" % d.isoformat())
            if not os.path.exists(path):
                day_cache[d] = None
            else:
                data = cd.decode_ohlc(pair, d, open(path, "rb").read())
                both = [abs(hd_close[t] - v[3]) <= tol for t, v in data.items() if t in hd_close]
                rate = sum(both) / len(both) if both else 0.0
                day_cache[d] = (data, rate, len(both))
        return day_cache[d]

    cal = calendar_for(pair)
    added, report = [], []
    for s, e in fillable_windows(m1, pair):
        filled, status = 0, "nguon_cung_khong_co_nen"
        for t in range(s, e, 60):
            if not cal.is_open(datetime.fromtimestamp(t, timezone.utc)):
                continue  # ngoài phiên theo lịch: không lấp
            dd = day_data(datetime.fromtimestamp(t, timezone.utc).date())
            if dd is None:
                status = "chua_tai_dukascopy"
                continue
            data, rate, n = dd
            if rate < 0.95 or n < 50:
                status = "khac_luong_gia (khớp %.0f%% / %d phút)" % (100 * rate, n)
                continue
            if t in data:
                o, h, lo, c = data[t]
                added.append((t, o, h, lo, c))
                filled += 1
        report.append({"tu_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(s)),
                       "den_utc": time.strftime("%Y-%m-%d %H:%M", time.gmtime(e)),
                       "phut_da_lap": filled, "trang_thai": status if filled == 0 else "da_lap"})
    summary = Counter(r["trang_thai"].split(" ")[0] for r in report)
    per_month = Counter(time.strftime("%Y-%m", time.gmtime(t[0])) for t in added)
    return sorted(m1 + added), {"khoang_trong_thieu_trong_phien_>=50p": len(report), "ket_qua": dict(summary),
                                "phut_da_lap": len(added), "phut_da_lap_theo_thang": dict(sorted(per_month.items())),
                                "ngay_dukascopy_khong_dung": sorted(
                                    "%s (khớp %.0f%%, %d phút)" % (d, 100 * v[1], v[2])
                                    for d, v in day_cache.items() if v and (v[1] < 0.95 or v[2] < 50))}, report


# ---------------------------------------------------------------- gộp khung
_KEY_CACHE: dict = {}


def bucket(epoch: int, tf: str, alignment: str):
    """(khoá bucket, epoch mở bucket)."""
    if tf in TF_MIN:
        size = TF_MIN[tf] * 60
        return epoch // size, epoch // size * size
    if alignment == "utc_epoch":
        size = 14400 if tf == "H4" else 86400
        return epoch // size, epoch // size * size
    hour = epoch // 3600
    ck = (tf, hour)
    if ck not in _KEY_CACHE:
        loc = datetime.fromtimestamp(hour * 3600, timezone.utc).astimezone(NY)
        sh = loc + timedelta(hours=7)               # ngày giao dịch kết thúc 17:00 NY
        d = sh.date()
        midnight = datetime(d.year, d.month, d.day, tzinfo=NY)
        if tf == "H4":
            k = sh.hour // 4
            start = midnight - timedelta(hours=7) + timedelta(hours=4 * k)
            key = (d.toordinal(), k)
        else:
            start = midnight - timedelta(hours=7)
            key = (d.toordinal(),)
        _KEY_CACHE[ck] = (key, int(start.astimezone(timezone.utc).timestamp()))
    return _KEY_CACHE[ck]


def aggregate(m1, tf: str, alignment: str):
    out, cur, ck = [], None, None
    for e, o, h, lo, c in m1:
        key, start = bucket(e, tf, alignment)
        if key != ck:
            if cur:
                out.append(cur)
            ck, cur = key, [start, o, h, lo, c, 1]
        else:
            if h > cur[2]:
                cur[2] = h
            if lo < cur[3]:
                cur[3] = lo
            cur[4] = c
            cur[5] += 1
    if cur:
        out.append(cur)
    return out


# ---------------------------------------------------------------- ghi file + kiểm tra
def fmt(x: float, nd: int) -> str:
    s = "%.*f" % (nd, x)
    return s.rstrip("0").rstrip(".") if "." in s else s


def write_csv(path, bars, nd, with_count=True, trading_day=False) -> dict:
    """``trading_day`` (chỉ D1 mốc ny_1700): ngày giao dịch kết thúc 17:00 NY của nến."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    h = hashlib.sha256()
    with open(path, "w", encoding="ascii", newline="\n") as f:
        head = ("time,open,high,low,close,volume" + (",m1_count" if with_count else "")
                + (",trading_day" if trading_day else "") + "\n")
        f.write(head)
        h.update(head.encode())
        for b in bars:
            td = ""
            if trading_day:
                loc = datetime.fromtimestamp(b[0], timezone.utc).astimezone(NY) + timedelta(hours=7)
                td = "," + loc.date().isoformat()
            line = "%s,%s,%s,%s,%s,0%s%s\n" % (
                time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(b[0])),
                fmt(b[1], nd), fmt(b[2], nd), fmt(b[3], nd), fmt(b[4], nd),
                (",%d" % b[5]) if with_count else "", td)
            f.write(line)
            h.update(line.encode())
    first = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(bars[0][0])) if bars else None
    last = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(bars[-1][0])) if bars else None
    return {"file": os.path.relpath(path, OUT).replace("\\", "/"), "rows": len(bars),
            "first_open_utc": first, "last_open_utc": last, "sha256": h.hexdigest()}


def quality(m1, pair: str) -> dict:
    """Đối chiếu dữ liệu với lịch phiên KHAI BÁO (calendars/):

    * khoảng trống giữa hai nến M1 → đóng cửa theo lịch (nghỉ hằng ngày / cuối tuần / lễ) hay thiếu
      dữ liệu trong phiên (kèm số phút thiếu);
    * nến nằm NGOÀI phiên theo lịch (lịch sai, hoặc nguồn báo giá lúc sàn đóng)."""
    cal = calendar_for(pair)
    step = timedelta(minutes=1)
    gaps, miss_len, outside, outside_day = Counter(), Counter(), Counter(), Counter()
    odd = []
    for i, (e, *_r) in enumerate(m1):
        t = datetime.fromtimestamp(e, timezone.utc)
        if cal.covers(t):
            r = cal.closure_reason(t)
            if r:
                outside[r] += 1
                outside_day["%s %s" % (t.astimezone(NY).strftime("%Y-%m-%d %a"), r)] += 1
        if i and e - m1[i - 1][0] > 60:
            t0 = datetime.fromtimestamp(m1[i - 1][0] + 60, timezone.utc)
            kind, miss = cal.classify_gap(t0, t, step)
            gaps[kind] += 1
            if miss:
                miss_len["<5" if miss < 5 else "5-29" if miss < 30 else "30-59" if miss < 60 else ">=60"] += miss
                if miss >= 30 and len(odd) < 400:
                    odd.append("%s +%dm (trong phiên %d)" % (
                        t0.astimezone(NY).strftime("%Y-%m-%d %a %H:%M NY"), (e - m1[i - 1][0]) // 60 - 1, miss))
    return {"lich": cal.name,
            "khoang_trong_theo_lich": dict(gaps),
            "phut_thieu_trong_phien_theo_do_dai_khoang": dict(miss_len),
            "thieu_trong_phien_tu_30_phut": odd,
            "nen_ngoai_phien_theo_lich": dict(outside),
            "ngay_co_nen_ngoai_phien": dict(outside_day.most_common(80))}


def build(pairs, years, rule, alignment, fill=False) -> None:
    manifest = {"source": "HistData.com ASCII M1 (bid)" + (
                    "; giờ mất lấp bằng Dukascopy M1 BID cùng luồng giá (xem fill)" if fill else ""),
                "tz_rule": rule,
                "tz_rule_detail": ("giờ gốc = New York trước %s; = giờ server châu Âu − 7h từ %s"
                                   % (HISTDATA_EU_FROM, HISTDATA_EU_FROM)) if rule == "histdata" else rule,
                "h4_d1_alignment": alignment,
                "time_convention": "giờ MỞ nến, UTC", "volume": "HistData không có volume (luôn 0)",
                "script_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
                "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "raw": {}, "files": {}}
    qual = {}
    for pair in pairs:
        nd = 3 if pair.startswith("XAU") else 5
        for year in years:
            p = os.path.join(RAW, "HISTDATA_COM_ASCII_%s_M1_%d.zip" % (pair, year))
            if os.path.exists(p):
                manifest["raw"][os.path.basename(p)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
        t0 = time.time()
        m1, stats = read_pair(pair, years, rule)
        lo_y, hi_y = years[0], years[-1]
        m1 = [r for r in m1 if lo_y <= time.gmtime(r[0]).tm_year <= hi_y]
        fill_info = None
        if fill:
            m1, fill_info, fill_rows = fill_from_dukascopy(pair, m1, nd)
            os.makedirs(os.path.join(OUT, pair), exist_ok=True)
            with open(os.path.join(OUT, pair, "%s_lap_tu_dukascopy.csv" % pair), "w", encoding="utf-8",
                      newline="\n") as f:
                f.write("tu_utc,den_utc,phut_da_lap,trang_thai\n")
                for r in fill_rows:
                    f.write("%s,%s,%d,%s\n" % (r["tu_utc"], r["den_utc"], r["phut_da_lap"], r["trang_thai"]))
        files = []
        for y in years:
            part = [r + (1,) for r in m1 if time.gmtime(r[0]).tm_year == y]
            files.append(write_csv(os.path.join(OUT, pair, "M1", "%s_M1_%d.csv" % (pair, y)), part, nd, False))
        for tf in ("M5", "M15", "H1", "H4", "D1"):
            bars = aggregate(m1, tf, alignment)
            files.append(write_csv(os.path.join(OUT, pair, "%s_%s_%d_%d.csv" % (pair, tf, lo_y, hi_y)), bars, nd,
                                   trading_day=(tf == "D1" and alignment == "ny_1700")))
        manifest["files"][pair] = files
        qual[pair] = {"thong_ke_doc": dict(stats), "lap_tu_dukascopy": fill_info, **quality(m1, pair)}
        print("%s: %d nến M1 sau quy đổi (%.0fs)" % (pair, len(m1), time.time() - t0), flush=True)
    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    with open(os.path.join(OUT, "quality.json"), "w", encoding="utf-8") as f:
        json.dump(qual, f, ensure_ascii=False, indent=1)
    print("Đã ghi manifest.json và quality.json vào", OUT)


def verify(pairs, years) -> None:
    """So close M1 HistData (từng quy tắc giờ) với Dukascopy (UTC) trên các ngày mẫu của
    ``marketdata.dukascopy``. Quy tắc đúng → lệch tốt nhất = 0 phút, chênh giá nhỏ."""
    path = os.path.join(OUT, "raw", "dukascopy", "dukascopy_m1_mau.json")
    duk = json.load(open(path, encoding="utf-8"))
    report = {}
    for pair in pairs:
        if pair not in duk:
            continue
        series = {r: {e: c for e, _o, _h, _l, c in read_pair(pair, years, r)[0]}
                  for r in ("histdata", "eu_server", "ny", "est")}
        for d, closes in sorted(duk[pair].items()):
            day0 = calendar.timegm(date.fromisoformat(d).timetuple())
            ref = {day0 + int(k[:2]) * 3600 + int(k[3:]) * 60: v for k, v in closes.items()}
            row = {}
            for r, s in series.items():
                best = None
                for shift in (-120, -60, -1, 0, 1, 60, 120):
                    diffs = sorted(abs(s[t + shift * 60] - v) for t, v in ref.items() if t + shift * 60 in s)
                    if len(diffs) < 100:
                        continue
                    med = diffs[len(diffs) // 2]
                    if best is None or med < best[1]:
                        best = (shift, med, len(diffs))
                row[r] = {"lech_tot_nhat_phut": best[0], "chenh_trung_vi": round(best[1], 6), "so_phut": best[2]} \
                    if best else None
            report.setdefault(pair, {})[d] = row
            print(pair, d, {r: (v["lech_tot_nhat_phut"] if v else None) for r, v in row.items()}, flush=True)
    with open(os.path.join(OUT, "verify_dukascopy.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("download", "build", "verify"))
    ap.add_argument("--pairs", default="XAUUSD,EURUSD")
    ap.add_argument("--years", default="2018-2025")
    ap.add_argument("--tz-rule", default="histdata", choices=("histdata", "eu_server", "ny", "est"))
    ap.add_argument("--h4d1-alignment", default="ny_1700", choices=("ny_1700", "utc_epoch"))
    ap.add_argument("--fill-dukascopy", action="store_true",
                    help="lấp giờ mất bằng Dukascopy đã tải (python -m marketdata.dukascopy --gap-days)")
    a = ap.parse_args()
    y0, y1 = (int(x) for x in a.years.split("-"))
    years = list(range(y0, y1 + 1))
    pairs = [p.strip().upper() for p in a.pairs.split(",") if p.strip()]
    if a.cmd == "download":
        download(pairs, years)
    elif a.cmd == "verify":
        verify(pairs, years)
    else:
        build(pairs, years, a.tz_rule, a.h4d1_alignment, a.fill_dukascopy)


if __name__ == "__main__":
    sys.exit(main())
