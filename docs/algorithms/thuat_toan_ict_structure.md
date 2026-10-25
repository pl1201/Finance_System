# `ict_structure` — bộ nhận diện cấu trúc ICT phân tầng

**Trạng thái:** giai đoạn 1–2 đã cài (v0.2.0, 05/10/2026), order flow theo thanh khoản (v0.3.0,
06/10/2026) và **giai đoạn 3 — phần lõi** (v0.4.0, 08/10/2026): khung lớn H1/H4 gộp nội bộ mốc `ny_1700`
theo lịch phiên, PDH/PDL/PWH/PWL, vùng khung lớn làm vùng thanh khoản, phản ứng ở FVG khung lớn (`pd_bias`),
DOL, `details.htf`; giao diện giai đoạn 3 (nhóm lớp «Khung lớn», vùng theo tầng, dòng giải thích khung lớn — §11)
cài cùng ngày; **v0.4.1** (18/10/2026) bỏ `details.htf` ở sự kiện nguyên liệu (dung lượng); **v0.4.2** (19/10/2026)
sửa hai chỗ hở ở dữ liệu ngoài lịch do kiểm độc lập tìm ra; **v0.5.0** (21/10/2026) thêm order block và OTE neo
vào SHIFT (§4.20–§4.21; [`plan_ket_hop_ict_indicator.md`](../plans/plan_ket_hop_ict_indicator.md) §3.4, luồng
[`kien_truc_luong_ict.md`](../guides/kien_truc_luong_ict.md) §4.4); **v0.6.0** (21/10/2026) thêm lớp nhận diện: khoảng giá
80% / 50% cho 1h, 4h, xác suất chạm vùng gần nhất, trạng thái trend / range / nén / nhiễu (bước 13, đặc tả riêng
[`thuat_toan_nhan_dien.md`](thuat_toan_nhan_dien.md)). Công cụ hồ sơ khung
(plan §11.6) và giai đoạn 4 ([`plan_bias_regime.md`](../plans/plan_bias_regime.md)) chưa cài.
Nguồn: [`plan_ict_structure.md`](../plans/plan_ict_structure.md) bản 2.3 — quyết định B1–B3 (02/10/2026),
D1–D15 (duyệt 04/10/2026) và OF1–OF2 (order flow, chốt 06/10/2026 — plan §8.3). Không có BOS/CHoCH/MSS
(B1): sự kiện đổi hướng chỉ là **shift**; order flow (§4.12) đọc cả run lẫn shift. Khung lớn theo plan §11
(D9–D14). Mã: `core/algorithms/ict_structure/`, thành phần dùng chung `core/components/`, bộ gộp khung lớn
`core/data/htf_stream.py`, plugin hiển thị `frontend/js/algos/ict_structure.js`.

Không phải tín hiệu giao dịch. Đầu ra là **bằng chứng có giải thích** cho tầng regime (plan §1).

---

## 1. Phiên bản

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| 0.1.0 | 05/10/2026 | Giai đoạn 1: [G] lịch phiên + phân loại khoảng trống, [A] ATR, [P1] STH/STL, [S1] ITH/ITL (+ cấp 3 tuỳ chọn), [S2] thứ tự đỉnh/đáy + mức được bảo vệ, [S4] dealing range; timeline, trạng thái replay, giao diện tối thiểu |
| 0.2.0 | 05/10/2026 | Giai đoạn 2: [P3] displacement, [P2] FVG M15 + vòng đời, [S3]/[E2] vùng thanh khoản ITH/ITL + vòng đời chạm → lấy → sweep / run / chưa rõ, [E3] shift + `SHIFT_FVG` + `group_id`, [C] killzone; mục tiêu chấm và loại nhãn shift; khung «Thuật toán đang làm gì». Sự kiện và timeline của giai đoạn 1 **không đổi** (chỉ thêm khoá `killzone`, `vung_thanh_khoan` vào `details`, thêm cột timeline) — đã đối chiếu (§8) |
| 0.3.0 | 06/10/2026 | [OF] **order flow theo thanh khoản** (OF1–OF2): trạng thái tăng / giảm / chưa rõ / chưa có sau mỗi nến, chỉ đổi theo `LIQ_RUN_*` và `SHIFT_*` đã xác nhận; run phía ngược → chưa rõ (§4.12). Thêm 3 loại sự kiện `ORDER_FLOW_UP/DOWN/UNCLEAR`, 3 khoá timeline, khối `order_flow` trong `pending_state` và `run_stats`; chart chế độ Gọn / Chi tiết (sau đó vẽ lại theo plan hiển thị H-A, H-B cùng ngày — §11, không đổi lõi). Không thêm tham số, mục tiêu chấm hay loại nhãn. Sự kiện và timeline của 0.2.0 giữ nguyên (chỉ thêm) — đối chiếu ở §8.1. Tên hiển thị: «Cấu trúc ICT phân tầng + order flow» |
| 0.4.0 | 08/10/2026 | Giai đoạn 3 — **lõi** (plan §10 dòng 3, §11): [T0] bộ gộp tuần tự `ny_1700` + lịch phiên (`period_end` ≠ `known_at`, `coverage`, `degraded` / `over` / `after_hole`); [T1] ngăn xếp H1/H4 chạy chính P1 → S1 → S2, S4, FVG trên nến khung lớn đã chốt; [T2] PDH/PDL, PWH/PWL, giá mở ngày, midnight open; vùng H1/H4/D/W vào [S3]; [S5] phản ứng ở FVG H1/H4 → `pd_bias`; [S6] DOL; [T3] `details.htf` trên mọi sự kiện khung chạy + 15 cột timeline (§4.13–§4.19). 12 loại sự kiện mới (`HTF_*`, `PD_*`, `DOL_REACHED`), 8 tham số mới. **Output mặc định đổi**: thêm vùng tầng H1/H4/D/W → thêm/đổi `LIQ_*`, `SHIFT*`, `ORDER_FLOW_*` (bảng khác biệt §8.2); swing, khoảng trống, displacement, FVG M15 + vòng đời giữ nguyên tuyệt đối. Tên hiển thị: «Cấu trúc ICT phân tầng + khung lớn + order flow». Giao diện chưa đổi (§11) |
| 0.4.1 | 18/10/2026 | Dung lượng: sự kiện «nguyên liệu» khung chạy — `SWING_HIGH/LOW` (STH/STL), `FVG_UP/DOWN/TOUCHED/FILLED` (FVG M15 + vòng đời), `DISPLACEMENT_UP/DOWN` — **không mang `details.htf`** nữa (chiếm ~35% JSON sự kiện). Mọi thứ khác giữ nguyên tuyệt đối: XAUUSD M15 2022–2023 (47 066 nến) cùng 72 083 sự kiện, `event_id` / giá / nến / `reason_code` / details khác `htf` và toàn bộ timeline trùng 0.4.0; JSON sự kiện 133.4 → 85.4 MB (−36%). Ngữ cảnh khung lớn vẫn có ở timeline từng nến và trên sự kiện cấu trúc (ITH/ITL trở lên, LIQ, SHIFT, ORDER_FLOW, PD, DOL, khoảng trống) |
| 0.4.2 | 19/10/2026 | Sửa hai chỗ hở do kiểm độc lập tìm ra (18/10/2026): **F1** ô khung lớn mà lịch đóng trọn nhưng dữ liệu có nến → `degraded` `ngoai_lich` (trước: nến thường + `over`); **F2** kỳ D/W ngoài lịch không xoá PDH/PDL (PWH/PWL) của kỳ thường vừa chốt. Dữ liệu 2024 (XAUUSD M15, M5) **không đổi** (sự kiện, timeline trùng 0.4.1). XAUUSD M15 2018–2023: +151 `HTF_BAR_DEGRADED`, ITH/ITL H1/H4 −59, FVG H1/H4 −110, PD −110, `DOL_REACHED` −4; khung chạy: thứ tự 0 nến khác, order flow 52/141 742 nến, 10 sự kiện; `pdh_taken` có giá trị thêm ở 989 nến. EURUSD M15 2018–2023: +55 degraded, PDH/PDL −4 (Giáng sinh), order flow 0 nến khác. Cột `liq_*_id` đổi vì số thứ tự vùng đánh lại; giá vùng gần nhất khác ở ≤ 45 nến |
| 0.9.3 | 25/10/2026 | Thêm `forecast_record()` (ngoài hợp đồng `StructureAlgorithm`): **bản ghi dự báo** của nến vừa nạp — khoảng, mức, phá biên, còn giữ, mỗi thứ kèm B0 (`NdLayer.record`, đặc tả nhận diện §2) — cho luồng live chỉ ghi thêm và bộ chấm forward ([`core/eval/forward.py`](../../core/eval/forward.py), plan [`plan_mt5_live.md`](../plans/plan_mt5_live.md) §5, §6). Sự kiện, timeline, `pending_state`, `run_stats` không đổi — so tuyệt đối với 0.9.2 trên dev XAUUSD / EURUSD M15 + XAUUSD H1 (254 070 / 268 046 / 66 905 sự kiện) |
| 0.9.2 | 22/10/2026 | Lớp nhận diện: trạng thái v2 **vắt qua nghỉ theo lịch phiên** ([G] `SCHEDULED`: nghỉ hằng ngày / cuối tuần / lễ) — luật ở đặc tả nhận diện §4 bước 1. Lý do: khung trạng thái trống gần trọn thứ Hai trên H1. Dev 2018 → 08/2024, nến không có trạng thái: XAUUSD M15 8,3% → 0,6%, EURUSD M15 7,0% → 0,4%, XAUUSD H1 27,5% → 2,0%. **Đổi:** `STATE_*` (XAUUSD M15 8 381 → 8 653, EURUSD M15 9 273 → 9 467, H1 3 447 → 4 264) và cột `nd_*` theo trạng thái (trạng thái, độ mạnh, nén, đường trend, biên range, còn giữ, thời gian còn lại, phá biên), `run_stats.nhan_dien` khối trạng thái / thời gian / chấm biên range. **Giữ tuyệt đối** (so trên dev, cả 3 bộ): mọi sự kiện khác (chỉ khác con dấu `algorithm_version`), 58 cột timeline ngoài `nd_*`, khoảng 1h / 4h và xác suất chạm vùng gần nhất, `pending_state` / `run_stats` ngoài `nhan_dien`. `nd_kieu = v1` không đổi |
| 0.9.1 | 22/10/2026 | Lớp nhận diện: cột timeline `nd_duong` = «đường trend» (mức giữ trend / giữa hộp range — đặc tả nhận diện §5c); giao diện vẽ đường trên giá thay dải trạng thái. Mọi output khác không đổi |
| 0.9.0 | 22/10/2026 | Lớp nhận diện: **trạng thái v2** (đặc tả nhận diện §5c, plan [`plan_nhan_dien_v2.md`](../plans/plan_nhan_dien_v2.md)) — trend theo cấu trúc + lực, giữ tới CHoCH; range = hộp bền tới khi phá biên; nén là cờ. Bước 13 nhận thêm thứ tự M15, «mức bảo vệ đã phá», thứ tự H1. `nd_kieu = v1` cho output như 0.8.0 (đã so tuyệt đối). Sự kiện ICT, khoảng, xác suất chạm không đổi; `STATE_*`, cột `nd_trang_thai` … đổi theo v2 |
| 0.8.0 | 21/10/2026 | Lớp nhận diện: **PDH / PDL** còn nguyên vào xác suất chạm, tự chấm theo loại mức kèm chạm thật / kỳ vọng (khảo sát [`khao_sat_pdh_pdl.md`](../research/khao_sat_pdh_pdl.md): đúng chuẩn, không hiệu chỉnh riêng). Bước 13 nhận thêm ngữ cảnh mức theo kỳ (`_level_context`, dùng chung với ảnh chụp ngữ cảnh). Sự kiện, timeline không đổi; `pending_state` / `run_stats` của `nhan_dien` thêm loại mức; `cham_tong` giữ tập mức 0.7.0 |
| 0.7.0 | 21/10/2026 | **Thời gian** của lớp nhận diện (plan nhận diện bước 5): xác suất trạng thái đang hiện còn giữ sau 1h / 4h, thời gian còn lại, xác suất phá biên khi range — thành phần `state_clock`, mẫu close trong `price_band`; 5 cột timeline `nd_giu_*`, `nd_con_lai`, `nd_pha_*`; khối `thoi_gian` (đặc tả nhận diện §5b). Sự kiện, các output khác không đổi |
| 0.6.1 | 21/10/2026 | Lớp «Khoảng giá 1h / 4h + xác suất chạm» lên giao diện kèm điểm thật; `pending_state.nhan_dien` thêm `nen`, `diem_that` thêm Brier theo loại mức + `cham_tong` (chi tiết: [`thuat_toan_nhan_dien.md`](thuat_toan_nhan_dien.md) §1). Sự kiện, timeline không đổi |
| 0.6.0 | 21/10/2026 | **[N] lớp nhận diện** (người dùng chọn «bản đầu lên web ngay»; đặc tả [`thuat_toan_nhan_dien.md`](thuat_toan_nhan_dien.md)): bước 13 (§4.1) sau ATR[t]; thành phần `price_band` (khoảng 80% / 50% cho 1h, 4h theo giờ NY × ATR, xác suất chạm, tự chấm so với B0) và `market_state` (range / nén / trend / nhiễu, chống nhấp nháy 2 nến); 5 loại sự kiện `STATE_*`, 17 cột timeline `nd_*`, khối `nhan_dien` trong `pending_state` và `run_stats`, 7 tham số nâng cao `nd_*` (`nd_bat` tắt → output như 0.5.0). **Mọi output cũ giữ nguyên tuyệt đối** (cùng phép so như 0.5.0, 5 cấu hình). Giao diện: lớp «Trạng thái» (dải + hộp range + hàng 3 của dòng trạng thái); khoảng giá và xác suất chạm chưa vẽ (bước sau) |
| 0.5.0 | 21/10/2026 | **[E4] order block** và **[E6] OTE** neo vào SHIFT (plan kết hợp §3.4, duyệt 21/10/2026): ba bước chèn 3b, 6c, 12b (§4.1); 12 loại sự kiện mới (`ORDER_BLOCK_*`, `OB_TAP_*`, `OB_FAIL_*`, `OB_EXPIRED`, `OTE_ENTRY_*`, `OTE_FAIL_*`, `OTE_EXPIRED`), 9 cột timeline, khối `order_block` / `ote` trong `pending_state` và `run_stats`, 8 tham số nâng cao (§3). **Mọi output cũ giữ nguyên tuyệt đối**: sự kiện cũ (id, giá, nến, lý do, details), timeline trừ cột mới, `run_stats` và `pending_state` trừ khối mới — trên XAUUSD M15 2024, M5, H1, EURUSD M15 2023 và cấu hình cấp 3; hồi quy 110 cấu hình: chỉ 13 cấu hình `ict_structure` khác (thêm sự kiện), 97 cấu hình của thuật toán khác trùng. Giao diện: lớp «Order block», «OTE 62–79%» (§11) |

Quy ước: mỗi giai đoạn sau thêm loại sự kiện → output khác → tăng phiên bản (AGENTS §5.3). «v0.1»
trong plan là phạm vi của đặc tả đầu, không phải một bản phát hành.

## 2. Tầng, đầu vào, đầu ra

| | |
|---|---|
| Tầng (kien_truc_luong_ict §2) | [G] tầng 0 (dữ liệu); [P1]/[S1]/[P2]/[P3] tầng 1 (swing, FVG, displacement); [S2]/[S3]/[S4] tầng 2 (thứ tự, vùng thanh khoản, dealing range); [E2]/[E3] tầng 3 (sự kiện: sweep/run, shift); [OF] trạng thái order flow, chỉ đọc sự kiện tầng 3 (run, shift) đã xác nhận; [T] tầng 0 + P6 (nến khung lớn gộp nội bộ) rồi chính tầng 1–2 trên nến khung lớn; [S5] (phản ứng ở PD array khung lớn) và [S6] (DOL) — tầng 4, ngữ cảnh |
| Đầu vào | Nến **một khung** (khuyến nghị M15 — D9; khung ≤ H1 mới có [T]), đã đóng, theo thứ tự; lịch phiên khai báo `data/calendars/` (D14). Khung lớn **không** nạp từ dataset khác — gộp tuần tự từ chính luồng nến |
| Đầu ra | Sự kiện (§7), `timeline_point` mỗi nến, `pending_state` (replay), `run_stats` (tab Thống kê) |
| Ngoài hợp đồng | `forecast_record()` (0.9.3, bản ghi dự báo cho luồng live); `llm_context(events, symbol, digits)` — **bản tóm gọn** ở nến cuối cho trợ lý tổng hợp trang Live ([`digest.py`](../../core/algorithms/ict_structure/digest.py): nến cuối, các mục chọn của `pending_state` bỏ trường nội bộ và làm tròn, 30 sự kiện gần nhất bỏ loại ồn + nghĩa mã từ `core/vocab`, bảng giải nghĩa và câu lệnh tổng hợp; chỉ đọc, không đổi output nên không đổi phiên bản — plan [`plan_tro_ly_tong_hop.md`](../plans/plan_tro_ly_tong_hop.md) §3) |
| Thành phần | `session_gap` [G] · `swing_source` [P1] · `hierarchy` [S1] · `structure_order` [S2] · `dealing_range` [S4] · `displacement` [P3] · `fvg` [P2] · `liquidity` [S3]/[E2] · `shift` [E3] · `killzone` [C] · `order_flow` [OF] · `core/data/htf_stream.SessionHtfAggregator` [T0] · `htf_stack` [T1] · `period_levels` [T2] · `pd_array` [S5] · `dol` [S6] · `order_block` [E4] · `ote` [E6] (0.5.0) |

Thành phần chỉ dùng cho `ict_structure` (plan R7) — `swing_pivot` / `swing_hierarchy` **không** bị
refactor; tương đương được kiểm bằng test (§10). Ngăn xếp khung lớn [T1] dùng lại **chính** các thành phần của
khung chạy (không viết lại định nghĩa); hai thành phần dùng chung được mở rộng tương thích ngược: `PivotSource`
nhận thêm cờ «nến xấu» (mặc định tắt), `LiquidityBook` giữ một heap mỗi (phía, tầng) — chỉ một tầng thì hành vi y
như cũ (đối chiếu §8.2: sự kiện swing / FVG / khoảng trống / displacement trùng tuyệt đối với 0.3.0).

## 3. Tham số

| Tham số | Mặc định | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| `timeframe` | M15 | khớp dataset | Bước nến để phân loại khoảng trống; trang Thử nghiệm tự điền, sai → lỗi |
| `session_calendar` | `auto` | `auto` · `cme_globex_metals` · `fx_spot` · `none` | `auto` = theo mã của dataset (XAUUSD → CME kim loại, EURUSD → FX spot) — service đổi thành tên cụ thể **trước** khi chạy, run lưu tên đó |
| `pivot_left` / `pivot_right` | 1 / 1 | 1–10 | Cửa sổ pivot strict (§4.3) |
| `structure_level` | 2 | 1–3 | Cấp swing dùng cho thứ tự, mức được bảo vệ, dealing range: 1 STH/STL, 2 ITH/ITL (D2), 3 LTH/LTL. Vùng thanh khoản **luôn** từ ITH/ITL |
| `atr_period` | 14 | 2–500 | ATR Wilder, seed = trung bình `period` TR đầu có close trước |
| `eq_tol_atr` | 0.1 | 0–5 | Dung sai bằng giá × ATR: HH/EQH… giữa hai swing cấu trúc, và gộp hai ITH (ITL) liên tiếp thành một vùng EQH (EQL) — **do lab chọn** |
| `gap_policy` | `giu_muc_chan_cua_so` | hoặc `giu_muc_khong_chan` | D1. Bản «không chặn» chỉ để đối chiếu với `swing_pivot` / `swing_hierarchy` |
| `k_disp` / `body_min` | 1.5 / 0.6 | > 0 / 0–1 | Displacement: biên độ ≥ k × ATR\[t−1\], thân ≥ tỷ lệ × biên độ (≈ 7% nến M15 — survey-v2, **do lab chọn**) |
| `fvg_min_atr` | 0 | 0–5 | Kích thước FVG tối thiểu × ATR\[t−1\]; 0 = không lọc |
| `min_pen_atr` | 0.1 | 0–5 | Ngưỡng «lấy» thanh khoản × ATR\[b−1\] (D4) |
| `sweep_window` | 3 | 0–50 | W: cửa sổ quay lại tính cả nến lấy; ghi `sweep_bars` để lọc bản cùng nến (D3) |
| `shift_window` | 3 | 0–50 | Cửa sổ tìm displacement ngược chiều sau sweep (D5) |
| `killzones` | `asia=20-24,london=2-5,ny_am=7-10,london_close=10-12` | `ten=giờ-giờ`, giờ nguyên, không chồng | Giờ New York (có đổi giờ mùa hè), theo giờ mở nến; chỉ là cờ |
| `htf_list` | `H1,H4` | tập con của {H1, H4}; rỗng = tắt ngăn xếp khung lớn | [T1] khung lớn có ngăn xếp cấu trúc. Khung không lớn hơn khung dataset bị bỏ qua (dataset H1 → chỉ H4); dataset > H1 → tắt cả [T] (kể cả mức ngày/tuần). Tên khung chuẩn hoá về thứ tự H1, H4 |
| `htf_alignment` | `ny_1700` | chỉ `ny_1700` | Mốc nến khung lớn (D10). `utc_epoch` chỉ dùng cho `c2_cisd_research` — bộ gộp có hỗ trợ nhưng `ict_structure` không mở (§12) |
| `htf_min_coverage` | 0.9 | 0–1 | Nến khung lớn có `coverage` < ngưỡng → `degraded` (D14) |
| `period_levels` | bật | bool | PDH/PDL, PWH/PWL thành vùng thanh khoản tầng D/W (D13). Tắt → mức vẫn có trong `details.htf.levels` nhưng không thành vùng (`*_taken` = None) |
| `htf_events` | `an` | `an` · `khong_phat` | `an` = phát `HTF_*` (ẩn mặc định trên chart, ngoài chấm M15 — D12); `khong_phat` = chỉ giữ ngữ cảnh, không phát `HTF_*` (vùng, PD, DOL vẫn chạy y hệt) |
| `pd_respect_mode` | `strict` | `strict` · `loose` · `ce` | [S5] cách đo respect / disrespect (D6, §4.17) |
| `respect_away_atr` | 1.0 | 0–10; chỉ khi `strict` | Respect chặt: close rời mép gần ≥ k × ATR khung chạy của nến trước |
| `dol_min_tier` | `H1` | `H1` · `H4` · `D` · `W` | [S6] tầng vùng tối thiểu làm đích DOL (D7) |
| `ob_bien_the` | `than_chuoi` | `than_chuoi` · `nen_cuoi_rau` | [E4] OB-T (chuỗi nến ngược màu cuối, chỉ thân — gốc ICT) hay OB-R (một nến cuối, cả râu) (§4.20) |
| `ob_neo` | `shift` | `shift` · `displacement` | [E4] mốc tạo OB: SHIFT; hoặc mọi displacement có close vượt cực trị `ob_lui` nến trước (OB-D, ~5 lần nhiều hơn — để đối chứng) |
| `ob_lui` | 5 | 1–20 | [E4] tìm nến ngược màu trong [nến lấy − `ob_lui`, d − 1] (neo displacement: [d − `ob_lui`, d − 1]) |
| `ob_han` | 96 | 1–2000 | [E4] số nến từ mốc d tới khi ứng viên / OB chưa chạm hết hạn |
| `ote_tu` / `ote_den` | 0.62 / 0.79 | 0 < từ < đến ≤ 1 | [E6] vùng hồi của nhịp; vào khi chạm mức `ote_tu` (§4.21) |
| `ote_nhip_min_atr` | 2.0 | 0–20 | [E6] nhịp < k × ATR\[t−1\] → chưa có vùng |
| `ote_han` | 96 | 1–2000 | [E6] số nến từ SHIFT tới khi nhịp chưa vào vùng hết hạn |

Mặc định là cấu hình thí nghiệm (AGENTS §5.2), đổi khi có nhãn (D8) và qua vòng ⑦–⑧.

## 4. Quy tắc

### 4.1. Thứ tự trong một nến t (cố định)

1. **[G]** Kiểm nến (giá hữu hạn, OHLC hợp lệ, đúng khung, index và thời gian tăng). Khoảng trống
   giữa nến trước và t → phân loại → `ICT_GAP` tại t.
2. **[A]** ATR\[t−1\] là ngưỡng cho **mọi** so sánh ở nến t.
3. **[E2]** Vùng thanh khoản đã biết **trước** t: vùng đang chờ (đã lấy ở nến trước) → quay lại /
   hết cửa sổ / gặp khoảng trống; rồi vùng còn nguyên → chạm / lấy ở t (xét quay lại ngay trong t).
   Mỗi sweep sinh ứng viên shift.

   **3b. [E4]/[E6]** (0.5.0) OB đã xác nhận trước t: chạm lần đầu / hỏng / hết hạn → `OB_TAP_*` / `OB_FAIL_*` /
   `OB_EXPIRED`; ứng viên OB vượt đầu xa ở t → xác nhận → `ORDER_BLOCK_*`; nhịp OTE đang chờ (đầu nhịp của nến t−1):
   thủng gốc / vào vùng / hết hạn → `OTE_FAIL_*` / `OTE_ENTRY_*` / `OTE_EXPIRED` (§4.20–§4.21).
4. **[P3]** Displacement của t.
5. **[P2]** Chạm / lấp của FVG đã biết trước t; rồi FVG có nến 3 = t.
6. **[E3]** Ứng viên shift (kể cả ứng viên vừa sinh ở bước 3) xét nến t → `SHIFT`. Shift ở t−1 + FVG
   ở t có nến giữa t−1 → `SHIFT_FVG` (shift gần nhất được giữ **trước** bước này, nên một shift mới
   ở t không che `SHIFT_FVG` của shift ở t−1).

   **6b. [OF]** Lấy các `LIQ_RUN_*` (sinh ở bước 3) và `SHIFT_*` (bước 6) **của chính nến t**, theo thứ
   tự phát → cập nhật order flow (§4.12) → `ORDER_FLOW_*` nếu trạng thái đổi. Không đọc sweep, FVG,
   displacement, thứ tự hay mức được bảo vệ.

   **6c. [E4]/[E6]** (0.5.0) SHIFT ở t: OB đã xác nhận chưa chạm của chiều ngược lại → `OB_EXPIRED` (ứng viên chiều
   ngược bị bỏ); ứng viên OB mới từ nến < t (vượt đầu xa ngay ở t → `ORDER_BLOCK_*`); nhịp OTE mới (gốc = cực trị cú
   quét, đầu = high/low của t) thay nhịp đang chờ → `OTE_EXPIRED`. Hiệu lực từ t+1.
7. **[S5]** (0.4.0) Vùng FVG khung lớn đã biết **trước** t: chạm (tap) rồi kết quả đầu tiên đo bằng close\[t\]
   → `PD_RESPECT_*` / `PD_DISRESPECT_*`, cập nhật `pd_bias` (§4.17).
8. **[S2]** close\[t\] so với mức được bảo vệ đã biết trước t → cờ `protected_broken`. **[S4]**
   dealing range mở rộng theo high/low của t.
9. **[P1]** Pivot xác nhận tại t → **[S1]** cấp 2 → cấp 3 → với swing ở cấp cấu trúc: **[S2]** so
   sánh, thứ tự, mức được bảo vệ; **[S4]** đặt mốc mới; với ITH/ITL: **[S3]** vùng thanh khoản mới.
   Tất cả có hiệu lực từ t+1 (không gì ở nến t bị so với mức/vùng vừa biết ở chính t).
10. **[S6]** (0.4.0) Đích DOL bị lấy ở bước 3 → `DOL_REACHED`; shift ở bước 6 → DOL mới thay DOL cũ (§4.18).
11. **[T]** (0.4.0) Bộ gộp nhận nến t → nến H1/H4/ngày/tuần **chốt** tại t → ngăn xếp H1/H4 (ITH/ITL, thứ tự,
    dealing range, FVG), vùng thanh khoản tầng H1/H4/D/W, vùng PD, `HTF_*` — mọi thứ có hiệu lực từ t+1; giá mở
    ngày, midnight open (§4.13–§4.16).
12. **[A]** Cập nhật ATR\[t\]; **[T3]** chụp ngữ cảnh khung lớn sau t → timeline của nến t và `details.htf` của
    mọi sự kiện ở nến t+1 (§4.19). **12b.** (0.5.0) Nhịp OTE còn chờ: đầu nhịp theo high (low) của nến t — dùng từ t+1.
13. **[N]** (0.6.0, khi `nd_bat`) Trạng thái sau t (sự kiện `STATE_*` khi đổi) → mẫu biên của nến t − h hoàn tất, chấm
    dự báo cũ → khoảng + xác suất chạm tại t — đặc tả [`thuat_toan_nhan_dien.md`](thuat_toan_nhan_dien.md) §4. Chạy
    trước ảnh chụp ngữ cảnh, nên `details.htf` của `STATE_*` ở nến t vẫn là ngữ cảnh sau t − 1 như mọi sự kiện khác.

Bước 3b, 6c, 12b (0.5.0) chỉ đọc nến và sự kiện SHIFT / displacement đã sinh, chỉ ghi vào hai thành phần mới — mọi
output cũ giữ nguyên tuyệt đối (§1).

Bước 8 (trước đây 7) đứng sau 3–6 không đổi gì của giai đoạn 1 (các bước độc lập) — đã kiểm bằng đối chiếu (§8).
Bước 6b chỉ đọc sự kiện đã sinh ở t và không ghi vào thành phần nào khác, nên sự kiện và timeline của 0.2.0
giữ nguyên — đối chiếu ở §8.1. Bước 7, 10, 11 chỉ ghi vào thành phần mới, trừ việc bước 11 thêm vùng tầng
H1/H4/D/W vào sổ thanh khoản — có hiệu lực từ t+1 nên không đổi gì ở nến t; nhưng các nến sau gặp thêm vùng →
thêm/đổi sweep, run, shift, order flow (§8.2).

**Nhân quả khung lớn:** sự kiện ở nến t mang ngữ cảnh chụp ở bước 12 của nến **t−1** — tức nến khung lớn đã chốt
**≤ t−1**. Nếu nến H4 chốt đúng tại t, sự kiện ở t vẫn đọc ngữ cảnh **trước** lần chốt đó; timeline của t (sau bước
12) mới có nến H4 mới. Một nến không thể vừa lật ngữ cảnh khung lớn vừa được đọc là nằm «trong» ngữ cảnh mới.

### 4.2. [G] Lịch phiên và khoảng trống

Khoảng trống = `bar_time(t) − bar_time(t−1)` khác một bước khung. Phân loại theo lịch khai báo
(`SessionCalendar.classify_gap`):

| Loại | Khi nào | Bất thường |
|---|---|---|
| `nghi_phien` / `cuoi_tuan` / `nghi_le` | mọi ô thiếu nằm ngoài phiên theo lịch | không |
| `thieu_trong_phien` | có ô thiếu nằm **trong** phiên — thiếu dữ liệu | **có** |
| `lech_buoc` | khoảng cách không phải bội số bước khung | **có** |
| `ngoai_lich` | khoảng trống ngoài phạm vi lịch (2018–2025) | không phân loại |
| `khong_ro_lich` | `session_calendar = none` | không phân loại |

Chính sách (D1): **giữ** mọi mức swing / dealing range / vùng thanh khoản qua mọi khoảng trống;
**chặn** (mọi loại khoảng trống, kể cả nghỉ phiên):

* cửa sổ pivot vắt qua khoảng trống;
* bộ ba nến FVG vắt qua khoảng trống (đó là khoảng trống mở phiên, không phải FVG);
* displacement ở nến đầu sau khoảng trống;
* cửa sổ sweep (→ `LIQ_UNRESOLVED`) và cửa sổ shift (→ huỷ ứng viên) có khoảng trống.

Không tự lấp nến; khoảng trống bất thường không bị gộp thành Range/Uncertain (AGENTS §2.2).

### 4.3. [P1] STH/STL

STH tại nến c: `high[c]` lớn hơn **nghiêm ngặt** mọi high trong `pivot_left` nến trước và
`pivot_right` nến sau. Biết khi nến `c + pivot_right` đóng. STL đối xứng. Outside bar có thể vừa là
STH vừa là STL. Hai high bằng nhau → không nến nào là đỉnh (D15). Cửa sổ có khoảng trống → không xét
(đếm vào «pivot bị chặn»).

### 4.4. [S1] ITH/ITL, LTH/LTL

Ba STH liên tiếp `trái, giữa, phải`: `giữa` là ITH khi cao hơn nghiêm ngặt cả hai; xác nhận **khi STH
bên phải xác nhận** (không gắn về lúc đỉnh giữa hình thành). ITL đối xứng. Cấp 3 lọc trên chuỗi
ITH/ITL theo cùng quy tắc, chỉ khi `structure_level = 3`. Chuỗi swing nối qua khoảng trống (mức giữ).

### 4.5. [S2] Thứ tự đỉnh/đáy và mức được bảo vệ

Khi một swing cấu trúc mới có hiệu lực, so với swing cùng phía liền trước, dung sai
`eq_tol_atr × ATR[t−1]` (t = nến xác nhận):

* `hh` = +1 (HH), −1 (LH), 0 (EQH); `hl` = +1 (HL), −1 (LL), 0 (EQL);
* `order` = +1 khi `hh = hl = +1`; −1 khi `hh = hl = −1`; 0 (lẫn lộn) mọi trường hợp còn lại;
  chưa có đủ hai so sánh → chưa có (`None`). **Chỉ đổi khi có swing mới.**
* **Mức được bảo vệ** (một định nghĩa): `order` +1 → đáy cấu trúc gần nhất; −1 → đỉnh gần nhất;
  0 → không có.
* **`protected_broken`**: đã có close vượt **nghiêm ngặt** mức (dưới đáy / trên đỉnh) kể từ khi nó
  thành mức được bảo vệ; xoá khi mức đổi sang swing khác. **Không** phát sự kiện, **không** đổi
  `order` — đổi hướng chỉ đến từ shift (§4.10).

### 4.6. [S4] Dealing range

`range_hi` = max(đỉnh cấu trúc gần nhất, high cao nhất từ nến cực trị của đỉnh đó tới nến hiện tại);
`range_lo` đối xứng. Mở rộng dần theo từng nến; đặt lại khi có đỉnh/đáy cấu trúc mới. Vì gồm cả nến
hiện tại, dealing range **luôn chứa close** → `zone` (premium > EQ > discount) và
`range_pos = (close − lo)/(hi − lo)` ∈ [0, 1] luôn xác định khi đã có cả hai mốc.

### 4.7. [P3] Displacement

Nến t là displacement **tăng** khi `close > open`, `high − low ≥ k_disp × ATR[t−1]` và
`|close − open| ≥ body_min × (high − low)`; **giảm** đối xứng. Không xét khi chưa có ATR hoặc t là
nến đầu sau khoảng trống. Sự kiện `DISPLACEMENT_UP/DOWN` ẩn mặc định trên chart; làm `basis` cho shift.

### 4.8. [P2] FVG M15 và vòng đời

* **Tăng:** `low[t] > high[t−2]`, vùng `[high[t−2], low[t]]`; **giảm:** `high[t] < low[t−2]`, vùng
  `[high[t], low[t−2]]`. Biết khi t đóng; `event_bar` = t−1 (nến giữa, để vẽ), giá sự kiện = giữa vùng.
* Loại nếu có khoảng trống trước t−1 hoặc trước t (đếm `bo_vi_khoang_trong`). `fvg_min_atr > 0` →
  loại vùng nhỏ hơn ngưỡng × ATR\[t−1\] (chưa có ATR cũng loại).
* `from_displacement` = nến giữa là displacement **cùng chiều**.
* Vòng đời, từ nến sau lúc biết: `FVG_TOUCHED` khi giá tới **mép gần** lần đầu (FVG tăng: `low ≤ hi`),
  `FVG_FILLED` khi tới **mép xa** (`low ≤ lo`); giảm đối xứng. Có thể cùng một nến (phát chạm rồi lấp).
  «Đã lấp» chỉ là mốc mô tả, không phải tín hiệu. FVG đang mở nằm trong heap theo mép → tổng chi phí
  O(N log N).

### 4.9. [S3]/[E2] Vùng thanh khoản và vòng đời: chạm → lấy → sweep / run / chưa rõ

**Nguồn:** ITH → vùng **BSL** (phía trên), ITL → **SSL** (phía dưới), tầng `M15` (= khung chạy, kể cả khi
dataset là M5/H1). Từ 0.4.0 thêm tầng `H1`, `H4` (ITH/ITL khung lớn — §4.14) và `D`, `W` (PDH/PDL, PWH/PWL —
§4.15); mọi tầng chung **một** vòng đời dưới đây (§4.16).

* **Hiệu lực** từ nến sau nến xác nhận ITH/ITL. Nếu trong các nến (cực trị, nến xác nhận] đã có nến
  xuyên mức ≥ `min_pen_atr × ATR[j−1]` → **không tạo** vùng (đã bị lấy trước khi biết; xảy ra khi có
  đỉnh bằng giá không thành STH, hoặc pivot bị chặn vì khoảng trống). Lý do ghi vào
  `details.vung_thanh_khoan` của ITH/ITL.
* **EQH/EQL:** ITH mới chênh với vùng của ITH **liền trước** cùng phía ≤ `eq_tol_atr × ATR[t−1]` và
  vùng đó còn nguyên → gộp, mức = cực trị của hai, `nguon` liệt kê cả hai. Swing liền trước không tạo
  vùng → không gộp vượt qua nó.
* **Vùng còn nguyên ở nến t** (BSL; SSL đối xứng):
  * **chạm**: `0 < high[t] − mức < min_pen_atr × ATR[t−1]` → vẫn còn nguyên, `so_lan_cham` +1, không
    phát sự kiện;
  * **lấy** tại nến b đầu tiên có `high[b] − mức ≥ min_pen_atr × ATR[b−1]` (định nghĩa duy nhất của «đã
    lấy»; vùng không bao giờ quay lại còn nguyên). **ATR khoá** = ATR\[b−1\]; `xuyen_atr` theo ATR khoá.
    Chưa có ATR → chưa xét.
* **Giải quyết** sau khi lấy, cửa sổ W = `sweep_window` (tính cả nến lấy):
  * `LIQ_SWEEP_BSL` tại r = nến **đầu tiên** trong [b, b+W] có `close[r] < mức`, không có khoảng trống
    trong (b, r]; `sweep_bars = r − b` (0 = quay lại ngay nến lấy);
  * `LIQ_RUN_UP` tại b+W nếu hết cửa sổ mà close không quay lại;
  * `LIQ_UNRESOLVED` nếu gặp khoảng trống (mọi loại) trước khi rõ — phát ở nến đầu sau khoảng trống,
    ghi loại khoảng trống; không thành sweep hay run;
  * hết dữ liệu khi đang chờ → vẫn chờ (không phát gì; `pending_state` liệt kê).
* **Gom sự kiện** theo (nến giải quyết, kết cục, phía): một sự kiện, `details.pools` liệt kê từng vùng
  với vòng đời riêng. **Vùng chính** = tầng cao nhất, rồi mức xa nhất (BSL cao nhất / SSL thấp nhất):
  nến sự kiện = nến lấy b của vùng chính, giá = mức vùng chính, `tang` = tầng vùng chính.
* Vùng còn nguyên nằm trong heap theo mức (xoá lười theo `version` khi gộp) → chỉ xét vùng giá đã chạm
  tới.

### 4.10. [E3] Shift = sweep → displacement ngược chiều

* Mỗi vùng trong một sweep tại r sinh **một ứng viên**: mức bị quét, cực trị cú quét
  `X = max(high[b..r])` (BSL) hoặc `min(low[b..r])` (SSL), hạn chót `r + shift_window`.
* **Shift giảm** (sau quét BSL) tại d = nến **đầu tiên** trong [r, r + shift_window] thoả cả bốn:
  1. d là displacement giảm (§4.7);
  2. `close[d] <` mức bị quét;
  3. không có khoảng trống trong (r, d] → nếu có, **huỷ**;
  4. không nến nào trong (r, d] có `high > X` → nếu có, **huỷ**, không tìm tiếp.

  Shift tăng đối xứng. Xét được ngay ở nến quét (d = r).
* **Cùng một nhịp (R4):** mọi ứng viên cùng chiều trúng ở cùng d → **một** `SHIFT_UP/DOWN` tại d,
  `details.swept` liệt kê tất cả. **Ứng viên chính** = tầng cao nhất, rồi sweep gần nhất, rồi mức xa
  nhất: `reference_event_id` = sweep của nó, `group_id` = `group_id` của sweep đó (= `event_id` sweep),
  `basis` = các sweep + displacement ở d. Giá = close\[d\].
* **`SHIFT_FVG_UP/DOWN`:** FVG cùng chiều biết ở d+1 có nến giữa = d (FVG do chính displacement tạo ra)
  → phát ở d+1, nến sự kiện = d, giá = close\[d\], `reference_event_id` = shift, cùng `group_id`. Shift
  **không bị sửa**; không tìm FVG xa hơn.
* **Ngôn ngữ:** «shift có displacement» lúc phát hiện — chưa biết sẽ tiếp diễn hay thất bại.

### 4.11. [C] Killzone

Giờ New York (`zoneinfo`, có đổi giờ mùa hè) theo **giờ mở** nến; khung nửa mở `[bắt đầu, kết thúc)`.
Mọi sự kiện mang `details.killzone` của nến sự kiện (`null` = ngoài killzone); timeline mang killzone của
nến t. Chỉ là cờ — không lọc sự kiện ở v0.2.

### 4.12. [OF] Order flow theo thanh khoản (0.3.0)

Quyết định OF1–OF2 (người dùng chốt 06/10/2026, plan §8.3). Thành phần `core/components/order_flow.py`
(lớp `OrderFlow`). Không có tham số riêng.

**Đầu vào ở nến t:** chỉ các sự kiện **đã xác nhận tại t** thuộc bốn loại dưới đây. Sweep, FVG,
displacement, HH/HL và mức được bảo vệ **không** là đầu vào.

| Loại | Kiểu, chiều | Nghĩa |
|---|---|---|
| `LIQ_RUN_UP` | run, +1 | BSL bị lấy, close không quay lại dưới mức trong W nến (§4.9) |
| `LIQ_RUN_DOWN` | run, −1 | SSL bị lấy, close không quay lại trên mức trong W nến |
| `SHIFT_UP` | shift, +1 | quét SSL rồi displacement tăng (§4.10) |
| `SHIFT_DOWN` | shift, −1 | quét BSL rồi displacement giảm |

**Trạng thái** `order_flow`: `1` tăng · `-1` giảm · `0` chưa rõ · `None` chưa có (chưa có run hay shift
nào kể từ đầu run).

**Cập nhật tại t** (chỉ khi t có ít nhất một sự kiện ở bảng trên):

1. Có cả chiều +1 lẫn −1 trong cùng nến → chưa rõ, lý do `hai_chieu_cung_nen`.
2. Ngược lại, gọi d là chiều duy nhất:
   * có shift chiều d → d, lý do `shift_tang` / `shift_giam` — kể cả khi đang −d;
   * chỉ có run: đang `None`, `0` hoặc d → d, lý do `run_tang` / `run_giam`; đang −d → chưa rõ, lý do
     `run_nguoc_chieu`.
3. Kết quả bằng trạng thái hiện tại → **không đổi gì**: không phát sự kiện, giữ nguyên `order_flow_since`
   và `order_flow_reason`. Khi đang tăng/giảm, sự kiện cùng chiều chỉ «ủng hộ»: ghi vào `ung_ho_gan_nhat`
   (`pending_state`; nến có cả run lẫn shift cùng chiều → ghi shift). Nến hai chiều khi đang chưa rõ giữ
   chưa rõ và không tính là ủng hộ.
4. Khác → đổi trạng thái: `order_flow_since` = t, `order_flow_reason` = mã ở trên, xoá `ung_ho_gan_nhat`,
   phát `ORDER_FLOW_*` (§7). Sự kiện kích hoạt = shift nếu có, không thì run; `hai_chieu_cung_nen` → không
   có sự kiện kích hoạt.

**Bảng chuyển trạng thái** (ô = trạng thái sau nến t · lý do; «—» = giữ nguyên, không phát sự kiện):

| Đang \ sự kiện ở t | chỉ run +1 | chỉ run −1 | shift +1 (có thể kèm run +1) | shift −1 (có thể kèm run −1) | có cả +1 lẫn −1 |
|---|---|---|---|---|---|
| chưa có (`None`) | tăng · `run_tang` | giảm · `run_giam` | tăng · `shift_tang` | giảm · `shift_giam` | chưa rõ · `hai_chieu_cung_nen` |
| chưa rõ (`0`) | tăng · `run_tang` | giảm · `run_giam` | tăng · `shift_tang` | giảm · `shift_giam` | — |
| tăng (`1`) | — (ủng hộ) | chưa rõ · `run_nguoc_chieu` | — (ủng hộ) | giảm · `shift_giam` | chưa rõ · `hai_chieu_cung_nen` |
| giảm (`-1`) | chưa rõ · `run_nguoc_chieu` | — (ủng hộ) | tăng · `shift_tang` | — (ủng hộ) | chưa rõ · `hai_chieu_cung_nen` |

Lý do → `reason_code` của sự kiện: `run_tang` / `run_giam` → `OF_RUN`; `shift_tang` / `shift_giam` →
`OF_SHIFT`; `run_nguoc_chieu` → `OF_OPPOSITE_RUN`; `hai_chieu_cung_nen` → `OF_BOTH_SIDES`.

Chuỗi trạng thái từng nến phải **trùng tuyệt đối** với `rule_a` của
[`research/orderflow_rules.py`](../../research/orderflow_rules.py) chạy trên chính các run/shift của lõi, khi
coi `None` là 0 — đây là bằng chứng nghiệm thu (§8.1, §10).

**Cơ sở ICT** (tóm tắt; chi tiết ở [`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md)
§2, trích video gốc có mốc thời gian ở [`nghien_cuu_orderflow_ict_nguon.md`](../research/nghien_cuu_orderflow_ict_nguon.md)
§1–§4):

* ICT đọc order flow **thuần từ giá**: giá đi lấy thanh khoản (stop) hoặc đi lấp chỗ kém hiệu quả —
  «thanh khoản → thanh khoản». Lab đọc phần «lấy thanh khoản» bằng run (lấy rồi đi tiếp) và shift (quét
  một phía rồi displacement ngược lại — B2).
* Quy tắc vận hành ICT nói rõ nhất (2023): khi tăng, đáy ngắn hạn bị lấy chỉ là stop run, giá phải quay lên
  ngay; đỉnh ngắn hạn liên tục bị lấy. Vì vậy **sweep** (lấy rồi quay lại) không đổi order flow — sweep
  không là đầu vào.
* Khi mức đang tin bị phá, ICT «sitting on my hands», chờ thêm thông tin — không đảo chiều ngay. Lab ứng
  với điều này bằng **run phía ngược** → chưa rõ; chỉ shift mới lật thẳng.
* ICT không cho con số: W, ngưỡng «lấy», displacement là của lab (§3). ICT còn coi FVG là thanh khoản
  trong range (IRL); 0.3.0 chưa dùng FVG (§9).

**Mô tả, không phải dự báo.** Trên dữ liệu lab (XAUUSD, EURUSD 2018–08/2024; M5–H4), không cách đọc order
flow nào — kể cả run + shift — cho biết phía thanh khoản nào bị lấy kế tiếp tốt hơn mốc ngẫu nhiên theo
khoảng cách (lợi thế trong ±2 điểm %; nghiên cứu §1, §5). Khi «chưa rõ» kết thúc, 44–50% quay lại chiều
cũ, 50–56% sang chiều mới (nghiên cứu §8.3). Dải order flow trả lời «giá vừa lấy thanh khoản phía nào, đang
đi về phía nào», không trả lời «giá sẽ đi đâu». Vì vậy `ORDER_FLOW_*` không có mục tiêu chấm hay loại
nhãn, và giao diện ghi «vùng gần nhất», không ghi «đích».

**Vùng theo vai** (`pending_state["order_flow"]`): khi tăng, vùng **cùng chiều** = BSL còn nguyên gần nhất
phía trên (như `liq_above`), vùng **ngược chiều** = SSL còn nguyên gần nhất phía dưới (bị run → chưa rõ);
khi giảm thì đối xứng; chưa rõ hoặc chưa có → không có vùng. Từ 0.4.0 vùng gồm mọi tầng (M15, H1, H4, D, W —
§4.9, §4.16), nên «vùng gần nhất» có thể là PDH hay ITH H4.

**Ví dụ thật.** XAUUSD M5 `ds_933fa5ec67e2`, tham số mặc định, lịch `cme_globex_metals`, chạy **từ đầu
dataset** (nến #0 = 01/01/2024 23:00 UTC; chỉ số nến = chỉ số trong dataset). Chuỗi dưới đây kiểm bằng sự
kiện run/shift của lõi (0.2.0 — 0.3.0 không đổi hai loại này) và `rule_a`:

| Nến (giờ UTC) | Sự kiện đầu vào xác nhận ở nến này | Order flow | Lý do → sự kiện 0.3.0 |
|---|---|---|---|
| #1653 · 09/01 21:45 | `LIQ_RUN_UP` (nến lấy #1650, 21:30) | giảm → **chưa rõ** | `run_nguoc_chieu` → `ict:ORDER_FLOW_UNCLEAR@1653>1653` (`OF_OPPOSITE_RUN`) |
| #1659 · 09/01 23:15 | `LIQ_SWEEP_BSL` | chưa rõ | sweep không là đầu vào |
| #1661 · 09/01 23:25 | `SHIFT_DOWN` (quét BSL 2031.005 ở #1659 rồi displacement giảm) | chưa rõ → **giảm** | `shift_giam` → `ict:ORDER_FLOW_DOWN@1661>1661` (`OF_SHIFT`) |
| #1683, #1684 · 10/01 01:15, 01:20 | `LIQ_SWEEP_SSL` (hai lần) | giảm | — |
| #1687 · 10/01 01:35 (Asia) | `SHIFT_UP` (quét SSL 2028.205 — nến lấy #1682, quay lại ở #1684 — rồi displacement tăng) | giảm → **tăng** | `shift_tang` → `ict:ORDER_FLOW_UP@1687>1687` (`OF_SHIFT`) |
| #1688, #1690 · 01:40, 01:50 | `LIQ_SWEEP_BSL` | tăng | — |
| #1706, #1735, #1738 · 03:10, 05:35, 05:50 | `LIQ_SWEEP_SSL` (nến lấy #1706, #1735, #1737) | tăng | đáy bị quét rồi quay lại: stop run, không đổi chiều |
| #1740 · 06:00 | `LIQ_RUN_DOWN` (nến lấy #1737, 05:45 — trễ W = 3 nến) | tăng → **chưa rõ** | `run_nguoc_chieu` → `ict:ORDER_FLOW_UNCLEAR@1740>1740` (`OF_OPPOSITE_RUN`) |
| #1763 · 07:55 (London) | `LIQ_RUN_UP` (nến lấy #1760, 07:40) | chưa rõ → **tăng** | `run_tang` → `ict:ORDER_FLOW_UP@1763>1763` (`OF_RUN`) |
| #1767 · 08:15 (London) | — | tăng | timeline: `order_flow` = 1, `order_flow_since` = 1763, `order_flow_reason` = `run_tang` |
| #1768 · 08:20 | `LIQ_RUN_UP` (nến lấy #1765) | tăng | cùng chiều: chỉ cập nhật `ung_ho_gan_nhat`, không phát sự kiện |

`reference_event_id` của mỗi `ORDER_FLOW_*` là sự kiện đầu vào cùng dòng (vd `ict:SHIFT_DOWN@1661>1661`
cho #1661, `ict:LIQ_RUN_DOWN@1737>1740` cho #1740). Các sweep không đổi gì vì không là đầu vào; giữa
#1687 và #1740 order flow giữ «tăng» qua năm sweep, cả hai phía.

Nến lấy #1737 cho thấy sweep và run khác nhau thế nào: nến này lấy bốn vùng SSL. Hai vùng thấp hơn
(2025.978, 2026.015) có close quay lại trên mức ở #1738 → sweep. Hai vùng cao hơn (2026.688, 2027.145)
không có close nào quay lại tới #1740 → run, và chính run này đưa order flow sang chưa rõ. Ở #1767, BSL
gần nhất phía trên (`liq_above`) là 2040.015, SSL gần nhất phía dưới (`liq_below`) là 2023.795.

Đã đối chiếu với lõi 0.3.0 (06/10/2026): đúng năm `ORDER_FLOW_*` ở bảng (id, `reason_code`, tham chiếu,
`ly_do`), timeline ở #1767, và `pending_state` — vùng cùng chiều B163 (2040.015), vùng ngược chiều S181
(2023.795); `ung_ho_gan_nhat` rỗng ở #1767, thành `ict:LIQ_RUN_UP@1765>1768` từ #1768.

### 4.13. [T0] Bộ gộp khung lớn `ny_1700` theo lịch phiên (0.4.0)

`core/data/htf_stream.SessionHtfAggregator` nhận **từng** nến khung chạy đã đóng (luồng duy nhất — không nạp dataset
khung lớn) và trả các nến khung lớn **vừa chốt** tại nến đó. Khung: H1, H4 (ngăn xếp cấu trúc) và D, W (chỉ mức
theo kỳ). Chỉ chạy khi khung chạy ≤ H1 và chia hết 1 giờ.

**Mốc `ny_1700`** (D10; `bucket_bounds`), giờ đồng hồ New York có đổi giờ mùa hè:

| Khung | Bucket danh nghĩa |
|---|---|
| H1 | giờ tròn (độ lệch New York là số giờ nguyên → trùng `utc_epoch`) |
| H4 | 6 nến từ 17:00 NY: 17, 21, 01, 05, 09, 13 giờ NY. Giờ nghỉ 17:00–18:00 nằm **trong** nến đầu ngày |
| D | 17:00 NY → 17:00 NY hôm sau (ngày giao dịch mang tên ngày nó kết thúc) |
| W | mở Chủ nhật 17:00 NY, danh nghĩa 7 ngày; theo lịch đóng Thứ Sáu 17:00 NY (xem `period_end`) |

Ví dụ: 08/03/2024 (EST) D = 07/03 22:00 → 08/03 22:00 UTC; sau đổi giờ 10/03 D = 10/03 21:00 → 11/03 21:00 UTC;
tuần có đổi giờ dài 167 giờ danh nghĩa (03/11/2024: 169 giờ).

**Số nến kỳ vọng, `period_end`:** `expected_bars` = số ô khung chạy (lưới neo ở mốc mở bucket) có giờ mở nằm trong
một phiên của lịch khai báo — cùng quy ước với `SessionCalendar.classify_gap`. `period_end` = mốc đóng của **ô mở
cuối cùng** trong bucket theo lịch: bằng mốc danh nghĩa trừ ngày đóng sớm (vd 15/01/2024 MLK: D, H4 13–17 đóng
19:30 UTC) và kỳ có ngày lễ (tuần có Good Friday đóng Thứ Năm 17:00 NY). Không có lịch (`none`) hoặc ngoài phạm vi
lịch → số ô danh nghĩa, `period_end` = mốc danh nghĩa (§12).

**Chốt nến:** khi nến khung chạy có `close_time` ≥ `period_end` → `known_at` = `close_time` của nến đó (= `period_end`
khi nến cuối đúng lịch — mọi trường hợp trên dữ liệu thật; kiểm độc lập 18/10/2026). Thiếu
nến cuối → chốt khi nến đầu của kỳ sau tới: `known_at` = close của nến đó > `period_end` (**chốt muộn**,
`late`). Nến khung chạy tới sau khi kỳ đã chốt theo lịch nhưng vẫn trong bucket danh nghĩa (dữ liệu khác lịch,
vd có nến sau giờ đóng sớm 23/11/2018) → **kỳ «nối tiếp»** riêng, `outside_calendar` + `over` + `degraded`
(lý do `ngoai_lich`): vài nến lẻ không thành một nến khung lớn trong cấu trúc. Từ **0.4.2**: ô mà lịch đóng trọn
(số nến kỳ vọng = 0) nhưng dữ liệu có nến (vd 24/12 EURUSD, nến 17:00 NY XAUUSD 2018) cũng `degraded` lý do `ngoai_lich`
— trước đó thành nến khung lớn thường, chỉ gắn `over` (kiểm độc lập F1).

**Mỗi nến chốt** (`HtfBar`, bất biến, dùng được như `Bar`): `index` (thứ tự nến đã chốt của khung), `bar_time` (mở
danh nghĩa), `close_time` = `period_end`, OHLC, `known_index` / `known_at` (nến khung chạy làm hệ thống biết),
`n_bars`, `expected_bars`, `coverage` = `n_bars / expected_bars` (None khi kỳ vọng 0), nến khung chạy đạt high /
low (nến **đầu tiên** đạt — strict), cờ:

* `degraded` — `coverage` < `htf_min_coverage` (lý do `coverage_thap`), hoặc kỳ đầu luồng thiếu nến (`ky_dau_thieu`
  — dataset/khoảng chạy bắt đầu giữa kỳ), hoặc kỳ «nối tiếp» (`ngoai_lich`) → `HTF_BAR_DEGRADED`;
* `over` — nhiều nến hơn lịch: chỉ gắn cờ, **không** coi là thiếu (plan §11.4);
* `after_hole` — giữa nến chốt trước và nến này có ô mở theo lịch mà không có nến nào (mất trọn bucket). Bucket
  không có nến không tồn tại;
* `contiguous_prev` — nến mở đúng lúc nến chốt trước **đóng theo lịch** (`start == prev.period_end`): sai khi
  giữa hai nến có nghỉ phiên (H1 qua 17:00–18:00), cuối tuần, đóng sớm, ngày lễ hoặc hole.

Nến đang hình thành chỉ có ở `forming()` (để vẽ, có nhãn «đang hình thành — chưa dùng»); không bao giờ vào trạng
thái. `HtfAggregator` (`utc_epoch`, `c2_cisd_research`) **giữ nguyên** — hồi quy khớp 100% (§8.2).
`core/data/resample.py` thêm `alignment = ny_1700` (+ `calendar` tuỳ chọn để «đủ nến» theo lịch) — dùng cho phép
thử tương đương.

### 4.14. [T1] Ngăn xếp H1/H4 (0.4.0)

`core/components/htf_stack.HtfStack` chạy **chính** các thành phần của khung chạy trên nến khung lớn đã chốt, ATR
Wilder riêng của khung (cùng `atr_period`), cùng `pivot_left/right`, `eq_tol_atr`, `k_disp`, `body_min`,
`fvg_min_atr`:

* [P1] STH/STL strict → [S1] **ITH/ITL** (cấp 2 — luôn cấp 2, không theo `structure_level`);
* [S2] thứ tự đỉnh/đáy, mức được bảo vệ (dung sai × ATR khung lớn lúc xác nhận); `protected_broken` theo
  **close nến khung lớn** đã chốt;
* [S4] dealing range mở rộng theo high/low nến khung lớn đã chốt;
* [P3] displacement (theo ATR khung lớn) chỉ để gắn `from_displacement` cho FVG; [P2] FVG ba nến khung lớn.

Thứ tự trong một nến khung lớn như bước 4–9, 12 của khung chạy: displacement → FVG (bộ ba kết thúc ở nến này) →
cờ vượt mức được bảo vệ → mở rộng dealing range → pivot → ITH/ITL → thứ tự, mức, mốc dealing range → ATR.

**Quy tắc chất lượng lan truyền (R3):**

* nến `degraded` không được nằm **ở bất kỳ vị trí nào** của cửa sổ pivot c−1..c+1 (`PivotSource(bad=…)`); cửa sổ
  vắt qua hole (`after_hole` của nến 2..3 trong cửa sổ) bị chặn. Nghỉ phiên, cuối tuần **không** chặn pivot khung
  lớn (khác khung chạy — D1 chặn mọi khoảng trống);
* FVG: ba nến phải liền kề theo lịch (`contiguous_prev` của nến 2 và 3) và không nến nào `degraded`;
* ITH/ITL chỉ dựng từ STH hợp lệ → thứ tự, dealing range, vùng, FVG tự không có trên dữ liệu thiếu. Không có cờ
  riêng cho từng sự kiện; ngữ cảnh mang `blocked_windows_recent` = số cửa sổ pivot (mọi tâm, không chỉ ứng viên)
  bị chặn vì chất lượng trong 20 nến khung lớn gần nhất (do lab chọn).

**Khởi động:** `ready` = đã có ATR khung lớn **và** đã có thứ tự (`order` khác None).

**Sự kiện** (ẩn mặc định, ngoài chấm M15 — D12; `htf_events = khong_phat` thì không phát):

* `HTF_SWING_HIGH/LOW` — mỗi ITH/ITL khung lớn: nến sự kiện = nến khung chạy **chạm cực trị**
  (`high_bar`/`low_bar` của nến khung lớn ở giữa), nến xác nhận = nến khung chạy tại `known_at` của nến khung lớn
  làm ITH/ITL được biết; giá = ITH/ITL. `details` mang chỉ số nến khung lớn ba STH, so sánh HH/LH…, `order_sau`,
  `period_end`, `known_at`, `coverage`, `vung_thanh_khoan`;
* `HTF_FVG_UP/DOWN` — nến sự kiện = nến khung chạy **đầu tiên** của nến khung lớn ở giữa; xác nhận ở `known_at` của
  nến thứ ba; giá = giữa vùng; vùng `lo`/`hi`, `kich_thuoc_atr` (ATR khung lớn), `from_displacement`,
  `hieu_luc_tu_nen`.

### 4.15. [T2] Mức theo kỳ: PDH/PDL, PWH/PWL, giá mở ngày, midnight open (0.4.0)

`core/components/period_levels.PeriodLevels` (R5):

* **PDH/PDL, PWH/PWL** = high/low của nến D / W đã chốt. Biết tại `known_at` của kỳ, hiệu lực từ nến sau. Kỳ
  `degraded` (kể cả kỳ đầu luồng thiếu nến, kỳ «nối tiếp») **không** tạo mức. Kỳ thường thiếu dữ liệu (coverage thấp,
  kỳ đầu) → PDH/PDL (PWH/PWL) = None tới khi kỳ sau chốt; kỳ **ngoài lịch** (`ngoai_lich` — nối tiếp sau giờ đóng, ô lịch
  đóng trọn) **không thay** mức của kỳ thường vừa chốt (0.4.2, kiểm độc lập F2 — trước đó mức thành None suốt kỳ sau trong
  khi vùng D/W của kỳ thường vẫn sống). Khi `period_levels` bật, mỗi mức thành vùng thanh khoản tầng `D` / `W` và phát `HTF_PERIOD_HIGH/LOW`
  (nến sự kiện = nến khung chạy đạt high/low của kỳ, xác nhận ở `known_at`; `details.ten` = PDH/PDL/PWH/PWL);
* **giá mở ngày** = open của nến khung chạy **đầu tiên** của ngày giao dịch, chỉ khi nến đó mở đúng **ô mở đầu
  tiên theo lịch** (thường 18:00 NY); thiếu → None, không lấy giá thay thế. Biết tại close nến đó;
* **midnight open** = open của nến mở đúng 00:00 NY của ngày giao dịch. Không có nến đó → None. Trước 00:00 NY
  (18:00–24:00) → None. Biết tại close nến đó.

### 4.16. [S3] Vùng thanh khoản nhiều tầng (0.4.0)

Cùng vòng đời §4.9 (chạm → lấy → sweep / run / chưa rõ, ATR khoá khung chạy, cửa sổ W khung chạy) cho mọi tầng:

| Tầng | Nguồn | Biết / hiệu lực | Gộp EQH/EQL |
|---|---|---|---|
| `M15` | ITH/ITL khung chạy | nến xác nhận / từ nến sau | `eq_tol_atr` × ATR khung chạy |
| `H1`, `H4` | ITH/ITL khung lớn (§4.14) | `known_at` / từ nến sau | `eq_tol_atr` × ATR **khung lớn** lúc xác nhận, chỉ cùng tầng |
| `D`, `W` | PDH/PDL, PWH/PWL (§4.15) | `known_at` / từ nến sau | không gộp |

«Đã bị lấy trước khi biết»: duyệt các nến khung chạy từ **sau nến chạm cực trị** tới nến làm vùng được biết (gồm
cả nến đầu kỳ sau khi chốt muộn) — xuyên ≥ `min_pen_atr` × ATR\[j−1\] → không tạo vùng. Vùng chính của một sự kiện
LIQ / shift = tầng cao nhất (`TIER_RANK`: M15 < H1 < H4 < D < W), rồi mức xa nhất — như cũ. Vì vậy một nến quét
cùng lúc vùng M15 và PDH sinh **một** sự kiện, `tang` = D, nến sự kiện = nến lấy của vùng D.

### 4.17. [S5] Phản ứng ở FVG khung lớn → `pd_bias` (0.4.0)

`core/components/pd_array.PdArrayTracker` (plan §4.9, D6). Vùng = FVG H1/H4 hợp lệ (§4.14), hiệu lực từ nến khung
chạy **sau** nến làm nó được biết. Đo bằng nến khung chạy đã đóng:

* **tap** = nến đầu tiên giá chạm vùng (FVG tăng: `low ≤ hi`; giảm: `high ≥ lo`);
* từ nến tap trở đi (kể cả nến tap), kết quả **đầu tiên** được ghi; mỗi vùng một kết quả, sau đó «đã dùng»:

| `pd_respect_mode` | respect (FVG tăng; giảm đối xứng) | disrespect (FVG tăng; giảm đối xứng) |
|---|---|---|
| `strict` (mặc định) | `close ≥ hi + respect_away_atr × ATR[t−1]` | `close < lo` (vượt mép xa) |
| `loose` | `close > hi` | `close < lo` |
| `ce` | `close > hi` (như `loose` — đúng cách survey-v2 đo) | `close < (lo + hi)/2` |

Chạm đúng mép là chạm; respect chặt đúng bằng ngưỡng là respect; close đúng bằng mép xa / CE chưa là disrespect.
Sự kiện: `PD_RESPECT_UP/DOWN`, `PD_DISRESPECT_UP/DOWN` — **hậu tố = chiều FVG**, `direction` = chiều hàm ý; nến sự
kiện = nến xác nhận = t, giá = close\[t\], `reference_event_id` = `HTF_FVG_*` nguồn.

**`pd_bias`** = chiều hàm ý của kết quả gần nhất (H1 và H4 gộp): respect FVG tăng → +1, disrespect FVG tăng → −1;
FVG giảm ngược lại. Nhiều kết quả trong cùng nến: cùng chiều → chiều đó (khung nguồn = khung cao nhất); ngược chiều
→ **0** «mâu thuẫn trong cùng nến» (do lab chọn — §12). Chưa có kết quả nào → None. Không ghép với thứ tự hay DOL
(B3). IFVG (vùng bị disrespect đổi vai) để v0.2.

### 4.18. [S6] DOL (0.4.0)

`core/components/dol.DrawOnLiquidity` (plan §4.10, D7). Sau mỗi `SHIFT` ở nến d (bước 10):

* `side` = chiều shift; `target` = vùng **còn nguyên** gần close\[d\] nhất, nằm hẳn phía shift (tăng: mức >
  close\[d\]; giảm: mức < close\[d\]), tầng ≥ `dol_min_tier`. Vùng xét là vùng còn nguyên **sau bước [E2] của d**
  (vùng bị lấy ở d không tính; vùng mới biết ở d chỉ có hiệu lực từ d+1). Bằng khoảng cách → tầng cao hơn, rồi
  vùng tạo trước. Khoảng cách lúc đặt theo ATR\[d−1\] khung chạy;
* không có vùng nào phía đó → DOL **none** (`side = target = None`); DOL cũ vẫn bị thay.

Hết hiệu lực khi đích bị **lấy** (theo định nghĩa «lấy» duy nhất §4.9 — `DOL_REACHED` tại nến lấy, giá = mức đích,
`reference_event_id` = shift đặt DOL) hoặc khi có shift mới. «Tỷ lệ đạt DOL» là nhãn đánh giá nhìn về sau — không
phải đặc trưng hay đầu vào.

### 4.19. [T3] Ngữ cảnh khung lớn trong sự kiện và timeline (0.4.0)

Ở bước 12 của nến t, thuật toán chụp các giá trị (bất biến) của ngữ cảnh khung lớn **sau** t. Mọi sự kiện
**không phải `HTF_*`** và không phải sự kiện nguyên liệu (từ 0.4.1: STH/STL, FVG M15 + vòng đời, displacement) ở nến
t+1 mang `details.htf` dựng từ ảnh chụp đó (một ảnh chụp dùng chung cho mọi sự kiện
của nến; chỉ dựng khi nến có sự kiện), đúng khuôn plan §11.5:

```json
"htf": {
  "alignment": "ny_1700",
  "H1": {"ready": true, "order": 1, "order_age_bars": 7, "protected": 2318.4, "protected_broken": false,
         "zone": "discount", "range_pos": 0.31, "liq_above": 2341.0, "liq_below": 2309.2, "age_ltf_bars": 2,
         "coverage_last": 1.0, "blocked_windows_recent": 0},
  "H4": {"...": "cùng các trường như H1"},
  "pd_bias": {"dir": -1, "tf": "H1", "age_ltf_bars": 5},
  "dol": {"side": 1, "target": 2341.0, "tier": "H1", "dist_atr": 4.2},
  "levels": {"pdh": 2339.1, "pdl": 2301.7, "pdh_taken": false, "pdl_taken": true,
             "pwh": 2350.2, "pwl": 2290.0, "pwh_taken": false, "pwl_taken": false,
             "day_open": 2312.0, "midnight_open": null}
}
```

* `order_age_bars` = số nến **khung lớn** kể từ khi `order` nhận giá trị hiện tại; `age_ltf_bars` = số nến khung
  chạy kể từ lần chốt nến khung lớn gần nhất (`known_index`);
* `zone` / `range_pos` = close khung chạy so với dealing range của nến khung lớn **đã chốt** (công thức §4.6) —
  `range_pos` có thể < 0 hoặc > 1 khi giá đã ra ngoài từ lần chốt gần nhất;
* `liq_above` / `liq_below` = vùng còn nguyên gần nhất **cùng tầng** (H1 / H4); `dist_atr` của DOL = |đích −
  close| / ATR khung chạy hiện tại;
* `levels.*_taken` = vùng của mức đã bị lấy (hoặc không tạo vì đã bị lấy trước khi biết); `period_levels` tắt →
  None; khung không chạy (dataset > H1, H1 trên dataset H1) → khối của khung đó là None;
* không có trường «bias tổng hợp» (B3). Số trong ví dụ chỉ minh hoạ định dạng.

**Cột timeline phẳng** (trạng thái **sau** nến t = ảnh chụp mà sự kiện ở t+1 mang): `htf_H1_order`,
`htf_H4_order`, `htf_H4_zone`, `htf_H4_range_pos`, `htf_H4_age`, `pd_bias`, `dol_side`, `pdh_taken`,
`pdl_taken` (plan §11.5) và thêm `htf_H4_dealing_hi`, `htf_H4_dealing_lo`, `pd_bias_tf`, `dol_target`, `dol_tier`,
`dol_dist_atr` (plan §5.2).

### 4.20. [E4] Order block neo vào SHIFT (0.5.0)

Lab không có MSS (B1) nên mốc là nến d của SHIFT. Mô tả cho OB tăng (sau `SHIFT_UP`); OB giảm đối xứng.

1. **Ứng viên** (bước 6c của d): lùi từ d − 1 về `nến lấy − ob_lui` (nến lấy của ứng viên shift chính), dừng sau nến có
   khoảng trống ngay trước nó; nến giảm (`close < open`, doji không tính) gần d nhất là nến OB. `than_chuoi`: gộp cả
   chuỗi nến giảm liền trước nó, vùng = [close thấp nhất, open cao nhất] (chỉ thân); `nen_cuoi_rau`: chỉ nến đó,
   vùng = [low, high]. Không có nến giảm → không có ứng viên. Chuỗi nến đã thành OB trước đó (cùng nến đầu, nến cuối —
   hai SHIFT cùng chiều sát nhau) → dùng lại OB đó, không phát sự kiện mới (`trung_ob_da_co`; một cấu trúc một sự kiện).
2. **Xác nhận** (nghiên cứu ICT §3.4: «xác nhận khi giá vượt đầu xa của khối»): nến đầu tiên ≥ d có `high > mép trên`
   → `ORDER_BLOCK_UP` ở nến đó (nến sự kiện = nến OB gần d nhất, giá = mean threshold). Ứng viên bị bỏ (không phát sự
   kiện) khi `close < mép dưới` trước lúc xác nhận (xét trước điều kiện vượt, kể cả ở chính nến d), quá `ob_han`, hoặc có
   SHIFT ngược chiều.
3. **Vòng đời** (bước 3b, từ nến sau xác nhận): lần chạm đầu `low ≤ mép trên` → `OB_FAIL_UP` nếu `close < mép dưới`,
   không thì `OB_TAP_UP` (giá = mép trên); chưa chạm mà `t ≥ d + ob_han` → `OB_EXPIRED` (`OB_EXPIRED_TIME`); SHIFT
   ngược chiều → `OB_EXPIRED` (`OB_EXPIRED_OPPOSITE_SHIFT`). Một OB một kết cục.
4. **Neo displacement** (`ob_neo = displacement`, OB-D): mọi `DISPLACEMENT_UP` có close > high cao nhất của `ob_lui`
   nến trước (không vượt khoảng trống) là mốc; tìm trong [d − `ob_lui`, d − 1].

Trên XAUUSD M15 01–08/2024 (mặc định): 150 ứng viên (+2 lần SHIFT tìm lại OB đã có), 123 xác nhận (82%), 101 chạm,
9 hỏng, 13 hết hạn; từ xác nhận tới chạm trung vị 1 nến (nến sau displacement thường hồi vào khối). OB-R: 141 xác nhận;
OB-D: 706 (thêm 81 lần displacement liên tiếp tìm lại cùng chuỗi nến — trước khi gộp là 787).

### 4.21. [E6] OTE — vùng hồi của nhịp sau SHIFT (0.5.0)

Mô tả cho nhịp tăng (sau `SHIFT_UP` ở d); nhịp giảm đối xứng.

* Gốc X = cực trị cú quét của shift chính; đầu H = high\[d\], sau mỗi nến t (bước 12b) `H = max(H, high[t])` tới khi
  kết thúc — nến t chỉ dùng H của nến t − 1. L = H − X.
* Vùng = [H − `ote_den`·L, H − `ote_tu`·L], chỉ có hiệu lực khi L ≥ `ote_nhip_min_atr` × ATR\[t−1\]
  (`ote_nhip_min_atr = 0`: không lọc, không cần ATR).
* Bước 3b của t > d: `low[t] < X` → `OTE_FAIL_UP` (xét trước); vùng có hiệu lực và `low[t] ≤ H − ote_tu·L` →
  `OTE_ENTRY_UP`, độ sâu = (H − low\[t\]) / L ∈ \[`ote_tu`, 1\] (= 1 khi low chạm đúng X mà không thủng); chưa
  vào mà `t ≥ d + ote_han` → `OTE_EXPIRED`.
* Một nhịp chờ tại một thời điểm: SHIFT mới thay nhịp đang chờ → `OTE_EXPIRED` (`OTE_EXPIRED_SHIFT`; `ket_cuc` =
  `expired_shift` nếu ngược chiều, `replaced` nếu cùng chiều).
* `OTE_ENTRY_*` ghi OB cùng SHIFT (kể cả khi còn là ứng viên — `da_xac_nhan`; None khi không có hoặc ứng viên đã bị
  bỏ) và `ob_giao_vung` (OB giao vùng OTE — luật K25 của plan kết hợp).

Trên XAUUSD M15 01–08/2024: 152 nhịp, 105 vào vùng (69%), 21 hỏng, 26 hết hạn / bị thay; độ sâu khi vào trung vị 70%,
P90 87%.

## 5. Thời điểm biết

| Đầu ra | Nến sự kiện | Biết lúc |
|---|---|---|
| STH/STL | nến c (cực trị) | close nến `c + pivot_right` |
| ITH/ITL | nến của STH ở giữa | close nến xác nhận STH bên phải |
| LTH/LTL | nến của ITH ở giữa | close nến xác nhận ITH bên phải |
| `ICT_GAP` | nến đầu tiên sau khoảng trống | chính nến đó |
| `DISPLACEMENT_*` | t | close t |
| `FVG_UP/DOWN` | t−1 (nến giữa) | close t (nến 3) |
| `FVG_TOUCHED/FILLED` | nến chạm/lấp | chính nến đó |
| `LIQ_SWEEP_*` | nến lấy b (của vùng chính) | close r (nến quay lại), `r − b` = `sweep_bars` ≤ W |
| `LIQ_RUN_*` | nến lấy b | close b + W |
| `LIQ_UNRESOLVED` | nến lấy b | close nến đầu sau khoảng trống |
| `SHIFT_*` | d (nến displacement) | close d |
| `SHIFT_FVG_*` | d | close d + 1 |
| `ORDER_FLOW_*` | t = nến xác nhận của run (b + W) hoặc shift (d) kích hoạt — nến sự kiện = nến xác nhận | close t |
| `order`, mức được bảo vệ, dealing range, vùng gần nhất, `order_flow` (timeline) | — | trạng thái **sau** nến t; dùng để so từ t+1 |
| Nến H1/H4/D/W | — | `known_at`: close nến khung chạy có `close_time` ≥ `period_end`, hoặc (chốt muộn) close nến đầu của kỳ sau |
| `HTF_SWING_*` | nến khung chạy chạm cực trị của nến khung lớn ở giữa | `known_at` của nến khung lớn làm STH bên phải xác nhận |
| `HTF_FVG_*` | nến khung chạy đầu tiên của nến khung lớn ở giữa | `known_at` của nến khung lớn thứ ba |
| `HTF_PERIOD_*` (PDH/PDL, PWH/PWL) | nến khung chạy đạt high/low của kỳ | `known_at` của kỳ |
| `HTF_BAR_DEGRADED` | nến khung chạy đầu tiên của nến khung lớn | `known_at` của nến đó |
| Vùng H1/H4/D/W, vùng PD (FVG khung lớn) | — | biết ở `known_at`, **hiệu lực từ nến sau** |
| `PD_RESPECT_*` / `PD_DISRESPECT_*` | t (nến có close quyết định) | close t |
| `DOL_REACHED` | t (nến lấy đích) | close t |
| `details.htf` của sự kiện ở nến t | — | ngữ cảnh sau nến **t−1** (nến khung lớn đã chốt ≤ t−1) |
| cột timeline `htf_*`, `pd_bias`, `dol_*`, `pd*_taken` | — | trạng thái **sau** nến t (= `details.htf` của sự kiện ở t+1) |

## 6. Chỗ mơ hồ đã chọn

| Chỗ | Chọn | Ảnh hưởng |
|---|---|---|
| Hai đỉnh bằng giá | Strict — không phải pivot (D15); EQH chỉ ở tầng so sánh, theo dung sai | Nhất quán với `swing_pivot`; biến thể không strict để sau |
| ATR chưa đủ nến khi so hai swing | **Chưa so** (`hh`/`hl` = None, «ATR chưa đủ nến») — không ép dung sai 0 | Chỉ đầu dataset/khoảng chạy. Survey-v2 dùng dung sai 0 khi chưa có ATR |
| Close đúng bằng mức được bảo vệ / mức bị quét | Không tính là vượt / chưa quay lại | — |
| Mức được bảo vệ đổi sang swing khác cùng giá | Xoá cờ vượt (mức mới) | Survey-v2 so theo giá nên giữ cờ khi cùng giá — hiếm |
| ATR qua khoảng trống | Không reset; TR nối qua khoảng trống gồm bước nhảy | Khác `dc_atr_structure` (reset mỗi segment) — vì mức được giữ qua khoảng trống |
| Nến nằm ngoài giờ phiên (vd dữ liệu mô phỏng 24/7) | Không chặn gì; chỉ đếm và cảnh báo khi > 20% số nến | Số «mỗi ngày» kém tin cậy với dữ liệu không theo lịch |
| Tỷ lệ thời gian (thứ tự, mức bị vượt) | Đếm trạng thái **sau** mỗi nến (như timeline) | Survey-v2 đếm trước khi áp swing xác nhận ở nến đó: «mức bị vượt / tổng nến» 0.120 so với 0.107 ở đây — cùng logic, đã kiểm (§8) |
| Nguồn vùng thanh khoản khi `structure_level` ≠ 2 | Vẫn là ITH/ITL | Vùng không đổi theo cấp cấu trúc; STH quá dày để làm vùng |
| Gộp EQH/EQL | Có (dung sai `eq_tol_atr`), chỉ giữa hai swing liên tiếp | Survey-v2 **không** gộp: ít vùng hơn ~5%; `eq_tol_atr = 0` tái lập survey (§8) |
| Kiểm «đã bị lấy trước khi biết» | Dùng ATR\[j−1\] của từng nến j trong (cực trị, nến xác nhận]; chạm nông trong khoảng đó không đếm | Khớp survey (13 vùng M15) |
| Một nến lấy nhiều vùng | Một ứng viên shift **mỗi vùng** (mức, X riêng); gom ở d | Vùng chính quyết định `reference`/`group_id`; mọi vùng nằm trong `swept` |
| Hướng của sweep/run | `LIQ_SWEEP_BSL` hướng `down`, `LIQ_SWEEP_SSL` `up`; `LIQ_RUN_UP` `up`, `LIQ_RUN_DOWN` `down` | Hướng = phía giá được kỳ vọng sau sự kiện, chỉ để hiển thị |
| `event_id` trùng nến | `LIQ_UNRESOLVED` thêm hậu tố `:BSL`/`:SSL`; `FVG_TOUCHED/FILLED` thêm `:<nến giữa FVG><U/D>` | Duy nhất trong run |
| Vòng đời FVG thành sự kiện | Có (plan §4.4, §5.1) | Khối lượng: ~45% số sự kiện trên M15 (§8). Chế độ Gọn chỉ vẽ FVG của shift; hộp FVG + vòng đời ở Chi tiết (§11) |
| Order flow: đầu vào | Chỉ run + shift đã xác nhận (OF1); sweep, FVG, displacement, HH/HL không dùng | ICT: sweep phía ngược trong order flow là stop run (§4.12); nghiên cứu §5: không cách đọc nào dự báo tốt hơn |
| Order flow: sự kiện cùng chiều | Không đổi gì, không phát sự kiện; chỉ ghi `ung_ho_gan_nhat` (`pending_state`) | Số `ORDER_FLOW_*` = số lần trạng thái đổi giá trị |
| Order flow: nến sự kiện | = nến xác nhận t; giá = close\[t\] | Khác `LIQ_RUN_*` (nến sự kiện = nến lấy b): trên chart `ORDER_FLOW_*` do run nằm sau `LIQ_RUN_*` W nến |
| Order flow: run trễ | Đổi ở nến xác nhận run (b + W), không phải nến lấy b | Trễ W = 3 nến so với lúc lấy; shift không trễ (đổi ngay ở nến displacement d) |
| Order flow: hai chiều cùng nến | Chưa rõ (`hai_chieu_cung_nen`); không có sự kiện kích hoạt (`reference_event_id` = None), `basis` liệt kê đủ | ~3% số lần vào «chưa rõ» (nghiên cứu §8.3) |
| Order flow: `None` khác `0` | `None` = chưa có run/shift nào từ đầu run (khởi động); `0` = chưa rõ. `None` → `0` cũng là một lần đổi (phát `ORDER_FLOW_UNCLEAR`) | `run_stats` tách «chưa có» khỏi «chưa rõ»; khảo sát `describe()` gộp hai thứ (§8.1) |
| Order flow: shift cùng chiều | Không đổi (vd đang tăng gặp `SHIFT_UP`) | Không phát sự kiện, giữ `order_flow_since` |
| Order flow: «hai phía đều bị run trong N nến» | Không cài (OF2 bỏ quy tắc B) | Thêm < 0.1 đoạn chưa rõ mỗi ngày ở M15 (nghiên cứu §8.2) |
| Order flow: vùng | 0.3.0: chỉ ITH/ITL của khung đang chạy; từ 0.4.0: mọi tầng (M15, H1, H4, D, W) | 0.4.0 thêm run/shift từ vùng khung lớn → order flow đổi ở 0.6–1.2% số nến (§8.2) |
| Mốc đóng kỳ khung lớn `period_end` | Mốc đóng của ô mở cuối cùng theo **lịch khai báo** (không phải mốc danh nghĩa) | Ngày đóng sớm, tuần có Good Friday chốt **đúng giờ** thay vì chờ phiên sau như survey-v2 (D: 1 lần chốt muộn thay vì 6 — §8.2) |
| Nến khung chạy nằm sau mốc đóng theo lịch | Kỳ «nối tiếp» riêng, `degraded` (`ngoai_lich`) | Không dựng cấu trúc từ vài nến lẻ; XAUUSD 2018–2023: 2 H4, 11 D, 2 W (§8.2) |
| Pivot khung lớn qua nghỉ phiên / cuối tuần | **Không** chặn; chỉ chặn nến degraded và hole (plan §11.4) | Khác khung chạy (D1). Khớp survey-v2: 2 cửa sổ H1 / 2 cửa sổ H4 bị chặn trong 8 tháng |
| FVG khung lớn «liền kề theo lịch» | Nến sau mở đúng lúc nến trước **đóng theo lịch** | H4 qua ngày thường liền kề (giờ nghỉ nằm trong nến 17–21 NY); qua cuối tuần, đóng sớm, ngày lễ, hole thì không; H1 qua giờ nghỉ thì không |
| `protected_broken` khung lớn | Theo close **nến khung lớn đã chốt** | Survey-v2 đo bằng close M15 — số «±1 nhưng mức bị vượt» không so trực tiếp |
| `zone` / `range_pos` khung lớn | Close khung chạy so với dealing range khung lớn đã chốt | `range_pos` có thể < 0 hoặc > 1 khi giá đã ra ngoài từ lần chốt gần nhất |
| Gộp EQH/EQL vùng khung lớn | H1/H4: dung sai × ATR **khung lớn**, chỉ cùng tầng; D/W: không gộp | PDH/PDL không phải ITH/ITL (plan chỉ nói gộp ITH/ITL); survey-v2 không gộp ở tầng nào |
| `pd_bias` khi nhiều kết quả cùng nến | Cùng chiều → chiều đó (khung cao nhất); ngược chiều → 0 | Hiếm: 0.1% thời gian ở XAUUSD M15 01–08/2024; survey-v2 chọn tuỳ thứ tự sắp |
| Respect ở chế độ `ce` | Như `loose` (close ra ngoài mép gần) | Đúng cách survey-v2 đo; plan chỉ định nghĩa disrespect của CE |
| DOL khi không có vùng phía shift | DOL none (`side` = None), DOL cũ vẫn bị thay | Như survey-v2 |
| Giá mở ngày khi thiếu nến đầu ngày | None (chỉ nhận nến mở đúng ô mở đầu tiên theo lịch) | Giống quy tắc midnight open; plan không nói rõ |
| Khung không chạy được | `htf_list` khung ≤ khung dataset bị bỏ qua; dataset > H1 → tắt [T] | Chạy mặc định trên dataset H1 vẫn được (chỉ H4, D, W), không lỗi |
| Tầng của ITH/ITL khung chạy | Vẫn ghi `M15` (= khung chạy) kể cả dataset M5/H1 | Giữ nhãn cũ để không đổi output; xếp hạng tầng vẫn đúng (khung chạy thấp nhất) |

## 7. Sự kiện và trường dữ liệu

| Loại | Lý do | `details` chính |
|---|---|---|
| `SWING_HIGH` / `SWING_LOW` (STH/STL) | `PIVOT_HIGH_STRICT` / `PIVOT_LOW_STRICT` | `cap`=1, `trai`/`phai`, `chan_cua_so_qua_gap` |
| `SWING_HIGH_L2` / `SWING_LOW_L2` (ITH/ITL) | `PIVOT_HIGH_L2` / `PIVOT_LOW_L2` | `basis` (3 STH), giá/nến của ba swing; nếu là cấp cấu trúc: `so_sanh`, `nhan` (HH/LH/EQH, HL/LL/EQL), `gia_truoc`, `chenh_lech`, `dung_sai`, `atr_luc_xac_nhan`, `order_sau`, `muc_bao_ve_sau`; `vung_thanh_khoan` (`trang_thai` tao_moi / gop_eq / khong_tao, `vung`, `muc_vung`, `hieu_luc_tu_nen`, `ly_do_vi`) |
| `SWING_HIGH_L3` / `SWING_LOW_L3` (LTH/LTL) | `PIVOT_HIGH_L3` / `PIVOT_LOW_L3` | như cấp 2, `basis` = 3 ITH/ITL |
| `ICT_GAP` | `GAP_NGHI_PHIEN` / `GAP_CUOI_TUAN` / `GAP_NGHI_LE` / `GAP_THIEU_TRONG_PHIEN` / `GAP_NGOAI_LICH` / `GAP_KHONG_RO_LICH` | `loai`, `bat_thuong`, `tu`, `den`, `so_o_thieu`, `so_o_trong_phien`, `lich_phien`, `chinh_sach` |
| `DISPLACEMENT_UP/DOWN` | `DISP_RANGE_BODY` | `bien_do_atr`, `than_ty_le`, `atr`, `nguong_vi` |
| `FVG_UP/DOWN` | `FVG_THREE_BAR` | `lo`, `hi`, `kich_thuoc`, `kich_thuoc_atr`, `from_displacement`, `nen_1`/`nen_giua`/`nen_3` |
| `FVG_TOUCHED` / `FVG_FILLED` | `FVG_FIRST_TOUCH` / `FVG_FULL_FILL` | `fvg` (id), `chieu_fvg`, `lo`, `hi`, `nen_giua_fvg`, `so_nen_tu_khi_biet`, `cham_tai_nen` |
| `LIQ_SWEEP_BSL/SSL` | `LIQ_TAKEN_THEN_CLOSE_BACK` | `phia`, `tang`, `muc`, `vung`, `nen_lay`, `atr_khoa`, `xuyen_atr`, `cuc_tri_cu_quet`, `sweep_bars`, `cung_nen_lay`, `cua_so`, `so_vung`, `pools`, `group_id` |
| `LIQ_RUN_UP/DOWN` | `LIQ_TAKEN_NO_RETURN` | như sweep (không `sweep_bars`/`group_id`), `so_nen_sau_lay` |
| `LIQ_UNRESOLVED` | `LIQ_GAP_IN_WINDOW` | như sweep, `loai_khoang_trong` |
| `SHIFT_UP/DOWN` | `SHIFT_SWEEP_THEN_DISPLACEMENT` | `chieu`, `tang`, `group_id`, `muc_bi_quet`, `cuc_tri_cu_quet`, `nen_sweep`, `so_nen_tu_sweep`, `displacement_tren_nen_lay`, `cung_nen_sweep`, `cua_so`, `swept`, `displacement`, `basis` |
| `SHIFT_FVG_UP/DOWN` | `SHIFT_FVG_SAME_DISPLACEMENT` | `shift`, `group_id`, `tang`, `fvg`, `lo`, `hi`, `nen_displacement` |
| `ORDER_FLOW_UP` / `ORDER_FLOW_DOWN` (hướng `up` / `down`) | `OF_RUN` / `OF_SHIFT` | `tu`, `sang` (giá trị cũ / mới: 1, −1, 0, None), `tu_vi`, `sang_vi`, `ly_do` (`run_tang`, `run_giam`, `shift_tang`, `shift_giam`), `ly_do_vi`, `basis` (id mọi run/shift ở t, theo thứ tự phát), `trang_thai_cu_tu_nen` (nến bắt đầu trạng thái cũ; None khi cũ là `None`), `trang_thai_cu_so_nen` (t − nến đó; None khi cũ là `None`) |
| `ORDER_FLOW_UNCLEAR` (hướng None) | `OF_OPPOSITE_RUN` / `OF_BOTH_SIDES` | như trên; `ly_do` = `run_nguoc_chieu` / `hai_chieu_cung_nen` |
| `HTF_SWING_HIGH/LOW` (0.4.0, ẩn) | `HTF_PIVOT_HIGH_L2` / `HTF_PIVOT_LOW_L2` | `khung`, `cap`=2, `ten`, `nen_htf` (+ `_trai`, `_phai`, `_xac_nhan`), `gia_trai`/`gia_phai`, `mo_nen_htf`, `atr_khung`, so sánh (`so_sanh`, `nhan`, `order_sau`, `muc_bao_ve_sau`…), `period_end`, `known_at`, `chot_muon`, `coverage`, `n_bars`, `expected_bars`, `vung_thanh_khoan` (tầng H1/H4) |
| `HTF_FVG_UP/DOWN` (0.4.0, ẩn) | `HTF_FVG_THREE_BAR` | `khung`, `lo`, `hi`, `ce`, `kich_thuoc`, `kich_thuoc_atr`, `atr_khung`, `from_displacement`, `nen_htf_1`/`_giua`/`_3`, `nen_giua_tu`/`_den` (nến khung chạy), `mo_nen_giua`, `hieu_luc_tu_nen`, `period_end`, `known_at`, `coverage` |
| `HTF_PERIOD_HIGH/LOW` (0.4.0, ẩn) | `HTF_PERIOD_LEVEL` | `khung` (D/W), `ten` (PDH/PDL/PWH/PWL), `muc`, `mo_ky`, `nen_htf`, `period_end`, `known_at`, `chot_muon`, `coverage`, `vung_thanh_khoan` (tầng D/W) |
| `HTF_BAR_DEGRADED` (0.4.0, ẩn) | `HTF_COVERAGE_LOW` / `HTF_FIRST_PERIOD_PARTIAL` / `HTF_OUTSIDE_CALENDAR` | toàn bộ `HtfBar.brief()` (khung, mở, `period_end`, `known_at`, OHLC, `n_bars`, `expected_bars`, `coverage`, cờ), `nguong_coverage`, `he_qua_vi` |
| `PD_RESPECT_UP/DOWN`, `PD_DISRESPECT_UP/DOWN` (0.4.0; hậu tố = chiều FVG, hướng = chiều hàm ý) | `PD_RESPECT_STRICT` / `PD_RESPECT_LOOSE` / `PD_DISRESPECT_FAR_EDGE` / `PD_DISRESPECT_CE` | `khung`, `fvg` (id `HTF_FVG_*`), `chieu_fvg`, `lo`, `hi`, `ce`, `from_displacement`, `ket_qua`, `che_do`, `mep`, `khoang_cach_yeu_cau`, `atr`, `quy_tac_vi`, `close`, `nen_cham`, `so_nen_tu_khi_biet`, `so_nen_tu_cham`, `chieu_ham_y`, `pd_bias_sau`, `pd_bias_khung` |
| `DOL_REACHED` (0.4.0) | `DOL_TARGET_TAKEN` | `chieu_dol`, `vung` (bản tóm tắt vùng đích), `muc`, `tang`, `phia`, `shift`, `nen_dat_dol`, `so_nen_tu_shift`, `khoang_cach_atr_luc_dat`, `xuyen_atr`, `basis` (shift + nguồn vùng) |
| `ORDER_BLOCK_UP/DOWN` (0.5.0; nến sự kiện = nến OB gần d nhất, nến xác nhận = nến vượt đầu xa) | `OB_BODY_RUN` / `OB_LAST_CANDLE_WICK` | `chieu`, `lo`, `hi`, `mean_threshold`, `kich_thuoc_atr`, `nen_dau`, `nen_cuoi`, `so_nen`, `bien_the`, `neo`, `nen_neo` (d), `nen_xac_nhan`, `han_nen`, `basis` (SHIFT / displacement) |
| `OB_TAP_UP/DOWN`, `OB_FAIL_UP/DOWN` (0.5.0) | `OB_FIRST_TAP` / `OB_CLOSE_BEYOND_FAR_EDGE` | `ob` (id), `chieu_ob`, `lo`, `hi`, `mean_threshold`, `nen_dau`, `nen_neo`, `so_nen_tu_tao`, `ket_cuc`, `ket_cuc_vi`, `close`, `close_qua_mean_threshold`, `atr` |
| `OB_EXPIRED` (0.5.0, hướng = chiều OB, không mang `details.htf`) | `OB_EXPIRED_TIME` / `OB_EXPIRED_OPPOSITE_SHIFT` | như trên, không có `close` |
| `OTE_ENTRY_UP/DOWN`, `OTE_FAIL_UP/DOWN` (0.5.0) | `OTE_RETRACE_ZONE` / `OTE_LEG_BROKEN` | `chieu`, `x`, `h`, `nhip`, `vung_lo`, `vung_hi`, `diem_ngot`, `nen_neo`, `shift`, `han_nen`, `ket_cuc`, `ket_cuc_vi`, `so_nen_tu_shift`, `nhip_atr`, `nhip_toi_thieu_atr`, `basis`; vào vùng thêm `do_sau`, `ob` (`id` — None khi còn ứng viên, `lo`, `hi`, `da_xac_nhan`, `nen_xac_nhan`), `ob_giao_vung` |
| `OTE_EXPIRED` (0.5.0, không mang `details.htf`) | `OTE_EXPIRED_TIME` / `OTE_EXPIRED_SHIFT` | như trên; `ket_cuc` = `expired_time` / `expired_shift` / `replaced` |

Mọi sự kiện có `details.killzone`; mọi sự kiện không phải `HTF_*` và không phải sự kiện nguyên liệu (STH/STL, FVG M15 + vòng
đời, displacement — 0.4.1) có `details.htf` (§4.19). `event_id`:
`ict:<loại>@<nến sự kiện>><nến xác nhận>` (hậu tố ở §6); khoảng trống `ict:ICT_GAP@<nến>`; order flow
`ict:ORDER_FLOW_UP@t>t` (nến sự kiện = nến xác nhận, giá = close\[t\]); khung lớn thêm hậu tố khung
(`ict:HTF_SWING_HIGH@a>b:H4`, `…:D`); PD thêm `:<khung>.<nến giữa>` (`ict:PD_RESPECT_UP@t>t:H1.1234`). Một sự kiện cho một cấu trúc — nhãn HH/LH… nằm trong `details` (AGENTS §5.1).
`reference_event_id`: swing → swing giữa cấp dưới; sweep/run → nguồn của vùng chính (ITH/ITL, `HTF_SWING_*` hay
`HTF_PERIOD_*`); shift → sweep chính; `SHIFT_FVG` → shift; vòng đời FVG → FVG; order flow → shift kích hoạt, không
có thì run (`hai_chieu_cung_nen` → None); `PD_*` → `HTF_FVG_*` (None khi `htf_events = khong_phat`); `DOL_REACHED`
→ shift đặt DOL. `HTF_*` không có tham chiếu.

**Chấm (trang Đánh giá):** ITH/ITL dùng chung loại với `swing_hierarchy` → mục tiêu **Swing cấu trúc
(cấp 2)**. Shift → mục tiêu **`ict_shift`** (nhãn `SHIFT_UP/DOWN` đặt ở nến displacement, giá = close;
phía «đỉnh» = `SHIFT_DOWN`). Sweep → shift → shift_fvg là **một cơ hội**: mặc định chấm `SHIFT_*`; chấm
tầng có FVG bằng `event_type_map` `SHIFT_FVG_UP → SHIFT_UP`, `SHIFT_FVG_DOWN → SHIFT_DOWN` — không đếm
cả hai tầng. `ORDER_FLOW_*` không có mục tiêu chấm, không có loại nhãn (mô tả, không phải dự báo — §4.12).
`HTF_*`, `PD_*`, `DOL_REACHED` (0.4.0) cũng không có mục tiêu chấm, không có loại nhãn, không nằm trong
`event_type_map` mặc định — không đếm trùng khi chấm M15 (D12).

**Timeline** mỗi nến: `order`, `protected`, `protected_side`, `protected_id`, `protected_broken`,
`dealing_hi`, `dealing_lo`, `dealing_eq`, `dealing_id`, `zone`, `range_pos`, `atr`, `gap`; giai đoạn 2:
`killzone`, `liq_above` / `liq_above_id` (BSL còn nguyên gần nhất), `liq_below` / `liq_below_id`,
`pending_takes`, `pending_shifts`, `last_sweep` (+ `last_sweep_bars`), `last_shift` (+ `last_shift_bars`,
`last_shift_fvg`), `open_fvg_up` / `open_fvg_down`, `displacement`; 0.3.0: `order_flow` (1 / −1 / 0 / None,
sau nến t), `order_flow_since` (nến bắt đầu giá trị hiện tại; None khi `None`), `order_flow_reason` (mã lý
do ở §4.12 hoặc None); 0.4.0: 15 cột khung lớn ở §4.19 (`htf_H1_order`, `htf_H4_order`, `htf_H4_zone`,
`htf_H4_range_pos`, `htf_H4_age`, `htf_H4_dealing_hi`, `htf_H4_dealing_lo`, `pd_bias`, `pd_bias_tf`, `dol_side`,
`dol_target`, `dol_tier`, `dol_dist_atr`, `pdh_taken`, `pdl_taken`); 0.5.0: `ob_up_hi` / `ob_up_lo` (OB tăng đã xác
nhận còn mở, gần close nhất — cùng thứ tự với `pending_state.order_block`), `ob_down_hi` / `ob_down_lo`, `ote_dir`,
`ote_neo` (nến SHIFT mở nhịp), `ote_x`, `ote_h`, `ote_lo` / `ote_hi` (vùng sẽ xét ở nến t+1; None khi nhịp chưa đủ lớn). Khoá cũ giữ nguyên tên; giá trị `liq_above` /
`liq_below` / `pending_takes` / `order_flow` có thể khác 0.3.0 vì có vùng khung lớn (§8.2).

**`pending_state["order_flow"]`** (bản sao, không trả tham chiếu nội bộ): `trang_thai`, `trang_thai_vi`
(tăng / giảm / chưa rõ / chưa có), `tu_nen`, `so_nen` (nến cuối − `tu_nen`), `ly_do`, `ly_do_vi`,
`su_kien` (id run/shift **kích hoạt** trạng thái hiện tại — không phải id `ORDER_FLOW_*`; None khi
`hai_chieu_cung_nen` hoặc chưa có), `ung_ho_gan_nhat` (`nen`, `su_kien`, `loai` run/shift — sự kiện cùng
chiều gần nhất kể từ lần đổi, §4.12 bước 3; None sau mỗi lần đổi), `vung_cung_chieu` / `vung_nguoc_chieu`
(§4.12; chưa rõ, chưa có → None), `dieu_kien_vi` (điều gì sẽ đổi trạng thái — khi tăng: «Run vùng phía
dưới (SSL) → chưa rõ», «Shift giảm (quét BSL rồi displacement giảm) → giảm», «Run/shift hai chiều trong
cùng một nến → chưa rõ»; giảm đối xứng; khi chưa rõ: «Run hoặc shift kế tiếp đặt chiều (lên → tăng, xuống
→ giảm)»; khi chưa có: «Run hoặc shift đầu tiên đặt chiều»).

**`pending_state` (0.4.0, bản sao):** `giai_doan` = 3; `khung_lon`: `bat`, `moc`, `khung`, `khung_bo_qua`,
`ngu_canh` (đúng `details.htf` mà sự kiện ở nến kế tiếp sẽ mang), `H1` / `H4` (`ready`, `atr`, `so_nen_da_chot`,
`cau_truc` = snapshot thứ tự + mức được bảo vệ, `dealing_range` theo close hiện tại, `nen_chot_gan_nhat` =
`HtfBar.brief()`, `dang_hinh_thanh` = nến đang hình thành — **chỉ để vẽ**, có `ghi_chu_vi`; `vung_gan_nhat`
BSL/SSL cùng tầng, `fvg_dang_mo_gan_nhat` ≤ 3 vùng PD còn mở gần giá nhất mỗi chiều, `so_fvg_dang_mo`,
`cua_so_bi_chan_gan_day`), `D` / `W` (`nen_chot_gan_nhat`, `dang_hinh_thanh`), `muc_theo_ky` (`levels` + kỳ D/W
gần nhất, vùng của mức, `day_open_nen`, `midnight_open_nen`); `pd` (`pd_bias`, `pd_bias_vi`, `khung`, `tu_nen`,
`so_nen`, `su_kien`, `che_do`, `respect_away_atr`); `dol` (`side`, `target`, `tier`, `dist_atr`, `vung`, `shift`,
`tu_nen`, `so_nen`, `khoang_cach_atr_luc_dat`, `tang_toi_thieu`). 0.5.0: `order_block` (`bien_the`, `neo`, `dang_mo`
≤ 3 OB đã xác nhận gần giá nhất mỗi chiều kèm `con_lai_nen`, `can`; `so_dang_mo`), `ote` (`tu`, `den`,
`nhip_toi_thieu_atr`, `dang_cho`: nhịp đang chờ + vùng, `vung_hieu_luc`, `nhip_atr`, `ob`, `can`).

**`run_stats` (0.4.0):** `giai_doan` = 3; `thanh_khoan.tang` = các tầng có vùng (vd `M15+H1+H4+D+W`),
`thanh_khoan.theo_tang` (tạo, gộp EQ, không tạo, bị lấy, sweep, run, chưa rõ mỗi tầng); `khung_lon` (`theo_khung`
H1/H4: nến chốt, `degraded`, `after_hole`, `over`, `ngoai_lich`, `chot_muon` + giờ lớn nhất, cửa sổ pivot bị chặn,
ITH/ITL, FVG, tỷ lệ thời gian `order` và `ready`; `ky` D/W: kỳ chốt, degraded không tạo mức, chốt muộn; `gia_mo_ngay`;
`nen_degraded` ≤ 50 dòng); `pd_array` (`theo_khung`: vùng, từ displacement, chạm, respect, disrespect; số sự kiện,
vùng còn mở, số lần và tỷ lệ thời gian `pd_bias`); `dol` (shift, có đích, không có vùng, đạt, bị thay, khoảng cách
TV/P25/P90 theo ATR, tầng đích, tỷ lệ thời gian). 0.5.0: `order_block` (ứng viên, trùng OB đã có, xác nhận + tỷ lệ, bỏ trước xác
nhận, chạm, hỏng, hết hạn theo thời gian / SHIFT, tỷ lệ chạm, hỏng khi chạm, nến tới chạm trung vị), `ote` (nhịp,
vào, hỏng, hết hạn, bị thay, tỷ lệ vào, độ sâu TV / P90).

**`run_stats["order_flow"]`:** `ty_le_thoi_gian` (`tang`, `giam`, `chua_ro`, `chua_co`; trên mọi nến, tổng
= 1), `doi_trang_thai` (số `ORDER_FLOW_*`), `doi_chieu` + `doi_chieu_moi_ngay` (đổi chiều thật: một đoạn ±1
khác chiều đoạn ±1 liền trước, có thể qua chưa rõ), `doan_chua_ro` + `doan_chua_ro_moi_ngay`,
`chua_ro_trung_vi_nen` / `_gio`, `mot_chieu_trung_vi_nen` / `_gio`, `theo_ly_do` (luôn đủ 6 mã),
`ghi_chu_vi`. Đoạn = dãy nến liên tiếp cùng giá trị; bỏ đoạn `None` đầu run; tính cả đoạn cuối đang mở.
Ngày = `so_ngay_giao_dich`. Trung vị nội suy (`_quantile`), None khi không có đoạn nào; giờ = số nến × độ
dài khung.

## 8. Đối chiếu survey-v2 (đoạn phát triển 01/01–31/08/2024, XAUUSD M15 `ds_db1583cd4dde`)

Survey là bản mẫu định nghĩa, không phải chuẩn đúng (plan §10). Số survey lấy từ
`docs/research/khao_sat/ict_survey_dev.json`. Chạy lại bằng lõi (05/10/2026):

| Đo | Survey-v2 | `ict_structure` 0.2.0 |
|---|---:|---:|
| Số nến / ngày giao dịch | 15 850 / 173 | 15 850 / 173 |
| Khoảng trống nghỉ phiên / cuối tuần / lễ / thiếu trong phiên | 133 / 32 / 6 / 1 | 133 / 32 / 6 / 1 (thiếu: 12/01/2024, 16 ô) |
| STH + STL mỗi ngày | 40.4 | 40.4 |
| ITH + ITL mỗi ngày (chặn gap) | 10.2 | 10.22 |
| Thứ tự +1 / −1 / lẫn lộn / chưa có | 30.0% / 22.1% / 47.7% / 0.2% | 30.0% / 22.1% / 47.7% / 0.2% |
| Đang ±1 nhưng mức được bảo vệ đã bị close vượt (/ tổng nến) | 12.0% | 10.7% (đếm sau nến); 12.0% khi đếm như survey (§6) |
| Displacement: tỷ lệ nến / mỗi ngày | 7.36% / 6.75 | 7.36% / 6.75 |
| FVG mỗi ngày / nến giữa là displacement / bị loại vì khoảng trống | 18.14 / 26% / 86 | 18.14 / 26.0% / 86 |
| Vùng M15 (ITH + ITL) / không tạo vì đã bị lấy | 1755 / 13 | 1675 vùng + 80 lần gộp EQ = 1755 / 13 |
| Bị lấy / chạm nông trước khi lấy | 1661 / 243 | 1583 / 229 (gộp EQ); **1660 / 241** khi `eq_tol_atr = 0` |
| Xuyên khi lấy × ATR — trung vị (P90) | 0.563 (1.932) | 0.564 (1.900); **0.563 (1.933)** khi `eq_tol_atr = 0` |
| W = 3: sweep / run / chưa rõ (theo vùng) | 1168 / 485 / 8 | 1113 / 462 / 8; **1167 / 485 / 8** khi `eq_tol_atr = 0` |
| W = 0: sweep / run (theo vùng) | 684 / 977 | **684 / 976** khi `eq_tol_atr = 0` |
| Shift W = 0: số / có FVG / displacement ngay nến lấy / NY AM | 55 / 56.4% / 14.5% / 40.0% | **55 / 56.4% / 14.5% / 40.0%** |
| Shift W = 3: số / có FVG / displacement ngay nến lấy / NY AM | 153 / 54.9% / 4.6% / 36.6% | 151 / 55.0% / 5.3% / 37.1% (0.87/ngày) |
| Killzone theo tỷ lệ nến: Asia / London / NY AM | 17.5% / 13.1% / 13.1% | 17.5% / 13.1% / 13.1% (London close 8.7%) |

**Sai lệch và giải thích:**

* **Gộp EQH/EQL** (lab có, survey không): bớt 80 vùng, nên số «bị lấy», «chạm», sweep/run thấp hơn
  ~5%. Đặt `eq_tol_atr = 0` (chỉ gộp mức **bằng hệt**, 2 lần) thì khớp survey tới 1 vùng.
* **Shift W = 3: 151–152 so với 153.** Survey có vùng mọi tầng (M15, H1, D, W); giai đoạn 2 chỉ có M15.
  Survey xếp shift theo tầng **cao nhất** bị quét (M15 96 · H1 26 · D 26 · W 5), nhưng gần như mọi shift
  đó đều quét cả một vùng M15 cùng nhịp — chỉ ~1 shift đến từ vùng tầng cao mà không có vùng M15. Phần
  còn thiếu sẽ có khi thêm vùng khung lớn (giai đoạn 3). W = 0 khớp tuyệt đối.
* **«Displacement ngay nến quét»** của survey là d = **b** (nến lấy). Lab ghi cả hai:
  `displacement_tren_nen_lay` (d = b: 8/151) và `cung_nen_sweep` (d = r: 86/151 — thường gặp vì nến
  displacement vượt lại mức cũng chính là nến làm sweep).
* Bảng ở plan §2.3 ghi FVG bị loại là 88; file kết quả survey ghi **86** — lab khớp file kết quả.

Hiệu năng (một luồng, Python): M15 2018–2025 (189 073 nến) 5.7 s, 251 450 sự kiện; M1 2024 (355 652 nến)
14.0 s, 537 151 sự kiện — tuyến tính theo số nến. Cơ cấu sự kiện M15 8 năm: swing + khoảng trống
105 929 (42%), FVG + chạm + lấp 112 667 (45%), displacement 13 919, sweep/run/chưa rõ 16 125, shift 1 786
(0.86/ngày), SHIFT_FVG 1 024.

### 8.1. Order flow (0.3.0): đối chiếu khảo sát quy tắc A

Số khảo sát lấy từ [`khao_sat/orderflow_rules_dev.json`](../research/khao_sat/orderflow_rules_dev.json)
(`research/orderflow_rules.py`, quy tắc A, trên sự kiện run/shift của 0.2.0 — 0.3.0 không đổi hai loại này;
nghiên cứu §8). Cột 0.3.0 lấy từ `run_stats["order_flow"]` khi chạy lõi với tham số mặc định trên đúng
khoảng đó. «Mỗi ngày» = mỗi ngày giao dịch (`so_ngay_giao_dich`). Hai chỗ khác định nghĩa đã biết trước:

* khảo sát gộp «chưa có» (khởi động) vào «chưa rõ»; 0.3.0 tách hai thứ → so với tổng «chưa rõ + chưa có»;
* trung vị: khảo sát lấy phần tử giữa (`xs[len // 2]`), 0.3.0 nội suy (`_quantile`) → có thể lệch tới
  ~0.1 giờ.

Mọi số khác phải khớp.

| Dữ liệu | Đo | Khảo sát (quy tắc A) | `ict_structure` 0.3.0 |
|---|---|---:|---:|
| XAUUSD M15 `ds_db1583cd4dde` 01/01–31/08/2024 | tăng / giảm / chưa rõ + chưa có (% thời gian) | 46.1 / 29.8 / 24.1 | 46.1 / 29.8 / 24.1 (23.9 + 0.3) — khớp |
| | đổi chiều · đoạn chưa rõ (mỗi ngày) | 0.72 · 0.64 | 0.72 · 0.64 — khớp |
| | trung vị giờ: chưa rõ · một chiều | 6.2 · 13.2 | 6.1 · 13.1 (nội suy 24.5 / 52.5 nến) |
| XAUUSD M15 `ds_a5212fd37814` 01/01/2018–31/12/2023 | tăng / giảm / chưa rõ + chưa có (% thời gian) | 40.8 / 37.2 / 21.9 | 40.8 / 37.2 / 21.9 (21.9 + 0.0) — khớp |
| | đổi chiều · đoạn chưa rõ (mỗi ngày) | 0.77 · 0.62 | 0.77 · 0.62 — khớp |
| | trung vị giờ: chưa rõ · một chiều | 5.8 · 13.0 | 5.75 · 13.0 — khớp (làm tròn) |
| EURUSD M15 `ds_a9a2a5e4cef5` 01/01/2018–31/12/2023 | tăng / giảm / chưa rõ + chưa có (% thời gian) | 40.4 / 37.6 / 21.9 | 40.4 / 37.6 / 21.9 (21.9 + 0.0) — khớp |
| | đổi chiều · đoạn chưa rõ (mỗi ngày) | 0.82 · 0.66 | 0.82 · 0.66 — khớp |
| | trung vị giờ: chưa rõ · một chiều | 6.2 · 13.0 | 6.25 · 13.0 — khớp (làm tròn) |
| XAUUSD M5 `ds_933fa5ec67e2` 01/01–31/08/2024 | tăng / giảm / chưa rõ + chưa có (% thời gian) | 43.0 / 32.2 / 24.8 | 43.0 / 32.2 / 24.8 (24.7 + 0.1) — khớp |
| | đổi chiều · đoạn chưa rõ (mỗi ngày) | 2.22 · 1.99 | 2.22 · 1.99 — khớp |
| | trung vị giờ: chưa rõ · một chiều | 1.9 · 4.2 | 1.92 · 4.17 — khớp (làm tròn) |
| Cả bốn cấu hình | trạng thái từng nến = `rule_a` trên run/shift của lõi (`None` → 0) | yêu cầu: khớp tuyệt đối | **0 nến lệch** (15 850 / 141 742 / 149 402 / 47 548 nến) |
| Cả bốn cấu hình | `ORDER_FLOW_*` phát ở đúng (và chỉ ở) nến trạng thái đổi | yêu cầu | khớp: 290 / 2 567 / 2 778 / 890 lần đổi = bấy nhiêu sự kiện, `tu`/`sang` đúng |
| Bản chụp 0.2.0 trước khi sửa | sự kiện và timeline của 0.2.0 giữ nguyên (bỏ phần 0.3.0 thêm) | yêu cầu | giữ nguyên trên 4 cấu hình (sự kiện cũ, khoá timeline cũ, `chi_so_thuat_toan` và `pending_state` cũ); golden 106 cấu hình: chỉ 5 cấu hình `ict_structure` khác; 3 run 0.2.0 đã lưu khớp khi bỏ `ORDER_FLOW_*` |
| Hiệu năng | XAUUSD M15 `ds_a5212fd37814` 01/2018–08/2024 (157 592 nến), trung vị 6 lần | — | 0.2.0: 4.19 s → 0.3.0: 4.29 s (+2.5%) |

### 8.2. Giai đoạn 3 lõi (0.4.0): đối chiếu survey-v2, khác biệt so với 0.3.0, hồi quy, hiệu năng

Chạy lõi 0.4.0 với tham số mặc định, lịch theo mã (08/10/2026). Script kiểm tra (đọc bản sao DB, chỉ đọc) nằm ngoài
repo — số liệu dưới đây là mô tả để đối chiếu, không dùng để chọn ngưỡng; không chạm đoạn kiểm tra (từ 01/09/2024).

**Đối chiếu survey-v2** (XAUUSD M15 `ds_db1583cd4dde`, 01/01–31/08/2024; số survey từ
`docs/research/khao_sat/ict_survey_dev.json`):

| Đo | Survey-v2 | `ict_structure` 0.4.0 |
|---|---:|---:|
| Nến chốt H1 / H4 / D / W | 3965 / 1037 / 173 / 35 | 3965 / 1037 / 173 / 35 |
| `degraded` H1 / H4 / D / W | 0 / 0 / 1 / 0 | 0 / 0 / 1 (D 11/01 → 12/01, coverage 0.83) / 0 |
| Sau bucket mất (hole) H1 / H4 | 1 / 1 | 1 / 1 |
| Chốt muộn H1 / H4 / D / W (lần; giờ lớn nhất) | 5 (3.25) / 5 (1.25) / 6 (49.25) / 2 (49.25) | 0 / 0 / 1 (49.25) / 1 (49.25) |
| Cửa sổ pivot bị chặn H1 / H4 | 2 / 2 | 2 / 2 |
| ITH + ITL mỗi ngày H1 / H4 | 2.7 / 0.68 | 2.71 / 0.68 (468 / 118) |
| Thứ tự H1: +1 / −1 / lẫn lộn / chưa có (% thời gian) | 31.0 / 24.5 / 43.4 / 1.1 | 31.0 / 24.5 / 43.4 / 1.1 |
| Thứ tự H4 | 35.0 / 19.2 / 41.8 / 4.0 | 35.0 / 19.2 / 41.8 / 4.0 |
| FVG H1 / H4 (nến giữa là displacement) | 729 (28.1%) / 218 (26.1%) | 729 (28.1%) / 218 (26.6%) |
| PD chặt H1: respect / disrespect / chưa chạm | 325 / 381 / 23 | 325 / 381 / 23 |
| PD chặt H4 | 114 / 90 / 14 | 113 / 90 / 15 |
| `pd_bias`: số lần đổi; +1 / −1 / chưa có (% thời gian) | 410; 52.7 / 47.0 / 0.3 | 411; 52.7 / 46.9 / 0.3 (mâu thuẫn 0: 0.1) |
| Vùng H1 / H4 / D / W (tạo + gộp EQ) | 467 / 118 / 342 / 67 | 468 / 118 / 344 / 70 |
| Vùng bị lấy H1 / H4 / D / W | 417 / 93 / 292 / 49 | 408 / 92 / 292 / 50 |
| W = 3 sweep / run: H1 · H4 · D · W | 287/130 · 57/36 · 193/99 · 26/23 | 279/129 · 56/36 · 193/99 · 26/24 |
| Shift W = 3 theo tầng vùng chính | M15 96 · H1 26 · D 26 · W 5 (153) | M15 95 · H1 26 · D 26 · W 5 (152) |
| DOL | sau shift W = 0: 54/55 có đích, TV 6.1 ATR, tầng H1 41 · D 13; có DOL 53% thời gian | sau shift W = 3 (mặc định): 148/152 có đích, TV 5.36 ATR (P25 3.39, P90 12.28), tầng H1 62 · D 71 · W 15; có DOL 64.7% thời gian; 60 `DOL_REACHED` |

Sai lệch và giải thích:

* **Chốt muộn:** survey chốt theo mốc **danh nghĩa** nên mọi ngày đóng sớm (MLK, Presidents' Day, Good Friday tuần,
  Memorial Day, Juneteenth, 04/07) chờ tới phiên sau; lõi chốt theo `period_end` của lịch (§4.13) → chỉ còn 12/01
  (nguồn dừng 13:00 NY) chốt muộn. Cũng vì vậy tuần có Good Friday chốt Thứ Năm: PWH/PWL của tuần đó được tạo
  (survey: «bị lấy trước khi biết» ở nến Chủ nhật) rồi bị lấy bình thường → W +1 vùng, +1 bị lấy, +1 run.
* **Vùng D/W/H1 nhiều hơn 1–3:** survey bỏ vùng biết ở nến cuối đoạn (không còn nến để có hiệu lực); lõi vẫn tạo.
* **Bị lấy H1/H4 ít hơn:** gộp EQH/EQL (10 vùng H1, 2 vùng H4 gộp) — survey không gộp ở tầng nào.
* **PD chặt H4 lệch 1 vùng**, FVG H4 từ displacement 58 thay 57: biên «liền kề theo lịch» ở ngày đóng sớm (H4 qua
  khoảng đóng sớm không còn liền kề — §6) và cờ displacement theo ATR khung lớn.
* **DOL:** survey đo sau shift W = 0 (55 shift), lõi đặt sau mọi shift mặc định (W = 3) — không cùng tập.

**Tương đương ngăn xếp H4 ↔ dataset H4 gộp `ny_1700`** (plan §11.7). H4 dựng bằng
`resample_ohlc(alignment="ny_1700", calendar=…, gap_policy="emit_available")`, chạy `ict_structure` khung H4
(`gap_policy = giu_muc_khong_chan`, không lịch); so ITH/ITL (phía, giá, giờ mở nến H4) và FVG (chiều, lo, hi, nến
giữa):

| Dữ liệu | ITH/ITL: run M15 / dataset H4 / chung | FVG: run M15 / dataset H4 / chung |
|---|---|---|
| XAUUSD M15 01–08/2024 | 118 / 118 / 117 | 218 / 218 / 217 |
| XAUUSD M15 2018–2023 | 1093 / 1101 / 1091 | 1732 / 1744 / 1732 |
| EURUSD M15 2018–2023 | 1051 / 1055 / 1050 | 1825 / 1830 / 1825 |

Mọi khác biệt nằm ở chỗ dataset H4 **không biết** chất lượng / lịch: hole 12/01/2024 (cửa sổ pivot qua hole bị chặn
trong run M15), nến H4 `degraded` (XAUUSD và EURUSD 02–07/2023: mở tuần Chủ nhật thiếu 1 giờ và đóng Thứ Sáu thiếu
1 giờ so với lịch — 28 nến H4 XAUUSD coverage 0.33–0.75), ngày đóng sớm (FVG qua khoảng đóng sớm không liền kề:
15/01/2024, 21/02/2022, 30/05/2022, 20/06/2022, 24/11/2022, 04/07/2023, 27/05/2019) và 1 FVG ở nến H4 cuối đoạn. Số
phía dataset H4 tuỳ cách dựng dataset đó: kiểm độc lập (18/10/2026) tự gộp ny_1700 được 218 / 219 / 218 cho XAUUSD
M15 01–08/2024 — vẫn mọi FVG của run M15 đều có ở dataset H4, khác ở FVG ngày đóng sớm 15/01/2024. Trên
dữ liệu dựng theo lịch không có ngày đóng sớm / hole, hai bên trùng tuyệt đối, kể cả nến H4 xác nhận
(`tests/algorithms/test_ict_htf.py`).

**Nhân quả trên dữ liệu thật** (XAUUSD M15 01–08/2024): chạy tới t = chạy trọn rồi cắt ở 11 điểm cắt (6 điểm ngay
sau một lần chốt H4, tức giữa nến H4 đang hình thành) — sự kiện (kể cả `details.htf`) và timeline trùng tuyệt đối;
sửa OHLC mọi nến sau t (6 điểm) → sự kiện ≤ t và timeline ≤ t không đổi.

**Khác biệt sự kiện khung chạy so với 0.3.0** (tham số mặc định; «cùng nến» = cùng loại, nến xác nhận, phía):

| Dữ liệu | Không đổi theo thiết kế (swing, khoảng trống, displacement, FVG M15 + vòng đời) | `LIQ_*` | `SHIFT_*` / `SHIFT_FVG_*` | `ORDER_FLOW_*` |
|---|---|---|---|---|
| XAUUSD M15 01–08/2024 (15 850 nến) | 19 377 sự kiện, **trùng tuyệt đối** (id, giá, nến, lý do, tham chiếu, details trừ id vùng) | 1320 → 1341: +21 (D 17, W 3, H1 1), bớt 0; 383 thêm vùng khung lớn vào `pools`, 2 đổi vùng chính | 151 → 152 (+1, D) / 83 → 84 | 290 → 292 (+4, −2); 0.6% số nến khác trạng thái |
| XAUUSD M15 2018–2023 (141 742) | 174 335, trùng tuyệt đối | 12 133 → 12 341: +208 (D 145, H1 39, W 24), bớt 0; 26 đổi vùng chính | 1344 → 1355 (+11) / 768 → 775 | 2567 → 2592 (+46, −21); 1.0% |
| EURUSD M15 2018–2023 (149 402) | 182 866, trùng tuyệt đối | 12 416 → 12 592: +176 (D 125, W 26, H1 25), bớt 0; 34 đổi vùng chính | 1453 → 1462 (+9) / 795 → 801 | 2778 → 2806 (+48, −20); 1.2% |
| XAUUSD M5 01–08/2024 (47 548) | 61 547, trùng tuyệt đối | 4065 → 4081: +16 (D 12, H1 2, W 2), bớt 0; 5 đổi vùng chính | 434 → 434 / 243 → 243 | 890 → 890 (+2, −2); 0.1% |

Vì sao:

* **Không bớt sự kiện LIQ / shift nào:** vòng đời mỗi vùng độc lập (§4.9) — vùng M15 cho đúng kết cục như 0.3.0; vùng
  khung lớn chỉ **thêm** kết cục. Ứng viên shift cũng độc lập theo vùng nên shift cũ vẫn còn, chỉ thêm shift từ vùng
  khung lớn (chủ yếu PDH/PDL).
* **Thêm vùng vào sự kiện cũ:** nến quét vùng M15 thường quét luôn ITH H1 / PDH cùng nhịp → `pools`, `swept` dài hơn,
  `tang` = tầng cao nhất (theo tầng, shift M15 1344 → 865, phần còn lại sang H1/H4/D/W).
* **Đổi vùng chính:** vùng tầng cao bị lấy ở nến khác vùng M15 → nến sự kiện (nến lấy của vùng chính) đổi → `event_id`
  của sự kiện LIQ đó đổi (26–34 sự kiện trên 6 năm). Không ảnh hưởng chấm: mục tiêu chấm chỉ là swing cấp 2 và shift
  (id `SHIFT_*` = nến displacement, không đổi).
* **Order flow:** run/shift mới từ vùng khung lớn → thêm lần đổi trạng thái (đa số `run_nguoc_chieu`, `run_giam`);
  tỷ lệ thời gian tăng/giảm/chưa rõ đổi ≤ 0.2 điểm %.
* Timeline: `liq_above` / `liq_below` / `pending_takes` khác ở ~1% số nến (vùng gần nhất có thể là vùng khung lớn).

**Hồi quy run đã lưu** (`scripts/regression_saved_runs.py --compare` với dấu vân tay 0.3.0, bản sao DB 108 cấu hình):
chỉ **7** cấu hình khác — đúng 7 cấu hình `ict_structure` chạy được (5 run đã lưu 0.2.0/0.3.0 + 2 ma trận M15; 3 ma
trận M5/H1 lỗi «sai khung» y như trước). **`c2_cisd_research` 9/9 cấu hình khớp 100%** (bộ gộp `utc_epoch` không đổi);
mọi thuật toán khác (swing_pivot 20, swing_hierarchy 19, dc_atr_structure 30, indicator_baseline 14, hmm_online 6) khớp
100%.

**Hiệu năng** (một luồng Python, mỗi lần đo một tiến trình mới, trung vị 3 lần, cùng phiên máy):

| Dữ liệu | 0.3.0 | 0.4.0 |
|---|---:|---:|
| XAUUSD M15 `ds_a5212fd37814` 01/2018–08/2024 (157 592 nến) | 3.81 s (đo trước: 4.29 s) | **9.22 s** (241 527 sự kiện) |
| Như trên, tắt GC Python | 3.27 s | 7.6–8.0 s |
| XAUUSD M1 `ds_0d44e89df5fd` 01–08/2024 (237 701 nến) | 5.89 s | 10.43 s (116 844 nến: 4.75 s — tuyến tính) |

Chi phí thêm ~30 µs/nến chia đều cho: bộ gộp 4 khung mỗi nến, ~58 000 lần chốt nến khung lớn (H1 chiếm ~2/3), chụp
ngữ cảnh mỗi nến + dựng `details.htf` ở nến có sự kiện, vùng nhiều tầng, PD array, thêm đối tượng cho GC. Không tăng
theo bình phương số nến.

**Dung lượng:** `details.htf` ~0.9 KB mỗi sự kiện khung chạy — XAUUSD M15 01–08/2024: JSON sự kiện 20.9 MB → 45.8 MB
(`details.htf` 20.2 MB), timeline 11.9 → 17.4 MB. Run 6–8 năm M15 lưu vào SQLite tăng tương ứng (~+200 MB) — §9.
**0.4.1** bỏ `details.htf` ở sự kiện nguyên liệu: XAUUSD M15 2022–2023 (47 066 nến, cỡ một lần chạy mặc định của trang)
JSON sự kiện 133.4 MB (0.4.0) → 85.4 MB; 0.3.0 cùng khoảng ~73 MB.

## 9. Giới hạn và việc để sau

* **Giao diện giai đoạn 3** đã cài (§11) nhưng chưa qua lần kiểm độc lập như H-A/H-B (nhân quả lớp «Khung lớn» khi
  replay, số đối tượng mặc định) — có test node (`tests/frontend/test_ict_display.py`).
* **Công cụ hồ sơ khung** (plan §11.6: null ghép cặp cùng killzone × nhóm ATR cho câu hỏi §11.2, sai số chuẩn) —
  chưa làm; `research/ict_survey.py` vẫn là bản mẫu.
* **Dung lượng:** 0.4.0 gắn `details.htf` trên mọi sự kiện (JSON ~2.2 lần 0.3.0); 0.4.1 bỏ ở sự kiện nguyên liệu (§8.2,
  −36%) — khác plan §11.5 («trên mọi sự kiện M15»), xem §12.
* **Hiệu năng:** chậm ~2.4 lần so với 0.3.0 (§8.2), vẫn tuyến tính.
* `htf_alignment` chỉ mở `ny_1700`; biến thể `utc_epoch` cho `ict_structure` (để so như survey «H4 khác nhau 30%»)
  chưa cài.
* Không có lịch (`session_calendar = none`) → số nến kỳ vọng danh nghĩa: với dữ liệu thật, nến H4 đầu ngày
  (12/16 nến) bị coi là thiếu → `degraded`. Dùng lịch theo mã (`auto`).
* `swing_source = dc` (biến thể D2) và `min_leg_atr` (plan §4.2) **chưa cài** — `min_leg_atr` cần định
  nghĩa chính xác trước.
* Khối lượng sự kiện: vòng đời FVG chiếm gần nửa số sự kiện. Nếu kho lưu/giao diện chậm với run dài,
  cân nhắc tham số tắt `FVG_TOUCHED/FILLED` (cần duyệt — plan đang yêu cầu phát).
* Hiển thị: tô màu nến theo order flow (H3) và dùng lại lớp vẽ chung cho thuật toán khác (H-C) để sau (§11).
* **Order flow là mô tả, không phải dự báo** ([`nghien_cuu_orderflow_ict.md`](../research/nghien_cuu_orderflow_ict.md)
  §1, §5): trên dữ liệu lab, không cách đọc nào (run + shift, chỉ run, chỉ shift, sweep, phản ứng FVG,
  HH/HL; M5–H4; lọc theo khung lớn; đích là vùng D1) dự báo phía thanh khoản bị lấy kế tiếp tốt hơn mốc
  ngẫu nhiên theo khoảng cách. Không có mục tiêu chấm; nếu dùng thì làm **đặc trưng** cho tầng regime
  (B3), không làm tín hiệu.
* **Order flow** (0.4.0) thấy vùng mọi tầng (M15, H1, H4, PDH/PDL, PWH/PWL); chưa có đỉnh/đáy phiên, chưa dùng
  FVG (IRL) làm đầu vào, chưa có order flow khung lớn làm ngữ cảnh.
* Order flow không có tham số riêng nhưng phụ thuộc gián tiếp `sweep_window` (run trễ W nến), `shift_window`,
  `k_disp` / `body_min`, `min_pen_atr`. Với mặc định, «chưa rõ» chiếm 22–25% thời gian ở M15 và M5
  (nghiên cứu §8.1).
* **OB / OTE (0.5.0) là mô tả**, chưa có mục tiêu chấm hay loại nhãn; giá trị đoán hướng / giữ giá đo ở khảo sát
  K17–K27 (plan kết hợp §3.4, bước 0). Breaker (OB hỏng đổi vai), IFVG, OB khung lớn, OTE theo nhịp không neo SHIFT để
  sau.
* Chưa có nhãn tham chiếu (D8) → chưa có F1; thống kê là mô tả hành vi. Loại nhãn tay `SHIFT_UP/DOWN` đã
  có (trang Gán nhãn), mục tiêu chấm `ict_shift` đã có.

## 10. Kiểm thử

`tests/algorithms/test_ict_structure.py` (17 test, giai đoạn 1), `tests/algorithms/test_ict_structure_g2.py`
(26 test, giai đoạn 2), `tests/algorithms/test_ict_order_flow.py` (33 test, order flow 0.3.0),
`tests/algorithms/test_ict_htf.py` (25 test, giai đoạn 3 lõi) và `tests/api/test_ict_structure_api.py` (7 test).
Toàn bộ `pytest`: 507/507 đạt (08/10/2026).

* tính tay: STH/STL strict, outside bar, hai high bằng nhau; ITH xác nhận khi STH phải xác nhận (basis,
  reference); cấp 3 chỉ khi bật và lọc trên ITH;
* thứ tự / mức được bảo vệ đúng ví dụ plan (ITL 100 → 105, close 104 → cờ vượt, thứ tự vẫn +1), HH + LL
  → lẫn lộn và mất mức, EQH trong dung sai, ATR chưa đủ → chưa so;
* dealing range chứa close; timeline: `lo ≤ close ≤ hi`, `range_pos` ∈ [0, 1], có mức bảo vệ ⇔ thứ tự ±1;
* khoảng trống theo lịch CME thật: nghỉ hằng ngày, cuối tuần, thiếu trong phiên (đếm ô), ngoài lịch,
  không chọn lịch; cửa sổ pivot vắt qua khoảng trống bị chặn; `auto` → lịch theo mã;
* displacement đúng/thiếu ngưỡng biên độ và thân, sau khoảng trống, chưa có ATR;
* FVG: vùng, `from_displacement`, vắt khoảng trống bị loại, lọc nhỏ; chạm rồi lấp, chạm + lấp cùng nến;
* thanh khoản: xuyên 0.05 ATR là chạm, 0.15 là lấy; ATR khoá đúng nến lấy; W tính cả nến lấy (quay lại ở
  b, b+3 → sweep; không quay lại tới b+3 → run tại b+3; quay lại ở b+4 không đổi run); khoảng trống →
  chưa rõ tại nến sau khoảng trống; một nến lấy nhiều vùng; gộp EQ chỉ giữa swing liên tiếp; vùng đã bị
  lấy trước khi biết → không tạo; một nến quét hai vùng → một sự kiện, vùng chính đúng;
* shift: displacement ngay nến quét, ở r+3, quá cửa sổ; vượt X → huỷ; khoảng trống → huỷ; close phải qua
  mức, đúng chiều; hai sweep → một shift; chuỗi dựng tay sweep → shift → `SHIFT_FVG` với `group_id`,
  `reference`, `basis`, ATR khoá tính độc lập; shift ngược chiều ở d+1 không che `SHIFT_FVG` của shift ở d;
* killzone: giờ New York trước/sau đổi giờ mùa hè, biên nửa mở, tham số sai bị từ chối;
* **tương đương** (3 chuỗi ngẫu nhiên có khoảng trống và giá bằng nhau): STH/STL = `swing_pivot(1,1)`,
  ITH/ITL = `swing_hierarchy(1,1)` khi tắt chặn; bản chặn là tập con;
* **bất biến** trên dữ liệu ngẫu nhiên có đủ mọi loại sự kiện: `event_id` duy nhất; `reference`/`basis`
  không trỏ tới sự kiện biết sau; vùng chỉ bị lấy sau nến làm nó được biết; `sweep_bars` ≤ W, run đúng
  b+W; shift có displacement cùng nến, cùng chiều; `SHIFT_FVG` ở d+1 cùng `group_id`;
* **nhân quả**: prefix = full lọc theo nến xác nhận ở nhiều điểm cắt (cấp 2 và 3, và chuỗi có shift);
  sửa mọi nến sau T không đổi sự kiện và timeline tới T; sự kiện đã trả không bị sửa ngầm; tất định; dữ
  liệu sai bị từ chối;
* API: đăng ký, `auto` → `cme_globex_metals`, lưu → mở lại → CSV/manifest, replay tiến/lùi, sai khung → 400,
  chấm ITH/ITL với mục tiêu Swing cấu trúc; chấm shift với mục tiêu `ict_shift` (khớp hết) và đổi tầng
  sang `SHIFT_FVG` qua `event_type_map`; order flow 0.3.0 trong run (khoá timeline, sự kiện có nến sự kiện =
  nến xác nhận, `pending_state` khớp timeline, thống kê), replay tới nến 400 khớp run;
* **order flow** (`test_ict_order_flow.py`): thành phần — bảng chuyển trạng thái §4.12 (15 ô đổi, 7 ô giữ
  nguyên / chỉ ủng hộ), `ung_ho_gan_nhat` xoá khi đổi, snapshot là bản sao, `reset`, đầu vào sai bị từ
  chối; chuỗi nến dựng tay: shift giảm rồi shift tăng, run tăng rồi run ngược chiều → chưa rõ; dữ liệu ngẫu
  nhiên có khoảng trống (2 seed): quy tắc A cài lại độc lập khớp timeline từng nến, `ORDER_FLOW_*` đúng
  (và chỉ) ở nến đổi với tham chiếu đúng, thống kê khớp số tính độc lập, nhân quả prefix = full và sửa đuôi
  không đổi quá khứ, `pending_state` là bản sao;
* **khung lớn** (`test_ict_htf.py`, plan §11.7): mốc `ny_1700` trước/sau đổi giờ 10/03 và 03/11/2024 (D, H4, tuần
  167/169 giờ), H1 = giờ tròn, `utc_epoch` giữ quy ước `resample`; bộ gộp trên dữ liệu dựng theo lịch CME: giờ nghỉ
  nằm trong nến H4 đầu ngày (12 nến), D 92 nến, tuần Chủ nhật 17:00 → Thứ Sáu 17:00 (460 nến), liền kề theo lịch (H4
  qua ngày có, qua cuối tuần không, H1 qua giờ nghỉ không); ngày đóng sớm 15/01/2024 không degraded, chốt đúng giờ
  19:30 UTC, nến sau không liền kề; chốt muộn khi thiếu nến cuối (`period_end` ≠ `known_at`, H1 3/4 → degraded); kỳ
  đầu thiếu, hole (`after_hole`), nến sau giờ đóng sớm → kỳ «nối tiếp» degraded; `HtfAggregator`/`resample`
  `utc_epoch` không đổi, `resample` `ny_1700` có/không lịch;
  ngăn xếp tính tay: ITH H4 xác nhận đúng nến, nến degraded trong cửa sổ → không ITH (2 cửa sổ bị chặn), hole chỉ
  chặn cửa sổ vắt qua; FVG cần liền kề theo lịch và không degraded; PD chặt / lỏng / CE (tap rồi kết quả đầu
  tiên, một kết quả mỗi vùng, chưa chạm thì không có kết quả, hai chiều cùng nến → 0); DOL (vùng gần nhất đúng
  tầng, đạt khi bị lấy, bị thay, none); thuật toán trên dữ liệu theo lịch: `details.htf` đúng khuôn §11.5 trên mọi
  sự kiện khung chạy và không có trên `HTF_*`, cột timeline; neo `HTF_*` đúng nến cực trị, vùng hiệu lực từ nến sau,
  tham chiếu không trỏ tới sự kiện biết sau; kỳ đầu thiếu → không PDH/PWH; midnight open thiếu → null (có nến 00:00
  NY → đúng open); H1 degraded → không ITH/ITL H1 nào có nến đó trong cửa sổ, 3 cửa sổ bị chặn; **nhân quả** prefix
  = full ở nhiều điểm cắt (cả giữa nến H4), sửa OHLC sau t trong nến H4 đang hình thành không đổi sự kiện/timeline
  ≤ t, sự kiện đã trả không bị sửa ngầm; **thứ tự**: sự kiện ở nến chốt H4 mang ngữ cảnh trước lần chốt (> 50 nến
  kiểm, có nến thứ tự H4 đổi đúng lúc đó); **tương đương** ITH/ITL và FVG H4 với dataset H4 gộp `ny_1700` (trùng
  tuyệt đối cả nến H4 xác nhận); tham số (`htf_list` sai bị từ chối, dataset H1/H4, mặc định), `khong_phat` không
  đổi gì khác, tắt [T] → không có vùng khung lớn, PD, DOL;
* API 0.4.0: tham số mới và mặc định, sự kiện `HTF_*`/`PD_*` có câu giải thích, `details.htf`, cột timeline, thống
  kê, `pending_state.khung_lon`, manifest, CSV, replay tới nến 600 khớp run, `htf_list` sai → 400.
* **OB / OTE 0.5.0** (`tests/algorithms/test_ict_ob_ote.py`, 15 test): thành phần tính tay — OB-T gộp chuỗi, OB-R cả
  râu, không lùi qua khoảng trống, không có nến ngược màu, ứng viên chờ xác nhận rồi chạm, hỏng cùng nến chạm, ứng viên
  bị bỏ, hết hạn theo thời gian / SHIFT ngược; OTE vào vùng + độ sâu, đầu nhịp chỉ lấy tới nến trước (nến vừa lập đỉnh
  vừa hồi sâu không tự vào), hỏng xét trước, nhịp nhỏ, hết hạn, nhịp giảm, thay nhịp; chuỗi BASE + 3 nến tính tay
  (OB giảm xác nhận ngay, hết hạn vì SHIFT ngược, OB tăng xác nhận muộn, chạm, vào OTE); biến thể và neo displacement;
  bất biến và nhân quả prefix = full trên dữ liệu ngẫu nhiên. API (`test_ob_ote_v050_qua_api`). Hiển thị
  (`tests/frontend/test_ict_ob_ote_display.py`, node): nét / chữ theo kết cục, OTE đang chờ, vùng OTE = timeline,
  OB mở gần nhất = cột `ob_*`, replay prefix = lọc theo con trỏ. Mốc so trước/sau: mọi output cũ trùng tuyệt đối (§1).

## 11. Hiển thị trên chart (giao diện, không đổi lõi)

Theo [`plan_hien_thi_ict.md`](../plans/plan_hien_thi_ict.md) (H1–H4 duyệt 06/10/2026; H-A, H-B đã cài cùng ngày —
nghiệm thu và chỗ cài khác plan ở plan §7.1–§7.2). Chỉ đổi phần vẽ: plugin `frontend/js/algos/ict_structure.js`,
dựng hình thuần `frontend/js/algos/ict_structure_view.js` (`MSL.ictView`), lớp vẽ chung
`frontend/js/chart/primitives.js`. Phần vẽ chỉ đọc sự kiện, timeline, `pending_state` — đổi giao diện không đổi lõi.

| Chế độ | Vẽ gì | Đọc từ |
|---|---|---|
| **Gọn** (mặc định: lớp `ict_flow` «Order flow + vùng thanh khoản», `ict_shift`, `ict_gap`) | Vùng BSL (cam) / SSL (xanh ngọc) vẽ **từ nến ITH/ITL gốc**, chỉ xuất hiện từ nến xác nhận: còn nguyên = nét liền tới con trỏ + 5 nến, nhãn BSL / SSL / EQH / EQL; sweep = dừng ở nến lấy, nét chấm + hộp phần râu vượt mức; run = dừng ở nến lấy, mờ; chưa rõ = chấm xám; đang chờ = nét đứt «bị lấy · chờ». «Hiện tại»: 2 vùng còn nguyên gần nhất mỗi phía, ≤ 3 nhóm kết cục gần con trỏ nhất mỗi phía (trong 60 nến), vùng của shift đang hiện, vùng đang chờ. «Shift ↓/↑» tại mức bị quét + hộp FVG của chính nến displacement. Dải order flow ở đáy, chữ ở đầu mỗi đoạn («↑ run BSL», «↓ shift», «? run ngược»…). Marker «thiếu» cho khoảng trống bất thường | `details.vung_thanh_khoan` của ITH/ITL, `details.pools` của `LIQ_*`, `pending_state.thanh_khoan.dang_cho_sweep_run`; `SHIFT_*`, `SHIFT_FVG_*`, `FVG_FILLED`; timeline `order_flow*` và `ORDER_FLOW_*`; `ICT_GAP` |
| **Chi tiết** (`ict_detail`, tắt; lớp con dùng `data-requires`) | ITH/ITL = chấm nhỏ tại pivot (nhãn HH / HL / LH / LL / EQ ở lớp `ict_labels`, tắt sẵn), STH/STL (tắt), LTH/LTL; «Protected Low/High» tới con trỏ + 20 nến (close đã vượt → nét đứt đỏ «broken» — chỉ là cờ, không phải BOS); dealing range = 3 dải Premium / EQ / Discount (nhãn ở đầu trái dải); FVG = hộp + CE nét đứt, viền theo vòng đời (mở / đã chạm / đã lấp), «Hiện tại» = FVG còn mở biết trong 200 nến và cách close ≤ 5 ATR, tối đa 3 gần giá nhất mỗi chiều (`ict_fvg` bật sẵn); «Mọi vùng còn nguyên» (`ict_liq`, tắt); displacement = quầng nhạt sau cây nến (`ict_disp`, tắt) | `SWING_*` (`details.nhan`); timeline `protected*`, `dealing_*` **tại con trỏ**; `FVG_*`; `DISPLACEMENT_*` |
| **Khung lớn** (`ict_htf`, tắt sẵn, nhóm riêng; lớp con `ict_htf_swing`, `ict_htf_range`, `ict_htf_fvg`, `ict_htf_levels`, `ict_htf_forming` bật, `ict_htf_h1` tắt — giao diện giai đoạn 3, 08/10/2026) | ITH/ITL H4 = vòng tròn rỗng tím tại nến khung chạy chạm cực trị, chữ «HH H4» / «ITL H4»…, hiện từ nến M15 biết nến H4 đã chốt; dealing range H4 + EQ (nét đứt / chấm tím) tại con trỏ; FVG H4 đang mở = hộp viền dày «FVG H4», dừng ở PD respect / disrespect đầu tiên («Hiện tại»: 2 gần giá nhất mỗi chiều trong 10 ATR + FVG đặt `pd_bias` hiện tại); PDH/PDL, PWH/PWL hiện hành (đã lấy → chấm mờ «· đã lấy»; mức đã vẽ thành vùng ở Gọn thì không vẽ lại); nến H4 đang hình thành = khung nét đứt + thân mờ «H4 đang hình thành — chưa dùng» (chỉ để vẽ, gộp từ nến ≤ con trỏ); «Thêm H1»: ITH/ITL H1 + FVG H1. Ngoài lớp này, vùng thanh khoản ở chế độ Gọn ghi **tầng** («BSL H1», «EQH H4», «PDH», «PWL»), nét đậm dần theo tầng; dòng trạng thái thêm «│ H4 … · pd … · DOL …»; khung «Thuật toán đang làm gì» thêm mục «Khung lớn (chỉ nến đã chốt)», mỗi thành phần một dòng | `HTF_SWING_*`, `HTF_FVG_*` (+ `PD_*` có `details.fvg`), `HTF_PERIOD_*`; timeline `htf_H4_dealing_hi/lo`, `htf_*`, `pd_bias*`, `dol_*`; `details.vung_thanh_khoan.tang`; `pending_state.khung_lon` / `pd` / `dol`. **Không đọc `details.htf`** |
| **Order block** (`ict_ob`, tắt sẵn) · **OTE** (`ict_ote`, tắt sẵn) — 0.5.0, dựng hình thuần `frontend/js/algos/ict_ob_ote_view.js` (`MSL.ictObOteView`) | OB = hộp xanh / đỏ từ nến đầu khối tới nến kết cục (còn mở: tới con trỏ + 5), nét liền = còn mở, đứt = đã chạm, chấm = hỏng / hết hạn; đường chấm = mean threshold; chữ «OB ↑ · chạm»… «Hiện tại»: ≤ 3 OB còn mở gần giá nhất mỗi chiều + ≤ 2 OB kết thúc trong 60 nến mỗi chiều. OTE đang chờ = hộp vàng nét đứt từ nến SHIFT tới con trỏ + điểm ngọt (chấm) + gốc nhịp (nét đứt mờ, «gốc nhịp · chờ nhịp đủ lớn» khi chưa có vùng); OTE vừa vào / hỏng (60 nến) = hộp vàng tới nến kết cục, «OTE ↑ · vào 66%». Khung «Thuật toán đang làm gì», tab Thống kê, trạng thái replay có mục OB / OTE | `ORDER_BLOCK_*` + kết cục (`OB_TAP_*`, `OB_FAIL_*`, `OB_EXPIRED` — `reference_event_id`); timeline `ote_*` **tại con trỏ**, gốc = SHIFT gần nhất; `OTE_ENTRY_*` / `OTE_FAIL_*`; `pending_state.order_block` / `.ote` |
| ~~Lịch sử~~ — **tạm bỏ khỏi giao diện** (người dùng, 08/10/2026; phần dựng hình thuần `opts.history` vẫn giữ và vẫn được test) | Thay «Hiện tại» bằng mọi vùng / shift / FVG đã biết tới con trỏ, mờ dần theo tuổi; Protected và dealing range vẫn chỉ tại con trỏ | như trên |

Không còn chú giải màu: chữ nằm ngay trên đối tượng (H2 — thuật ngữ ICT ngắn tiếng Anh). Dòng trạng thái 2 hàng
`#ict-status` ở góc trên chart ghi order flow ở nến dưới chuột (mặc định nến con trỏ): trạng thái, từ khi nào, vì sao;
vùng gần nhất, điều gì làm đổi, đang chờ gì. Rê chuột vào đường / hộp / dải → tooltip giải thích tiếng Việt. Kết quả
cũ (0.2.0, chưa có khoá order flow) vẫn hiển thị được, chỉ thiếu phần order flow.

**Nhân quả khi replay:** mọi đối tượng chỉ xuất hiện khi `confirmed_bar_index` ≤ con trỏ — vẽ từ nến gốc chỉ là chỗ
bắt đầu vẽ, không phải biết sớm hơn. «Hiện tại», dòng trạng thái và tooltip tính theo con trỏ (nến cuối khi xem toàn
lịch sử), không theo vùng đang nhìn; vùng đang chờ lấy từ `pending_state` tại con trỏ. Plugin chỉ đọc sự kiện,
timeline, `pending_state` — không tính lại quy tắc nào. Kiểm bằng `tests/frontend/test_ict_display.py` (hàm thuần
chạy bằng node: kịch bản dựng tay; dữ liệu lõi thật — vùng gần nhất khớp `liq_above` / `liq_below` ở mọi nến, replay
prefix cho cùng đối tượng như toàn bộ sự kiện lọc theo con trỏ, không đối tượng nào trước nến xác nhận).

## 12. Chỗ cài khác plan / quyết định khi cài (giai đoạn 3, 0.4.0)

Những chỗ plan không nói rõ — chọn phương án bảo thủ nhất khớp tinh thần plan:

| # | Chỗ | Plan | Đã cài | Lý do |
|---|---|---|---|---|
| G3-1 | `period_end` | «mốc đóng theo lịch» | Mốc đóng của ô mở cuối theo **lịch khai báo** (ngày đóng sớm chốt đúng giờ); survey-v2 dùng mốc danh nghĩa | Lịch là dữ liệu khai báo biết trước → nhân quả; ngữ cảnh ngày lễ không phải chờ tới phiên sau (§8.2: D chốt muộn 1 thay 6) |
| G3-2 | Nến sau mốc đóng theo lịch (dữ liệu khác lịch) | Không nói | Kỳ «nối tiếp» riêng, `degraded` (`ngoai_lich`), `HTF_BAR_DEGRADED` | Không để 1–4 nến lẻ thành một nến H4/D/W trong cấu trúc hay tạo PWH; `over` vẫn chỉ là cờ với kỳ thường |
| G3-3 | Pivot khung lớn qua nghỉ phiên / cuối tuần | Chỉ nói degraded và hole chặn | Không chặn | Theo đúng §11.4 và survey-v2 (2/2 cửa sổ bị chặn) |
| G3-4 | «Liền kề theo lịch» của bộ ba FVG | Không vắt qua nghỉ phiên / cuối tuần / bucket mất | Nến sau mở đúng lúc nến trước **đóng theo lịch** | H4: giờ nghỉ nằm trong nến 17–21 nên qua ngày vẫn liền kề (như survey); khác survey ở ngày đóng sớm (không liền kề) |
| G3-5 | `protected_broken`, dealing range khung lớn | «cùng thành phần với M15» | Theo nến khung lớn **đã chốt** (close, high/low) | AGENTS §2.1: nến khung lớn đang hình thành không vào trạng thái. Survey-v2 đo bằng nến M15 |
| G3-6 | `zone`, `range_pos` trong `details.htf` | «giá ở discount 31%» | Close khung chạy so với dealing range khung lớn đã chốt; `range_pos` không kẹp vào [0, 1] | Giá hiện tại là thông tin đã biết; không kẹp để thấy giá đã ra ngoài |
| G3-7 | Gộp EQH/EQL tầng khung lớn | «hai ITH (ITL) liên tiếp cùng tầng» | H1/H4: × ATR khung lớn; D/W: không gộp | PDH/PDL không phải ITH/ITL |
| G3-8 | `pd_bias` khi nhiều kết quả cùng nến | «sự kiện gần nhất» | Cùng chiều → chiều đó; ngược chiều → 0 | Không chọn im lặng một phía (AGENTS §3.2); như order flow «hai chiều cùng nến» |
| G3-9 | Respect của biến thể `ce` | Chỉ định nghĩa disrespect | Như `loose` | Đúng cách survey-v2 đo (plan §2.6) |
| G3-10 | DOL không có vùng phía shift | «→ none» | `side = target = None`, DOL cũ bị thay | Như survey-v2 |
| G3-11 | Giá mở ngày khi thiếu nến đầu ngày | Không nói | None | Cùng tinh thần «midnight open thiếu → null, không lấy giá thay thế» |
| G3-12 | Sự kiện tạo mức theo kỳ | §5.1 không có | Thêm `HTF_PERIOD_HIGH/LOW` (ẩn, như `HTF_*`) mang `vung_thanh_khoan` | Giao diện dựng vùng từ sự kiện (không tính lại logic): không có sự kiện này thì chart không biết PDH/PDL còn nguyên ở đâu (test hiển thị «vùng gần nhất khớp timeline» sẽ sai) |
| G3-13 | `levels` trong `details.htf` | `pdh`, `pdl`, `pdh_taken`, `pdl_taken`, `day_open`, `midnight_open` | Thêm `pwh`, `pwl`, `pwh_taken`, `pwl_taken` | PWH/PWL là vùng ngang PDH/PDL (D13); thêm khoá, không đổi khoá của plan |
| G3-14 | Cột timeline | 9 cột §11.5 | 9 cột + `htf_H4_dealing_hi/lo`, `pd_bias_tf`, `dol_target`, `dol_tier`, `dol_dist_atr` (§5.2) | Để giao diện vẽ dealing range H4 / DOL ở mọi nến mà không tính lại |
| G3-15 | `htf_events = ẩn` | Không định nghĩa giá trị | `an` (phát, ẩn trên chart — việc của plugin) / `khong_phat` | Tham số lõi không quyết định hiển thị; cho phép giảm số sự kiện |
| G3-16 | `htf_alignment` | Tham số, mặc định `ny_1700` | Chỉ một lựa chọn `ny_1700` | D10; `utc_epoch` giữ cho `c2_cisd_research` (bộ gộp `utc_epoch` cũ không đụng) |
| G3-17 | Dataset không phải M15 | Không nói | Khung ≤ khung dataset bỏ qua; dataset > H1 tắt [T]; dữ liệu lệch lưới giờ → lỗi rõ ràng | Mốc `ny_1700` trên giờ tròn; chạy mặc định trên H1 vẫn được |
| G3-18 | Không có lịch | D14 yêu cầu lịch | Số nến kỳ vọng danh nghĩa | Không đoán lịch từ dữ liệu (AGENTS §2.2); dữ liệu mô phỏng 24/7 vẫn đúng |
| G3-19 | `blocked_windows_recent` | Không có cửa sổ | 20 nến khung lớn gần nhất, đếm mọi tâm cửa sổ | Do lab chọn — chỉ là bối cảnh cho regime |
| G3-20 | `details.htf` dựng lười | «ảnh chụp tại lúc xác nhận, bất biến» | Chụp giá trị ở cuối mỗi nến, dựng dict khi nến sau có sự kiện; dùng chung một dict cho các sự kiện cùng nến | Cùng nội dung; giảm thời gian và bộ nhớ (§8.2) |
| G3-0.4.1 | `details.htf` trên **mọi** sự kiện khung chạy (plan §11.5) | Từ 0.4.1 chỉ trên sự kiện cấu trúc; STH/STL, FVG M15 + vòng đời, displacement không mang | Các sự kiện nguyên liệu chiếm ~35% JSON (§8.2); ngữ cảnh của chúng tra được ở timeline nến xác nhận − 1. Đề xuất 08/10, làm 18/10/2026 |
| G3-0.4.2 | Ô lịch đóng trọn có dữ liệu; kỳ ngoài lịch và mức theo kỳ | Không nói | `degraded` `ngoai_lich`; kỳ ngoài lịch không thay PDH/PDL, PWH/PWL của kỳ thường | Đúng ý G3-2 (vài nến lẻ không thành nến khung lớn); PDH/PDL vẫn là của ngày giao dịch trước. Kiểm độc lập 18/10/2026 (F1, F2) |

**0.5.0 (order block, OTE) — chỗ plan kết hợp §3.4 không nói rõ:**

| # | Chỗ | Plan | Đã cài | Lý do |
|---|---|---|---|---|
| E-1 | Xác nhận OB | Bảng §3.4 không ghi | OB chỉ có hiệu lực (và phát `ORDER_BLOCK_*`) khi giá vượt đầu xa của khối; trước đó là ứng viên | Nghiên cứu ICT §3.4 (gốc ICT) mà plan dẫn; bản đầu không có điều kiện này cho OB nằm cả trên giá (đỉnh thân cao hơn đỉnh nhịp) → «chạm» ngay nến sau một cách vô nghĩa |
| E-2 | Hết hạn | «không phát sự kiện» (luồng §4.4 bản đầu) | Phát `OB_EXPIRED` / `OTE_EXPIRED` (ẩn trên chart, không mang `details.htf`) | Giao diện phải biết hộp dừng ở đâu mà không tính lại quy tắc (AGENTS: plugin chỉ đọc lõi) |
| E-3 | SHIFT cùng chiều khi nhịp OTE đang chờ | Chỉ nói SHIFT ngược chiều | Thay nhịp (`replaced`) | Một nhịp đang chờ tại một thời điểm; SHIFT mới là nhịp ICT đang xét |
| E-4 | «Nến lấy» của OB khi shift gom nhiều sweep | Không nói | Nến lấy của ứng viên shift chính (cùng quy tắc chọn `cuc_tri_cu_quet`) | Một shift một OB |
| E-5 | Ứng viên OB gặp SHIFT ngược chiều | Không nói | Bỏ (đếm), không phát sự kiện | Chưa từng có hiệu lực |
| E-6 | Neo displacement (OB-D) | «displacement phá đỉnh/đáy 5 nến» | close > high cao nhất (< low thấp nhất) của `ob_lui` nến trước, không vượt khoảng trống | Cùng `ob_lui` với tìm nến; phá bằng close cho chắc |
| E-7 | Hai SHIFT (hoặc hai displacement, OB-D) cùng chiều tìm ra đúng một chuỗi nến | Không nói | Dùng lại OB đã có, không phát sự kiện mới (đếm `trung_ob_da_co`); nhịp OTE mới gắn OB đó | AGENTS §5.1: một cấu trúc một sự kiện (matcher không đếm trùng); OB-D trước khi gộp có 81/787 OB trùng |
| E-8 | Nến d vừa vượt đầu xa vừa close qua mép xa | Không nói | Bỏ ứng viên (xét «close qua mép xa» trước, như mọi nến sau d) | Một quy tắc cho mọi nến ≥ d |
| E-9 | OTE vào vùng khi ứng viên OB cùng shift đã bị bỏ | «kể cả khi còn là ứng viên» | `details.ob = None`, `ob_giao_vung = None` | Vùng của ứng viên bị bỏ không còn — không dùng cho luật K25 |
