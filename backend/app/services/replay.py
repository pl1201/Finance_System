"""Replay từng nến: các phiên được giữ trong bộ nhớ tiến trình."""
from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from backend.app import config
from backend.app.errors import ServiceError
from backend.app.services.common import load_bars
from core.engine import ReplaySession
from core.registry import get_algorithm_class


class ReplayStore:
    """Giữ các phiên replay đang mở trong bộ nhớ tiến trình."""

    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def create(
        self,
        *,
        dataset_id: str,
        algorithm: str,
        params: dict[str, Any] | None,
        range_start: Optional[str],
        range_end: Optional[str],
    ) -> tuple[str, dict[str, Any]]:
        ds, bars, _ = load_bars(dataset_id, range_start, range_end)
        try:
            cls = get_algorithm_class(algorithm)
            norm = cls.validate_params(params)
            cls.check_dataset(ds["timeframe"], norm)
            algo = cls(**norm)
        except (KeyError, ValueError) as exc:
            raise ServiceError(str(exc)) from exc

        sid = "rp_" + uuid.uuid4().hex[:10]
        session = ReplaySession(bars, algo)
        with self._lock:
            if len(self._sessions) >= config.MAX_REPLAY_SESSIONS:
                oldest = min(self._sessions, key=lambda k: self._sessions[k]["created_at"])
                self._sessions.pop(oldest, None)
            self._sessions[sid] = {
                "session": session,
                "dataset": ds,
                "algorithm": algorithm,
                "algorithm_version": algo.version,
                "params": norm,
                "created_at": datetime.now(timezone.utc).timestamp(),
                "bars": bars,
            }
        return sid, self._meta(sid)

    def _entry(self, sid: str) -> dict[str, Any]:
        entry = self._sessions.get(sid)
        if not entry:
            raise ServiceError(
                "Phiên replay %r không còn tồn tại (có thể do khởi động lại "
                "backend). Hãy tạo phiên mới." % sid
            )
        return entry

    def _meta(self, sid: str, since: Optional[int] = None) -> dict[str, Any]:
        e = self._entry(sid)
        snap = e["session"].snapshot(since)
        snap["session_id"] = sid
        snap["dataset"] = e["dataset"]
        snap["algorithm"] = e["algorithm"]
        snap["algorithm_version"] = e["algorithm_version"]
        snap["params"] = e["params"]
        return snap

    def snapshot(self, sid: str) -> dict[str, Any]:
        return self._meta(sid)

    def step(self, sid: str, n: int = 1, since: Optional[int] = None) -> dict[str, Any]:
        try:
            self._entry(sid)["session"].step_forward(n)
        except ValueError as exc:
            raise ServiceError(str(exc)) from exc
        return self._meta(sid, since)

    def next_event(self, sid: str, since: Optional[int] = None) -> dict[str, Any]:
        try:
            self._entry(sid)["session"].step_until_event()
        except ValueError as exc:
            raise ServiceError(str(exc)) from exc
        return self._meta(sid, since)

    def back(self, sid: str, n: int = 1, since: Optional[int] = None) -> dict[str, Any]:
        try:
            self._entry(sid)["session"].step_back(n)
        except ValueError as exc:
            raise ServiceError(str(exc)) from exc
        return self._meta(sid, since)

    def seek(self, sid: str, index: int, since: Optional[int] = None) -> dict[str, Any]:
        try:
            self._entry(sid)["session"].seek(index)
        except ValueError as exc:
            raise ServiceError(str(exc)) from exc
        return self._meta(sid, since)

    def reset(self, sid: str) -> dict[str, Any]:
        self._entry(sid)["session"].reset()
        return self._meta(sid)

    def close(self, sid: str) -> None:
        with self._lock:
            self._sessions.pop(sid, None)

    def bars(self, sid: str) -> list[dict[str, Any]]:
        e = self._entry(sid)
        return [
            {
                "index": b.index,
                "bar_time": b.bar_time.isoformat(),
                "close_time": b.close_time.isoformat(),
                "time": int(b.bar_time.timestamp()),
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in e["bars"]
        ]


replay_store = ReplayStore()
