# Plan: giai đoạn 4 — lớp kịch bản bias → regime (`ict_regime`)

Bản 1 — 07/10/2026. **Trạng thái: đề xuất; Q1–Q7 (§9) dùng đúng theo đề xuất để làm bước 4a (người dùng 18/10/2026:
«tiếp tục làm đi, rồi tôi sẽ review») — duyệt chính thức sau khi xem kết quả 4a. Chưa có code thuật toán.**
Theo vòng thiết kế trong [`AGENTS.md`](../../AGENTS.md) §3, đây là bước ① (nguồn) + bản nháp bước ② (định nghĩa
vận hành). Mọi ngưỡng ở §4 là **tham số thí nghiệm** — chốt bằng khảo sát trên đoạn phát triển (4a, §8) trước khi
viết code; đoạn kiểm tra vẫn khoá.

Phụ thuộc: `ict_structure` **0.4.x** (giai đoạn 3, đã cài 08/10/2026: thứ tự H1/H4, `pd_bias`, DOL, PDH/PDL, `details.htf` —
[`plan_ict_structure.md`](plan_ict_structure.md) §11). Tên trường theo bản cài thật — đặc tả
[`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md) §4.13–§4.19.

Nguồn:
- [`nghien_cuu_bias_regime.md`](../research/nghien_cuu_bias_regime.md) — tài liệu: định nghĩa regime, breakout,
  ICT daily bias, cách ghép bằng chứng, đánh giá không dùng P&L, router.
- [`nghien_cuu_regime_copilot_va_repo_cu.md`](../research/nghien_cuu_regime_copilot_va_repo_cu.md) — yêu cầu sản
  phẩm AI Trading Copilot và bài học từ dự án `regime-aware-ai-trading`.
- Số liệu lab: [`plan_ict_structure.md`](plan_ict_structure.md) §2.6, §11.2;
  [`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md) §4.12, §8.1;
  [`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md).

---

## 0. Tóm tắt

- **Làm gì:** tại mỗi nến (mặc định M15), chỉ dùng thông tin đã biết, gán **regime** ∈ Trend ↑ / Trend ↓ / Range /
  Breakout ↑↓ / Uncertain, kèm **lý do** và **bằng chứng** truy được về sự kiện của `ict_structure`. Hai trạng thái
  không phải regime: **Khởi động** và **Dữ liệu thiếu** (không gộp vào Uncertain — AGENTS §2.2).
- **Không làm:** tín hiệu vào lệnh, router, P&L. Router (Trend Pullback / Range Mean Reversion / No Trade) và phép
  thử giá trị E1 thuộc repo giao dịch; lab xuất một bản «RegimeEstimate» cho repo đó dùng.
- **Cách ghép:** hai biến thể có tên, chấm như nhau (AGENTS §3.2): **«kịch bản»** — cây luật đọc như cách bạn đọc
  chart (§4.3, phần bạn cần duyệt) — và **«điểm»** — điểm đều trọng số theo 4 nhóm bằng chứng + vùng chết (§4.4).
  Cả hai có hysteresis và thời gian giữ tối thiểu.
- **Đo trước khi tin:** khảo sát 4a trả lời câu hỏi có đáng làm không — regime ở M15 có kéo dài đủ lâu sau khi phát
  hiện để router dùng được không; bằng chứng ICT có thêm gì so với một chỉ số thống kê đơn giản không.
- **Kỳ vọng trung thực:** lab đã đo order flow / shift không dự báo phía thanh khoản tốt hơn ngẫu nhiên; tài liệu
  không có kiểm định nào ủng hộ ICT «như được dạy». Regime từ cấu trúc vẫn có giá trị **mô tả** (giải thích được,
  nhân quả), nhưng có thể không tách kết cục tương lai hơn một baseline thống kê. Kết quả âm tính là kết quả hợp lệ
  và sẽ được báo kèm lực thống kê.

---

## 1. Bài toán và ranh giới

```text
Cấu trúc (ict_structure 0.4.0)  ──►  Regime (ict_regime, plan này)  ──►  Router (repo giao dịch)
sự kiện + timeline + htf            Trend/Range/Breakout/Uncertain      Trend Pullback · Range MR · No Trade
                                     + Khởi động / Dữ liệu thiếu          (E0 → E1 → E2, có chi phí)
```

**Bias tách khỏi regime** (bài học repo cũ: gộp hướng vào «trending» làm xu hướng giảm bị xếp thành ranging/calm):
- `bias` ∈ {+1, −1, 0}: chiều mà các nhóm bằng chứng có hướng nghiêng về.
- `regime` không có hướng; Trend và Breakout lấy chiều từ `bias` / chiều phá.
- Trong Trend có thêm trường mô tả **pha**: `hoi` (giá ở discount khi tăng / premium khi giảm) hoặc `mo_rong`. Pha
  không phải regime (giống «bull correction» của Maheu et al.); chiến lược pullback ở repo giao dịch tự quyết dùng.

**Ánh xạ sang router** (cố định theo `[C]AI_Trading_Copilot_Luong_He_Thong.md` §4, không tính trong lab): Trend →
Trend Pullback được xét; Range → Mean Reversion được xét; Breakout, Uncertain → No Trade; Dữ liệu thiếu → chặn đề
xuất (lỗi dữ liệu, không phải No Trade do thị trường); Khởi động → chặn. Event-risk cần lịch tin — ngoài phạm vi
(Q2).

---

## 2. Căn cứ

### 2.1. Từ dữ liệu lab (XAUUSD M15 dev 01–08/2024 trừ khi ghi khác)

| Phát hiện | Số | Hệ quả cho thiết kế |
|---|---|---|
| Thứ tự M15 / H1 / H4 «lẫn lộn» | 48% / 43% / 42% thời gian | Trạng thái không có hướng là bình thường, không phải lỗi |
| Bộ ba thứ tự H1 + pd_bias + DOL | cùng chiều 4.1%, mâu thuẫn 26%, thiếu ≥ 1 thành phần 70% | Không đòi «cả ba cùng chiều» cho Trend — gần như không bao giờ xảy ra |
| `pd_bias` | 410 lần đổi, trung vị 7.5 giờ; shift cùng chiều pd_bias 33% (ngẫu nhiên 50%) | Nhiễu, đo nhịp gần → không dùng trong «kịch bản»; trọng số nhỏ trong «điểm» |
| Order flow (0.3.0) | tăng / giảm / chưa rõ 46 / 30 / 24%; đoạn một chiều trung vị 13 giờ (~52 nến) | Thang thời gian để so với độ trễ phát hiện |
| `protected_broken` | ~12% thời gian ở mọi khung | Phản bác cứng cho Trend |
| `dc_regime` (dataset lệch giờ) | Range ≤ 0.2%, Chưa rõ 46–91% | Điều kiện Range quá chặt → đo tỷ lệ thời gian trước khi chốt ngưỡng (4a) |
| Dùng nến khung lớn đang hình thành | thứ tự sai 6% số nến | Chỉ nến đã chốt (giai đoạn 3 đã lo) |

### 2.2. Từ tài liệu

- Không có định nghĩa chuẩn Trend/Range/Breakout; ngưỡng ADX 20/25, CHOP 38.2/61.8 không có căn cứ thống kê → đặt
  ngưỡng theo **phân vị trên dev**, cố định trước.
- Đánh đổi cố hữu **trễ ↔ nhấp nháy**: hysteresis / hình phạt nhảy giảm số lần đổi nhưng thêm trễ → phải đo cả hai.
- **Đếm trùng bằng chứng tương quan** làm bộ ghép quá tự tin (naive Bayes) → gom thành nhóm, mỗi nhóm một phiếu;
  trọng số đều (Dawes 1979) khi chưa có nhãn.
- Breakout: hiệu ứng vi cấu trúc có thật nhưng nhỏ (Osler: vài điểm %); phá biên intraday FX không sinh lời trung
  bình; không có nghiên cứu phân biệt breakout thật/giả bằng cấu trúc → Breakout là **trạng thái chuyển tiếp ngắn**,
  kết cục (đi tiếp hay thất bại) phải đo với null mức ngẫu nhiên.
- Sweep dự báo **tiếp diễn** nhiều hơn đảo chiều (preprint 2026, chưa xác minh gốc) — khớp số của lab; luật «sweep →
  đảo chiều» phải kiểm, không mặc định.
- Đánh giá không cần P&L: độ bền, trễ so với nhãn hậu kiểm (họ tham số), độ tách kết cục tương lai **trong từng tầng
  ATR** (biến động tự tương quan làm mọi bộ phân loại dính ATR đều «tách» được), shift test làm null cho chuỗi trạng
  thái, baseline «không đổi» (thắng nhiều thuật toán trong benchmark TCPD).

### 2.3. Từ yêu cầu sản phẩm và repo cũ

- Copilot cần đúng 5 trạng thái router (Trend, Range, Breakout, Event-risk, Uncertain) và lỗi dữ liệu tách riêng;
  bộ đánh giá phải có nhiều nhóm tình huống, báo **tỷ lệ Uncertain**, nhãn độc lập.
- Repo cũ không có Breakout/Uncertain, không có nhãn regime, rò tương lai ở HMM, khung lớn và pivot; khung đáng giữ:
  bỏ phiếu + làm mượt + hysteresis + «không chắc → đứng ngoài»; hợp đồng `RegimeEstimate`.

---

## 3. Đầu vào: bốn nhóm bằng chứng (khử trùng lặp)

Thứ tự M15, mức bảo vệ, order flow, shift đều sinh từ cùng chuỗi swing → không cộng riêng từng cái.

| Nhóm | Câu hỏi | Trường (đọc ở nến t, trạng thái **sau** t) | Giá trị nhóm |
|---|---|---|---|
| **G1 Cấu trúc khung chạy** | Giá đang lấy thanh khoản phía nào? | `order_flow`, `order`, `protected_broken`, `last_shift(_bars)` | hướng ∈ [−1, 1] |
| **G2 Ngữ cảnh khung lớn** | Khung lớn nghiêng về đâu? | `htf_H1_order`, `htf_H4_order`, `dol_side` (+ `pd_bias` chỉ ở «điểm») | hướng ∈ [−1, 1] |
| **G3 Biên** | Giá có đang bị giữ giữa hai biên không? | sweep **hai phía** trong W nến không kèm run; độ rộng dealing range / ATR; `range_pos`; PDH/PDL đều chưa bị lấy | mức «đi ngang» ∈ [0, 1] |
| **G4 Hiệu quả giá** (không ICT, Q4) | Giá đi thẳng hay đi zigzag? | Kaufman ER trên n nến (tính trong `ict_regime`, nhân quả) | ∈ [0, 1] |

4a đo tương quan giữa các nhóm trên dev; nhóm nào trùng thông tin (|tương quan| cao) thì gộp hoặc bỏ.

---

## 4. Định nghĩa vận hành (bản nháp)

### 4.1. Thứ tự trong một nến t

1. `ict_structure` xử lý nến t (bước 1–10 của nó, gồm ngữ cảnh khung lớn đã chốt).
2. `ict_regime` đọc timeline + sự kiện đã xác nhận ≤ t, tính G1–G4.
3. Xét trạng thái không phải regime (§4.2) → Breakout đang mở (§4.5) → luật của biến thể (§4.3 / §4.4) → hysteresis
   (§4.6).
4. Ghi timeline; phát sự kiện nếu trạng thái đổi (nến sự kiện = nến xác nhận = t). Regime tại t dùng được từ t+1.

### 4.2. Trạng thái không phải regime

| Trạng thái | Khi nào | Thoát |
|---|---|---|
| **Dữ liệu thiếu** | khoảng trống bất thường (`gap` ∈ thiếu trong phiên, lệch bước) trong G nến gần nhất; nến H1/H4 vừa chốt `degraded`; nến M15 nằm trong khoảng trống bất thường | hết G nến không có lỗi mới |
| **Khởi động** | `order` M15 chưa có, hoặc H1 chưa `ready` | đủ cả hai |

Không tính hai trạng thái này vào tỷ lệ thời gian của regime (mẫu số = nến có regime). Plan `ict_structure` §5.3
(bản nháp cũ) xếp gap/degraded vào Uncertain — plan này thay thế chỗ đó.

### 4.3. Biến thể «kịch bản» (cây luật — **Q5: bạn duyệt / sửa**)

Xét theo thứ tự, luật đầu tiên đúng thắng. `d` = +1 (tăng) hoặc −1 (giảm).

| # | Luật | Kết quả |
|---|---|---|
| K1 | **Trend d** — cấu trúc hai khung cùng chiều: `order_flow` = d **và** (`htf_H1_order` = d, hoặc `htf_H1_order` = 0 và `htf_H4_order` = d) | Trend d, nếu không vướng K2 |
| K2 | Phản bác Trend: mức bảo vệ M15 phía d đã bị close vượt (`protected_broken`), hoặc DOL đang có ngược d | Uncertain, lý do «mức bảo vệ bị vượt» / «DOL ngược» |
| K3 | **Range** — không có Trend; `order` M15 = 0 hoặc `order_flow` = chưa rõ; trong W nến có **sweep cả BSL và SSL** mà **không có run**; độ rộng dealing range / ATR trong [a, b]; (nếu Q4 đồng ý) ER thấp | Range, biên = dealing range lúc vào |
| K4 | Xung đột khung: `order_flow` = d nhưng `htf_H1_order` = −d | Uncertain, lý do «xung đột khung» |
| K5 | Vừa có shift ≤ S nến, chưa có run / cực trị mới cùng chiều | Uncertain, lý do «shift chưa đi tiếp» |
| K6 | Còn lại | Uncertain, lý do «không đủ bằng chứng» |

Vì sao như vậy:
- Trend dựa trên order flow (giá vừa **lấy thanh khoản** phía nào — đúng cách đọc của bạn) cộng khung lớn không
  ngược; không đòi DOL / pd_bias cùng chiều vì bộ ba gần như không bao giờ cùng chiều (§2.1).
- Range kiểu ICT: hai biên đều bị **quét rồi quay lại** (sweep) mà không bị **phá** (run) — dùng đúng định nghĩa
  sweep/run sẵn có của `ict_structure`.
- K4/K5 là hai dạng Uncertain tài liệu nói đến nhiều nhất: khung nhanh và chậm bất đồng (Garg et al.: chiếm hơn 1/3
  thời gian ở dữ liệu ngày), và vừa đổi chiều chưa được xác nhận.

### 4.4. Biến thể «điểm»

- Điểm hướng `D = trung bình(G1, G2)` ∈ [−1, 1]; điểm đi ngang `R = trung bình(G3, G4)` ∈ [0, 1] (không có G4 thì
  chỉ G3).
- Trend d khi `|D| ≥ θ_vào` và `R < ρ`; giữ Trend tới khi `|D| < θ_ra` (θ_ra < θ_vào — hysteresis hai ngưỡng) hoặc
  có phản bác cứng (như K2).
- Range khi `R ≥ ρ` và `|D| < θ_ra`.
- Còn lại (vùng chết) → Uncertain, lý do = thành phần nào kéo điểm vào vùng chết.
- θ, ρ đặt theo phân vị dev ở 4a; khi có nhãn (4d) chọn lại vùng chết bằng đường risk–coverage trên dev.
- `bias = sign(D)` khi `|D| ≥ θ_ra`, ngược lại 0 — dùng chung cho cả hai biến thể.

### 4.5. Breakout và phá vỡ thất bại

- **Vào** (chỉ từ Range đã kéo dài ≥ N_r nến): vùng thanh khoản ở biên range bị **lấy** và trong cùng nến có
  displacement cùng chiều, hoặc nến **đóng** ngoài biên ≥ k·ATR → Breakout d.
- **Trong Breakout** (tối đa B nến):
  - `ict_structure` kết luận **run** cho vùng biên, hoặc có cực trị mới cùng chiều và không đóng lại trong biên →
    thoát Breakout, xét K1 (thường thành Trend d; nếu chưa đủ → Uncertain «breakout chưa xác nhận»).
  - Kết luận **sweep**, hoặc đóng lại trong biên trong m nến → sự kiện `REGIME_BREAKOUT_FAILED`, quay về Range (biên
    cũ) nếu K3 còn đúng, ngược lại Uncertain.
  - Hết B nến chưa rõ → Uncertain «breakout chưa xác nhận».
- Kết cục breakout (đi tiếp / thất bại) là **thứ phải đo** (M7, §6) với null mức ngẫu nhiên, không phải giả định.

### 4.6. Hysteresis và giữ tối thiểu

- Đã vào Trend / Range thì giữ ít nhất H nến, **trừ** phản bác cứng: mức bảo vệ bị vượt, order flow đổi chiều bằng
  shift, Breakout, Dữ liệu thiếu.
- Vào Trend cần điều kiện đúng c nến liên tiếp (c = 1 ở bản đầu; lưới ở 4a).
- 4a vẽ đường «số lần đổi / ngày» theo «trễ phát hiện trung vị» cho lưới (H, c, θ) và chọn điểm ở khuỷu **trước khi**
  mở đoạn kiểm tra.

### 4.7. Tham số (tham số thí nghiệm, do lab chọn — chốt ở 4a)

| Tham số | Nghĩa | Giá trị nháp | Cách chốt |
|---|---|---|---|
| `bien_the` | `kich_ban` / `diem` | `kich_ban` | Q5 |
| G | cửa sổ Dữ liệu thiếu | 4 nến | cố định |
| W | cửa sổ tìm sweep hai phía (K3) | 48 nến (12 giờ) | thang đoạn order flow (~52 nến) |
| [a, b] | độ rộng range / ATR | phân vị 20–80% dev | phân vị dev |
| S | «vừa shift» (K5) | 4 nến | lưới 4a |
| N_r, k, B, m | Breakout | 16 nến, 0.25 ATR, 12 nến, 4 nến | lưới 4a, chọn trước khi xem test |
| H, c | giữ tối thiểu, xác nhận vào | 8 nến, 1 | đường trễ ↔ lật (§4.6) |
| θ_vào, θ_ra, ρ | biến thể «điểm» | phân vị dev | phân vị dev; sau 4d: risk–coverage |
| n (ER) | cửa sổ G4 | 32 nến | cố định |

Mọi cấu hình đã thử được ghi lại (để báo số cấu hình và đánh giá overfit — M13).

---

## 5. Đầu ra

- **Sự kiện** (chỉ khi trạng thái đổi; nến sự kiện = nến xác nhận): `REGIME_TREND_UP`, `REGIME_TREND_DOWN`,
  `REGIME_RANGE`, `REGIME_BREAKOUT_UP`, `REGIME_BREAKOUT_DOWN`, `REGIME_UNCERTAIN`, `REGIME_NO_DATA`, cộng
  `REGIME_BREAKOUT_FAILED`. `details`: lý do, giá trị G1–G4, `bias`, biên range, `reference_event_id` /
  `details.basis` = id sự kiện `ict_structure` làm căn cứ (shift, run, sweep…), ảnh chụp `htf`. Timeline không lưu
  vào DB nên sự kiện đổi trạng thái là thứ được lưu và mở lại được (giống `DC_REGIME_*`).
- **Timeline:** `regime`, `regime_dir`, `regime_since`, `regime_reason`, `bias`, `g1`–`g4`, `pha`, `breakout_age`,
  `range_hi`, `range_lo`.
- **`pending_state`:** regime hiện tại + «điều gì sẽ đổi nó» (như khối order flow của 0.3.0) — dùng cho khung «Thuật
  toán đang làm gì».
- **`run_stats`:** tỷ lệ thời gian từng trạng thái (mẫu số = nến có regime), tỷ lệ Uncertain, số lần đổi / ngày giao
  dịch, độ dài đoạn trung vị / P90 mỗi trạng thái, % đoạn < 4 nến, số Breakout và tỷ lệ thất bại.
- **Xuất cho repo giao dịch** (4e): CSV/JSON mỗi nến theo khuôn `RegimeEstimate` — `estimator` (`ict_regime` +
  phiên bản + biến thể), `as_of` = close nến, `available_at` = close nến, `state`, `bias`, `reason`, điểm nhóm (thay
  cho «filtered probabilities»), `uncertainty` (Uncertain / vùng chết), `train_cutoff` = hết đoạn dev dùng để chốt
  ngưỡng.
- **Giao diện:** dải regime ở đáy chart (lớp vẽ chung `Band` đã có), dòng trạng thái thêm một hàng «Regime: …, vì …»,
  tooltip lý do; khung «Thuật toán đang làm gì» thêm một dòng.

---

## 6. Đánh giá (không P&L)

Đoạn: dev XAUUSD M15 01–08/2024 (`ds_db1583cd4dde`); dev mở rộng XAUUSD và EURUSD M15 2018–2023 (độ bền theo năm,
theo mã); kiểm tra 09–12/2024 **khoá** tới khi bạn đồng ý mở (một lần, cho cấu hình đã chốt).

| # | Đo | Null / so với |
|---|---|---|
| M1 | Tỷ lệ thời gian mỗi trạng thái, tỷ lệ Uncertain, theo mã × năm | các baseline |
| M2 | Độ bền: số lần đổi / ngày; độ dài đoạn trung vị, IQR, P90; % đoạn < 4 nến | baseline «không đổi»; các baseline |
| M3 | Trễ phát hiện và báo động giả so với ranh giới **nhãn hậu kiểm** (họ tham số: DC / Lunde–Timmermann θ ∈ {1, 2, 4} ATR; trend-scanning vài L) — dùng matcher điểm sẵn có, dung sai theo nến | baseline «không đổi»; `dc_regime`; ADX |
| M4 | **Tuổi thọ còn lại sau phát hiện** = (độ dài đoạn tham chiếu − trễ) / độ dài | — (chỉ số «router có gì để khai thác») |
| M5 | Độ tách kết cục tương lai (h ∈ {4, 16, 64} nến): ER tương lai, biên độ / ATR_t, «chạm +k·ATR trước −k·ATR», «về giữa range trước khi phá biên» — **trong từng tầng ATR**; khoảng tin cậy bootstrap theo khối | **shift test** trên chuỗi trạng thái; các baseline |
| M6 | Giá trị cận biên của bằng chứng ICT: M5 của «điểm» có / không có G1–G3 (chỉ G4) | shift test; báo lực thống kê (hiệu ứng nhỏ nhất phát hiện được) |
| M7 | Breakout: tỷ lệ đi tiếp / thất bại, biên độ sau phá | **mức ngẫu nhiên** cùng khoảng cách ATR, cùng giờ New York, cùng tầng ATR (mở rộng `matched_hour_atr_v1`) |
| M8 | Đồng thuận giữa các bộ phân loại (theo từng lớp) | giá trị kỳ vọng khi độc lập |
| M9 | So nhãn tay (4d): ma trận nhầm lẫn, F1 từng lớp, trễ; κ chỉ kèm cảnh báo mất cân bằng lớp | đồng thuận khi bạn tự gán lại |
| M10 | Đường risk–coverage (chọn vùng chết) | — |
| M11 | Ổn định: cấu hình chốt trên dev, đo trên dev mở rộng theo năm/mã rồi đoạn kiểm tra; cùng dấu qua các năm; bảng độ nhạy tham số | — |
| M12 | Nhân quả: prefix = chạy trọn rồi cắt; sửa nến sau t không đổi regime ≤ t; replay | test bắt buộc |
| M13 | Overfit: liệt kê mọi cấu hình đã thử; nếu chọn theo một thước đo thì báo xác suất overfit (CSCV) | — |

**Baseline:** `dc_regime` (chạy lại trên dataset đúng giờ — số cũ đo trên dataset lệch giờ), `indicator_baseline`
(ADX/Donchian), `hmm_online`, và jump model online (chỉ trong script nghiên cứu, Q4). Không baseline nào là «sự thật».

Không bao giờ: accuracy theo từng nến làm thước đo chính (phạt mọi bộ nhân quả ở đầu đoạn); t-test theo nến (cỡ mẫu
hiệu dụng là số đoạn); chọn ngưỡng sau khi xem đoạn kiểm tra; nói «tốt hơn» khi chưa có nhãn và null.

---

## 7. Nhãn regime (4d)

- **Dạng nhãn — không đổi schema:** nhãn điểm «regime X bắt đầu từ nến này» (`REGIME_TREND_UP`… như loại nhãn mới
  của thuật toán, cơ chế `label_types` sẵn có). Chuỗi nhãn điểm liên tiếp trong khoảng coverage = một phân đoạn →
  vừa chấm trễ / P / R bằng matcher điểm, vừa dựng được ma trận nhầm lẫn theo nến (cần thêm một phép chấm «theo đoạn»
  trong `core/eval/`, tăng `PROTOCOL_VERSION`).
- **Rubric** viết trước khi gán, kèm ví dụ ảnh: Trend = gì, Range = gì, khi nào gọi Uncertain; gán **hồi cứu** (được
  nhìn cả đoạn) — nhãn chỉ để đánh giá.
- **Khối lượng đề xuất:** XAUUSD M15, 2 tuần dev + 2 tuần kiểm tra (cùng cửa sổ D8); bạn tự gán lại 1 tuần dev sau ≥
  7 ngày, không xem bản cũ → đồng thuận với chính mình làm «trần» cho M9.
- Nhãn D8 (ITH/ITL + shift) vẫn là việc riêng của `ict_structure`, không chặn giai đoạn 4.

---

## 8. Lộ trình

| Bước | Nội dung | Nghiệm thu |
|---|---|---|
| **4a Khảo sát** | Script `research/regime_survey.py` (chỉ đọc DB, đoạn dev): (1) đo lại baseline M1–M2 trên dataset đúng giờ; (2) dựng nhãn hậu kiểm họ θ, đo M3–M4 cho baseline và cho bằng chứng thô (order flow, thứ tự H1); (3) phân phối + tương quan G1–G4; (4) tỷ lệ thời gian của hai biến thể với tham số nháp + lưới (H, c, θ, W, N_r, k, B); (5) M5–M6 sơ bộ | Báo cáo `docs/research/khao_sat_regime.md` + JSON tái lập; bạn duyệt ngưỡng; **cổng đi / dừng** (dưới) |
| **4b Đặc tả + code** | `docs/algorithms/thuat_toan_ict_regime.md`; `core/algorithms/ict_regime/` 0.1.0 (hai biến thể); test tính tay, nhân quả, Dữ liệu thiếu / Khởi động, replay; giao diện dải + dòng trạng thái | pytest toàn repo; hồi quy: `ict_structure` và mọi thuật toán khác **không đổi**; kiểm độc lập |
| **4c Đánh giá không nhãn** | M1–M8, M11 (dev mở rộng), M12, M13; jump model online trong script | Báo cáo có null, khoảng tin cậy, lực thống kê |
| **4d Nhãn** | Rubric, loại nhãn regime, phép chấm theo đoạn; bạn gán; M9–M10 | Bộ nhãn lưu có `revision`, coverage; đồng thuận tự gán lại |
| **4e Kiểm tra + bàn giao** | Mở đoạn kiểm tra một lần cho cấu hình đã chốt; xuất `RegimeEstimate` cho repo giao dịch (E1 ở đó) | Báo cáo cuối; tài liệu hợp đồng xuất |

**Cổng sau 4a (đề xuất):** nếu với mọi bộ phát hiện (kể cả baseline), trung vị «tuổi thọ còn lại sau phát hiện» (M4)
ở M15 dưới khoảng một phần tư độ dài đoạn tham chiếu, thì regime M15 khó dùng cho router dù «đúng». Khi đó báo lại và
đề xuất chạy regime ở H1 (cùng thuật toán, dataset H1) trước khi làm 4b.

---

## 9. Câu hỏi cần bạn chốt

| # | Câu hỏi | Đề xuất |
|---|---|---|
| Q1 | Code regime ở đâu? | **Thuật toán mới `ict_regime`** chạy `ict_structure` bên trong và chỉ đọc đầu ra của nó. Đổi luật regime không làm đổi phiên bản `ict_structure`; giữ đúng B3 («không ghép trong bộ nhận diện»). |
| Q2 | Tập trạng thái | Trend ↑ / Trend ↓ / Range / Breakout ↑↓ (chuyển tiếp ≤ B nến, có sự kiện phá vỡ thất bại) / Uncertain (có lý do) + Khởi động + Dữ liệu thiếu. **Event-risk để sau** — cần lịch tin, không suy được từ OHLC. Regime tính ở khung của run (M15 mặc định), H1/H4 là ngữ cảnh. |
| Q3 | Pha «hồi / mở rộng» trong Trend | Có, là **trường mô tả**, không phải regime. |
| Q4 | Thêm nhóm G4 (hiệu quả giá Kaufman ER, không phải ICT) và jump model làm baseline? | **Có.** G4 là một phiếu trong «điểm» và là mốc để đo bằng chứng ICT có thêm gì (M6). Jump model chỉ trong script nghiên cứu, không thành thuật toán của lab. |
| Q5 | Cây luật «kịch bản» §4.3 | Dùng bản nháp; bạn sửa chỗ nào khác cách bạn đọc chart (nhất là K1 — Trend cần những gì — và K3 — Range kiểu ICT). Đây là phần «kịch bản bias của bạn» trong plan gốc. |
| Q6 | Router trong lab? | **Không.** Lab dừng ở regime + bản xuất `RegimeEstimate`; router và phép thử E1 (có chi phí) ở repo giao dịch. |
| Q7 | Nhãn regime | Nhãn điểm «regime bắt đầu từ đây» (không đổi schema), 2 tuần dev + 2 tuần kiểm tra XAUUSD M15, tự gán lại 1 tuần; làm ở 4d, sau khi 4a–4c xong. |

---

## 10. Rủi ro và giới hạn

- **Bằng chứng ICT có thể không thêm thông tin** so với G4 / baseline (đã thấy ở order flow). Plan đo điều này (M6) và
  báo cả kết quả âm tính kèm lực thống kê; regime vẫn dùng được như lớp mô tả có giải thích.
- **Range khó định nghĩa** (baseline DC gần như không bao giờ ra Range). 4a đo tỷ lệ thời gian trước khi chốt.
- **Trễ:** mọi bằng chứng cấu trúc đều trễ (pivot ~5 nến, run W = 3 nến); hysteresis thêm trễ. M3–M4 đo trực tiếp.
- **Một mã, một năm** ở đoạn dev chính; dev mở rộng 2018–2023 và EURUSD để kiểm độ bền.
- **Nhãn của một người:** đồng thuận tự gán lại chỉ là trần gần đúng.
- Không có nghiên cứu nào chứng minh định tuyến pullback / mean reversion theo regime ở M15 FX/vàng có lợi — đó là câu
  hỏi của E1 ở repo giao dịch, không phải kết luận của lab.
