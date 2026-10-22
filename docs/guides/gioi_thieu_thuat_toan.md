# Giới thiệu các thuật toán của lab — và cách mở rộng sang quant

Ngày 19/10/2026, theo code hiện tại (`ict_structure` 0.4.2; cập nhật 21/10/2026: 0.5.0 thêm order block, OTE; 0.6.x–0.9.1 thêm lớp nhận diện: trạng thái (v2 từ 0.9.0), khoảng giá + xác suất chạm (vùng, biên range, PDH / PDL), còn giữ / thời gian còn lại / phá biên). Đây là **bản đồ và lời giới thiệu**: mỗi thuật toán
trả lời câu hỏi gì, chạy ra sao, chỉnh tham số nào, đã đo được gì, dùng vào thí nghiệm quant thế nào. Định nghĩa
chuẩn nằm ở đặc tả từng thuật toán trong [`docs/algorithms/`](../algorithms/) — chỗ nào khác nhau thì đặc tả đúng.

Luật làm việc của lab: [`AGENTS.md`](../../AGENTS.md). Học nền định lượng: [`docs/hoc_quant/`](../hoc_quant/README.md).

---

## 0. Đọc nhanh

1. **Sáu thuật toán, ba nhóm.**
   - *Cấu trúc swing cổ điển:* `swing_pivot` (baseline có BOS/CHoCH, giữ cố định để so), `swing_hierarchy`.
   - *Cấu trúc ICT/SMC:* `ict_structure` (thuật toán chính, giai đoạn 1–3 đã xong). `c2_cisd_research` đã gỡ ngày 21/10/2026.
   - *Trạng thái thị trường (regime) và đối chứng:* `dc_atr_structure`, `indicator_baseline`, `hmm_online`.
2. **Mọi thuật toán chạy từng nến đã đóng** và chỉ dùng thông tin đã biết. Mỗi sự kiện có hai mốc: nến nó xảy ra
   và nến thuật toán **biết** nó (`confirmed_at`). Đọc kết quả mà quên mốc thứ hai là tự lừa mình.
3. **Đã đo được** (đoạn phát triển, mọi dữ liệu trước 01/09/2024):
   - order flow kiểu ICT **không dự báo** phía thanh khoản bị lấy kế tiếp tốt hơn ngẫu nhiên (lệch trong ±2 điểm %);
   - khi phân loại Trend/Range, bằng chứng ICT **không thêm thông tin đo được** so với một chỉ số thống kê đơn giản
     (Kaufman ER) — khảo sát 4a;
   - các bộ Trend/Range có sẵn gần như không nhận ra Range (`dc_regime` 0%), HMM lật 33 lần/ngày;
   - **chưa có nhãn tay**, nên chưa thuật toán nào có precision / recall / F1.
4. **Muốn thử quant:** bắt đầu bằng một script đọc dữ liệu qua [`research/hoc_quant/hoc.py`](../../research/hoc_quant/hoc.py)
   (§6.2). Khi cần chart, replay hay chấm điểm thì mới đưa thành thuật toán của lab (§6.3). Nên thử gì: §6.6 và
   [`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md) (287 phương pháp, 18 cái đề xuất thử trước).

---

## 1. Bản đồ

| Thuật toán | Tên trên giao diện | Bản | Trả lời câu hỏi | Đầu ra chính | Độ chín |
|---|---|---|---|---|---|
| [`swing_pivot`](../algorithms/thuat_toan_swing_pivot.md) | Swing Pivot + HH/HL/LH/LL + BOS/CHoCH | 1.1.0 | Đỉnh/đáy nào? Cấu trúc đã bị phá chưa? | swing, HH/HL…, BOS / BOS nội bộ / CHoCH | Ổn định — mốc so sánh cố định |
| [`swing_hierarchy`](../algorithms/thuat_toan_swing_cap_2.md) | Swing phân cấp (cấp 1 + cấp 2) | 1.0.0 | Đỉnh/đáy nào là cấu trúc, đỉnh nào là nhiễu? | swing cấp 2 + HH/LH cấp 2 | Thí nghiệm |
| [`ict_structure`](../algorithms/thuat_toan_ict_structure.md) | Cấu trúc ICT phân tầng + khung lớn + order flow | 0.9.1 | Giá vừa lấy thanh khoản phía nào? Có shift chưa? Khung lớn nghiêng về đâu? Order block / OTE của shift ở đâu? Đang trend, range hay sideway; 1–4 giờ tới giá có thể đi trong khoảng nào? | ~40 loại sự kiện, timeline ~50 cột | Đang phát triển |
| [`dc_atr_structure`](../algorithms/thuat_toan_dc_atr_structure.md) | DC theo close + ATR (Trend/Range, nghiên cứu) | 0.2.0 | Giá đã đảo chiều đủ k × ATR chưa? Trend hay Range? | pivot DC, regime, Range | Nghiên cứu |
| [`indicator_baseline`](../algorithms/thuat_toan_indicator_baseline.md) | Baseline chỉ báo (SMA/ATR, ADX, Donchian) | 1.0.0 | Mốc đơn giản: chỉ báo phổ thông nói Trend hay Range? | lớp up / down / range / uncertain | Đối chứng cố định |
| [`hmm_online`](../algorithms/thuat_toan_hmm_online.md) | HMM lọc online (forward, hmmlearn) | 1.0.0 | Mô hình trạng thái ẩn thấy mấy «chế độ» lợi suất/biến động? | đổi trạng thái | Đối chứng thống kê, trạng thái chưa gán nghĩa |

Dữ liệu đi qua lab như sau:

```text
dataset (nến đã đóng, giờ UTC)
   │  thuật_toán.on_bar(nến t) — chỉ thấy nến ≤ t
   ▼
sự kiện (lưu DB) + timeline trạng thái mỗi nến + pending_state
   │
   ├─► trang Thử nghiệm: chart, replay từng nến, khung «Thuật toán đang làm gì»
   ├─► trang Gán nhãn: nhãn tay độc lập ──► trang Đánh giá: P / R / F1, độ trễ, chuẩn ngẫu nhiên
   └─► script research/ (chỉ đọc DB) ──► báo cáo docs/research/ + JSON tái lập
```

Vị trí của lab trong sản phẩm AI Trading Copilot ([`nghien_cuu_regime_copilot_va_repo_cu.md`](../research/nghien_cuu_regime_copilot_va_repo_cu.md)):

```text
cấu trúc & đặc trưng giá (LAB NÀY) ─► regime: Trend / Range / Breakout / Uncertain ─► router: Trend Pullback · Range MR · No Trade
                                      (giai đoạn 4 — plan_bias_regime.md)            (repo giao dịch, có chi phí)
```

Lab dừng ở bằng chứng và regime. Lab **không** tính P&L hay win rate; giá trị giao dịch đo ở repo giao dịch.

---

## 2. Khái niệm chung — đọc trước khi đọc kết quả

### 2.1. Nến đã đóng và «lúc biết»

Thuật toán nhận nến qua `on_bar(nến)`, theo thứ tự thời gian, và không có cách nào đọc nến sau. Một pivot 3/3 có
đỉnh ở nến 100 chỉ được **biết** khi nến 103 đóng:

| Trường | Nghĩa |
|---|---|
| `event_bar_index`, `event_time` | Nến chứa cấu trúc (đỉnh ở nến 100) |
| `confirmed_bar_index`, `confirmed_at` | Nến mà thuật toán biết (nến 103, lúc nó đóng) |
| `confirmation_lag_bars` | Trễ xác nhận (3 nến) |

Chart vẽ đỉnh ở nến 100 cho dễ nhìn, nhưng mọi phép đo «dùng được lúc nào» phải dùng `confirmed_at`. Replay chỉ hiện
đối tượng khi con trỏ ≥ nến xác nhận.

### 2.2. Bốn loại đầu ra

| Đầu ra | Là gì | Lưu ở đâu |
|---|---|---|
| **Sự kiện** | Mỗi dòng một cấu trúc vừa xác nhận: loại, giá, hai mốc thời gian, mã lý do, tham chiếu sự kiện trước, `details` | Bảng `events` (khi tick «Lưu lần chạy»), CSV |
| **Timeline** | Trạng thái **sau** mỗi nến (thứ tự đỉnh/đáy, vùng gần nhất, order flow…) | Không lưu DB — mở lại run = chạy lại |
| **`pending_state`** | Trạng thái nội bộ ở nến cuối / con trỏ replay: cái gì đang chờ, điều gì sẽ làm đổi trạng thái | Chỉ trong phiên |
| **`run_stats`** | Thống kê của lần chạy (tỷ lệ thời gian, số lần đổi, độ dài đoạn…) | Cột `stats_json` của run |

Giá trị timeline ở nến t là trạng thái sau t: dùng được từ lúc nến t đóng (tức để quyết định ở t+1).

### 2.3. Tái lập và phiên bản

- `event_id` tất định: cùng dữ liệu + tham số → cùng bộ `event_id`.
- Run lưu tham số, phiên bản thuật toán và checksum dataset. Mở lại một run = chạy lại và báo «khớp» hay «khác».
- Đổi output mặc định → **tăng phiên bản**, kèm bảng khác biệt và hồi quy
  (`scripts/regression_saved_runs.py --snapshot / --compare`). Không bao giờ âm thầm đổi kết quả cũ.

### 2.4. Warm-up và khoảng trống

Mỗi thuật toán cần một số nến đầu trước khi có kết quả (warm-up). Khoảng trống giữa hai nến (nghỉ phiên, cuối tuần,
thiếu dữ liệu) được xử lý khác nhau:

| Thuật toán | Cách xử lý khoảng trống |
|---|---|
| `swing_pivot`, `swing_hierarchy`, `indicator_baseline`, `hmm_online` | Không xét — chuỗi nến được coi là liền |
| `ict_structure` | Phân loại theo **lịch phiên khai báo** (`data/calendars/`): nghỉ phiên / cuối tuần / lễ là bình thường; thiếu dữ liệu trong phiên là bất thường → chặn cửa sổ pivot, FVG, displacement vắt qua nó, gắn marker «thiếu» |
| `dc_atr_structure` | `reset` (mặc định): mỗi khoảng trống cắt segment, warm-up lại; `bridge_short`: nối khoảng trống ≤ 2 giờ |

### 2.5. ATR

Mọi ngưỡng «× ATR» dùng ATR Wilder 14. Có hai cách khởi tạo: `WilderATR` (nến đầu lấy high − low; dùng ở
`indicator_baseline`, trang Đánh giá) và `WilderATRPrevClose` (cần close trước; dùng ở `dc_atr_structure`,
`ict_structure`). So số giữa các thuật toán thì nhớ điều này — chỉ khác ở vài nến đầu.

---

## 3. Từng thuật toán

### 3.1. `swing_pivot` — baseline cấu trúc cổ điển

**Để làm gì.** Định nghĩa «theo sách» của swing, HH/HL và BOS/CHoCH. Giữ cố định (v1.1.0) để mọi thứ khác có một mốc
so sánh.

**Chạy thế nào.**
- **Pivot:** nến c là đỉnh khi high[c] lớn hơn **tuyệt đối** high của `left` nến trái và `right` nến phải (mặc định 3/3).
  Bằng nhau → không phải pivot. Biết ở nến c + `right`.
- **Nhãn:** so với swing cùng phía trước đó → HH / LH / EQH, HL / LL / EQL (EQ khi chênh trong dung sai).
- **Phá vỡ:** close vượt mức swing đang hoạt động → BOS. Khi đã có bias (HH+HL = tăng, LH+LL = giảm) thì phân loại:
  phá mức chính cùng chiều = BOS chính, phá đỉnh/đáy hồi = BOS nội bộ, phá mức chính ngược chiều = CHoCH. Dùng close,
  không dùng râu; mỗi mức chỉ phát một lần.

| Tham số | Mặc định | Chỉnh thì sao |
|---|---|---|
| `left`, `right` | 3, 3 | Lớn hơn → ít swing hơn, trễ đúng bằng `right` nến |
| `label_eq_tolerance` | 0 | Lớn hơn → nhiều EQH/EQL hơn |
| `bos_buffer` | 0 | Close phải vượt thêm bao nhiêu mới tính phá |
| `enable_bos`, `enable_choch` | bật | Tắt CHoCH → mọi phá vỡ là BOS như v1.0.0 |

**Đã đo:** XAUUSD M15 2024, pivot 3/3 cho ~17 swing/ngày (pivot 1/1: ~42). M15 8 năm chạy ~5 s.
**Giới hạn:** không đa khung, không volume; nến bằng giá làm mất pivot.
**Dùng khi thử quant:** mốc «cấu trúc theo sách» để so mọi định nghĩa mới; `bias` là một đặc trưng hướng đơn giản.

### 3.2. `swing_hierarchy` — lọc đỉnh/đáy cấu trúc

**Để làm gì.** Bớt nhiễu của pivot nhỏ: chỉ coi là cấu trúc những đỉnh nổi lên trên chính chuỗi pivot.

**Chạy thế nào.**
- Cấp 1 = pivot như `swing_pivot`.
- Cấp 2: trong ba đỉnh cấp 1 **liên tiếp**, đỉnh giữa cao hơn hai đỉnh bên → đỉnh cấp 2 (cách của Larry Williams).
  Biết khi đỉnh cấp 1 bên phải được xác nhận, nên trễ hơn cấp 1.
- HH / LH chỉ so giữa hai đỉnh cấp 2. Không có BOS.

| Tham số | Mặc định | Chỉnh thì sao |
|---|---|---|
| `left`, `right` | 3, 3 | Như `swing_pivot` (cho cấp 1) |
| `label_eq_tolerance` | 0 | Dung sai HH/EQH giữa hai đỉnh cấp 2 |
| `emit_level1` | bật | Phát thêm swing cấp 1 để đối chiếu trên chart |

`ict_structure` dùng đúng ý tưởng này với nền pivot 1/1 (ITH/ITL ≈ 10 mỗi ngày ở M15, trễ trung vị 5 nến).

### 3.3. `ict_structure` — cấu trúc ICT phân tầng (thuật toán chính)

**Để làm gì.** Mô tả cấu trúc theo cách đọc ICT, nhân quả và có giải thích từng bước, làm bằng chứng cho tầng regime.
Theo quyết định của bạn: **không có BOS/CHoCH** — đổi hướng chỉ đến từ *shift* (quét thanh khoản rồi displacement
ngược chiều).

**Các thành phần** (mỗi cái một file trong [`core/components/`](../../core/components/), dùng lại được cho thuật toán khác):

| Mã | Thành phần | Làm gì | Sự kiện |
|---|---|---|---|
| [G] | `session_gap.py` | Phân loại khoảng trống theo lịch phiên khai báo | `ICT_GAP` |
| [P1] | `swing_source.py` | Pivot strict 1/1 → STH/STL | `SWING_HIGH/LOW` |
| [S1] | `hierarchy.py` | Cấp 2 ITH/ITL, cấp 3 LTH/LTL | `SWING_*_L2`, `SWING_*_L3` |
| [S2] | `structure_order.py` | Thứ tự đỉnh/đáy (+1 / −1 / lẫn lộn), mức được bảo vệ, cờ «close đã vượt» | timeline `order`, `protected*` |
| [S4] | `dealing_range.py` | Dealing range, premium / EQ / discount | timeline `dealing_*`, `zone` |
| [P3] | `displacement.py` | Nến biên độ ≥ k × ATR, thân lớn | `DISPLACEMENT_*` |
| [P2] | `fvg.py` | FVG ba nến + vòng đời chạm → lấp | `FVG_UP/DOWN/TOUCHED/FILLED` |
| [S3]/[E2] | `liquidity.py` | Vùng thanh khoản BSL/SSL từ ITH/ITL (và H1/H4/ngày/tuần); vòng đời chạm → lấy → **sweep** (quay lại trong W nến) / **run** (không quay lại) / chưa rõ | `LIQ_SWEEP_*`, `LIQ_RUN_*`, `LIQ_UNRESOLVED` |
| [E3] | `shift.py` | Sweep rồi displacement ngược chiều trong cửa sổ → shift (+ FVG của chính nến displacement) | `SHIFT_*`, `SHIFT_FVG_*` |
| [C] | `killzone.py` | Cờ giờ New York (Asia, London, NY AM, London close) — không lọc gì | trong `details` |
| [OF] | `order_flow.py` | Order flow tăng / giảm / chưa rõ: run hoặc shift đặt chiều; run phía ngược → chưa rõ; shift lật thẳng | `ORDER_FLOW_*` |
| [T] | `core/data/htf_stream.py`, `htf_stack.py`, `period_levels.py` | Gộp H1/H4/ngày/tuần theo mốc 17:00 New York, **chỉ nến đã chốt**; cấu trúc khung lớn; PDH/PDL, PWH/PWL | `HTF_SWING_*`, `HTF_FVG_*`, `HTF_PERIOD_*`, `HTF_BAR_DEGRADED` |
| [S5] | `pd_array.py` | Phản ứng của giá ở FVG H1/H4 → `pd_bias` | `PD_RESPECT_*`, `PD_DISRESPECT_*` |
| [S6] | `dol.py` | DOL: sau mỗi shift, đích = vùng thanh khoản gần nhất phía shift (tầng ≥ H1) | `DOL_REACHED` |

Mỗi nến đi qua 12 bước theo thứ tự cố định ([đặc tả §4.1](../algorithms/thuat_toan_ict_structure.md)); thứ gì biết ở
nến t chỉ có hiệu lực từ t+1. Ba thành phần bias (thứ tự đỉnh/đáy, phản ứng ở FVG khung lớn, DOL) **để riêng**, không
ghép thành một «bias tổng hợp» — ghép là việc của giai đoạn 4.

**Lịch sử:** 0.1.0 (05/10/2026, giai đoạn 1) → 0.2.0 (giai đoạn 2: displacement, FVG, thanh khoản, shift) → 0.3.0
(order flow) → 0.4.0 (08/10, khung lớn) → 0.4.1 (bỏ ảnh chụp khung lớn ở sự kiện «nguyên liệu» cho nhẹ) → 0.4.2
(19/10, sửa hai chỗ hở ở dữ liệu ngoài lịch phiên) → 0.5.0 (21/10, order block và OTE neo vào SHIFT — đặc tả §4.20–§4.21;
8 tham số nâng cao `ob_*`, `ote_*`; mọi output cũ giữ nguyên) → 0.6.0 (21/10, lớp nhận diện: khoảng giá + xác suất
chạm + trạng thái, tự chấm trong lần chạy — đặc tả [`thuat_toan_nhan_dien.md`](../algorithms/thuat_toan_nhan_dien.md);
7 tham số nâng cao `nd_*`; mọi output cũ giữ nguyên).

**Tham số.** Trên form, 11 tham số hay chỉnh nằm trên; 12 tham số còn lại — phản ứng ở FVG khung lớn, DOL, PDH/PDL,
sự kiện khung lớn và nhóm cấu hình ở dòng cuối bảng — nằm trong mục «Tham số nâng cao» gập sẵn. Dòng giải thích của mỗi ô hiện khi bấm vào ô đó. Số đo trên XAUUSD M15
01–08/2024, mỗi lần đổi **một** tham số so với mặc định:

| Tham số (tên trên form) | Mặc định | Đổi thì sao |
|---|---|---|
| Số nến trái / phải (STH/STL) | 1 / 1 | Trái = 3 → ITH/ITL từ 10,2 còn 6,2/ngày, trễ 5 → 10 nến. Phải = 3 → 6,3/ngày, trễ 8 |
| Cấp cấu trúc | 2 | 1 → thứ tự đổi 18,5 lần/ngày (rất nhiễu); 3 → 1,4 lần/ngày nhưng trễ ~23 nến |
| Dung sai bằng giá (× ATR) | 0,1 | 0 → thứ tự «lẫn lộn» 43% thời gian; 0,3 → 54% |
| Ngưỡng «lấy» thanh khoản (× ATR) | 0,1 | 0 → 76% lượt lấy là sweep; 0,5 → 56% (lượt sâu hay thành run) |
| **Cửa sổ sweep W (nến)** | 3 | Mạnh nhất. W = 0 → sweep 44%, shift 0,32/ngày; W = 12 → sweep 83%, shift 1,1/ngày. Run được báo trễ W nến |
| Displacement: biên độ ≥ k × ATR | 1,5 | % nến displacement: 1,0 → 16,5%; 2,0 → 3,3%. Shift/ngày 1,71 / 0,45 |
| Displacement: thân ≥ tỷ lệ biên độ | 0,6 | 0,4 → 10,7% nến; 0,8 → 3,0% |
| Cửa sổ shift (nến) | 3 | 1 → 0,67 shift/ngày; 12 → 1,25 |
| FVG: kích thước tối thiểu (× ATR) | 0 | 0,25 → FVG M15 từ 18 còn 9,4/ngày (lọc cả FVG khung lớn) |
| Khung lớn | `H1,H4` | Để trống → tắt khung lớn (không có pd_bias, vùng H1/H4) |
| Phản ứng ở FVG khung lớn, Tôn trọng chặt | chặt, 1,0 | Chỉ đổi pd_bias — vốn nhiễu với mọi cách đặt |
| DOL: tầng vùng tối thiểu | H1 | Cao hơn → đích xa hơn, DOL «đang có» lâu hơn (65% → 75% thời gian) |
| Lịch phiên, khung của dataset, mốc nến khung lớn, độ đủ dữ liệu, killzone, chu kỳ ATR, khoảng trống dữ liệu | — | Để mặc định (cấu hình dữ liệu hoặc chỉ để đối chiếu) |

**Số đo mặc định** (XAUUSD M15 01–08/2024):

| Đại lượng | Giá trị |
|---|---|
| STH/STL · ITH/ITL mỗi ngày | 40 · 10,2 (trễ trung vị ITH/ITL 5 nến) |
| Thứ tự đỉnh/đáy tăng / giảm / lẫn lộn | 30 / 22 / 48% thời gian |
| Nến displacement · FVG M15 | 7,4% số nến · 18/ngày |
| Lượt lấy thanh khoản | 7,8/ngày, 72% là sweep |
| Shift | 0,88/ngày |
| Order flow tăng / giảm / chưa rõ | 46 / 30 / 24% thời gian, đổi 1,7 lần/ngày, đoạn một chiều trung vị ~13 giờ |
| pd_bias tăng / giảm | 53 / 47% (đổi ~410 lần trong 8 tháng — nhiễu) |
| Có DOL | 65% thời gian |
| Tốc độ | 47 000 nến M15 ~2 s; M15 6,5 năm ~9 s |

**Trên chart.** Chế độ *Gọn* (BSL/SSL từ đỉnh/đáy gốc, sweep/run, «Shift ↓/↑» + FVG, dải order flow có chữ, dòng
trạng thái), *Chi tiết* (ITH/ITL, mức được bảo vệ, Premium/EQ/Discount, hộp FVG, displacement), nhóm *Khung lớn*
(ITH/ITL H4, range H4, FVG H4, PDH/PDL, nến H4 đang hình thành). Replay có khung «Thuật toán đang làm gì».

**Đã biết từ nghiên cứu.**
- Order flow là **mô tả** (giá vừa lấy gì), không phải dự báo:
  [`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md).
- Shift cùng chiều thứ tự H1 38% so với 28% ngẫu nhiên — chỉ 55 shift, chưa đủ để làm bộ lọc
  ([`plan_ict_structure.md`](../plans/plan_ict_structure.md) §11.2).
- Khảo sát 4a: dùng các bằng chứng này để gán regime không tốt hơn Kaufman ER
  ([`khao_sat_regime.md`](../research/khao_sat_regime.md)).

**Giới hạn.** Chưa có nhãn ITH/ITL + shift (việc D8) nên chưa có F1. Mọi ngưỡng là *tham số thí nghiệm*. Chậm hơn 0.3.0
khoảng 2,4 lần vì khung lớn.

### 3.4. `dc_atr_structure` — Directional Change + Trend/Range

**Để làm gì.** Định nghĩa swing không theo cửa sổ nến mà theo **biên độ**: đỉnh được xác nhận khi giá đóng cửa đã lùi
≥ Δ từ cực trị, Δ = k × ATR (hoặc %). Từ chuỗi pivot DC, phân loại Trend/Range.

**Chạy thế nào.**
- Detector tìm cực trị theo close, khoá Δ tại nến cực trị; close lùi đủ Δ → xác nhận `DC_HIGH` / `DC_LOW`.
- Regime (`dc_regime`): Trend tăng = hai đỉnh và hai đáy gần nhất đều tăng (HH + HL, dung sai 0,1 ATR); Trend giảm đối
  xứng. Range = 3 đỉnh và 3 đáy gần nhất tụ trong 0,5 ATR, rộng ≥ 1 ATR, close nằm trong biên. Thoát Range khi close
  ra ngoài biên ± 0,25 ATR. Còn lại → UNKNOWN (kèm lý do).

| Tham số | Mặc định | Chỉnh thì sao |
|---|---|---|
| `atr_multiplier` (k) | 1,5 | Lớn hơn → ít pivot, nhịp dài hơn, trễ hơn |
| `threshold_mode` | atr | `percent` dùng `reversal_pct` thay cho ATR |
| `gap_policy` | reset | `bridge_short`: nối khoảng trống ≤ 2 giờ — bớt warm-up lại sau nghỉ phiên |
| `range_*` | 3 / 0,5 / 1,0 / 0,25 | Điều kiện Range; hiện quá chặt |

**Đã đo** (khảo sát 4a, XAUUSD M15 2024 đúng giờ): `reset` — Uncertain 80%, Range 0,0%, đổi 1,1 lần/ngày; `bridge_short`
— Uncertain 50%, đổi 2,7 lần/ngày. **Range gần như không bao giờ xuất hiện** do chính điều kiện Range.
**Lưu ý:** `research/dc_experiment.py` mặc định chạy dataset lệch giờ cũ (để tái lập số trong đặc tả) — thí nghiệm mới
truyền `--dataset ds_db1583cd4dde`.

### 3.5. `indicator_baseline` — đối chứng chỉ báo

**Để làm gì.** Mốc «không cần nghĩ nhiều»: nếu một thuật toán phức tạp không hơn được mấy chỉ báo phổ thông thì chưa
đáng dùng. Công thức viết tay, khớp MQL5 (`iMA` SMA, `iATR`, `iADX` Wilder), không dùng TA-Lib.

**Luật** (xét theo thứ tự): ADX ≥ 20 và |độ dốc SMA20 trên 5 nến| / ATR ≥ 0,15 → up / down theo dấu độ dốc;
Donchian 20 / ATR ≤ 3 và ADX < 20 → range; còn lại → uncertain. Phát sự kiện khi lớp đổi.

**Tham số:** `sma_period` 20, `slope_lookback` 5, `atr_period` 14, `adx_period` 14, `range_period` 20, `slope_min` 0,15,
`adx_trend_min` 20, `range_narrow_max` 3,0 — điểm xuất phát để so, không phải ngưỡng tối ưu.

**Đã đo** (4a): up / down / range / uncertain = 31 / 25 / 5 / 38% thời gian, đổi 8,3 lần/ngày, đoạn trung vị 6 nến. Ở
nhịp dài (10–15 giờ) là bộ phát hiện giữ đúng chiều tốt nhất trong 4a — nhưng chỉ 0,39–0,44 phần đoạn so với mốc ngẫu
nhiên 0,28–0,30.

### 3.6. `hmm_online` — mô hình trạng thái ẩn, lọc online

**Để làm gì.** Đối chứng thống kê: để dữ liệu tự chia «chế độ» mà không áp định nghĩa ICT.

**Chạy thế nào.** `GaussianHMM` (hmmlearn) 3 trạng thái trên ba đặc trưng: lợi suất log, |lợi suất|, (high − low) /
close. **Fit một lần** trên `train_bars` nến đầu; sau đó mỗi nến chỉ chạy bước lọc forward với tham số đã đóng băng —
không Viterbi, không làm trơn, nên không nhìn tương lai. Trạng thái **chưa gán nghĩa** (`chua_gan_nghia`).

**Tham số:** `n_states` 3, `train_bars` 80, `seed` 42, `n_iter` 50, `state_map` (gán nghĩa — là quyết định nghiên cứu,
phải ghi lại).

**Đã đo** (4a, fit trên 2000 nến đầu): lật 33 lần/ngày, 86% đoạn ngắn hơn 4 nến. Trạng thái tách theo **biến động**
chứ không theo hướng — khớp tài liệu (HMM trên lợi suất FX tách theo độ lớn dao động).
**Giới hạn:** fit trên phần đầu của chính chuỗi rồi lọc tiếp — không phải walk-forward; không refit.

### 3.7. Nguyên mẫu nghiên cứu (chưa phải thuật toán của lab)

Các script trong [`research/`](../../research/) đọc DB ở chế độ chỉ đọc, từ chối đoạn kiểm tra, ghi JSON có checksum:

| Script | Làm gì | Kết quả |
|---|---|---|
| [`ict_survey.py`](../../research/ict_survey.py) | Bản mẫu định nghĩa ICT trước khi cài (swing các cấp, FVG, thanh khoản, shift, pd_bias, DOL, hồ sơ khung) | [`khao_sat/ict_survey_dev.json`](../research/khao_sat/ict_survey_dev.json), số ở `plan_ict_structure.md` §2, §11 |
| [`orderflow_survey.py`](../../research/orderflow_survey.py) | 7 cách đọc order flow × M5–H4 × XAU/EUR: có đoán được phía thanh khoản bị lấy kế tiếp không | [`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md) — không, ±2 điểm % |
| [`orderflow_rules.py`](../../research/orderflow_rules.py) | So các quy tắc «chưa rõ» của dải order flow | quy tắc A được chọn |
| [`regime_survey.py`](../../research/regime_survey.py) | Khảo sát 4a: hai biến thể regime «kịch bản» / «điểm», nhãn hậu kiểm (DC, trend-scanning), độ bền, trễ, kết cục tương lai với null dịch vòng | [`khao_sat_regime.md`](../research/khao_sat_regime.md) — cổng: dừng trước 4b |
| [`dc_experiment.py`](../../research/dc_experiment.py) | Lưới k × chính sách khoảng trống cho DC | đặc tả DC §8 |
| [`ict_indicator_survey.py`](../../research/ict_indicator_survey.py) | Kết hợp indicator + ICT (21 tín hiệu, 16 kết hợp luật, mô hình học walk-forward) cho hướng, trạng thái «đi một chiều», dải giá 1h/4h; vùng thanh khoản có hút giá không. Hình: [`ve_ict_indicator.py`](../../research/ve_ict_indicator.py) | [`khao_sat_ict_indicator.md`](../research/khao_sat_ict_indicator.md) — hướng: không; dải giá: cấu trúc không giúp |
| [`chart_ket_hop.py`](../../research/chart_ket_hop.py) | Nguyên mẫu chart (thư viện + primitive của lab, Chrome headless): bốn cách kết hợp indicator + ICT trông thế nào trên chart, kèm điểm thật | [`khao_sat/chart_ket_hop/`](../research/khao_sat/chart_ket_hop/) — chưa phải plugin |
| [`khao_sat_ob_ote.py`](../../research/khao_sat_ob_ote.py) | Order block / OTE của `ict_structure` 0.5.0: luật K17–K27 (đúng hướng 1h/4h tại nến chạm OB / vào OTE), OB so với vùng giả cùng bề rộng, OTE so với các độ sâu hồi khác | [`khao_sat_ob_ote.md`](../research/khao_sat_ob_ote.md) — hướng: không; OB giữ giá chỉ nhờ vị trí; OTE không đặc biệt |
| [`vi_du_range_sideway.py`](../../research/vi_du_range_sideway.py) | Hình minh hoạ range biên rõ / sideway nhiễu / sideway nén trên dữ liệu thật | `plan_nhan_dien_trang_thai.md` §3 |

---

## 4. Lắp thuật toán mới từ phần có sẵn

| Cần | Dùng |
|---|---|
| Chỉ báo (SMA, ATR Wilder, ADX…) | [`core/indicators.py`](../../core/indicators.py) |
| Lịch phiên, phân loại khoảng trống | `core/data/session_calendar.py`, `core/components/session_gap.py` |
| Pivot, phân cấp swing, thứ tự đỉnh/đáy, dealing range | `swing_source.py`, `hierarchy.py`, `structure_order.py`, `dealing_range.py` |
| Displacement, FVG, vùng thanh khoản + sweep/run, shift, order flow | `displacement.py`, `fvg.py`, `liquidity.py`, `shift.py`, `order_flow.py` |
| Khung lớn từ chính luồng nến (chỉ nến đã chốt) | `core/data/htf_stream.py` (`ny_1700` hoặc `utc_epoch`), `htf_stack.py`, `period_levels.py` |
| Chạy trên prefix / replay | `core/engine.py`: `run_algorithm(bars, algo, upto_index=…)`, `ReplaySession` |

Mẫu ghép nhiều thành phần: [`core/algorithms/ict_structure/algorithm.py`](../../core/algorithms/ict_structure/algorithm.py).

---

## 5. Đo và đánh giá

**Hai loại so sánh, không trộn:**
1. *Cài đúng đặc tả chưa?* — test tính tay, test nhân quả (chạy tới t = chạy trọn rồi cắt; sửa nến sau t không đổi gì
   ≤ t), hồi quy run đã lưu. Không nói gì về thị trường.
2. *Nhận diện có tốt không?* — so với nhãn tay độc lập, hoặc với kết cục tương lai, **luôn kèm chuẩn ngẫu nhiên**.

**Trang Đánh giá** ([`danh_gia_thuat_toan.md`](danh_gia_thuat_toan.md)): protocol 1.0.0; mục tiêu chấm `swing_nho`,
`swing_cau_truc`, `ict_shift`; ghép một-một (matcher `min_cost_v1`, dung sai 1 nến); chuẩn ngẫu nhiên
`matched_hour_atrnorm_v2` (sự kiện ngẫu nhiên cùng giờ New York và cùng nhóm ATR chuẩn hoá theo giờ; v1 dùng ATR thô); đoạn phát triển / kiểm tra (đoạn kiểm
tra khoá). Chỉ chấm **sự kiện điểm** — chưa có nhãn theo đoạn cho regime, chưa có ma trận nhầm lẫn.

**Nhãn** ([`nhan_tham_chieu.md`](nhan_tham_chieu.md)): DB mới có 3 bộ thử (1–3 nhãn mỗi bộ) → chưa có F1. Việc D8 (nhãn
ITH/ITL + shift, 2 tuần phát triển + 2 tuần kiểm tra) đang treo — làm xong mới đo được thuật toán đúng bao nhiêu.

**Khi chưa có nhãn**, đo trong script:

| Đo | Cách | Mẫu |
|---|---|---|
| Độ bền | Số lần đổi/ngày, độ dài đoạn (trung vị, P90), % đoạn < 4 nến | `regime_survey.py` |
| Trễ | So với ranh giới **nhãn hậu kiểm** (nhìn tương lai, chỉ để chấm) — báo trên một họ tham số, không một tham số «đẹp» | `regime_survey.py` |
| Thông tin về tương lai | Kết cục (biên độ, ER, chạm +1 ATR trước −1 ATR) **trong từng tầng ATR** — vì biến động tự tương quan | `regime_survey.py` |
| Null | Dịch vòng chuỗi trạng thái (giữ độ bền, cắt liên hệ thời gian); mức ngẫu nhiên cùng giờ / cùng ATR | `orderflow_survey.py`, `regime_survey.py` |
| Khoảng tin cậy | Bootstrap theo khối tuần; cỡ mẫu hiệu dụng = số đoạn/sự kiện, không phải số nến | `orderflow_survey.py` |
| Lực thống kê | Hiệu ứng nhỏ nhất phát hiện được — bắt buộc khi kết quả âm tính | `regime_survey.py` |

---

## 6. Mở rộng sang quant

### 6.1. Luật không được phá

| Luật | Vì sao |
|---|---|
| Đặc trưng ở nến t chỉ dùng nến ≤ t; khung lớn chỉ dùng nến **đã chốt** | Dùng nến H4 đang hình thành làm thứ tự sai ~6% số nến — kết quả đẹp giả |
| Không chuẩn hoá / chọn ngưỡng bằng thống kê của **cả** dataset làm đầu vào | Rò rỉ tương lai (lỗi chính của repo regime cũ) |
| Đoạn phát triển: trước 01/09/2024. Từ 01/09/2024 trở đi (cả 2025) là đoạn kiểm tra — **khoá**, mở một lần cho cấu hình đã chốt | Chọn tham số trên đoạn kiểm tra thì không còn phép kiểm độc lập |
| Không dùng dataset «LỆCH GIỜ» hay «MÔ PHỎNG» để phân tích | Bản lệch giờ sai mốc phiên; mô phỏng chỉ để thử công cụ |
| Luôn có baseline đơn giản + chuẩn ngẫu nhiên; báo lực thống kê khi âm tính | «58% đúng» không nói gì nếu ngẫu nhiên cũng 56% |
| Không P&L / win rate trong lab | Giá trị giao dịch đo ở repo giao dịch, có chi phí |
| Đổi output của thuật toán có sẵn → tăng phiên bản + hồi quy | Không âm thầm đổi kết quả cũ |
| Thí nghiệm = script tái lập + JSON có checksum + báo cáo `docs/research/` | Ai cũng chạy lại được |

### 6.2. Cách nhanh nhất: một script đọc dữ liệu

[`research/hoc_quant/hoc.py`](../../research/hoc_quant/hoc.py) mở DB ở chế độ chỉ đọc và **từ chối** mọi khoảng chạm
đoạn kiểm tra. Ví dụ đầy đủ — câu hỏi: «khi order flow của `ict_structure` đang tăng, giá 16 nến sau có cao hơn khi nó
đang giảm không?»

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
import numpy as np

TU, DEN = "2024-01-01", "2024-09-01"                    # chỉ đoạn phát triển
r = chay_thuat_toan("ict_structure", XAU_M15, TU, DEN)
tl = r["timeline"]
close = np.array([b.close for b in r["nen"]])
atr = tl["atr"].to_numpy(dtype=float)
state = tl["order_flow"].to_numpy(dtype=float)          # trạng thái SAU nến t → biết lúc close[t]

# kết cục (chỉ để chấm, nhìn tương lai): lợi suất 16 nến tới, đo bằng ATR của nến t
h = 16
fwd = np.full(len(close), np.nan)
fwd[:-h] = (close[h:] - close[:-h]) / atr[:-h]

def chenh(s):
    ok = ~np.isnan(fwd) & ~np.isnan(s)
    return np.nanmean(fwd[ok & (s == 1)]) - np.nanmean(fwd[ok & (s == -1)])

thuc = chenh(state)
# null «dịch vòng»: giữ nguyên độ bền của chuỗi trạng thái, cắt mọi liên hệ thời gian với kết cục
rng = np.random.default_rng(1)
null = np.array([chenh(np.roll(state, k)) for k in rng.integers(500, len(state) - 500, 400)])
print("chênh lệch lợi suất 16 nến tới (ATR), order flow tăng − giảm: %.3f" % thuc)
print("null dịch vòng: P5 %.3f · P50 %.3f · P95 %.3f · p = %.2f" % (
    *np.percentile(null, [5, 50, 95]), (1 + (np.abs(null) >= abs(thuc)).sum()) / (len(null) + 1)))
```

Kết quả khi mình chạy (19/10/2026, `ict_structure` 0.4.2):

```text
chênh lệch lợi suất 16 nến tới (ATR), order flow tăng − giảm: -0.140
null dịch vòng: P5 -0.412 · P50 0.021 · P95 0.450 · p = 0.56
```

Đọc: chênh lệch nằm giữa vùng của null → **không có bằng chứng** order flow cho biết hướng 4 giờ tới, khớp nghiên cứu
order flow. Ba điểm cần giữ ở mọi thí nghiệm: đặc trưng chỉ dùng thông tin đã biết; kết cục tương lai chỉ để chấm; null
giữ cấu trúc tự tương quan của dữ liệu (dịch vòng), không xáo trộn từng nến.

Chạy: lưu đoạn trên thành file ngoài repo (vd `D:\nhap\vi_du.py`), rồi từ thư mục `market-structure-lab`:
`.\.venv\Scripts\python.exe D:\nhap\vi_du.py`.

Khi thí nghiệm đáng giữ, đưa thành `research/<ten>.py` theo mẫu [`orderflow_survey.py`](../../research/orderflow_survey.py):
tham số `--json` (kết quả kèm sha256 script, checksum dataset, phiên bản thuật toán), `--allow-test` mặc định tắt, seed
cố định, thời gian chạy; báo cáo tiếng Việt ở `docs/research/`.

### 6.3. Khi nào đưa thành thuật toán của lab

Khi cần chart, replay từng nến, lưu run, chấm ở trang Đánh giá, hoặc so trên giao diện với thuật toán khác. Các bước
(chi tiết: [`them_thuat_toan.md`](them_thuat_toan.md)):

1. Viết **đặc tả trước** `docs/algorithms/thuat_toan_<ten>.md` theo khung `AGENTS.md` §3.1 (đầu vào/ra, tham số, thứ
   tự trong nến, lúc biết, chỗ mơ hồ đã chọn).
2. Gói `core/algorithms/<ten>/`: lớp con `StructureAlgorithm` với `param_specs`, `on_bar`, `timeline_point`,
   `pending_state`; ghép thành phần ở §4 thay vì viết lại.
3. Đăng ký trong `core/registry.py` — form trên trang tự sinh từ `ParamSpec`.
4. Test: tính tay trên chuỗi nhỏ, nhân quả (prefix = trọn rồi cắt; sửa đuôi không đổi quá khứ), replay.
5. Tuỳ chọn: plugin vẽ `frontend/js/algos/<ten>.js`, mục tiêu chấm riêng (`eval_targets.py`), loại nhãn riêng.

Chưa có căn cứ chọn giữa hai cách định nghĩa → cài **hai biến thể có tên**, chấm trên cùng thước (`AGENTS.md` §3.2).

### 6.4. Thêm vào thuật toán có sẵn

Thêm thành phần vào `ict_structure` (vd một loại vùng thanh khoản mới) làm đổi output → tăng phiên bản, bảng khác biệt
trước/sau trên các dataset phát triển, hồi quy run đã lưu. Mẫu: bản ghi 0.4.2 ở đặc tả §1.

### 6.5. Dữ liệu dùng được

Nguồn HistData, giờ đã sửa về UTC, nến đã đóng, không có volume. Mã hằng có sẵn trong `hoc.py`:

| Hằng trong `hoc.py` | Dataset | Khung · khoảng |
|---|---|---|
| `XAU_M15` | `ds_db1583cd4dde` | XAUUSD M15 · 2024 — dataset chính của lab |
| `XAU_M15_DAI`, `EUR_M15_DAI` | `ds_a5212fd37814`, `ds_a9a2a5e4cef5` | M15 · 2018–2025 |
| `XAU_M5`, `XAU_M5_2018`, `XAU_M5_2022` | `ds_933fa5ec67e2`, … | M5 · 2024, 2018–2021, 2022–2025 |
| `XAU_H1`, `EUR_H1` | `ds_83abaa3c6eab`, `ds_ab9f7729cb17` | H1 · 2018–2025 |
| `XAU_H4`, `XAU_D1`, `EUR_H4`, `EUR_D1` | … | H4 / D1 · 2018–2025, mốc 17:00 New York |
| `XAU_M1`, `XAU_M1_NAM[năm]`, `EUR_M1_NAM[năm]` | … | M1 theo từng năm — nặng, chỉ dùng khi cần biến động trong nến |

Tránh: 4 dataset tên bắt đầu bằng «[LỆCH GIỜ» và 5 dataset «MÔ PHỎNG». Danh sách đầy đủ: `danh_sach_dataset()` hoặc
[`du_lieu_thi_truong.md`](du_lieu_thi_truong.md).

Một điều đã gặp: XAUUSD và EURUSD M15 tháng 2–7/2023 thiếu khoảng 1 giờ ở lúc mở phiên Chủ nhật và đóng phiên thứ Sáu
— `ict_structure` đánh dấu đúng các nến H4 đó là thiếu dữ liệu. Nên kiểm ở `market-data-pipeline`.

### 6.6. Nên thử gì tiếp theo

Hai phát hiện định hướng cho mọi thí nghiệm sau:
- **Biến động đoán được, hướng thì gần như không** ở khung trong ngày (tài liệu + mọi phép đo của lab).
- **Nhiều «quy luật» cấu trúc cũng xuất hiện trên bước ngẫu nhiên** → thống kê swing / sweep / shift phải đặt cạnh cùng
  thống kê trên dữ liệu mô phỏng (`chay_tren_df` + `nen_tu_gia` trong `hoc.py`).

Lộ trình đề xuất ([`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md) §4, khảo sát 4a):

1. **Làm sạch thước đo:** khử dao động theo giờ phiên (M15 dao động mạnh theo giờ); đo biến động từ nến M1; kiểm định
   nhảy giá; cờ giờ thanh khoản mỏng.
2. **Vòng so tài trên đoạn phát triển** — mỗi đối thủ một script, chấm cùng thước (mô phỏng, null dịch vòng, baseline
   «không làm gì», bootstrap theo ngày): tỷ lệ biến động ngắn/dài, Page–Hinkley / CUSUM (điểm đổi), độ dốc lọc Kalman,
   variance ratio, time-series momentum, jump model online.
3. **Regime hai trục:** trục **biến động** (nén / bình thường / bung / nhảy — có bằng chứng vững, Breakout nằm ở đây) và
   trục **hướng** (Trend ↑ / ↓ / Range — chỉ giữ ở M15 nếu thắng ngẫu nhiên, không thì lên H1).

Câu hỏi đang chờ bạn chốt sau 4a (Q-A…Q-D, báo cáo §8): regime phục vụ nhịp nào; luật giữ Range; điều kiện Trend; có
làm `ict_regime` như lớp mô tả không.

### 6.7. Học nền theo nhu cầu

| Định làm | Đọc module ([`docs/hoc_quant/`](../hoc_quant/README.md)) |
|---|---|
| Hiểu dữ liệu, giờ phiên, gộp khung | 1 — Dữ liệu giá |
| Đọc p-value, khoảng tin cậy, bootstrap, lực thống kê | 2 — Thống kê nền |
| Dựng null, chạy thuật toán trên bước ngẫu nhiên | 3 — Bước ngẫu nhiên và null |
| Biến động, tự tương quan, chuẩn hoá theo giờ phiên | 4 — Chuỗi thời gian và biến động |
| Viết luật cấu trúc đo được, không nhìn tương lai | 5 — Cấu trúc định lượng |
| Regime, HMM, độ trễ ↔ nhấp nháy | 6 — Regime |
| Chia phát triển / kiểm tra, overfit khi thử nhiều cấu hình | 7 — Đánh giá và overfit |
| Từ nhận diện tới chiến lược, chi phí | 8 — Chiến lược và chi phí |

### 6.8. Trước khi viết kết luận

- [ ] Đặc trưng chỉ dùng thông tin ≤ t; đã thử chạy trên prefix và sửa nến sau điểm cắt → kết quả không đổi.
- [ ] Chỉ dùng đoạn phát triển; ghi số cấu hình đã thử.
- [ ] Có baseline đơn giản (ER, ADX, «không làm gì») và null; kiểm trong từng tầng ATR.
- [ ] Cỡ mẫu hiệu dụng = số đoạn / sự kiện; có khoảng tin cậy; có hiệu ứng nhỏ nhất phát hiện được.
- [ ] Kết quả tách theo năm, theo mã (XAU / EUR) — cùng dấu không?
- [ ] Script + JSON tái lập; báo cáo nói rõ chỗ chọn tham số sau khi xem số.

---

## 7. Tra cứu nhanh

| Việc | Lệnh (PowerShell, trong `market-structure-lab`) |
|---|---|
| Chạy lab | `.\run.ps1` → http://127.0.0.1:8099 |
| Chạy test | `.\run.ps1 -Test` |
| Hồi quy run đã lưu | `.\.venv\Scripts\python.exe scripts\regression_saved_runs.py --snapshot truoc.json` rồi `--compare truoc.json` |
| Khảo sát 4a | `.\.venv\Scripts\python.exe research\regime_survey.py --quick` (đoạn phát triển, ~25 s) |
| Khảo sát order flow | `.\.venv\Scripts\python.exe research\orderflow_survey.py --json nhap.json` |
| Khảo sát indicator + ICT | `.\.venv\Scripts\python.exe research\ict_indicator_survey.py --nhanh --json nhap.json` (~1 phút; bỏ `--nhanh` để chạy đủ, ~6 phút) |
| Khảo sát OB / OTE | `.\.venv\Scripts\python.exe research\khao_sat_ob_ote.py --json nhap.json` (~1,5 phút; `--nhanh` để thử) |
| Python tương tác với dữ liệu | `.\.venv\Scripts\python.exe` rồi `import sys; sys.path.insert(0, "research/hoc_quant"); from hoc import *` |

| Tìm | Ở đâu |
|---|---|
| Đặc tả thuật toán | `docs/algorithms/thuat_toan_<ten>.md` |
| Plan đang làm | [`plan_bias_regime.md`](../plans/plan_bias_regime.md) (giai đoạn 4), [`plan_ict_structure.md`](../plans/plan_ict_structure.md) |
| Nghiên cứu + số liệu | `docs/research/` (JSON ở `docs/research/khao_sat/`) |
| Kiến trúc tầng ICT | [`kien_truc_luong_ict.md`](kien_truc_luong_ict.md) |
| Luật của lab | [`AGENTS.md`](../../AGENTS.md) |
