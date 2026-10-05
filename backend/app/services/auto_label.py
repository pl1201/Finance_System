"""Auto label: thuật toán có sẵn ĐỀ XUẤT nhãn, người duyệt. Không ghi gì vào kho nhãn."""
from __future__ import annotations

import json
from typing import Any, Optional

from backend.app.errors import ServiceError
from backend.app.services.common import get_dataset_or_error, load_bars, resolve_dataset_params
from core.engine import run_algorithm
from core.registry import get_algorithm_class, list_algorithms


def auto_label_algorithms() -> list[dict[str, Any]]:
    """Các thuật toán đề xuất được nhãn cấu trúc, kèm loại nhãn mỗi cái sinh ra."""
    from core.labels import label_types

    known = label_types()
    out = []
    for a in list_algorithms():
        types = [t for t in a.get("emits_types") or [] if t in known]
        if types:
            out.append({**a, "label_types": types})
    return out


def suggest_auto_labels(
    *,
    dataset_id: str,
    algorithm: str,
    params: dict[str, Any] | None,
    start_index: Optional[int] = None,
    end_index: Optional[int] = None,
    types: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Chạy một thuật toán có sẵn và trả về ĐỀ XUẤT nhãn trong khoảng nến.

    Không ghi gì vào kho nhãn. Người dùng phải chấp nhận từng đề xuất (hoặc
    chấp nhận hàng loạt có chủ đích) rồi bấm Lưu.

    Thuật toán chạy trên TOÀN BỘ dataset rồi mới lọc theo khoảng: nhãn là
    đánh giá hồi cứu nên được phép nhìn các nến sau, và nhờ vậy pivot ở sát
    mép phải của khoảng vẫn có đủ nến bên phải để xác nhận.
    """
    from core.labels import label_types

    known = label_types()
    ds = get_dataset_or_error(dataset_id)
    n_bars = int(ds["row_count"])
    try:
        cls = get_algorithm_class(algorithm)
    except KeyError as exc:
        raise ServiceError(str(exc)) from exc

    emitted = [t for t in cls.emits_types if t in known]
    if not emitted:
        usable = ", ".join(a["name"] for a in auto_label_algorithms()) or "(không có)"
        raise ServiceError(
            "Thuật toán %r không sinh loại nhãn cấu trúc nào nên không dùng để "
            "đề xuất nhãn được. Dùng: %s." % (algorithm, usable)
        )

    start = 0 if start_index is None else int(start_index)
    end = n_bars - 1 if end_index is None else int(end_index)
    if start < 0 or end > n_bars - 1 or start > end:
        raise ServiceError(
            "Khoảng nến %d → %d không hợp lệ cho dataset %s %s (0 → %d)."
            % (start, end, ds["symbol"], ds["timeframe"], n_bars - 1)
        )

    warnings: list[str] = []
    wanted = set(emitted)
    if types:
        bad = [t for t in types if t not in known]
        if bad:
            raise ServiceError("Loại nhãn không hỗ trợ: %s" % ", ".join(bad))
        not_emitted = [t for t in types if t not in emitted]
        if not_emitted:
            warnings.append(
                "%s không sinh loại %s — không có đề xuất cho các loại này."
                % (cls.name, ", ".join(not_emitted))
            )
        wanted = set(types) & set(emitted)

    try:
        norm = cls.validate_params(resolve_dataset_params(cls, params, ds))
        cls.check_dataset(ds["timeframe"], norm)
        algo = cls(**norm)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc

    _, bars, _ = load_bars(dataset_id)
    try:
        result = run_algorithm(bars, algo)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc

    detail = "%s v%s %s" % (
        algo.name, algo.version, json.dumps(norm, sort_keys=True, ensure_ascii=False)
    )
    suggestions: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for e in result.events:
        if e.structure_type not in wanted:
            continue
        if not (start <= e.event_bar_index <= end):
            continue
        key = (e.structure_type, e.event_bar_index)
        if key in seen:
            continue
        seen.add(key)
        d = e.to_dict()
        suggestions.append({
            "structure_type": e.structure_type,
            "bar_index": e.event_bar_index,
            "price": e.price,
            "event_id": e.event_id,
            "confirmed_bar_index": e.confirmed_bar_index,
            "confirmation_lag_bars": e.confirmation_lag_bars,
            "reason_code": e.reason_code,
            "reason_text_vi": d.get("reason_text_vi") or "",
            "structure_text_vi": d.get("structure_text_vi") or "",
            "source": "auto_accepted",
            "source_algorithm": algo.name,
            "source_detail": detail,
        })
    suggestions.sort(key=lambda x: (x["bar_index"], x["structure_type"]))

    # Nến sát cuối dataset có thể chưa đủ nến bên phải để xác nhận — thiếu đề
    # xuất ở đó không có nghĩa là không có cấu trúc.
    tail = algo.warmup_bars()
    if end > n_bars - 1 - tail:
        warnings.append(
            "Khoảng chạm %d nến cuối dataset: thuật toán có thể chưa đủ nến bên "
            "phải để xác nhận cấu trúc ở đó. Hãy tự rà phần này." % tail
        )

    by_type: dict[str, int] = {}
    for sg in suggestions:
        by_type[sg["structure_type"]] = by_type.get(sg["structure_type"], 0) + 1

    return {
        "dataset": {"id": ds["id"], "symbol": ds["symbol"], "timeframe": ds["timeframe"]},
        "algorithm": algo.name,
        "algorithm_version": algo.version,
        "params": norm,
        "source_detail": detail,
        "start_index": start,
        "end_index": end,
        "types": sorted(wanted),
        "suggestions": suggestions,
        "so_de_xuat_theo_loai": by_type,
        "warnings": warnings,
        "ghi_chu_vi": (
            "%d đề xuất từ %s trong nến %d → %d. Đây CHƯA phải nhãn: chỉ đề xuất "
            "được bạn chấp nhận mới vào bộ nháp, và vẫn phải bấm Lưu. Nhãn chấp "
            "nhận từ đề xuất được ghi nguồn gốc để trang Đánh giá cảnh báo khi "
            "chấm chính thuật toán đã đề xuất chúng."
            % (len(suggestions), detail, start, end)
        ),
    }
