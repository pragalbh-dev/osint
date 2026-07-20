# SCORE → API / FRONTEND — the supersession beat changes `GET /view` (fold into `API-to-FRONTEND-contract-log.md`)

Branch `fix/phase4-derived-and-surfaces`. Three additive, non-breaking changes an analyst can now SEE.
No route, request or response *schema* changed — this is new data on existing shapes.

## 1. A new edge type appears: `supersedes` (node→node)

`view.edges` now contains at most one `supersedes` edge per promoted relocation, e.g.

    id     e:site_rahwali:supersedes:site_rawalpindi
    type   "supersedes"      source site_rahwali (newer)   target site_rawalpindi (older)

It carries the **union** of the two basing edges' `claim_ids` (so the provenance drawer works on it), and
`status: null` / `confidence: null` **by design** — it renders a version link between two edges that were
each already scored; scoring it again would be a second score of one fact (gate G5). It is a *timeline*
relationship, **not an alarm** — give it the "replaced by →" treatment, never the contradiction treatment
(product/02 §7). `attrs`: `derived_via: "supersede"`, `newer_edge`, `older_edge`, `subject`,
`source_edge_instance`.

**Frontend action:** any component that assumes every edge has a status badge (or that switches on edge
type) needs a case for this. The same applies to `same-as` / `distinct-from`, which have always been
status-less.

## 2. Edges can now carry `status: "stale"` on the corpus

`stale` was previously reachable only via the freshness half-life and fired on nothing real. The
relocation edge `e:unit_hq9b:based-at:site_rawalpindi` now reads **stale** (it used to read
`insufficient`, which was wrong — it implied missing coverage when the truth is that the unit left). Its
`confidence.integrity_flags` include `"superseded"`, and `attrs.supersede_gate == "promoted"`.

**Frontend action:** `stale` must be visually distinct from `insufficient` — history vs an evidence gap.

## 3. New `attrs` on `based-at` edges that are half of an unadjudicated supersession

- `candidate_supersede: true` — the pair is **not** retired; the analyst decides. This is the *default*
  outcome (D-P4.4), not an exception, so the review queue should surface it.
- `supersede_gate`: `"pending"` | `"promoted"` | `"held"`.
- `supersede_pending_newer` (on the older edge) / `supersede_pending_older` (on the newer edge) — the
  ordered pair.
- `supersede_hold_reason`: list of strings, e.g. `["newer-below-probable", "newer-deception-gate:decoy-risk"]`
  — human-readable enough to render verbatim as "why this wasn't auto-retired".

Nothing in the corpus is currently `held`, but the golden/unit fixtures cover it and the d20 spoof is the
intended trigger.

## Config surface (hot-config screen)

`config/credibility.yaml` gains a `supersede_floor` block (`min_band`, `min_independent_looks`,
`newer_status_allow`, `blocking_gate_flags`). It is analyst-editable like every other credibility knob and
takes effect on the next `rebuild()` — no restart. Deleting it fails **closed** (nothing is auto-retired),
which is worth saying in the UI if the config editor exposes it.
