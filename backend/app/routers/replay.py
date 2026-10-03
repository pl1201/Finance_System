"""Replay từng nến.

``since`` (tuỳ chọn, mọi thao tác replay): client đã có dữ liệu tới nến này →
chỉ trả phần sự kiện/timeline mới hơn (``delta_since``). Không gửi = trả đủ.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body

from backend.app.schemas.replay import ReplayCreateRequest
from backend.app.services.replay import replay_store

router = APIRouter()


@router.post("/api/replay")
def replay_create(req: ReplayCreateRequest) -> dict[str, Any]:
    sid, snap = replay_store.create(
        dataset_id=req.dataset_id,
        algorithm=req.algorithm,
        params=req.params,
        range_start=req.range_start,
        range_end=req.range_end,
    )
    if req.start_index >= 0:
        snap = replay_store.seek(sid, req.start_index)
    return snap


@router.get("/api/replay/{sid}")
def replay_get(sid: str) -> dict[str, Any]:
    return replay_store.snapshot(sid)


@router.get("/api/replay/{sid}/bars")
def replay_bars(sid: str) -> dict[str, Any]:
    return {"bars": replay_store.bars(sid)}


@router.post("/api/replay/{sid}/step")
def replay_step(
    sid: str, n: int = Body(1, embed=True), since: Optional[int] = Body(None, embed=True)
) -> dict[str, Any]:
    return replay_store.step(sid, n, since)


@router.post("/api/replay/{sid}/next-event")
def replay_next_event(sid: str, since: Optional[int] = Body(None, embed=True)) -> dict[str, Any]:
    """Tiến từng nến tới lần xác nhận sự kiện kế tiếp (không nhìn trước)."""
    return replay_store.next_event(sid, since)


@router.post("/api/replay/{sid}/back")
def replay_back(
    sid: str, n: int = Body(1, embed=True), since: Optional[int] = Body(None, embed=True)
) -> dict[str, Any]:
    return replay_store.back(sid, n, since)


@router.post("/api/replay/{sid}/seek")
def replay_seek(
    sid: str, index: int = Body(..., embed=True), since: Optional[int] = Body(None, embed=True)
) -> dict[str, Any]:
    return replay_store.seek(sid, index, since)


@router.post("/api/replay/{sid}/reset")
def replay_reset(sid: str) -> dict[str, Any]:
    return replay_store.reset(sid)


@router.delete("/api/replay/{sid}")
def replay_close(sid: str) -> dict[str, Any]:
    replay_store.close(sid)
    return {"closed": sid}


@router.post("/api/replay/{sid}/close")
def replay_close_post(sid: str) -> dict[str, Any]:
    """Bản POST để trình duyệt gọi được bằng ``navigator.sendBeacon`` khi đóng tab."""
    replay_store.close(sid)
    return {"closed": sid}
