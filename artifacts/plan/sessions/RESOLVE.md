# Session RESOLVE — Iterative Relational Entity Resolution

**Wave 1 · depends on F0 (merged) only · offline LLM (proposer).**
Read `../00-master-plan.md` §4.2 (records — `resolved_ref`, the `same-as`/`distinct-from` + `merge_confidence`
carriers, the `merge_proposal`/`merge_adjudication` decision records), §4.3 (the `resolve()` stage signature
+ fixed rebuild order), §4.4 (config store — every knob read through it), and §5 (gates G1/G2/G5/G6/G10 you
must keep green). This session implements exactly the `resolution` stage of `rebuild()` — nothing more. It is
**C's marquee graded feature** (`spine/03`): confidently fusing "Factory 404" = a chassis in a photo into one
node across transliterations and shell aliases, *while keeping the traps apart*.

## Goal

Fill F0's `resolution` stub with the **pure, deterministic** iterative relational resolver: deterministic
candidate-gen (with an offline raise-only LLM proposer feeding it), a stored-breakdown `merge_score`, the
bootstrap→relational-fixpoint collective ER, reversible `same-as`/`distinct-from`, a replay-derived alias
table, and location resolution reusing the same machinery over `config/places.yaml`. Precision-first merge;
recall lives at candidate-gen + iteration + HITL. The whole thing runs inside `rebuild()` as a pure function
of (evidence log, decision log, config) — no LLM, network, clock, or RNG on the rebuild path.

## Design docs to read first
`spine/03` (the full resolution design — iterative/relational, bands + HITL middle, precision-first, two
scores, alias-table learning, proposer-not-authority, selective invocation) · `spine/08` §3.9 (resolution
scoring, `merge_score`, bands, blocking keys, traps engineered into the middle band) + §3.11 (LLM
proposer-vs-authority, the raise-only red-team patch, selective-invocation pre-filter) · `md/13`
(location-normalization — coord-canonicaliser + place-resolution as the resolution layer with a geodesic term;
the Karachi-Port ≠ Port-Qasim trap; the withheld "Chaklala" alias) · `md/05` §4 (alias ground truth — the
seeded transliteration/alias tables, FD-2000 ≠ FT-2000, HT-233 radar-vs-system) · `C/01`
(same-as/distinct-from edges; the HQ-9/P vs HQ-9BE flagship + FD-2000 vs FT-2000 secondary cases) ·
`config/places.yaml` (the seed gazetteer + proximity radii + the two withheld forms) · `DECISIONS.md` rows on
iterative-collective-ER-precision-first, two-scores-never-averaged, LLM-proposer-never-authority, and
location-normalization.

## Scope (build these)

1. **Deterministic resolver core** — fill `resolve(claims, config, prev_view) -> Partition` (master §4.3):
   `resolved_ref` per claim + `same-as` edges (each carrying `merge_confidence` + the score breakdown) +
   `distinct-from` edges. Pure: **no `anthropic`/`httpx`/network/clock/RNG import on the rebuild path** (G1);
   byte-deterministic given a fixed processing order + replayed decisions (G2). Merges are **reversible**
   (`same-as` edges in the knowledge layer), never destructive node-collapse.
2. **Candidate generation (the recall job).** (a) Deterministic **blocking keys** = *type + country/domain
   namespace + name token* (keys are config; all-pairs-within-block is fine at demo scale). (b) Consume the
   frozen LLM candidate-proposal records from §5. Candidate-gen's goal is **max recall — propose every pair
   worth checking**; the merge decision (below) is where precision lives.
3. **`merge_score` + bands.** `merge_score = 0.30·attribute + 0.40·relational + 0.15·temporal_consistency +
   0.15·source_asserted`; **store the full breakdown** on the `same-as` edge (explainability). Bands from
   config: **auto-merge ≥ 0.85 · HITL 0.55–0.85 · keep-separate < 0.55**. `source_asserted` is an **identity**
   signal (a merge a credible source explicitly asserts), *not* `claim_credibility` — never blended into truth
   (G5, two-scores-never-averaged).
4. **Two-phase iterative collective ER.** *Bootstrap pass* — merge only on shared hard ID / exact-strong
   attribute+name, **no relational term** → initial partition. *Relational fixpoint pass* — recompute
   `merge_score` with the `0.40·relational` (shared-neighbourhood) term over the current partition,
   auto-merge/HITL/separate, and **iterate until a full pass fires no new auto-merge**. Terminates because
   merges are **monotone** (clusters only grow within a rebuild). **Precision-first:** a plausible-but-wrong
   pair lands in HITL, never auto-merges; lost recall is recovered by iteration + HITL, **never by loosening
   the threshold**.
5. **LLM proposer — offline, raise-only, gated.** A candidate/alias-rule proposer that: (i) runs **offline,
   upstream of rebuild**, emits cited + model/versioned **frozen `merge_proposal` records**, and is kept
   **out of the rebuild import closure** so G1 stays green (mirrors INGEST's upstream-LLM pattern — reconcile
   the exact placement with F0's G1 import-boundary check; a small F0-amendment if the gate bans `anthropic`
   directory-wide rather than by rebuild-reachability); (ii) traverses **only the evidence-layer claim graph +
   the previous frozen view**, never the in-progress rebuild; (iii) emits **no relational score** (relational
   is the fixpoint's job); (iv) is **RAISE-ONLY** — may lift a weak pair *into* the HITL band, but a raised
   pair is **hard-clamped below 0.85**: auto-merge is reachable by the deterministic terms alone. Gated by a
   deterministic **pre-filter**: fire only on high-alias-risk types **{variant, component, unit,
   manufacturer}** AND orphan/thin-block (`deterministic_candidate_count < k`); one batched call per orphan;
   **budget cap; log skips**. Demo target: recover **one planted alias not in the seed** (an orphan component).
6. **`same-as` / `distinct-from` + alias table (learning).** `distinct-from` = explicit do-not-merge, enforced
   as a **hard veto** before any band decision (carries HQ-9/P vs HQ-9BE and Karachi-Port vs Port-Qasim). The
   **alias table is DERIVED STATE**, not a stored table: *seeded aliases (config, `md/05` §4)* ∪ *aliases
   replayed from decision-log `merge_adjudication` (accept) records* — so "the same pair auto-resolves next
   time" **falls out of replay**.
7. **Transliteration normalizer.** Deterministic rule-based normalizer + the seeded alias table
   (Triumf/Triumph/Триумф; Hongqi/红旗/紅旗 — `md/05` §4). Rules + seed are **config**; no learned model; the
   LLM may only *propose* new rules (raise-only, §5).
8. **Location resolution (reuses this machinery — not a new subsystem).** *Coord-canonicalisation + geocoding
   are INGEST's, done at extraction* (master §4.2): the canonical WGS84 coords + `geocode_candidates` are
   **already frozen onto the claim** — RESOLVE **consumes** them, it does not geocode/canonicalise (keeps
   `rebuild()` network-free, **G1**). RESOLVE's job is **place resolution over `config/places.yaml`** — the
   attribute term reads toponym/alias match **+ geodesic proximity** (per-`precision_class` radii from the
   gazetteer) over those frozen coords, fed through the **same** `merge_score`/bands. Keep the **Karachi-Port
   ≠ Port-Qasim** distinct-from trap distinct;
   ambiguous parent-city "Karachi" resolves to the metro (or HITL), not to either terminal. The **withheld
   "Chaklala" alias** is *earned* via ICAO `OPRN` co-reference + geodesic proximity (or an LLM alias proposal →
   HITL), then carried by the replay-derived alias table.
9. **Route the mid-band to HITL (seam only).** 0.55–0.85 pairs emit a **review-queue merge item** (envelope
   per master §4.7) for the HITL service to adjudicate. RESOLVE *produces* the item and *replays* the
   resulting adjudication; it does **not** build the review UI or the writeback (HITL owns those).

## Contracts implemented
Master **§4.3** (the `resolve()` signature + its fixed slot in the rebuild order), **§4.2** (`resolved_ref` as
the match target; `same-as`/`distinct-from` edges + `merge_confidence`; `merge_proposal` and
`merge_adjudication` decision records), **§4.4** + `config/places.yaml` (every merge weight, band, blocking
key, high-alias-risk type set, orphan-`k`, LLM budget, transliteration rule, alias seed, and proximity radius
is read through F0's live config store — **no code constants, G6**; the resolution config *section* is DATA-C
content — if F0's frozen config models lack a `resolution` schema, add it via a small **F0-amendment** per
master §2 Rule 3, don't inline literals). Gates: **G1** (rebuild purity), **G2** (determinism), **G5**
(two-scores separation), **G6** (no magic numbers), **G10** (subject-as-lens: the resolver takes subject/config
as a param, no per-subject table).

## Acceptance criteria
- [ ] **FD-2000 / FT-2000** lands in the **mid HITL band** (high attribute similarity, conflicting relational
      evidence) — neither auto-merged nor kept-separate.
- [ ] **HQ-9/P vs HQ-9BE** held apart by an explicit **`distinct-from`** (never merges despite high attribute
      similarity across the source base).
- [ ] **FD-2000 ↔ HQ-9/P auto-merges** (marketing-name alias; deterministic terms reach ≥ 0.85).
- [ ] The **relational fixpoint terminates** — a full pass adding no new auto-merge is the fixed point; the
      monotone-merge (clusters only grow) property is asserted.
- [ ] **Property test:** a maximal LLM **raise-only** signal on the FD-2000/FT-2000 trap **cannot push it
      across 0.85** (stays in the HITL band) — auto-merge is reachable by the deterministic terms alone.
- [ ] **Alias table grows from the log:** appending a `merge_adjudication` (accept) makes the same pair
      **auto-resolve on the next `rebuild()` with no HITL** (replay-derived learning).
- [ ] **Karachi-Port (Keamari) ≠ Port-Qasim (Bin Qasim)** stays distinct (~35 km; `distinct-from` + proximity);
      bare "Karachi" resolves to the metro/HITL, not either terminal.
- [ ] The **withheld "Chaklala" alias resolves to `pl_nurkhan`** after the earned merge; once adjudicated, the
      alias table carries it.
- [ ] Place-resolution matches the **frozen canonical WGS84 coords + toponyms** (produced by INGEST at
      extraction) to gazetteer nodes deterministically, via toponym match + geodesic proximity through
      `merge_score`/bands — RESOLVE does **not** geocode or canonicalise (that is INGEST's, §4.2).
- [ ] **G1/G2/G5/G6/G10** green; **all LLM-touching tests use recorded/mocked transcripts** (offline +
      deterministic — `respx`/fixture); `ruff`/`mypy`/`pytest` green.

## Owned paths (nothing else)
`chanakya/resolve/**`, `tests/resolve/**`. **Depends on:** F0 (merged). **LLM:** offline — the candidate/alias
proposer only; the pure resolver on the rebuild path is LLM-free.

## Out of scope
The **credibility/status arithmetic** — `claim_credibility`, `assertion_confidence`, status machine, freshness
(that's **SCORE**; RESOLVE emits only `merge_confidence`, an identity number, never truth). The **merge review
UI + decision-log writeback** (that's **HITL**) — RESOLVE only *emits* the 0.55–0.85 review-queue item and
*replays* the resulting adjudication. Claim **extraction** (INGEST). Config **content authoring** — the alias
seed, merge weights, and any `places.yaml` extensions are DATA-C's (RESOLVE consumes them through the store).

## Worktree lifecycle
`git worktree add ../wt-RESOLVE -b feat/resolve` → implement e2e inside owned paths → PR `[RESOLVE]` → **you
review & merge** → you update `PROGRESS.md` → `git worktree remove ../wt-RESOLVE`. Starts only after F0 is on
`main`; conflict-free with sibling Wave-1 sessions (disjoint ownership → clean rebase, any merge order).
