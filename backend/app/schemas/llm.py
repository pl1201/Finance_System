"""Request của trợ lý tổng hợp (plan_tro_ly_tong_hop.md)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class LlmChatRequest(BaseModel):
    feed_id: str
    mode: Literal["tong_hop", "hoi"] = "hoi"
    cau_hoi: str = ""
    lich_su: list[ChatMessage] = Field(default_factory=list)
    digits: int = Field(2, ge=0, le=8, description="số chữ số giá như chart (MSL.format.detectDigits)")
