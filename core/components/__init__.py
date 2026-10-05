"""Thành phần trạng thái dùng chung cho thuật toán tổ hợp (kien_truc_luong_ict.md §4.2).

Mỗi thành phần nhận nến (và sự kiện tầng dưới) **theo thứ tự**, chỉ dùng thông tin đã biết, giữ
trạng thái riêng và có ``reset()``. Thuật toán tổ hợp (vd ``ict_structure``) gọi chúng theo thứ tự
cố định trong mỗi nến — thứ tự ghi trong đặc tả của thuật toán đó.

Hiện có (giai đoạn 1 của ``ict_structure``, docs/plans/plan_ict_structure.md §10):

* ``session_gap``     [G]  phân loại khoảng trống theo lịch phiên khai báo
* ``swing_source``    [P1] pivot strict left/right (STH/STL), chặn cửa sổ vắt qua gap
* ``hierarchy``       [S1] lọc cấp k+1 trên chuỗi pivot cấp k (ITH/ITL, LTH/LTL)
* ``structure_order`` [S2] thứ tự đỉnh/đáy + mức được bảo vệ
* ``dealing_range``   [S4] dealing range, premium/discount

Chỉ ``ict_structure`` dùng ở v0.1 — thuật toán cũ **không** bị refactor sang đây (plan R7); tương
đương được kiểm bằng test (pivot/cấp 2 khớp ``swing_pivot(1,1)`` / ``swing_hierarchy(1,1)`` khi tắt
chặn gap).
"""
