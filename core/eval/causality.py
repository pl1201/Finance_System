"""Kiểm tra bất biến nhân quả trên sự kiện ĐÃ LƯU của một lần chạy.

Đây không phải test suite. Bộ pytest xanh không khiến mọi run mang trạng thái
«đạt nhân quả». Chỉ các kiểm tra dưới đây, trên đúng thuật toán/tham số/phạm vi
của run đó, mới được ghi vào kết quả đánh giá.
"""
from __future__ import annotations

from typing import Any, Sequence


STATUS_CHUA_KIEM_TRA = "chua_kiem_tra"
STATUS_CO_VI_PHAM = "co_vi_pham"
STATUS_DAT = "dat_kiem_tra"


def check_stored_event_invariants(
    events: Sequence[Any],
    *,
    warmup_bars: int = 0,
    bars_processed: int = 0,
) -> dict[str, Any]:
    """Bất biến đọc được từ sự kiện đã lưu — không chạy lại thuật toán trên prefix.

    Phát hiện: xác nhận trước nến sự kiện, trễ âm, nến ngoài phạm vi, xác nhận
    trước khi đủ warm-up. Không chứng minh thuật toán không nhìn tương lai.
    """
    checks: list[dict[str, Any]] = []
    violations: list[str] = []

    def _as_dict(e: Any) -> dict[str, Any]:
        if isinstance(e, dict):
            return e
        return {
            "event_id": e.event_id,
            "event_bar_index": e.event_bar_index,
            "confirmed_bar_index": e.confirmed_bar_index,
            "confirmation_lag_bars": e.confirmation_lag_bars,
            "confirmed_at": str(getattr(e, "confirmed_at", "")),
        }

    n = 0
    for raw in events:
        e = _as_dict(raw)
        n += 1
        eid = e.get("event_id") or "?"
        ev_i = int(e["event_bar_index"])
        cf_i = int(e["confirmed_bar_index"])
        lag = int(e.get("confirmation_lag_bars", cf_i - ev_i))
        if cf_i < ev_i:
            violations.append("%s: confirmed_bar_index (%s) < event_bar_index (%s)" % (eid, cf_i, ev_i))
        if lag != cf_i - ev_i:
            violations.append(
                "%s: confirmation_lag_bars=%s khác confirmed-event=%s" % (eid, lag, cf_i - ev_i)
            )
        if lag < 0:
            violations.append("%s: độ trễ âm (%s)" % (eid, lag))
        if warmup_bars and cf_i < warmup_bars - 1:
            violations.append(
                "%s: xác nhận tại nến %s trước warm-up %s" % (eid, cf_i, warmup_bars)
            )
        if bars_processed and (ev_i < 0 or cf_i >= bars_processed or ev_i >= bars_processed):
            violations.append(
                "%s: nến sự kiện/xác nhận nằm ngoài bars_processed=%s" % (eid, bars_processed)
            )

    checks.append(
        {
            "id": "confirmed_khong_truoc_event",
            "label_vi": "Nến xác nhận không trước nến sự kiện",
            "ok": not any("confirmed_bar_index" in v and "< event" in v for v in violations),
        }
    )
    checks.append(
        {
            "id": "lag_khop_chi_so",
            "label_vi": "Độ trễ = confirmed_bar_index − event_bar_index",
            "ok": not any("confirmation_lag_bars" in v for v in violations),
        }
    )
    checks.append(
        {
            "id": "khong_xac_nhan_trong_warmup",
            "label_vi": "Không xác nhận trong giai đoạn warm-up",
            "ok": not any("warm-up" in v for v in violations),
        }
    )

    if not events:
        status = STATUS_CHUA_KIEM_TRA
        note = "Chưa có sự kiện để kiểm tra bất biến trên run này."
    elif violations:
        status = STATUS_CO_VI_PHAM
        note = "Phát hiện %d vi phạm bất biến trên sự kiện đã lưu." % len(violations)
    else:
        status = STATUS_DAT
        note = (
            "Đạt kiểm tra bất biến trên %d sự kiện đã lưu (xác nhận ≥ sự kiện, "
            "trễ khớp chỉ số, không xác nhận trong warm-up). "
            "Không thay thế test prefix/tương lai của bộ pytest."
            % n
        )

    return {
        "status": status,
        "status_label_vi": {
            STATUS_CHUA_KIEM_TRA: "Chưa kiểm tra",
            STATUS_CO_VI_PHAM: "Có vi phạm",
            STATUS_DAT: "Đạt kiểm tra",
        }[status],
        "n_events": n,
        "n_violations": len(violations),
        "violations": violations[:40],
        "checks": checks,
        "note_vi": note,
        "pham_vi_vi": "Sự kiện đã lưu của đúng run (thuật toán, phiên bản, tham số, khoảng nến).",
    }
