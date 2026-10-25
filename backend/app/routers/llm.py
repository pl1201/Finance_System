"""Trợ lý tổng hợp (LLM qua OpenRouter) cho trang Live MT5 và trang Thử nghiệm (Replay) — chỉ đọc trạng thái thuật toán,
không khuyên giao dịch."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.app.schemas.llm import LlmChatRequest
from backend.app.services import llm

router = APIRouter()


@router.get("/api/llm/status")
def llm_status() -> dict[str, Any]:
    return llm.status()


@router.post("/api/llm/chat")
def llm_chat(req: LlmChatRequest) -> dict[str, Any]:
    return llm.chat(req.nguon, req.nguon_id, req.mode, req.cau_hoi, [m.model_dump() for m in req.lich_su], req.digits)
