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

Bản này có năm thuật toán đăng ký trong `core/registry.py` (giao diện tự sinh form):

* **Swing Pivot + BOS/CHoCH** (`swing_pivot` **v1.1.0**) —
  [`docs/thuat_toan_swing_pivot.md`](docs/thuat_toan_swing_pivot.md).
  Pivot left/right tuyệt đối, HH/HL/LH/LL/EQH/EQL, phá vỡ theo close, phân loại
  **BOS chính / BOS nội bộ / CHoCH** khi đã có bias HH+HL hoặc LH+LL.
  Tắt `enable_choch` để mọi phá vỡ mang nhãn `BOS_UP`/`BOS_DOWN` như v1.0.0.
  HH/LH **so từng đỉnh cấp 1**.
* **Swing phân cấp** (`swing_hierarchy` **v1.0.0**) —
  [`docs/thuat_toan_swing_cap_2.md`](docs/thuat_toan_swing_cap_2.md).
  Cùng fractal cấp 1, rồi lọc đỉnh/đáy cấp 2 trên *chuỗi pivot* (ba đỉnh cấp 1
  liên tiếp, đỉnh giữa cao hơn hai cạnh). HH/LH **chỉ so hai đỉnh cấp 2**.
  Xác nhận cấp 2 lúc pivot cấp 1 bên phải đóng — không gắn tín hiệu về lúc đỉnh
  giữa hình thành. **Không** gồm BOS. Đây là thí nghiệm lọc cấu trúc, chưa phải ICT.
* **Baseline chỉ báo** (`indicator_baseline` v1.0.0) — đối chứng SMA/ATR Wilder,
  ADX Wilder, Donchian/ATR. [`docs/thuat_toan_indicator_baseline.md`](docs/thuat_toan_indicator_baseline.md).
  Không dùng TA-Lib. Ngưỡng mặc định không phải tối ưu XAUUSD.
* **HMM lọc online** (`hmm_online` v1.0.0) — fit `hmmlearn` trên prefix
  `train_bars`, `on_bar` chỉ bước forward. State mặc định `chua_gan_nghia`
  (không tự gắn Trend/Range). [`docs/thuat_toan_hmm_online.md`](docs/thuat_toan_hmm_online.md).
* **C2 Sweep + CISD** (`c2_cisd_research` **v0.1.0**, bản nghiên cứu) — chuyển thể
  closed-bar từ CantoLab *Open Source Fractal* (MIT, commit `1bb5326`). Chỉ dataset
  **M15** + kỳ **H4 mốc UTC epoch**: C2 quét low/high H4 rồi đóng lại, mức CISD trên
  M15 (nhánh trực tiếp / tìm ngược 2–10 / dự phòng như Pine), early CISD, vòng đời
  C3/C4 (phá, C4 không hợp lệ, hết hạn, gap). Chart có marker/đường mức/tooltip
  riêng và 4 lớp bật tắt; tab Thống kê có vòng đời setup và MFE/MAE đối chứng
  C2-only vs C2+CISD. **Chưa xác minh parity với Pine.**
  [`docs/thuat_toan_c2_cisd.md`](docs/thuat_toan_c2_cisd.md) (đặc tả, timeline tính
  tay, bảng khác biệt Pine, run minh hoạ). Giấy phép gốc:
  [`third_party/open-source-fractal/LICENSE`](third_party/open-source-fractal/LICENSE).

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

Xem [`docs/them_thuat_toan.md`](docs/them_thuat_toan.md).

**MT5 / tổng hợp nến.** [`docs/mt5_va_tong_hop_nen.md`](docs/mt5_va_tong_hop_nen.md).
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
[`docs/nhan_tham_chieu.md`](docs/nhan_tham_chieu.md).

**Đánh giá thuật toán.** Trang riêng [`/danh-gia`](http://127.0.0.1:8099/danh-gia)
— protocol có phiên bản, khoảng gán nhãn đầy đủ, F1, P90, ATR, so nhiều run,
nhảy từ TP/FP/FN tới nến. Không nhét metric vào tab thống kê dưới chart.
[`docs/danh_gia_thuat_toan.md`](docs/danh_gia_thuat_toan.md).

**Python ↔ MQL5.** Script [`mql5/SwingPivotExport.mq5`](mql5/SwingPivotExport.mq5),
tab *Đối chiếu MQL5*. Cần cùng `dataset_checksum`.
[`docs/doi_chieu_python_mql5.md`](docs/doi_chieu_python_mql5.md).

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
- Mã từng dataset: [`docs/du_lieu_thi_truong.md`](docs/du_lieu_thi_truong.md).

**Nạp thêm hoặc nạp lại sau khi pipeline dựng dữ liệu mới:**

```powershell
.\.venv\Scripts\python.exe scripts\import_market_data.py --dry-run series --pair XAUUSD --tf M15   # thử trên bản sao DB
.\.venv\Scripts\python.exe scripts\import_market_data.py series --pair XAUUSD --tf M15,H1         # nạp thật (tự sao lưu DB)
.\.venv\Scripts\python.exe scripts\import_market_data.py m1-year --pair EURUSD --year 2024 --resample ""
```

**Lưu ý:**
- Bộ XAUUSD 2024 cũ (tên bắt đầu bằng `[LỆCH GIỜ …]`) chỉ giữ để mở các run cũ; không dùng cho phân
  tích mới.
- Mọi thuật toán chạy được trên mọi dataset mới. Riêng `c2_cisd_research` chỉ nhận M15 (theo
  thiết kế).
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
│  ├─ types.py                Bar, StructureEvent, từ điển loại & mã lý do
│  ├─ engine.py               chạy tuần tự, ReplaySession, thống kê
│  ├─ registry.py             đăng ký thuật toán
│  ├─ algorithms/
│  │  ├─ base.py              interface StructureAlgorithm + ParamSpec
│  │  ├─ swing_pivot.py       v1.1.0 pivot + BOS/CHoCH
│  │  ├─ swing_hierarchy.py   v1.0.0 swing cấp 2
│  │  ├─ indicator_baseline.py đối chứng SMA/ATR/ADX
│  │  ├─ hmm_online.py        HMM forward (hmmlearn lúc fit)
│  │  └─ c2_cisd_research.py  v0.1.0 C2 sweep + CISD (M15–H4, nghiên cứu)
│  ├─ indicators.py           ATR/ADX Wilder, SMA, Donchian
│  ├─ labels.py               ghép nhãn greedy (tab Nhãn tham chiếu)
│  ├─ eval/                   protocol, matcher min-cost, F1/P90/ATR
│  ├─ mql5_compare.py         đối chiếu CSV MT5
│  └─ data/
│     ├─ loader.py            nạp CSV, dò cột, ánh xạ, múi giờ
│     ├─ validate.py          kiểm tra chất lượng
│     ├─ synthetic.py         bộ sinh dữ liệu mô phỏng
│     ├─ resample.py          tổng hợp nến utc_epoch
│     ├─ htf_stream.py        gộp H4 TUẦN TỰ từ M15 đã đóng (cho C2/CISD)
│     └─ mt5_source.py        MetaTrader5 tuỳ chọn (loại nến đang chạy)
├─ mql5/SwingPivotExport.mq5
├─ third_party/open-source-fractal/LICENSE   MIT của CantoLab (nguồn C2/CISD)
├─ backend/app/
│  ├─ main.py                 FastAPI routes + phục vụ frontend
│  ├─ service.py              nghiệp vụ: nhập, chạy, replay, so sánh, xuất
│  ├─ config.py               đường dẫn, giới hạn
│  └─ storage/db.py           SQLite
├─ frontend/                  HTML/CSS/JS tĩnh, không cần build
│  ├─ index.html              thử nghiệm
│  ├─ danh-gia.html           đánh giá thuật toán
│  └─ vendor/                 TradingView Lightweight Charts (Apache-2.0)
├─ data/                      lab.sqlite, raw/, samples/, exports/  (không commit)
├─ docs/                      đặc tả thuật toán, hướng dẫn mở rộng
├─ scripts/generate_synthetic.py
├─ tests/                     pytest (toàn bộ test cũ + phần mới)
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
| `tests/test_swing_pivot.py` | Pivot trên chuỗi nhỏ tính tay; nến bằng giá; dung sai EQH; warm-up; độ trễ xác nhận; BOS close/wick/chống phát lặp |
| `tests/test_choch_bos.py` | CHoCH, BOS nội bộ, BOS chính tính tay; cùng nến xuyên hai mức; `enable_choch=false`; nhân quả |
| `tests/test_indicator_baseline.py` | ATR Wilder tính tay; warm-up ADX; chuỗi tăng ra BASELINE_UP; nhân quả |
| `tests/test_resample_mt5.py` | M1→M5 tính tay; drop_incomplete; không lấp gap; MT5 mock loại nến đang hình thành |
| `tests/test_labels.py` / `test_mql5_compare.py` / `test_hmm_online.py` | Ghép nhãn precision/recall; checksum MQL5; HMM không phát trong prefix train |
| `tests/test_replay_causality.py` | Thêm **và sửa** dữ liệu sau `T` không đổi sự kiện đã xác nhận tại `T` |
| `tests/test_data.py` | CSV / MT5 TAB / chất lượng dữ liệu |
| `tests/test_api_flow.py` | Luồng API + resample + nhãn + evaluate |
| `tests/test_eval_protocol.py` | Matcher greedy vs min-cost tính tay; F1; P90; phạm vi nhãn không thành FP |
| `tests/test_eval_api.py` | Trang `/danh-gia`, lưu/mở evaluation, F1 trống khi chưa có nhãn, chấm M5/M15 tách nhóm khỏi H1 |
| `tests/test_label_page.py` | Trang `/gan-nhan`, nav 3 trang, nhãn M15 không hiện trên M5, bắt buộc tên người gán, đủ nút lưu/ghi đè/CSV, JS không lỗi cú pháp (`node --check`) |
| `tests/test_auto_label.py` | Đề xuất chỉ trong khoảng nến và khớp đúng sự kiện thuật toán; lọc loại; từ chối thuật toán không sinh nhãn cấu trúc và khoảng sai; cảnh báo nến cuối; đề xuất không tự lưu; nguồn gốc nhãn giữ qua lưu/ghi đè/CSV; cảnh báo khi chấm chính thuật toán đã đề xuất (và không cảnh báo với thuật toán khác) |
| `tests/test_c2_cisd.py` | C2/CISD: timeline tính tay (tăng, giảm lật giá), sweep bằng mức/không reclaim, outside bar, bias, mọi nhánh chọn mức CISD (doji, tìm ngược, nâng, dự phòng, biên i=10/11), chống reclaim bằng close cũ hơn mức, early CISD, phá trước xác nhận, CISD trong C4 rồi C4 fail, gap/kỳ thiếu/warm-up/biên UTC; nhân quả trên chuỗi ngẫu nhiên có gap và doji: prefix = full lọc theo `confirmed_at`, sửa suffix, batch/stream/reset/replay, không mutation, bất biến log |
| `tests/test_c2_cisd_api.py` | C2/CISD qua API: từ chối dataset không M15, lưu → mở lại → CSV/manifest giữ `details`, metric vòng đời + MFE/MAE, replay chỉ hiện sự kiện đã biết, chấm mục tiêu `c2`/`cisd` một-một cùng hướng và "chưa có nhãn" |
| `tests/test_label_persistence.py` | Nhãn ngoài phạm vi nến bị từ chối; nhãn trùng bị gộp; ghi đè tăng `revision` và giữ nguyên dataset; chặn ghi đè khi bộ đã dùng trong đánh giá đã lưu; xuất CSV nạp lại khớp; `parse-csv` không tự lưu |

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
