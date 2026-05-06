"""In-memory pub/sub event bus.

Behaviors and emitters publish events; collectors and archive sinks subscribe.
Subscribers can filter by `kind` or take everything (None).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

EventT = dict[str, Any]
HandlerT = Callable[[EventT], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[HandlerT]] = defaultdict(list)
        self._all: list[HandlerT] = []
        self._published_count = 0

    def subscribe(self, kind: str | None, cb: HandlerT) -> None:
        if kind is None:
            self._all.append(cb)
        else:
            self._subs[kind].append(cb)

    def publish(self, event: EventT) -> None:
        self._published_count += 1
        kind = event.get("kind", "")
        for cb in self._subs.get(kind, ()):
            try:
                cb(event)
            except Exception as exc:  # noqa: BLE001
                # Don't let a buggy subscriber kill the simulator.
                print(f"[bus] subscriber error on kind={kind}: {exc!r}")
        for cb in self._all:
            try:
                cb(event)
            except Exception as exc:  # noqa: BLE001
                print(f"[bus] catchall subscriber error: {exc!r}")

    @property
    def published_count(self) -> int:
        return self._published_count
