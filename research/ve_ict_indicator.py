"""Vẽ hình cho khảo sát indicator + ICT (``research/ict_indicator_survey.py``) từ file JSON kết quả.

Chỉ đọc JSON, không đọc database. Cần ``matplotlib`` (không có trong ``.venv`` của lab — chạy bằng một Python có
matplotlib và numpy)::

    python research\\ve_ict_indicator.py --json docs\\research\\khao_sat\\ict_indicator_dev.json --out docs\\research\\khao_sat

Sáu hình:

1. ``ict_ind_1_huong.png`` — đúng hướng cân bằng 1h/4h của từng tín hiệu và từng kết hợp luật;
2. ``ict_ind_2_so_voi_cha.png`` — kết hợp có hơn tín hiệu ICT «cha» của nó không;
3. ``ict_ind_3_theo_nam.png`` — độ ổn định theo năm (4h);
4. ``ict_ind_4_mo_hinh.png`` — kết hợp học (walk-forward): hướng, trạng thái một chiều, dải giá 80%;
5. ``ict_ind_5_vung_ict.png`` — vùng thanh khoản ICT có hút giá hơn mức bất kỳ không;
6. ``ict_ind_6_vi_du.png`` — một đoạn XAUUSD M15 thật với sự kiện ICT, indicator và dự báo ngoài mẫu.
"""
from __future__ import annotations

import argparse
import json
import math
import os

import numpy as np

UP, DOWN, LINE, MUTED, ACC = "#1d7466", "#b4532a", "#17201d", "#7a8a84", "#946708"
SYM_COL = {"XAUUSD": "#946708", "EURUSD": "#2f6db5"}
MODEL_COL = {"B0": "#c9d1cd", "B1": "#a9b4af", "NEN": "#7a8a84", "NEN+IND": "#2f6db5", "NEN+ICT": "#c07a12",
             "NEN+CA_HAI": "#1d7466"}
MODEL_TEN = {"B0": "B0 không điều kiện", "B1": "B1 theo giờ", "NEN": "Nền", "NEN+IND": "Nền + indicator",
             "NEN+ICT": "Nền + ICT", "NEN+CA_HAI": "Nền + cả hai"}
GROUP_TEN = {"ICT": "ICT (một tín hiệu)", "IND": "Indicator (một tín hiệu)", "K": "Kết hợp ICT + indicator (luật)"}


def vn(x, d=1):
    """Số kiểu Việt Nam: dấu phẩy thập phân."""
    return ("%.*f" % (d, x)).replace(".", ",")


def style(ax):
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(axis="x", color="#e6ebe8", lw=0.6)
    ax.set_axisbelow(True)


def head(fig, title, sub):
    """Tiêu đề + dòng giải thích, đặt theo inch để không chồng nhau; trả về mép trên cho tight_layout."""
    H = fig.get_size_inches()[1]
    fig.suptitle(title, x=0.01, y=1 - 0.2 / H, ha="left", va="top", fontsize=13, color=LINE)
    fig.text(0.01, 1 - 0.55 / H, sub, fontsize=9, color=MUTED, va="top", linespacing=1.5)
    return 1 - (0.8 + 0.2 * sub.count("\n")) / H


def boot_bh(J):
    """Kiểm thêm (thêm 21/10/2026 SAU lần chạy đầu): null dịch vòng 199 độ dịch cho p nhỏ nhất 0,005 nên BH trên 148
    phép thử gần như không thể qua. Ở đây dùng p hai phía từ bootstrap, z = (BA − 0,5) / SE, rồi BH trên toàn bộ phép
    thử. SE bootstrap theo tuần có thể thấp hơn thật với tín hiệu kéo dài nhiều tuần → coi là gợi ý, không phải kết luận."""
    refs = []
    for sym, R in J["ket_qua"].items():
        for h, A in R["A"].items():
            for k, t in A["tin_hieu"].items():
                if t.get("du_mau") and t.get("se"):
                    refs.append(((sym, h, k), math.erfc(abs(t["ba"] - 0.5) / t["se"] / math.sqrt(2))))
    n = len(refs)
    order = sorted(range(n), key=lambda i: refs[i][1])
    q, prev = [1.0] * n, 1.0
    for rank in range(n - 1, -1, -1):
        i = order[rank]
        prev = min(prev, refs[i][1] * n / (rank + 1))
        q[i] = prev
    return {refs[i][0]: q[i] for i in range(n)}


def rows_spec(J):
    out = []
    for g in ("ICT", "IND"):
        for k, v in J["tin_hieu"].items():
            if v["nhom"] == g:
                out.append((g, k, v["mo_ta"]))
    for k, v in J["ket_hop"].items():
        out.append(("K", k, "%s · %s" % (k, v["mo_ta"])))
    return out


def ypos(rows, gap=1.2):
    ys, y, prev = {}, 0.0, None
    heads = []
    for g, k, _t in rows:
        if prev is not None and g != prev:
            y += gap
        if g != prev:
            heads.append((g, y))
            y += 0.9
        ys[k] = y
        y += 1.0
        prev = g
    return ys, heads, y


# ---------------------------------------------------------------- hình 1


def fig_huong(J, out, plt):
    syms = [s for s in ("XAUUSD", "EURUSD") if s in J["ket_qua"]]
    rows = rows_spec(J)
    ys, heads, ymax = ypos(rows)
    cost = J["meta"]["tham_so"]["chi_phi_atr"]
    qb = boot_bh(J)
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 14), sharey=True)
    for ax, h in zip(axes, ("1h", "4h")):
        style(ax)
        lo_be = min((1 + cost[s]) / 2 * 100 for s in syms)
        hi_be = max((1 + cost[s]) / 2 * 100 for s in syms)
        ax.axvspan(lo_be, hi_be + 0.15, color=DOWN, alpha=0.13, lw=0)
        ax.text((lo_be + hi_be) / 2, -1.2, "hoà vốn\nsau phí", ha="center", va="bottom", fontsize=8, color=DOWN)
        ax.axvline(50, color=MUTED, lw=1, ls="--")
        for si, sym in enumerate(syms):
            A = J["ket_qua"][sym]["A"][h]["tin_hieu"]
            off = -0.2 if si == 0 else 0.2
            col = SYM_COL[sym]
            for _g, k, _t in rows:
                r = A[k]
                if not r.get("du_mau"):
                    continue
                y = ys[k] + off
                lo, hi = (v * 100 for v in r["ci95"])
                ax.hlines(y, lo, hi, color=col, lw=1.5, alpha=0.9)
                ax.plot(r["ba"] * 100, y, marker="o" if si == 0 else "D", ms=5 if si == 0 else 4.5,
                        mfc=col if si == 0 else "white", mec=col, mew=1.3, zorder=4)
                if r.get("vuot_null"):
                    ax.text(hi + 0.15, y, "★", fontsize=8.5, color=col, va="center")
                elif qb.get((sym, h, k), 1.0) < 0.05:
                    ax.text(hi + 0.15, y, "†", fontsize=9.5, color=col, va="center", fontweight="bold")
        for g, y in heads:
            ax.text(44.2, y, GROUP_TEN[g].upper(), fontsize=8.5, color=LINE, fontweight="bold", va="center")
        ax.set_xlim(44, 61)
        ax.set_title("Tầm %s tới" % ("1 giờ" if h == "1h" else "4 giờ"), fontsize=11, color=LINE, loc="left")
        ax.set_xlabel("Đúng hướng cân bằng (%) — 50% = đoán mò", fontsize=9, color=MUTED)
    A4 = J["ket_qua"][syms[0]]["A"]["4h"]["tin_hieu"]
    axes[0].set_yticks([ys[k] for _g, k, _t in rows])
    axes[0].set_yticklabels(["%s   (phủ %d%%)" % (t, round(100 * (A4[k].get("phu") or 0))) for _g, k, t in rows],
                            fontsize=8.3, color=LINE)
    axes[0].set_ylim(ymax + 0.3, -1.6)
    from matplotlib.lines import Line2D
    hs = [Line2D([], [], color=SYM_COL[s], marker="o" if i == 0 else "D", mfc=SYM_COL[s] if i == 0 else "white",
                 lw=1.5, label=s) for i, s in enumerate(syms)]
    hs.append(Line2D([], [], color=LINE, marker="$★$", lw=0, ms=8, label="vượt null dịch vòng + BH (luật khai trước)"))
    hs.append(Line2D([], [], color=LINE, marker="$†$", lw=0, ms=8, label="chỉ qua BH khi dùng p bootstrap (kiểm thêm)"))
    fig.legend(handles=hs, loc="lower center", ncol=4, fontsize=8.5, frameon=False)
    top = head(fig, "Đoán hướng: chạm +1 ATR trước hay −1 ATR trước trong 1 giờ / 4 giờ tới  ·  M15, 2018 – 08/2024",
               "Chấm = ước lượng, thanh = CI 95% (bootstrap theo tuần). «Phủ» = tỷ lệ nến tín hiệu có ý kiến "
               "(XAUUSD, 4h). Vùng đỏ = mức đúng hướng cần có để hoà vốn sau phí với rào ±1 ATR M15.")
    fig.tight_layout(rect=(0, 0.025, 1, top))
    fig.savefig(os.path.join(out, "ict_ind_1_huong.png"), dpi=125)
    plt.close(fig)


# ---------------------------------------------------------------- hình 2


def fig_so_voi_cha(J, out, plt):
    syms = [s for s in ("XAUUSD", "EURUSD") if s in J["ket_qua"]]
    keys = list(J["ket_hop"])
    names = {**{k: v["mo_ta"] for k, v in J["tin_hieu"].items()}, **{k: k for k in J["ket_hop"]}}
    fig, axes = plt.subplots(1, 2, figsize=(14, 7.6), sharey=True)
    for ax, h in zip(axes, ("1h", "4h")):
        style(ax)
        ax.axvline(0, color=MUTED, lw=1, ls="--")
        for si, sym in enumerate(syms):
            A = J["ket_qua"][sym]["A"][h]["tin_hieu"]
            col = SYM_COL[sym]
            off = -0.17 if si == 0 else 0.17
            for i, k in enumerate(keys):
                c = A[k].get("so_voi_cha")
                if not c:
                    continue
                lo, hi = (v * 100 for v in c["ci95"])
                ax.hlines(i + off, lo, hi, color=col, lw=1.5)
                ax.plot(c["chenh"] * 100, i + off, marker="o" if si == 0 else "D", ms=5 if si == 0 else 4.5,
                        mfc=col if si == 0 else "white", mec=col, mew=1.3, zorder=4)
                if c.get("hon_cha"):
                    ax.text(hi + 0.1, i + off, "★", fontsize=8.5, color=col, va="center")
        ax.set_title("Tầm %s tới" % ("1 giờ" if h == "1h" else "4 giờ"), fontsize=11, color=LINE, loc="left")
        ax.set_xlabel("Chênh đúng hướng so với tín hiệu «cha» (điểm %)", fontsize=9, color=MUTED)
    A4 = J["ket_qua"][syms[0]]["A"]["4h"]["tin_hieu"]
    labels = []
    for k in keys:
        par = J["ket_hop"][k]["cha"]
        labels.append("%s · %s\n      so với: %s   (phủ %d%% → %d%%)" % (
            k, J["ket_hop"][k]["mo_ta"], names[par] if par in J["tin_hieu"] else par + " · " + J["ket_hop"][par]["mo_ta"],
            round(100 * (A4[par].get("phu") or 0)), round(100 * (A4[k].get("phu") or 0))))
    axes[0].set_yticks(range(len(keys)))
    axes[0].set_yticklabels(labels, fontsize=7.8, color=LINE)
    axes[0].set_ylim(len(keys) - 0.4, -0.6)
    from matplotlib.lines import Line2D
    hs = [Line2D([], [], color=SYM_COL[s], marker="o" if i == 0 else "D", mfc=SYM_COL[s] if i == 0 else "white",
                 lw=1.5, label=s) for i, s in enumerate(syms)]
    hs.append(Line2D([], [], color=LINE, marker="$★$", lw=0, ms=8, label="hơn cha: p null < 0,05 và CI > 0"))
    fig.legend(handles=hs, loc="lower center", ncol=3, fontsize=8.5, frameon=False)
    top = head(fig, "Thêm điều kiện indicator vào tín hiệu ICT có làm đoán hướng tốt hơn không?",
               "Mỗi dòng: kết hợp (luật) trừ tín hiệu «cha» của nó, trên cùng các tuần (bootstrap ghép cặp). "
               "> 0 = kết hợp đúng hướng hơn; đổi lại độ phủ giảm (số trong ngoặc, XAUUSD 4h).\n"
               "★ chưa hiệu chỉnh nhiều phép thử: 64 phép so cặp thì ngẫu nhiên cũng có khoảng 3 dấu ★.")
    fig.tight_layout(rect=(0, 0.04, 1, top))
    fig.savefig(os.path.join(out, "ict_ind_2_so_voi_cha.png"), dpi=125)
    plt.close(fig)


# ---------------------------------------------------------------- hình 3


def fig_theo_nam(J, out, plt):
    from matplotlib.colors import LinearSegmentedColormap
    syms = [s for s in ("XAUUSD", "EURUSD") if s in J["ket_qua"]]
    rows = rows_spec(J)
    years = sorted({y for s in syms for r in J["ket_qua"][s]["A"]["4h"]["tin_hieu"].values()
                    for y in (r.get("theo_nam") or {})})
    cmap = LinearSegmentedColormap.from_list("bd", [DOWN, "#f7f7f2", UP])
    fig, axes = plt.subplots(1, len(syms), figsize=(13.5, 13), sharey=True)
    axes = np.atleast_1d(axes)
    for ax, sym in zip(axes, syms):
        A = J["ket_qua"][sym]["A"]["4h"]["tin_hieu"]
        Z = np.full((len(rows), len(years)), np.nan)
        for i, (_g, k, _t) in enumerate(rows):
            tn = A[k].get("theo_nam") or {}
            for j, y in enumerate(years):
                v = tn.get(y)
                if v is not None:
                    Z[i, j] = (v - 0.5) * 100
        ax.imshow(Z, cmap=cmap, vmin=-6, vmax=6, aspect="auto")
        for i in range(Z.shape[0]):
            for j in range(Z.shape[1]):
                if np.isfinite(Z[i, j]):
                    ax.text(j, i, vn(Z[i, j], 1), ha="center", va="center", fontsize=6.6,
                            color="white" if abs(Z[i, j]) > 4 else LINE)
        ax.set_xticks(range(len(years)))
        ax.set_xticklabels([y if y != "2024" else "2024\n(01–08)" for y in years], fontsize=8, color=MUTED)
        ax.set_title(sym, fontsize=11, color=LINE, loc="left")
        for sp in ax.spines.values():
            sp.set_visible(False)
        b = [i for i in range(1, len(rows)) if rows[i][0] != rows[i - 1][0]]
        for i in b:
            ax.axhline(i - 0.5, color="white", lw=3)
    axes[0].set_yticks(range(len(rows)))
    axes[0].set_yticklabels([t for _g, _k, t in rows], fontsize=8, color=LINE)
    top = head(fig, "Đúng hướng 4 giờ theo từng năm: lệch so với 50% (điểm %)",
               "Xanh = đúng hướng hơn đoán mò, cam = kém hơn. Một tín hiệu dùng được phải xanh đều qua các năm, không "
               "chỉ trung bình dương nhờ một hai năm. Ô trống = năm đó có < 200 nến mỗi phía.")
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(os.path.join(out, "ict_ind_3_theo_nam.png"), dpi=125)
    plt.close(fig)


# ---------------------------------------------------------------- hình 4


def fig_mo_hinh(J, out, plt):
    syms = [s for s in ("XAUUSD", "EURUSD") if s in J["ket_qua"]]
    models = ("NEN", "NEN+IND", "NEN+ICT", "NEN+CA_HAI")
    fig, axes = plt.subplots(len(syms), 3, figsize=(15, 4.6 * len(syms)))
    axes = np.atleast_2d(axes)
    for r, sym in enumerate(syms):
        B = J["ket_qua"][sym]["B"]
        for c, target in enumerate(("huong", "mot_chieu")):
            ax = axes[r, c]
            style(ax)
            ax.grid(axis="y", color="#e6ebe8", lw=0.6)
            ax.grid(axis="x", visible=False)
            ax.axhline(0.5, color=MUTED, lw=1, ls="--")
            for gi, h in enumerate(("1h", "4h")):
                R = B[h][target]["mo_hinh"]
                for mi, m in enumerate(models):
                    x = gi * 5 + mi
                    v, (lo, hi) = R[m]["auc"], R[m]["ci95"]
                    ax.bar(x, v - 0.5, bottom=0.5, color=MODEL_COL[m], width=0.8)
                    ax.errorbar(x, v, yerr=[[v - lo], [hi - v]], color=LINE, lw=1, capsize=2.5)
                    ax.text(x, max(hi, 0.5) + 0.002, vn(v, 3), ha="center", va="bottom", fontsize=7, color=LINE)
            ax.set_xticks([1.5, 6.5])
            ax.set_xticklabels(["1 giờ tới", "4 giờ tới"], fontsize=9, color=LINE)
            ax.set_ylim(0.47, 0.6 if target == "mot_chieu" else 0.56)
            ax.set_ylabel("AUC ngoài mẫu (0,5 = đoán mò)", fontsize=8.5, color=MUTED)
            ttl = "Hướng (+1 ATR trước −1 ATR)" if target == "huong" else "Trạng thái «đi một chiều» (ER tương lai cao)"
            ax.set_title("%s · %s" % (sym, ttl), fontsize=10.5, color=LINE, loc="left")
        ax = axes[r, 2]
        style(ax)
        ax.grid(axis="y", color="#e6ebe8", lw=0.6)
        ax.grid(axis="x", visible=False)
        mm = ("B1",) + models
        for gi, h in enumerate(("1h", "4h")):
            R = B[h]["dai_gia"]["mo_hinh"]
            for mi, m in enumerate(mm):
                x = gi * 6 + mi
                v, (lo, hi) = R[m]["skill_vs_B0"] * 100, (q * 100 for q in R[m]["skill_ci95"])
                ax.bar(x, v, color=MODEL_COL[m], width=0.8)
                ax.errorbar(x, v, yerr=[[v - lo], [hi - v]], color=LINE, lw=1, capsize=2.5)
                ax.text(x, hi + 0.3, vn(v, 1), ha="center", va="bottom", fontsize=7, color=LINE)
        ax.set_xticks([2, 8])
        ax.set_xticklabels(["1 giờ tới", "4 giờ tới"], fontsize=9, color=LINE)
        ax.set_ylabel("Điểm tốt hơn B0 (% pinball, cao = tốt)", fontsize=8.5, color=MUTED)
        ax.set_ylim(0, max(25, ax.get_ylim()[1] + 3))
        cov = [B[h]["dai_gia"]["mo_hinh"][m]["phu_chung"] * 100 for h in ("1h", "4h") for m in mm]
        ax.set_title("%s · Dải giá 80%% (thực tế phủ %d–%d%%)" % (sym, math.floor(min(cov)), math.ceil(max(cov))),
                     fontsize=10.5, color=LINE, loc="left")
    from matplotlib.patches import Patch
    hs = [Patch(color=MODEL_COL[m], label=MODEL_TEN[m]) for m in ("B1",) + models]
    fig.legend(handles=hs, loc="lower center", ncol=5, fontsize=9, frameon=False)
    top = head(fig, "Kết hợp bằng mô hình học (cây tăng cường, walk-forward: học các năm trước, chấm năm sau, "
                    "2020 – 08/2024)",
               "«Nền» = giờ trong ngày, thứ, biên độ và lợi suất 1h/4h gần nhất, ATR so với 10 ngày. Chỉ khi cột cao "
               "hơn «Nền» và thanh lỗi tách hẳn thì ICT / indicator mới có thêm thông tin.")
    fig.tight_layout(rect=(0, 0.04, 1, top))
    fig.savefig(os.path.join(out, "ict_ind_4_mo_hinh.png"), dpi=125)
    plt.close(fig)


# ---------------------------------------------------------------- hình 5


def fig_vung(J, out, plt):
    syms = [s for s in ("XAUUSD", "EURUSD") if s in J["ket_qua"]]
    fig, axes = plt.subplots(2, 2, figsize=(14, 8.6), sharex=True)
    side_ten = {"tren": "vùng phía trên", "duoi": "vùng phía dưới"}
    for c, h in enumerate(("1h", "4h")):
        ax0, ax1 = axes[0, c], axes[1, c]
        for ax in (ax0, ax1):
            style(ax)
            ax.grid(axis="y", color="#e6ebe8", lw=0.6)
        ax1.axhline(0, color=MUTED, lw=1, ls="--")
        k = 0
        for sym in syms:
            for side in ("tren", "duoi"):
                R = J["ket_qua"][sym]["C"][h][side]["theo_khoang_cach"]
                pts = [(i, x) for i, x in enumerate(R) if "thuc_te" in x]
                xs = np.array([i for i, _x in pts], float)
                col = SYM_COL[sym]
                ls = "-" if side == "tren" else ":"
                mk = "o" if side == "tren" else "s"
                ax0.plot(xs, [x["thuc_te"] * 100 for _i, x in pts], color=col, ls=ls, marker=mk, ms=4.5,
                         label="%s · %s · thực tế" % (sym, side_ten[side]))
                ax0.plot(xs, [x["ky_vong"] * 100 for _i, x in pts], color=col, ls=ls, lw=0.8, alpha=0.6,
                         marker="x", ms=4, label="%s · %s · mức bất kỳ" % (sym, side_ten[side]))
                off = (k - 1.5) * 0.12
                for i, x in pts:
                    lo, hi = (v * 100 for v in x["ci95"])
                    ax1.vlines(i + off, lo, hi, color=col, lw=1.4)
                    ax1.plot(i + off, x["chenh"] * 100, marker=mk, ms=4.5, color=col,
                             mfc=col if side == "tren" else "white")
                k += 1
        ax0.set_title("Tầm %s tới · xác suất chạm vùng ICT gần nhất" % ("1 giờ" if h == "1h" else "4 giờ"),
                      fontsize=10.5, color=LINE, loc="left")
        ax0.set_ylabel("Xác suất chạm (%)", fontsize=8.5, color=MUTED)
        ax1.set_title("Chênh: vùng ICT − mức bất kỳ cùng khoảng cách (điểm %, CI 95%)", fontsize=10, color=LINE,
                      loc="left")
        ax1.set_ylabel("Chênh (điểm %)", fontsize=8.5, color=MUTED)
        R = J["ket_qua"][syms[0]]["C"][h]["tren"]["theo_khoang_cach"]
        ax1.set_xticks(range(len(R)))
        ax1.set_xticklabels(["%s–%s ATR" % (vn(x["tu"], 1), vn(x["den"], 1)) if x["den"] is not None
                             else "≥ %s ATR" % vn(x["tu"], 0) for x in R], fontsize=8.5, color=LINE)
    axes[0, 1].legend(fontsize=7, frameon=False, loc="upper right", ncol=2)
    top = head(fig, "Vùng thanh khoản ICT gần nhất có «hút» giá hơn một mức bất kỳ cùng khoảng cách không?",
               "Vùng = liq_above / liq_below còn nguyên của ict_structure. «Mức bất kỳ» = xác suất chạm một mức đặt ở "
               "đúng khoảng cách đó, cùng giờ NY và cùng mức biến động. Trục ngang = khoảng cách tới vùng.")
    fig.tight_layout(rect=(0, 0, 1, top))
    fig.savefig(os.path.join(out, "ict_ind_5_vung_ict.png"), dpi=125)
    plt.close(fig)


# ---------------------------------------------------------------- hình 6


def fig_vi_du(J, out, plt, start="2024-08-20 02:00", n_bars=176, step=16):
    from matplotlib.patches import Rectangle
    ex = J["ket_qua"].get("XAUUSD", {}).get("vi_du")
    if not ex:
        return
    t = ex["gio_ny"]
    s = t.index(start)
    e = min(len(t), s + n_bars)
    sl = slice(s, e)
    arr = {k: np.array([np.nan if v is None else v for v in ex[k]], float) for k in ex if isinstance(ex[k], list)
           and k not in ("gio_ny", "su_kien", "ok")}
    o, h, l, c = (arr[k][sl] for k in ("open", "high", "low", "close"))
    atr = arr["atr"][sl]
    n = e - s
    fig = plt.figure(figsize=(15, 11.5))
    gs = fig.add_gridspec(4, 1, height_ratios=[5.2, 0.9, 1.6, 1.5], hspace=0.12)
    ax = fig.add_subplot(gs[0])
    axs = fig.add_subplot(gs[1], sharex=ax)
    axp = fig.add_subplot(gs[2], sharex=ax)
    axi = fig.add_subplot(gs[3], sharex=ax)
    for a in (ax, axs, axp, axi):
        style(a)
        a.grid(axis="x", visible=False)
    # dải dự báo 80% cho 4 giờ tới (ngoài mẫu, mô hình Nền + cả hai), mỗi 16 nến một hộp
    for k in range(0, n - 1, step):
        qu, qd = arr["q_len_4h_NEN+CA_HAI"][s + k], arr["q_xuong_4h_NEN+CA_HAI"][s + k]
        if not (np.isfinite(qu) and np.isfinite(qd) and np.isfinite(atr[k])):
            continue
        top, bot = c[k] + qu * atr[k], c[k] - qd * atr[k]
        w = min(step, n - 1 - k)
        ax.add_patch(Rectangle((k + 0.5, bot), w, top - bot, facecolor=ACC, alpha=0.10, edgecolor=ACC, lw=0.8,
                               ls="--"))
        ax.plot([k], [c[k]], marker="o", ms=3.5, color=ACC, zorder=6)
    for i in range(n):
        col = UP if c[i] >= o[i] else DOWN
        ax.vlines(i, l[i], h[i], color=col, lw=0.8)
        lo, hi = sorted((o[i], c[i]))
        ax.add_patch(Rectangle((i - 0.32, lo), 0.64, max(hi - lo, 0.03), facecolor=col, edgecolor=col, lw=0.5))
    ax.plot(range(n), arr["ema50"][sl], color="#2f6db5", lw=1.1, label="EMA50 M15")
    ax.plot(range(n), arr["ema200"][sl], color="#6b4fa0", lw=1.1, label="EMA200 M15")
    ax.plot(range(n), arr["liq_tren"][sl], color=DOWN, lw=0.9, ls=(0, (2, 2)), drawstyle="steps-post",
            label="vùng thanh khoản gần nhất (trên / dưới)")
    ax.plot(range(n), arr["liq_duoi"][sl], color=DOWN, lw=0.9, ls=(0, (2, 2)), drawstyle="steps-post")
    mk = {"LIQ_SWEEP_BSL": ("v", DOWN, "sweep BSL"), "LIQ_SWEEP_SSL": ("^", UP, "sweep SSL"),
          "SHIFT_UP": ("D", UP, "SHIFT tăng"), "SHIFT_DOWN": ("D", DOWN, "SHIFT giảm"),
          "LIQ_RUN_UP": ("P", UP, "run tăng"), "LIQ_RUN_DOWN": ("P", DOWN, "run giảm")}
    seen = set()
    for ev in ex["su_kien"]:
        i = ev["nen"] - s
        if not 0 <= i < n:
            continue
        m, col, ten = mk[ev["loai"]]
        yv = h[i] + 0.35 * atr[i] if ev["loai"] in ("LIQ_SWEEP_BSL", "SHIFT_DOWN", "LIQ_RUN_UP") else l[i] - 0.35 * atr[i]
        ax.plot(i, yv, marker=m, ms=7, color=col, mec="white", mew=0.6, ls="none", zorder=7,
                label=None if ev["loai"] in seen else ten)
        seen.add(ev["loai"])
    ax.add_patch(Rectangle((0, 0), 0, 0, facecolor=ACC, alpha=0.15, edgecolor=ACC, ls="--",
                           label="dải 80% dự báo cho 4 giờ tới (ngoài mẫu)"))
    ax.legend(loc="upper left", fontsize=7.8, ncol=3, frameon=False)
    ax.set_title("XAUUSD M15 · %s → %s (giờ New York) · đoạn phát triển, dự báo từ mô hình học trên 2018–2023" % (
        t[s], t[e - 1]), fontsize=11, color=LINE, loc="left")
    # dải trạng thái ICT
    for row, (k, ten) in enumerate((("ict_h4", "ICT H4"), ("ict_h1", "ICT H1"), ("ict_of", "Order flow M15"))):
        v = arr[k][sl]
        for i in range(n):
            if np.isfinite(v[i]) and v[i] != 0:
                axs.add_patch(Rectangle((i - 0.5, row), 1, 0.8, color=UP if v[i] > 0 else DOWN, alpha=0.75, lw=0))
        axs.text(-1.5, row + 0.4, ten, ha="right", va="center", fontsize=8, color=LINE)
    axs.set_ylim(-0.2, 3)
    axs.set_yticks([])
    axs.invert_yaxis()
    # xác suất dự báo
    axp.axhline(50, color=MUTED, lw=0.8, ls="--")
    axp.plot(range(n), arr["p_len_4h_NEN+CA_HAI"][sl] * 100, color=UP, lw=1.2, label="P(lên trước) 4h · nền + cả hai")
    axp.plot(range(n), arr["p_len_4h_NEN"][sl] * 100, color=MUTED, lw=1, ls="--", label="P(lên trước) 4h · chỉ nền")
    axp.plot(range(n), arr["p_1chieu_4h_NEN+CA_HAI"][sl] * 100, color=ACC, lw=1.2, label="P(đi một chiều) 4h")
    axp.set_ylabel("%", fontsize=8.5, color=MUTED)
    axp.legend(loc="upper left", fontsize=7.5, ncol=3, frameon=False)
    axp.set_ylim(15, 70)
    # indicator
    axi.plot(range(n), arr["rsi"][sl], color="#6b4fa0", lw=1, label="RSI 14")
    axi.plot(range(n), arr["adx"][sl], color=LINE, lw=1, label="ADX 14")
    for yv in (30, 70):
        axi.axhline(yv, color="#6b4fa0", lw=0.6, ls=":")
    axi.axhline(25, color=LINE, lw=0.6, ls=":")
    axi.legend(loc="upper left", fontsize=7.5, ncol=2, frameon=False)
    axi.set_ylim(0, 100)
    ticks = list(range(0, n, 16))
    axi.set_xticks(ticks)
    axi.set_xticklabels([t[s + k][5:].replace("-", "/") for k in ticks], fontsize=8, color=MUTED)
    for a in (ax, axs, axp):
        plt.setp(a.get_xticklabels(), visible=False)
    ax.set_xlim(-2, n + 1)
    fig.text(0.01, 0.065, "Dự báo ngoài mẫu: mô hình học trên 2018–2023, áp vào 2024. Dải vàng = khoảng giá dự báo phủ 80% "
             "cho 4 giờ tới, vẽ mỗi 4 giờ từ chấm vàng. Dải màu giữa = trạng thái ICT (xanh tăng, cam giảm).\n"
             "P(lên trước) dao động quanh 50% chứ không bám theo trạng thái ICT hay EMA — đúng như hình 4: mô hình không "
             "có thông tin hướng đáng kể.", fontsize=8.5, color=MUTED, linespacing=1.5)
    fig.savefig(os.path.join(out, "ict_ind_6_vi_du.png"), dpi=125, bbox_inches="tight")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.abspath(os.path.join(here, ".."))
    ap.add_argument("--json", default=os.path.join(root, "docs", "research", "khao_sat", "ict_indicator_dev.json"))
    ap.add_argument("--out", default=os.path.join(root, "docs", "research", "khao_sat"))
    args = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    with open(args.json, encoding="utf-8") as fh:
        J = json.load(fh)
    os.makedirs(args.out, exist_ok=True)
    for f in (fig_huong, fig_so_voi_cha, fig_theo_nam, fig_mo_hinh, fig_vung, fig_vi_du):
        f(J, args.out, plt)
        print("xong", f.__name__)


if __name__ == "__main__":
    main()
