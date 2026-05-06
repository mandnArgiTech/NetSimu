"""Run NSX, NX-API, and gNMI mocks concurrently on different ports.

Usage:  python -m netops_sim.emitters.serve_all
"""
from __future__ import annotations

import asyncio

import uvicorn


async def _run(app_path: str, port: int) -> None:
    config = uvicorn.Config(app_path, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main() -> None:
    print("Starting mock APIs:")
    print("  NSX Policy API   → http://localhost:8443  (try /healthz)")
    print("  Cisco NX-API     → http://localhost:8444/ins")
    print("  gNMI WebSocket   → ws://localhost:8445/gnmi/subscribe")
    await asyncio.gather(
        _run("netops_sim.emitters.nsx_api:app", 8443),
        _run("netops_sim.emitters.nxapi:app", 8444),
        _run("netops_sim.emitters.gnmi_ws:app", 8445),
    )


if __name__ == "__main__":
    asyncio.run(main())
