"""In-memory audit log buffer used by the NSX/NX-API mocks."""
from __future__ import annotations

from threading import Lock
from typing import Any

_BUFFER: list[dict[str, Any]] = []
_LOCK = Lock()


def append(entry: dict[str, Any]) -> None:
    with _LOCK:
        _BUFFER.append(entry)


def recent(since_ts: float | None = None) -> list[dict[str, Any]]:
    with _LOCK:
        if since_ts is None:
            return list(_BUFFER)
        return [e for e in _BUFFER if e.get("ts", 0) >= since_ts]


def clear() -> None:
    with _LOCK:
        _BUFFER.clear()
