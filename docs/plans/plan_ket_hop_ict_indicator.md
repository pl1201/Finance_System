# Plan: kết hợp ICT + indicator

Ngày: 21/10/2026. Trạng thái: **bản nháp chờ duyệt.** Gom mọi thuật toán kết hợp đã thử và việc làm tiếp vào một chỗ.
Cập nhật cùng ngày: thêm Order Block và OTE (§3.4), lộ trình bước 0 và danh sách cần duyệt (§8) — **§8 đã duyệt
21/10/2026**; OB / OTE đã cài vào `ict_structure` 0.5.0 và lên web (bước 0b); khảo sát K17–K27 (bước 0) **đã chạy
21/10/2026** — kết quả và đề xuất quyết định chờ duyệt: [`khao_sat_ob_ote.md`](../research/khao_sat_ob_ote.md).

- Mục tiêu chung: [`plan_nhan_dien_trang_thai.md`](plan_nhan_dien_trang_thai.md)
- Số liệu: [`khao_sat_ict_indicator.md`](../research/khao_sat_ict_indicator.md) · OB / OTE:
  [`khao_sat_ob_ote.md`](../research/khao_sat_ob_ote.md)
- Hình chart mẫu: [`khao_sat/chart_ket_hop/`](../research/khao_sat/chart_ket_hop/)

## 1. Khung

- **Bias:** H1 + H4. **Đích giá:** M15. **Vào lệnh:** M5 (ngoài bộ nhận diện).
- **Tầm dự báo H:** 1 giờ và 4 giờ.
- **Đầu ra của bộ nhận diện:** khoảng giá, mức có thể chạm (kèm xác suất), trạng thái.
- **Dữ liệu:** XAUUSD (chính), EURUSD (lặp lại). Chỉ dùng dev trước 01/09/2024; đoạn test khoá.

## 2. Kết quả đã có (dev 2018 – 08/2024)

| Câu hỏi | Kết quả | Kết luận |
|---|---|---|
| Đoán hướng 1–4h | Tín hiệu đơn 49–51,5%; kết hợp tốt nhất 52–53%. Hoà vốn sau phí cần ≈ 59% | Không dùng để đoán hướng |
| Bias H1/H4 | 49,4–51,2% | Chỉ là bối cảnh |
| Trạng thái «đi một chiều» 1–4h | AUC ≤ 0,527 | Chỉ mô tả, không dự báo |
| Dải giá 80% | Nền (giờ + biến động gần) tốt hơn dải cố định 13–18%. Thêm ICT/indicator làm kém đi | Mô hình biến động làm lõi |
| Vùng thanh khoản ICT | Bị chạm ít hơn mức bất kỳ cùng khoảng cách 0,2–1 điểm % | Dùng để chọn mức vẽ; xác suất chạm tính theo khoảng cách |

## 3. Danh mục thuật toán kết hợp

### 3.1 Thành phần

| Nhóm | Tín hiệu (±1 / 0) |
|---|---|
| ICT (10) | thứ tự H4, H1, M15 · order flow M15 · phía DOL · pd_bias · SHIFT 4h qua · sweep 4h qua (đảo chiều) · discount/premium M15, H4 |
| Indicator (11) | EMA50/200 (M15, H1, H4) · +DI/−DI (M15, H1) · RSI > 50 · RSI ≤ 30 / ≥ 70 · MACD hist (M15, H1) · Donchian 20 (M15, H1) |
| ICT mới (2), đã cài 0.5.0 | Order Block chạm lần đầu · giá vào OTE 62–79% (§3.4) |

### 3.2 Luật kết hợp K01–K16

Cột XAU / EUR là đúng hướng 4h (%). «Phủ» là tỷ lệ nến có ý kiến (XAUUSD).

| Mã | Luật | Kiểu | XAU | EUR | Phủ | Quyết định |
|---|---|---|---|---|---|---|
| K01 | ICT H1 = H4 | đồng thuận | 50,8 | 51,2 | 16% | Lớp bối cảnh |
| K02 | EMA H1 = H4 | đồng thuận | 50,7 | 50,9 | 72% | Lớp bối cảnh |
| K03 | K01 ∧ K02 | đồng thuận | 51,4 | 51,4 | 11% | Bỏ (không hơn K01) |
| K04 | ICT H4 = H1 = order flow | top-down | **52,5** | 51,3 | 7% | Theo dõi (XAU) |
| K05 | K04 ∧ EMA H1 | top-down + lọc | **52,6** | 51,3 | 6% | Theo dõi (XAU) |
| K06 | K04 ∧ ADX H1 ≥ 25 | top-down + lọc | **52,8** | 51,7 | 4% | Theo dõi (XAU) |
| K07 | OF ∧ ADX M15 ≥ 25 | lọc ADX | 50,6 | 49,8 | 34% | Bỏ |
| K08 | OF ∧ ADX M15 ≤ 20 | lọc ADX | 50,3 | 49,9 | 28% | Bỏ |
| K09 | Sweep ∧ RSI ≤ 35 / ≥ 65 | hợp lưu oscillator | 50,2 | **52,0** | 14% | Theo dõi (EUR) |
| K10 | Sweep ∧ ADX M15 ≤ 20 | lọc ADX | 50,3 | 50,2 | 22% | Bỏ |
| K11 | SHIFT ∧ MACD M15 | đồng thuận | 51,1 | 51,3 | 9% | Bỏ (không hơn SHIFT) |
| K12 | DOL ∧ Donchian M15 | đồng thuận | 50,4 | 48,9 | 28% | Bỏ |
| K13 | Discount/premium theo bias ICT | vùng × bias | 50,9 | 51,8 | 8% | Lớp mô tả |
| K14 | Discount/premium theo bias EMA | vùng × bias | 50,5 | **51,6** | 35% | Theo dõi (EUR) |
| K15 | OF ∧ MACD ∧ RSI M15 | đồng thuận | 51,0 | 49,4 | 31% | Bỏ |
| K16 | Bỏ phiếu 8 thành phần, \|phiếu\| ≥ 6 | bỏ phiếu | 51,1 | 48,9 | 7% | Bỏ (chỉ hiện để so) |

- **Theo dõi:** chỉ kiểm lại **một lần** trên đoạn test, khi protocol được ký. Không tinh chỉnh thêm trên dev.
- **Lớp bối cảnh / mô tả:** được hiện trên chart nhưng không gọi là dự báo.

### 3.3 Kết hợp học

| Mô hình | Đặc trưng | Kết quả | Quyết định |
|---|---|---|---|
| HGB, walk-forward theo năm | Nền / + indicator / + ICT / + cả hai | AUC hướng 0,505–0,521; thêm đặc trưng không tăng | Không dùng cho hướng |
| HGB phân vị 90% (biên lên, biên xuống) | như trên | Nền tốt nhất; thêm cấu trúc làm độ phủ tụt còn 73–77% | Nền làm lõi dải giá |

### 3.4 Mới: Order Block (OB) và OTE — đã duyệt, cài (`ict_structure` 0.5.0) và đo (bước 0)

> **Kết quả bước 0** ([`khao_sat_ob_ote.md`](../research/khao_sat_ob_ote.md)): K17–K27 đúng hướng 49–53%, 0/40 qua
> null + BH, không luật lọc nào hơn cha; K18, K20, K23 không đủ mẫu (69–130 sự kiện). OB giữ giá hơn vùng giả cạnh nó
> +7 điểm ở cả hai mã, nhưng chẩn đoán sau cho thấy đó là hiệu ứng vị trí (vùng ở chân nhịp), không phải của nến OB.
> OTE 62–79% không hơn một mức bất kỳ cùng khoảng cách. Đề xuất: bỏ K17–K27 như tín hiệu hướng; OB / OTE giữ làm lớp
> mô tả. **Chờ bạn duyệt.**

**Mốc chung là SHIFT.** ICT dựng OB và OTE từ cú phá cấu trúc có displacement (MSS). Lab không có BOS/MSS (quyết
định B1); đổi hướng là SHIFT = sweep → displacement ngược chiều, close qua mức bị quét. Mỗi SHIFT tăng tại nến d đã
ghi sẵn ba mốc cần dùng: nến lấy b, nến sweep r, cực trị cú quét X. Dev có khoảng 1 500 SHIFT mỗi mã (0,9 lần/ngày),
nên mỗi biến thể có tối đa khoảng 1 500 OB / OTE. Mọi định nghĩa dưới đây viết cho chiều tăng; chiều giảm đối xứng.

**Order Block**

| Mục | Định nghĩa |
|---|---|
| Nến OB — biến thể chính **OB-T** (gốc ICT, nghiên cứu §3.4) | Chuỗi nến giảm (close < open) liên tiếp **cuối cùng** trong [b − 5, d − 1], gộp thành một khối. Bỏ nến thân nhỏ nằm lọt trong thân nến kề |
| Vùng OB-T | Chỉ thân: mép trên = open cao nhất của chuỗi, mép dưới = close thấp nhất. Mean threshold = giữa vùng |
| Biến thể đối chứng **OB-R** | Một nến giảm cuối, lấy cả râu (high – low). Cách SMC phổ biến (LuxAlgo-kiểu) |
| Biến thể mẫu lớn **OB-D** | Neo vào mọi displacement tăng có close vượt high cao nhất của 5 nến trước (nhiều hơn SHIFT khoảng 10 lần), lấy nến như OB-T |
| Xác nhận (thêm khi cài) | OB chỉ có hiệu lực khi giá vượt đầu xa của khối (`high > mép trên`) — gốc ICT, nghiên cứu §3.4. Trước đó là ứng viên; ứng viên bị bỏ khi close thủng mép dưới, hết hạn hoặc SHIFT ngược chiều |
| Biết lúc | Nến vượt đầu xa (d hoặc sau); có hiệu lực từ nến sau |
| Chạm | Nến đầu tiên t > d có low[t] ≤ mép trên → `OB_TAP_UP`. Chỉ tính lần chạm đầu |
| Hỏng | Close < mép dưới → `OB_FAIL_UP` (ứng viên breaker, để sau) |
| Hết hạn | 96 nến (24 giờ) từ d không chạm, hoặc có SHIFT ngược chiều → `OB_EXPIRED` |
| Không có OB | Không có nến giảm nào trong [b − 5, d − 1] → không tạo |

**OTE**

| Mục | Định nghĩa |
|---|---|
| Nhịp | Đáy X = cực trị cú quét của SHIFT. Đỉnh H = high cao nhất từ d tới nến **trước** nến đang xét; ngừng cập nhật khi giá đã vào OTE |
| Vùng | Từ H − 0,79·(H − X) đến H − 0,62·(H − X); «điểm ngọt» 70,5% |
| Điều kiện | H − X ≥ 2 ATR (nhịp nhỏ hơn thì bỏ) |
| Vào OTE | Nến đầu tiên có low ≤ H − 0,62·(H − X) → `OTE_ENTRY_UP`, ghi độ sâu hồi thật. Chỉ tính lần vào đầu |
| Hỏng | Low < X trước khi vào → `OTE_FAIL_UP` |
| Hết hạn | 96 nến, hoặc SHIFT mới (ngược chiều; cùng chiều thì thay nhịp — thêm khi cài) → `OTE_EXPIRED` |

**Luật kết hợp mới K17–K27** — khai báo trước, đo như K01–K16: đúng hướng 1h/4h, nhưng tính **tại nến sự kiện**
(chạm OB / vào OTE). Mỗi luật được so cặp với tín hiệu «cha».

| Mã | Luật | So với | Kiểu |
|---|---|---|---|
| K17 | OB-T chạm lần đầu → theo chiều OB | SHIFT 4h qua | ICT đơn |
| K18 | K17 ∧ bias ICT H1 = H4 cùng chiều | K17 | top-down |
| K19 | K17 ∧ bias EMA H1 = H4 cùng chiều | K17 | lọc indicator |
| K20 | K17 ∧ RSI ≤ 40 (OB tăng) / ≥ 60 (OB giảm) | K17 | hợp lưu oscillator |
| K21 | K17, chỉ OB có FVG (SHIFT_FVG) | K17 | «OB hợp lệ» kiểu ICT |
| K22 | Vào OTE lần đầu → theo chiều SHIFT | SHIFT 4h qua | ICT đơn |
| K23 | K22 ∧ bias ICT H1 = H4 | K22 | top-down |
| K24 | K22 ∧ bias EMA H1 = H4 | K22 | lọc indicator |
| K25 | K22 ∧ có OB-T (cùng SHIFT) giao với vùng OTE | K22 | hợp lưu OB + OTE |
| K26 | K22 ∧ ADX H1 ≥ 25 | K22 | lọc xu hướng |
| K27 | K22 trong killzone London (02–05) hoặc NY sáng (07–10), giờ NY | K22 | lọc giờ ICT |

Chạy thêm K17 với OB-R và OB-D để kiểm chéo. Các kết hợp K18–K21 chỉ chạy trên OB-T.

**Phép đo cho mức** (phục vụ đầu ra «mức có thể chạm» của bộ nhận diện):

- **OB có giữ giá hơn vùng giả không.** Tại lần chạm, đo P(đi +1 ATR theo chiều OB trước khi close vượt mép xa).
  So với vùng giả cùng bề rộng, lấy từ một nến khác trong 10 nến trước displacement (không phải nến OB). Câu hỏi:
  «nến ngược màu cuối» có gì đặc biệt không.
- **OTE 62–79% có hơn độ sâu hồi khác không.** Đo P(nhịp đi tiếp, vượt H trong 4 giờ) theo độ sâu hồi: 0–38%,
  38–50%, 50–62%, 62–79%, 79–100%.
- **Mô hình học.** Thêm đặc trưng: khoảng cách tới OB mở gần nhất phía trên / dưới, cờ đang ở trong OTE, độ sâu hồi
  của nhịp hiện tại. Chấm lại hướng, trạng thái, dải giá như §3.3.

**Lực thống kê (ước lượng trước khi đo).**

- K17 / K22: khoảng 700–1 200 sự kiện mỗi mã → hiệu ứng nhỏ nhất thấy được ≈ 4–5 điểm %.
- Luật có lọc (300–500 sự kiện): ≈ 6–8 điểm %.
- Như vậy đủ để thấy một hiệu ứng **đủ lớn để giao dịch** (cần ≈ +9 điểm so với 50%), nhưng không đủ để thấy hiệu
  ứng 1–2 điểm. OB-D tăng mẫu khoảng 10 lần để kiểm chéo.
- Họ phép thử mới: 11 luật × 2 mã × 2 tầm = 44, cộng 2 biến thể đối chứng. BH tính riêng cho họ này; ghi cả vào sổ thử.

## 4. Thuật toán của bộ nhận diện (đề xuất)

1. **Dải giá 80% (+ lõi 50%) cho 1h / 4h.**
   - Đầu vào: giờ NY, thứ, biến động gần, ATR tương đối.
   - Bậc baseline: Nền → B2 (Log-HAR/EWMA) → hiệu chỉnh độ phủ bằng conformal.
   - Chấm: độ phủ theo giờ, interval score.
2. **Mức có thể chạm.**
   - Mức: vùng thanh khoản ICT, biên range biên rõ, PDH/PDL. OB và vùng OTE là ứng viên, chỉ thêm nếu §3.4 cho thấy
     chúng giữ giá hơn vùng giả.
   - Xác suất chạm 1h / 4h = f(khoảng cách theo ATR, giờ, biến động).
   - Chấm: Brier, đường hiệu chuẩn.
3. **Trạng thái mô tả.**
   - Bốn trạng thái: trend, range biên rõ, sideway nhiễu, sideway nén (plan nhận diện §3).
   - Kèm bối cảnh K01/K02 và vùng K13/K14.
   - Không có xác suất hướng.
4. **Lớp kết hợp luật (tuỳ chọn trên chart).**
   - Gồm K04–K06, K09, K14.
   - Luôn kèm điểm thật (đúng hướng, độ phủ, mức hoà vốn).

## 5. Lộ trình

| Bước | Việc | Xong khi |
|---|---|---|
| 0 | **Đã chạy 21/10/2026** ([`khao_sat_ob_ote.md`](../research/khao_sat_ob_ote.md)): bảng K17–K27, phép đo mức, MDE. Đặc trưng OB / OTE cho mô hình học chưa làm (đề xuất gộp vào bước 3) | Bạn duyệt kết quả |
| 0b | **Xong 21/10/2026.** `order_block.py`, `ote.py` trong `ict_structure` 0.5.0; lớp «Order block», «OTE 62–79%» trên web | 15 test thành phần / thuật toán + API + hiển thị; mọi output cũ khớp tuyệt đối (đặc tả §1) |
| 1 | Dải giá: Nền → B2 → conformal, chấm theo giờ | Độ phủ 78–82% ở mọi khung giờ |
| 2 | Xác suất chạm: thêm biên range và PDH/PDL; so với vùng ICT | Có bảng hiệu chuẩn cho từng loại mức |
| 3 | Trạng thái mô tả v1 theo định nghĩa §3; vài trăm nhãn tay | Tỷ lệ thời gian hợp lý, khớp nhãn tay |
| 4 | Thử range biên rõ / DC làm đặc trưng cho dải giá: range có giữ giá trong biên hay làm dải lệch không | Biết cấu trúc có thêm thông tin so với B2 không |
| 5 | Đưa lên web lab: lớp «nhận diện» (dải + mức + trạng thái) và lớp «kết hợp luật» tuỳ chọn, có replay | Xem được trên chart, kèm điểm thật |
| 6 | Kiểm một lần trên đoạn test: dải giá, xác suất chạm, K04–K06 (XAU), K09 và K14 (EUR) | Kết quả ghi vào sổ thử, không sửa sau đó |
| 7 | Vào lệnh M5 (protocol Copilot): dùng dải giá cho SL/TP và để «không giao dịch» khi dải < k × phí | Thành ứng viên E2 của protocol |

## 6. Quy tắc

- Mỗi lần thử một cấu hình mới đều ghi vào sổ thử (N), tính PBO trước khi chọn.
- Mọi so sánh phải có baseline, CI theo tuần và null dịch vòng.
- Chỉ gọi là «dự báo» khi có xác suất hoặc khoảng, có protocol chấm, có baseline và hiện điểm thật (AGENTS.md §4).
- Không P&L, không win rate trong thống kê lần chạy.

## 7. Tái lập

| Script | Việc |
|---|---|
| [`research/ict_indicator_survey.py`](../../research/ict_indicator_survey.py) | Khảo sát: luật, mô hình học, vùng ICT (≈ 6 phút) |
| [`research/ve_ict_indicator.py`](../../research/ve_ict_indicator.py) | Sáu hình kết quả |
| [`research/chart_ket_hop.py`](../../research/chart_ket_hop.py) | Bốn chart mẫu (nguyên mẫu, chưa phải plugin) |
| [`research/khao_sat_ob_ote.py`](../../research/khao_sat_ob_ote.py) | Bước 0: K17–K27, OB so với vùng giả, OTE theo độ sâu (≈ 1,5 phút) |

Luồng xử lý của OB / OTE (vị trí trong từng nến của `ict_structure`, chuỗi sự kiện, vòng nghiên cứu):
[`kien_truc_luong_ict.md`](../guides/kien_truc_luong_ict.md) §4.4.

## 8. Cần duyệt — **đã duyệt 21/10/2026** (đúng đề xuất)

| # | Câu hỏi | Đề xuất |
|---|---|---|
| 1 | Neo OB và OTE vào SHIFT (thay cho MSS) | Đồng ý — lab không có BOS/MSS (B1) |
| 2 | OB lấy nến nào | Chính: chuỗi nến ngược màu cuối, chỉ thân (OB-T). Đối chứng: một nến cuối cả râu (OB-R). Mẫu lớn: neo displacement (OB-D) |
| 3 | Vòng đời OB | Chỉ lần chạm đầu; hỏng khi close vượt mép xa; hết hạn 24 giờ hoặc khi có SHIFT ngược chiều |
| 4 | OTE | Vùng 62–79% (điểm ngọt 70,5%), nhịp ≥ 2 ATR, hết hạn 24 giờ |
| 5 | Ngưỡng của luật kết hợp | RSI 40 / 60 (K20); killzone London 02–05, NY sáng 07–10 theo mặc định của lab (K27) |
| 6 | Thứ tự làm | Khảo sát trước (bước 0), cài vào `ict_structure` sau khi xem số (bước 0b) |
| 7 | Breaker (OB hỏng đổi vai), IFVG | Để sau bước 0 |
