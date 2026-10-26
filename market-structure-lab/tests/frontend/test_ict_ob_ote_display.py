"""Hiển thị order block / OTE (lõi 0.5.0): hàm thuần frontend/js/algos/ict_ob_ote_view.js, chạy bằng node
(tests/frontend/ict_ob_ote_check.js nạp file JS trong vm, không cần trình duyệt):

* kịch bản dựng tay — nét / chữ theo kết cục OB (mở, chạm, hỏng), OTE đang chờ (chưa có vùng / có vùng, gốc = SHIFT gần
  nhất), OTE vừa vào, nhân quả theo con trỏ, tắt lớp, câu giải thích, «Đang theo dõi»;
* dữ liệu lõi thật (chuỗi nến ngẫu nhiên) — hộp OTE = cột timeline ote_lo / ote_hi tại con trỏ, OB mở gần nhất = cột
  ob_up_hi / ob_down_lo, replay prefix cho cùng đối tượng vẽ như toàn bộ sự kiện lọc theo con trỏ, mọi hộp có tooltip.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

import pytest

from core.algorithms.ict_structure import IctStructureAlgorithm
from core.engine import run_algorithm
from tests.algorithms.test_ict_structure_g2 import _p, _random_bars

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "ict_ob_ote_check.js")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="cần node để chạy hàm JS thuần")


def _node(*args: str) -> dict:
    out = subprocess.run([NODE, SCRIPT, *args], capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert out.returncode == 0, out.stderr
    res = json.loads(out.stdout)
    assert res["checks"] > 0
    return res


def test_ham_thuan_ob_ote_kich_ban_dung_tay():
    res = _node("hand")
    assert res["failures"] == [], "\n".join(res["failures"][:20])


@pytest.mark.parametrize("seed", [3, 11])
def test_ob_ote_khop_timeline_va_replay_nhan_qua(seed):
    bars = _random_bars(seed, 1500)
    algo = IctStructureAlgorithm(**_p())
    full = run_algorithm(bars, algo)
    tl = full.timeline
    # Con trỏ: vài nến đang có vùng OTE và vài nến có OB mở (timeline) + vài nến bất kỳ.
    ote_at = [p["bar_index"] for p in tl if p["ote_lo"] is not None and p["bar_index"] > 150]
    ob_at = [p["bar_index"] for p in tl if p["ob_up_hi"] is not None and p["bar_index"] > 150]
    assert ote_at and ob_at
    cursors = sorted(set(ote_at[:: max(1, len(ote_at) // 3)][:3] + ob_at[:: max(1, len(ob_at) // 3)][:3] + [700]))
    data = {"digits": 2, "full": {"events": [e.to_dict() for e in full.events], "timeline": tl}, "prefixes": []}
    for c in cursors:
        a = IctStructureAlgorithm(**_p())
        px = run_algorithm(bars, a, upto_index=c)
        data["prefixes"].append({"cursor": c, "events": [e.to_dict() for e in px.events], "timeline": px.timeline,
                                 "pending": a.pending_state(), "close": bars[c].close})
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(data, fh, default=str)
        path = fh.name
    try:
        res = _node("real", path)
    finally:
        os.unlink(path)
    assert res["failures"] == [], "\n".join(res["failures"][:20])
