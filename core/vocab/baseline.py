"""Từ vựng sự kiện: Đối chứng chỉ báo và HMM (``indicator_baseline``, ``hmm_online``).

Ghép vào ``core.types.StructureType`` / ``ReasonCode`` / ``*_TEXT_VI``.
"""
from __future__ import annotations


class BaselineType:
    BASELINE_UP = "BASELINE_UP"
    BASELINE_DOWN = "BASELINE_DOWN"
    BASELINE_RANGE = "BASELINE_RANGE"
    BASELINE_UNCERTAIN = "BASELINE_UNCERTAIN"
    HMM_STATE_CHANGE = "HMM_STATE_CHANGE"

    BASELINE_ALL = (
        BASELINE_UP, BASELINE_DOWN, BASELINE_RANGE, BASELINE_UNCERTAIN,
        HMM_STATE_CHANGE,
    )


class BaselineReason:
    BASELINE_RULE_CROSS = "BASELINE_RULE_CROSS"
    HMM_FILTERED_STATE_CHANGE = "HMM_FILTERED_STATE_CHANGE"


#: Giải thích tiếng Việt cho từng loại sự kiện.
STRUCTURE_TEXT_VI: dict[str, str] = {
    BaselineType.BASELINE_UP: "Baseline chỉ báo: hướng tăng",
    BaselineType.BASELINE_DOWN: "Baseline chỉ báo: hướng giảm",
    BaselineType.BASELINE_RANGE: "Baseline chỉ báo: biên độ hẹp / ADX yếu",
    BaselineType.BASELINE_UNCERTAIN: "Baseline chỉ báo: chưa đủ điều kiện",
    BaselineType.HMM_STATE_CHANGE: "HMM online: state lọc (forward) đổi",
}

#: Giải thích tiếng Việt cho từng mã lý do (tooltip giao diện).
REASON_TEXT_VI: dict[str, str] = {
    BaselineReason.BASELINE_RULE_CROSS: (
        "Phân loại baseline chỉ báo thay đổi: độ dốc SMA chuẩn hoá ATR, ADX và "
        "bề rộng vùng giá (Donchian/ATR) thỏa bộ ngưỡng đã khai báo."
    ),
    BaselineReason.HMM_FILTERED_STATE_CHANGE: (
        "State MAP của bộ lọc HMM online (bước forward) thay đổi so với nến trước. "
        "Không dùng smoothing/Viterbi trên toàn chuỗi."
    ),
}
