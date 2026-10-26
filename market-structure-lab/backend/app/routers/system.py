"""Hệ thống: tình trạng backend, danh sách thuật toán, trạng thái gói MT5."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from backend.app import config
from backend.app.services import datasets, runs

router = APIRouter()


@router.get("/api/health")
def health(request: Request) -> dict[str, Any]:
    return {
        "status": "ok",
        "app": "market-structure-lab",
        "version": request.app.version,
        "db_path": config.DB_PATH,
        "canh_bao_vi": (
            "Đây là công cụ nghiên cứu cấu trúc thị trường. Không phải hệ thống "
            "giao dịch: không kết nối broker, không gửi lệnh, không tính P&L."
        ),
    }


@router.get("/api/algorithms")
def get_algorithms() -> list[dict[str, Any]]:
    return runs.algorithms()


@router.get("/api/mt5/status")
def mt5_status() -> dict[str, Any]:
    return datasets.mt5_status()
