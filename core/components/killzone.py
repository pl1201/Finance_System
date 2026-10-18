"""[C] Killzone theo giờ New York (có đổi giờ mùa hè, ``zoneinfo``), theo giờ MỞ nến.

Chỉ là cờ trong ``details`` / timeline — không lọc sự kiện (plan_ict_structure §4.11). Khung giờ là
tham số dạng ``ten=giờ_bắt_đầu-giờ_kết_thúc`` (giờ nguyên, nửa mở), ngăn bằng dấu phẩy.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Optional

NY_TZ = "America/New_York"
DEFAULT_KILLZONES = "asia=20-24,london=2-5,ny_am=7-10,london_close=10-12"
_ITEM = re.compile(r"^([a-z][a-z0-9_]{0,23})=(\d{1,2})-(\d{1,2})$")


def parse_killzones(text: str) -> tuple[tuple[str, int, int], ...]:
    """``"asia=20-24,london=2-5"`` → ((ten, bắt đầu, kết thúc), …). Sai → ``ValueError``."""
    out: list[tuple[str, int, int]] = []
    for raw in str(text or "").split(","):
        item = raw.strip().lower()
        if not item:
            continue
        m = _ITEM.match(item)
        if not m:
            raise ValueError("Killzone %r sai dạng — cần ten=giờ-giờ, vd ny_am=7-10." % raw.strip())
        name, a, b = m.group(1), int(m.group(2)), int(m.group(3))
        if not 0 <= a < b <= 24:
            raise ValueError("Killzone %s: giờ phải 0 ≤ bắt đầu < kết thúc ≤ 24." % name)
        out.append((name, a, b))
    for i in range(len(out)):
        for j in range(i + 1, len(out)):
            if out[i][1] < out[j][2] and out[j][1] < out[i][2]:
                raise ValueError("Killzone %s và %s chồng giờ nhau." % (out[i][0], out[j][0]))
    return tuple(out)


class Killzones:
    def __init__(self, spec: str = DEFAULT_KILLZONES) -> None:
        from zoneinfo import ZoneInfo

        self.zones = parse_killzones(spec)
        self._tz = ZoneInfo(NY_TZ)

    def of(self, t: datetime) -> Optional[str]:
        if t.tzinfo is None:                 # nến của lab là UTC tz-aware; phòng vệ cho dữ liệu naive
            t = t.replace(tzinfo=timezone.utc)
        h = t.astimezone(self._tz).hour
        for name, a, b in self.zones:
            if a <= h < b:
                return name
        return None
