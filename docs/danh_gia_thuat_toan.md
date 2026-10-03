# Đánh giá thuật toán nhận diện cấu trúc

Trang **Đánh giá thuật toán** (`/danh-gia`) so sánh chất lượng nhận diện và độ
trễ xác nhận. Không nhét F1/P90 vào tab thống kê nhỏ dưới chart thử nghiệm.

> Không có đồng hồ «chất lượng 85/100», không tự gắn «thuật toán tốt nhất».
> Nếu nhóm chưa chốt tiêu chí, trang chỉ trình bày đánh đổi (F1 ↔ độ trễ).
> Precision/recall/F1 **không hiện số 0** khi chưa có nhãn tham chiếu.

Giai đoạn A–C (protocol, trang, truy vết/lưu) nằm trong bản này. Walk-forward,
độ nhạy tham số và khoảng bất định (giai đoạn D) **chưa** triển khai.

---

## 1. Protocol `1.0.0`

Mọi lần chấm lưu đủ quy tắc để tái lập. Đổi quy tắc phải tăng `PROTOCOL_VERSION`
hoặc `matcher_version` — kết quả cũ/mới không trộn (nhóm so sánh khoá theo
`protocol_hash`).

| Trường | Mặc định | Ý nghĩa |
|---|---|---|
| `target` | `swing_cau_truc` | `swing_nho` (cấp 1), `swing_cau_truc` (cấp 2), `c2` hoặc `cisd` (c2_cisd_research) |
| `matcher_version` | `min_cost_v1` | Cách ghép một-một |
| `time_tolerance_bars` | 1 | Dung sai vị trí theo nến |
| `price_tolerance` | 0 | Dung sai giá |
| `coverage_start_index` / `coverage_end_index` | trống = cả lần chạy | **Khoảng được khai là gán nhãn đầy đủ** |
| `event_type_map` | theo mục tiêu | Loại sự kiện thuật toán → loại nhãn được chấm |
| `map_level1_to_structure` | false | Ánh xạ `SWING_HIGH`→`SWING_HIGH_L2` khi so pivot cấp 1 với mục tiêu cấp 2 |
| `atr_period` / `atr_source` | 14 / `wilder_confirm_bar` | ATR Wilder tại **nến xác nhận** |
| `exclude_unconfirmed_tail` | true | Bỏ sự kiện xác nhận sau nến cuối khoảng chấm |
| `max_lag_bars` | trống | Loại sự kiện trễ hơn ngưỡng |
| `min_recall` | trống | Sàn recall nếu nhóm đã chốt; không tự gắn «tốt nhất» |

**Khoảng gán nhãn đầy đủ rất quan trọng.** Sự kiện có `event_bar_index` ngoài
`[start, end]` bị **bỏ**, không phải false positive. Chưa khai khoảng → mọi sự
kiện trong lần chạy được coi là trong phạm vi chấm (ghi chú trên trang).

### Ánh xạ loại — không đếm hai lần cùng một pivot

Chỉ loại có trong `event_type_map` mới được đếm là swing của mục tiêu.

* Mục tiêu `swing_nho`: `SWING_HIGH`, `SWING_LOW`. HH/LH/EQH/BOS **không** đếm
  thành swing thứ hai của cùng pivot.
* Mục tiêu `swing_cau_truc`: `SWING_HIGH_L2`, `SWING_LOW_L2`.
* Mục tiêu `c2`: `C2_CONFIRMED_UP/DOWN` — nhãn ở nến M15 cực trị của C2, giá low
  (tăng) / high (giảm). Mục tiêu `cisd`: `CISD_CONFIRMED_UP/DOWN` — nhãn ở nến có
  close vượt mức CISD, giá = mức CISD (trang Gán nhãn mặc định lấy close — sửa giá
  hoặc nới dung sai giá). Ghép cùng loại, cùng hướng. Phía high = loại `_DOWN`,
  low = `_UP`. Không dùng nhãn HH/MSS thay nhãn C2/CISD. Xem
  [`thuat_toan_c2_cisd.md`](thuat_toan_c2_cisd.md) mục 10.
* So pivot cấp 1 với mục tiêu cấp 2: bật `map_level1_to_structure` — ánh xạ được
  **khai báo**, không chỉ so hai tên `structure_type` khác nhau.

Độ trễ swing **không** gộp với độ trễ BOS.

### Matcher

Hai phiên bản, lưu cùng kết quả:

| Phiên bản | Hành vi |
|---|---|
| `greedy_label_order_v1` | Tab *Nhãn tham chiếu* / `POST /api/evaluate`. Mỗi nhãn (theo thứ tự nến) lấy sự kiện chưa dùng có \|Δnến\| nhỏ nhất, hoà thì \|Δgiá\|. Có thể bỏ lỡ gán tốt hơn khi nhiều sự kiện nằm gần nhau. |
| `min_cost_v1` | Mặc định trang đánh giá. Luồng chi phí tối thiểu (một-một, cùng loại, trong dung sai). |

Ví dụ greedy thất bại (có test tính tay): nhãn A tại nến 2 giá 10 lấy sự kiện Q
(nến 4, giá 10) thay vì P (nến 0, giá 12); nhãn B tại 5 không còn ứng viên → 1
TP. `min_cost_v1` gán A–P và B–Q → 2 TP.

---

## 2. Metric phiên bản đầu

| Nhóm | Hiển thị | Điều kiện |
|---|---|---|
| Chất lượng | Precision, recall, F1; TP/FP/FN; tách high/low | Có nhãn đúng phạm vi và mục tiêu |
| Độ trễ | Median, P90 nearest-rank `ceil(p/100*n)`; histogram | Có sự kiện và thời điểm xác nhận |
| Giá khi xác nhận | Median/P90 \|close xác nhận − pivot\|, chia ATR Wilder tại nến xác nhận | ATR đã seed; mẫu ATR không hợp lệ **bị loại**, không gán 0 |
| Mật độ | Swing / 100 nến chấm được; khoảng cách median giữa swing | Chỉ loại của mục tiêu |
| Tính hợp lệ | Bất biến trên **sự kiện đã lưu** của đúng run | Không suy từ pytest xanh |
| Hiệu năng | `algorithm_ms` (lúc chạy) vs `evaluation_ms` (lúc chấm) | Tách hai giai đoạn |

F1 = `2PR/(P+R)`. Mẫu số rỗng hoặc P=R=0 → F1 trống (không ép 0 trừ khi có nhãn
và mẫu số > 0).

Kiểm tra nhân quả trên trang này = bất biến đọc được từ sự kiện đã lưu (xác nhận
≥ nến sự kiện, trễ khớp chỉ số, không xác nhận trong warm-up). Trạng thái:
**Chưa kiểm tra** / **Có vi phạm** / **Đạt kiểm tra** — luôn kèm chữ, không chỉ
màu. Phạm vi ghi rõ thuật toán, phiên bản, tham số, khoảng nến của **run đó**.

---

## 3. Nhóm so sánh

Các run được xếp cùng nhóm khi trùng `dataset_id`, `range_start`/`range_end` và
`protocol_hash`. Khác dataset, khoảng chạy, bộ nhãn (lọc phía API) hoặc protocol
thì **tách nhóm** và ghi lý do. Baseline chỉ so trong cùng nhóm.

**M5, M15, H1 là các dataset khác nhau.** Không gian chỉ số nến không trùng, độ
trễ là **số nến của đúng khung** (3 nến M5 ≠ 3 nến H1). Trang có thanh **Khung**
để chuyển sang dataset cùng symbol nếu đã có — không tổng hợp/tách nến từ trang
đánh giá. Scatter và histogram chỉ vẽ nhóm của run đang chọn.

---

## 4. API

| Phương thức | Đường dẫn | Việc |
|---|---|---|
| GET | `/api/eval/meta` | Protocol, matcher, mục tiêu |
| POST | `/api/evaluations` | Chấm và (mặc định) lưu |
| GET | `/api/evaluations?dataset_id=` | Danh sách đã lưu |
| GET | `/api/evaluations/{id}` | Mở lại đủ protocol + kết quả |
| DELETE | `/api/evaluations/{id}` | Xoá bản ghi |
| GET | `/api/evaluations/{id}/report.md` | Xuất markdown |
| POST | `/api/evaluate` | Ghép greedy của tab nhãn — **không** phải protocol trang này |

`POST /api/evaluations` nhận `{run_ids, protocol, label_set_id?, baseline_run_id?, save, note_vi}`.

Lõi: `core/eval/` (không import FastAPI/pandas/MT5).

---

## 5. Giao diện

Điều hướng chính: **Thử nghiệm | Gán nhãn | Đánh giá thuật toán**.

Luồng: chọn dataset → khung M5/M15/H1 (dataset cùng symbol) → mục tiêu → bộ nhãn
(tạo trên [`/gan-nhan`](http://127.0.0.1:8099/gan-nhan) hoặc tab Thử nghiệm) → protocol → các run (một baseline) →
**Đánh giá** → chọn dòng/điểm scatter → bấm TP/FP/FN để chart nhảy tới nến → lưu
(tự lưu) / xuất báo cáo / mở lại.

Run đang chọn: viền xanh dương. Baseline: hình ◆ / nét vàng. Số căn phải, cùng
đơn vị. Scatter chọn được bằng bảng và phím mũi tên.

---

## 6. Việc chưa làm (giai đoạn D)

Đánh giá nhiều cửa sổ thời gian, độ nhạy tham số, khoảng bất định / báo cáo
ngoài mẫu.
