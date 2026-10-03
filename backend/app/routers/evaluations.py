"""Đánh giá: ghép nhãn (tab cũ), protocol trang Đánh giá, đánh giá đã lưu, báo cáo."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse

from backend.app.schemas.evaluations import AlgorithmEvalRequest, EvaluateRequest
from backend.app.services import evaluations

router = APIRouter()


@router.post("/api/evaluate")
def evaluate(req: EvaluateRequest) -> dict[str, Any]:
    """Ghép tham lam của tab Nhãn tham chiếu (không phải protocol trang đánh giá)."""
    return evaluations.evaluate_run_against_labels(
        req.run_id, req.label_set_id, req.time_tolerance_bars, req.price_tolerance
    )


@router.get("/api/eval/meta")
def eval_meta() -> dict[str, Any]:
    return evaluations.eval_meta()


@router.post("/api/evaluations")
def create_evaluation(req: AlgorithmEvalRequest) -> dict[str, Any]:
    ls = (req.label_set_id or "").strip() or None
    base = (req.baseline_run_id or "").strip() or None
    return evaluations.evaluate_algorithm_runs(
        run_ids=req.run_ids,
        protocol_raw=req.protocol,
        label_set_id=ls,
        baseline_run_id=base,
        save=req.save,
        note_vi=req.note_vi or "",
    )


@router.get("/api/evaluations")
def list_evaluations(
    dataset_id: Optional[str] = None, limit: int = Query(50, ge=1, le=200)
) -> list[dict[str, Any]]:
    return evaluations.list_evaluations(dataset_id, limit)


@router.get("/api/evaluations/{eval_id}")
def get_evaluation(eval_id: str) -> dict[str, Any]:
    return evaluations.get_evaluation(eval_id)


@router.delete("/api/evaluations/{eval_id}")
def delete_evaluation(eval_id: str) -> dict[str, Any]:
    return evaluations.delete_evaluation(eval_id)


@router.get("/api/evaluations/{eval_id}/report.md")
def evaluation_report(eval_id: str):
    filename, content = evaluations.evaluation_report_markdown(eval_id)
    return PlainTextResponse(
        content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="%s"' % filename},
    )
