# Kiểm định các kiểu order block — bản khai trước

* Ngày khai: 24/10/2026. Người dùng hỏi: «thử các order block rồi chọn cho tôi setup order block tốt nhất».
* Script: [`research/kiem_dinh_order_block.py`](../../research/kiem_dinh_order_block.py). Chỉ đọc database, chỉ đoạn
  phát triển 2018-01-01 → 2024-09-01; đoạn kiểm tra (từ 01/09/2024) vẫn khoá.
* Nguồn định nghĩa: [`reports/Thuật toán ICT của LuxAlgo.md`](../../../reports/Thuật%20toán%20ICT%20của%20LuxAlgo.md)
  (mục order block / breaker) và đặc tả `ict_structure` §4.20. Code LuxAlgo chỉ đọc để hiểu định nghĩa — các biến thể dưới
  đây tự cài lại.
* Làm tiếp [`khao_sat_ob_ote.md`](khao_sat_ob_ote.md): OB của lab giữ giá hơn vùng giả cạnh nó ~7 điểm nhưng ưu thế đến
  từ **vị trí ở chân nhịp**. Lần này so **nhiều định nghĩa** với cùng một chuẩn hình học.

Tiêu chí dưới đây chốt trước khi chạy. Sửa thì ghi ở «Sổ sửa» kèm lý do, trước khi xem kết quả.

## 1. Câu hỏi

Định nghĩa order block nào cho vùng **giữ giá** tốt nhất so với một vùng bất kỳ có **cùng hình học** (cùng khoảng cách tới
giá, cùng bề rộng, tính theo ATR) — chọn trên một nửa dev và **có giữ được ở nửa kia không**? Đây là phép đo chất lượng
vùng, không phải tín hiệu giao dịch.

## 2. Biến thể (mô tả cho chiều tăng; chiều giảm đối xứng)

| # | Tên | Định nghĩa | Nguồn |
|---|---|---|---|
| L1 | Lab OB-T neo shift (mặc định 0.9.2) | chuỗi nến giảm cuối trước nến displacement của SHIFT tăng, vùng = thân chuỗi; hiệu lực khi giá vượt đầu xa | `ict_structure` |
| L2 | Lab OB-R neo shift | nến giảm cuối trước displacement của SHIFT, vùng = [low, high] | `ob_bien_the = nen_cuoi_rau` |
| L3 | Lab OB-T neo displacement | như L1 nhưng neo vào displacement phá high 5 nến trước, không cần sweep | `ob_neo = displacement` |
| X1 | Nến cực trị, pivot 10 | pivot high đối xứng 10/10 (biết ở p + 10); close đầu tiên vượt pivot high gần nhất chưa bị phá → OB = nến có low thấp nhất trong [p, nến phá − 1], vùng = [low, high]; hiệu lực từ nến phá | LuxAlgo Order Blocks & Breaker Blocks |
| X2 | Nến cực trị, pivot 5, lọc nến lớn | như X1 với pivot 5/5, bỏ qua nến có biên độ ≥ 2·ATR khi tìm cực trị | kiểu OB nội bộ của LuxAlgo SMC |
| X3 | Nến cực trị trên swing 3 nến | pivot 1/1 (high[p] > high[p ± 1], = STH của lab); phá bằng close → nến cực trị như X1 | LuxAlgo Pure Price Action OB |
| B1 | Breaker từ X1 | OB tăng X1 bị close dưới mép dưới trong thời gian còn theo dõi → vùng [low, high] thành breaker **giảm** từ nến đó | LuxAlgo Order Blocks & Breaker Blocks |

Mọi cửa sổ (pivot, tìm nến cực trị) không vắt qua khoảng trống > 3 giờ. Không kiểm: OB theo volume (Order Block
Detector, Volumetric OB, Volumized OB của Flux Charts) — **dữ liệu dev không có volume** (cột volume = 0); mitigation
block, propulsion, rejection, unicorn — để sau.

## 3. Vòng đời chung (áp như nhau cho mọi biến thể và cho vùng song sinh)

* Vùng [lo, hi] hiệu lực từ nến xác nhận c (L: `confirmed_bar_index` của `ORDER_BLOCK_*`; X: nến phá; B1: nến close
  qua mép xa của OB).
* **Chạm lần đầu**: nến t > c đầu tiên có low ≤ hi (OB tăng), trong tối đa 96 nến; không chạm → bỏ.
* **Giữ giá** G (thước chính, như khảo sát OB cũ): nến chạm close < lo → hỏng; còn lại xét 32 nến kể từ nến chạm: high ≥
  hi + 1·ATR_t trước khi có close < lo → giữ; close < lo trước → hỏng; chưa rõ sau 32 nến, hoặc cửa sổ vắt khoảng trống
  > 3 giờ → bỏ (không vào mẫu).
* **Setup R** (thước phụ, chỉ mô tả, không dùng để chọn): vào ở hi khi chạm, dừng = lo − 0,1·ATR_t, đích = 2R; trong 32
  nến, nến chạm cả dừng lẫn đích → tính thua; hết giờ → R theo close nến cuối. **Chưa trừ phí / spread.**
* ATR = ATR của `ict_structure` (cột `atr` của timeline).

## 4. Chuẩn so sánh: vùng song sinh hình học

Mỗi vùng thật (xác nhận ở c, close C, ATR A): khoảng cách k = (C − hi) / A, bề rộng w = (hi − lo) / A. Chọn ngẫu nhiên 5
nến t′ (seed cố định) **cùng mã, cùng nửa dev, cùng giờ New York** với c, cách c ≥ 96 nến và trong ±13 tuần; vùng song
sinh hi′ = C_t′ − k·A_t′, lo′ = hi′ − w·A_t′, cùng chiều, cùng vòng đời §3. Δ = G(thật) − G(song sinh, trung bình các
song sinh có kết cục). Câu hỏi của chuẩn: định nghĩa có chọn được mức **tốt hơn một mức bất kỳ cùng khoảng cách, cùng
cỡ** không.

## 5. Chọn và xác nhận

* Đoạn A (chọn): 2018-01-01 → 2021-12-31. Đoạn B (xác nhận): 2022-01-01 → 2024-08-31. Vùng thuộc đoạn theo nến xác nhận.
* CI 95%: bootstrap khối tuần (tuần của nến chạm), 1 000 lần, kết cục của vùng thật và song sinh của nó đi cùng nhau.
* **Hợp lệ ở A**: cả XAUUSD và EURUSD có Δ với cận dưới CI > 0 và ≥ 200 lần chạm có kết cục.
* **Chọn**: biến thể hợp lệ có Δ trung bình hai mã lớn nhất. Không có biến thể hợp lệ → kết luận «không định nghĩa OB
  nào giữ giá hơn mức ngẫu nhiên cùng hình học» (vẫn báo đủ bảng; biến thể có Δ trung bình lớn nhất ghi là «ít tệ nhất»,
  không gọi là tốt nhất).
* **Xác nhận ở B**: biến thể đã chọn có Δ với cận dưới CI > 0 ở cả hai mã → **đạt**. Chỉ một phép thử ở B nên không cần
  hiệu chỉnh đa phép thử; ở A có 7 × 2 phép thử — điều kiện «cả hai mã» là hàng rào.
* Báo kèm (mô tả): số vùng, tỷ lệ được chạm, G thật / song sinh, setup R thật / song sinh, bề rộng trung vị (ATR).

## Sổ sửa

Sửa ngày 24/10/2026, **trước khi chạy thật** (mới chạy thử 2 tháng `--thu`, chỉ in số vùng), theo /code-review của script:

1. **Bootstrap khối 4 tuần** (thay 1 tuần), rút trên đúng các khối có trong mẫu (theo tuần của nến chạm). Lý do: kết
   cục song sinh lấy trong ±13 tuần nên phụ thuộc nhau quá một tuần — CI khối tuần sẽ hẹp giả; và vùng xác nhận ở A mà
   chạm ở tuần đầu của B không rơi vào lần rút nào.
2. **B1** rõ nghĩa «trong thời gian còn theo dõi»: breaker chỉ khi vòng đời §3 của OB X1 kết thúc bằng **hỏng** (close
   qua mép xa ở nến chạm hoặc trong 32 nến sau), hiệu lực từ nến hỏng. OB đã giữ giá, không được chạm, hoặc chưa rõ → không
   có breaker.
3. Cửa sổ tìm nến cực trị là [p, nến phá − 1]; nến phá được phép nằm ngay sau khoảng trống (trước: cả nến phá bị tính
   vào cửa sổ, làm rơi mọi vùng xác nhận ở nến đầu tuần).
4. Ngưỡng hợp lệ ≥ 200 tính trên **số cặp** dùng để tính Δ (vùng thật có kết cục và có ≥ 1 song sinh có kết cục).
5. Vùng thật cũng cần còn đủ 96 + 32 nến sau xác nhận, như vùng song sinh (cùng cách cắt mẫu ở cuối dữ liệu).
6. Setup R (thước phụ): nến chạm mở lọt vào vùng → vào ở giá mở; mở vượt luôn mức dừng → bỏ khỏi thước R.

Không sửa (ghi lại): song sinh không mang điều kiện khoảng trống của vùng X — sau mục 3, vùng X cũng có thể xác nhận ngay
sau khoảng trống, và song sinh đã khớp giờ New York.
