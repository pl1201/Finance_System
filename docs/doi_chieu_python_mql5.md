# Đối chiếu Python ↔ MQL5 (`swing_pivot`)

Script [`mql5/SwingPivotExport.mq5`](../mql5/SwingPivotExport.mq5) lặp nến
**đã đóng** (`i = rates_total-1 … 1`, bỏ nến 0 đang chạy), áp cùng quy tắc
pivot left/right tuyệt đối, HH/HL/EQH, phá close, phân loại CHoCH / BOS nội bộ
như `docs/thuat_toan_swing_pivot.md` v1.1.0.

Xuất CSV: `structure_type,event_bar_index,confirmed_bar_index,price,event_id,algorithm_version`.

Cột `event_bar_index` là chỉ số **tăng theo thời gian** (0 = nến cũ nhất trong
snapshot), trùng `Bar.index` Python trên cùng dải.

## Cách so

1. Xuất cùng snapshot OHLC (custom symbol hoặc file) → nhập lab, ghi
   `checksum_sha256`.
2. Chạy `swing_pivot` 1.1.0 cùng `left/right/bos_buffer`.
3. Chạy script MQL5 trên đúng symbol/TF, copy CSV.
4. Tab **Đối chiếu MQL5** hoặc `POST /api/compare-mql5`.

**Checksum khác nhau → cảnh báo, không kết luận lỗi code** (hai feed).

Ghép sự kiện: cùng loại, dung sai nến/giá (mặc định 0 nến / 0 giá vì cùng
công thức). Báo cáo lệch theo loại, vị trí, `confirmed_bar_index`.
