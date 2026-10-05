"""Chuẩn ngẫu nhiên cho chất lượng nhận diện — «thuật toán có hơn đặt sự kiện ngẫu nhiên cùng mật
độ không?» (AGENTS.md §6.3; kien_truc_luong_ict.md §6 bước 1; plan_ict_structure.md §11.6).

Nhãn giữ nguyên, chỉ **sự kiện** bị thay bằng sự kiện ngẫu nhiên:

* cùng số lượng theo từng loại nguồn (``source_structure_type``) trong từng cửa sổ chấm;
* đặt trên nến **thật** của cửa sổ, sau warm-up — không rơi vào giờ nghỉ hay chỗ thiếu dữ liệu;
* giá theo đúng quy tắc giá của detector, suy từ sự kiện thật (high / low / close / open của nến
  sự kiện); loại nào không suy được (vd giá là một mức tính ra) → chuẩn ngẫu nhiên «không áp dụng»;
* chấm bằng chính matcher, dung sai và quy tắc của protocol.

Hai chế độ:

* ``uniform_v1`` — đồng đều trên các nến chấm được.
* ``matched_hour_atr_v1`` — «null ghép cặp»: mỗi sự kiện thật kéo một sự kiện ngẫu nhiên cùng **giờ
  New York** (giờ mở nến, có đổi giờ mùa hè) và cùng **nhóm ATR** (tam phân vị ATR Wilder trên các
  nến của cửa sổ). Nhãn và swing thật dồn vào giờ sôi động, biến động lớn; rải đồng đều sẽ đưa sự
  kiện ngẫu nhiên vào giờ vắng và làm thuật toán trông giỏi hơn thực tế → nên đọc chế độ này.
  Nhóm thiếu nến thì lấy bù cùng giờ, rồi bù đồng đều; số sự kiện phải bù được ghi lại.

Chỉ dùng khi ĐÁNH GIÁ (nhìn cả cửa sổ, kể cả phần «tương lai» của nó) — không bao giờ là đầu vào
của detector (AGENTS.md §2.1). Không có win rate / P&L.

Tất định: số ngẫu nhiên lấy từ sha256(seed|cửa sổ|loại|nhóm|lượt|bộ đếm) — không phụ thuộc phiên
bản Python, thứ tự run hay các run khác trong cùng lần đánh giá (các run có cùng số sự kiện dùng
cùng các lượt ngẫu nhiên → so sánh công bằng hơn).
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

NULL_OFF = "off"
NULL_UNIFORM = "uniform_v1"
NULL_MATCHED = "matched_hour_atr_v1"
NULL_MODES = (NULL_OFF, NULL_UNIFORM, NULL_MATCHED)
NULL_MODE_TEXT_VI = {
    NULL_UNIFORM: "đồng đều trên các nến chấm được",
    NULL_MATCHED: "ghép cặp: cùng giờ New York × cùng nhóm ATR",
}
NULL_N_MIN = 10
NULL_N_MAX = 1000
RNG_ID = "sha256_fisher_yates_v1"
# Giới hạn khối lượng: N × (số sự kiện + số nhãn trong các cửa sổ) của một run.
WORK_LIMIT = 3_000_000
PRICE_FIELDS = ("high", "low", "close", "open")
PRICE_RULE_MIN_SHARE = 0.95
NY_TZ = "America/New_York"


@dataclass
class NullWindow:
    """Một cửa sổ chấm. ``lo``/``hi``: chỉ số **dataset**, đã giao khoảng chấm, khoảng run và sau warm-up."""

    lo: int
    hi: int
    events: list = field(default_factory=list)   # sự kiện thật được chấm (dict đã ánh xạ, chỉ số dataset)
    labels: list = field(default_factory=list)   # ReferenceLabel trong cửa sổ, đúng loại của mục tiêu


class _HashRng:
    """Số nguyên ngẫu nhiên tất định: sha256(khoá|bộ đếm), lấy mẫu loại bỏ để không lệch."""

    def __init__(self, key: str) -> None:
        self._key = key.encode("utf-8")
        self._i = 0

    def below(self, n: int) -> int:
        if n <= 0:
            raise ValueError("below(n) cần n > 0")
        limit = (1 << 64) - ((1 << 64) % n)
        while True:
            self._i += 1
            digest = hashlib.sha256(self._key + b"|" + str(self._i).encode("ascii")).digest()
            x = int.from_bytes(digest[:8], "big")
            if x < limit:
                return x % n


def _sample(pool: Sequence[int], k: int, key: str) -> list[int]:
    """``k`` phần tử khác nhau của ``pool`` — Fisher–Yates thưa (không chép mảng)."""
    n = len(pool)
    k = min(k, n)
    if k <= 0:
        return []
    rng = _HashRng(key)
    swaps: dict[int, int] = {}
    out = []
    for i in range(k):
        j = i + rng.below(n - i)
        vi, vj = swaps.get(i, i), swaps.get(j, j)
        swaps[j] = vi
        out.append(pool[vj])
    return out


def _bar_fields(bar: Any) -> tuple[float, float, float, float]:
    if isinstance(bar, dict):
        return float(bar["open"]), float(bar["high"]), float(bar["low"]), float(bar["close"])
    return float(bar.open), float(bar.high), float(bar.low), float(bar.close)


def _bar_time(bar: Any) -> Optional[datetime]:
    t = bar.get("bar_time") if isinstance(bar, dict) else getattr(bar, "bar_time", None)
    if t is None:
        return None
    if not isinstance(t, datetime):
        t = datetime.fromisoformat(str(t).replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t


def _bar_index(bar: Any, fallback: int) -> int:
    if isinstance(bar, dict):
        return int(bar.get("index", bar.get("idx", fallback)))
    return int(getattr(bar, "index", fallback))


def infer_price_rules(events: Sequence[dict[str, Any]], ohlc: dict[int, tuple]) -> dict[str, Optional[str]]:
    """Mỗi loại nguồn → trường giá (high/low/close/open) mà giá sự kiện thật trùng ≥ 95% số lần."""
    by_type: dict[str, list[dict[str, Any]]] = {}
    for e in events:
        by_type.setdefault(str(e.get("source_structure_type") or e["structure_type"]), []).append(e)
    rules: dict[str, Optional[str]] = {}
    for src, evs in sorted(by_type.items()):
        counts = dict.fromkeys(PRICE_FIELDS, 0)
        n = 0
        for e in evs:
            row = ohlc.get(int(e["event_bar_index"]))
            if row is None:
                continue
            n += 1
            price = float(e["price"])
            o, h, lo_, c = row
            for name, v in zip(("open", "high", "low", "close"), (o, h, lo_, c)):
                if abs(price - v) <= 1e-9 * max(1.0, abs(v)):
                    counts[name] += 1
        rule = None
        if n:
            for name in PRICE_FIELDS:
                if counts[name] / n >= PRICE_RULE_MIN_SHARE:
                    rule = name
                    break
        rules[src] = rule
    return rules


def _price_of(row: tuple, rule: str) -> float:
    o, h, lo_, c = row
    return {"open": o, "high": h, "low": lo_, "close": c}[rule]


def _summ(values: Sequence[float]) -> dict[str, Optional[float]]:
    from core.eval.metrics import percentile_nearest_rank

    xs = [float(v) for v in values]
    if not xs:
        return {"mean": None, "sd": None, "p5": None, "p50": None, "p95": None}
    mean = sum(xs) / len(xs)
    sd = math.sqrt(sum((x - mean) ** 2 for x in xs) / (len(xs) - 1)) if len(xs) > 1 else 0.0
    return {
        "mean": mean,
        "sd": sd,
        "p5": percentile_nearest_rank(xs, 5),
        "p50": percentile_nearest_rank(xs, 50),
        "p95": percentile_nearest_rank(xs, 95),
    }


def _se(p: Optional[float], n: int) -> Optional[float]:
    if p is None or n <= 0:
        return None
    return math.sqrt(max(0.0, p * (1.0 - p)) / n)


def _count_tp(labels: Sequence[Any], events: Sequence[dict[str, Any]], protocol: Any) -> int:
    """Số TP khi ghép ``events`` với ``labels`` bằng matcher của protocol.

    Tách theo loại rồi theo cụm nến (hai phần tử liền nhau cách > dung sai thời gian → cụm mới).
    Không có cặp hợp lệ nào nối hai cụm, thứ tự tương đối được giữ → số TP **bằng đúng** khi gọi
    matcher trên toàn bộ, nhưng tránh dựng O(nhãn × sự kiện) cặp mỗi lượt.
    """
    from core.eval.matcher import match_labels, pair_cost

    tol = int(protocol.time_tolerance_bars)
    by_type_l: dict[str, list[tuple[int, Any]]] = {}
    for i, lb in enumerate(labels):
        by_type_l.setdefault(lb.structure_type, []).append((i, lb))
    by_type_e: dict[str, list[tuple[int, dict[str, Any]]]] = {}
    for j, e in enumerate(events):
        by_type_e.setdefault(e["structure_type"], []).append((j, e))
    total = 0
    for stype, evs in by_type_e.items():
        labs = by_type_l.get(stype)
        if not labs:
            continue
        items = sorted(
            [(int(lb.bar_index), 0, i) for i, lb in labs] + [(int(e["event_bar_index"]), 1, j) for j, e in evs]
        )
        lab_of = dict(labs)
        ev_of = dict(evs)
        comp: list[tuple[int, int, int]] = []
        prev = None

        def flush(part: list[tuple[int, int, int]]) -> int:
            ls = [lab_of[i] for _b, kind, i in sorted(part, key=lambda x: x[2]) if kind == 0]
            es = [ev_of[j] for _b, kind, j in sorted(part, key=lambda x: x[2]) if kind == 1]
            if not ls or not es:
                return 0
            if len(ls) == 1 and len(es) == 1:
                ok = pair_cost(ls[0], es[0], time_tolerance_bars=tol, price_tolerance=protocol.price_tolerance)
                return 1 if ok is not None else 0
            return len(match_labels(
                ls, es, time_tolerance_bars=tol, price_tolerance=protocol.price_tolerance,
                matcher_version=protocol.matcher_version,
            ).matches)

        for it in items:
            if prev is not None and it[0] - prev > tol:
                total += flush(comp)
                comp = []
            comp.append(it)
            prev = it[0]
        if comp:
            total += flush(comp)
    return total


def _ny_hour(t: Optional[datetime]) -> Optional[int]:
    if t is None:
        return None
    from zoneinfo import ZoneInfo

    return t.astimezone(ZoneInfo(NY_TZ)).hour


def null_baseline(
    windows: Sequence[NullWindow],
    *,
    bars: Sequence[Any],
    offset: int,
    protocol: Any,
    rule_events: Sequence[dict[str, Any]],
    real: dict[str, Any],
) -> dict[str, Any]:
    """Phân phối P/R/F1 của ``protocol.null_n`` lượt sự kiện ngẫu nhiên, gộp qua các cửa sổ, và vị trí
    của run thật trong phân phối đó. ``real`` = {tp, fp, fn, precision, recall, f1} của run thật."""
    mode = protocol.null_mode
    n_rep = int(protocol.null_n)
    seed = int(protocol.null_seed)
    base = {
        "mode": mode,
        "mode_vi": NULL_MODE_TEXT_VI.get(mode, mode),
        "n": n_rep,
        "seed": seed,
        "rng": RNG_ID,
    }
    n_labels = sum(len(w.labels) for w in windows)
    n_events = sum(len(w.events) for w in windows)
    if not n_labels:
        return dict(base, status="chua_co_nhan",
                    note_vi="Chưa có nhãn trong cửa sổ chấm — không có chuẩn ngẫu nhiên (không hiện số 0).")
    work = n_rep * (n_labels + n_events)
    if work > WORK_LIMIT:
        raise ValueError(
            "Chuẩn ngẫu nhiên quá nặng: %d lượt × %d (nhãn + sự kiện) = %d > %d. "
            "Giảm số lượt hoặc thu hẹp khoảng chấm / các đoạn." % (n_rep, n_labels + n_events, work, WORK_LIMIT)
        )

    ohlc: dict[int, tuple] = {}
    times: dict[int, Optional[datetime]] = {}
    for i, bar in enumerate(bars):
        idx = _bar_index(bar, i) + offset
        ohlc[idx] = _bar_fields(bar)
        times[idx] = _bar_time(bar)

    needed_types = sorted({str(e.get("source_structure_type") or e["structure_type"]) for w in windows for e in w.events})
    rules = infer_price_rules(rule_events, ohlc)
    missing = [t for t in needed_types if not rules.get(t)]
    if missing:
        return dict(base, status="khong_ap_dung", price_rule={t: rules.get(t) for t in needed_types},
                    note_vi=(
                        "Không áp dụng: giá sự kiện loại %s không trùng high/low/close/open của nến sự kiện "
                        "(≥ %d%% số lần) — chưa biết đặt giá cho sự kiện ngẫu nhiên." % (
                            ", ".join(missing), int(PRICE_RULE_MIN_SHARE * 100))
                    ))

    atr_of: dict[int, Optional[float]] = {}
    if mode == NULL_MATCHED:
        from core.indicators import WilderATR

        atr = WilderATR(int(protocol.atr_period))
        for i, bar in enumerate(bars):
            _o, h, lo_, c = _bar_fields(bar)
            atr_of[_bar_index(bar, i) + offset] = atr.update(h, lo_, c)

    # --- chuẩn bị từng cửa sổ: nến đủ điều kiện, nhóm, số sự kiện cần đặt theo loại × nhóm
    plans = []
    eligible_total = 0
    fallback_events = 0
    strata_used: set[Any] = set()
    for wi, w in enumerate(windows):
        eligible = [i for i in range(w.lo, w.hi + 1) if i in ohlc]
        eligible_total += len(eligible)
        mapped_of: dict[str, str] = {}
        need: dict[str, dict[Any, int]] = {}
        stratum_of: dict[int, Any] = {}
        hour_pool: dict[Any, list[int]] = {}
        if mode == NULL_MATCHED:
            from core.eval.metrics import percentile_nearest_rank

            vals = [atr_of[i] for i in eligible if atr_of.get(i) is not None]
            q1 = percentile_nearest_rank(vals, 100.0 / 3.0) if vals else None
            q2 = percentile_nearest_rank(vals, 200.0 / 3.0) if vals else None

            def stratum(i: int) -> Any:
                a = atr_of.get(i)
                bucket = "na" if a is None or q1 is None else (0 if a <= q1 else (1 if a <= q2 else 2))
                return (_ny_hour(times.get(i)), bucket)

            for i in eligible:
                stratum_of[i] = stratum(i)
                hour_pool.setdefault(stratum_of[i][0], []).append(i)
        for e in w.events:
            src = str(e.get("source_structure_type") or e["structure_type"])
            mapped_of[src] = e["structure_type"]
            b = int(e["event_bar_index"])
            if mode == NULL_MATCHED:
                key = stratum_of.get(b)
                if key is None and b in ohlc:
                    key = stratum(b)
                key = key if key is not None else ("*", "*")
            else:
                key = "u"
            need.setdefault(src, {})
            need[src][key] = need[src].get(key, 0) + 1
        pools: dict[Any, list[int]] = {}
        if mode == NULL_MATCHED:
            for i in eligible:
                pools.setdefault(stratum_of[i], []).append(i)
        plans.append((wi, w, eligible, mapped_of, need, pools, hour_pool))

    def draw(wi: int, src: str, need_src: dict[Any, int], eligible: list[int], pools: dict, hour_pool: dict,
             rep: int, count_fallback: bool) -> list[int]:
        nonlocal fallback_events
        tag = "%d|%d-%d|%s" % (seed, windows[wi].lo, windows[wi].hi, src)
        if mode != NULL_MATCHED:
            return _sample(eligible, need_src.get("u", 0), "%s|u|%d" % (tag, rep))
        chosen: list[int] = []
        used: set[int] = set()
        short_by_hour: dict[Any, int] = {}
        for key in sorted(need_src, key=lambda k: (str(k[0]), str(k[1]))):
            k = need_src[key]
            pool = pools.get(key, [])
            got = _sample(pool, k, "%s|%s|%d" % (tag, key, rep))
            chosen += got
            used.update(got)
            if count_fallback:
                strata_used.add(key)
            if k > len(got):
                short_by_hour[key[0]] = short_by_hour.get(key[0], 0) + (k - len(got))
        rest = 0
        for hour in sorted(short_by_hour, key=str):
            k = short_by_hour[hour]
            pool = [i for i in hour_pool.get(hour, []) if i not in used]
            got = _sample(pool, k, "%s|h%s|%d" % (tag, hour, rep))
            chosen += got
            used.update(got)
            rest += k - len(got)
            if count_fallback:
                fallback_events += len(got)
        if rest:
            pool = [i for i in eligible if i not in used]
            got = _sample(pool, rest, "%s|all|%d" % (tag, rep))
            chosen += got
            if count_fallback:
                fallback_events += len(got)
        return chosen

    f1s: list[float] = []
    precs: list[float] = []
    recs: list[float] = []
    for rep in range(n_rep):
        tp = n_ev = 0
        for wi, w, eligible, mapped_of, need, pools, hour_pool in plans:
            rnd: list[dict[str, Any]] = []
            for src in sorted(need):
                rule = rules[src]
                for b in draw(wi, src, need[src], eligible, pools, hour_pool, rep, rep == 0):
                    rnd.append({
                        "event_id": "rnd:%d:%s:%d" % (rep, src, b),
                        "structure_type": mapped_of[src],
                        "source_structure_type": src,
                        "event_bar_index": b,
                        "price": _price_of(ohlc[b], rule),
                    })
            rnd.sort(key=lambda x: (x["event_bar_index"], x["source_structure_type"]))
            n_ev += len(rnd)
            tp += _count_tp(w.labels, rnd, protocol)
        fp, fn = n_ev - tp, n_labels - tp
        den = 2 * tp + fp + fn
        f1s.append((2.0 * tp / den) if den else 0.0)
        recs.append(tp / n_labels)
        if n_ev:
            precs.append(tp / n_ev)

    real_f1 = real.get("f1")
    real_cmp = float(real_f1) if real_f1 is not None else 0.0
    eps = 1e-12
    n_lt = sum(1 for x in f1s if x < real_cmp - eps)
    n_eq = sum(1 for x in f1s if abs(x - real_cmp) <= eps)
    n_ge = n_rep - n_lt                      # ngẫu nhiên ≥ thực tế (kể cả bằng)
    f1_summary = _summ(f1s)
    tp_r, fp_r, fn_r = int(real.get("tp") or 0), int(real.get("fp") or 0), int(real.get("fn") or 0)
    out = dict(base)
    out.update(
        status="ok",
        n_windows=len(windows),
        eligible_bars=eligible_total,
        n_events=n_events,
        n_labels=n_labels,
        price_rule={t: rules[t] for t in needed_types},
        precision=_summ(precs),
        recall=_summ(recs),
        f1=f1_summary,
        real={
            "precision": real.get("precision"),
            "recall": real.get("recall"),
            "f1": real_f1,
            "precision_se": _se(real.get("precision"), tp_r + fp_r),
            "recall_se": _se(real.get("recall"), tp_r + fn_r),
        },
        f1_minus_mean=(real_cmp - f1_summary["mean"]) if f1_summary["mean"] is not None else None,
        n_ge_real=n_ge,
        p_ge=(1 + n_ge) / (n_rep + 1),
        percentile=100.0 * (n_lt + 0.5 * n_eq) / n_rep,
        note_vi=(
            "%d lượt sự kiện ngẫu nhiên (%s), cùng số lượng theo loại trong từng cửa sổ, giá theo quy tắc "
            "của detector, chấm bằng cùng matcher. %d/%d lượt có F1 ≥ thực tế. Sai số chuẩn của P/R thực "
            "tế là xấp xỉ lạc quan (swing không độc lập). Chỉ để đánh giá — không phải tín hiệu."
            % (n_rep, NULL_MODE_TEXT_VI.get(mode, mode), n_ge, n_rep)
        ),
    )
    if mode == NULL_MATCHED:
        out["strata"] = {"n_strata": len(strata_used), "fallback_events": fallback_events}
    return out
