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

## 6. Kết quả (chạy 22/10/2026, `kiem-dinh-trang-thai-v1.0`, 27 phút)

Số liệu đầy đủ: [`khao_sat/kiem_dinh_trang_thai_dev.json`](khao_sat/kiem_dinh_trang_thai_dev.json). Sổ thử: một lần chạy
hỏng giữa chừng vì lỗi script (chuỗi giả dùng số numpy, lõi nhận `float` Python — đã sửa, không đổi tiêu chí); số in ra
trước khi hỏng (κ3 XAUUSD thật) trùng lần chạy đầy đủ.

| # | Tiêu chí | XAUUSD | EURUSD | Đạt |
|---|---|---|---|---|
| C1 | Nhân quả (5 điểm cắt, 16 000 nến cuối dev; thuộc tính của code nên đo một mã) | 0 nến lệch | — | **đạt** |
| C2 | Đổi / 100 nến · đoạn < 4 nến | 5,53 · 17,7% | 5,78 · 18,5% | **đạt** |
| C3 | κ3 với tham chiếu nhìn lại | 0,135 | 0,125 | không (≥ 0,40) |
| C4 | κ3 − ngây thơ · κ3 − null dịch vòng | −0,077 · +0,137 | −0,078 · +0,124 | không |
| C5 | Sai chiều · recall trend đúng chiều | 4,3% · 46,6% | 4,0% · 45,4% | không (recall) |
| C6 | Trung vị phần đoạn trend bị mất trước khi nhận ra | 59% | 57% | không (≤ 35%) |
| C7 | Trend thật − chuỗi giả · độ dài trung vị đoạn trend thật / giả | +3,0 điểm · 19 / 21,3 nến | +1,7 điểm · 18 / 20,7 nến | không |
| C8 | Tiếp diễn 16 nến trong trend | 47,7% [46,7; 48,8] | 48,3% [47,3; 49,3] | không (dưới 50% có ý nghĩa) |
| C9 | Range giữ giá hơn hộp bất kỳ (khảo sát v2) | −0,000 [−0,009; 0,008] | −0,001 [−0,009; 0,008] | không |

**Kết luận theo khai trước: N1 đáp ứng; N2, N3, N4 không đáp ứng** (cả hai mã).

Đọc số (mô tả, không đổi kết luận):

* **v2 gọi trend / range nhiều hơn hẳn cái nhìn lại thấy.** v2: trend 49%, range 33%, nhiễu 18% thời gian; tham chiếu: trend
  28%, range 8%, nhiễu 64%. Ở XAUUSD, 62% số nến v2 gọi trend nằm ở chỗ tham chiếu là nhiễu; 67% số nến v2 gọi range cũng vậy.
  Khi v2 đã gọi trend thì hiếm sai chiều (4%), nhưng bỏ sót hơn nửa số nến trend của tham chiếu và nhận ra muộn (mất ~58%
  đoạn).
* **Mốc đơn giản thắng.** Bộ phân loại ngây thơ (chính định nghĩa tham chiếu, chỉ nhìn 8 giờ qua) có κ3 0,21 / 0,20; ADX + DI
  0,19 / 0,19 — đều hơn v2. v2 hơn null dịch vòng (≈ 0), tức có căn chỉnh thời gian thật, nhưng ít hơn mốc tầm thường.
* **Trên chuỗi không có cấu trúc, v2 vẫn gần như y hệt.** Random walk giữ mùa vụ: v2 gọi trend 45–48% thời gian, đoạn trend còn
  dài hơn dữ liệu thật, κ3 với tham chiếu của chính chuỗi giả 0,15–0,16 (cao hơn dữ liệu thật). Trạng thái chủ yếu phản ánh
  hình dạng mà nhiễu cũng tạo ra — khớp cảnh báo «ER sát nền nhiễu» (plan tích hợp §2, H4).
* **Trạng thái không mang thông tin về sau.** Sau khi v2 gọi trend, 16 nến sau đi cùng chiều 47,7% / 48,3% — thấp hơn 50% có ý
  nghĩa (chuỗi giả: 50%); range không giữ giá hơn hộp bất kỳ.

**Khám phá — ngoài khai trước** (`--kham-pha`,
[`khao_sat/kiem_dinh_trang_thai_kham_pha_dev.json`](khao_sat/kiem_dinh_trang_thai_kham_pha_dev.json)): v2 có khớp hơn ở thang
dài không (vì v2 giữ trend tới CHoCH)? Nửa cửa sổ tham chiếu W = 32 (±8 giờ): κ3 0,16 / 0,17, recall 65%, sai chiều 0,9% —
vẫn dưới mốc ngây thơ (0,23 / 0,20). W = 64: tham chiếu chỉ còn 3–4% nến trend (ngưỡng cố định theo ATR), κ3 0,05 / 0,04. Lệch
thang không giải thích được kết quả.

**Giới hạn:** tham chiếu nhìn lại do lab chọn, không phải nhãn người — N2 phải chấm lại trên nhãn người (plan nhận diện v2 bước
5, plan tích hợp A4). N3 (chuỗi giả) và N4 (tiếp diễn, giữ giá) không phụ thuộc tham chiếu.

## 7. Chạy lại cho `ict_structure` 0.9.2 (22/10/2026, cùng script và tiêu chí, 29 phút)

0.9.2 chỉ đổi một điều: trạng thái v2 không khởi động lại chỉ báo qua nghỉ theo lịch phiên (cuối tuần, lễ) — trước đó
mỗi tuần trống ~33 nến M15 «chưa đủ nến» (đặc tả nhận diện §4 bước 1). Số liệu:
[`khao_sat/kiem_dinh_trang_thai_dev_0_9_2.json`](khao_sat/kiem_dinh_trang_thai_dev_0_9_2.json). Các nến trước đây trống
nay có trạng thái nên số nến được chấm tăng (XAUUSD 138 230 → 144 499, EURUSD 148 767 → 154 468); mốc ngây thơ / ADX + DI
không phụ thuộc thuật toán nên giữ nguyên.

| # | XAUUSD 0.9.1 → 0.9.2 | EURUSD 0.9.1 → 0.9.2 | Đạt (0.9.2) |
|---|---|---|---|
| C1 | 0 → 0 nến lệch | — | **đạt** |
| C2 | 5,53 → 5,51 / 100 nến · 17,7% → 17,1% | 5,78 → 5,71 · 18,5% → 17,8% | **đạt** |
| C3 | κ3 0,135 → 0,134 | 0,125 → 0,127 | không |
| C5 | sai chiều 4,3% → 4,3% · recall 46,6% → 46,1% | 4,0% → 4,0% · 45,4% → 45,1% | không (recall) |
| C6 | mất đoạn 59% → 54% | 57% → 55% | không |
| C7 | trend thật − giả +3,0 → +3,9 điểm | +1,7 → +1,9 điểm | không |
| C8 | tiếp diễn 47,7% → 47,7% [46,6; 48,7] | 48,3% → 48,5% [47,6; 49,5] | không |

C4 vẫn dưới mốc ngây thơ (κ3 0,21 / 0,20); C9 lấy từ khảo sát v2 như §6 (không đo lại). **Kết luận không đổi: N1 đáp ứng;
N2, N3, N4 không đáp ứng.** Sửa khởi động sau nghỉ theo lịch là sửa hiển thị (khung không còn trống đầu tuần), không phải
nguyên nhân của N2–N4.
