"""Hiển thị lớp «Trạng thái» (lõi 0.6.0): hàm thuần frontend/js/algos/ict_nhan_dien_view.js, chạy bằng node
(tests/frontend/ict_nhan_dien_check.js nạp file JS trong vm, không cần trình duyệt):

* kịch bản dựng tay — dải trạng thái theo nến, đoạn trạng thái, dòng trạng thái, hộp range đang có / đã qua, tooltip, câu
  giải thích, «Đang theo dõi», nhân quả theo con trỏ, kết quả cũ không có lớp;
* dữ liệu lõi thật (bước ngẫu nhiên + một đoạn dao động có biên rõ) — dải = cột nd_trang_thai, replay prefix cho cùng dải
  và hộp như toàn bộ lọc theo con trỏ, hộp range = biên timeline tại con trỏ.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import tempfile

import pytest

from core.algorithms.ict_structure import IctStructureAlgorithm
from core.engine import run_algorithm
from tests.algorithms.test_ict_structure_g2 import _ohlc, _p

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "ict_nhan_dien_check.js")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="cần node để chạy hàm JS thuần")


def _node(*args: str) -> dict:
    out = subprocess.run([NODE, SCRIPT, *args], capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert out.returncode == 0, out.stderr
    res = json.loads(out.stdout)
    assert res["checks"] > 0
    return res


def _rows(seed: int) -> list[tuple[float, float, float, float]]:
    """400 nến bước ngẫu nhiên, 160 nến dao động 100 ↔ 102 (chu kỳ 8), 300 nến bước ngẫu nhiên."""
    rnd, rows = random.Random(seed), []

    def bar(c):
        o = rows[-1][3] if rows else 101.0
        return o, c, max(o, c), min(o, c)

    def walk(n):
        for _ in range(n):
            o, c, hi, lo = bar((rows[-1][3] if rows else 101.0) + rnd.gauss(0, 0.4))
            rows.append((o, hi + abs(rnd.gauss(0, 0.15)), lo - abs(rnd.gauss(0, 0.15)), c))

    walk(400)
    for i in range(160):
        o, c, hi, lo = bar(100.0 + abs(4 - i % 8) * 0.5)
        rows.append((o, hi + 0.05, lo - 0.05, c))
    walk(300)
    return rows


def test_ham_thuan_trang_thai_kich_ban_dung_tay():
    res = _node("hand")
    assert res["failures"] == [], "\n".join(res["failures"][:20])


@pytest.mark.parametrize("seed", [3, 11])
def test_trang_thai_khop_timeline_va_replay_nhan_qua(seed):
    bars = _ohlc(_rows(seed))
    full = run_algorithm(bars, IctStructureAlgorithm(**_p()))
    tl = full.timeline
    rng_at = [p["bar_index"] for p in tl if p["nd_trang_thai"] == "range"]
    assert rng_at, "đoạn dao động phải cho range"
    cursors = sorted({rng_at[0], rng_at[len(rng_at) // 2], rng_at[-1], min(rng_at[-1] + 40, len(bars) - 1), 300,
                      len(bars) - 1})
    data = {"digits": 2, "full": {"events": [e.to_dict() for e in full.events], "timeline": tl}, "prefixes": []}
    for c in cursors:
        a = IctStructureAlgorithm(**_p())
        px = run_algorithm(bars, a, upto_index=c)
        data["prefixes"].append({"cursor": c, "events": [e.to_dict() for e in px.events], "timeline": px.timeline,
                                 "pending": a.pending_state()})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(data, fh, default=str)
        path = fh.name
    try:
        res = _node("real", path)
    finally:
        os.unlink(path)
    assert res["failures"] == [], "\n".join(res["failures"][:20])
