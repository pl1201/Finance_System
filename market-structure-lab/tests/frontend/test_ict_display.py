"""Hiển thị ict_structure chế độ Gọn (plan_hien_thi_ict §3, §5): hàm thuần frontend/js/algos/ict_structure_view.js.

Chạy bằng node (tests/frontend/ict_display_check.js nạp file JS trong vm, không cần trình duyệt):
* kịch bản dựng tay — vòng đời vùng (tạo, gộp EQ, sweep, run, chưa rõ, đang chờ), lọc «Hiện tại» (≤ 3 nhóm kết cục mỗi
  phía), gộp vùng trùng, thứ tự ưu tiên nhãn + ký hiệu thay chữ, đối tượng vẽ, nhân quả ở mọi con trỏ, dòng trạng thái,
  tooltip, kết quả cũ thiếu khoá; Chi tiết (FVG + vòng đời mở / chạm / lấp + CE, Protected và dealing range đọc đúng
  timeline, ITH/ITL + nhãn HH…, displacement) và Lịch sử (mọi vùng / shift / FVG tới con trỏ, mờ dần theo tuổi), nhân quả
  của cả hai;
* dữ liệu lõi thật (chuỗi nến ngẫu nhiên có khoảng trống) — vùng còn nguyên gần nhất suy từ sự kiện KHỚP
  liq_above / liq_below của timeline ở mọi nến; replay prefix (sự kiện + pending_state tại con trỏ) cho cùng đối tượng
  vẽ như toàn bộ sự kiện lọc theo con trỏ (cả Chi tiết + Lịch sử); không vùng nào hiện trước nến xác nhận; vòng đời FVG.
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
SCRIPT = os.path.join(HERE, "ict_display_check.js")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="cần node để chạy hàm JS thuần")


def _node(*args: str) -> dict:
    out = subprocess.run([NODE, SCRIPT, *args], capture_output=True, text=True, encoding="utf-8", timeout=300)
    assert out.returncode == 0, out.stderr
    res = json.loads(out.stdout)
    assert res["checks"] > 0
    return res


def _dump(res, algo) -> dict:
    return {
        "events": [e.to_dict() for e in res.events],
        "timeline": res.timeline,
        "pending": algo.pending_state(),
    }


def test_ham_thuan_kich_ban_dung_tay():
    res = _node("hand")
    assert res["failures"] == [], "\n".join(res["failures"][:20])
    assert res["checks"] >= 300


@pytest.mark.parametrize("seed", [3, 11])
def test_vung_gan_nhat_khop_timeline_va_replay_nhan_qua(seed):
    bars = _random_bars(seed, 1500)
    algo = IctStructureAlgorithm(**_p())
    full = run_algorithm(bars, algo)
    data = {"digits": 2, "full": _dump(full, algo), "prefixes": []}
    tl = full.timeline
    # Con trỏ replay: vài nến đang có vùng chờ sweep/run (pending_state mới biết) + vài nến bất kỳ.
    waiting = [p["bar_index"] for p in tl if p["pending_takes"] and p["bar_index"] > 200]
    cursors = sorted(set(waiting[:: max(1, len(waiting) // 4)][:4] + [400, 977, len(bars) - 2]))
    assert waiting, "dữ liệu phải có lúc đang chờ sweep/run"
    for c in cursors:
        a = IctStructureAlgorithm(**_p())
        px = run_algorithm(bars, a, upto_index=c)
        d = _dump(px, a)
        d["cursor"] = c
        data["prefixes"].append(d)
    # Khung lớn (0.4.0): OHLC để giao diện tự gộp nến H4 đang hình thành + nến H4 đang hình thành của lõi ở thêm vài con trỏ
    # (gồm nến ngay sau / đúng lúc chốt một nến H4) để so.
    data["bars"] = [{"index": b.index, "open": b.open, "high": b.high, "low": b.low, "close": b.close} for b in bars]
    data["forming"] = []
    for c in sorted(set(list(range(150, len(bars) - 1, 97)) + [16 * k + j for k in (30, 61) for j in (-1, 0, 1)])):
        a = IctStructureAlgorithm(**_p())
        run_algorithm(bars, a, upto_index=c)
        kl = a.pending_state()["khung_lon"]
        data["forming"].append({"cursor": c, "forming": (kl.get("H4") or {}).get("dang_hinh_thanh")})
    # Thư mục tạm của conftest (MSL_DATA_DIR) — không dùng fixture tmp_path.
    fd, path = tempfile.mkstemp(suffix=".json", prefix="ict_real_", dir=os.environ.get("MSL_DATA_DIR"))
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, default=str)
    try:
        res = _node("real", path)
    finally:
        os.remove(path)
    assert res["failures"] == [], "\n".join(res["failures"][:20])
    assert res["info"]["nen_so_khop"] == len(bars)
    assert res["info"]["cho"] >= 1
    assert res["info"]["forming_so"]["co"] >= 5 and res["info"]["dol_nen"] > 20
