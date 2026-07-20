# HANDOFF — d18 imagery claim orphans onto its own node; fuse it into the Rahwali site

**For:** the backend-fix agent (DATA-C / RESOLVE). **From:** live-QA (frontend session, 2026-07-20),
verified on the running keyed build with extraction on. **Supersedes** the display-only framing in
`QA-d18-imagery-claim-provenance.md` — the imagery claim IS in the graph; the problem is it does not
fuse with the real site, so the analyst never sees it.

**Working rule:** this touches the **frozen corpus** and lands on the **flagship Rahwali node**, so it
was not self-fixed in the QA session. Pick an approach, apply it, and re-verify the beat (below).

---

## Task, in one line

Make d18's imagery-derived basing claim resolve onto `site_rahwali` (instead of a placeholder orphan
node), so clicking **Rahwali airfield** shows the assessment made from the `.png`, not only the `.txt`
prose. Then (frontend follow-on) surface the imagery claim first in the drawer.

## Reproduce

1. Boot the app (keyless is fine — the frozen bundle already contains the imagery claim).
2. Ingest `d18_rahwali_pass1` (left-rail Awaiting-ingest, or POST /ingest with its bundle).
3. `GET /evidence/site_rahwali` → two claims, both **text**: `d18-rahwali-pass1-l16`,
   `d19-rahwali-confirm-l11`. The L16 quote is the "Site sits on the northern perimeter apron…" prose.
4. `GET /view` → a **separate** node `ent:basing_site:imagery-site:d18_rahwali_pass1` (status probable,
   1 claim) carries `d18-rahwali-pass1-full` — the VLM claim (`method: vlm`, `.png` region:full, with
   `image_fingerprint`). No `same-as` / `distinct-from` links either way.

## Root cause (verified)

d18 has two basing-site chains that cannot resolve together:

| Node | Claim | Location source | Name |
|---|---|---|---|
| `site_rahwali` (confirmed) | `…-l16` (text) | coords 32.2389, 74.1311 (pad) — parsed from the DMS in the **.txt** LOCATION section | "Rahwali airfield" |
| `…:imagery-site:d18_rahwali_pass1` (orphan) | `…-full` (VLM, from **.png**) | **no `coordinates` key at all** | "imagery-site:d18_rahwali_pass1" (placeholder) |

Neither a shared name nor a shared coordinate exists, so RESOLVE correctly leaves them apart. The
imagery claim's real content (`description`, `observed_features`, `occupancy_state`,
`resolution_sufficiency`, `site_signature_geometry`, `count`) is stranded on the orphan.

File: `corpus/scenarios/hq9p_primary/claims/d18_rahwali_pass1.json` (claim `d18-rahwali-pass1-full`).

## Approaches (cheapest first — pick one)

1. **RECOMMENDED — deterministic, additive (renormalize-style):** copy the site's DMS coordinates onto
   the `-full` imagery claim's `payload.attrs.coordinates` (same values the L16 text claim already
   carries: 32°14′20″N 074°07′52″E → 32.2389, 74.1311, precision `pad`, surface_format DMS). Geo-
   proximity then fuses the imagery node into `site_rahwali`. No LLM, no re-record; mirror the offline,
   dry-run-by-default, additive style of `backend/chanakya/ingest/renormalize.py`. Faithful because the
   coordinates genuinely describe the same pass over the same site.
2. **Alias / coref the placeholder name** `imagery-site:d18_rahwali_pass1` → "Rahwali airfield" so the
   two merge on the name channel instead of coordinates (`config/resolution.yaml` alias table or a coref
   binding). Same outcome, different signal.
3. **Re-record d18 through the VLM lane** so the imagery observation itself emits the site name +
   coordinates (fix the producer, not the artifact). Keyed re-record. d18 does NOT carry the d06 LR-SAM
   alias risk, but it DOES back the flagship relocation beat — diff the before/after basing edge.

## Acceptance criteria (any approach)

- `GET /evidence/site_rahwali` now includes `d18-rahwali-pass1-full` among its claims, and the orphan
  node `ent:basing_site:imagery-site:d18_rahwali_pass1` is gone (merged) — verify via `GET /view`.
- `site_rahwali` status is still **confirmed** after the extra claim (re-check confidence inputs; a new
  independent look must not accidentally *lower* it via the double-counted independence weight, and must
  not *fabricate* corroboration — it is the same document, so the imagery + text claims should group as
  ONE independent look, not two. Confirm the grouping.)
- **`make beat` still fires with the relocation alert** (before=Rawalpindi stale, after=Rahwali
  confirmed, unchanged claim-id count) — this is the non-negotiable check; the fix is void if the beat
  changes.
- `make check` green (ruff + mypy + pytest incl. gates).

## Frontend follow-on (separate, after the merge lands)

Once `site_rahwali` carries the imagery claim, the provenance drawer should **lead with the imagery-
derived claim** — observed-vs-inferred tag + source class "imagery" — and show the L16 text as the
corroborating locator, rather than opening on the text prose. Small adapter/ordering change in
`frontend/src/api/adapters.ts` + the drawer; not worth doing until there is an imagery claim on the node
to lead with. File a note to FRONTEND when the merge is in.

## Not a beat-breaker

The based-at edge `e:unit_hq9b:based-at:site_rahwali` is backed by the derived basing inference + d19
and still reads probable→confirmed. The orphan is a provenance-quality gap on the site node, not a break
in the flagship trace — important for the imagery story, not urgent for the demo path.
