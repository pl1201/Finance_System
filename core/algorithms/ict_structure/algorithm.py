"""Bộ nhận diện cấu trúc ICT phân tầng — giai đoạn 3 lõi: khung lớn, PD array, DOL; order block, OTE (``ict_structure`` v0.5.0).

Đặc tả: ``docs/algorithms/thuat_toan_ict_structure.md`` (lập từ ``docs/plans/plan_ict_structure.md``,
quyết định D1–D15 duyệt 04/10/2026).

Giai đoạn 1:

* **[G]** lịch phiên khai báo + phân loại khoảng trống → ``ICT_GAP``;
* **[A]** ATR Wilder (seed theo close trước); giá trị của nến TRƯỚC làm ngưỡng cho nến hiện tại;
* **[P1]** STH/STL — pivot strict ``pivot_left``/``pivot_right`` (1/1), chặn cửa sổ vắt qua gap (D1);
* **[S1]** ITH/ITL (cấp 2), tuỳ chọn LTH/LTL (cấp 3);
* **[S2]** thứ tự đỉnh/đáy ``order`` + mức được bảo vệ + ``protected_broken`` (không phát sự kiện);
* **[S4]** dealing range, premium / discount.

Giai đoạn 2:

* **[P3]** displacement → ``DISPLACEMENT_UP/DOWN``;
* **[P2]** FVG M15 → ``FVG_UP/DOWN``, vòng đời ``FVG_TOUCHED`` / ``FVG_FILLED``;
* **[S3]/[E2]** vùng thanh khoản từ ITH/ITL M15 (EQH/EQL gộp) và vòng đời chạm → lấy →
  ``LIQ_SWEEP_*`` / ``LIQ_RUN_*`` / ``LIQ_UNRESOLVED``;
* **[E3]** shift = sweep → displacement ngược chiều → ``SHIFT_UP/DOWN``, ``SHIFT_FVG_UP/DOWN``,
  chung ``group_id`` với sweep;
* **[C]** killzone theo giờ New York — chỉ là cờ ``details.killzone`` / timeline.

Order flow (v0.3.0, người dùng chốt 06/10/2026 — ``docs/research/nghien_cuu_orderflow_ict.md``):

* **[OF]** order flow đọc theo thanh khoản: chỉ từ ``LIQ_RUN_*`` và ``SHIFT_*`` đã xác nhận ở nến t;
  shift đặt chiều (lật thẳng), run đặt chiều khi chưa có / chưa rõ / cùng chiều, run phía ngược →
  chưa rõ, hai chiều cùng nến → chưa rõ (quy tắc A, ``core/components/order_flow.py``) →
  ``ORDER_FLOW_UP/DOWN/UNCLEAR`` khi trạng thái đổi; timeline ``order_flow`` / ``order_flow_since`` /
  ``order_flow_reason``. Là mô tả theo thanh khoản, không phải tín hiệu.

Giai đoạn 3 — lõi (v0.4.0, plan §10 dòng 3, §11; giao diện lớp phủ H4 để sau):

* **[T0]** bộ gộp tuần tự ``ny_1700`` + lịch phiên khai báo (``core/data/htf_stream.SessionHtfAggregator``):
  nến H1/H4/ngày/tuần chốt khi nến khung chạy đóng đúng ``period_end`` (thiếu nến cuối → khi kỳ sau mở),
  ``known_at`` riêng, ``coverage``, ``degraded`` / ``over`` / ``after_hole`` → ``HTF_BAR_DEGRADED``;
* **[T1]** ngăn xếp H1, H4 (``core/components/htf_stack.py``): chính P1 → S1 → S2, S4, FVG trên nến khung lớn
  đã chốt, ATR riêng; nến degraded / hole chặn cửa sổ → ``HTF_SWING_*``, ``HTF_FVG_*``;
* **[T2]** PDH/PDL, PWH/PWL (``HTF_PERIOD_*``), giá mở ngày, midnight open (``period_levels.py``);
* **[S3]** vùng thanh khoản thêm tầng H1, H4 (ITH/ITL khung lớn), D, W (mức theo kỳ) — cùng vòng đời §4.9;
* **[S5]** phản ứng của close M15 ở FVG H1/H4 → ``PD_RESPECT_*`` / ``PD_DISRESPECT_*``, ``pd_bias``
  (``pd_array.py``); **[S6]** DOL sau mỗi shift → ``DOL_REACHED`` (``dol.py``);
* **[T3]** ``details.htf`` (ảnh chụp gọn, bất biến) trên mọi sự kiện khung chạy, cột timeline phẳng.

Thứ tự trong một nến t (cố định, plan §3.1):

1. kiểm nến; phân loại khoảng trống trước t → ``ICT_GAP``;
2. ATR[t−1] dùng cho mọi ngưỡng của nến t;
3. [E2] vùng đã biết **trước** t (mọi tầng): vùng đang chờ (quay lại / hết cửa sổ / gặp gap), rồi vùng
   còn nguyên (chạm / lấy, xét quay lại ngay trong t) → sweep sinh ứng viên shift;
4. [P3] displacement của t;
5. [P2] chạm/lấp của FVG đã biết trước t; FVG với nến 3 = t;
6. [E3] ứng viên shift (kể cả ứng viên vừa sinh ở bước 3) → ``SHIFT``; shift ở t−1 + FVG ở t có
   nến giữa t−1 → ``SHIFT_FVG``;
6b. [OF] run (bước 3) và shift (bước 6) xác nhận ở t → cập nhật order flow → ``ORDER_FLOW_*`` nếu đổi;
7. [S5] phản ứng của nến t ở các FVG khung lớn đã biết trước t → ``PD_*``, ``pd_bias``;
8. [S2] close[t] so với mức được bảo vệ đã biết trước t; [S4] mở rộng dealing range theo t;
9. [P1] pivot xác nhận tại t → [S1] cấp 2 → cấp 3 → [S2] thứ tự/mức được bảo vệ, [S4] mốc mới và
   [S3] vùng thanh khoản mới từ ITH/ITL — tất cả có hiệu lực từ t+1;
10. [S6] DOL: đích bị lấy ở bước 3 → ``DOL_REACHED``; shift ở bước 6 → DOL mới;
11. [T] nến khung lớn chốt tại t → ngăn xếp H1/H4, vùng/FVG/mức mới (hiệu lực từ t+1), ``HTF_*``; giá mở
    ngày / midnight open;
12. cập nhật ATR[t]; [T3] ảnh chụp ngữ cảnh sau t → timeline nến t và ``details.htf`` của sự kiện ở t+1.

Sự kiện ở nến t mang ngữ cảnh khung lớn đã chốt **≤ t−1** (ảnh chụp lập ở bước 12 của nến t−1): một nến
không thể vừa lật ngữ cảnh khung lớn vừa được đọc là «trong» ngữ cảnh mới.

Không có BOS/CHoCH/MSS (B1); ba thành phần bias (thứ tự, ``pd_bias``, DOL) không được ghép (B3).

v0.5.0 — order block và OTE neo vào SHIFT (``docs/plans/plan_ket_hop_ict_indicator.md`` §3.4, duyệt 21/10/2026; luồng
``docs/guides/kien_truc_luong_ict.md`` §4.4). Ba bước chèn vào thứ tự trên, sự kiện cũ không đổi:

* **3b** OB / nhịp OTE đã biết TRƯỚC t: chạm / hỏng / hết hạn → ``OB_TAP_*``, ``OB_FAIL_*``, ``OB_EXPIRED``; vào vùng
  62–79% / thủng gốc nhịp / hết hạn → ``OTE_ENTRY_*``, ``OTE_FAIL_*``, ``OTE_EXPIRED``
  (``core/components/order_block.py``, ``core/components/ote.py``);
* **6c** SHIFT xác nhận ở t → OB từ chuỗi nến ngược màu cuối trong [nến lấy − ob_lui, t − 1] (``ORDER_BLOCK_*``) và nhịp
  OTE mới (gốc = cực trị cú quét); SHIFT ngược chiều → OB chưa chạm của chiều cũ hết hạn, SHIFT mới thay nhịp đang chờ;
* **12b** nhịp OTE đang chờ: đầu nhịp theo cực trị của nến t (dùng từ t + 1).
"""
from __future__ import annotations

import copy
import functools
import math
from collections import deque
from datetime import timedelta
from typing import Any, Optional

from core.algorithms.base import ParamSpec, StructureAlgorithm
from core.algorithms.ict_structure import digest
from core.algorithms.ict_structure import nhan_dien as nd
from core.algorithms.ict_structure.eval_targets import EVAL_TARGETS, SHIFT_TYPES
from core.components.dealing_range import DealingRange
from core.components.displacement import Displacement
from core.components.dol import TIERS as DOL_TIERS
from core.components.dol import DrawOnLiquidity
from core.components.fvg import Fvg, FvgTracker
from core.components.hierarchy import HierarchyLevel
from core.components.htf_stack import BLOCKED_RECENT_BARS, HtfStack
from core.components.killzone import DEFAULT_KILLZONES, Killzones
from core.components.liquidity import TIER_RANK, LiquidityBook, Pool
from core.components.order_block import ANCHORS as OB_ANCHORS
from core.components.order_block import END_TEXT_VI as OB_END_VI
from core.components.order_block import VARIANTS as OB_VARIANTS
from core.components.order_block import OrderBlock, OrderBlockTracker
from core.components.ote import END_TEXT_VI as OTE_END_VI
from core.components.ote import OteLeg, OteTracker
from core.components.order_flow import (
    BOTH_SIDES,
    FLOW_KEYS,
    FLOW_REASON_VI,
    FLOW_TEXT_VI,
    OPPOSITE_RUN,
    REASONS,
    RUN,
    RUN_DOWN,
    RUN_UP,
    SHIFT,
    SHIFT_DOWN,
    SHIFT_UP,
    OrderFlow,
)
from core.components.pd_array import MODES as PD_MODES
from core.components.pd_array import PdArrayTracker, PdZone
from core.components.period_levels import NAMES as LEVEL_NAMES
from core.components.period_levels import PeriodLevels
from core.components.rolling_stats import quantile
from core.components.session_gap import GAP_KINDS, GAP_TEXT_VI, GapClassifier
from core.components.shift import ShiftCandidate, ShiftTracker
from core.components.structure_order import ORDER_TEXT_VI, StructureOrder
from core.components.swing_source import Pivot, PivotSource, with_event_id
from core.data.htf_stream import ALIGNMENT_NY_1700, HtfBar, SessionHtfAggregator
from core.data.session_calendar import (
    CAL_AUTO,
    CAL_NONE,
    CUOI_TUAN,
    DEFAULT_FOR_SYMBOL,
    NGHI_LE,
    NGHI_PHIEN,
    THIEU_TRONG_PHIEN,
    SessionCalendar,
)
from core.indicators import WilderATRPrevClose
from core.types import TIMEFRAME_SECONDS, Bar, ReasonCode, StructureEvent, StructureType

SPEC = "docs/algorithms/thuat_toan_ict_structure.md"
CALENDARS = (CAL_AUTO,) + tuple(sorted(set(DEFAULT_FOR_SYMBOL.values()))) + (CAL_NONE,)
GAP_BLOCK = "giu_muc_chan_cua_so"
GAP_NO_BLOCK = "giu_muc_khong_chan"
#: Tầng của vùng thanh khoản lấy từ ITH/ITL của chính khung chạy (nhãn «M15» = khung chạy).
POOL_LEVEL = 2
POOL_TIER = "M15"
#: [T] khung lớn có ngăn xếp cấu trúc (plan §11, D9) và khung chỉ cho mức theo kỳ (D/W).
HTF_FRAMES = ("H1", "H4")
LEVEL_FRAMES = ("D", "W")
HTF_EMIT = "an"
HTF_NO_EMIT = "khong_phat"
#: Khung chạy lớn nhất còn gộp được khung lớn: mốc ny_1700 nằm trên giờ tròn.
MAX_LTF_SECONDS_FOR_HTF = 3600

_TYPES = {
    (1, "high"): (StructureType.SWING_HIGH, ReasonCode.PIVOT_HIGH_STRICT, "STH"),
    (1, "low"): (StructureType.SWING_LOW, ReasonCode.PIVOT_LOW_STRICT, "STL"),
    (2, "high"): (StructureType.SWING_HIGH_L2, ReasonCode.PIVOT_HIGH_L2, "ITH"),
    (2, "low"): (StructureType.SWING_LOW_L2, ReasonCode.PIVOT_LOW_L2, "ITL"),
    (3, "high"): (StructureType.SWING_HIGH_L3, ReasonCode.PIVOT_HIGH_L3, "LTH"),
    (3, "low"): (StructureType.SWING_LOW_L3, ReasonCode.PIVOT_LOW_L3, "LTL"),
}
_GAP_REASON = {
    NGHI_PHIEN: ReasonCode.GAP_NGHI_PHIEN,
    CUOI_TUAN: ReasonCode.GAP_CUOI_TUAN,
    NGHI_LE: ReasonCode.GAP_NGHI_LE,
    THIEU_TRONG_PHIEN: ReasonCode.GAP_THIEU_TRONG_PHIEN,
    "ngoai_lich": ReasonCode.GAP_NGOAI_LICH,
    "khong_ro_lich": ReasonCode.GAP_KHONG_RO_LICH,
    "lech_buoc": ReasonCode.GAP_THIEU_TRONG_PHIEN,
}
#: (kết cục, phía vùng) → (loại sự kiện, lý do, hướng). Phía "high" = BSL.
_LIQ = {
    ("sweep", "high"): (StructureType.LIQ_SWEEP_BSL, ReasonCode.LIQ_TAKEN_THEN_CLOSE_BACK, "down"),
    ("sweep", "low"): (StructureType.LIQ_SWEEP_SSL, ReasonCode.LIQ_TAKEN_THEN_CLOSE_BACK, "up"),
    ("run", "high"): (StructureType.LIQ_RUN_UP, ReasonCode.LIQ_TAKEN_NO_RETURN, "up"),
    ("run", "low"): (StructureType.LIQ_RUN_DOWN, ReasonCode.LIQ_TAKEN_NO_RETURN, "down"),
    ("unresolved", "high"): (StructureType.LIQ_UNRESOLVED, ReasonCode.LIQ_GAP_IN_WINDOW, None),
    ("unresolved", "low"): (StructureType.LIQ_UNRESOLVED, ReasonCode.LIQ_GAP_IN_WINDOW, None),
}
_LIQ_ORDER = tuple(_LIQ)
_SIDE_NAME = {"high": "BSL", "low": "SSL"}
MAX_ABNORMAL_LISTED = 50
#: [OF] đầu vào order flow: loại sự kiện → (loại, chiều). Không dùng sweep/FVG/displacement/HH-HL.
_OF_INPUT = {
    StructureType.LIQ_RUN_UP: (RUN, 1),
    StructureType.LIQ_RUN_DOWN: (RUN, -1),
    StructureType.SHIFT_UP: (SHIFT, 1),
    StructureType.SHIFT_DOWN: (SHIFT, -1),
}
#: [OF] giá trị mới → (loại sự kiện, hướng); mã chữ thường của lần đổi → ReasonCode.
_OF_EVENT = {
    1: (StructureType.ORDER_FLOW_UP, "up"),
    -1: (StructureType.ORDER_FLOW_DOWN, "down"),
    0: (StructureType.ORDER_FLOW_UNCLEAR, None),
}
_OF_REASON = {
    RUN_UP: ReasonCode.OF_RUN, RUN_DOWN: ReasonCode.OF_RUN,
    SHIFT_UP: ReasonCode.OF_SHIFT, SHIFT_DOWN: ReasonCode.OF_SHIFT,
    OPPOSITE_RUN: ReasonCode.OF_OPPOSITE_RUN, BOTH_SIDES: ReasonCode.OF_BOTH_SIDES,
}
_HTF_TYPESET = frozenset(StructureType.HTF_TYPES)
# 0.4.1: sự kiện «nguyên liệu» khung chạy (STH/STL, FVG M15 + vòng đời, displacement) không mang details.htf — chiếm
# ~35% JSON sự kiện; ngữ cảnh khung lớn vẫn có đủ ở timeline từng nến và trên các sự kiện cấu trúc.
_NO_CTX_TYPESET = frozenset((
    StructureType.SWING_HIGH, StructureType.SWING_LOW, StructureType.FVG_UP, StructureType.FVG_DOWN,
    StructureType.FVG_TOUCHED, StructureType.FVG_FILLED, StructureType.DISPLACEMENT_UP, StructureType.DISPLACEMENT_DOWN,
    StructureType.OB_EXPIRED, StructureType.OTE_EXPIRED,      # 0.5.0: hết hạn chỉ để vẽ dừng đúng chỗ
))
#: [E4] OB mới theo chiều / biến thể; kết cục: loại = _OB_TYPE.get((kết cục, chiều), OB_EXPIRED), lý do = _OB_REASON.
_OB_NEW = {"up": StructureType.ORDER_BLOCK_UP, "down": StructureType.ORDER_BLOCK_DOWN}
_OB_NEW_REASON = {"than_chuoi": ReasonCode.OB_BODY_RUN, "nen_cuoi_rau": ReasonCode.OB_LAST_CANDLE_WICK}
_OB_TYPE = {("tap", "up"): StructureType.OB_TAP_UP, ("tap", "down"): StructureType.OB_TAP_DOWN,
            ("fail", "up"): StructureType.OB_FAIL_UP, ("fail", "down"): StructureType.OB_FAIL_DOWN}
_OB_REASON = {"tap": ReasonCode.OB_FIRST_TAP, "fail": ReasonCode.OB_CLOSE_BEYOND_FAR_EDGE,
              "expired_time": ReasonCode.OB_EXPIRED_TIME, "expired_shift": ReasonCode.OB_EXPIRED_OPPOSITE_SHIFT}
#: [E6] kết cục nhịp: loại = _OTE_TYPE.get((kết cục, chiều), OTE_EXPIRED), lý do = _OTE_REASON.
_OTE_TYPE = {("entry", "up"): StructureType.OTE_ENTRY_UP, ("entry", "down"): StructureType.OTE_ENTRY_DOWN,
             ("fail", "up"): StructureType.OTE_FAIL_UP, ("fail", "down"): StructureType.OTE_FAIL_DOWN}
_OTE_REASON = {"entry": ReasonCode.OTE_RETRACE_ZONE, "fail": ReasonCode.OTE_LEG_BROKEN,
               "expired_time": ReasonCode.OTE_EXPIRED_TIME, "expired_shift": ReasonCode.OTE_EXPIRED_SHIFT,
               "replaced": ReasonCode.OTE_EXPIRED_SHIFT}
#: Cột timeline OB / OTE khi không có OB mở và không có nhịp chờ (phần lớn nến) — dựng một lần.
_TL_OB_OTE_NONE = dict.fromkeys(("ob_up_hi", "ob_up_lo", "ob_down_hi", "ob_down_lo", "ote_dir", "ote_neo", "ote_x",
                                 "ote_h", "ote_lo", "ote_hi"))
_OF_NOTE_VI = (
    "Đọc theo thanh khoản: run + shift; run phía ngược → chưa rõ (chốt 06/10/2026). Mô tả, không phải "
    "dự báo — docs/research/nghien_cuu_orderflow_ict.md."
)


@functools.lru_cache(maxsize=8)
def _calendar(name: str) -> SessionCalendar:
    return SessionCalendar.load(name)


SESSION_SECONDS = {"H1": 3600, "H4": 4 * 3600}


def _parse_htf_list(text: Any) -> tuple[str, ...]:
    """``"H1,H4"`` → ("H1", "H4") theo thứ tự khung; rỗng → (). Khung lạ / trùng → ``ValueError``."""
    items = [x.strip().upper() for x in str(text or "").split(",") if x.strip()]
    for x in items:
        if x not in HTF_FRAMES:
            raise ValueError("htf_list: khung %r không hỗ trợ — chọn trong %s (rỗng = tắt)." % (x, list(HTF_FRAMES)))
    if len(set(items)) != len(items):
        raise ValueError("htf_list: khung bị lặp (%s)." % ",".join(items))
    return tuple(f for f in HTF_FRAMES if f in items)


def _shift_main(direction: str, cands: list[ShiftCandidate]) -> ShiftCandidate:
    """Ứng viên «chính» của một shift (nhiều sweep cùng dẫn tới một displacement): tầng cao nhất, sweep gần nhất, mức xa."""
    down = direction == "down"
    return max(cands, key=lambda c: (TIER_RANK.get(c.tier, 0), c.r, c.level if down else -c.level))


def _quantile(sorted_vals: list[float], q: float) -> Optional[float]:
    return quantile(sorted_vals, q) if sorted_vals else None


class IctStructureAlgorithm(StructureAlgorithm):
    name = "ict_structure"
    display_name_vi = "Cấu trúc ICT phân tầng + khung lớn + order flow"
    version = "0.9.3"
    emits_types = (
        StructureType.SWING_HIGH, StructureType.SWING_LOW,
        StructureType.SWING_HIGH_L2, StructureType.SWING_LOW_L2,
        StructureType.SWING_HIGH_L3, StructureType.SWING_LOW_L3,
        StructureType.ICT_GAP,
        StructureType.DISPLACEMENT_UP, StructureType.DISPLACEMENT_DOWN,
        StructureType.FVG_UP, StructureType.FVG_DOWN, StructureType.FVG_TOUCHED, StructureType.FVG_FILLED,
        StructureType.LIQ_SWEEP_BSL, StructureType.LIQ_SWEEP_SSL,
        StructureType.LIQ_RUN_UP, StructureType.LIQ_RUN_DOWN, StructureType.LIQ_UNRESOLVED,
        StructureType.SHIFT_UP, StructureType.SHIFT_DOWN,
        StructureType.SHIFT_FVG_UP, StructureType.SHIFT_FVG_DOWN,
        StructureType.ORDER_FLOW_UP, StructureType.ORDER_FLOW_DOWN, StructureType.ORDER_FLOW_UNCLEAR,
        StructureType.PD_RESPECT_UP, StructureType.PD_RESPECT_DOWN,
        StructureType.PD_DISRESPECT_UP, StructureType.PD_DISRESPECT_DOWN, StructureType.DOL_REACHED,
    ) + StructureType.HTF_TYPES + StructureType.OB_TYPES + StructureType.OTE_TYPES + StructureType.STATE_TYPES
    label_types = SHIFT_TYPES
    eval_targets = EVAL_TARGETS
    description_vi = (
        "Bộ nhận diện ICT trên một khung: STH/STL → ITH/ITL → thứ tự đỉnh/đáy, mức được bảo vệ, dealing "
        "range; displacement, FVG; vùng thanh khoản ITH/ITL với vòng đời chạm → lấy → sweep/run; shift = "
        "sweep rồi displacement ngược chiều (+ SHIFT_FVG); order flow đọc theo thanh khoản (run + shift, "
        "run phía ngược → chưa rõ) — mô tả, không phải tín hiệu. Khung lớn H1/H4 gộp nội bộ (mốc 17:00 New York, "
        "lịch phiên, chỉ nến đã chốt): ITH/ITL, thứ tự, dealing range, FVG; PDH/PDL, PWH/PWL; vùng khung lớn làm "
        "vùng thanh khoản; phản ứng ở FVG khung lớn (pd_bias), DOL sau shift — là đặc trưng, không lọc sự kiện. "
        "Order block (chuỗi nến ngược màu cuối trước displacement của shift) và OTE (vùng hồi 62–79% của nhịp sau "
        "shift) với vòng đời chạm / hỏng / hết hạn — mô tả, chưa phải tín hiệu. Không có BOS/CHoCH."
    )

    @classmethod
    def param_specs(cls) -> tuple[ParamSpec, ...]:
        # Chữ trên form: ngắn, lời thường, nói «tăng / giảm thì sao». Định nghĩa đầy đủ ở đặc tả §3–§4; số đo độ nhạy ở
        # docs/guides/gioi_thieu_thuat_toan.md §3.3. advanced=True → mục «Tham số nâng cao» gập sẵn (cấu hình dữ liệu,
        # chỉ để đối chiếu, hoặc gần như không đổi kết quả). Chỉ đổi hiển thị — không đổi output, không đổi phiên bản.
        return (
            # --- cấu trúc: đỉnh/đáy
            ParamSpec("pivot_left", "Số nến trái (STH/STL)", "int", 1, min=1, max=10, step=1,
                      help_vi="Đỉnh phải cao hơn bấy nhiêu nến bên trái. Tăng → ít đỉnh/đáy hơn."),
            ParamSpec("pivot_right", "Số nến phải (STH/STL)", "int", 1, min=1, max=10, step=1,
                      help_vi="Đỉnh phải cao hơn bấy nhiêu nến bên phải — cũng là số nến phải chờ mới biết. "
                              "Tăng → ít đỉnh hơn, biết trễ hơn."),
            ParamSpec("structure_level", "Cấp cấu trúc", "int", 2, min=1, max=3, step=1,
                      help_vi="Đỉnh/đáy cấp nào dùng cho thứ tự HH/HL, mức bảo vệ, range. 1 = mọi đỉnh nhỏ (nhiễu), "
                              "2 = ITH/ITL (mặc định), 3 = đỉnh lớn (biết trễ ~23 nến)."),
            ParamSpec("eq_tol_atr", "Dung sai bằng giá (× ATR)", "float", 0.1, min=0.0, max=5.0, step=0.05,
                      help_vi="Hai đỉnh chênh nhau ít hơn mức này coi là bằng nhau (EQH/EQL) và gộp thành một vùng "
                              "thanh khoản. Tăng → nhiều đỉnh «bằng» hơn."),
            # --- displacement, FVG
            ParamSpec("k_disp", "Displacement: biên độ ≥ k × ATR", "float", 1.5, min=0.1, max=10.0, step=0.1,
                      help_vi="Nến phải dài ít nhất k lần ATR mới là displacement. Tăng → ít displacement, ít shift."),
            ParamSpec("body_min", "Displacement: thân ≥ tỷ lệ biên độ", "float", 0.6, min=0.0, max=1.0, step=0.05,
                      help_vi="Thân nến phải chiếm ít nhất tỷ lệ này của cả cây nến. Tăng → chỉ tính nến «đặc»."),
            ParamSpec("fvg_min_atr", "FVG: kích thước tối thiểu (× ATR)", "float", 0.0, min=0.0, max=5.0,
                      step=0.05, help_vi="Bỏ FVG nhỏ hơn mức này. 0 = giữ mọi FVG; 0,25 bớt khoảng một nửa."),
            # --- thanh khoản, shift
            ParamSpec("min_pen_atr", "Ngưỡng «lấy» thanh khoản (× ATR)", "float", 0.1, min=0.0, max=5.0,
                      step=0.05, help_vi="Giá phải vượt mức ít nhất bấy nhiêu mới tính là lấy (ít hơn chỉ là chạm). "
                                         "Tăng → ít lượt lấy, nhiều run hơn."),
            ParamSpec("sweep_window", "Cửa sổ sweep W (nến)", "int", 3, min=0, max=50, step=1,
                      help_vi="Lấy xong mà đóng cửa quay lại trong W nến → sweep, không quay lại → run. "
                              "Tăng → nhiều sweep hơn, run biết trễ hơn."),
            ParamSpec("shift_window", "Cửa sổ shift (nến)", "int", 3, min=0, max=50, step=1,
                      help_vi="Sau sweep, displacement ngược chiều phải đến trong bấy nhiêu nến mới thành shift. "
                              "Tăng → nhiều shift hơn."),
            # --- khung lớn
            ParamSpec("htf_list", "Khung lớn", "str", ",".join(HTF_FRAMES),
                      help_vi="H1, H4 dựng từ chính nến đang chạy, chỉ dùng nến đã đóng. Để trống = tắt phần khung lớn."),
            # --- nâng cao: cấu hình dữ liệu / đối chiếu / ít ảnh hưởng
            ParamSpec("timeframe", "Khung của dataset", "choice", "M15", choices=tuple(TIMEFRAME_SECONDS),
                      advanced=True, help_vi="Tự điền theo dataset — không cần chỉnh."),
            ParamSpec("session_calendar", "Lịch phiên", "choice", CAL_AUTO, choices=CALENDARS, advanced=True,
                      choice_labels_vi=((CAL_AUTO, "tự chọn theo mã"), ("cme_globex_metals", "CME kim loại (vàng)"),
                                        ("fx_spot", "FX (EURUSD…)"), (CAL_NONE, "không dùng lịch")),
                      help_vi="Giờ mở/đóng phiên, để phân biệt giờ nghỉ với dữ liệu thiếu. «Tự chọn»: vàng → CME, "
                              "EURUSD → FX."),
            ParamSpec("atr_period", "Chu kỳ ATR", "int", 14, min=2, max=500, step=1, advanced=True,
                      help_vi="Số nến tính ATR — thước đo biến động dùng cho mọi ngưỡng «× ATR». Đổi 7 hay 28 gần như "
                              "không đổi kết quả."),
            ParamSpec("gap_policy", "Khoảng trống dữ liệu", "choice", GAP_BLOCK, choices=(GAP_BLOCK, GAP_NO_BLOCK),
                      advanced=True,
                      choice_labels_vi=((GAP_BLOCK, "chặn chỗ thiếu (mặc định)"),
                                        (GAP_NO_BLOCK, "không chặn (để đối chiếu)")),
                      help_vi="Mặc định: không tìm đỉnh/đáy vắt qua chỗ thiếu dữ liệu. Lựa chọn kia chỉ để so với "
                              "thuật toán swing cũ."),
            ParamSpec("killzones", "Killzone (giờ New York)", "str", DEFAULT_KILLZONES, advanced=True,
                      help_vi="Chỉ là nhãn giờ ghi vào sự kiện, không lọc gì. Dạng ten=giờ-giờ, cách nhau dấu phẩy."),
            ParamSpec("htf_alignment", "Mốc nến khung lớn", "choice", ALIGNMENT_NY_1700, choices=(ALIGNMENT_NY_1700,),
                      advanced=True, choice_labels_vi=((ALIGNMENT_NY_1700, "17:00 New York"),),
                      help_vi="Ngày giao dịch bắt đầu 17:00 giờ New York (như nến ngày của broker FX). Chỉ có một "
                              "lựa chọn."),
            ParamSpec("htf_min_coverage", "Độ đủ dữ liệu nến khung lớn", "float", 0.9, min=0.0, max=1.0,
                      step=0.05, advanced=True,
                      help_vi="Nến H1/H4/ngày có ít hơn tỷ lệ này số nến con theo lịch → coi là thiếu dữ liệu, không "
                              "dùng."),
            ParamSpec("period_levels", "PDH/PDL, PWH/PWL là vùng thanh khoản", "bool", True, advanced=True,
                      help_vi="Đỉnh/đáy ngày trước và tuần trước thành vùng BSL/SSL."),
            ParamSpec("htf_events", "Sự kiện khung lớn trong bảng", "choice", HTF_EMIT,
                      choices=(HTF_EMIT, HTF_NO_EMIT), advanced=True,
                      choice_labels_vi=((HTF_EMIT, "có (ẩn trên chart)"), (HTF_NO_EMIT, "không ghi")),
                      help_vi="Có ghi đỉnh/đáy, FVG, mức ngày/tuần của khung lớn vào bảng sự kiện không. Không đổi "
                              "phần còn lại."),
            ParamSpec("pd_respect_mode", "Phản ứng ở FVG khung lớn", "choice", "strict", choices=PD_MODES,
                      advanced=True,
                      choice_labels_vi=(("strict", "chặt"), ("loose", "lỏng"), ("ce", "theo 50% vùng (CE)")),
                      help_vi="Cách tính giá «tôn trọng» FVG H1/H4 (cho pd_bias). Chặt: phải rời FVG đủ xa."),
            ParamSpec("respect_away_atr", "Tôn trọng chặt: rời FVG ≥ k × ATR", "float", 1.0, min=0.0, max=10.0,
                      step=0.1, show_if=("pd_respect_mode", "strict"), advanced=True,
                      help_vi="Giá phải rời mép FVG khung lớn bấy nhiêu ATR mới tính là tôn trọng."),
            ParamSpec("dol_min_tier", "DOL: tầng vùng tối thiểu", "choice", "H1", choices=DOL_TIERS, advanced=True,
                      choice_labels_vi=(("H1", "H1"), ("H4", "H4"), ("D", "ngày (PDH/PDL)"), ("W", "tuần (PWH/PWL)")),
                      help_vi="Đích DOL sau shift chỉ lấy vùng từ tầng này trở lên. Cao hơn → đích xa hơn."),
            # --- nâng cao: order block, OTE (v0.5.0, plan_ket_hop_ict_indicator.md §3.4)
            ParamSpec("ob_bien_the", "Order block: lấy nến nào", "choice", "than_chuoi", choices=OB_VARIANTS,
                      advanced=True,
                      choice_labels_vi=(("than_chuoi", "chuỗi nến ngược màu cuối, chỉ thân (gốc ICT)"),
                                        ("nen_cuoi_rau", "một nến cuối, cả râu (SMC)")),
                      help_vi="Cách lấy vùng OB trước displacement của shift."),
            ParamSpec("ob_neo", "Order block: neo vào", "choice", "shift", choices=OB_ANCHORS, advanced=True,
                      choice_labels_vi=(("shift", "SHIFT (mặc định)"),
                                        ("displacement", "mọi displacement có close vượt các nến trước (nhiều OB hơn)")),
                      help_vi="Mốc tạo OB. Neo displacement: close phải vượt đỉnh/đáy của «lùi thêm» nến trước; "
                              "nhiều OB hơn khoảng 5 lần — để đối chứng."),
            ParamSpec("ob_lui", "Order block: lùi thêm (nến)", "int", 5, min=1, max=20, step=1, advanced=True,
                      help_vi="Tìm nến ngược màu từ nến lấy thanh khoản lùi thêm bấy nhiêu nến."),
            ParamSpec("ob_han", "Order block: hạn chờ chạm (nến)", "int", 96, min=1, max=2000, step=1, advanced=True,
                      help_vi="Quá bấy nhiêu nến chưa chạm thì OB hết hạn (96 nến M15 = 24 giờ)."),
            ParamSpec("ote_tu", "OTE: mức hồi từ", "float", 0.62, min=0.01, max=0.99, step=0.01, advanced=True,
                      help_vi="Giá hồi tới mức này của nhịp sau shift là vào vùng OTE."),
            ParamSpec("ote_den", "OTE: mức hồi đến", "float", 0.79, min=0.02, max=1.0, step=0.01, advanced=True,
                      help_vi="Mép xa của vùng OTE. Phải lớn hơn «mức hồi từ»."),
            ParamSpec("ote_nhip_min_atr", "OTE: nhịp tối thiểu (× ATR)", "float", 2.0, min=0.0, max=20.0, step=0.5,
                      advanced=True, help_vi="Nhịp nhỏ hơn bấy nhiêu ATR thì chưa có vùng OTE."),
            ParamSpec("ote_han", "OTE: hạn chờ hồi (nến)", "int", 96, min=1, max=2000, step=1, advanced=True,
                      help_vi="Quá bấy nhiêu nến chưa hồi vào vùng thì nhịp hết hạn."),
            # --- nâng cao: lớp nhận diện (v0.6.0, thuat_toan_nhan_dien.md)
            *nd.PARAMS,
        )

    @classmethod
    def validate_params(cls, raw: dict[str, Any] | None) -> dict[str, Any]:
        p = super().validate_params(raw)
        Killzones(p["killzones"])           # sai dạng → ValueError có thông điệp tiếng Việt
        p["htf_list"] = ",".join(_parse_htf_list(p["htf_list"]))
        if not p["ote_tu"] < p["ote_den"]:
            raise ValueError("OTE: «mức hồi từ» (%s) phải nhỏ hơn «mức hồi đến» (%s)." % (p["ote_tu"], p["ote_den"]))
        nd.validate(p)                      # [N] ràng buộc liên trường của nd_* (dựng thử thành phần)
        return p

    @classmethod
    def check_dataset(cls, timeframe: str, params: dict[str, Any]) -> None:
        if (timeframe or "").upper() != params.get("timeframe"):
            raise ValueError(
                "ict_structure: tham số timeframe=%s không khớp dataset %s. Chọn lại khung trong form "
                "(dùng để phân loại khoảng trống)." % (params.get("timeframe"), timeframe)
            )

    @classmethod
    def manifest_info(cls, params: dict[str, Any]) -> dict[str, Any]:
        cal = params.get("session_calendar") or CAL_AUTO
        cal_info: dict[str, Any] = {"ten": cal}
        if cal not in (CAL_AUTO, CAL_NONE):
            meta = _calendar(cal).meta
            cal_info.update({k: meta.get(k) for k in ("nguon", "nguon_ngoai_le", "timezone", "so_phien", "created")})
        return {
            "spec": SPEC,
            "giai_doan": "3 (lõi) — giai đoạn 1 ([G] [P1] [S1] [S2] [S4]) + 2 ([P3] [P2] [S3]/[E2] [E3] [C]) + "
                         "[OF] order flow theo thanh khoản (v0.3.0) + [T] khung lớn H1/H4 ny_1700, PDH/PDL/PWH/PWL, "
                         "[S5] phản ứng FVG khung lớn (pd_bias), [S6] DOL (v0.4.0)",
            "lich_phien": cal_info,
            "chinh_sach_khoang_trong": params.get("gap_policy"),
            "atr": "Wilder, seed SMA của period TR đầu có close trước (WilderATRPrevClose); ngưỡng ở nến t dùng ATR[t-1]",
            "vung_thanh_khoan": "ITH/ITL (cấp 2) của khung chạy, tầng %s; gộp EQH/EQL giữa hai swing liên tiếp" % POOL_TIER,
            "killzone": params.get("killzones"),
            "order_flow": (
                "Chỉ từ LIQ_RUN_* và SHIFT_* đã xác nhận ở nến t: shift đặt chiều (lật thẳng); run đặt chiều khi "
                "chưa có / chưa rõ, run phía ngược → chưa rõ; hai chiều cùng nến → chưa rõ (quy tắc A, chốt "
                "06/10/2026). Mô tả theo thanh khoản, không phải tín hiệu — docs/research/nghien_cuu_orderflow_ict.md"
            ),
            "khung_lon": {
                "khung": params.get("htf_list"),
                "moc": params.get("htf_alignment"),
                "coverage_toi_thieu": params.get("htf_min_coverage"),
                "muc_theo_ky_la_vung": params.get("period_levels"),
                "su_kien_htf": params.get("htf_events"),
                "chi_dung_nen_da_chot": True,
                "ghi_chu_vi": (
                    "Khung lớn gộp tuần tự từ chính luồng nến (ny_1700, lịch phiên khai báo); sự kiện ở nến t dùng "
                    "ngữ cảnh khung lớn đã chốt ≤ t−1. Là đặc trưng, không lọc sự kiện M15 (D11)."
                ),
            },
            "pd_array": {"che_do": params.get("pd_respect_mode"), "respect_away_atr": params.get("respect_away_atr"),
                         "nguon": "FVG H1/H4 hợp lệ (ba nến đã chốt, liền kề theo lịch, không degraded)"},
            "dol": {"tang_toi_thieu": params.get("dol_min_tier")},
            "order_block": {
                "bien_the": params.get("ob_bien_the"), "neo": params.get("ob_neo"), "lui": params.get("ob_lui"),
                "han_nen": params.get("ob_han"),
                "ghi_chu_vi": "Chuỗi nến ngược màu cuối trước displacement của SHIFT (lab không có MSS); chỉ lần chạm "
                              "đầu; hỏng khi close vượt mép xa. Mô tả — plan_ket_hop_ict_indicator.md §3.4.",
            },
            "ote": {
                "tu": params.get("ote_tu"), "den": params.get("ote_den"),
                "nhip_toi_thieu_atr": params.get("ote_nhip_min_atr"), "han_nen": params.get("ote_han"),
                "ghi_chu_vi": "Nhịp từ cực trị cú quét của SHIFT tới đỉnh/đáy mới (lấy tới nến trước); một nhịp chờ "
                              "tại một thời điểm, SHIFT mới thay nhịp. Mô tả — plan_ket_hop_ict_indicator.md §3.4.",
            },
            **({"nhan_dien": nd.manifest(params)} if params.get("nd_bat", True) else {}),
            "khong_co": "BOS/CHoCH/MSS (quyết định B1 — đổi hướng chỉ đến từ shift); bias tổng hợp (B3)",
        }

    def __init__(self, **params: Any) -> None:
        p = self.validate_params(params)
        self.params = p
        self.left = p["pivot_left"]
        self.right = p["pivot_right"]
        self.structure_level = p["structure_level"]
        self.step = timedelta(seconds=TIMEFRAME_SECONDS[p["timeframe"]])
        cal = p["session_calendar"]
        self.calendar_name = cal
        self.calendar: Optional[SessionCalendar] = None if cal in (CAL_AUTO, CAL_NONE) else _calendar(cal)
        self._kz = Killzones(p["killzones"])
        # [T] khung nào chạy được trên dataset này (mốc ny_1700 nằm trên giờ tròn → khung chạy ≤ H1)
        ltf_s = int(self.step.total_seconds())
        self.htf_on = ltf_s <= MAX_LTF_SECONDS_FOR_HTF and 3600 % ltf_s == 0
        wanted = _parse_htf_list(p["htf_list"])
        self.htf_frames = tuple(f for f in wanted if self.htf_on and SESSION_SECONDS[f] > ltf_s)
        self.htf_skipped = tuple(f for f in wanted if f not in self.htf_frames)
        self.level_frames = LEVEL_FRAMES if self.htf_on else ()
        self.emit_htf = p["htf_events"] == HTF_EMIT
        self.nd_horizons = nd.horizons_for(ltf_s)
        self.reset()

    def reset(self) -> None:
        p = self.params
        self._prev: Optional[Bar] = None
        self._atr = WilderATRPrevClose(p["atr_period"])
        self._gaps = GapClassifier(self.step, self.calendar)
        self._pivots = PivotSource(self.left, self.right, block_gaps=p["gap_policy"] == GAP_BLOCK)
        self._l2 = HierarchyLevel(2)
        self._l3 = HierarchyLevel(3) if self.structure_level >= 3 else None
        self._order = StructureOrder(p["eq_tol_atr"])
        self._range = DealingRange()
        self._disp = Displacement(p["k_disp"], p["body_min"])
        self._fvg = FvgTracker(p["fvg_min_atr"])
        self._liq = LiquidityBook(p["min_pen_atr"], p["sweep_window"], p["eq_tol_atr"])
        self._shift = ShiftTracker(p["shift_window"])
        self._of = OrderFlow()
        # [T] khung lớn, [S5] PD array, [S6] DOL
        frames = self.htf_frames + self.level_frames
        self._agg = (SessionHtfAggregator(int(self.step.total_seconds()), frames, p["htf_alignment"], self.calendar,
                                          p["htf_min_coverage"]) if frames else None)
        self._stacks = {f: HtfStack(f, self.left, self.right, p["atr_period"], p["eq_tol_atr"], p["k_disp"],
                                    p["body_min"], p["fvg_min_atr"]) for f in self.htf_frames}
        self._levels = PeriodLevels()
        self._pd = PdArrayTracker(p["pd_respect_mode"], p["respect_away_atr"])
        self._dol = DrawOnLiquidity(p["dol_min_tier"])
        # [E4] order block, [E6] OTE (0.5.0) — bộ đệm OB đủ cho [nến lấy − ob_lui, d − 1]
        self._ob = OrderBlockTracker(p["ob_bien_the"], p["ob_lui"], p["ob_han"],
                                     buffer=p["ob_lui"] + p["sweep_window"] + p["shift_window"] + 2)
        self._ob_anchor = p["ob_neo"]
        self._ote = OteTracker(p["ote_tu"], p["ote_den"], p["ote_nhip_min_atr"], p["ote_han"])
        self._ote_ob: Optional[OrderBlock] = None   # OB (hoặc ứng viên) cùng SHIFT với nhịp OTE đang chờ
        # [N] lớp nhận diện (0.6.0): khoảng giá + xác suất chạm, trạng thái
        self._nd = nd.NdLayer(p, self.nd_horizons, self.step.total_seconds()) if p["nd_bat"] else None
        self._htf_degraded: list[dict[str, Any]] = []
        self._htf_late: dict[str, list[float]] = {}
        self._htf_bars = {f: {"1": 0, "-1": 0, "0": 0, "none": 0, "ready": 0} for f in HTF_FRAMES}
        self._pd_bars = {"1": 0, "-1": 0, "0": 0, "none": 0}
        self._dol_bars = {"1": 0, "-1": 0, "none": 0, "co_dich": 0}
        # chuỗi theo vị trí nến trong run (Pivot.pos trỏ vào đây)
        self._highs: list[float] = []
        self._lows: list[float] = []
        self._atr_prev_hist: list[Optional[float]] = []
        self._recent: deque[Bar] = deque(maxlen=max(p["sweep_window"], 2) + 1)
        self._gap_prev_bar = False          # có khoảng trống ngay trước nến t−1 (cho FVG t−2..t)
        self._gap_now: Optional[dict[str, Any]] = None
        self._kz_now: Optional[str] = None
        self._disp_now: Optional[dict[str, Any]] = None
        self._disp_prev_dir: Optional[str] = None
        self._last_sweep: Optional[dict[str, Any]] = None
        self._last_shift: Optional[dict[str, Any]] = None
        self._emitted: set[str] = set()
        self._cur_index = -1                # chỉ số nến đang xử lý (đổi vị trí trong luồng ↔ chỉ số nến)
        # thống kê theo nến (đọc ở run_stats / pending_state)
        self._n = 0
        self._days: set[Any] = set()
        self._outside = 0
        self._gap_count = dict.fromkeys(GAP_KINDS, 0)
        self._abnormal: list[dict[str, Any]] = []
        self._order_bars = {"1": 0, "-1": 0, "0": 0, "none": 0}
        self._protected_bars = 0
        self._broken_bars = 0
        self._kz_bars: dict[str, int] = {}
        self._shift_kz: dict[str, int] = {}
        self._shift_tier: dict[str, int] = {}
        self._shift_on_take_bar = 0
        self._shift_on_sweep_bar = 0
        self._pool_status: dict[str, int] = {}
        # [OF] số nến theo trạng thái sau nến; các đoạn [giá trị, số nến] liên tiếp (bỏ đoạn None đầu run)
        self._of_bars = {k: 0 for k in FLOW_KEYS.values()}
        self._of_segs: list[list[int]] = []
        # [T3] ảnh chụp ngữ cảnh khung lớn sau nến trước — gắn vào details.htf của mọi sự kiện ở nến hiện tại
        self._levels_key: Optional[tuple] = None
        self._levels_ctx: Optional[dict[str, Any]] = None
        self._ctx_raw: tuple = self._capture_ctx(None)
        self._ctx: Optional[dict[str, Any]] = None       # dựng lười từ _ctx_raw ở sự kiện đầu tiên của nến

    def warmup_bars(self) -> int:
        return self.left + self.right + 1

    # ------------------------------------------------------------------ on_bar

    def _validate(self, bar: Bar) -> None:
        vals = (bar.open, bar.high, bar.low, bar.close)
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in vals):
            raise ValueError("Nến #%d có giá không hữu hạn (NaN/inf)." % bar.index)
        if not bar.is_valid_ohlc():
            raise ValueError("Nến #%d vi phạm quan hệ OHLC (low ≤ open/close ≤ high)." % bar.index)
        span = (bar.close_time - bar.bar_time).total_seconds()
        if span not in (0, self.step.total_seconds()):
            raise ValueError("Nến #%d không phải khung %s (bar_time→close_time = %ds)."
                             % (bar.index, self.params["timeframe"], span))
        prev = self._prev
        if prev is not None:
            if bar.index <= prev.index:
                raise ValueError("Nến phải nạp theo index tăng dần: nhận #%d sau #%d." % (bar.index, prev.index))
            if bar.bar_time <= prev.bar_time:
                raise ValueError("Timestamp trùng hoặc lùi tại nến #%d (%s ≤ %s). Không tự sắp lại."
                                 % (bar.index, bar.bar_time.isoformat(), prev.bar_time.isoformat()))

    def on_bar(self, bar: Bar) -> list[StructureEvent]:
        self._validate(bar)
        out: list[StructureEvent] = []
        prev = self._prev
        t = bar.index
        self._cur_index = t
        self._recent.append(bar)
        self._kz_now = self._kz.of(bar.bar_time)
        # 1. [G] khoảng trống trước nến này
        gap = self._gaps.classify(prev, bar) if prev is not None else None
        self._gap_now = gap
        if gap is not None:
            self._gap_count[gap["loai"]] += 1
            if gap["bat_thuong"] and len(self._abnormal) < MAX_ABNORMAL_LISTED:
                self._abnormal.append({"nen": bar.index, "tu": gap["tu"], "den": gap["den"],
                                       "loai": gap["loai"], "so_o_trong_phien": gap["so_o_trong_phien"]})
            out.append(self._gap_event(bar, prev, gap))
        # 2. [A] ngưỡng của nến t dùng ATR[t-1]
        atr_prev = self._atr.value
        self._highs.append(bar.high)
        self._lows.append(bar.low)
        self._atr_prev_hist.append(atr_prev)
        # 3. [E2] vùng thanh khoản đã biết trước t
        liq = self._liq.on_bar(bar, atr_prev, gap)
        out.extend(self._liq_events(bar, liq["resolved"]))
        # 3b. [E4] OB / [E6] nhịp OTE đã biết trước t: chạm / hỏng / hết hạn, ứng viên vượt đầu xa → xác nhận;
        #     nhịp OTE: vào vùng / thủng gốc / hết hạn
        ob_done, ob_new = self._ob.on_bar(bar)
        for ob in ob_done:
            out.append(self._ob_end_event(bar, ob, atr_prev))
        for ob in ob_new:
            out.append(self._ob_new_event(bar, ob, atr_prev))
        leg = self._ote.on_bar(bar, atr_prev)
        if leg is not None:
            out.append(self._ote_end_event(bar, leg, atr_prev))
        self._ob.push(bar, gap is not None)
        # 4. [P3] displacement của t
        disp = self._disp.check(bar, atr_prev, after_gap=gap is not None)
        self._disp_now = disp
        disp_ev: Optional[StructureEvent] = None
        if disp is not None:
            disp_ev = self._disp_event(bar, disp)
            out.append(disp_ev)
        # 5. [P2] FVG đã biết trước t, rồi FVG với nến 3 = t
        for kind, f in self._fvg.update_open(bar):
            out.append(self._fvg_life_event(bar, kind, f))
        new_fvg: Optional[Fvg] = None
        if len(self._recent) >= 3:
            b1, b2 = self._recent[-3], self._recent[-2]
            new_fvg = self._fvg.detect(b1, b2, bar, self._gap_prev_bar or gap is not None, atr_prev,
                                       self._disp_prev_dir)
            if new_fvg is not None:
                ev = self._fvg_event(b2, bar, new_fvg, atr_prev)
                new_fvg.event_id = ev.event_id
                out.append(ev)
        # 6. [E3] shift ở t, rồi SHIFT_FVG của shift ở t−1 (giữ trước: shift mới ở t không được che nó)
        ls = self._last_shift
        new_shifts: list[tuple[StructureEvent, ShiftCandidate]] = []
        for direction, cands in self._shift.on_bar(bar, disp, gap is not None).items():
            main = _shift_main(direction, cands)
            out.append(self._shift_event(bar, direction, cands, main, disp, disp_ev))
            new_shifts.append((out[-1], main))
        if (new_fvg is not None and ls is not None and ls["d"] == t - 1 and new_fvg.mid_index == t - 1
                and new_fvg.direction == ls["dir"]):
            out.append(self._shift_fvg_event(bar, new_fvg, ls))
        # 6b. [OF] order flow: run (bước 3) + shift (bước 6) xác nhận ở t, theo thứ tự phát
        flow = self._of.on_bar(t, [_OF_INPUT[e.structure_type] + (e.event_id,) for e in out
                                   if e.structure_type in _OF_INPUT])
        if flow is not None:
            out.append(self._order_flow_event(bar, flow))
        # 6c. [E4]/[E6] SHIFT ở t → OB + nhịp OTE mới; SHIFT ngược chiều → OB chiều cũ hết hạn (hiệu lực từ t+1)
        if new_shifts or (disp_ev is not None and self._ob_anchor == "displacement"):
            out.extend(self._on_shift_ob_ote(bar, new_shifts, disp, disp_ev, atr_prev))
        # 7. [S5] phản ứng của nến t ở FVG khung lớn đã biết trước t → pd_bias
        pd_ids = [self._pd_event(bar, kind, z, info) for kind, z, info in self._pd.on_bar(bar, atr_prev)]
        if pd_ids:
            out.extend(pd_ids)
            self._pd.bias_events = [e.event_id for e in pd_ids]
        # 8. [S2] close[t] so với mức được bảo vệ đã biết trước t; [S4] dealing range gồm cả t
        self._order.check_close(bar)
        self._range.on_bar(bar)
        # 9. swing xác nhận tại t (thứ tự, mức, range, vùng thanh khoản mới — hiệu lực từ t+1)
        for p in self._pivots.update(bar, gap_before=gap is not None):
            out.extend(self._on_swing(p, atr_prev))
        # 10. [S6] DOL: đích bị lấy ở bước 3 → DOL_REACHED; shift ở bước 6 → DOL mới (thay DOL cũ)
        reached = self._dol.check_reached(liq["taken"])
        if reached is not None:
            out.append(self._dol_event(bar, reached))
        if self._last_shift is not None and self._last_shift["d"] == t and self._last_shift is not ls:
            sh = self._last_shift
            self._dol.set_from_shift(self._liq, 1 if sh["dir"] == "up" else -1, bar.close, atr_prev, t, sh["id"])
        # 11. [T] nến khung lớn chốt tại t → ngăn xếp, vùng, FVG, mức mới (hiệu lực từ t+1); giá mở ngày
        if self._agg is not None:
            pos = len(self._highs) - 1
            for hb in self._agg.push(bar, pos):
                out.extend(self._on_htf_bar(hb, bar))
            if "D" in self.level_frames:
                cur = self._agg.current("D")
                self._levels.on_bar(bar.close_time - self.step, bar.open, t, self._agg.started("D"),
                                    cur.first_slot, cur.start)
        # 12. ATR[t]; [T3] ảnh chụp ngữ cảnh sau t (timeline nến t, details.htf của sự kiện ở t+1)
        self._atr.update(bar.high, bar.low, bar.close)
        self._ote.after_bar(bar)            # 12b. đầu nhịp OTE đang chờ theo nến t (dùng từ t+1)
        # 13. [N] nhận diện (0.6.0): trạng thái sau t → khoảng + xác suất chạm tại t; chấm dự báo đã có kết cục
        if self._nd is not None:
            h1 = self._stacks.get("H1")
            changed = self._nd.step(bar, self._atr.value, gap, self._liq.nearest(), self._level_context(),
                                    nd.Structure(self._order.order, self._order.broken,
                                                 h1.order.order if h1 is not None else None))
            if changed is not None:
                out.append(self._state_event(bar, *changed))
        self._gap_prev_bar = gap is not None
        self._disp_prev_dir = disp["dir"] if disp is not None else None
        self._prev = bar
        self._ctx_raw = self._capture_ctx(bar)
        self._ctx = None
        self._count_bar(bar)
        return out

    def _bar_at(self, index: int) -> Bar:
        for b in reversed(self._recent):
            if b.index == index:
                return b
        raise RuntimeError("Không còn nến #%d trong bộ đệm gần nhất." % index)  # pragma: no cover

    # ------------------------------------------------------------------ [N] lớp nhận diện (0.6.0)

    def _state_event(self, bar: Bar, name: str, first: Bar, info: dict[str, Any]) -> StructureEvent:
        """``STATE_*`` khi trạng thái đổi: nến sự kiện = nến đầu của trạng thái mới, xác nhận ở nến t."""
        stype, reason, direction = self._nd.event_kind(name)
        return self._event(stype, first.close, first, bar, reason, direction,
                           details=self._nd.event_details(name, first, info, self._order.order))

    # ------------------------------------------------------------------ swing + vùng thanh khoản mới

    def _on_swing(self, p: Pivot, atr_prev: Optional[float]) -> list[StructureEvent]:
        stype, reason, short = _TYPES[(p.level, p.side)]
        is_high = p.side == "high"
        details: dict[str, Any] = {"cap": p.level, "ten": short}
        if p.level == 1:
            details.update({
                "trai": self.left, "phai": self.right,
                "quy_tac": ("high[pivot] > mọi high trong cửa sổ" if is_high else "low[pivot] < mọi low trong cửa sổ"),
                "chan_cua_so_qua_gap": self.params["gap_policy"] == GAP_BLOCK,
            })
        else:
            left, mid, right = p.members
            details.update({
                "basis": [left.event_id, mid.event_id, right.event_id],
                "gia_trai": left.price, "gia_giua": mid.price, "gia_phai": right.price,
                "nen_trai": left.bar_index, "nen_giua": mid.bar_index, "nen_phai": right.bar_index,
                "quy_tac": (
                    "đỉnh cấp %d ở giữa > hai đỉnh cấp %d liền trước và liền sau" % (p.level - 1, p.level - 1)
                    if is_high else
                    "đáy cấp %d ở giữa < hai đáy cấp %d liền trước và liền sau" % (p.level - 1, p.level - 1)
                ),
                "xac_nhan_khi": "swing cấp %d bên phải vừa xác nhận" % (p.level - 1),
            })
        if p.level == self.structure_level:
            details["cap_cau_truc"] = True
            details.update(self._order.on_swing(p, atr_prev))
            seq = self._highs if is_high else self._lows
            extreme = max(seq[p.pos:]) if is_high else min(seq[p.pos:])
            self._range.on_swing(p, extreme)
        ev = self._event(stype, p.price, p.bar, p.confirmed_bar, reason, "up" if is_high else "down",
                         reference=(p.members[1].event_id if p.members else None), details=details)
        if p.level == POOL_LEVEL:
            details["vung_thanh_khoan"] = self._add_pool(p, ev.event_id, atr_prev)
        p = with_event_id(p, ev.event_id)
        out = [ev]
        nxt = None
        if p.level == 1:
            nxt = self._l2.update(p)
        elif p.level == 2 and self._l3 is not None:
            nxt = self._l3.update(p)
        if nxt is not None:
            out.extend(self._on_swing(nxt, atr_prev))
        return out

    def _add_pool(self, p: Pivot, source_id: str, atr_prev: Optional[float]) -> dict[str, Any]:
        """ITH/ITL vừa xác nhận → vùng BSL/SSL (hiệu lực từ nến sau). Không tạo nếu đã bị lấy trước khi biết."""
        return self._new_pool(p.side, p.price, POOL_TIER, source_id, p.confirmed_bar.index, p.bar.index, p.pos,
                              atr_prev)[2]

    def _taken_before(self, is_high: bool, level: float, extreme_pos: int) -> Optional[int]:
        """Nến đầu tiên SAU cực trị (tới nến hiện tại) xuyên mức ≥ ngưỡng × ATR[j−1] — vùng đã bị lấy trước khi
        được biết; None nếu chưa."""
        seq = self._highs if is_high else self._lows
        start = extreme_pos + 1
        if start >= len(seq):
            return None
        if (max(seq[start:]) <= level) if is_high else (min(seq[start:]) >= level):
            return None                                   # lọc nhanh: không nến nào vượt mức
        offset = self._prev_index_offset()
        thr = self._liq.min_pen_atr
        for j in range(start, len(seq)):
            a = self._atr_prev_hist[j]
            if a is None:
                continue
            pen = (seq[j] - level) if is_high else (level - seq[j])
            if pen > 0 and pen >= thr * a:
                return j + offset
        return None

    def _prev_index_offset(self) -> int:
        """Chỉ số nến − vị trí trong luồng (nến nạp liên tiếp từ engine → hằng số)."""
        return self._cur_index - (len(self._highs) - 1)

    def _new_pool(self, side: str, level: float, tier: str, source_id: str, known_index: int, extreme_index: int,
                  extreme_pos: int, atr_eq: Optional[float]) -> tuple[str, Optional[Pool], dict[str, Any]]:
        """Vùng thanh khoản mới (mọi tầng) → (trạng thái, vùng, ``details.vung_thanh_khoan``). ``atr_eq`` = ATR
        dùng cho dung sai gộp EQH/EQL (ATR của khung nguồn); None → không gộp."""
        taken_before = self._taken_before(side == "high", level, extreme_pos)
        status, pool = self._liq.add(side, level, tier, source_id, known_index, extreme_index, atr_eq,
                                     taken_before is not None)
        self._pool_status[status] = self._pool_status.get(status, 0) + 1
        info: dict[str, Any] = {
            "trang_thai": {"created": "tao_moi", "merged": "gop_eq", "not_created": "khong_tao"}[status],
            "phia": _SIDE_NAME[side],
            "tang": tier,
        }
        if pool is not None:
            info.update({"vung": pool.brief()["id"], "muc_vung": pool.level, "hieu_luc_tu_nen": known_index + 1})
        else:
            info["ly_do_vi"] = "đã bị lấy ở nến #%d trước khi đỉnh/đáy được biết" % taken_before
        return status, pool, info

    # ------------------------------------------------------------------ sự kiện giai đoạn 2

    def _liq_events(self, bar: Bar, resolved: list[tuple[str, Pool]]) -> list[StructureEvent]:
        if not resolved:
            return []
        t = bar.index
        groups: dict[tuple[str, str], list[Pool]] = {}
        for kind, pool in resolved:
            groups.setdefault((kind, pool.side), []).append(pool)
        out: list[StructureEvent] = []
        for key in _LIQ_ORDER:
            pools = groups.get(key)
            if not pools:
                continue
            kind, side = key
            pools.sort(key=lambda q: q.seq)
            stype, reason, direction = _LIQ[key]
            main = max(pools, key=lambda q: (TIER_RANK.get(q.tier, 0), q.level if side == "high" else -q.level, -q.seq))
            b = self._bar_at(main.taken_index)
            briefs = []
            for q in pools:
                d = q.brief()
                if kind == "sweep":
                    d["sweep_bars"] = t - q.taken_index
                briefs.append(d)
            details: dict[str, Any] = {
                "phia": _SIDE_NAME[side],
                "tang": main.tier,
                "muc": main.level,
                "vung": main.brief()["id"],
                "nen_lay": main.taken_index,
                "atr_khoa": main.atr_locked,
                "xuyen_atr": (main.pen / main.atr_locked) if main.atr_locked else None,
                "cuc_tri_cu_quet": main.extreme,
                "cua_so": self.params["sweep_window"],
                "so_vung": len(pools),
                "pools": briefs,
            }
            suffix = None
            if kind == "sweep":
                details["sweep_bars"] = t - main.taken_index
                details["cung_nen_lay"] = t == main.taken_index
            elif kind == "run":
                details["so_nen_sau_lay"] = t - main.taken_index
            else:
                details["loai_khoang_trong"] = main.gap_kind
                suffix = _SIDE_NAME[side]
            ev = self._event(stype, main.level, b, bar, reason, direction, reference=main.sources[-1],
                             details=details, suffix=suffix)
            if kind == "sweep":
                details["group_id"] = ev.event_id
                self._last_sweep = {"phia": _SIDE_NAME[side], "r": t, "tang": main.tier, "id": ev.event_id}
                for q in pools:
                    self._shift.add(ShiftCandidate(
                        direction="down" if side == "high" else "up", level=q.level, extreme=q.extreme, r=t,
                        deadline=t + self.params["shift_window"], sweep_event_id=ev.event_id,
                        group_id=ev.event_id, tier=q.tier, pools=[q.brief()], taken_index=q.taken_index,
                    ))
            out.append(ev)
        return out

    def _disp_event(self, bar: Bar, disp: dict[str, Any]) -> StructureEvent:
        up = disp["dir"] == "up"
        details = dict(disp)
        details.pop("dir")
        return self._event(StructureType.DISPLACEMENT_UP if up else StructureType.DISPLACEMENT_DOWN, bar.close,
                           bar, bar, ReasonCode.DISP_RANGE_BODY, disp["dir"], details=details)

    def _fvg_event(self, mid: Bar, bar: Bar, f: Fvg, atr_prev: Optional[float]) -> StructureEvent:
        up = f.direction == "up"
        size = f.hi - f.lo
        details = {
            "lo": f.lo, "hi": f.hi, "kich_thuoc": size,
            "kich_thuoc_atr": (size / atr_prev) if atr_prev else None,
            "from_displacement": f.from_displacement,
            "nen_1": mid.index - 1, "nen_giua": mid.index, "nen_3": bar.index,
        }
        return self._event(StructureType.FVG_UP if up else StructureType.FVG_DOWN, (f.lo + f.hi) / 2.0, mid, bar,
                           ReasonCode.FVG_THREE_BAR, f.direction, details=details)

    def _fvg_life_event(self, bar: Bar, kind: str, f: Fvg) -> StructureEvent:
        up = f.direction == "up"
        touched = kind == "touched"
        # FVG tăng nằm dưới giá: mép gần = hi, mép xa = lo; FVG giảm ngược lại.
        price = (f.hi if up else f.lo) if touched else (f.lo if up else f.hi)
        details = {
            "fvg": f.event_id, "chieu_fvg": f.direction, "lo": f.lo, "hi": f.hi,
            "nen_giua_fvg": f.mid_index, "so_nen_tu_khi_biet": bar.index - f.index,
        }
        if not touched:
            details["cham_tai_nen"] = f.touched_at
        return self._event(StructureType.FVG_TOUCHED if touched else StructureType.FVG_FILLED, price, bar, bar,
                           ReasonCode.FVG_FIRST_TOUCH if touched else ReasonCode.FVG_FULL_FILL, f.direction,
                           reference=f.event_id, details=details,
                           suffix="%d%s" % (f.mid_index, "U" if up else "D"))

    def _shift_event(self, bar: Bar, direction: str, cands: list[ShiftCandidate], main: ShiftCandidate,
                     disp: dict[str, Any], disp_ev: Optional[StructureEvent]) -> StructureEvent:
        t = bar.index
        down = direction == "down"
        sweep_ids: list[str] = []
        for c in cands:
            if c.sweep_event_id not in sweep_ids:
                sweep_ids.append(c.sweep_event_id)
        swept = [{
            "sweep": c.sweep_event_id, "vung": c.pools[0]["id"] if c.pools else None, "muc": c.level,
            "tang": c.tier, "nen_lay": c.taken_index, "nen_sweep": c.r, "cuc_tri_cu_quet": c.extreme,
        } for c in cands]
        details = {
            "chieu": direction,
            "tang": main.tier,
            "group_id": main.group_id,
            "muc_bi_quet": main.level,
            "cuc_tri_cu_quet": main.extreme,
            "nen_sweep": main.r,
            "so_nen_tu_sweep": t - main.r,
            # d = b: displacement ngay trên nến lấy (survey-v2 «trên nến quét»); d = r: chính nến close
            # quay lại — thường gặp vì nến displacement vượt lại mức cũng là nến làm sweep.
            "displacement_tren_nen_lay": t == main.taken_index,
            "cung_nen_sweep": t == main.r,
            "cua_so": self.params["shift_window"],
            "swept": swept,
            "displacement": {k: disp[k] for k in ("bien_do_atr", "than_ty_le", "atr")},
            "basis": sweep_ids + ([disp_ev.event_id] if disp_ev is not None else []),
            "ghi_chu_vi": "Shift có displacement lúc phát hiện — chưa biết sẽ tiếp diễn hay thất bại.",
        }
        ev = self._event(StructureType.SHIFT_DOWN if down else StructureType.SHIFT_UP, bar.close, bar, bar,
                         ReasonCode.SHIFT_SWEEP_THEN_DISPLACEMENT, direction, reference=main.sweep_event_id,
                         details=details)
        self._last_shift = {"dir": direction, "d": t, "id": ev.event_id, "group_id": main.group_id,
                            "price": bar.close, "fvg": False, "tang": main.tier}
        kz = self._kz_now or "ngoai"
        self._shift_kz[kz] = self._shift_kz.get(kz, 0) + 1
        self._shift_tier[main.tier] = self._shift_tier.get(main.tier, 0) + 1
        if t == main.taken_index:
            self._shift_on_take_bar += 1
        if t == main.r:
            self._shift_on_sweep_bar += 1
        return ev

    def _shift_fvg_event(self, bar: Bar, f: Fvg, ls: dict[str, Any]) -> StructureEvent:
        d = self._bar_at(ls["d"])
        up = ls["dir"] == "up"
        details = {
            "shift": ls["id"], "group_id": ls["group_id"], "tang": ls["tang"],
            "fvg": f.event_id, "lo": f.lo, "hi": f.hi, "nen_displacement": ls["d"],
        }
        ls["fvg"] = True
        return self._event(StructureType.SHIFT_FVG_UP if up else StructureType.SHIFT_FVG_DOWN, ls["price"], d, bar,
                           ReasonCode.SHIFT_FVG_SAME_DISPLACEMENT, ls["dir"], reference=ls["id"], details=details)

    def _order_flow_event(self, bar: Bar, flow: dict[str, Any]) -> StructureEvent:
        """[OF] Trạng thái vừa đổi ở t: nến sự kiện = nến xác nhận = t, giá = close[t], tham chiếu = sự kiện
        kích hoạt (shift nếu có, không thì run; hai chiều cùng nến → không có)."""
        stype, direction = _OF_EVENT[flow["sang"]]
        details = {
            "tu": flow["tu"],
            "sang": flow["sang"],
            "tu_vi": FLOW_TEXT_VI[flow["tu"]],
            "sang_vi": FLOW_TEXT_VI[flow["sang"]],
            "ly_do": flow["ly_do"],
            "ly_do_vi": FLOW_REASON_VI[flow["ly_do"]],
            "basis": list(flow["basis"]),
            "trang_thai_cu_tu_nen": flow["trang_thai_cu_tu_nen"],
            "trang_thai_cu_so_nen": flow["trang_thai_cu_so_nen"],
        }
        return self._event(stype, bar.close, bar, bar, _OF_REASON[flow["ly_do"]], direction,
                           reference=flow["trigger"], details=details)

    # ------------------------------------------------------------------ 0.5.0: [E4] order block, [E6] OTE

    def _on_shift_ob_ote(self, bar: Bar, new_shifts: list[tuple[StructureEvent, ShiftCandidate]],
                         disp: Optional[dict[str, Any]], disp_ev: Optional[StructureEvent],
                         atr_prev: Optional[float]) -> list[StructureEvent]:
        """Bước 6c của nến t (= d): OB chiều ngược hết hạn → ứng viên / OB mới → nhịp OTE mới (thay nhịp đang chờ)."""
        out: list[StructureEvent] = []
        t = bar.index
        for sh_ev, _main in new_shifts:
            for ob in self._ob.expire_opposite(sh_ev.direction):
                out.append(self._ob_end_event(bar, ob, atr_prev))
        if self._ob_anchor == "shift":                     # tìm từ nến lấy thanh khoản của ứng viên shift chính
            made = {sh.direction: self._ob.create(sh.direction, bar, m.taken_index if m.taken_index is not None else m.r,
                                                  sh.event_id) for sh, m in new_shifts}
        else:                                               # neo displacement: close vượt cực trị ob_lui nến trước
            made = {disp["dir"]: self._ob.create_on_break(disp["dir"], bar, disp_ev.event_id)} if disp_ev else {}
        for ob in made.values():                           # OB dùng lại (``trung``) đã phát sự kiện → event_id có sẵn
            if ob is not None and ob.confirmed_at == t and not ob.event_id:
                out.append(self._ob_new_event(bar, ob, atr_prev))
        for sh_ev, main in new_shifts:
            up = sh_ev.direction == "up"
            old = self._ote.start(sh_ev.direction, main.extreme, bar.high if up else bar.low, t, sh_ev.event_id)
            if old is not None:                             # nhịp cũ kết thúc cùng OB của chính nó
                out.append(self._ote_end_event(bar, old, atr_prev))
            self._ote_ob = made.get(sh_ev.direction)
        return out

    def _ob_new_event(self, bar: Bar, ob: OrderBlock, atr_prev: Optional[float]) -> StructureEvent:
        """``ORDER_BLOCK_*`` khi OB được xác nhận (giá vượt đầu xa, ở d hoặc sau): nến sự kiện = nến OB gần d nhất,
        nến xác nhận = nến vượt, giá = mean threshold."""
        details: dict[str, Any] = {
            "chieu": ob.direction, "lo": ob.lo, "hi": ob.hi, "mean_threshold": ob.mid,
            "kich_thuoc_atr": (ob.hi - ob.lo) / atr_prev if atr_prev else None,
            "nen_dau": ob.first_bar.index, "nen_cuoi": ob.last_bar.index, "so_nen": ob.n_bars,
            "bien_the": self._ob.variant, "neo": self._ob_anchor, "nen_neo": ob.anchor,
            "nen_xac_nhan": ob.confirmed_at, "han_nen": ob.deadline, "basis": [ob.anchor_id],
        }
        ev = self._event(_OB_NEW[ob.direction], ob.mid, ob.last_bar, bar, _OB_NEW_REASON[self._ob.variant],
                         ob.direction, reference=ob.anchor_id, details=details, suffix=str(ob.anchor))
        ob.event_id = ev.event_id
        return ev

    def _ob_end_event(self, bar: Bar, ob: OrderBlock, atr_prev: Optional[float]) -> StructureEvent:
        """Kết cục OB ở nến t: chạm (giá = mép gần), hỏng (giá = close), hết hạn (giá = mean threshold)."""
        kind, up = ob.ended, ob.direction == "up"
        touched = kind in ("tap", "fail")
        details: dict[str, Any] = {
            "ob": ob.event_id, "chieu_ob": ob.direction, "lo": ob.lo, "hi": ob.hi, "mean_threshold": ob.mid,
            "nen_dau": ob.first_bar.index, "nen_neo": ob.anchor, "so_nen_tu_tao": bar.index - ob.anchor,
            "ket_cuc": kind, "ket_cuc_vi": OB_END_VI[kind],
        }
        if touched:
            details.update({"close": bar.close, "close_qua_mean_threshold": bar.close < ob.mid if up else bar.close > ob.mid,
                            "atr": atr_prev})
            price = bar.close if kind == "fail" else (ob.hi if up else ob.lo)
        else:
            price = ob.mid
        suffix = "%d.%d" % (ob.last_bar.index, ob.anchor) + ("" if touched else ("U" if up else "D"))
        return self._event(_OB_TYPE.get((kind, ob.direction), StructureType.OB_EXPIRED), price, bar, bar,
                           _OB_REASON[kind], ob.direction, reference=ob.event_id, details=details, suffix=suffix)

    def _ote_end_event(self, bar: Bar, leg: OteLeg, atr_prev: Optional[float]) -> StructureEvent:
        """Kết cục nhịp OTE ở nến t: vào vùng (giá = mức ote_tu), thủng gốc (giá = gốc), hết hạn (giá = đầu nhịp)."""
        kind, o = leg.ended, self._ote
        ob = self._ote_ob.link() if self._ote_ob else None
        details: dict[str, Any] = leg.brief(o.frac_lo, o.frac_hi)
        details.update({
            "ket_cuc": kind, "ket_cuc_vi": OTE_END_VI[kind], "so_nen_tu_shift": bar.index - leg.anchor,
            "nhip_atr": leg.leg / atr_prev if atr_prev else None, "nhip_toi_thieu_atr": o.min_leg_atr,
            "basis": [leg.anchor_id] + ([ob["id"]] if ob and ob["id"] else []),
        })
        if kind == "entry":
            lo, hi = details["vung_lo"], details["vung_hi"]
            details.update({"do_sau": leg.depth, "ob": ob,
                            "ob_giao_vung": (ob["lo"] <= hi and ob["hi"] >= lo) if ob else None})
        price = leg.level(o.frac_lo) if kind == "entry" else (leg.x if kind == "fail" else leg.h)
        return self._event(_OTE_TYPE.get((kind, leg.direction), StructureType.OTE_EXPIRED), price, bar, bar,
                           _OTE_REASON[kind], leg.direction, reference=leg.anchor_id, details=details,
                           suffix=str(leg.anchor))

    # ------------------------------------------------------------------ giai đoạn 3: [T] [S5] [S6]

    def _on_htf_bar(self, hb: HtfBar, bar: Bar) -> list[StructureEvent]:
        """[T] Nến khung lớn ``hb`` vừa chốt, biết ở nến ``bar`` (= t). Mọi thứ mới có hiệu lực từ t+1."""
        out: list[StructureEvent] = []
        f = hb.frame
        if hb.late:
            self._htf_late.setdefault(f, []).append((hb.known_at - hb.close_time).total_seconds() / 3600.0)
        if hb.degraded:
            if len(self._htf_degraded) < MAX_ABNORMAL_LISTED:
                self._htf_degraded.append({"khung": f, "mo": hb.bar_time.isoformat(), "nen_biet": hb.known_index,
                                           "coverage": hb.coverage, "ly_do": hb.degraded_reason})
            if self.emit_htf:
                out.append(self._htf_degraded_event(hb, bar))
        if f in LEVEL_FRAMES:
            if self._levels.on_period(hb) and self.params["period_levels"]:
                for side in ("high", "low"):
                    ev = self._period_level(hb, side, bar)
                    if ev is not None:
                        out.append(ev)
            return out
        res = self._stacks[f].on_bar(hb)
        if res["fvg"] is not None:
            ev = self._htf_fvg(f, res["fvg"], res["fvg_bars"], res["atr_prev"], bar)
            if ev is not None:
                out.append(ev)
        for q, det in res["swings"]:
            ev = self._htf_swing(f, q, det, res["atr_prev"], bar)
            if ev is not None:
                out.append(ev)
        return out

    @staticmethod
    def _eid(stype: str, event_index: int, confirmed_index: int, suffix: str) -> str:
        return "ict:%s@%d>%d:%s" % (stype, event_index, confirmed_index, suffix)

    @staticmethod
    def _htf_meta(hb: HtfBar) -> dict[str, Any]:
        return {"period_end": hb.close_time.isoformat(), "known_at": hb.known_at.isoformat(),
                "chot_muon": hb.late, "coverage": hb.coverage, "n_bars": hb.n_bars, "expected_bars": hb.expected_bars}

    def _htf_swing(self, f: str, q: Pivot, det: dict[str, Any], atr_htf: Optional[float],
                   bar: Bar) -> Optional[StructureEvent]:
        """ITH/ITL khung lớn → ``HTF_SWING_*`` (nến sự kiện = nến khung chạy đạt cực trị) + vùng thanh khoản tầng f."""
        is_high = q.side == "high"
        hb: HtfBar = q.bar                            # nến khung lớn của đỉnh/đáy ở giữa
        conf: HtfBar = q.confirmed_bar                # nến khung lớn làm ITH/ITL được biết
        ext_bar = hb.high_bar if is_high else hb.low_bar
        ext_pos = hb.high_pos if is_high else hb.low_pos
        stype = StructureType.HTF_SWING_HIGH if is_high else StructureType.HTF_SWING_LOW
        eid = self._eid(stype, ext_bar.index, bar.index, f)
        left, _mid, right = q.members
        details: dict[str, Any] = {
            "khung": f, "cap": 2, "ten": "ITH" if is_high else "ITL",
            "nen_htf": hb.index, "nen_htf_trai": left.bar.index, "nen_htf_phai": right.bar.index,
            "gia_trai": left.price, "gia_phai": right.price, "nen_htf_xac_nhan": conf.index,
            "mo_nen_htf": hb.bar_time.isoformat(), "atr_khung": atr_htf,
            "quy_tac": ("đỉnh ngắn hạn khung %s ở giữa > hai đỉnh liền trước và liền sau" if is_high else
                        "đáy ngắn hạn khung %s ở giữa < hai đáy liền trước và liền sau") % f,
        }
        details.update(self._htf_meta(conf))
        details.update(det)
        details["vung_thanh_khoan"] = self._new_pool(q.side, q.price, f, eid, bar.index, ext_bar.index, ext_pos,
                                                     atr_htf)[2]
        if not self.emit_htf:
            return None
        return self._event(stype, q.price, ext_bar, bar,
                           ReasonCode.HTF_PIVOT_HIGH_L2 if is_high else ReasonCode.HTF_PIVOT_LOW_L2,
                           "up" if is_high else "down", details=details, suffix=f)

    def _htf_fvg(self, f: str, fvg: Fvg, trio: tuple[HtfBar, HtfBar, HtfBar], atr_htf: Optional[float],
                 bar: Bar) -> Optional[StructureEvent]:
        """FVG khung lớn → vùng PD array cho [S5] (hiệu lực từ t+1) + ``HTF_FVG_*`` (nến sự kiện = nến khung
        chạy đầu tiên của nến khung lớn ở giữa)."""
        b1, b2, b3 = trio
        up = fvg.direction == "up"
        stype = StructureType.HTF_FVG_UP if up else StructureType.HTF_FVG_DOWN
        mid_first = b2.first_bar
        eid = self._eid(stype, mid_first.index, bar.index, f)
        zone = self._pd.add(f, fvg.direction, fvg.lo, fvg.hi, bar.index, eid, fvg.from_displacement, mid_first.index)
        if not self.emit_htf:
            return None
        size = fvg.hi - fvg.lo
        details: dict[str, Any] = {
            "khung": f, "lo": fvg.lo, "hi": fvg.hi, "ce": zone.ce, "kich_thuoc": size,
            "kich_thuoc_atr": (size / atr_htf) if atr_htf else None, "atr_khung": atr_htf,
            "from_displacement": fvg.from_displacement,
            "nen_htf_1": b1.index, "nen_htf_giua": b2.index, "nen_htf_3": b3.index,
            "nen_giua_tu": mid_first.index, "nen_giua_den": b2.last_index,
            "mo_nen_giua": b2.bar_time.isoformat(), "hieu_luc_tu_nen": bar.index + 1,
        }
        details.update(self._htf_meta(b3))
        return self._event(stype, (fvg.lo + fvg.hi) / 2.0, mid_first, bar, ReasonCode.HTF_FVG_THREE_BAR,
                           fvg.direction, details=details, suffix=f)

    def _htf_degraded_event(self, hb: HtfBar, bar: Bar) -> StructureEvent:
        details = hb.brief()
        details.update({"nguong_coverage": self.params["htf_min_coverage"],
                        "he_qua_vi": "không nằm trong cửa sổ swing/FVG khung lớn; kỳ ngày/tuần không tạo mức"})
        reason = {"ky_dau_thieu": ReasonCode.HTF_FIRST_PERIOD_PARTIAL,
                  "ngoai_lich": ReasonCode.HTF_OUTSIDE_CALENDAR}.get(hb.degraded_reason, ReasonCode.HTF_COVERAGE_LOW)
        return self._event(StructureType.HTF_BAR_DEGRADED, hb.close, hb.first_bar, bar, reason, None,
                           details=details, suffix=hb.frame)

    def _period_level(self, hb: HtfBar, side: str, bar: Bar) -> Optional[StructureEvent]:
        """[T2] PDH/PDL (khung D), PWH/PWL (khung W) → vùng thanh khoản tầng D/W, hiệu lực từ t+1."""
        f = hb.frame
        is_high = side == "high"
        level = hb.high if is_high else hb.low
        ext_bar = hb.high_bar if is_high else hb.low_bar
        ext_pos = hb.high_pos if is_high else hb.low_pos
        stype = StructureType.HTF_PERIOD_HIGH if is_high else StructureType.HTF_PERIOD_LOW
        eid = self._eid(stype, ext_bar.index, bar.index, f)
        status, pool, info = self._new_pool(side, level, f, eid, bar.index, ext_bar.index, ext_pos, None)
        self._levels.set_pool(f, side, pool, status == "not_created")
        if not self.emit_htf:
            return None
        details: dict[str, Any] = {"khung": f, "ten": LEVEL_NAMES[(f, side)], "muc": level,
                                   "mo_ky": hb.bar_time.isoformat(), "nen_htf": hb.index}
        details.update(self._htf_meta(hb))
        details["vung_thanh_khoan"] = info
        return self._event(stype, level, ext_bar, bar, ReasonCode.HTF_PERIOD_LEVEL, "up" if is_high else "down",
                           details=details, suffix=f)

    def _pd_event(self, bar: Bar, kind: str, z: PdZone, info: dict[str, Any]) -> StructureEvent:
        """[S5] Kết quả đầu tiên của nến t ở vùng FVG khung lớn ``z``: nến sự kiện = nến xác nhận = t, giá = close."""
        up = z.direction == "up"
        if kind == "respect":
            stype = StructureType.PD_RESPECT_UP if up else StructureType.PD_RESPECT_DOWN
            reason = ReasonCode.PD_RESPECT_STRICT if self._pd.mode == "strict" else ReasonCode.PD_RESPECT_LOOSE
        else:
            stype = StructureType.PD_DISRESPECT_UP if up else StructureType.PD_DISRESPECT_DOWN
            reason = ReasonCode.PD_DISRESPECT_CE if self._pd.mode == "ce" else ReasonCode.PD_DISRESPECT_FAR_EDGE
        t = bar.index
        details: dict[str, Any] = {
            "khung": z.tf, "fvg": z.event_id, "chieu_fvg": z.direction, "lo": z.lo, "hi": z.hi, "ce": z.ce,
            "from_displacement": z.from_displacement, "ket_qua": kind, "che_do": self._pd.mode,
            "mep": info["mep"], "khoang_cach_yeu_cau": info["khoang_cach_yeu_cau"], "atr": info["atr"],
            "quy_tac_vi": info["quy_tac_vi"], "close": bar.close, "nen_cham": z.tap_index,
            "so_nen_tu_khi_biet": t - z.known_index, "so_nen_tu_cham": t - z.tap_index,
            "chieu_ham_y": info["chieu_ham_y"], "pd_bias_sau": self._pd.bias, "pd_bias_khung": self._pd.bias_tf,
        }
        return self._event(stype, bar.close, bar, bar, reason, "up" if info["chieu_ham_y"] > 0 else "down",
                           reference=z.event_id if self.emit_htf else None, details=details,
                           suffix="%s.%d" % (z.tf, z.mid_index))

    def _dol_event(self, bar: Bar, reached: dict[str, Any]) -> StructureEvent:
        """[S6] Đích DOL bị lấy ở bước [E2] của nến t: nến sự kiện = nến lấy = t, giá = mức vùng đích."""
        tg: Pool = reached["target"]
        details: dict[str, Any] = {
            "chieu_dol": reached["side"], "vung": tg.brief(), "muc": tg.level, "tang": tg.tier,
            "phia": _SIDE_NAME[tg.side], "shift": reached["shift_id"], "nen_dat_dol": reached["since"],
            "so_nen_tu_shift": bar.index - reached["since"], "khoang_cach_atr_luc_dat": reached["dist_atr_at_set"],
            "xuyen_atr": (tg.pen / tg.atr_locked) if (tg.pen is not None and tg.atr_locked) else None,
            "ghi_chu_vi": "Mô tả: đích DOL đã bị lấy. «Tỷ lệ đạt DOL» chỉ là nhãn đánh giá, không là đầu vào.",
            "basis": [reached["shift_id"]] + list(tg.sources),
        }
        return self._event(StructureType.DOL_REACHED, tg.level, bar, bar, ReasonCode.DOL_TARGET_TAKEN,
                           "up" if reached["side"] > 0 else "down", reference=reached["shift_id"], details=details)

    def _level_context(self) -> Optional[dict[str, Any]]:
        """[T2] Ngữ cảnh mức theo kỳ (PDH/PDL, PWH/PWL kèm «đã lấy») sau nến hiện tại — None khi tắt khung lớn. Dựng lại chỉ
        khi mức / trạng thái vùng đổi; dict bất biến nên bước 13 và ảnh chụp ngữ cảnh dùng chung."""
        if not self.level_frames:
            return None
        key = (self._levels.rev, self._liq.rev)
        if key != self._levels_key:
            self._levels_key = key
            self._levels_ctx = self._levels.context(self.params["period_levels"])
        return self._levels_ctx

    def _capture_ctx(self, bar: Optional[Bar]) -> tuple:
        """[T3] Chụp các giá trị (bất biến) của ngữ cảnh khung lớn SAU nến ``bar``. Dict ``details.htf`` chỉ được
        dựng (``_ctx_dict``) khi nến kế tiếp thật sự phát sự kiện — cùng nội dung, rẻ hơn khi nến không có sự kiện."""
        frames = []
        for f in HTF_FRAMES:
            st = self._stacks.get(f)
            if st is None:
                frames.append(None)
                continue
            near = self._liq.nearest(tier=f)
            a, b = near["high"], near["low"]
            frames.append((st.static, a.level if a else None, b.level if b else None))
        levels = self._level_context()
        pd, dl = self._pd, self._dol
        tg = dl.target
        return (bar.close if bar is not None else None, bar.index if bar is not None else None, self._atr.value,
                frames, pd.bias, pd.bias_tf, pd.bias_since, dl.side, tg.level if tg is not None else None,
                tg.tier if tg is not None else None, levels)

    def _ctx_dict(self, raw: tuple) -> dict[str, Any]:
        """Ảnh chụp gọn ``details.htf`` (plan §11.5) từ giá trị đã chụp. Khoảng cách tính bằng ATR khung chạy."""
        close, t, atr, frames, pdb, pdtf, pds, dside, dtarget, dtier, levels = raw
        out: dict[str, Any] = {"alignment": self.params["htf_alignment"]}
        for f, fr in zip(HTF_FRAMES, frames):
            out[f] = None if fr is None else HtfStack.context_from(fr[0], close, t, fr[1], fr[2])
        out["pd_bias"] = {"dir": pdb, "tf": pdtf,
                          "age_ltf_bars": (t - pds) if (t is not None and pds is not None) else None}
        out["dol"] = {"side": dside, "target": dtarget, "tier": dtier,
                      "dist_atr": (abs(dtarget - close) / atr) if (dtarget is not None and close is not None and atr)
                      else None}
        out["levels"] = levels
        return out

    def _gap_event(self, bar: Bar, prev: Bar, gap: dict[str, Any]) -> StructureEvent:
        details = dict(gap)
        details.update({
            "nen_truoc": prev.index,
            "lich_phien": self.calendar_name,
            "chinh_sach": (
                "giữ mức swing/vùng; chặn cửa sổ pivot vắt qua khoảng trống"
                if self.params["gap_policy"] == GAP_BLOCK else "giữ mức; không chặn cửa sổ (chỉ để đối chiếu)"
            ),
        })
        return self._event(StructureType.ICT_GAP, bar.open, bar, bar, _GAP_REASON[gap["loai"]], None,
                           details=details)

    def _event(self, stype: str, price: float, event_bar: Bar, confirming: Bar, reason: str,
               direction: Optional[str], reference: Optional[str] = None,
               details: Optional[dict[str, Any]] = None, suffix: Optional[str] = None) -> StructureEvent:
        if stype == StructureType.ICT_GAP:
            event_id = "ict:%s@%d" % (stype, event_bar.index)
        else:
            event_id = "ict:%s@%d>%d" % (stype, event_bar.index, confirming.index)
        if suffix:
            event_id += ":" + suffix
        if event_id in self._emitted:  # pragma: no cover - phòng vệ
            raise RuntimeError("Trùng event_id: %s" % event_id)
        self._emitted.add(event_id)
        details = details if details is not None else {}
        # [C] cờ killzone theo giờ mở của nến sự kiện (không lọc gì)
        details.setdefault("killzone", self._kz.of(event_bar.bar_time))
        # [T3] ngữ cảnh khung lớn đã chốt ≤ nến trước (dùng chung một ảnh chụp bất biến cho mọi sự kiện của nến);
        # không gắn cho sự kiện khung lớn và sự kiện «nguyên liệu» (_NO_CTX_TYPESET, 0.4.1)
        if stype not in _HTF_TYPESET and stype not in _NO_CTX_TYPESET:
            if self._ctx is None:
                self._ctx = self._ctx_dict(self._ctx_raw)
            details["htf"] = self._ctx
        return StructureEvent(
            event_id=event_id, structure_type=stype, price=float(price),
            event_bar_index=event_bar.index, event_time=event_bar.bar_time, event_close_time=event_bar.close_time,
            confirmed_bar_index=confirming.index, confirmed_at=confirming.close_time,
            algorithm=self.name, algorithm_version=self.version, reason_code=reason, direction=direction,
            reference_event_id=reference, details=details,
        )

    def _count_bar(self, bar: Bar) -> None:
        self._n += 1
        if self.calendar is not None:
            s = self.calendar.session_at(bar.bar_time)
            if s is None:
                self._outside += 1
            else:
                self._days.add(s.trading_day)
        else:
            self._days.add(bar.bar_time.date())
        o = self._order
        self._order_bars["none" if o.order is None else str(o.order)] += 1
        if o.protected is not None:
            self._protected_bars += 1
            if o.broken:
                self._broken_bars += 1
        kz = self._kz_now or "ngoai"
        self._kz_bars[kz] = self._kz_bars.get(kz, 0) + 1
        s = self._of.state
        self._of_bars[FLOW_KEYS[s]] += 1
        if s is not None:                    # None chỉ có ở đầu run (trước run/shift đầu tiên) → bỏ
            segs = self._of_segs
            if segs and segs[-1][0] == s:
                segs[-1][1] += 1
            else:
                segs.append([s, 1])
        # [T] [S5] [S6] trạng thái SAU nến (như timeline)
        raw = self._ctx_raw
        for f, fr in zip(HTF_FRAMES, raw[3]):
            if fr is None:
                continue
            ready, order = (fr[0][0], fr[0][1]) if fr[0] is not None else (False, None)
            hb = self._htf_bars[f]
            hb["none" if order is None else str(order)] += 1
            hb["ready"] += ready
        pdb = raw[4]
        self._pd_bars["none" if pdb is None else str(pdb)] += 1
        self._dol_bars["none" if raw[7] is None else str(raw[7])] += 1
        self._dol_bars["co_dich"] += raw[8] is not None

    # ------------------------------------------------------------------ hiển thị

    def timeline_point(self, bar: Bar) -> Optional[dict[str, Any]]:
        o = self._order
        r = self._range.snapshot(bar.close)
        p = o.protected
        near = self._liq.nearest()
        above, below = near["high"], near["low"]
        ls, lw = self._last_shift, self._last_sweep
        return {
            "order": o.order,
            "protected": p.price if p else None,
            "protected_side": p.side if p else None,
            "protected_id": ("%s%d" % (p.side[0], p.bar_index)) if p else None,
            "protected_broken": o.broken if p else None,
            "dealing_hi": r["hi"],
            "dealing_lo": r["lo"],
            "dealing_eq": r["eq"],
            "dealing_id": r["id"],
            "zone": r["zone"],
            "range_pos": r["range_pos"],
            "atr": self._atr.value,
            "gap": self._gap_now["loai"] if self._gap_now else None,
            "killzone": self._kz_now,
            "liq_above": above.level if above else None,
            "liq_above_id": above.brief()["id"] if above else None,
            "liq_below": below.level if below else None,
            "liq_below_id": below.brief()["id"] if below else None,
            "pending_takes": len(self._liq.pending()),
            "pending_shifts": len(self._shift.pending),
            "last_sweep": lw["phia"] if lw else None,
            "last_sweep_bars": (bar.index - lw["r"]) if lw else None,
            "last_shift": ls["dir"] if ls else None,
            "last_shift_bars": (bar.index - ls["d"]) if ls else None,
            "last_shift_fvg": ls["fvg"] if ls else None,
            "open_fvg_up": self._fvg.open["up"],
            "open_fvg_down": self._fvg.open["down"],
            "displacement": self._disp_now["dir"] if self._disp_now else None,
            "order_flow": self._of.state,
            "order_flow_since": self._of.since,
            "order_flow_reason": self._of.reason,
            # [T3] cột phẳng (plan §11.5, §5.2) — trạng thái SAU nến t, cùng ảnh chụp details.htf của nến t+1
            **self._timeline_htf(),
            **self._timeline_ob_ote(bar.close),
            **(self._nd.timeline() if self._nd is not None else {}),
        }

    def _timeline_ob_ote(self, close: float) -> dict[str, Any]:
        """[E4]/[E6] sau nến t: OB còn mở gần close nhất mỗi chiều; nhịp OTE đang chờ và vùng sẽ xét ở nến t+1 (None khi
        nhịp chưa đủ ``ote_nhip_min_atr`` × ATR[t])."""
        leg = self._ote.pending
        if leg is None and not self._ob.open:
            return _TL_OB_OTE_NONE
        up, dn = (next(iter(self._ob.ranked(d, close)), None) for d in ("up", "down"))
        zone = self._ote.zone(leg, self._atr.value) if leg is not None else None
        return {
            "ob_up_hi": up.hi if up else None, "ob_up_lo": up.lo if up else None,
            "ob_down_hi": dn.hi if dn else None, "ob_down_lo": dn.lo if dn else None,
            "ote_dir": leg.direction if leg else None, "ote_neo": leg.anchor if leg else None,
            "ote_x": leg.x if leg else None, "ote_h": leg.h if leg else None,
            "ote_lo": zone[0] if zone else None, "ote_hi": zone[1] if zone else None,
        }

    def _timeline_htf(self) -> dict[str, Any]:
        close, t, atr, frames, pdb, pdtf, _pds, dside, dtarget, dtier, lv = self._ctx_raw
        h1, h4 = frames
        s4 = h4[0] if h4 is not None else None
        zone = pos = age = None
        if s4 is not None:
            zone, pos = HtfStack.zone_of(s4, close)
            age = (t - s4[5]) if t is not None else None
        return {
            "htf_H1_order": h1[0][1] if (h1 is not None and h1[0] is not None) else None,
            "htf_H4_order": s4[1] if s4 is not None else None,
            "htf_H4_zone": zone,
            "htf_H4_range_pos": pos,
            "htf_H4_age": age,
            "htf_H4_dealing_hi": s4[8] if s4 is not None else None,
            "htf_H4_dealing_lo": s4[9] if s4 is not None else None,
            "pd_bias": pdb,
            "pd_bias_tf": pdtf,
            "dol_side": dside,
            "dol_target": dtarget,
            "dol_tier": dtier,
            "dol_dist_atr": (abs(dtarget - close) / atr) if (dtarget is not None and close is not None and atr) else None,
            "pdh_taken": lv["pdh_taken"] if lv else None,
            "pdl_taken": lv["pdl_taken"] if lv else None,
        }

    def forecast_record(self) -> Optional[dict[str, Any]]:
        """0.9.3 — bản ghi dự báo của nến vừa nạp (``NdLayer.record``; None khi tắt ``nd_bat``) cho luồng live chỉ ghi thêm
        (plan_mt5_live.md §5). Không thuộc hợp đồng ``StructureAlgorithm``."""
        return self._nd.record() if self._nd is not None else None

    def llm_context(self, events: list[StructureEvent], *, symbol: str, digits: int) -> Optional[dict[str, Any]]:
        """Bản tóm gọn ở nến vừa nạp cho trợ lý tổng hợp (``digest.py``, plan_tro_ly_tong_hop.md §3) — chỉ đọc
        ``pending_state`` + sự kiện đã xác nhận, không đổi output nào. Không thuộc hợp đồng ``StructureAlgorithm``."""
        return digest.llm_context(self.pending_state(), events, self._prev, symbol=symbol,
                                  timeframe=self.params["timeframe"], digits=digits)

    def pending_state(self) -> dict[str, Any]:
        last = self._prev
        last_close = last.close if last is not None else None
        near = self._liq.nearest()
        t = last.index if last is not None else None
        W = self.params["sweep_window"]
        pending_takes = []
        for q in self._liq.pending():
            d = q.brief()
            d["con_lai_nen"] = (q.taken_index + W - t) if t is not None else None
            d["can_close"] = ("< %s để thành sweep" if q.side == "high" else "> %s để thành sweep") % q.level
            pending_takes.append(d)
        shifts = [{
            "chieu": c.direction, "muc_bi_quet": c.level, "cuc_tri_cu_quet": c.extreme, "nen_sweep": c.r,
            "han_chot": c.deadline, "sweep": c.sweep_event_id, "tang": c.tier,
            "can": ("displacement giảm, close < %s, không high > %s" if c.direction == "down"
                    else "displacement tăng, close > %s, không low < %s") % (c.level, c.extreme),
        } for c in self._shift.pending]
        above, below = near["high"], near["low"]
        return {
            "ict": True,
            "giai_doan": 3,
            "lich_phien": self.calendar_name,
            "cap_cau_truc": self.structure_level,
            "atr_hien_tai": self._atr.value,
            # [OF] bản sao; vùng cùng/ngược chiều = vùng còn nguyên gần nhất phía trên/dưới theo chiều
            "order_flow": self._of.snapshot(t, above.brief() if above else None, below.brief() if below else None),
            "cau_truc": self._order.snapshot(),
            "dealing_range": self._range.snapshot(last_close) if last_close is not None else None,
            "pivot": self._pivots.snapshot(),
            "cap2": self._l2.snapshot(),
            "cap3": self._l3.snapshot() if self._l3 else None,
            "khoang_trong": {k: v for k, v in self._gap_count.items() if v},
            "khoang_trong_truoc_nen_nay": self._gap_now,
            "so_nen": self._n,
            "killzone": self._kz_now,
            "thanh_khoan": {
                "gan_nhat_phia_tren": near["high"].brief() if near["high"] else None,
                "gan_nhat_phia_duoi": near["low"].brief() if near["low"] else None,
                "con_nguyen": self._liq.intact_count(),
                "dang_cho_sweep_run": pending_takes,
                "sweep_gan_nhat": dict(self._last_sweep) if self._last_sweep else None,
            },
            "shift": {"dang_cho": shifts, "gan_nhat": dict(self._last_shift) if self._last_shift else None},
            "displacement_nen_nay": dict(self._disp_now) if self._disp_now else None,
            "fvg_chua_cham_gan_nhat": self._fvg.nearest(),
            "fvg_dang_mo": dict(self._fvg.open),
            # [T] [S5] [S6] (bản sao — không trả tham chiếu nội bộ)
            "khung_lon": self._htf_pending(last),
            "pd": self._pd.snapshot(t),
            "dol": self._dol.snapshot(t, last_close, self._atr.value),
            # [E4] [E6] (0.5.0)
            "order_block": self._ob_pending(t, last_close),
            "ote": self._ote_pending(t),
            **({"nhan_dien": self._nd.pending()} if self._nd is not None else {}),     # [N] 0.6.0, khi bật
            "ghi_chu_vi": (
                "Thứ tự chỉ đổi khi có swing cấu trúc mới; close vượt mức được bảo vệ chỉ bật cờ, "
                "không phát sự kiện (không có BOS/CHoCH). Đổi hướng chỉ đến từ shift."
            ),
        }

    def _ob_pending(self, t: Optional[int], close: Optional[float]) -> dict[str, Any]:
        """OB còn mở (chưa chạm), gần giá nhất trước — tối đa 3 mỗi chiều."""
        rows, n_open = [], {}
        for d in ("up", "down"):
            obs = self._ob.ranked(d, close)
            n_open[d] = len(obs)
            for ob in obs[:3]:
                r = ob.brief()
                r["con_lai_nen"] = (ob.deadline - t) if t is not None else None
                r["can"] = ("low ≤ %s (chạm); close < %s là hỏng" % (ob.hi, ob.lo) if d == "up"
                            else "high ≥ %s (chạm); close > %s là hỏng" % (ob.lo, ob.hi))
                rows.append(r)
        return {"bien_the": self._ob.variant, "neo": self._ob_anchor, "dang_mo": rows, "so_dang_mo": n_open}

    def _ote_pending(self, t: Optional[int]) -> dict[str, Any]:
        """Nhịp OTE đang chờ (một nhịp tại một thời điểm) + vùng sẽ xét ở nến kế tiếp."""
        o, leg = self._ote, self._ote.pending
        out: dict[str, Any] = {"tu": o.frac_lo, "den": o.frac_hi, "nhip_toi_thieu_atr": o.min_leg_atr, "dang_cho": None}
        if leg is None:
            return out
        r = leg.brief(o.frac_lo, o.frac_hi)
        zone = o.zone(leg, self._atr.value)
        near = leg.level(o.frac_lo)
        up = leg.direction == "up"
        r.update({
            "con_lai_nen": (leg.deadline - t) if t is not None else None,
            "vung_hieu_luc": zone is not None,
            "nhip_atr": (leg.leg / self._atr.value) if self._atr.value else None,
            "ob": self._ote_ob.link() if self._ote_ob else None,
            "can": (("low ≤ %s (vào OTE); low < %s là hỏng" if up else "high ≥ %s (vào OTE); high > %s là hỏng")
                    % (near, leg.x)) if zone is not None else
                   "nhịp chưa đủ %s ATR — chờ giá đi tiếp" % o.min_leg_atr,
        })
        out["dang_cho"] = r
        return out

    def _htf_pending(self, last: Optional[Bar]) -> dict[str, Any]:
        close = last.close if last is not None else None
        out: dict[str, Any] = {
            "bat": self._agg is not None,
            "moc": self.params["htf_alignment"],
            "khung": list(self.htf_frames),
            "khung_bo_qua": list(self.htf_skipped),
            "ngu_canh": copy.deepcopy(self._ctx_dict(self._ctx_raw)),
            "ghi_chu_vi": (
                "Chỉ nến khung lớn ĐÃ CHỐT vào trạng thái; «dang_hinh_thanh» chỉ để vẽ. Sự kiện ở nến kế tiếp mang "
                "«ngu_canh» này trong details.htf."
            ),
        }
        zones = self._pd.open_zones()
        for f in HTF_FRAMES:
            st = self._stacks.get(f)
            if st is None:
                out[f] = None
                continue
            near = self._liq.nearest(tier=f)
            fz = []
            for d in ("up", "down"):
                zs = [z for z in zones if z.tf == f and z.direction == d]
                if close is not None:
                    zs.sort(key=lambda z: (max(z.lo - close, close - z.hi, 0.0), z.seq))
                fz.extend(z.brief() for z in zs[:3])
            out[f] = {
                "ready": st.ready(),
                "atr": st.atr.value,
                "so_nen_da_chot": st.n,
                "cau_truc": st.order.snapshot(),
                "dealing_range": st.range.snapshot(close) if (close is not None and st.range.ready()) else None,
                "nen_chot_gan_nhat": st.last.brief() if st.last is not None else None,
                "dang_hinh_thanh": self._agg.forming(f),
                "vung_gan_nhat": {"BSL": near["high"].brief() if near["high"] else None,
                                  "SSL": near["low"].brief() if near["low"] else None},
                "fvg_dang_mo_gan_nhat": fz,
                "so_fvg_dang_mo": {d: sum(1 for z in zones if z.tf == f and z.direction == d) for d in ("up", "down")},
                "cua_so_bi_chan_gan_day": st.blocked_recent(),
                "cua_so_gan_day_nen": BLOCKED_RECENT_BARS,
            }
        for f in LEVEL_FRAMES:
            if f not in self.level_frames:
                out[f] = None
                continue
            lb = self._agg.last(f)
            out[f] = {"nen_chot_gan_nhat": lb.brief() if lb is not None else None, "dang_hinh_thanh": self._agg.forming(f)}
        out["muc_theo_ky"] = self._levels.snapshot(self.params["period_levels"]) if self.level_frames else None
        return out

    def _ob_stats(self, per_day: Any, ratio: Any) -> dict[str, Any]:
        c = self._ob.counts
        ended = sum(c[k] for k in OB_END_VI)
        ages = sorted(self._ob.tap_ages)
        return {
            "bien_the": self._ob.variant, "neo": self._ob_anchor, "lui": self._ob.lookback, "han_nen": self._ob.expiry,
            "ung_vien": c["ung_vien"], "khong_co_nen_nguoc_mau": c["khong_co_nen"], "trung_ob_da_co": c["trung"],
            "xac_nhan": c["xac_nhan"], "moi_ngay": per_day(c["xac_nhan"]),
            "ty_le_xac_nhan": ratio(c["xac_nhan"], c["ung_vien"]), "bo_truoc_xac_nhan": c["bo_truoc_xac_nhan"],
            "cham": c["tap"], "hong": c["fail"], "het_han": c["expired_time"], "het_han_vi_shift": c["expired_shift"],
            "con_mo_cuoi_run": len(self._ob.open), "ung_vien_cuoi_run": len(self._ob.candidates),
            "ty_le_cham": ratio(c["tap"], ended), "ty_le_hong_khi_cham": ratio(c["fail"], c["tap"] + c["fail"]),
            "nen_toi_cham_trung_vi": _quantile(ages, 0.5),
            "ghi_chu_vi": "Mô tả hành vi của OB (chạm / hỏng / hết hạn) — không phải tỷ lệ thắng.",
        }

    def _ote_stats(self, ratio: Any) -> dict[str, Any]:
        c = self._ote.counts
        ended = sum(c[k] for k in OTE_END_VI)
        depth = sorted(self._ote.depths)
        return {
            "tu": self._ote.frac_lo, "den": self._ote.frac_hi, "nhip_toi_thieu_atr": self._ote.min_leg_atr,
            "han_nen": self._ote.expiry, "nhip": c["nhip"], "vao": c["entry"], "hong": c["fail"],
            "het_han": c["expired_time"], "het_han_vi_shift": c["expired_shift"], "bi_thay": c["replaced"],
            "dang_cho_cuoi_run": 1 if self._ote.pending is not None else 0,
            "ty_le_vao": ratio(c["entry"], ended),
            "do_sau_trung_vi": _quantile(depth, 0.5), "do_sau_p90": _quantile(depth, 0.9),
            "ghi_chu_vi": "Mô tả: nhịp sau SHIFT có hồi vào 62–79% không — không phải tỷ lệ thắng.",
        }

    def run_stats(self, events: list[StructureEvent]) -> Optional[dict[str, Any]]:
        by_type: dict[str, int] = {}
        for e in events:
            by_type[e.structure_type] = by_type.get(e.structure_type, 0) + 1
        n_days = len(self._days)

        def per_day(n: int) -> Optional[float]:
            return (n / n_days) if n_days else None

        def ratio(a: int, b: int) -> Optional[float]:
            return (a / b) if b else None

        T = StructureType
        levels = {}
        for (lvl, side), (stype, _r, short) in _TYPES.items():
            levels[short] = {"so": by_type.get(stype, 0), "moi_ngay": per_day(by_type.get(stype, 0)), "cap": lvl}
        n = self._n or 1
        n_disp = by_type.get(T.DISPLACEMENT_UP, 0) + by_type.get(T.DISPLACEMENT_DOWN, 0)
        fc = self._fvg.counts
        lc = self._liq.counts
        sc = self._shift.counts
        pen = sorted(self._liq.pen_atr)
        n_shift = by_type.get(T.SHIFT_UP, 0) + by_type.get(T.SHIFT_DOWN, 0)
        n_shift_fvg = by_type.get(T.SHIFT_FVG_UP, 0) + by_type.get(T.SHIFT_FVG_DOWN, 0)
        n_sweep = by_type.get(T.LIQ_SWEEP_BSL, 0) + by_type.get(T.LIQ_SWEEP_SSL, 0)
        n_run = by_type.get(T.LIQ_RUN_UP, 0) + by_type.get(T.LIQ_RUN_DOWN, 0)
        n_pools = lc["tao"]
        # [OF] đoạn = dãy nến liên tiếp cùng trạng thái (đã bỏ đoạn None đầu run, gồm đoạn cuối đang mở);
        # đổi chiều thật = đoạn ±1 khác chiều đoạn ±1 liền trước (có thể đi qua 0).
        of_reasons = dict.fromkeys(REASONS, 0)
        for e in events:
            if e.structure_type in T.ORDER_FLOW_TYPES:
                of_reasons[e.details["ly_do"]] += 1
        of_dir = sorted(k for v, k in self._of_segs if v != 0)
        of_zero = sorted(k for v, k in self._of_segs if v == 0)
        of_flips, prev_dir = 0, 0
        for v, _k in self._of_segs:
            if v != 0:
                if prev_dir != 0 and v != prev_dir:
                    of_flips += 1
                prev_dir = v
        bar_hours = self.step.total_seconds() / 3600.0
        med_zero, med_dir = _quantile(of_zero, 0.5), _quantile(of_dir, 0.5)
        # [T] [S5] [S6]
        htf: dict[str, Any] = {}
        for f, st in self._stacks.items():
            c = st.counts
            late = self._htf_late.get(f, [])
            n_sw = c["ith"] + c["itl"]
            n_fvg = c["fvg_tang"] + c["fvg_giam"]
            htf[f] = {
                "nen_chot": c["nen"], "degraded": c["degraded"], "after_hole": c["after_hole"], "over": c["over"],
                "ngoai_lich": c["ngoai_lich"], "chot_muon": c["chot_muon"],
                "chot_muon_gio_lon_nhat": max(late) if late else None,
                "cua_so_pivot_bi_chan": c["cua_so_bi_chan"], "pivot_bi_chan": dict(st.pivots.blocked),
                "ith": c["ith"], "itl": c["itl"], "ith_itl_moi_ngay": per_day(n_sw),
                "fvg": n_fvg, "fvg_tang": c["fvg_tang"], "fvg_giam": c["fvg_giam"], "fvg_moi_ngay": per_day(n_fvg),
                "ty_le_thoi_gian_order": {k: v / n for k, v in self._htf_bars[f].items() if k != "ready"},
                "ty_le_thoi_gian_ready": self._htf_bars[f]["ready"] / n,
            }
        periods: dict[str, Any] = {}
        for f in self.level_frames:
            late = self._htf_late.get(f, [])
            lc_f = self._levels.counts[f]
            periods[f] = {"ky_chot": lc_f["ky"], "degraded_khong_tao_muc": lc_f["degraded"], "chot_muon": len(late),
                          "chot_muon_gio_lon_nhat": max(late) if late else None}
        pdc = self._pd.counts
        n_pd = sum(by_type.get(x, 0) for x in T.PD_TYPES)
        dc = self._dol.counts
        dist = sorted(self._dol.dist)
        pd_changes = 0
        prev_pd = None
        for e in events:
            if e.structure_type in T.PD_TYPES:
                v = e.details["pd_bias_sau"]
                if v != prev_pd:
                    pd_changes += 1
                    prev_pd = v
        return {
            "giai_doan": 3,
            "lich_phien": self.calendar_name,
            "cap_cau_truc": self.structure_level,
            "so_nen": self._n,
            "so_ngay_giao_dich": n_days,
            "ngay_tinh_theo": "lịch phiên (ngày giao dịch)" if self.calendar is not None else "ngày UTC của nến",
            "nen_ngoai_phien": self._outside,
            "swing": levels,
            "ty_le_thoi_gian_order": {k: v / n for k, v in self._order_bars.items()},
            # Trạng thái SAU mỗi nến (như timeline). Survey-v2 đếm trước khi áp swing xác nhận ở nến đó
            # → cao hơn ~1 điểm %; cùng logic (xem đặc tả §9).
            "ty_le_muc_bao_ve_bi_vuot_tren_tong_nen": (self._broken_bars / self._n) if self._n else None,
            "ty_le_muc_bao_ve_bi_vuot_khi_co_muc": (
                (self._broken_bars / self._protected_bars) if self._protected_bars else None),
            "so_nen_co_muc_bao_ve": self._protected_bars,
            "khoang_trong": dict(self._gap_count),
            "khoang_trong_bat_thuong": list(self._abnormal),
            "pivot_bi_chan_vi_gap": dict(self._pivots.blocked),
            "displacement": {
                "so": n_disp, "ty_le_nen": ratio(n_disp, self._n), "moi_ngay": per_day(n_disp),
                "tang": by_type.get(T.DISPLACEMENT_UP, 0), "giam": by_type.get(T.DISPLACEMENT_DOWN, 0),
            },
            "fvg": {
                "so": fc["tao"], "moi_ngay": per_day(fc["tao"]),
                "tang": by_type.get(T.FVG_UP, 0), "giam": by_type.get(T.FVG_DOWN, 0),
                "tu_displacement": fc["tu_displacement"], "ty_le_tu_displacement": ratio(fc["tu_displacement"], fc["tao"]),
                "bo_vi_khoang_trong": fc["bo_vi_khoang_trong"], "bo_vi_nho": fc["bo_vi_nho"],
                "cham": fc["cham"], "lap": fc["lap"], "con_mo": dict(self._fvg.open),
            },
            "thanh_khoan": {
                "tang": "+".join(sorted(self._liq.tier_counts, key=lambda x: TIER_RANK.get(x, 0))) or POOL_TIER,
                "theo_tang": {k: dict(v) for k, v in sorted(self._liq.tier_counts.items(),
                                                            key=lambda kv: TIER_RANK.get(kv[0], 0))},
                "vung_tao": n_pools, "vung_moi_ngay": per_day(n_pools),
                "gop_eq": lc["gop_eq"], "khong_tao_da_bi_lay": lc["khong_tao_da_bi_lay"],
                "bi_lay": lc["lay"], "cham_truoc_khi_lay": lc["lay_sau_khi_cham"],
                "ty_le_cham_truoc_khi_lay": ratio(lc["lay_sau_khi_cham"], lc["lay"]),
                "xuyen_atr_trung_vi": _quantile(pen, 0.5), "xuyen_atr_p90": _quantile(pen, 0.9),
                "vung_sweep": lc["sweep"], "vung_sweep_cung_nen": lc["sweep_cung_nen"], "vung_run": lc["run"],
                "vung_chua_ro": lc["chua_ro"],
                "su_kien_sweep": n_sweep, "su_kien_run": n_run,
                "su_kien_chua_ro": by_type.get(T.LIQ_UNRESOLVED, 0),
                "con_nguyen_cuoi_run": self._liq.intact_count(),
                "dang_cho_cuoi_run": len(self._liq.pending()),
                "cua_so_sweep": self.params["sweep_window"],
            },
            "shift": {
                "so": n_shift, "moi_ngay": per_day(n_shift),
                "tang": by_type.get(T.SHIFT_UP, 0), "giam": by_type.get(T.SHIFT_DOWN, 0),
                "co_fvg": n_shift_fvg, "ty_le_co_fvg": ratio(n_shift_fvg, n_shift),
                "displacement_tren_nen_lay": self._shift_on_take_bar,
                "cung_nen_sweep": self._shift_on_sweep_bar,
                "theo_killzone": dict(sorted(self._shift_kz.items())),
                "theo_tang": dict(sorted(self._shift_tier.items())),
                "ung_vien": sc["ung_vien"], "huy_vuot_cuc_tri": sc["huy_vuot_cuc_tri"],
                "huy_khoang_trong": sc["huy_khoang_trong"], "het_cua_so": sc["het_cua_so"],
                "cua_so_shift": self.params["shift_window"],
            },
            "order_flow": {
                "ty_le_thoi_gian": {k: v / n for k, v in self._of_bars.items()},
                "doi_trang_thai": sum(by_type.get(x, 0) for x in T.ORDER_FLOW_TYPES),
                "doi_chieu": of_flips, "doi_chieu_moi_ngay": per_day(of_flips),
                "doan_chua_ro": len(of_zero), "doan_chua_ro_moi_ngay": per_day(len(of_zero)),
                "chua_ro_trung_vi_nen": med_zero,
                "chua_ro_trung_vi_gio": med_zero * bar_hours if med_zero is not None else None,
                "mot_chieu_trung_vi_nen": med_dir,
                "mot_chieu_trung_vi_gio": med_dir * bar_hours if med_dir is not None else None,
                "theo_ly_do": of_reasons,
                "ghi_chu_vi": _OF_NOTE_VI,
            },
            "khung_lon": {
                "bat": self._agg is not None,
                "moc": self.params["htf_alignment"],
                "khung": list(self.htf_frames),
                "khung_bo_qua": list(self.htf_skipped),
                "coverage_toi_thieu": self.params["htf_min_coverage"],
                "theo_khung": htf,
                "ky": periods,
                "gia_mo_ngay": {"co": self._levels.counts["ngay_co_gia_mo"],
                                "thieu": self._levels.counts["ngay_thieu_gia_mo"],
                                "midnight_open_co": self._levels.counts["midnight_co"]},
                "nen_degraded": list(self._htf_degraded),
            },
            "pd_array": {
                "che_do": self._pd.mode,
                "respect_away_atr": self._pd.away_atr if self._pd.mode == "strict" else None,
                "theo_khung": {k: dict(v) for k, v in sorted(pdc.items())},
                "su_kien": n_pd,
                "vung_con_mo_cuoi_run": len(self._pd.open_zones()),
                "pd_bias_doi": pd_changes,
                "pd_bias_doi_moi_ngay": per_day(pd_changes),
                "ty_le_thoi_gian_pd_bias": {k: v / n for k, v in self._pd_bars.items()},
            },
            "dol": {
                "tang_toi_thieu": self._dol.min_tier,
                "shift": dc["shift"], "co_dich": dc["co_dich"], "khong_co_vung": dc["khong_co_vung"],
                "dat": dc["dat"], "bi_thay": dc["bi_thay"],
                "khoang_cach_atr_trung_vi": _quantile(dist, 0.5), "khoang_cach_atr_p25": _quantile(dist, 0.25),
                "khoang_cach_atr_p90": _quantile(dist, 0.9),
                "tang_dich": dict(sorted(self._dol.tiers.items(), key=lambda kv: TIER_RANK.get(kv[0], 0))),
                "ty_le_thoi_gian": {k: v / n for k, v in self._dol_bars.items()},
                "ghi_chu_vi": "«Tỷ lệ đạt DOL» là nhãn đánh giá nhìn về sau — không phải đặc trưng hay đầu vào.",
            },
            "order_block": self._ob_stats(per_day, ratio),
            "ote": self._ote_stats(ratio),
            **({"nhan_dien": self._nd.stats(n)} if self._nd is not None else {}),     # [N] 0.6.0, khi bật
            "killzone_ty_le_nen": {k: v / n for k, v in sorted(self._kz_bars.items())},
            "ghi_chu_vi": (
                "Mật độ tính trên ngày giao dịch. «order» lẫn lộn là trạng thái hợp lệ (range hoặc chuyển "
                "tiếp), không phải lỗi. Vùng thanh khoản gồm tầng khung chạy (ITH/ITL), H1/H4 (ITH/ITL khung lớn) "
                "và D/W (PDH/PDL, PWH/PWL). Ba thành phần bias (thứ tự, pd_bias, DOL) không ghép (B3). Đây là mô tả "
                "hành vi, không phải accuracy — cần nhãn tham chiếu (D8)."
            ),
            "loai_khoang_trong_vi": GAP_TEXT_VI,
            "order_vi": {str(k) if k is not None else "none": v for k, v in ORDER_TEXT_VI.items()},
        }
