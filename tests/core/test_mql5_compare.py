"""Đối chiếu CSV MQL5 với sự kiện Python."""
from __future__ import annotations

from core.mql5_compare import compare_python_mql5, parse_mql5_events_csv


def test_parse_va_khop_cung_checksum():
    py = [
        {"event_id": "SWING_HIGH@1>2", "structure_type": "SWING_HIGH",
         "event_bar_index": 1, "price": 12.0},
        {"event_id": "CHOCH_DOWN@9>9", "structure_type": "CHOCH_DOWN",
         "event_bar_index": 9, "price": 10.0},
    ]
    csv = (
        "structure_type,event_bar_index,confirmed_bar_index,price,event_id,"
        "algorithm_version,dataset_checksum\n"
        "SWING_HIGH,1,2,12.0,SWING_HIGH@1>2,1.1.0,abc\n"
        "CHOCH_DOWN,9,9,10.0,CHOCH_DOWN@9>9,1.1.0,abc\n"
    )
    out = compare_python_mql5(py, csv, python_checksum="abc", python_version="1.1.0")
    assert out["checksum_khop"] is True
    assert out["true_positives"] == 2
    assert out["false_positives"] == 0
    assert out["warnings"] == []


def test_checksum_khac_canh_bao_khong_ket_luan_loi_code():
    py = [{"event_id": "A", "structure_type": "SWING_HIGH", "event_bar_index": 1, "price": 1.0}]
    csv = "structure_type,event_bar_index,price,dataset_checksum\nSWING_HIGH,1,1.0,khac\n"
    out = compare_python_mql5(py, csv, python_checksum="goc", python_version="1.1.0")
    assert out["checksum_khop"] is False
    assert any("CHECKSUM" in w for w in out["warnings"])
    assert "feed" in out["note_vi"].lower() or "feed" in out["warnings"][0].lower()


def test_parse_thieu_cot_bao_loi():
    import pytest
    with pytest.raises(ValueError):
        parse_mql5_events_csv("foo,bar\n1,2\n")
