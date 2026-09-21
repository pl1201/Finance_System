"""FastAPI app: API nghiên cứu cấu trúc thị trường + phục vụ giao diện tĩnh."""
from __future__ import annotations

import os
from typing import Any, Optional

from fastapi import Body, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.app import config, service
from backend.app.service import ServiceError, db

app = FastAPI(
    title="Market Structure Lab",
    description=(
        "Công cụ nghiên cứu thuật toán nhận diện cấu trúc thị trường. "
        "Chạy local, không kết nối broker, không gửi lệnh."
    ),
    version="0.2.1",
)


@app.exception_handler(ServiceError)
async def _service_error_handler(_request, exc: ServiceError):  # noqa: ANN001
    return JSONResponse(status_code=400, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Hệ thống
# ---------------------------------------------------------------------------


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "app": "market-structure-lab",
        "version": app.version,
        "db_path": config.DB_PATH,
        "canh_bao_vi": (
            "Đây là công cụ nghiên cứu cấu trúc thị trường. Không phải hệ thống "
            "giao dịch: không kết nối broker, không gửi lệnh, không tính P&L."
        ),
    }


@app.get("/api/algorithms")
def get_algorithms() -> list[dict[str, Any]]:
    return service.algorithms()


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------


@app.get("/api/datasets")
def get_datasets() -> list[dict[str, Any]]:
    return db.list_datasets()


@app.get("/api/datasets/{dataset_id}")
def get_dataset(dataset_id: str) -> dict[str, Any]:
    ds = db.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, "Không tìm thấy dataset %s" % dataset_id)
    return ds


@app.delete("/api/datasets/{dataset_id}")
def delete_dataset(dataset_id: str) -> dict[str, Any]:
    ds = db.get_dataset(dataset_id)
    if not ds:
        raise HTTPException(404, "Không tìm thấy dataset %s" % dataset_id)
    db.delete_dataset(dataset_id)
    return {"deleted": dataset_id}


@app.get("/api/datasets/{dataset_id}/bars")
def get_bars(
    dataset_id: str,
    start: Optional[str] = Query(None, description="ISO datetime, lọc bar_time >="),
    end: Optional[str] = Query(None, description="ISO datetime, lọc bar_time <="),
) -> dict[str, Any]:
    return service.bars_payload(dataset_id, start, end)


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


@app.post("/api/datasets/preview")
async def preview_dataset(file: UploadFile = File(...)) -> dict[str, Any]:
    text = await _read_upload(file)
    out = service.preview_upload(text)
    out["filename"] = file.filename
    return out


@app.post("/api/datasets/import")
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
    import json as _json

    text = await _read_upload(file)
    try:
        mapping = _json.loads(mapping_json or "{}")
    except ValueError as exc:
        raise ServiceError("mapping_json không phải JSON hợp lệ.") from exc
    return service.import_dataset(
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


@app.post("/api/datasets/seed-samples")
def seed_samples() -> dict[str, Any]:
    created = service.seed_sample_datasets()
    return {
        "created": created,
        "canh_bao_vi": (
            "Các dataset này là DỮ LIỆU MÔ PHỎNG do bộ sinh nội bộ tạo ra, "
            "không phải dữ liệu thị trường thật."
        ),
    }


class ResampleRequest(BaseModel):
    dataset_id: str
    target_timeframe: str
    gap_policy: str = "drop_incomplete"


@app.post("/api/datasets/resample")
def resample(req: ResampleRequest) -> dict[str, Any]:
    return service.resample_dataset(req.dataset_id, req.target_timeframe, req.gap_policy)


class Mt5ImportRequest(BaseModel):
    symbol: str
    timeframe: str
    source_timezone: str
    timestamp_convention: str
    count: Optional[int] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    terminal_path: str = ""
    price_type: str = "unspecified"
    name: str = ""
    notes: str = ""


@app.get("/api/mt5/status")
def mt5_status() -> dict[str, Any]:
    from core.data.mt5_source import mt5_available
    return {
        "available": mt5_available(),
        "note_vi": (
            "Gói MetaTrader5 là tuỳ chọn. Chưa cài thì lõi lab vẫn chạy. "
            "copy_rates_from_pos index 0 là nến đang hình thành — lab loại nến đó. "
            "Người dùng vẫn phải khai báo múi giờ nguồn và quy ước timestamp "
            "(MT5 thường là mốc MỞ, UTC)."
        ),
    }


@app.post("/api/datasets/import-mt5")
def import_mt5(req: Mt5ImportRequest) -> dict[str, Any]:
    return service.import_from_mt5(
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


# ---------------------------------------------------------------------------
# Chạy thử
# ---------------------------------------------------------------------------


class RunRequest(BaseModel):
    dataset_id: str
    algorithm: str = "swing_pivot"
    params: dict[str, Any] = Field(default_factory=dict)
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    label: str = ""
    save: bool = True


@app.post("/api/runs")
def create_run(req: RunRequest) -> dict[str, Any]:
    return service.execute_run(
        dataset_id=req.dataset_id,
        algorithm=req.algorithm,
        params=req.params,
        range_start=req.range_start,
        range_end=req.range_end,
        label=req.label,
        save=req.save,
    )


@app.get("/api/runs")
def list_runs(
    dataset_id: Optional[str] = None, limit: int = Query(200, ge=1, le=1000)
) -> list[dict[str, Any]]:
    return db.list_runs(dataset_id, limit)


@app.get("/api/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(404, "Không tìm thấy lần chạy %s" % run_id)
    run["events"] = db.get_events(run_id)
    return run


@app.get("/api/runs/{run_id}/manifest")
def get_manifest(run_id: str) -> dict[str, Any]:
    return service.run_manifest(run_id)


@app.delete("/api/runs/{run_id}")
def delete_run(run_id: str) -> dict[str, Any]:
    if not db.get_run(run_id):
        raise HTTPException(404, "Không tìm thấy lần chạy %s" % run_id)
    db.delete_run(run_id)
    return {"deleted": run_id}


@app.get("/api/runs/{run_id}/export.csv")
def export_run_csv(run_id: str):
    filename, content = service.export_events_csv(run_id)
    return PlainTextResponse(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="%s"' % filename},
    )


class CompareRequest(BaseModel):
    run_id_a: str
    run_id_b: str


@app.post("/api/compare")
def compare(req: CompareRequest) -> dict[str, Any]:
    return service.compare_runs(req.run_id_a, req.run_id_b)


class LabelSetRequest(BaseModel):
    dataset_id: str
    annotator: str
    version: str = "1"
    rubric_vi: str = ""
    labels: list[dict[str, Any]] = Field(default_factory=list)


@app.post("/api/label-sets")
def create_label_set(req: LabelSetRequest) -> dict[str, Any]:
    return service.save_label_set(
        dataset_id=req.dataset_id,
        annotator=req.annotator,
        version=req.version,
        rubric_vi=req.rubric_vi,
        labels=req.labels,
    )


@app.get("/api/label-sets")
def list_label_sets(dataset_id: Optional[str] = None) -> list[dict[str, Any]]:
    return service.db.list_label_sets(dataset_id)


@app.get("/api/label-sets/{label_set_id}")
def get_label_set(label_set_id: str) -> dict[str, Any]:
    ls = service.db.get_label_set(label_set_id)
    if not ls:
        raise HTTPException(404, "Không tìm thấy bộ nhãn %s" % label_set_id)
    return ls


class EvaluateRequest(BaseModel):
    run_id: str
    label_set_id: str
    time_tolerance_bars: int = 1
    price_tolerance: float = 0.0


@app.post("/api/evaluate")
def evaluate(req: EvaluateRequest) -> dict[str, Any]:
    return service.evaluate_run_against_labels(
        req.run_id, req.label_set_id, req.time_tolerance_bars, req.price_tolerance
    )


class Mql5CompareRequest(BaseModel):
    run_id: str
    csv_text: str
    csv_checksum: Optional[str] = None
    time_tolerance_bars: int = 0
    price_tolerance: float = 0.0


@app.post("/api/compare-mql5")
def compare_mql5(req: Mql5CompareRequest) -> dict[str, Any]:
    return service.compare_run_to_mql5(
        req.run_id, req.csv_text, req.csv_checksum,
        req.time_tolerance_bars, req.price_tolerance,
    )


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


class ReplayCreateRequest(BaseModel):
    dataset_id: str
    algorithm: str = "swing_pivot"
    params: dict[str, Any] = Field(default_factory=dict)
    range_start: Optional[str] = None
    range_end: Optional[str] = None
    start_index: int = -1


@app.post("/api/replay")
def replay_create(req: ReplayCreateRequest) -> dict[str, Any]:
    sid, snap = service.replay_store.create(
        dataset_id=req.dataset_id,
        algorithm=req.algorithm,
        params=req.params,
        range_start=req.range_start,
        range_end=req.range_end,
    )
    if req.start_index >= 0:
        snap = service.replay_store.seek(sid, req.start_index)
    return snap


@app.get("/api/replay/{sid}")
def replay_get(sid: str) -> dict[str, Any]:
    return service.replay_store.snapshot(sid)


@app.get("/api/replay/{sid}/bars")
def replay_bars(sid: str) -> dict[str, Any]:
    return {"bars": service.replay_store.bars(sid)}


@app.post("/api/replay/{sid}/step")
def replay_step(sid: str, n: int = Body(1, embed=True)) -> dict[str, Any]:
    return service.replay_store.step(sid, n)


@app.post("/api/replay/{sid}/back")
def replay_back(sid: str, n: int = Body(1, embed=True)) -> dict[str, Any]:
    return service.replay_store.back(sid, n)


@app.post("/api/replay/{sid}/seek")
def replay_seek(sid: str, index: int = Body(..., embed=True)) -> dict[str, Any]:
    return service.replay_store.seek(sid, index)


@app.post("/api/replay/{sid}/reset")
def replay_reset(sid: str) -> dict[str, Any]:
    return service.replay_store.reset(sid)


@app.delete("/api/replay/{sid}")
def replay_close(sid: str) -> dict[str, Any]:
    service.replay_store.close(sid)
    return {"closed": sid}


@app.post("/api/replay/{sid}/close")
def replay_close_post(sid: str) -> dict[str, Any]:
    """Bản POST để trình duyệt gọi được bằng ``navigator.sendBeacon`` khi đóng tab."""
    service.replay_store.close(sid)
    return {"closed": sid}


# ---------------------------------------------------------------------------
# Giao diện tĩnh
# ---------------------------------------------------------------------------

if os.path.isdir(config.FRONTEND_DIR):
    app.mount(
        "/app",
        StaticFiles(directory=config.FRONTEND_DIR, html=True),
        name="frontend",
    )

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(os.path.join(config.FRONTEND_DIR, "index.html"))
