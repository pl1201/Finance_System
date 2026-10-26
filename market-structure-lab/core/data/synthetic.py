"""Sinh dữ liệu OHLC MÔ PHỎNG để thử nghiệm công cụ.

CẢNH BÁO: đây KHÔNG phải dữ liệu thị trường thật. Dữ liệu do bộ sinh này
tạo ra chỉ dùng để kiểm tra pipeline, giao diện và thuật toán. Mọi dataset
sinh ra đều được đánh dấu ``is_synthetic = True`` và hiển thị nhãn
"DỮ LIỆU MÔ PHỎNG" trên giao diện.

Bộ sinh dùng chuỗi các "giai đoạn" (trend tăng, tích lũy, trend giảm,
breakout, phá vỡ thất bại) để dataset mẫu có đủ tình huống cho việc quan
sát thuật toán, chứ không nhằm tái tạo tính chất thống kê của thị trường thật.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from core.types import TIMEFRAME_SECONDS, timeframe_delta

SYNTHETIC_LABEL = "DỮ LIỆU MÔ PHỎNG"

#: Cấu hình giá gốc và biên độ theo symbol (chỉ để dữ liệu trông hợp lý về
#: mặt đơn vị; không phải tham số thị trường thật).
SYMBOL_PROFILES: dict[str, dict[str, float]] = {
    "XAUUSD": {"start_price": 2000.0, "bar_atr_h1": 4.5, "digits": 2},
    "EURUSD": {"start_price": 1.0850, "bar_atr_h1": 0.0011, "digits": 5},
    "USDJPY": {"start_price": 150.00, "bar_atr_h1": 0.16, "digits": 3},
}

#: (tên giai đoạn, drift theo ATR/nến, hệ số biến động, số nến tương đối)
_PHASES: tuple[tuple[str, float, float, int], ...] = (
    ("trend_tang", 0.16, 1.0, 180),
    ("tich_luy_bien_dong_thap", 0.0, 0.45, 150),
    ("breakout_len", 0.30, 1.6, 60),
    ("trend_tang_yeu_dan", 0.05, 1.1, 120),
    ("pha_vo_that_bai", -0.02, 1.9, 70),
    ("trend_giam", -0.18, 1.2, 190),
    ("tich_luy_bien_dong_cao", 0.0, 1.5, 140),
    ("breakout_xuong", -0.32, 1.7, 60),
    ("hoi_phuc_range", 0.03, 0.8, 160),
)


@dataclass
class SyntheticSpec:
    symbol: str = "XAUUSD"
    timeframe: str = "H1"
    bars: int = 1800
    seed: int = 20260920
    start: Optional[datetime] = None


def _is_market_open(t: datetime) -> bool:
    """Lịch giao dịch giả định: nghỉ từ 21:00 thứ Sáu UTC đến 22:00 CN UTC."""
    wd, hour = t.weekday(), t.hour
    if wd == 4 and hour >= 21:
        return False
    if wd == 5:
        return False
    if wd == 6 and hour < 22:
        return False
    return True


def generate(spec: SyntheticSpec) -> dict[str, Any]:
    """Sinh dataset mô phỏng.

    Trả về dict gồm ``rows`` (đã chuẩn hoá, ``bar_time`` UTC, quy ước MỞ nến)
    và ``phases`` (nhãn giai đoạn theo chỉ số nến, để tham khảo khi đọc chart).
    """
    profile = SYMBOL_PROFILES.get(spec.symbol.upper())
    if profile is None:
        raise ValueError(
            "Chưa có hồ sơ mô phỏng cho symbol %r. Hỗ trợ: %s"
            % (spec.symbol, ", ".join(SYMBOL_PROFILES))
        )
    if spec.timeframe.upper() not in TIMEFRAME_SECONDS:
        raise ValueError("Timeframe không hỗ trợ: %r" % spec.timeframe)

    rng = random.Random(spec.seed)
    delta = timeframe_delta(spec.timeframe)
    # Quy đổi biên độ H1 sang timeframe khác theo căn bậc hai của thời gian.
    scale = (TIMEFRAME_SECONDS[spec.timeframe.upper()] / 3600.0) ** 0.5
    atr = profile["bar_atr_h1"] * scale
    digits = int(profile["digits"])

    start = spec.start or datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    while not _is_market_open(start):
        start += delta

    # Dựng lịch giai đoạn đủ dài cho số nến yêu cầu.
    total_weight = sum(p[3] for p in _PHASES)
    plan: list[tuple[str, float, float]] = []
    while len(plan) < spec.bars:
        for name, drift, vol, weight in _PHASES:
            n = max(5, round(spec.bars * weight / total_weight))
            for _ in range(n):
                plan.append((name, drift, vol))
                if len(plan) >= spec.bars:
                    break
            if len(plan) >= spec.bars:
                break

    price = profile["start_price"]
    t = start
    rows: list[dict[str, Any]] = []
    phases: list[str] = []

    for i in range(spec.bars):
        while not _is_market_open(t):
            t += delta

        phase_name, drift, vol = plan[i]
        step = atr * vol
        o = price
        # Đường đi trong nến: 4 bước ngẫu nhiên quanh drift.
        path = [o]
        for _ in range(4):
            path.append(path[-1] + rng.gauss(drift * atr / 4.0, step / 2.0))
        c = path[-1]
        hi = max(path) + abs(rng.gauss(0, step * 0.25))
        lo = min(path) - abs(rng.gauss(0, step * 0.25))
        hi = max(hi, o, c)
        lo = min(lo, o, c)

        rows.append(
            {
                "bar_time": t,
                "open": round(o, digits),
                "high": round(hi, digits),
                "low": round(lo, digits),
                "close": round(c, digits),
                "volume": float(rng.randint(400, 5200)),
            }
        )
        phases.append(phase_name)
        price = c
        t += delta

    # Bảo đảm bất biến OHLC sau khi làm tròn.
    for r in rows:
        r["high"] = max(r["high"], r["open"], r["close"])
        r["low"] = min(r["low"], r["open"], r["close"])

    return {
        "rows": rows,
        "phases": phases,
        "symbol": spec.symbol.upper(),
        "timeframe": spec.timeframe.upper(),
        "seed": spec.seed,
        "timestamp_convention": "open",
        "source_timezone": "UTC",
        "is_synthetic": True,
        "label": SYNTHETIC_LABEL,
    }


def to_csv_text(result: dict[str, Any]) -> str:
    """Xuất kết quả sinh ra thành CSV chuẩn của công cụ."""
    lines = ["time,open,high,low,close,volume"]
    digits = int(SYMBOL_PROFILES[result["symbol"]]["digits"])
    fmt = "%%.%df" % digits
    for r in result["rows"]:
        lines.append(
            "%s,%s,%s,%s,%s,%d"
            % (
                r["bar_time"].strftime("%Y-%m-%d %H:%M:%S"),
                fmt % r["open"],
                fmt % r["high"],
                fmt % r["low"],
                fmt % r["close"],
                int(r["volume"]),
            )
        )
    return "\n".join(lines) + "\n"
