"""Persistence for user-edited node positions on the visual lab canvas.

The user can drag nodes around the topology canvas and click "Save layout"
to persist those positions across sessions. We write a flat JSON file —
the lab is single-user / local, so atomic-write semantics aren't needed.

Default location: ~/.netsimu/web_layout.json
Override via NETSIMU_LAYOUT_PATH env var (used by tests, and by users
who want a project-scoped layout instead of a per-user one).

CLAUDE.md hard rule #7: state lives in Python, never in browser storage.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

DEFAULT_PATH = Path.home() / ".netsimu" / "web_layout.json"


def get_layout_path() -> Path:
    override = os.environ.get("NETSIMU_LAYOUT_PATH")
    return Path(override) if override else DEFAULT_PATH


def read_layout() -> dict[str, Any]:
    """Return the saved payload, or {} if no file / unreadable."""
    path = get_layout_path()
    if not path.is_file():
        return {}
    try:
        with path.open() as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def write_layout(payload: dict[str, Any]) -> None:
    path = get_layout_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(payload, f, indent=2)


def clear_layout() -> bool:
    """Delete the saved layout file. Returns True if a file was removed."""
    path = get_layout_path()
    if path.is_file():
        path.unlink()
        return True
    return False
