# Đánh giá thuật toán nhận diện cấu trúc

Trang **Đánh giá thuật toán** (`/danh-gia`) so sánh chất lượng nhận diện và độ
trễ xác nhận. Không nhét F1/P90 vào tab thống kê nhỏ dưới chart thử nghiệm.

> Không có đồng hồ «chất lượng 85/100», không tự gắn «thuật toán tốt nhất».
> Nếu nhóm chưa chốt tiêu chí, trang chỉ trình bày đánh đổi (F1 ↔ độ trễ).
> Precision/recall/F1 **không hiện số 0** khi chưa có nhãn tham chiếu.

Giai đoạn A–C (protocol, trang, truy vết/lưu) nằm trong bản này. Từ 10/2026 có thêm
**đoạn phát triển / kiểm tra** (§1.2) và **chuẩn ngẫu nhiên** (§1.3) — bộ đo dùng chung cho mọi
thuật toán sau (`kien_truc_luong_ict.md` §6 bước 1). Độ nhạy tham số và khoảng bất định
(bootstrap) **chưa** có (§6).

---

## 1. Protocol `1.0.0`

Mọi lần chấm lưu đủ quy tắc để tái lập. Đổi quy tắc phải tăng `PROTOCOL_VERSION`
hoặc `matcher_version` — kết quả cũ/mới không trộn (nhóm so sánh khoá theo
`protocol_hash`).

| Trường | Mặc định | Ý nghĩa |
|---|---|---|
| `target` | `swing_cau_truc` | `swing_nho` (cấp 1), `swing_cau_truc` (cấp 2), `ict_shift` (ict_structure) |
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
| `null_mode` / `null_n` / `null_seed` | `off` / 200 / 1 | Chuẩn ngẫu nhiên (§1.3): `uniform_v1` hoặc `matched_hour_atr_v1`; N trong [10, 1000] |
| `segments` / `test_unlocked` | `[]` / false | Đoạn phát triển / kiểm tra theo thời gian (§1.2); mở đoạn kiểm tra |

Các trường `null_*`, `segments`, `test_unlocked` **chỉ có mặt** trong protocol (và trong
`protocol_hash`) khi được bật. Protocol cũ giữ nguyên dict và hash — có test khoá hash của các
protocol thật đã lưu.

**Khoảng gán nhãn đầy đủ rất quan trọng.** Sự kiện có `event_bar_index` ngoài
`[start, end]` bị **bỏ**, không phải false positive. Chưa khai khoảng → mọi sự
kiện trong lần chạy được coi là trong phạm vi chấm (ghi chú trên trang).

### 1.1. Không gian chỉ số — chấm theo chỉ số nến của dataset

Nhãn và khoảng chấm (`coverage_*_index`) đếm nến **từ đầu dataset**. Sự kiện của một run chạy
khoảng con đếm từ **nến đầu của run**. Khi chấm, sự kiện được cộng `range_start_index` của run
(run chạy cả dataset: cộng 0). TP/FP trong kết quả mang chỉ số dataset; chart chi tiết đánh số
nến theo `dataset_index` mà API nến trả kèm.

> **Sửa lỗi 10/2026.** Trước đó chỉ số không được đổi: run bắt đầu sau nến 0 bị chấm lệch đúng
> `range_start_index` nến (cùng các pivot với run cả dataset nhưng recall 0), và nhãn bấm trên
> chart trang Thử nghiệm khi đang xem một khoảng con bị lưu sai vị trí. Không đánh giá đã lưu
> nào bị ảnh hưởng (mọi đánh giá đã lưu dùng run bắt đầu ở nến 0). Test:
> `tests/api/test_eval_index_space.py`.

### 1.2. Đoạn phát triển / kiểm tra (walk-forward theo cửa sổ)

Khai **trước khi xem kết quả** (AGENTS.md §6.3). Mỗi đoạn: tên, vai (`dev` | `test`), từ, đến —
giờ UTC, nửa mở `[từ, đến)` theo giờ **mở** nến. Theo thời gian chứ không theo chỉ số, vì M5 /
M15 / H1 có không gian chỉ số khác nhau.

* **Mỗi đoạn là một cửa sổ chấm** (giao với khoảng chấm, nếu khai): sự kiện ngoài mọi đoạn không
  bị tính FP — như ngoài khoảng chấm. Vì vậy đoạn phải là khoảng **đã gán nhãn đầy đủ**. Nhãn gán
  ở vài cửa sổ rời nhau (bộ nhãn D8: 2 tuần trong đoạn phát triển + 2 tuần trong đoạn kiểm tra)
  chấm được mà phần không gán ở giữa không thành FP.
* Ghép **riêng từng đoạn** (không có cặp nhãn–sự kiện vắt qua hai đoạn); quy tắc «bỏ đuôi chưa xác
  nhận» tính theo nến cuối của **từng đoạn** — sự kiện của đoạn phát triển xác nhận trong đoạn sau
  không được tính cho đoạn phát triển.
* **Số tổng = gộp các đoạn phát triển.** `by_segment` cho số riêng từng đoạn (F1, P, R, TP/FP/FN,
  trễ P90, mật độ, chuẩn ngẫu nhiên nếu bật).
* **Đoạn kiểm tra khoá mặc định**: không chấm, không hiện số, không lọt vào số tổng. Mở bằng
  `test_unlocked` (ô «Mở đoạn kiểm tra», có hỏi lại) — ghi vào protocol/hash và gắn
  `[ĐÃ MỞ ĐOẠN KIỂM TRA]` vào ghi chú đánh giá. Khi đã mở, đoạn kiểm tra chỉ có số riêng, vẫn
  không gộp vào số tổng. Chỉnh tham số theo số của đoạn kiểm tra làm mất tính độc lập của nó.
* Luật hợp lệ: tối đa 24 đoạn, không chồng nhau, mọi đoạn kiểm tra nằm **sau** mọi đoạn phát
  triển. Sai → lỗi 400 nêu rõ.
* Đoạn nằm ngoài khoảng run đã chạy → trạng thái «ngoài khoảng».
* Khoá chỉ áp dụng cho **chấm điểm**: trang Thử nghiệm vẫn vẽ sự kiện của giai đoạn kiểm tra nếu bạn
  chạy tới đó.

### 1.3. Chuẩn ngẫu nhiên — có hơn đặt sự kiện ngẫu nhiên cùng mật độ không?

F1 = 0.6 chưa nói được gì nếu đặt sự kiện ngẫu nhiên cũng được 0.5. Chuẩn ngẫu nhiên giữ nguyên
**nhãn**, thay **sự kiện** của run bằng sự kiện ngẫu nhiên rồi chấm bằng đúng protocol:

* cùng số sự kiện theo từng loại nguồn trong từng cửa sổ chấm (khoảng chấm, hoặc từng đoạn);
* đặt trên nến **thật** trong cửa sổ, sau warm-up — không rơi vào giờ nghỉ / chỗ thiếu dữ liệu;
* giá theo quy tắc giá của detector, suy từ sự kiện thật (trường high / low / close / open trùng
  ≥ 95% số lần). Loại nào không suy được (giá là một mức tính ra) → «không áp dụng»;
* cùng matcher và dung sai. Số TP của mỗi lượt bằng đúng matcher gốc (tách cụm theo dung sai thời
  gian chỉ để nhanh — có test so trên 300 ca ngẫu nhiên cho cả hai matcher).

| Chế độ | Đặt sự kiện ngẫu nhiên |
|---|---|
| `matched_hour_atr_v1` (nên đọc) | Mỗi sự kiện thật kéo một sự kiện ngẫu nhiên cùng **giờ New York** của nến (theo giờ mở nến, có đổi giờ mùa hè) và cùng **nhóm ATR** (tam phân vị ATR Wilder trên các nến của cửa sổ). Nhóm thiếu nến → bù cùng giờ, rồi bù đồng đều; số sự kiện phải bù được ghi lại. |
| `uniform_v1` | Đồng đều trên các nến chấm được. Swing và nhãn dồn vào giờ sôi động, biến động lớn — rải đồng đều đưa sự kiện ngẫu nhiên vào giờ vắng nên **làm thuật toán trông giỏi hơn thực tế**. Chỉ để so. |

Kết quả `null_baseline` của mỗi run: phân phối P / R / F1 qua N lượt (TB, sd, P5, P50, P95), F1 thực
tế, số lượt có F1 ≥ thực tế và `p_ge = (1 + số lượt ≥) / (N + 1)`, phân vị của thực tế, sai số
chuẩn √(p(1−p)/n) của P/R thực tế (xấp xỉ **lạc quan** vì swing không độc lập). Lượt có TP = 0
tính F1 = 0, không bỏ; F1 thực tế trống (TP = 0) khi có nhãn được so như 0. Chưa có nhãn →
«chưa có nhãn», không hiện số.

* **Tất định**: số ngẫu nhiên lấy từ sha256(seed | cửa sổ | loại | nhóm | lượt | bộ đếm) — không
  phụ thuộc phiên bản Python, thứ tự run hay các run khác trong cùng lần đánh giá (các run có cùng
  số sự kiện dùng chung các lượt → so sánh công bằng hơn). Đổi seed = lần lấy mẫu khác.
* **Chỉ để đánh giá.** Nhóm ATR dùng thống kê của cả cửa sổ (kể cả «tương lai» của nó) — được vì
  đây là thước đo sau sự kiện, không bao giờ là đầu vào detector (AGENTS.md §2.1). Không có win
  rate / P&L.
* Giới hạn khối lượng: N × (số nhãn + số sự kiện trong các cửa sổ) ≤ 3 000 000 mỗi run; vượt → lỗi
  400, giảm N hoặc thu hẹp khoảng chấm.
* Bật chuẩn ngẫu nhiên **không đổi** số của run thật (có test so từng trường).

### Ánh xạ loại — không đếm hai lần cùng một pivot

Chỉ loại có trong `event_type_map` mới được đếm là swing của mục tiêu.

* Mục tiêu `swing_nho`: `SWING_HIGH`, `SWING_LOW`. HH/LH/EQH/BOS **không** đếm
  thành swing thứ hai của cùng pivot.
* Mục tiêu `swing_cau_truc`: `SWING_HIGH_L2`, `SWING_LOW_L2`.
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
| POST | `/api/evaluate` | Ghép greedy của tab nhãn — **không** phải protocol trang này (cũng chấm theo chỉ số dataset, §1.1) |

`POST /api/evaluations` nhận `{run_ids, protocol, label_set_id?, baseline_run_id?, save, note_vi}`.
Bật chuẩn ngẫu nhiên / đoạn → mỗi run có thêm `null_baseline`, `by_segment`, `segments_note_vi`;
báo cáo `report.md` thêm hai bảng tương ứng.

`GET /api/datasets/{id}/bars` và `GET /api/replay/{sid}/bars`: mỗi nến có `index` (từ nến đầu
khoảng, như sự kiện của run chạy khoảng đó) và `dataset_index` (từ nến đầu dataset, như nhãn).

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

Trong khung **Protocol chấm**: «Chuẩn ngẫu nhiên» (chế độ, N, seed) và «Đoạn phát triển / kiểm
tra» (bảng đoạn, ô mở đoạn kiểm tra). Khi bật: thẻ F1 có dòng «Ngẫu nhiên TB … [P5–P95] · x/N lượt
≥ thực tế» (màu cảnh báo khi p ≈ > 0.05), bảng so sánh thêm cột «F1 ngẫu nhiên», tab Tổng quan
thêm khối chuẩn ngẫu nhiên và bảng **Theo đoạn**. Tắt cả hai thì trang giữ nguyên như trước.

---

## 6. Việc chưa làm (giai đoạn D)

* Độ nhạy tham số (lưới tham số trên đoạn phát triển, báo cáo độ ổn định).
* Khoảng bất định bootstrap cho P/R/F1 (hiện chỉ có sai số chuẩn xấp xỉ lạc quan).
* Chuẩn ngẫu nhiên cho metric nhìn về sau (vd «đạt DOL») — hiện chỉ cho
  chất lượng nhận diện so với nhãn.
* Ghép cặp theo killzone thay vì giờ: để khi định nghĩa killzone đã chốt (giờ tròn giữ được mọi
  định nghĩa killzone đang cân nhắc).
