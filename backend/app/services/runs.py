"""Lần chạy: chạy thuật toán, lưu / mở lại / xoá, so sánh hai run, xuất CSV, manifest."""
from __future__ import annotations

import csv
import io
import json
import uuid
from typing import Any, Optional

from backend.app.errors import NotFoundError, ServiceError
from backend.app.services.common import db, get_dataset_or_error, load_bars
from backend.app.storage import utcnow_iso
from core.engine import run_algorithm
from core.registry import get_algorithm_class, list_algorithms


def list_runs(dataset_id: Optional[str], limit: int) -> list[dict[str, Any]]:
    return db.list_runs(dataset_id, limit)


def get_run_with_events(run_id: str) -> dict[str, Any]:
    run = db.get_run(run_id)
    if not run:
        raise NotFoundError("Không tìm thấy lần chạy %s" % run_id)
    run["events"] = db.get_events(run_id)
    return run


def delete_run(run_id: str) -> dict[str, Any]:
    if not db.get_run(run_id):
        raise NotFoundError("Không tìm thấy lần chạy %s" % run_id)
    db.delete_run(run_id)
    return {"deleted": run_id}


def execute_run(
    *,
    dataset_id: str,
    algorithm: str,
    params: dict[str, Any] | None,
    range_start: Optional[str] = None,
    range_end: Optional[str] = None,
    label: str = "",
    save: bool = True,
) -> dict[str, Any]:
    ds, bars, source_indices = load_bars(dataset_id, range_start, range_end)
    try:
        cls = get_algorithm_class(algorithm)
        norm_params = cls.validate_params(params)
        cls.check_dataset(ds["timeframe"], norm_params)
        algo = cls(**norm_params)
    except (KeyError, ValueError) as exc:
        raise ServiceError(str(exc)) from exc

    try:
        result = run_algorithm(bars, algo)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc
    run_id = "run_" + uuid.uuid4().hex[:12]
    events = [e.to_dict() for e in result.events]

    run_row = {
        "run_id": run_id,
        "label": label or "",
        "dataset_id": dataset_id,
        "dataset_checksum": ds["checksum_sha256"],
        "symbol": ds["symbol"],
        "timeframe": ds["timeframe"],
        "algorithm": algo.name,
        "algorithm_version": algo.version,
        "params_json": json.dumps(norm_params, ensure_ascii=False),
        "range_start": bars[0].bar_time.isoformat(),
        "range_end": bars[-1].bar_time.isoformat(),
        "range_start_index": source_indices[0],
        "range_end_index": source_indices[-1],
        "bars_processed": result.bars_processed,
        "warmup_bars": result.warmup_bars,
        "duration_ms": result.duration_ms,
        "data_status": result.data_status,
        "stats_json": json.dumps(result.stats, ensure_ascii=False),
        "created_at": utcnow_iso(),
    }
    if save:
        db.insert_run(run_row, events)

    payload = dict(run_row)
    payload.pop("params_json")
    payload.pop("stats_json")
    payload["params"] = norm_params
    payload["stats"] = result.stats
    payload["saved"] = save
    payload["dataset_name"] = ds["name"]
    payload["is_synthetic"] = ds["is_synthetic"]
    payload["data_status_message_vi"] = result.data_status_message_vi
    payload["events"] = events
    payload["timeline"] = result.timeline
    payload["pending_state"] = algo.pending_state()
    return payload


def compare_runs(run_id_a: str, run_id_b: str) -> dict[str, Any]:
    a = db.get_run(run_id_a)
    b = db.get_run(run_id_b)
    if not a or not b:
        raise ServiceError("Không tìm thấy một trong hai lần chạy cần so sánh.")

    warnings: list[str] = []
    if a["dataset_id"] != b["dataset_id"]:
        warnings.append(
            "Hai lần chạy dùng DATASET KHÁC NHAU. Khác biệt kết quả có thể do dữ liệu, "
            "không chỉ do tham số."
        )
    elif a["dataset_checksum"] != b["dataset_checksum"]:
        warnings.append("Dataset trùng id nhưng khác checksum nội dung.")
    if (a["range_start"], a["range_end"]) != (b["range_start"], b["range_end"]):
        warnings.append(
            "Hai lần chạy dùng KHOẢNG THỜI GIAN KHÁC NHAU (%s..%s so với %s..%s)."
            % (a["range_start"], a["range_end"], b["range_start"], b["range_end"])
        )
    if a["algorithm_version"] != b["algorithm_version"]:
        warnings.append(
            "Khác phiên bản thuật toán: %s so với %s."
            % (a["algorithm_version"], b["algorithm_version"])
        )

    ev_a = db.get_events(run_id_a)
    ev_b = db.get_events(run_id_b)
    key = lambda e: (e["structure_type"], e["event_bar_index"], e["confirmed_bar_index"])
    set_a = {key(e) for e in ev_a}
    set_b = {key(e) for e in ev_b}
    only_a = set_a - set_b
    only_b = set_b - set_a
    common = set_a & set_b

    types = sorted(
        set(a["stats"].get("so_su_kien_theo_loai", {}))
        | set(b["stats"].get("so_su_kien_theo_loai", {}))
    )
    by_type = [
        {
            "structure_type": t,
            "a": a["stats"].get("so_su_kien_theo_loai", {}).get(t, 0),
            "b": b["stats"].get("so_su_kien_theo_loai", {}).get(t, 0),
        }
        for t in types
    ]

    return {
        "run_a": a,
        "run_b": b,
        "canh_bao": warnings,
        "so_sanh_theo_loai": by_type,
        "so_su_kien_chung": len(common),
        "chi_co_o_a": len(only_a),
        "chi_co_o_b": len(only_b),
        "mau_chi_co_o_a": [
            {"structure_type": t, "event_bar_index": i, "confirmed_bar_index": c}
            for (t, i, c) in sorted(only_a, key=lambda x: x[1])[:25]
        ],
        "mau_chi_co_o_b": [
            {"structure_type": t, "event_bar_index": i, "confirmed_bar_index": c}
            for (t, i, c) in sorted(only_b, key=lambda x: x[1])[:25]
        ],
        "do_tre_a": a["stats"].get("do_tre_xac_nhan_chung_nen"),
        "do_tre_b": b["stats"].get("do_tre_xac_nhan_chung_nen"),
        "thoi_gian_tinh_toan_ms": {
            "a": a["duration_ms"],
            "b": b["duration_ms"],
        },
        "ghi_chu_vi": (
            "So sánh chỉ dựa trên sự kiện cấu trúc và hiệu năng. Không kết luận "
            "cấu hình nào 'đúng hơn' trừ khi đối chiếu với bộ nhãn tham chiếu "
            "do người gán."
        ),
    }


EXPORT_COLUMNS = [
    "run_id", "symbol", "timeframe", "seq", "event_id", "structure_type",
    "price", "event_bar_index", "event_time", "event_close_time",
    "confirmed_bar_index", "confirmed_at", "confirmation_lag_bars",
    "algorithm", "algorithm_version", "reason_code", "direction",
    "reference_event_id", "details_json",
]


def export_events_csv(run_id: str) -> tuple[str, str]:
    """Trả về (tên file, nội dung CSV) cho bảng sự kiện của một lần chạy."""
    run = db.get_run(run_id)
    if not run:
        raise ServiceError("Không tìm thấy lần chạy %r." % run_id)
    events = db.get_events(run_id)
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(EXPORT_COLUMNS)
    for e in events:
        w.writerow(
            [
                run_id, run["symbol"], run["timeframe"], e["seq"], e["event_id"],
                e["structure_type"], e["price"], e["event_bar_index"], e["event_time"],
                e["event_close_time"], e["confirmed_bar_index"], e["confirmed_at"],
                e["confirmation_lag_bars"], e["algorithm"], e["algorithm_version"],
                e["reason_code"], e["direction"] or "", e["reference_event_id"] or "",
                json.dumps(e["details"], ensure_ascii=False),
            ]
        )
    filename = "su_kien_%s_%s_%s.csv" % (run["symbol"], run["timeframe"], run_id)
    return filename, buf.getvalue()


def c2_cisd_run_metrics(run_id: str, horizon_bars: int = 16) -> dict[str, Any]:
    """Vòng đời setup + MFE/MAE đối chứng C2-only vs C2+CISD cho một run đã lưu.

    MFE/MAE dùng nến SAU thời điểm biết — chỉ phục vụ đánh giá, không đưa ngược
    vào detector. Chạy trên đúng khoảng nến của run (cùng snapshot dataset).
    """
    from core.eval.c2_cisd_metrics import excursion_metrics, lifecycle_metrics

    run = db.get_run(run_id)
    if not run:
        raise ServiceError("Không tìm thấy lần chạy %r." % run_id)
    if run["algorithm"] != "c2_cisd_research":
        raise ServiceError("Chỉ số này chỉ dành cho run c2_cisd_research.")
    if not 1 <= int(horizon_bars) <= 500:
        raise ServiceError("Horizon phải trong 1–500 nến.")
    ds = get_dataset_or_error(run["dataset_id"])
    if ds["checksum_sha256"] != run["dataset_checksum"]:
        raise ServiceError("Dataset đã đổi nội dung so với lúc chạy — không tính MFE/MAE.")
    events = db.get_events(run_id)
    _, bars, _ = load_bars(run["dataset_id"], run["range_start"], run["range_end"])
    return {
        "run_id": run_id,
        "algorithm_version": run["algorithm_version"],
        "dataset_checksum": run["dataset_checksum"],
        "vong_doi": lifecycle_metrics(events),
        "mfe_mae": excursion_metrics(events, bars, int(horizon_bars)),
    }


def run_manifest(run_id: str) -> dict[str, Any]:
    """Hồ sơ đầy đủ của một lần chạy, đủ để chạy lại."""
    run = db.get_run(run_id)
    if not run:
        raise ServiceError("Không tìm thấy lần chạy %r." % run_id)
    ds = db.get_dataset(run["dataset_id"])
    try:
        info = get_algorithm_class(run["algorithm"]).manifest_info(run.get("params") or {})
    except KeyError:
        info = {}
    return {
        "run": run,
        "dataset": ds,
        "algorithm_info": info,
        "ghi_chu_vi": (
            "Chạy lại bằng cùng dataset_checksum, algorithm_version và params "
            "sẽ cho cùng bộ sự kiện."
        ),
    }


def algorithms() -> list[dict[str, Any]]:
    return list_algorithms()
