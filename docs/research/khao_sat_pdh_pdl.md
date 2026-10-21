# Khảo sát: xác suất chạm PDH / PDL so với vùng ICT và biên range

Ngày 21/10/2026. Script [`research/khao_sat_pdh_pdl.py`](../../research/khao_sat_pdh_pdl.py) (`pdh-pdl-survey-v1.1`),
số liệu đầy đủ [`khao_sat/pdh_pdl_dev.json`](khao_sat/pdh_pdl_dev.json). Plan: [`plan_ket_hop_ict_indicator.md`](../plans/plan_ket_hop_ict_indicator.md)
§5 bước 2, [`plan_nhan_dien_trang_thai.md`](../plans/plan_nhan_dien_trang_thai.md) bước 2. Chỉ dữ liệu dev
(XAUUSD, EURUSD M15, 2018 – 08/2024), database chỉ đọc.

## 1. Kết luận

1. **PDH / PDL không cần hiệu chỉnh riêng.** Tỷ lệ chạm thật lệch kỳ vọng (một mức bất kỳ cùng khoảng cách, cùng giờ
   NY) từ −0,3 tới +0,4 điểm %, dưới ngưỡng 1 điểm khai trước ở cả hai mã, cả hai tầm. Mô hình khoảng cách của lõi đã
   đúng chuẩn cho PDH / PDL; bảng hiệu chuẩn 10 nhóm nằm sát đường chéo. Brier tốt hơn B0 (mẫu chung mọi giờ) 5–11%.
2. **PDH / PDL «trung tính», vùng ICT hơi bị né.** Vùng thanh khoản gần nhất bị chạm ít hơn kỳ vọng 0,25–1,0 điểm (XAU
   có ý nghĩa ở cả 1h, 4h; EUR ở 1h), khớp khảo sát trước. PDH / PDL không có hiệu ứng đó (PDH −0,3 tới +0,3, PDL +0,2 tới +0,4).
3. **Biên range đúng chuẩn**, nhưng mẫu nhỏ (≈ 2 700 dự báo mỗi mã): chênh −1,0 tới +1,8 điểm, CI rộng ±2–5 điểm.
4. **Giả thuyết cho bước sau (không khai trước — chỉ ghi lại):** khi PDH / PDL cách giá 1–2 ATR, chúng bị chạm nhiều
   hơn kỳ vọng +0,5 tới +4,9 điểm — dương ở cả 8 ô (2 mã × PDH / PDL × 1h / 4h), 4 ô có CI không chứa 0. Khi cách
   < 0,5 ATR thì phần lớn ngược lại: −4 tới −8 điểm ở 5/8 ô (4 ô có ý nghĩa), nhưng mỗi ô chỉ vài trăm dự báo. Vì phần
   lớn dự báo PDH / PDL ở xa (trung vị 7–8 ATR), hiệu ứng tổng gần 0. Muốn dùng phải khai trước rồi kiểm trên đoạn test.

## 2. Cách đo

- Chạy `ict_structure` 0.8.0 (lớp nhận diện bật). Ghi lại mọi dự báo chạm mà lõi tự chấm trong lần chạy (`PriceBand._grade`,
  phép thử `price_band.touched`) — không tính lại gì ngoài lõi; số dự báo và tỷ lệ chạm mỗi (tầm, loại mức) được đối
  chiếu với `run_stats` của chính lần chạy.
- **Mức:** vùng thanh khoản còn nguyên gần nhất mỗi phía (`vung_tren` / `vung_duoi`), PDH / PDL còn nguyên ở đúng phía
  giá (`pdh` / `pdl`), biên range khi đang range.
- **Kỳ vọng** = p của lõi = tỷ lệ mẫu biên (cùng giờ NY, theo ATR) ≥ khoảng cách hiện tại. **Chênh** = tỷ lệ chạm thật
  − kỳ vọng trung bình; > 0 → loại mức đó hút giá hơn một mức bất kỳ.
- CI 95% bootstrap khối tuần (tuần ISO của ngày giao dịch NY của nến dự báo, như các khảo sát trước; 1 000 lần). Dự báo ở các nến liền
  nhau chồng lấn kết cục, nên n thô không dùng để kết luận.
- **Quy tắc khai trước:** thêm hiệu chỉnh riêng cho PDH / PDL chỉ khi ở cả hai mã, ít nhất một tầm, |chênh| ≥ 1 điểm và
  CI không chứa 0. Kết quả: không mã nào đạt → không hiệu chỉnh.

## 3. Bảng chính

Chênh = chạm thật − kỳ vọng, điểm %, kèm CI 95%. n = số dự báo đã chấm.

| Mã | Tầm | Vùng trên | Vùng dưới | PDH | PDL | Biên trên | Biên dưới |
|---|---|---|---|---|---|---|---|
| XAU | 1h | −0,76 [−1,01; −0,50] | −0,51 [−0,75; −0,26] | +0,07 [−0,07; +0,23] | +0,31 [+0,18; +0,44] | −0,9 [−3,2; +1,5] | +0,3 [−1,8; +2,4] |
| XAU | 4h | −0,96 [−1,56; −0,29] | −0,83 [−1,50; −0,18] | −0,29 [−0,83; +0,36] | +0,29 [−0,18; +0,78] | +1,7 [−2,8; +6,5] | −0,1 [−4,9; +4,4] |
| EUR | 1h | −0,32 [−0,58; −0,07] | −0,33 [−0,55; −0,11] | +0,16 [+0,00; +0,32] | +0,21 [+0,07; +0,36] | +0,6 [−1,7; +2,9] | −1,0 [−2,8; +1,0] |
| EUR | 4h | −0,25 [−0,93; +0,45] | −0,43 [−1,03; +0,17] | +0,31 [−0,23; +0,84] | +0,39 [−0,11; +0,92] | +1,8 [−2,5; +5,9] | −0,0 [−3,7; +3,9] |

Tỷ lệ chạm thật của PDH / PDL: ≈ 3% trong 1h, ≈ 10–11% trong 4h (n ≈ 105–120 nghìn mỗi ô). Vùng gần nhất: 13–14% /
32–34%. Biên range: 23–27% / 46–52%.

**PDH / PDL theo khoảng cách** (chênh, điểm %; in đậm khi CI không chứa 0):

| Mã · mức · tầm | 0–0,5 ATR | 0,5–1 | 1–2 | 2–4 | ≥ 4 |
|---|---|---|---|---|---|
| XAU PDH 1h | +1,5 | +1,6 | +1,6 | +0,3 | **−0,1** |
| XAU PDL 1h | **−6,4** | +2,4 | **+4,9** | **+1,1** | −0,0 |
| XAU PDH 4h | −0,5 | +1,1 | +0,7 | +0,0 | **−0,4** |
| XAU PDL 4h | −4,2 | +2,2 | **+4,9** | +1,5 | −0,1 |
| EUR PDH 1h | **−4,4** | −0,8 | **+2,0** | +0,6 | +0,0 |
| EUR PDL 1h | **−8,0** | −0,5 | **+2,0** | **+0,9** | +0,0 |
| EUR PDH 4h | −0,0 | −2,3 | +1,7 | +1,3 | +0,1 |
| EUR PDL 4h | **−5,5** | −0,3 | +0,5 | +1,3 | +0,3 |

Mỗi ô 0–0,5 ATR chỉ có 235–585 dự báo; ô ≥ 4 ATR có 82–95 nghìn. Có 40 ô nên vài ô «có ý nghĩa» có thể do ngẫu nhiên;
điểm đáng chú ý là dấu dương lặp lại ở 1–2 ATR.

## 4. Trong lab

`ict_structure` 0.8.0 (đặc tả [`thuat_toan_nhan_dien.md`](../algorithms/thuat_toan_nhan_dien.md)):

- PDH / PDL còn nguyên ở đúng phía giá vào danh sách mức có xác suất chạm (đường chấm «PDH chạm 1h …% · 4h …%»; trùng
  giá với vùng gần nhất thì một đường).
- Lõi tự chấm mỗi loại mức: Brier, B0, tỷ lệ chạm thật, kỳ vọng và chênh (`ty_le_cham`, `p_tb`, `chenh`), 10 nhóm hiệu
  chuẩn. Ô Brier gộp (`cham_tong`) giữ tập mức như 0.7.0 (vùng gần nhất + biên range): PDH / PDL phần lớn ở xa (p ≈ 0),
  gộp vào sẽ kéo Brier gộp xuống ≈ 30% mà dự báo không tốt hơn.
- Tab Thống kê có ô «PDH / PDL — chạm thật − kỳ vọng». Tooltip của mức ghi chạm thật / kỳ vọng tới nến đang xem.

Tái lập (≈ 1 phút):

```
.\.venv\Scripts\python.exe research\khao_sat_pdh_pdl.py --json docs\research\khao_sat\pdh_pdl_dev.json
```
