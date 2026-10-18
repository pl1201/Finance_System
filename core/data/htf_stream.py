"""Gộp nến khung lớn (HTF) TUẦN TỰ từ nến khung nhỏ (LTF) đã đóng.

Khác ``core/data/resample.py`` (gộp cả chuỗi một lần để tạo dataset mới), module
này nhận từng nến LTF đã đóng và cho biết, tại đúng nến đó:

* nến HTF đang chạy (chưa hoàn tất) có OHLC bao nhiêu tính tới giờ;
* nến HTF vừa HOÀN TẤT (đủ số nến LTF kỳ vọng, liên tiếp, đúng mốc);
* bucket nào bị thiếu dữ liệu — và thời điểm phát hiện ra điều đó.

Không bao giờ đọc OHLC cuối của một bucket trước khi nến LTF cuối cùng của nó
đóng. Không tự bù nến thiếu.

Mốc bucket (``alignment = utc_epoch``): mở nến HTF là bội số Unix epoch của độ
dài HTF tính theo UTC — cùng quy ước với ``resample.py``. KHÔNG tuyên bố khớp
mốc H4 của broker hay TradingView khi chưa đối chiếu.

Hai bộ gộp:

* :class:`HtfAggregator` — ``utc_epoch``, một khung, «đủ nến» theo số nến danh nghĩa.
  Dùng bởi ``c2_cisd_research``; **giữ nguyên** hành vi (hồi quy AGENTS §7.3).
* :class:`SessionHtfAggregator` — ``ny_1700`` (plan_ict_structure §11.3–§11.4, D10, D14), nhiều
  khung một lúc (H1, H4, D, W), số nến kỳ vọng theo **lịch phiên khai báo**; mỗi nến chốt mang
  ``period_end`` ≠ ``known_at``, ``n_bars`` / ``expected_bars`` / ``coverage``, cờ ``degraded`` /
  ``over`` / ``after_hole``. Dùng bởi ``ict_structure`` [T0].

Mốc ``ny_1700``: ngày giao dịch bắt đầu 17:00 New York (giờ đồng hồ, có đổi giờ mùa hè); H4 = 6 nến
từ 17:00 NY (17, 21, 01, 05, 09, 13); D = 17:00 NY → 17:00 NY hôm sau; tuần mở Chủ nhật 17:00 NY.
H1 = giờ tròn (độ lệch New York là số giờ nguyên nên trùng ``utc_epoch``).
"""
from __future__ import annotations

import bisect
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from zoneinfo import ZoneInfo

from core.types import Bar

ALIGNMENT_UTC_EPOCH = "utc_epoch"
ALIGNMENT_NY_1700 = "ny_1700"
ALIGNMENTS = (ALIGNMENT_UTC_EPOCH, ALIGNMENT_NY_1700)
NY_TZ = ZoneInfo("America/New_York")
#: Khung của bộ gộp theo lịch → độ dài danh nghĩa (giây). D, W chỉ dùng cho mức theo kỳ (plan §11.1).
SESSION_FRAMES = {"H1": 3600, "H4": 4 * 3600, "D": 86400, "W": 7 * 86400}


@dataclass(frozen=True)
class HtfBucket:
    """Ảnh chụp BẤT BIẾN của một nến HTF tại một thời điểm."""

    index: int                 # số thứ tự bucket = open_ts // htf_seconds
    start: datetime            # mở bucket (UTC)
    end: datetime              # đóng bucket (UTC)
    expected_bars: int
    open: float
    high: float
    low: float
    close: float
    high_bar_index: int        # nến LTF ĐẦU TIÊN đạt high (so strict như Pine)
    low_bar_index: int
    first_bar_index: int
    last_bar_index: int
    n_bars: int
    contiguous: bool           # chưa từng thiếu nến LTF nào (kể cả thiếu nến đầu)

    @property
    def complete(self) -> bool:
        return self.contiguous and self.n_bars == self.expected_bars

    @property
    def mid(self) -> float:
        return (self.high + self.low) / 2.0


@dataclass
class PushResult:
    """Những gì aggregator biết được SAU KHI nhận một nến LTF."""

    current: HtfBucket                        # bucket chứa nến vừa nhận
    started_new_bucket: bool = False
    previous: Optional[HtfBucket] = None      # bucket vừa bị bỏ lại (nếu đổi bucket)
    previous_adjacent: bool = False           # bucket mới liền kề bucket trước?
    completed_now: bool = False               # nến vừa nhận là nến cuối, bucket đủ
    newly_incomplete: list = field(default_factory=list)   # bucket vừa bị phát hiện thiếu


class HtfAggregator:
    """Theo dõi bucket HTF hiện tại từ luồng nến LTF đã đóng."""

    def __init__(self, ltf_seconds: int, htf_seconds: int) -> None:
        if htf_seconds % ltf_seconds != 0:
            raise ValueError("HTF phải là bội số của LTF.")
        self.ltf = timedelta(seconds=ltf_seconds)
        self.ltf_seconds = ltf_seconds
        self.htf_seconds = htf_seconds
        self.expected = htf_seconds // ltf_seconds
        self.reset()

    def reset(self) -> None:
        self._cur: Optional[HtfBucket] = None
        self._last_open: Optional[datetime] = None
        self._reported_incomplete: set[int] = set()

    def _bucket_start(self, open_time: datetime) -> tuple[int, datetime]:
        ts = int(open_time.timestamp())
        idx = ts // self.htf_seconds
        return idx, datetime.fromtimestamp(idx * self.htf_seconds, tz=timezone.utc)

    def push(
        self, bar_index: int, open_time: datetime, o: float, h: float, l: float, c: float
    ) -> PushResult:
        idx, start = self._bucket_start(open_time)
        prev = self._cur
        newly_incomplete: list[HtfBucket] = []

        if prev is not None and idx < prev.index:
            raise ValueError("Nến LTF đi lùi thời gian.")

        if prev is None or idx != prev.index:
            # --- mở bucket mới ---
            if prev is not None and not prev.complete and prev.index not in self._reported_incomplete:
                # Bucket cũ kết thúc mà chưa đủ nến (thiếu nến cuối).
                newly_incomplete.append(prev)
                self._reported_incomplete.add(prev.index)
            cur = HtfBucket(
                index=idx, start=start, end=start + timedelta(seconds=self.htf_seconds),
                expected_bars=self.expected,
                open=o, high=h, low=l, close=c,
                high_bar_index=bar_index, low_bar_index=bar_index,
                first_bar_index=bar_index, last_bar_index=bar_index,
                n_bars=1,
                contiguous=(open_time == start),   # thiếu nến đầu -> hỏng ngay
            )
            res = PushResult(
                current=cur, started_new_bucket=True, previous=prev,
                previous_adjacent=(prev is not None and idx == prev.index + 1),
            )
        else:
            # --- cùng bucket ---
            contiguous = prev.contiguous and self._last_open is not None and (
                open_time == self._last_open + self.ltf
            )
            cur = replace(
                prev,
                high=h if h > prev.high else prev.high,          # strict: giữ nến đầu tiên
                high_bar_index=bar_index if h > prev.high else prev.high_bar_index,
                low=l if l < prev.low else prev.low,
                low_bar_index=bar_index if l < prev.low else prev.low_bar_index,
                close=c,
                last_bar_index=bar_index,
                n_bars=prev.n_bars + 1,
                contiguous=contiguous,
            )
            res = PushResult(current=cur)

        if not cur.contiguous and cur.index not in self._reported_incomplete:
            newly_incomplete.append(cur)
            self._reported_incomplete.add(cur.index)

        close_time = open_time + self.ltf
        res.completed_now = cur.complete and close_time == cur.end
        res.newly_incomplete = newly_incomplete
        self._cur = cur
        self._last_open = open_time
        return res


# ============================================================================ ny_1700 + lịch phiên


def bucket_bounds(open_time: datetime, frame: str, alignment: str) -> tuple[datetime, datetime]:
    """Mốc mở và mốc đóng DANH NGHĨA (UTC) của bucket ``frame`` chứa ô mở lúc ``open_time``.

    ``utc_epoch``: bội số Unix epoch của độ dài khung (H1, H4, D; W không định nghĩa). ``ny_1700``: xem
    đầu module. Khung không quá H1 ở cả hai mốc đều là bội số epoch (độ lệch New York là số giờ nguyên).
    """
    if open_time.tzinfo is None:
        open_time = open_time.replace(tzinfo=timezone.utc)
    if frame in SESSION_FRAMES:
        sec = SESSION_FRAMES[frame]
    else:
        from core.types import TIMEFRAME_SECONDS

        if frame not in TIMEFRAME_SECONDS:
            raise ValueError("Khung %r không hỗ trợ." % frame)
        sec = TIMEFRAME_SECONDS[frame]
    if alignment not in ALIGNMENTS:
        raise ValueError("alignment phải thuộc %s, nhận %r" % (list(ALIGNMENTS), alignment))
    if alignment == ALIGNMENT_UTC_EPOCH or sec <= 3600:
        if frame == "W":
            raise ValueError("Mốc utc_epoch không định nghĩa nến tuần.")
        ts = int(open_time.timestamp())
        s = ts - ts % sec
        start = datetime.fromtimestamp(s, tz=timezone.utc)
        return start, start + timedelta(seconds=sec)
    loc = open_time.astimezone(NY_TZ)
    d = loc.date() if loc.hour >= 17 else loc.date() - timedelta(days=1)
    day = datetime(d.year, d.month, d.day, 17, tzinfo=NY_TZ)        # 17:00 NY (giờ đồng hồ) mở ngày giao dịch
    if frame == "H4":
        k = ((loc.hour - 17) % 24) // 4
        s_loc = day + timedelta(hours=4 * k)                       # cộng theo giờ đồng hồ (có đổi giờ)
        e_loc = s_loc + timedelta(hours=4)
    elif frame == "D":
        s_loc, e_loc = day, day + timedelta(days=1)
    else:                                                          # W: mở Chủ nhật 17:00 NY, danh nghĩa 7 ngày
        end_day = d + timedelta(days=1)                            # ngày giao dịch mang tên ngày nó kết thúc
        monday = end_day - timedelta(days=end_day.weekday())
        s_loc = datetime(monday.year, monday.month, monday.day, 17, tzinfo=NY_TZ) - timedelta(days=1)
        e_loc = s_loc + timedelta(days=7)
    return s_loc.astimezone(timezone.utc), e_loc.astimezone(timezone.utc)


def open_slots(calendar: Any, opens: Optional[list[datetime]], start: datetime, end: datetime,
               step: timedelta) -> tuple[int, Optional[datetime], Optional[datetime], bool]:
    """Số ô LTF (lưới neo tại ``start``, bước ``step``) có giờ mở nằm trong phiên theo lịch khai báo.

    Trả ``(số ô, ô mở đầu tiên, mốc đóng của ô mở cuối, theo_lich)``. Ô «mở» khi giờ mở của ô nằm trong
    một phiên ``[open, close)`` — cùng quy ước với ``SessionCalendar.classify_gap``. Không có lịch, hoặc
    khoảng nằm ngoài phạm vi lịch → mọi ô danh nghĩa đều kỳ vọng (``theo_lich = False``). ``opens`` =
    danh sách giờ mở các phiên của lịch (để tìm nhị phân), người gọi giữ sẵn.
    """
    st = int(step.total_seconds())
    if calendar is None or not (calendar.covers(start) and calendar.covers(end - step)):
        n = int((end - start).total_seconds()) // st
        return n, (start if n else None), (end if n else None), False
    sessions = calendar.sessions
    i = max(0, bisect.bisect_right(opens, start) - 1)
    n, first, last_end = 0, None, None
    while i < len(sessions) and sessions[i].open < end:
        s = sessions[i]
        i += 1
        a, b = max(start, s.open), min(end, s.close)
        if b <= a:
            continue
        k0 = -(-int((a - start).total_seconds()) // st)
        f = start + timedelta(seconds=k0 * st)
        if f >= b:
            continue
        cnt = -(-int((b - f).total_seconds()) // st)
        n += cnt
        if first is None:
            first = f
        last_end = f + timedelta(seconds=cnt * st)
    return n, first, last_end, True


@dataclass(frozen=True)
class HtfBar(Bar):
    """Nến khung lớn ĐÃ CHỐT (bất biến) — dùng được như ``Bar`` cho các thành phần cấu trúc.

    ``index`` = số thứ tự nến đã chốt của khung trong luồng (0, 1, …); ``bar_time`` = mốc mở danh nghĩa;
    ``close_time`` = ``period_end`` (mốc đóng theo lịch). ``known_*`` = nến LTF làm hệ thống BIẾT nến này
    đã chốt — ``known_at`` > ``period_end`` khi chốt muộn (thiếu nến cuối, biết khi nến đầu kỳ sau tới).
    """

    frame: str = ""
    nominal_end: Optional[datetime] = None
    known_index: int = -1
    known_pos: int = -1
    known_at: Optional[datetime] = None
    n_bars: int = 0
    expected_bars: Optional[int] = None
    coverage: Optional[float] = None
    by_calendar: bool = False               # số nến kỳ vọng lấy từ lịch khai báo (False = danh nghĩa)
    degraded: bool = False
    degraded_reason: Optional[str] = None   # "coverage_thap" | "ky_dau_thieu" | "ngoai_lich"
    over: bool = False                      # nhiều nến hơn lịch → lịch dữ liệu khác lịch khai báo (chỉ gắn cờ)
    outside_calendar: bool = False          # kỳ «nối tiếp»: mọi nến nằm sau mốc đóng theo lịch của kỳ
    after_hole: bool = False                # trước nó mất trọn ít nhất một bucket giao dịch
    contiguous_prev: bool = False           # liền kề nến chốt trước theo lịch: mở đúng lúc nến trước đóng
    first_in_stream: bool = False
    first_bar: Optional[Bar] = None         # nến LTF đầu / đạt high / đạt low (nến ĐẦU TIÊN đạt — strict)
    high_bar: Optional[Bar] = None
    low_bar: Optional[Bar] = None
    first_pos: int = -1                     # vị trí trong luồng LTF (0 = nến đầu tiên đã nạp)
    high_pos: int = -1
    low_pos: int = -1
    last_index: int = -1

    @property
    def period_end(self) -> datetime:
        return self.close_time

    @property
    def late(self) -> bool:
        return self.known_at is not None and self.known_at > self.close_time

    def brief(self) -> dict[str, Any]:
        """Tóm tắt để ghi vào ``details`` / ``pending_state`` (không chứa tham chiếu nội bộ)."""
        return {
            "khung": self.frame,
            "nen_htf": self.index,
            "mo": self.bar_time.isoformat(),
            "period_end": self.close_time.isoformat(),
            "known_at": self.known_at.isoformat() if self.known_at else None,
            "nen_biet": self.known_index,
            "chot_muon": self.late,
            "open": self.open, "high": self.high, "low": self.low, "close": self.close,
            "n_bars": self.n_bars,
            "expected_bars": self.expected_bars,
            "coverage": self.coverage,
            "theo_lich": self.by_calendar,
            "degraded": self.degraded,
            "ly_do_degraded": self.degraded_reason,
            "over": self.over,
            "ngoai_lich": self.outside_calendar,
            "after_hole": self.after_hole,
            "lien_ke_nen_truoc": self.contiguous_prev,
            "nen_dau": self.first_bar.index if self.first_bar else None,
            "nen_cuoi": self.last_index,
            "nen_high": self.high_bar.index if self.high_bar else None,
            "nen_low": self.low_bar.index if self.low_bar else None,
        }


class _Forming:
    """Kỳ đang hình thành (trạng thái trong của bộ gộp — chỉ để vẽ, không vào cấu trúc)."""

    __slots__ = ("start", "nominal_end", "period_end", "expected", "first_slot", "by_calendar", "continuation",
                 "first_in_stream", "open", "high", "low", "close", "first_bar", "high_bar", "low_bar",
                 "first_pos", "high_pos", "low_pos", "last_index", "n", "closed", "end_ts", "period_end_ts")

    def __init__(self, start: datetime, nominal_end: datetime, period_end: datetime, expected: int,
                 first_slot: Optional[datetime], by_calendar: bool, continuation: bool, first_in_stream: bool,
                 bar: Bar, pos: int) -> None:
        self.start, self.nominal_end, self.period_end = start, nominal_end, period_end
        self.expected, self.first_slot, self.by_calendar = expected, first_slot, by_calendar
        self.continuation, self.first_in_stream = continuation, first_in_stream
        self.open, self.high, self.low, self.close = bar.open, bar.high, bar.low, bar.close
        self.first_bar = self.high_bar = self.low_bar = bar
        self.first_pos = self.high_pos = self.low_pos = pos
        self.last_index = bar.index
        self.n = 1
        self.closed = False
        self.end_ts = nominal_end.timestamp()           # so sánh bằng số giây (nhanh hơn datetime)
        self.period_end_ts = period_end.timestamp()

    def add(self, bar: Bar, pos: int) -> None:
        if bar.high > self.high:                    # strict: giữ nến ĐẦU TIÊN đạt high
            self.high, self.high_bar, self.high_pos = bar.high, bar, pos
        if bar.low < self.low:
            self.low, self.low_bar, self.low_pos = bar.low, bar, pos
        self.close = bar.close
        self.last_index = bar.index
        self.n += 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "mo": self.start.isoformat(), "period_end": self.period_end.isoformat(),
            "open": self.open, "high": self.high, "low": self.low, "close": self.close,
            "n_bars": self.n, "expected_bars": self.expected, "nen_dau": self.first_bar.index,
            "nen_cuoi": self.last_index, "ngoai_lich": self.continuation,
            "ghi_chu_vi": "đang hình thành — chưa dùng (chỉ nến đã chốt mới vào trạng thái)",
        }


class _FrameState:
    __slots__ = ("cur", "last", "n_closed", "started")

    def __init__(self) -> None:
        self.cur: Optional[_Forming] = None
        self.last: Optional[HtfBar] = None
        self.n_closed = 0
        self.started = False


class SessionHtfAggregator:
    """Gộp TUẦN TỰ nhiều khung lớn từ luồng nến LTF đã đóng, số nến kỳ vọng theo lịch phiên khai báo.

    **Chốt nến** (plan §11.4 [T0]): khi nến LTF có ``close_time`` = ``period_end``; thiếu nến cuối → chốt khi
    nến đầu của kỳ sau tới (``known_at`` > ``period_end``). ``period_end`` = mốc đóng của ô mở cuối cùng
    trong bucket theo lịch (bằng mốc danh nghĩa, trừ ngày đóng sớm / kỳ chứa ngày lễ); không có lịch → mốc
    danh nghĩa. Nến LTF tới sau khi kỳ đã chốt theo lịch nhưng còn trong bucket danh nghĩa (dữ liệu khác
    lịch, vd 2018-11-23 có nến sau giờ đóng sớm) → một kỳ «nối tiếp» riêng, gắn ``outside_calendar`` + ``over``
    và ``degraded`` (lý do ``ngoai_lich``): vài nến lẻ không được thành một nến khung lớn trong cấu trúc.

    **Chất lượng** (R3, D14): ``coverage = n_bars / expected_bars``; ``degraded`` khi ``coverage`` <
    ``min_coverage``, kỳ đầu luồng thiếu nến, hoặc kỳ «nối tiếp»; ``over`` khi nhiều nến hơn lịch (chỉ gắn cờ);
    ``after_hole`` khi giữa nến chốt trước và nến này có ô mở theo lịch mà không có nến nào (mất trọn
    bucket — «hole»). Bucket không có nến nào không tồn tại.

    Không tự bù nến; không đọc OHLC của kỳ trước khi nó chốt (kỳ đang hình thành chỉ có ở ``forming``).
    """

    def __init__(self, ltf_seconds: int, frames: tuple[str, ...], alignment: str = ALIGNMENT_NY_1700,
                 calendar: Any = None, min_coverage: float = 0.9) -> None:
        if alignment != ALIGNMENT_NY_1700:
            raise ValueError("SessionHtfAggregator chỉ hỗ trợ mốc ny_1700 (utc_epoch: HtfAggregator).")
        for f in frames:
            if f not in SESSION_FRAMES:
                raise ValueError("Khung lớn %r không hỗ trợ (chọn trong %s)." % (f, list(SESSION_FRAMES)))
            if SESSION_FRAMES[f] <= ltf_seconds or 3600 % ltf_seconds:
                raise ValueError("Khung lớn %s phải lớn hơn khung %ds, và khung nhỏ phải chia hết 1 giờ."
                                 % (f, ltf_seconds))
        if not 0.0 <= min_coverage <= 1.0:
            raise ValueError("min_coverage phải trong [0, 1].")
        self.ltf = timedelta(seconds=ltf_seconds)
        self._ltf_s = float(ltf_seconds)
        self.frames = tuple(frames)
        self.alignment = alignment
        self.calendar = calendar
        self.min_coverage = min_coverage
        self._opens = [s.open for s in calendar.sessions] if calendar is not None else None
        self.reset()

    def reset(self) -> None:
        self._st = {f: _FrameState() for f in self.frames}
        self._last_open: Optional[float] = None      # giờ mở nến trước (giây Unix)

    def _new(self, start: datetime, nominal_end: datetime, continuation: bool, first: bool,
             bar: Bar, pos: int) -> _Forming:
        if continuation:
            return _Forming(start, nominal_end, nominal_end, 0, None, True, True, first, bar, pos)
        n, first_slot, last_end, by_cal = open_slots(self.calendar, self._opens, start, nominal_end, self.ltf)
        return _Forming(start, nominal_end, last_end if last_end is not None else nominal_end, n, first_slot,
                        by_cal, False, first, bar, pos)

    def _close(self, f: str, st: _FrameState, cur: _Forming, bar: Bar, pos: int) -> HtfBar:
        prev = st.last
        exp = cur.expected
        cov = (cur.n / exp) if exp else None
        reason = None
        if cur.continuation:
            reason = "ngoai_lich"           # chỉ gồm nến sau mốc đóng theo lịch — không phải một nến khung lớn hợp lệ
        elif cur.first_in_stream and cur.n < exp:
            reason = "ky_dau_thieu"
        elif cov is not None and cov < self.min_coverage:
            reason = "coverage_thap"
        hole = (prev is not None and not cur.continuation and cur.start > prev.nominal_end
                and open_slots(self.calendar, self._opens, prev.nominal_end, cur.start, self.ltf)[0] > 0)
        hb = HtfBar(
            index=st.n_closed, bar_time=cur.start, close_time=cur.period_end,
            open=cur.open, high=cur.high, low=cur.low, close=cur.close, volume=0.0,
            frame=f, nominal_end=cur.nominal_end, known_index=bar.index, known_pos=pos, known_at=bar.close_time,
            n_bars=cur.n, expected_bars=exp, coverage=cov, by_calendar=cur.by_calendar,
            degraded=reason is not None, degraded_reason=reason, over=cur.n > exp,
            outside_calendar=cur.continuation, after_hole=hole,
            contiguous_prev=(prev is not None and not cur.continuation and cur.start == prev.close_time),
            first_in_stream=cur.first_in_stream,
            first_bar=cur.first_bar, high_bar=cur.high_bar, low_bar=cur.low_bar,
            first_pos=cur.first_pos, high_pos=cur.high_pos, low_pos=cur.low_pos, last_index=cur.last_index,
        )
        cur.closed = True
        st.last = hb
        st.n_closed += 1
        return hb

    def push(self, bar: Bar, pos: int) -> list[HtfBar]:
        """Nạp nến LTF đã đóng (``pos`` = vị trí trong luồng). Trả các nến khung lớn vừa CHỐT tại nến này,
        theo thứ tự khung khai báo; trong một khung: kỳ chốt muộn trước, kỳ chốt đúng giờ sau."""
        ct = bar.close_time.timestamp()
        ot = ct - self._ltf_s
        if self._last_open is not None and ot <= self._last_open:
            raise ValueError("Nến #%d không tăng dần thời gian." % bar.index)
        self._last_open = ot
        out: list[HtfBar] = []
        for f in self.frames:
            st = self._st[f]
            cur = st.cur
            st.started = False
            if cur is None or ot >= cur.end_ts:
                if cur is not None and not cur.closed:
                    out.append(self._close(f, st, cur, bar, pos))          # chốt muộn: biết khi kỳ sau mở
                start, nominal_end = bucket_bounds(bar.close_time - self.ltf, f, self.alignment)
                cur = st.cur = self._new(start, nominal_end, False, cur is None, bar, pos)
                st.started = True
            elif cur.closed:                                               # dữ liệu sau mốc đóng theo lịch
                cur = st.cur = self._new(cur.start, cur.nominal_end, True, False, bar, pos)
            else:                                                          # cùng kỳ (= _Forming.add, viết gọn)
                if bar.high > cur.high:                                    # strict: giữ nến ĐẦU TIÊN đạt high
                    cur.high, cur.high_bar, cur.high_pos = bar.high, bar, pos
                if bar.low < cur.low:
                    cur.low, cur.low_bar, cur.low_pos = bar.low, bar, pos
                cur.close = bar.close
                cur.last_index = bar.index
                cur.n += 1
            if ct > cur.end_ts:
                raise ValueError("Nến #%d (mở %s) vắt qua mốc đóng nến %s %s — dữ liệu lệch lưới."
                                 % (bar.index, (bar.close_time - self.ltf).isoformat(), f,
                                    cur.nominal_end.isoformat()))
            if not cur.closed and ct >= cur.period_end_ts:
                out.append(self._close(f, st, cur, bar, pos))              # chốt đúng mốc đóng theo lịch
        return out

    def started(self, frame: str) -> bool:
        """Nến vừa nạp mở một kỳ mới (không tính kỳ «nối tiếp»)."""
        return self._st[frame].started

    def current(self, frame: str) -> Optional[_Forming]:
        return self._st[frame].cur

    def last(self, frame: str) -> Optional[HtfBar]:
        return self._st[frame].last

    def n_closed(self, frame: str) -> int:
        return self._st[frame].n_closed

    def forming(self, frame: str) -> Optional[dict[str, Any]]:
        """Kỳ đang hình thành (chưa chốt) — chỉ để vẽ có nhãn; ``None`` nếu kỳ hiện tại đã chốt."""
        cur = self._st[frame].cur
        return None if cur is None or cur.closed else cur.snapshot()
