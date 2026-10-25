"""Live chỉ đọc từ MT5: tạo luồng, xem như replay ghim ở nến cuối, điểm forward. Không có route gửi lệnh."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter

from backend.app.schemas.live import LiveCreateRequest, LiveHintRequest
from backend.app.services.live import live_manager

router = APIRouter()


@router.get("/api/live")
def live_list() -> dict[str, Any]:
    return live_manager.list_feeds()


@router.post("/api/live")
def live_create(req: LiveCreateRequest) -> dict[str, Any]:
    return live_manager.create(**req.model_dump())


@router.post("/api/live/hint")
def live_hint(req: LiveHintRequest) -> dict[str, Any]:
    """Gợi ý kiểm khai báo giờ server: giờ tick cuối − đồng hồ máy (không tự áp). POST JSON — trang lạ không gọi được
    (preflight), vì lời gọi nối terminal MT5."""
    return live_manager.hint(**req.model_dump())


@router.get("/api/live/{feed_id}")
def live_snapshot(feed_id: str, since: Optional[int] = None) -> dict[str, Any]:
    return live_manager.snapshot(feed_id, since)


@router.get("/api/live/{feed_id}/bars")
def live_bars(feed_id: str) -> dict[str, Any]:
    return {"bars": live_manager.bars(feed_id)}


@router.get("/api/live/{feed_id}/forward")
def live_forward(feed_id: str) -> dict[str, Any]:
    return live_manager.forward_scores(feed_id)


@router.post("/api/live/{feed_id}/stop")
def live_stop(feed_id: str) -> dict[str, Any]:
    return live_manager.stop(feed_id)


@router.post("/api/live/{feed_id}/resume")
def live_resume(feed_id: str) -> dict[str, Any]:
    return live_manager.resume(feed_id)
