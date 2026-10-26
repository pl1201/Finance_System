"""Nhãn tham chiếu: lưu, liệt kê, xem, ghi đè, xuất / đọc CSV; auto label (chỉ đề xuất)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from backend.app.schemas.labels import (
    AutoLabelRequest,
    LabelCsvParseRequest,
    LabelSetRequest,
    LabelSetUpdateRequest,
)
from backend.app.services import auto_label, labels

router = APIRouter()


@router.post("/api/label-sets")
def create_label_set(req: LabelSetRequest) -> dict[str, Any]:
    return labels.save_label_set(
        dataset_id=req.dataset_id,
        annotator=req.annotator,
        version=req.version,
        rubric_vi=req.rubric_vi,
        labels=req.labels,
    )


@router.get("/api/label-sets")
def list_label_sets(dataset_id: Optional[str] = None) -> list[dict[str, Any]]:
    return labels.list_label_sets(dataset_id)


@router.get("/api/label-sets/{label_set_id}")
def get_label_set(label_set_id: str) -> dict[str, Any]:
    return labels.get_label_set_detail(label_set_id)


@router.put("/api/label-sets/{label_set_id}")
def overwrite_label_set(label_set_id: str, req: LabelSetUpdateRequest) -> dict[str, Any]:
    """Ghi đè bộ nhãn đã lưu. Tăng ``revision``; dataset không đổi."""
    return labels.update_label_set(
        label_set_id=label_set_id,
        annotator=req.annotator,
        version=req.version,
        rubric_vi=req.rubric_vi,
        labels=req.labels,
        confirm_overwrite=req.confirm_overwrite,
    )


@router.get("/api/label-sets/{label_set_id}/export.csv")
def export_label_set(label_set_id: str):
    filename, content = labels.export_label_set_csv(label_set_id)
    return PlainTextResponse(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="%s"' % filename},
    )


@router.get("/api/auto-label/algorithms")
def auto_label_algorithms() -> list[dict[str, Any]]:
    """Thuật toán dùng được để đề xuất nhãn cấu trúc, kèm loại nhãn sinh ra."""
    return auto_label.auto_label_algorithms()


@router.post("/api/auto-label/suggest")
def auto_label_suggest(req: AutoLabelRequest) -> dict[str, Any]:
    """Đề xuất nhãn trong khoảng nến. KHÔNG ghi vào kho nhãn — người phải duyệt."""
    return auto_label.suggest_auto_labels(
        dataset_id=req.dataset_id,
        algorithm=req.algorithm,
        params=req.params,
        start_index=req.start_index,
        end_index=req.end_index,
        types=req.types,
    )


@router.post("/api/label-sets/parse-csv")
def parse_label_csv(req: LabelCsvParseRequest) -> dict[str, Any]:
    """Đọc CSV nhãn thành bộ nháp đã kiểm tra. KHÔNG tự lưu vào kho nhãn."""
    return labels.parse_label_csv(dataset_id=req.dataset_id, csv_text=req.csv_text)
