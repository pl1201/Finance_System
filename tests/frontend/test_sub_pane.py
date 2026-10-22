"""Khung phụ dưới chart chính (frontend/js/chart/sub-pane.js, hook `pane` của plugin — algos/registry.js):

* node nạp script thật với Lightweight Charts / DOM giả (tests/frontend/sub_pane_check.js): SubPane — giao diện chung,
  trục giá rộng bằng chart chính, khoảng nhìn + crosshair đồng bộ hai chiều không vọng lại, bỏ qua khi ẩn, draw (cả chuỗi
  / thêm cuối), reset; hook `pane` của ict_structure — lớp bật sẵn, has, init (thang dọc cố định), points cả chuỗi / chỉ
  nến mới, legend;
* trang Thử nghiệm nạp script đúng chỗ (sau Lightweight Charts / format.js / market-chart.js, trước pages/lab), có khung
  ngay dưới chart chính (trên panel baseline) với dòng chú giải và ô lớp; hai trang kia không nạp.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from tests.helpers import assert_page_scripts_served

client = TestClient(app)

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(HERE, "sub_pane_check.js")
NODE = shutil.which("node")
SUB_PANE = "/app/js/chart/sub-pane.js"


@pytest.mark.skipif(NODE is None, reason="cần node để chạy JS")
def test_sub_pane_voi_lightweight_charts_gia():
    out = subprocess.run([NODE, SCRIPT], capture_output=True, text=True, encoding="utf-8", timeout=120)
    assert out.returncode == 0, out.stderr
    res = json.loads(out.stdout)
    assert res["checks"] > 0
    assert res["failures"] == [], "\n".join(res["failures"][:20])


def test_trang_thu_nghiem_nap_khung_phu_duoi_chart():
    html = client.get("/").text
    srcs = assert_page_scripts_served(client, "/")
    i = srcs.index(SUB_PANE)
    assert srcs.index("/app/vendor/lightweight-charts.standalone.production.js") < i
    assert srcs.index("/app/js/lib/format.js") < srcs.index("/app/js/chart/market-chart.js") < i
    lab = [s for s in srcs if s.startswith("/app/js/pages/lab/")]
    assert lab and all(i < srcs.index(s) for s in lab)
    assert re.search(r'<script src="/app/js/chart/sub-pane\.js\?v=[\d.]+"></script>', html)
    # ngay dưới chart chính, trên panel baseline; ẩn sẵn (chỉ hiện khi plugin có hook `pane` và có dữ liệu)
    assert html.index('<div id="chart">') < html.index('id="pane-wrap"') < html.index('id="chart2-wrap"')
    assert '<div id="pane-wrap" class="pane-wrap" hidden>' in html
    assert 'id="pane-legend"' in html and '<div id="pane"></div>' in html
    m = re.search(r'<label class="check" title="([^"]+)"><input type="checkbox" data-layer="ict_nd_pane" checked>', html)
    assert m, "thiếu ô lớp «Khung trạng thái»"
    for word in ("trend lên", "trend xuống", "range", "sideway nhiễu", "nén", "không phải dự báo"):
        assert word in m.group(1), word
    for path in ("/gan-nhan", "/danh-gia"):
        assert SUB_PANE not in assert_page_scripts_served(client, path), path
    with open(os.path.join(REPO, "frontend", "css", "app.css"), encoding="utf-8") as fh:
        css = fh.read()
    assert ".pane-wrap" in css and "#pane {" in css
