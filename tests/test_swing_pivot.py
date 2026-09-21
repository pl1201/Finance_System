"""Test thuật toán Swing Pivot trên các chuỗi nhỏ có kết quả tính tay."""
from __future__ import annotations

import pytest

from core.algorithms.swing_pivot import SwingPivotAlgorithm
from core.engine import run_algorithm
from core.types import DATA_STATUS_OK, DATA_STATUS_WARMUP, StructureType
from tests.helpers import make_bars, signature, types_at


# ---------------------------------------------------------------------------
# 1. Pivot trên chuỗi nhỏ, kết quả tính tay
# ---------------------------------------------------------------------------

# idx:      0                1                 2                3                4                 5
# high:    10               12                11                9               13                11
# low:      8                9                 7                5                9                 8
HAND_SERIES = [
    (9.0, 10.0, 8.0, 9.5),
    (9.5, 12.0, 9.0, 11.0),
    (11.0, 11.0, 7.0, 8.0),
    (8.0, 9.0, 5.0, 6.0),
    (9.5, 13.0, 9.0, 12.0),
    (9.5, 11.0, 8.0, 9.0),
]


def test_pivot_tinh_tay_left1_right1():
    """left=1, right=1: chỉ có SWING_HIGH@1, SWING_LOW@3, SWING_HIGH@4 (+ nhãn HH)."""
    bars = make_bars(HAND_SERIES)
    algo = SwingPivotAlgorithm(left=1, right=1)
    events = algo.run(bars)

    assert signature(events) == [
        (StructureType.SWING_HIGH, 1, 2, 12.0),
        (StructureType.SWING_LOW, 3, 4, 5.0),
        (StructureType.SWING_HIGH, 4, 5, 13.0),
        (StructureType.HH, 4, 5, 13.0),
    ]


def test_pivot_khong_co_bos_trong_chuoi_nay():
    bars = make_bars(HAND_SERIES)
    events = SwingPivotAlgorithm(left=1, right=1).run(bars)
    assert not types_at(events, StructureType.BOS_UP)
    assert not types_at(events, StructureType.BOS_DOWN)


def test_pivot_cua_so_rong_hon_loai_bot_pivot():
    """left=2, right=2 trên cùng chuỗi: chỉ còn pivot ở giữa chuỗi."""
    bars = make_bars(HAND_SERIES)
    events = SwingPivotAlgorithm(left=2, right=2).run(bars)
    # c phải thoả c >= 2 và c + 2 <= 5  ->  c thuộc {2, 3}
    # c=2: high 11 < 12 -> không; low 7 < (10?) ... low[0..1]=8,9 và low[3..4]=5,9 -> 7 < 5 sai
    # c=3: high 9 -> không; low 5 < 9,7 và < 9,8 -> đúng
    assert signature(events) == [(StructureType.SWING_LOW, 3, 5, 5.0)]


# ---------------------------------------------------------------------------
# 2. Nến bằng giá
# ---------------------------------------------------------------------------


def test_high_bang_nhau_khong_tao_pivot():
    """Hai high bằng nhau cạnh nhau: không nến nào được nhận là pivot."""
    bars = make_bars([
        (9.0, 10.0, 8.0, 9.5),
        (9.5, 12.0, 9.0, 11.0),
        (11.0, 12.0, 9.5, 11.5),   # high bằng đúng nến trước
        (8.8, 9.0, 8.0, 8.5),
    ])
    events = SwingPivotAlgorithm(left=1, right=1, enable_bos=False).run(bars)
    assert not types_at(events, StructureType.SWING_HIGH)


def test_low_bang_nhau_khong_tao_pivot():
    bars = make_bars([
        (9.0, 10.0, 8.0, 9.5),
        (9.5, 9.6, 7.0, 8.0),
        (8.0, 9.0, 7.0, 8.5),      # low bằng đúng nến trước
        (8.5, 10.0, 8.0, 9.5),
    ])
    events = SwingPivotAlgorithm(left=1, right=1, enable_bos=False).run(bars)
    assert not types_at(events, StructureType.SWING_LOW)


EQ_SERIES = [
    (9.0, 10.0, 8.0, 9.0),
    (9.0, 12.0, 9.0, 11.0),     # swing high = 12
    (8.5, 9.0, 7.0, 7.5),
    (7.5, 8.0, 6.0, 7.0),       # swing low = 6
    (9.5, 12.0, 9.0, 11.0),     # swing high = 12 -> BẰNG đỉnh trước
    (8.9, 9.0, 8.0, 8.5),
    (8.5, 8.6, 7.0, 7.2),
]


def test_hai_dinh_bang_nhau_nhan_EQH_khong_ep_thanh_HH_hay_LH():
    bars = make_bars(EQ_SERIES)
    events = SwingPivotAlgorithm(left=1, right=1).run(bars)
    labels = [e.structure_type for e in events]
    assert StructureType.EQH in labels
    assert StructureType.HH not in labels
    assert StructureType.LH not in labels
    eqh = types_at(events, StructureType.EQH)[0]
    assert eqh.event_bar_index == 4 and eqh.confirmed_bar_index == 5
    assert eqh.reference_event_id == "SWING_HIGH@1>2"


def test_dung_sai_bang_gia_gan_nhan_EQH():
    """Chênh lệch nhỏ hơn dung sai vẫn là EQH, lớn hơn thì thành HH."""
    series = list(EQ_SERIES)
    series[4] = (9.5, 12.05, 9.0, 11.0)   # đỉnh thứ hai cao hơn 0.05
    bars = make_bars(series)

    labels_tight = [e.structure_type for e in SwingPivotAlgorithm(left=1, right=1).run(bars)]
    assert StructureType.HH in labels_tight

    labels_loose = [
        e.structure_type
        for e in SwingPivotAlgorithm(left=1, right=1, label_eq_tolerance=0.1).run(bars)
    ]
    assert StructureType.EQH in labels_loose
    assert StructureType.HH not in labels_loose


# ---------------------------------------------------------------------------
# 3. Warm-up và thời điểm xác nhận
# ---------------------------------------------------------------------------


def test_warmup_thieu_khong_sinh_su_kien():
    algo = SwingPivotAlgorithm(left=3, right=3)
    assert algo.warmup_bars() == 7
    bars = make_bars([(10 + i * 0.1, 11 + i * 0.1, 9 + i * 0.1, 10.5 + i * 0.1) for i in range(6)])
    res = run_algorithm(bars, algo)
    assert res.events == []
    assert res.data_status == DATA_STATUS_WARMUP
    assert "warm-up" in res.data_status_message_vi.lower()


def test_du_warmup_thi_trang_thai_ok():
    algo = SwingPivotAlgorithm(left=1, right=1)
    res = run_algorithm(make_bars(HAND_SERIES), algo)
    assert res.data_status == DATA_STATUS_OK


@pytest.mark.parametrize("right", [1, 2, 3, 5])
def test_do_tre_xac_nhan_dung_bang_so_nen_phai(right):
    """Pivot chỉ được xác nhận khi nến bên phải CUỐI CÙNG đã đóng."""
    n = 2 * right + 5
    series = []
    peak = right + 2
    for i in range(n):
        base = 10.0 - abs(i - peak) * 0.5
        series.append((base - 0.1, base, base - 1.0, base - 0.2))
    bars = make_bars(series)
    events = SwingPivotAlgorithm(left=right, right=right, enable_bos=False).run(bars)
    highs = types_at(events, StructureType.SWING_HIGH)
    assert highs, "Phải có ít nhất một swing high"
    for e in highs:
        assert e.confirmation_lag_bars == right
        assert e.confirmed_bar_index == e.event_bar_index + right
        assert e.confirmed_at == bars[e.confirmed_bar_index].close_time
        assert e.event_time == bars[e.event_bar_index].bar_time


def test_confirmed_at_khac_event_time_va_dung_close_time():
    bars = make_bars(HAND_SERIES)
    events = SwingPivotAlgorithm(left=1, right=1).run(bars)
    sh = types_at(events, StructureType.SWING_HIGH)[0]
    assert sh.event_time == bars[1].bar_time
    assert sh.event_close_time == bars[1].close_time
    assert sh.confirmed_at == bars[2].close_time
    # Quy ước 'open': close_time = bar_time + 1 giờ.
    assert (sh.event_close_time - sh.event_time).total_seconds() == 3600
    assert sh.confirmed_at > sh.event_close_time


def test_quy_uoc_timestamp_close_thi_close_time_bang_bar_time():
    bars = make_bars(HAND_SERIES, convention="close")
    events = SwingPivotAlgorithm(left=1, right=1).run(bars)
    sh = types_at(events, StructureType.SWING_HIGH)[0]
    assert sh.event_close_time == sh.event_time
    assert sh.confirmed_at == bars[2].bar_time


# ---------------------------------------------------------------------------
# 4. Quy tắc BOS và chống phát lặp
# ---------------------------------------------------------------------------

BOS_SERIES = [
    (10.0, 10.5, 9.5, 10.0),
    (10.0, 12.0, 9.8, 11.0),     # 1: swing high = 12
    (11.0, 11.5, 10.5, 11.0),    # 2: xác nhận swing high@1
    (11.0, 13.0, 10.9, 12.5),    # 3: close 12.5 > 12  -> BOS_UP
    (12.5, 13.5, 12.4, 13.2),    # 4: close cao hơn nữa nhưng mức đã bị phá
    (13.2, 13.6, 13.0, 13.4),    # 5: swing high = 13.6
    (13.4, 13.5, 12.0, 12.5),    # 6: xác nhận swing high@5 và swing low@6=12
    (12.5, 14.0, 12.4, 13.9),    # 7: close 13.9 > 13.6 -> BOS_UP thứ hai
    (13.9, 14.0, 13.5, 13.7),
]


def test_bos_phat_dung_mot_lan_cho_moi_muc():
    bars = make_bars(BOS_SERIES)
    events = SwingPivotAlgorithm(left=1, right=1).run(bars)
    bos = types_at(events, StructureType.BOS_UP)
    assert [e.confirmed_bar_index for e in bos] == [3, 7]
    assert [e.price for e in bos] == [12.0, 13.6]
    assert [e.reference_event_id for e in bos] == ["SWING_HIGH@1>2", "SWING_HIGH@5>6"]
    # BOS dùng close của chính nến đang xét -> không có độ trễ.
    assert all(e.confirmation_lag_bars == 0 for e in bos)
    assert all(e.event_bar_index == e.confirmed_bar_index for e in bos)


def test_bos_khong_phat_lai_tren_cung_mot_muc():
    """Bar 4 có close cao hơn bar 3 nhưng mức 12 đã bị phá -> không phát lại."""
    bars = make_bars(BOS_SERIES)
    events = SwingPivotAlgorithm(left=1, right=1).run(bars)
    bos_at_4 = [e for e in events if e.structure_type == StructureType.BOS_UP and e.confirmed_bar_index == 4]
    assert bos_at_4 == []


def test_bien_pha_vo_chan_bos_bien_do_nho():
    bars = make_bars(BOS_SERIES)
    ít = SwingPivotAlgorithm(left=1, right=1, bos_buffer=0.0).run(bars)
    nhiều = SwingPivotAlgorithm(left=1, right=1, bos_buffer=1.0).run(bars)
    assert len(types_at(ít, StructureType.BOS_UP)) == 2
    # Với biên 1.0: close 12.5 tại nến 3 chỉ vượt mức 12 đúng 0.5 nên không tính;
    # phải tới nến 4 (close 13.2 > 12 + 1.0) mới phát BOS. Mức 13.6 sau đó không
    # bị phá vì close cao nhất 13.9 < 13.6 + 1.0.
    assert [e.confirmed_bar_index for e in types_at(nhiều, StructureType.BOS_UP)] == [4]


def test_bos_dung_close_khong_dung_wick():
    """Bar 3 có high 13 > 12 nhưng nếu close <= 12 thì không có BOS."""
    series = list(BOS_SERIES)
    series[3] = (11.0, 13.0, 10.9, 11.8)   # wick vượt 12, close 11.8 không vượt
    bars = make_bars(series)
    events = SwingPivotAlgorithm(left=1, right=1).run(bars)
    assert [e.confirmed_bar_index for e in types_at(events, StructureType.BOS_UP)] != [3]


def test_tat_bos_thi_khong_co_su_kien_bos():
    bars = make_bars(BOS_SERIES)
    events = SwingPivotAlgorithm(left=1, right=1, enable_bos=False).run(bars)
    assert not types_at(events, StructureType.BOS_UP)
    assert not types_at(events, StructureType.BOS_DOWN)


def test_bos_xuong_doi_xung():
    series = [(h, hi, lo, c) for (h, hi, lo, c) in BOS_SERIES]
    # Lật chuỗi quanh giá 24 để tạo gương: high <-> low.
    mirrored = [(24 - o, 24 - l, 24 - h, 24 - c) for (o, h, l, c) in series]
    bars = make_bars(mirrored)
    events = SwingPivotAlgorithm(left=1, right=1).run(bars)
    down = types_at(events, StructureType.BOS_DOWN)
    assert [e.confirmed_bar_index for e in down] == [3, 7]


# ---------------------------------------------------------------------------
# 5. Trường tổng quát của sự kiện
# ---------------------------------------------------------------------------


def test_moi_su_kien_co_du_truong_bat_buoc():
    bars = make_bars(BOS_SERIES)
    algo = SwingPivotAlgorithm(left=1, right=1)
    events = algo.run(bars)
    assert events
    ids = set()
    for e in events:
        assert e.event_id and e.event_id not in ids
        ids.add(e.event_id)
        assert e.structure_type in StructureType.ALL
        assert e.algorithm == "swing_pivot"
        assert e.algorithm_version == algo.version
        assert e.reason_code
        assert e.confirmed_bar_index >= e.event_bar_index
        d = e.to_dict()
        assert d["reason_text_vi"], "Mã lý do %s thiếu giải thích tiếng Việt" % e.reason_code
        assert d["structure_text_vi"]


def test_nhan_hh_hl_lh_ll_tham_chieu_dung_swing_truoc():
    bars = make_bars(BOS_SERIES)
    events = SwingPivotAlgorithm(left=1, right=1).run(bars)
    by_id = {e.event_id: e for e in events}
    for e in events:
        if e.structure_type in (StructureType.HH, StructureType.LH, StructureType.EQH):
            ref = by_id[e.reference_event_id]
            assert ref.structure_type == StructureType.SWING_HIGH
            assert ref.confirmed_bar_index < e.confirmed_bar_index
        if e.structure_type in (StructureType.HL, StructureType.LL, StructureType.EQL):
            ref = by_id[e.reference_event_id]
            assert ref.structure_type == StructureType.SWING_LOW


def test_nap_nen_sai_thu_tu_bi_tu_choi():
    bars = make_bars(HAND_SERIES)
    algo = SwingPivotAlgorithm(left=1, right=1)
    algo.on_bar(bars[2])
    with pytest.raises(ValueError):
        algo.on_bar(bars[1])


def test_tham_so_khong_hop_le_bi_tu_choi():
    with pytest.raises(ValueError):
        SwingPivotAlgorithm(left=0, right=3)
    with pytest.raises(ValueError):
        SwingPivotAlgorithm(left=3, right=-1)
    with pytest.raises(ValueError):
        SwingPivotAlgorithm(left="ba", right=3)
