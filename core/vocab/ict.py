"""Từ vựng sự kiện: bộ nhận diện cấu trúc ICT phân tầng (``ict_structure``).

STH/STL dùng lại ``SWING_HIGH``/``SWING_LOW``, ITH/ITL dùng lại ``SWING_HIGH_L2``/``SWING_LOW_L2``
(họ ``swing``) — cùng nghĩa (pivot strict; cấp 2 lọc trên chuỗi cấp 1), nên chấm được với mục tiêu
«Swing cấu trúc (cấp 2)» sẵn có. Ở đây chỉ khai phần mới. Ghép vào ``core.types``.
"""
from __future__ import annotations


class IctType:
    SWING_HIGH_L3 = "SWING_HIGH_L3"
    SWING_LOW_L3 = "SWING_LOW_L3"
    ICT_GAP = "ICT_GAP"

    ICT_TYPES = (SWING_HIGH_L3, SWING_LOW_L3, ICT_GAP)


class IctReason:
    PIVOT_HIGH_L3 = "PIVOT_HIGH_L3"
    PIVOT_LOW_L3 = "PIVOT_LOW_L3"
    GAP_NGHI_PHIEN = "GAP_NGHI_PHIEN"
    GAP_CUOI_TUAN = "GAP_CUOI_TUAN"
    GAP_NGHI_LE = "GAP_NGHI_LE"
    GAP_THIEU_TRONG_PHIEN = "GAP_THIEU_TRONG_PHIEN"
    GAP_NGOAI_LICH = "GAP_NGOAI_LICH"
    GAP_KHONG_RO_LICH = "GAP_KHONG_RO_LICH"


STRUCTURE_TEXT_VI: dict[str, str] = {
    IctType.SWING_HIGH_L3: "Đỉnh swing cấp 3 (LTH — lọc trên chuỗi đỉnh cấp 2)",
    IctType.SWING_LOW_L3: "Đáy swing cấp 3 (LTL — lọc trên chuỗi đáy cấp 2)",
    IctType.ICT_GAP: "Khoảng trống dữ liệu trước nến này (phân loại theo lịch phiên khai báo)",
}

REASON_TEXT_VI: dict[str, str] = {
    IctReason.PIVOT_HIGH_L3: (
        "Đỉnh cấp 2 ở giữa cao hơn (so sánh nghiêm ngặt) đỉnh cấp 2 liền trước và liền sau. "
        "Xác nhận khi đỉnh cấp 2 bên phải được xác nhận."
    ),
    IctReason.PIVOT_LOW_L3: (
        "Đáy cấp 2 ở giữa thấp hơn (so sánh nghiêm ngặt) đáy cấp 2 liền trước và liền sau. "
        "Xác nhận khi đáy cấp 2 bên phải được xác nhận."
    ),
    IctReason.GAP_NGHI_PHIEN: "Nghỉ hằng ngày theo lịch phiên (không phải thiếu dữ liệu).",
    IctReason.GAP_CUOI_TUAN: "Đóng cửa cuối tuần theo lịch phiên.",
    IctReason.GAP_NGHI_LE: "Đóng sớm hoặc đóng cả ngày theo lịch lễ khai báo.",
    IctReason.GAP_THIEU_TRONG_PHIEN: (
        "THIẾU DỮ LIỆU trong giờ thị trường mở theo lịch — bất thường, không phải nghỉ phiên. "
        "Không tự lấp; mức giữ nguyên, cửa sổ pivot vắt qua bị chặn."
    ),
    IctReason.GAP_NGOAI_LICH: (
        "Khoảng trống nằm ngoài phạm vi lịch phiên khai báo — không phân loại được."
    ),
    IctReason.GAP_KHONG_RO_LICH: (
        "Chưa chọn lịch phiên — không phân biệt được nghỉ phiên với thiếu dữ liệu."
    ),
}
