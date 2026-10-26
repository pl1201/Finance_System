# dc_atr_structure v0.2.0 — Directional Change theo close + ATR, phân loại Trend/Range

Ngày: 25/09/2026. Lập từ [`plan_dc_atr_trend_range.md`](../plans/plan_dc_atr_trend_range.md).

Lịch sử phiên bản:

* **0.1.0** — detector DC, classifier regime, `gap_policy=reset`.
* **0.2.0** — thêm `gap_policy=bridge_short` (nối gap ngắn, §3). Với
  `gap_policy=reset` (mặc định) kết quả **giống hệt 0.1.0**: 8 run 0.1.0 đã lưu
  chạy lại khớp event_id, giá, nến, reason; khác duy nhất là sự kiện
  `DC_SEGMENT_GAP` có thêm khoá `bridge_max_gap_hours = null` trong `details`.
  Trường `algorithm_version` của run mới là 0.2.0.

**Trạng thái:** thuật toán nghiên cứu dựa trên luật, đã chạy end-to-end trong web
(run, replay, lưu, mở lại, export, so sánh baseline) và có test nhân quả. Không phải
AI, không phải công thức ICT chuẩn, không phải công cụ dự báo đảo chiều hay thuật
toán tối ưu. Trend/Range là **định nghĩa vận hành do lab đề xuất**, không phải chân
lý gán nhãn thị trường. Chưa có nhãn tham chiếu nên **chưa có số đo độ chính xác**.

## 1. Kiến trúc và file

```text
Nến đã đóng → validate/gap → ATR Wilder → DcDetector → pivot DC + nhãn HH/HL…
                                                         ↓
                                          RegimeClassifier (module riêng)
                                                         ↓
                          StructureEvent / timeline / pending / run_stats
                                                         ↓
                              API · SQLite · CSV/manifest · chart/replay
```

| File | Vai trò |
|---|---|
| `core/algorithms/dc_atr_structure/detector.py` | `DcDetector` (thuần DC, không biết regime) |
| `core/algorithms/dc_atr_structure/algorithm.py` | adapter `DcAtrStructureAlgorithm`: gap/segment, ATR, thứ tự trong nến, sự kiện |
| `core/algorithms/dc_atr_structure/regime.py` | `RegimeClassifier` v0.1.0 — test độc lập, không tác động ngược vào detector |
| `core/indicators.py` | thêm `WilderATRPrevClose` (seed đúng spec). `WilderATR` cũ **không đổi** |
| `core/algorithms/dc_atr_structure/metrics.py` | metric không cần nhãn + `DC_CROSS_DEFINITION_EVENT_MAP` |
| `core/vocab/dc.py`, `core/registry.py` | 9 `structure_type`, 10 `reason_code` + câu giải thích tiếng Việt; đăng ký |
| `core/algorithms/base.py` | thêm trường tuỳ chọn `ParamSpec.show_if` (mặc định `None`) |
| `core/engine.py`, `backend/app/*` | `ReplaySession.step_until_event` + `POST /api/replay/{sid}/next-event` |
| `frontend/js/algos/dc_atr.js` | plugin hiển thị: lớp vẽ DC, dải regime, Range, ẩn chữ khi zoom xa, tooltip, ghi chú, chỉ số, trạng thái replay, panel chi tiết, khung «Thuật toán đang làm gì», cấu hình so baseline, ánh xạ chấm chéo |
| `frontend/js/pages/lab/*`, `index.html`, `css/app.css` | form `show_if`, baseline (overlay + panel đồng bộ), điều hướng bàn phím; khung lớp `#dc-layers` |
| `frontend/js/pages/eval/protocol.js`, `danh-gia.html` | ô tích «chấm pivot DC như swing cấp 1 — so chéo định nghĩa» (ánh xạ lấy từ plugin) |
| `research/dc_experiment.py` | harness thí nghiệm đối chứng tái lập |
| `tests/algorithms/test_dc_atr_structure.py`, `test_dc_regime.py`, `test_dc_api.py` | 85 test |

Không thêm cột/bảng SQLite: mọi metadata nằm trong `details_json` của sự kiện,
`params_json`, `stats_json` và `manifest_info` — nên run cũ mở được như trước.

## 2. Tham số

| Tham số | Mặc định | Ràng buộc | Ghi chú |
|---|---:|---|---|
| `timeframe` | M15 | phải khớp dataset | **Thêm so với plan** (xem §9). Form tự điền theo dataset |
| `gap_policy` | reset | `reset` \| `bridge_short` | từ 0.2.0, xem §3 |
| `bridge_max_gap_hours` | 2.0 | > 0, ≤ 72 | chỉ hiện khi `bridge_short` |
| `price_source` | close | chỉ `close` | OHLC chỉ dùng tính ATR và vẽ nến |
| `threshold_mode` | atr | `atr` \| `percent` | |
| `atr_period` | 14 | int 2–500 | cần `period + 1` nến mỗi segment |
| `atr_multiplier` | 1.5 | > 0, hữu hạn | chỉ hiện khi mode = atr |
| `reversal_pct` | 0.2 | > 0 | **0.2 = 0,2 %**; chỉ hiện khi mode = percent; cần close > 0 |
| `label_tolerance_atr` | 0.1 | ≥ 0 | dung sai HH/EQ × ATR tại cực trị hiện tại |
| `range_swings_per_side` | 3 | int ≥ 3 | m |
| `range_cluster_tolerance_atr` | 0.5 | ≥ 0 | |
| `range_min_width_atr` | 1.0 | > 0 | |
| `range_break_buffer_atr` | 0.25 | ≥ 0 | |

Validate: số hữu hạn (NaN/inf bị từ chối), int không nhận `3.5`/`True`/`"abc"`,
tham số lạ bị từ chối (chặt hơn các thuật toán cũ, cố ý). Tham số của mode không
dùng vẫn được lưu nhưng manifest ghi rõ `tham_so_khong_hieu_luc`.

## 3. ATR và dữ liệu

* `TR[t] = max(H−L, |H−C[t−1]|, |L−C[t−1]|)`; nến đầu segment **chỉ** lấy close
  trước. `ATR_seed` = trung bình n TR đầu → ATR đầu tiên ở nến thứ n+1.
  `ATR[t] = ((n−1)·ATR[t−1] + TR[t]) / n`. Test tính tay:
  `test_atr_seed_va_wilder_tinh_tay`.
* `WilderATR` cũ (nến đầu dùng H−L) giữ nguyên cho baseline và metric
  `price_atr` của trang Đánh giá — khác seed là có chủ đích, có test chứng minh.
* Nến phải hữu hạn, OHLC hợp lệ, `bar_time` tăng nghiêm ngặt, `index` tăng, và
  `close_time − bar_time ∈ {0, bước khung}`. Trùng/lùi thời gian → `ValueError`
  rõ ràng (API trả 400), không tự sắp lại.
* **`gap_policy = reset`:** `bar_time − bar_time trước ≠ bước khung` → phát
  `DC_SEGMENT_GAP`, tăng segment, bỏ ứng viên, ATR, lịch sử pivot/nhãn/range,
  warm-up lại. Log trước gap không đổi (test `test_log_truoc_gap_khong_doi`).
  Nghỉ phiên hằng ngày và cuối tuần cũng là gap. Chưa suy đoán lịch broker.
* **`gap_policy = bridge_short` (0.2.0):** gap có `bước khung < khoảng cách ≤
  bridge_max_gap_hours` (đo giữa hai `bar_time`) được **nối**: không reset
  segment; giữ ứng viên, Δ đã khoá, ATR, lịch sử pivot/nhãn/range; TR của nến đầu
  sau gap tính với close trước gap (gồm cả bước nhảy giá — giống ATR của MT5 qua
  phiên). Phát `DC_GAP_BRIDGED` (chỉ là ghi nhận, marker «nối»). Gap dài hơn vẫn
  reset như trên. Mặc định 2 giờ: nối nghỉ phiên hằng ngày của XAUUSD (~1,25 giờ),
  reset ở cuối tuần (~49 giờ) và các gap ≥ 3,75 giờ. Đây là **lựa chọn phương
  pháp**, không biến dữ liệu thành liền mạch; lag theo phút của pivot qua đêm gồm
  cả thời gian nghỉ. Chưa dùng lịch phiên broker.
* ATR = 0: không khởi tạo detector; nếu cần đặt ứng viên mới khi ATR = 0 → pha
  `WAIT_ATR`, lý do ghi trong pending, không phát pivot với ngưỡng 0.

## 4. Detector DC (tuần tự, close)

1. Sau warm-up: anchor = close hiện tại, khoá Δ anchor, pha `SEEK_DIRECTION`.
   Không phát pivot ở anchor, không chọn hướng trong chính nến anchor.
2. `SEEK_DIRECTION`: close ≥ anchor + Δ → `SEEK_HIGH` (ứng viên = close);
   close ≤ anchor − Δ → `SEEK_LOW`. Nhánh này chỉ chọn hướng.
3. `SEEK_HIGH`: close > ứng viên → cập nhật ứng viên, **khoá Δ mới tại nến đó**;
   ngược lại close ≤ ứng viên − Δ → `DC_HIGH` tại ứng viên, `confirmed_at` =
   close_time nến hiện tại, chuyển `SEEK_LOW` với ứng viên = close hiện tại, khoá Δ
   tại nến này. Không xét thêm reversal trong cùng nến. `SEEK_LOW` đối xứng.
4. `Δ = k × ATR[e]` hoặc `|close[e]| × pct / 100`, e = nến cực trị. Bằng cực trị
   giữ nến đầu và Δ cũ. ATR đổi ở nến sau không đổi Δ. Chạm ngưỡng là đạt.
   So sánh float chính xác, không epsilon.
5. Không ép ứng viên cuối dataset thành pivot; ứng viên nằm trong pending/timeline,
   không bao giờ tính vào metric.

## 5. Sự kiện và hợp đồng tích hợp

| structure_type | event_bar_index | Ghi chú |
|---|---|---|
| `DC_HIGH` / `DC_LOW` | nến cực trị | **Một sự kiện cho mỗi pivot**; nhãn HH/HL/LH/LL/EQH/EQL nằm trong `details.nhan` (không phát event HH riêng → matcher không đếm trùng). `direction` theo quy ước `swing_pivot` (đỉnh = up) |
| `DC_REGIME_UP/DOWN/UNKNOWN` | nến biết (= nến xác nhận) | chỉ khi trạng thái thực sự đổi; lag = 0, không tô ngược |
| `DC_RANGE_START` / `DC_RANGE_EXIT` | nến biết | ID riêng; exit → trạng thái UNKNOWN |
| `DC_SEGMENT_GAP` | nến đầu segment mới | chụp trạng thái/ứng viên bị bỏ |
| `DC_GAP_BRIDGED` | nến đầu sau gap ngắn | chỉ khi `bridge_short`; ghi bước nhảy, ứng viên được giữ |

`event_id = dc:s{segment}:{TYPE}:{extreme}>{confirm}` (pivot) hoặc
`dc:s{segment}:{TYPE}:{bar}` — tất định, không phụ thuộc độ dài dataset. Chi tiết
pivot lưu: `candidate_index`, `candidate_atr`, `delta_e`, `threshold_set_at`,
`cong_thuc_nguong`, `dieu_kien_xac_nhan`, `confirmation_close`,
`reversal_distance(_atr)`, `lag_bars`, `lag_seconds`, nhãn + tham chiếu + giá
trước/sau + dung sai, `nhip` (biên độ / ATR pivot đầu nhịp).

**Đánh giá có nhãn:** protocol mặc định **bỏ qua** DC (loại không có trong map).
Muốn so với nhãn swing (thường theo wick) phải khai báo
`event_type_map = {"DC_HIGH": "SWING_HIGH", "DC_LOW": "SWING_LOW"}`
(`DC_CROSS_DEFINITION_EVENT_MAP`) và ghi rõ đây là **so sánh chéo định nghĩa**.
Trang Đánh giá có ô tích làm việc này (chỉ bật được với mục tiêu «Swing nhỏ»), kèm
cảnh báo chéo định nghĩa trong phần trợ giúp; ánh xạ được lưu trong protocol của
lần đánh giá.

## 6. Classifier regime (`dc_regime` v0.1.0)

* Nhãn cùng loại: so với pivot cùng loại liền trước **trong segment**,
  `tol = label_tolerance_atr × ATR tại cực trị hiện tại`, khoá lúc xác nhận.
* `UPTREND`: nhãn đỉnh gần nhất HH **và** nhãn đáy gần nhất HL (tức hai đỉnh và
  hai đáy gần nhất đều tăng). `DOWNTREND`: LH + LL. Thiếu hai đỉnh/hai đáy →
  UNKNOWN (`thieu_pivot`); mâu thuẫn → `nhan_mau_thuan`; có EQ → `co_nhan_EQ`.
* Range (chỉ thử tại lúc xác nhận pivot, khi không có trend): m đỉnh/m đáy gần
  nhất, `A = ATR[t]` > 0, mỗi cụm rộng ≤ `cluster × A`, `min(highs) > max(lows)`,
  `upper − lower ≥ min_width × A`, `lower ≤ close ≤ upper`. Đạt → khoá biên,
  `A`, buffer, danh sách pivot bằng chứng. Không đạt → lý do cụ thể trong
  `details.kiem_tra_range.ly_do_vi`.
* Range đang khoá: mỗi nến, close > upper + buffer hoặc < lower − buffer → exit
  (wick không đủ), chặn phân loại lại ở chính nến đó; pivot từ nến sau mới được
  xét. Pivot mới trong Range tạo HH+HL/LH+LL → đóng Range, chuyển trend. Không
  tạo Range mới khi Range cũ còn hoạt động.
* Thứ tự mỗi nến: gap → ATR → phá Range → DC → classifier → timeline.

## 7. Giao diện

* **Chạy:** chọn dataset → thuật toán «DC theo close + ATR» → form chỉ hiện `k`
  (mode atr) hoặc `%` (mode percent); khung tự điền → **Chạy thử**.
* **Chart:** mặc định bật marker pivot tại **đúng giá close** (không snap lên
  wick), đường nối hai pivot đã xác nhận (không nối qua gap), biên Range (chỉ từ
  nến sau lúc vào Range tới exit), dải trạng thái ở đáy (bắt đầu từ lúc biết) +
  marker gap. Mặc định tắt: chữ HH/HL…, điểm xác nhận (ô vàng tại close nến xác
  nhận), ứng viên (nét đứt, «có thể đổi»), baseline. Legend ghi chữ cho mọi màu.
* **Tooltip / panel chi tiết:** rê chuột → trạng thái sau nến, ATR, Range khoá,
  công thức Δ với số thực, điều kiện xác nhận, nhãn + dung sai. Bấm một dòng trong
  bảng sự kiện → panel «Chi tiết sự kiện được chọn» + hiện điểm xác nhận của pivot.
* **So sánh baseline (pivot 3/3):** chạy `swing_pivot` 3/3 không đổi trên cùng
  dataset/khoảng (kiểm checksum), phủ marker «B» theo wick, cảnh báo «baseline theo
  WICK, DC theo CLOSE». Lưu run nếu đang bật «Lưu» → chọn hai run ở tab Lịch sử để
  so sánh bảng.
* **Panel baseline đồng bộ:** tích «Baseline ở panel riêng (đồng bộ)» → chart thứ
  hai dưới chart chính, cùng chuỗi nến. Cuộn/zoom ở chart nào thì chart kia theo
  (theo logical range); crosshair theo nhau, tooltip chỉ hiện ở chart đang rê
  chuột. Replay: cả hai cùng con trỏ, baseline cũng chỉ hiện pivot đã xác nhận.
  Chỉ hiện khi run baseline cùng khoảng nến với chart đang xem (nếu khác thì ẩn
  cả overlay lẫn panel, tránh lệch bar_index). Hai chart chia nhau chiều cao.
* **Ẩn chữ khi zoom xa:** khi khoảng cách trung bình giữa các marker DC trong
  khung nhìn < 26 px, chữ HH/HL… và «ứng viên» bị ẩn (marker giữ nguyên; legend
  ghi «chữ nhãn đang ẩn vì zoom xa»). Chỉ đổi phần vẽ, không đổi dữ liệu.
* **Bàn phím trên bảng sự kiện:** Tab vào bảng; ↑/↓, PageUp/PageDown, Home/End di
  chuyển; Enter/Space chọn dòng (mở panel chi tiết, hiện điểm xác nhận).
  Roving tabindex + `aria-selected`.
* **Replay:** tiến/lùi/phát/về đầu, «Tới xác nhận kế tiếp ⏭» (tiến từng nến tới
  khi có sự kiện mới, không nhìn trước). Lùi = dựng lại từ đầu → ứng viên, Δ,
  regime tại con trỏ đúng (test API + smoke). Tab Thống kê hiện pha detector, ứng
  viên, Range khoá, segment tại con trỏ.
* **Replay từ vùng đang xem (học cách thuật toán chạy):** sau khi chạy, nút nổi
  «▶ Replay từ vùng đang xem» trên chart mở replay với **đúng tham số của lần chạy
  đang hiển thị**, nhảy tới nến đầu vùng nhìn (thuật toán vẫn chạy nhân quả từ nến
  #0 tới đó) và tự bật lớp ứng viên + đường chấm vàng «mức xác nhận» (ứng viên ∓ Δ
  đã khoá). Khung «Thuật toán đang làm gì» (bên trái chart, tắt bằng ô «Giải
  thích») mô tả mỗi nến: (1) điều vừa xảy ra — đặt anchor, chọn hướng, ứng viên
  dời và Δ khoá lại, xác nhận pivot kèm bất đẳng thức với số thực + nhãn HH/HL…,
  đổi trạng thái, gap reset/nối; (2) trạng thái detector — ứng viên, Δ, mức xác
  nhận, còn cách bao xa, thanh «đã đảo chiều x % Δ»; (3) trạng thái Trend/Range và
  lý do. Nhảy nhiều nến (seek/tới xác nhận) thì chỉ mô tả trạng thái hiện tại.
* **Replay nhẹ:** mọi thao tác replay gửi `since` = con trỏ client đang có; server
  chỉ trả sự kiện/timeline mới hơn (`delta_since`, an toàn nhờ nhân quả). Ở nến
  ~20 000 của XAUUSD M15, mỗi bước giảm từ ~10,8 MB xuống ~11 KB; lần nhảy đầu vẫn
  tải đủ lịch sử một lần. Không gửi `since` = hành vi cũ (trả đủ).
* **Trạng thái riêng:** loading, lỗi, «chưa có pivot DC», warm-up, gap/segment,
  «chưa có nhãn tham chiếu», «dữ liệu MÔ PHỎNG».

## 8. Thí nghiệm đối chứng (dữ liệu thật)

Snapshot: **XAUUSD M15 · HistData 2024 (từ M1)**, `ds_564bff443e42`, checksum
`40dd738276fa4b7d…`, 23 713 nến, 260 gap (199 nghỉ phiên ~1,25 h, 46 cuối tuần…),
segment liên tục trung vị 92 nến. Đoạn phát triển 01/01–31/08/2024, đoạn kiểm tra
01/09–31/12/2024 (cố định trước khi chạy). Classifier giữ mặc định. Tái lập:
`research/dc_experiment.py --dataset ds_564bff443e42 [--save]` (lần chạy khô và lần
lưu cho số giống hệt). Run đã lưu mang nhãn `[DC thí nghiệm 20260925] …`.

| Đoạn | Cấu hình | run_id | Pivot | /1000 nến | Trễ TV/P90 (nến) | Đảo chiều/ATR TV | Nhịp/ATR TV/P90 | Tăng/Giảm/Range/Chưa rõ | Chuyển | Range |
|---|---|---|---:|---:|---|---:|---|---|---:|---:|
| dev | baseline pivot 3/3 (wick) | run_ffdfe8c75f58 | 2971 | 187.5 | 3 / 3 | — | — | — | — | — |
| dev | pivot CLOSE 3/3 (harness, không lưu) | — | 3199 | 201.9 | 3 / 3 | — | — | — | — | — |
| dev | DC percent 0.2% | run_4f57fdf0b4b8 | 779 | 58.0 | 3 / 8 | 1.73 | 2.90 / 7.77 | 6.6/6.6/0.0/86.8 % | 165 | 0 |
| dev | DC ATR14 k=1.0 | run_c41d5fe28795 | 1532 | 114.2 | 2 / 5 | 1.28 | 2.19 / 6.03 | 18.5/15.3/0.0/66.2 % | 539 | 1 |
| dev | DC ATR14 k=1.5 | run_dc371ed15e4f | 856 | 63.8 | 3 / 8 | 1.84 | 3.07 / 7.77 | 11.4/8.4/0.0/80.2 % | 196 | 0 |
| dev | DC ATR14 k=2.0 | run_d5d14dcbc80a | 553 | 41.2 | 4 / 11 | 2.34 | 4.07 / 8.75 | 5.4/3.2/0.0/91.4 % | 74 | 0 |
| test | baseline pivot 3/3 (wick) | run_744dcfe46c22 | 1497 | 190.3 | 3 / 3 | — | — | — | — | — |
| test | pivot CLOSE 3/3 (harness, không lưu) | — | 1585 | 201.5 | 3 / 3 | — | — | — | — | — |
| test | DC percent 0.2% | run_ed47bffd0497 | 409 | 61.4 | 3 / 9 | 1.84 | 2.99 / 6.64 | 6.4/8.1/0.0/85.4 % | 97 | 1 |
| test | DC ATR14 k=1.0 | run_807293a1a561 | 774 | 116.3 | 2 / 5 | 1.30 | 2.31 / 5.85 | 15.7/16.1/0.1/68.0 % | 275 | 2 |
| test | DC ATR14 k=1.5 | run_558116cbfe15 | 446 | 67.0 | 3 / 8 | 1.85 | 3.20 / 6.88 | 8.8/12.2/0.1/78.9 % | 116 | 1 |
| test | DC ATR14 k=2.0 | run_5b2dd3522f41 | 285 | 42.8 | 4 / 11 | 2.38 | 3.75 / 7.48 | 3.5/5.4/0.0/91.1 % | 43 | 0 |

Mật độ: baseline/harness chia cho mọi nến; DC chia cho nến đã có ATR (sau warm-up
mỗi segment). «Nhịp/ATR» = |pivot − pivot trước| / ATR tại pivot đầu nhịp.

**Đọc kết quả (không kết luận «tốt hơn»):**

* DC giảm số pivot so với 3/3: ≈ 1,9 lần (k = 1,0), 3,5 lần (k = 1,5), 5,4 lần
  (k = 2,0), 3,8 lần (0,2 %) trên đoạn dev. Pivot close 3/3 còn nhiều hơn wick 3/3
  (+6–8 %), nên phần giảm đến từ **ngưỡng** chứ không phải từ việc dùng close.
* Mỗi tăng k: ít pivot hơn, nhịp lớn hơn, trễ dài hơn (TV 2 → 3 → 4 nến, P90
  5 → 8 → 11). Đây là đánh đổi, không có điểm tối ưu nếu chưa có nhãn.
* Các chỉ số dev và test gần nhau cho cùng cấu hình (ổn định theo thời gian ở mức
  mô tả hành vi). ATR k = 1,5 và percent 0,2 % cho mật độ tương tự trên giai đoạn
  này; **chưa có bằng chứng ATR tốt hơn percent** — cần nhãn tham chiếu.
* «Chưa rõ» chiếm 66–91 % thời gian và Range gần như không xuất hiện (≤ 0,1 %).
  Nguyên nhân chính: `gap_policy=reset` cắt dữ liệu thành segment ~92 nến, mỗi
  segment phải warm-up 15 nến và cần ≥ 2 đỉnh + 2 đáy (trend) hoặc ≥ 3 + 3
  (Range) mới phân loại được. Đây là giới hạn của định nghĩa hiện tại trên
  XAUUSD M15, không phải trạng thái thị trường.

### 8b. Cùng cấu hình với `gap_policy = bridge_short` (≤ 2 giờ)

Cùng snapshot, cùng hai đoạn, classifier mặc định; baseline không phụ thuộc gap
nên không chạy lại. `research/dc_experiment.py --gap-policy bridge_short --bridge-hours 2 [--save]`.
Toàn năm: 200 gap được nối, 60 gap reset → 61 segment (so với 261).

| Đoạn | Cấu hình | run_id | Pivot | /1000 nến | Trễ TV/P90 (nến) | Đảo chiều/ATR TV | Nhịp/ATR TV/P90 | Tăng/Giảm/Range/Chưa rõ | Chuyển | Range |
|---|---|---|---:|---:|---|---:|---|---|---:|---:|
| dev | DC percent 0.2% | run_a5b9d3fec479 | 968 | 63.3 | 4 / 11 | 1.80 | 3.13 / 8.00 | 25.1/23.7/0.0/51.2 % | 426 | 0 |
| dev | DC ATR14 k=1.0 | run_d84a10cb740e | 1818 | 118.9 | 2 / 6 | 1.27 | 2.18 / 5.65 | 29.3/24.3/0.0/46.4 % | 859 | 1 |
| dev | DC ATR14 k=1.5 | run_9c3dd9e21889 | 1032 | 67.5 | 4 / 10 | 1.80 | 3.12 / 7.80 | 27.1/23.3/0.0/49.6 % | 466 | 0 |
| dev | DC ATR14 k=2.0 | run_0a0d4be6cc9b | 665 | 43.5 | 5 / 17 | 2.32 | 4.12 / 9.57 | 23.2/18.8/0.0/58.1 % | 285 | 0 |
| test | DC percent 0.2% | run_3985e17e58ed | 503 | 66.4 | 4 / 11 | 1.95 | 3.22 / 7.48 | 28.0/19.8/0.0/52.2 % | 228 | 1 |
| test | DC ATR14 k=1.0 | run_f234751ea663 | 898 | 118.6 | 2 / 5 | 1.29 | 2.27 / 5.66 | 28.4/21.4/0.2/50.0 % | 426 | 3 |
| test | DC ATR14 k=1.5 | run_f17086308d20 | 520 | 68.7 | 3 / 10 | 1.85 | 3.22 / 7.48 | 24.7/22.9/0.1/52.3 % | 243 | 1 |
| test | DC ATR14 k=2.0 | run_50e809ddd88e | 364 | 48.1 | 4.5 / 15 | 2.33 | 3.79 / 8.38 | 25.6/20.8/0.0/53.6 % | 155 | 0 |

**Đọc kết quả:** nối gap ngắn giảm «Chưa rõ» từ 66–91 % xuống 46–58 % và tăng số
pivot 12–22 % (ít mất nhịp đầu phiên vì không phải warm-up lại). Đổi lại, trễ P90
tăng (vd k = 2,0: 11 → 17 nến trên dev) vì ứng viên sống qua đêm. **Range vẫn gần
như không xuất hiện (≤ 0,2 %)** — nguyên nhân giờ nằm ở chính điều kiện Range
(m = 3 mỗi phía, cụm ≤ 0,5 × ATR), không phải ở gap. Muốn Range có ý nghĩa cần
xem lại tham số Range; chưa chỉnh vì chưa có nhãn để tránh tối ưu theo mắt.

## 9. Quyết định thực tế và khác biệt so với plan

1. **Thêm tham số `timeframe`.** Engine không truyền timeframe cho thuật toán, và
   với quy ước timestamp «close» không suy được bước khung từ một nến. Giống
   `c2_cisd_research` (`ltf`), tham số được kiểm bằng `check_dataset` và form tự
   điền — không phải cấu hình thí nghiệm.
2. **Không đổi contract engine/storage.** Chỉ thêm `ParamSpec.show_if` (tuỳ chọn),
   `ReplaySession.step_until_event` và endpoint `next-event`; thuật toán khác không
   đổi output (36/36 run đã lưu trước đó chạy lại khớp event_id).
3. Sau reversal, ứng viên mới = close nến xác nhận (đúng spec) → một nến có thể
   vừa là nến xác nhận đáy vừa là nến cực trị của đỉnh kế tiếp. «Tối đa một pivot
   mỗi nến» áp dụng cho lần xác nhận.
4. Pha `WAIT_ATR` giữa chừng khởi tạo lại từ anchor mới nên có thể phá tính luân
   phiên high/low. Thực tế gần như không xảy ra: có cực trị mới hoặc đảo chiều ≥ Δ
   thì TR > 0 nên ATR > 0. Ghi lại để không ngạc nhiên.
5. Timeline có giá trị giả `regime = "WARMUP"` khi chưa có ATR (sau gap) — không
   phải regime, không cộng vào tỷ lệ thời gian.
6. `reference_event_id` của sự kiện regime = pivot đỉnh trong bằng chứng; toàn bộ
   ID bằng chứng ở `details.bang_chung` / `details.range.evidence_ids`.
7. Tham số lạ bị từ chối (các thuật toán cũ bỏ qua). Có chủ đích để tránh gõ sai.
8. `bridge_short` là mở rộng ngoài plan (plan chỉ có `reset`), thêm theo yêu cầu
   sau bàn giao 0.1.0; mặc định vẫn `reset` để run cũ không đổi.
9. Ẩn chữ nhãn theo **mật độ marker DC** (px / nhãn) chứ không theo px / nến: pivot
   DC thưa (~1 / 15 nến) nên ở khung mặc định 350 nến chữ không đè nhau.
10. Panel đồng bộ: chart chính là chart «dẫn» khi khung nhìn đổi do chương trình
    (nạp nến, showLast, replay); chart baseline chỉ đẩy ngược khi người dùng cuộn.
    Panel baseline giảm lề trục giá và cỡ marker (autoscale của LWC chừa chỗ cho
    marker theo pixel, làm nến bị ép khi panel thấp).
11. Quan sát ngoài phạm vi (không sửa): helper vẽ `levelSeriesData` của C2 tiếp tục
   phát điểm trong suốt ở mức cũ sau khi mức kết thúc, có thể làm giãn autoscale
   trục giá khi xem vùng xa. Biên Range của DC dùng hàm riêng `rangeSeriesData`
   để tránh lỗi này.

## 10. Giới hạn đã biết

* Chưa có nhãn tham chiếu cho swing close hay đoạn regime → không có precision,
  recall, F1, confusion matrix; UI ghi rõ, không tự tạo.
* `reset` làm «Chưa rõ» chiếm đa số trên XAUUSD M15 (§8); `bridge_short` giảm còn
  ~50 % nhưng chỉ dựa vào độ dài gap, chưa dùng lịch phiên broker.
* Range gần như không kích hoạt với tham số mặc định trên dữ liệu này (§8b).
* Metric có nhãn: chưa có bộ nhãn swing close hay giao diện gán nhãn **đoạn**
  regime; chỉ có chấm chéo định nghĩa DC ↔ nhãn swing theo wick.
* Chưa có: multi-timeframe, protected swing, BOS/MSS, simulator, tối ưu tự động,
  downsample khi vẽ (23 713 nến M15 vẽ mượt; chỉ nên làm khi đo được vấn đề hiệu
  năng, vd dataset M1). Panel đồng bộ chỉ cho baseline swing_pivot 3/3.
* Chỉ đã thử trên XAUUSD M15 HistData 2024 và dữ liệu MÔ PHỎNG (synthetic —
  chỉ để test). Không hardcode giá XAUUSD.

## 11. Kiểm thử

```powershell
.\.venv\Scripts\python.exe -m pytest                       # toàn bộ: 343 passed
.\.venv\Scripts\python.exe -m pytest tests\algorithms\test_dc_atr_structure.py tests\algorithms\test_dc_regime.py tests\api\test_dc_api.py
```

* Detector/ATR: seed tính tay, warm-up n+1, ATR 0, NaN/inf/OHLC sai, trùng/lùi
  thời gian, sai khung, đơn điệu, đi ngang, thiếu/đúng/vượt ngưỡng, đỉnh bằng nhau,
  Δ khoá khi ATR đổi, ứng viên mới khoá Δ mới, percent 0,25 % tính tay, wick lớn,
  luân phiên, một pivot/nến, gap reset, validate tham số; `bridge_short`: nối gap
  ngắn giữ ứng viên/segment, TR tính với close trước gap (tính tay), gap dài vẫn
  reset, pivot nối qua gap tham chiếu pivot trước gap, prefix = full, `reset` mặc
  định không đổi.
* Classifier: HH+HL, LH+LL, HH+LL, thiếu pivot, EQ, Range đạt / cụm rộng / chồng
  nhau / hẹp / close ngoài, khoá biên, chạm đúng biên+buffer chưa thoát, breakout
  chặn phân loại cùng nến, range → trend, reset, tham số sai.
* Nhân quả: 8 prefix (2 mode × 4 điểm cắt, có gap) so với full lọc theo lúc biết
  — cả sự kiện (toàn bộ `to_dict`) lẫn timeline; sửa đuôi sau T; deep-copy phát
  hiện mutation; batch = tuần tự; replay lùi = chạy prefix mới (pending + timeline).
* Tích hợp API: registry/`show_if`, 400 khi sai tham số/khung, run → save → get →
  CSV → manifest, so baseline cùng checksum, replay next-event + lùi.
* Browser smoke (Chrome headless qua CDP, DB bản sao): 23/23 kiểm tra đạt — chạy,
  form `show_if`, lớp hiển thị, chọn pivot xem công thức, baseline, đổi mode tạo
  run mới, replay tới xác nhận/lùi khôi phục trạng thái, mở lại run (tái lập khớp),
  export CSV/manifest, không lỗi JS.
* Smoke replay từ vùng đang xem: 16/16 — nút ẩn/hiện đúng lúc, con trỏ = nến đầu
  vùng nhìn, khung giải thích đủ 3 phần, bước 1 nến / tới xác nhận có mô tả sự
  kiện, mức xác nhận + tiến độ, lùi khôi phục đúng, phản hồi step ~11 KB, ẩn/hiện
  khung, replay từ đầu vẫn chạy, không lỗi JS. Test API ghép delta = bản đầy đủ
  (tiến, tới xác nhận, lùi, seek lùi).
* Smoke 0.2.0: 19/19 — form `bridge_short`, ghi chú gap nối, ẩn/hiện chữ khi
  zoom xa/gần, bàn phím (↓×3, Enter, End), panel baseline hiện + cuộn hai chiều
  đồng bộ, rê chuột chỉ bật tooltip chart đang trỏ, replay với panel, ô tích so
  chéo trên trang Đánh giá (khoá khi mục tiêu cấp 2, cảnh báo khi bật), không lỗi JS.
