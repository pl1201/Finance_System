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
điểm tín hiệu thực sự khả dụng → lưu, mở lại và so sánh các lần chạy → xuất CSV
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

Bản này có bốn thuật toán đăng ký trong `core/registry.py` (giao diện tự sinh form):

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

**Nhãn tham chiếu.** Tab *Nhãn tham chiếu* — click chart, lưu bộ nhãn có người
gán và rubric, đối chiếu precision/recall.
[`docs/nhan_tham_chieu.md`](docs/nhan_tham_chieu.md).

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
│  │  ├─ indicator_baseline.py đối chứng SMA/ATR/ADX
│  │  └─ hmm_online.py        HMM forward (hmmlearn lúc fit)
│  ├─ indicators.py           ATR/ADX Wilder, SMA, Donchian
│  ├─ labels.py               ghép nhãn, precision/recall
│  ├─ mql5_compare.py         đối chiếu CSV MT5
│  └─ data/
│     ├─ loader.py            nạp CSV, dò cột, ánh xạ, múi giờ
│     ├─ validate.py          kiểm tra chất lượng
│     ├─ synthetic.py         bộ sinh dữ liệu mô phỏng
│     ├─ resample.py          tổng hợp nến utc_epoch
│     └─ mt5_source.py        MetaTrader5 tuỳ chọn (loại nến đang chạy)
├─ mql5/SwingPivotExport.mq5
├─ tests/                     > 84 test gốc + phần mới
├─ backend/app/
│  ├─ main.py                 FastAPI routes + phục vụ frontend
│  ├─ service.py              nghiệp vụ: nhập, chạy, replay, so sánh, xuất
│  ├─ config.py               đường dẫn, giới hạn
│  └─ storage/db.py           SQLite
├─ frontend/                  HTML/CSS/JS tĩnh, không cần build
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

---

## 9. Giới hạn đã biết

**Phạm vi**

* Chưa có LLM, chưa kết nối broker để **gửi lệnh**, chưa có backtest hay P&L.
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

**Đã kiểm chứng và chưa kiểm chứng**

* Đã chạy bộ pytest đầy đủ trên máy phát triển (kể cả test cũ).
* **Chưa** biên dịch/chạy `SwingPivotExport.mq5` trong MetaEditor trên máy này.
* **Chưa** lấy lịch sử live từ terminal MT5 trong phiên làm việc này (có test mock).
* **Chưa** kiểm tra Firefox/Safari hay dataset hàng trăm nghìn nến.
