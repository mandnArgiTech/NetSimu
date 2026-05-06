"""gNMI-shaped streaming mock over WebSocket.

Faithful gRPC gNMI server is overkill for PoC. We expose a WebSocket that
streams JSON updates with the same logical schema as gNMI Subscribe.
The collector has a switch (gnmi_grpc | gnmi_ws) — pick ws against this mock.
"""
from __future__ import annotations

import asyncio
import json
from collections import deque
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI(title="gNMI WS mock", version="0.1.0")

# In-process queue. The runner can push into this; subscribers fan out.
_QUEUE: deque[dict[str, Any]] = deque(maxlen=10_000)
_LISTENERS: list[asyncio.Queue] = []


def push(event: dict[str, Any]) -> None:
    """External entrypoint for the simulator to feed gNMI-shaped events in."""
    _QUEUE.append(event)
    for q in list(_LISTENERS):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass


@app.websocket("/gnmi/subscribe")
async def subscribe(ws: WebSocket) -> None:
    await ws.accept()
    q: asyncio.Queue = asyncio.Queue(maxsize=2048)
    _LISTENERS.append(q)
    try:
        while True:
            ev = await q.get()
            translated = _translate(ev)
            if translated:
                await ws.send_json(translated)
    except WebSocketDisconnect:
        pass
    finally:
        if q in _LISTENERS:
            _LISTENERS.remove(q)


def _translate(ev: dict[str, Any]) -> dict[str, Any] | None:
    """Convert a NetSimu interface_counters event to gNMI-shaped JSON."""
    if ev.get("kind") != "interface_counters":
        return None
    return {
        "update": {
            "timestamp": int(ev.get("ts", 0) * 1e9),
            "path": f"/interfaces/interface[name={ev['entity']}]/state/counters",
            "values": {
                "in-octets": ev.get("in_octets"),
                "out-octets": ev.get("out_octets"),
                "in-errors": ev.get("in_errors"),
                "in-discards": ev.get("in_discards"),
                "in-pkts": ev.get("in_pkts"),
                "out-pkts": ev.get("out_pkts"),
                "crc-errors": ev.get("crc_errors"),
                "oper-status": ev.get("oper_status"),
                "mtu": ev.get("mtu"),
            },
        }
    }


@app.get("/healthz")
def health():
    return {"ok": True, "buffered": len(_QUEUE), "listeners": len(_LISTENERS)}
