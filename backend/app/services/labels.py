"""Bộ nhãn tham chiếu: lưu / ghi đè / xuất / đọc CSV, nguồn gốc nhãn."""
from __future__ import annotations

import csv
import io
import uuid
from typing import Any

from backend.app.errors import NotFoundError, ServiceError
from backend.app.services.common import db, get_dataset_or_error
from backend.app.storage import utcnow_iso


def list_label_sets(dataset_id: str | None) -> list[dict[str, Any]]:
    return db.list_label_sets(dataset_id)


def get_label_set_detail(label_set_id: str) -> dict[str, Any]:
    ls = db.get_label_set(label_set_id)
    if not ls:
        raise NotFoundError("Không tìm thấy bộ nhãn %s" % label_set_id)
    ls["used_by_evaluations"] = db.evaluations_using_label_set(label_set_id)
    return ls


def save_label_set(
    *,
    dataset_id: str,
    annotator: str,
    version: str,
    rubric_vi: str,
    labels: list[dict[str, Any]],
) -> dict[str, Any]:
    get_dataset_or_error(dataset_id)
    if not (annotator or "").strip():
        raise ServiceError("Phải ghi tên người gán nhãn.")
    cleaned, warnings = _clean_labels(labels, dataset_id)
    sid = "lab_" + uuid.uuid4().hex[:12]
    db.insert_label_set(
        {
            "id": sid,
            "dataset_id": dataset_id,
            "version": (version or "1").strip(),
            "annotator": annotator.strip(),
            "rubric_vi": rubric_vi or "",
            "created_at": utcnow_iso(),
        },
        cleaned,
    )
    out = db.get_label_set(sid)
    assert out is not None
    out["warnings"] = warnings
    return out


#: Nguồn gốc của một nhãn tham chiếu.
#:
#: * ``human`` — người tự click gán.
#: * ``auto_accepted`` — thuật toán đề xuất, người đã xem và chấp nhận nguyên.
#: * ``auto_edited`` — thuật toán đề xuất, người chấp nhận rồi sửa (dời nến,
#:   đổi loại hoặc sửa giá).
#:
#: Không có nguồn "auto chưa duyệt": đề xuất chưa được người chấp nhận không
#: bao giờ được lưu vào kho nhãn.
LABEL_SOURCES = ("human", "auto_accepted", "auto_edited")


def _clean_labels(
    labels: list[dict[str, Any]], dataset_id: str
) -> tuple[list[dict[str, Any]], list[str]]:
    """Kiểm tra và chuẩn hoá danh sách nhãn theo đúng dataset.

    ``bar_index`` chỉ có nghĩa trong dataset của nó, nên nhãn nằm ngoài phạm vi
    nến của dataset bị từ chối thay vì lưu âm thầm.
    """
    from core.labels import LABEL_TYPES, ReferenceLabel

    ds = get_dataset_or_error(dataset_id)
    n_bars = int(ds["row_count"])
    cleaned: list[dict[str, Any]] = []
    warnings: list[str] = []
    seen: set[tuple[str, int]] = set()

    for i, lb in enumerate(labels):
        st = (lb.get("structure_type") or "").strip()
        if st not in LABEL_TYPES:
            raise ServiceError(
                "Dòng %d: loại nhãn không hỗ trợ %r. Hỗ trợ: %s"
                % (i + 1, st, ", ".join(LABEL_TYPES))
            )
        try:
            bar_index = int(lb["bar_index"])
            price = float(lb["price"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ServiceError(
                "Dòng %d: bar_index/price không hợp lệ (%s)." % (i + 1, exc)
            ) from exc
        if bar_index < 0 or bar_index >= n_bars:
            raise ServiceError(
                "Dòng %d: bar_index %d nằm ngoài dataset %s %s (0..%d). "
                "Nhãn của dataset khác không dùng lại được."
                % (i + 1, bar_index, ds["symbol"], ds["timeframe"], n_bars - 1)
            )
        key = (st, bar_index)
        if key in seen:
            warnings.append(
                "Bỏ nhãn trùng: %s tại nến %d (chỉ giữ bản đầu tiên)." % (st, bar_index)
            )
            continue
        seen.add(key)
        ReferenceLabel(st, bar_index, price)
        source = (lb.get("source") or "human").strip()
        if source not in LABEL_SOURCES:
            raise ServiceError(
                "Dòng %d: nguồn nhãn %r không hợp lệ. Hỗ trợ: %s"
                % (i + 1, source, ", ".join(LABEL_SOURCES))
            )
        source_algorithm = (lb.get("source_algorithm") or "").strip()
        if source != "human" and not source_algorithm:
            raise ServiceError(
                "Dòng %d: nhãn nguồn %r phải ghi thuật toán đã đề xuất nó "
                "(source_algorithm)." % (i + 1, source)
            )
        cleaned.append({
            "structure_type": st,
            "bar_index": bar_index,
            "price": price,
            "notes": (lb.get("notes") or "").strip(),
            "source": source,
            "source_algorithm": source_algorithm if source != "human" else "",
            "source_detail": (lb.get("source_detail") or "").strip() if source != "human" else "",
        })

    cleaned.sort(key=lambda x: (x["bar_index"], x["structure_type"]))
    return cleaned, warnings


def update_label_set(
    *,
    label_set_id: str,
    annotator: str,
    version: str,
    rubric_vi: str,
    labels: list[dict[str, Any]],
    confirm_overwrite: bool = False,
) -> dict[str, Any]:
    """Ghi đè nội dung một bộ nhãn đã lưu (tăng ``revision``).

    Nếu bộ nhãn đã được dùng trong đánh giá đã lưu, phải có
    ``confirm_overwrite=True``: các kết quả cũ gắn với bản nhãn TRƯỚC đó và
    không tự tính lại.
    """
    ls = db.get_label_set(label_set_id)
    if not ls:
        raise ServiceError("Không tìm thấy bộ nhãn %r." % label_set_id)
    if not (annotator or "").strip():
        raise ServiceError("Phải ghi tên người gán nhãn.")

    used_by = db.evaluations_using_label_set(label_set_id)
    if used_by and not confirm_overwrite:
        raise ServiceError(
            "Bộ nhãn %s đã được dùng trong %d đánh giá đã lưu (%s). Ghi đè sẽ "
            "làm các kết quả đó gắn với bản nhãn cũ. Xác nhận ghi đè, hoặc bấm "
            "\"Lưu bộ nhãn\" để tạo bộ mới."
            % (label_set_id, len(used_by), ", ".join(e["id"] for e in used_by[:5]))
        )

    cleaned, warnings = _clean_labels(labels, ls["dataset_id"])
    new_rev = db.update_label_set(
        {
            "id": label_set_id,
            "version": (version or "1").strip(),
            "annotator": annotator.strip(),
            "rubric_vi": rubric_vi or "",
            "updated_at": utcnow_iso(),
        },
        cleaned,
    )
    out = db.get_label_set(label_set_id)
    assert out is not None
    out["warnings"] = warnings
    out["revision"] = new_rev
    out["ghi_chu_vi"] = (
        "Đã ghi đè thành bản %d. %d đánh giá đã lưu trước đó vẫn gắn với bản "
        "nhãn cũ và KHÔNG tự tính lại." % (new_rev, len(used_by))
    )
    return out


#: Cột CSV khi xuất/nhập nhãn tham chiếu.
LABEL_CSV_COLUMNS = [
    "structure_type", "bar_index", "price", "notes",
    "source", "source_algorithm", "source_detail",
]


def export_label_set_csv(label_set_id: str) -> tuple[str, str]:
    """Trả về (tên file, nội dung CSV) của một bộ nhãn.

    Các dòng bắt đầu bằng ``#`` là chú thích ghi nguồn gốc bộ nhãn; bộ nạp bỏ
    qua chúng, nên file xuất ra nạp lại được nguyên vẹn.
    """
    ls = db.get_label_set(label_set_id)
    if not ls:
        raise ServiceError("Không tìm thấy bộ nhãn %r." % label_set_id)
    ds = db.get_dataset(ls["dataset_id"])

    buf = io.StringIO()
    buf.write("# Bộ nhãn tham chiếu — Market Structure Lab\n")
    buf.write("# label_set_id=%s revision=%s version=%s\n"
              % (ls["id"], ls.get("revision") or 1, ls["version"]))
    buf.write("# annotator=%s\n" % (ls["annotator"],))
    buf.write("# dataset_id=%s symbol=%s timeframe=%s\n"
              % (ls["dataset_id"], (ds or {}).get("symbol", "?"), (ds or {}).get("timeframe", "?")))
    buf.write("# dataset_checksum=%s\n" % ((ds or {}).get("checksum_sha256", "?"),))
    buf.write("# rubric=%s\n" % ((ls.get("rubric_vi") or "").replace("\n", " ") or "(khong ghi)",))
    buf.write("# bar_index chi co nghia trong dung dataset tren.\n")

    w = csv.writer(buf, lineterminator="\n")
    w.writerow(LABEL_CSV_COLUMNS)
    for lb in ls.get("labels") or []:
        w.writerow([
            lb["structure_type"], lb["bar_index"], lb["price"], lb.get("notes") or "",
            lb.get("source") or "human", lb.get("source_algorithm") or "",
            lb.get("source_detail") or "",
        ])

    filename = "nhan_%s_%s_%s.csv" % (
        (ds or {}).get("symbol", "ds"), (ds or {}).get("timeframe", ""), ls["id"]
    )
    return filename, buf.getvalue()


def parse_label_csv(*, dataset_id: str, csv_text: str) -> dict[str, Any]:
    """Đọc CSV nhãn thành danh sách nháp đã kiểm tra — KHÔNG tự lưu.

    Người dùng vẫn phải bấm Lưu, nên chỉ có một đường ghi vào kho nhãn.
    """
    ds = get_dataset_or_error(dataset_id)
    text = (csv_text or "").lstrip("﻿")
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]
    if not lines:
        raise ServiceError("File không có dòng nhãn nào (ngoài chú thích).")

    warnings: list[str] = []
    header_meta = _label_csv_meta(text)
    if header_meta.get("dataset_checksum") and header_meta["dataset_checksum"] != ds["checksum_sha256"]:
        warnings.append(
            "File ghi dataset_checksum=%s nhưng dataset đang chọn có checksum %s. "
            "bar_index có thể trỏ sai nến."
            % (header_meta["dataset_checksum"][:12] + "…", ds["checksum_sha256"][:12] + "…")
        )

    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    if not reader.fieldnames:
        raise ServiceError("Không đọc được dòng tiêu đề của file CSV.")
    have = {(h or "").strip().lower() for h in reader.fieldnames}
    missing = [c for c in ("structure_type", "bar_index", "price") if c not in have]
    if missing:
        raise ServiceError(
            "CSV thiếu cột bắt buộc: %s. Cột bắt buộc: structure_type, bar_index, "
            "price (tuỳ chọn: %s)"
            % (", ".join(missing), ", ".join(LABEL_CSV_COLUMNS[3:]))
        )

    raw: list[dict[str, Any]] = []
    for row in reader:
        norm = {(k or "").strip().lower(): (v or "") for k, v in row.items()}
        raw.append({
            "structure_type": norm.get("structure_type", ""),
            "bar_index": norm.get("bar_index", ""),
            "price": norm.get("price", ""),
            "notes": norm.get("notes", ""),
            # File cũ không có cột nguồn -> coi là người gán.
            "source": norm.get("source", "") or "human",
            "source_algorithm": norm.get("source_algorithm", ""),
            "source_detail": norm.get("source_detail", ""),
        })

    cleaned, dup_warnings = _clean_labels(raw, dataset_id)
    warnings.extend(dup_warnings)
    return {
        "labels": cleaned,
        "warnings": warnings,
        "meta_trong_file": header_meta,
        "dataset": {"id": ds["id"], "symbol": ds["symbol"], "timeframe": ds["timeframe"]},
        "ghi_chu_vi": (
            "Đã đọc %d nhãn vào bộ nháp. Kiểm tra rồi bấm Lưu — công cụ không "
            "tự ghi vào kho nhãn." % len(cleaned)
        ),
    }


def _label_csv_meta(text: str) -> dict[str, str]:
    """Đọc các dòng chú thích ``# key=value`` ở đầu file xuất."""
    meta: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("#"):
            if s:
                break
            continue
        for part in s.lstrip("#").strip().split(" "):
            if "=" in part:
                k, v = part.split("=", 1)
                if k and v:
                    meta[k.strip()] = v.strip()
    return meta


def label_provenance(labels: list[dict[str, Any]]) -> dict[str, Any]:
    """Đếm nhãn theo nguồn gốc: người gán / auto chấp nhận nguyên / auto người đã sửa."""
    human = 0
    by_algo: dict[str, int] = {}
    edited_by_algo: dict[str, int] = {}
    for lb in labels:
        src = lb.get("source") or "human"
        if src == "human":
            human += 1
            continue
        a = lb.get("source_algorithm") or "?"
        bucket = edited_by_algo if src == "auto_edited" else by_algo
        bucket[a] = bucket.get(a, 0) + 1
    return {
        "tong": len(labels),
        "nguoi_gan": human,
        "auto_da_duyet": sum(by_algo.values()),
        "auto_da_sua": sum(edited_by_algo.values()),
        "auto_theo_thuat_toan": by_algo,
        "auto_sua_theo_thuat_toan": edited_by_algo,
    }


def provenance_warnings(
    labels: list[dict[str, Any]], run_algorithms: list[str]
) -> list[str]:
    """Cảnh báo khi chấm một thuật toán trên nhãn do chính nó đề xuất.

    Nhãn tham chiếu phải độc lập với thuật toán được chấm (tài liệu nhóm, mục
    5.8). Nhãn auto đã duyệt vẫn mang dấu của thuật toán đề xuất: người duyệt
    có xu hướng chấp nhận cái được gợi ý, nên F1 sẽ cao hơn thực tế.
    """
    prov = label_provenance(labels)
    out: list[str] = []
    total = prov["tong"] or 0
    for algo_name in sorted(set(run_algorithms)):
        n = prov["auto_theo_thuat_toan"].get(algo_name, 0)
        e = prov["auto_sua_theo_thuat_toan"].get(algo_name, 0)
        if n:
            out.append(
                "%d/%d nhãn trong bộ này do chính %s đề xuất rồi người duyệt chấp "
                "nhận. Chấm %s trên bộ nhãn này bị thiên lệch (nhãn không độc lập "
                "với thuật toán) — precision/recall/F1 sẽ cao hơn thực tế. Dùng bộ "
                "nhãn người tự gán, hoặc bộ auto từ thuật toán KHÁC, để so sánh "
                "công bằng." % (n, total, algo_name, algo_name)
            )
        if e:
            out.append(
                "%d/%d nhãn xuất phát từ đề xuất của %s rồi được người sửa (dời nến, "
                "đổi loại hoặc giá). Ít phụ thuộc hơn nhãn chấp nhận nguyên nhưng vẫn "
                "neo theo gợi ý của thuật toán — kết quả có thể thiên lệch nhẹ."
                % (e, total, algo_name)
            )
    return out
