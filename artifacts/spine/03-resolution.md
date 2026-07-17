# Spine — Entity Resolution

Covers: how identity is resolved across sources. In C this is the *marquee* graded feature
(`../md/04-claude-chat.md` Q1) — the whole value rests on confidently fusing "Factory 404" =
"State Research Bureau 404" = a chassis in a photo into one node across transliterations and shell aliases.

---

## Decisions

### Resolve like a senior analyst would — iterative, relational, not just string/embedding
Resolution is **iterative collective / relational entity resolution**, not attribute similarity alone and
not single-pass. The signal stack, roughly in the order an analyst weighs them, feeds one merge score:

1. **Attribute match** — name variants, transliteration rules, IDs, HS codes.
2. **Relational match (highest value)** — **shared neighbourhood**: two nodes that both connect to the
   same regiment and the same site are probably the same entity even if names differ. This is the
   "analyst" signal that pure similarity misses.
3. **Contextual/temporal consistency** — can't be in two places at once; timeline coherence.
4. **Corroboration weighting** — a merge asserted by a credible source beats one merely inferred (this is
   the `source_asserted` term of the *merge* score — an identity signal, **not** claim credibility).

`merge_score = 0.30·attribute + 0.40·relational + 0.15·temporal_consistency + 0.15·source_asserted`; bands
**≥0.85 auto-merge · 0.55–0.85 HITL · <0.55 keep-separate**.

Because resolution is relational and the 0.40 relational term is **uncomputable before any partition
exists**, the merge runs in two phases, iterated:

- **Phase 1 — high-precision bootstrap pass.** Merge only on unambiguous evidence (shared hard ID, or
  exact-strong attribute + name). No relational term needed. Produces an initial partition.
- **Phase 2 — iterative relational fixpoint.** With a partition in hand, recompute `merge_score`
  (relational term now defined by shared neighbourhood) and auto-merge/HITL/separate. Merging one pair
  changes neighbourhoods and can unlock further merges, so **iterate the pass until no new auto-merge
  fires** (the fixpoint). This terminates because merges are monotone — clusters only grow, never split,
  within a rebuild. Mid-band pairs route to HITL; weak pairs stay separate.

This whole pipeline runs inside `rebuild()` as a pure function of (evidence log, decision log, config), so
it is deterministic given a fixed processing order and replayed HITL decisions.

### Confidence bands with a HITL middle
Every candidate merge gets a `merge_confidence`:
- **above high threshold** → auto-merge;
- **below low threshold** → keep separate;
- **in between** → route to HITL for accept / reject / split (via the adjudication service,
  `05-hitl-and-triage.md`).

### Recall is the goal of candidate-gen; the merge decision is precision-first
**Max recall is the job of blocking / candidate-generation (propose every pair worth checking), NOT of
the merge decision.** The merge decision is deliberately precision-first: a plausible-but-wrong pair
(**FD-2000 ≠ FT-2000**) lands in the HITL band rather than auto-merging. Recall lost to that conservatism
is recovered by the relational iteration (a later pass may confirm the link) and by HITL. Never frame the
merge step as "resolve as many pairs as possible" — that corrupts the ORBAT.

### Two scores, two objects — never averaged
`merge_confidence` (does node A = node B, an **identity** question, carried on the `same-as` edge) is a
different quantity from `claim_credibility` / `assertion_confidence` (is the assertion **true**, carried
on the resolved node/edge — see `04-credibility.md`). They are never blended into one number. This
separation is what lets the system say *"the node is real (confidently resolved) but its basing claim is
only probable (credibility)"*. The "credibility" that appears inside resolution is only the
`source_asserted` term of `merge_score`, not `claim_credibility`.

### HITL merge decisions grow the alias table (learning)
Each analyst merge/split decision is written back and **grows the alias table**, so the same pair
auto-resolves next time. This is one concrete adaptation mechanism (`06-adaptation.md`).

### False-merge discipline
Resolution must be as good at *keeping things apart* as fusing them. C has real false-merge traps (e.g.
**FD-2000 ≠ FT-2000** — different systems the trade press conflates; radar-vs-system conflation like
HT-233 vs FD-2000) catalogued in `../md/05-data-scoping-C.md` §4. A confident wrong merge corrupts the
ORBAT; the middle band exists precisely to surface these to a human.

### The LLM at resolution is a PROPOSER, never the authority
No LLM call runs inside `rebuild()`. At resolution the LLM does two things, once, offline, logged as
cited/versioned records the deterministic rebuild then consumes:

1. **Proposes candidate pairs** (a recall aid into candidate-gen) — and proposes alias / normalizer rules.
   Every proposal is cited to `claim_ids` + model/version.
2. **Raise-only merge signal** — the LLM may *lift a weak pair into the HITL band* so a human sees it, but
   **it can never push a pair across the ≥0.85 auto-merge line**: auto-merge must be reachable by the
   deterministic terms alone. The LLM does **not** emit a relational score (relational is the fixpoint's
   job) and traverses only the **evidence-layer claim graph + the previous frozen view**, never the
   in-progress rebuild.

The deterministic authority — `merge_score`, the bands, clustering, the fixpoint — always disposes.

**Selective invocation (the LLM must earn its place — it's offline, so cost is build tokens + candidate
noise, both gated by a deterministic pre-filter).** Fire the LLM candidate-gen only on entities that are
**(i) a high-alias-risk type** (variant / component / unit / manufacturer — configurable) **and (ii)
orphan / thin-block** (`deterministic_candidate_count < k`). One batched call per orphan over its block;
cap by a config budget; log skips. This is ≈ #orphan-risky-entities, not O(n²). For the demo, deterministic
blocking + the seeded alias table cover the *known* traps; the LLM path is shown recovering **one planted
alias not in the seeded table** (an orphan component) — the adaptation/recall story. Everything past that
one instance is design-note.

### Analyst-defined rubric logic needs an LLM
Where merge logic is genuinely qualitative (an analyst-authored rubric for "are these two systems the
same"), that rubric is executed by the LLM proposer above — cited, logged, raise-only — not baked into the
deterministic terms. The numeric `merge_score` stays the authority.

---

## Open questions
- **Blocking / candidate generation** — a **configurable attribute soft-filter** that encodes the initial
  search an analyst would run over a corpus (name + attribute similarity keys); **entity-type-dependent**
  (the useful keys differ per type). Configure a few cases suitable for C progressively, not
  exploratorily. Its goal is **max recall** (propose everything worth checking); precision is the merge
  decision's job. The LLM candidate-gen (above) supplements it on the selective orphan/thin-block gate.
  All-pairs-within-block is fine at demo scale.
- **Threshold values** — the high/low band cutoffs. Pick defensible defaults; make configurable; tune
  from HITL decisions over time.
- **Merge representation** — store merges as reversible (a "same-as" edge in the knowledge layer) rather
  than destructive node-collapse, so an analyst can split later. **Decided: reversible.**
- **Transliteration handling** — **rule-based normaliser + a seeded alias table**, with the LLM allowed
  only to *propose* new alias rules (cited, logged, human/deterministic-gated), never to decide merges.
  C needs Triumf/Triumph/Триумф and Hongqi/红旗/紅旗 (see `../md/05-data-scoping-C.md` §4).

## Research directions
- **Collective / relational ER literature** — techniques where resolving one pair informs others
  (relationship-aware ER, graph-based dedup). Candidate research task.
- **IAF/OSINT tradecraft** — what disambiguates units/formations/platforms in practice (designators,
  garrison, equipment fingerprint). Feeds the materiality work in `../C/01-materiality-ontology.md`.
