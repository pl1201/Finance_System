"""ict_structure 0.5.0 — order block và OTE neo vào SHIFT (plan_ket_hop_ict_indicator.md §3.4, luồng
kien_truc_luong_ict.md §4.4).

Thành phần thử trực tiếp trên nến dựng tay; thuật toán thử trên chuỗi BASE của test giai đoạn 2 nối thêm ba nến
(tính tay ở chú thích) và trên dữ liệu ngẫu nhiên (bất biến + nhân quả).
"""
from __future__ import annotations

import pytest

from core.algorithms.ict_structure import IctStructureAlgorithm
from core.components.order_block import DROPPED, OrderBlock, OrderBlockTracker
from core.components.ote import OteTracker
from core.engine import run_algorithm
from tests.algorithms.test_ict_structure_g2 import BASE, _algo, _ohlc, _one, _p, _random_bars, _types

NEW = {"ORDER_BLOCK_UP", "ORDER_BLOCK_DOWN", "OB_TAP_UP", "OB_TAP_DOWN", "OB_FAIL_UP", "OB_FAIL_DOWN", "OB_EXPIRED",
       "OTE_ENTRY_UP", "OTE_ENTRY_DOWN", "OTE_FAIL_UP", "OTE_FAIL_DOWN", "OTE_EXPIRED"}

# #0 tăng · #1, #2 giảm (chuỗi) · #3 tăng nhỏ · #4 displacement tăng = d
RUN = [(10.0, 11.0, 9.5, 10.5), (10.5, 10.6, 9.8, 10.0), (10.0, 10.1, 9.4, 9.5), (9.5, 9.7, 9.0, 9.6),
       (9.6, 11.5, 9.5, 11.4)]


def _tracker(variant="than_chuoi", gaps=(), expiry=10, lookback=5, **kw):
    """Bộ theo dõi đã nạp RUN #0–#3 (kw: pd_mode / away_atr — vòng đời PD array 0.10.0, tests/algorithms/test_ict_mss.py)."""
    bars = _ohlc(RUN)
    tr = OrderBlockTracker(variant, lookback=lookback, expiry=expiry, buffer=20, **kw)
    for b in bars[:4]:
        tr.push(b, b.index in gaps)
    return tr, bars


# ------------------------------------------------------------------ [E4] thành phần order block


def test_ob_than_chuoi_gop_chuoi_nen_giam_cuoi_va_xac_nhan_ngay_khi_vuot_dau_xa():
    tr, bars = _tracker()
    ob = tr.create("up", bars[4], 0, "S")
    # bỏ #3 (tăng), gộp #2 + #1 (giảm), dừng ở #0 (tăng): thân = [close thấp nhất 9.5, open cao nhất 10.5]
    assert (ob.lo, ob.hi, ob.first_bar.index, ob.last_bar.index, ob.n_bars) == (9.5, 10.5, 1, 2, 2)
    assert ob.mid == pytest.approx(10.0) and ob.confirmed_at == 4 and ob.deadline == 14   # high 11.5 > 10.5
    assert tr.open == [ob] and tr.candidates == [] and tr.counts["xac_nhan"] == 1


def test_ob_nen_cuoi_rau_va_khong_lui_qua_khoang_trong():
    tr, bars = _tracker("nen_cuoi_rau")
    ob = tr.create("up", bars[4], 0, "S")
    assert (ob.lo, ob.hi, ob.n_bars, ob.last_bar.index) == (9.4, 10.1, 1, 2)        # cả râu của nến giảm #2
    tr2, bars2 = _tracker(gaps=(2,))                       # khoảng trống ngay trước #2 → không xét #1
    ob2 = tr2.create("up", bars2[4], 0, "S")
    assert (ob2.lo, ob2.hi, ob2.first_bar.index) == (9.5, 10.0, 2)


def test_ob_khong_co_nen_nguoc_mau_va_lo_index():
    tr, bars = _tracker(lookback=1)                        # cửa sổ = [4 − 1, d − 1] = chỉ #3
    assert tr.create("up", bars[4], 4, "S") is None and tr.counts["khong_co_nen"] == 1   # chỉ xét #3 (tăng)
    assert tr.create("down", bars[4], 0, "S").last_bar.index == 3     # OB giảm: nến tăng gần d nhất là #3


LOW_D = RUN[:4] + [(9.6, 10.4, 9.5, 10.3)]                 # #4 = d không vượt 10.5 → chỉ là ứng viên


def test_ob_ung_vien_cho_xac_nhan_roi_cham_hong_het_han():
    tr, bars = _tracker()
    low_d = _ohlc(LOW_D)[4]
    ob = tr.create("up", low_d, 0, "S")
    assert ob.confirmed_at is None and tr.candidates == [ob] and tr.open == []
    nxt = _ohlc([(0, 0, 0, 0)] * 5 + [(10.3, 10.7, 10.2, 10.6)])[5]   # nến #5: high 10.7 > 10.5 → xác nhận ở #5
    done, new, _taps, _brs = tr.on_bar(nxt)         # 0.10.0: (kết cục, xác nhận, chạm PD, breaker)
    assert done == [] and new == [ob] and ob.confirmed_at == 5
    tap = _ohlc([(0, 0, 0, 0)] * 6 + [(10.6, 10.7, 10.4, 10.6)])[6]   # low 10.4 ≤ 10.5, close ≥ 9.5 → chạm
    done, *_ = tr.on_bar(tap)
    assert done == [ob] and ob.ended == "tap" and tr.tap_ages == [1]


def test_ob_hong_khi_close_thung_mep_duoi_cung_nen_cham_va_ung_vien_bi_bo():
    tr, bars = _tracker()
    ob = tr.create("up", bars[4], 0, "S")
    bad = _ohlc([(0, 0, 0, 0)] * 5 + [(10.0, 10.2, 9.0, 9.3)])[5]
    done, *_ = tr.on_bar(bad)
    assert done == [ob] and ob.ended == "fail" and tr.counts["fail"] == 1
    tr2, _b = _tracker()
    cand = tr2.create("up", _ohlc(LOW_D)[4], 0, "S")
    tr2.on_bar(_ohlc([(0, 0, 0, 0)] * 5 + [(10.3, 10.4, 9.2, 9.4)])[5])   # close 9.4 < 9.5 trước khi xác nhận
    assert tr2.candidates == [] and cand.confirmed_at is None and tr2.counts["bo_truoc_xac_nhan"] == 1


def test_ob_het_han_theo_thoi_gian_va_theo_shift_nguoc():
    tr, bars = _tracker(expiry=2)
    ob = tr.create("up", bars[4], 0, "S")                    # hạn = 4 + 2 = 6
    far = lambda i: _ohlc([(0, 0, 0, 0)] * i + [(12.0, 12.5, 11.8, 12.2)])[i]
    assert tr.on_bar(far(5)) == ([], [], [], []) and ob.ended is None
    done, *_ = tr.on_bar(far(6))
    assert done == [ob] and ob.ended == "expired_time"
    tr2, b2 = _tracker()
    ob2 = tr2.create("up", b2[4], 0, "S")
    assert tr2.expire_opposite("up") == []                # SHIFT cùng chiều: giữ
    assert tr2.expire_opposite("down") == [ob2] and ob2.ended == "expired_shift" and tr2.open == []


def test_ob_mot_cau_truc_mot_ob_va_lien_ket_ote():
    tr, bars = _tracker()
    cand = tr.create("up", _ohlc(LOW_D)[4], 0, "S1")
    assert cand.link() == {"id": None, "lo": 9.5, "hi": 10.5, "da_xac_nhan": False, "nen_xac_nhan": None}
    again = tr.create("up", _ohlc(LOW_D)[4], 0, "S2")       # SHIFT thứ hai tìm lại đúng chuỗi #1–#2
    assert again is cand and tr.candidates == [cand] and tr.counts["ung_vien"] == 1 and tr.counts["trung"] == 1
    tr.on_bar(_bar(5, 10.3, 10.4, 9.2, 9.4))                # close 9.4 < 9.5 → ứng viên bị bỏ: vùng không còn
    assert cand.ended == DROPPED and cand.link() is None


def test_ob_close_vuot_mep_xa_ngay_o_nen_d_la_bo_khong_xac_nhan():
    tr, bars = _tracker()
    d = _ohlc(RUN[:4] + [(9.6, 11.0, 9.0, 9.2)])[4]          # high 11 > 10.5 nhưng close 9.2 < 9.5: xét bỏ trước
    ob = tr.create("up", d, 0, "S")
    assert ob.ended == DROPPED and ob.confirmed_at is None and tr.open == [] and tr.candidates == []
    assert tr.counts["bo_truoc_xac_nhan"] == 1 and tr.counts["xac_nhan"] == 0


def test_ob_xep_hang_va_bo_dem_va_tham_so():
    tr, bars = _tracker()
    old, new = (OrderBlock(k, "up", 9.0, 10.0, bars[0], bars[0], 1, 4, "S", 99) for k in (0, 1))
    tr.open = [old, new]
    assert tr.ranked("up", 12.0) == [new, old]               # cùng khoảng cách → OB mới hơn trước
    small = OrderBlockTracker(lookback=1, buffer=3)           # bộ đệm 3 nến: #2..#4
    for b in _ohlc([(1, 2, 0.5, 1.5)] * 6)[:5]:               # toàn nến tăng → duyệt hết bộ đệm
        small.push(b, False)
    with pytest.raises(RuntimeError, match="Bộ đệm OB"):
        small.create("up", _ohlc([(1, 2, 0.5, 1.5)] * 6)[5], 1, "S")
    with pytest.raises(ValueError, match="ob_lui"):
        OrderBlockTracker(lookback=0)


# ------------------------------------------------------------------ [E6] thành phần OTE


def _bar(i, o, h, lo, c):
    return _ohlc([(0, 0, 0, 0)] * i + [(o, h, lo, c)])[i]


def test_ote_vao_vung_do_sau_va_dau_nhip_lay_toi_nen_truoc():
    ote = OteTracker(0.62, 0.79, min_leg_atr=0.0, expiry=10)
    ote.start("up", 100.0, 110.0, 0, "S")
    assert ote.on_bar(_bar(1, 110, 112, 104.0, 111), 1.0) is None   # mức 62% = 110 − 6.2 = 103.8; low 104 chưa tới
    ote.after_bar(_bar(1, 110, 112, 104.0, 111))                    # H = 112 → mức 62% = 112 − 7.44 = 104.56
    # nến vừa lập đỉnh 120 vừa hồi tới 104.7: dùng H của nến trước (112) → 104.7 > 104.56, chưa vào
    assert ote.on_bar(_bar(2, 111, 120, 104.7, 119), 1.0) is None
    ote.after_bar(_bar(2, 111, 120, 104.7, 119))                    # H = 120, L = 20 → mức 62% = 107.6
    leg = ote.on_bar(_bar(3, 119, 119.5, 107.0, 108), 1.0)
    assert leg.ended == "entry" and leg.depth == pytest.approx((120 - 107.0) / 20) and ote.pending is None
    assert ote.zone(leg, 1.0) == pytest.approx((120 - 0.79 * 20, 120 - 0.62 * 20))


def test_ote_hong_xet_truoc_nhip_nho_va_het_han():
    ote = OteTracker(min_leg_atr=0.0)
    ote.start("up", 100.0, 110.0, 0, "S")
    leg = ote.on_bar(_bar(1, 105, 106, 99.0, 100.5), 1.0)     # vừa xuống dưới 103.8 vừa thủng gốc 100 → hỏng
    assert leg.ended == "fail" and leg.depth is None
    small = OteTracker(min_leg_atr=2.0, expiry=3)
    small.start("up", 100.0, 110.0, 0, "S")                   # L = 10 < 2 × ATR 6 → chưa có vùng
    assert small.zone(small.pending, 6.0) is None
    assert small.on_bar(_bar(1, 105, 106, 102.0, 103), 6.0) is None
    assert small.on_bar(_bar(2, 103, 104, 102.0, 103), 6.0) is None
    assert small.on_bar(_bar(3, 103, 104, 102.0, 103), 6.0).ended == "expired_time"
    edge = OteTracker(min_leg_atr=0.0)
    edge.start("up", 100.0, 110.0, 0, "S")
    assert edge.zone(edge.pending, None) is not None         # không lọc nhịp → không cần ATR
    leg = edge.on_bar(_bar(1, 105, 106, 100.0, 101), None)    # low chạm đúng gốc 100, không thủng → vào, độ sâu 1
    assert leg.ended == "entry" and leg.depth == pytest.approx(1.0)


def test_ote_nhip_giam_doi_xung_va_shift_moi_thay_nhip():
    ote = OteTracker(min_leg_atr=0.0)
    ote.start("down", 110.0, 100.0, 0, "S1")                 # gốc 110 (đỉnh quét), đầu nhịp 100
    leg = ote.on_bar(_bar(1, 101, 106.5, 100.5, 106), 1.0)   # mức 62% = 100 + 6.2 = 106.2; high 106.5 → vào
    assert leg.ended == "entry" and leg.depth == pytest.approx(0.65)
    ote.start("down", 110.0, 100.0, 2, "S2")
    old = ote.start("down", 111.0, 101.0, 3, "S3")           # cùng chiều → thay
    assert old.ended == "replaced" and ote.pending.anchor_id == "S3"
    old = ote.start("up", 95.0, 101.0, 4, "S4")              # ngược chiều → hết hạn vì shift
    assert old.ended == "expired_shift" and ote.counts["nhip"] == 4


def test_ote_kiem_tham_so():
    with pytest.raises(ValueError):
        OteTracker(0.8, 0.7)
    with pytest.raises(ValueError, match="OTE"):
        IctStructureAlgorithm.validate_params({"ote_tu": 0.8, "ote_den": 0.7})


# ------------------------------------------------------------------ thuật toán: chuỗi dựng tay

# BASE (test giai đoạn 2): #8 SHIFT_DOWN (quét B0 lấy ở #7, X = 102.6), #9 SHIFT_UP (quét S1 lấy ở #8, X = 96.7).
TAIL = [
    (100.6, 102.2, 100.4, 102.0),   # #10 high 102.2 > 101.8 → OB tăng (thân #8 [98.8, 101.8]) xác nhận; H → 102.2
    (102.0, 102.1, 99.9, 100.2),    # #11 low 99.9 ≤ 101.8, close ≥ 98.8 → chạm OB; mức 62% = 102.2 − 0.62 × 5.5 = 98.79
    (100.2, 100.4, 98.5, 98.9),     # #12 low 98.5 ≤ 98.79 → vào OTE, độ sâu (102.2 − 98.5) / 5.5
]


def test_chuoi_ob_ote_tren_base():
    res = run_algorithm(_ohlc(BASE + TAIL), _algo(ote_nhip_min_atr=0.0))
    ev = res.events
    sh_dn, sh_up = _one(ev, "SHIFT_DOWN"), _one(ev, "SHIFT_UP")
    # #8: OB giảm = thân nến tăng #7 [101.0, 101.8] (nến #6 giảm chặn chuỗi); low 98.6 < 101.0 → xác nhận ngay ở d
    ob_dn = _one(ev, "ORDER_BLOCK_DOWN")
    assert (ob_dn.event_bar_index, ob_dn.confirmed_bar_index, ob_dn.price) == (7, 8, pytest.approx(101.4))
    assert (ob_dn.details["lo"], ob_dn.details["hi"], ob_dn.details["nen_xac_nhan"]) == (101.0, 101.8, 8)
    assert ob_dn.reference_event_id == sh_dn.event_id and ob_dn.details["basis"] == [sh_dn.event_id]
    # #9: SHIFT tăng → OB giảm chưa chạm hết hạn; nhịp OTE giảm bị thay (ngược chiều)
    exp = _one(ev, "OB_EXPIRED")
    assert (exp.confirmed_bar_index, exp.reason_code, exp.reference_event_id) == (9, "OB_EXPIRED_OPPOSITE_SHIFT",
                                                                                   ob_dn.event_id)
    ote_exp = _one(ev, "OTE_EXPIRED")
    assert (ote_exp.confirmed_bar_index, ote_exp.reason_code, ote_exp.details["x"]) == (9, "OTE_EXPIRED_SHIFT", 102.6)
    # #10: ứng viên OB tăng (thân #8 [98.8, 101.8]) được xác nhận khi high 102.2 > 101.8
    ob_up = _one(ev, "ORDER_BLOCK_UP")
    assert (ob_up.event_bar_index, ob_up.confirmed_bar_index, ob_up.details["nen_neo"]) == (8, 10, 9)
    assert (ob_up.details["lo"], ob_up.details["hi"]) == (98.8, 101.8) and ob_up.reference_event_id == sh_up.event_id
    tap = _one(ev, "OB_TAP_UP")
    assert (tap.confirmed_bar_index, tap.price, tap.reference_event_id) == (11, 101.8, ob_up.event_id)
    assert tap.details["so_nen_tu_tao"] == 2
    assert tap.details["close_qua_mean_threshold"] is True       # close 100.2 < mean threshold (98.8 + 101.8) / 2 = 100.3
    ent = _one(ev, "OTE_ENTRY_UP")
    x = ent.details
    assert (ent.confirmed_bar_index, x["x"], x["h"]) == (12, 96.7, 102.2)
    assert x["do_sau"] == pytest.approx(3.7 / 5.5) and ent.price == pytest.approx(102.2 - 0.62 * 5.5)
    assert x["ob"]["id"] == ob_up.event_id and x["ob_giao_vung"] is False      # OB [98.8, …] trên vùng [97.86, 98.79]
    assert x["basis"] == [sh_up.event_id, ob_up.event_id]
    tl = res.timeline
    assert (tl[10]["ob_up_lo"], tl[10]["ob_up_hi"], tl[11]["ob_up_hi"]) == (98.8, 101.8, None)
    assert (tl[11]["ote_dir"], tl[11]["ote_x"], tl[11]["ote_h"]) == ("up", 96.7, 102.2)
    assert tl[11]["ote_hi"] == pytest.approx(102.2 - 0.62 * 5.5) and tl[12]["ote_dir"] is None
    st = res.stats["chi_so_thuat_toan"]
    assert (st["order_block"]["xac_nhan"], st["order_block"]["cham"], st["ote"]["vao"]) == (2, 1, 1)


def test_bien_the_va_neo_displacement():
    rows = BASE + TAIL
    r = run_algorithm(_ohlc(rows), _algo(ote_nhip_min_atr=0.0, ob_bien_the="nen_cuoi_rau"))
    ob = _one(r.events, "ORDER_BLOCK_DOWN")
    assert (ob.details["lo"], ob.details["hi"], ob.reason_code) == (101.0, 102.6, "OB_LAST_CANDLE_WICK")
    d = run_algorithm(_ohlc(rows), _algo(ob_neo="displacement"))
    obs = [e for e in d.events if e.structure_type.startswith("ORDER_BLOCK_")]
    assert obs and all(e.details["neo"] == "displacement" for e in obs)
    assert all(e.reference_event_id.startswith("ict:DISPLACEMENT_") for e in obs)


# ------------------------------------------------------------------ dữ liệu ngẫu nhiên


@pytest.mark.parametrize("seed", [3, 4])
def test_bat_bien_ob_ote_tren_du_lieu_ngau_nhien(seed):
    res = run_algorithm(_random_bars(seed, 1500), IctStructureAlgorithm(**_p()))
    ev = res.events
    by_id = {e.event_id: e for e in ev}
    kinds = {e.structure_type for e in ev}
    assert {"ORDER_BLOCK_UP", "ORDER_BLOCK_DOWN", "OB_TAP_UP", "OB_TAP_DOWN", "OTE_ENTRY_UP", "OTE_ENTRY_DOWN"} <= kinds
    for e in ev:
        if e.structure_type not in NEW:
            continue
        x = e.details
        for rid in ([e.reference_event_id] if e.reference_event_id else []) + list(x.get("basis") or []):
            assert by_id[rid].confirmed_bar_index <= e.confirmed_bar_index, (e.event_id, rid)
        if e.structure_type.startswith("ORDER_BLOCK_"):
            assert x["nen_dau"] <= x["nen_cuoi"] < x["nen_neo"] <= x["nen_xac_nhan"] == e.confirmed_bar_index
            assert x["lo"] < x["hi"] and by_id[e.reference_event_id].structure_type.startswith("SHIFT_")
        if e.structure_type.startswith(("OB_TAP", "OB_FAIL")):
            ob = by_id[e.reference_event_id]
            assert e.confirmed_bar_index > ob.confirmed_bar_index          # chỉ chạm từ nến sau lúc xác nhận
        if e.structure_type.startswith("OTE_ENTRY"):
            assert 0.62 - 1e-9 <= x["do_sau"] <= 1.0 and x["vung_lo"] < x["vung_hi"]
            assert x["nhip_atr"] >= 2.0 - 1e-9
    taps = {e.reference_event_id for e in ev if e.structure_type.startswith(("OB_TAP", "OB_FAIL", "OB_EXPIRED"))}
    assert len(taps) == len([e for e in ev if e.structure_type.startswith(("OB_TAP", "OB_FAIL", "OB_EXPIRED"))])
    for p in res.timeline:
        if p["ote_lo"] is not None:
            assert p["ote_dir"] in ("up", "down") and p["ote_lo"] < p["ote_hi"]


def test_nhan_qua_prefix_bang_full_ob_ote():
    bars = _random_bars(11, 900)
    full = run_algorithm(bars, IctStructureAlgorithm(**_p()))
    assert _types(full.events, "OB_TAP_UP") and _types(full.events, "OTE_ENTRY_DOWN")
    full_ev = [e.to_dict() for e in full.events]
    for cut in (150, 444, 777):
        part = run_algorithm(bars, IctStructureAlgorithm(**_p()), upto_index=cut)
        assert [e.to_dict() for e in part.events] == [e for e in full_ev if e["confirmed_bar_index"] <= cut]
        assert part.timeline == full.timeline[: cut + 1]
