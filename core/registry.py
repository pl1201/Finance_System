"""Registry thuật toán.

Thêm thuật toán mới:

1. Tạo file trong ``core/algorithms/`` với một lớp con của
   :class:`core.algorithms.base.StructureAlgorithm`.
2. Import và thêm vào ``_ALGORITHMS`` bên dưới.

Giao diện web tự động đọc registry này để dựng danh sách thuật toán và
form tham số — không cần sửa frontend.
"""
from __future__ import annotations

from typing import Any, Type

from core.algorithms.base import StructureAlgorithm
from core.algorithms.hmm_online import HmmOnlineAlgorithm
from core.algorithms.indicator_baseline import IndicatorBaselineAlgorithm
from core.algorithms.swing_hierarchy import SwingHierarchyAlgorithm
from core.algorithms.swing_pivot import SwingPivotAlgorithm

_ALGORITHMS: dict[str, Type[StructureAlgorithm]] = {
    SwingPivotAlgorithm.name: SwingPivotAlgorithm,
    SwingHierarchyAlgorithm.name: SwingHierarchyAlgorithm,
    IndicatorBaselineAlgorithm.name: IndicatorBaselineAlgorithm,
    HmmOnlineAlgorithm.name: HmmOnlineAlgorithm,
}


def list_algorithms() -> list[dict[str, Any]]:
    """Mô tả toàn bộ thuật toán đã đăng ký, dạng JSON cho giao diện."""
    out = []
    for key, cls in _ALGORITHMS.items():
        out.append(
            {
                "name": key,
                "display_name_vi": cls.display_name_vi,
                "version": cls.version,
                "description_vi": cls.description_vi,
                "params": [s.to_dict() for s in cls.param_specs()],
            }
        )
    return out


def get_algorithm_class(name: str) -> Type[StructureAlgorithm]:
    if name not in _ALGORITHMS:
        raise KeyError(
            "Không có thuật toán %r. Hiện có: %s"
            % (name, ", ".join(_ALGORITHMS))
        )
    return _ALGORITHMS[name]


def create_algorithm(name: str, params: dict[str, Any] | None = None) -> StructureAlgorithm:
    cls = get_algorithm_class(name)
    return cls(**(params or {}))
