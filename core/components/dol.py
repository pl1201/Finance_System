"""[S6] DOL — draw on liquidity (plan_ict_structure §4.10, D7).

Sau mỗi ``SHIFT`` ở nến d:

* ``side`` = chiều shift (+1 tăng / −1 giảm);
* ``target`` = vùng thanh khoản **còn nguyên** gần nhất phía đó, tầng ≥ ``dol_min_tier`` (mặc định H1: ITH/ITL
  H1/H4, PDH/PDL, PWH/PWL), nằm hẳn ngoài close nến shift (tăng: mức > close[d]; giảm: mức < close[d]).
  Vùng xét là vùng còn nguyên sau bước [E2] của nến d (vùng bị lấy ở chính d không tính; vùng mới biết ở d
  — ITH/ITL khung chạy, khung lớn chốt ở d — chỉ có hiệu lực từ d+1 nên không tính). Khoảng cách ghi theo
  ATR khung chạy ATR[d−1];
* không có vùng nào phía đó → DOL ``none`` (``side = target = None``); DOL cũ vẫn bị thay.

Hết hiệu lực khi đích bị **lấy** (``DOL_REACHED`` tại nến lấy) hoặc khi có shift mới (thay thế). «Tỷ lệ đạt
DOL» là nhãn đánh giá nhìn về sau — không bao giờ là đầu vào. Định nghĩa khác (theo premium/discount khung
lớn, vùng D/W lớn nhất) để v0.2 (D7).
"""
from __future__ import annotations

from typing import Any, Optional

from core.components.liquidity import TIER_RANK, LiquidityBook, Pool

TIERS = ("H1", "H4", "D", "W")


class DrawOnLiquidity:
    def __init__(self, min_tier: str = "H1") -> None:
        if min_tier not in TIERS:
            raise ValueError("dol_min_tier phải thuộc %s" % (list(TIERS),))
        self.min_tier = min_tier
        self.min_rank = TIER_RANK[min_tier]
        self.reset()

    def reset(self) -> None:
        self.side: Optional[int] = None
        self.target: Optional[Pool] = None
        self.shift_id: Optional[str] = None
        self.since: Optional[int] = None
        self.dist_atr_at_set: Optional[float] = None
        self.counts = {"shift": 0, "co_dich": 0, "khong_co_vung": 0, "dat": 0, "bi_thay": 0}
        self.tiers: dict[str, int] = {}
        self.dist: list[float] = []

    def check_reached(self, taken: list[Pool]) -> Optional[dict[str, Any]]:
        """Bước [E2] của nến này vừa lấy các vùng ``taken``. Đích nằm trong đó → trả mô tả và xoá DOL."""
        tg = self.target
        if tg is None or not any(p is tg for p in taken):
            return None
        info = {"side": self.side, "target": tg, "shift_id": self.shift_id, "since": self.since,
                "dist_atr_at_set": self.dist_atr_at_set}
        self.counts["dat"] += 1
        self.side, self.target, self.shift_id, self.since, self.dist_atr_at_set = None, None, None, None, None
        return info

    def set_from_shift(self, book: LiquidityBook, side: int, close: float, atr_prev: Optional[float], t: int,
                       shift_id: str) -> Optional[Pool]:
        if self.target is not None:
            self.counts["bi_thay"] += 1
        self.counts["shift"] += 1
        tg = book.nearest_beyond("high" if side > 0 else "low", close, self.min_rank)
        self.target, self.shift_id, self.since = tg, shift_id, t
        if tg is None:                                  # không có vùng phía đó → DOL «none» (shift vẫn thay DOL cũ)
            self.side = None
            self.counts["khong_co_vung"] += 1
            self.dist_atr_at_set = None
            return None
        self.side = side
        self.counts["co_dich"] += 1
        self.tiers[tg.tier] = self.tiers.get(tg.tier, 0) + 1
        self.dist_atr_at_set = abs(tg.level - close) / atr_prev if atr_prev else None
        if self.dist_atr_at_set is not None:
            self.dist.append(self.dist_atr_at_set)
        return tg

    def context(self, close: Optional[float], atr: Optional[float]) -> dict[str, Any]:
        """Ảnh chụp gọn ``details.htf.dol`` (plan §11.5): khoảng cách tới đích theo ATR khung chạy hiện tại."""
        tg = self.target
        return {
            "side": self.side,
            "target": tg.level if tg is not None else None,
            "tier": tg.tier if tg is not None else None,
            "dist_atr": (abs(tg.level - close) / atr) if (tg is not None and close is not None and atr) else None,
        }

    def snapshot(self, t: Optional[int], close: Optional[float], atr: Optional[float]) -> dict[str, Any]:
        tg = self.target
        d = self.context(close, atr)
        d.update({
            "vung": tg.brief() if tg is not None else None,
            "shift": self.shift_id,
            "tu_nen": self.since,
            "so_nen": (t - self.since) if (t is not None and self.since is not None) else None,
            "khoang_cach_atr_luc_dat": self.dist_atr_at_set,
            "tang_toi_thieu": self.min_tier,
        })
        return d
