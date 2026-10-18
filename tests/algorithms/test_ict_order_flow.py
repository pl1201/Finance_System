"""ict_structure v0.3.0 — order flow đọc theo thanh khoản: run + shift, run phía ngược → chưa rõ (quy tắc A).

Thành phần ``OrderFlow`` thử từng ô của bảng quy tắc; thuật toán thử trên chuỗi nến dựng tay (ATR Wilder
chu kỳ 2, tính tay ở chú thích) và trên dữ liệu ngẫu nhiên có khoảng trống: quy tắc A cài lại độc lập
khớp timeline từng nến, ``ORDER_FLOW_*`` đúng chỗ đổi, thống kê khớp số tính độc lập, nhân quả,
``pending_state`` là bản sao.
"""
from __future__ import annotations

import copy
import statistics
from collections import Counter, defaultdict
from itertools import groupby

import pytest

from core.algorithms.ict_structure import IctStructureAlgorithm
from core.components.order_flow import OrderFlow
from core.engine import run_algorithm
from core.types import Bar
from tests.algorithms.test_ict_structure_g2 import BASE, _algo, _expected_atr, _ohlc, _one, _p, _random_bars, _types

#: Đầu vào order flow (đặc tả §1) và loại sự kiện đầu ra → giá trị mới.
OF_IN = {"LIQ_RUN_UP": ("run", 1), "LIQ_RUN_DOWN": ("run", -1), "SHIFT_UP": ("shift", 1), "SHIFT_DOWN": ("shift", -1)}
OF_OUT = {"ORDER_FLOW_UP": 1, "ORDER_FLOW_DOWN": -1, "ORDER_FLOW_UNCLEAR": 0}
OF_DIR = {1: "up", -1: "down", 0: None}
OF_RC = {"run_tang": "OF_RUN", "run_giam": "OF_RUN", "shift_tang": "OF_SHIFT", "shift_giam": "OF_SHIFT",
         "run_nguoc_chieu": "OF_OPPOSITE_RUN", "hai_chieu_cung_nen": "OF_BOTH_SIDES"}
TEXT = {1: "tăng", -1: "giảm", 0: "chưa rõ", None: "chưa có"}
DK_TANG = ["Run vùng phía dưới (SSL) → chưa rõ", "Shift giảm (quét BSL rồi displacement giảm) → giảm",
           "Run/shift hai chiều trong cùng một nến → chưa rõ"]
DK_CHUA_RO = ["Run hoặc shift kế tiếp đặt chiều (lên → tăng, xuống → giảm)"]


# ------------------------------------------------------------------ thành phần: bảng quy tắc


def _start(state):
    """OrderFlow đang ở ``state`` sau các nến 0–1 (None = chưa có sự kiện nào)."""
    of = OrderFlow()
    if state == 1:
        of.on_bar(0, [("run", 1, "a")])
    elif state == -1:
        of.on_bar(0, [("run", -1, "a")])
    elif state == 0:
        of.on_bar(0, [("run", 1, "a")])
        of.on_bar(1, [("run", -1, "b")])                 # tăng + run xuống → chưa rõ
    assert of.state == state
    return of


RU, RD, SU, SD = ("run", 1, "ru"), ("run", -1, "rd"), ("shift", 1, "su"), ("shift", -1, "sd")


@pytest.mark.parametrize("start, events, sang, ly_do, trigger", [
    (None, [RU], 1, "run_tang", "ru"),
    (None, [RD], -1, "run_giam", "rd"),
    (None, [SD], -1, "shift_giam", "sd"),
    (1, [RD], 0, "run_nguoc_chieu", "rd"),            # run phía ngược → chưa rõ, không lật ngay
    (0, [RD], -1, "run_giam", "rd"),
    (0, [RU], 1, "run_tang", "ru"),
    (-1, [RU], 0, "run_nguoc_chieu", "ru"),
    (1, [SD], -1, "shift_giam", "sd"),                # shift lật thẳng
    (-1, [SU], 1, "shift_tang", "su"),
    (0, [SU], 1, "shift_tang", "su"),
    (1, [RD, SU], 0, "hai_chieu_cung_nen", None),     # hai chiều cùng nến thắng cả shift
    (-1, [RU, RD], 0, "hai_chieu_cung_nen", None),
    (None, [RU, SD], 0, "hai_chieu_cung_nen", None),
    (-1, [RU, SU], 1, "shift_tang", "su"),            # run + shift cùng chiều: kích hoạt = shift
    (None, [RD, SD], -1, "shift_giam", "sd"),
])
def test_bang_quy_tac_doi_trang_thai(start, events, sang, ly_do, trigger):
    of = _start(start)
    old_since = of.since
    ch = of.on_bar(5, events)
    assert ch == {
        "nen": 5, "tu": start, "sang": sang, "ly_do": ly_do, "trigger": trigger,
        "basis": [e[2] for e in events],
        "trang_thai_cu_tu_nen": old_since,
        "trang_thai_cu_so_nen": None if old_since is None else 5 - old_since,
    }
    assert (of.state, of.since, of.reason, of.trigger_id, of.last_support) == (sang, 5, ly_do, trigger, None)


@pytest.mark.parametrize("start, events, support", [
    (1, [RU], {"nen": 5, "su_kien": "ru", "loai": "run"}),
    (1, [SU], {"nen": 5, "su_kien": "su", "loai": "shift"}),
    (-1, [RD], {"nen": 5, "su_kien": "rd", "loai": "run"}),
    (1, [RU, SU], {"nen": 5, "su_kien": "su", "loai": "shift"}),
    (0, [RU, RD], None),                               # đang chưa rõ + hai chiều → vẫn chưa rõ, không «ủng hộ» ai
    (1, [], None),
    (None, [], None),
])
def test_khong_doi_chi_ung_ho(start, events, support):
    of = _start(start)
    before = (of.state, of.since, of.reason, of.trigger_id)
    assert of.on_bar(5, events) is None
    assert (of.state, of.since, of.reason, of.trigger_id) == before
    assert of.last_support == support


def test_ung_ho_xoa_khi_doi_snapshot_la_ban_sao_va_reset():
    of = _start(1)
    of.on_bar(3, [RU])
    assert of.last_support == {"nen": 3, "su_kien": "ru", "loai": "run"}
    above, below = {"id": "B1", "muc": 101.0}, {"id": "S2", "muc": 99.0}
    s = of.snapshot(7, above, below)
    assert s == {
        "trang_thai": 1, "trang_thai_vi": "tăng", "tu_nen": 0, "so_nen": 7, "ly_do": "run_tang",
        "ly_do_vi": "Run lên: lấy BSL, close không quay lại trong cửa sổ", "su_kien": "a",
        "ung_ho_gan_nhat": {"nen": 3, "su_kien": "ru", "loai": "run"},
        "vung_cung_chieu": above, "vung_nguoc_chieu": below, "dieu_kien_vi": DK_TANG,
    }
    s["ung_ho_gan_nhat"]["nen"] = -1
    s["dieu_kien_vi"].append("x")
    assert of.last_support["nen"] == 3 and of.snapshot(7)["dieu_kien_vi"] == DK_TANG
    of.on_bar(8, [SD])                                  # shift giảm: lật thẳng, xoá «ủng hộ»
    s = of.snapshot(9, above, below)
    assert (s["trang_thai"], s["tu_nen"], s["so_nen"], s["su_kien"], s["ung_ho_gan_nhat"]) == (-1, 8, 1, "sd", None)
    assert s["vung_cung_chieu"] is below and s["vung_nguoc_chieu"] is above      # giảm: cùng chiều = SSL phía dưới
    of.on_bar(9, [RU])                                  # run lên ngược chiều → chưa rõ: không gán vùng nào
    s = of.snapshot(9, above, below)
    assert (s["trang_thai_vi"], s["vung_cung_chieu"], s["vung_nguoc_chieu"], s["dieu_kien_vi"]) == (
        "chưa rõ", None, None, DK_CHUA_RO)
    of.reset()
    assert of.snapshot(None) == {
        "trang_thai": None, "trang_thai_vi": "chưa có", "tu_nen": None, "so_nen": None, "ly_do": None,
        "ly_do_vi": None, "su_kien": None, "ung_ho_gan_nhat": None, "vung_cung_chieu": None,
        "vung_nguoc_chieu": None, "dieu_kien_vi": ["Run hoặc shift đầu tiên đặt chiều"],
    }
    assert of.on_bar(0, [RD])["tu"] is None             # sau reset nhận lại từ nến 0


def test_dau_vao_sai_bi_tu_choi():
    of = OrderFlow()
    with pytest.raises(ValueError, match="sai dạng"):
        of.on_bar(0, [("sweep", 1, "x")])
    with pytest.raises(ValueError, match="sai dạng"):
        of.on_bar(1, [("run", 0, "x")])
    of.on_bar(2, [RU])
    with pytest.raises(ValueError, match="tăng dần"):
        of.on_bar(2, [RD])


# ------------------------------------------------------------------ thuật toán: chuỗi dựng tay


def test_chuoi_base_shift_giam_roi_shift_tang():
    """BASE (test_ict_structure_g2): SHIFT_DOWN ở #8, SHIFT_UP ở #9, không có run."""
    res = run_algorithm(_ohlc(BASE), _algo())
    ev = res.events
    assert not _types(ev, "LIQ_RUN_UP") and not _types(ev, "LIQ_RUN_DOWN") and not _types(ev, "ORDER_FLOW_UNCLEAR")
    sd, su = _one(ev, "SHIFT_DOWN"), _one(ev, "SHIFT_UP")
    down, up = _one(ev, "ORDER_FLOW_DOWN"), _one(ev, "ORDER_FLOW_UP")
    assert (down.event_id, down.event_bar_index, down.confirmed_bar_index, down.price, down.direction) == (
        "ict:ORDER_FLOW_DOWN@8>8", 8, 8, 98.8, "down")                          # giá = close #8
    assert down.reason_code == "OF_SHIFT" and down.reference_event_id == sd.event_id
    assert {k: v for k, v in down.details.items() if k != "htf"} == {     # «htf» (0.4.0): xem test_ict_htf.py
        "tu": None, "sang": -1, "tu_vi": "chưa có", "sang_vi": "giảm", "ly_do": "shift_giam",
        "ly_do_vi": "Shift giảm: quét BSL rồi displacement giảm", "basis": [sd.event_id],
        "trang_thai_cu_tu_nen": None, "trang_thai_cu_so_nen": None, "killzone": "london_close",
    }
    assert (up.event_id, up.price, up.direction, up.reason_code, up.reference_event_id) == (
        "ict:ORDER_FLOW_UP@9>9", 100.6, "up", "OF_SHIFT", su.event_id)          # shift lật thẳng giảm → tăng
    x = up.details
    assert (x["tu"], x["sang"], x["tu_vi"], x["sang_vi"], x["ly_do"], x["basis"]) == (
        -1, 1, "giảm", "tăng", "shift_tang", [su.event_id])
    assert (x["trang_thai_cu_tu_nen"], x["trang_thai_cu_so_nen"]) == (8, 1)
    # bước 6b: sau shift và SHIFT_FVG của nến đó
    ids = [e.event_id for e in ev]
    assert ids.index(up.event_id) > max(ids.index(su.event_id), ids.index(_one(ev, "SHIFT_FVG_DOWN").event_id))
    tl = res.timeline
    assert [p["order_flow"] for p in tl] == [None] * 8 + [-1, 1]
    assert [p["order_flow_since"] for p in tl] == [None] * 8 + [8, 9]
    assert [p["order_flow_reason"] for p in tl] == [None] * 8 + ["shift_giam", "shift_tang"]
    st = res.stats["chi_so_thuat_toan"]["order_flow"]
    assert st["ty_le_thoi_gian"] == pytest.approx({"tang": 0.1, "giam": 0.1, "chua_ro": 0.0, "chua_co": 0.8})
    assert (st["doi_trang_thai"], st["doi_chieu"], st["doi_chieu_moi_ngay"], st["doan_chua_ro"]) == (2, 1, 1.0, 0)
    assert (st["mot_chieu_trung_vi_nen"], st["mot_chieu_trung_vi_gio"], st["chua_ro_trung_vi_nen"]) == (1.0, 0.25, None)
    assert st["theo_ly_do"] == {"run_tang": 0, "run_giam": 0, "shift_tang": 1, "shift_giam": 1,
                                "run_nguoc_chieu": 0, "hai_chieu_cung_nen": 0}


# BASE[:7] dựng B0 = 102 (ITH #3, biết ở #6) và S1 = 99.3 (ITL #4, biết ở #7, hiệu lực từ #8). ATR Wilder
# chu kỳ 2 sau từng nến (TR theo close trước): #6 1.634375 · #7 2.1171875 · #8 1.40859375 (TR 0.7) ·
# #9 1.004296875 (TR 0.6) · #10 0.8021484375 (TR 0.6) · #11 2.60107421875 (TR 4.4) · #12 1.625537109375
# (TR 0.65) · #13 1.1627685546875 (TR 0.7). Không có sweep nào → không có shift.
RUN_SEQ = BASE[:7] + [
    (101.0, 102.6, 101.0, 102.4),   # #7 lấy B0: xuyên 0.6 ≥ 0.1 × ATR[6] 1.634; close 102.4 ≥ 102 → chờ (W = 3)
    (102.4, 102.9, 102.2, 102.8),   # #8 close ≥ 102
    (102.8, 103.2, 102.6, 103.0),   # #9 close ≥ 102
    (103.0, 103.5, 102.9, 103.3),   # #10 = 7 + 3, chưa quay lại → LIQ_RUN_UP → order flow chưa có → tăng (run_tang)
    (103.3, 103.4, 99.0, 99.1),     # #11 lấy S1: xuyên 0.3 ≥ 0.1 × ATR[10] 0.802; close 99.1 ≤ 99.3 → chờ.
                                    #     biên độ 4.4 ≥ 1.5 × 0.802 → displacement giảm, không có sweep → không shift
    (99.1, 99.25, 98.6, 98.8),      # #12 close ≤ 99.3
    (98.8, 99.0, 98.3, 98.5),       # #13 close ≤ 99.3
    (98.5, 98.7, 98.0, 98.2),       # #14 = 11 + 3 → LIQ_RUN_DOWN, ngược order flow tăng → chưa rõ (run_nguoc_chieu)
]


def test_chuoi_run_tang_roi_run_nguoc_chieu_thanh_chua_ro():
    atr_prev = _expected_atr(RUN_SEQ)                      # ATR[t−1] dùng ở nến t
    assert atr_prev[7] == pytest.approx(1.634375) and atr_prev[11] == pytest.approx(0.8021484375)
    assert atr_prev[12] == pytest.approx(2.60107421875) and atr_prev[14] == pytest.approx(1.1627685546875)
    bars = _ohlc(RUN_SEQ)
    res = run_algorithm(bars, _algo())
    ev = res.events
    assert _one(ev, "DISPLACEMENT_DOWN").event_bar_index == 11 and not _types(ev, "SHIFT_DOWN")
    assert not _types(ev, "SHIFT_UP") and not _types(ev, "LIQ_SWEEP_BSL") and not _types(ev, "LIQ_SWEEP_SSL")
    run_up, run_dn = _one(ev, "LIQ_RUN_UP"), _one(ev, "LIQ_RUN_DOWN")
    assert (run_up.event_bar_index, run_up.confirmed_bar_index, run_up.details["vung"]) == (7, 10, "B0")
    assert (run_dn.event_bar_index, run_dn.confirmed_bar_index, run_dn.details["vung"]) == (11, 14, "S1")
    up = _one(ev, "ORDER_FLOW_UP")
    assert (up.event_id, up.price, up.direction, up.reason_code, up.reference_event_id) == (
        "ict:ORDER_FLOW_UP@10>10", 103.3, "up", "OF_RUN", run_up.event_id)
    assert (up.details["tu"], up.details["sang"], up.details["ly_do"], up.details["basis"]) == (
        None, 1, "run_tang", [run_up.event_id])
    unc = _one(ev, "ORDER_FLOW_UNCLEAR")
    assert (unc.event_id, unc.price, unc.direction, unc.reason_code, unc.reference_event_id) == (
        "ict:ORDER_FLOW_UNCLEAR@14>14", 98.2, None, "OF_OPPOSITE_RUN", run_dn.event_id)
    x = unc.details
    assert (x["tu"], x["sang"], x["tu_vi"], x["sang_vi"], x["ly_do"], x["basis"]) == (
        1, 0, "tăng", "chưa rõ", "run_nguoc_chieu", [run_dn.event_id])
    assert (x["trang_thai_cu_tu_nen"], x["trang_thai_cu_so_nen"]) == (10, 4)
    assert not _types(ev, "ORDER_FLOW_DOWN")              # run ngược chiều không lật thẳng sang giảm
    tl = res.timeline
    assert [p["order_flow"] for p in tl] == [None] * 10 + [1] * 4 + [0]
    assert [p["order_flow_since"] for p in tl] == [None] * 10 + [10] * 4 + [14]
    assert [p["order_flow_reason"] for p in tl] == [None] * 10 + ["run_tang"] * 4 + ["run_nguoc_chieu"]
    # trạng thái replay: #10 tăng — chưa có BSL nào còn nguyên phía trên; vùng ngược chiều = S1 phía dưới
    algo = _algo()
    run_algorithm(bars, algo, upto_index=10)
    s = algo.pending_state()["order_flow"]
    assert (s["trang_thai"], s["trang_thai_vi"], s["tu_nen"], s["so_nen"], s["ly_do"], s["su_kien"]) == (
        1, "tăng", 10, 0, "run_tang", run_up.event_id)
    assert s["ung_ho_gan_nhat"] is None and s["vung_cung_chieu"] is None and s["dieu_kien_vi"] == DK_TANG
    assert (s["vung_nguoc_chieu"]["id"], s["vung_nguoc_chieu"]["phia"], s["vung_nguoc_chieu"]["muc"]) == ("S1", "SSL", 99.3)
    run_algorithm(bars, algo, upto_index=13)               # S1 đã bị lấy ở #11 (đang chờ) → không còn vùng
    s = algo.pending_state()["order_flow"]
    assert (s["trang_thai"], s["so_nen"], s["vung_cung_chieu"], s["vung_nguoc_chieu"]) == (1, 3, None, None)
    run_algorithm(bars, algo)
    s = algo.pending_state()["order_flow"]
    assert (s["trang_thai"], s["tu_nen"], s["so_nen"], s["ly_do"], s["su_kien"], s["dieu_kien_vi"]) == (
        0, 14, 0, "run_nguoc_chieu", run_dn.event_id, DK_CHUA_RO)
    st = res.stats["chi_so_thuat_toan"]["order_flow"]
    assert st["ty_le_thoi_gian"] == pytest.approx({"tang": 4 / 15, "giam": 0.0, "chua_ro": 1 / 15, "chua_co": 10 / 15})
    assert (st["doi_trang_thai"], st["doi_chieu"], st["doan_chua_ro"], st["doan_chua_ro_moi_ngay"]) == (2, 0, 1, 1.0)
    assert (st["chua_ro_trung_vi_nen"], st["chua_ro_trung_vi_gio"]) == (1.0, 0.25)        # đoạn cuối đang mở được tính
    assert (st["mot_chieu_trung_vi_nen"], st["mot_chieu_trung_vi_gio"]) == (4.0, 1.0)
    assert st["theo_ly_do"]["run_tang"] == 1 and st["theo_ly_do"]["run_nguoc_chieu"] == 1


# ------------------------------------------------------------------ dữ liệu ngẫu nhiên


SEEDS = (14, 23)       # mỗi seed có đủ sáu lý do, gồm một lần hai chiều cùng nến (run + shift ngược chiều)


def _inputs_by_bar(events):
    out = defaultdict(list)
    for e in events:
        if e.structure_type in OF_IN:
            out[e.confirmed_bar_index].append(e)
    return out


def _rule_a(n, by_bar):
    """Quy tắc A cài lại độc lập (như ``rule_a`` của script khảo sát: 0 cả lúc khởi động)."""
    s, out = 0, []
    for t in range(n):
        evs = [OF_IN[e.structure_type] for e in by_bar.get(t, ())]
        if evs:
            dirs = {d for _k, d in evs}
            if len(dirs) == 2:
                s = 0
            else:
                d = dirs.pop()
                s = d if ("shift", d) in evs or s in (0, d) else 0
        out.append(s)
    return out


@pytest.mark.parametrize("seed", SEEDS)
def test_quy_tac_a_doc_lap_khop_timeline_va_su_kien_dung_cho_doi(seed):
    bars = _random_bars(seed, 1500)
    res = run_algorithm(bars, IctStructureAlgorithm(**_p()))
    ev, tl = res.events, res.timeline
    by_id = {e.event_id: e for e in ev}
    by_bar = _inputs_by_bar(ev)
    vals = [p["order_flow"] for p in tl]
    # (a) từng nến khớp quy tắc A độc lập (None ≡ 0); None chỉ trước run/shift đầu tiên
    assert [0 if v is None else v for v in vals] == _rule_a(len(bars), by_bar)
    first = min(by_bar)
    assert all((v is None) == (t < first) for t, v in enumerate(vals))
    # (b) ORDER_FLOW_* đúng ở các nến timeline đổi giá trị, tu/sang khớp
    changes = [(t, a, b) for t, (a, b) in enumerate(zip([None] + vals[:-1], vals)) if a != b]
    flows = [e for e in ev if e.structure_type in OF_OUT]
    assert [(e.confirmed_bar_index, e.details["tu"], e.details["sang"]) for e in flows] == changes
    reasons = Counter(e.details["ly_do"] for e in flows)
    assert set(reasons) == set(OF_RC)                       # đủ sáu lý do trên dữ liệu này
    ids = [e.event_id for e in ev]
    for e in flows:
        t, x = e.confirmed_bar_index, e.details
        assert OF_OUT[e.structure_type] == x["sang"] and e.direction == OF_DIR[x["sang"]]
        assert e.event_id == "ict:%s@%d>%d" % (e.structure_type, t, t) and e.event_bar_index == t
        assert e.price == bars[t].close and e.reason_code == OF_RC[x["ly_do"]]
        assert (x["tu_vi"], x["sang_vi"]) == (TEXT[x["tu"]], TEXT[x["sang"]])
        assert (tl[t]["order_flow_since"], tl[t]["order_flow_reason"]) == (t, x["ly_do"])
        old_since = tl[t - 1]["order_flow_since"] if t > 0 else None
        assert x["trang_thai_cu_tu_nen"] == old_since
        assert x["trang_thai_cu_so_nen"] == (None if old_since is None else t - old_since)
        # (c) basis = mọi run/shift xác nhận ở chính nến t, theo thứ tự phát; tham chiếu thuộc basis
        here = by_bar[t]
        assert x["basis"] == [i.event_id for i in here] and here
        assert all(by_id[i].confirmed_bar_index == t for i in x["basis"])
        assert ids.index(e.event_id) > max(ids.index(i) for i in x["basis"])
        dirs = {OF_IN[i.structure_type][1] for i in here}
        ref = e.reference_event_id
        if x["ly_do"] == "hai_chieu_cung_nen":
            assert ref is None and dirs == {1, -1} and x["sang"] == 0
        else:
            assert ref in x["basis"] and len(dirs) == 1
            kind = OF_IN[by_id[ref].structure_type][0]
            has_shift = any(OF_IN[i.structure_type][0] == "shift" for i in here)
            assert kind == ("shift" if has_shift else "run") and x["ly_do"].startswith(kind)
    # trạng thái chỉ đổi ở nến có run/shift; since/reason giữ nguyên giữa hai lần đổi
    for t in range(1, len(tl)):
        if t not in {c[0] for c in changes}:
            assert (tl[t]["order_flow_since"], tl[t]["order_flow_reason"]) == (
                tl[t - 1]["order_flow_since"], tl[t - 1]["order_flow_reason"])


@pytest.mark.parametrize("seed", SEEDS)
def test_thong_ke_order_flow_khop_so_tinh_doc_lap_tu_timeline(seed):
    bars = _random_bars(seed, 1500)
    res = run_algorithm(bars, IctStructureAlgorithm(**_p()))
    stats = res.stats["chi_so_thuat_toan"]
    st, days = stats["order_flow"], stats["so_ngay_giao_dich"]
    vals = [p["order_flow"] for p in res.timeline]
    n = len(vals)
    assert st["ty_le_thoi_gian"] == pytest.approx(
        {"tang": vals.count(1) / n, "giam": vals.count(-1) / n, "chua_ro": vals.count(0) / n,
         "chua_co": vals.count(None) / n})
    assert sum(st["ty_le_thoi_gian"].values()) == pytest.approx(1.0)
    segs = [(v, len(list(g))) for v, g in groupby(vals) if v is not None]     # bỏ đoạn None đầu; gồm đoạn cuối
    sides = [v for v, _k in segs if v != 0]
    flips = sum(1 for a, b in zip(sides, sides[1:]) if a != b)
    zero = [k for v, k in segs if v == 0]
    one_way = [k for v, k in segs if v != 0]
    flows = [e for e in res.events if e.structure_type in OF_OUT]
    assert st["doi_trang_thai"] == len(flows) == len(segs)
    assert (st["doi_chieu"], st["doan_chua_ro"]) == (flips, len(zero)) and flips > 5
    assert st["doi_chieu_moi_ngay"] == pytest.approx(flips / days)
    assert st["doan_chua_ro_moi_ngay"] == pytest.approx(len(zero) / days)
    assert st["chua_ro_trung_vi_nen"] == pytest.approx(statistics.median(zero))
    assert st["chua_ro_trung_vi_gio"] == pytest.approx(statistics.median(zero) * 0.25)      # M15
    assert st["mot_chieu_trung_vi_nen"] == pytest.approx(statistics.median(one_way))
    assert st["mot_chieu_trung_vi_gio"] == pytest.approx(statistics.median(one_way) * 0.25)
    counts = Counter(e.details["ly_do"] for e in flows)
    assert st["theo_ly_do"] == {k: counts.get(k, 0) for k in OF_RC}
    assert "không phải dự báo" in st["ghi_chu_vi"]


def test_nhan_qua_prefix_bang_full_va_sua_duoi_khong_doi_qua_khu():
    bars = _random_bars(23, 1200)
    full = run_algorithm(bars, IctStructureAlgorithm(**_p()))
    full_ev = [e.to_dict() for e in full.events]
    flow_bars = [e.confirmed_bar_index for e in full.events if e.structure_type in OF_OUT]
    both = [e.confirmed_bar_index for e in full.events if e.structure_type == "ORDER_FLOW_UNCLEAR"
            and e.details["ly_do"] == "hai_chieu_cung_nen"]
    assert both and len(flow_bars) > 20
    cuts = sorted({150, 517, 1199, flow_bars[3], flow_bars[3] - 1, flow_bars[12] - 2, both[0], both[0] - 1})
    for cut in cuts:
        part = run_algorithm(bars, IctStructureAlgorithm(**_p()), upto_index=cut)
        assert [e.to_dict() for e in part.events] == [e for e in full_ev if e["confirmed_bar_index"] <= cut]
        assert part.timeline == full.timeline[: cut + 1]           # gồm order_flow / _since / _reason
        if cut == len(bars) - 1:
            continue
        tail = _random_bars(cut + 1000, len(bars) - cut - 1, gaps=False)
        changed = list(bars[: cut + 1]) + [
            Bar(index=cut + 1 + k, bar_time=bars[cut + 1 + k].bar_time, close_time=bars[cut + 1 + k].close_time,
                open=b.open, high=b.high, low=b.low, close=b.close, volume=b.volume) for k, b in enumerate(tail)]
        other = run_algorithm(changed, IctStructureAlgorithm(**_p()))
        assert [e.to_dict() for e in other.events if e.confirmed_bar_index <= cut] == \
               [e for e in full_ev if e["confirmed_bar_index"] <= cut]
        assert other.timeline[: cut + 1] == full.timeline[: cut + 1]


@pytest.mark.parametrize("seed", SEEDS)
def test_pending_state_order_flow_khop_timeline_va_la_ban_sao(seed):
    bars = _random_bars(seed, 1500)
    full = run_algorithm(bars, IctStructureAlgorithm(**_p()))
    tl = full.timeline
    algo = IctStructureAlgorithm(**_p())
    algo.reset()
    events, timeline, seen = [], [], Counter()
    for b in bars:
        events.extend(algo.on_bar(b))
        timeline.append(dict(algo.timeline_point(b), bar_index=b.index, time=int(b.bar_time.timestamp())))
        if b.index % 7:
            continue
        t, p = b.index, tl[b.index]
        ps = algo.pending_state()
        s = ps["order_flow"]
        state, since = p["order_flow"], p["order_flow_since"]
        assert (s["trang_thai"], s["trang_thai_vi"], s["tu_nen"], s["ly_do"]) == (
            state, TEXT[state], since, p["order_flow_reason"])
        assert s["so_nen"] == (None if since is None else t - since)
        flows = [e for e in events if e.structure_type in OF_OUT]
        assert s["su_kien"] == (flows[-1].reference_event_id if flows else None)
        above, below = (s["vung_cung_chieu"], s["vung_nguoc_chieu"]) if state != -1 else (
            s["vung_nguoc_chieu"], s["vung_cung_chieu"])
        if state in (1, -1):
            assert (above or {}).get("id") == p["liq_above_id"] and (below or {}).get("id") == p["liq_below_id"]
            assert (above or {}).get("muc") == p["liq_above"] and (below or {}).get("muc") == p["liq_below"]
            seen["vung"] += s["vung_cung_chieu"] is not None and s["vung_nguoc_chieu"] is not None
            # ủng hộ = run/shift gần nhất sau nến đổi (đều cùng chiều, vì không làm đổi trạng thái)
            after = [e for e in events if e.structure_type in OF_IN and e.confirmed_bar_index > since]
            assert all(OF_IN[e.structure_type][1] == state for e in after)
            want = None
            if after:
                last = [e for e in after if e.confirmed_bar_index == after[-1].confirmed_bar_index]
                pick = next((e for e in last if e.structure_type.startswith("SHIFT")), last[0])
                want = {"nen": pick.confirmed_bar_index, "su_kien": pick.event_id, "loai": OF_IN[pick.structure_type][0]}
            assert s["ung_ho_gan_nhat"] == want
            seen["ung_ho"] += want is not None
        else:
            assert s["vung_cung_chieu"] is None and s["vung_nguoc_chieu"] is None and s["ung_ho_gan_nhat"] is None
            seen["chua_ro" if state == 0 else "chua_co"] += 1
        # sửa dict trả về không ảnh hưởng thuật toán
        keep = copy.deepcopy(ps)
        s["trang_thai"] = 99
        s["dieu_kien_vi"].append("x")
        for k in ("ung_ho_gan_nhat", "vung_cung_chieu", "vung_nguoc_chieu"):
            if s[k]:
                s[k]["nen" if k == "ung_ho_gan_nhat" else "muc"] = -1
                if k != "ung_ho_gan_nhat":
                    s[k]["nguon"].append("x")
        assert algo.pending_state() == keep
    assert seen["vung"] and seen["ung_ho"] and seen["chua_ro"] and seen["chua_co"]
    assert [e.to_dict() for e in events] == [e.to_dict() for e in full.events] and timeline == tl
