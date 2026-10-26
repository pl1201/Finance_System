"""Giao diện tĩnh: các trang HTML và thư mục ``/app`` (JS/CSS/vendor).

Trang có thể ghép mảnh HTML dùng chung lúc phục vụ: dòng ``<!--#include ten-manh -->`` được thay bằng nội dung
``frontend/partials/ten-manh.html`` (vd khung lớp của ``ict_structure`` dùng ở trang Thử nghiệm và trang Live MT5). Ghép ở
mọi đường phục vụ HTML — đường dẫn trang (``/``, ``/live``…) lẫn file ``/app/*.html`` — nên không có bản thô thiếu mảnh.
"""
from __future__ import annotations

import os
import re

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from backend.app import config

#: Đường dẫn trang → file HTML trong ``frontend/``.
PAGES = {"/": "index.html", "/danh-gia": "danh-gia.html", "/gan-nhan": "gan-nhan.html", "/live": "live.html"}
INCLUDE = re.compile(r"<!--#include ([a-z0-9-]+) -->")


def render_html(path: str) -> HTMLResponse:
    """File HTML đã ghép mảnh (đọc lại mỗi lần — sửa HTML không cần khởi động lại backend)."""
    def part(m: re.Match) -> str:
        with open(os.path.join(config.FRONTEND_DIR, "partials", m.group(1) + ".html"), encoding="utf-8") as fh:
            return fh.read()

    with open(path, encoding="utf-8") as fh:
        return HTMLResponse(INCLUDE.sub(part, fh.read()))


class FrontendFiles(StaticFiles):
    """File tĩnh của frontend; file ``.html`` được ghép mảnh như khi mở qua đường dẫn trang."""

    async def get_response(self, path, scope):
        resp = await super().get_response(path, scope)
        if isinstance(resp, FileResponse) and str(resp.path).lower().endswith(".html"):
            return render_html(resp.path)
        return resp


def mount_frontend(app: FastAPI) -> None:
    if not os.path.isdir(config.FRONTEND_DIR):
        return
    app.mount("/app", FrontendFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
    for url, filename in PAGES.items():
        app.add_api_route(url, _page(filename), methods=["GET"])


def _page(filename: str):
    path = os.path.join(config.FRONTEND_DIR, filename)

    def page() -> HTMLResponse:
        return render_html(path)

    page.__name__ = "page_" + filename.replace("-", "_").replace(".html", "")
    return page
