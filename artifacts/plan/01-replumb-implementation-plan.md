# Chanakya OSINT — Identity Re-key & Type/Instance Replumb (IMPLEMENTATION PLAN)

**What this is.** The build plan for the substrate rework designed in `../spine/13-type-instance-and-identity-replumb.md`
(realizing D1–D3 of `../spine/10-resolution-real-world-redesign.md`). spine/13 is the *what* and *why* — the
decisions D-13.1…D-13.16, verified against code and aligned across three design sessions. This document is the
*how* and *in what order*: the staged migration decomposed into commit-sized sessions, the frozen-contract
amendments, the new gates, the three-hands verification, and the extractor-model bake-off. It is written to be
read alongside `00-master-plan.md` (the backend master), whose contracts this plan **amends** rather than
restates.

**How to read it.** §0–§5 are the coordination floor (scope, the invariants, the migration DAG, concurrency,
contract amendments, gates). §6 is the operating procedure for running any one stage (read-first → three opus
subagents → verify → handoff) — it makes the plan self-sufficient. §7 is the meat — each migration stage as a
session-style spec you can hand to an implementer. §8 is the extractor-model bake-off. §9–§11 are verification,
data/rollback, and the open items closed by the spike. §12 is handoff & progress. **Appendix A** is the code
reference index every stage's "Read first" line cites. Per repo idiom, contracts are stated once and cited by
number; each stage's session file (`sessions/RK-*.md`, spun out when the stage starts) stays thin and points
back here.

**The non-negotiable, carried into every stage.** Where evidence is absent/ambiguous/contradictory the running
system returns an explicit "insufficient evidence," names the gap, and escalates — never fabricates. The replumb
*strengthens* this (individuated instances let us say *whose* dependency is missing) and must never weaken it.
A stage that could unground or fabricate an assessment does not ship.

**This is post-deadline, multi-week substrate work — the real-system build, not a demo fix.** There is no
wall-clock pressure to jam it in; correctness and reversibility win over speed. Re-extraction is free (data is
rebuilt in parallel), so we choose target-correct designs and let the corpus/answer-key/golden regenerate to
match (working-principles #1/#3).

---

## 0. Scope

**In scope (this plan):**
- The four-stage migration of spine/13 §12: mint atoms at ingest (S1) → layer typing + endpoint materialization
  + presence/formation citizens + basing-as-a-rebuild-derived-edge (S2) → per-document coref-cluster minting,
  Tiers 0/1, the per-layer identity policy + the co-location cap + the relationship-conflict wall (S3) → cut the
  name-key + re-anchor the decision log, observables, and lens anchors (S4).
- The **design spike** that closes the open micro-decisions and prototypes the highest-risk piece (S0).
- The **extractor-model bake-off** (Gemini vs Opus 4.8 vs GPT), contract-first, with the scoring harness the repo
  does not yet have (§8).
- The **two-layer operator-scoped chokepoint** rework (spine/13 §9), which can only follow S3.
- The **data regeneration** sequencing (§10), which runs in parallel with code once contracts freeze.

**Out of scope (deliberately deferred):**
- **Location containment / query-time proximity** ("near Rawalpindi" lending graded support to a Nur-Khan query)
  — D-13.16, roadmap. Purely additive (place-to-place edges + one query tool); forces no rework here. The
  precision-honest refusal already works (a `Location` carries `precision_class`), so the non-negotiable half
  needs nothing.
- **Scale / incremental rebuild** — D12 of spine/10; the re-key keeps pure-recompute semantics so this stays a
  later, drop-in optimization.
- Any B (intent / I&W) capability.

---

## 1. Invariants — what the replumb changes, and what it must NOT

**Changed (the substrate itself):**
- Identity stops being `type+name`. Today it is minted as a name-derived string in *three* code paths and
  collapses in *two* stacked lanes (an exact-string dict-key collision at profile build, and an
  exact-normalized-name auto-merge at confidence 1.0 in the resolver bootstrap). Both go; identity becomes an
  earned partition over immutable **atoms**.
- The instance layer gains two citizens — **presence** (equipment observed at a site; the workhorse) and
  **formation** (the named organizational unit; earned) — naming and elevating the existing `observed-at` /
  `based-at` edge split.
- Node ids become a deterministic function of atom membership (not names), with a rebuild-emitted old→new
  redirect map.

**Preserved (do not break):**
- **G1 rebuild-purity / G2 determinism.** No LLM/network/clock/RNG in `rebuild()`; two rebuilds byte-identical;
  hash-seed-independent. Note: these gates run against the *abstract golden fixture* (`comp_gizmo`/`mfr_foundry`/…),
  **not** the corpus — so a corpus *data* re-key cannot break them. (A5 does change `rebuild()`'s id-derivation
  *code*, which runs over the golden too and regenerates its committed output at S4 — see §9. The determinism/purity
  *semantics* are what the gates guard, and those survive.)
- **The bi-level rule: `rebuild()` never writes evidence.** The knowledge layer is a pure function of the
  append-only logs; nothing under `rebuild()` mints an atom or appends a claim. The basing derivation moving into
  rebuild (S2) becomes a **pure derived-layer edge** — it mints no claim and appends nothing (see G17), so it is a
  knowledge-layer derivation exactly like `resolve`/`score`. The old "no LLM, so G1-safe" rationale answered a
  non-risk (basing never had an LLM); the real invariants it must honor are **G17 (no rebuild-time minting)** and
  this bi-level rule.
- **The non-negotiable** (anti-fabrication) and the **extract-raw guardrail** (extract only *stated* claims;
  never resolve/normalize the unstated).
- **Pure-recompute semantics (D12).** Reversal is always "append evidence / a decision, then recompute," never
  in-place mutation. Atoms are append-only; the knowledge layer re-forms every rebuild.
- **KEYLESS ≡ LIVE.** The keyless boot appends frozen bundles that equal what a live re-extract would produce.
  The re-key changes what the bundles *contain* (new atom ids, new contract), but the equivalence must hold after
  regeneration — and (§8) the selected extractor must be live-runnable in the shipped image, else the invariant
  is not actually restored.

---

## 2. Migration DAG & build order

Eight sessions (the bake-off is one session run in two phases). The core chain **S1 → S2 → S3 → S4** is strict (each stage's substrate is the next's input);
S0 and the bake-off open the work; materiality and data-regen hang off the chain where noted.

| ID | Session | Wave | Depends on (merged) | Runs | Owns (top-level) |
|---|---|---|---|---|---|
| **RK-SPIKE** | Design spike: close micro-decisions + prototype characterize-and-cluster | 0 | — | throwaway branch | `tmp/` prototypes + doc updates only |
| **RK-BAKEOFF** | Extractor-model bake-off + the scoring harness (Wave-0 screen + post-S1/S3 definitive pass) | 0 / post-S1+S3 | RK-SPIKE gold slice (screen); RK-ATOMS + RK-COREF (definitive) | offline | `backend/eval/extraction/**` (greenfield), a new `ExtractionClient` impl; a production winner's client → `chanakya/ingest` |
| **RK-ATOMS** | S1 — claim atom + referent field (dormant) + atom-aware dedup + A7 discriminator schema (non-breaking) | 1 | RK-SPIKE | offline+live | `schemas/{claim,ids,config_models}.py` (amend), `ingest/**` mint/remap sites |
| **RK-LAYER** | S2 — layer typing + endpoint materialization + presence/formation + basing-as-rebuild-edge (flagged) | 2 | RK-ATOMS | offline | `config/ontology.yaml`, `ontology.py`, `schemas/config_models.py`, `view/pipeline.py`, `resolve/__init__.py` (endpoint-layer typing; contended), `ingest/basing.py` |
| **RK-COREF** | S3 — coref-cluster minting (Tiers 0/1) + per-layer policy + co-location cap + relationship-conflict wall | 3 | RK-LAYER | offline | `ingest/coref.py`, `resolve/{__init__,cluster,rconfig}.py` |
| **RK-NAMECUT** | S4 — cut the name-key + re-anchor decisions to atoms & config anchors to stable handles + golden regen | 4 | RK-COREF | offline | `resolve/{entities,aliases,__init__,cluster}.py`, `view/pipeline.py`, `hitl/**`, `schemas/stage_io.py`, `tests/fixtures/golden/**` |
| **RK-MATERIALITY** | Two-layer operator-scoped chokepoints (spine/13 §9) | 4 | RK-COREF | offline | `materiality/precompute.py` |
| **RK-DATA** | Corpus/answer-key/golden regeneration + coverage additions | 2–4 | contract-freeze per stage | data hand | `corpus/**`, `config/{entities,observables,subjects}.yaml`, `answer_key.json` |

**Recommended order.** RK-SPIKE first (it closes the design opens the rest assume). **RK-BAKEOFF runs in two
phases:** a Wave-0 substrate-independent screen concurrent with the early chain, then a *definitive* pass after
RK-ATOMS (discriminator schema) and RK-COREF (coref) — it is **not** fully independent of the chain, because its
top-weighted criteria depend on those stages' work (see §8). Both phases finish **before RK-DATA's full regen**,
since the chosen model regenerates the corpus. The code chain S1→S2→S3→S4 does not wait on the bake-off's *verdict*
(the chain's own logic is model-agnostic), but the bake-off waits on the chain for its definitive criteria.
RK-MATERIALITY starts after S3 (it needs individuated instances). RK-DATA runs in parallel with the code stages,
regenerating against each stage's frozen contract, and gates the final cutover.

**Dependency notes.** The chain is strict because: S2's layer routing needs S1's atoms to route; S3's cluster
minting needs S2's layer/endpoint machinery; S4's name-key cut needs S3's earned clusters to replace the name as
the address. **F8 caveat (load-bearing):** S2 landing *before* S3 produces per-mention provisional instances —
known, transient fragmentation. **Fragmentation metrics are meaningless until S3 lands and must never be "fixed"
by loosening merge thresholds** (they would be far too loose once coref clustering arrives). Every stage lands
behind a flag and dual-runs old-vs-new before its cutover.

---

## 3. Concurrency & file-ownership

Unlike the backend's Wave-1 (disjoint-ownership, fully parallel), this migration is **mostly serial** because
its heaviest files are contended across stages. The concurrency rule here is *temporal*, not spatial: a contended
file is owned end-to-end by one stage at a time, in DAG order.

**Contended files — owned sequentially, never parallel:**
1. **`view/pipeline.py`** (`rebuild()` / `_assemble`) — S2 (straddle split, endpoint materialization, basing edge
   materialized in-rebuild), S3 (Tier-0/1 grouping consumed), S4 (`to_canonical`, name fallback removal, decision
   re-anchor, redirect-map emission). The single most contended file.
2. **`resolve/__init__.py`** — S2 (endpoint layer typing), S3 (`_coref_pairs` promotion, provisional-instance
   clustering, relationship wall), S4 (name-key cut in `_matching_eids`/`_link_endpoints`/`_to_partition`).
3. **`resolve/cluster.py`** — S3 (per-layer policy, co-location cap, Tier-1 same-doc, relationship-conflict wall)
   then S4 (kill the name-verdict bootstrap).
4. **`resolve/entities.py`** — S4 only (kill `ent:type:name`; thread the atom into `Edge`/`Entity` as the name-key
   is cut). S1 touches only `schemas/` + `ingest/` per its owned paths — no atom threading into `entities.py` yet.
5. **`schemas/{claim,stage_io}.py`** — bracket the migration (`claim` amended at S1, `stage_io` at S4).
   (`config/ontology.yaml` is single-owner S2/RK-LAYER — not contended.)
6. **`schemas/config_models.py`** — S1 (restructure `TypeDef.attrs` from `list[str]` to structured entries, for
   A7's discriminator declarations) then S2 (add the per-attribute `layer` field, for A2). Same field, two stages,
   strict serial.
7. **`config/observables.yaml`**, **`config/subjects.yaml`** — S4 (RK-NAMECUT does the *key-format* re-anchor:
   analyst-facing references to atoms, config anchors to stable handles) then RK-DATA (regenerates *content* on
   rebase). Added here because §7 (RK-NAMECUT) and RK-DATA both edit them; serialized like the other contended files.

**Genuinely parallel / low-contention:** `view/coverage.py` (S3 reporting, reads only), `materiality/precompute.py`
(RK-MATERIALITY, distinct concern), `resolve/aliases.py` (self-contained once the indirection contract is fixed),
and the RK-BAKEOFF harness (`backend/eval/extraction/**`, a new file tree that touches nothing existing).

**Amendment protocol.** Because this rework *changes* frozen contracts (schemas, identity, Partition keys), every
such change is an **F0-amendment**: a small contract PR that lands first, is logged in **both** `PROGRESS.md` and
`DECISIONS.md`, and that dependents pick up on rebase. §4 lists them.

---

## 4. Frozen-contract amendments (the shared reference this plan introduces)

Each is an F0-amendment against `00-master-plan.md` §4. Stated once here; cited by number from the stage sessions.

- **A1 — two atom levels: the claim atom and the referent atom (amends master §4.2 record schema).**
  - **Claim atom** = the per-mention bedrock = the **post-dedup `claim_id`** (canonicalised in
    `dedup.assign_claim_ids`, not at construction). S1 formalizes it as the stable addressing bedrock; no new id is
    minted — this names and freezes what already exists.
  - **Referent atom** = an immutable, opaque, identity-blind **referent id**, one per **document-local
    coreference cluster**, minted at ingest **in S3** (when coref becomes a required tier) — **not** in S1, because
    coref is off in S1 so there is no cluster grain yet. The field is added to `ClaimRecord` in S1 as
    **optional, default `None`** (so `extra="forbid"` fixtures still load and S1 stays non-breaking) and is populated
    only from S3. `make_referent_id` lives beside `make_claim_id` in `schemas/ids.py`.
  **A knowledge node (S4) is a derived grouping of CLAIM atoms; the referent atom is a grouping *signal* the
  rebuild consults — never the address of the node.** (Corrected 2026-07-25 per **D-13.18** and the review
  verdict: the earlier wording made the referent atom the grouping unit, which — with "atoms never split" —
  makes an intra-document over-bind **permanent** and is disqualifying. Claim-atom-primary is what keeps
  spine/13 §4's "challengeable proposal" true: the rebuild may **decline** a referent grouping and de-group to
  claim-atom granularity, raising for an analyst. No atom splits; the grouping declines.) Nothing re-mints
  (D-13.11's mint-once holds). `resolved_ref` stays the *derived* pointer. `Record` is `extra="forbid"`, so the
  optional field is a real schema amendment, not a loose add. (Realizes D-13.7/D-13.11/**D-13.18**; claim atom
  **S1**, referent atom **S3**.)
- **A2 — layer as a type property (amends the ontology contract + the config schema).** Every `node_type` **and**
  every `attribute_type` in `config/ontology.yaml` gains a `layer` tag (design | instance). This builds on the
  **structured `TypeDef.attrs`** that **S1** already introduces for A7 (converting `schemas/config_models.py`'s bare
  `list[str]` to structured entries): A2/S2 adds only the per-attribute **`layer`** field to that same structured
  entry — same field, two stages, strict serial (§3). The `ontology.py` layer accessor reads it. Edge
  endpoint-layers derive from the already-declared `from`/`to`. The per-*attribute* layer is the non-obvious piece:
  an instance-layer attribute on a design-layer node is the **straddle-split trigger** (it signals a lumped mention).
  **Dual-attribute-split sub-rule (D-13.3):** a genuinely dual-natured attribute (a design's nominal range vs a
  deployment's effective range) is **split into two attribute-types**, one per layer — not made contextual. (D-13.3; S2.)
- **A3 — presence & formation as instance citizens (amends the node model).** Two instance node kinds:
  **presence** (from `observed-at`; equipment at a site; `count` is a *sourced attribute*, default unknown, never
  `= reports merged`) and **formation** (from `based-at`; the named unit; earned). based-at has two provenance
  paths — *stated* (extractor-emitted, normal credibility, can confirm) and *derived* (`observed-at` +
  `inducted-into`, capped inference). (D-13.13/D-13.14; S2/S3.)
- **A4 — endpoint identity resolved at rebuild (amends the `rebuild()` stage contract).** Edge endpoint *layer*
  is static (ontology); endpoint *identity* is resolved and materialized at rebuild, never per-query, never baked
  into the immutable claim. An instance-layer edge materializes the instance it implies; a cross-layer holding
  edge does not. (D-13.6; S2.)
- **A5 — node id from atoms, name becomes a label (amends master §4.2 + the id namespace).** Canonical id =
  deterministic function of member atoms, computed **after** grouping — **keyed on the member CLAIM atoms**
  (min member `claim_id`, or a unique identifier when the cluster has one). *(Corrected 2026-07-25 per D-13.18
  and the review verdict: the earlier wording keyed on the referent atom with the claim atom only as a
  "fallback" — the inverted ordering. Claim-atom-primary is not a fallback, it is the rule: the referent atom
  is a grouping signal, and a node whose id keyed on it could not survive the rebuild **declining** that
  grouping.)* A referent atom may still be *recorded* on the node as the signal that produced its grouping; it
  is never the address. The human label ("HQ-9/P (PAF, Rahwali)") is *derived*. `rebuild()` emits an old→new
  redirect map. (D-13.11/**D-13.18**; S4.)
- **A6 — analyst decisions key on atoms; human-authored config anchors stay on stable handles (amends master §4.7
  HITL + §4.4 config).** Two distinct cases:
  - **Analyst decisions** — merge accept/reject/split and status/integrity overrides — key on **claim/referent
    atom ids**. An atom→current-node index is threaded into `apply_decision_effects` and the `controlpoints` replay;
    replay **fails loudly** on a dangling atom reference (replacing today's silent skip). Analyst authority must not
    degrade to a hint.
  - **Human-authored config anchors** — `config/observables.yaml` watch-lists and `config/subjects.yaml` lens
    anchors — stay on **stable handles**: registry entity ids or names resolved through `resolve/anchor.py`'s
    existing string→node ladder, **NOT** the drifting min-member node id (which changes every regen).
  "Fail loudly on dangling" scopes to **analyst decisions only**; applying it to config anchors would break
  lenses/observables on every re-key — the opposite of durability. (Realizes **D-13.15 as amended** — the
  config-anchor carve-out is a design amendment logged this session; atom-keying a human-authored watch-list over a
  whole cluster has no natural atom. S4.)
- **A7 — the extractor contract, in two parts (amends master §4.2 / the INGEST contract).**
  - **Structured discriminators** (operator, geography, unit designation, time) are emitted as **structured claim
    context**, not buried in the untyped `attrs` bag. This needs new fields on the `extract.py` mention schemas plus
    the `config_models.py` structured-attrs representation they are declared against — a schema deliverable of
    **RK-ATOMS (S1)**, which already amends schemas.
  - **Within-document coreference handles** are emitted, promoting the built-but-off coref pass to a required tier
    — a deliverable of **RK-COREF (S3)**.
  `kind` stays a *hint* the build may override. All fields **optional** — absence is `unknown`, never fabricated.
  The bake-off (§8) measures discriminator capture only after S1 and coref binding only after S3. (§10 of spine/13.)

---

## 5. Gates (extends master §5's G1–G12)

The architecture is enforced by tests, not prose. Each new gate gets an **abstract fixture** (corpus-independent,
like G1/G2) so it is immune to the re-key's data churn. New rows:

| Gate | Checks | Catches (violation signature) |
|---|---|---|
| **G13 no-name-as-address** | After S4: `ent:{type}:{name}` construction is absent from `resolve/`+`view/`; identity flows through atom→entity indirection; edge endpoints are atom handles, not raw designator strings. **Event mints stay per-claim** (`event:{claim_id}`) and are exempt; the scan must **anchor on the opening quote / word boundary** (match `"ent:` / `f"ent:`, which never occurs inside `"event:`) so event mints are excluded by construction, not false-flagged | a name-derived address (either stacked lane) sneaking back |
| **G14 decision-durability** | A recorded analyst decision (merge accept/reject, status override) re-applies correctly after a simulated wholesale re-key on the abstract fixture; a dangling *decision* reference raises, never silently no-ops | the silent decision drop (today's `idx.get(elid)` skip); analyst authority degrading to a hint |
| **G15 presence-not-fused** | An `observed-at` equipment sighting never becomes a `based-at` formation basing without organizational evidence (`inducted-into` or a stated formation); the two citizens stay distinct | the imagery-lane conflation returning; kit-photographed-here → formation-stationed-here |
| **G16 co-location-cap** | Two instances sharing only design+site+operator cannot reach `confirmed` formation-merge without a unit-level discriminator; they may reach presence-merge | OOB undercount by fusing two batteries into one unit on co-location |
| **G17 atom-immutability** | Atoms are minted only at ingest and never inside `rebuild()`; **no code path under `rebuild()` calls `make_claim_id` or `store.append`** (the basing derivation must be a pure edge, not a minted claim); node ids derive deterministically from atom membership; two rebuilds yield identical ids (extends G2). *Phasing:* the no-mint/no-append clause binds from **S2**, the id-from-atoms/determinism clause from **S4** (A5). *Fixture must be non-vacuous:* include an `observed-at`+`inducted-into` premise pair so the derived-basing branch actually executes under `rebuild()` (else it passes vacuously), or use an input-independent static call-graph scan of rebuild-reachable modules for `make_claim_id(`/`store.append` | rebuild-time minting or evidence-writing; basing minting a claim inside rebuild; a random/nondeterministic id breaking pure-recompute |
| **G18 relationship-conflict-wall** | A **stated** `based-at`/`operated-by` conflict at overlapping times **within the same `site_type`** (**C1**) **hard-walls** a merge (never overridable by a relational score); value normalization (PAF ≡ "Pakistan Air Force") fires before the wall is tested, and an **unnormalizable** stated value yields the third state — no wall *and* no fusion, plus a named gap (**C7**). The gate must **name the wall channel** and assert an **analyst-visible reason** (§5a) | two units at different sites at overlapping times fusing into one; the operator-conflict wall not firing because normalization didn't run; a wall built the geo-veto way (non-transitive **and** unreported) while the gate passes; a differing `site_type` mis-read as a conflict |
| **G19 cross-namespace-non-fusion** | Two instances in incompatible namespaces (a PLA-side and a PAF-side unit) **cannot fuse** — in the Phase-2 fuzzy fixpoint **and** in the Phase-1 bootstrap. Covers the alias branch: `AliasIndex` equivalence must be **non-reflexive** (a real alias link) and the alias branch must be **type- and namespace-gated**, else the namespace-gated exact-name branch is never reached | the single most dangerous over-merge class for an operator-scoped OOB map (D4); cross-**type** fusion through the same alias hole; a remedy that gates only the Phase-2 loop and leaves bootstrap open |

**G6 no-magic-numbers still binds:** the co-location cap threshold, the per-layer merge floors, the coref
auto-bind threshold, the relationship-wall's overlap window, and any discriminator-priority weights live in
`config/`, never as code literals.

### 5a. Gate amendments forced by RK-SPIKE (2026-07-24)

RK-SPIKE verified ten substrate defects (`../../tmp/conv/rk-spike-verified-defects.md`) and found that **three
of the gates above would pass while the harm they name is realized.** A gate that cannot fail is a gate that
lies. These amendments are **mandatory** for the stages that own them; the register carries the `file:line`
evidence for each.

| Gate | Defect | Required amendment |
|---|---|---|
| **G15** presence-not-fused | **D2** | As written it **passes vacuously** — `basing.find_candidates` already skips when no formation link exists (`ingest/basing.py:296-300`), so the asserted behaviour is *current* behaviour. Keep it as a regression guard and **add the clause that bites**: an **ambiguous or truncated formation attribution must produce a named gap**. Today `formations[:max_units]` (`basing.py:301`, `max_units_per_site: 1`) silently discards a second candidate formation while **every other rejection path appends a `SkipRecord`** — an order-of-battle undercount with **no merge involved**, which is why neither G15 nor G16 can currently see it. *Two candidate formations ⇒ two attributions, or one plus an explicit named gap. Never a silent pick.* (Requirement on **S2's replacement**, since the pass itself is deleted — §7 RK-LAYER item 4.) |
| **G16** co-location-cap | **D1, D3** | **Add the D1 clause: assert the absence of a derived `supersedes` / drawn relocation edge**, not merely the absence of a confirmed merge. `based-at` is FUNCTIONAL and keyed on the unit alone (`config/ontology.yaml:146`, `instance_key: [from]`), so fusing two co-located batteries makes their two sites one unit's before/after; `promote_supersessions` (`credibility/supersession.py:165-209`, called at `view/pipeline.py:795`) then promotes it, **pops the pair out of the analyst's queue** ("adjudicated by the machine — no longer a question for the analyst") and **draws** the edge when the targets differ. An identity error therefore becomes a **fabricated movement assessment with the human removed** — the non-negotiable breached structurally. Without this clause G16 goes green one stage upstream of the harm. **Also add the D3 clause:** a name-only pair must not **fuse** at *any* configured floor, including `auto_merge_by_type` overrides. |
| **G18** relationship-conflict-wall | **D7** | Two holes. (i) **`operated-by` does not exist** as a predicate anywhere in `config/ontology.yaml` — **now assigned to RK-LAYER/S2**, which owns that file (§7 RK-LAYER item 5); it was previously mis-assigned to S3, which neither owns the file nor listed the work, so the gate would have silently tested half of itself. (ii) The gate **does not name which kind of wall**, and the two available kinds are not equivalent: membership in `veto` is hard **and transitive** and re-applied in `finalise` (`cluster.py:363-370`, `:638-648`), whereas consultation inside `vetoed()` only is hard, **pairwise and invisible** to `finalise`, the D9 bridge alarm and `res.distinct_from` (how the geo veto is wired, `cluster.py:357-361`). Built the geo-veto way, the wall is non-transitive *and unreported* and G18 still passes. **The gate must name the channel and assert an analyst-visible reason.** |
| **G19** *(new)* cross-namespace-non-fusion | **D4** | **No gate currently names the most dangerous over-merge class for an operator-scoped OOB map.** `namespace_compatible` gates only bootstrap-exact-name, `_name_containment` (`cluster.py:261`), `_identity_pairs` (`resolve/__init__.py:596`) and `_coref_pairs` (`:654`) — **never the Phase-2 fuzzy fixpoint** — and relational blocking emits pairs with **no namespace key** (`cluster.py:182-187`). So a PLA-side and a PAF-side instance can be scored and auto-merged, directly contradicting spine/13 §3 ("never across operators within the instance layer"). RK-COREF owns closing it. Note D-13.20's composite AND-key identifier depends on this. |

**Two further items that are new code, not configuration — do not let them be assumed:**
- **D6 — the D-13.9(b) source-independence guard does not exist in the merge path.** The independence machinery
  exists for *claim* corroboration (`credibility/status.py`, spine/04) and appears **nowhere in `resolve/`**.
  `identity_ledger`'s "one entry per independent identity **signal**" is about signal *classes*, not source
  independence — it is the thing most likely to be mistaken for the guard. §7 RK-COREF item 5 currently reads
  as configuration. **Scope it in S3 or disclose it.**
- **"Rarity-graded name" has no implementation anywhere**, yet D-13.2 and D-13.10 both rest on it. Either S3
  builds it or the design stops claiming it.

### 5a-bis. "Byte-identical" is S1's invariant ONLY — for S2–S4 it is a FAILURE signal

Recorded 2026-07-25 after the user challenged whether S1's unchanged-view result was force-fitting to the
corpus (working-principles #1). The distinction is real but easy to cargo-cult forward, so it is written down:

- **S1 legitimately changes nothing** because it *builds* nothing behavioural: it names an id that already
  existed, adds a **dormant** field (referents are minted in **S3** — A1 says so explicitly, because coref is
  off in S1 so there is no cluster grain to mint against), and adds schema the next stages consume. An
  unchanged graph is the *evidence the plumbing is inert*, not evidence the corpus was protected. It was
  verified on the **real corpus** (identical view hash, 160 nodes / 73 edges) precisely because the golden
  fixture never exercises `dedup` at all — so the golden alone would have been corroboration, not proof.
- **S2, S3 and S4 change what the graph contains** — layer routing splits straddling mentions, presence and
  formation become citizens, coref clusters become the mint grain, ids stop deriving from names. **For those
  stages an unchanged view means the stage did nothing.** Do not carry S1's invariant forward, and do not
  accept "the golden is byte-identical" as a stage-passing criterion after S1. The plan already says the golden
  **regenerates** at S4 (§9); the fragmentation metrics are meaningless until S3 (F8) and **must never be
  "fixed" by loosening thresholds**.
- **Never gate, default-away, or curb a target-correct capability to keep a fixture green** (#1/#5). A mechanism
  may legitimately be **byte-inert on the current corpus** — the data pass established that the corpus holds
  essentially one numbered formation, one stated basing and zero serials, so most of the discriminator ladder
  *cannot* fire on it — but inert-because-the-data-is-sparse is not the same as hidden-to-protect-a-fixture.
  The first is honest; the second is forbidden.

**One S1 affordance with an expiry date, flagged rather than left to rot.** S1's `TypeDef.attrs` loader accepts
**both** the legacy bare-string form and the new structured form, so no config file had to change in S1. That is
a *migration affordance*, *not* a permanent feature — and if it is left indefinitely it becomes exactly the
mechanism by which `config/ontology.yaml` never migrates and the data never bends to the design. **S2 must
populate the structured form for every node-type and attribute-type (A2's `layer` tag), and should then either
remove the legacy tolerance or record explicitly why it stays.** Track it as an S2 acceptance item, not as a
nice-to-have.

### 5b. The spec closures C1–C10 (RK-SPIKE + its adversarial review) — binding

Full statements: **C1–C4** in `../../tmp/conv/rk-spike-DECISIONS.md`; **C5–C10** in
`../../tmp/conv/rk-spike-REVIEW-VERDICT.md`. They are cited by number from the stage scopes in §7, which is
what the hands actually read — **this appendix alone does not reach them.**

| # | Closure | Lands in |
|---|---|---|
| **C1** | G18's relationship wall fires on a conflict at overlapping times **within one `site_type`**; a differing `site_type` is **not** a conflict (so a unit at a garrison *and* a forward site is two valid basings). One declaration, **two consumers**: the wall (S3) *and* `based-at`'s supersede `instance_key` (S2) — the second is where the D1 fabrication path stays open if it is missed. `unknown` `site_type` must **fail safe** (same bucket / raise, never de-conflicted) | §7 RK-LAYER 5, RK-COREF 7 |
| **C2** | G16 asserts on the **observable outcome**: no confirmed formation merge · node count preserved · **no drawn relocation** · **no Known-Gap deletion / no `insufficient → stale`** on the retired edge. A presence-level merge in the same case is *expected* | §5a G16, §7 RK-COREF |
| **C3** | The D-13.18 decline fires on a conflicting critical discriminator of **either kind** — attributes (read `attr_history`, never the first-wins scalar) **and relationships** (the same overlapping-time predicate G18 uses, under C1's `site_type` rule) | §7 RK-COREF 7 |
| **C4** | What the spike does **NOT** verify: no contract slot for a sourced `count`, design-layer nodes, the **licensing quote**, **source identity** (so D6/C8 independence is unverified), or config | disclosures, §9 |
| **C5** | The Tier-0 gate is evaluated **per link**; a cluster binds only over passing links and each failing link becomes an injected Tier-1 candidate pair — a **partial** bind, not all-or-nothing (the spec's "**both** members' surface forms" never generalised to n-ary clusters) | §7 RK-COREF 7 |
| **C6** | `perishable` is declared **per (type, attribute)**: geography is perishable for a *formation*, **constitutive** for a *presence*, **identifying** for a *place*. Without it no anchor/design can confirm and lever 2 cannot exist. Plus fix the `places.augment` ordering | §7 RK-COREF 7 |
| **C7** | Value normalization is a prerequisite for walling on **any** slot (not just operator); an unnormalizable stated critical value ⇒ **no wall AND no fusion** + a named gap. **A gap must bind the fusion path, not merely annotate it** | §5 G18, §7 RK-COREF 7 |
| **C8** | **ROADMAP, not S3 (user ruling 2026-07-25).** The rule stands unchanged — **two independent sources ⇒ `confirmed`**. Re-keying *detection* onto evidential lineage (a cite-of-a-prior-report is same-group) is deferred: the independence-group mechanism already exists and already applies the lineage idea to inferences (`config/credibility.yaml:160`), so the change is cheap later. **Disclosed** in the meantime | roadmap + disclosures |
| **C9** | An authoritative coref bind may instantiate **only over entity ids attested in the contributing document** — decisions (a) and (b) share the `Entity.doc_ids` carrier and (a) must not ship without it | §7 RK-COREF 7 |
| **C10** | A relocation may be drawn from one source only when that source authoritatively co-refers its own mentions **and** clears the authoritative-bind grade floor; a bare single-member instance never licenses one | §7 RK-COREF 7 |

**Two further review findings that raise the severity of what §5a already names:**
- **Name is a verdict in Phase 1, at every type.** The widest name-only fusion path **bypasses the bands
  entirely** via the Phase-1 bootstrap disjunction (`resolve/cluster.py:455-463`) and applies to `unit`,
  `variant`, `basing_site` and every other type — **not** only the two lowered per-type floors, and it never
  reaches `confirm_is_durable` at all. R1.2/R3.1/R3.2 must bind the **bootstrap**, not just Phase 2.
- **Alias self-equivalence bypasses both the namespace and the type gate.** `AliasIndex` equivalence is
  reflexive where its docstring promises a real alias link, so the namespace-gated exact-name branch is never
  reached — making cross-operator **and cross-type** fusion reachable in **Phase 1**. G19's remedy must cover
  the bootstrap, not only the Phase-2 loop.

**And one ordering fix, cheap and load-bearing:** `places.augment` runs **after** `resolve_entities`
(`resolve/__init__.py:181` vs `:177`), so place merges are invisible to `relational_score`. spine/13 §6 lever 2
names places as a clean anchor the instance layer crystallizes onto — **mechanically they are not one.**
Together with **F9** (only *completed* merges carry relational weight) this makes lever 2 weaker than the design
assumes in **two independent ways**. Fix the ordering in S3.

---

## 6. Running a stage (orchestrator + subagents)

Every RK-* stage runs through the same procedure, so the plan is self-sufficient: an orchestrator can kick off a
stage from this document alone. The three-hands separation is **structural** here — enforced by how the subagents
are wired, not by discipline alone.

**Subagents are opus.** Every hand below is dispatched as an **opus** subagent — never fable, never sonnet (the
standing session directive; the reasoning load of substrate work demands it). Right-size only the *helper* lookups
(a doc-read, a grep) to a smaller model.

**The procedure:**
1. **Read first.** The orchestrator reads this plan's stage section and the stage's **"Read first (design + code)"**
   line (its spine/13 §§, DECISIONS rows, and Appendix A code anchors) — and delegates any heavier reading.
2. **Spin the thin session file.** Create `sessions/RK-*.md` citing this document's §§ — it stays thin (goal,
   scope pointer, gates, acceptance), never restating the design.
3. **Open the worktree.** `wt-RK-*` off the design branch, never the main checkout.
4. **Dispatch the three hands as separate opus subagents:**
   - **Implementer (corpus-blind).** Receives the stage's scope + gates from this plan; chooses gate fixtures on
     general principle; never sees the frozen corpus or the answer key. Commits impl on the impl branch.
   - **Independent test author (separate branch).** Receives **only this spec** (the stage's scope + acceptance +
     gate definitions) — **never the impl branch**. Writes the abstract unit tests + gate fixtures asserting what
     correct *is*, and commits them on a **separate branch merged before the impl branch is verified**.
   - **Independent data hand.** Authors fixtures/gold independently (and, for RK-DATA-adjacent work, documents-then-
     executes per §10).
5. **Orchestrator stays lean.** Reads each hand's *conclusions*, not raw files; spot-checks only the load-bearing
   claims (a cited `file:line`, a gate's failure signature).
6. **Verify.** Run the independently-authored tests against the independently-authored code on independently-authored
   data: abstract unit tests + the dual-run old-vs-new at the flag boundary + **predict-then-verify** the expected
   diff (test id + exact diff + why it's target-correct). Any unexplained diff is a regression until proven otherwise.
7. **Commit + handoff.** Commit each sub-stage; add a `PROGRESS.md` board row + a `DECISIONS.md` entry for any
   behaviour-changing call or contract amendment; write the five-beat handoff note (Shipped · Decisions
   [principle → choice → alt rejected] · Deviations · Follow-ups · Gate fixtures), **noting how the three-hands
   separation was evidenced this stage** (which branch held the tests, that the impl hand never saw the corpus).

**Kickoff checklist (per stage):**
- [ ] Stage's "Read first" opened (plan §§ + spine/13 §§ + DECISIONS rows + Appendix A anchors).
- [ ] Prerequisite stage merged (per the §2 DAG); contended files (§3) free of concurrent owners.
- [ ] Thin `sessions/RK-*.md` spun out, citing this plan.
- [ ] Worktree `wt-RK-*` opened off the design branch.
- [ ] Three **opus** subagents dispatched with disjoint inputs (impl corpus-blind; test author spec-only on a
      separate branch; data hand independent).
- [ ] Gates for this stage identified from §5; abstract fixtures planned.
- [ ] Flag boundary + dual-run plan defined; predict-then-verify diff prepared.
- [ ] `PROGRESS`/`DECISIONS` rows + five-beat handoff templated.

---

## 7. The stages in detail

Each stage below is the source for its `sessions/RK-*.md` file (spun out at stage start, thin, citing this
document's §§) and is run via the procedure in §6 (read-first → three opus subagents → verify → handoff). Every
stage carries a **"Read first (design + code)"** line, lands behind a flag, dual-runs old-vs-new before its
cutover, and ends verified (its abstract unit tests + the dual-run) and committed before the next.

### RK-SPIKE (S0) — close the design opens; prototype the risk

**Read first (design + code).** spine/13 §13 (the open micro-decisions + "highest-risk piece"); D-13.7/D-13.11
(referent grain / mint-once); the **no-embeddings** DECISIONS lock (:116). Code: skim `ingest/coref.py` and
`resolve/cluster.py` (Appendix A) to ground the prototype — no production code is written.

**Goal.** Retire the three open micro-decisions and de-risk the one concentrated design unknown *before* code,
on a throwaway branch, so the chain doesn't build on guesses.
- **Prototype characterize-and-cluster** (spine/13 §13 "highest-risk piece"): on a handful of representative
  shapes (from the existing frozen corpus or tiny fixtures — no full regen), show how a provisional instance is
  described richly enough to cluster cross-document, in what discriminator priority, and how a thin-context bind
  degrades to "under-determined + gap" rather than fabricating or over-merging.
- **Close the micro-decisions:** (a) Tier-0 auto-bind graded by coref category (explicit-equivalence/apposition
  binds tight; bare pronoun chains held looser); (b) Tier-1 same-document comparison + the strength of the
  contrastive anti-merge prior (F5); (c) discriminator priority (working assumption: designation > operator+geo >
  relational > name-as-recall).
- **Build the claim-gold slice** the bake-off needs (a few hand-labeled docs) — done by the data hand, so it is
  independent of both code and the model.

**Constraint (locked).** Characterize-and-cluster uses **only** the sanctioned runtime signals — alias/rarity +
BM25 + fuzzy + relational/discriminator. **No runtime embeddings**; any embedding-based candidate-generation stays
offline/roadmap (DECISIONS lock :116). Guard this in the prototype so an implementer isn't tempted to reach for
sentence-transformer similarity.

**Output:** decisions written into spine/13 §13 (moving them from "open" to "decided"); a small prototype in
`tmp/`; the claim-gold slice. No production code. **Acceptance:** each micro-decision has a decision + rationale;
the prototype demonstrates the degrade-to-gap path on at least one thin-context case, using no embeddings.

### RK-ATOMS (S1) — claim atom, dormant referent field, atom-aware dedup, A7 discriminator schema (non-breaking)

**Read first (design + code).** spine/13 §8 (mint grain / atoms) + §12 (migration); D-13.7/D-13.11; A1 + A7's
discriminator half (§4). Code (Appendix A): the ClaimRecord **construction** sites and the canonical-id **remap**
sites; `schemas/{claim,ids,base,config_models}.py`.

**Goal.** Formalize the claim atom as the stable addressing bedrock, add the (dormant) referent field, make dedup
atom-aware, and land the A7 structured-discriminator schema — with **zero behavioural change** (the derived graph
is byte-identical after S1).

**Scope (build these):**
1. **Claim atom = post-dedup `claim_id`.** Formalize the canonical `claim_id` assigned in `dedup.assign_claim_ids`
   as *the claim atom* — the per-mention addressing bedrock. No new id here; this names and freezes what already
   exists (the canonical id is *not* set at construction — it is reassigned in dedup).
2. **Referent field (A1), optional/`None`.** Add an optional referent id (default `None`) to `ClaimRecord`/payloads
   (`schemas/claim.py`); add `make_referent_id` beside `make_claim_id` (`schemas/ids.py`) **but do not invoke it** —
   referents are minted in S3. `resolved_ref` stays derived. Optional-default keeps `extra="forbid"` fixtures loading
   and S1 non-breaking.
3. **Atom-aware dedup.** Extend `remap_claim_refs` **and** `dedup_within_doc` (`ingest/dedup.py`) to carry/reconcile
   the referent field, so a value populated later (S3) is never silently orphaned or collapsed — dedup reassigns
   `claim_id` and folds same-signature mentions, and today neither carries a referent. This is the real risk the
   old plan missed.
4. **A7 structured-discriminator schema (RK-ATOMS half of A7).** Add the structured claim-context fields
   (operator/geo/designation/time) to the `extract.py` mention schemas and the `config_models.py` structured-attrs
   representation they are declared against (restructuring `TypeDef.attrs` from a bare string list to structured
   entries). All optional; absence is `unknown`.
5. **Mint/remap sites — confirm at stage start with `grep 'ClaimRecord('`.** `ClaimRecord` is **CONSTRUCTED** in
   `extract.py` (`_emit` ~:815 + the `transform_*` fns — the primary builder), `coref.py`, `basing.py`,
   `attribute.py`, `imagery.py`. The canonical claim-atom id is **REMAPPED** downstream in `dedup.py`
   (`assign_claim_ids`/`remap_claim_refs`), `lane.py` (chunk-namespacing), and `seed.py` (recorder). `adapters.py`,
   `lane.py`-as-orchestrator, and `seed.py`-as-bundle-reader do **not** construct `ClaimRecord`s (seed reads frozen
   bundles via `model_validate` — minting there would overwrite a frozen referent and break KEYLESS≡LIVE).

**Contracts:** freezes A1 (claim-atom half) + A7 (discriminator-schema half). **Gates:** G17 — RK-ATOMS authors the
*atoms-minted-only-at-ingest* portion; the no-mint/no-append-under-`rebuild()` clause is RK-LAYER's (§7) and the
id-from-atoms clause is S4's (A5); G1/G2 unchanged. **Owned paths:** `schemas/{claim,ids,config_models}.py`,
`ingest/**` (extract/dedup/coref/basing/attribute/imagery), `tests/ingest/**`, `tests/gates/test_g17_*`.
**Acceptance:** the claim atom (post-dedup `claim_id`) is stable and named; the referent field is present-and-`None`
on ingest-minted claims and tolerated-absent on pre-baked fixtures; dedup carries the referent field; the A7
discriminator fields are present-and-optional; the golden view is byte-identical to pre-S1; G17 green. **Out of
scope:** minting referents (S3); using the atom for addressing (S4).

### RK-LAYER (S2) — layer typing, endpoint materialization, presence/formation (flagged)

**Read first (design + code).** spine/13 §3a (presence/formation citizens), §5 (layer / straddle-split); D-13.3/D-13.5/D-13.6/D-13.13/D-13.14; the
bi-level "rebuild never writes evidence" rule (§1 + DECISIONS); A2/A3/A4. Code (Appendix A): `view/pipeline.py`
(`rebuild`/`_assemble`), `ontology.py`, `config/ontology.yaml`, `schemas/config_models.py`, `ingest/basing.py:357-366`.

**Goal.** Route each fact to its layer; materialize provisional instances at rebuild; stand up the presence and
formation citizens; replace the offline basing pass with a pure rebuild-derived edge. **Behind a flag**, dual-run only.

**Scope (build these):**
1. **Layer tags (A2)** — a `layer` on every node-type and attribute-type in `config/ontology.yaml`, reading the
   structured `attrs` entry S1 introduced; add the `layer` field to that entry (`schemas/config_models.py`) and a
   layer accessor in `ontology.py` (`NodeTypeIndex`, beside `refines`/`identity`).
2. **Straddle split + endpoint materialization (A4)** in `view/pipeline.py` `_assemble`/`rebuild`: design atoms →
   shared design node; instance atoms → instance node; an instance-layer edge whose mention named only the design
   materializes a provisional **presence**.
3. **Presence & formation citizens (A3)** — the two instance kinds; `count` as a sourced attribute; a bare
   sighting never forces a formation.
4. **Basing as a pure rebuild-derived edge (A4/D-13.6) — deleted, not relocated.** The offline pass in
   `ingest/basing.py` that **MINTS** a `kind='inference'` `ClaimRecord` (`make_claim_id`, `basing.py:357-366`) and
   **appends** it (`store.append_many`) is **DELETED**. In its place, `rebuild()` materializes a derived-layer
   `based-at` **EDGE** each rebuild, **citing its two premise claim-atoms** (the `observed-at` claim + the
   `inducted-into` claim) for one-click provenance — with **NO `make_claim_id`/`ClaimRecord` mint and NO
   `store.append` inside rebuild**. This satisfies **G17** (no rebuild-time minting) and the bi-level rule that
   rebuild never writes evidence; it is a pure knowledge-layer derivation exactly like `resolve`/`score`.
   Consequently the **`__basing.json` derived-claim bundles cease to exist**: the seed loader's
   `_DERIVED_BUNDLE_SUFFIXES` glob and the `pending.py` references that ride them **drop with the deleted pass**
   (RK-DATA removes them from the regen set — §10). Correct the three stale "no source states basing" comments
   (the design pass is done in this branch; keep aligned).

5. **Ontology additions this stage owns (added 2026-07-25 — S2 owns `config/ontology.yaml`, and no later stage
   does).**
   - **`operated-by`** — G18's relationship wall names it and **the predicate does not exist**. Add it here, or
     G18 silently tests half of itself. (Previously mis-assigned to S3, which neither owns the file nor listed
     the work.)
   - **D12's `contract_import_event` ↔ `trading_org` edge** — the customs document's actual spine (event ↔
     consignee ↔ shipper) is currently **unrepresentable**, while the schema *does* offer `imported-by → unit`,
     which no such document states. **A schema that makes the sourced relation inexpressible and the unsourced
     one easy pressures extraction toward fabrication.** Also re-examine whether `imported-by → unit` should
     require a stated unit.
   - **`based-at`'s supersede `instance_key` tagged by `site_type`** (**R1.3 / C1's second consumer**) — so a
     unit legitimately at a garrison *and* a forward site is **two concurrent valid basings, not a relocation**.
     The ontology currently rests unit-only keying on "correct while the corpus has no such simultaneous pair"
     (`config/ontology.yaml:40-44`), which working-principles #1 forbids as a design input. **State the absent
     `site_type` default explicitly and fail safe:** `unknown` ⇒ same bucket (the wall fires) or ⇒ raise —
     **never** ⇒ de-conflicted, since the evasion direction is over-merge. `site_type` becomes a config-declared
     closed vocabulary under the same normalization prerequisite (C7).
   - **Carry forward the relocation/relational mitigation** (`co_instances`, `resolve/scoring.py:337-350`): a
     dated relationship to the same neighbour at two different times is **not** the same relationship. A naive
     `site_type` re-key changes the `edge_instance` shape and would **silently drop this mitigation**, so a
     confirmed relocation would manufacture relational evidence that origin ≡ destination. Gate-fixture it.

**Contracts:** A2, A3, A4. **Gates:** G15 (presence-not-fused — **plus the C/D2 clause: an ambiguous or
truncated formation attribution must produce a named gap; never a silent pick**, since the truncation at
`ingest/basing.py:301` records no `SkipRecord` while every other rejection path does), **G17** (RK-ATOMS authors the atoms-only-at-ingest
portion; RK-LAYER **extends** it with the no-mint/no-append-under-`rebuild()` clause — the fixture must include an
`observed-at`+`inducted-into` premise pair so the derived-basing branch actually runs, else it passes vacuously),
G1/G2 (basing stays pure). **Owned paths:** `config/ontology.yaml`, `ontology.py`, `schemas/config_models.py`
(contended, after S1), `view/pipeline.py`, `resolve/__init__.py` (endpoint-layer typing; contended — see §3),
`ingest/basing.py`, **`config/credibility.yaml`**, **`credibility/supersession.py`** (the D1 promotion path —
`promote_supersessions` must not machine-adjudicate a pair out of the analyst's queue over a sub-confirmed
identity, **R1.4**, and must not delete the retired edge's Known Gap), `tests/view/**`,
`tests/gates/test_g15_*`, `test_g17_*`. **Acceptance:** a straddling mention
splits into linked design+instance nodes; an `observed-at` materializes a presence; a **stated** `based-at` binds a
formation directly while a **derived** one is a rebuild-materialized edge citing its two premise claim-atoms (no
minted claim); G17 green (no mint/append under `rebuild()`); **flag off ⇒ byte-identical to S1**. **Out of scope:**
the coref-cluster mint grain (S3) — until then this fragments per-mention (F8), which is expected and must not be
"fixed."

### RK-COREF (S3) — coref-cluster minting, per-layer policy, co-location cap, relationship-conflict wall

**Read first (design + code).** spine/13 §6 (two-tier resolution + fragmentation control / the three levers), §7 ("Reuse vs. new"); D-13.8/D-13.9/D-13.10/D-13.14; A7's coref half; the
**no-embeddings** lock (:116); F9 (below). Code (Appendix A): `ingest/coref.py` (off via `resolve/rconfig.py`
`coref_authoritative_evidence` empty); `resolve/{__init__,cluster,rconfig}.py` (walls/veto/bands/fixpoint — reuse,
**extend** with the relationship wall).

**Goal.** Make the doc-local coreference cluster the mint grain (Tiers 0/1); apply the per-layer identity policy;
enforce the co-location cap; **extend the judge with the relationship discriminator**. First stage at which
fragmentation metrics are meaningful.

**Scope (build these):**
1. **Promote Tier-0 coref** — `ingest/coref.py` from optional to required; the doc-local coref cluster **GROUPS the
   per-mention claim atoms** and is **where the referent atom is minted at ingest** (`make_referent_id`, added
   dormant in S1, invoked here); auto-bind graded by coref category (RK-SPIKE decision). Populate
   `coref_authoritative_evidence` (`resolve/rconfig.py`) per that policy. (It does *not* "carry the S1 atom" — S1
   mints no referent.)
2. **Tier-1 cross-doc + same-doc (F5)** — `resolve/__init__.py`/`cluster.py` cluster *provisional instances*, not
   bare mentions; compare same-document pairs too, with a contrastive anti-merge prior only when the source
   syntactically distinguishes them.
3. **Per-layer identity policy (D-13.10)** — one judge, permissive per-layer profile: design collapses readily but
   *never on name alone* (name is a rarity-graded contributor, capped at *possible*); instance fully earned.
   Plugs into `_band`/`auto_merge_for_pair`.
4. **Co-location cap (D-13.14/G16)** — shared design+site+operator → presence-merge OK, formation-merge capped at
   *probable*; confirming a formation needs a unit-level discriminator. Residual surfaced as a coverage item.
5. **Confirmed-without-unique-id guards (D-13.9)** — geography is perishable (perishable-only ≤ probable);
   corroboration inherits source-independence (two reprints of one almanac can't confirm).
6. **Relationship-conflict wall (D-13.8/D-13.9; NEW code, extends the judge — G18).** A **stated** `based-at` /
   `operated-by` conflict at overlapping times is a **hard wall**, not a relational score — two units at different
   sites at overlapping times are different units. Add this discriminator to the judge
   (`resolve/cluster.py` walls/veto). **Value normalization is a prerequisite** (D-13.8): **S3 owns** the
   per-instance-type critical-discriminator declaration (operator/branch critical) and value normalization
   (PAF ≡ "Pakistan Air Force"), distinct from RK-DATA's data/answer-key regen; confirm at stage start whether the
   existing normalization suffices or needs extension.

**Caveats to carry (spine/13 §13):**
- **F9 (load-bearing).** The shipped status-weighted relational signal counts **only completed merges** — a
  sub-confirmed (probable/possible) link contributes **0** weight. So **spine/13 §6 lever-2** (clean-anchor
  relational scaffolding) works **only via anchors that resolve into real merges**. Either accept this gap explicitly or scope the
  sub-confirmed-relational-weight fix; do not assume graded sub-confirmed relational weight exists.
- **No runtime embeddings** (as RK-SPIKE): the cluster machinery uses only alias/rarity + BM25 + fuzzy +
  relational/discriminator signals.

7. **The RK-SPIKE closures C1/C3/C5–C10 (mandatory — added 2026-07-25).** These are stage scope, not
   background reading; the full statements are in `../../tmp/conv/rk-spike-DECISIONS.md` (C1–C4) and
   `../../tmp/conv/rk-spike-REVIEW-VERDICT.md` (C5–C10).
   - **C5** the Tier-0 gate is evaluated **per link** (anchor→member); a cluster binds only over passing links,
     and each failing link becomes an injected Tier-1 candidate pair (a **partial** bind, not all-or-nothing).
     Declare the equivalence-marker vocabulary in config, verb forms included.
   - **C6** declare `perishable` **per (type, attribute)** — geography is perishable for a *formation*,
     constitutive for a *presence*, identifying for a *place*. The shipped `attribute_roles.<type>.<attr>`
     schema already supports it. This is what lets an anchor/design layer confirm at all (without it designs
     never collapse and spine/13 §6 lever 2 cannot exist). **Also fix the ordering bug:** `places.augment`
     runs *after* `resolve_entities` (`resolve/__init__.py:181` vs `:177`), so place merges are invisible to
     `relational_score`.
   - **C7** normalization is a prerequisite for walling on **any** slot (not just operator); an unnormalizable
     stated critical value ⇒ **no wall AND no fusion**, plus a named gap. **A gap must bind the fusion path,
     not merely annotate it.**
   - **C8 — NOT in this stage's scope (user ruling 2026-07-25).** The independence *rule* is correct and
     unchanged: **two independent sources ⇒ `confirmed`**. Re-keying how independence is *detected* (evidential
     lineage rather than publisher / source-type, so a cite-of-a-prior-report is same-group) is a **roadmap
     refinement**, because the independence-group mechanism already exists and the config already applies the
     lineage idea to inferences (`config/credibility.yaml:160`) — so extending it later is cheap. **Do not
     build it here.** It is **disclosed** instead (design-note disclosures): where one source's report reads
     another's, the system may count two looks where a strict reading sees one.
   - **C9** an authoritative coref bind may instantiate **only over entity ids attested in the contributing
     document** — it shares decision (b)'s `Entity.doc_ids` carrier and must not ship without it.
   - **C10** a relocation may be drawn from one source only when that source authoritatively co-refers its own
     mentions **and** clears the authoritative-bind grade floor; a bare single-member instance never licenses
     one.
   - **Bind the caps to the Phase-1 bootstrap disjunction** (`resolve/cluster.py:455-463`), not only to the
     Phase-2 collection loop: **name is a verdict in Phase 1 at every type**, and the caps exist only in
     Phase 2. R1.2/R3.1/R3.2 all depend on this.
   - **Reject the "fusion is licensed by a structural trigger, never a score" whitelist** (the prototype's
     invention): D-13.9 specifies a *graded* path constrained by two guards. Keep the half that is right — the
     guard is a hard **precondition on the fusion path** (R3.1) — and reject the positive trigger whitelist.
   - **Reformulate the anaphor gate positively** (named, declared, ontology-typed antecedent; `unknown`-typed
     endpoints count as type-compatible so a second undeclared endpoint fails the gate). **If the positive gate
     is not built, `UNAMBIGUOUS_ANAPHOR` reverts to raise-only.**

**Contracts:** consumes A2–A4; lands A7's coref half; **extends** the earned-identity judge with the relationship
discriminator (not merely "exercises" it). **Gates:** G16 (three-part per **C2**: no confirmed formation merge ·
**no drawn relocation edge** · **no Known-Gap deletion and no `insufficient → stale` transition** on the retired
edge), **G18** (per **C1**: fires within one `site_type`; names the wall channel; asserts an analyst-visible
reason), **G19** (cross-namespace **and** cross-type non-fusion, covering the Phase-1 alias branch), plus the
existing G7 confirmed-gate. **Owned paths:** `ingest/coref.py`, `resolve/{__init__,cluster,rconfig,aliases}.py`,
**`config/resolution.yaml`** (the home of nearly every knob this stage adds — `coref_authoritative_evidence`,
`hard_id_fields.unique`, `attribute_roles` incl. per-(type,attribute) `perishable`, the value-normalization
classes, the contrast band ceiling), `tests/resolve/**`, `tests/gates/test_g16_*`, `test_g18_*`, **`test_g19_*`**.
**Acceptance:** the characterize-and-cluster prototype's cases pass; co-location does not over-confirm a
formation **and draws no relocation**; a stated based-at/operated-by conflict at overlapping times within one
`site_type` hard-walls (G18); a cross-namespace or cross-type pair cannot fuse in **either** phase (G19); an
untestable critical discriminator neither walls nor fuses; honest residual fragmentation reports as a
`/coverage` gap. **Out of scope:** cutting the name-key (S4).

### RK-NAMECUT (S4) — cut the name-key; re-anchor decisions to atoms & config to stable handles; regen the golden

**Read first (design + code).** spine/13 §8/§11; D-13.11/D-13.15; A5/A6 (§4). Code (Appendix A): the name-address
mint sites, the name-verdict bootstrap, the alias index, the decision-replay paths (merge-by-name and
status-by-node-id), and the golden fixture + its id-pinned gates.

**Goal.** Entity address stops being the name; the atom→entity indirection replaces it everywhere; analyst
decisions re-anchor to atoms, config anchors stay on stable handles, and the abstract golden regenerates for the
new id-derivation.

**Scope (build these):**
1. **Kill the name mints (A5)** — remove `ent:{type}:{name}` at `resolve/entities.py:49/56/180`,
   `resolve/__init__.py:328/411`, `view/pipeline.py:343`; edge endpoints become atom handles. **Event mints are
   exempt** — `resolve/entities.py:57` (`event:{event_type}:{claim_id}`) and `view/pipeline.py:363` (`event:{claim_id}`)
   stay **per-claim (claim-atom keyed)**; do not re-key them, and G13's `ent:{type}:{name}` scan need not cover
   `event:` mints.
2. **Kill the name-verdict bootstrap** — `resolve/cluster.py:457-458/465` and the `has_durable_trigger` exact-name
   path (`:411-415`); name becomes a rarity-graded contributor + blocking key only.
3. **Alias index as pure recall** — `resolve/aliases.py` name-class buys a *comparison*, never a merge.
4. **Node id from atoms + redirect map (A5)** — `view/pipeline.py` derives ids from atom membership (claim-atom
   fallback when no referent, per A5) and emits the old→new redirect map; the `display_names` map becomes the
   derived label.
5. **Decision-log re-anchor (A6/D-13.15) — the two cases, kept distinct:**
   - **Analyst decisions** — merge accept/reject (today replay by *name* via `aliases.py`/`controlpoints.py`) and
     status/integrity overrides (today by *node-id*, silently dropped) — both key on **atoms**; thread an
     atom→current-node index into `apply_decision_effects` (`view/pipeline.py:615-629`) + the `controlpoints` replay;
     replay **fails loudly** on a dangling atom reference.
   - **Human-authored config anchors** — `config/observables.yaml` watch-lists and `config/subjects.yaml` anchors —
     re-anchor to **stable handles** (registry ids or names resolved via `resolve/anchor.py`'s ladder), **NOT** the
     drifting min-member node id. "Fail loudly" does **not** apply here.
6. **Partition keys to atoms** — `schemas/stage_io.py` (`same_as`/`candidates`/`possible`/`entity_canonical`/…).
7. **Regenerate the abstract golden (A5 changes rebuild()'s id-derivation code, which runs over the golden too):**
   (a) re-mint `tests/fixtures/golden/{evidence_log,expected_view}.json` through the S1 ingest path so golden claims
   carry atoms (or, absent them, key on the claim-atom fallback); (b) update the id-pinned assertions in
   `test_g5_two_scores.py:52-53`, `test_g10_subject_as_lens.py:40`, `test_g12_hitl_propagation.py:15` — **refactor to
   resolve via lookups, not literal ids, where feasible**; (c) re-commit `expected_view.json` so **G2** matches.

**Contracts:** freezes A5, A6. **Gates:** G13 (no-name-as-address; events exempt), G14 (decision-durability), and
the four id-pinned golden gates (**G2/G5/G10/G12**) regenerated here. **Owned paths:** `resolve/**`,
`view/pipeline.py`, `hitl/**`, `schemas/stage_io.py`, `config/{observables,subjects}.yaml` (key-format re-anchor
only — content is RK-DATA's, §3), **`tests/fixtures/golden/**`**, `tests/{resolve,view,api,config}/**`,
`tests/gates/test_g13_*`, `test_g14_*`, **`test_g2/g5/g10/g12`**. **Acceptance:** identity survives a simulated
re-key with all recorded **analyst decisions** re-applying (loud-fail on dangling); **config anchors** resolve
stably across the re-key; the four golden-pinned gates re-mint and pass; G13/G14 green; the worked-query regression
(invariants, no ids) still passes. **Out of scope:** the corpus id regeneration itself (RK-DATA).

### RK-MATERIALITY — two-layer operator-scoped chokepoints (after S3)

**Read first (design + code).** spine/13 §9 (two-layer operator-scoped chokepoints). Code (Appendix A):
`materiality/precompute.py` (today a flat, name-keyed sole-source in-degree).

**Goal.** spine/13 §9: the same materiality test over dependency edges at *both* layers; a chokepoint assessment
for an operator is a layer-crossing traversal (walk the operator's instance layer + down into the shared design
layer, union, scoped to the operator).

**Scope:** rework `materiality/precompute.py` to the layer-crossing, operator-scoped traversal. Depends on S3 (needs
individuated instances to scope by operator). The un-observable sustainment tier surfaces as **named gaps**, never
fabricated providers (the non-negotiable at the instance layer). **Owned paths:** `materiality/**`,
`tests/materiality/**`. **Acceptance:** "where does Pakistan's capability break" scopes to Pakistan's instance layer
+ inherited design chokepoints; an under-observed sustainment dependency is a named gap.

---

## 8. The extractor-model bake-off (RK-BAKEOFF)

**Read first (design + code).** spine/13 §10 (the extractor contract); DECISIONS rows on the extraction primary,
the **locked in-scope VLM imagery path** (:124/:125/:128), and **no-sampling-params**; the provider seam
`ingest/client.py` (Appendix A).

**Framing.** The replumb makes extraction more load-bearing (it now carries coref handles + structured
discriminators, A7) and the data pass regenerates the corpus *using* the extractor — so the model must be settled
**before the full regen**. It is a contract-first, measured bake-off, **not** post-hoc tuning. I do not assert a
winner: I can't verify the comparative capabilities of the specific candidates, and fabricating benchmarks would
violate the one rule the project is built on. The harness decides on evidence — and where the evidence is within
noise, the honest verdict is **"no measured difference."**

**Not independent of the code chain.** The bake-off's top criteria are substrate-*dependent*:
discriminator capture needs A7's schema fields (RK-ATOMS), and coref-binding needs the promoted coref tier
(RK-COREF). So it runs in two phases:
- **Wave-0 substrate-INDEPENDENT screen** (before any code): surface-claim P/R/F1, citation faithfulness,
  extract-only-stated discipline, structured-output reliability, cost/latency, and the VLM gate. These need no new
  schema and measure the model on the task any substrate shares.
- **Definitive pass** (after RK-ATOMS for discriminator capture; after RK-COREF for coref binding): the two
  top-weighted criteria, measured against the real extractor contract.
Both phases complete before RK-DATA's full regen — consistent with §2's two-phase build order.

**What already exists.** The provider seam is abstracted: an `ExtractionClient` Protocol (`ingest/client.py`) with
`GeminiExtractionClient`, `AnthropicExtractionClient`, and `ScriptedExtractionClient` behind one
`build_extraction_client(model_id)` factory; SDKs imported lazily. Adding a candidate = one new class (or the
`litellm` roadmap swap). **What does NOT exist and is greenfield:** claim-level gold, an extraction scorer, and the
comparative-scorecard runner — `report.py`'s `AcceptanceReport`/`CheckResult`/`StatusDiffRow` scaffolding is **dead
code** (imported nowhere), single-scenario pass/fail, not a model-comparative matrix. Budget this as a **from-scratch
scorer + orchestrator**, not an extension.

**What must be built** (under `backend/eval/extraction/`):
1. **A labeled claim-gold slice** (from RK-SPIKE, data hand): per representative doc, the gold
   `(subject-surface, predicate, object-surface, tier-3 attributes, doc_ref span, polarity, coref-cluster,
   discriminators)` tuples.
2. **A per-slice SUB-ORACLE** (data hand): the node/edge subgraph derivable from *exactly the labeled docs*, so
   graph-recall is measured on the same doc set every model sees. The **full** `answer_key.ground_truth` (18 nodes /
   19 edges across 26 docs) is **NOT** the bake-off metric — a few-doc slice scored against the full oracle would be
   dominated by which docs are in the slice, i.e. identical noise across candidates. **No full-corpus re-extraction
   happens during the bake-off**; full-corpus graph-recall belongs to RK-DATA under EVAL coordination.
3. **A claim-matcher + scorecard**: fuzzy surface/span alignment → precision/recall/F1 over claims;
   **coref-binding accuracy** (proposed clusters vs gold, *post-S3*); **discriminator-capture rate** (*post-S1*);
   citation-faithfulness (span slices back, G4); structured-output reliability (obeys the forced schema, no
   hallucinated fields); the extract-only-stated discipline (no fabrication); and graph-recall vs the **per-slice
   sub-oracle**.
4. **The orchestration**: record bundles under each candidate, rebuild each, emit a comparative scorecard.
   **Replication:** N repeated scoring runs per model with variance reported, a minimum margin before a difference is
   "material," and within-noise gaps reported as **"no measured difference"** — consistent with the no-winner
   posture, and necessary given confirmed run-to-run non-determinism on a small slice.

**Gating preconditions (a candidate must satisfy these to WIN — they are not weighted score lines):**
- **VLM imagery path preserved (locked).** The chosen primary is either **natively multimodal**, or a **declared
  multimodal tier** retains the locked in-scope VLM path. A text-only-strong primary that would drop the VLM path is
  **disqualified**, not merely down-weighted (re-litigating a locked demo capability is out of bounds).
- **KEYLESS≡LIVE restorable.** The selected primary must be **installed and successfully live-extract inside the
  shipped image** AND be the producer that **freezes the seed bundles** (so keyless == live *by construction*). A
  capability-winner that can't run live in the image does not restore the invariant. **Selecting Gemini is
  conditional on fixing the `google-genai` install**; a production winner's client lives in **`chanakya/ingest`, not
  `backend/eval`**.
- **Pinned model id.** Evaluate and freeze a **concrete pinned** Gemini version, not the floating `-latest` alias
  (the alias is a live-resilience fallback only; a floating seed producer breaks KEYLESS≡LIVE and reproducibility).

**Scored criteria, weighted to what the replumb depends on** (highest first): coref-binding quality (post-S3);
discriminator capture (post-S1); citation faithfulness (non-negotiable); structured-output/tool-call reliability;
extract-only-stated discipline (non-negotiable). Medium: determinism/reproducibility across the N runs (the live
lane is *allowed* non-deterministic, but a steadier model reduces re-record churn — and re-extraction is
*empirically confirmed non-deterministic and has broken the hero query*, so this matters); cost/latency for the
high-volume keyless seed. Kind-tagging accuracy is **low** weight — it self-corrects (the build routes by layer,
D-13.5).

**Candidates + execution preconditions (honest about what can be exercised).** Each candidate needs a **built
client + a provisioned key + the SDK installed**:
- **Anthropic Opus 4.8** — client built, key present, SDK installed: the **de-facto incumbent** (the shipped/tested/
  graded path).
- **Gemini** (a **pinned** flash version, i.e. the user's "3.6 Flash") — client built, but `google-genai` is absent
  from the shipped image (live 500s today); the install must be fixed for it to be a live candidate.
- **OpenAI GPT** ("5.6 Sol") — **no client and no provisioned key** in `chanakya`; needs a new `ExtractionClient`
  (or `litellm`) before it can be exercised.
**Fallback if a candidate can't be exercised:** state it plainly. If only Anthropic can be exercised, "the harness
decides" collapses to **"the incumbent stays"** — a legitimate outcome, but **not** a 3-way measurement, and the
scorecard must say so rather than imply a comparison that did not run. Evaluate a **tiered** option too (a cheap
model for easy formats, a stronger model for hard/coref/discriminator docs), but a Flash "latest and best" is a
cost/speed claim, not a guarantee it wins the *hard* judgment the replumb leans on.

**Drift to resolve.** The ledger says *Gemini primary*; the shipped/tested/graded path is *Anthropic Opus 4.8*
(`google-genai` isn't installed, so Gemini live 500s). Treat Anthropic as the de-facto incumbent and settle the
primary here **on evidence** — and **do not re-freeze the graded corpus/answer key without EVAL coordination**
(frozen-data rule). No sampling params on any provider (400 on Opus; omitted for Gemini too).

**Output:** a scorecard + a recorded decision (in `DECISIONS.md`) of the primary extractor and any tiering,
**including how the winner keeps the VLM path whole and restores KEYLESS≡LIVE, and the pinned model id frozen into
the seed** — with the adapter kept swappable so a re-run against a newer model later is cheap.

---

## 9. Verification & testing strategy

- **Three hands, every stage (structural — see §6).** Implementer (corpus-blind, gates chosen on general principle)
  ≠ test author (writes from this spec, on a **separate branch**, never seeing the impl branch, merged before the
  impl branch is verified) ≠ data hand (fixtures independent). Enforced by the subagent wiring in §6, not by
  orchestrator discipline alone; **evidenced per stage in the handoff note** (§12).
- **Corpus-independent unit tests per mechanism** are the primary defence — logic correctness never depends on a
  stale-corpus test. The new gates (G13–G18) get abstract fixtures like G1/G2.
- **Dual-run old-vs-new on the frozen corpus** at each stage's flag boundary; **predict-then-verify** the expected
  diff (test id + exact diff + why it's target-correct). Any new/unmatched/compound diff is a regression until
  proven otherwise.
- **The agent regenerates nothing.** A target-correct change that invalidates a fixture is marked
  `xfail(strict, reason=…)` and recorded in the data-refresh ledger (`../spine/12-data-refresh-calibrations.md`);
  the data hand regenerates.
- **Abstract golden: semantics survive, output regenerates.** G1/G2's determinism & purity *semantics* survive a
  re-key — but **A5 changes `rebuild()`'s id-derivation *code***, and that code runs over the abstract golden too,
  whose own ids are name-derived (`comp_gizmo`, `e:mfr_foundry:supplies-component:comp_gizmo`). So the committed
  golden **output** and the **four id-pinned gates (G2/G5/G10/G12)** regenerate at S4 (RK-NAMECUT scope item 7) —
  this is **not** a claim that "the golden is untouched." The worked-query regression (invariants, no ids) *does*
  survive unchanged.
- **Re-key blast radius — audit required, not a guess.** Node ids are minted at rebuild from `config/entities.yaml`
  and shared with the oracle, so a re-key ripples to `entities.yaml`, `observables.yaml`, `subjects.yaml`,
  `answer_key.json`, `SCENARIO_MANIFEST.json`, the **`__attr` bundles** (the **`__basing` bundles cease to exist** —
  §7 RK-LAYER / basing is now a rebuild-derived edge), and the test files with hardcoded ids. An id-literal scan
  finds **~65 test files** holding id-shaped literals; **~15–18** of those pin the **abstract golden** ids
  (regenerated at S4, above), leaving **~45+ corpus-id-pinned files** for RK-DATA's coordinated regeneration. **Run
  the audit and record both counts before cutover**, and use a **helper that rewrites id literals via the emitted
  old→new redirect map** so the regen is mechanical, not manual.

---

## 10. Data regeneration, sequencing & rollback

**Read first (design + code).** `../spine/12-data-refresh-calibrations.md` (§B coverage additions + the refresh
ledger); spine/13 §12 (migration/regen). DECISIONS: the graded-regen entry this stage requires (below). Data:
`corpus/**`, `config/{entities,observables,subjects}.yaml`, `answer_key.json`, `SCENARIO_MANIFEST.json`.

- **Sequencing (settled earlier this session):** contract-freeze → then RK-DATA regenerates *in parallel* with the
  code stages, against each stage's frozen contract; the data hand documents-then-executes (findings first into
  `../spine/12-*.md`, execution after the contract freezes). RK-DATA does **not** run ahead of the contracts —
  target-first means the data follows the design.
- **Coverage additions RK-DATA owns** (from `../spine/12-*.md` §B): the ORBAT stated-basing gap (§B6 — a crisp
  numbered-unit ORBAT doc + a corroborating source so a *stated* `based-at` reaches confirmed, distinct from the
  capped derived edge), plus the existing §B1–B5 items the replumb makes live (attribute-role wall, credibility
  floor, bridge-across-a-wall, perishable succession, trajectory cap).

  **Sharpened by RK-SPIKE's data pass (2026-07-24)** — the independent data hand hand-labelled 7 representative
  documents (125 claim rows, 32 coref clusters, every span and licensing quote verified byte-for-byte) and
  established the following corpus-wide facts. Deliverables in `tmp/spike-rk/gold/`; findings in
  `tmp/spike-rk/gold/DATA-FINDINGS.md`.
  - **§B6 is confirmed and wider than assumed.** Across all 52 documents there is **exactly one** numbered
    formation and **exactly one** stated "based at" — both the same off-subject unit in a chaff doc — and
    **zero serials or registrations anywhere**. So **the entire top of D-13.20's discriminator ladder is inert
    on the current corpus**, and "formation identity unresolved" is the *only honest outcome available*, not a
    conservative choice. The answer key independently agrees: every `based-at` is `basis: derived`.
    **This is legitimate byte-inertness** (working-principles #5: a consequence of sparse data, mechanism at
    full strength) — **not** a reason to weaken the ladder. Two consequences: (i) the G16/G18/G19 fixtures
    **must** be abstract, because the corpus cannot exercise them; (ii) RK-DATA owes the numbered-unit ORBAT
    doc, and until it lands the formation layer correctly reports unresolved.
  - **NEW — the OOB-undercount trap does not exist in the corpus and must be authored.** Over-merge traps
    exist at *event*, *site* and *design* level, but **never at formation level**: there is no pair of
    individuated batteries at one garrison. The nearest doc raises co-location only as an *uncertainty*, which
    is useless as an anti-merge test. **Author it** — it is the shape D-13.14 / G16 exist for, and the one that
    guards the D1 fabricated-relocation path.
  - **NEW — the Rahwali confirm needs a genuinely independent second look** (defect register **D11**). Five
    documents mention Rahwali, three are deceptions, and the real pair may not be independent: the confirming
    document appears to *read* the first one's report, and its own claimed second signal is an unnamed vendor
    via an unnamed intermediary that released no geolocation. **DATA-C / EVAL adjudicate the source text
    first**; if it is derivative, either the independence grouping must treat cite-of-a-prior-report as
    same-group, or the corpus needs a real second look. Do not tidy this quietly — the honest fix may be to
    *lower* the flagship to `probable`.
  - **NEW — an ontology gap, not a data one** (defect register **D12**, owner **RK-LAYER/S2**): the customs
    document's actual spine (event ↔ consignee ↔ shipper) is **unrepresentable** — no edge connects
    `contract_import_event` to `trading_org` — while the schema *does* offer `imported-by → unit`, which that
    document never states. A schema that makes the sourced relation inexpressible and the unsourced one easy
    **pressures extraction toward fabrication**.
  - **NEW, user-ratified 2026-07-25 — the sub-oracle must not confirm on a single source.** Twelve
    `confirmed` entries in `tmp/spike-rk/gold/sub-oracle.json` rest on **one** source document each, which
    violates the system's own rule (`config/credibility.yaml:101` `min_independent_groups: 2` — *"≥2
    independent looks required to reach `confirmed`"*). This matters more than an ordinary data nit: the
    sub-oracle is the **yardstick** the bake-off and slice-recall score against, so a yardstick that confirms
    on one source is more confident than the system it grades, biased in the direction that flatters us.
    **Fix: cap every single-source entry at `probable`** (or, where a shared unique identifier inside one
    primary record is genuinely thought to justify a bypass, record that as an explicit `DECISIONS.md` entry
    with its rationale rather than letting it sit implicit). Also drop the one alias entry graded `confirmed`
    on a single hedged grade-C source while citing a row that implies the opposite. **Owner: DATA.**
  - **Answer-key items flagged, deliberately not fixed** (frozen-data rule): the ground truth contains no
    `trading_org` and none of the customs declarations — the concrete reason slice recall must score against
    the **per-slice sub-oracle**, never the full oracle (§8 item 2) — and the flagship `distinct-from` is
    graded `confirmed` on one hedged grade-C source while a grade-B document blurs the same designators. Also
    recorded: three irreconcilable induction dates, three range figures for one designator, and one document's
    self-inconsistent geography that **looks deliberate and should not be tidied**.
- **Full regen is a consequence of the re-key, coordinated with EVAL — and gated by a DECISIONS entry.** Re-extract
  the corpus with the bake-off's chosen (**pinned**) model, re-elect canonical ids, regenerate `answer_key.json` +
  the golden + the id-pinned tests. The **`__basing.json` bundles are NOT regenerated — they cease to exist** (basing
  is now a rebuild-derived edge; §7 RK-LAYER). Re-extraction is confirmed non-deterministic, so freeze once and
  version (KEYLESS≡LIVE). Because this **re-freezes the graded oracle** — the single most consequential, hardest-to-
  reverse action in the plan — RK-DATA does **not** begin the full regen until a **`DECISIONS.md` ledger entry**
  records it as a **user-approved, EVAL-coordinated re-freeze**, with the **OLD oracle archived/versioned** so pre-
  and post-re-key grading remain comparable.
- **Rollback:** every stage lands behind a flag and dual-runs before cutover; the chain is bisectable (each stage
  verified + committed). Because reversal is "append + recompute," a bad stage is a flag flip + revert, not a data
  surgery. The redirect map keeps provenance continuous across the id change.

---

## 11. Open items — closed by RK-SPIKE, tracked here

- ~~Tier-0 auto-bind threshold, graded by coref category.~~ **CLOSED — D-13.17** (+ the anaphor-gate
  reformulation, and **C5**'s per-link quantifier).
- ~~Tier-1 same-document comparison + contrastive-prior strength (F5).~~ **CLOSED — D-13.19.** Note the finding
  that removed work: **Tier 1 already compares same-doc pairs** (no document filter exists anywhere in
  `resolve/**`), so that half of F5 needs **no code** — do not budget for it.
- ~~Discriminator priority for cross-doc clustering.~~ **CLOSED — D-13.20** (+ **C6/C7/C8**).
- ~~The characterize-and-cluster of provisional instances.~~ **PROTOTYPED** (`tmp/spike-rk/proto/`), run against
  24 independently-authored cases (`tmp/spike-rk/cases/`) — **15/24**, with the residue triaged in
  `tmp/conv/rk-spike-REVIEW-VERDICT.md` §2. No embeddings; byte-deterministic across randomized hash seeds.
- **STILL OPEN, and S3 must not assume otherwise:** the D-13.9(b)/D6 **source-independence** guard (**C8** — new
  code, unverified by the spike), the **licensing quote** end-to-end (written but read nowhere), **rarity-graded
  name** (no implementation anywhere, yet D-13.2/D-13.10 rest on it), and whether the production knobs are
  wired (**C4**).
- Extractor primary + tiering — resolved by RK-BAKEOFF on the claim-gold slice (§8), subject to the VLM and
  KEYLESS≡LIVE gating preconditions.

---

## 12. Handoff & progress

Reuse the backend's mechanism: a board row + a five-beat handoff note (Shipped · Decisions [principle → choice →
alt rejected] · Deviations · Follow-ups · Gate fixtures) per stage in `PROGRESS.md`; each stage spins out a thin
`sessions/RK-*.md` citing this document's §§; every contract amendment (A1–A7) logged in `PROGRESS.md` +
`DECISIONS.md` with an additive/breaking annotation. The handoff also **records how the three-hands separation was
evidenced** (§6/§9). Design *why* stays in `../spine/13-*.md`; this plan is the *how*; the session files are the
per-stage execution.

---

## Appendix A — Code reference index

The concrete anchors each stage's "Read first" line points at. Line numbers are as verified at plan time; the
implementer re-confirms at stage start (`grep` for the symbol), since files move under the rework.

- **Name-address mint sites** (Stage-4 cut targets, §7 RK-NAMECUT item 1): `resolve/entities.py:49/56/180`,
  `resolve/__init__.py:328/411`, `view/pipeline.py:343`. **Event mints (exempt, stay per-claim):**
  `resolve/entities.py:57` (`event:{event_type}:{claim_id}`), `view/pipeline.py:363` (`event:{claim_id}`).
- **Name-verdict bootstrap** (§7 RK-NAMECUT item 2): `resolve/cluster.py:457-458/465`; `has_durable_trigger`
  `:411-415`.
- **Alias index (name-keyed)** (§7 RK-NAMECUT item 3): `resolve/aliases.py:23/41-56/79-88`;
  `resolve/__init__.py` `_matching_eids:232-241`.
- **Decision replay** (§7 RK-NAMECUT item 5 / A6): merge-by-name `resolve/aliases.py:106-156` +
  `hitl/controlpoints.py:93-99`; status/integrity-by-node-id (the **silent drop**) `view/pipeline.py:615-629` +
  `hitl/controlpoints.py:134-136` + `hitl/writeback.py:57`.
- **ClaimRecord construction sites (S1, §7 RK-ATOMS item 5):** `extract.py` `_emit ~:815` (+ `transform_*` fns —
  the primary builder), `coref.py`, `basing.py:357`, `attribute.py:333` (in `_build_inference`), `imagery.py:375`/`:406` (in `read_image_document`). **Canonical-id remap:**
  `dedup.py` `assign_claim_ids`/`remap_claim_refs`, `lane.py` chunk-namespacing, `seed.py` recorder. (Not
  constructors: `adapters.py`, `lane.py`-as-orchestrator, `seed.py`-as-bundle-reader.)
- **Basing derivation (§7 RK-LAYER item 4):** `ingest/basing.py:357-366` mints a `kind='inference'` `ClaimRecord`
  and appends it — **to be DELETED and replaced by a pure rebuild-derived edge** citing its two premise claim-atoms.
  Its frozen output (`__basing.json`) is loaded via `seed.py` `_DERIVED_BUNDLE_SUFFIXES` and ridden by `pending.py`
  — both drop with the pass.
- **Exists-off / offline vs build-new:** coref (`ingest/coref.py`, **off** via `resolve/rconfig.py`
  `coref_authoritative_evidence` empty — *promote* in S3); basing (offline pass — *replace* with a rebuild edge in
  S2); the earned-identity judge (`resolve/cluster.py` walls/veto/bands/fixpoint — **reuse**, *extend* with the
  relationship wall in S3); **new**: layer tags, atom indirection, presence/formation split, two-layer chokepoints
  (`materiality/precompute.py`).
- **Golden fixture (§7 RK-NAMECUT item 7):** `tests/fixtures/golden/{evidence_log,expected_view}.json`; gates
  pinning golden ids `test_g5:52-53`, `test_g10:40`, `test_g12:15` (plus `test_g2` matching the committed
  `expected_view.json`).
- **Provider seam (§8 RK-BAKEOFF):** `ingest/client.py` — `ExtractionClient` Protocol,
  `build_extraction_client:312-323`, `MODEL="claude-opus-4-8"`, `DEFAULT_GEMINI_MODEL="gemini-flash-latest"` (the
  floating alias — pin a concrete version for the frozen seed, per §8).
