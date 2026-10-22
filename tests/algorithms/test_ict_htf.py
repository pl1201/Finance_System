"""ict_structure v0.4.0 — giai đoạn 3 lõi: khung lớn [T0]–[T3], PD array [S5], DOL [S6] (plan §11.7, §9).

* bộ gộp ``ny_1700`` theo lịch CME khai báo: mốc 17:00 New York trước/sau đổi giờ, giờ nghỉ nằm trong nến H4 đầu
  ngày, tuần Chủ nhật 17:00 → Thứ Sáu 17:00, ngày lễ đóng sớm không degraded, chốt muộn (``period_end`` ≠
  ``known_at``), kỳ đầu thiếu, hole, nến ngoài lịch; ``utc_epoch`` và ``resample`` cũ không đổi;
* quy tắc chất lượng lan truyền trên ngăn xếp khung lớn (tính tay): degraded / hole chặn cửa sổ pivot, bộ ba FVG;
* PD array và DOL (thành phần, tính tay);
* thuật toán trên dữ liệu dựng theo lịch CME: không có PDH/PWH ở kỳ đầu thiếu, midnight open thiếu → null,
  ``details.htf`` đúng khuôn, nhân quả (prefix = full, sửa đuôi trong nến H4 đang hình thành, sự kiện không bị sửa
  ngầm), thứ tự (sự kiện ở nến chốt H4 dùng ngữ cảnh trước lần chốt), tương đương với dataset H4 gộp ``ny_1700``.
"""
from __future__ import annotations

import copy
import random
from datetime import timedelta, timezone

import pytest

from core.algorithms.ict_structure import IctStructureAlgorithm
from core.components.dol import DrawOnLiquidity
from core.components.htf_stack import HtfStack
from core.components.liquidity import LiquidityBook
from core.components.pd_array import PdArrayTracker
from core.data.htf_stream import HtfAggregator, HtfBar, SessionHtfAggregator, bucket_bounds
from core.data.resample import bucket_start_utc, resample_ohlc
from core.data.session_calendar import SessionCalendar
from core.engine import run_algorithm
from core.types import Bar, StructureType, build_bars
from tests.helpers import cal_bars, u

UTC = timezone.utc
M15 = timedelta(minutes=15)
CAL = SessionCalendar.load("cme_globex_metals")
HTF_T = set(StructureType.HTF_TYPES)
NO_CTX = {StructureType.SWING_HIGH, StructureType.SWING_LOW, StructureType.FVG_UP, StructureType.FVG_DOWN,
          StructureType.FVG_TOUCHED, StructureType.FVG_FILLED, StructureType.DISPLACEMENT_UP,
          StructureType.DISPLACEMENT_DOWN,   # 0.4.1: không mang details.htf
          StructureType.OB_EXPIRED, StructureType.OTE_EXPIRED}   # 0.5.0: hết hạn chỉ để vẽ dừng đúng chỗ


def _closed(bars, frames=("H1", "H4", "D", "W"), calendar=CAL, cov=0.9):
    agg = SessionHtfAggregator(int(bars[1].close_time.timestamp() - bars[1].bar_time.timestamp()), frames, "ny_1700",
                               calendar, cov)
    out = []
    for i, b in enumerate(bars):
        out.extend(agg.push(b, i))
    return out, agg


def _p(**kw):
    p = {"timeframe": "M15", "session_calendar": "cme_globex_metals"}
    p.update(kw)
    return p


# ============================================================================ [T0] mốc ny_1700


def test_moc_ny_1700_truoc_va_sau_doi_gio():
    # Thứ Sáu 08/03/2024 (EST, UTC−5): 17:00 NY = 22:00 UTC
    assert bucket_bounds(u(2024, 3, 8, 21, 45), "D", "ny_1700") == (u(2024, 3, 7, 22), u(2024, 3, 8, 22))
    assert bucket_bounds(u(2024, 3, 8, 21, 45), "H4", "ny_1700") == (u(2024, 3, 8, 18), u(2024, 3, 8, 22))
    # Chủ nhật 10/03/2024 sau 02:00 (EDT, UTC−4): 17:00 NY = 21:00 UTC; H4 đầu ngày 17–21 NY
    assert bucket_bounds(u(2024, 3, 10, 22), "D", "ny_1700") == (u(2024, 3, 10, 21), u(2024, 3, 11, 21))
    assert bucket_bounds(u(2024, 3, 10, 22), "H4", "ny_1700") == (u(2024, 3, 10, 21), u(2024, 3, 11, 1))
    assert bucket_bounds(u(2024, 3, 11, 5), "H4", "ny_1700") == (u(2024, 3, 11, 5), u(2024, 3, 11, 9))
    # tuần: Chủ nhật 17:00 NY; tuần có đổi giờ dài 167 giờ danh nghĩa
    s, e = bucket_bounds(u(2024, 3, 6, 12), "W", "ny_1700")
    assert (s, e) == (u(2024, 3, 3, 22), u(2024, 3, 10, 21)) and (e - s) == timedelta(hours=167)
    assert bucket_bounds(u(2024, 3, 11, 12), "W", "ny_1700")[0] == u(2024, 3, 10, 21)
    # 03/11/2024 (về EST): Thứ Sáu 01/11 17:00 NY = 21:00 UTC; Chủ nhật 03/11 17:00 NY = 22:00 UTC
    assert bucket_bounds(u(2024, 11, 1, 20, 45), "D", "ny_1700") == (u(2024, 10, 31, 21), u(2024, 11, 1, 21))
    assert bucket_bounds(u(2024, 11, 3, 23), "D", "ny_1700") == (u(2024, 11, 3, 22), u(2024, 11, 4, 22))
    s, e = bucket_bounds(u(2024, 10, 30, 12), "W", "ny_1700")
    assert (s, e) == (u(2024, 10, 27, 21), u(2024, 11, 3, 22)) and (e - s) == timedelta(hours=169)
    # H1 = giờ tròn (trùng utc_epoch); utc_epoch giữ nguyên quy ước của resample
    assert bucket_bounds(u(2024, 3, 10, 22, 30), "H1", "ny_1700") == (u(2024, 3, 10, 22), u(2024, 3, 10, 23))
    for t in (u(2024, 3, 10, 22, 30), u(2024, 11, 3, 23, 45)):
        assert bucket_bounds(t, "H4", "utc_epoch")[0] == bucket_start_utc(t, "H4")
    with pytest.raises(ValueError):
        bucket_bounds(u(2024, 3, 10, 22), "W", "utc_epoch")


def test_gop_theo_lich_nghi_phien_trong_nen_dau_ngay_tuan_va_doi_gio():
    # hai tuần đủ dữ liệu theo lịch, qua đổi giờ 10/03/2024
    _rows, bars = cal_bars(u(2024, 3, 3, 23), u(2024, 3, 16))
    closed, _agg = _closed(bars)
    by = {f: [h for h in closed if h.frame == f] for f in ("H1", "H4", "D", "W")}
    assert len(by["D"]) == 10 and len(by["W"]) == 2 and len(by["H4"]) == 60
    for h in closed:
        assert not h.degraded and not h.over and not h.after_hole and not h.late and h.coverage == 1.0
        assert h.known_at == h.period_end == h.close_time and h.by_calendar
    for d in by["D"]:                       # 18:00 → 17:00 NY = 92 nến M15; giờ nghỉ 17–18 nằm đầu kỳ
        assert d.expected_bars == 92 and d.bar_time.astimezone(CAL_TZ).hour == 17
    first_h4 = [h for h in by["H4"] if h.bar_time.astimezone(CAL_TZ).hour == 17]
    assert len(first_h4) == 10 and all(h.expected_bars == 12 for h in first_h4)   # 18:00–21:00 NY
    # tuần: Chủ nhật 17:00 → Thứ Sáu 17:00 NY (theo lịch), 5 × 92 nến
    w1, w2 = by["W"]
    assert (w1.close_time, w1.expected_bars) == (u(2024, 3, 8, 22), 460)
    assert w2.close_time == u(2024, 3, 15, 21)                                     # sau đổi giờ: 17:00 EDT
    # liền kề theo lịch: H4 qua ngày liền kề (giờ nghỉ nằm trong nến 17–21); qua cuối tuần thì không;
    # H1 qua giờ nghỉ hằng ngày không liền kề
    h4_mon = [h for h in by["H4"] if h.bar_time == u(2024, 3, 10, 21)][0]
    h4_tue = [h for h in by["H4"] if h.bar_time == u(2024, 3, 11, 21)][0]
    assert not h4_mon.contiguous_prev and h4_tue.contiguous_prev
    h1_18 = [h for h in by["H1"] if h.bar_time == u(2024, 3, 11, 22)][0]           # 18:00 EDT
    assert not h1_18.contiguous_prev and not h1_18.after_hole


CAL_TZ = __import__("zoneinfo").ZoneInfo("America/New_York")


def test_ngay_le_dong_som_khong_degraded_chot_dung_lich_va_khong_lien_ke():
    # 15/01/2024 (MLK): đóng sớm 19:30 UTC (14:30 NY) theo lịch khai báo
    _rows, bars = cal_bars(u(2024, 1, 14, 23), u(2024, 1, 17))
    closed, _agg = _closed(bars)
    d15 = [h for h in closed if h.frame == "D" and h.bar_time == u(2024, 1, 14, 22)][0]
    assert d15.close_time == u(2024, 1, 15, 19, 30) and d15.expected_bars == 82 and d15.coverage == 1.0
    assert not d15.degraded and d15.known_at == d15.close_time and not d15.late
    h4 = [h for h in closed if h.frame == "H4" and h.bar_time == u(2024, 1, 15, 18)][0]
    assert (h4.expected_bars, h4.close_time, h4.degraded) == (6, u(2024, 1, 15, 19, 30), False)
    nxt = [h for h in closed if h.frame == "H4" and h.bar_time == u(2024, 1, 15, 22)][0]
    assert not nxt.contiguous_prev and not nxt.after_hole       # khoảng đóng sớm nằm GIỮA hai nến → không liền kề


def test_chot_muon_period_end_khac_known_at_va_coverage():
    # thiếu nến cuối 16:45–17:00 NY của 05/03/2024 → H4 13–17, H1 16–17, D chốt khi nến 18:00 NY tới
    miss = u(2024, 3, 5, 21, 45)
    _rows, bars = cal_bars(u(2024, 3, 3, 23), u(2024, 3, 7), drop={miss})
    closed, _agg = _closed(bars)
    first_next = [b for b in bars if b.bar_time == u(2024, 3, 5, 23)][0]
    for f, start, exp, deg in (("H4", u(2024, 3, 5, 18), 16, False), ("H1", u(2024, 3, 5, 21), 4, True),
                               ("D", u(2024, 3, 4, 22), 92, False)):
        h = [x for x in closed if x.frame == f and x.bar_time == start][0]
        assert h.close_time == u(2024, 3, 5, 22) and h.known_at == first_next.close_time and h.late, f
        assert h.n_bars == exp - 1 and h.degraded is deg, f
        assert h.known_index == first_next.index
    h1 = [x for x in closed if x.frame == "H1" and x.bar_time == u(2024, 3, 5, 21)][0]
    assert h1.coverage == 0.75 and h1.degraded_reason == "coverage_thap"


def test_ky_dau_thieu_hole_va_nen_ngoai_lich():
    # luồng bắt đầu giữa ngày 05/03 → kỳ đầu (H4, D, W) thiếu → degraded «ky_dau_thieu»
    _rows, bars = cal_bars(u(2024, 3, 5, 15), u(2024, 3, 7))
    closed, _agg = _closed(bars)
    firsts = {h.frame: h for h in closed if h.first_in_stream}
    assert firsts["D"].degraded_reason == "ky_dau_thieu" and firsts["H4"].degraded_reason == "ky_dau_thieu"
    assert not [h for h in closed if h.frame == "D" and not h.first_in_stream][0].degraded
    # mất trọn H1 10:00–11:00 NY ngày 06/03 → H1 sau có after_hole; H4 9–13 còn 12/16 → degraded
    hole = {u(2024, 3, 6, 15) + i * M15 for i in range(4)}
    _rows, bars = cal_bars(u(2024, 3, 3, 23), u(2024, 3, 8), drop=hole)
    closed, _agg = _closed(bars)
    h1 = [h for h in closed if h.frame == "H1" and h.bar_time == u(2024, 3, 6, 16)][0]
    assert h1.after_hole and not h1.contiguous_prev
    h4 = [h for h in closed if h.frame == "H4" and h.bar_time == u(2024, 3, 6, 14)][0]
    assert h4.coverage == 0.75 and h4.degraded and not h4.after_hole
    # có nến SAU giờ đóng sớm theo lịch (dữ liệu khác lịch) → kỳ «nối tiếp» riêng, degraded «ngoai_lich»
    _rows, bars = cal_bars(u(2024, 1, 14, 23), u(2024, 1, 17), extra={u(2024, 1, 15, 19, 30)})
    closed, _agg = _closed(bars)
    d = [h for h in closed if h.frame == "D" and h.bar_time == u(2024, 1, 14, 22)]
    assert [(x.n_bars, x.degraded, x.outside_calendar) for x in d] == [(82, False, False), (1, True, True)]
    assert d[1].degraded_reason == "ngoai_lich" and d[1].over


def test_o_ma_lich_dong_ca_ky_nhung_co_nen_la_ngoai_lich():
    # 0.4.2 (kiểm độc lập F1): MLK 15/01/2024 đóng sớm 19:30 UTC; ô H1 20:00–21:00 UTC lịch đóng trọn (expected 0) mà
    # dữ liệu có nến → nến H1 degraded «ngoai_lich», không thành nến khung lớn hợp lệ (trước đây chỉ gắn cờ over)
    _rows, bars = cal_bars(u(2024, 1, 14, 23), u(2024, 1, 17), extra={u(2024, 1, 15, 20)})
    closed, _agg = _closed(bars)
    h1 = [h for h in closed if h.frame == "H1" and h.bar_time == u(2024, 1, 15, 20)]
    assert len(h1) == 1 and h1[0].expected_bars == 0 and h1[0].n_bars == 1
    assert h1[0].degraded and h1[0].degraded_reason == "ngoai_lich" and h1[0].over
    assert not [h for h in closed if h.frame == "H1" and h.bar_time == u(2024, 1, 15, 18)][0].degraded


def test_ky_ngoai_lich_khong_xoa_pdh_pdl_cua_ky_thuong():
    # 0.4.2 (kiểm độc lập F2): kỳ D «nối tiếp» (nến sau giờ đóng sớm) chốt khi ngày sau mở — không được ghi đè PDH/PDL
    # của kỳ thường vừa xong (trước đây PDH/PDL = None suốt ngày kế tiếp trong khi vùng D vẫn sống)
    _rows, bars = cal_bars(u(2024, 1, 11, 23), u(2024, 1, 18), extra={u(2024, 1, 15, 19, 30)})
    closed, _agg = _closed(bars)
    reg = [h for h in closed if h.frame == "D" and h.bar_time == u(2024, 1, 14, 22) and not h.outside_calendar][0]
    at = [b for b in bars if b.bar_time == u(2024, 1, 16, 12)][0]
    algo = IctStructureAlgorithm(**_p())
    res = run_algorithm(bars, algo, upto_index=at.index)
    lv = algo.pending_state()["khung_lon"]["muc_theo_ky"]
    assert lv["pdh"] == reg.high and lv["pdl"] == reg.low
    assert res.timeline[-1]["pdh_taken"] is not None and res.timeline[-1]["pdl_taken"] is not None


def test_utc_epoch_va_resample_cu_khong_doi():
    """HtfAggregator (utc_epoch, bộ gộp chung) và resample cũ: hành vi giữ nguyên."""
    agg = HtfAggregator(900, 14400)
    r = agg.push(0, u(2024, 3, 5, 4), 1, 2, 0.5, 1.5)
    assert r.current.start == u(2024, 3, 5, 4) and r.current.expected_bars == 16
    rows, _bars = cal_bars(u(2024, 3, 3, 23), u(2024, 3, 6, 22))          # Chủ nhật 18:00 → Thứ Tư 17:00 NY
    out_utc, rep_utc = resample_ohlc(rows, "M15", "H4")
    assert rep_utc.alignment == "utc_epoch" and all(r["bar_time"].hour % 4 == 0 for r in out_utc)
    out_ny, rep_ny = resample_ohlc(rows, "M15", "H4", alignment="ny_1700", gap_policy="emit_available",
                                   calendar=CAL)
    assert {r["bar_time"].astimezone(CAL_TZ).hour for r in out_ny} == {17, 21, 1, 5, 9, 13}
    assert not any(r["incomplete"] for r in out_ny)                 # nến H4 đầu ngày: 12/12 theo lịch
    out_nom, _ = resample_ohlc(rows, "M15", "H4", alignment="ny_1700", gap_policy="emit_available")
    assert sum(r["incomplete"] for r in out_nom) == 3               # không lịch: 12/16 danh nghĩa → thiếu


# ============================================================================ [T1] ngăn xếp: chất lượng lan truyền


def _hb(i, h, lo, degraded=False, hole=False, contiguous=True, o=None, c=None):
    t = u(2024, 3, 4) + i * timedelta(hours=4)
    o = (h + lo) / 2 if o is None else o
    c = (h + lo) / 2 if c is None else c
    return HtfBar(index=i, bar_time=t, close_time=t + timedelta(hours=4), open=o, high=h, low=lo, close=c,
                  frame="H4", known_at=t + timedelta(hours=4), degraded=degraded, after_hole=hole,
                  contiguous_prev=contiguous and i > 0)


def _stack():
    return HtfStack("H4", 1, 1, 2, 0.1, 1.5, 0.6, 0.0)


HIGHS = [10, 12, 11, 14, 12, 13, 11, 12, 10]           # STH @1, @3, @5, @7 → ITH 14 @3, biết khi STH @5 xác nhận (#6)


def _run_stack(bad=None, hole=None):
    st = _stack()
    sw = []
    for i, h in enumerate(HIGHS):
        res = st.on_bar(_hb(i, h, h - 3, degraded=(i == bad), hole=(i == hole)))
        sw.extend((i, q.side, q.price, q.bar.index) for q, _d in res["swings"])
    return st, sw


def test_ngan_xep_ith_tinh_tay_va_degraded_hoac_hole_chan_cua_so():
    st, sw = _run_stack()
    assert ("high", 14, 3) in [(s, p, b) for _i, s, p, b in sw] and [i for i, s, *_r in sw if s == "high"] == [6]
    _st, sw = _run_stack(bad=4)                        # nến 4 degraded: cửa sổ của STH @3 (2–4) và @5 (4–6) bị chặn
    assert not [x for x in sw if x[1] == "high"]
    assert _st.pivots.blocked["high"] == 2 and _st.counts["cua_so_bi_chan"] >= 3
    _st, sw = _run_stack(hole=4)                       # hole trước nến 4: chỉ cửa sổ 2–4 vắt qua (STH @3 mất)
    assert not [x for x in sw if x[1] == "high" and x[2] == 14]
    assert _st.pivots.blocked["high"] == 1


def test_ngan_xep_fvg_can_lien_ke_theo_lich_va_khong_degraded():
    def trio(**kw):
        st = _stack()
        bars = [_hb(0, 10, 9), _hb(1, 13, 9.5, o=9.6, c=12.9, **kw.get("b1", {})), _hb(2, 14, 11, **kw.get("b2", {}))]
        return [st.on_bar(b)["fvg"] for b in bars][-1]
    f = trio()
    assert (f.direction, f.lo, f.hi, f.mid_index) == ("up", 10, 11, 1)
    assert trio(b2={"contiguous": False}) is None      # nến 3 không mở đúng lúc nến 2 đóng (cuối tuần, đóng sớm…)
    assert trio(b1={"degraded": True}) is None         # nến giữa thiếu dữ liệu
    assert trio(b2={"hole": True, "contiguous": False}) is None


# ============================================================================ [S5] PD array, [S6] DOL (tính tay)


def _m15(i, o, h, lo, c):
    t = u(2024, 3, 5, 14) + i * M15
    return Bar(index=i, bar_time=t, close_time=t + M15, open=o, high=h, low=lo, close=c)


@pytest.mark.parametrize("mode, closes, kind, at", [
    ("strict", [101.5, 102.9, 103.0], "respect", 2),     # tap ở #0 (low 99.5 ≤ hi 100); close ≥ 100 + 3 × 1 ở #2
    ("strict", [101.5, 97.9], "disrespect", 1),           # close < mép xa 98
    ("loose", [100.5], "respect", 0),                      # close > hi ngay nến tap
    ("ce", [99.0], None, None),                            # 99 > CE 99 không đúng → chưa có kết quả
    ("ce", [98.9], "disrespect", 0),                       # close < CE 99
])
def test_pd_tap_roi_ket_qua_dau_tien(mode, closes, kind, at):
    pd = PdArrayTracker(mode, 3.0)
    z = pd.add("H1", "up", 98.0, 100.0, known_index=-1, event_id="fvg", from_displacement=False, mid_index=-3)
    got = []
    for i, c in enumerate(closes):
        lo = 99.5 if i == 0 else min(c, 100.5) - 0.1
        got += [(k, i) for k, _z, _x in pd.on_bar(_m15(i, c, max(c, 100.6), lo, c), 1.0)]
    assert got == ([] if kind is None else [(kind, at)])
    assert z.tap_index == 0
    if kind:
        assert z.state == "da_dung" and pd.bias == (1 if kind == "respect" else -1) and pd.bias_tf == "H1"
        assert pd.on_bar(_m15(9, 90, 101, 89, 90), 1.0) == []          # mỗi vùng một kết quả


def test_pd_chua_cham_thi_khong_co_ket_qua_va_hai_chieu_cung_nen_la_0():
    pd = PdArrayTracker("loose", 1.0)
    pd.add("H1", "up", 98.0, 100.0, -1, "a", False, -3)
    assert pd.on_bar(_m15(0, 105, 106, 100.5, 105), 1.0) == [] and pd.bias is None      # chưa chạm: không respect
    pd.add("H4", "down", 103.0, 104.0, 0, "b", True, -2)
    # nến 1: chạm cả hai; close 102.5 → respect FVG giảm (close < 103) và respect FVG tăng (close > 100) → hai chiều
    res = pd.on_bar(_m15(1, 103, 103.5, 99.5, 102.5), 1.0)
    assert sorted((k, z.direction) for k, z, _x in res) == [("respect", "down"), ("respect", "up")]
    assert pd.bias == 0 and pd.bias_tf is None and pd.bias_since == 1


def test_dol_vung_gan_nhat_tang_toi_thieu_dat_va_thay():
    bk = LiquidityBook(0.1, 3, 0.1)
    bk.add("high", 105.0, "M15", "m", 0, 0, 1.0, False)            # tầng M15: không tính
    _s, h1 = bk.add("high", 108.0, "H1", "h1", 0, 0, 1.0, False)
    _s, d = bk.add("high", 110.0, "D", "d", 0, 0, None, False)
    _s, lo = bk.add("low", 95.0, "H4", "l", 0, 0, 1.0, False)
    dol = DrawOnLiquidity("H1")
    assert dol.set_from_shift(bk, 1, 101.0, 2.0, 10, "s1") is h1 and dol.dist_atr_at_set == pytest.approx(3.5)
    assert DrawOnLiquidity("D").set_from_shift(bk, 1, 101.0, 2.0, 10, "s1") is d
    assert DrawOnLiquidity("H1").set_from_shift(bk, 1, 111.0, 2.0, 10, "s1") is None        # không còn vùng phía trên
    assert dol.check_reached([lo]) is None
    got = dol.check_reached([h1])
    assert got["target"] is h1 and got["shift_id"] == "s1" and dol.side is None and dol.counts["dat"] == 1
    dol.set_from_shift(bk, -1, 101.0, 2.0, 12, "s2")
    assert dol.target is lo
    dol.set_from_shift(bk, 1, 101.0, 2.0, 13, "s3")
    assert dol.target is h1 and dol.counts["bi_thay"] == 1                                  # shift mới thay DOL cũ


# ============================================================================ thuật toán trên dữ liệu theo lịch


@pytest.fixture(scope="module")
def cal_run():
    _rows, bars = cal_bars(u(2024, 3, 3, 23), u(2024, 4, 27), seed=11, vol=1.2)
    algo = IctStructureAlgorithm(**_p())
    res = run_algorithm(bars, algo)
    return bars, res, algo


def test_details_htf_dung_khuon_tren_moi_su_kien_khung_chay(cal_run):
    bars, res, _algo = cal_run
    kinds = {e.structure_type for e in res.events}
    assert {"HTF_SWING_HIGH", "HTF_SWING_LOW", "HTF_FVG_UP", "HTF_FVG_DOWN", "HTF_PERIOD_HIGH", "HTF_PERIOD_LOW",
            "DOL_REACHED"} <= kinds
    assert kinds & set(StructureType.PD_TYPES)
    keys_tf = {"ready", "order", "order_age_bars", "protected", "protected_broken", "zone", "range_pos", "liq_above",
               "liq_below", "age_ltf_bars", "coverage_last", "blocked_windows_recent"}
    for e in res.events:
        if e.structure_type in HTF_T:
            assert "htf" not in e.details
            assert {"period_end", "known_at", "coverage"} <= set(e.details)
            continue
        if e.structure_type in NO_CTX:                                  # 0.4.1: sự kiện nguyên liệu không mang htf
            assert "htf" not in e.details
            continue
        x = e.details["htf"]
        assert set(x) == {"alignment", "H1", "H4", "pd_bias", "dol", "levels"} and x["alignment"] == "ny_1700"
        assert set(x["H1"]) == keys_tf and set(x["H4"]) == keys_tf
        assert set(x["pd_bias"]) == {"dir", "tf", "age_ltf_bars"} and set(x["dol"]) == {"side", "target", "tier",
                                                                                          "dist_atr"}
        assert {"pdh", "pdl", "pdh_taken", "pdl_taken", "day_open", "midnight_open"} <= set(x["levels"])
        assert "bias" not in str(sorted(x)).replace("pd_bias", "")         # không có «bias tổng hợp» (B3)
    tl = res.timeline[-1]
    for k in ("htf_H1_order", "htf_H4_order", "htf_H4_zone", "htf_H4_range_pos", "pd_bias", "dol_side", "pdh_taken",
              "pdl_taken", "htf_H4_age"):
        assert k in tl


def test_su_kien_khung_lon_neo_dung_nen_va_vung_hieu_luc_tu_nen_sau(cal_run):
    bars, res, _algo = cal_run
    by_id = {e.event_id: e for e in res.events}
    for e in res.events:
        t = e.structure_type
        if t in ("HTF_SWING_HIGH", "HTF_SWING_LOW", "HTF_PERIOD_HIGH", "HTF_PERIOD_LOW"):
            b = bars[e.event_bar_index]
            assert (b.high if t.endswith("HIGH") else b.low) == e.price     # nến M15 chạm cực trị
            assert e.confirmed_at.isoformat() == e.details["known_at"]
            v = e.details["vung_thanh_khoan"]
            if v["trang_thai"] != "khong_tao":
                assert v["hieu_luc_tu_nen"] == e.confirmed_bar_index + 1
        if t.startswith("LIQ_"):
            for p in e.details["pools"]:
                assert p["nen_lay"] > p["biet_tai_nen"]                       # vùng mọi tầng chỉ bị lấy SAU lúc biết
        if t.startswith("PD_"):
            f = by_id[e.reference_event_id]
            assert f.structure_type.startswith("HTF_FVG") and f.confirmed_bar_index < e.confirmed_bar_index
        if t == "DOL_REACHED":
            sh = by_id[e.reference_event_id]
            assert sh.structure_type.startswith("SHIFT_") and sh.confirmed_bar_index < e.confirmed_bar_index
        refs = ([e.reference_event_id] if e.reference_event_id else []) + list(e.details.get("basis") or [])
        for rid in refs:
            assert by_id[rid].confirmed_bar_index <= e.confirmed_bar_index, (e.event_id, rid)


def test_ky_dau_thieu_khong_co_pdh_pwh_va_midnight_open_thieu_la_null():
    # bắt đầu 06/03 10:00 UTC (giữa ngày, giữa tuần): ngày và tuần đầu thiếu → không có mức; thiếu nến 00:00 NY 07/03
    mid = u(2024, 3, 7, 5)                                           # 00:00 EST
    _rows, bars = cal_bars(u(2024, 3, 6, 10), u(2024, 3, 13), drop={mid})
    res = run_algorithm(bars, IctStructureAlgorithm(**_p()))
    per = [e for e in res.events if e.structure_type in ("HTF_PERIOD_HIGH", "HTF_PERIOD_LOW")]
    deg = [e for e in res.events if e.structure_type == "HTF_BAR_DEGRADED"]
    assert {(e.details["khung"], e.reason_code) for e in deg} >= {("D", "HTF_FIRST_PERIOD_PARTIAL"),
                                                                  ("W", "HTF_FIRST_PERIOD_PARTIAL")}
    first_d_known = min(e.confirmed_bar_index for e in deg if e.details["khung"] == "D")
    assert all(e.confirmed_bar_index > first_d_known for e in per)    # kỳ đầu không tạo PDH/PDL
    assert not [e for e in per if e.details["khung"] == "W" and e.confirmed_bar_index < bars[-1].index - 400]
    tl = {p["bar_index"]: p for p in res.timeline}
    i_mid_next = [b.index for b in bars if b.bar_time == mid + M15][0]
    assert tl[i_mid_next]["pdh_taken"] is None                          # PDH của ngày đầu thiếu không tồn tại
    algo = IctStructureAlgorithm(**_p())
    run_algorithm(bars, algo, upto_index=i_mid_next)
    lv = algo.pending_state()["khung_lon"]["muc_theo_ky"]
    assert lv["pdh"] is None and lv["pwh"] is None
    assert lv["midnight_open"] is None and lv["day_open"] is not None   # 00:00 NY thiếu → null, không lấy giá thay
    ev = [e for e in res.events if e.confirmed_bar_index == i_mid_next + 1 and "htf" in e.details]
    assert all(e.details["htf"]["levels"]["midnight_open"] is None for e in ev)
    # ngày sau có nến 00:00 NY → midnight open = open nến đó; PDH của ngày đủ dữ liệu đã có
    i8 = [b for b in bars if b.bar_time == u(2024, 3, 8, 5)][0]
    algo2 = IctStructureAlgorithm(**_p())
    run_algorithm(bars, algo2, upto_index=i8.index)
    lv2 = algo2.pending_state()["khung_lon"]["muc_theo_ky"]
    assert lv2["midnight_open"] == i8.open and lv2["pdh"] is not None and lv2["pdh_taken"] in (True, False)


def test_degraded_trong_cua_so_khong_co_ith_va_co_htf_bar_degraded():
    # mất 2/4 nến H1 13:00 NY 07/03 → H1 degraded; không ITH/ITL H1 nào có nến đó trong cửa sổ c−1..c+1
    drop = {u(2024, 3, 7, 18), u(2024, 3, 7, 18, 15)}
    _rows, bars = cal_bars(u(2024, 3, 3, 23), u(2024, 3, 16), seed=3, drop=drop)
    res = run_algorithm(bars, IctStructureAlgorithm(**_p()))
    deg = [e for e in res.events if e.structure_type == "HTF_BAR_DEGRADED" and e.details["khung"] == "H1"]
    assert [e.details["mo"] for e in deg] == [u(2024, 3, 7, 18).isoformat()]
    k = deg[0].details["nen_htf"]
    for e in res.events:
        if e.structure_type in ("HTF_SWING_HIGH", "HTF_SWING_LOW") and e.details["khung"] == "H1":
            # STH ở giữa và hai STH bên cạnh đều là pivot hợp lệ → mọi cửa sổ không chứa nến k
            for c in (e.details["nen_htf_trai"], e.details["nen_htf"], e.details["nen_htf_phai"]):
                assert abs(c - k) > 1
    st = res.stats["chi_so_thuat_toan"]["khung_lon"]["theo_khung"]["H1"]
    assert st["degraded"] == 1 and st["cua_so_pivot_bi_chan"] == 3


def test_nhan_qua_prefix_bang_full_va_su_kien_khong_bi_sua_ngam(cal_run):
    bars, full, _algo = cal_run
    fe = [e.to_dict() for e in full.events]
    h4_close = sorted({e.confirmed_bar_index for e in full.events if e.structure_type.startswith("HTF_")})
    cuts = [55, 777, 2001, len(bars) - 2] + [c + 2 for c in h4_close[3:200:40]]
    for c in cuts:
        part = run_algorithm(bars, IctStructureAlgorithm(**_p()), upto_index=c)
        assert [e.to_dict() for e in part.events] == [e for e in fe if e["confirmed_bar_index"] <= c], c
        assert part.timeline == full.timeline[: c + 1], c
    algo = IctStructureAlgorithm(**_p())
    algo.reset()
    seen = []
    snap = None
    for b in bars:
        seen.extend(algo.on_bar(b))
        if b.index == 1500:
            snap = copy.deepcopy([e.to_dict() for e in seen])
    assert [e.to_dict() for e in seen[: len(snap)]] == snap


def test_khong_nhin_truoc_sua_nen_sau_t_trong_nen_h4_dang_hinh_thanh(cal_run):
    bars, full, _algo = cal_run
    rng = random.Random(9)
    starts = [i for i, b in enumerate(bars) if b.bar_time.astimezone(CAL_TZ).hour in (1, 5, 9) and
              b.bar_time.astimezone(CAL_TZ).minute == 0]
    for s in starts[10:400:70]:
        t = s + rng.randint(1, 12)                                   # giữa nến H4: còn nến sau t trong cùng kỳ
        mod = list(bars[: t + 1])
        for b in bars[t + 1:]:
            k = rng.uniform(0.98, 1.02)
            o, c = b.open * k, b.close * k
            mod.append(Bar(b.index, b.bar_time, b.close_time, o, max(o, c, b.high * k * 1.002),
                           min(o, c, b.low * k * 0.998), c))
        r2 = run_algorithm(mod, IctStructureAlgorithm(**_p()))
        assert [e.to_dict() for e in r2.events if e.confirmed_bar_index <= t] == \
            [e.to_dict() for e in full.events if e.confirmed_bar_index <= t], t
        assert r2.timeline[: t + 1] == full.timeline[: t + 1], t


def test_su_kien_o_nen_chot_h4_dung_ngu_canh_truoc_lan_chot(cal_run):
    bars, res, _algo = cal_run
    tl = res.timeline
    algo = IctStructureAlgorithm(**_p())
    algo.reset()
    changed = 0
    checked = 0
    for b in bars:
        evs = algo.on_bar(b)
        t = b.index
        ctx_after = algo.pending_state()["khung_lon"]["ngu_canh"] if t < len(bars) - 1 else None
        m15 = [e for e in evs if "htf" in e.details]
        if t == 0 or not m15 or tl[t]["htf_H4_age"] != 0:
            continue
        # nến t vừa chốt một nến H4: sự kiện ở t mang ngữ cảnh SAU nến t−1, không phải sau lần chốt ở t
        x = m15[0].details["htf"]["H4"]
        assert x["order"] == tl[t - 1]["htf_H4_order"] and x["zone"] == tl[t - 1]["htf_H4_zone"]
        assert x["age_ltf_bars"] == tl[t - 1]["htf_H4_age"] and x["age_ltf_bars"] > 0
        assert ctx_after["H4"]["age_ltf_bars"] == 0
        checked += 1
        changed += tl[t]["htf_H4_order"] != tl[t - 1]["htf_H4_order"]
    assert checked > 30 and changed >= 1      # 0.4.1: sự kiện nguyên liệu không mang htf → ít mẫu hơn (44 trên dữ liệu thử)


def test_tuong_duong_ngan_xep_h4_va_dataset_h4_gop_ny_1700(cal_run):
    """Không ngày đóng sớm, không hole: ITH/ITL và FVG H4 trong run M15 trùng (giá, nến H4) với cùng thành phần chạy
    trực tiếp trên dataset H4 gộp ny_1700 theo lịch; chỉ thời điểm xác nhận là nến M15 thay vì nến H4."""
    bars, res, _algo = cal_run
    rows = [{"bar_time": b.bar_time, "open": b.open, "high": b.high, "low": b.low, "close": b.close, "volume": 1.0}
            for b in bars]
    h4rows, _rep = resample_ohlc(rows, "M15", "H4", alignment="ny_1700", gap_policy="emit_available", calendar=CAL)
    h4bars = build_bars(h4rows, "H4", "open")
    h4 = run_algorithm(h4bars, IctStructureAlgorithm(timeframe="H4", session_calendar="none",
                                                     gap_policy="giu_muc_khong_chan"))
    # dữ liệu kết thúc đúng lúc đóng phiên Thứ Sáu → nến H4 cuối cũng đã chốt trong run M15
    a_sw = {(e.structure_type[-4:], e.price, e.details["nen_htf"], e.details["nen_htf_xac_nhan"]) for e in res.events
            if e.structure_type in ("HTF_SWING_HIGH", "HTF_SWING_LOW") and e.details["khung"] == "H4"}
    b_sw = {(e.structure_type[-7:-3], e.price, e.event_bar_index, e.confirmed_bar_index) for e in h4.events
            if e.structure_type in ("SWING_HIGH_L2", "SWING_LOW_L2")}
    a_sw = {("HIGH" if s == "HIGH" else "_LOW", p, i, c) for s, p, i, c in a_sw}
    b_sw = {("HIGH" if s == "HIGH" else "_LOW", p, i, c) for s, p, i, c in b_sw}
    assert len(a_sw) >= 10 and a_sw == b_sw
    a_f = {(e.direction, e.details["lo"], e.details["hi"], e.details["nen_htf_giua"]) for e in res.events
           if e.structure_type in ("HTF_FVG_UP", "HTF_FVG_DOWN") and e.details["khung"] == "H4"}
    b_f = {(e.direction, e.details["lo"], e.details["hi"], e.event_bar_index) for e in h4.events
           if e.structure_type in ("FVG_UP", "FVG_DOWN")}
    assert len(a_f) >= 10 and a_f == b_f
    for e in res.events:                                            # thời điểm biết: nến M15 đóng đúng lúc H4 chốt
        if e.structure_type in ("HTF_SWING_HIGH", "HTF_SWING_LOW") and e.details["khung"] == "H4":
            assert e.confirmed_at == h4bars[e.details["nen_htf_xac_nhan"]].close_time


# ============================================================================ tham số


def test_tham_so_khung_lon():
    with pytest.raises(ValueError):
        IctStructureAlgorithm(**_p(htf_list="H1,D"))
    with pytest.raises(ValueError):
        IctStructureAlgorithm(**_p(htf_list="H4,H4"))
    assert IctStructureAlgorithm.validate_params(_p(htf_list=" h4 , h1 "))["htf_list"] == "H1,H4"
    a = IctStructureAlgorithm(**_p(timeframe="H1"))
    assert a.htf_frames == ("H4",) and a.htf_skipped == ("H1",) and a.level_frames == ("D", "W")
    a = IctStructureAlgorithm(**_p(timeframe="H4"))
    assert a.htf_frames == () and a.level_frames == () and a._agg is None
    specs = {s.name: s for s in IctStructureAlgorithm.param_specs()}
    assert (specs["htf_list"].default, specs["htf_alignment"].default, specs["htf_min_coverage"].default,
            specs["period_levels"].default, specs["pd_respect_mode"].default, specs["respect_away_atr"].default,
            specs["dol_min_tier"].default) == ("H1,H4", "ny_1700", 0.9, True, "strict", 1.0, "H1")


def test_tat_khung_lon_va_khong_phat_su_kien_htf():
    _rows, bars = cal_bars(u(2024, 3, 3, 23), u(2024, 3, 23), seed=4, vol=1.2)
    full = run_algorithm(bars, IctStructureAlgorithm(**_p()))
    quiet = run_algorithm(bars, IctStructureAlgorithm(**_p(htf_events="khong_phat")))
    assert not [e for e in quiet.events if e.structure_type in HTF_T]
    strip = lambda evs: [(e.event_id, e.price, e.reason_code) for e in evs if e.structure_type not in HTF_T
                         and not e.structure_type.startswith("PD_")]
    assert strip(quiet.events) == strip(full.events)                  # không phát HTF_* không đổi gì khác
    off = run_algorithm(bars, IctStructureAlgorithm(**_p(htf_list="", period_levels=False)))
    kinds = {e.structure_type for e in off.events}
    assert not kinds & (HTF_T - {"HTF_BAR_DEGRADED"}) and not kinds & set(StructureType.PD_TYPES)
    assert "DOL_REACHED" not in kinds
    for e in off.events:
        if e.structure_type.startswith("LIQ_"):
            assert {p["tang"] for p in e.details["pools"]} == {"M15"}
    assert {p["dol_side"] for p in off.timeline} == {None}
