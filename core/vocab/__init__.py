"""Từ vựng sự kiện theo họ thuật toán: loại sự kiện, mã lý do, câu giải thích tiếng Việt.

Mỗi họ một file (``swing``, ``baseline``, ``c2_cisd``, ``dc``). ``core.types`` ghép lại
thành ``StructureType``, ``ReasonCode``, ``STRUCTURE_TEXT_VI``, ``REASON_TEXT_VI`` —
mọi nơi vẫn import từ ``core.types`` như trước.

Thêm họ mới: tạo ``core/vocab/<họ>.py`` (lớp loại, lớp lý do, hai từ điển giải thích)
rồi thêm vào ``FAMILIES`` dưới đây. Mã phải duy nhất giữa các họ, trừ khi cùng
nghĩa (vd ``DC_GAP_BRIDGED`` vừa là loại vừa là lý do).
"""
from core.vocab import baseline, c2_cisd, dc, swing

#: Thứ tự ghép (cũng là thứ tự trong ``StructureType.ALL``).
FAMILIES = (swing, baseline, c2_cisd, dc)
