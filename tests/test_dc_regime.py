"""Test classifier Trend/Range/UNKNOWN (dc_regime) độc lập với detector DC."""
from __future__ import annotations

import pytest

from core.algorithms.dc_regime import (
    DOWNTREND,
    RANGE,
    UNKNOWN,
    UPTREND,
    WHY_CO_EQ,
    WHY_MAU_THUAN,
    WHY_THIEU_PIVOT,
    PivotRef,
    RegimeClassifier,
    RegimeParams,
)


class Feeder:
    """Nạp pivot tuần tự, mỗi pivot xác nhận ở một nến mới."""

    def __init__(self, **params):
        self.cls = RegimeClassifier(RegimeParams(**params))
        self.bar = 10
        self.n = 0

    def pivot(self, kind, price, label=None, *, close=None, atr=1.0, bar=None):
        self.bar = self.bar + 1 if bar is None else bar
        self.n += 1
        ref = PivotRef("p%d" % self.n, kind, price, label, self.bar - 1, self.bar)
        return self.cls.on_pivot(ref, self.bar, price if close is None else close, atr)


def test_hh_hl_la_tang_lh_ll_la_giam():
    f = Feeder()
    assert f.pivot("high", 110) is None
    assert f.pivot("low", 100) is None
    assert f.pivot("high", 112, "HH") is None          # chưa đủ hai đáy
    assert f.cls.why == WHY_THIEU_PIVOT
    tr = f.pivot("low", 102, "HL")
    assert tr is not None and (tr.from_state, tr.to_state) == (UNKNOWN, UPTREND)
    assert tr.bar_index == f.bar                         # bắt đầu lúc biết, không lùi
    assert tr.details["bang_chung"] == ["p3", "p4"]
    assert f.pivot("high", 115, "HH") is None            # vẫn tăng: không phát trùng
    assert f.cls.state == UPTREND
    tr = f.pivot("low", 99, "LL")                        # HH + LL → mâu thuẫn
    assert tr.to_state == UNKNOWN and f.cls.why == WHY_MAU_THUAN
    tr = f.pivot("high", 108, "LH")                      # LH + LL → giảm
    assert tr.to_state == DOWNTREND


def test_eq_khong_du_trend():
    f = Feeder()
    f.pivot("high", 110)
    f.pivot("low", 100)
    f.pivot("high", 110, "EQH")
    assert f.pivot("low", 102, "HL") is None
    assert f.cls.state == UNKNOWN and f.cls.why == WHY_CO_EQ


def _range_setup(f, highs=(110, 110.25, 109.75), lows=(100, 100.25, 99.75), close=105, atr=1.0):
    """Pivot xen kẽ, nhãn không tạo trend. Pivot cuối chạy kiểm tra Range."""
    out = None
    labels_h = [None, "EQH", "EQH"]
    labels_l = [None, "EQL", "EQL"]
    for i in range(3):
        f.pivot("high", highs[i], labels_h[i], close=close, atr=atr)
        out = f.pivot("low", lows[i], labels_l[i], close=close, atr=atr)
    return out


def test_range_du_m_moi_phia():
    f = Feeder()
    tr = _range_setup(f)
    assert tr is not None and tr.kind == "RANGE_START" and f.cls.state == RANGE
    rng = f.cls.active_range
    assert (rng.upper, rng.lower, rng.atr, rng.buffer) == (110.25, 99.75, 1.0, 0.25)
    assert rng.start_index == f.bar and len(rng.evidence_ids) == 6


@pytest.mark.parametrize(
    "kw,msg",
    [
        ({"highs": (110, 110.75, 109.75)}, "cụm đỉnh"),               # spread 1.0 > 0.5
        ({"lows": (100, 100.75, 99.75)}, "cụm đáy"),
        ({"highs": (101, 101.25, 101), "lows": (101, 101.25, 100.75)}, "chồng nhau"),
        ({"highs": (100.5, 100.75, 100.5), "lows": (100, 100.25, 100), "close": 100.5}, "hẹp"),
        ({"close": 111}, "ngoài"),
    ],
)
def test_range_khong_dat(kw, msg):
    f = Feeder()
    tr = _range_setup(f, **kw)
    assert f.cls.state != RANGE
    assert msg in f.cls.snapshot()["kiem_tra_range_gan_nhat"]["ly_do_vi"]
    assert tr is None or tr.kind != "RANGE_START"


def test_range_thieu_pivot_hoac_atr_0():
    f = Feeder()
    f.pivot("high", 110, close=105)
    f.pivot("low", 100, close=105)
    f.pivot("high", 110, "EQH", close=105)
    f.pivot("low", 100, "EQL", close=105)
    assert f.cls.state == UNKNOWN
    f2 = Feeder()
    _range_setup(f2, atr=0.0)
    assert f2.cls.state == UNKNOWN


def test_range_khoa_bien_wick_khong_du_close_moi_thoat():
    f = Feeder()
    _range_setup(f)
    b = f.bar
    # close đúng bằng biên + buffer: chưa thoát (phải vượt hẳn)
    assert f.cls.check_range_break(b + 1, 110.5) is None
    assert f.cls.check_range_break(b + 2, 99.5) is None
    # pivot mới không trend trong Range: giữ biên cũ, không tạo range mới
    assert f.pivot("high", 110, "EQH", close=105) is None
    assert f.cls.active_range.upper == 110.25 and f.cls.active_range.start_index == b
    tr = f.cls.check_range_break(f.bar + 1, 110.75)
    assert tr is not None and tr.kind == "RANGE_EXIT" and tr.to_state == UNKNOWN
    assert tr.details["huong_pha"] == "up" and f.cls.active_range is None


def test_nen_breakout_khong_phan_loai_lai_nen_sau_moi_duoc():
    f = Feeder()
    _range_setup(f)
    brk = f.bar + 1
    assert f.cls.check_range_break(brk, 95.0) is not None
    # pivot cùng nến breakout, dù đủ LH+LL → bị chặn
    assert f.pivot("low", 98, "LL", close=95.0, bar=brk) is None
    assert f.cls.state == UNKNOWN
    assert f.pivot("high", 104, "LH", close=100.0, bar=brk) is None  # vẫn nến đó
    tr = f.pivot("high", 103, "LH", close=100.0, bar=brk + 1)
    assert tr is not None and tr.to_state == DOWNTREND


def test_range_chuyen_trend_theo_bang_chung_moi():
    f = Feeder()
    _range_setup(f)
    f.pivot("high", 110.5, "HH", close=105)              # HH + EQL: giữ Range
    assert f.cls.state == RANGE
    tr = f.pivot("low", 101, "HL", close=106)
    assert tr.to_state == UPTREND and tr.from_state == RANGE
    assert tr.details["range_dong"]["upper"] == 110.25
    assert f.cls.active_range is None


def test_reset_xoa_sach():
    f = Feeder()
    _range_setup(f)
    f.cls.reset()
    s = f.cls.snapshot()
    assert s["state"] == UNKNOWN and s["range"] is None
    assert s["so_dinh_xac_nhan"] == 0 and s["so_day_xac_nhan"] == 0


def test_tham_so_khong_hop_le():
    with pytest.raises(ValueError):
        RegimeParams(swings_per_side=2)
    with pytest.raises(ValueError):
        RegimeParams(min_width_atr=0)
    with pytest.raises(ValueError):
        RegimeParams(cluster_tolerance_atr=-1)


# ---------------------------------------------------------------------------
# Tích hợp qua adapter: regime event chỉ khi đổi, không backdate, gap reset
# ---------------------------------------------------------------------------


def test_adapter_regime_event_tai_luc_biet_va_khong_trung():
    from core.algorithms.dc_atr_structure import DcAtrStructureAlgorithm
    from core.data.synthetic import SyntheticSpec, generate
    from core.engine import run_algorithm
    from core.types import build_bars

    rows = generate(SyntheticSpec(symbol="XAUUSD", timeframe="M15", bars=1600, seed=5))["rows"]
    bars = build_bars(rows, "M15", "open")
    algo = DcAtrStructureAlgorithm(timeframe="M15", atr_multiplier=1.0)
    res = run_algorithm(bars, algo)
    reg = [e for e in res.events if e.structure_type.startswith("DC_REGIME") or
           e.structure_type in ("DC_RANGE_START", "DC_RANGE_EXIT")]
    assert reg
    for e in reg:
        assert e.event_bar_index == e.confirmed_bar_index          # không tô ngược
        assert e.details["tu_trang_thai"] != e.details["sang_trang_thai"]
    # timeline: trạng thái đổi đúng tại nến có regime event, không sớm hơn
    changes = {e.confirmed_bar_index: e.details["sang_trang_thai"] for e in reg}
    prev = None
    for p in res.timeline:
        st = p["regime"]
        if prev is not None and st != prev and st != "WARMUP" and prev != "WARMUP":
            assert changes.get(p["bar_index"]) == st
        prev = st
    # range entry luôn gắn pivot xác nhận ở cùng nến
    pivot_confirms = {e.confirmed_bar_index for e in res.events if e.structure_type in ("DC_HIGH", "DC_LOW")}
    for e in reg:
        if e.structure_type != "DC_RANGE_EXIT":
            assert e.confirmed_bar_index in pivot_confirms
    st = res.stats["chi_so_thuat_toan"]
    assert st["so_lan_chuyen_trang_thai"] == len(reg)
    assert sum(st["regime_so_nen"].values()) == st["so_nen_du_dieu_kien"]
    assert st["nhan_tham_chieu"]["co_nhan"] is False
