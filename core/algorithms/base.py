"""Interface chung cho mọi thuật toán nhận diện cấu trúc thị trường.

Thiết kế theo kiểu **streaming / nhân quả**: lõi chỉ nhận từng nến ĐÃ ĐÓNG
theo thứ tự thời gian và trả về các sự kiện được xác nhận TẠI nến đó.

Điều này làm cho việc "không dùng dữ liệu tương lai" trở thành tính chất
cấu trúc của code chứ không phải một quy ước phải nhớ: hàm ``on_bar`` không
có cách nào nhìn thấy nến phía sau.

Thêm thuật toán mới (ví dụ HMM, BOCD) = tạo một lớp con của
:class:`StructureAlgorithm` và đăng ký trong ``core/registry.py``.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from core.types import Bar, StructureEvent


@dataclass(frozen=True)
class ParamSpec:
    """Mô tả một tham số để giao diện tự sinh form nhập liệu."""

    name: str
    label_vi: str
    type: str  # "int" | "float" | "bool" | "choice"
    default: Any
    min: Optional[float] = None
    max: Optional[float] = None
    step: Optional[float] = None
    choices: Optional[tuple[str, ...]] = None
    help_vi: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "label_vi": self.label_vi,
            "type": self.type,
            "default": self.default,
            "min": self.min,
            "max": self.max,
            "step": self.step,
            "choices": list(self.choices) if self.choices else None,
            "help_vi": self.help_vi,
        }


class StructureAlgorithm(abc.ABC):
    """Lớp cơ sở cho thuật toán nhận diện cấu trúc.

    Vòng đời:

    1. ``__init__(**params)`` — nhận tham số đã được validate.
    2. ``reset()`` — xoá toàn bộ trạng thái nội bộ.
    3. ``on_bar(bar)`` — gọi một lần cho MỖI nến đã đóng, theo đúng thứ tự
       tăng dần của ``bar.index``. Trả về danh sách sự kiện được xác nhận
       tại chính nến này (có thể rỗng).
    4. ``pending_state()`` — trạng thái tạm thời để hiển thị (KHÔNG phải
       sự kiện đã xác nhận).

    Hợp đồng bắt buộc:

    * ``on_bar`` không được sửa hoặc thu hồi sự kiện đã trả về trước đó.
    * Với cùng một chuỗi nến, kết quả phải tất định (deterministic).
    * ``confirmed_at`` của sự kiện trả về tại nến ``i`` phải bằng
      ``bar[i].close_time``.
    """

    #: Tên định danh, dùng làm khoá trong registry.
    name: str = "base"
    #: Tên hiển thị tiếng Việt.
    display_name_vi: str = "Thuật toán cơ sở"
    #: Phiên bản thuật toán — đổi khi quy tắc thay đổi để truy vết kết quả cũ.
    version: str = "0.0.0"
    #: Mô tả ngắn cho giao diện.
    description_vi: str = ""

    @classmethod
    def param_specs(cls) -> tuple[ParamSpec, ...]:
        """Danh sách tham số của thuật toán."""
        return ()

    @classmethod
    def validate_params(cls, raw: dict[str, Any] | None) -> dict[str, Any]:
        """Ép kiểu và kiểm tra tham số; trả về dict đã chuẩn hoá."""
        raw = dict(raw or {})
        out: dict[str, Any] = {}
        for spec in cls.param_specs():
            value = raw.get(spec.name, spec.default)
            try:
                if spec.type == "int":
                    value = int(value)
                elif spec.type == "float":
                    value = float(value)
                elif spec.type == "bool":
                    if isinstance(value, str):
                        value = value.strip().lower() in ("1", "true", "yes", "on")
                    value = bool(value)
                elif spec.type == "choice":
                    value = str(value)
                    if spec.choices and value not in spec.choices:
                        raise ValueError(
                            "Giá trị %r không thuộc %s" % (value, list(spec.choices))
                        )
                elif spec.type in ("str", "string"):
                    value = str(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "Tham số '%s' (%s) không hợp lệ: %s" % (spec.name, spec.label_vi, exc)
                ) from exc
            if spec.min is not None and value < spec.min:
                raise ValueError(
                    "Tham số '%s' phải >= %s (nhận %s)" % (spec.name, spec.min, value)
                )
            if spec.max is not None and value > spec.max:
                raise ValueError(
                    "Tham số '%s' phải <= %s (nhận %s)" % (spec.name, spec.max, value)
                )
            out[spec.name] = value
        return out

    @abc.abstractmethod
    def reset(self) -> None:
        """Xoá toàn bộ trạng thái nội bộ, đưa về như mới khởi tạo."""

    @abc.abstractmethod
    def on_bar(self, bar: Bar) -> list[StructureEvent]:
        """Xử lý một nến đã đóng, trả về sự kiện được xác nhận tại nến này."""

    def warmup_bars(self) -> int:
        """Số nến tối thiểu cần có trước khi thuật toán có thể sinh sự kiện."""
        return 0

    def pending_state(self) -> dict[str, Any]:
        """Trạng thái tạm thời (chưa xác nhận) để hiển thị, tuỳ chọn."""
        return {}

    def timeline_point(self, bar: Bar) -> Optional[dict[str, Any]]:
        """Trạng thái nội bộ SAU khi xử lý ``bar``, để vẽ lên chart.

        Engine gọi hàm này ngay sau mỗi ``on_bar``. Giá trị trả về mô tả
        thông tin thuật toán ĐÃ BIẾT tại nến đó — nhờ vậy overlay trên chart
        cũng tôn trọng tính nhân quả. Trả ``None`` nếu thuật toán không có
        chuỗi trạng thái cần vẽ.
        """
        return None

    def run(self, bars: Iterable[Bar]) -> list[StructureEvent]:
        """Chạy tuần tự trên một chuỗi nến. Tiện cho test và notebook."""
        self.reset()
        events: list[StructureEvent] = []
        for bar in bars:
            events.extend(self.on_bar(bar))
        return events
