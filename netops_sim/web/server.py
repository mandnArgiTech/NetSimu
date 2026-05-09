"""FastAPI app for the visual lab.

Surface so far:
  GET  /api/topology         — initial graph (M1)
  GET  /api/layout, POST, DELETE — persisted node positions (M1)
  GET  /api/concept/{id}     — markdown explainer (M2)
  WS   /api/stream           — live counters + heartbeats (M3)

The topology is built once at app startup. M3 introduces a long-running
SimRuntime that owns synthetic counter state and broadcasts events to
WebSocket subscribers. M4 will plug fault scenarios into the same
runtime; the WS layer should not need to change.
"""
from __future__ import annotations

import asyncio
import contextlib
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..topology import Topology, build_reference_topology
from .content_loader import list_concept_ids, load_concept
from .layout_store import clear_layout, read_layout, write_layout
from .serialize import serialize_topology
from .sim_runtime import SimRuntime


class _Position(BaseModel):
    x: float
    y: float


class _LayoutPayload(BaseModel):
    positions: dict[str, _Position] = Field(default_factory=dict)

# frontend/dist is produced by `npm run build` in the frontend/ directory.
# We resolve it relative to the repo root, which is two levels up from this file.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_FRONTEND_DIST = _REPO_ROOT / "frontend" / "dist"


def create_app(
    topology: Topology | None = None,
    *,
    enable_runtime: bool = True,
) -> FastAPI:
    """Build the FastAPI app. `topology` is injectable for tests.

    `enable_runtime=False` skips SimRuntime startup — used by tests that
    only exercise REST endpoints and don't want a background ticker
    polluting their event loop.
    """
    resolved_topology = topology or build_reference_topology()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if enable_runtime:
            runtime = SimRuntime(resolved_topology)
            await runtime.start()
            app.state.runtime = runtime
        else:
            app.state.runtime = None
        try:
            yield
        finally:
            if app.state.runtime is not None:
                await app.state.runtime.stop()

    app = FastAPI(title="NetSimu Visual Lab", version="0.1.0", lifespan=lifespan)
    app.state.topology = resolved_topology

    @app.get("/api/topology")
    def get_topology() -> dict:
        return serialize_topology(app.state.topology)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "milestone": "M3"}

    @app.get("/api/layout")
    def get_layout() -> dict:
        """Return saved per-node positions. Empty dict if nothing saved."""
        return read_layout()

    @app.post("/api/layout")
    def save_layout(payload: _LayoutPayload) -> dict:
        """Persist per-node positions sent from the canvas."""
        write_layout(payload.model_dump())
        return {"saved": True, "count": len(payload.positions)}

    @app.delete("/api/layout")
    def reset_layout() -> dict:
        """Delete the saved layout so the canvas falls back to defaults."""
        removed = clear_layout()
        return {"reset": True, "removed": removed}

    @app.get("/api/concepts")
    def list_concepts() -> dict:
        """List every concept id available for /api/concept/{id}."""
        return {"ids": list_concept_ids()}

    @app.get("/api/concept/{concept_id}")
    def get_concept(concept_id: str) -> dict:
        """Return {id, title, body} for a concept, or 404."""
        concept = load_concept(concept_id)
        if concept is None:
            raise HTTPException(status_code=404, detail=f"unknown concept: {concept_id}")
        return {"id": concept.id, "title": concept.title, "body": concept.body}

    @app.websocket("/api/stream")
    async def stream(ws: WebSocket) -> None:
        """Live event stream.

        Protocol:
          server → client: first message is {"type":"snapshot","state":{id:event}}
                          then {"type":"event","event":{...}} for each tick.
          client → server: nothing in M3. M4 will add inject/reset commands.
        """
        runtime: SimRuntime | None = app.state.runtime
        if runtime is None:
            await ws.close(code=1011)  # internal error
            return
        await ws.accept()
        queue = runtime.subscribe()
        try:
            await ws.send_json({"type": "snapshot", "state": runtime.snapshot()})
            while True:
                event = await queue.get()
                if event.get("kind") == "_shutdown":
                    break
                await ws.send_json({"type": "event", "event": event})
        except WebSocketDisconnect:
            pass
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            # Don't let a single bad event drop the server.
            with contextlib.suppress(Exception):
                await ws.close(code=1011)
        finally:
            runtime.unsubscribe(queue)

    if _FRONTEND_DIST.is_dir():
        # html=True makes the mount serve index.html for "/" — single-page app.
        app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="ui")

    return app


# Module-level app for `uvicorn netops_sim.web.server:app`.
app = create_app()
