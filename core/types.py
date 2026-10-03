"""Kiểu dữ liệu dùng chung cho lõi thuật toán cấu trúc thị trường.

Lõi này KHÔNG phụ thuộc web framework, notebook hay MT5. Chỉ dùng thư viện
chuẩn Python để có thể tái sử dụng ở bất kỳ môi trường nào.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# --------------------------------------------------------------------------
# Timeframe
# --------------------------------------------------------------------------

#: Các timeframe được hỗ trợ và độ dài tương ứng (giây).
TIMEFRAME_SECONDS: dict[str, int] = {
    "M1": 60,
    "M5": 5 * 60,
    "M15": 15 * 60,
    "M30": 30 * 60,
    "H1": 60 * 60,
    "H4": 4 * 60 * 60,
    "D1": 24 * 60 * 60,
}


def timeframe_delta(timeframe: str) -> timedelta:
    """Độ dài một nến của timeframe."""
    tf = (timeframe or "").upper().strip()
    if tf not in TIMEFRAME_SECONDS:
        raise ValueError(
            "Timeframe khong ho tro: %r. Ho tro: %s"
            % (timeframe, ", ".join(TIMEFRAME_SECONDS))
        )
    return timedelta(seconds=TIMEFRAME_SECONDS[tf])


#: Quy ước timestamp của nến: mốc mở nến hay mốc đóng nến.
TIMESTAMP_CONVENTIONS = ("open", "close")


# --------------------------------------------------------------------------
# Bar
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Bar:
    """Một nến ĐÃ ĐÓNG.

    ``bar_time``  : timestamp của nến theo quy ước dataset (UTC, tz-aware).
    ``close_time``: thời điểm nến đóng (UTC, tz-aware). Với quy ước ``open``
                    thì ``close_time = bar_time + timeframe``; với quy ước
                    ``close`` thì ``close_time = bar_time``.

    Lõi thuật toán luôn dùng ``close_time`` làm mốc "thời điểm thông tin
    khả dụng", không dùng ``bar_time``.
    """

    index: int
    bar_time: datetime
    close_time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def is_valid_ohlc(self) -> bool:
        return (
            self.low <= self.open <= self.high
            and self.low <= self.close <= self.high
            and self.low <= self.high
        )


def build_bars(
    rows: list[dict[str, Any]],
    timeframe: str,
    timestamp_convention: str,
) -> list[Bar]:
    """Dựng danh sách ``Bar`` từ các dict đã chuẩn hoá (``bar_time`` là UTC)."""
    if timestamp_convention not in TIMESTAMP_CONVENTIONS:
        raise ValueError(
            "timestamp_convention phai la 'open' hoac 'close', nhan %r"
            % (timestamp_convention,)
        )
    delta = timeframe_delta(timeframe)
    bars: list[Bar] = []
    for i, r in enumerate(rows):
        bt: datetime = r["bar_time"]
        if bt.tzinfo is None:
            bt = bt.replace(tzinfo=timezone.utc)
        ct = bt + delta if timestamp_convention == "open" else bt
        bars.append(
            Bar(
                index=i,
                bar_time=bt,
                close_time=ct,
                open=float(r["open"]),
                high=float(r["high"]),
                low=float(r["low"]),
                close=float(r["close"]),
                volume=float(r.get("volume") or 0.0),
            )
        )
    return bars


# --------------------------------------------------------------------------
# Structure event
# --------------------------------------------------------------------------


class StructureType:
    """Từ điển loại cấu trúc do thuật toán swing pivot sinh ra."""

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
    BASELINE_UP = "BASELINE_UP"
    BASELINE_DOWN = "BASELINE_DOWN"
    BASELINE_RANGE = "BASELINE_RANGE"
    BASELINE_UNCERTAIN = "BASELINE_UNCERTAIN"
    HMM_STATE_CHANGE = "HMM_STATE_CHANGE"
    # --- c2_cisd_research (CantoLab C2 Sweep + CISD, bản closed-bar) ---
    C2_CONFIRMED_UP = "C2_CONFIRMED_UP"
    C2_CONFIRMED_DOWN = "C2_CONFIRMED_DOWN"
    CISD_LEVEL_SET_UP = "CISD_LEVEL_SET_UP"
    CISD_LEVEL_SET_DOWN = "CISD_LEVEL_SET_DOWN"
    EARLY_CISD_UP = "EARLY_CISD_UP"
    EARLY_CISD_DOWN = "EARLY_CISD_DOWN"
    CISD_CONFIRMED_UP = "CISD_CONFIRMED_UP"
    CISD_CONFIRMED_DOWN = "CISD_CONFIRMED_DOWN"
    SETUP_C4_INVALIDATED = "SETUP_C4_INVALIDATED"
    SETUP_INVALIDATED = "SETUP_INVALIDATED"
    SETUP_EXPIRED = "SETUP_EXPIRED"
    SETUP_SUPERSEDED = "SETUP_SUPERSEDED"
    SETUP_DATA_GAP = "SETUP_DATA_GAP"
    HTF_BUCKET_INCOMPLETE = "HTF_BUCKET_INCOMPLETE"

    C2_CISD_TYPES = (
        C2_CONFIRMED_UP, C2_CONFIRMED_DOWN,
        CISD_LEVEL_SET_UP, CISD_LEVEL_SET_DOWN,
        EARLY_CISD_UP, EARLY_CISD_DOWN,
        CISD_CONFIRMED_UP, CISD_CONFIRMED_DOWN,
        SETUP_C4_INVALIDATED, SETUP_INVALIDATED, SETUP_EXPIRED,
        SETUP_SUPERSEDED, SETUP_DATA_GAP, HTF_BUCKET_INCOMPLETE,
    )

    # --- dc_atr_structure (Directional Change theo close + phân loại regime) ---
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

    ALL = (
        SWING_HIGH, SWING_LOW, SWING_HIGH_L2, SWING_LOW_L2,
        HH, LH, EQH, HL, LL, EQL,
        BOS_UP, BOS_DOWN, BOS_INTERNAL_UP, BOS_INTERNAL_DOWN,
        CHOCH_UP, CHOCH_DOWN,
        BASELINE_UP, BASELINE_DOWN, BASELINE_RANGE, BASELINE_UNCERTAIN,
        HMM_STATE_CHANGE,
    ) + C2_CISD_TYPES + DC_TYPES


class ReasonCode:
    """Mã lý do để truy vết vì sao một sự kiện được sinh ra."""

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
    BASELINE_RULE_CROSS = "BASELINE_RULE_CROSS"
    HMM_FILTERED_STATE_CHANGE = "HMM_FILTERED_STATE_CHANGE"
    PIVOT_HIGH_L2 = "PIVOT_HIGH_L2"
    PIVOT_LOW_L2 = "PIVOT_LOW_L2"
    SEQ_HIGHER_HIGH_L2 = "SEQ_HIGHER_HIGH_L2"
    SEQ_LOWER_HIGH_L2 = "SEQ_LOWER_HIGH_L2"
    SEQ_EQUAL_HIGH_L2 = "SEQ_EQUAL_HIGH_L2"
    SEQ_HIGHER_LOW_L2 = "SEQ_HIGHER_LOW_L2"
    SEQ_LOWER_LOW_L2 = "SEQ_LOWER_LOW_L2"
    SEQ_EQUAL_LOW_L2 = "SEQ_EQUAL_LOW_L2"
    # --- c2_cisd_research ---
    C2_SWEEP_LOW_RECLAIM = "C2_SWEEP_LOW_RECLAIM"
    C2_SWEEP_HIGH_RECLAIM = "C2_SWEEP_HIGH_RECLAIM"
    CISD_LEVEL_DIRECT = "CISD_LEVEL_DIRECT"
    CISD_LEVEL_SCAN = "CISD_LEVEL_SCAN"
    CISD_LEVEL_FALLBACK = "CISD_LEVEL_FALLBACK"
    EARLY_CISD_RECLAIM_IN_SWEEP = "EARLY_CISD_RECLAIM_IN_SWEEP"
    CISD_CLOSE_BEYOND_LEVEL = "CISD_CLOSE_BEYOND_LEVEL"
    CISD_ALREADY_RECLAIMED_AT_C2 = "CISD_ALREADY_RECLAIMED_AT_C2"
    C4_CLOSE_BEYOND_TSPOT = "C4_CLOSE_BEYOND_TSPOT"
    SETUP_EXTREME_BREACHED = "SETUP_EXTREME_BREACHED"
    SETUP_C4_FAIL_AFTER_CISD_IN_C4 = "SETUP_C4_FAIL_AFTER_CISD_IN_C4"
    SETUP_C4_PERIOD_ENDED = "SETUP_C4_PERIOD_ENDED"
    SETUP_REPLACED_BY_NEW_C2 = "SETUP_REPLACED_BY_NEW_C2"
    SETUP_LTF_GAP = "SETUP_LTF_GAP"
    HTF_BUCKET_MISSING_BARS = "HTF_BUCKET_MISSING_BARS"
    # --- dc_atr_structure ---
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


#: Giải thích tiếng Việt cho từng mã lý do (dùng cho tooltip giao diện).
REASON_TEXT_VI: dict[str, str] = {
    ReasonCode.PIVOT_HIGH_STRICT: (
        "High của nến pivot LỚN HƠN TUYỆT ĐỐI mọi high trong cửa sổ trái/phải. "
        "Trường hợp bằng nhau không được nhận là pivot ở phiên bản này."
    ),
    ReasonCode.PIVOT_LOW_STRICT: (
        "Low của nến pivot NHỎ HƠN TUYỆT ĐỐI mọi low trong cửa sổ trái/phải. "
        "Trường hợp bằng nhau không được nhận là pivot ở phiên bản này."
    ),
    ReasonCode.SEQ_HIGHER_HIGH: (
        "Swing high đã xác nhận CAO HƠN swing high đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_LOWER_HIGH: (
        "Swing high đã xác nhận THẤP HƠN swing high đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_EQUAL_HIGH: (
        "Hai swing high liên tiếp BẰNG NHAU trong dung sai đã khai báo. "
        "Gắn nhãn riêng EQH, không ép thành HH hoặc LH."
    ),
    ReasonCode.SEQ_HIGHER_LOW: (
        "Swing low đã xác nhận CAO HƠN swing low đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_LOWER_LOW: (
        "Swing low đã xác nhận THẤP HƠN swing low đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_EQUAL_LOW: (
        "Hai swing low liên tiếp BẰNG NHAU trong dung sai đã khai báo. "
        "Gắn nhãn riêng EQL, không ép thành HL hoặc LL."
    ),
    ReasonCode.BOS_CLOSE_ABOVE_SWING_HIGH: (
        "Giá ĐÓNG CỬA vượt lên trên mức swing high đã xác nhận (cộng biên phá vỡ). "
        "Mỗi mức chỉ phát tín hiệu một lần."
    ),
    ReasonCode.BOS_CLOSE_BELOW_SWING_LOW: (
        "Giá ĐÓNG CỬA xuống dưới mức swing low đã xác nhận (trừ biên phá vỡ). "
        "Mỗi mức chỉ phát tín hiệu một lần. Đây là BOS chính hoặc BOS khi chưa có bias."
    ),
    ReasonCode.BOS_INTERNAL_CLOSE_ABOVE: (
        "Giá đóng cửa vượt đỉnh swing nội bộ (không phải mức high cực trị còn nguyên). "
        "Chưa phá mức chính."
    ),
    ReasonCode.BOS_INTERNAL_CLOSE_BELOW: (
        "Giá đóng cửa thủng đáy swing nội bộ (không phải mức low cực trị còn nguyên). "
        "Chưa phá mức chính."
    ),
    ReasonCode.CHOCH_CLOSE_ABOVE_SWING_HIGH: (
        "CHoCH tăng: giá đóng cửa phá mức swing high CHÍNH trong lúc bias đang giảm. "
        "Bias chuyển sang tăng sau nến này."
    ),
    ReasonCode.CHOCH_CLOSE_BELOW_SWING_LOW: (
        "CHoCH giảm: giá đóng cửa phá mức swing low CHÍNH trong lúc bias đang tăng. "
        "Bias chuyển sang giảm sau nến này."
    ),
    ReasonCode.BASELINE_RULE_CROSS: (
        "Phân loại baseline chỉ báo thay đổi: độ dốc SMA chuẩn hoá ATR, ADX và "
        "bề rộng vùng giá (Donchian/ATR) thỏa bộ ngưỡng đã khai báo."
    ),
    ReasonCode.HMM_FILTERED_STATE_CHANGE: (
        "State MAP của bộ lọc HMM online (bước forward) thay đổi so với nến trước. "
        "Không dùng smoothing/Viterbi trên toàn chuỗi."
    ),
    ReasonCode.PIVOT_HIGH_L2: (
        "Đỉnh cấp 2: pivot cấp 1 giữa cao hơn tuyệt đối hai đỉnh cấp 1 liền kề "
        "trên chuỗi pivot (không phải ba nến liên tiếp). Chỉ xác nhận khi đỉnh "
        "cấp 1 bên phải đã xác nhận — không gắn về lúc đỉnh giữa hình thành."
    ),
    ReasonCode.PIVOT_LOW_L2: (
        "Đáy cấp 2: pivot cấp 1 giữa thấp hơn tuyệt đối hai đáy cấp 1 liền kề "
        "trên chuỗi pivot. Chỉ xác nhận khi đáy cấp 1 bên phải đã xác nhận."
    ),
    ReasonCode.SEQ_HIGHER_HIGH_L2: (
        "Đỉnh cấp 2 vừa xác nhận CAO HƠN đỉnh cấp 2 đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_LOWER_HIGH_L2: (
        "Đỉnh cấp 2 vừa xác nhận THẤP HƠN đỉnh cấp 2 đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_EQUAL_HIGH_L2: (
        "Hai đỉnh cấp 2 liên tiếp BẰNG NHAU trong dung sai đã khai báo. "
        "Gắn nhãn riêng EQH, không ép thành HH hoặc LH."
    ),
    ReasonCode.SEQ_HIGHER_LOW_L2: (
        "Đáy cấp 2 vừa xác nhận CAO HƠN đáy cấp 2 đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_LOWER_LOW_L2: (
        "Đáy cấp 2 vừa xác nhận THẤP HƠN đáy cấp 2 đã xác nhận liền trước."
    ),
    ReasonCode.SEQ_EQUAL_LOW_L2: (
        "Hai đáy cấp 2 liên tiếp BẰNG NHAU trong dung sai đã khai báo. "
        "Gắn nhãn riêng EQL, không ép thành HL hoặc LL."
    ),
    ReasonCode.C2_SWEEP_LOW_RECLAIM: (
        "C2 tăng: nến H4 vừa hoàn tất có low THẤP HƠN low nến H4 liền trước (C1) "
        "và đóng cửa TRỞ LẠI trên low C1. So sánh strict, không dung sai."
    ),
    ReasonCode.C2_SWEEP_HIGH_RECLAIM: (
        "C2 giảm: nến H4 vừa hoàn tất có high CAO HƠN high C1 và đóng cửa "
        "TRỞ LẠI dưới high C1. So sánh strict, không dung sai."
    ),
    ReasonCode.CISD_LEVEL_DIRECT: (
        "Mức CISD nhánh trực tiếp: nến tạo đáy/đỉnh mới của kỳ H4 là nến ngược "
        "màu (hoặc doji) ngay sau nến cùng màu/doji — mức = open của nến này."
    ),
    ReasonCode.CISD_LEVEL_SCAN: (
        "Mức CISD nhánh tìm ngược 2–10 nến: lấy open của nến giảm (tăng) đầu "
        "chuỗi gần nhất, nâng/hạ theo open các nến cùng màu phía sau."
    ),
    ReasonCode.CISD_LEVEL_FALLBACK: (
        "Mức CISD nhánh dự phòng: mức tìm được nằm sai phía so với open nến "
        "hiện tại nên thay bằng high/low (nến cùng hướng) hoặc open nến hiện tại."
    ),
    ReasonCode.EARLY_CISD_RECLAIM_IN_SWEEP: (
        "Early CISD: close nến trước vượt mức CISD đang theo dõi trong lúc kỳ H4 "
        "hiện tại đã quét đáy/đỉnh kỳ trước. Mới là ứng viên — chưa phải setup C2."
    ),
    ReasonCode.CISD_CLOSE_BEYOND_LEVEL: (
        "CISD xác nhận: close của nến TRƯỚC (close[1] như Pine) vượt mức CISD "
        "của setup trong C3/C4. Phát hiện ở nến hiện tại."
    ),
    ReasonCode.CISD_ALREADY_RECLAIMED_AT_C2: (
        "CISD đã được reclaim trước khi C2 hoàn tất (early). Xác nhận cùng lúc "
        "setup được tạo; nến bằng chứng nằm trong hoặc trước C2."
    ),
    ReasonCode.C4_CLOSE_BEYOND_TSPOT: (
        "C4 không hợp lệ: close nến trước vượt cạnh T-Spot C4 (giữa C3 và open "
        "đầu C4) theo hướng ngược setup. Chưa kết thúc setup."
    ),
    ReasonCode.SETUP_EXTREME_BREACHED: (
        "Setup thất bại: giá phá cực trị C2 (low/high của nến quét). Ưu tiên "
        "trước xác nhận CISD trong cùng nến."
    ),
    ReasonCode.SETUP_C4_FAIL_AFTER_CISD_IN_C4: (
        "Setup thất bại: CISD chỉ xác nhận trong C4 rồi C4 không hợp lệ. Sự kiện "
        "CISD đã phát vẫn giữ trong log (Pine xoá hình, lab không xoá lịch sử)."
    ),
    ReasonCode.SETUP_C4_PERIOD_ENDED: (
        "Setup hết hạn: kỳ H4 C4 đã hoàn tất mà setup chưa bị phá."
    ),
    ReasonCode.SETUP_REPLACED_BY_NEW_C2: (
        "Setup bị thay: C2 mới cùng hướng hoàn tất khi setup cũ còn theo dõi."
    ),
    ReasonCode.SETUP_LTF_GAP: (
        "Setup dừng vì thiếu nến M15 (gap dữ liệu). Không phải giá phá setup."
    ),
    ReasonCode.HTF_BUCKET_MISSING_BARS: (
        "Kỳ H4 không đủ nến M15 liên tiếp đúng mốc — không dùng làm C1/C2/C3/C4 "
        "và không tự bù nến."
    ),
    ReasonCode.DC_CLOSE_REVERSAL_FROM_HIGH: (
        "Đỉnh theo CLOSE (Directional Change): close hiện tại đã giảm ít nhất một "
        "ngưỡng Δ so với close cao nhất của ứng viên. Δ khoá tại nến cực trị "
        "(k × ATR hoặc % close). Chạm đúng ngưỡng là đạt. Không phải đỉnh theo wick."
    ),
    ReasonCode.DC_CLOSE_REVERSAL_FROM_LOW: (
        "Đáy theo CLOSE (Directional Change): close hiện tại đã tăng ít nhất một "
        "ngưỡng Δ so với close thấp nhất của ứng viên. Δ khoá tại nến cực trị "
        "(k × ATR hoặc % close). Chạm đúng ngưỡng là đạt. Không phải đáy theo wick."
    ),
    ReasonCode.DC_TREND_HH_HL: (
        "Định nghĩa vận hành của lab: đỉnh DC gần nhất là HH và đáy DC gần nhất là HL "
        "(so với pivot cùng loại liền trước, dung sai khoá lúc xác nhận). Không phải dự báo."
    ),
    ReasonCode.DC_TREND_LH_LL: (
        "Định nghĩa vận hành của lab: đỉnh DC gần nhất là LH và đáy DC gần nhất là LL. "
        "Không phải dự báo."
    ),
    ReasonCode.DC_NO_TREND_NO_RANGE: (
        "Chưa rõ: thiếu pivot để so sánh, nhãn mâu thuẫn (vd HH + LL) hoặc có EQ, và "
        "cũng chưa đủ điều kiện Range. Không gán Range chỉ vì không thấy trend."
    ),
    ReasonCode.DC_RANGE_CLUSTERS: (
        "Range: m đỉnh và m đáy DC gần nhất tạo hai cụm hẹp (≤ dung sai × ATR), tách "
        "nhau, đủ rộng và close hiện tại nằm giữa hai biên. Biên và buffer khoá từ lúc này."
    ),
    ReasonCode.DC_RANGE_CLOSE_BREAK_UP: (
        "Range kết thúc: CLOSE vượt biên trên + buffer đã khoá. Wick vượt biên không đủ. "
        "Trạng thái về «chưa rõ» chờ pivot mới ở nến sau."
    ),
    ReasonCode.DC_RANGE_CLOSE_BREAK_DOWN: (
        "Range kết thúc: CLOSE thủng biên dưới − buffer đã khoá. Wick không đủ. "
        "Trạng thái về «chưa rõ» chờ pivot mới ở nến sau."
    ),
    ReasonCode.DC_GAP_RESET: (
        "Gap dữ liệu (khoảng cách nến khác bước timeframe, gồm nghỉ phiên/cuối tuần): "
        "kết thúc segment, bỏ ứng viên, ATR, lịch sử pivot/range; warm-up lại. Log cũ giữ nguyên."
    ),
    ReasonCode.DC_GAP_BRIDGED: (
        "Gap ngắn được NỐI (gap_policy=bridge_short): không reset segment; giữ ứng viên, "
        "ngưỡng đã khoá, ATR và lịch sử pivot/range. TR nến đầu sau gap tính với close "
        "trước gap nên gồm cả bước nhảy giá qua gap. Chỉ là ghi nhận dữ liệu."
    ),
}

#: Giải thích tiếng Việt cho từng loại cấu trúc.
STRUCTURE_TEXT_VI: dict[str, str] = {
    StructureType.SWING_HIGH: "Đỉnh swing đã xác nhận",
    StructureType.SWING_LOW: "Đáy swing đã xác nhận",
    StructureType.SWING_HIGH_L2: "Đỉnh swing cấp 2 (lọc trên chuỗi đỉnh cấp 1)",
    StructureType.SWING_LOW_L2: "Đáy swing cấp 2 (lọc trên chuỗi đáy cấp 1)",
    StructureType.HH: "Đỉnh cao hơn (Higher High)",
    StructureType.LH: "Đỉnh thấp hơn (Lower High)",
    StructureType.EQH: "Đỉnh bằng nhau (Equal High)",
    StructureType.HL: "Đáy cao hơn (Higher Low)",
    StructureType.LL: "Đáy thấp hơn (Lower Low)",
    StructureType.EQL: "Đáy bằng nhau (Equal Low)",
    StructureType.BOS_UP: "Phá vỡ cấu trúc chính lên (BOS tăng)",
    StructureType.BOS_DOWN: "Phá vỡ cấu trúc chính xuống (BOS giảm)",
    StructureType.BOS_INTERNAL_UP: "BOS nội bộ lên",
    StructureType.BOS_INTERNAL_DOWN: "BOS nội bộ xuống",
    StructureType.CHOCH_UP: "Đổi hướng cấu trúc lên (CHoCH tăng)",
    StructureType.CHOCH_DOWN: "Đổi hướng cấu trúc xuống (CHoCH giảm)",
    StructureType.BASELINE_UP: "Baseline chỉ báo: hướng tăng",
    StructureType.BASELINE_DOWN: "Baseline chỉ báo: hướng giảm",
    StructureType.BASELINE_RANGE: "Baseline chỉ báo: biên độ hẹp / ADX yếu",
    StructureType.BASELINE_UNCERTAIN: "Baseline chỉ báo: chưa đủ điều kiện",
    StructureType.HMM_STATE_CHANGE: "HMM online: state lọc (forward) đổi",
    StructureType.C2_CONFIRMED_UP: "C2 tăng (quét low H4 rồi đóng lại trên)",
    StructureType.C2_CONFIRMED_DOWN: "C2 giảm (quét high H4 rồi đóng lại dưới)",
    StructureType.CISD_LEVEL_SET_UP: "Mức CISD tăng mới",
    StructureType.CISD_LEVEL_SET_DOWN: "Mức CISD giảm mới",
    StructureType.EARLY_CISD_UP: "Early CISD tăng (ứng viên, chưa có C2)",
    StructureType.EARLY_CISD_DOWN: "Early CISD giảm (ứng viên, chưa có C2)",
    StructureType.CISD_CONFIRMED_UP: "CISD tăng xác nhận cho setup C2",
    StructureType.CISD_CONFIRMED_DOWN: "CISD giảm xác nhận cho setup C2",
    StructureType.SETUP_C4_INVALIDATED: "C4 không hợp lệ (setup chưa kết thúc)",
    StructureType.SETUP_INVALIDATED: "Setup C2 thất bại",
    StructureType.SETUP_EXPIRED: "Setup C2 hết hạn sau C4",
    StructureType.SETUP_SUPERSEDED: "Setup C2 bị setup mới cùng hướng thay",
    StructureType.SETUP_DATA_GAP: "Setup C2 dừng vì thiếu dữ liệu",
    StructureType.HTF_BUCKET_INCOMPLETE: "Kỳ H4 thiếu nến M15",
    StructureType.DC_HIGH: "Đỉnh DC theo close (đã xác nhận)",
    StructureType.DC_LOW: "Đáy DC theo close (đã xác nhận)",
    StructureType.DC_REGIME_UP: "Trạng thái → Tăng (theo swing DC đã xác nhận)",
    StructureType.DC_REGIME_DOWN: "Trạng thái → Giảm (theo swing DC đã xác nhận)",
    StructureType.DC_REGIME_UNKNOWN: "Trạng thái → Chưa rõ",
    StructureType.DC_RANGE_START: "Range bắt đầu (biên khoá)",
    StructureType.DC_RANGE_EXIT: "Range kết thúc do close phá biên",
    StructureType.DC_SEGMENT_GAP: "Gap dữ liệu — reset segment DC",
    StructureType.DC_GAP_BRIDGED: "Gap ngắn — được nối, không reset",
}


@dataclass
class StructureEvent:
    """Một sự kiện cấu trúc do thuật toán sinh ra.

    Phân biệt ba mốc thời gian:

    * ``event_time``       : timestamp của NẾN chứa cấu trúc (theo quy ước dataset).
    * ``event_close_time`` : thời điểm nến đó ĐÓNG.
    * ``confirmed_at``     : thời điểm thuật toán THỰC SỰ xác nhận được cấu trúc
      (= ``close_time`` của nến xác nhận). Marker chỉ được phép xuất hiện trong
      chế độ replay từ mốc này trở đi.
    """

    event_id: str
    structure_type: str
    price: float

    event_bar_index: int
    event_time: datetime
    event_close_time: datetime

    confirmed_bar_index: int
    confirmed_at: datetime

    algorithm: str
    algorithm_version: str
    reason_code: str

    direction: Optional[str] = None            # "up" | "down" | None
    reference_event_id: Optional[str] = None
    details: dict[str, Any] = field(default_factory=dict)

    @property
    def confirmation_lag_bars(self) -> int:
        return self.confirmed_bar_index - self.event_bar_index

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["event_time"] = self.event_time.isoformat()
        d["event_close_time"] = self.event_close_time.isoformat()
        d["confirmed_at"] = self.confirmed_at.isoformat()
        d["confirmation_lag_bars"] = self.confirmation_lag_bars
        d["structure_text_vi"] = STRUCTURE_TEXT_VI.get(
            self.structure_type, self.structure_type
        )
        d["reason_text_vi"] = REASON_TEXT_VI.get(self.reason_code, "")
        return d


# --------------------------------------------------------------------------
# Trạng thái dữ liệu
# --------------------------------------------------------------------------

DATA_STATUS_OK = "OK"
DATA_STATUS_WARMUP = "WARMUP_INSUFFICIENT"
DATA_STATUS_INVALID = "DATA_INVALID"
