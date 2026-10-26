"""Kiểm định OB theo ngữ cảnh — tìm OB mạnh, vùng giá trị (bản khai trước ``docs/research/kiem_dinh_ob_ngu_canh.md``).

CHỈ ĐỌC database, chỉ đoạn phát triển. Tập OB gốc X1 (``kiem_dinh_order_block.extreme_zones`` pivot 10); điều kiện K1–K6
đọc ở hàng timeline / sự kiện của ``ict_structure`` tới nến c (nhân quả). Mỗi bộ lọc: Δ = G(OB thỏa) − G(5 vùng song sinh
hình học của chính các OB đó), vòng đời / song sinh / bootstrap của ``kiem_dinh_order_block``. Chọn ở A, xác nhận ở B.
Đọc thêm: OB thỏa so với không thỏa; K1, K5 so với song sinh khớp ngữ cảnh; bảng theo số điều kiện đạt.

Ví dụ (PowerShell, từ thư mục market-structure-lab)::

    .\\.venv\\Scripts\\python.exe research\\kiem_dinh_ob_ngu_canh.py
    .\\.venv\\Scripts\\python.exe research\\kiem_dinh_ob_ngu_canh.py --thu     # 2 tháng, chỉ in số OB mỗi điều kiện
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import platform
import sqlite3
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import ict_indicator_survey as S  # noqa: E402
import kiem_dinh_order_block as K  # noqa: E402  (vòng đời, song sinh, bootstrap)
import regime_survey as RS  # noqa: E402
from core.algorithms.ict_structure import LEGACY_0_9, IctStructureAlgorithm  # noqa: E402
from core.engine import run_algorithm  # noqa: E402

VERSION = "kiem-dinh-ob-ngu-canh-v1.0"
FILTERS = ("K1", "K2", "K3", "K4", "K5", "K6")
TEN = {"K1": "Cùng chiều khung lớn (thứ tự H4)", "K2": "Killzone London / NY AM", "K3": "Sweep phía ngược trước đó",
       "K4": "Displacement rời OB", "K5": "Vùng giá trị (discount / premium H4)", "K6": "Hợp lưu ≥ 3/5"}
KZ = {"london", "ny_am"}


def pos_h4(row, mid):
    """Vị trí của giá ``mid`` trong dealing range H4 ở hàng timeline (None khi chưa có)."""
    hi, lo = row.get("htf_H4_dealing_hi"), row.get("htf_H4_dealing_lo")
    if hi is None or lo is None or not hi > lo:
        return None
    return (mid - lo) / (hi - lo)


def in_value(dr, pos):
    return pos is not None and (pos <= 0.5 if dr > 0 else pos >= 0.5)


def contexts(tl, events, zones):
    """K1–K6 của mỗi OB (dr, lo, hi, c, p, i) — chỉ đọc tới nến c."""
    sweep = {1: sorted(e.confirmed_bar_index for e in events if e.structure_type == "LIQ_SWEEP_SSL"),
             -1: sorted(e.confirmed_bar_index for e in events if e.structure_type == "LIQ_SWEEP_BSL")}
    disp = {1: sorted(e.confirmed_bar_index for e in events if e.structure_type == "DISPLACEMENT_UP"),
            -1: sorted(e.confirmed_bar_index for e in events if e.structure_type == "DISPLACEMENT_DOWN")}

    def any_in(xs, a, b):                                  # có phần tử trong [a, b]
        j = bisect.bisect_left(xs, a)
        return j < len(xs) and xs[j] <= b

    out = []
    for dr, lo, hi, c, p, i in zones:
        row = tl[c]
        k = {"K1": row.get("htf_H4_order") == dr,
             "K2": row.get("killzone") in KZ,
             "K3": any_in(sweep[dr], p, c),
             "K4": any_in(disp[dr], i + 1, c),
             "K5": in_value(dr, pos_h4(row, (lo + hi) / 2))}
        k["diem"] = sum(k.values())
        k["K6"] = k["diem"] >= 3
        out.append(k)
    return out


def measure(d, tl, zones, ctx, rng, rng_ctx):
    """Hàng đo cho mỗi OB (cùng điều kiện bỏ vùng như ``kiem_dinh_order_block.measure``) + song sinh khớp K1 / K5."""
    rows = []
    for (dr, lo, hi, c, _p, _i), k in zip(zones, ctx):
        if not (hi > lo) or not np.isfinite(d.atr[c]) or d.atr[c] <= 0 or not K.full_window(d, c):
            continue
        tau, g, r = K.life(d, dr, lo, hi, c)
        tw = K.twins(d, dr, lo, hi, c, rng)
        row = dict(k, part=int(d.part[c]), tau=tau, g=g, r=r, w=(hi - lo) / d.atr[c],
                   gt=_mean([x[1] for x in tw]), rt=_mean([x[2] for x in tw]),
                   touch_t=float(np.mean([x[0] is not None for x in tw])) if tw else np.nan)
        if k["K1"]:
            row["gt_K1"] = _mean([x[1] for x in K.twins(d, dr, lo, hi, c, rng_ctx,
                                                       accept=lambda t, a, b: tl[t].get("htf_H4_order") == dr)])
        if k["K5"]:
            row["gt_K5"] = _mean([x[1] for x in K.twins(d, dr, lo, hi, c, rng_ctx,
                                                       accept=lambda t, a, b: in_value(dr, pos_h4(tl[t], (a + b) / 2)))])
        rows.append(row)
    return rows


def _mean(xs):
    xs = [x for x in xs if np.isfinite(x)]
    return float(np.mean(xs)) if xs else np.nan


def summarize(d, rows, part):
    out = {"tat_ca": K.summarize(d, rows, part)}       # kiểm chéo: phải trùng X1 của kiem_dinh_order_block_dev.json
    for f in FILTERS:
        yes = [x for x in rows if x[f]]
        no = [x for x in rows if not x[f]]
        s = K.summarize(d, yes, part)
        s_no = K.summarize(d, no, part)
        s["giu_that_khi_khong_thoa"] = s_no["giu_that"]
        s["ty_le_thoa"] = round(len([x for x in yes if x["part"] == part]) /
                                max(len([x for x in rows if x["part"] == part]), 1), 4)
        if f in ("K1", "K5"):
            alt = [dict(x, gt=x.get("gt_" + f, np.nan)) for x in yes]
            m = K.summarize(d, alt, part)
            s["delta_giu_song_sinh_khop_ngu_canh"] = m["delta_giu"]
            s["delta_giu_song_sinh_khop_ngu_canh_ci95"] = m["delta_giu_ci95"]
            s["giu_song_sinh_khop_ngu_canh"] = m["giu_song_sinh"]
        out[f] = s
    out["theo_diem"] = {}
    for sc in range(6):
        sel = [x for x in rows if x["diem"] == sc]
        m = K.summarize(d, sel, part)
        out["theo_diem"][str(sc)] = {k: m[k] for k in ("so_vung", "n_cap", "giu_that", "giu_song_sinh", "delta_giu")}
    return out


def judge(res):
    syms = list(res)
    rows = []
    for f in FILTERS:
        a = [res[s]["A"][f] for s in syms]
        ok = all(x["delta_giu"] is not None and x["delta_giu_ci95"] and x["delta_giu_ci95"][0] > 0
                 and x["n_cap"] >= K.MIN_N for x in a)
        row = {"bo_loc": f, "hop_le_A": ok}
        if ok:
            b = [res[s]["B"][f] for s in syms]
            row["xac_nhan_B"] = all(x["delta_giu_ci95"] and x["delta_giu_ci95"][0] > 0 for x in b)
        rows.append(row)
    return {"bang": rows, "vung_manh": [r["bo_loc"] for r in rows if r.get("xac_nhan_B")]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", default=os.path.join(ROOT, "docs", "research", "khao_sat", "kiem_dinh_ob_ngu_canh_dev.json"))
    ap.add_argument("--db", default=os.environ.get("MSL_DB_PATH") or os.path.join(ROOT, "data", "lab.sqlite"))
    ap.add_argument("--thu", action="store_true", help="Chạy thử 2 tháng đầu, chỉ in số OB thỏa mỗi điều kiện")
    args = ap.parse_args()
    t_all = time.time()
    con = sqlite3.connect("file:%s?mode=ro" % args.db.replace("\\", "/"), uri=True)
    with open(os.path.abspath(__file__), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    meta = {"phien_ban": VERSION, "script_sha256": sha, "python": platform.python_version(),
            "khai_truoc": "docs/research/kiem_dinh_ob_ngu_canh.md (commit 30b4bd3)", "doan_kiem_tra_tu": S.TEST_START,
            "chia_A_B": K.SPLIT.date().isoformat(), "n_boot": S.N_BOOT, "lan_chay": {}}
    res = {}
    for spec in S.SETS:
        sym = spec["key"].split()[0]
        if args.thu:
            spec = dict(spec, end="2018-03-01")
        t0 = time.time()
        _d, bars, tf, src_meta = RS.load(con, spec, allow_test=False)
        algo = IctStructureAlgorithm(timeframe=tf, session_calendar=RS.CAL[sym], **LEGACY_0_9)
        run = run_algorithm(bars, algo)
        tl = run.timeline
        assert all(p["bar_index"] == j for j, p in enumerate(tl))
        d = K.Data(bars, [p.get("atr") for p in tl])
        zones = K.extreme_zones(d, 10, False, full=True)
        ctx = contexts(tl, run.events, zones)
        print("%s: %d OB X1 · thỏa %s · %.0f s" % (sym, len(zones), {f: sum(k[f] for k in ctx) for f in FILTERS},
                                                  time.time() - t0), flush=True)
        if args.thu:
            continue
        rows = measure(d, tl, zones, ctx, np.random.default_rng(S.SEED + 41), np.random.default_rng(S.SEED + 47))
        res[sym] = {"A": summarize(d, rows, 0), "B": summarize(d, rows, 1)}
        for f in FILTERS:
            a = res[sym]["A"][f]
            print("  %s %-38s A: thỏa %.0f%% · G %s / ss %s · Δ %s %s · n cặp %d" % (
                f, TEN[f], 100 * a["ty_le_thoa"], a["giu_that"], a["giu_song_sinh"], a["delta_giu"],
                a["delta_giu_ci95"], a["n_cap"]), flush=True)
        meta["lan_chay"][sym] = dict(src_meta, phien_ban_thuat_toan=algo.version, giay=round(time.time() - t0, 1))
    if args.thu:
        return
    verdict = judge(res)
    meta["giay"] = round(time.time() - t_all, 1)
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "ten_bo_loc": TEN, "ket_qua": res, "danh_gia": verdict}, fh, ensure_ascii=False,
                  indent=1)
    print(json.dumps(verdict, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
