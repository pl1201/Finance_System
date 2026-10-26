"""Khảo sát xác suất chạm theo loại mức: PDH / PDL so với vùng ICT và biên range (plan_ket_hop_ict_indicator.md §5
bước 2; plan_nhan_dien_trang_thai.md bước 2) — CHỈ ĐỌC database.

Chạy ``ict_structure`` ≥ 0.8.0 (lớp nhận diện bật) trên dev (2018 – 08/2024, XAUUSD / EURUSD M15) và ghi lại MỌI dự
báo chạm đã có kết cục mà lõi tự chấm (``PriceBand._grade``, cùng phép thử ``price_band.touched``): loại mức, tầm, p, p0
(B0), chạm hay không, khoảng cách theo ATR, tuần giao dịch. Không tính lại gì ngoài lõi — số đếm và tỷ lệ chạm của mỗi
(tầm, loại mức) được đối chiếu với ``run_stats`` của chính lần chạy.

* **Mức** (lõi, bước 13): vùng thanh khoản còn nguyên gần nhất mỗi phía (``vung_tren`` / ``vung_duoi``), PDH / PDL
  còn nguyên ở đúng phía giá (``pdh`` / ``pdl``, 0.8.0), biên range khi đang range (``range_tren`` / ``range_duoi``).
* **Kỳ vọng** = p của lõi = tỷ lệ mẫu biên (cùng giờ NY, theo ATR) ≥ khoảng cách hiện tại, tức xác suất chạm một mức
  BẤT KỲ đặt đúng khoảng cách đó. **Chênh** = tỷ lệ chạm thật − kỳ vọng trung bình: > 0 → loại mức này «hút» giá hơn
  một mức bất kỳ. CI 95% bootstrap khối tuần (tuần ISO của ngày giao dịch NY, mốc 17:00 — như các khảo sát trước).
* Kèm: Brier so với B0 (mẫu chung mọi giờ), theo khoảng cách (``KC_BINS`` của khảo sát v1 phần C), 10 nhóm hiệu chuẩn
  (như lõi); PDH / PDL tách «trùng vùng gần nhất» (vùng gần nhất CHÍNH là PDH / PDL) và «không trùng».

Khai báo trước (không sửa sau khi xem kết quả; sửa thì đổi ``SURVEY_VERSION`` và ghi lý do):

* Quy tắc quyết định: chỉ thêm hiệu chỉnh riêng cho PDH / PDL vào lõi khi, ở CẢ HAI mã và ít nhất một tầm, |chênh| ≥
  ``MIN_EFFECT`` = 1 điểm % VÀ CI 95% không chứa 0. Không thì giữ mô hình khoảng cách (PDH / PDL như mức bất kỳ).
* Dự báo ở các nến liền nhau chồng lấn kết cục — chỉ CI khối tuần được dùng để kết luận, không dùng n thô. Khối = tuần
  của nến DỰ BÁO. Chạy thiếu mã (``--ma``) hoặc ``--nhanh`` → không dùng để kết luận.

v1.1 (trước khi viết kết luận cuối): khối tuần đổi từ tuần UTC của nến kết cục sang tuần giao dịch NY của nến dự báo
cho khớp các khảo sát khác — chỉ CI đổi, ước lượng điểm giữ nguyên.

Ví dụ (PowerShell, từ thư mục market-structure-lab)::

    .\\.venv\\Scripts\\python.exe research\\khao_sat_pdh_pdl.py --json docs\\research\\khao_sat\\pdh_pdl_dev.json
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
from array import array
from datetime import timedelta

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import ict_indicator_survey as S  # noqa: E402  (đoạn dev, seed, số lần bootstrap, KC_BINS)
import khao_sat_ob_ote as OB  # noqa: E402  (tỷ lệ bootstrap khối tuần, CI)
import regime_survey as RS  # noqa: E402
from core.algorithms.ict_structure import LEGACY_0_9, IctStructureAlgorithm  # noqa: E402
from core.components import price_band as PB  # noqa: E402
from core.engine import run_algorithm  # noqa: E402

SURVEY_VERSION = "pdh-pdl-survey-v1.1"
MIN_EFFECT = 0.01
KINDS = ("vung_tren", "vung_duoi", "pdh", "pdl", "range_tren", "range_duoi")
NEAR = {"up": "vung_tren", "down": "vung_duoi"}
MIN_CELL = 200                         # ô (khoảng cách) cần ≥ 200 dự báo mới ghi tỷ lệ


class Recorder:
    """Bọc ``PriceBand.step`` / ``_grade`` của lõi: ghi mỗi dự báo chạm đã chấm theo cột (mã số nguyên cho tầm / loại)."""

    def __init__(self) -> None:
        self.cols = {"h": array("b"), "kind": array("b"), "p": array("d"), "p0": array("d"), "hit": array("b"),
                     "kc": array("d"), "week": array("i"), "trung": array("b")}
        self.horizons: list[str] = []
        self.weeks = array("i")                         # tuần giao dịch của từng nến đã qua (dự báo ở s lấy tuần của s)
        self._keys: dict[int, int] = {}                 # id(_Score) → mã tầm
        self._step, self._grade = PB.PriceBand.step, PB.PriceBand._grade

    def __enter__(self):
        rec, c = self, self.cols
        kind_code = {k: i for i, k in enumerate(KINDS)}

        def step(band, bar, *a, **k):
            y, w, _d = (bar.bar_time.astimezone(RS.NY) + timedelta(hours=7)).date().isocalendar()
            rec.weeks.append(y * 100 + w)
            return rec._step(band, bar, *a, **k)

        def grade(band, sc, hour, fc, hi, lo, u, d):
            rec._grade(band, sc, hour, fc, hi, lo, u, d)
            code = rec._keys.get(id(sc))
            if code is None:
                for key, v in band.score.items():
                    if key not in rec.horizons:
                        rec.horizons.append(key)
                    rec._keys[id(v)] = rec.horizons.index(key)
                code = rec._keys[id(sc)]
            week = rec.weeks[-1 - band.horizons[rec.horizons[code]]]          # nến s = t − h của dự báo
            near = {m["phia"]: m["gia"] for m in fc["muc"] if m["loai"] == NEAR[m["phia"]]}
            for m in fc["muc"]:
                c["h"].append(code)
                c["kind"].append(kind_code[m["loai"]])
                c["p"].append(m["p"])
                c["p0"].append(m["p0"])
                c["hit"].append(PB.touched(m, hi, lo))
                c["kc"].append(m["kc_atr"])
                c["week"].append(week)
                c["trung"].append(m["loai"] in ("pdh", "pdl") and near.get(m["phia"]) == m["gia"])

        PB.PriceBand.step, PB.PriceBand._grade = step, grade
        return self

    def __exit__(self, *exc):
        PB.PriceBand.step, PB.PriceBand._grade = self._step, self._grade

    def arrays(self) -> dict[str, np.ndarray]:
        return {k: np.frombuffer(v, dtype={"b": np.int8, "d": np.float64, "i": np.int32}[v.typecode]) for k, v in self.cols.items()}


def _ci(week, diff, M, nW):
    return OB.ci(OB.week_ratio_boot(M, week, nW, diff, np.ones(diff.size))[0])


def summarize(p, p0, hit, kc, week, M, nW):
    diff = hit - p
    b, b0 = np.mean((p - hit) ** 2), np.mean((p0 - hit) ** 2)
    out = {"n": int(p.size), "so_tuan": int(np.unique(week).size), "thuc_te": RS.rnd(hit.mean(), 4),
           "ky_vong": RS.rnd(p.mean(), 4), "chenh": RS.rnd(diff.mean(), 4), "ci95": _ci(week, diff, M, nW),
           "kc_trung_vi_atr": RS.rnd(np.median(kc), 3), "brier": RS.rnd(b, 5), "brier_b0": RS.rnd(b0, 5),
           "skill_so_voi_b0": RS.rnd(1 - b / b0, 4) if b0 > 0 else None}
    rows = []
    for lo, hi in zip(S.KC_BINS[:-1], S.KC_BINS[1:]):
        sel = (kc >= lo) & (kc < hi)
        n = int(sel.sum())
        row = {"tu": lo, "den": None if np.isinf(hi) else hi, "n": n}
        if n >= MIN_CELL:
            row.update({"thuc_te": RS.rnd(hit[sel].mean(), 4), "ky_vong": RS.rnd(p[sel].mean(), 4),
                        "chenh": RS.rnd(diff[sel].mean(), 4), "ci95": _ci(week[sel], diff[sel], M, nW)})
        rows.append(row)
    out["theo_khoang_cach"] = rows
    g = np.minimum((p * PB.HIT_BINS).astype(int), PB.HIT_BINS - 1)       # cùng nhóm hiệu chuẩn với lõi
    out["hieu_chuan"] = []
    for i in range(PB.HIT_BINS):
        sel = g == i
        if sel.any():
            out["hieu_chuan"].append({"p_tb": RS.rnd(p[sel].mean(), 4), "cham": RS.rnd(hit[sel].mean(), 4), "n": int(sel.sum())})
    return out


def survey(rec: Recorder, n_boot):
    a = rec.arrays()
    hit = a["hit"].astype(float)
    weeks, week = np.unique(a["week"], return_inverse=True)
    nW = weeks.size
    M = np.random.default_rng(S.SEED + 5).multinomial(nW, np.full(nW, 1.0 / nW), size=n_boot).astype(float)
    out = {}
    for hc, h in enumerate(rec.horizons):
        kh, res = a["h"] == hc, {}
        for kc_, name in enumerate(KINDS):
            sel = kh & (a["kind"] == kc_)
            if not sel.any():
                continue
            res[name] = summarize(a["p"][sel], a["p0"][sel], hit[sel], a["kc"][sel], week[sel], M, nW)
            if name in ("pdh", "pdl"):
                for tag, part in (("trung_vung_gan_nhat", sel & (a["trung"] == 1)), ("khong_trung", sel & (a["trung"] == 0))):
                    if part.sum() >= MIN_CELL:
                        res[name][tag] = summarize(a["p"][part], a["p0"][part], hit[part], a["kc"][part], week[part], M, nW)
        out[h] = res
    return out


def check_against_core(res_sym, cham_core):
    """Số dự báo và số lần chạm ghi lại phải khớp đúng điểm lõi tự chấm (``run_stats…khoang_va_cham.<tầm>.cham``)."""
    for h, kinds in res_sym.items():
        for name, r in kinds.items():
            core = cham_core[h]["cham"][name]
            if r["n"] != core["n"] or abs(r["thuc_te"] - core["ty_le_cham"]) >= 1e-4:
                raise RuntimeError("Bản ghi lệch điểm lõi: %s %s n %d / %d" % (h, name, r["n"], core["n"]))


def decide(res):
    """Quy tắc khai trước: kết luận mỗi loại PDH / PDL."""
    out = {}
    for name in ("pdh", "pdl"):
        per_sym = {}
        for sym, by_h in res.items():
            per_sym[sym] = any(abs(r[name]["chenh"]) >= MIN_EFFECT and r[name]["ci95"] is not None
                               and (r[name]["ci95"][0] > 0 or r[name]["ci95"][1] < 0)
                               for r in by_h.values() if name in r)
        both = {"XAUUSD", "EURUSD"} <= set(per_sym)        # quy tắc cần CẢ HAI mã — thiếu mã thì không kết luận
        out[name] = {"theo_ma": per_sym, "du_hai_ma": both, "hieu_chinh_rieng": both and all(per_sym.values())}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", default=os.path.join(ROOT, "docs", "research", "khao_sat", "pdh_pdl_dev.json"))
    ap.add_argument("--db", default=os.environ.get("MSL_DB_PATH") or os.path.join(ROOT, "data", "lab.sqlite"))
    ap.add_argument("--ma", default="XAUUSD,EURUSD", help="Danh sách mã, cách nhau bởi dấu phẩy")
    ap.add_argument("--nhanh", action="store_true", help="Chạy thử nhanh (ít bootstrap) — không dùng để kết luận")
    args = ap.parse_args()
    t_all = time.time()
    n_boot = 200 if args.nhanh else S.N_BOOT
    con = sqlite3.connect("file:%s?mode=ro" % args.db.replace("\\", "/"), uri=True)
    with open(os.path.abspath(__file__), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    meta = {"phien_ban": SURVEY_VERSION, "script_sha256": sha, "python": platform.python_version(),
            "numpy": np.__version__, "doan_kiem_tra_tu": S.TEST_START, "seed": S.SEED, "chay_nhanh": bool(args.nhanh),
            "tham_so": {"n_boot": n_boot, "min_effect": MIN_EFFECT,
                        "kc_bins": [x if np.isfinite(x) else None for x in S.KC_BINS], "cal_bins": PB.HIT_BINS,
                        "min_cell": MIN_CELL}, "lan_chay": {}}
    res = {}
    wanted = [s.strip() for s in args.ma.split(",") if s.strip()]
    for spec in S.SETS:
        sym = spec["key"].split()[0]
        if sym not in wanted:
            continue
        _d, bars, _tf, src_meta = RS.load(con, spec, allow_test=False)
        algo = IctStructureAlgorithm(timeframe="M15", session_calendar=RS.CAL[sym], **LEGACY_0_9)
        t0 = time.time()
        with Recorder() as rec:
            run = run_algorithm(bars, algo)
        res[sym] = survey(rec, n_boot)
        check_against_core(res[sym], algo.run_stats(run.events)["nhan_dien"]["khoang_va_cham"])
        meta["lan_chay"][sym] = dict(src_meta, nen=len(bars), giay=round(time.time() - t0, 1),
                                     phien_ban_thuat_toan=algo.version, du_bao_cham=len(rec.cols["p"]))
        print("%s: %d nến, %d dự báo chạm, %.0f s" % (sym, len(bars), len(rec.cols["p"]), time.time() - t0), flush=True)
    meta["giay"] = round(time.time() - t_all, 1)
    out = {"meta": meta, "ket_qua": res, "ket_luan": decide(res)}
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    for sym, by_h in res.items():
        for h, kinds in by_h.items():
            for name, r in kinds.items():
                print("%s %s %-10s n %7d · thật %.3f · kỳ vọng %.3f · chênh %+.4f %s · skill B0 %s" % (
                    sym, h, name, r["n"], r["thuc_te"], r["ky_vong"], r["chenh"], r["ci95"], r["skill_so_voi_b0"]))
    print("Kết luận:", json.dumps(out["ket_luan"], ensure_ascii=False))


if __name__ == "__main__":
    main()
