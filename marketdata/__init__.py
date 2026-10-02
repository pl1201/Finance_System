"""Bộ sinh dữ liệu thị trường XAUUSD/EURUSD (M1 → M5/M15/H1/H4/D1, giờ UTC) kèm lịch phiên khai báo.

Đường dẫn mặc định:

* ``ROOT``     — thư mục gốc của repo;
* ``DATA_DIR`` — nơi ghi dữ liệu tải về và dữ liệu dựng ra (mặc định ``ROOT/data``, đổi bằng biến
  môi trường ``MDP_DATA_DIR``). Thư mục này KHÔNG đưa lên git;
* ``CAL_DIR``  — lịch phiên khai báo (``ROOT/calendars``, có trong git).
"""
from __future__ import annotations

import os

__version__ = "1.0.0"

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.abspath(os.environ.get("MDP_DATA_DIR") or os.path.join(ROOT, "data"))
CAL_DIR = os.path.join(ROOT, "calendars")
