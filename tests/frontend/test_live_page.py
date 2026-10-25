"""Chế độ Live trên trang Thử nghiệm (pages/lab/live.js, plan_mt5_live.md §7): nạp đúng thứ tự, có thanh / hộp tạo luồng,
gợi ý giờ server gọi bằng POST JSON, trang không có lời gọi lệnh nào."""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app
from tests.helpers import assert_page_scripts_served

client = TestClient(app)


def test_trang_thu_nghiem_co_che_do_live():
    html = client.get("/").text
    srcs = assert_page_scripts_served(client, "/")
    order = [srcs.index("/app/js/pages/lab/" + f) for f in ("replay.js", "live.js", "main.js")]
    assert order == sorted(order)                       # live.js dùng L.renderReplay; main.js gọi L.bindLive
    for el in ('data-mode="live"', 'id="live-bar"', 'id="lv-feed"', 'id="lv-toggle"', 'id="live-modal"', 'id="lv-tz"',
               'id="lv-check-tz"', "không kết nối broker, không gửi lệnh"):
        assert el in html, el
    live_js = client.get("/app/js/pages/lab/live.js").text
    api_js = client.get("/app/js/lib/api.js").text
    assert "request('POST', '/api/live/hint'" in api_js     # nối terminal → chỉ POST JSON (trang lạ không gọi được)
    for word in ("order_send", "positions_get", "account_info"):
        assert word not in live_js and word not in api_js
