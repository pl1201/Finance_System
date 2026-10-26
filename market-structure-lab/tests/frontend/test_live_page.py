"""Trang Live MT5 riêng (/live, pages/live/*.js, plan_mt5_live.md §7): nạp đúng thứ tự, có chọn / tạo luồng, khung lớp ghép
từ mảnh dùng chung với trang Thử nghiệm, gợi ý giờ server gọi bằng POST JSON, không có lời gọi lệnh; trang Thử nghiệm không
còn chế độ Live."""
from __future__ import annotations

import re

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.routers.pages import PAGES
from tests.helpers import assert_page_scripts_served

client = TestClient(app)


def test_trang_live_rieng_nap_dung_thu_tu_va_co_dieu_khien_luong():
    html = client.get("/live").text
    srcs = assert_page_scripts_served(client, "/live")
    order = [srcs.index(s) for s in ("/app/js/lib/layers.js", "/app/js/lib/bottom_panel.js", "/app/js/chart/market-chart.js", "/app/js/chart/sub-pane.js",
                                     "/app/js/chart/pane-host.js", "/app/js/pages/live/state.js",
                                     "/app/js/pages/live/view.js", "/app/js/pages/live/main.js")]
    assert order == sorted(order)
    assert not [s for s in srcs if s.startswith("/app/js/pages/lab/")]          # không kéo theo module của trang Thử nghiệm
    for el in ('id="lv-feed"', 'id="lv-new"', 'id="lv-toggle"', 'id="live-modal"', 'id="lv-tz"', 'id="lv-check-tz"',
               'id="forward-body"', 'id="events-table"', 'id="chart"', 'id="pane-wrap"', 'id="ict-status"',
               'id="ict-nd-panel"', 'id="rp-explain"', 'class="nav-link active" href="/live"', "không gửi lệnh",
               'id="btn-toggle-bottom"', 'id="bottom-resizer"'):
        assert el in html, el
    page_js = "".join(client.get("/app/js/pages/live/%s.js" % f).text for f in ("state", "view", "main"))
    api_js = client.get("/app/js/lib/api.js").text
    assert "request('POST', '/api/live/hint'" in api_js     # nối terminal → chỉ POST JSON (trang lạ không gọi được)
    for word in ("order_send", "positions_get", "account_info"):
        assert word not in page_js and word not in api_js


def test_khung_lop_ghep_tu_manh_dung_chung_o_ca_hai_trang():
    lab, live = client.get("/").text, client.get("/live").text
    assert "<!--#include" not in lab and "<!--#include" not in live                  # đã ghép hết lúc phục vụ
    layers = lambda h: re.findall(r'data-layer="(ict_[a-z0-9_]+)"', h)  # noqa: E731
    assert layers(lab) == layers(live) and "ict_nd_pane" in layers(live) and len(layers(live)) > 15
    assert '<div id="ict-layers" class="layers" hidden>' in live                      # hiện theo plugin của luồng (panels)
    for raw, page in (("/app/index.html", "/"), ("/app/live.html", "/live"), ("/app/", "/"), ("/app/Live.HTML", "/live")):
        assert client.get(raw).text == client.get(page).text, raw                     # file .html dưới /app cũng đã ghép
    js = client.get("/app/js/pages/live/main.js")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]       # file tĩnh khác phục vụ thẳng


def test_moi_trang_co_lien_ket_live_va_trang_thu_nghiem_khong_con_che_do_live():
    for path in PAGES:
        assert 'href="/live"' in client.get(path).text, path
    lab = client.get("/").text
    srcs = assert_page_scripts_served(client, "/")
    for gone in ('data-mode="live"', 'id="live-bar"', 'id="live-modal"', 'id="lv-feed"'):
        assert gone not in lab, gone
    assert not [s for s in srcs if "/live/" in s or s.endswith("/live.js")]
    assert "/app/js/chart/pane-host.js" in srcs and "/app/js/lib/layers.js" in srcs
