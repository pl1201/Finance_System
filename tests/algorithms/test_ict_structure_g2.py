"""ict_structure giai đoạn 2 — displacement, FVG, vùng thanh khoản + vòng đời, shift, killzone (plan §9).

Thành phần thử trực tiếp với ATR cho sẵn (tính tay); thuật toán thử trên chuỗi nến dựng tay (ATR Wilder
chu kỳ 2, tính tay ở chú thích) và trên dữ liệu ngẫu nhiên (bất biến + nhân quả).
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

import pytest

from core.algorithms.ict_structure import IctStructureAlgorithm
from core.components.displacement import Displacement
from core.components.fvg import FvgTracker
from core.components.killzone import Killzones, parse_killzones
from core.components.liquidity import LiquidityBook
from core.components.shift import ShiftCandidate, ShiftTracker
from core.engine import run_algorithm
from core.eval.targets import get_target
from core.indicators import WilderATRPrevClose
from core.labels import label_types
from core.types import Bar, build_bars

UTC = timezone.utc
M15 = timedelta(minutes=15)
T0 = datetime(2024, 1, 3, 14, 0, tzinfo=UTC)      # 09:00 New York (giờ mùa đông) — NY AM


def _ohlc(rows, times=None):
    return build_bars([{"bar_time": times[i] if times else T0 + i * M15, "open": o, "high": h, "low": lo,
                        "close": c, "volume": 1.0} for i, (o, h, lo, c) in enumerate(rows)], "M15", "open")


def _algo(**kw):
    p = {"timeframe": "M15", "session_calendar": "none", "atr_period": 2}
    p.update(kw)
    return IctStructureAlgorithm(**p)


def _types(events, t):
    return [e for e in events if e.structure_type == t]


def _one(events, t):
    found = _types(events, t)
    assert len(found) == 1, (t, [e.event_id for e in events])
    return found[0]


# ------------------------------------------------------------------ [P3] displacement


def test_displacement_dung_nguong_thieu_nguong_va_sau_khoang_trong():
    d = Displacement(1.5, 0.6)
    b = _ohlc([(100.0, 101.5, 100.0, 100.9)])[0]          # biên độ 1.5 = 1.5 × ATR 1; thân 0.9 = 60%
    got = d.check(b, 1.0, after_gap=False)
    assert got["dir"] == "up" and got["bien_do_atr"] == pytest.approx(1.5) and got["than_ty_le"] == pytest.approx(0.6)
    assert d.check(b, 1.01, after_gap=False) is None       # thiếu biên độ
    assert d.check(_ohlc([(100.0, 101.5, 100.0, 100.85)])[0], 1.0, after_gap=False) is None   # thiếu thân
    assert d.check(b, 1.0, after_gap=True) is None         # nến đầu sau khoảng trống
    assert d.check(b, None, after_gap=False) is None       # chưa có ATR
    assert d.check(_ohlc([(101.4, 101.5, 100.0, 100.1)])[0], 1.0, after_gap=False)["dir"] == "down"


# ------------------------------------------------------------------ [P2] FVG


def test_fvg_vung_co_displacement_loai_qua_khoang_trong_va_loc_nho():
    b1, b2, b3 = _ohlc([(9.5, 10.0, 9.0, 9.8), (9.8, 12.0, 9.7, 11.8), (11.8, 12.5, 11.0, 12.2)])
    tr = FvgTracker()
    f = tr.detect(b1, b2, b3, gap_in_window=False, atr_prev=1.0, mid_disp="up")
    assert (f.direction, f.lo, f.hi, f.index, f.mid_index, f.from_displacement) == ("up", 10.0, 11.0, 2, 1, True)
    assert tr.detect(b1, b2, b3, gap_in_window=False, atr_prev=1.0, mid_disp="down").from_displacement is False
    assert tr.detect(b1, b2, b3, gap_in_window=True, atr_prev=1.0, mid_disp=None) is None
    assert tr.counts["bo_vi_khoang_trong"] == 1
    small = FvgTracker(min_atr=1.5)                        # vùng 1.0 < 1.5 × ATR 1
    assert small.detect(b1, b2, b3, False, 1.0, None) is None and small.counts["bo_vi_nho"] == 1
    assert small.detect(b1, b2, b3, False, None, None) is None   # có ngưỡng mà chưa có ATR → bỏ


def test_fvg_cham_roi_lap_va_cham_lap_cung_nen():
    b1, b2, b3, b4, b5 = _ohlc([(9.5, 10.0, 9.0, 9.8), (9.8, 12.0, 9.7, 11.8), (11.8, 12.5, 11.0, 12.2),
                                (12.2, 12.4, 10.8, 11.0), (11.0, 11.2, 9.9, 10.0)])
    tr = FvgTracker()
    f = tr.detect(b1, b2, b3, False, 1.0, None)
    assert tr.update_open(b4) == [("touched", f)] and f.touched_at == 3 and tr.open["up"] == 1
    assert tr.update_open(b5) == [("filled", f)] and f.filled_at == 4 and tr.open["up"] == 0
    tr2 = FvgTracker()
    g = tr2.detect(b1, b2, b3, False, 1.0, None)
    assert tr2.update_open(b5) == [("touched", g), ("filled", g)]      # một nến đi hết vùng
    assert tr2.counts["cham"] == 1 and tr2.counts["lap"] == 1


# ------------------------------------------------------------------ [S3]/[E2] vùng thanh khoản


def _bar(i, o, h, lo, c, gap_minutes=0):
    t = T0 + i * M15 + timedelta(minutes=gap_minutes)
    return Bar(index=i, bar_time=t, close_time=t + M15, open=o, high=h, low=lo, close=c, volume=1.0)


def _book(W=3):
    bk = LiquidityBook(min_pen_atr=0.1, sweep_window=W, eq_tol_atr=0.1)
    status, pool = bk.add("high", 100.0, "M15", "src", known_index=0, extreme_index=0, atr=1.0, already_taken=False)
    assert status == "created"
    return bk, pool


def test_cham_nong_roi_moi_lay_va_atr_khoa_dung_nen():
    bk, pool = _book()
    r1 = bk.on_bar(_bar(1, 99.8, 100.05, 99.5, 99.9), 1.0, None)          # xuyên 0.05 < 0.1 × 1.0
    assert r1["touched"] == [pool] and not r1["taken"] and pool.state == "intact" and pool.touch_count == 1
    r2 = bk.on_bar(_bar(2, 99.9, 100.15, 99.8, 100.1), 1.2, None)         # xuyên 0.15 ≥ 0.1 × 1.2
    assert r2["taken"] == [pool] and pool.taken_index == 2 and pool.atr_locked == 1.2
    assert pool.pen == pytest.approx(0.15) and bk.pen_atr == [pytest.approx(0.125)]
    bk.on_bar(_bar(3, 100.1, 100.2, 100.0, 100.1), 5.0, None)              # ATR đổi sau đó: ATR khoá giữ nguyên
    assert pool.atr_locked == 1.2 and bk.counts["lay_sau_khi_cham"] == 1


@pytest.mark.parametrize("ret_at, kind, idx", [(2, "sweep", 2), (5, "sweep", 5), (6, "run", 5), (None, "run", 5)])
def test_cua_so_W_tinh_ca_nen_lay(ret_at, kind, idx):
    """Lấy ở b = 2, W = 3: close quay lại ở b..b+3 → sweep; không quay lại tới b+3 → run tại b+3."""
    bk, pool = _book()
    got = []
    for i in range(2, 8):
        c = 99.9 if i == ret_at else 100.3
        got += bk.on_bar(_bar(i, 100.2, 100.5, 99.8, c), 1.0, None)["resolved"]
    assert [(k, p.resolved_index) for k, p in got] == [(kind, idx)]
    if kind == "sweep":
        assert idx - pool.taken_index == ret_at - 2 and pool.extreme == 100.5


def test_khoang_trong_trong_cua_so_thanh_chua_ro_tai_nen_sau_khoang_trong():
    bk, pool = _book()
    bk.on_bar(_bar(2, 100.2, 100.5, 99.8, 100.3), 1.0, None)
    got = bk.on_bar(_bar(3, 100.3, 100.4, 99.7, 99.9, gap_minutes=60), 1.0, {"loai": "nghi_phien"})["resolved"]
    assert [(k, p.resolved_index) for k, p in got] == [("unresolved", 3)] and pool.gap_kind == "nghi_phien"
    assert bk.counts["chua_ro"] == 1 and bk.counts["sweep"] == 0     # close quay lại nhưng không thành sweep


def test_mot_nen_lay_nhieu_vung_moi_vung_mot_vong_doi():
    bk, a = _book()
    _s, b = bk.add("high", 100.5, "M15", "src2", 1, 1, 1.0, False)     # chênh 0.5 > 0.1 × ATR → không gộp
    got = bk.on_bar(_bar(2, 100.0, 101.0, 99.8, 100.2), 1.0, None)
    assert {p.seq for p in got["taken"]} == {a.seq, b.seq}
    assert [(k, p.seq) for k, p in got["resolved"]] == [("sweep", b.seq)]      # close 100.2 < 100.5, > 100.0
    assert [p.seq for p in bk.pending()] == [a.seq]


def test_gop_eq_chi_giua_hai_swing_lien_tiep():
    bk, a = _book()
    st, m = bk.add("high", 100.05, "M15", "s2", 1, 1, 1.0, False)
    assert st == "merged" and m is a and a.level == 100.05 and a.sources == ["src", "s2"]
    assert bk.on_bar(_bar(2, 99.9, 100.07, 99.8, 99.9), 1.0, None)["touched"] == [a]   # chỉ còn một vùng
    st, _ = bk.add("high", 100.0, "M15", "s3", 3, 3, 1.0, already_taken=True)
    assert st == "not_created"
    st, c = bk.add("high", 100.02, "M15", "s4", 4, 4, 1.0, False)
    assert st == "created" and c is not a          # swing liền trước không tạo vùng → không gộp vượt qua nó


# ------------------------------------------------------------------ [E3] shift (thành phần)


def _cand(r=5, deadline=8):
    return ShiftCandidate(direction="down", level=100.0, extreme=101.0, r=r, deadline=deadline,
                          sweep_event_id="sw%d" % r, group_id="sw%d" % r, tier="M15")


DISP_DOWN = {"dir": "down"}


def test_shift_ngay_nen_quet_va_o_r_cong_3_het_han_o_r_cong_4():
    tr = ShiftTracker(3)
    tr.add(_cand())
    assert tr.on_bar(_bar(5, 100.5, 100.8, 99.0, 99.5), DISP_DOWN, False)["down"][0].r == 5     # d = r
    tr = ShiftTracker(3)
    tr.add(_cand())
    for i in (5, 6, 7):
        assert tr.on_bar(_bar(i, 100.2, 100.6, 99.8, 100.1), None, False) == {}
    assert "down" in tr.on_bar(_bar(8, 100.2, 100.6, 98.8, 99.0), DISP_DOWN, False)                # d = r + 3
    tr = ShiftTracker(3)
    tr.add(_cand())
    for i in (5, 6, 7, 8):
        tr.on_bar(_bar(i, 100.2, 100.6, 99.8, 100.1), None, False)
    assert not tr.pending and tr.counts["het_cua_so"] == 1


def test_shift_huy_khi_vuot_cuc_tri_hoac_khoang_trong_va_can_close_qua_muc():
    tr = ShiftTracker(3)
    tr.add(_cand())
    tr.on_bar(_bar(6, 100.2, 101.1, 99.8, 100.1), None, False)          # high > X → huỷ
    assert not tr.pending and tr.counts["huy_vuot_cuc_tri"] == 1
    assert tr.on_bar(_bar(7, 100.2, 100.6, 98.8, 99.0), DISP_DOWN, False) == {}
    tr = ShiftTracker(3)
    tr.add(_cand())
    tr.on_bar(_bar(6, 100.2, 100.6, 99.8, 100.1, gap_minutes=60), None, True)
    assert not tr.pending and tr.counts["huy_khoang_trong"] == 1
    tr = ShiftTracker(3)
    tr.add(_cand())
    assert tr.on_bar(_bar(6, 100.9, 100.95, 100.0, 100.0), DISP_DOWN, False) == {}   # close = mức, chưa dưới
    assert tr.on_bar(_bar(7, 100.2, 100.6, 99.8, 100.1), {"dir": "up"}, False) == {}  # sai chiều
    assert len(tr.pending) == 1


def test_hai_sweep_cung_dan_toi_mot_nen_displacement():
    tr = ShiftTracker(3)
    tr.add(_cand(r=5, deadline=8))
    tr.add(ShiftCandidate("down", 99.5, 101.0, 6, 9, "sw6", "sw6", "M15"))
    got = tr.on_bar(_bar(7, 100.2, 100.6, 98.8, 99.0), DISP_DOWN, False)
    assert [c.sweep_event_id for c in got["down"]] == ["sw5", "sw6"] and not tr.pending


# ------------------------------------------------------------------ [C] killzone


def test_killzone_theo_gio_new_york_co_doi_gio_mua_he():
    kz = Killzones()
    assert kz.of(datetime(2024, 3, 8, 12, 0, tzinfo=UTC)) == "ny_am"        # 07:00 EST
    assert kz.of(datetime(2024, 3, 11, 11, 0, tzinfo=UTC)) == "ny_am"       # 07:00 EDT (đã đổi giờ)
    assert kz.of(datetime(2024, 3, 8, 11, 0, tzinfo=UTC)) is None           # 06:00 EST
    assert kz.of(datetime(2024, 1, 3, 1, 0, tzinfo=UTC)) == "asia"          # 20:00 hôm trước
    assert kz.of(datetime(2024, 1, 3, 8, 0, tzinfo=UTC)) == "london"        # 03:00
    assert kz.of(datetime(2024, 1, 3, 15, 59, tzinfo=UTC)) == "london_close"  # 10:59
    assert parse_killzones("a=1-2, b=2-3") == (("a", 1, 2), ("b", 2, 3))     # nửa mở: chạm biên không chồng
    for bad in ("a=1-3,b=2-4", "ny am=7-10", "x=10-7", "x=7-25"):
        with pytest.raises(ValueError):
            parse_killzones(bad)
    with pytest.raises(ValueError, match="Killzone"):
        IctStructureAlgorithm.validate_params({"killzones": "ny_am=7"})


# ------------------------------------------------------------------ thuật toán: chuỗi dựng tay

# STH 101 (#1), 102 (#3), 101.5 (#5) → ITH #3 = 102, biết ở #6 (BSL B0, hiệu lực từ #7).
# STL 99.7 (#2), 99.3 (#4), 99.8 (#6) → ITL #4 = 99.3, biết ở #7 (SSL S1, hiệu lực từ #8).
# ATR Wilder chu kỳ 2 (TR theo close trước): #2 0.95 · #3 1.475 · #4 1.8375 · #5 1.86875 · #6 1.634375 · #7 2.1171875.
BASE = [
    (100.0, 100.5, 99.9, 100.2),
    (100.2, 101.0, 100.0, 100.5),
    (100.5, 100.6, 99.7, 100.0),
    (100.0, 102.0, 100.0, 101.5),
    (100.8, 101.0, 99.3, 99.6),
    (100.0, 101.5, 99.9, 101.2),
    (101.2, 101.2, 99.8, 100.0),
    (101.0, 102.6, 101.0, 101.8),   # #7 lấy B0 (xuyên 0.6 ≥ 0.1 × 1.634) và close quay lại → sweep, sweep_bars 0
    (101.8, 101.9, 98.6, 98.8),     # #8 displacement giảm (3.3 ≥ 1.5 × 2.117), close < 102, high ≤ X 102.6 → SHIFT_DOWN; lấy S1
    (96.8, 100.8, 96.7, 100.6),     # #9 close > 99.3 → sweep S1; displacement tăng → SHIFT_UP; FVG giảm giữa #8 → SHIFT_FVG_DOWN
]


def _expected_atr(rows):
    atr, out = WilderATRPrevClose(2), []
    for _o, h, lo, c in rows:
        out.append(atr.value)              # ATR[t−1] dùng ở nến t
        atr.update(h, lo, c)
    return out


def test_chuoi_sweep_shift_shift_fvg_group_id_va_tham_chieu():
    res = run_algorithm(_ohlc(BASE), _algo())
    ev = res.events
    ith = _one(ev, "SWING_HIGH_L2")
    assert ith.details["vung_thanh_khoan"] == {"trang_thai": "tao_moi", "phia": "BSL", "tang": "M15", "vung": "B0",
                                               "muc_vung": 102.0, "hieu_luc_tu_nen": 7}
    atr_prev = _expected_atr(BASE)
    sw = _one(ev, "LIQ_SWEEP_BSL")
    assert (sw.event_bar_index, sw.confirmed_bar_index, sw.price, sw.direction) == (7, 7, 102.0, "down")
    x = sw.details
    assert x["sweep_bars"] == 0 and x["nen_lay"] == 7 and x["cuc_tri_cu_quet"] == 102.6 and x["group_id"] == sw.event_id
    assert x["atr_khoa"] == pytest.approx(atr_prev[7]) == pytest.approx(1.634375)
    assert x["xuyen_atr"] == pytest.approx(0.6 / 1.634375) and sw.reference_event_id == ith.event_id
    sh = _one(ev, "SHIFT_DOWN")
    disp = _one(ev, "DISPLACEMENT_DOWN")
    assert (sh.event_bar_index, sh.confirmed_bar_index, sh.price) == (8, 8, 98.8)
    assert sh.reference_event_id == sw.event_id and sh.details["group_id"] == sw.event_id
    assert sh.details["basis"] == [sw.event_id, disp.event_id] and sh.details["so_nen_tu_sweep"] == 1
    assert sh.details["muc_bi_quet"] == 102.0 and sh.details["cuc_tri_cu_quet"] == 102.6
    # Nến #9 vừa là shift tăng (sau quét SSL) — shift mới không được che SHIFT_FVG của shift ở #8.
    up = _one(ev, "SHIFT_UP")
    ssl = _one(ev, "LIQ_SWEEP_SSL")
    assert (ssl.event_bar_index, ssl.confirmed_bar_index, ssl.details["sweep_bars"]) == (8, 9, 1)
    assert ssl.details["atr_khoa"] == pytest.approx(atr_prev[8]) and up.details["group_id"] == ssl.event_id
    fvg = _one(ev, "FVG_DOWN")
    assert (fvg.event_bar_index, fvg.confirmed_bar_index, fvg.details["lo"], fvg.details["hi"]) == (8, 9, 100.8, 101.0)
    assert fvg.details["from_displacement"] is True
    sf = _one(ev, "SHIFT_FVG_DOWN")
    assert (sf.event_bar_index, sf.confirmed_bar_index, sf.price) == (8, 9, 98.8)
    assert sf.reference_event_id == sh.event_id and sf.details["group_id"] == sw.event_id
    assert sf.details["fvg"] == fvg.event_id
    assert all(e.details["killzone"] in ("ny_am", "london_close") for e in ev)   # 09:00–11:15 New York
    tl = res.timeline
    assert tl[8]["last_shift"] == "down" and tl[8]["last_shift_bars"] == 0 and tl[8]["last_shift_fvg"] is False
    assert (tl[5]["liq_above"], tl[6]["liq_above"], tl[6]["liq_above_id"]) == (None, 102.0, "B0")
    assert tl[7]["liq_above"] is None and tl[7]["last_sweep"] == "BSL"
    stats = res.stats["chi_so_thuat_toan"]
    assert stats["shift"]["so"] == 2 and stats["shift"]["co_fvg"] == 1


def test_shift_huy_khi_nen_sau_vuot_cuc_tri_cu_quet():
    rows = list(BASE)
    rows[8] = (101.8, 102.7, 98.6, 98.8)          # high 102.7 > X 102.6 ở nến displacement
    ev = run_algorithm(_ohlc(rows), _algo()).events
    assert _types(ev, "DISPLACEMENT_DOWN") and not _types(ev, "SHIFT_DOWN")


def test_shift_huy_khi_co_khoang_trong_sau_sweep():
    small = (101.8, 102.2, 101.4, 101.6)
    rows = BASE[:8] + [small] + BASE[8:]
    times = [T0 + i * M15 for i in range(8)] + [T0 + (i + 4) * M15 for i in range(8, len(rows))]   # gap trước #8
    algo = _algo()
    ev = run_algorithm(_ohlc(rows, times), algo).events
    assert _types(ev, "LIQ_SWEEP_BSL") and _types(ev, "DISPLACEMENT_DOWN") and not _types(ev, "SHIFT_DOWN")
    assert algo._shift.counts["huy_khoang_trong"] == 1


@pytest.mark.parametrize("n_small, shift", [(2, True), (3, False)])
def test_shift_o_r_cong_3_va_qua_cua_so(n_small, shift):
    smalls = [(101.8, 102.2, 101.4, 101.6), (101.6, 102.0, 101.3, 101.5), (101.5, 101.9, 101.3, 101.5)][:n_small]
    rows = BASE[:8] + smalls + [(101.5, 101.6, 98.6, 98.8)]
    ev = run_algorithm(_ohlc(rows), _algo()).events
    d = len(rows) - 1
    assert _one(ev, "DISPLACEMENT_DOWN").event_bar_index == d
    got = _types(ev, "SHIFT_DOWN")
    assert bool(got) is shift
    if shift:
        assert got[0].details["so_nen_tu_sweep"] == 3


def test_mot_nen_quet_hai_vung_gom_mot_su_kien():
    rows = [(100.2, 100.5, 99.5, 100.0), (100.0, 101.0, 100.0, 100.5), (100.5, 100.6, 99.6, 100.0),
            (100.0, 102.0, 100.0, 101.5), (101.0, 101.0, 100.0, 100.5), (100.5, 101.5, 100.5, 101.0),
            (101.0, 101.0, 100.0, 100.5), (100.5, 101.8, 100.5, 101.2), (101.2, 101.2, 100.2, 100.6),
            (100.6, 101.4, 100.4, 101.0), (101.0, 101.0, 100.0, 100.4), (100.4, 102.5, 100.3, 101.0)]
    ev = run_algorithm(_ohlc(rows), _algo()).events
    assert [e.details["vung_thanh_khoan"]["vung"] for e in _types(ev, "SWING_HIGH_L2")] == ["B0", "B1"]
    sw = _one(ev, "LIQ_SWEEP_BSL")
    assert sw.details["so_vung"] == 2 and [p["id"] for p in sw.details["pools"]] == ["B0", "B1"]
    assert sw.details["vung"] == "B0" and sw.price == 102.0      # vùng chính: cùng tầng → mức xa nhất


def test_vung_da_bi_lay_truoc_khi_biet_thi_khong_tao():
    # ITH #3 = 102 chỉ biết ở #9; #5/#6 high 102.5 (bằng nhau → không phải STH) đã xuyên ≥ ngưỡng.
    rows = [(100.2, 100.5, 99.5, 100.0), (100.0, 101.0, 100.0, 100.5), (100.5, 100.6, 99.6, 100.0),
            (100.0, 102.0, 100.0, 101.5), (101.5, 101.5, 100.5, 101.0), (101.0, 102.5, 101.0, 102.0),
            (102.0, 102.5, 101.5, 101.8), (101.0, 101.2, 100.4, 100.8), (100.8, 101.5, 100.5, 101.2),
            (101.2, 101.2, 100.2, 100.6)]
    algo = _algo()
    res = run_algorithm(_ohlc(rows), algo)
    ith = _one(res.events, "SWING_HIGH_L2")
    assert ith.confirmed_bar_index == 9
    v = ith.details["vung_thanh_khoan"]
    assert v["trang_thai"] == "khong_tao" and "#5" in v["ly_do_vi"]
    assert res.stats["chi_so_thuat_toan"]["thanh_khoan"]["khong_tao_da_bi_lay"] == 1
    assert not any(e.structure_type.startswith("LIQ_") for e in res.events)


# ------------------------------------------------------------------ dữ liệu ngẫu nhiên: bất biến + nhân quả


def _random_bars(seed, n, gaps=True):
    rng = random.Random(seed)
    t = datetime(2024, 1, 3, 1, 0, tzinfo=UTC)
    rows, price = [], 2000.0
    for _ in range(n):
        if gaps and rng.random() < 0.02:
            t += M15 * rng.randint(2, 6)
        vol = 3.0 if rng.random() < 0.08 else 1.0          # thỉnh thoảng nến lớn → có displacement / shift
        price += rng.gauss(0, 1.2 * vol)
        o = price + rng.gauss(0, 0.4)
        c = price + rng.gauss(0, 0.4) + (rng.choice((-1, 1)) * 2.5 * vol if vol > 1 else 0)
        h = max(o, c) + abs(rng.gauss(0, 0.6))
        lo = min(o, c) - abs(rng.gauss(0, 0.6))
        r = lambda x: round(x * 4) / 4
        rows.append({"bar_time": t, "open": r(o), "high": max(r(h), r(o), r(c)), "low": min(r(lo), r(o), r(c)),
                     "close": r(c), "volume": 1.0})
        price = c
        t += M15
    return build_bars(rows, "M15", "open")


def _p(**kw):
    p = {"timeframe": "M15", "session_calendar": "none"}
    p.update(kw)
    return p


@pytest.mark.parametrize("seed", [3, 4])
def test_bat_bien_tren_du_lieu_ngau_nhien(seed):
    bars = _random_bars(seed, 1500)
    params = _p()
    res = run_algorithm(bars, IctStructureAlgorithm(**params))
    ev = res.events
    by_id = {e.event_id: e for e in ev}
    assert len(by_id) == len(ev)
    kinds = {e.structure_type for e in ev}
    assert {"LIQ_SWEEP_BSL", "LIQ_SWEEP_SSL", "LIQ_RUN_UP", "LIQ_RUN_DOWN", "SHIFT_UP", "SHIFT_DOWN",
            "SHIFT_FVG_UP", "SHIFT_FVG_DOWN", "FVG_TOUCHED", "FVG_FILLED", "LIQ_UNRESOLVED"} <= kinds
    W, S = 3, 3
    disp_at = {(e.event_bar_index, e.direction) for e in ev if e.structure_type.startswith("DISPLACEMENT_")}
    for e in ev:
        x = e.details
        assert "killzone" in x
        # tham chiếu / basis chỉ trỏ tới sự kiện đã biết, không sau sự kiện này
        refs = ([e.reference_event_id] if e.reference_event_id else []) + list(x.get("basis") or [])
        for rid in refs:
            assert by_id[rid].confirmed_bar_index <= e.confirmed_bar_index, (e.event_id, rid)
        t = e.structure_type
        if t.startswith("LIQ_"):
            assert x["so_vung"] == len(x["pools"]) >= 1
            for p in x["pools"]:
                assert p["nen_lay"] > p["biet_tai_nen"]          # vùng chỉ bị lấy SAU nến làm nó được biết
            if t.startswith("LIQ_SWEEP"):
                assert 0 <= x["sweep_bars"] <= W
            elif t.startswith("LIQ_RUN"):
                assert e.confirmed_bar_index - x["nen_lay"] == W
        if t in ("SHIFT_UP", "SHIFT_DOWN"):
            assert 0 <= x["so_nen_tu_sweep"] <= S and (e.event_bar_index, e.direction) in disp_at
            assert by_id[e.reference_event_id].structure_type == ("LIQ_SWEEP_BSL" if t == "SHIFT_DOWN" else "LIQ_SWEEP_SSL")
            for s in x["swept"]:
                assert (s["muc"] > e.price) if t == "SHIFT_DOWN" else (s["muc"] < e.price)
        if t.startswith("SHIFT_FVG"):
            sh = by_id[e.reference_event_id]
            assert sh.event_bar_index == e.event_bar_index == e.confirmed_bar_index - 1
            assert sh.details["group_id"] == x["group_id"] and sh.direction == e.direction
    seen = set()
    for e in ev:                                      # gom theo (nến, phía): một sự kiện mỗi loại mỗi nến
        if e.structure_type.startswith("LIQ_") and e.structure_type != "LIQ_UNRESOLVED":
            key = (e.structure_type, e.confirmed_bar_index)
            assert key not in seen
            seen.add(key)
    for p in res.timeline:
        if p["liq_above"] is not None and p["liq_below"] is not None:
            assert p["liq_below"] < p["liq_above"]


def test_nhan_qua_prefix_bang_full_giai_doan_2():
    bars = _random_bars(7, 900)
    full = run_algorithm(bars, IctStructureAlgorithm(**_p()))
    assert _types(full.events, "SHIFT_UP") and _types(full.events, "SHIFT_FVG_DOWN")
    full_ev = [e.to_dict() for e in full.events]
    for cut in (120, 333, 640, 899):
        part = run_algorithm(bars, IctStructureAlgorithm(**_p()), upto_index=cut)
        assert [e.to_dict() for e in part.events] == [e for e in full_ev if e["confirmed_bar_index"] <= cut]
        assert part.timeline == full.timeline[: cut + 1]


def test_muc_tieu_cham_shift_va_loai_nhan():
    t = get_target("ict_shift")
    assert t.label_types == ("SHIFT_UP", "SHIFT_DOWN") and t.high_types == ("SHIFT_DOWN",)
    assert t.default_event_type_map() == {"SHIFT_UP": "SHIFT_UP", "SHIFT_DOWN": "SHIFT_DOWN"}
    assert {"SHIFT_UP", "SHIFT_DOWN"} <= set(label_types())
