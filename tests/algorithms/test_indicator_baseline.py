"""Test baseline chỉ báo: chuỗi tính tay, warm-up, nhân quả."""
from __future__ import annotations

from core.algorithms.indicator_baseline import IndicatorBaselineAlgorithm
from core.engine import run_algorithm
from core.indicators import WilderADX, WilderATR, true_range
from core.types import DATA_STATUS_OK, DATA_STATUS_WARMUP, StructureType
from tests.helpers import make_bars, signature


def test_true_range_nen_dau_va_nen_sau():
    assert true_range(12.0, 10.0, None) == 2.0
    assert true_range(13.0, 11.0, 11.0) == 2.0
    assert true_range(15.0, 10.0, 12.0) == 5.0  # max(5, 3, 2)


def test_atr_wilder_tinh_tay_period_2():
    atr = WilderATR(2)
    assert atr.update(12.0, 10.0, 11.0) is None  # 1 TR, chưa seed
    assert atr.update(13.0, 11.0, 12.0) == 2.0   # SMA(TR=2, TR=2)
    assert atr.update(15.0, 12.0, 14.0) == 2.5   # (2*(2-1) + 3) / 2


def test_adx_warmup_2_nhan_period():
    adx = WilderADX(2)
    # 2*period = 4 nến mới có ADX (index 3)
    closes = []
    vals = []
    for i in range(6):
        h, l, c = 10.0 + i, 9.0 + i * 0.5, 9.5 + i
        vals.append(adx.update(h, l, c))
        closes.append(c)
    assert vals[0] is None
    assert vals[2] is None  # chưa đủ 2*2 nến
    assert vals[3] is not None
    assert adx.plus_di is not None


def test_baseline_warmup_khong_sinh_su_kien():
    algo = IndicatorBaselineAlgorithm(
        sma_period=5, slope_lookback=2, atr_period=3, adx_period=3, range_period=4
    )
    assert algo.warmup_bars() == max(7, 3, 6, 4)
    bars = make_bars([
        (10 + i * 0.1, 11 + i * 0.1, 9 + i * 0.1, 10.5 + i * 0.1) for i in range(5)
    ])
    res = run_algorithm(bars, algo)
    assert res.events == []
    assert res.data_status == DATA_STATUS_WARMUP


def test_baseline_chuoi_tang_sinh_up_sau_warmup():
    """Chuỗi tăng đều: sau warm-up phải ra BASELINE_UP (ADX và dốc dương)."""
    series = []
    px = 100.0
    for i in range(80):
        px += 0.8
        series.append((px - 0.3, px + 0.4, px - 0.5, px))
    bars = make_bars(series)
    algo = IndicatorBaselineAlgorithm(
        sma_period=5, slope_lookback=2, atr_period=5, adx_period=5, range_period=5,
        slope_min=0.05, adx_trend_min=10.0, range_narrow_max=8.0,
    )
    res = run_algorithm(bars, algo)
    assert res.data_status == DATA_STATUS_OK
    kinds = [e.structure_type for e in res.events]
    assert StructureType.BASELINE_UP in kinds
    first = res.events[0]
    assert first.confirmed_at == bars[first.confirmed_bar_index].close_time
    assert first.confirmation_lag_bars == 0
    assert first.confirmed_bar_index >= algo.warmup_bars() - 1


def test_baseline_them_du_lieu_sau_T_khong_doi_su_kien_tai_T():
    series = []
    px = 50.0
    for i in range(60):
        px += 0.4 if i < 40 else -0.5
        series.append((px - 0.2, px + 0.3, px - 0.4, px))
    bars = make_bars(series)
    algo_kw = dict(
        sma_period=5, slope_lookback=2, atr_period=4, adx_period=4, range_period=5,
        slope_min=0.05, adx_trend_min=8.0,
    )
    cut = 45
    prefix = run_algorithm(bars[:cut], IndicatorBaselineAlgorithm(**algo_kw)).events
    full = [
        e for e in run_algorithm(bars, IndicatorBaselineAlgorithm(**algo_kw)).events
        if e.confirmed_bar_index < cut
    ]
    assert signature(prefix) == signature(full)


def test_baseline_khong_nhin_tuong_lai_trong_on_bar():
    """Sửa nến sau T không đổi sự kiện đã xác nhận trước T."""
    series = [(10.0 + i * 0.2, 10.4 + i * 0.2, 9.7 + i * 0.2, 10.2 + i * 0.2) for i in range(50)]
    bars = make_bars(series)
    kw = dict(sma_period=4, slope_lookback=2, atr_period=4, adx_period=4, range_period=4)
    cut = 30
    base = [
        e for e in run_algorithm(bars, IndicatorBaselineAlgorithm(**kw)).events
        if e.confirmed_bar_index < cut
    ]
    series2 = list(series)
    for i in range(cut, 50):
        series2[i] = (1.0, 2.0, 0.5, 1.5)
    after = [
        e for e in run_algorithm(make_bars(series2), IndicatorBaselineAlgorithm(**kw)).events
        if e.confirmed_bar_index < cut
    ]
    assert signature(base) == signature(after)
