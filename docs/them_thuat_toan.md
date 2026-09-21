# Thêm thuật toán mới và hướng tích hợp MT5/MQL5

## 1. Kiến trúc: ba phần tách rời

```
core/data/      adapter dữ liệu   — nạp CSV, kiểm tra, chuẩn hoá thời gian
core/algorithms/ lõi thuật toán   — thuần tính toán, chỉ dùng thư viện chuẩn
core/engine.py  chạy & replay     — nạp nến tuần tự, gom sự kiện, thống kê
backend/        API + lưu trữ     — FastAPI, SQLite
frontend/       giao diện         — HTML/JS tĩnh
```

Lõi thuật toán **không import** FastAPI, SQLite, pandas, notebook hay
MetaTrader5. `hmm_online` import hmmlearn/numpy **chỉ khi fit**. Nhờ vậy phần
còn lại chạy được khi chưa cài các gói đó.

## 2. Thêm một thuật toán

### Bước 1 — tạo lớp con của `StructureAlgorithm`

```python
# core/algorithms/vi_du.py
from core.algorithms.base import ParamSpec, StructureAlgorithm
from core.types import Bar, StructureEvent


class ViDuAlgorithm(StructureAlgorithm):
    name = "vi_du"
    display_name_vi = "Thuật toán ví dụ"
    version = "0.1.0"
    description_vi = "Mô tả ngắn hiển thị trên giao diện."

    @classmethod
    def param_specs(cls):
        return (
            ParamSpec("cua_so", "Độ dài cửa sổ", "int", 20, min=2, max=500,
                      help_vi="Số nến dùng để tính."),
        )

    def __init__(self, **params):
        p = self.validate_params(params)
        self.cua_so = p["cua_so"]
        self.params = p
        self.reset()

    def reset(self):
        self._bars = []

    def warmup_bars(self):
        return self.cua_so

    def on_bar(self, bar: Bar) -> list[StructureEvent]:
        self._bars.append(bar)
        if len(self._bars) < self.cua_so:
            return []          # chưa đủ warm-up
        return []              # trả về các sự kiện XÁC NHẬN tại chính nến này
```

### Bước 2 — đăng ký

Thêm vào `_ALGORITHMS` trong [`core/registry.py`](../core/registry.py).
Giao diện tự đọc registry để dựng dropdown và form tham số — **không cần sửa
frontend**.

### Bước 3 — viết test

Tối thiểu: một chuỗi nhỏ có kết quả tính tay, một test warm-up, và một test
"thêm dữ liệu sau T không đổi sự kiện đã xác nhận tại T"
(xem mẫu trong `tests/test_replay_causality.py`).

### Hợp đồng bắt buộc

| Yêu cầu | Lý do |
|---|---|
| `on_bar` chỉ dùng nến đã nạp | Không rò rỉ dữ liệu tương lai |
| Không sửa/thu hồi sự kiện đã trả về | Lịch sử quyết định bất biến |
| `confirmed_at == bar.close_time` của nến đang xử lý | Phân biệt thời điểm sự kiện và thời điểm biết |
| Tất định với cùng chuỗi nến | Tái lập được; nếu có ngẫu nhiên phải lưu seed |
| `reset()` xoá sạch trạng thái | Replay lùi dựa vào việc dựng lại từ đầu |

### Tuỳ chọn

* `pending_state()` — trạng thái tạm thời để hiển thị (không phải sự kiện).
* `timeline_point(bar)` — giá trị vẽ overlay theo từng nến (mức swing, xác suất
  regime…). Engine gọi ngay sau `on_bar` nên chuỗi này cũng tôn trọng nhân quả.
* Thêm `structure_type` và `reason_code` mới vào `core/types.py`, kèm câu giải
  thích tiếng Việt cho tooltip, và một lớp badge `.b-<TYPE>` trong
  `frontend/css/app.css` nếu muốn có màu riêng.

## 3. Ghi chú cho HMM và BOCD

**HMM:** đã triển khai `hmm_online` v1.0.0 — xem [`thuat_toan_hmm_online.md`](thuat_toan_hmm_online.md).
Fit trên prefix `train_bars` bằng hmmlearn; `on_bar` chỉ bước forward. State
mặc định `chua_gan_nghia` (không tự gắn Trend/Range).

**BOCD (Adams–MacKay)** chưa triển khai.

Hai ứng viên trong tài liệu nhóm khớp với interface này, nhưng cần lưu ý:

**HMM (hmmlearn).** Phải tách rõ **fit** và **lọc online**:

* `fit` chỉ được chạy trên phần dữ liệu train, ở ngoài vòng `on_bar`. Thuật toán
  nhận model đã fit qua tham số khởi tạo hoặc một đường dẫn file.
* Trong `on_bar` chỉ được dùng bước **filtering** (forward), tuyệt đối không dùng
  kết quả **smoothing** (Viterbi/forward-backward trên toàn chuỗi) vì nó dùng
  dữ liệu tương lai.
* Nếu có lịch refit, phải ghi rõ thời điểm model mới được phép sử dụng và không
  cho model nhìn thấy dữ liệu sau mốc đó.
* State của HMM không tự mang nghĩa Trend/Range — cần một bảng ánh xạ công bố trước.

**BOCD (Adams–MacKay).** Bản chất là online nên hợp với `on_bar`. Lưu ý:

* Chọn likelihood và hazard rate là lựa chọn mô hình — phải lưu vào tham số.
* Điểm đổi chế độ không tự cho hướng tăng/giảm; đừng biến nó thành tín hiệu lệnh.

**`ruptures`** hướng tới offline. Nếu dùng, chỉ để phân tích hồi cứu; **không**
lấy breakpoint tính trên toàn chuỗi làm tín hiệu online tại thời điểm quá khứ.

## 4. MT5 / MQL5

Đã có `core/data/mt5_source.py` (gói tuỳ chọn) và script
[`mql5/SwingPivotExport.mq5`](../mql5/SwingPivotExport.mq5). Xem
[`mt5_va_tong_hop_nen.md`](mt5_va_tong_hop_nen.md) và
[`doi_chieu_python_mql5.md`](doi_chieu_python_mql5.md).

Bốn đường tích hợp (tài liệu nhóm):

| Phương án | Cách làm trong dự án này | Giới hạn |
|---|---|---|
| **Lấy dữ liệu qua Python** | `core/data/mt5_source.py` + `POST /api/datasets/import-mt5`. Loại nến đang hình thành. | Gói tuỳ chọn; không thay Strategy Tester. |
| **Chuyển logic sang MQL5** | Script `mql5/SwingPivotExport.mq5` + tab Đối chiếu MQL5 / `POST /api/compare-mql5`. | Cần cùng dataset_checksum. |
| **Xuất mô hình ONNX** | Chỉ áp dụng khi có ML; vòng lặp pivot bằng Python không xuất ONNX được. | ONNX chuyển phần mô hình, không chuyển pandas hay vòng lặp. |
| **Bridge Python–EA** | Ghi kết quả ra file/HTTP cho EA đọc. | `WebRequest` không chạy trong Strategy Tester. Từng hàng kết quả phải được sinh chỉ từ thông tin khả dụng tại thời điểm đó. |

**Đường đề xuất cho nhóm:** giữ Python làm bản tham chiếu; chuyển thuật toán
cấu trúc dùng luật sang MQL5 để quan sát trong MT5; đối chiếu hai bên bằng
CSV sự kiện trên **cùng một snapshot dữ liệu**. Chênh lệch giữa hai feed khác
nhau chưa đủ để kết luận có lỗi code.

### Chuẩn bị sẵn cho việc đối chiếu

Mỗi lần chạy đã lưu đủ thông tin để một bản triển khai khác tái lập:

* `dataset_checksum` — checksum nội dung nến đã chuẩn hoá (không phụ thuộc định
  dạng file), nên bản MQL5 nạp cùng dữ liệu là so được.
* `algorithm_version` + `params` — quy tắc và tham số chính xác.
* `range_start` / `range_end` và `warmup_bars`.
* CSV sự kiện có `event_time`, `confirmed_at`, `confirmation_lag_bars` — đủ để
  kiểm tra cả vị trí lẫn thời điểm xác nhận, không chỉ vị trí.

Gọi `GET /api/runs/{run_id}/manifest` để lấy toàn bộ hồ sơ này dưới dạng JSON.
