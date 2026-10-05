# `ict_structure` — bộ nhận diện cấu trúc ICT phân tầng

**Trạng thái:** giai đoạn 1 đã cài (v0.1.0, 05/10/2026). Giai đoạn 2–4 chưa cài.
Nguồn: [`plan_ict_structure.md`](../plans/plan_ict_structure.md) bản 2.2 — quyết định B1–B3 (02/10/2026)
và D1–D15 (duyệt 04/10/2026). Không có BOS/CHoCH/MSS (B1). Mã: `core/algorithms/ict_structure/`,
thành phần dùng chung `core/components/`, plugin hiển thị `frontend/js/algos/ict_structure.js`.

Không phải tín hiệu giao dịch. Đầu ra là **bằng chứng có giải thích** cho tầng regime (plan §1).

---

## 1. Phiên bản

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| 0.1.0 | 05/10/2026 | Giai đoạn 1: [G] lịch phiên + phân loại khoảng trống, [A] ATR, [P1] STH/STL, [S1] ITH/ITL (+ cấp 3 tuỳ chọn), [S2] thứ tự đỉnh/đáy + mức được bảo vệ, [S4] dealing range; timeline, trạng thái replay, giao diện tối thiểu |

Quy ước: mỗi giai đoạn sau thêm loại sự kiện (sweep, shift, FVG, khung lớn…) → output khác → tăng
phiên bản (AGENTS §5.3). «v0.1» trong plan là phạm vi của đặc tả đầu, không phải một bản phát hành.

## 2. Tầng, đầu vào, đầu ra

| | |
|---|---|
| Tầng (kien_truc_luong_ict §2) | [G] tầng 0 (dữ liệu); [P1]/[S1] tầng 1 (swing); [S2]/[S4] tầng 2 (thứ tự, dealing range) |
| Đầu vào | Nến **một khung** (khuyến nghị M15 — D9), đã đóng, theo thứ tự; lịch phiên khai báo `data/calendars/` (D14) |
| Đầu ra | Sự kiện (§7), `timeline_point` mỗi nến, `pending_state` (replay), `run_stats` (tab Thống kê) |
| Thành phần | `session_gap` [G] · `swing_source` [P1] · `hierarchy` [S1] · `structure_order` [S2] · `dealing_range` [S4] |

Thành phần chỉ dùng cho `ict_structure` (plan R7) — `swing_pivot` / `swing_hierarchy` **không** bị
refactor; tương đương được kiểm bằng test (§10).

## 3. Tham số

| Tham số | Mặc định | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| `timeframe` | M15 | khớp dataset | Bước nến để phân loại khoảng trống; trang Thử nghiệm tự điền, sai → lỗi |
| `session_calendar` | `auto` | `auto` · `cme_globex_metals` · `fx_spot` · `none` | `auto` = theo mã của dataset (XAUUSD → CME kim loại, EURUSD → FX spot) — service đổi thành tên cụ thể **trước** khi chạy, run lưu tên đó |
| `pivot_left` / `pivot_right` | 1 / 1 | 1–10 | Cửa sổ pivot strict (§4.3) |
| `structure_level` | 2 | 1–3 | Cấp swing dùng cho thứ tự, mức được bảo vệ, dealing range: 1 STH/STL, 2 ITH/ITL (D2), 3 LTH/LTL |
| `atr_period` | 14 | 2–500 | ATR Wilder, seed = trung bình `period` TR đầu có close trước |
| `eq_tol_atr` | 0.1 | 0–5 | Dung sai bằng giá giữa hai swing cấu trúc cùng phía, × ATR — **do lab chọn** |
| `gap_policy` | `giu_muc_chan_cua_so` | hoặc `giu_muc_khong_chan` | D1. Bản «không chặn» chỉ để đối chiếu với `swing_pivot` / `swing_hierarchy` |

Mặc định là cấu hình thí nghiệm (AGENTS §5.2), đổi khi có nhãn (D8) và qua vòng ⑦–⑧.

## 4. Quy tắc

### 4.1. Thứ tự trong một nến t (cố định)

1. **[G]** Kiểm nến (giá hữu hạn, OHLC hợp lệ, đúng khung, index và thời gian tăng). Khoảng trống
   giữa nến trước và t → phân loại → `ICT_GAP` tại t.
2. **[A]** ATR\[t−1\] là ngưỡng cho mọi so sánh ở nến t.
3. **[S2]** close\[t\] so với mức được bảo vệ đã biết **trước** t → bật cờ `protected_broken`.
4. **[S4]** Dealing range mở rộng theo high/low của t.
5. **[P1]** Pivot xác nhận tại t → **[S1]** cấp 2 → cấp 3 → với swing ở cấp cấu trúc: **[S2]** so
   sánh, thứ tự, mức được bảo vệ; **[S4]** đặt mốc mới. Có hiệu lực từ t+1 (close\[t\] không bao giờ
   bị so với mức vừa biết ở chính t).
6. **[A]** Cập nhật ATR\[t\].

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

Chính sách (D1): **giữ** mọi mức swing/dealing range qua mọi khoảng trống; **chặn** cửa sổ pivot vắt
qua khoảng trống (mọi loại, kể cả nghỉ phiên). Không tự lấp nến; khoảng trống bất thường không bị gộp
thành Range/Uncertain (AGENTS §2.2).

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
  `order` — đổi hướng chỉ đến từ shift (giai đoạn 2).

### 4.6. [S4] Dealing range

`range_hi` = max(đỉnh cấu trúc gần nhất, high cao nhất từ nến cực trị của đỉnh đó tới nến hiện tại);
`range_lo` đối xứng. Mở rộng dần theo từng nến; đặt lại khi có đỉnh/đáy cấu trúc mới. Vì gồm cả nến
hiện tại, dealing range **luôn chứa close** → `zone` (premium > EQ > discount) và
`range_pos = (close − lo)/(hi − lo)` ∈ [0, 1] luôn xác định khi đã có cả hai mốc.

## 5. Thời điểm biết

| Đầu ra | Nến sự kiện | Biết lúc |
|---|---|---|
| STH/STL | nến c (cực trị) | close nến `c + pivot_right` |
| ITH/ITL | nến của STH ở giữa | close nến xác nhận STH bên phải |
| LTH/LTL | nến của ITH ở giữa | close nến xác nhận ITH bên phải |
| `ICT_GAP` | nến đầu tiên sau khoảng trống | chính nến đó |
| `order`, mức được bảo vệ, dealing range (timeline) | — | trạng thái **sau** nến t; dùng để so từ t+1 |

## 6. Chỗ mơ hồ đã chọn

| Chỗ | Chọn | Ảnh hưởng |
|---|---|---|
| Hai đỉnh bằng giá | Strict — không phải pivot (D15); EQH chỉ ở tầng so sánh, theo dung sai | Nhất quán với `swing_pivot`; biến thể không strict để v0.2 |
| ATR chưa đủ nến khi so hai swing | **Chưa so** (`hh`/`hl` = None, «ATR chưa đủ nến») — không ép dung sai 0 | Chỉ đầu dataset/khoảng chạy. Survey-v2 dùng dung sai 0 khi chưa có ATR |
| Close đúng bằng mức được bảo vệ | Không tính là vượt | — |
| Mức được bảo vệ đổi sang swing khác cùng giá | Xoá cờ vượt (mức mới) | Survey-v2 so theo giá nên giữ cờ khi cùng giá — hiếm |
| ATR qua khoảng trống | Không reset; TR nối qua khoảng trống gồm bước nhảy | Khác `dc_atr_structure` (reset mỗi segment) — vì mức được giữ qua khoảng trống |
| Nến nằm ngoài giờ phiên (vd dữ liệu mô phỏng 24/7) | Không chặn gì; chỉ đếm và cảnh báo khi > 20% số nến | Số «mỗi ngày» kém tin cậy với dữ liệu không theo lịch |
| Tỷ lệ thời gian (thứ tự, mức bị vượt) | Đếm trạng thái **sau** mỗi nến (như timeline) | Survey-v2 đếm trước khi áp swing xác nhận ở nến đó: «mức bị vượt / tổng nến» 0.120 so với 0.107 ở đây — cùng logic, đã kiểm (§8) |

## 7. Sự kiện và trường dữ liệu

| Loại | Lý do | `details` chính |
|---|---|---|
| `SWING_HIGH` / `SWING_LOW` (STH/STL) | `PIVOT_HIGH_STRICT` / `PIVOT_LOW_STRICT` | `cap`=1, `trai`/`phai`, `chan_cua_so_qua_gap` |
| `SWING_HIGH_L2` / `SWING_LOW_L2` (ITH/ITL) | `PIVOT_HIGH_L2` / `PIVOT_LOW_L2` | `basis` (3 STH), giá/nến của ba swing; nếu là cấp cấu trúc: `so_sanh`, `nhan` (HH/LH/EQH, HL/LL/EQL), `gia_truoc`, `chenh_lech`, `dung_sai`, `atr_luc_xac_nhan`, `order_sau`, `muc_bao_ve_sau` |
| `SWING_HIGH_L3` / `SWING_LOW_L3` (LTH/LTL) | `PIVOT_HIGH_L3` / `PIVOT_LOW_L3` | như cấp 2, `basis` = 3 ITH/ITL |
| `ICT_GAP` | `GAP_NGHI_PHIEN` / `GAP_CUOI_TUAN` / `GAP_NGHI_LE` / `GAP_THIEU_TRONG_PHIEN` / `GAP_NGOAI_LICH` / `GAP_KHONG_RO_LICH` | `loai`, `bat_thuong`, `tu`, `den`, `so_o_thieu`, `so_o_trong_phien`, `lich_phien`, `chinh_sach` |

`event_id`: `ict:<loại>@<nến sự kiện>><nến xác nhận>`; khoảng trống `ict:ICT_GAP@<nến>`. Một sự kiện
cho một cấu trúc — nhãn HH/LH… nằm trong `details` (AGENTS §5.1). ITH/ITL dùng chung loại với
`swing_hierarchy` nên chấm được với mục tiêu **Swing cấu trúc (cấp 2)** sẵn có.

Timeline mỗi nến: `order`, `protected`, `protected_side`, `protected_id`, `protected_broken`,
`dealing_hi`, `dealing_lo`, `dealing_eq`, `dealing_id`, `zone`, `range_pos`, `atr`, `gap`.

## 8. Đối chiếu survey-v2 (đoạn phát triển 01/01–31/08/2024, XAUUSD M15 `ds_db1583cd4dde`)

Survey là bản mẫu định nghĩa, không phải chuẩn đúng (plan §10). Chạy lại bằng lõi (05/10/2026):

| Đo | Survey-v2 | `ict_structure` 0.1.0 |
|---|---:|---:|
| Số nến / ngày giao dịch | 15 850 / 173 | 15 850 / 173 |
| Khoảng trống nghỉ phiên / cuối tuần / lễ / thiếu trong phiên | 133 / 32 / 6 / 1 | 133 / 32 / 6 / 1 (thiếu: 12/01/2024, 16 ô) |
| STH + STL mỗi ngày | 40.4 | 40.4 |
| ITH + ITL mỗi ngày (chặn gap) | 10.2 | 10.22 |
| Thứ tự +1 / −1 / lẫn lộn / chưa có | 30.0% / 22.1% / 47.7% / 0.2% | 30.0% / 22.1% / 47.7% / 0.2% |
| Đang ±1 nhưng mức được bảo vệ đã bị close vượt (/ tổng nến) | 12.0% | 10.7% (đếm sau nến); 12.0% khi đếm như survey (§6) |

Hiệu năng (một luồng, Python): M15 2018–2025 (189 073 nến) 1.8 s; M1 2024 (355 652 nến) 5.3 s —
tuyến tính theo số nến.

## 9. Giới hạn và việc để sau

* **Giai đoạn 2:** displacement, FVG M15, vòng đời thanh khoản (chạm → lấy → sweep/run), shift +
  `SHIFT_FVG`, killzone, khung «Thuật toán đang làm gì» cho chuỗi quét → displacement → FVG.
* **Giai đoạn 3:** khung lớn H1/H4 gộp `ny_1700` (D10), PDH/PDL/PWH/PWL làm vùng thanh khoản (D13),
  phản ứng PD array (D6), DOL (D7), lớp phủ H4.
* `swing_source = dc` (biến thể D2) và `min_leg_atr` (plan §4.2) **chưa cài** — `min_leg_atr` cần định
  nghĩa chính xác trước.
* Chưa có loại nhãn tay cho shift; nhãn ITH/ITL dùng «Đỉnh/Đáy cấp 2».
* Chưa có nhãn tham chiếu (D8) → chưa có F1; thống kê là mô tả hành vi.

## 10. Kiểm thử

`tests/algorithms/test_ict_structure.py` (17 test) và `tests/api/test_ict_structure_api.py` (4 test):

* tính tay: STH/STL strict, outside bar, hai high bằng nhau; ITH xác nhận khi STH phải xác nhận (basis,
  reference); cấp 3 chỉ khi bật và lọc trên ITH;
* thứ tự / mức được bảo vệ đúng ví dụ plan (ITL 100 → 105, close 104 → cờ vượt, thứ tự vẫn +1), HH + LL
  → lẫn lộn và mất mức, EQH trong dung sai, ATR chưa đủ → chưa so;
* dealing range chứa close; timeline: `lo ≤ close ≤ hi`, `range_pos` ∈ [0, 1], có mức bảo vệ ⇔ thứ tự ±1;
* khoảng trống theo lịch CME thật: nghỉ hằng ngày, cuối tuần, thiếu trong phiên (đếm ô), ngoài lịch,
  không chọn lịch; cửa sổ pivot vắt qua khoảng trống bị chặn; `auto` → lịch theo mã;
* **tương đương** (3 chuỗi ngẫu nhiên có khoảng trống và giá bằng nhau): STH/STL = `swing_pivot(1,1)`,
  ITH/ITL = `swing_hierarchy(1,1)` khi tắt chặn; bản chặn là tập con;
* **nhân quả**: prefix = full lọc theo nến xác nhận ở nhiều điểm cắt (cấp 2 và 3); sửa mọi nến sau T
  không đổi sự kiện và timeline tới T; sự kiện đã trả không bị sửa ngầm; tất định; dữ liệu sai bị từ chối;
* API: đăng ký, `auto` → `cme_globex_metals`, lưu → mở lại → CSV/manifest, replay tiến/lùi, sai khung → 400,
  chấm ITH/ITL với mục tiêu Swing cấu trúc.
