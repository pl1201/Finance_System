"""ict_structure 0.6.0 — lớp nhận diện: khoảng giá, xác suất chạm, trạng thái (thuat_toan_nhan_dien.md).

Thành phần thử trên nến dựng tay (số tính tay ở chú thích); thuật toán thử nhân quả, tắt ``nd_bat`` = 0.5.0, khung H4.
"""
from __future__ import annotations

import random
from datetime import timedelta

import pytest

from core.algorithms.ict_structure import IctStructureAlgorithm
from core.components.market_state import MarketState
from core.components.price_band import PriceBand, quantile
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


def _band(rows=ROWS, times=None, levels=None):
    pb = PriceBand({"h2": 2}, q80=0.905, q50=0.745, max_samples=100, min_samples=1)
    bars = _ohlc(rows, times)
    out = [pb.step(b, 1.0, b.bar_time.astimezone(NY_TZ).hour, g, (levels or {}).get(b.index, []))
           for b, g in zip(bars, _long_gaps(bars))]
    return pb, out


def test_phan_vi_noi_suy():
    assert quantile([1.0, 2.0, 3.0, 4.0], 0.5) == pytest.approx(2.5)
    assert quantile([1.0, 2.0, 3.0, 4.0], 0.905) == pytest.approx(3.715)      # vị trí 3·0,905 = 2,715
    assert quantile([7.0], 0.9) == 7.0


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


def test_kiem_tham_so_trang_thai():
    with pytest.raises(ValueError, match="ngưỡng ER"):
        MarketState(900, er_threshold=1.5)


# ------------------------------------------------------------------ thuật toán (ict_structure 0.6.0)


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
    assert {e.structure_type for e in st} >= {"STATE_TREND_UP", "STATE_TREND_DOWN", "STATE_CHOP"}
    for e in st:                                                 # giữ 2 nến: nến sự kiện = nến đầu của trạng thái mới
        assert e.event_bar_index == e.confirmed_bar_index - 1 and e.details["nen_dau"] == e.event_bar_index
    seen = [p for p in full.timeline if p["nd_4h_lo80"] is not None]
    assert seen and all(p["nd_4h_lo80"] < p["nd_4h_lo50"] < p["nd_4h_hi50"] < p["nd_4h_hi80"] for p in seen)
    sc = algo.run_stats(full.events)["nhan_dien"]["khoang_va_cham"]["4h"]
    assert sc["n"] > 0 and 0.0 <= sc["phu_80"] <= 1.0 and sc["phu_50"] <= sc["phu_80"]
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
    assert algo._nd.state.range_w == (5,)                                   # 16 / 12 / 8 giờ kẹp ≥ 5 nến → một cửa sổ
    assert any(e.structure_type in STATE for e in res.events)
    assert sum(p["nd_trang_thai"] is not None for p in res.timeline) > 400
    assert any(p["nd_4h_lo80"] is not None for p in res.timeline) and all(p["nd_1h_lo80"] is None for p in res.timeline)


def test_kiem_tham_so_thuat_toan():
    assert IctStructureAlgorithm(**_p()).nd_horizons == {"1h": 4, "4h": 16}
    with pytest.raises(ValueError, match="khoảng 50%"):
        IctStructureAlgorithm.validate_params({"nd_muc_50": 0.9, "nd_muc_80": 0.8})
    with pytest.raises(ValueError, match="mẫu tối thiểu"):
        IctStructureAlgorithm.validate_params({"nd_mau_toi_thieu": 700, "nd_mau_toi_da": 600})
