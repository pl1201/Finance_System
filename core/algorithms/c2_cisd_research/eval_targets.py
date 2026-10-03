"""Mục tiêu chấm của ``c2_cisd_research`` trên trang Đánh giá (ghép qua ``core.eval.targets``).

Ghép một-một cùng loại, cùng hướng. Phía "high" = C2/CISD giảm (quét high), "low" = tăng.
Không dùng nhãn HH/MSS làm nhãn thay cho C2/CISD.
"""
from __future__ import annotations

from core.eval.targets import EvalTarget

TARGET_C2 = "c2"
TARGET_CISD = "cisd"

C2_TYPES = ("C2_CONFIRMED_UP", "C2_CONFIRMED_DOWN")
CISD_TYPES = ("CISD_CONFIRMED_UP", "CISD_CONFIRMED_DOWN")

EVAL_TARGETS = (
    EvalTarget(
        id=TARGET_C2,
        label_vi="C2 sweep H4 (c2_cisd_research)",
        label_types=C2_TYPES,
        help_vi=(
            "Chấm C2_CONFIRMED_UP/DOWN: nhãn đặt ở NẾN M15 CỰC TRỊ của C2, giá = low "
            "(tăng) / high (giảm). Một-một, cùng hướng. Chỉ khi đã có nhãn C2 do người gán "
            "— không dựng F1 từ output của chính thuật toán hay từ nhãn HH/MSS."
        ),
        high_types=("C2_CONFIRMED_DOWN",),
        low_types=("C2_CONFIRMED_UP",),
    ),
    EvalTarget(
        id=TARGET_CISD,
        label_vi="CISD xác nhận cho setup C2 (c2_cisd_research)",
        label_types=CISD_TYPES,
        help_vi=(
            "Chấm CISD_CONFIRMED_UP/DOWN: nhãn đặt ở nến có CLOSE vượt mức CISD (nến bằng "
            "chứng), giá = mức CISD. Early CISD của setup cũng là CISD_CONFIRMED. Nếu nhãn "
            "không ghi đúng mức, nới dung sai giá hoặc chỉ chấm theo thời gian."
        ),
        high_types=("CISD_CONFIRMED_DOWN",),
        low_types=("CISD_CONFIRMED_UP",),
    ),
)
