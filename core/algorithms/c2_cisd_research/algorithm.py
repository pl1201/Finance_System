"""C2 Sweep + CISD — bản nghiên cứu closed-bar M15–H4.

Chuyển thể (không phải port tương đương realtime) từ indicator Pine
"Open Source Fractal" của CantoLab, commit
``1bb53262deba9456f2b1a85d15c6ac5a5e880cf7``
(https://github.com/cantolab/open-source-fractal).

Giấy phép của mã nguồn gốc (giữ nguyên văn):

    MIT License

    Copyright (c) 2026 cantolab

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

    (Bản sao: ``third_party/open-source-fractal/LICENSE``.)

Đặc tả, timeline tính tay và bảng khác biệt với Pine:
``docs/thuat_toan_c2_cisd.md``. Tóm tắt thứ tự xử lý tại MỖI nến M15 t:

1. Kiểm tra nến (M15, đúng lưới 15 phút). Nến không liền nến trước → gap:
   setup đang mở kết thúc ``SETUP_DATA_GAP``, xoá mức CISD và lịch sử LTF.
2. Nạp nến vào aggregator H4; báo ``HTF_BUCKET_INCOMPLETE``. Nến đầu kỳ mới:
   setup đang ở C3 chuyển C4, tính cạnh T-Spot C4 = (mid C3, open nến này).
3. Kiểm tra setup: phá cực trị (low/high[t]) → C4 invalid (close[t-1]) →
   xác nhận CISD (close[t-1] so với mức của setup). Đúng thứ tự Pine.
4. Theo dõi reclaim mức CISD: close[t-1] so với mức CÓ HIỆU LỰC CUỐI nến t-1.
5. Cập nhật mức CISD bằng nến t (nhánh trực tiếp / tìm ngược 2–10 / dự phòng).
6. Nến t là nến cuối của kỳ H4 đủ nến: hết hạn setup có C4 = kỳ này, rồi
   xét C2 (C1 = kỳ trước, phải đủ nến và liền kề) và tạo setup.

Không dùng dữ liệu sau nến t. Không sửa sự kiện đã phát. Không T-Spot vẽ,
projections, cảnh báo hay đặt lệnh.
"""
from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
from typing import Any, Optional

from core.algorithms.base import ParamSpec, StructureAlgorithm
from core.algorithms.c2_cisd_research.eval_targets import EVAL_TARGETS
from core.algorithms.c2_cisd_research.levels import select_cisd_level
from core.algorithms.c2_cisd_research.metrics import excursion_metrics, lifecycle_metrics
from core.algorithms.c2_cisd_research.state import (
    PHASE_C3,
    PHASE_C4,
    SCAN_MAX,
    SOURCE_COMMIT,
    SOURCE_REPO,
    SUPPORTED_PAIRS,
    CisdLevel,
    Setup,
    bar_doji,
    iso,
    time_key,
)
from core.data.htf_stream import ALIGNMENT_UTC_EPOCH, HtfAggregator, HtfBucket
from core.types import TIMEFRAME_SECONDS, Bar, ReasonCode, StructureEvent, StructureType


class C2CisdResearchAlgorithm(StructureAlgorithm):
    name = "c2_cisd_research"
    display_name_vi = "C2 Sweep + CISD (nghiên cứu, M15–H4)"
    version = "0.1.0"
    description_vi = (
        "Bản nghiên cứu closed-bar chuyển thể từ CantoLab Open Source Fractal "
        "(MIT, commit 1bb5326): C2 quét low/high H4 rồi đóng lại, mức CISD trên "
        "M15, early CISD, vòng đời C3/C4. Chỉ M15 + H4 mốc UTC epoch. Chưa xác "
        "minh parity với Pine; không phải tín hiệu giao dịch."
    )
    emits_types = (
        StructureType.C2_CONFIRMED_UP, StructureType.C2_CONFIRMED_DOWN,
        StructureType.CISD_CONFIRMED_UP, StructureType.CISD_CONFIRMED_DOWN,
    )
    #: C2 neo ở nến cực trị; CISD neo ở nến có close vượt mức.
    label_types = emits_types
    eval_targets = EVAL_TARGETS

    @classmethod
    def param_specs(cls):
        return (
            ParamSpec("ltf", "Khung nhỏ (LTF)", "choice", "M15", choices=("M15",),
                      help_vi="MVP chỉ hỗ trợ M15. Dataset phải là M15."),
            ParamSpec("htf", "Khung lớn (HTF)", "choice", "H4", choices=("H4",),
                      help_vi="MVP chỉ hỗ trợ H4, mốc kỳ theo UTC epoch (00,04,08,…)."),
            ParamSpec("bias", "Bias lọc hướng", "choice", "Neutral",
                      choices=("Neutral", "Bullish", "Bearish"),
                      help_vi="Lọc do người chọn, KHÔNG phải bias suy luận. "
                              "Bullish chỉ tạo setup tăng; Bearish chỉ setup giảm."),
        )

    @classmethod
    def check_dataset(cls, timeframe: str, params: dict[str, Any]) -> None:
        tf = (timeframe or "").upper()
        if tf != params.get("ltf", "M15"):
            raise ValueError(
                "c2_cisd_research cần dataset %s (dataset này là %s). Không tự "
                "tổng hợp/tách nến." % (params.get("ltf", "M15"), timeframe)
            )

    @classmethod
    def manifest_info(cls, params: dict[str, Any]) -> dict[str, Any]:
        return {
            "ltf": params.get("ltf", "M15"),
            "htf": params.get("htf", "H4"),
            "htf_alignment": ALIGNMENT_UTC_EPOCH,
            "htf_alignment_vi": "Kỳ H4 mở tại bội số 4 giờ tính từ Unix epoch (UTC). "
                                "Chưa đối chiếu với mốc H4 của broker/TradingView.",
            "bias": params.get("bias", "Neutral"),
            "nguon": {"repo": SOURCE_REPO, "commit": SOURCE_COMMIT, "license": "MIT",
                      "copyright": "Copyright (c) 2026 cantolab"},
            "parity_pine": "CHƯA XÁC MINH",
            "spec": "docs/thuat_toan_c2_cisd.md",
        }

    @classmethod
    def evaluation_metrics(cls, events, bars, **options):
        """Vòng đời setup + MFE/MAE đối chứng C2-only vs C2+CISD (``horizon`` nến M15, mặc định 16)."""
        try:
            horizon = int(options.get("horizon", 16))
        except (TypeError, ValueError) as exc:
            raise ValueError("Horizon phải là số nguyên.") from exc
        if not 1 <= horizon <= 500:
            raise ValueError("Horizon phải trong 1–500 nến.")
        return {
            "vong_doi": lifecycle_metrics(events),
            "mfe_mae": excursion_metrics(events, bars, horizon),
        }

    def __init__(self, **params):
        p = self.validate_params(params)
        if (p["ltf"], p["htf"]) not in SUPPORTED_PAIRS:
            raise ValueError("Cặp khung %s–%s chưa hỗ trợ." % (p["ltf"], p["htf"]))
        self.params = p
        self.ltf_seconds = TIMEFRAME_SECONDS[p["ltf"]]
        self.htf_seconds = TIMEFRAME_SECONDS[p["htf"]]
        self.allow_up = p["bias"] != "Bearish"
        self.allow_down = p["bias"] != "Bullish"
        self._ltf = timedelta(seconds=self.ltf_seconds)
        self.reset()

    # ------------------------------------------------------------------ state

    def reset(self) -> None:
        self._agg = HtfAggregator(self.ltf_seconds, self.htf_seconds)
        self._bars: dict[int, Bar] = {}
        self._hist: deque[Bar] = deque(maxlen=SCAN_MAX + 1)
        self._last_open: Optional[datetime] = None
        self._cur: Optional[HtfBucket] = None
        self._prev: Optional[HtfBucket] = None     # kỳ trước: đủ nến & liền kề
        self._levels: dict[str, Optional[CisdLevel]] = {"up": None, "down": None}
        self._level_rev = {"up": 0, "down": 0}
        self._active: dict[str, Optional[Setup]] = {"up": None, "down": None}
        self._n_gaps = 0
        self._n_incomplete = 0
        self._n_complete = 0

    def warmup_bars(self) -> int:
        # C1 và C2 phải là hai kỳ H4 đủ nến → ít nhất 2 × 16 nến M15.
        return 2 * (self.htf_seconds // self.ltf_seconds)

    # ------------------------------------------------------------- helpers

    def _ev(
        self, stype: str, bar: Bar, *, price: float, event_bar: int, reason: str,
        key: str, direction: Optional[str] = None, ref: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> StructureEvent:
        eb = self._bars[event_bar]
        d = {
            "observed_bar_index": bar.index,
            "observed_at": iso(bar.close_time),
            "htf": self.params["htf"],
            "ltf": self.params["ltf"],
            "htf_alignment": ALIGNMENT_UTC_EPOCH,
        }
        if details:
            d.update(details)
        return StructureEvent(
            event_id="c2cisd:%s:%d:%s" % (stype, bar.index, key),
            structure_type=stype,
            price=float(price),
            event_bar_index=event_bar,
            event_time=eb.bar_time,
            event_close_time=eb.close_time,
            confirmed_bar_index=bar.index,
            confirmed_at=bar.close_time,
            algorithm=self.name,
            algorithm_version=self.version,
            reason_code=reason,
            direction=direction,
            reference_event_id=ref,
            details=d,
        )

    def _setup_details(self, s: Setup) -> dict[str, Any]:
        return {
            "setup_id": s.setup_id,
            "phase": s.phase,
            "c2_start": iso(s.c2_start),
            "extreme": s.extreme,
            "extreme_bar_index": s.extreme_bar,
            "cisd_level": s.level,
            "cisd_level_source_bar_index": s.level_source_bar,
            "cisd_level_revision": s.level_revision,
            "cisd_confirmed": s.cisd_confirmed,
            "cisd_confirmed_in_c4": s.cisd_confirmed_in_c4,
            "c4_top": s.c4_top,
            "c4_bottom": s.c4_bottom,
            "c4_invalid": s.c4_invalid,
        }

    def _check_bar(self, bar: Bar) -> datetime:
        span = (bar.close_time - bar.bar_time).total_seconds()
        if span not in (0, self.ltf_seconds):
            raise ValueError(
                "Nến #%d không phải %s (bar_time→close_time = %ds)."
                % (bar.index, self.params["ltf"], span)
            )
        if int(bar.close_time.timestamp()) % self.ltf_seconds:
            raise ValueError(
                "Nến #%d đóng lúc %s không nằm trên lưới %s UTC."
                % (bar.index, bar.close_time.isoformat(), self.params["ltf"])
            )
        return bar.close_time - self._ltf

    # ------------------------------------------------------------- on_bar

    def on_bar(self, bar: Bar) -> list[StructureEvent]:
        open_time = self._check_bar(bar)
        out: list[StructureEvent] = []

        # 1. gap LTF
        if self._last_open is not None:
            if open_time <= self._last_open:
                raise ValueError("Nến #%d không tăng dần thời gian." % bar.index)
            if open_time != self._last_open + self._ltf:
                self._n_gaps += 1
                self._on_gap(bar, open_time, out)
        self._last_open = open_time
        self._bars[bar.index] = bar

        # 2. aggregator H4
        res = self._agg.push(bar.index, open_time, bar.open, bar.high, bar.low, bar.close)
        for bk in res.newly_incomplete:
            self._n_incomplete += 1
            ev_bar = min(bk.last_bar_index, bar.index)
            out.append(self._ev(
                StructureType.HTF_BUCKET_INCOMPLETE, bar, price=bk.close,
                event_bar=ev_bar, reason=ReasonCode.HTF_BUCKET_MISSING_BARS,
                key=time_key(bk.start),
                details={
                    "bucket_start": iso(bk.start), "bucket_end": iso(bk.end),
                    "n_bars_seen": bk.n_bars, "expected_bars": bk.expected_bars,
                    "first_bar_index": bk.first_bar_index,
                    "last_bar_index_seen": bk.last_bar_index,
                },
            ))
        if res.started_new_bucket:
            prev = res.previous
            self._prev = prev if (prev is not None and prev.complete and res.previous_adjacent) else None
            self._advance_phases(bar, res.current)
        self._cur = res.current
        self._hist.append(bar)
        prev_bar = self._hist[-2] if len(self._hist) >= 2 else None

        # 3. setup: phá cực trị → C4 invalid → xác nhận CISD
        for d in ("up", "down"):
            self._check_breach(bar, d, out)
        for d in ("up", "down"):
            self._check_c4_invalid(bar, prev_bar, d, out)
        for d in ("up", "down"):
            self._check_cisd(bar, prev_bar, d, out)

        # 4. reclaim mức đang theo dõi (mức có hiệu lực cuối nến t-1)
        for d in ("up", "down"):
            self._track_reclaim(bar, prev_bar, d, out)

        # 5. cập nhật mức CISD bằng nến t
        for d in ("up", "down"):
            self._update_level(bar, d, out)

        # 6. kỳ H4 vừa hoàn tất
        if res.completed_now:
            self._n_complete += 1
            self._on_bucket_complete(bar, res.current, out)
        return out

    # ------------------------------------------------------------- steps

    def _terminate(self, bar: Bar, d: str, stype: str, reason: str, *,
                   price: float, event_bar: int, ref: Optional[str] = None,
                   extra: Optional[dict[str, Any]] = None,
                   out: list[StructureEvent]) -> None:
        s = self._active[d]
        assert s is not None
        det = self._setup_details(s)
        det["terminal"] = True
        if extra:
            det.update(extra)
        out.append(self._ev(stype, bar, price=price, event_bar=event_bar, reason=reason,
                            key=s.setup_id, direction=d, ref=ref or s.c2_event_id,
                            details=det))
        self._active[d] = None

    def _on_gap(self, bar: Bar, open_time: datetime, out: list[StructureEvent]) -> None:
        gap_info = {
            "gap_after_bar_open": iso(self._last_open) if self._last_open else None,
            "gap_resume_bar_open": iso(open_time),
            "missing_ltf_bars": int((open_time - self._last_open).total_seconds()
                                    // self.ltf_seconds) - 1 if self._last_open else None,
        }
        # nến hiện tại chưa vào self._bars → dùng nến trước làm event_bar
        self._bars[bar.index] = bar
        for d in ("up", "down"):
            s = self._active[d]
            if s is not None:
                self._terminate(bar, d, StructureType.SETUP_DATA_GAP, ReasonCode.SETUP_LTF_GAP,
                                price=s.extreme, event_bar=bar.index, extra=gap_info, out=out)
        self._levels = {"up": None, "down": None}
        self._hist.clear()
        self._prev = None

    def _advance_phases(self, bar: Bar, cur: HtfBucket) -> None:
        prev = self._prev
        for d in ("up", "down"):
            s = self._active[d]
            if s is None or s.phase != PHASE_C3:
                continue
            if cur.index == s.c4_bucket_index and prev is not None and prev.index == s.c3_bucket_index:
                mid = (prev.high + prev.low) / 2.0
                s.phase = PHASE_C4
                s.c4_top = max(bar.open, mid)
                s.c4_bottom = min(bar.open, mid)
                s.c4_start_bar = bar.index
                s.c4_invalid = False

    def _check_breach(self, bar: Bar, d: str, out: list[StructureEvent]) -> None:
        s = self._active[d]
        if s is None:
            return
        breach = bar.low < s.extreme if s.is_bull else bar.high > s.extreme
        if breach:
            self._terminate(bar, d, StructureType.SETUP_INVALIDATED, ReasonCode.SETUP_EXTREME_BREACHED,
                            price=s.extreme, event_bar=bar.index,
                            extra={"breach_price": bar.low if s.is_bull else bar.high},
                            out=out)

    def _check_c4_invalid(self, bar: Bar, prev_bar: Optional[Bar], d: str,
                          out: list[StructureEvent]) -> None:
        s = self._active[d]
        if s is None or s.phase != PHASE_C4 or s.c4_invalid or prev_bar is None:
            return
        invalid = prev_bar.close < s.c4_bottom if s.is_bull else prev_bar.close > s.c4_top
        if not invalid:
            return
        s.c4_invalid = True
        edge = s.c4_bottom if s.is_bull else s.c4_top
        evidence = {"evidence_bar_index": prev_bar.index,
                    "evidence_close": prev_bar.close,
                    "evidence_close_time": iso(prev_bar.close_time)}
        if s.cisd_confirmed_in_c4:
            self._terminate(bar, d, StructureType.SETUP_INVALIDATED,
                            ReasonCode.SETUP_C4_FAIL_AFTER_CISD_IN_C4,
                            price=edge, event_bar=prev_bar.index, ref=s.cisd_event_id,
                            extra=evidence, out=out)
            return
        det = self._setup_details(s)
        det.update(evidence)
        det["terminal"] = False
        out.append(self._ev(StructureType.SETUP_C4_INVALIDATED, bar, price=edge,
                            event_bar=prev_bar.index, reason=ReasonCode.C4_CLOSE_BEYOND_TSPOT,
                            key=s.setup_id, direction=d, ref=s.c2_event_id, details=det))

    def _check_cisd(self, bar: Bar, prev_bar: Optional[Bar], d: str,
                    out: list[StructureEvent]) -> None:
        s = self._active[d]
        if s is None or s.cisd_confirmed or s.level is None or prev_bar is None:
            return
        ok = prev_bar.close > s.level if s.is_bull else prev_bar.close < s.level
        if not ok:
            return
        s.cisd_confirmed = True
        s.cisd_confirmed_in_c4 = s.phase == PHASE_C4
        stype = StructureType.CISD_CONFIRMED_UP if s.is_bull else StructureType.CISD_CONFIRMED_DOWN
        det = self._setup_details(s)
        det.update({
            "early": False,
            "confirm_phase": s.phase,
            "evidence_bar_index": prev_bar.index,
            "evidence_close": prev_bar.close,
            "evidence_close_time": iso(prev_bar.close_time),
            "delay_bars_from_c2": bar.index - s.created_bar,
            "cisd_level_event_id": s.level_event_id,
        })
        ev = self._ev(stype, bar, price=s.level, event_bar=prev_bar.index,
                      reason=ReasonCode.CISD_CLOSE_BEYOND_LEVEL, key=s.setup_id,
                      direction=d, ref=s.c2_event_id, details=det)
        s.cisd_event_id = ev.event_id
        out.append(ev)

    def _track_reclaim(self, bar: Bar, prev_bar: Optional[Bar], d: str,
                       out: list[StructureEvent]) -> None:
        lv = self._levels[d]
        if lv is None or lv.reclaimed or prev_bar is None:
            return
        # Chỉ close của nến ĐÃ đóng SAU lúc mức được xác lập mới tính.
        if prev_bar.index < lv.set_bar:
            return
        ok = prev_bar.close > lv.price if d == "up" else prev_bar.close < lv.price
        if not ok:
            return
        lv.reclaimed = True
        lv.reclaim_evidence_bar = prev_bar.index
        lv.reclaim_observed_bar = bar.index
        cur, prev = self._cur, self._prev
        if cur is None or prev is None or not cur.contiguous:
            return
        swept = cur.low < prev.low if d == "up" else cur.high > prev.high
        if not swept:
            return
        stype = StructureType.EARLY_CISD_UP if d == "up" else StructureType.EARLY_CISD_DOWN
        cand = "%s-%s" % (d, time_key(cur.start))
        ev = self._ev(stype, bar, price=lv.price, event_bar=prev_bar.index,
                      reason=ReasonCode.EARLY_CISD_RECLAIM_IN_SWEEP, key=cand,
                      direction=d, ref=lv.event_id, details={
                          "candidate_id": cand,
                          "candidate_bucket_start": iso(cur.start),
                          "cisd_level": lv.price,
                          "cisd_level_id": lv.level_id,
                          "cisd_level_source_bar_index": lv.source_bar,
                          "cisd_level_revision": lv.revision,
                          "evidence_bar_index": prev_bar.index,
                          "evidence_close": prev_bar.close,
                          "evidence_close_time": iso(prev_bar.close_time),
                          "note_vi": "Ứng viên — chỉ thành CISD của setup nếu kỳ này đóng thành C2.",
                      })
        lv.early_event_id = ev.event_id
        out.append(ev)

    def _update_level(self, bar: Bar, d: str, out: list[StructureEvent]) -> None:
        cur, prev = self._cur, self._prev
        # l1 phải từ kỳ trước đủ nến & liền kề; kỳ hiện tại chưa thiếu nến nào.
        if cur is None or prev is None or not cur.contiguous:
            return
        h = list(self._hist)  # h[-1] = nến t, h[-1-i] = nến [i]
        t = h[-1]
        bull = d == "up"
        if bull:
            if not (t.low == cur.low and t.low < prev.low):
                return
        else:
            if not (t.high == cur.high and t.high > prev.high):
                return

        choice = select_cisd_level(h, bull)
        if choice is None:
            return
        level, idx, branch, scan_i = choice
        old = self._levels[d]
        if old is not None and old.source_bar == idx:
            return                          # Pine: index không đổi → không phải mức mới
        self._level_rev[d] += 1
        rev = self._level_rev[d]
        stype = StructureType.CISD_LEVEL_SET_UP if bull else StructureType.CISD_LEVEL_SET_DOWN
        reason = {
            "truc_tiep": ReasonCode.CISD_LEVEL_DIRECT,
            "tim_nguoc": ReasonCode.CISD_LEVEL_SCAN,
        }.get(branch, ReasonCode.CISD_LEVEL_FALLBACK)
        ev = self._ev(stype, bar, price=level, event_bar=idx, reason=reason,
                      key="%s-r%d" % (d, rev), direction=d,
                      ref=old.event_id if old else None, details={
                          "cisd_level_id": "L%d@%d" % (idx, bar.index),
                          "revision": rev,
                          "branch": branch,
                          "scan_i": scan_i,
                          "trigger_bar_index": bar.index,
                          "trigger_extreme": t.low if bull else t.high,
                          "bucket_start": iso(cur.start),
                          "prev_bucket_extreme": prev.low if bull else prev.high,
                          "doji_trigger": bar_doji(t),
                          "previous_level": old.price if old else None,
                          "previous_level_reclaimed": old.reclaimed if old else None,
                      })
        out.append(ev)
        self._levels[d] = CisdLevel(price=level, source_bar=idx, set_bar=bar.index,
                                 branch=branch, revision=rev, event_id=ev.event_id)

    def _on_bucket_complete(self, bar: Bar, cur: HtfBucket, out: list[StructureEvent]) -> None:
        # a. hết hạn setup có C4 = kỳ vừa đóng
        for d in ("up", "down"):
            s = self._active[d]
            if s is not None and s.phase == PHASE_C4 and s.c4_bucket_index == cur.index:
                self._terminate(bar, d, StructureType.SETUP_EXPIRED, ReasonCode.SETUP_C4_PERIOD_ENDED,
                                price=s.extreme, event_bar=bar.index, out=out)
        # b. C2
        c1 = self._prev
        if c1 is None or c1.index != cur.index - 1:
            return
        bull = cur.low < c1.low and cur.close > c1.low
        bear = cur.high > c1.high and cur.close < c1.high
        outside = bull and bear
        if bull and self.allow_up:
            self._create_setup(bar, "up", c1, cur, outside, out)
        if bear and self.allow_down:
            self._create_setup(bar, "down", c1, cur, outside, out)

    def _create_setup(self, bar: Bar, d: str, c1: HtfBucket, c2: HtfBucket, outside: bool,
                      out: list[StructureEvent]) -> None:
        bull = d == "up"
        setup_id = "%s-%s" % (d, time_key(c2.start))
        c2_type = StructureType.C2_CONFIRMED_UP if bull else StructureType.C2_CONFIRMED_DOWN
        c2_event_id = "c2cisd:%s:%d:%s" % (c2_type, bar.index, setup_id)

        old = self._active[d]
        if old is not None:
            self._terminate(bar, d, StructureType.SETUP_SUPERSEDED, ReasonCode.SETUP_REPLACED_BY_NEW_C2,
                            price=old.extreme, event_bar=bar.index,
                            extra={"superseded_by_setup_id": setup_id,
                                   "superseded_by_event_id": c2_event_id},
                            out=out)

        lv = self._levels[d]
        s = Setup(
            setup_id=setup_id, direction=d,
            extreme=c2.low if bull else c2.high,
            extreme_bar=c2.low_bar_index if bull else c2.high_bar_index,
            c2_bucket_index=c2.index, c2_start=c2.start, created_bar=bar.index,
            c2_event_id=c2_event_id,
            level=lv.price if lv else None,
            level_source_bar=lv.source_bar if lv else None,
            level_revision=lv.revision if lv else None,
            level_event_id=lv.event_id if lv else None,
            outside_bar=outside,
        )
        det = self._setup_details(s)
        det.update({
            "c1_start": iso(c1.start),
            "c1_open": c1.open, "c1_high": c1.high, "c1_low": c1.low, "c1_close": c1.close,
            "c2_end": iso(c2.end),
            "c2_open": c2.open, "c2_high": c2.high, "c2_low": c2.low, "c2_close": c2.close,
            "sweep_from": c1.low if bull else c1.high,
            "sweep_from_bar_index": c1.low_bar_index if bull else c1.high_bar_index,
            "c3_start": iso(c2.end),
            "c4_start": iso(c2.end + timedelta(seconds=self.htf_seconds)),
            "outside_bar_ambiguous": outside,
            "cisd_level_event_id": s.level_event_id,
            "cisd_already_reclaimed": bool(lv and lv.reclaimed),
            "bias": self.params["bias"],
        })
        out.append(self._ev(c2_type, bar, price=s.extreme, event_bar=s.extreme_bar,
                            reason=ReasonCode.C2_SWEEP_LOW_RECLAIM if bull else ReasonCode.C2_SWEEP_HIGH_RECLAIM,
                            key=setup_id, direction=d, ref=s.level_event_id, details=det))
        self._active[d] = s

        # Pine: cisdAlreadyConfirmed = bullReclaimed[1] → xác nhận ngay khi tạo setup.
        if lv is not None and lv.reclaimed:
            s.cisd_confirmed = True
            ev_bar = lv.reclaim_evidence_bar
            cisd_type = StructureType.CISD_CONFIRMED_UP if bull else StructureType.CISD_CONFIRMED_DOWN
            cdet = self._setup_details(s)
            cdet.update({
                "early": True,
                "confirm_phase": "C2",
                "evidence_bar_index": ev_bar,
                "evidence_close": self._bars[ev_bar].close,
                "evidence_close_time": iso(self._bars[ev_bar].close_time),
                "reclaim_observed_bar_index": lv.reclaim_observed_bar,
                "reclaim_before_c2": ev_bar < c2.first_bar_index,
                "evidence_bars_before_c2_end": bar.index - ev_bar,
                "early_cisd_event_id": lv.early_event_id,
                "cisd_level_event_id": lv.event_id,
                "delay_bars_from_c2": 0,
            })
            ev = self._ev(cisd_type, bar, price=lv.price, event_bar=ev_bar,
                          reason=ReasonCode.CISD_ALREADY_RECLAIMED_AT_C2, key=setup_id,
                          direction=d, ref=lv.early_event_id or c2_event_id, details=cdet)
            s.cisd_event_id = ev.event_id
            out.append(ev)

    def run_stats(self, events: list[StructureEvent]) -> Optional[dict[str, Any]]:
        m = lifecycle_metrics(e.to_dict() for e in events)
        m["so_gap_ltf"] = self._n_gaps
        m["so_ky_htf_du"] = self._n_complete
        m["htf_alignment"] = ALIGNMENT_UTC_EPOCH
        return m

    # ------------------------------------------------------------- display

    def pending_state(self) -> dict[str, Any]:
        def lv(d: str) -> Optional[dict[str, Any]]:
            x = self._levels[d]
            if x is None:
                return None
            return {"price": x.price, "source_bar_index": x.source_bar, "set_bar_index": x.set_bar,
                    "branch": x.branch, "revision": x.revision, "reclaimed": x.reclaimed}

        def st(d: str) -> Optional[dict[str, Any]]:
            s = self._active[d]
            return self._setup_details(s) if s is not None else None

        cur = self._cur
        return {
            "setup_dang_mo": {"up": st("up"), "down": st("down")},
            "muc_cisd_dang_theo_doi": {"up": lv("up"), "down": lv("down")},
            "ky_htf_hien_tai": None if cur is None else {
                "start": iso(cur.start), "n_bars": cur.n_bars,
                "expected_bars": cur.expected_bars, "complete": cur.complete,
            },
            "so_gap_ltf": self._n_gaps,
            "so_ky_htf_thieu": self._n_incomplete,
            "so_ky_htf_du": self._n_complete,
            "htf_alignment": ALIGNMENT_UTC_EPOCH,
            "nguon": {"repo": SOURCE_REPO, "commit": SOURCE_COMMIT, "license": "MIT"},
        }

    def timeline_point(self, bar: Bar) -> Optional[dict[str, Any]]:
        def lvp(d: str) -> Optional[float]:
            x = self._levels[d]
            return x.price if x is not None else None

        pt: dict[str, Any] = {"cisd_up": lvp("up"), "cisd_down": lvp("down")}
        for d in ("up", "down"):
            s = self._active[d]
            pt["setup_%s_level" % d] = s.level if s is not None else None
            pt["setup_%s_extreme" % d] = s.extreme if s is not None else None
            pt["setup_%s_phase" % d] = s.phase if s is not None else None
            pt["setup_%s_id" % d] = s.setup_id if s is not None else None
        return pt
