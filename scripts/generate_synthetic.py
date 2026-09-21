"""Sinh lại dữ liệu MÔ PHỎNG ra file CSV.

Ví dụ (PowerShell, từ thư mục market-structure-lab):

    .\.venv\Scripts\python.exe scripts\generate_synthetic.py --symbol XAUUSD --timeframe H1 --bars 1800 --seed 20260920

Không truyền tham số sẽ sinh lại đúng bộ dataset mẫu mà nút "Tạo dữ liệu mẫu"
trên giao diện tạo ra, ghi vào ``data/samples/``.
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.data.synthetic import SYMBOL_PROFILES, SyntheticSpec, generate, to_csv_text  # noqa: E402

DEFAULT_SET = [
    ("XAUUSD", "H1", 1800, 20260920),
    ("XAUUSD", "M15", 2400, 20260921),
    ("XAUUSD", "M5", 2400, 20260922),
    ("EURUSD", "H1", 1800, 20260923),
]


def write_one(symbol: str, timeframe: str, bars: int, seed: int, outdir: str) -> str:
    result = generate(SyntheticSpec(symbol=symbol, timeframe=timeframe, bars=bars, seed=seed))
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "MOPHONG_%s_%s_seed%d.csv" % (symbol, timeframe, seed))
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(to_csv_text(result))
    print("Đã ghi %s (%d nến, %s .. %s)" % (
        path, len(result["rows"]),
        result["rows"][0]["bar_time"], result["rows"][-1]["bar_time"],
    ))
    return path


def main() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    ap = argparse.ArgumentParser(description="Sinh dữ liệu OHLC MÔ PHỎNG (không phải dữ liệu thật).")
    ap.add_argument("--symbol", choices=sorted(SYMBOL_PROFILES), help="Mã cần sinh")
    ap.add_argument("--timeframe", default="H1")
    ap.add_argument("--bars", type=int, default=1800)
    ap.add_argument("--seed", type=int, default=20260920)
    ap.add_argument("--outdir", default=os.path.join(root, "data", "samples"))
    args = ap.parse_args()

    print("CẢNH BÁO: đây là DỮ LIỆU MÔ PHỎNG, không phải dữ liệu thị trường thật.")
    if args.symbol:
        write_one(args.symbol, args.timeframe, args.bars, args.seed, args.outdir)
    else:
        for sym, tf, bars, seed in DEFAULT_SET:
            write_one(sym, tf, bars, seed, args.outdir)


if __name__ == "__main__":
    main()
