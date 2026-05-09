"""Tests for /api/layout (save / load / reset of canvas node positions)."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from netops_sim.topology import build_reference_topology
from netops_sim.web.server import create_app


@pytest.fixture
def layout_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the layout store to a tmp file for the duration of the test."""
    path = tmp_path / "web_layout.json"
    monkeypatch.setenv("NETSIMU_LAYOUT_PATH", str(path))
    return path


def _client() -> TestClient:
    return TestClient(create_app(topology=build_reference_topology()))


def test_get_layout_returns_empty_when_no_file(layout_file: Path) -> None:
    assert not layout_file.exists()
    res = _client().get("/api/layout")
    assert res.status_code == 200
    assert res.json() == {}


def test_post_layout_writes_file_and_get_returns_it(layout_file: Path) -> None:
    payload = {
        "positions": {
            "spine-01": {"x": 700.0, "y": 100.0},
            "host-01": {"x": 240.5, "y": 580.5},
        }
    }
    res = _client().post("/api/layout", json=payload)
    assert res.status_code == 200
    body = res.json()
    assert body["saved"] is True
    assert body["count"] == 2

    # File written
    assert layout_file.is_file()
    on_disk = json.loads(layout_file.read_text())
    assert on_disk["positions"]["spine-01"] == {"x": 700.0, "y": 100.0}

    # Round-trip via GET
    res2 = _client().get("/api/layout")
    assert res2.status_code == 200
    assert res2.json() == on_disk


def test_delete_layout_removes_file(layout_file: Path) -> None:
    _client().post(
        "/api/layout",
        json={"positions": {"spine-01": {"x": 1.0, "y": 2.0}}},
    )
    assert layout_file.is_file()

    res = _client().delete("/api/layout")
    assert res.status_code == 200
    body = res.json()
    assert body["reset"] is True
    assert body["removed"] is True
    assert not layout_file.exists()

    # Subsequent GET is empty again.
    assert _client().get("/api/layout").json() == {}


def test_delete_when_nothing_saved_is_idempotent(layout_file: Path) -> None:
    res = _client().delete("/api/layout")
    assert res.status_code == 200
    assert res.json()["removed"] is False


def test_post_validates_position_shape(layout_file: Path) -> None:
    res = _client().post(
        "/api/layout",
        json={"positions": {"x": "not-a-position"}},
    )
    assert res.status_code == 422


def test_default_path_is_user_home(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NETSIMU_LAYOUT_PATH", raising=False)
    from netops_sim.web.layout_store import get_layout_path

    p = get_layout_path()
    # Don't write here — just check the default resolves under $HOME.
    assert str(p).endswith(os.path.join(".netsimu", "web_layout.json"))
