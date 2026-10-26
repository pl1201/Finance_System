"""Route HTTP theo mảng. Route chỉ đọc request, gọi ``services`` và trả kết quả.

``main.py`` đăng ký theo đúng thứ tự ``ROUTERS``.
"""
from backend.app.routers import datasets, evaluations, labels, live, llm, mql5, replay, runs, system

ROUTERS = [
    system.router,
    datasets.router,
    runs.router,
    labels.router,
    evaluations.router,
    mql5.router,
    replay.router,
    live.router,
    llm.router,
]
