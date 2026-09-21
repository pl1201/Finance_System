# Nguồn MT5 và tổng hợp nến

## 1. `core/data/mt5_source.py`

Gói `MetaTrader5` **tuỳ chọn**. `import core.data.mt5_source` không yêu cầu đã cài
gói; `mt5_available()` cho biết máy hiện tại có gói hay không. Phần còn lại của
`core/` không import MetaTrader5.

### Nến đang hình thành

`copy_rates_from_pos(symbol, timeframe, start_pos=0, count)`: **index 0 là nến
đang hình thành**. Lab mặc định `drop_forming=True` và loại nến đó.

Với `copy_rates_range`, nến cuối bị loại nếu thời điểm đóng lý thuyết
(`bar_time + timeframe`) vẫn ở tương lai so với đồng hồ máy.

### Schema

Mỗi nến: `{bar_time, open, high, low, close, volume}` — `bar_time` UTC, **mốc
mở nến** (đúng MT5). Khi nhập vào lab, người dùng **vẫn phải khai báo** múi giờ
nguồn và quy ước timestamp; form MT5 điền sẵn UTC + mốc MỞ nhưng không tự suy
ra sau lưng.

Đưa vào DB qua `service.import_from_rows` → cùng đường `validate_and_clean`
như CSV.

API:

* `GET /api/mt5/status`
* `POST /api/datasets/import-mt5` với `symbol`, `timeframe`, `source_timezone`,
  `timestamp_convention`, và `count` hoặc `date_from`/`date_to`.

Cần terminal MT5 đang mở, symbol trong Market Watch.

## 2. Tổng hợp nến `core/data/resample.py`

Hỗ trợ **M1 → M5/M15/M30/H1/H4** và mọi bước lên (M5→H1, M15→H1, …) miễn đích
lớn hơn nguồn.

**Không tách nến lớn thành nến nhỏ** (H4→M5). Giao diện có thanh **Khung**:
nếu đã có dataset cùng symbol ở M5 thì bấm M5 để chuyển sang dataset đó;
nếu chưa có thì phải nhập CSV/MT5 khung nhỏ. Tổng hợp chỉ gộp lên.

**Mốc nến `utc_epoch`:** mở nến đích = bội số Unix UTC của độ dài timeframe
đích. H4 = 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC. Lab **không** đoán
lệch H4 theo broker.

**Giả định:** `bar_time` nguồn là mốc MỞ. Dataset nguồn phải khai báo
`timestamp_convention=open`.

**Khoảng không giao dịch:**

* Bucket không có nến nguồn: bỏ qua, không đúc nến giả, không ffill.
* Bucket thiếu nến so với `target_seconds / source_seconds`:
  * `drop_incomplete` (mặc định): không phát nến đích, ghi báo cáo.
  * `emit_available`: phát OHLCV từ nến có mặt, gắn cờ incomplete.

API: `POST /api/datasets/resample` `{dataset_id, target_timeframe, gap_policy}`.

Dataset tổng hợp từ nguồn mô phỏng vẫn gắn `is_synthetic` và ghi chú
DỮ LIỆU MÔ PHỎNG.
