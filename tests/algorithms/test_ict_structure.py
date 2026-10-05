"""ict_structure giai đoạn 1 + thành phần core/components — tính tay, biên, tương đương, nhân quả."""
from __future__ import annotations

import copy
import math
import random
from datetime import datetime, timedelta, timezone

import pytest

from core.algorithms.ict_structure import IctStructureAlgorithm
from core.algorithms.swing_hierarchy import SwingHierarchyAlgorithm
from core.algorithms.swing_pivot import SwingPivotAlgorithm
from core.components.dealing_range import DealingRange
from core.components.session_gap import GapClassifier
from core.components.structure_order import StructureOrder
from core.components.swing_source import Pivot
from core.data.session_calendar import SessionCalendar, resolve_calendar_name
from core.engine import run_algorithm
from core.types import build_bars

UTC = timezone.utc
M15 = timedelta(minutes=15)


def _bars(hl, start=datetime(2024, 1, 3, 1, 0, tzinfo=UTC), times=None, tf="M15"):
    """Nến từ cặp (high, low); open/close nằm trong nến. ``times``: giờ mở từng nến (để tạo khoảng trống)."""
    rows = []
    for i, (h, l) in enumerate(hl):
        t = times[i] if times else start + i * M15
        o = l + 0.25 * (h - l)
        c = l + 0.75 * (h - l)
        rows.append({"bar_time": t, "open": o, "high": h, "low": l, "close": c, "volume": 1.0})
    return build_bars(rows, tf, "open")


def _algo(**kw):
    p = {"timeframe": "M15", "session_calendar": "none"}
    p.update(kw)
    return IctStructureAlgorithm(**p)


def _types(events, t):
    return [e for e in events if e.structure_type == t]


# ------------------------------------------------------------------ [P1] STH/STL


def test_sth_stl_strict_va_outside_bar():
    bars = _bars([(10, 9), (12, 8), (11, 9.5), (13, 10), (13, 10.5), (12, 10)])
    ev = _algo().run(bars)
    sth = [(e.event_bar_index, e.confirmed_bar_index, e.price) for e in _types(ev, "SWING_HIGH")]
    stl = [(e.event_bar_index, e.confirmed_bar_index, e.price) for e in _types(ev, "SWING_LOW")]
    assert (1, 2, 12) in sth                          # 12 > 10 và 12 > 11
    assert (1, 2, 8) in stl                           # outside bar: vừa đỉnh vừa đáy
    assert not any(e[0] in (3, 4) for e in sth)       # hai high 13 bằng nhau → không phải đỉnh (strict)


def _gap_bars():
    t0 = datetime(2024, 1, 3, 10, 0, tzinfo=UTC)
    times = [t0, t0 + M15, t0 + 4 * M15, t0 + 5 * M15]   # thiếu 10:30, 10:45
    return _bars([(10, 9), (12, 10), (11, 9.5), (10.5, 9)], times=times)


def test_cua_so_pivot_vat_qua_khoang_trong_bi_chan():
    ev = _algo().run(_gap_bars())
    assert not _types(ev, "SWING_HIGH")               # cửa sổ 0..2 vắt qua khoảng trống giữa nến 1 và 2
    algo = _algo()
    algo.run(_gap_bars())
    assert algo.run_stats(ev)["pivot_bi_chan_vi_gap"]["high"] == 1
    ev2 = _algo(gap_policy="giu_muc_khong_chan").run(_gap_bars())
    assert [(e.event_bar_index, e.price) for e in _types(ev2, "SWING_HIGH")] == [(1, 12)]


# ------------------------------------------------------------------ [S1] ITH/ITL


def test_ith_xac_nhan_khi_sth_ben_phai_xac_nhan():
    # STH: nến 1 (10), 3 (15), 5 (12) → ITH = nến 3, biết khi STH nến 5 xác nhận (nến 6)
    hl = [(9, 8), (10, 8.5), (9, 8.2), (15, 8.6), (9, 8.3), (12, 8.7), (9, 8.4)]
    ev = _algo().run(_bars(hl))
    ith = _types(ev, "SWING_HIGH_L2")
    assert [(e.event_bar_index, e.confirmed_bar_index, e.price) for e in ith] == [(3, 6, 15)]
    sth_ids = [e.event_id for e in _types(ev, "SWING_HIGH")]
    assert ith[0].reference_event_id == sth_ids[1]
    assert ith[0].details["basis"] == sth_ids
    assert ith[0].details["cap_cau_truc"] is True and ith[0].details["ly_do_chua_so"] == "swing đầu tiên cùng phía"


def test_cap_3_chi_khi_bat_va_la_cap_cau_truc():
    rng = random.Random(3)
    bars = _random_bars(rng, 900)
    ev2 = _algo().run(bars)
    ev3 = _algo(structure_level=3).run(bars)
    assert not _types(ev2, "SWING_HIGH_L3")
    l3 = _types(ev3, "SWING_HIGH_L3") + _types(ev3, "SWING_LOW_L3")
    assert l3 and all(e.details.get("cap_cau_truc") for e in l3)
    assert not any(e.details.get("cap_cau_truc") for e in _types(ev3, "SWING_HIGH_L2"))
    # cấp 3 lọc trên cấp 2: mỗi LTH là một ITH đã có
    ith = {(e.event_bar_index, e.price) for e in _types(ev3, "SWING_HIGH_L2")}
    assert all((e.event_bar_index, e.price) in ith for e in _types(ev3, "SWING_HIGH_L3"))


# ------------------------------------------------------------------ [S2] thứ tự + mức được bảo vệ


def _pv(side, price, i, conf=None):
    b = _bars([(price + 1, price - 1)], start=datetime(2024, 1, 3, tzinfo=UTC) + i * M15)[0]
    return Pivot(side, 2, price, b, i, b if conf is None else conf)


def test_thu_tu_va_muc_duoc_bao_ve_vi_du_plan():
    o = StructureOrder(eq_tol_atr=0.1)
    o.on_swing(_pv("high", 110, 1), atr=1.0)
    o.on_swing(_pv("low", 100, 2), atr=1.0)
    assert o.order is None                            # chưa đủ hai so sánh
    o.on_swing(_pv("high", 115, 3), atr=1.0)          # HH
    d = o.on_swing(_pv("low", 105, 4), atr=1.0)       # HL → thứ tự tăng, mức bảo vệ = đáy 105
    assert (d["nhan"], o.order, o.protected.price) == ("HL", 1, 105)
    base = _bars([(106, 103.5)])[0]
    close104 = type(base)(index=5, bar_time=base.bar_time, close_time=base.close_time,
                          open=105.0, high=106.0, low=103.5, close=104.0, volume=1.0)
    assert o.check_close(close104) is True and o.broken
    assert o.order == 1                                # chỉ là cờ, thứ tự không đổi, không có sự kiện
    o.on_swing(_pv("high", 120, 6), atr=1.0)          # HH: mức bảo vệ vẫn là đáy 105 → cờ giữ nguyên
    assert o.order == 1 and o.broken
    o.on_swing(_pv("low", 98, 7), atr=1.0)            # LL + HH → lẫn lộn → không có mức bảo vệ
    assert o.order == 0 and o.protected is None and not o.broken
    d = o.on_swing(_pv("high", 120.05, 8), atr=1.0)   # chênh 0.05 < dung sai 0.1 → EQH
    assert d["nhan"] == "EQH" and d["so_sanh"] == 0 and o.order == 0


def test_chua_co_atr_thi_chua_so_khong_ep_dung_sai_0():
    o = StructureOrder(eq_tol_atr=0.1)
    o.on_swing(_pv("high", 110, 1), atr=None)
    d = o.on_swing(_pv("high", 115, 2), atr=None)
    assert d["so_sanh"] is None and d["ly_do_chua_so"] == "ATR chưa đủ nến"


def test_dealing_range_chua_gia():
    r = DealingRange()
    r.on_swing(_pv("high", 110, 1), extreme_since=111)
    r.on_swing(_pv("low", 100, 2), extreme_since=100)
    bar = type(_pv("high", 1, 0).bar)(index=3, bar_time=datetime(2024, 1, 3, tzinfo=UTC),
                                     close_time=datetime(2024, 1, 3, 0, 15, tzinfo=UTC),
                                     open=108, high=112, low=107, close=108, volume=1)
    r.on_bar(bar)
    s = r.snapshot(108)
    assert (s["hi"], s["lo"], s["eq"], s["zone"]) == (112, 100, 106, "premium")
    assert s["range_pos"] == pytest.approx(8 / 12)


# ------------------------------------------------------------------ [G] khoảng trống theo lịch


def test_phan_loai_khoang_trong_theo_lich_cme():
    cal = SessionCalendar.load("cme_globex_metals")
    g = GapClassifier(M15, cal)
    def two(t1, t2):
        b = _bars([(10, 9), (10, 9)], times=[t1, t2])
        return g.classify(b[0], b[1])
    # 03/01/2024 (thứ Tư, EST): phiên đóng 17:00 NY = 22:00 UTC, mở lại 18:00 NY = 23:00 UTC
    assert two(datetime(2024, 1, 3, 21, 30, tzinfo=UTC), datetime(2024, 1, 3, 21, 45, tzinfo=UTC)) is None
    x = two(datetime(2024, 1, 3, 21, 45, tzinfo=UTC), datetime(2024, 1, 3, 23, 0, tzinfo=UTC))
    assert (x["loai"], x["bat_thuong"], x["so_o_thieu"]) == ("nghi_phien", False, 4)
    x = two(datetime(2024, 1, 3, 10, 0, tzinfo=UTC), datetime(2024, 1, 3, 10, 45, tzinfo=UTC))
    assert (x["loai"], x["bat_thuong"], x["so_o_trong_phien"]) == ("thieu_trong_phien", True, 2)
    x = two(datetime(2024, 1, 5, 21, 45, tzinfo=UTC), datetime(2024, 1, 7, 23, 0, tzinfo=UTC))
    assert x["loai"] == "cuoi_tuan"
    x = two(datetime(2030, 1, 3, 10, 0, tzinfo=UTC), datetime(2030, 1, 3, 10, 45, tzinfo=UTC))
    assert x["loai"] == "ngoai_lich"
    x = GapClassifier(M15, None).classify(*_bars([(10, 9), (10, 9)], times=[
        datetime(2024, 1, 3, 10, 0, tzinfo=UTC), datetime(2024, 1, 3, 10, 45, tzinfo=UTC)]))
    assert x["loai"] == "khong_ro_lich"


def test_su_kien_ict_gap_va_lich_auto_theo_ma():
    ev = _algo(session_calendar="cme_globex_metals").run(_gap_bars())
    gaps = _types(ev, "ICT_GAP")
    assert len(gaps) == 1 and gaps[0].event_bar_index == 2 and gaps[0].confirmed_bar_index == 2
    assert gaps[0].reason_code == "GAP_THIEU_TRONG_PHIEN" and gaps[0].details["bat_thuong"] is True
    assert resolve_calendar_name("auto", "XAUUSD") == "cme_globex_metals"
    assert resolve_calendar_name("auto", "eurusd") == "fx_spot"
    assert resolve_calendar_name("auto", "BTCUSD") == "none"
    assert resolve_calendar_name("fx_spot", "XAUUSD") == "fx_spot"


# ------------------------------------------------------------------ tương đương (không refactor)


def _random_bars(rng, n, gaps=False):
    t = datetime(2024, 1, 3, 1, 0, tzinfo=UTC)
    rows, price = [], 2000.0
    for i in range(n):
        if gaps and rng.random() < 0.03:
            t += M15 * rng.randint(2, 6)
        price += rng.gauss(0, 1.5)
        o = price + rng.gauss(0, 0.5)
        c = price + rng.gauss(0, 0.5)
        h = max(o, c) + abs(rng.gauss(0, 0.8))
        lo = min(o, c) - abs(rng.gauss(0, 0.8))
        r = lambda x: round(x * 2) / 2   # nến bằng giá xuất hiện thường xuyên
        rows.append({"bar_time": t, "open": r(o), "high": max(r(h), r(o), r(c)), "low": min(r(lo), r(o), r(c)),
                     "close": r(c), "volume": 1.0})
        t += M15
    return build_bars(rows, "M15", "open")


def _sig(events, types):
    return sorted((e.structure_type, e.event_bar_index, e.confirmed_bar_index, e.price)
                  for e in events if e.structure_type in types)


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_tuong_duong_swing_pivot_va_swing_hierarchy_khi_tat_chan(seed):
    bars = _random_bars(random.Random(seed), 800, gaps=True)
    ict = _algo(gap_policy="giu_muc_khong_chan").run(bars)
    piv = SwingPivotAlgorithm(left=1, right=1).run(bars)
    hie = SwingHierarchyAlgorithm(left=1, right=1).run(bars)
    assert _sig(ict, {"SWING_HIGH", "SWING_LOW"}) == _sig(piv, {"SWING_HIGH", "SWING_LOW"})
    assert _sig(ict, {"SWING_HIGH_L2", "SWING_LOW_L2"}) == _sig(hie, {"SWING_HIGH_L2", "SWING_LOW_L2"})
    blocked = _algo().run(bars)                     # chặn gap: tập con của bản không chặn
    assert set(_sig(blocked, {"SWING_HIGH", "SWING_LOW"})) <= set(_sig(ict, {"SWING_HIGH", "SWING_LOW"}))


# ------------------------------------------------------------------ timeline + nhân quả


def test_timeline_dealing_range_luon_chua_close():
    bars = _random_bars(random.Random(5), 600, gaps=True)
    res = run_algorithm(bars, _algo())
    closes = {b.index: b.close for b in bars}
    seen = 0
    for p in res.timeline:
        if p["dealing_hi"] is None:
            continue
        seen += 1
        assert p["dealing_lo"] <= closes[p["bar_index"]] <= p["dealing_hi"]
        assert 0.0 <= p["range_pos"] <= 1.0
        assert (p["protected"] is not None) == (p["order"] in (1, -1))
    assert seen > 400


@pytest.mark.parametrize("structure_level", [2, 3])
def test_nhan_qua_prefix_bang_full_va_sua_duoi_khong_doi_qua_khu(structure_level):
    rng = random.Random(11)
    bars = _random_bars(rng, 700, gaps=True)
    full = run_algorithm(bars, _algo(structure_level=structure_level))
    full_ev = [e.to_dict() for e in full.events]
    for cut in (50, 211, 400, 699):
        part = run_algorithm(bars, _algo(structure_level=structure_level), upto_index=cut)
        assert [e.to_dict() for e in part.events] == [e for e in full_ev if e["confirmed_bar_index"] <= cut]
        assert part.timeline == full.timeline[: cut + 1]
        # sửa mọi nến sau cut → không đổi gì tới cut
        tail = _random_bars(random.Random(cut), len(bars) - cut - 1)
        changed = list(bars[: cut + 1])
        for k, b in enumerate(tail):
            changed.append(type(b)(index=cut + 1 + k, bar_time=bars[cut + 1 + k].bar_time,
                                   close_time=bars[cut + 1 + k].close_time, open=b.open, high=b.high,
                                   low=b.low, close=b.close, volume=b.volume))
        other = run_algorithm(changed, _algo(structure_level=structure_level))
        assert [e.to_dict() for e in other.events if e.confirmed_bar_index <= cut] == \
               [e for e in full_ev if e["confirmed_bar_index"] <= cut]
        assert other.timeline[: cut + 1] == full.timeline[: cut + 1]


def test_su_kien_da_tra_khong_bi_sua_va_tat_dinh():
    bars = _random_bars(random.Random(21), 500, gaps=True)
    algo = _algo()
    algo.reset()
    snaps = []
    for b in bars:
        for e in algo.on_bar(b):
            snaps.append((e, copy.deepcopy(e.to_dict())))
    assert all(e.to_dict() == d for e, d in snaps)
    again = _algo().run(bars)
    assert [e.to_dict() for e in again] == [d for _e, d in snaps]


def test_du_lieu_sai_bi_tu_choi():
    good = _bars([(10, 9), (11, 9.5)])
    with pytest.raises(ValueError, match="lùi"):
        _algo().run([good[1], type(good[0])(index=2, bar_time=good[0].bar_time, close_time=good[0].close_time,
                                            open=9.5, high=10, low=9, close=9.6, volume=1)])
    bad = type(good[0])(index=0, bar_time=good[0].bar_time, close_time=good[0].close_time,
                        open=math.nan, high=10, low=9, close=9.5, volume=1)
    with pytest.raises(ValueError, match="hữu hạn"):
        _algo().run([bad])
    with pytest.raises(ValueError, match="không phải khung"):
        _algo(timeframe="H1").run(good)
    with pytest.raises(ValueError, match="không khớp dataset"):
        IctStructureAlgorithm.check_dataset("H1", IctStructureAlgorithm.validate_params({"timeframe": "M15"}))
