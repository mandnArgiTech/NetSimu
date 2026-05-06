import asyncio
from datetime import datetime, timezone

import pytest

from netops_sim.clock import VirtualClock


def test_now_returns_start():
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    c = VirtualClock(start=start)
    assert c.now() == start


@pytest.mark.asyncio
async def test_schedule_fires_in_order():
    c = VirtualClock()
    fired: list[int] = []

    def make_cb(i: int):
        def cb():
            fired.append(i)
        return cb

    c.schedule(5.0, make_cb(2))
    c.schedule(1.0, make_cb(1))
    c.schedule(10.0, make_cb(3))

    await c.run_until(c.now_ts() + 100)
    assert fired == [1, 2, 3]


@pytest.mark.asyncio
async def test_run_until_advances_time_to_end():
    c = VirtualClock()
    start = c.now_ts()
    await c.run_until(start + 50)
    assert c.now_ts() == start + 50


@pytest.mark.asyncio
async def test_async_callbacks_supported():
    c = VirtualClock()
    fired = []

    async def cb():
        fired.append(c.now_ts())

    c.schedule(2.0, cb)
    c.schedule(4.0, cb)
    await c.run_until(c.now_ts() + 10)
    assert len(fired) == 2
