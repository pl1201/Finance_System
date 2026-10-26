"""Kiểm định bộ trạng thái v2 (trend / range / sideway) theo bản khai trước ``docs/research/kiem_dinh_trang_thai.md``.

CHỈ ĐỌC database, chỉ đoạn phát triển (2018-01-01 → 2024-09-01). Đo C1–C9 cho bốn nhu cầu N1–N4:

* C1 nhân quả (chạy cắt = chạy trọn rồi lọc); C2 ổn định hiển thị;
* C3–C6 khớp tham chiếu nhìn lại (cửa sổ tâm ±16 nến — nhìn tương lai có chủ ý, chỉ để chấm), so với mốc ngây thơ
  (cùng định nghĩa nhưng chỉ nhìn quá khứ), ADX + DI, null dịch vòng;
* C7 khác nhiễu: chạy v2 trên random walk giữ mùa vụ (σ theo giờ New York × biến động ngày, Student-t 4);
* C8 tiếp diễn 16 nến trong trend (CI khối tuần); C9 lấy từ ``khao_sat/trang_thai_v2_dev.json``.

Không đổi tiêu chí sau khi xem số (bản khai trước commit 4fffacb, sửa trước khi chạy 2c2ed12).

Ví dụ::

    .\\.venv\\Scripts\\python.exe research\\kiem_dinh_trang_thai.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sqlite3
import sys
import time
from dataclasses import replace
from datetime import timedelta

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import ict_indicator_survey as S  # noqa: E402  (đoạn dev, seed, số lượt bootstrap)
import khao_sat_ob_ote as OB  # noqa: E402  (bootstrap khối tuần, CI)
import khao_sat_trang_thai_v2 as T2  # noqa: E402  (wilder, đoạn, κ)
import regime_survey as RS  # noqa: E402
from core.algorithms.ict_structure import LEGACY_0_9, IctStructureAlgorithm  # noqa: E402
from core.engine import run_algorithm  # noqa: E402

VERSION = "kiem-dinh-trang-thai-v1.0"
W = 16                      # nửa cửa sổ tham chiếu nhìn lại (nến)
W_PAST = 32                 # cửa sổ mốc ngây thơ (nến) — cửa sổ ER 8 giờ của v2
GAP_MAX = timedelta(hours=2)
SHIFT_WEEKS = (5, 10, 20)
BARS_PER_WEEK = 460
SEEDS = (11, 12, 13)
TARGETS = {"C2_doi_moi_100": 10, "C2_doan_ngan": 0.25, "C3_kappa": 0.40, "C4_hon_ngay_tho": 0.05,
           "C4_hon_null": 0.30, "C5_sai_chieu": 0.05, "C5_recall": 0.70, "C6_mat_doan": 0.35,
           "C7_trend_hon": 0.05, "C7_do_dai": 1.2, "C8_tiep_dien": 0.53}
V2_CLASS = {"trend_len": "len", "trend_xuong": "xuong", "range": "range", "nhieu": "nhieu"}


# ------------------------------------------------------------------ chạy thuật toán

def run_states(bars, sym):
    algo = IctStructureAlgorithm(timeframe="M15", session_calendar=RS.CAL[sym], **LEGACY_0_9)
    r = run_algorithm(bars, algo)
    tl = r.timeline
    st = np.array([V2_CLASS.get(p.get("nd_trang_thai"), "none") for p in tl], dtype=object)
    raw = [(p.get("nd_trang_thai"), p.get("nd_do_manh"), p.get("nd_nen")) for p in tl]
    return st, raw, algo.version


# ------------------------------------------------------------------ tham chiếu, mốc

def gap_ok(bars, lo_off, hi_off):
    """ok[t] = cửa sổ [t+lo_off, t+hi_off] nằm trong dữ liệu và không vắt khoảng trống > GAP_MAX."""
    n = len(bars)
    big = np.zeros(n, dtype=int)                     # big[i] = 1 nếu giữa nến i−1 và i có khoảng trống lớn
    for i in range(1, n):
        if bars[i].bar_time - bars[i - 1].bar_time > GAP_MAX:
            big[i] = 1
    cum = np.cumsum(big)
    ok = np.zeros(n, dtype=bool)
    for t in range(n):
        a, b = t + lo_off, t + hi_off
        if a < 0 or b >= n:
            continue
        ok[t] = cum[b] - cum[a] == 0                 # không có khoảng trống lớn trong (a, b]
    return ok


def classify(C, H, L, atr, a_off, b_off, ok):
    """Lớp theo cửa sổ [t+a_off, t+b_off]: N = C[b] − C[a], e = |N| / Σ|ΔC|, R = max H − min L (định nghĩa §2)."""
    n = C.size
    dc = np.abs(np.r_[np.nan, np.diff(C)])
    cs = np.r_[0.0, np.nancumsum(dc[1:])]            # cs[i] = Σ|ΔC| tới nến i
    width = b_off - a_off + 1
    hmax = pd.Series(H).rolling(width).max().values
    lmin = pd.Series(L).rolling(width).min().values
    out = np.full(n, "none", dtype=object)
    for t in range(n):
        a, b = t + a_off, t + b_off
        if not ok[t] or a < 0 or b >= n or not np.isfinite(atr[t]) or atr[t] <= 0:
            continue
        N = C[b] - C[a]
        path = cs[b] - cs[a]
        e = abs(N) / path if path > 0 else 0.0
        R = hmax[b] - lmin[b]
        A = atr[t]
        if N >= 2 * A and e >= 0.25:
            out[t] = "len"
        elif N <= -2 * A and e >= 0.25:
            out[t] = "xuong"
        elif R <= 4 * A and abs(N) < A:
            out[t] = "range"
        else:
            out[t] = "nhieu"
    return out


def adx_di(H, L, C):
    pc = np.r_[np.nan, C[:-1]]
    tr = np.nanmax(np.vstack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=0)
    up, dn = np.r_[np.nan, np.diff(H)], np.r_[np.nan, -np.diff(L)]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    atr = T2.wilder(tr, 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        pdi, mdi = 100 * T2.wilder(pdm, 14) / atr, 100 * T2.wilder(mdm, 14) / atr
        adx = T2.wilder(100 * np.abs(pdi - mdi) / (pdi + mdi), 14)
    return atr, adx, pdi, mdi


def three(x):
    return np.where(x == "len", 1, np.where(x == "xuong", -1, np.where(x == "none", 9, 0)))


def kappa3(a, b):
    a3, b3 = three(a), three(b)
    ok = (a3 != 9) & (b3 != 9)
    a3, b3 = a3[ok], b3[ok]
    if not a3.size:
        return None
    po = float((a3 == b3).mean())
    pe = sum(float((a3 == c).mean()) * float((b3 == c).mean()) for c in (-1, 0, 1))
    return round((po - pe) / (1 - pe), 4) if pe < 1 else None


# ------------------------------------------------------------------ thước

def segments(lab, cls_ok):
    """Đoạn liên tiếp cùng nhãn (cắt ở nến 'none'): [(nhãn, đầu, độ dài)]."""
    out, i, n = [], 0, lab.size
    while i < n:
        if not cls_ok[i]:
            i += 1
            continue
        j = i
        while j + 1 < n and cls_ok[j + 1] and lab[j + 1] == lab[i]:
            j += 1
        out.append((lab[i], i, j - i + 1))
        i = j + 1
    return out


def measures(v2, ref, C, week, nW, M, fwd_ok):
    valid = (v2 != "none") & (ref != "none")
    trend_v2 = np.isin(v2, ("len", "xuong"))
    d_v2 = np.where(v2 == "len", 1, np.where(v2 == "xuong", -1, 0))
    d_ref = np.where(ref == "len", 1, np.where(ref == "xuong", -1, 0))
    ref_tr = valid & (d_ref != 0)
    recall = float((d_v2[ref_tr] == d_ref[ref_tr]).mean()) if ref_tr.any() else None
    wrong_mask = valid & trend_v2
    wrong = float((d_ref[wrong_mask] == -d_v2[wrong_mask]).mean()) if wrong_mask.any() else None
    # trễ vào trend trên đoạn tham chiếu ≥ 8 nến
    fracs = []
    for name, s, k in segments(ref, ref != "none"):
        if name not in ("len", "xuong") or k < 8:
            continue
        want = 1 if name == "len" else -1
        hit = np.nonzero(d_v2[s:s + k] == want)[0]
        fracs.append(float(hit[0]) / k if hit.size else 1.0)
    # ổn định hiển thị
    v_ok = v2 != "none"
    segs = segments(v2, v_ok)
    changes = sum(1 for i in range(1, v2.size) if v_ok[i] and v_ok[i - 1] and v2[i] != v2[i - 1])
    n_ok = int(v_ok.sum())
    # tiếp diễn 16 nến
    fut = np.r_[C[W:] - C[:-W], np.full(W, np.nan)]
    cont = trend_v2 & fwd_ok & np.isfinite(fut) & (fut != 0)
    num = (np.sign(fut[cont]) == d_v2[cont]).astype(float)
    bs, est = OB.week_ratio_boot(M, week[cont], nW, num, np.ones(num.size))
    trend_lens = [k for name, _s, k in segs if name in ("len", "xuong")]
    return {
        "n_cham": int(valid.sum()),
        "ty_le_v2": {c: round(float((v2[v_ok] == c).mean()), 4) for c in ("len", "xuong", "range", "nhieu")},
        "ty_le_tham_chieu": {c: round(float((ref[ref != "none"] == c).mean()), 4) for c in ("len", "xuong", "range", "nhieu")},
        "kappa3": kappa3(v2, ref),
        "recall_trend_dung_chieu": round(recall, 4) if recall is not None else None,
        "sai_chieu": round(wrong, 4) if wrong is not None else None,
        "mat_doan_trung_vi": round(float(np.median(fracs)), 4) if fracs else None,
        "so_doan_tham_chieu_trend": len(fracs),
        "doi_moi_100": round(100.0 * changes / max(n_ok, 1), 2),
        "doan_ngan_duoi_4": round(sum(1 for _n, _s, k in segs if k < 4) / max(len(segs), 1), 4),
        "trend_do_dai_trung_vi": float(np.median(trend_lens)) if trend_lens else None,
        "tiep_dien_16": round(float(est), 4), "tiep_dien_16_ci95": OB.ci(bs), "n_tiep_dien": int(cont.sum()),
        "ma_tran": {r: {c: int(((ref == r) & (v2 == c) & valid).sum()) for c in ("len", "xuong", "range", "nhieu")}
                    for r in ("len", "xuong", "range", "nhieu")},
    }


# ------------------------------------------------------------------ chuỗi giả

def surrogate(bars, seed):
    """Random walk giữ mùa vụ (§3): σ theo giờ New York × biến động ngày thật, Student-t 4; râu theo nến thật."""
    rng = np.random.default_rng(seed)
    n = len(bars)
    O = np.array([b.open for b in bars]); H = np.array([b.high for b in bars])
    L = np.array([b.low for b in bars]); C = np.array([b.close for b in bars])
    hour = np.array([b.bar_time.astimezone(RS.NY).hour for b in bars])
    day = np.array([(b.bar_time.astimezone(RS.NY) + timedelta(hours=7)).date().toordinal() for b in bars])
    dc = np.r_[np.nan, np.abs(np.diff(C))]
    contiguous = np.r_[False, np.array([bars[i].bar_time - bars[i - 1].bar_time <= GAP_MAX for i in range(1, n)])]
    sig_h = {h: float(np.nanmedian(dc[(hour == h) & contiguous])) for h in range(24) if ((hour == h) & contiguous).any()}
    base = np.array([sig_h.get(h, np.nanmedian(dc)) for h in hour])
    dvol = pd.Series(np.where(contiguous, dc / base, np.nan)).groupby(day).transform(lambda x: np.sqrt(np.nanmean(x ** 2)))
    s_day = (dvol / np.nanmedian(dvol.values)).fillna(1.0).values
    scale = base * s_day
    z = rng.standard_t(4, n) / np.sqrt(2.0)
    up_w = (H - np.maximum(O, C)) / np.where(scale > 0, scale, 1.0)
    dn_w = (np.minimum(O, C) - L) / np.where(scale > 0, scale, 1.0)
    out, prev = [], float(C[0])
    for i, b in enumerate(bars):                     # float Python như nến thật (lõi so sánh kiểu bool của số thường)
        o = prev
        c = float(o + scale[i] * z[i])
        h = float(max(o, c) + up_w[i] * scale[i])
        lo = float(min(o, c) - dn_w[i] * scale[i])
        out.append(replace(b, open=o, high=h, low=lo, close=c))
        prev = c
    return out


# ------------------------------------------------------------------ main

def causality(bars, sym, n_tail=16000, cuts=(0.2, 0.4, 0.6, 0.8, 0.95)):
    """C1: chạy trên n_tail nến cuối của dev; chạy cắt ở 5 điểm phải trùng chạy trọn tới điểm cắt."""
    part = bars[-n_tail:]
    _st, full, _v = run_states(part, sym)
    diff = 0
    for c in cuts:
        k = int(len(part) * c)
        _s, pre, _v = run_states(part[:k], sym)
        diff += sum(1 for a, b in zip(pre, full[:k]) if a != b)
    return {"nen": len(part), "diem_cat": list(cuts), "nen_lech": diff}


def explore(con, out_path):
    """KHÁM PHÁ — ngoài bản khai trước, không vào tiêu chí: v2 có khớp tham chiếu nhìn lại ở thang dài hơn không?
    κ3 / recall / sai chiều của v2 và mốc ngây thơ (cửa sổ quá khứ 2W) với tham chiếu nửa cửa sổ W ∈ {16, 32, 64}."""
    out = {"ghi_chu": "khám phá sau khi xem kết quả chính — không đổi kết luận C1–C9", "ket_qua": {}}
    for spec in S.SETS:
        sym = spec["key"].split()[0]
        _d, bars, _tf, _m = RS.load(con, spec, allow_test=False)
        C = np.array([b.close for b in bars]); H = np.array([b.high for b in bars]); L = np.array([b.low for b in bars])
        atr, _adx, _p, _q = adx_di(H, L, C)
        v2, _raw, _ver = run_states(bars, sym)
        rows = {}
        for w in (16, 32, 64):
            ref = classify(C, H, L, atr, -w, w, gap_ok(bars, -w, w))
            naive = classify(C, H, L, atr, -2 * w, 0, gap_ok(bars, -2 * w, 0))
            valid = (v2 != "none") & (ref != "none")
            d_v2 = np.where(v2 == "len", 1, np.where(v2 == "xuong", -1, 0))
            d_ref = np.where(ref == "len", 1, np.where(ref == "xuong", -1, 0))
            rt, vt = valid & (d_ref != 0), valid & (d_v2 != 0)
            rows[str(w)] = {"kappa3_v2": kappa3(v2, ref), "kappa3_ngay_tho": kappa3(naive, ref),
                            "recall_v2": round(float((d_v2[rt] == d_ref[rt]).mean()), 4),
                            "sai_chieu_v2": round(float((d_ref[vt] == -d_v2[vt]).mean()), 4),
                            "trend_tham_chieu": round(float(np.isin(ref[ref != "none"], ("len", "xuong")).mean()), 4)}
            print(sym, "W", w, rows[str(w)], flush=True)
        out["ket_qua"][sym] = rows
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", default=os.path.join(ROOT, "docs", "research", "khao_sat", "kiem_dinh_trang_thai_dev.json"))
    ap.add_argument("--db", default=os.environ.get("MSL_DB_PATH") or os.path.join(ROOT, "data", "lab.sqlite"))
    ap.add_argument("--kham-pha", action="store_true", help="Chỉ chạy phần khám phá thang (ngoài khai trước)")
    args = ap.parse_args()
    t_all = time.time()
    con = sqlite3.connect("file:%s?mode=ro" % args.db.replace("\\", "/"), uri=True)
    if args.kham_pha:
        explore(con, os.path.join(ROOT, "docs", "research", "khao_sat", "kiem_dinh_trang_thai_kham_pha_dev.json"))
        return
    with open(os.path.abspath(__file__), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    meta = {"phien_ban": VERSION, "script_sha256": sha, "python": platform.python_version(), "doan_kiem_tra_tu": S.TEST_START,
            "khai_truoc": "docs/research/kiem_dinh_trang_thai.md (commit 4fffacb, sửa 2c2ed12)", "nguong": TARGETS,
            "seed_chuoi_gia": list(SEEDS), "n_boot": S.N_BOOT, "lan_chay": {}}
    res = {}
    for spec in S.SETS:
        sym = spec["key"].split()[0]
        t0 = time.time()
        _d, bars, _tf, src_meta = RS.load(con, spec, allow_test=False)
        C = np.array([b.close for b in bars]); H = np.array([b.high for b in bars]); L = np.array([b.low for b in bars])
        atr, adx, pdi, mdi = adx_di(H, L, C)
        ok_c = gap_ok(bars, -W, W)
        ok_p = gap_ok(bars, -W_PAST, 0)
        fwd_ok = gap_ok(bars, 0, W)
        ref = classify(C, H, L, atr, -W, W, ok_c)
        naive = classify(C, H, L, atr, -W_PAST, 0, ok_p)
        b_adx = np.where(~np.isfinite(adx), "none", np.where(adx >= 25, np.where(pdi > mdi, "len", "xuong"), "nhieu"))
        wk = [((b.bar_time.astimezone(RS.NY) + timedelta(hours=7)).date().isocalendar()[:2]) for b in bars]
        weeks = {w: i for i, w in enumerate(sorted(set(wk)))}
        week = np.array([weeks[w] for w in wk]); nW = len(weeks)
        M = np.random.default_rng(S.SEED + 21).multinomial(nW, np.full(nW, 1.0 / nW), size=S.N_BOOT).astype(float)

        v2, _raw, ver = run_states(bars, sym)
        r = {"v2": measures(v2, ref, C, week, nW, M, fwd_ok)}
        r["ngay_tho"] = {"kappa3": kappa3(naive, ref)}
        r["adx_di"] = {"kappa3": kappa3(b_adx, ref)}
        r["null_dich_vong"] = {str(k): kappa3(np.roll(v2, k * BARS_PER_WEEK), ref) for k in SHIFT_WEEKS}
        print("%s thật %.0f s · κ3 %s · ngây thơ %s · ADX %s · null %s" % (
            sym, time.time() - t0, r["v2"]["kappa3"], r["ngay_tho"]["kappa3"], r["adx_di"]["kappa3"],
            r["null_dich_vong"]), flush=True)
        gia = []
        for seed in SEEDS:
            t1 = time.time()
            sb = surrogate(bars, seed)
            Cs = np.array([b.close for b in sb]); Hs = np.array([b.high for b in sb]); Ls = np.array([b.low for b in sb])
            atr_s, _a, _p, _m = adx_di(Hs, Ls, Cs)
            ref_s = classify(Cs, Hs, Ls, atr_s, -W, W, ok_c)
            v2s, _raw_s, _ver = run_states(sb, sym)
            g = measures(v2s, ref_s, Cs, week, nW, M, fwd_ok)
            g.pop("ma_tran")
            gia.append(g)
            print("%s giả seed %d %.0f s · trend %.3f · κ3 %s · tiếp diễn %s" % (
                sym, seed, time.time() - t1, g["ty_le_v2"]["len"] + g["ty_le_v2"]["xuong"], g["kappa3"],
                g["tiep_dien_16"]), flush=True)
        r["chuoi_gia"] = gia
        r["nhan_qua"] = causality(bars, sym) if sym == "XAUUSD" else None
        res[sym] = r
        meta["lan_chay"][sym] = dict(src_meta, phien_ban_thuat_toan=ver, giay=round(time.time() - t0, 1))

    # C9 từ khảo sát v2 đã có
    with open(os.path.join(ROOT, "docs", "research", "khao_sat", "trang_thai_v2_dev.json"), encoding="utf-8") as fh:
        old = json.load(fh)
    c9 = {sym: old["ket_qua"][sym]["v2"]["range_giu_gia"] for sym in res}
    verdict = judge(res, c9)
    meta["giay"] = round(time.time() - t_all, 1)
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "ket_qua": res, "c9_tu_khao_sat_v2": c9, "danh_gia": verdict}, fh, ensure_ascii=False, indent=1)
    print(json.dumps(verdict, ensure_ascii=False, indent=1))


def judge(res, c9):
    T = TARGETS
    out = {}
    for sym, r in res.items():
        v = r["v2"]
        g_trend = float(np.mean([g["ty_le_v2"]["len"] + g["ty_le_v2"]["xuong"] for g in r["chuoi_gia"]]))
        g_len = float(np.mean([g["trend_do_dai_trung_vi"] for g in r["chuoi_gia"]]))
        real_trend = v["ty_le_v2"]["len"] + v["ty_le_v2"]["xuong"]
        null_mean = float(np.mean([k for k in r["null_dich_vong"].values() if k is not None]))
        ci8 = v["tiep_dien_16_ci95"]
        ci9 = c9[sym]["ci95"]
        nq = r["nhan_qua"]
        out[sym] = {
            "C1": None if nq is None else nq["nen_lech"] == 0,
            "C2": v["doi_moi_100"] <= T["C2_doi_moi_100"] and v["doan_ngan_duoi_4"] <= T["C2_doan_ngan"],
            "C3": v["kappa3"] is not None and v["kappa3"] >= T["C3_kappa"],
            "C4": (v["kappa3"] - r["ngay_tho"]["kappa3"] >= T["C4_hon_ngay_tho"]
                   and v["kappa3"] - null_mean >= T["C4_hon_null"]),
            "C5": v["sai_chieu"] <= T["C5_sai_chieu"] and v["recall_trend_dung_chieu"] >= T["C5_recall"],
            "C6": v["mat_doan_trung_vi"] <= T["C6_mat_doan"],
            "C7": (real_trend - g_trend >= T["C7_trend_hon"]
                   and v["trend_do_dai_trung_vi"] >= T["C7_do_dai"] * g_len),
            "C8": v["tiep_dien_16"] >= T["C8_tiep_dien"] and ci8 is not None and ci8[0] > 0.5,
            "C9": ci9 is not None and ci9[0] > 0,
            "so": {"trend_that": round(real_trend, 4), "trend_gia": round(g_trend, 4),
                   "do_dai_trend_that": v["trend_do_dai_trung_vi"], "do_dai_trend_gia": round(g_len, 2),
                   "null_dich_vong_tb": round(null_mean, 4)},
        }
    for sym in out:
        o = out[sym]
        o["N1"] = (o["C1"] is not False) and o["C2"]
        o["N2"] = o["C3"] and o["C4"] and o["C5"] and o["C6"]
        o["N3"] = o["C7"]
        o["N4"] = o["C8"] and o["C9"]
    return out


if __name__ == "__main__":
    main()
