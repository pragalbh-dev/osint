"""The SPA static seam — the **only** connection to the excluded frontend track (API.md scope 9).

If a built SPA exists at ``frontend/dist/`` the app serves it same-origin (so CORS is a non-issue) with
client-side-route fallback to ``index.html``; otherwise it serves a minimal placeholder so the app is
still browsable. The API ships the mount; the real ``dist/`` lands via SHIP's Docker Node build stage.
Mounted **after** the JSON routers, so the API always wins over the SPA catch-all.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

from chanakya import settings

_PLACEHOLDER = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Chanakya OSINT</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{font-family:system-ui,sans-serif;max-width:44rem;margin:4rem auto;padding:0 1.5rem;
line-height:1.6;color:#1a1a1a}code{background:#f0f0f0;padding:.15rem .35rem;border-radius:.25rem}
a{color:#0b5cad}</style></head><body>
<h1>Chanakya OSINT</h1>
<p>The API is running. The single-page app has not been built into this image yet
(<code>frontend/dist/</code> is absent — SHIP's build stage adds it).</p>
<p>The JSON API is live: try <a href="/health">/health</a>, <a href="/view">/view</a>,
and the OpenAPI docs at <a href="/docs">/docs</a>.</p>
</body></html>"""


def _dist_dir() -> Path:
    return settings.repo_root() / "frontend" / "dist"


class _SPAStaticFiles(StaticFiles):
    """StaticFiles that falls back to ``index.html`` on 404 — SPA client-side routing over deep links."""

    async def get_response(self, path: str, scope: Any) -> Any:
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code == 404:
                return await super().get_response("index.html", scope)
            raise


def mount_spa(app: FastAPI) -> None:
    """Mount the built SPA at ``/`` if present, else a placeholder root. Call last in ``create_app``."""
    dist = _dist_dir()
    if dist.is_dir() and (dist / "index.html").is_file():
        app.mount("/", _SPAStaticFiles(directory=dist, html=True), name="spa")
        return

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    def _placeholder_root() -> str:
        return _PLACEHOLDER
