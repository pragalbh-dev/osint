# INGEST → RESOLVE — in-document coreference: what INGEST now emits, and what RESOLVE must do

**Status:** INGEST half **DONE** on `feat/ingest-coref` (worktree `wt-INGEST-coref`, branched off
`origin/main` @ ea392c6). RESOLVE half **NOT STARTED** — that is this handoff.
**Source design:** `tmp/conv/INGEST-RESOLVE-in-document-coreference-clustering-PROPOSAL.md` (Option B,
derived overlay). **Decisions:** `DECISIONS.md` → "INGEST — in-document coreference clustering".

---

## 1. Why you are getting this (the measurement)

On the rebuilt view, **86 of 258 nodes (33%) are `unknown`-type nodes** — dangling relation endpoints that
never got an entity claim. They include:

```
CPMIEC                                         BIRM
China Precision Machinery Import-Export Corp.  Beijing Institute of Radio Measurement
China National Precision Machinery Import & Export Corporation
CASIC                                          CASIC's 23rd Research Institute
China Aerospace Science and Industry Corp.     23rd Research Institute
FD-2000                                        FD-2000 long-range surface-to-air missile system
```

These are one entity each, fragmented across surface forms, and RESOLVE cannot fix it from strings alone —
the licensing evidence ("… Corporation (CPMIEC)") lives in the document and is gone by the time RESOLVE
runs. INGEST now captures it. **Nothing consumes it yet.**

## 2. What INGEST emits

One relationship claim per non-anchor cluster member, on a **dedicated predicate**:

| Field | Value |
|---|---|
| `payload.predicate` | **`coref-same-as`** (new; `config/ontology.yaml`, symmetric, NOT `extractor`) |
| `payload.subject` / `.object` | the two verbatim surface forms |
| `attributes._coref_cluster` | document-local cluster id (`c1`, `c2` …) — groups a >2-member cluster |
| `attributes._coref_evidence` | `EXPLICIT_EQUIVALENCE` \| `NAME_VARIANT` \| `UNAMBIGUOUS_ANAPHOR` |
| `attributes.source_quote` | the **verbatim licensing span**, checked to occur in the document |
| `attributes._subject_mention` / `._object_mention` | the entity-claim id that named each endpoint (when declared) |
| `doc_ref` | the licensing span itself (G4: one click to the text that licenses the merge) |
| `kind` | `inference` (+`premises` = member mentions) when a member is a declared entity; else `observation` |

Ordinary relationship claims **also** now carry `_subject_mention` / `_object_mention`. These are
**positional** (they describe `Triple.subject`/`.object`) — `edge_direction.swap_mention_refs` keeps them in
sync under reorientation, and `dedup.remap_claim_refs` rewrites them wherever ids are reassigned.

## 3. THE critical constraint — do not "score" this

`coref-same-as` is deliberately **absent** from `resolve.scoring._IDENTITY_PREDICATES`
(`{same-as, same_as, aka, also-known-as, marketed-as, is}`), which feed the `source_asserted` **weighted
term** of `merge_score`.

**Do not simply add `coref-same-as` to that set.** That is the failure mode the proposal explicitly
rejected: it would turn a decision made *with* the document's discourse context into a partial score that
attribute-dissimilarity can outvote — re-deriving, with less information, what the extractor already
decided with more. The whole point of the separate lane is that the honor policy is a **different
mechanism**, not a heavier weight.

There is a regression test pinning this: `tests/ingest/test_coref.py::
test_coref_lane_is_inert_to_the_resolvers_merge_scoring`.

## 4. What RESOLVE should do — "authoritative-unless-contradicted"

Proposed shape (proposal §4), to be confirmed when you build it:

1. **Treat an in-document cluster as a merge directive that shortcuts the attribute scorer**, not as a
   scoring input. Mechanically this most resembles the existing **bootstrap** pass (high-precision, no
   relational term) or `AliasIndex` equivalence — not `merge_score`.
2. **`EXPLICIT_EQUIVALENCE` / `NAME_VARIANT`** → co-locate the members onto one node **unless a hard
   attribute contradiction** exists among them (conflicting `origin_country`, `designator`, coordinates) —
   in which case route to HITL rather than merge.
3. **`UNAMBIGUOUS_ANAPHOR`** → open question: auto-apply, or route to HITL by default? Measure the
   false-merge rate on the 6 frozen scenarios and decide from data. The emission side can already be
   restricted to the two safe categories via `credibility.yaml → coreference.categories`.
4. **The existing `distinct_from` veto must still outrank a cluster.** INGEST already refuses to cluster a
   pair the document itself distinguished, but the configured/learned veto is a second, independent rail —
   keep it above this.
5. **Store the cluster id, evidence category and licensing quote on the derived node** so HITL can inspect
   and **split** (apply the cluster to a subset). Split is native here — you are choosing a partition, never
   un-welding — which is what keeps RESOLVE's merge-monotonicity from becoming a trap.
6. **Relations follow their mention.** Under a split, each relation is already anchored by
   `_subject_mention`/`_object_mention` to the mention that named it, so it follows its sub-node with zero
   re-inference. Prefer the mention ref over the surface string once you honour clusters.

## 5. How to turn it on

Dormant by default. Uncomment the `coreference:` block in `config/credibility.yaml`. **Enable it together
with the honor policy, not before** — it costs a second extraction call per document and re-records every
frozen bundle, and until RESOLVE honours it the clusters are inert (that is by design, so this branch could
land safely ahead of you).

Note for EVAL/DATA: enabling **will** require re-recording the frozen bundles, and will add `coref-same-as`
edges to the view. Coordinate that with the Phase-3 re-record rather than doing it twice.

## 6. Limitation to carry forward

A "mention" is keyed by **surface form within one document** (pass 1 already collapses same-name mentions
per document). So one document using one string for two genuinely different entities ("3rd Battalion" twice)
is not separable. This is an **under-reach, never an over-merge** — those two occurrences were already a
single claim before this pass existed.

## 7. Tests to read first

`backend/tests/ingest/test_coref.py` (28 tests) — dormancy, the lane separation, every over-merge rail
(unquotable span, unknown evidence kind, cross-type, stated distinction, lone member, invented id,
overlapping clusters), ontology typing of undeclared endpoints, and the mention-ref remap/swap contracts.
