"""[N] Thời gian của trạng thái (thuat_toan_nhan_dien.md §5b) — ``ict_structure`` 0.7.0.

**Đoạn hiển thị**: từ nến trạng thái bắt đầu hiện tới nến trước khi trạng thái khác hiện; độ dài L (nến). Đoạn kết thúc vì
«chưa đủ nến» (khoảng trống dài, thiếu ATR) bị kiểm duyệt — không vào mẫu. Tại nến t (tuổi a = t − nến bắt đầu + 1),
tầm h:

* xác suất còn giữ p = #(L ≥ a + h) / #(L ≥ a) trên các đoạn đã kết thúc cùng trạng thái; mẫu số #(L ≥ a) <
  ``MIN_EPISODES`` → mọi trạng thái; vẫn thiếu → None;
* **B0** (bỏ điều kiện tuổi) = tỷ lệ nến của cùng mẫu mà đoạn còn kéo dài thêm ≥ h nến = Σ max(L − h, 0) / Σ L;
* thời gian còn lại = trung vị (L − a) trên các đoạn có L ≥ a (cùng mẫu);
* chấm ở t + h: trạng thái hiện ở t + h vẫn là đoạn đó; cửa sổ có lần cắt (khoảng trống dài, hoặc rơi về «chưa đủ
  nến») → không chấm (kết cục không biết).

Chỉ dùng đoạn đã kết thúc trước t và kết cục đã biết: nhân quả. Giới hạn đã biết: đoạn bị cắt bỏ hẳn khỏi mẫu (chưa ước
lượng kiểu Kaplan–Meier) — đoạn dài dễ vắt khoảng trống hơn nên hơi thiếu trong mẫu.
"""
from __future__ import annotations

import bisect
from collections import defaultdict, deque
from typing import Any, Optional

from core.components.rolling_stats import BrierTally, SortedWindow, quantile

MAX_EPISODES = 400                     # đoạn gần nhất giữ cho mỗi trạng thái
POOLED_EPISODES = 5 * MAX_EPISODES     # mẫu chung: đủ chỗ cho cả năm trạng thái
MIN_EPISODES = 30


class StateClock:
    def __init__(self, horizons: dict[str, int], min_episodes: int = MIN_EPISODES) -> None:
        self.horizons = {k: h for k, h in horizons.items() if h >= 1}
        self.min_episodes = max(1, min_episodes)
        self.reset()

    def reset(self) -> None:
        self.name: Optional[str] = None
        self.start: Optional[int] = None                # nến bắt đầu đoạn hiển thị hiện tại — cũng là định danh đoạn
        self._cuts = 0                                  # số lần cắt: khoảng trống dài, rơi về «chưa đủ nến»
        self._len: dict[str, SortedWindow] = defaultdict(lambda: SortedWindow(MAX_EPISODES))
        self._all = SortedWindow(POOLED_EPISODES)
        self._b0: dict[tuple[Optional[str], int], float] = {}   # (mẫu, tầm) → B0; xoá khi mẫu đổi
        self._due = {k: deque() for k in self.horizons}  # (nến chấm, nến đầu đoạn, lần cắt, p, p0) theo thời gian
        self.score = {k: BrierTally() for k in self.horizons}
        self.fc: Optional[dict[str, Any]] = None

    def step(self, t: int, name: Optional[str], gap_before: bool) -> Optional[dict[str, Any]]:
        """Nến t: trạng thái đang hiện sau t (``name``; None = chưa đủ nến). Ghi đoạn vừa kết thúc, chấm dự báo tới hạn
        ở t, rồi dự báo tại t. Trả dự báo (``self.fc``) hoặc None."""
        self._cuts += gap_before or (name is None and self.name is not None)
        if name != self.name:
            if self.name is not None and name is not None:     # đoạn kết thúc vì trạng thái khác hiện (không kiểm duyệt)
                length = t - self.start
                self._len[self.name].add(length)
                self._all.add(length)
                self._b0.clear()
            self.name, self.start = name, t
        for k, q in self._due.items():
            while q and q[0][0] <= t:
                _t, start, cuts, p, p0 = q.popleft()
                if cuts == self._cuts:
                    self.score[k].add(p, p0, start == self.start)
        self.fc = self._forecast(t) if name is not None else None
        return self.fc

    def _base(self, key: Optional[str], win: SortedWindow, h: int) -> float:
        """B0 của mẫu ``key`` (tên trạng thái; None = mẫu chung): Σ max(L − h, 0) / Σ L — tính lại chỉ khi mẫu đổi."""
        v = self._b0.get((key, h))
        if v is None:
            xs = win.xs
            i = bisect.bisect_right(xs, h)
            v = self._b0[(key, h)] = (sum(xs[i:]) - h * (len(xs) - i)) / sum(xs)
        return v

    def _forecast(self, t: int) -> Optional[dict[str, Any]]:
        a = t - self.start + 1
        for win, src, key in ((self._len.get(self.name), "trang_thai", self.name), (self._all, "chung", None)):
            n_alive = win.count_at_least(a) if win is not None else 0      # mẫu số: số đoạn có L ≥ a
            if n_alive >= self.min_episodes:
                break
        else:
            return None
        giu = {}
        for k, h in self.horizons.items():
            giu[k] = p = win.count_at_least(a + h) / n_alive
            self._due[k].append((t + h, self.start, self._cuts, p, self._base(key, win, h)))
        # trung vị (L − a) trên đuôi đã sắp xs[−n_alive:] — đọc thẳng, không cắt danh sách (O(1) mỗi nến)
        med = quantile(win.xs, 0.5, len(win.xs) - n_alive) - a
        return {"tuoi_nen": a, "giu": giu, "con_lai_nen": med, "nguon": src, "n_doan": len(win), "n_doan_con": n_alive}

    def brief(self) -> dict[str, Any]:
        """Điểm thật tới nến hiện tại: mỗi tầm n, tỷ lệ còn giữ thật (``ty_le``), Brier, Brier của B0."""
        return {k: sc.summary() for k, sc in self.score.items()}
