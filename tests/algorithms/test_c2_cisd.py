"""Fixture tính tay + kiểm tra nhân quả cho ``c2_cisd_research``.

Timeline ví dụ được mô tả trong ``docs/algorithms/thuat_toan_c2_cisd.md`` mục 6. Nến M15
bắt đầu 2024-01-01 00:00 UTC (đầu kỳ H4 theo UTC epoch). Chỉ số nến:

* kỳ 0 (C1)  : nến 0–15   (00:00–04:00)
* kỳ 1 (C2)  : nến 16–31  (04:00–08:00)
* kỳ 2 (C3)  : nến 32–47  (08:00–12:00)
* kỳ 3 (C4)  : nến 48–63  (12:00–16:00)
"""
from __future__ import annotations

import copy
import random
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from core.algorithms.c2_cisd_research import C2CisdResearchAlgorithm
from core.data.htf_stream import HtfAggregator
from core.engine import ReplaySession, run_algorithm
from core.types import Bar, StructureType as T
from tests.helpers import make_bars

START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def rep(bar, n):
    return [bar] * n


def mirror(rows):
    """Lật giá quanh 100: nến tăng ↔ giảm, low ↔ high. Dùng cho test hướng giảm."""
    return [(200 - o, 200 - l, 200 - h, 200 - c) for (o, h, l, c) in rows]


def m15(rows, start=START):
    return make_bars(rows, timeframe="M15", start=start)


def run(bars, **params):
    return C2CisdResearchAlgorithm(**params).run(bars)


def sig(events, types=None):
    return [
        (e.structure_type, e.event_bar_index, e.confirmed_bar_index, round(e.price, 6))
        for e in events
        if types is None or e.structure_type in types
    ]


C1 = rep((100.0, 100.5, 99.5, 100.2), 16)
C2_BULL = rep((100.0, 100.5, 99.6, 100.2), 5) + [(100.2, 100.3, 99.0, 99.3)] + rep((99.4, 99.9, 99.2, 99.8), 10)
C3_CONFIRM = [(99.8, 100.0, 99.5, 99.9), (99.9, 100.6, 99.8, 100.5)] + rep((100.5, 100.7, 100.3, 100.6), 14)
C4_CALM = rep((100.6, 100.8, 100.4, 100.7), 16)
BASIC = C1 + C2_BULL + C3_CONFIRM + C4_CALM

SETUP_TYPES = {
    T.C2_CONFIRMED_UP, T.C2_CONFIRMED_DOWN, T.CISD_CONFIRMED_UP, T.CISD_CONFIRMED_DOWN,
    T.SETUP_INVALIDATED, T.SETUP_C4_INVALIDATED, T.SETUP_EXPIRED, T.SETUP_SUPERSEDED,
    T.SETUP_DATA_GAP, T.EARLY_CISD_UP, T.EARLY_CISD_DOWN, T.CISD_LEVEL_SET_UP,
    T.CISD_LEVEL_SET_DOWN, T.HTF_BUCKET_INCOMPLETE,
}


# ---------------------------------------------------------------------------
# Timeline tính tay
# ---------------------------------------------------------------------------


def test_timeline_tang_c2_c3_c4_het_han():
    ev = run(m15(BASIC))
    assert sig(ev) == [
        (T.CISD_LEVEL_SET_UP, 21, 21, 100.2),     # nhánh trực tiếp: nến 21 giảm sau nến 20 tăng
        (T.C2_CONFIRMED_UP, 21, 31, 99.0),        # biết lúc nến 31 (cuối C2) đóng
        (T.CISD_CONFIRMED_UP, 33, 34, 100.2),     # close[33] > 100.2, phát hiện ở nến 34
        (T.SETUP_EXPIRED, 63, 63, 99.0),          # C4 đóng xong
    ]
    c2 = ev[1]
    assert c2.confirmed_at == datetime(2024, 1, 1, 8, 0, tzinfo=timezone.utc)
    assert c2.details["setup_id"] == "up-20240101T0400"
    assert c2.details["sweep_from"] == 99.5 and c2.details["sweep_from_bar_index"] == 0
    assert c2.details["cisd_level"] == 100.2 and c2.details["cisd_level_source_bar_index"] == 21
    assert c2.reference_event_id == ev[0].event_id
    cisd = ev[2]
    assert cisd.details["early"] is False and cisd.details["confirm_phase"] == "C3"
    assert cisd.details["evidence_bar_index"] == 33 and cisd.details["delay_bars_from_c2"] == 3
    assert cisd.reference_event_id == c2.event_id
    lvl = ev[0]
    assert lvl.details["branch"] == "truc_tiep" and lvl.details["revision"] == 1
    exp = ev[3]
    assert exp.details["phase"] == "C4" and exp.details["terminal"] is True
    assert exp.details["c4_top"] == 100.6 and exp.details["c4_bottom"] == pytest.approx(100.1)


def test_timeline_giam_doi_xung():
    ev = run(m15(mirror(BASIC)))
    assert sig(ev) == [
        (T.CISD_LEVEL_SET_DOWN, 21, 21, 99.8),
        (T.C2_CONFIRMED_DOWN, 21, 31, 101.0),
        (T.CISD_CONFIRMED_DOWN, 33, 34, 99.8),
        (T.SETUP_EXPIRED, 63, 63, 101.0),
    ]
    assert all(e.direction == "down" for e in ev)


def test_c2_bang_muc_khong_dat_va_xuyen_khong_reclaim():
    # low C2 == low C1 → không phải sweep
    eq_low = rep((100.0, 100.5, 99.6, 100.2), 5) + [(100.2, 100.3, 99.5, 99.8)] + rep((99.8, 100.0, 99.6, 99.9), 10)
    assert not [e for e in run(m15(C1 + eq_low)) if e.structure_type == T.C2_CONFIRMED_UP]
    # xuyên nhưng close == low C1 → không đạt (strict)
    close_eq = C2_BULL[:-1] + [(99.4, 99.9, 99.2, 99.5)]
    assert not [e for e in run(m15(C1 + close_eq)) if e.structure_type == T.C2_CONFIRMED_UP]
    # xuyên nhưng close dưới → không đạt
    close_below = C2_BULL[:-1] + [(99.4, 99.9, 99.2, 99.3)]
    assert not [e for e in run(m15(C1 + close_below)) if e.structure_type == T.C2_CONFIRMED_UP]


def test_outside_bar_hai_setup_doc_lap():
    c2 = [(100.2, 101.0, 100.1, 100.3)] + rep((100.2, 100.4, 99.8, 100.1), 3) + \
         [(100.1, 100.2, 99.0, 99.4)] + rep((99.4, 100.3, 99.3, 100.2), 11)
    ev = run(m15(C1 + c2))
    c2s = [e for e in ev if e.structure_type in (T.C2_CONFIRMED_UP, T.C2_CONFIRMED_DOWN)]
    assert {e.structure_type for e in c2s} == {T.C2_CONFIRMED_UP, T.C2_CONFIRMED_DOWN}
    assert all(e.details["outside_bar_ambiguous"] for e in c2s)
    assert c2s[0].details["setup_id"] != c2s[1].details["setup_id"]
    assert all(e.confirmed_bar_index == 31 for e in c2s)


def test_bias_chi_loc_huong_khong_doi_huong_con_lai():
    c2 = [(100.2, 101.0, 100.1, 100.3)] + rep((100.2, 100.4, 99.8, 100.1), 3) + \
         [(100.1, 100.2, 99.0, 99.4)] + rep((99.4, 100.3, 99.3, 100.2), 11)
    bars = m15(C1 + c2 + C3_CONFIRM + C4_CALM)
    neutral = run(bars)
    bull = run(bars, bias="Bullish")
    setup_down = {T.C2_CONFIRMED_DOWN, T.CISD_CONFIRMED_DOWN}
    assert not [e for e in bull if e.structure_type in setup_down]
    def strip(e):
        d = e.to_dict()
        d["details"] = {k: v for k, v in d["details"].items() if k != "bias"}
        return d

    keep = [strip(e) for e in neutral
            if not (e.direction == "down" and e.structure_type not in (T.CISD_LEVEL_SET_DOWN, T.EARLY_CISD_DOWN))]
    assert keep == [strip(e) for e in bull]
    assert [e.details["bias"] for e in bull if e.structure_type == T.C2_CONFIRMED_UP] == ["Bullish"]


# ---------------------------------------------------------------------------
# Chọn mức CISD — từng nhánh Pine
# ---------------------------------------------------------------------------


def level_at(rows_c2, bar_index):
    ev = run(m15(C1 + rows_c2))
    got = [e for e in ev if e.structure_type == T.CISD_LEVEL_SET_UP and e.confirmed_bar_index == bar_index]
    return got[0] if got else None


def test_muc_truc_tiep_doji_va_hai_doji():
    up = (100.0, 100.5, 99.6, 100.2)
    # nến kích hoạt là doji, nến trước tăng → nhánh trực tiếp
    lv = level_at(rep(up, 5) + [(100.1, 100.3, 99.0, 100.1)], 21)
    assert lv.price == 100.1 and lv.event_bar_index == 21 and lv.details["branch"] == "truc_tiep"
    assert lv.details["doji_trigger"] is True
    # hai doji liên tiếp → không trực tiếp; tìm ngược không có nến giảm → không có mức
    assert level_at(rep(up, 4) + [(100.1, 100.3, 99.8, 100.1), (100.1, 100.3, 99.0, 100.1)], 21) is None


def test_muc_tim_nguoc_va_nang_theo_open():
    up = (100.0, 100.5, 99.6, 100.2)
    # [3]=tăng, [2]=A giảm open 100.4, [1]=B giảm open 100.3, [0]=nến kích hoạt giảm
    rows = rep(up, 3) + [(100.4, 100.45, 99.9, 100.0), (100.3, 100.35, 99.8, 99.9), (100.25, 100.3, 99.0, 99.2)]
    lv = level_at(rows, 21)
    assert (lv.price, lv.event_bar_index, lv.details["branch"], lv.details["scan_i"]) == (100.4, 19, "tim_nguoc", 3)
    # B mở cao hơn A → mức nâng lên open B
    rows = rep(up, 3) + [(100.3, 100.35, 99.9, 100.0), (100.4, 100.45, 99.8, 99.9), (100.35, 100.4, 99.0, 99.2)]
    lv = level_at(rows, 21)
    assert (lv.price, lv.event_bar_index) == (100.4, 20)


def test_muc_du_phong_high_va_open():
    up = (100.0, 100.5, 99.6, 100.2)
    a = (100.3, 100.35, 99.8, 99.9)  # nến giảm, open 100.3
    lv = level_at(rep(up, 4) + [a, (100.5, 100.9, 98.9, 100.6)], 21)
    assert (lv.price, lv.event_bar_index, lv.details["branch"]) == (100.9, 21, "du_phong_high")
    lv = level_at(rep(up, 4) + [a, (100.5, 100.6, 98.9, 100.5)], 21)
    assert (lv.price, lv.event_bar_index, lv.details["branch"]) == (100.5, 21, "du_phong_open")


def _down_run(n, start=100.4):
    out = []
    o = start
    for _ in range(n):
        out.append((o, o + 0.01, o - 0.02, o - 0.01))
        o = round(o - 0.02, 4)
    return out


def test_bien_tim_nguoc_10_nen():
    up = (100.0, 100.5, 99.6, 100.2)
    trig = (99.95, 100.0, 99.0, 99.1)
    # [10] tăng, [1..9] giảm → khớp ở i = 10
    lv = level_at([up, up] + _down_run(9) + [trig], 27)
    assert lv is not None and lv.details["scan_i"] == 10 and lv.event_bar_index == 18
    # [11] tăng, [1..10] giảm → ngoài cửa sổ, không đổi mức
    assert level_at([up] + _down_run(10) + [trig], 27) is None


def test_muc_ton_tai_qua_ky_va_muc_moi_thay_the():
    # C3 lập đáy mới dưới đáy C2 bằng nến tăng (không có mẫu) → giữ mức cũ;
    # C2 kế tiếp dùng mức từ kỳ trước.
    ev = run(m15(BASIC))
    assert [e.details["revision"] for e in ev if e.structure_type == T.CISD_LEVEL_SET_UP] == [1]
    # hai đáy mới liên tiếp, mỗi đáy trực tiếp → revision 1, 2; tham chiếu mức trước
    up = (100.0, 100.5, 99.6, 100.2)
    rows = rep(up, 4) + [(100.2, 100.3, 99.0, 99.3), (99.3, 99.6, 99.1, 99.5), (99.5, 99.6, 98.8, 99.0)]
    ev = run(m15(C1 + rows))
    lv = [e for e in ev if e.structure_type == T.CISD_LEVEL_SET_UP]
    assert [(e.price, e.details["revision"]) for e in lv] == [(100.2, 1), (99.5, 2)]
    assert lv[1].reference_event_id == lv[0].event_id
    assert lv[1].details["previous_level"] == 100.2


def test_muc_moi_khong_duoc_reclaim_bang_close_truoc_khi_muc_ton_tai():
    """Chống leak: nến t-1 đóng 100.3, nến t gap xuống mở 100.2 và lập mức 100.2.

    Pine so close[1]=100.3 với mức vừa lập ở t → reclaim ngay. Lab khoá mức có
    hiệu lực cuối nến t-1 (chưa có) nên KHÔNG reclaim bằng bằng chứng cũ hơn mức.
    """
    rows = rep((100.0, 100.5, 99.6, 100.2), 4) + [(100.2, 100.35, 99.9, 100.3), (100.2, 100.25, 99.0, 99.2)] + \
        rep((99.2, 99.4, 99.1, 99.3), 10)
    ev = run(m15(C1 + rows))
    assert not [e for e in ev if e.structure_type == T.EARLY_CISD_UP]
    c2 = [e for e in ev if e.structure_type == T.C2_CONFIRMED_UP]
    assert c2 == []  # close C2 99.3 < 99.5 → không phải C2; chỉ kiểm mức
    lv = [e for e in ev if e.structure_type == T.CISD_LEVEL_SET_UP]
    assert lv[0].price == 100.2 and lv[0].confirmed_bar_index == 21


# ---------------------------------------------------------------------------
# Early CISD, xác nhận, invalidation
# ---------------------------------------------------------------------------


def test_early_cisd_trong_c2_roi_c2_xac_nhan():
    c2 = C2_BULL[:9] + [(99.4, 100.4, 99.3, 100.3)] + C2_BULL[10:]
    ev = run(m15(C1 + c2 + C3_CONFIRM + C4_CALM))
    assert sig(ev) == [
        (T.CISD_LEVEL_SET_UP, 21, 21, 100.2),
        (T.EARLY_CISD_UP, 25, 26, 100.2),
        (T.C2_CONFIRMED_UP, 21, 31, 99.0),
        (T.CISD_CONFIRMED_UP, 25, 31, 100.2),
        (T.SETUP_EXPIRED, 63, 63, 99.0),
    ]
    early, c2e, cisd = ev[1], ev[2], ev[3]
    assert early.details["candidate_id"] == "up-20240101T0400"
    assert cisd.details["early"] is True and cisd.details["confirm_phase"] == "C2"
    assert cisd.details["early_cisd_event_id"] == early.event_id
    assert cisd.reference_event_id == early.event_id
    assert cisd.details["reclaim_before_c2"] is False
    assert c2e.details["cisd_already_reclaimed"] is True


def test_early_cisd_ung_vien_khong_thanh_c2():
    c2 = C2_BULL[:9] + [(99.4, 100.4, 99.3, 100.3)] + C2_BULL[10:-1] + [(99.4, 99.9, 99.2, 99.4)]
    ev = run(m15(C1 + c2 + C3_CONFIRM))
    assert [e.structure_type for e in ev if e.structure_type == T.EARLY_CISD_UP] == [T.EARLY_CISD_UP]
    assert not [e for e in ev if e.structure_type in (T.C2_CONFIRMED_UP, T.CISD_CONFIRMED_UP)]


def test_pha_cuc_tri_uu_tien_truoc_xac_nhan_cung_nen():
    c3 = [(99.8, 100.6, 99.5, 100.5), (100.5, 100.6, 98.9, 99.0)] + rep((99.0, 99.3, 98.95, 99.2), 14)
    ev = run(m15(C1 + C2_BULL + c3))
    setup_ev = [e for e in ev if e.details.get("setup_id") == "up-20240101T0400"]
    assert [(e.structure_type, e.confirmed_bar_index) for e in setup_ev] == [
        (T.C2_CONFIRMED_UP, 31), (T.SETUP_INVALIDATED, 33)]
    assert setup_ev[1].reason_code == "SETUP_EXTREME_BREACHED"
    assert setup_ev[1].details["breach_price"] == 98.9


def test_xac_nhan_trong_c4_roi_c4_that_bai_khong_xoa_cisd():
    c3 = rep((99.8, 100.0, 99.5, 99.9), 16)                       # mid C3 = 99.75
    c4 = [(99.9, 100.5, 99.8, 100.4), (100.4, 100.4, 99.6, 99.7)] + rep((99.7, 99.9, 99.6, 99.8), 14)
    ev = run(m15(C1 + C2_BULL + c3 + c4))
    setup_ev = [e for e in ev if e.details.get("setup_id") == "up-20240101T0400"]
    assert [(e.structure_type, e.event_bar_index, e.confirmed_bar_index) for e in setup_ev] == [
        (T.C2_CONFIRMED_UP, 21, 31), (T.CISD_CONFIRMED_UP, 48, 49), (T.SETUP_INVALIDATED, 49, 50)]
    cisd, inv = setup_ev[1], setup_ev[2]
    assert cisd.details["confirm_phase"] == "C4" and cisd.details["cisd_confirmed_in_c4"] is True
    assert inv.reason_code == "SETUP_C4_FAIL_AFTER_CISD_IN_C4"
    assert inv.reference_event_id == cisd.event_id
    assert inv.price == pytest.approx(99.75)


def test_c4_invalid_khong_ket_thuc_khi_cisd_da_co_tu_c3():
    c4 = [(100.6, 100.7, 99.9, 100.0)] + rep((100.0, 100.3, 99.9, 100.2), 15)
    ev = run(m15(C1 + C2_BULL + C3_CONFIRM + c4))
    setup_ev = [e for e in ev if e.details.get("setup_id") == "up-20240101T0400"]
    assert [(e.structure_type, e.confirmed_bar_index) for e in setup_ev] == [
        (T.C2_CONFIRMED_UP, 31), (T.CISD_CONFIRMED_UP, 34), (T.SETUP_C4_INVALIDATED, 49), (T.SETUP_EXPIRED, 63)]
    assert setup_ev[2].details["terminal"] is False and setup_ev[2].event_bar_index == 48


def test_xac_nhan_o_nen_cuoi_c4_cung_nen_het_han_va_close_cuoi_khong_duoc_xet():
    c3 = rep((99.8, 100.0, 99.5, 99.9), 16)
    c4 = rep((99.9, 100.1, 99.8, 100.0), 14) + [(100.0, 100.4, 99.9, 100.3), (100.3, 100.4, 100.0, 100.1)]
    ev = run(m15(C1 + C2_BULL + c3 + c4))
    setup_ev = [e for e in ev if e.details.get("setup_id") == "up-20240101T0400"]
    assert [(e.structure_type, e.confirmed_bar_index) for e in setup_ev] == [
        (T.C2_CONFIRMED_UP, 31), (T.CISD_CONFIRMED_UP, 63), (T.SETUP_EXPIRED, 63)]
    # close nến 63 vượt mức nhưng setup đã hết hạn — giống Pine (finish trước check).
    c4b = rep((99.9, 100.1, 99.8, 100.0), 15) + [(100.0, 100.4, 99.9, 100.3)]
    ev = run(m15(C1 + C2_BULL + c3 + c4b + rep((100.3, 100.4, 100.2, 100.3), 2)))
    assert not [e for e in ev if e.structure_type == T.CISD_CONFIRMED_UP]


def test_setup_moi_cung_huong_luon_pha_cuc_tri_truoc_nen_khong_co_superseded():
    """C2 mới cùng hướng trong C3 buộc low C3 < low C2 cũ = cực trị → breach trước.

    Vì vậy SETUP_SUPERSEDED không đạt được với so sánh strict hiện tại (xem spec).
    """
    c3_new_c2 = rep((99.8, 100.0, 99.5, 99.9), 5) + [(99.9, 100.0, 98.5, 98.8)] + rep((98.8, 99.5, 98.7, 99.4), 10)
    ev = run(m15(C1 + C2_BULL + c3_new_c2 + C4_CALM))
    kinds = [(e.structure_type, e.details.get("setup_id")) for e in ev
             if e.structure_type in (T.C2_CONFIRMED_UP, T.SETUP_INVALIDATED, T.SETUP_SUPERSEDED)]
    assert kinds == [
        (T.C2_CONFIRMED_UP, "up-20240101T0400"),
        (T.SETUP_INVALIDATED, "up-20240101T0400"),
        (T.C2_CONFIRMED_UP, "up-20240101T0800"),
    ]


# ---------------------------------------------------------------------------
# Dữ liệu thiếu, warm-up, biên H4
# ---------------------------------------------------------------------------


def test_gap_trong_c3_ket_thuc_setup_va_xoa_muc():
    bars = m15(BASIC)
    gapped = [b for b in bars if b.index != 40]
    gapped = [replace(b, index=i) for i, b in enumerate(gapped)]
    algo = C2CisdResearchAlgorithm()
    ev = algo.run(gapped)
    kinds = [(e.structure_type, e.confirmed_bar_index) for e in ev]
    assert (T.SETUP_DATA_GAP, 40) in kinds
    assert (T.HTF_BUCKET_INCOMPLETE, 40) in kinds
    assert not [e for e in ev if e.structure_type == T.SETUP_EXPIRED]
    gap_ev = [e for e in ev if e.structure_type == T.SETUP_DATA_GAP][0]
    assert gap_ev.reason_code == "SETUP_LTF_GAP" and gap_ev.details["missing_ltf_bars"] == 1
    assert algo.pending_state()["muc_cisd_dang_theo_doi"] == {"up": None, "down": None}
    inc = [e for e in ev if e.structure_type == T.HTF_BUCKET_INCOMPLETE][0]
    assert inc.details["bucket_start"].startswith("2024-01-01T08:00")


def test_ky_dau_thieu_nen_khong_lam_c1():
    ev = run(m15(BASIC[4:], start=START + timedelta(hours=1)))
    assert [(e.structure_type, e.confirmed_bar_index) for e in ev if e.structure_type == T.HTF_BUCKET_INCOMPLETE] == [
        (T.HTF_BUCKET_INCOMPLETE, 0)]
    assert not [e for e in ev if e.structure_type == T.C2_CONFIRMED_UP]
    assert not [e for e in ev if e.structure_type == T.CISD_LEVEL_SET_UP]


def test_ky_cuoi_dang_chay_khong_bao_thieu_va_setup_con_mo():
    algo = C2CisdResearchAlgorithm()
    ev = algo.run(m15(BASIC[:40]))
    assert not [e for e in ev if e.structure_type == T.HTF_BUCKET_INCOMPLETE]
    st = algo.pending_state()["setup_dang_mo"]["up"]
    assert st["setup_id"] == "up-20240101T0400" and st["phase"] == "C3"


def test_warmup_chua_du_hai_ky():
    algo = C2CisdResearchAlgorithm()
    assert algo.warmup_bars() == 32
    r = run_algorithm(m15(BASIC[:31]), algo)
    assert r.data_status == "WARMUP_INSUFFICIENT"
    assert not [e for e in r.events if e.structure_type.startswith("C2_")]


def test_tu_choi_dataset_khong_phai_m15():
    with pytest.raises(ValueError):
        C2CisdResearchAlgorithm.check_dataset("H1", {"ltf": "M15"})
    h1 = make_bars(rep((100.0, 100.5, 99.5, 100.2), 3), timeframe="H1")
    with pytest.raises(ValueError):
        C2CisdResearchAlgorithm().run(h1)
    lech = m15(rep((100.0, 100.5, 99.5, 100.2), 3), start=START + timedelta(minutes=7))
    with pytest.raises(ValueError):
        C2CisdResearchAlgorithm().run(lech)
    with pytest.raises(ValueError):
        C2CisdResearchAlgorithm(htf="H1")


def test_aggregator_bien_utc_va_hoan_tat():
    agg = HtfAggregator(900, 14400)
    t0 = datetime(2024, 3, 5, 3, 45, tzinfo=timezone.utc)
    r = agg.push(0, t0, 1, 2, 0.5, 1.5)
    assert r.current.start == datetime(2024, 3, 5, 0, 0, tzinfo=timezone.utc)
    assert not r.current.contiguous and r.newly_incomplete  # thiếu nến đầu kỳ
    assert not r.completed_now
    for i in range(16):
        r = agg.push(i + 1, datetime(2024, 3, 5, 4, 0, tzinfo=timezone.utc) + timedelta(minutes=15 * i),
                     1, 2 if i != 3 else 3, 0.5 if i != 7 else 0.2, 1.5)
        assert r.completed_now == (i == 15)
    assert r.current.high_bar_index == 4 and r.current.low_bar_index == 8
    r = agg.push(17, datetime(2024, 3, 5, 8, 30, tzinfo=timezone.utc), 1, 2, 0.5, 1.5)
    assert r.started_new_bucket and r.previous_adjacent and r.previous.complete
    assert not r.current.contiguous  # thiếu nến 08:00


# ---------------------------------------------------------------------------
# Nhân quả, tái lập, bất biến — trên chuỗi ngẫu nhiên có doji và gap
# ---------------------------------------------------------------------------


def random_m15(n=3000, seed=11):
    rnd = random.Random(seed)
    bars = []
    t = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    price = 2000.0
    idx = 0
    while len(bars) < n:
        # nghỉ phiên 21:00–22:00 UTC mỗi ngày + thỉnh thoảng thiếu 1 nến
        if t.hour == 21 or rnd.random() < 0.004:
            t += timedelta(minutes=15)
            continue
        o = price
        c = round(o + rnd.choice([-1, 0, 1]) * rnd.choice([0.0, 0.5, 1.0, 2.0]), 1)
        h = round(max(o, c) + rnd.choice([0.0, 0.5, 1.0]), 1)
        l = round(min(o, c) - rnd.choice([0.0, 0.5, 1.0]), 1)
        bars.append(Bar(index=idx, bar_time=t, close_time=t + timedelta(minutes=15),
                        open=o, high=h, low=l, close=c))
        price = c
        idx += 1
        t += timedelta(minutes=15)
    return bars


@pytest.fixture(scope="module")
def rbars():
    return random_m15()


@pytest.fixture(scope="module")
def full(rbars):
    return run_algorithm(rbars, C2CisdResearchAlgorithm())


def dicts(events):
    return [e.to_dict() for e in events]


def test_ngau_nhien_co_du_moi_loai_su_kien(full):
    kinds = {e.structure_type for e in full.events}
    for k in (T.C2_CONFIRMED_UP, T.C2_CONFIRMED_DOWN, T.CISD_CONFIRMED_UP, T.CISD_CONFIRMED_DOWN,
              T.EARLY_CISD_UP, T.EARLY_CISD_DOWN, T.SETUP_EXPIRED, T.SETUP_INVALIDATED,
              T.SETUP_DATA_GAP, T.HTF_BUCKET_INCOMPLETE, T.SETUP_C4_INVALIDATED):
        assert k in kinds, k


@pytest.mark.parametrize("cut", [100, 777, 1500, 2222, 2999])
def test_prefix_bang_full_loc_theo_confirmed(rbars, full, cut):
    pre = run_algorithm(rbars[:cut], C2CisdResearchAlgorithm())
    assert dicts(pre.events) == dicts([e for e in full.events if e.confirmed_bar_index < cut])
    assert pre.timeline == full.timeline[:cut]


def test_sua_suffix_khong_doi_log_truoc_T(rbars, full):
    cut = 1600
    tampered = list(rbars[:cut]) + [
        replace(b, open=b.open + 50, high=b.high + 80, low=b.low - 40, close=b.close - 30)
        for b in rbars[cut:]
    ]
    after = run_algorithm(tampered, C2CisdResearchAlgorithm())
    assert dicts([e for e in after.events if e.confirmed_bar_index < cut]) == \
        dicts([e for e in full.events if e.confirmed_bar_index < cut])


def test_batch_stream_reset_replay_giong_nhau(rbars, full):
    algo = C2CisdResearchAlgorithm()
    algo.run(rbars[:500])               # trạng thái bẩn
    algo.reset()
    stream = []
    for b in rbars:
        stream.extend(algo.on_bar(b))
    assert dicts(stream) == dicts(full.events)
    rp = ReplaySession(rbars, C2CisdResearchAlgorithm())
    rp.seek(2500)
    rp.seek(1200)                       # lùi = reset + chạy lại
    rp.seek(len(rbars) - 1)
    assert dicts(rp.events) == dicts(full.events)


def test_su_kien_da_phat_khong_bi_sua(rbars):
    algo = C2CisdResearchAlgorithm()
    algo.reset()
    emitted, snaps = [], []
    for b in rbars:
        out = algo.on_bar(b)
        emitted.extend(out)
        snaps.extend(copy.deepcopy(e.to_dict()) for e in out)
    assert [e.to_dict() for e in emitted] == snaps


def test_bat_bien_log(rbars, full):
    ev = full.events
    ids = [e.event_id for e in ev]
    assert len(ids) == len(set(ids))
    by_bar = {b.index: b for b in rbars}
    level_set_bar = {}
    terminal = {}
    for e in ev:
        assert e.confirmed_at == by_bar[e.confirmed_bar_index].close_time
        assert e.event_bar_index <= e.confirmed_bar_index
        if e.structure_type in (T.CISD_LEVEL_SET_UP, T.CISD_LEVEL_SET_DOWN):
            level_set_bar[e.event_id] = e.confirmed_bar_index
        if e.structure_type in (T.EARLY_CISD_UP, T.EARLY_CISD_DOWN, T.CISD_CONFIRMED_UP, T.CISD_CONFIRMED_DOWN):
            lvl_ev = e.details.get("cisd_level_event_id") or e.reference_event_id
            if lvl_ev in level_set_bar:
                # bằng chứng close phải ở nến >= lúc mức được biết
                assert e.details["evidence_bar_index"] >= level_set_bar[lvl_ev]
        if e.structure_type in (T.C2_CONFIRMED_UP, T.C2_CONFIRMED_DOWN):
            assert e.confirmed_at.isoformat() == e.details["c2_end"]
            assert e.confirmed_at.hour % 4 == 0 and e.confirmed_at.minute == 0
        sid = e.details.get("setup_id")
        if sid:
            assert sid not in terminal, "sự kiện sau terminal: %s" % e.event_id
            if e.details.get("terminal"):
                terminal[sid] = e.structure_type


def test_moi_setup_toi_da_mot_terminal_va_censored_khi_het_du_lieu(full):
    from core.algorithms.c2_cisd_research.metrics import lifecycle_metrics

    m = lifecycle_metrics([e.to_dict() for e in full.events])
    n = m["tong_setup"]
    assert n == sum(m["ket_thuc_theo_ly_do"].values()) + m["censored_dang_mo"]


def test_ham_chon_muc_thuan_khop_thuat_toan():
    """``select_cisd_level`` dùng được độc lập, cho đúng mức như khi chạy cả thuật toán."""
    from core.algorithms.c2_cisd_research.levels import select_cisd_level

    up = (100.0, 100.5, 99.6, 100.2)
    rows = rep(up, 3) + [(100.3, 100.35, 99.9, 100.0), (100.4, 100.45, 99.8, 99.9), (100.35, 100.4, 99.0, 99.2)]
    bars = m15(C1 + rows)
    choice = select_cisd_level(bars[:22], bull=True)
    assert choice is not None
    assert (choice.price, choice.source_index, choice.branch, choice.scan_i) == (100.4, 20, "tim_nguoc", 3)
    lv = level_at(rows, 21)
    assert (lv.price, lv.event_bar_index, lv.details["branch"]) == (choice.price, choice.source_index, choice.branch)
    # chỉ một nến lịch sử, nến kích hoạt tăng: không nhánh nào khớp → giữ mức cũ
    assert select_cisd_level(bars[21:22], bull=True) is None
