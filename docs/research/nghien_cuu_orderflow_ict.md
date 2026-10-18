# Nghiên cứu: order flow kiểu ICT — đọc theo giá, qua thanh khoản

Ngày: 06/10/2026. Câu hỏi của người dùng: order flow (đọc thuần từ giá, «thanh khoản → thanh khoản»)
nên hiểu và đưa vào `ict_structure` thế nào. Ba phần:

1. **Tài liệu:** ICT nói gì về order flow; cái gì xác nhận, cái gì làm đổi chiều. Tóm tắt ở §2, nguồn
   đầy đủ (trích phụ đề video gốc có mốc thời gian, mã nguồn indicator, preprint) ở
   [`nghien_cuu_orderflow_ict_nguon.md`](nghien_cuu_orderflow_ict_nguon.md).
2. **Dữ liệu:** dùng chính sự kiện của `ict_structure` v0.2.0, đo xem các cách đọc order flow có cho biết
   **phía thanh khoản nào bị lấy kế tiếp** tốt hơn mốc ngẫu nhiên không (§3–§5). Script:
   [`research/orderflow_survey.py`](../../research/orderflow_survey.py); kết quả đầy đủ:
   [`khao_sat/orderflow_survey_dev.json`](khao_sat/orderflow_survey_dev.json).
3. **Quyết định (06/10/2026):** dải order flow đọc theo run + shift, «chưa rõ» theo quy tắc A (§7). Số mô tả
   so các quy tắc «chưa rõ» ở §8. Script: [`research/orderflow_rules.py`](../../research/orderflow_rules.py);
   kết quả: [`khao_sat/orderflow_rules_dev.json`](khao_sat/orderflow_rules_dev.json).

Không phải tín hiệu giao dịch, không có P&L. Mọi dữ liệu kết thúc **trước 01/09/2024** — đoạn kiểm tra
vẫn khoá.

---

## 1. Kết luận ngắn

1. **Theo ICT, order flow chỉ đọc từ giá** và là chuyện **giá đi đâu lấy gì**: đi lấy stop (thanh khoản
   ngoài, ERL) hoặc đi lấp chỗ kém hiệu quả (FVG — thanh khoản trong, IRL); không có hai thứ đó thì đi
   ngang. Cách hiểu «thanh khoản → thanh khoản» của bạn khớp ICT, với điều kiện tính cả FVG là thanh
   khoản trong range. Quy tắc vận hành ICT nói rõ nhất (2023): *khi tăng, nến đóng giảm đỡ giá; đáy ngắn
   hạn bị lấy chỉ là stop run và giá phải quay lên ngay*. ICT nói thẳng HH/HL **không** phải tiêu chí
   chính; tiêu chí chính là draw, và draw nằm ở **khung ngày**.
2. **ICT gần như không có định nghĩa định lượng:** chỉ có swing 3 nến, FVG 3 nến, mức 50% (CE),
   «thân nến kể chuyện, râu gây thiệt hại». Ngưỡng ATR, số nến cho sweep, cửa sổ shift… đều do lab /
   cộng đồng đặt.
3. **Trên dữ liệu lab, không cách đọc order flow nào dự báo phía thanh khoản bị lấy kế tiếp tốt hơn mốc
   ngẫu nhiên theo khoảng cách.** Đã thử 7 cách đọc × M5/M15/H1/H4 × đích cùng khung hoặc D1 × chờ hồi
   FVG × lọc theo khung lớn × theo killzone, trên XAUUSD và EURUSD 2018–08/2024 (hơn 100 nghìn lần lật được chấm, cộng mọi cách đọc).
   Ở mọi mẫu lớn, lợi thế nằm trong **±2 điểm %**; khoảng tin cậy chứa 0 hoặc hơi âm.
4. **Khớp với kiểm định công khai:** hai preprint 2026 và một blog backtest không thấy lợi thế của
   ICT/SMC «như được dạy»; sweep không phải tín hiệu đảo chiều (một preprint G10 FX thấy thiên về tiếp
   diễn). Chưa có nghiên cứu nào kiểm định *trạng thái* order flow — §5 ở đây là phép đo đầu tiên lab có.
5. **Hệ quả cho thiết kế:** order flow đáng có trên chart như một **mô tả** — giá vừa lấy gì, đang đi về
   phía nào, vùng gần nhất phía đó ở đâu. Không nên trình bày đường «đích» như dự báo. Thứ duy nhất ảnh
   hưởng rõ đến việc thanh khoản D1 nào bị lấy trước là **xu hướng dài hạn** (vàng tăng 2018–2023 →
   BSL D1 bị lấy trước nhiều hơn mốc ~15 điểm %), không phải sự kiện M15/H1 (§5.4).
6. **Một giả thuyết đáng kiểm thêm, chưa phải phát hiện:** shift trong phiên **London** dương +4–5 điểm %
   ở cả XAUUSD lẫn EURUSD 2018–2023 (khoảng tin cậy chạm 0; 1 trong ~10 lát cắt đã thử; 2024 không lặp
   lại). Muốn biết thật phải khai báo trước rồi kiểm trên đoạn chưa dùng (§6).
7. **Đã chốt (06/10/2026):** dải order flow = **run + shift**; run phía **ngược** order flow đang có →
   **chưa rõ** (quy tắc A); bỏ quy tắc «hai phía đều bị run trong N nến». Cài ở `ict_structure` 0.3.0 (§7).
   Với quy tắc A, order flow M15 đổi chiều 0.72–0.82 lần mỗi ngày giao dịch và «chưa rõ» chiếm 22–24% thời
   gian (§8).

---

## 2. ICT nói gì (tóm tắt — nguồn ở file phụ lục)

| Chủ đề | ICT gốc (mức A — lời ICT, phụ đề tự động) | Ghi chú |
|---|---|---|
| Định nghĩa | 2016: *«the seeking of large institutional liquidity»* — tìm thanh khoản lớn ở tháng/tuần, nhìn nó được giao dịch vào ở khung ngày. 2023: order flow đọc *«in price action»*, DOM/footprint «can be spoofed» | Thuần giá |
| Hai động cơ của giá | Đi lấy stop, hoặc đi tái cân bằng chỗ kém hiệu quả; không có cái nào → đi ngang (2023) | Cơ sở cho «thanh khoản → thanh khoản» |
| Dấu hiệu tăng / giảm | Tăng: nến đóng giảm đỡ giá; đáy ngắn hạn bị lấy = stop run, quay lên ngay; đỉnh ngắn hạn liên tục bị lấy. Giảm: đối xứng (2022–2023) | Sweep SSL **trong** order flow tăng là tiếp diễn, không phải đảo chiều |
| Thân hay râu | «bodies tell the story, wicks do the damage»; OB/FVG được tôn trọng khi **thân** không vượt 50% | Lấy thanh khoản: chỉ cần vượt thân/râu |
| ERL / IRL | ERL = stop trên/dưới biên range; IRL = FVG, void, OB, đỉnh/đáy ngắn hạn trong range; **tương đối** theo range chọn | Chu kỳ «ERL → IRL → ERL» là cách nói thứ cấp |
| Đổi chiều | Chạm mục tiêu thanh khoản/PD array khung lớn; MSS (sau khi lấy thanh khoản, giá **giao dịch qua** đỉnh/đáy ngắn hạn, không cần close, kèm FVG); CISD (vượt giá mở nến đầu chuỗi sau «sự kiện chuyển tiếp») | ICT mơ hồ close/wick ở CISD |
| «Chưa rõ» | Đỉnh/đáy trung hạn đang tin bị phá → *«sitting on my hands»*, chờ thêm thông tin | Không đảo chiều ngay |
| HH/HL | *«we're not looking for just the simple higher high higher low…»* | Không phải tiêu chí chính |
| Nhiều khung | Tuần: bias; **ngày: nơi chứa draw**; H1/M15: dựng setup; M1–M5: vào lệnh. Khung nhỏ «phụ thuộc» khung lớn | «H1/H4 → M15/M5» chỉ là quy ước thứ cấp |
| Swing trung hạn | Swing tạo ra **lúc lấp FVG** được ICT gọi ngay là ITH/ITL | Khác ITH/ITL kiểu Larry Williams mà lab dùng |

Code công khai: không cài đặt mở nào có biến «trạng thái order flow» tường minh; thư viện Python
`smart-money-concepts` nhìn dữ liệu tương lai (không dùng được cho kiểm định nhân quả).

---

## 3. Các cách đọc order flow đã thử (nhân quả)

Trạng thái ±1 sau mỗi nến, chỉ đổi khi có sự kiện **đã xác nhận** ở nến đó (hai chiều ngược nhau cùng
nến → 0). Sự kiện lấy từ `ict_structure` v0.2.0, tham số mặc định.

| Cách đọc | Tăng khi | Giảm khi | Ứng với ICT |
|---|---|---|---|
| **run + shift** | `LIQ_RUN_UP` hoặc `SHIFT_UP` | `LIQ_RUN_DOWN` hoặc `SHIFT_DOWN` | «thanh khoản → thanh khoản»: lấy BSL rồi đi luôn, hoặc quét SSL rồi displacement |
| chỉ run | `LIQ_RUN_UP` | `LIQ_RUN_DOWN` | «đỉnh ngắn hạn liên tục bị lấy» |
| chỉ shift | `SHIFT_UP` | `SHIFT_DOWN` | gần MSS (lab không yêu cầu phá đỉnh/đáy ngắn hạn — B1) |
| theo sweep | `LIQ_SWEEP_SSL` | `LIQ_SWEEP_BSL` | đọc sweep là đảo chiều. Đọc ngược lại (sweep = tiếp diễn) có lợi thế đúng bằng **trừ** con số này |
| phản ứng FVG — mép xa | FVG tăng được tôn trọng (sau khi chạm, close rời mép gần ≥ 1 ATR) hoặc FVG giảm bị xuyên (close qua mép xa) | đối xứng | PD array respect / disrespect |
| phản ứng FVG — CE | như trên nhưng «xuyên» = close qua 50% vùng | đối xứng | cách ICT xét bằng thân nến |
| thứ tự HH/HL | `order` = +1 | `order` = −1 | cấu trúc (lab đang có) |

Thêm ba biến thể: **chờ hồi về FVG** của `SHIFT_FVG` rồi mới chấm (mô hình shift → FVG điển hình);
**lọc theo khung lớn** (lật M15 cùng / ngược chiều order flow H1, H4); **đích là vùng D1** thay cho vùng
cùng khung.

## 4. Cách đo

* Tại nến t trạng thái vừa lật sang s: vùng còn nguyên gần nhất phía trên (BSL) và phía dưới (SSL) sau
  nến t. **Kết cục** = vùng nào bị **lấy** trước (định nghĩa lấy của lab: xuyên ≥ 0.1·ATR). «Trúng» =
  vùng phía s bị lấy trước. Kết cục chỉ dùng để chấm — không bao giờ là đầu vào.
* **Mốc ngẫu nhiên:** giá không xu hướng chạm vùng trên trước với xác suất
  `d_dưới / (d_trên + d_dưới)`. **Lợi thế** = tỷ lệ trúng − mốc. Nếu order flow có thông tin, lợi thế
  phải dương rõ.
* **Kiểm thước đo:** trên mẫu mọi nến (cách 8 nến) M15 2018–2023, mốc khớp thực tế từng nhóm:
  0.13→0.14, 0.30→0.31, 0.50→0.49, 0.70→0.69, 0.87→0.87 (XAUUSD); EURUSD tương tự. Năm 2024 (vàng
  tăng mạnh) và với vùng D1 ở xa, mốc lệch theo xu hướng dài hạn → báo thêm **lợi thế cân bằng chiều**
  (trung bình lợi thế lật tăng và lật giảm — độ trôi cộng một chiều bao nhiêu thì trừ chiều kia bấy
  nhiêu). Ở mọi mẫu lớn hai con số gần như trùng nhau.
* Khoảng tin cậy 95%: bootstrap theo khối tuần (2000 lần). Bỏ dòng thiếu vùng, hai vùng bị lấy cùng một
  nến, hoặc chưa rõ tới hết đoạn.

## 5. Kết quả

Lợi thế (điểm %) và khoảng tin cậy 95%; n = số lần lật được chấm.

### 5.1. Cùng khung (vùng thanh khoản của chính khung đó)

| Cách đọc | XAUUSD 2018–2023 | EURUSD 2018–2023 | XAUUSD 01–08/2024 | EURUSD 01–08/2024 |
|---|---|---|---|---|
| M15 run + shift | +0.5 [−1.0, +2.2] n 1977 | **−1.9** [−3.4, −0.6] n 2168 | −1.4 [−6.4, +3.3] n 219 | −0.4 [−4.4, +3.3] n 253 |
| M15 chỉ run | +0.7 [−1.4, +2.8] n 1264 | −1.8 [−3.8, +0.1] n 1377 | −5.7 [−11.9, +0.7] n 160 | −4.1 [−9.6, +1.7] n 161 |
| M15 chỉ shift | +2.1 [−1.0, +5.2] n 701 | −0.5 [−3.1, +2.2] n 771 | +1.7 [−9.9, +12.6] n 73 | −2.8 [−12.2, +6.3] n 87 |
| M15 theo sweep | +0.3 [−1.1, +1.5] n 3452 | −0.1 [−1.4, +1.1] n 3522 | +2.0 [−1.9, +5.8] n 388 | **−3.7** [−7.0, −0.4] n 389 |
| M15 phản ứng FVG — mép xa | −0.5 [−1.0, 0.0] n 12124 | **−0.9** [−1.4, −0.4] n 12845 | −0.4 [−1.7, +0.9] n 1268 | −0.8 [−2.1, +0.7] n 1478 |
| M15 phản ứng FVG — CE | **−0.7** [−1.1, −0.2] n 13033 | **−1.0** [−1.4, −0.5] n 13835 | −0.1 [−1.1, +1.0] n 1375 | −0.9 [−2.1, +0.3] n 1615 |
| M15 thứ tự HH/HL | 0.0 [−1.5, +1.4] n 3871 | −0.6 [−1.9, +0.8] n 3887 | **−4.7** [−8.3, −0.9] n 437 | +0.6 [−3.5, +4.6] n 426 |
| H1 run + shift | +1.3 [−2.4, +5.0] n 454 | +1.3 [−1.8, +4.6] n 546 | −1.4 [−11.7, +9.6] n 41 | −7.8 [−15.9, +0.5] n 62 |
| H4 run + shift | −2.1 [−9.8, +5.3] n 126 | +4.2 [−2.7, +10.5] n 130 | (n 9) | (n 8) |

XAUUSD M5 01–08/2024: run + shift −1.8 [−4.3, +0.9] (n 683); chỉ shift −3.0; theo sweep −0.2; phản ứng
FVG −0.7; HH/HL −0.6.

**Tần suất lật ở M15** (`lat_moi_ngay` trong JSON): run + shift ~1.1, chỉ shift ~0.4, HH/HL ~2.1, phản ứng
FVG ~6.6–7.5 lần mỗi **ngày lịch UTC có nến**. Đây là đơn vị của `orderflow_survey.py`: nó đếm số ngày UTC
khác nhau của `bar_time`, gồm cả phần phiên mở tối Chủ nhật, nên một tuần có ~6 «ngày». Một tuần có ~5
**ngày giao dịch** (theo lịch phiên); 1 ngày giao dịch ≈ 1.20 ngày UTC có nến (XAUUSD 2018–2023: 1859 ngày
UTC / 1548 ngày giao dịch). Tính theo ngày giao dịch thì nhân ~1.2: run + shift lật 1.30 lần/ngày ở XAUUSD
và 1.42 ở EURUSD 2018–2023 (đổi chiều thật 1.29 và 1.40), chỉ shift ~0.5, HH/HL ~2.5. Với quy tắc A đã
chốt, order flow đổi chiều 0.72–0.82 lần mỗi ngày giao dịch (§8.4). Các số «/ngày» ở §1, §7, §8 và trong
`ict_structure` (thống kê lần chạy) đều tính theo ngày giao dịch.

### 5.2. Mô hình shift → hồi về FVG → đích

Chấm tại lần đầu giá hồi về FVG của `SHIFT_FVG` (≤ 32 nến, trước khi đích bị lấy, close chưa xuyên mép
xa): XAUUSD 2018–2023 **+0.4** [−3.9, +4.6] (n 456); EURUSD **−0.1** [−4.4, +4.5] (n 443). Khoảng 27–28%
số `SHIFT_FVG` không hồi về trong 32 nến, 12–15% hồi rồi close xuyên mép xa ngay.

### 5.3. Khung lớn có giúp không

| M15 run + shift, tách theo order flow khung lớn (đã biết lúc lật) | XAUUSD 2018–2023 | EURUSD 2018–2023 |
|---|---|---|
| H1 cùng chiều | 0.0 [−2.9, +3.0] n 881 | −1.7 [−4.4, +1.1] n 982 |
| H1 ngược chiều | +1.3 [−1.5, +3.9] n 1077 | −2.1 [−4.7, +0.2] n 1180 |
| H4 cùng chiều | −1.5 [−4.4, +1.4] n 929 | −1.5 [−4.0, +1.0] n 1062 |
| H4 ngược chiều | +2.5 [−0.3, +5.2] n 1016 | −2.3 [−5.1, +0.4] n 1102 |

Lật cùng chiều khung lớn **không** tốt hơn lật ngược chiều.

### 5.4. Đích là vùng D1 (ICT: draw nằm ở khung ngày)

| Order flow → vùng D1 | XAUUSD 2018–2023 | EURUSD 2018–2023 |
|---|---|---|
| M15 run + shift | −0.2 [−0.8, +0.5] n 1633 — lật tăng +14.6 / lật giảm −15.1 | +0.2 [−0.5, +0.8] n 1646 — tăng −8.4 / giảm +8.6 |
| H1 run + shift | −0.5 [−3.2, +2.4] n 356 — tăng +12.6 / giảm −13.5 | +0.9 [−1.5, +3.3] n 414 — tăng −7.2 / giảm +8.7 |

Tách theo chiều lệch rất lớn nhưng **cân bằng về 0**: vùng D1 nào bị lấy trước được quyết định bởi xu
hướng dài hạn (vàng tăng, EURUSD giảm trong 2018–2023), không phải bởi order flow M15/H1.

### 5.5. Shift theo killzone (M15)

| Killzone của nến shift | XAUUSD 2018–2023 | EURUSD 2018–2023 |
|---|---|---|
| London | +4.9 [−1.3, +11.4] n 176 | +4.0 [−0.8, +8.2] n 306 |
| Asia | +6.2 [−3.4, +15.0] n 75 | +5.2 [−3.5, +14.0] n 79 |
| NY AM | +1.2 [−4.1, +6.6] n 263 | −2.8 [−9.1, +3.2] n 160 |
| London close | −3.3 [−12.6, +6.7] n 83 | **−11.5** [−19.6, −3.1] n 97 |
| ngoài killzone | +0.9 [−8.2, +10.2] n 104 | −3.1 [−9.9, +4.3] n 129 |

Đây là 10 lát cắt; với ngần ấy phép thử, một hai ô «có ý nghĩa» là chuyện bình thường. London dương ở cả
hai cặp là điểm đáng chú ý duy nhất; 2024 (mẫu nhỏ) không lặp lại.

---

## 6. Diễn giải và giới hạn

* **Đo một kết cục cụ thể:** «vùng gần nhất phía nào bị lấy trước». Order flow có thể vẫn có ích theo
  nghĩa khác (độ dài cú chạy, tốc độ, phản ứng sau khi tới đích) — chưa đo.
* **Vùng thanh khoản của lab:** ITH/ITL kiểu Larry Williams (+ gộp EQ) của từng khung. Chưa có PDH/PDL,
  PWH/PWL, đỉnh/đáy phiên (Asia/London range), và chưa có ITH/ITL kiểu ICT (swing tạo lúc lấp FVG) —
  giai đoạn 3 thêm vùng khung lớn và PDH/PDL.
* **Một cách vận hành hoá:** sweep cần close quay lại trong 3 nến, displacement ≥ 1.5 ATR, shift trong 3
  nến, lấy = 0.1 ATR. ICT không cho số; biến thể khác có thể cho kết quả khác — nhưng mọi biến thể đã thử
  đều ra cùng một hướng (≈ 0).
* **Dữ liệu:** giá BID spot HistData, không volume; hai mã; nhiều phép thử → cần điều chỉnh khi đọc
  từng ô lẻ.
* Đoạn kiểm tra (từ 09/2024) **chưa dùng**. Nếu muốn kiểm giả thuyết London (§5.5), nên khai báo trước
  đúng một giả thuyết (vd «shift M15 trong London, run + shift, lợi thế > 0») rồi mới mở khoá.

## 7. Đề xuất cho `ict_structure` và quyết định (chốt 06/10/2026)

**Quyết định của người dùng, 06/10/2026.** Ghi ở [`plan_ict_structure.md`](../plans/plan_ict_structure.md)
§8.3; cài ở `ict_structure` 0.3.0 ([`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md)
§4.12).

| # | Quyết định | Căn cứ |
|---|---|---|
| OF1 | Dải order flow đọc theo **run + shift** («thanh khoản → thanh khoản»): `LIQ_RUN_UP` hoặc `SHIFT_UP` → tăng; `LIQ_RUN_DOWN` hoặc `SHIFT_DOWN` → giảm. Sweep, FVG, displacement, HH/HL **không** là đầu vào | Đề xuất 1 dưới đây; khớp ICT 2023 (§2). Không cách đọc nào dự báo tốt hơn mốc ngẫu nhiên (§5), nên chọn cách đọc sát ICT, ít lật, dễ giải thích |
| OF2 | «Chưa rõ» theo **quy tắc A**: run phía **ngược** order flow đang có → chưa rõ (không lật ngay); shift vẫn lật thẳng; hai chiều cùng nến → chưa rõ; từ chưa rõ, run hoặc shift kế tiếp đặt chiều. **Bỏ quy tắc B** (hai phía đều bị run trong N nến → chưa rõ) | §8: B gần như không xảy ra — ở N = 4/8/16 nến M15 chỉ thêm < 0.1 đoạn chưa rõ mỗi ngày giao dịch và ≤ 0.5 điểm % thời gian «chưa rõ»; A + B(8) gần như trùng A |

Các đề xuất gốc bên dưới giữ nguyên; dòng «→» ghi kết quả.

Nhắc lại vai trò của bộ nhận diện: cung cấp **bằng chứng có giải thích** cho tầng regime, không phát
tín hiệu (plan §1). Với kết quả trên:

1. **Hiển thị order flow như mô tả, đọc theo thanh khoản.** Đề xuất cách đọc **run + shift**: khớp
   «thanh khoản → thanh khoản» và quy tắc ICT 2023, ít lật (~1.1 lần mỗi ngày UTC có nến ở M15, tức ~1.3
   lần mỗi ngày giao dịch — §5.1). Chart mặc định: một dải tăng / giảm / chưa rõ, vùng gần nhất phía order
   flow ghi là «vùng gần nhất phía trên/dưới» (không ghi «đích»), mức vô hiệu, mũi tên shift, kèm chú
   giải; phần còn lại vào chế độ «chi tiết».
   → **Đã chốt (OF1).** Giao diện (vẽ lại theo [`plan_hien_thi_ict.md`](../plans/plan_hien_thi_ict.md),
   06/10/2026): dải order flow có chữ ở đáy chart, vùng BSL/SSL vẽ từ đỉnh/đáy gốc, «Shift ↓/↑», dòng trạng thái
   thay chú giải màu; chế độ Gọn / Chi tiết / Lịch sử.
2. **Trạng thái «chưa rõ»** theo ICT («sitting on my hands»): khi vùng phía ngược lại bị **run** mà chưa
   có shift/run cùng chiều mới, hoặc khi hai phía đều bị run trong vài nến. Cần bạn chọn quy tắc.
   → **Đã chốt: quy tắc A (OF2)**; quy tắc «hai phía đều bị run» bỏ (§8.2).
3. **Wick hay close:** giữ phân vai lai như lab đang làm — râu (xuyên ≥ 0.1 ATR) cho «lấy thanh khoản»,
   close cho «quay lại / phá / tôn trọng».
   → 0.3.0 không đổi phân vai này (run, sweep giữ định nghĩa của 0.2.0).
4. **Không thêm order flow vào chấm điểm như một dự báo** cho tới khi có bằng chứng; nếu muốn, thêm nó
   làm **đặc trưng** cho tầng regime (B3 — ghép ở lớp kịch bản).
   → 0.3.0 không có mục tiêu chấm hay loại nhãn cho order flow.
5. **Giả thuyết London shift:** quyết định có mở đoạn kiểm tra cho một giả thuyết khai báo trước hay
   không.
   → Chưa quyết; đoạn kiểm tra vẫn khoá.

Các điểm mơ hồ khác (vùng nào được tính, ITH/ITL kiểu ICT, CISD, thời hạn vùng, ưu tiên khung) liệt kê
kèm phương án ở file nguồn §8.

## 8. Quy tắc dải order flow và «chưa rõ»: số mô tả (06/10/2026)

Câu hỏi: đọc run + shift thì dải order flow trông thế nào (mỗi trạng thái chiếm bao nhiêu thời gian, bao
lâu đổi một lần), và hai quy tắc «chưa rõ» của đề xuất 2 khác nhau ra sao. Đây là **mô tả**, không đo dự
báo.

Cách làm: sự kiện `LIQ_RUN_*` và `SHIFT_*` của `ict_structure` (0.2.0, tham số mặc định; 0.3.0 không đổi
hai loại này) trên bốn cấu hình của đoạn phát triển. Trạng thái sau mỗi nến chỉ đổi theo sự kiện đã xác
nhận ở chính nến đó. Script [`research/orderflow_rules.py`](../../research/orderflow_rules.py), kết quả
[`khao_sat/orderflow_rules_dev.json`](khao_sat/orderflow_rules_dev.json).

| Quy tắc | Định nghĩa |
|---|---|
| run + shift | sự kiện đặt chiều; hai chiều ngược nhau cùng nến → chưa rõ |
| **A** (đã chốt) | shift đặt chiều ngay; run cùng chiều giữ nguyên; run **ngược** chiều đang có → chưa rõ; từ chưa rõ, sự kiện kế tiếp (run hoặc shift) đặt chiều; hai chiều cùng nến → chưa rõ |
| B(N) (đã bỏ) | như run + shift, nhưng nến nào mà trong N nến gần nhất (tính cả nến đó) có cả `LIQ_RUN_UP` lẫn `LIQ_RUN_DOWN` → chưa rõ |
| A + B(N) | áp B lên kết quả của A |

Quy ước đo:

* «/ngày» = mỗi **ngày giao dịch** (`so_ngay_giao_dich` của lõi, theo lịch phiên) — xem §8.4;
* **đoạn** = dãy nến liên tiếp cùng trạng thái; bỏ đoạn khởi động trước sự kiện đầu tiên; tính cả đoạn
  cuối đang mở;
* **đổi chiều** = một đoạn tăng/giảm khác chiều đoạn tăng/giảm liền trước (có thể đi qua chưa rõ);
* TV = trung vị độ dài đoạn (phần tử giữa của dãy đã sắp), đổi ra giờ;
* «chưa rõ %» gồm cả khởi động. `ict_structure` 0.3.0 tách phần này thành «chưa có».

### 8.1. Run + shift và quy tắc A

| Dữ liệu (run / shift mỗi ngày) | Quy tắc | tăng % | giảm % | chưa rõ % | đổi chiều / ngày | đoạn chưa rõ / ngày | chưa rõ TV giờ | một chiều TV giờ |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| XAUUSD M15 `ds_db1583cd4dde` 01–08/2024 (2.08 / 0.87) | run + shift | 54.5 | 43.5 | 2.0 | 1.34 | 0.02 | 19.5 | 12.8 |
| | **A** | 46.1 | 29.8 | 24.1 | 0.72 | 0.64 | 6.2 | 13.2 |
| XAUUSD M15 `ds_a5212fd37814` 2018–2023 (2.11 / 0.87) | run + shift | 51.7 | 47.4 | 0.9 | 1.29 | 0.02 | 6.5 | 13.2 |
| | **A** | 40.8 | 37.2 | 21.9 | 0.77 | 0.62 | 5.8 | 13.0 |
| EURUSD M15 `ds_a9a2a5e4cef5` 2018–2023 (2.26 / 0.93) | run + shift | 50.9 | 48.2 | 0.9 | 1.40 | 0.03 | 7.0 | 13.0 |
| | **A** | 40.4 | 37.6 | 21.9 | 0.82 | 0.66 | 6.2 | 13.0 |
| XAUUSD M5 `ds_933fa5ec67e2` 01–08/2024 (6.35 / 2.51) | run + shift | 54.0 | 44.4 | 1.6 | 4.01 | 0.08 | 5.3 | 4.1 |
| | **A** | 43.0 | 32.2 | 24.8 | 2.22 | 1.99 | 1.9 | 4.2 |

* Quy tắc A chuyển khoảng 1/5 thời gian sang «chưa rõ» (22–25%), lấy từ cả hai chiều. Số lần đổi chiều thật
  giảm 40–46% (M15: 1.29–1.40 → 0.72–0.82 mỗi ngày giao dịch).
* Đoạn một chiều vẫn dài ~13 giờ (trung vị) ở M15, ~4 giờ ở M5. Đoạn «chưa rõ» M15 dài trung vị ~6 giờ,
  ~0.6 đoạn mỗi ngày giao dịch.
* «Chưa rõ» của run + shift chỉ đến từ hai chiều cùng nến (và khởi động) nên hiếm: 0.02–0.03 đoạn mỗi ngày
  ở M15. Trung vị của nó (19.5 giờ ở XAUUSD 2024) chỉ tính trên vài đoạn.

### 8.2. Quy tắc B gần như không xảy ra

| Dữ liệu | chưa rõ % — run + shift / B(4) / B(8) / B(16) | đoạn chưa rõ / ngày — run + shift / B(4) / B(8) / B(16) | A + B(8) so với A |
|---|---|---|---|
| XAUUSD M15 01–08/2024 | 2.0 / 2.0 / 2.0 / 2.3 | 0.02 / 0.02 / 0.03 / 0.08 | trùng mọi số |
| XAUUSD M15 2018–2023 | 0.9 / 0.9 / 0.9 / 1.4 | 0.02 / 0.02 / 0.04 / 0.11 | trùng mọi số |
| EURUSD M15 2018–2023 | 0.9 / 0.9 / 0.9 / 1.4 | 0.03 / 0.03 / 0.04 / 0.12 | đoạn chưa rõ 0.67 (A: 0.66) mỗi ngày; một chiều TV 12.8 (A: 13.0) giờ |
| XAUUSD M5 01–08/2024 | 1.6 / 1.6 / 1.6 / 2.1 | 0.08 / 0.08 / 0.12 / 0.34 | trùng mọi số |

Ở M15, B thêm nhiều nhất 0.09 đoạn chưa rõ mỗi ngày và 0.5 điểm % thời gian «chưa rõ» (N = 16); N = 4 ra
cùng số với run + shift ở độ chính xác của bảng. Số đổi chiều gần như không đổi (1.29 → 1.28 ở XAUUSD
2018–2023 với N = 16). Hai phía cùng bị **run** trong vài nến là chuyện hiếm, nên ghép B vào A gần như
không đổi gì. → **Bỏ B** (OF2).

### 8.3. Quy tắc A: «chưa rõ» vào bằng gì, kết thúc ra sao

| Dữ liệu | số đoạn chưa rõ | vào: run ngược chiều / hai chiều cùng nến | kết thúc: quay lại chiều cũ / sang chiều mới | thoát bằng run / shift |
|---|---:|---|---|---|
| XAUUSD M15 01–08/2024 | 110 | 97.3% / 2.7% | 49.5% / 50.5% | 69.7% / 30.3% |
| XAUUSD M15 2018–2023 | 958 | 96.7% / 3.3% | 43.7% / 56.3% | 71.8% / 28.2% |
| EURUSD M15 2018–2023 | 1034 | 97.5% / 2.5% | 45.5% / 54.5% | 69.8% / 30.2% |
| XAUUSD M5 01–08/2024 | 344 | 97.1% / 2.9% | 46.9% / 53.1% | 73.5% / 26.5% |

«Chiều cũ» = chiều của đoạn tăng/giảm ngay trước đoạn chưa rõ. Tỷ lệ kết thúc tính trên các đoạn đã kết
thúc; đoạn còn mở ở cuối dữ liệu (1 đoạn ở ba cấu hình) không tính. «Thoát bằng shift» = nến kết thúc có
shift cùng chiều mới; không thì là run.

* Khi «chưa rõ» kết thúc, sang chiều mới nhỉnh hơn quay lại chiều cũ (50–56% so với 44–50%), tức hơi
  nghiêng về chiều của run đã gây «chưa rõ». Đây là mô tả trên đoạn phát triển, không phải phép đo dự báo
  (không có mốc ngẫu nhiên như §4).
* Sang chiều mới chủ yếu bằng run (73–82% số lần); quay lại chiều cũ có tỷ lệ shift cao hơn (33–41%).

### 8.4. Đơn vị «/ngày»: ngày giao dịch và ngày UTC có nến

| Dữ liệu | ngày giao dịch | ngày UTC có nến | run + shift: lật / ngày UTC có nến | run + shift: lật / ngày giao dịch | đổi chiều thật / ngày giao dịch: run + shift · A |
|---|---:|---:|---:|---:|---:|
| XAUUSD M15 01–08/2024 | 173 | 208 | 1.12 | 1.35 | 1.34 · 0.72 |
| XAUUSD M15 2018–2023 | 1548 | 1859 | 1.08 | 1.30 | 1.29 · 0.77 |
| EURUSD M15 2018–2023 | 1557 | 1874 | 1.18 | 1.42 | 1.40 · 0.82 |
| XAUUSD M5 01–08/2024 | 173 | 208 | 3.38 | 4.06 | 4.01 · 2.22 |

«Lật» đếm như `orderflow_survey.py`: nến có trạng thái tăng/giảm khác nến trước, gồm cả lúc từ «chưa rõ»
quay về chiều cũ, nên nhỉnh hơn «đổi chiều thật». Cột «ngày UTC có nến» tái lập đúng `lat_moi_ngay` của
[`khao_sat/orderflow_survey_dev.json`](khao_sat/orderflow_survey_dev.json) (khảo sát đó dùng
`ds_a5212fd37814` cho XAUUSD M15 2024; con số trùng). Một ngày giao dịch ≈ 1.20 ngày UTC có nến ở cả bốn
cấu hình.

## 9. Tái lập

```powershell
.\.venv\Scripts\python.exe research\orderflow_survey.py --json docs\research\khao_sat\orderflow_survey_dev.json
.\.venv\Scripts\python.exe research\orderflow_rules.py --json docs\research\khao_sat\orderflow_rules_dev.json
```

Cả hai đọc `data/lab.sqlite` chỉ đọc (`--db` để chỉ tới bản sao khác) và từ chối khoảng chạm đoạn kiểm tra
(cần `--allow-test`). JSON ghi dataset, checksum, phiên bản thuật toán, định nghĩa và toàn bộ ô kết quả;
`orderflow_survey` thêm bảng hiệu chuẩn, `orderflow_rules` thêm `script_sha256` (nó dùng chung `load` với
`orderflow_survey.py`).

Bản `orderflow_rules_dev.json` hiện có chạy với sự kiện của `ict_structure` 0.2.0 (06/10/2026). Chạy lại với
0.3.0 ra đúng cùng mọi số (đã kiểm cùng ngày) vì 0.3.0 không đổi run/shift.
