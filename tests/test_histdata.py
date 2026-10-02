"""Quy đổi giờ HistData, gộp khung, đọc zip, ghi CSV — số tính tay, không cần mạng."""
import zipfile
from datetime import date, datetime, timezone

import pytest

from marketdata import histdata as hd


def ts(*a):
    return int(datetime(*a, tzinfo=timezone.utc).timestamp())


@pytest.mark.parametrize("rule,day,hours", [
    ("histdata", date(2018, 3, 14), 4),   # 2018: giờ gốc = New York; Mỹ đã đổi giờ (11/03)
    ("histdata", date(2024, 3, 13), 5),   # từ 2019: giờ server châu Âu − 7h; châu Âu chưa đổi giờ
    ("histdata", date(2024, 7, 10), 4),
    ("histdata", date(2024, 1, 10), 5),
    ("ny", date(2024, 3, 13), 4),
    ("eu_server", date(2018, 3, 14), 5),
    ("est", date(2024, 7, 10), 5),
])
def test_offset_for(rule, day, hours):
    assert hd.offset_for(rule, day) == hours * 3600


def test_bucket_ny1700_follows_dst():
    # 13:30 NY mùa hè (EDT) = 17:30 UTC → nến H4 mở 13:00 NY = 17:00 UTC
    assert hd.bucket(ts(2024, 3, 13, 17, 30), "H4", "ny_1700")[1] == ts(2024, 3, 13, 17, 0)
    # 13:30 NY mùa đông (EST) = 18:30 UTC → mở 18:00 UTC
    assert hd.bucket(ts(2024, 1, 10, 18, 30), "H4", "ny_1700")[1] == ts(2024, 1, 10, 18, 0)
    # 18:30 NY ngày 10/01 thuộc ngày giao dịch 11/01; nến D1 mở 17:00 NY = 22:00 UTC
    assert hd.bucket(ts(2024, 1, 10, 23, 30), "D1", "ny_1700")[1] == ts(2024, 1, 10, 22, 0)
    assert hd.bucket(ts(2024, 1, 10, 18, 30), "H4", "utc_epoch")[1] == ts(2024, 1, 10, 16, 0)
    assert hd.bucket(ts(2024, 1, 10, 18, 37), "M15", "ny_1700")[1] == ts(2024, 1, 10, 18, 30)


def test_aggregate_ohlc_and_count():
    m1 = [(ts(2024, 1, 10, 10, 0), 1.0, 2.0, 0.5, 1.5),
          (ts(2024, 1, 10, 10, 1), 1.5, 3.0, 1.2, 2.5),
          (ts(2024, 1, 10, 10, 5), 2.5, 2.6, 2.4, 2.45)]
    assert hd.aggregate(m1, "M5", "ny_1700") == [
        [ts(2024, 1, 10, 10, 0), 1.0, 3.0, 0.5, 2.5, 2],
        [ts(2024, 1, 10, 10, 5), 2.5, 2.6, 2.4, 2.45, 1],
    ]


def test_read_pair_converts_dedupes_and_drops_bad_rows(tmp_path, monkeypatch):
    monkeypatch.setattr(hd, "RAW", str(tmp_path))
    lines = ["20240710 120000;2378.728;2379.078;2378.585;2378.908;0",
             "20240710 120000;2378.728;2379.078;2378.585;2378.908;0",   # dòng lặp nguyên văn
             "20240710 120100;2378.9;2378.0;2378.5;2378.6;0"]            # high < open → bỏ
    with zipfile.ZipFile(tmp_path / "HISTDATA_COM_ASCII_XAUUSD_M1_2024.zip", "w") as z:
        z.writestr("DAT_ASCII_XAUUSD_M1_2024.csv", "\n".join(lines))
    rows, stats = hd.read_pair("XAUUSD", [2024], "histdata")
    assert rows == [(ts(2024, 7, 10, 16, 0), 2378.728, 2379.078, 2378.585, 2378.908)]  # 12:00 + 4h
    assert stats["trung_thoi_diem"] == 1 and stats["ohlc_sai_bo"] == 1


def test_write_csv_format(tmp_path, monkeypatch):
    monkeypatch.setattr(hd, "OUT", str(tmp_path))
    bars = [[ts(2024, 1, 10, 22, 0), 2030.5, 2031.25, 2029.0, 2030.0, 1380]]
    info = hd.write_csv(str(tmp_path / "X" / "x.csv"), bars, 3, trading_day=True)
    assert (tmp_path / "X" / "x.csv").read_text().splitlines() == [
        "time,open,high,low,close,volume,m1_count,trading_day",
        "2024-01-10 22:00:00,2030.5,2031.25,2029,2030,0,1380,2024-01-11",
    ]
    assert info["rows"] == 1 and info["file"] == "X/x.csv" and len(info["sha256"]) == 64
