"""Chọn mức CISD — chuyển nguyên các nhánh của Pine ``openSourceFractal.pine`` dòng 680–749.

Nhánh trực tiếp (nến kích hoạt ngược màu hoặc doji sau nến cùng màu/doji), tìm
ngược 2–10 nến rồi nâng/hạ theo open các nến cùng màu, và nhánh dự phòng khi mức
nằm sai phía open nến hiện tại. Đặc tả: ``docs/thuat_toan_c2_cisd.md`` §4.

Chuyển thể từ CantoLab Open Source Fractal (MIT, Copyright (c) 2026 cantolab,
commit ``1bb53262deba9456f2b1a85d15c6ac5a5e880cf7``); toàn văn giấy phép ở
``algorithm.py`` và ``third_party/open-source-fractal/LICENSE``.
"""
from __future__ import annotations

from typing import NamedTuple, Optional, Sequence

from core.algorithms.c2_cisd_research.state import SCAN_MAX, bar_doji, bar_down, bar_up
from core.types import Bar


class LevelChoice(NamedTuple):
    price: float
    source_index: int        # nến cung cấp giá mức (bullIndexFixed / bearIndexFixed)
    branch: str              # truc_tiep | tim_nguoc | du_phong_high | du_phong_low | du_phong_open
    scan_i: Optional[int]    # i của nhánh tìm ngược, None ở nhánh trực tiếp


def select_cisd_level(hist: Sequence[Bar], bull: bool) -> Optional[LevelChoice]:
    """Mức CISD mới khi nến ``hist[-1]`` vừa tạo đáy (``bull``) / đỉnh mới của kỳ.

    ``hist[-1]`` là nến t, ``hist[-1 - i]`` là nến [i] (như ``low[i]`` của Pine).
    Không kiểm điều kiện kích hoạt — người gọi đã kiểm ``low[t] == l0 and low[t] < l1``.
    Trả ``None`` khi không nhánh nào khớp (giữ mức cũ, như Pine).
    """
    n = len(hist)

    def at(i: int) -> Optional[Bar]:
        return hist[-1 - i] if i < n else None

    t = hist[-1]
    b1 = at(1)
    same = bar_down if bull else bar_up         # màu "ngược" của nến tạo mức
    opp = bar_up if bull else bar_down
    level: Optional[float] = None
    idx: Optional[int] = None
    branch = ""
    scan_i: Optional[int] = None
    if (same(t) or bar_doji(t)) and b1 is not None and (opp(b1) or bar_doji(b1)) and not (bar_doji(t) and bar_doji(b1)):
        level, idx, branch = t.open, t.index, "truc_tiep"
    else:
        for i in range(2, SCAN_MAX + 1):
            bi = at(i)
            if bi is None:
                break                   # Pine: na → mọi điều kiện sai, không đổi mức
            if (bi.low < t.low) if bull else (bi.high > t.high):
                break
            bim1 = at(i - 1)
            if (opp(bi) or bar_doji(bi)) and same(bim1):
                b = i - 1
                scan_i = i
                src = at(b)
                level, idx, branch = src.open, src.index, "tim_nguoc"
                for j in range(b, -1, -1):
                    bj = at(j)
                    better = bj.open > level if bull else bj.open < level
                    if better and same(bj):
                        level, idx = bj.open, bj.index
                wrong_side = level < t.open if bull else level > t.open
                if wrong_side:
                    if bull:
                        level = t.high if t.close > t.open else t.open
                        branch = "du_phong_high" if t.close > t.open else "du_phong_open"
                    else:
                        level = t.low if t.close < t.open else t.open
                        branch = "du_phong_low" if t.close < t.open else "du_phong_open"
                    idx = t.index
                break
    if level is None:
        return None
    return LevelChoice(level, idx, branch, scan_i)
