# Nhãn tham chiếu và đo nhận diện

Precision/recall **chỉ** được tính khi có bộ nhãn do người gán, kèm tên người
gán. Công cụ không bịa accuracy.

## Trang Gán nhãn (`/gan-nhan`)

Luồng dùng hàng ngày:

1. Mở [`/gan-nhan`](http://127.0.0.1:8099/gan-nhan), chọn dataset (M5 / M15 / H1
   là dataset khác nhau — trang không tách/gộp nến).
2. Ghi **Người gán nhãn**, phiên bản, rubric.
3. Chọn loại (`SWING_HIGH` / `SWING_LOW` cho cấp 1, `*_L2` cho cấp 2).
4. Click nến **trống**: gán loại đang chọn — HIGH lấy `high`, LOW/DOWN lấy `low`.
   Click nến **đã có nhãn hoặc chấm đề xuất** thì mở bảng thao tác cạnh nến (xem
   *Thao tác trực tiếp trên chart* bên dưới). <kbd>Shift</kbd>+click luôn là
   gán/gỡ nhanh loại đang chọn, không mở bảng. Không cần chạy thuật toán trước.
5. **Lưu thành bộ mới** — tạo bộ mới (`lab_…`), không đụng bộ cũ.
6. **Mở đánh giá** mang `dataset_id` và `label_set_id` sang `/danh-gia` để chấm
   F1 (matcher `min_cost_v1`). Trang gán nhãn **không** hiện precision giả.

Nếu chỉ gán một đoạn chart, khai `coverage_start_index` / `coverage_end_index`
khi chấm — sự kiện ngoài khoảng không bị tính false positive.

Tab *Nhãn tham chiếu* trên trang Thử nghiệm có cùng các nút này (bản rút gọn,
gán trên chart thử nghiệm); matcher tab đó là `greedy_label_order_v1` /
`POST /api/evaluate`.

## Auto label: đề xuất + người duyệt (hybrid)

Khung **Auto label** ở cột phải trang `/gan-nhan` dùng thuật toán **có sẵn** để
đề xuất nhãn, người gán chấp nhận hoặc bỏ từng cái.

1. Chọn **thuật toán đề xuất** — chỉ liệt kê thuật toán sinh loại nhãn cấu trúc
   (`GET /api/auto-label/algorithms`, dựa trên `emits_types` của từng lớp):
   * `swing_pivot` — đỉnh/đáy cấp 1, BOS chính/nội bộ, CHoCH.
   * `swing_hierarchy` — đỉnh/đáy cấp 1 và **cấp 2**.
   * `indicator_baseline`, `hmm_online` không sinh nhãn cấu trúc nên không có mặt.
2. Chỉnh tham số (mặc định theo thuật toán) và chọn **khoảng thời gian**: chọn
   *Từ ngày giờ / Đến ngày giờ* (**UTC**), bấm **Vùng đang xem** (lấy đúng khoảng
   đang hiện trên chart) hoặc **Toàn bộ dataset**. Dòng bên dưới cho biết khoảng
   đó gồm bao nhiêu nến và tương ứng nến số mấy — nến đầu là nến đầu tiên có thời
   gian ≥ "Từ", nến cuối là nến cuối cùng có thời gian ≤ "Đến".
3. Chọn loại cần đề xuất rồi bấm **Đề xuất nhãn**
   (`POST /api/auto-label/suggest`).
4. Duyệt: đề xuất chờ duyệt hiện là **chấm xám `?H` / `?L`**, đề xuất đang xem
   là **chấm vàng `▶`**, chart tự căn giữa vào nó. Thanh duyệt dưới chart cho biết
   loại, nến, giá, nến thuật toán xác nhận và lý do.
   * <kbd>A</kbd> chấp nhận → vào bộ nháp, nhảy tới đề xuất kế tiếp.
   * <kbd>X</kbd> bỏ. <kbd>N</kbd> / <kbd>P</kbd> kế tiếp / trước.
   * Hoặc **bấm thẳng vào chấm** trên chart để chấp nhận / bỏ / chấp nhận thành
     loại khác ngay tại chỗ (xem dưới).
   * Đề xuất lệch một hai nến: chấp nhận rồi dời ◀ ▶ trong bảng thao tác.
   * **Chấp nhận hết phần còn lại** / **Bỏ hết phần còn lại** — có hộp xác nhận.
5. Sửa nhãn nếu cần (xem dưới), rồi bấm **Lưu** như bình thường. Tiến độ duyệt
   được giữ trong nháp trình duyệt nên tải lại trang không phải duyệt lại.

### Thao tác trực tiếp trên chart

Bấm vào nến có chấm đề xuất (xám/vàng) hoặc có nhãn nháp → bảng nhỏ mở cạnh nến,
liệt kê **mọi** đề xuất và nhãn trên nến đó:

* **Đề xuất**: *Chấp nhận*, *Bỏ*, hoặc *Chấp nhận nhưng đổi thành* một loại khác
  (vd. chấm `?BU` nhưng thực ra là `CU`). Đổi loại khi chấp nhận thì nguồn ghi
  ngay là `auto_edited`, không bao giờ thành `human`. Giá theo cùng quy tắc sửa
  nhãn bên dưới.
* **Nhãn nháp**: đổi loại, dời ◀ ▶ (bảng đi theo nhãn), sửa giá, *Xoá*.
* **Thêm nhãn vào nến này**: gán tay thêm loại khác trên cùng nến (nguồn `human`).

Bảng bám theo nến khi kéo/zoom chart; tooltip tạm tắt khi bảng mở. Đóng bằng
<kbd>Esc</kbd>, nút ×, hoặc click một nến trống (click này **chỉ đóng bảng**,
không gán nhãn). Bấm <kbd>A</kbd>/<kbd>X</kbd>/<kbd>N</kbd>/<kbd>P</kbd> cũng
đóng bảng rồi duyệt như thường. Mọi thao tác trong bảng hoàn tác được bằng
<kbd>Ctrl+Z</kbd>.

### Sửa nhãn sau khi auto label, và hoàn tác

Ngoài bảng trên chart, bảng *Nhãn trong bộ đang soạn* cũng cho sửa trực tiếp
từng nhãn — kể cả nhãn vừa chấp nhận từ đề xuất:

* **Loại** — chọn loại khác trong ô.
* **Nến** — nút ◀ ▶ dời sang nến trước/sau; hoặc chọn nhãn rồi bấm <kbd>[</kbd>
  <kbd>]</kbd>. Nhãn vừa chấp nhận tự được chọn, nên có thể dời ngay.
* **Giá** — gõ trực tiếp. Khi dời nến hoặc đổi loại: đỉnh/đáy tự lấy high/low
  của nến mới; BOS/CHoCH giữ mức giá cũ (mức bị phá không đổi theo nến) trừ khi
  đổi chiều lên/xuống.
* **Xoá** — nút *xoá* hoặc <kbd>Delete</kbd> với nhãn đang chọn.

Nhãn auto bị sửa chuyển nguồn thành `auto_edited` (*auto · … (người đã sửa)*),
vẫn giữ tên thuật toán gốc; bảng đề xuất ghi *đã chấp nhận rồi sửa*. Trang Đánh
giá đếm riêng loại này và cảnh báo nhẹ hơn nhãn chấp nhận nguyên, vì vị trí đã
do người quyết nhưng vẫn xuất phát từ gợi ý của thuật toán.

**Hoàn tác** (nút *Hoàn tác* trên đầu trang, nút *↶ Hoàn tác* trong thanh duyệt,
<kbd>Ctrl+Z</kbd> hoặc <kbd>Backspace</kbd>) lùi từng bước cho **mọi** thao tác:
click tay, xoá, sửa loại/nến/giá/ghi chú, chấp nhận, bỏ, chấp nhận/bỏ hàng loạt.
Mỗi bước chụp cả bộ nháp lẫn trạng thái duyệt đề xuất. Lịch sử (40 bước gần
nhất) được giữ cùng nháp nên **tải lại trang vẫn hoàn tác được**. Đề xuất lại
một phiên mới thì các bước cũ chỉ khôi phục bộ nháp, không khôi phục trạng thái
duyệt của phiên cũ.

Quy tắc:

* **Đề xuất không bao giờ tự vào kho nhãn.** `suggest` chỉ đọc; chỉ đề xuất đã
  chấp nhận mới vào nháp, và nháp chỉ vào kho khi bấm Lưu.
* Thuật toán chạy trên **toàn bộ dataset** rồi mới lọc theo khoảng: nhãn là đánh
  giá hồi cứu, và pivot sát mép phải khoảng vẫn đủ nến bên phải để xác nhận.
  Khoảng chạm các nến cuối dataset thì có cảnh báo — thuật toán có thể chưa kịp
  xác nhận ở đó.
* Giá của nhãn chấp nhận là **giá sự kiện của thuật toán** (BOS/CHoCH = mức bị
  phá), không phải high/low của nến như khi click tay.
* Đề xuất trùng nhãn bạn đã gán tay (cùng loại + cùng nến) hiện là *đã có trong
  nháp*, không bị thêm lần hai.

### Nguồn gốc nhãn và cảnh báo "tự chứng minh"

Mỗi nhãn lưu `source` (`human` | `auto_accepted`), `source_algorithm` và
`source_detail` (tên + phiên bản + tham số thuật toán đã đề xuất). Trường này đi
theo nhãn qua lưu, ghi đè, xuất/nhập CSV; tải bộ nhãn ở tab trang chính cũng giữ
nguyên, để không có đường nào biến nhãn auto thành "người gán".

Tài liệu nhóm (mục 5.8) yêu cầu nhãn tham chiếu **độc lập** với thuật toán được
chấm. Nhãn auto đã duyệt vẫn mang dấu của thuật toán đề xuất: người duyệt có xu
hướng chấp nhận cái được gợi ý. Vì vậy khi chấm một thuật toán trên bộ nhãn có
nhãn do **chính thuật toán đó** đề xuất:

* trang **Đánh giá** hiện khung cảnh báo và dòng *Nguồn nhãn: … người gán ·
  … auto từ …*; danh sách bộ nhãn ghi *(N từ auto label)*;
* kết quả API có `nguon_nhan` và `canh_bao_nguon_nhan` (cả `/api/evaluations` lẫn
  `/api/evaluate` của tab trang chính).

Công cụ **không chặn** việc chấm — chỉ nói rõ con số bị thiên lệch. So sánh công
bằng thì dùng bộ nhãn người tự gán, hoặc bộ auto từ một thuật toán **khác**
thuật toán đang chấm.

## Giữ công sức gán nhãn

### Nháp tự lưu trong trình duyệt

Bộ đang soạn được ghi vào `localStorage` **theo từng dataset**
(`msl.labeldraft.v1.<dataset_id>`, xem `frontend/js/labeldraft.js`):

* Tải lại trang, đóng/mở tab, chuyển qua lại giữa Thử nghiệm và Gán nhãn đều
  giữ nguyên nháp. Hai trang dùng chung một nháp cho cùng dataset.
* Mở lại app sẽ quay về **dataset đang làm dở**, nếu không nháp khôi phục xong
  lại nằm ở dataset người dùng không nhìn thấy.
* Nháp của XAUUSD H1 **không** bao giờ hiện trên EURUSD hay M15: `bar_index`
  chỉ có nghĩa trong đúng dataset sinh ra nó.
* Rời trang khi còn nhãn chưa lưu thì trình duyệt hỏi lại.

Nháp **không phải** nơi lưu chính thức. Nó nằm trong máy người dùng, người khác
không thấy, và mất khi xoá site data. Chỉ **Lưu** / **Cập nhật** mới ghi vào
`data/lab.sqlite`. Dòng trạng thái trên đầu tab luôn nói rõ nhãn đã vào kho hay
chưa; nếu trình duyệt chặn `localStorage`, dòng này cảnh báo đừng tải lại trang
trước khi lưu.

### Ghi đè bộ đã lưu

**Cập nhật bộ đang mở** (`PUT /api/label-sets/{id}`) ghi đè nội dung và **tăng
`revision`**; `dataset_id` không bao giờ đổi.

Nếu bộ nhãn đó đã được dùng trong **đánh giá đã lưu**, backend chặn lại và đòi
`confirm_overwrite`. Lý do: kết quả đánh giá cũ gắn với bản nhãn TRƯỚC đó và
không tự tính lại. Mỗi đánh giá lưu `label_set_revision` để về sau còn biết nó
được chấm trên bản nhãn nào. Muốn giữ cả hai bản thì dùng **Lưu thành bộ mới**.

### Xuất / nhập CSV

* **Xuất CSV** (`GET /api/label-sets/{id}/export.csv`) — cột
  `structure_type,bar_index,price,notes,source,source_algorithm,source_detail`, kèm các dòng `#` ghi `label_set_id`,
  `revision`, người gán, dataset và `dataset_checksum`.
* **Nhập CSV** (`POST /api/label-sets/parse-csv`) — đọc vào **bộ nháp**, không
  tự ghi vào kho; vẫn phải bấm Lưu. Nhờ vậy chỉ có một đường ghi dữ liệu.
* File xuất nạp lại được nguyên vẹn (các dòng `#` bị bỏ qua). Nếu
  `dataset_checksum` trong file khác dataset đang chọn, công cụ cảnh báo; nếu
  `bar_index` vượt số nến của dataset thì từ chối hẳn.

Kiểm tra khi lưu/ghi đè/nhập (`_clean_labels` trong `backend/app/service.py`):
loại nhãn phải thuộc `LABEL_TYPES`, `0 ≤ bar_index < row_count`, nhãn trùng
(cùng loại + cùng nến) bị gộp và báo cảnh báo, danh sách được sắp theo nến.

## Rubric tối thiểu (người gán phải ghi)

Đánh trên chart, nến đã đóng:

* `SWING_HIGH` / `SWING_LOW` — đỉnh/đáy mắt thường theo cùng ý tưởng cửa sổ
  pivot (không nhìn tương lai khi gán cho thí nghiệm online; nếu gán hồi cứu
  phải ghi rõ trong rubric).
* `SWING_HIGH_L2` / `SWING_LOW_L2` — đỉnh/đáy cấp 2 (lọc trên chuỗi pivot cấp 1),
  nếu thí nghiệm dùng `swing_hierarchy`.
* `BOS_UP` / `BOS_DOWN` — phá cấu trúc chính theo close.
* `BOS_INTERNAL_*` — phá đỉnh/đáy hồi, chưa phá mức chính.
* `CHOCH_*` — đổi hướng, phá HL/LH đang định nghĩa bias.

## Quy tắc ghép (`core/labels.py`)

* Cùng `structure_type` (không gộp BOS nội bộ với BOS chính).
* `|Δ nến| ≤ time_tolerance_bars` (mặc định 1).
* `|Δ giá| ≤ price_tolerance` (mặc định 0).
* Ghép tham lam 1-1, ưu tiên Δnến rồi Δgiá.

Precision = TP/(TP+FP), Recall = TP/(TP+FN). Bộ nhãn trống → không ra số.

Matcher này là **`greedy_label_order_v1`**: mỗi nhãn (theo thứ tự nến) lấy sự kiện
chưa dùng có |Δnến| nhỏ nhất. Có thể bỏ lỡ phép gán tốt hơn khi nhiều sự kiện
nằm gần nhau. Trang **Đánh giá thuật toán** (`/danh-gia`) dùng protocol riêng,
mặc định `min_cost_v1`, F1, P90 và khoảng gán nhãn đầy đủ — xem
[`danh_gia_thuat_toan.md`](danh_gia_thuat_toan.md).

## API

* `POST /api/label-sets` — tạo bộ (dataset_id, annotator, version, rubric_vi, labels[])
* `GET /api/label-sets?dataset_id=` — danh sách, có `revision` và `n_labels`
* `GET /api/label-sets/{id}` — chi tiết, kèm `used_by_evaluations`
* `PUT /api/label-sets/{id}` — ghi đè, tăng `revision`; cần `confirm_overwrite`
  nếu bộ đã được dùng trong đánh giá đã lưu
* `GET /api/label-sets/{id}/export.csv` — xuất CSV
* `POST /api/label-sets/parse-csv` — `{dataset_id, csv_text}` → nhãn cho nháp
  (KHÔNG tự lưu)
* `GET /api/auto-label/algorithms` — thuật toán đề xuất được nhãn + `label_types`
* `POST /api/auto-label/suggest` — `{dataset_id, algorithm, params, start_index,
  end_index, types}` → `suggestions[]` (KHÔNG tự lưu)
* `POST /api/evaluate` — `{run_id, label_set_id, time_tolerance_bars, price_tolerance}`
