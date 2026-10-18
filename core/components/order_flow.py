"""[OF] Order flow đọc theo thanh khoản: run + shift (``ict_structure`` v0.3.0).

Người dùng chốt ngày 06/10/2026 — khảo sát và lý do: ``docs/research/nghien_cuu_orderflow_ict.md``.
Order flow ở đây là chuyện **giá vừa lấy thanh khoản phía nào** («thanh khoản → thanh khoản»), đọc từ
hai loại sự kiện ĐÃ XÁC NHẬN của lõi; không dùng sweep, FVG, displacement, HH/HL hay mức được bảo vệ.

Đầu vào ở nến t: các sự kiện xác nhận tại t, mỗi cái là ``(loại, chiều, event_id)``:

* ``LIQ_RUN_UP`` → ("run", +1), ``LIQ_RUN_DOWN`` → ("run", −1) — lấy BSL/SSL, close không quay lại
  trong cửa sổ W nến;
* ``SHIFT_UP`` → ("shift", +1), ``SHIFT_DOWN`` → ("shift", −1) — quét rồi displacement ngược chiều.

Trạng thái ∈ {``1`` tăng, ``-1`` giảm, ``0`` chưa rõ, ``None`` chưa có — chưa có run/shift nào kể từ
đầu run}. Cập nhật tại t, chỉ khi t có ít nhất một sự kiện (**quy tắc A**):

1. có cả chiều +1 và −1 trong cùng nến → 0, lý do ``hai_chieu_cung_nen``;
2. ngược lại, gọi chiều duy nhất là d:

   * có shift chiều d → d, lý do ``shift_tang`` / ``shift_giam`` — kể cả khi đang −d (shift lật thẳng);
   * chỉ có run: đang None / 0 / d → d, lý do ``run_tang`` / ``run_giam``; đang −d → 0, lý do
     ``run_nguoc_chieu`` (run phía ngược không lật ngay mà thành «chưa rõ» — ICT «sitting on my hands»);

3. giá trị mới bằng giá trị cũ → **không đổi gì**: sự kiện cùng chiều chỉ «ủng hộ» (ghi vào
   ``last_support``), không phát sự kiện, giữ ``since`` / ``reason``;
4. khác → đổi: ``since = t``, ``reason`` = mã ở trên, sự kiện kích hoạt (``trigger_id``) = shift nếu có,
   không thì run; ``hai_chieu_cung_nen`` không có sự kiện kích hoạt.

Quy tắc B (hai phía đều bị run trong N nến → chưa rõ) đã bỏ: gần như không xảy ra (ở M15, N = 4/8/16 nến:
thêm < 0.1 đoạn chưa rõ mỗi ngày, ≤ 0.5 điểm % thời gian — ``research/orderflow_rules.py``). Tương đương
``rule_a`` của script khảo sát khi coi None = 0.

Đây là **mô tả**, không phải tín hiệu hay dự báo: khảo sát không thấy cách đọc order flow nào đoán phía
thanh khoản bị lấy kế tiếp tốt hơn mốc ngẫu nhiên. Máy trạng thái thuần — không biết nến, chỉ nhận chỉ
số nến và danh sách sự kiện theo thứ tự phát.
"""
from __future__ import annotations

from typing import Any, Optional, Sequence

RUN = "run"
SHIFT = "shift"

RUN_UP = "run_tang"
RUN_DOWN = "run_giam"
SHIFT_UP = "shift_tang"
SHIFT_DOWN = "shift_giam"
OPPOSITE_RUN = "run_nguoc_chieu"
BOTH_SIDES = "hai_chieu_cung_nen"
#: Mọi mã lý do, thứ tự cố định (thống kê «theo lý do»).
REASONS = (RUN_UP, RUN_DOWN, SHIFT_UP, SHIFT_DOWN, OPPOSITE_RUN, BOTH_SIDES)

#: Trạng thái → chữ hiển thị.
FLOW_TEXT_VI: dict[Optional[int], str] = {1: "tăng", -1: "giảm", 0: "chưa rõ", None: "chưa có"}
#: Trạng thái → khoá thống kê.
FLOW_KEYS: dict[Optional[int], str] = {1: "tang", -1: "giam", 0: "chua_ro", None: "chua_co"}
#: Mã lý do → câu giải thích.
FLOW_REASON_VI: dict[str, str] = {
    RUN_UP: "Run lên: lấy BSL, close không quay lại trong cửa sổ",
    RUN_DOWN: "Run xuống: lấy SSL, close không quay lại trong cửa sổ",
    SHIFT_UP: "Shift tăng: quét SSL rồi displacement tăng",
    SHIFT_DOWN: "Shift giảm: quét BSL rồi displacement giảm",
    OPPOSITE_RUN: "Run phía ngược với order flow đang có → chưa rõ (không lật ngay)",
    BOTH_SIDES: "Run/shift hai chiều trong cùng một nến → chưa rõ",
}
#: Trạng thái → điều gì làm nó đổi (cho trạng thái replay).
FLOW_CONDITIONS_VI: dict[Optional[int], tuple[str, ...]] = {
    1: (
        "Run vùng phía dưới (SSL) → chưa rõ",
        "Shift giảm (quét BSL rồi displacement giảm) → giảm",
        "Run/shift hai chiều trong cùng một nến → chưa rõ",
    ),
    -1: (
        "Run vùng phía trên (BSL) → chưa rõ",
        "Shift tăng (quét SSL rồi displacement tăng) → tăng",
        "Run/shift hai chiều trong cùng một nến → chưa rõ",
    ),
    0: ("Run hoặc shift kế tiếp đặt chiều (lên → tăng, xuống → giảm)",),
    None: ("Run hoặc shift đầu tiên đặt chiều",),
}


class OrderFlow:
    """Trạng thái order flow theo quy tắc A. Đọc ``state``, ``since``, ``reason``, ``trigger_id``,
    ``last_support`` sau mỗi ``on_bar``."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.state: Optional[int] = None            # 1 | -1 | 0 | None
        self.since: Optional[int] = None            # nến bắt đầu giá trị hiện tại
        self.reason: Optional[str] = None           # mã lý do của lần đổi gần nhất
        self.trigger_id: Optional[str] = None       # sự kiện kích hoạt lần đổi gần nhất
        #: run/shift cùng chiều gần nhất không đổi trạng thái: {"nen", "su_kien", "loai"}; xoá khi đổi.
        self.last_support: Optional[dict[str, Any]] = None
        self._t: Optional[int] = None

    def on_bar(self, t: int, events: Sequence[tuple[str, int, str]]) -> Optional[dict[str, Any]]:
        """Nến t với các run/shift xác nhận tại t (theo thứ tự phát). Trả mô tả lần đổi, hoặc None nếu
        trạng thái giữ nguyên (gồm cả khi không có sự kiện)."""
        if self._t is not None and t <= self._t:
            raise ValueError("Order flow: nến phải tăng dần (nhận #%d sau #%d)." % (t, self._t))
        self._t = t
        if not events:
            return None
        for kind, d, eid in events:
            if kind not in (RUN, SHIFT) or d not in (1, -1):
                raise ValueError("Order flow: sự kiện sai dạng %r." % ((kind, d, eid),))
        cur = self.state
        dirs = {d for _k, d, _e in events}
        trigger: Optional[tuple[str, int, str]] = None
        if len(dirs) > 1:
            new, reason = 0, BOTH_SIDES
        else:
            d = events[0][1]
            trigger = next((e for e in events if e[0] == SHIFT), None)
            if trigger is not None:
                new, reason = d, (SHIFT_UP if d == 1 else SHIFT_DOWN)
            else:
                trigger = events[0]
                if cur == -d:
                    new, reason = 0, OPPOSITE_RUN
                else:
                    new, reason = d, (RUN_UP if d == 1 else RUN_DOWN)
        if new == cur:
            if trigger is not None:                 # cùng chiều đang có: chỉ ủng hộ
                self.last_support = {"nen": t, "su_kien": trigger[2], "loai": trigger[0]}
            return None
        change = {
            "nen": t,
            "tu": cur,
            "sang": new,
            "ly_do": reason,
            "trigger": trigger[2] if trigger is not None else None,
            "basis": [e[2] for e in events],
            "trang_thai_cu_tu_nen": self.since,
            "trang_thai_cu_so_nen": (t - self.since) if self.since is not None else None,
        }
        self.state, self.since, self.reason = new, t, reason
        self.trigger_id = change["trigger"]
        self.last_support = None
        return change

    def snapshot(self, last_index: Optional[int], above: Optional[dict[str, Any]] = None,
                 below: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        """Trạng thái hiện tại (bản sao). ``above`` / ``below``: vùng còn nguyên gần nhất phía trên (BSL) /
        dưới (SSL) do người gọi đưa — tăng thì vùng cùng chiều là phía trên, giảm thì phía dưới; chưa rõ /
        chưa có thì không gán vùng nào."""
        s = self.since
        same = above if self.state == 1 else below if self.state == -1 else None
        opposite = below if self.state == 1 else above if self.state == -1 else None
        return {
            "trang_thai": self.state,
            "trang_thai_vi": FLOW_TEXT_VI[self.state],
            "tu_nen": s,
            "so_nen": (last_index - s) if s is not None and last_index is not None else None,
            "ly_do": self.reason,
            "ly_do_vi": FLOW_REASON_VI[self.reason] if self.reason else None,
            "su_kien": self.trigger_id,
            "ung_ho_gan_nhat": dict(self.last_support) if self.last_support else None,
            "vung_cung_chieu": same,
            "vung_nguoc_chieu": opposite,
            "dieu_kien_vi": list(FLOW_CONDITIONS_VI[self.state]),
        }
