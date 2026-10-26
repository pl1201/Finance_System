# Khảo sát: Order Block và OTE (bước 0 của plan kết hợp)

Ngày: 21/10/2026. Thuộc [`plan_ket_hop_ict_indicator.md`](../plans/plan_ket_hop_ict_indicator.md) §3.4 và §5 bước 0.

- Script: [`research/khao_sat_ob_ote.py`](../../research/khao_sat_ob_ote.py) (`ob-ote-survey-v1.1`, ≈ 1,5 phút)
- Kết quả đầy đủ: [`khao_sat/ob_ote_dev.json`](khao_sat/ob_ote_dev.json)
- Sự kiện: `ict_structure` 0.5.0, tham số mặc định (OB-T neo SHIFT, `ob_lui` 5, hạn 96 nến; OTE 62–79%, nhịp ≥ 2 ATR).
- Khung đo dùng lại của [`khao_sat_ict_indicator.md`](khao_sat_ict_indicator.md): nến hợp lệ, kết cục ±1 ATR, đúng hướng
  cân bằng (BA), CI bootstrap khối tuần, null dịch vòng, BH.

Đây không phải tín hiệu giao dịch: không có P&L, không có win rate. Phạm vi: XAUUSD và EURUSD M15, 2018 – 08/2024
(đoạn phát triển). Đoạn kiểm tra (từ 01/09/2024) vẫn khoá. Luật, ngưỡng và cách dựng vùng giả được khai báo ở đầu script
trước khi chạy; chỗ nào thêm sau khi xem kết quả đều ghi rõ.

---

## 1. Kết luận ngắn

1. **K17–K27 không đoán được hướng 1–4 giờ.**
   - Chạm OB-T lần đầu (K17): XAUUSD 52,8% (1h), 53,0% (4h), CI [49,8; 56,2] vẫn chứa 50%. EURUSD 49,4% và 49,1%.
   - Vào OTE lần đầu (K22): 49,4–51,0% ở cả hai mã.
   - Không luật lọc nào hơn luật cha. Chênh từ −1,1 đến +1,6 điểm, mọi CI chứa 0.
   - Null dịch vòng + BH trên 40 phép thử đủ mẫu: **0/40 qua**.
   - Hiệu ứng nhỏ nhất thấy được (MDE80) là 4–5 điểm cho K17/K22 và 6–8 điểm cho luật lọc. Ngưỡng hoà vốn cần ≈ +9 điểm,
     nên mẫu đủ để loại các luật này.
   - K18, K20, K23 **không đủ mẫu** (69–130 sự kiện trong gần 7 năm). Bias H1 = H4 cùng chiều với OB, hay RSI ở vùng
     quá mua/bán đúng lúc chạm OB, rất hiếm.
   - Đối chứng OB-R và OB-D: 48,6–50,9%. Riêng OB-D có 4 100–4 600 sự kiện, MDE 2 điểm, và đúng 50%.
2. **OB giữ giá tốt hơn vùng giả cạnh nó khoảng 7 điểm. Lý do là vị trí ở chân nhịp, không phải «nến ngược màu cuối».**
   - Thước đo: tại lần chạm đầu, P(giá đi +1 ATR theo chiều OB trước khi close vượt mép xa).
   - OB thật: XAUUSD 63,2%, EURUSD 59,7%. So với vùng giả cùng bề rộng của chính OB đó: **+6,9 [4,5; 9,3]** và
     **+7,2 [4,8; 9,6]** điểm.
   - Chẩn đoán thêm sau khi xem kết quả (§4) tách theo vị trí của vùng giả:
     - vùng giả gần trùng OB: chênh +0,7 và +1,1, CI chứa 0;
     - vùng giả nông hơn (nằm trong nhịp, gần giá hơn): OB thật hơn 13 điểm;
     - vùng giả sâu hơn (xa giá hơn): OB thật **kém** 7 điểm.
   - Nghĩa là vùng càng gần chân nhịp displacement thì càng giữ giá. OB chỉ là một cách chọn vùng ở chân nhịp.
3. **OTE 62–79% không có gì đặc biệt.**
   - Ở mọi dải độ sâu hồi, P(vượt đầu nhịp trong 4 giờ) khớp kỳ vọng của một mức bất kỳ cùng khoảng cách. Chênh từ −2,3
     đến +1,0 điểm, mọi CI chứa 0.
   - So dải 62–79% với các dải khác: XAUUSD −2,1 [−4,4; +0,4], EURUSD +0,1 [−2,6; +2,7].
   - Xác suất nhịp đi tiếp chỉ phụ thuộc khoảng cách tới đầu nhịp tính bằng ATR. Khảo sát trước cũng thấy điều này ở vùng
     thanh khoản.
4. **Lõi 0.5.0 khớp với mô phỏng độc lập.** Vòng đời OB viết lại trong script cho cùng nến xác nhận và cùng nến chạm đầu
   với sự kiện của lõi ở 100% OB (1 259 OB XAUUSD, 1 397 OB EURUSD).

## 2. Đề xuất quyết định (cần bạn duyệt)

| Mục | Đề xuất | Vì sao |
|---|---|---|
| K17–K27 (hướng) | **Bỏ**, không đưa vào bộ nhận diện như tín hiệu hướng | BA 49–53%, 0/40 qua null + BH, không luật lọc nào hơn cha |
| Lớp OB / OTE trên chart | Giữ như hiện tại: **lớp mô tả**, ghi «chưa phải tín hiệu» | Người dùng vẫn cần thấy cấu trúc ICT; không gọi là dự báo |
| OB như «mức có thể giữ giá» | Chưa dùng. Nếu muốn, khai báo một phép đo mới: «vùng ở chân nhịp sau SHIFT» theo khoảng cách tới cực trị cú quét, thay cho nến OB | Ưu thế của OB đến từ vị trí (§4); đo trực tiếp vị trí sẽ gọn hơn, ít tham số hơn |
| OTE | Chỉ là lớp mô tả. Không thêm vào luật, không thêm vào mô hình học | Không hơn một mức bất kỳ cùng khoảng cách |
| Đặc trưng OB / OTE cho mô hình học (plan §3.4, ý thứ ba) | **Không làm riêng.** Gộp vào lần chấm lại mô hình ở bước 3 nếu bạn vẫn muốn | Phần A và C không thấy thông tin hướng hay đi tiếp; khảo sát trước cho thấy thêm cấu trúc làm dải giá kém đi |

## 3. Phần A · K17–K27

Đúng hướng cân bằng (%) tại nến sự kiện. «Ít mẫu» = một phía có < 100 sự kiện hợp lệ. Cha của K17 và K22 là «SHIFT
trong 4 giờ qua» (BA 50,4–50,8%); cha của các luật lọc là K17 hoặc K22.

| Mã | Luật | Sự kiện XAU / EUR | XAU 1h | XAU 4h | EUR 1h | EUR 4h | Chênh với cha 4h (XAU / EUR) | MDE80 4h |
|---|---|---|---|---|---|---|---|---|
| K17 | OB-T chạm lần đầu → theo chiều OB | 999 / 1095 | 52,8 | 53,0 | 49,4 | 49,1 | +2,2 [−0,9; 5,3] / −1,6 [−4,8; 1,4] | 4,5 / 4,2 |
| K18 | K17 ∧ bias ICT H1 = H4 cùng chiều | 71 / 92 | ít mẫu | ít mẫu | ít mẫu | ít mẫu | — | — |
| K19 | K17 ∧ bias EMA H1 = H4 cùng chiều | 327 / 347 | 52,4 | 52,2 | 48,6 | 50,6 | −0,8 [−5,5; 3,9] / +1,5 [−2,4; 5,7] | 8,1 / 7,4 |
| K20 | K17 ∧ RSI M15 ≤ 40 (OB tăng) / ≥ 60 (OB giảm) | 118 / 130 | ít mẫu | ít mẫu | ít mẫu | ít mẫu | — | — |
| K21 | K17, chỉ OB của SHIFT có FVG | 598 / 621 | 52,5 | 52,4 | 50,4 | 50,4 | −0,6 [−3,0; 1,9] / +1,3 [−1,5; 4,1] | 6,0 / 5,9 |
| K22 | Vào OTE lần đầu → theo chiều SHIFT | 1050 / 1164 | 49,4 | 50,4 | 51,0 | 50,1 | −0,4 [−3,3; 2,6] / −0,6 [−3,9; 2,6] | 4,3 / 4,5 |
| K23 | K22 ∧ bias ICT H1 = H4 cùng chiều | 69 / 92 | ít mẫu | ít mẫu | ít mẫu | ít mẫu | — | — |
| K24 | K22 ∧ bias EMA H1 = H4 cùng chiều | 339 / 369 | 49,6 | 51,9 | 50,6 | 49,2 | +1,5 [−2,7; 6,1] / −0,9 [−5,3; 3,1] | 7,9 / 7,2 |
| K25 | K22 ∧ OB-T cùng SHIFT giao vùng OTE | 890 / 994 | 49,4 | 50,7 | 50,7 | 49,6 | +0,3 [−1,1; 1,6] / −0,5 [−1,8; 0,8] | 5,0 / 5,0 |
| K26 | K22 ∧ ADX H1 ≥ 25 | 433 / 518 | 49,2 | 50,3 | 52,8 | 51,7 | −0,1 [−3,7; 3,4] / +1,6 [−1,5; 4,4] | 6,4 / 6,2 |
| K27 | K22 trong killzone London 02–05 / NY sáng 07–10 (giờ NY) | 536 / 575 | 50,0 | 49,3 | 49,7 | 49,5 | −1,1 [−3,8; 1,6] / −0,7 [−3,6; 2,1] | 5,9 / 6,0 |
| K17R | Như K17, OB-R (nến cuối, cả râu) — đối chứng | 1136 / 1260 | 50,9 | 50,9 | 49,0 | 48,6 | −2,1 [−5,3; 1,1] / −0,6 [−3,7; 2,5] | 4,5 / 4,0 |
| K17D | Như K17, OB-D (neo mọi displacement) — đối chứng | 4085 / 4615 | 49,1 | 50,1 | 50,1 | 50,1 | −2,9 [−6,0; 0,2] / +0,9 [−2,1; 4,0] | 2,2 / 2,2 |

Ghi chú:

- K17 XAUUSD là số cao nhất của họ này (p null 0,07 ở 4h, q BH 0,96). Nó không lặp lại ở EURUSD và không hơn cha
  có ý nghĩa.
- K25 gần như trùng K22: 85% lần vào OTE có OB-T cùng shift giao vùng OTE. Vì thế điều kiện «hợp lưu OB + OTE» gần
  như không lọc gì.

## 4. Phần B · OB thật so với vùng giả

Thước đo, tại lần chạm đầu τ (sau khi OB đã xác nhận):

- close\[τ\] vượt mép xa → 0;
- sau đó, nến đầu tiên có high ≥ mép gần + ATR\[τ\] (OB tăng) → 1, close vượt mép xa → 0;
- chưa rõ sau 32 nến, hoặc có khoảng trống > 3 giờ → bỏ.

Vùng giả: cùng bề rộng với OB, tâm ở giữa thân một nến khác trong 10 nến trước d (không thuộc OB). Vùng giả đi cùng
vòng đời với OB thật: xác nhận khi vượt đầu xa, lần chạm đầu, hạn 96 nến, SHIFT ngược chiều.

| | XAUUSD | EURUSD |
|---|---|---|
| Số OB-T | 1 259 | 1 397 |
| Tỷ lệ được chạm: OB thật / vùng giả | 86,7% / 62,8% | 85,8% / 60,6% |
| Giữ giá: OB thật | 63,2% [60,3; 66,2] (n 1 038) | 59,7% [57,0; 62,6] (n 1 153) |
| Giữ giá: vùng giả | 60,5% [58,1; 62,8] | 57,3% [55,0; 59,6] |
| **Cùng OB: thật − giả** | **+6,9 [4,5; 9,3]** (n 930, MDE80 3,4) | **+7,2 [4,8; 9,6]** (n 1 043, MDE80 3,4) |

**Chẩn đoán thêm sau khi xem kết quả (v1.1, không khai trước).** Mỗi cặp (OB, vùng giả) được xếp theo độ lệch của
tâm vùng giả so với tâm OB, tính bằng bề rộng OB. Dương nghĩa là vùng giả sâu hơn: dưới OB tăng, trên OB giảm.

| Vị trí vùng giả | XAUUSD: thật − giả | EURUSD: thật − giả |
|---|---|---|
| Sâu hơn (> 0,25) | **−7,0 [−11,9; −2,1]** (717 cặp) | **−7,1 [−12,0; −2,2]** (812 cặp) |
| Gần trùng (\|lệch\| ≤ 0,25) | +0,7 [−0,9; 2,3] (1 502 cặp) | +1,1 [−0,7; 3,2] (1 682 cặp) |
| Nông hơn (< −0,25) | +13,2 [9,5; 16,8] (3 141 cặp) | +12,6 [9,1; 16,2] (3 409 cặp) |

Trong 10 nến trước displacement, phần lớn vùng giả nằm nông hơn OB, tức là trong thân nhịp. Vì vậy trung bình nghiêng
về OB thật. Khi so với vùng ở cùng chỗ, OB không hơn. Khi so với vùng ở sâu hơn, OB kém.

## 5. Phần C · OTE so với các độ sâu hồi khác

Mỗi nhịp sau SHIFT dùng gốc X của sự kiện OTE và đầu H = cực trị từ d (nến t dùng H của nến t − 1). Mỗi lần độ sâu
lớn nhất sang dải mới, và nhịp ≥ 2 ATR, ghi một quan sát. Cột «Vượt H» là P(vượt đầu nhịp trong 4 giờ). Cột «Kỳ vọng»
là P(biên 4 giờ ≥ cùng khoảng cách) của mọi nến hợp lệ cùng giờ NY × tam phân vị ATR/giá.

| Dải độ sâu | XAU n | XAU KC trung vị (ATR) | XAU vượt H / kỳ vọng | XAU chênh | EUR n | EUR vượt H / kỳ vọng | EUR chênh |
|---|---|---|---|---|---|---|---|
| 0–38% | 904 | 0,50 | 83,5 / 82,5 | +1,0 [−1,2; 3,3] | 942 | 85,2 / 84,4 | +0,9 [−1,3; 3,0] |
| 38–50% | 767 | 1,21 | 59,5 / 60,5 | −1,0 [−4,1; 1,9] | 732 | 61,1 / 61,5 | −0,4 [−3,4; 2,4] |
| 50–62% | 724 | 1,66 | 50,8 / 50,0 | +0,8 [−2,4; 3,9] | 731 | 49,8 / 50,8 | −1,0 [−4,0; 2,1] |
| **62–79% (OTE)** | 804 | 2,09 | 39,1 / 41,3 | −2,3 [−5,2; 0,6] | 846 | 44,4 / 44,5 | −0,1 [−2,9; 2,6] |
| 79–100% | 709 | 2,75 | 30,9 / 32,9 | −2,0 [−5,0; 1,0] | 819 | 36,6 / 37,2 | −0,6 [−3,5; 2,3] |

So chênh của dải OTE với chênh của dải khác:

- XAUUSD: so với 50–62% là −3,1 [−6,4; 0,2]; so với 79–100% là −0,3 [−3,4; 2,9]; so với mọi dải khác là
  −2,1 [−4,4; 0,4];
- EURUSD: lần lượt +0,9 [−2,7; 4,2], +0,5 [−2,8; 3,5] và +0,1 [−2,6; 2,7].

## 6. Giới hạn

- Chỉ đo tham số mặc định của 0.5.0. Không tinh chỉnh `ob_lui`, hạn, dải OTE trên dev, để tránh chọn tham số theo
  kết quả.
- Thước đo «giữ giá» ở phần B có rào lệch: đích là mép gần + 1 ATR, dừng là close qua mép xa. Nó chỉ dùng để so OB thật
  với vùng giả theo cùng một quy tắc, không phải tỷ lệ thắng.
- Phần chẩn đoán vị trí ở §4 được thêm sau khi xem kết quả. Nó giải thích kết quả, không phải phép thử khai trước.
  Nếu dùng «chân nhịp» làm mức, phải khai báo lại và đo riêng.
- Quan sát ở phần C chồng lấn trong cùng nhịp (mỗi nhịp có tối đa 5 quan sát). CI bootstrap theo tuần đã tính phần
  phụ thuộc này.
