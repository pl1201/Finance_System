"""Khảo sát MSS (ict_structure 0.10.0) trên đoạn dev — plan_mss_ob_pd.md §6 (khai trước khi chạy).

Chỉ số MÔ TẢ (không có đúng / sai): tần suất MSS / shift, tỷ lệ sweep → MSS, độ trễ, cờ significant / FVG, phá yếu, phần giao
MSS–shift cùng chiều (±3 nến), độ nhạy theo ``mss_chan_atr`` × ``mss_chan_nen``; OB theo MSS so với theo shift (giữ / hỏng / hết
hạn, breaker), order flow «vô hiệu». Tắt lớp nhận diện (``nd_bat = false``) cho nhanh — MSS / OB không phụ thuộc lớp đó.

Tiêu chí giữ mặc định (khai trước): giữ k = 2.0, n = 5 nếu MSS / ngày ∈ [0,5×; 2×] shift / ngày trên cả hai mã; nếu không, chọn k
gần 2.0 nhất trong lưới thoả. Không chỉnh theo kết cục giá nào. Không dùng đoạn kiểm tra (≥ 2024-09-01).

    .\\.venv\\Scripts\\python.exe research\\khao_sat_mss.py --db data\\lab.sqlite --json docs\\research\\khao_sat\\mss_dev.json
"""
from __future__ import annotations

import argparse
import bisect
import json
import os
import sqlite3
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import regime_survey as RS  # noqa: E402
from core.algorithms.ict_structure import IctStructureAlgorithm  # noqa: E402
from core.engine import run_algorithm  # noqa: E402

SETS = [
    {"key": "XAUUSD M15 2018–08/2024", "ds": "ds_a5212fd37814", "start": "2018-01-01", "end": RS.TEST_START},
    {"key": "EURUSD M15 2018–08/2024", "ds": "ds_a9a2a5e4cef5", "start": "2018-01-01", "end": RS.TEST_START},
]
GRID_K = (1.0, 1.5, 2.0, 2.5, 3.0)
GRID_N = (3, 8)                     # thêm hai độ dài đoạn ở k = 2.0 (n = 5 nằm trong GRID_K)
MATCH_BARS = 3
DEFAULT = {"mss_chan_atr": 2.0, "mss_chan_nen": 5}


def run(bars, tf, cal, **kw):
    t0 = time.time()
    res = run_algorithm(bars, IctStructureAlgorithm(timeframe=tf, session_calendar=cal, nd_bat=False, **kw))
    return res, time.time() - t0


def flips(events, prefix):
    return [(e.confirmed_bar_index, e.direction) for e in events if e.structure_type in (prefix + "_UP", prefix + "_DOWN")]


def matched(a, b, w):
    """Tỷ lệ phần tử của a có phần tử cùng chiều của b cách ≤ w nến."""
    by = {"up": sorted(i for i, d in b if d == "up"), "down": sorted(i for i, d in b if d == "down")}
    hit = 0
    for i, d in a:
        xs = by[d]
        j = bisect.bisect_left(xs, i - w)
        hit += j < len(xs) and xs[j] <= i + w
    return hit / len(a) if a else None


def ob_block(st):
    ob, of = st["order_block"], st["order_flow"]
    keys = ("xac_nhan", "moi_ngay", "cham", "hong", "giu", "het_han", "het_han_sau_cham", "het_han_vi_shift", "breaker",
            "breaker_giu", "breaker_hong", "ty_le_giu_khi_cham", "ty_le_hong_sau_cham")
    out = {k: ob.get(k) for k in keys if k in ob}
    out["order_flow_doi_chieu_moi_ngay"] = of["doi_chieu_moi_ngay"]
    out["order_flow_ly_do"] = of["theo_ly_do"]
    out["ob_hong_moi_ngay"] = (of["theo_ly_do"].get("ob_hong", 0) / st["so_ngay_giao_dich"]) if st["so_ngay_giao_dich"] else None
    out["pd_bias_doi_moi_ngay"] = st["pd_array"]["pd_bias_doi_moi_ngay"]
    return out


def mss_block(st):
    m = st["mss"]
    keys = ("so", "moi_ngay", "ty_le_sweep_thanh_mss", "tre_tu_sweep_trung_vi", "tre_tu_sweep_p90", "ty_le_significant",
            "ty_le_co_fvg", "chan_so_nen_trung_vi", "chan_atr_trung_vi", "ung_vien", "khong_co_moc", "huy_vuot_cuc_tri",
            "huy_khoang_trong", "pha_yeu", "gop_vao_mss")
    return {k: m[k] for k in keys}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join("data", "lab.sqlite"))
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    con = sqlite3.connect("file:%s?mode=ro" % a.db.replace("\\", "/"), uri=True)
    report = {"plan": "docs/plans/plan_mss_ob_pd.md §6", "thuat_toan": "ict_structure " + IctStructureAlgorithm.version,
              "doan_kiem_tra_tu": RS.TEST_START, "nd_bat": False, "lich": RS.CAL, "mac_dinh": DEFAULT,
              "luoi_k": list(GRID_K), "luoi_n_o_k_mac_dinh": list(GRID_N),
              "khop_mss_shift_trong_nen": MATCH_BARS, "bo": []}
    for spec in SETS:
        ds, bars, tf, meta = RS.load(con, spec, False)
        cal = RS.CAL[ds["symbol"]]                     # lịch phiên theo mã, như regime_survey (khoảng trống / killzone đúng)
        print("==", spec["key"], len(bars), "nến", flush=True)
        legacy, dt = run(bars, tf, cal, doi_huong="shift", ob_pd_array=False)
        st_l = legacy.stats["chi_so_thuat_toan"]
        days = st_l["so_ngay_giao_dich"]
        shift_day = st_l["shift"]["moi_ngay"]
        shifts = flips(legacy.events, "SHIFT")
        print("  shift %.3f/ngày (%.0fs)" % (shift_day, dt), flush=True)
        row = {"meta": meta, "so_ngay": days, "shift": {"so": len(shifts), "moi_ngay": shift_day},
               "ob_theo_shift_0_9": ob_block(st_l), "luoi": []}
        for k, n in [(k, 5) for k in GRID_K] + [(2.0, n) for n in GRID_N]:
            res, dt = run(bars, tf, cal, mss_chan_atr=k, mss_chan_nen=n)
            st = res.stats["chi_so_thuat_toan"]
            ms = flips(res.events, "MSS")
            cell = {"mss_chan_atr": k, "mss_chan_nen": n, **mss_block(st),
                    "ty_le_so_voi_shift": (st["mss"]["moi_ngay"] / shift_day) if shift_day else None,
                    "mss_co_shift_gan": matched(ms, shifts, MATCH_BARS), "shift_co_mss_gan": matched(shifts, ms, MATCH_BARS)}
            if k == DEFAULT["mss_chan_atr"] and n == DEFAULT["mss_chan_nen"]:
                row["ob_theo_mss_pd"] = ob_block(st)
            row["luoi"].append(cell)
            print("  k=%.1f n=%d: %.3f MSS/ngày (×%s shift), giao %.2f / %.2f (%.0fs)" % (
                k, n, cell["moi_ngay"] or 0, "%.2f" % cell["ty_le_so_voi_shift"] if shift_day else "—",
                cell["mss_co_shift_gan"] or 0, cell["shift_co_mss_gan"] or 0, dt), flush=True)
        report["bo"].append(row)
    ok = {}
    for k in GRID_K:
        rs = [next(c for c in r["luoi"] if c["mss_chan_atr"] == k and c["mss_chan_nen"] == 5)["ty_le_so_voi_shift"]
              for r in report["bo"]]
        ok[k] = all(x is not None and 0.5 <= x <= 2.0 for x in rs)       # không có shift → không so được → không đạt
    keep = ok[DEFAULT["mss_chan_atr"]]
    chosen = DEFAULT["mss_chan_atr"] if keep else min((k for k in GRID_K if ok[k]),
                                                       key=lambda k: abs(k - DEFAULT["mss_chan_atr"]), default=None)
    report["tieu_chi"] = {"khoang_ty_le": [0.5, 2.0], "dat_theo_k": {str(k): v for k, v in ok.items()},
                          "giu_mac_dinh": keep, "k_chon": chosen, "n_chon": DEFAULT["mss_chan_nen"]}
    print("Tiêu chí:", report["tieu_chi"], flush=True)
    if a.json:
        with open(a.json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=1)
        print("đã ghi", a.json)


if __name__ == "__main__":
    main()
