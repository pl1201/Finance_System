# Khảo sát 4a: regime M15 — đo trước khi viết `ict_regime`

Ngày: 19/10/2026. Bước 4a của [`plan_bias_regime.md`](../plans/plan_bias_regime.md) §8 (Q1–Q7 dùng đúng đề xuất;
người dùng duyệt sau khi xem kết quả này). Script: [`research/regime_survey.py`](../../research/regime_survey.py);
kết quả đầy đủ: [`khao_sat/regime_survey_dev.json`](khao_sat/regime_survey_dev.json).

Không phải tín hiệu giao dịch, không có P&L hay win rate. Chỉ đoạn phát triển (mọi nến **trước 01/09/2024**); đoạn
kiểm tra vẫn khoá. Hai biến thể «kịch bản» / «điểm» là **nguyên mẫu cài ngay trong script**, chưa phải thuật toán
của lab. Mọi bộ phát hiện chỉ dùng thông tin ≤ t (đã tự kiểm, §3.3). Nhãn hậu kiểm và kết cục tương lai nhìn về sau
— chỉ dùng để chấm.

---

## 1. Kết luận ngắn

1. **Cổng đi/dừng: dừng trước 4b với bản nháp hiện tại.** Hai biến thể nháp có trung vị M4 (tuổi thọ còn lại sau
   phát hiện) **= 0** ở mọi nhãn tham chiếu, ở cả M15 lẫn H1, trên cả 5 bộ dữ liệu. Lý do chính: chúng ở Uncertain
   51–68% thời gian nên chỉ bắt được 11–41% số đoạn xu hướng tham chiếu (§5.6).
2. **Với nhịp ngắn, không bộ phát hiện nào qua 0.25** — kể cả baseline. Nhịp ngắn = DC θ ≤ 2 ATR, trend-scanning
   L ≤ 32; đoạn trung vị 6–19 nến M15 (1.5–5 giờ). Với nhịp dài (DC θ = 4 ATR, đoạn trung vị 40–60 nến M15
   ≈ 10–15 giờ), baseline đơn giản (ADX/SMA, thứ tự M15, order flow, ER) có trung vị M4 0.26–0.63. Nhưng M4 của
   chúng **thấp hơn** mốc dịch vòng (cùng độ bền, đặt ngẫu nhiên). Phần đoạn mà chúng **giữ đúng chiều** chỉ hơn
   mốc 3–11 điểm %.
3. **Chuyển sang H1 (phương án dự phòng của plan) đã đo: M4 tương đối không khá hơn.** Cùng mẫu hình như M15: nhịp
   ≤ 2 ATR đều dưới 0.25; θ = 4 ATR thì baseline 0.35–0.68, biến thể 0. Chỉ số giờ còn lại dài hơn 3–6 lần, vì nến
   dài hơn.
4. **Bằng chứng ICT không thêm thông tin đo được so với Kaufman ER (M6).** Chênh giữa biến thể có bằng chứng ICT và
   «điểm» chỉ G4 không vượt null ở phép đo nào: 0/84 ở dev (4 cặp so × 3 h × 7 kết cục), 0/18 ở dev mở rộng.
   Hiệu ứng nhỏ nhất phát hiện được trên 6 năm: ≈ 0.010 ER tương lai và ≈ 3 điểm % xác suất chạm +1 ATR trước. Hiệu ứng cỡ Osler (4–6 điểm %) sẽ thấy được nếu có; không
   thấy. Riêng M5: không trạng thái nào tách kết cục tương lai rõ hơn null. Số kết quả vượt null (2/177 ở dev,
   8/76 ở dev mở rộng) cỡ số dương tính giả kỳ vọng, dấu không nhất quán giữa mã và năm.
5. **Bốn nhóm bằng chứng không trùng nhau tới mức phải gộp** (|ρ| lớn nhất 0.49: G1 ~ ER có dấu). Hai chỗ nên sửa:
   `pd_bias` gần như không đổi G2 (ρ 0.92 giữa G2 có/không pd_bias); `dol_side` tương quan với `order_flow`
   (ρ 0.34–0.40), tức một phần G1 lọt vào G2.
6. **Range và Breakout của nháp gần như không hoạt động.** Range «kịch bản» chiếm 4.7% thời gian, đoạn trung vị 8
   nến (= H). Ở H = 8, 24% («kịch bản») và 41% («điểm») số nến Range chỉ còn ở Range **nhờ bộ đếm giữ tối thiểu
   H**; ở H = 16 là 41% và 52%. Range hiếm khi đủ N_r = 16 nến, nên Breakout chỉ có 5–7 lần trong 8 tháng, 8–16
   lần trong 6 năm — quá ít để chấm M7.
7. **Đường trễ ↔ lật gần như phẳng theo H.** Trễ chuyển chiều không đổi khi H từ 1 lên 64 nến, vì phản bác cứng
   (shift ngược, mức bảo vệ bị vượt) đến trước H. Quy tắc khuỷu khai trước vì vậy suy biến: nó luôn chọn H lớn nhất
   của lưới. Chi phí thật của H là trạng thái «cũ»; tôi đề xuất chọn H theo chi phí đó (§7).

---

## 2. Mục đích

Plan §8 dòng 4a, ba câu hỏi:

- Regime M15 có kéo dài đủ lâu **sau khi phát hiện** để router dùng được không? Đây là cổng đi/dừng.
- Bằng chứng ICT có thêm thông tin so với một chỉ số thống kê đơn giản (Kaufman ER) không?
- Số liệu nào để chốt ngưỡng nháp ở plan §4.7?

Sáu việc theo yêu cầu, ánh xạ sang mục kết quả:

| Việc | Nội dung | Mục |
|---|---|---|
| 1 | Baseline M1–M2 trên dataset đúng giờ + bằng chứng thô | §5.1 |
| 2 | Nhãn hậu kiểm (họ θ, họ L); M3, M4 | §5.2 |
| 3 | G1–G4: phân phối, tương quan | §5.3 |
| 4 | Hai biến thể nháp, lưới, đường trễ ↔ lật | §5.4 |
| 5 | M5–M6 sơ bộ, null shift test, MDE | §5.5 |
| 6 | Cổng đi/dừng M15, đo lại ở H1 | §5.6 |

---

## 3. Dữ liệu và cách tái lập

### 3.1. Dữ liệu

| Vai | Dataset | Khoảng | Nến | Ngày GD / tuần | Checksum dataset (đầu) |
|---|---|---|---:|---|---|
| Dev chính | XAUUSD M15 `ds_db1583cd4dde` | 01/01–31/08/2024 | 15 850 | 173 / 35 | `39428eac…` |
| Dev mở rộng | XAUUSD M15 `ds_a5212fd37814` | 2018–2023 | 141 742 | 1548 / 313 | `355c9beb…` |
| Dev mở rộng | EURUSD M15 `ds_a9a2a5e4cef5` | 2018–2023 | 149 402 | 1561 / 313 | `3be62fdd…` |
| Cổng H1 | XAUUSD H1 `ds_771a79d4d604` | 01/01–31/08/2024 | 3965 | 173 / 35 | `53175c3a…` |
| Cổng H1 | XAUUSD M15 `ds_a5212fd37814` gộp H1 (`utc_epoch`, phát cả giờ thiếu nến) | 2018–2023 | 35 545 | 1548 / 313 | `355c9beb…` |

- Checksum đầy đủ của dataset và của **đoạn** (`rows_checksum`) nằm trong `meta` từng khối JSON.
- Không dùng bộ lệch giờ `ds_564bff443e42`.
- Lịch phiên theo mã: `cme_globex_metals` cho XAUUSD, `fx_spot` cho EURUSD.
- Thuật toán của lab đã dùng: `ict_structure` 0.4.1, `dc_atr_structure` 0.2.0, `indicator_baseline` 1.0.0,
  `hmm_online` 1.0.0, tất cả với tham số mặc định (trừ HMM, §4).

### 3.2. Lệnh chạy

```powershell
# từ thư mục market-structure-lab; DB mở chế độ chỉ đọc (mode=ro)
.\.venv\Scripts\python.exe research\regime_survey.py --db <đường dẫn lab.sqlite> --json docs\research\khao_sat\regime_survey_dev.json
# chỉ dev chính, để thử nhanh (~25 s):
.\.venv\Scripts\python.exe research\regime_survey.py --quick --json <tệp tạm>.json
```

- `--db` mặc định là `data/lab.sqlite`, nhưng script luôn mở nó chỉ đọc. Lần chạy cho báo cáo này dùng một bản sao DB.
- Đoạn chạm 2024-09-01 bị từ chối nếu không có `--allow-test`. Lần chạy này **không** dùng `--allow-test`.
- Thời gian chạy đầy đủ: **142.5 s** (`meta.thoi_gian_chay_s`; một luồng; Python 3.11.9, numpy 2.4.6).
- Seed cố định: 7 cho bootstrap, 42 cho HMM.
- Hai lần chạy `--quick` liên tiếp cho JSON trùng nhau tuyệt đối (bỏ trường thời gian), và trùng phần dev chính của
  lần chạy đầy đủ.
- `meta.script_sha256` trong JSON khớp với bản script đã sinh ra nó.

### 3.3. Tự kiểm nhân quả

Chạy lại `ict_structure` cùng bốn biến thể trên prefix [0, cut), với cut = 4000, 9000, 13000. Chuỗi trạng thái trùng
lần chạy đủ: **0 nến khác**. Sửa giá mọi nến từ cut trở đi (+1%) cũng **không** đổi trạng thái trước cut (0 nến
khác). Kết quả ở `dev_chinh.kiem_tra_nhan_qua`.

Ngưỡng (phân vị dev, bảng F của ER) là tham số cố định, không tính lại trên prefix.

---

## 4. Định nghĩa đã chọn cho chỗ plan mơ hồ

Bản đầy đủ ở `dinh_nghia` trong JSON. Những chỗ ảnh hưởng tới số:

| Chỗ | Chọn | Vì sao / ảnh hưởng |
|---|---|---|
| Nhãn DC / Lunde–Timmermann | `DcDetector` của lab, close, Δ = θ·ATR[e] khoá tại cực trị. Chạy **liên tục** qua khoảng trống. Gán ngược: nến (e_i, e_{i+1}] mang chiều nhịp | Đúng họ θ của plan. DC không có trạng thái Range |
| Trend-scanning | OLS close theo nến trên [t, t+ℓ], ℓ ∈ [L/4, L]. Lấy ℓ có \|t\| lớn nhất; \|t\| ≥ 2 → ±1, còn lại 0 | t-value OLS bị thổi phồng do sai số tự tương quan. Nhãn 0 chỉ chiếm 3.8 / 0.7 / 0.1% nến (L = 16 / 32 / 64), mỗi đoạn 0 dài 1–3 nến. Không chấm được Range bằng nhãn này (§9) |
| Ranh giới, trễ (M3) | Đoạn (b, e, d): b = nến cuối đoạn trước. Trễ = k* − b, với k* là nến đầu trong [b, e] mà bộ phát hiện ở Trend d (trạng thái sau nến). Trễ 0 = đã đúng chiều từ trước | Trạng thái ở k* dùng được từ k*+1 |
| «Trễ chuyển» | Trễ chỉ trên các đoạn mà bộ phát hiện phải đổi chiều (k* > b) và có đổi trong đoạn | Dùng cho đường trễ ↔ lật (§5.4) |
| M4 | (e − k*)/(e − b); bỏ lỡ = 0 (đúng công thức plan). Báo thêm M4 trên đoạn phát hiện được, và M4 theo nến (Σ/Σ) | Trung vị M4 vì vậy phụ thuộc mạnh vào tỷ lệ phát hiện |
| M4 «giữ chiều» (thêm) | Phần (k*, e] mà trạng thái vẫn ở chiều d, chia (e − b). Null = cùng đại lượng trên chuỗi dịch vòng | Thêm sau lần chạy thử: M4 thường **dưới** mốc dịch vòng vì nó thưởng cho việc lật nhiều. Đại lượng này phạt việc lật ra rồi vào lại |
| Báo động giả | Lần vào Trend d mà nhãn ở nến kế tiếp ≠ d | — |
| F1 điểm đổi | Điểm tham chiếu (b, d) và điểm vào Trend (k, d), dung sai 8 / 32 nến. Dùng matcher `min_cost_v1` của lab, chia theo thành phần liên thông. Null = dịch vòng chuỗi điểm phát hiện (99 độ dịch) | Lab matcher và ghép tham lam cho cùng TP ở mọi ô (`TP_matcher_lab_khop_tham_lam`) |
| G1 | Trung bình có mặt của `order_flow` và `order` M15; `order` đặt 0 khi `protected_broken` | `last_shift` đã nằm trong order flow (shift lật order flow). Ở «kịch bản», `last_shift` chỉ dùng cho K5 |
| G2 | Thứ tự H1 (1), H4 (1), `dol_side` (None → 0, trọng số 1). Ở «điểm» thêm `pd_bias` trọng số 0.5 | Plan: pd_bias «trọng số nhỏ» |
| G3 | Trung bình 4 thành phần ∈ [0, 1]: (i) sweep cả BSL và SSL trong W nến mà không có run; (ii) độ rộng dealing range / ATR ∈ [a, b]; (iii) 1 − \|2·range_pos − 1\|; (iv) PDH và PDL đều chưa bị lấy | — |
| G4 | ER n = 32 trên close. Trong R dùng 1 − F_dev(ER), với F là phân phối của ER trên dev chính | Để cùng thang với G3. Trọng số đều chỉ có nghĩa khi cùng thang |
| «điểm» chỉ G4 | D = ER có dấu, R = 1 − F(ER). Không Breakout, không phản bác ICT | Mốc thống kê thuần cho M6 |
| «điểm» chỉ ICT | D như bản đủ, R = G3 | So thêm |
| Khởi động | `order` M15 = None, hoặc khung lớn chính chưa ready, hoặc chưa có ER/ATR. Dùng **chung** cho mọi biến thể | Để M6 so trên cùng tập nến |
| Dữ liệu thiếu | Trong G nến gần nhất có `ICT_GAP` bất thường, hoặc `HTF_BAR_DEGRADED` của H1/H4. Sau đó máy trạng thái bắt đầu lại | Chỉ 0.03% nến ở dev chính, 0.09–0.13% ở dev mở rộng |
| K2 ở «điểm» | Chặn **vào** Trend (như «kịch bản»). Trong lúc giữ H, chỉ phản bác cứng mới thoát | Plan chỉ nói K2 khi giữ |
| Phản bác cứng | Close vượt mức bảo vệ phía d; SHIFT ngược chiều xác nhận ở t; Dữ liệu thiếu. Với Range: Breakout, hoặc close ra ngoài biên ≥ k·ATR | — |
| Breakout | Vào: close ngoài biên ≥ k·ATR[t−1], hoặc xuyên biên ≥ 0.1·ATR cùng nến có displacement cùng chiều. Biên = dealing range lúc vào Range. Thất bại: LIQ_SWEEP có vùng ở biên, hoặc close quay lại trong biên trong m nến. Thành công: LIQ_RUN có vùng ở biên, hoặc STH/STL mới ngoài biên mà close vẫn ngoài. Quá m nến mà close quay lại, hoặc hết B nến → Uncertain | «Vùng ở biên» = mức ≥ biên − 0.5·ATR (lab chọn) |
| Range sau H nến | Giữ khi điều kiện Range còn đúng | Đây là lý do Range nhấp nháy (§5.4). Đã thử một tuỳ chọn khác trong lưới |
| HMM | 3 trạng thái, fit một lần trên 2000 nến đầu (≈ 3 tuần), rồi chỉ lọc forward | Mặc định 80 nến quá ngắn. Trạng thái không mang nghĩa → chỉ M1, M2 |
| M5 | Hiệu = trung bình nhóm A − nhóm B trong từng tam phân vị ATR_t/close, rồi lấy trung bình 3 tầng (bỏ tầng có nhóm < 30 nến). CI bootstrap khối tuần (1000 lần). Shift test: dịch vòng chuỗi trạng thái so với (kết cục, tầng ATR); các độ dịch đều nhau ≥ max(128, độ trễ ACF < 0.05) | MDE ≈ 2.8 × SE bootstrap (α 0.05 hai phía, lực 80%). «Vượt null» = p < 0.05 **và** CI 95% không chứa 0 |
| H1 | Tham số theo nến giữ nguyên. Khung lớn chính = H4 (không có khung phụ). Ngưỡng theo phân vị dev H1 2024, áp nguyên cho H1 2018–2023 | Plan: «cùng thuật toán, dataset H1» |
| Dev mở rộng | Dùng nguyên ngưỡng số của dev chính, kể cả với EURUSD (các ngưỡng đều không có đơn vị: × ATR, ER, phân vị) | Cấu hình chốt trên dev chính, đo độ bền ở chỗ khác (M11) |

---

## 5. Kết quả

### 5.1. Việc 1 — baseline M1, M2 (dev chính, đúng giờ)

Tỷ lệ thời gian tính trên nến có regime. «Khởi động» tính trên mọi nến.

| Bộ phát hiện | Trend ↑ | Trend ↓ | Range | Uncertain | Khởi động | Đổi / ngày | Đoạn TV (IQR) · P90 | % đoạn < 4 nến |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| `dc_regime` (reset) | 11.4 | 8.4 | 0.0 | 80.2 | 15.3 | 1.13 | 32 (14–53) · 78 | 4.3 |
| `dc_regime` (bridge_short 2h) | 27.1 | 23.1 | 0.0 | 49.8 | 3.5 | 2.69 | 21 (9–43) · 70 | 7.5 |
| `indicator_baseline` | 31.3 | 24.9 | 5.3 | 38.4 | 0.2 | 8.30 | 6 (2–16) · 27 | 36.9 |
| `hmm_online` (3 trạng thái: 54 / 31 / 15%) | — | — | — | — | 12.6 | 32.94 | 1 (1–2) · 5 | 85.5 |
| `order_flow` (thô) | 46.0 | 30.0 | — | 24.0 | 0.3 | 1.68 | 40 (19–76) · 120 | 6.2 |
| `order` M15 (thô) | 30.0 | 22.2 | — | 47.8 | 0.2 | 5.12 | 13 (7–24) · 39 | 9.7 |
| `htf_H1_order` (thô) | 31.3 | 24.8 | — | 43.9 | 1.1 | 1.40 | 50 (28–88) · 132 | 0.4 |
| `htf_H4_order` (thô) | 36.5 | 20.0 | — | 43.6 | 4.0 | 0.35 | 190 (136–324) · 492 | 0.0 |
| «kịch bản» nháp | 18.9 | 8.4 | 4.7 | 68.0 | 1.1 | 2.21 | 20 (8–48) · 100 | 8.6 |
| «điểm» nháp (G1–G4) | 22.9 | 11.0 | 15.0 | 51.0 | 1.1 | 5.47 | 8 (4–19) · 40 | 21.5 |
| «điểm» chỉ ICT (G1–G3) | 22.3 | 10.1 | 13.3 | 54.2 | 1.1 | 4.73 | 8 (5–22) · 46 | 16.8 |
| «điểm» chỉ G4 (ER) | 23.6 | 16.9 | 36.1 | 23.4 | 1.1 | 10.58 | 8 (3–9) · 15 | 25.5 |
| «không đổi» | — | — | — | — | — | 0 | cả đoạn | — |

Đọc bảng:

- **`dc_regime` trên dataset đúng giờ vẫn gần như không bao giờ ra Range (0.0%).** Số cũ ≤ 0.2% đo trên dataset
  lệch giờ được xác nhận: nguyên nhân là chính điều kiện Range, không phải lỗi giờ.
- `dc_regime` reset: «chưa rõ» chiếm 80%, khởi động 15% (warm-up lại sau mỗi khoảng trống). Ở H1, bản reset gần như
  vô dụng: khởi động 61%, Uncertain 100%.
- HMM lật 33 lần/ngày, 86% đoạn ngắn hơn 4 nến. Trạng thái không có nghĩa nên không chấm M3–M5.
- Dev mở rộng cho cùng thứ tự độ lớn. Ví dụ «kịch bản»: Uncertain 70.6% (XAU) / 70.3% (EUR), đổi 2.31 / 2.28 lần/ngày.
  «điểm»: Uncertain 53.6 / 53.4%, đổi 5.46 / 5.66 lần/ngày. Order flow: đổi 1.67 / 1.80 lần/ngày.

### 5.2. Việc 2 — nhãn hậu kiểm, M3, M4

**Thang của nhãn** (độ dài đoạn tăng / giảm, trung vị, tính bằng nến của khung chạy):

| Nhãn | Dev chính: số đoạn · TV (nến) | ≈ giờ ở M15 | XAU 18–23: số đoạn · TV | EUR 18–23: số đoạn · TV | XAU H1 2024: số đoạn · TV |
|---|---|---:|---|---|---|
| DC θ = 1 ATR | 1909 · 7 / 6 | 1.6 | 17 304 · 6 / 6 | 18 697 · 6 / 6 | 443 · 8 / 5 |
| DC θ = 2 ATR | 724 · 19 / 13 | 4 | 6640 · 16 / 15 | 7290 · 14 / 14 | 207 · 18 / 13 |
| DC θ = 4 ATR | 248 · 61 / 39 | 12 | 2068 · 55 / 47 | 2272 · 51 / 52 | 65 · 59 / 34 |
| trend-scanning L = 16 | 2000 · 7 / 5 | 1.5 | 18 841 · 6 / 6 | 19 754 · 6 / 6 | 508 · 7 / 6 |
| trend-scanning L = 32 | 920 · 14 / 11 | 3 | 8403 · 12 / 12 | 8918 · 12 / 12 | 254 · 12 / 9 |
| trend-scanning L = 64 | 430 · 27 / 24 | 6 | 3936 · 27 / 24 | 4362 · 24 / 23 | 103 · 35 / 24 |

Cỡ mẫu hiệu dụng là **số đoạn**, không phải số nến. Ở dev chính, θ = 4 chỉ có 248 đoạn; ở H1 2024 chỉ có 65.

**M3, M4 trên dev chính.** Bảng dưới cho DC θ = 2, DC θ = 4 và trend-scanning L = 64. DC θ = 1, L = 16 và L = 32 ở
JSON; ở ba nhãn đó, trung vị M4 = 0 với mọi bộ phát hiện.

Ý nghĩa các cột:

- «Phát hiện» = tỷ lệ đoạn mà bộ phát hiện có lúc ở đúng chiều.
- «Giữ chiều» = phần đoạn router thật sự ở đúng chiều sau khi phát hiện. Trong ngoặc: mốc dịch vòng (trung vị) và p
  một phía.
- «F1@8» = F1 điểm đổi, dung sai 8 nến. Trong ngoặc: null trung bình / P95.

DC θ = 2 ATR (724 đoạn):

| Bộ phát hiện | Phát hiện | M4 TV | M4 theo nến | Giữ chiều (null · p) | Trễ chuyển TV / P90 | Báo động giả | F1@8 (null TB / P95) |
|---|---:|---:|---:|---|---|---:|---|
| `dc_regime` (reset) | 0.18 | 0 | 0.17 | 0.08 (0.09 · 0.68) | 9 / 38 | 0.49 | 0.16 (0.12 / 0.16) |
| `dc_regime` (bridge) | 0.41 | 0 | 0.36 | 0.23 (0.25 · 0.78) | 9 / 46 | 0.50 | 0.23 (0.19 / 0.21) |
| `indicator_baseline` | 0.58 | 0.13 | 0.46 | 0.33 (0.29 · 0.02) | 14 / 28 | 0.29 | 0.24 (0.30 / 0.33) |
| `order_flow` | 0.51 | 0 | 0.45 | 0.41 (0.39 · 0.06) | 4 / 43 | 0.30 | 0.22 (0.15 / 0.18) |
| `order` M15 | 0.47 | 0 | 0.43 | 0.26 (0.27 · 0.92) | 19 / 40 | 0.52 | 0.22 (0.28 / 0.31) |
| `htf_H1_order` | 0.35 | 0 | 0.36 | 0.28 (0.28 · 0.52) | 16 / 51 | 0.59 | 0.10 (0.11 / 0.13) |
| `htf_H4_order` | 0.32 | 0 | 0.30 | 0.28 (0.28 · 0.60) | 17 / 54 | 0.36 | 0.02 (0.03 / 0.04) |
| «kịch bản» | 0.21 | 0 | 0.20 | 0.15 (0.14 · 0.10) | 6 / 48 | 0.40 | 0.15 (0.10 / 0.12) |
| «điểm» (G1–G4) | 0.27 | 0 | 0.22 | 0.19 (0.17 · 0.16) | 14 / 44 | 0.30 | 0.15 (0.14 / 0.17) |
| «điểm» chỉ G4 | 0.41 | 0 | 0.30 | 0.24 (0.21 · 0.02) | 22 / 35 | 0.29 | 0.15 (0.25 / 0.28) |
| «luôn tăng» | 0.50 | 0.5 | 0.55 | 0.55 | — | — | 0 |
| «không đổi» | 0 | 0 | 0 | 0 | — | — | 0 |

DC θ = 4 ATR (248 đoạn):

| Bộ phát hiện | Phát hiện | M4 TV | M4 TV (đoạn phát hiện) | M4 theo nến | Giữ chiều (null · p) | Trễ chuyển TV / P90 | Báo động giả | F1@8 (null TB / P95) |
|---|---:|---:|---:|---:|---|---|---:|---|
| `dc_regime` (reset) | 0.35 | 0 | 0.55 | 0.30 | 0.09 (0.09 · 0.20) | 38 / 121 | 0.42 | 0.08 (0.10 / 0.15) |
| `dc_regime` (bridge) | 0.54 | 0.11 | 0.75 | 0.51 | 0.26 (0.24 · 0.20) | 39 / 78 | 0.42 | 0.07 (0.13 / 0.17) |
| `indicator_baseline` | 0.85 | **0.59** | 0.69 | 0.69 | 0.39 (0.28 · 0.02) | 17 / 43 | 0.28 | 0.13 (0.17 / 0.20) |
| `order_flow` | 0.63 | **0.40** | 0.95 | 0.57 | 0.44 (0.39 · 0.04) | 19 / 70 | 0.34 | 0.23 (0.11 / 0.15) |
| `order` M15 | 0.69 | **0.48** | 0.70 | 0.62 | 0.30 (0.27 · 0.02) | 29 / 58 | 0.44 | 0.07 (0.17 / 0.20) |
| `htf_H1_order` | 0.46 | 0 | 1.0 | 0.47 | 0.29 (0.28 · 0.34) | 33 / 111 | 0.51 | 0.06 (0.09 / 0.12) |
| `htf_H4_order` | 0.34 | 0 | 1.0 | 0.32 | 0.26 (0.29 · 0.88) | 49 / 105 | 0.50 | 0.01 (0.03 / 0.06) |
| «kịch bản» | 0.29 | 0 | 0.90 | 0.32 | 0.17 (0.14 · 0.06) | 24 / 95 | 0.38 | 0.16 (0.08 / 0.12) |
| «điểm» (G1–G4) | 0.40 | 0 | 0.71 | 0.37 | 0.21 (0.17 · 0.02) | 26 / 77 | 0.31 | 0.12 (0.11 / 0.14) |
| «điểm» chỉ ICT | 0.38 | 0 | 0.71 | 0.36 | 0.20 (0.17 · 0.04) | 26 / 74 | 0.30 | 0.12 (0.10 / 0.14) |
| «điểm» chỉ G4 | 0.70 | **0.26** | 0.52 | 0.52 | 0.29 (0.21 · 0.02) | 31 / 63 | 0.24 | 0.04 (0.16 / 0.18) |
| «luôn tăng» | 0.50 | 0.5 | 1.0 | 0.57 | 0.57 | — | — | 0 |

trend-scanning L = 64 (430 đoạn, chỉ 419 đoạn có hướng):

| Bộ phát hiện | Phát hiện | M4 TV | M4 theo nến | Giữ chiều (null · p) | Trễ chuyển TV |
|---|---:|---:|---:|---|---:|
| `indicator_baseline` | 0.58 | **0.28** | 0.54 | 0.28 (0.29 · 0.70) | 33 |
| `order_flow` | 0.53 | 0.15 | 0.54 | 0.37 (0.39 · 0.82) | 29 |
| `order` M15 | 0.55 | 0.21 | 0.56 | 0.27 (0.26 · 0.34) | 13 |
| «kịch bản» | 0.24 | 0 | 0.25 | 0.14 (0.14 · 0.40) | 25 |
| «điểm» (G1–G4) | 0.30 | 0 | 0.31 | 0.18 (0.17 · 0.32) | 34 |
| «điểm» chỉ G4 | 0.40 | 0 | 0.38 | 0.19 (0.21 · 0.82) | 47 |

Đọc bảng:

- **Trung vị M4 bị chi phối bởi tỷ lệ phát hiện.** Bộ phát hiện bỏ lỡ hơn nửa số đoạn thì trung vị = 0, dù khi bắt
  được thì còn nhiều. Ví dụ «kịch bản», θ = 4: trên đoạn phát hiện được, M4 trung vị 0.90.
- **M4 thưởng cho việc lật nhiều.** Trên θ = 4, mốc dịch vòng của M4 *cao hơn* quan sát: `indicator_baseline` 0.59
  so với 0.71; `order` M15 0.48 so với 0.67; `order_flow` 0.40 so với 0.64. Lý do: bộ phát hiện nhân quả bắt đầu mỗi
  đoạn ở **chiều cũ** (vì còn theo đoạn trước) nên mất phần đầu; chuỗi cùng độ bền đặt ngẫu nhiên không chịu thiệt này.
- **«Giữ chiều» cho thấy có khớp, nhưng nhỏ.** Trên θ = 4 (θ = 2 với vài bộ), hơn mốc dịch vòng 3–11 điểm % (p ≤
  0.06): `indicator_baseline` +11, «điểm» chỉ G4 +8, `order_flow` +5, «điểm» +4, «kịch bản» +3 (p 0.06). Trên
  trend-scanning, không bộ nào hơn mốc.
- **Trễ chuyển chiều** (trung vị): 4–6 nến (order flow, «kịch bản») tới 14–22 nến («điểm», ADX, ER) trên DC θ = 2;
  17–49 nến trên θ = 4. Thang so sánh: đoạn θ = 2 dài trung vị 13–19 nến, θ = 4 dài 39–61 nến.
- **F1 điểm đổi thấp (≤ 0.3 ở dung sai 8 nến) và phần lớn bằng null.**
  - F1@8 vượt P95 của null ở một số ô trên nhãn DC: `order_flow` (θ = 1, 2, 4; θ = 4: 0.23 so với null 0.11 / P95
    0.15), «kịch bản» (θ = 1, 2, 4), `dc_regime` (θ = 1, 2).
  - Trên trend-scanning, chỉ có một ô vượt (`dc_regime` reset, L = 64). F1@32 bằng null ở mọi ô.
  - Cách đọc hợp lý: điểm vào Trend của các bộ dựa trên order flow / DC rơi gần cực trị DC vì **cùng phản ứng với một
    cú đảo chiều giá**. Đó là khớp thời điểm có cơ chế, không phải dự báo.
  - Baseline «không đổi» cho R = F1 = 0. Mọi bộ đều «thắng» nó, nên F1 phải đọc cạnh null.
- Matcher `min_cost_v1` của lab và ghép tham lam cho cùng TP ở mọi ô (không có thành phần liên thông nào quá lớn).
- **M4 cho Range** (Range bên trong các đoạn 0 của trend-scanning): không đo được. Đoạn 0 dài 1–3 nến; trung vị M4 = 0
  với mọi bộ có Range.

### 5.3. Việc 3 — bốn nhóm bằng chứng G1–G4 (dev chính)

Phân phối (trên nến không phải Khởi động; mọi nhóm có giá trị ở 98.9% số nến):

| Nhóm | P10 · P25 · P50 · P75 · P90 | Trung bình | Ghi chú |
|---|---|---:|---|
| G1 (hướng khung chạy) | −0.5 · −0.5 · 0 · 0.5 · 1 | +0.12 | 5 giá trị; ≠ 0 ở 75% số nến |
| G2 (hướng khung lớn, có pd_bias) | −0.43 · −0.14 · 0.14 · 0.43 · 0.43 | +0.08 | ≠ 0 ở mọi nến |
| G3 (đi ngang) | 0.11 · 0.30 · 0.44 · 0.62 · 0.73 | 0.45 | Thành phần (tỷ lệ = 1): sweep hai phía không run 19%; độ rộng trong [a, b] 60%; PDH/PDL đều chưa lấy 50%; 1 − \|2·range_pos − 1\| trung bình 0.49 |
| G4 (ER, n = 32) | 0.03 · 0.08 · 0.16 · 0.27 · 0.38 | 0.19 | — |

Tương quan Spearman. Cột «dev» kèm CI 95% bootstrap khối tuần (200 lần); hai cột mở rộng chỉ có điểm ước lượng:

| Cặp | Dev chính (CI 95%) | XAU 18–23 | EUR 18–23 |
|---|---|---:|---:|
| G1 ~ G2 | 0.25 (0.15; 0.33) | 0.21 | 0.21 |
| G1 ~ ER có dấu | **0.49** (0.43; 0.53) | 0.50 | 0.50 |
| G2 ~ ER có dấu | 0.10 (0.04; 0.16) | 0.04 | 0.04 |
| G3 ~ G4 (ER) | −0.37 (−0.41; −0.34) | −0.38 | −0.37 |
| \|G1\| ~ G3 | −0.06 (−0.12; −0.01) | −0.06 | −0.06 |
| \|G2\| ~ G3 | 0.09 (0.01; 0.16) | 0.01 | 0.04 |
| \|G1\| ~ \|G2\| | −0.03 (−0.08; 0.05) | 0.01 | −0.01 |
| G2 ~ G2 không pd_bias | **0.92** (0.90; 0.93) | 0.92 | 0.92 |

Tương quan giữa các thành phần (dev chính / XAU 18–23 / EUR 18–23):

- `order_flow ~ dol_side`: 0.40 / 0.38 / 0.34. DOL được đặt sau mỗi shift, mà shift cũng lật order flow.
- `htf_H1_order ~ dol_side`: −0.20 / −0.22 / −0.24.
- `order_flow ~ order` (đã đặt 0 khi mức bảo vệ bị vượt): 0.15–0.18.
- `H1 ~ H4`: 0.03–0.06.
- Các thành phần của G3 với nhau: |ρ| ≤ 0.08.

Khử trùng lặp — đề xuất:

- **Không cặp nhóm nào có |ρ| ≥ 0.7**, nên không cần gộp nhóm.
- G1 chia khoảng 1/4 phương sai hạng với ER có dấu (ρ² ≈ 0.24). Ở «điểm», G4 chỉ vào R, không vào D, nên không bị đếm
  hai lần. Giữ như vậy.
- **Bỏ `pd_bias` khỏi G2** (hoặc ghi rõ nó vô hiệu): G2 có và không có nó tương quan 0.92.
- **Chuyển `dol_side` từ G2 sang G1, hoặc bỏ.** DOL sinh từ cùng shift với order flow (ρ ≈ 0.4), nên là bằng chứng
  khung chạy lọt vào nhóm khung lớn. Nó còn ngược với H1 (ρ ≈ −0.2), làm G2 yếu đi.
- G3 ~ ER −0.37: hai «phiếu đi ngang» của R có liên quan vừa phải nhưng không trùng. Giữ cả hai.

### 5.4. Việc 4 — hai biến thể nháp

Tham số nháp plan §4.7: G = 4, W = 48, S = 4, N_r = 16, k = 0.25, B = 12, m = 4, H = 8, c = 1, n = 32.

Ngưỡng theo phân vị của dev chính:

| Ngưỡng | Giá trị |
|---|---|
| [a, b] = P20–P80 của độ rộng dealing range / ATR | 3.48–6.89 ATR |
| ER thấp (K3) = P50 | ≤ 0.164 |
| «điểm» θ_vào / θ_ra / ρ (phân vị 0.7 / 0.5 / 0.8) | 0.464 / 0.321 / 0.669 |
| «điểm» chỉ G4: θ_vào / θ_ra / ρ | 0.246 / 0.164 / 0.800 |
| H1 dev: [a, b] | 3.83–7.32 ATR |
| H1 dev: ER thấp | ≤ 0.18 |
| H1 dev: «điểm» θ_vào / θ_ra / ρ | 0.50 / 0.35 / 0.675 |

**Lý do Uncertain** (% số nến Uncertain):

- «kịch bản» (dev chính; XAU 18–23 và EUR 18–23 gần như y hệt):
  - K6 «không đủ bằng chứng» 63.5%;
  - K4 «xung đột khung» 25.2%;
  - K2 «DOL ngược» 8.9%;
  - K2 «mức bảo vệ bị vượt» 1.9%;
  - K5 «shift chưa đi tiếp» 0.5%.
- «điểm»:
  - không hướng, không biên 58.6%;
  - hướng chưa đủ 32.7%;
  - có hướng nhưng đi ngang 3.1%;
  - K2 5.6%.

**Range và Breakout:**

- Range «kịch bản» 4.7% thời gian. Đoạn Range: trung vị 8 nến, P90 17 — tức gần đúng bằng H.
- Breakout cả 8 tháng: «kịch bản» 5 lần, thất bại 3; «điểm» 7 lần, thất bại 5.
- Dev mở rộng 6 năm: 8–16 lần mỗi biến thể.
- Đa số Breakout kết thúc sau 1–3 nến.

**Lưới H × c** (các tham số khác nháp).

- Trễ chuyển, phát hiện: so với DC θ = 2.
- «Giữ nhờ H» = phần nến Trend / Range mà điều kiện giữ đã sai, chỉ còn nhờ bộ đếm H.

«kịch bản»:

| H | c | Trễ chuyển | Phát hiện | Đổi / ngày | % đoạn < 4 | Range % | Uncertain % | Giữ nhờ H: Trend / Range |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 1 | 6.0 | 0.21 | 2.51 | 24.0 | 3.6 | 69.3 | 0 / 0 |
| 4 | 1 | 6.0 | 0.21 | 2.36 | 11.0 | 4.2 | 68.7 | 0.2 / 13.8 |
| 8 | 1 | 6.0 | 0.21 | 2.21 | 8.6 | 4.7 | 68.0 | 0.8 / 24.3 |
| 8 | 2 | 6.5 | 0.21 | 2.19 | 7.9 | 4.7 | 68.7 | 0.8 / 24.3 |
| 8 | 4 | 8.0 | 0.20 | 2.16 | 6.9 | 4.7 | 70.1 | 0.9 / 24.3 |
| 16 | 1 | 6.0 | 0.21 | 2.17 | 11.1 | 6.0 | 66.0 | 3.4 / 40.8 |
| 32 | 1 | 6.0 | 0.22 | 2.06 | 11.5 | 7.1 | 62.6 | 10.7 / 52.1 |
| 64 | 1 | 6.0 | 0.24 | 1.91 | 15.0 | 8.5 | 56.4 | 24.0 / 60.2 |

«điểm»:

| H | c | Trễ chuyển | Phát hiện | Đổi / ngày | % đoạn < 4 | Range % | Uncertain % | Giữ nhờ H: Trend / Range |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 1 | 13.0 | 0.27 | 7.29 | 47.3 | 9.1 | 57.4 | 0 / 0 |
| 4 | 1 | 14.0 | 0.27 | 6.27 | 23.0 | 12.1 | 54.3 | 0.4 / 25.4 |
| 8 | 1 | 14.0 | 0.27 | 5.47 | 21.5 | 15.0 | 51.0 | 1.7 / 40.7 |
| 8 | 2 | 15.0 | 0.25 | 5.33 | 19.8 | 15.1 | 53.9 | 1.8 / 40.6 |
| 8 | 4 | 17.0 | 0.21 | 5.08 | 20.1 | 15.2 | 58.4 | 1.2 / 40.7 |
| 16 | 1 | 15.0 | 0.27 | 4.76 | 20.1 | 18.2 | 47.1 | 4.8 / 51.7 |
| 32 | 1 | 13.0 | 0.27 | 4.31 | 23.2 | 20.6 | 41.9 | 11.5 / 60.0 |
| 64 | 1 | 12.5 | 0.28 | 3.71 | 24.7 | 20.8 | 36.6 | 19.9 / 62.7 |

**Đường trễ ↔ lật:**

- Trễ chuyển **không đổi theo H**: 6 nến («kịch bản») và 12.5–15 nến («điểm») với mọi H từ 1 tới 64. Lý do: phản bác
  cứng (shift ngược, close vượt mức bảo vệ) đến trước khi hết H.
- c thêm khoảng 0.5–1 nến trễ cho mỗi nến xác nhận thêm. c cũng giảm tỷ lệ phát hiện (0.27 → 0.21 ở «điểm») và chỉ
  bớt 1–7% số lần đổi.
- Quy tắc khuỷu khai trước (biên Pareto, điểm xa dây cung nhất) chọn H = 64 (c = 1 «kịch bản», c = 2 «điểm»), tức
  **mép lưới**. Lưới ban đầu tới H = 32 cũng chọn mép. Quy tắc suy biến vì H không tốn trễ ở đây.
- Chi phí thật của H là **trạng thái cũ**, đo ở cột «giữ nhờ H». Range: 24–41% số nến đã chỉ còn nhờ H ngay ở H = 8.
  Trend: dưới 2% ở H = 8, 3–5% ở H = 16, 11–12% ở H = 32.

**Lưới một tham số** (các tham số khác nháp):

| Thay | «kịch bản» | «điểm» |
|---|---|---|
| W 24 / 48 / 96 | Range 4.4 / 4.7 / 1.8%; đổi 2.20 / 2.21 / 1.72 | Range 15.7 / 15.0 / 15.8%; đổi 5.63 / 5.47 / 5.57 |
| S 2 / 8 | không đổi gì (K5 quyết 0.5% số nến Uncertain) | — |
| N_r 8 / 16 / 32 | Breakout 22 / 5 / 0 | Breakout 38 / 7 / 0 |
| k 0.1 / 0.25 / 0.5 | Breakout 5 / 5 / 6 | Breakout 4 / 7 / 6 |
| B 6 / 24, m 2 / 8 | không đổi gì (Breakout kết thúc trong 1–3 nến) | không đổi gì |
| (q_vào, q_ra) 0.6/0.4 · 0.8/0.6 · 0.9/0.7 | — | Trend 48.8 / 33.9 / 15.5%. Phát hiện θ = 4: 0.56 / 0.40 / 0.23. M4 θ = 4: 0.09 / 0 / 0. 0.8/0.6 **trùng hệt** 0.7/0.5 vì D rời rạc |
| q_ρ 0.7 / 0.8 / 0.9 | — | Range 20.6 / 15.0 / 8.8%; đổi 6.24 / 5.47 / 4.12 |

**Hai tuỳ chọn thử** (không phải đề xuất của plan; chỉ đo độ bền và trễ):

- **Range giữ tới khi phá biên** (`range_giu = bien`): Range giữ tới khi Breakout, close ra ngoài biên ≥ k·ATR, hoặc
  điều kiện vào Trend xuất hiện.
  - «kịch bản», N_r = 16: Range 8.8%, đoạn Range trung vị 15.5 nến (P90 50). Giữ nhờ H 0.5%. Breakout 32 lần
    (0.19/ngày), thất bại 53%.
  - «điểm», N_r = 16: Range 23.3%, Breakout 59 lần, thất bại 64%.
  - Trend không đổi.
- **K1 «khung lớn không ngược»** (`k1 = khong_nguoc`): order_flow = d và H1, H4 đều không = −d. Đây là đúng câu ở phần
  «Vì sao» của plan §4.3; bảng K1 thì đòi H1 cùng chiều.
  - Trend 27.3 → 33.3%.
  - Trên θ = 4: phát hiện 0.29 → 0.33, giữ chiều 0.165 → 0.195.
  - Trung vị M4 **vẫn 0**.

Tổng số cấu hình biến thể đã thử trên dev chính: **73** (69 trong lưới + 4 biến thể nháp), cộng ngưỡng H1. Danh
sách ở `luoi_tham_so.cau_hinh` (M13).

### 5.5. Việc 5 — M5, M6 (kết cục tương lai trong từng tầng ATR)

Tam phân vị ATR/close (dev chính): 9.7 và 13.4 bps.

Hiệu h = 16 nến (4 giờ) trên dev chính. Mỗi ô: hiệu [CI 95%], p shift test.

- «trend vs khác»: trung bình ở Trend (↑ và ↓ gộp) trừ trung bình ở các trạng thái regime khác.
- «hướng»: P(chạm +1 ATR trước | Trend ↑) − P(… | Trend ↓). Null = 0; độ trôi giá dài hạn triệt tiêu.

| Bộ phát hiện | trend vs khác · ER tương lai | trend vs khác · biên độ/ATR | hướng · chạm +1 ATR trước | range vs khác · ER tương lai | MDE (ER · hướng) |
|---|---|---|---|---|---|
| `dc_regime` (reset) | −0.009 [−0.024; +0.011] p 0.47 | −0.86 [−1.35; −0.12] p 0.53 | −0.051 [−0.142; +0.064] p 0.26 | — | 0.025 · 0.139 |
| `dc_regime` (bridge) | −0.011 [−0.026; +0.005] p 0.21 | +0.03 [−0.32; +0.38] p 0.84 | −0.034 [−0.080; +0.009] p 0.15 | — | 0.023 · 0.063 |
| `indicator_baseline` | +0.001 [−0.013; +0.014] p 0.91 | +0.23 [−0.01; +0.50] p 0.50 | −0.009 [−0.053; +0.035] p 0.68 | −0.027 [−0.069; +0.009] p 0.07 | 0.019 · 0.062 |
| `order_flow` | −0.012 [−0.035; +0.009] p 0.16 | +0.20 [−0.12; +0.51] p 0.29 | +0.008 [−0.038; +0.044] p 0.70 | — | 0.031 · 0.055 |
| `order` M15 | −0.002 [−0.015; +0.011] p 0.78 | +0.27 [+0.05; +0.52] p 0.10 | −0.008 [−0.064; +0.045] p 0.73 | — | 0.020 · 0.076 |
| `htf_H1_order` | +0.010 [−0.005; +0.024] p 0.15 | −0.08 [−0.35; +0.20] p 0.56 | +0.015 [−0.037; +0.067] p 0.49 | — | 0.021 · 0.075 |
| `htf_H4_order` | +0.001 [−0.016; +0.016] p 0.96 | +0.26 [−0.13; +0.62] p 0.21 | −0.012 [−0.054; +0.030] p 0.64 | — | 0.023 · 0.060 |
| «kịch bản» | −0.008 [−0.026; +0.012] p 0.40 | +0.01 [−0.39; +0.38] p 0.96 | +0.046 [−0.036; +0.123] p 0.21 | +0.015 [−0.017; +0.053] p 0.36 | 0.027 · 0.114 |
| «điểm» (G1–G4) | **−0.020 [−0.036; −0.004] p 0.03** | −0.26 [−0.59; +0.07] p 0.12 | +0.018 [−0.047; +0.068] p 0.56 | +0.008 [−0.013; +0.031] p 0.44 | 0.023 · 0.082 |
| «điểm» chỉ ICT | −0.016 [−0.033; +0.000] p 0.06 | −0.25 [−0.56; +0.08] p 0.13 | +0.013 [−0.055; +0.064] p 0.63 | +0.003 [−0.018; +0.030] p 0.77 | 0.023 · 0.086 |
| «điểm» chỉ G4 | −0.010 [−0.024; +0.003] p 0.12 | +0.09 [−0.23; +0.45] p 0.56 | −0.018 [−0.070; +0.036] p 0.49 | +0.009 [−0.006; +0.025] p 0.17 | 0.019 · 0.076 |

Ví dụ trung bình theo trạng thái × tầng ATR («điểm», h = 16). ER tương lai qua ba tầng ATR (thấp / giữa / cao):

| Trạng thái | ER tương lai | P(chạm +1 ATR trước) |
|---|---|---|
| Trend ↑ | 0.254 / 0.248 / 0.217 | 0.55 / 0.52 / 0.53 |
| Trend ↓ | 0.214 / 0.254 / 0.254 | 0.47 / 0.56 / 0.51 |
| Range | 0.271 / 0.248 / 0.263 | — |
| Uncertain | 0.269 / 0.245 / 0.266 | — |

Không có tách rõ giữa các trạng thái.

Dev mở rộng (h = 16; 6 năm, 313 tuần; 99 độ dịch):

- **XAUUSD 2018–2023:** 3/38 phép đo vượt null.
  - `dc_regime` reset, trend vs khác: ER −0.012, biên độ −0.97 ATR.
  - `htf_H4_order`: biên độ −0.10 ATR.
  - Mọi hiệu «hướng» trong ±0.015. MDE hướng ≈ 0.02–0.03 (0.05 với `dc_regime` reset).
- **EURUSD 2018–2023:** 5/38 phép đo vượt null.
  - `indicator_baseline`, trend vs khác: ER −0.007.
  - `order` M15, hướng: −0.018 (đảo chiều nhẹ).
  - «điểm» chỉ G4, trend vs khác: ER −0.006.
  - Range «kịch bản» và Range «điểm» chỉ ICT: ER tương lai **cao hơn** +0.016 và +0.012. Range đi trước nhịp đi
    thẳng, ngược giả định «Range → về giữa».
- Theo năm (`theo_nam` trong JSON): dấu của hiệu «hướng» đổi qua các năm.
  - «điểm» XAU: +0.017, +0.054, +0.032, +0.015, +0.022, −0.007.
  - «điểm» EUR: +0.014, −0.055, −0.011, +0.015, +0.016, −0.033.
  - `order_flow`: dương 5/6 năm ở XAU, âm 6/6 năm ở EUR (mỗi năm |hiệu| ≤ 0.07).
  - Không có hiệu nào cùng dấu qua các năm **và** qua hai mã.

**M6 — ICT có thêm gì so với ER?** Chênh = hiệu của biến thể có bằng chứng ICT − hiệu của «điểm» chỉ G4. Cùng
bootstrap ghép cặp, cùng độ dịch.

| So | Dữ liệu | trend vs khác · ER (h 16) | hướng (h 16) | range vs khác · ER (h 16) |
|---|---|---|---|---|
| «điểm» đủ − chỉ G4 | dev chính | −0.010 [−0.029; +0.009] p 0.28 · MDE 0.027 | +0.035 [−0.035; +0.087] p 0.28 · MDE 0.089 | −0.002 [−0.019; +0.017] p 0.85 |
| «điểm» đủ − chỉ G4 | XAU 18–23 | +0.006 [−0.002; +0.013] p 0.20 · MDE 0.011 | +0.004 [−0.016; +0.025] p 0.75 · MDE 0.030 | +0.001 [−0.005; +0.008] p 0.68 |
| «điểm» đủ − chỉ G4 | EUR 18–23 | +0.005 [−0.002; +0.012] p 0.20 · MDE 0.010 | +0.008 [−0.008; +0.028] p 0.44 · MDE 0.027 | +0.002 [−0.003; +0.007] p 0.57 |
| «điểm» chỉ ICT − chỉ G4 | EUR 18–23 | +0.005 [−0.002; +0.012] p 0.22 | +0.006 [−0.011; +0.025] p 0.55 | +0.008 [−0.000; +0.016] p 0.05 |
| «kịch bản» − chỉ G4 | EUR 18–23 | +0.007 [−0.000; +0.015] p 0.06 | +0.016 [−0.008; +0.039] p 0.28 | +0.013 [+0.001; +0.024] p 0.06 |

Kết quả M6:

- Dev chính: **0/84** phép đo vượt null, gồm mọi h ∈ {4, 16, 64}, mọi kết cục, bốn cặp so.
- Dev mở rộng: **0/18**. Hai ô EUR ở bảng trên sát ngưỡng (p 0.05–0.06), và chúng là ô Range — đúng loại kết quả
  «Range → ER cao hơn» ngược trực giác nói trên.

**Lực thống kê.** Tám tháng dev chính chỉ thấy được hiệu ≥ 0.02–0.03 ER và ≥ 6–14 điểm % hướng. Sáu năm dev mở rộng
thấy được ≈ 0.007–0.011 ER và ≈ 2–4 điểm % hướng. Kết luận âm tính trên 6 năm vì vậy có nghĩa ở mức đó: bằng chứng
ICT (G1–G3), ghép theo cách nháp, **không** tách kết cục 4 giờ tới tốt hơn ER quá ≈ 3 điểm % (hướng) hay ≈ 0.01 ER.

Kiểm định bội:

- 177 + 76 phép đo M5 (dev chính + dev mở rộng) và 102 phép đo M6.
- Tiêu chí kép (p < 0.05 và CI không chứa 0) vẫn để lọt vài dương tính giả. 10 phép đo M5 vượt null, dấu lẫn lộn,
  phù hợp với mức ngẫu nhiên.

### 5.6. Việc 6 — cổng đi/dừng

**Trung vị M4 cao nhất trong các bộ phát hiện** (trừ «không đổi», «luôn tăng»), kèm tên bộ và số bộ đạt ≥ 0.25:

| Nhãn | XAU M15 2024 | XAU M15 18–23 | EUR M15 18–23 | XAU H1 2024 | XAU H1 18–23 (gộp) |
|---|---|---|---|---|---|
| DC θ = 1 | 0.00 (0 bộ) | 0.00 (0) | 0.00 (0) | 0.00 (0) | 0.00 (0) |
| DC θ = 2 | 0.12 ADX/SMA (0) | 0.06 (0) | 0.06 (0) | 0.00 (0) | 0.11 (0) |
| DC θ = 4 | 0.59 ADX/SMA (4) | 0.63 (5) | 0.63 (6) | 0.60 order flow (3) | 0.68 ADX/SMA (4) |
| TS L = 16 | 0.00 (0) | 0.00 (0) | 0.00 (0) | 0.00 (0) | 0.00 (0) |
| TS L = 32 | 0.00 (0) | 0.00 (0) | 0.00 (0) | 0.00 (0) | 0.00 (0) |
| TS L = 64 | 0.28 ADX/SMA (1) | 0.22 (0) | 0.22 (0) | 0.23 (0) | 0.35 order flow (3) |

**DC θ = 4 ATR theo bộ phát hiện.** Mỗi ô: M4 TV · giữ chiều theo nến (mốc dịch vòng).

| Bộ phát hiện | XAU M15 2024 | XAU M15 18–23 | EUR M15 18–23 | XAU H1 2024 | XAU H1 18–23 |
|---|---|---|---|---|---|
| `dc_regime` (bridge) | 0.11 · 0.26 (0.24) | 0.25 · 0.28 (0.24) | 0.27 · 0.29 (0.26) | 0 · 0.09 (0.08) | 0 · 0.11 (0.09) |
| `indicator_baseline` | 0.59 · 0.39 (0.28) | 0.63 · 0.40 (0.28) | 0.63 · 0.40 (0.28) | 0.54 · 0.40 (0.30) | 0.68 · 0.44 (0.30) |
| `order_flow` | 0.40 · 0.44 (0.39) | 0.45 · 0.45 (0.39) | 0.47 · 0.44 (0.39) | 0.60 · 0.41 (0.39) | 0.53 · 0.45 (0.40) |
| `order` khung chạy | 0.48 · 0.30 (0.27) | 0.47 · 0.31 (0.27) | 0.46 · 0.30 (0.26) | 0.35 · 0.30 (0.29) | 0.50 · 0.33 (0.28) |
| `htf_H1_order` | 0 · 0.29 (0.28) | 0 · 0.27 (0.27) | 0 · 0.29 (0.28) | — | — |
| `htf_H4_order` | 0 · 0.26 (0.29) | 0 · 0.28 (0.28) | 0 · 0.29 (0.29) | 0.10 · 0.31 (0.29) | 0 · 0.28 (0.28) |
| «kịch bản» | 0 · 0.17 (0.14) | 0 · 0.14 (0.12) | 0 · 0.14 (0.13) | 0 · 0.12 (0.10) | 0 · 0.10 (0.09) |
| «điểm» (G1–G4) | 0 · 0.21 (0.17) | 0 · 0.19 (0.15) | 0 · 0.19 (0.16) | 0 · 0.19 (0.18) | 0 · 0.19 (0.15) |
| «điểm» chỉ G4 | 0.26 · 0.29 (0.21) | 0.32 · 0.29 (0.20) | 0.31 · 0.28 (0.19) | 0.22 · 0.29 (0.20) | 0.26 · 0.28 (0.18) |

Trên trend-scanning L = 64, phần «giữ chiều» của mọi bộ nằm ở hoặc dưới mốc dịch vòng (chênh −0.06 … +0.01).

**Giờ còn lại sau phát hiện** (trung vị nến còn lại × độ dài nến; bỏ lỡ = 0), DC θ = 4:

| Bộ phát hiện | XAU M15 2024 | XAU M15 18–23 | XAU H1 2024 | XAU H1 18–23 |
|---|---:|---:|---:|---:|
| `indicator_baseline` | 6.8 giờ | 7.5 giờ | 21 giờ | 35 giờ |
| `order` khung chạy | 5.5 giờ | 5.2 giờ | 15 giờ | 26 giờ |
| `order_flow` | 2.8 giờ | 3.8 giờ | 18 giờ | 21 giờ |
| «kịch bản», «điểm» | 0 | 0 | 0 | 0 |

---

## 6. Kết luận cho cổng đi/dừng

**Đề xuất: DỪNG trước 4b** — không viết `ict_regime` theo bản nháp §4.3–§4.6 như hiện tại. Cần bạn quyết định hướng
(§8). Vì sao:

1. **Điều kiện cổng của plan đúng với cả hai biến thể nháp.** Trung vị M4 của «kịch bản» và «điểm» = 0 ở cả 6 nhãn ×
   5 bộ dữ liệu (M15 và H1). Chúng chỉ bắt được 11–41% số đoạn xu hướng tham chiếu.
2. **Điều kiện cổng đúng với mọi bộ phát hiện ở nhịp ngắn.** Ở DC θ ≤ 2 ATR và trend-scanning L ≤ 32 (đoạn trung
   vị ≤ 5 giờ ở M15), kể cả baseline, ở cả 3 bộ M15. Theo đúng chữ của plan («với mọi bộ phát hiện… dưới một phần
   tư»), regime M15 ở thang nhịp này **không dùng được cho router**.
3. **Ở nhịp dài (DC θ = 4 ATR, ≈ 10–15 giờ ở M15), cổng chỉ qua nhờ baseline đơn giản, và qua một cách yếu.**
   - ADX/SMA, thứ tự M15, order flow, ER có trung vị M4 0.26–0.63, ổn định qua 3 bộ M15.
   - Nhưng M4 đó thấp hơn mốc dịch vòng, nghĩa là phần lớn đến từ độ bền và việc lật, không đến từ khớp.
   - Phần thời gian **giữ đúng chiều** chỉ hơn mốc ngẫu nhiên 3–11 điểm % (ADX/SMA 0.39–0.44 so với 0.28–0.30).
4. **Đổi sang H1 không tự mở cổng.**
   - Mẫu hình M4 tương đối giữ nguyên: nhịp ≤ 2 ATR_H1 dưới 0.25; θ = 4 thì baseline 0.35–0.68, biến thể 0.
   - H1 chỉ kéo dài thời gian tuyệt đối: 15–35 giờ còn lại thay vì 3–8 giờ ở M15.
   - Nếu router cần nắm xu hướng nhiều giờ, H1 cho nhiều giờ hơn. Nhưng lý do không phải là H1 «nhận diện tốt hơn».
5. **Không có bằng chứng ICT thêm thông tin so với ER** (M6 ở 6 năm, MDE ≈ 3 điểm %). Bản thân M5 cũng không cho
   trạng thái nào tách kết cục 4 giờ tới rõ hơn null. Regime từ cấu trúc vẫn có thể có giá trị **mô tả** (giải thích
   được, nhân quả), đúng như plan §0 «kỳ vọng trung thực» đã dự liệu. Nhưng 4a không cho căn cứ để gọi nó là đầu vào có
   ích cho router.

Kết quả âm tính này là kết quả hợp lệ. Nó đến kèm lực thống kê: 2068–2272 đoạn θ = 4 và 313 tuần mỗi mã ở dev mở rộng.

---

## 7. Đề xuất ngưỡng cho plan §4.7

Áp dụng **nếu** bạn vẫn cho làm 4b (dù chỉ như lớp mô tả). Mọi giá trị chỉ dựa trên độ bền, trễ và tỷ lệ thời gian
ở dev chính — **không** chọn theo kết cục M5. Giá trị số tính trên XAUUSD M15 01–08/2024.

| Tham số | Nháp | Đề xuất | Lý do (số ở §5.4) |
|---|---|---|---|
| `bien_the` | `kich_ban` | để bạn chốt — xem §8 Q-A, Q-D | Hai biến thể ngang nhau trên M5/M6. «kịch bản» bền hơn (2.2 so với 5.5 lần đổi/ngày) nhưng Uncertain 68% |
| G | 4 | **4** | Dữ liệu thiếu chỉ 0.03–0.13% số nến; không có căn cứ đổi |
| W | 48 | **48** | W = 24 cho Range gần như nhau (4.4%), W = 96 bóp Range còn 1.8%. Range bị chi phối bởi luật giữ (Q-B), không bởi W |
| [a, b] | P20–P80 | **3.48–6.89 ATR** (H1: 3.83–7.32) | Phân vị dev, đúng như plan |
| ER thấp (K3) | — | **≤ 0.164** (P50 dev; H1 0.18) | Q4 đồng ý dùng ER; lab chọn P50 |
| S | 4 | **4** (hoặc bỏ K5) | S = 2 / 8 không đổi số nào; K5 chỉ quyết 0.5% số nến Uncertain |
| N_r | 16 | **chưa chốt** — phụ thuộc Q-B | Với luật Range hiện tại, đoạn Range P90 = 17 nến → Breakout 5 lần / 8 tháng. N_r = 8 → 22 lần. Luật «giữ tới khi phá biên» với N_r = 16 → 32 lần |
| k | 0.25 | **0.25** | k = 0.1–0.5 gần như không đổi số Breakout (4–7) |
| B, m | 12, 4 | **12, 4** | Không nhạy: Breakout kết thúc trong 1–3 nến |
| c | 1 | **1** | Mỗi nến xác nhận thêm: +0.5–1 nến trễ, tỷ lệ phát hiện giảm tới 6 điểm %, số lần đổi chỉ bớt 1–7%. Quy tắc khuỷu chọn c = 2 cho «điểm» ở mép lưới — xem dòng H |
| H | 8 | **16 cho Trend**; Range xem Q-B | Trễ không đổi theo H nên quy tắc khuỷu suy biến (luôn chọn mép lưới, nay là 64). Tôi chọn theo chi phí trạng thái cũ: H lớn nhất mà phần Trend «giữ nhờ H» ≤ 5% → H = 16 (3.4% «kịch bản», 4.8% «điểm»). Đổi so với H = 8: −2% («kịch bản») và −13% («điểm») số lần đổi. Với Range, ngay H = 8 đã có 24–41% số nến Range chỉ còn nhờ H — không nên dùng chung H cho Range. *Quy tắc «≤ 5%» đặt sau khi thấy đường cong, ghi rõ ở đây* |
| θ_vào, θ_ra, ρ | phân vị dev | **0.464 / 0.321 / 0.669** (phân vị 0.7 / 0.5 / 0.8) | D rời rạc: phân vị 0.8 / 0.6 cho cùng ngưỡng với 0.7 / 0.5. 0.6 / 0.4 tăng phát hiện θ = 4 lên 0.56 nhưng Trend 49% thời gian. Sau 4d chọn lại bằng risk–coverage như plan |
| n (ER) | 32 | **32** | Cố định như plan |
| `pd_bias` trong G2 | 0.5 | **bỏ** | G2 có / không có nó tương quan 0.92 |
| `dol_side` | trong G2 | **sang G1 hoặc bỏ** | Tương quan 0.34–0.40 với order flow (cùng nguồn shift) |

Đường trễ ↔ lật đầy đủ (18 điểm mỗi biến thể, kèm phát hiện, M4, «giữ nhờ H») ở `luoi_tham_so.duong_tre_lat`.

---

## 8. Câu hỏi cần bạn chốt (mới, sau 4a)

| # | Câu hỏi | Lựa chọn và số liên quan |
|---|---|---|
| Q-A | Regime phục vụ nhịp nào? | (1) Nhịp dài ≈ DC θ = 4 ATR M15 (10–15 giờ) — thang duy nhất mà baseline giữ được ≥ 0.25 phần đoạn. Khi đó Trend nên dựa trên bằng chứng chậm hơn và ít phủ quyết hơn, rồi đo lại 4a trên cùng dev. (2) Chạy regime ở H1, cùng M4 tương đối, nhưng nhiều giờ hơn cho router. (3) Giữ M15 nhưng chỉ làm lớp **mô tả**, không hứa gì về router |
| Q-B | Luật giữ Range | Luật hiện tại (giữ khi K3 còn đúng): Range nhấp nháy, 24–52% số nến «chỉ nhờ H», Breakout gần như không có. Tuỳ chọn «giữ tới khi phá biên»: Range 8.8%, đoạn trung vị 15.5 nến, Breakout 32 lần / 8 tháng, thất bại 53%. Hoặc định nghĩa lại K3 (vd bỏ điều kiện «không run trong W») |
| Q-C | K1 «kịch bản» | Bảng K1 đòi H1 cùng chiều; phần «Vì sao» nói «khung lớn không ngược». Bản «không ngược»: Trend 33% (so với 27%), phát hiện θ = 4 0.33 (so với 0.29), M4 vẫn 0. Uncertain chủ yếu do K6 (63%) và K4 (25%) — nới K1 không đủ |
| Q-D | Có đáng làm 4b không, khi M6 âm tính? | Plan §10 đã lường trước. Nếu làm thì làm như lớp mô tả có giải thích, kèm baseline ER (G4) chạy song song để mọi báo cáo sau luôn có mốc |

---

## 9. Giới hạn

- **Một mã, một giai đoạn ở dev chính** (XAUUSD 8 tháng, 35 tuần). CI ở dev chính rộng: MDE hướng 6–14 điểm %.
  Dev mở rộng (6 năm × 2 mã) mới cho lực đủ để nói âm tính.
- **Cỡ mẫu hiệu dụng là số đoạn**: dev chính chỉ có 248 đoạn θ = 4, H1 2024 chỉ có 65. Bootstrap theo khối tuần
  và shift test có tính tự tương quan, nhưng không sửa được việc có ít đoạn.
- **Nhãn hậu kiểm chỉ là một họ định nghĩa.**
  - DC không có Range.
  - Trend-scanning với |t| ≥ 2 gần như không cho nhãn 0, vì t-value OLS bị thổi phồng. Vì vậy **chưa chấm được
    Range** so với tham chiếu nào. Đó là việc của nhãn tay (4d).
- **M4 nhạy với định nghĩa.** Trung vị M4 (bỏ lỡ = 0) gần như là chỉ báo «phát hiện > 50% số đoạn?». Bản thân M4
  thưởng cho việc lật. Tôi thêm «giữ chiều» và mốc dịch vòng để đọc đúng; hai thứ này **không có trong plan**.
- **Shift test cho M5** giữ nguyên tầng ATR và kết cục, chỉ dịch trạng thái. Mùa vụ trong ngày được kiểm một phần (độ
  dịch không là bội số của ngày), nhưng không chặt như null ghép giờ New York.
- **Kiểm định bội:** hàng trăm phép đo. Chỉ nên tin hiệu vượt null **và** cùng dấu qua năm và mã. Không có hiệu nào
  như vậy.
- **Biến thể là nguyên mẫu.** Nhiều chỗ chọn của tôi (§4) có thể khác cách bạn đọc chart, nhất là biên «vùng ở biên»
  của Breakout và luật giữ Range. Kết luận âm tính áp dụng cho **bản nháp này**, không cho mọi cách đọc ICT.
- Ngưỡng dev mở rộng lấy từ XAUUSD 2024 (đều không có đơn vị). Với EURUSD điều này hợp lệ về đơn vị nhưng chưa tối ưu
  — đúng tinh thần «chốt trên dev, đo nơi khác».
- HMM fit trên 2000 nến đầu mỗi đoạn là in-sample trên prefix, như ghi chú của `hmm_online`.

---

## 10. Chưa làm, và thay đổi so với lần chạy thử

**Chưa làm** (ngoài phạm vi 4a hoặc không đủ dữ liệu):

- M7 (Breakout so với mức ngẫu nhiên): chỉ có 5–16 Breakout mỗi bộ dữ liệu.
- Kết cục «về giữa range trước khi phá biên» của M5.
- M8 (đồng thuận giữa các bộ phát hiện).
- Jump model online — plan đặt ở 4c.
- Không chạy và không chấm gì trên đoạn kiểm tra.
- Không ghi gì vào DB. Không sửa `core/`, `backend/`, `frontend/`, `tests/`, plan hay đặc tả.

**Thay đổi sau lần chạy thử đầu** (đều trên dev chính, đều **không** dựa trên kết cục M5):

1. Trục x của đường trễ ↔ lật đổi từ «trễ kiểm duyệt» sang «trễ chuyển». Trễ kiểm duyệt bị bão hoà ở độ dài đoạn,
   vì đa số đoạn bị bỏ lỡ.
2. Thêm «M4 giữ chiều» kèm null. Lý do: M4 của baseline thấp hơn mốc dịch vòng.
3. Mở lưới H tới 64 và thêm «giữ nhờ H». Lý do: quy tắc khuỷu chọn mép lưới.
4. Thêm hai tuỳ chọn thử: `range_giu = bien` và `k1 = khong_nguoc`. Cả hai chỉ để bạn thấy hệ quả; không tuỳ chọn nào
   được chọn làm nháp.
