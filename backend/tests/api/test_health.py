"""``GET /health`` readiness gate — 503 before the boot rebuild, 200 after (API.md acceptance)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from chanakya.api import create_app
from tests.api.conftest import build_golden_state


def test_health_503_before_boot_then_200_after() -> None:
    state = build_golden_state(boot=False)  # un-booted
    app = create_app(state)
    client = TestClient(app)  # NOT a context manager → lifespan/boot does not run

    before = client.get("/health")
    assert before.status_code == 503
    assert before.json() == {"status": "starting", "rebuilt": False, "node_count": 0,
                             "edge_count": 0, "config_version": 0}

    state.boot()  # the first rebuild() lands

    after = client.get("/health")
    assert after.status_code == 200
    body = after.json()
    assert body["status"] == "ok" and body["rebuilt"] is True
    assert body["node_count"] == len(state.view().nodes)
    assert body["config_version"] == state.config.version
