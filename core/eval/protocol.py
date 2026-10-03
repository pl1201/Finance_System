"""Protocol đánh giá nhận diện — phiên bản được lưu cùng kết quả.

Thay đổi quy tắc chấm phải tăng ``PROTOCOL_VERSION`` hoặc ``matcher_version``
để không trộn kết quả cũ/mới.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from core.eval.targets import (  # noqa: F401 — tên công khai cũ của module này
    SWING_TYPES_CAU_TRUC,
    SWING_TYPES_NHO,
    TARGET_SWING_CAU_TRUC,
    TARGET_SWING_NHO,
    all_targets,
    get_target,
)

PROTOCOL_VERSION = "1.0.0"

MATCHER_GREEDY_LABEL_ORDER_V1 = "greedy_label_order_v1"
MATCHER_MIN_COST_V1 = "min_cost_v1"
MATCHER_VERSIONS = (MATCHER_GREEDY_LABEL_ORDER_V1, MATCHER_MIN_COST_V1)

ATR_SOURCE_WILDER_CONFIRM = "wilder_confirm_bar"


def target_ids() -> tuple[str, ...]:
    return tuple(t.id for t in all_targets())


def default_event_type_map(target: str, *, map_level1_to_structure: bool = False) -> dict[str, str]:
    """Ánh xạ loại sự kiện thuật toán → loại nhãn được chấm.

    Chỉ những loại có trong map mới được đếm. HH/LH/BOS mặc định bị loại.
    """
    return get_target(target).default_event_type_map(map_level1_to_structure)


def target_label_types(target: str) -> tuple[str, ...]:
    return get_target(target).label_types


def target_label_vi(target: str) -> str:
    return get_target(target).label_vi


@dataclass
class EvalProtocol:
    """Quy tắc chấm một lần đánh giá — phải đủ để tái lập số liệu."""

    version: str = PROTOCOL_VERSION
    target: str = TARGET_SWING_CAU_TRUC
    matcher_version: str = MATCHER_MIN_COST_V1
    time_tolerance_bars: int = 1
    price_tolerance: float = 0.0
    coverage_start_index: Optional[int] = None
    coverage_end_index: Optional[int] = None
    event_type_map: dict[str, str] = field(default_factory=dict)
    map_level1_to_structure: bool = False
    atr_period: int = 14
    atr_source: str = ATR_SOURCE_WILDER_CONFIRM
    exclude_unconfirmed_tail: bool = True
    max_lag_bars: Optional[int] = None
    min_recall: Optional[float] = None

    def __post_init__(self) -> None:
        if self.target not in target_ids():
            raise ValueError("Mục tiêu không hỗ trợ: %r" % self.target)
        if self.matcher_version not in MATCHER_VERSIONS:
            raise ValueError(
                "Phiên bản matcher không hỗ trợ: %r. Có: %s"
                % (self.matcher_version, list(MATCHER_VERSIONS))
            )
        if self.time_tolerance_bars < 0 or self.price_tolerance < 0:
            raise ValueError("Dung sai thời gian và giá phải >= 0.")
        if self.atr_period < 1:
            raise ValueError("atr_period phải >= 1.")
        if self.atr_source != ATR_SOURCE_WILDER_CONFIRM:
            raise ValueError("atr_source không hỗ trợ: %r" % self.atr_source)
        if not self.event_type_map:
            self.event_type_map = default_event_type_map(
                self.target, map_level1_to_structure=self.map_level1_to_structure
            )
        self.event_type_map = {str(k): str(v) for k, v in self.event_type_map.items()}
        wanted = set(target_label_types(self.target))
        for src, dst in self.event_type_map.items():
            if dst not in wanted:
                raise ValueError(
                    "Ánh xạ %s → %s không thuộc mục tiêu %s (nhãn hợp lệ: %s)."
                    % (src, dst, self.target, list(wanted))
                )

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "EvalProtocol":
        raw = dict(raw or {})
        map_l1 = bool(raw.get("map_level1_to_structure", False))
        target = str(raw.get("target") or TARGET_SWING_CAU_TRUC)
        ev_map = raw.get("event_type_map") or default_event_type_map(
            target, map_level1_to_structure=map_l1
        )
        cov_s = raw.get("coverage_start_index")
        cov_e = raw.get("coverage_end_index")
        return cls(
            version=str(raw.get("version") or PROTOCOL_VERSION),
            target=target,
            matcher_version=str(raw.get("matcher_version") or MATCHER_MIN_COST_V1),
            time_tolerance_bars=int(raw.get("time_tolerance_bars", 1)),
            price_tolerance=float(raw.get("price_tolerance", 0.0)),
            coverage_start_index=None if cov_s is None or cov_s == "" else int(cov_s),
            coverage_end_index=None if cov_e is None or cov_e == "" else int(cov_e),
            event_type_map=dict(ev_map),
            map_level1_to_structure=map_l1,
            atr_period=int(raw.get("atr_period", 14)),
            atr_source=str(raw.get("atr_source") or ATR_SOURCE_WILDER_CONFIRM),
            exclude_unconfirmed_tail=bool(raw.get("exclude_unconfirmed_tail", True)),
            max_lag_bars=(
                None
                if raw.get("max_lag_bars") in (None, "")
                else int(raw["max_lag_bars"])
            ),
            min_recall=(
                None
                if raw.get("min_recall") in (None, "")
                else float(raw["min_recall"])
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d

    def fingerprint(self) -> str:
        """Khoá ổn định để tách nhóm so sánh và truy vết kết quả."""
        payload = {
            "version": self.version,
            "target": self.target,
            "matcher_version": self.matcher_version,
            "time_tolerance_bars": self.time_tolerance_bars,
            "price_tolerance": self.price_tolerance,
            "coverage_start_index": self.coverage_start_index,
            "coverage_end_index": self.coverage_end_index,
            "event_type_map": dict(sorted(self.event_type_map.items())),
            "map_level1_to_structure": self.map_level1_to_structure,
            "atr_period": self.atr_period,
            "atr_source": self.atr_source,
            "exclude_unconfirmed_tail": self.exclude_unconfirmed_tail,
            "max_lag_bars": self.max_lag_bars,
            "min_recall": self.min_recall,
        }
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]

    def label_types(self) -> tuple[str, ...]:
        return target_label_types(self.target)

    def coverage_tuple(self) -> tuple[Optional[int], Optional[int]]:
        return (self.coverage_start_index, self.coverage_end_index)


def describe_targets() -> list[dict[str, Any]]:
    return [t.describe() for t in all_targets()]
