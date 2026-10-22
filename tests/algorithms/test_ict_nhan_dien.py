"""ict_structure 0.6.0 — lớp nhận diện: khoảng giá, xác suất chạm, trạng thái (thuat_toan_nhan_dien.md).

Thành phần thử trên nến dựng tay (số tính tay ở chú thích); thuật toán thử nhân quả, tắt ``nd_bat`` = 0.5.0, khung H4.
"""
from __future__ import annotations

import math
import random
from datetime import timedelta

import pytest

from core.algorithms.ict_structure import IctStructureAlgorithm
from core.algorithms.ict_structure import nhan_dien as nd
from core.components.market_state import MarketState
from core.components.market_state_v2 import NO_STRUCTURE, MarketStateV2, Structure
from core.components.price_band import PriceBand
from core.components.rolling_stats import quantile
from core.components.state_clock import StateClock
from core.data.htf_stream import NY_TZ
from core.engine import run_algorithm
from core.types import StructureType
from tests.algorithms.test_ict_structure_g2 import M15, T0, _ohlc, _p, _random_bars
from tests.helpers import make_bars

STATE = set(StructureType.STATE_TYPES)

# ------------------------------------------------------------------ [N] khoảng giá + xác suất chạm

#        o      h      l     c        giờ NY: #0–#3 = 09:xx, #4… = 10:xx
ROWS = [(10.0, 10.0, 10.0, 10.0), (10.0, 11.0, 9.5, 10.5), (10.5, 12.0, 10.0, 11.0), (11.0, 11.5, 10.8, 11.2),
        (11.2, 11.4, 9.0, 9.5), (9.5, 10.0, 9.2, 9.8), (9.8, 10.5, 9.5, 10.0), (10.0, 10.2, 9.7, 10.1)]


def _long_gaps(bars):
    """Cờ khoảng trống dài (> 3 giờ) trước mỗi nến — như thuật toán truyền vào."""
    return [i > 0 and bars[i].bar_time - bars[i - 1].bar_time > timedelta(hours=3) for i in range(len(bars))]


def _band(rows=ROWS, times=None, levels=None, edges=None):
    pb = PriceBand({"h2": 2}, q80=0.905, q50=0.745, max_samples=100, min_samples=1)
    bars = _ohlc(rows, times)
    out = [pb.step(b, 1.0, b.bar_time.astimezone(NY_TZ).hour, g, (levels or {}).get(b.index, []), (edges or {}).get(b.index))
           for b, g in zip(bars, _long_gaps(bars))]
    return pb, out


def test_phan_vi_noi_suy():
    assert quantile([1.0, 2.0, 3.0, 4.0], 0.5) == pytest.approx(2.5)
    assert quantile([1.0, 2.0, 3.0, 4.0], 0.905) == pytest.approx(3.715)      # vị trí 3·0,905 = 2,715
    assert quantile([7.0], 0.9) == 7.0
    assert quantile([0.0, 1.0, 2.0, 3.0, 10.0], 0.5, 2) == 3.0                # chỉ đuôi [2, 3, 10]


def test_mau_bien_chi_dung_nen_da_hoan_tat_va_du_bao_tinh_tay():
    pb, out = _band(levels={5: [("vung_tren", "up", 11.0)]})
    # mẫu s = t − 2: u = max high (s, t] − C_s, d = C_s − min low (s, t] (ATR = 1)
    #   s=0: u 12 − 10 = 2,  d 10 − 9,5 = 0,5 · s=1: 1,5, 0,5 · s=2: 0,5, 2 · s=3: 0,2, 2,2 · s=4: 1,0, 0,3 · s=5: 0,7, 0,3
    assert pb._pooled["h2"].u.xs == pytest.approx(sorted([2.0, 1.5, 0.5, 0.2, 1.0, 0.7]))
    assert out[4]["h2"] is None                                  # #4: mới 3 mẫu < 4 × min_samples → khởi động
    f = out[5]["h2"]                                             # #5 (10:xx, giờ chưa có mẫu) → mẫu chung s = 0..3
    assert f["nguon"] == "chung" and f["n_mau"] == 4 and f["b0"] == (f["qu80"], f["qd80"])
    assert f["qu80"] == pytest.approx(1.5 + 0.715 * 0.5) and f["qd80"] == pytest.approx(2.0 + 0.715 * 0.2)
    assert (f["lo80"], f["hi80"]) == pytest.approx((9.8 - f["qd80"], 9.8 + f["qu80"]))
    assert f["muc"][0]["p"] == pytest.approx(0.5)                # khoảng cách 1,2 ATR: u ≥ 1,2 ở 2/4 mẫu
    # chấm ở #7: đường giá (5, 7] = high 10,5, low 9,5 nằm trong cả khoảng 80% và 50%; mức 11,0 không bị chạm
    sc = pb.scores()["h2"]
    assert sc["n"] == 1 and sc["phu_80"] == 1.0 and sc["phu_50"] == 1.0
    assert sc["cham"]["vung_tren"]["n"] == 1 and sc["cham"]["vung_tren"]["brier"] == pytest.approx(0.25)


def test_mau_vat_qua_khoang_trong_bi_bo():
    times = [T0 + i * M15 + (timedelta(hours=4) if i >= 4 else timedelta()) for i in range(len(ROWS))]
    pb, _ = _band(times=times)
    # khoảng trống trước #4 → bỏ s = 2 (cửa sổ #3–#4) và s = 3 (#4–#5); còn s = 0, 1, 4, 5
    assert pb._pooled["h2"].u.xs == pytest.approx(sorted([2.0, 1.5, 1.0, 0.7]))


def test_pha_bien_range_tu_mau_close_tinh_tay():
    pb, out = _band(edges={5: (9.0, 10.5)})
    # mẫu close s = t − 2 (ATR 1): s0 (uc 1,0; dc −0,5) · s1 (0,7; −0,5) · s2 (0,2; 1,5) · s3 (−1,4; 1,7)
    # ở #5 (close 9,8): phá khi uc > 10,5 − 9,8 = 0,7 hoặc dc > 9,8 − 9,0 = 0,8 → s0, s2, s3 = 3/4 (mẫu chung → p = B0)
    f = out[5]["h2"]["pha_bien"]
    assert f["p"] == pytest.approx(0.75) and f["p0"] == pytest.approx(0.75) and out[4]["h2"] is None
    # chấm ở #7: close (5, 7] = 10,0 / 10,1 nằm trong [9,0; 10,5] → không phá, Brier = 0,75²
    sc = pb.break_brief()["h2"]
    assert (sc["n"], sc["ty_le"]) == (1, 0.0) and sc["brier"] == pytest.approx(0.5625)


def test_con_giu_va_thoi_gian_con_lai_tinh_tay():
    ck = StateClock({"h2": 2}, min_episodes=1)
    fc = [ck.step(t, s, False) for t, s in enumerate("AABBBAAAAB")]
    # chưa có đoạn nào / cả mẫu riêng lẫn mẫu chung không có đoạn dài ≥ tuổi (mẫu số #(L ≥ a) = 0)
    assert fc[0] is None and fc[4] is None and fc[8] is None
    # #2: B mới (tuổi 1), chưa có đoạn B → mẫu chung = [A dài 2]: còn giữ 2 nến nữa = #(L ≥ 3)/#(L ≥ 1) = 0
    assert fc[2]["nguon"] == "chung" and fc[2]["giu"]["h2"] == 0.0 and fc[2]["con_lai_nen"] == 1.0
    # #6: A tuổi 2, đoạn A = [2] → còn giữ 0, thời gian còn lại = trung vị(2 − 2) = 0
    assert fc[6]["nguon"] == "trang_thai" and fc[6]["tuoi_nen"] == 2 and fc[6]["giu"]["h2"] == 0.0 and fc[6]["con_lai_nen"] == 0.0
    # #7: A tuổi 3, đoạn A = [2] không có L ≥ 3 → mẫu chung [2, 3] (mẫu số 1): còn giữ #(L ≥ 5)/1 = 0
    assert fc[7]["nguon"] == "chung" and fc[7]["n_doan_con"] == 1 and fc[7]["giu"]["h2"] == 0.0
    assert fc[9]["nguon"] == "trang_thai" and fc[9]["giu"]["h2"] == 1.0 and fc[9]["con_lai_nen"] == 2.0    # B = [3]
    # chấm (#2→#4 giữ, #3→#5 đổi, #5→#7 giữ, #6→#8 giữ, #7→#9 đổi): p = 0 cả năm → Brier 3/5.
    # B0 = Σ max(L − 2, 0) / Σ L: mẫu [2] → 0 (bốn lần đầu); mẫu chung [2, 3] → 1/5 (#7) → Brier (1 + 0 + 1 + 1 + 0,04)/5
    sc = ck.brief()["h2"]
    assert (sc["n"], sc["ty_le"]) == (5, 0.6) and sc["brier"] == pytest.approx(0.6) and sc["brier_b0"] == pytest.approx(0.608)
    assert ck.step(10, None, True) is None and ck._len["A"].xs == [2, 4]   # đoạn B cắt vì khoảng trống: không vào mẫu
    # rơi về «chưa đủ nến» (không khoảng trống) cũng là lần cắt: dự báo vắt qua không được chấm
    ck = StateClock({"h2": 2}, min_episodes=1)
    for t, s in enumerate(["A", "A", "B", "B", None, "B", "B"]):
        ck.step(t, s, False)
    assert ck.brief()["h2"]["n"] == 0 and ck._len["B"].xs == []


def test_kiem_tham_so_khoang():
    with pytest.raises(ValueError, match="khoảng 50%"):
        PriceBand({"h": 4}, q80=0.7, q50=0.8)
    assert PriceBand({"1h": 4, "x": 0}).horizons == {"1h": 4}   # tầm < 1 nến bị bỏ


# ------------------------------------------------------------------ [N] trạng thái


def _zigzag(points, step=4):
    """Nến từ chuỗi điểm close nối thẳng (``step`` nến mỗi đoạn); high/low = thân ± 0,05."""
    closes = [points[0]]
    for a, b in zip(points, points[1:]):
        closes += [a + (b - a) * k / step for k in range(1, step + 1)]
    rows, prev = [], closes[0]
    for c in closes:
        rows.append((prev, max(prev, c) + 0.05, min(prev, c) - 0.05, c))
        prev = c
    return _ohlc(rows)


def _run_state(bars, atr=1.0, hold=2):
    ms = MarketState(900, er_threshold=0.3, hold=hold)
    changes = [(b.index, ms.on_bar(b, atr, False)) for b in bars]
    return ms, [(i, ch) for i, ch in changes if ch is not None]


def test_range_moi_bien_cham_hai_lan():
    ms, ch = _run_state(_zigzag([100.0, 102.0] * 10))            # dao động 100 ↔ 102, chu kỳ 8 nến
    assert ms.state == "range" and len(ch) == 1
    i, (name, first, info) = ch[0]
    assert name == "range" and first.index == i - 1               # giữ 2 nến mới đổi; nến sự kiện = nến đầu
    assert info["nen_dau_cua_so"] == i - info["cua_so_nen"] + 1   # cửa sổ kết thúc ở nến xác nhận
    assert info["bien_tren"] == pytest.approx(102.05) and info["bien_duoi"] == pytest.approx(99.95)
    assert info["rong_atr"] == pytest.approx(2.1) and info["er"] < 0.3
    assert len(info["cham_tren"]) >= 2 and all(b - a >= 6 for a, b in zip(info["cham_tren"], info["cham_tren"][1:]))


def test_dang_cho_roi_range_bien_theo_nen_t():
    bars = _zigzag([100.0, 102.0] * 10)
    ms, _ = _run_state(bars[:50])
    assert ms.state == "range"
    up = _ohlc([(0, 0, 0, 0)] * 50 + [(101.0, 104.0, 100.9, 103.9)])[50]   # nến phá lên: ứng viên khác, chưa đủ 2 nến
    assert ms.on_bar(up, 1.0, False) is None and ms.state == "range" and ms.pending_candidate() is not None
    assert ms.info["bien_tren"] == 104.0                                     # biên trên = biên của nến t, không cũ


def test_trend_va_nhieu():
    ms, _ = _run_state(_zigzag([100.0, 120.0], step=40))         # đi thẳng lên: ER = 1
    assert ms.state == "trend_len" and ms.info["er"] == pytest.approx(1.0)
    ms, _ = _run_state(_zigzag([100.0, 110.0] * 10))             # đi ngang nhưng rộng 10 ATR > 5 → không range
    assert ms.state == "nhieu"


def test_nen_dinh_thap_dan_day_cao_dan():
    pts = []
    for k in range(8):
        pts += [95.0 + 0.7 * k, 105.0 - 0.7 * k]
    ms, _ = _run_state(_zigzag(pts))
    assert ms.state == "nen"
    assert ms.info["dinh"][0] > ms.info["dinh"][1] > ms.info["dinh"][2] and ms.info["ty_le_rong"] <= 0.5


def test_khoang_trong_dat_lai_va_chua_du_nen():
    bars = _zigzag([100.0, 102.0] * 10)
    ms, _ = _run_state(bars[:50])
    assert ms.state == "range"
    assert ms.on_bar(bars[50], 1.0, True) is None and ms.state is None   # sau khoảng trống dài: chưa đủ nến
    assert MarketState(900).on_bar(bars[0], None, False) is None


# ------------------------------------------------------------------ [N] trạng thái v2 (0.9.0, plan_nhan_dien_v2.md §3)


def _v2_rows_trend():
    """40 nến dao động nhẹ quanh 100, rồi 40 nến tăng 0,6 / nến (cứ 5 nến hồi 0,3)."""
    rows, p = [], 100.0
    for i in range(40):
        c = 100 + 0.4 * math.sin(i)
        rows.append((p, max(p, c) + 0.2, min(p, c) - 0.2, c))
        p = c
    for i in range(41):
        c = p + (0.6 if i % 5 else -0.3) if i < 40 else p - 0.3
        rows.append((p, max(p, c) + 0.2, min(p, c) - (0.2 if i < 40 else 0.5), c))
        p = c
    return rows


def test_v2_trend_vao_theo_cau_truc_va_luc_thoat_ngay_khi_choch():
    ms, bars, seen = MarketStateV2(900), _ohlc(_v2_rows_trend()), []
    for b in bars:
        structure = Structure(0 if b.index < 40 else 1, b.index == 80, None)        # HH-HL từ #40; #80: phá mức bảo vệ
        ch = ms.on_bar(b, 1.0, False, structure)
        if ch:
            seen.append((b.index, ch[0], ch[1].index, ch[2].get("ly_do"), ch[2].get("thoat"), ch[2].get("doi_ngay")))
        if b.index == 79:
            trend_line_79 = ms.timeline_extra()["nd_duong"]
    # khởi động 32 nến; trend vào khi cấu trúc + lực (giữ 2 nến: nến đầu #43, xác nhận #44); CHoCH → đổi ngay ở #80
    assert seen[0][1] == "nhieu"
    assert seen[1] == (44, "trend_len", 43, "cau_truc_va_luc", None, None)
    # «đường trend» (0.9.1) sau #79 khi đang trend lên = đáy thấp nhất 16 nến tới #79 (kênh thoát của nến #80)
    assert trend_line_79 == pytest.approx(min(b.low for b in bars[64:80]))
    assert seen[2][0] == 80 and seen[2][2] == 80 and seen[2][4:] == ("choch", True) and seen[2][1] != "trend_len"


def test_v2_khong_vao_lai_trend_khi_muc_bao_ve_van_bi_pha():
    """Mức bảo vệ bị phá giữ nguyên tới swing mới: luật vào dùng cùng định nghĩa «cấu trúc ngược chiều» với luật ra →
    không vào lại trend lên rồi ra ngay (nhấp nháy) dù giá còn tăng và ER cao."""
    rows = _v2_rows_trend()
    p = rows[-1][3]
    for _ in range(40):
        rows.append((p, p + 0.8, p - 0.2, p + 0.6))
        p += 0.6
    ms, seen = MarketStateV2(900), []
    for b in _ohlc(rows):
        ch = ms.on_bar(b, 1.0, False, Structure(0 if b.index < 40 else 1, b.index >= 80, None))
        if ch:
            seen.append((b.index, ch[0]))
    assert (44, "trend_len") in seen and [x for x in seen if x[0] >= 80][0] == (80, "nhieu")
    assert all(name != "trend_len" for i, name in seen if i > 80)


def _v2_rows_range():
    rows, p = [], 101.0
    for i in range(60):                                                       # 100 ↔ 102, chu kỳ 8 nến
        c = 101 + math.sin(i * math.pi / 4)
        rows.append((p, max(p, c) + 0.15, min(p, c) - 0.15, c))
        p = c
    for c in (102.3, 102.6, 102.9):                                           # 102,3 chưa quá biên + 0,25
        rows.append((p, c + 0.1, p - 0.1, c))
        p = c
    return rows


def test_v2_range_giu_toi_khi_hai_close_pha_bien():
    ms, log = MarketStateV2(900), []
    for b in _ohlc(_v2_rows_range()):
        ch = ms.on_bar(b, 1.0, False, Structure(0, False, None))
        if ch:
            log.append((b.index, ch[0], ch[1].index, ch[2].get("thoat"), ch[2].get("bien_tren"), ch[2].get("bien_duoi")))
        if b.index == 60:
            assert ms.state == "range"                                        # 1 close ngoài chưa đủ
            line_60 = ms.timeline_extra()["nd_duong"]
    # «đường trend» (0.9.1) khi range = giữa hộp ghi lúc vào range (hộp cố định tới khi phá)
    assert line_60 == pytest.approx((log[0][4] + log[0][5]) / 2)
    # hộp Donchian 6 giờ (24 nến), mỗi biên được thăm ≥ 2 lần → range từ #32; biên trên = max high = 102,15
    assert log[0][:3] == (33, "range", 32) and log[0][4] == pytest.approx(102.15)
    # close #61 = 102,6, #62 = 102,9 > 102,15 + 0,25·ATR → phá biên lên, đổi ngay ở #62
    assert log[1][0] == 62 and log[1][2] == 62 and log[1][3] == "pha_bien_len"


def test_v2_co_nen_khi_bien_dong_co_lai_va_reset_sau_khoang_trong():
    rows, p = [], 100.0
    for i in range(120):
        amp = 2.0 if i < 80 else 2.0 * 0.9 ** (i - 80)
        c = 100 + amp * math.sin(i * math.pi / 3)
        rows.append((p, max(p, c) + 0.05, min(p, c) - 0.05, c))
        p = c
    ms, flags = MarketStateV2(900), []
    for b in _ohlc(rows):
        ms.on_bar(b, 1.0, False, NO_STRUCTURE)
        flags.append(ms.squeeze)
    assert not any(flags[:80]) and flags[-1]                                   # BB co vào trong KC, độ rộng thấp nhất
    assert ms.on_bar(_ohlc(rows)[0], 1.0, True, NO_STRUCTURE) is None and ms.state is None   # khoảng trống: chưa đủ nến


def test_kiem_tham_so_trang_thai_v2():
    with pytest.raises(ValueError, match="nd_er_ra"):
        MarketStateV2(900, er_strong=0.3, er_in=0.1, er_out=0.2)


def test_kiem_tham_so_trang_thai():
    with pytest.raises(ValueError, match="ngưỡng ER"):
        MarketState(900, er_threshold=1.5)


# ------------------------------------------------------------------ thuật toán (ict_structure 0.6.0)


def test_pdh_pdl_vao_xac_suat_cham_khi_con_nguyen_va_dung_phia():
    """0.8.0: PDH / PDL vào danh sách mức chỉ khi biết còn nguyên (``*_taken`` = False; None = không theo dõi → bỏ) và ở
    đúng phía close."""
    layer = nd.NdLayer(IctStructureAlgorithm.validate_params(_p()), {"h2": 2}, 900)
    seen = []
    layer.band.step = lambda bar, atr, hour, gap, levels, edges: seen.append(list(levels)) or {}
    bar = _ohlc(ROWS)[3]                                                      # close 11,2
    per = {"pdh": 11.5, "pdh_taken": False, "pdl": 9.0, "pdl_taken": False}
    for p in (per, dict(per, pdl_taken=True), dict(per, pdh=11.0), dict(per, pdh_taken=None), None):
        layer.step(bar, 1.0, None, {"high": None, "low": None}, p, nd.Structure(None, False, None))
    both = [("pdh", "up", 11.5), ("pdl", "down", 9.0)]
    assert seen == [both, both[:1], both[1:], both[1:], []]   # đã lấy / dưới close / không theo dõi → bỏ; không khung lớn


def test_tat_nd_bat_giong_ban_khong_co_lop_nhan_dien():
    bars = _random_bars(5, 1200)
    on = run_algorithm(bars, IctStructureAlgorithm(**_p()))
    a = IctStructureAlgorithm(**_p(nd_bat=False))
    off = run_algorithm(bars, a)
    assert not any(e.structure_type in STATE for e in off.events)
    assert [e.to_dict() for e in off.events] == [e.to_dict() for e in on.events if e.structure_type not in STATE]
    assert all(not any(k.startswith("nd_") for k in p) for p in off.timeline)
    assert [{k: v for k, v in p.items() if not k.startswith("nd_")} for p in on.timeline] == off.timeline
    assert "nhan_dien" not in a.pending_state()
    assert "nhan_dien" not in IctStructureAlgorithm.manifest_info(IctStructureAlgorithm.validate_params(_p(nd_bat=False)))
    assert "nhan_dien" in IctStructureAlgorithm.manifest_info(IctStructureAlgorithm.validate_params(_p()))


def test_nhan_dien_tren_du_lieu_ngau_nhien_va_nhan_qua_prefix():
    bars = _random_bars(7, 1500)
    algo = IctStructureAlgorithm(**_p())
    full = run_algorithm(bars, algo)
    st = [e for e in full.events if e.structure_type in STATE]
    assert {e.structure_type for e in st} >= {"STATE_TREND_UP", "STATE_TREND_DOWN", "STATE_CHOP", "STATE_RANGE"}
    for e in st:              # v2: giữ 2 nến (nến sự kiện = nến đầu), trừ thoát do sự kiện đã xác nhận (doi_ngay)
        now = e.details.get("doi_ngay", False)
        assert e.confirmed_bar_index - e.event_bar_index == (0 if now else 1) and e.details["nen_dau"] == e.event_bar_index
    assert {e.reason_code for e in st} <= {"STATE_TREND_STRUCTURE", "STATE_RANGE_BOX", "STATE_CHOP_NO_BOX"}
    assert all(p["nd_trang_thai"] != "nen" and p["nd_nen"] in (True, False, None) for p in full.timeline)
    seen = [p for p in full.timeline if p["nd_4h_lo80"] is not None]
    assert seen and all(p["nd_4h_lo80"] < p["nd_4h_lo50"] < p["nd_4h_hi50"] < p["nd_4h_hi80"] for p in seen)
    stats = algo.run_stats(full.events)["nhan_dien"]
    sc = stats["khoang_va_cham"]["4h"]
    assert sc["n"] > 0 and 0.0 <= sc["phu_80"] <= 1.0 and sc["phu_50"] <= sc["phu_80"]
    for kind in ("vung_tren", "pdh", "pdl"):                  # 0.8.0: PDH / PDL chấm như mọi loại mức, kèm thật / kỳ vọng
        r = sc["cham"][kind]
        assert r["n"] > 0 and 0.0 <= r["ty_le_cham"] <= 1.0 and 0.0 <= r["p_tb"] <= 1.0 and r["hieu_chuan"]
    giu, pha = stats["thoi_gian"]["con_giu"]["4h"], stats["thoi_gian"]["pha_bien"]["4h"]
    assert giu["n"] > 0 and 0.0 <= giu["ty_le"] <= 1.0 and giu["brier"] is not None and pha["n"] > 0
    tg = algo.pending_state()["nhan_dien"]["thoi_gian"]
    assert set(tg) == {"con_giu", "pha_bien", "diem_that"} and tg["diem_that"]["con_giu"] == stats["thoi_gian"]["con_giu"]
    assert any(p["nd_giu_4h"] is not None and p["nd_con_lai"] is not None for p in full.timeline)
    # phá biên chỉ khi đang range, đã có khoảng, close còn trong hộp (v2: hộp cố định, close ra ngoài → không dự báo)
    assert all(p["nd_pha_4h"] is None or (p["nd_trang_thai"] == "range" and p["nd_4h_lo80"] is not None) for p in full.timeline)
    assert any(p["nd_pha_4h"] is not None for p in full.timeline)
    full_ev = [e.to_dict() for e in full.events]
    for cut in (300, 900):
        part = run_algorithm(bars, IctStructureAlgorithm(**_p()), upto_index=cut)
        assert [e.to_dict() for e in part.events] == [e for e in full_ev if e["confirmed_bar_index"] <= cut]
        assert part.timeline == full.timeline[: cut + 1]


def test_khung_h4_co_trang_thai_va_tam_4h():
    """Khung H4: nến cách nhau 4 giờ không phải khoảng trống dài (lớp nhận diện vẫn chạy); chỉ còn tầm 4h (1 nến)."""
    rnd, rows, c = random.Random(4), [], 100.0
    for _ in range(600):
        o, c = c, c + rnd.gauss(0, 1.0)
        rows.append((o, max(o, c) + abs(rnd.gauss(0, 0.4)), min(o, c) - abs(rnd.gauss(0, 0.4)), c))
    algo = IctStructureAlgorithm(timeframe="H4", session_calendar="none")
    res = run_algorithm(make_bars(rows, "H4"), algo)
    assert algo.nd_horizons == {"4h": 1}
    # v2: 8 giờ / 6 giờ kẹp ≥ 5 nến; thoát trend 4 giờ = 1 nến kẹp ≥ 2
    assert algo._nd.state.windows() == {"trend": 5, "hop": 5, "nen": 20, "thoat_trend": 2}
    assert any(e.structure_type in STATE for e in res.events)
    assert sum(p["nd_trang_thai"] is not None for p in res.timeline) > 400
    assert any(p["nd_4h_lo80"] is not None for p in res.timeline) and all(p["nd_1h_lo80"] is None for p in res.timeline)
    assert any(p["nd_giu_4h"] is not None for p in res.timeline) and all(p["nd_giu_1h"] is None for p in res.timeline)


def test_kiem_tham_so_thuat_toan():
    assert IctStructureAlgorithm(**_p()).nd_horizons == {"1h": 4, "4h": 16}
    with pytest.raises(ValueError, match="khoảng 50%"):
        IctStructureAlgorithm.validate_params({"nd_muc_50": 0.9, "nd_muc_80": 0.8})
    with pytest.raises(ValueError, match="mẫu tối thiểu"):
        IctStructureAlgorithm.validate_params({"nd_mau_toi_thieu": 700, "nd_mau_toi_da": 600})
