# Thuật toán: lớp nhận diện — khoảng giá, xác suất chạm mức, trạng thái (`ict_structure` 0.6.0)

## 1. Trạng thái, phiên bản

| Mục | Giá trị |
|---|---|
| Trạng thái | **Bản đầu lên web** (người dùng chọn 21/10/2026: «bản đầu lên web ngay»; conformal, nhãn tay, thời gian còn lại để bản sau) |
| Nằm trong | `ict_structure` 0.6.0 — tham số `nd_bat` (mặc định bật); tắt thì output giống hệt 0.5.0 |
| Thành phần | [`core/components/price_band.py`](../../core/components/price_band.py), [`core/components/market_state.py`](../../core/components/market_state.py); keo nối vào thuật toán: [`core/algorithms/ict_structure/nhan_dien.py`](../../core/algorithms/ict_structure/nhan_dien.py) (`NdLayer`) |
| Plan | [`plan_nhan_dien_trang_thai.md`](../plans/plan_nhan_dien_trang_thai.md) §3 (định nghĩa trạng thái), §4 (đầu ra), §5 (chấm); [`plan_ket_hop_ict_indicator.md`](../plans/plan_ket_hop_ict_indicator.md) §4 |
| Số liệu dùng để chọn | [`khao_sat_ict_indicator.md`](../research/khao_sat_ict_indicator.md) (giờ + biến động gần là nền tốt nhất cho dải giá; xác suất chạm chỉ phụ thuộc khoảng cách theo ATR) |

| Phiên bản | Ngày | Thay đổi |
|---|---|---|
| 0.6.0 (`ict_structure`) | 21/10/2026 | Bản đầu: khoảng 80% / 50% cho 1h và 4h, xác suất chạm vùng thanh khoản gần nhất và biên range, trạng thái 4 loại, tự chấm trong lần chạy |

**Khoảng và xác suất chạm** có đủ ba điều đầu của AGENTS §2.4 (khoảng / xác suất; chấm trên kết cục tương lai ngay
trong lần chạy, §6; baseline B0). Điều thứ tư (giao diện hiện điểm thật) đến khi lớp khoảng giá lên chart — **tới lúc đó
chỉ gọi là mô tả**; số liệu đã có trong `run_stats.nhan_dien` và `pending_state.nhan_dien`. **Trạng thái là mô tả**,
không có xác suất. Giao diện bản đầu: lớp «Trạng thái» (người dùng chọn làm trước, 21/10/2026).

## 2. Tầng, đầu vào, đầu ra

- Tầng: trên cùng (bộ nhận diện), đọc sau khi `ict_structure` đã xử lý xong nến t (bước 13 trong nến, §4).
- Đầu vào mỗi nến: OHLC, giờ New York của nến, ATR Wilder 14 sau nến t (cùng ATR của `ict_structure`), vùng thanh
  khoản còn nguyên gần nhất trên / dưới (`liq_above` / `liq_below`), thứ tự cấp cấu trúc (chỉ ghi kèm).
- Đầu ra:
  - timeline (mỗi nến): `nd_trang_thai`, `nd_tu`, `nd_range_tu` (nến đầu cửa sổ range), `nd_range_hi` / `nd_range_lo`,
    `nd_1h_lo80` … `nd_4h_hi50`,
    `nd_p_tren_1h` / `_4h`, `nd_p_duoi_1h` / `_4h`;
  - sự kiện khi trạng thái đổi: `STATE_TREND_UP`, `STATE_TREND_DOWN`, `STATE_RANGE`, `STATE_SQUEEZE`, `STATE_CHOP`;
  - `pending_state.nhan_dien`: trạng thái kèm lý do, khoảng, mức kèm xác suất, điểm thật tới nến hiện tại;
  - `run_stats.nhan_dien`: điểm thật cả lần chạy.

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
     Mức gồm vùng thanh khoản còn nguyên gần nhất mỗi phía và biên range khi trạng thái là range.

Phân vị: nội suy tuyến tính trên mẫu đã sắp, vị trí (n − 1)·q.

## 5. Trạng thái (mô tả, theo plan nhận diện §3)

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

## 6. Chấm trong lần chạy (điểm thật)

Với mỗi tầm h và mỗi dự báo đưa ở nến s mà kết cục đã biết (không vắt khoảng trống):

| Đại lượng | Định nghĩa |
|---|---|
| Độ phủ 80% / 50% | Tỷ lệ dự báo mà max high (s, s+h] ≤ cận trên **và** min low ≥ cận dưới |
| Độ rộng | Trung bình (cận trên − cận dưới) / ATR_s |
| Skill so với B0 | 1 − L / L_B0, L = pinball loss của hai biên ở mức `nd_muc_80`; B0 = phân vị của mẫu chung (bỏ giờ), cùng thời điểm, cùng cửa sổ |
| Theo giờ NY | Độ phủ 80% theo từng giờ (24 dòng) |
| Xác suất chạm | Theo loại mức (vùng trên, vùng dưới, biên range trên / dưới): Brier, Brier của B0 (mẫu chung), 10 nhóm hiệu chuẩn (p dự báo trung bình, tỷ lệ chạm thật) |

Giao diện hiện các số này trong tooltip của khoảng / mức và trong tab Thống kê. Không có P&L, không có win rate.

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
- Không có xác suất trạng thái còn giữ, thời gian còn lại, xác suất phá biên (bản sau, plan bước 5).
- Test: [`tests/algorithms/test_ict_nhan_dien.py`](../../tests/algorithms/test_ict_nhan_dien.py) — phân vị, mẫu nhân quả,
  khoảng trống, chấm; luật trạng thái tính tay; nhân quả prefix; tắt `nd_bat` = 0.5.0. Hiển thị:
  [`tests/frontend/test_ict_nhan_dien_display.py`](../../tests/frontend/test_ict_nhan_dien_display.py).
