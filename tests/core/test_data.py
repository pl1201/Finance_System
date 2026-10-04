"""Test nạp CSV, ánh xạ cột, múi giờ và kiểm tra chất lượng dữ liệu."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.data.loader import CsvImportError, load_csv, preview_csv, rows_checksum
from core.data.synthetic import SyntheticSpec, generate, to_csv_text
from core.data.validate import infer_timeframe, validate_and_clean

CSV_CHUAN = """time,open,high,low,close,volume
2024-01-02 00:00:00,2000.0,2005.0,1998.0,2003.0,120
2024-01-02 01:00:00,2003.0,2008.0,2001.0,2006.0,140
2024-01-02 02:00:00,2006.0,2009.0,2002.0,2004.0,110
"""

# Định dạng xuất bars của MT5: TAB, ngày dạng 2024.01.02, cột bọc trong <>
CSV_MT5 = (
    "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\t<VOL>\t<SPREAD>\n"
    "2024.01.02\t00:00:00\t2000.00\t2005.00\t1998.00\t2003.00\t120\t0\t25\n"
    "2024.01.02\t01:00:00\t2003.00\t2008.00\t2001.00\t2006.00\t140\t0\t24\n"
    "2024.01.02\t02:00:00\t2006.00\t2009.00\t2002.00\t2004.00\t110\t0\t26\n"
)

# MT4-style: không header, ngày và giờ tách cột, phân tách bằng dấu phẩy
CSV_MT4 = (
    "2024.01.02,00:00,2000.00,2005.00,1998.00,2003.00,120\n"
    "2024.01.02,01:00,2003.00,2008.00,2001.00,2006.00,140\n"
    "2024.01.02,02:00,2006.00,2009.00,2002.00,2004.00,110\n"
)

CSV_TEN_COT_LA = (
    "Ngay_Gio;Gia_Mo;Gia_Cao;Gia_Thap;Gia_Dong\n"
    "2024-01-02 00:00;2000;2005;1998;2003\n"
    "2024-01-02 01:00;2003;2008;2001;2006\n"
    "2024-01-02 02:00;2006;2009;2002;2004\n"
)


# ---------------------------------------------------------------------------
# Nhận diện định dạng
# ---------------------------------------------------------------------------


def test_nap_csv_chuan():
    r = load_csv(CSV_CHUAN, source_timezone="UTC")
    assert len(r.rows) == 3
    assert r.rows[0]["bar_time"] == datetime(2024, 1, 2, 0, 0, tzinfo=timezone.utc)
    assert r.rows[0]["open"] == 2000.0 and r.rows[0]["volume"] == 120.0


def test_nap_dinh_dang_mt5_tab():
    pv = preview_csv(CSV_MT5)
    assert pv.delimiter == "\t"
    assert pv.has_header
    assert pv.suggested_mapping["date_part"] == "DATE"
    assert pv.suggested_mapping["time_part"] == "TIME"
    assert pv.suggested_mapping["open"] == "OPEN"
    assert not pv.needs_manual_mapping

    r = load_csv(CSV_MT5, source_timezone="UTC")
    assert len(r.rows) == 3
    assert r.rows[1]["bar_time"] == datetime(2024, 1, 2, 1, 0, tzinfo=timezone.utc)
    assert r.rows[0]["volume"] == 120.0  # lấy TICKVOL


def test_nap_dinh_dang_mt4_khong_header():
    pv = preview_csv(CSV_MT4)
    assert not pv.has_header
    r = load_csv(CSV_MT4, source_timezone="UTC")
    assert len(r.rows) == 3
    assert r.rows[2]["close"] == 2004.0


def test_ten_cot_la_can_anh_xa_thu_cong():
    pv = preview_csv(CSV_TEN_COT_LA)
    assert pv.needs_manual_mapping
    assert "Chưa nhận diện được cột" in pv.note_vi
    with pytest.raises(CsvImportError):
        load_csv(CSV_TEN_COT_LA, source_timezone="UTC")

    r = load_csv(
        CSV_TEN_COT_LA,
        source_timezone="UTC",
        mapping={
            "time": "Ngay_Gio", "open": "Gia_Mo", "high": "Gia_Cao",
            "low": "Gia_Thap", "close": "Gia_Dong",
        },
    )
    assert len(r.rows) == 3
    assert r.rows[0]["high"] == 2005.0


# ---------------------------------------------------------------------------
# Múi giờ
# ---------------------------------------------------------------------------


def test_mui_gio_nguon_duoc_quy_doi_ve_utc():
    r = load_csv(CSV_CHUAN, source_timezone="UTC+2")
    assert r.rows[0]["bar_time"] == datetime(2024, 1, 1, 22, 0, tzinfo=timezone.utc)

    r2 = load_csv(CSV_CHUAN, source_timezone="UTC-05:00")
    assert r2.rows[0]["bar_time"] == datetime(2024, 1, 2, 5, 0, tzinfo=timezone.utc)


def test_mui_gio_khong_hop_le_bi_tu_choi():
    with pytest.raises(CsvImportError):
        load_csv(CSV_CHUAN, source_timezone="Europe/London")
    with pytest.raises(CsvImportError):
        load_csv(CSV_CHUAN, source_timezone="UTC+99")


# ---------------------------------------------------------------------------
# Kiểm tra chất lượng
# ---------------------------------------------------------------------------


def test_phat_hien_ohlc_khong_hop_le_va_cach_ly():
    bad = CSV_CHUAN + "2024-01-02 03:00:00,2010.0,2005.0,2012.0,2008.0,90\n"
    rows = load_csv(bad, source_timezone="UTC").rows
    clean, report = validate_and_clean(rows, "H1")
    assert len(clean) == 3
    codes = {i.code for i in report.issues}
    assert "INVALID_OHLC" in codes
    assert report.has_error


def test_phat_hien_trung_timestamp_giu_ban_dau():
    dup = CSV_CHUAN + "2024-01-02 01:00:00,9999.0,9999.0,9999.0,9999.0,1\n"
    rows = load_csv(dup, source_timezone="UTC").rows
    clean, report = validate_and_clean(rows, "H1")
    assert len(clean) == 3
    assert any(i.code == "DUPLICATE_TIMESTAMP" for i in report.issues)
    at_1h = [r for r in clean if r["bar_time"].hour == 1][0]
    assert at_1h["open"] == 2003.0  # giữ bản ghi đầu tiên


def test_phat_hien_sai_thu_tu_va_sap_xep_lai():
    text = (
        "time,open,high,low,close\n"
        "2024-01-02 02:00:00,2006,2009,2002,2004\n"
        "2024-01-02 00:00:00,2000,2005,1998,2003\n"
        "2024-01-02 01:00:00,2003,2008,2001,2006\n"
    )
    rows = load_csv(text, source_timezone="UTC").rows
    clean, report = validate_and_clean(rows, "H1")
    assert [r["bar_time"].hour for r in clean] == [0, 1, 2]
    assert any(i.code == "OUT_OF_ORDER" for i in report.issues)


def test_nen_thieu_trong_phien_duoc_bao_cao_va_khong_noi_suy():
    text = (
        "time,open,high,low,close\n"
        "2024-01-02 00:00:00,2000,2005,1998,2003\n"
        "2024-01-02 01:00:00,2003,2008,2001,2006\n"
        "2024-01-02 06:00:00,2006,2009,2002,2004\n"   # thiếu 4 nến
    )
    rows = load_csv(text, source_timezone="UTC").rows
    clean, report = validate_and_clean(rows, "H1")
    assert len(clean) == 3, "Không được tự tạo nến thay thế"
    assert report.missing_in_session == 4
    assert any(i.code == "MISSING_BARS_IN_SESSION" for i in report.issues)


def test_khoang_nghi_cuoi_tuan_khong_bi_coi_la_loi():
    # Thứ Sáu 2024-01-05 20:00 UTC -> Chủ nhật 2024-01-07 22:00 UTC:
    # mọi vị trí nến thiếu đều rơi vào cửa sổ nghỉ.
    text = (
        "time,open,high,low,close\n"
        "2024-01-05 20:00:00,2000,2005,1998,2003\n"
        "2024-01-07 22:00:00,2003,2008,2001,2006\n"
    )
    rows = load_csv(text, source_timezone="UTC").rows
    _, report = validate_and_clean(rows, "H1")
    assert report.missing_in_session == 0
    assert report.missing_weekend == 49
    assert not report.has_error


def test_khoang_trong_lan_qua_cuoi_tuan_duoc_tach_tung_nen():
    """Khoảng trống vừa trùm cuối tuần vừa thiếu nến trong phiên."""
    text = (
        "time,open,high,low,close\n"
        "2024-01-05 20:00:00,2000,2005,1998,2003\n"
        "2024-01-08 01:00:00,2003,2008,2001,2006\n"   # thiếu thêm 22h, 23h CN và 00h T2
    )
    rows = load_csv(text, source_timezone="UTC").rows
    _, report = validate_and_clean(rows, "H1")
    assert report.missing_weekend == 49
    assert report.missing_in_session == 3


def test_gia_am_hoac_bang_khong_bi_cach_ly():
    text = CSV_CHUAN + "2024-01-02 03:00:00,0,0,0,0\n"
    rows = load_csv(text, source_timezone="UTC").rows
    clean, report = validate_and_clean(rows, "H1")
    assert len(clean) == 3
    assert any(i.code == "NON_POSITIVE_PRICE" for i in report.issues)


def test_dong_hong_bi_bo_qua_va_ghi_log():
    text = CSV_CHUAN + "2024-01-02 03:00:00,khong-phai-so,2005,1998,2003\n"
    r = load_csv(text, source_timezone="UTC")
    assert len(r.rows) == 3
    assert len(r.skipped_rows) == 1
    assert "open" in r.skipped_rows[0]["error"]


def test_file_rong_bao_loi_ro_rang():
    with pytest.raises(CsvImportError):
        load_csv("", source_timezone="UTC")
    with pytest.raises(CsvImportError):
        load_csv("   \n  \n", source_timezone="UTC")


def test_do_timeframe():
    rows = load_csv(CSV_CHUAN, source_timezone="UTC").rows
    assert infer_timeframe(rows) == "H1"


def test_checksum_on_dinh_va_nhay_voi_thay_doi():
    a = load_csv(CSV_CHUAN, source_timezone="UTC").rows
    b = load_csv(CSV_CHUAN, source_timezone="UTC").rows
    assert rows_checksum(a) == rows_checksum(b)
    b[0]["close"] += 0.01
    assert rows_checksum(a) != rows_checksum(b)


# ---------------------------------------------------------------------------
# Bộ sinh dữ liệu mô phỏng
# ---------------------------------------------------------------------------


def test_du_lieu_mo_phong_tat_dinh_theo_seed():
    a = generate(SyntheticSpec("XAUUSD", "H1", 200, seed=42))
    b = generate(SyntheticSpec("XAUUSD", "H1", 200, seed=42))
    c = generate(SyntheticSpec("XAUUSD", "H1", 200, seed=43))
    assert rows_checksum(a["rows"]) == rows_checksum(b["rows"])
    assert rows_checksum(a["rows"]) != rows_checksum(c["rows"])


def test_du_lieu_mo_phong_hop_le_va_duoc_danh_dau():
    res = generate(SyntheticSpec("XAUUSD", "H1", 500, seed=1))
    assert res["is_synthetic"] is True
    assert res["label"] == "DỮ LIỆU MÔ PHỎNG"
    clean, report = validate_and_clean(res["rows"], "H1")
    assert len(clean) == 500
    assert not report.has_error


def test_csv_mo_phong_nap_lai_duoc():
    res = generate(SyntheticSpec("EURUSD", "M15", 120, seed=5))
    text = to_csv_text(res)
    back = load_csv(text, source_timezone="UTC")
    assert len(back.rows) == 120
    assert infer_timeframe(back.rows) == "M15"
