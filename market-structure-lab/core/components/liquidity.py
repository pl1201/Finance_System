"""[S3] Vùng thanh khoản và [E2] vòng đời: chạm → lấy → sweep / run / chưa rõ (plan_ict_structure §4.6).

* Vùng: BSL (phía trên, từ đỉnh) và SSL (phía dưới, từ đáy) theo tầng: ITH/ITL của khung chạy
  (``M15``), ITH/ITL khung lớn (``H1``, ``H4``) và mức theo kỳ (``D`` = PDH/PDL, ``W`` = PWH/PWL — giai
  đoạn 3). Hai đỉnh (đáy) liên tiếp cùng tầng chênh ≤ ``eq_tol_atr × ATR`` → một vùng gộp (EQH/EQL), mức
  là cực trị của hai (người gọi không đưa ATR → không gộp).
* Hiệu lực từ nến sau nến làm vùng được biết. Đã bị xuyên ≥ ngưỡng trong khoảng từ cực trị tới lúc
  biết → **không tạo** (đã bị lấy trước khi biết).
* Vùng còn nguyên ở nến t (BSL; SSL đối xứng):
  * **chạm**: ``0 < high[t] − mức < min_pen_atr × ATR[t−1]`` → vẫn còn nguyên, ``touch_count`` +1;
  * **lấy** tại nến b đầu tiên có ``high[b] − mức ≥ min_pen_atr × ATR[b−1]``; ATR khoá = ATR[b−1].
    Định nghĩa duy nhất của «đã lấy»; vùng không bao giờ quay lại còn nguyên. ATR chưa có → chưa xét.
* Sau khi lấy, cửa sổ W (``sweep_window``, tính cả nến lấy):
  * **sweep** tại r = nến đầu tiên trong [b, b+W] có ``close[r] < mức``, không có khoảng trống trong
    (b, r]; ``sweep_bars = r − b``;
  * **run** tại b+W nếu hết cửa sổ mà không quay lại;
  * **chưa rõ** nếu gặp khoảng trống (mọi loại) trước khi rõ — tại nến đầu tiên sau khoảng trống;
  * hết dữ liệu khi đang chờ → vẫn chờ (không phát gì).

Vùng còn nguyên nằm trong heap theo mức, **mỗi (phía, tầng) một heap** → chỉ xét vùng giá đã chạm tới;
vùng gộp (mức đổi) dùng xoá lười theo ``version``. Chỉ có một tầng thì hành vi y như một heap chung.
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any, Optional

from core.types import Bar

TIER_RANK = {"M15": 1, "H1": 2, "H4": 3, "D": 4, "W": 5}
_TIER_KEYS = ("tao", "gop_eq", "khong_tao_da_bi_lay", "lay", "sweep", "run", "chua_ro")


@dataclass
class Pool:
    seq: int
    side: str                     # "high" = BSL (phía trên) | "low" = SSL (phía dưới)
    level: float
    tier: str
    known_index: int
    extreme_index: int
    sources: list[str] = field(default_factory=list)
    state: str = "intact"         # intact | taken | swept | run | unresolved
    touch_count: int = 0
    taken_index: Optional[int] = None
    atr_locked: Optional[float] = None
    pen: Optional[float] = None
    extreme: Optional[float] = None   # cực trị cú quét X = max(high[b..r]) / min(low[b..r])
    resolved_index: Optional[int] = None
    gap_kind: Optional[str] = None
    version: int = 0

    def brief(self) -> dict[str, Any]:
        return {
            "id": "%s%d" % ("B" if self.side == "high" else "S", self.seq),
            "phia": "BSL" if self.side == "high" else "SSL",
            "muc": self.level,
            "tang": self.tier,
            "nguon": list(self.sources),
            "biet_tai_nen": self.known_index,
            "so_lan_cham": self.touch_count,
            "nen_lay": self.taken_index,
            "atr_khoa": self.atr_locked,
            "xuyen": self.pen,
            "xuyen_atr": (self.pen / self.atr_locked) if self.pen is not None and self.atr_locked else None,
            "cuc_tri_cu_quet": self.extreme,
        }


class LiquidityBook:
    def __init__(self, min_pen_atr: float, sweep_window: int, eq_tol_atr: float) -> None:
        if min_pen_atr < 0 or sweep_window < 0 or eq_tol_atr < 0:
            raise ValueError("min_pen_atr, sweep_window, eq_tol_atr phải >= 0")
        self.min_pen_atr = min_pen_atr
        self.window = sweep_window
        self.eq_tol_atr = eq_tol_atr
        self.reset()

    def reset(self) -> None:
        self._seq = 0
        # (phía, tầng) → heap: BSL (mức, seq, version, pool), SSL (−mức, seq, version, pool)
        self._heaps: dict[tuple[str, str], list[tuple]] = {}
        self._order: dict[str, list[tuple[str, str]]] = {"high": [], "low": []}   # khoá heap theo hạng tầng
        self._scan: list[tuple[str, list[tuple]]] = []    # (phía, heap): BSL rồi SSL, mỗi phía theo hạng tầng
        self._pending: list[Pool] = []
        self._last: dict[tuple[str, str], Pool] = {}
        self.counts = {"tao": 0, "gop_eq": 0, "khong_tao_da_bi_lay": 0, "lay": 0, "lay_sau_khi_cham": 0,
                       "sweep": 0, "sweep_cung_nen": 0, "run": 0, "chua_ro": 0}
        self.tier_counts: dict[str, dict[str, int]] = {}
        self.pen_atr: list[float] = []
        #: tăng mỗi khi tập vùng còn nguyên đổi (thêm, gộp, bị lấy) — khoá cache «vùng gần nhất»
        self.rev = 0
        self._near_cache: dict[Optional[str], dict[str, Optional[Pool]]] = {}
        self._near_rev = -1

    def _tc(self, tier: str, key: str) -> None:
        c = self.tier_counts.get(tier)
        if c is None:
            c = self.tier_counts[tier] = dict.fromkeys(_TIER_KEYS, 0)
        c[key] += 1

    def _heap(self, side: str, tier: str) -> list[tuple]:
        key = (side, tier)
        h = self._heaps.get(key)
        if h is None:
            h = self._heaps[key] = []
            self._order[side].append(key)
            self._order[side].sort(key=lambda k: (TIER_RANK.get(k[1], 0), k[1]))
            self._scan = [(sd, self._heaps[k]) for sd in ("high", "low") for k in self._order[sd]]
        return h

    def _push(self, p: Pool) -> None:
        h = self._heap(p.side, p.tier)
        if p.side == "high":
            heapq.heappush(h, (p.level, p.seq, p.version, p))
        else:
            heapq.heappush(h, (-p.level, p.seq, p.version, p))

    def add(self, side: str, level: float, tier: str, source_id: str, known_index: int,
            extreme_index: int, atr: Optional[float], already_taken: bool) -> tuple[str, Optional[Pool]]:
        """Vùng mới biết tại ``known_index`` (hiệu lực từ nến sau). Trả ("created"|"merged"|"not_created", pool)."""
        if already_taken:
            self.counts["khong_tao_da_bi_lay"] += 1
            self._tc(tier, "khong_tao_da_bi_lay")
            self._last.pop((side, tier), None)   # gộp EQ chỉ giữa hai swing LIÊN TIẾP
            return "not_created", None
        last = self._last.get((side, tier))
        if (last is not None and last.state == "intact" and atr is not None
                and abs(level - last.level) <= self.eq_tol_atr * atr):
            last.level = max(last.level, level) if side == "high" else min(last.level, level)
            last.sources.append(source_id)
            last.version += 1
            self.rev += 1
            self._push(last)
            self.counts["gop_eq"] += 1
            self._tc(tier, "gop_eq")
            return "merged", last
        p = Pool(self._seq, side, level, tier, known_index, extreme_index, [source_id])
        self._seq += 1
        self.rev += 1
        self._push(p)
        self._last[(side, tier)] = p
        self.counts["tao"] += 1
        self._tc(tier, "tao")
        return "created", p

    def on_bar(self, bar: Bar, atr_prev: Optional[float], gap: Optional[dict[str, Any]]) -> dict[str, list]:
        """Nến t: vùng đang chờ trước, rồi vùng còn nguyên (đã biết trước t)."""
        t = bar.index
        resolved: list[tuple[str, Pool]] = []
        taken: list[Pool] = []
        touched: list[Pool] = []
        still: list[Pool] = []
        for p in self._pending:
            if gap is not None:
                self._resolve(p, "unresolved", t, resolved)
                p.gap_kind = gap.get("loai")
                continue
            if p.side == "high":
                p.extreme = max(p.extreme, bar.high)
                back = bar.close < p.level
            else:
                p.extreme = min(p.extreme, bar.low)
                back = bar.close > p.level
            if back:
                self._resolve(p, "sweep", t, resolved)
            elif t - p.taken_index >= self.window:
                self._resolve(p, "run", t, resolved)
            else:
                still.append(p)
        self._pending = still

        for side, heap in self._scan:
            keep: list[Pool] = []
            while heap:
                key, _seq, ver, p = heap[0]
                level = key if side == "high" else -key
                pen = (bar.high - level) if side == "high" else (level - bar.low)
                if pen <= 0:
                    break                        # heap theo mức: các vùng còn lại chưa bị chạm
                heapq.heappop(heap)
                if ver != p.version or p.state != "intact":
                    continue                     # bản ghi cũ (vùng đã gộp / đã lấy)
                if atr_prev is None:
                    keep.append(p)
                    continue
                if pen >= self.min_pen_atr * atr_prev:
                    p.state = "taken"
                    self.rev += 1
                    p.taken_index = t
                    p.atr_locked = atr_prev
                    p.pen = pen
                    p.extreme = bar.high if side == "high" else bar.low
                    self.counts["lay"] += 1
                    self._tc(p.tier, "lay")
                    if p.touch_count:
                        self.counts["lay_sau_khi_cham"] += 1
                    self.pen_atr.append(pen / atr_prev)
                    taken.append(p)
                    back = bar.close < p.level if side == "high" else bar.close > p.level
                    if back:
                        self._resolve(p, "sweep", t, resolved)
                    elif self.window == 0:
                        self._resolve(p, "run", t, resolved)
                    else:
                        self._pending.append(p)
                else:
                    p.touch_count += 1
                    touched.append(p)
                    keep.append(p)
            for p in keep:
                self._push(p)
        return {"resolved": resolved, "taken": taken, "touched": touched}

    def _resolve(self, p: Pool, kind: str, t: int, out: list) -> None:
        p.state = {"sweep": "swept", "run": "run", "unresolved": "unresolved"}[kind]
        p.resolved_index = t
        self.counts["chua_ro" if kind == "unresolved" else kind] += 1
        self._tc(p.tier, "chua_ro" if kind == "unresolved" else kind)
        if kind == "sweep" and t == p.taken_index:
            self.counts["sweep_cung_nen"] += 1
        out.append((kind, p))

    def _top(self, heap: list) -> Optional[Pool]:
        while heap:
            _k, _s, ver, p = heap[0]
            if ver == p.version and p.state == "intact":
                return p
            heapq.heappop(heap)
        return None

    def _nearest_side(self, side: str, tier: Optional[str]) -> Optional[Pool]:
        best: Optional[Pool] = None
        best_key: Optional[tuple] = None
        for key in self._order[side]:
            if tier is not None and key[1] != tier:
                continue
            p = self._top(self._heaps[key])
            if p is None:
                continue
            k = (p.level if side == "high" else -p.level, p.seq)
            if best_key is None or k < best_key:
                best, best_key = p, k
        return best

    def nearest(self, tier: Optional[str] = None) -> dict[str, Optional[Pool]]:
        """Vùng còn nguyên gần nhất: BSL mức thấp nhất, SSL mức cao nhất (mọi tầng, hoặc chỉ ``tier``).

        Kết quả được nhớ tới khi tập vùng còn nguyên đổi (``rev``); người gọi chỉ đọc, không sửa."""
        if self._near_rev != self.rev:
            self._near_cache = {}
            self._near_rev = self.rev
        r = self._near_cache.get(tier)
        if r is None:
            r = self._near_cache[tier] = {"high": self._nearest_side("high", tier),
                                          "low": self._nearest_side("low", tier)}
        return r

    def nearest_beyond(self, side: str, price: float, min_rank: int) -> Optional[Pool]:
        """Vùng còn nguyên gần ``price`` nhất nằm hẳn phía ``side`` (BSL: mức > price; SSL: mức < price), tầng
        có hạng ≥ ``min_rank`` (``TIER_RANK``). Bằng khoảng cách → tầng cao hơn, rồi vùng tạo trước."""
        best: Optional[Pool] = None
        best_key: Optional[tuple] = None
        for key in self._order[side]:
            if TIER_RANK.get(key[1], 0) < min_rank:
                continue
            heap = self._heaps[key]
            held: list[tuple] = []
            found: Optional[Pool] = None
            while heap:
                _k, _s, ver, p = heap[0]
                if ver != p.version or p.state != "intact":
                    heapq.heappop(heap)              # bản ghi cũ — xoá lười
                    continue
                if (p.level > price) if side == "high" else (p.level < price):
                    found = p
                    break
                held.append(heapq.heappop(heap))     # còn nguyên nhưng chưa nằm hẳn phía side (đã bị chạm nông)
            for item in held:
                heapq.heappush(heap, item)
            if found is None:
                continue
            k = (abs(found.level - price), -TIER_RANK.get(found.tier, 0), found.seq)
            if best_key is None or k < best_key:
                best, best_key = found, k
        return best

    def pending(self) -> list[Pool]:
        return list(self._pending)

    def intact_count(self) -> dict[str, int]:
        def n(side: str) -> int:
            return sum(1 for key in self._order[side] for _k, _s, ver, p in self._heaps[key]
                       if ver == p.version and p.state == "intact")
        return {"BSL": n("high"), "SSL": n("low")}

    def intact_by_tier(self) -> dict[str, dict[str, int]]:
        """Số vùng còn nguyên theo tầng và phía (quét toàn heap — chỉ dùng cho thống kê / trạng thái replay)."""
        out: dict[str, dict[str, int]] = {}
        for side in ("high", "low"):
            for key in self._order[side]:
                c = sum(1 for _k, _s, ver, p in self._heaps[key] if ver == p.version and p.state == "intact")
                out.setdefault(key[1], {"BSL": 0, "SSL": 0})["BSL" if side == "high" else "SSL"] = c
        return out
