"""Request của nhóm lần chạy."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    dataset_id: str
    algorithm: str = "swing_pivot"
    params: dict[str, Any] = Field(default_factory=dict)
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    label: str = ""
    save: bool = True


class CompareRequest(BaseModel):
    run_id_a: str
    run_id_b: str
