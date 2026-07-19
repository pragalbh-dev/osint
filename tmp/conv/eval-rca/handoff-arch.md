# EVAL RCA handoff — ARCH / F0 / lens (cross-cutting id + lens design)

## Context

The pipeline was run end-to-end for the first time over real extracted bundles (generated from
`corpus/scenarios/hq9p_primary/claims/`), and the resulting graph diverges sharply from the
oracle (`answer_key.json`). This handoff is your service's (ARCH / F0 cross-cutting design) share
of the root-cause fix — the F0-level id/lens contract decisions plus the lens implementation bugs
that fall directly under ARCH. See the evidence bundle at
`tmp/conv/eval-rca/00-evidence-summary.md` and `tmp/conv/eval-rca/view_full.json` for full detail.

## TL;DR

1. **No canonical semantic-id mechanism exists anywhere in the architecture.** Entity node ids are
   name-derived (`ent:<type>:<name>`), never the oracle/config ids (`unit_paad`, `mfr_casic`,
   `site_rawalpindi`...). This is an F0 contract gap — ARCH must ratify introducing an entity
   gazetteer/registry (mirroring `config/places.yaml`'s `place_id` pattern) that DATA-C builds and
   RESOLVE consumes to assign canonical node ids.
2. **The lens (`apply_lens`) seeds traversal by literal string membership of the anchor id in the
   graph**, so it silently returns empty (0 nodes/0 edges) the moment the id space doesn't match —
   which it currently never does. This is a real code defect independent of the id-registry
   decision, and the same anti-pattern exists in ASK (`tools.py:397`).
3. **The lens's declared materiality-filter schema is dead code.** `subjects.yaml` declares
   `node_types_allow`, `exclude_off_subject`, `materiality_attrs`, `never_drop_indeterminate`, but
   the implementation only understands two chokepoint-related keys — no chaff protection is
   actually happening once anchors resolve.

## Findings

### AR-1 — No canonical semantic-id mechanism (F0 contract gap)

- **Symptom:** Node ids are name-derived (`ent:<type>:<name>`), never the oracle/config canonical
  ids (`unit_paad`, `mfr_casic`, `site_rawalpindi`, `unit_hq9b`). Subject-lens anchors,
  observables, and the oracle all reference an id space that no runtime node ever occupies.
- **Evidence:**
  - `answer_key.json` ground-truth ids (`mfr_casic`, `comp_ht233`, `mfr_23rd_ri` — hand-assigned)
  - `config/subjects.yaml:8-9` (`unit_paad`, `site_karachi`); `config/observables.yaml:16-18`
    (`unit_hq9b`, `site_rawalpindi`, `site_rahwali`)
  - `backend/chanakya/resolve/entities.py:41-43` (`base_ref` = `ent:{type}:{name}`);
    `backend/chanakya/resolve/cluster.py:310-320` (`_preferred` picks a surviving surface-form id,
    never a semantic id like `var_hq9p`)
  - `config/resolution.yaml` `alias_table` (name -> name, no id column) vs.
    `config/places.yaml` (`place_id: pl_nurkhan` + aliases — the intended pattern, already
    working for places)
  - `tmp/conv/eval-rca/00-evidence-summary.md` lines 70-152 (every oracle canonical id maps to
    1..9 name-derived view nodes instead of one canonical node)
- **Root cause:** The architecture has two incompatible id spaces: entities are identified purely
  by extracted surface form at every stage, and even after merge the "canonical" id is just the
  winning surface form (`cluster._preferred`), never a stable semantic id. Places already solve
  this with a `place_id` gazetteer; entities have no analogous registry. Nothing in the pipeline
  can ever produce `unit_paad`, so every id-based join across graph / lens / observables / oracle
  fails structurally, not incidentally.
- **Recommended fix:** Make the F0 decision (ARCH ratifies; not yours to implement code for) to
  introduce an entity gazetteer/registry mirroring `config/places.yaml`: each real entity gets a
  stable semantic id + aliases + type. DATA-C supplies the registry; RESOLVE consumes it so a
  cluster's canonical **node id** becomes the semantic id; ARCH ratifies the contract that triple
  endpoints are resolved entity references (not free strings). EVAL then matches on the shared id
  space. This one decision is the root fix for the lens/observable/oracle anchor breaks below.
- **Severity:** blocks-demo.
- **Cross-service dependencies:** This is the master contract decision everything else in this
  handoff depends on. It must land before AR-2 can be considered resolved (AR-2's own code fix is
  still needed regardless — see below). It also unblocks RESOLVE's endpoint-linking fix (RES-1,
  owned by RESOLVE) and MONITOR/ASK's anchor resolution. Nothing here should be built by ARCH
  alone — DATA-C owns the registry content, RESOLVE owns consuming it into canonical node ids; ARCH's
  job is the contract ratification plus the two lens code fixes below (AR-2, AR-3), which are
  needed either way.

### AR-2 — Lens anchor matching is literal-id, not resolved (blocks-demo)

- **Symptom:** `apply_lens` returns 0 nodes / 0 edges for `lens-hq9p-pk` (anchors `unit_paad`,
  `site_karachi`) — `view_lens.json` is empty.
- **Evidence:**
  - `backend/chanakya/view/lens.py:52-57` — `for anchor in subject.anchors: if anchor in und:` —
    literal string membership check against the graph's node-id set, with no resolution/lookup
    step.
  - `config/subjects.yaml:7-10`; `view_full.json` (no node has id `unit_paad` or `site_karachi`);
    `tmp/conv/eval-rca/00-evidence-summary.md:5`; `view_lens.json` is empty.
  - The same literal-id-anchor pattern exists in ASK's `query_graph` (`tools.py:397`) — a sibling
    defect in a different service, not yours to fix, but worth flagging for consistency.
- **Root cause:** `apply_lens` assumes anchor ids in config are already node ids in the graph. Two
  things make that false today: (a) AR-1 — no node carries the canonical semantic id at all; (b)
  even independent of AR-1, the lens never resolves an anchor through an alias/attribute lookup —
  it only ever does exact membership testing. So this bug would resurface even after AR-1 lands
  for any anchor spelled slightly differently than the stored node id.
- **Recommended fix:** If the AR-1 registry lands and RESOLVE writes canonical ids onto nodes,
  anchor matching becomes a direct hit. Regardless, `apply_lens` should resolve each anchor through
  an alias/attribute index (reuse whatever name/alias resolution mechanism the agent or RESOLVE
  exposes) before seeding traversal — never bare `anchor in und`. Do this defensively even if AR-1
  lands, so a future registry typo or alias drift doesn't silently re-empty the lens.
- **Severity:** blocks-demo.
- **Cross-service dependencies:** Depends on AR-1 (registry) and on RES-1 (RESOLVE's
  edge/entity-namespace-split fix — until edges and entity nodes are joined, the lens will remain
  near-empty even with anchors correctly resolved, since anchors would resolve to isolated nodes
  with no incident edges). Unblocks: any subject-scoped view, the demo's primary lens
  (`lens-hq9p-pk`), and downstream consumers of the lens (ASK, MONITOR scoping).

### AR-3 — Lens materiality-filter schema drift (major)

- **Symptom:** The subject's chaff/off-subject scoping is dead. `subjects.yaml` declares
  `node_types_allow`, `exclude_off_subject`, `materiality_attrs`, `never_drop_indeterminate`, but
  the lens silently ignores all of them.
- **Evidence:**
  - `backend/chanakya/view/lens.py:24-37` — `_passes_materiality` reads **only**
    `min_chokepoint_count` and `chokepoint_status_in` (verified by direct read).
  - `config/subjects.yaml:11-32` — `materiality_filter` block declares `node_types_allow`,
    `exclude_off_subject`, `materiality_attrs`, `never_drop_indeterminate`, none of which are
    consumed.
- **Root cause:** The lens implementation and the subjects config were written against two
  different (never-reconciled) versions of the materiality-filter schema. There is no schema
  validation on the filter dict, so unknown keys pass through silently instead of erroring —
  masking the drift.
- **Recommended fix:** Implement the declared filter semantics in `_passes_materiality` (honor
  `node_types_allow` / `exclude_off_subject` / `never_drop_indeterminate`), or explicitly converge
  config and code on one agreed schema and update `subjects.yaml` to match. Either way, add
  validation so an unknown filter key raises rather than silently passing — this is what let the
  drift go unnoticed.
- **Severity:** major (not the cause of today's empty lens — that's AR-1/AR-2 — but means zero
  chaff protection once anchors resolve).
- **Cross-service dependencies:** None upstream; independent of AR-1/AR-2 and can be fixed in
  parallel. It only becomes visible/testable once AR-1+AR-2 (and RES-1) let the lens return a
  non-empty node set to filter.

## Reattributed away (not ARCH's finding — noted for completeness)

- **Eval matching by literal oracle id** — not a defect; `eval/report.py` + `gen_evidence.py`
  already match oracle -> view by name/type overlap, not id equality. The reported divergence is
  real RESOLVE under-merge (RES-2) + the id-namespace split (RES-1); a DATA-C attribute matcher
  would not move these numbers.
- **Id-namespace split (edges keyed by bare LLM string vs. entities keyed `ent:<type>:<name>`)** —
  merged into RESOLVE's RES-1; RESOLVE owns the endpoint-linking fix, ARCH only ratifies the
  id-registry contract (AR-1).
- **Hero-query crash / node-id KeyError** — owned by ASK (AS-1), not ARCH.

## How to reproduce + verify your fix

```bash
export CHANAKYA_ROOT=/home/synaptic/data-science/research/rough/osint/wt-EVAL
cd /home/synaptic/data-science/research/rough/osint/wt-EVAL

# Regenerate the evidence bundle after your change
/home/synaptic/data-science/research/rough/osint/wt-EVAL/backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py

# Then inspect the refreshed outputs:
#   tmp/conv/eval-rca/00-evidence-summary.md  — check the oracle-id-to-view-node mapping (AR-1)
#   tmp/conv/eval-rca/view_lens.json          — should now be non-empty for lens-hq9p-pk (AR-2)
```

Verification checklist per finding:

- **AR-1:** After the registry/RESOLVE changes land, confirm in `00-evidence-summary.md` that at
  least the primary oracle ids (`unit_paad`, `mfr_casic`, `site_karachi`, `unit_hq9b`) now
  correspond to exactly one canonical view node each, not 1..9 name-derived duplicates.
- **AR-2:** Confirm `view_lens.json` for `lens-hq9p-pk` is non-empty (anchors `unit_paad`,
  `site_karachi` resolve to real nodes and traversal returns a connected subgraph, not zero
  nodes/edges). Note this also requires RES-1 to be fixed for the returned subgraph to have
  meaningful edges, not just isolated anchor nodes.
- **AR-3:** Once the lens returns a non-empty node set, confirm off-subject / disallowed node types
  declared in `subjects.yaml`'s `materiality_filter` are actually excluded from `view_lens.json`,
  and that an unrecognized filter key now raises instead of being silently ignored.
