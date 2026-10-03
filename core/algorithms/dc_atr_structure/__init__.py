"""Directional Change theo CLOSE với ngưỡng ATR khoá tại cực trị + phân loại regime.

Đặc tả: ``docs/thuat_toan_dc_atr_structure.md``.

| Module | Việc |
|---|---|
| ``algorithm`` | ``DcAtrStructureAlgorithm``: gap/segment, ATR, thứ tự trong nến, sự kiện |
| ``detector`` | ``DcDetector`` — DC thuần trên close, không biết regime |
| ``regime`` | ``RegimeClassifier`` Trend/Range/Chưa rõ từ pivot đã xác nhận |
| ``metrics`` | metric không cần nhãn + ánh xạ chấm chéo định nghĩa |
"""
from core.algorithms.dc_atr_structure.algorithm import (
    GAP_BRIDGE_SHORT,
    GAP_POLICIES,
    GAP_RESET,
    REGIME_WARMUP,
    DcAtrStructureAlgorithm,
)
from core.algorithms.dc_atr_structure.detector import (
    PHASE_SEEK_DIRECTION,
    PHASE_SEEK_HIGH,
    PHASE_SEEK_LOW,
    PHASE_TEXT_VI,
    PHASE_WAIT_ATR,
    PHASE_WARMUP,
    Candidate,
    DcDetector,
    DcPivot,
)

__all__ = [
    "DcAtrStructureAlgorithm", "DcDetector", "Candidate", "DcPivot",
    "PHASE_WARMUP", "PHASE_WAIT_ATR", "PHASE_SEEK_DIRECTION", "PHASE_SEEK_HIGH", "PHASE_SEEK_LOW",
    "PHASE_TEXT_VI", "REGIME_WARMUP", "GAP_RESET", "GAP_BRIDGE_SHORT", "GAP_POLICIES",
]
