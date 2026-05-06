"""FastAPI app for the visual lab.

M1 surface: a single endpoint that serves the reference topology, plus a
static-files mount that serves the built frontend bundle. Later milestones
will add /api/stream (WebSocket), /api/inject, /api/reset, /api/concept/{id}.

The topology is built once at app startup and held in app.state. M1 doesn't
mutate it; later milestones will swap in a live simulator instance.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ..topology import Topology, build_reference_topology
from .serialize import serialize_topology

# frontend/dist is produced by `npm run build` in the frontend/ directory.
# We resolve it relative to the repo root, which is two levels up from this file.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_FRONTEND_DIST = _REPO_ROOT / "frontend" / "dist"


def create_app(topology: Topology | None = None) -> FastAPI:
    """Build the FastAPI app. `topology` is injectable for tests."""
    app = FastAPI(title="NetSimu Visual Lab", version="0.1.0")
    app.state.topology = topology or build_reference_topology()

    @app.get("/api/topology")
    def get_topology() -> dict:
        return serialize_topology(app.state.topology)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "milestone": "M1"}

    if _FRONTEND_DIST.is_dir():
        # html=True makes the mount serve index.html for "/" — single-page app.
        app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="ui")

    return app


# Module-level app for `uvicorn netops_sim.web.server:app`.
app = create_app()
