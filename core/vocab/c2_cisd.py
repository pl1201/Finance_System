"""Từ vựng sự kiện: C2 Sweep + CISD (``c2_cisd_research``).

Ghép vào ``core.types.StructureType`` / ``ReasonCode`` / ``*_TEXT_VI``.
"""
from __future__ import annotations


class C2CisdType:
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


class C2CisdReason:
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


#: Giải thích tiếng Việt cho từng loại sự kiện.
STRUCTURE_TEXT_VI: dict[str, str] = {
    C2CisdType.C2_CONFIRMED_UP: "C2 tăng (quét low H4 rồi đóng lại trên)",
    C2CisdType.C2_CONFIRMED_DOWN: "C2 giảm (quét high H4 rồi đóng lại dưới)",
    C2CisdType.CISD_LEVEL_SET_UP: "Mức CISD tăng mới",
    C2CisdType.CISD_LEVEL_SET_DOWN: "Mức CISD giảm mới",
    C2CisdType.EARLY_CISD_UP: "Early CISD tăng (ứng viên, chưa có C2)",
    C2CisdType.EARLY_CISD_DOWN: "Early CISD giảm (ứng viên, chưa có C2)",
    C2CisdType.CISD_CONFIRMED_UP: "CISD tăng xác nhận cho setup C2",
    C2CisdType.CISD_CONFIRMED_DOWN: "CISD giảm xác nhận cho setup C2",
    C2CisdType.SETUP_C4_INVALIDATED: "C4 không hợp lệ (setup chưa kết thúc)",
    C2CisdType.SETUP_INVALIDATED: "Setup C2 thất bại",
    C2CisdType.SETUP_EXPIRED: "Setup C2 hết hạn sau C4",
    C2CisdType.SETUP_SUPERSEDED: "Setup C2 bị setup mới cùng hướng thay",
    C2CisdType.SETUP_DATA_GAP: "Setup C2 dừng vì thiếu dữ liệu",
    C2CisdType.HTF_BUCKET_INCOMPLETE: "Kỳ H4 thiếu nến M15",
}

#: Giải thích tiếng Việt cho từng mã lý do (tooltip giao diện).
REASON_TEXT_VI: dict[str, str] = {
    C2CisdReason.C2_SWEEP_LOW_RECLAIM: (
        "C2 tăng: nến H4 vừa hoàn tất có low THẤP HƠN low nến H4 liền trước (C1) "
        "và đóng cửa TRỞ LẠI trên low C1. So sánh strict, không dung sai."
    ),
    C2CisdReason.C2_SWEEP_HIGH_RECLAIM: (
        "C2 giảm: nến H4 vừa hoàn tất có high CAO HƠN high C1 và đóng cửa "
        "TRỞ LẠI dưới high C1. So sánh strict, không dung sai."
    ),
    C2CisdReason.CISD_LEVEL_DIRECT: (
        "Mức CISD nhánh trực tiếp: nến tạo đáy/đỉnh mới của kỳ H4 là nến ngược "
        "màu (hoặc doji) ngay sau nến cùng màu/doji — mức = open của nến này."
    ),
    C2CisdReason.CISD_LEVEL_SCAN: (
        "Mức CISD nhánh tìm ngược 2–10 nến: lấy open của nến giảm (tăng) đầu "
        "chuỗi gần nhất, nâng/hạ theo open các nến cùng màu phía sau."
    ),
    C2CisdReason.CISD_LEVEL_FALLBACK: (
        "Mức CISD nhánh dự phòng: mức tìm được nằm sai phía so với open nến "
        "hiện tại nên thay bằng high/low (nến cùng hướng) hoặc open nến hiện tại."
    ),
    C2CisdReason.EARLY_CISD_RECLAIM_IN_SWEEP: (
        "Early CISD: close nến trước vượt mức CISD đang theo dõi trong lúc kỳ H4 "
        "hiện tại đã quét đáy/đỉnh kỳ trước. Mới là ứng viên — chưa phải setup C2."
    ),
    C2CisdReason.CISD_CLOSE_BEYOND_LEVEL: (
        "CISD xác nhận: close của nến TRƯỚC (close[1] như Pine) vượt mức CISD "
        "của setup trong C3/C4. Phát hiện ở nến hiện tại."
    ),
    C2CisdReason.CISD_ALREADY_RECLAIMED_AT_C2: (
        "CISD đã được reclaim trước khi C2 hoàn tất (early). Xác nhận cùng lúc "
        "setup được tạo; nến bằng chứng nằm trong hoặc trước C2."
    ),
    C2CisdReason.C4_CLOSE_BEYOND_TSPOT: (
        "C4 không hợp lệ: close nến trước vượt cạnh T-Spot C4 (giữa C3 và open "
        "đầu C4) theo hướng ngược setup. Chưa kết thúc setup."
    ),
    C2CisdReason.SETUP_EXTREME_BREACHED: (
        "Setup thất bại: giá phá cực trị C2 (low/high của nến quét). Ưu tiên "
        "trước xác nhận CISD trong cùng nến."
    ),
    C2CisdReason.SETUP_C4_FAIL_AFTER_CISD_IN_C4: (
        "Setup thất bại: CISD chỉ xác nhận trong C4 rồi C4 không hợp lệ. Sự kiện "
        "CISD đã phát vẫn giữ trong log (Pine xoá hình, lab không xoá lịch sử)."
    ),
    C2CisdReason.SETUP_C4_PERIOD_ENDED: (
        "Setup hết hạn: kỳ H4 C4 đã hoàn tất mà setup chưa bị phá."
    ),
    C2CisdReason.SETUP_REPLACED_BY_NEW_C2: (
        "Setup bị thay: C2 mới cùng hướng hoàn tất khi setup cũ còn theo dõi."
    ),
    C2CisdReason.SETUP_LTF_GAP: (
        "Setup dừng vì thiếu nến M15 (gap dữ liệu). Không phải giá phá setup."
    ),
    C2CisdReason.HTF_BUCKET_MISSING_BARS: (
        "Kỳ H4 không đủ nến M15 liên tiếp đúng mốc — không dùng làm C1/C2/C3/C4 "
        "và không tự bù nến."
    ),
}
