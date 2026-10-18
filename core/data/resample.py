"""Tổng hợp nến từ timeframe nhỏ lên timeframe lớn.

Chỉ gộp nến **đã đóng**. Không nội suy, không lấp khoảng trống bằng nến
tương lai hay close trước đó.

**Mốc nến (`alignment = utc_epoch`).** Thời điểm mở nến đích là bội số Unix
epoch của độ dài timeframe đích (UTC):

* M5  → :00, :05, :10, …
* M15 → :00, :15, :30, :45
* M30 → :00, :30
* H1  → :00 mỗi giờ
* H4  → 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC

Một số broker đặt H4 lệch (ví dụ 02:00). Lab **không** đoán lệch đó; nếu
feed của bạn khác, hãy tổng hợp từ MT5 theo đúng mốc broker rồi nhập CSV.

**Mốc `ny_1700`** (plan_ict_structure §11.3, D10): ngày giao dịch mở 17:00 New
York; H4 = 6 nến từ 17:00 NY (17, 21, 01, 05, 09, 13 giờ NY, có đổi giờ mùa
hè) — cùng mốc với bộ gộp tuần tự ``core/data/htf_stream.py`` mà ``ict_structure``
dùng. Khung ≤ H1 trùng ``utc_epoch``. Có thể đưa ``calendar`` (lịch phiên khai
báo) để số nến kỳ vọng mỗi bucket theo lịch (nến H4 đầu ngày chỉ có 3 giờ giao
dịch); không có lịch → số nến danh nghĩa.

**Giả định `bar_time` nguồn là mốc MỞ nến.** Người gọi phải bảo đảm điều
này (cùng quy ước với dataset nguồn).

**Khoảng không giao dịch.** Bucket không có nến nguồn bị bỏ qua — không đúc
nến giả. Bucket có nến nhưng thiếu so với số nến nguồn kỳ vọng
(`target_seconds / source_seconds`):

* `drop_incomplete` (mặc định): không phát nến đích, ghi vào báo cáo.
* `emit_available`: phát nến từ các nến nguồn có mặt, gắn `incomplete=True`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from core.data.htf_stream import bucket_bounds, open_slots
from core.types import TIMEFRAME_SECONDS, timeframe_delta

RESAMPLE_TARGETS = ("M5", "M15", "M30", "H1", "H4")
ALIGNMENTS = ("utc_epoch", "ny_1700")
GAP_POLICIES = ("drop_incomplete", "emit_available")


class ResampleError(ValueError):
    """Lỗi tổng hợp nến."""


@dataclass
class ResampleReport:
    source_timeframe: str
    target_timeframe: str
    alignment: str
    gap_policy: str
    source_bars: int
    target_bars: int
    buckets_empty: int
    buckets_incomplete_dropped: int
    buckets_incomplete_emitted: int
    expected_source_per_bucket: int
    note_vi: str
    incomplete_samples: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_timeframe": self.source_timeframe,
            "target_timeframe": self.target_timeframe,
            "alignment": self.alignment,
            "gap_policy": self.gap_policy,
            "source_bars": self.source_bars,
            "target_bars": self.target_bars,
            "buckets_empty": self.buckets_empty,
            "buckets_incomplete_dropped": self.buckets_incomplete_dropped,
            "buckets_incomplete_emitted": self.buckets_incomplete_emitted,
            "expected_source_per_bucket": self.expected_source_per_bucket,
            "note_vi": self.note_vi,
            "incomplete_samples": self.incomplete_samples[:20],
        }


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def bucket_start_utc(bar_time: datetime, target_tf: str) -> datetime:
    """Mốc mở nến đích theo utc_epoch."""
    dt = _as_utc(bar_time)
    sec = TIMEFRAME_SECONDS[target_tf]
    epoch = int(dt.timestamp())
    aligned = epoch - (epoch % sec)
    return datetime.fromtimestamp(aligned, tz=timezone.utc)


def resample_ohlc(
    rows: list[dict[str, Any]],
    source_timeframe: str,
    target_timeframe: str,
    *,
    alignment: str = "utc_epoch",
    gap_policy: str = "drop_incomplete",
    calendar: Any = None,
) -> tuple[list[dict[str, Any]], ResampleReport]:
    """Gộp ``rows`` (đã sắp theo thời gian) lên ``target_timeframe``.

    ``calendar`` (``SessionCalendar``, tuỳ chọn, chỉ với ``ny_1700``): số nến nguồn kỳ vọng mỗi bucket
    = số ô mở theo lịch thay vì số ô danh nghĩa.
    """
    src = (source_timeframe or "").upper().strip()
    dst = (target_timeframe or "").upper().strip()
    if src not in TIMEFRAME_SECONDS:
        raise ResampleError("Timeframe nguồn không hỗ trợ: %r" % source_timeframe)
    if dst not in RESAMPLE_TARGETS:
        raise ResampleError(
            "Timeframe đích phải thuộc %s, nhận %r" % (list(RESAMPLE_TARGETS), target_timeframe)
        )
    if TIMEFRAME_SECONDS[dst] <= TIMEFRAME_SECONDS[src]:
        raise ResampleError(
            "Không tách được nến %s thành %s — tổng hợp chỉ gộp lên khung lớn hơn "
            "(ví dụ M5→H1, H1→H4). Để xem %s, hãy chọn dataset cùng symbol đã có "
            "ở khung đó, hoặc nhập CSV/MT5 khung nhỏ rồi tổng hợp lên."
            % (src, dst, dst)
        )
    if alignment not in ALIGNMENTS:
        raise ResampleError("alignment phải thuộc %s." % (list(ALIGNMENTS),))
    if calendar is not None and alignment != "ny_1700":
        raise ResampleError("calendar chỉ dùng với alignment ny_1700.")
    if gap_policy not in GAP_POLICIES:
        raise ResampleError("gap_policy phải là drop_incomplete hoặc emit_available.")

    expected = TIMEFRAME_SECONDS[dst] // TIMEFRAME_SECONDS[src]
    buckets: dict[datetime, list[dict[str, Any]]] = {}
    order: list[datetime] = []
    ends: dict[datetime, datetime] = {}
    for r in rows:
        if alignment == "utc_epoch":
            key = bucket_start_utc(r["bar_time"], dst)
        else:
            key, end = bucket_bounds(_as_utc(r["bar_time"]), dst, alignment)
            ends[key] = end
        if key not in buckets:
            buckets[key] = []
            order.append(key)
        buckets[key].append(r)

    out: list[dict[str, Any]] = []
    empty = 0
    dropped = 0
    emitted_inc = 0
    samples: list[dict[str, Any]] = []
    src_delta = timeframe_delta(src)
    opens = [s.open for s in calendar.sessions] if calendar is not None else None

    for key in order:
        group = sorted(buckets[key], key=lambda x: _as_utc(x["bar_time"]))
        n = len(group)
        if alignment != "utc_epoch":
            # ny_1700: kỳ vọng theo lịch (nếu có) hoặc số ô danh nghĩa của bucket (nến H4/D có thể dài 23–25 giờ)
            expected = open_slots(calendar, opens, key, ends[key], src_delta)[0]
        incomplete = n < expected
        if n == 0:
            empty += 1
            continue
        if incomplete and gap_policy == "drop_incomplete":
            dropped += 1
            if len(samples) < 20:
                samples.append({
                    "bucket_start": key.isoformat(),
                    "source_bars": n,
                    "expected": expected,
                    "xu_ly": "bo_qua",
                })
            continue
        if incomplete:
            emitted_inc += 1
            if len(samples) < 20:
                samples.append({
                    "bucket_start": key.isoformat(),
                    "source_bars": n,
                    "expected": expected,
                    "xu_ly": "phat_tu_nen_co_mat",
                })
        agg = {
            "bar_time": key,
            "open": float(group[0]["open"]),
            "high": max(float(x["high"]) for x in group),
            "low": min(float(x["low"]) for x in group),
            "close": float(group[-1]["close"]),
            "volume": float(sum(float(x.get("volume") or 0.0) for x in group)),
            "incomplete": incomplete,
            "source_bar_count": n,
            "source_first": _as_utc(group[0]["bar_time"]).isoformat(),
            "source_last": _as_utc(group[-1]["bar_time"]).isoformat(),
            "source_last_close_time": (
                _as_utc(group[-1]["bar_time"]) + src_delta
            ).isoformat(),
        }
        out.append(agg)

    if alignment != "utc_epoch":
        expected = TIMEFRAME_SECONDS[dst] // TIMEFRAME_SECONDS[src]
    note = (
        ("Mốc nến: utc_epoch (bội số Unix UTC của timeframe đích). " if alignment == "utc_epoch" else
         "Mốc nến: ny_1700 (ngày giao dịch mở 17:00 New York; số nến kỳ vọng %s). "
         % ("theo lịch phiên %s" % getattr(calendar, "name", "") if calendar is not None else "danh nghĩa")) +
        "Khoảng không giao dịch: bucket trống bị bỏ qua, không nội suy. "
        "Nến nguồn được giả định có bar_time = mốc MỞ. "
        "Policy %s: bucket thiếu nến nguồn so với %d nến kỳ vọng %s."
        % (
            gap_policy,
            expected,
            "bị bỏ" if gap_policy == "drop_incomplete" else "vẫn phát từ nến có mặt",
        )
    )
    report = ResampleReport(
        source_timeframe=src,
        target_timeframe=dst,
        alignment=alignment,
        gap_policy=gap_policy,
        source_bars=len(rows),
        target_bars=len(out),
        buckets_empty=empty,
        buckets_incomplete_dropped=dropped,
        buckets_incomplete_emitted=emitted_inc,
        expected_source_per_bucket=expected,
        note_vi=note,
        incomplete_samples=samples,
    )
    return out, report
