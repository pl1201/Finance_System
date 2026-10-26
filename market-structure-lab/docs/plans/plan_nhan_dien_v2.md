# Plan: lớp nhận diện v2 — trạng thái thị trường, giao diện, kiểm chứng

**Trạng thái: đã chốt (22/10/2026)**, đang làm (§6). Nối tiếp [`plan_nhan_dien_trang_thai.md`](plan_nhan_dien_trang_thai.md)
(v1 đã lên web trong `ict_structure` 0.6.0–0.8.0, đặc tả [`thuat_toan_nhan_dien.md`](../algorithms/thuat_toan_nhan_dien.md)).
Mọi số đo ở đây chỉ dùng dữ liệu dev (< 2024-09-01). Ảnh chụp người dùng gửi ngày 22/10 thuộc đoạn test: chỉ dùng để
nhận xét giao diện, không dùng để chỉnh ngưỡng.

## 1. Vì sao làm lại

**Thuật toán trạng thái v1 quá dè dặt.** Đo trên XAUUSD / EURUSD M15, 2021–2023 (script ở §9):

| | v1 (lõi 0.8.0) | Chuẩn phổ biến cùng dữ liệu |
|---|---|---|
| Thời gian «nhiễu» | **78–79%** | — |
| Thời gian trend | 17–18% | ADX(14) > 25: 42–44% |
| Thời gian range | 2% | Range Detector (LuxAlgo, 20 nến): ≈ 5%; Choppiness > 61,8: 11–12% |
| Thời gian nén | 0,8–1,2% | TTM Squeeze: 25–28% |
| Nến đi một chiều rõ (8 giờ ≥ 3 ATR và ADX > 25) bị gọi «nhiễu» | **43%** | — |
| Trend của v1 có ADX > 25 | 86–90% | — |
| Độ dài trung vị của đoạn range | 4 nến (1 giờ) | — |

Tức là v1 **đúng khi đã gọi**, nhưng bỏ sót gần nửa số nhịp trend nhìn thấy được (ER 8 giờ ≥ 0,3 đòi giá đi
≈ 6 ATR mới nhận), range gần như không bao giờ có, và hộp range nhấp nháy (1 giờ). Đây là điều người dùng thấy trên
chart: nhịp tăng rõ vẫn ghi «nhiễu».

**Giao diện** (theo ảnh người dùng gửi và đối chiếu §2):

1. Bên phải chart có ~10 nhãn số chen nhau (PDH 0%, PDL 1%, 1h 80%, 4h 80%, hai dòng «chạm …», BSL / SSL / H1).
   Mức xa (p < 10%) vẫn hiện; nhãn xác suất tách khỏi tên mức; không ghi cỡ mẫu.
2. Không có chỗ đọc nhanh «bây giờ thế nào»: trạng thái, còn giữ, khoảng, mức gần nằm rải ở hàng 3 dòng trạng thái,
   tooltip và «Đang theo dõi».
3. Hai dải dưới (trạng thái / order flow) đọc ngược nhau mà không giải thích (order flow «↓ run SSL» trong khi giá
   tăng và trạng thái «nhiễu»).
4. Khoảng 1h / 4h là hai hộp chữ nhật xếp chồng — không thể hiện độ bất định tăng theo thời gian.

## 2. Tham khảo đã xem (22/10/2026)

| Công cụ / mã nguồn | Cách tính (tóm tắt) | Cách vẽ | Lấy gì cho lab |
|---|---|---|---|
| [Smart Money Concepts — LuxAlgo](https://www.tradingview.com/script/CnB3fSph-Smart-Money-Concepts-SMC-LuxAlgo/) | Swing (50) và internal (5); BOS / CHoCH khi close phá đỉnh / đáy; xu hướng = chiều lần phá gần nhất (luôn lên hoặc xuống) | Internal nét đứt nhãn rất nhỏ, swing nét liền; chế độ Present / Historical | Hai tầng nét, chế độ Live / Review; xu hướng giữ tới khi CHoCH |
| [Range Detector — LuxAlgo](https://www.tradingview.com/script/QOuZIuvH-Range-Detector-LuxAlgo/) | 20 close đều trong SMA20 ± 1·ATR dài; hộp kéo dài tới khi close ra ngoài; gộp hộp chồng | Hộp + đường giữa chấm; biên đổi màu khi phá lên / xuống | Hộp range bền, tô màu theo phá biên |
| [TTM Squeeze](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/ttm-squeeze), [Choppiness](https://www.luxalgo.com/library/concept/choppiness-index.md), ADX / DI | BB(20,2) trong KC(20,1,5); CHOP 14 (38,2 / 61,8); ADX 14 (20 / 25) | Chấm / dải / tô nền | Nén là **cờ biến động**, không phải trạng thái loại trừ; ADX / CHOP làm thước đối chiếu |
| [Regime Detector — StrixEDGE](https://ru.tradingview.com/script/JKwUOYDQ-Regime-Detector-StrixEDGE/) | ADX + RSI + KAMA + ATR → mạnh / yếu / range / nhiễu | Tô nền (range xanh dương, nhiễu vàng cam), dấu đổi trạng thái, bảng góc | Bảng góc, dấu đổi trạng thái |
| [Liquidity Draw Probability Map — ForexCracked](https://de.tradingview.com/script/l4nMbqY8-Liquidity-Draw-Probability-Map-ForexCracked/) | Tỷ lệ tới mức theo loại × khoảng cách ATR; mẫu < 20 → «building» | «reach X% of N», nét đậm theo xác suất, giới hạn số mức mỗi phía | Nhãn kèm n, ẩn khi thiếu mẫu, ≤ 2 mức mỗi phía |
| [Probability Cone](https://de.tradingview.com/script/tMPjsTe2-Probability-Cone-Forecast/) (ChartPrime và các bản khác) | σ × √t | Hình nón mờ dần theo tầm | Khoảng 1h / 4h vẽ thành nón |
| [smart-money-concepts (Python)](https://github.com/joshyattridge/smart-money-concepts) | swing cửa sổ giữa (nhìn trước ~50 nến), BOS / CHoCH quét về sau | — | **Không** dùng được nến-theo-nến; chỉ lấy mẫu so thứ tự mức BOS / CHoCH |
| [jump-models](https://github.com/Yizhan-Oliver-Shu/jump-models), hmmlearn | Chế độ có phạt chuyển; `predict` nhìn cả chuỗi, chỉ `predict_online` / lọc tiến là nhân quả | — | Ý tưởng «phạt đổi trạng thái» = trễ vào / ra; thước đối chiếu sau này |
| [Repainting — Pine docs](https://www.tradingview.com/pine-script-docs/concepts/repainting/) | — | — | Ghi rõ nến xác nhận; chấm từ lúc xác nhận |

Nhận xét chung: **không công cụ nào công bố hiệu chuẩn** cho xác suất của mình (ForexCracked gần nhất: có n, có ngưỡng
mẫu). Lab đã tự chấm mọi xác suất trong lần chạy — giữ lợi thế này, chỉ cần hiện gọn hơn.

## 3. Thuật toán trạng thái v2

### 3.1 Hai trục, bốn trạng thái + một cờ

- **Trục hướng / hiệu quả** (loại trừ nhau): `trend_len`, `trend_xuong`, `range`, `nhieu`.
- **Cờ nén** (`nd_nen`, có thể đi cùng range hoặc nhiễu): biến động co lại — BB(20,2) trong KC(20,1,5) và độ rộng BB
  thuộc 20% thấp nhất của 500 nến. Quy tắc v1 (3 đỉnh thấp dần + 3 đáy cao dần) thành điểm «nén mạnh».
- Lý do: trend / range đo hướng và độ hiệu quả, nén đo biến động — gộp vào một trục làm «nén» chiếm chỗ của range
  (tham khảo TTM, CHOP, khái niệm trend / range classifier của LuxAlgo).

### 3.2 Bằng chứng mỗi nến (nhân quả, chỉ dữ liệu ≤ t)

| Bằng chứng | Định nghĩa | Đã có trong lõi? |
|---|---|---|
| Cấu trúc M15 | thứ tự ITH / ITL của chính `ict_structure` (`order`: +1 HH-HL, −1 LH-LL, 0 chưa rõ) | có |
| Cấu trúc H1 | `htf_H1_order` | có |
| Hiệu quả | ER 16 và ER 32 nến | có (ER 32) |
| Lực có hướng | ADX(14), +DI / −DI | thêm |
| Động lượng | (C_t − C_{t−32}) / ATR | thêm (rẻ) |
| Hộp range | (a) 20 close trong SMA20 ± 1·ATR dài (Range Detector); (b) hộp swing: cấu trúc chưa rõ, rộng 1,5–5 ATR, ER32 < 0,3 | (b) gần như có |
| Nén | TTM + phân vị độ rộng BB | thêm |

### 3.3 Luật vào / ra (có trễ — vào chặt, ra lỏng)

1. **Trend lên — vào** khi cả ba: cấu trúc M15 không ngược (`order` ≥ 0) và (cấu trúc lên ở M15 hoặc H1); bằng chứng
   lực (ER32 ≥ `nd_er_vao` hoặc ADX ≥ 20 với +DI > −DI); động lượng 32 nến > 0. Hoặc ER32 ≥ 0,3 như v1 (giữ đường
   vào cũ cho nhịp rất thẳng).
   **Ra** khi: cấu trúc M15 đổi chiều (CHoCH — `order` = −1), hoặc lực tắt hẳn (ER32 < `nd_er_ra` và ADX < 18). Trend
   xuống: đối xứng.
2. **Range — vào** khi không trend và có hộp (a) hoặc (b). Biên = max high / min low của cửa sổ phát hiện; hộp chồng
   hộp trước thì gộp. **Giữ** tới khi 2 close liên tiếp ra ngoài biên quá 0,25 ATR (= phá biên — cũng là kết cục của
   xác suất phá biên). Số lần chạm mỗi biên thành **điểm chất lượng** (hiện ở bảng), không còn là điều kiện.
3. **Nhiễu**: còn lại.
4. **Giữ tối thiểu** `nd_giu_nen` = 2 nến cho mọi lần đổi (như v1).
5. **Độ mạnh trend** 0–1 (để hiển thị độ đậm, không phải xác suất): trung bình chuẩn hoá của ER32, ADX, |động lượng|.

Tham số mới (nâng cao, có mặc định): `nd_kieu` (`v2` mặc định / `v1` giữ cách cũ để so), `nd_er_vao` (0,18),
`nd_er_ra` (0,10). Ngưỡng chốt trên dev theo §5, ghi vào sổ thử.

### 3.4 Ảnh hưởng tới các phần khác

- Phá biên range, còn giữ / thời gian còn lại dùng đoạn và hộp v2 (cùng code, khác đầu vào) — chấm lại trên dev.
- Khoảng giá, xác suất chạm, sự kiện ICT không đổi. Sự kiện `STATE_*` đổi theo trạng thái v2; thêm cột timeline
  `nd_nen`, `nd_do_manh`. Phiên bản `ict_structure` 0.9.0; `nd_kieu = v1` cho output trạng thái như 0.8.0.

## 4. Giao diện v2

```
┌─ chart ───────────────────────────────────────────────┬─ Nhận diện (gọn được) ───────────┐
│                                   ░░ nón 4h 80% ░░     │ Trạng thái  trend ↑  (2.5h, mạnh) │
│      ╭─╮                       ░▒▒ nón 1h ▒▒░          │ Còn giữ 4h  62%  · còn ~1.5h      │
│  ╭──╯  ╰╮ ╭╮        ── BSL H1 · 4h 41% (n 212) ────    │ Khoảng 4h   [4296 – 4362]  80%    │
│ ─╯       ╰╯╰─ ●    ·· BSL · 4h 68% (n 380) ·······     │ Gần nhất    BSL 68% · SSL 44%     │
│                    ·· SSL · 4h 44% (n 371) ·······     │ Nén         không                 │
│                                                        │ Điểm thật   phủ 80%: 80.9% · …    │
├─ dải trạng thái  ▌trend ↑ ▌nhiễu ▌range ▌ (◆ = đổi) ──┤                                   │
├─ dải order flow ─────────────────────────────────────┤                                   │
└────────────────────────────────────────────────────────┴───────────────────────────────────┘
```

1. **Hai chế độ** (như LuxAlgo Present / Historical): **Live** (mặc định) — chỉ nhịp hiện tại, hộp range hiện tại,
   mức gần, nón, bảng; **Review** — toàn lịch sử, dải trạng thái, hộp range đã qua.
2. **Bảng «Nhận diện»** ở góc phải trên, thu gọn được: mọi con số một chỗ, mỗi số kèm tầm và điểm thật (n).
   Hàng 3 dòng trạng thái trên cùng rút còn «trạng thái + khoảng 4h».
3. **Mức**: tối đa 2 mỗi phía; ẩn khi p 4h < 10% hoặc nằm ngoài nón 80% 4h; gộp mức cách nhau < 0,15 ATR thành một
   đường ghi đủ tên; nhãn một khối «BSL H1 · 4h 41% (n 212)»; nét đậm theo xác suất; n < 30 → «đang gom mẫu».
4. **Khoảng giá thành nón**: lõi 50% đậm, 80% nhạt, mờ dần theo tầm; bỏ nhãn «1h 80%» / «4h 80%» rời (số nằm ở bảng).
5. **Dải trạng thái**: giữ dải dưới; thêm dấu ◆ ở nến đổi trạng thái; tô nền rất nhạt cho range (xanh dương) và trend
   (theo chiều) — bật / tắt được; nén = gạch chéo mảnh trên dải. Không đổi màu nến.
6. **Hộp range** kiểu Range Detector: hộp + đường giữa chấm; biên đổi màu khi phá lên / xuống; xác suất phá biên ghi
   một lần ở mép phải hộp.
7. **Order flow và trạng thái**: chú thích dải ghi rõ «order flow = chiều thanh khoản bị lấy gần nhất (ICT), trạng thái
   = hình dạng giá 8 giờ» để hai dải ngược nhau không gây hiểu lầm.
8. **Kiểm chéo nội bộ** (chỉ trong tab Thống kê): xác suất chạm mép nón 80% ≈ 2 × 10% theo nguyên lý phản xạ — lệch
   nhiều nghĩa là một trong hai mô hình sai.

**Đã làm (22/10/2026, bước 4)** — khác thiết kế ở hai chỗ, đều có lý do:

- **Nón bậc, không nội suy √t** (thay 25/10 bằng hai vùng lồng nhau — mục kế dưới). Lõi chỉ tính và chấm khoảng ở 1h và 4h; nội suy giữa hai tầm là giao diện tự đặt ra
  số dự báo (AGENTS §8). Vẽ: khoảng 1h từ con trỏ tới +1h, khoảng 4h nối tiếp tới +4h (khoảng của cả đường giá 4h nên
  cũng đúng ở mọi thời điểm trước đó), 80% viền đứt, lõi 50% đậm, tầm sau mờ hơn.
- **Hai vùng lồng nhau thay nón bậc** (25/10/2026 — người dùng: khung hộp nét đứt khó hiểu): vùng 4h (nhạt, dài) và
  vùng 1h (đậm hơn, ngắn, nằm trong) CÙNG bắt đầu ở con trỏ, không viền, lõi 50% đậm hơn, nhãn giá ở mép phải (kẹp mép
  khi ngoài khung giá). Đã thử nón quạt (từ close nối thẳng tới mốc 1h rồi 4h) và bỏ: nón hẹp hơn khoảng của lõi ở đoạn
  đầu — khoảng là của CẢ đường giá, đúng ngay từ nến kế tiếp — nên giá vượt mép nón chưa chắc ra khỏi khoảng (người dùng
  chọn lại sau khi được giải thích). Nón quạt thật cần lõi tính thêm mốc (15m, 30m, 2h…) — để sau.
- **Bỏ vùng khoảng giá khỏi chart** (25/10/2026, người dùng: «không cần»): lớp `ict_nd_band` chỉ còn «Xác suất chạm 1h /
  4h» (đường chấm trên mức); số khoảng 80% / 50% vẫn ở bảng «Nhận diện», dòng trạng thái, «Đang theo dõi», tab Thống kê.
- **Bảng «Nhận diện» ở cột trái** dưới dòng trạng thái (thu gọn được) — đặt góc phải thì che nến mới nhất và nón.
- Có: mức gọn (trong khoảng 80% 4h, p ≥ 10%, ≤ 2 mỗi phía, nét đậm theo p, bảng ghi đúng các mức đang vẽ), hộp range kiểu
  Range Detector (đường giữa chấm; range đã qua tô xanh / đỏ theo chiều phá, tooltip ghi bằng chữ), lớp «Lịch sử range»
  (mọi range đã qua, tối đa 40), dải mảnh «nén», bảng ghi điểm thật lõi gửi kèm, chú thích hai dải trạng thái / order flow.
- **Đường trend thay dải «trạng thái»** (người dùng chọn 22/10, sau khi xem dải): đường bậc thang trên giá — xanh dưới
  giá khi trend ↑ (đáy 4 giờ trước: close thủng là hết trend), đỏ trên giá khi trend ↓, chàm giữa hộp khi range, không
  vẽ khi nhiễu (lõi 0.9.1, cột `nd_duong`). Dải order flow giữ nguyên; dải trạng thái chỉ còn cho run v1.
- **Khung trạng thái dưới chart** (người dùng yêu cầu 22/10: «khung chart ở dưới chart chính … trending, range,
  sideway»): lớp `ict_nd_pane` (bật sẵn) — chart riêng ngay dưới chart giá, cùng trục thời gian (cuộn / zoom / crosshair
  đồng bộ hai chiều, nến thẳng hàng), một cột mỗi nến đọc thẳng cột timeline của lõi: trend ↑ xanh / ↓ đỏ, cao theo
  `nd_do_manh` (chỉ để hiển thị); range khối chàm đối xứng quanh 0; sideway nhiễu vạch xám mảnh; dải tím trên cùng = cờ
  nén; trống = chưa đủ nến. Dòng chữ trên khung: chú giải màu + trạng thái ở nến dưới chuột. Replay chỉ vẽ tới con trỏ.
  Hạ tầng chung [`chart/sub-pane.js`](../../frontend/js/chart/sub-pane.js) + hook plugin `pane` (hợp đồng ở đầu
  `algos/registry.js`) — thuật toán khác dùng lại được. Bộ trạng thái kiểm theo nhu cầu (khai trước, dev):
  [`kiem_dinh_trang_thai.md`](../research/kiem_dinh_trang_thai.md) — N1 (đúng và ổn định: nhân quả, ít nhấp nháy) đạt;
  N2 (khớp cấu trúc nhìn lại ±4 giờ — tham chiếu do lab chọn, chưa phải nhãn người), N3 (khác nhiễu so với random walk
  giữ mùa vụ), N4 (có ích cho router: trend → đi tiếp, range → giữ giá) không đạt → khung là mô tả hình dạng giá để nhìn,
  chưa đủ để làm regime cho chiến lược.
- Chưa làm: dấu ◆ ở nến đổi trạng thái; gộp mức cách nhau < 0,15 ATR; «(n …)» / «đang gom mẫu» trên nhãn mức (n có ở
  tooltip); chế độ Live / Review chung cho cả lớp ICT (plugin đã tạm bỏ «Lịch sử» từ 08/10 — cần người dùng chốt lại);
  kiểm chéo nguyên lý phản xạ trong tab Thống kê.

## 5. Kiểm chứng (khai trước — chỉ dev)

| Thước | Mục tiêu v2 |
|---|---|
| Nhân quả | chạy cắt ở nến t = chạy đủ rồi lọc (như mọi lớp) |
| Bắt nhịp một chiều rõ (8 giờ ≥ 3 ATR, ADX > 25) | ≥ 85% (v1: 56%) |
| Trend có ADX > 20 | ≥ 80% |
| Trend sai chiều so với tham chiếu nhìn lại ±16 nến | < 5% |
| Độ dài trung vị đoạn range | ≥ 12 nến (3 giờ) (v1: 4) |
| Range: giá còn trong hộp 1 giờ sau | cao hơn nhiễu, có CI khối tuần |
| Số lần đổi trạng thái | ≤ 10 / 100 nến |
| Ổn định: ngưỡng ± 20% | κ ≥ 0,7 so với mặc định |
| Nhãn tay (người dùng, ~150 cửa sổ ngẫu nhiên phân tầng, có «không chắc») | κ ≥ 0,6 |

**Kết quả (22/10/2026, dev 2018 → 08/2024, `khao_sat_trang_thai_v2.py` v1.2, bản sau code-review,
[`trang_thai_v2_dev.json`](../research/khao_sat/trang_thai_v2_dev.json))** — v2 mặc định, XAU / EUR:

| Thước | v1 | v2 | Đạt? |
|---|---|---|---|
| Bắt nhịp một chiều rõ | 56 / 55% | 88,3 / 87,8% | Đạt |
| Trend có ADX > 20 | 96 / 95% | 86,3 / 85,8% | Đạt |
| Sai chiều (±16 nến) | 7,7 / 7,2% | 12,5 / 12,7% | **Không** — mục tiêu 5% lấy theo prototype của agent (tham chiếu khác); đo trên dev, chính các nhịp rõ nhất gắn nhãn theo chiều 8 giờ đã sai 8–9%, phủ rộng như v2 thì ≈ 12%: đây là mức sàn của mọi nhãn nhân quả (nửa sau cửa sổ là tương lai) |
| Đoạn range trung vị | 4 / 4 nến | 13 / 11 nến | XAU đạt, EUR thiếu 1 nến (đếm đoạn cắt ở giai đoạn khởi động, v1.2) |
| Range giữ giá hơn hộp bất kỳ cùng bề rộng × vị trí (close trong hộp) | +0,3 / −1,3 điểm | 0,0 / −0,1 điểm (CI chứa 0) | **Không** — biên range không giữ giá hơn; range là mô tả |
| Đổi / 100 nến | 4,7 / 4,8 | 5,5 / 5,8 | Đạt |
| κ khi đổi ngưỡng ± 20% | — | 0,79–0,98 | Đạt |
| Nhãn tay | — | chờ người dùng gán | — |

Tỷ lệ thời gian v2: trend 49%, range 33%, nhiễu 18–19%, cờ nén 13–15%. Code-review (22/10) sửa ba lỗi luật — vào /
ra dùng chung định nghĩa «cấu trúc ngược chiều» (bản trước nhấp nháy khi mức bảo vệ đã phá), thủng kênh xét trước lực
tắt, chỉ báo bắt đầu lại sau khoảng trống — và chỉ dự báo phá biên / chạm biên khi close còn trong hộp; bảng trên là số
sau khi sửa (trước khi sửa: bắt rõ 85 / 84%, đổi 7,0 / 7,4). **Sổ thử (N = 18 cấu hình, tính cả bản sửa lỗi)**: định nghĩa
thử tay 3 (`proto_v2.py`: v2a / v2b / v2c); bản v2 đầu (chưa có kênh thoát, chưa có đường vào «lực mạnh», có nhánh
Range Detector) 1; 4 biến thể thoát (kênh 2 / 3 / 4 giờ, bỏ đường vào «lực mạnh» — kênh 4 giờ thành mặc định); 3 biến
thể hộp (chỉ hộp swing — thành mặc định vì gọn hơn mà gần như trùng, chỉ Range Detector, 3 lần thăm); lưới ổn định
± 20% (6 cấu hình). Phép đo «range giữ giá» sửa một lần sau khi xem số (v1.1: chỉ nến close trong hộp — hộp đối chứng
luôn chứa close). Chọn mặc định trước khi xem lưới
ổn định; không chọn lại theo kết quả (cấu hình hộp + 20% giữ giá dương nhưng range lên 43% thời gian — không dùng).

Không kỳ vọng trạng thái dự báo được hướng: đo trên dev, mọi biến thể đều có tỷ lệ «4 giờ sau cùng chiều trend» 48–49%.
Trạng thái là **mô tả**; phần dự báo vẫn là khoảng giá, xác suất chạm, phá biên — đã chấm sẵn.

## 6. Lộ trình

| Bước | Việc | Xong khi |
|---|---|---|
| 1 | **Xong 22/10.** Script `research/khao_sat_trang_thai_v2.py`: v1 / v2 cùng thước §5 trên dev, sổ thử | Bảng §5 (đạt 5/7, hai mục không đạt ghi lý do) |
| 2 | **Xong 22/10.** Thành phần `market_state_v2` — `ict_structure` 0.9.0, `nd_kieu` | Test tay + nhân quả; `nd_kieu = v1` = 0.8.0 (đã so tuyệt đối) |
| 3 | **Xong 22/10.** Phá biên / còn giữ theo đoạn v2; chấm lại | Điểm dev ghi vào đặc tả §5b |
| 4 | **Xong 22/10 (phần chính, xem §4 «Đã làm»).** Giao diện: bảng, mức gọn, nón bậc, hộp range, lịch sử range, dải nén | Ảnh chụp web thật, test hiển thị |
| 5 | Bộ nhãn tay trạng thái trên trang Gán nhãn (người dùng gán) | κ báo cáo |
| 6 | Kiểm một lần trên đoạn test (khi người dùng duyệt) | Ghi sổ, không sửa sau |

## 7. Không làm / giới hạn

- Không đổi màu nến theo trạng thái (một màu một nghĩa; nến giữ màu tăng / giảm).
- Không đưa HMM / jump model vào lõi ở bản này — chỉ làm thước đối chiếu nếu cần.
- Không gọi trạng thái là dự báo.

## 8. Đã chốt (người dùng, 22/10/2026)

| Câu hỏi | Chốt |
|---|---|
| Nén là cờ đi kèm hay trạng thái thứ 5? | **Cờ đi kèm** (4 trạng thái + cờ nén) |
| Trend theo cấu trúc + bằng chứng, giữ tới CHoCH? | **Có** |
| Giao diện làm đủ (bảng, Live / Review, mức gọn, nón, hộp range)? | **Làm đủ**, sau lõi |
| Nhãn tay ~150 cửa sổ? | **Có**, người dùng gán sau khi lõi v2 xong |

## 9. Tái lập

- Chẩn đoán v1 và thử v2 (dev 2021–2023): script tạm `chan_doan.py`, `proto_v2.py` → chuyển vào `research/` ở bước 1.
- Ghi chú khảo sát nguồn tham khảo: lưu kèm bước 1. Một agent khảo sát đã tự đo tỷ lệ chỉ báo trên cả 2018–2025 (có
  đoạn test, chỉ đọc, chỉ tỷ lệ mô tả) — các số đó **không** dùng; mọi ngưỡng v2 chốt lại trên dev.
