# Kiểm định OB theo ngữ cảnh — tìm OB mạnh, vùng giá trị (bản khai trước)

* Ngày khai: 24/10/2026. Người dùng: «không phải là tìm kiểu OB tốt nhất, mà hãy tìm được OB mạnh, vùng giá trị» — kiểm OB
  khi có ngữ cảnh (cùng chiều khung lớn, killzone, sweep và displacement mạnh trước đó), bộ lọc ít tham số, khai trước.
* Script: [`research/kiem_dinh_ob_ngu_canh.py`](../../research/kiem_dinh_ob_ngu_canh.py) (dùng lại vòng đời, vùng song
  sinh, bootstrap của [`kiem_dinh_order_block.py`](../../research/kiem_dinh_order_block.py)). Chỉ đọc database, chỉ dev
  2018-01-01 → 2024-09-01; đoạn kiểm tra khoá.
* Nối tiếp [`kiem_dinh_order_block.md`](kiem_dinh_order_block.md): OB «trần» (7 định nghĩa) không giữ giá hơn vùng song sinh
  hình học; tỷ lệ giữ giá do bề rộng / khoảng cách quyết định.

Tiêu chí chốt trước khi chạy; sửa thì ghi «Sổ sửa» kèm lý do, trước khi xem kết quả.

## 1. Câu hỏi

Có **điều kiện ngữ cảnh** nào (biết được ở nến OB có hiệu lực) mà OB thỏa điều kiện đó giữ giá **hơn hẳn vùng song sinh
cùng hình học** — tức là «vùng mạnh, có giá trị» — và điều đó **lặp lại** ở nửa dev còn lại? Đo chất lượng vùng, không
phải tín hiệu giao dịch.

## 2. Tập OB gốc

**X1** của kiểm định trước (nến cực trị trước lần close phá pivot đối xứng 10/10 gần nhất — kiểu LuxAlgo Order Blocks &
Breaker Blocks, Δ «ít tệ nhất»), với p = nến pivot bị phá, i = nến OB, c = nến phá (vùng hiệu lực từ c). Một tập gốc duy
nhất để các bộ lọc so được với nhau; X1 không đòi sweep / displacement nên các điều kiện K3, K4 thật sự lọc. (OB của lab
neo SHIFT vốn đã có sweep + displacement, đã đo ở kiểm định trước: Δ +1,8 / −1,1.)

## 3. Điều kiện ngữ cảnh (mô tả cho OB tăng; OB giảm đối xứng) — đọc ở hàng timeline / sự kiện của `ict_structure` 0.9.2 tới nến c

| # | Tên | Điều kiện | Cột / sự kiện |
|---|---|---|---|
| K1 | Cùng chiều khung lớn | thứ tự swing H4 = tăng (HH-HL) ở nến c | `htf_H4_order` = +1 |
| K2 | Killzone | nến c trong killzone London (02–05) hoặc NY AM (07–10) giờ New York | `killzone` ∈ {london, ny_am} |
| K3 | Sweep trước | có sweep thanh khoản phía bán (SSL) xác nhận trong [p, c] — nhịp tạo OB mở đầu bằng cú quét | `LIQ_SWEEP_SSL` |
| K4 | Displacement mạnh | có displacement tăng xác nhận trong (i, c] — nhịp rời OB là displacement | `DISPLACEMENT_UP` |
| K5 | Vùng giá trị (discount) | tâm vùng OB ở nửa dưới dealing range H4 ở nến c | (tâm − `htf_H4_dealing_lo`) / (hi − lo) ≤ 0,5 |
| K6 | Hợp lưu | đạt ≥ 3 trong K1–K5 | — |

Thiếu cột (khung lớn chưa đủ, dealing range chưa có) → điều kiện tính là không đạt. Không thêm ngưỡng nào ngoài mặc định
của lõi.

## 4. Thước, chuẩn, CI (như kiểm định trước, đã sửa theo code-review)

* Vòng đời §3 của kiểm định trước: chạm lần đầu trong 96 nến; **giữ giá** G = +1·ATR từ mép gần trước close vượt mép xa,
  32 nến; setup R (mô tả, chưa trừ phí).
* Chuẩn chính: 5 **vùng song sinh hình học** (cùng khoảng cách và bề rộng theo ATR, cùng giờ New York — nên K2 được khớp
  sẵn —, cùng nửa dev, ±13 tuần). Δ = G(OB thỏa Kk) − G(song sinh của chính các OB đó).
* CI 95% bootstrap khối 4 tuần theo nến chạm, rút trên khối có trong mẫu, 1 000 lần.

## 5. Chọn và xác nhận

* Đoạn A: 2018 → 2021; đoạn B: 2022-01-01 → 2024-08-31 (theo nến c).
* **Hợp lệ ở A** (mỗi Kk): cả XAUUSD và EURUSD có Δ với cận dưới CI > 0 và ≥ 200 cặp.
* **Xác nhận ở B**: mỗi Kk hợp lệ ở A được kiểm lại ở B; đạt khi cả hai mã có cận dưới CI > 0. 6 bộ lọc × 2 mã — hàng rào
  là «cả hai mã ở A» rồi «cả hai mã ở B».
* Kết luận «vùng mạnh» chỉ cho bộ lọc đạt cả A và B. Không có → «chưa tìm được ngữ cảnh làm OB mạnh hơn vùng ngẫu nhiên
  cùng hình học».

## 6. Đọc thêm (mô tả, không phải tiêu chí)

* Δ giữa OB thỏa và OB không thỏa Kk (cùng tập X1) — điều kiện có làm OB khác đi không.
* K1, K5: thêm **song sinh khớp ngữ cảnh** (song sinh chỉ lấy ở nến mà thứ tự H4 cùng chiều / vùng song sinh nằm ở
  discount) — giá trị đến từ OB hay chỉ từ ngữ cảnh.
* Bảng theo số điều kiện đạt (0 … 5).

## Sổ sửa

(chưa có)

## 7. Kết quả (chạy 24/10/2026, `kiem-dinh-ob-ngu-canh-v1.0`, 1 phút)

Số liệu đầy đủ: [`khao_sat/kiem_dinh_ob_ngu_canh_dev.json`](khao_sat/kiem_dinh_ob_ngu_canh_dev.json). Δ = G(OB thỏa) −
G(song sinh hình học), điểm %, CI 95% khối 4 tuần. «Thỏa» = tỷ lệ OB X1 thỏa điều kiện.

| # | Điều kiện | A · XAUUSD | A · EURUSD | B · XAUUSD | B · EURUSD | Hợp lệ A |
|---|---|---|---|---|---|---|
| K1 | Cùng chiều H4 (thỏa ~28%) | +1,2 [−4,3; 6,8] | **+4,4 [0,5; 8,1]** | +1,5 [−4,6; 8,2] | +1,7 [−4,4; 8,1] | không |
| K2 | Killzone London / NY AM (~42%) | −1,3 [−5,7; 2,8] | +3,1 [−1,0; 6,9] | +1,3 [−4,5; 6,8] | −2,7 [−8,9; 3,4] | không |
| K3 | Sweep phía ngược trước đó (~43%) | +1,8 [−2,6; 6,0] | +1,8 [−2,3; 5,9] | −0,4 [−6,6; 5,7] | −0,3 [−5,3; 5,0] | không |
| K4 | Displacement rời OB (~68%) | +2,3 [−1,4; 6,1] | +2,6 [−0,3; 5,4] | +0,8 [−3,6; 5,2] | −0,1 [−4,6; 4,1] | không |
| K5 | Vùng giá trị: discount / premium H4 (~53%) | **+4,7 [0,5; 8,6]** | +0,9 [−2,1; 3,8] | +2,0 [−3,4; 6,6] | +1,6 [−3,0; 5,8] | không |
| K6 | Hợp lưu ≥ 3/5 (~46%) | +2,2 [−2,3; 6,6] | **+4,8 [0,8; 8,5]** | +3,7 [−1,7; 9,1] | +0,7 [−5,1; 6,6] | không |

**Kết luận theo khai trước: không bộ lọc nào hợp lệ ở A (cần cả hai mã) → «chưa tìm được ngữ cảnh làm OB mạnh hơn vùng
ngẫu nhiên cùng hình học».**

Đọc số (mô tả, không đổi kết luận):

* **Ba ngữ cảnh dương ở cả bốn ô** (2 mã × 2 đoạn): K1 cùng chiều H4, K5 discount / premium, K6 hợp lưu — Δ +0,7 … +4,8
  điểm, mỗi ô chỉ một lần CI loại 0. Một bộ lọc vô dụng ra dương cả 4 ô với xác suất ~1/16; nhưng K6 chứa K1, K5 nên ba
  bộ lọc không phải ba bằng chứng độc lập. Đây là **gợi ý một hiệu ứng nhỏ (vài điểm %)**, chưa phải kết quả — muốn kết
  luận cần một phép thử mới, khai trước, gộp hai mã (một phép thử, đủ lực).
* **K5 không đến từ «nằm ở discount» nói chung**: so với song sinh cũng nằm ở discount, Δ gần như giữ nguyên (A XAUUSD +4,1
  [0,7; 8,0]). K1 tương tự ở EURUSD (+4,6 so với song sinh cùng chiều H4).
* **Sweep (K3) và displacement (K4) không làm OB mạnh hơn rõ rệt** — dương nhỏ ở A, về 0 ở B. Khớp kiểm định trước: OB
  neo SHIFT (vốn có sweep + displacement) cũng không hơn song sinh.
* **Theo số điều kiện đạt (0 … 5): không có xu hướng tăng đều** — vd XAUUSD đoạn A, OB không đạt điều kiện nào giữ 68%,
  đạt 5 giữ 65%.
* **Setup R (2R, chưa trừ phí) vẫn quanh 0 hoặc âm** với mọi bộ lọc ở B (−0,17 … −0,00 R); có ô dương ở A (K6 EURUSD
  +0,11 R) không lặp lại ở B.
* Kiểm chéo «tất cả X1»: Δ lệch tới ~1 điểm so với kiểm định trước vì chuỗi ngẫu nhiên chọn song sinh khác (vùng thật
  trùng) — cỡ nhiễu của việc bốc song sinh, nằm trong CI.

**Giới hạn:** một tập OB gốc (X1); điều kiện nhị phân theo mặc định của lõi; chỉ M15 XAUUSD / EURUSD, đoạn dev; chưa
khớp song sinh theo chế độ biến động ngày.
