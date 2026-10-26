"""Lỗi nghiệp vụ trả về cho giao diện. ``main.py`` ánh xạ sang mã HTTP."""
from __future__ import annotations


class ServiceError(Exception):
    """Lỗi nghiệp vụ có thông điệp hiển thị được cho người dùng (HTTP 400)."""


class NotFoundError(ServiceError):
    """Không tìm thấy đối tượng được hỏi trực tiếp theo id (HTTP 404)."""
