"""Cấu hình chung cho test: dùng thư mục dữ liệu tạm, không đụng data/ thật."""
from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="msl_test_")
os.environ.setdefault("MSL_DATA_DIR", _TMP)
os.environ.setdefault("MSL_DB_PATH", os.path.join(_TMP, "test.sqlite"))
