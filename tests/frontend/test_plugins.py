"""Plugin hiển thị theo thuật toán (frontend/js/algos/): thứ tự nạp và ranh giới với lõi chart / trang."""
from __future__ import annotations

import os
import re

from fastapi.testclient import TestClient

from backend.app.main import app
from tests.helpers import assert_page_scripts_served

client = TestClient(app)

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
JS_DIR = os.path.join(REPO, "frontend", "js")
PAGES = ("/", "/gan-nhan", "/danh-gia")


def test_moi_plugin_nap_o_ca_ba_trang_giua_registry_va_chart():
    plugins = sorted(
        "/app/js/algos/" + f for f in os.listdir(os.path.join(JS_DIR, "algos"))
        if f.endswith(".js") and f != "registry.js"
    )
    assert len(plugins) >= 4, plugins
    for path in PAGES:
        srcs = assert_page_scripts_served(client, path)
        reg = srcs.index("/app/js/algos/registry.js")
        chart = srcs.index("/app/js/chart/market-chart.js")
        assert srcs.index("/app/js/lib/format.js") < srcs.index("/app/js/chart/series.js") < reg, path
        for p in plugins:
            # MarketChart tạo series của mọi plugin khi khởi tạo → plugin phải đăng ký trước.
            assert p in srcs, (path, p)
            assert reg < srcs.index(p) < chart, (path, p)
        assert srcs.index("/app/js/chart/overlays.js") > chart, path


def test_loi_chart_va_trang_khong_so_ten_thuat_toan():
    """Phần riêng thuật toán nằm ở algos/. Ngoại lệ duy nhất: run baseline swing_pivot 3/3 (AGENTS.md §11)."""
    names = ("dc_atr_structure", "indicator_baseline", "hmm_online",
             "swing_hierarchy", "swing_pivot")
    pat = re.compile(r"""['"](%s)['"]""" % "|".join(names))
    allowed = {("pages/lab/run.js", "swing_pivot")}
    found = []
    for sub in ("chart", "pages", "lib"):
        for root, _dirs, files in os.walk(os.path.join(JS_DIR, sub)):
            for name in files:
                if not name.endswith(".js"):
                    continue
                full = os.path.join(root, name)
                rel = os.path.relpath(full, JS_DIR).replace(os.sep, "/")
                with open(full, encoding="utf-8") as fh:
                    for m in pat.finditer(fh.read()):
                        if (rel, m.group(1)) not in allowed:
                            found.append((rel, m.group(1)))
    assert not found, found
