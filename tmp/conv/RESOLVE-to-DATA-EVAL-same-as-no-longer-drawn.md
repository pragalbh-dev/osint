# RESOLVE → DATA-C / EVAL: `same-as` is no longer a drawn edge (P3.2 / D-2.5)

**From:** RESOLVE (Phase-3 Wave 2, branch `fix/phase3-resolve`) · **Date:** 2026-07-19
**Action needed by:** whoever owns `corpus/scenarios/*/answer_key.json` and the eval scoring.
**Do not treat this as done — RESOLVE deliberately did not touch the answer key.**

## What changed

Per ratified decision **D-2.5** (Phase 2) and **D-P3.4** (`tmp/conv/eval-rca/phase3-resolve-PLAN.md` §2, P3.2),
an identity assertion is now **consumed as a merge signal, not drawn as a relationship**:

- a `same-as` claim no longer produces a view edge. The knowledge layer answers "are these the same
  thing?" by **merging** the two nodes, or by leaving them apart with a **candidate** `same-as` edge the
  analyst still has to adjudicate (`merge_band: candidate`, emitted by `view/pipeline._resolution_edges`).
- `distinct-from` is unchanged: still a hard veto **and** still drawn.

Effect on the frozen scenario: drawn `same-as` went 58 → 9, and all 9 remaining ones are adjudication
candidates rather than claim-derived relationships.

## The conflict

`corpus/scenarios/hq9p_primary/answer_key.json` → `ground_truth.edges` contains:

```json
{"rel": "same-as", "from": "FD-2000", "to": "var_hq9p", "status": "confirmed",
 "note": "export designator = HQ-9/P"}
```

That expectation is now **structurally unsatisfiable**: FD-2000 and `var_hq9p` are auto-merged into one
node (confidence 1.0, via the alias class), so there is nothing left to draw an edge *between*. The eval
line in `tmp/conv/eval-rca/00-evidence-summary.md` reading

    - **FD-2000 -same-as-> var_hq9p** (want confirmed): 9 view edges of type 'same-as'

is now counting *candidate* edges, which is not what it means to check.

## Suggested resolution (DATA-C / EVAL call, not RESOLVE's)

The ground truth here is right, but it is stated in the wrong layer. The check that FD-2000 ≡ HQ-9/P
should assert a **merge**, not an edge — e.g. move it out of `ground_truth.edges` into an identity/merge
section, graded against the node's `attrs.resolved_from` (which carries `merged_ref`, `merge_confidence`
and the score breakdown) or against `Partition.same_as` / `entity_canonical`. The `distinct-from` entries
in `ground_truth.edges` stay exactly as they are — those *are* drawn.

## Second, smaller observation (no action requested)

The fixed hero path's answer lost `comp_tel_chassis` from its match list. Cause: that node was reachable
from the lens anchor **only through a `same-as` hop**. That is arguably the change working as intended —
traversing an identity edge is not a relationship hop — but it means the TEL chassis is currently
connected to the subject only via `component-of` → a TEL-platform node that `equips` **`ent:variant:HQ-9`**
(the China variant), never `var_hq9p`. The hero path already returned `hops: []` before this change, so
this is not a new break; it points at edge coverage / basing (RES-3, P3.4-P3.5 and the INGEST structural
edges), not at identity.
