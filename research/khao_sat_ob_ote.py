"""Khảo sát Order Block / OTE (plan_ket_hop_ict_indicator.md §3.4, lộ trình bước 0) — CHỈ ĐỌC database.

Dùng sự kiện ``ict_structure`` ≥ 0.5.0 (``ORDER_BLOCK_*``, ``OB_TAP_*``, ``OTE_ENTRY_*`` …) và khung đo của
``ict_indicator_survey.py`` (dữ liệu dev 2018 – 08/2024, nến hợp lệ, kết cục ±1 ATR, đúng hướng cân bằng, CI bootstrap
khối tuần, null dịch vòng, BH). Ba phần:

A. **Luật K17–K27** (``LUAT``): tín hiệu ±1 chỉ ở nến sự kiện (nến chạm OB lần đầu / nến vào OTE lần đầu), 0 ở nến
   khác. Đúng hướng cân bằng 1h / 4h, so cặp với tín hiệu cha. K17 chạy thêm với OB-R và OB-D để kiểm chéo. BH riêng
   cho họ phép thử này.
B. **OB có giữ giá hơn vùng giả không.** Tại lần chạm đầu, P(giá đi +1·ATR theo chiều OB, tính từ mép gần, trước khi
   close vượt mép xa). Vùng giả: cùng bề rộng, tâm ở giữa thân một nến khác trong 10 nến trước d (không phải nến OB,
   không vắt qua khoảng trống), cùng vòng đời với OB thật (xác nhận khi vượt đầu xa, lần chạm đầu, hạn 96 nến, SHIFT
   ngược chiều). Câu hỏi: «nến ngược màu cuối» có gì đặc biệt so với một vùng bất kỳ ngay cạnh nó.
C. **OTE 62–79% có hơn độ sâu hồi khác không.** Mỗi nhịp sau SHIFT (gốc X của sự kiện OTE, đầu H = cực trị từ d, nến
   t dùng H của nến t − 1, như lõi): lần đầu độ sâu hồi chạm một dải mới (0–38, 38–50, 50–62, 62–79, 79–100%), nhịp
   đủ ``ote_nhip_min_atr`` × ATR → đo P(vượt H trong 4 giờ). So với kỳ vọng của một mức BẤT KỲ cùng khoảng cách (phân
   phối biên lên/xuống của mọi nến hợp lệ cùng giờ NY × tam phân vị ATR/giá — cách của phần C khảo sát v1).

Khai báo trước (không sửa sau khi xem kết quả; sửa thì đổi ``SURVEY_VERSION`` và ghi lý do):

* K17 = ``OB_TAP_*`` (lần chạm đầu không hỏng). ``OB_FAIL_*`` không tính: tới close của nến chạm, OB đã hỏng.
* Mỗi phía (+1 / −1) cần ≥ ``MIN_SIDE_EV`` = 100 sự kiện (luật sự kiện thưa hơn luật theo nến của v1: 200).
* Ngưỡng: RSI M15 ≤ 40 / ≥ 60 (K20), ADX H1 ≥ 25 (K26), killzone ``london`` (02–05) / ``ny_am`` (07–10) giờ NY theo mặc
  định của lab, đọc ở ``details.killzone`` của sự kiện (K27).
* Phần B: kết cục trong tối đa 32 nến (8 giờ) từ nến chạm; chưa rõ / vắt qua khoảng trống > 3 giờ → bỏ.

Chẩn đoán SAU khi xem kết quả (v1.1, không khai trước — chỉ để đọc kết quả phần B): tách cặp (OB, vùng giả) theo vị
trí tâm vùng giả so với tâm OB, tính theo bề rộng OB — sâu hơn (> 0,25: dưới OB tăng), gần trùng, nông hơn (< −0,25).

Ví dụ (PowerShell, từ thư mục market-structure-lab)::

    .\\.venv\\Scripts\\python.exe research\\khao_sat_ob_ote.py --json docs\\research\\khao_sat\\ob_ote_dev.json
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import platform
import sqlite3
import sys
import time
import warnings

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import ict_indicator_survey as S  # noqa: E402  (dữ liệu, kết cục, thước đo phần A, BH)
import regime_survey as RS  # noqa: E402
from core.algorithms.ict_structure import IctStructureAlgorithm  # noqa: E402
from core.engine import run_algorithm  # noqa: E402

SURVEY_VERSION = "ob-ote-survey-v1.1"   # v1.1: thêm chẩn đoán SAU phần B (vị trí vùng giả) — phần khai trước giữ nguyên
MIN_SIDE_EV = 100
RSI_LO, RSI_HI = 40.0, 60.0
ADX_MIN = 25.0
KZ = ("london", "ny_am")
OB_HAN = 96                           # = ob_han mặc định của lõi (vòng đời vùng giả)
HOLD_W = 32                           # phần B: tối đa 32 nến để biết kết cục
FAKE_BACK = 10                        # phần B: vùng giả từ 10 nến trước d
DEPTH_BINS = (0.0, 0.38, 0.5, 0.62, 0.79, 1.0)
OTE_BIN = 3                           # dải 62–79%
OTE_MIN_LEG_ATR = 2.0                 # = ote_nhip_min_atr mặc định
OTE_HAN = 96
H_C = 16                              # phần C: 4 giờ
VARIANTS = {"K17R": {"ob_bien_the": "nen_cuoi_rau"}, "K17D": {"ob_neo": "displacement"}}

LUAT = {
    # tên: (mô tả, tín hiệu «cha» để so cặp)
    "K17": ("OB-T chạm lần đầu → theo chiều OB", "ict_shift16"),
    "K18": ("K17 ∧ bias ICT H1 = H4 cùng chiều", "K17"),
    "K19": ("K17 ∧ bias EMA H1 = H4 cùng chiều", "K17"),
    "K20": ("K17 ∧ RSI M15 ≤ 40 (OB tăng) / ≥ 60 (OB giảm)", "K17"),
    "K21": ("K17, chỉ OB của SHIFT có FVG", "K17"),
    "K22": ("Vào OTE lần đầu → theo chiều SHIFT", "ict_shift16"),
    "K23": ("K22 ∧ bias ICT H1 = H4 cùng chiều", "K22"),
    "K24": ("K22 ∧ bias EMA H1 = H4 cùng chiều", "K22"),
    "K25": ("K22 ∧ OB-T cùng SHIFT giao vùng OTE", "K22"),
    "K26": ("K22 ∧ ADX H1 ≥ 25", "K22"),
    "K27": ("K22 trong killzone London 02–05 / NY sáng 07–10 (giờ NY)", "K22"),
    "K17R": ("Như K17, OB-R (nến ngược màu cuối, cả râu) — đối chứng", "K17"),
    "K17D": ("Như K17, OB-D (neo mọi displacement) — đối chứng", "K17"),
}
DINH_NGHIA = {
    "su_kien": "Tín hiệu luật = chiều sự kiện ở nến xác nhận của nó (chạm OB / vào OTE), 0 ở nến khác; hai sự kiện "
               "ngược chiều cùng nến → 0. Kết cục, nến hợp lệ, BA, CI, null: như ict_indicator_survey.py.",
    "giu_gia": "Phần B: từ nến chạm τ, close[τ] vượt mép xa → 0; sau đó nến đầu tiên high ≥ mép gần + ATR[τ] (OB tăng) → "
               "1, close vượt mép xa → 0; 32 nến chưa rõ hoặc có khoảng trống > 3 giờ → bỏ.",
    "vung_gia": "Cùng bề rộng OB, tâm = (open + close)/2 của một nến j ∈ [d − 10, d − 1] không thuộc OB, cùng phía khoảng "
                "trống với d. Vòng đời như OrderBlockTracker: xác nhận từ d (close qua mép xa trước → bỏ), lần chạm đầu "
                "trước d + 96 và trước SHIFT ngược chiều. Mỗi OB: trung bình các vùng giả có kết cục.",
    "do_sau": "Phần C: độ sâu = (H[t−1] − low[t]) / (H[t−1] − X) (nhịp tăng). Ghi một quan sát mỗi lần độ sâu lớn nhất "
              "sang dải mới khi nhịp ≥ 2 × ATR[t−1]; dừng khi thủng X, có SHIFT mới, hoặc quá 96 nến. Thực tế = biên "
              "lên 4 giờ ≥ (H[t] − C[t]) / ATR[t]; kỳ vọng = P(biên ≥ khoảng cách đó) của mọi nến hợp lệ cùng giờ NY × "
              "tam phân vị ATR/giá.",
}
TAP = ("OB_TAP_UP", "OB_TAP_DOWN")
KEEP = {"ORDER_BLOCK_UP", "ORDER_BLOCK_DOWN", "OB_TAP_UP", "OB_TAP_DOWN", "OB_FAIL_UP", "OB_FAIL_DOWN", "OB_EXPIRED",
        "OTE_ENTRY_UP", "OTE_ENTRY_DOWN", "OTE_FAIL_UP", "OTE_FAIL_DOWN", "OTE_EXPIRED",
        "SHIFT_UP", "SHIFT_DOWN", "SHIFT_FVG_UP", "SHIFT_FVG_DOWN"}
SGN = {"up": 1.0, "down": -1.0}


class Data(S.Data):
    """Như ``S.Data``; giữ thêm sự kiện OB / OTE / SHIFT của lần chạy mặc định (OB-T, neo SHIFT)."""

    def _ict(self, tl, events):
        self.ev = [e for e in events if e.structure_type in KEEP]
        return super()._ict(tl, events)


class EventRules(S.RuleEngine):
    """Thước đo phần A của v1, ngưỡng mẫu cho luật sự kiện = ``MIN_SIDE_EV`` mỗi phía."""

    def point(self, s, y, base):
        parts = self.sums(s, y, base)
        Sp, Cp, Sn, Cn = parts
        if Cp.sum() < MIN_SIDE_EV or Cn.sum() < MIN_SIDE_EV:
            return None, parts
        return float(self.ba(Sp.sum(), Cp.sum(), Sn.sum(), Cn.sum())), parts


def at_events(N, pairs):
    s = np.zeros(N)
    for t, v in pairs:
        s[t] += v
    return np.sign(s)


def variant_taps(spec, con, symbol, params, log):
    """Nến chạm lần đầu (``OB_TAP_*``) của một biến thể OB — chạy lại lõi trên đúng các nến đó."""
    t0 = time.time()
    _ds, bars, _tf, _m = RS.load(con, spec, allow_test=False)
    res = run_algorithm(bars, IctStructureAlgorithm(timeframe="M15", session_calendar=RS.CAL[symbol], **params))
    out = [(e.confirmed_bar_index, SGN[e.direction]) for e in res.events if e.structure_type in TAP]
    log("  biến thể %s: %d lần chạm, %.0f s" % (params, len(out), time.time() - t0))
    return out


def rules(d, var_taps):
    """Tín hiệu K17–K27 (+ đối chứng) theo nến; mỗi luật kèm số sự kiện trước khi lọc nến hợp lệ."""
    N, I, sig, M, H1 = d.N, d.ict, d.sig, d.ind["M15"], d.ind["H1"]
    ob_shift = {e.event_id: e.reference_event_id for e in d.ev if e.structure_type.startswith("ORDER_BLOCK")}
    fvg_shift = {e.details.get("shift") for e in d.ev if e.structure_type.startswith("SHIFT_FVG")}
    taps = [e for e in d.ev if e.structure_type in TAP]
    otes = [e for e in d.ev if e.structure_type.startswith("OTE_ENTRY")]

    def ev(lst):
        return at_events(N, [(e.confirmed_bar_index, SGN[e.direction]) for e in lst])

    k = {"K17": ev(taps), "K22": ev(otes)}
    r = M["rsi"]
    with np.errstate(invalid="ignore"):
        k["K18"] = S.agree(k["K17"], I["h1"], I["h4"])
        k["K19"] = S.agree(k["K17"], sig["ema_h1"], sig["ema_h4"])
        k["K20"] = S.gate(k["K17"], ((k["K17"] > 0) & (r <= RSI_LO)) | ((k["K17"] < 0) & (r >= RSI_HI)), r)
        k["K21"] = ev([e for e in taps if ob_shift.get(e.reference_event_id) in fvg_shift])
        k["K23"] = S.agree(k["K22"], I["h1"], I["h4"])
        k["K24"] = S.agree(k["K22"], sig["ema_h1"], sig["ema_h4"])
        k["K25"] = ev([e for e in otes if e.details.get("ob_giao_vung")])
        k["K26"] = S.gate(k["K22"], H1["adx"] >= ADX_MIN, H1["adx"])
        k["K27"] = ev([e for e in otes if e.details.get("killzone") in KZ])
    for name, pairs in var_taps.items():
        k[name] = at_events(N, pairs)
    n_ev = {name: int(np.count_nonzero(np.nan_to_num(v))) for name, v in k.items()}
    return k, n_ev


def part_a(d, eng, k, n_ev, log):
    out = {}
    for h in S.HS:
        y = d.y[h]["up"]
        base = d.ok & np.isfinite(y)
        t0 = time.time()
        rows = {}
        for name, (_desc, par) in LUAT.items():
            rows[name] = eng.test(k[name], y, base, d.year, parent=k[par] if par in k else d.sig[par])
            rows[name]["n_su_kien"] = n_ev[name]
        out[S.TEN_H[h]] = {"n_nen": int(base.sum()), "ty_le_len_truoc": RS.rnd(np.nanmean(y[base]), 4), "tin_hieu": rows}
        log("  A · %s: %d luật, %.0f s" % (S.TEN_H[h], len(rows), time.time() - t0))
    return out


# ---------------------------------------------------------------- phần B: OB thật so với vùng giả


class Bars:
    """Mảng giá + khoảng trống + SHIFT theo chiều (để mô phỏng vòng đời vùng)."""

    def __init__(self, d):
        self.d = d
        gap = np.r_[False, np.diff(d.t_open.to_numpy()) > S.GAP_MAX.to_timedelta64()]   # khoảng trống ngay trước nến
        self.gapc = np.cumsum(gap)
        sh = sorted((e.confirmed_bar_index, SGN[e.direction]) for e in d.ev if e.structure_type.startswith("SHIFT_")
                    and not e.structure_type.startswith("SHIFT_FVG"))
        self.shift_at = {1.0: [t for t, v in sh if v > 0], -1.0: [t for t, v in sh if v < 0]}
        self.shift_all = [t for t, _v in sh]

    def next_shift(self, after, direction=None):
        lst = self.shift_all if direction is None else self.shift_at[direction]
        i = bisect.bisect_right(lst, after)
        return lst[i] if i < len(lst) else None

    def first_touch(self, up, lo, hi, d0):
        """Vòng đời như ``OrderBlockTracker``: (nến xác nhận k, nến chạm đầu τ); None khi không có."""
        d = self.d
        C, Hh, Ll, last = d.C, d.H, d.L, d.N - 1
        dl = d0 + OB_HAN
        opp = self.next_shift(d0, -1.0 if up else 1.0)
        k = None
        for t in range(d0, min(dl, last) + 1):
            if k is None:                                    # ứng viên: close qua mép xa / hết hạn → bỏ; vượt đầu xa → xác nhận
                if ((C[t] < lo) if up else (C[t] > hi)) or t >= dl:
                    return None, None
                if (Hh[t] > hi) if up else (Ll[t] < lo):
                    k = t
            else:                                            # đã xác nhận (từ nến sau k): chạm đầu / hết hạn
                if (Ll[t] <= hi) if up else (Hh[t] >= lo):
                    return k, t
                if t >= dl:
                    return k, None
            if opp is not None and t >= opp:                 # SHIFT ngược chiều ở bước 6c của nến t (sau 3b)
                return k, None
        return k, None

    def hold(self, up, lo, hi, tau):
        """1 = đi +1·ATR[τ] từ mép gần trước khi close vượt mép xa; 0 = ngược lại; NaN = chưa rõ / khoảng trống."""
        d = self.d
        a = d.atr[tau]
        if not (np.isfinite(a) and a > 0):
            return np.nan
        if (d.C[tau] < lo) if up else (d.C[tau] > hi):
            return 0.0
        target = hi + a if up else lo - a
        for t in range(tau + 1, min(tau + HOLD_W, d.N - 1) + 1):
            if self.gapc[t] != self.gapc[tau]:
                return np.nan
            if (d.H[t] >= target) if up else (d.L[t] <= target):
                return 1.0
            if (d.C[t] < lo) if up else (d.C[t] > hi):
                return 0.0
        return np.nan


def week_ratio_boot(M, wk, nW, num, den):
    Sx = np.bincount(wk, weights=num, minlength=nW)
    Cx = np.bincount(wk, weights=den, minlength=nW)
    with np.errstate(invalid="ignore", divide="ignore"):
        return (M @ Sx) / (M @ Cx), Sx.sum() / max(Cx.sum(), 1e-12)


def ci(x):
    x = x[np.isfinite(x)]
    return [RS.rnd(np.quantile(x, 0.025), 4), RS.rnd(np.quantile(x, 0.975), 4)] if x.size else None


def part_b(d, B, n_boot):
    rng = np.random.default_rng(S.SEED + 3)
    M = rng.multinomial(d.nW, np.full(d.nW, 1.0 / d.nW), size=n_boot).astype(float)
    obs = [e for e in d.ev if e.structure_type.startswith("ORDER_BLOCK")]
    first = {}
    for e in d.ev:
        if e.structure_type.startswith(("OB_TAP", "OB_FAIL")) and e.reference_event_id not in first:
            first[e.reference_event_id] = e.confirmed_bar_index
    rows, pairs = [], []
    same_k = same_tau = 0
    for e in obs:
        x = e.details
        up, lo, hi, d0 = e.direction == "up", float(x["lo"]), float(x["hi"]), int(x["nen_neo"])
        k, tau = B.first_touch(up, lo, hi, d0)
        same_k += int(k == e.confirmed_bar_index)
        same_tau += int(tau == first.get(e.event_id))
        real = B.hold(up, lo, hi, tau) if tau is not None else np.nan
        w = hi - lo
        fakes, fake_touch, mid = [], [], (lo + hi) / 2.0
        for j in range(max(0, d0 - FAKE_BACK), d0):
            if x["nen_dau"] <= j <= x["nen_cuoi"] or B.gapc[j] != B.gapc[d0]:
                continue
            m = (d.O[j] + d.C[j]) / 2.0
            fl, fh = m - w / 2.0, m + w / 2.0
            _k, ftau = B.first_touch(up, fl, fh, d0)
            fake_touch.append(0.0 if ftau is None else 1.0)
            if ftau is not None:
                fakes.append(B.hold(up, fl, fh, ftau))
                if np.isfinite(real) and np.isfinite(fakes[-1]) and w > 0:
                    pairs.append((d.week[d0], real - fakes[-1], ((mid - m) if up else (m - mid)) / w))
        fk = np.array(fakes, float)
        fk = fk[np.isfinite(fk)]
        rows.append((d.week[d0], real, fk.mean() if fk.size else np.nan, 0.0 if tau is None else 1.0,
                     np.mean(fake_touch) if fake_touch else np.nan))
    if not rows:
        return {"n_ob": 0}
    wk = np.array([r[0] for r in rows])
    real, fake, rt, ftc = (np.array([r[i] for r in rows], float) for i in (1, 2, 3, 4))
    rr, ff = np.isfinite(real), np.isfinite(fake)
    b_real, p_real = week_ratio_boot(M, wk[rr], d.nW, real[rr], np.ones(rr.sum()))
    b_fake, p_fake = week_ratio_boot(M, wk[ff], d.nW, fake[ff], np.ones(ff.sum()))
    both = rr & ff
    b_pair, p_pair = week_ratio_boot(M, wk[both], d.nW, real[both] - fake[both], np.ones(both.sum()))
    ft_ok = np.isfinite(ftc)
    b_tr, p_tr = week_ratio_boot(M, wk, d.nW, rt, np.ones(len(rt)))
    b_tf, p_tf = week_ratio_boot(M, wk[ft_ok], d.nW, ftc[ft_ok], np.ones(ft_ok.sum()))
    pw, pd_, po = (np.array([p[i] for p in pairs], float) for i in range(3))
    pos = {}
    for name, sel in (("gia_sau_hon", po > 0.25), ("gia_gan_trung", np.abs(po) <= 0.25), ("gia_nong_hon", po < -0.25)):
        if sel.sum() >= 100:
            bx, px = week_ratio_boot(M, pw[sel].astype(int), d.nW, pd_[sel], np.ones(sel.sum()))
            pos[name] = {"n_cap": int(sel.sum()), "chenh_that_tru_gia": RS.rnd(px, 4), "ci95": ci(bx)}
    return {"n_ob": len(rows), "chan_doan_sau_vi_tri": pos, "mo_phong_khop_lop_loi": {"nen_xac_nhan": RS.rnd(same_k / len(rows), 4),
                                                         "nen_cham_dau": RS.rnd(same_tau / len(rows), 4)},
            "ty_le_cham": {"that": RS.rnd(p_tr, 4), "that_ci95": ci(b_tr), "gia": RS.rnd(p_tf, 4), "gia_ci95": ci(b_tf)},
            "giu_gia": {"that": {"n": int(rr.sum()), "p": RS.rnd(p_real, 4), "ci95": ci(b_real)},
                        "gia": {"n_ob": int(ff.sum()), "p": RS.rnd(p_fake, 4), "ci95": ci(b_fake)},
                        "chenh_cung_ob": {"n": int(both.sum()), "chenh": RS.rnd(p_pair, 4), "ci95": ci(b_pair),
                                          "mde80": RS.rnd(2.8 * np.nanstd(b_pair, ddof=1), 4)}}}


# ---------------------------------------------------------------- phần C: độ sâu hồi của nhịp sau SHIFT


def depth_obs(d, B):
    """(t, dải, chiều, khoảng cách tới H theo ATR[t]) mỗi lần độ sâu lớn nhất của một nhịp sang dải mới."""
    legs = {}
    for e in d.ev:
        if e.structure_type.startswith("OTE_") and e.details.get("nen_neo") is not None:
            legs.setdefault(int(e.details["nen_neo"]), (e.details["chieu"] == "up", float(e.details["x"])))
    out = []
    last = d.N - 1 - H_C
    for d0, (up, X) in sorted(legs.items()):
        nxt = B.next_shift(d0)
        end = min(d0 + OTE_HAN, nxt if nxt is not None else last, last)
        Hp = d.H[d0] if up else d.L[d0]
        best = -1
        for t in range(d0 + 1, end + 1):
            leg = (Hp - X) if up else (X - Hp)
            if leg <= 0 or ((d.L[t] < X) if up else (d.H[t] > X)):
                break
            dep = ((Hp - d.L[t]) if up else (d.H[t] - Hp)) / leg
            a1 = d.atr[t - 1]
            b = int(np.searchsorted(DEPTH_BINS, min(dep, 1.0), side="right")) - 1 if dep >= 0 else -1
            b = min(b, len(DEPTH_BINS) - 2)
            if b > best and np.isfinite(a1) and leg >= OTE_MIN_LEG_ATR * a1 and d.ok[t]:
                best = b
                Ht = max(Hp, d.H[t]) if up else min(Hp, d.L[t])
                out.append((t, b, up, ((Ht - d.C[t]) if up else (d.C[t] - Ht)) / d.atr[t]))
            Hp = max(Hp, d.H[t]) if up else min(Hp, d.L[t])
    return out


def part_c(d, B, n_boot):
    rng = np.random.default_rng(S.SEED + 4)
    M = rng.multinomial(d.nW, np.full(d.nW, 1.0 / d.nW), size=n_boot).astype(float)
    Y = d.y[H_C]
    bps = d.atr / d.C
    cut = np.quantile(bps[np.isfinite(bps) & d.ok], [1 / 3, 2 / 3])
    stratum = np.floor(d.hour_ny).astype(int) * 3 + np.digitize(np.nan_to_num(bps), cut)
    pools = {}
    for side in ("mfe_up", "mfe_dn"):
        base = d.ok & np.isfinite(Y[side])
        pools[side] = {g: np.sort(Y[side][base & (stratum == g)]) for g in np.unique(stratum[base])}
    rec = []
    for t, b, up, dist in depth_obs(d, B):
        side = "mfe_up" if up else "mfe_dn"
        mfe, pool = Y[side][t], pools[side].get(stratum[t])
        if not np.isfinite(mfe) or pool is None or pool.size < 50 or not np.isfinite(dist):
            continue
        exp = 1.0 - np.searchsorted(pool, dist, side="left") / pool.size
        rec.append((d.week[t], b, 1.0 if mfe >= dist else 0.0, exp, dist))
    if not rec:
        return {"n": 0}
    wk, bb, hit, exp, dist = (np.array([r[i] for r in rec]) for i in range(5))
    wk, bb = wk.astype(int), bb.astype(int)
    rows, boots = [], {}
    for i in range(len(DEPTH_BINS) - 1):
        sel = bb == i
        row = {"tu": DEPTH_BINS[i], "den": DEPTH_BINS[i + 1], "n": int(sel.sum())}
        if sel.sum() >= 100:
            bx, px = week_ratio_boot(M, wk[sel], d.nW, hit[sel] - exp[sel], np.ones(sel.sum()))
            boots[i] = (M @ np.bincount(wk[sel], weights=hit[sel] - exp[sel], minlength=d.nW),
                        M @ np.bincount(wk[sel], minlength=d.nW).astype(float))
            row.update({"vuot_h": RS.rnd(hit[sel].mean(), 4), "ky_vong": RS.rnd(exp[sel].mean(), 4),
                        "chenh": RS.rnd(px, 4), "ci95": ci(bx), "kc_trung_vi_atr": RS.rnd(np.median(dist[sel]), 3)})
        rows.append(row)
    cmp = {}
    if OTE_BIN in boots:
        so, co = boots[OTE_BIN]
        for name, others in (("so_voi_50_62", (2,)), ("so_voi_79_100", (4,)), ("so_voi_moi_dai_khac", (0, 1, 2, 4))):
            if all(i in boots for i in others):
                sx = sum(boots[i][0] for i in others)
                cx = sum(boots[i][1] for i in others)
                with np.errstate(invalid="ignore", divide="ignore"):
                    dd = so / co - sx / cx
                sel_o, sel_x = bb == OTE_BIN, np.isin(bb, others)
                pt = (hit[sel_o] - exp[sel_o]).mean() - (hit[sel_x] - exp[sel_x]).mean()
                cmp[name] = {"chenh_cua_chenh": RS.rnd(pt, 4), "ci95": ci(dd), "mde80": RS.rnd(2.8 * np.nanstd(dd, ddof=1), 4)}
    return {"n": len(rec), "theo_do_sau": rows, "dai_ote_so_voi": cmp}


# ---------------------------------------------------------------- chạy


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--json", default=os.path.join(ROOT, "docs", "research", "khao_sat", "ob_ote_dev.json"))
    ap.add_argument("--db", default=os.environ.get("MSL_DB_PATH") or os.path.join(ROOT, "data", "lab.sqlite"))
    ap.add_argument("--ma", default="XAUUSD,EURUSD", help="Danh sách mã, cách nhau bởi dấu phẩy")
    ap.add_argument("--nhanh", action="store_true", help="Chạy thử nhanh (ít bootstrap) — không dùng để kết luận")
    args = ap.parse_args()
    t_all = time.time()

    def log(msg):
        print(msg, flush=True)

    n_boot, n_shift = (200, 29) if args.nhanh else (S.N_BOOT, S.N_SHIFT)
    con = sqlite3.connect("file:%s?mode=ro" % args.db.replace("\\", "/"), uri=True)
    with open(os.path.abspath(__file__), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    meta = {"phien_ban": SURVEY_VERSION, "script_sha256": sha, "khung_do": S.SURVEY_VERSION,
            "python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
            "doan_kiem_tra_tu": S.TEST_START, "seed": S.SEED, "chay_nhanh": bool(args.nhanh),
            "tham_so": {"HS": list(S.HS), "k_cham": S.K_TOUCH, "n_boot": n_boot, "n_shift": n_shift,
                        "min_moi_phia": MIN_SIDE_EV, "rsi": [RSI_LO, RSI_HI], "adx_h1": ADX_MIN, "killzone": list(KZ),
                        "giu_gia_toi_da_nen": HOLD_W, "vung_gia_lui": FAKE_BACK, "ob_han": OB_HAN,
                        "dai_do_sau": list(DEPTH_BINS), "ote_nhip_min_atr": OTE_MIN_LEG_ATR, "phan_c_tam_nen": H_C,
                        "bien_the": VARIANTS},
            "tao_luc": pd.Timestamp.now(tz="UTC").isoformat(timespec="seconds")}
    out = {"meta": meta, "dinh_nghia": DINH_NGHIA, "luat": {k: {"mo_ta": t, "cha": p} for k, (t, p) in LUAT.items()},
           "ket_qua": {}}
    wanted = [s.strip() for s in args.ma.split(",") if s.strip()]
    for spec in S.SETS:
        sym = spec["key"].split()[0]
        if sym not in wanted:
            continue
        log("== %s" % spec["key"])
        t0 = time.time()
        d = Data(spec, con, log)
        log("  dữ liệu: %.0f s, %d nến, %d hợp lệ, %d sự kiện OB/OTE/SHIFT" % (time.time() - t0, d.N, d.ok.sum(), len(d.ev)))
        var_taps = {name: variant_taps(spec, con, sym, p, log) for name, p in VARIANTS.items()}
        k, n_ev = rules(d, var_taps)
        eng = EventRules(d.week, d.nW, n_boot, n_shift)
        B = Bars(d)
        res = {"meta": d.meta, "A": part_a(d, eng, k, n_ev, log)}
        t0 = time.time()
        res["B"] = part_b(d, B, n_boot)
        res["C"] = part_c(d, B, n_boot)
        log("  B + C: %.0f s" % (time.time() - t0))
        out["ket_qua"][sym] = res
        del d
    meta["so_phep_thu_bh"] = S.apply_bh(out["ket_qua"])
    meta["thoi_gian_chay_s"] = round(time.time() - t_all, 1)
    os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
    with open(args.json, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    log("Đã ghi %s (%.0f s)" % (args.json, time.time() - t_all))


if __name__ == "__main__":
    warnings.filterwarnings("ignore", category=RuntimeWarning)
    main()
