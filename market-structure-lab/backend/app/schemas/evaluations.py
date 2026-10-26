"""Request của nhóm đánh giá và đối chiếu MQL5."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class EvaluateRequest(BaseModel):
    run_id: str
    label_set_id: str
    time_tolerance_bars: int = 1
    price_tolerance: float = 0.0


class AlgorithmEvalRequest(BaseModel):
    run_ids: list[str]
    protocol: dict[str, Any] = Field(default_factory=dict)
    label_set_id: Optional[str] = None
    baseline_run_id: Optional[str] = None
    save: bool = True
    note_vi: str = ""


class Mql5CompareRequest(BaseModel):
    run_id: str
    csv_text: str
    csv_checksum: Optional[str] = None
    time_tolerance_bars: int = 0
    price_tolerance: float = 0.0
