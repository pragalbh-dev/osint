"""SPA static seam — placeholder when unbuilt, real mount + deep-link fallback when built, never shadows
the JSON API (API.md scope 9)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from chanakya.api import create_app
from chanakya.api import spa as spa_mod
from tests.api.conftest import build_golden_state


def test_placeholder_when_no_spa_build(monkeypatch, tmp_path: Path) -> None:
    # "No SPA build" has to be asserted HERMETICALLY rather than inferred from the developer's working
    # tree. Reading the real frontend/dist made this test's result depend on the environment: it passes
    # on a fresh clone and fails the moment anyone runs `npm run build` — and SHIP's image *always*
    # bakes a dist, so a tree-dependent assertion could never hold in the shipped artifact. Point the
    # seam at a missing dir instead (the same monkeypatch the built-SPA test uses, inverted). The
    # intent — unbuilt SPA ⇒ browsable placeholder, never a 404 — is unchanged and now always testable.
    monkeypatch.setattr(spa_mod, "_dist_dir", lambda: tmp_path / "no-such-dist")
    with TestClient(create_app(build_golden_state())) as client:
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        assert "Chanakya OSINT" in r.text  # the placeholder…
        assert "has not been built into this image yet" in r.text  # …and specifically the placeholder


def test_spa_does_not_shadow_the_json_api(golden_client) -> None:
    # The JSON API still answers even though "/" is served by the SPA seam.
    assert golden_client.get("/health").status_code == 200
    assert golden_client.get("/view").headers["content-type"].startswith("application/json")


def test_built_spa_is_served_with_deeplink_fallback(monkeypatch, tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>SPA ROOT</body></html>")
    (dist / "app.js").write_text("console.log('spa')")
    monkeypatch.setattr(spa_mod, "_dist_dir", lambda: dist)

    with TestClient(create_app(build_golden_state())) as client:
        assert client.get("/").text == "<html><body>SPA ROOT</body></html>"  # index at root
        assert "console.log" in client.get("/app.js").text  # a real asset by path
        # an unknown client-side route falls back to index.html (SPA routing), not a 404
        deep = client.get("/some/client/route")
        assert deep.status_code == 200 and "SPA ROOT" in deep.text
        # API routes still win over the SPA catch-all
        assert client.get("/health").status_code == 200
        assert client.get("/view").status_code == 200
