"""Khảo sát kết hợp indicator + ICT cho bộ nhận diện trạng thái — CHỈ ĐỌC database.

Thuộc ``docs/plans/plan_nhan_dien_trang_thai.md`` (§6: tối ưu ICT + indicator bằng điểm dự báo; §7 bước 2b, 4).
Khung của người dùng: bias H1/H4, đích M15, vào lệnh M5. Tầm dự báo H = 1 giờ (4 nến M15) và 4 giờ (16 nến).

Ba câu hỏi:

1. Từng tín hiệu ICT (timeline ``ict_structure``) và từng indicator (EMA, ADX, RSI, MACD, Donchian trên M15 và H1/H4)
   đoán đúng HƯỚNG 1h/4h tới đâu? (phần A, luật đơn)
2. Các kiểu KẾT HỢP luật hay dùng có hơn tín hiệu ICT «cha» của nó không? Gồm: đồng thuận (AND), lọc theo ADX,
   hợp lưu với oscillator, discount/premium theo bias, bỏ phiếu. (phần A, luật kết hợp)
3. Kết hợp HỌC (cây tăng cường, walk-forward theo năm). Lấy một nền tối thiểu: giờ trong ngày, biến động gần,
   lợi suất gần. Thêm ICT, thêm indicator, hay thêm cả hai thì ba đầu ra của bộ nhận diện có tốt hơn không?
   Ba đầu ra: hướng 1h/4h, trạng thái «đi một chiều» 1h/4h, dải giá 80% 1h/4h. (phần B)
4. Vùng thanh khoản ICT còn nguyên gần nhất (trên/dưới) có bị chạm trong 1h/4h thường hơn một mức BẤT KỲ cùng khoảng
   cách không? Đây là đầu ra «mức gần nhất + xác suất chạm» của bộ nhận diện. (phần C)

Quy tắc:

* DB mở CHỈ ĐỌC. Chỉ dùng đoạn phát triển (trước 2024-09-01); script dừng nếu đoạn chạm đoạn kiểm tra.
* Đặc trưng ở nến t chỉ dùng thông tin ≤ t:
  - timeline ``ict_structure`` (trạng thái SAU nến t) và sự kiện có ``confirmed_bar_index`` ≤ t;
  - indicator tính trên nến ≤ t;
  - H1/H4 chỉ lấy nến khung lớn đã ĐÓNG trước close_time của nến t.
  Kết cục trên (t, t+h] chỉ dùng để chấm.
* Khai báo trước ở đầu file: tín hiệu (``TIN_HIEU``), kết hợp (``KET_HOP``), đặc trưng, siêu tham số, năm gập.
  Không sửa sau khi xem kết quả; nếu sửa thì đổi ``SURVEY_VERSION`` và ghi lý do.
* Không tính P&L hay win rate chiến lược. «Đúng hướng cân bằng» là thước đo thông tin, không phải tỷ lệ thắng.
  Mọi so sánh đều kèm CI bootstrap khối tuần. Phần A có thêm null dịch vòng và hiệu chỉnh BH.

Ví dụ (PowerShell, từ thư mục market-structure-lab)::

    .\\.venv\\Scripts\\python.exe research\\ict_indicator_survey.py --json docs\\research\\khao_sat\\ict_indicator_dev.json

Hình: ``research\\ve_ict_indicator.py`` (cần matplotlib).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sqlite3
import sys
import time
import warnings
from collections import Counter
from datetime import timedelta

import numpy as np
import pandas as pd
from numpy.lib.stride_tricks import sliding_window_view

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import regime_survey as RS  # noqa: E402  (nạp dữ liệu chỉ đọc + tiện ích thống kê của khảo sát 4a)
from core.algorithms.ict_structure import LEGACY_0_9, IctStructureAlgorithm  # noqa: E402
from core.engine import run_algorithm  # noqa: E402

SURVEY_VERSION = "ict-indicator-survey-v1"
TEST_START = RS.TEST_START
NY = RS.NY
SEED = 7
SETS = (
    {"key": "XAUUSD M15 2018–08/2024", "ds": "ds_a5212fd37814", "start": "2018-01-01", "end": TEST_START},
    {"key": "EURUSD M15 2018–08/2024", "ds": "ds_a9a2a5e4cef5", "start": "2018-01-01", "end": TEST_START},
)
HS = (4, 16)                          # 1 giờ, 4 giờ (nến M15)
TEN_H = {4: "1h", 16: "4h"}
K_TOUCH = 1.0                         # hướng = chạm +1·ATR_t trước −1·ATR_t
GAP_MAX = pd.Timedelta(hours=3)       # cửa sổ kết cục vắt qua khoảng trống > 3 giờ (cuối tuần, lễ) → bỏ
BAD_G = 4                             # có dữ liệu bất thường trong 4 nến gần nhất → bỏ nến
RECENT = 16                           # «gần đây» = 16 nến (4 giờ)
WARM_M15, WARM_HTF = 600, 210         # nến khởi động indicator (EMA200, ADX)
COST_ATR = {"XAUUSD": 0.19, "EURUSD": 0.17}   # chi phí cơ sở / ATR M15 (plan_nhan_dien_trang_thai.md §2)
N_BOOT, N_SHIFT, N_BOOT_ML = 1000, 199, 300
MIN_SIDE = 200                        # mỗi phía (+1 / −1) cần ≥ 200 nến
FOLDS = (2020, 2021, 2022, 2023, 2024)   # năm kiểm, walk-forward mở rộng (2024 = 01–08)
TRAIN_STEP = 2                        # huấn luyện trên 1/2 số nến (kết cục chồng lấn → nến kề nhau gần trùng)
HGB = dict(max_iter=200, learning_rate=0.05, max_leaf_nodes=31, min_samples_leaf=400, l2_regularization=1.0,
           early_stopping=False, random_state=SEED)
Q_BAND = 0.9                          # dải giá: phân vị 90% của biên lên và của biên xuống → dải ≈ 80%
TREND_Q = 2 / 3                       # «đi một chiều» = ER tương lai ≥ phân vị 2/3 của 2018–2019
VI_DU = ("2024-08-12", "2024-08-24")  # cửa sổ lưu cho hình ví dụ (XAUUSD, dự báo của gập 2024)
BO_DAC_TRUNG = ("NEN", "NEN+IND", "NEN+ICT", "NEN+CA_HAI")

TIN_HIEU = {
    # tên: (nhóm, mô tả) — giá trị +1 / −1 / 0 (không ý kiến) / NaN (chưa có)
    "ict_h4": ("ICT", "Thứ tự cấu trúc H4"),
    "ict_h1": ("ICT", "Thứ tự cấu trúc H1"),
    "ict_of": ("ICT", "Order flow M15"),
    "ict_order": ("ICT", "Thứ tự cấu trúc M15"),
    "ict_dol": ("ICT", "Phía DOL sau shift"),
    "ict_pd": ("ICT", "pd_bias (phản ứng ở FVG H1/H4)"),
    "ict_shift16": ("ICT", "SHIFT trong 4 giờ qua"),
    "ict_sweep16": ("ICT", "Sweep trong 4 giờ qua (đảo chiều)"),
    "ict_zone": ("ICT", "Discount/premium M15 (đảo chiều)"),
    "ict_h4zone": ("ICT", "Discount/premium H4 (đảo chiều)"),
    "ema_m15": ("IND", "EMA50 > EMA200 · M15"),
    "ema_h1": ("IND", "EMA50 > EMA200 · H1"),
    "ema_h4": ("IND", "EMA50 > EMA200 · H4"),
    "adx_di_m15": ("IND", "+DI > −DI · M15"),
    "adx_di_h1": ("IND", "+DI > −DI · H1"),
    "rsi_m15": ("IND", "RSI > 50 · M15"),
    "rsi_ext_m15": ("IND", "RSI ≤ 30 / ≥ 70 · M15 (đảo chiều)"),
    "macd_m15": ("IND", "MACD hist > 0 · M15"),
    "macd_h1": ("IND", "MACD hist > 0 · H1"),
    "don_m15": ("IND", "Phá kênh Donchian 20 · M15"),
    "don_h1": ("IND", "Phá kênh Donchian 20 · H1"),
}
KET_HOP = {
    # tên: (mô tả, tín hiệu «cha» để so cặp: kết hợp có hơn cha không)
    "K01": ("ICT H1 = H4", "ict_h4"),
    "K02": ("EMA H1 = H4", "ema_h4"),
    "K03": ("ICT H1=H4 ∧ EMA H1=H4", "K01"),
    "K04": ("ICT top-down H4=H1=OF", "ict_of"),
    "K05": ("Top-down ICT ∧ EMA H1", "K04"),
    "K06": ("Top-down ICT ∧ ADX H1 ≥ 25", "K04"),
    "K07": ("OF ∧ ADX M15 ≥ 25", "ict_of"),
    "K08": ("OF ∧ ADX M15 ≤ 20", "ict_of"),
    "K09": ("Sweep ∧ RSI ≤ 35 / ≥ 65", "ict_sweep16"),
    "K10": ("Sweep ∧ ADX M15 ≤ 20", "ict_sweep16"),
    "K11": ("Shift ∧ MACD M15 cùng chiều", "ict_shift16"),
    "K12": ("DOL ∧ Donchian M15 cùng chiều", "ict_dol"),
    "K13": ("Discount/premium theo bias ICT H1=H4", "ict_zone"),
    "K14": ("Discount/premium theo bias EMA H1=H4", "ict_zone"),
    "K15": ("OF ∧ MACD ∧ RSI M15 cùng chiều", "ict_of"),
    "K16": ("Bỏ phiếu 8 (≥ 6 cùng chiều)", "K01"),
}

DINH_NGHIA = {
    "trang_thai_sau_nen_t": "Đặc trưng ở nến t dùng timeline ict_structure sau nến t, sự kiện confirmed ≤ t, indicator "
                            "trên nến ≤ t; H1/H4 (gộp từ M15 theo mốc UTC) chỉ nến có giờ đóng ≤ close_time của t.",
    "huong": "Chạm +1·ATR_t trước −1·ATR_t trong (t, t+h] (cùng nến hoặc không chạm → bỏ). ATR_t = ATR Wilder 14 của "
             "ict_structure sau nến t.",
    "dung_huong_can_bang": "BA = ½·[P(lên trước | tín hiệu +1) + P(xuống trước | tín hiệu −1)] = 0,5 + ½·(P(lên|+1) − "
                           "P(lên|−1)). Không bị trôi giá (drift) làm lệch: tín hiệu vô ích → 50%. Hoà vốn với rào ±1 "
                           "ATR M15 và chi phí c (theo ATR): BA ≥ (1 + c)/2.",
    "phu": "Độ phủ = tỷ lệ nến đủ điều kiện mà tín hiệu ≠ 0.",
    "ci": "Bootstrap khối tuần (tuần ISO của ngày giao dịch kết thúc 17:00 NY), 1000 lần, seed 7. MDE80 = 2,8 × SE.",
    "null": "Dịch vòng chuỗi tín hiệu so với kết cục, 199 độ dịch đều trong [s_min, N − s_min], s_min = max(128, độ "
            "trễ ACF < 0,05 của tín hiệu). p hai phía theo |BA − 0,5|. So cặp: dịch cùng lúc kết hợp và cha.",
    "bh": "Benjamini–Hochberg trên toàn bộ phép thử luật (2 mã × 2 tầm × đơn + kết hợp), q < 0,05.",
    "nen_hop_le": "ATR > 0, ICT đã có thứ tự M15/H1/H4, indicator đã qua khởi động (M15 600 nến, H1/H4 210 nến), không "
                  "có ICT_GAP bất thường / HTF_BAR_DEGRADED H1/H4 trong 4 nến gần nhất, cửa sổ kết cục không vắt qua "
                  "khoảng trống > 3 giờ.",
    "walk_forward": "Năm kiểm 2020, 2021, 2022, 2023, 2024 (01–08); huấn luyện trên mọi năm trước (mở rộng), bỏ h nến "
                    "cuối trước năm kiểm (kết cục chồng lấn), lấy 1/2 số nến. HistGradientBoosting (siêu tham số cố "
                    "định HGB, không tinh chỉnh).",
    "bo_dac_trung": "NEN: giờ NY, thứ, biên độ 4/16 nến gần nhất, ATR so với trung vị 10 ngày, lợi suất 4/16 nến. IND: "
                    "EMA, ADX/DI, RSI, MACD, Donchian trên M15/H1/H4 + ER 32. ICT: order flow, thứ tự M15/H1/H4, DOL, "
                    "pd_bias, shift/sweep gần đây, vị trí dealing range M15/H4, displacement, PDH/PDL đã lấy, khoảng "
                    "cách tới vùng thanh khoản trên/dưới, số sweep/run/shift gần đây.",
    "trang_thai_1_chieu": "ER tương lai |C[t+h] − C[t]| / Σ|ΔC| trong (t, t+h] ≥ phân vị 2/3 của 2018–2019 → 1.",
    "dai_gia": "Biên lên = (max high (t, t+h] − C_t)/ATR_t; biên xuống = (C_t − min low)/ATR_t. Mỗi mô hình dự báo "
               "phân vị 90% của từng biên → dải [C − q↓·ATR, C + q↑·ATR], phủ chung mục tiêu ≈ 80%. Điểm: pinball "
               "loss q = 0,9 (cộng hai biên), skill = 1 − loss / loss của B0. B0 = phân vị huấn luyện không điều "
               "kiện; B1 = phân vị theo giờ NY.",
    "auc_ci": "AUC gộp các năm kiểm; CI bootstrap khối tuần 300 lần trên chính các dự báo ngoài mẫu (không huấn "
              "luyện lại) — chỉ tính bất định của tập kiểm.",
    "vung_hut_gia": "Phần C. Vùng = liq_above / liq_below của timeline (vùng còn nguyên gần nhất). Thực tế = biên "
                    "lên/xuống ≥ khoảng cách tới vùng. Kỳ vọng = tỷ lệ nến hợp lệ cùng giờ NY × tam phân vị ATR/giá có "
                    "biên ≥ đúng khoảng cách đó (mức đặt bất kỳ). Chênh > 0 → vùng ICT hút giá hơn mức bất kỳ.",
}


# ---------------------------------------------------------------- indicator (nhân quả, trên nến ≤ t)


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def rma(x, n):
    return pd.Series(x).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def adx_di(h, l, c, n=14):
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)])
    up = np.r_[0.0, np.diff(h)]
    dn = np.r_[0.0, -np.diff(l)]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    mdm = np.where((dn > up) & (dn > 0), dn, 0.0)
    atr = rma(tr, n)
    with np.errstate(invalid="ignore", divide="ignore"):
        pdi = 100 * rma(pdm, n) / atr
        mdi = 100 * rma(mdm, n) / atr
        dx = 100 * np.abs(pdi - mdi) / (pdi + mdi)
    return rma(np.nan_to_num(dx, nan=0.0), n), pdi, mdi


def rsi(c, n=14):
    d = np.r_[0.0, np.diff(c)]
    g, lo = rma(np.maximum(d, 0), n), rma(np.maximum(-d, 0), n)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(lo > 0, 100 - 100 / (1 + g / np.where(lo > 0, lo, 1)), 100.0)


def macd_hist(c):
    m = ema(c, 12) - ema(c, 26)
    return m - ema(m, 9)


def donchian(h, l, c, n=20):
    """Vị trí close trong kênh 20 nến (gồm t), hướng phá kênh gần nhất (close vượt kênh của 20 nến TRƯỚC t), bề rộng."""
    hh = pd.Series(h).rolling(n, min_periods=n).max().to_numpy()
    ll = pd.Series(l).rolling(n, min_periods=n).min().to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        pos = (c - ll) / (hh - ll)
    ph, pl = np.r_[np.nan, hh[:-1]], np.r_[np.nan, ll[:-1]]
    brk = np.where(c > ph, 1.0, np.where(c < pl, -1.0, 0.0))
    d = pd.Series(np.where(brk != 0, brk, np.nan)).ffill().fillna(0.0).to_numpy()
    return pos, d, hh - ll


def ind_pack(h, l, c, warm):
    adx, pdi, mdi = adx_di(h, l, c)
    pos, d, w = donchian(h, l, c)
    out = {"e50": ema(c, 50), "e200": ema(c, 200), "adx": adx, "di": pdi - mdi, "rsi": rsi(c), "macd": macd_hist(c),
           "don_pos": pos, "don_dir": d, "don_w": w}
    out = {k: np.array(v, float) for k, v in out.items()}     # pandas 3 trả mảng chỉ đọc
    for v in out.values():
        v[:warm] = np.nan
    return out


# ---------------------------------------------------------------- dữ liệu + đặc trưng

DIR = {"up": 1.0, "down": -1.0, 1: 1.0, -1: -1.0, 0: 0.0}
SWEEP_DIR = {"SSL": 1.0, "BSL": -1.0}            # quét thanh khoản bên bán → hàm ý tăng (đảo chiều)
ZONE_DIR = {"discount": 1.0, "premium": -1.0, "eq": 0.0}
EV_KEEP = ("SHIFT_UP", "SHIFT_DOWN", "LIQ_SWEEP_BSL", "LIQ_SWEEP_SSL", "LIQ_RUN_UP", "LIQ_RUN_DOWN")


def rolling_sum(x, w):
    c = np.cumsum(x)
    out = c.copy()
    out[w:] -= c[:-w]
    return out


def sgn(a):
    return np.where(np.isfinite(a), np.sign(a), np.nan)


def agree(*xs):
    """Tất cả cùng dấu ≠ 0 → dấu đó; có NaN → NaN; còn lại 0."""
    X = np.vstack(xs)
    nan = np.isnan(X).any(0)
    s = np.sign(np.nan_to_num(X[0]))
    same = np.all(np.nan_to_num(X) == s, axis=0) & (s != 0)
    out = np.where(same, s, 0.0)
    out[nan] = np.nan
    return out


def gate(x, cond, cond_val):
    """Giữ tín hiệu x khi cond đúng, còn lại 0; giá trị điều kiện NaN → NaN."""
    out = np.where(cond, x, 0.0)
    out[np.isnan(x) | np.isnan(cond_val)] = np.nan
    return out


class Data:
    def __init__(self, spec, con, log):
        ds, bars, tf, meta = RS.load(con, spec, allow_test=False)
        if tf != "M15":
            raise SystemExit("Khảo sát này chạy trên M15.")
        self.meta, self.symbol, self.key = meta, ds["symbol"], spec["key"]
        N = self.N = len(bars)
        self.O = np.array([b.open for b in bars])
        self.H = np.array([b.high for b in bars])
        self.L = np.array([b.low for b in bars])
        self.C = np.array([b.close for b in bars])
        t_open = pd.DatetimeIndex([b.bar_time for b in bars]).tz_convert("UTC")
        if t_open[-1] >= pd.Timestamp(TEST_START, tz="UTC"):
            raise SystemExit("Có nến trong đoạn kiểm tra — dừng.")
        self.t_open = t_open.tz_localize(None)
        t_close = pd.DatetimeIndex([b.close_time for b in bars]).tz_convert("UTC").tz_localize(None).to_numpy()
        ny = t_open.tz_convert("America/New_York")
        self.ny = ny
        self.hour_ny = (ny.hour + ny.minute / 60.0).to_numpy().astype(float)
        td = [(b.bar_time.astimezone(NY) + timedelta(hours=7)).date() for b in bars]
        wk = [d.isocalendar()[:2] for d in td]
        wmap = {w: i for i, w in enumerate(sorted(set(wk)))}
        self.week = np.array([wmap[w] for w in wk])
        self.nW = len(wmap)
        self.year = np.array([d.year for d in td])
        self.weekday = np.array([d.weekday() for d in td], float)
        self.meta["so_tuan"] = self.nW
        self.meta["so_ngay_giao_dich"] = len(set(td))
        # ---- ICT
        t0 = time.time()
        algo = IctStructureAlgorithm(timeframe="M15", session_calendar=RS.CAL[self.symbol], **LEGACY_0_9)
        res = run_algorithm(bars, algo)
        self.meta["ict_structure"] = algo.version
        self.meta["thoi_gian_ict_s"] = round(time.time() - t0, 2)
        log("  ict_structure %s: %.1f s" % (algo.version, time.time() - t0))
        self.ict, self.events, self.bad = self._ict(res.timeline, res.events)
        del res
        # ---- indicator M15, H1, H4
        self.ind = {"M15": ind_pack(self.H, self.L, self.C, WARM_M15)}
        df = pd.DataFrame({"o": self.O, "h": self.H, "l": self.L, "c": self.C}, index=self.t_open)
        for name, rule, delta in (("H1", "1h", pd.Timedelta(hours=1)), ("H4", "4h", pd.Timedelta(hours=4))):
            g = df.resample(rule, label="left", closed="left").agg(
                {"o": "first", "h": "max", "l": "min", "c": "last"}).dropna()
            ends = (g.index + delta).to_numpy()
            j = np.searchsorted(ends, t_close, side="right") - 1        # nến khung lớn cuối cùng đã đóng
            pk = ind_pack(g["h"].to_numpy(), g["l"].to_numpy(), g["c"].to_numpy(), WARM_HTF)
            jj = np.clip(j, 0, None)
            self.ind[name] = {k: np.where(j >= 0, v[jj], np.nan) for k, v in pk.items()}
            self.meta["so_nen_%s" % name] = int(len(g))
        # ---- kết cục (chỉ để chấm)
        self.atr = self.ict["atr"]
        gap_after = np.r_[np.diff(self.t_open.to_numpy()) > GAP_MAX.to_timedelta64(), False]
        cg = np.r_[0, np.cumsum(gap_after)]
        self.y = {}
        for h in HS:
            T = np.arange(N - h)
            a = self.atr[T]
            good = np.isfinite(a) & (a > 0)
            aa = np.where(good, a, np.nan)
            Hw = sliding_window_view(self.H[1:], h)
            Lw = sliding_window_view(self.L[1:], h)
            with np.errstate(invalid="ignore", divide="ignore"):
                hi, lo = Hw.max(1), Lw.min(1)
                uh = Hw >= (self.C[T] + K_TOUCH * aa)[:, None]
                dh = Lw <= (self.C[T] - K_TOUCH * aa)[:, None]
                fu = np.where(uh.any(1), uh.argmax(1), h)
                fd = np.where(dh.any(1), dh.argmax(1), h)
                up = np.where(fu < fd, 1.0, np.where(fd < fu, 0.0, np.nan))
                cabs = np.r_[0.0, np.cumsum(np.abs(np.diff(self.C)))]
                den = cabs[T + h] - cabs[T]
                fer = np.where(den > 0, np.abs(self.C[T + h] - self.C[T]) / np.where(den > 0, den, 1), np.nan)
            gap_ok = (cg[T + h] - cg[T]) == 0                         # không khoảng trống > 3h trong (t, t+h]
            out = {}
            for k, v in (("up", up), ("mfe_up", (hi - self.C[T]) / aa), ("mfe_dn", (self.C[T] - lo) / aa),
                         ("fer", fer)):
                full = np.full(N, np.nan)
                full[T] = np.where(good & gap_ok, v, np.nan)
                out[k] = full
            self.y[h] = out
        # ---- nến hợp lệ
        I, X = self.ict, self.ind
        self.ok = (np.isfinite(self.atr) & (np.nan_to_num(self.atr) > 0) & np.isfinite(I["order"])
                   & np.isfinite(I["h1"]) & np.isfinite(I["h4"]) & np.isfinite(X["M15"]["e200"])
                   & np.isfinite(X["H1"]["e200"]) & np.isfinite(X["H4"]["e200"])
                   & (rolling_sum(self.bad.astype(int), BAD_G) == 0))
        self.meta["nen_hop_le"] = int(self.ok.sum())
        self.sig = self._signals()
        self.feat = self._features()

    # ------------------------------------------------------------ ICT
    def _ict(self, tl, events):
        N = self.N

        def col(k):
            return [p.get(k) if p else None for p in tl]

        def mapped(k, table):
            return np.array([table.get(v, np.nan) if v is not None else np.nan for v in col(k)], float)

        I = {"atr": RS.arr(col("atr")), "of": RS.arr(col("order_flow")), "order": RS.arr(col("order")),
             "h1": RS.arr(col("htf_H1_order")), "h4": RS.arr(col("htf_H4_order")), "pd": RS.arr(col("pd_bias")),
             "shift_dir": mapped("last_shift", DIR), "shift_age": RS.arr(col("last_shift_bars")),
             "sweep_dir": mapped("last_sweep", SWEEP_DIR), "sweep_age": RS.arr(col("last_sweep_bars")),
             "zone": mapped("zone", ZONE_DIR), "h4_zone": mapped("htf_H4_zone", ZONE_DIR),
             "range_pos": RS.arr(col("range_pos")), "dhi": RS.arr(col("dealing_hi")), "dlo": RS.arr(col("dealing_lo")),
             "h4_pos": RS.arr(col("htf_H4_range_pos")), "liq_above": RS.arr(col("liq_above")),
             "liq_below": RS.arr(col("liq_below")), "dol_dist": RS.arr(col("dol_dist_atr")),
             "pdh_taken": RS.arr(col("pdh_taken")), "pdl_taken": RS.arr(col("pdl_taken")),
             "of_since": RS.arr(col("order_flow_since"))}
        I["dol"] = np.nan_to_num(RS.arr(col("dol_side")), nan=0.0)            # không có DOL → 0
        I["disp"] = np.nan_to_num(mapped("displacement", DIR), nan=0.0)
        pb = np.array([v is True for v in col("protected_broken")])
        I["order_eff"] = np.where(pb & np.isfinite(I["order"]), 0.0, I["order"])
        cnt = {k: np.zeros(N) for k in EV_KEEP}
        bad = np.zeros(N, bool)
        keep = []
        n_bad = Counter()
        for e in events:
            s, t = e.structure_type, e.confirmed_bar_index
            if s in cnt:
                cnt[s][t] += 1
                keep.append((s, int(t), float(e.price)))
            elif s == "ICT_GAP" and e.details.get("bat_thuong"):
                bad[t] = True
                n_bad["khoang_trong_bat_thuong"] += 1
            elif s == "HTF_BAR_DEGRADED" and e.details.get("khung") in ("H1", "H4"):
                bad[t] = True
                n_bad["nen_%s_degraded" % e.details.get("khung")] += 1
        self.meta["su_kien_bat_thuong"] = dict(n_bad)
        for k in EV_KEEP:
            I["n16_" + k] = rolling_sum(cnt[k], RECENT)
        I["n48_SHIFT_UP"] = rolling_sum(cnt["SHIFT_UP"], 48)
        I["n48_SHIFT_DOWN"] = rolling_sum(cnt["SHIFT_DOWN"], 48)
        return I, keep, bad

    # ------------------------------------------------------------ tín hiệu luật (khai báo trước)
    def _signals(self):
        I, X = self.ict, self.ind
        M, H1 = X["M15"], X["H1"]
        s = {"ict_h4": I["h4"], "ict_h1": I["h1"], "ict_of": I["of"], "ict_order": I["order"], "ict_dol": I["dol"],
             "ict_pd": I["pd"]}
        with np.errstate(invalid="ignore"):
            s["ict_shift16"] = np.where(I["shift_age"] <= RECENT, I["shift_dir"], 0.0)
            s["ict_sweep16"] = np.where(I["sweep_age"] <= RECENT, I["sweep_dir"], 0.0)
            s["ict_zone"], s["ict_h4zone"] = I["zone"], I["h4_zone"]
            for f in ("M15", "H1", "H4"):
                s["ema_" + f.lower()] = sgn(X[f]["e50"] - X[f]["e200"])
            s["adx_di_m15"], s["adx_di_h1"] = sgn(M["di"]), sgn(H1["di"])
            s["rsi_m15"] = sgn(M["rsi"] - 50)
            r = M["rsi"]
            s["rsi_ext_m15"] = np.where(np.isfinite(r), np.where(r <= 30, 1.0, np.where(r >= 70, -1.0, 0.0)), np.nan)
            s["macd_m15"], s["macd_h1"] = sgn(M["macd"]), sgn(H1["macd"])
            s["don_m15"], s["don_h1"] = M["don_dir"], H1["don_dir"]
            k = {}
            k["K01"] = agree(I["h1"], I["h4"])
            k["K02"] = agree(s["ema_h1"], s["ema_h4"])
            k["K03"] = agree(I["h1"], I["h4"], s["ema_h1"], s["ema_h4"])
            k["K04"] = agree(I["h4"], I["h1"], I["of"])
            k["K05"] = agree(I["h4"], I["h1"], I["of"], s["ema_h1"])
            k["K06"] = gate(k["K04"], H1["adx"] >= 25, H1["adx"])
            k["K07"] = gate(I["of"], M["adx"] >= 25, M["adx"])
            k["K08"] = gate(I["of"], M["adx"] <= 20, M["adx"])
            sw = s["ict_sweep16"]
            conf = ((sw > 0) & (r <= 35)) | ((sw < 0) & (r >= 65))
            k["K09"] = gate(sw, conf, r)
            k["K10"] = gate(sw, M["adx"] <= 20, M["adx"])
            k["K11"] = agree(s["ict_shift16"], s["macd_m15"])
            k["K12"] = agree(I["dol"], s["don_m15"])
            k["K13"] = agree(I["zone"], k["K01"])
            k["K14"] = agree(I["zone"], k["K02"])
            k["K15"] = agree(I["of"], s["macd_m15"], s["rsi_m15"])
            v = np.vstack([I["h1"], I["h4"], I["of"], I["dol"], s["ema_h1"], s["ema_h4"], s["macd_m15"],
                           s["don_m15"]])
            vs = v.sum(0)
            k["K16"] = np.where(np.isnan(vs), np.nan, np.where(np.abs(vs) >= 6, np.sign(vs), 0.0))
        s.update(k)
        return s

    # ------------------------------------------------------------ đặc trưng cho mô hình học
    def _features(self):
        I, X, C, a = self.ict, self.ind, self.C, self.atr
        N = self.N
        idx = np.arange(N)
        with np.errstate(invalid="ignore", divide="ignore"):
            hh4 = pd.Series(self.H).rolling(4).max().to_numpy()
            ll4 = pd.Series(self.L).rolling(4).min().to_numpy()
            hh16 = pd.Series(self.H).rolling(16).max().to_numpy()
            ll16 = pd.Series(self.L).rolling(16).min().to_numpy()
            amed = pd.Series(a).rolling(960, min_periods=200).median().to_numpy()
            base = {"gio_ny": self.hour_ny, "thu": self.weekday, "bien_do_4": np.log((hh4 - ll4) / a),
                    "bien_do_16": np.log((hh16 - ll16) / a), "atr_so_trung_vi": np.log(a / amed),
                    "loi_suat_4": (C - np.r_[np.full(4, np.nan), C[:-4]]) / a,
                    "loi_suat_16": (C - np.r_[np.full(16, np.nan), C[:-16]]) / a}
            ind = {}
            for f in ("M15", "H1", "H4"):
                P = X[f]
                fl = f.lower()
                ind["ema_kc_" + fl] = (P["e50"] - P["e200"]) / a
                ind["gia_ema50_" + fl] = (C - P["e50"]) / a
                ind["adx_" + fl] = P["adx"]
                ind["di_" + fl] = P["di"]
                ind["rsi_" + fl] = P["rsi"]
                ind["macd_" + fl] = P["macd"] / a
                ind["don_vi_tri_" + fl] = P["don_pos"]
                ind["don_huong_" + fl] = P["don_dir"]
            ind["don_rong_m15"] = np.log(X["M15"]["don_w"] / a)
            n = 32
            cabs = np.r_[0.0, np.cumsum(np.abs(np.diff(C)))]
            ser = np.full(N, np.nan)
            den = cabs[n:] - cabs[:-n]
            ser[n:] = np.where(den > 0, (C[n:] - C[:-n]) / np.where(den > 0, den, 1), 0.0)
            ind["er32"] = ser
            ict = {k: I[k] for k in ("of", "order", "order_eff", "h1", "h4", "dol", "pd", "shift_dir", "sweep_dir",
                                     "zone", "h4_zone", "range_pos", "disp", "pdh_taken", "pdl_taken")}
            ict["shift_tuoi"] = np.minimum(I["shift_age"], 500)
            ict["sweep_tuoi"] = np.minimum(I["sweep_age"], 500)
            ict["shift_gan"] = np.nan_to_num(I["shift_dir"]) * np.exp(-np.nan_to_num(I["shift_age"], nan=1e9) / RECENT)
            ict["sweep_gan"] = np.nan_to_num(I["sweep_dir"]) * np.exp(-np.nan_to_num(I["sweep_age"], nan=1e9) / RECENT)
            ict["dealing_rong"] = np.log((I["dhi"] - I["dlo"]) / a)
            ict["h4_vi_tri"] = np.clip(I["h4_pos"], -1, 2)
            ict["kc_vung_tren"] = np.log1p(np.maximum(I["liq_above"] - C, 0) / a)
            ict["kc_vung_duoi"] = np.log1p(np.maximum(C - I["liq_below"], 0) / a)
            ict["kc_dol"] = np.log1p(I["dol_dist"])
            ict["of_tuoi"] = np.minimum(idx - I["of_since"], 2000)
            for k in EV_KEEP:
                ict["n16_" + k] = I["n16_" + k]
            ict["n48_SHIFT_UP"], ict["n48_SHIFT_DOWN"] = I["n48_SHIFT_UP"], I["n48_SHIFT_DOWN"]
        return {"NEN": base, "IND": ind, "ICT": ict}

    def matrix(self, which):
        parts = {"NEN": ("NEN",), "NEN+IND": ("NEN", "IND"), "NEN+ICT": ("NEN", "ICT"),
                 "NEN+CA_HAI": ("NEN", "IND", "ICT")}[which]
        names, cols = [], []
        for p in parts:
            for k, v in self.feat[p].items():
                names.append("%s:%s" % (p, k))
                cols.append(np.asarray(v, float))
        X = np.column_stack(cols).astype(np.float32)
        X[~np.isfinite(X)] = np.nan
        return X, names


# ---------------------------------------------------------------- phần A: luật đơn và luật kết hợp


class RuleEngine:
    """Đúng hướng cân bằng (BA) của một tín hiệu ±1; CI bootstrap khối tuần; null dịch vòng; so cặp với «cha»."""

    def __init__(self, week, nW, n_boot, n_shift):
        self.week, self.nW, self.n_shift = week, nW, n_shift
        rng = np.random.default_rng(SEED)
        self.M = rng.multinomial(nW, np.full(nW, 1.0 / nW), size=n_boot).astype(float)

    def sums(self, s, y, base):
        with np.errstate(invalid="ignore"):
            v = base & np.isfinite(s) & (s != 0)
            p, n = v & (s > 0), v & (s < 0)
        wk, nW = self.week, self.nW
        return (np.bincount(wk[p], weights=y[p], minlength=nW), np.bincount(wk[p], minlength=nW).astype(float),
                np.bincount(wk[n], weights=y[n], minlength=nW), np.bincount(wk[n], minlength=nW).astype(float))

    @staticmethod
    def ba(Sp, Cp, Sn, Cn):
        with np.errstate(invalid="ignore", divide="ignore"):
            return 0.5 + 0.5 * (Sp / Cp - Sn / Cn)

    def point(self, s, y, base):
        Sp, Cp, Sn, Cn = self.sums(s, y, base)
        if Cp.sum() < MIN_SIDE or Cn.sum() < MIN_SIDE:
            return None, (Sp, Cp, Sn, Cn)
        return float(self.ba(Sp.sum(), Cp.sum(), Sn.sum(), Cn.sum())), (Sp, Cp, Sn, Cn)

    def boot(self, parts):
        Sp, Cp, Sn, Cn = parts
        M = self.M
        return self.ba(M @ Sp, M @ Cp, M @ Sn, M @ Cn)

    def shifts(self, s):
        smin = max(128, RS.decor_lag(np.nan_to_num(s, nan=0.0)))
        return RS.shift_list(len(s), smin, self.n_shift)

    def test(self, s, y, base, year, parent=None):
        val, parts = self.point(s, y, base)
        Sp, Cp, Sn, Cn = parts
        elig = base & np.isfinite(s)
        out = {"n_tang": int(Cp.sum()), "n_giam": int(Cn.sum()),
               "phu": RS.rnd((Cp.sum() + Cn.sum()) / max(1, elig.sum()), 4)}
        if val is None:
            out["du_mau"] = False
            return out
        bs = self.boot(parts)
        bs = bs[np.isfinite(bs)]
        sh = self.shifts(s)
        nulls = []
        for k in sh:
            v, _p = self.point(np.roll(s, k), y, base)
            if v is not None:
                nulls.append(v)
        nulls = np.array(nulls)
        p = (1 + np.sum(np.abs(nulls - 0.5) >= abs(val - 0.5))) / (1 + len(nulls))
        se = float(np.std(bs, ddof=1))
        out.update({"du_mau": True, "ba": RS.rnd(val, 4),
                    "p_len_khi_tang": RS.rnd(Sp.sum() / Cp.sum(), 4), "p_xuong_khi_giam": RS.rnd(1 - Sn.sum() / Cn.sum(), 4),
                    "ci95": [RS.rnd(np.quantile(bs, 0.025), 4), RS.rnd(np.quantile(bs, 0.975), 4)],
                    "se": RS.rnd(se, 4), "mde80": RS.rnd(2.8 * se, 4),
                    "null": {"p": RS.rnd(p, 4), "tb": RS.rnd(nulls.mean(), 4),
                             "p2.5_p97.5": [RS.rnd(np.quantile(nulls, 0.025), 4), RS.rnd(np.quantile(nulls, 0.975), 4)],
                             "so_do_dich": int(len(nulls)), "s_min": int(sh[0])}})
        out["theo_nam"] = {}
        for Y in np.unique(year[base]):
            v, _p = self.point(s, y, base & (year == Y))
            out["theo_nam"][str(int(Y))] = RS.rnd(v, 4)
        if parent is not None:
            out["so_voi_cha"] = self.paired(s, parent, y, base, val, bs_self=parts)
        return out

    def paired(self, s, par, y, base, val, bs_self):
        vp, pparts = self.point(par, y, base)
        if vp is None:
            return None
        d = self.boot(bs_self) - self.boot(pparts)
        d = d[np.isfinite(d)]
        sh = self.shifts(s)
        nulls = []
        for k in sh:
            a, _x = self.point(np.roll(s, k), y, base)
            b, _x = self.point(np.roll(par, k), y, base)
            if a is not None and b is not None:
                nulls.append(a - b)
        nulls = np.array(nulls)
        delta = val - vp
        p = (1 + np.sum(np.abs(nulls) >= abs(delta))) / (1 + len(nulls)) if len(nulls) else None
        return {"ba_cha": RS.rnd(vp, 4), "chenh": RS.rnd(delta, 4),
                "ci95": [RS.rnd(np.quantile(d, 0.025), 4), RS.rnd(np.quantile(d, 0.975), 4)],
                "p_null": RS.rnd(p, 4),
                "hon_cha": bool(p is not None and p < 0.05 and np.quantile(d, 0.025) > 0)}


def part_a(d, eng, log):
    out = {}
    for h in HS:
        y = d.y[h]["up"]
        base = d.ok & np.isfinite(y)
        rows = {}
        t0 = time.time()
        for name in TIN_HIEU:
            rows[name] = eng.test(d.sig[name], y, base, d.year)
        for name, (_desc, par) in KET_HOP.items():
            rows[name] = eng.test(d.sig[name], y, base, d.year, parent=d.sig[par])
        out[TEN_H[h]] = {"n_nen": int(base.sum()), "ty_le_len_truoc": RS.rnd(np.nanmean(y[base]), 4), "tin_hieu": rows}
        log("  A · %s: %d phép thử, %.0f s" % (TEN_H[h], len(rows), time.time() - t0))
    return out


def apply_bh(results):
    """BH trên mọi phép thử luật đủ mẫu (cả hai mã, cả hai tầm); ghi q vào chỗ."""
    refs = []
    for sym in results.values():
        for hh in sym["A"].values():
            for r in hh["tin_hieu"].values():
                if r.get("du_mau"):
                    refs.append(r)
    if not refs:
        return 0
    p = np.array([r["null"]["p"] for r in refs])
    n = len(p)
    o = np.argsort(p)
    q = p[o] * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    qq = np.empty(n)
    qq[o] = np.minimum(q, 1.0)
    for r, v in zip(refs, qq):
        r["null"]["q_bh"] = RS.rnd(v, 4)
        r["vuot_null"] = bool(v < 0.05 and (r["ci95"][0] > 0.5 or r["ci95"][1] < 0.5))
    return n


# ---------------------------------------------------------------- phần B: kết hợp học (walk-forward)


class AucBoot:
    """AUC có trọng số (xử lý điểm bằng nhau), sắp một lần, bootstrap bằng trọng số dòng."""

    def __init__(self, score, y):
        o = np.argsort(score, kind="mergesort")
        s = score[o]
        self.o, self.y = o, y[o]
        self.starts = np.r_[0, np.flatnonzero(np.diff(s)) + 1]

    def auc(self, w):
        ws = w[self.o]
        gp = np.add.reduceat(ws * self.y, self.starts)
        gn = np.add.reduceat(ws * (1 - self.y), self.starts)
        cn = np.cumsum(gn) - gn
        return float((gp * (cn + 0.5 * gn)).sum() / (gp.sum() * gn.sum()))


def pinball(y, q, tau):
    u = y - q
    return np.where(u >= 0, tau * u, (tau - 1) * u)


def fold_masks(d, valid, h):
    idx = np.arange(d.N)
    for Y in FOLDS:
        test = valid & (d.year == Y)
        if not test.any():
            continue
        first = int(np.argmax(d.year == Y))
        train = valid & (idx < first - h) & (idx % TRAIN_STEP == 0)
        yield Y, train, test


def part_b(d, n_boot_ml, log, hgb, keep_pred):
    from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

    rng = np.random.default_rng(SEED + 1)
    Mw = rng.multinomial(d.nW, np.full(d.nW, 1.0 / d.nW), size=n_boot_ml).astype(float)
    mats = {k: d.matrix(k) for k in BO_DAC_TRUNG}
    out = {"dac_trung": {k: v[1] for k, v in mats.items()}}
    preds = {}
    fer_thr = {}
    for h in HS:
        Y = d.y[h]
        early = d.ok & np.isfinite(Y["fer"]) & (d.year <= 2019)
        fer_thr[h] = float(np.quantile(Y["fer"][early], TREND_Q))
    out["nguong_er_1_chieu"] = {TEN_H[h]: RS.rnd(v, 4) for h, v in fer_thr.items()}
    for h in HS:
        Y = d.y[h]
        res_h = {}
        # ---- hướng và trạng thái: phân loại
        for target in ("huong", "mot_chieu"):
            t0 = time.time()
            if target == "huong":
                y = Y["up"]
            else:
                with np.errstate(invalid="ignore"):
                    y = np.where(np.isfinite(Y["fer"]), (Y["fer"] >= fer_thr[h]).astype(float), np.nan)
            valid = d.ok & np.isfinite(y)
            P = {}
            per_fold = {}
            for m in BO_DAC_TRUNG:
                X = mats[m][0]
                pr = np.full(d.N, np.nan)
                for Yr, tr, te in fold_masks(d, valid, h):
                    clf = HistGradientBoostingClassifier(**hgb)
                    clf.fit(X[tr], y[tr])
                    te_all = d.ok & (d.year == Yr)          # dự báo mọi nến hợp lệ (cho hình); chấm chỉ trên te
                    pr[te_all] = clf.predict_proba(X[te_all])[:, 1]
                P[m] = pr
            oos = valid & np.isfinite(P[BO_DAC_TRUNG[0]])
            yy = y[oos]
            wk = d.week[oos]
            aucs = {m: AucBoot(P[m][oos], yy) for m in BO_DAC_TRUNG}
            ones = np.ones(oos.sum())
            point = {m: aucs[m].auc(ones) for m in BO_DAC_TRUNG}
            bs = {m: np.array([aucs[m].auc(Mw[b][wk]) for b in range(n_boot_ml)]) for m in BO_DAC_TRUNG}
            for m in BO_DAC_TRUNG:
                per_fold[m] = {}
                for Yr in FOLDS:
                    sel = oos & (d.year == Yr)
                    if sel.sum() > 100 and 0 < y[sel].mean() < 1:
                        per_fold[m][str(Yr)] = RS.rnd(AucBoot(P[m][sel], y[sel]).auc(np.ones(sel.sum())), 4)
            # log-loss skill so với tỷ lệ nền của tập huấn luyện từng năm
            clim = np.full(d.N, np.nan)
            for Yr, tr, te in fold_masks(d, valid, h):
                clim[te] = y[tr].mean()
            eps = 1e-6

            def ll(p):
                p = np.clip(p, eps, 1 - eps)
                return -(yy * np.log(p) + (1 - yy) * np.log(1 - p))

            ll0 = ll(clim[oos])
            mres = {}
            for m in BO_DAC_TRUNG:
                lm = ll(P[m][oos])
                S0 = np.bincount(wk, weights=ll0, minlength=d.nW)
                Sm = np.bincount(wk, weights=lm, minlength=d.nW)
                sk_b = 1 - (Mw @ Sm) / (Mw @ S0)
                mres[m] = {"auc": RS.rnd(point[m], 4),
                           "ci95": [RS.rnd(np.quantile(bs[m], 0.025), 4), RS.rnd(np.quantile(bs[m], 0.975), 4)],
                           "theo_nam": per_fold[m],
                           "ll_skill": RS.rnd(1 - lm.sum() / ll0.sum(), 5),
                           "ll_skill_ci95": [RS.rnd(np.quantile(sk_b, 0.025), 5), RS.rnd(np.quantile(sk_b, 0.975), 5)]}
            pairs = {}
            for a, b in (("NEN+IND", "NEN"), ("NEN+ICT", "NEN"), ("NEN+CA_HAI", "NEN"), ("NEN+CA_HAI", "NEN+IND"),
                         ("NEN+CA_HAI", "NEN+ICT")):
                dd = bs[a] - bs[b]
                lo, hi = np.quantile(dd, 0.025), np.quantile(dd, 0.975)
                pairs["%s − %s" % (a, b)] = {"chenh": RS.rnd(point[a] - point[b], 4), "ci95": [RS.rnd(lo, 4), RS.rnd(hi, 4)],
                                             "hon": bool(lo > 0), "kem": bool(hi < 0)}
            res_h[target] = {"n_kiem": int(oos.sum()), "ty_le_1": RS.rnd(yy.mean(), 4), "mo_hinh": mres, "so_cap": pairs}
            if keep_pred:
                preds[(target, h)] = P
            log("  B · %s · %s: %.0f s" % (TEN_H[h], target, time.time() - t0))
        # ---- dải giá: hồi quy phân vị cho biên lên / biên xuống
        t0 = time.time()
        valid = d.ok & np.isfinite(Y["mfe_up"]) & np.isfinite(Y["mfe_dn"])
        Q = {}
        hour = np.floor(d.hour_ny).astype(int)
        for side in ("mfe_up", "mfe_dn"):
            y = Y[side]
            Q[("B0", side)] = np.full(d.N, np.nan)
            Q[("B1", side)] = np.full(d.N, np.nan)
            for Yr, tr, te in fold_masks(d, valid, h):
                te_all = d.ok & (d.year == Yr)
                Q[("B0", side)][te_all] = np.quantile(y[tr], Q_BAND)
                qh = np.array([np.quantile(y[tr & (hour == g)], Q_BAND) if (tr & (hour == g)).sum() > 50
                               else np.quantile(y[tr], Q_BAND) for g in range(24)])
                Q[("B1", side)][te_all] = qh[hour[te_all]]
            for m in BO_DAC_TRUNG:
                X = mats[m][0]
                pr = np.full(d.N, np.nan)
                for Yr, tr, te in fold_masks(d, valid, h):
                    reg = HistGradientBoostingRegressor(loss="quantile", quantile=Q_BAND, **hgb)
                    reg.fit(X[tr], y[tr])
                    te_all = d.ok & (d.year == Yr)
                    pr[te_all] = reg.predict(X[te_all])
                Q[(m, side)] = pr
        oos = valid & np.isfinite(Q[("B0", "mfe_up")])
        wk = d.week[oos]
        models = ("B0", "B1") + BO_DAC_TRUNG
        loss = {m: pinball(Y["mfe_up"][oos], Q[(m, "mfe_up")][oos], Q_BAND)
                + pinball(Y["mfe_dn"][oos], Q[(m, "mfe_dn")][oos], Q_BAND) for m in models}
        S = {m: np.bincount(wk, weights=loss[m], minlength=d.nW) for m in models}
        band = {}
        for m in models:
            qu, qd_ = Q[(m, "mfe_up")][oos], Q[(m, "mfe_dn")][oos]
            inside = (Y["mfe_up"][oos] <= qu) & (Y["mfe_dn"][oos] <= qd_)
            sk_b = 1 - (Mw @ S[m]) / (Mw @ S["B0"])
            band[m] = {"skill_vs_B0": RS.rnd(1 - loss[m].sum() / loss["B0"].sum(), 4),
                       "skill_ci95": [RS.rnd(np.quantile(sk_b, 0.025), 4), RS.rnd(np.quantile(sk_b, 0.975), 4)],
                       "phu_chung": RS.rnd(inside.mean(), 4),
                       "phu_tren": RS.rnd((Y["mfe_up"][oos] <= qu).mean(), 4),
                       "phu_duoi": RS.rnd((Y["mfe_dn"][oos] <= qd_).mean(), 4),
                       "rong_tb_atr": RS.rnd(np.mean(qu + qd_), 3),
                       "rong_trung_vi_atr": RS.rnd(np.median(qu + qd_), 3)}
        pairs = {}
        for a, b in (("NEN", "B1"), ("NEN+IND", "NEN"), ("NEN+ICT", "NEN"), ("NEN+CA_HAI", "NEN"),
                     ("NEN+CA_HAI", "NEN+IND"), ("NEN+CA_HAI", "NEN+ICT")):
            dd = 1 - (Mw @ S[a]) / (Mw @ S[b])       # skill của a so với b
            lo, hi = np.quantile(dd, 0.025), np.quantile(dd, 0.975)
            pairs["%s so với %s" % (a, b)] = {"skill": RS.rnd(1 - S[a].sum() / S[b].sum(), 4),
                                               "ci95": [RS.rnd(lo, 4), RS.rnd(hi, 4)], "hon": bool(lo > 0),
                                               "kem": bool(hi < 0)}
        res_h["dai_gia"] = {"n_kiem": int(oos.sum()), "mo_hinh": band, "so_cap": pairs,
                            "bien_trung_vi_atr": {"len": RS.rnd(np.median(Y["mfe_up"][oos]), 3),
                                                  "xuong": RS.rnd(np.median(Y["mfe_dn"][oos]), 3)}}
        if keep_pred:
            preds[("dai_gia", h)] = Q
        log("  B · %s · dải giá: %.0f s" % (TEN_H[h], time.time() - t0))
        out[TEN_H[h]] = res_h
    return out, preds


# ---------------------------------------------------------------- phần C: mức thanh khoản ICT có «hút» giá không

KC_BINS = (0.0, 0.5, 1.0, 2.0, 4.0, np.inf)     # khoảng cách tới vùng, theo ATR_t


def part_c(d, n_boot):
    """Vùng thanh khoản còn nguyên gần nhất phía trên / dưới (``liq_above`` / ``liq_below``) bị chạm trong (t, t+h]
    thường hơn một mức BẤT KỲ cùng khoảng cách không?

    Thực tế: chạm = biên lên (xuống) ≥ khoảng cách. Kỳ vọng: P(biên ≥ khoảng cách) theo phân phối biên của MỌI nến
    hợp lệ cùng giờ NY và cùng tam phân vị ATR/giá — tức là một mức đặt ngẫu nhiên ở đúng khoảng cách đó. Chênh > 0 →
    vùng ICT hút giá hơn mức bất kỳ. CI bootstrap khối tuần."""
    rng = np.random.default_rng(SEED + 2)
    M = rng.multinomial(d.nW, np.full(d.nW, 1.0 / d.nW), size=n_boot).astype(float)
    bps = d.atr / d.C
    okb = np.isfinite(bps)
    cut = np.quantile(bps[okb & d.ok], [1 / 3, 2 / 3])
    stratum = np.floor(d.hour_ny).astype(int) * 3 + np.digitize(np.nan_to_num(bps), cut)
    out = {}
    for h in HS:
        Y = d.y[h]
        res_h = {}
        for side, mfe in (("tren", Y["mfe_up"]), ("duoi", Y["mfe_dn"])):
            with np.errstate(invalid="ignore", divide="ignore"):
                dist = ((d.ict["liq_above"] - d.C) if side == "tren" else (d.C - d.ict["liq_below"])) / d.atr
            base = d.ok & np.isfinite(mfe)
            valid = base & np.isfinite(dist) & (dist > 0)
            pred = np.full(d.N, np.nan)
            for g in np.unique(stratum[base]):
                pool = np.sort(mfe[base & (stratum == g)])
                sel = valid & (stratum == g)
                if pool.size < 50 or not sel.any():
                    continue
                pred[sel] = 1.0 - np.searchsorted(pool, dist[sel], side="left") / pool.size
            valid &= np.isfinite(pred)
            hit = (mfe >= dist).astype(float)
            rows = []
            for lo, hi in zip(KC_BINS[:-1], KC_BINS[1:]):
                sel = valid & (dist >= lo) & (dist < hi)
                if sel.sum() < 200:
                    rows.append({"tu": lo, "den": None if math.isinf(hi) else hi, "n": int(sel.sum())})
                    continue
                wk = d.week[sel]
                Sd = np.bincount(wk, weights=hit[sel] - pred[sel], minlength=d.nW)
                Cn = np.bincount(wk, minlength=d.nW).astype(float)
                bs = (M @ Sd) / (M @ Cn)
                rows.append({"tu": lo, "den": None if math.isinf(hi) else hi, "n": int(sel.sum()),
                             "thuc_te": RS.rnd(hit[sel].mean(), 4), "ky_vong": RS.rnd(pred[sel].mean(), 4),
                             "chenh": RS.rnd(hit[sel].mean() - pred[sel].mean(), 4),
                             "ci95": [RS.rnd(np.quantile(bs, 0.025), 4), RS.rnd(np.quantile(bs, 0.975), 4)]})
            wk = d.week[valid]
            Sd = np.bincount(wk, weights=hit[valid] - pred[valid], minlength=d.nW)
            Cn = np.bincount(wk, minlength=d.nW).astype(float)
            bs = (M @ Sd) / (M @ Cn)
            res_h[side] = {"n": int(valid.sum()), "co_vung": RS.rnd(valid.sum() / max(1, base.sum()), 4),
                           "kc_trung_vi_atr": RS.rnd(np.median(dist[valid]), 3),
                           "thuc_te": RS.rnd(hit[valid].mean(), 4), "ky_vong": RS.rnd(pred[valid].mean(), 4),
                           "chenh": RS.rnd(hit[valid].mean() - pred[valid].mean(), 4),
                           "ci95": [RS.rnd(np.quantile(bs, 0.025), 4), RS.rnd(np.quantile(bs, 0.975), 4)],
                           "theo_khoang_cach": rows}
        out[TEN_H[h]] = res_h
    return out


# ---------------------------------------------------------------- dữ liệu cho hình ví dụ


def example_dump(d, preds):
    t0, t1 = (pd.Timestamp(x, tz="America/New_York") for x in VI_DU)
    sel = np.flatnonzero((d.ny >= t0) & (d.ny < t1))
    if sel.size == 0:
        return None
    a, b = int(sel[0]), int(sel[-1]) + 1
    if d.t_open[b - 1] >= pd.Timestamp(TEST_START):
        raise SystemExit("Cửa sổ ví dụ chạm đoạn kiểm tra.")

    def L(x, k=4):
        return [RS.rnd(v, k) for v in np.asarray(x, float)[a:b]]

    M = d.ind["M15"]
    ex = {"tu": VI_DU[0], "den_truoc": VI_DU[1], "gio_ny": [t.strftime("%Y-%m-%d %H:%M") for t in d.ny[a:b]],
          "open": L(d.O, 3), "high": L(d.H, 3), "low": L(d.L, 3), "close": L(d.C, 3), "atr": L(d.atr, 3),
          "ema50": L(M["e50"], 3), "ema200": L(M["e200"], 3), "adx": L(M["adx"], 2), "rsi": L(M["rsi"], 2),
          "macd": L(M["macd"], 4), "ict_h1": L(d.ict["h1"], 0), "ict_h4": L(d.ict["h4"], 0),
          "ict_of": L(d.ict["of"], 0), "liq_tren": L(d.ict["liq_above"], 3), "liq_duoi": L(d.ict["liq_below"], 3),
          "ok": [bool(v) for v in d.ok[a:b]],
          "su_kien": [{"loai": s, "nen": t - a, "gia": RS.rnd(p, 3)} for s, t, p in d.events if a <= t < b]}
    for h in HS:
        tag = TEN_H[h]
        for m in ("NEN", "NEN+CA_HAI"):
            ex["p_len_%s_%s" % (tag, m)] = L(preds[("huong", h)][m], 4)
            ex["p_1chieu_%s_%s" % (tag, m)] = L(preds[("mot_chieu", h)][m], 4)
            ex["q_len_%s_%s" % (tag, m)] = L(preds[("dai_gia", h)][(m, "mfe_up")], 3)
            ex["q_xuong_%s_%s" % (tag, m)] = L(preds[("dai_gia", h)][(m, "mfe_dn")], 3)
        ex["q_len_%s_B1" % tag] = L(preds[("dai_gia", h)][("B1", "mfe_up")], 3)
        ex["q_xuong_%s_B1" % tag] = L(preds[("dai_gia", h)][("B1", "mfe_dn")], 3)
    return ex


# ---------------------------------------------------------------- chạy


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", default=os.path.join(ROOT, "docs", "research", "khao_sat", "ict_indicator_dev.json"))
    ap.add_argument("--db", default=os.environ.get("MSL_DB_PATH") or os.path.join(ROOT, "data", "lab.sqlite"))
    ap.add_argument("--ma", default="XAUUSD,EURUSD", help="Danh sách mã, cách nhau bởi dấu phẩy")
    ap.add_argument("--nhanh", action="store_true", help="Chạy thử nhanh (ít bootstrap, ít cây) — không dùng để kết luận")
    args = ap.parse_args()
    t_all = time.time()

    def log(msg):
        print(msg, flush=True)

    n_boot, n_shift, n_boot_ml, hgb = N_BOOT, N_SHIFT, N_BOOT_ML, dict(HGB)
    if args.nhanh:
        n_boot, n_shift, n_boot_ml = 200, 29, 60
        hgb["max_iter"] = 40
    uri = "file:%s?mode=ro" % args.db.replace("\\", "/")
    con = sqlite3.connect(uri, uri=True)
    with open(os.path.abspath(__file__), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    import sklearn
    meta = {"phien_ban": SURVEY_VERSION, "script_sha256": sha, "python": platform.python_version(),
            "numpy": np.__version__, "pandas": pd.__version__, "sklearn": sklearn.__version__,
            "doan_kiem_tra_tu": TEST_START, "seed": SEED, "chay_nhanh": bool(args.nhanh),
            "tham_so": {"HS": list(HS), "k_cham": K_TOUCH, "recent": RECENT, "n_boot": n_boot, "n_shift": n_shift,
                        "n_boot_ml": n_boot_ml, "min_moi_phia": MIN_SIDE, "folds": list(FOLDS),
                        "train_step": TRAIN_STEP, "hgb": hgb, "q_band": Q_BAND, "trend_q": TREND_Q,
                        "chi_phi_atr": COST_ATR, "gap_max_gio": 3, "bad_g": BAD_G},
            "tao_luc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    out = {"meta": meta, "dinh_nghia": DINH_NGHIA,
           "tin_hieu": {k: {"nhom": g, "mo_ta": t} for k, (g, t) in TIN_HIEU.items()},
           "ket_hop": {k: {"mo_ta": t, "cha": p} for k, (t, p) in KET_HOP.items()}, "ket_qua": {}}
    wanted = [s.strip() for s in args.ma.split(",") if s.strip()]
    for spec in SETS:
        sym = spec["key"].split()[0]
        if sym not in wanted:
            continue
        log("== %s" % spec["key"])
        t0 = time.time()
        d = Data(spec, con, log)
        log("  dữ liệu + đặc trưng: %.0f s, %d nến, %d hợp lệ" % (time.time() - t0, d.N, d.ok.sum()))
        eng = RuleEngine(d.week, d.nW, n_boot, n_shift)
        res = {"meta": d.meta, "A": part_a(d, eng, log)}
        res["C"] = part_c(d, n_boot)
        res["B"], preds = part_b(d, n_boot_ml, log, hgb, keep_pred=(sym == "XAUUSD"))
        if sym == "XAUUSD":
            res["vi_du"] = example_dump(d, preds)
        out["ket_qua"][sym] = res
        del d, preds
    n_tests = apply_bh(out["ket_qua"])
    meta["so_phep_thu_bh"] = n_tests
    meta["thoi_gian_chay_s"] = round(time.time() - t_all, 1)
    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    log("Đã ghi %s (%.0f s)" % (args.json, time.time() - t_all))


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    main()
