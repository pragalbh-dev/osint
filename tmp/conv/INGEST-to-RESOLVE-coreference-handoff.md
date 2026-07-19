# In-document coreference — INGEST pass 2 + the RESOLVE honor policy (BOTH HALVES DONE)

**Status:** **COMPLETE** on `feat/ingest-coref` (worktree `wt-INGEST-coref`, rebased onto `origin/main`
after Phase 3 / PR #35 + #36). Design: `INGEST-RESOLVE-in-document-coreference-clustering-PROPOSAL.md`
(Option B, derived overlay). Decisions: `DECISIONS.md` → the two "in-document coreference" blocks.

> **This file previously specified the RESOLVE half and was written against pre-Phase-3 code. Two of its
> assumptions were wrong by the time Phase 3 landed** (see §5). It is now a record of what was built, not a
> spec. Consistent with the Phase-4 audit's finding that handoffs go stale as specs — verify against code.

---

## 1. What Phase 3 changed, and what that did to the case for this

Phase 3 (`24124b1`) largely closed the gap this feature was built for, **deterministically**:

| | RCA baseline | Phase 2 | **Phase 3** |
|---|---|---|---|
| nodes | 294 | 258 | **162** |
| `unknown` (dangling endpoints) | 109 | 86 | **3** |
| merges | 5 | 5 | **53** |

Its "endpoint-as-mention" fix plus a **containment/acronym bootstrap** now resolve `CPMIEC`, `BIRM` /
`Beijing Institute of Radio Measurement`, and `CASIC` / `China Aerospace Science and Industry Corporation`
with no model call. **Those were the motivating examples in this document's first version — they are no
longer the case for coreference.** A deterministic rule beats an LLM pass whenever it can reach the answer.

**What remains, honestly.** Of the 9 pairs still in the adjudication queue, ~4 are genuine equivalences a
document quote could settle (`HQ-9P fire control radar ↔ Type 305B`, `WS-series 8x8 chassis ↔ TEL
platform`, `CPMIEC ↔ China National Precision Machinery Import & Export Corp`, `HQ-16 ↔ LY-80`) and 5 are
traps that must stay apart (three distinct customs contract numbers; `Turkmenistan ↔ Uzbekistan`). The
first two of those four are **descriptive ↔ designator** pairs sharing no token — the slice no string
method can ever reach. So the value is now: **reach the non-lexical cases, and attach a verbatim licence
to what an analyst would otherwise adjudicate unaided** — not "find merges nothing else can".

## 2. The policy as built

`EXPLICIT_EQUIVALENCE` (the document *states* it — apposition, acronym expansion, "also known as") may
**bootstrap** (auto-merge). `NAME_VARIANT` and `UNAMBIGUOUS_ANAPHOR` are the extractor *interpreting*, so
they stay **raise-only** and reach the analyst queue carrying their quote.

This deliberately crosses Phase-3's D-2.5 raise-only rule for one narrow, opted-in category, on the
grounds that a coreference claim is not an ordinary identity assertion: it is a reading of one document's
own discourse, and it must quote the licensing span. Everything else about D-2.5 is untouched.

**Authoritative is never unconditional.** In `resolve._coref_pairs`:
- a stated/configured `distinct-from` **drops** the pair outright — a do-not-merge outranks any reading;
- a **type**, **namespace**, or **hard-attribute** contradiction (`scoring.has_hard_conflict`) **demotes**
  the pair to the analyst queue rather than deleting it — the evidence still reaches a human;
- an absent attribute is *not* a contradiction (absence ≠ disagreement).

## 3. Where it lives

| Concern | Location |
|---|---|
| Emission (pass 2) | `ingest/coref.py`, invoked from `extract_document` (so the live lane **and** the keyless bundle seed inherit it) |
| Predicate | `coref-same-as` — `config/ontology.yaml`, symmetric, **not** `extractor` |
| Claim payload | evidence category + verbatim quote + cluster id in the tier-3 bag; `doc_ref` cites the licensing span |
| Edge plumbing | `resolve/entities.py` — `Edge.attributes` carries the claim's tier-3 bag |
| Split & gates | `resolve.__init__._coref_pairs` → `(authoritative, raise_only)` |
| Bootstrap | `resolve/cluster.py::resolve_entities(..., authoritative)` |
| View | consumed, **not drawn** (`view/pipeline._assemble`), same as `same-as` |
| Config | `resolution.yaml → coref_authoritative_evidence` (RESOLVE) · `credibility.yaml → coreference` (INGEST, **still commented out**) |

## 4. To actually turn it on — BOTH GATES ARE SHUT

The feature ships **fully off**: the producer is commented out *and*
`resolution.yaml → coref_authoritative_evidence` is **empty** (every cluster raise-only = Phase-3 D-2.5
behaviour). Two independent switches on purpose — a pre-set honor policy would mean enabling the producer
silently switched auto-merging on in the same motion.

**Do this in order, with EVAL:**

1. Uncomment `coreference:` in `config/credibility.yaml`. Costs a **second extraction call per document**
   and **re-records every frozen bundle** — coordinate with EVAL's re-record rather than doing it twice.
2. **Measure the false-merge rate on the 6 frozen scenarios**, and the before/after adjudication-queue size.
3. Only then consider `coref_authoritative_evidence: [EXPLICIT_EQUIVALENCE]`.

### ⚠ Known collision to check at step 2

`d10_sat_cloud_gap` states *"HT-233 (H-200) engagement radar array"* — a textbook `Full Name (SHORT)`
apposition, exactly what `EXPLICIT_EQUIVALENCE` catches. But that orphan alias is a **deliberate demo beat
an analyst is meant to earn** (`cluster._descriptor_extension` says so). Auto-merging it would silently
delete the beat. **Not measured** — the producer is dormant, so this is a pattern match, not an observation.

Raise-only is arguably the better demo behaviour regardless: the pair reaches the queue **with its
licensing quote**, so the human still earns the merge but is handed the exact sentence justifying it.

## 5. Corrections to this document's earlier version (kept deliberately)

- It said "do not add `coref-same-as` to `_IDENTITY_PREDICATES`". That constant was **renamed** to public
  `IDENTITY_PREDICATES` and its meaning changed: identity claims are now *consumed as merge signals and
  suppressed from the view*, not scored as graph edges. The advice's intent survived (coreference gets its
  own channel, not a heavier weight on an existing one); its literal wording did not.
- It cited 86 dangling `unknown` nodes as the motivating evidence. That is now **3**.

## 6. Limitation to carry forward

A mention is keyed by **surface form within one document** (pass 1 already collapses same-name mentions per
document), so one document using a single label for two genuinely different entities is not separable. An
**under-reach, never an over-merge**.

## 7. Tests

`backend/tests/ingest/test_coref.py` (28) — emission, dormancy, and every over-merge rail.
`backend/tests/resolve/test_coref_honor.py` (11) — opt-in, category split, veto, contradiction demotion,
cross-type refusal, and consumed-not-drawn. Note the fixture lesson: entities must use production ids
(`ent:<type>:<name>`) or endpoints resolve to freshly minted attribute-less twins and every
attribute-reading rail silently passes.
