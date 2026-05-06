"""Replay a recorded JSONL archive into an event bus, at chosen speed."""
from __future__ import annotations

import argparse
import asyncio
import json
import time
from pathlib import Path
from typing import Callable

from .bus import EventBus


async def replay(
    path: str,
    speed: float = 10.0,
    target: EventBus | None = None,
    on_event: Callable[[dict], None] | None = None,
) -> int:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)

    events: list[dict] = []
    with p.open() as f:
        for line in f:
            line = line.strip()
            if line:
                events.append(json.loads(line))

    if not events:
        return 0

    events.sort(key=lambda e: e.get("ts", 0))
    t0 = events[0]["ts"]
    wall0 = time.time()

    bus = target or EventBus()
    if on_event:
        bus.subscribe(None, on_event)

    for ev in events:
        target_dt = (ev["ts"] - t0) / speed
        wait = (wall0 + target_dt) - time.time()
        if wait > 0:
            await asyncio.sleep(wait)
        bus.publish(ev)

    return len(events)


def main() -> None:
    p = argparse.ArgumentParser(description="Replay a NetSimu JSONL archive.")
    p.add_argument("path", help="Path to .jsonl archive")
    p.add_argument("--speed", type=float, default=10.0,
                   help="Replay speed multiplier (default 10x)")
    p.add_argument("--quiet", action="store_true",
                   help="Don't print events to stdout")
    args = p.parse_args()

    def printer(ev: dict) -> None:
        if not args.quiet:
            kind = ev.get("kind", "?")
            ent = ev.get("entity", "?")
            print(f"[{ev.get('ts'):.1f}] {kind:20s} {ent}")

    n = asyncio.run(replay(args.path, args.speed, on_event=printer))
    print(f"\nReplayed {n} events.")


if __name__ == "__main__":
    main()
