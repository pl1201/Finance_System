"""CHoCH / BOS nội bộ / BOS chính trên chuỗi nhỏ tính tay (swing_pivot 1.1.0).

Chuỗi dùng left=1, right=1. Mỗi nến ghi chú pivot/phá vỡ kỳ vọng.
"""
from __future__ import annotations

from core.algorithms.swing_pivot import SwingPivotAlgorithm
from core.engine import run_algorithm
from core.types import StructureType
from tests.helpers import make_bars, signature, types_at


# idx:  0     1 SH=12   2         3 SL=8    4         5 SH=16 + BOS_UP
#       6 HH           7 SL=10   8 HL+bias 9 CHoCH_DOWN (close 9.5 < HL 10)
CHOCH_SERIES = [
    (10.0, 10.5, 9.8, 10.2),   # 0
    (10.2, 12.0, 10.0, 11.5),  # 1  swing high 12
    (11.5, 11.6, 10.8, 11.0),  # 2  xác nhận SH@1
    (11.0, 11.2, 8.0, 8.5),    # 3  swing low 8
    (8.5, 9.5, 8.2, 9.0),      # 4  xác nhận SL@3
    (9.0, 16.0, 8.9, 15.0),    # 5  close 15 > 12 → BOS_UP (bias còn none)
    (15.0, 15.2, 14.5, 14.8),  # 6  xác nhận SH@5 = HH
    (14.8, 15.0, 10.0, 10.5),  # 7  swing low 10
    (10.5, 12.0, 10.2, 11.5),  # 8  xác nhận SL@7 = HL → bias bullish
    (11.5, 12.0, 9.0, 9.5),    # 9  close 9.5 < 10 (HL) → CHOCH_DOWN
]


def _sp(**kw):
    params = dict(left=1, right=1)
    params.update(kw)
    return SwingPivotAlgorithm(**params)


def test_choch_giam_tinh_tay_sau_hh_hl():
    """HH rồi HL → bias tăng; close thủng HL là CHoCH giảm, không phải BOS_DOWN."""
    bars = make_bars(CHOCH_SERIES)
    events = _sp().run(bars)

    assert types_at(events, StructureType.HH)[0].event_bar_index == 5
    assert types_at(events, StructureType.HL)[0].event_bar_index == 7
    bos_up = types_at(events, StructureType.BOS_UP)
    assert [e.confirmed_bar_index for e in bos_up] == [5]

    choch = types_at(events, StructureType.CHOCH_DOWN)
    assert len(choch) == 1
    e = choch[0]
    assert e.confirmed_bar_index == 9
    assert e.event_bar_index == 9
    assert e.confirmation_lag_bars == 0
    assert e.price == 10.0
    assert e.confirmed_at == bars[9].close_time
    assert e.details["phan_loai"] == "choch"
    assert e.details["bias_truoc"] == "bullish"
    assert e.details["bias_sau"] == "bearish"
    assert not types_at(events, StructureType.BOS_DOWN)
    assert not types_at(events, StructureType.BOS_INTERNAL_DOWN)


def test_tat_choch_thi_pha_hl_van_la_bos_down():
    bars = make_bars(CHOCH_SERIES)
    events = _sp(enable_choch=False).run(bars)
    assert not types_at(events, StructureType.CHOCH_DOWN)
    assert not types_at(events, StructureType.BOS_INTERNAL_UP)
    down = types_at(events, StructureType.BOS_DOWN)
    assert [e.confirmed_bar_index for e in down] == [9]


# Sau nến 8 (bias tăng, HH=16, HL=10): đỉnh hồi 14 rồi close xuyên 14 nhưng chưa 16.
INTERNAL_SERIES = CHOCH_SERIES[:9] + [
    (11.5, 14.0, 11.0, 13.0),  # 9  swing high nội bộ 14
    (13.0, 13.2, 12.5, 12.8),  # 10 xác nhận SH@9 = LH
    (12.8, 14.8, 12.6, 14.3),  # 11 close 14.3 > 14, < 16 → BOS_INTERNAL_UP
]


def test_bos_noi_bo_len_tinh_tay():
    bars = make_bars(INTERNAL_SERIES)
    events = _sp().run(bars)
    internal = types_at(events, StructureType.BOS_INTERNAL_UP)
    assert len(internal) == 1
    e = internal[0]
    assert e.confirmed_bar_index == 11
    assert e.price == 14.0
    assert e.details["phan_loai"] == "noi_bo"
    assert e.details["bias_truoc"] == "bullish"
    assert e.details["muc_chinh"] == 16.0
    assert not types_at(events, StructureType.CHOCH_UP)
    # chưa phá HH 16
    assert all(e.confirmed_bar_index != 11 for e in types_at(events, StructureType.BOS_UP))


MAJOR_THROUGH_INTERNAL = CHOCH_SERIES[:9] + [
    (11.5, 14.0, 11.0, 13.0),  # 9  đỉnh nội bộ 14
    (13.0, 13.2, 12.5, 12.8),  # 10 xác nhận LH
    (12.8, 17.0, 12.6, 16.5),  # 11 close 16.5 > 14 và > 16 → chỉ BOS_UP (chính)
]


def test_cung_nen_xuyen_noi_bo_va_chinh_chi_phat_bos_chinh():
    bars = make_bars(MAJOR_THROUGH_INTERNAL)
    events = _sp().run(bars)
    at_11 = [e for e in events if e.confirmed_bar_index == 11]
    kinds = [e.structure_type for e in at_11]
    assert StructureType.BOS_UP in kinds
    assert StructureType.BOS_INTERNAL_UP not in kinds
    bos = types_at(events, StructureType.BOS_UP)
    last = [e for e in bos if e.confirmed_bar_index == 11][0]
    assert last.details["phan_loai"] == "chinh"
    assert last.price == 14.0  # tham chiếu mức active (nội bộ), phân loại theo mức chính


def test_choch_doi_xung_len():
    """Lật chuỗi CHoCH quanh 24: CHoCH_DOWN → CHOCH_UP."""
    mirrored = [(24 - o, 24 - l, 24 - h, 24 - c) for (o, h, l, c) in CHOCH_SERIES]
    bars = make_bars(mirrored)
    events = _sp().run(bars)
    up = types_at(events, StructureType.CHOCH_UP)
    assert len(up) == 1
    assert up[0].confirmed_bar_index == 9
    assert not types_at(events, StructureType.CHOCH_DOWN)


def test_warmup_choch_khong_doi():
    algo = _sp(left=3, right=3)
    assert algo.warmup_bars() == 7


def test_them_nen_sau_choch_khong_doi_su_kien_da_xac_nhan():
    bars = make_bars(CHOCH_SERIES)
    prefix = run_algorithm(bars, _sp()).events
    longer_ohlc = CHOCH_SERIES + [(9.5, 20.0, 9.0, 19.0), (19.0, 19.5, 18.0, 18.5)]
    longer = make_bars(longer_ohlc)
    cut = len(bars)
    full = [e for e in run_algorithm(longer, _sp()).events if e.confirmed_bar_index < cut]
    assert signature(prefix) == signature(full)


def test_sua_du_lieu_sau_T_khong_doi_choch_da_xac_nhan():
    bars = make_bars(CHOCH_SERIES)
    cut = 9  # CHoCH xác nhận tại nến 9; T = trước nến cuối
    base = [e for e in run_algorithm(bars, _sp()).events if e.confirmed_bar_index < cut]
    tampered_ohlc = list(CHOCH_SERIES)
    tampered_ohlc[-1] = (11.5, 30.0, 1.0, 25.0)
    after = [
        e for e in run_algorithm(make_bars(tampered_ohlc), _sp()).events
        if e.confirmed_bar_index < cut
    ]
    assert signature(base) == signature(after)
