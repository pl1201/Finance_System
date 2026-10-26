"""Kiểm định các kiểu order block theo bản khai trước ``docs/research/kiem_dinh_order_block.md``.

CHỈ ĐỌC database, chỉ đoạn phát triển (2018-01-01 → 2024-09-01). Bảy biến thể (§2): L1–L3 lấy từ sự kiện
``ORDER_BLOCK_*`` của ``ict_structure`` (ba bộ tham số OB), X1–X3 / B1 tự cài theo định nghĩa của LuxAlgo (chỉ đọc code
LuxAlgo để hiểu định nghĩa, không chép). Mọi vùng — thật và song sinh — đi qua cùng một vòng đời (§3): chạm lần đầu trong
96 nến, «giữ giá» như khảo sát OB cũ (+1·ATR từ mép gần trước close vượt mép xa, 32 nến), setup R mô tả (đích 2R, chưa trừ
phí). Chuẩn (§4): 5 vùng song sinh cùng khoảng cách / bề rộng theo ATR, cùng giờ New York, cùng nửa dev, ±13 tuần. Chọn ở
đoạn A, xác nhận ở đoạn B (§5).

Ví dụ (PowerShell, từ thư mục market-structure-lab)::

    .\\.venv\\Scripts\\python.exe research\\kiem_dinh_order_block.py
    .\\.venv\\Scripts\\python.exe research\\kiem_dinh_order_block.py --thu      # chạy thử 2 tháng, chỉ in số vùng
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
from datetime import datetime, timedelta, timezone

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import ict_indicator_survey as S  # noqa: E402  (đoạn dev, seed, số lượt bootstrap)
import khao_sat_ob_ote as OB  # noqa: E402  (bootstrap khối tuần, CI)
import regime_survey as RS  # noqa: E402
from core.algorithms.ict_structure import LEGACY_0_9, IctStructureAlgorithm  # noqa: E402
from core.engine import run_algorithm  # noqa: E402

VERSION = "kiem-dinh-order-block-v1.0"
SPLIT = datetime(2022, 1, 1, tzinfo=timezone.utc)      # đoạn A < SPLIT ≤ đoạn B (theo nến xác nhận)
GAP = timedelta(hours=3)
TOUCH_MAX, HOLD_W = 96, 32
N_TWIN, TWIN_MIN_SEP, TWIN_SPAN = 5, 96, timedelta(weeks=13)
STOP_PAD, R_TARGET = 0.1, 2.0
MIN_N = 200
BLOCK_WEEKS = 4
VARIANTS = ("L1", "L2", "L3", "X1", "X2", "X3", "B1")
LAB = {"L1": {}, "L2": {"ob_bien_the": "nen_cuoi_rau"}, "L3": {"ob_neo": "displacement"}}
TEN = {"L1": "Lab OB-T neo shift (mặc định)", "L2": "Lab OB-R neo shift", "L3": "Lab OB-T neo displacement",
       "X1": "Nến cực trị, pivot 10", "X2": "Nến cực trị, pivot 5, lọc nến ≥ 2·ATR", "X3": "Nến cực trị, swing 3 nến",
       "B1": "Breaker từ X1"}


# ------------------------------------------------------------------ dữ liệu một mã

class Data:
    def __init__(self, bars, atr):
        self.N = len(bars)
        self.O = np.array([b.open for b in bars]); self.H = np.array([b.high for b in bars])
        self.L = np.array([b.low for b in bars]); self.C = np.array([b.close for b in bars])
        self.atr = np.array([np.nan if a is None else float(a) for a in atr])
        self.T = np.array([int(b.bar_time.timestamp()) for b in bars])
        self.hour = np.array([b.bar_time.astimezone(RS.NY).hour for b in bars])
        self.part = np.array([0 if b.bar_time < SPLIT else 1 for b in bars])
        big = np.zeros(self.N, dtype=int)                 # big[i] = 1: khoảng trống > 3 giờ ngay trước nến i
        for i in range(1, self.N):
            big[i] = bars[i].bar_time - bars[i - 1].bar_time > GAP
        self.gapc = np.cumsum(big)
        wk = [(b.bar_time.astimezone(RS.NY) + timedelta(hours=7)).date().isocalendar()[:2] for b in bars]
        ids = {w: i for i, w in enumerate(sorted(set(wk)))}
        self.week = np.array([ids[w] for w in wk])
        self.by_hour = {h: np.nonzero(self.hour == h)[0] for h in range(24)}

    def no_gap(self, a, b):
        """Không có khoảng trống > 3 giờ trong (a, b]."""
        return self.gapc[b] == self.gapc[a]


# ------------------------------------------------------------------ biến thể

def lab_zones(events):
    """L1–L3: vùng của ``ORDER_BLOCK_*`` (hiệu lực từ nến xác nhận)."""
    out = []
    for e in events:
        if e.structure_type in ("ORDER_BLOCK_UP", "ORDER_BLOCK_DOWN"):
            x = e.details
            out.append((1 if x["chieu"] == "up" else -1, float(x["lo"]), float(x["hi"]), int(e.confirmed_bar_index)))
    return out


def pivots(d, X, n, high):
    """Pivot đối xứng chặt n/n (duy nhất là cực trị của cửa sổ), cửa sổ không vắt khoảng trống; biết ở p + n."""
    out = np.zeros(d.N, dtype=bool)
    for p in range(n, d.N - n):
        if not d.no_gap(p - n, p + n):
            continue
        w = X[p - n:p + n + 1]
        v = X[p]
        out[p] = (v == w.max() if high else v == w.min()) and int((w == v).sum()) == 1
    return out


def extreme_zones(d, n, skip_big, full=False):
    """X1–X3: close đầu tiên vượt pivot gần nhất chưa bị phá → nến cực trị trong [pivot, nến phá − 1] (bỏ nến biên độ
    ≥ 2·ATR nếu ``skip_big``), vùng = [low, high], hiệu lực từ nến phá. Pivot mới thay pivot cũ (swing gần nhất).
    ``full``: thêm (nến pivot p, nến OB i) vào mỗi bộ — cho kiểm định theo ngữ cảnh."""
    ph, pl = pivots(d, d.H, n, True), pivots(d, d.L, n, False)
    H, L, C, A = d.H, d.L, d.C, d.atr
    out, top, bot = [], None, None
    for t in range(d.N):
        p = t - n
        if p >= 0 and ph[p]:
            top = [p, H[p], False]
        if p >= 0 and pl[p]:
            bot = [p, L[p], False]
        for sw, up in ((top, True), (bot, False)):
            if sw is None or sw[2] or not ((C[t] > sw[1]) if up else (C[t] < sw[1])):
                continue
            sw[2] = True
            if not d.no_gap(sw[0], t - 1):                  # cửa sổ tìm nến cực trị [p, t − 1]
                continue
            idx = [i for i in range(sw[0], t) if not (skip_big and np.isfinite(A[i]) and H[i] - L[i] >= 2 * A[i])]
            if not idx:
                continue
            i = min(idx, key=lambda k: L[k]) if up else max(idx, key=lambda k: H[k])
            if H[i] > L[i]:
                z = (1 if up else -1, float(L[i]), float(H[i]), t)
                out.append(z + (sw[0], i) if full else z)
    return out


def breaker_zones(d, x1):
    """B1: OB X1 mà vòng đời §3 kết thúc bằng hỏng (close qua mép xa, ở nến chạm hoặc trong 32 nến sau) → cùng vùng,
    chiều ngược, hiệu lực từ nến hỏng."""
    out = []
    for dr, lo, hi, c in x1:
        tau = first_touch(d, dr, lo, hi, c) if full_window(d, c) else None
        if tau is not None:
            g, at = hold(d, dr, lo, hi, tau, with_bar=True)
            if g == 0.0:
                out.append((-dr, lo, hi, at))
    return out


# ------------------------------------------------------------------ vòng đời chung (§3)

def first_touch(d, dr, lo, hi, c):
    a, b = c + 1, min(c + TOUCH_MAX, d.N - 1)
    if a > b:
        return None
    hit = (d.L[a:b + 1] <= hi) if dr > 0 else (d.H[a:b + 1] >= lo)
    k = int(np.argmax(hit))
    return a + k if hit[k] else None


def hold(d, dr, lo, hi, tau, with_bar=False):
    """1 = đi +1·ATR[τ] từ mép gần trước khi close vượt mép xa; 0 = ngược lại; NaN = chưa rõ / khoảng trống (như
    ``khao_sat_ob_ote.hold``: nến chạm close qua mép xa = 0; từ nến sau, đích xét trước close)."""
    def out(v, t):
        return (v, t) if with_bar else v
    a = d.atr[tau]
    if not (np.isfinite(a) and a > 0):
        return out(np.nan, None)
    up = dr > 0
    if (d.C[tau] < lo) if up else (d.C[tau] > hi):
        return out(0.0, tau)
    target = hi + a if up else lo - a
    for t in range(tau + 1, min(tau + HOLD_W, d.N - 1) + 1):
        if not d.no_gap(tau, t):
            return out(np.nan, None)
        if (d.H[t] >= target) if up else (d.L[t] <= target):
            return out(1.0, t)
        if (d.C[t] < lo) if up else (d.C[t] > hi):
            return out(0.0, t)
    return out(np.nan, None)


def setup_r(d, dr, lo, hi, tau):
    """Vào ở mép gần khi chạm, dừng mép xa ± 0,1·ATR, đích 2R, 32 nến; cùng nến chạm dừng và đích → thua; hết giờ → R
    theo close; chưa trừ phí. NaN khi thiếu ATR / cửa sổ chưa đủ / vắt khoảng trống."""
    a = d.atr[tau]
    if not (np.isfinite(a) and a > 0) or tau + HOLD_W > d.N - 1:
        return np.nan
    up = dr > 0
    stop = lo - STOP_PAD * a if up else hi + STOP_PAD * a
    entry = min(hi, d.O[tau]) if up else max(lo, d.O[tau])      # lệnh chờ ở mép gần; mở lọt vào vùng → khớp ở giá mở
    if (entry <= stop) if up else (entry >= stop):              # mở vượt luôn mức dừng → bỏ
        return np.nan
    risk = abs(entry - stop)
    target = entry + R_TARGET * risk * dr
    if (d.L[tau] <= stop) if up else (d.H[tau] >= stop):
        return -1.0
    for t in range(tau + 1, tau + HOLD_W + 1):
        if not d.no_gap(tau, t):
            return np.nan
        if (d.L[t] <= stop) if up else (d.H[t] >= stop):
            return -1.0
        if (d.H[t] >= target) if up else (d.L[t] <= target):
            return R_TARGET
    return dr * (d.C[tau + HOLD_W] - entry) / risk


def full_window(d, c):
    """Còn đủ nến cho cả vòng đời (96 nến chờ chạm + 32 nến kết cục) — như điều kiện của vùng song sinh."""
    return c + TOUCH_MAX + HOLD_W < d.N


def life(d, dr, lo, hi, c):
    """(nến chạm, giữ giá, R) — nến chạm None khi không chạm trong 96 nến."""
    tau = first_touch(d, dr, lo, hi, c)
    if tau is None:
        return None, np.nan, np.nan
    return tau, hold(d, dr, lo, hi, tau), setup_r(d, dr, lo, hi, tau)


def twins(d, dr, lo, hi, c, rng, accept=None):
    """§4: 5 vùng cùng khoảng cách k và bề rộng w (theo ATR), cùng giờ NY, cùng nửa dev, ±13 tuần, cách c ≥ 96 nến.
    ``accept(t′, lo′, hi′)``: chỉ nhận song sinh thỏa điều kiện (song sinh khớp ngữ cảnh) — duyệt ứng viên theo thứ tự
    ngẫu nhiên tới khi đủ 5; None = cách chọn gốc."""
    A = d.atr[c]
    if not (np.isfinite(A) and A > 0):
        return []
    near = hi if dr > 0 else lo
    k, w = dr * (d.C[c] - near) / A, (hi - lo) / A
    idx = d.by_hour[d.hour[c]]
    span = int(TWIN_SPAN.total_seconds())
    T = d.T[idx]
    cand = idx[np.searchsorted(T, d.T[c] - span):np.searchsorted(T, d.T[c] + span, side="right")]
    cand = cand[(d.part[cand] == d.part[c]) & (np.abs(cand - c) >= TWIN_MIN_SEP) & np.isfinite(d.atr[cand])
                & np.array([full_window(d, int(t)) for t in cand], dtype=bool)]
    if not cand.size:
        return []
    out = []
    pick = rng.choice(cand, size=min(N_TWIN, cand.size), replace=False) if accept is None else rng.permutation(cand)
    for t in pick:
        At = d.atr[t]
        n2 = d.C[t] - dr * k * At
        lo2, hi2 = (n2 - w * At, n2) if dr > 0 else (n2, n2 + w * At)
        if accept is not None and not accept(int(t), lo2, hi2):
            continue
        out.append(life(d, dr, lo2, hi2, int(t)))
        if len(out) == N_TWIN:
            break
    return out


# ------------------------------------------------------------------ đo một biến thể trên một mã

def measure(d, zones, rng):
    rows = []
    for dr, lo, hi, c in zones:
        if not (hi > lo) or not np.isfinite(d.atr[c]) or d.atr[c] <= 0 or not full_window(d, c):
            continue
        tau, g, r = life(d, dr, lo, hi, c)
        tw = twins(d, dr, lo, hi, c, rng)
        gt = [x[1] for x in tw if np.isfinite(x[1])]
        rt = [x[2] for x in tw if np.isfinite(x[2])]
        rows.append({"part": int(d.part[c]), "tau": tau, "g": g, "r": r, "w": (hi - lo) / d.atr[c],
                     "gt": float(np.mean(gt)) if gt else np.nan, "rt": float(np.mean(rt)) if rt else np.nan,
                     "touch_t": float(np.mean([x[0] is not None for x in tw])) if tw else np.nan})
    return rows


def summarize(d, rows, part):
    rs = [x for x in rows if x["part"] == part]
    touched = [x for x in rs if x["tau"] is not None]
    pg = [x for x in touched if np.isfinite(x["g"]) and np.isfinite(x["gt"])]
    pr = [x for x in touched if np.isfinite(x["r"]) and np.isfinite(x["rt"])]

    def boot(sel, a, b):
        if not sel:
            return None, None
        # khối BLOCK_WEEKS tuần theo nến chạm, rút trên đúng các khối có trong mẫu (song sinh lấy trong ±13 tuần nên kết
        # cục phụ thuộc nhau quá một tuần — Sổ sửa 1)
        ids, blk = np.unique([d.week[x["tau"]] // BLOCK_WEEKS for x in sel], return_inverse=True)
        M = np.random.default_rng(S.SEED + 43).multinomial(ids.size, np.full(ids.size, 1.0 / ids.size),
                                                          size=S.N_BOOT).astype(float)
        num = np.array([x[a] - x[b] for x in sel])
        bs, est = OB.week_ratio_boot(M, blk, ids.size, num, np.ones(num.size))
        return round(float(est), 4), OB.ci(bs)

    dg, dg_ci = boot(pg, "g", "gt")
    dr_, dr_ci = boot(pr, "r", "rt")
    res_g = [x["g"] for x in touched if np.isfinite(x["g"])]
    return {
        "so_vung": len(rs), "ty_le_cham": round(len(touched) / len(rs), 4) if rs else None,
        "ty_le_cham_song_sinh": round(float(np.nanmean([x["touch_t"] for x in rs])), 4) if rs else None,
        "n_giu_co_ket_cuc": len(res_g), "giu_that": round(float(np.mean(res_g)), 4) if res_g else None,
        "n_cap": len(pg), "giu_song_sinh": round(float(np.mean([x["gt"] for x in pg])), 4) if pg else None,
        "delta_giu": dg, "delta_giu_ci95": dg_ci,
        "n_cap_r": len(pr), "r_that": round(float(np.mean([x["r"] for x in pr])), 4) if pr else None,
        "r_song_sinh": round(float(np.mean([x["rt"] for x in pr])), 4) if pr else None,
        "delta_r": dr_, "delta_r_ci95": dr_ci,
        "be_rong_trung_vi_atr": round(float(np.median([x["w"] for x in rs])), 3) if rs else None,
    }


def zones_for(d, runs):
    x1 = extreme_zones(d, 10, False)
    return {"L1": lab_zones(runs["L1"]), "L2": lab_zones(runs["L2"]), "L3": lab_zones(runs["L3"]), "X1": x1,
            "X2": extreme_zones(d, 5, True), "X3": extreme_zones(d, 1, False), "B1": breaker_zones(d, x1)}


# ------------------------------------------------------------------ chọn / xác nhận (§5)

def judge(res):
    syms = list(res)
    rows = []
    for v in VARIANTS:
        a = [res[s][v]["A"] for s in syms]
        ok = all(x["delta_giu"] is not None and x["delta_giu_ci95"] and x["delta_giu_ci95"][0] > 0
                 and x["n_cap"] >= MIN_N for x in a)
        mean = float(np.mean([x["delta_giu"] for x in a])) if all(x["delta_giu"] is not None for x in a) else None
        rows.append({"bien_the": v, "hop_le_A": ok, "delta_tb_A": None if mean is None else round(mean, 4)})
    valid = [r for r in rows if r["hop_le_A"]]
    ranked = sorted((r for r in rows if r["delta_tb_A"] is not None), key=lambda r: -r["delta_tb_A"])
    pick = max(valid, key=lambda r: r["delta_tb_A"])["bien_the"] if valid else None
    out = {"bang_A": rows, "chon": pick, "it_te_nhat": ranked[0]["bien_the"] if (not valid and ranked) else None}
    if pick:
        b = [res[s][pick]["B"] for s in syms]
        out["xac_nhan_B"] = all(x["delta_giu_ci95"] and x["delta_giu_ci95"][0] > 0 for x in b)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", default=os.path.join(ROOT, "docs", "research", "khao_sat", "kiem_dinh_order_block_dev.json"))
    ap.add_argument("--db", default=os.environ.get("MSL_DB_PATH") or os.path.join(ROOT, "data", "lab.sqlite"))
    ap.add_argument("--thu", action="store_true", help="Chạy thử 2 tháng đầu, chỉ in số vùng (không đo, không ghi)")
    args = ap.parse_args()
    t_all = time.time()
    con = sqlite3.connect("file:%s?mode=ro" % args.db.replace("\\", "/"), uri=True)
    with open(os.path.abspath(__file__), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    meta = {"phien_ban": VERSION, "script_sha256": sha, "python": platform.python_version(),
            "khai_truoc": "docs/research/kiem_dinh_order_block.md (commit 2c55945)", "doan_kiem_tra_tu": S.TEST_START,
            "chia_A_B": SPLIT.date().isoformat(), "n_boot": S.N_BOOT, "lan_chay": {}}
    res = {}
    for spec in S.SETS:
        sym = spec["key"].split()[0]
        if args.thu:
            spec = dict(spec, end="2018-03-01")
        t0 = time.time()
        _d, bars, tf, src_meta = RS.load(con, spec, allow_test=False)
        runs, atr, ver = {}, None, None
        for v, p in LAB.items():
            algo = IctStructureAlgorithm(timeframe=tf, session_calendar=RS.CAL[sym], **{**LEGACY_0_9, **p})
            r = run_algorithm(bars, algo)
            runs[v], ver = r.events, algo.version
            if atr is None:
                atr = [x.get("atr") for x in r.timeline]
        d = Data(bars, atr)
        zones = zones_for(d, runs)
        print("%s: %s · %.0f s" % (sym, {v: len(z) for v, z in zones.items()}, time.time() - t0), flush=True)
        if args.thu:
            continue
        rng = np.random.default_rng(S.SEED + 41)
        res[sym] = {}
        for v in VARIANTS:
            rows = measure(d, zones[v], rng)
            res[sym][v] = {"A": summarize(d, rows, 0), "B": summarize(d, rows, 1)}
            a = res[sym][v]["A"]
            print("  %s %-38s A: %d vùng · Δ giữ %s %s · n cặp %d" % (v, TEN[v], a["so_vung"], a["delta_giu"],
                                                                     a["delta_giu_ci95"], a["n_cap"]), flush=True)
        meta["lan_chay"][sym] = dict(src_meta, phien_ban_thuat_toan=ver, giay=round(time.time() - t0, 1))
    if args.thu:
        return
    verdict = judge(res)
    meta["giay"] = round(time.time() - t_all, 1)
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "ten_bien_the": TEN, "ket_qua": res, "danh_gia": verdict}, fh, ensure_ascii=False,
                  indent=1)
    print(json.dumps(verdict, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
