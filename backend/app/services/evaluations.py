"""Đánh giá: ghép nhãn (tab cũ), protocol trang Đánh giá, đánh giá đã lưu, báo cáo."""
from __future__ import annotations

import json
import uuid
from typing import Any, Optional

from backend.app.errors import NotFoundError, ServiceError
from backend.app.services.common import db, get_dataset_or_error, load_bars
from backend.app.services.labels import label_provenance, provenance_warnings
from backend.app.storage import utcnow_iso


def list_evaluations(dataset_id: Optional[str], limit: int) -> list[dict[str, Any]]:
    return db.list_evaluations(dataset_id, limit)


def get_evaluation(eval_id: str) -> dict[str, Any]:
    row = db.get_evaluation(eval_id)
    if not row:
        raise NotFoundError("Không tìm thấy đánh giá %s" % eval_id)
    return row


def delete_evaluation(eval_id: str) -> dict[str, Any]:
    get_evaluation(eval_id)
    db.delete_evaluation(eval_id)
    return {"deleted": eval_id}


def evaluate_run_against_labels(
    run_id: str,
    label_set_id: str,
    time_tolerance_bars: int = 1,
    price_tolerance: float = 0.0,
) -> dict[str, Any]:
    from core.labels import ReferenceLabel, evaluate_detection
    run = db.get_run(run_id)
    if not run:
        raise ServiceError("Không tìm thấy lần chạy %r." % run_id)
    ls = db.get_label_set(label_set_id)
    if not ls:
        raise ServiceError("Không tìm thấy bộ nhãn %r." % label_set_id)
    if ls["dataset_id"] != run["dataset_id"]:
        raise ServiceError("Bộ nhãn và lần chạy không cùng dataset.")
    # Nhãn đếm nến từ đầu dataset; sự kiện đếm từ nến đầu của run → đưa về cùng không gian.
    offset = int(run.get("range_start_index") or 0)
    events = []
    for e in db.get_events(run_id):
        e = dict(e)
        if offset:
            e["event_bar_index"] = int(e["event_bar_index"]) + offset
            if e.get("confirmed_bar_index") is not None:
                e["confirmed_bar_index"] = int(e["confirmed_bar_index"]) + offset
        events.append(e)
    labels = [
        ReferenceLabel(
            structure_type=x["structure_type"],
            bar_index=x["bar_index"],
            price=x["price"],
            notes=x.get("notes") or "",
            seq=x["seq"],
        )
        for x in ls["labels"]
    ]
    try:
        ev = evaluate_detection(
            events,
            labels,
            annotator=ls["annotator"],
            label_set_id=ls["id"],
            label_set_version=ls["version"],
            rubric_vi=ls["rubric_vi"],
            time_tolerance_bars=time_tolerance_bars,
            price_tolerance=price_tolerance,
        )
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc
    out = ev.to_dict()
    out["nguon_nhan"] = label_provenance(ls["labels"])
    out["canh_bao_nguon_nhan"] = provenance_warnings(ls["labels"], [run["algorithm"]])
    if out["canh_bao_nguon_nhan"]:
        out["note_vi"] = ((out.get("note_vi") or "") + " CẢNH BÁO: " +
                          " ".join(out["canh_bao_nguon_nhan"])).strip()
    return out


def eval_meta() -> dict[str, Any]:
    from core.eval.protocol import (
        MATCHER_VERSIONS,
        PROTOCOL_VERSION,
        describe_targets,
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "matcher_versions": list(MATCHER_VERSIONS),
        "targets": describe_targets(),
        "atr_source": "wilder_confirm_bar",
        "note_vi": (
            "Precision/recall/F1 chỉ khi có bộ nhãn do người gán trong khoảng chấm. "
            "Không có đồng hồ chất lượng hay nhãn «thuật toán tốt nhất»."
        ),
    }


def evaluate_algorithm_runs(
    *,
    run_ids: list[str],
    protocol_raw: dict[str, Any] | None,
    label_set_id: Optional[str] = None,
    baseline_run_id: Optional[str] = None,
    save: bool = True,
    note_vi: str = "",
) -> dict[str, Any]:
    from core.eval.evaluate import evaluate_runs
    from core.eval.protocol import EvalProtocol
    from core.labels import ReferenceLabel

    if not run_ids:
        raise ServiceError("Chọn ít nhất một lần chạy để đánh giá.")
    try:
        protocol = EvalProtocol.from_dict(protocol_raw)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc

    runs: list[dict[str, Any]] = []
    bars_by_run: dict[str, list] = {}
    dataset_meta = None
    for rid in run_ids:
        run = db.get_run(rid)
        if not run:
            raise ServiceError("Không tìm thấy lần chạy %r." % rid)
        run = dict(run)
        run["events"] = db.get_events(rid)
        _, bars, _ = load_bars(run["dataset_id"], run.get("range_start"), run.get("range_end"))
        bars_by_run[rid] = bars
        if dataset_meta is None:
            dataset_meta = get_dataset_or_error(run["dataset_id"])
        runs.append(run)

    labels: list[ReferenceLabel] = []
    label_set_meta = None
    annotator = ""
    extra_note = note_vi.strip()
    if label_set_id:
        ls = db.get_label_set(label_set_id)
        if not ls:
            raise ServiceError("Không tìm thấy bộ nhãn %r." % label_set_id)
        annotator = (ls.get("annotator") or "").strip()
        if not annotator:
            raise ServiceError("Bộ nhãn thiếu tên người gán — không tính precision ẩn danh.")
        label_set_meta = {
            "id": ls["id"],
            "version": ls["version"],
            "annotator": annotator,
            "rubric_vi": ls.get("rubric_vi") or "",
            "dataset_id": ls["dataset_id"],
            "n_labels": len(ls.get("labels") or []),
            # Bộ nhãn có thể bị ghi đè về sau; ghi lại bản đã dùng để kết quả
            # này vẫn giải thích được.
            "revision": ls.get("revision") or 1,
            "nguon_nhan": label_provenance(ls.get("labels") or []),
        }
        kept = []
        skipped = []
        for run in runs:
            if run["dataset_id"] != ls["dataset_id"]:
                skipped.append(run["run_id"])
            else:
                kept.append(run)
        runs = kept
        if skipped:
            extra_note = (
                (extra_note + " " if extra_note else "")
                + "Bỏ run khác dataset với bộ nhãn: %s." % ", ".join(skipped)
            )
        if not runs:
            raise ServiceError("Không còn lần chạy nào cùng dataset với bộ nhãn.")
        labels = [
            ReferenceLabel(
                structure_type=x["structure_type"],
                bar_index=x["bar_index"],
                price=x["price"],
                notes=x.get("notes") or "",
                seq=x["seq"],
            )
            for x in ls["labels"]
        ]
        dataset_meta = get_dataset_or_error(ls["dataset_id"])

    if baseline_run_id and baseline_run_id not in [r["run_id"] for r in runs]:
        baseline_run_id = None

    try:
        result = evaluate_runs(
            runs,
            protocol=protocol,
            labels=labels,
            bars_by_run=bars_by_run,
            dataset_meta={
                "id": dataset_meta["id"],
                "name": dataset_meta["name"],
                "symbol": dataset_meta["symbol"],
                "timeframe": dataset_meta["timeframe"],
                "is_synthetic": dataset_meta["is_synthetic"],
                "row_count": dataset_meta["row_count"],
            } if dataset_meta else {},
            label_set_meta=label_set_meta,
            baseline_run_id=baseline_run_id,
            annotator=annotator,
        )
    except ValueError as exc:   # vd chuẩn ngẫu nhiên vượt giới hạn khối lượng
        raise ServiceError(str(exc)) from exc
    if protocol.test_unlocked:
        # Đứng đầu ghi chú → hiện ngay trong danh sách đánh giá đã lưu.
        extra_note = "[ĐÃ MỞ ĐOẠN KIỂM TRA]" + ((" " + extra_note) if extra_note else "")
    prov_warn: list[str] = []
    if label_set_id and label_set_meta:
        prov_warn = provenance_warnings(
            db.get_label_set(label_set_id)["labels"],  # type: ignore[index]
            [r["algorithm"] for r in runs],
        )
    result["nguon_nhan"] = (label_set_meta or {}).get("nguon_nhan")
    result["canh_bao_nguon_nhan"] = prov_warn
    if prov_warn:
        extra_note = ((extra_note + " ") if extra_note else "") + "CẢNH BÁO: " + " ".join(prov_warn)
    if extra_note:
        result["note_vi"] = ((result.get("note_vi") or "") + " " + extra_note).strip()

    eval_id = "ev_" + uuid.uuid4().hex[:12]
    result["evaluation_id"] = eval_id
    result["saved"] = bool(save)
    if save:
        created = utcnow_iso()
        db.insert_evaluation(
            {
                "id": eval_id,
                "created_at": created,
                "dataset_id": (dataset_meta or {}).get("id") or runs[0]["dataset_id"],
                "label_set_id": label_set_id,
                "label_set_revision": (label_set_meta or {}).get("revision"),
                "protocol_json": json.dumps(protocol.to_dict(), ensure_ascii=False),
                "protocol_hash": protocol.fingerprint(),
                "baseline_run_id": baseline_run_id,
                "run_ids_json": json.dumps([r["run_id"] for r in runs], ensure_ascii=False),
                "result_json": json.dumps(result, ensure_ascii=False),
                "duration_ms": result["duration_ms"],
                "note_vi": result.get("note_vi") or "",
            }
        )
        result["created_at"] = created
    return result


def get_evaluation_or_error(eval_id: str) -> dict[str, Any]:
    row = db.get_evaluation(eval_id)
    if not row:
        raise ServiceError("Không tìm thấy đánh giá %r." % eval_id)
    return row


def _fmt3(x: Any, d: int = 3) -> str:
    if x is None:
        return "—"
    if isinstance(x, float):
        return ("%." + str(d) + "f") % x
    return str(x)


def _report_extras(lines: list[str], result: dict[str, Any]) -> None:
    """Chuẩn ngẫu nhiên và số theo đoạn — chỉ khi lần đánh giá có bật."""
    runs = [r for g in result.get("groups") or [] if g.get("comparable") for r in g.get("runs") or []]
    nulls = [(r, r["null_baseline"]) for r in runs if r.get("null_baseline")]
    if nulls:
        first = nulls[0][1]
        lines.extend([
            "",
            "## Chuẩn ngẫu nhiên (%s, %s lượt, seed %s)" % (first.get("mode_vi"), first.get("n"), first.get("seed")),
            "",
            "| Run | F1 thực tế | F1 ngẫu nhiên TB [P5 – P95] | Lượt ≥ thực tế | Ghi chú |",
            "|---|---:|---|---:|---|",
        ])
        for r, nb in nulls:
            if nb.get("status") != "ok":
                lines.append("| `%s` | — | — | — | %s |" % (r["run_id"], nb.get("note_vi") or nb.get("status")))
                continue
            f = nb.get("f1") or {}
            lines.append("| `%s` | %s | %s [%s – %s] | %s/%s | p ≈ %s |" % (
                r["run_id"], _fmt3((nb.get("real") or {}).get("f1")), _fmt3(f.get("mean")), _fmt3(f.get("p5")),
                _fmt3(f.get("p95")), nb.get("n_ge_real"), nb.get("n"), _fmt3(nb.get("p_ge"), 4)))
    segged = [r for r in runs if r.get("by_segment")]
    if segged:
        lines.extend(["", "## Theo đoạn", ""])
        for r in segged:
            lines.append("**`%s`** — %s" % (r["run_id"], r.get("segments_note_vi") or ""))
            lines.extend(["", "| Đoạn | Vai | Từ | Đến | Trạng thái | F1 | P | R | Trễ P90 | /100 nến |",
                          "|---|---|---|---|---|---:|---:|---:|---:|---:|"])
            for sg in r["by_segment"]:
                q = sg.get("quality") or {}
                lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    sg.get("name"), sg.get("role"), sg.get("start"), sg.get("end"), sg.get("status"),
                    _fmt3(q.get("f1")), _fmt3(q.get("precision")), _fmt3(q.get("recall")),
                    _fmt3((sg.get("lag") or {}).get("p90"), 1), _fmt3(sg.get("density_per_100"), 2)))
            lines.append("")


def evaluation_report_markdown(eval_id: str) -> tuple[str, str]:
    row = get_evaluation_or_error(eval_id)
    result = row["result"]
    proto = result.get("protocol") or row.get("protocol") or {}
    lines = [
        "# Báo cáo đánh giá thuật toán",
        "",
        "- Mã: `%s`" % row["id"],
        "- Lúc: %s" % row["created_at"],
        "- Protocol: %s · matcher `%s` · hash `%s`"
        % (proto.get("version"), proto.get("matcher_version"), row["protocol_hash"]),
        "- Mục tiêu: %s" % (result.get("target_label_vi") or proto.get("target")),
        "- Dataset: %s" % ((result.get("dataset") or {}).get("name") or row["dataset_id"]),
        "- Bộ nhãn: %s" % (row.get("label_set_id") or "không có"),
        "- Baseline: `%s`" % (row.get("baseline_run_id") or "—"),
        "",
        result.get("note_vi") or "",
        "",
        "## Các lần chạy",
        "",
        "| Run | Thuật toán | F1 | Precision | Recall | Trễ P90 | Median trễ | /100 nến | Nhân quả |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for g in result.get("groups") or []:
        if not g.get("comparable"):
            for ex in g.get("excluded") or []:
                lines.append(
                    "| `%s` | — | — | — | — | — | — | — | %s |"
                    % (ex.get("run_id"), ex.get("reason_vi"))
                )
            continue
        for r in g.get("runs") or []:
            q, lag, den, val = r["quality"], r["lag"], r["density"], r["validity"]

            def fmt(x: Any, d: int = 3) -> str:
                if x is None:
                    return "—"
                if isinstance(x, float):
                    return ("%." + str(d) + "f") % x
                return str(x)

            mark = " baseline" if r.get("is_baseline") else ""
            lines.append(
                "| `%s`%s | %s v%s | %s | %s | %s | %s | %s | %s | %s |"
                % (
                    r["run_id"], mark,
                    r.get("algorithm"), r.get("algorithm_version"),
                    fmt(q.get("f1")), fmt(q.get("precision")), fmt(q.get("recall")),
                    fmt(lag.get("p90"), 1), fmt(lag.get("median"), 1),
                    fmt(den.get("per_100"), 2),
                    val.get("status_label_vi") or val.get("status"),
                )
            )
    _report_extras(lines, result)
    lines.extend(["", "Không phải win-rate, P&L hay xếp hạng thuật toán tốt nhất.", ""])
    filename = "evaluation_%s.md" % row["id"]
    return filename, "\n".join(lines)
