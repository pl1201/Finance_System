"""FastAPI app: API nghiên cứu cấu trúc thị trường + phục vụ giao diện tĩnh.

Route nằm trong ``routers/`` (mỗi mảng một file), request model trong ``schemas/``,
nghiệp vụ trong ``services/``, lưu trữ trong ``storage/``. File này chỉ dựng app,
middleware và bộ xử lý lỗi.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from backend.app.errors import NotFoundError, ServiceError
from backend.app.routers import ROUTERS
from backend.app.routers.pages import mount_frontend
from backend.app.services import llm
from backend.app.services.live import live_manager


@asynccontextmanager
async def _lifespan(_app):  # noqa: ANN001
    """Luồng nền live (MT5 chỉ đọc) mở lại các luồng đang chạy; tắt khi backend dừng (kèm client HTTP của trợ lý)."""
    live_manager.start()
    yield
    live_manager.shutdown()
    llm.close()


app = FastAPI(
    lifespan=_lifespan,
    title="Market Structure Lab",
    description=(
        "Công cụ nghiên cứu thuật toán nhận diện cấu trúc thị trường. "
        "Chạy local, không kết nối broker, không gửi lệnh."
    ),
    version="0.3.1",
)


@app.middleware("http")
async def _no_stale_frontend(request, call_next):  # noqa: ANN001
    """Bắt trình duyệt hỏi lại server mỗi lần mở trang / JS / CSS.

    Không có header này, trình duyệt được phép tự dùng bản cũ trong cache một
    lúc (heuristic caching), nên người dùng sửa code xong vẫn thấy giao diện cũ.
    ``no-cache`` vẫn dùng ETag/Last-Modified nên file không đổi chỉ tốn một
    phản hồi 304, không tải lại.
    """
    response = await call_next(request)
    if not request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.exception_handler(ServiceError)
async def _service_error_handler(_request, exc: ServiceError):  # noqa: ANN001
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
async def _not_found_handler(_request, exc: NotFoundError):  # noqa: ANN001
    return JSONResponse(status_code=404, content={"detail": str(exc)})


for _router in ROUTERS:
    app.include_router(_router)

mount_frontend(app)
