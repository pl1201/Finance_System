"""Engine chạy thuật toán trên chuỗi nến và tính thống kê lần chạy.

Engine chỉ nạp nến theo thứ tự thời gian tăng dần vào ``algorithm.on_bar``.
Không có đường nào để thuật toán nhìn thấy nến phía sau.
"""
from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Optional, Sequence

from core.algorithms.base import StructureAlgorithm
from core.types import (
    DATA_STATUS_OK,
    DATA_STATUS_WARMUP,
    Bar,
    StructureEvent,
)


@dataclass
class RunResult:
    events: list[StructureEvent]
    bars_processed: int
    warmup_bars: int
    duration_ms: float
    data_status: str
    data_status_message_vi: str
    stats: dict[str, Any] = field(default_factory=dict)
    timeline: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events],
            "bars_processed": self.bars_processed,
            "warmup_bars": self.warmup_bars,
            "duration_ms": round(self.duration_ms, 3),
            "data_status": self.data_status,
            "data_status_message_vi": self.data_status_message_vi,
            "stats": self.stats,
            "timeline": self.timeline,
        }


def compute_stats(
    events: Sequence[StructureEvent], bars_processed: int, duration_ms: float
) -> dict[str, Any]:
    """Thống kê mô tả cho một lần chạy.

    Chỉ gồm các đại lượng đếm được trực tiếp từ sự kiện: số sự kiện theo
    loại, độ trễ xác nhận và thời gian tính toán. KHÔNG nhúng accuracy,
    win-rate hay P&L vào thống kê lần chạy — precision/recall chỉ có khi
    đối chiếu với bộ nhãn do người gán; chưa có simulator giao dịch.
    """
    by_type: dict[str, int] = {}
    lag_by_type: dict[str, list[int]] = {}
    for e in events:
        by_type[e.structure_type] = by_type.get(e.structure_type, 0) + 1
        lag_by_type.setdefault(e.structure_type, []).append(e.confirmation_lag_bars)

    lag_summary: dict[str, dict[str, float]] = {}
    for stype, lags in lag_by_type.items():
        lag_summary[stype] = {
            "min": min(lags),
            "trung_binh": round(statistics.fmean(lags), 3),
            "trung_vi": float(statistics.median(lags)),
            "max": max(lags),
        }

    all_lags = [e.confirmation_lag_bars for e in events]
    return {
        "tong_su_kien": len(events),
        "so_su_kien_theo_loai": by_type,
        "do_tre_xac_nhan_theo_loai_nen": lag_summary,
        "do_tre_xac_nhan_chung_nen": (
            {
                "min": min(all_lags),
                "trung_binh": round(statistics.fmean(all_lags), 3),
                "trung_vi": float(statistics.median(all_lags)),
                "max": max(all_lags),
            }
            if all_lags
            else None
        ),
        "so_nen_xu_ly": bars_processed,
        "thoi_gian_tinh_toan_ms": round(duration_ms, 3),
        "toc_do_nen_tren_giay": (
            round(bars_processed / (duration_ms / 1000.0), 1) if duration_ms > 0 else None
        ),
        "ghi_chu_vi": (
            "Thống kê chỉ gồm số đếm sự kiện, độ trễ xác nhận và hiệu năng. "
            "Precision/recall chỉ có ở tab Nhãn tham chiếu khi đã có bộ nhãn "
            "do người gán. Thống kê lần chạy không báo cáo accuracy, "
            "win rate hay P&L."
        ),
    }


def run_algorithm(
    bars: Sequence[Bar],
    algorithm: StructureAlgorithm,
    *,
    upto_index: Optional[int] = None,
) -> RunResult:
    """Chạy thuật toán trên ``bars[0 : upto_index+1]``.

    ``upto_index`` là chỉ số nến CUỐI CÙNG được nạp (0-based). ``None``
    nghĩa là chạy toàn bộ. Đây chính là cơ chế replay: thuật toán chỉ nhận
    prefix dữ liệu, không nhận nến phía sau.
    """
    algorithm.reset()
    last = len(bars) - 1 if upto_index is None else min(upto_index, len(bars) - 1)
    warmup = algorithm.warmup_bars()

    t0 = time.perf_counter()
    events: list[StructureEvent] = []
    timeline: list[dict[str, Any]] = []
    processed = 0
    for i in range(last + 1):
        events.extend(algorithm.on_bar(bars[i]))
        point = algorithm.timeline_point(bars[i])
        if point is not None:
            point = dict(point)
            point["bar_index"] = bars[i].index
            point["time"] = int(bars[i].bar_time.timestamp())
            timeline.append(point)
        processed += 1
    duration_ms = (time.perf_counter() - t0) * 1000.0

    if processed < warmup:
        status = DATA_STATUS_WARMUP
        msg = (
            "Chưa đủ warm-up: thuật toán cần ít nhất %d nến, hiện có %d. "
            "Chưa thể xác nhận cấu trúc nào." % (warmup, processed)
        )
    else:
        status = DATA_STATUS_OK
        msg = "Đã xử lý %d nến (warm-up %d nến)." % (processed, warmup)

    stats = compute_stats(events, processed, duration_ms)
    extra = algorithm.run_stats(events)
    if extra:
        stats["chi_so_thuat_toan"] = extra

    return RunResult(
        events=events,
        bars_processed=processed,
        warmup_bars=warmup,
        duration_ms=duration_ms,
        data_status=status,
        data_status_message_vi=msg,
        stats=stats,
        timeline=timeline,
    )


class ReplaySession:
    """Trạng thái replay theo từng nến cho một cấu hình cụ thể.

    * ``step_forward`` nạp thêm đúng một nến vào thuật toán.
    * ``step_back`` và ``seek`` lùi lại bằng cách RESET thuật toán và chạy
      lại từ nến đầu tiên đến vị trí mới. Cách này bảo đảm trạng thái nội
      bộ được tái dựng đúng, không phụ thuộc vào việc "hoàn tác" thủ công.
    * Sự kiện đã xác nhận không bao giờ bị sửa bởi nến nạp thêm sau đó:
      danh sách chỉ được nối thêm khi tiến, và được dựng lại từ đầu khi lùi.
    """

    def __init__(
        self,
        bars: Sequence[Bar],
        algorithm: StructureAlgorithm,
    ) -> None:
        self._bars = bars
        self._algo = algorithm
        self._algo.reset()
        self._cursor = -1  # chỉ số nến cuối cùng đã nạp
        self._events: list[StructureEvent] = []
        self._timeline: list[dict[str, Any]] = []

    # -- thuộc tính -----------------------------------------------------

    @property
    def cursor(self) -> int:
        return self._cursor

    @property
    def total_bars(self) -> int:
        return len(self._bars)

    @property
    def events(self) -> list[StructureEvent]:
        return list(self._events)

    # -- điều khiển -----------------------------------------------------

    def reset(self) -> None:
        self._algo.reset()
        self._cursor = -1
        self._events = []
        self._timeline = []

    def step_forward(self, n: int = 1) -> list[StructureEvent]:
        """Tiến ``n`` nến. Trả về các sự kiện MỚI được xác nhận."""
        new_events: list[StructureEvent] = []
        for _ in range(max(0, n)):
            if self._cursor + 1 >= len(self._bars):
                break
            self._cursor += 1
            bar = self._bars[self._cursor]
            emitted = self._algo.on_bar(bar)
            new_events.extend(emitted)
            self._events.extend(emitted)
            point = self._algo.timeline_point(bar)
            if point is not None:
                point = dict(point)
                point["bar_index"] = bar.index
                point["time"] = int(bar.bar_time.timestamp())
                self._timeline.append(point)
        return new_events

    def step_until_event(self, max_bars: int = 5000) -> list[StructureEvent]:
        """Tiến từng nến cho tới khi có ít nhất một sự kiện mới (hoặc hết dữ liệu).

        Vẫn nạp đúng một nến mỗi bước — không nhìn trước nến sau để quyết định.
        """
        for _ in range(max(0, max_bars)):
            if self._cursor + 1 >= len(self._bars):
                break
            new = self.step_forward(1)
            if new:
                return new
        return []

    def seek(self, index: int) -> None:
        """Nhảy tới vị trí nến ``index`` (``-1`` = chưa nạp nến nào)."""
        target = max(-1, min(index, len(self._bars) - 1))
        if target >= self._cursor:
            self.step_forward(target - self._cursor)
            return
        # Lùi: tái dựng trạng thái từ đầu.
        self.reset()
        if target >= 0:
            self.step_forward(target + 1)

    def step_back(self, n: int = 1) -> None:
        self.seek(self._cursor - max(0, n))

    # -- kết xuất -------------------------------------------------------

    def snapshot(self, since: Optional[int] = None) -> dict[str, Any]:
        """Trạng thái tại con trỏ.

        ``since`` (tuỳ chọn): client đã có sự kiện/timeline tới nến ``since``.
        Khi đó chỉ trả phần có ``confirmed_bar_index`` / ``bar_index`` > ``s`` với
        ``s = min(since, cursor)`` và ghi ``delta_since = s``. An toàn nhờ tính
        nhân quả: phần tới ``s`` không bao giờ đổi khi nạp thêm nến; khi lùi,
        client cắt bỏ phần sau ``s``. ``pending_state`` luôn là của con trỏ hiện tại.
        """
        warmup = self._algo.warmup_bars()
        processed = self._cursor + 1
        if processed == 0:
            status, msg = DATA_STATUS_WARMUP, "Chưa nạp nến nào. Nhấn Tiến để bắt đầu."
        elif processed < warmup:
            status = DATA_STATUS_WARMUP
            msg = (
                "Chưa đủ warm-up: cần %d nến, đã nạp %d. Chưa thể xác nhận cấu trúc."
                % (warmup, processed)
            )
        else:
            status, msg = DATA_STATUS_OK, "Đã nạp %d/%d nến." % (processed, len(self._bars))
        s = None if since is None else min(int(since), self._cursor)
        return {
            "cursor": self._cursor,
            "total_bars": len(self._bars),
            "bars_loaded": processed,
            "warmup_bars": warmup,
            "data_status": status,
            "data_status_message_vi": msg,
            "events": [e.to_dict() for e in self._events if s is None or e.confirmed_bar_index > s],
            "timeline": (
                self._timeline if s is None else [p for p in self._timeline if p["bar_index"] > s]
            ),
            "delta_since": s,
            "pending_state": self._algo.pending_state(),
            "current_bar_time": (
                self._bars[self._cursor].bar_time.isoformat() if processed else None
            ),
            "current_bar_close_time": (
                self._bars[self._cursor].close_time.isoformat() if processed else None
            ),
        }
