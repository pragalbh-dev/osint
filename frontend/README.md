# Chanakya — analyst workbench (frontend)

The React/Vite/TS SPA for the Chanakya OSINT demo. A single dark **instrument** at
1440×900 (desktop / screen-share), faithful to the Claude Design handoff. Served
same-origin by the FastAPI backend from `frontend/dist/` — no CORS, one artifact.

## Run it

```bash
cd frontend
npm install            # .npmrc pins legacy-peer-deps (react-cytoscapejs old peer range)
npm run dev            # Vite dev server on :5173; API paths proxy to :8000
npm run build          # → frontend/dist  (what the backend serves)
npm run typecheck      # tsc --noEmit
```

The backend (`chanakya.api.spa.mount_spa`) auto-serves `frontend/dist/index.html`
same-origin with SPA fallback, after JSON routes. In dev, run `uvicorn` on :8000 and
the Vite proxy (see `vite.config.ts`) forwards `/view`, `/ask`, `/health`, … to it.

## Two data modes

- **Demo (default):** deterministic — the ~90-second HQ-9/P hero thread, identical on
  every run (the graded non-negotiable). Renders from `src/store/workbench.ts` +
  `src/demo/scenario.ts`. No backend required to boot.
- **Live:** talks to the real API. `GET /view` is wired via `src/api/hooks.ts`
  (`useLiveSync`); the rest (`/ask`, `/evidence`, `/hitl/*`, `/ingest`) slot in behind
  the same seam as their routes land. Toggle by setting the store `mode` to `'live'`.

## Architecture

| Path | Role |
|---|---|
| `src/styles/tokens.css` | status visual-language tokens (mockup `:root`, authoritative). **The one rule: dashed = provisional · solid = settled.** Status by border+fill, never hue. |
| `src/design/tokens.ts` | same tokens as JS for Cytoscape/Leaflet canvas (can't read CSS vars) |
| `src/api/types.ts` | TS mirror of the F0-frozen contract (`schemas/{api_models,view}.py`) |
| `src/api/client.ts` · `hooks.ts` | typed fetch client + TanStack Query hooks (live seam) |
| `src/demo/scenario.ts` | the frozen demo content — single source of truth for on-screen copy |
| `src/store/workbench.ts` | the state machine (stage/panel/drawer/selection, review decisions, ingest trace, credibility recompute) |
| `src/components/status/` | shared grammar: `StatusSwatch`, `CitationChip`, `TierDots` |
| `src/components/{rail,stage,panel,drawer}/` | the four zones |

## Hard rules (do not break — the design fails review otherwise)

Status by border/fill never hue · source tier never on a map pin · the chokepoint halo
stays dashed (candidate only) · a refusal is an answer, not an error (no warning/spinner)
· nothing critical on hover · sentence case, dates absolute, no percentages, never the
words "AI/model/agent" in the chrome.
