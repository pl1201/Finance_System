# AGENTS.md — Quy tắc thiết kế và làm việc trong Market Structure Lab

Áp dụng cho mọi người và mọi AI agent (Codex, Claude…) sửa code hoặc tài liệu trong thư mục này.
Khi một quy tắc ở đây mâu thuẫn với yêu cầu trong một task cụ thể, **hỏi lại người giao việc**,
không tự chọn.

Lab là **công cụ nghiên cứu nhận diện cấu trúc thị trường**: chạy local, không kết nối broker,
không gửi lệnh, không tính P&L. ICT/SMC, swing, BOS… là **ứng viên nghiên cứu**, phải được định
nghĩa chính xác và kiểm chứng — chưa phải công thức đã chốt.

---

## 1. Đọc trước khi làm

| Thứ tự | File | Để biết |
|---|---|---|
| 1 | `AGENTS.md` (file này) | Quy tắc bắt buộc |
| 2 | [`docs/guides/kien_truc_luong_ict.md`](docs/guides/kien_truc_luong_ict.md) | Khái niệm nào cần khái niệm nào; dữ liệu đi qua các tầng nào; việc đang làm nằm ở đâu |
| 3 | `docs/algorithms/thuat_toan_<tên>.md` của thuật toán liên quan | Định nghĩa đang có hiệu lực, phiên bản, chỗ đã chọn |
| 4 | [`docs/guides/them_thuat_toan.md`](docs/guides/them_thuat_toan.md) | Hợp đồng `StructureAlgorithm`, cách đăng ký |
| 5 | [`docs/research/nghien_cuu_ict_smc_thuat_toan.md`](docs/research/nghien_cuu_ict_smc_thuat_toan.md) §3, §7 | Khi đụng khái niệm ICT: các cài đặt khác làm thế nào, chỗ nào mơ hồ |
| 6 | `git status` | Thay đổi đang có của người khác — phải giữ nguyên |

---

## 2. Nguyên tắc bất biến

Vi phạm một trong các điều dưới đây = kết quả nghiên cứu vô giá trị. Không đánh đổi để kịp tiến độ.

1. **Nhân quả.**
   - `on_bar` chỉ dùng nến đã nạp. Không truy cập nến sau, không dùng min/max/thống kê của toàn
     dataset.
   - `confirmed_at` = `close_time` của nến đang xử lý. `event_time` là nến chứa cấu trúc.
   - Sự kiện đã trả về không bị sửa hay thu hồi. `reset()` xoá sạch trạng thái. Cùng dữ liệu →
     cùng kết quả, kể cả `event_id`.
   - Kết quả tương lai (FVG «đã lấp», MFE/MAE, trend «đúng») chỉ là **nhãn đánh giá**, không bao
     giờ là tín hiệu hay đầu vào của detector.
   - Ngữ cảnh khung lớn chỉ lấy từ nến khung lớn **đã chốt**, gộp tuần tự từ chính luồng nến đang
     xử lý. Nến khung lớn đang hình thành chỉ được vẽ (có nhãn), không vào trạng thái.
2. **Dữ liệu.**
   - Không tự lấp nến thiếu. Gap phải có trạng thái/sự kiện riêng và chính sách xử lý ghi rõ.
   - Lỗi dữ liệu có trạng thái riêng, **không gộp** thành Range, Uncertain hay «không có cơ hội».
   - Timestamp lưu UTC; múi giờ nguồn và quy ước mốc mở/đóng nến do người nhập khai báo, không
     tự đoán. Dữ liệu mô phỏng luôn gắn nhãn MÔ PHỎNG.
3. **Không âm thầm đổi kết quả cũ.** Thay đổi làm output mặc định của thuật toán đã có khác đi
   phải tăng phiên bản, ghi lịch sử phiên bản, và chứng minh bằng hồi quy (§7.3).
4. **Không thổi phồng.** Không gọi thuật toán là AI, dự báo, «công thức ICT chuẩn» hay tín hiệu
   giao dịch. Không đưa win rate/P&L vào thống kê lần chạy. Không kết luận «tốt hơn» khi chưa có
   nhãn tham chiếu và chuẩn so sánh (§6).
5. **Nguồn và giấy phép.** Chép/chuyển thể code ngoài phải ghi repo + commit + giấy phép trong
   file và tài liệu (mẫu: `core/algorithms/c2_cisd_research/algorithm.py`). Code giấy phép CC BY-NC-SA (vd LuxAlgo) **chỉ
   đọc để so sánh định nghĩa**, không chép vào lab.

---

## 3. Vòng thiết kế cho một khái niệm hoặc thuật toán mới

Mỗi khái niệm đi đủ 8 bước. Không bỏ bước 2 và 4.

| Bước | Việc | Sản phẩm bắt buộc |
|---|---|---|
| ① Đọc nguồn | Video/bài gốc, các cài đặt khác (nghiên cứu §3) | Danh sách nguồn có link; video ghi ID + mốc thời gian |
| ② Định nghĩa vận hành | Viết spec **trước khi code** | `docs/algorithms/thuat_toan_<tên>.md` theo khung §3.1 |
| ③ Code | Đặt đúng tầng (§4), thứ tự xử lý trong nến cố định | Thuật toán/thành phần + đăng ký registry; plugin hiển thị `frontend/js/algos/<tên>.js` nếu cần vẽ riêng (§8) |
| ④ Test | Tính tay + nhân quả + biên (§7.1) | `tests/algorithms/test_<tên>.py` (+ `tests/api/` nếu đổi backend) |
| ⑤ Chạy thật | Dữ liệu thật, xem từng nến bằng replay | Số liệu mô tả (mật độ, độ trễ), ảnh/ghi chú |
| ⑥ Nhãn | Người gán nhãn độc lập với output (§6.2) | Bộ nhãn có quy tắc, người gán, khoảng gán đầy đủ |
| ⑦ Đánh giá | So với baseline/chuẩn ngẫu nhiên, đoạn phát triển rồi đoạn kiểm tra | Bảng kết quả + run_id tái lập được |
| ⑧ Sửa | Đổi định nghĩa → tăng phiên bản → lặp lại từ ② | Lịch sử phiên bản trong spec |

### 3.1. Khung bắt buộc của `docs/algorithms/thuat_toan_<tên>.md`

1. Trạng thái, phiên bản, lịch sử phiên bản.
2. Khái niệm này nằm ở tầng nào, cần đầu vào gì, cho đầu ra gì (theo `kien_truc_luong_ict.md` §2).
3. Tham số: mặc định, ràng buộc, ý nghĩa; tham số nào chỉ có hiệu lực trong chế độ nào.
4. Quy tắc từng bước, **thứ tự xử lý trong một nến**, điều kiện biên (bằng nhau, chạm đúng ngưỡng).
5. Thời điểm biết của mỗi sự kiện (`event_time` vs `confirmed_at`).
6. **Chỗ mơ hồ đã chọn**: phương án nào, vì sao, nguồn nào, ảnh hưởng tới kết quả ra sao
   (mẫu: `disambiguation.md` của smc-ict-research, xem nghiên cứu §5.1).
7. Khác biệt so với plan/nguồn gốc, giới hạn đã biết, kiểm thử đã chạy.

Mẫu đầy đủ: [`docs/algorithms/thuat_toan_dc_atr_structure.md`](docs/algorithms/thuat_toan_dc_atr_structure.md).

### 3.2. Chỗ mơ hồ

- Không chọn im lặng. Khi các nguồn cho định nghĩa khác nhau mà chưa có căn cứ chọn, cài **hai
  biến thể có tên riêng** và chấm trên cùng bộ nhãn.
- Con số không có nguồn gốc (ngưỡng displacement, dung sai «bằng giá», số nến cho sweep…) là
  **tham số thí nghiệm**: đặt tên, có mặc định, ghi rõ «do lab chọn».
- Nguồn do LLM tổng hợp (vd ict-knowledge-library) chỉ dùng để tìm video gốc; số liệu không trỏ
  tới video thì không dùng làm căn cứ.

---

## 4. Kiến trúc và vị trí code

```text
core/data/         nạp, kiểm tra, chuẩn hoá, tổng hợp khung       (không biết thuật toán)
core/indicators.py chỉ báo thuần Python (ATR…)
core/vocab/        loại sự kiện + mã lý do + câu giải thích theo họ (ghép ở core/types.py)
core/algorithms/   StructureAlgorithm — mỗi thuật toán một gói <tên>/ (algorithm.py + phần riêng)
core/engine.py     nạp từng nến, replay                           (không sửa khi thêm thuật toán)
core/eval/         protocol, matcher, metric, kiểm tra nhân quả
backend/app/       FastAPI + SQLite                               (không chứa logic thuật toán)
  routers/ schemas/  route + model Pydantic theo mảng (datasets, runs, labels, evaluations, mql5, replay)
  services/          nghiệp vụ cùng tên router; storage/ = repo SQLite + schema/migrate
frontend/          HTML/JS tĩnh, không bước build
  js/lib/            dùng chung: dom, format, timeframe, api, labeldraft
  js/chart/          lõi chart (market-chart), dựng series, lớp phủ trang Đánh giá/Gán nhãn
  js/algos/          plugin hiển thị theo thuật toán (registry + swing, baseline, c2_cisd, dc_atr)
  js/pages/<trang>/  lab · label · eval — mỗi trang nhiều script nhỏ chung namespace MSL.<trang>
scripts/           công cụ: nạp dữ liệu, sinh dữ liệu mô phỏng, hồi quy run đã lưu
research/          script thí nghiệm / khảo sát tái lập (dc_experiment, ict_survey)
tests/             core/ · algorithms/ · api/ · frontend/ (helpers.py, conftest.py ở gốc)
docs/              algorithms/ (spec) · plans/ · research/ (+ khao_sat/) · guides/
```

1. **Chiều phụ thuộc:** `core` không import `backend`, `frontend`, FastAPI, SQLite, pandas,
   notebook hay MetaTrader5. numpy/hmmlearn chỉ trong `hmm_online` lúc fit.
2. **Theo tầng khái niệm** (`kien_truc_luong_ict.md` §2): tầng trên chỉ đọc sự kiện **đã xác nhận**
   của tầng dưới, ở nến này hoặc trước. Khái niệm tầng 1–3 mới nên viết thành **thành phần dùng
   chung** (hướng `core/components/`, §4.2 tài liệu kiến trúc) thay vì cài lại trong một khối mới.
3. **Nguồn swing phải thay được** (pivot, DC, «leg»…) vì mọi tầng trên phụ thuộc nó.
4. **Thứ tự trong một nến** của thuật toán tổ hợp được ghi trong spec và cố định trong code.
5. **Truy vết:** sự kiện suy ra từ sự kiện khác ghi `reference_event_id` và/hoặc
   `details.basis = [event_id, …]`.
6. Không đổi chữ ký `StructureAlgorithm`, `engine`, schema SQLite khi chưa thống nhất. Thêm thông
   tin mới vào `details`, `manifest_info`, `run_stats`, `timeline_point`, `pending_state`.
   Thay đổi hợp đồng dùng chung (vd `ParamSpec.show_if`, `since` của replay) phải tương thích
   ngược và ghi vào `docs/guides/them_thuat_toan.md`.

---

## 5. Quy ước sự kiện, tham số, phiên bản

### 5.1. Sự kiện
- `structure_type` và `reason_code` mới khai báo trong `core/vocab/<họ>.py` (lớp loại, lớp lý do,
  hai từ điển câu giải thích tiếng Việt), thêm họ vào `core/vocab/__init__.py::FAMILIES`.
  `core/types.py` ghép lại: mọi nơi vẫn dùng `StructureType.X`, `ReasonCode.Y` (tooltip đọc từ đây).
- `event_id` tất định, không phụ thuộc độ dài dataset (vd `dc:s{segment}:{TYPE}:{extreme}>{confirm}`).
- **Một sự kiện cho một cấu trúc**: nhãn phụ (HH/HL/EQ…) để trong `details`, không phát sự kiện
  thứ hai cho cùng pivot (matcher sẽ đếm trùng).
- `details` mang **công thức với số thực** đã dùng để quyết định (ngưỡng, mức so sánh, dung sai),
  để giao diện giải thích được mà không tính lại.

### 5.2. Tham số
- Khai báo bằng `ParamSpec`: kiểu, min/max, `help_vi`; `show_if` nếu chỉ có hiệu lực ở một chế độ.
- Validate chặt: số hữu hạn, đúng kiểu, ràng buộc liên trường, từ chối tham số lạ.
- Mặc định là **cấu hình thí nghiệm**, không gọi là «tối ưu».

### 5.3. Phiên bản thuật toán

| Thay đổi | Phiên bản | Bằng chứng cần có |
|---|---|---|
| Refactor, sửa chữ, không đổi output | giữ nguyên | Hồi quy run đã lưu khớp (§7.3) |
| Thêm tuỳ chọn/biến thể, **mặc định không đổi output** | tăng minor (vd 0.1.0 → 0.2.0) | Hồi quy khớp `event_id`, giá, nến, `reason_code` |
| Output mặc định thay đổi (kể cả sửa lỗi) | tăng phiên bản, ghi lý do | Bảng khác biệt trước/sau trong spec |

---

## 6. Đánh giá

### 6.1. Hai loại so sánh — không trộn
| Loại | Hỏi | Cần |
|---|---|---|
| Kiểm tra bản cài đặt | Hai bản code (Python/MQL5/Pine) có thực hiện **cùng** định nghĩa không? | Cùng snapshot dữ liệu (checksum), cùng tham số, cùng warm-up |
| Chất lượng nhận diện | Định nghĩa nào khớp cấu trúc mà người phân tích thấy, trễ bao nhiêu? | Nhãn tham chiếu + protocol chấm cố định |

### 6.2. Nhãn tham chiếu
- Gán theo **quy tắc viết sẵn** (gán cấp swing nào, wick hay close, xử lý gap, hai đỉnh bằng nhau).
- Độc lập với output thuật toán: không chấp nhận hàng loạt gợi ý auto-label rồi coi là chân lý.
- Khai báo **khoảng gán đầy đủ** (coverage); ngoài khoảng đó không tính false positive.
- So khác định nghĩa (vd DC theo close vs nhãn swing theo wick) phải khai `event_type_map` và ghi
  «so chéo định nghĩa».

### 6.3. Thí nghiệm
- Cố định snapshot dữ liệu, đoạn phát triển / đoạn kiểm tra theo thời gian **trước khi** xem kết quả.
- Chọn tham số trên đoạn phát triển; đoạn kiểm tra chỉ dùng để xác nhận. Mở rộng lưới tham số sau
  khi đã xem đoạn kiểm tra thì không còn gọi là kiểm tra độc lập.
- Luôn có baseline (pivot 3/3 hiện tại) và, khi đo giá trị dự báo, chuẩn **vào lệnh ngẫu nhiên có
  cấu trúc tương đương** — không so với 0.
- Báo cáo kèm số mẫu, độ trễ (trung vị, P90), mật độ; nêu rõ khi chưa có nhãn.
- Thí nghiệm phải tái lập bằng script (mẫu `research/dc_experiment.py`); run lưu vào DB gắn nhãn rõ
  (vd `[DC thí nghiệm YYYYMMDD] …`).

---

## 7. Kiểm thử và xác minh trước khi báo «xong»

### 7.1. Test bắt buộc cho thuật toán/thành phần mới
- Chuỗi nhỏ **tính tay**, gồm các biên: thiếu ngưỡng / đúng ngưỡng / vượt ngưỡng, bằng nhau.
- Warm-up, dữ liệu không hợp lệ (NaN/inf, OHLC sai, timestamp trùng/lùi), gap.
- **Nhân quả**: chạy prefix tại nhiều điểm cắt = full run lọc theo `confirmed_at`; sửa dữ liệu sau
  T không đổi sự kiện trước T; deep-copy sự kiện đã trả rồi nạp tiếp để phát hiện sửa ngầm;
  replay lùi = chạy prefix mới.
- Tích hợp API nếu có thay đổi backend: run → lưu → mở lại → CSV/manifest.
- Vị trí: thuật toán/thành phần → `tests/algorithms/`, lõi dùng chung → `tests/core/`, API →
  `tests/api/`, trang/JS → `tests/frontend/`. Fixture dùng chung để ở `tests/helpers.py`.

### 7.2. Lệnh
```powershell
.\run.ps1 -Test
# hoặc
$env:PYTHONPATH = $PWD; .\.venv\Scripts\python.exe -m pytest -q
```
Chạy **toàn bộ** test, không chỉ file mới. Test dùng thư mục tạm, không đụng `data/`.

### 7.3. Hồi quy run đã lưu
Khi sửa thuật toán đã có hoặc thành phần dùng chung: chạy lại mọi run đã lưu của thuật toán đó
với `save=False` và so `event_id`, giá, `confirmed_bar_index`, `reason_code` với sự kiện trong DB
(chỉ đọc). Ghi kết quả vào báo cáo.
```powershell
.\.venv\Scripts\python.exe scripts
egression_saved_runs.py                 # so với sự kiện trong DB
.\.venv\Scripts\python.exe scripts
egression_saved_runs.py --snapshot F.json # dấu vân tay đầy đủ trước khi sửa
.\.venv\Scripts\python.exe scripts
egression_saved_runs.py --compare F.json  # ... và so sau khi sửa
```

### 7.4. Thay đổi giao diện
Kiểm tra bằng trình duyệt thật trên **bản sao DB** (đặt `MSL_DATA_DIR`/`MSL_DB_PATH` trỏ vào thư
mục tạm), không trên `data/lab.sqlite` thật. Kiểm tra cả: replay lùi/tiến, không lỗi JS, bố cục
không tràn, trục giá không bị giãn.

---

## 8. Giao diện

- Giữ stack hiện có: HTML/JS tĩnh, không bundler, Lightweight Charts v4.2.3. JS theo phong cách
  sẵn có (`var`, hàm thường, IIFE gắn vào `window.MSL`). Đổi JS/CSS thì tăng `?v=` trong các file HTML.
- **Phần hiển thị riêng của một thuật toán chỉ nằm trong plugin** `frontend/js/algos/<tên>.js`
  (`MSL.algos.register`, danh sách hook ở `algos/registry.js`, cách viết ở
  `docs/guides/them_thuat_toan.md` §2, Bước 4). Lõi chart và các trang không so tên thuật toán. Plugin mới
  thêm `<script>` vào cả ba trang, sau `algos/registry.js` và trước `chart/market-chart.js`.
- Replay chỉ hiện sự kiện có `confirmed_at` ≤ con trỏ; trạng thái/vùng chỉ tô từ lúc biết,
  không tô ngược.
- Phân biệt rõ: close vs wick, ứng viên (nét đứt, «có thể đổi») vs đã xác nhận, nến sự kiện vs nến
  xác nhận.
- Màu không là kênh duy nhất: có chữ, legend, tooltip, bảng thay thế.
- Mỗi trạng thái có hiển thị riêng: đang tải, lỗi, không có sự kiện, warm-up, gap, chưa có nhãn,
  dữ liệu mô phỏng.
- Thuật toán mới có replay thì cân nhắc thêm nhánh cho khung «Thuật toán đang làm gì», đọc từ
  `pending_state` và `details` — không tính lại logic ở frontend.
- **Dataset dài** (dữ liệu thật tới 372 000 nến):
  - Khoảng mặc định ≤ 50 000 nến; khoảng > 100 000 nến phải xác nhận.
  - Thuật toán mới phải chạy được trên M15 8 năm và M1 một năm mà **không** tăng theo bình phương
    số nến — thử bằng ma trận thuật toán × dataset trước khi báo xong.
  - `chart.setBars` xoá lớp phủ cũ; mọi nơi gọi phải dựng lại lớp phủ bằng `setEvents`.

---

## 9. Thị trường và dữ liệu cần nhớ

- XAUUSD M15 (HistData 2024) có nghỉ phiên hằng ngày ~1,25 giờ (20:45→22:00 UTC mùa hè,
  21:45→23:00 UTC mùa đông) và nghỉ cuối tuần. Mọi detector phải có chính sách gap rõ ràng.
- Killzone/phiên ICT tính theo **giờ New York**, phải xử lý đổi giờ mùa hè; không dùng mốc UTC cố định.
- Ngày giao dịch của dữ liệu bắt đầu 17:00 New York (giờ nghỉ 17:00–18:00 NY). Mốc nến H4/D1
  (`utc_epoch` hay `ny_1700`) làm đổi kết quả — luôn là tham số ghi trong run
  (`docs/plans/plan_ict_structure.md` §11.3).
- Lịch phiên (nghỉ hằng ngày, cuối tuần, ngày lễ đóng sớm/đóng cả ngày) là **dữ liệu khai báo**,
  không suy từ dữ liệu. Ngày lễ ≠ mất dữ liệu.
- **Giờ gốc HistData không phải «EST cố định»:**
  - tới hết 2018 bám giờ New York;
  - từ 2019 = giờ server châu Âu − 7 giờ.

  Quy đổi theo New York làm lệch 1 giờ trong các tuần Mỹ–Âu lệch lịch đổi giờ. Bộ XAUUSD 2024 cũ
  (`ds_1f78f44c0ba5`, `ds_84680e6033c3`, `ds_564bff443e42`, `ds_5797877d0752`) mắc lỗi này; đã thay
  bằng bộ đúng giờ (M15 `ds_db1583cd4dde`, M5 `ds_933fa5ec67e2`, H1 `ds_771a79d4d604`, M1
  `ds_0d44e89df5fd`). Bộ cũ chỉ giữ để mở run cũ — **không dùng cho phân tích mới**.
- **Dữ liệu thị trường do repo riêng `market-data-pipeline` sinh** (cạnh lab; đã kiểm bằng Dukascopy,
  FXCM, COMEX). Lab chỉ nạp: `scripts/import_market_data.py`. Dataset đã nạp và cách nạp thêm:
  `docs/guides/du_lieu_thi_truong.md`. Không viết lại bộ tải/quy đổi trong lab.
- Lịch phiên khai báo: bản sao ở `data/calendars/` (`cme_globex_metals` cho XAUUSD, `fx_spot` cho
  EURUSD), đọc bằng `core/data/session_calendar.py`. Lịch gốc và mọi sửa đổi nằm ở pipeline; sửa lịch
  chỉ khi có nguồn ngoài (`market-data-pipeline/docs/du_lieu_thi_truong.md` §5).
- Số liệu khảo sát dùng để thiết kế phải tái lập được: script trong `research/`, JSON trong
  `docs/research/khao_sat/` kèm checksum dataset/đoạn, phiên bản, cấu hình (mẫu: `research/ict_survey.py`).
- Không dùng thông số pip/lot của EURUSD cho vàng. So sánh biên độ giữa các mã dùng ATR hoặc
  basis point.

---

## 10. Làm việc với repo

- **Giữ nguyên thay đổi đang có**: không `reset`, `checkout --`, `clean`, không ghi đè file mình
  chưa đọc.
- **Không commit/push** trừ khi được yêu cầu rõ. Repo có thể báo «dubious ownership»: chỉ dùng
  `git -c safe.directory=<đường dẫn> …` cho lệnh đọc, không sửa cấu hình git global.
- Không ghi vào `data/lab.sqlite` ngoài các run thí nghiệm được yêu cầu (gắn nhãn rõ). Không xoá
  run, dataset, bộ nhãn.
- Không mở rộng/chỉnh thuật toán ngoài phạm vi task (vd `c2_cisd_research` khi task không nói tới).
- Tài liệu, chữ trên giao diện, câu giải thích sự kiện viết **tiếng Việt**; tên biến, mã sự kiện
  giữ tiếng Anh như hiện tại.
- **Báo cáo khi xong:** file đã đổi; lệnh test đã chạy và kết quả; hồi quy/smoke đã làm; phần chưa
  làm hoặc không kiểm tra được (nói thẳng, không đánh dấu xong).

---

## 11. Quyết định đã chốt (cập nhật khi chốt thêm)

| Quyết định | Giá trị hiện tại | Nguồn |
|---|---|---|
| Baseline cấu trúc | `swing_pivot` 3/3 v1.1.0, không đổi | `docs/algorithms/thuat_toan_swing_pivot.md` |
| DC: giá tìm cực trị | close | `docs/algorithms/thuat_toan_dc_atr_structure.md` |
| DC: chính sách gap mặc định | `reset` (tuỳ chọn `bridge_short` ≤ 2 giờ) | như trên, §3 |
| Trend/Range của DC | định nghĩa vận hành của lab, không phải chân lý | như trên, §6 |
| FVG | 3 nến, gắn nhãn tại nến thứ 3 (khi được cài) | nghiên cứu §3.3, §6.1 |
| Nguồn swing chuẩn cho các tầng ICT | **chưa chốt** — chờ so sánh trên nhãn thật | `kien_truc_luong_ict.md` §6 |
| `ict_structure`: BOS/CHoCH/MSS | **không dùng** (người dùng chốt 02/10/2026); BOS/CHoCH chỉ còn ở baseline `swing_pivot` | `plan_ict_structure.md` §8.1 B1 |
| `ict_structure`: tín hiệu đổi hướng | shift = quét thanh khoản rồi displacement ngược chiều | như trên, B2, §4.7 |
| `ict_structure`: bias | ba thành phần riêng (thứ tự đỉnh/đáy, phản ứng PD array khung lớn, DOL); **không ghép** trong bộ nhận diện — ghép ở lớp kịch bản | như trên, B3 |
| Order block; ngưỡng sweep/displacement/respect | **chưa chốt** — mặc định đề xuất ở plan §8.2, chờ nhãn | `plan_ict_structure.md` §8.2 |
