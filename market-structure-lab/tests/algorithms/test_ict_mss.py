"""ict_structure 0.10.0 — MSS thay shift, order block là PD array (docs/plans/plan_mss_ob_pd.md).

Thành phần thử trên nến dựng tay (số tính tay ở chú thích); thuật toán thử trên dữ liệu ngẫu nhiên (bất biến + nhân quả). Chế độ
cũ (``doi_huong = shift``, ``ob_pd_array = false``) đã so tuyệt đối với 0.9.3 bằng mốc hồi quy (đặc tả §1 dòng 0.10.0).
"""
from __future__ import annotations

import pytest

from core.algorithms.ict_structure import LEGACY_0_9, IctStructureAlgorithm
from core.components.mss import MssTracker
from core.components.order_block import OrderBlockTracker
from core.components.order_flow import OB_FAIL, OrderFlow, reasons
from core.components.pd_array import PdArrayTracker, reaction
from core.engine import run_algorithm
from tests.algorithms.test_ict_ob_ote import RUN, _bar, _tracker
from tests.algorithms.test_ict_structure_g2 import _ohlc, _random_bars, _types

# ------------------------------------------------------------------ [E3] thành phần MSS

# #0–#7 nền thấp · #8, #9 chạy lên · #10 = nến sweep (lấy BSL 108 rồi close 107 quay lại) · #11 hồi · #12 close 99,5 < STL 100
ROWS = [(100.0, 101.0, 99.5, 100.5)] * 8 + [
    (100.5, 105.0, 100.4, 104.8),      # #8
    (104.8, 108.5, 104.5, 108.2),      # #9  nến lấy b
    (108.2, 110.0, 106.0, 107.0),      # #10 r: cực trị cú quét X = 110
    (107.0, 107.5, 101.0, 101.5),      # #11 close 101,5 > 100 — chưa phá
    (101.5, 102.0, 99.0, 99.5),        # #12 close 99,5 < 100 → quyết định
]


def _mss(swings=(("low", 1, 100.0, 5),), leg_atr=2.0):
    """Bộ theo dõi đã biết các swing (phía, cấp, giá, nến cực trị)."""
    tr = MssTracker(5, leg_atr)
    for side, lvl, price, bar in swings:
        tr.on_swing(side, lvl, price, bar, "%s%d@%d" % (side, lvl, bar))
    return tr


def _sweep(side="high", extreme=110.0, taken=9, r=10, level=108.0):
    return {"side": side, "level": level, "extreme": extreme, "taken": taken, "r": r, "sweep_id": "SW", "tier": "M15",
            "pool": {"id": "B1"}}


def _feed(tr, rows, upto, atr, add=(), gaps=(), at=10):
    """Nạp nến #0..upto; quét ``add`` (tham số add_from_sweep) ngay trước nến ``at``; trả kết quả của từng nến ≥ at."""
    out = {}
    for b in _ohlc(rows)[: upto + 1]:
        if b.index == at:
            for kw in add:
                tr.add_from_sweep(**kw)
        res = tr.on_bar(b, atr, b.index in gaps)
        if b.index >= at:
            out[b.index] = res
    return out


def test_mss_moc_la_stl_truoc_nen_lay_va_pha_bang_doan_manh_tinh_tay():
    tr = _mss((("low", 1, 98.0, 2), ("low", 1, 100.0, 5), ("low", 1, 104.5, 9), ("low", 2, 99.8, 3)))
    res = _feed(tr, ROWS, 12, 3.0, add=[_sweep()])
    assert res[10] == {} and res[11] == {} and tr.pending == []       # #12 quyết định → hết chờ
    (got,), leg = res[12]["down"]
    # mốc = STL gần nhất có nến cực trị < nến lấy #9: STL #5 (100), không phải #9 (cùng nến lấy) hay #2 (cũ hơn)
    assert (got.ref.price, got.ref.bar, got.sig.price, got.direction, got.level) == (100.0, 5, 99.8, "down", 108.0)
    # đoạn = 5 nến #8..#12, đỉnh đoạn H = 110 ở #10; H − close = 110 − 99,5 = 10,5 ≥ 2 × ATR 3 = 6
    assert leg["nen_dau"] == 10 and leg["cuc_tri"] == 110.0 and leg["so_nen"] == 3
    assert leg["bien_do"] == pytest.approx(10.5) and leg["bien_do_atr"] == pytest.approx(3.5)
    assert got.significant(99.5) and not got.significant(99.9)          # close < ITL 99,8 → significant
    assert tr.counts["thanh_mss"] == 1 and tr.counts["ung_vien"] == 1
    assert _mss(()).add_from_sweep(**_sweep()) is None                  # chưa có STL nào → không ứng viên
    tr.on_fvg(11, "down", "F11")
    assert tr.leg_fvg("down", 10, 12) == "F11" and tr.leg_fvg("down", 12, 12) is None and tr.leg_fvg("up", 10, 12) is None


def test_mss_pha_yeu_vuot_cuc_tri_khoang_trong_bang_nhau():
    weak = _mss(leg_atr=2.0)                                             # ATR 6 → cần 12 > 10,5: phá yếu, không có MSS
    assert _feed(weak, ROWS, 12, 6.0, add=[_sweep()])[12] == {} and weak.counts["pha_yeu"] == 1 and weak.pending == []
    over = ROWS[:11] + [(107.0, 110.5, 101.0, 101.5)]                    # #11 high 110,5 > X → huỷ
    tr = _mss()
    _feed(tr, over, 11, 3.0, add=[_sweep()])
    assert tr.pending == [] and tr.counts["huy_vuot_cuc_tri"] == 1
    eq = ROWS[:11] + [(107.0, 110.0, 100.0, 100.0)]                      # high = X, close = STL: không huỷ, chưa phá
    tr = _mss()
    _feed(tr, eq, 11, 3.0, add=[_sweep()])
    assert len(tr.pending) == 1 and tr.counts["huy_vuot_cuc_tri"] == 0
    tr = _mss()                                                          # khoảng trống trước #11 → huỷ
    _feed(tr, ROWS, 12, 3.0, add=[_sweep()], gaps=(11,))
    assert tr.pending == [] and tr.counts["huy_khoang_trong"] == 1


def test_mss_doan_khong_vat_qua_khoang_trong_va_gom_cung_chieu():
    tr = _mss()                                                          # khoảng trống trước #12: đoạn chỉ còn #12 (H = 102)
    res = _feed(tr, ROWS, 12, 1.0, add=[_sweep(r=12)], gaps=(12,), at=12)
    _cands, leg = res[12]["down"]
    assert leg["nen_dau"] == 12 and leg["bien_do"] == pytest.approx(2.5)
    tr = _mss((("low", 1, 98.0, 2), ("low", 1, 100.0, 5)))               # nến lấy #9 → mốc 100; nến lấy #4 → mốc 98: gom vào
    res = _feed(tr, ROWS, 12, 3.0, add=[_sweep(), _sweep(taken=4)])
    assert len(res[12]["down"][0]) == 1 and tr.pending == [] and tr.counts["gop_vao_mss"] == 1


def test_mss_tang_doi_xung():
    rows = [(100.0, 100.5, 99.0, 99.5)] * 8 + [
        (99.5, 99.6, 95.0, 95.2), (95.2, 95.5, 91.5, 91.8), (91.8, 94.0, 90.0, 93.0), (93.0, 99.0, 92.5, 98.5),
        (98.5, 101.0, 98.0, 100.5)]                                       # #12 close 100,5 > STH 100
    tr = _mss((("high", 1, 100.0, 5),))
    res = _feed(tr, rows, 12, 3.0, add=[_sweep("low", 90.0, level=92.0)])
    (c,), leg = res[12]["up"]
    assert c.direction == "up" and leg["nen_dau"] == 10 and leg["cuc_tri"] == 90.0 and leg["bien_do"] == pytest.approx(10.5)
    with pytest.raises(ValueError):
        MssTracker(0, 2.0)


# ------------------------------------------------------------------ [OF] order flow với MSS, OB hỏng


def test_order_flow_mss_lat_thang_va_ob_hong_vo_hieu():
    of = OrderFlow("mss", invalidate=True)
    assert of.on_bar(1, [("mss", 1, "M1")])["ly_do"] == "mss_tang" and of.state == 1
    assert of.on_bar(2, [(OB_FAIL, -1, "F0")]) is None and of.state == 1       # OB chiều ngược: không ảnh hưởng
    ch = of.on_bar(3, [(OB_FAIL, 1, "F1")])
    assert (ch["sang"], ch["ly_do"], ch["trigger"], of.state) == (0, "ob_hong", "F1", 0)
    assert of.on_bar(4, [("mss", -1, "M2"), (OB_FAIL, 1, "F2")])["ly_do"] == "mss_giam"   # có lật: OB hỏng bỏ qua
    of.on_bar(5, [("run", -1, "R1")])                                             # cùng chiều: chỉ ủng hộ
    assert of.state == -1 and of.last_support["su_kien"] == "R1"
    assert of.snapshot(5)["dieu_kien_vi"][-1].startswith("Order block của MSS")
    assert reasons("mss", True) == ("run_tang", "run_giam", "mss_tang", "mss_giam", "run_nguoc_chieu", "hai_chieu_cung_nen",
                                    "ob_hong")
    with pytest.raises(ValueError):
        OrderFlow("shift").on_bar(1, [("mss", 1, "x")])                          # chế độ shift không nhận MSS
    with pytest.raises(ValueError):
        OrderFlow("mss").on_bar(1, [(OB_FAIL, 1, "x")])                        # không bật vô hiệu


# ------------------------------------------------------------------ [E4] OB là PD array, breaker


def _ob(pd_mode="strict", expiry=10):
    """OB tăng [9,5; 10,5] từ chuỗi RUN (test 0.5.0), xác nhận ở #4."""
    tr, bars = _tracker(expiry=expiry, pd_mode=pd_mode, away_atr=1.0)
    ob = tr.create("up", bars[4], 0, "S")
    ob.event_id = "OB1"
    return tr, ob


_b = _bar


def test_ob_pd_cham_roi_giu_theo_luat_chat():
    tr, ob = _ob()
    done, new, taps, brs = tr.on_bar(_b(5, 10.7, 10.8, 10.4, 10.6), 0.5)          # low 10,4 ≤ 10,5: chạm, chưa có kết quả
    assert (done, taps, brs) == ([], [ob], []) and ob.tapped_at == 5 and ob.tap_deadline == 15
    done, *_ = tr.on_bar(_b(6, 10.6, 11.1, 10.6, 10.95), 0.5)                     # cần close ≥ 10,5 + 0,5 = 11 → chưa
    assert done == []
    done, *_ = tr.on_bar(_b(7, 10.95, 11.2, 10.9, 11.0), 0.5)                     # close 11,0 = ngưỡng → giữ
    assert done == [ob] and ob.ended == "respect" and tr.counts["respect"] == 1 and tr.open == []


def test_ob_pd_hong_thanh_breaker_va_breaker_giu():
    tr, ob = _ob()
    _done, _n, taps, _b2 = tr.on_bar(_b(5, 10.6, 10.6, 9.9, 10.0), 0.5)
    assert taps == [ob]
    done, _n, _t, brs = tr.on_bar(_b(6, 10.0, 10.1, 9.3, 9.4), 0.5)              # close 9,4 < 9,5: hỏng → breaker giảm
    (br,) = brs
    assert done == [ob] and ob.ended == "fail" and br.kind == "breaker" and br.direction == "down"
    assert (br.lo, br.hi, br.confirmed_at, br.anchor, br.anchor_id) == (9.5, 10.5, 6, 6, "OB1") and tr.open == [br]
    _d, _n, taps, _b2 = tr.on_bar(_b(7, 9.4, 9.8, 9.3, 9.6), 0.5)                # breaker giảm: high 9,8 ≥ 9,5 → chạm
    assert taps == [br]
    done, *_ = tr.on_bar(_b(8, 9.6, 9.6, 8.8, 8.9), 0.5)                          # close 8,9 ≤ 9,5 − 0,5 → giữ
    assert done == [br] and br.ended == "respect" and tr.counts["breaker"] == 1 and tr.counts["breaker_respect"] == 1


def test_hai_ob_cung_chieu_hong_cung_nen_cho_hai_breaker_khac_ma():
    """Bản cài đầu trùng event_id breaker khi hai OB tăng hỏng ở cùng một nến (dữ liệu thật XAUUSD) — mã kèm nến cuối OB."""
    bars = _ohlc(RUN)
    tr = OrderBlockTracker("nen_cuoi_rau", lookback=5, buffer=20, pd_mode="strict", away_atr=1.0)
    for b in bars[:4]:
        tr.push(b, False)
    a = tr.create("up", bars[4], 0, "S1")                  # nến giảm gần d nhất: #2 [9,4; 10,1]
    b = tr.create("up", bars[4], 0, "S2", before=2)        # chỉ xét nến < #2: #1 [9,8; 10,6]
    a.event_id, b.event_id = "OB_A", "OB_B"
    done, _n, _t, brs = tr.on_bar(_b(5, 9.5, 9.6, 8.0, 8.1), 0.5)  # chạm cả hai, close 8,1 thủng mép dưới cả hai
    assert sorted(o.event_id for o in done) == ["OB_A", "OB_B"] and len(brs) == 2
    assert len({(br.last_bar.index, br.anchor) for br in brs}) == 2 and {br.anchor_id for br in brs} == {"OB_A", "OB_B"}
    res = run_algorithm(_random_bars(31, 2500), IctStructureAlgorithm(**_mss_params()))
    assert len({e.event_id for e in res.events}) == len(res.events)


def test_ob_pd_ce_hong_o_mean_threshold_va_het_han_sau_cham():
    tr, ob = _ob("ce")
    done, _n, taps, brs = tr.on_bar(_b(5, 10.6, 10.6, 9.8, 9.9), 0.5)            # chạm và close 9,9 < MT 10,0 cùng nến
    assert taps == [ob] and done == [ob] and ob.ended == "fail" and len(brs) == 1 and tr.counts["fail"] == 1   # lý do MT ở sự kiện
    tr, ob = _ob(expiry=2)
    tr.on_bar(_b(5, 10.6, 10.6, 10.4, 10.6), 0.5)                                 # chạm ở #5 → hạn kết quả #7
    assert tr.on_bar(_b(6, 10.6, 10.7, 10.4, 10.6), 0.5)[0] == []
    done, *_ = tr.on_bar(_b(7, 10.6, 10.7, 10.4, 10.6), 0.5)
    assert done == [ob] and ob.ended == "expired_tapped"
    with pytest.raises(ValueError):
        OrderBlockTracker(pd_mode="sai")


def test_ob_pd_cua_so_mss_chan_tren_va_che_do_cu_giu_nguyen():
    bars = _ohlc(RUN)
    tr = OrderBlockTracker("than_chuoi", lookback=5, buffer=20, pd_mode="strict")
    for b in bars[:4]:
        tr.push(b, False)
    ob = tr.create("down", bars[4], 2, "M", before=3)        # MSS: chỉ xét nến ≤ #2 → nến tăng gần nhất là #0
    assert ob.last_bar.index == 0
    old = OrderBlockTracker("than_chuoi", lookback=5, buffer=20)
    assert old.on_bar(bars[4]) == ((), (), (), ()) and "respect" not in old.counts


# ------------------------------------------------------------------ [S5] pd_bias nhận kết quả OB


def test_reaction_dung_chung_luat_pd_array():
    """Hàm thuần dùng cho OB / breaker = đúng bảng luật PdArrayTracker (vùng tăng [10, 12], ATR 1, rời ≥ 1 ATR)."""
    assert reaction("up", 10, 12, 9.9, 1.0, "strict", 1.0) == "disrespect"      # thủng mép xa — xét trước
    assert reaction("up", 10, 12, 12.9, 1.0, "strict", 1.0) is None            # chưa rời đủ 1 ATR
    assert reaction("up", 10, 12, 13.0, 1.0, "strict", 1.0) == "respect"       # = mép gần + 1 ATR
    assert reaction("up", 10, 12, 13.0, None, "strict", 1.0) is None           # chưa có ATR
    assert reaction("up", 10, 12, 12.1, None, "loose", 1.0) == "respect"
    assert reaction("up", 10, 12, 10.9, None, "ce", 1.0) == "disrespect"       # ce: dưới 50% vùng
    assert reaction("down", 10, 12, 12.1, 1.0, "strict", 1.0) == "disrespect"
    assert reaction("down", 10, 12, 9.0, 1.0, "strict", 1.0) == "respect"


def test_pd_bias_gop_ket_qua_ob_cung_nen():
    pd = PdArrayTracker("strict", 1.0)
    bar = _b(3, 10.0, 10.2, 9.8, 10.1)
    assert pd.on_bar(bar, 0.5, [(1, "OB", "R1")]) == [] and (pd.bias, pd.bias_tf, pd.bias_since) == (1, "OB", 3)
    assert pd.bias_events == ["R1"]                                                # tracker ghi id kết quả OB
    pd.on_bar(_b(4, 10.0, 10.2, 9.8, 10.1), 0.5, [(1, "OB", "R2"), (-1, "OB", "F1")])
    assert pd.bias == 0 and pd.bias_tf is None
    pd.on_bar(_b(5, 10.0, 10.2, 9.8, 10.1), 0.5)                                  # không có kết quả: giữ nguyên
    assert pd.bias == 0 and pd.bias_since == 4


# ------------------------------------------------------------------ thuật toán: bất biến, nhân quả


def _mss_params(**kw):
    return {"timeframe": "M15", "session_calendar": "none", **kw}


@pytest.mark.parametrize("seed", [3, 4])
def test_bat_bien_mss_ob_pd_tren_du_lieu_ngau_nhien(seed):
    bars = _random_bars(seed, 1500)
    res = run_algorithm(bars, IctStructureAlgorithm(**_mss_params()))
    ev, tl = res.events, res.timeline
    by_id = {e.event_id: e for e in ev}
    assert len(by_id) == len(ev)
    kinds = {e.structure_type for e in ev}
    assert {"MSS_UP", "MSS_DOWN", "OB_RESPECT_UP", "OB_RESPECT_DOWN"} <= kinds and {"BREAKER_UP", "BREAKER_DOWN"} & kinds
    assert not {k for k in kinds if k.startswith("SHIFT_")}
    close = {b.index: b.close for b in bars}
    for e in ev:
        x, t = e.details, e.structure_type
        refs = ([e.reference_event_id] if e.reference_event_id else []) + list(x.get("basis") or [])
        for rid in refs:
            assert by_id[rid].confirmed_bar_index <= e.confirmed_bar_index, (e.event_id, rid)
        if t in ("MSS_UP", "MSS_DOWN"):
            down = t == "MSS_DOWN"
            c = close[e.confirmed_bar_index]
            assert e.price == x["moc_pha"] and (c < x["moc_pha"] if down else c > x["moc_pha"])
            assert by_id[x["moc_pha_id"]].structure_type == ("SWING_LOW" if down else "SWING_HIGH")
            assert by_id[e.reference_event_id].structure_type == ("LIQ_SWEEP_BSL" if down else "LIQ_SWEEP_SSL")
            for s in x["swept"]:
                assert s["nen_moc_pha"] < s["nen_lay"] <= s["nen_sweep"] <= e.confirmed_bar_index
            assert x["chan"]["bien_do_atr"] >= x["chan"]["nguong_atr"] and 1 <= x["chan"]["so_nen"] <= 5
            assert x["significant"] == (x["moc_significant"] is not None and
                                        (c < x["moc_significant"] if down else c > x["moc_significant"]))
        if t.startswith("MSS_FVG"):
            m = by_id[e.reference_event_id]
            assert m.confirmed_bar_index == e.confirmed_bar_index - 1 and m.direction == e.direction
        if t.startswith("ORDER_FLOW") and x["ly_do"] in ("mss_tang", "mss_giam"):
            assert by_id[e.reference_event_id].structure_type.startswith("MSS_")
        if t.startswith("ORDER_FLOW") and x["ly_do"] == "ob_hong":
            f = by_id[e.reference_event_id]
            assert f.structure_type.startswith("OB_FAIL") and f.confirmed_bar_index == e.confirmed_bar_index
            assert x["tu"] == (1 if f.direction == "up" else -1) and x["sang"] == 0
        if t in ("ORDER_BLOCK_UP", "ORDER_BLOCK_DOWN"):
            m = by_id[e.reference_event_id]
            assert x["neo"] == "mss" and m.structure_type.startswith("MSS_") and x["kieu"] == "ob"
            assert x["nen_cuoi"] < m.confirmed_bar_index                  # OB nằm trước nến phá (kể cả đoạn 1 nến)
        if t.startswith("BREAKER_"):
            src = by_id[e.reference_event_id]
            assert src.structure_type.startswith("ORDER_BLOCK_") and src.direction != e.direction
            fails = [f for f in _types(ev, "OB_FAIL_" + ("UP" if src.direction == "up" else "DOWN"))
                     if f.reference_event_id == src.event_id]
            assert [f.confirmed_bar_index for f in fails] == [e.confirmed_bar_index]
        if t.startswith("OB_RESPECT"):                       # giữ chỉ sau (hoặc cùng) nến chạm của chính vùng đó
            taps = [p for p in ev if p.structure_type.startswith("OB_TAP") and p.reference_event_id == e.reference_event_id]
            assert len(taps) == 1 and taps[0].confirmed_bar_index <= e.confirmed_bar_index
            pd_t = tl[e.confirmed_bar_index]
            same_bar = [p for p in ev if p.confirmed_bar_index == e.confirmed_bar_index and
                        p.structure_type.startswith(("PD_", "OB_RESPECT", "OB_FAIL"))]
            if len(same_bar) == 1:                            # kết quả duy nhất trong nến → pd_bias theo OB
                assert pd_t["pd_bias"] == (1 if e.direction == "up" else -1) and pd_t["pd_bias_tf"] == "OB"
    st = res.stats["chi_so_thuat_toan"]
    assert st["mss"]["so"] == len(_types(ev, "MSS_UP")) + len(_types(ev, "MSS_DOWN"))
    assert st["order_flow"]["theo_ly_do"]["ob_hong"] == sum(
        1 for e in ev if e.structure_type.startswith("ORDER_FLOW") and e.details["ly_do"] == "ob_hong")
    assert all(p["pending_mss"] >= 0 and "pending_shifts" not in p and "last_shift" not in p for p in tl)   # cột shift rỗng: bỏ
    assert "shift" not in st and "shift" not in run_algorithm(bars[:300], IctStructureAlgorithm(**_mss_params())).stats[
        "chi_so_thuat_toan"]


def test_nhan_qua_prefix_bang_full_mss():
    bars = _random_bars(7, 900)
    full = run_algorithm(bars, IctStructureAlgorithm(**_mss_params()))
    assert _types(full.events, "MSS_UP") and _types(full.events, "BREAKER_DOWN") + _types(full.events, "BREAKER_UP")
    full_ev = [e.to_dict() for e in full.events]
    for cut in (150, 420, 777, 899):
        part = run_algorithm(bars, IctStructureAlgorithm(**_mss_params()), upto_index=cut)
        assert [e.to_dict() for e in part.events] == [e for e in full_ev if e["confirmed_bar_index"] <= cut]
        assert part.timeline == full.timeline[: cut + 1]


def test_tham_so_mss_va_manifest():
    with pytest.raises(ValueError):
        IctStructureAlgorithm(**_mss_params(doi_huong="bos"))
    with pytest.raises(ValueError):
        IctStructureAlgorithm(**_mss_params(mss_chan_nen=0))
    m = IctStructureAlgorithm.manifest_info(IctStructureAlgorithm.validate_params(_mss_params()))
    assert m["doi_huong"]["su_kien"] == "mss" and m["doi_huong"]["chan_nen"] == 5 and m["order_block"]["pd_array"] is True
    assert "MSS" in m["khong_co"]
    legacy = IctStructureAlgorithm.manifest_info(IctStructureAlgorithm.validate_params(
        _mss_params(**LEGACY_0_9)))
    assert legacy["doi_huong"] == {"su_kien": "shift", "cua_so_shift": 3} and "shift" in legacy["khong_co"]


def test_ob_pd_che_do_ce_ghi_ly_do_mean_threshold_va_dol_khoa_mss():
    res = run_algorithm(_random_bars(5, 1500), IctStructureAlgorithm(**_mss_params(pd_respect_mode="ce")))
    fails = [e for e in res.events if e.structure_type.startswith("OB_FAIL")]
    assert fails and {e.reason_code for e in fails} == {"OB_CLOSE_BEYOND_MEAN_THRESHOLD"}
    assert all(e.details["ket_cuc"] == "fail" and "mean threshold" in e.details["ket_cuc_vi"] for e in fails)
    dol = [e for e in res.events if e.structure_type == "DOL_REACHED"]
    assert dol and all("mss" in e.details and "shift" not in e.details and "so_nen_tu_mss" in e.details for e in dol)
    st = res.stats["chi_so_thuat_toan"]["dol"]
    assert "mss" in st and "shift" not in st


def test_ob_neo_displacement_khong_vo_hieu_order_flow_va_ghi_chu_dung_che_do():
    bars = _random_bars(4, 1500)
    disp = run_algorithm(bars, IctStructureAlgorithm(**_mss_params(ob_neo="displacement")))
    st = disp.stats["chi_so_thuat_toan"]["order_flow"]
    assert "ob_hong" not in st["theo_ly_do"] and "OB" not in st["ghi_chu_vi"] and "MSS" in st["ghi_chu_vi"]
    sh = run_algorithm(bars, IctStructureAlgorithm(**_mss_params(doi_huong="shift")))         # shift + OB là PD array
    note = sh.stats["chi_so_thuat_toan"]["order_flow"]["ghi_chu_vi"]
    assert "run + shift" in note and "OB của shift" in note and "MSS" not in note
    m = IctStructureAlgorithm.manifest_info(IctStructureAlgorithm.validate_params(_mss_params(doi_huong="shift")))
    assert m["order_flow"] == note
