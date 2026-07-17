# backend/

All Python backend code, tests, and dependencies live here — the shared spine + the C layer's runtime + the
API. This directory is scaffolded by session **F0** (`artifacts/plan/sessions/F0.md`): `pyproject.toml`,
`chanakya/` (the package), `tests/`, `eval/`.

Repo-root siblings that stay outside `backend/`: `config/` (the 7 pipeline YAML), `corpus/` (frozen data),
`tools/` (the ontology-blind generator), `frontend/` (the SPA — out of scope for the backend plan), and the
deploy files (`Dockerfile`, `docker-compose.yml`, `Makefile`, `deploy/`). The app resolves `config/` +
`corpus/` via a settings path defaulting to the repo root; the Docker build COPYs them into the image.

**Read `../artifacts/plan/00-master-plan.md` before implementing any module here** — it carries the frozen
inter-module contracts (§4), the executable abstraction gates (§5), and the worktree/PR workflow (§8).
