# Ngoài cách đọc ICT, lab nên thử phương pháp nào?

Ngày 12/10/2026 · khảo sát tài liệu, **chưa chạy thí nghiệm** trên dữ liệu lab. Dữ liệu đầy đủ 287 mục (mọi trường, nguồn có
link): [`khao_sat/danh_muc_quant_2026-10-12.json`](khao_sat/danh_muc_quant_2026-10-12.json). Bản xem có lọc / xuất CSV:
`D:\Finance_System\Danh_muc_phuong_phap_quant_2026-10-12.html`. Liên quan: [`../plans/plan_bias_regime.md`](../plans/plan_bias_regime.md).

## 1. Vấn đề

Cách đọc ICT mô tả cấu trúc tốt nhưng chưa có bằng chứng biết trước giá đi đâu: 7 cách đọc order flow không hơn đoán ngẫu nhiên
(±2 điểm %); bộ Trend/Range hiện có gần như không báo Range (≤ 0,2% thời gian); chưa thuật toán nào có F1 vì chưa có nhãn. Cần
đối thủ độc lập để so.

## 2. Cách tìm

8 agent nghiên cứu song song, mỗi agent một nhóm (R1 mô hình trạng thái · R2 điểm đổi · R3 chỉ số trend/range/biến động · R4 vi
cấu trúc · R5 mẫu hình giá · R6 học máy · R7 đánh giá · R8 chiến lược router), được 287 mục. Chấm 1–5 theo năm tiêu chí: chỉ cần
OHLC · dùng được ở từng nến · giải thích được · có bằng chứng độc lập · cài không tốn. Tin cậy A/B/C. Hạn mức tìm kiếm web hết giữa
chừng, 34 mục ở mức C.

## 3. Phát hiện

1. **Biến động đoán được, hướng thì gần như không** ở khung trong ngày (R1-06, R1-29).
2. **Nhiều «quy luật» cấu trúc là tính chất của bước ngẫu nhiên** (R5-03, R5-18) → thống kê swing / sweep / shift phải đặt cạnh
   cùng thống kê trên dữ liệu mô phỏng.
3. **Đo sai rất dễ nếu không chuẩn hoá:** dao động M15 theo giờ phiên làm sai các phép kiểm trên dữ liệu thô; «không báo gì cả»
   thắng nhiều thuật toán điểm đổi (R2-25, R2-35) → khử giờ phiên trước, luôn có baseline «không làm gì».

## 4. Đề xuất: regime hai trục, 3 bước, 18 phương pháp

Trục **biến động** (nén · bình thường · bung · nhảy) — bằng chứng vững, Breakout nằm ở đây. Trục **hướng** (Trend ↑ / ↓ · Range) —
phải thắng ngẫu nhiên mới giữ ở M15, không thì chuyển H1.

1. **Làm sạch thước đo:** khử dao động theo giờ phiên (R3-26) · dao động từ nến M1 (R4-10) · kiểm định nhảy giá (R4-14) · cờ giờ
   thanh khoản mỏng + cột spread MT5 (R4-09).
2. **Vòng so tài ICT với 6 đối thủ** trên đoạn phát triển: tỷ lệ dao động ngắn/dài (R3-27) · Page–Hinkley/CUSUM (R2-02) · độ dốc
   Kalman (R1-25) · variance ratio (R3-13) · time-series momentum (R3-31) · jump model online (R1-17). Chấm cùng thước: mô phỏng
   (R7-22), shift test (R7-20), baseline «không làm gì» (R7-46), bootstrap theo ngày (R7-17).
3. **Dựng `ict_regime` hai trục:** Uncertain có nguyên tắc (R6-29, R6-31) · giảm công gán nhãn (R6-25, R6-27).

Cho repo giao dịch sau này: luôn đứng ngoài (R8-33), trend-following khung ngày (R8-02), Donchian (R8-05).

## 5. Cần quyết

1. Tách regime hai trục trong plan giai đoạn 4? — đề xuất: có.
2. Chạy vòng so tài trước khi code `ict_regime`? — đề xuất: có.
3. Đọc cột spread MT5 (lấy lại dữ liệu) và chọn nguồn lịch tin? — đề xuất: spread ở bước 1, lịch tin để sau.

## Phụ lục: bảng 287 mục (rút gọn cột)

### R1 — Mô hình trạng thái & regime thống kê (33 mục)

Bằng chứng ngoài mẫu cho mô hình trạng thái trên FX yếu: Markov-switching khớp tốt in-sample nhưng không thắng random walk theo MSE (Engel 1994, 18 tỷ giá); Ardia et al. (2018) thấy MS-GARCH «generally not required» cho 8 tỷ giá ngày; kiểm định mạnh hầu hết nằm ở cổ phiếu ngày/tuần, intraday FX chỉ có một preprint 2026 (EUR/USD H1/H4). Điểm chung quan trọng cho lab: trạng thái HMM fit trên return FX tách theo VOL chứ không theo HƯỚNG (Persson 2021: EUR/USD 3 trạng thái mean ≈ 0, σ 0.33/0.52/0.89%), nên muốn Trend/Range phải đưa nghĩa vào cấu trúc mô hình (dấu hệ số AR trong MS-AR, slope/SE của local linear trend, đặc trưng ER/DC trong jump model). Đánh đổi trễ ↔ nhấp nháy là trục chính; fixed-lag smoothing (trễ đúng L nến) và phạt nhảy λ (jump model) là hai núm điều khiển rõ ràng, không cần P&L. Ghi chú quy trình: hạn mức WebSearch dùng chung bị hết giữa chừng; các mục cuối được xác minh bằng WebFetch trực tiếp trang IDEAS/arXiv/tài liệu thư viện.

Đề xuất: thử sớm 9, cân nhắc 13, để sau 9, bỏ qua 2.

| Mã | Phương pháp | Dữ liệu | Nhân quả | Tin cậy | Phù hợp | Đề xuất | Vai trò |
|---|---|---|---|---|---:|---|---|
| R1-01 | Markov-switching trung bình/phương sai (Hamilton) *(đã có trong tài liệu lab)* | OHLC | online | A | 4 | cân nhắc | baseline, bằng chứng regime, nhãn tham chiếu |
| R1-02 | Markov-switching tự hồi quy với hệ số AR đổi theo chế độ (MS-AR) | OHLC | online | A | 4 | thử sớm | bộ phân loại, bằng chứng regime, baseline |
| R1-03 | Markov-switching với xác suất chuyển thay đổi theo thời gian (TVTP) | OHLC+tick_volume | online | B | 4 | cân nhắc | bằng chứng regime, bộ phân loại, đặc trưng |
| R1-04 | Markov-switching GARCH (MS-GARCH) | OHLC | online | A | 3 | để sau | đặc trưng, bằng chứng regime |
| R1-05 | Multi-scale MS-GARCH cho EUR/USD intraday (1D/4H/1H) | OHLC | online | B | 3 | để sau | bằng chứng regime, đặc trưng |
| R1-06 | Gaussian HMM lọc forward (tách fit / suy luận) *(đã có trong tài liệu lab)* | OHLC | online | B | 4 | thử sớm | baseline, bằng chứng regime |
| R1-07 | Làm trơn trễ cố định (fixed-lag smoothing) cho HMM / state-space | OHLC | online, có trễ | B | 4 | thử sớm | nhãn tham chiếu, bằng chứng regime, đánh giá |
| R1-08 | HMM phát xạ Student-t / hỗn hợp Gaussian | OHLC | online | A | 4 | cân nhắc | bộ phân loại, baseline |
| R1-09 | Hidden semi-Markov model (HSMM) *(đã có trong tài liệu lab)* | OHLC | online | B | 3 | để sau | bằng chứng regime |
| R1-10 | Sticky HDP-HMM (Fox et al.) | OHLC | hậu kiểm | A | 2 | để sau | nhãn tham chiếu |
| R1-11 | Infinite HMM gộp regime switching và structural break (Song) | OHLC | hậu kiểm | A | 2 | bỏ qua | nhãn tham chiếu |
| R1-12 | Chọn số trạng thái HMM theo cách thực dụng (Pohle et al.) | OHLC | hậu kiểm | A | 4 | thử sớm | đánh giá |
| R1-13 | Label switching và ánh xạ trạng thái → nghĩa *(đã có trong tài liệu lab)* | OHLC | online | A | 4 | thử sớm | đánh giá |
| R1-14 | HMM thích nghi với tham số thay đổi theo thời gian (forgetting) | OHLC | online | B | 4 | cân nhắc | bộ phân loại, bằng chứng regime |
| R1-15 | Online EM cho HMM (Cappé) | OHLC | online | A | 4 | để sau | bộ phân loại |
| R1-16 | Statistical jump model (JM) *(đã có trong tài liệu lab)* | OHLC | online, có trễ | B | 4 | thử sớm | baseline, bằng chứng regime, bộ phân loại |
| R1-17 | Greedy online jump model với đặc trưng realized volatility intraday *(đã có trong tài liệu lab)* | OHLC | online | A | 4 | thử sớm | baseline, bằng chứng regime |
| R1-18 | Sparse jump model (chọn đặc trưng trong jump model) | OHLC | online, có trễ | B | 4 | cân nhắc | đánh giá, đặc trưng, bằng chứng regime |
| R1-19 | Continuous jump model (CJM) *(đã có trong tài liệu lab)* | OHLC | online, có trễ | B | 4 | cân nhắc | bằng chứng regime, bộ phân loại |
| R1-20 | Wasserstein k-means phân cụm regime theo phân phối | OHLC | hậu kiểm | A | 4 | cân nhắc | nhãn tham chiếu, bằng chứng regime, đặc trưng |
| R1-21 | Regime theo đường đi: MMD với signature kernel (Issa & Horvath) | OHLC | online, có trễ | B | 2 | để sau | nhãn tham chiếu |
| R1-22 | Phân cụm GMM / k-means trên đặc trưng return–vol (không có động học Markov) | OHLC | online | B | 3 | cân nhắc | baseline |
| R1-23 | Threshold AR (TAR / SETAR / band-TAR) | OHLC | online | A | 4 | cân nhắc | bộ phân loại, bằng chứng regime |
| R1-24 | Smooth transition AR (STAR: LSTAR / ESTAR) | OHLC | online | A | 3 | để sau | đặc trưng, bằng chứng regime |
| R1-25 | Local linear trend + Kalman filter (độ dốc xu hướng có khoảng tin cậy) | OHLC | online | B | 4 | thử sớm | bộ phân loại, baseline, đặc trưng |
| R1-26 | Bayesian dynamic linear model với hệ số chiết khấu (West–Harrison) | OHLC | online | B | 3 | để sau | đặc trưng, bằng chứng regime |
| R1-27 | State-space có Markov switching (Kim filter) | OHLC | online | B | 3 | để sau | bộ phân loại, bằng chứng regime |
| R1-28 | Stochastic volatility Markov-switching + particle filter | OHLC | online | A | 2 | bỏ qua | đặc trưng |
| R1-29 | HAR-RV và regime theo realized volatility | OHLC | online | A | 4 | thử sớm | đặc trưng, bằng chứng regime, baseline |
| R1-30 | Chỉ số turbulence (Kritzman–Li, khoảng cách Mahalanobis) | nhieu_tai_san | online | A | 4 | cân nhắc | đặc trưng, bằng chứng regime |
| R1-31 | Mô hình bull/bear 4 trạng thái (Maheu–McCurdy–Song) *(đã có trong tài liệu lab)* | OHLC | online | A | 4 | cân nhắc | bằng chứng regime, bộ phân loại |
| R1-32 | Hierarchical HMM hai tầng (Oelschläger–Adam) | OHLC | online, có trễ | A | 3 | cân nhắc | bằng chứng regime, bộ phân loại |
| R1-33 | HMM trên chỉ báo directional change (Chen–Tsang) *(đã có trong tài liệu lab)* | OHLC | online, có trễ | C | 4 | cân nhắc | bằng chứng regime, đặc trưng |

### R2 — Phát hiện điểm đổi (change-point) & ngắt cấu trúc (36 mục)

Nhóm tách thành hai họ. Họ thứ nhất là detector tuần tự online, có lý thuyết về ARL0 và độ trễ: CUSUM, Page–Hinkley, Shiryaev–Roberts, GLR/FOCuS, BOCPD, ADWIN, monitoring kiểu Chu–Stinchcombe–White, MOSUM (trễ cố định G nến) và BSADF. Họ thứ hai là phân đoạn offline (PELT, BS/WBS/SeedBS/NOT/SMUCE, Bai–Perron, ICSS, KCPA, e-divisive), chỉ hợp làm nhãn tham chiếu hậu kiểm. Có ba điều đáng chú ý nhất. (1) Trên TCPDBench, cấu hình mặc định không thắng có ý nghĩa baseline «không có điểm đổi», nên mọi detector phải so với baseline zero và với báo động ngẫu nhiên cùng tần suất. (2) Các kiểm định biến động kinh điển bị méo size nặng khi đuôi dày và biến động dai dẳng: ICSS gốc (theo Sansó et al.) và CUSUM trên \|r\| 5 phút thô (theo Andreou–Ghysels). Vì vậy phải khử mùa vụ trong ngày, dùng ước lượng biến động gộp hoặc bản hiệu chỉnh κ trước khi tin vào một «regime». (3) Hầu như không tìm được kiểm định độc lập nào của các detector này trên FX/vàng intraday. Bằng chứng tài chính chủ yếu là dữ liệu ngày/tháng (CNY, S&P 500, tỷ giá G10). Lưu ý quy trình: hạn mức WebSearch dùng chung đã hết giữa chừng; các mục sau đó chỉ dựa trên trang đã mở bằng WebFetch.

Đề xuất: thử sớm 8, cân nhắc 12, để sau 11, bỏ qua 5.

| Mã | Phương pháp | Dữ liệu | Nhân quả | Tin cậy | Phù hợp | Đề xuất | Vai trò |
|---|---|---|---|---|---:|---|---|
| R2-01 | CUSUM (Page) | OHLC | online | A | 4 | thử sớm | bằng chứng regime, đặc trưng, baseline |
| R2-02 | Page–Hinkley test | OHLC | online | B | 4 | thử sớm | baseline, bằng chứng regime, đặc trưng |
| R2-03 | Shiryaev–Roberts (SR) procedure | OHLC | online | A | 3 | cân nhắc | bằng chứng regime, đặc trưng |
| R2-04 | GLR CUSUM (độ lớn thay đổi chưa biết) | OHLC | online | A | 4 | cân nhắc | bằng chứng regime, đặc trưng |
| R2-05 | SPRT (Wald sequential probability ratio test) | OHLC | online | B | 2 | bỏ qua | đặc trưng |
| R2-06 | FOCuS (Functional Online CuSUM) | OHLC | online | A | 4 | cân nhắc | bằng chứng regime, đặc trưng |
| R2-07 | BOCPD (Adams–MacKay) *(đã có trong tài liệu lab)* | OHLC | online | A | 4 | thử sớm | bằng chứng regime, bộ phân loại, đặc trưng |
| R2-08 | BOCPD với mô hình Student-t và hazard học được | OHLC | online | A | 4 | thử sớm | bằng chứng regime, bộ phân loại, đặc trưng, nhãn tham chiếu |
| R2-09 | Robust BOCPD (β-divergence) và BOCPD-MS | OHLC | online | A | 3 | để sau | bằng chứng regime, đặc trưng |
| R2-10 | BOCPD score-driven / tự hồi quy (Tsaknaki–Lillo–Mazzarisi) | OHLC | online | B | 3 | để sau | bằng chứng regime, đặc trưng |
| R2-11 | ADWIN (Adaptive Windowing) | OHLC | online | A | 4 | cân nhắc | baseline, bằng chứng regime |
| R2-12 | Giám sát ngắt cấu trúc (Chu–Stinchcombe–White; generalized fluctuation monitoring) | OHLC | online | A | 4 | cân nhắc | bằng chứng regime, đặc trưng |
| R2-13 | Andrews end-of-sample instability test | OHLC | online | A | 3 | để sau | bằng chứng regime, đặc trưng |
| R2-14 | PELT (Pruned Exact Linear Time) + CROPS | OHLC | hậu kiểm | A | 3 | thử sớm | nhãn tham chiếu, đánh giá |
| R2-15 | Binary Segmentation | OHLC | hậu kiểm | A | 3 | cân nhắc | nhãn tham chiếu, baseline |
| R2-16 | Wild Binary Segmentation (WBS) | OHLC | hậu kiểm | A | 3 | để sau | nhãn tham chiếu |
| R2-17 | Seeded Binary Segmentation | OHLC | hậu kiểm | A | 3 | để sau | nhãn tham chiếu |
| R2-18 | Narrowest-Over-Threshold (NOT) | OHLC | hậu kiểm | A | 3 | cân nhắc | nhãn tham chiếu |
| R2-19 | SMUCE (Simultaneous MUltiscale Change-point Estimator) | OHLC | hậu kiểm | B | 3 | để sau | nhãn tham chiếu |
| R2-20 | MOSUM (Moving Sum) change-point procedure | OHLC | online, có trễ | A | 4 | thử sớm | bằng chứng regime, đặc trưng, nhãn tham chiếu |
| R2-21 | Bai–Perron (nhiều điểm gãy trong hồi quy tuyến tính) | OHLC | hậu kiểm | A | 3 | cân nhắc | nhãn tham chiếu, đánh giá |
| R2-22 | Chow test và Quandt–Andrews sup-F | OHLC | hậu kiểm | A | 2 | bỏ qua | đánh giá |
| R2-23 | Zivot–Andrews (nghiệm đơn vị có một điểm gãy nội sinh) | OHLC | hậu kiểm | B | 2 | bỏ qua | đánh giá |
| R2-24 | ICSS (Inclán–Tiao) và bản hiệu chỉnh κ1/κ2 (Sansó–Aragó–Carrion) | OHLC | hậu kiểm | A | 3 | cân nhắc | nhãn tham chiếu, đánh giá |
| R2-25 | CUSUM cho động lực biến động trên ước lượng tần số cao (Kokoszka–Leipus; Andreou–Ghysels) | OHLC | hậu kiểm | B | 3 | cân nhắc | nhãn tham chiếu, đặc trưng, đánh giá |
| R2-26 | Kernel change-point (KCPA; Harchaoui–Cappé, Arlot–Celisse–Harchaoui) | OHLC+tick_volume | hậu kiểm | A | 3 | cân nhắc | nhãn tham chiếu |
| R2-27 | E-divisive / E-agglo (Matteson–James, gói ecp) | OHLC+tick_volume | hậu kiểm | A | 3 | để sau | nhãn tham chiếu |
| R2-28 | Scan B-statistic (kernel MMD online) | OHLC+tick_volume | online | A | 3 | để sau | bằng chứng regime, đặc trưng |
| R2-29 | NEWMA (No-prior-knowledge EWMA) | OHLC+tick_volume | online | B | 3 | để sau | đặc trưng |
| R2-30 | Bayesian Blocks (Scargle) | OHLC+tick_volume | hậu kiểm | A | 3 | để sau | nhãn tham chiếu, đặc trưng |
| R2-31 | FLUSS / FLOSS (matrix profile semantic segmentation) | OHLC | online, có trễ | A | 2 | để sau | đặc trưng |
| R2-32 | SADF / GSADF / BSADF (Phillips–Wu–Yu; Phillips–Shi–Yu) — phát hiện chế độ bùng nổ | OHLC | online, có trễ | A | 3 | cân nhắc | bằng chứng regime, đặc trưng |
| R2-33 | ChangeFinder (SDAR hai tầng) | OHLC | online | C | 2 | bỏ qua | đặc trưng |
| R2-34 | KL-CPD (kernel học sâu cho change-point) | OHLC+tick_volume | online, có trễ | A | 2 | bỏ qua | đặc trưng |
| R2-35 | TCPDBench và phép chấm F1 (biên M) / covering *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | B | 4 | thử sớm | đánh giá |
| R2-36 | Khung đo detector online: ARL0, ARL1/độ trễ (SADD, CADD), xác suất báo giả trong cửa sổ | OHLC | online | A | 5 | thử sớm | đánh giá |

### R3 — Chỉ số xu hướng / đi ngang / hiệu quả giá / biến động (trend–range metrics) (35 mục)

Gần như mọi chỉ báo kỹ thuật tách trend/range (ADX, CHOP, VHF, Aroon, Vortex, PFE, Supertrend, Ehlers, MMI, squeeze, NR7) không có kiểm định peer-review nào; ngưỡng của chúng là quy ước. Phần có nền thống kê thật là: variance ratio / tự tương quan (có phân phối dưới giả thuyết bước ngẫu nhiên), bộ ước lượng biến động OHLC, chuẩn hoá mùa vụ trong ngày, HAR-RV, và tín hiệu TSMOM/MA (bằng chứng mạnh ở khung tháng, yếu dần ở ngắn hạn; FX: lợi nhuận luật MA biến mất từ đầu 1990s; preprint 2026 thấy trend ngắn hạn suy sụp sau 2009 ở hợp đồng tick nhỏ). Điều đáng chú ý nhất cho M15: mùa vụ biến động trong ngày (phiên Á/London/NY) chi phối mọi chỉ số dựa trên range/biến động và cả Hurst cục bộ, và nhiễu báo giá tạo tự tương quan âm ở lag ngắn — nên phải khử mùa vụ trước, và hiệu chỉnh ngưỡng bằng phân phối null mô phỏng (bước ngẫu nhiên cùng biến động) trên đoạn phát triển thay vì dùng ngưỡng quy ước. Hạn chế: hạn mức WebSearch của phiên đã hết giữa chừng nên một số mục (TTM Squeeze, Choppiness gốc, Trend Intensity Index) không mở được nguồn gốc; TII bị loại khỏi danh mục vì không có nguồn đã mở.

Đề xuất: thử sớm 11, cân nhắc 7, để sau 10, bỏ qua 7.

| Mã | Phương pháp | Dữ liệu | Nhân quả | Tin cậy | Phù hợp | Đề xuất | Vai trò |
|---|---|---|---|---|---:|---|---|
| R3-01 | ADX / DMI (Average Directional Index) *(đã có trong tài liệu lab)* | OHLC | online, có trễ | C | 4 | thử sớm | baseline, đặc trưng |
| R3-02 | Choppiness Index *(đã có trong tài liệu lab)* | OHLC | online, có trễ | C | 4 | cân nhắc | đặc trưng, baseline |
| R3-03 | Kaufman Efficiency Ratio *(đã có trong tài liệu lab)* | OHLC | online, có trễ | C | 4 | thử sớm | baseline, đặc trưng |
| R3-04 | Vertical Horizontal Filter | OHLC | online, có trễ | C | 4 | cân nhắc | đặc trưng |
| R3-05 | Polarized Fractal Efficiency | OHLC | online, có trễ | C | 3 | bỏ qua | đặc trưng |
| R3-06 | Aroon / Aroon Oscillator | OHLC | online | C | 4 | để sau | đặc trưng |
| R3-07 | Vortex Indicator | OHLC | online, có trễ | C | 4 | bỏ qua | đặc trưng |
| R3-08 | Hồi quy tuyến tính cuốn chiếu: độ dốc, R², t-stat | OHLC | online, có trễ | B | 4 | thử sớm | đặc trưng, baseline, nhãn tham chiếu |
| R3-09 | Kiểm định Mann–Kendall cuốn chiếu (+ Sen slope, hiệu chỉnh Hamed–Rao) | OHLC | online, có trễ | B | 4 | cân nhắc | đặc trưng |
| R3-10 | Độ dốc Kalman (local linear trend / unobserved components) | OHLC | online | B | 4 | thử sớm | đặc trưng, bằng chứng regime, baseline |
| R3-11 | Hurst R/S (cổ điển, hiệu chỉnh Anis–Lloyd–Peters, Lo modified R/S) *(đã có trong tài liệu lab)* | OHLC | online, có trễ | A | 3 | để sau | đặc trưng, đánh giá |
| R3-12 | Hurst theo DFA (Detrended Fluctuation Analysis) | OHLC | online, có trễ | A | 3 | để sau | đặc trưng |
| R3-13 | Variance ratio (Lo–MacKinlay, Chow–Denning, wild bootstrap) *(đã có trong tài liệu lab)* | OHLC | online, có trễ | B | 4 | thử sớm | bằng chứng regime, đặc trưng, đánh giá |
| R3-14 | Tự tương quan cuốn chiếu / Ljung–Box | OHLC | online, có trễ | B | 4 | cân nhắc | đặc trưng, bằng chứng regime |
| R3-15 | Market Meanness Index | OHLC | online, có trễ | C | 3 | bỏ qua | đặc trưng |
| R3-16 | Fractal dimension (Higuchi, Katz, Sevcik, madogram) và FRAMA | OHLC | online, có trễ | B | 3 | để sau | đặc trưng |
| R3-17 | Permutation entropy (và forbidden patterns) | OHLC | online, có trễ | A | 3 | để sau | đặc trưng |
| R3-18 | Sample entropy / Approximate entropy | OHLC | online, có trễ | B | 3 | để sau | đặc trưng |
| R3-19 | Ehlers Hilbert Transform — Trend vs Cycle Mode (MESA/MAMA, HT_DCPERIOD) | OHLC | online, có trễ | B | 3 | để sau | đặc trưng, baseline |
| R3-20 | Ehlers SuperSmoother / Cyber Cycle / Even Better Sinewave | OHLC | online | C | 3 | bỏ qua | đặc trưng |
| R3-21 | L1 trend filtering (Kim–Koh–Boyd–Gorinevsky) | OHLC | hậu kiểm | B | 3 | cân nhắc | nhãn tham chiếu, đánh giá |
| R3-22 | HP filter một phía và bộ lọc hồi quy Hamilton | OHLC | online, có trễ | B | 3 | bỏ qua | đặc trưng |
| R3-23 | Wavelet cho xu hướng (à trous Haar nhân quả, MODWT) | OHLC | online, có trễ | B | 3 | để sau | đặc trưng |
| R3-24 | EMD / Hilbert–Huang Transform cho xu hướng | OHLC | hậu kiểm | B | 2 | bỏ qua | nhãn tham chiếu |
| R3-25 | Bộ ước lượng biến động OHLC (Parkinson, Garman–Klass, Rogers–Satchell, Yang–Zhang) | OHLC | online | A | 5 | thử sớm | đặc trưng, bằng chứng regime, đánh giá |
| R3-26 | Chuẩn hoá mùa vụ biến động trong ngày (intraday periodicity) | OHLC | online | A | 5 | thử sớm | đặc trưng, đánh giá |
| R3-27 | Tỷ lệ biến động ngắn/dài làm chỉ báo nén → bung | OHLC | online | B | 4 | thử sớm | bằng chứng regime, đặc trưng, bộ phân loại |
| R3-28 | HAR-RV (biến động thực hiện, dự báo đa thang) | OHLC | online | B | 4 | thử sớm | baseline, đánh giá |
| R3-29 | Bollinger BandWidth / Keltner squeeze / TTM Squeeze | OHLC | online, có trễ | C | 4 | cân nhắc | đặc trưng |
| R3-30 | NR4 / NR7 / inside bar (nến nén biến động) | OHLC | online | C | 3 | để sau | đặc trưng |
| R3-31 | Time-series momentum (dấu return k kỳ, chuẩn hoá biến động) | OHLC | online | B | 4 | thử sớm | baseline, đặc trưng, bằng chứng regime |
| R3-32 | MA crossover / độ dốc MA chuẩn hoá ATR | OHLC | online, có trễ | B | 4 | cân nhắc | baseline, đặc trưng |
| R3-33 | Độ rộng Donchian / ATR *(đã có trong tài liệu lab)* | OHLC | online, có trễ | C | 4 | thử sớm | baseline, đặc trưng |
| R3-34 | Supertrend | OHLC | online | C | 4 | để sau | đặc trưng, baseline |
| R3-35 | Ichimoku Kinko Hyo (mây Ichimoku) | OHLC | online, có trễ | B | 3 | bỏ qua | đặc trưng |

### R4 — Vi cấu trúc thị trường, thanh khoản, biến động nhảy, mùa vụ phiên — suy từ OHLC (+tick volume) (38 mục)

Nhóm này chia hai nửa rõ rệt. Nửa dùng được ngay chỉ cần nến M1 mà lab đã có: realized variance/range, kiểm định nhảy Lee–Mykland (nhân quả, có bằng chứng FX), mùa vụ trong ngày FFF/WSD, và lịch phiên/tin/fixing. Các thứ này nên thành lớp chuẩn hoá và cờ «bất thường» cho tầng regime. Nửa còn lại dựa trên volume/dấu lệnh (VPIN, BVC, Kyle lambda, OFI, volume profile) thì yếu với tick volume: tick volume FX chỉ khớp tốt volume thật ở mức hồ sơ theo giờ (r≈0.96–0.99, nguồn nhà bán), còn ở tần số cao Fed IFDP 903 nói chỉ «loosely related». Điều đáng chú ý nhất: OHLC của HistData là giá Bid (và MT5 thường cũng vậy), nên các bộ ước lượng spread (Roll/CS/AR/EDGE) trên dữ liệu này đo nhiễu của quote chứ không phải spread. Cần đối chiếu với cột «spread» của MT5, cột mà loader hiện đang bỏ.

Đề xuất: thử sớm 14, cân nhắc 9, để sau 7, bỏ qua 8.

| Mã | Phương pháp | Dữ liệu | Nhân quả | Tin cậy | Phù hợp | Đề xuất | Vai trò |
|---|---|---|---|---|---:|---|---|
| R4-01 | Roll (1984) implied spread | OHLC | online, có trễ | A | 2 | bỏ qua | đặc trưng, đánh giá |
| R4-02 | Corwin–Schultz high-low spread estimator | OHLC | online, có trễ | A | 3 | cân nhắc | đặc trưng, đánh giá |
| R4-03 | Abdi–Ranaldo CHL spread estimator | OHLC | online, có trễ | A | 3 | để sau | đặc trưng |
| R4-04 | EDGE — efficient OHLC spread estimator (Ardia–Guidotti–Kroencke) | OHLC | online, có trễ | A | 3 | cân nhắc | đặc trưng, đánh giá |
| R4-05 | Hasbrouck Gibbs sampler (Bayesian Roll) | OHLC | online, có trễ | A | 2 | bỏ qua | đặc trưng |
| R4-06 | Chỉ số thanh khoản FX tổng hợp kiểu KRS (PCA của Volatility, CS, Gibbs) | OHLC | online, có trễ | A | 3 | để sau | đặc trưng, bằng chứng regime |
| R4-07 | Amihud illiquidity với tick volume (quote frequency) | OHLC+tick_volume | online | A | 4 | thử sớm | đặc trưng, bằng chứng regime |
| R4-08 | Kyle lambda proxy từ nến | OHLC+tick_volume | online, có trễ | B | 2 | bỏ qua | đặc trưng |
| R4-09 | Cột spread của MT5 + kiểm định chất lượng dữ liệu quanh rollover, cuối tuần, ngày lễ | OHLC+tick_volume | online | B | 5 | thử sớm | đánh giá, bằng chứng regime, nhãn tham chiếu |
| R4-10 | Realized variance từ M1 (RV) | OHLC | online | A | 5 | thử sớm | đặc trưng, bằng chứng regime, baseline |
| R4-11 | Realized range (Martens–van Dijk; Christensen–Podolskij) | OHLC | online | A | 4 | thử sớm | đặc trưng, baseline |
| R4-12 | Volatility signature plot + RV kháng nhiễu (TSRV, realized kernel) | OHLC | hậu kiểm | A | 4 | thử sớm | đánh giá |
| R4-13 | Bipower variation + kiểm định nhảy BNS (theo ngày) | OHLC | online, có trễ | A | 4 | thử sớm | nhãn tham chiếu, đặc trưng |
| R4-14 | Kiểm định nhảy intraday Lee–Mykland | OHLC | online | A | 5 | thử sớm | bằng chứng regime, đặc trưng, nhãn tham chiếu |
| R4-15 | Ước lượng biến động kháng nhảy MedRV/MinRV và phát hiện nhảy ABD | OHLC | online, có trễ | A | 4 | cân nhắc | đặc trưng |
| R4-16 | Kiểm định nhảy Aït-Sahalia–Jacod (hai thang lấy mẫu) | OHLC | online, có trễ | B | 3 | để sau | nhãn tham chiếu |
| R4-17 | Tách thành phần liên tục/nhảy (HAR-RV-CJ) và liên kết nhảy–tin | OHLC | online, có trễ | A | 3 | để sau | đặc trưng, bằng chứng regime |
| R4-18 | Mùa vụ biến động trong ngày — Flexible Fourier Form (Andersen–Bollerslev) và chuẩn hoá theo giờ | OHLC | online | A | 5 | thử sớm | đặc trưng, baseline, bằng chứng regime |
| R4-19 | Ước lượng mùa vụ kháng nhảy (Boudt–Croux–Laurent WSD/TML) | OHLC | online | A | 4 | thử sớm | đặc trưng, bằng chứng regime |
| R4-20 | Mô hình địa lý mùa vụ FX và thời gian θ (Dacorogna et al., Olsen) | OHLC | online | C | 3 | bỏ qua | đặc trưng |
| R4-21 | Phân phiên Asia/London/New York và chồng phiên (hoạt động, biến động, khám phá giá vàng) | OHLC | online | A | 4 | thử sớm | đặc trưng, bằng chứng regime, đánh giá |
| R4-22 | Mẫu hình lợi suất theo giờ địa phương (Breedon–Ranaldo) | OHLC | online | A | 3 | cân nhắc | baseline, đánh giá |
| R4-23 | Cửa sổ tin vĩ mô (NFP, CPI, FOMC…) — cờ sự kiện và phản ứng giá | OHLC | online | A | 4 | thử sớm | bằng chứng regime, nhãn tham chiếu, đánh giá |
| R4-24 | Hiệu ứng giờ fixing (WM/R 16:00 London, Tokyo 9:55, LBMA gold) | OHLC | online | A | 4 | cân nhắc | đặc trưng, đánh giá |
| R4-25 | Kiểm tra tính hợp lệ của tick volume như proxy volume thật | OHLC+tick_volume | hậu kiểm | B | 3 | cân nhắc | đánh giá |
| R4-26 | Tick volume tương đối theo giờ trong ngày (RVOL) và đột biến hoạt động | OHLC+tick_volume | online | B | 4 | thử sớm | đặc trưng, bằng chứng regime |
| R4-27 | Đồng hồ giao dịch / business time theo tick (Ané–Geman) | OHLC+tick_volume | online | A | 3 | để sau | đặc trưng |
| R4-28 | Hiệu ứng số tròn / psychological barriers và price clustering | OHLC | online | A | 4 | thử sớm | đặc trưng, đánh giá |
| R4-29 | Osler: tụ lệnh stop-loss/take-profit và price cascades *(đã có trong tài liệu lab)* | OHLC | online | A | 4 | thử sớm | bằng chứng regime, đánh giá |
| R4-30 | Xác suất bật tại hỗ trợ/kháng cự (Chung–Bellotti) *(đã có trong tài liệu lab)* | OHLC | online | B | 3 | cân nhắc | đặc trưng, đánh giá |
| R4-31 | Stop-hunt / liquidity sweep đo định lượng *(đã có trong tài liệu lab)* | OHLC | online | B | 3 | cân nhắc | nhãn tham chiếu, đánh giá |
| R4-32 | Volume profile / value area / POC từ tick volume | OHLC+tick_volume | online | C | 2 | để sau | đặc trưng |
| R4-33 | VWAP trong ngày / anchored VWAP (trọng số tick volume) | OHLC+tick_volume | online | C | 3 | để sau | đặc trưng |
| R4-34 | Bulk Volume Classification (BVC) với tick volume | OHLC+tick_volume | online | A | 2 | bỏ qua | đặc trưng |
| R4-35 | VPIN (volume-synchronized probability of informed trading) | OHLC+tick_volume | online, có trễ | A | 2 | bỏ qua | đặc trưng |
| R4-36 | Tick rule / Lee–Ready (phân loại từng giao dịch) | tick_L1 | online | A | 2 | bỏ qua | đặc trưng |
| R4-37 | Order Flow Imbalance (Cont–Kukanov–Stoikov) | tick_L1 | online | A | 2 | bỏ qua | đặc trưng |
| R4-38 | Đặc trưng liên thị trường cho vàng: USD (DXY/EURUSD) và lợi suất thực | nhieu_tai_san | online, có trễ | B | 3 | cân nhắc | đặc trưng, bằng chứng regime |

### R5 — Nhận dạng cấu trúc giá & mẫu hình định lượng (thay thế / bổ sung cho cách đọc ICT) (30 mục)

Phần lớn nhóm này là cách ĐỊNH NGHĨA / BIỂU DIỄN cấu trúc (DC, zigzag, pivot, PIP, SAX, matrix profile, P&F, Renko), không phải bằng chứng dự báo. Khi có null nghiêm túc (bootstrap OHLC, random walk, SPA), mẫu nến, P&F, Fibonacci đều không vượt chuẩn ngẫu nhiên. H&S có lợi nhuận nhưng bị luật đơn giản lấn át (Chang–Osler FX). Điều đáng chú ý nhất cho lab: nhiều «quy luật» DC chính là tính chất của random walk. Overshoot trung bình ≈ ngưỡng θ cũng đúng với Gaussian random walk (Glattfelder 2011). Tỷ lệ nowcast đúng 66,6% / 59,8% của Tsang 2024 trùng với xác suất gambler's ruin dưới RW (≈68% / 61%, agent tự tính). Pagan–Sossounov cũng cho thấy RW tái tạo được đặc trưng bull/bear. Vì vậy mọi thống kê swing/DC của lab phải so với mô phỏng RW / bootstrap. Đổi lại, null phân tích này cho một định nghĩa Trend/Range nhân quả trên DC: OS/θ trượt > 1 hay < 1, có thể sửa lỗi «Range gần như không xuất hiện». Bằng chứng dương tính đáng chú ý nhất là S/R tự động trên EURUSD M1 2018 (HistData, cùng nguồn với lab): xác suất bật tăng theo số lần chạm và vượt null xáo trộn (Chung–Bellotti 2021, preprint). Wyckoff, Elliott, harmonic không có kiểm định peer-review. Ngân sách WebSearch chung hết giữa chừng, nên các mục harmonic, Wyckoff, floor pivots, Market Profile, Renko/HA, Elliott dựa trên ít nguồn (chủ yếu Wikipedia và tài liệu kỹ thuật).

Đề xuất: thử sớm 3, cân nhắc 13, để sau 6, bỏ qua 8.

| Mã | Phương pháp | Dữ liệu | Nhân quả | Tin cậy | Phù hợp | Đề xuất | Vai trò |
|---|---|---|---|---|---:|---|---|
| R5-01 | Directional change (DC) & intrinsic time *(đã có trong tài liệu lab)* | OHLC | online, có trễ | A | 4 | cân nhắc | bằng chứng regime, nhãn tham chiếu, đặc trưng |
| R5-02 | Luật tỷ lệ DC & tỷ số overshoot/θ (null random walk có sẵn) *(đã có trong tài liệu lab)* | OHLC | online, có trễ | A | 4 | thử sớm | bằng chứng regime, đặc trưng, baseline |
| R5-03 | Bộ chỉ số DC (NDC, TMV/aTMV, T, R, coastline, BM) & DC nowcasting | OHLC | online | B | 4 | thử sớm | đặc trưng, bằng chứng regime, đánh giá |
| R5-04 | Zigzag & thống kê swing (độ dài, thời gian, tỷ lệ retracement) *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | C | 3 | cân nhắc | nhãn tham chiếu, đánh giá |
| R5-05 | Fibonacci retracement (38,2 / 50 / 61,8%) — các kiểm định | OHLC | online, có trễ | C | 2 | để sau | đánh giá |
| R5-06 | Pivot n-nến / Fractal Bill Williams *(đã có trong tài liệu lab)* | OHLC | online, có trễ | B | 4 | cân nhắc | đặc trưng, nhãn tham chiếu |
| R5-07 | Phân cấp swing ngắn / trung / dài hạn (Larry Williams STH/ITH/LTH) *(đã có trong tài liệu lab)* | OHLC | online, có trễ | C | 3 | cân nhắc | đặc trưng, nhãn tham chiếu |
| R5-08 | Định ngày chu kỳ Bry–Boschan / Pagan–Sossounov / Lunde–Timmermann *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | A | 3 | cân nhắc | nhãn tham chiếu, đánh giá |
| R5-09 | Nhận dạng mẫu hình bằng hồi quy kernel (Lo–Mamaysky–Wang) *(đã có trong tài liệu lab)* | OHLC | online, có trễ | A | 3 | cân nhắc | đánh giá, đặc trưng |
| R5-10 | Kiểm lại H&S: Savin–Weller–Zvingelis 2007, Chong–Poon 2017 | OHLC | online, có trễ | A | 2 | để sau | đánh giá |
| R5-11 | H&S trên FX với null bootstrap (Osler & Chang 1995; Chang & Osler 1999) | OHLC | online, có trễ | A | 3 | cân nhắc | đánh giá |
| R5-12 | Perceptually Important Points (PIP) *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | B | 3 | để sau | nhãn tham chiếu, đặc trưng |
| R5-13 | Khớp khuôn mẫu (template matching) & Dynamic Time Warping | OHLC | online | B | 2 | để sau | đặc trưng |
| R5-14 | Matrix Profile (motif / discord / FLOSS) — STUMPY | OHLC | online | B | 3 | cân nhắc | đặc trưng, đánh giá |
| R5-15 | SAX — biểu diễn ký hiệu (Symbolic Aggregate approXimation) | OHLC | online | A | 2 | bỏ qua | đặc trưng |
| R5-16 | Mẫu thứ tự (ordinal patterns) & permutation entropy trên chuỗi swing | OHLC | online | B | 3 | cân nhắc | đặc trưng, đánh giá |
| R5-17 | Topological data analysis — persistent homology (Gidea–Katz) | nhieu_tai_san | online, có trễ | B | 2 | bỏ qua | đặc trưng |
| R5-18 | Mẫu nến Nhật (candlestick) — các kiểm định có null | OHLC | online | A | 3 | cân nhắc | đặc trưng, đánh giá |
| R5-19 | Point & Figure | OHLC | online, có trễ | B | 2 | bỏ qua | baseline |
| R5-20 | Renko / Heikin-Ashi / Kagi / Line break | OHLC | online, có trễ | C | 2 | bỏ qua | baseline |
| R5-21 | Market Profile / TPO (Steidlmayer) — value area, POC, balance/imbalance | OHLC | online, có trễ | C | 3 | cân nhắc | đặc trưng, bằng chứng regime |
| R5-22 | Phương pháp Wyckoff (tích luỹ / phân phối, spring, upthrust) | volume_that | hậu kiểm | C | 1 | bỏ qua |  |
| R5-23 | Elliott Wave | OHLC | hậu kiểm | C | 1 | bỏ qua |  |
| R5-24 | Harmonic patterns (Gartley, Bat, Butterfly, Crab) | OHLC | online, có trễ | C | 1 | bỏ qua |  |
| R5-25 | Thanh thông tin (tick / volume / dollar / imbalance / run bars — López de Prado) | tick_L1 | online | B | 2 | để sau | đặc trưng |
| R5-26 | Floor pivots / Camarilla / Woodie | OHLC | online | C | 3 | để sau | baseline, đặc trưng |
| R5-27 | Phát hiện S/R tự động & xác suất bật theo số lần chạm (Chung–Bellotti; Garzarelli) | OHLC | online | B | 4 | thử sớm | đặc trưng, bằng chứng regime, đánh giá |
| R5-28 | Mức S/R công bố bởi ngân hàng trong FX intraday (Osler 2000) *(đã có trong tài liệu lab)* | OHLC | online | A | 2 | bỏ qua | đánh giá |
| R5-29 | Trading range break (Brock–Lakonishok–LeBaron 1992) *(đã có trong tài liệu lab)* | OHLC | online | A | 4 | cân nhắc | baseline |
| R5-30 | Equal highs/lows, double top/bottom & «liquidity pool» đo ngoài ICT | OHLC | online, có trễ | C | 3 | cân nhắc | đặc trưng, đánh giá |

### R6 — Học máy & học biểu diễn cho regime / cấu trúc / nhãn (33 mục)

Phần hợp lab nhất là các kỹ thuật rẻ quanh việc gán nhãn và độ tin: meta-labeling trên các bộ luật sẵn có, trọng số theo uniqueness, purged CV, LightGBM + SHAP, hiệu chỉnh xác suất, conformal và selective classification để ra lớp Uncertain. Nút thắt thật là thiếu nhãn, nên weak supervision + active learning + confident learning đáng làm trước mọi mô hình sâu. Bằng chứng cho mô hình sâu trên dữ liệu tài chính yếu hoặc ngược chiều: trên bộ Exchange-Rate, baseline «Repeat» thắng mọi Transformer; foundation model zero-shot cho R² âm trên lợi suất ngày ở 94 nước; CNN ảnh chart (Jiang–Kelly–Xiu) mạnh nhưng là xếp hạng cắt ngang cổ phiếu, không phải regime chuỗi FX. Lưu ý: công cụ WebSearch hết hạn mức giữa chừng; các mục sau đó được kiểm bằng cách mở trực tiếp URL đã biết (arXiv, tài liệu thư viện).

Đề xuất: thử sớm 13, cân nhắc 8, để sau 11, bỏ qua 1.

| Mã | Phương pháp | Dữ liệu | Nhân quả | Tin cậy | Phù hợp | Đề xuất | Vai trò |
|---|---|---|---|---|---:|---|---|
| R6-01 | Nhãn kỳ hạn cố định (fixed-time-horizon labeling) | OHLC | hậu kiểm | B | 3 | cân nhắc | nhãn tham chiếu, baseline |
| R6-02 | Triple-barrier labeling (kèm lấy mẫu sự kiện bằng CUSUM filter) | OHLC | hậu kiểm | B | 3 | thử sớm | nhãn tham chiếu, đánh giá |
| R6-03 | Trend-scanning labels *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | B | 3 | thử sớm | nhãn tham chiếu |
| R6-04 | Meta-labeling (mô hình thứ cấp đánh giá tín hiệu của mô hình sơ cấp) | OHLC | online | C | 4 | thử sớm | bộ phân loại, bằng chứng regime |
| R6-05 | Trọng số mẫu theo uniqueness + sequential bootstrap | OHLC | hậu kiểm | B | 4 | thử sớm | đánh giá |
| R6-06 | Bộ phân loại cây tổ hợp (Random Forest, LightGBM, XGBoost, CatBoost) cho regime với purged CV | OHLC+tick_volume | online | A | 4 | thử sớm | bộ phân loại, baseline |
| R6-07 | Độ quan trọng đặc trưng MDI / MDA / SFI và clustered feature importance | OHLC | hậu kiểm | B | 4 | cân nhắc | đánh giá, đặc trưng |
| R6-08 | SHAP / TreeSHAP để giữ tính giải thích | OHLC | online | A | 4 | thử sớm | đánh giá, bằng chứng regime |
| R6-09 | Gaussian Mixture Model trên vector đặc trưng (phân cụm regime không giám sát) | OHLC | online | B | 3 | cân nhắc | baseline, đặc trưng |
| R6-10 | Wasserstein k-means (phân cụm phân phối lợi suất theo cửa sổ) | OHLC | online, có trễ | A | 3 | cân nhắc | bằng chứng regime, baseline |
| R6-11 | Phân cụm theo mật độ và phổ (HDBSCAN, spectral clustering) | OHLC | hậu kiểm | B | 3 | để sau | đặc trưng, baseline |
| R6-12 | Phân cụm theo hình dạng chuỗi (TimeSeriesKMeans DTW / soft-DTW, k-Shape) | OHLC | online, có trễ | B | 2 | để sau | đặc trưng |
| R6-13 | Self-Organizing Map (bản đồ Kohonen) cho trạng thái thị trường | OHLC | online | C | 2 | để sau | đặc trưng |
| R6-14 | Autoencoder / VAE nén cửa sổ giá rồi phân cụm | OHLC | online, có trễ | B | 2 | để sau | đặc trưng |
| R6-15 | Mixture-VAE có ràng buộc thời gian cho nhận diện regime (deep generative + statistical jump model) | OHLC | hậu kiểm | B | 2 | để sau | bằng chứng regime |
| R6-16 | Học biểu diễn tự giám sát tương phản (TS2Vec, TNC, TS-TCC, CPC) rồi phân cụm hoặc phân loại tuyến tính | OHLC | online, có trễ | B | 2 | để sau | đặc trưng |
| R6-17 | ROCKET / MiniRocket / MultiROCKET-Hydra (phân loại chuỗi bằng kernel tích chập ngẫu nhiên) | OHLC | online | A | 4 | thử sớm | bộ phân loại, baseline |
| R6-18 | Transformer chuỗi thời gian (PatchTST, TimesNet, iTransformer) cho phân loại/dự báo | OHLC | online | A | 2 | bỏ qua | bộ phân loại |
| R6-19 | CNN trên ảnh chart giá (Jiang–Kelly–Xiu «(Re-)Imag(in)ing Price Trends») | OHLC+tick_volume | online | A | 2 | để sau | đặc trưng |
| R6-20 | Foundation model chuỗi thời gian (Chronos, TimesFM, Moirai, Lag-Llama, MOMENT) làm đặc trưng / dự báo biến động | OHLC | online | B | 3 | cân nhắc | đặc trưng |
| R6-21 | Kronos – foundation model chuyên cho nến K-line (OHLCV) | OHLC+tick_volume | online | B | 2 | để sau | đặc trưng |
| R6-22 | Mô hình chuyển trạng thái nơ-ron (recurrent SLDS, switching nonlinear dynamical systems / deep switching) | OHLC | online, có trễ | B | 2 | để sau | bằng chứng regime |
| R6-23 | Phát hiện điểm đổi bằng mạng nơ-ron (KL-CPD, TS-CP2) | OHLC | online, có trễ | A | 2 | để sau | bằng chứng regime |
| R6-24 | Đặc trưng điểm đổi (GP changepoint) đưa vào mạng LSTM/Transformer (Slow Momentum with Fast Reversion; Momentum Transformer) | OHLC | online | A | 3 | cân nhắc | đặc trưng, bằng chứng regime |
| R6-25 | Weak supervision – gộp nhiều bộ gán nhãn heuristic (Snorkel, Dawid–Skene) *(đã có trong tài liệu lab)* | OHLC | online | A | 4 | thử sớm | nhãn tham chiếu, đánh giá |
| R6-26 | Confident learning – tìm nhãn sai trong bộ nhãn tay / nhãn yếu (cleanlab) | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá, nhãn tham chiếu |
| R6-27 | Active learning để giảm công gán nhãn tay (uncertainty sampling, query-by-committee) | OHLC | hậu kiểm | B | 4 | thử sớm | nhãn tham chiếu |
| R6-28 | Bán giám sát: self-training và label propagation / spreading | OHLC | online | B | 3 | để sau | bộ phân loại |
| R6-29 | Conformal prediction cho phân loại regime (split / Mondrian / APS-RAPS / Adaptive Conformal Inference) *(đã có trong tài liệu lab)* | OHLC | online, có trễ | A | 4 | thử sớm | bộ phân loại, đánh giá |
| R6-30 | Hiệu chỉnh xác suất (Platt / isotonic / temperature scaling / Venn-Abers) | OHLC | online | A | 4 | thử sớm | đánh giá, bộ phân loại |
| R6-31 | Selective classification / reject option (đường risk–coverage) *(đã có trong tài liệu lab)* | OHLC | online | A | 4 | thử sớm | đánh giá, bộ phân loại |
| R6-32 | Phân loại rò rỉ dữ liệu trong khoa học dùng ML (Kapoor & Narayanan) – danh mục kiểm tra | OHLC | hậu kiểm | A | 4 | thử sớm | đánh giá |
| R6-33 | ML dự báo jump intraday trên FX (Uzun, Şensoy, Nguyen 2023) | tick_L1 | online | A | 3 | cân nhắc | đặc trưng, bằng chứng regime |

### R7 — Phương pháp đánh giá, kiểm định thống kê và chống overfit (không dùng P&L là chính) (46 mục)

Công cụ hợp nhất với lab đều không gắn với P&L: block bootstrap theo ngày (arch), null dịch vòng / hoán vị có ràng buộc, kiểm soát FDR (statsmodels), kiểm định Pesaran–Timmermann 2009 cho phụ thuộc giữa nhãn nhiều lớp và kết cục khi có tự tương quan, cùng các phép chấm sự kiện/đoạn có so với chuẩn ngẫu nhiên. Có hai cảnh báo lớn. Một: nhiều thước đo sự kiện bị «lừa» dễ dàng (point-adjust cho điểm cao cả khi điểm số là ngẫu nhiên; range-based bị dự đoán đối nghịch đánh lừa), và baseline «zero» thắng nhiều thuật toán trong TCPD. Hai: null phá vỡ volatility clustering (hoán vị iid, phase-randomized surrogate) quá yếu, nên mọi bộ phân loại tương quan với ATR đều «vượt null». Nhóm công cụ theo Sharpe (DSR, PSR, haircut) chỉ chuyển sang lab qua ý tưởng cực đại kỳ vọng của N lần thử. Ghi chú quy trình: hết ngân sách WebSearch giữa chừng, nên các nguồn sau đó được mở bằng URL trực tiếp (arXiv, IDEAS/RePEc, tài liệu thư viện).

Đề xuất: thử sớm 23, cân nhắc 17, để sau 4, bỏ qua 2.

| Mã | Phương pháp | Dữ liệu | Nhân quả | Tin cậy | Phù hợp | Đề xuất | Vai trò |
|---|---|---|---|---|---:|---|---|
| R7-01 | Purged k-fold cross-validation + embargo *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | B | 4 | thử sớm | đánh giá |
| R7-02 | Combinatorial Purged Cross-Validation (CPCV) | OHLC | hậu kiểm | B | 3 | để sau | đánh giá |
| R7-03 | Walk-forward: cửa sổ mở rộng (anchored) và cửa sổ trượt (rolling-origin) | OHLC | hậu kiểm | A | 4 | thử sớm | đánh giá |
| R7-04 | Kiểm thử bất biến tiền tố (prefix/truncation invariance) và nhiễu tương lai | OHLC | hậu kiểm | B | 5 | thử sớm | đánh giá |
| R7-05 | Đăng ký trước kế hoạch phân tích (pre-registration) + sổ đăng ký mọi lần thử + đối chứng dương | OHLC | hậu kiểm | B | 5 | thử sớm | đánh giá |
| R7-06 | Probability of Backtest Overfitting (PBO) bằng CSCV *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | A | 4 | thử sớm | đánh giá |
| R7-07 | Deflated Sharpe Ratio và cực đại kỳ vọng sau N lần thử (False Strategy Theorem) | OHLC | hậu kiểm | A | 3 | cân nhắc | đánh giá |
| R7-08 | Probabilistic Sharpe Ratio (PSR) và Minimum Track Record Length | OHLC | hậu kiểm | B | 2 | bỏ qua | đánh giá |
| R7-09 | Ngưỡng Harvey–Liu–Zhu «t > 3» và haircut theo multiple testing | OHLC | hậu kiểm | A | 3 | cân nhắc | đánh giá |
| R7-10 | White's Reality Check for data snooping *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá |
| R7-11 | Hansen Test for Superior Predictive Ability (SPA) | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá |
| R7-12 | Romano–Wolf StepM (stepwise multiple testing) | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá |
| R7-13 | Model Confidence Set (Hansen–Lunde–Nason) | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá |
| R7-14 | Kiểm soát FDR Benjamini–Hochberg | OHLC | hậu kiểm | A | 5 | thử sớm | đánh giá |
| R7-15 | Kiểm soát FDR Benjamini–Yekutieli (mọi cấu trúc phụ thuộc) | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá |
| R7-16 | Stationary bootstrap (Politis–Romano) *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | A | 5 | thử sớm | đánh giá |
| R7-17 | Circular / moving block bootstrap, khối theo ngày hoặc tuần | OHLC | hậu kiểm | A | 5 | thử sớm | đánh giá |
| R7-18 | Chọn độ dài khối tự động Politis–White (có bản sửa 2009) | OHLC | hậu kiểm | A | 5 | thử sớm | đánh giá |
| R7-19 | Kiểm định hoán vị / ngẫu nhiên hoá cho chuỗi phụ thuộc + p-value chính xác (Phipson–Smyth) | OHLC | hậu kiểm | A | 5 | thử sớm | đánh giá |
| R7-20 | Shift test / circular shift (Harris) *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | B | 5 | thử sớm | đánh giá |
| R7-21 | Surrogate data: phase randomization, AAFT, IAAFT, twin surrogates | OHLC | hậu kiểm | A | 3 | để sau | đánh giá |
| R7-22 | Null mô phỏng (random walk, AR, GARCH, regime-switching) + đối chứng dương có regime cài sẵn | OHLC | hậu kiểm | A | 5 | thử sớm | đánh giá, baseline |
| R7-23 | Diebold–Mariano test (+ hiệu chỉnh Harvey–Leybourne–Newbold) | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá |
| R7-24 | Giacomini–White test of conditional predictive ability | OHLC | hậu kiểm | A | 3 | để sau | đánh giá |
| R7-25 | Pesaran–Timmermann: kiểm định dự báo hướng (1992) và phụ thuộc giữa các biến phân loại có tương quan chuỗi (2009) | OHLC | hậu kiểm | A | 4 | thử sớm | đánh giá |
| R7-26 | Sai số chuẩn HAC (Newey–West) và hiệu chỉnh tầm chồng lấp (Hansen–Hodrick) | OHLC | hậu kiểm | A | 5 | thử sớm | đánh giá |
| R7-27 | So phân phối có điều kiện và không điều kiện (Lo–Mamaysky–Wang): KS, χ² goodness-of-fit *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá |
| R7-28 | Concordance Harding–Pagan và kiểm định đồng bộ chu kỳ (2006) *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá |
| R7-29 | Cỡ mẫu hiệu dụng (ESS) và phân tích lực / hiệu ứng tối thiểu phát hiện được (MDE) cho chuỗi phụ thuộc | OHLC | hậu kiểm | B | 5 | thử sớm | đánh giá |
| R7-30 | Chấm điểm đổi có dung sai (F1 theo margin) và covering metric (TCPD), kèm baseline «zero» *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | B | 5 | thử sớm | đánh giá |
| R7-31 | NAB scoring (Numenta Anomaly Benchmark) | OHLC | hậu kiểm | B | 3 | bỏ qua | đánh giá |
| R7-32 | Precision/Recall theo khoảng (range-based, Tatbul et al.) | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá |
| R7-33 | Bẫy point-adjust (PA) và giao thức PA%K | OHLC | hậu kiểm | A | 4 | thử sớm | đánh giá |
| R7-34 | Affiliation precision/recall (Huet–Navarro–Rossi) | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá |
| R7-35 | Đánh đổi trễ phát hiện và tần suất báo động giả (ARL0 / ARL1, đường delay–false-alarm) | OHLC | hậu kiểm | B | 5 | thử sớm | đánh giá |
| R7-36 | Thước đo theo đoạn: segmental F1@k (IoU), edit score, confusion matrix theo đoạn, macro-F1 | OHLC | hậu kiểm | A | 5 | thử sớm | đánh giá |
| R7-37 | Đồng thuận giữa hai phân hoạch: Adjusted Rand Index, Adjusted Mutual Information, V-measure | OHLC | hậu kiểm | B | 4 | cân nhắc | đánh giá |
| R7-38 | So nhiều thuật toán trên nhiều bộ dữ liệu bằng hạng: Friedman + Wilcoxon–Holm (Demšar) | OHLC | hậu kiểm | B | 4 | cân nhắc | đánh giá |
| R7-39 | McNemar test so hai bộ phân loại trên cùng nhãn (kèm hiệu chỉnh phụ thuộc) | OHLC | hậu kiểm | B | 3 | cân nhắc | đánh giá |
| R7-40 | Cohen's kappa / Fleiss' kappa cho đồng thuận người gán nhãn *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá |
| R7-41 | Krippendorff's alpha | OHLC | hậu kiểm | B | 5 | thử sớm | đánh giá |
| R7-42 | Gwet's AC1 và cặp chỉ số ppos/pneg (khắc phục nghịch lý kappa) | OHLC | hậu kiểm | A | 4 | thử sớm | đánh giá |
| R7-43 | Đường risk–coverage / selective classification (AURC) *(đã có trong tài liệu lab)* | OHLC | hậu kiểm | A | 5 | thử sớm | đánh giá |
| R7-44 | Hiệu chuẩn xác suất: Brier score, reliability diagram, ECE | OHLC | hậu kiểm | A | 4 | cân nhắc | đánh giá |
| R7-45 | Conformal prediction thích ứng (ACI) cho tập dự đoán dưới dịch chuyển phân phối *(đã có trong tài liệu lab)* | OHLC | online | A | 3 | để sau | đánh giá, bộ phân loại |
| R7-46 | Baseline ngây thơ và skill score (zero / persistence / climatology / theo giờ) | OHLC | online | B | 5 | thử sớm | đánh giá, baseline |

### R8 — Chiến lược theo regime cho tầng router (trend-following, pullback, breakout, mean reversion, đứng ngoài) (36 mục)

Bằng chứng sau chi phí mạnh nhất thuộc về trend-following khung tháng/ngày trên nhiều tài sản (TSMOM, channel/MA trên futures, 1880–2016). Ngược lại, luật MA/filter trên FX phát triển đã hết lợi nhuận từ đầu thập niên 1990, và phần lớn tín hiệu intraday OHLCV thất bại sau chi phí: ORB, London/Asian breakout, OU mean reversion trên vàng micro, luật GP intraday FX. Hiệu ứng intraday FX có cơ sở vi cấu trúc (giờ phiên, giờ fix) là có thật nhưng chỉ vài bp, và chỉ dương khi chi phí thấp hơn spread niêm yết. Router theo regime chỉ có bằng chứng sau chi phí ở phân bổ tài sản dữ liệu ngày (jump model, HMM). Không tìm được nghiên cứu peer-review nào cho trend pullback, hay cho router Trend Pullback / Range MR / No Trade ở M5–H1 trên FX/vàng; vì vậy No Trade phải là baseline bắt buộc. Hạn mức WebSearch của phiên hết giữa chừng, nên cặp vàng–bạc, spread lúc rollover và Turtle peer-review chưa tra đủ.

Đề xuất: thử sớm 12, cân nhắc 12, để sau 7, bỏ qua 5.

| Mã | Phương pháp | Dữ liệu | Nhân quả | Tin cậy | Phù hợp | Đề xuất | Vai trò |
|---|---|---|---|---|---:|---|---|
| R8-01 | Time-series momentum (TSMOM) — Moskowitz, Ooi, Pedersen 2012 | OHLC | online | A | 3 | thử sớm | chiến lược router, baseline |
| R8-02 | Trend-following một thế kỷ (Hurst, Ooi, Pedersen 2017) | OHLC | online | A | 4 | thử sớm | chiến lược router, baseline |
| R8-03 | Hai thế kỷ trend-following (Lempérière et al. 2014, CFM) | OHLC | online | B | 3 | cân nhắc | chiến lược router, baseline |
| R8-04 | Phản biện TSMOM: dự báo yếu, hiệu ứng nằm ở vol scaling (Huang et al. 2020; Kim, Tse, Wald 2016) | OHLC | online | A | 3 | thử sớm | baseline |
| R8-05 | Channel / Donchian breakout (Turtle) và dual MA trên futures hàng hoá *(đã có trong tài liệu lab)* | OHLC | online | A | 4 | thử sớm | chiến lược router, baseline |
| R8-06 | Moving-average / filter rule trên FX — lợi nhuận suy giảm (Neely, Weller, Ulrich 2009; Olson 2004) | OHLC | online | A | 1 | cân nhắc | baseline |
| R8-07 | Họ 21,000 luật kỹ thuật FX kiểm bằng stepwise SPA (Hsu, Taylor, Wang 2016; Qi, Wu 2006) | OHLC | online | A | 2 | cân nhắc | baseline |
| R8-08 | Luật kỹ thuật DJIA dưới White's Reality Check (Sullivan, Timmermann, White 1999) *(đã có trong tài liệu lab)* | OHLC | online | A | 1 | bỏ qua | baseline |
| R8-09 | Tổng quan phân tích kỹ thuật trên FX (Menkhoff, Taylor 2007) | OHLC | online | A | 2 | để sau | chiến lược router |
| R8-10 | Luật kỹ thuật intraday FX tìm bằng genetic programming (Neely, Weller 2003) | OHLC | online | A | 1 | bỏ qua | baseline |
| R8-11 | Market intraday momentum (Gao, Han, Li, Zhou 2018; Baltussen, Da, Lammers, Martens 2021) *(đã có trong tài liệu lab)* | OHLC | online | A | 3 | cân nhắc | chiến lược router, đặc trưng |
| R8-12 | Intraday momentum trên FX có giờ giao dịch rõ (Elaut, Frömmel, Lampaert 2018) *(đã có trong tài liệu lab)* | OHLC | online | A | 2 | để sau | đặc trưng |
| R8-13 | Opening range breakout (ORB) *(đã có trong tài liệu lab)* | OHLC | online | B | 2 | cân nhắc | chiến lược router, baseline |
| R8-14 | London breakout / Asian range breakout trên FX | OHLC | online | C | 1 | cân nhắc | baseline |
| R8-15 | Volatility breakout (Larry Williams) | OHLC | online | C | 1 | để sau | baseline |
| R8-16 | RSI(2) mean reversion có bộ lọc trend (Connors, Alvarez) | OHLC | online | C | 2 | cân nhắc | chiến lược router |
| R8-17 | Bollinger Bands — bản trend và bản contrarian (Lento, Gradojevic, Wright 2007) | OHLC | online | B | 2 | cân nhắc | chiến lược router, baseline |
| R8-18 | Mean reversion intraday kiểu OU / z-score trên vàng (MGC) và FX | OHLC | online | B | 1 | cân nhắc | chiến lược router, baseline |
| R8-19 | Đảo chiều quanh giờ fix FX — hình chữ W (Krohn, Mueller, Whelan 2024) | OHLC | online | A | 3 | thử sớm | chiến lược router, đặc trưng |
| R8-20 | Mùa vụ theo giờ phiên FX — đồng tiền yếu trong giờ làm việc nội địa (Ranaldo 2007/2009; Breedon, Ranaldo 2013) | OHLC | online | B | 3 | thử sớm | chiến lược router, baseline, đặc trưng |
| R8-21 | Pairs trading / cointegration (Gatev, Goetzmann, Rouwenhorst 2006; Do, Faff 2010) | nhieu_tai_san | online | A | 2 | để sau | chiến lược router |
| R8-22 | Volatility-managed portfolios (Moreira, Muir 2017) và phản biện ngoài mẫu (Cederburg et al. 2020) | OHLC | online | A | 2 | để sau | chiến lược router |
| R8-23 | Volatility targeting theo lớp tài sản (Harvey et al. 2018, Man AHL) | OHLC | online | B | 3 | thử sớm | chiến lược router |
| R8-24 | FX carry trade (bối cảnh): rủi ro biến động toàn cầu và kết quả ngoài mẫu | nhieu_tai_san | online | A | 1 | bỏ qua | chiến lược router |
| R8-25 | Currency momentum cắt ngang (Menkhoff et al. 2012) | nhieu_tai_san | online | A | 2 | bỏ qua | chiến lược router |
| R8-26 | Phân bổ theo regime Markov-switching (Kritzman, Page, Turkington 2012) *(đã có trong tài liệu lab)* | nhieu_tai_san | online, có trễ | A | 3 | để sau | chiến lược router |
| R8-27 | Phân bổ theo HMM 2 trạng thái ước lượng thích nghi (Nystrup et al.) *(đã có trong tài liệu lab)* | nhieu_tai_san | online, có trễ | B | 4 | cân nhắc | chiến lược router |
| R8-28 | Long/flat theo statistical jump model (Shu, Yu, Mulvey 2024) *(đã có trong tài liệu lab)* | OHLC | online, có trễ | A | 4 | thử sớm | chiến lược router, baseline |
| R8-29 | Chọn tốc độ momentum động theo pha (Garg, Goulding, Harvey, Mazzoleni — Momentum Turning Points) *(đã có trong tài liệu lab)* | OHLC | online | B | 3 | cân nhắc | chiến lược router, bằng chứng regime |
| R8-30 | Momentum crashes và momentum động (Daniel, Moskowitz 2016) *(đã có trong tài liệu lab)* | nhieu_tai_san | online | A | 3 | để sau | chiến lược router, bằng chứng regime |
| R8-31 | Nghiên cứu falsification tín hiệu intraday OHLCV trên MNQ/MGC (Mesfin 2026) *(đã có trong tài liệu lab)* | OHLC+tick_volume | online | B | 3 | thử sớm | chiến lược router, baseline |
| R8-32 | Day trading tuỳ ý của nhà đầu tư cá nhân — bằng chứng nền âm | OHLC | hậu kiểm | A | 1 | bỏ qua | baseline |
| R8-33 | No Trade / abstain như một quyết định của router (baseline + cổng chi phí) *(đã có trong tài liệu lab)* | OHLC | online | B | 4 | thử sớm | chiến lược router, baseline |
| R8-34 | Bộ lọc thời gian: tránh tin vĩ mô, giờ fix và rollover | OHLC | online | A | 3 | thử sớm | chiến lược router, đặc trưng |
| R8-35 | Trend pullback (mua hồi trong xu hướng) *(đã có trong tài liệu lab)* | OHLC | online | C | 2 | thử sớm | chiến lược router |
| R8-36 | Luật trend-following tối ưu trong mô hình hai trạng thái (Zakamulin, Giner 2024) *(đã có trong tài liệu lab)* | OHLC | online | A | 3 | cân nhắc | chiến lược router, bằng chứng regime |
