"""Test ghép nhãn — precision/recall chỉ khi có người gán."""
from __future__ import annotations

import pytest

from core.labels import ReferenceLabel, evaluate_detection
from tests.helpers import make_bars
from core.algorithms.swing_pivot import SwingPivotAlgorithm
from tests.algorithms.test_choch_bos import CHOCH_SERIES


def test_precision_recall_chuoi_nho_tinh_tay():
    bars = make_bars(CHOCH_SERIES)
    events = SwingPivotAlgorithm(left=1, right=1).run(bars)
    labels = [
        ReferenceLabel("SWING_HIGH", 1, 12.0, seq=0),
        ReferenceLabel("SWING_LOW", 3, 8.0, seq=1),
        ReferenceLabel("CHOCH_DOWN", 9, 10.0, seq=2),
        ReferenceLabel("SWING_HIGH", 99, 1.0, seq=3),  # bỏ sót / nhãn sai vị trí
    ]
    ev = evaluate_detection(
        events, labels, annotator="Tester A",
        label_set_id="ls1", label_set_version="1",
        time_tolerance_bars=0, price_tolerance=0.0,
    )
    assert ev.true_positives == 3
    assert ev.false_negatives == 1
    assert ev.recall == pytest.approx(3 / 4)
    assert ev.annotator == "Tester A"
    assert "Tester A" in ev.note_vi


def test_dung_sai_nen_cho_phep_lech():
    events = [{"event_id": "SWING_HIGH@5>6", "structure_type": "SWING_HIGH",
               "event_bar_index": 5, "price": 16.0}]
    labels = [ReferenceLabel("SWING_HIGH", 6, 16.0, seq=0)]
    tight = evaluate_detection(events, labels, annotator="A", time_tolerance_bars=0)
    assert tight.true_positives == 0
    loose = evaluate_detection(events, labels, annotator="A", time_tolerance_bars=1)
    assert loose.true_positives == 1


def test_bo_nhan_trong_khong_tinh_precision():
    ev = evaluate_detection([], [], annotator="A")
    assert ev.precision is None and ev.recall is None
    assert "trống" in ev.note_vi


def test_thieu_ten_nguoi_gan_bi_tu_choi():
    with pytest.raises(ValueError):
        evaluate_detection([], [ReferenceLabel("SWING_HIGH", 0, 1.0)], annotator="  ")
