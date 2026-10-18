"""Test matcher, F1/P90, phạm vi nhãn và quy tắc đếm — kết quả tính tay."""
from __future__ import annotations

import pytest

from core.eval.causality import STATUS_CO_VI_PHAM, STATUS_DAT, check_stored_event_invariants
from core.eval.evaluate import evaluate_runs, score_one_run
from core.eval.matcher import match_labels
from core.eval.metrics import f1_score, percentile_nearest_rank
from core.eval.protocol import (
    MATCHER_GREEDY_LABEL_ORDER_V1,
    MATCHER_MIN_COST_V1,
    TARGET_SWING_CAU_TRUC,
    TARGET_SWING_NHO,
    EvalProtocol,
)
from core.labels import ReferenceLabel
from tests.helpers import make_bars


def test_p90_nearest_rank_tinh_tay():
    # n=10, ceil(0.9*10)=9 → phần tử thứ 9 (index 8) = 9
    assert percentile_nearest_rank(list(range(1, 11)), 90) == 9
    assert percentile_nearest_rank([5], 90) == 5
    assert percentile_nearest_rank([], 90) is None


def test_f1_tinh_tay():
    # P=0.5, R=1 → F1 = 2*0.5*1 / 1.5 = 2/3
    assert f1_score(0.5, 1.0) == pytest.approx(2 / 3)
    assert f1_score(None, 1.0) is None
    assert f1_score(0.0, 0.0) is None


def test_greedy_bo_lo_ghep_tot_hon():
    """Nhãn A lấy sự kiện Q vì Δgiá nhỏ hơn, khiến B không còn ứng viên — greedy 1 TP.

    Optimal: A–P và B–Q → 2 TP.
    """
    labels = [
        ReferenceLabel("SWING_HIGH", 2, 10.0, seq=0),
        ReferenceLabel("SWING_HIGH", 5, 10.0, seq=1),
    ]
    events = [
        {"event_id": "P", "structure_type": "SWING_HIGH", "event_bar_index": 0, "price": 12.0},
        {"event_id": "Q", "structure_type": "SWING_HIGH", "event_bar_index": 4, "price": 10.0},
    ]
    greedy = match_labels(
        labels, events, time_tolerance_bars=2, price_tolerance=10,
        matcher_version=MATCHER_GREEDY_LABEL_ORDER_V1,
    )
    opt = match_labels(
        labels, events, time_tolerance_bars=2, price_tolerance=10,
        matcher_version=MATCHER_MIN_COST_V1,
    )
    assert {h.event_id for h in greedy.matches} == {"Q"}
    assert len(greedy.matches) == 1
    assert {h.event_id for h in opt.matches} == {"P", "Q"}
    assert len(opt.matches) == 2


def test_min_cost_khong_ghep_khac_loai():
    labels = [ReferenceLabel("SWING_HIGH", 1, 10.0, seq=0)]
    events = [{"event_id": "L", "structure_type": "SWING_LOW", "event_bar_index": 1, "price": 10.0}]
    out = match_labels(
        labels, events, time_tolerance_bars=0, price_tolerance=0,
        matcher_version=MATCHER_MIN_COST_V1,
    )
    assert out.matches == []
    assert out.unmatched_label_indices == [0]


def test_khong_dem_hh_thanh_swing():
    proto = EvalProtocol(target=TARGET_SWING_NHO)
    run = {
        "run_id": "r1",
        "dataset_id": "ds",
        "events": [
            {"event_id": "SH", "structure_type": "SWING_HIGH", "event_bar_index": 3,
             "confirmed_bar_index": 6, "confirmation_lag_bars": 3, "price": 12.0},
            {"event_id": "HH", "structure_type": "HH", "event_bar_index": 3,
             "confirmed_bar_index": 6, "confirmation_lag_bars": 3, "price": 12.0},
        ],
        "bars_processed": 20,
        "warmup_bars": 7,
        "duration_ms": 1.0,
    }
    out = score_one_run(run, protocol=proto, labels=[], bars=[], annotator="A")
    assert out["density"]["n_swings"] == 1
    assert out["quality"]["n_events_scored"] == 1
    assert out["counts_ignored"]["unmapped_type"] == 1


def test_su_kien_ngoai_khoang_nhan_khong_la_fp():
    proto = EvalProtocol(
        target=TARGET_SWING_NHO,
        coverage_start_index=0,
        coverage_end_index=10,
        matcher_version=MATCHER_MIN_COST_V1,
        time_tolerance_bars=0,
    )
    run = {
        "run_id": "r1", "dataset_id": "ds", "bars_processed": 30, "warmup_bars": 3,
        "events": [
            {"event_id": "in", "structure_type": "SWING_HIGH", "event_bar_index": 5,
             "confirmed_bar_index": 8, "confirmation_lag_bars": 3, "price": 10.0},
            {"event_id": "out", "structure_type": "SWING_HIGH", "event_bar_index": 20,
             "confirmed_bar_index": 23, "confirmation_lag_bars": 3, "price": 11.0},
        ],
    }
    labels = [ReferenceLabel("SWING_HIGH", 5, 10.0, seq=0)]
    out = score_one_run(run, protocol=proto, labels=labels, bars=[], annotator="A")
    assert out["quality"]["true_positives"] == 1
    assert out["quality"]["false_positives"] == 0
    assert out["counts_ignored"]["outside_coverage"] == 1


def test_chua_co_nhan_khong_hien_precision_0():
    proto = EvalProtocol(target=TARGET_SWING_NHO)
    run = {
        "run_id": "r1", "dataset_id": "ds", "bars_processed": 10, "warmup_bars": 3,
        "events": [
            {"event_id": "a", "structure_type": "SWING_HIGH", "event_bar_index": 3,
             "confirmed_bar_index": 6, "confirmation_lag_bars": 3, "price": 1.0},
        ],
    }
    out = score_one_run(run, protocol=proto, labels=[], bars=[], annotator="A")
    assert out["quality"]["has_labels"] is False
    assert out["quality"]["precision"] is None
    assert out["quality"]["f1"] is None
    assert "Chưa có nhãn" in out["quality"]["note_vi"]
    assert out["lag"]["median"] == 3


def test_anh_xa_cap1_sang_cau_truc():
    proto = EvalProtocol(
        target=TARGET_SWING_CAU_TRUC,
        map_level1_to_structure=True,
        time_tolerance_bars=0,
        price_tolerance=0,
    )
    assert proto.event_type_map["SWING_HIGH"] == "SWING_HIGH_L2"
    run = {
        "run_id": "r1", "dataset_id": "ds", "bars_processed": 10, "warmup_bars": 3,
        "events": [
            {"event_id": "l1", "structure_type": "SWING_HIGH", "event_bar_index": 4,
             "confirmed_bar_index": 7, "confirmation_lag_bars": 3, "price": 20.0},
        ],
    }
    labels = [ReferenceLabel("SWING_HIGH_L2", 4, 20.0, seq=0)]
    out = score_one_run(run, protocol=proto, labels=labels, bars=[], annotator="A")
    assert out["quality"]["true_positives"] == 1
    assert out["matches"][0]["source_structure_type"] == "SWING_HIGH"


def test_khong_anh_xa_thi_cap1_khong_cham_nhan_cap2():
    proto = EvalProtocol(target=TARGET_SWING_CAU_TRUC, map_level1_to_structure=False)
    run = {
        "run_id": "r1", "dataset_id": "ds", "bars_processed": 10, "warmup_bars": 3,
        "events": [
            {"event_id": "l1", "structure_type": "SWING_HIGH", "event_bar_index": 4,
             "confirmed_bar_index": 7, "confirmation_lag_bars": 3, "price": 20.0},
        ],
    }
    labels = [ReferenceLabel("SWING_HIGH_L2", 4, 20.0, seq=0)]
    out = score_one_run(run, protocol=proto, labels=labels, bars=[], annotator="A")
    assert out["quality"]["true_positives"] == 0
    assert out["quality"]["false_negatives"] == 1
    assert out["quality"]["n_events_scored"] == 0


def test_tail_chua_xac_nhan_khong_tinh_fp():
    proto = EvalProtocol(
        target=TARGET_SWING_NHO,
        coverage_start_index=0,
        coverage_end_index=10,
        exclude_unconfirmed_tail=True,
    )
    run = {
        "run_id": "r1", "dataset_id": "ds", "bars_processed": 20, "warmup_bars": 3,
        "events": [
            {"event_id": "late", "structure_type": "SWING_HIGH", "event_bar_index": 9,
             "confirmed_bar_index": 12, "confirmation_lag_bars": 3, "price": 8.0},
        ],
    }
    labels: list[ReferenceLabel] = []
    out = score_one_run(run, protocol=proto, labels=labels, bars=[], annotator="A")
    assert out["counts_ignored"]["unconfirmed_tail"] == 1
    assert out["quality"]["n_events_scored"] == 0


def test_atr_khoang_gia_tinh_tay():
    # 14 nến TR=1 (high-low=1, close đi ngang) → ATR seed = 1
    # nến 13 close=10, pivot price=8 → dist=2, ratio=2
    ohlc = [(10.0, 10.5, 9.5, 10.0)] * 14
    bars = make_bars(ohlc)
    proto = EvalProtocol(target=TARGET_SWING_NHO, atr_period=14)
    run = {
        "run_id": "r1", "dataset_id": "ds", "bars_processed": 14, "warmup_bars": 3,
        "events": [
            {"event_id": "a", "structure_type": "SWING_HIGH", "event_bar_index": 10,
             "confirmed_bar_index": 13, "confirmation_lag_bars": 3, "price": 8.0},
        ],
    }
    out = score_one_run(run, protocol=proto, labels=[], bars=bars, annotator="A")
    assert out["price_atr"]["n"] == 1
    assert out["price_atr"]["median_distance"] == pytest.approx(2.0)
    assert out["price_atr"]["median_atr_ratio"] == pytest.approx(2.0)


def test_fingerprint_doi_khi_doi_matcher():
    a = EvalProtocol(target=TARGET_SWING_NHO, matcher_version=MATCHER_MIN_COST_V1)
    b = EvalProtocol(target=TARGET_SWING_NHO, matcher_version=MATCHER_GREEDY_LABEL_ORDER_V1)
    assert a.fingerprint() != b.fingerprint()


def test_nhom_tach_khac_dataset():
    proto = EvalProtocol(target=TARGET_SWING_NHO)
    runs = [
        {"run_id": "a", "dataset_id": "ds1", "range_start": "t0", "range_end": "t1",
         "events": [], "bars_processed": 5, "warmup_bars": 3},
        {"run_id": "b", "dataset_id": "ds2", "range_start": "t0", "range_end": "t1",
         "events": [], "bars_processed": 5, "warmup_bars": 3},
    ]
    out = evaluate_runs(runs, protocol=proto, labels=[], annotator="A")
    comparable = [g for g in out["groups"] if g["comparable"]]
    assert len(comparable) == 2


def test_bat_bien_nhan_qua_tren_su_kien_luu():
    ok = check_stored_event_invariants(
        [{"event_id": "a", "event_bar_index": 3, "confirmed_bar_index": 6,
          "confirmation_lag_bars": 3}],
        warmup_bars=3,
        bars_processed=10,
    )
    assert ok["status"] == STATUS_DAT
    bad = check_stored_event_invariants(
        [{"event_id": "b", "event_bar_index": 8, "confirmed_bar_index": 5,
          "confirmation_lag_bars": -3}],
        warmup_bars=3,
        bars_processed=10,
    )
    assert bad["status"] == STATUS_CO_VI_PHAM
    assert bad["n_violations"] >= 1


def test_bang_muc_tieu_va_loai_nhan_gom_thuat_toan_khai_bao():
    """Swing dựng sẵn + mục tiêu/loại nhãn do thuật toán khai báo, đúng thứ tự cũ."""
    from core.eval.protocol import describe_targets, target_ids
    from core.eval.targets import high_types, low_types
    from core.labels import label_types

    # mục / loại mới (ict_structure: shift) nối cuối, thứ tự cũ giữ nguyên
    assert target_ids() == ("swing_nho", "swing_cau_truc", "c2", "cisd", "ict_shift")
    assert [t["id"] for t in describe_targets()] == list(target_ids())
    assert high_types() == {"SWING_HIGH", "SWING_HIGH_L2", "C2_CONFIRMED_DOWN", "CISD_CONFIRMED_DOWN", "SHIFT_DOWN"}
    assert low_types() == {"SWING_LOW", "SWING_LOW_L2", "C2_CONFIRMED_UP", "CISD_CONFIRMED_UP", "SHIFT_UP"}
    assert label_types() == (
        "SWING_HIGH", "SWING_LOW", "SWING_HIGH_L2", "SWING_LOW_L2", "BOS_UP", "BOS_DOWN",
        "BOS_INTERNAL_UP", "BOS_INTERNAL_DOWN", "CHOCH_UP", "CHOCH_DOWN",
        "C2_CONFIRMED_UP", "C2_CONFIRMED_DOWN", "CISD_CONFIRMED_UP", "CISD_CONFIRMED_DOWN",
        "SHIFT_UP", "SHIFT_DOWN",
    )
    with pytest.raises(ValueError):
        EvalProtocol(target="khong_co")
