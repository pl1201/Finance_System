"""[T1] Ngăn xếp cấu trúc khung lớn (H1/H4) — plan_ict_structure §11.4.

Chạy **chính** các thành phần của khung nhỏ trên nến khung lớn ĐÃ CHỐT (``HtfBar`` của bộ gộp
``core/data/htf_stream.SessionHtfAggregator``), ATR riêng của khung:

* [P1] ``PivotSource`` (STH/STL strict ``left``/``right``) → [S1] ``HierarchyLevel(2)`` (ITH/ITL);
* [S2] ``StructureOrder`` (thứ tự đỉnh/đáy, mức được bảo vệ, cờ vượt — close của nến khung lớn);
* [S4] ``DealingRange`` (mở rộng theo high/low nến khung lớn đã chốt);
* [P3] ``Displacement`` (cờ ``from_displacement`` của FVG, theo ATR khung lớn) và [P2] ``FvgTracker.detect``
  (chỉ phát hiện vùng — phản ứng của giá đo ở [S5], ``pd_array.py``).

Cấu trúc khung lớn luôn ở cấp 2 (ITH/ITL), không theo ``structure_level`` của khung chạy.

**Quy tắc chất lượng lan truyền (R3):**

* nến ``degraded`` không được nằm trong cửa sổ pivot (c−1..c+1) hay bộ ba FVG; cửa sổ pivot vắt qua
  hole (``after_hole``) bị chặn. Nghỉ phiên / cuối tuần **không** chặn pivot khung lớn (khác khung chạy — D1);
* bộ ba FVG phải liền kề theo lịch (``contiguous_prev``: nến mở đúng lúc nến trước đóng theo lịch — không vắt
  qua nghỉ phiên, cuối tuần, đóng sớm, hole) và không có nến ``degraded``;
* ITH/ITL chỉ dựng từ STH hợp lệ → thứ tự, dealing range, vùng thanh khoản, FVG tự không có trên dữ liệu thiếu.

Thứ tự trong một nến khung lớn (như bước 4–9 của khung chạy): displacement → FVG (bộ ba kết thúc ở nến này)
→ cờ vượt mức được bảo vệ (close) → mở rộng dealing range → pivot → ITH/ITL → thứ tự, mức, dealing range
mới → cập nhật ATR. Chỉ nhận nến đã chốt; nến đang hình thành không vào trạng thái (AGENTS §2.1).
"""
from __future__ import annotations

from collections import deque
from typing import Any, Optional

from core.components.dealing_range import DealingRange
from core.components.displacement import Displacement
from core.components.fvg import Fvg, FvgTracker
from core.components.hierarchy import HierarchyLevel
from core.components.structure_order import StructureOrder
from core.components.swing_source import Pivot, PivotSource
from core.data.htf_stream import HtfBar
from core.indicators import WilderATRPrevClose

#: Số nến khung lớn gần nhất dùng để đếm ``blocked_windows_recent`` (do lab chọn).
BLOCKED_RECENT_BARS = 20


class HtfStack:
    def __init__(self, frame: str, left: int, right: int, atr_period: int, eq_tol_atr: float,
                 k_disp: float, body_min: float, fvg_min_atr: float) -> None:
        self.frame = frame
        self.left, self.right = left, right
        self.atr_period = atr_period
        self.eq_tol_atr = eq_tol_atr
        self.k_disp, self.body_min, self.fvg_min_atr = k_disp, body_min, fvg_min_atr
        self.reset()

    def reset(self) -> None:
        self.pivots = PivotSource(self.left, self.right, block_gaps=True)
        self.l2 = HierarchyLevel(2)
        self.order = StructureOrder(self.eq_tol_atr)
        self.range = DealingRange()
        self.disp = Displacement(self.k_disp, self.body_min)
        self.fvg = FvgTracker(self.fvg_min_atr)
        self.atr = WilderATRPrevClose(self.atr_period)
        self._recent: deque[HtfBar] = deque(maxlen=3)
        self._highs: list[float] = []
        self._lows: list[float] = []
        self._disp_prev_dir: Optional[str] = None
        n = self.left + self.right + 1
        self._win_flags: deque[tuple[bool, bool]] = deque(maxlen=n)   # (degraded, after_hole) theo nến
        self._blocked_recent: deque[bool] = deque(maxlen=BLOCKED_RECENT_BARS)
        self.last: Optional[HtfBar] = None
        self.n = 0
        self.order_since: Optional[int] = None           # nến khung lớn mà ``order`` nhận giá trị hiện tại
        self._static: Optional[tuple] = None             # phần ngữ cảnh chỉ đổi khi chốt nến khung lớn
        self.counts = {"nen": 0, "degraded": 0, "after_hole": 0, "over": 0, "ngoai_lich": 0, "chot_muon": 0,
                       "cua_so_bi_chan": 0, "ith": 0, "itl": 0, "fvg_tang": 0, "fvg_giam": 0}

    def ready(self) -> bool:
        """Đủ ATR và đã có trạng thái thứ tự (plan §11.4 «Khởi động»)."""
        return self.atr.value is not None and self.order.order is not None

    def on_bar(self, hb: HtfBar) -> dict[str, Any]:
        """Nến khung lớn vừa chốt. Trả ``{"swings": [(Pivot ITH/ITL, chi tiết so sánh)], "fvg": Fvg|None,
        "atr_prev": ATR khung lớn trước nến này, "fvg_bars": (nến 1, giữa, 3)}``."""
        c = self.counts
        c["nen"] += 1
        c["degraded"] += hb.degraded
        c["after_hole"] += hb.after_hole
        c["over"] += hb.over
        c["ngoai_lich"] += hb.outside_calendar
        c["chot_muon"] += hb.late
        atr_prev = self.atr.value
        disp = self.disp.check(hb, atr_prev, after_gap=not hb.contiguous_prev)
        # [P2] FVG với nến 3 = hb: ba nến liền kề theo lịch, không nến nào degraded
        fvg: Optional[Fvg] = None
        trio = None
        if len(self._recent) >= 2:
            b1, b2 = self._recent[-2], self._recent[-1]
            bad = (not b2.contiguous_prev or not hb.contiguous_prev or b1.degraded or b2.degraded or hb.degraded)
            fvg = self.fvg.detect(b1, b2, hb, bad, atr_prev, self._disp_prev_dir)
            if fvg is not None:
                trio = (b1, b2, hb)
                c["fvg_tang" if fvg.direction == "up" else "fvg_giam"] += 1
        # [S2] close nến khung lớn so với mức được bảo vệ đã biết trước nó; [S4] dealing range gồm nến này
        self.order.check_close(hb)
        self.range.on_bar(hb)
        self._highs.append(hb.high)
        self._lows.append(hb.low)
        # cửa sổ pivot có tâm ở nến (n − right): bị chặn vì chất lượng? (đếm mọi cửa sổ, không chỉ ứng viên)
        self._win_flags.append((hb.degraded, hb.after_hole))
        if len(self._win_flags) == self._win_flags.maxlen:
            flags = list(self._win_flags)
            blocked = any(d for d, _h in flags) or any(h for _d, h in flags[1:])
            self._blocked_recent.append(blocked)
            c["cua_so_bi_chan"] += blocked
        swings: list[tuple[Pivot, dict[str, Any]]] = []
        before = self.order.order
        for p in self.pivots.update(hb, gap_before=hb.after_hole, bad=hb.degraded):
            q = self.l2.update(p)
            if q is None:
                continue
            det = self.order.on_swing(q, atr_prev)
            seq = self._highs if q.side == "high" else self._lows
            extreme = max(seq[q.pos:]) if q.side == "high" else min(seq[q.pos:])
            self.range.on_swing(q, extreme)
            c["ith" if q.side == "high" else "itl"] += 1
            swings.append((q, det))
        if self.order.order != before:
            self.order_since = hb.index
        self.atr.update(hb.high, hb.low, hb.close)
        self._recent.append(hb)
        self._disp_prev_dir = disp["dir"] if disp is not None else None
        self.last = hb
        self.n += 1
        o = self.order
        p = o.protected
        r = self.range
        self._static = (
            self.ready(), o.order,
            (hb.index - self.order_since) if (o.order is not None and self.order_since is not None) else None,
            p.price if p else None, o.broken if p else None,
            hb.known_index, hb.coverage, self.blocked_recent(),
            r.hi if r.ready() else None, r.lo if r.ready() else None,
        )
        return {"swings": swings, "fvg": fvg, "fvg_bars": trio, "atr_prev": atr_prev}

    def blocked_recent(self) -> int:
        return sum(self._blocked_recent)

    @property
    def static(self) -> Optional[tuple]:
        """Phần ngữ cảnh chỉ đổi khi chốt nến khung lớn (bộ bất biến): (ready, order, order_age_bars, protected,
        protected_broken, nến khung nhỏ biết lần chốt gần nhất, coverage_last, blocked_windows_recent, hi, lo)."""
        return self._static

    @staticmethod
    def zone_of(st: Optional[tuple], close: Optional[float]) -> tuple[Optional[str], Optional[float]]:
        """Vùng premium/discount và vị trí của close khung nhỏ trong dealing range khung lớn đã chốt (công thức
        ``DealingRange.snapshot``). Vị trí có thể < 0 hoặc > 1 khi giá đã ra ngoài từ lần chốt gần nhất."""
        if st is None or close is None or st[8] is None:
            return None, None
        hi, lo = st[8], st[9]
        eq = (hi + lo) / 2.0
        zone = "premium" if close > eq else ("discount" if close < eq else "eq")
        return zone, ((close - lo) / (hi - lo) if hi > lo else 0.5)

    @staticmethod
    def context_from(st: Optional[tuple], close: Optional[float], t: Optional[int], liq_above: Optional[float],
                     liq_below: Optional[float]) -> dict[str, Any]:
        """Ảnh chụp gọn ``details.htf[khung]`` (plan §11.5) sau nến khung nhỏ t (close = close[t])."""
        if st is None:
            return {"ready": False, "order": None, "order_age_bars": None, "protected": None,
                    "protected_broken": None, "zone": None, "range_pos": None, "liq_above": liq_above,
                    "liq_below": liq_below, "age_ltf_bars": None, "coverage_last": None, "blocked_windows_recent": 0}
        ready, order, age, prot, broken, known, cov, blocked, _hi, _lo = st
        zone, pos = HtfStack.zone_of(st, close)
        return {
            "ready": ready, "order": order, "order_age_bars": age, "protected": prot, "protected_broken": broken,
            "zone": zone, "range_pos": pos, "liq_above": liq_above, "liq_below": liq_below,
            "age_ltf_bars": (t - known) if t is not None else None, "coverage_last": cov,
            "blocked_windows_recent": blocked,
        }

    def context(self, close: Optional[float], t: Optional[int], liq_above: Optional[float],
                liq_below: Optional[float]) -> dict[str, Any]:
        return self.context_from(self._static, close, t, liq_above, liq_below)
