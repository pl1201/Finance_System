"""Khảo sát tái lập làm căn cứ thiết kế ``ict_structure`` (docs/plan_ict_structure.md §2, §11).

Đây là BẢN MẪU định nghĩa (survey-v2), không phải thuật toán sẽ cài:

* đọc ``data/lab.sqlite`` ở chế độ CHỈ ĐỌC, không ghi gì; khoá dữ liệu bằng checksum;
* mặc định chỉ đoạn phát triển 2024-01-01..2024-08-31 — đoạn kiểm tra cần ``--allow-test``;
* nhân quả theo nghĩa: thông tin dùng tại nến t chỉ đến từ nến ≤ t; mức/vùng mới có hiệu lực
  từ nến sau nến làm nó được biết; nến khung lớn chỉ dùng khi ĐÃ CHỐT;
* không có BOS/CHoCH: đổi hướng = quét thanh khoản rồi displacement ngược chiều («shift»);
  bias = ba thành phần riêng (thứ tự đỉnh/đáy, phản ứng ở FVG khung lớn, DOL).

Định nghĩa chi tiết nằm ở docstring từng hàm và ở plan §4. Kết quả là số mô tả, không có
win rate/P&L, không có nhãn tham chiếu.

Ví dụ (PowerShell, từ thư mục market-structure-lab):

    .\\.venv\\Scripts\\python.exe scripts\\ict_survey.py --json docs\\khao_sat\\ict_survey_dev.json
"""
from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import platform
import sqlite3
import statistics as st
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from core.algorithms.dc_atr_structure import DcAtrStructureAlgorithm  # noqa: E402
from core.algorithms.swing_hierarchy import SwingHierarchyAlgorithm  # noqa: E402
from core.algorithms.swing_pivot import SwingPivotAlgorithm  # noqa: E402
from core.data.loader import rows_checksum  # noqa: E402
from core.data.session_calendar import SessionCalendar  # noqa: E402
from core.engine import run_algorithm  # noqa: E402
from core.indicators import WilderATRPrevClose  # noqa: E402
from core.types import build_bars, timeframe_delta  # noqa: E402

SURVEY_VERSION = "survey-v2"
NY = ZoneInfo("America/New_York")
TEST_START = "2024-09-01"
CFG = {
    "atr_period": 14,             # Wilder, seed theo close trước; giá trị nến t−1 dùng cho nến t
    "k_disp": 1.5,                # displacement: biên độ ≥ k·ATR
    "body_min": 0.6,              # và thân ≥ 60% biên độ
    "min_pen_atr": 0.1,           # vùng thanh khoản bị LẤY khi xuyên ≥ 0.1·ATR; nông hơn = CHẠM
    "sweep_windows": [0, 3],      # close quay lại trong [nến lấy, nến lấy + W]
    "shift_window": 3,            # displacement ngược chiều trong [nến quay lại, +3]
    "eq_tol_atr": 0.1,            # dung sai HH/HL
    "killzones_ny": {"Asia": [20, 24], "London": [2, 5], "NY AM": [7, 10]},
    "session_break_ny": "17:00-18:00, cuối tuần Thứ Sáu 17:00 → Chủ nhật 18:00",
    "htf_alignment": "ny_1700",
    "htf_min_coverage": 0.9,      # nến khung lớn thiếu > 10% số nến theo lịch → «thiếu dữ liệu»
    "respect_away_atr": 1.0,      # biến thể respect chặt: close rời mép gần ≥ 1·ATR M15
    "dol_min_tier": "H1",
    "default_sweep_window_for_bias": 0,
}
# Lịch phiên KHAI BÁO (data/calendars, bản sao từ market-data-pipeline) — không suy từ dữ liệu.
CAL = SessionCalendar.load("cme_globex_metals")
TIERS = ("M15", "H1", "H4", "D", "W")
RANK = {t: i for i, t in enumerate(TIERS)}


# ---------------------------------------------------------------- tiện ích
def q(xs, ps=(0.1, 0.25, 0.5, 0.75, 0.9)):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return {}
    return {"p%d" % int(p * 100): round(xs[min(len(xs) - 1, int(p * len(xs)))], 3) for p in ps}


def shares(counter: Counter, total: int) -> dict:
    return {str(k): round(v / total, 3) for k, v in sorted(counter.items(), key=lambda kv: str(kv[0]))}


def ny(t: datetime) -> datetime:
    return t.astimezone(NY)


def in_closure(t: datetime) -> bool:
    """Ô bắt đầu lúc t (UTC) nằm ngoài phiên theo lịch khai báo (nghỉ hằng ngày, cuối tuần, lễ)."""
    return CAL.closure_reason(t) is not None


def killzone(t: datetime) -> str:
    """Theo giờ mở nến, giờ New York."""
    loc = ny(t)
    h = loc.hour + loc.minute / 60
    for name, (a, b) in CFG["killzones_ny"].items():
        if a <= h < b:
            return name
    return "ngoai"


def trading_day(t: datetime):
    """Ngày giao dịch kết thúc 17:00 NY; nhãn = ngày kết thúc."""
    return (ny(t) + timedelta(hours=7)).date()


def cmp(a: float, b: float, tol: float) -> int:
    return 1 if a > b + tol else (-1 if a < b - tol else 0)


def prev_atr(highs, lows, closes, period):
    a, last, out = WilderATRPrevClose(period), None, []
    for h, l, c in zip(highs, lows, closes):
        out.append(last)
        last = a.update(h, l, c)
    return out


def pivots(H, L, blocked):
    """STH/STL strict 3 nến; ``blocked(c)`` loại cửa sổ c−1..c+1. Trả (c, conf=c+1, giá)."""
    sth, stl = [], []
    for c in range(1, len(H) - 1):
        if blocked(c):
            continue
        if H[c] > H[c - 1] and H[c] > H[c + 1]:
            sth.append((c, c + 1, H[c]))
        if L[c] < L[c - 1] and L[c] < L[c + 1]:
            stl.append((c, c + 1, L[c]))
    return sth, stl


def level_up(seq, is_high):
    """Larry Williams: swing cấp trên = swing có hai swing cùng loại liền kề kém hơn (strict).
    Biết khi swing bên phải được xác nhận."""
    out = []
    for k in range(1, len(seq) - 1):
        a, b, c = seq[k - 1][2], seq[k][2], seq[k + 1][2]
        if (b > a and b > c) if is_high else (b < a and b < c):
            out.append((seq[k][0], seq[k + 1][1], b))
    return out


def runs(states, times):
    """Độ dài (giờ, đồng hồ thật) các đoạn trạng thái liên tiếp, bỏ None."""
    out, start, cur = [], None, None
    for s, t in zip(states, times):
        if s != cur:
            if cur is not None and start is not None:
                out.append((cur, (t - start).total_seconds() / 3600))
            cur, start = s, t
    return out


# ---------------------------------------------------------------- dữ liệu
def load(con, dataset_id, start, end):
    row = con.execute(
        "SELECT id,name,timeframe,timestamp_convention,is_synthetic,checksum_sha256,row_count "
        "FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if row is None:
        raise SystemExit("Không tìm thấy dataset %s." % dataset_id)
    ds = dict(zip(("id", "name", "timeframe", "timestamp_convention", "is_synthetic",
                   "checksum_sha256", "row_count"), row))
    rows = [{"bar_time": datetime.fromisoformat(t), "open": o, "high": h, "low": lo, "close": c,
             "volume": v}
            for t, o, h, lo, c, v in con.execute(
                "SELECT bar_time,open,high,low,close,volume FROM bars WHERE dataset_id=? "
                "AND bar_time>=? AND bar_time<? ORDER BY idx", (dataset_id, start, end))]
    if not rows:
        raise SystemExit("Khoảng thời gian không có nến.")
    return ds, rows, build_bars(rows, ds["timeframe"], ds["timestamp_convention"])


class Series:
    def __init__(self, bars, timeframe):
        self.bars = bars
        self.n = len(bars)
        self.step = timeframe_delta(timeframe)
        self.O = [b.open for b in bars]
        self.H = [b.high for b in bars]
        self.L = [b.low for b in bars]
        self.C = [b.close for b in bars]
        self.gap = [False] + [bars[i].bar_time - bars[i - 1].bar_time != self.step
                              for i in range(1, self.n)]
        self.atr = prev_atr(self.H, self.L, self.C, CFG["atr_period"])

    def swings(self):
        """ITH/ITL của khung này; cửa sổ pivot không được vắt qua gap (plan D1)."""
        sth, stl = pivots(self.H, self.L, lambda c: self.gap[c] or self.gap[c + 1])
        return sth, stl, level_up(sth, True), level_up(stl, False)


# ---------------------------------------------------------------- nến khung lớn
@dataclass
class HBar:
    tf: str
    key: tuple
    start: datetime
    end: datetime
    expected: int
    o: float
    h: float
    l: float  # noqa: E741
    c: float
    first: int
    last: int
    n: int
    high_idx: int
    low_idx: int
    known: int = -1          # nến LTF mà tại close của nó biết nến này đã chốt
    degraded: bool = False   # thiếu > 10% nến so với lịch phiên (bất thường hoặc kỳ đầu dataset)
    over: bool = False       # nhiều nến hơn lịch phiên (lịch dữ liệu khác lịch giả định)
    after_hole: bool = False  # trước nó có cả bucket giao dịch bị mất


def bucket_bounds(tf: str, t: datetime):
    ts = int(t.timestamp())
    if tf in ("H1", "H4utc", "Dutc"):
        size = {"H1": 3600, "H4utc": 14400, "Dutc": 86400}[tf]
        s = ts // size * size
        start = datetime.fromtimestamp(s, timezone.utc)
        return (s,), start, start + timedelta(seconds=size)
    sh = ny(t) + timedelta(hours=7)
    d = sh.date()
    midnight = datetime(d.year, d.month, d.day, tzinfo=NY)
    if tf == "H4":
        k = sh.hour // 4
        s_loc = midnight - timedelta(hours=7) + timedelta(hours=4 * k)
        return (d, k), s_loc.astimezone(timezone.utc), (s_loc + timedelta(hours=4)).astimezone(timezone.utc)
    if tf == "D":
        s_loc = midnight - timedelta(hours=7)
        return (d,), s_loc.astimezone(timezone.utc), (s_loc + timedelta(days=1)).astimezone(timezone.utc)
    if tf == "W":
        monday = d - timedelta(days=d.weekday())
        s_loc = datetime(monday.year, monday.month, monday.day, tzinfo=NY) - timedelta(hours=7)
        return (monday,), s_loc.astimezone(timezone.utc), (s_loc + timedelta(days=5)).astimezone(timezone.utc)
    raise ValueError(tf)


_EXP_CACHE: dict = {}


def expected_slots(start, end, step):
    key = (start, end, step)
    if key not in _EXP_CACHE:
        n, s = 0, start
        while s < end:
            n += 0 if in_closure(s) else 1
            s += step
        _EXP_CACHE[key] = n
    return _EXP_CACHE[key]


def aggregate(S: Series, tf: str):
    """Gộp tuần tự. Chốt khi nến LTF có close = mốc đóng; thiếu nến cuối thì chốt khi nến
    đầu của bucket sau tới (biết tại close của nến đó). Bucket cuối chưa chốt bị bỏ."""
    out, cur = [], None
    for i, b in enumerate(S.bars):
        key, s, e = bucket_bounds(tf, b.bar_time)
        if cur is None or key != cur.key:
            if cur is not None:
                if cur.known < 0:
                    cur.known = i
                out.append(cur)
            cur = HBar(tf, key, s, e, expected_slots(s, e, S.step), b.open, b.high, b.low, b.close,
                       i, i, 1, i, i)
        else:
            if b.high > cur.h:
                cur.h, cur.high_idx = b.high, i
            if b.low < cur.l:
                cur.l, cur.low_idx = b.low, i
            cur.c, cur.last, cur.n = b.close, i, cur.n + 1
        if b.close_time == cur.end:
            cur.known = i
    if cur is not None and cur.known >= 0:
        out.append(cur)
    for k, x in enumerate(out):
        x.degraded = x.n < CFG["htf_min_coverage"] * x.expected
        x.over = x.n > x.expected
        x.after_hole = k > 0 and expected_slots(out[k - 1].end, x.start, S.step) > 0
    return out


def htf_swings(hb, tf):
    """ITH/ITL trên nến khung lớn đã chốt. Cửa sổ pivot chứa nến thiếu dữ liệu hoặc vắt qua
    bucket bị mất thì không tạo swing (lan truyền: ITH chỉ dựng từ STH hợp lệ)."""
    H = [x.h for x in hb]
    L = [x.l for x in hb]
    atr = prev_atr(H, L, [x.c for x in hb], CFG["atr_period"])

    def blocked(c):
        return any(x.degraded for x in hb[c - 1:c + 2]) or hb[c].after_hole or hb[c + 1].after_hole

    sth, stl = pivots(H, L, blocked)
    ith, itl = level_up(sth, True), level_up(stl, False)
    sw = []
    for side, seq in ((1, ith), (-1, itl)):
        for c, conf, price in seq:
            a = atr[conf]
            sw.append({"tf": tf, "side": side, "c": c, "conf": conf, "price": price,
                       "ext": hb[c].high_idx if side > 0 else hb[c].low_idx,
                       "known": hb[conf].known, "eff": hb[conf].known + 1,
                       "eff_leak": hb[conf].first,
                       "tol": CFG["eq_tol_atr"] * a if a else 0.0})
    blocked_n = sum(1 for c in range(1, len(hb) - 1) if blocked(c))
    return sw, {"sth": len(sth), "stl": len(stl), "ith": len(ith), "itl": len(itl),
                "cua_so_bi_chan": blocked_n}, atr


def ltf_swings(S: Series, tf="M15"):
    sth, stl, ith, itl = S.swings()
    sw = []
    for side, seq in ((1, ith), (-1, itl)):
        for c, conf, price in seq:
            a = S.atr[conf] if conf < S.n else None
            sw.append({"tf": tf, "side": side, "c": c, "conf": conf, "price": price, "ext": c,
                       "known": conf, "eff": conf + 1, "eff_leak": conf + 1,
                       "tol": CFG["eq_tol_atr"] * a if a else 0.0})
    return sw, {"sth": len(sth), "stl": len(stl), "ith": len(ith), "itl": len(itl)}


# ---------------------------------------------------------------- thứ tự đỉnh/đáy + dealing range
def order_series(S: Series, sw_list, eff_key="eff"):
    """Trạng thái thứ tự đỉnh/đáy sau mỗi nến LTF (dùng swing có hiệu lực ≤ t):
    +1 = HH và HL; −1 = LH và LL; 0 = lẫn lộn; None = chưa đủ 2 đỉnh + 2 đáy.
    Mức được bảo vệ: +1 → ITL gần nhất; −1 → ITH gần nhất. ``broken`` = đã có close vượt mức đó
    kể từ khi nó thành mức được bảo vệ (không đổi trạng thái — chỉ là cờ).
    Dealing range: [min(ITL gần nhất, low thấp nhất sau nó), max(ITH gần nhất, high cao nhất sau nó)]."""
    N, H, L, C = S.n, S.H, S.L, S.C
    sw = sorted(sw_list, key=lambda s: (s[eff_key], s["ext"]))
    ptr, hs, ls = 0, [], []
    state, broken_arr, rng = [None] * N, [False] * N, [None] * N
    cur, prot, broken, run_hi, run_lo = None, None, False, None, None
    for t in range(N):
        changed = False
        while ptr < len(sw) and sw[ptr][eff_key] <= t:
            s = sw[ptr]
            ptr += 1
            if s["side"] > 0:
                hs.append(s)
                run_hi = max([s["price"]] + H[s["ext"] + 1:t])
            else:
                ls.append(s)
                run_lo = min([s["price"]] + L[s["ext"] + 1:t])
            changed = True
        if run_hi is not None:
            run_hi = max(run_hi, H[t])
        if run_lo is not None:
            run_lo = min(run_lo, L[t])
        if changed and len(hs) >= 2 and len(ls) >= 2:
            hh = cmp(hs[-1]["price"], hs[-2]["price"], hs[-1]["tol"])
            hl = cmp(ls[-1]["price"], ls[-2]["price"], ls[-1]["tol"])
            new = 1 if (hh > 0 and hl > 0) else (-1 if (hh < 0 and hl < 0) else 0)
            new_prot = ls[-1]["price"] if new == 1 else (hs[-1]["price"] if new == -1 else None)
            if new != cur or new_prot != prot:
                broken = False
            cur, prot = new, new_prot
        if prot is not None and not broken:
            broken = (C[t] < prot) if cur == 1 else (C[t] > prot)
        state[t], broken_arr[t] = cur, broken
        if run_hi is not None and run_lo is not None and run_hi > run_lo:
            rng[t] = (run_lo, run_hi)
    return state, broken_arr, rng


# ---------------------------------------------------------------- chương trình chính
def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dataset", default="ds_db1583cd4dde", help="M15 thật (2024, giờ đã sửa)")
    ap.add_argument("--m5-dataset", default="ds_933fa5ec67e2", help="M5 cho hồ sơ khung; '' để bỏ")
    ap.add_argument("--start", default="2024-01-01")
    ap.add_argument("--end", default=TEST_START, help="không gồm")
    ap.add_argument("--allow-test", action="store_true")
    ap.add_argument("--db", default=os.path.join(ROOT, "data", "lab.sqlite"))
    ap.add_argument("--json", default="")
    args = ap.parse_args()
    if args.end > TEST_START and not args.allow_test:
        raise SystemExit("Đoạn kiểm tra (từ %s) chưa dùng cho thiết kế; cần --allow-test." % TEST_START)

    con = sqlite3.connect("file:%s?mode=ro" % args.db.replace("\\", "/"), uri=True)
    ds, rows, bars = load(con, args.dataset, args.start, args.end)
    if ds["timeframe"] != "M15" or ds["is_synthetic"]:
        raise SystemExit("Khảo sát khoá cho M15 dữ liệu thật.")
    S = Series(bars, "M15")
    N, O, H, L, C, atr, gap = S.n, S.O, S.H, S.L, S.C, S.atr, S.gap
    day_of = [trading_day(b.bar_time) for b in bars]
    days = len(set(day_of))
    out: dict = {"meta": {
        "survey_version": SURVEY_VERSION,
        "script_sha256": hashlib.sha256(open(__file__, "rb").read()).hexdigest(),
        "python": platform.python_version(),
        "dataset": {k: ds[k] for k in ("id", "name", "timeframe", "checksum_sha256", "row_count")},
        "doan": [args.start, args.end],
        "checksum_doan": rows_checksum(rows),
        "so_nen": N, "so_ngay_giao_dich": days,
        "ngay_giao_dich_la": "kết thúc 17:00 New York (Chủ nhật tối thuộc ngày Thứ Hai)",
        "phien_ban_thuat_toan_lab": {"swing_pivot": SwingPivotAlgorithm.version,
                                     "swing_hierarchy": SwingHierarchyAlgorithm.version,
                                     "dc_atr_structure": DcAtrStructureAlgorithm.version},
        "cau_hinh": CFG,
        "lich_phien": {k: CAL.meta.get(k) for k in ("name", "nguon", "nguon_ngoai_le", "ngoai_le")},
        "tao_luc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }}

    # ------------------------------------------------ 0. gap & lịch phiên
    gaps = Counter()
    abnormal = Counter()
    for i in range(1, N):
        if not gap[i]:
            continue
        kind, miss = CAL.classify_gap(bars[i - 1].bar_time + S.step, bars[i].bar_time, S.step)
        gaps[kind] += 1
        if miss:
            abnormal["%s: bắt đầu %s NY, %d ô trong phiên" % (
                ny(bars[i - 1].bar_time + S.step).strftime("%Y-%m-%d"),
                ny(bars[i - 1].bar_time + S.step).strftime("%H:%M"), miss)] += 1
    out["du_lieu"] = {"gap": dict(gaps), "gap_thieu_trong_phien": dict(abnormal.most_common(20))}

    # ------------------------------------------------ 1. swing (lab, không chặn gap) + đối chiếu
    def lab_swings(alg, types):
        ev = [e for e in run_algorithm(bars, alg).events if e.structure_type in types]
        lag = [e.confirmation_lag_bars for e in ev]
        return ev, {"so": len(ev), "moi_ngay": round(len(ev) / days, 2), "tre_nen": q(lag, (0.5, 0.9))}

    res = {}
    sth_lab, res["pivot 1/1 (STH/STL) — swing_pivot"] = lab_swings(
        SwingPivotAlgorithm(left=1, right=1, enable_bos=False), {"SWING_HIGH", "SWING_LOW"})
    _, res["pivot 3/3 — baseline swing_pivot"] = lab_swings(
        SwingPivotAlgorithm(left=3, right=3, enable_bos=False), {"SWING_HIGH", "SWING_LOW"})
    ith_lab, res["ITH/ITL (cấp 2 trên 1/1) — swing_hierarchy"] = lab_swings(
        SwingHierarchyAlgorithm(left=1, right=1), {"SWING_HIGH_L2", "SWING_LOW_L2"})
    dc_lab, res["DC k=1.5, close, bridge_short — dc_atr_structure"] = lab_swings(
        DcAtrStructureAlgorithm(timeframe="M15", gap_policy="bridge_short"), {"DC_HIGH", "DC_LOW"})

    sth, stl, ith, itl = S.swings()
    own_nogap = pivots(H, L, lambda c: False)
    res["kiem_tra_tuong_duong"] = {
        "pivot 1/1 tự viết (không chặn gap) == swing_pivot 1/1": sorted(
            [(c, p) for c, _, p in own_nogap[0] + own_nogap[1]]) == sorted(
            [(e.event_bar_index, e.price) for e in sth_lab]),
        "ITH/ITL tự viết (không chặn gap) == swing_hierarchy": sorted(
            [(c, p) for c, _, p in level_up(own_nogap[0], True) + level_up(own_nogap[1], False)]) == sorted(
            [(e.event_bar_index, e.price) for e in ith_lab]),
    }
    res["ITH/ITL chặn gap (survey-v2)"] = {"so": len(ith) + len(itl),
                                          "moi_ngay": round((len(ith) + len(itl)) / days, 2)}
    lth = level_up(ith, True) + level_up(itl, False)
    res["LTH/LTL (cấp 3, chặn gap)"] = {"so": len(lth), "moi_ngay": round(len(lth) / days, 2),
                                       "tre_nen": q([conf - c for c, conf, _ in lth], (0.5, 0.9))}

    def amp(seq_pairs):
        seq = sorted(seq_pairs)
        a = []
        for (c1, p1, s1), (c2, p2, s2) in zip(seq, seq[1:]):
            if s1 != s2 and atr[c2]:
                a.append(abs(p2 - p1) / atr[c2])
        return q(a, (0.5, 0.9))

    res["bien_do_nhip_ATR"] = {
        "STH/STL": amp([(c, p, 1) for c, _, p in sth] + [(c, p, -1) for c, _, p in stl]),
        "ITH/ITL": amp([(c, p, 1) for c, _, p in ith] + [(c, p, -1) for c, _, p in itl]),
        "DC": amp([(e.event_bar_index, e.price, 1 if e.structure_type == "DC_HIGH" else -1) for e in dc_lab]),
    }

    def near(a_ev, a_hi, b_ev, b_hi, tol=2):
        idx = {True: [], False: []}
        for e in b_ev:
            idx[e.structure_type == b_hi].append(e.event_bar_index)
        hit = sum(1 for e in a_ev
                  if any(abs(e.event_bar_index - j) <= tol for j in idx[e.structure_type == a_hi]))
        return round(hit / max(1, len(a_ev)), 3)

    res["doi_chieu_DC_ITH"] = {
        "quy_tac": "cùng phía (đỉnh/đáy), |event_bar_index chênh| ≤ 2 nến; ITH theo wick, DC theo "
                   "close; không xét giá; mỗi phần tử bên A được đếm nếu có ít nhất một phần tử B gần",
        "DC có ITH/ITL gần": near(dc_lab, "DC_HIGH", ith_lab, "SWING_HIGH_L2"),
        "ITH/ITL có DC gần": near(ith_lab, "SWING_HIGH_L2", dc_lab, "DC_HIGH"),
    }
    out["swing"] = res

    # ------------------------------------------------ 2. displacement & FVG
    disp = [0] * N
    ra, br = [], []
    for i in range(N):
        a, r = atr[i], H[i] - L[i]
        if a is None or r <= 0:
            continue
        ra.append(r / a)
        br.append(abs(C[i] - O[i]) / r)
        if not gap[i] and r >= CFG["k_disp"] * a and abs(C[i] - O[i]) >= CFG["body_min"] * r:
            disp[i] = 1 if C[i] > O[i] else (-1 if C[i] < O[i] else 0)
    fvg_at, fvg_sizes, fvg_gap = {}, [], 0
    for i in range(2, N):
        d = 1 if L[i] > H[i - 2] else (-1 if H[i] < L[i - 2] else 0)
        if not d:
            continue
        if gap[i] or gap[i - 1]:
            fvg_gap += 1
            continue
        fvg_at[i] = {"dir": d, "from_disp": disp[i - 1] == d}
        if atr[i]:
            fvg_sizes.append(((L[i] - H[i - 2]) if d > 0 else (L[i - 2] - H[i])) / atr[i])
    n_disp = sum(1 for x in disp if x)
    out["displacement_fvg"] = {
        "bien_do/ATR": q(ra, (0.5, 0.9, 0.95)), "than/bien_do": q(br, (0.5, 0.9)),
        "displacement": {"ty_le_nen": round(n_disp / N, 4), "moi_ngay": round(n_disp / days, 2)},
        "fvg": {"moi_ngay": round(len(fvg_at) / days, 2), "kich_thuoc/ATR": q(fvg_sizes, (0.5, 0.9)),
                "ty_le_nen_giua_la_displacement": round(
                    sum(f["from_disp"] for f in fvg_at.values()) / len(fvg_at), 3),
                "ung_vien_vat_qua_gap_bi_loai": fvg_gap},
    }

    # ------------------------------------------------ 3. khung lớn (ny_1700) + mức theo kỳ
    hbars = {tf: aggregate(S, tf) for tf in ("H1", "H4", "D", "W", "H4utc", "Dutc")}
    htf_sw, htf_info, htf_atr = {}, {}, {}
    for tf in ("H1", "H4", "D", "H4utc"):
        htf_sw[tf], htf_info[tf], htf_atr[tf] = htf_swings(hbars[tf], tf)
    m15_sw, m15_info = ltf_swings(S)

    def bucket_quality(hb):
        med = st.median(x.n for x in hb)
        lag = [(bars[x.known].close_time - x.end).total_seconds() / 3600 for x in hb]
        return {"so_nen": len(hb), "thieu_so_voi_lich": sum(x.n < x.expected for x in hb),
                "thieu_du_lieu (coverage < 0.9)": sum(x.degraded for x in hb),
                "thua_so_voi_lich": sum(x.over for x in hb),
                "nen_cut (< nửa trung vị)": sum(1 for x in hb if x.n < 0.5 * med),
                "sau_bucket_mat": sum(x.after_hole for x in hb),
                "chot_muon (giờ) — số lần, lớn nhất": [sum(1 for v in lag if v > 0), round(max(lag), 2)]}

    out["moc_nen"] = {tf: bucket_quality(hbars[tf]) for tf in ("H1", "H4", "H4utc", "D", "Dutc", "W")}

    # ------------------------------------------------ 4. vùng thanh khoản: tạo, chạm, lấy
    pools = []
    for s in m15_sw + htf_sw["H1"] + htf_sw["H4"]:
        if s["eff"] < N:
            pools.append({"tier": s["tf"], "side": s["side"], "price": s["price"], "ext": s["ext"],
                          "eff": s["eff"]})
    skipped_period = Counter()
    for tf in ("D", "W"):
        for x in hbars[tf]:
            if x.degraded:
                skipped_period[tf] += 1
                continue
            if x.known + 1 >= N:
                continue
            pools.append({"tier": tf, "side": 1, "price": x.h, "ext": x.high_idx, "eff": x.known + 1})
            pools.append({"tier": tf, "side": -1, "price": x.l, "ext": x.low_idx, "eff": x.known + 1})
    thr_k = CFG["min_pen_atr"]

    def pen(p, k):
        return (H[k] - p["price"]) if p["side"] > 0 else (p["price"] - L[k])

    pre = Counter()
    live = []
    for p in pools:
        p.update(touches=0, taken_t=None, take_pen=None)
        if any(atr[k] and pen(p, k) >= thr_k * atr[k] for k in range(p["ext"] + 1, p["eff"])):
            pre[p["tier"]] += 1      # đã bị lấy trước khi được biết → không thành vùng
            continue
        live.append(p)
    pools = sorted(live, key=lambda p: p["eff"])
    for i, p in enumerate(pools):
        p["id"] = i
    act = {1: [], -1: []}
    ptr = 0
    for t in range(N):
        while ptr < len(pools) and pools[ptr]["eff"] <= t:
            p = pools[ptr]
            ptr += 1
            bisect.insort(act[p["side"]], (p["price"], p["id"]))
        a = atr[t]
        if a is None:
            continue
        lst = act[1]
        j = bisect.bisect_left(lst, (H[t],))
        keep = []
        for price, pid in lst[:j]:
            p = pools[pid]
            pe = H[t] - price
            if pe >= thr_k * a:
                p["taken_t"], p["take_pen"] = t, pe / a
            else:
                p["touches"] += 1
                keep.append((price, pid))
        act[1] = keep + lst[j:]
        lst = act[-1]
        j = bisect.bisect_right(lst, (L[t], float("inf")))
        keep = []
        for price, pid in lst[j:]:
            p = pools[pid]
            pe = price - L[t]
            if pe >= thr_k * a:
                p["taken_t"], p["take_pen"] = t, pe / a
            else:
                p["touches"] += 1
                keep.append((price, pid))
        act[-1] = lst[:j] + keep

    def resolve(p, W):
        """Sweep nếu close quay về phía trong mức ở nến r ∈ [b, b+W], không gap ở (b, r].
        Gặp gap trước khi rõ → unresolved_gap. Hết cửa sổ → run (biết tại b+W)."""
        b = p["taken_t"]
        for r in range(b, min(N, b + W + 1)):
            if r > b and gap[r]:
                return "unresolved_gap", r
            if (C[r] < p["price"]) if p["side"] > 0 else (C[r] > p["price"]):
                return "sweep", r
        return ("run", b + W) if b + W < N else ("het_du_lieu", None)

    taken = [p for p in pools if p["taken_t"] is not None]
    liq = {"vung_bi_lay_truoc_khi_biet (bỏ)": dict(pre), "mua_D_W_bo_vi_thieu_du_lieu": dict(skipped_period)}
    for tier in TIERS:
        ps = [p for p in pools if p["tier"] == tier]
        tk = [p for p in ps if p["taken_t"] is not None]
        row = {"vung": len(ps), "moi_ngay": round(len(ps) / days, 2), "bi_lay": len(tk),
               "chua_bi_lay_cuoi_doan": len(ps) - len(tk),
               "vung_co_cham_nong_truoc_khi_lay": sum(1 for p in ps if p["touches"]),
               "do_xuyen_khi_lay/ATR": q([p["take_pen"] for p in tk], (0.25, 0.5, 0.9))}
        for W in CFG["sweep_windows"]:
            row["W=%d" % W] = dict(Counter(resolve(p, W)[0] for p in tk))
        liq[tier] = row
    out["thanh_khoan"] = liq

    # ------------------------------------------------ 5. shift = sweep → displacement ngược chiều
    def find_shift(p, b, r):
        """Displacement ngược chiều ở d ∈ [r, r+shift_window], không gap ở (r, d], không nến nào
        trong (r, d] vượt cực trị của cú quét (cực trị trên [b, r]), close[d] ở phía trong mức."""
        side, lvl = p["side"], p["price"]
        X = max(H[b:r + 1]) if side > 0 else min(L[b:r + 1])
        for d in range(r, min(N, r + CFG["shift_window"] + 1)):
            if d > r and (gap[d] or ((H[d] > X) if side > 0 else (L[d] < X))):
                return None
            if disp[d] == -side and ((C[d] < lvl) if side > 0 else (C[d] > lvl)):
                return d, X
        return None

    all_kz = Counter(killzone(b.bar_time) for b in bars)
    shift_out, shifts_by_W = {}, {}
    for W in CFG["sweep_windows"]:
        cand = {}
        for p in taken:
            kind, r = resolve(p, W)
            if kind != "sweep":
                continue
            f = find_shift(p, p["taken_t"], r)
            if not f:
                continue
            d, X = f
            key = (d, -p["side"])
            score = (RANK[p["tier"]], p["price"] * p["side"])
            if key not in cand or score > cand[key]["score"]:
                cand[key] = {"d": d, "dir": -p["side"], "b": p["taken_t"], "r": r, "tier": p["tier"],
                             "level": p["price"], "X": X, "score": score,
                             "fvg": (d + 1) in fvg_at and fvg_at[d + 1]["dir"] == -p["side"]}
        sh = sorted(cand.values(), key=lambda s: s["d"])
        shifts_by_W[W] = sh
        kz = Counter(killzone(bars[s["d"]].bar_time) for s in sh)
        shift_out["W=%d" % W] = {
            "so": len(sh), "moi_ngay": round(len(sh) / days, 2),
            "theo_tang_vung_bi_quet": dict(Counter(s["tier"] for s in sh)),
            "co_FVG_tu_chinh_displacement (biết ở d+1)": round(sum(s["fvg"] for s in sh) / max(1, len(sh)), 3),
            "displacement_ngay_nen_quet (d = b)": round(sum(s["d"] == s["b"] for s in sh) / max(1, len(sh)), 3),
            "killzone": shares(kz, max(1, len(sh))),
        }
    shift_out["killzone_moi_nen (để so)"] = shares(all_kz, N)
    out["shift"] = shift_out

    # ------------------------------------------------ 6. ba thành phần bias
    orders = {"M15": order_series(S, m15_sw)}
    for tf in ("H1", "H4", "D", "H4utc"):
        orders[tf] = order_series(S, htf_sw[tf])
    times = [b.close_time for b in bars]
    bias = {}
    for tf, (stt, brk, _) in orders.items():
        rr = runs(stt, times)
        bias["thu_tu_" + tf] = {
            "ty_le_thoi_gian": shares(Counter(stt), N),
            "so_lan_doi": len(rr),
            "thoi_luong_gio (+1/−1)": q([h for s, h in rr if s in (1, -1)], (0.5, 0.9)),
            "dang_+1_hoac_−1_nhung_muc_bao_ve_da_bi_close_vuot": round(
                sum(1 for s, b_ in zip(stt, brk) if s in (1, -1) and b_) / N, 3),
        }
    leak = {}
    for tf in ("H1", "H4"):
        st_leak = order_series(S, htf_sw[tf], eff_key="eff_leak")[0]
        leak[tf] = round(sum(1 for a_, b_ in zip(orders[tf][0], st_leak) if a_ != b_) / N, 4)
    bias["ro_ri_neu_dung_nen_dang_hinh_thanh (tỷ lệ nến khác)"] = leak
    bias["H4_ny1700_vs_utc (tỷ lệ nến thứ tự khác)"] = round(
        sum(1 for a_, b_ in zip(orders["H4"][0], orders["H4utc"][0]) if a_ != b_) / N, 3)

    # PD array: FVG khung lớn, phản ứng đo trên close M15
    pd_events, pd_events_loose, pd_stats = [], [], {}
    for tf in ("H1", "H4"):
        hb, ha = hbars[tf], htf_atr[tf]
        zones = []
        for j in range(2, len(hb)):
            a0, a1, a2 = hb[j - 2], hb[j - 1], hb[j]
            if a1.start != a0.end or a2.start != a1.end or a0.degraded or a1.degraded or a2.degraded:
                continue
            d = 1 if a2.l > a0.h else (-1 if a2.h < a0.l else 0)
            if not d or a2.known + 1 >= N:
                continue
            lo, hi = (a0.h, a2.l) if d > 0 else (a2.h, a0.l)
            r_ = a1.h - a1.l
            mid_disp = bool(ha[j - 1]) and r_ >= CFG["k_disp"] * ha[j - 1] and \
                abs(a1.c - a1.o) >= CFG["body_min"] * r_ and (a1.c - a1.o) * d > 0
            zones.append({"dir": d, "lo": lo, "hi": hi, "eff": a2.known + 1, "mid_disp": mid_disp})
        res_edge, res_ce, res_strict, tap_wait = Counter(), Counter(), Counter(), []
        k_away = CFG["respect_away_atr"]
        for z in zones:
            d, lo, hi = z["dir"], z["lo"], z["hi"]
            ce = (lo + hi) / 2
            tap, oe, oc, os_ = None, None, None, None
            for t in range(z["eff"], N):
                if tap is None:
                    if not ((L[t] <= hi) if d > 0 else (H[t] >= lo)):
                        continue
                    tap = t
                a = atr[t] or 0.0
                if d > 0:
                    if oe is None:
                        oe = ("disrespect", t) if C[t] < lo else (("respect", t) if C[t] > hi else None)
                    if oc is None:
                        oc = ("disrespect", t) if C[t] < ce else (("respect", t) if C[t] > hi else None)
                    if os_ is None:
                        os_ = ("disrespect", t) if C[t] < lo else (
                            ("respect", t) if C[t] >= hi + k_away * a else None)
                else:
                    if oe is None:
                        oe = ("disrespect", t) if C[t] > hi else (("respect", t) if C[t] < lo else None)
                    if oc is None:
                        oc = ("disrespect", t) if C[t] > ce else (("respect", t) if C[t] < lo else None)
                    if os_ is None:
                        os_ = ("disrespect", t) if C[t] > hi else (
                            ("respect", t) if C[t] <= lo - k_away * a else None)
                if oe and oc and os_:
                    break
            if tap is not None:
                tap_wait.append((bars[tap].close_time - bars[z["eff"]].close_time).total_seconds() / 3600)
            for res_c, o_ in ((res_edge, oe), (res_ce, oc), (res_strict, os_)):
                res_c[o_[0] if o_ else ("chua_cham" if tap is None else "dang_cho")] += 1
            if oe:
                pd_events_loose.append((oe[1], d if oe[0] == "respect" else -d, tf))
            if os_:
                pd_events.append((os_[1], d if os_[0] == "respect" else -d, tf))
        pd_stats[tf] = {"so_vung": len(zones), "moi_ngay": round(len(zones) / days, 2),
                        "nen_giua_la_displacement": round(sum(z["mid_disp"] for z in zones) / max(1, len(zones)), 3),
                        "ket_qua (disrespect = close vượt mép xa)": dict(res_edge),
                        "ket_qua (disrespect = close vượt CE 50%)": dict(res_ce),
                        "ket_qua (respect chặt: close rời mép gần ≥ 1 ATR)": dict(res_strict),
                        "gio_tu_khi_biet_toi_khi_cham": q(tap_wait, (0.5, 0.9))}

    def pd_series(events):
        events = sorted(events)
        arr, k_, cur_ = [None] * N, 0, None
        for t in range(N):
            while k_ < len(events) and events[k_][0] <= t:
                cur_ = events[k_][1]
                k_ += 1
            arr[t] = cur_
        return arr

    pd_state = pd_series(pd_events)
    for name, arr in (("pd_bias chặt (H1+H4, sự kiện gần nhất)", pd_state),
                      ("pd_bias lỏng (H1+H4, sự kiện gần nhất)", pd_series(pd_events_loose))):
        rr = runs(arr, times)
        pd_stats[name] = {"ty_le_thoi_gian": shares(Counter(arr), N), "so_lan_doi": len(rr),
                          "thoi_luong_gio": q([h for s, h in rr if s], (0.5, 0.9))}
    bias["pd_array"] = pd_stats

    # DOL: sau mỗi shift (W mặc định), đích = vùng chưa bị lấy gần nhất (tầng ≥ H1) phía shift
    Wd = CFG["default_sweep_window_for_bias"]
    sh = shifts_by_W[Wd]
    dol_state = [None] * N
    dist, tiers_t, no_target = [], Counter(), 0
    for idx, s in enumerate(sh):
        d, di = s["d"], s["dir"]
        cands = [p for p in pools if RANK[p["tier"]] >= RANK[CFG["dol_min_tier"]] and p["side"] == di
                 and p["eff"] <= d and (p["taken_t"] is None or p["taken_t"] > d)
                 and ((p["price"] > C[d]) if di > 0 else (p["price"] < C[d]))]
        nxt = sh[idx + 1]["d"] if idx + 1 < len(sh) else N
        if not cands:
            no_target += 1
            continue
        tgt = min(cands, key=lambda p: abs(p["price"] - C[d]))
        if atr[d]:
            dist.append(abs(tgt["price"] - C[d]) / atr[d])
        tiers_t[tgt["tier"]] += 1
        end = min(nxt, tgt["taken_t"] if tgt["taken_t"] is not None else N)
        for t in range(d + 1, min(end + 1, N)):
            dol_state[t] = di
    bias["dol"] = {"shift_dung": "W=%d" % Wd, "shift_co_dich": len(sh) - no_target,
                   "shift_khong_co_vung_phia_do": no_target,
                   "khoang_cach_toi_dich/ATR": q(dist, (0.25, 0.5, 0.9)),
                   "tang_cua_dich": dict(tiers_t),
                   "ty_le_thoi_gian": shares(Counter(dol_state), N)}

    comps = {"thu_tu_M15": orders["M15"][0], "thu_tu_H1": orders["H1"][0],
             "thu_tu_H4": orders["H4"][0], "pd": pd_state, "dol": dol_state}
    agree = {}
    names = list(comps)
    for i_, a_ in enumerate(names):
        for b_ in names[i_ + 1:]:
            both = [(x, y) for x, y in zip(comps[a_], comps[b_]) if x in (1, -1) and y in (1, -1)]
            agree["%s ~ %s" % (a_, b_)] = [round(sum(x == y for x, y in both) / max(1, len(both)), 3), len(both)]
    for o in ("thu_tu_H1", "thu_tu_H4"):
        tri = Counter()
        for x, y, z in zip(comps[o], pd_state, dol_state):
            vals = [v for v in (x, y, z) if v in (1, -1)]
            tri["du_3_cung_chieu" if len(vals) == 3 and len(set(vals)) == 1 else
                ("du_3_mau_thuan" if len(vals) == 3 else "thieu_thanh_phan")] += 1
        agree["%s + pd + dol" % o] = shares(tri, N)
    bias["dong_thuan [ty_le, so_nen_ca_hai_co_chieu]"] = agree
    out["bias"] = bias

    # ------------------------------------------------ 7. shift so với ngữ cảnh khung lớn
    ctx = {}
    for name in ("thu_tu_H1", "thu_tu_H4", "pd", "dol"):
        arr = comps[name]
        share_t = Counter(arr)
        hit = sum(1 for s in sh if s["d"] > 0 and arr[s["d"] - 1] == s["dir"])
        exp = sum(share_t[s["dir"]] / N for s in sh)
        ctx[name] = {"cung_chieu": round(hit / max(1, len(sh)), 3), "ngau_nhien": round(exp / max(1, len(sh)), 3),
                     "n": len(sh)}
    for tf in ("H1", "H4"):
        rng = orders[tf][2]
        lows_disc = highs_prem = nb = 0
        for t in range(1, N):
            r_ = rng[t - 1]
            if not r_:
                continue
            lo, hi = r_
            nb += 1
            lows_disc += (L[t] - lo) / (hi - lo) < 0.5
            highs_prem += (H[t] - lo) / (hi - lo) > 0.5
        good = n_ = 0
        exp = 0.0
        for s in sh:
            r_ = rng[s["b"] - 1] if s["b"] > 0 else None
            if not r_:
                continue
            lo, hi = r_
            pos = (s["X"] - lo) / (hi - lo)
            n_ += 1
            good += (pos < 0.5) if s["dir"] > 0 else (pos > 0.5)
            exp += (lows_disc if s["dir"] > 0 else highs_prem) / nb
        ctx["vi_tri_cuc_tri_quet_trong_dealing_range_" + tf] = {
            "dung_phia (tăng ở discount / giảm ở premium)": round(good / max(1, n_), 3),
            "ngau_nhien": round(exp / max(1, n_), 3), "n": n_}
    out["shift_vs_khung_lon (W=%d, trạng thái ở nến d−1 / b−1)" % Wd] = ctx

    # ------------------------------------------------ 8. hồ sơ khung
    def profile(series_h, series_l, series_atr, sw_list, sth_n, tf_hours, close_times, lag_wall, d_count):
        seq = sorted([(s["c"], s["price"], s["side"]) for s in sw_list])
        amp_usd, amp_atr = [], []
        for (c1, p1, s1), (c2, p2, s2) in zip(seq, seq[1:]):
            if s1 != s2:
                amp_usd.append(abs(p2 - p1))
                if series_atr[c2]:
                    amp_atr.append(abs(p2 - p1) / series_atr[c2])
        return {"STH_STL_moi_ngay": round(sth_n / d_count, 2),
                "ITH_ITL_moi_ngay": round(len(sw_list) / d_count, 2),
                "tre_nen_khung": q([s["conf"] - s["c"] for s in sw_list], (0.5, 0.9)),
                "tre_gio_dong_ho": q(lag_wall, (0.5, 0.9)),
                "bien_do_USD": q(amp_usd, (0.5,)), "bien_do_ATR_khung": q(amp_atr, (0.5,))}

    prof = {}
    if args.m5_dataset:
        ds5, rows5, bars5 = load(con, args.m5_dataset, args.start, args.end)
        S5 = Series(bars5, ds5["timeframe"])
        sw5, info5 = ltf_swings(S5, "M5")
        d5 = len({trading_day(b.bar_time) for b in bars5})
        prof["M5"] = profile(S5.H, S5.L, S5.atr, sw5, info5["sth"] + info5["stl"], 5 / 60, None,
                             [(bars5[s["conf"]].close_time - bars5[s["c"]].close_time).total_seconds() / 3600
                              for s in sw5], d5)
        prof["M5"]["dataset"] = {"id": ds5["id"], "checksum_sha256": ds5["checksum_sha256"],
                                 "checksum_doan": rows_checksum(rows5)}
    prof["M15"] = profile(H, L, atr, m15_sw, m15_info["sth"] + m15_info["stl"], 0.25, None,
                          [(bars[s["conf"]].close_time - bars[s["c"]].close_time).total_seconds() / 3600
                           for s in m15_sw], days)
    for tf in ("H1", "H4", "D"):
        hb = hbars[tf]
        prof[tf] = profile([x.h for x in hb], [x.l for x in hb], htf_atr[tf], htf_sw[tf],
                           htf_info[tf]["sth"] + htf_info[tf]["stl"], None, None,
                           [(bars[s["known"]].close_time - hb[s["c"]].end).total_seconds() / 3600
                            for s in htf_sw[tf]], days)
        prof[tf]["cua_so_pivot_bi_chan_vi_du_lieu"] = htf_info[tf]["cua_so_bi_chan"]
    out["ho_so_khung"] = prof

    # ------------------------------------------------ 9. ví dụ để tự kiểm (6 shift đầu tháng 3)
    ex = []
    for s in shifts_by_W[Wd]:
        bb, bd = bars[s["b"]], bars[s["d"]]
        if bb.bar_time.month != 3:
            continue
        ex.append({"quet": "BSL (đỉnh)" if s["dir"] < 0 else "SSL (đáy)", "tang": s["tier"],
                   "muc": round(s["level"], 2),
                   "nen_quet_UTC": bb.bar_time.strftime("%Y-%m-%d %H:%M"),
                   "nen_quet_NY": ny(bb.bar_time).strftime("%H:%M"),
                   "nen_quet_HLC": [bb.high, bb.low, bb.close],
                   "displacement_UTC": bd.bar_time.strftime("%Y-%m-%d %H:%M"),
                   "displacement_OC": [bd.open, bd.close], "fvg": s["fvg"]})
        if len(ex) >= 6:
            break
    out["vi_du_thang_3"] = ex

    text = json.dumps(out, ensure_ascii=False, indent=1, default=str)
    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            f.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
