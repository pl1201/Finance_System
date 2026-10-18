"""[T2] Mức theo kỳ: PDH/PDL, PWH/PWL, giá mở ngày, midnight open (plan_ict_structure §11.4, R5, D13).

* **PDH/PDL, PWH/PWL** = high/low của nến ngày / tuần (mốc ``ny_1700``) đã chốt. Biết tại ``known_at`` của kỳ,
  hiệu lực từ nến sau. Kỳ ``degraded`` (kể cả kỳ đầu luồng thiếu nến) **không** tạo mức: mức của kỳ đó là
  ``None`` cho tới khi kỳ sau chốt. Khi ``period_levels`` bật, thuật toán đưa mỗi mức vào sổ thanh khoản
  (tầng ``D`` / ``W``) và ghi vùng ở đây để biết «đã bị lấy chưa».
* **Giá mở ngày** = open của nến khung chạy ĐẦU TIÊN của ngày giao dịch, chỉ khi nến đó mở đúng ô mở đầu
  tiên theo lịch (thường 18:00 NY — lúc 17:00 nghỉ). Thiếu nến đầu ngày → ``None`` (không lấy giá thay thế).
  Biết tại close nến đó.
* **Midnight open** = open của nến khung chạy mở đúng 00:00 New York của ngày giao dịch. Không có nến đó →
  ``None``, không lấy giá thay thế. Trước 00:00 NY của ngày (18:00–24:00) → ``None``. Biết tại close nến đó.

Thành phần chỉ giữ trạng thái; không phát sự kiện (thuật toán phát ``HTF_PERIOD_*``).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from core.components.liquidity import Pool
from core.data.htf_stream import NY_TZ, HtfBar

NAMES = {("D", "high"): "PDH", ("D", "low"): "PDL", ("W", "high"): "PWH", ("W", "low"): "PWL"}


class PeriodLevels:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        #: khung → {"bar": HtfBar, "high", "low", "pool": {"high": Pool|None, "low": Pool|None},
        #:          "taken_before": {"high": bool, "low": bool}} hoặc {"bar": HtfBar, "degraded": True}
        self.levels: dict[str, Optional[dict[str, Any]]] = {"D": None, "W": None}
        self.day_open: Optional[float] = None
        self.day_open_index: Optional[int] = None
        self.midnight_open: Optional[float] = None
        self.midnight_index: Optional[int] = None
        self._midnight_utc: Optional[datetime] = None   # 00:00 NY của ngày giao dịch hiện tại (UTC)
        #: tăng mỗi khi mức / giá mở đổi — khoá cache ngữ cảnh của thuật toán
        self.rev = 0
        self.counts = {"D": {"ky": 0, "degraded": 0}, "W": {"ky": 0, "degraded": 0},
                       "ngay_co_gia_mo": 0, "ngay_thieu_gia_mo": 0, "midnight_co": 0}

    def on_period(self, hb: HtfBar) -> bool:
        """Kỳ ngày/tuần vừa chốt. True nếu tạo mức (kỳ không degraded)."""
        c = self.counts[hb.frame]
        c["ky"] += 1
        self.rev += 1
        if hb.degraded:
            c["degraded"] += 1
            # 0.4.2: kỳ ngoài lịch (nối tiếp sau giờ đóng / ô lịch đóng trọn) không thay mức của kỳ thường vừa chốt —
            # PDH/PDL vẫn là của ngày giao dịch trước; kỳ thường thiếu dữ liệu (coverage thấp, kỳ đầu) thì không có mức
            if hb.degraded_reason != "ngoai_lich":
                self.levels[hb.frame] = {"bar": hb, "degraded": True}
            return False
        self.levels[hb.frame] = {"bar": hb, "high": hb.high, "low": hb.low, "pool": {"high": None, "low": None},
                                 "taken_before": {"high": False, "low": False}}
        return True

    def set_pool(self, frame: str, side: str, pool: Optional[Pool], taken_before: bool) -> None:
        lv = self.levels[frame]
        lv["pool"][side] = pool
        lv["taken_before"][side] = taken_before
        self.rev += 1

    def on_bar(self, open_time: datetime, bar_open: float, index: int, day_started: bool,
               first_slot: Optional[datetime], day_start: Optional[datetime]) -> None:
        """Nến khung chạy vừa đóng (giờ mở ``open_time``). ``day_started``: nến này mở một ngày giao dịch mới
        (``day_start`` = mốc mở danh nghĩa 17:00 NY, UTC); ``first_slot``: ô mở đầu tiên của ngày theo lịch (hoặc
        mốc mở danh nghĩa khi không có lịch)."""
        if day_started:
            ok = first_slot is not None and open_time == first_slot
            self.day_open = bar_open if ok else None
            self.day_open_index = index if ok else None
            self.counts["ngay_co_gia_mo" if ok else "ngay_thieu_gia_mo"] += 1
            self.midnight_open = None
            self.midnight_index = None
            # 00:00 NY = 17:00 NY mở ngày + 7 giờ đồng hồ (đổi giờ chỉ xảy ra lúc 02:00 Chủ nhật — sau nửa đêm)
            self._midnight_utc = ((day_start.astimezone(NY_TZ) + timedelta(hours=7)).astimezone(timezone.utc)
                                  if day_start is not None else None)
            self.rev += 1
        if open_time == self._midnight_utc:
            self.midnight_open = bar_open
            self.midnight_index = index
            self.counts["midnight_co"] += 1
            self.rev += 1

    def _side(self, frame: str, side: str, track: bool) -> tuple[Optional[float], Optional[bool]]:
        lv = self.levels[frame]
        if lv is None or lv.get("degraded"):
            return None, None
        level = lv[side]
        if not track:
            return level, None
        pool = lv["pool"][side]
        if pool is None:
            return level, bool(lv["taken_before"][side])
        return level, pool.state != "intact"

    def context(self, track: bool) -> dict[str, Any]:
        """``details.htf.levels`` (plan §11.5; thêm PWH/PWL). ``track`` = mức là vùng thanh khoản (biết «đã lấy»)."""
        pdh, pdh_t = self._side("D", "high", track)
        pdl, pdl_t = self._side("D", "low", track)
        pwh, pwh_t = self._side("W", "high", track)
        pwl, pwl_t = self._side("W", "low", track)
        return {
            "pdh": pdh, "pdl": pdl, "pdh_taken": pdh_t, "pdl_taken": pdl_t,
            "pwh": pwh, "pwl": pwl, "pwh_taken": pwh_t, "pwl_taken": pwl_t,
            "day_open": self.day_open, "midnight_open": self.midnight_open,
        }

    def snapshot(self, track: bool) -> dict[str, Any]:
        out = self.context(track)
        for f in ("D", "W"):
            lv = self.levels[f]
            if lv is None:
                out["ky_" + f] = None
                continue
            d = {"nen": lv["bar"].brief(), "degraded": bool(lv.get("degraded"))}
            if not lv.get("degraded"):
                d["vung"] = {s: (lv["pool"][s].brief() if lv["pool"][s] is not None else None) for s in ("high", "low")}
            out["ky_" + f] = d
        out["day_open_nen"] = self.day_open_index
        out["midnight_open_nen"] = self.midnight_index
        return out
