"""Dataset: liệt kê, xem, xoá, đọc nến, xem trước / nhập CSV, dữ liệu mẫu, tổng hợp, MT5."""
from __future__ import annotations

import json
from typing import Any, Optional

from fastapi import APIRouter, File, Form, Query, UploadFile

from backend.app import config
from backend.app.errors import ServiceError
from backend.app.schemas.datasets import Mt5ImportRequest, ResampleRequest
from backend.app.services import datasets

router = APIRouter()


@router.get("/api/datasets")
def get_datasets() -> list[dict[str, Any]]:
    return datasets.list_datasets()


@router.get("/api/datasets/{dataset_id}")
def get_dataset(dataset_id: str) -> dict[str, Any]:
    return datasets.get_dataset(dataset_id)


@router.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: str) -> dict[str, Any]:
    return datasets.delete_dataset(dataset_id)


@router.get("/api/datasets/{dataset_id}/bars")
def get_bars(
    dataset_id: str,
    start: Optional[str] = Query(None, description="ISO datetime, lọc bar_time >="),
    end: Optional[str] = Query(None, description="ISO datetime, lọc bar_time <="),
) -> dict[str, Any]:
    return datasets.bars_payload(dataset_id, start, end)


async def _read_upload(file: UploadFile) -> str:
    raw = await file.read()
    if len(raw) > config.MAX_UPLOAD_BYTES:
        raise ServiceError(
            "File quá lớn (%.1f MB, giới hạn %d MB)."
            % (len(raw) / 1e6, config.MAX_UPLOAD_BYTES // (1024 * 1024))
        )
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ServiceError("Không giải mã được nội dung file. Hãy lưu lại dạng UTF-8.")


@router.post("/api/datasets/preview")
async def preview_dataset(file: UploadFile = File(...)) -> dict[str, Any]:
    text = await _read_upload(file)
    out = datasets.preview_upload(text)
    out["filename"] = file.filename
    return out


@router.post("/api/datasets/import")
async def import_dataset(
    file: UploadFile = File(...),
    name: str = Form(""),
    symbol: str = Form(...),
    timeframe: str = Form(""),
    source: str = Form(""),
    source_timezone: str = Form(...),
    timestamp_convention: str = Form(...),
    price_type: str = Form("unspecified"),
    notes: str = Form(""),
    mapping_json: str = Form("{}"),
) -> dict[str, Any]:
    text = await _read_upload(file)
    try:
        mapping = json.loads(mapping_json or "{}")
    except ValueError as exc:
        raise ServiceError("mapping_json không phải JSON hợp lệ.") from exc
    return datasets.import_dataset(
        text=text,
        filename=file.filename or "upload.csv",
        name=name,
        symbol=symbol,
        timeframe=timeframe,
        source=source,
        source_timezone=source_timezone,
        timestamp_convention=timestamp_convention,
        price_type=price_type,
        mapping=mapping or None,
        notes=notes,
        is_synthetic=False,
    )


@router.post("/api/datasets/seed-samples")
def seed_samples() -> dict[str, Any]:
    created = datasets.seed_sample_datasets()
    return {
        "created": created,
        "canh_bao_vi": (
            "Các dataset này là DỮ LIỆU MÔ PHỎNG do bộ sinh nội bộ tạo ra, "
            "không phải dữ liệu thị trường thật."
        ),
    }


@router.post("/api/datasets/resample")
def resample(req: ResampleRequest) -> dict[str, Any]:
    return datasets.resample_dataset(req.dataset_id, req.target_timeframe, req.gap_policy)


@router.post("/api/datasets/import-mt5")
def import_mt5(req: Mt5ImportRequest) -> dict[str, Any]:
    return datasets.import_from_mt5(
        symbol=req.symbol,
        timeframe=req.timeframe,
        source_timezone=req.source_timezone,
        timestamp_convention=req.timestamp_convention,
        count=req.count,
        date_from=req.date_from,
        date_to=req.date_to,
        terminal_path=req.terminal_path,
        price_type=req.price_type,
        name=req.name,
        notes=req.notes,
    )
