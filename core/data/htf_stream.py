"""Gộp nến khung lớn (HTF) TUẦN TỰ từ nến khung nhỏ (LTF) đã đóng.

Khác ``core/data/resample.py`` (gộp cả chuỗi một lần để tạo dataset mới), module
này nhận từng nến LTF đã đóng và cho biết, tại đúng nến đó:

* nến HTF đang chạy (chưa hoàn tất) có OHLC bao nhiêu tính tới giờ;
* nến HTF vừa HOÀN TẤT (đủ số nến LTF kỳ vọng, liên tiếp, đúng mốc);
* bucket nào bị thiếu dữ liệu — và thời điểm phát hiện ra điều đó.

Không bao giờ đọc OHLC cuối của một bucket trước khi nến LTF cuối cùng của nó
đóng. Không tự bù nến thiếu.

Mốc bucket (``alignment = utc_epoch``): mở nến HTF là bội số Unix epoch của độ
dài HTF tính theo UTC — cùng quy ước với ``resample.py``. KHÔNG tuyên bố khớp
mốc H4 của broker hay TradingView khi chưa đối chiếu.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Optional

ALIGNMENT_UTC_EPOCH = "utc_epoch"


@dataclass(frozen=True)
class HtfBucket:
    """Ảnh chụp BẤT BIẾN của một nến HTF tại một thời điểm."""

    index: int                 # số thứ tự bucket = open_ts // htf_seconds
    start: datetime            # mở bucket (UTC)
    end: datetime              # đóng bucket (UTC)
    expected_bars: int
    open: float
    high: float
    low: float
    close: float
    high_bar_index: int        # nến LTF ĐẦU TIÊN đạt high (so strict như Pine)
    low_bar_index: int
    first_bar_index: int
    last_bar_index: int
    n_bars: int
    contiguous: bool           # chưa từng thiếu nến LTF nào (kể cả thiếu nến đầu)

    @property
    def complete(self) -> bool:
        return self.contiguous and self.n_bars == self.expected_bars

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2.0


@dataclass
class PushResult:
    """Những gì aggregator biết được SAU KHI nhận một nến LTF."""

    current: HtfBucket                        # bucket chứa nến vừa nhận
    started_new_bucket: bool = False
    previous: Optional[HtfBucket] = None      # bucket vừa bị bỏ lại (nếu đổi bucket)
    previous_adjacent: bool = False           # bucket mới liền kề bucket trước?
    completed_now: bool = False               # nến vừa nhận là nến cuối, bucket đủ
    newly_incomplete: list = field(default_factory=list)   # bucket vừa bị phát hiện thiếu


class HtfAggregator:
    """Theo dõi bucket HTF hiện tại từ luồng nến LTF đã đóng."""

    def __init__(self, ltf_seconds: int, htf_seconds: int) -> None:
        if htf_seconds % ltf_seconds != 0:
            raise ValueError("HTF phải là bội số của LTF.")
        self.ltf = timedelta(seconds=ltf_seconds)
        self.ltf_seconds = ltf_seconds
        self.htf_seconds = htf_seconds
        self.expected = htf_seconds // ltf_seconds
        self.reset()

    def reset(self) -> None:
        self._cur: Optional[HtfBucket] = None
        self._last_open: Optional[datetime] = None
        self._reported_incomplete: set[int] = set()

    def _bucket_start(self, open_time: datetime) -> tuple[int, datetime]:
        ts = int(open_time.timestamp())
        idx = ts // self.htf_seconds
        return idx, datetime.fromtimestamp(idx * self.htf_seconds, tz=timezone.utc)

    def push(
        self, bar_index: int, open_time: datetime, o: float, h: float, l: float, c: float
    ) -> PushResult:
        idx, start = self._bucket_start(open_time)
        prev = self._cur
        newly_incomplete: list[HtfBucket] = []

        if prev is not None and idx < prev.index:
            raise ValueError("Nến LTF đi lùi thời gian.")

        if prev is None or idx != prev.index:
            # --- mở bucket mới ---
            if prev is not None and not prev.complete and prev.index not in self._reported_incomplete:
                # Bucket cũ kết thúc mà chưa đủ nến (thiếu nến cuối).
                newly_incomplete.append(prev)
                self._reported_incomplete.add(prev.index)
            cur = HtfBucket(
                index=idx, start=start, end=start + timedelta(seconds=self.htf_seconds),
                expected_bars=self.expected,
                open=o, high=h, low=l, close=c,
                high_bar_index=bar_index, low_bar_index=bar_index,
                first_bar_index=bar_index, last_bar_index=bar_index,
                n_bars=1,
                contiguous=(open_time == start),   # thiếu nến đầu -> hỏng ngay
            )
            res = PushResult(
                current=cur, started_new_bucket=True, previous=prev,
                previous_adjacent=(prev is not None and idx == prev.index + 1),
            )
        else:
            # --- cùng bucket ---
            contiguous = prev.contiguous and self._last_open is not None and (
                open_time == self._last_open + self.ltf
            )
            cur = replace(
                prev,
                high=h if h > prev.high else prev.high,          # strict: giữ nến đầu tiên
                high_bar_index=bar_index if h > prev.high else prev.high_bar_index,
                low=l if l < prev.low else prev.low,
                low_bar_index=bar_index if l < prev.low else prev.low_bar_index,
                close=c,
                last_bar_index=bar_index,
                n_bars=prev.n_bars + 1,
                contiguous=contiguous,
            )
            res = PushResult(current=cur)

        if not cur.contiguous and cur.index not in self._reported_incomplete:
            newly_incomplete.append(cur)
            self._reported_incomplete.add(cur.index)

        close_time = open_time + self.ltf
        res.completed_now = cur.complete and close_time == cur.end
        res.newly_incomplete = newly_incomplete
        self._cur = cur
        self._last_open = open_time
        return res
