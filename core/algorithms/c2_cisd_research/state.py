"""Trạng thái nội bộ của ``c2_cisd_research``: hằng, mức CISD đang theo dõi, setup C2.

Chuyển thể từ CantoLab Open Source Fractal (MIT, Copyright (c) 2026 cantolab,
commit ``1bb53262deba9456f2b1a85d15c6ac5a5e880cf7``); toàn văn giấy phép ở
``algorithm.py`` và ``third_party/open-source-fractal/LICENSE``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from core.types import Bar

SOURCE_REPO = "https://github.com/cantolab/open-source-fractal"
SOURCE_COMMIT = "1bb53262deba9456f2b1a85d15c6ac5a5e880cf7"

PHASE_C3 = "C3"
PHASE_C4 = "C4"

SUPPORTED_PAIRS = {("M15", "H4")}
SCAN_MAX = 10  # Pine: for i = 2 to 10


def bar_up(b: Bar) -> bool:
    return b.close > b.open


def bar_down(b: Bar) -> bool:
    return b.close < b.open


def bar_doji(b: Bar) -> bool:
    return b.close == b.open


def iso(dt: datetime) -> str:
    return dt.isoformat()


def time_key(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M")


@dataclass
class CisdLevel:
    """Mức CISD đang theo dõi của một hướng (``bullLevelFixed``/``bearLevelFixed``)."""

    price: float
    source_bar: int          # nến cung cấp giá mức (bullIndexFixed)
    set_bar: int             # nến mà tại lúc đóng mức được xác lập
    branch: str
    revision: int
    event_id: str
    reclaimed: bool = False
    reclaim_evidence_bar: Optional[int] = None   # nến có close vượt mức
    reclaim_observed_bar: Optional[int] = None   # nến phát hiện (t)
    early_event_id: Optional[str] = None

    @property
    def level_id(self) -> str:
        return "L%d@%d" % (self.source_bar, self.set_bar)


@dataclass
class Setup:
    setup_id: str
    direction: str            # "up" | "down"
    extreme: float
    extreme_bar: int
    c2_bucket_index: int
    c2_start: datetime
    created_bar: int
    c2_event_id: str
    level: Optional[float]
    level_source_bar: Optional[int]
    level_revision: Optional[int]
    level_event_id: Optional[str]
    phase: str = PHASE_C3
    cisd_confirmed: bool = False
    cisd_confirmed_in_c4: bool = False
    cisd_event_id: Optional[str] = None
    c4_top: Optional[float] = None
    c4_bottom: Optional[float] = None
    c4_start_bar: Optional[int] = None
    c4_invalid: bool = False
    outside_bar: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def is_bull(self) -> bool:
        return self.direction == "up"

    @property
    def c3_bucket_index(self) -> int:
        return self.c2_bucket_index + 1

    @property
    def c4_bucket_index(self) -> int:
        return self.c2_bucket_index + 2
