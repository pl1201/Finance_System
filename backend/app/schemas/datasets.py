"""Request của nhóm dataset."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class ResampleRequest(BaseModel):
    dataset_id: str
    target_timeframe: str
    gap_policy: str = "drop_incomplete"


class Mt5ImportRequest(BaseModel):
    symbol: str
    timeframe: str
    source_timezone: str
    timestamp_convention: str
    count: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    terminal_path: str = ""
    price_type: str = "unspecified"
    name: str = ""
    notes: str = ""
