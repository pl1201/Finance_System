# Plan giao diện v3 — gọn, chuyên nghiệp, dễ dùng

Bắt đầu 26/10/2026, theo yêu cầu người dùng: «update giao diện trông gọn hơn, chuyên nghiệp hơn, dễ dùng».

## 1. Hiện trạng trước khi sửa (ảnh khảo sát trên bản sao DB, 1600×1000 và 1366×768)

- **Cột trái trang Thử nghiệm dài 3 264 px (3,6 màn hình).**
  - Gồm 90 ô nhập và 49 ô tick.
  - Có một đoạn chú giải khoảng 60 dòng chữ.
  - Có thanh cuộn ngang; ô «Đến ngày» bị cắt.
  - 4 nút quản lý dữ liệu (ít dùng) chiếm chỗ ngay đầu cột.
- **Lớp hiển thị xếp 2 cột, nên tên lớp gãy thành 3 dòng.**
- **Chart quá thấp trên laptop 1366×768.** Vùng giá còn khoảng 250 px, phần còn lại bị bảng dưới, khung trạng thái và các dòng chú giải trên chart chiếm.
- **Bốn trang mỗi trang một bố cục.** Thanh trên có dòng phụ đề dài.

## 2. Quyết định (người dùng chọn 26/10/2026)

| Câu hỏi | Chọn |
|---|---|
| Phạm vi | Làm trang Thử nghiệm trước, sau đó áp cùng hệ thống cho Gán nhãn, Đánh giá, Live MT5. Mỗi phần một commit. |
| Cột trái | 3 mục gập (Dữ liệu / Thuật toán / Lớp hiển thị), có tóm tắt trên tiêu đề khi gập. Nút «Chạy thử» ghim ở đáy. Ẩn được cả cột. |
| Lớp hiển thị | Một cột: ô màu, tên, công tắc, dấu ⓘ. Nút «Chú giải» mở bảng có cấu trúc thay đoạn chữ dài. |
| Theme | Giữ nền tối, tinh chỉnh khoảng cách, cỡ chữ, nút, ô nhập. |

## 3. Phần 1 — trang Thử nghiệm (đã làm 26/10/2026)

### Thanh trên
- Gọn còn 46 px, có logo SVG.
- Phụ đề dài chuyển vào tooltip.
- Mục đang xem có `aria-current`.

### Cột cấu hình
- **Mục gập.** Mục là `<details data-remember>` (`lib/ui.js`), trạng thái mở / gập nhớ theo trình duyệt. Tóm tắt trên tiêu đề do `pages/lab/sidebar.js` ghi, ví dụ:
  - «XAUUSD M15 · 02/01/2023 → 31/03/2023 · ~5.761 / 189.073 nến», ghi rõ khi khoảng bị rút gọn;
  - «n tham số đã đổi», không đếm ô đang ẩn theo `show_if`;
  - «7 / 27 lớp đang bật».
- **Dữ liệu.**
  - Menu «＋ Thêm dữ liệu» gom 4 nút cũ, giữ nguyên ID.
  - Khung thời gian là thanh phân đoạn một hàng.
  - Ô «Từ / Đến» nằm cùng hàng với nhãn, nên không tràn cột.
- **Thuật toán.**
  - Ô số / chữ hiện một hàng: nhãn trái, ô phải (class `param-row`).
  - Nút «Mặc định» chỉ dựng lại form tham số.
- **Lớp hiển thị.**
  - Một cột với công tắc (CSS trên `.layers .check`, dùng chung với trang Live).
  - Dấu ⓘ hiện khi ô có câu giải thích.
  - «Chú giải» là `<dialog>` dựng bằng `MSL.layerToggles.legendHtml` từ các ô lớp đang hiện: tên, bật / tắt và câu giải thích lấy từ `title`, nên chỉ có một nguồn nội dung. Đoạn `layerHints` của plugin nằm trong mục «Ghi chú lớp của thuật toán».
- **Chân cột.**
  - Ô «Lưu vào lịch sử» và nút «▶ Chạy thử» luôn thấy.
  - Ctrl+Enter = Chạy thử, trừ khi đang gõ ở ô nhiều dòng hoặc khung chat.

### Thanh công cụ chart
- Nút ẩn / hiện cột cấu hình.
- Dòng ngữ cảnh «XAUUSD M15 · thuật toán · n tham số đã đổi», vẫn thấy khi cột đang ẩn.
- Menu «Xuất ▾» (CSV sự kiện, ảnh PNG).

### Bảng dưới
- Màn hình thấp hơn 860 px thì thu gọn sẵn (`bottomPanel` có `collapsedByDefault`, không ghi thành lựa chọn).
- Bấm một tab là mở lại; lựa chọn của người dùng được nhớ.

### Khung chung
- Token: `--ctl-h`, `--focus`, `--shadow-pop`, `--radius-sm`, `--bg-hover`.
- Viền focus cho bàn phím.
- Nút `btn-ghost` / `btn-xs` / `btn-icon-sm`.
- Menu thả `.menu`.
- `MSL.dom.load/save`: đọc / ghi localStorage an toàn.

### Kết quả
- Cột trái dài 1 970 px khi có ICT (trước 3 264 px). Không còn cuộn ngang.
- Ở 1366×768: chart rộng 1066 px, cao 456 px (gồm khung trạng thái). Vùng giá khoảng 400 px, trước khoảng 250 px.
- Kiểm trên web thật, bản sao DB: menu, chú giải, ẩn cột, gập mục, «Mặc định», Ctrl+Enter, Space trong replay. Không có lỗi console.

## 4. Phần 2 — còn làm (chờ người dùng xem ảnh phần 1)

- **Gán nhãn.**
  - Thanh nút 7 nút gom lại: nút chính + menu.
  - Cột phải chuyển sang mục gập.
  - Dòng phím tắt chuyển vào nút «Phím tắt».
- **Đánh giá.**
  - Form vào một thẻ.
  - Trạng thái trống có hướng dẫn.
  - Bảng không bị cắt.
- **Live MT5.** Cột trái theo cùng cấu trúc mục gập; nút Tạo luồng ghim.
- **Chung.**
  - Thanh trên giống nhau ở 4 trang.
  - Ba modal cũ (`.modal[hidden]`) chuyển sang `<dialog>` để có Esc và bấm nền đóng.
  - Gom các bản try/catch localStorage còn lại về `MSL.dom.load/save`.
