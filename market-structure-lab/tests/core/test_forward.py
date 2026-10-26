"""Chấm forward bản ghi dự báo (core/eval/forward.py, plan_mt5_live.md §5): tính tay + kiểm chéo với điểm thật trong lần chạy."""
from __future__ import annotations

import math
from dataclasses import replace
from datetime import timedelta

import pytest

from core.algorithms.ict_structure import IctStructureAlgorithm
from core.components.price_band import pinball
from core.eval import forward
from tests.helpers import cal_bars, make_bars, u

M15 = timedelta(minutes=15)


def _rec(t, close, atr, state, **tam):
    return {"t": t, "close": close, "atr": atr, "trang_thai": state, "tam": tam}


def _band(close, atr, qu80, qd80, qu50, qd50, b0):
    return {"lo80": close - qd80 * atr, "hi80": close + qu80 * atr, "lo50": close - qd50 * atr,
            "hi50": close + qu50 * atr, "qu80": qu80, "qd80": qd80, "b0": list(b0)}


def test_cham_tay_khoang_muc_pha_bien_con_giu():
    # close 100, ATR 1; 2 nến sau: high max 101.5, low min 99.5, close 101.2 / 100.4
    bars = make_bars([(100, 100.2, 99.8, 100), (100, 101.5, 99.9, 101.2), (101.2, 101.3, 99.5, 100.4)], "M15")
    band = _band(100, 1.0, 2.0, 1.0, 1.0, 0.4, (1.0, 2.0))
    r0 = {"h": 2, "khoang": band,
          "muc": [{"loai": "vung_tren", "phia": "up", "gia": 101.4, "p": 0.6, "p0": 0.5},
                  {"loai": "vung_duoi", "phia": "down", "gia": 99.0, "p": 0.3, "p0": 0.2}],
          "pha_bien": {"lo": 99.6, "hi": 101.0, "p": 0.7, "p0": 0.4},
          "con_giu": {"p": 0.8, "p0": 0.6}}
    recs = {0: _rec(0, 100, 1.0, "range", **{"30m": r0}), 1: _rec(1, 101.2, 1.0, "range"),
            2: _rec(2, 100.4, 1.0, "range")}
    s = forward.score(bars, recs, 0.9, M15)["30m"]
    # khoảng 80% [99, 102] chứa [99.5, 101.5]; 50% [99.6, 101] thì không
    assert (s["n"], s["phu_80"], s["phu_50"], s["rong_80_atr"]) == (1, 1.0, 0.0, 3.0)
    loss = pinball(0.9, 1.5, 2.0) + pinball(0.9, 0.5, 1.0)
    loss0 = pinball(0.9, 1.5, 1.0) + pinball(0.9, 0.5, 2.0)
    assert s["skill_so_voi_b0"] == pytest.approx(1 - loss / loss0)
    # vùng trên 101.4 bị chạm (high 101.5), vùng dưới 99.0 không (low 99.5)
    assert s["cham"]["vung_tren"] == {"n": 1, "brier": pytest.approx(0.16), "brier_b0": pytest.approx(0.25),
                                      "ty_le_cham": 1.0}
    assert s["cham"]["vung_duoi"]["brier"] == pytest.approx(0.09)
    assert s["cham_tong"] == {"n": 2, "brier": pytest.approx((0.16 + 0.09) / 2), "brier_b0": pytest.approx((0.25 + 0.04) / 2)}
    # close 101.2 > biên trên 101.0 → phá; trạng thái range giữ suốt cửa sổ → còn giữ
    assert s["pha_bien"] == {"n": 1, "ty_le": 1.0, "brier": pytest.approx(0.09), "brier_b0": pytest.approx(0.36)}
    assert s["con_giu"] == {"n": 1, "ty_le": 1.0, "brier": pytest.approx(0.04), "brier_b0": pytest.approx(0.16)}
    assert (s["cho_ket_cuc"], s["bo_qua_khoang_trong"]) == (0, 0)


def test_con_giu_doi_trang_thai_chua_du_nen_cho_ket_cuc_va_chi_cham_ban_ghi_chon():
    bars = make_bars([(100, 100.2, 99.8, 100)] * 5, "M15")
    g = {"h": 1, "con_giu": {"p": 0.5, "p0": 0.5}}
    recs = {0: _rec(0, 100, 1, "trend_len", x=g), 1: _rec(1, 100, 1, "nhieu", x=g), 2: _rec(2, 100, 1, "nhieu", x=g),
            3: _rec(3, 100, 1, None), 4: _rec(4, 100, 1, "nhieu", x=g)}
    s = forward.score(bars, recs, 0.9, M15)["x"]
    # t=0: đổi sang nhiễu → không giữ; t=1: giữ; t=2: nến sau «chưa đủ nến» → không chấm; t=4: chưa có nến sau
    assert (s["con_giu"]["n"], s["con_giu"]["ty_le"], s["cho_ket_cuc"]) == (2, 0.5, 1)
    assert s["n"] == 0                                  # không có khoảng
    only = forward.score(bars, recs, 0.9, M15, only=[0])["x"]
    assert (only["con_giu"]["n"], only["con_giu"]["ty_le"], only["cho_ket_cuc"]) == (1, 0.0, 0)


def test_cua_so_vat_khoang_trong_dai_khong_cham_nhung_dung_buoc_khung_lon_thi_cham():
    rows = [(100, 100.2, 99.8, 100)] * 3
    bars = make_bars(rows, "M15")
    bars[2] = replace(bars[2], bar_time=bars[2].bar_time + timedelta(hours=4),
                      close_time=bars[2].close_time + timedelta(hours=4))     # nến 1 → 2 cách 4 giờ 15 phút
    g = {"h": 1, "con_giu": {"p": 0.5, "p0": 0.5}}
    recs = {t: _rec(t, 100, 1, "nhieu", x=g) for t in range(3)}
    s = forward.score(bars, recs, 0.9, M15)["x"]
    assert (s["con_giu"]["n"], s["bo_qua_khoang_trong"], s["cho_ket_cuc"]) == (1, 1, 1)
    h4 = make_bars(rows, "H4")                          # nến H4 cách 4 giờ = đúng bước, không phải khoảng trống
    assert forward.score(h4, recs, 0.9, timedelta(hours=4))["x"]["con_giu"]["n"] == 2


def test_kip_thoi_q80_va_ban_ghi_khi_tat_nhan_dien():
    t = u(2024, 1, 2, 10)
    assert forward.is_timely(t + M15, t, M15) and not forward.is_timely(t + M15 + timedelta(seconds=1), t, M15)
    assert forward.quantile_80({"nd_bat": True, "nd_muc_80": 0.905}) == 0.905
    with pytest.raises(ValueError):
        forward.quantile_80({"nd_bat": False, "nd_muc_80": 0.905})
    algo = IctStructureAlgorithm(timeframe="M15", nd_bat=False)
    algo.reset()
    algo.on_bar(make_bars([(100, 100.2, 99.8, 100)], "M15")[0])
    assert algo.forecast_record() is None


def _close(a, b):
    if a is None or b is None:
        return a is b
    return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)


def test_kiem_cheo_cham_forward_tu_ban_ghi_bang_diem_that_trong_lan_chay():
    """Bản ghi mọi nến + nến đã lưu → đúng điểm thật của lần chạy: bản ghi đủ thông tin, bộ chấm đúng định nghĩa."""
    _rows, bars = cal_bars(u(2024, 1, 2), u(2024, 3, 9), seed=7)
    algo = IctStructureAlgorithm(timeframe="M15", session_calendar="cme_globex_metals")
    algo.reset()
    recs = {}
    for b in bars:                                      # bản ghi lấy ngay sau nến t, như luồng live
        algo.on_bar(b)
        recs[b.index] = rec = algo.forecast_record()
        assert rec["t"] == b.index
    nd = algo.pending_state()["nhan_dien"]
    fw = forward.score(bars, recs, algo.run_stats([])["nhan_dien"]["muc_80"], M15)
    assert set(fw) == {"1h", "4h"}
    for k, s in fw.items():
        want = nd["diem_that"][k]
        for key in ("n", "phu_80", "phu_50", "rong_80_atr", "skill_so_voi_b0"):
            assert _close(s[key], want[key]), (k, key, s[key], want[key])
        assert set(s["cham"]) == set(want["cham"])
        for kind, row in s["cham"].items():
            for key in ("n", "brier", "brier_b0", "ty_le_cham"):
                assert _close(row[key], want["cham"][kind][key]), (k, kind, key)
        for key in ("n", "brier", "brier_b0"):
            assert _close(s["cham_tong"][key], want["cham_tong"][key]), (k, "cham_tong", key)
        for fam in ("con_giu", "pha_bien"):
            got, exp = s[fam], nd["thoi_gian"]["diem_that"][fam][k]
            for key in ("n", "ty_le", "brier", "brier_b0"):
                assert _close(got[key], exp[key]), (k, fam, key, got[key], exp[key])
        # dữ liệu đủ để mọi nhánh đều được chấm, kể cả cửa sổ vắt cuối tuần
        assert s["n"] > 500 and s["pha_bien"]["n"] > 50 and s["con_giu"]["n"] > 500 and s["bo_qua_khoang_trong"] > 0
