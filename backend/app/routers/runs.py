"""Lần chạy: chạy, liệt kê, mở lại, manifest, chỉ số riêng, xoá, xuất CSV, so sánh."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Query, Request
from fastapi.responses import PlainTextResponse

from backend.app.schemas.runs import CompareRequest, RunRequest
from backend.app.services import runs

router = APIRouter()


@router.post("/api/runs")
def create_run(req: RunRequest) -> dict[str, Any]:
    return runs.execute_run(
        dataset_id=req.dataset_id,
        algorithm=req.algorithm,
        params=req.params,
        range_start=req.range_start,
        range_end=req.range_end,
        label=req.label,
        save=req.save,
    )


@router.get("/api/runs")
def list_runs(
    dataset_id: Optional[str] = None, limit: int = Query(200, ge=1, le=1000)
) -> list[dict[str, Any]]:
    return runs.list_runs(dataset_id, limit)


@router.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    return runs.get_run_with_events(run_id)


@router.get("/api/runs/{run_id}/manifest")
def get_manifest(run_id: str) -> dict[str, Any]:
    return runs.run_manifest(run_id)


@router.get("/api/runs/{run_id}/metrics")
def get_algorithm_metrics(run_id: str, request: Request) -> dict[str, Any]:
    """Chỉ số đánh giá riêng của thuật toán (vd ``?horizon=16`` cho c2_cisd_research)."""
    return runs.algorithm_metrics(run_id, dict(request.query_params))


@router.get("/api/runs/{run_id}/c2-cisd-metrics")
def get_c2_cisd_metrics(run_id: str, horizon: int = Query(16, ge=1, le=500)) -> dict[str, Any]:
    return runs.c2_cisd_run_metrics(run_id, horizon)


@router.delete("/api/runs/{run_id}")
def delete_run(run_id: str) -> dict[str, Any]:
    return runs.delete_run(run_id)


@router.get("/api/runs/{run_id}/export.csv")
def export_run_csv(run_id: str):
    filename, content = runs.export_events_csv(run_id)
    return PlainTextResponse(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="%s"' % filename},
    )


@router.post("/api/compare")
def compare(req: CompareRequest) -> dict[str, Any]:
    return runs.compare_runs(req.run_id_a, req.run_id_b)
