"""[E4] Order block neo vào sự kiện đổi hướng (plan_ket_hop_ict_indicator.md §3.4; luồng: kien_truc_luong_ict.md §4.4).

Mốc của OB là nến d của sự kiện đổi hướng — ``MSS`` (0.10.0, mặc định, plan_mss_ob_pd.md §3) hoặc ``SHIFT`` (0.5.0) — hoặc của
displacement (biến thể ``neo = "displacement"``). Mô tả cho OB tăng; OB giảm đối xứng (đổi vai nến tăng / giảm, mép trên / dưới).

**MSS** (0.10.0): tìm chuỗi nến ngược màu cuối trong [s − lookback, s] với s = nến đầu đoạn displacement của MSS (``create(...,
before=s + 1)``) — không tìm trong chính đoạn (nến hồi nhỏ giữa đoạn không phải OB).

**Ứng viên** (bước 6c của nến d, chỉ dùng nến < d đã có trong bộ đệm):

* tìm lùi từ d − 1 về ``nến bắt đầu − lookback`` (nến bắt đầu = nến lấy thanh khoản của SHIFT; với neo displacement =
  d) nến giảm (``close < open``) gần d nhất. Không lùi qua khoảng trống dữ liệu: nến có khoảng trống ngay trước nó là
  nến cuối cùng được xét;
* ``than_chuoi`` (OB-T, gốc ICT — nghiên cứu §3.4): gộp cả chuỗi nến giảm liền trước nến đó thành một khối; vùng chỉ
  lấy thân = [close thấp nhất, open cao nhất]. (Quy tắc «bỏ nến thân nhỏ nằm lọt trong thân nến kề» không đổi vùng
  nên không cần cài.);
* ``nen_cuoi_rau`` (OB-R, cách SMC phổ biến): chỉ nến giảm gần d nhất, vùng = [low, high];
* không có nến giảm nào → không có ứng viên (đếm ``khong_co_nen``);
* neo displacement (``create_on_break``): chỉ khi close[d] vượt high cao nhất của ``lookback`` nến trước;
* một cấu trúc một OB: SHIFT sau tìm lại đúng chuỗi nến của OB đã tạo → dùng lại OB đó (đếm ``trung``), không tạo mới.

**Xác nhận** (nghiên cứu §3.4: «xác nhận khi giá vượt đầu xa của khối»): nến đầu tiên ≥ d có ``high > mép trên`` —
từ đây OB mới có hiệu lực (sự kiện ``ORDER_BLOCK_*`` ở nến này). Ứng viên bị bỏ (``ended = DROPPED``, không phát sự
kiện, chỉ đếm) khi ``close < mép dưới`` trước lúc xác nhận (xét trước, kể cả ở chính nến d), hết hạn, hoặc gặp SHIFT
ngược chiều.

**Vòng đời** (bước 3b của nến t, chỉ OB đã xác nhận ở nến < t):

* chạm lần đầu: ``low[t] ≤ mép trên`` → ``fail`` nếu ``close[t] < mép dưới``, không thì ``tap``. Sau đó thôi theo dõi;
* chưa chạm mà ``t ≥ d + han`` → ``expired_time``;
* SHIFT ngược chiều ở nến t (bước 6c) → ``expired_shift``.

**Vòng đời PD array** (0.10.0, ``pd_mode`` ≠ None — plan_mss_ob_pd.md §4): chạm lần đầu không kết thúc OB. Từ nến chạm trở đi (kể
cả nến chạm), **kết quả đầu tiên**: hỏng (``close`` vượt mép xa; chế độ ``ce``: vượt mean threshold — xét trước) → ``fail``; giữ
(``strict``: close rời mép gần ≥ ``away_atr`` × ATR[t−1]; ``loose`` / ``ce``: close ra ngoài mép gần) → ``respect``. Đã chạm mà quá
``han`` nến từ nến chạm chưa có kết quả → ``expired_tapped``; đổi hướng ngược chiều → ``expired_shift`` (cả OB đã chạm chưa kết quả).
OB hỏng → **breaker** ngược chiều trên đúng vùng (``kind = "breaker"``, có hiệu lực từ nến sau, cùng vòng đời; breaker hỏng không
sinh breaker mới).

Thành phần chỉ giữ trạng thái; thuật toán phát sự kiện (``ORDER_BLOCK_*``, ``BREAKER_*``, ``OB_TAP_*``, ``OB_RESPECT_*``, ``OB_FAIL_*``,
``OB_EXPIRED``).
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Iterator, Optional

from core.components.pd_array import MODES as PD_MODES
from core.components.pd_array import reaction
from core.types import Bar

VARIANTS = ("than_chuoi", "nen_cuoi_rau")
ANCHORS = ("shift", "displacement")
#: Kết cục → chữ ngắn (details / thống kê). Khoá cũng là danh sách mọi kết cục (0.5.0 — chế độ shift giữ đúng chữ này).
END_TEXT_VI = {"tap": "chạm lần đầu", "fail": "close vượt mép xa", "expired_time": "hết hạn",
               "expired_shift": "SHIFT ngược chiều"}
#: Vòng đời PD array (0.10.0): kết cục thêm và chữ cho chế độ MSS.
END_TEXT_PD_VI = {"tap": "chạm lần đầu — chờ giữ / hỏng", "respect": "được giữ (close rời mép gần đủ xa)", "fail": "hỏng (close vượt mép xa)",
                  "fail_ce": "hỏng (close vượt mean threshold)", "expired_time": "hết hạn chưa chạm",
                  "expired_tapped": "đã chạm, hết hạn chưa giữ / hỏng", "expired_shift": "đổi hướng ngược chiều"}
#: ``ended`` của ứng viên bị bỏ trước khi xác nhận (không phải kết cục — không có sự kiện).
DROPPED = "dropped"
_NONE: tuple = ((), (), (), ())


@dataclass
class OrderBlock:
    seq: int
    direction: str                # "up" (OB tăng, dưới giá) | "down"
    lo: float
    hi: float
    first_bar: Bar                # nến đầu của khối (xa d nhất)
    last_bar: Bar                 # nến cuối (gần d nhất) — «nến OB»
    n_bars: int
    anchor: int                   # d
    anchor_id: str                # sự kiện SHIFT (hoặc DISPLACEMENT) ở d
    deadline: int                 # d + han
    confirmed_at: Optional[int] = None     # nến giá vượt đầu xa (None: còn là ứng viên)
    event_id: str = ""
    ended: Optional[str] = None   # khoá END_TEXT_VI / END_TEXT_PD_VI | DROPPED
    kind: str = "ob"              # "ob" | "breaker" (0.10.0)
    tapped_at: Optional[int] = None        # PD array: nến chạm lần đầu
    tap_deadline: Optional[int] = None     # PD array: hạn chờ kết quả sau chạm

    @property
    def mid(self) -> float:
        """Mean threshold (50% vùng)."""
        return (self.lo + self.hi) / 2.0

    def brief(self) -> dict[str, Any]:
        return {"id": self.event_id, "chieu": self.direction, "lo": self.lo, "hi": self.hi, "mean_threshold": self.mid,
                "nen_dau": self.first_bar.index, "nen_cuoi": self.last_bar.index, "nen_neo": self.anchor,
                "nen_xac_nhan": self.confirmed_at, "han_nen": self.deadline}

    def link(self) -> Optional[dict[str, Any]]:
        """Bản gọn gắn vào nhịp OTE cùng SHIFT (id None khi còn ứng viên); None khi ứng viên đã bị bỏ (vùng không còn)."""
        if self.ended == DROPPED:
            return None
        return {"id": self.event_id or None, "lo": self.lo, "hi": self.hi, "da_xac_nhan": self.confirmed_at is not None,
                "nen_xac_nhan": self.confirmed_at}

    def dist(self, close: Optional[float]) -> float:
        """Khoảng cách từ close tới vùng (0 khi close nằm trong vùng)."""
        return 0.0 if close is None else max(self.lo - close, close - self.hi, 0.0)

    def beyond_far(self, bar: Bar) -> bool:
        """Giá vượt đầu xa của khối (điều kiện xác nhận)."""
        return bar.high > self.hi if self.direction == "up" else bar.low < self.lo

    def touched(self, bar: Bar) -> bool:
        return bar.low <= self.hi if self.direction == "up" else bar.high >= self.lo

    def closed_through(self, bar: Bar) -> bool:
        """Close vượt mép xa phía ngược chiều OB (thủng mép dưới của OB tăng)."""
        return bar.close < self.lo if self.direction == "up" else bar.close > self.hi


def _opposite(bar: Bar, direction: str) -> bool:
    """Nến «ngược màu» với chiều OB: OB tăng cần nến giảm, OB giảm cần nến tăng (doji không tính)."""
    return bar.close < bar.open if direction == "up" else bar.close > bar.open


class OrderBlockTracker:
    def __init__(self, variant: str = "than_chuoi", lookback: int = 5, expiry: int = 96, buffer: int = 16,
                 pd_mode: Optional[str] = None, away_atr: float = 1.0) -> None:
        if variant not in VARIANTS:
            raise ValueError("ob_bien_the phải thuộc %s" % (list(VARIANTS),))
        if lookback < 1 or expiry < 1:
            raise ValueError("ob_lui phải ≥ 1, ob_han phải ≥ 1")
        if pd_mode is not None and pd_mode not in PD_MODES:
            raise ValueError("Chế độ PD array của OB phải thuộc %s" % (list(PD_MODES),))
        self.variant = variant
        self.lookback = lookback
        self.expiry = expiry
        self.pd_mode = pd_mode            # None = vòng đời 0.5.0 (chỉ lần chạm đầu)
        self.away_atr = away_atr
        self._cap = max(buffer, lookback + 2)
        self.reset()

    def reset(self) -> None:
        self._seq = 0
        self._recent: deque[tuple[Bar, bool]] = deque(maxlen=self._cap)   # (nến, có khoảng trống ngay trước nó)
        self.candidates: list[OrderBlock] = []     # chờ giá vượt đầu xa
        self.open: list[OrderBlock] = []           # đã xác nhận, chưa chạm
        self._made: dict[tuple[str, int, int], OrderBlock] = {}   # (chiều, nến đầu, nến cuối) → OB, trong tầm bộ đệm
        self.counts = {"ung_vien": 0, "khong_co_nen": 0, "trung": 0, "xac_nhan": 0, "bo_truoc_xac_nhan": 0,
                       "tap": 0, "fail": 0, "expired_time": 0, "expired_shift": 0}
        if self.pd_mode is not None:      # khoá thêm chỉ ở vòng đời PD array (chế độ cũ giữ đúng bộ khoá 0.5.0)
            self.counts.update({"respect": 0, "expired_tapped": 0, "breaker": 0, "breaker_respect": 0, "breaker_fail": 0})
        self.tap_ages: list[int] = []

    # ------------------------------------------------------------------ bộ đệm nến
    def push(self, bar: Bar, gap_before: bool) -> None:
        """Ghi nến t vào bộ đệm (gọi mỗi nến, sau bước 3b) — ứng viên tạo ở nến sau chỉ đọc nến < nến tạo."""
        self._recent.append((bar, gap_before))

    def _window(self, end: int, lo_index: int) -> Iterator[Bar]:
        """Nến trong [lo_index, end − 1] theo thứ tự lùi; dừng sau nến có khoảng trống ngay trước nó."""
        for b, gap_before in reversed(self._recent):
            if b.index >= end:
                continue
            if b.index < lo_index:
                return
            yield b
            if gap_before:
                return
        if len(self._recent) == self._recent.maxlen and self._recent[0][0].index > lo_index:
            raise RuntimeError("Bộ đệm OB (%d nến) không đủ cho khoảng [%d, %d]." % (self._cap, lo_index, end - 1))

    # ------------------------------------------------------------------ ứng viên, xác nhận
    def create(self, direction: str, bar: Bar, start: int, anchor_id: str,
               before: Optional[int] = None) -> Optional[OrderBlock]:
        """OB của mốc d = ``bar`` từ nến trong [start − lookback, (before hoặc d) − 1]; None nếu không có nến ngược màu. Nến d
        xét như mọi nến sau (``_advance``): đã xác nhận (``confirmed_at == d``), bị bỏ, hoặc nằm trong ``candidates``. Chuỗi
        nến đã thành OB trước đó → trả lại chính OB đó (người gọi chỉ phát sự kiện khi ``event_id`` còn rỗng)."""
        d = bar.index
        run: list[Bar] = []
        for b in self._window(d if before is None else before, start - self.lookback):
            if _opposite(b, direction):
                run.append(b)
                if self.variant == "nen_cuoi_rau":
                    break
            elif run:
                break
        if not run:
            self.counts["khong_co_nen"] += 1
            return None
        last, first = run[0], run[-1]
        key = (direction, first.index, last.index)
        self._made = {k: v for k, v in self._made.items() if k[2] >= d - self._cap}   # ngoài bộ đệm: không tìm lại được
        if key in self._made:
            self.counts["trung"] += 1
            return self._made[key]
        if self.variant == "nen_cuoi_rau":
            lo, hi = last.low, last.high
        elif direction == "up":                     # chuỗi nến giảm: thân = [close, open]
            lo, hi = min(b.close for b in run), max(b.open for b in run)
        else:                                       # chuỗi nến tăng: thân = [open, close]
            lo, hi = min(b.open for b in run), max(b.close for b in run)
        ob = OrderBlock(self._seq, direction, lo, hi, first, last, len(run), d, anchor_id, d + self.expiry)
        self._seq += 1
        self._made[key] = ob
        self.counts["ung_vien"] += 1
        if not self._advance(ob, bar):
            self.candidates.append(ob)
        return ob

    def create_on_break(self, direction: str, bar: Bar, anchor_id: str) -> Optional[OrderBlock]:
        """Neo displacement: chỉ tạo khi close[d] vượt high cao nhất (low thấp nhất) của ``lookback`` nến trước."""
        d = bar.index
        vals = [b.high if direction == "up" else b.low for b in self._window(d, d - self.lookback)]
        if not vals or not (bar.close > max(vals) if direction == "up" else bar.close < min(vals)):
            return None
        return self.create(direction, bar, d, anchor_id)

    def _advance(self, ob: OrderBlock, bar: Bar) -> bool:
        """Ứng viên gặp nến ``bar`` (≥ d): close vượt mép xa / hết hạn → bỏ; vượt đầu xa → xác nhận; còn lại chờ (False)."""
        if ob.closed_through(bar) or bar.index >= ob.deadline:
            self._drop(ob)
        elif ob.beyond_far(bar):
            ob.confirmed_at = bar.index
            self.counts["xac_nhan"] += 1
            self.open.append(ob)
        else:
            return False
        return True

    def _drop(self, ob: OrderBlock) -> None:
        ob.ended = DROPPED
        self.counts["bo_truoc_xac_nhan"] += 1

    # ------------------------------------------------------------------ vòng đời
    def on_bar(self, bar: Bar, atr_prev: Optional[float] = None) -> tuple:
        """Bước 3b của nến t: (OB đã xác nhận vừa kết thúc — ``ended`` đã ghi, ứng viên vừa xác nhận ở t, OB vừa chạm lần
        đầu mà chưa kết thúc — chỉ PD array, breaker vừa sinh từ OB hỏng — chỉ PD array)."""
        if not self.open and not self.candidates:
            return _NONE
        taps: list[OrderBlock] = []
        breakers: list[OrderBlock] = []
        if self.pd_mode is None:
            done = self._first_touch(bar)
        else:
            done = self._pd_step(bar, atr_prev, taps, breakers)
        return done, self._advance_candidates(bar), taps, breakers

    def _first_touch(self, bar: Bar) -> list[OrderBlock]:
        """Vòng đời 0.5.0: lần chạm đầu là kết cục (``tap`` / ``fail``); chưa chạm quá hạn → ``expired_time``."""
        t = bar.index
        done: list[OrderBlock] = []
        still: list[OrderBlock] = []
        for ob in self.open:
            if ob.touched(bar):
                failed = ob.closed_through(bar)
                self._end(ob, "fail" if failed else "tap")
                if not failed:
                    self.tap_ages.append(t - ob.confirmed_at)
                done.append(ob)
            elif t >= ob.deadline:
                self._end(ob, "expired_time")
                done.append(ob)
            else:
                still.append(ob)
        self.open = still
        return done

    def _pd_step(self, bar: Bar, atr_prev: Optional[float], taps: list[OrderBlock],
                 breakers: list[OrderBlock]) -> list[OrderBlock]:
        """PD array (0.10.0): chạm đầu ghi ``taps`` (chưa kết thúc); kết quả theo ``pd_array.reaction`` — hỏng (``fail``) xét trước,
        giữ (``respect``); hết hạn chưa chạm / sau chạm; OB hỏng → breaker ngược chiều (``breakers``, hiệu lực từ nến sau)."""
        t = bar.index
        done: list[OrderBlock] = []
        still: list[OrderBlock] = []
        for ob in self.open:
            if ob.tapped_at is None and ob.touched(bar):
                ob.tapped_at, ob.tap_deadline = t, t + self.expiry
                self.counts["tap"] += 1
                self.tap_ages.append(t - ob.confirmed_at)
                taps.append(ob)
            if ob.tapped_at is None:
                outcome = "expired_time" if t >= ob.deadline else None
            else:
                r = reaction(ob.direction, ob.lo, ob.hi, bar.close, atr_prev, self.pd_mode, self.away_atr)
                outcome = {"disrespect": "fail", "respect": "respect"}.get(r) or (
                    "expired_tapped" if t >= ob.tap_deadline else None)
            if outcome is None:
                still.append(ob)
                continue
            self._end(ob, outcome)
            done.append(ob)
            if ob.kind == "breaker" and outcome in ("respect", "fail"):
                self.counts["breaker_" + outcome] += 1
            if outcome == "fail" and ob.kind == "ob":
                br = OrderBlock(self._seq, "down" if ob.direction == "up" else "up", ob.lo, ob.hi, ob.first_bar,
                                ob.last_bar, ob.n_bars, t, ob.event_id, t + self.expiry, confirmed_at=t, kind="breaker")
                self._seq += 1
                self.counts["breaker"] += 1
                breakers.append(br)
        self.open = still + breakers
        return done

    def _advance_candidates(self, bar: Bar) -> list[OrderBlock]:
        """Ứng viên gặp nến ``bar``: trả ứng viên vừa xác nhận (bỏ / hết hạn chỉ đếm)."""
        confirmed: list[OrderBlock] = []
        waiting: list[OrderBlock] = []
        for ob in self.candidates:
            if not self._advance(ob, bar):
                waiting.append(ob)
            elif ob.ended is None:
                confirmed.append(ob)
        self.candidates = waiting
        return confirmed

    def expire_opposite(self, shift_direction: str) -> list[OrderBlock]:
        """Bước 6c: SHIFT chiều ``shift_direction`` → OB đã xác nhận chưa chạm của chiều ngược lại hết hạn (trả về để
        phát sự kiện); ứng viên chiều ngược lại bị bỏ (chỉ đếm)."""
        done = [ob for ob in self.open if ob.direction != shift_direction]
        for ob in done:
            self._end(ob, "expired_shift")
        self.open = [ob for ob in self.open if ob.direction == shift_direction]
        for ob in self.candidates:
            if ob.direction != shift_direction:
                self._drop(ob)
        self.candidates = [ob for ob in self.candidates if ob.direction == shift_direction]
        return done

    def _end(self, ob: OrderBlock, kind: str) -> None:
        ob.ended = kind
        self.counts[kind] += 1

    # ------------------------------------------------------------------ đọc trạng thái
    def ranked(self, direction: str, close: Optional[float], kind: str = "ob") -> list[OrderBlock]:
        """OB (hoặc breaker) đã xác nhận còn mở của một chiều, gần close nhất trước (cùng khoảng cách → mới hơn trước)."""
        return sorted((ob for ob in self.open if ob.direction == direction and ob.kind == kind),
                      key=lambda o: (o.dist(close), -o.seq))
