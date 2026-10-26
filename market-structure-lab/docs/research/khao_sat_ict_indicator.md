# Khảo sát: kết hợp indicator + ICT cho bộ nhận diện trạng thái

Ngày: 21/10/2026. Thuộc [`plan_nhan_dien_trang_thai.md`](../plans/plan_nhan_dien_trang_thai.md): §6 và §7 bước 2, 2b, 4.

- Script: [`research/ict_indicator_survey.py`](../../research/ict_indicator_survey.py)
- Hình: [`research/ve_ict_indicator.py`](../../research/ve_ict_indicator.py)
- Kết quả đầy đủ: [`khao_sat/ict_indicator_dev.json`](khao_sat/ict_indicator_dev.json)

Đây không phải tín hiệu giao dịch: không có P&L, không có win rate. Phạm vi:

- XAUUSD và EURUSD M15, 2018 – 08/2024. Chỉ đoạn phát triển; đoạn kiểm tra (từ 01/09/2024) vẫn khoá.
- Tầm H = 1 giờ (4 nến) và 4 giờ (16 nến), đúng khung đã chốt: bias H1/H4, đích M15, vào lệnh M5.
- Đặc trưng ở nến t chỉ dùng thông tin ≤ t. H1/H4 chỉ lấy nến đã đóng.
- Danh sách tín hiệu, kết hợp và siêu tham số được khai báo trước khi chạy.

---

## 1. Kết luận ngắn

1. **Đoán hướng 1–4 giờ: không tín hiệu nào gần mức dùng được.**
   - Tín hiệu đơn (ICT hay indicator) đúng hướng 49–51,5%.
   - Kết hợp tốt nhất đạt 52–53%.
   - Để hoà vốn sau phí với rào ±1 ATR M15 cần khoảng 59% (hình 1).
2. **Kết hợp luật: có hai kết hợp nhỉnh hơn, nhưng mỗi kết hợp chỉ thấy ở một mã.**
   - **ICT top-down H4 = H1 = order flow** (K04) trên XAUUSD: 52,3% (1h), 52,5% (4h), chỉ có ý kiến ở 7% số nến.
     - Lọc thêm bằng EMA H1 (K05) hoặc ADX H1 ≥ 25 (K06): 52,6–52,8%, độ phủ còn 4–6%.
     - EURUSD: 50,6–51,7%, CI chứa 50%.
   - **Sweep ∧ RSI ≤ 35 / ≥ 65** (K09) trên EURUSD: 51,7% (1h), 52,0% (4h).
     - Hơn sweep đơn 1,4–1,7 điểm %; dương ở 6/7 năm.
     - XAUUSD không có hiệu ứng: 49,6% và 50,2%.
3. **Thống kê.**
   - Theo luật khai trước (null dịch vòng + BH trên 148 phép thử): **0/148 qua**.
   - Null 199 độ dịch không cho được p < 0,005, nên luật này rất khắt khe. Vì vậy mình kiểm thêm bằng p từ bootstrap (sau
     lần chạy đầu, ghi rõ ở hình 1 bằng dấu †): 4/148 qua — K09 EURUSD 1h và 4h, K14 EURUSD 4h, +DI > −DI M15
     XAUUSD 1h. Cả bốn đều không lặp lại ở mã còn lại.
   - Số phép thử có p < 0,05 là 26/148, trong khi ngẫu nhiên chỉ khoảng 7. Vậy có cấu trúc thật, nhưng rất nhỏ
     (0,5–2,5 điểm %) và đổi dấu giữa hai mã: indicator động lượng nhỉnh dương ở XAUUSD 1h, nhưng âm ở EURUSD 4h.
4. **Bias H1/H4 (bước 2b): là bối cảnh, không phải thông tin hướng 1–4 giờ.**
   - Thứ tự cấu trúc ICT H1/H4: 49,4–50,6%. EMA50/200 H1/H4: 50,2–50,7%.
   - H1 và H4 cùng chiều: ICT 50,7–51,2%, EMA 50,3–50,9%.
5. **Kết hợp bằng mô hình học (walk-forward 2020 – 08/2024): ICT và indicator không thêm gì vào nền.**
   - Nền = giờ, thứ, biên độ và lợi suất gần, ATR tương đối.
   - AUC hướng: 0,505–0,521. Chênh khi thêm ICT, indicator hay cả hai: −0,005 đến +0,003, mọi CI chứa 0.
   - AUC trạng thái «đi một chiều» 1–4 giờ: 0,504–0,527, thêm gì cũng không tăng (hình 4).
6. **Dải giá 80% là phần đoán được thật, và cấu trúc làm nó kém đi.**
   - Giờ trong ngày (B1) tốt hơn dải cố định (B0) 12–17%.
   - Thêm biến động gần (nền) được thêm 1,2–1,9 điểm.
   - Thêm ICT hay indicator làm điểm **giảm**: ở 4h giảm 1,4–3,3 điểm, có ý nghĩa. Dải hẹp lại nhưng độ phủ 4h tụt
     từ 77–79% xuống 73–77%, tức là mô hình học thuộc dữ liệu cũ.
7. **Vùng thanh khoản ICT gần nhất không «hút» giá (bước 2, phần vùng).**
   - Xác suất chạm vùng thấp hơn xác suất chạm một mức bất kỳ cùng khoảng cách, cùng giờ, cùng biến động:
     0,2–1,0 điểm % (XAUUSD 1h, phía trên: −0,75 [−1,02; −0,49]).
   - Khi vùng ở rất gần (< 0,5 ATR): thấp hơn tới 4 điểm (hình 5).
   - Xác suất chạm gần như chỉ phụ thuộc khoảng cách tính bằng ATR.

## 2. Đã thử những gì

| Phần | Nội dung |
|---|---|
| A · luật đơn (21) | ICT (timeline `ict_structure` 0.4.2): thứ tự H4, H1, M15; order flow; phía DOL; pd_bias; shift/sweep trong 4 giờ; discount/premium M15, H4. Indicator: EMA50/200 (M15, H1, H4), +DI/−DI (M15, H1), RSI > 50, RSI ≤ 30/≥ 70, MACD hist (M15, H1), phá kênh Donchian 20 (M15, H1) |
| A · luật kết hợp (16) | Đồng thuận (K01–K05, K11, K12, K15); lọc ADX (K06–K08, K10); hợp lưu oscillator (K09); discount/premium theo bias ICT hoặc EMA (K13, K14); bỏ phiếu 8 thành phần (K16). Mỗi kết hợp được so cặp với tín hiệu ICT «cha» |
| A · thước đo | Đúng hướng cân bằng = ½·[P(lên trước \| +1) + P(xuống trước \| −1)]. Hướng = chạm +1 ATR trước −1 ATR. Trôi giá không làm lệch: vô ích thì ra 50% |
| B · mô hình học | HistGradientBoosting, siêu tham số cố định. Bốn bộ đặc trưng: Nền, Nền + indicator (33), Nền + ICT (40), Nền + cả hai (66). Học các năm trước, chấm năm sau (2020, …, 2024) |
| B · ba đầu ra | Hướng (AUC); «đi một chiều» = ER tương lai ≥ phân vị 2/3 của 2018–2019 (AUC); dải giá = phân vị 90% của biên lên và biên xuống (pinball, độ phủ chung) |
| C · vùng ICT | `liq_above` / `liq_below` so với mức bất kỳ cùng khoảng cách, cùng giờ NY, cùng tam phân vị ATR/giá |
| Thống kê | CI bootstrap theo tuần (348 tuần). Null dịch vòng 199 độ dịch. BH trên toàn bộ phép thử luật |

## 3. Số chính

**Đúng hướng (%), các dòng đáng chú ý** — đủ 37 dòng × 2 mã × 2 tầm ở hình 1 và JSON.

| Tín hiệu | Phủ | XAU 1h | XAU 4h | EUR 1h | EUR 4h |
|---|---|---|---|---|---|
| Thứ tự ICT H4 | 56% | 50,6 | 50,6 | 50,1 | 50,5 |
| Thứ tự ICT H1 | 55% | 49,7 | 49,4 | 50,3 | 50,5 |
| EMA50 > EMA200 H4 | 100% | 50,2 | 50,5 | 50,2 | 50,7 |
| K01 ICT H1 = H4 | 16% | 50,9 | 50,8 | 50,7 | 51,2 |
| K04 ICT top-down H4=H1=OF | 7% | **52,3** | **52,5** | 50,6 | 51,3 |
| K05 top-down ∧ EMA H1 | 6% | **52,6** | **52,6** | 50,8 | 51,3 |
| K06 top-down ∧ ADX H1 ≥ 25 | 4% | **52,7** | **52,8** | 50,7 | 51,7 |
| K09 Sweep ∧ RSI ≤ 35 / ≥ 65 | 14% | 49,6 | 50,2 | **51,7** | **52,0** |
| K14 Discount/premium theo bias EMA | 35% | 49,9 | 50,5 | 50,7 | **51,6** |
| Mức hoà vốn sau phí (rào ±1 ATR M15) | | 59,5 | 59,5 | 58,5 | 58,5 |

**Mô hình học (ngoài mẫu 2020 – 08/2024).** Mỗi ô ghi bốn giá trị theo thứ tự Nền / + indicator / + ICT / + cả hai.

| Đầu ra | XAU 1h | XAU 4h | EUR 1h | EUR 4h |
|---|---|---|---|---|
| AUC hướng | 0,511 / 0,510 / 0,511 / 0,508 | 0,511 / 0,507 / 0,511 / 0,505 | 0,519 / 0,521 / 0,521 / 0,519 | 0,516 / 0,518 / 0,519 / 0,517 |
| AUC «đi một chiều» | 0,508 / 0,504 / 0,506 / 0,504 | 0,526 / 0,524 / 0,527 / 0,522 | 0,512 / 0,511 / 0,508 / 0,510 | 0,517 / 0,514 / 0,516 / 0,518 |
| Dải giá: điểm hơn B0 (%) | 13,4 / 13,2 / 13,2 / 13,2 | 14,7 / 12,4 / 13,5 / 11,9 | 15,7 / 15,1 / 15,1 / 15,1 | 17,7 / 15,5 / 16,0 / 15,4 |
| Dải giá: độ phủ thật (%) | 79 / 78 / 78 / 78 | 79 / 76 / 77 / 75 | 78 / 77 / 77 / 77 | 77 / 74 / 74 / 73 |

Hai mốc để so dải giá:

- B1 (chỉ giờ trong ngày) hơn B0 11,8 / 13,7 / 14,5 / 16,8% và phủ 79–81%.
- Bề rộng trung bình của dải 80% theo «Nền»: khoảng 4,3 ATR M15 cho 1 giờ và 9,4 ATR cho 4 giờ (XAUUSD).

**Xác suất chạm vùng ICT gần nhất theo khoảng cách.** Mỗi ô ghi «thực tế» / «mức bất kỳ», %, XAUUSD, vùng phía trên.

| Khoảng cách | 0–0,5 ATR | 0,5–1 | 1–2 | 2–4 | ≥ 4 |
|---|---|---|---|---|---|
| 1 giờ | 74,1 / 76,3 | 46,5 / 48,4 | 22,3 / 23,2 | 5,8 / 6,5 | 0,6 / 0,8 |
| 4 giờ | 87,8 / 89,2 | 72,7 / 73,7 | 52,8 / 53,4 | 27,4 / 28,7 | 7,1 / 7,9 |

## 4. Ý nghĩa cho bộ nhận diện

- **Khoảng giá («đi trong giá nào»):** lấy mô hình biến động làm lõi: giờ trong ngày + biến động gần, rồi tới B2
  (Log-HAR/EWMA) và hiệu chỉnh độ phủ bằng conformal. Cấu trúc ICT và indicator không giúp thu hẹp dải. Đây là câu
  trả lời sơ bộ cho «câu hỏi quyết định» ở plan §6.
- **Mức sẽ chạm:** xác suất chạm tính từ khoảng cách (theo ATR), giờ và biến động. Bảng trên đã là đường hiệu chuẩn
  thô. Nhãn «vùng thanh khoản ICT» giúp chỉ ra mức nào đáng vẽ, nhưng không làm xác suất chạm cao hơn.
- **Trạng thái trend / range / sideway:** để ở mức **mô tả**. Với đặc trưng hiện có, chưa đoán trước được 1–4 giờ
  tới sẽ đi một chiều hay không (AUC ≤ 0,527).
  - Range có biên rõ (định nghĩa mới ở plan §3) chưa được thử. Bước 3 sẽ thử xem nó có làm dải giá lệch về một
    phía hay giữ giá trong biên không.
- **Hướng:** bias H1/H4 dùng làm bối cảnh hiển thị, không dùng làm dự báo.
  - Hai kết hợp đáng theo dõi: K04–K06 trên XAUUSD, K09 trên EURUSD. Chỉ nên kiểm lại **một lần** trên đoạn kiểm
    tra khi protocol được ký.
  - Không nên tối ưu thêm tham số của chúng trên dev, vì mỗi lần thử thêm làm tăng N và PBO.

## 5. Giới hạn

- Mới đo M15 với kết cục 1 và 4 giờ. Chưa đo vào lệnh M5, chưa đo TP/SL xa hơn ±1 ATR, chưa đo DC
  (`dc_atr_structure`), chưa đo range biên rõ.
- Siêu tham số mô hình học cố định, không tinh chỉnh. Có thể có cấu hình tốt hơn, nhưng mỗi lần thử phải ghi vào sổ
  thử.
- CI bootstrap theo tuần có thể hẹp hơn thật với tín hiệu kéo dài nhiều tuần (EMA H4, discount/premium). Null dịch
  vòng xử lý được việc này nhưng độ phân giải p chỉ tới 0,005.
- Xác suất của mô hình học chưa hiệu chỉnh: log-loss kém hơn tỷ lệ nền ở mọi mô hình. AUC là thước đo chính ở phần B.

## 6. Tái lập

```powershell
# từ thư mục market-structure-lab — khoảng 6 phút
.\.venv\Scripts\python.exe research\ict_indicator_survey.py --json docs\research\khao_sat\ict_indicator_dev.json
# hình (cần một Python có matplotlib)
python research\ve_ict_indicator.py
```

Chạy thử nhanh (khoảng 1 phút, không dùng để kết luận): thêm `--nhanh`.

Nguyên mẫu chart: `.\.venv\Scripts\python.exe research\chart_ket_hop.py` (cần JSON ở trên và Chrome hoặc Edge). Lệnh ghi
bốn trang HTML và ảnh chụp vào [`khao_sat/chart_ket_hop/`](khao_sat/chart_ket_hop/). Mở trang HTML để cuộn và zoom.
