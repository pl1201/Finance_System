"""Nguyên mẫu: các cách kết hợp indicator + ICT nếu đưa lên chart — CHỈ ĐỌC database, KHÔNG phải plugin của lab.

Dựng bốn trang HTML dùng đúng thư viện chart của lab (``frontend/vendor`` Lightweight Charts 4.2.3 + primitive
``frontend/js/chart/primitives.js``), dữ liệu thật đoạn phát triển, sự kiện ``ict_structure`` thật, tín hiệu K01–K16 đúng
như ``research/ict_indicator_survey.py``, rồi chụp ảnh bằng Chrome / Edge headless:

1. ``1_top_down.png``   top-down ICT + lọc indicator (K04, K05, K06) — XAUUSD
2. ``2_sweep_rsi.png``  sweep + RSI cực trị (K09) — EURUSD
3. ``3_vung_bias.png``  discount/premium theo bias ICT / EMA (K13, K14) — XAUUSD
4. ``4_nhan_dien.png``  bỏ phiếu (K16), mô hình học, dải giá 80%, xác suất chạm vùng — XAUUSD

Số «đúng hướng», độ phủ, AUC, độ phủ dải giá lấy từ ``docs/research/khao_sat/ict_indicator_dev.json`` (khảo sát
2018 – 08/2024) và in ngay trên chart — đúng AGENTS.md §4: hiện điểm thật, không gọi là tín hiệu giao dịch.

Ví dụ (PowerShell, từ thư mục market-structure-lab)::

    .\\.venv\\Scripts\\python.exe research\\chart_ket_hop.py

Trang HTML ở lại cạnh ảnh — mở bằng trình duyệt để cuộn / zoom.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import ict_indicator_survey as S  # noqa: E402

WIN = ("2024-08-19 12:00", "2024-08-22 00:00")      # UTC, đoạn phát triển; trang 4 dừng ở NOW
NOW = "2024-08-21 14:00"                              # nến «hiện tại» của trang 4 (UTC)
H_FUT = 16                                            # 4 giờ phía trước
UP, DOWN, MUTED = "#26a69a", "#ef5350", "#9aa7b4"
BAND_UP, BAND_DOWN, BAND_FLAT = "#1e6b63", "#8c3b39", "#3a4654"
CHROME = (r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def vn(x, d=1):
    return ("%.*f" % (d, x)).replace(".", ",")


def pct(x, d=1):
    return vn(100 * x, d) + "%"


# ---------------------------------------------------------------- dữ liệu một cửa sổ


class Win:
    def __init__(self, d, t0, t1):
        self.d = d
        t = d.t_open
        self.a = int(np.searchsorted(t.values, np.datetime64(pd.Timestamp(t0))))
        self.b = int(np.searchsorted(t.values, np.datetime64(pd.Timestamp(t1))))
        if t[self.b - 1] >= pd.Timestamp(S.TEST_START):
            raise SystemExit("Cửa sổ chạm đoạn kiểm tra.")
        self.idx = np.arange(self.a, self.b)
        self.times = (t.values[self.a:self.b].astype("datetime64[s]").astype("int64")).tolist()

    def l(self, i):
        return int(i - self.a)

    def candles(self, a=None, b=None):
        d = self.d
        a = self.a if a is None else a
        b = self.b if b is None else b
        return [{"time": int(d.t_open.values[i].astype("datetime64[s]").astype("int64")), "open": d.O[i],
                 "high": d.H[i], "low": d.L[i], "close": d.C[i]} for i in range(a, b)]

    def line(self, arr, k=4):
        out = []
        for t, v in zip(self.times, np.asarray(arr, float)[self.a:self.b]):
            out.append({"time": t, "value": round(float(v), k)} if np.isfinite(v) else {"time": t})
        return out

    def shade(self, s, alpha=0.11, top=None):
        """Dãy nến liên tiếp cùng dấu ≠ 0 → hộp nền cao hết pane (hoặc dải mỏng ở mép trên nếu top)."""
        s = np.nan_to_num(np.asarray(s, float)[self.a:self.b])
        out, i, n = [], 0, len(s)
        while i < n:
            if s[i] == 0:
                i += 1
                continue
            j = i
            while j + 1 < n and s[j + 1] == s[i]:
                j += 1
            out.append({"l1": i - 0.5, "l2": j + 0.5, "fill": UP if s[i] > 0 else DOWN, "alpha": alpha, "top": top})
            i = j + 1
        return out

    def band(self, s, up_txt, down_txt, flat_txt=None, colors=None):
        cu, cd, cf = colors or (BAND_UP, BAND_DOWN, BAND_FLAT)
        out = []
        for i, v in enumerate(np.asarray(s, float)[self.a:self.b]):
            if not np.isfinite(v):
                continue
            if v > 0:
                out.append({"l": i, "key": "u", "color": cu, "text": up_txt})
            elif v < 0:
                out.append({"l": i, "key": "d", "color": cd, "text": down_txt})
            elif flat_txt:
                out.append({"l": i, "key": "f", "color": cf, "text": flat_txt})
        return out

    def turn_markers(self, s, name, color_up=UP, color_down=DOWN, size=1.3):
        s = np.nan_to_num(np.asarray(s, float))
        out = []
        for i in range(self.a, self.b):
            if s[i] != 0 and s[i] != s[i - 1]:
                up = s[i] > 0
                out.append({"time": self.times[i - self.a], "position": "belowBar" if up else "aboveBar",
                            "color": color_up if up else color_down, "shape": "arrowUp" if up else "arrowDown",
                            "text": name + (" ↑" if up else " ↓"), "size": size})
        return out

    def ict_markers(self, kinds=("LIQ_SWEEP_BSL", "LIQ_SWEEP_SSL", "SHIFT_UP", "SHIFT_DOWN"), dim=False):
        out = []
        for s, t, _p in self.d.events:
            if not (self.a <= t < self.b) or s not in kinds:
                continue
            tm = self.times[t - self.a]
            if s == "LIQ_SWEEP_BSL":
                out.append({"time": tm, "position": "aboveBar", "color": "#78909c" if dim else "#f48fb1",
                            "shape": "circle", "text": "quét", "size": 0.6})
            elif s == "LIQ_SWEEP_SSL":
                out.append({"time": tm, "position": "belowBar", "color": "#78909c" if dim else "#80cbc4",
                            "shape": "circle", "text": "quét", "size": 0.6})
            elif s == "SHIFT_UP":
                out.append({"time": tm, "position": "belowBar", "color": "#00e676", "shape": "arrowUp",
                            "text": "SHIFT", "size": 0.9})
            elif s == "SHIFT_DOWN":
                out.append({"time": tm, "position": "aboveBar", "color": "#ff1744", "shape": "arrowDown",
                            "text": "SHIFT", "size": 0.9})
        return out


def score(J, sym, k):
    A = J["ket_qua"][sym]["A"]
    r1, r4 = A["1h"]["tin_hieu"][k], A["4h"]["tin_hieu"][k]
    return r1, r4


def score_txt(J, sym, k):
    r1, r4 = score(J, sym, k)
    return "đúng hướng 1h <b>%s</b> · 4h <b>%s</b> · phủ %d%%" % (pct(r1["ba"]), pct(r4["ba"]), round(100 * r4["phu"]))


def touch_prob(d, i, level, side, h):
    """Tỷ lệ nến hợp lệ TRƯỚC 2024, cùng giờ NY và cùng tam phân vị ATR/giá, có biên ≥ khoảng cách tới mức."""
    if not np.isfinite(level):
        return None
    dist = ((level - d.C[i]) if side > 0 else (d.C[i] - level)) / d.atr[i]
    mfe = d.y[h]["mfe_up" if side > 0 else "mfe_dn"]
    bps = d.atr / d.C
    train = d.ok & np.isfinite(mfe) & (d.year < 2024)
    cut = np.quantile(bps[train], [1 / 3, 2 / 3])
    st = np.floor(d.hour_ny).astype(int) * 3 + np.digitize(np.nan_to_num(bps), cut)
    pool = mfe[train & (st == st[i])]
    return float(np.mean(pool >= dist)), float(dist)


# ---------------------------------------------------------------- bốn trang


def legend_ict():
    return [{"c": "#f48fb1", "t": "quét BSL"}, {"c": "#80cbc4", "t": "quét SSL"}, {"c": "#00e676", "t": "SHIFT tăng"},
            {"c": "#ff1744", "t": "SHIFT giảm"}, {"c": "#4c9aff", "t": "EMA50 M15"}, {"c": "#ba68c8", "t": "EMA200 M15"}]


def prec(w):
    return 5 if w.d.symbol == "EURUSD" else 2


def ema_lines(w):
    M = w.d.ind["M15"]
    k = prec(w) + 1
    return [{"color": "#4c9aff", "width": 1, "data": w.line(M["e50"], k)},
            {"color": "#ba68c8", "width": 1, "data": w.line(M["e200"], k)}]


def page1(J, dX):
    w = Win(dX, *WIN)
    d, sg, I, X = dX, dX.sig, dX.ict, dX.ind
    adx_ok = np.where(np.isfinite(X["H1"]["adx"]), (X["H1"]["adx"] >= 25).astype(float), np.nan)
    return {
        "file": "1_top_down", "title": "1 · Top-down ICT + lọc bằng indicator (K04, K05, K06)", "sym": "XAUUSD M15",
        "info": [
            "<b>Luật:</b> K04 bật khi thứ tự H4 = thứ tự H1 = order flow M15 (cùng chiều). K05 thêm điều kiện EMA50 > EMA200 "
            "trên H1 cùng chiều. K06 thêm ADX H1 ≥ 25.",
            "<b>Trên chart:</b> nền xanh / đỏ = K04 đang bật; vạch đậm ở mép trên = K05 (vạch 1) và K06 (vạch 2); mũi tên "
            "= lúc bật. Năm dải dưới đáy = từng thành phần, để thấy vì sao luật bật / tắt.",
            "<b>Điểm thật (2018 – 08/2024, XAUUSD):</b> K04 %s · K05 %s · K06 %s." % (
                score_txt(J, "XAUUSD", "K04"), score_txt(J, "XAUUSD", "K05"), score_txt(J, "XAUUSD", "K06")),
            "<b>EURUSD:</b> K04 %s. Hoà vốn sau phí cần ≈ 59%%." % score_txt(J, "EURUSD", "K04"),
        ],
        "prec": prec(w), "candles": w.candles(), "lines": ema_lines(w),
        "markers": w.ict_markers() + w.turn_markers(sg["K04"], "K04"),
        "boxes": w.shade(sg["K04"], 0.10) + w.shade(sg["K05"], 0.85, top=(0, 7)) + w.shade(sg["K06"], 0.85, top=(9, 16)),
        "bands": [
            {"caption": "ADX H1 ≥ 25", "bars": w.band(adx_ok, "ADX ≥ 25", "", "ADX < 25",
                                                      colors=("#5c6bc0", BAND_FLAT, BAND_FLAT))},
            {"caption": "EMA H1", "bars": w.band(sg["ema_h1"], "EMA H1 ↑", "EMA H1 ↓")},
            {"caption": "Order flow M15", "bars": w.band(I["of"], "OF ↑", "OF ↓", "OF chưa rõ")},
            {"caption": "ICT H1", "bars": w.band(I["h1"], "H1 ↑", "H1 ↓", "H1 —")},
            {"caption": "ICT H4", "bars": w.band(I["h4"], "H4 ↑", "H4 ↓", "H4 —")},
        ],
        "panes": [{"title": "ADX 14 · H1 (đường) và M15 (chấm) — ngưỡng 25", "height": 150, "range": [0, 60],
                   "series": [{"color": "#5c6bc0", "width": 2, "data": w.line(X["H1"]["adx"], 2)},
                              {"color": "#9aa7b4", "width": 1, "style": 1, "data": w.line(X["M15"]["adx"], 2)}],
                   "hlines": [{"value": 25, "color": "#ffb300"}]}],
        "legend": legend_ict() + [{"c": UP, "t": "K04 tăng (nền)", "box": True}, {"c": DOWN, "t": "K04 giảm (nền)", "box": True}],
    }


def page2(J, dE):
    w = Win(dE, *WIN)
    d, sg, X = dE, dE.sig, dE.ind
    r = X["M15"]["rsi"]
    rz = np.where(np.isfinite(r), np.where(r <= 35, 1.0, np.where(r >= 65, -1.0, 0.0)), np.nan)
    return {
        "file": "2_sweep_rsi", "title": "2 · Sweep + RSI cực trị (K09)", "sym": "EURUSD M15",
        "info": [
            "<b>Luật:</b> trong 4 giờ sau một sweep: quét SSL (bên bán) và RSI 14 ≤ 35 → hướng lên; quét BSL và RSI ≥ 65 "
            "→ hướng xuống. Sweep không kèm RSI cực trị thì bỏ (chấm xám).",
            "<b>Trên chart:</b> nền = K09 đang bật; mũi tên K09 = lúc bật; dải dưới = sweep gần nhất và vùng RSI.",
            "<b>Điểm thật EURUSD:</b> K09 %s — hơn sweep đơn (%s)." % (
                score_txt(J, "EURUSD", "K09"), score_txt(J, "EURUSD", "ict_sweep16")),
            "<b>XAUUSD:</b> K09 %s — không lặp lại. Hoà vốn sau phí cần ≈ 58,5%%." % score_txt(J, "XAUUSD", "K09"),
        ],
        "prec": prec(w), "candles": w.candles(), "lines": ema_lines(w),
        "markers": w.ict_markers(dim=True) + w.turn_markers(sg["K09"], "K09", "#80cbc4", "#f48fb1", 1.4),
        "boxes": w.shade(sg["K09"], 0.12),
        "bands": [
            {"caption": "RSI M15", "bars": w.band(rz, "RSI ≤ 35", "RSI ≥ 65", "RSI giữa")},
            {"caption": "Sweep 4h qua", "bars": w.band(sg["ict_sweep16"], "quét SSL", "quét BSL")},
        ],
        "panes": [{"title": "RSI 14 · M15 — ngưỡng 35 / 65", "height": 150, "range": [10, 90],
                   "series": [{"color": "#ba68c8", "width": 2, "data": w.line(r, 2)}],
                   "hlines": [{"value": 35, "color": "#80cbc4"}, {"value": 65, "color": "#f48fb1"},
                              {"value": 50, "color": "#3a4654"}]}],
        "legend": [{"c": "#78909c", "t": "sweep (chưa đủ điều kiện)"}, {"c": "#80cbc4", "t": "K09 ↑ (SSL + RSI ≤ 35)"},
                   {"c": "#f48fb1", "t": "K09 ↓ (BSL + RSI ≥ 65)"}, {"c": "#00e676", "t": "SHIFT"},
                   {"c": "#4c9aff", "t": "EMA50"}, {"c": "#ba68c8", "t": "EMA200"}],
    }


def page3(J, dX):
    w = Win(dX, *WIN)
    d, sg, I = dX, dX.sig, dX.ict
    segs = []
    for name, arr, col, style in (("đỉnh dealing range", I["dhi"], "#78909c", "solid"),
                                  ("cân bằng 50%", (I["dhi"] + I["dlo"]) / 2, "#b0bec5", "dashed"),
                                  ("đáy dealing range", I["dlo"], "#78909c", "solid")):
        v = arr[w.a:w.b]
        i = 0
        while i < len(v):
            if not np.isfinite(v[i]):
                i += 1
                continue
            j = i
            while j + 1 < len(v) and v[j + 1] == v[i]:
                j += 1
            segs.append({"l1": i - 0.5, "p1": float(v[i]), "l2": j + 0.5, "p2": float(v[i]), "color": col,
                         "width": 1, "style": style, "alpha": 0.8, "autoscale": False})
            i = j + 1
    return {
        "file": "3_vung_bias", "title": "3 · Discount / premium theo bias (K13 bias ICT, K14 bias EMA)", "sym": "XAUUSD M15",
        "info": [
            "<b>Luật:</b> bias khung lớn tăng (H1 = H4) và giá đang ở nửa dưới dealing range M15 (discount) → hướng lên; "
            "bias giảm và giá ở nửa trên (premium) → hướng xuống. K13 lấy bias từ thứ tự ICT, K14 từ EMA50/200.",
            "<b>Trên chart:</b> nền = K14 đang bật; vạch ở mép trên = K13; đường xám = đỉnh / đáy (liền) và mức 50% (đứt) "
            "của dealing range. Dải dưới đáy = ba thành phần.",
            "<b>Điểm thật XAUUSD:</b> K13 %s · K14 %s." % (score_txt(J, "XAUUSD", "K13"), score_txt(J, "XAUUSD", "K14")),
            "<b>EURUSD:</b> K13 %s · K14 %s. Hoà vốn sau phí cần ≈ 59%%." % (
                score_txt(J, "EURUSD", "K13"), score_txt(J, "EURUSD", "K14")),
        ],
        "prec": prec(w), "candles": w.candles(), "lines": ema_lines(w),
        "markers": w.ict_markers(),
        "boxes": w.shade(sg["K14"], 0.10) + w.shade(sg["K13"], 0.85, top=(0, 7)),
        "segments": segs,
        "bands": [
            {"caption": "Vùng M15", "bars": w.band(I["zone"], "discount", "premium", "cân bằng")},
            {"caption": "Bias EMA H1=H4", "bars": w.band(sg["K02"], "EMA ↑", "EMA ↓", "lệch")},
            {"caption": "Bias ICT H1=H4", "bars": w.band(sg["K01"], "ICT ↑", "ICT ↓", "lệch")},
        ],
        "panes": [{"title": "Vị trí giá trong dealing range M15 (0 = đáy, 1 = đỉnh; dưới 0,5 = discount)", "height": 150,
                   "range": [-0.1, 1.1], "prec": 1,
                   "series": [{"color": "#b0bec5", "width": 2, "data": w.line(I["range_pos"], 3)}],
                   "hlines": [{"value": 0.5, "color": "#ffb300"}]}],
        "legend": legend_ict() + [{"c": UP, "t": "K14 tăng (nền)", "box": True}, {"c": DOWN, "t": "K14 giảm (nền)", "box": True}],
    }


def page4(J, dX):
    w = Win(dX, WIN[0], NOW)
    d, sg, I, X = dX, dX.sig, dX.ict, dX.ind
    now = w.b - 1
    ex = J["ket_qua"]["XAUUSD"]["vi_du"]
    t_ex = pd.to_datetime(ex["gio_ny"]).tz_localize("America/New_York").tz_convert("UTC").tz_localize(None)
    pos = {int(t.value // 10**9): k for k, t in enumerate(t_ex)}

    def ex_line(key, mul=1.0):
        out = []
        for t in w.times:
            k = pos.get(t)
            v = ex[key][k] if k is not None else None
            out.append({"time": t, "value": round(v * mul, 3)} if v is not None else {"time": t})
        return out

    def ex_at(key, i):
        k = pos.get(int(d.t_open.values[i].astype("datetime64[s]").astype("int64")))
        return ex[key][k] if k is not None else None

    v = np.vstack([I["h1"], I["h4"], I["of"], I["dol"], sg["ema_h1"], sg["ema_h4"], sg["macd_m15"], sg["don_m15"]]).sum(0)
    vote = [{"time": t, "value": float(x), "color": (UP if x >= 6 else DOWN if x <= -6 else
                                                      "rgba(38,166,154,.45)" if x > 0 else "rgba(239,83,80,.45)")}
            if np.isfinite(x) else {"time": t} for t, x in zip(w.times, v[w.a:w.b])]
    # dải 80% cho 4 giờ tới: ở NOW (đậm) và các mốc trước đó mỗi 4 giờ (nhạt, để đối chiếu với giá thật)
    boxes = []
    for k in range(0, 9):
        i = now - k * H_FUT
        if i < w.a:
            break
        qu, qd = ex_at("q_len_4h_NEN", i), ex_at("q_xuong_4h_NEN", i)
        if qu is None or qd is None:
            continue
        top, bot = d.C[i] + qu * d.atr[i], d.C[i] - qd * d.atr[i]
        boxes.append({"l1": w.l(i) + 0.5, "l2": w.l(i) + H_FUT + 0.5, "p1": float(bot), "p2": float(top),
                      "fill": "#ffb300", "alpha": 0.16 if k == 0 else 0.07, "border": "#ffb300",
                      "borderStyle": "dashed"})
        if k == 0:
            band_lbl = [{"l1": w.l(i) + 0.5, "p1": float(p), "l2": w.l(i) + H_FUT + 0.5, "p2": float(p), "color": "#ffca28",
                         "width": 1.5, "style": "solid",
                         "label": {"text": "%s 80%%: %s" % (nm, vn(p, 1)), "pos": "end", "side": sd, "size": 11}}
                        for p, nm, sd in ((top, "trên", "above"), (bot, "dưới", "below"))]
    # vùng thanh khoản gần nhất ở NOW + xác suất chạm
    segs, pool_txt = list(band_lbl), []
    for side, key, col, name in ((1, "liq_above", "#f48fb1", "vùng trên"), (-1, "liq_below", "#80cbc4", "vùng dưới")):
        lv = float(I[key][now])
        if not np.isfinite(lv):
            continue
        p1, dist = touch_prob(d, now, lv, side, 4)
        p4, _ = touch_prob(d, now, lv, side, 16)
        txt = "%s %s · cách %s ATR · chạm 1h %d%% · 4h %d%%" % (name, vn(lv, 1), vn(dist, 1), round(100 * p1),
                                                                 round(100 * p4))
        pool_txt.append(txt)
        segs.append({"l1": w.l(now) - 24, "p1": lv, "l2": w.l(now) + H_FUT + 0.5, "p2": lv, "color": col, "width": 1.5,
                     "style": "dashed", "autoscale": "near", "near": 30,
                     "label": {"text": txt, "pos": "end", "side": "above" if side > 0 else "below", "size": 11}})
    B4 = J["ket_qua"]["XAUUSD"]["B"]["4h"]
    band_nen = B4["dai_gia"]["mo_hinh"]["NEN"]
    ghost = w.candles(w.b, w.b + H_FUT)
    fut = [c["time"] for c in ghost]
    return {
        "file": "4_nhan_dien", "title": "4 · Đầu ra gợi ý cho bộ nhận diện: dải giá + xác suất chạm vùng (kèm bỏ phiếu và "
                                         "mô hình học để so)", "sym": "XAUUSD M15",
        "info": [
            "<b>Dải vàng</b> = khoảng giá 80%% cho 4 giờ tới, tính tại nến hiện tại (đậm) và mỗi 4 giờ trước đó (nhạt). "
            "Mô hình «Nền» (giờ + biến động gần): phủ thật %s, tốt hơn dải cố định %s. Thêm ICT / indicator làm dải kém đi." % (
                pct(band_nen["phu_chung"], 0), pct(band_nen["skill_vs_B0"], 0)),
            "<b>Đường hồng / xanh</b> = vùng thanh khoản ICT gần nhất + xác suất chạm (theo khoảng cách, giờ, biến động; "
            "2018–2023). Vùng ICT không hút giá hơn mức bất kỳ cùng khoảng cách.",
            "<b>Nến xám</b> sau vạch «hiện tại» = giá thật sau đó, chỉ để đối chiếu.",
            "<b>Pane dưới:</b> bỏ phiếu 8 thành phần (K16 %s) và P(lên trước) của mô hình học (AUC 4h %s) — gần như đoán mò." % (
                score_txt(J, "XAUUSD", "K16"), vn(B4["huong"]["mo_hinh"]["NEN+CA_HAI"]["auc"], 3)),
        ],
        "prec": prec(w), "candles": w.candles(), "ghost": ghost, "future": fut, "lines": ema_lines(w),
        "markers": w.ict_markers(),
        "boxes": boxes, "segments": segs, "now_l": w.l(now), "pool_txt": pool_txt,
        "bands": [
            {"caption": "Order flow M15", "bars": w.band(I["of"], "OF ↑", "OF ↓", "OF chưa rõ")},
            {"caption": "ICT H1", "bars": w.band(I["h1"], "H1 ↑", "H1 ↓", "H1 —")},
            {"caption": "ICT H4", "bars": w.band(I["h4"], "H4 ↑", "H4 ↓", "H4 —")},
        ],
        "panes": [
            {"title": "Bỏ phiếu 8 thành phần (ICT H1, H4, OF, DOL + EMA H1, H4, MACD, Donchian) — K16 bật khi |phiếu| ≥ 6",
             "height": 120, "range": [-8.5, 8.5], "hist": vote, "hlines": [{"value": 6, "color": "#3a4654"},
                                                                         {"value": -6, "color": "#3a4654"}]},
            {"title": "Mô hình học (ngoài mẫu): P(lên trước) 4h — nền + cả hai (xanh), chỉ nền (xám); P(đi một chiều) 4h (vàng)",
             "height": 130, "range": [10, 75],
             "series": [{"color": UP, "width": 2, "data": ex_line("p_len_4h_NEN+CA_HAI", 100)},
                        {"color": "#78909c", "width": 1, "style": 2, "data": ex_line("p_len_4h_NEN", 100)},
                        {"color": "#ffb300", "width": 1.5, "data": ex_line("p_1chieu_4h_NEN+CA_HAI", 100)}],
             "hlines": [{"value": 50, "color": "#3a4654"}]},
        ],
        "legend": legend_ict() + [{"c": "#ffb300", "t": "dải 80% (4h tới)", "box": True},
                                  {"c": "#f48fb1", "t": "vùng trên"}, {"c": "#80cbc4", "t": "vùng dưới"},
                                  {"c": "#78909c", "t": "giá thật sau đó", "box": True}],
    }


# ---------------------------------------------------------------- HTML

HTML = r"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><title>__TITLE__</title>
<style>
  :root { --bg:#0f1419; --line:#2a3441; --text:#e6edf3; --dim:#9aa7b4; --mute:#6e7d8c; }
  html,body { margin:0; background:var(--bg); color:var(--text); font:13px -apple-system,"Segoe UI",Roboto,Arial,sans-serif; }
  .top { display:flex; align-items:center; gap:14px; padding:8px 16px; border-bottom:1px solid var(--line); background:#121920; }
  .top b { font-size:14px; } .top .tag { color:#ffb300; border:1px solid #5a4510; border-radius:10px; padding:1px 8px; font-size:12px; }
  .top .sym { color:var(--dim); }
  h1 { font-size:16px; font-weight:600; margin:10px 16px 6px; }
  .wrap { position:relative; margin:0 16px; }
  .info { display:grid; grid-template-columns:1fr 1fr; gap:4px 24px; margin:0 16px 8px; background:#121920;
          border:1px solid var(--line); border-radius:6px; padding:8px 12px; color:var(--dim); line-height:1.45;
          font-size:12.5px; }
  .info p { margin:0; } .info b { color:var(--text); }
  .ptitle { color:var(--dim); font-size:12px; margin:6px 0 2px; }
  .legend { display:flex; flex-wrap:wrap; gap:14px; margin:8px 16px; color:var(--dim); font-size:12px; }
  .legend i { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:5px; vertical-align:-1px; }
  .legend i.box { border-radius:2px; opacity:.6; }
  .foot { margin:4px 16px 10px; color:var(--mute); font-size:11.5px; }
</style>
<script>window.MSL = {};</script>
<script src="__LWC__"></script>
<script src="__PRIM__"></script>
</head><body>
<div class="top"><b>Market Structure Lab</b><span class="tag">nguyên mẫu — chưa phải plugin của lab</span>
  <span class="sym">__SYM__ · giờ UTC · đoạn phát triển (trước 01/09/2024)</span></div>
<h1>__TITLE__</h1>
<div class="info" id="info"></div>
<div class="wrap"><div id="main"></div></div>
<div id="panes"></div>
<div class="legend" id="legend"></div>
<div class="foot">Số «đúng hướng» = đúng hướng cân bằng 1h / 4h trên XAUUSD, EURUSD M15 2018 – 08/2024
(docs/research/khao_sat_ict_indicator.md). 50% = đoán mò. Không phải tín hiệu giao dịch.
Biểu đồ: TradingView Lightweight Charts™ (Apache-2.0).</div>
<script>
var SPEC = __SPEC__;
var LWC = LightweightCharts, P = MSL.primitives, W = 1568;
function base(el, h, showTime) {
  return LWC.createChart(el, { width: W, height: h,
    layout: { background: { color: '#0f1419' }, textColor: '#9aa7b4', fontSize: 11, attributionLogo: false },
    grid: { vertLines: { color: '#1b232c' }, horzLines: { color: '#1b232c' } },
    rightPriceScale: { borderColor: '#2a3441', minimumWidth: 74 },
    timeScale: { borderColor: '#2a3441', timeVisible: true, secondsVisible: false, visible: showTime, rightOffset: 0 },
    crosshair: { mode: LWC.CrosshairMode.Normal }, handleScroll: false, handleScale: false });
}
var allTimes = SPEC.candles.map(function (c) { return c.time; }).concat(SPEC.future || []);
var nL = allTimes.length;
var RIGHT = SPEC.future ? 30 : 16;           // chỗ trống bên phải cho nhãn dải / chú thích
function frame(ch) { ch.timeScale().setVisibleLogicalRange({ from: -1, to: nL - 1 + RIGHT }); }
function filler(ch) {   // series rỗng mang đủ mốc thời gian → chỉ số logic giống nhau ở mọi chart
  var s = ch.addLineSeries({ lastValueVisible: false, priceLineVisible: false, visible: false, priceScaleId: 'filler' });
  ch.priceScale('filler').applyOptions({ visible: false });
  s.setData(allTimes.map(function (t) { return { time: t }; }));
}
// ---- chart giá
var mainH = 600, nb = (SPEC.bands || []).length, bandH = 14, bandGap = 3;
var main = base(document.getElementById('main'), mainH, false);
filler(main);
var cs = main.addCandlestickSeries({ upColor: '#26a69a', downColor: '#ef5350', borderUpColor: '#26a69a',
  borderDownColor: '#ef5350', wickUpColor: '#26a69a', wickDownColor: '#ef5350', priceLineVisible: false });
cs.setData(SPEC.candles);
cs.applyOptions({ priceFormat: { type: 'price', precision: SPEC.prec, minMove: Math.pow(10, -SPEC.prec) } });
var bottomPx = nb * (bandH + bandGap) + 12;
main.priceScale('right').applyOptions({ scaleMargins: { top: 0.06, bottom: bottomPx / mainH } });
if (SPEC.ghost) {
  var gs = main.addCandlestickSeries({ upColor: 'rgba(120,144,156,.55)', downColor: 'rgba(120,144,156,.3)',
    borderUpColor: '#78909c', borderDownColor: '#78909c', wickUpColor: '#78909c', wickDownColor: '#78909c',
    lastValueVisible: false, priceLineVisible: false });
  gs.setData(SPEC.ghost);
}
(SPEC.lines || []).forEach(function (L) {
  var s = main.addLineSeries({ color: L.color, lineWidth: L.width || 1, lastValueVisible: false, priceLineVisible: false,
    crosshairMarkerVisible: false });
  s.setData(L.data);
});
var mk = (SPEC.markers || []).slice().sort(function (a, b) { return a.time - b.time; });
cs.setMarkers(mk);
// nền (hộp cao hết pane) + vạch mỏng ở mép trên
var shade = new P.Boxes({}), strips = [];
var boxes = (SPEC.boxes || []).filter(function (b) { return !b.top; }).map(function (b) {
  if (b.p1 == null) { b.p1 = -1e7; b.p2 = 1e7; b.autoscale = false; }
  return b; });
shade.setItems(boxes);
cs.attachPrimitive(shade);
var topBoxes = (SPEC.boxes || []).filter(function (b) { return b.top; });
if (topBoxes.length) {   // vạch mỏng: quy đổi px → giá ở mỗi khung hình
  var tb = new P.Boxes({});
  cs.attachPrimitive(tb);
  var refresh = function () {
    tb.setItems(topBoxes.map(function (b) {
      var y1 = b.top[0] + 2, y2 = b.top[1] + 2;
      return { l1: b.l1, l2: b.l2, p1: cs.coordinateToPrice(y1), p2: cs.coordinateToPrice(y2), fill: b.fill,
               alpha: b.alpha, autoscale: false };
    }));
  };
  setTimeout(refresh, 50); setTimeout(refresh, 300);
}
if (SPEC.segments) {
  var sg = new P.Segments({ reserved: function () { return P.reservedRects(document.getElementById('main')); } });
  sg.setItems(SPEC.segments.map(function (s) { s.label = s.label || undefined; return s; }));
  cs.attachPrimitive(sg);
}
(SPEC.bands || []).forEach(function (B, i) {
  var band = new P.Band({ height: bandH, bottom: 3 + i * (bandH + bandGap), caption: B.caption, minTextX: 4 });
  band.setBars(B.bars.map(function (b) { b.textColor = '#e6edf3'; return b; }));
  cs.attachPrimitive(band);
});
if (SPEC.now_l != null) {
  var nowSeg = new P.Segments({});
  cs.attachPrimitive(nowSeg);
  var setNow = function () {
    var r = cs.coordinateToPrice(18), r2 = cs.coordinateToPrice(mainH - bottomPx);
    nowSeg.setItems([{ l1: SPEC.now_l + 0.5, p1: r, l2: SPEC.now_l + 0.5, p2: r2, color: '#e6edf3', width: 1,
      style: 'dotted', alpha: 0.7, autoscale: false,
      label: { text: 'hiện tại', pos: 'end', side: 'above', size: 11, color: '#e6edf3' } }]);
  };
  setTimeout(setNow, 60); setTimeout(setNow, 320);
}
frame(main);
// ---- pane phụ
var charts = [main];
(SPEC.panes || []).forEach(function (pn, k) {
  var box = document.createElement('div');
  box.className = 'wrap';
  box.innerHTML = '<div class="ptitle">' + pn.title + '</div><div></div>';
  document.getElementById('panes').appendChild(box);
  var last = k === SPEC.panes.length - 1;
  var ch = base(box.lastChild, pn.height + (last ? 26 : 0), last);
  filler(ch);
  var rng = pn.range;
  var prov = rng ? function () { return { priceRange: { minValue: rng[0], maxValue: rng[1] } }; } : undefined;
  var pp = pn.prec || 0, pf = { type: 'price', precision: pp, minMove: Math.pow(10, -pp) };
  if (pn.hist) {
    var hs = ch.addHistogramSeries({ base: 0, lastValueVisible: false, priceLineVisible: false, autoscaleInfoProvider: prov,
      priceFormat: pf });
    hs.setData(pn.hist);
    (pn.hlines || []).forEach(function (h) { hs.createPriceLine({ price: h.value, color: h.color, lineWidth: 1,
      lineStyle: 2, axisLabelVisible: false }); });
  }
  (pn.series || []).forEach(function (S, j) {
    var s = ch.addLineSeries({ color: S.color, lineWidth: S.width || 1, lineStyle: S.style || 0, lastValueVisible: false,
      priceLineVisible: false, autoscaleInfoProvider: prov, crosshairMarkerVisible: false, priceFormat: pf });
    s.setData(S.data);
    if (j === 0) (pn.hlines || []).forEach(function (h) { s.createPriceLine({ price: h.value, color: h.color,
      lineWidth: 1, lineStyle: 2, axisLabelVisible: true, title: '' }); });
  });
  frame(ch);
  charts.push(ch);
});
if (charts.length === 1) main.applyOptions({ timeScale: { visible: true } });
// ---- chú thích + hộp giải thích
document.getElementById('info').innerHTML = SPEC.info.map(function (t) { return '<p>' + t + '</p>'; }).join('');
document.getElementById('legend').innerHTML = (SPEC.legend || []).map(function (L) {
  return '<span><i class="' + (L.box ? 'box' : '') + '" style="background:' + L.c + '"></i>' + L.t + '</span>'; }).join('');
</script></body></html>
"""


def write_page(spec, out_dir):
    def rel(p):
        full = os.path.join(ROOT, p)
        try:
            return os.path.relpath(full, out_dir).replace("\\", "/")
        except ValueError:                       # khác ổ đĩa → đường dẫn tuyệt đối
            return "file:///" + full.replace("\\", "/")

    html = (HTML.replace("__TITLE__", spec["title"]).replace("__SYM__", spec["sym"])
            .replace("__LWC__", rel("frontend/vendor/lightweight-charts.standalone.production.js"))
            .replace("__PRIM__", rel("frontend/js/chart/primitives.js"))
            .replace("__SPEC__", json.dumps(spec, ensure_ascii=False, allow_nan=False)))
    path = os.path.join(out_dir, spec["file"] + ".html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    return path


def shoot(html, png, browser, height):
    url = "file:///" + os.path.abspath(html).replace("\\", "/")
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
           "--window-size=1600,%d" % height, "--virtual-time-budget=4000", "--screenshot=" + os.path.abspath(png),
           "--allow-file-access-from-files", url]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", default=os.path.join(ROOT, "docs", "research", "khao_sat", "ict_indicator_dev.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "research", "khao_sat", "chart_ket_hop"))
    ap.add_argument("--db", default=os.environ.get("MSL_DB_PATH") or os.path.join(ROOT, "data", "lab.sqlite"))
    ap.add_argument("--trinh-duyet", default=next((p for p in CHROME if os.path.exists(p)), None))
    args = ap.parse_args()
    with open(args.json, encoding="utf-8") as fh:
        J = json.load(fh)
    con = sqlite3.connect("file:%s?mode=ro" % args.db.replace("\\", "/"), uri=True)
    data = {}
    for spec in S.SETS:
        sym = spec["key"].split()[0]
        print("nạp", sym, flush=True)
        data[sym] = S.Data(spec, con, lambda m: None)
    os.makedirs(args.out, exist_ok=True)
    pages = [page1(J, data["XAUUSD"]), page2(J, data["EURUSD"]), page3(J, data["XAUUSD"]), page4(J, data["XAUUSD"])]
    for p in pages:
        html = write_page(p, args.out)
        if args.trinh_duyet:
            h = 175 + 600 + sum(pn["height"] + 30 for pn in p["panes"]) + 26 + 70
            shoot(html, os.path.join(args.out, p["file"] + ".png"), args.trinh_duyet, h)
            print("chụp", p["file"], flush=True)
        else:
            print("không thấy Chrome/Edge — chỉ ghi", html)


if __name__ == "__main__":
    main()
