"""Request của nhóm replay."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ReplayCreateRequest(BaseModel):
    dataset_id: str
    algorithm: str = "swing_pivot"
    params: dict[str, Any] = Field(default_factory=dict)
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    start_index: int = -1
