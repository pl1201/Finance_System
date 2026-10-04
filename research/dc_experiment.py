"""Thí nghiệm đối chứng tái lập cho dc_atr_structure (docs/algorithms/thuat_toan_dc_atr_structure.md §10).

Chạy trên MỘT snapshot dataset (khoá bằng checksum), hai đoạn thời gian cố định
trước khi xem kết quả:

* đoạn phát triển (dev) và đoạn kiểm tra (test) theo thời gian, không chồng nhau;
* cấu hình: swing_pivot 3/3 (baseline, không đổi), DC percent 0.2%, DC ATR14 k = 1.0 / 1.5 / 2.0;
* tham số classifier giữ mặc định cho mọi run DC.

Thêm pivot CLOSE 3/3 trong harness (nến giả h = l = o = c = close, KHÔNG lưu run,
không sửa baseline) để tách ảnh hưởng «nguồn giá» khỏi «ngưỡng».

Chỉ số mô tả hành vi — không có nhãn tham chiếu nên KHÔNG có precision/recall/F1.

Ví dụ (PowerShell, từ thư mục market-structure-lab):

    .\.venv\Scripts\python.exe research\dc_experiment.py --dataset ds_564bff443e42 --save

``--gap-policy bridge_short --bridge-hours 2`` chạy lại các cấu hình DC với chính
sách nối gap ngắn (baseline và harness không phụ thuộc gap nên được bỏ qua).

``--save`` ghi các run vào lịch sử (bảng runs) kèm nhãn ``[DC thí nghiệm] …`` để mở
lại / so sánh trên giao diện; mặc định không ghi.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.common import get_dataset_or_error, load_bars  # noqa: E402
from backend.app.services.runs import execute_run  # noqa: E402
from core.algorithms.swing_pivot import SwingPivotAlgorithm  # noqa: E402
from core.engine import run_algorithm  # noqa: E402
from core.eval.metrics import median, percentile_nearest_rank  # noqa: E402

PERIODS = {
    "dev": ("2024-01-01T00:00:00+00:00", "2024-08-31T23:59:59+00:00"),
    "test": ("2024-09-01T00:00:00+00:00", "2024-12-31T23:59:59+00:00"),
}

CONFIGS = [
    ("baseline pivot 3/3 (wick)", "swing_pivot", {"left": 3, "right": 3}),
    ("DC percent 0.2%", "dc_atr_structure", {"threshold_mode": "percent", "reversal_pct": 0.2}),
    ("DC ATR14 k=1.0", "dc_atr_structure", {"threshold_mode": "atr", "atr_multiplier": 1.0}),
    ("DC ATR14 k=1.5", "dc_atr_structure", {"threshold_mode": "atr", "atr_multiplier": 1.5}),
    ("DC ATR14 k=2.0", "dc_atr_structure", {"threshold_mode": "atr", "atr_multiplier": 2.0}),
]


def _fmt(x, d=2):
    return "—" if x is None else ("%.*f" % (d, x))


def close_pivot_33(bars):
    """Pivot 3/3 trên CLOSE trong harness (không phải thuật toán đăng ký, không lưu)."""
    from dataclasses import replace

    flat = [replace(b, open=b.close, high=b.close, low=b.close) for b in bars]
    ev = run_algorithm(flat, SwingPivotAlgorithm(left=3, right=3, enable_bos=False)).events
    return [e for e in ev if e.structure_type in ("SWING_HIGH", "SWING_LOW")]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="ds_564bff443e42")
    ap.add_argument("--save", action="store_true")
    ap.add_argument("--json", default="")
    ap.add_argument("--gap-policy", default="reset", choices=("reset", "bridge_short"))
    ap.add_argument("--bridge-hours", type=float, default=2.0)
    args = ap.parse_args()

    ds = get_dataset_or_error(args.dataset)
    if ds["timeframe"] != "M15":
        raise SystemExit("Thí nghiệm khoá cho M15 (dataset là %s)." % ds["timeframe"])
    out = {
        "dataset_id": ds["id"],
        "dataset_name": ds["name"],
        "checksum": ds["checksum_sha256"],
        "is_synthetic": bool(ds["is_synthetic"]),
        "periods": PERIODS,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "rows": [],
    }
    stamp = datetime.utcnow().strftime("%Y%m%d")
    for period, (start, end) in PERIODS.items():
        for label, algo, params in CONFIGS:
            p = dict(params)
            if algo != "dc_atr_structure" and args.gap_policy != "reset":
                continue
            if algo == "dc_atr_structure":
                p["timeframe"] = "M15"
                p["gap_policy"] = args.gap_policy
                if args.gap_policy == "bridge_short":
                    p["bridge_max_gap_hours"] = args.bridge_hours
                    label = label + " · nối gap ≤ %gh" % args.bridge_hours
            res = execute_run(
                dataset_id=ds["id"], algorithm=algo, params=p, range_start=start, range_end=end,
                label="[DC thí nghiệm %s] %s — %s" % (stamp, period, label), save=args.save,
            )
            row = {
                "period": period, "config": label, "algorithm": algo,
                "algorithm_version": res["algorithm_version"], "params": res["params"],
                "run_id": res["run_id"] if args.save else None,
                "bars": res["bars_processed"], "range": [res["range_start"], res["range_end"]],
            }
            evs = res["events"]
            if algo == "swing_pivot":
                piv = [e for e in evs if e["structure_type"] in ("SWING_HIGH", "SWING_LOW")]
                lags = [e["confirmation_lag_bars"] for e in piv]
                row.update({
                    "pivots": len(piv),
                    "density_per_1000": 1000.0 * len(piv) / res["bars_processed"],
                    "density_base_vi": "mọi nến của khoảng",
                    "lag_median": median(lags), "lag_p90": percentile_nearest_rank(lags, 90),
                })
            else:
                m = res["stats"]["chi_so_thuat_toan"]
                row.update({
                    "pivots": m["so_pivot_xac_nhan"],
                    "density_per_1000": m["mat_do_tren_1000_nen"],
                    "density_base_vi": "nến đã có ATR",
                    "lag_median": m["do_tre_nen"]["trung_vi"], "lag_p90": m["do_tre_nen"]["p90"],
                    "lag_min_median": m["do_tre_phut"]["trung_vi"],
                    "rev_atr_median": m["reversal_distance_atr"]["trung_vi"],
                    "amp_atr_median": m["bien_do_nhip_atr"]["trung_vi"],
                    "amp_atr_p90": m["bien_do_nhip_atr"]["p90"],
                    "share": m["regime_ty_le_thoi_gian"],
                    "transitions": m["so_lan_chuyen_trang_thai"],
                    "run_len_median": m["do_dai_doan_trung_vi_tat_ca"],
                    "gaps": m["so_gap"], "bridged": m.get("so_gap_noi", 0), "segments": m["so_segment"],
                    "eligible": m["so_nen_du_dieu_kien"],
                    "labels": m["nhan_so_sanh"],
                    "range_starts": sum(1 for e in evs if e["structure_type"] == "DC_RANGE_START"),
                })
            out["rows"].append(row)
        if args.gap_policy != "reset":
            continue
        _, bars, _ = load_bars(ds["id"], start, end)
        cp = close_pivot_33(bars)
        out["rows"].append({
            "period": period, "config": "pivot CLOSE 3/3 (harness, không lưu)", "algorithm": "harness",
            "pivots": len(cp), "density_per_1000": 1000.0 * len(cp) / len(bars),
            "density_base_vi": "mọi nến của khoảng", "lag_median": 3.0, "lag_p90": 3.0, "bars": len(bars),
        })

    print("Dataset %s (%s) checksum %s%s" % (
        ds["name"], ds["id"], ds["checksum_sha256"][:16], " — MÔ PHỎNG" if ds["is_synthetic"] else ""))
    print("| Đoạn | Cấu hình | run_id | Pivot | /1000 nến | Trễ TV/P90 (nến) | Đảo chiều/ATR TV | Nhịp/ATR TV/P90 | Tăng/Giảm/Range/Chưa rõ | Chuyển | Range |")
    print("|---|---|---|---:|---:|---|---:|---|---|---:|---:|")
    for r in out["rows"]:
        sh = r.get("share")
        share = "—" if not sh else "/".join("%.1f%%" % (100 * (sh[k] or 0)) for k in ("UPTREND", "DOWNTREND", "RANGE", "UNKNOWN"))
        print("| %s | %s | %s | %d | %s | %s / %s | %s | %s / %s | %s | %s | %s |" % (
            r["period"], r["config"], r.get("run_id") or "—", r["pivots"], _fmt(r["density_per_1000"], 1),
            _fmt(r["lag_median"], 1), _fmt(r["lag_p90"], 1), _fmt(r.get("rev_atr_median")),
            _fmt(r.get("amp_atr_median")), _fmt(r.get("amp_atr_p90")), share,
            r.get("transitions", "—"), r.get("range_starts", "—"),
        ))
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
