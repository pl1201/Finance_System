# Dữ liệu thị trường trong lab

Ngày: 02/10/2026.

- **Bộ sinh dữ liệu** nằm ở repo riêng `market-data-pipeline`:
  - repo chung của team trên GitHub: `https://github.com/pl1201/Finance_System`;
  - bản làm việc ở `D:\Finance_System\market-data-pipeline`, đặt cạnh lab. Ở đó có mọi thứ về nguồn, quy đổi giờ, lấp dữ liệu, lịch phiên, kiểm chứng và các
  lệnh dựng lại: **`market-data-pipeline/docs/du_lieu_thi_truong.md`**. Các mục tham chiếu trong tài
  liệu lab: §3 múi giờ, §4 lấp, §5 lịch phiên, §6 chất lượng, §8 đối chiếu nguồn ngoài.
- Tài liệu này chỉ ghi phần **lab dùng**: dataset nào đã nạp, cách nạp thêm, bản sao lịch phiên, giới
  hạn khi chạy trên dữ liệu dài.

## 1. Dataset đã nạp

Tất cả: giá BID, giờ UTC (mốc mở nến), không có volume; H4/D1 cắt theo ngày giao dịch bắt đầu 17:00
New York.

**XAUUSD và EURUSD 2018–2025** — nạp thẳng file của pipeline (`import_market_data.py series`):

| Khung | XAUUSD | EURUSD |
|---|---|---|
| M5 2018–2021 | `ds_c962af6036a4` (283 745) | `ds_a34c46a44233` (299 182) |
| M5 2022–2025 | `ds_4624bac8a089` (283 172) | `ds_17ffe8e4b74d` (298 571) |
| M15 | `ds_a5212fd37814` (189 073) | `ds_a9a2a5e4cef5` (199 296) |
| H1 | `ds_83abaa3c6eab` (47 386) | `ds_ab9f7729cb17` (49 827) |
| H4 (mốc 17:00 NY) | `ds_2c79dddcd829` (12 365) | `ds_8e87b4f82dfe` (12 468) |
| D1 (mốc 17:00 NY) | `ds_ba2c0dbea8c0` (2 065) | `ds_370f222212a9` (2 082) |

M5 chia hai dataset vì giới hạn 500 000 nến/dataset (`MAX_BARS_PER_DATASET`).

**M1 — mỗi năm một dataset** (`import_market_data.py m1-year --resample ""`; nặng — không nên mở chart):

| Năm | XAUUSD | EURUSD |
|---|---|---|
| 2018 | `ds_ef510eb77ea7` (353 778) | `ds_056876879fa1` (372 607) |
| 2019 | `ds_c48463e3c905` (352 928) | `ds_4a0fea697508` (372 890) |
| 2020 | `ds_0738ef2ade75` (355 492) | `ds_8f479b72086e` (373 473) |
| 2021 | `ds_0866d7660d81` (354 346) | `ds_084a261f98aa` (370 685) |
| 2022 | `ds_96f52ae16db4` (354 628) | `ds_6ac1a1a5f4c0` (372 865) |
| 2023 | `ds_0dea7c8ebb18` (351 019) | `ds_4ee0d2b0c434` (368 253) |
| 2024 | `ds_0d44e89df5fd` (355 652) — nạp cùng bộ 2024 bên dưới | `ds_01e4988cab6f` (372 723) |
| 2025 | `ds_3d1122e324f8` (354 071) | `ds_1363922882cc` (372 084) |

Sau khi nạp đủ, `data/lab.sqlite` ~1,4 GB.

**XAUUSD 2024** (`import_market_data.py m1-year`):
- nạp M1, rồi gộp M5/M15/H1 bằng `resample_dataset` của lab;
- **thay bộ 2024 cũ bị lệch giờ** (bộ cũ quy đổi theo giờ New York, sai trong các tuần Mỹ–Âu lệch
  lịch đổi giờ — §3 tài liệu pipeline).

| Khung | Dataset (đúng giờ) | Bộ cũ — giữ lại, tên có tiền tố `[LỆCH GIỜ — dùng …]` |
|---|---|---|
| M1 | `ds_0d44e89df5fd` | `ds_1f78f44c0ba5` |
| M5 | `ds_933fa5ec67e2` | `ds_84680e6033c3` |
| M15 | `ds_db1583cd4dde` (dùng cho `research/ict_survey.py`) | `ds_564bff443e42` — 30 run cũ dùng bộ này |
| H1 | `ds_771a79d4d604` | `ds_5797877d0752` |

Bộ cũ chỉ để mở run cũ. **Không dùng cho phân tích mới.** Đã kiểm trước khi thay:
- 21 965 nến M15 ngoài các tuần lệch lịch trùng hệt bộ cũ;
- 1 748 nến trong các tuần lệch lịch khớp khi dời +1 giờ;
- không có khác biệt nào khác.

**Sao lưu DB** trước mỗi lần nạp: `data/backup/` (không đưa vào git). Hiện có 3 bản, tổng ~0,9 GB;
bản mới nhất `lab_20261002T062027Z.sqlite` là trạng thái ngay trước khi nạp M1. Các bản cũ hơn xoá
được khi không cần quay lại.

## 2. Nạp thêm

```powershell
# thử trên bản sao DB (không đụng DB và data/raw thật)
.\.venv\Scripts\python.exe scripts\import_market_data.py --dry-run series --pair EURUSD --tf M15
# nạp thật (tự sao lưu DB)
.\.venv\Scripts\python.exe scripts\import_market_data.py series --pair EURUSD --tf M15,H1
.\.venv\Scripts\python.exe scripts\import_market_data.py m1-year --pair EURUSD --year 2024 --resample M5,M15,H1
```

- Thư mục nguồn mặc định là `..\market-data-pipeline\data`; đổi bằng `--source-dir` hoặc biến môi
  trường `MDP_DATA_DIR`.
- Dữ liệu trùng nội dung với dataset đã có thì được bỏ qua.
- Ghi chú (`notes`) của mỗi dataset ghi file nguồn, sha256 và quy tắc giờ.

## 3. Lịch phiên khai báo

- Lab giữ **bản sao** lịch của pipeline: `data/calendars/cme_globex_metals.json` (XAUUSD) và
  `data/calendars/fx_spot.json` (EURUSD).
- Hai lịch được đọc bằng `core/data/session_calendar.py` — bản sao của `marketdata/session_calendar.py`.
- Khi pipeline sinh lại lịch thì chép hai file JSON sang đây và chạy `pytest tests/core/test_session_calendar.py`.
- Lịch là dữ liệu khai báo (AGENTS §2.2). Chỗ lịch và dữ liệu chưa khớp nằm ở §5 tài liệu pipeline.

## 4. Thuật toán trên dữ liệu dài (kiểm 02/10/2026)

**Ma trận** 6 thuật toán × 12 dataset (mỗi khung một dataset cho mỗi cặp), chạy toàn bộ dataset,
không lưu run; thời gian tính cả nạp nến và đóng gói kết quả:

| Thuật toán | M1 (1 năm) | M5 (4 năm) | M15 (8 năm) | H1 / H4 / D1 (8 năm) |
|---|---|---|---|---|
| `swing_pivot` | ~10 s | ~8–9 s | ~5 s | ≤ 1,3 s |
| `swing_hierarchy` | 7–8 s | 6 s | 3–4 s | ≤ 1 s |
| `indicator_baseline` | 4–5 s | 4 s | 2 s | ≤ 1 s |
| `hmm_online` | 17–26 s | 19–23 s | 9–12 s | 1–3 s |
| `dc_atr_structure` | 12–13 s | 8–9 s | 3–5 s | ≤ 1 s |
| `c2_cisd_research` | — | — | 8–10 s | — |

`c2_cisd_research` chỉ nhận M15 (chiến lược M15–H4) — theo thiết kế, không phải lỗi.

**Đã sửa để chạy được:**
- `swing_pivot` trước đây chậm theo bình phương số nến (M15 8 năm quá 60 s). Đã tối ưu, output
  không đổi — `thuat_toan_swing_pivot.md` §9b; hồi quy 60/60 run đã lưu khớp.

**Lưu, mở lại, replay** (bản sao DB):
- Lưu run 46 000–145 000 sự kiện: 6–17 s.
- Mở lại run đã lưu: 1–2 s.
- Xuất CSV: 1–3 s.
- Replay trên M15 8 năm: seek tới nến 150 000 mất 3,7 s; mỗi bước tiến/lùi ≤ 1 s.

**Giao diện:**
- Kết quả chạy cả dataset dài nặng 90–230 MB JSON (timeline có một điểm mỗi nến).
- Vì vậy khoảng mặc định chỉ lấy **~50 000 nến gần nhất**.
- Chạy hoặc replay trên khoảng ước tính hơn 100 000 nến phải xác nhận.
- Smoke Chrome: mỗi lần chạy mặc định ~3 s. Chạy toàn bộ M15 8 năm (`dc_atr_structure`) ~8–11 s; heap
  ~290 MB.
- Lỗi vẽ biểu đồ «Value is null» khi đổi dataset sau một lần chạy đã sửa (`frontend/js/chart/market-chart.js`: xoá lớp phủ
  trước khi nạp nến mới).

**Lưu ý phân tích:** dataset 2018–2025 **chứa cả đoạn kiểm tra** của plan ICT (09–12/2024). Khi phân
tích thiết kế, giới hạn khoảng thời gian về đoạn phát triển.
