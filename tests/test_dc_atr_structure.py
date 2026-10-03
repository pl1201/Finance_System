"""Test dc_atr_structure: ATR seed, detector DC, nhãn, gap, validate, nhân quả.

Fixture tính tay dùng giá có biểu diễn nhị phân chính xác (bội số 0.25/0.5)
để so sánh đúng ngưỡng không bị sai số float.
"""
from __future__ import annotations

import copy
import math
from dataclasses import replace
from datetime import timedelta

import pytest

from core.algorithms.dc_atr_structure import (
    PHASE_SEEK_DIRECTION,
    PHASE_SEEK_HIGH,
    PHASE_SEEK_LOW,
    PHASE_WAIT_ATR,
    PHASE_WARMUP,
    DcAtrStructureAlgorithm,
    DcDetector,
)
from core.data.synthetic import SyntheticSpec, generate
from core.engine import ReplaySession, run_algorithm
from core.indicators import WilderATR, WilderATRPrevClose
from core.registry import get_algorithm_class, list_algorithms
from core.types import build_bars
from tests.helpers import make_bars


def closes_to_bars(closes, wick=0.25, timeframe="M15"):
    """Nến có close cho trước; high/low = close ± wick (open = close)."""
    return make_bars([(c, c + wick, c - wick, c) for c in closes], timeframe=timeframe)


def dc_algo(**kw):
    params = dict(timeframe="M15")
    params.update(kw)
    return DcAtrStructureAlgorithm(**params)


def pivots(events):
    return [e for e in events if e.structure_type in ("DC_HIGH", "DC_LOW")]


# ---------------------------------------------------------------------------
# ATR Wilder (seed theo spec)
# ---------------------------------------------------------------------------


def test_atr_seed_va_wilder_tinh_tay():
    atr = WilderATRPrevClose(3)
    rows = [(10, 8, 9), (11, 9, 10), (13, 10, 12), (12, 11, 11.5), (15, 11, 14)]
    out = [atr.update(h, l, c) for h, l, c in rows]
    # nến 0 chỉ lấy close trước; TR: 2, 3, 1 → seed 2 tại nến 3 (cần n+1 nến)
    assert out[:3] == [None, None, None]
    assert out[3] == pytest.approx(2.0)
    # TR[4] = max(4, |15-11.5|, |11-11.5|) = 4 → (2*2 + 4) / 3
    assert out[4] == pytest.approx(8.0 / 3.0)


def test_atr_moi_khac_seed_atr_cu_va_khong_doi_atr_cu():
    rows = [(10, 8, 9), (11, 9, 10), (13, 10, 12), (12, 11, 11.5)]
    old = WilderATR(3)
    vals = [old.update(h, l, c) for h, l, c in rows]
    # ATR cũ: TR nến đầu = high-low = 2 → seed (2+2+3)/3 tại nến 2 — giữ nguyên.
    assert vals[2] == pytest.approx(7.0 / 3.0)


def test_warmup_can_n_cong_1_nen():
    a = dc_algo(atr_period=5)
    assert a.warmup_bars() == 6
    bars = closes_to_bars([100 + 0.25 * i for i in range(6)])
    for b in bars[:5]:
        a.on_bar(b)
        assert a.pending_state()["dc"]["phase"] == PHASE_WARMUP
        assert a.pending_state()["regime"] == "WARMUP"
    a.on_bar(bars[5])
    assert a.pending_state()["atr_hien_tai"] is not None
    assert a.pending_state()["dc"]["phase"] == PHASE_SEEK_DIRECTION


# ---------------------------------------------------------------------------
# Detector DC (ATR truyền tay, tách khỏi ATR thật)
# ---------------------------------------------------------------------------


def feed(det, closes, atrs):
    bars = closes_to_bars(closes, wick=5.0)
    return [det.update(b, a) for b, a in zip(bars, atrs)], bars


def test_khoi_tao_cho_huong_khong_phat_pivot_o_anchor():
    det = DcDetector("atr", 1.0, 0.2)
    out, _ = feed(det, [100, 100, 100.5, 101], [None, 1, 1, 1])
    assert out == [None, None, None, None]
    # nến 1: anchor 100, Δ 1. Nến 3 chạm 101 = anchor + Δ → SEEK_HIGH, ứng viên 101.
    assert det.phase == PHASE_SEEK_HIGH
    assert det.candidate.price == 101 and det.candidate.index == 3


def test_reversal_thieu_dung_vuot_nguong():
    closes = [100, 100, 101, 103, 102.25, 102]
    det = DcDetector("atr", 1.0, 0.2)
    out, _ = feed(det, closes, [None, 1, 1, 1, 1, 1])
    assert out[4] is None                       # 102.25 > 103 - 1: thiếu ngưỡng
    p = out[5]                                  # 102 = 103 - 1: chạm là đạt
    assert p is not None and p.kind == "high"
    assert (p.price, p.extreme_index, p.confirm_index) == (103, 3, 5)
    assert det.phase == PHASE_SEEK_LOW and det.candidate.price == 102
    det2 = DcDetector("atr", 1.0, 0.2)
    out2, _ = feed(det2, [100, 100, 101, 103, 101.5], [None, 1, 1, 1, 1])
    assert out2[4] is not None and out2[4].confirm_close == 101.5   # vượt ngưỡng


def test_nguong_khoa_khi_atr_doi_nhung_ung_vien_khong_doi():
    det = DcDetector("atr", 1.0, 0.2)
    # ứng viên 103 khoá Δ=1 (ATR=1); sau đó ATR tăng 10 nhưng Δ không đổi.
    out, _ = feed(det, [100, 100, 101, 103, 102.5, 102], [None, 1, 1, 1, 10, 10])
    assert out[5] is not None and out[5].delta == 1.0
    assert out[5].atr_at_extreme == 1.0


def test_ung_vien_moi_khoa_nguong_moi():
    det = DcDetector("atr", 1.0, 0.2)
    out, _ = feed(det, [100, 100, 101, 103, 104, 103], [None, 1, 1, 1, 4, 1])
    assert out[5] is None                       # Δ mới = 4 (khoá tại 104)
    assert det.candidate.price == 104 and det.candidate.delta == 4.0
    assert det.candidate.threshold_set_at is not None


def test_dinh_bang_nhau_giu_nen_dau():
    det = DcDetector("atr", 1.0, 0.2)
    out, _ = feed(det, [100, 100, 101, 103, 103, 102], [None, 1, 1, 1, 7, 7])
    assert out[5] is not None
    assert out[5].extreme_index == 3 and out[5].delta == 1.0


def test_day_doi_xung():
    det = DcDetector("atr", 2.0, 0.2)
    out, _ = feed(det, [100, 100, 98, 97, 97.5, 99], [None, 0.5, 0.5, 0.5, 0.5, 0.5])
    # Δ = 2 × 0.5 = 1. Nến 2: 98 ≤ 99 → SEEK_LOW; đáy 97; 98 ≥ 97+1 tại nến 5 (99).
    assert out[4] is None
    p = out[5]
    assert p is not None and p.kind == "low" and p.price == 97 and p.extreme_index == 3
    assert det.phase == PHASE_SEEK_HIGH and det.candidate.price == 99


def test_percent_mode_don_vi_phan_tram():
    det = DcDetector("percent", 1.5, 0.25)
    # Anchor: Δ = |200| × 0.25 / 100 = 0.5 → 0.25 nghĩa là 0,25% chứ không phải 25%.
    out, _ = feed(det, [200, 200], [None, 9])
    assert det.anchor["delta"] == pytest.approx(0.5)
    # Ứng viên 201 khoá Δ = 201 × 0.25% = 0.5025; 200.5 chưa đủ, 200.25 đủ.
    det2 = DcDetector("percent", 1.5, 0.25)
    out, _ = feed(det2, [200, 200, 200.5, 201, 200.5, 200.25], [None, 9, 9, 9, 9, 9])
    assert out[4] is None
    assert out[5] is not None and out[5].delta == pytest.approx(0.5025)
    assert det2.phase == PHASE_SEEK_LOW


def test_moi_nen_toi_da_mot_pivot_va_khong_reversal_cung_nen():
    det = DcDetector("atr", 1.0, 0.2)
    # Nến 5 giảm cực mạnh: xác nhận đỉnh, đặt ứng viên đáy = close nến 5,
    # không xác nhận thêm gì trong cùng nến.
    out, _ = feed(det, [100, 100, 101, 103, 102.5, 90], [None, 1, 1, 1, 1, 1])
    assert out[5] is not None and out[5].kind == "high"
    assert det.candidate.price == 90 and det.candidate.index == 5


def test_atr_bang_0_khong_khoi_tao_detector():
    det = DcDetector("atr", 1.5, 0.2)
    out, _ = feed(det, [100, 100, 100, 101], [None, 0.0, 0.0, 1.0])
    assert out == [None] * 4
    assert det.threshold(100, 0.0) is None
    # nến 1-2: ATR = 0 → chờ; nến 3: ATR > 0 mới đặt anchor.
    assert det.phase == PHASE_SEEK_DIRECTION and det.anchor["index"] == 3


def test_atr_0_khi_can_ung_vien_moi_thi_cho():
    det = DcDetector("atr", 1.0, 0.2)
    out, _ = feed(det, [100, 100, 101, 102], [None, 1, 1, 0.0])
    assert det.phase == PHASE_WAIT_ATR and det.candidate is None
    assert "ATR = 0" in det.wait_reason


# ---------------------------------------------------------------------------
# Adapter: close vs wick, đơn điệu, đi ngang, pivot luân phiên, nhãn
# ---------------------------------------------------------------------------


def test_chuoi_don_dieu_khong_ep_pivot_cuoi():
    up = run_algorithm(closes_to_bars([100 + i for i in range(60)]), dc_algo()).events
    down = run_algorithm(closes_to_bars([200 - i for i in range(60)]), dc_algo()).events
    assert pivots(up) == [] and pivots(down) == []


def test_di_ngang_khong_chia_0_khong_pivot():
    bars = make_bars([(100, 100, 100, 100)] * 80, timeframe="M15")
    a = dc_algo()
    res = run_algorithm(bars, a)
    assert pivots(res.events) == []
    assert a.pending_state()["dc"]["phase"] == PHASE_WAIT_ATR
    pct = run_algorithm(bars, dc_algo(threshold_mode="percent")).events
    assert pivots(pct) == []


def test_wick_lon_khong_thanh_pivot_close():
    closes = [100 + 0.5 * math.sin(i / 3.0) for i in range(80)]
    base = make_bars([(c, c + 0.5, c - 0.5, c) for c in closes], timeframe="M15")
    spiky = list(base)
    b = spiky[50]
    spiky[50] = replace(b, high=b.close + 80, low=b.close - 80)
    ev = pivots(run_algorithm(spiky, dc_algo(atr_multiplier=50)).events)
    assert all(e.price in closes for e in ev)
    assert all(e.event_bar_index != 50 or e.price == closes[50] for e in ev)


@pytest.fixture(scope="module")
def syn_bars():
    res = generate(SyntheticSpec(symbol="XAUUSD", timeframe="M15", bars=1600, seed=11))
    return build_bars(res["rows"], "M15", "open")


def test_pivot_luan_phien_mot_pivot_moi_nen_va_gia_la_close(syn_bars):
    res = run_algorithm(syn_bars, dc_algo())
    pv = pivots(res.events)
    assert len(pv) > 10
    by_seg: dict[int, list] = {}
    for e in pv:
        by_seg.setdefault(e.details["segment"], []).append(e)
    for seg in by_seg.values():
        kinds = [e.structure_type for e in seg]
        assert all(a != b for a, b in zip(kinds, kinds[1:]))
    confirms = [e.confirmed_bar_index for e in pv]
    assert len(confirms) == len(set(confirms))
    close_by_index = {b.index: b.close for b in syn_bars}
    for e in pv:
        assert e.price == close_by_index[e.event_bar_index]
        assert e.confirmed_at == syn_bars[e.confirmed_bar_index].close_time
        d = e.details
        assert d["delta_e"] == pytest.approx(1.5 * d["candidate_atr"])
        c = close_by_index[e.confirmed_bar_index]
        if e.structure_type == "DC_HIGH":
            assert c <= e.price - d["delta_e"]
        else:
            assert c >= e.price + d["delta_e"]


def test_nhan_hh_hl_so_voi_pivot_cung_loai_lien_truoc(syn_bars):
    pv = pivots(run_algorithm(syn_bars, dc_algo(label_tolerance_atr=0.1)).events)
    last: dict[tuple, object] = {}
    for e in pv:
        key = (e.details["segment"], e.structure_type)
        prev = last.get(key)
        d = e.details
        if prev is None:
            assert d["nhan"] is None and e.reference_event_id is None
        else:
            assert e.reference_event_id == prev.event_id
            tol = 0.1 * d["candidate_atr"]
            assert d["nhan_dung_sai"] == pytest.approx(tol)
            hi = e.structure_type == "DC_HIGH"
            if e.price > prev.price + tol:
                assert d["nhan"] == ("HH" if hi else "HL")
            elif e.price < prev.price - tol:
                assert d["nhan"] == ("LH" if hi else "LL")
            else:
                assert d["nhan"] == ("EQH" if hi else "EQL")
        last[key] = e


def test_mot_su_kien_cho_moi_pivot_khong_dem_trung(syn_bars):
    ev = run_algorithm(syn_bars, dc_algo()).events
    assert not [e for e in ev if e.structure_type in ("HH", "HL", "LH", "LL", "EQH", "EQL")]
    ids = [e.event_id for e in ev]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Gap / validate dữ liệu
# ---------------------------------------------------------------------------


def _with_gap(bars, at, minutes=75):
    out = list(bars[:at])
    shift = timedelta(minutes=minutes)
    for b in bars[at:]:
        out.append(replace(b, bar_time=b.bar_time + shift, close_time=b.close_time + shift))
    return out


def test_gap_reset_segment_khong_noi_swing(syn_bars):
    # syn_bars có gap cuối tuần tự nhiên tại nến 468 → chỉ dùng 450 nến đầu.
    bars = _with_gap(syn_bars[:450], 300)
    a = dc_algo()
    ev = run_algorithm(bars, a).events
    gaps = [e for e in ev if e.structure_type == "DC_SEGMENT_GAP"]
    assert len(gaps) == 1 and gaps[0].confirmed_bar_index == 300
    assert gaps[0].details["segment_moi"] == 1 and gaps[0].details["khoang_cach_giay"] == 90 * 60
    after = [e for e in pivots(ev) if e.confirmed_bar_index >= 300]
    before_ids = {e.event_id for e in pivots(ev) if e.confirmed_bar_index < 300}
    assert after and all(e.details["segment"] == 1 for e in after)
    assert all(e.reference_event_id not in before_ids for e in after)
    assert all((e.details.get("nhip") or {}).get("tu_pivot") not in before_ids for e in after)
    # warm-up lại: ATR có từ nến 300+14, anchor tại đó → không pivot nào xác nhận trước 316.
    assert min(e.confirmed_bar_index for e in after) >= 300 + 14 + 2
    # regime không mang qua gap
    first_regime_after = [e for e in ev if e.confirmed_bar_index >= 300 and e.structure_type.startswith("DC_REGIME")]
    if first_regime_after:
        assert first_regime_after[0].details["tu_trang_thai"] == "UNKNOWN"
    st = a.run_stats(ev)
    assert st["so_gap"] == 1 and st["so_segment"] == 2


def test_log_truoc_gap_khong_doi(syn_bars):
    plain = run_algorithm(syn_bars[:450], dc_algo()).events
    gapped = run_algorithm(_with_gap(syn_bars[:450], 300), dc_algo()).events
    pre_a = [e.to_dict() for e in plain if e.confirmed_bar_index < 300]
    pre_b = [e.to_dict() for e in gapped if e.confirmed_bar_index < 300]
    assert pre_a == pre_b


@pytest.mark.parametrize("bad", ["nan", "inf", "ohlc"])
def test_nen_khong_hop_le_bao_loi(bad):
    bars = closes_to_bars([100.0] * 5)
    b = bars[3]
    if bad == "nan":
        bars[3] = replace(b, close=float("nan"))
    elif bad == "inf":
        bars[3] = replace(b, high=float("inf"))
    else:
        bars[3] = replace(b, low=b.high + 1)
    with pytest.raises(ValueError):
        run_algorithm(bars, dc_algo())


def test_timestamp_trung_hoac_lui_bao_loi():
    bars = closes_to_bars([100.0, 100.25, 100.5, 100.75])
    dup = list(bars)
    dup[2] = replace(bars[2], bar_time=bars[1].bar_time, close_time=bars[1].close_time)
    with pytest.raises(ValueError, match="trùng hoặc lùi"):
        run_algorithm(dup, dc_algo())
    back = [bars[0], bars[2], replace(bars[1], index=2), replace(bars[3], index=3)]
    back[1] = replace(back[1], index=1)
    with pytest.raises(ValueError):
        run_algorithm(back, dc_algo())


def test_sai_khung_bao_loi():
    bars = closes_to_bars([100.0] * 3, timeframe="H1")
    with pytest.raises(ValueError, match="không phải khung"):
        run_algorithm(bars, dc_algo())
    with pytest.raises(ValueError, match="không khớp"):
        DcAtrStructureAlgorithm.check_dataset("H1", DcAtrStructureAlgorithm.validate_params({"timeframe": "M15"}))


def test_percent_mode_can_close_duong():
    bars = make_bars([(1, 1, -1, -0.5)] * 3, timeframe="M15")
    with pytest.raises(ValueError, match="close > 0"):
        run_algorithm(bars, dc_algo(threshold_mode="percent"))


@pytest.mark.parametrize(
    "params",
    [
        {"atr_multiplier": 0},
        {"atr_multiplier": float("nan")},
        {"atr_multiplier": True},
        {"reversal_pct": 0},
        {"atr_period": 1},
        {"atr_period": 3.5},
        {"atr_period": "abc"},
        {"label_tolerance_atr": -0.1},
        {"range_swings_per_side": 2},
        {"range_min_width_atr": 0},
        {"range_break_buffer_atr": float("inf")},
        {"price_source": "high"},
        {"threshold_mode": "points"},
        {"khong_co": 1},
    ],
)
def test_validate_tham_so(params):
    with pytest.raises(ValueError):
        DcAtrStructureAlgorithm.validate_params(params)


def test_registry_va_form_chi_hien_tham_so_cua_mode():
    cls = get_algorithm_class("dc_atr_structure")
    assert cls.version == "0.2.0"
    spec = [a for a in list_algorithms() if a["name"] == "dc_atr_structure"][0]
    by = {p["name"]: p for p in spec["params"]}
    assert by["atr_multiplier"]["show_if"] == {"param": "threshold_mode", "value": "atr"}
    assert by["reversal_pct"]["show_if"] == {"param": "threshold_mode", "value": "percent"}
    assert by["atr_period"]["show_if"] is None
    assert by["price_source"]["choices"] == ["close"]
    info = cls.manifest_info(cls.validate_params({}))
    assert info["gap_policy"] == "reset" and info["classifier"]["version"] == "0.1.0"
    assert by["bridge_max_gap_hours"]["show_if"] == {"param": "gap_policy", "value": "bridge_short"}
    assert info["atr"]["seed"] == WilderATRPrevClose.SEED_METHOD


# ---------------------------------------------------------------------------
# Nhân quả
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", ["atr", "percent"])
@pytest.mark.parametrize("cut", [40, 250, 777, 1333])
def test_prefix_bang_full_loc_theo_luc_biet(syn_bars, mode, cut):
    bars = _with_gap(syn_bars, 900)
    full = run_algorithm(bars, dc_algo(threshold_mode=mode))
    pre = run_algorithm(bars[:cut], dc_algo(threshold_mode=mode))
    assert [e.to_dict() for e in pre.events] == [
        e.to_dict() for e in full.events if e.confirmed_bar_index < cut
    ]
    assert pre.timeline == full.timeline[:cut]


def test_sua_duoi_sau_T_khong_doi_log_truoc_T(syn_bars):
    cut = 800
    base = run_algorithm(syn_bars, dc_algo())
    tampered = list(syn_bars[:cut])
    for b in syn_bars[cut:]:
        tampered.append(replace(b, open=b.open * 1.3, high=b.high * 1.3 + 9, low=b.low * 1.3 - 9, close=b.close * 1.3))
    after = run_algorithm(tampered, dc_algo())
    assert [e.to_dict() for e in base.events if e.confirmed_bar_index < cut] == [
        e.to_dict() for e in after.events if e.confirmed_bar_index < cut
    ]
    assert base.timeline[:cut] == after.timeline[:cut]


def test_su_kien_da_tra_ve_khong_bi_sua(syn_bars):
    a = dc_algo()
    a.reset()
    returned, snapshots = [], []
    for b in syn_bars:
        new = a.on_bar(b)
        returned.extend(new)
        snapshots.extend(copy.deepcopy(new))
    assert [e.to_dict() for e in returned] == [e.to_dict() for e in snapshots]
    # event_id tất định
    again = run_algorithm(syn_bars, dc_algo()).events
    assert [e.event_id for e in again] == [e.event_id for e in returned]


def test_replay_lui_khoi_phuc_ung_vien_nguong_regime(syn_bars):
    bars = syn_bars[:700]
    sess = ReplaySession(bars, dc_algo())
    sess.seek(650)
    sess.seek(321)
    snap = sess.snapshot()
    fresh = dc_algo()
    ref = run_algorithm(bars[:322], fresh)
    assert snap["pending_state"] == fresh.pending_state()
    assert snap["timeline"] == ref.timeline
    assert [e["event_id"] for e in snap["events"]] == [e.event_id for e in ref.events]
    sess.reset()
    new = sess.step_until_event()
    assert new and sess.cursor == new[0].confirmed_bar_index
    first = run_algorithm(bars, dc_algo()).events[0]
    assert new[0].event_id == first.event_id


def test_batch_va_tuan_tu_bang_nhau(syn_bars):
    a = dc_algo()
    batch = a.run(syn_bars)
    b = dc_algo()
    b.reset()
    seq = []
    for bar in syn_bars:
        seq.extend(b.on_bar(bar))
    assert [e.to_dict() for e in batch] == [e.to_dict() for e in seq]
    a.reset()
    assert a.pending_state()["so_nen_da_xu_ly"] == 0
    assert [e.to_dict() for e in a.run(syn_bars)] == [e.to_dict() for e in batch]


# ---------------------------------------------------------------------------
# Đánh giá: DC không lọt vào mục tiêu swing trừ khi khai báo ánh xạ chéo
# ---------------------------------------------------------------------------


def test_protocol_mac_dinh_bo_qua_dc_chi_cham_khi_khai_bao_map(syn_bars):
    from core.eval.dc_metrics import DC_CROSS_DEFINITION_EVENT_MAP
    from core.eval.evaluate import score_one_run
    from core.eval.protocol import EvalProtocol
    from core.labels import ReferenceLabel

    res = run_algorithm(syn_bars[:400], dc_algo())
    run = {"run_id": "r", "events": [e.to_dict() for e in res.events],
           "bars_processed": res.bars_processed, "warmup_bars": res.warmup_bars}
    piv = pivots(res.events)
    labels = [ReferenceLabel("SWING_HIGH" if e.structure_type == "DC_HIGH" else "SWING_LOW",
                             e.event_bar_index, e.price, seq=i) for i, e in enumerate(piv)]
    plain = score_one_run(run, protocol=EvalProtocol(target="swing_nho"), labels=labels, bars=[])
    assert plain["quality"]["n_events_scored"] == 0
    assert plain["counts_ignored"]["unmapped_type"] == len(res.events)
    cross = score_one_run(
        run, protocol=EvalProtocol(target="swing_nho", event_type_map=DC_CROSS_DEFINITION_EVENT_MAP),
        labels=labels, bars=[])
    assert cross["quality"]["true_positives"] == len(piv)
    assert cross["event_type_map"] == DC_CROSS_DEFINITION_EVENT_MAP


# ---------------------------------------------------------------------------
# gap_policy = bridge_short (v0.2.0)
# ---------------------------------------------------------------------------


def test_bridge_noi_gap_ngan_giu_ung_vien_atr_va_segment(syn_bars):
    bars = _with_gap(syn_bars[:450], 300, minutes=60)          # gap 75 phút giữa hai bar_time
    a = dc_algo(gap_policy="bridge_short", bridge_max_gap_hours=2)
    a.reset()
    for b in bars[:300]:
        a.on_bar(b)
    before = a.pending_state()
    atr_before = a._atr.value
    ev = a.on_bar(bars[300])
    br = [e for e in ev if e.structure_type == "DC_GAP_BRIDGED"]
    assert len(br) == 1 and br[0].details["khoang_cach_giay"] == 75 * 60
    assert br[0].details["ung_vien_giu_nguyen"] == before["dc"]["ung_vien"]
    assert not [e for e in ev if e.structure_type == "DC_SEGMENT_GAP"]
    after = a.pending_state()
    assert after["segment"] == before["segment"] and after["so_gap"] == 0 and after["so_gap_noi"] == 1
    # TR của nến đầu sau gap tính với close trước gap (gồm bước nhảy)
    b0, b1 = bars[299], bars[300]
    tr = max(b1.high - b1.low, abs(b1.high - b0.close), abs(b1.low - b0.close))
    assert a._atr.value == pytest.approx((13 * atr_before + tr) / 14)


def test_bridge_gap_dai_van_reset(syn_bars):
    bars = _with_gap(syn_bars[:450], 300, minutes=180)         # 3h15 > 2h
    ev = run_algorithm(bars, dc_algo(gap_policy="bridge_short", bridge_max_gap_hours=2)).events
    assert [e.confirmed_bar_index for e in ev if e.structure_type == "DC_SEGMENT_GAP"] == [300]
    assert not [e for e in ev if e.structure_type == "DC_GAP_BRIDGED"]


def test_bridge_pivot_duoc_noi_qua_gap_va_nhan_tham_chieu_truoc_gap(syn_bars):
    bars = _with_gap(syn_bars[:450], 300, minutes=60)
    ev = run_algorithm(bars, dc_algo(gap_policy="bridge_short")).events
    pv = pivots(ev)
    assert {e.details["segment"] for e in pv} == {0}
    before = {e.event_id for e in pv if e.confirmed_bar_index < 300}
    after = [e for e in pv if e.confirmed_bar_index >= 300]
    assert after and after[0].reference_event_id in before


def test_reset_mac_dinh_khong_doi_so_voi_khong_khai_bao(syn_bars):
    a = run_algorithm(syn_bars, dc_algo()).events
    b = run_algorithm(syn_bars, dc_algo(gap_policy="reset", bridge_max_gap_hours=9)).events
    assert [e.to_dict() for e in a] == [e.to_dict() for e in b]


@pytest.mark.parametrize("cut", [300, 470, 1000])
def test_bridge_prefix_bang_full(syn_bars, cut):
    bars = _with_gap(syn_bars, 300, minutes=60)
    full = run_algorithm(bars, dc_algo(gap_policy="bridge_short"))
    pre = run_algorithm(bars[:cut], dc_algo(gap_policy="bridge_short"))
    assert [e.to_dict() for e in pre.events] == [
        e.to_dict() for e in full.events if e.confirmed_bar_index < cut
    ]
    assert pre.timeline == full.timeline[:cut]


@pytest.mark.parametrize("params", [{"gap_policy": "session"}, {"bridge_max_gap_hours": 0},
                                    {"bridge_max_gap_hours": 100}])
def test_validate_gap_policy(params):
    with pytest.raises(ValueError):
        DcAtrStructureAlgorithm.validate_params(params)
