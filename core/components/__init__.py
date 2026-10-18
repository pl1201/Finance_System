"""Thành phần trạng thái dùng chung cho thuật toán tổ hợp (kien_truc_luong_ict.md §4.2).

Mỗi thành phần nhận nến (và sự kiện tầng dưới) **theo thứ tự**, chỉ dùng thông tin đã biết, giữ
trạng thái riêng và có ``reset()``. Thuật toán tổ hợp (vd ``ict_structure``) gọi chúng theo thứ tự
cố định trong mỗi nến — thứ tự ghi trong đặc tả của thuật toán đó.

Hiện có (``ict_structure``, docs/plans/plan_ict_structure.md §10).

Giai đoạn 1:

* ``session_gap``     [G]  phân loại khoảng trống theo lịch phiên khai báo
* ``swing_source``    [P1] pivot strict left/right (STH/STL), chặn cửa sổ vắt qua gap
* ``hierarchy``       [S1] lọc cấp k+1 trên chuỗi pivot cấp k (ITH/ITL, LTH/LTL)
* ``structure_order`` [S2] thứ tự đỉnh/đáy + mức được bảo vệ
* ``dealing_range``   [S4] dealing range, premium/discount

Giai đoạn 2:

* ``displacement``    [P3] nến displacement (biên độ ≥ k × ATR, thân ≥ tỷ lệ biên độ)
* ``fvg``             [P2] FVG ba nến + vòng đời chạm → lấp
* ``liquidity``       [S3]/[E2] vùng thanh khoản BSL/SSL (gộp EQH/EQL) + vòng đời chạm → lấy →
  sweep / run / chưa rõ
* ``shift``           [E3] shift = sweep → displacement ngược chiều
* ``killzone``        [C]  killzone theo giờ New York (chỉ là cờ, không lọc)
* ``order_flow``      [OF] order flow đọc theo thanh khoản: run + shift, run phía ngược → chưa rõ
  (v0.3.0, chốt 06/10/2026) — mô tả, không phải tín hiệu

Giai đoạn 3 (v0.4.0 — bộ gộp khung lớn ``ny_1700`` nằm ở ``core/data/htf_stream.SessionHtfAggregator``):

* ``htf_stack``       [T1] ngăn xếp cấu trúc khung lớn H1/H4: chính P1 → S1 → S2, S4, FVG trên nến khung
  lớn đã chốt, ATR riêng; nến degraded / hole chặn cửa sổ
* ``period_levels``   [T2] PDH/PDL, PWH/PWL, giá mở ngày, midnight open
* ``pd_array``        [S5] phản ứng của giá ở FVG khung lớn (respect / disrespect) → ``pd_bias``
* ``dol``             [S6] DOL — vùng thanh khoản còn nguyên gần nhất phía shift, tầng ≥ H1

Chỉ ``ict_structure`` dùng (từ v0.1) — thuật toán cũ **không** bị refactor sang đây (plan R7); tương
đương được kiểm bằng test (pivot/cấp 2 khớp ``swing_pivot(1,1)`` / ``swing_hierarchy(1,1)`` khi tắt
chặn gap).
"""
