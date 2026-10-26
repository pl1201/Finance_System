# Plan: trợ lý tổng hợp (LLM) trên trang Live MT5 và trang Thử nghiệm

**Trạng thái: đang làm (25/10/2026).** Người dùng: «tích hợp thêm một con LLM tổng hợp thông tin từ chart», chọn
«khung chat tổng hợp, dùng OpenRouter model DeepSeek Flash» — tức đồng ý gửi trạng thái thuật toán (giá, cấu trúc; không tài
khoản, không lệnh) qua OpenRouter tới DeepSeek.

## 1. Vai trò — đọc, không nhận diện

* Thuật toán (`ict_structure`) vẫn tất định, nhân quả, đo được. LLM **chỉ đọc** output của nó ở nến cuối và nói lại bằng
  tiếng Việt: gom nhiều lớp (khung lớn, cấu trúc, order flow, thanh khoản, khoảng giá / xác suất kèm điểm thật) thành vài
  câu, trả lời câu hỏi.
* Không vào lõi: không đổi sự kiện, timeline, dự báo, điểm forward; không phải đầu vào của thuật toán nào.
* Không khuyên giao dịch: không mua / bán, không điểm vào, SL, TP, khối lượng. Hỏi tín hiệu → nói rõ đây là công cụ nghiên cứu.

## 2. Mô hình, nhà cung cấp

* OpenRouter `POST https://openrouter.ai/api/v1/chat/completions` (chuẩn OpenAI), gọi bằng `httpx` (đã có trong
  requirements) từ backend. Khoá: biến môi trường `OPENROUTER_API_KEY` — lab không lưu khoá, không ghi khoá vào nhật ký.
* Mô hình mặc định `deepseek/deepseek-v4.1-flash-1017` (bản DeepSeek đang phục vụ dưới tên `deepseek-flash`; ghim phiên
  bản để câu trả lời không đổi theo cập nhật ngầm); đổi bằng `MSL_LLM_MODEL`. Giá OpenRouter 25/10/2026: $0,15 vào /
  $0,60 ra mỗi 1M token ($0,30 / $1,20 giờ cao điểm DeepSeek), cache đọc $0,003.
* `reasoning: {effort: "low", exclude: true}` — suy nghĩ ít, không trả phần suy nghĩ (vẫn tính tiền như token ra).

## 3. Đầu vào — bản tóm gọn ở nến cuối

`core/algorithms/ict_structure/digest.py` (hàm thuần, không đổi output của thuật toán):
* thông tin nến cuối (mã, khung, chỉ số, giờ mở UTC / New York, giờ đóng UTC, OHLC);
* các mục `SECTIONS` của `pending_state` (mục mới phải được xếp vào `SECTIONS` hoặc `IGNORED` — test kiểm), đã lược
  trường nội bộ (id, nguồn, danh sách chờ…), số làm tròn theo số chữ số giá của chart (giao diện gửi kèm);
* 30 sự kiện đã xác nhận gần nhất, mỗi sự kiện một dòng (bỏ loại «nguyên liệu» quá dày: STH/STL, FVG chạm / lấp, khoảng
  trống, nến khung lớn thiếu), kèm nghĩa của từng loại / mã lý do lấy từ `core/vocab`;
* bảng giải nghĩa các mục (cố định — phần đầu prompt giống nhau giữa các lần gọi nên được cache) và câu lệnh tổng hợp
  theo mục — cả hai thuộc thuật toán; backend chỉ giữ quy tắc chung.

## 4. Rào chắn và nhật ký

* Prompt hệ thống: chỉ dùng dữ liệu được đưa, giữ nguyên số, nói «không có trong dữ liệu» khi thiếu, xác suất là của
  thuật toán kèm điểm thật nếu có, không khuyên lệnh.
* **Kiểm số liệu** sau mỗi câu trả lời: mọi số có phần thập phân hoặc ≥ 100, và mọi phần trăm, phải có trong dữ liệu đầu
  vào (sai số làm tròn) — số lạ được gắn cờ trên giao diện.
* **Nhật ký** `llm_log` trong `live.sqlite` (chỉ ghi thêm): luồng, nến, chế độ, mô hình (OpenRouter trả về), câu hỏi, câu
  trả lời, token, token trúng cache, chi phí, số bị gắn cờ, cắt ngắn, sha256 của dữ liệu đầu vào; dữ liệu gửi đi lưu một
  lần theo sha256 ở `llm_data` (các câu hỏi cùng nến dùng chung).

## 5. Giao diện (trang Live MT5, trang Thử nghiệm)

Khung chat bên phải (bật / tắt, nhớ theo trình duyệt): nút «Tổng hợp nến cuối», ô hỏi, lịch sử cuộc trò chuyện, mỗi câu
trả lời ghi nến dữ liệu, token, chi phí, cảnh báo số lạ; nút «Cuộc mới». Chỉ gọi khi người dùng bấm — không tự gọi mỗi nến.

Có ở **cả hai trang** (mảnh `partials/chat-panel.html` + `js/lib/chat_panel.js` dùng chung, người dùng yêu cầu 25/10/2026):
* **Live MT5** — nguồn = luồng đang mở, dữ liệu ở nến cuối của luồng;
* **Thử nghiệm** — nguồn = phiên Replay, dữ liệu tại con trỏ (thuật toán chỉ mới thấy nến tới đó; hỏi khi đang phát thì
  dừng phát trước). Chế độ «Toàn lịch sử» không có thực thể thuật toán tại một nến → khung chat nhắc chuyển sang Replay /
  «Replay từ đây». Thuật toán chưa có hook `llm_context` (hiện chỉ `ict_structure` có) → báo chưa hỗ trợ.
Nhật ký ghi nguồn (`live` / `replay`), id và nguồn gốc (`nguon_info`: thuật toán, phiên bản, tham số / dataset —
phiên replay chỉ sống trong bộ nhớ nên phải ghi kèm để lần lại được).

## 6. Kiểm thử

* Bản tóm gọn: tất định, đủ mục, không có trường nội bộ, cỡ vừa phải (dữ liệu tổng hợp + luồng thật).
* Kiểm số liệu: tính tay (giá, phần trăm, giờ / ngày bỏ qua).
* Dịch vụ: OpenRouter giả (`httpx.MockTransport`) — thân request (mô hình, reasoning, thứ tự tin nhắn), thiếu khoá, nội dung
  rỗng thử lại một lần, lỗi OpenRouter, nhật ký chỉ ghi thêm, khoá không xuất hiện trong nhật ký.
* Trình duyệt thật với OpenRouter giả lập (script trong thư mục tạm); gọi thật khi người dùng đặt khoá.

## 7. Thứ tự (mỗi khối: simplify → code-review → chạy thật → commit + push `rieng`)

| Khối | Việc | Trạng thái |
|---|---|---|
| T1 | Plan + AGENTS.md; bản tóm gọn + kiểm số liệu + dịch vụ + route + nhật ký; khung chat | đang làm |
| T2 | Bộ kiểm ~30 tình huống (đúng số, không bịa, không khuyên lệnh), chi phí đo thật — cần khoá | |
