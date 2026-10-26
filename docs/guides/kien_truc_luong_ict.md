# Kiến trúc và các luồng nối: từ nến đến cấu trúc ICT

Ngày: 01/10/2026. Tài liệu này **nối** các phần đang nằm rời nhau:

* [`nghien_cuu_ict_smc_thuat_toan.md`](../research/nghien_cuu_ict_smc_thuat_toan.md) — so sánh định nghĩa
  từng khái niệm (xếp theo khái niệm, nên không thấy khái niệm nào cần khái niệm nào);
* các thuật toán đang có trong lab — mỗi cái là một khối độc lập;
* thứ tự đọc tài liệu — trước đây chỉ là danh sách.

Đọc theo ba trục, mỗi trục trả lời một câu hỏi:

| Trục | Câu hỏi | Mục |
|---|---|---|
| A. Chuỗi khái niệm | Khái niệm ICT nào được xây trên khái niệm nào? | §2 |
| B. Đường đi dữ liệu | Một nến đi qua những tầng nào của lab để thành sự kiện trên chart? | §3 |
| C. Vòng nghiên cứu | Một khái niệm đi từ «đọc nguồn» tới «có số liệu kiểm chứng» qua những bước nào? | §5 |

Phần §4 ghép trục A vào trục B: lab đang có gì, thiếu gì, và nên nối bằng cách nào.

---

## 1. Vì sao hiện tại thấy rời rạc

1. **Nghiên cứu xếp theo khái niệm.** Mục 3 của tài liệu nghiên cứu là 3.1 Swing, 3.2 BOS/MSS,
   3.3 FVG… — mỗi mục đứng riêng. Thực tế MSS cần swing + displacement + FVG; order block cần
   BOS/MSS; sweep cần vùng thanh khoản, mà vùng thanh khoản lại lấy từ swing.
2. **Code xếp theo thuật toán nguyên khối.** Kiểm tra import trong `core/algorithms/`:

   | Thuật toán | Dùng chung từ lab | Tự cài lại |
   |---|---|---|
   | `swing_pivot` | `base`, `types` | pivot, nhãn HH/HL, BOS/CHoCH |
   | `swing_hierarchy` | `base`, `types` | pivot cấp 1 (lặp lại logic của `swing_pivot`), cấp 2 |
   | `dc_atr_structure` | `base`, `types`, `indicators`, `dc_regime` | detector DC, nhãn HH/HL |
   | `indicator_baseline`, `hmm_online` | `base`, `types`, `indicators` | phân loại riêng |

   Không thuật toán nào **tiêu thụ sự kiện** của thuật toán khác. Muốn có «MSS sau sweep» thì
   hiện chỉ có cách viết một khối mới tự làm lại từ swing trở lên.

→ Cần một **lớp nối**: các khái niệm nền được cài một lần thành thành phần dùng chung, các khái
niệm tầng trên đọc sự kiện của tầng dưới, và mỗi sự kiện ghi lại nó được suy ra từ sự kiện nào.

---

## 2. Trục A — Chuỗi phụ thuộc khái niệm ICT

### 2.1. Sơ đồ tầng

Mũi tên `→` nghĩa là «là đầu vào của». Tầng trên chỉ được xét **sau khi** tầng dưới đã xác
nhận ở cùng nến hoặc nến trước (giữ nhân quả).

```text
TẦNG 0  Nến đã đóng ─────────────────────────────────────────────────────────────────────
        OHLC · timeframe · gap · giờ New York (đổi giờ mùa hè) · nến khung lớn (H4/D1)
          │
TẦNG 1  NGUYÊN TỐ — chỉ cần nến ─────────────────────────────────────────────────────────
          ├─ P1 Swing ngắn hạn (STH/STL)     ← nguồn có thể thay: pivot 1/1 · DC · «leg»
          ├─ P2 FVG (khoảng hở 3 nến)
          ├─ P3 Displacement (nến bứt mạnh)  ← cần ngưỡng: ATR
          ├─ P4 ATR / thước đo biến động
          ├─ P5 Phiên & killzone (giờ NY)
          └─ P6 Nến khung lớn (HTF)
          │
TẦNG 2  CẤU TRÚC — cần tầng 1 ───────────────────────────────────────────────────────────
          ├─ S1 Phân cấp swing STH → ITH → LTH            (P1)
          ├─ S2 Xu hướng / bias theo HH-HL, LH-LL          (S1)
          ├─ S3 Vùng thanh khoản: đỉnh/đáy chưa bị lấy,    (S1, P4 cho dung sai)
          │     EQH/EQL, đỉnh/đáy phiên trước
          └─ S4 Dealing range → premium / discount / EQ     (S1)
          │
TẦNG 3  SỰ KIỆN TỔ HỢP — cần tầng 2 ─────────────────────────────────────────────────────
          ├─ E1 BOS / CHoCH: close phá mức swing           (S1, S2)
          │     MSS = CHoCH + displacement (+ FVG?)         (E1, P3, P2)
          ├─ E2 Sweep: wick vượt vùng thanh khoản,          (S3)
          │     close quay lại (trong ≤ Z nến)
          ├─ E3 Order block: nến trước displacement         (E1, P3)
          │     dẫn tới BOS/MSS — trong lab neo vào SHIFT   (SHIFT, P3) — §4.4, đã cài 0.5.0
          ├─ E4 Breaker: OB bị phá sau khi có sweep         (E3, E2)
          ├─ E5 CISD                                        (nến, mức mở cửa chuỗi nến)
          └─ E6 OTE: vùng hồi 62–79% của nhịp sau SHIFT     (SHIFT; đáy nhịp = cực trị cú quét E2) — §4.4, đã cài 0.5.0
          │
TẦNG 4  NGỮ CẢNH / BỘ LỌC ───────────────────────────────────────────────────────────────
          ├─ C1 PD array: OB/FVG/breaker nằm ở premium hay discount   (S4 + E3/P2/E4)
          ├─ C2 Trong killzone hay không                              (P5)
          └─ C3 Bias khung lớn                                        (S2 chạy trên P6)
          │
TẦNG 5  MÔ HÌNH / SETUP (ghép nhiều sự kiện theo thứ tự thời gian) ─────────────────────
          ├─ «ICT 2022 model»: sweep (E2) → MSS có displacement (E1) → FVG (P2) trong killzone (C2)
          ├─ Silver Bullet: FVG (P2) trong khung giờ cố định (P5)
          └─ C2 + CISD (lab từng có bản H4–M15, đã gỡ 21/10/2026)
```

### 2.2. Ba điều rút ra từ sơ đồ

1. **Swing (P1) là gốc của gần như mọi thứ.** Đổi cách tìm swing (pivot 1/1, 3/3, DC, «leg»)
   là đổi S1–S4, E1–E4 và mọi tầng trên. Vì vậy nguồn swing phải **thay được** và có phiên bản;
   so sánh nguồn swing là thí nghiệm quan trọng nhất (nghiên cứu §3.1, §6.2).
2. **FVG (P2) và displacement (P3) không cần swing** — làm được độc lập, sớm, và là đầu vào
   cho MSS/OB về sau.
3. **Chỗ mơ hồ dồn ở tầng 3** (MSS, sweep, OB — nghiên cứu §7 #1, #3, #5). Tầng 1–2 gần như
   đã đồng thuận. Nên xây chắc tầng 1–2 trước rồi mới thử các phương án tầng 3.

> **Cập nhật 02/10/2026 — cách đánh của người dùng:** `ict_structure` **không dùng E1**
> (BOS/CHoCH/MSS). Đổi hướng = E2 sweep rồi P3 displacement ngược chiều («shift»). Bias = ba thành
> phần riêng: S2 (thứ tự HH-HL), phản ứng ở FVG khung lớn, DOL. Sơ đồ trên vẫn đúng như bản đồ
> khái niệm ICT chung; đặc tả áp dụng nằm ở [`plan_ict_structure.md`](../plans/plan_ict_structure.md) §0, §4.
>
> **Cập nhật 26/10/2026 (0.10.0):** người dùng đổi — vẫn không BOS/CHoCH, nhưng đổi hướng = **MSS** kiểu ICT 2022 (sweep → close
> phá STL / STH trước cú chạy bằng đoạn displacement); OB / OTE neo vào MSS, OB là PD array (breaker, `pd_bias`). Shift còn là
> tham số đối chiếu — [`plan_mss_ob_pd.md`](../plans/plan_mss_ob_pd.md).

### 2.3. Bảng tra: mỗi nút cần gì, cho ra gì, mơ hồ ở đâu

| Nút | Đầu vào | Đầu ra (sự kiện, biết lúc nào) | Mức đồng thuận | Nghiên cứu |
|---|---|---|---|---|
| P1 Swing | nến | đỉnh/đáy, biết khi nến phải cuối đóng (pivot) hoặc khi đảo chiều ≥ Δ (DC) | 2 trường phái | §3.1, §7 #4 |
| P2 FVG | 3 nến | vùng [đáy, đỉnh], biết khi **nến 3** đóng | cao | §3.3 |
| P3 Displacement | nến + ATR | cờ trên nến, biết khi nến đóng (hoặc nến sau nếu cần tiếp diễn) | không có số gốc | §3.6, §7 #2 |
| S1 Phân cấp | chuỗi P1 | ITH/ITL, biết khi đỉnh cấp 1 bên phải xác nhận | cao (Larry Williams) | §3.1 |
| S2 Bias | chuỗi S1 | tăng/giảm/chưa rõ, đổi khi có pivot mới | cao | §3.2 |
| S3 Vùng thanh khoản | S1 + ATR | mức/vùng đang chờ bị lấy | ngưỡng EQ chưa thống nhất | §3.5, §7 #6 |
| S4 Dealing range | S1 | biên trên/dưới + mốc 50% | chọn range nào chưa thống nhất | §3.7, §7 #8 |
| E1 BOS/MSS | S1, S2 (+P3, P2) | sự kiện tại nến close phá mức | BOS cao; MSS chưa có nguồn gốc | §3.2, §7 #5 |
| E2 Sweep | S3 | sự kiện tại nến close quay lại | có cần quay lại / bao nhiêu nến | §3.5, §7 #3 |
| E3 Order block | E1, P3 (lab: SHIFT) | vùng, biết lúc BOS/MSS (lab: SHIFT) xác nhận | 2–3 trường phái | §3.4, §7 #1 |
| E6 OTE | SHIFT, cực trị cú quét | vùng hồi 62–79%, cập nhật tới khi giá vào; sự kiện ở nến vào vùng | tỷ lệ thống nhất; chọn nhịp nào thì chưa | plan kết hợp §3.4 |
| C2 Killzone | P5 | cờ thời gian | mâu thuẫn London 01–05 vs 02–05 | §3.7, §7 #7 |

---

## 3. Trục B — Đường đi dữ liệu trong lab

### 3.1. Sơ đồ

```text
 ┌──────────────── core/data ─────────────────┐
 │ nạp CSV/MT5 → kiểm tra → chuẩn hoá UTC     │  validate.py, loader.py, mt5_source.py
 │ tổng hợp khung (resample) · kỳ H4 (htf)    │  resample.py, htf_stream.py
 └───────────────────────┬────────────────────┘
                         │ Bar (đã đóng, theo thứ tự)
 ┌───────────────────────▼────────────────────┐
 │ core/engine.py                              │  run_algorithm (toàn bộ) · ReplaySession
 │ nạp TỪNG nến → algorithm.on_bar(bar)        │  (từng nến, lùi = dựng lại từ đầu,
 │ → timeline_point · pending_state            │   gửi phần chênh lệch `since`)
 └───────────────────────┬────────────────────┘
                         │
 ┌───────────────────────▼────────────────────┐
 │ core/algorithms — MỘT StructureAlgorithm    │  ← TRỤC A nằm trọn trong hộp này
 │ (hiện tại: mỗi thuật toán tự làm mọi tầng)  │
 └───────────────────────┬────────────────────┘
                         │ StructureEvent: event_time · confirmed_at · reason_code · details
 ┌───────────────────────▼────────────────────┐
 │ backend: routers/ → services/ → storage/    │  lưu run, sự kiện, manifest, export CSV
 └──────┬──────────────────────────┬──────────┘
        │                          │
 ┌──────▼──────────────┐   ┌───────▼──────────────────────────────┐
 │ core/eval            │   │ frontend                              │
 │ protocol · matcher   │◄──│ Thử nghiệm: chart, replay, giải thích │
 │ metric · causality   │   │ Gán nhãn: nhãn người gán ─────────────┼──► core/labels
 │ dc_metrics …         │──►│ Đánh giá: F1, độ trễ, so sánh run     │
 └──────────────────────┘   └───────────────────────────────────────┘
```

### 3.2. Hợp đồng nối các tầng (đã có, phải giữ)

| Chỗ nối | Hợp đồng | Vì sao |
|---|---|---|
| data → engine | Nến đã đóng, thời gian tăng nghiêm ngặt, gap được báo | Mọi tầng trên tin vào thứ tự nến |
| engine → algorithm | Chỉ gọi `on_bar` từng nến; `reset()` xoá sạch | Không có đường nhìn tương lai |
| algorithm → event | `confirmed_at` = close nến đang xử lý; sự kiện đã trả về không bị sửa | Replay, đánh giá độ trễ, chống nhìn tương lai |
| event → eval | Ánh xạ loại sự kiện → loại nhãn phải khai báo (`event_type_map`) | Không chấm nhầm khái niệm (vd DC vs swing wick) |
| event → frontend | Vẽ theo `confirmed_at` trong replay; `details` mang công thức để giải thích | Chart không «biết trước» |

---

## 4. Ghép A vào B — lab có gì, thiếu gì, nối thế nào

### 4.1. Hiện trạng theo từng nút

| Nút | Trạng thái | Nằm ở đâu |
|---|---|---|
| Tầng 0 | **Có** (lịch phiên khai báo + phân loại khoảng trống; nến khung lớn gộp tuần tự `utc_epoch` và `ny_1700` theo lịch) | `core/data`, `htf_stream` (`HtfAggregator` mốc UTC, bộ gộp chung chưa thuật toán nào dùng; `SessionHtfAggregator` `ny_1700` cho `ict_structure`), `core/components/session_gap.py` |
| P1 Swing — pivot | **Có**; thành phần dùng chung (chặn cửa sổ vắt qua khoảng trống) | `swing_pivot`, `swing_hierarchy`; `core/components/swing_source.py` (`ict_structure`) |
| P1 Swing — DC | **Có**, nằm trong khối | `dc_atr_structure` (`DcDetector` tách được) |
| P1 Swing — «leg» | Chưa | — |
| P2 FVG | **Có** (M15, vòng đời chạm/lấp) | `core/components/fvg.py` (`ict_structure`) |
| P3 Displacement | **Có** | `core/components/displacement.py` (`ict_structure`) |
| P4 ATR | **Có** (2 biến thể seed) | `core/indicators.py` |
| P5 Killzone | **Có** (cờ, giờ New York) | `core/components/killzone.py` (`ict_structure`) |
| S1 Phân cấp | **Có** (cấp 2, cấp 3) | `swing_hierarchy`; `core/components/hierarchy.py` |
| S2 Bias | **Có**, 3 cách | `swing_pivot` (bias), `dc_regime`; thứ tự đỉnh/đáy + mức được bảo vệ `core/components/structure_order.py` |
| S3 Vùng thanh khoản | **Có** cho tầng khung chạy (ITH/ITL, gộp EQ), H1/H4 (ITH/ITL khung lớn), D/W (PDH/PDL, PWH/PWL) — v0.4.0 | `core/components/liquidity.py` (`ict_structure`); `swing_pivot` timeline `muc_high/muc_low` |
| S4 Dealing range | **Có** | `core/components/dealing_range.py` (`ict_structure`) |
| E1 BOS/CHoCH | **Có** | `swing_pivot` |
| E1 MSS (có displacement) | Chưa | — |
| E2 Sweep | **Có** (vòng đời chạm → lấy → sweep / run / chưa rõ, vùng M15) | `core/components/liquidity.py` (`ict_structure`) |
| Shift (thay MSS — B1) | **Có** (sweep → displacement ngược chiều + `SHIFT_FVG`) | `core/components/shift.py` (`ict_structure`) |
| Order flow theo thanh khoản (đọc run + shift) | **Có** (tăng / giảm / chưa rõ sau mỗi nến; mô tả, không phải dự báo — OF1–OF2) | `core/components/order_flow.py` (`ict_structure` v0.3.0) |
| P6 + C3 Khung lớn (H1/H4 đã chốt: ITH/ITL, thứ tự, dealing range, FVG; PDH/PDL, PWH/PWL) | **Có** (v0.4.0; đặc trưng, không lọc) | `core/components/htf_stack.py`, `period_levels.py` (`ict_structure`) |
| C1 Phản ứng ở PD array khung lớn (FVG H1/H4) → `pd_bias`; DOL | **Có** (v0.4.0; ba thành phần bias không ghép — B3) | `core/components/pd_array.py`, `dol.py` (`ict_structure`) |
| E3 OB | **Có** (0.5.0, 21/10/2026; neo SHIFT; biến thể OB-T, OB-R, OB-D) — `core/components/order_block.py` | [`plan_ket_hop_ict_indicator.md`](../plans/plan_ket_hop_ict_indicator.md) §3.4; luồng §4.4 |
| E4 Breaker | Chưa (sau OB) | — |
| E6 OTE | **Có** (0.5.0, 21/10/2026) — `core/components/ote.py` | [`plan_ket_hop_ict_indicator.md`](../plans/plan_ket_hop_ict_indicator.md) §3.4; luồng §4.4 |
| E5 CISD | Chưa (`c2_cisd_research` đã gỡ 21/10/2026) | — |
| Tầng 4–5 | Chưa | — |

### 4.2. Đề xuất cách nối (thiết kế, **chưa cài**)

**Ý chính:** tách các nút tầng 1–3 thành **thành phần trạng thái dùng chung** (component), mỗi cái
nhận nến (và sự kiện tầng dưới), trả sự kiện của mình. Một thuật toán tổ hợp gọi chúng theo thứ
tự cố định trong mỗi nến. Engine, lưu trữ, đánh giá, giao diện **không phải đổi** vì thuật toán
tổ hợp vẫn là một `StructureAlgorithm`.

```text
core/components/                 (đề xuất)
  swing_source.py   P1  ── PivotSource(left,right) · DcSource(k, mode) · LegSource(len)
  fvg.py            P2
  displacement.py   P3
  hierarchy.py      S1  ── đọc sự kiện của bất kỳ SwingSource nào
  bias.py           S2
  liquidity.py      S3  ── vùng chưa bị lấy, EQH/EQL
  structure.py      E1  ── BOS/CHoCH, cờ displacement → MSS
  sweep.py          E2
  order_block.py    E3/E4 ── hai biến thể, có tên riêng
  session.py        P5/C2 ── giờ New York

Mỗi component:  reset() · update(bar, ctx) -> list[sự kiện] · snapshot()
```

**Thứ tự trong mỗi nến** (cùng nguyên tắc với `dc_atr_structure` §6 hiện tại):

```text
1. kiểm tra nến / gap         → reset các component theo chính sách gap
2. ATR, phiên (P4, P5)
3. swing source (P1)          → nếu có pivot mới: hierarchy (S1) → bias (S2) → liquidity (S3)
4. FVG (P2), displacement (P3) cho nến này
5. sweep (E2)                 ← dùng S3 của nến TRƯỚC (vùng đã biết từ trước)
6. structure (E1)             ← close nến này vs mức swing đã xác nhận; cờ P3/P2 → MSS
7. order block / breaker (E3/E4) ← chỉ khi E1 vừa xảy ra
8. gắn ngữ cảnh (C1–C3) vào details của sự kiện ở bước 5–7
```

**Truy vết chuỗi:** mỗi sự kiện tầng trên ghi `details.basis = [event_id tầng dưới, …]`
(hiện đã có `reference_event_id` cho một tham chiếu). Khung «Thuật toán đang làm gì» trong
replay khi đó vẽ được cả chuỗi: *sweep #A → displacement → FVG #B → MSS #C → OB #D*.

**Ràng buộc khi tách:**

* Thuật toán cũ giữ nguyên output: chạy lại các run đã lưu phải khớp event_id (như đã làm khi
  nâng `dc_atr_structure` lên 0.2.0). Nếu đổi thì tăng phiên bản.
* Nguồn swing là tham số của thuật toán tổ hợp → cùng một chuỗi tầng 2–3 chạy được trên pivot,
  DC, «leg» để so sánh (điều nghiên cứu §6.2 yêu cầu).
* Không dùng sự kiện tầng dưới «của tương lai»: bước 5 dùng vùng thanh khoản đã biết trước nến
  này; OB chỉ được tạo khi E1 đã xác nhận.

### 4.3. Ví dụ một chuỗi trên M15 (minh hoạ cách các nút nối nhau)

```text
nến 100  P1  xác nhận đáy ngắn hạn STL = 2650.0 (pivot 1/1, biết lúc nến 101 đóng)
nến 140  S3  STL 2650.0 vẫn chưa bị lấy → là vùng sell-side liquidity
nến 152  E2  low 2648.6 < 2650.0, close 2651.2 > 2650.0 → SWEEP (basis: STL@100)
nến 153  P3  thân = 0.82 × biên độ, biên độ = 1.9 × ATR → DISPLACEMENT tăng
nến 154  P2  low[154] 2655.1 > high[152] 2652.4 → FVG tăng [2652.4, 2655.1], biết lúc 154 đóng
nến 154  E1  close 2656.0 > STH gần nhất 2655.5, bias trước = giảm → CHoCH;
             có P3 (153) + P2 (154) → MSS (basis: STH@…, DISP@153, FVG@154, SWEEP@152)
nến 154  E3  OB tăng = nến giảm cuối trước displacement (biến thể ICT) (basis: MSS@154)
         C2  nến 154 nằm trong NY killzone? → ghi vào details
```

Mỗi dòng là một sự kiện riêng với `confirmed_at` riêng; chart và đánh giá dùng được từng mắt
xích hoặc cả chuỗi.

### 4.4. Luồng Order Block và OTE (duyệt và cài 21/10/2026 — `ict_structure` 0.5.0)

> Khi cài có ba chỗ khác bản đề xuất (đặc tả §12, E-1…E-3): **(1)** OB chỉ có hiệu lực khi giá **vượt đầu xa** của
> khối (nghiên cứu ICT §3.4) — trước đó là ứng viên, `ORDER_BLOCK_*` phát ở nến vượt; **(2)** hết hạn **có** phát
> `OB_EXPIRED` / `OTE_EXPIRED` (để chart dừng hộp đúng chỗ mà không tính lại quy tắc); **(3)** SHIFT cùng chiều cũng
> thay nhịp OTE đang chờ. Sơ đồ dưới đã sửa theo bản cài. Sau code-review thêm E-7…E-9: hai SHIFT cùng chiều tìm ra
> đúng một chuỗi nến → **một** OB (không phát trùng); nến d close qua mép xa → bỏ ứng viên; ứng viên đã bỏ không còn
> gắn vào nhịp OTE.

Định nghĩa, tham số và các luật kết hợp K17–K27: [`plan_ket_hop_ict_indicator.md`](../plans/plan_ket_hop_ict_indicator.md)
§3.4. Mục này chỉ nói **nối vào đâu** và **chạy theo thứ tự nào**.

**(a) Vị trí trong từng nến của `ict_structure`.** Giữ nguyên 12 bước hiện có ([`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md));
chèn ba bước, đánh dấu `+`:

```text
 1. kiểm nến; khoảng trống trước t → ICT_GAP
 2. ATR[t−1] cho mọi ngưỡng của nến t
 3. [E2] vùng thanh khoản đã biết trước t → chạm / lấy / sweep / run
+3b. [OB/OTE] vùng đã biết TRƯỚC t (tạo ở nến ≤ t−1):
       OB đã xác nhận, chưa chạm:
                      low[t] ≤ mép trên              → OB_TAP_UP, hoặc OB_FAIL_UP nếu close[t] < mép dưới
                      quá 96 nến từ d               → OB_EXPIRED
       ứng viên OB:   close[t] < mép dưới / quá hạn → bỏ (chỉ đếm)
                      high[t] > mép trên             → xác nhận → ORDER_BLOCK_UP (chạm xét từ t+1)
       OTE đang chờ:  low[t] < X                     → OTE_FAIL_UP
                      low[t] ≤ H − 0,62·(H − X)      → OTE_ENTRY_UP (H, X của nến trước; ghi độ sâu hồi)
 4. [P3] displacement của t
 5. [P2] FVG
 6. [E3] ứng viên shift → SHIFT (+ SHIFT_FVG)
 6b. [OF] order flow
+6c. [OB/OTE] SHIFT vừa xác nhận ở t (= d):
       SHIFT ngược chiều → OB đã xác nhận chưa chạm của chiều cũ → OB_EXPIRED; ứng viên chiều cũ bị bỏ
       OB  : chuỗi nến ngược màu cuối trong [b−5, d−1] → ứng viên; high[d] > mép trên → ORDER_BLOCK_UP ngay ở d
       OTE : nhịp X = cực trị cú quét, H = high[d]   → bắt đầu chờ (nếu H − X ≥ 2 ATR thì mới được vào);
             nhịp cũ đang chờ (mọi chiều)         → OTE_EXPIRED
 7. [S5] pd_bias          8. [S2] mức bảo vệ, [S4] dealing range
 9. [P1] pivot → S1 → S2, S4, S3          10. [S6] DOL          11. [T] khung lớn H1/H4
 12. ATR[t]; ảnh chụp timeline sau t
+12b. [OTE] nhịp chưa vào: H = max(H, high[t]) — dùng từ nến t+1
```

Hai quy tắc nhân quả: (i) vùng tạo ở nến d chỉ được chạm từ d + 1; (ii) đỉnh nhịp H dùng ở nến t là H của
nến t − 1, nên một nến vừa lập đỉnh mới vừa hồi sâu không tự vào OTE của chính nó.

**(b) Chuỗi sự kiện ví dụ trên M15** (số minh hoạ, ATR = 2,0):

```text
nến 199–200  hai nến giảm liền nhau: thân [2651,8 ; 2654,0] và [2651,2 ; 2651,9]; nến 201 tăng
nến 200  E2    low 2648,6 quét SSL 2650,0, close 2651,2 quay lại → SWEEP (b = r = 200, X = 2648,6)
nến 202  P3+E3 displacement tăng, close 2657,4 > 2650,0 → SHIFT_UP (d = 202)
nến 202  OB    OB-T = thân chuỗi 199–200: [2651,2 ; 2654,0], mean threshold 2652,6; high 2658,0 > 2654,0
               → xác nhận ngay → ORDER_BLOCK_UP (basis: SHIFT@202)
nến 202  OTE   X = 2648,6, H = 2658,0 → chờ
nến 203–206    giá lên tiếp, H = 2661,2 → vùng OTE = [2651,2 ; 2653,4]; OB giao với vùng OTE (K25)
nến 208  OB    low 2653,8 ≤ 2654,0 → OB_TAP_UP (K17; thêm K18–K21 nếu điều kiện đúng)
nến 210  OTE   low 2652,9 ≤ 2653,4 → OTE_ENTRY_UP, độ sâu 66% (K22, K25)
```

**(c) Đầu ra thêm** (đã cài):

| Loại | Nội dung |
|---|---|
| Sự kiện | `ORDER_BLOCK_UP/DOWN`, `OB_TAP_UP/DOWN`, `OB_FAIL_UP/DOWN`, `OB_EXPIRED`, `OTE_ENTRY_UP/DOWN`, `OTE_FAIL_UP/DOWN`, `OTE_EXPIRED`; `details.basis` trỏ về SHIFT (và OB khi K25) |
| Timeline | OB mở gần nhất phía dưới / trên giá (mép trên, mép dưới); OTE đang chờ (chiều, X, H, vùng, độ sâu hồi hiện tại) |
| Tham số | `ob_bien_the` (thân chuỗi / nến cuối cả râu), `ob_lui` 5, `ob_han` 96, `ote_tu` 0,62, `ote_den` 0,79, `ote_nhip_min_atr` 2,0, `ote_han` 96 |
| Phiên bản | `ict_structure` 0.5.0 (đã cài). Sự kiện cũ không đổi — kiểm bằng mốc so trước/sau và `scripts/regression_saved_runs.py` (đặc tả §1) |

**(d) Luồng làm việc và chỗ dừng duyệt:**

```text
① định nghĩa (plan §3.4) ──► ② BẠN DUYỆT (plan §8) ──► ③ khảo sát (research/, DB chỉ đọc, dev < 09/2024)
                                                              │ đúng hướng K17–K27, OB vs vùng giả,
                                                              │ OTE theo độ sâu, thêm vào mô hình học
                                                              ▼
⑦ lớp chart + replay ◄── ⑥ hồi quy run cũ khớp 100% ◄── ⑤ component + test ◄── ④ BẠN DUYỆT KẾT QUẢ
   (bật/tắt, kèm điểm thật)     (sự kiện cũ không đổi)       (order_block.py, ote.py;      (dừng ở đây nếu
                                                              tính tay, nhân quả)            không có giá trị
                                                                                             và không cần chart)
```

---

## 5. Trục C — Vòng nghiên cứu cho mỗi khái niệm

```text
 ① Đọc nguồn ──► ② Định nghĩa vận hành ──► ③ Code component ──► ④ Test
 (nghiên cứu §7,    (docs/thuat_toan_*.md,     (core/components,     tính tay, nhân quả
  video + mốc giờ)   tham số, phiên bản,        thứ tự trong nến)     prefix/suffix, gap
                     chỗ mơ hồ đã chọn)
        ▲                                                                  │
        │                                                                  ▼
 ⑧ Sửa định nghĩa ◄── ⑦ Đánh giá ◄──────── ⑥ Gán nhãn ◄──────── ⑤ Chạy dữ liệu thật
 (tăng phiên bản)     (so với ngẫu nhiên /    (trang Gán nhãn,      + replay «giải thích»
                       baseline, walk-forward, nhãn độc lập với      để nhìn từng nến
                       độ trễ, mật độ)         output thuật toán)
```

| Bước | Công cụ trong lab | Tài liệu mẫu |
|---|---|---|
| ② | `docs/thuat_toan_*.md` | `thuat_toan_dc_atr_structure.md` (có lịch sử phiên bản, khác biệt so với plan) |
| ④ | `tests/` | `test_dc_atr_structure.py` (tính tay, prefix = full, sửa đuôi không đổi quá khứ) |
| ⑤ | Thử nghiệm + «Replay từ vùng đang xem» | khung «Thuật toán đang làm gì» |
| ⑥ | trang Gán nhãn | `docs/guides/nhan_tham_chieu.md` |
| ⑦ | trang Đánh giá, `research/dc_experiment.py` | nghiên cứu §5.1, §6.3 |

---

## 6. Lộ trình: thứ tự đọc ↔ thứ tự xây

Mỗi bước đọc ở danh sách trước giờ gắn với một tầng cần xây:

| Bước | Đọc (nghiên cứu) | Xây (trục A) | Kết quả kiểm chứng |
|---|---|---|---|
| 1. Cách đánh giá | §1, §5.1, `disambiguation.md` | Tầng đánh giá: chuẩn so sánh ngẫu nhiên, walk-forward — **đã có** (10/2026, `danh_gia_thuat_toan.md` §1.2–1.3) | Bộ đo dùng chung cho mọi bước sau |
| 2. Swing | video bài 1.5, Larry Williams, §3.1 | P1 thành component có nhiều nguồn; S1 dùng chung | So pivot 1/1 vs 3/3 vs DC trên cùng nhãn |
| 3. FVG, BOS/MSS | §3.2, §3.3 | P2; E1 đọc S1/S2 từ component | FVG gắn nhãn nến 3; BOS khớp `swing_pivot` cũ |
| 4. Sweep, displacement, OB | §3.4–§3.6, §7 #1–#3 | S3, P3, E2, E3/E4 (mỗi chỗ mơ hồ = 2 biến thể) | Biến thể nào ổn định hơn trên nhãn |
| 5. Ngữ cảnh | §3.7, nền học thuật §5.2 | P5/C2, S4/C1, C3; regime (HMM/BOCPD) | Bộ lọc có làm tốt hơn baseline không |

Nguyên tắc: **không xây tầng trên khi tầng dưới chưa có test nhân quả và chưa có tài liệu định
nghĩa có phiên bản.** Lỗi ở P1 lan lên mọi tầng.
