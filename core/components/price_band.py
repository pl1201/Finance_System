"""[N] Khoảng giá 80% / 50% và xác suất chạm mức (thuat_toan_nhan_dien.md §4, §6) — ``ict_structure`` 0.6.0.

Mỗi tầm h (số nến), sau nến t:

* **Mẫu** của nến s = t − h hoàn tất: u = (max high (s, t] − C_s) / ATR_s, d = (C_s − min low (s, t]) / ATR_s. Mẫu vào
  nhóm giờ New York của s (cửa sổ trượt ``max_samples`` mẫu) và vào mẫu chung (4 × ``max_samples``). Bỏ khi (s, t] có
  khoảng trống dài (thuật toán báo, > 3 giờ) hoặc ATR_s chưa có.
* **Chấm** dự báo đã đưa ở nến s bằng đúng kết cục đó (§6 của đặc tả).
* **Khoảng** tại t: phân vị ``q80`` / ``q50`` mỗi phía của mẫu giờ NY của t (hoặc mẫu chung khi giờ còn < ``min_samples``)
  → khoảng [C_t − qd·ATR_t, C_t + qu·ATR_t]; xác suất chạm mức P = tỷ lệ mẫu có biên ≥ |P − C_t| / ATR_t.

Khoảng ở t chỉ dùng mẫu có s + h ≤ t: không mẫu nào nhìn quá nến đang xử lý. Giao diện hiện điểm thật kèm khoảng
(đặc tả §1), nên đây là dự báo khoảng theo AGENTS §2.4.
"""
from __future__ import annotations

import bisect
from collections import defaultdict, deque
from typing import Any, Optional

from core.indicators import RollingHighLow
from core.types import Bar

POOLED_FACTOR = 4
HIT_BINS = 10


def quantile(xs: list[float], q: float) -> float:
    """Phân vị nội suy tuyến tính trên danh sách đã sắp, vị trí (n − 1)·q."""
    pos = (len(xs) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def _ratio(a: float, n: int) -> Optional[float]:
    return a / n if n else None


class _Window:
    """Cửa sổ trượt cỡ ``cap`` giữ bản đã sắp (phân vị, tỷ lệ ≥ x trong O(log n))."""

    __slots__ = ("cap", "fifo", "xs")

    def __init__(self, cap: int) -> None:
        self.cap = cap
        self.fifo: deque[float] = deque()
        self.xs: list[float] = []

    def add(self, x: float) -> None:
        self.fifo.append(x)
        bisect.insort(self.xs, x)
        if len(self.fifo) > self.cap:
            del self.xs[bisect.bisect_left(self.xs, self.fifo.popleft())]

    def __len__(self) -> int:
        return len(self.xs)

    def at_least(self, x: float) -> float:
        return (len(self.xs) - bisect.bisect_left(self.xs, x)) / len(self.xs)


class _Pair:
    """Mẫu biên lên (u) và biên xuống (d) của một nhóm."""

    __slots__ = ("u", "d")

    def __init__(self, cap: int) -> None:
        self.u, self.d = _Window(cap), _Window(cap)

    def add(self, u: float, d: float) -> None:
        self.u.add(u)
        self.d.add(d)


def _touch_row() -> dict[str, Any]:
    return {"n": 0, "cham": 0, "brier": 0.0, "brier0": 0.0, "nhom": [[0, 0.0, 0] for _ in range(HIT_BINS)]}


class _Score:
    """Điểm thật của một tầm: khoảng (độ phủ, độ rộng, pinball so với B0, theo giờ) và xác suất chạm theo loại mức."""

    __slots__ = ("n", "cov80", "cov50", "w80", "w50", "loss", "loss0", "by_hour", "touch")

    def __init__(self) -> None:
        self.n = 0
        self.cov80 = self.cov50 = 0
        self.w80 = self.w50 = 0.0
        self.loss = self.loss0 = 0.0
        self.by_hour = [[0, 0] for _ in range(24)]
        self.touch: dict[str, dict[str, Any]] = defaultdict(_touch_row)


def _pinball(q: float, y: float, qhat: float) -> float:
    return (q - (1.0 if y < qhat else 0.0)) * (y - qhat)


class PriceBand:
    def __init__(self, horizons: dict[str, int], q80: float = 0.905, q50: float = 0.745, max_samples: int = 600,
                 min_samples: int = 60) -> None:
        if not 0.5 <= q50 < q80 < 1.0:
            raise ValueError("Nhận diện: phân vị khoảng 50%% (%s) phải nhỏ hơn của khoảng 80%% (%s), cả hai trong "
                             "[0,5; 1)." % (q50, q80))
        if min_samples < 1 or max_samples < min_samples:
            raise ValueError("Nhận diện: «mẫu tối thiểu mỗi giờ» không được lớn hơn «số mẫu mỗi giờ NY».")
        self.horizons = {k: h for k, h in horizons.items() if h >= 1}
        self.q80, self.q50 = q80, q50
        self.max_samples, self.min_samples = max_samples, min_samples
        self.reset()

    def reset(self) -> None:
        span = max(self.horizons.values(), default=0) + 1
        self._bars: deque[dict[str, Any]] = deque(maxlen=span)     # nến gần nhất: close, ATR, giờ, khoảng trống, dự báo
        self._gaps = 0
        self._ext = {k: RollingHighLow(h) for k, h in self.horizons.items()}
        self._by_hour = {k: [_Pair(self.max_samples) for _ in range(24)] for k in self.horizons}
        self._pooled = {k: _Pair(POOLED_FACTOR * self.max_samples) for k in self.horizons}
        self.score = {k: _Score() for k in self.horizons}

    # ------------------------------------------------------------------ mỗi nến
    def step(self, bar: Bar, atr: Optional[float], hour: int, gap_before: bool,
             levels: list[tuple[str, str, float]]) -> dict[str, Optional[dict]]:
        """Bước 13 của nến t (``hour`` = giờ New York của t, ``gap_before`` = khoảng trống dài ngay trước t): mẫu + chấm
        của các nến s = t − h, rồi dự báo tại t cho mọi tầm. ``levels`` = [(loại, "up" | "down", giá)] — mức để tính
        xác suất chạm (được chấm khi kết cục đã biết)."""
        self._gaps += gap_before
        for k, h in self.horizons.items():
            hi, lo = self._ext[k].push(bar.index, bar.high, bar.low)
            if len(self._bars) >= h:
                self._complete(k, self._bars[-h], hi, lo)
        ok = atr is not None and atr > 0
        out = {k: (self._forecast(k, hour, bar.close, atr, levels) if ok else None) for k in self.horizons}
        self._bars.append({"c": bar.close, "atr": atr, "hour": hour, "gaps": self._gaps, "fc": out})
        return out

    def _complete(self, k: str, s: dict[str, Any], hi: float, lo: float) -> None:
        """Nến s vừa đủ h nến sau: thêm mẫu, chấm dự báo của s. Bỏ nếu có khoảng trống hoặc thiếu ATR."""
        a = s["atr"]
        if a is None or a <= 0 or s["gaps"] != self._gaps:
            return
        u, d = (hi - s["c"]) / a, (s["c"] - lo) / a
        self._by_hour[k][s["hour"]].add(u, d)
        self._pooled[k].add(u, d)
        fc = s["fc"][k]
        if fc is not None:
            self._grade(self.score[k], s["hour"], fc, hi, lo, u, d)

    def _grade(self, sc: _Score, hour: int, fc: dict[str, Any], hi: float, lo: float, u: float, d: float) -> None:
        inside80 = hi <= fc["hi80"] and lo >= fc["lo80"]
        sc.n += 1
        sc.cov80 += inside80
        sc.cov50 += hi <= fc["hi50"] and lo >= fc["lo50"]
        sc.w80 += fc["qu80"] + fc["qd80"]
        sc.w50 += fc["qu50"] + fc["qd50"]
        q = self.q80
        sc.loss += _pinball(q, u, fc["qu80"]) + _pinball(q, d, fc["qd80"])
        sc.loss0 += _pinball(q, u, fc["b0"][0]) + _pinball(q, d, fc["b0"][1])
        sc.by_hour[hour][0] += 1
        sc.by_hour[hour][1] += inside80
        for m in fc["muc"]:
            hit = (hi >= m["gia"]) if m["phia"] == "up" else (lo <= m["gia"])
            row = sc.touch[m["loai"]]
            row["n"] += 1
            row["cham"] += hit
            row["brier"] += (m["p"] - hit) ** 2
            row["brier0"] += (m["p0"] - hit) ** 2
            b = row["nhom"][min(int(m["p"] * HIT_BINS), HIT_BINS - 1)]
            b[0] += 1
            b[1] += m["p"]
            b[2] += hit

    def _forecast(self, k: str, hour: int, close: float, atr: float,
                  levels: list[tuple[str, str, float]]) -> Optional[dict[str, Any]]:
        pooled = self._pooled[k]
        if len(pooled.u) < POOLED_FACTOR * self.min_samples:
            return None                                             # khởi động
        grp = self._by_hour[k][hour]
        src, own = ("gio", grp) if len(grp.u) >= self.min_samples else ("chung", pooled)
        qu80, qd80 = quantile(own.u.xs, self.q80), quantile(own.d.xs, self.q80)
        qu50, qd50 = quantile(own.u.xs, self.q50), quantile(own.d.xs, self.q50)
        b0 = (qu80, qd80) if own is pooled else (quantile(pooled.u.xs, self.q80), quantile(pooled.d.xs, self.q80))
        muc = []
        for kind, side, price in levels:
            dist = ((price - close) if side == "up" else (close - price)) / atr
            win, win0 = (own.u, pooled.u) if side == "up" else (own.d, pooled.d)
            p, p0 = win.at_least(dist), win0.at_least(dist)
            muc.append({"loai": kind, "phia": side, "gia": price, "kc_atr": dist, "p": p, "p0": p0})
        return {"lo80": close - qd80 * atr, "hi80": close + qu80 * atr, "lo50": close - qd50 * atr,
                "hi50": close + qu50 * atr, "qu80": qu80, "qd80": qd80, "qu50": qu50, "qd50": qd50, "b0": b0,
                "nguon": src, "n_mau": len(own.u), "gio_ny": hour, "muc": muc}

    # ------------------------------------------------------------------ đọc điểm
    @staticmethod
    def _summary(sc: _Score) -> dict[str, Any]:
        """Điểm gọn của một tầm (dùng chung cho ``brief`` và ``scores``): độ phủ, độ rộng, skill so với B0, Brier xác suất
        chạm theo loại mức và gộp mọi loại (``cham_tong`` — ô tiêu đề của giao diện)."""
        n, touch = sc.n, sorted(sc.touch.items())
        tn = sum(r["n"] for _k, r in touch)
        return {
            "n": n, "phu_80": _ratio(sc.cov80, n), "phu_50": _ratio(sc.cov50, n), "rong_80_atr": _ratio(sc.w80, n),
            "skill_so_voi_b0": (1.0 - sc.loss / sc.loss0) if sc.loss0 > 0 else None,
            "cham": {kind: {"n": r["n"], "brier": _ratio(r["brier"], r["n"]), "brier_b0": _ratio(r["brier0"], r["n"])}
                     for kind, r in touch},
            "cham_tong": {"n": tn, "brier": _ratio(sum(r["brier"] for _k, r in touch), tn),
                          "brier_b0": _ratio(sum(r["brier0"] for _k, r in touch), tn)},
        }

    def brief(self) -> dict[str, Any]:
        """Điểm gọn tới nến hiện tại cho tooltip / «Đang theo dõi» — đọc thẳng bộ đếm, không dựng bảng theo giờ."""
        return {k: self._summary(sc) for k, sc in self.score.items()}

    def scores(self) -> dict[str, Any]:
        """Điểm thật tới nến hiện tại (chỉ khoảng đã có kết cục): điểm gọn + độ rộng lõi, độ phủ theo giờ NY, tỷ lệ chạm
        và hiệu chuẩn theo loại mức."""
        out = {}
        for k, sc in self.score.items():
            row = self._summary(sc)
            row["rong_50_atr"] = _ratio(sc.w50, sc.n)
            row["phu_80_theo_gio"] = [{"gio": g, "n": c[0], "phu_80": _ratio(c[1], c[0])} for g, c in enumerate(sc.by_hour)]
            for kind, r in sc.touch.items():
                row["cham"][kind].update({"ty_le_cham": _ratio(r["cham"], r["n"]),
                                          "hieu_chuan": [{"p_tb": b[1] / b[0], "cham": b[2] / b[0], "n": b[0]}
                                                         for b in r["nhom"] if b[0]]})
            out[k] = row
        return out
