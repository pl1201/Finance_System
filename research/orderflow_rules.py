"""Quy tắc dải order flow (run + shift) và trạng thái «chưa rõ»: số mô tả, tái lập được.

Tài liệu: ``docs/research/nghien_cuu_orderflow_ict.md`` §8 (quyết định 06/10/2026 ở §7). Đây là khảo sát
MÔ TẢ (trạng thái kéo dài bao lâu, đổi bao nhiêu lần), không phải thuật toán và không đo khả năng dự báo:

* đọc ``data/lab.sqlite`` CHỈ ĐỌC; mọi đoạn kết thúc trước 2024-09-01 (đoạn kiểm tra khoá — script từ chối
  khoảng chạm vào đó, trừ khi có ``--allow-test``);
* sự kiện lấy từ ``ict_structure`` (tham số mặc định, lịch phiên theo mã) chạy nhân quả trên từng dataset,
  bằng hàm ``load`` của ``orderflow_survey.py``;
* trạng thái sau mỗi nến t: +1 tăng, −1 giảm, 0 chưa rõ. Chỉ đổi theo sự kiện ĐÃ XÁC NHẬN ở t thuộc bốn
  loại ``LIQ_RUN_UP`` / ``LIQ_RUN_DOWN`` (run) và ``SHIFT_UP`` / ``SHIFT_DOWN`` (shift). Trước sự kiện đầu
  tiên trạng thái là 0 (khởi động — «chưa có» của lõi): tính vào «chưa rõ» ở tỷ lệ thời gian, bỏ khỏi phần
  đếm đoạn.

Các quy tắc so sánh:

* ``base`` (run + shift): sự kiện đặt chiều; hai chiều ngược nhau cùng nến → 0.
* ``A``: shift đặt chiều ngay; run cùng chiều giữ nguyên; run NGƯỢC chiều đang có → 0 (chưa rõ); từ 0, sự
  kiện kế tiếp (run hoặc shift) đặt chiều của nó; hai chiều cùng nến → 0. Đây là quy tắc người dùng chốt
  ngày 06/10/2026 (``ict_structure`` 0.3.0, khi coi «chưa có» là 0).
* ``B(N)``: như ``base``, nhưng nến nào mà trong N nến gần nhất (tính cả nến đó) có cả ``LIQ_RUN_UP`` lẫn
  ``LIQ_RUN_DOWN`` thì ghi 0. Đã bỏ (06/10/2026).
* ``A+B(N)``: áp B lên kết quả của A.

Đo (``describe``): tỷ lệ thời gian; số lần đổi chiều thật (một đoạn ±1 khác chiều đoạn ±1 liền trước, có
thể đi qua 0) và số đoạn chưa rõ, chia cho số NGÀY GIAO DỊCH (``so_ngay_giao_dich`` của lõi, theo lịch
phiên); trung vị độ dài đoạn = phần tử giữa của dãy đã sắp (``xs[len // 2]``), đổi ra giờ. Riêng quy tắc A
(``A_chua_ro``): «chưa rõ» vào bằng gì và kết thúc ra sao — quay lại chiều cũ hay sang chiều mới, bằng run
hay shift. ``tan_suat_lat``: số lần lật đếm như ``orderflow_survey.py`` (nến có trạng thái ±1 khác nến
trước) chia cho ngày UTC có nến (đơn vị của ``lat_moi_ngay`` trong khảo sát đó) và cho ngày giao dịch.

Ví dụ (PowerShell, từ thư mục market-structure-lab)::

    .\\.venv\\Scripts\\python.exe research\\orderflow_rules.py --json docs\\research\\khao_sat\\orderflow_rules_dev.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sqlite3
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from core.types import timeframe_delta  # noqa: E402
from orderflow_survey import TEST_START, load  # noqa: E402

RULES_VERSION = "orderflow-rules-v1"
EV = {   # loại sự kiện → (kiểu, chiều)
    "LIQ_RUN_UP": ("run", 1), "SHIFT_UP": ("shift", 1),
    "LIQ_RUN_DOWN": ("run", -1), "SHIFT_DOWN": ("shift", -1),
}
B_WINDOWS = (4, 8, 16)
AB_WINDOW = 8
CASES = (   # (nhãn, dataset, từ, đến) — bốn cấu hình của khảo sát 06/10/2026
    ("XAUUSD M15 01–08/2024", "ds_db1583cd4dde", "2024-01-01", TEST_START),
    ("XAUUSD M15 2018–2023", "ds_a5212fd37814", "2018-01-01", "2024-01-01"),
    ("EURUSD M15 2018–2023", "ds_a9a2a5e4cef5", "2018-01-01", "2024-01-01"),
    ("XAUUSD M5 01–08/2024", "ds_933fa5ec67e2", "2024-01-01", TEST_START),
)
RULE_TEXT = {
    "base": "run + shift: sự kiện đặt chiều; hai chiều ngược nhau cùng nến → 0",
    "A": "shift đặt chiều; run cùng chiều giữ; run ngược chiều đang có → 0; từ 0 sự kiện kế tiếp đặt chiều; "
         "hai chiều cùng nến → 0 (chốt 06/10/2026)",
    "B(N)": "như base; trong N nến gần nhất (tính cả nến đó) có cả LIQ_RUN_UP và LIQ_RUN_DOWN → 0 (đã bỏ)",
    "A+B(N)": "áp B lên A",
}
MEASURE_TEXT = {
    "ty_le": "trên mọi nến của đoạn; khởi động (trước sự kiện đầu) tính vào chưa rõ",
    "doan": "dãy nến liên tiếp cùng giá trị; bỏ đoạn 0 khởi động; tính cả đoạn cuối đang mở",
    "doi_chieu": "đoạn ±1 khác chiều đoạn ±1 liền trước (có thể qua 0)",
    "ngay": "so_ngay_giao_dich của ict_structure (ngày giao dịch theo lịch phiên)",
    "trung_vi": "phần tử giữa xs[len // 2] của độ dài đoạn (nến) × độ dài khung, đổi ra giờ, làm tròn 0.1",
    "lat_kieu_orderflow_survey": "nến t ≥ 1 có trạng thái ±1 khác trạng thái nến t−1",
    "ngay_utc_co_nen": "số ngày lịch UTC có ít nhất một nến (gồm phần phiên mở tối Chủ nhật)",
}


# ---------------------------------------------------------------- quy tắc


def events_by_bar(res):
    """{nến xác nhận: [(kiểu, chiều), …]} theo thứ tự phát của lõi."""
    out = defaultdict(list)
    for e in res.events:
        if e.structure_type in EV:
            out[e.confirmed_bar_index].append(EV[e.structure_type])
    return out


def rule_base(n, ev):
    s, out = 0, []
    for t in range(n):
        if t in ev:
            dirs = {d for _k, d in ev[t]}
            s = dirs.pop() if len(dirs) == 1 else 0
        out.append(s)
    return out


def rule_a(n, ev):
    s, out = 0, []
    for t in range(n):
        if t in ev:
            dirs = {d for _k, d in ev[t]}
            if len(dirs) > 1:
                s = 0
            else:
                d = dirs.pop()
                kinds = {k for k, dd in ev[t] if dd == d}
                if "shift" in kinds or s == 0 or s == d:
                    s = d
                else:                     # chỉ run, ngược chiều đang có → chưa rõ
                    s = 0
        out.append(s)
    return out


def apply_b(states, ev, n_window):
    last = {1: -10 ** 9, -1: -10 ** 9}
    out = []
    for t, s in enumerate(states):
        for k, d in ev.get(t, ()):
            if k == "run":
                last[d] = t
        both = t - last[1] < n_window and t - last[-1] < n_window
        out.append(0 if both else s)
    return out


# ---------------------------------------------------------------- đo


def segments(states):
    """[[giá trị, nến đầu, độ dài], …] — các đoạn liên tiếp cùng giá trị."""
    segs = []
    for t, x in enumerate(states):
        if segs and segs[-1][0] == x:
            segs[-1][2] += 1
        else:
            segs.append([x, t, 1])
    return segs


def describe(states, step_minutes, days):
    n = len(states)
    share = {k: sum(1 for x in states if x == k) / n for k in (1, -1, 0)}
    runs = [[v, length] for v, _start, length in segments(states)]
    if runs and runs[0][0] == 0:
        runs = runs[1:]                        # bỏ đoạn khởi động trước sự kiện đầu tiên
    dir_runs = [length for v, length in runs if v != 0]
    zero_runs = [length for v, length in runs if v == 0]
    flips = 0                                  # đổi chiều thật (±1 → ∓1, có thể qua 0)
    prev = 0
    for v, _length in runs:
        if v != 0:
            if prev != 0 and v != prev:
                flips += 1
            prev = v

    def med_h(xs):
        if not xs:
            return None
        xs = sorted(xs)
        return round(xs[len(xs) // 2] * step_minutes / 60, 1)

    return {
        "tang_%": round(100 * share[1], 1), "giam_%": round(100 * share[-1], 1), "chua_ro_%": round(100 * share[0], 1),
        "doi_chieu_moi_ngay": round(flips / days, 2),
        "doan_chua_ro_moi_ngay": round(len(zero_runs) / days, 2),
        "chua_ro_keo_dai_TV_gio": med_h(zero_runs),
        "mot_chieu_keo_dai_TV_gio": med_h(dir_runs),
    }


def unclear_episodes(states, ev):
    """Quy tắc A: mỗi đoạn «chưa rõ» (bỏ đoạn khởi động) vào bằng gì và kết thúc ra sao.

    Vào: run ngược chiều đang có, hoặc hai chiều cùng nến. Ra (nến đầu của đoạn ±1 kế tiếp): quay lại chiều
    của đoạn ±1 trước nó hay sang chiều mới; «bằng shift» nếu nến đó có shift cùng chiều mới, không thì
    «bằng run». Đoạn còn mở ở cuối dữ liệu đếm riêng.
    """
    segs = segments(states)
    if segs and segs[0][0] == 0:
        segs = segs[1:]
    vao = {"run_nguoc_chieu": 0, "hai_chieu_cung_nen": 0}
    ra = {"quay_lai_chieu_cu": {"run": 0, "shift": 0}, "sang_chieu_moi": {"run": 0, "shift": 0}}
    con_mo = 0
    for i, (v, start, _length) in enumerate(segs):
        if v != 0:
            continue
        prev = segs[i - 1][0]                  # luôn ±1: đoạn 0 đầu đã bỏ, hai đoạn kề nhau khác giá trị
        dirs = {d for _k, d in ev.get(start, ())}
        if len(dirs) > 1:
            vao["hai_chieu_cung_nen"] += 1
        else:
            assert dirs == {-prev} and all(k == "run" for k, _d in ev[start]), start
            vao["run_nguoc_chieu"] += 1
        if i + 1 == len(segs):
            con_mo += 1
            continue
        new, t_exit = segs[i + 1][0], segs[i + 1][1]
        kinds = {k for k, d in ev.get(t_exit, ()) if d == new}
        assert kinds, t_exit
        ra["quay_lai_chieu_cu" if new == prev else "sang_chieu_moi"]["shift" if "shift" in kinds else "run"] += 1
    n_seg = vao["run_nguoc_chieu"] + vao["hai_chieu_cung_nen"]
    n_end = n_seg - con_mo

    def pct(a, b):
        return round(100 * a / b, 1) if b else None

    back = sum(ra["quay_lai_chieu_cu"].values())
    by_run = ra["quay_lai_chieu_cu"]["run"] + ra["sang_chieu_moi"]["run"]
    return {
        "so_doan": n_seg,
        "vao_run_nguoc_chieu_%": pct(vao["run_nguoc_chieu"], n_seg),
        "vao_hai_chieu_cung_nen_%": pct(vao["hai_chieu_cung_nen"], n_seg),
        "ket_thuc": n_end, "con_mo_cuoi_doan": con_mo,
        "quay_lai_chieu_cu_%": pct(back, n_end), "sang_chieu_moi_%": pct(n_end - back, n_end),
        "thoat_bang_run_%": pct(by_run, n_end), "thoat_bang_shift_%": pct(n_end - by_run, n_end),
        "vao": vao, "ra": ra,
    }


def flip_rates(states, days, utc_days):
    """Lật kiểu ``orderflow_survey.py``: nến t ≥ 1 có trạng thái ±1 khác nến t−1."""
    flips = sum(1 for t in range(1, len(states)) if states[t] != 0 and states[t] != states[t - 1])
    return {"so_lan_lat": flips, "lat_moi_ngay_utc_co_nen": round(flips / utc_days, 2),
            "lat_moi_ngay_giao_dich": round(flips / days, 2)}


# ---------------------------------------------------------------- chạy


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default=os.path.join(ROOT, "data", "lab.sqlite"))
    ap.add_argument("--json", default="")
    ap.add_argument("--allow-test", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    con = sqlite3.connect("file:%s?mode=ro" % args.db, uri=True)
    with open(os.path.abspath(__file__), "rb") as f:
        script_sha = hashlib.sha256(f.read()).hexdigest()
    out = {"meta": {"phien_ban": RULES_VERSION, "script_sha256": script_sha, "python": platform.python_version(),
                    "doan_kiem_tra_tu": TEST_START,
                    "dinh_nghia": {"su_kien": {k: list(v) for k, v in EV.items()}, "quy_tac": RULE_TEXT,
                                   "do": MEASURE_TEXT, "B_N": list(B_WINDOWS), "A+B_N": AB_WINDOW},
                    "du_lieu": []},
           "ket_qua": {}}
    for label, ds, a, b in CASES:
        bars, res, meta = load(con, ds, a, b, args.allow_test)
        if not bars:
            out["ket_qua"][label] = "dataset %s không có nến trong %s..%s" % (ds, a, b)
            continue
        out["meta"]["du_lieu"].append(meta)
        step = timeframe_delta(meta["khung"]).total_seconds() / 60
        days = res.stats["chi_so_thuat_toan"]["so_ngay_giao_dich"]
        utc_days = len({br.bar_time.date() for br in bars})
        ev = events_by_bar(res)
        n = len(bars)
        base, ra = rule_base(n, ev), rule_a(n, ev)
        n_run = sum(1 for t in ev for k, _d in ev[t] if k == "run")
        n_shift = sum(1 for t in ev for k, _d in ev[t] if k == "shift")
        o = {"so_ngay": days, "run_moi_ngay": round(n_run / days, 2), "shift_moi_ngay": round(n_shift / days, 2),
             "base": describe(base, step, days), "A": describe(ra, step, days)}
        for w in B_WINDOWS:
            o["B(N=%d)" % w] = describe(apply_b(base, ev, w), step, days)
        o["A+B(N=%d)" % AB_WINDOW] = describe(apply_b(ra, ev, AB_WINDOW), step, days)
        o["A_chua_ro"] = unclear_episodes(ra, ev)
        o["tan_suat_lat"] = {"so_ngay_giao_dich": days, "so_ngay_utc_co_nen": utc_days,
                             "ngay_utc_tren_ngay_giao_dich": round(utc_days / days, 3),
                             "base": flip_rates(base, days, utc_days), "A": flip_rates(ra, days, utc_days)}
        out["ket_qua"][label] = o
        print("==", label, "| ngày giao dịch", days, "| ngày UTC có nến", utc_days,
              "| run/ngày", o["run_moi_ngay"], "| shift/ngày", o["shift_moi_ngay"])
        for k, v in o.items():
            if isinstance(v, dict):
                print("   %-14s %s" % (k, json.dumps(v, ensure_ascii=False)))
        sys.stdout.flush()
    out["meta"]["thoi_gian_s"] = round(time.time() - t0, 1)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print("Đã ghi", args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
