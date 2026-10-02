# Dữ liệu thị trường XAUUSD và EURUSD 2018–2025

Ngày: 02/10/2026. Repo: `market-data-pipeline` (gói `marketdata`).

**Module:**
- `marketdata/histdata.py` — tải, quy đổi giờ, lấp, gộp khung, kiểm chất lượng.
- `marketdata/dukascopy.py` — kiểm giờ và tải ngày để lấp.
- `marketdata/build_calendars.py` — sinh lịch phiên.
- `marketdata/compare.py` — đối chiếu với nguồn ngoài.
- `marketdata/session_calendar.py` — đọc lịch phiên.

**Dữ liệu:**
- `data/` (không đưa vào git, ~460 MB, dựng lại được);
- `calendars/` (lịch khai báo, có trong git).

---

## 1. Có gì và chạy lại thế nào

| Cặp | M1 (8 file theo năm) | M5 | M15 | H1 | H4 | D1 |
|---|---:|---:|---:|---:|---:|---:|
| XAUUSD | 2 831 914 | 566 917 | 189 073 | 47 386 | 12 365 | 2 065 |
| EURUSD | 2 975 580 | 597 753 | 199 296 | 49 827 | 12 468 | 2 082 |

Thời gian 01/01/2018 → 31/12/2025, giá **BID**. Mọi file đã được nạp thử bằng bộ nạp và bộ kiểm tra
của market-structure-lab, không lỗi.

```text
data/
  XAUUSD/M1/XAUUSD_M1_2018.csv … _2025.csv      ← M1 theo năm (UTC)
  XAUUSD/XAUUSD_{M5,M15,H1,H4,D1}_2018_2025.csv
  XAUUSD/XAUUSD_lap_tu_dukascopy.csv            ← nhật ký từng khoảng đã lấp (§4)
  EURUSD/…                                      ← như trên
  manifest.json          ← sha256, số dòng, mốc đầu/cuối từng file; sha256 file gốc; quy ước
  quality.json           ← khoảng trống theo lịch, nến ngoài phiên, phần lấp (§5, §6)
  verify_dukascopy.json  ← kiểm chứng múi giờ (§3)
  compare_external.json  ← đối chiếu FXCM và Yahoo (§8)
  raw/histdata/ raw/dukascopy/ raw/fxcm/ raw/yahoo/   ← file gốc đã tải
calendars/
  cme_globex_metals.json  fx_spot.json          ← lịch phiên khai báo (§5)
```

Chạy lại từ đầu (5–10 phút; Dukascopy đôi khi trả 503 nên có thử lại) — lệnh ở
[`README.md`](../README.md). Lịch phiên chỉ cần sinh lại khi muốn đổi nguồn lịch:

```powershell
pip install -r requirements-calendars.txt
python -m marketdata.build_calendars
```

## 2. Nguồn — vì sao chọn

| Nguồn | Ưu | Nhược | Vai trò |
|---|---|---|---|
| **HistData.com** (ASCII M1) | Miễn phí, 1 file zip/năm/cặp, tải ~3 s/file | Không có volume; giờ gốc ghi sai trên trang (§3); 2023 mất nhiều giờ | **Nguồn chính** |
| **Dukascopy** datafeed (`.bi5`) | Giờ UTC, có cả BID/ASK | 1 file/ngày; mở kết nối mất ~20 s (giữ kết nối thì ~0.3 s/file); hay trả 503 | Kiểm chứng giờ; lấp giờ mất |
| **FXCM** candledata (broker) | Dữ liệu của một broker thật, công khai, giờ UTC, BID+ASK | Không có vàng | Đối chiếu EURUSD (§8) |
| **Yahoo Finance** | Vàng COMEX `GC=F` (dữ liệu CME), `EURUSD=X` | Nến 60 phút chỉ ~730 ngày gần nhất; GC=F là hợp đồng tương lai | Đối chiếu giờ (§8) |

Không dùng:
- yfinance/Yahoo cho M1: chỉ có vài chục ngày gần nhất.
- MT5: máy chưa cài terminal và broker.
- Stooq: chặn bằng JavaScript.
- TradingView: không có API công khai (§8.3).

## 3. Múi giờ của HistData — quan trọng

Trang HistData ghi giờ là «EST, không đổi giờ mùa hè». Dữ liệu cho thấy **không đúng**. Kiểm theo
giờ New York của nến cuối tuần, trên toàn bộ 2018–2025:

| Quy đổi giờ gốc → UTC | Tuần bình thường | Tuần Mỹ–Âu lệch lịch đổi giờ (~3 tuần/năm) |
|---|---|---|
| EST cố định (UTC−5) | đóng tuần **18:00** NY vào mùa hè → sai | |
| Giờ New York có đổi giờ (cách market-structure-lab từng nhập dataset 2024) | đóng 17:00 NY | 2019–2025: đóng **16:00** NY → sai; 2018: đúng |
| Giờ server châu Âu − 7 giờ | đóng 17:00 NY | 2019–2025: đúng; 2018: đóng **18:00** NY → sai |

→ Quy tắc `histdata` (mặc định của script):
- **tới hết 2018**: giờ gốc = giờ New York;
- **từ 2019**: giờ gốc = giờ server châu Âu − 7 giờ.

Mốc chuyển thật nằm giữa 04/11/2018 và 10/03/2019.

Kiểm chứng:
- **Dukascopy** (giờ UTC), 24 ngày mẫu: quy tắc `histdata` khớp ở **0 phút** trên cả **24/24**
  ngày; quy đổi theo New York lệch 60 phút ở mọi ngày lệch lịch từ 2021.
- **Hai nguồn hoàn toàn độc lập** (FXCM, COMEX) cũng khớp ở độ lệch 0, kể cả trong các tuần lệch
  lịch (§8).

**Hệ quả:** dữ liệu HistData quy đổi theo giờ New York bị **sớm 1 giờ** trong các tuần lệch lịch
(năm 2024: 10–30/03 và 27/10–02/11). market-structure-lab đã gặp lỗi này và đã sửa (§9).

## 4. Lấp giờ mất bằng Dukascopy

- **Cùng luồng giá:** từ 2021, close M1 của HistData và Dukascopy **trùng hệt nhau** (chênh trung vị
  0 trên ~1 380 phút/ngày). Năm 2018 thì khác nguồn (XAUUSD chênh 0.02–0.06 USD).
- **Vấn đề:** HistData **2023 tháng 1–7** mất rất nhiều giờ lẻ: ~480 giờ XAUUSD, ~560 giờ EURUSD.
  Ngoài ra rải rác vài ngày (30/11/2020, 31/05/2021, 27/05/2019, giờ đầu phiên Chủ nhật ngày châu Âu
  đổi giờ).
- **Quy tắc lấp** (`--fill-dukascopy`):
  1. Chỉ xét khoảng trống có **≥ 50 phút nằm trong phiên theo lịch khai báo** (§5), dài tối đa 24
     giờ; **chỉ lấp phút nằm trong phiên**.
  2. Chỉ dùng một ngày Dukascopy khi ≥ 95% (và ≥ 50) số phút trùng nhau có close bằng nhau đến
     từng điểm giá.
  3. Bỏ nến «phẳng» volume 0 của Dukascopy (thị trường đóng).
  4. Không nội suy.
- **Kết quả:**

  | Cặp | Khoảng đã lấp / xét | Phút đã lấp | Trong đó 2023 |
  |---|---|---:|---:|
  | XAUUSD | 612 / 616 | 44 968 | 42 267 |
  | EURUSD | 691 / 691 | 49 000 | 45 675 |

  Mọi ngày Dukascopy được dùng đều khớp **100%** số phút trùng. 4 khoảng không lấp được vì nguồn
  cũng không có nến.
- **Truy vết:** danh sách khoảng ở `{PAIR}_lap_tu_dukascopy.csv`, tổng theo tháng trong
  `quality.json`. Cần dữ liệu chỉ một nguồn thì chạy `build` **không** có `--fill-dukascopy`.

## 5. Lịch phiên khai báo 2018–2025

Lịch là **dữ liệu khai báo** (nguyên tắc của dự án), không suy từ dữ liệu. Dữ liệu và nguồn ngoài chỉ dùng
để **kiểm** lịch.

| Lịch | Dùng cho | Nguồn | Nội dung |
|---|---|---|---|
| `cme_globex_metals` | XAUUSD | `pandas_market_calendars` 5.4.0, lịch `CMEGlobex_Gold` + ngoại lệ có nguồn | 2 065 phiên Chủ nhật–Thứ Sáu 18:00 → 17:00 NY; nghỉ 17:00–18:00; 23 ngày thường đóng cửa (Năm mới, Good Friday, Giáng sinh…); 65 phiên đóng sớm |
| `fx_spot` | EURUSD | Thông lệ FX giao ngay OTC (không có lịch sàn) | 2 076 phiên Chủ nhật 17:00 → Thứ Sáu 17:00 NY, không nghỉ hằng ngày; đóng 12 ngày giao dịch 25/12 và 01/01 rơi vào ngày thường |

**Giờ đóng sớm ngày lễ Mỹ** (theo thư viện):
- 13:00 NY tới 2021; 14:30 NY từ 2022 (Labor Day vẫn 13:00);
- ngày sau Lễ Tạ ơn: 13:45 NY.

**Ngoại lệ bổ sung** — chỉ khi có nguồn ngoài thư viện:
- **24/12 đóng 13:45 NY** (12:45 giờ Chicago), các năm 2018–2020, 2024, 2025. Thư viện thiếu quy
  tắc này. Nguồn: [lịch nghỉ lễ CME](https://www.cmegroup.com/trading-hours.html),
  [CrossTrade](https://crosstrade.io/blog/cme-trading-hours-2026). Dữ liệu dừng lúc 13:43–13:44 NY
  các năm đó.
- **04/07/2025 đóng 13:00 NY** (thư viện ghi 14:30): GC=F (dữ liệu CME qua Yahoo) có nến cuối
  12:00–13:00, không có nến sau đó; dữ liệu nguồn cũng dừng 12:58.

**Kiểm lịch bằng dữ liệu** (`quality.json`): đếm nến nằm **ngoài** phiên theo lịch.

| | XAUUSD | EURUSD |
|---|---|---|
| Nến ngoài phiên | 644 | 2 449 |
| Ở đâu | 127 nến lẻ đúng 17:00 NY năm 2018 (một tick lúc 17:00:00); 517 nến trong giờ lịch ghi đóng sớm ngày lễ (bảng dưới) | Phiên Á tối 24/12 → ~03:00 NY sáng 25/12 mỗi năm |

**Chỗ lịch và dữ liệu chưa khớp — chưa xác minh được, KHÔNG sửa lịch:**

| Ngày | Lịch (thư viện) | Dữ liệu nguồn | Nguồn ngoài |
|---|---|---|---|
| Labor Day 2022–2025 | đóng 13:00 NY | chạy tới 14:29 NY (~89 phút ngoài lịch) | Các trang tổng hợp mâu thuẫn (12:30 ET hay 13:30 CT); Yahoo không có nến ngày này |
| Sau Lễ Tạ ơn 2024, 2025 | đóng 13:45 NY | chạy tới 14:44 NY | GC=F 2025 có nến cuối 12:30–13:30 → nhiều khả năng nguồn (giá giao ngay) báo giá quá giờ CME |
| MLK 2022, 2023; 19/06 và 04/07/2023 | đóng 14:30 NY | dừng 13:00 / 14:00 NY | Không có (ngoài khoảng 730 ngày của Yahoo) |
| FX 25/12 | đóng cả ngày | có giá phiên Á ~10 giờ | Broker FXCM gần như không có nến 25/12 và 01/01 (chỉ 5 nến H1 cả 8 năm) → giữ lịch đóng |

Hệ quả khi dùng:
- Các phút đó bị tính là «nến ngoài phiên» hoặc «thiếu trong phiên» trong báo cáo chất lượng.
- Chúng **không** được lấp và **không** bị xoá.

## 6. Chất lượng còn lại — cần biết khi dùng

**Chung:**
- **Không có volume** (HistData luôn 0) và chỉ có BID, không có spread.
- **Dòng trùng:** mỗi năm 2019–2025 có 60 dòng HistData lặp nguyên văn (tháng 10); đã bỏ, không có
  dòng trùng khác giá.

**Khoảng trống giữa hai nến M1, phân loại theo lịch** (`quality.json`):

| | XAUUSD | EURUSD |
|---|---|---|
| Nghỉ hằng ngày · cuối tuần · lễ | 1 330 · 297 · 54 | — · 330 · 282 |
| Khoảng trống có phút thiếu trong phiên | 1 814 | 9 657 |
| Phút thiếu trong phiên — khoảng < 5 phút | 1 996 | 11 977 |
| Phút thiếu trong phiên — khoảng 5–59 phút | 235 | 958 |
| Phút thiếu trong phiên — khoảng ≥ 60 phút | 3 251 | 3 372 |

- Khoảng ngắn là phút không có giao dịch (thanh khoản mỏng), bình thường.
- Khoảng ≥ 30 phút còn lại (30 với XAUUSD, 20 với EURUSD) gồm:
  - HistData 2023 dừng sớm 1–3 giờ trước giờ đóng tuần (≈ 20 Thứ Sáu tháng 2–7/2023). Khoảng này
    vắt qua cuối tuần nên dài hơn 24 giờ, chưa xét lấp.
  - 12/01/2024 XAUUSD mất 13:00–17:00 NY.
  - 05/12/2025 XAUUSD mất 11:00–17:00 NY.
  - 24/05/2019 mất phiên tối Chủ nhật.
  - Good Friday 2023 với EURUSD.
  - Các chỗ lệch lịch ngày lễ ở §5.

  Danh sách đầy đủ ở `thieu_trong_phien_tu_30_phut`.

## 7. Định dạng và quy ước

- CSV `time,open,high,low,close,volume[,m1_count][,trading_day]`.
  - `time` = **giờ MỞ nến, UTC**.
  - `m1_count` = số nến M1 tạo nên nến đó.
  - `trading_day` (chỉ D1) = ngày giao dịch kết thúc 17:00 NY.
- Giá: XAUUSD 3 chữ số thập phân, EURUSD 5.
- **Mốc nến:** M5/M15/H1 theo bội số UTC; **H4/D1 theo `ny_1700`** (ngày giao dịch bắt đầu 17:00
  New York; H4 mở 17, 21, 01, 05, 09, 13 giờ NY). Muốn mốc UTC: `build --h4d1-alignment utc_epoch`.
  Lưu ý: chức năng gộp khung của market-structure-lab (`resample.py`) dùng mốc UTC cho H4.

## 8. Đối chiếu nguồn ngoài (`python -m marketdata.compare`)

### 8.1. EURUSD so với broker FXCM — H1 2018–2025 (48 380 nến khớp giờ)

| Đo | Kết quả |
|---|---|
| Tương quan lợi suất theo giờ ở độ lệch −2 / −1 / **0** / +1 / +2 giờ | −0.004 / −0.015 / **0.998** / −0.016 / −0.004 |
| Riêng các tuần Mỹ–Âu lệch lịch (3 329 nến) | **0.9985** ở độ lệch 0; ~0.04 ở ±1 giờ |
| Từng năm 2018–2025 | 0.997–0.999 ở độ lệch 0 |
| Chênh close H1 (BID–BID) | trung vị 0.1 pip, P90 0.3 pip, P99 2 pip |
| Close D1, cùng gộp theo mốc **17:00 NY** | trung vị **0.5 pip**, P90 2.5 pip |
| Close D1, nếu gộp theo mốc 00:00 UTC | trung vị 3.0 pip, P90 9.7 pip |

→ Giờ của dữ liệu đúng tới từng giờ ở mọi năm, kể cả tuần lệch lịch. D1 của ta trùng cách broker
chia ngày (17:00 New York).

### 8.2. So với Yahoo (nến 60 phút, 04/10/2024 → 31/12/2025)

Lợi suất mỗi nến Yahoo so với giá M1 của ta lấy đúng mốc đầu/cuối nến đó:

| Mã Yahoo | So với | Độ lệch 0 | ±1 giờ | Tuần lệch lịch |
|---|---|---:|---:|---:|
| `GC=F` (vàng COMEX, CME) | XAUUSD | **0.947** | −0.01 / −0.02 | 0.945 |
| `EURUSD=X` | EURUSD | **0.977** | −0.02 / −0.02 | 0.977 |

GC=F là hợp đồng tương lai nên giá khác giao ngay một khoản; chỉ so lợi suất. Tương quan < 1 là do
khác công cụ và nến Yahoo trong giờ chính lệch mốc :30.

### 8.3. TradingView — so bằng mắt

TradingView không có API công khai; tự động lấy dữ liệu từ đó vi phạm điều khoản sử dụng, nên
không làm. Để tự kiểm:
1. Mở `OANDA:XAUUSD` hoặc `FX:EURUSD`.
2. Đặt múi giờ biểu đồ là **New York**.
3. Tìm các nến dưới đây.

Khác broker thì giá lệch vài cent (vàng) hoặc 0.1–1 pip (EURUSD), nhưng **giờ mở nến và hình dạng
phải trùng**. Nến H4/D1 trên TradingView của các mã forex/kim loại thường chia theo phiên 17:00 NY.
Nếu thấy nến H4 mở lúc 16:00/20:00 NY thì biểu đồ đang chia theo mốc khác.

| Mã | Khung | Nến (giờ NY) | Open | High | Low | Close | Ghi chú |
|---|---|---|---:|---:|---:|---:|---|
| XAUUSD | H4 | 13/03/2024 13:00 | 2173.585 | 2179.745 | 2171.665 | 2174.065 | tuần lệch lịch — bản cũ sai ở đây |
| XAUUSD | H4 | 10/07/2024 09:00 | 2377.685 | 2386.548 | 2373.848 | 2377.748 | tuần bình thường |
| XAUUSD | H4 | 29/10/2025 13:00 | 3992.398 | 4007.025 | 3927.585 | 3928.435 | tuần lệch lịch mùa thu |
| XAUUSD | D1 | ngày 13/03/2024 (mở 12/03 17:00) | 2157.538 | 2179.745 | 2155.665 | 2174.065 | |
| XAUUSD | D1 | ngày 29/10/2025 (mở 28/10 17:00) | 3952.598 | 4029.955 | 3914.548 | 3928.435 | |
| EURUSD | H4 | 13/03/2024 13:00 | 1.09490 | 1.09638 | 1.09456 | 1.09471 | |
| EURUSD | H4 | 29/10/2025 09:00 | 1.16340 | 1.16660 | 1.16316 | 1.16570 | |
| EURUSD | D1 | ngày 13/03/2024 | 1.09257 | 1.09638 | 1.09201 | 1.09471 | |
| EURUSD | D1 | ngày 29/10/2025 | 1.16504 | 1.16660 | 1.15773 | 1.16005 | |

## 9. Dùng trong market-structure-lab

- Lab nạp dữ liệu từ thư mục `data/` của repo này bằng `scripts/import_market_data.py` của lab. Đặt
  hai repo cạnh nhau, hoặc chỉ đường bằng `--source-dir` / biến môi trường `MDP_DATA_DIR`.
- Lab giữ bản sao `calendars/*.json` (ở `data/calendars/`) và `session_calendar.py` (ở
  `core/data/`). Khi lịch ở đây đổi thì chép lại sang lab.
- Lab từng nạp XAUUSD 2024 với quy đổi giờ New York (sai, §3). Ngày 02/10/2026 đã thay bằng bản đúng
  giờ: bản cũ được giữ, tên có tiền tố `[LỆCH GIỜ …]`, chỉ để mở các run cũ.
