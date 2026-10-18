"""[S5] Phản ứng của giá ở PD array khung lớn (FVG H1/H4) → ``pd_bias`` (plan_ict_structure §4.9, D6).

Vùng = FVG khung lớn hợp lệ do ``htf_stack.HtfStack`` phát hiện (ba nến khung lớn đã chốt, liền kề theo lịch,
không nến nào ``degraded``); có hiệu lực từ nến khung nhỏ SAU nến làm nó được biết. Tương tác đo bằng nến
khung nhỏ (M15) đã đóng:

* **tap** = nến đầu tiên giá chạm vùng (FVG tăng: ``low ≤ hi``; FVG giảm: ``high ≥ lo``);
* từ nến tap trở đi (kể cả nến tap), kết quả **đầu tiên** được ghi — mỗi vùng chỉ một kết quả, sau đó vùng
  là «đã dùng»:

  ========  ===========================================  ==========================================
  Chế độ    respect (FVG tăng; giảm đối xứng)             disrespect (FVG tăng; giảm đối xứng)
  ========  ===========================================  ==========================================
  strict    ``close ≥ hi + respect_away_atr × ATR[t−1]``  ``close < lo`` (vượt mép xa)
  loose     ``close > hi`` (ra ngoài mép gần)             ``close < lo``
  ce        ``close > hi``                                ``close < (lo + hi) / 2`` (vượt CE 50%)
  ========  ===========================================  ==========================================

  ``ce`` lấy respect như ``loose`` — đúng cách survey-v2 đo (plan §2.6). Mặc định ``strict`` (D6).

``pd_bias`` = chiều hàm ý của kết quả gần nhất (H1 và H4 gộp): respect FVG tăng → +1, disrespect FVG tăng →
−1; FVG giảm ngược lại. Nhiều kết quả trong cùng một nến: cùng chiều → chiều đó (khung nguồn = khung cao
nhất); ngược chiều → ``0`` (mâu thuẫn trong cùng nến — do lab chọn, giống order flow «hai chiều cùng nến»).
Không có kết quả nào → ``None``.

Vùng chờ tap / chờ kết quả nằm trong heap theo mép → mỗi nến chỉ xét vùng giá đã tới; tổng chi phí
O(N log N). IFVG (vùng bị disrespect đổi vai) để v0.2 (plan §7).
"""
from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Any, Optional

from core.types import Bar

MODES = ("strict", "loose", "ce")
TF_RANK = {"H1": 1, "H4": 2}
#: (chiều FVG, kết quả) → chiều hàm ý cho pd_bias.
IMPLIED = {("up", "respect"): 1, ("up", "disrespect"): -1, ("down", "respect"): -1, ("down", "disrespect"): 1}
BIAS_TEXT_VI = {1: "tăng", -1: "giảm", 0: "mâu thuẫn trong cùng nến", None: "chưa có"}


@dataclass
class PdZone:
    seq: int
    tf: str
    direction: str                 # chiều FVG: "up" | "down"
    lo: float
    hi: float
    known_index: int               # nến khung nhỏ làm vùng được biết (hiệu lực từ nến sau)
    event_id: str                  # HTF_FVG_* nguồn
    from_displacement: bool
    mid_index: int                 # nến khung nhỏ đầu tiên của nến khung lớn ở giữa (để vẽ)
    state: str = "cho_cham"        # cho_cham | da_cham | da_dung
    tap_index: Optional[int] = None
    outcome: Optional[str] = None  # respect | disrespect
    outcome_index: Optional[int] = None

    @property
    def ce(self) -> float:
        return (self.lo + self.hi) / 2.0

    def brief(self) -> dict[str, Any]:
        return {
            "fvg": self.event_id, "khung": self.tf, "chieu_fvg": self.direction, "lo": self.lo, "hi": self.hi,
            "ce": self.ce, "biet_tai_nen": self.known_index, "nen_giua": self.mid_index,
            "from_displacement": self.from_displacement, "trang_thai": self.state, "cham_tai_nen": self.tap_index,
        }


class PdArrayTracker:
    def __init__(self, mode: str = "strict", away_atr: float = 1.0) -> None:
        if mode not in MODES:
            raise ValueError("pd_respect_mode phải thuộc %s" % (list(MODES),))
        if away_atr < 0:
            raise ValueError("respect_away_atr phải >= 0")
        self.mode = mode
        self.away_atr = away_atr
        self.reset()

    def reset(self) -> None:
        self._seq = 0
        self._up_tap: list[tuple] = []      # (−hi, seq, vùng): tap khi low ≤ hi
        self._dn_tap: list[tuple] = []      # (lo, seq, vùng): tap khi high ≥ lo
        self._up_dis: list[tuple] = []      # (−mép xa, seq, vùng): disrespect khi close < mép xa
        self._up_res: list[tuple] = []      # (hi, seq, vùng): respect khi close vượt hi (+ khoảng cách)
        self._dn_dis: list[tuple] = []      # (mép xa, seq, vùng): disrespect khi close > mép xa
        self._dn_res: list[tuple] = []      # (−lo, seq, vùng): respect khi close dưới lo (− khoảng cách)
        self._open: dict[int, PdZone] = {}
        self.bias: Optional[int] = None
        self.bias_tf: Optional[str] = None
        self.bias_since: Optional[int] = None
        self.bias_events: list[str] = []
        self.counts: dict[str, dict[str, int]] = {}

    def _c(self, tf: str, key: str) -> None:
        c = self.counts.get(tf)
        if c is None:
            c = self.counts[tf] = {"vung": 0, "tu_displacement": 0, "cham": 0, "respect": 0, "disrespect": 0}
        c[key] += 1

    def add(self, tf: str, direction: str, lo: float, hi: float, known_index: int, event_id: str,
            from_displacement: bool, mid_index: int) -> PdZone:
        z = PdZone(self._seq, tf, direction, lo, hi, known_index, event_id, from_displacement, mid_index)
        self._seq += 1
        self._open[z.seq] = z
        self._c(tf, "vung")
        if from_displacement:
            self._c(tf, "tu_displacement")
        if direction == "up":
            heapq.heappush(self._up_tap, (-hi, z.seq, z))
        else:
            heapq.heappush(self._dn_tap, (lo, z.seq, z))
        return z

    def _far(self, z: PdZone) -> float:
        if self.mode == "ce":
            return z.ce
        return z.lo if z.direction == "up" else z.hi

    def on_bar(self, bar: Bar, atr_prev: Optional[float]) -> list[tuple[str, PdZone, dict[str, Any]]]:
        """Nến t với các vùng đã biết TRƯỚC t. Trả [(kết quả, vùng, số liệu)] theo thứ tự tạo vùng; cập nhật
        ``bias`` nếu có kết quả."""
        t = bar.index
        while self._up_tap and -self._up_tap[0][0] >= bar.low:
            _k, _s, z = heapq.heappop(self._up_tap)
            self._tap(z, t)
        while self._dn_tap and self._dn_tap[0][0] <= bar.high:
            _k, _s, z = heapq.heappop(self._dn_tap)
            self._tap(z, t)
        close = bar.close
        away = self.away_atr * atr_prev if (self.mode == "strict" and atr_prev is not None) else None
        hits: dict[int, tuple[str, PdZone]] = {}
        while self._up_dis and -self._up_dis[0][0] > close:
            _k, _s, z = heapq.heappop(self._up_dis)
            if z.state == "da_cham" and z.seq not in hits:
                hits[z.seq] = ("disrespect", z)
        while self._dn_dis and self._dn_dis[0][0] < close:
            _k, _s, z = heapq.heappop(self._dn_dis)
            if z.state == "da_cham" and z.seq not in hits:
                hits[z.seq] = ("disrespect", z)
        if self.mode == "strict":
            if away is not None:
                while self._up_res and self._up_res[0][0] <= close - away:
                    _k, _s, z = heapq.heappop(self._up_res)
                    if z.state == "da_cham" and z.seq not in hits:
                        hits[z.seq] = ("respect", z)
                while self._dn_res and -self._dn_res[0][0] >= close + away:
                    _k, _s, z = heapq.heappop(self._dn_res)
                    if z.state == "da_cham" and z.seq not in hits:
                        hits[z.seq] = ("respect", z)
        else:
            while self._up_res and self._up_res[0][0] < close:
                _k, _s, z = heapq.heappop(self._up_res)
                if z.state == "da_cham" and z.seq not in hits:
                    hits[z.seq] = ("respect", z)
            while self._dn_res and -self._dn_res[0][0] > close:
                _k, _s, z = heapq.heappop(self._dn_res)
                if z.state == "da_cham" and z.seq not in hits:
                    hits[z.seq] = ("respect", z)
        out: list[tuple[str, PdZone, dict[str, Any]]] = []
        for seq in sorted(hits):
            kind, z = hits[seq]
            z.state, z.outcome, z.outcome_index = "da_dung", kind, t
            self._open.pop(z.seq, None)
            self._c(z.tf, kind)
            up = z.direction == "up"
            if kind == "respect":
                edge = z.hi if up else z.lo
                if self.mode == "strict":
                    rule = ("close ≥ mép gần (hi) + %s × ATR" if up else "close ≤ mép gần (lo) − %s × ATR") \
                        % self.away_atr
                else:
                    rule = "close > mép gần (hi)" if up else "close < mép gần (lo)"
            else:
                edge = self._far(z)
                if self.mode == "ce":
                    rule = "close < CE 50%" if up else "close > CE 50%"
                else:
                    rule = "close < mép xa (lo)" if up else "close > mép xa (hi)"
            out.append((kind, z, {
                "mep": edge, "khoang_cach_yeu_cau": away if kind == "respect" else None, "atr": atr_prev,
                "quy_tac_vi": rule, "chieu_ham_y": IMPLIED[(z.direction, kind)],
            }))
        if out:
            dirs = {info["chieu_ham_y"] for _k, _z, info in out}
            if len(dirs) == 1:
                d = dirs.pop()
                self.bias = d
                self.bias_tf = max((z.tf for _k, z, info in out if info["chieu_ham_y"] == d),
                                   key=lambda f: TF_RANK.get(f, 0))
            else:
                self.bias, self.bias_tf = 0, None
            self.bias_since = t
            self.bias_events = []
        return out

    def _tap(self, z: PdZone, t: int) -> None:
        z.state, z.tap_index = "da_cham", t
        self._c(z.tf, "cham")
        far = self._far(z)
        if z.direction == "up":
            heapq.heappush(self._up_dis, (-far, z.seq, z))
            heapq.heappush(self._up_res, (z.hi, z.seq, z))
        else:
            heapq.heappush(self._dn_dis, (far, z.seq, z))
            heapq.heappush(self._dn_res, (-z.lo, z.seq, z))

    def open_zones(self) -> list[PdZone]:
        return list(self._open.values())

    def snapshot(self, t: Optional[int]) -> dict[str, Any]:
        return {
            "pd_bias": self.bias,
            "pd_bias_vi": BIAS_TEXT_VI[self.bias],
            "khung": self.bias_tf,
            "tu_nen": self.bias_since,
            "so_nen": (t - self.bias_since) if (t is not None and self.bias_since is not None) else None,
            "su_kien": list(self.bias_events),
            "che_do": self.mode,
            "respect_away_atr": self.away_atr if self.mode == "strict" else None,
        }
