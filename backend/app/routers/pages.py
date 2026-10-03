"""Giao diện tĩnh: ba trang HTML và thư mục ``/app`` (JS/CSS/vendor)."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app import config

#: Đường dẫn trang → file HTML trong ``frontend/``.
PAGES = {"/": "index.html", "/danh-gia": "danh-gia.html", "/gan-nhan": "gan-nhan.html"}


def mount_frontend(app: FastAPI) -> None:
    if not os.path.isdir(config.FRONTEND_DIR):
        return
    app.mount("/app", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
    for url, filename in PAGES.items():
        app.add_api_route(url, _page(filename), methods=["GET"])


def _page(filename: str):
    path = os.path.join(config.FRONTEND_DIR, filename)

    def page() -> FileResponse:
        return FileResponse(path)

    page.__name__ = "page_" + filename.replace("-", "_").replace(".html", "")
    return page
