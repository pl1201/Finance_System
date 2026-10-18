# Học quant qua chính dự án market-structure-lab

Bộ tài liệu này viết riêng cho bạn: người đọc chart theo ICT, đang xây lab nhận diện cấu trúc thị trường, muốn học định lượng
(quant) bằng chính dữ liệu và mã của lab. Mỗi khái niệm đi kèm một câu hỏi thật của dự án, và mọi bài tập chạy trên dữ liệu
XAUUSD / EURUSD của bạn.

Bắt đầu: tháng 10/2026. Giả định: bạn đọc được Python cơ bản (biến, vòng lặp, hàm) và chưa học thống kê bài bản. Nếu module nào quá
dễ hay quá khó, nói để mình chỉnh.

---

## Cách học một module

1. **Đọc ô «Ba điều cần nhớ» ở đầu module** để biết đích đến, rồi phần «Vì sao cần» để biết module trả lời câu hỏi nào của
   dự án. Ôn lại sau này: chỉ cần đọc ô này.
2. **Đọc từng khái niệm**, chạy ngay đoạn code ví dụ bên dưới nó, so với «Kết quả khi mình chạy».
3. **Làm bài tập** ở cuối module. Mỗi bài có gợi ý; tự làm trước rồi mới so.
4. **Trả lời phần tự kiểm.** Đáp án nằm trong ô thu gọn, bấm để mở.
5. Muốn đi sâu: phần «Đọc thêm».

Mỗi module khoảng 5–7 giờ, cả bộ khoảng 50 giờ. Đi theo thứ tự: module sau dùng khái niệm của module trước. Module dài
(750–950 dòng) chủ yếu vì code và kết quả thật; phần chữ cần đọc ít hơn một nửa.

## Chạy code thế nào

Mọi đoạn code dùng Python trong môi trường của lab (`.venv`) và chỉ cần các thư viện đã có: numpy, pandas, scipy, scikit-learn,
hmmlearn. Không cần cài thêm gì.

Cách đơn giản nhất (PowerShell, đứng ở thư mục `market-structure-lab`):

```powershell
.\.venv\Scripts\python.exe
```

Rồi dán từng đoạn code vào. Hoặc lưu đoạn code thành file (vd `bai.py`, để ngoài thư mục lab hoặc trong một thư mục nháp) rồi chạy
`.\.venv\Scripts\python.exe bai.py` — vẫn đứng ở thư mục `market-structure-lab`.

Mọi đoạn code bắt đầu bằng hai dòng nạp module trợ giúp
[`research/hoc_quant/hoc.py`](../../research/hoc_quant/hoc.py):

```python
import sys; sys.path.insert(0, "research/hoc_quant")
from hoc import *
```

Module này cho bạn:

| Hàm / hằng | Làm gì |
|---|---|
| `nap_nen(dataset, tu, den)` | Nến OHLC dạng bảng pandas, index là giờ mở nến (UTC) |
| `chay_thuat_toan(ten, dataset, tu, den)` | Chạy thuật toán của lab (vd `"ict_structure"`), trả bảng sự kiện và timeline |
| `chay_tren_df(ten, df, khung)` | Chạy thuật toán của lab trên nến bạn tự tạo (vd chuỗi mô phỏng) |
| `nen_tu_gia(gia)` | Dựng nến từ một chuỗi giá mô phỏng |
| `danh_sach_dataset()` | Mọi dataset trong database |
| `XAU_M15`, `XAU_M1`, `XAU_H1`, `XAU_D1`, `EUR_M15_DAI`… | Mã các dataset hay dùng |

**An toàn:** database được mở ở chế độ chỉ đọc nên bài tập không sửa được dữ liệu, run hay nhãn của lab. Hàm cũng **từ chối mọi
khoảng chạm từ 01/09/2024 trở đi**: đó là đoạn kiểm tra của lab, phải để dành, không dùng để học hay chọn tham số. Vì sao phải
khoá như vậy là nội dung của module 7.

## Lộ trình

| # | Module | Trả lời câu hỏi nào của dự án | Chỗ trong lab | Giờ |
|---|---|---|---|---:|
| 1 | [Dữ liệu giá](01_du_lieu_gia.md) | Nến của mình thật sự chứa gì? Giờ nào là «một ngày»? Khoảng trống nào là lỗi? | dữ liệu, lịch phiên, gộp khung | ~5 |
| 2 | [Thống kê nền](02_thong_ke_nen.md) | Một con số «58% đúng» có nghĩa gì? Khi nào là may mắn? | chuẩn ngẫu nhiên ở trang Đánh giá | ~6 |
| 3 | [Bước ngẫu nhiên và null](03_buoc_ngau_nhien.md) | Nếu giá là ngẫu nhiên, thuật toán của mình có còn «thấy» cấu trúc không? | mốc ngẫu nhiên của nghiên cứu order flow | ~6 |
| 4 | [Chuỗi thời gian và biến động](04_chuoi_thoi_gian_bien_dong.md) | Cái gì của giá đoán được? Vì sao ATR lệch theo giờ? | ATR, displacement, trục biến động | ~7 |
| 5 | [Cấu trúc thị trường định lượng](05_cau_truc_dinh_luong.md) | Viết «đỉnh», «sweep», «shift» thành luật đo được thế nào, không nhìn tương lai? | `ict_structure`, `dc_atr_structure` | ~6 |
| 6 | [Regime](06_regime.md) | Thị trường đang trend hay range — đo thế nào, trễ bao nhiêu? | `hmm_online`, plan giai đoạn 4 | ~7 |
| 7 | [Đánh giá và overfit](07_danh_gia_overfit.md) | Làm sao biết thuật toán tốt thật hay chỉ khớp quá khứ? | đoạn phát triển / kiểm tra, trang Đánh giá | ~7 |
| 8 | [Chiến lược và chi phí](08_chien_luoc_chi_phi.md) | Từ «nhận diện đúng» tới «kiếm được tiền» còn thiếu gì? | router, repo giao dịch | ~6 |

Thêm: [từ điển thuật ngữ Việt – Anh](tu_dien.md).

```text
1 Dữ liệu ─► 2 Thống kê ─► 3 Ngẫu nhiên ─► 4 Biến động ─► 6 Regime ─► 8 Chiến lược
                              │                           ▲
                              └──────► 5 Cấu trúc ────────┘
                                            7 Đánh giá (dùng từ module 2, cần cho 6 và 8)
```

## Sách nền nên có bên cạnh

| Sách | Dùng cho | Ghi chú |
|---|---|---|
| Hyndman & Athanasopoulos, *Forecasting: Principles and Practice* | module 4, 6 | đọc miễn phí trên mạng; chuỗi thời gian từ cơ bản |
| James, Witten, Hastie, Tibshirani, Taylor, *An Introduction to Statistical Learning (with Applications in Python)* | module 2, 7 | miễn phí; thống kê và học máy nền |
| David Aronson, *Evidence-Based Technical Analysis* | module 2, 3, 7 | gần nhất với bài toán của bạn: kiểm định luật kỹ thuật bằng chuẩn ngẫu nhiên, thiên lệch do đào dữ liệu |
| Ruey Tsay, *Analysis of Financial Time Series* | module 4, 6 | lợi suất, biến động, mô hình chuyển trạng thái; nặng toán hơn |
| Marcos López de Prado, *Advances in Financial Machine Learning* | module 7 | gán nhãn, rò rỉ dữ liệu, overfit khi thử nhiều cấu hình |
| Larry Harris, *Trading and Exchanges* | module 1, 8 | thị trường vận hành ra sao: spread, thanh khoản, người tham gia |

## Liên hệ với tài liệu khác của lab

- Luật làm việc của lab: [`AGENTS.md`](../../AGENTS.md) — đọc sau module 7 sẽ thấy vì sao từng luật tồn tại.
- Đặc tả thuật toán ICT: [`thuat_toan_ict_structure.md`](../algorithms/thuat_toan_ict_structure.md) — module 5.
- Danh mục 287 phương pháp quant: [`danh_muc_phuong_phap_quant.md`](../research/danh_muc_phuong_phap_quant.md) — tra cứu sau module 6.
