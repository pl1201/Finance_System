"""Ghép sự kiện thuật toán với nhãn tham chiếu — mới được phép nói precision/recall.

Quy tắc ghép của ``evaluate_detection`` (tab Nhãn tham chiếu, ``/api/evaluate``):

* Cùng ``structure_type`` (khớp nguyên chuỗi, không gộp BOS nội bộ với BOS chính).
* ``|event_bar_index − label.bar_index| ≤ time_tolerance_bars``
* ``|event.price − label.price| ≤ price_tolerance`` (đơn vị giá).
* Matcher ``greedy_label_order_v1``: mỗi nhãn (theo thứ tự nến rồi seq) lấy sự
  kiện chưa ghép có |Δnến| nhỏ nhất, hoà thì |Δgiá| nhỏ hơn; một-một.
  Cách này có thể bỏ lỡ phép gán tốt hơn khi nhiều sự kiện nằm gần nhau.

Trang Đánh giá thuật toán dùng protocol riêng (``core.eval``): mặc định
``min_cost_v1``, F1, P90, phạm vi gán nhãn đầy đủ. Không trộn số liệu hai
matcher / hai phiên bản protocol. Xem ``docs/guides/danh_gia_thuat_toan.md``.

Precision = TP / (TP + FP), Recall = TP / (TP + FN).
Không tính nếu bộ nhãn rỗng. Báo cáo luôn kèm tên người gán.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence


#: Loại nhãn dựng sẵn của lab (swing hai cấp, BOS/CHoCH).
BUILTIN_LABEL_TYPES = (
    "SWING_HIGH", "SWING_LOW",
    "SWING_HIGH_L2", "SWING_LOW_L2",
    "BOS_UP", "BOS_DOWN",
    "BOS_INTERNAL_UP", "BOS_INTERNAL_DOWN",
    "CHOCH_UP", "CHOCH_DOWN",
)


def label_types() -> tuple[str, ...]:
    """Loại nhãn tham chiếu được chấp nhận: dựng sẵn + loại thuật toán khai ``label_types``.

    Vd ``ict_structure`` thêm SHIFT_UP / SHIFT_DOWN
    (neo ở nến có close vượt mức). Thứ tự: dựng sẵn rồi theo thứ tự registry.
    """
    from core.registry import algorithm_classes  # import muộn: registry nạp thuật toán

    out = list(BUILTIN_LABEL_TYPES)
    for cls in algorithm_classes():
        out.extend(t for t in cls.label_types if t not in out)
    return tuple(out)


@dataclass
class ReferenceLabel:
    structure_type: str
    bar_index: int
    price: float
    notes: str = ""
    seq: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "structure_type": self.structure_type,
            "bar_index": self.bar_index,
            "price": self.price,
            "notes": self.notes,
            "seq": self.seq,
        }


@dataclass
class MatchPair:
    label_seq: int
    event_id: str
    structure_type: str
    delta_bars: int
    delta_price: float


@dataclass
class EvaluationResult:
    annotator: str
    label_set_id: str
    label_set_version: str
    rubric_vi: str
    time_tolerance_bars: int
    price_tolerance: float
    true_positives: int
    false_positives: int
    false_negatives: int
    precision: Optional[float]
    recall: Optional[float]
    by_type: dict[str, dict[str, Any]]
    matches: list[MatchPair] = field(default_factory=list)
    unmatched_labels: list[dict[str, Any]] = field(default_factory=list)
    unmatched_events: list[str] = field(default_factory=list)
    note_vi: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "annotator": self.annotator,
            "label_set_id": self.label_set_id,
            "label_set_version": self.label_set_version,
            "rubric_vi": self.rubric_vi,
            "time_tolerance_bars": self.time_tolerance_bars,
            "price_tolerance": self.price_tolerance,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "by_type": self.by_type,
            "matches": [
                {
                    "label_seq": m.label_seq,
                    "event_id": m.event_id,
                    "structure_type": m.structure_type,
                    "delta_bars": m.delta_bars,
                    "delta_price": m.delta_price,
                }
                for m in self.matches
            ],
            "unmatched_labels": self.unmatched_labels,
            "unmatched_events": self.unmatched_events,
            "note_vi": self.note_vi,
        }


def evaluate_detection(
    events: Sequence[Any],
    labels: Sequence[ReferenceLabel],
    *,
    annotator: str,
    label_set_id: str = "",
    label_set_version: str = "",
    rubric_vi: str = "",
    time_tolerance_bars: int = 1,
    price_tolerance: float = 0.0,
    event_types: Optional[Sequence[str]] = None,
) -> EvaluationResult:
    if not annotator or not str(annotator).strip():
        raise ValueError("Phải ghi tên người gán nhãn — không tính precision ẩn danh.")
    if time_tolerance_bars < 0 or price_tolerance < 0:
        raise ValueError("Dung sai thời gian và giá phải >= 0.")

    wanted = set(event_types) if event_types else set(label_types())
    evs = [
        e for e in events
        if _stype(e) in wanted
    ]
    labs = [lb for lb in labels if lb.structure_type in wanted]

    if not labs:
        return EvaluationResult(
            annotator=annotator.strip(),
            label_set_id=label_set_id,
            label_set_version=label_set_version,
            rubric_vi=rubric_vi,
            time_tolerance_bars=time_tolerance_bars,
            price_tolerance=price_tolerance,
            true_positives=0,
            false_positives=0,
            false_negatives=0,
            precision=None,
            recall=None,
            by_type={},
            note_vi="Bộ nhãn trống — không tính precision/recall.",
        )

    used_e: set[int] = set()
    matches: list[MatchPair] = []
    unmatched_l: list[dict[str, Any]] = []

    # Ưu tiên nhãn theo thứ tự nến rồi seq.
    ordered = sorted(labs, key=lambda x: (x.bar_index, x.seq))
    for lb in ordered:
        best_i = None
        best_key = None
        for i, e in enumerate(evs):
            if i in used_e:
                continue
            if _stype(e) != lb.structure_type:
                continue
            dbars = abs(int(_bar(e)) - int(lb.bar_index))
            dpx = abs(float(_price(e)) - float(lb.price))
            if dbars > time_tolerance_bars or dpx > price_tolerance:
                continue
            key = (dbars, dpx)
            if best_key is None or key < best_key:
                best_key = key
                best_i = i
        if best_i is None:
            unmatched_l.append(lb.to_dict())
            continue
        used_e.add(best_i)
        e = evs[best_i]
        matches.append(
            MatchPair(
                label_seq=lb.seq,
                event_id=_eid(e),
                structure_type=lb.structure_type,
                delta_bars=abs(int(_bar(e)) - int(lb.bar_index)),
                delta_price=abs(float(_price(e)) - float(lb.price)),
            )
        )

    tp = len(matches)
    fn = len(unmatched_l)
    fp = len(evs) - len(used_e)
    precision = (tp / (tp + fp)) if (tp + fp) else None
    recall = (tp / (tp + fn)) if (tp + fn) else None

    by_type: dict[str, dict[str, Any]] = {}
    types = sorted({_stype(e) for e in evs} | {lb.structure_type for lb in labs})
    for t in types:
        t_labs = [lb for lb in labs if lb.structure_type == t]
        t_evs = [i for i, e in enumerate(evs) if _stype(e) == t]
        t_tp = sum(1 for m in matches if m.structure_type == t)
        t_fn = sum(1 for lb in unmatched_l if lb["structure_type"] == t)
        t_fp = len(t_evs) - sum(
            1 for i in used_e if _stype(evs[i]) == t
        )
        by_type[t] = {
            "nhan": len(t_labs),
            "su_kien_thuat_toan": len(t_evs),
            "true_positives": t_tp,
            "false_positives": t_fp,
            "false_negatives": t_fn,
            "precision": (t_tp / (t_tp + t_fp)) if (t_tp + t_fp) else None,
            "recall": (t_tp / (t_tp + t_fn)) if (t_tp + t_fn) else None,
        }

    unmatched_e = [_eid(evs[i]) for i in range(len(evs)) if i not in used_e]
    return EvaluationResult(
        annotator=annotator.strip(),
        label_set_id=label_set_id,
        label_set_version=str(label_set_version),
        rubric_vi=rubric_vi,
        time_tolerance_bars=time_tolerance_bars,
        price_tolerance=price_tolerance,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        by_type=by_type,
        matches=matches,
        unmatched_labels=unmatched_l,
        unmatched_events=unmatched_e,
        note_vi=(
            "Precision/recall so với nhãn của %s (bộ %s, phiên bản %s). "
            "Dung sai %d nến / %s đơn vị giá. Không phải win-rate hay P&L."
            % (annotator.strip(), label_set_id or "—", label_set_version or "—",
               time_tolerance_bars, price_tolerance)
        ),
    )


def _stype(e: Any) -> str:
    return e["structure_type"] if isinstance(e, dict) else e.structure_type


def _bar(e: Any) -> int:
    if isinstance(e, dict):
        return int(e.get("event_bar_index", e.get("bar_index", 0)))
    return int(e.event_bar_index)


def _price(e: Any) -> float:
    return float(e["price"] if isinstance(e, dict) else e.price)


def _eid(e: Any) -> str:
    return str(e["event_id"] if isinstance(e, dict) else e.event_id)
