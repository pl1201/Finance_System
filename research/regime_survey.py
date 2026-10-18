"""Khảo sát 4a của giai đoạn 4 (``docs/plans/plan_bias_regime.md`` §8): đo trước khi viết ``ict_regime``.

Ba câu hỏi:

1. regime ở M15 có kéo dài đủ lâu SAU KHI PHÁT HIỆN để router dùng được không (cổng đi/dừng — M3, M4);
2. bằng chứng ICT có thêm thông tin so với một chỉ số thống kê đơn giản (Kaufman ER) không (M5, M6);
3. số liệu để chốt ngưỡng nháp ở plan §4.7 (M1, M2, đường trễ ↔ lật).

Đây là khảo sát, KHÔNG phải thuật toán của lab:

* đọc DB CHỈ ĐỌC (``mode=ro``); mọi đoạn kết thúc trước 2024-09-01 — script từ chối khoảng chạm đoạn kiểm tra
  nếu không có ``--allow-test`` (không bao giờ dùng cho thiết kế);
* mọi «bộ phát hiện» (baseline của lab, bằng chứng thô, hai biến thể nháp «kịch bản» / «điểm» cài NGAY TRONG
  SCRIPT) ở nến t chỉ dùng thông tin ≤ t: timeline của ``ict_structure`` 0.4.1 (trạng thái SAU nến t) và sự kiện có
  ``confirmed_bar_index`` ≤ t. Trạng thái ở t dùng được từ t+1;
* nhãn hậu kiểm (DC / Lunde–Timmermann họ θ × ATR, trend-scanning họ L nến) và kết cục tương lai NHÌN VỀ SAU — chỉ
  dùng để chấm, không bao giờ là đầu vào;
* không P&L, không win rate. Mọi so sánh kèm null (shift test, chuỗi dịch vòng) và khoảng tin cậy bootstrap theo
  khối tuần; cỡ mẫu hiệu dụng là số đoạn / số tuần, không phải số nến.

Chỗ plan mơ hồ: chọn ở docstring từng hàm và gom lại ở ``DINH_NGHIA`` (ghi vào JSON).

Ví dụ (PowerShell, từ thư mục market-structure-lab)::

    .\\.venv\\Scripts\\python.exe research\\regime_survey.py --json docs\\research\\khao_sat\\regime_survey_dev.json
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
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.stats import spearmanr

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from core.algorithms.dc_atr_structure import DcAtrStructureAlgorithm  # noqa: E402
from core.algorithms.dc_atr_structure.detector import DcDetector  # noqa: E402
from core.algorithms.hmm_online import HmmOnlineAlgorithm  # noqa: E402
from core.algorithms.ict_structure import IctStructureAlgorithm  # noqa: E402
from core.algorithms.indicator_baseline import IndicatorBaselineAlgorithm  # noqa: E402
from core.data.loader import rows_checksum  # noqa: E402
from core.data.resample import resample_ohlc  # noqa: E402
from core.engine import run_algorithm  # noqa: E402
from core.eval.matcher import match_labels  # noqa: E402
from core.eval.protocol import MATCHER_MIN_COST_V1  # noqa: E402
from core.labels import ReferenceLabel  # noqa: E402
from core.types import build_bars  # noqa: E402

SURVEY_VERSION = "regime-survey-v1"
TEST_START = "2024-09-01"
SEED = 7
NY = ZoneInfo("America/New_York")
CAL = {"XAUUSD": "cme_globex_metals", "EURUSD": "fx_spot"}

DEV_MAIN = {"key": "XAUUSD M15 01–08/2024", "ds": "ds_db1583cd4dde", "start": "2024-01-01", "end": TEST_START}
DEV_EXT = (
    {"key": "XAUUSD M15 2018–2023", "ds": "ds_a5212fd37814", "start": "2018-01-01", "end": "2024-01-01"},
    {"key": "EURUSD M15 2018–2023", "ds": "ds_a9a2a5e4cef5", "start": "2018-01-01", "end": "2024-01-01"},
)
H1_SETS = (
    {"key": "XAUUSD H1 01–08/2024", "ds": "ds_771a79d4d604", "start": "2024-01-01", "end": TEST_START},
    {"key": "XAUUSD H1 2018–2023 (gộp từ M15)", "ds": "ds_a5212fd37814", "start": "2018-01-01",
     "end": "2024-01-01", "resample": "H1"},
)

# Mã trạng thái (không phải mã sự kiện của lab — chỉ trong khảo sát)
KD, DT, UNC, TUP, TDN, RNG, BUP, BDN = -1, -2, 0, 1, 2, 3, 4, 5
STATE_NAME = {KD: "khoi_dong", DT: "du_lieu_thieu", UNC: "uncertain", TUP: "trend_tang", TDN: "trend_giam",
              RNG: "range", BUP: "breakout_tang", BDN: "breakout_giam"}
# Mã lý do Uncertain (biến thể nháp)
REASONS = {0: "-", 1: "K2_muc_bao_ve_bi_vuot", 2: "K2_dol_nguoc", 3: "K4_xung_dot_khung", 4: "K5_shift_chua_di_tiep",
           5: "K6_khong_du_bang_chung", 6: "cho_xac_nhan_c_nen", 7: "breakout_chua_xac_nhan",
           8: "diem_huong_chua_du", 9: "diem_co_huong_nhung_di_ngang", 10: "diem_khong_huong_khong_bien",
           11: "breakout_that_bai_khong_ve_range"}

# Tham số nháp plan §4.7 (+ vài lựa chọn của khảo sát cho chỗ plan không nói — xem DINH_NGHIA)
DRAFT = {"G": 4, "W": 48, "S": 4, "Nr": 16, "k": 0.25, "B": 12, "m": 4, "H": 8, "c": 1, "n_er": 32,
         "q_wid": [0.2, 0.8], "q_er_low": 0.5, "q_in": 0.7, "q_out": 0.5, "q_rho": 0.8,
         "pen_atr": 0.1, "edge_atr": 0.5, "w_pd": 0.5, "range_giu": "dieu_kien", "k1": "cung_chieu"}
REF_THETA = (1, 2, 4)
REF_L = (16, 32, 64)
TS_TMIN = 2.0
HS = (4, 16, 64)
K_FP = 1.0
TOLS = (8, 32)
N_BOOT = 1000
N_SHIFT = 199
N_SHIFT_EXT = 99
N_SHIFT_M4 = 49
N_SHIFT_F1 = 99
MIN_N_TERCILE = 30
HMM_PARAMS = {"n_states": 3, "train_bars": 2000, "seed": 42, "n_iter": 50}

DINH_NGHIA = {
    "trang_thai_sau_nen_t": "Mọi bộ phát hiện: trạng thái ở nến t tính từ timeline (sau t) + sự kiện confirmed ≤ t; "
                            "dùng được từ t+1. Nhãn hậu kiểm và kết cục chỉ để chấm.",
    "nhan_DC": "DcDetector của lab (close, Δ = θ·ATR[e] khoá tại nến cực trị e), chạy LIÊN TỤC qua khoảng trống (không "
               "reset), ATR = ATR Wilder 14 của ict_structure. Gán ngược: nến (e_i, e_{i+1}] mang chiều của nhịp "
               "e_i → e_{i+1}. Đoạn đầu (trước pivot đầu) và đoạn cuối (ứng viên chưa xác nhận) bỏ.",
    "nhan_trend_scanning": "Tại t: hồi quy OLS close[t..t+ℓ] theo thời gian (nến), ℓ ∈ [max(4, L/4), L]; chọn ℓ có "
                           "|t-value| lớn nhất; |t| ≥ 2 → dấu, còn lại 0. Nến không đủ L nến tương lai: không nhãn. "
                           "t-value OLS bị thổi phồng do sai số tự tương quan → nhãn 0 hiếm (báo tỷ lệ).",
    "ranh_gioi_doan": "Đoạn tham chiếu (b, e, d): b = nến cuối của đoạn trước (cực trị với DC), các nến b+1..e mang d. "
                      "Đoạn đầu tiên (không có ranh giới) bỏ.",
    "M3_tre": "k* = nến đầu tiên trong [b, e] mà bộ phát hiện ở Trend d (trạng thái sau nến k*). Trễ = k* − b "
              "(0 = đã đúng chiều từ trước). Không phát hiện trong đoạn = bỏ lỡ. «Trễ kiểm duyệt» = min(trễ, e − b) với "
              "bỏ lỡ tính = e − b (dùng cho đường trễ ↔ lật).",
    "M3_bao_dong_gia": "Lần vào Trend d (trạng thái đổi sang d) ở nến k mà nhãn tham chiếu ở nến k+1 khác d (DC: chiều "
                       "khác; trend-scanning: khác d, kể cả 0). Chỉ tính trong vùng có nhãn.",
    "M3_F1": "Điểm tham chiếu = (b, d) mỗi đoạn có hướng; điểm phát hiện = (k, d) mỗi lần vào Trend d. Ghép cùng chiều, "
             "|Δnến| ≤ dung sai, matcher min_cost_v1 của lab (chia thành phần liên thông); null = dịch vòng chuỗi điểm "
             "phát hiện. Baseline «không đổi»: không có điểm nào → R = F1 = 0.",
    "M4": "Tuổi thọ còn lại = (e − k*) / (e − b) — phần đoạn còn lại sau nến biết (dùng được từ k*+1); bỏ lỡ = 0. "
          "Null = dịch vòng chuỗi chiều của chính bộ phát hiện (giữ độ bền, bỏ căn chỉnh).",
    "M4_range": "Như M4 nhưng cho trạng thái Range trong các đoạn 0 (không xu hướng) của trend-scanning.",
    "M4_giu_chieu": "Bổ sung của khảo sát (không có trong plan): phần đoạn (k*, e] mà trạng thái (của nến trước) vẫn ở "
                    "đúng chiều d, chia (e − b). Khác M4 ở chỗ phạt việc lật ra rồi vào lại; «theo nến» = Σ / Σ độ dài. "
                    "Null = cùng đại lượng trên chuỗi dịch vòng (một phía: tỷ lệ độ dịch cho giá trị ≥ quan sát).",
    "M5": "Kết cục trên (t, t+h]: ER tương lai, (max high − min low)/ATR_t, |close[t+h] − close[t]|/ATR_t, chạm "
          "+1·ATR_t trước −1·ATR_t (cùng nến hoặc không chạm → bỏ). Hiệu = trung bình nhóm A − trung bình nhóm B "
          "TRONG từng tam phân vị ATR_t/close (của chính đoạn), rồi lấy trung bình 3 tầng (bỏ tầng có nhóm < 30 nến). "
          "CI 95% bootstrap khối tuần (1000 lần, seed 7); MDE ≈ 2.8 × SE bootstrap (α 0.05 hai phía, lực 80%). "
          "Shift test: dịch vòng chuỗi trạng thái so với (kết cục, tầng ATR) — các độ dịch đều nhau trong "
          "[s_min, N − s_min], s_min = max(128, độ trễ ACF < 0.05 của chỉ báo trạng thái); p hai phía theo |hiệu|.",
    "M6": "Hiệu M5 của «điểm» đủ (G1–G4) trừ «điểm chỉ G4»; cùng bootstrap ghép cặp, cùng độ dịch.",
    "G1": "trung bình có mặt của order_flow (None → thiếu) và order M15 (đặt 0 khi protected_broken).",
    "G2": "trung bình có trọng số của thứ tự khung lớn chính (H1 ở M15, H4 ở H1) = 1, khung phụ (H4 ở M15) = 1, "
          "dol_side (None → 0) = 1, pd_bias = 0.5 (chỉ trong «điểm»).",
    "G3": "trung bình của 4 thành phần ∈ [0, 1]: sweep cả BSL và SSL trong W nến mà không có run nào; độ rộng dealing "
          "range/ATR trong [a, b]; 1 − |2·range_pos − 1|; PDH và PDL đều chưa bị lấy.",
    "G4": "Kaufman ER n = 32 nến trên close (nhân quả, nối qua khoảng trống). Trong R dùng 1 − F_dev(ER) (F = phân phối "
          "thực nghiệm của ER trên dev chính) để cùng thang với G3 (trọng số đều chỉ có nghĩa khi cùng thang).",
    "diem": "D = trung bình(G1, G2); R = trung bình(G3, 1 − F(ER)). «điểm chỉ G4»: D = ER có dấu, R = 1 − F(ER), "
            "không Breakout, không phản bác ICT. «điểm chỉ ICT»: D như đủ, R = G3. θ_vào, θ_ra, ρ = phân vị dev của |D|, "
            "|D|, R. K2 chặn vào Trend ở «điểm» đủ/ICT (giống «kịch bản»).",
    "khoi_dong": "order M15 = None, hoặc thứ tự khung lớn chính chưa có (chưa ready), hoặc chưa có ER/ATR. Dùng chung "
                 "cho mọi biến thể (kể cả chỉ G4) để M6 so trên cùng tập nến. Baseline: trạng thái warm-up của chúng.",
    "du_lieu_thieu": "Trong G nến gần nhất có ICT_GAP bất thường (thiếu trong phiên, lệch bước) hoặc HTF_BAR_DEGRADED "
                     "của H1/H4. Sau Dữ liệu thiếu / Khởi động máy trạng thái bắt đầu lại (không nhớ regime cũ).",
    "breakout": "Vào (chỉ từ Range đã ≥ N_r nến): close vượt biên ≥ k·ATR[t−1], hoặc high/low xuyên biên ≥ 0.1·ATR[t−1] "
                "(định nghĩa «lấy» của lab) cùng nến có displacement cùng chiều. Biên = dealing range M15 lúc vào Range. "
                "Thất bại: LIQ_SWEEP phía đó có vùng ở biên (mức ≥ biên − 0.5·ATR lúc phá) hoặc close quay lại trong "
                "biên trong m nến → về Range (biên cũ, tuổi Range giữ) nếu K3 còn đúng, không thì Uncertain. Thành công: "
                "LIQ_RUN phía đó có vùng ở biên, hoặc STH/STL mới ngoài biên mà close vẫn ngoài → Trend nếu điều kiện "
                "Trend đúng (không cần c), không thì Uncertain. Close quay lại sau m nến, hoặc hết B nến → Uncertain "
                "«breakout chưa xác nhận».",
    "hysteresis": "Trend: vào khi điều kiện đúng c nến liên tiếp; giữ ≥ H nến trừ phản bác cứng (close vượt mức bảo vệ "
                  "phía d; SHIFT ngược chiều xác nhận ở t; Dữ liệu thiếu). Range: giữ ≥ H nến trừ Breakout, Dữ liệu "
                  "thiếu, close ra ngoài biên ≥ k·ATR (khi chưa đủ N_r). Hết H: giữ khi điều kiện còn đúng (K1 ∧ ¬K2 / "
                  "K3 ở «kịch bản»; |D| ≥ θ_ra cùng dấu ∧ ¬K2 / R ≥ ρ ∧ |D| < θ_ra ở «điểm»).",
    "K3_ER_thap": "ER ≤ phân vị 50% dev (Q4 đồng ý dùng ER).",
    "k1": "Mặc định («cung_chieu»): K1 đúng như bảng plan §4.3 (order_flow = d và H1 = d, hoặc H1 = 0 và H4 = d). Tuỳ "
          "chọn thử trong lưới («khong_nguoc»): order_flow = d và H1, H4 đều không = −d — đúng câu «khung lớn không ngược» "
          "ở phần «Vì sao» của plan; chỉ đo độ bền/trễ, không dùng để chọn theo M5.",
    "range_giu": "Mặc định («dieu_kien»): hết H nến thì Range chỉ giữ khi điều kiện Range (K3 / R ≥ ρ ∧ |D| < θ_ra) còn "
                 "đúng. Tuỳ chọn thử trong lưới («bien», không phải đề xuất của plan): Range giữ tới khi Breakout, close ra "
                 "ngoài biên ≥ k·ATR, hoặc điều kiện vào Trend xuất hiện.",
    "K5": "last_shift_bars ≤ S và từ nến shift chưa có LIQ_RUN cùng chiều hay high (low) vượt high (low) của nến shift.",
    "doi_moi_ngay": "Số lần trạng thái đổi giữa hai nến liên tiếp đều có regime / số ngày giao dịch (ngày kết thúc "
                    "17:00 New York). Đoạn = dãy nến liên tiếp cùng trạng thái, cắt ở trạng thái không phải regime.",
    "giu_nho_H": "Tỷ lệ nến Trend (Range) mà điều kiện giữ đã sai, chỉ còn ở trạng thái đó nhờ giữ tối thiểu H — chi phí "
                 "trực tiếp của H (trạng thái «cũ»), đo vì trễ chuyển gần như không đổi theo H.",
    "khuyu": "Đường trễ ↔ lật: lưới H × c (các tham số khác nháp). Trục x = trung vị «trễ chuyển» so với DC θ = 2 (đoạn "
             "mà bộ phát hiện phải đổi chiều và có đổi trong đoạn; trễ kiểm duyệt bị bão hoà vì đa số đoạn bị bỏ lỡ — đổi "
             "sau lần chạy thử đầu, trước khi chọn), trục y = số lần đổi/ngày. Biên Pareto (cả hai nhỏ), chuẩn hoá [0, 1], "
             "khuỷu = điểm xa dây cung nhất. Chỉ dùng độ bền và trễ — không dùng kết cục M5.",
    "HMM": "hmm_online 3 trạng thái, fit một lần trên 2000 nến đầu của mỗi đoạn (≈ 3 tuần), sau đó chỉ lọc forward. "
           "Trạng thái không mang nghĩa → chỉ M1, M2.",
    "H1": "Cùng định nghĩa, tham số theo NẾN giữ nguyên; khung lớn chính = H4 (không có khung phụ); ngưỡng theo phân vị "
          "của dev H1 01–08/2024 (dataset ds_771a79d4d604), áp nguyên cho H1 2018–2023 gộp từ M15.",
}


# ---------------------------------------------------------------- tiện ích


def rnd(x, d=3):
    if x is None:
        return None
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return x
    if not math.isfinite(xf):
        return None
    return round(xf, d)


def qd(xs, ps=(0.1, 0.25, 0.5, 0.75, 0.9), d=3):
    a = np.asarray(xs, float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return {}
    return {"p%d" % int(round(p * 100)): rnd(np.quantile(a, p), d) for p in ps}


def nmean(cols, w=None):
    """Trung bình có trọng số chỉ trên giá trị hữu hạn; mọi cột thiếu → NaN."""
    X = np.vstack([np.asarray(c, float) for c in cols])
    W = np.ones(len(cols)) if w is None else np.asarray(w, float)
    fin = np.isfinite(X)
    s = np.where(fin, X * W[:, None], 0.0).sum(0)
    c = np.where(fin, W[:, None], 0.0).sum(0)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(c > 0, s / np.where(c > 0, c, 1), np.nan)


def arr(lst, true_val=1.0):
    """Danh sách giá trị timeline (None/bool/số) → mảng float, None → NaN."""
    out = np.full(len(lst), np.nan)
    for i, v in enumerate(lst):
        if v is None:
            continue
        if v is True:
            out[i] = true_val
        elif v is False:
            out[i] = 0.0
        else:
            out[i] = float(v)
    return out


def next_idx(mask):
    n = len(mask)
    idx = np.where(mask, np.arange(n), n)
    return np.minimum.accumulate(idx[::-1])[::-1]


def decor_lag(x, thr=0.05):
    """Độ trễ nhỏ nhất mà ACF của chuỗi < thr (ước lượng qua FFT); để loại các độ dịch nhỏ trong shift test."""
    x = np.asarray(x, float)
    x = x - x.mean()
    n = len(x)
    if n < 10 or not np.any(x):
        return 1
    f = np.fft.rfft(x, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n]
    ac = ac / ac[0]
    below = np.flatnonzero(ac < thr)
    return int(below[0]) if below.size else n


def shift_list(n, s_min, k):
    s_min = int(min(max(1, s_min), n // 4))
    return np.unique(np.linspace(s_min, n - s_min, k).astype(int))


# ---------------------------------------------------------------- dữ liệu


def load(con, spec, allow_test):
    """Nạp một đoạn (nửa mở [start, end)) — từ chối đoạn chạm 2024-09-01 nếu không có --allow-test."""
    start, end = spec["start"], spec["end"]
    if end > TEST_START and not allow_test:
        raise SystemExit("Khoảng %s..%s chạm đoạn kiểm tra (từ %s) — cần --allow-test." % (start, end, TEST_START))
    row = con.execute("select id, name, symbol, timeframe, timestamp_convention, checksum_sha256, is_synthetic "
                      "from datasets where id=?", (spec["ds"],)).fetchone()
    if row is None:
        raise SystemExit("Không tìm thấy dataset %s." % spec["ds"])
    ds = dict(zip(("id", "name", "symbol", "timeframe", "timestamp_convention", "checksum_sha256", "is_synthetic"), row))
    if ds["is_synthetic"]:
        raise SystemExit("Khảo sát chỉ dùng dữ liệu thật.")
    rows = [{"bar_time": datetime.fromisoformat(r[0]), "open": r[1], "high": r[2], "low": r[3], "close": r[4],
             "volume": r[5]}
            for r in con.execute("select bar_time, open, high, low, close, volume from bars where dataset_id=? and "
                                 "bar_time>=? and bar_time<? order by idx", (spec["ds"], start, end))]
    if not rows:
        raise SystemExit("Đoạn %s không có nến." % spec["key"])
    if not allow_test and rows[-1]["bar_time"] >= datetime.fromisoformat(TEST_START + "T00:00:00+00:00"):
        raise SystemExit("Có nến trong đoạn kiểm tra — dừng.")
    ck = rows_checksum(rows)
    tf = ds["timeframe"]
    use = rows
    rep = None
    if spec.get("resample"):
        use, rep = resample_ohlc(rows, tf, spec["resample"], alignment="utc_epoch", gap_policy="emit_available")
        tf = spec["resample"]
    bars = build_bars(use, tf, ds["timestamp_convention"])
    meta = {"khoa": spec["key"], "dataset": ds["id"], "ten": ds["name"], "ma": ds["symbol"],
            "checksum_dataset": ds["checksum_sha256"], "checksum_doan_nguon": ck, "khung_nguon": ds["timeframe"],
            "khung_chay": tf, "tu": start, "den_truoc": end, "so_nen_nguon": len(rows), "so_nen": len(bars),
            "nen_dau": bars[0].bar_time.isoformat(), "nen_cuoi": bars[-1].bar_time.isoformat()}
    if rep is not None:
        meta["gop_khung"] = {"alignment": rep.alignment, "gap_policy": rep.gap_policy,
                             "bucket_thieu_van_phat": rep.buckets_incomplete_emitted}
    return ds, bars, tf, meta


class Base:
    """Một đoạn dữ liệu + một lần chạy ``ict_structure`` (tham số mặc định, lịch theo mã) + các mảng dùng chung."""

    def __init__(self, spec, ds, bars, tf):
        self.key, self.tf, self.symbol = spec["key"], tf, ds["symbol"]
        self.cal = CAL[ds["symbol"]]
        algo = IctStructureAlgorithm(timeframe=tf, session_calendar=self.cal)
        t0 = time.time()
        res = run_algorithm(bars, algo)
        self.t_ict = round(time.time() - t0, 2)
        self.ict_version = algo.version
        self.bars = bars
        N = self.N = len(bars)
        tl = res.timeline
        self.O = np.array([b.open for b in bars])
        self.H = np.array([b.high for b in bars])
        self.L = np.array([b.low for b in bars])
        self.C = np.array([b.close for b in bars])
        self.atr = np.array([np.nan if p["atr"] is None else p["atr"] for p in tl], float)
        self.atrp = np.r_[np.nan, self.atr[:-1]]

        def col(k):
            return [p.get(k) for p in tl]

        self.of, self.od, self.pb = col("order_flow"), col("order"), col("protected_broken")
        self.dhi, self.dlo, self.rpos = col("dealing_hi"), col("dealing_lo"), col("range_pos")
        self.disp, self.lsh, self.lshb = col("displacement"), col("last_shift"), col("last_shift_bars")
        self.h1, self.h4 = col("htf_H1_order"), col("htf_H4_order")
        self.dol, self.pd = col("dol_side"), col("pd_bias")
        self.pdh_t, self.pdl_t = col("pdh_taken"), col("pdl_taken")
        if tf == "M15":
            self.hp, self.hs, self.hp_name, self.hs_name = self.h1, self.h4, "H1", "H4"
        else:
            self.hp, self.hs, self.hp_name, self.hs_name = self.h4, [None] * N, "H4", None
        # sự kiện (theo nến xác nhận)
        kinds = ("LIQ_SWEEP_BSL", "LIQ_SWEEP_SSL", "LIQ_RUN_UP", "LIQ_RUN_DOWN")
        cnt = {k: np.zeros(N, np.int32) for k in kinds}
        sh_up, sh_dn, bad = np.zeros(N, bool), np.zeros(N, bool), np.zeros(N, bool)
        self.run_lv, self.sweep_lv, self.sth, self.stl = {}, {}, {}, {}
        self.n_bad = Counter()
        self.ev_count = Counter()
        side_of = {"LIQ_SWEEP_BSL": 1, "LIQ_SWEEP_SSL": -1, "LIQ_RUN_UP": 1, "LIQ_RUN_DOWN": -1}
        for e in res.events:
            s, t = e.structure_type, e.confirmed_bar_index
            self.ev_count[s] += 1
            if s in cnt:
                cnt[s][t] += 1
                lv = [p["muc"] for p in e.details.get("pools", ())]
                tgt = self.sweep_lv if s.startswith("LIQ_SWEEP") else self.run_lv
                tgt.setdefault((t, side_of[s]), []).extend(lv)
            elif s == "SHIFT_UP":
                sh_up[t] = True
            elif s == "SHIFT_DOWN":
                sh_dn[t] = True
            elif s == "ICT_GAP" and e.details.get("bat_thuong"):
                bad[t] = True
                self.n_bad["khoang_trong_bat_thuong"] += 1
            elif s == "HTF_BAR_DEGRADED" and e.details.get("khung") in ("H1", "H4"):
                bad[t] = True
                self.n_bad["nen_%s_degraded" % e.details.get("khung")] += 1
            elif s == "SWING_HIGH":
                self.sth[t] = max(self.sth.get(t, -math.inf), e.price)
            elif s == "SWING_LOW":
                self.stl[t] = min(self.stl.get(t, math.inf), e.price)
        self.cum = {k: np.cumsum(v) for k, v in cnt.items()}
        self.shift_at = sh_up.astype(int) - sh_dn.astype(int)
        self.bad = bad
        del res
        # thời gian: ngày giao dịch (kết thúc 17:00 NY), tuần ISO của ngày giao dịch, năm
        td = [(b.bar_time.astimezone(NY) + timedelta(hours=7)).date() for b in bars]
        self.n_days = len(set(td))
        wk = [d.isocalendar()[:2] for d in td]
        uniq = sorted(set(wk))
        wmap = {w: i for i, w in enumerate(uniq)}
        self.week = np.array([wmap[w] for w in wk])
        self.nW = len(uniq)
        self.year = np.array([d.year for d in td])
        self.days_by_year = Counter()
        for d in set(td):
            self.days_by_year[d.year] += 1
        # Kaufman ER (nhân quả)
        n = DRAFT["n_er"]
        self.cabs = np.r_[0.0, np.cumsum(np.abs(np.diff(self.C)))]
        self.ER = np.full(N, np.nan)
        self.sER = np.full(N, np.nan)
        num = self.C[n:] - self.C[:-n]
        den = self.cabs[n:] - self.cabs[:-n]
        with np.errstate(invalid="ignore", divide="ignore"):
            self.sER[n:] = np.where(den > 0, num / np.where(den > 0, den, 1), 0.0)
        self.ER = np.abs(self.sER)
        with np.errstate(invalid="ignore", divide="ignore"):
            self.wr = (arr(self.dhi) - arr(self.dlo)) / self.atr
        self.kd = np.array([o is None for o in self.od]) | np.array([h is None for h in self.hp]) | \
            ~np.isfinite(self.ER) | ~np.isfinite(self.atrp)
        self._grp = {}

    # -------------------------------------------- cửa sổ sự kiện
    def win(self, k, W):
        c = self.cum[k]
        out = c.copy()
        out[W:] -= c[:-W]
        return out

    def b2(self, W):
        """Trong (t−W, t]: có LIQ_SWEEP_BSL và LIQ_SWEEP_SSL, không có LIQ_RUN nào (theo nến xác nhận)."""
        return (self.win("LIQ_SWEEP_BSL", W) > 0) & (self.win("LIQ_SWEEP_SSL", W) > 0) & \
            ((self.win("LIQ_RUN_UP", W) + self.win("LIQ_RUN_DOWN", W)) == 0)

    def bad_recent(self, G):
        c = np.cumsum(self.bad)
        out = c.copy()
        out[G:] -= c[:-G]
        return out > 0

    # -------------------------------------------- nhóm bằng chứng
    def groups(self, W, ab, er_sorted, w_pd):
        key = (W, ab, w_pd)
        if key in self._grp:
            return self._grp[key]
        of = arr(self.of)
        od = arr(self.od)
        pbt = np.array([v is True for v in self.pb])
        od_eff = np.where(pbt & np.isfinite(od) & (od != 0), 0.0, od)
        G1 = nmean([of, od_eff])
        dol0 = np.nan_to_num(arr(self.dol), nan=0.0)
        G2 = nmean([arr(self.hp), arr(self.hs), dol0, arr(self.pd)], w=[1, 1, 1, w_pd])
        G2k = nmean([arr(self.hp), arr(self.hs), dol0])            # không pd_bias (để so tương quan)
        b2 = self.b2(W).astype(float)
        with np.errstate(invalid="ignore"):
            wid = np.where(np.isfinite(self.wr), ((self.wr >= ab[0]) & (self.wr <= ab[1])).astype(float), np.nan)
        rp = arr(self.rpos)
        mid = 1.0 - np.abs(2.0 * rp - 1.0)
        ph, pl = arr(self.pdh_t), arr(self.pdl_t)
        pdin = np.where(np.isfinite(ph) & np.isfinite(pl), ((ph == 0) & (pl == 0)).astype(float), np.nan)
        G3 = nmean([b2, wid, mid, pdin])
        F = np.searchsorted(er_sorted, np.nan_to_num(self.ER, nan=0.0), side="right") / len(er_sorted)
        G4r = np.where(np.isfinite(self.ER), 1.0 - F, np.nan)
        out = {"G1": G1, "G2": G2, "G2_khong_pd": G2k, "G3": G3, "G4r": G4r,
               "thanh_phan": {"of": of, "od_eff": od_eff, "hp": arr(self.hp), "hs": arr(self.hs), "dol": dol0,
                              "pd": arr(self.pd), "b2": b2, "wid": wid, "mid": mid, "pdin": pdin}}
        self._grp[key] = out
        return out

    def score(self, kind, P, thr):
        g = self.groups(P["W"], (thr["a"], thr["b"]), thr["er_sorted"], P["w_pd"])
        if kind == "diem":
            return nmean([g["G1"], g["G2"]]), nmean([g["G3"], g["G4r"]])
        if kind == "diem_ict":
            return nmean([g["G1"], g["G2"]]), g["G3"]
        if kind == "diem_g4":
            return self.sER.copy(), g["G4r"]
        raise ValueError(kind)


# ---------------------------------------------------------------- ngưỡng (phân vị dev)


def make_thr(base, P):
    """Ngưỡng theo phân vị của CHÍNH đoạn này (dùng trên dev chính; đoạn khác nhận ngưỡng số đã chốt)."""
    reg = ~base.kd
    wr = base.wr[reg & np.isfinite(base.wr)]
    a, b = (float(v) for v in np.quantile(wr, P["q_wid"]))
    er = base.ER[reg & np.isfinite(base.ER)]
    thr = {"a": a, "b": b, "er_max": float(np.quantile(er, P["q_er_low"])), "er_sorted": np.sort(er), "diem": {}}
    for kind in ("diem", "diem_ict", "diem_g4"):
        D, R = base.score(kind, P, thr)
        m = reg & np.isfinite(D) & np.isfinite(R)
        aD = np.abs(D[m])
        th_in = float(np.quantile(aD, P["q_in"]))
        th_out = float(np.quantile(aD, P["q_out"]))
        if th_out >= th_in:
            lower = np.unique(aD[aD < th_in])
            th_out = float(lower[-1]) if lower.size else 0.0
        rho = float(np.quantile(R[m], P["q_rho"]))
        thr["diem"][kind] = {"theta_vao": th_in, "theta_ra": th_out, "rho": rho}
    return thr


def thr_public(thr):
    return {"a_rong_atr": rnd(thr["a"]), "b_rong_atr": rnd(thr["b"]), "er_thap_max": rnd(thr["er_max"]),
            "so_mau_bang_F_ER": int(len(thr["er_sorted"])),
            "diem": {k: {kk: rnd(vv, 4) for kk, vv in v.items()} for k, v in thr["diem"].items()}}


# ---------------------------------------------------------------- baseline + bằng chứng thô


def code_from_dir(vals):
    st = np.full(len(vals), KD, np.int8)
    for i, v in enumerate(vals):
        if v is None:
            continue
        st[i] = TUP if v == 1 else (TDN if v == -1 else UNC)
    return st


def run_baselines(base, with_hmm=True):
    """Baseline của lab trên đúng đoạn này + bằng chứng thô từ ict_structure. Trả {tên: (st, ghi_chú)}."""
    out, versions, timing = {}, {}, {}
    m = {"UPTREND": TUP, "DOWNTREND": TDN, "RANGE": RNG, "UNKNOWN": UNC}
    for name, gp in (("dc_regime (reset)", "reset"), ("dc_regime (bridge_short 2h)", "bridge_short")):
        alg = DcAtrStructureAlgorithm(timeframe=base.tf, gap_policy=gp)
        t0 = time.time()
        res = run_algorithm(base.bars, alg)
        timing[name] = round(time.time() - t0, 2)
        versions["dc_atr_structure"] = alg.version
        out[name] = np.array([m.get(p["regime"], KD) for p in res.timeline], np.int8)
    alg = IndicatorBaselineAlgorithm()
    t0 = time.time()
    res = run_algorithm(base.bars, alg)
    timing["indicator_baseline"] = round(time.time() - t0, 2)
    versions["indicator_baseline"] = alg.version
    mi = {"up": TUP, "down": TDN, "range": RNG, "uncertain": UNC}
    out["indicator_baseline"] = np.array([mi.get(p.get("class"), KD) for p in res.timeline], np.int8)
    if with_hmm:
        alg = HmmOnlineAlgorithm(**HMM_PARAMS)
        t0 = time.time()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = run_algorithm(base.bars, alg)
        timing["hmm_online"] = round(time.time() - t0, 2)
        versions["hmm_online"] = alg.version
        st = np.full(base.N, KD, np.int8)
        for i, p in enumerate(res.timeline):
            if i >= HMM_PARAMS["train_bars"] and p.get("filtered_state") is not None:
                st[i] = 10 + int(p["filtered_state"])
        out["hmm_online (3 trạng thái)"] = st
    out["order_flow (thô)"] = code_from_dir(base.of)
    out["order M15 (thô)" if base.tf == "M15" else "order %s (thô)" % base.tf] = code_from_dir(base.od)
    if base.tf == "M15":
        out["htf_H1_order (thô)"] = code_from_dir(base.h1)
    out["htf_H4_order (thô)"] = code_from_dir(base.h4)
    return out, versions, timing


# ---------------------------------------------------------------- hai biến thể nháp (nguyên mẫu trong script)


def _breakout_step(bo, t, C, sweep_lv, run_lv, sth, stl, m, Bmax, edge):
    """Một nến khi đang Breakout. Trả (kết cục | None)."""
    d, s0, hi, lo, a0 = bo["d"], bo["s0"], bo["hi"], bo["lo"], bo["a0"]
    age = t - s0
    ct = C[t]
    if d == 1:
        back = ct <= hi
        lv0 = hi - edge * a0
        swept = any(v >= lv0 for v in sweep_lv.get((t, 1), ()))
        ran = any(v >= lv0 for v in run_lv.get((t, 1), ()))
        newx = t in sth and sth[t] > hi and ct > hi
    else:
        back = ct >= lo
        lv0 = lo + edge * a0
        swept = any(v <= lv0 for v in sweep_lv.get((t, -1), ()))
        ran = any(v <= lv0 for v in run_lv.get((t, -1), ()))
        newx = t in stl and stl[t] < lo and ct < lo
    if swept or (back and age <= m):
        return "that_bai_sweep" if swept else "that_bai_dong_lai"
    if back:
        return "dong_lai_sau_m"
    if ran or newx:
        return "thanh_cong"
    if age >= Bmax:
        return "het_B"
    return None


def run_variant(base, P, thr, kind):
    """Nguyên mẫu biến thể nháp (plan §4.2–§4.6) — chạy tuần tự, chỉ đọc thông tin ≤ t.

    ``kind``: ``kich_ban`` (cây K1–K6), ``diem`` (G1–G4), ``diem_ict`` (G1–G3), ``diem_g4`` (chỉ ER)."""
    N = base.N
    C, Hh, Ll = base.C.tolist(), base.H.tolist(), base.L.tolist()
    atrp = base.atrp.tolist()
    of, od, pb, hp, hs, dol = base.of, base.od, base.pb, base.hp, base.hs, base.dol
    disp, lsh, lshb, dhi, dlo = base.disp, base.lsh, base.lshb, base.dhi, base.dlo
    bad = base.bad_recent(P["G"]).tolist()
    kd = base.kd.tolist()
    shift_at = base.shift_at.tolist()
    sweep_lv, run_lv, sth, stl = base.sweep_lv, base.run_lv, base.sth, base.stl
    S, Nr, kk, Bmax, m, Hold, c = P["S"], P["Nr"], P["k"], P["B"], P["m"], P["H"], P["c"]
    pen, edge = P["pen_atr"], P["edge_atr"]
    keep_box = P.get("range_giu") == "bien"
    k1_loose = P.get("k1") == "khong_nguoc"
    ict = kind != "diem_g4"
    if kind == "kich_ban":
        b2 = base.b2(P["W"]).tolist()
        wr = base.wr.tolist()
        ER = base.ER.tolist()
        a_w, b_w, er_max = thr["a"], thr["b"], thr["er_max"]
        cru, crd = base.cum["LIQ_RUN_UP"].tolist(), base.cum["LIQ_RUN_DOWN"].tolist()
    else:
        D, R = base.score(kind, P, thr)
        D, R = D.tolist(), R.tolist()
        th = thr["diem"][kind]
        th_in, th_out, rho = th["theta_vao"], th["theta_ra"], th["rho"]
    st = np.zeros(N, np.int8)
    rs = np.zeros(N, np.int8)
    stale = np.zeros(N, bool)       # nến chỉ còn ở Trend/Range nhờ giữ tối thiểu H (điều kiện giữ đã sai)
    state, hold, cu, cd = UNC, -1, 0, 0
    rng = None
    bo = None
    log = []
    for t in range(N):
        if bad[t] or kd[t]:
            if bo is not None:
                bo["ket_cuc"], bo["nen_ket_thuc"] = "gian_doan", t
                log.append(bo)
            st[t] = DT if bad[t] else KD
            state, hold, cu, cd, rng, bo = UNC, -1, 0, 0, None, None
            continue
        o = od[t]
        pbt = pb[t] is True
        dl = dol[t]
        ap = atrp[t]
        ct = C[t]
        r = 0
        new = None
        # ---- điều kiện của biến thể ở nến t
        if kind == "kich_ban":
            f = of[t] or 0
            hpv, hsv = hp[t], hs[t]
            if k1_loose:                                # «khung lớn không ngược» (lý do ở plan §4.3)
                k1u = f == 1 and hpv != -1 and hsv != -1
                k1d = f == -1 and hpv != 1 and hsv != 1
            else:
                k1u = f == 1 and (hpv == 1 or (hpv == 0 and hsv == 1))
                k1d = f == -1 and (hpv == -1 or (hpv == 0 and hsv == -1))
            k2u_pb, k2d_pb = (o == 1 and pbt), (o == -1 and pbt)
            k2u = k2u_pb or dl == -1
            k2d = k2d_pb or dl == 1
            eu, ed = k1u and not k2u, k1d and not k2d          # điều kiện vào
            su, sd = eu, ed                                     # điều kiện giữ (sau H)
            w = wr[t]
            rc = (o == 0 or f == 0) and b2[t] and (w == w) and a_w <= w <= b_w and ER[t] <= er_max
        else:
            dv, rv = D[t], R[t]
            if dv != dv or rv != rv:
                st[t] = UNC
                rs[t] = 5
                state, hold, cu, cd, rng, bo = UNC, -1, 0, 0, None, None
                continue
            ad = abs(dv)
            sg = (dv > 0) - (dv < 0)
            k2u_pb, k2d_pb = ict and o == 1 and pbt, ict and o == -1 and pbt
            k2u = k2u_pb or (ict and dl == -1)
            k2d = k2d_pb or (ict and dl == 1)
            k1u = sg == 1 and ad >= th_in and rv < rho
            k1d = sg == -1 and ad >= th_in and rv < rho
            eu, ed = k1u and not k2u, k1d and not k2d
            su = sg == 1 and ad >= th_out and not k2u
            sd = sg == -1 and ad >= th_out and not k2d
            rc = rv >= rho and ad < th_out
        cu = cu + 1 if eu else 0
        cd = cd + 1 if ed else 0
        # ---- Breakout đang mở
        if state == BUP or state == BDN:
            oc = _breakout_step(bo, t, C, sweep_lv, run_lv, sth, stl, m, Bmax, edge)
            if oc is None:
                st[t] = state
                continue
            d = bo["d"]
            if oc.startswith("that_bai"):
                if rc:
                    new = RNG
                    rng = [bo["hi"], bo["lo"], bo["rs0"]]
                else:
                    new, r = UNC, 11
            elif oc == "thanh_cong" and (eu if d == 1 else ed):
                new = TUP if d == 1 else TDN
            else:
                new, r = UNC, 7
            bo["ket_cuc"] = oc if not (oc == "thanh_cong" and new == UNC) else "thanh_cong_chua_trend"
            bo["nen_ket_thuc"] = t
            log.append(bo)
            bo = None
            hold = t + Hold if new in (TUP, TDN, RNG) else -1
            state = new
            st[t] = new
            rs[t] = r
            continue
        # ---- Range: Breakout / phản bác / giữ
        if state == RNG:
            hi, lo, s0 = rng
            if ict and hi is not None and lo is not None:
                up_b = (ct - hi >= kk * ap) or (Hh[t] - hi >= pen * ap and disp[t] == "up")
                dn_b = (lo - ct >= kk * ap) or (lo - Ll[t] >= pen * ap and disp[t] == "down")
                if t - s0 >= Nr and up_b != dn_b:
                    d = 1 if up_b else -1
                    bo = {"d": d, "s0": t, "hi": hi, "lo": lo, "a0": ap, "rs0": s0, "tuoi_range": t - s0}
                    state = BUP if d == 1 else BDN
                    st[t] = state
                    continue
                hard = ct > hi + kk * ap or ct < lo - kk * ap
            else:
                hard = False
            if not hard and (t < hold or rc or (keep_box and not (eu or ed))):
                st[t] = RNG
                stale[t] = not (rc or (keep_box and not (eu or ed)))
                continue
            state = UNC
        elif state == TUP or state == TDN:
            d = 1 if state == TUP else -1
            hard = ict and ((o == d and pbt) or shift_at[t] == -d)
            if not hard and (t < hold or (su if d == 1 else sd)):
                st[t] = state
                stale[t] = not (su if d == 1 else sd)
                continue
            state = UNC
        # ---- luật của biến thể
        if eu and cu >= c:
            new = TUP
        elif ed and cd >= c:
            new = TDN
        elif eu or ed:
            new, r = UNC, 6
        elif k1u or k1d:
            new, r = UNC, (1 if (k2u_pb if k1u else k2d_pb) else 2)
        elif rc:
            new = RNG
        elif kind == "kich_ban":
            if (f == 1 and hpv == -1) or (f == -1 and hpv == 1):
                new, r = UNC, 3
            else:
                k5 = False
                lb = lshb[t]
                if lb is not None and lb <= S:
                    d0 = t - lb
                    if lsh[t] == "up":
                        prog = cru[t] - cru[d0] > 0 or (t > d0 and max(Hh[d0 + 1:t + 1]) > Hh[d0])
                    else:
                        prog = crd[t] - crd[d0] > 0 or (t > d0 and min(Ll[d0 + 1:t + 1]) < Ll[d0])
                    k5 = not prog
                new, r = UNC, (4 if k5 else 5)
        else:
            if ad >= th_in and rv >= rho:
                new, r = UNC, 9
            elif ad >= th_out:
                new, r = UNC, 8
            else:
                new, r = UNC, 10
        if new != state:
            if new in (TUP, TDN):
                hold = t + Hold
            elif new == RNG:
                hold = t + Hold
                rng = [dhi[t], dlo[t], t]
            else:
                hold = -1
        state = new
        st[t] = new
        rs[t] = r
    rs[stale] = -1
    return st, rs, log


# ---------------------------------------------------------------- nhãn hậu kiểm (nhìn về sau — chỉ để chấm)


def dc_reference(base, theta):
    det = DcDetector("atr", float(theta), 0.2)
    piv = []
    for i, b in enumerate(base.bars):
        a = base.atr[i]
        p = det.update(b, float(a) if np.isfinite(a) else None)
        if p is not None:
            piv.append((p.extreme_index, 1 if p.kind == "high" else -1))
    segs = [(e0, e1, 1 if k1 == 1 else -1) for (e0, _k0), (e1, k1) in zip(piv, piv[1:])]
    lab = np.full(base.N, np.nan)
    for b, e, d in segs:
        lab[b + 1:e + 1] = d
    return {"ten": "DC θ=%g ATR" % theta, "segs": np.array(segs, int).reshape(-1, 3), "lab": lab,
            "loai": "dc", "tham_so": theta}


def ts_reference(base, L):
    C = base.C
    N = len(C)
    y = C - C.mean()
    cy = np.r_[0.0, np.cumsum(y)]
    cy2 = np.r_[0.0, np.cumsum(y * y)]
    cxy = np.r_[0.0, np.cumsum(np.arange(N) * y)]
    best = np.zeros(N)
    besta = np.full(N, -1.0)
    lmin = max(4, L // 4)
    for ell in range(lmin, L + 1):
        n = ell + 1
        T = np.arange(N - ell)
        Sy = cy[T + n] - cy[T]
        Syy = cy2[T + n] - cy2[T]
        Sxy = (cxy[T + n] - cxy[T]) - T * Sy
        sx = ell * (ell + 1) / 2.0
        sxx = ell * (ell + 1) * (2 * ell + 1) / 6.0
        Sxx_c = sxx - sx * sx / n
        Sxy_c = Sxy - sx * Sy / n
        Syy_c = Syy - Sy * Sy / n
        b = Sxy_c / Sxx_c
        ssr = np.maximum(Syy_c - b * Sxy_c, 1e-12)
        tv = b / np.sqrt(ssr / (n - 2) / Sxx_c)
        tv = np.clip(tv, -1e6, 1e6)
        upd = np.abs(tv) > besta[T]
        besta[T] = np.where(upd, np.abs(tv), besta[T])
        best[T] = np.where(upd, tv, best[T])
    lab = np.where(besta >= TS_TMIN, np.sign(best), 0.0)
    lab[N - L:] = np.nan
    # đoạn = dãy nến cùng nhãn; ranh giới b = nến cuối của đoạn trước
    segs = []
    valid = np.isfinite(lab)
    t = 0
    prev_end = None
    while t < N:
        if not valid[t]:
            prev_end = None
            t += 1
            continue
        s = t
        v = lab[t]
        while t + 1 < N and valid[t + 1] and lab[t + 1] == v:
            t += 1
        if prev_end is not None:
            segs.append((s - 1, t, int(v)))
        prev_end = t
        t += 1
    return {"ten": "trend-scanning L=%d" % L, "segs": np.array(segs, int).reshape(-1, 3), "lab": lab,
            "loai": "ts", "tham_so": L}


def build_refs(base):
    refs = {}
    for th in REF_THETA:
        r = dc_reference(base, th)
        refs[r["ten"]] = r
    for L in REF_L:
        r = ts_reference(base, L)
        refs[r["ten"]] = r
    return refs


def describe_ref(base, ref):
    s = ref["segs"]
    lab = ref["lab"]
    fin = np.isfinite(lab)
    out = {"so_doan": int(len(s))}
    for d, nm in ((1, "tang"), (-1, "giam"), (0, "khong_xu_huong")):
        sel = s[s[:, 2] == d] if len(s) else s
        if len(sel):
            out["doan_" + nm] = {"so": int(len(sel)), "do_dai_nen": qd(sel[:, 1] - sel[:, 0], d=1)}
    out["ty_le_nen"] = {nm: rnd(np.mean(lab[fin] == d)) for d, nm in ((1, "tang"), (-1, "giam"), (0, "khong_xu_huong"))}
    out["nen_co_nhan"] = int(fin.sum())
    return out


# ---------------------------------------------------------------- M1, M2


def dir_of(st):
    d = np.zeros(len(st), np.int8)
    d[st == TUP] = 1
    d[st == TDN] = -1
    return d


def m1(st):
    reg = st >= 0
    n = int(reg.sum())
    out = {"nen_co_regime": n, "khoi_dong_ty_le_moi_nen": rnd(np.mean(st == KD)),
           "du_lieu_thieu_ty_le_moi_nen": rnd(np.mean(st == DT), 4)}
    if n == 0:
        return out
    codes = Counter(st[reg].tolist())
    names = {c: (STATE_NAME[c] if c in STATE_NAME else "hmm_%d" % (c - 10)) for c in codes}
    out["ty_le"] = {names[c]: rnd(v / n) for c, v in sorted(codes.items())}
    return out


def segments(st):
    """Đoạn = dãy nến liên tiếp cùng trạng thái regime; cắt ở trạng thái không phải regime. Trả (đầu, độ dài, mã)."""
    N = len(st)
    reg = st >= 0
    prev = np.r_[-99, st[:-1]]
    prev_reg = np.r_[False, reg[:-1]]
    start = reg & (~prev_reg | (st != prev))
    idx = np.flatnonzero(start)
    bnd = np.flatnonzero(start | ~reg)
    pos = np.searchsorted(bnd, idx, side="right")
    nxt = np.where(pos < len(bnd), bnd[np.minimum(pos, len(bnd) - 1)], N)
    return idx, nxt - idx, st[idx]


def m2(st, n_days, short=4):
    reg = st >= 0
    prev = np.r_[-99, st[:-1]]
    prev_reg = np.r_[False, reg[:-1]]
    changes = int((reg & prev_reg & (st != prev)).sum())
    idx, lens, codes = segments(st)
    out = {"doi_moi_ngay": rnd(changes / max(1, n_days), 2), "so_lan_doi": changes, "so_doan": int(len(lens))}
    if len(lens):
        out.update({"do_dai_trung_vi": rnd(np.median(lens), 1), "iqr": [rnd(np.quantile(lens, 0.25), 1),
                                                                         rnd(np.quantile(lens, 0.75), 1)],
                    "p90": rnd(np.quantile(lens, 0.9), 1), "doan_duoi_%d_nen" % short: rnd(np.mean(lens < short))})
        cls = {"trend": np.isin(codes, (TUP, TDN)), "range": codes == RNG, "uncertain": codes == UNC,
               "breakout": np.isin(codes, (BUP, BDN))}
        per = {}
        for nm, msk in cls.items():
            if msk.sum():
                per[nm] = {"so_doan": int(msk.sum()), "trung_vi": rnd(np.median(lens[msk]), 1),
                           "p90": rnd(np.quantile(lens[msk], 0.9), 1)}
        if per:
            out["theo_lop"] = per
    return out


# ---------------------------------------------------------------- M3, M4


def m4_core(dirv, segs):
    nu, nd = next_idx(dirv == 1), next_idx(dirv == -1)
    b, e, d = segs[:, 0], segs[:, 1], segs[:, 2]
    k = np.where(d == 1, nu[b], nd[b])
    det = k <= e
    L = e - b
    delay_c = np.where(det, k - b, L)
    rem = np.where(det, (e - k) / L, 0.0)
    return det, k, delay_c, rem, L


def held_core(dirv, sd, k, det):
    """Số nến trong (k*, e] mà trạng thái của nến trước vẫn ở đúng chiều d (router «đang ở đúng chiều»)."""
    P1 = np.r_[0, np.cumsum(dirv == 1)]
    P2 = np.r_[0, np.cumsum(dirv == -1)]
    b, e, d = sd[:, 0], sd[:, 1], sd[:, 2]
    kk = np.minimum(k, e)
    h = np.where(d == 1, P1[e] - P1[kk], P2[e] - P2[kk])
    return np.where(det, h, 0)


def tp_greedy(r, e, tol):
    """Ghép tối đa một-một điểm cùng loại với |Δ| ≤ tol (khoảng cùng độ dài → tham lam theo thứ tự là tối ưu)."""
    i = j = tp = 0
    nr, ne = len(r), len(e)
    while i < nr and j < ne:
        if e[j] < r[i] - tol:
            j += 1
        elif e[j] > r[i] + tol:
            i += 1
        else:
            tp += 1
            i += 1
            j += 1
    return tp


def tp_lab(r, e, tol, max_comp=400):
    """Như ``tp_greedy`` nhưng dùng matcher ``min_cost_v1`` của lab trên từng thành phần liên thông."""
    pts = sorted([(int(x), 0) for x in r] + [(int(x), 1) for x in e])
    tp, comps, big = 0, [], 0
    cur = []
    for p in pts:
        if cur and p[0] - cur[-1][0] > tol:
            comps.append(cur)
            cur = []
        cur.append(p)
    if cur:
        comps.append(cur)
    for comp in comps:
        rr = [x for x, k in comp if k == 0]
        ee = [x for x, k in comp if k == 1]
        if not rr or not ee:
            continue
        if len(comp) > max_comp:
            big += 1
            tp += tp_greedy(np.array(rr), np.array(ee), tol)
            continue
        labels = [ReferenceLabel(structure_type="DOI", bar_index=x, price=0.0, seq=i) for i, x in enumerate(rr)]
        events = [{"event_id": str(j), "structure_type": "DOI", "event_bar_index": x, "price": 0.0}
                  for j, x in enumerate(ee)]
        res = match_labels(labels, events, time_tolerance_bars=tol, price_tolerance=0.0,
                           matcher_version=MATCHER_MIN_COST_V1)
        tp += len(res.matches)
    return tp, big


def f1_points(dirv, ref, cov):
    segs = ref["segs"]
    sd = segs[segs[:, 2] != 0]
    prev = np.r_[0, dirv[:-1]]
    ent = np.flatnonzero((dirv != 0) & (prev != dirv))
    ent = ent[(ent >= cov[0]) & (ent <= cov[1])]
    rp = {d: np.sort(sd[sd[:, 2] == d, 0]) for d in (1, -1)}
    ep = {d: ent[dirv[ent] == d] for d in (1, -1)}
    return rp, ep, ent


def prf(tp, n_ref, n_det):
    p = tp / n_det if n_det else None
    r = tp / n_ref if n_ref else None
    f = (2 * p * r / (p + r)) if (p and r) else 0.0
    return p, r, f


def m3m4(dirv, ref, n_days, check_lab=False, null=True, null_f1=True):
    segs = ref["segs"]
    sd = segs[segs[:, 2] != 0]
    N = len(dirv)
    out = {}
    if len(sd) == 0:
        return out
    det, k, delay_c, rem, L = m4_core(dirv, sd)
    already = det & (k == sd[:, 0])
    out["so_doan"] = int(len(sd))
    out["ty_le_phat_hien"] = rnd(det.mean())
    out["ty_le_dung_chieu_tu_truoc"] = rnd(already.mean())
    out["tre_nen (đoạn phát hiện được)"] = qd((k - sd[:, 0])[det], (0.5, 0.9), d=1)
    out["tre_kiem_duyet_trung_vi"] = rnd(np.median(delay_c), 1)
    out["M4_trung_vi"] = rnd(np.median(rem))
    out["M4_trung_binh"] = rnd(rem.mean())
    out["M4_iqr"] = [rnd(np.quantile(rem, 0.25)), rnd(np.quantile(rem, 0.75))]
    out["M4_trung_vi_doan_phat_hien"] = rnd(np.median(rem[det])) if det.any() else None
    rb = np.where(det, sd[:, 1] - k, 0)
    out["nen_con_lai_trung_vi"] = rnd(np.median(rb), 1)
    out["M4_theo_nen"] = rnd(rb.sum() / max(1, L.sum()))
    held = held_core(dirv, sd, k, det)
    out["M4_giu_chieu_trung_vi"] = rnd(np.median(held / L))
    out["M4_giu_chieu_theo_nen"] = rnd(held.sum() / max(1, L.sum()))
    sw = det & (k > sd[:, 0])
    out["tre_chuyen (đoạn phải đổi chiều)"] = dict(qd((k - sd[:, 0])[sw], (0.5, 0.9), d=1), so=int(sw.sum()))
    # báo động giả
    cov = (int(sd[:, 0].min()), int(sd[:, 1].max()))
    prev = np.r_[0, dirv[:-1]]
    ent = np.flatnonzero((dirv != 0) & (prev != dirv))
    ent = ent[(ent >= cov[0]) & (ent < min(cov[1], N - 1))]
    labn = ref["lab"][ent + 1]
    fin = np.isfinite(labn)
    false = (labn[fin] != dirv[ent][fin])
    out["lan_vao_trend"] = int(fin.sum())
    out["bao_dong_gia_ty_le"] = rnd(false.mean()) if fin.any() else None
    out["bao_dong_gia_moi_ngay"] = rnd(false.sum() / max(1, n_days), 2)
    # P/R/F1 có dung sai
    rp, ep, _ = f1_points(dirv, ref, cov)
    n_ref = sum(len(v) for v in rp.values())
    n_det = sum(len(v) for v in ep.values())
    f1 = {}
    for tol in TOLS:
        tp = sum(tp_greedy(rp[d], ep[d], tol) for d in (1, -1))
        p, r, f = prf(tp, n_ref, n_det)
        row = {"P": rnd(p), "R": rnd(r), "F1": rnd(f)}
        if check_lab:
            tl, big = 0, 0
            for d in (1, -1):
                a, bb = tp_lab(rp[d], ep[d], tol)
                tl += a
                big += bb
            row["TP_matcher_lab_khop_tham_lam"] = (tl == tp)
            if big:
                row["thanh_phan_lon_dung_tham_lam"] = big
        if null and null_f1 and n_det:
            fs = []
            for s in shift_list(N, 192, N_SHIFT_F1):
                es = {d: np.sort((ep[d] + s) % N) for d in (1, -1)}
                es = {d: v[(v >= cov[0]) & (v <= cov[1])] for d, v in es.items()}
                nd = sum(len(v) for v in es.values())
                tps = sum(tp_greedy(rp[d], es[d], tol) for d in (1, -1))
                fs.append(prf(tps, n_ref, nd)[2])
            row["F1_null_tb"] = rnd(np.mean(fs))
            row["F1_null_p95"] = rnd(np.quantile(fs, 0.95))
        f1["dung_sai_%d" % tol] = row
    out["F1"] = f1
    if null:
        meds, hw = [], []
        for s in shift_list(N, max(192, decor_lag(dirv != 0)), N_SHIFT_M4):
            dr = np.roll(dirv, s)
            det_s, k_s, _dc, rem_s, _L = m4_core(dr, sd)
            meds.append(np.median(rem_s))
            hw.append(held_core(dr, sd, k_s, det_s).sum() / max(1, L.sum()))
        out["M4_null_dich_vong"] = {"trung_vi_cua_trung_vi": rnd(np.median(meds)), "p95": rnd(np.quantile(meds, 0.95))}
        out["M4_giu_chieu_theo_nen_null"] = {"trung_vi": rnd(np.median(hw)), "p95": rnd(np.quantile(hw, 0.95)),
                                             "p_mot_phia": rnd((1 + np.sum(np.array(hw) >= held.sum() / max(1, L.sum())))
                                                               / (1 + len(hw)), 3)}
    return out


def m4_range(st, ref):
    """M4 cho Range trong các đoạn 0 của trend-scanning."""
    segs = ref["segs"]
    s0 = segs[segs[:, 2] == 0]
    if len(s0) == 0 or not np.any(st == RNG):
        return None
    nk = next_idx(st == RNG)
    b, e = s0[:, 0], s0[:, 1]
    k = nk[b]
    det = k <= e
    rem = np.where(det, (e - k) / (e - b), 0.0)
    return {"so_doan_0": int(len(s0)), "ty_le_phat_hien": rnd(det.mean()), "M4_trung_vi": rnd(np.median(rem)),
            "M4_trung_binh": rnd(rem.mean())}


# ---------------------------------------------------------------- M5, M6


class M5Engine:
    """Kết cục tương lai + hiệu theo trạng thái trong từng tầng ATR; bootstrap khối tuần, shift test."""

    STATS = {
        "trend_vs_khac": ((1, 2), (3, 4, 5), ("fer", "rng", "ar")),
        "range_vs_khac": ((3,), (1, 2, 4, 5), ("fer", "rng", "ar")),
        "huong_tang_vs_giam": ((1,), (2,), ("up",)),
    }

    def __init__(self, base, hs=HS, n_boot=N_BOOT):
        C, H, L, atr = base.C, base.H, base.L, base.atr
        N = self.N = base.N
        self.y = {}
        for h in hs:
            T = np.arange(N - h)
            a = atr[T]
            good = np.isfinite(a) & (a > 0)
            num = np.abs(C[T + h] - C[T])
            den = base.cabs[T + h] - base.cabs[T]
            fer = np.full(N, np.nan)
            ar_ = np.full(N, np.nan)
            rg = np.full(N, np.nan)
            up = np.full(N, np.nan)
            with np.errstate(invalid="ignore", divide="ignore"):
                fer[T] = np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)
                aa = np.where(good, a, np.nan)
                ar_[T] = num / aa
                Hw = sliding_window_view(H[1:], h)
                Lw = sliding_window_view(L[1:], h)
                rg[T] = (Hw.max(1) - Lw.min(1)) / aa
                uh = Hw >= (C[T] + K_FP * aa)[:, None]
                dh = Lw <= (C[T] - K_FP * aa)[:, None]
            fu = np.where(uh.any(1), uh.argmax(1), h)
            fdn = np.where(dh.any(1), dh.argmax(1), h)
            up[T] = np.where(fu < fdn, 1.0, np.where(fdn < fu, 0.0, np.nan))
            up[T] = np.where(good, up[T], np.nan)
            self.y[("fer", h)] = fer
            self.y[("rng", h)] = rg
            self.y[("ar", h)] = ar_
            self.y[("up", h)] = up
        bps = atr / C
        ok = np.isfinite(bps)
        qs = np.quantile(bps[ok], [1 / 3, 2 / 3])
        self.tert = np.where(ok, np.digitize(np.nan_to_num(bps), qs), -1)
        self.tert_cut = [rnd(v * 1e4, 2) for v in qs]
        self.week, self.nW = base.week, base.nW
        rng = np.random.default_rng(SEED)
        self.M = rng.multinomial(self.nW, np.full(self.nW, 1.0 / self.nW), size=n_boot).astype(float)

    @staticmethod
    def groups(st):
        g = np.zeros(len(st), np.int8)
        g[st == TUP] = 1
        g[st == TDN] = 2
        g[st == RNG] = 3
        g[st == UNC] = 4
        g[(st == BUP) | (st == BDN)] = 5
        return g

    def _agg(self, g, y, mask=None):
        valid = np.isfinite(y) & (self.tert >= 0) & (g > 0)
        if mask is not None:
            valid &= mask
        key = self.tert * 6 + g
        S = np.bincount(key[valid], weights=y[valid], minlength=18).reshape(3, 6)
        Cn = np.bincount(key[valid], minlength=18).reshape(3, 6).astype(float)
        return S, Cn

    def _agg_week(self, g, y, mask=None):
        valid = np.isfinite(y) & (self.tert >= 0) & (g > 0)
        if mask is not None:
            valid &= mask
        key = (self.week * 3 + self.tert) * 6 + g
        S = np.bincount(key[valid], weights=y[valid], minlength=self.nW * 18).reshape(self.nW, 18)
        Cn = np.bincount(key[valid], minlength=self.nW * 18).reshape(self.nW, 18).astype(float)
        return S, Cn

    @staticmethod
    def _diff(S, Cn, A, B, ok):
        A, B = list(A), list(B)
        sA, cA = S[..., A].sum(-1), Cn[..., A].sum(-1)
        sB, cB = S[..., B].sum(-1), Cn[..., B].sum(-1)
        with np.errstate(invalid="ignore", divide="ignore"):
            d = sA / cA - sB / cB
        d = np.where(ok, d, np.nan)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return np.nanmean(d, axis=-1)

    def stat(self, g, y, A, B, mask=None):
        S, Cn = self._agg(g, y, mask)
        cA, cB = Cn[:, list(A)].sum(1), Cn[:, list(B)].sum(1)
        ok = (cA >= MIN_N_TERCILE) & (cB >= MIN_N_TERCILE)
        if not ok.any():
            return None, ok, None
        with np.errstate(invalid="ignore", divide="ignore"):
            per = S[:, list(A)].sum(1) / cA - S[:, list(B)].sum(1) / cB
        return float(self._diff(S, Cn, A, B, ok)), ok, [rnd(v, 4) if o else None for v, o in zip(per, ok)]

    def boot(self, g, y, A, B, ok, mask=None):
        S, Cn = self._agg_week(g, y, mask)
        Sb = (self.M @ S).reshape(-1, 3, 6)
        Cb = (self.M @ Cn).reshape(-1, 3, 6)
        return self._diff(Sb, Cb, A, B, ok)

    def s_min(self, sts):
        lags = [128]
        for st in sts:
            lags.append(decor_lag(np.isin(st, (TUP, TDN))))
            if np.any(st == RNG):
                lags.append(decor_lag(st == RNG))
        return max(lags)

    def full(self, st, outcome, h, A, B, n_shift=N_SHIFT, mask=None):
        g = self.groups(st)
        y = self.y[(outcome, h)]
        val, ok, per = self.stat(g, y, A, B, mask)
        if val is None:
            return None
        bs = self.boot(g, y, A, B, ok, mask)
        bs = bs[np.isfinite(bs)]
        se = float(np.std(bs, ddof=1))
        smin = self.s_min([st])
        sh = shift_list(self.N, smin, n_shift)
        nulls = []
        for s in sh:
            v, _o, _p = self.stat(np.roll(g, s), y, A, B, mask)
            if v is not None:
                nulls.append(v)
        nulls = np.array(nulls)
        p = (1 + np.sum(np.abs(nulls) >= abs(val))) / (1 + len(nulls))
        _S, Cn = self._agg(g, y, mask)
        return {"hieu": rnd(val, 4), "ci95": [rnd(np.quantile(bs, 0.025), 4), rnd(np.quantile(bs, 0.975), 4)],
                "se": rnd(se, 4), "mde80": rnd(2.8 * se, 4), "theo_tang_atr": per,
                "n_A": int(Cn[:, list(A)].sum()), "n_B": int(Cn[:, list(B)].sum()),
                "shift": {"p": rnd(p, 3), "null_tb": rnd(nulls.mean(), 4),
                          "null_p2.5_p97.5": [rnd(np.quantile(nulls, 0.025), 4), rnd(np.quantile(nulls, 0.975), 4)],
                          "so_do_dich": int(len(nulls)), "s_min": int(sh[0]) if len(sh) else None},
                "vuot_null": bool(p < 0.05 and (np.quantile(bs, 0.025) > 0 or np.quantile(bs, 0.975) < 0))}

    def paired(self, st1, st2, outcome, h, A, B, n_shift=N_SHIFT):
        g1, g2 = self.groups(st1), self.groups(st2)
        y = self.y[(outcome, h)]
        v1, ok1, _ = self.stat(g1, y, A, B)
        v2, ok2, _ = self.stat(g2, y, A, B)
        if v1 is None or v2 is None:
            return None
        b1 = self.boot(g1, y, A, B, ok1)
        b2 = self.boot(g2, y, A, B, ok2)
        dd = b1 - b2
        dd = dd[np.isfinite(dd)]
        se = float(np.std(dd, ddof=1))
        sh = shift_list(self.N, self.s_min([st1, st2]), n_shift)
        nulls = []
        for s in sh:
            a, _o, _p = self.stat(np.roll(g1, s), y, A, B)
            b, _o, _p = self.stat(np.roll(g2, s), y, A, B)
            if a is not None and b is not None:
                nulls.append(a - b)
        nulls = np.array(nulls)
        delta = v1 - v2
        p = (1 + np.sum(np.abs(nulls) >= abs(delta))) / (1 + len(nulls))
        return {"hieu_1": rnd(v1, 4), "hieu_2": rnd(v2, 4), "chenh": rnd(delta, 4),
                "ci95": [rnd(np.quantile(dd, 0.025), 4), rnd(np.quantile(dd, 0.975), 4)], "se": rnd(se, 4),
                "mde80": rnd(2.8 * se, 4), "shift_p": rnd(p, 3),
                "vuot_null": bool(p < 0.05 and (np.quantile(dd, 0.025) > 0 or np.quantile(dd, 0.975) < 0))}

    def describe(self, st, h):
        """Trung bình kết cục theo trạng thái × tầng ATR (mô tả)."""
        g = self.groups(st)
        out = {}
        names = {1: "trend_tang", 2: "trend_giam", 3: "range", 4: "uncertain", 5: "breakout"}
        for oc in ("fer", "rng", "ar", "up"):
            S, Cn = self._agg(g, self.y[(oc, h)])
            with np.errstate(invalid="ignore", divide="ignore"):
                mean = S / Cn
            out[oc] = {names[k]: [rnd(mean[t, k], 3) if Cn[t, k] >= MIN_N_TERCILE else None for t in range(3)]
                       for k in names if Cn[:, k].sum() > 0}
        S, Cn = self._agg(g, self.y[("fer", h)])
        out["n"] = {names[k]: [int(Cn[t, k]) for t in range(3)] for k in names if Cn[:, k].sum() > 0}
        return out


def m5_block(eng, dets, hs=HS, n_shift=N_SHIFT):
    out = {}
    for name, st in dets.items():
        row = {}
        for h in hs:
            hr = {}
            for sname, (A, B, ocs) in M5Engine.STATS.items():
                if sname == "range_vs_khac" and np.mean(st[st >= 0] == RNG) < 0.01:
                    continue
                for oc in ocs:
                    r = eng.full(st, oc, h, A, B, n_shift=n_shift)
                    if r is not None:
                        hr["%s · %s" % (sname, oc)] = r
            row["h=%d" % h] = hr
        out[name] = row
    return out


# ---------------------------------------------------------------- G1–G4: phân phối, tương quan


def spearman_ci(x, y, week, nW, rng, n_boot=200):
    ok = np.isfinite(x) & np.isfinite(y)
    rho = spearmanr(x[ok], y[ok]).statistic
    idx = [np.flatnonzero(ok & (week == w)) for w in range(nW)]
    bs = []
    for _ in range(n_boot):
        ws = rng.integers(0, nW, nW)
        ii = np.concatenate([idx[w] for w in ws])
        if len(ii) > 10:
            bs.append(spearmanr(x[ii], y[ii]).statistic)
    return {"rho": rnd(rho), "ci95": [rnd(np.nanquantile(bs, 0.025)), rnd(np.nanquantile(bs, 0.975))],
            "n": int(ok.sum())}


def evidence_section(base, P, thr, with_ci=True):
    g = base.groups(P["W"], (thr["a"], thr["b"]), thr["er_sorted"], P["w_pd"])
    reg = ~base.kd
    v = {"G1": g["G1"], "G2": g["G2"], "G3": g["G3"], "G4 (ER)": base.ER, "ER có dấu": base.sER,
         "|G1|": np.abs(g["G1"]), "|G2|": np.abs(g["G2"]), "G2 không pd_bias": g["G2_khong_pd"]}
    v = {k: np.where(reg, x, np.nan) for k, x in v.items()}
    dist = {}
    for k in ("G1", "G2", "G3", "G4 (ER)"):
        x = v[k]
        fin = np.isfinite(x)
        vals = Counter(np.round(x[fin], 2).tolist())
        dist[k] = {"co_gia_tri_ty_le_moi_nen": rnd(fin.mean()), "phan_vi": qd(x),
                   "trung_binh": rnd(np.nanmean(x)), "gia_tri_hay_gap": {str(a): rnd(b / fin.sum())
                                                                         for a, b in vals.most_common(8)}}
        if k in ("G1", "G2"):
            dist[k]["ty_le_khac_0"] = rnd(np.mean(x[fin] != 0))
    comp = {k: np.where(reg, x, np.nan) for k, x in g["thanh_phan"].items()}
    dist["thanh_phan_ty_le_co_gia_tri"] = {k: rnd(np.mean(np.isfinite(x))) for k, x in comp.items()}
    dist["thanh_phan_trung_binh"] = {k: rnd(np.nanmean(x)) for k, x in comp.items()}
    pairs = [("G1", "G2"), ("G1", "ER có dấu"), ("G2", "ER có dấu"), ("G3", "G4 (ER)"), ("|G1|", "G3"),
             ("|G2|", "G3"), ("|G1|", "G4 (ER)"), ("|G2|", "G4 (ER)"), ("|G1|", "|G2|"), ("G2", "G2 không pd_bias")]
    rng = np.random.default_rng(SEED)
    corr = {}
    for a, b in pairs:
        if with_ci:
            corr["%s ~ %s" % (a, b)] = spearman_ci(v[a], v[b], base.week, base.nW, rng)
        else:
            ok = np.isfinite(v[a]) & np.isfinite(v[b])
            corr["%s ~ %s" % (a, b)] = {"rho": rnd(spearmanr(v[a][ok], v[b][ok]).statistic), "n": int(ok.sum())}
    cpairs = [("of", "od_eff"), ("hp", "hs"), ("hp", "dol"), ("hp", "pd"), ("dol", "pd"), ("of", "hp"),
              ("of", "dol"), ("b2", "wid"), ("b2", "mid"), ("wid", "mid"), ("mid", "pdin")]
    cc = {}
    for a, b in cpairs:
        x, y = comp[a], comp[b]
        ok = np.isfinite(x) & np.isfinite(y)
        if ok.sum() > 100 and np.std(x[ok]) > 0 and np.std(y[ok]) > 0:
            cc["%s ~ %s" % (a, b)] = rnd(spearmanr(x[ok], y[ok]).statistic)
    return {"phan_phoi": dist, "tuong_quan_spearman": corr, "tuong_quan_thanh_phan": cc}


# ---------------------------------------------------------------- lưới tham số + đường trễ ↔ lật


def summarize_variant(base, refs, st, rs, log, n_days, full=False):
    out = {"M1": m1(st), "M2": m2(st, n_days)}
    reg = st >= 0
    tr = np.isin(st, (TUP, TDN, RNG))
    if tr.any():
        out["ty_le_giu_nho_H"] = {"trend": rnd(np.mean(rs[np.isin(st, (TUP, TDN))] == -1)) if np.isin(st, (TUP, TDN)).any() else None,
                                  "range": rnd(np.mean(rs[st == RNG] == -1)) if (st == RNG).any() else None}
    unc = (st == UNC) & reg
    if unc.any():
        cnt = Counter(rs[unc].tolist())
        out["ly_do_uncertain"] = {REASONS[k]: rnd(v / unc.sum()) for k, v in sorted(cnt.items())}
    oc = Counter(b["ket_cuc"] for b in log)
    nb = len(log)
    out["breakout"] = {"so": nb, "moi_ngay": rnd(nb / max(1, n_days), 3), "ket_cuc": dict(oc),
                       "ty_le_that_bai": rnd(sum(v for k, v in oc.items() if k.startswith("that_bai")) / nb) if nb else None}
    dirv = dir_of(st)
    m4 = {}
    for rn, ref in refs.items():
        sd = ref["segs"][ref["segs"][:, 2] != 0]
        det, k, delay_c, rem, L = m4_core(dirv, sd)
        sw = det & (k > sd[:, 0])
        m4[rn] = {"M4_trung_vi": rnd(np.median(rem)), "M4_theo_nen": rnd(np.where(det, sd[:, 1] - k, 0).sum() / L.sum()),
                  "M4_giu_chieu_theo_nen": rnd(held_core(dirv, sd, k, det).sum() / L.sum()),
                  "tre_kiem_duyet_trung_vi": rnd(np.median(delay_c), 1),
                  "tre_chuyen_trung_vi": rnd(np.median((k - sd[:, 0])[sw]), 1) if sw.any() else None,
                  "ty_le_phat_hien": rnd(det.mean())}
    out["M3_M4_gon"] = m4
    return out


def knee(points):
    """points: [(x, y, idx)] — biên Pareto (x nhỏ, y nhỏ) rồi điểm xa dây cung nhất sau chuẩn hoá."""
    pts = sorted(p for p in points if p[0] is not None and p[1] is not None)
    front, best = [], math.inf
    for x, y, i in pts:
        if y < best:
            front.append((x, y, i))
            best = y
    if len(front) <= 2:
        return front[0][2] if front else None, [f[2] for f in front]
    xs = np.array([f[0] for f in front], float)
    ys = np.array([f[1] for f in front], float)
    xn = (xs - xs.min()) / max(1e-12, xs.max() - xs.min())
    yn = (ys - ys.min()) / max(1e-12, ys.max() - ys.min())
    x0, y0, x1, y1 = xn[0], yn[0], xn[-1], yn[-1]
    dist = np.abs((y1 - y0) * xn - (x1 - x0) * yn + x1 * y0 - y1 * x0) / math.hypot(y1 - y0, x1 - x0)
    return front[int(np.argmax(dist))][2], [f[2] for f in front]


def grid_section(base, refs, thr):
    configs = []
    for kind in ("kich_ban", "diem"):
        for H in (1, 4, 8, 16, 32, 64):
            for c in (1, 2, 4):
                configs.append((kind, "H×c", {"H": H, "c": c}))
    for kind in ("kich_ban", "diem"):
        for k_, vals in (("W", (24, 96)), ("S", (2, 8)), ("Nr", (8, 32)), ("k", (0.1, 0.5)), ("B", (6, 24)),
                         ("m", (2, 8))):
            if kind == "diem" and k_ == "S":
                continue
            for v in vals:
                configs.append((kind, "mot_tham_so", {k_: v}))
        if kind == "diem":
            for qi, qo in ((0.6, 0.4), (0.8, 0.6), (0.9, 0.7)):
                configs.append((kind, "nguong", {"q_in": qi, "q_out": qo}))
            for qr in (0.7, 0.9):
                configs.append((kind, "nguong", {"q_rho": qr}))
        for nr in (8, 16):
            configs.append((kind, "range_giu_bien", {"range_giu": "bien", "Nr": nr}))
        if kind == "kich_ban":
            configs.append((kind, "k1_khong_nguoc", {"k1": "khong_nguoc"}))
            configs.append((kind, "k1_khong_nguoc", {"k1": "khong_nguoc", "H": 16}))
    rows = []
    for kind, group, ch in configs:
        P = dict(DRAFT)
        P.update(ch)
        th = thr
        if any(k in ch for k in ("W", "q_in", "q_out", "q_rho")):
            th = make_thr(base, P)
            th["a"], th["b"], th["er_max"], th["er_sorted"] = thr["a"], thr["b"], thr["er_max"], thr["er_sorted"]
        st, rs, log = run_variant(base, P, th, kind)
        s = summarize_variant(base, refs, st, rs, log, base.n_days)
        rows.append({"bien_the": kind, "nhom": group, "doi": ch, "ket_qua": s,
                     "nguong_diem": thr_public(th)["diem"].get(kind) if kind != "kich_ban" else None})
    curve = {}
    for kind in ("kich_ban", "diem"):
        pts = []
        for i, r in enumerate(rows):
            if r["bien_the"] == kind and r["nhom"] == "H×c":
                x = r["ket_qua"]["M3_M4_gon"]["DC θ=2 ATR"]["tre_chuyen_trung_vi"]
                y = r["ket_qua"]["M2"]["doi_moi_ngay"]
                pts.append((x, y, i))
        ki, front = knee(pts)
        g = lambda i, rn, kk: rows[i]["ket_qua"]["M3_M4_gon"][rn][kk]  # noqa: E731
        curve[kind] = {"truc": "x = trung vị trễ chuyển so với DC θ=2 (đoạn phải đổi chiều, phát hiện được); "
                               "y = số lần đổi / ngày giao dịch",
                       "diem": [{"H": rows[i]["doi"]["H"], "c": rows[i]["doi"]["c"], "tre_chuyen_DC2": x, "doi_moi_ngay": y,
                                 "phat_hien_DC2": g(i, "DC θ=2 ATR", "ty_le_phat_hien"),
                                 "tre_chuyen_DC4": g(i, "DC θ=4 ATR", "tre_chuyen_trung_vi"),
                                 "phat_hien_DC4": g(i, "DC θ=4 ATR", "ty_le_phat_hien"),
                                 "M4_DC4": g(i, "DC θ=4 ATR", "M4_trung_vi"), "M4_theo_nen_DC4": g(i, "DC θ=4 ATR", "M4_theo_nen"),
                                 "M4_TS64": g(i, "trend-scanning L=64", "M4_trung_vi"),
                                 "ty_le_range": rows[i]["ket_qua"]["M1"]["ty_le"].get("range"),
                                 "giu_nho_H": rows[i]["ket_qua"].get("ty_le_giu_nho_H"),
                                 "doan_duoi_4": rows[i]["ket_qua"]["M2"].get("doan_duoi_4_nen"),
                                 "ty_le_uncertain": rows[i]["ket_qua"]["M1"]["ty_le"].get("uncertain")}
                                for x, y, i in pts],
                       "bien_pareto": [rows[i]["doi"] for i in front], "khuyu": rows[ki]["doi"] if ki is not None else None}
    return rows, curve


# ---------------------------------------------------------------- theo năm (dev mở rộng)


def per_year(base, dets, refs, eng):
    years = sorted(set(base.year.tolist()))
    out = {}
    for y in years:
        ym = base.year == y
        row = {}
        for name, st in dets.items():
            s = st.copy()
            s[~ym] = KD
            r = {"M1": m1(s)["ty_le"] if (s >= 0).any() else None,
                 "doi_moi_ngay": m2(s, base.days_by_year[y])["doi_moi_ngay"]}
            if not (st >= 10).any():
                dirv = dir_of(st)
                m4 = {}
                for rn, ref in refs.items():
                    sd = ref["segs"][ref["segs"][:, 2] != 0]
                    sel = sd[ym[sd[:, 0]]]
                    if len(sel):
                        det_, k_, _d, rem_, L_ = m4_core(dirv, sel)
                        m4[rn] = rnd(np.median(rem_))
                        m4[rn + " · giữ chiều theo nến"] = rnd(held_core(dirv, sel, k_, det_).sum() / max(1, L_.sum()))
                r["M4_trung_vi"] = m4
                mk = {}
                for sname, oc in (("trend_vs_khac", "fer"), ("huong_tang_vs_giam", "up"), ("range_vs_khac", "fer")):
                    A, B, _ = M5Engine.STATS[sname]
                    if sname == "range_vs_khac" and np.mean(st[st >= 0] == RNG) < 0.01:
                        continue
                    v, _ok, _p = eng.stat(M5Engine.groups(st), eng.y[(oc, 16)], A, B, mask=ym)
                    mk["%s · %s · h=16" % (sname, oc)] = rnd(v, 4)
                r["M5"] = mk
            row[name] = r
        out[str(y)] = row
    return out


# ---------------------------------------------------------------- tự kiểm nhân quả (biến thể nháp)


def causality_check(spec, ds, bars, tf, base, P, thr, cuts=(4000, 9000, 13000)):
    """Chạy lại ict_structure + biến thể trên prefix [0, cut) → phải trùng chuỗi trạng thái của lần chạy đủ; sửa giá
    mọi nến từ cut → trạng thái trước cut không đổi. Ngưỡng là tham số cố định (không tính lại trên prefix)."""
    from dataclasses import replace
    kinds = ("kich_ban", "diem", "diem_ict", "diem_g4")
    full = {k: run_variant(base, P, thr, k)[0] for k in kinds}
    out = {}
    for cut in cuts:
        if cut >= base.N:
            continue
        bp = Base(spec, ds, bars[:cut], tf)
        row = {k: int((run_variant(bp, P, thr, k)[0] != full[k][:cut]).sum()) for k in kinds}
        mod = list(bars[:cut]) + [replace(b, open=b.open * 1.01, high=b.high * 1.01, low=b.low * 1.01, close=b.close * 1.01)
                                  for b in bars[cut:]]
        bm = Base(spec, ds, mod, tf)
        row.update({k + " · sửa đuôi": int((run_variant(bm, P, thr, k)[0][:cut] != full[k][:cut]).sum()) for k in kinds})
        out["cat_%d" % cut] = row
    out["ghi_chu"] = "Số nến khác (phải = 0): prefix vs chạy đủ; và trạng thái trước điểm cắt khi sửa giá mọi nến sau đó."
    return out


# ---------------------------------------------------------------- chạy


def run_dataset(con, spec, args, P, thr_fixed=None, full=True, with_hmm=True, n_shift=N_SHIFT):
    t0 = time.time()
    ds, bars, tf, meta = load(con, spec, args.allow_test)
    base = Base(spec, ds, bars, tf)
    meta.update({"so_ngay_giao_dich": base.n_days, "so_tuan": base.nW, "lich_phien": base.cal,
                 "thoi_gian_ict_s": base.t_ict, "ict_structure": base.ict_version,
                 "su_kien_bat_thuong": dict(base.n_bad)})
    thr = thr_fixed if thr_fixed is not None else make_thr(base, P)
    refs = build_refs(base)
    dets, versions, timing = run_baselines(base, with_hmm=with_hmm)
    meta["phien_ban_baseline"] = versions
    meta["thoi_gian_baseline_s"] = timing
    var_logs = {}
    names = {"kich_ban": "«kịch bản» nháp", "diem": "«điểm» nháp (G1–G4)", "diem_g4": "«điểm» chỉ G4 (ER)",
             "diem_ict": "«điểm» chỉ ICT (G1–G3)"}
    tv = time.time()
    for kind in ("kich_ban", "diem", "diem_ict", "diem_g4"):
        st, rs, log = run_variant(base, P, thr, kind)
        dets[names[kind]] = st
        var_logs[names[kind]] = (rs, log)
    meta["thoi_gian_bien_the_s"] = round(time.time() - tv, 2)
    out = {"meta": meta, "nguong": thr_public(thr),
           "nhan_hau_kiem": {rn: describe_ref(base, r) for rn, r in refs.items()}}
    # M1, M2
    mm = {}
    for name, st in dets.items():
        row = {"M1": m1(st), "M2": m2(st, base.n_days)}
        if name in var_logs:
            s = summarize_variant(base, refs, st, var_logs[name][0], var_logs[name][1], base.n_days)
            row["ly_do_uncertain"] = s.get("ly_do_uncertain")
            row["breakout"] = s["breakout"]
        mm[name] = row
    mm["«không đổi» (một trạng thái)"] = {"M2": {"doi_moi_ngay": 0.0, "so_doan": 1}}
    out["M1_M2"] = mm
    # M3, M4
    tm = time.time()
    m34 = {}
    dir_dets = {k: v for k, v in dets.items() if not (v >= 10).any()}
    consts = {"«không đổi» (luôn Uncertain)": np.zeros(base.N, np.int8),
              "«luôn tăng» (+1)": np.full(base.N, TUP, np.int8)}
    for rn, ref in refs.items():
        row = {}
        for name, st in list(dir_dets.items()) + list(consts.items()):
            row[name] = m3m4(dir_of(st), ref, base.n_days, check_lab=(full and args.check_lab),
                             null=(name not in consts), null_f1=full)
        m34[rn] = row
    out["M3_M4"] = m34
    rr = {}
    for rn, ref in refs.items():
        if ref["loai"] != "ts":
            continue
        rr[rn] = {name: m4_range(st, ref) for name, st in dir_dets.items() if np.any(st == RNG)}
    out["M4_range"] = rr
    out["meta"]["thoi_gian_M3_M4_s"] = round(time.time() - tm, 1)
    if full:
        out["kiem_tra_nhan_qua"] = causality_check(spec, ds, bars, tf, base, P, thr)
    out["_base"] = base
    out["_dets"] = dets
    out["_refs"] = refs
    out["_thr"] = thr
    out["meta"]["thoi_gian_tong_s"] = round(time.time() - t0, 1)
    return out


def gate(m34, exclude=("«không đổi» (luôn Uncertain)", "«luôn tăng» (+1)")):
    out = {}
    for rn, row in m34.items():
        vals = {k: v.get("M4_trung_vi") for k, v in row.items() if k not in exclude and v}
        passing = sorted([k for k, v in vals.items() if v is not None and v >= 0.25])
        best = max(vals.items(), key=lambda kv: -1 if kv[1] is None else kv[1]) if vals else (None, None)
        out[rn] = {"bo_phat_hien_dat_0.25": {k: {"M4_trung_vi": row[k]["M4_trung_vi"],
                                                  "M4_null_dich_vong": row[k].get("M4_null_dich_vong"),
                                                  "ty_le_phat_hien": row[k]["ty_le_phat_hien"],
                                                  "M4_theo_nen": row[k].get("M4_theo_nen"),
                                                  "M4_giu_chieu_theo_nen": row[k].get("M4_giu_chieu_theo_nen"),
                                                  "M4_giu_chieu_theo_nen_null": row[k].get("M4_giu_chieu_theo_nen_null")}
                                              for k in passing},
                   "cao_nhat": {"ten": best[0], "M4_trung_vi": best[1]}, "dat": bool(passing)}
    return out


def strip(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=os.path.join(ROOT, "data", "lab.sqlite"))
    ap.add_argument("--json", default="")
    ap.add_argument("--allow-test", action="store_true")
    ap.add_argument("--quick", action="store_true", help="chỉ dev chính (bỏ dev mở rộng, H1) — để thử")
    ap.add_argument("--no-check-lab", dest="check_lab", action="store_false",
                    help="không kiểm TP của matcher lab = ghép tham lam")
    args = ap.parse_args()
    t_all = time.time()
    con = sqlite3.connect("file:%s?mode=ro" % args.db.replace("\\", "/"), uri=True)
    P = dict(DRAFT)
    out = {"meta": {"phien_ban": SURVEY_VERSION,
                    "script_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
                    "python": platform.python_version(), "numpy": np.__version__,
                    "doan_kiem_tra_tu": TEST_START, "seed": SEED, "tham_so_nhap": P,
                    "nhan_hau_kiem": {"dc_theta_atr": list(REF_THETA), "ts_L": list(REF_L), "ts_t_min": TS_TMIN},
                    "M5": {"h": list(HS), "k_cham": K_FP, "n_boot": N_BOOT, "n_shift": N_SHIFT,
                           "min_nen_moi_tang": MIN_N_TERCILE},
                    "M3": {"dung_sai_nen": list(TOLS), "n_shift_F1": N_SHIFT_F1, "n_shift_M4": N_SHIFT_M4},
                    "hmm": HMM_PARAMS, "tao_luc": datetime.now(timezone.utc).isoformat(timespec="seconds")},
           "dinh_nghia": DINH_NGHIA}
    # ------------------------------------------------ 1. dev chính
    print("== dev chính", DEV_MAIN["key"])
    sys.stdout.flush()
    main_r = run_dataset(con, DEV_MAIN, args, P)
    base, dets, refs, thr = main_r["_base"], main_r["_dets"], main_r["_refs"], main_r["_thr"]
    out["dev_chinh"] = strip(main_r)
    out["cong_M15"] = gate(main_r["M3_M4"])
    print("   M1/M2/M3/M4 xong (%.1f s)" % (time.time() - t_all))
    sys.stdout.flush()
    # G1–G4
    t1 = time.time()
    out["nhom_bang_chung"] = evidence_section(base, P, thr)
    out["meta"]["thoi_gian_nhom_bang_chung_s"] = round(time.time() - t1, 1)
    # lưới + đường trễ ↔ lật
    t1 = time.time()
    rows, curve = grid_section(base, refs, thr)
    out["luoi_tham_so"] = {"so_cau_hinh": len(rows) + 4, "cau_hinh": rows, "duong_tre_lat": curve}
    out["meta"]["thoi_gian_luoi_s"] = round(time.time() - t1, 1)
    print("   lưới %d cấu hình xong (%.1f s)" % (len(rows), time.time() - t1))
    sys.stdout.flush()
    # M5, M6
    t1 = time.time()
    eng = M5Engine(base)
    m5d = {k: v for k, v in dets.items() if not (v >= 10).any()}
    out["M5"] = {"tam_phan_vi_atr_bps": eng.tert_cut, "ket_qua": m5_block(eng, m5d),
                 "mo_ta_h16": {k: eng.describe(v, 16) for k, v in m5d.items()
                               if k.startswith("«") or k.startswith("order_flow")}}
    full, g4, ictv = dets["«điểm» nháp (G1–G4)"], dets["«điểm» chỉ G4 (ER)"], dets["«điểm» chỉ ICT (G1–G3)"]
    kb = dets["«kịch bản» nháp"]
    m6 = {}
    for lab_, s1, s2 in (("điểm đủ − chỉ G4", full, g4), ("điểm chỉ ICT − chỉ G4", ictv, g4),
                         ("điểm đủ − chỉ ICT", full, ictv), ("kịch bản − chỉ G4", kb, g4)):
        row = {}
        for h in HS:
            for sname, (A, B, ocs) in M5Engine.STATS.items():
                for oc in ocs:
                    r = eng.paired(s1, s2, oc, h, A, B)
                    if r is not None:
                        row["h=%d · %s · %s" % (h, sname, oc)] = r
        m6[lab_] = row
    out["M6"] = m6
    out["meta"]["thoi_gian_M5_M6_s"] = round(time.time() - t1, 1)
    print("   M5/M6 xong (%.1f s)" % (time.time() - t1))
    sys.stdout.flush()
    if not args.quick:
        # ------------------------------------------------ 2. dev mở rộng
        ext = {}
        for spec in DEV_EXT:
            t1 = time.time()
            print("== dev mở rộng", spec["key"])
            sys.stdout.flush()
            r = run_dataset(con, spec, args, P, thr_fixed=thr, full=False, with_hmm=True)
            b2_, d2_, f2_ = r["_base"], r["_dets"], r["_refs"]
            e2 = M5Engine(b2_)
            m5d2 = {k: v for k, v in d2_.items() if not (v >= 10).any()}
            key_stats = {}
            for name, st in m5d2.items():
                row = {}
                for sname, oc in (("trend_vs_khac", "fer"), ("trend_vs_khac", "rng"), ("huong_tang_vs_giam", "up"),
                                  ("range_vs_khac", "fer")):
                    if sname == "range_vs_khac" and np.mean(st[st >= 0] == RNG) < 0.01:
                        continue
                    A, B, _ = M5Engine.STATS[sname]
                    res = e2.full(st, oc, 16, A, B, n_shift=N_SHIFT_EXT)
                    if res is not None:
                        row["h=16 · %s · %s" % (sname, oc)] = res
                key_stats[name] = row
            m6x = {}
            for lab_, a_, b_ in (("điểm đủ − chỉ G4", "«điểm» nháp (G1–G4)", "«điểm» chỉ G4 (ER)"),
                                 ("điểm chỉ ICT − chỉ G4", "«điểm» chỉ ICT (G1–G3)", "«điểm» chỉ G4 (ER)"),
                                 ("kịch bản − chỉ G4", "«kịch bản» nháp", "«điểm» chỉ G4 (ER)")):
                row = {}
                for sname, oc in (("trend_vs_khac", "fer"), ("huong_tang_vs_giam", "up"), ("range_vs_khac", "fer")):
                    A, B, _ = M5Engine.STATS[sname]
                    res = e2.paired(d2_[a_], d2_[b_], oc, 16, A, B, n_shift=N_SHIFT_EXT)
                    if res is not None:
                        row["h=16 · %s · %s" % (sname, oc)] = res
                m6x[lab_] = row
            rs_ = strip(r)
            rs_["M5_chinh"] = key_stats
            rs_["M6"] = m6x
            rs_["theo_nam"] = per_year(b2_, d2_, f2_, e2)
            rs_["nhom_bang_chung"] = evidence_section(b2_, P, thr, with_ci=False)
            rs_["cong"] = gate(r["M3_M4"])
            rs_["meta"]["thoi_gian_tong_s"] = round(time.time() - t1, 1)
            ext[spec["key"]] = rs_
            print("   xong (%.1f s)" % (time.time() - t1))
            sys.stdout.flush()
            del r, b2_, d2_, f2_, e2
        out["dev_mo_rong"] = ext
        # ------------------------------------------------ 3. H1 (cổng)
        h1o = {}
        thr_h1 = None
        for spec in H1_SETS:
            t1 = time.time()
            print("== H1", spec["key"])
            sys.stdout.flush()
            r = run_dataset(con, spec, args, P, thr_fixed=thr_h1, full=False, with_hmm=False)
            if thr_h1 is None:
                thr_h1 = r["_thr"]
            rs_ = strip(r)
            rs_["cong"] = gate(r["M3_M4"])
            rs_["meta"]["thoi_gian_tong_s"] = round(time.time() - t1, 1)
            h1o[spec["key"]] = rs_
            print("   xong (%.1f s)" % (time.time() - t1))
            sys.stdout.flush()
            del r
        out["H1"] = h1o
    out["meta"]["thoi_gian_chay_s"] = round(time.time() - t_all, 1)
    text = json.dumps(out, ensure_ascii=False, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print("Đã ghi", args.json)
    print("Thời gian chạy: %.1f s" % (time.time() - t_all))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
