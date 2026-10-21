"""Hình minh hoạ ba trạng thái đi ngang (plan_nhan_dien_trang_thai.md §3) trên dữ liệu thật — CHỈ ĐỌC database.

Vẽ ba đoạn XAUUSD M15 thuộc đoạn phát triển (trước 2024-09-01), giờ New York:

1. **Range có biên rõ** — trong cửa sổ W nến, mỗi biên (high cao nhất / low thấp nhất) bị chạm ≥ 2 lần; một lần chạm
   là một swing (pivot 2/2) nằm trong 0,3·ATR của biên; hai lần chạm cách nhau ≥ 6 nến; bề rộng 1,5–5 ATR; ER < 0,3.
2. **Sideway nhiễu** — ER < 0,25 nhưng mỗi biên chỉ bị chạm 1 lần: đỉnh/đáy rải rác, không cụm lại quanh mức nào.
3. **Sideway đang nén** — đỉnh swing thấp dần, đáy swing cao dần, bề rộng cuối ≤ 50% bề rộng đầu.

Ngưỡng là bản đầu để minh hoạ định nghĩa; bước 3 của plan kiểm lại bằng nhãn tay. Ba đoạn được chọn từ danh sách
ứng viên do chính luật trên sinh ra (mốc thời gian ghi cố định bên dưới để tái lập).

Cần ``matplotlib`` (không có trong ``.venv`` của lab — chạy bằng một Python có matplotlib, pandas, numpy)::

    python research\\vi_du_range_sideway.py --out docs\\research\\khao_sat\\range_sideway.png
"""
from __future__ import annotations

import argparse
import os
import sqlite3

import numpy as np
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.environ.get("MSL_DB_PATH") or os.path.join(ROOT, "data", "lab.sqlite")
DATASET = "ds_a5212fd37814"          # XAUUSD M15 2018–2025, HistData bid, giờ đã sửa
DOAN_KIEM_TRA = "2024-09-01"
VI_DU = {                              # (mốc mở đoạn theo giờ NY, số nến W)
    "range": ("2023-01-09 21:00", 48),
    "noise": ("2023-02-15 03:00", 48),
    "squeeze": ("2023-12-06 01:15", 48),
}
UP, DOWN, LINE, MUTED, ACC = "#1d7466", "#b4532a", "#17201d", "#7a8a84", "#946708"


def load():
    uri = "file:%s?mode=ro" % DB_PATH.replace("\\", "/")
    con = sqlite3.connect(uri, uri=True)
    df = pd.read_sql("select bar_time, open, high, low, close from bars where dataset_id = ? and bar_time >= '2023-01-01' "
                     "and bar_time < ? order by idx", con, params=(DATASET, DOAN_KIEM_TRA))
    df["t"] = pd.to_datetime(df.bar_time, utc=True).dt.tz_convert("America/New_York")
    return df


def prepare(df):
    o, h, l, c = (df[k].to_numpy() for k in ("open", "high", "low", "close"))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.where(np.isnan(pc), h - l, np.maximum.reduce([h - l, np.abs(h - pc), np.abs(l - pc)]))
    atr = pd.Series(tr).ewm(alpha=1 / 14, adjust=False).mean().to_numpy()
    n = len(df)
    sh, sl = np.zeros(n, bool), np.zeros(n, bool)
    for i in range(2, n - 2):
        sh[i] = h[i] == h[i - 2:i + 3].max() and h[i] > h[i - 2:i].max() and h[i] >= h[i + 1:i + 3].max()
        sl[i] = l[i] == l[i - 2:i + 3].min() and l[i] < l[i - 2:i].min() and l[i] <= l[i + 1:i + 3].min()
    return o, h, l, c, atr, sh, sl


def touches(idx, level, side, tol, h, l):
    keep = []
    for j in idx:
        hit = h[j] >= level - tol if side > 0 else l[j] <= level + tol
        if hit and (not keep or j - keep[-1] >= 6):
            keep.append(j)
    return keep


def candles(ax, df, o, h, l, c, s0, e0):
    from matplotlib.patches import Rectangle
    for k, j in enumerate(range(s0, e0)):
        col = UP if c[j] >= o[j] else DOWN
        ax.vlines(k, l[j], h[j], color=col, lw=0.8)
        lo, hi = sorted((o[j], c[j]))
        ax.add_patch(Rectangle((k - 0.32, lo), 0.64, max(hi - lo, 0.02), facecolor=col, edgecolor=col, lw=0.6))
    ticks = list(range(0, e0 - s0, 8))
    ax.set_xticks(ticks)
    ax.set_xticklabels([df.t[s0 + k].strftime("%H:%M") for k in ticks], fontsize=8, color=MUTED)
    ax.tick_params(axis="y", labelsize=8, colors=MUTED)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.set_xlim(-1, e0 - s0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "research", "khao_sat", "range_sideway.png"))
    args = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = load()
    o, h, l, c, atr, sh, sl = prepare(df)
    fig, axes = plt.subplots(3, 1, figsize=(11, 12.5))
    for ax, kind in zip(axes, ("range", "noise", "squeeze")):
        start, W = VI_DU[kind]
        s = int(np.flatnonzero(df.t.dt.strftime("%Y-%m-%d %H:%M") == start)[0])
        e = s + W
        a = atr[e - 1]
        his = [j for j in range(s + 2, e - 2) if sh[j]]
        los = [j for j in range(s + 2, e - 2) if sl[j]]
        s0, e0 = s - 16, min(len(df), e + 16)
        candles(ax, df, o, h, l, c, s0, e0)
        ax.axvspan(s - s0 - 0.5, e - s0 - 0.5, color=MUTED, alpha=0.08, lw=0)
        if kind == "range":
            U, D = h[s:e].max(), l[s:e].min()
            tu, td = touches(his, U, +1, 0.3 * a, h, l), touches(los, D, -1, 0.3 * a, h, l)
            ax.hlines([U, D], s - s0 - 0.5, e - s0 - 0.5, colors=ACC, linestyles="--", lw=1.4)
            ax.text(s - s0, U, "  biên trên ≈ %.1f" % U, va="bottom", fontsize=9, color=ACC)
            ax.text(s - s0, D, "  biên dưới ≈ %.1f" % D, va="top", fontsize=9, color=ACC)
            ax.scatter([j - s0 for j in tu], [h[j] for j in tu], s=70, facecolors="none", edgecolors=ACC, lw=1.6, zorder=5)
            ax.scatter([j - s0 for j in td], [l[j] for j in td], s=70, facecolors="none", edgecolors=ACC, lw=1.6, zorder=5)
            rong = ("%.1f" % ((U - D) / a)).replace(".", ",")
            title = "1. RANGE CÓ BIÊN RÕ  ·  %s  ·  mỗi biên bị chạm ≥ 2 lần (vòng tròn), rộng %s ATR" % (df.t[s].strftime("%d/%m/%Y"), rong)
        elif kind == "noise":
            ax.scatter([j - s0 for j in his], [h[j] for j in his], marker="v", s=40, color=MUTED, zorder=5)
            ax.scatter([j - s0 for j in los], [l[j] for j in los], marker="^", s=40, color=MUTED, zorder=5)
            title = "2. SIDEWAY NHIỄU  ·  %s  ·  cũng đi ngang, nhưng đỉnh/đáy rải rác, không cụm lại quanh mức nào" % df.t[s].strftime("%d/%m/%Y")
        else:
            ax.plot([j - s0 for j in his], [h[j] for j in his], color=ACC, lw=1.4, ls="--", marker="v", ms=6)
            ax.plot([j - s0 for j in los], [l[j] for j in los], color=ACC, lw=1.4, ls="--", marker="^", ms=6)
            title = "3. SIDEWAY ĐANG NÉN  ·  %s  ·  đỉnh thấp dần, đáy cao dần, biên độ co lại" % df.t[s].strftime("%d/%m/%Y")
        ax.set_title(title, loc="left", fontsize=11, color=LINE, pad=8)
    fig.text(0.01, 0.005, "XAUUSD M15, giờ New York. Vùng nền xám = đoạn được nhận diện; 16 nến trước và sau để thấy bối cảnh.",
             fontsize=9, color=MUTED)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    fig.savefig(args.out, dpi=130)
    print("Đã lưu", args.out)


if __name__ == "__main__":
    main()
