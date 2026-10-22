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
    # v0.5.0 — [E4] order block, [E6] OTE neo vào SHIFT (plan_ket_hop_ict_indicator.md §3.4)
    ORDER_BLOCK_UP = "ORDER_BLOCK_UP"
    ORDER_BLOCK_DOWN = "ORDER_BLOCK_DOWN"
    OB_TAP_UP = "OB_TAP_UP"
    OB_TAP_DOWN = "OB_TAP_DOWN"
    OB_FAIL_UP = "OB_FAIL_UP"
    OB_FAIL_DOWN = "OB_FAIL_DOWN"
    OB_EXPIRED = "OB_EXPIRED"
    OTE_ENTRY_UP = "OTE_ENTRY_UP"
    OTE_ENTRY_DOWN = "OTE_ENTRY_DOWN"
    OTE_FAIL_UP = "OTE_FAIL_UP"
    OTE_FAIL_DOWN = "OTE_FAIL_DOWN"
    OTE_EXPIRED = "OTE_EXPIRED"
    # v0.6.0 — [N] trạng thái mô tả của lớp nhận diện (thuat_toan_nhan_dien.md §5): phát khi trạng thái đổi
    STATE_TREND_UP = "STATE_TREND_UP"
    STATE_TREND_DOWN = "STATE_TREND_DOWN"
    STATE_RANGE = "STATE_RANGE"
    STATE_SQUEEZE = "STATE_SQUEEZE"
    STATE_CHOP = "STATE_CHOP"

    SHIFT_TYPES = (SHIFT_UP, SHIFT_DOWN)
    OB_TYPES = (ORDER_BLOCK_UP, ORDER_BLOCK_DOWN, OB_TAP_UP, OB_TAP_DOWN, OB_FAIL_UP, OB_FAIL_DOWN, OB_EXPIRED)
    OTE_TYPES = (OTE_ENTRY_UP, OTE_ENTRY_DOWN, OTE_FAIL_UP, OTE_FAIL_DOWN, OTE_EXPIRED)
    STATE_TYPES = (STATE_TREND_UP, STATE_TREND_DOWN, STATE_RANGE, STATE_SQUEEZE, STATE_CHOP)
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
    ) + OB_TYPES + OTE_TYPES + STATE_TYPES


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
    # v0.5.0
    OB_BODY_RUN = "OB_BODY_RUN"
    OB_LAST_CANDLE_WICK = "OB_LAST_CANDLE_WICK"
    OB_FIRST_TAP = "OB_FIRST_TAP"
    OB_CLOSE_BEYOND_FAR_EDGE = "OB_CLOSE_BEYOND_FAR_EDGE"
    OB_EXPIRED_TIME = "OB_EXPIRED_TIME"
    OB_EXPIRED_OPPOSITE_SHIFT = "OB_EXPIRED_OPPOSITE_SHIFT"
    OTE_RETRACE_ZONE = "OTE_RETRACE_ZONE"
    OTE_LEG_BROKEN = "OTE_LEG_BROKEN"
    OTE_EXPIRED_TIME = "OTE_EXPIRED_TIME"
    OTE_EXPIRED_SHIFT = "OTE_EXPIRED_SHIFT"
    STATE_ER_HIGH = "STATE_ER_HIGH"
    STATE_RANGE_EDGES = "STATE_RANGE_EDGES"
    STATE_SQUEEZE_CONVERGE = "STATE_SQUEEZE_CONVERGE"
    STATE_ER_LOW = "STATE_ER_LOW"
    # v0.9.0 — trạng thái v2
    STATE_TREND_STRUCTURE = "STATE_TREND_STRUCTURE"
    STATE_RANGE_BOX = "STATE_RANGE_BOX"
    STATE_CHOP_NO_BOX = "STATE_CHOP_NO_BOX"


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
    IctType.ORDER_BLOCK_UP: "Order block tăng: chuỗi nến giảm cuối trước displacement của SHIFT tăng (vùng dưới giá)",
    IctType.ORDER_BLOCK_DOWN: "Order block giảm: chuỗi nến tăng cuối trước displacement của SHIFT giảm (vùng trên giá)",
    IctType.OB_TAP_UP: "Giá chạm order block tăng lần đầu (close chưa thủng mép dưới)",
    IctType.OB_TAP_DOWN: "Giá chạm order block giảm lần đầu (close chưa vượt mép trên)",
    IctType.OB_FAIL_UP: "Order block tăng hỏng: lần chạm đầu close thủng mép dưới",
    IctType.OB_FAIL_DOWN: "Order block giảm hỏng: lần chạm đầu close vượt mép trên",
    IctType.OB_EXPIRED: "Order block hết hạn chưa được chạm (quá hạn, hoặc có SHIFT ngược chiều)",
    IctType.OTE_ENTRY_UP: "Giá hồi vào vùng OTE 62–79% của nhịp tăng sau SHIFT tăng",
    IctType.OTE_ENTRY_DOWN: "Giá hồi vào vùng OTE 62–79% của nhịp giảm sau SHIFT giảm",
    IctType.OTE_FAIL_UP: "Nhịp OTE tăng hỏng: giá thủng đáy nhịp (cực trị cú quét) trước khi vào vùng",
    IctType.OTE_FAIL_DOWN: "Nhịp OTE giảm hỏng: giá vượt đỉnh nhịp (cực trị cú quét) trước khi vào vùng",
    IctType.OTE_EXPIRED: "Nhịp OTE hết hạn chưa vào vùng (quá hạn, hoặc SHIFT mới thay nhịp)",
    IctType.STATE_TREND_UP: "Trạng thái: trend lên (giá đi một chiều lên — mô tả, không phải dự báo hướng)",
    IctType.STATE_TREND_DOWN: "Trạng thái: trend xuống (giá đi một chiều xuống — mô tả, không phải dự báo hướng)",
    IctType.STATE_RANGE: "Trạng thái: range biên rõ (đi ngang, mỗi biên bị chạm ≥ 2 lần)",
    IctType.STATE_SQUEEZE: "Trạng thái: sideway nén (đỉnh thấp dần, đáy cao dần, biên co lại)",
    IctType.STATE_CHOP: "Trạng thái: sideway nhiễu (đi ngang, không có biên rõ)",
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
    IctReason.OB_BODY_RUN: (
        "OB-T (gốc ICT): chuỗi nến ngược màu liên tiếp gần displacement nhất trong [nến lấy − ob_lui, d − 1], gộp một "
        "khối, vùng chỉ lấy thân. Biết khi SHIFT xác nhận; hiệu lực từ nến sau."
    ),
    IctReason.OB_LAST_CANDLE_WICK: (
        "OB-R: một nến ngược màu gần displacement nhất, vùng = cả râu (low–high). Biết khi SHIFT xác nhận."
    ),
    IctReason.OB_FIRST_TAP: "Lần đầu giá chạm mép gần của OB (đã biết từ nến trước) và close chưa vượt mép xa.",
    IctReason.OB_CLOSE_BEYOND_FAR_EDGE: "Lần chạm đầu có close vượt mép xa của OB → OB hỏng (ứng viên breaker).",
    IctReason.OB_EXPIRED_TIME: "Quá ob_han nến từ lúc tạo mà giá chưa chạm OB.",
    IctReason.OB_EXPIRED_OPPOSITE_SHIFT: "Có SHIFT ngược chiều trước khi giá chạm OB.",
    IctReason.OTE_RETRACE_ZONE: (
        "Giá hồi tới mức ote_tu (mặc định 62%) của nhịp từ cực trị cú quét tới đỉnh/đáy mới sau SHIFT; nhịp ≥ "
        "ote_nhip_min_atr × ATR. Đỉnh/đáy nhịp lấy tới nến trước (nhân quả)."
    ),
    IctReason.OTE_LEG_BROKEN: "Giá thủng gốc nhịp (cực trị cú quét của SHIFT) trước khi hồi vào vùng OTE.",
    IctReason.OTE_EXPIRED_TIME: "Quá ote_han nến từ SHIFT mà giá chưa hồi vào vùng OTE.",
    IctReason.OTE_EXPIRED_SHIFT: "SHIFT mới (ngược chiều, hoặc cùng chiều — thay nhịp) trước khi giá vào vùng OTE.",
    IctReason.STATE_ER_HIGH: (
        "Hiệu suất đường đi ER (|C_t − C_{t−W}| / tổng |ΔC|, W = 8 giờ) ≥ nd_er_nguong; chiều theo giá đóng cửa. Đổi "
        "trạng thái khi giữ đủ nd_giu_nen nến."
    ),
    IctReason.STATE_RANGE_EDGES: (
        "Trong cửa sổ 8–16 giờ: mỗi biên (high cao nhất / low thấp nhất) bị ≥ 2 swing pivot 2/2 chạm trong 0,3·ATR, "
        "cách nhau ≥ 1,5 giờ; rộng 1,5–5 ATR; ER < nd_er_nguong."
    ),
    IctReason.STATE_SQUEEZE_CONVERGE: (
        "Cửa sổ 12 giờ: ba đỉnh swing cuối thấp dần, ba đáy cao dần, bề rộng ¼ cuối ≤ 50% ¼ đầu; ER < nd_er_nguong."
    ),
    IctReason.STATE_ER_LOW: "ER < nd_er_nguong, không có biên rõ, không nén.",
    IctReason.STATE_TREND_STRUCTURE: (
        "Trạng thái v2: động lượng 8 giờ cùng chiều và cấu trúc swing cùng chiều (khung chạy hoặc H1) + lực (ER ≥ "
        "nd_er_vao hoặc ADX ≥ 20 cùng chiều DI), hoặc ER và ADX cùng mạnh, hoặc ER ≥ nd_er_nguong. Giữ tới CHoCH, thủng "
        "kênh 4 giờ hoặc lực tắt — lý do ở details.ly_do / details.thoat."
    ),
    IctReason.STATE_RANGE_BOX: (
        "Trạng thái v2: hộp Donchian 6 giờ rộng 1,5–4,5 ATR, ER < nd_er_nguong, mỗi biên được thăm lại ≥ 2 lần; giữ tới "
        "khi 2 close liên tiếp ra ngoài biên quá 0,25·ATR."
    ),
    IctReason.STATE_CHOP_NO_BOX: "Trạng thái v2: không trend, không hộp range.",
}
