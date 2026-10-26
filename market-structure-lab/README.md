# Market Structure Lab

Web app chạy **local** để nhóm nghiên cứu và thử nghiệm thuật toán nhận diện
cấu trúc thị trường trên dữ liệu OHLC (ưu tiên XAUUSD H1/M15/M5).

> **Đây là công cụ nghiên cứu cấu trúc giá, chưa phải hệ thống giao dịch.**
> Không kết nối broker, không gửi lệnh, không backtest, không tính P&L.
> Không có LLM trong vòng này.
>
> Công cụ **không** tự báo cáo accuracy, win rate hay P&L. Precision/recall
> chỉ hiện khi có **bộ nhãn do người gán** (tab Nhãn tham chiếu), kèm tên
> người gán. Không có simulator giao dịch.

Người dùng có thể: nạp CSV OHLC → chọn thuật toán và tham số → chạy thử → xem
chart nến với cấu trúc được phát hiện → **replay từng nến** để kiểm tra thời
điểm tín hiệu thực sự khả dụng → lưu, mở lại và so sánh các lần chạy → **đánh
giá thuật toán** (F1, P90, khoảng giá/ATR, TP/FP/FN trên chart) → xuất CSV
và ảnh chart.

---

## 1. Cài đặt và chạy trên Windows / PowerShell

Yêu cầu: **Python 3.10 trở lên** (đã kiểm tra trên 3.11) và một trình duyệt.
Không cần Node.js, không cần internet sau khi cài xong.

```powershell
cd D:\Finance_System\market-structure-lab
.\run.ps1
```

Lần chạy đầu, script tự tạo `.venv`, cài dependency, khởi động server rồi mở
trình duyệt tại <http://127.0.0.1:8099/>. Nhấn `Ctrl+C` để dừng.

**Chỉ cần một tiến trình** — backend FastAPI phục vụ luôn giao diện tĩnh.

Nếu PowerShell chặn script:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Các lệnh khác

```powershell
.\run.ps1 -Setup        # chỉ cài môi trường
.\run.ps1 -Test         # chạy bộ test
.\run.ps1 -Port 8100    # đổi cổng
.\run.ps1 -NoBrowser    # không tự mở trình duyệt
```

### Tái lập môi trường chính xác

`requirements.txt` khai báo dependency tối thiểu (ràng buộc lỏng).
`requirements-lock.txt` ghim **đúng phiên bản đã kiểm chứng** — dùng file này khi
cần dựng lại môi trường giống hệt để đối chiếu kết quả giữa các máy:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

### Chạy thủ công (nếu không dùng script)

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = $PWD
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8099
```

### Bắt đầu nhanh

1. Mở app → bấm **Tạo dữ liệu mẫu** (sinh 4 dataset **MÔ PHỎNG**: XAUUSD H1/M15/M5, EURUSD H1).
2. Chọn dataset ở cột trái, để nguyên tham số mặc định (pivot 3/3).
3. Bấm **Chạy thử** → chart hiện swing, nhãn HH/HL/LH/LL và BOS.
4. Chuyển tab **Replay từng nến** để xem thuật toán "biết" điều gì tại từng thời điểm.

---

## 2. Định dạng CSV

### Tự nhận diện được

| Kiểu | Ví dụ dòng | Ghi chú |
|---|---|---|
| CSV chuẩn | `time,open,high,low,close,volume`<br>`2024-01-02 00:00:00,2000,2005,1998,2003,120` | Dấu phẩy, có tiêu đề |
| MT5 export bars | `<DATE>⇥<TIME>⇥<OPEN>⇥<HIGH>⇥<LOW>⇥<CLOSE>⇥<TICKVOL>⇥<VOL>⇥<SPREAD>` | TAB, ngày `2024.01.02`, ngày/giờ hai cột |
| MT4-style không tiêu đề | `2024.01.02,00:00,2000,2005,1998,2003,120` | Đoán theo vị trí cột |

Delimiter nhận diện được: `,` `;` TAB `|`. Encoding: UTF-8 (có/không BOM),
cp1252, latin-1. Thời gian nhận `YYYY-MM-DD HH:MM[:SS]`, `YYYY.MM.DD`,
`DD/MM/YYYY`, ISO 8601 và epoch giây/mili giây.

### Nếu không nhận diện được cột

Hộp thoại **Nhập CSV…** hiện bảng xem trước và cho phép **ánh xạ thủ công**
từng cột (time / date+time tách riêng / open / high / low / close / volume).

### Hai khai báo bắt buộc — công cụ KHÔNG tự đoán

| Khai báo | Vì sao bắt buộc |
|---|---|
| **Múi giờ nguồn** (`UTC`, `UTC+2`, `UTC-05:00`) | Sai múi giờ làm lệch toàn bộ phân tích theo phiên. Chỉ nhận **offset cố định**; múi giờ có giờ mùa hè (`Europe/London`) bị từ chối — hãy quy đổi trước hoặc khai báo offset đúng với dữ liệu. |
| **Timestamp là mốc MỞ hay ĐÓNG nến** | Quyết định `confirmed_at` lệch đi đúng một nến. |

Ngoài ra nên khai báo nguồn/broker và loại giá (bid/ask/midpoint/last) — cả hai
được lưu cùng dataset để sau này so sánh giữa các feed.

### Kiểm tra dữ liệu khi nhập

| Kiểm tra | Xử lý |
|---|---|
| Sai thứ tự thời gian | Sắp xếp lại, ghi số lần vào báo cáo |
| Trùng timestamp | Giữ bản ghi **đầu tiên**, cách ly các bản sau |
| `low ≤ open/close ≤ high` sai, giá trị thiếu | **Cách ly**, không đưa vào thuật toán, báo lỗi |
| Giá ≤ 0 | Cách ly, báo lỗi |
| Nến thiếu | Đếm và liệt kê. **Không nội suy, không lấp bằng dữ liệu tương lai.** Mỗi vị trí nến thiếu được xếp riêng là "cuối tuần/nghỉ" hay "thiếu trong phiên" |
| Nội dung trùng dataset đã có | Từ chối nhập (so bằng checksum SHA-256 của nến đã chuẩn hoá) |

File CSV gốc được sao lưu nguyên vẹn vào `data/raw/`. Báo cáo kiểm tra hiện
trong mục **Báo cáo kiểm tra dữ liệu** ở cột trái.

> **Heuristic cuối tuần** (21:00 thứ Sáu UTC → 22:00 Chủ nhật UTC) là quy ước
> chung cho forex/vàng, **không phải lịch phiên chính thức của broker**. Hãy
> đối chiếu lịch phiên thật trước khi kết luận dataset bị thiếu dữ liệu.

---

## 3. Thuật toán

Bản này có sáu thuật toán đăng ký trong `core/registry.py` (giao diện tự sinh form). Giới thiệu tổng quan — mỗi
thuật toán trả lời câu hỏi gì, chỉnh tham số nào, đã đo được gì, cách mở rộng sang thí nghiệm quant:
[`docs/guides/gioi_thieu_thuat_toan.md`](docs/guides/gioi_thieu_thuat_toan.md).

Hướng tiếp theo (bản nháp chờ duyệt): bộ nhận diện trạng thái thị trường cho ra trạng thái, khoảng giá có khả năng đi,
mức sẽ chạm và thời gian còn giữ, chấm bằng kết cục thật —
[`docs/plans/plan_nhan_dien_trang_thai.md`](docs/plans/plan_nhan_dien_trang_thai.md).

* **Swing Pivot + BOS/CHoCH** (`swing_pivot` **v1.1.0**) —
  [`docs/algorithms/thuat_toan_swing_pivot.md`](docs/algorithms/thuat_toan_swing_pivot.md).
  Pivot left/right tuyệt đối, HH/HL/LH/LL/EQH/EQL, phá vỡ theo close, phân loại
  **BOS chính / BOS nội bộ / CHoCH** khi đã có bias HH+HL hoặc LH+LL.
  Tắt `enable_choch` để mọi phá vỡ mang nhãn `BOS_UP`/`BOS_DOWN` như v1.0.0.
  HH/LH **so từng đỉnh cấp 1**.
* **Swing phân cấp** (`swing_hierarchy` **v1.0.0**) —
  [`docs/algorithms/thuat_toan_swing_cap_2.md`](docs/algorithms/thuat_toan_swing_cap_2.md).
  Cùng fractal cấp 1, rồi lọc đỉnh/đáy cấp 2 trên *chuỗi pivot* (ba đỉnh cấp 1
  liên tiếp, đỉnh giữa cao hơn hai cạnh). HH/LH **chỉ so hai đỉnh cấp 2**.
  Xác nhận cấp 2 lúc pivot cấp 1 bên phải đóng — không gắn tín hiệu về lúc đỉnh
  giữa hình thành. **Không** gồm BOS. Đây là thí nghiệm lọc cấu trúc, chưa phải ICT.
* **Baseline chỉ báo** (`indicator_baseline` v1.0.0) — đối chứng SMA/ATR Wilder,
  ADX Wilder, Donchian/ATR. [`docs/algorithms/thuat_toan_indicator_baseline.md`](docs/algorithms/thuat_toan_indicator_baseline.md).
  Không dùng TA-Lib. Ngưỡng mặc định không phải tối ưu XAUUSD.
* **HMM lọc online** (`hmm_online` v1.0.0) — fit `hmmlearn` trên prefix
  `train_bars`, `on_bar` chỉ bước forward. State mặc định `chua_gan_nghia`
  (không tự gắn Trend/Range). [`docs/algorithms/thuat_toan_hmm_online.md`](docs/algorithms/thuat_toan_hmm_online.md).
* **C2 Sweep + CISD** (`c2_cisd_research`) — **đã gỡ khỏi lab ngày 21/10/2026.** Code còn trong lịch sử git;
  các lần chạy cũ vẫn nằm trong DB (mở xem được) nhưng không chạy lại hay replay được.
* **DC theo close + ATR** (`dc_atr_structure` **v0.2.0**) — Directional Change trên giá đóng cửa, ngưỡng
  k×ATR hoặc %, xác nhận khi close đảo chiều ≥ Δ; Trend/Range theo swing DC đã xác nhận; gap reset segment
  (hoặc nối gap ngắn). [`docs/algorithms/thuat_toan_dc_atr_structure.md`](docs/algorithms/thuat_toan_dc_atr_structure.md).
* **Cấu trúc ICT phân tầng + khung lớn + order flow** (`ict_structure` **v0.10.0** — đổi hướng = MSS, OB là PD array) — STH/STL (pivot 1/1) → ITH/ITL
  (cấp 2) → thứ tự đỉnh/đáy, mức được bảo vệ (cờ «close đã vượt», không phải BOS), dealing range
  premium/discount; vùng thanh khoản từ ITH/ITL với vòng đời chạm → lấy → sweep / run / chưa rõ;
  **shift** = sweep rồi displacement ngược chiều (+ `SHIFT_FVG`, chung `group_id`); FVG, displacement,
  killzone giờ New York; khoảng trống phân loại theo lịch phiên khai báo. **Không có BOS/CHoCH.**
  **Order flow theo thanh khoản** (v0.3.0): tăng / giảm / chưa rõ sau mỗi nến, đọc từ run + shift; run
  phía ngược → chưa rõ. Đây là **mô tả, không phải dự báo**
  ([`docs/research/nghien_cuu_orderflow_ict.md`](docs/research/nghien_cuu_orderflow_ict.md)). **Order block và OTE**
  (v0.5.0): OB = chuỗi nến ngược màu cuối trước displacement của shift (chỉ thân), có hiệu lực khi giá vượt đầu xa;
  OTE = vùng hồi 62–79% của nhịp sau shift; vòng đời chạm / hỏng / hết hạn; hai lớp bật/tắt trên chart — mô tả, chưa
  phải tín hiệu ([`docs/plans/plan_ket_hop_ict_indicator.md`](docs/plans/plan_ket_hop_ict_indicator.md) §3.4). **Lớp nhận
  diện** (v0.6.0): khoảng giá 80% / 50% cho 1h, 4h và xác suất chạm vùng gần nhất, tự chấm độ phủ / Brier so với B0 trong
  lần chạy; trạng thái trend / range biên rõ / sideway nén / nhiễu (mô tả) — lớp «Trạng thái» trên chart
  ([`docs/algorithms/thuat_toan_nhan_dien.md`](docs/algorithms/thuat_toan_nhan_dien.md)). Chart vẽ theo
  cách các indicator ICT/SMC làm, **không chú giải màu** — chữ ngay trên đối tượng + dòng trạng thái 2 hàng, rê
  chuột để xem giải thích: chế độ **Gọn** (mặc định: vùng BSL/SSL vẽ từ đỉnh/đáy ITH/ITL gốc với sweep / run /
  đang chờ, «Shift ↓/↑» + FVG, dải order flow có chữ ở đáy, khoảng trống bất thường), **Chi tiết** (ITH/ITL,
  Protected, Premium / EQ / Discount, hộp FVG, displacement…); chế độ **Lịch sử** tạm bỏ khỏi giao diện
  (08/10/2026) — [`docs/plans/plan_hien_thi_ict.md`](docs/plans/plan_hien_thi_ict.md), nguồn
  [`docs/research/nghien_cuu_hien_thi_indicator.md`](docs/research/nghien_cuu_hien_thi_indicator.md). Có mục
  tiêu chấm `ict_shift`, loại nhãn tay shift, khung «Thuật toán đang làm gì» khi replay. **Khung lớn**
  (v0.4.0, giai đoạn 3 lõi): H1/H4 gộp tuần tự trong chính run, mốc 17:00 New York (`ny_1700`) theo lịch phiên, chỉ
  dùng nến đã chốt (`period_end` ≠ `known_at`, `coverage`, nến thiếu dữ liệu không vào cấu trúc) → ITH/ITL, thứ tự,
  dealing range, FVG khung lớn; PDH/PDL, PWH/PWL; vùng H1/H4/D/W cùng vòng đời thanh khoản; phản ứng ở FVG khung lớn
  (`pd_bias`), DOL sau shift; sự kiện cấu trúc mang `details.htf` (ngữ cảnh đã chốt trước nến đó; từ 0.4.1 bỏ ở sự
  kiện «nguyên liệu»). Là **đặc trưng**, không lọc sự kiện. Chart có nhóm lớp **Khung lớn** (ITH/ITL H4, range H4,
  FVG H4, PDH/PDL, nến H4 đang hình thành).
  [`docs/algorithms/thuat_toan_ict_structure.md`](docs/algorithms/thuat_toan_ict_structure.md).

Tóm tắt swing_pivot:

* **Pivot.** `high[c]` lớn hơn **tuyệt đối** mọi high trong cửa sổ `left`/`right`
  (mặc định 3/3); swing low đối xứng. **Bằng nhau không nhận pivot** ở phiên bản này.
* **Xác nhận.** Pivot chỉ được xác nhận khi nến bên phải **cuối cùng** đã đóng,
  tức trễ đúng `right` nến. Đỉnh ở nến 100 với `right=3` có `event_time` tại nến
  100 nhưng `confirmed_at` tại nến 103.
* **Nhãn.** So hai swing cùng phía đã xác nhận liên tiếp → `HH`/`LH` hoặc `HL`/`LL`.
  Giá bằng nhau nhận nhãn riêng **`EQH`/`EQL`**, không ép thành HH/HL/LH/LL.
* **BOS / CHoCH.** `close` vượt mức swing active. Khi `bias=none` → `BOS_UP`/`BOS_DOWN`
  như v1.0.0. Khi đã có HH+HL: phá HL là `CHOCH_DOWN`, phá đỉnh hồi là
  `BOS_INTERNAL_UP`, phá HH là `BOS_UP` (chính). Cùng nến xuyên nội bộ lẫn chính
  chỉ phát sự kiện mức chính. Dùng close, **không** dùng wick. Mỗi mức một lần.
* **Thứ tự trong cùng một nến:** xác nhận pivot → gắn nhãn → đăng ký mức → kiểm
  tra BOS. Tài liệu chứng minh thứ tự này không làm thay đổi kết quả.
* Chỉ xử lý **nến đã đóng**.

### Mỗi sự kiện gồm

`event_id`, `structure_type`, `price`, `event_bar_index`, `event_time`,
`event_close_time`, `confirmed_bar_index`, `confirmed_at`,
`confirmation_lag_bars`, `algorithm`, `algorithm_version`, `reason_code`,
`direction`, `reference_event_id`, `details`.

Ba mốc thời gian được phân biệt rõ:

| Mốc | Ý nghĩa |
|---|---|
| `event_time` | Timestamp của **nến** chứa cấu trúc |
| `event_close_time` | Thời điểm nến đó **đóng** |
| `confirmed_at` | Thời điểm thuật toán **thực sự xác nhận được** cấu trúc |

### Thêm thuật toán mới

Xem [`docs/guides/them_thuat_toan.md`](docs/guides/them_thuat_toan.md).

**MT5 / tổng hợp nến.** [`docs/guides/mt5_va_tong_hop_nen.md`](docs/guides/mt5_va_tong_hop_nen.md).
Gói `MetaTrader5` tuỳ chọn; `core/` vẫn import được khi chưa cài. Nến đang
hình thành (index 0) bị loại. Tổng hợp M1→M5/M15/M30/H1/H4 theo mốc `utc_epoch`,
không lấp gap bằng tương lai.

**Nhãn tham chiếu.** Trang [`/gan-nhan`](http://127.0.0.1:8099/gan-nhan)
— chọn dataset/khung, click nến, ghi tên người gán, lưu bộ. Không cần chạy
thuật toán trước. Tab *Nhãn tham chiếu* trên Thử nghiệm là bản rút gọn với cùng
các nút.

**Auto label (hybrid: đề xuất + người duyệt).** Trên `/gan-nhan`, chọn
`swing_pivot` hoặc `swing_hierarchy`, chọn khoảng **ngày giờ UTC** (nhập tay, *Vùng đang xem*
hoặc *Toàn bộ*), bấm **Đề xuất nhãn**. Đề xuất hiện thành chấm xám trên chart;
duyệt từng cái bằng <kbd>A</kbd> chấp nhận / <kbd>X</kbd> bỏ / <kbd>N</kbd> kế
tiếp, hoặc chấp nhận/bỏ hàng loạt. Sau đó sửa nhãn ngay trong bảng nháp (đổi
loại, dời nến ◀ ▶ hoặc <kbd>[</kbd> <kbd>]</kbd>, sửa giá, xoá); **hoàn tác**
(<kbd>Ctrl+Z</kbd>) lùi được mọi thao tác kể cả chấp nhận/bỏ, và vẫn còn sau khi
tải lại trang. Đề xuất **không bao giờ tự vào kho nhãn**.
Mỗi nhãn ghi nguồn gốc (người gán hay auto từ thuật toán nào, tham số gì); trang
Đánh giá **cảnh báo** khi chấm một thuật toán trên nhãn do chính nó đề xuất, vì
F1 khi đó bị thổi phồng.

Giữ công sức gán nhãn:

* **Nháp tự lưu trong trình duyệt theo từng dataset.** Tải lại trang, đóng tab
  hay chuyển qua lại giữa hai trang đều không mất nhãn đang soạn; mở lại app sẽ
  quay về dataset đang làm dở. Nháp của XAUUSD H1 không bao giờ hiện trên
  EURUSD hay M15 — `bar_index` chỉ có nghĩa trong đúng dataset của nó.
* **Cảnh báo khi rời trang** lúc còn nhãn chưa lưu.
* **Lưu thành bộ mới** tạo `lab_…` mới; **Cập nhật bộ đang mở** ghi đè và tăng
  `revision`. Nếu bộ nhãn đã được dùng trong đánh giá đã lưu thì phải xác nhận,
  vì kết quả cũ gắn với bản nhãn trước đó và không tự tính lại.
* **Xuất / nhập CSV** để sao lưu và chia sẻ. File nhập vào chỉ đi vào bộ nháp —
  vẫn phải bấm Lưu, nên chỉ có một đường ghi vào kho nhãn.

Dòng trạng thái đầu tab luôn nói rõ nhãn đã vào kho (`data/lab.sqlite`) hay mới
chỉ nằm trong nháp của trình duyệt.
[`docs/guides/nhan_tham_chieu.md`](docs/guides/nhan_tham_chieu.md).

**Đánh giá thuật toán.** Trang riêng [`/danh-gia`](http://127.0.0.1:8099/danh-gia)
— protocol có phiên bản, khoảng gán nhãn đầy đủ, F1, P90, ATR, so nhiều run,
nhảy từ TP/FP/FN tới nến. Không nhét metric vào tab thống kê dưới chart.
[`docs/guides/danh_gia_thuat_toan.md`](docs/guides/danh_gia_thuat_toan.md).

**Python ↔ MQL5.** Script [`mql5/SwingPivotExport.mq5`](mql5/SwingPivotExport.mq5),
tab *Đối chiếu MQL5*. Cần cùng `dataset_checksum`.
[`docs/guides/doi_chieu_python_mql5.md`](docs/guides/doi_chieu_python_mql5.md).

---

## 4. Replay

Chuyển sang tab **Replay từng nến** để chạy lại theo thời gian.

* Điều khiển: về đầu ⏮, lùi ◀, tiến ▶|, phát/tạm dừng ▶, chọn tốc độ
  (1–25 nến/giây), thanh trượt nhảy tới vị trí bất kỳ.
* Phím tắt: `→` tiến, `←` lùi, `Space` phát/tạm dừng.

**Thuật toán thực sự chỉ nhận prefix dữ liệu**, không phải chỉ che tương lai
trên chart. Server giữ một `ReplaySession` nạp từng nến vào `on_bar`; chart cũng
chỉ vẽ tới nến hiện tại.

* **Khi lùi**, trạng thái thuật toán được **reset và dựng lại từ nến đầu tiên**
  tới vị trí mới — không "hoàn tác" thủ công, nên không có nguy cơ sót trạng thái.
* **Sự kiện đã xác nhận không bị sửa** bởi dữ liệu nạp thêm sau đó.
* **Marker pivot vẫn nằm tại nến chứa cấu trúc**, nhưng chỉ **xuất hiện** sau khi
  nến xác nhận đã đóng.
* Panel **Thống kê** trong chế độ replay hiển thị trạng thái nội bộ tại nến hiện
  tại: mức swing đang hoạt động, số mức đã bị phá, các nến chưa đủ cửa sổ phải.

**Chế độ Toàn lịch sử** có một dòng nhắc thường trực: marker nằm tại `event_time`,
**không phải** thời điểm hệ thống đã biết sự kiện. Có tuỳ chọn *"Đặt marker tại
nến XÁC NHẬN"* để xem cách trình bày còn lại.

---

## 5. Lưu, mở lại, so sánh, xuất

Mỗi lần chạy lưu vào SQLite (`data/lab.sqlite`) với: `run_id`, nhãn,
`dataset_id` + **checksum dataset**, symbol, timeframe, thuật toán +
`algorithm_version`, toàn bộ tham số, khoảng thời gian, số nến, warm-up, thời
gian tính toán, thống kê và toàn bộ bảng sự kiện. Lịch sử vẫn mở lại được sau
khi khởi động lại app.

* **Mở lại** một lần chạy cũ đồng thời là **kiểm tra tái lập**: app chạy lại đúng
  cấu hình đó và báo rõ kết quả có khớp bản đã lưu hay không.
* **So sánh** hai lần chạy: số sự kiện theo loại, độ trễ xác nhận (min/TB/trung
  vị/max), thời gian tính toán, số sự kiện chung và số chỉ có ở một bên.
  Nếu hai lần chạy khác dataset, khác khoảng thời gian hoặc khác phiên bản thuật
  toán, app **cảnh báo rõ** để không quy kết sai nguyên nhân khác biệt.
* **Xuất CSV sự kiện** — đầy đủ các trường, kể cả `confirmed_at` và độ trễ.
* **Xuất ảnh chart** — PNG của khung nhìn hiện tại.
* **Ghi chú (n)** — hiện / ẩn các ghi chú phía trên chart (dòng chế độ, kết quả lần chạy, ghi chú của thuật
  toán). Ẩn sẵn để chart chiếm chỗ; trình duyệt nhớ lựa chọn. Viền vàng = trong số ghi chú đang ẩn có cảnh báo
  (vd khoảng trống bất thường). Lỗi và cảnh báo của thao tác (chạy hỏng, mở lại không khớp…) luôn hiện.
* `GET /api/runs/{run_id}/manifest` trả hồ sơ JSON đủ để tái lập.

---

## 5b. Dữ liệu thị trường thật (XAUUSD, EURUSD 2018–2025)

**Nguồn:**
- Dữ liệu do repo riêng **`market-data-pipeline`** sinh (repo chung của team:
  `https://github.com/pl1201/Finance_System`; bản làm việc đặt cạnh lab ở `..\market-data-pipeline`).
- Gốc là HistData M1 (BID), đã sửa giờ, kiểm bằng Dukascopy, broker FXCM và COMEX. Giờ lưu UTC, mốc
  mở nến.

**Đã nạp sẵn vào lab:**
- M1 theo năm, M5 (hai phần), M15, H1, H4, D1 cho cả hai cặp; H4/D1 cắt theo ngày giao dịch 17:00 New
  York.
- Mã từng dataset: [`docs/guides/du_lieu_thi_truong.md`](docs/guides/du_lieu_thi_truong.md).

**Nạp thêm hoặc nạp lại sau khi pipeline dựng dữ liệu mới:**

```powershell
.\.venv\Scripts\python.exe scripts\import_market_data.py --dry-run series --pair XAUUSD --tf M15   # thử trên bản sao DB
.\.venv\Scripts\python.exe scripts\import_market_data.py series --pair XAUUSD --tf M15,H1         # nạp thật (tự sao lưu DB)
.\.venv\Scripts\python.exe scripts\import_market_data.py m1-year --pair EURUSD --year 2024 --resample ""
```

**Lưu ý:**
- Bộ XAUUSD 2024 cũ (tên bắt đầu bằng `[LỆCH GIỜ …]`) chỉ giữ để mở các run cũ; không dùng cho phân
  tích mới.
- Mọi thuật toán chạy được trên mọi dataset mới.
- Dataset dài thì giao diện mặc định chỉ lấy khoảng 50 000 nến gần nhất (xem mục Giới hạn).

---

## 6. Dữ liệu mô phỏng đi kèm

Nút **Tạo dữ liệu mẫu** sinh 4 dataset để mở app là thử được ngay:
XAUUSD H1 (1800 nến), XAUUSD M15 (2400), XAUUSD M5 (2400), EURUSD H1 (1800).

> **DỮ LIỆU MÔ PHỎNG — KHÔNG PHẢI DỮ LIỆU THỊ TRƯỜNG THẬT.**
> Mọi dataset sinh ra đều gắn nhãn `[MÔ PHỎNG]` trong danh sách, có huy hiệu
> **DỮ LIỆU MÔ PHỎNG** ở thông tin dataset và **watermark trên chart**.
> Chúng chỉ dùng để kiểm tra pipeline, giao diện và hành vi thuật toán; không
> nhằm tái tạo tính chất thống kê của thị trường thật, và **không được dùng để
> đánh giá chất lượng thuật toán**.

Bộ sinh dựng chuỗi các giai đoạn (trend tăng, tích lũy biên độ thấp/cao,
breakout lên/xuống, trend suy yếu, phá vỡ thất bại) để có đủ tình huống quan sát,
và bỏ qua cuối tuần theo cùng heuristic với phần kiểm tra dữ liệu.

**Tái tạo bằng lệnh** (tất định theo seed):

```powershell
$env:PYTHONPATH = $PWD
.\.venv\Scripts\python.exe scripts\generate_synthetic.py
# hoặc một bộ cụ thể:
.\.venv\Scripts\python.exe scripts\generate_synthetic.py --symbol XAUUSD --timeframe H1 --bars 1800 --seed 20260920
```

File CSV ghi vào `data/samples/`. Bản đi kèm repo đã sinh sẵn ở đó.

---

## 7. Cấu trúc dự án

```
market-structure-lab/
├─ core/                      lõi độc lập giao diện (chỉ thư viện chuẩn Python)
│  ├─ types.py                Bar, StructureEvent; ghép StructureType / ReasonCode từ vocab/
│  ├─ vocab/                  loại sự kiện + mã lý do + câu giải thích theo họ (swing, baseline, dc, ict)
│  ├─ engine.py               chạy tuần tự, ReplaySession, thống kê
│  ├─ registry.py             đăng ký thuật toán
│  ├─ algorithms/             mỗi thuật toán một gói: __init__.py + algorithm.py (+ phần riêng)
│  │  ├─ base.py              interface StructureAlgorithm + ParamSpec + hook tuỳ chọn
│  │  ├─ swing_pivot/         v1.1.0 pivot + BOS/CHoCH (baseline)
│  │  ├─ swing_hierarchy/     v1.0.0 swing cấp 2
│  │  ├─ indicator_baseline/  đối chứng SMA/ATR/ADX
│  │  ├─ hmm_online/          HMM forward (hmmlearn lúc fit)
│  │  ├─ dc_atr_structure/    v0.2.0 DC close + regime: algorithm, detector, regime, metrics
│  │  └─ ict_structure/       v0.10.0 cấu trúc ICT phân tầng (giai đoạn 3: khung lớn, PD array, DOL; order block, OTE; lớp nhận diện): algorithm, eval_targets; ghép core/components
│  ├─ components/             thành phần dùng chung: session_gap, swing_source, hierarchy, structure_order, dealing_range,
│  │                          displacement, fvg, liquidity, shift, killzone, order_flow
│  ├─ indicators.py           ATR/ADX Wilder, SMA, Donchian
│  ├─ labels.py               loại nhãn (dựng sẵn + thuật toán khai), ghép nhãn greedy (tab Nhãn tham chiếu)
│  ├─ eval/                   protocol, targets (mục tiêu chấm), matcher min-cost, F1/P90/ATR
│  ├─ mql5_compare.py         đối chiếu CSV MT5
│  └─ data/
│     ├─ loader.py            nạp CSV, dò cột, ánh xạ, múi giờ
│     ├─ validate.py          kiểm tra chất lượng
│     ├─ synthetic.py         bộ sinh dữ liệu mô phỏng
│     ├─ resample.py          tổng hợp nến utc_epoch (+ ny_1700, số nến kỳ vọng theo lịch)
│     ├─ htf_stream.py        gộp nến khung lớn TUẦN TỰ: utc_epoch (bộ gộp chung, hiện chưa thuật toán nào dùng), ny_1700 + lịch phiên (ict_structure)
│     └─ mt5_source.py        MetaTrader5 tuỳ chọn (loại nến đang chạy)
├─ mql5/SwingPivotExport.mq5
├─ backend/app/
│  ├─ main.py                 dựng app, middleware, lỗi → HTTP, gắn router
│  ├─ errors.py               ServiceError (400), NotFoundError (404)
│  ├─ routers/                route HTTP theo mảng: datasets, runs, labels, evaluations, mql5, replay, pages
│  ├─ schemas/                model Pydantic của thân request
│  ├─ services/               nghiệp vụ theo mảng (common, datasets, runs, replay, labels, auto_label, evaluations, mql5)
│  ├─ storage/                SQLite: db.py ghép các *_repo.py, schema.py (lược đồ + migration)
│  └─ config.py               đường dẫn, giới hạn
├─ frontend/                  HTML/CSS/JS tĩnh, không cần build (script thường, namespace window.MSL)
│  ├─ index.html              thử nghiệm
│  ├─ gan-nhan.html           gán nhãn tham chiếu
│  ├─ danh-gia.html           đánh giá thuật toán
│  ├─ js/lib/                 dùng chung: dom, format, timeframe, api, labeldraft
│  ├─ js/chart/               market-chart (nến, khung nhìn, marker, tooltip), series, overlays, primitives (lớp vẽ chung)
│  ├─ js/algos/               plugin hiển thị theo thuật toán: registry, swing, baseline, dc_atr, ict_structure
│  │                          (+ ict_structure_view: dựng hình thuần, kiểm bằng node)
│  ├─ js/pages/lab/           trang Thử nghiệm: state, algorithm, dataset, run, replay, explain, stats, history…
│  ├─ js/pages/label/         trang Gán nhãn: state, dataset, draft, store, auto, range, popover, main
│  ├─ js/pages/eval/          trang Đánh giá: state, protocol, dataset, results, plots, detail, saved, main
│  └─ vendor/                 TradingView Lightweight Charts (Apache-2.0)
├─ data/                      lab.sqlite, raw/, samples/, exports/  (không commit)
├─ docs/
│  ├─ algorithms/             đặc tả từng thuật toán (thuat_toan_<tên>.md)
│  ├─ plans/                  kế hoạch tích hợp / thiết kế
│  ├─ research/               nghiên cứu nguồn + khao_sat/ (số liệu khảo sát tái lập)
│  ├─ guides/                 hướng dẫn: giới thiệu thuật toán, thêm thuật toán, dữ liệu, nhãn, đánh giá, MT5/MQL5, kiến trúc
│  └─ hoc_quant/              tài liệu học quant qua chính dự án: 8 module, bài tập chạy trên dữ liệu lab (chỉ đọc)
├─ scripts/                   import_market_data, generate_synthetic, regression_saved_runs
├─ research/                  thí nghiệm / khảo sát tái lập: dc_experiment, ict_survey, orderflow_survey, orderflow_rules;
│                             hoc_quant/hoc.py: nạp nến / chạy thuật toán chỉ đọc cho bài tập của docs/hoc_quant
├─ tests/                     pytest: core/ · algorithms/ · api/ · frontend/ (helpers.py, conftest.py ở gốc)
├─ requirements.txt / requirements-lock.txt
├─ run.ps1
└─ README.md
```

### Lựa chọn kỹ thuật

| Quyết định | Lý do |
|---|---|
| **FastAPI + uvicorn**, một tiến trình phục vụ cả API và giao diện | Không cần dựng hai tiến trình hay reverse proxy khi chạy local |
| **SQLite** | Không cần cài server; lịch sử thí nghiệm là một file, dễ sao lưu và chia sẻ |
| **Không dùng pandas trong lõi; numpy chỉ trong `hmm_online` lúc fit** | Pivot/BOS/baseline/resample dùng thư viện chuẩn |
| **Frontend thuần HTML/JS, không bundler** | Không cần Node.js, không có bước build; sửa file là thấy ngay |
| **[TradingView Lightweight Charts](https://github.com/tradingview/lightweight-charts) v4.2.3** | Giấy phép **Apache-2.0** (bản sao ở `frontend/vendor/lightweight-charts.LICENSE.txt`), ~160 KB, có nến, zoom/pan, marker và crosshair sẵn; nhúng offline được. Bản quyền và tên TradingView được ghi nhận ở chân trang theo yêu cầu của license. |

---

## 8. Kiểm thử

```powershell
.\run.ps1 -Test
# hoặc
$env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest -q
```

Test dùng thư mục dữ liệu tạm nên **không đụng vào `data/`** của bạn.

| File | Nội dung |
|---|---|
| `tests/algorithms/test_swing_pivot.py` | Pivot trên chuỗi nhỏ tính tay; nến bằng giá; dung sai EQH; warm-up; độ trễ xác nhận; BOS close/wick/chống phát lặp |
| `tests/algorithms/test_choch_bos.py` | CHoCH, BOS nội bộ, BOS chính tính tay; cùng nến xuyên hai mức; `enable_choch=false`; nhân quả |
| `tests/algorithms/test_indicator_baseline.py` | ATR Wilder tính tay; warm-up ADX; chuỗi tăng ra BASELINE_UP; nhân quả |
| `tests/core/test_resample_mt5.py` | M1→M5 tính tay; drop_incomplete; không lấp gap; MT5 mock loại nến đang hình thành |
| `tests/core/test_labels.py` / `test_mql5_compare.py` / `test_hmm_online.py` | Ghép nhãn precision/recall; checksum MQL5; HMM không phát trong prefix train |
| `tests/core/test_replay_causality.py` | Thêm **và sửa** dữ liệu sau `T` không đổi sự kiện đã xác nhận tại `T` |
| `tests/core/test_data.py` | CSV / MT5 TAB / chất lượng dữ liệu |
| `tests/api/test_api_flow.py` | Luồng API + resample + nhãn + evaluate |
| `tests/core/test_eval_protocol.py` | Matcher greedy vs min-cost tính tay; F1; P90; phạm vi nhãn không thành FP |
| `tests/api/test_eval_api.py` | Trang `/danh-gia`, lưu/mở evaluation, F1 trống khi chưa có nhãn, chấm M5/M15 tách nhóm khỏi H1 |
| `tests/api/test_eval_index_space.py` | Run chạy khoảng con được chấm theo chỉ số dataset như run cả dataset (lỗi lệch `range_start_index` cũ); tab đối chiếu nhãn; nến/replay trả `dataset_index` |
| `tests/api/test_eval_null_segments.py` | Chuẩn ngẫu nhiên + đoạn phát triển/kiểm tra qua API: đoạn kiểm tra khoá, mở thì có dấu trong ghi chú, lưu/mở lại giữ kết quả, báo cáo .md, lỗi 400, protocol mặc định không thêm khoá |
| `tests/core/test_eval_null.py` | Chuẩn ngẫu nhiên tính tay (1 nến, 10 nến, dung sai), F1 lượt = 0 không phải None, không suy được quy tắc giá, tất định theo seed và độc lập với run khác, ghép cặp đúng giờ New York (có đổi giờ), tách cụm cho đúng số TP như matcher gốc (300 ca) |
| `tests/algorithms/test_ict_structure.py` | `ict_structure` giai đoạn 1: STH/STL strict + outside bar, chặn cửa sổ vắt qua khoảng trống, ITH xác nhận khi STH phải xác nhận, cấp 3, thứ tự + mức được bảo vệ (ví dụ plan), dealing range chứa giá, khoảng trống theo lịch CME, tương đương `swing_pivot(1,1)`/`swing_hierarchy(1,1)`, nhân quả prefix/suffix |
| `tests/algorithms/test_ict_structure_g2.py` | `ict_structure` giai đoạn 2: displacement đúng/thiếu ngưỡng; FVG + vắt khoảng trống + chạm/lấp; thanh khoản chạm 0.05 rồi lấy 0.15 ATR, ATR khoá, W tính cả nến lấy, khoảng trống → chưa rõ, nhiều vùng một nến, gộp EQ, đã bị lấy trước khi biết; shift ở nến quét / r+3 / quá cửa sổ, huỷ khi vượt X hoặc khoảng trống, hai sweep → một shift; chuỗi dựng tay sweep → shift → `SHIFT_FVG` (group_id, ATR khoá tính độc lập); killzone đổi giờ mùa hè; bất biến + nhân quả trên dữ liệu ngẫu nhiên |
| `tests/algorithms/test_ict_order_flow.py` | `ict_structure` order flow (v0.3.0): bảng chuyển trạng thái của thành phần (chưa có / chưa rõ / tăng / giảm × run / shift / hai chiều cùng nến), «ủng hộ» xoá khi đổi, snapshot là bản sao, đầu vào sai bị từ chối; chuỗi dựng tay có shift và run ngược chiều → chưa rõ; dữ liệu ngẫu nhiên có khoảng trống: trạng thái từng nến khớp quy tắc A cài độc lập, `ORDER_FLOW_*` đúng lúc đổi, thống kê khớp số tính độc lập, nhân quả prefix = full, sửa đuôi không đổi quá khứ |
| `tests/algorithms/test_ict_htf.py` | `ict_structure` giai đoạn 3 lõi (v0.4.0): mốc `ny_1700` trước/sau đổi giờ, bộ gộp theo lịch CME (giờ nghỉ trong nến H4 đầu ngày, tuần, ngày đóng sớm không degraded, chốt muộn, kỳ đầu thiếu, hole, nến ngoài lịch), `utc_epoch`/`resample` cũ không đổi; ngăn xếp H4 tính tay (degraded / hole chặn cửa sổ, FVG cần liền kề); PD array, DOL tính tay; `details.htf` đúng khuôn, neo sự kiện khung lớn, không PDH/PWH ở kỳ đầu thiếu, midnight open thiếu → null, nhân quả (prefix, sửa nến sau t trong nến H4 đang hình thành), thứ tự ở nến chốt H4, tương đương với dataset H4 gộp `ny_1700` |
| `tests/api/test_ict_structure_api.py` | `ict_structure` qua API: lịch `auto` → lịch theo mã, lưu → mở lại → CSV/manifest, replay tiến/lùi, sai khung → 400, chấm ITH/ITL với mục tiêu Swing cấu trúc, chấm shift với mục tiêu `ict_shift` và đổi tầng sang `SHIFT_FVG`; order flow trong run (timeline, `pending_state`, thống kê) và khi replay; khung lớn 0.4.0 (sự kiện `HTF_*`/`PD_*`, `details.htf`, cột timeline, `pending_state.khung_lon`, replay khớp run, `htf_list` sai → 400) |
| `tests/core/test_eval_segments.py` | Hash/dict của protocol thật đã lưu không đổi; tuỳ chọn mới chỉ xuất hiện khi bật; luật hợp lệ của đoạn; một đoạn = khai khoảng chấm tay; đuôi chưa xác nhận theo từng đoạn; khoá đoạn kiểm tra; không tính FP giữa hai đoạn |
| `tests/frontend/test_label_page.py` | Trang `/gan-nhan`, nav 3 trang, nhãn M15 không hiện trên M5, bắt buộc tên người gán, đủ nút lưu/ghi đè/CSV, mọi `<script>` của trang trả 200, JS không lỗi cú pháp (`node --check`, quét cả thư mục con) |
| `tests/frontend/test_plugins.py` | Mọi plugin `js/algos/*.js` nạp ở cả ba trang, giữa `registry.js` và `chart/market-chart.js`; lõi chart / trang / lib không so tên thuật toán (trừ run baseline `swing_pivot` 3/3) |
| `tests/frontend/test_ict_display.py` | Hiển thị `ict_structure` (hàm thuần `ict_structure_view.js` chạy bằng node qua `ict_display_check.js`): kịch bản dựng tay — vòng đời vùng, lọc «Hiện tại», gộp vùng trùng, ưu tiên nhãn + ký hiệu thay chữ, dòng trạng thái, tooltip, Chi tiết, Lịch sử, nhân quả ở mọi con trỏ; dữ liệu lõi thật — vùng gần nhất khớp `liq_above` / `liq_below` mọi nến, replay prefix = lọc theo con trỏ, không đối tượng nào trước nến xác nhận (bỏ qua khi không có node) |
| `tests/api/test_auto_label.py` | Đề xuất chỉ trong khoảng nến và khớp đúng sự kiện thuật toán; lọc loại; từ chối thuật toán không sinh nhãn cấu trúc và khoảng sai; cảnh báo nến cuối; đề xuất không tự lưu; nguồn gốc nhãn giữ qua lưu/ghi đè/CSV; cảnh báo khi chấm chính thuật toán đã đề xuất (và không cảnh báo với thuật toán khác) |
| `tests/api/test_label_persistence.py` | Nhãn ngoài phạm vi nến bị từ chối; nhãn trùng bị gộp; ghi đè tăng `revision` và giữ nguyên dataset; chặn ghi đè khi bộ đã dùng trong đánh giá đã lưu; xuất CSV nạp lại khớp; `parse-csv` không tự lưu |

---

## 9. Giới hạn đã biết

**Phạm vi**

* Chưa đánh giá walk-forward / độ nhạy tham số (giai đoạn D của trang đánh giá).
* Chưa có tầng regime sản phẩm (Trend/Range/Breakout/Uncertain) — HMM state
  mặc định `chua_gan_nghia`; baseline chỉ báo là đối chứng, không phải router.
* Kết nối MT5 lấy lịch sử **đã có** nhưng là tuỳ chọn (cần terminal + gói
  `MetaTrader5`). Không thay Strategy Tester.

**Thuật toán**

* `swing_pivot` v1.1.0 có CHoCH và BOS nội bộ/chính. Giá bằng nhau không tạo pivot.
* HMM cần `hmmlearn`/`numpy`. Fit trên prefix rồi lọc tiếp **không** phải
  walk-forward đầy đủ. BOCD **chưa** triển khai.
* MQL5 export là script tham chiếu — phải biên dịch trong MetaEditor; lab không
  chạy MQL5 hộ.

**Dữ liệu**

* Chỉ nhận offset múi giờ cố định; **không** xử lý giờ mùa hè.
* Tổng hợp nến theo `utc_epoch` (H4 00/04/08/12/16/20 UTC), không đoán lệch broker.
  Không tách H4→M5; thanh **Khung** chuyển sang dataset cùng symbol nếu đã có.
* Không nội suy khoảng trống.
* Heuristic cuối tuần là quy ước chung, không phải lịch phiên broker.
* Giới hạn 500.000 nến mỗi dataset và 80 MB mỗi file tải lên.

**Giao diện và vận hành**

* Thiết kế cho **desktop**; chưa tối ưu cho màn hình hẹp.
* Không có authentication — chỉ nên chạy trên `127.0.0.1`.
* Phiên replay giữ trong bộ nhớ tiến trình.
* Bảng sự kiện hiển thị tối đa 3000 dòng.
* **Nháp gán nhãn nằm trong trình duyệt của từng máy** (`localStorage`): người
  khác không thấy, không đồng bộ giữa hai trình duyệt, và mất khi xoá site data
  hoặc dùng cửa sổ riêng tư. Muốn giữ chắc chắn thì bấm Lưu (vào
  `data/lab.sqlite`) hoặc xuất CSV. Nếu trình duyệt chặn `localStorage`, giao
  diện báo rõ và nhắc không tải lại trang trước khi lưu.
* Ghi đè bộ nhãn **không** tự tính lại các đánh giá đã lưu trước đó; chúng gắn
  với `label_set_revision` tại thời điểm chấm.
* Nhãn không chuyển được giữa các dataset/khung — kể cả cùng symbol.
* Auto label chỉ dùng thuật toán sinh loại nhãn cấu trúc (`swing_pivot`,
  `swing_hierarchy`). Chưa có đề xuất theo "đồng thuận nhiều thuật toán", chưa
  xếp ưu tiên đề xuất theo độ không chắc chắn, và chart chưa tô màu khoảng đang
  đề xuất.
* Nhãn chấp nhận từ đề xuất **không độc lập** với thuật toán đã đề xuất nó; công
  cụ cảnh báo chứ không chặn việc chấm.

**Đã kiểm chứng và chưa kiểm chứng**

* Đã chạy bộ pytest đầy đủ trên máy phát triển (kể cả test cũ).
* Luồng lưu nhãn đã kiểm tra trực tiếp trên Chrome headless qua CDP: gán nhãn →
  tải lại trang (nháp còn nguyên) → đổi dataset (không mang nhãn sang) → lưu →
  ghi đè lên bản 2 → xuất CSV và nạp lại khớp → trang `/gan-nhan` dùng chung
  nháp. Ba trang nạp không lỗi console.
* **Chưa** biên dịch/chạy `SwingPivotExport.mq5` trong MetaEditor trên máy này.
* **Chưa** lấy lịch sử live từ terminal MT5 trong phiên làm việc này (có test mock).
* **Chưa** kiểm tra Firefox/Safari.
* **Dataset dài** (tới 372 000 nến, đã thử bằng Chrome 02/10/2026):
  - Khoảng thời gian mặc định chỉ lấy khoảng **50 000 nến gần nhất**.
  - Chạy hoặc replay trên khoảng ước tính hơn 100 000 nến sẽ phải xác nhận, vì kết quả có thể hàng
    trăm MB.
  - Nút «Dùng toàn bộ khoảng dữ liệu» vẫn chọn đủ cả dataset.
