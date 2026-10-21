"""[N] Trạng thái mô tả: range biên rõ / nén / trend / nhiễu (thuat_toan_nhan_dien.md §5; plan nhận diện §3).

Sau nến t, theo thứ tự (điều kiện đầu tiên đúng là ứng viên):

1. **range** — cửa sổ 16, 12, 8 giờ (dài trước), biên trên U = max high, biên dưới D = min low; ≥ 2 swing đỉnh
   (pivot 2/2 đã xác nhận) trong 0,3·ATR của U cách nhau ≥ 1,5 giờ, tương tự ở D; (U − D)/ATR trong [1,5; 5]; ER < ngưỡng.
2. **nen** — cửa sổ 12 giờ: ba swing đỉnh cuối giảm ngặt, ba swing đáy cuối tăng ngặt, bề rộng ¼ cuối ≤ 50% ¼ đầu,
   ER < ngưỡng.
3. **trend_len / trend_xuong** — ER(8 giờ) ≥ ngưỡng, chiều theo C_t − C_{t−W}.
4. **nhieu** — còn lại.

Pivot 2/2 của lớp này (đặc tả N-5): high lớn hơn **ngặt** 2 nến trái, **≥** 2 nến phải (đỉnh bằng giá liền nhau → nến đầu
là pivot) — đúng ví dụ ``research/vi_du_range_sideway.py`` của plan; khác ``PivotSource`` (ngặt cả hai phía).

Cửa sổ không vắt qua khoảng trống dài (thuật toán báo qua ``gap_before``); chưa đủ nến → None. Trạng thái chỉ đổi khi
ứng viên giữ đủ ``hold`` nến. Hằng số do lab chọn theo plan §3 (đã chốt 21/10/2026). Thành phần chỉ giữ trạng thái;
thuật toán phát sự kiện.
"""
from __future__ import annotations

from collections import deque
from typing import Any, Optional

from core.indicators import RollingHighLow
from core.types import Bar

RANGE_HOURS = (16, 12, 8)
TOUCH_TOL_ATR = 0.3
MIN_TOUCH = 2
TOUCH_GAP_HOURS = 1.5
RANGE_WIDTH_ATR = (1.5, 5.0)
SQUEEZE_HOURS = 12
SQUEEZE_RATIO = 0.5
TREND_HOURS = 8
PIVOT = 2
#: Trạng thái → chữ ngắn (details, giao diện). Khoá cũng là danh sách trạng thái.
TEXT_VI = {"trend_len": "trend lên", "trend_xuong": "trend xuống", "range": "range biên rõ", "nen": "sideway nén",
           "nhieu": "sideway nhiễu"}


def _spaced(idx: list[int], min_gap: int) -> list[int]:
    """Lần chạm cách nhau ≥ ``min_gap`` nến (giữ lần sớm nhất của mỗi cụm)."""
    keep: list[int] = []
    for j in idx:
        if not keep or j - keep[-1] >= min_gap:
            keep.append(j)
    return keep


def _since(pivots: deque[tuple[int, float]], start: int) -> list[tuple[int, float]]:
    return [(j, p) for j, p in pivots if j >= start]


class MarketState:
    def __init__(self, step_seconds: float, er_threshold: float = 0.3, hold: int = 2) -> None:
        if not 0.0 < er_threshold < 1.0 or hold < 1:
            raise ValueError("Nhận diện: cần 0 < ngưỡng ER < 1 và «giữ trạng thái mới» ≥ 1 nến.")
        per_hour = 3600.0 / step_seconds

        def bars(hours: float) -> int:
            return max(int(round(hours * per_hour)), 2 * PIVOT + 1)

        self.range_w = tuple(dict.fromkeys(bars(h) for h in RANGE_HOURS))   # H4/D1: kẹp ≥ 5 nến → có thể trùng
        self.squeeze_w, self.trend_w = bars(SQUEEZE_HOURS), bars(TREND_HOURS)
        self.touch_gap = max(int(round(TOUCH_GAP_HOURS * per_hour)), 1)
        self.er_threshold, self.hold = er_threshold, hold
        self._cap = max(self.range_w + (self.squeeze_w, self.trend_w)) + 1
        self.reset()

    def reset(self) -> None:
        self._bars: deque[Bar] = deque(maxlen=self._cap)
        self._cum: deque[float] = deque(maxlen=self._cap)             # Σ|ΔC| cộng dồn (cho ER)
        self._run = 0                                                  # số nến liên tiếp từ khoảng trống gần nhất
        self._hl = {w: RollingHighLow(w) for w in self.range_w}        # biên của từng cửa sổ range, O(1) mỗi nến
        self._hl_now: dict[int, tuple[float, float]] = {}
        self._piv_hi: deque[tuple[int, float]] = deque()
        self._piv_lo: deque[tuple[int, float]] = deque()
        self.state: Optional[str] = None
        self.since: Optional[int] = None
        self.info: dict[str, Any] = {}
        self._pending: Optional[list] = None                           # [ứng viên, nến đầu, số nến liên tiếp]
        self.counts = dict.fromkeys(TEXT_VI, 0)                        # số nến theo trạng thái đang hiện sau nến
        self.changes = 0

    # ------------------------------------------------------------------ mỗi nến
    def on_bar(self, bar: Bar, atr: Optional[float], gap_before: bool) -> Optional[tuple[str, Bar, dict[str, Any]]]:
        """Trạng thái sau nến t (``gap_before`` = khoảng trống dài ngay trước t). Trả (trạng thái mới, nến đầu của nó,
        info) khi vừa đổi, không thì None."""
        if gap_before:
            self._run = 0
            self._piv_hi.clear()
            self._piv_lo.clear()
        prev = self._bars[-1] if self._bars and self._run > 0 else None
        self._run += 1
        self._cum.append((self._cum[-1] + abs(bar.close - prev.close)) if prev is not None else 0.0)
        self._bars.append(bar)
        for w, hl in self._hl.items():
            self._hl_now[w] = hl.push(bar.index, bar.high, bar.low)
        self._pivot()
        cand = self._classify(atr)
        changed = None
        if cand is None:                                               # chưa đủ nến / chưa có ATR: không phát sự kiện
            self.state, self.since, self.info, self._pending = None, None, {}, None
        elif cand[0] == self.state:
            self.info, self._pending = cand[1], None
        else:
            name, info = cand
            if self.state == "range":                                  # đang chờ rời range: biên vẫn là biên của nến t
                self.info = {**self.info, "bien_tren": max(self.info["bien_tren"], bar.high),
                             "bien_duoi": min(self.info["bien_duoi"], bar.low)}
            p = self._pending
            p = self._pending = [name, bar, 1] if p is None or p[0] != name else [name, p[1], p[2] + 1]
            if p[2] >= self.hold:
                self.state, self.since, self.info, self._pending = name, p[1].index, info, None
                self.changes += 1
                changed = (name, p[1], info)
        if self.state is not None:
            self.counts[self.state] += 1
        return changed

    def pending_candidate(self) -> Optional[dict[str, Any]]:
        """Trạng thái ứng viên đang chờ đủ ``hold`` nến liên tiếp; None nếu không có."""
        p = self._pending
        return None if p is None else {"trang_thai": p[0], "trang_thai_vi": TEXT_VI[p[0]], "tu_nen": p[1].index,
                                       "so_nen": p[2], "can": self.hold}

    def _pivot(self) -> None:
        """Pivot 2/2 tại nến t − 2 (xác nhận ở t); không vắt khoảng trống."""
        if self._run < 2 * PIVOT + 1:
            return
        w = [self._bars[i] for i in range(-(2 * PIVOT + 1), 0)]
        m = w[PIVOT]
        if m.high > max(b.high for b in w[:PIVOT]) and m.high >= max(b.high for b in w[PIVOT + 1:]):
            self._piv_hi.append((m.index, m.high))
        if m.low < min(b.low for b in w[:PIVOT]) and m.low <= min(b.low for b in w[PIVOT + 1:]):
            self._piv_lo.append((m.index, m.low))
        oldest = self._bars[0].index
        for q in (self._piv_hi, self._piv_lo):
            while q and q[0][0] < oldest:
                q.popleft()

    def _er(self, w: int) -> float:
        net = abs(self._bars[-1].close - self._bars[-1 - w].close)
        path = self._cum[-1] - self._cum[-1 - w]
        return net / path if path > 0 else 0.0

    def _classify(self, atr: Optional[float]) -> Optional[tuple[str, dict[str, Any]]]:
        if atr is None or atr <= 0 or self._run <= self.trend_w:
            return None
        t = self._bars[-1].index
        thr = self.er_threshold
        for w in self.range_w:
            if self._run <= w:
                continue
            er = self._er(w)
            if er >= thr:
                continue
            top, bot = self._hl_now[w]
            width = (top - bot) / atr
            if not RANGE_WIDTH_ATR[0] <= width <= RANGE_WIDTH_ATR[1]:
                continue
            start, tol = t - w + 1, TOUCH_TOL_ATR * atr
            tu = _spaced([j for j, p in _since(self._piv_hi, start) if p >= top - tol], self.touch_gap)
            td = _spaced([j for j, p in _since(self._piv_lo, start) if p <= bot + tol], self.touch_gap)
            if len(tu) >= MIN_TOUCH and len(td) >= MIN_TOUCH:
                return "range", {"cua_so_nen": w, "nen_dau_cua_so": start, "bien_tren": top, "bien_duoi": bot,
                                 "rong_atr": width, "er": er, "cham_tren": tu, "cham_duoi": td, "dung_sai": tol,
                                 "rong_cho_phep_atr": list(RANGE_WIDTH_ATR), "so_lan_cham_toi_thieu": MIN_TOUCH,
                                 "cach_nhau_toi_thieu_nen": self.touch_gap}
        w = self.squeeze_w
        er = self._er(w) if self._run > w else thr
        if er < thr:
            start = t - w + 1
            hs = [p for _j, p in _since(self._piv_hi, start)][-3:]
            ls = [p for _j, p in _since(self._piv_lo, start)][-3:]
            if len(hs) == 3 and len(ls) == 3 and hs[0] > hs[1] > hs[2] and ls[0] < ls[1] < ls[2]:
                win, q = list(self._bars)[-w:], max(w // 4, 1)
                first = max(b.high for b in win[:q]) - min(b.low for b in win[:q])
                last = max(b.high for b in win[-q:]) - min(b.low for b in win[-q:])
                if first > 0 and last <= SQUEEZE_RATIO * first:
                    return "nen", {"cua_so_nen": w, "dinh": hs, "day": ls, "rong_dau": first, "rong_cuoi": last,
                                   "ty_le_rong": last / first, "ty_le_toi_da": SQUEEZE_RATIO, "er": er}
        w = self.trend_w
        er = self._er(w)
        if er >= thr:
            up = self._bars[-1].close >= self._bars[-1 - w].close
            return ("trend_len" if up else "trend_xuong"), {"cua_so_nen": w, "er": er}
        return "nhieu", {"cua_so_nen": w, "er": er}
