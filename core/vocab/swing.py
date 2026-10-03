"""Từ vựng sự kiện: Swing pivot, phân cấp, HH/HL/LH/LL/EQ, BOS/CHoCH (``swing_pivot``, ``swing_hierarchy``).

Ghép vào ``core.types.StructureType`` / ``ReasonCode`` / ``*_TEXT_VI``.
"""
from __future__ import annotations


class SwingType:
    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"
    SWING_HIGH_L2 = "SWING_HIGH_L2"
    SWING_LOW_L2 = "SWING_LOW_L2"
    HH = "HH"          # higher high
    LH = "LH"          # lower high
    EQH = "EQH"        # equal high — KHÔNG ép thành HH/LH
    HL = "HL"          # higher low
    LL = "LL"          # lower low
    EQL = "EQL"        # equal low — KHÔNG ép thành HL/LL
    BOS_UP = "BOS_UP"
    BOS_DOWN = "BOS_DOWN"
    BOS_INTERNAL_UP = "BOS_INTERNAL_UP"
    BOS_INTERNAL_DOWN = "BOS_INTERNAL_DOWN"
    CHOCH_UP = "CHOCH_UP"
    CHOCH_DOWN = "CHOCH_DOWN"

    SWING_ALL = (
        SWING_HIGH, SWING_LOW, SWING_HIGH_L2, SWING_LOW_L2,
        HH, LH, EQH, HL, LL, EQL,
        BOS_UP, BOS_DOWN, BOS_INTERNAL_UP, BOS_INTERNAL_DOWN,
        CHOCH_UP, CHOCH_DOWN,
    )


class SwingReason:
    PIVOT_HIGH_STRICT = "PIVOT_HIGH_STRICT"
    PIVOT_LOW_STRICT = "PIVOT_LOW_STRICT"
    SEQ_HIGHER_HIGH = "SEQ_HIGHER_HIGH"
    SEQ_LOWER_HIGH = "SEQ_LOWER_HIGH"
    SEQ_EQUAL_HIGH = "SEQ_EQUAL_HIGH"
    SEQ_HIGHER_LOW = "SEQ_HIGHER_LOW"
    SEQ_LOWER_LOW = "SEQ_LOWER_LOW"
    SEQ_EQUAL_LOW = "SEQ_EQUAL_LOW"
    BOS_CLOSE_ABOVE_SWING_HIGH = "BOS_CLOSE_ABOVE_SWING_HIGH"
    BOS_CLOSE_BELOW_SWING_LOW = "BOS_CLOSE_BELOW_SWING_LOW"
    BOS_INTERNAL_CLOSE_ABOVE = "BOS_INTERNAL_CLOSE_ABOVE"
    BOS_INTERNAL_CLOSE_BELOW = "BOS_INTERNAL_CLOSE_BELOW"
    CHOCH_CLOSE_ABOVE_SWING_HIGH = "CHOCH_CLOSE_ABOVE_SWING_HIGH"
    CHOCH_CLOSE_BELOW_SWING_LOW = "CHOCH_CLOSE_BELOW_SWING_LOW"
    PIVOT_HIGH_L2 = "PIVOT_HIGH_L2"
    PIVOT_LOW_L2 = "PIVOT_LOW_L2"
    SEQ_HIGHER_HIGH_L2 = "SEQ_HIGHER_HIGH_L2"
    SEQ_LOWER_HIGH_L2 = "SEQ_LOWER_HIGH_L2"
    SEQ_EQUAL_HIGH_L2 = "SEQ_EQUAL_HIGH_L2"
    SEQ_HIGHER_LOW_L2 = "SEQ_HIGHER_LOW_L2"
    SEQ_LOWER_LOW_L2 = "SEQ_LOWER_LOW_L2"
    SEQ_EQUAL_LOW_L2 = "SEQ_EQUAL_LOW_L2"


#: Giải thích tiếng Việt cho từng loại sự kiện.
STRUCTURE_TEXT_VI: dict[str, str] = {
    SwingType.SWING_HIGH: "Đỉnh swing đã xác nhận",
    SwingType.SWING_LOW: "Đáy swing đã xác nhận",
    SwingType.SWING_HIGH_L2: "Đỉnh swing cấp 2 (lọc trên chuỗi đỉnh cấp 1)",
    SwingType.SWING_LOW_L2: "Đáy swing cấp 2 (lọc trên chuỗi đáy cấp 1)",
    SwingType.HH: "Đỉnh cao hơn (Higher High)",
    SwingType.LH: "Đỉnh thấp hơn (Lower High)",
    SwingType.EQH: "Đỉnh bằng nhau (Equal High)",
    SwingType.HL: "Đáy cao hơn (Higher Low)",
    SwingType.LL: "Đáy thấp hơn (Lower Low)",
    SwingType.EQL: "Đáy bằng nhau (Equal Low)",
    SwingType.BOS_UP: "Phá vỡ cấu trúc chính lên (BOS tăng)",
    SwingType.BOS_DOWN: "Phá vỡ cấu trúc chính xuống (BOS giảm)",
    SwingType.BOS_INTERNAL_UP: "BOS nội bộ lên",
    SwingType.BOS_INTERNAL_DOWN: "BOS nội bộ xuống",
    SwingType.CHOCH_UP: "Đổi hướng cấu trúc lên (CHoCH tăng)",
    SwingType.CHOCH_DOWN: "Đổi hướng cấu trúc xuống (CHoCH giảm)",
}

#: Giải thích tiếng Việt cho từng mã lý do (tooltip giao diện).
REASON_TEXT_VI: dict[str, str] = {
    SwingReason.PIVOT_HIGH_STRICT: (
        "High của nến pivot LỚN HƠN TUYỆT ĐỐI mọi high trong cửa sổ trái/phải. "
        "Trường hợp bằng nhau không được nhận là pivot ở phiên bản này."
    ),
    SwingReason.PIVOT_LOW_STRICT: (
        "Low của nến pivot NHỎ HƠN TUYỆT ĐỐI mọi low trong cửa sổ trái/phải. "
        "Trường hợp bằng nhau không được nhận là pivot ở phiên bản này."
    ),
    SwingReason.SEQ_HIGHER_HIGH: (
        "Swing high đã xác nhận CAO HƠN swing high đã xác nhận liền trước."
    ),
    SwingReason.SEQ_LOWER_HIGH: (
        "Swing high đã xác nhận THẤP HƠN swing high đã xác nhận liền trước."
    ),
    SwingReason.SEQ_EQUAL_HIGH: (
        "Hai swing high liên tiếp BẰNG NHAU trong dung sai đã khai báo. "
        "Gắn nhãn riêng EQH, không ép thành HH hoặc LH."
    ),
    SwingReason.SEQ_HIGHER_LOW: (
        "Swing low đã xác nhận CAO HƠN swing low đã xác nhận liền trước."
    ),
    SwingReason.SEQ_LOWER_LOW: (
        "Swing low đã xác nhận THẤP HƠN swing low đã xác nhận liền trước."
    ),
    SwingReason.SEQ_EQUAL_LOW: (
        "Hai swing low liên tiếp BẰNG NHAU trong dung sai đã khai báo. "
        "Gắn nhãn riêng EQL, không ép thành HL hoặc LL."
    ),
    SwingReason.BOS_CLOSE_ABOVE_SWING_HIGH: (
        "Giá ĐÓNG CỬA vượt lên trên mức swing high đã xác nhận (cộng biên phá vỡ). "
        "Mỗi mức chỉ phát tín hiệu một lần."
    ),
    SwingReason.BOS_CLOSE_BELOW_SWING_LOW: (
        "Giá ĐÓNG CỬA xuống dưới mức swing low đã xác nhận (trừ biên phá vỡ). "
        "Mỗi mức chỉ phát tín hiệu một lần. Đây là BOS chính hoặc BOS khi chưa có bias."
    ),
    SwingReason.BOS_INTERNAL_CLOSE_ABOVE: (
        "Giá đóng cửa vượt đỉnh swing nội bộ (không phải mức high cực trị còn nguyên). "
        "Chưa phá mức chính."
    ),
    SwingReason.BOS_INTERNAL_CLOSE_BELOW: (
        "Giá đóng cửa thủng đáy swing nội bộ (không phải mức low cực trị còn nguyên). "
        "Chưa phá mức chính."
    ),
    SwingReason.CHOCH_CLOSE_ABOVE_SWING_HIGH: (
        "CHoCH tăng: giá đóng cửa phá mức swing high CHÍNH trong lúc bias đang giảm. "
        "Bias chuyển sang tăng sau nến này."
    ),
    SwingReason.CHOCH_CLOSE_BELOW_SWING_LOW: (
        "CHoCH giảm: giá đóng cửa phá mức swing low CHÍNH trong lúc bias đang tăng. "
        "Bias chuyển sang giảm sau nến này."
    ),
    SwingReason.PIVOT_HIGH_L2: (
        "Đỉnh cấp 2: pivot cấp 1 giữa cao hơn tuyệt đối hai đỉnh cấp 1 liền kề "
        "trên chuỗi pivot (không phải ba nến liên tiếp). Chỉ xác nhận khi đỉnh "
        "cấp 1 bên phải đã xác nhận — không gắn về lúc đỉnh giữa hình thành."
    ),
    SwingReason.PIVOT_LOW_L2: (
        "Đáy cấp 2: pivot cấp 1 giữa thấp hơn tuyệt đối hai đáy cấp 1 liền kề "
        "trên chuỗi pivot. Chỉ xác nhận khi đáy cấp 1 bên phải đã xác nhận."
    ),
    SwingReason.SEQ_HIGHER_HIGH_L2: (
        "Đỉnh cấp 2 vừa xác nhận CAO HƠN đỉnh cấp 2 đã xác nhận liền trước."
    ),
    SwingReason.SEQ_LOWER_HIGH_L2: (
        "Đỉnh cấp 2 vừa xác nhận THẤP HƠN đỉnh cấp 2 đã xác nhận liền trước."
    ),
    SwingReason.SEQ_EQUAL_HIGH_L2: (
        "Hai đỉnh cấp 2 liên tiếp BẰNG NHAU trong dung sai đã khai báo. "
        "Gắn nhãn riêng EQH, không ép thành HH hoặc LH."
    ),
    SwingReason.SEQ_HIGHER_LOW_L2: (
        "Đáy cấp 2 vừa xác nhận CAO HƠN đáy cấp 2 đã xác nhận liền trước."
    ),
    SwingReason.SEQ_LOWER_LOW_L2: (
        "Đáy cấp 2 vừa xác nhận THẤP HƠN đáy cấp 2 đã xác nhận liền trước."
    ),
    SwingReason.SEQ_EQUAL_LOW_L2: (
        "Hai đáy cấp 2 liên tiếp BẰNG NHAU trong dung sai đã khai báo. "
        "Gắn nhãn riêng EQL, không ép thành HL hoặc LL."
    ),
}
