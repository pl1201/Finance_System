# Đặc tả thuật toán Swing theo persistence (ba cấp, ngưỡng ATR)

**Mã thuật toán:** `swing_persistence` · **Phiên bản dự kiến:** `0.1.0` · Ngày: 22/10/2026

**Trạng thái: bản nháp đặc tả — chờ duyệt, chưa có code** (bước ② của [`AGENTS.md`](../../AGENTS.md) §3). Các câu
hỏi cần chốt ở §13. Sau khi duyệt mới code (bước ③), viết test (④), chạy trên dữ liệu thật (⑤).

File dự kiến (chưa tạo): `core/components/persistence_source.py` (thành phần), `core/algorithms/swing_persistence/`
(thuật toán), `core/vocab/persistence.py` (mã lý do), `tests/algorithms/test_swing_persistence.py`.

Đây là **một nguồn swing thay thế** để nghiên cứu, không phải phương pháp ICT, không phải tín hiệu. Mọi ngưỡng là
**cấu hình thí nghiệm do lab chọn**. Chưa có nhãn tham chiếu nên chưa có số đo độ chính xác.

Nguồn: báo cáo `D:\Finance_System\reports\Định nghĩa cấu trúc thị trường.md` và ghi chú
`D:\Finance_System\research_notes\Định nghĩa cấu trúc thị trường\academic_quant.md` §2.

---

## 0. Tóm tắt

Pivot (STH/STL) chọn đỉnh/đáy theo **số nến**: nến cao hơn hai nến bên cạnh. Persistence chọn theo **biên độ giá**:
một đỉnh chỉ được tính khi giá đã đi ngược ít nhất R ở **cả hai phía** của nó, trước khi có đỉnh cao hơn. Đặt ba
ngưỡng R₁ < R₂ < R₃ (mặc định 1×, 3×, 9× ATR) là có ba cấp swing lồng nhau, không cần bước lồng pivot kiểu
Larry Williams.

| | Pivot 1/1 + Williams (`ict_structure`) | DC-ATR (`dc_atr_structure`) | Persistence (đặc tả này) |
|---|---|---|---|
| Giá | high/low | close | high/low |
| Tiêu chí | số nến | đảo chiều ≥ Δ từ cực trị đang chạy | đi ngược ≥ R ở **cả hai phía** |
| Phân cấp | lồng pivot (ITH = STH có STH thấp hơn hai bên) | một ngưỡng mỗi lần chạy | ba ngưỡng, **tự lồng nhau** |
| Trễ xác nhận | cấp 1: 1 nến; cấp 2–3: không giới hạn trên | khi giá đi hết Δ | khi giá đi hết R của cấp đó |

Tầng 2–3 (HH/HL, phá mức, trend/range) **không** nằm trong bản này.

## 1. Phiên bản

| Phiên bản | Ngày | Nội dung |
|---|---|---|
| 0.1.0 (dự kiến) | — | Bản đầu theo đặc tả này |

Thuật toán mới, chỉ thêm loại mã lý do và mục registry: output của mọi thuật toán khác phải giữ nguyên (hồi quy
run đã lưu, §11).

## 2. Tầng, đầu vào, đầu ra

| | |
|---|---|
| Tầng ([`kien_truc_luong_ict.md`](../guides/kien_truc_luong_ict.md) §2) | **P1 + S1** gộp một: swing và cấp của nó đến cùng lúc, không qua bước lồng. Thay được cho `swing_source` + `hierarchy` (§10) |
| Đầu vào | Nến **một khung** (khuyến nghị M15), đã đóng, theo thứ tự; lịch phiên khai báo `data/calendars/` để phân loại khoảng trống |
| Đầu ra | Sự kiện swing ba cấp, sự kiện khoảng trống, `timeline_point`, `pending_state`, `run_stats` (§6) |
| Không làm | HH/HL/LH/LL, BOS/CHoCH, vùng thanh khoản, trend/range; không sửa `ict_structure` |

## 3. Tham số

| Tham số | Mặc định | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| `timeframe` | M15 | khớp dataset | Bước nến để phân loại khoảng trống (giống `ict_structure`) |
| `session_calendar` | `auto` | `auto` · `cme_globex_metals` · `fx_spot` · `none` | Như `ict_structure` §3 |
| `atr_period` | 14 | int 2–500 | ATR Wilder, seed = trung bình `period` TR đầu có close trước (`WilderATRPrevClose`, như `ict_structure`) |
| `nguong_cap1_atr` | 1.0 | > 0 | R₁ = hệ số × ATR khoá (§4.3) |
| `nguong_cap2_atr` | 3.0 | > `nguong_cap1_atr` | R₂ |
| `nguong_cap3_atr` | 9.0 | > `nguong_cap2_atr`, ≤ 100 | R₃ |
| `thu_tu_trong_nen` | `duong_oc` | `duong_oc` · `loai_tru` | Cách xử lý thứ tự high/low trong một nến (§4.1) |
| `gap_policy` | `giu_gan_co` | `giu_gan_co` · `reset_bat_thuong` | Xử lý khoảng trống (§4.6) |

Validate như `dc_atr_structure`: số hữu hạn, đúng kiểu, ràng buộc liên trường (R₁ < R₂ < R₃), từ chối tham số lạ.
Hệ số 1/3/9 (bội 3) là lựa chọn của lab, chưa có nguồn cho con số 3; bước ⑤ khai trước một biến thể «cùng mật độ»
hiệu chỉnh trên đoạn phát triển (§12).

**Warm-up:** `atr_period + 1` nến. Nến trước đó vẫn vào đường giá (làm biên và đoạn giá cho cực trị sau), chỉ
không thể là ứng viên vì chưa có ngưỡng.

## 4. Quy tắc

### 4.1. Đường giá trong nến (`thu_tu_trong_nen`)

OHLC không cho biết high hay low xảy ra trước. Persistence cần thứ tự đó khi một nến chứa cả cực trị lẫn phần đi
ngược của nó.

**`duong_oc` (mặc định).** Mỗi nến t thành **hai điểm** trên đường giá, theo hướng open → close — đúng quy tắc
Larry Williams dùng cho outside day: «the way price moved from the opening of the day to the close»
([*Long-Term Secrets to Short-Term Trading*, Wiley 1999, ch. 1](https://catalogimages.wiley.com/images/db/pdf/0471297224.pdf)):

| Nến | Thứ tự hai điểm |
|---|---|
| `close > open` | `low`, rồi `high` |
| `close < open` | `high`, rồi `low` |
| `close = open` | cực trị gần `open` hơn trước; cách đều → `low` trước |

Open và close nằm trong [low, high] nên không phải cực trị — bỏ qua mà không đổi kết quả. Cực đại cục bộ của đường
luôn là `high` của một nến, cực tiểu luôn là `low` (đã kiểm, §8). Giữa hai nến, đường nhảy thẳng từ điểm cuối nến
trước sang điểm đầu nến sau; **không** thêm điểm nào cho khoảng trống.

**`loai_tru` (biến thể đối chứng).** Không giả định thứ tự: đỉnh dùng `high`, phần đi ngược dùng `low`, và
**loại khỏi phép tính** mọi nến mà thứ tự có thể đổi kết quả — nến cực trị, nến biên trái, nến vượt cực trị (§4.2).

### 4.2. Persistence của một cực trị

Viết cho đỉnh; đáy đối xứng (đổi ≥ ↔ ≤, min ↔ max, «cao hơn» ↔ «thấp hơn»).

Gọi p₀, p₁, … là các điểm của đường giá (`duong_oc`). Với đỉnh tại điểm i:

* **Biên trái** a = điểm j < i gần nhất có `p_j ≥ p_i`. Không có (đầu dữ liệu, hoặc ngay sau reset) → **biên trái
  bị cắt** (`bien_trai_cat`), lấy từ điểm đầu đoạn.
* **Đoạn trái** `D_trái = p_i − min{p_j : a < j < i}`. Tập rỗng → `D_trái = 0`, tức điểm này không bao giờ là
  ứng viên (điểm liền trước cao hơn hoặc bằng).
* **Bị vượt** tại điểm đầu tiên u > i có `p_u > p_i` (nghiêm ngặt). Từ đó đỉnh i dừng.
* **Đoạn phải** tới điểm u (chưa bị vượt) `D_phải(u) = p_i − min{p_j : i < j ≤ u}`. Không giảm theo u.
* **Persistence** tới u: `min(D_trái, D_phải(u))`.

**`loai_tru`** — cùng định nghĩa trên nến thay cho điểm. Với đỉnh tại nến m:
`a = nến j < m gần nhất có high_j ≥ high_m`; `D_trái = high_m − min{low_j : a < j < m}`;
`D_phải(t) = high_m − min{low_j : m < j ≤ t}`, chỉ khi `high_j ≤ high_m` với mọi m < j ≤ t. Nến vượt (high > high_m)
không đóng góp low của nó.

Đây là persistence bậc 0 (độ nổi bật, *prominence*) của cực trị; survey của Chiarot & Silvestri mô tả «important
extrema» của Fink theo cùng ý ([arXiv 2101.08784](https://arxiv.org/abs/2101.08784); bài gốc chưa đối chiếu được
toàn văn). Lab dùng định nghĩa trên, không phụ thuộc vào việc tương đương đó.

### 4.3. Cấp và ngưỡng

* **Ngưỡng khoá tại nến cực trị:** `R_k = nguong_capk_atr × ATR[m−1]`, m = nến chứa cực trị. ATR đã biết **trước**
  nến m — cùng quy ước «ATR khoá» của vùng thanh khoản (`ict_structure` D4). Khác DC-ATR (khoá ATR[e], tính cả nến
  cực trị). ATR đổi về sau không đổi R.
* **Cấp tối đa** `k_max = max{k : D_trái ≥ R_k}` — biết ngay tại cực trị. `k_max = 0` → không phải ứng viên.
* Cực trị là **swing cấp k** tại điểm u đầu tiên (chưa bị vượt) mà `D_phải(u) ≥ R_k` và `k ≤ k_max`.
  **Chạm đúng ngưỡng là đạt** (≥), như DC và «lấy» thanh khoản.
* Cấp k chỉ đạt sau cấp k−1 (cùng điểm hoặc muộn hơn): một swing cấp 3 có đủ ba sự kiện cấp 1, 2, 3 cùng
  `event_time`, `confirmed_at` không giảm.
* `ATR[m−1]` chưa có hoặc ≤ 0 → không phải ứng viên (đếm `atr_chua_co`).

### 4.4. Tính trực tuyến và thứ tự trong một nến t

Mỗi phía giữ một **ngăn xếp** các điểm chưa bị vượt, giá không tăng từ đáy lên đỉnh, kèm min của các điểm nằm
giữa hai phần tử kề nhau («khe»). Mỗi điểm vào ngăn xếp một lần và ra tối đa một lần → O(1) khấu hao mỗi điểm.
Ứng viên còn chờ lên cấp nằm trong tập **theo dõi**; ứng viên đạt `k_max` rời tập này nhưng vẫn ở ngăn xếp (làm biên
cho điểm sau).

Thứ tự cố định trong nến t:

1. **[G]** Kiểm nến (giá hữu hạn, OHLC hợp lệ, đúng khung, `index` và thời gian tăng) — sai → `ValueError` như
   `ict_structure`. Khoảng trống trước t → phân loại theo lịch → `PERSIST_GAP` (§4.6).
2. **[A]** Đọc `ATR[t−1]` làm ngưỡng cho ứng viên mới ở nến t.
3. **[W]** Dựng hai điểm của nến t (§4.1). Với **từng điểm** theo thứ tự, phía đỉnh rồi phía đáy:
   1. **Vượt:** lấy khỏi ngăn xếp mọi phần tử có giá < điểm (phía đáy: >). Chúng dừng; giá trị persistence cuối vào
      phổ của `run_stats`, không phát sự kiện.
   2. **Xác nhận:** mọi ứng viên còn sống trong tập theo dõi cập nhật đoạn phải bằng điểm này; đạt cấp mới → sự kiện.
      Nhiều cấp cùng lúc → phát theo cấp tăng dần.
   3. **Ứng viên mới:** đoạn trái của điểm = giá − min của {khe của biên trái; giá và khe của mọi phần tử vừa lấy
      ra} (phía đáy: max, đổi dấu); khe của biên trái nhận luôn min đó; đẩy điểm vào ngăn xếp với khe rỗng;
      `k_max ≥ 1` → vào tập theo dõi.
4. **[A]** Cập nhật `ATR[t]` bằng nến t.
5. `timeline_point`, `pending_state` sau t.

`loai_tru` chạy bước 3 một lần mỗi nến: phía đỉnh vượt bằng `high[t]`, xác nhận bằng `low[t]`, ứng viên mới là
`high[t]`; phía đáy đối xứng.

Sự kiện trong một nến xếp theo (thứ tự điểm, phía đỉnh trước, cấp tăng dần, vị trí cực trị) — tất định.

### 4.5. Điều kiện biên

| Trường hợp | Quy tắc |
|---|---|
| Đoạn phải = R đúng | Đạt |
| Hai đỉnh **bằng giá** | Nến **sớm hơn** thắng: đỉnh sau có biên trái là đỉnh trước (≥) nên chỉ đo được khoảng hở giữa hai đỉnh; đỉnh sau không vượt đỉnh trước (vượt là >). Cờ `bang_dinh_truoc` trên đỉnh sau. Khác pivot strict (D15: bằng giá → không là pivot) |
| Chuỗi nến cùng high (plateau) | Nến đầu chuỗi là cực trị (hệ quả của dòng trên) |
| Outside bar | Có thể vừa là swing đỉnh vừa là swing đáy, như pivot của lab |
| Xác nhận ngay trong nến cực trị (`duong_oc`) | Được — trễ 0 nến, vd nến giảm mà `high − low ≥ R` sau một đoạn trái đủ dài. Cờ `dua_vao_thu_tu_nen` |
| Cùng nến vừa xác nhận vừa vượt (`duong_oc`) | Theo thứ tự điểm: nến tăng có low (xác nhận) trước high (vượt) → vẫn xác nhận, cờ `bi_vuot_cung_nen`. `loai_tru`: nến vượt không đóng góp → không xác nhận |
| Biên trái bị cắt | Vẫn xét, đoạn trái tính từ đầu đoạn (nhỏ hơn hoặc bằng thật) — cờ `bien_trai_cat`; khi chấm có thể loại |
| Cuối dữ liệu | Ứng viên đang chờ chỉ nằm trong `pending_state`, không bao giờ thành sự kiện hay vào chỉ số |
| Xen kẽ đỉnh/đáy | **Không ép.** Ngưỡng hằng + `duong_oc` thì tự xen kẽ (§8); ATR đổi giữa hai swing thì có thể vỡ — đếm trong `run_stats` |

### 4.6. Khoảng trống (`gap_policy`)

Phân loại bằng `GapClassifier` + lịch phiên, như `ict_structure` §4.2: `nghi_phien`, `cuoi_tuan`, `nghi_le` (đóng
cửa theo lịch), `thieu_trong_phien`, `lech_buoc` (**bất thường**), `ngoai_lich`, `khong_ro_lich` (không phân loại).
Mỗi khoảng trống phát một `PERSIST_GAP` ở nến đầu sau nó.

* **`giu_gan_co` (mặc định):** giữ mọi ứng viên, ngăn xếp, ATR qua mọi khoảng trống — cùng tinh thần «giữ mức»
  của `ict_structure` D1. Đóng cửa theo lịch không có giao dịch nên không có đỉnh/đáy bị che. Mỗi swing ghi số khoảng
  trống theo loại nằm trong **đoạn quyết định** của nó (từ nến của điểm đoạn trái tới nến xác nhận); có khoảng trống
  bất thường → `qua_bat_thuong = true` để khi chấm có thể loại.
* **`reset_bat_thuong`:** khoảng trống bất thường → bỏ mọi ứng viên, xoá ngăn xếp, sang **đoạn** mới (`phan_doan`
  + 1, biên trái bị cắt từ đó). ATR giữ nguyên. Khoảng trống theo lịch vẫn giữ như trên.

**Không** có chính sách reset ở mọi khoảng trống như DC (`gap_policy=reset`): nghỉ phiên hằng ngày của XAUUSD sẽ cắt
mọi swing dài hơn một phiên, nên cấp 2–3 gần như không thể hình thành (DC §8: «Chưa rõ» 66–91% vì đoạn trung vị
chỉ 92 nến).

## 5. Thời điểm biết

* `event_time` = nến chứa cực trị; `confirmed_at` = `close_time` của nến chứa điểm làm đoạn phải đạt R_k.
* Trễ ≥ 0 nến (0 chỉ có ở `duong_oc`, §4.5). Không có giới hạn trên: giá chưa đi ngược đủ thì chưa biết.
* Mọi so sánh ở nến t chỉ dùng điểm của nến ≤ t và `ATR[m−1]` đã khoá. Sự kiện đã phát không bao giờ sửa hay thu
  hồi: đoạn phải chỉ tăng, nên «persistence ≥ R» đã đúng thì đúng mãi. Giá trị persistence **cuối** chỉ biết khi
  cực trị bị vượt — không phát thành sự kiện (sẽ thành sự kiện thứ hai cho cùng cực trị, matcher đếm trùng),
  chỉ vào phổ `run_stats`.

## 6. Sự kiện và dữ liệu đầu ra

### 6.1. Loại sự kiện

Dùng lại loại swing có sẵn — theo tiền lệ `ict_structure` (STH/ITH/LTH dùng `SWING_HIGH` / `_L2` / `_L3`), để các
mục tiêu chấm «Swing nhỏ (cấp 1)» và «Swing cấu trúc (cấp 2)» dùng được ngay. Phân biệt bằng `algorithm` và
`reason_code` (câu hỏi Q3, §13).

| `structure_type` | `reason_code` (họ mới `persistence`) | `direction` |
|---|---|---|
| `SWING_HIGH` / `SWING_LOW` | `PERSIST_HIGH_L1` / `PERSIST_LOW_L1` | `up` / `down` (quy ước `swing_pivot`) |
| `SWING_HIGH_L2` / `SWING_LOW_L2` | `PERSIST_HIGH_L2` / `PERSIST_LOW_L2` | như trên |
| `SWING_HIGH_L3` / `SWING_LOW_L3` | `PERSIST_HIGH_L3` / `PERSIST_LOW_L3` | như trên |
| `PERSIST_GAP` (loại mới) | `PERSIST_GAP_GIU` / `PERSIST_GAP_RESET` | — |

* `price` = high (đỉnh) / low (đáy) của nến cực trị.
* `event_id = ps:s{phan_doan}:{TYPE}@{nến cực trị}>{nến xác nhận}`; `PERSIST_GAP`: `ps:s{phan_doan}:PERSIST_GAP@{nến}`.
  Tất định, không phụ thuộc độ dài dataset.
* `reference_event_id`: cấp k ≥ 2 trỏ tới sự kiện cấp k−1 của cùng cực trị; cấp 1 = `null`.

### 6.2. `details` của swing (số thực đã dùng để quyết định)

| Khoá | Nội dung |
|---|---|
| `cap`, `phia` | 1–3; `high` / `low` |
| `he_so_atr`, `atr_khoa`, `nguong` | hệ số cấp k, `ATR[m−1]`, `R_k` (giá) |
| `doan_trai`, `doan_trai_atr`, `diem_trai` | đoạn trái (giá, đơn vị ATR khoá), `{gia, nen}` của điểm đối diện tạo nó |
| `bien_trai`, `bien_trai_cat` | nến biên trái (`null` nếu bị cắt) |
| `doan_phai`, `doan_phai_atr`, `diem_phai` | đoạn phải lúc xác nhận, `{gia, nen}` của điểm làm đạt ngưỡng |
| `cap_toi_da` | `k_max` theo đoạn trái |
| `cong_thuc` | vd `"min(trái 6,50; phải 6,50) ≥ 3 × 2,00 = 6,00"` |
| `tre_nen`, `tre_giay` | `confirmed_bar_index − event_bar_index`; theo giây |
| `thu_tu_trong_nen`, `dua_vao_thu_tu_nen`, `bi_vuot_cung_nen` | chế độ §4.1; kết quả có phụ thuộc thứ tự giả định trong nến không — đúng khi điểm đoạn trái nằm trong nến cực trị hoặc nến biên trái, điểm xác nhận nằm trong nến cực trị, hoặc nến xác nhận cũng vượt cực trị (`loai_tru`: luôn sai); cờ §4.5 |
| `bang_dinh_truoc` | biên trái có đúng cùng giá (§4.5) |
| `khoang_trong`, `qua_bat_thuong`, `phan_doan` | số khoảng trống theo loại trong đoạn quyết định; có loại bất thường không; đoạn |

`PERSIST_GAP`: `loai`, `bat_thuong`, `tu`, `den`, `so_o_thieu`, `so_o_trong_phien`, `lich_phien`, `chinh_sach`,
`ung_vien_bi_bo` (khi reset).

### 6.3. Timeline, pending, thống kê

* **`timeline_point`:** `muc_high_c1` … `muc_low_c3` — giá swing gần nhất **đã xác nhận** mỗi phía mỗi cấp
  (`null` nếu chưa có). Không tô ngược.
* **`pending_state`:** đoạn, ATR, chế độ; tối đa 6 ứng viên gần đạt cấp kế nhất
  (`phia, nen, gia, cap_da_dat, cap_toi_da, doan_trai_atr, doan_phai_atr, nguong_ke_tiep, con_thieu`); cỡ hai
  ngăn xếp — đủ cho khung «Thuật toán đang làm gì» sau này.
* **`run_stats`:** số swing và mật độ /1000 nến theo cấp × phía; trễ trung vị / P90 / max theo cấp; tỷ lệ trễ 0;
  tỷ lệ `dua_vao_thu_tu_nen`; số lần **không xen kẽ** theo cấp (hai swing liên tiếp cùng phía, xếp theo
  `event_time`); `bien_trai_cat`; `qua_bat_thuong`; khoảng trống theo loại; ngăn xếp / tập theo dõi lớn nhất;
  phổ persistence cuối của mọi cực trị đã bị vượt (đơn vị ATR khoá, các ô 0–0,5 · 0,5–1 · 1–2 · 2–3 · 3–5 · 5–9 · ≥ 9).
* **`manifest_info`:** nguồn (§4.1, §4.2), «không phải ICT», chế độ và chính sách đang dùng.

## 7. Ví dụ tính tay

Giả sử `ATR[m−1] = 2,0` ở mọi nến (bỏ qua warm-up), hệ số cấp 1 = 1, cấp 2 = 3 → R₁ = 2,0, R₂ = 6,0.

| Nến | O | H | L | C | Hướng | Hai điểm (`duong_oc`) |
|---:|---:|---:|---:|---:|---|---|
| 0 | 100,0 | 101,0 | 99,5 | 100,5 | tăng | 99,5 → 101,0 |
| 1 | 100,5 | 102,0 | 100,0 | 101,8 | tăng | 100,0 → 102,0 |
| 2 | 101,8 | **104,5** | 101,5 | 104,0 | tăng | 101,5 → 104,5 |
| 3 | 104,0 | 104,2 | 101,0 | 101,5 | giảm | 104,2 → 101,0 |
| 4 | 101,5 | 102,5 | 100,0 | 100,4 | giảm | 102,5 → 100,0 |
| 5 | 100,4 | 101,0 | 97,8 | 98,2 | giảm | 101,0 → 97,8 |
| 6 | 98,2 | 99,0 | **97,0** | 98,8 | tăng | 97,0 → 99,0 |
| 7 | 98,8 | **103,5** | 98,5 | 103,2 | tăng | 98,5 → 103,5 |
| 8 | 103,2 | 103,4 | 101,2 | 101,5 | giảm | 103,4 → 101,2 |
| 9 | 101,5 | 105,0 | **101,0** | 104,8 | tăng | 101,0 → 105,0 |

Kết quả `duong_oc`:

| Xác nhận tại nến | Sự kiện | Cực trị | Đoạn trái | Đoạn phải lúc xác nhận | Trễ | Ghi chú |
|---:|---|---|---|---|---:|---|
| 3 | `SWING_HIGH` | 104,5 (nến 2) | 104,5 − 99,5 = 5,0 (cắt) | 104,5 − 101,0 = 3,5 ≥ 2 | 1 | `k_max` = 1 vì 5,0 < 6 |
| 6 | `SWING_LOW` | 97,0 (nến 6) | 104,5 − 97,0 = 7,5 (cắt) | 99,0 − 97,0 = 2,0 ≥ 2 | **0** | chạm đúng ngưỡng; `dua_vao_thu_tu_nen` (nến tăng: low trước high) |
| 7 | `SWING_LOW_L2` | 97,0 (nến 6) | 7,5 | 103,5 − 97,0 = 6,5 ≥ 6 | 1 | `reference_event_id` → sự kiện ở nến 6 |
| 8 | `SWING_HIGH` | 103,5 (nến 7) | 103,5 − 97,0 = 6,5 | 103,5 − 101,2 = 2,3 ≥ 2 | 1 | `k_max` = 2; bị 105,0 vượt ở nến 9 khi đoạn phải mới 2,5 → dừng ở cấp 1 |
| 9 | `SWING_LOW` | 101,0 (nến 9) | 103,5 − 101,0 = 2,5 | 105,0 − 101,0 = 4,0 ≥ 2 | **0** | biên trái = low 98,5 (nến 7); `dua_vao_thu_tu_nen` |

Cuối dữ liệu: đỉnh 105,0 (nến 9, đoạn trái 8,0, `k_max` = 2) đang chờ, chỉ ở `pending_state`. Các cực trị khác không
đủ đoạn trái (vd đáy 101,0 nến 3: đoạn trái 3,5 nhưng bị 100,0 vượt khi đoạn phải mới 1,5). Đỉnh/đáy xen kẽ ở cấp 1:
H (2) – L (6) – H (7) – L (9).

**`loai_tru`** cùng dữ liệu: đáy 97,0 xác nhận cấp 1 **và** cấp 2 cùng ở nến 7 (nến 6 không được tính cho chính nó);
đáy 101,0 nến 9 chưa xác nhận. Còn lại giống hệt.

**So với pivot 1/1** (STH/STL của `ict_structure`): STH nến 2, STL nến 6, STH nến 7 — cùng vị trí nhưng STL 97,0 biết ở
nến 7, và chưa có ITH/ITL nào (cần STH thứ ba bên phải). Persistence cấp 2 đã biết đáy 97,0 là swing lớn ở nến 7.

Ví dụ này đã chạy lại bằng bản mẫu (§8) cho đúng các sự kiện trên ở cả hai chế độ; sẽ thành test tính tay.

## 8. Tính chất đã kiểm bằng bản mẫu (MÔ PHỎNG)

Bản mẫu Python thuần viết trước đặc tả để kiểm các khẳng định, chạy trên dữ liệu **mô phỏng** (random walk Gauss, râu
nến ngẫu nhiên). Không phải code của lab; các phép kiểm thành test ở bước ④.

| # | Kiểm | Kết quả |
|---|---|---|
| 1 | Bản trực tuyến (ngăn xếp) = định nghĩa §4.2 tính lại toàn bộ (vét cạn), ngưỡng đổi theo nến, có warm-up | `loai_tru` 300/300, `duong_oc` 300/300 chuỗi khớp |
| 2 | Chuỗi một giá (H = L = C), ngưỡng hằng δ: swing cấp 1 = đỉnh/đáy DC(δ) cổ điển, **cả nến xác nhận** (sau cực trị DC đầu) | 500/500 khớp |
| 3 | `duong_oc`, ngưỡng hằng: persistence = DC chạy trên chính đường hai điểm/nến; cực trị luôn là high/low của nến | 300/300 khớp; không lần nào sai |
| 4 | Xen kẽ, ngưỡng hằng 2,0 ≈ một biên độ nến | `duong_oc` 0 / 62 830 swing vi phạm; `loai_tru` 7 656 / 46 678 (16,4%) |
| 5 | Xen kẽ, ngưỡng 1/3/9 × ATR(14), biến động đổi theo «phiên» (`duong_oc`, 100 000 nến) | không xen kẽ: cấp 1 1 016 / 45 599 (2,2%), cấp 2 448 / 4 415 (10,1%), cấp 3 82 / 403 (20,3%) |
| 6 | Trễ 0 (`duong_oc`, ngưỡng ≈ một biên độ nến) | 36% số swing — phần phụ thuộc giả định thứ tự trong nến |
| 7 | Quy mô: 200 000 nến, 1/3/9 × ATR | ~1,5 giây; tập theo dõi ≤ 4; ngăn xếp tới ~70 000 phần tử khi trend một chiều rất mạnh (bộ nhớ O(n) xấu nhất, thời gian O(1) khấu hao) |
| 8 | Mật độ trên random walk, 1/3/9 × ATR(14) | ≈ 459 / 41 / 3,8 swing mỗi 1 000 nến (đỉnh + đáy) |

Đọc nhanh: (2)–(3) xác nhận persistence và DC là **cùng một khái niệm** khi chuỗi và ngưỡng như nhau; khác biệt với
`dc_atr_structure` chỉ đến từ giá dùng (wick vs close) và cách khoá ATR. (4)–(5) là lý do chọn `duong_oc` và lý do
**không** hứa «luôn xen kẽ». (8): cấp 1 ở 1×ATR dày gần như STH pivot 1/1 (lý thuyết ≈ 1/4 nến mỗi phía trên random
walk theo close), cấp 2–3 thưa hơn nhiều so với ITH/LTH dự kiến — cần biến thể «cùng mật độ» (§12).

## 9. Chỗ mơ hồ đã chọn

| # | Câu hỏi | Chọn | Vì sao | Ảnh hưởng / biến thể |
|---|---|---|---|---|
| 1 | Giá nào | high/low | Khớp STH/ITH, ICT, nhãn người theo wick | DC dùng close → so với DC là so chéo định nghĩa |
| 2 | Thứ tự trong nến | `duong_oc` | Quy tắc outside day của Williams; tự xen kẽ khi ngưỡng hằng; trùng DC trên đường (§8) | Dựa vào giả định — đo bằng `dua_vao_thu_tu_nen`; đối chứng `loai_tru`. Sau này có thể dùng nến M1 (lab có M1 2018–2025) |
| 3 | Khoá ATR nào | `ATR[m−1]` | Quy ước «ATR khoá» của lab (D4) | Khác DC (ATR[e]); ATR đổi giữa hai swing làm vỡ xen kẽ (§8.5). Biến thể «chuẩn hoá đường giá theo ATR» (mỗi bước chia ATR lúc đó → xen kẽ chính xác) để sau |
| 4 | Bằng giá | nến sớm hơn thắng | Quy tắc chuẩn của persistence; không mất đỉnh đôi bằng giá tuyệt đối | Khác pivot strict (D15). Cờ `bang_dinh_truoc` |
| 5 | Ép xen kẽ | không | Persistence không cần; ép là thêm quy tắc không có nguồn | Báo cáo số vi phạm |
| 6 | Khoảng trống | giữ + gắn cờ | Đóng cửa theo lịch không che giá; reset mỗi khoảng trống phá cấp 2–3 | **Đổi so với đề xuất ban đầu** «reset như DC» (§13 Q2); biến thể `reset_bat_thuong` |
| 7 | Biên trái bị cắt | vẫn xét, gắn cờ | Không bỏ dữ liệu đầu; đoạn trái chỉ có thể bị ước thấp | Khi chấm có thể loại |
| 8 | Ba cấp 1/3/9 | bội 3 | Ngưỡng đa cấp theo cấp số nhân giống «intrinsic time» nhiều ngưỡng ([Glattfelder & Olsen 2024](https://arxiv.org/abs/2406.07354)); số 3 do lab chọn | Hiệu chỉnh «cùng mật độ» ở §12 |
| 9 | Persistence cuối | không phát sự kiện | Một sự kiện cho một cấu trúc mỗi cấp (AGENTS §5.1) | Chỉ vào phổ `run_stats` |
| 10 | `Pivot.members` | không có | Persistence không dựng từ ba swing cấp dưới | Cắm vào `ict_structure` cần sửa (§10) |

## 10. Khác biệt với các thuật toán đang có, giới hạn đã biết

* **Không đổi thuật toán nào khác.** Muốn cắm làm nguồn swing cho `ict_structure` sau này phải sửa thêm:
  `ict_structure` đọc `Pivot.members` (ba swing tạo nên ITH) ở `algorithm.py` dòng 745 và 1126. Đó là biến thể mới
  (tăng minor) và quyết định riêng — chỉ nên làm nếu §12 và nhãn người cho thấy persistence đáng thay.
* ATR M15 mang mùa vụ theo giờ phiên: cùng một khoảng giá là «lớn» ở phiên Á, «nhỏ» ở New York — như DC-ATR. Chưa
  khử mùa vụ.
* Bộ nhớ ngăn xếp O(n) trong trend một chiều rất dài (§8.7). Thời gian không tăng theo bình phương.
* Thứ tự trong nến là giả định (§9.2).
* Tương đương với «important extrema» của Fink lấy qua survey, chưa đối chiếu bài gốc; tương đương với DC đã kiểm (§8).
* Chưa có HH/HL, trend/range, plugin hiển thị riêng, nhãn tham chiếu.

## 11. Kiểm thử bắt buộc (bước ④)

* **Tính tay:** ví dụ §7 cả hai chế độ — từng sự kiện, giá, nến, trễ, `details` chính.
* **Biên:** đoạn phải = R − ε / = R / > R; đỉnh đôi bằng giá; plateau; outside bar hai phía; doji (gần open, cách
  đều); nhiều cấp cùng nến; trễ 0; xác nhận và vượt cùng nến (`duong_oc` có, `loai_tru` không); biên trái bị cắt;
  warm-up; ATR = 0.
* **Dữ liệu sai:** NaN/inf, OHLC sai, thời gian trùng/lùi, lệch bước → `ValueError`.
* **Khoảng trống:** từng loại; `giu_gan_co` đếm đúng và gắn `qua_bat_thuong`; `reset_bat_thuong` bỏ ứng viên, tăng
  `phan_doan`, `event_id` mang đoạn mới.
* **Tính chất (§8, seed cố định):** trực tuyến = vét cạn; một giá + ngưỡng hằng = DC tham chiếu (viết trong test);
  `duong_oc` + ngưỡng hằng → 0 vi phạm xen kẽ; lồng nhau (mọi cấp 2 có cấp 1 cùng cực trị, `confirmed_at` không giảm
  theo cấp); cực trị luôn là high/low của nến.
* **Nhân quả** (AGENTS §7.1): prefix tại nhiều điểm cắt = chạy trọn lọc theo `confirmed_at` (sự kiện + timeline);
  sửa dữ liệu sau T không đổi sự kiện trước T; deep-copy sự kiện đã trả rồi nạp tiếp; `reset()` rồi chạy lại = như
  cũ; replay lùi = prefix mới.
* **Quy mô:** XAUUSD M15 2018–2025 (`ds_a5212fd37814`, 189 073 nến) và một năm M1 — ghi thời gian, ngăn xếp lớn nhất.
* **API:** run → lưu → mở lại → CSV / manifest.
* **Hồi quy:** `scripts/regression_saved_runs.py` — mọi run đã lưu của thuật toán khác khớp tuyệt đối.

## 12. Chạy thật và so sánh (bước ⑤) — khai trước

Dữ liệu: XAUUSD M15 `ds_a5212fd37814`, EURUSD M15 `ds_a9a2a5e4cef5`, **chỉ đoạn phát triển** 2018 – 31/08/2024; đoạn
kiểm tra (từ 01/09/2024) khoá. Script `research/khao_sat_persistence.py`, số liệu `docs/research/khao_sat/persistence_dev.json`
kèm checksum dataset, phiên bản, cấu hình (AGENTS §9).

Cấu hình:

1. Mặc định (1/3/9, `duong_oc`, `giu_gan_co`).
2. `loai_tru` — đo mức phụ thuộc thứ tự trong nến.
3. `reset_bat_thuong`.
4. **«Cùng mật độ»:** trên đoạn phát triển, chọn mỗi hệ số trong lưới 0,25–12 (bước 0,25) sao cho mật độ cấp k gần
   nhất với mật độ STH / ITH / LTH của `ict_structure` (pivot 1/1, cùng dữ liệu). Quy tắc chọn khai ở đây, trước khi
   chạy.

Chỉ số (chưa có nhãn — **không** kết luận «tốt hơn»): mật độ theo cấp × phía; trễ trung vị / P90 (nến, giờ); tỷ lệ
trễ 0 và `dua_vao_thu_tu_nen`; tỷ lệ không xen kẽ; độ trùng vị trí với STH/ITH/LTH (cùng nến, ±1 nến) theo hai chiều;
phổ persistence của chính các ITH/LTH kiểu Williams (ITH có phải là «nhịp lớn» không); cùng các số đó trên chuỗi giả
của nghiên cứu nền nhiễu (random walk giữ biến động và mùa vụ) để biết phần nào chỉ là tính chất của nhiễu.

Có nhãn người (bộ nhãn D8) thì chấm bằng mục tiêu «Swing nhỏ» / «Swing cấu trúc», báo F1 **cạnh mật độ** (F1 phụ
thuộc mật độ) và cạnh chuẩn ngẫu nhiên.

## 13. Câu hỏi cần duyệt

| # | Câu hỏi | Đề xuất |
|---|---|---|
| Q1 | Thứ tự high/low trong nến | `duong_oc` mặc định, `loai_tru` đối chứng. Chưa nêu ở đề xuất trước — phát hiện khi viết bản mẫu |
| Q2 | Khoảng trống | **Đổi** từ «reset như DC» sang «giữ + gắn cờ» (lý do §4.6); `reset_bat_thuong` là biến thể |
| Q3 | Loại sự kiện | Dùng lại `SWING_HIGH` / `_L2` / `_L3` + mã lý do riêng (tiền lệ `ict_structure`), thay vì loại riêng `PERSIST_*` kèm ánh xạ khi chấm |
| Q4 | Hệ số mặc định | 1/3/9, kèm biến thể «cùng mật độ» hiệu chỉnh trên dev (§12) |
| Q5 | Hiển thị | v0.1 dựa vào plugin swing có sẵn (vẽ theo loại `SWING_*`); plugin riêng (ba cấp, đường mức) để sau khi xem số liệu §12 |
