# Resolution redesign — implementation plan (foundation-first, dependency-ordered)

**Status:** plan, not built. Companion to `10-resolution-real-world-redesign.md` (the *why* — north star + decision
ledger D1–D12). This doc is the *how*: the buildable sequence, with a concrete decision made at each step
rather than options left open. **Every seam below is grounded in verified current code** (read this session,
not from stale MDs); load-bearing claims were spot-checked against source. Lives on branch
`design/resolution-redesign` (worktree `wt-RESOLUTION-REDESIGN`).

**Governing principle (from the user):** prefer *extendable, decision-framework-true* changes over
shortcuts. The recurring shape of that here: the primitives we need mostly **already exist** in the code but
are inert, edge-only, or dropped at the derived layer — so we **add thin declarative layers that compile
DOWN onto the existing detectors/machinery**, rather than bolting on parallel mechanisms. We never hardcode
identity behaviour; it lives in config and in the evidence/decision logs.

---

## What already exists to build on (verified) — so the plan isn't hand-wavy

| Capability we need | What's already there | What's genuinely new |
|---|---|---|
| **Time axes** | A claim carries `event_time` (valid), `report_time`, `ingest_time`, each a `DateValue` that includes an interval type (`Period` range). Freshness decay + clock-free "now" work. | Carrying the interval onto *derived* node attrs/edges (today the date is **dropped** at assembly); "report ≥ validity" coupling; surfaced per-value history. |
| **Value-over-time reasoning** | The relocation trick: functional-edge `instance_key:[from]` + `supersede` ordering (ordered / contradiction / unorderable, newer nominates older, credibility-gated). A clean, config-gated, reusable prototype. | It's **edge-only** — entity attributes have no instance/succession analog. |
| **Attribute-conflict detection** | `has_hard_conflict` + `attribute_rules{identity,conflict,numeric_conflict}` + `attribute_scoring` readers, all wired and tested. | They're **unconfigured** (inert), mostly **soft** (score penalty), and `has_hard_conflict` is wired into **one** caller (coref→HITL), never the veto set. The `conflict` list is **overloaded** (feeds both soft penalty and the detector). No per-attribute role, no perishability, no neutral-retention. |
| **Hard walls (cannot-link)** | `vetoed()` runs before scoring at every stage; transitive; beats any score. Sources: curated/registry/gazetteer/claim distinct_from, learned barred, name-pattern id, geo. | A *declarative attribute-incompatibility* wall (critical-attr disagreement) computed from data; credibility floor on the vetoing claim. |
| **Status → outcome** | `_band`: `auto` (deterministic subtotal ≥ per-type floor → **collapse**), `hitl` (total ≥ `hitl_low` **or** raise-only → **candidate same-as edge**), `separate` (dropped). Candidate edge carries confidence + breakdown + band label. Confirmed merge → collapse + `resolved_from` provenance. | A retained **`possible`** tier (today `separate` pairs are discarded); confirmed represented as a retained same-as edge (audit) not only a collapse; a merge's own **corroboration ledger**. |
| **HITL replay** | Append-only decision log; `rebuild()` replays it; accept→alias link, reject/split→barred. **The pattern is right.** | **BUG (verified):** the live `build_record` writes `decision={chosen,rationale}` with the pair in `subject_ref`/`effects`, but replay reads `decision[pair/verdict]` → `_pair` returns None → the record is skipped. The learning loop is inert on the live path (works only in tests that pre-shape records). |
| **Relational (collective) signal** | `relational_score` reads the **live, growing** partition via `uf.find` (resolved neighbours collapse correctly); monotone fixpoint terminates. | **No per-link weighting** — every resolved neighbour counts equally regardless of merge confidence. Status-weighting is new. |

Two invariants hold throughout and constrain every stage: **rebuild purity** (no clock/network/parse in
replay or validators — so new claim fields must be declared, pure, optional) and **append-only / pure
recompute** (no in-place mutation; reversal is a new appended record + rebuild).

---

## Dependency graph (why this order)

```
Stage 0  HITL replay contract fix ──────────────┐  (unblocks every graded transition & earned-merge)
                                                 ▼
Stage 1  FOUNDATION (two parked load-bearing decisions, buildable in parallel)
         1A attribute_roles block (compile-down)      1B temporal validity on derived values
                    │                                        │
                    └───────────────┬────────────────────────┘
                                    ▼
Stage 2  Identity-as-hypothesis spine (possible/probable/confirmed + merge-corroboration ledger)
                                    │
                                    ▼
Stage 3  MECHANISMS on the foundation
         3A declarative cannot-links (+ D9 bridge alarm)   3B update/stale framework   3C staged resolution + status-weighted relational
                                    │
                                    ▼
Stage 4  Operator policy dials + coverage-gap output
—————————————————————————————————————————————————————————————
Roadmap (deferred, per D12): incremental/scale recompute · source-latency priors · richer trajectory intelligence
```

Rule of thumb the order encodes: **fix the loop, lay the foundation, erect the spine, then build the
mechanisms on it, then expose the policy.** Nothing graded is built before Stage 0; no mechanism (Stage 3)
is built before the roles + time it stands on (Stage 1) and the status model it reports into (Stage 2).

---

## Stage 0 — Fix the HITL → resolution replay contract *(prerequisite, small, high-leverage)*

**Decision.** Make the replay understand the *live* record shape rather than only the test-shaped one — do
**not** change the writeback (it is the append-only, deterministic, effects-preview-honest path we want).

**Build.** In the merge-adjudication replay: read the verdict from `decision["chosen"]` (with the existing
`verdict`/`action`/`accept` keys kept as accepted aliases), and recover the pair from `subject_ref`
(`"merge:a:b"`) and/or the structured `effects` (`grow_alias.same_as` / `record_distinct.pair`) rather than
from `decision`. Add a regression test that drives a real `build_record` output through replay end-to-end
(the missing coverage that hid this).

**Why / backbone.** The redesign's confirm/reject/earned-merge transitions are all "append a decision →
next rebuild reflects it." If replay can't read live decisions, the graded model is decorative. This is the
one place where the *pattern* is correct but the *contract* drifted between producer and consumer.

**Take care.** Also confirm whether `apply_decision_effects` should consume `grow_alias`/`record_distinct`
(today it reads only `set_status`/`add_integrity_flag`) — decide one owner for the effect, don't apply it
twice. Keep replay pure and deterministic (byte-identical on re-run).

---

## Stage 1 — Foundation (the two parked load-bearing decisions)

### 1A — A declarative `attribute_roles` block that compiles down onto existing detectors

**Decision.** Introduce a fresh per-type config block — each attribute declared explicitly with a **role**
(`critical` | `supporting` | `neutral`) and a **perishability** (durable vs a half-life/rate) — and write a
small **compiler** that lowers it onto the machinery that already exists. Do **not** stretch the existing
`attribute_rules` (its single `conflict` list is overloaded to feed both the soft penalty and the
`has_hard_conflict` detector, so it *cannot* separate critical from supporting).

**Compiles down as:**
- `supporting` agreement → the existing `identity`-list path (raises the attribute sub-score).
- `supporting` disagreement → the existing `conflict` + `conflict_penalty` soft path.
- `critical` disagreement → **new veto-wired set**: reuse `has_hard_conflict`'s detection, but route the
  resulting pairs into the `veto` set (beside the name-pattern id veto) so they become true cannot-links,
  before scoring, transitive.
- `neutral` conflict → **retain both values with provenance** (see below), never touch identity.

**Neutral retention.** Today attribute values fold in first-claim-wins (`setdefault`), silently dropping
conflicts. Add a per-attribute provenance sidecar (mirroring the existing node-level `resolved_from`
list pattern) — e.g. a `contested_attrs` map of `attr → [{value, claim_id, when}]` — populated at the
assembly fold. The node keeps one "current" value but no longer hides that others were asserted.

**Also folds in.** The parked *"rigorous per-type taxonomy"* is done here, as **config** (which attributes
of variant/unit/site/manufacturer/… are critical vs supporting vs neutral, and which are perishable) — a
decision surface, not code.

**Take care.** Keep the compiler the single source of truth so old `attribute_rules` config (if any) still
loads; `hard_id_fields` (attribute-value agreement → merge trigger) stays a separate, positive mechanism —
don't conflate it with critical-disagreement. Credibility floor on the critical veto is added in 3A.

### 1B — Temporal validity on derived values (the enabling primitive)

**Decision.** Stop dropping the claim's date at assembly. Carry a validity view onto **derived** node
attributes and edges, and surface retained per-value history — reusing the interval type and the
succession machinery that already exist, not inventing them.

**Build.**
- Attach `event_time` (and `report_time` as an upper bound) to each materialized attribute value and edge —
  mirror `EventView.time_interval`, which already carries an interval end-to-end.
- Enforce **report-date as an upper bound on validity** where an explicit validity interval isn't stated.
- Surface a **time-ordered series of values per attribute** (retained history) instead of collapsing to
  first-claim-wins — the raw history already lives in the append-only claim log; this exposes it in the view.
- Share the **succession *logic*, not the data shape.** Extract the supersede decision core — order
  time-stamped values of one single-valued-over-time slot, classify ordered/contradiction/unorderable,
  newer-supersedes-older gated by credibility — into a **slot-agnostic** function, and feed it from *both*
  edge-instances and attribute-series via thin adapters. Do **not** coerce attributes into edges just to
  reuse the engine: that couples the *representation* and is hard to unwind. Sharing the logic keeps the
  two easily separable — if attribute-succession ever needs to diverge, it's a branch inside the core (or a
  second consumer), a function boundary, not a data migration. The points where they *could* diverge (what
  to do with a contradiction; expected-change-rate/trajectory reasoning) already live in orthogonal axes
  (attribute *role* from 1A; per-slot config) **downstream** of the core, so the core itself stays shared.

**Why / backbone.** D8 (update vs stale) is undecidable without "when was this true," and reporting≠validity
is exactly what lets a disagreement read as *possible staleness* rather than contradiction. The relocation
trick proves the concepts (interval, order-by-event_time, newer-nominates-older, credibility-gated) — we
generalize its seam.

**Take care.** New claim fields must be declared on the model (records are `extra="forbid"`), optional
(old records load), and validated purely (no clock/parse — rebuild G1). Don't over-reach into a full
bitemporal store; carry the two axes we already have.

---

## Stage 2 — Identity as an evidence-backed hypothesis (the spine)

**Decision.** Make a merge a hypothesis with three statuses and its own corroboration ledger.

**Build.**
- **Three statuses:** `possible` (scored, retained, off the analyst's desk), `probable` (candidate same-as
  edge → HITL), `confirmed` (independently corroborated → collapse in the default view **and** a retained
  same-as identity edge in the evidence/audit layer — the natural home of the merge-corroboration ledger,
  rendered on demand in an expand/audit view, not as a second edge cluttering the merged graph). Map onto
  `_band`, but **retain the `possible` tier** — today `separate` pairs are dropped;
  keep the scored latent link (this is the watch-list, and the antidote to fragmentation).
- **Name alone reaches only `possible`, never `probable`** (banked correction) — so a bare name match never
  spends analyst attention.
- **Merge-corroboration ledger:** record *why* a merge holds — the independent identity-evidence items
  (unique-id, relational overlap, source-asserted same-as, transition bridge) — as the merge's own
  accounting, distinct from any fact's corroboration. The existing `resolved_from` breakdown is the seam to
  grow into this.

**Why / backbone.** Reuses the system's own confirmed/probable discipline for identity ("merge
corroboration, not assertion corroboration"). Depends on Stage 0 so the confirm/reject transitions actually
persist.

**Take care.** Confirmed-as-retained-edge is a view/schema change (today confirmed = collapse, no edge);
the collapse for display stays, the edge underneath is what makes identity auditable and reversible.

---

## Stage 3 — Mechanisms on the foundation

### 3A — Declarative cannot-links, credibility-gated, + the bridge-across-a-wall alarm (D5, D9)

Largely delivered by 1A's critical→veto wiring. This stage adds: (i) a **credibility floor** on the claim
that triggers a critical-attribute veto (below the floor → raise to HITL, don't wall) so one flaky source
can't shatter a good merge; (ii) the **absence≠conflict** discipline made explicit for all critical attrs
(as geo already does); (iii) **D9** — when a mention bridges two walled clusters, surface it as a
high-priority adjudication item rather than a silent non-merge.

### 3B — The update / stale decision framework (D8)

Depends on 1A (roles + perishability) and 1B (time). Build: the **overlap window as a signal, not a gate**
(agreement = corroboration; non-critical disagreement = soft negative weighed against commonality; critical
disagreement = the 3A wall); the **bridge-node cases** (per-attribute temporal alignment → toward confirmed,
credibility-gated; single current dateline with mixed values → probable/HITL); **explicit-transition claims**
as strong bridges (reusing the supersede ordering); and the rule that **perishable-only** evidence can reach
at most `probable`, never auto-`confirmed`.

### 3C — Staged, confidence-ordered resolution + status-weighted relational signal (D10)

**Decision.** Reorder the resolver into explicit evidence-strength stages — walls → unique-id merges →
strong anchors (location) → collective/relational over the trusted core → residual as `possible` — wrapped
in the existing monotone fixpoint (**monotone within a rebuild**, per the Support-5 decision: revealed
contradictions become flags for the next rebuild, never mid-loop backtracks). Add **per-link weighting** to
`relational_score`: a resolved neighbour reached through a `confirmed` link counts full, `probable` less,
`possible` least — so a weak over-merge can't lend certainty it didn't earn (the real cascade guard).

**Take care.** Location is a strong *separator* (geo veto) but a weak *unifier* (a base hosts many units) —
use it to anchor/partition, not to merge alone. Preserve termination: clusters only grow, statuses only
strengthen, within a rebuild.

---

## Stage 4 — Operator policy dials + coverage-gap output (D11)

**Decision.** Expose the possible/probable/confirmed thresholds and merge-aggressiveness as **policy dials**
(they already live in `resolution.yaml` as floors/bands — extend, keep in config), and emit **unresolved
identity as a coverage/collection gap** ("need more data on these entity types") rather than as silent
fragmentation, with each setting's cost made visible (how many links left at `possible`, how many
`confirmed` a stricter operator would have questioned). Ties into the existing freshness/coverage adaptation
surface.

**Take care.** Enumerate the full analyst-knob set here with a decision behind each; don't invent dials.

---

## Roadmap (deferred by decision, not omission)

- **Incremental / scale recompute (D12):** keep pure-recompute *semantics*; when near the scale problem,
  make the *implementation* incremental (bounded re-resolution blast radius, bit-identical results, never
  in-place mutable state). Deferred safely *because* Stages 0–4 preserve pure-function semantics.
- **Source latency / freshness priors:** discount overlap disagreement by how stale a "slow" source's
  current data tends to be (the update-lag scenario).
- **Richer trajectory intelligence:** beyond "stitch into one consistent trajectory," use an entity's own
  history and typical change rates.
- Also transitivity enforcement is currently an O(|veto|·N) rescan per candidate — fold its incremental
  form into the scale work, not before.

---

## Open decisions to confirm before/at build time

1. **Confirmed representation — DECIDED: keep the same-as edge.** Confirmed = collapse in the default view
   + a retained same-as identity edge in the evidence/audit layer. Buys: one uniform representation across
   possible/probable/confirmed (the status machine and UI treat identity as one graded thing, no
   discontinuity at the top), the natural home for the merge-corroboration ledger, and first-class
   one-click traceability + symmetric reversibility of the merge. Side effect to manage: don't let it
   become a dangling/duplicate edge — it lives in the provenance/audit layer (grown from `resolved_from`)
   and renders as an edge only in the expand/audit view; every domain-edge traversal/count must keep
   excluding same-as (as it already does for candidates).
2. **Functional-edge vs attribute-succession — DECIDED: shared logic core, not data coercion.** Extract the
   supersede decision core as a slot-agnostic function fed by both edge-instances and attribute-series;
   don't force attributes into the edge shape. Easily separable later (function boundary).
3. **Effect ownership** (Stage 0) — whether resolution reads `grow_alias`/`record_distinct` from `effects`
   or continues to reconstruct from the record; pick one to avoid double-application.
