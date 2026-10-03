"""Chấm một hoặc nhiều lần chạy theo protocol — F1, độ trễ, ATR, mật độ.

Lõi thuần Python, không phụ thuộc FastAPI. Precision/recall/F1 chỉ khi có
nhãn trong khoảng được khai là gán đầy đủ. Không bịa «thuật toán tốt nhất».
"""
from __future__ import annotations

import time
from typing import Any, Optional, Sequence

from core.eval.causality import check_stored_event_invariants
from core.eval.matcher import match_labels
from core.eval.metrics import f1_score, lag_histogram, median, percentile_nearest_rank, ratio
from core.eval.protocol import EvalProtocol, target_label_vi
from core.eval.targets import high_types, low_types
from core.indicators import WilderATR
from core.labels import ReferenceLabel, _bar, _eid, _price, _stype


def evaluate_runs(
    runs: Sequence[dict[str, Any]],
    *,
    protocol: EvalProtocol,
    labels: Sequence[ReferenceLabel] | None = None,
    bars_by_run: Optional[dict[str, Sequence[Any]]] = None,
    dataset_meta: Optional[dict[str, Any]] = None,
    label_set_meta: Optional[dict[str, Any]] = None,
    baseline_run_id: Optional[str] = None,
    annotator: str = "",
) -> dict[str, Any]:
    t0 = time.perf_counter()
    labels = list(labels or [])
    bars_by_run = bars_by_run or {}
    groups_map: dict[tuple, list[dict[str, Any]]] = {}
    leftover: list[dict[str, Any]] = []

    for run in runs:
        key, why = _group_key(run, protocol)
        if key is None:
            leftover.append({"run": run, "reason_vi": why})
            continue
        groups_map.setdefault(key, []).append(run)

    groups_out: list[dict[str, Any]] = []
    for key, members in groups_map.items():
        scored = []
        for run in members:
            bid = run.get("run_id") or ""
            scored.append(
                score_one_run(
                    run,
                    protocol=protocol,
                    labels=labels,
                    bars=bars_by_run.get(bid) or run.get("bars") or [],
                    annotator=annotator,
                    label_set_meta=label_set_meta,
                )
            )
        tf = (members[0].get("timeframe") or "")
        sym = (members[0].get("symbol") or "")
        groups_out.append(
            {
                "group_key": "|".join(str(x) for x in key),
                "comparable": True,
                "timeframe": tf,
                "symbol": sym,
                "reason_vi": (
                    "Cùng dataset %s %s, khoảng chạy, khoảng chấm, bộ nhãn (nếu có) và protocol %s/%s. "
                    "Không so chéo khung: M5, M15, H1 là các không gian nến khác nhau."
                    % (sym or "?", tf or "?", protocol.version, protocol.matcher_version)
                ),
                "runs": scored,
            }
        )
    if leftover:
        groups_out.append(
            {
                "group_key": "incompatible",
                "comparable": False,
                "reason_vi": "Các run này không cùng nhóm so sánh.",
                "runs": [],
                "excluded": [
                    {
                        "run_id": (x["run"].get("run_id") or ""),
                        "reason_vi": x["reason_vi"],
                    }
                    for x in leftover
                ],
            }
        )

    all_scored = [r for g in groups_out if g.get("comparable") for r in g["runs"]]
    selected_id = None
    if baseline_run_id and any(r["run_id"] == baseline_run_id for r in all_scored):
        selected_id = baseline_run_id
    elif all_scored:
        selected_id = all_scored[0]["run_id"]

    if baseline_run_id:
        base = next((r for r in all_scored if r["run_id"] == baseline_run_id), None)
        if base:
            for g in groups_out:
                if not g.get("comparable"):
                    continue
                in_group = any(r["run_id"] == baseline_run_id for r in g["runs"])
                for r in g["runs"]:
                    r["delta_vs_baseline"] = (
                        _delta(r, base) if in_group and r["run_id"] != baseline_run_id else None
                    )
                    r["is_baseline"] = r["run_id"] == baseline_run_id

    n_labels_cov = len(_labels_in_coverage(labels, protocol))
    duration_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "protocol": protocol.to_dict(),
        "protocol_hash": protocol.fingerprint(),
        "protocol_version": protocol.version,
        "matcher_version": protocol.matcher_version,
        "target": protocol.target,
        "target_label_vi": target_label_vi(protocol.target),
        "dataset": dataset_meta or {},
        "label_set": label_set_meta,
        "annotator": (annotator or (label_set_meta or {}).get("annotator") or "").strip(),
        "coverage": {
            "start_index": protocol.coverage_start_index,
            "end_index": protocol.coverage_end_index,
            "n_labels_in_coverage": n_labels_cov,
            "note_vi": (
                "Chỉ sự kiện có nến sự kiện trong [start, end] mới bị tính FP. "
                "Ngoài khoảng được khai là gán đầy đủ sẽ bị bỏ, không phải false positive."
                if protocol.coverage_start_index is not None
                else (
                    "Chưa khai khoảng gán nhãn đầy đủ — mọi sự kiện trong lần chạy "
                    "được coi là trong phạm vi chấm."
                )
            ),
        },
        "groups": groups_out,
        "baseline_run_id": baseline_run_id,
        "selected_run_id": selected_id,
        "duration_ms": round(duration_ms, 3),
        "note_vi": (
            "Không xếp hạng «thuật toán tốt nhất». F1 và độ trễ là đánh đổi. "
            "Precision/recall chỉ khi có nhãn do người gán trong khoảng chấm."
        ),
    }


def score_one_run(
    run: dict[str, Any],
    *,
    protocol: EvalProtocol,
    labels: Sequence[ReferenceLabel],
    bars: Sequence[Any],
    annotator: str = "",
    label_set_meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    events = list(run.get("events") or [])
    mapped, ignored_type = _map_events(events, protocol)
    in_cov, ignored_cov = _events_in_coverage(mapped, protocol)
    scored, ignored_tail = _apply_tail_rule(in_cov, protocol)
    if protocol.max_lag_bars is not None:
        scored, ignored_lag = _filter_max_lag(scored, protocol.max_lag_bars)
    else:
        ignored_lag = []

    cov_labels = _labels_in_coverage(labels, protocol)
    wanted = set(protocol.label_types())
    cov_labels = [lb for lb in cov_labels if lb.structure_type in wanted]

    has_labels = bool(cov_labels)
    match = match_labels(
        cov_labels,
        scored,
        time_tolerance_bars=protocol.time_tolerance_bars,
        price_tolerance=protocol.price_tolerance,
        matcher_version=protocol.matcher_version,
    ) if has_labels else None

    tp = len(match.matches) if match else 0
    fn = len(match.unmatched_label_indices) if match else 0
    fp = len(match.unmatched_event_indices) if match else 0
    precision = ratio(tp, tp + fp) if has_labels else None
    recall = ratio(tp, tp + fn) if has_labels else None
    f1 = f1_score(precision, recall) if has_labels else None

    by_side = _by_side(cov_labels, scored, match) if match else {
        "high": _empty_side(),
        "low": _empty_side(),
    }

    quality_note = (
        "Chưa có nhãn tham chiếu trong khoảng chấm — không tính precision/recall/F1 "
        "(không hiện số 0)."
        if not has_labels
        else (
            "Ghép matcher %s, dung sai %d nến / %s đơn vị giá, người gán %s."
            % (
                protocol.matcher_version,
                protocol.time_tolerance_bars,
                protocol.price_tolerance,
                (annotator or (label_set_meta or {}).get("annotator") or "—"),
            )
        )
    )

    lags_all = [int(e.get("confirmation_lag_bars", 0)) for e in scored]
    tp_ids = {h.event_id for h in match.matches} if match else set()
    lags_tp = [
        int(e.get("confirmation_lag_bars", 0))
        for e in scored
        if _eid(e) in tp_ids
    ]

    atr_rows = _price_atr_rows(scored, bars, protocol.atr_period)
    gaps = _swing_gaps(scored)
    n_bars = _n_scorable_bars(run, protocol)
    n_swings = len(scored)
    validity = check_stored_event_invariants(
        events,
        warmup_bars=int(run.get("warmup_bars") or 0),
        bars_processed=int(run.get("bars_processed") or 0),
    )

    matches_out = []
    fps = []
    fns = []
    if match:
        for h in match.matches:
            e = scored[h.event_index]
            lb = cov_labels[h.label_index]
            matches_out.append(_hit_dict(h, e, lb))
        for j in match.unmatched_event_indices:
            fps.append(_event_brief(scored[j], role="fp"))
        for i in match.unmatched_label_indices:
            lb = cov_labels[i]
            fns.append(
                {
                    "role": "fn",
                    "label_seq": lb.seq,
                    "structure_type": lb.structure_type,
                    "bar_index": lb.bar_index,
                    "price": lb.price,
                    "side": _side(lb.structure_type),
                }
            )

    eval_ms = (time.perf_counter() - t0) * 1000.0
    return {
        "run_id": run.get("run_id") or "",
        "label": run.get("label") or "",
        "algorithm": run.get("algorithm") or "",
        "algorithm_version": run.get("algorithm_version") or "",
        "params": run.get("params") or {},
        "timeframe": run.get("timeframe") or "",
        "symbol": run.get("symbol") or "",
        "dataset_id": run.get("dataset_id") or "",
        "range_start": run.get("range_start"),
        "range_end": run.get("range_end"),
        "is_synthetic": bool(run.get("is_synthetic")),
        "bars_processed": run.get("bars_processed"),
        "warmup_bars": run.get("warmup_bars"),
        "is_baseline": False,
        "delta_vs_baseline": None,
        "event_type_map": dict(protocol.event_type_map),
        "quality": {
            "has_labels": has_labels,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "true_positives": tp if has_labels else None,
            "false_positives": fp if has_labels else None,
            "false_negatives": fn if has_labels else None,
            "n_labels": len(cov_labels),
            "n_events_scored": n_swings,
            "by_side": by_side,
            "note_vi": quality_note,
        },
        "lag": {
            "n": len(lags_all),
            "median": median(lags_all),
            "p90": percentile_nearest_rank(lags_all, 90),
            "min": min(lags_all) if lags_all else None,
            "max": max(lags_all) if lags_all else None,
            "n_tp": len(lags_tp),
            "median_tp": median(lags_tp),
            "p90_tp": percentile_nearest_rank(lags_tp, 90),
            "histogram": lag_histogram(lags_all),
            "values": lags_all,
            "note_vi": (
                "Độ trễ xác nhận của swing đang chấm, đơn vị nến khung %s "
                "(không đổi ra phút; 3 nến M5 ≠ 3 nến H1). Không gộp BOS. "
                "Median/P90 trên mọi sự kiện được đếm; kèm median/P90 trên TP khi có nhãn."
                % (run.get("timeframe") or "?")
            ),
        },
        "price_atr": _summarize_atr(atr_rows),
        "density": {
            "n_swings": n_swings,
            "n_scorable_bars": n_bars,
            "per_100": (100.0 * n_swings / n_bars) if n_bars else None,
            "median_gap_bars": median(gaps),
            "note_vi": "Chỉ đếm loại swing của mục tiêu, không kể HH/LH của cùng pivot.",
        },
        "validity": validity,
        "performance": {
            "algorithm_ms": run.get("duration_ms"),
            "evaluation_ms": round(eval_ms, 3),
        },
        "counts_ignored": {
            "unmapped_type": len(ignored_type),
            "outside_coverage": len(ignored_cov),
            "unconfirmed_tail": len(ignored_tail),
            "over_max_lag": len(ignored_lag),
        },
        "matches": matches_out,
        "false_positives": fps,
        "false_negatives": fns,
        "min_recall": protocol.min_recall,
        "recall_meets_floor": (
            None
            if protocol.min_recall is None or recall is None
            else recall >= protocol.min_recall
        ),
    }


def _group_key(run: dict[str, Any], protocol: EvalProtocol) -> tuple[Optional[tuple], str]:
    ds = run.get("dataset_id")
    if not ds:
        return None, "Thiếu dataset_id."
    return (
        (
            ds,
            run.get("range_start") or "",
            run.get("range_end") or "",
            protocol.fingerprint(),
        ),
        "",
    )


def _map_events(events: Sequence[Any], protocol: EvalProtocol) -> tuple[list[dict[str, Any]], list[Any]]:
    kept: list[dict[str, Any]] = []
    ignored: list[Any] = []
    mapping = protocol.event_type_map
    for e in events:
        src = _stype(e)
        if src not in mapping:
            ignored.append(e)
            continue
        d = dict(e) if isinstance(e, dict) else (
            e.to_dict() if hasattr(e, "to_dict") else {
            "event_id": _eid(e),
            "structure_type": src,
            "price": _price(e),
            "event_bar_index": _bar(e),
            "confirmed_bar_index": int(getattr(e, "confirmed_bar_index", _bar(e))),
            "confirmation_lag_bars": int(getattr(e, "confirmation_lag_bars", 0)),
            "event_time": str(getattr(e, "event_time", "")),
            "confirmed_at": str(getattr(e, "confirmed_at", "")),
            }
        )
        d["source_structure_type"] = src
        d["structure_type"] = mapping[src]
        kept.append(d)
    return kept, ignored


def _in_cov(index: int, protocol: EvalProtocol) -> bool:
    s, e = protocol.coverage_start_index, protocol.coverage_end_index
    if s is not None and index < s:
        return False
    if e is not None and index > e:
        return False
    return True


def _events_in_coverage(
    events: Sequence[dict[str, Any]], protocol: EvalProtocol
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept, ignored = [], []
    for e in events:
        if _in_cov(int(e["event_bar_index"]), protocol):
            kept.append(e)
        else:
            ignored.append(e)
    return kept, ignored


def _labels_in_coverage(
    labels: Sequence[ReferenceLabel], protocol: EvalProtocol
) -> list[ReferenceLabel]:
    return [lb for lb in labels if _in_cov(int(lb.bar_index), protocol)]


def _apply_tail_rule(
    events: Sequence[dict[str, Any]], protocol: EvalProtocol
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not protocol.exclude_unconfirmed_tail or protocol.coverage_end_index is None:
        return list(events), []
    end = protocol.coverage_end_index
    kept, ignored = [], []
    for e in events:
        if int(e.get("confirmed_bar_index", e["event_bar_index"])) > end:
            ignored.append(e)
        else:
            kept.append(e)
    return kept, ignored


def _filter_max_lag(
    events: Sequence[dict[str, Any]], max_lag: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    kept, ignored = [], []
    for e in events:
        if int(e.get("confirmation_lag_bars", 0)) > max_lag:
            ignored.append(e)
        else:
            kept.append(e)
    return kept, ignored


def _empty_side() -> dict[str, Any]:
    return {
        "true_positives": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "precision": None,
        "recall": None,
        "f1": None,
        "n_labels": 0,
        "n_events": 0,
    }


def _side(stype: str) -> str:
    if stype in high_types():
        return "high"
    if stype in low_types():
        return "low"
    return "other"


def _by_side(
    labels: Sequence[ReferenceLabel],
    events: Sequence[dict[str, Any]],
    match: Any,
) -> dict[str, Any]:
    out = {"high": _empty_side(), "low": _empty_side()}
    matched_e = {h.event_index for h in match.matches}
    matched_l = {h.label_index for h in match.matches}
    highs, lows = high_types(), low_types()
    for side in ("high", "low"):
        types = highs if side == "high" else lows
        n_lab = sum(1 for lb in labels if lb.structure_type in types)
        n_ev = sum(1 for e in events if e["structure_type"] in types)
        tp = sum(1 for h in match.matches if h.structure_type in types)
        fn = sum(
            1
            for i, lb in enumerate(labels)
            if i not in matched_l and lb.structure_type in types
        )
        fp = sum(
            1
            for j, e in enumerate(events)
            if j not in matched_e and e["structure_type"] in types
        )
        p = ratio(tp, tp + fp)
        r = ratio(tp, tp + fn)
        out[side] = {
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "precision": p,
            "recall": r,
            "f1": f1_score(p, r),
            "n_labels": n_lab,
            "n_events": n_ev,
        }
    return out


def _bar_ohlc(bar: Any) -> tuple[float, float, float]:
    if isinstance(bar, dict):
        return float(bar["high"]), float(bar["low"]), float(bar["close"])
    return float(bar.high), float(bar.low), float(bar.close)


def _bar_index(bar: Any, fallback: int) -> int:
    if isinstance(bar, dict):
        return int(bar.get("index", bar.get("idx", fallback)))
    return int(getattr(bar, "index", fallback))


def _price_atr_rows(
    events: Sequence[dict[str, Any]], bars: Sequence[Any], atr_period: int
) -> list[dict[str, Any]]:
    if not bars:
        return []
    atr = WilderATR(atr_period)
    by_index: dict[int, tuple[Optional[float], float]] = {}
    for i, bar in enumerate(bars):
        h, l, c = _bar_ohlc(bar)
        val = atr.update(h, l, c)
        by_index[_bar_index(bar, i)] = (val, c)
    rows = []
    for e in events:
        cf = int(e.get("confirmed_bar_index", e["event_bar_index"]))
        if cf not in by_index:
            continue
        atr_v, close_v = by_index[cf]
        dist = abs(close_v - float(e["price"]))
        ratio_v = None if atr_v is None or atr_v <= 0 else dist / atr_v
        rows.append(
            {
                "event_id": e.get("event_id"),
                "distance": dist,
                "atr": atr_v,
                "atr_ratio": ratio_v,
                "atr_valid": ratio_v is not None,
            }
        )
    return rows


def _summarize_atr(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    valid = [r for r in rows if r.get("atr_valid")]
    dists = [r["distance"] for r in valid]
    ratios = [r["atr_ratio"] for r in valid]
    return {
        "n": len(valid),
        "n_atr_invalid": sum(1 for r in rows if not r.get("atr_valid")),
        "median_distance": median(dists),
        "p90_distance": percentile_nearest_rank(dists, 90),
        "median_atr_ratio": median(ratios),
        "p90_atr_ratio": percentile_nearest_rank(ratios, 90),
        "formula_vi": (
            "|close(nến xác nhận) − giá pivot| / ATR Wilder tại nến xác nhận. "
            "ATR chưa seed thì mẫu bị loại, không gán 0."
        ),
        "note_vi": (
            "Chưa đủ nến để seed ATR."
            if rows and not valid
            else "Khoảng giá lúc xác nhận, chuẩn hoá ATR Wilder."
        ),
    }


def _swing_gaps(events: Sequence[dict[str, Any]]) -> list[int]:
    xs = sorted(int(e["event_bar_index"]) for e in events)
    return [xs[i] - xs[i - 1] for i in range(1, len(xs))]


def _n_scorable_bars(run: dict[str, Any], protocol: EvalProtocol) -> int:
    n = int(run.get("bars_processed") or 0)
    s = protocol.coverage_start_index if protocol.coverage_start_index is not None else 0
    e = protocol.coverage_end_index if protocol.coverage_end_index is not None else n - 1
    if n <= 0:
        return 0
    s = max(0, s)
    e = min(n - 1, e)
    warm = int(run.get("warmup_bars") or 0)
    s = max(s, max(0, warm - 1))
    return max(0, e - s + 1)


def _hit_dict(h: Any, event: dict[str, Any], label: ReferenceLabel) -> dict[str, Any]:
    return {
        "role": "tp",
        "label_seq": h.label_seq,
        "event_id": h.event_id,
        "structure_type": h.structure_type,
        "source_structure_type": event.get("source_structure_type"),
        "event_bar_index": int(event["event_bar_index"]),
        "confirmed_bar_index": int(event.get("confirmed_bar_index", event["event_bar_index"])),
        "price": float(event["price"]),
        "label_bar_index": label.bar_index,
        "label_price": label.price,
        "delta_bars": h.delta_bars,
        "delta_price": h.delta_price,
        "lag": int(event.get("confirmation_lag_bars", 0)),
        "side": _side(h.structure_type),
    }


def _event_brief(event: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "role": role,
        "event_id": event.get("event_id"),
        "structure_type": event.get("structure_type"),
        "source_structure_type": event.get("source_structure_type"),
        "event_bar_index": int(event["event_bar_index"]),
        "confirmed_bar_index": int(event.get("confirmed_bar_index", event["event_bar_index"])),
        "price": float(event["price"]),
        "lag": int(event.get("confirmation_lag_bars", 0)),
        "side": _side(str(event.get("structure_type") or "")),
    }


def _delta(cur: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    def sub(a: Optional[float], b: Optional[float]) -> Optional[float]:
        if a is None or b is None:
            return None
        return a - b

    cq, bq = cur["quality"], base["quality"]
    cl, bl = cur["lag"], base["lag"]
    return {
        "f1": sub(cq.get("f1"), bq.get("f1")),
        "precision": sub(cq.get("precision"), bq.get("precision")),
        "recall": sub(cq.get("recall"), bq.get("recall")),
        "lag_p90": sub(cl.get("p90"), bl.get("p90")),
        "lag_median": sub(cl.get("median"), bl.get("median")),
        "density_per_100": sub(cur["density"].get("per_100"), base["density"].get("per_100")),
        "atr_ratio_median": sub(
            cur["price_atr"].get("median_atr_ratio"),
            base["price_atr"].get("median_atr_ratio"),
        ),
    }
