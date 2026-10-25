"""Cấu hình đường dẫn của ứng dụng."""
from __future__ import annotations

import os

#: Thư mục gốc dự án (market-structure-lab/).
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)

DATA_DIR = os.environ.get("MSL_DATA_DIR") or os.path.join(PROJECT_ROOT, "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")
EXPORT_DIR = os.path.join(DATA_DIR, "exports")
DB_PATH = os.environ.get("MSL_DB_PATH") or os.path.join(DATA_DIR, "lab.sqlite")
#: Kho live riêng (nến MT5 + bản ghi dự báo, chỉ ghi thêm) — plan_mt5_live.md §2; tạo khi dùng lần đầu.
LIVE_DB_PATH = os.environ.get("MSL_LIVE_DB_PATH") or os.path.join(DATA_DIR, "live.sqlite")
FRONTEND_DIR = os.path.join(PROJECT_ROOT, "frontend")

#: Giới hạn an toàn cho ứng dụng chạy local.
MAX_UPLOAD_BYTES = 80 * 1024 * 1024        # 80 MB
MAX_BARS_PER_DATASET = 500_000
MAX_REPLAY_SESSIONS = 16

for _d in (DATA_DIR, RAW_DIR, EXPORT_DIR):
    os.makedirs(_d, exist_ok=True)
