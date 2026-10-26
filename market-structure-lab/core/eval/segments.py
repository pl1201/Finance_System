"""Đoạn phát triển / kiểm tra (walk-forward) khai báo theo thời gian trong protocol đánh giá.

Mỗi đoạn: ``{"name", "role": "dev" | "test", "start", "end"}`` — UTC, nửa mở ``[start, end)``
theo giờ MỞ nến. Khai **trước** khi xem kết quả (AGENTS.md §6.3).

* Khai đoạn thì **chỉ các đoạn được chấm**: mỗi đoạn là một cửa sổ chấm (giao với khoảng chấm
  ``coverage_*_index`` nếu có). Sự kiện ngoài mọi đoạn không bị tính FP — như ngoài khoảng chấm.
  Nhờ vậy nhãn gán ở vài cửa sổ rời nhau (vd 2 tuần trong đoạn phát triển + 2 tuần trong đoạn
  kiểm tra) chấm được mà phần không gán ở giữa không thành FP.
* Số tổng của run = **gộp các đoạn phát triển**. Đoạn kiểm tra không bao giờ lọt vào số tổng.
* Đoạn kiểm tra **khoá** mặc định: không chấm, không hiện số. Mở bằng ``test_unlocked`` trong
  protocol (ghi vào hash) — chỉ làm khi cấu hình đã chốt trên đoạn phát triển.
* Theo thời gian, không theo chỉ số nến: M5/M15/H1 là các không gian chỉ số khác nhau.
"""
from __future__ import annotations

import bisect
from datetime import datetime, timezone
from typing import Any, Optional, Sequence

ROLE_DEV = "dev"
ROLE_TEST = "test"
ROLES = (ROLE_DEV, ROLE_TEST)
ROLE_TEXT_VI = {ROLE_DEV: "phát triển", ROLE_TEST: "kiểm tra"}
MAX_SEGMENTS = 24
MAX_NAME = 40


def _parse_time(value: Any, what: str) -> datetime:
    if isinstance(value, datetime):
        t = value
    else:
        s = str(value or "").strip()
        if not s:
            raise ValueError("Thiếu %s." % what)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            t = datetime.fromisoformat(s)
        except ValueError as exc:
            raise ValueError("%s không phải ngày giờ ISO: %r." % (what, value)) from exc
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)
    return t.astimezone(timezone.utc)


def normalize_segments(raw: Any) -> list[dict[str, Any]]:
    """Kiểm tra và chuẩn hoá danh sách đoạn. Sai → ``ValueError`` (câu tiếng Việt)."""
    if raw is None:
        return []
    if not isinstance(raw, (list, tuple)):
        raise ValueError("segments phải là danh sách đoạn.")
    if len(raw) > MAX_SEGMENTS:
        raise ValueError("Tối đa %d đoạn." % MAX_SEGMENTS)
    out: list[dict[str, Any]] = []
    spans: list[tuple[datetime, datetime]] = []
    for i, seg in enumerate(raw):
        if not isinstance(seg, dict):
            raise ValueError("Đoạn %d phải là object {name, role, start, end}." % (i + 1))
        role = str(seg.get("role") or "").strip()
        if role not in ROLES:
            raise ValueError("Đoạn %d: vai %r không hỗ trợ (dev | test)." % (i + 1, role))
        start = _parse_time(seg.get("start"), "giờ bắt đầu của đoạn %d" % (i + 1))
        end = _parse_time(seg.get("end"), "giờ kết thúc của đoạn %d" % (i + 1))
        if not start < end:
            raise ValueError("Đoạn %d: giờ bắt đầu phải trước giờ kết thúc." % (i + 1))
        name = str(seg.get("name") or "").strip()[:MAX_NAME] or "Đoạn %d" % (i + 1)
        out.append({"name": name, "role": role, "start": start.isoformat(), "end": end.isoformat()})
        spans.append((start, end))
    for i in range(len(out)):
        for j in range(i + 1, len(out)):
            if spans[i][0] < spans[j][1] and spans[j][0] < spans[i][1]:
                raise ValueError(
                    "Đoạn «%s» và «%s» chồng nhau — các đoạn phải rời nhau." % (out[i]["name"], out[j]["name"])
                )
    dev_end = max((sp[1] for sp, seg in zip(spans, out) if seg["role"] == ROLE_DEV), default=None)
    for sp, seg in zip(spans, out):
        if seg["role"] == ROLE_TEST and dev_end is not None and sp[0] < dev_end:
            raise ValueError(
                "Đoạn kiểm tra «%s» phải nằm sau mọi đoạn phát triển (AGENTS.md §6.3)." % seg["name"]
            )
    return out


def _bar_time(bar: Any) -> datetime:
    t = bar.get("bar_time") if isinstance(bar, dict) else bar.bar_time
    return _parse_time(t, "bar_time")


def resolve_windows(
    segments: Sequence[dict[str, Any]],
    bars: Sequence[Any],
    offset: int,
    coverage: tuple[Optional[int], Optional[int]] = (None, None),
) -> list[dict[str, Any]]:
    """Đoạn (thời gian) → cửa sổ chỉ số nến **của dataset** ``[lo, hi]`` trên các nến của run.

    ``bars`` là nến của run theo thứ tự (chỉ số từ nến đầu run); ``offset`` = ``range_start_index``.
    Cửa sổ giao với khoảng chấm ``coverage`` (chỉ số dataset). Đoạn nằm ngoài khoảng run đã chạy
    hoặc ngoài khoảng chấm → ``lo``/``hi`` = None.
    """
    times = [_bar_time(b) for b in bars]
    cs, ce = coverage
    out = []
    for seg in segments:
        start = _parse_time(seg["start"], "start")
        end = _parse_time(seg["end"], "end")
        lo_rel = bisect.bisect_left(times, start)
        hi_rel = bisect.bisect_left(times, end) - 1
        lo, hi = lo_rel + offset, hi_rel + offset
        if cs is not None:
            lo = max(lo, cs)
        if ce is not None:
            hi = min(hi, ce)
        row = dict(seg)
        if lo_rel >= len(times) or hi_rel < 0 or lo > hi:
            row.update(lo=None, hi=None)
        else:
            row.update(lo=lo, hi=hi)
        out.append(row)
    return out
