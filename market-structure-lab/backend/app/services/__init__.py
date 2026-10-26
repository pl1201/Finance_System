"""Tầng nghiệp vụ: nối lõi thuật toán (``core/``) với lưu trữ; không chứa chi tiết HTTP.

| Module | Việc |
|---|---|
| ``common`` | DB của ứng dụng, tra dataset, đọc nến thành ``Bar`` |
| ``datasets`` | nhập CSV / MT5, tổng hợp nến, dữ liệu mẫu, trả nến cho chart |
| ``runs`` | chạy thuật toán, lưu / mở lại / xoá run, so sánh, xuất CSV, manifest |
| ``replay`` | phiên replay từng nến (bộ nhớ tiến trình) |
| ``labels`` | bộ nhãn tham chiếu, CSV nhãn, nguồn gốc nhãn |
| ``auto_label`` | đề xuất nhãn từ thuật toán có sẵn (người duyệt) |
| ``evaluations`` | chấm run với nhãn, đánh giá đã lưu, báo cáo |
| ``mql5`` | đối chiếu sự kiện Python với CSV MQL5 |

Lỗi nghiệp vụ: ``backend.app.errors.ServiceError`` (400), ``NotFoundError`` (404).
"""
