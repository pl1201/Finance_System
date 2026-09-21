"""Kiểm tra chất lượng dữ liệu OHLC.

Kiểm tra và BÁO CÁO, không tự sửa. Nguyên tắc:

* Bản ghi trùng timestamp: giữ bản ghi ĐẦU TIÊN, cách ly các bản sau.
* Bản ghi sai thứ tự: sắp xếp lại theo thời gian và ghi lại số lần.
* OHLC không hợp lệ (``low <= open/close <= high`` sai): cách ly bản ghi.
* Nến thiếu: đếm và liệt kê khoảng trống, KHÔNG nội suy và KHÔNG lấp bằng
  dữ liệu tương lai. Cuối tuần / giờ nghỉ được tách riêng khỏi "khoảng
  trống trong phiên" bằng heuristic có công bố (xem ``GAP_WEEKEND_NOTE``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from core.types import timeframe_delta

GAP_WEEKEND_NOTE = (
    "Mỗi vị trí nến thiếu được xếp loại riêng: 'cuối tuần/nghỉ' nếu rơi vào "
    "cửa sổ từ 21:00 thứ Sáu UTC đến 22:00 Chủ nhật UTC, ngược lại là 'thiếu "
    "trong phiên'. Đây là heuristic cho lịch forex/vàng thông dụng, KHÔNG phải "
    "lịch phiên chính thức của broker — hãy đối chiếu với lịch phiên thật của "
    "nguồn dữ liệu trước khi kết luận dataset bị thiếu."
)


@dataclass
class QualityIssue:
    code: str
    severity: str  # "error" | "warning" | "info"
    message_vi: str
    count: int = 1
    samples: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message_vi": self.message_vi,
            "count": self.count,
            "samples": self.samples[:10],
        }


@dataclass
class QualityReport:
    rows_in: int
    rows_out: int
    issues: list[QualityIssue]
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    expected_bars: Optional[int] = None
    missing_in_session: int = 0
    missing_weekend: int = 0

    @property
    def has_error(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows_in": self.rows_in,
            "rows_out": self.rows_out,
            "issues": [i.to_dict() for i in self.issues],
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "expected_bars": self.expected_bars,
            "missing_in_session": self.missing_in_session,
            "missing_weekend": self.missing_weekend,
            "has_error": self.has_error,
            "gap_note_vi": GAP_WEEKEND_NOTE,
        }


#: Số vị trí nến tối đa được phân loại từng cái một trong một khoảng trống.
_MAX_GAP_SLOTS = 200_000


def _in_weekend_break(t: datetime) -> bool:
    """Mốc thời gian có nằm trong cửa sổ nghỉ cuối tuần giả định không."""
    u = t.astimezone(timezone.utc)
    wd, hour = u.weekday(), u.hour  # Thứ Hai = 0
    return (
        (wd == 4 and hour >= 21)    # Thứ Sáu từ 21:00
        or wd == 5                  # Thứ Bảy
        or (wd == 6 and hour < 22)  # Chủ nhật trước 22:00
    )


def _classify_gap(
    first_missing: datetime, next_bar: datetime, delta: timedelta
) -> tuple[int, int]:
    """Đếm số vị trí nến thiếu, tách thành (trong phiên, nghỉ cuối tuần).

    Phân loại TỪNG vị trí nến, không phải cả khoảng: một khoảng trống dài
    có thể vừa trùm cuối tuần vừa thiếu vài nến trong phiên.
    """
    total = int((next_bar - first_missing) / delta)
    if total <= 0:
        return 0, 0
    if total > _MAX_GAP_SLOTS:
        # Khoảng trống quá lớn (vd dataset ghép từ hai giai đoạn rời nhau):
        # không duyệt từng nến, tính hết vào "trong phiên" để không che giấu.
        return total, 0
    in_session = 0
    weekend = 0
    cursor = first_missing
    for _ in range(total):
        if _in_weekend_break(cursor):
            weekend += 1
        else:
            in_session += 1
        cursor += delta
    return in_session, weekend


def validate_and_clean(
    rows: list[dict[str, Any]], timeframe: str
) -> tuple[list[dict[str, Any]], QualityReport]:
    """Kiểm tra, sắp xếp và cách ly bản ghi lỗi. Trả về (rows_sạch, báo cáo)."""
    issues: list[QualityIssue] = []
    rows_in = len(rows)
    if not rows:
        return [], QualityReport(0, 0, [
            QualityIssue("EMPTY", "error", "Không có bản ghi nào.")
        ], None, None)

    delta = timeframe_delta(timeframe)

    # 1. Thứ tự thời gian.
    out_of_order = sum(
        1 for a, b in zip(rows, rows[1:]) if b["bar_time"] < a["bar_time"]
    )
    ordered = sorted(rows, key=lambda r: r["bar_time"])
    if out_of_order:
        issues.append(
            QualityIssue(
                "OUT_OF_ORDER",
                "warning",
                "Có %d bản ghi sai thứ tự thời gian; đã sắp xếp lại theo timestamp."
                % out_of_order,
                count=out_of_order,
            )
        )

    # 2. Trùng timestamp — giữ bản đầu tiên.
    dedup: list[dict[str, Any]] = []
    dup_samples: list[str] = []
    seen: set[datetime] = set()
    for r in ordered:
        t = r["bar_time"]
        if t in seen:
            dup_samples.append(t.isoformat())
            continue
        seen.add(t)
        dedup.append(r)
    if dup_samples:
        issues.append(
            QualityIssue(
                "DUPLICATE_TIMESTAMP",
                "warning",
                "Có %d bản ghi trùng timestamp; giữ bản ghi đầu tiên, bỏ các bản sau."
                % len(dup_samples),
                count=len(dup_samples),
                samples=dup_samples[:10],
            )
        )

    # 3. Tính hợp lệ OHLC và giá trị thiếu/không hợp lý.
    clean: list[dict[str, Any]] = []
    invalid_samples: list[dict[str, Any]] = []
    nonpositive_samples: list[dict[str, Any]] = []
    for r in dedup:
        o, h, l, c = r["open"], r["high"], r["low"], r["close"]
        if any(v != v for v in (o, h, l, c)):  # NaN
            invalid_samples.append({"time": r["bar_time"].isoformat(), "ly_do": "giá trị thiếu"})
            continue
        if min(o, h, l, c) <= 0:
            nonpositive_samples.append(
                {"time": r["bar_time"].isoformat(), "ly_do": "giá <= 0"}
            )
            continue
        if not (l <= o <= h and l <= c <= h and l <= h):
            invalid_samples.append(
                {
                    "time": r["bar_time"].isoformat(),
                    "ly_do": "vi phạm low <= open/close <= high",
                    "ohlc": [o, h, l, c],
                }
            )
            continue
        clean.append(r)

    if invalid_samples:
        issues.append(
            QualityIssue(
                "INVALID_OHLC",
                "error",
                "Có %d nến vi phạm quan hệ OHLC hoặc thiếu giá trị; đã cách ly, "
                "không đưa vào thuật toán." % len(invalid_samples),
                count=len(invalid_samples),
                samples=invalid_samples[:10],
            )
        )
    if nonpositive_samples:
        issues.append(
            QualityIssue(
                "NON_POSITIVE_PRICE",
                "error",
                "Có %d nến có giá <= 0; đã cách ly." % len(nonpositive_samples),
                count=len(nonpositive_samples),
                samples=nonpositive_samples[:10],
            )
        )

    # 4. Nến thiếu.
    missing_session = 0
    missing_weekend = 0
    gap_samples: list[dict[str, Any]] = []
    for a, b in zip(clean, clean[1:]):
        gap = b["bar_time"] - a["bar_time"]
        if gap <= delta:
            continue
        in_session, weekend = _classify_gap(a["bar_time"] + delta, b["bar_time"], delta)
        missing_weekend += weekend
        missing_session += in_session
        if in_session and len(gap_samples) < 10:
            gap_samples.append(
                {
                    "tu": a["bar_time"].isoformat(),
                    "den": b["bar_time"].isoformat(),
                    "so_nen_thieu_trong_phien": in_session,
                    "so_nen_thieu_cuoi_tuan": weekend,
                }
            )

    if missing_session:
        issues.append(
            QualityIssue(
                "MISSING_BARS_IN_SESSION",
                "warning",
                "Thiếu khoảng %d nến ngoài cửa sổ nghỉ cuối tuần. KHÔNG nội suy "
                "và KHÔNG lấp bằng dữ liệu tương lai; thuật toán chạy trên các "
                "nến thực có." % missing_session,
                count=missing_session,
                samples=gap_samples,
            )
        )
    if missing_weekend:
        issues.append(
            QualityIssue(
                "MISSING_BARS_WEEKEND",
                "info",
                "Có khoảng %d vị trí nến trống rơi vào cửa sổ nghỉ cuối tuần "
                "(bình thường với forex/vàng)." % missing_weekend,
                count=missing_weekend,
            )
        )

    if not clean:
        issues.append(
            QualityIssue(
                "NO_VALID_ROWS",
                "error",
                "Không còn bản ghi hợp lệ nào sau khi kiểm tra.",
            )
        )
        return [], QualityReport(rows_in, 0, issues, None, None)

    start, end = clean[0]["bar_time"], clean[-1]["bar_time"]
    expected = int((end - start) / delta) + 1
    return clean, QualityReport(
        rows_in=rows_in,
        rows_out=len(clean),
        issues=issues,
        start_time=start,
        end_time=end,
        expected_bars=expected,
        missing_in_session=missing_session,
        missing_weekend=missing_weekend,
    )


def infer_timeframe(rows: list[dict[str, Any]]) -> Optional[str]:
    """Đoán timeframe từ khoảng cách phổ biến nhất giữa các nến (chỉ để gợi ý)."""
    from collections import Counter

    from core.types import TIMEFRAME_SECONDS

    if len(rows) < 3:
        return None
    ordered = sorted(rows, key=lambda r: r["bar_time"])
    deltas = Counter(
        int((b["bar_time"] - a["bar_time"]).total_seconds())
        for a, b in zip(ordered, ordered[1:])
    )
    if not deltas:
        return None
    most_common = deltas.most_common(1)[0][0]
    for name, sec in TIMEFRAME_SECONDS.items():
        if sec == most_common:
            return name
    return None
