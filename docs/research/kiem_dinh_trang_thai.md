# Kiểm định bộ trạng thái thị trường (trend / range / sideway) — bản khai trước

Ngày 22/10/2026. **Bản này viết và commit TRƯỚC khi chạy.** Tiêu chí, định nghĩa và đối chứng dưới đây không đổi sau
khi xem số; nếu phải sửa (vd lỗi code), ghi lý do và giữ cả số trước / sau (sổ thử, AGENTS.md §6.3).

* Đối tượng: lớp nhận diện **trạng thái v2** của `ict_structure` 0.9.1, tham số mặc định (đặc tả
  [`thuat_toan_nhan_dien.md`](../algorithms/thuat_toan_nhan_dien.md) §5c) — đúng cái khung trạng thái dưới chart hiển thị.
* Dữ liệu: XAUUSD M15 `ds_a5212fd37814`, EURUSD M15 `ds_a9a2a5e4cef5`, **2018-01-01 → 2024-09-01 (đoạn phát triển)**;
  đoạn kiểm tra khoá. Database chỉ đọc.
* Script: `research/kiem_dinh_trang_thai.py`; số liệu `docs/research/khao_sat/kiem_dinh_trang_thai_dev.json`.
* Căn cứ thiết kế: [`plan_tich_hop_nghien_cuu.md`](../plans/plan_tich_hop_nghien_cuu.md) §4.5–§4.6 (N1–N4, V2–V3, H4) và
  báo cáo `D:\Finance_System\reports\Tài liệu ICT và quant.md` (mốc tầm thường kiểu TCPDBench, null giữ mùa vụ).

## 1. Nhu cầu

| Nhu cầu | Câu hỏi | Tiêu chí |
|---|---|---|
| **N1 Đúng và ổn định** | Khung trạng thái có nhìn tương lai, có nhấp nháy không? | C1, C2 |
| **N2 Khớp cấu trúc nhìn lại** | Trạng thái ở nến t có khớp cái người thấy khi nhìn lại 4 giờ trước và sau không? | C3–C6 |
| **N3 Khác nhiễu** | Trạng thái mô tả cấu trúc thật hay chỉ hình dạng mà random walk cũng tạo ra? | C7 |
| **N4 Có ích cho router** | Trend → giá đi tiếp? Range → giá giữ trong hộp? | C8, C9 |

N1 + N2 = nhu cầu **hiển thị** (khung chart mô tả đúng). N3 + N4 = nhu cầu dùng trạng thái làm **regime cho chiến lược**
(AI Trading Copilot: Trend Pullback / Range Mean Reversion / No Trade).

## 2. Tham chiếu nhìn lại (nhãn — nhìn tương lai có chủ ý, chỉ để chấm)

Cửa sổ tâm `[t − 16, t + 16]` (4 giờ mỗi bên), `A` = ATR Wilder 14 tại t:
`N = C[t+16] − C[t−16]`, `e = |N| / Σ|ΔC|` trong cửa sổ, `R = max H − min L` trong cửa sổ.

* **lên**: `N ≥ 2A` và `e ≥ 0,25`; **xuống**: `N ≤ −2A` và `e ≥ 0,25`;
* **range**: `R ≤ 4A` và `|N| < A`;
* còn lại: **nhiễu**. Cửa sổ vắt khoảng trống > 2 giờ hoặc thiếu ATR → không chấm.

> **Sửa trước khi chạy** (22/10/2026, chưa có số nào): bản đầu ghi «> 1 giờ» — sẽ loại mọi cửa sổ vắt giờ nghỉ hằng ngày
> của XAUUSD (khoảng cách 75 phút), tức khoảng 1/3 số nến, trái với quy ước của lõi (mức giữ qua nghỉ phiên). Đổi thành
> «> 2 giờ»: chỉ loại cuối tuần, ngày lễ và chỗ thiếu dữ liệu. Áp dụng như nhau cho mọi thước có cửa sổ (B_ngay_tho,
> tiếp diễn 16 nến).

Do lab chọn — **không phải nhãn người**. Dùng thay bộ nhãn D8 khi chưa có; khi có nhãn người thì chấm lại N2 trên nhãn.

## 3. Đối chứng

* **B_ngay_tho** — cùng định nghĩa §2 nhưng chỉ nhìn quá khứ, cửa sổ `[t − 32, t]` (8 giờ, đúng cửa sổ ER của v2): mốc
  «đơn giản nhất làm cùng việc» (bài học TCPDBench: mốc tầm thường có thể ngang thuật toán).
* **B_adx** — ADX(14) ≥ 25 → trend theo chiều +DI / −DI; còn lại không trend.
* **Null dịch vòng** — chuỗi trạng thái v2 dịch vòng k ∈ {5, 10, 20} tuần (k × 460 nến): giữ tỷ lệ và độ dài đoạn, phá
  căn chỉnh thời gian.
* **Chuỗi giả** (cho N3, C8) — random walk giữ mùa vụ: bước close `r_t = σ_giờ(t) · s_ngày(t) · z_t`, `z` ~ Student-t 4
  chuẩn hoá phương sai 1; `σ_giờ` = trung vị |ΔC| theo giờ New York (trên dev), `s_ngày` = biến động ngày thật / trung vị
  (giữ cụm biến động giữa các ngày); open = close trước; râu nến theo tỷ lệ râu / biên độ của nến thật cùng vị trí; cùng
  mốc thời gian và lịch phiên → v2 chạy như trên dữ liệu thật. 3 seed.

## 4. Thước

* **κ3**: Cohen κ trên 3 lớp (lên / xuống / không trend = range + nhiễu), mọi nến chấm được; kèm ma trận 4 × 4.
* **Recall trend đúng chiều**: trong nến tham chiếu lên (xuống), tỷ lệ v2 gọi trend lên (xuống).
* **Sai chiều**: trong nến v2 gọi trend, tỷ lệ tham chiếu là trend **ngược** chiều.
* **Trễ vào trend**: mỗi đoạn tham chiếu lên / xuống liên tiếp ≥ 8 nến — số nến từ đầu đoạn tới nến đầu tiên v2 gọi trend
  cùng chiều (không gọi → cả đoạn), chia độ dài đoạn = «phần đoạn bị mất»; trung vị.
* **Đổi / 100 nến**, **tỷ lệ đoạn < 4 nến** (đoạn cắt ở nến chưa có trạng thái, như khảo sát v2).
* **Tiếp diễn 16 nến**: trong nến v2 gọi trend, tỷ lệ `sign(C[t+16] − C[t])` = chiều trend; CI 95% bootstrap khối tuần
  (1 000 lượt).
* Mọi số báo cho cả hai mã; chuỗi giả báo trung bình 3 seed.

## 5. Tiêu chí đạt (chốt trước, do lab chọn)

| # | Nhu cầu | Tiêu chí | Ngưỡng đạt |
|---|---|---|---|
| C1 | N1 | Nhân quả: chạy cắt ở 5 điểm = chạy trọn rồi lọc (`nd_trang_thai`, `nd_do_manh`, `nd_nen`) | 0 nến lệch |
| C2 | N1 | Ổn định hiển thị | đổi ≤ 10 / 100 nến **và** đoạn < 4 nến ≤ 25% số đoạn |
| C3 | N2 | κ3 với tham chiếu nhìn lại | ≥ 0,40 ở cả hai mã |
| C4 | N2 | Hơn mốc | κ3 − κ3(B_ngay_tho) ≥ +0,05 **và** κ3 − κ3(null dịch vòng, TB 3 k) ≥ +0,30 |
| C5 | N2 | Đúng chiều | sai chiều ≤ 5% **và** recall trend đúng chiều ≥ 70% |
| C6 | N2 | Trễ vào trend | trung vị phần đoạn bị mất ≤ 35% |
| C7 | N3 | Khác nhiễu | tỷ lệ thời gian trend thật − chuỗi giả ≥ +5 điểm % **và** độ dài trung vị đoạn trend thật ≥ 1,2 × chuỗi giả |
| C8 | N4 | Trend → đi tiếp | tiếp diễn 16 nến ≥ 53%, CI không chứa 50% |
| C9 | N4 | Range → giữ giá | range giữ giá hơn hộp bất kỳ (CI không chứa 0) — **lấy từ** [`khao_sat/trang_thai_v2_dev.json`](khao_sat/trang_thai_v2_dev.json) (đã đo 22/10/2026, không đo lại) |

Một nhu cầu **đáp ứng** khi mọi tiêu chí của nó đạt ở cả hai mã. B_adx chỉ để tham khảo (không vào tiêu chí).

## 6. Kết quả

*(điền sau khi chạy — xem mục này ở bản commit sau)*
