"""Test swing phân cấp trên chuỗi nhỏ có kết quả tính tay."""
from __future__ import annotations

from dataclasses import replace

from core.algorithms.swing_hierarchy import SwingHierarchyAlgorithm
from core.algorithms.swing_pivot import SwingPivotAlgorithm
from core.engine import run_algorithm
from core.types import StructureType
from tests.helpers import make_bars, signature, types_at


def _peak(high: float, low: float = 2900.0) -> tuple[float, float, float, float]:
    """Nến hợp lệ OHLC với high cho trước; low phẳng để không tạo đáy cấp 1."""
    mid = (high + low) / 2.0
    return (mid, high, low, mid)


def _trough(low: float, high: float = 3100.0) -> tuple[float, float, float, float]:
    mid = (high + low) / 2.0
    return (mid, high, low, mid)


# left=right=1. High: 2985, 2990, 2970, 3000, 2975, 2980, 2972, 2988, 2976, 2982,
# 2970, 3010, 2980, 2995, 2975
# Đỉnh cấp 1: 2990, 3000, 2980, 2988, 2982, 3010, 2995
# Đỉnh cấp 2: 3000 (không nhãn), 2988 LH, 3010 HH
EXAMPLE_HIGHS = [
    2985, 2990, 2970, 3000, 2975, 2980, 2972, 2988, 2976, 2982,
    2970, 3010, 2980, 2995, 2975,
]


def example_high_bars():
    return make_bars([_peak(h) for h in EXAMPLE_HIGHS])


def test_vi_du_dinh_cap_2_hh_lh():
    """Ví dụ đề xuất: cấp 1 có HH nhỏ tại 2988, cấp 2 gán LH cấu trúc."""
    events = SwingHierarchyAlgorithm(left=1, right=1).run(example_high_bars())
    assert signature(events) == [
        (StructureType.SWING_HIGH, 1, 2, 2990.0),
        (StructureType.SWING_HIGH, 3, 4, 3000.0),
        (StructureType.SWING_HIGH, 5, 6, 2980.0),
        (StructureType.SWING_HIGH_L2, 3, 6, 3000.0),
        (StructureType.SWING_HIGH, 7, 8, 2988.0),
        (StructureType.SWING_HIGH, 9, 10, 2982.0),
        (StructureType.SWING_HIGH_L2, 7, 10, 2988.0),
        (StructureType.LH, 7, 10, 2988.0),
        (StructureType.SWING_HIGH, 11, 12, 3010.0),
        (StructureType.SWING_HIGH, 13, 14, 2995.0),
        (StructureType.SWING_HIGH_L2, 11, 14, 3010.0),
        (StructureType.HH, 11, 14, 3010.0),
    ]
    lh = types_at(events, StructureType.LH)[0]
    assert lh.details["cap_do"] == 2
    assert lh.details["gia_swing_truoc"] == 3000.0
    assert lh.reference_event_id == "SWING_HIGH_L2@3>6"
    # Không phát HH cấp 1 (2988 > 2980 sẽ là HH nhỏ nếu so fractal).
    assert all(e.structure_type != StructureType.HH or e.price == 3010.0 for e in events)


def test_cung_chuoi_swing_pivot_van_gan_hh_cap_1():
    """Đổi cách chọn đỉnh, không đổi swing_pivot 1.1.0: 2988 vẫn là HH cấp 1."""
    events = SwingPivotAlgorithm(left=1, right=1, enable_bos=False).run(example_high_bars())
    hh_prices = [e.price for e in types_at(events, StructureType.HH)]
    assert 2988.0 in hh_prices


def test_khong_gan_cap_2_ve_luc_dinh_giua_hinh_thanh():
    """Cấp 2 của 3000 chỉ khả dụng khi đỉnh cấp 1 bên phải (2980) đã xác nhận."""
    bars = example_high_bars()
    # Nến 4 đóng: đỉnh 3000 vừa xác nhận cấp 1; mới có 2 đỉnh cấp 1 → chưa L2.
    at_mid = SwingHierarchyAlgorithm(left=1, right=1).run(bars[:5])
    assert types_at(at_mid, StructureType.SWING_HIGH_L2) == []
    assert [e.price for e in types_at(at_mid, StructureType.SWING_HIGH)] == [2990.0, 3000.0]

    # Nến 6 đóng: đỉnh 2980 xác nhận → L2 tại nến 3, confirmed_at = close nến 6.
    at_right = SwingHierarchyAlgorithm(left=1, right=1).run(bars[:7])
    l2 = types_at(at_right, StructureType.SWING_HIGH_L2)
    assert signature(l2) == [(StructureType.SWING_HIGH_L2, 3, 6, 3000.0)]
    assert l2[0].confirmed_at == bars[6].close_time
    assert l2[0].event_time == bars[3].bar_time
    assert l2[0].confirmation_lag_bars == 3


def test_cap_2_dau_khong_co_nhan():
    events = SwingHierarchyAlgorithm(left=1, right=1).run(example_high_bars()[:7])
    assert types_at(events, StructureType.HH) == []
    assert types_at(events, StructureType.LH) == []
    assert types_at(events, StructureType.EQH) == []
    assert len(types_at(events, StructureType.SWING_HIGH_L2)) == 1


def test_khong_phat_bos():
    events = SwingHierarchyAlgorithm(left=1, right=1).run(example_high_bars())
    assert not any("BOS" in e.structure_type or "CHOCH" in e.structure_type for e in events)


def test_tat_emit_level1_chi_con_cap_2():
    events = SwingHierarchyAlgorithm(left=1, right=1, emit_level1=False).run(
        example_high_bars()
    )
    assert types_at(events, StructureType.SWING_HIGH) == []
    assert signature(types_at(events, StructureType.SWING_HIGH_L2)) == [
        (StructureType.SWING_HIGH_L2, 3, 6, 3000.0),
        (StructureType.SWING_HIGH_L2, 7, 10, 2988.0),
        (StructureType.SWING_HIGH_L2, 11, 14, 3010.0),
    ]


def test_giua_khong_cao_hon_ca_hai_canh_khong_la_cap_2():
    """10, 9, 11: đỉnh giữa không phải cấp 2."""
    highs = [8.0, 10.0, 7.0, 9.0, 8.0, 11.0, 8.5]
    bars = make_bars([_peak(h, low=1.0) for h in highs])
    events = SwingHierarchyAlgorithm(left=1, right=1).run(bars)
    assert types_at(events, StructureType.SWING_HIGH_L2) == []
    assert [e.price for e in types_at(events, StructureType.SWING_HIGH)] == [10.0, 9.0, 11.0]


def test_bang_gia_khong_la_cap_2():
    """Pk == P{k+1} không thoả Pk > P{k+1}."""
    highs = [8.0, 12.0, 7.0, 10.0, 8.0, 10.0, 7.5]
    bars = make_bars([_peak(h, low=1.0) for h in highs])
    events = SwingHierarchyAlgorithm(left=1, right=1).run(bars)
    assert types_at(events, StructureType.SWING_HIGH_L2) == []


def test_eqh_cap_2_khi_hai_dinh_cap_2_bang_nhau():
    # L1: 10, 12, 11, 9, 12, 10 → L2: 12 rồi 12 → EQH
    highs = [8.0, 10.0, 7.0, 12.0, 8.0, 11.0, 8.5, 9.0, 7.0, 12.0, 8.0, 10.0, 7.5]
    bars = make_bars([_peak(h, low=1.0) for h in highs])
    events = SwingHierarchyAlgorithm(left=1, right=1).run(bars)
    l2 = types_at(events, StructureType.SWING_HIGH_L2)
    assert [e.price for e in l2] == [12.0, 12.0]
    eqh = types_at(events, StructureType.EQH)
    assert len(eqh) == 1
    assert eqh[0].price == 12.0
    assert eqh[0].reason_code == "SEQ_EQUAL_HIGH_L2"


def test_day_cap_2_ll():
    lows = [
        110.0, 100.0, 108.0, 90.0, 105.0, 95.0, 104.0, 92.0, 103.0, 80.0,
        102.0, 85.0, 100.0,
    ]
    bars = make_bars([_trough(x) for x in lows])
    events = SwingHierarchyAlgorithm(left=1, right=1).run(bars)
    # L1 lows: 100, 90, 95, 92, 80, 85
    # L2: 90 (đầu), rồi 80 → LL
    l2 = types_at(events, StructureType.SWING_LOW_L2)
    assert [e.price for e in l2] == [90.0, 80.0]
    assert signature(types_at(events, StructureType.LL)) == [
        (StructureType.LL, 9, 12, 80.0),
    ]
    assert types_at(events, StructureType.HL) == []


def test_warmup_chua_du_nen():
    bars = example_high_bars()[:2]
    events = SwingHierarchyAlgorithm(left=1, right=1).run(bars)
    assert events == []
    res = run_algorithm(bars, SwingHierarchyAlgorithm(left=1, right=1))
    assert res.warmup_bars == 3


def test_them_du_lieu_sau_T_khong_doi_su_kien_da_xac_nhan():
    bars = example_high_bars()
    cut = 9
    prefix = run_algorithm(bars[:cut], SwingHierarchyAlgorithm(left=1, right=1)).events
    full = run_algorithm(bars, SwingHierarchyAlgorithm(left=1, right=1)).events
    full_upto = [e for e in full if e.confirmed_bar_index < cut]
    assert signature(prefix) == signature(full_upto)


def test_sua_du_lieu_sau_T_khong_doi_su_kien_da_xac_nhan():
    bars = example_high_bars()
    cut = 8
    base = [
        e
        for e in run_algorithm(bars, SwingHierarchyAlgorithm(left=1, right=1)).events
        if e.confirmed_bar_index < cut
    ]
    tampered = list(bars[:cut])
    for b in bars[cut:]:
        tampered.append(replace(b, high=b.high + 80, close=b.close + 40))
    after = [
        e
        for e in run_algorithm(tampered, SwingHierarchyAlgorithm(left=1, right=1)).events
        if e.confirmed_bar_index < cut
    ]
    assert signature(base) == signature(after)


def test_confirmed_at_bang_close_nen_dang_xu_ly():
    bars = example_high_bars()
    algo = SwingHierarchyAlgorithm(left=1, right=1)
    for bar in bars:
        for e in algo.on_bar(bar):
            assert e.confirmed_at == bar.close_time
            assert e.confirmed_bar_index == bar.index
            assert e.algorithm == "swing_hierarchy"
            assert e.algorithm_version == "1.0.0"
            assert e.structure_type in StructureType.ALL
