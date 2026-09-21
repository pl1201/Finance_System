"""Nạp OHLC từ CSV: nhận diện cột, ánh xạ thủ công, chuẩn hoá thời gian.

Hỗ trợ:

* CSV chuẩn: ``time,open,high,low,close,volume`` (dấu phẩy).
* Định dạng xuất từ MT5 (History Center / "Export bars"):
  ``<DATE>\\t<TIME>\\t<OPEN>\\t<HIGH>\\t<LOW>\\t<CLOSE>\\t<TICKVOL>\\t<VOL>\\t<SPREAD>``
  ngăn cách bằng TAB, ngày dạng ``2024.01.02``.
* Định dạng MT4-style không header: ``2024.01.02,10:00,1.1,1.2,1.0,1.15,123``.

Nguyên tắc:

* KHÔNG tự đoán múi giờ. ``source_timezone`` phải do người dùng khai báo.
* KHÔNG tự đoán timestamp là mở hay đóng nến. ``timestamp_convention``
  phải do người dùng khai báo.
* KHÔNG lấp dữ liệu thiếu bằng dữ liệu tương lai. Bản nạp này chỉ phát
  hiện và báo cáo, không nội suy.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

CANONICAL_FIELDS = ("time", "open", "high", "low", "close", "volume")

#: Từ đồng nghĩa cho từng cột chuẩn (đã hạ chữ thường, bỏ ký tự đặc biệt).
_ALIASES: dict[str, tuple[str, ...]] = {
    "time": (
        "time", "date", "datetime", "timestamp", "date_time", "bar_time",
        "opentime", "open_time", "gmt_time", "local_time", "dt",
    ),
    "date_part": ("date", "day"),
    "time_part": ("time", "hour", "clock"),
    "open": ("open", "o", "openprice", "first"),
    "high": ("high", "h", "highprice", "max"),
    "low": ("low", "l", "lowprice", "min"),
    "close": ("close", "c", "closeprice", "last", "adjclose", "adj_close"),
    "volume": (
        "volume", "vol", "v", "tickvol", "tick_volume", "tickvolume",
        "realvolume", "real_volume",
    ),
}

_TIME_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y.%m.%d %H:%M:%S",
    "%Y.%m.%d %H:%M",
    "%Y/%m/%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d",
    "%Y.%m.%d",
    "%Y/%m/%d",
)


class CsvImportError(ValueError):
    """Lỗi không thể nạp file CSV."""


@dataclass
class ColumnPreview:
    """Kết quả dò cấu trúc file, dùng cho bước ánh xạ cột trên giao diện."""

    delimiter: str
    has_header: bool
    headers: list[str]
    sample_rows: list[list[str]]
    suggested_mapping: dict[str, Optional[str]]
    needs_manual_mapping: bool
    note_vi: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "delimiter": self.delimiter,
            "has_header": self.has_header,
            "headers": self.headers,
            "sample_rows": self.sample_rows,
            "suggested_mapping": self.suggested_mapping,
            "needs_manual_mapping": self.needs_manual_mapping,
            "note_vi": self.note_vi,
        }


@dataclass
class LoadResult:
    rows: list[dict[str, Any]]
    mapping_used: dict[str, Optional[str]]
    delimiter: str
    has_header: bool
    skipped_rows: list[dict[str, Any]] = field(default_factory=list)
    checksum_sha256: str = ""


# ---------------------------------------------------------------------------
# Dò cấu trúc
# ---------------------------------------------------------------------------


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").strip().lower())


def _sniff_delimiter(text: str) -> str:
    head = "\n".join(text.splitlines()[:20])
    counts = {d: head.count(d) for d in ("\t", ";", ",", "|")}
    best = max(counts, key=lambda d: counts[d])
    return best if counts[best] > 0 else ","


def _looks_numeric(s: str) -> bool:
    try:
        float(s.replace(",", "."))
        return True
    except (TypeError, ValueError):
        return False


def preview_csv(text: str) -> ColumnPreview:
    """Dò delimiter, header và đề xuất ánh xạ cột."""
    text = text.lstrip("﻿")
    if not text.strip():
        raise CsvImportError("File rỗng.")
    delimiter = _sniff_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        raise CsvImportError("Không đọc được dòng dữ liệu nào.")

    first = rows[0]
    # Có header nếu dòng đầu có ít nhất 2 ô KHÔNG phải số VÀ KHÔNG phải mốc
    # thời gian. Chỉ đếm "không phải số" là không đủ: dòng dữ liệu kiểu MT4
    # ("2024.01.02,00:00,...") cũng có hai ô đầu không phải số.
    def _is_data_cell(c: str) -> bool:
        c = (c or "").strip()
        if not c:
            return True
        if _looks_numeric(c):
            return True
        try:
            parse_timestamp(c)
            return True
        except CsvImportError:
            return False

    header_like = sum(1 for c in first if not _is_data_cell(c))
    has_header = header_like >= 2

    if has_header:
        headers = [h.strip().strip("<>") for h in first]
        data_rows = rows[1:]
    else:
        headers = ["col%d" % i for i in range(len(first))]
        data_rows = rows

    mapping = _suggest_mapping(headers, data_rows, has_header)
    missing = [
        f for f in ("time", "open", "high", "low", "close") if not mapping.get(f)
    ]
    note = ""
    if missing:
        note = (
            "Chưa nhận diện được cột: %s. Hãy ánh xạ thủ công trước khi nạp."
            % ", ".join(missing)
        )
    elif mapping.get("date_part") and mapping.get("time_part"):
        note = "Phát hiện ngày và giờ nằm ở hai cột riêng; sẽ ghép lại khi nạp."
    return ColumnPreview(
        delimiter=delimiter,
        has_header=has_header,
        headers=headers,
        sample_rows=[list(r) for r in data_rows[:8]],
        suggested_mapping=mapping,
        needs_manual_mapping=bool(missing),
        note_vi=note,
    )


def _suggest_mapping(
    headers: list[str], data_rows: list[list[str]], has_header: bool
) -> dict[str, Optional[str]]:
    mapping: dict[str, Optional[str]] = {f: None for f in CANONICAL_FIELDS}
    mapping["date_part"] = None
    mapping["time_part"] = None
    norm_headers = [_norm(h) for h in headers]

    if has_header:
        used: set[int] = set()
        # Ngày + giờ tách cột (đặc trưng MT5 export).
        if "date" in norm_headers and "time" in norm_headers:
            di, ti = norm_headers.index("date"), norm_headers.index("time")
            mapping["date_part"] = headers[di]
            mapping["time_part"] = headers[ti]
            mapping["time"] = headers[di]
            used.update({di, ti})
        for field_name in ("time", "open", "high", "low", "close", "volume"):
            if mapping.get(field_name):
                continue
            for idx, nh in enumerate(norm_headers):
                if idx in used:
                    continue
                if nh in _ALIASES[field_name]:
                    mapping[field_name] = headers[idx]
                    used.add(idx)
                    break
        return mapping

    # Không header: đoán theo vị trí và hình dạng dữ liệu.
    sample = data_rows[0] if data_rows else []
    n = len(sample)
    if n >= 6 and not _looks_numeric(sample[0]) and not _looks_numeric(sample[1]):
        # date, time, o, h, l, c[, v]
        mapping["date_part"] = headers[0]
        mapping["time_part"] = headers[1]
        mapping["time"] = headers[0]
        for k, f in enumerate(("open", "high", "low", "close")):
            mapping[f] = headers[2 + k]
        if n >= 7:
            mapping["volume"] = headers[6]
    elif n >= 5:
        mapping["time"] = headers[0]
        for k, f in enumerate(("open", "high", "low", "close")):
            mapping[f] = headers[1 + k]
        if n >= 6:
            mapping["volume"] = headers[5]
    return mapping


# ---------------------------------------------------------------------------
# Phân tích thời gian
# ---------------------------------------------------------------------------


def parse_timestamp(value: str) -> datetime:
    """Phân tích chuỗi thời gian (naive, chưa gắn múi giờ)."""
    s = (value or "").strip().replace("T", " ")
    if not s:
        raise CsvImportError("Ô thời gian rỗng.")
    # Epoch giây/mili giây.
    if re.fullmatch(r"\d{9,13}", s):
        num = int(s)
        if num > 10**11:
            num //= 1000
        return datetime.fromtimestamp(num, tz=timezone.utc).replace(tzinfo=None)
    for fmt in _TIME_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None)
    except ValueError as exc:
        raise CsvImportError("Không phân tích được thời gian: %r" % value) from exc


def _tz_offset(source_timezone: str) -> timedelta:
    """Chuyển khai báo múi giờ dạng UTC/UTC+2/UTC-05:00 thành offset.

    Chỉ chấp nhận offset cố định. Múi giờ có DST (ví dụ ``Europe/London``)
    không được đoán ngầm — người dùng phải quy đổi trước hoặc khai báo offset
    tương ứng với dữ liệu, và điều này được ghi lại trong hồ sơ dataset.
    """
    s = (source_timezone or "UTC").strip().upper().replace(" ", "")
    if s in ("UTC", "GMT", "UTC+0", "UTC+00", "UTC+00:00", "Z"):
        return timedelta(0)
    m = re.fullmatch(r"(?:UTC|GMT)?([+-])(\d{1,2})(?::?(\d{2}))?", s)
    if not m:
        raise CsvImportError(
            "Múi giờ nguồn %r không hợp lệ. Dùng dạng UTC, UTC+2, UTC-05:00."
            % source_timezone
        )
    sign = 1 if m.group(1) == "+" else -1
    hours = int(m.group(2))
    minutes = int(m.group(3) or 0)
    if hours > 14 or minutes >= 60:
        raise CsvImportError("Offset múi giờ ngoài phạm vi: %r" % source_timezone)
    return sign * timedelta(hours=hours, minutes=minutes)


def normalize_timezone_label(source_timezone: str) -> str:
    off = _tz_offset(source_timezone)
    total = int(off.total_seconds() // 60)
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    return "UTC%s%02d:%02d" % (sign, total // 60, total % 60)


# ---------------------------------------------------------------------------
# Nạp
# ---------------------------------------------------------------------------


def _to_float(value: str, column: str, line_no: int) -> float:
    s = (value or "").strip().replace(" ", "")
    if not s:
        raise CsvImportError("Dòng %d: cột %s rỗng." % (line_no, column))
    s = s.replace(",", ".") if s.count(",") == 1 and "." not in s else s.replace(",", "")
    try:
        return float(s)
    except ValueError as exc:
        raise CsvImportError(
            "Dòng %d: cột %s không phải số: %r" % (line_no, column, value)
        ) from exc


def load_csv(
    text: str,
    *,
    source_timezone: str,
    mapping: dict[str, Optional[str]] | None = None,
    delimiter: Optional[str] = None,
    has_header: Optional[bool] = None,
) -> LoadResult:
    """Nạp CSV thành danh sách dict đã chuẩn hoá (``bar_time`` là UTC tz-aware).

    Tham số ``mapping`` dùng tên cột (hoặc ``col0``, ``col1``... nếu không có
    header). Nếu bỏ trống sẽ dùng kết quả dò tự động.
    """
    text = text.lstrip("﻿")
    checksum = hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()
    preview = preview_csv(text)
    delim = delimiter or preview.delimiter
    header_flag = preview.has_header if has_header is None else has_header
    used_mapping = dict(preview.suggested_mapping)
    if mapping:
        used_mapping.update({k: v for k, v in mapping.items() if v})

    required = ("time", "open", "high", "low", "close")
    missing = [f for f in required if not used_mapping.get(f)]
    if missing:
        raise CsvImportError(
            "Thiếu ánh xạ cột bắt buộc: %s. Hãy chọn cột tương ứng."
            % ", ".join(missing)
        )

    reader = csv.reader(io.StringIO(text), delimiter=delim)
    all_rows = [r for r in reader if any(c.strip() for c in r)]
    if header_flag:
        headers = [h.strip().strip("<>") for h in all_rows[0]]
        data_rows = all_rows[1:]
        first_line_no = 2
    else:
        headers = ["col%d" % i for i in range(len(all_rows[0]))]
        data_rows = all_rows
        first_line_no = 1

    index_of = {h: i for i, h in enumerate(headers)}

    def col(row: list[str], name: Optional[str]) -> str:
        if not name:
            return ""
        i = index_of.get(name)
        if i is None or i >= len(row):
            return ""
        return row[i]

    offset = _tz_offset(source_timezone)
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for k, raw in enumerate(data_rows):
        line_no = first_line_no + k
        try:
            if used_mapping.get("date_part") and used_mapping.get("time_part"):
                stamp = "%s %s" % (
                    col(raw, used_mapping["date_part"]).strip(),
                    col(raw, used_mapping["time_part"]).strip(),
                )
            else:
                stamp = col(raw, used_mapping["time"])
            naive = parse_timestamp(stamp)
            bar_time = (naive - offset).replace(tzinfo=timezone.utc)
            row = {
                "bar_time": bar_time,
                "open": _to_float(col(raw, used_mapping["open"]), "open", line_no),
                "high": _to_float(col(raw, used_mapping["high"]), "high", line_no),
                "low": _to_float(col(raw, used_mapping["low"]), "low", line_no),
                "close": _to_float(col(raw, used_mapping["close"]), "close", line_no),
                "volume": 0.0,
                "source_line": line_no,
            }
            vol_col = used_mapping.get("volume")
            if vol_col:
                vtxt = col(raw, vol_col).strip()
                if vtxt:
                    try:
                        row["volume"] = _to_float(vtxt, "volume", line_no)
                    except CsvImportError:
                        row["volume"] = 0.0
            rows.append(row)
        except CsvImportError as exc:
            skipped.append({"line": line_no, "raw": delim.join(raw), "error": str(exc)})

    if not rows:
        raise CsvImportError(
            "Không nạp được dòng hợp lệ nào. Lỗi đầu tiên: %s"
            % (skipped[0]["error"] if skipped else "không rõ")
        )

    return LoadResult(
        rows=rows,
        mapping_used=used_mapping,
        delimiter=delim,
        has_header=header_flag,
        skipped_rows=skipped[:100],
        checksum_sha256=checksum,
    )


def rows_checksum(rows: Iterable[dict[str, Any]]) -> str:
    """Checksum trên nội dung nến đã chuẩn hoá (không phụ thuộc định dạng file)."""
    h = hashlib.sha256()
    for r in rows:
        h.update(
            ("%s|%.10g|%.10g|%.10g|%.10g|%.10g\n"
             % (
                 r["bar_time"].astimezone(timezone.utc).isoformat(),
                 r["open"], r["high"], r["low"], r["close"], r.get("volume") or 0.0,
             )).encode("ascii")
        )
    return h.hexdigest()
