"""Từ vựng sự kiện: Directional Change theo close + regime (``dc_atr_structure``).

Ghép vào ``core.types.StructureType`` / ``ReasonCode`` / ``*_TEXT_VI``.
"""
from __future__ import annotations


class DcType:
    DC_HIGH = "DC_HIGH"
    DC_LOW = "DC_LOW"
    DC_REGIME_UP = "DC_REGIME_UP"
    DC_REGIME_DOWN = "DC_REGIME_DOWN"
    DC_REGIME_UNKNOWN = "DC_REGIME_UNKNOWN"
    DC_RANGE_START = "DC_RANGE_START"
    DC_RANGE_EXIT = "DC_RANGE_EXIT"
    DC_SEGMENT_GAP = "DC_SEGMENT_GAP"
    DC_GAP_BRIDGED = "DC_GAP_BRIDGED"

    DC_PIVOT_TYPES = (DC_HIGH, DC_LOW)
    DC_REGIME_TYPES = (
        DC_REGIME_UP, DC_REGIME_DOWN, DC_REGIME_UNKNOWN, DC_RANGE_START, DC_RANGE_EXIT,
    )
    DC_TYPES = DC_PIVOT_TYPES + DC_REGIME_TYPES + (DC_SEGMENT_GAP, DC_GAP_BRIDGED)


class DcReason:
    DC_CLOSE_REVERSAL_FROM_HIGH = "DC_CLOSE_REVERSAL_FROM_HIGH"
    DC_CLOSE_REVERSAL_FROM_LOW = "DC_CLOSE_REVERSAL_FROM_LOW"
    DC_TREND_HH_HL = "DC_TREND_HH_HL"
    DC_TREND_LH_LL = "DC_TREND_LH_LL"
    DC_NO_TREND_NO_RANGE = "DC_NO_TREND_NO_RANGE"
    DC_RANGE_CLUSTERS = "DC_RANGE_CLUSTERS"
    DC_RANGE_CLOSE_BREAK_UP = "DC_RANGE_CLOSE_BREAK_UP"
    DC_RANGE_CLOSE_BREAK_DOWN = "DC_RANGE_CLOSE_BREAK_DOWN"
    DC_GAP_RESET = "DC_GAP_RESET"
    DC_GAP_BRIDGED = "DC_GAP_BRIDGED"


#: Giải thích tiếng Việt cho từng loại sự kiện.
STRUCTURE_TEXT_VI: dict[str, str] = {
    DcType.DC_HIGH: "Đỉnh DC theo close (đã xác nhận)",
    DcType.DC_LOW: "Đáy DC theo close (đã xác nhận)",
    DcType.DC_REGIME_UP: "Trạng thái → Tăng (theo swing DC đã xác nhận)",
    DcType.DC_REGIME_DOWN: "Trạng thái → Giảm (theo swing DC đã xác nhận)",
    DcType.DC_REGIME_UNKNOWN: "Trạng thái → Chưa rõ",
    DcType.DC_RANGE_START: "Range bắt đầu (biên khoá)",
    DcType.DC_RANGE_EXIT: "Range kết thúc do close phá biên",
    DcType.DC_SEGMENT_GAP: "Gap dữ liệu — reset segment DC",
    DcType.DC_GAP_BRIDGED: "Gap ngắn — được nối, không reset",
}

#: Giải thích tiếng Việt cho từng mã lý do (tooltip giao diện).
REASON_TEXT_VI: dict[str, str] = {
    DcReason.DC_CLOSE_REVERSAL_FROM_HIGH: (
        "Đỉnh theo CLOSE (Directional Change): close hiện tại đã giảm ít nhất một "
        "ngưỡng Δ so với close cao nhất của ứng viên. Δ khoá tại nến cực trị "
        "(k × ATR hoặc % close). Chạm đúng ngưỡng là đạt. Không phải đỉnh theo wick."
    ),
    DcReason.DC_CLOSE_REVERSAL_FROM_LOW: (
        "Đáy theo CLOSE (Directional Change): close hiện tại đã tăng ít nhất một "
        "ngưỡng Δ so với close thấp nhất của ứng viên. Δ khoá tại nến cực trị "
        "(k × ATR hoặc % close). Chạm đúng ngưỡng là đạt. Không phải đáy theo wick."
    ),
    DcReason.DC_TREND_HH_HL: (
        "Định nghĩa vận hành của lab: đỉnh DC gần nhất là HH và đáy DC gần nhất là HL "
        "(so với pivot cùng loại liền trước, dung sai khoá lúc xác nhận). Không phải dự báo."
    ),
    DcReason.DC_TREND_LH_LL: (
        "Định nghĩa vận hành của lab: đỉnh DC gần nhất là LH và đáy DC gần nhất là LL. "
        "Không phải dự báo."
    ),
    DcReason.DC_NO_TREND_NO_RANGE: (
        "Chưa rõ: thiếu pivot để so sánh, nhãn mâu thuẫn (vd HH + LL) hoặc có EQ, và "
        "cũng chưa đủ điều kiện Range. Không gán Range chỉ vì không thấy trend."
    ),
    DcReason.DC_RANGE_CLUSTERS: (
        "Range: m đỉnh và m đáy DC gần nhất tạo hai cụm hẹp (≤ dung sai × ATR), tách "
        "nhau, đủ rộng và close hiện tại nằm giữa hai biên. Biên và buffer khoá từ lúc này."
    ),
    DcReason.DC_RANGE_CLOSE_BREAK_UP: (
        "Range kết thúc: CLOSE vượt biên trên + buffer đã khoá. Wick vượt biên không đủ. "
        "Trạng thái về «chưa rõ» chờ pivot mới ở nến sau."
    ),
    DcReason.DC_RANGE_CLOSE_BREAK_DOWN: (
        "Range kết thúc: CLOSE thủng biên dưới − buffer đã khoá. Wick không đủ. "
        "Trạng thái về «chưa rõ» chờ pivot mới ở nến sau."
    ),
    DcReason.DC_GAP_RESET: (
        "Gap dữ liệu (khoảng cách nến khác bước timeframe, gồm nghỉ phiên/cuối tuần): "
        "kết thúc segment, bỏ ứng viên, ATR, lịch sử pivot/range; warm-up lại. Log cũ giữ nguyên."
    ),
    DcReason.DC_GAP_BRIDGED: (
        "Gap ngắn được NỐI (gap_policy=bridge_short): không reset segment; giữ ứng viên, "
        "ngưỡng đã khoá, ATR và lịch sử pivot/range. TR nến đầu sau gap tính với close "
        "trước gap nên gồm cả bước nhảy giá qua gap. Chỉ là ghi nhận dữ liệu."
    ),
}
