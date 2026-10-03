"""Matcher 1-1 giữa nhãn tham chiếu và sự kiện đã ánh xạ.

Hai phiên bản được khoá:

* ``greedy_label_order_v1`` — mỗi nhãn (theo thứ tự nến, seq) lấy sự kiện
  chưa dùng có |Δnến| nhỏ nhất, hoà thì |Δgiá| nhỏ hơn. Đây là hành vi
  ``evaluate_detection`` cũ. Có thể bỏ lỡ cách ghép có nhiều TP hơn.
* ``min_cost_v1`` — trong tập cặp hợp lệ, tối đa số cặp rồi tối thiểu tổng
  (Δnến, Δgiá). Đây là mặc định của protocol đánh giá 1.0.0.

Không ghép khác ``structure_type`` (sau ánh xạ).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence

from core.eval.protocol import (
    MATCHER_GREEDY_LABEL_ORDER_V1,
    MATCHER_MIN_COST_V1,
)
from core.labels import ReferenceLabel, _bar, _eid, _price, _stype


@dataclass
class MatchHit:
    label_seq: int
    label_index: int
    event_index: int
    event_id: str
    structure_type: str
    delta_bars: int
    delta_price: float


@dataclass
class MatchResult:
    matcher_version: str
    matches: list[MatchHit]
    unmatched_label_indices: list[int]
    unmatched_event_indices: list[int]


def pair_cost(
    label: ReferenceLabel,
    event: Any,
    *,
    time_tolerance_bars: int,
    price_tolerance: float,
) -> Optional[tuple[int, float]]:
    if _stype(event) != label.structure_type:
        return None
    dbars = abs(int(_bar(event)) - int(label.bar_index))
    dpx = abs(float(_price(event)) - float(label.price))
    if dbars > time_tolerance_bars or dpx > price_tolerance:
        return None
    return (dbars, dpx)


def match_labels(
    labels: Sequence[ReferenceLabel],
    events: Sequence[Any],
    *,
    time_tolerance_bars: int,
    price_tolerance: float,
    matcher_version: str,
) -> MatchResult:
    if matcher_version == MATCHER_GREEDY_LABEL_ORDER_V1:
        return _greedy_label_order(labels, events, time_tolerance_bars, price_tolerance)
    if matcher_version == MATCHER_MIN_COST_V1:
        return _min_cost(labels, events, time_tolerance_bars, price_tolerance)
    raise ValueError("Phiên bản matcher không hỗ trợ: %r" % matcher_version)


def _greedy_label_order(
    labels: Sequence[ReferenceLabel],
    events: Sequence[Any],
    time_tol: int,
    price_tol: float,
) -> MatchResult:
    used: set[int] = set()
    matches: list[MatchHit] = []
    unmatched_l: list[int] = []
    order = sorted(range(len(labels)), key=lambda i: (labels[i].bar_index, labels[i].seq, i))
    for li in order:
        lb = labels[li]
        best_j = None
        best_key = None
        for j, e in enumerate(events):
            if j in used:
                continue
            cost = pair_cost(lb, e, time_tolerance_bars=time_tol, price_tolerance=price_tol)
            if cost is None:
                continue
            if best_key is None or cost < best_key:
                best_key = cost
                best_j = j
        if best_j is None or best_key is None:
            unmatched_l.append(li)
            continue
        used.add(best_j)
        e = events[best_j]
        matches.append(
            MatchHit(
                label_seq=lb.seq,
                label_index=li,
                event_index=best_j,
                event_id=_eid(e),
                structure_type=lb.structure_type,
                delta_bars=best_key[0],
                delta_price=best_key[1],
            )
        )
    unmatched_e = [j for j in range(len(events)) if j not in used]
    return MatchResult(
        matcher_version=MATCHER_GREEDY_LABEL_ORDER_V1,
        matches=matches,
        unmatched_label_indices=unmatched_l,
        unmatched_event_indices=unmatched_e,
    )


def _encode_cost(dbars: int, dpx: float) -> int:
    """Đóng gói (Δnến, Δgiá) thành một số nguyên để min-cost.

    1 đơn vị nến nặng hơn mọi chênh giá dưới 1e6 đơn vị giá.
    """
    px = int(round(dpx * 1000.0))
    if px < 0:
        px = 0
    return dbars * 1_000_000_000 + px


def _min_cost(
    labels: Sequence[ReferenceLabel],
    events: Sequence[Any],
    time_tol: int,
    price_tol: float,
) -> MatchResult:
    n, m = len(labels), len(events)
    edges: list[tuple[int, int, int, int, float]] = []
    for i, lb in enumerate(labels):
        for j, e in enumerate(events):
            cost = pair_cost(lb, e, time_tolerance_bars=time_tol, price_tolerance=price_tol)
            if cost is None:
                continue
            edges.append((i, j, _encode_cost(cost[0], cost[1]), cost[0], cost[1]))

    assigned = _min_cost_max_flow(n, m, [(a, b, c) for a, b, c, _, _ in edges])
    cost_lookup = {(a, b): (db, dp) for a, b, _, db, dp in edges}
    used_l: set[int] = set()
    used_e: set[int] = set()
    matches: list[MatchHit] = []
    for i, j in assigned:
        lb = labels[i]
        e = events[j]
        db, dp = cost_lookup[(i, j)]
        used_l.add(i)
        used_e.add(j)
        matches.append(
            MatchHit(
                label_seq=lb.seq,
                label_index=i,
                event_index=j,
                event_id=_eid(e),
                structure_type=lb.structure_type,
                delta_bars=db,
                delta_price=dp,
            )
        )
    matches.sort(key=lambda h: (h.label_seq, h.label_index))
    return MatchResult(
        matcher_version=MATCHER_MIN_COST_V1,
        matches=matches,
        unmatched_label_indices=[i for i in range(n) if i not in used_l],
        unmatched_event_indices=[j for j in range(m) if j not in used_e],
    )


def _min_cost_max_flow(
    n_left: int, n_right: int, edges: Sequence[tuple[int, int, int]]
) -> list[tuple[int, int]]:
    """Gán 1-1: tối đa số cạnh, rồi tối thiểu tổng cost (số nguyên).

    Mạng: source → nhãn → sự kiện → sink, mỗi cạnh dung lượng 1.
    """
    if n_left == 0 or n_right == 0 or not edges:
        return []

    src = n_left + n_right
    sink = src + 1
    n_nodes = sink + 1
    graph: list[list[int]] = [[] for _ in range(n_nodes)]
    to: list[int] = []
    cap: list[int] = []
    cost: list[int] = []

    def add_edge(u: int, v: int, capacity: int, cst: int) -> None:
        graph[u].append(len(to))
        to.append(v)
        cap.append(capacity)
        cost.append(cst)
        graph[v].append(len(to))
        to.append(u)
        cap.append(0)
        cost.append(-cst)

    for i in range(n_left):
        add_edge(src, i, 1, 0)
    for j in range(n_right):
        add_edge(n_left + j, sink, 1, 0)
    for i, j, cst in edges:
        add_edge(i, n_left + j, 1, cst)

    inf = 10**18
    while True:
        dist = [inf] * n_nodes
        dist[src] = 0
        inq = [False] * n_nodes
        q = [src]
        inq[src] = True
        parent_edge = [-1] * n_nodes
        head = 0
        while head < len(q):
            u = q[head]
            head += 1
            inq[u] = False
            for ei in graph[u]:
                if cap[ei] <= 0:
                    continue
                v = to[ei]
                nd = dist[u] + cost[ei]
                if nd < dist[v]:
                    dist[v] = nd
                    parent_edge[v] = ei
                    if not inq[v]:
                        inq[v] = True
                        q.append(v)
        if dist[sink] >= inf:
            break
        v = sink
        while v != src:
            ei = parent_edge[v]
            cap[ei] -= 1
            cap[ei ^ 1] += 1
            v = to[ei ^ 1]

    assigned: list[tuple[int, int]] = []
    for i in range(n_left):
        for ei in graph[i]:
            v = to[ei]
            if not (n_left <= v < n_left + n_right):
                continue
            if cap[ei] == 0:
                assigned.append((i, v - n_left))
    return sorted(assigned)
