"""Default keyless boot (the production path) + the frozen-contract OpenAPI surface (API.md acceptance).

Uses the *real* ``config/`` + ``corpus/`` via ``create_app()`` with no injected state — so this exercises
``build_default_state`` + the lifespan boot, not a fixture. With no committed claim bundles the graph boots
empty (the app stands up keyless and the analyst populates it via ``/ingest``); once DATA/SHIP commit the
extracted bundles, the same boot yields the seeded baseline with no code change.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from chanakya.api import create_app


def test_default_keyless_boot_stands_up() -> None:
    with TestClient(create_app()) as client:  # no state → build_default_state() + lifespan boot
        health = client.get("/health")
        assert health.status_code == 200
        body = health.json()
        assert body["rebuilt"] is True
        assert body["config_version"] >= 1  # the real config/*.yaml loaded into the live store
        # A valid (possibly empty) view is served without a key.
        assert client.get("/view").status_code == 200


def test_openapi_spec_exposes_the_frozen_contract() -> None:
    # FastAPI generates /openapi.json from the frozen response models — the frontend's codegen source.
    with TestClient(create_app()) as client:
        spec = client.get("/openapi.json").json()
        paths = spec["paths"]
        for endpoint in ("/health", "/view", "/node/{node_id}", "/evidence/{element_id}",
                         "/ask", "/ingest", "/hitl/status", "/config/{section}"):
            assert endpoint in paths, f"missing {endpoint} in OpenAPI"
