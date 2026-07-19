# EVAL RCA handoff — ASK (query agent)

## Context

The pipeline was run end-to-end for the first time over real extracted bundles, and the rebuilt
graph diverges sharply from the oracle. This is ASK's (query/retrieval agent) share of the fix.
Evidence bundle: `tmp/conv/eval-rca/00-evidence-summary.md` and `tmp/conv/eval-rca/view_full.json`
(the rebuilt view used for the live repro below); generated claim bundles at
`corpus/scenarios/hq9p_primary/claims/`.

## TL;DR

1. `_from_get_node` in `assemble.py` KeyErrors (hard crash) whenever `get_node` fails — every
   error-shaped tool result must be guarded, not just the happy path.
2. The hero query path (`run_fixed_hero_path`) hardcodes fallback ids and never checks whether
   upstream link/gather calls actually succeeded, so on a broken/empty view it silently runs on
   phantom ids and emits a misleading refusal instead of an honest one.
3. Two minor robustness gaps: `check_sufficiency` doesn't raise on an unknown id (unlike its
   sibling tools), and the hero `find_paths` call has no `edge_whitelist`, so it would BFS through
   junk edges (same-as / ad-hoc predicates) even once upstream is fixed.

**Important framing:** the deep reason the hero trace can't run at all right now (name-derived
ids, empty lens, "unknown" node types, 0/109 edge endpoints matching a real entity) is upstream —
owned by RESOLVE (`RES-1`, edge/entity id-namespace split) and ARCH (`AR-2`, lens literal-id
match). ASK is NOT the root cause of the graph divergence. ASK's job is to (a) stop crashing and
(b) degrade honestly instead of masking upstream failure — both are ASK-owned regardless of when
upstream lands.

## Findings

### AS-1 — `_from_get_node` KeyError crash on any failed `get_node` call

- **Severity:** blocks-demo
- **Symptom:** The hero query crashes with `KeyError: 'node_id'` at `backend/chanakya/agent/assemble.py:149`
  (`_from_get_node`) whenever `get_node` did not return a success payload. This is a hard crash on
  the disqualifying/refusal path — exactly the path that must never fail.
- **Evidence:**
  - `backend/chanakya/agent/assemble.py:134-152` — `_from_get_node` guards only `if call is None`,
    then unconditionally reads `r['node_id']` at line 149.
  - `backend/chanakya/agent/tools.py:225-226` — `get_node` raises `ToolError` when the node is
    absent.
  - `backend/chanakya/agent/tools.py:570-573` — `run_tool` catches that and returns a structured
    error dict `{'error': ..., 'suggestion': ...}` (no `node_id` key).
  - Live repro: calling `get_node` for a missing id returns
    `{'error': "no node with id 'comp_ht233'", 'suggestion': ...}`; feeding that result into
    `_from_get_node` raises the `KeyError` at line 149.
  - Contrast: `_from_paths`'s `node_id` read (assemble.py:73) IS gated by
    `result.get('materiality')`; `_from_query_graph` / `_from_neighbors` guard on their own result
    keys. `_from_get_node` is the one builder that skips this pattern.
- **Root cause:** Every per-shape result builder in `assemble.py` is supposed to check for an
  error-shaped result before reading fields, but `_from_get_node` only checks `call is None` and
  never checks for the `error` key, so an error dict gets treated as a success payload.
- **Recommended fix:** Guard `_from_get_node`:
  `if call is None or 'node_id' not in call.result: return None`. Better: add one uniform helper,
  e.g. `_ok(result) = 'error' not in result`, and have every builder call it first, so a failed
  tool call always falls through to the refusal path instead of crashing.
- **Cross-service dependencies:** None — fully ASK-owned, fixable independently and immediately.

### AS-2 — Hero path masks upstream failure with hardcoded fallback ids, then emits a misleading refusal

- **Severity:** major
- **Symptom:** On the real (broken) view, every hero tool call in the fixed demo path errors out —
  yet the path keeps going, substituting hardcoded ids (`comp_ht233`, `mfr_casic`,
  `site_karachi`) at each step, and — once the AS-1 crash is patched — ends by emitting
  `"Insufficient evidence to assess comp_ht233"`. That message implies a genuine evidence gap,
  when in fact the anchors and the chain never resolved to anything real at all. Separately,
  `find_entity('HQ-9/P')` is called to resolve the variant anchor but its result is discarded, and
  `variant_anchor` ends up bound to a unit (`unit_paad`) rather than to the resolved variant.
- **Evidence:**
  - `backend/chanakya/agent/loop.py:147-153` — anchors taken verbatim from the lens;
    `find_entity('HQ-9/P')` result discarded.
  - `backend/chanakya/agent/loop.py:163` — `query_graph(anchor='unit_paad')`.
  - `backend/chanakya/agent/loop.py:167` — `comp_id = pool[0]` else falls back to literal
    `'comp_ht233'`.
  - `backend/chanakya/agent/loop.py:171` — `mfr_id` else falls back to literal `'mfr_casic'`.
  - `backend/chanakya/agent/loop.py:174` — `find_paths(src=site='site_karachi', ...)`.
  - `backend/chanakya/agent/loop.py:184` — `check_sufficiency('comp_ht233')`.
  - Live repro: all 5 hero tool calls returned `{'error': ...}`. `find_entity('HQ-9/P')` returned
    `{'error': "did you mean 'HQ-9P'"}` (node name is literally `HQ-9P`, a normalization mismatch).
    `unit_paad` / `site_karachi` / `comp_ht233` / `mfr_casic` were all `in-view=False` against
    `view_full.json`.
  - `check_sufficiency('comp_ht233')` returned `sufficient=False, known_gap=None, missing=[]`,
    which the hero path then surfaces as a refusal naming a phantom entity that was never real to
    begin with.
- **Root cause:** `run_fixed_hero_path` hardcodes the demo's canonical ids as fallbacks and never
  checks `result.get('error')` after preceding link/gather calls before using their outputs.
  There's no "the chain could not be built" branch — every failure silently degrades into a
  hardcoded literal id, so the final `check_sufficiency` call runs against a scope that was never
  grounded in the actual (rebuilt) graph.
- **Recommended fix:** Resolve anchors through `find_entity` / alias lookup before use (don't
  discard the `find_entity('HQ-9/P')` result). After each link/gather call, check
  `result.get('error')` and short-circuit to a first-class, honest refusal that names the *actual*
  missing input (e.g. "subject anchors not present in rebuilt view; lens is empty") instead of
  substituting a hardcoded literal. Only call `check_sufficiency` on a scope that is confirmed to
  exist.
- **Cross-service dependencies:** Depends on `AS-1` (must not crash first). To actually *run* the
  hero trace end-to-end (not just refuse honestly), ASK needs a non-empty lens with resolvable ids
  and canonical directed edges from upstream — specifically `RES-1` (RESOLVE: edge/entity
  id-namespace split fix) and `AR-2` (ARCH: lens literal-id-match fix). Until those land, the
  correct ASK behavior is an honest, clearly-worded refusal — not a working trace.

### AS-3 — `check_sufficiency` silently returns a fabricated "insufficient evidence" verdict for a nonexistent id

- **Severity:** minor
- **Symptom:** `check_sufficiency` returns a generic `sufficient=False` "insufficient evidence"
  verdict for a node id that doesn't exist at all, rather than signalling "no such node." This is
  the mechanism that lets the hero path (AS-2) refuse about a phantom entity as if it had actually
  assessed it.
- **Evidence:**
  - `backend/chanakya/agent/tools.py:490-531` — `check_sufficiency` does
    `ctx.nodes_by_id.get(scope) or ctx.edges_by_id.get(scope)`; on a miss it falls straight through
    to `sufficient=False` with empty `missing_slots`, instead of raising.
  - `backend/chanakya/agent/tools.py:226, 257, 288-291, 397` — sibling id-taking tools
    (`get_node`, `neighbors`, `find_paths`, `query_graph`) all raise `ToolError` for an unknown id.
- **Root cause:** `check_sufficiency` is missing the existence guard that every other id-taking
  tool has, so it can't distinguish "this real node lacks corroborating evidence" from "this id
  doesn't exist."
- **Recommended fix:** Add an existence guard at the top of `check_sufficiency` that raises
  `ToolError` on an unknown id, matching its siblings, so an unknown id becomes a lookup failure
  rather than a fabricated evidence-gap verdict.
- **Cross-service dependencies:** None — independent, ASK-owned.

### AS-4 — Hero `find_paths` call has no edge-type whitelist

- **Severity:** minor
- **Symptom:** Even after AS-1/AS-2 are fixed and upstream anchors resolve, the flagship
  "supply-chain chain" query is an unconstrained BFS over *all* edge types, so it could route
  through same-as merge shortcuts or ad-hoc predicate edges instead of the intended
  based-at → inducted-into → equips → manufactures chain.
- **Evidence:**
  - `backend/chanakya/agent/loop.py:174` — `find_paths(src=site, dst=mfr_id, ...)` passes no
    `edge_whitelist`.
  - `backend/chanakya/agent/tools.py:293, 307-322` — `find_paths` does bidirectional BFS over
    every edge type unless `edge_whitelist` is set.
  - `tmp/conv/eval-rca/00-evidence-summary.md:20-49` — the current view is dominated by ~42
    same-as edges and ~25 ad-hoc predicate edges, exactly the kind of edge that an unconstrained
    BFS would wander through.
- **Root cause:** The hero query never constrains which edge types are traversable, relying on the
  view being "clean" — which it currently is not (see cross-service note below).
- **Recommended fix:** Pass an `edge_whitelist` of the canonical ontology chain edge types
  (based-at, inducted-into, equips, manufactures / supplies-component, etc.) to the hero
  `find_paths` call so the trace is constrained to meaningful relations, independent of whatever
  junk edges exist in the view.
- **Cross-service dependencies:** None to implement now; its practical value is fully realized
  once `INGEST` stops minting same-as/ad-hoc edges (fix-order items 3-4) and `RESOLVE` reconnects
  the graph (`RES-1`).

## No independent graph-shape defects found

ASK does not own the reason the graph itself is disconnected/wrong (109 "unknown" endpoint nodes,
0/190 entities with an incident edge, zeroed relational/source-asserted scores). That is Master A
in the shared cross-service note — owned by **RESOLVE** (`RES-1`, id-namespace split between
bare-string triple endpoints and `ent:<type>:<name>` entity nodes) and **ARCH** (`AR-2`, lens
anchor resolution). ASK's findings above are strictly about how the query agent behaves *given*
that broken input: it must not crash (AS-1), and it must not paper over the breakage with
hardcoded ids and a misleading refusal (AS-2/AS-3/AS-4).

## How to reproduce + verify your fix

```bash
export CHANAKYA_ROOT=/home/synaptic/data-science/research/rough/osint/wt-EVAL

# Run the hero path directly to reproduce the crash (AS-1) / masked failure (AS-2):
/home/synaptic/data-science/research/rough/osint/wt-EVAL/backend/.venv/bin/python -c "
from chanakya.agent.loop import run_fixed_hero_path
print(run_fixed_hero_path())
"

# Regenerate the evidence bundle after your change (rebuilds view_full.json / view_lens.json /
# 00-evidence-summary.md at tmp/conv/eval-rca/):
/home/synaptic/data-science/research/rough/osint/wt-EVAL/backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py
```

Verify per finding:
- **AS-1:** the hero path call above must not raise `KeyError` even when every upstream tool call
  errors — it should return a refusal object, not a traceback.
- **AS-2:** inspect the refusal text/object returned — it must name the actual unresolved input
  (e.g. "lens empty" / "anchor `HQ-9/P` did not resolve") rather than a hardcoded literal like
  `comp_ht233` that was never grounded in the view. Confirm `find_entity('HQ-9/P')`'s result is
  actually consumed, not discarded.
- **AS-3:** call `check_sufficiency` with a made-up id (e.g. `"comp_does_not_exist"`) directly via
  the tool dispatcher and confirm it raises `ToolError`, not a silent `sufficient=False`.
- **AS-4:** confirm the `find_paths` call inside `run_fixed_hero_path` passes a non-empty
  `edge_whitelist` and that regenerating the evidence bundle shows no same-as/ad-hoc edges in the
  returned path.

Once `RES-1` / `AR-2` land upstream, re-run the hero path end-to-end and confirm it produces a real
traced chain (not just an honest refusal) through `view_full.json`'s reconnected entities.
