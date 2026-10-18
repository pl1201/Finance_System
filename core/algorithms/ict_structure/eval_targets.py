"""Mục tiêu chấm của ``ict_structure`` trên trang Đánh giá (ghép qua ``core.eval.targets``).

Một mục tiêu «shift» (D8: bạn gán nhãn ITH/ITL — đã có mục tiêu swing cấp 2 — và shift). Phía "high"
= shift giảm (sau quét BSL), "low" = shift tăng. Sweep → shift → shift_fvg mang cùng ``group_id`` và là
**một** cơ hội: mặc định chấm ``SHIFT_*``; muốn chấm tầng có FVG thì đổi ``event_type_map`` thành
``SHIFT_FVG_UP → SHIFT_UP``, ``SHIFT_FVG_DOWN → SHIFT_DOWN`` (không đếm cả hai tầng).
"""
from __future__ import annotations

from core.eval.targets import EvalTarget
from core.types import StructureType

TARGET_SHIFT = "ict_shift"

SHIFT_TYPES = (StructureType.SHIFT_UP, StructureType.SHIFT_DOWN)

EVAL_TARGETS = (
    EvalTarget(
        id=TARGET_SHIFT,
        label_vi="Shift — quét rồi displacement ngược chiều (ict_structure)",
        label_types=SHIFT_TYPES,
        help_vi=(
            "Chấm SHIFT_UP/DOWN: nhãn đặt ở NẾN DISPLACEMENT của shift, giá = close nến đó. Một-một, "
            "cùng hướng. Mặc định chấm tầng SHIFT; để chấm tầng có FVG, đổi ánh xạ SHIFT_FVG_* → SHIFT_* "
            "(sự kiện SHIFT_FVG nằm ở cùng nến displacement) — không đếm cả hai tầng."
        ),
        high_types=(StructureType.SHIFT_DOWN,),
        low_types=(StructureType.SHIFT_UP,),
    ),
)
