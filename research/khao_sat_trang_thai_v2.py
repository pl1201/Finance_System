"""Khảo sát trạng thái v1 / v2 của lớp nhận diện (plan_nhan_dien_v2.md §5) — CHỈ ĐỌC database, chỉ dev.

Chạy ``ict_structure`` ≥ 0.9.0 với ``nd_kieu`` = v1 / v2 (và các cấu hình v2 trong ``CAU_HINH``) trên XAUUSD / EURUSD
M15 2018 – 08/2024; đo theo §5 của plan, bằng chỉ báo tính độc lập ở đây (không đọc lại từ lõi):

* tỷ lệ thời gian mỗi trạng thái, cờ nén, số lần đổi / 100 nến, độ dài trung vị mỗi loại đoạn;
* **bắt nhịp một chiều rõ**: trong các nến có |C_t − C_{t−32}| ≥ 3·ATR và ADX(14) > 25, tỷ lệ gọi trend đúng chiều;
* **trend có ADX > 20**; **sai chiều so với tham chiếu nhìn lại**: C_{t+16} − C_{t−16} ngược chiều trend quá 2·ATR
  (chỉ để chấm, nhìn tương lai có chủ ý);
* **range giữ giá**: 4 nến sau còn đóng cửa trong biên range, trừ kỳ vọng của một hộp BẤT KỲ cùng bề rộng (ATR) và
  cùng vị trí close trong hộp (hộp Donchian 24 nến của mọi nến, chia nhóm bề rộng × vị trí); CI 95% bootstrap khối
  tuần (tuần giao dịch NY). Kèm cùng phép đo cho nến nhiễu (hộp Donchian của chính nó) để đối chiếu;
* **ổn định**: κ của nhãn khi đổi ngưỡng ± 20% so với mặc định.

v1.2: đoạn / số lần đổi tính theo ``RS.segments`` (cắt ở nến chưa có trạng thái, như khảo sát regime) — trước đó nối
đoạn qua giai đoạn khởi động sau khoảng trống; kiểm hằng số đổi có hiệu lực. Nhãn không đổi.

v1.1 (sau khi xem số lần đầu, ghi lý do): «range giữ giá» chỉ tính nến close còn trong hộp range — hộp đối chứng
Donchian luôn chứa close hiện tại, nên so cả nến đã ra ngoài (chưa đủ 2 close để phá) là không công bằng.

Khai báo trước (plan §5): v2 đạt khi bắt nhịp rõ ≥ 85%, trend có ADX > 20 ≥ 80%, sai chiều < 5%, độ dài trung vị range
≥ 12 nến, range giữ giá cao hơn đối chứng (CI không chứa 0), đổi ≤ 10 / 100 nến, κ ± 20% ≥ 0,7. Mọi cấu hình đã thử
ghi trong ``meta.so_thu`` (N).

Ví dụ::

    .\\.venv\\Scripts\\python.exe research\\khao_sat_trang_thai_v2.py --json docs\\research\\khao_sat\\trang_thai_v2_dev.json
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
from datetime import timedelta

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import ict_indicator_survey as S  # noqa: E402  (đoạn dev, seed)
import khao_sat_ob_ote as OB  # noqa: E402  (bootstrap khối tuần, CI)
import regime_survey as RS  # noqa: E402
from core.algorithms.ict_structure import IctStructureAlgorithm  # noqa: E402
from core.components import market_state_v2 as V2  # noqa: E402
from core.engine import run_algorithm  # noqa: E402

SURVEY_VERSION = "trang-thai-v2-survey-v1.2"
TRENDS = ("trend_len", "trend_xuong")
#: Cấu hình v2 thử (tham số thuật toán, hằng số thành phần) — mặc định trước, ± 20% để đo ổn định.
CAU_HINH = {
    "v2": ({}, {}),
    "v2_er+20": ({"nd_er_vao": 0.216, "nd_er_ra": 0.12}, {}),
    "v2_er-20": ({"nd_er_vao": 0.144, "nd_er_ra": 0.08}, {}),
    "v2_hop+20": ({}, {"BOX_WIDTH_ATR": (1.5, 5.4), "BOX_HOURS": 7.2}),
    "v2_hop-20": ({}, {"BOX_WIDTH_ATR": (1.5, 3.6), "BOX_HOURS": 4.8}),
    "v2_thoat+20": ({}, {"EXIT_HOURS": 4.8}),
    "v2_thoat-20": ({}, {"EXIT_HOURS": 3.2}),
}
W_BINS = (2.0, 3.0, 4.0, 5.0, 6.0, 8.0)           # nhóm bề rộng hộp (ATR) cho kỳ vọng «hộp bất kỳ»
TARGETS = {"bat_nhip_ro": 0.85, "trend_adx20": 0.80, "sai_chieu": 0.05, "range_trung_vi_nen": 12, "doi_moi_100": 10,
           "kappa": 0.7}


def wilder(x, n):
    out, a = np.full(x.size, np.nan), np.nan
    for i, v in enumerate(x):
        if np.isnan(v):
            continue
        a = v if np.isnan(a) else a + (v - a) / n
        out[i] = a
    return out


def reference(bars):
    """Chỉ báo độc lập (không đọc từ lõi): ATR 14, ADX 14, động lượng 8 giờ, tham chiếu nhìn lại ±16 nến, tuần NY."""
    H = np.array([b.high for b in bars]); L = np.array([b.low for b in bars]); C = np.array([b.close for b in bars])
    pc = np.r_[np.nan, C[:-1]]
    tr = np.nanmax(np.vstack([H - L, np.abs(H - pc), np.abs(L - pc)]), axis=0)
    up, dn = np.r_[np.nan, np.diff(H)], np.r_[np.nan, -np.diff(L)]
    pdm = np.where((up > dn) & (up > 0), up, 0.0); mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    atr = wilder(tr, 14)
    with np.errstate(invalid="ignore", divide="ignore"):
        pdi, mdi = 100 * wilder(pdm, 14) / atr, 100 * wilder(mdm, 14) / atr
        adx = wilder(100 * np.abs(pdi - mdi) / (pdi + mdi), 14)
    c = pd.Series(C)
    move8 = ((c - c.shift(32)) / atr).values
    look = ((c.shift(-16) - c.shift(16)) / atr).values
    wk = [((b.bar_time.astimezone(RS.NY) + timedelta(hours=7)).date().isocalendar()[:2]) for b in bars]
    weeks = {w: i for i, w in enumerate(sorted(set(wk)))}
    return {"C": C, "H": H, "L": L, "atr": atr, "adx": adx, "move8": move8, "look": look,
            "week": np.array([weeks[w] for w in wk]), "nW": len(weeks)}


def labels(bars, sym, params, consts):
    saved = {k: getattr(V2, k) for k in consts}
    try:
        for k, v in consts.items():
            setattr(V2, k, v)
        algo = IctStructureAlgorithm(timeframe="M15", session_calendar=RS.CAL[sym], **params)
        st = algo._nd.state                                       # hằng số đổi phải có hiệu lực thật (không đo nhầm mặc định)
        for k, v in consts.items():
            if k.endswith("_HOURS") and st.windows()[{"BOX_HOURS": "hop", "EXIT_HOURS": "thoat_trend"}[k]] != round(v * 4):
                raise RuntimeError("Hằng số %s không có hiệu lực" % k)
        r = run_algorithm(bars, algo)
    finally:
        for k, v in saved.items():
            setattr(V2, k, v)
    tl = r.timeline
    return (np.array([p.get("nd_trang_thai") or "none" for p in tl], dtype=object),
            np.array([p.get("nd_range_hi") if p.get("nd_range_hi") is not None else np.nan for p in tl], float),
            np.array([p.get("nd_range_lo") if p.get("nd_range_lo") is not None else np.nan for p in tl], float),
            np.array([bool(p.get("nd_nen")) for p in tl]), algo.version)


def runs(lab, ok):
    """(nhãn, độ dài) của các đoạn liên tiếp — cắt ở nến chưa có trạng thái / ngoài ``ok`` (``RS.segments``)."""
    names = sorted(set(lab[ok]))
    code = np.where(ok, np.array([names.index(x) if x in names else -1 for x in lab]), -1)
    _idx, lens, codes = RS.segments(code)
    return [(names[c], int(n)) for c, n in zip(codes, lens)]


def evaluate(lab, rhi, rlo, sqz, ref, M):
    ok = (lab != "none") & np.isfinite(ref["adx"]) & np.isfinite(ref["move8"])
    n = int(ok.sum())
    tr = np.isin(lab, TRENDS)
    d = np.where(lab == "trend_len", 1, np.where(lab == "trend_xuong", -1, 0))
    clear = ok & (np.abs(ref["move8"]) >= 3) & (ref["adx"] > 25)
    caught = d[clear] == np.sign(ref["move8"][clear])
    lk = ok & tr & np.isfinite(ref["look"])
    wrong = (d[lk] * ref["look"][lk]) < -2
    ep = runs(lab, ok)
    changes = int(sum(1 for i in range(1, lab.size) if ok[i] and ok[i - 1] and lab[i] != lab[i - 1]))
    med = {s: float(np.median([k for name, k in ep if name == s])) for s in set(lab[ok])}
    # range giữ giá: 4 nến sau còn đóng cửa trong biên, so với kỳ vọng của hộp bất kỳ cùng bề rộng × vị trí
    C, H, L, atr = ref["C"], ref["H"], ref["L"], ref["atr"]
    hi24 = pd.Series(H).rolling(24).max().values; lo24 = pd.Series(L).rolling(24).min().values
    fut_hi = pd.Series(C[::-1]).rolling(4).max().values[::-1]; fut_lo = pd.Series(C[::-1]).rolling(4).min().values[::-1]
    fut_hi, fut_lo = np.r_[fut_hi[1:], np.nan], np.r_[fut_lo[1:], np.nan]

    def bucket(hi, lo):
        with np.errstate(invalid="ignore", divide="ignore"):
            w, pos = (hi - lo) / atr, (C - lo) / (hi - lo)
        return np.digitize(w, W_BINS) * 3 + np.clip(np.floor(pos * 3), 0, 2).astype(int, copy=False)

    base = ok & np.isfinite(hi24) & np.isfinite(fut_hi) & np.isfinite(atr)
    kb = bucket(hi24, lo24)
    keep_all = ((fut_hi <= hi24) & (fut_lo >= lo24)).astype(float)
    rate = {b: keep_all[base & (kb == b)].mean() for b in np.unique(kb[base])}
    with np.errstate(invalid="ignore"):                # chỉ nến close còn trong hộp (hộp đối chứng luôn chứa close)
        rng = ok & (lab == "range") & np.isfinite(rhi) & np.isfinite(fut_hi) & (C <= rhi) & (C >= rlo)
    chop = base & (lab == "nhieu")
    kr = bucket(rhi, rlo)
    rng &= np.isin(kr, list(rate))
    diff_r = ((fut_hi <= rhi) & (fut_lo >= rlo))[rng].astype(float) - np.array([rate[b] for b in kr[rng]])
    diff_c = keep_all[chop] - np.array([rate[b] for b in kb[chop]])
    bs_r, est_r = OB.week_ratio_boot(M, ref["week"][rng], ref["nW"], diff_r, np.ones(diff_r.size))
    bs_c, est_c = OB.week_ratio_boot(M, ref["week"][chop], ref["nW"], diff_c, np.ones(diff_c.size))
    return {
        "n": n, "ty_le": {s: round(float((lab[ok] == s).mean()), 4) for s in sorted(set(lab[ok]))},
        "co_nen": round(float(sqz[ok].mean()), 4), "doi_moi_100": round(100 * changes / n, 2),
        "do_dai_trung_vi_nen": med, "bat_nhip_ro": round(float(caught.mean()), 4), "n_nhip_ro": int(clear.sum()),
        "trend_adx20": round(float((ref["adx"][ok & tr] > 20).mean()), 4) if tr.any() else None,
        "sai_chieu": round(float(wrong.mean()), 4) if lk.any() else None,
        "range_giu_gia": {"range_tru_ky_vong": round(float(est_r), 4), "ci95": OB.ci(bs_r),
                          "nhieu_tru_ky_vong": round(float(est_c), 4), "ci95_nhieu": OB.ci(bs_c)},
    }


def kappa(a, b, ok):
    a, b = a[ok], b[ok]
    cats = sorted(set(a) | set(b))
    po = float((a == b).mean())
    pe = sum(float((a == c).mean()) * float((b == c).mean()) for c in cats)
    return round((po - pe) / (1 - pe), 4) if pe < 1 else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", default=os.path.join(ROOT, "docs", "research", "khao_sat", "trang_thai_v2_dev.json"))
    ap.add_argument("--db", default=os.environ.get("MSL_DB_PATH") or os.path.join(ROOT, "data", "lab.sqlite"))
    ap.add_argument("--ma", default="XAUUSD,EURUSD")
    ap.add_argument("--nhanh", action="store_true", help="Chỉ v1 / v2 mặc định, ít bootstrap — không dùng để kết luận")
    args = ap.parse_args()
    t_all = time.time()
    n_boot = 200 if args.nhanh else S.N_BOOT
    con = sqlite3.connect("file:%s?mode=ro" % args.db.replace("\\", "/"), uri=True)
    with open(os.path.abspath(__file__), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    configs = {"v1": ({"nd_kieu": "v1"}, {}), **({"v2": CAU_HINH["v2"]} if args.nhanh else CAU_HINH)}
    meta = {"phien_ban": SURVEY_VERSION, "script_sha256": sha, "python": platform.python_version(),
            "doan_kiem_tra_tu": S.TEST_START, "seed": S.SEED, "chay_nhanh": bool(args.nhanh), "n_boot": n_boot,
            "muc_tieu": TARGETS, "so_thu": {k: {"tham_so": p, "hang_so": {kk: list(vv) if isinstance(vv, tuple) else vv
                                                                          for kk, vv in c.items()}}
                                           for k, (p, c) in configs.items()}, "lan_chay": {}}
    res = {}
    wanted = [s.strip() for s in args.ma.split(",") if s.strip()]
    for spec in S.SETS:
        sym = spec["key"].split()[0]
        if sym not in wanted:
            continue
        _d, bars, _tf, src_meta = RS.load(con, spec, allow_test=False)
        ref = reference(bars)
        M = np.random.default_rng(S.SEED + 11).multinomial(ref["nW"], np.full(ref["nW"], 1.0 / ref["nW"]),
                                                             size=n_boot).astype(float)
        res[sym], labs = {}, {}
        for name, (params, consts) in configs.items():
            t0 = time.time()
            lab, rhi, rlo, sqz, ver = labels(bars, sym, params, consts)
            labs[name] = lab
            res[sym][name] = evaluate(lab, rhi, rlo, sqz, ref, M)
            print("%s %-10s %.0f s · %s" % (sym, name, time.time() - t0, json.dumps(res[sym][name], ensure_ascii=False)),
                  flush=True)
        ok = labs["v2"] != "none"
        res[sym]["kappa_so_v2"] = {k: kappa(labs["v2"], v, ok & (v != "none")) for k, v in labs.items() if k != "v2"}
        meta["lan_chay"][sym] = dict(src_meta, nen=len(bars), phien_ban_thuat_toan=ver)
    meta["giay"] = round(time.time() - t_all, 1)
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "ket_qua": res}, fh, ensure_ascii=False, indent=1)
    for sym, r in res.items():
        print(sym, "κ so với v2:", r["kappa_so_v2"])


if __name__ == "__main__":
    main()
