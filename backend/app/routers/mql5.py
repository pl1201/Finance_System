"""Đối chiếu sự kiện Python với CSV do script MQL5 xuất."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from backend.app.schemas.evaluations import Mql5CompareRequest
from backend.app.services import mql5

router = APIRouter()


@router.post("/api/compare-mql5")
def compare_mql5(req: Mql5CompareRequest) -> dict[str, Any]:
    return mql5.compare_run_to_mql5(
        req.run_id, req.csv_text, req.csv_checksum,
        req.time_tolerance_bars, req.price_tolerance,
    )
