"""Request của nhóm live (MT5 chỉ đọc, plan_mt5_live.md)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class LiveCreateRequest(BaseModel):
    symbol: str
    mt5_symbol: str = ""
    timeframe: str = "M15"
    server_tz: str
    history_bars: int = 20_000
    params: dict[str, Any] = Field(default_factory=dict)
    terminal_path: str = ""


class LiveHintRequest(BaseModel):
    mt5_symbol: str
    server_tz: str = ""
    terminal_path: str = ""
