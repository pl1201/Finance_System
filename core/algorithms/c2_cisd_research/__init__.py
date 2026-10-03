"""C2 Sweep + CISD — bản nghiên cứu closed-bar M15–H4 (``docs/thuat_toan_c2_cisd.md``).

Chuyển thể từ CantoLab Open Source Fractal (MIT, Copyright (c) 2026 cantolab, commit
``1bb53262deba9456f2b1a85d15c6ac5a5e880cf7``); toàn văn giấy phép trong ``algorithm.py``
và ``third_party/open-source-fractal/LICENSE``.

| Module | Việc |
|---|---|
| ``algorithm`` | ``C2CisdResearchAlgorithm``: thứ tự xử lý trong nến, vòng đời setup, sự kiện |
| ``state`` | hằng, mức CISD đang theo dõi, setup C2, tiện ích màu nến |
| ``levels`` | chọn mức CISD (các nhánh Pine) — hàm thuần |
| ``metrics`` | vòng đời setup (từ log) và MFE/MAE (chỉ để đánh giá) |
| ``eval_targets`` | mục tiêu chấm ``c2`` / ``cisd`` |
"""
from core.algorithms.c2_cisd_research.algorithm import C2CisdResearchAlgorithm
from core.algorithms.c2_cisd_research.state import SOURCE_COMMIT, SOURCE_REPO

__all__ = ["C2CisdResearchAlgorithm", "SOURCE_COMMIT", "SOURCE_REPO"]
