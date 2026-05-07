"""FastAPI app for the visual lab.

M1 surface: a single endpoint that serves the reference topology, plus a
static-files mount that serves the built frontend bundle. Later milestones
will add /api/stream (WebSocket), /api/inject, /api/reset, /api/concept/{id}.

The topology is built once at app startup and held in app.state. M1 doesn't
mutate it; later milestones will swap in a live simulator instance.
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ..topology import Topology, build_reference_topology
from .content_loader import list_concept_ids, load_concept
from .layout_store import clear_layout, read_layout, write_layout
from .serialize import serialize_topology


class _Position(BaseModel):
    x: float
    y: float


class _LayoutPayload(BaseModel):
    positions: dict[str, _Position] = Field(default_factory=dict)

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

    if _FRONTEND_DIST.is_dir():
        # html=True makes the mount serve index.html for "/" — single-page app.
        app.mount("/", StaticFiles(directory=_FRONTEND_DIST, html=True), name="ui")

    return app


# Module-level app for `uvicorn netops_sim.web.server:app`.
app = create_app()
