"""[E3] MSS — market structure shift kiểu ICT 2022 (``ict_structure`` 0.10.0, plan_mss_ob_pd.md §2).

Mô tả cho **MSS giảm** (sau quét BSL); MSS tăng đối xứng.

* **Ứng viên** (bước 3 của nến sweep r): vùng bị quét (mức L, nến lấy b, cực trị cú quét ``X = max(high[b..r])``) + **mốc phá** = STL
  gần nhất có nến cực trị < b (người gọi tìm, trong các STL đã xác nhận trước r) + mốc ITL tuỳ chọn (cờ ``significant``).
* **Xét ở bước 6 của mỗi nến t ≥ r:**

  1. t > r: có khoảng trống trước t → huỷ; ``high[t] > X`` → huỷ (cú quét đã bị vượt; bằng X không huỷ);
  2. ``close[t] < STL`` (nghiêm ngặt) → quyết định **một lần**: đoạn displacement = ``leg_bars`` nến cuối tới t (không vắt qua khoảng
     trống), đỉnh đoạn H = max high (nến muộn nhất nếu bằng nhau); ``H − close[t] ≥ leg_atr × ATR[t−1]`` → **MSS**; không đủ / chưa có
     ATR → kết thúc «phá yếu», không có sự kiện;
  3. còn lại: chờ tiếp, không giới hạn thời gian.

* Nhiều ứng viên cùng chiều thành MSS ở cùng nến → một MSS (người gọi gom); ứng viên cùng chiều còn chờ bị gom vào MSS đó.

Thành phần chỉ giữ trạng thái; thuật toán phát sự kiện (``MSS_*``, ``MSS_FVG_*``).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Optional

from core.components.shift import overrun
from core.types import Bar


@dataclass
class MssRef:
    """Mốc phá (STL / STH) hoặc mốc significant (ITL / ITH)."""

    price: float
    bar: int                      # nến cực trị
    event_id: str


@dataclass
class MssCandidate:
    direction: str                # "down" (sau quét BSL) | "up" (sau quét SSL)
    level: float                  # mức bị quét
    extreme: float                # X
    r: int                        # nến sweep
    ref: MssRef                   # STL (MSS giảm) / STH (MSS tăng) trước cú chạy
    sig: Optional[MssRef]         # ITL / ITH trước cú chạy (cờ significant)
    sweep_event_id: str
    group_id: str
    tier: str
    pools: list[dict[str, Any]] = field(default_factory=list)
    taken_index: Optional[int] = None

    def broken(self, close: float) -> bool:
        return close < self.ref.price if self.direction == "down" else close > self.ref.price

    def significant(self, close: float) -> bool:
        return self.sig is not None and (close < self.sig.price if self.direction == "down" else close > self.sig.price)


class MssTracker:
    """Ứng viên MSS + mốc phá. Tự giữ STL / STH, ITL / ITH đã xác nhận (``on_swing``) và FVG gần đây (``on_fvg``) — thuật toán chỉ
    báo nguyên liệu, không biết quy tắc tìm mốc."""

    def __init__(self, leg_bars: int, leg_atr: float, memory: int = 64) -> None:
        if leg_bars < 1 or leg_atr < 0:
            raise ValueError("mss_chan_nen phải ≥ 1, mss_chan_atr phải ≥ 0")
        self.leg_bars = leg_bars
        self.leg_atr = leg_atr
        self.memory = memory              # số swing mỗi (phía, cấp) giữ lại: mốc = swing gần nhất trước nến lấy
        self.reset()

    def reset(self) -> None:
        self.pending: list[MssCandidate] = []
        self._leg: deque[Bar] = deque(maxlen=self.leg_bars)    # nến của đoạn đang xét, không vắt qua khoảng trống
        self._swings: dict[tuple[str, int], deque[MssRef]] = {
            (side, lvl): deque(maxlen=self.memory) for side in ("high", "low") for lvl in (1, 2)}
        self._fvgs: deque[tuple[int, str, str]] = deque(maxlen=self.leg_bars + 2)   # (nến giữa, chiều, id)
        self.counts = {"ung_vien": 0, "khong_co_moc": 0, "huy_vuot_cuc_tri": 0, "huy_khoang_trong": 0, "pha_yeu": 0,
                       "gop_vao_mss": 0, "thanh_mss": 0}

    # ------------------------------------------------------------------ nguyên liệu
    def on_swing(self, side: str, level: int, price: float, bar: int, event_id: str) -> None:
        """Swing cấp 1 / 2 vừa xác nhận (bước 9 — có hiệu lực cho sweep từ nến sau)."""
        if level <= 2:
            self._swings[(side, level)].append(MssRef(price, bar, event_id))

    def on_fvg(self, mid: int, direction: str, event_id: str) -> None:
        """FVG vừa biết (bước 5) — để ghi «FVG trong đoạn displacement» của MSS."""
        self._fvgs.append((mid, direction, event_id))

    def _before(self, side: str, level: int, b: int) -> Optional[MssRef]:
        for ref in reversed(self._swings[(side, level)]):
            if ref.bar < b:
                return ref
        return None

    def add_from_sweep(self, side: str, level: float, extreme: float, taken: int, r: int, sweep_id: str, tier: str,
                       pool: dict[str, Any]) -> Optional[MssCandidate]:
        """Vùng phía ``side`` ("high" = BSL) bị quét ở nến r (nến lấy ``taken``): mốc = STL (quét BSL) / STH (quét SSL) gần nhất có
        nến cực trị < nến lấy; mốc significant = ITL / ITH tương tự. Không có STL / STH → không ứng viên (chỉ đếm)."""
        ref_side = "low" if side == "high" else "high"
        ref = self._before(ref_side, 1, taken)
        if ref is None:
            self.counts["khong_co_moc"] += 1
            return None
        c = MssCandidate(direction="down" if side == "high" else "up", level=level, extreme=extreme, r=r, ref=ref,
                         sig=self._before(ref_side, 2, taken), sweep_event_id=sweep_id, group_id=sweep_id, tier=tier,
                         pools=[pool], taken_index=taken)
        self.pending.append(c)
        self.counts["ung_vien"] += 1
        return c

    def leg_fvg(self, direction: str, start: int, t: int) -> Optional[str]:
        """FVG cùng chiều đã biết tới nến t có nến giữa trong [start, t − 1] (đoạn displacement)."""
        return next((eid for mid, d, eid in self._fvgs if d == direction and start <= mid <= t - 1), None)

    # ------------------------------------------------------------------ xét nến
    def leg(self, direction: str, close: float, atr_prev: Optional[float]) -> dict[str, Any]:
        """Đoạn displacement tới nến hiện tại: nến đầu (cực trị của đoạn — muộn nhất nếu bằng), cực trị, biên độ tới close."""
        best: Optional[Bar] = None
        for b in self._leg:
            if best is None or (b.high >= best.high if direction == "down" else b.low <= best.low):
                best = b
        top = best.high if direction == "down" else best.low
        size = (top - close) if direction == "down" else (close - top)
        return {"nen_dau": best.index, "cuc_tri": top, "bien_do": size, "so_nen": self._leg[-1].index - best.index + 1,
                "atr": atr_prev, "bien_do_atr": size / atr_prev if atr_prev else None}

    def on_bar(self, bar: Bar, atr_prev: Optional[float],
               gap_before: bool) -> dict[str, tuple[list[MssCandidate], dict[str, Any]]]:
        """Xét nến t cho mọi ứng viên (kể cả ứng viên vừa thêm ở chính t). Trả {chiều: (ứng viên thành MSS, đoạn)} — đoạn chỉ phụ
        thuộc chiều và close nên tính một lần mỗi chiều."""
        t = bar.index
        if gap_before:
            self._leg.clear()
        self._leg.append(bar)
        if not self.pending:
            return {}
        legs: dict[str, dict[str, Any]] = {}
        ok: dict[str, tuple[list[MssCandidate], dict[str, Any]]] = {}
        still: list[MssCandidate] = []
        for c in self.pending:
            if t > c.r:
                if gap_before:
                    self.counts["huy_khoang_trong"] += 1
                    continue
                if overrun(c.direction, c.extreme, bar):
                    self.counts["huy_vuot_cuc_tri"] += 1
                    continue
            if not c.broken(bar.close):
                still.append(c)
                continue
            leg = legs.get(c.direction) or legs.setdefault(c.direction, self.leg(c.direction, bar.close, atr_prev))
            if atr_prev and leg["bien_do"] >= self.leg_atr * atr_prev:
                ok.setdefault(c.direction, ([], leg))[0].append(c)
                self.counts["thanh_mss"] += 1
            else:
                self.counts["pha_yeu"] += 1
        if ok:                                       # một cú đảo, một MSS: ứng viên cùng chiều còn chờ gom vào MSS vừa phát
            kept = [c for c in still if c.direction not in ok]
            self.counts["gop_vao_mss"] += len(still) - len(kept)
            still = kept
        self.pending = still
        return ok
