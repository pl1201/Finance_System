"""Khảo sát tái lập: order flow đọc theo thanh khoản (ICT, thuần giá) có mang thông tin không?

Tài liệu: ``docs/research/nghien_cuu_orderflow_ict.md``. Đây là khảo sát, không phải thuật toán sẽ cài:

* đọc ``data/lab.sqlite`` CHỈ ĐỌC; mọi đoạn dữ liệu kết thúc trước 2024-09-01 (đoạn kiểm tra khoá —
  script từ chối khoảng chạm vào đó);
* sự kiện lấy từ ``ict_structure`` (v0.2.0, tham số mặc định) chạy nhân quả trên từng dataset;
* **trạng thái order flow** cập nhật theo sự kiện ĐÃ XÁC NHẬN tại nến t (không nhìn tương lai);
* **kết cục** (chỉ dùng để chấm, nhìn về sau): tại nến t trạng thái vừa lật sang s, lấy vùng còn nguyên
  gần nhất phía trên (BSL) và phía dưới (SSL) sau nến t; vùng nào bị LẤY trước (định nghĩa lấy của
  lab: xuyên ≥ 0.1·ATR). «Trúng» = vùng phía s bị lấy trước;
* **mốc ngẫu nhiên**: giá không trôi chạm vùng trên trước với xác suất d_dưới / (d_trên + d_dưới).
  Mốc được kiểm hiệu chuẩn trên mẫu mọi nến (``calibration``). Lợi thế = tỷ lệ trúng − mốc; CI 95%
  bootstrap theo khối tuần (2000 lần, seed 7).

Ví dụ (PowerShell, từ thư mục market-structure-lab)::

    .\\.venv\\Scripts\\python.exe research\\orderflow_survey.py --json docs\\research\\khao_sat\\orderflow_survey_dev.json
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import platform
import random
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from core.algorithms.ict_structure import IctStructureAlgorithm  # noqa: E402
from core.engine import run_algorithm  # noqa: E402
from core.types import build_bars  # noqa: E402

SURVEY_VERSION = "orderflow-v1"
TEST_START = "2024-09-01"
PERIODS = {"2018–2023": ("2018-01-01", "2024-01-01"), "01–08/2024": ("2024-01-01", TEST_START)}
DATASETS = {   # chỉ bản «giờ đã sửa»
    "XAUUSD": {"M5": "ds_933fa5ec67e2", "M15": "ds_a5212fd37814", "H1": "ds_83abaa3c6eab", "H4": "ds_2c79dddcd829",
               "D1": "ds_ba2c0dbea8c0"},
    "EURUSD": {"M15": "ds_a9a2a5e4cef5", "H1": "ds_ab9f7729cb17", "H4": "ds_8e87b4f82dfe", "D1": "ds_370f222212a9"},
}
DEFS = {   # loại sự kiện → chiều order flow (sweep đứng riêng để so)
    "run+shift": {"LIQ_RUN_UP": 1, "SHIFT_UP": 1, "LIQ_RUN_DOWN": -1, "SHIFT_DOWN": -1},
    "chỉ run": {"LIQ_RUN_UP": 1, "LIQ_RUN_DOWN": -1},
    "chỉ shift": {"SHIFT_UP": 1, "SHIFT_DOWN": -1},
    "theo sweep (quét SSL = tăng)": {"LIQ_SWEEP_SSL": 1, "LIQ_SWEEP_BSL": -1},
}


# ---------------------------------------------------------------- dữ liệu


def load(con, ds, start, end, allow_test):
    if end > TEST_START and not allow_test:
        raise SystemExit("Khoảng %s..%s chạm đoạn kiểm tra (từ %s) — cần --allow-test." % (start, end, TEST_START))
    tf, conv, sym, name, ck = con.execute(
        "select timeframe, timestamp_convention, symbol, name, checksum_sha256 from datasets where id=?", (ds,)).fetchone()
    rows = [{"bar_time": datetime.fromisoformat(r[0]), "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]}
            for r in con.execute("select bar_time, open, high, low, close, volume from bars where dataset_id=? and "
                                 "bar_time>=? and bar_time<? order by idx", (ds, start, end))]
    bars = build_bars(rows, tf, conv)
    cal = "cme_globex_metals" if sym == "XAUUSD" else "fx_spot"
    algo = IctStructureAlgorithm(timeframe=tf, session_calendar=cal)
    res = run_algorithm(bars, algo)
    meta = {"dataset": ds, "ten": name, "checksum": ck, "khung": tf, "tu": start, "den": end, "so_nen": len(bars),
            "thuat_toan": "%s %s" % (algo.name, algo.version), "lich_phien": cal}
    return bars, res, meta


# ---------------------------------------------------------------- trạng thái order flow (nhân quả)


def event_states(res, n, mapping):
    """Trạng thái sau mỗi nến: sự kiện xác nhận ở nến t đặt chiều; hai chiều ngược nhau cùng nến → 0."""
    votes = defaultdict(set)
    for e in res.events:
        v = mapping.get(e.structure_type)
        if v:
            votes[e.confirmed_bar_index].add(v)
    return _hold(votes, n)


def _hold(votes, n):
    out, s = [], 0
    for t in range(n):
        if t in votes:
            vs = votes[t]
            s = next(iter(vs)) if len(vs) == 1 else 0
        out.append(s)
    return out


def pd_respect_states(bars, res, away_atr=1.0, breach="far"):
    """FVG cùng khung: sau lần chạm đầu, close rời mép gần ≥ away_atr·ATR[t−1] → tôn trọng; close vượt
    mép xa (``breach="far"``) hoặc vượt 50% vùng (``breach="ce"`` — cách ICT xét bằng thân nến) → xuyên
    (kết quả đầu tiên, một lần mỗi FVG). Tôn trọng FVG tăng / xuyên FVG giảm → tăng."""
    tl, n = res.timeline, len(bars)
    votes = defaultdict(set)
    for f in res.events:
        if f.structure_type not in ("FVG_UP", "FVG_DOWN"):
            continue
        up = f.structure_type == "FVG_UP"
        lo, hi = f.details["lo"], f.details["hi"]
        ce = (lo + hi) / 2.0
        far_lo, far_hi = (ce, ce) if breach == "ce" else (lo, hi)
        touched = False
        for t in range(f.confirmed_bar_index + 1, n):
            b = bars[t]
            if not touched:
                touched = (b.low <= hi) if up else (b.high >= lo)
                if not touched:
                    continue
            atr = tl[t - 1]["atr"]
            if atr is None:
                continue
            if up and b.close < far_lo or (not up) and b.close > far_hi:
                votes[t].add(-1 if up else 1)
                break
            if up and b.close >= hi + away_atr * atr or (not up) and b.close <= lo - away_atr * atr:
                votes[t].add(1 if up else -1)
                break
    return _hold(votes, n)


def structure_states(res):
    return [(p["order"] if p["order"] in (1, -1) else 0) for p in res.timeline]


def htf_state_at(ltf_bars, htf_bars, htf_state):
    """Trạng thái khung lớn đã biết lúc đóng mỗi nến nhỏ (chỉ nến lớn đã đóng)."""
    closes = [b.close_time for b in htf_bars]
    return [htf_state[j] if (j := bisect.bisect_right(closes, b.close_time) - 1) >= 0 else 0 for b in ltf_bars]


# ---------------------------------------------------------------- kết cục + thống kê


def take_bars(res):
    first = {}
    for e in res.events:
        if e.structure_type.startswith("LIQ_"):
            for p in e.details["pools"]:
                first.setdefault(p["id"], p["nen_lay"])
    return first


def outcome(bars, res, take, t, s):
    """Dòng kết cục tại nến t (sau khi đóng) cho chiều s; None nếu thiếu vùng hoặc chưa rõ tới hết đoạn."""
    p = res.timeline[t]
    a, b = p["liq_above"], p["liq_below"]
    if a is None or b is None:
        return None
    c = bars[t].close
    da, db = a - c, c - b
    if da <= 0 or db <= 0:
        return None
    ta, tb = take.get(p["liq_above_id"]), take.get(p["liq_below_id"])
    ta = ta if ta is not None and ta > t else None
    tb = tb if tb is not None and tb > t else None
    if (ta is None and tb is None) or (ta is not None and ta == tb):
        return None
    up_first = tb is None or (ta is not None and ta < tb)
    exp_up = db / (da + db)
    return {"t": t, "s": s, "up_first": up_first, "exp_up": exp_up,
            "hit": up_first if s == 1 else (not up_first), "exp": exp_up if s == 1 else 1 - exp_up,
            "week": bars[t].bar_time.isocalendar()[:2]}


def flip_rows(bars, res, st, take):
    rows = []
    for t in range(1, len(bars)):
        if st[t] != 0 and st[t] != st[t - 1]:
            r = outcome(bars, res, take, t, st[t])
            if r:
                rows.append(r)
    return rows


def summarize(rows, n_flips=None, days=None):
    k = len(rows)
    out = {"mau": k}
    if n_flips is not None and days:
        out["lat_moi_ngay"] = round(n_flips / days, 2)
    if k < 10:
        return out
    hit = sum(r["hit"] for r in rows) / k
    exp = sum(r["exp"] for r in rows) / k
    byw = defaultdict(list)
    for r in rows:
        byw[r["week"]].append(r["hit"] - r["exp"])
    weeks = list(byw)
    rng = random.Random(7)
    bs = []
    for _ in range(2000):
        s = c = 0
        for _w in weeks:
            xs = byw[weeks[rng.randrange(len(weeks))]]
            s += sum(xs)
            c += len(xs)
        bs.append(s / c)
    bs.sort()
    out.update({"trung": round(hit, 3), "moc": round(exp, 3), "loi_the": round(hit - exp, 3),
                "ci95": [round(bs[50], 3), round(bs[1950], 3)]})
    # Cân bằng chiều: trung bình lợi thế của lần lật tăng và lật giảm — độ trôi dài hạn (vd vàng tăng
    # 2018–2023) cộng vào một chiều bao nhiêu thì trừ ở chiều kia bấy nhiêu, nên triệt tiêu.
    side = {}
    for s in (1, -1):
        rs = [r for r in rows if r["s"] == s]
        if rs:
            side[s] = sum(r["hit"] - r["exp"] for r in rs) / len(rs)
    if len(side) == 2:
        out["loi_the_tang"] = round(side[1], 3)
        out["loi_the_giam"] = round(side[-1], 3)
        out["loi_the_can_bang"] = round((side[1] + side[-1]) / 2, 3)
    return out


def calibration_rows(rows):
    bins = [[0, 0, 0.0] for _ in range(5)]
    for r in rows:
        k = min(4, int(r["exp_up"] * 5))
        bins[k][0] += 1
        bins[k][1] += r["up_first"]
        bins[k][2] += r["exp_up"]
    return [{"moc": round(e / n, 3), "thuc": round(u / n, 3), "n": n} for n, u, e in bins if n]


def calibration(bars, res, take, stride=8):
    bins = [[0, 0, 0.0] for _ in range(5)]
    for t in range(1, len(bars), stride):
        r = outcome(bars, res, take, t, 1)
        if r:
            k = min(4, int(r["exp_up"] * 5))
            bins[k][0] += 1
            bins[k][1] += r["up_first"]
            bins[k][2] += r["exp_up"]
    return [{"moc": round(e / n, 3), "thuc": round(u / n, 3), "n": n} for n, u, e in bins if n]


def htf_draw_rows(bars, st, hbars, hres):
    """Lật order flow ở khung nhỏ, đích/vô hiệu = vùng còn nguyên gần nhất của khung lớn (vd D1 — ICT: draw
    nằm ở khung ngày), lấy từ nến lớn ĐÃ ĐÓNG gần nhất. Bỏ dòng nếu trong nến lớn đang chạy giá đã xuyên
    vùng ≥ 0.1·ATR khung lớn trước lúc lật. Kết cục đo trên nến nhỏ (xuyên ≥ 0.1·ATR khung lớn)."""
    closes = [b.close_time for b in hbars]
    rows = []
    for t in range(1, len(bars)):
        s = st[t]
        if s == 0 or s == st[t - 1]:
            continue
        j = bisect.bisect_right(closes, bars[t].close_time) - 1
        if j < 0:
            continue
        p = hres.timeline[j]
        a, lw, atr = p["liq_above"], p["liq_below"], p["atr"]
        if a is None or lw is None or not atr:
            continue
        thr = 0.1 * atr
        c = bars[t].close
        if not (lw < c < a):
            continue
        k0 = t
        while k0 > 0 and bars[k0 - 1].close_time > closes[j]:
            k0 -= 1                                     # nến nhỏ đầu tiên sau lúc nến lớn j đóng
        if any(bars[k].high >= a + thr or bars[k].low <= lw - thr for k in range(k0, t + 1)):
            continue                                    # vùng đã bị lấy trong nến lớn đang chạy
        up_first = None
        for k in range(t + 1, len(bars)):
            hu, hd = bars[k].high >= a + thr, bars[k].low <= lw - thr
            if hu and hd:
                break                                   # cùng một nến nhỏ — bỏ
            if hu or hd:
                up_first = hu
                break
        if up_first is None:
            continue
        exp_up = (c - lw) / (a - lw)
        rows.append({"t": t, "s": s, "up_first": up_first, "exp_up": exp_up,
                     "hit": up_first if s == 1 else (not up_first), "exp": exp_up if s == 1 else 1 - exp_up,
                     "week": bars[t].bar_time.isocalendar()[:2]})
    return rows


def retrace_rows(bars, res, take, max_wait=32):
    """SHIFT_FVG: chờ lần chạm lại đầu tiên vào FVG (≤ max_wait nến, trước khi đích bị lấy, close chưa xuyên
    mép xa) rồi chấm từ nến đó."""
    tl = res.timeline
    rows, skip = [], {"khong_hoi": 0, "xuyen": 0, "thieu_vung": 0}
    for e in res.events:
        if e.structure_type not in ("SHIFT_FVG_UP", "SHIFT_FVG_DOWN"):
            continue
        up = e.structure_type == "SHIFT_FVG_UP"
        lo, hi = e.details["lo"], e.details["hi"]
        c0 = e.confirmed_bar_index
        tgt = tl[c0]["liq_above_id" if up else "liq_below_id"]
        r = None
        for t in range(c0 + 1, min(len(bars), c0 + 1 + max_wait)):
            if tgt is not None and take.get(tgt) is not None and take[tgt] <= t:
                break
            if (bars[t].low <= hi) if up else (bars[t].high >= lo):
                r = t
                break
        if r is None:
            skip["khong_hoi"] += 1
            continue
        if (bars[r].close < lo) if up else (bars[r].close > hi):
            skip["xuyen"] += 1
            continue
        o = outcome(bars, res, take, r, 1 if up else -1)
        if o is None:
            skip["thieu_vung"] += 1
            continue
        rows.append(o)
    return rows, skip


# ---------------------------------------------------------------- chạy


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=os.path.join(ROOT, "data", "lab.sqlite"))
    ap.add_argument("--json", default="")
    ap.add_argument("--allow-test", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    con = sqlite3.connect("file:%s?mode=ro" % args.db, uri=True)
    out = {"meta": {"phien_ban": SURVEY_VERSION, "python": platform.python_version(), "doan_kiem_tra_tu": TEST_START,
                    "dinh_nghia": {k: v for k, v in DEFS.items()}, "du_lieu": []},
           "ket_qua": {}}
    for sym, tfs in DATASETS.items():
        for pname, (a, b) in PERIODS.items():
            key = "%s %s" % (sym, pname)
            runs = {}
            o = {}
            for tf, ds in tfs.items():
                r = load(con, ds, a, b, args.allow_test)
                if not r[0]:
                    o["%s · (bỏ qua)" % tf] = "dataset %s không có nến trong %s" % (ds, pname)
                    continue
                runs[tf] = r
                out["meta"]["du_lieu"].append(r[2])
            for tf, (bars, res, _m) in runs.items():
                take = take_bars(res)
                days = len({br.bar_time.date() for br in bars})
                series = {name: event_states(res, len(bars), m) for name, m in DEFS.items()}
                if tf in ("M5", "M15"):
                    series["phản ứng FVG (chặt 1 ATR)"] = pd_respect_states(bars, res)
                    series["phản ứng FVG (xuyên = close qua CE 50%)"] = pd_respect_states(bars, res, breach="ce")
                    series["thứ tự HH/HL (cấu trúc)"] = structure_states(res)
                for name, st in series.items():
                    flips = sum(1 for t in range(1, len(st)) if st[t] != 0 and st[t] != st[t - 1])
                    o["%s · %s" % (tf, name)] = summarize(flip_rows(bars, res, st, take), flips, days)
                if tf == "M15":
                    o["M15 · hiệu chuẩn mốc ngẫu nhiên"] = calibration(bars, res, take)
                    rows, skip = retrace_rows(bars, res, take)
                    o["M15 · shift+FVG, chấm lúc hồi về FVG"] = dict(summarize(rows), bo_qua=skip)
                    sh_rows = flip_rows(bars, res, series["chỉ shift"], take)
                    kz = {e.event_bar_index: (e.details.get("killzone") or "ngoai")
                          for e in res.events if e.structure_type in ("SHIFT_UP", "SHIFT_DOWN")}
                    for z in ("ny_am", "london", "asia", "london_close", "ngoai"):
                        o["M15 · chỉ shift, killzone %s" % z] = summarize([r for r in sh_rows if kz.get(r["t"]) == z])
                    rs = flip_rows(bars, res, series["run+shift"], take)
                    for htf in ("H1", "H4"):
                        hb, hr, _hm = runs[htf]
                        hst = htf_state_at(bars, hb, event_states(hr, len(hb), DEFS["run+shift"]))
                        for lab, sign in (("cùng chiều", 1), ("ngược chiều", -1)):
                            o["M15 · run+shift, %s %s" % (htf, lab)] = summarize([r for r in rs if hst[r["t"]] == sign * r["s"]])
            if "D1" in runs:                            # ICT: draw on liquidity nằm ở khung ngày
                db, dr, _dm = runs["D1"]
                for ltf in ("M15", "H1"):
                    if ltf not in runs:
                        continue
                    lb, lr, _lm = runs[ltf]
                    for name in ("run+shift", "chỉ shift"):
                        st = event_states(lr, len(lb), DEFS[name])
                        o["%s · %s → đích/vô hiệu là vùng D1" % (ltf, name)] = summarize(htf_draw_rows(lb, st, db, dr))
                lb, lr, _lm = runs["H1"]
                cal = htf_draw_rows(lb, [((t // 8) % 2) * 2 - 1 for t in range(len(lb))], db, dr)   # lật đều đặn → mẫu hiệu chuẩn
                o["H1 · hiệu chuẩn mốc với vùng D1"] = calibration_rows(cal)
            out["ket_qua"][key] = o
            print("==", key)
            for k, v in o.items():
                print("   %-48s %s" % (k, json.dumps(v, ensure_ascii=False)))
            sys.stdout.flush()
    out["meta"]["thoi_gian_s"] = round(time.time() - t0, 1)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print("Đã ghi", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
