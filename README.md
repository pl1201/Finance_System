# Finance_System — market-data-pipeline

Bộ sinh dữ liệu giá **XAUUSD** và **EURUSD** 2018–2025 cho dự án AI Trading Copilot. Gồm:
- nến **M1, M5, M15, H1, H4, D1**, giờ **UTC**, giá BID;
- **lịch phiên khai báo** (giờ mở/đóng cửa, ngày lễ).

Mọi bước đều tái lập được và có checksum.

| Cặp | M1 | M5 | M15 | H1 | H4 | D1 |
|---|---:|---:|---:|---:|---:|---:|
| XAUUSD | 2 831 914 | 566 917 | 189 073 | 47 386 | 12 365 | 2 065 |
| EURUSD | 2 975 580 | 597 753 | 199 296 | 49 827 | 12 468 | 2 082 |

> **Dữ liệu không nằm trong repo** (~460 MB). Lý do: dung lượng, và điều khoản của các nguồn
> (HistData, Dukascopy…) không cho phân phối lại. Mỗi người tự chạy các lệnh dưới đây để tải và dựng
> — khoảng 5–10 phút.

## Cài đặt

Cần Python 3.11+.

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Chạy

```powershell
python -m marketdata.histdata download                 # 16 file zip M1 của HistData (2 cặp × 8 năm)
python -m marketdata.dukascopy                         # 24 ngày mẫu Dukascopy để kiểm múi giờ
python -m marketdata.dukascopy --gap-days 2            # các ngày Dukascopy dùng để lấp giờ mất
python -m marketdata.histdata build --fill-dukascopy   # dựng M1 UTC + M5/M15/H1/H4/D1 → data/
python -m marketdata.histdata verify                   # kiểm múi giờ với Dukascopy
python -m marketdata.compare all                       # đối chiếu với broker FXCM và COMEX (Yahoo)
pytest                                                  # kiểm thử, không cần mạng
```

Tuỳ chọn:
- `--pairs XAUUSD`, `--years 2020-2025`;
- `--h4d1-alignment utc_epoch` để cắt H4/D1 theo mốc UTC;
- bỏ `--fill-dukascopy` để chỉ dùng một nguồn;
- biến môi trường `MDP_DATA_DIR` để ghi dữ liệu ra thư mục khác.

## Đầu ra (`data/`)

```text
data/
  XAUUSD/M1/XAUUSD_M1_2018.csv … _2025.csv
  XAUUSD/XAUUSD_{M5,M15,H1,H4,D1}_2018_2025.csv
  XAUUSD/XAUUSD_lap_tu_dukascopy.csv     ← nhật ký các khoảng đã lấp
  EURUSD/…
  manifest.json      ← sha256, số dòng, mốc đầu/cuối của từng file; sha256 file gốc; quy ước
  quality.json       ← khoảng trống theo lịch, nến ngoài phiên, phần lấp
  verify_dukascopy.json, compare_external.json
  raw/               ← file gốc đã tải (HistData, Dukascopy, FXCM, Yahoo)
```

**Quy ước file CSV:** `time,open,high,low,close,volume[,m1_count][,trading_day]`.
- `time` là **giờ MỞ nến, UTC**.
- M5/M15/H1 cắt theo bội số UTC; **H4/D1 cắt theo ngày giao dịch bắt đầu 17:00 New York** (giống
  broker «giờ đóng cửa New York»).
- `m1_count` = số nến M1 tạo nên nến đó.
- `trading_day` (chỉ D1) = ngày giao dịch.
- `volume` luôn 0 (HistData không có volume).

## Ba điều cần biết

1. **Giờ gốc của HistData không phải «EST cố định» như trang web ghi.** Tới hết 2018 giờ gốc là giờ
   New York; từ 2019 là giờ server châu Âu − 7 giờ. Quy đổi sai thì mọi nến trong ~3 tuần Mỹ–Âu lệch
   lịch đổi giờ mỗi năm bị lệch 1 giờ. Quy tắc đúng đã được kiểm bằng ba nguồn độc lập: Dukascopy
   24/24 ngày mẫu, broker FXCM, vàng COMEX.
2. **HistData 2023 mất nhiều giờ** (tháng 1–7). Phần thiếu được lấp bằng Dukascopy — cùng luồng giá,
   khớp 100% đến từng điểm giá ở mọi phút trùng — và chỉ lấp phút nằm trong phiên theo lịch. Mọi
   khoảng đã lấp đều được ghi lại.
3. **Lịch phiên là dữ liệu khai báo** (`calendars/`), không suy từ dữ liệu:
   - XAUUSD dùng lịch CME Globex kim loại;
   - EURUSD dùng lịch FX giao ngay.

   Vài giờ đóng sớm ngày lễ chưa xác minh được — xem tài liệu §5.

Chi tiết nguồn, bằng chứng, chất lượng và bảng đối chiếu: [`docs/du_lieu_thi_truong.md`](docs/du_lieu_thi_truong.md).

## Cấu trúc

```text
marketdata/
  histdata.py          tải HistData, quy đổi giờ, lấp, gộp khung, kiểm chất lượng, ghi manifest
  dukascopy.py         tải/giải mã nến M1 Dukascopy (.bi5); ngày mẫu và ngày để lấp
  session_calendar.py  đọc lịch phiên khai báo; phân loại khoảng trống
  build_calendars.py   sinh calendars/*.json (cần requirements-calendars.txt)
  compare.py           đối chiếu với FXCM (broker) và Yahoo (COMEX GC=F, EURUSD=X)
calendars/             cme_globex_metals.json (XAUUSD), fx_spot.json (EURUSD)
docs/                  du_lieu_thi_truong.md
tests/                 kiểm thử không cần mạng
```

## Dùng trong market-structure-lab

Lab nạp dữ liệu từ thư mục `data/` của repo này bằng `scripts/import_market_data.py`. Lab giữ một
bản sao `calendars/*.json` và `session_calendar.py`. Khi lịch ở đây thay đổi thì chép lại sang lab.

## Nguồn dữ liệu

- [HistData.com](https://www.histdata.com/) — M1 miễn phí.
- [Dukascopy](https://www.dukascopy.com/) datafeed.
- FXCM candledata — công khai.
- Yahoo Finance.
- Lịch CME qua [`pandas_market_calendars`](https://github.com/rsheftel/pandas_market_calendars) và
  [lịch nghỉ lễ CME](https://www.cmegroup.com/trading-hours.html).

Tuân thủ điều khoản của từng nguồn; không đưa dữ liệu tải về lên repo.
