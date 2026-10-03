"""Protocol đánh giá nhận diện — phiên bản được lưu cùng kết quả.

Thay đổi quy tắc chấm phải tăng ``PROTOCOL_VERSION`` hoặc ``matcher_version``
để không trộn kết quả cũ/mới.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


PROTOCOL_VERSION = "1.0.0"

MATCHER_GREEDY_LABEL_ORDER_V1 = "greedy_label_order_v1"
MATCHER_MIN_COST_V1 = "min_cost_v1"
MATCHER_VERSIONS = (MATCHER_GREEDY_LABEL_ORDER_V1, MATCHER_MIN_COST_V1)

TARGET_SWING_NHO = "swing_nho"
TARGET_SWING_CAU_TRUC = "swing_cau_truc"
TARGET_C2 = "c2"
TARGET_CISD = "cisd"
TARGETS = (TARGET_SWING_NHO, TARGET_SWING_CAU_TRUC, TARGET_C2, TARGET_CISD)

#: Loại sự kiện được đếm là "một swing". HH/LH/EQH/BOS không nằm đây.
SWING_TYPES_NHO = ("SWING_HIGH", "SWING_LOW")
SWING_TYPES_CAU_TRUC = ("SWING_HIGH_L2", "SWING_LOW_L2")
#: c2_cisd_research — chấm đúng loại, cùng hướng; không dùng HH/MSS làm nhãn thay.
C2_TYPES = ("C2_CONFIRMED_UP", "C2_CONFIRMED_DOWN")
CISD_TYPES = ("CISD_CONFIRMED_UP", "CISD_CONFIRMED_DOWN")

#: Phía "high" = sự kiện ở đỉnh (C2/CISD giảm quét high), "low" = ở đáy.
HIGH_TYPES = frozenset({"SWING_HIGH", "SWING_HIGH_L2", "C2_CONFIRMED_DOWN", "CISD_CONFIRMED_DOWN"})
LOW_TYPES = frozenset({"SWING_LOW", "SWING_LOW_L2", "C2_CONFIRMED_UP", "CISD_CONFIRMED_UP"})

ATR_SOURCE_WILDER_CONFIRM = "wilder_confirm_bar"


def default_event_type_map(target: str, *, map_level1_to_structure: bool = False) -> dict[str, str]:
    """Ánh xạ loại sự kiện thuật toán → loại nhãn được chấm.

    Chỉ những loại có trong map mới được đếm. HH/LH/BOS mặc định bị loại.
    """
    if target == TARGET_SWING_NHO:
        return {"SWING_HIGH": "SWING_HIGH", "SWING_LOW": "SWING_LOW"}
    if target == TARGET_SWING_CAU_TRUC:
        out = {
            "SWING_HIGH_L2": "SWING_HIGH_L2",
            "SWING_LOW_L2": "SWING_LOW_L2",
        }
        if map_level1_to_structure:
            out["SWING_HIGH"] = "SWING_HIGH_L2"
            out["SWING_LOW"] = "SWING_LOW_L2"
        return out
    if target == TARGET_C2:
        return {t: t for t in C2_TYPES}
    if target == TARGET_CISD:
        return {t: t for t in CISD_TYPES}
    raise ValueError("Mục tiêu không hỗ trợ: %r" % target)


def target_label_types(target: str) -> tuple[str, ...]:
    if target == TARGET_SWING_NHO:
        return SWING_TYPES_NHO
    if target == TARGET_SWING_CAU_TRUC:
        return SWING_TYPES_CAU_TRUC
    if target == TARGET_C2:
        return C2_TYPES
    if target == TARGET_CISD:
        return CISD_TYPES
    raise ValueError("Mục tiêu không hỗ trợ: %r" % target)


def target_label_vi(target: str) -> str:
    return {
        TARGET_SWING_NHO: "Swing nhỏ (cấp 1)",
        TARGET_SWING_CAU_TRUC: "Swing cấu trúc (cấp 2)",
        TARGET_C2: "C2 sweep H4 (c2_cisd_research)",
        TARGET_CISD: "CISD xác nhận cho setup C2 (c2_cisd_research)",
    }[target]


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
        if self.target not in TARGETS:
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
    return [
        {
            "id": TARGET_SWING_NHO,
            "label_vi": target_label_vi(TARGET_SWING_NHO),
            "label_types": list(SWING_TYPES_NHO),
            "help_vi": (
                "Chấm đỉnh/đáy fractal cấp 1. Không đếm nhãn HH/LH hay BOS "
                "của cùng một pivot thành swing thứ hai."
            ),
        },
        {
            "id": TARGET_SWING_CAU_TRUC,
            "label_vi": target_label_vi(TARGET_SWING_CAU_TRUC),
            "label_types": list(SWING_TYPES_CAU_TRUC),
            "help_vi": (
                "Chấm đỉnh/đáy cấp 2. Muốn đưa run cấp 1 vào cùng bảng, bật "
                "ánh xạ SWING_HIGH→SWING_HIGH_L2 (khai báo rõ, không trộn tên loại)."
            ),
        },
        {
            "id": TARGET_C2,
            "label_vi": target_label_vi(TARGET_C2),
            "label_types": list(C2_TYPES),
            "help_vi": (
                "Chấm C2_CONFIRMED_UP/DOWN: nhãn đặt ở NẾN M15 CỰC TRỊ của C2, giá = low "
                "(tăng) / high (giảm). Một-một, cùng hướng. Chỉ khi đã có nhãn C2 do người gán "
                "— không dựng F1 từ output của chính thuật toán hay từ nhãn HH/MSS."
            ),
        },
        {
            "id": TARGET_CISD,
            "label_vi": target_label_vi(TARGET_CISD),
            "label_types": list(CISD_TYPES),
            "help_vi": (
                "Chấm CISD_CONFIRMED_UP/DOWN: nhãn đặt ở nến có CLOSE vượt mức CISD (nến bằng "
                "chứng), giá = mức CISD. Early CISD của setup cũng là CISD_CONFIRMED. Nếu nhãn "
                "không ghi đúng mức, nới dung sai giá hoặc chỉ chấm theo thời gian."
            ),
        },
    ]
