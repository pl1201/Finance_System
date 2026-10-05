"""Đoạn phát triển / kiểm tra (core/eval/segments.py) và tương thích protocol cũ."""
from __future__ import annotations

from datetime import timedelta

import pytest

from core.eval.evaluate import score_one_run
from core.eval.protocol import EvalProtocol
from core.eval.segments import normalize_segments, resolve_windows
from core.labels import ReferenceLabel
from tests.helpers import START, make_bars

LEGACY_KEYS = {
    "version", "target", "matcher_version", "time_tolerance_bars", "price_tolerance", "coverage_start_index",
    "coverage_end_index", "event_type_map", "map_level1_to_structure", "atr_period", "atr_source",
    "exclude_unconfirmed_tail", "max_lag_bars", "min_recall",
}
# Hai protocol thật đã lưu trong data/lab.sqlite (09/2026) và hash ghi kèm.
SAVED = [
    ({"atr_period": 14, "atr_source": "wilder_confirm_bar", "coverage_end_index": None, "coverage_start_index": None,
      "event_type_map": {"SWING_HIGH": "SWING_HIGH", "SWING_LOW": "SWING_LOW"}, "exclude_unconfirmed_tail": True,
      "map_level1_to_structure": False, "matcher_version": "min_cost_v1", "max_lag_bars": None, "min_recall": None,
      "price_tolerance": 0.0, "target": "swing_nho", "time_tolerance_bars": 1, "version": "1.0.0"},
     "b81d1072b6c20259"),
    ({"atr_period": 14, "atr_source": "wilder_confirm_bar", "coverage_end_index": None, "coverage_start_index": None,
      "event_type_map": {"SWING_HIGH": "SWING_HIGH_L2", "SWING_HIGH_L2": "SWING_HIGH_L2",
                         "SWING_LOW": "SWING_LOW_L2", "SWING_LOW_L2": "SWING_LOW_L2"},
      "exclude_unconfirmed_tail": True, "map_level1_to_structure": True, "matcher_version": "min_cost_v1",
      "max_lag_bars": None, "min_recall": None, "price_tolerance": 0.0, "target": "swing_cau_truc",
      "time_tolerance_bars": 1, "version": "1.0.0"},
     "a4a9f6a4436a1547"),
]


def _t(i):
    """Giờ mở của nến H1 thứ i trong fixture."""
    return (START + timedelta(hours=i)).isoformat()


def _seg(role, a, b, name=""):
    return {"name": name, "role": role, "start": _t(a), "end": _t(b)}


def _ohlc(n):
    return [(100 + 0.1 * i, 101 + 0.1 * i, 99 + 0.1 * i, 100.3 + 0.1 * i) for i in range(n)]


def _run(bars, idxs, offset=0):
    evs = [{"event_id": "e%d" % i, "structure_type": "SWING_HIGH", "event_bar_index": i,
            "confirmed_bar_index": i + 1, "confirmation_lag_bars": 1, "price": bars[i].high} for i in idxs]
    return {"run_id": "r", "dataset_id": "ds", "events": evs, "bars_processed": len(bars), "warmup_bars": 0,
            "range_start_index": offset, "timeframe": "H1", "symbol": "X"}


def _labels(bars, idxs, offset=0):
    return [ReferenceLabel("SWING_HIGH", i + offset, bars[i].high, seq=k) for k, i in enumerate(idxs)]


def _p(**kw):
    base = {"target": "swing_nho", "time_tolerance_bars": 0, "price_tolerance": 0}
    base.update(kw)
    return EvalProtocol.from_dict(base)


@pytest.mark.parametrize("raw,expected", SAVED)
def test_protocol_cu_giu_nguyen_dict_va_hash(raw, expected):
    p = EvalProtocol.from_dict(raw)
    assert p.to_dict() == raw
    assert p.fingerprint() == expected


def test_tuy_chon_moi_chi_xuat_hien_khi_bat():
    assert set(_p().to_dict()) == LEGACY_KEYS
    base = _p().fingerprint()
    with_null = _p(null_mode="uniform_v1")
    assert set(with_null.to_dict()) == LEGACY_KEYS | {"null_mode", "null_n", "null_seed"}
    assert with_null.fingerprint() != base
    assert _p(null_mode="uniform_v1", null_seed=2).fingerprint() != with_null.fingerprint()
    seg = _p(segments=[_seg("dev", 0, 10), _seg("test", 20, 30)])
    assert set(seg.to_dict()) == LEGACY_KEYS | {"segments", "test_unlocked"}
    assert seg.fingerprint() not in (base, _p(segments=[_seg("dev", 0, 10), _seg("test", 20, 30)],
                                              test_unlocked=True).fingerprint())
    assert _p(test_unlocked=True).test_unlocked is False      # không có đoạn kiểm tra → không có gì để mở
    assert EvalProtocol.from_dict(seg.to_dict()).to_dict() == seg.to_dict()


@pytest.mark.parametrize("segments,msg", [
    ([_seg("dev", 0, 10), _seg("dev", 5, 15)], "chồng nhau"),
    ([_seg("test", 0, 10), _seg("dev", 20, 30)], "sau mọi đoạn phát triển"),
    ([_seg("abc", 0, 10)], "vai"),
    ([_seg("dev", 10, 10)], "trước giờ kết thúc"),
    ([{"role": "dev", "start": "khong-phai-gio", "end": _t(3)}], "ISO"),
    ([_seg("dev", i, i + 1) for i in range(25)], "Tối đa"),
])
def test_doan_khong_hop_le(segments, msg):
    with pytest.raises(ValueError, match=msg):
        _p(segments=segments)


@pytest.mark.parametrize("raw", [{"null_mode": "abc"}, {"null_n": 5}, {"null_n": 5000}, {"null_seed": -1}])
def test_tuy_chon_ngau_nhien_khong_hop_le(raw):
    with pytest.raises(ValueError):
        _p(**raw)


def test_chuan_hoa_gio_va_nua_mo():
    segs = normalize_segments([{"role": "dev", "start": "2024-01-01T00:00Z", "end": "2024-01-01T10:00"}])
    assert segs[0]["start"] == "2024-01-01T00:00:00+00:00" and segs[0]["end"] == "2024-01-01T10:00:00+00:00"
    assert segs[0]["name"] == "Đoạn 1"
    bars = make_bars(_ohlc(50))
    w = resolve_windows(segs, bars, offset=0)[0]
    assert (w["lo"], w["hi"]) == (0, 9)                        # [00:00, 10:00) → nến 0..9
    w = resolve_windows(segs, bars, offset=100)[0]
    assert (w["lo"], w["hi"]) == (100, 109)                    # chỉ số dataset của run bắt đầu ở nến 100
    w = resolve_windows(segs, bars, offset=0, coverage=(3, 6))[0]
    assert (w["lo"], w["hi"]) == (3, 6)                        # giao với khoảng chấm
    late = normalize_segments([{"role": "dev", "start": _t(80), "end": _t(90)}])
    assert resolve_windows(late, bars, offset=0)[0]["lo"] is None   # ngoài khoảng run đã chạy


def test_mot_doan_bang_khai_khoang_cham_tay():
    bars = make_bars(_ohlc(50))
    run = _run(bars, [5, 12, 20, 33, 41])
    labels = _labels(bars, [5, 12, 21, 40])
    for tol in (0, 1):
        manual = score_one_run(run, protocol=_p(time_tolerance_bars=tol, coverage_start_index=10,
                                                coverage_end_index=35), labels=labels, bars=bars)
        seg = score_one_run(run, protocol=_p(time_tolerance_bars=tol, segments=[_seg("dev", 10, 36)]),
                            labels=labels, bars=bars)
        for k in ("quality", "matches", "false_positives", "false_negatives", "lag", "density", "price_atr"):
            assert seg[k] == manual[k], (tol, k)
        assert seg["counts_ignored"] == manual["counts_ignored"]
        assert seg["by_segment"][0]["status"] == "ok"
        assert seg["by_segment"][0]["quality"]["f1"] == manual["quality"]["f1"]


def test_duoi_chua_xac_nhan_tinh_theo_tung_doan():
    bars = make_bars(_ohlc(30))
    out = score_one_run(_run(bars, [2, 5]), protocol=_p(segments=[_seg("dev", 0, 6)]),   # nến 0..5
                        labels=_labels(bars, [2, 5]), bars=bars)
    assert out["counts_ignored"]["unconfirmed_tail"] == 1      # sự kiện nến 5 xác nhận ở nến 6 > 5
    assert out["quality"]["true_positives"] == 1 and out["quality"]["false_negatives"] == 1


def test_khoa_doan_kiem_tra_va_khong_tinh_fp_giua_hai_doan():
    bars = make_bars(_ohlc(50))
    run = _run(bars, [3, 15, 33])                               # nến 15: giữa hai đoạn, không có nhãn
    labels = _labels(bars, [3, 33])
    segs = [_seg("dev", 0, 10, "dev"), _seg("test", 30, 40, "test")]
    locked = score_one_run(run, protocol=_p(segments=segs), labels=labels, bars=bars)
    q = locked["quality"]
    assert (q["true_positives"], q["false_positives"], q["false_negatives"]) == (1, 0, 0)
    assert locked["counts_ignored"]["outside_coverage"] == 2   # nến 15 và nến 33 (đoạn kiểm tra đang khoá)
    assert [m["event_bar_index"] for m in locked["matches"]] == [3]
    dev_row, test_row = locked["by_segment"]
    assert dev_row["status"] == "ok" and test_row["status"] == "khoa" and "quality" not in test_row
    opened = score_one_run(run, protocol=_p(segments=segs, test_unlocked=True), labels=labels, bars=bars)
    assert opened["quality"] == locked["quality"]               # số tổng chỉ gộp đoạn phát triển
    assert opened["by_segment"][1]["status"] == "ok"
    assert opened["by_segment"][1]["quality"]["true_positives"] == 1


def test_chi_khai_doan_kiem_tra_dang_khoa_thi_khong_cham_gi():
    bars = make_bars(_ohlc(50))
    out = score_one_run(_run(bars, [33]), protocol=_p(segments=[_seg("test", 30, 40)]),
                        labels=_labels(bars, [33]), bars=bars)
    assert out["quality"]["has_labels"] is False and out["quality"]["f1"] is None
    assert out["by_segment"][0]["status"] == "khoa"


def test_doan_tren_run_bat_dau_sau_nen_0():
    bars = make_bars(_ohlc(50))                                 # nến của run; run bắt đầu ở nến 100 của dataset
    run = _run(bars, [5, 12], offset=100)
    labels = _labels(bars, [5, 12], offset=100)
    out = score_one_run(run, protocol=_p(segments=[_seg("dev", 0, 20)]), labels=labels, bars=bars)
    assert out["quality"]["true_positives"] == 2
    assert (out["by_segment"][0]["lo"], out["by_segment"][0]["hi"]) == (100, 119)
