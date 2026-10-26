"""Chấm forward bản ghi dự báo của lớp nhận diện (``ict_structure`` ≥ 0.9.3) — ``docs/plans/plan_mt5_live.md`` §5.

* Bản ghi của nến t = ``IctStructureAlgorithm.forecast_record()`` ngay sau nến t (``NdLayer.record``): khoảng, mức, phá
  biên, còn giữ, mỗi thứ kèm B0. Lưu một lần, không sửa (kho live chỉ ghi thêm).
* ``is_timely``: bản ghi kịp thời = ghi trước khi nến kế tiếp đóng (trước khi biết bất kỳ phần kết cục nào).
* ``score``: chấm bản ghi bằng nến đã lưu, **không chạy lại thuật toán** — cùng định nghĩa §6 của
  ``docs/algorithms/thuat_toan_nhan_dien.md``: cửa sổ = h nến kế tiếp (s, s+h]; cửa sổ có khoảng trống dài (hai nến liền
  nhau cách > 180 phút, không đúng bước khung) → không chấm. Còn giữ: trạng thái ở mọi nến của cửa sổ (đọc ở bản ghi của
  các nến đó) bằng trạng thái ở s; có nến «chưa đủ nến» → không chấm.

Chấm mọi bản ghi của một lần chạy phải ra đúng điểm thật trong lần chạy (``diem_that``) — test kiểm chéo. Không có P&L.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional, Sequence

from core.algorithms.ict_structure.nhan_dien import TOUCH_TOTAL_KINDS, is_long_gap
from core.components.price_band import pinball, touched
from core.components.rolling_stats import BrierTally, ratio
from core.types import Bar

#: Dưới số dự báo đã chấm này thì chưa kết luận (như tooltip điểm thật trong lần chạy).
MIN_SCORED = 100


def quantile_80(params: dict[str, Any]) -> float:
    """``nd_muc_80`` của lần chạy (pinball); lỗi khi tắt lớp nhận diện — không có dự báo để ghi."""
    if not params.get("nd_bat"):
        raise ValueError("Bản ghi forward là dự báo của lớp nhận diện — phải bật nd_bat.")
    return params["nd_muc_80"]


def is_timely(written_at: datetime, close_time: datetime, step: timedelta) -> bool:
    """Ghi trước khi nến kế tiếp đóng — trước khi biết bất kỳ phần kết cục nào. Ghi muộn hơn («ghi bù») vẫn nhân quả
    nhưng không vào điểm chính."""
    return written_at <= close_time + step


class _Horizon:
    __slots__ = ("n", "cov80", "cov50", "w80", "loss", "loss0", "touch", "pha", "giu", "cho", "khoang_trong")

    def __init__(self) -> None:
        self.n = self.cov80 = self.cov50 = self.cho = self.khoang_trong = 0
        self.w80 = self.loss = self.loss0 = 0.0
        self.touch: dict[str, BrierTally] = defaultdict(BrierTally)
        self.pha, self.giu = BrierTally(), BrierTally()

    def summary(self) -> dict[str, Any]:
        def touch_row(t: BrierTally) -> dict[str, Any]:
            s = t.summary()
            return {"n": s["n"], "brier": s["brier"], "brier_b0": s["brier_b0"], "ty_le_cham": s["ty_le"]}

        tot = [t for kind, t in self.touch.items() if kind in TOUCH_TOTAL_KINDS]
        tn = sum(t.n for t in tot)
        return {
            "n": self.n, "phu_80": ratio(self.cov80, self.n), "phu_50": ratio(self.cov50, self.n),
            "rong_80_atr": ratio(self.w80, self.n),
            "skill_so_voi_b0": (1.0 - self.loss / self.loss0) if self.loss0 > 0 else None,
            "cham": {kind: touch_row(t) for kind, t in sorted(self.touch.items())},
            "cham_tong": {"n": tn, "brier": ratio(sum(t.brier for t in tot), tn),
                          "brier_b0": ratio(sum(t.brier0 for t in tot), tn)},
            "pha_bien": self.pha.summary(), "con_giu": self.giu.summary(),
            "cho_ket_cuc": self.cho, "bo_qua_khoang_trong": self.khoang_trong,
        }


def score(bars: Sequence[Bar], records: dict[int, dict[str, Any]], q80: float, step: timedelta,
          only: Optional[Iterable[int]] = None) -> dict[str, Any]:
    """Điểm forward mỗi tầm. ``bars[i].index`` = i; ``records`` = {t: bản ghi} (mọi bản ghi đã có — trạng thái của cửa sổ
    còn giữ đọc ở đây); ``only`` = các t được chấm (vd chỉ bản ghi kịp thời), None = mọi bản ghi. ``q80`` = ``nd_muc_80``
    của lần chạy (pinball)."""
    gaps = [0]                                          # gaps[j] = số khoảng trống dài trước các nến 1..j
    for j in range(1, len(bars)):
        d = bars[j].bar_time - bars[j - 1].bar_time
        gaps.append(gaps[-1] + is_long_gap(None if d == step else d.total_seconds() / 60.0))
    last = len(bars) - 1
    out: dict[str, _Horizon] = defaultdict(_Horizon)
    for t in sorted(records if only is None else only):
        rec = records[t]
        for k, r in rec["tam"].items():
            sc, h = out[k], r["h"]
            band, g = r.get("khoang"), r.get("con_giu")
            if not band and g is None:
                continue
            if t + h > last:
                sc.cho += 1
                continue
            if gaps[t + h] != gaps[t]:
                sc.khoang_trong += 1
                continue
            win = bars[t + 1:t + h + 1]
            if band:
                _grade_band(sc, rec, r, win, q80)
            if g is not None:
                states = [records[j]["trang_thai"] if j in records else None for j in range(t + 1, t + h + 1)]
                if None not in states:
                    sc.giu.add(g["p"], g["p0"], all(s == rec["trang_thai"] for s in states))
    return {k: sc.summary() for k, sc in sorted(out.items())}


def _grade_band(sc: _Horizon, rec: dict[str, Any], r: dict[str, Any], win: Sequence[Bar], q80: float) -> None:
    band = r["khoang"]
    hi, lo = max(b.high for b in win), min(b.low for b in win)
    c, a = rec["close"], rec["atr"]
    u, d = (hi - c) / a, (c - lo) / a
    sc.n += 1
    sc.cov80 += hi <= band["hi80"] and lo >= band["lo80"]
    sc.cov50 += hi <= band["hi50"] and lo >= band["lo50"]
    sc.w80 += band["qu80"] + band["qd80"]
    sc.loss += pinball(q80, u, band["qu80"]) + pinball(q80, d, band["qd80"])
    sc.loss0 += pinball(q80, u, band["b0"][0]) + pinball(q80, d, band["b0"][1])
    for m in r["muc"]:
        sc.touch[m["loai"]].add(m["p"], m["p0"], touched(m, hi, lo))
    pb = r.get("pha_bien")
    if pb is not None:
        closes = [b.close for b in win]
        sc.pha.add(pb["p"], pb["p0"], max(closes) > pb["hi"] or min(closes) < pb["lo"])
