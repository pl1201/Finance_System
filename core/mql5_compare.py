"""Đối chiếu sự kiện Python với CSV xuất từ MQL5 trên cùng snapshot dữ liệu."""
from __future__ import annotations

import csv
import io
from typing import Any, Optional, Sequence

from core.labels import ReferenceLabel, evaluate_detection


MQL5_NOTE_VI = (
    "Chỉ kết luận lệch implementation khi cùng dataset_checksum, cùng tham số "
    "và cùng quy ước timestamp. Hai feed/broker khác nhau chưa đủ để quy kết lỗi code."
)


def parse_mql5_events_csv(text: str) -> dict[str, Any]:
    """CSV tối thiểu: structure_type, event_bar_index, confirmed_bar_index, price.

    Tuỳ chọn: event_id, dataset_checksum, algorithm_version, confirmed_at.
    """
    sample = text.lstrip("\ufeff")
    reader = csv.DictReader(io.StringIO(sample))
    if not reader.fieldnames:
        raise ValueError("CSV MQL5 không có tiêu đề.")
    fields = {h.strip().lower(): h for h in reader.fieldnames}

    def col(*names: str) -> Optional[str]:
        for n in names:
            if n.lower() in fields:
                return fields[n.lower()]
        return None

    c_type = col("structure_type", "type", "loai")
    c_bar = col("event_bar_index", "bar_index", "shift")
    c_price = col("price", "gia")
    if not c_type or not c_bar or not c_price:
        raise ValueError(
            "CSV MQL5 cần cột structure_type, event_bar_index, price "
            "(tên tiếng Anh như script SwingPivotExport.mq5)."
        )
    c_id = col("event_id")
    c_sum = col("dataset_checksum", "checksum")
    c_ver = col("algorithm_version", "version")
    events = []
    checksum = None
    version = None
    for i, row in enumerate(reader):
        st = (row.get(c_type) or "").strip()
        if not st:
            continue
        bar = int(float(row[c_bar]))
        price = float(row[c_price])
        eid = (row.get(c_id) or "").strip() or ("%s@%s" % (st, bar))
        events.append({
            "event_id": eid,
            "structure_type": st,
            "event_bar_index": bar,
            "price": price,
            "seq": i,
        })
        if c_sum and row.get(c_sum) and checksum is None:
            checksum = row[c_sum].strip()
        if c_ver and row.get(c_ver) and version is None:
            version = row[c_ver].strip()
    return {"events": events, "dataset_checksum": checksum, "algorithm_version": version}


def compare_python_mql5(
    python_events: Sequence[Any],
    mql5_csv_text: str,
    *,
    python_checksum: str,
    python_version: str,
    csv_checksum_override: Optional[str] = None,
    time_tolerance_bars: int = 0,
    price_tolerance: float = 0.0,
) -> dict[str, Any]:
    parsed = parse_mql5_events_csv(mql5_csv_text)
    mql_checksum = csv_checksum_override or parsed["dataset_checksum"]
    warnings = []
    if mql_checksum and python_checksum and mql_checksum != python_checksum:
        warnings.append(
            "DATASET_CHECKSUM KHÁC NHAU — không kết luận lỗi code. "
            "Python=%s, MQL5=%s. Có thể là hai feed/snapshot."
            % (python_checksum, mql_checksum)
        )
    if parsed["algorithm_version"] and parsed["algorithm_version"] != python_version:
        warnings.append(
            "Phiên bản thuật toán khác nhau: Python %s vs MQL5 %s."
            % (python_version, parsed["algorithm_version"])
        )
    labels = [
        ReferenceLabel(
            structure_type=e["structure_type"],
            bar_index=e["event_bar_index"],
            price=e["price"],
            seq=e["seq"],
        )
        for e in parsed["events"]
    ]
    ev = evaluate_detection(
        python_events,
        labels,
        annotator="MQL5 export",
        label_set_id="mql5_csv",
        label_set_version=parsed["algorithm_version"] or "",
        rubric_vi="CSV sự kiện do SwingPivotExport.mq5 ghi",
        time_tolerance_bars=time_tolerance_bars,
        price_tolerance=price_tolerance,
    )
    d = ev.to_dict()
    d["warnings"] = warnings
    d["python_checksum"] = python_checksum
    d["mql5_checksum"] = mql_checksum
    d["python_event_count"] = len(list(python_events))
    d["mql5_event_count"] = len(parsed["events"])
    d["note_vi"] = MQL5_NOTE_VI + " " + (d.get("note_vi") or "")
    d["checksum_khop"] = bool(mql_checksum) and mql_checksum == python_checksum
    return d
