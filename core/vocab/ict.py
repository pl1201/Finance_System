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
    # giai đoạn 2
    DISPLACEMENT_UP = "DISPLACEMENT_UP"
    DISPLACEMENT_DOWN = "DISPLACEMENT_DOWN"
    FVG_UP = "FVG_UP"
    FVG_DOWN = "FVG_DOWN"
    FVG_TOUCHED = "FVG_TOUCHED"
    FVG_FILLED = "FVG_FILLED"
    LIQ_SWEEP_BSL = "LIQ_SWEEP_BSL"
    LIQ_SWEEP_SSL = "LIQ_SWEEP_SSL"
    LIQ_RUN_UP = "LIQ_RUN_UP"
    LIQ_RUN_DOWN = "LIQ_RUN_DOWN"
    LIQ_UNRESOLVED = "LIQ_UNRESOLVED"
    SHIFT_UP = "SHIFT_UP"
    SHIFT_DOWN = "SHIFT_DOWN"
    SHIFT_FVG_UP = "SHIFT_FVG_UP"
    SHIFT_FVG_DOWN = "SHIFT_FVG_DOWN"
    # order flow theo thanh khoản (v0.3.0) — mô tả, không phải tín hiệu
    ORDER_FLOW_UP = "ORDER_FLOW_UP"
    ORDER_FLOW_DOWN = "ORDER_FLOW_DOWN"
    ORDER_FLOW_UNCLEAR = "ORDER_FLOW_UNCLEAR"
    # giai đoạn 3 (v0.4.0) — khung lớn [T]: ẩn mặc định, ngoài chấm M15 (D12)
    HTF_SWING_HIGH = "HTF_SWING_HIGH"
    HTF_SWING_LOW = "HTF_SWING_LOW"
    HTF_FVG_UP = "HTF_FVG_UP"
    HTF_FVG_DOWN = "HTF_FVG_DOWN"
    HTF_BAR_DEGRADED = "HTF_BAR_DEGRADED"
    HTF_PERIOD_HIGH = "HTF_PERIOD_HIGH"
    HTF_PERIOD_LOW = "HTF_PERIOD_LOW"
    # giai đoạn 3 — [S5] phản ứng ở FVG khung lớn (hậu tố = chiều FVG), [S6] DOL
    PD_RESPECT_UP = "PD_RESPECT_UP"
    PD_RESPECT_DOWN = "PD_RESPECT_DOWN"
    PD_DISRESPECT_UP = "PD_DISRESPECT_UP"
    PD_DISRESPECT_DOWN = "PD_DISRESPECT_DOWN"
    DOL_REACHED = "DOL_REACHED"

    SHIFT_TYPES = (SHIFT_UP, SHIFT_DOWN)
    ORDER_FLOW_TYPES = (ORDER_FLOW_UP, ORDER_FLOW_DOWN, ORDER_FLOW_UNCLEAR)
    HTF_TYPES = (HTF_SWING_HIGH, HTF_SWING_LOW, HTF_FVG_UP, HTF_FVG_DOWN, HTF_BAR_DEGRADED,
                 HTF_PERIOD_HIGH, HTF_PERIOD_LOW)
    PD_TYPES = (PD_RESPECT_UP, PD_RESPECT_DOWN, PD_DISRESPECT_UP, PD_DISRESPECT_DOWN)
    ICT_TYPES = (
        SWING_HIGH_L3, SWING_LOW_L3, ICT_GAP,
        DISPLACEMENT_UP, DISPLACEMENT_DOWN, FVG_UP, FVG_DOWN, FVG_TOUCHED, FVG_FILLED,
        LIQ_SWEEP_BSL, LIQ_SWEEP_SSL, LIQ_RUN_UP, LIQ_RUN_DOWN, LIQ_UNRESOLVED,
        SHIFT_UP, SHIFT_DOWN, SHIFT_FVG_UP, SHIFT_FVG_DOWN,
        ORDER_FLOW_UP, ORDER_FLOW_DOWN, ORDER_FLOW_UNCLEAR,
        HTF_SWING_HIGH, HTF_SWING_LOW, HTF_FVG_UP, HTF_FVG_DOWN, HTF_BAR_DEGRADED, HTF_PERIOD_HIGH, HTF_PERIOD_LOW,
        PD_RESPECT_UP, PD_RESPECT_DOWN, PD_DISRESPECT_UP, PD_DISRESPECT_DOWN, DOL_REACHED,
    )


class IctReason:
    PIVOT_HIGH_L3 = "PIVOT_HIGH_L3"
    PIVOT_LOW_L3 = "PIVOT_LOW_L3"
    GAP_NGHI_PHIEN = "GAP_NGHI_PHIEN"
    GAP_CUOI_TUAN = "GAP_CUOI_TUAN"
    GAP_NGHI_LE = "GAP_NGHI_LE"
    GAP_THIEU_TRONG_PHIEN = "GAP_THIEU_TRONG_PHIEN"
    GAP_NGOAI_LICH = "GAP_NGOAI_LICH"
    GAP_KHONG_RO_LICH = "GAP_KHONG_RO_LICH"
    # giai đoạn 2
    DISP_RANGE_BODY = "DISP_RANGE_BODY"
    FVG_THREE_BAR = "FVG_THREE_BAR"
    FVG_FIRST_TOUCH = "FVG_FIRST_TOUCH"
    FVG_FULL_FILL = "FVG_FULL_FILL"
    LIQ_TAKEN_THEN_CLOSE_BACK = "LIQ_TAKEN_THEN_CLOSE_BACK"
    LIQ_TAKEN_NO_RETURN = "LIQ_TAKEN_NO_RETURN"
    LIQ_GAP_IN_WINDOW = "LIQ_GAP_IN_WINDOW"
    SHIFT_SWEEP_THEN_DISPLACEMENT = "SHIFT_SWEEP_THEN_DISPLACEMENT"
    SHIFT_FVG_SAME_DISPLACEMENT = "SHIFT_FVG_SAME_DISPLACEMENT"
    # order flow (v0.3.0)
    OF_RUN = "OF_RUN"
    OF_SHIFT = "OF_SHIFT"
    OF_OPPOSITE_RUN = "OF_OPPOSITE_RUN"
    OF_BOTH_SIDES = "OF_BOTH_SIDES"
    # giai đoạn 3 (v0.4.0)
    HTF_PIVOT_HIGH_L2 = "HTF_PIVOT_HIGH_L2"
    HTF_PIVOT_LOW_L2 = "HTF_PIVOT_LOW_L2"
    HTF_FVG_THREE_BAR = "HTF_FVG_THREE_BAR"
    HTF_COVERAGE_LOW = "HTF_COVERAGE_LOW"
    HTF_FIRST_PERIOD_PARTIAL = "HTF_FIRST_PERIOD_PARTIAL"
    HTF_OUTSIDE_CALENDAR = "HTF_OUTSIDE_CALENDAR"
    HTF_PERIOD_LEVEL = "HTF_PERIOD_LEVEL"
    PD_RESPECT_STRICT = "PD_RESPECT_STRICT"
    PD_RESPECT_LOOSE = "PD_RESPECT_LOOSE"
    PD_DISRESPECT_FAR_EDGE = "PD_DISRESPECT_FAR_EDGE"
    PD_DISRESPECT_CE = "PD_DISRESPECT_CE"
    DOL_TARGET_TAKEN = "DOL_TARGET_TAKEN"


STRUCTURE_TEXT_VI: dict[str, str] = {
    IctType.SWING_HIGH_L3: "Đỉnh swing cấp 3 (LTH — lọc trên chuỗi đỉnh cấp 2)",
    IctType.SWING_LOW_L3: "Đáy swing cấp 3 (LTL — lọc trên chuỗi đáy cấp 2)",
    IctType.ICT_GAP: "Khoảng trống dữ liệu trước nến này (phân loại theo lịch phiên khai báo)",
    IctType.DISPLACEMENT_UP: "Displacement tăng (nến biên độ lớn, thân lớn)",
    IctType.DISPLACEMENT_DOWN: "Displacement giảm (nến biên độ lớn, thân lớn)",
    IctType.FVG_UP: "FVG tăng (khoảng trống giá ba nến)",
    IctType.FVG_DOWN: "FVG giảm (khoảng trống giá ba nến)",
    IctType.FVG_TOUCHED: "Giá chạm FVG lần đầu",
    IctType.FVG_FILLED: "Giá đi hết FVG (đã lấp)",
    IctType.LIQ_SWEEP_BSL: "Quét thanh khoản phía trên (lấy đỉnh rồi close quay lại dưới mức)",
    IctType.LIQ_SWEEP_SSL: "Quét thanh khoản phía dưới (lấy đáy rồi close quay lại trên mức)",
    IctType.LIQ_RUN_UP: "Lấy thanh khoản phía trên và đi luôn (không quay lại trong cửa sổ)",
    IctType.LIQ_RUN_DOWN: "Lấy thanh khoản phía dưới và đi luôn (không quay lại trong cửa sổ)",
    IctType.LIQ_UNRESOLVED: "Đã lấy thanh khoản nhưng gặp khoảng trống dữ liệu trước khi rõ sweep hay run",
    IctType.SHIFT_UP: "Shift tăng: quét đáy rồi displacement tăng ngược chiều",
    IctType.SHIFT_DOWN: "Shift giảm: quét đỉnh rồi displacement giảm ngược chiều",
    IctType.SHIFT_FVG_UP: "Shift tăng có FVG do chính nến displacement tạo ra",
    IctType.SHIFT_FVG_DOWN: "Shift giảm có FVG do chính nến displacement tạo ra",
    IctType.ORDER_FLOW_UP: (
        "Order flow sang tăng — đọc theo thanh khoản (run lên hoặc shift tăng). Là mô tả giá vừa lấy "
        "thanh khoản phía nào, không phải tín hiệu"
    ),
    IctType.ORDER_FLOW_DOWN: (
        "Order flow sang giảm — đọc theo thanh khoản (run xuống hoặc shift giảm). Là mô tả giá vừa lấy "
        "thanh khoản phía nào, không phải tín hiệu"
    ),
    IctType.ORDER_FLOW_UNCLEAR: (
        "Order flow chưa rõ — run phía ngược với order flow đang có, hoặc run/shift hai chiều cùng nến. "
        "Là mô tả, không phải tín hiệu"
    ),
    IctType.HTF_SWING_HIGH: (
        "Đỉnh cấu trúc khung lớn (ITH H1/H4, tính trên nến khung lớn ĐÃ CHỐT) — vẽ ở nến M15 đạt đỉnh, biết khi "
        "nến khung lớn xác nhận chốt"
    ),
    IctType.HTF_SWING_LOW: (
        "Đáy cấu trúc khung lớn (ITL H1/H4, tính trên nến khung lớn ĐÃ CHỐT) — vẽ ở nến M15 đạt đáy, biết khi "
        "nến khung lớn xác nhận chốt"
    ),
    IctType.HTF_FVG_UP: "FVG tăng khung lớn (H1/H4) — vùng PD array để đo phản ứng của giá",
    IctType.HTF_FVG_DOWN: "FVG giảm khung lớn (H1/H4) — vùng PD array để đo phản ứng của giá",
    IctType.HTF_BAR_DEGRADED: (
        "Nến khung lớn không dùng được (degraded): thiếu dữ liệu so với lịch phiên, kỳ đầu luồng thiếu nến, hoặc chỉ "
        "gồm nến nằm ngoài lịch — không được nằm trong cửa sổ swing/FVG, không tạo PDH/PDL/PWH/PWL"
    ),
    IctType.HTF_PERIOD_HIGH: "Mức theo kỳ: high của ngày (PDH) / tuần (PWH) vừa chốt — vùng thanh khoản phía trên",
    IctType.HTF_PERIOD_LOW: "Mức theo kỳ: low của ngày (PDL) / tuần (PWL) vừa chốt — vùng thanh khoản phía dưới",
    IctType.PD_RESPECT_UP: "FVG tăng khung lớn được tôn trọng (respect) — hàm ý tăng cho pd_bias",
    IctType.PD_RESPECT_DOWN: "FVG giảm khung lớn được tôn trọng (respect) — hàm ý giảm cho pd_bias",
    IctType.PD_DISRESPECT_UP: "FVG tăng khung lớn bị xuyên (disrespect) — hàm ý GIẢM cho pd_bias",
    IctType.PD_DISRESPECT_DOWN: "FVG giảm khung lớn bị xuyên (disrespect) — hàm ý TĂNG cho pd_bias",
    IctType.DOL_REACHED: (
        "Đích DOL (vùng thanh khoản gần nhất phía shift, tầng ≥ H1) đã bị lấy — DOL hết hiệu lực. Là mô tả, "
        "«tỷ lệ đạt DOL» chỉ là nhãn đánh giá"
    ),
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
    IctReason.DISP_RANGE_BODY: (
        "Biên độ nến ≥ k × ATR của nến trước và thân ≥ tỷ lệ tối thiểu của biên độ; chiều theo close so "
        "với open. Không xét nến đầu sau khoảng trống."
    ),
    IctReason.FVG_THREE_BAR: (
        "Ba nến liền nhau: low nến 3 > high nến 1 (tăng) hoặc high nến 3 < low nến 1 (giảm); biết khi nến 3 "
        "đóng. Ba nến không vắt qua khoảng trống."
    ),
    IctReason.FVG_FIRST_TOUCH: "Giá chạm mép gần của FVG lần đầu sau khi FVG được biết.",
    IctReason.FVG_FULL_FILL: "Giá đi tới mép xa của FVG — FVG đã lấp (chỉ là mốc mô tả, không phải tín hiệu).",
    IctReason.LIQ_TAKEN_THEN_CLOSE_BACK: (
        "Giá xuyên mức ≥ ngưỡng × ATR (đã lấy) rồi close quay lại phía trong mức trong cửa sổ W nến "
        "(tính cả nến lấy), không gặp khoảng trống."
    ),
    IctReason.LIQ_TAKEN_NO_RETURN: "Đã lấy thanh khoản, hết cửa sổ W nến mà close không quay lại.",
    IctReason.LIQ_GAP_IN_WINDOW: (
        "Gặp khoảng trống dữ liệu trong cửa sổ sau khi lấy — không xếp sweep hay run."
    ),
    IctReason.SHIFT_SWEEP_THEN_DISPLACEMENT: (
        "Sau một sweep: nến displacement ngược chiều trong cửa sổ, close vượt lại mức bị quét, cực trị "
        "của cú quét chưa bị vượt, không có khoảng trống. Là «shift có displacement» lúc phát hiện — "
        "chưa biết sẽ tiếp diễn hay thất bại."
    ),
    IctReason.SHIFT_FVG_SAME_DISPLACEMENT: (
        "FVG cùng chiều ngay sau shift, nến giữa của FVG chính là nến displacement của shift."
    ),
    IctReason.OF_RUN: (
        "Run (lấy thanh khoản, close không quay lại trong cửa sổ W nến) đặt chiều order flow khi đang "
        "chưa có hoặc chưa rõ. Order flow ở đây là MÔ TẢ theo thanh khoản (run + shift), không phải tín "
        "hiệu hay dự báo."
    ),
    IctReason.OF_SHIFT: (
        "Shift (quét thanh khoản rồi displacement ngược chiều) đặt chiều order flow — kể cả khi đang ngược "
        "chiều (lật thẳng). Mô tả theo thanh khoản, không phải tín hiệu hay dự báo."
    ),
    IctReason.OF_OPPOSITE_RUN: (
        "Run phía NGƯỢC với order flow đang có (vd đang tăng mà SSL bị run) → chưa rõ, không lật ngay; run "
        "hoặc shift kế tiếp đặt chiều. Mô tả, không phải tín hiệu."
    ),
    IctReason.OF_BOTH_SIDES: (
        "Trong cùng một nến có run/shift cả hai chiều → chưa rõ (không có sự kiện kích hoạt). Mô tả, không "
        "phải tín hiệu."
    ),
    IctReason.HTF_PIVOT_HIGH_L2: (
        "Trên nến khung lớn đã chốt: đỉnh ngắn hạn ở giữa cao hơn (nghiêm ngặt) đỉnh ngắn hạn liền trước và liền "
        "sau. Cửa sổ không chứa nến thiếu dữ liệu, không vắt qua bucket bị mất. Biết khi nến khung lớn xác nhận chốt."
    ),
    IctReason.HTF_PIVOT_LOW_L2: (
        "Trên nến khung lớn đã chốt: đáy ngắn hạn ở giữa thấp hơn (nghiêm ngặt) đáy ngắn hạn liền trước và liền "
        "sau. Cửa sổ không chứa nến thiếu dữ liệu, không vắt qua bucket bị mất. Biết khi nến khung lớn xác nhận chốt."
    ),
    IctReason.HTF_FVG_THREE_BAR: (
        "Ba nến khung lớn đã chốt, liền kề theo lịch (không vắt qua nghỉ phiên, cuối tuần, đóng sớm, bucket bị "
        "mất), không nến nào thiếu dữ liệu: low nến 3 > high nến 1 (tăng) hoặc high nến 3 < low nến 1 (giảm)."
    ),
    IctReason.HTF_COVERAGE_LOW: (
        "Số nến khung nhỏ trong nến khung lớn thấp hơn ngưỡng coverage so với số nến kỳ vọng theo lịch phiên "
        "khai báo — thiếu dữ liệu, không phải nghỉ lễ."
    ),
    IctReason.HTF_FIRST_PERIOD_PARTIAL: (
        "Kỳ đầu tiên của luồng dữ liệu thiếu nến (dataset/khoảng chạy bắt đầu giữa kỳ) — không đủ để dùng."
    ),
    IctReason.HTF_OUTSIDE_CALENDAR: (
        "Các nến khung nhỏ này nằm SAU mốc đóng theo lịch phiên khai báo của kỳ (dữ liệu khác lịch, vd có nến sau giờ "
        "đóng sớm ngày lễ) — kỳ đã chốt theo lịch; phần nối tiếp không được dùng làm nến khung lớn."
    ),
    IctReason.HTF_PERIOD_LEVEL: (
        "High/low của nến ngày/tuần (mốc 17:00 New York) đã chốt, không thiếu dữ liệu; là vùng thanh khoản từ nến "
        "sau lúc biết."
    ),
    IctReason.PD_RESPECT_STRICT: (
        "Sau khi chạm FVG khung lớn, close M15 rời mép gần ≥ respect_away_atr × ATR M15 trước khi xuyên mép xa "
        "(respect chặt — D6). Một kết quả mỗi vùng."
    ),
    IctReason.PD_RESPECT_LOOSE: (
        "Sau khi chạm FVG khung lớn, close M15 ra ngoài mép gần trước khi xuyên (respect lỏng — biến thể). Một kết "
        "quả mỗi vùng."
    ),
    IctReason.PD_DISRESPECT_FAR_EDGE: (
        "Sau khi chạm FVG khung lớn, close M15 vượt mép xa của vùng trước khi respect. Một kết quả mỗi vùng."
    ),
    IctReason.PD_DISRESPECT_CE: (
        "Sau khi chạm FVG khung lớn, close M15 vượt 50% vùng (CE) trước khi respect (biến thể CE). Một kết quả mỗi vùng."
    ),
    IctReason.DOL_TARGET_TAKEN: (
        "Vùng đích DOL (đặt sau shift gần nhất) bị lấy: xuyên mức ≥ ngưỡng × ATR. DOL hết hiệu lực."
    ),
}
