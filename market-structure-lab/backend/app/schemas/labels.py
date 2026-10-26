"""Request của nhóm nhãn tham chiếu và auto label."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class LabelSetRequest(BaseModel):
    dataset_id: str
    annotator: str
    version: str = "1"
    rubric_vi: str = ""
    labels: list[dict[str, Any]] = Field(default_factory=list)


class LabelSetUpdateRequest(BaseModel):
    annotator: str
    version: str = "1"
    rubric_vi: str = ""
    labels: list[dict[str, Any]] = Field(default_factory=list)
    confirm_overwrite: bool = False


class LabelCsvParseRequest(BaseModel):
    dataset_id: str
    csv_text: str


class AutoLabelRequest(BaseModel):
    dataset_id: str
    algorithm: str = "swing_pivot"
    params: dict[str, Any] = Field(default_factory=dict)
    start_index: Optional[int] = None
    end_index: Optional[int] = None
    types: Optional[list[str]] = None
