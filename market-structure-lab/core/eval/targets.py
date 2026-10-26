"""Mục tiêu chấm (target) của trang Đánh giá — dữ liệu khai báo, không phải luồng ``if``.

Mỗi mục tiêu nói: chấm loại nhãn nào, ánh xạ sự kiện → nhãn mặc định, loại nào thuộc
phía đỉnh / đáy (F1 theo phía). Swing cấp 1 / cấp 2 là mục tiêu dựng sẵn của lab;
thuật toán có loại nhãn riêng tự khai ``eval_targets`` trên lớp thuật toán (vd
``ict_structure``). ``all_targets()`` ghép dựng sẵn + theo thứ tự registry.

Đổi định nghĩa một mục tiêu đang dùng (loại nhãn, ánh xạ) = đổi quy tắc chấm → phải
tăng ``PROTOCOL_VERSION`` (``protocol.py``). Thêm mục tiêu mới không đổi kết quả cũ.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TARGET_SWING_NHO = "swing_nho"
TARGET_SWING_CAU_TRUC = "swing_cau_truc"

#: Loại sự kiện được đếm là "một swing". HH/LH/EQH/BOS không nằm đây.
SWING_TYPES_NHO = ("SWING_HIGH", "SWING_LOW")
SWING_TYPES_CAU_TRUC = ("SWING_HIGH_L2", "SWING_LOW_L2")


@dataclass(frozen=True)
class EvalTarget:
    id: str
    label_vi: str
    label_types: tuple[str, ...]
    help_vi: str
    #: Loại thuộc phía đỉnh / đáy, dùng để tách F1 theo phía.
    high_types: tuple[str, ...] = ()
    low_types: tuple[str, ...] = ()
    #: Ánh xạ thêm khi bật ``map_level1_to_structure`` (chỉ swing cấu trúc dùng).
    level1_map: tuple[tuple[str, str], ...] = ()

    def default_event_type_map(self, map_level1_to_structure: bool = False) -> dict[str, str]:
        """Loại sự kiện thuật toán → loại nhãn được chấm. Chỉ loại có trong map mới được đếm."""
        out = {t: t for t in self.label_types}
        if map_level1_to_structure:
            out.update(dict(self.level1_map))
        return out

    def describe(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label_vi": self.label_vi,
            "label_types": list(self.label_types),
            "help_vi": self.help_vi,
        }


BUILTIN_TARGETS: tuple[EvalTarget, ...] = (
    EvalTarget(
        id=TARGET_SWING_NHO,
        label_vi="Swing nhỏ (cấp 1)",
        label_types=SWING_TYPES_NHO,
        help_vi=(
            "Chấm đỉnh/đáy fractal cấp 1. Không đếm nhãn HH/LH hay BOS "
            "của cùng một pivot thành swing thứ hai."
        ),
        high_types=("SWING_HIGH",),
        low_types=("SWING_LOW",),
    ),
    EvalTarget(
        id=TARGET_SWING_CAU_TRUC,
        label_vi="Swing cấu trúc (cấp 2)",
        label_types=SWING_TYPES_CAU_TRUC,
        help_vi=(
            "Chấm đỉnh/đáy cấp 2. Muốn đưa run cấp 1 vào cùng bảng, bật "
            "ánh xạ SWING_HIGH→SWING_HIGH_L2 (khai báo rõ, không trộn tên loại)."
        ),
        high_types=("SWING_HIGH_L2",),
        low_types=("SWING_LOW_L2",),
        level1_map=(("SWING_HIGH", "SWING_HIGH_L2"), ("SWING_LOW", "SWING_LOW_L2")),
    ),
)


def all_targets() -> tuple[EvalTarget, ...]:
    """Mục tiêu dựng sẵn + mục tiêu do thuật toán đã đăng ký khai báo (theo thứ tự registry)."""
    from core.registry import algorithm_classes  # import muộn: registry nạp thuật toán

    out = list(BUILTIN_TARGETS)
    seen = {t.id for t in out}
    for cls in algorithm_classes():
        for t in cls.eval_targets:
            if t.id in seen:
                raise ValueError("Mục tiêu chấm %r bị khai báo hai lần (%s)." % (t.id, cls.name))
            seen.add(t.id)
            out.append(t)
    return tuple(out)


def get_target(target_id: str) -> EvalTarget:
    for t in all_targets():
        if t.id == target_id:
            return t
    raise ValueError("Mục tiêu không hỗ trợ: %r" % target_id)


def high_types() -> frozenset[str]:
    return frozenset(x for t in all_targets() for x in t.high_types)


def low_types() -> frozenset[str]:
    return frozenset(x for t in all_targets() for x in t.low_types)
