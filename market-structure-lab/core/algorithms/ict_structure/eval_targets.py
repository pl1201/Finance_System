"""Mục tiêu chấm của ``ict_structure`` trên trang Đánh giá (ghép qua ``core.eval.targets``).

0.10.0: thêm mục tiêu «MSS» (``MSS_*``, sự kiện đổi hướng mặc định — plan_mss_ob_pd.md); mục tiêu shift giữ cho chế độ
``doi_huong = shift``.

Một mục tiêu «shift» (D8: bạn gán nhãn ITH/ITL — đã có mục tiêu swing cấp 2 — và shift). Phía "high"
= shift giảm (sau quét BSL), "low" = shift tăng. Sweep → shift → shift_fvg mang cùng ``group_id`` và là
**một** cơ hội: mặc định chấm ``SHIFT_*``; muốn chấm tầng có FVG thì đổi ``event_type_map`` thành
``SHIFT_FVG_UP → SHIFT_UP``, ``SHIFT_FVG_DOWN → SHIFT_DOWN`` (không đếm cả hai tầng).
"""
from __future__ import annotations

from core.eval.targets import EvalTarget
from core.types import StructureType

TARGET_SHIFT = "ict_shift"
TARGET_MSS = "ict_mss"

SHIFT_TYPES = (StructureType.SHIFT_UP, StructureType.SHIFT_DOWN)
MSS_TYPES = StructureType.MSS_TYPES

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
    EvalTarget(
        id=TARGET_MSS,
        label_vi="MSS — quét rồi close phá STL / STH trước cú chạy (ict_structure)",
        label_types=MSS_TYPES,
        help_vi=(
            "Chấm MSS_UP/DOWN: nhãn đặt ở NẾN PHÁ (close vượt STL / STH), giá = mức STL / STH bị phá (trang Gán nhãn gợi ý close "
            "nến phá — sửa về mức STL / STH nếu cách xa hơn dung sai giá). Một-một, cùng hướng. "
            "MSS_FVG_* là tầng phụ (cùng group_id) — không đếm cả hai tầng."
        ),
        high_types=(StructureType.MSS_DOWN,),
        low_types=(StructureType.MSS_UP,),
    ),
)
