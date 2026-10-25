"""Bản tóm gọn trạng thái ở nến cuối cho trợ lý tổng hợp (LLM) — docs/plans/plan_tro_ly_tong_hop.md §3.

Hàm thuần, chỉ đọc output đã có của thuật toán tới nến cuối (``pending_state`` + sự kiện đã xác nhận) — nhân quả, không đổi
output nào. Chỉ lấy các mục ``SECTIONS`` của ``pending_state``, lược trường nội bộ (id, nguồn, danh sách chờ…), làm tròn số
theo số chữ số giá để mô hình đọc đúng và bộ kiểm số liệu so được. ``GLOSSARY_VI`` (cố định) giải nghĩa các mục cho mô hình;
mã loại sự kiện / lý do trong danh sách sự kiện gần đây được giải nghĩa từ ``core/vocab``.
"""
from __future__ import annotations

import re
from typing import Any, Optional, Sequence

from core.data.htf_stream import NY_TZ
from core.types import REASON_TEXT_VI, STRUCTURE_TEXT_VI, Bar, StructureEvent, StructureType

#: Mục của ``pending_state`` đưa vào bản tóm gọn (``GLOSSARY_VI`` nói về đúng các mục này) …
SECTIONS = ("lich_phien", "atr_hien_tai", "so_nen", "khoang_trong_truoc_nen_nay", "killzone", "order_flow", "cau_truc",
            "dealing_range", "thanh_khoan", "shift", "displacement_nen_nay", "fvg_chua_cham_gan_nhat", "fvg_dang_mo",
            "khung_lon", "pd", "dol", "order_block", "ote", "nhan_dien", "ghi_chu_vi")
#: … và mục bỏ (cờ, nguyên liệu nội bộ). Mục mới của ``pending_state`` phải vào một trong hai — test kiểm.
IGNORED = frozenset({"ict", "giai_doan", "cap_cau_truc", "pivot", "cap2", "cap3", "khoang_trong"})
#: Trường nội bộ trong các mục (định danh vùng, nguồn, mốc kỹ thuật) — mô hình không cần, chỉ tốn token.
DROP = frozenset({"id", "nguon", "biet_tai_nen", "tam_nen", "known_at", "nen_chot_gan_nhat", "ky_D", "ky_W",
                  "cua_so_bi_chan_gan_day", "cua_so_gan_day_nen"})
#: Id sự kiện nội bộ («ict:SHIFT_UP@1730>1730») — bỏ theo giá trị: cùng tên trường (fvg, su_kien) có nơi là cờ / số có nghĩa.
EVENT_ID = re.compile(r"^[a-z_]+:[A-Z0-9_]+@")
#: Loại sự kiện «nguyên liệu» quá dày / kỹ thuật — không đưa vào danh sách sự kiện gần đây.
NOISY = frozenset((StructureType.SWING_HIGH, StructureType.SWING_LOW, StructureType.FVG_TOUCHED, StructureType.FVG_FILLED,
                   StructureType.HTF_BAR_DEGRADED, StructureType.ICT_GAP))
RECENT = 30
MAX_LIST = 8                # chặn trên độ dài danh sách (dài nhất hiện có: 6 — mức + xác suất chạm, FVG khung lớn)

GLOSSARY_VI = """\
Dữ liệu là output của thuật toán ict_structure (lab nghiên cứu cấu trúc thị trường, nến đã đóng, nhân quả) ở NẾN CUỐI.
- nen_cuoi: nến cuối (khung = khung nến); mọi trường nen / tu_nen / xac_nhan_tai / r / d / nen_neo / han_nen là chỉ số
  nến cùng chuỗi; so_nen = số nến từ đó tới nay.
- order_flow: chiều đi của dòng lệnh theo thanh khoản (tăng / giảm / chưa rõ), đổi khi có run (lấy thanh khoản, close không
  quay lại) hoặc shift (quét thanh khoản rồi displacement ngược chiều). vung_cung_chieu / vung_nguoc_chieu = vùng thanh
  khoản mục tiêu / đe doạ.
- cau_truc: thứ tự đỉnh / đáy cấp 2 (ITH/ITL): HH-HL = tăng, LH-LL = giảm, lẫn lộn; muc_bao_ve = mức được bảo vệ.
- dealing_range: biên trên / dưới giữa đỉnh và đáy cấu trúc gần nhất; zone premium (nửa trên) / discount (nửa dưới) /
  equilibrium; range_pos 0–1 = vị trí giá trong biên.
- thanh_khoan: BSL (trên đỉnh) / SSL (dưới đáy) còn nguyên gần nhất mỗi phía (muc, tang = khung, so_lan_cham); sweep = quét
  rồi quay lại, run = lấy và đi tiếp.
- shift: sweep rồi displacement ngược chiều (dir up / down); displacement = nến thân lớn ≥ k×ATR; FVG = khoảng trống giá
  ba nến (lo–hi).
- khung_lon.ngu_canh: H1 / H4 (chỉ nến đã chốt): order (1 tăng, -1 giảm, 0 lẫn lộn), protected, zone, liq_above /
  liq_below; pd: phản ứng ở vùng PD array khung lớn (pd_bias); dol: đích thanh khoản (draw on liquidity) gần nhất.
- order_block / ote: OB đang mở; OTE = vùng hồi 62–79% của nhịp sau shift (dang_cho: vùng, điều kiện vào / hỏng).
- nhan_dien: lớp nhận diện. trang_thai (trend_len / trend_xuong / range / nhieu, kèm cờ nén); khoang.<tầm> = khoảng giá
  80% (lo80–hi80) và lõi 50% cho 1h / 4h tới — khả năng ≈80% cả đường giá nằm trong khoảng, KHÔNG nói lên hay xuống; muc =
  mức kèm xác suất bị chạm trong 1h / 4h (p_1h, p_4h); thoi_gian.con_giu = xác suất trạng thái còn giữ; pha_bien = xác suất
  phá biên range; diem_that = điểm thật đã chấm trong lần chạy (phu_80 = độ phủ thực tế của khoảng 80%; brier so với
  brier_b0 — nhỏ hơn B0 là tốt hơn mức nền; cham = điểm xác suất chạm theo loại mức).
- su_kien_gan_day: sự kiện đã xác nhận gần nhất, mỗi dòng: #nến xác nhận · giờ UTC · loại · giá · mã lý do;
  giai_nghia_ma = nghĩa của từng loại / mã lý do xuất hiện trong đó.
"""

SUMMARY_VI = """\
Tổng hợp trạng thái ở nến cuối theo đúng các mục, mỗi mục 1–3 gạch đầu dòng:
### Tóm tắt
### Khung lớn (H1 / H4, PD, DOL)
### Cấu trúc và order flow
### Thanh khoản gần
### Khoảng giá và xác suất (kèm điểm thật)
### Điều cần theo dõi (điều gì sẽ làm trạng thái / order flow đổi)
### Lưu ý (dữ liệu thiếu, độ tin cậy)"""


def _is_id(v: Any) -> bool:
    if isinstance(v, list):
        return bool(v) and all(_is_id(x) for x in v)
    return isinstance(v, str) and EVENT_ID.match(v) is not None


def _round(x: Any, nd: int) -> Any:
    if isinstance(x, float):
        return round(x, nd)
    if isinstance(x, dict):
        out = {k: _round(v, nd) for k, v in x.items() if k not in DROP and v is not None and not _is_id(v)}
        return {k: v for k, v in out.items() if v not in ({}, [])}
    if isinstance(x, (list, tuple)):
        return [_round(v, nd) for v in list(x)[-MAX_LIST:]]
    return x


def _recent(events: Sequence[StructureEvent]) -> list[StructureEvent]:
    """``RECENT`` sự kiện không ồn cuối cùng — duyệt ngược, dừng khi đủ (luồng live dài có thể hàng trăm nghìn sự kiện)."""
    out: list[StructureEvent] = []
    for e in reversed(events):
        if e.structure_type not in NOISY:
            out.append(e)
            if len(out) == RECENT:
                break
    return out[::-1]


def llm_context(pending: dict[str, Any], events: Sequence[StructureEvent], bar: Optional[Bar], *, symbol: str,
                timeframe: str, digits: int) -> Optional[dict[str, Any]]:
    """{"glossary", "summary", "data"} cho trợ lý tổng hợp ở nến ``bar`` (nến cuối); None khi chưa có nến. ``data``: thông
    tin nến, các mục ``SECTIONS`` của ``pending_state`` đã lược, sự kiện gần đây + nghĩa của mã."""
    if bar is None:
        return None
    nd = max(digits, 3)
    recent = _recent(events)
    codes: dict[str, str] = {}
    for e in recent:
        for code, texts in ((e.structure_type, STRUCTURE_TEXT_VI), (e.reason_code, REASON_TEXT_VI)):
            if code not in codes and texts.get(code):
                codes[code] = texts[code]
    trang_thai = _round({k: pending[k] for k in SECTIONS if k in pending}, nd)
    data = {
        "nen_cuoi": {
            "ma": symbol, "khung": timeframe, "chi_so": bar.index,
            "mo_luc_utc": bar.bar_time.strftime("%Y-%m-%d %H:%M"),
            "mo_luc_new_york": bar.bar_time.astimezone(NY_TZ).strftime("%Y-%m-%d %H:%M"),
            "dong_luc_utc": bar.close_time.strftime("%Y-%m-%d %H:%M"),
            "open": bar.open, "high": bar.high, "low": bar.low, "close": bar.close,
        },
        "trang_thai": trang_thai,
        "su_kien_gan_day": ["#%d · %s · %s · %s · %s" % (e.confirmed_bar_index, e.confirmed_at.strftime("%Y-%m-%d %H:%M"),
                                                         e.structure_type, ("%." + str(digits) + "f") % e.price,
                                                         e.reason_code) for e in recent],
        "giai_nghia_ma": codes,
    }
    return {"glossary": GLOSSARY_VI, "summary": SUMMARY_VI, "data": data}
