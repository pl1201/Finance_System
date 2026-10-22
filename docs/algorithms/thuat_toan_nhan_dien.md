# Thuật toán: lớp nhận diện — khoảng giá, xác suất chạm mức, trạng thái, thời gian (`ict_structure` 0.9.1)

## 1. Trạng thái, phiên bản

| Mục | Giá trị |
|---|---|
| Trạng thái | **Bản đầu lên web** (người dùng chọn 21/10/2026: «bản đầu lên web ngay»; conformal, nhãn tay, thời gian còn lại để bản sau) |
| Nằm trong | `ict_structure` 0.6.0 — tham số `nd_bat` (mặc định bật); tắt thì output giống hệt 0.5.0 |
| Thành phần | [`core/components/price_band.py`](../../core/components/price_band.py), [`core/components/market_state.py`](../../core/components/market_state.py), [`core/components/state_clock.py`](../../core/components/state_clock.py) (0.7.0); keo nối vào thuật toán: [`core/algorithms/ict_structure/nhan_dien.py`](../../core/algorithms/ict_structure/nhan_dien.py) (`NdLayer`) |
| Plan | [`plan_nhan_dien_trang_thai.md`](../plans/plan_nhan_dien_trang_thai.md) §3 (định nghĩa trạng thái), §4 (đầu ra), §5 (chấm); [`plan_ket_hop_ict_indicator.md`](../plans/plan_ket_hop_ict_indicator.md) §4 |
| Số liệu dùng để chọn | [`khao_sat_ict_indicator.md`](../research/khao_sat_ict_indicator.md) (giờ + biến động gần là nền tốt nhất cho dải giá; xác suất chạm chỉ phụ thuộc khoảng cách theo ATR) |

| Phiên bản | Ngày | Thay đổi |
|---|---|---|
| 0.6.0 (`ict_structure`) | 21/10/2026 | Bản đầu: khoảng 80% / 50% cho 1h và 4h, xác suất chạm vùng thanh khoản gần nhất và biên range, trạng thái 4 loại, tự chấm trong lần chạy |
| 0.7.0 (`ict_structure`) | 21/10/2026 | **Thời gian** (plan nhận diện bước 5, §5b): xác suất trạng thái đang hiện còn giữ sau 1h / 4h, thời gian còn lại (trung vị), xác suất phá biên khi range; mỗi thứ tự chấm Brier so với B0. Thêm cột timeline `nd_giu_*`, `nd_con_lai`, `nd_pha_*`; khối `thoi_gian` trong pending / stats. Sự kiện, timeline cũ, khoảng / xác suất chạm không đổi |
| 0.9.1 (`ict_structure`) | 22/10/2026 | **Đường trend** (người dùng chọn thay dải «trạng thái»): cột timeline `nd_duong` — trend lên = đáy thấp nhất 4 giờ tới nến t (close nến sau thủng là hết trend, đúng luật thoát «thủng kênh»), trend xuống = đỉnh cao nhất, range = giữa hộp, nhiễu = null. Giao diện vẽ đường bậc thang trên giá. Mọi output khác không đổi |
| 0.9.0 (`ict_structure`) | 22/10/2026 | **Trạng thái v2** (plan [`plan_nhan_dien_v2.md`](../plans/plan_nhan_dien_v2.md), §5c): 4 trạng thái (trend ↑ / ↓, range, nhiễu) + cờ nén; trend theo cấu trúc + lực, giữ tới CHoCH / thủng kênh / lực tắt; range = hộp Donchian 6 giờ có biên được thăm lại, giữ tới khi 2 close phá biên. Tham số `nd_kieu` (v2 mặc định; v1 = output như 0.8.0, đã so tuyệt đối), `nd_er_vao`, `nd_er_ra`; cột timeline `nd_nen`, `nd_do_manh`. **Đổi:** trạng thái, sự kiện `STATE_*`, còn giữ / phá biên (theo đoạn / hộp v2). Khoảng giá, xác suất chạm không đổi |
| 0.8.0 (`ict_structure`) | 21/10/2026 | **PDH / PDL** còn nguyên ở đúng phía giá vào xác suất chạm (plan kết hợp bước 2; khảo sát [`khao_sat_pdh_pdl.md`](../research/khao_sat_pdh_pdl.md): không cần hiệu chỉnh riêng). Điểm theo loại mức thêm `ty_le_cham`, `p_tb` (kỳ vọng), `chenh` ở cả `diem_that` lẫn `run_stats`. **Đổi:** `muc` có thêm dòng `pdh` / `pdl` và `cham` thêm hai loại; `cham_tong` **giữ** tập mức như 0.7.0 (vùng gần nhất + biên range — PDH / PDL phần lớn ở xa, p ≈ 0, gộp vào sẽ kéo Brier gộp xuống ≈ 30% mà dự báo không tốt hơn). Sự kiện, timeline, khoảng, trạng thái, thời gian, `cham_tong` không đổi |
| 0.6.1 (`ict_structure`) | 21/10/2026 | Lớp «Khoảng giá» lên giao diện kèm điểm thật. Thêm (không đổi sự kiện / timeline): `pending_state.nhan_dien.nen` (nến của trạng thái — giao diện chỉ dùng mức / điểm thật khi = con trỏ), `diem_that.<tầm>.cham` + `cham_tong` (Brier gộp mọi loại mức), `run_stats…cham_tong`; câu `ghi_chu_vi` của thống kê |

**Khoảng, xác suất chạm, xác suất còn giữ / phá biên (0.7.0) là dự báo** theo AGENTS §2.4 (đủ bốn điều): đầu ra là khoảng / xác suất; chấm trên kết cục
tương lai ngay trong lần chạy (§6); có baseline B0; giao diện hiện điểm thật — tooltip của khoảng / mức (độ phủ thực tế,
Brier so với B0 tới nến đang xem), «Đang theo dõi» và tab Thống kê (cả lần chạy). **Trạng thái là mô tả**, không có xác
suất. Giao diện: lớp «Trạng thái» (làm trước, 21/10/2026) và lớp «Khoảng giá 1h / 4h + xác suất chạm»; «Khung trạng
thái» dưới chart (lớp `ict_nd_pane`, 22/10/2026 — chart riêng cùng trục thời gian, đọc thẳng cột `nd_trang_thai` /
`nd_do_manh` / `nd_nen`, xem [`plan_nhan_dien_v2.md`](../plans/plan_nhan_dien_v2.md) §4 «Đã làm»). Kiểm định bộ trạng
thái v2 theo nhu cầu (khai trước, dev): [`kiem_dinh_trang_thai.md`](../research/kiem_dinh_trang_thai.md).

## 2. Tầng, đầu vào, đầu ra

- Tầng: trên cùng (bộ nhận diện), đọc sau khi `ict_structure` đã xử lý xong nến t (bước 13 trong nến, §4).
- Đầu vào mỗi nến: OHLC, giờ New York của nến, ATR Wilder 14 sau nến t (cùng ATR của `ict_structure`), vùng thanh
  khoản còn nguyên gần nhất trên / dưới (`liq_above` / `liq_below`), thứ tự cấp cấu trúc (chỉ ghi kèm).
- Đầu ra:
  - timeline (mỗi nến): `nd_trang_thai`, `nd_tu`, `nd_range_tu` (nến đầu cửa sổ range), `nd_range_hi` / `nd_range_lo`,
    `nd_1h_lo80` … `nd_4h_hi50`,
    `nd_p_tren_1h` / `_4h`, `nd_p_duoi_1h` / `_4h`; 0.7.0: `nd_giu_1h` / `_4h` (xác suất trạng thái đang hiện còn giữ),
    `nd_con_lai` (thời gian còn lại, trung vị, nến), `nd_pha_1h` / `_4h` (xác suất phá biên — chỉ khi range);
  - sự kiện khi trạng thái đổi: `STATE_TREND_UP`, `STATE_TREND_DOWN`, `STATE_RANGE`, `STATE_SQUEEZE`, `STATE_CHOP`;
  - `pending_state.nhan_dien`: `nen` (nến của trạng thái này — giao diện chỉ dùng mức / điểm thật khi `nen` = con trỏ,
    không tô ngược), trạng thái kèm lý do, khoảng, mức kèm xác suất, điểm thật tới nến hiện tại (`diem_that`, có
    `cham_tong` = Brier gộp vùng gần nhất + biên range); 0.7.0: một khối `thoi_gian` = `con_giu` (`tuoi_nen` = số nến đã hiện,
    `giu.<tầm>`, `con_lai_nen`, `nguon`, `n_doan` = cỡ mẫu, `n_doan_con` = mẫu số #(L ≥ tuổi); None khi chưa đủ mẫu), `pha_bien` (`lo`, `hi`, `p.<tầm>`; None khi
    không range), `diem_that.con_giu|pha_bien.<tầm>` (`n`, `ty_le`, `brier`, `brier_b0`);
  - `run_stats.nhan_dien`: điểm thật cả lần chạy; 0.7.0: `thoi_gian.con_giu|pha_bien.<tầm>` (như trên) + `b0_vi`
    (B0 của mỗi xác suất, giao diện ghi kèm).

## 3. Tham số

| Tham số | Mặc định | Ràng buộc | Ý nghĩa |
|---|---|---|---|
| `nd_bat` | true | bool | Bật lớp nhận diện |
| `nd_muc_80` | 0,905 | 0,5–0,99 | Phân vị mỗi phía của khoảng 80%. Chọn trên dev: học 2018, chấm 2019, XAUUSD + EURUSD, 1h + 4h → độ phủ chung 78–82% |
| `nd_muc_50` | 0,745 | 0,5–0,99, < `nd_muc_80` | Phân vị mỗi phía của khoảng lõi 50% (cùng cách chọn → 49–51%) |
| `nd_mau_toi_da` | 600 | 100–5 000 | Số mẫu gần nhất giữ cho mỗi giờ NY (M15: ≈ 150 ngày giao dịch) |
| `nd_mau_toi_thieu` | 60 | 20–1 000 | Dưới số này dùng mẫu chung mọi giờ; mẫu chung < 4× số này → chưa có khoảng (khởi động) |
| `nd_er_nguong` | 0,3 | 0,05–0,9 | Ngưỡng ER phân biệt đi một chiều / đi ngang |
| `nd_giu_nen` | 2 | 1–10 | Trạng thái ứng viên phải giữ đủ số nến này mới đổi (chống nhấp nháy) |
| `nd_kieu` | `v2` | `v2` / `v1` | 0.9.0: kiểu trạng thái (§5c). `v1` = như 0.6–0.8 (§5) |
| `nd_er_vao` | 0,18 | 0,05–0,9, < `nd_er_nguong` | v2: ER 8 giờ vào trend khi cấu trúc cùng chiều (hoặc ADX ≥ 20 cùng chiều DI) |
| `nd_er_ra` | 0,10 | 0,01–0,9, < `nd_er_vao` | v2: trend kết thúc khi ER < ngưỡng này và ADX < 18 |

Hằng số do lab chọn, theo plan nhận diện §3 (đã chốt 21/10/2026), ghi trong `market_state.py`:

- cửa sổ range 8, 12, 16 giờ;
- dung sai chạm biên 0,3·ATR;
- ≥ 2 lần chạm mỗi biên, cách nhau ≥ 1,5 giờ;
- bề rộng range 1,5–5 ATR;
- cửa sổ nén 12 giờ, bề rộng cuối ≤ 50% bề rộng đầu;
- cửa sổ ER của trend 8 giờ;
- swing của lớp này: pivot 2/2.

Khoảng trống dài (> 3 giờ: cuối tuần, lễ) cắt mọi cửa sổ, như khảo sát. Thuật toán báo cờ này một lần mỗi nến từ phân
loại khoảng trống sẵn có (`GapClassifier`: chỉ khi hai nến không liền bước), nên khung H4 / D1 (nến cách nhau ≥ 4 giờ)
không bị coi là khoảng trống.

## 4. Thứ tự trong một nến (bước 13 của `ict_structure`, sau ATR[t], trước ảnh chụp ngữ cảnh)

1. **Khoảng trống.** Hai nến không liền bước và cách nhau > 3 giờ → khoảng trống dài. Mẫu và cửa sổ không vắt qua nó.
2. **Mẫu biên của nến s = t − h hoàn tất** (mỗi tầm h = 1h, 4h tính bằng số nến; tầm < 1 nến thì bỏ):
   - u = (max high (s, t] − C_s) / ATR_s, d = (C_s − min low (s, t]) / ATR_s;
   - thêm vào mẫu của giờ NY của s và vào mẫu chung (4× `nd_mau_toi_da` gần nhất);
   - bỏ mẫu nếu có khoảng trống > 3 giờ trong (s, t] hoặc ATR_s chưa có.
3. **Chấm dự báo đã đưa ở nến s** (§6): khoảng có chứa cả đường giá (s, t] không, xác suất chạm có đúng không.
   Dự báo chỉ được chấm khi kết cục đã biết; không dự báo nào dùng kết cục chưa biết.
4. **Trạng thái sau nến t** (§5). Đổi trạng thái → sự kiện `STATE_*`, nến sự kiện = nến đầu của trạng thái mới.
5. **Dự báo tại nến t**, dùng mẫu đã hoàn tất tới t:
   - mẫu = mẫu của giờ NY của t nếu ≥ `nd_mau_toi_thieu`, không thì mẫu chung;
   - qu = phân vị `nd_muc_80` của u, qd = phân vị `nd_muc_80` của d;
   - khoảng 80% = [C_t − qd·ATR_t, C_t + qu·ATR_t], khoảng 50% tương tự với `nd_muc_50`;
   - xác suất chạm mức P ở trên: khoảng cách D = (P − C_t) / ATR_t, p = tỷ lệ mẫu có u ≥ D. Mức ở dưới dùng d.
     Mức gồm vùng thanh khoản còn nguyên gần nhất mỗi phía, PDH / PDL (0.8.0: biết còn nguyên — vùng D chưa bị lấy;
     cần khung lớn và `period_levels` bật, tắt thì không biết «đã lấy» nên không dùng — và ở đúng phía close: PDH ≥ C_t,
     PDL ≤ C_t) và biên range khi trạng thái là range. PDH / PDL trùng giá vùng gần nhất vẫn là hai dòng `muc` (chấm
     riêng từng loại); giao diện vẽ một đường ghi đủ tên.

Phân vị: nội suy tuyến tính trên mẫu đã sắp, vị trí (n − 1)·q.

## 5. Trạng thái v1 (`nd_kieu = v1`; mặc định tới 0.8.0 — mô tả, theo plan nhận diện §3)

Xét theo thứ tự; điều kiện đầu tiên đúng là trạng thái ứng viên của nến t.

1. **Range** (`range`). Thử cửa sổ 16, 12, 8 giờ (dài trước). Cửa sổ W nến kết thúc ở t, không vắt qua khoảng trống,
   được nhận nếu:
   - biên trên U = max high, biên dưới D = min low;
   - có ≥ 2 swing đỉnh đã xác nhận (pivot 2/2, đỉnh trong cửa sổ) với high ≥ U − 0,3·ATR_t, hai lần chạm cách nhau
     ≥ 1,5 giờ; tương tự ≥ 2 swing đáy với low ≤ D + 0,3·ATR_t;
   - (U − D) / ATR_t trong [1,5; 5];
   - ER(W) < `nd_er_nguong`.
2. **Nén** (`nen`). Cửa sổ 12 giờ, không vắt qua khoảng trống:
   - ba swing đỉnh cuối thấp dần (giảm ngặt), ba swing đáy cuối cao dần (tăng ngặt);
   - bề rộng (max high − min low) của ¼ cuối cửa sổ ≤ 50% bề rộng của ¼ đầu;
   - ER(W) < `nd_er_nguong`.
3. **Trend** (`trend_len` / `trend_xuong`). ER(8 giờ) ≥ `nd_er_nguong`; chiều = dấu của C_t − C_{t−W}. Thứ tự cấu trúc
   của `ict_structure` chỉ ghi kèm (`thu_tu_cung_chieu`), không là điều kiện — chỗ chọn ở §7.
4. **Nhiễu** (`nhieu`). Còn lại khi đủ nến: đi ngang, không có biên rõ, không nén.

ER(W) = |C_t − C_{t−W}| / Σ |C_i − C_{i−1}| trên W nến cuối. Chưa đủ nến sau khoảng trống, hoặc chưa có ATR →
`None` («chưa đủ nến»).

**Chống nhấp nháy:** trạng thái chỉ đổi khi ứng viên khác trạng thái hiện tại giữ đủ `nd_giu_nen` nến liên tiếp. Sự
kiện phát ở nến t (xác nhận), nến sự kiện = nến đầu của chuỗi ứng viên. Biên range trên timeline là biên của nến t
(cập nhật mỗi nến khi đang range).

## 5c. Trạng thái v2 (`nd_kieu = v2`, mặc định từ 0.9.0 — plan_nhan_dien_v2.md §3)

Thành phần [`core/components/market_state_v2.py`](../../core/components/market_state_v2.py). Hai trục: bốn trạng thái
loại trừ nhau (`trend_len`, `trend_xuong`, `range`, `nhieu`) và **cờ nén** (`nd_nen`, đi kèm bất kỳ trạng thái nào).
Thuật toán đưa thêm vào bước 13: thứ tự ITH / ITL khung chạy (`order`), «mức bảo vệ đã bị phá» và thứ tự H1 —
thứ tự H1 chỉ có khi bật khung lớn (`htf_list` có H1) và khung chạy < H1; không có thì luật chỉ dùng cấu trúc khung
chạy (`details.cau_truc_h1` = null). Mỗi lần thoát ghi `details.thoat` và `details.doi_ngay`; mã lý do v2:
`STATE_TREND_STRUCTURE`, `STATE_RANGE_BOX`, `STATE_CHOP_NO_BOX`.

- **Cấu trúc ngược chiều d** (một định nghĩa cho cả vào lẫn ra): thứ tự khung chạy = −d và mức bảo vệ còn, hoặc = d
  nhưng mức bảo vệ đã bị close phá (CHoCH — cờ này giữ tới swing mới). **Cùng chiều d**: thứ tự khung chạy = d còn nguyên,
  hoặc thứ tự H1 = d.
- **Trend lên — vào** khi động lượng 8 giờ > 0, cấu trúc **không** ngược chiều, và một trong: (a) cấu trúc cùng chiều
  + ER 8 giờ ≥ `nd_er_vao` hoặc ADX(14) ≥ 20 với +DI > −DI; (b) ER ≥ 0,25 và ADX ≥ 25 cùng chiều DI (cấu trúc còn trễ);
  (c) ER ≥ `nd_er_nguong` (đường vào của v1). **Ra** (xét theo thứ tự): cấu trúc ngược chiều (CHoCH); close thủng đáy
  thấp nhất 4 giờ trước (kênh Donchian); lực tắt (ER < `nd_er_ra` và ADX < 18). Trend xuống đối xứng. (Cùng định
  nghĩa cho vào và ra để không vào rồi ra ngay — bản trước code-review nhấp nháy khi mức bảo vệ đã phá.)
- **Range — vào** khi không trend: hộp Donchian 6 giờ rộng 1,5–4,5 ATR, ER < `nd_er_nguong`, mỗi biên được thăm ≥ 2 lần
  (high trong ¼ trên / low trong ¼ dưới của hộp, cách nhau ≥ 2 nến). Biên = max high / min low của cửa sổ phát hiện.
  **Giữ** tới khi 2 close liên tiếp ra ngoài biên quá 0,25·ATR (phá biên).
- **Nhiễu**: còn lại. **Cờ nén**: BB(20, 2) trong KC(20, 1,5·TB TR 20) và độ rộng BB thuộc 20% thấp nhất của 500 nến.
- Đổi trạng thái: ứng viên giữ `nd_giu_nen` nến; thoát do sự kiện đã xác nhận (CHoCH, thủng kênh, phá biên) đổi ngay
  (nến sự kiện = nến xác nhận, `details.doi_ngay` = true); lực tắt chờ giữ như mọi ứng viên. ADX / DI và BB / KC bắt
  đầu lại sau khoảng trống dài. `details` ghi `ly_do` (vì sao vào), `thoat` (vì sao trạng thái trước kết thúc), ER, ADX,
  động lượng, `cau_truc` (khung chạy) / `cau_truc_pha` / `cau_truc_h1`, `kenh_thoat` (max high / min low 4 giờ trước),
  `nguong` (mọi ngưỡng đã dùng), độ mạnh 0–1 (chỉ để hiển thị — không phải xác suất).
- **Đường trend** (0.9.1, cột `nd_duong`): trend lên = đáy thấp nhất 4 giờ tới nến t (mức close nến sau thủng là hết
  trend), trend xuống = đỉnh cao nhất 4 giờ, range = giữa hộp, nhiễu / chưa đủ nến = null. Giao diện vẽ thành đường
  bậc thang trên giá thay dải «trạng thái».
- Khi range: biên range vào xác suất chạm và phá biên **chỉ khi close còn trong hộp** (hộp v2 cố định từ lúc nhận ra;
  close đã ra ngoài mà chưa đủ 2 close để phá thì dự báo «chạm / phá» gần như chắc đúng — không đưa vào điểm thật).
- **Điểm dev** (M15, 2018 → 2024-08, XAU / EUR; [`khao_sat_trang_thai_v2.py`](../../research/khao_sat_trang_thai_v2.py),
  [`trang_thai_v2_dev.json`](../research/khao_sat/trang_thai_v2_dev.json), v1.2): trend 49%, range 33%, nhiễu 18–19%,
  cờ nén 13–15% thời gian; bắt 88% nhịp đi một chiều rõ (v1: 55–56%), trend có ADX > 20: 86%; đổi 5,5–5,8 / 100 nến;
  đoạn range trung vị 13 / 11 nến (v1: 4); ổn định khi đổi ngưỡng ± 20%: κ 0,79–0,98. Trend sai chiều so với tham chiếu
  nhìn lại ±16 nến 12,5–12,7% — đúng mức sàn của mọi nhãn động lượng nhân quả cùng độ phủ (≈ 12%). Biên range **không**
  giữ giá hơn một hộp bất kỳ cùng bề rộng (chênh 0,0 / −0,1 điểm, CI chứa 0): range là mô tả hình dạng, không phải tín
  hiệu.

## 5b. Thời gian (0.7.0, plan nhận diện bước 5)

**Đoạn hiển thị** của một trạng thái: từ nến trạng thái bắt đầu hiện (nến xác nhận của sự kiện `STATE_*`) tới nến trước
khi trạng thái khác hiện. Độ dài L (nến). Tuổi tại nến t: a = t − nến bắt đầu hiện + 1. Đoạn bị cắt vì «chưa đủ nến»
(khoảng trống dài) là **bị kiểm duyệt**: không vào mẫu (không biết nó còn kéo dài bao lâu).

- **Xác suất còn giữ** sau tầm h: p = #(L ≥ a + h) / #(L ≥ a) trên các đoạn đã kết thúc **cùng trạng thái** (400 đoạn
  gần nhất mỗi trạng thái). Mẫu số #(L ≥ a) < 30 → dùng mọi trạng thái (2 000 đoạn gần nhất); vẫn < 30 → chưa có.
  Kết cục: trạng thái hiện ở nến t + h vẫn là đoạn đó (biết đúng ở t + h); cửa sổ có lần cắt (khoảng trống dài, hoặc
  trạng thái rơi về «chưa đủ nến») → không chấm. **B0** (bỏ điều kiện tuổi) = tỷ lệ nến của cùng mẫu mà đoạn còn kéo
  dài thêm ≥ h nến = Σ max(L − h, 0) / Σ L.
- **Thời gian còn lại** = trung vị của (L − a) trên các đoạn của cùng mẫu có L ≥ a. Mô tả kèm (không chấm riêng; xác
  suất còn giữ là phần được chấm).
- Điểm dev (M15, 2018 → 2024-08, XAUUSD / EURUSD, chạy cả đoạn), trạng thái v2 (0.9.0): **còn giữ ngang B0** — skill
  Brier 1h −0,2% / −0,1%, 4h +0,4% / +0,5%. **Phá biên có skill** — 1h 5,9% / 9,6%, 4h 13,9% / 22,8% (≈ 41–44 nghìn dự
  báo mỗi mã, chỉ khi close còn trong hộp; range bị phá trong 4h ở 65–66% số lần). Với v1 (0.7.0–0.8.0): còn giữ +0,5 / +0,3 (1h), −0,4 / −0,2 (4h);
  phá biên 1h 3,8 / 8,2, 4h 12,4 / 33,0 trên ≈ 2,7 nghìn dự báo.
- Giới hạn đã biết: đoạn bị cắt bỏ hẳn khỏi mẫu, chưa ước lượng kiểu Kaplan–Meier. Đoạn dài dễ vắt cuối tuần hơn nên
  hơi thiếu trong mẫu → xác suất còn giữ ở tuổi lớn có thể thấp hơn thật.
- **Xác suất phá biên** (chỉ khi range, biên [D, U] của nến t): p = tỷ lệ mẫu cùng giờ NY có close vượt ra ngoài
  khoảng cách tới biên — mẫu (uc, dc) = (max close (s, s+h] − C_s, C_s − min close (s, s+h]) / ATR_s, cùng cách lấy mẫu
  và cùng mẫu chung dự phòng với khoảng giá (§4); phá = uc > (U − C_t)/ATR_t hoặc dc > (C_t − D)/ATR_t. Kết cục: có
  close trong (t, t+h] > U hoặc < D. **B0** = cùng cách trên mẫu chung mọi giờ.

## 6. Chấm trong lần chạy (điểm thật)

Với mỗi tầm h và mỗi dự báo đưa ở nến s mà kết cục đã biết (không vắt khoảng trống):

| Đại lượng | Định nghĩa |
|---|---|
| Độ phủ 80% / 50% | Tỷ lệ dự báo mà max high (s, s+h] ≤ cận trên **và** min low ≥ cận dưới |
| Độ rộng | Trung bình (cận trên − cận dưới) / ATR_s |
| Skill so với B0 | 1 − L / L_B0, L = pinball loss của hai biên ở mức `nd_muc_80`; B0 = phân vị của mẫu chung (bỏ giờ), cùng thời điểm, cùng cửa sổ |
| Theo giờ NY | Độ phủ 80% theo từng giờ (24 dòng) |
| Xác suất chạm | Theo loại mức (vùng trên, vùng dưới, PDH, PDL, biên range trên / dưới): Brier, Brier của B0 (mẫu chung), tỷ lệ chạm thật, kỳ vọng `p_tb` (= xác suất chạm một mức bất kỳ cùng khoảng cách, cùng giờ; chạm thật > kỳ vọng → loại mức hút giá), `chenh` = thật − kỳ vọng, 10 nhóm hiệu chuẩn. `cham_tong` gộp vùng gần nhất + biên range (như 0.6.1–0.7.0; PDH / PDL báo riêng) |
| Còn giữ / phá biên (0.7.0) | Mỗi tầm: n, tỷ lệ thật, Brier, Brier của B0 (§5b) |

Giao diện hiện: tooltip của khoảng (độ phủ 80% / 50%, độ rộng, so với B0 — chỉ kết luận khi ≥ 100 khoảng đã chấm), tooltip
của mức (Brier so với B0 từng tầm), tab Thống kê (độ phủ, skill, Brier gộp + từng loại mức, độ phủ 80% theo giờ NY thấp /
cao nhất). Nhóm hiệu chuẩn (10 nhóm) chỉ có trong `run_stats` (JSON), chưa vẽ. Không có P&L, không có win rate.

## 7. Chỗ mơ hồ đã chọn

| # | Chỗ | Chọn | Vì sao |
|---|---|---|---|
| N-1 | Mô hình khoảng | Phân vị theo giờ NY của biên chuẩn hoá ATR, cửa sổ trượt | Khảo sát: giờ + biến động gần tốt hơn dải cố định 12–17%; HGB chỉ thêm 1–2 điểm mà nặng, không chạy được từng nến |
| N-2 | 80% «chung» hay mỗi phía | Chung cả đường giá, chọn mức mỗi phía theo dev (§3) | Đúng nghĩa ở plan §4: «toàn bộ đường giá H giờ tới nằm trong khoảng» |
| N-3 | Conformal | Chưa (bản sau) | Người dùng chọn bản đầu; độ phủ thật hiện ngay trên giao diện để thấy lệch |
| N-4 | Mức để tính xác suất | Vùng còn nguyên gần nhất mỗi phía + biên range | Khảo sát C: vùng ICT bị chạm gần như theo khoảng cách; OB / OTE không thêm (khảo sát OB / OTE) |
| N-5 | Swing của trạng thái | Pivot 2/2 riêng: high lớn hơn **ngặt** 2 nến trái, **≥** 2 nến phải (đỉnh bằng giá liền nhau → nến đầu); không dùng STH/STL 1/1 của người dùng | Đúng ví dụ plan §3 (`research/vi_du_range_sideway.py`); không đổi theo tham số pivot của cấu trúc. Khác `PivotSource` (ngặt cả hai phía) |
| N-6 | Trend | ER ≥ ngưỡng; thứ tự cấu trúc chỉ ghi kèm | Thứ tự cấp 2 trễ nhiều nến; bước 3 của plan kiểm bằng nhãn tay |
| N-7 | Hai điều kiện cùng đúng | range > nén > trend > nhiễu | Range là trạng thái người dùng cần thấy nhất; trend trong range ngắn hạn vẫn là range |

## 8. Giới hạn, kiểm thử

- Chưa có nhãn tay cho trạng thái: tỷ lệ thời gian mỗi trạng thái chỉ là mô tả.
- Độ phủ có thể lệch khi biến động đổi chế độ nhanh (cửa sổ 150 ngày); chưa có conformal để tự chỉnh.
- Xác suất còn giữ dựa trên độ dài đoạn của chính lớp này (chống nhấp nháy 2 nến làm đoạn dài hơn đoạn ứng viên); chưa
  có mô hình rủi ro theo phiên / tin (plan bước 5 còn phần này).
- Test: [`tests/algorithms/test_ict_nhan_dien.py`](../../tests/algorithms/test_ict_nhan_dien.py) — phân vị, mẫu nhân quả,
  khoảng trống, chấm; luật trạng thái tính tay; nhân quả prefix; tắt `nd_bat` = 0.5.0. Hiển thị:
  [`tests/frontend/test_ict_nhan_dien_display.py`](../../tests/frontend/test_ict_nhan_dien_display.py); khung trạng
  thái: [`tests/frontend/test_sub_pane.py`](../../tests/frontend/test_sub_pane.py) (khung phụ + hook `pane`, đồng bộ với
  chart chính) và phần khung trong `ict_nhan_dien_check.js` (cột = cột timeline của lõi ở mọi nến, prefix replay).
