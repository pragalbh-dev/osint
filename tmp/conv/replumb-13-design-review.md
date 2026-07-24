# Review — is the replumb (spine/13) making the right calls for the north goal?

**Status: FINAL (2026-07-24) — folded into `artifacts/spine/13-*.md`.** The agreed changes in §5/§5b/§5c
below and findings F1–F9 were incorporated into the replumb doc on 2026-07-24 (new §3a, reworked §6/§7/§8,
decisions D-13.9…D-13.16, migration §12, open-items §13). This review is retained as the reasoning +
code-receipt trail behind those edits.

Reviewer: orchestrator-side design analysis, per
`artifacts/working-principles.md` (target-first; code-verified premises; findings ranked by severity).
All premises verified against code by two read-only agents; the four most load-bearing receipts
(S1, S2, J2's bootstrap rule, J3's silent drop) independently spot-read by the reviewer.

Scope: `artifacts/spine/13-type-instance-and-identity-replumb.md` (the D1–D3 substrate) judged against
`artifacts/spine/10-resolution-real-world-redesign.md` §0 (the north star) and its decision ledger,
with `12-data-refresh-calibrations.md` as the data-pass context.

---

## 1. Verdict

**The replumb is the right substrate, and its central moves are correct for the north goal.** Specifically:

- **The two-layer reframe (§2–3) is the genuinely good idea in the doc.** It correctly shrinks the problem
  from "stop name-collapse" to "individuate instances + route facts to the right layer," and it recognises
  that design-layer sharing is a *feature* of the supply-chain use case, not a bug to fix. This is exactly
  "design the mechanism for the discipline, not the corpus in hand."
- **The stated/earned seam (§4, D-13.4) is principled and correctly placed.** Within-doc coreference as
  *reading* (source is sole authority on its own pronouns), cross-doc identity as *earned* — with coref kept
  challengeable — is faithful to north-star commitment 1 without over-applying it to intra-source reference.
- **D-13.6 (endpoint identity resolved at rebuild, never baked into the claim) is load-bearing and right.**
  It is the move that keeps the re-key inside the bi-level invariant and D12's pure-recompute semantics.
- **D-13.7 (mint per doc-local coref cluster) is the right grain.** Per-mention minting fragments; anything
  coarser smuggles cross-doc identity into ingest.
- **D-13.8 (critical-if-present, absence = unknown, normalization prerequisite) correctly extends D5/D6 to
  relationships** and keeps the non-negotiable intact (never force the extractor to fabricate a
  discriminator).
- **§9 (two-layer, operator-scoped chokepoints) is a strong consequence, not decoration** — it shows the
  individuation is what makes the mission question ("where does *Pakistan's* capability break") expressible,
  and it routes the un-observable sustainment tier into named gaps rather than fabrication.
- **§10 (discriminators optional-structured; no cross-doc identity from the extractor) is right**, for the
  non-negotiable reason the doc gives.

**The code verification strengthens the doc's case rather than weakening it.** Every premise of its "why"
holds (§2) — and the substrate is *worse* than §1 describes: name-as-identity runs in two stacked lanes
(exact-string dict collision at build, plus an exact-normalized-name auto-merge at confidence 1.0 inside the
resolver's bootstrap), both of which the re-key removes. Tier 0 is also cheaper than the doc implies — the
coref pass is already merged into main and reconciliation-wired, dormant behind two config gates.

**No finding below reverses the direction.** The findings are sharpenings — two places where the design's
fragmentation-control enthusiasm leans toward forced density against doc 10's own warnings (F1, F3), one
under-designed consequence of "identity is the cluster" that verification made concrete (F2: today's decision
log is split-keyed by name and by id, and the re-key disturbs both halves — one silently), and spec gaps to
close before implementation (F4–F9). F1 and F2 should be resolved *in the design doc* before any build; the
rest can be absorbed as stated sub-decisions.

---

## 2. Code-claim verification (premises of §1 of the replumb doc)

Verified against `wt-RESOLUTION-REDESIGN` @ `design/resolution-redesign` by a read-only verification agent;
the two most load-bearing receipts (S1, S2) spot-read independently by the reviewer.

### 2a. Substrate claims — all premises hold

| # | Doc-13 premise | Verdict | Receipt |
|---|---|---|---|
| S1 | Identity = `type+name` dict-key collision at profile build, upstream of the resolver | **CONFIRMED** | `backend/chanakya/resolve/entities.py:180` — `eid = base_ref(c, lane).entity_id or f"ent:{p.entity_type}:{p.name}"; ent = entities.get(eid)`. Same minting repeated at the view layer (`view/pipeline.py:343`). Runs before all candidate-gen/veto/bootstrap logic (`resolve/__init__.py:107` vs `:109-184`). |
| S2 | First-value-wins absorption; loser parked in history, not used as canonical | **CONFIRMED** | `entities.py:188-199` — `ent.attrs.setdefault(k, v)` (first claim replayed wins) + every value appended to `attr_history`. History **is** on the wire (`NodeView.attr_history`, `view/pipeline.py:359`), so the loser is traceable — but never the canonical scalar. |
| S3 | Graph addresses entities by name: edge endpoints are raw strings; alias index is name-keyed | **CONFIRMED** | `Edge.subject/object` are raw claim strings (`entities.py:135-138`, `:204-213`); resolver docstring says so explicitly (`resolve/__init__.py:346-351`); `AliasIndex._class_of: dict[str,str]` is normalized-name-keyed (`resolve/aliases.py:20-22`). Nuance: post-resolution `_link_endpoints` can attach entity ids — names are the *native currency*, not the only final form. |
| S4 | Extractor already tags kind; discriminators structured | **PARTIAL** | `entity_type` is a real structured field (`schemas/claim.py:69-70`); time/geo have typed slots (`claim.py:63,80-81`). But **operator and unit designation live in the untyped `attrs: dict[str,Any]` bag** (`claim.py:72,83`) — ontology only allow-lists the key names. So §10's "structured claim context" is a genuine contract change, not already done. |
| S5 | Ontology declares edge endpoint node-types | **CONFIRMED** | `config/ontology.yaml:141-153` — e.g. `{name: based-at, from: unit, to: basing_site, …}`; read at runtime by `EdgeLaneIndex`. §5's "endpoint layers fall out of endpoint types" premise holds. |
| S6 | Within-doc coref built but off | **CONFIRMED** | `backend/chanakya/ingest/coref.py` (488 lines) — and it is **merged into main** (PR #37), not on an unmerged branch. Dormant behind two closed-by-default gates: the `coreference:` block in `config/credibility.yaml:172-183` is commented out, and `config/resolution.yaml:180` ships `coref_authoritative_evidence: []` (raise-only). One stale comment in credibility.yaml claims RESOLVE doesn't honour coref pairs — the mechanism is actually wired (`resolve/__init__.py:616-645`); off via config only. |

**Two nuances that matter for the doc's §1 wording:**
- The collision key is the **exact byte-identical string**, not a normalized name — `normalize()` exists but
  only feeds the alias/fuzzy path. So the substrate has *two* name-as-identity mechanisms stacked: exact-string
  dict collision (build) + alias-closure-as-certainty (resolver bootstrap). Doc 13 §1 should say "exact
  name" for the collision; the substance of the claim is unchanged (if anything, stronger).
- Tier 0's promotion to a required tier is cheaper than the doc implies: the coref pass is already merged and
  reconciliation-wired; "promote" means populating two config blocks + quality-hardening, not landing a branch.

### 2b. Judge / decision-log / coverage claims

| # | Doc-13 premise | Verdict | Receipt |
|---|---|---|---|
| J1 | The pair judge is built: bands, credibility-gated critical wall, geo veto, transitive veto, bridge-alarm, monotone fixpoint | **CONFIRMED** (one PARTIAL sub-part, see J5) | Bands: `schemas/stage_io.py:101-117` + `resolve/cluster.py:81-101` (internal vocabulary is auto/hitl/possible; confirmed/probable/possible are the schema names). Wall: `resolve/scoring.py:149-177` gated by `critical_veto_min_grade: C` (`config/resolution.yaml:370`). Geo veto: `scoring.py:49-78` + `cluster.py:350-361`. Transitive: `cluster.py:363-370`, checked in both phases. Bridge-alarm: `cluster.py:504-510`. Monotone fixpoint, union-only: `cluster.py:467-496`, no backtracking machinery exists. |
| J2 | "There is never a candidate pair" for same-name mentions | **PARTIAL — half refuted, substance intact** | Byte-identical `(type, name)` → upstream dict collision (S1), never a pair. But **normalized-equal, differently-spelled** pairs DO form candidate pairs (`cluster.py:151-203` blocking) and are then auto-merged at **identity confidence 1.0** by the exact-normalized-name bootstrap rule (`cluster.py:452-465`: `na == nb and same_ns` → `merge(a, b, 1.0, …)`). Spot-verified. So name-as-identity runs in **two stacked lanes**: exact-string collision at build + normalized-name verdict in the resolver bootstrap. Doc 13 §1 should describe both; the re-key + name-as-recall fix addresses both, so the design's remedy is unchanged — only its mechanics narrative needs the correction. |
| J3 | (Review question, not a doc-13 claim) How is the decision log keyed? | **Split keying; both halves disturbed by the re-key** | Merge accept/reject/split replay **by normalized name** (`hitl/controlpoints.py:86-111` writes names into effects; `resolve/aliases.py:106-156` reads names first, ids as last-resort) — robust to id churn, but premised on names being identity currency. Status overrides / integrity flags replay **by element id** (`view/pipeline.py:599-630`): `idx.get(elid)` → **silently skipped when the id dangles** (spot-verified). No error, no report. |
| J4 | D-13.12 can lean on `/coverage` reporting the unresolved-identity tail | **CONFIRMED** | `api/routes/coverage.py:25-34`, `view/coverage.py:49-51,146-153` — per-type confirmed/probable/possible counts, `collection_gaps` when `(probable+possible)/confirmed ≥ coverage_gap_ratio` (2.0, config). Genuinely built and wired, not aspirational. |
| J5 | Doc 13 §7: relational contribution "already built"; doc 10 D10: relational signal weighted by link status (confirmed > probable > possible) | **PARTIAL — drift** | Shipped as *continuous merge-confidence of completed merges only* (`scoring.py:480-542`, `cluster.py:270-303`): a sub-review (probable/possible) link contributes **exactly 0** — `_neighbours()` keys on the live union-find root, so unmerged pairs structurally never appear as shared neighbours; `identity_status()` is never consulted anywhere. Byte-inert on the frozen corpus per its own commit message. Conservative direction (under-cascades, never over-cascades), but doc 10 D10's take-care (a) as written is not what shipped. |
| J6 | Attribute roles + no value normalization + per-type floors (context for D-13.8) | **CONFIRMED** | `config/resolution.yaml:325-349` roles (`variant.operator_branch` the only critical, currently inert; `unit.alert_posture` the only perishable); `:317-324` states in-config why service_branch/origin_country stay supporting — values compared raw (`scoring.py:99-100`, no normalize on values); floors `auto_merge: 0.85` global, `manufacturer/trading_org: 0.37`. Matches doc 12 §B1 and doc 13's normalization-prerequisite framing exactly. |

---

## 3. Findings (ranked)

### F1 — HIGH — Co-location is being used as a unifier; doc 10 says it must not be. The OOB mission makes this the costliest failure mode.

§6 lever 2's worked example: *"Two provisional units that both field HQ-9/P and both sit at Rahwali share
neighbourhood and cluster."* Doc 10 D10 warns, in its own examples: *"Location is a strong separator but a
weak unifier (a base hosts many distinct units) — used to partition and anchor, not to merge by itself."*
Design + site is exactly the weak-unifier pair: a garrison can host two batteries of the same system, and
merging them **undercounts the adversary's order of battle** — for this use case that is the harmful
direction of error (an analyst told "one battery at Rahwali" when there are two). The same applies
temporally: same design + same site at *different* eras may be rotation through a base, not persistence of
one unit (doc 10 D8's "two distinct entities passing through the same states at different times" — the doc
handles relocation but not rotation).

The doc has the right counterweight in principle ("honest fragmentation is the goal, not forced density")
but the lever-2 example as written encodes the over-merge.

**Recommendation.** Add to §7's evidence model an explicit cap: **shared anchors (design + site + operator)
are recall + graded support that tops out at *probable*; confirming an instance merge requires a unit-level
discriminator** (designation, serial, temporally-witnessed continuity, or analyst confirmation). And make
the residual a first-class coverage item: *"HQ-9/P presence at Rahwali confirmed; unit count unresolved
(1–2 candidate units), designation coverage needed"* — that is the honest OOB answer and a better demo of
the non-negotiable than a tidy merge.

### F2 — HIGH — D-13.11's id story is internally inconsistent, and the migration misses the references that must survive the re-key.

D-13.11 wants the canonical id to be both **"a deterministic function of the cluster"** and **"stable across
rebuilds."** Those conflict the moment cluster membership changes across rebuilds — which is the *point* of
reversal-by-evidence: clusters grow, split, gain their first unique identifier (flipping the id from
derived to id-based), or merge (one id must die). A membership-derived id is deterministic but *not* stable
under evidence evolution.

Why it matters — three classes of reference hang off entity identity, with different requirements. The
verification (J3) shows today's decision log is **split-keyed, and the re-key disturbs both halves**:

1. **Inputs to the pure function (D12): the decision log.**
   - *Merge accept/reject/split decisions replay by normalized name* (deliberately — the code comments say
     ids "would match nothing" in the name-keyed alias index). That survives id churn, but it is premised on
     exactly the thing the replumb abolishes: names as identity currency. Under doc 13, a name-closure only
     buys *comparison* (recall), so a replayed analyst "accept" recorded as a name-alias would no longer
     carry merge authority — analyst authority would silently degrade from verdict to hint. The decision
     effects must migrate to **evidence-layer keys (mention ids / mention-pairs / claim ids)**, which are
     append-only and survive every recompute by construction.
   - *Status overrides and integrity flags replay by element id* and are **silently dropped** when the id
     dangles (`idx.get(elid)` → skip, no error). A wholesale re-key would void every recorded analyst
     override without a trace — the exact opposite of "overrides mutate graph state" (HITL working
     agreement). Two consequences: these decisions also need evidence-layer re-anchoring, and the migration
     needs a **loud-failure guard** (a dangling decision reference is a migration error surfaced to the
     analyst, never a silent skip).
2. **Standing config that references nodes** — user-defined observables watching an entity, subject-lens
   anchor lists. User state, not regenerable fixtures; §12 doesn't mention re-anchoring them.
3. **Regenerable surfaces** — answer key, golden view, cached citations, frontend links. §12 already accepts
   full regen for these. Fine.

**Recommendation.** Decide the id mechanics explicitly in the doc: (a) evidence-layer keys for everything
that participates in recompute — both decision-log halves; (b) cluster ids derived deterministically (e.g.
min-mention-id, or the unique identifier when present) and *allowed to drift* on membership change, with the
rebuild emitting an old→new redirect map for display/provenance continuity; (c) add to §12 stage 4: migrate
the decision log, re-anchor observables and lenses, and make decision replay fail loudly on dangling
references.

### F3 — MEDIUM — D-13.10's design-layer "collapses by name" should be a permissive *policy* on the one earned mechanism, not a second identity path.

As written ("design layer collapses by name but discriminator-walled") it is ambiguous between (a) the same
graded judge run with a permissive per-layer profile, and (b) a structural name-key collapse for
design-kinds. Reading (b) re-imports the substrate bug for one layer and contradicts D1's universality —
design names collide too at real-world scale (export renames like FD-2000 ≡ HQ-9/P are the *alias* problem;
generic names like "Falcon"/"Barak" are the collision problem), and the walls only protect when a
discriminator happens to be *stated* (absence = unknown = collapse proceeds).

The behavioural intent (designs do collapse readily; one HQ-9 node) is right. The mechanism should be:
**same judge, same walls, with a per-layer policy profile under which name+type (rarity-graded per D3, so
BM25 already discounts generic names) alone reaches the merge band for design-kinds.** That keeps one code
path, degrades gracefully to possible/probable on generic-name collisions, and turns "how much does a name
conclude for designs" into a D11 operator dial instead of architecture.

### F4 — MEDIUM — Confirmed-without-unique-id (D-13.9) needs the D8 perishable cap and source-independence made explicit.

D-13.9 is reconcilable with D2 (ids/humans are the only *singly*-decisive signals; corroborated
combinations may still confirm, per D4) — but two guards from the shipped ledger must be stated as applying
to *identity* confirmation, or the instance layer will quietly confirm on weak evidence:

- **Geography is perishable.** "Operator + geo agreement" is perishable-heavy; by D8's cap
  (perishable-only ≤ probable), a confirm must rest on a non-perishable discriminator (designation), a
  temporally-witnessed continuity, or an analyst. The priority list in §7 implies this but never states the
  cap.
- **Independence.** "Enough independent corroboration" should explicitly inherit the corroboration ledger's
  source-independence / too-clean machinery (spine/04) — two derivative reprints of one almanac must not
  confirm an instance merge.

### F5 — MEDIUM — Tier 1 must be allowed to compare *same-document* provisional instances, and the doc should say what source-stated distinctness counts for.

Tier 0 under-binding (coref misses that two mentions co-refer) produces two provisional instances from one
document. If Tier 1 only compares *across* documents, intra-doc fragments can never rejoin — a permanent
fragmentation class created by the design's own grain choice. Conversely, when a source *deliberately*
distinguishes two units ("battery A… another battery…"), that is stated anti-identity evidence Tier 1
should respect. **Recommendation:** Tier 1 compares all provisional-instance pairs including same-doc ones;
a same-doc pair carries a prior *against* merging only when the source syntactically contrasts them
(enumeration, "another", distinct designations), else neutral. Add to the open micro-decisions.

### F6 — LOW — §4's "this *relaxes* the extractor requirement" oversells; the burden moves rather than shrinks.

True for *kind* (layer routing self-corrects). But the design's two biggest levers — Tier-0 coref and
structured discriminators — are both extractor outputs. The load-bearing extraction quality shifts from
kind-tagging (easy) to coreference + discriminator capture (harder). The doc already ranks
characterize-and-cluster as the highest-risk piece; the risk statement should name extraction quality of
coref/discriminators as part of that same concentration, so the eval for the replumb measures it.

### F7 — LOW — Doc 10 §2's "the hard case can't arise" weakens once discriminators can be *derived through* merges; the monotone conclusion still stands.

The monotone-within-rebuild recommendation rested partly on "walls are computed up front from the full claim
set, so a merge can never reveal a hard conflict." With materialized provisional instances, a discriminator
can become visible only *after* a merge (e.g. a unit acquires derived geo via an anchor merge, now
conflicting with a sibling's geo at overlapping time). The right behaviour is unchanged — flag now, split
on next recompute, per doc 10's own fallback — but the frequency argument should be softened and the
flag-then-split path treated as a normal outcome, not a rare corner.

### F8 — LOW — Migration sequencing: stage 2 (endpoint materialization) before stage 3 (coref-cluster minting) creates a transient, known-fragmenting interim.

Endpoint materialization without Tier 0 means per-edge/per-mention provisional instances — the exact
fragmentation §6 exists to prevent. Fine behind a flag for dual-run verification, but say explicitly:
**fragmentation metrics are meaningless at stage 2 and must only be evaluated after stage 3**, so nobody
"fixes" the interim state by loosening merge thresholds (which would then be too loose after stage 3).

### F9 — LOW — §1's mechanics narrative should describe *two* stacked name-as-identity lanes; and §7's "relational — already built" inherits a doc-10 drift.

Two corrections of fact (verification J2, J5), neither changing the design's remedy:

- **Two lanes, not one.** Byte-identical `(type, name)` mentions collide upstream at profile build (the
  dict-key lane, as §1 says). But normalized-equal, differently-spelled mentions *do* form candidate pairs —
  and are then auto-merged at identity confidence 1.0 by the resolver's exact-normalized-name bootstrap
  rule. So the judgment layer is bypassed by the first lane and *overridden by a name-verdict rule* in the
  second. The re-key + name-as-recall fix addresses both lanes at once; §1 should state both so the
  implementation knows to remove the bootstrap verdict rule too, not just the dict key.
- **Status-weighted relational didn't ship as described.** Doc 10 D10's cascade guard ("confirmed links full
  weight, probable less, possible least") shipped as *completed merges only* — sub-review links contribute
  exactly zero to the relational term. Conservative (it under-cascades), so nothing to fix urgently — but
  doc 13 §6's anchor-scaffolding lever assumes relational signal flows through the anchor links, and
  §7 calls relational "already built." True only for merged anchors. Since designs/places resolve cleanly
  (they *will* be real merges), the lever still works; note the drift in doc 10's ledger so nobody counts on
  graded sub-confirmed relational weight existing.

---

## 4. What the doc gets right that's worth protecting during implementation

- The **anchors-first build order** (§6): resolve designs/places/operators before instances. This is D10's
  confidence-ordered staging applied structurally; it is also why F1's cap is affordable — the anchors give
  recall, the discriminators give precision.
- **"Forced density is the name-collapse bug returning"** (D-13.12). This sentence is the north star's local
  form; F1 and F3 are just places where the doc's own examples drift from it.
- **The extractor never decides cross-doc identity** (§10). Any implementation shortcut that lets extraction
  emit a resolved entity id is a regression to the substrate bug via the side door.
- **Holding edges mint no units** (§5.3 contrast). Country-level "Pakistan equips HQ-9/P" staying a
  holding edge — not a phantom unit — is what keeps the instance layer meaning *units*, and OOB counts
  honest.

## 5. Session-2 synthesis (user discussion, 2026-07-24) — resolutions for F1 and F2

### F1 resolved by a two-grain instance layer: **emplacement** (default, site-scoped) + **unit** (earned)

The user's counter-proposal: k reports of a system at one site should aggregate into ONE instance carrying
all the presence evidence, with `count` as an explicit (currently unpopulated) field — and instances
separate *by site*, because the evidence for Nur Khan is physically different from the evidence for
Karachi. This is accepted, with the semantics made explicit:

- **Emplacement node** = "presence of <design> by <operator> at <site>" — the default merge grain.
  Merging k co-location reports into it is SAFE because the node asserts only *presence*, which
  co-location evidence genuinely supports. It never asserts "one unit."
  - Key = design + operator + site. Operator stays in the key (absence = unknown-operator presence node,
    flagged, never fused). Site identity rides the gazetteer/precision ladder (`md/13`): aggregate at the
    stated precision; a district-precision report supports contained sites, it does not pin one.
  - `count` = an **assessed attribute with its own evidence** (imagery TEL count, stated OOB), default
    unknown/≥1. Never derived from number-of-merged-reports (k reports ≠ k units).
- **Unit node** = the movable, designation-bearing individual — identity earned per §7 (designation /
  serial / temporally-witnessed continuity / analyst). Links to emplacements (`present-at` over time).
- This is doc 13 §3's own hierarchy (it already lists both "unit/battery" and "equipment-seen-at-a-site");
  the design just never said which level is the default merge grain. Resolution: **emplacement is the
  default; unit identity is the earned exception.**
- **Relocation** consequently lives at the unit level: "presence ended at X / new presence at Y" is always
  expressible (emplacements); "the unit relocated X→Y" additionally requires earned unit identity — which
  is the honest ladder for the tripwire (fires as *possible relocation, unit unresolved* when identity
  isn't earned). Check the hero relocation beat against this (designation continuity in the corpus should
  earn the unit link; per working-principles the demo doesn't gate the design either way).
- F4 falls out: geography agreement builds emplacements (safe); unit confirmation still requires
  non-perishable discriminators; rotation-vs-persistence is a unit-level question by construction.

### F2 resolved by evidence-layer minting: **mint once at ingest; derive everything at rebuild**

User proposal: mint an opaque unique id (UUID-like) when the bare-minimum referent is identified —
after Tier-0 coref — and treat all identity as same-as/links between ids. Accepted with two precision
rules:

1. **Random minting is allowed only where it is written once into the append-only evidence log.** The
   doc-instance id is minted at ingest (per document-local coref cluster) and stored with the claims;
   rebuild READS ids, never creates them. Anything created during rebuild must be a deterministic
   function (pure-recompute/G1-G2 survive). A rebuild-time UUID would break determinism.
2. **Splits never mint at the knowledge layer.** The knowledge layer is a derived partition over
   evidence-layer ids; a split is just a different partition; a fragment's address derives
   deterministically from its members (e.g. min member id; unique identifier when present). Claim ids
   remain the bedrock below doc-instance ids (a Tier-0 over-bind split partitions the claims).
3. Decisions, walls, observables, lens anchors all reference **evidence-layer ids** (doc-instance /
   claim ids) → they survive every recompute by construction; canonical display ids may drift with a
   derived redirect map. The silent-drop replay path (J3) is replaced by loud failure during migration.

### F6 disposition — mechanism kept; grade + measure the binding

The coref-cluster-mint + discriminator-split + walls mechanism stands (no better alternative identified).
Do it well by: (a) grading Tier-0 auto-bind by coref category (explicit equivalence/apposition binds
tightly; bare pronoun chains held looser — this *is* the open auto-bind-threshold micro-decision);
(b) making coref over/under-binding a measured eval quantity on seeded docs (data pass per doc 12);
(c) noting the emplacement grain shrinks the blast radius of coref errors (same-site fragments land on
the same emplacement regardless).

F3 stands as written (same judge, permissive per-layer policy — not a second path). F7–F9 parked by user
decision; logged here.

## 5b. Session-3 refinements (user, 2026-07-24) — the terminology is wrong; grounding it

The user rejected "emplacement vs unit" as under-defined and pushed on: what IS a unit, is it just count,
do we even have evidence for it, what real evidence shows relocation, and how are sites/granularity
handled. Reworked model:

### The instance layer has two *citizens*, defined by the evidence that creates them (not two arbitrary grains)

- **Presence** (the workhorse; rename of "emplacement"): *operator's <design> observed at <site> during
  <time-window>*. Created by **observation** evidence — imagery, NOTAM/NAVAREA, geolocated photo, news
  sighting. Concrete, sourced, individuated by operator + site + time. This is the default instance and it
  is almost always what open sources actually give you. `count` (how many launchers/TELs/rounds) is an
  **attribute of a presence with its own sourced evidence** (e.g. an imagery TEL count), default unknown,
  never derived from how many reports merged.
- **Formation** (the rare, earned citizen; rename of "unit"): *the organizational individual* — a
  designation-bearing battalion/battery with a chain of command that persists through moves. Created only
  when **organizational** evidence exists: a stated designation ("8th AD Bn"), an order-of-battle
  reference, an order document, occasionally a logistics doc. **We do not force a formation node** — minting
  one without organizational evidence would reify an individual we cannot source (a structural violation of
  the non-negotiable). A formation *threads* presences across time and space.

**So "is a unit just count?" — no.** Count is an attribute of a presence. A formation is the organizational
thread. **"Do we have evidence to count units?"** — equipment counts come from imagery (real, per-presence);
formation counts come from OOB/white-paper/logistics sources (sparse, lower-confidence) — both are sourced
claims defaulting to unknown, never fabricated. If a customs/logistics doc states "N battalions' worth,"
that is a citeable claim, use it.

### Design vs instance — the clean statement

- **Design** = the abstract type: variant, component, radar, manufacturer. Geography-agnostic, operator-
  agnostic, legitimately shared. "What is an HQ-9/P made of / who builds the HT-233" is a design fact.
- **Instance** = a concrete, sourced, operator-bound, located, timed individual: a *presence* (always) or a
  *formation* (when earned). "Where is Pakistan's HQ-9/P / when did it move" is an instance fact.
- The test for which layer a fact lands on: **does the fact change if a different operator fields the same
  design?** No → design (shared). Yes → instance (operator-scoped). This is the operational form of §5's
  layer routing.

### Relocation — the real-world evidence, and the honest ladder

Real relocation evidence is a **chain of presence observations plus (maybe) a continuity signal**, never a
single "relocated" fact:
- dated imagery sequence (present at A on d1 → absent by d2 → present at B by d3);
- a NOTAM/airspace-closure pattern that shifts;
- news reporting a redeployment;
- a designation re-appearing at a new site in an OOB source.

None of these *alone* says "the same formation moved" unless there is **designation continuity** OR a
**temporal-exclusivity** argument (equipment left A exactly as it appeared at B, same operator, plausible
transit — doc 10 D7/D8 succession reasoning). So the honest ladder:
- presence-ended-at-A + presence-began-at-B → always expressible (two presences);
- *possible relocation* → same operator + design + temporal exclusivity, formation unresolved;
- *confirmed relocation* → + designation continuity or explicit transition claim (credibility-gated).

If the corpus lacks such a chain, **synthesize it as a dated-imagery pair (+ optional designation
continuity), not as a magic edge** — the tripwire then fires on the real reasoning, and degrades to
"possible relocation, formation identity unresolved" when continuity is absent. (Check the hero beat lands
on the right rung; per working-principles the demo doesn't gate the design.)

### Sites & location granularity — verified, and the presence/formation split is ALREADY in the ontology

**Major validation.** The presence/formation two-citizen model is not new — the ontology already
deliberately separates the two edges (verified `config/ontology.yaml:146-147`):
- **`observed-at`** (`[variant, component] → basing_site`) = **the presence citizen**: "equipment was seen
  at site Y." The comment says it exactly: *"what a satellite frame … can honestly state is that*
  *equipment* *is at a place, not that a* *named formation* *is based there."* Not functional (equipment at
  many sites at once).
- **`based-at`** (`unit → basing_site`, FUNCTIONAL, `instance_key: [from]`) = **the formation citizen**: a
  named formation based at a site; keyed on the unit so a relocation's before/after co-locate. The comment:
  *"Attributing the occupancy to a unit is a derived inference (ingest/basing.py) that keeps its own, lower*
  *confidence — never fused."*

So the reframe's job is to *name and elevate* a distinction the code already draws implicitly, and to make
formation minting explicitly evidence-gated (derive `based-at` from `observed-at` only when organizational
evidence exists) rather than an ingest-side heuristic.

**Sites & granularity — what exists (verified):**
- A **site IS a gazetteer node** (`config/places.yaml`): `place_id`, `canonical_name`, `kind`,
  `precision_class`, `canonical_dd` coords, `aliases`, `admin` (free-text parent hierarchy string), optional
  `icao`/`locode`, `distinct_from[]`.
- The **precision ladder** exists: `pad | site | terminal | district | city | province`, and a
  `proximity_radius_m` uncertainty envelope per class (`places.yaml:249-255`): pad 500 m … district 5 km …
  province 150 km. `Location` claim values already carry coords + `precision_class` + `resolved_place_ref`
  (`schemas/values.py:183-197`).
- A presence attaches at the **stated precision** (site vs district), and `area_of_operations refines
  basing_site` sub-types coarse "sector/belt/province" mentions so they aren't offered as merge-duplicates
  of sites.

**What does NOT exist (this is the build for the user's "near Rawalpindi → Nur Khan" ask):**
- **No positive place-to-place containment/within edge** anywhere — gazetteer, ontology, or spec. The only
  place↔place relations are `distinct_from` (negative veto) and the `refines` type-refinement. Containment
  ("Nur Khan ∈ Rawalpindi District") lives only as prose in the `admin` string.
- **No query-time proximity or containment reasoning.** The ~7 `graph_*` ASK tools have no geo operator;
  `query_graph` can't ask "within radius" or "near place"; traversal can't climb a place hierarchy because
  the edges don't exist. The one geodesic primitive (`within_area`, `observe/dsl.py:87-102`) is **unwired
  and marked roadmap**, and lives in the observable DSL, not the ASK agent. All spatial logic today is
  **resolution-time** (the `geo_conflict_km` veto and `resolve_place` proximity matching) — building the
  graph, not answering over it.

**The critical doctrine tension the user must resolve deliberately.** The existing system has an explicit,
correct doctrine that a **coarse mention must never pin/merge to a fine site** — `places.yaml` Sargodha
note: *"binding it to an airbase would manufacture the very precision the claim lacks,"* and
`place_identity_precision_classes` bars anything coarser than a terminal from *constituting identity*. The
user's "near Rawalpindi should lend confidence to Nur Khan" is **compatible with this only by separating two
times**:
- **Resolution time (unchanged):** coarse never pins/merges to fine. Keep the trap guard — it protects the
  non-negotiable (no fabricated precision).
- **Query time (new capability):** a coarse presence *may* contribute **graded, explicitly-labelled
  "area-consistent" support** to a question about a fine site — because that is not fabricating precision,
  it is honestly reporting "here is what we have near there, at area precision." The honest answer:
  *"No sighting places PAF HQ-9/P AT Nur Khan. One report places it NEAR Rawalpindi (district precision,
  ±5 km, [date], [source]); Nur Khan lies within that district → area-consistent, not site-confirmed;
  site-precision coverage of Nur Khan is the gap."* THAT is the non-negotiable done well.

**How the linkage works (the user's "is there a linkage, or something else?"):** both, and they are
different relations —
- **"within" (containment)** is best a **materialized linkage**: parse the `admin` hierarchy (or add
  `parent_place_id`) into place-containment edges so the graph can traverse district → contained sites.
  Discrete, traceable, one-click provenance — graph-native, not RAG.
- **"near" (proximity)** is best **computed from coordinates + the `proximity_radius_m` envelope**, not
  pre-materialized (near-ness is continuous). Wire the existing `within_area` geodesic primitive into a
  query-time `graph_*` tool. A district-precision presence has a 5 km envelope; whether Nur Khan's point
  falls in it is a graded, sourced relevance contribution — scaled down as the envelope coarsens.
Together these give the query-time spatial relevance that lets ASK answer at/near questions with cited
evidence and honest precision — the capability that is entirely absent today.

### Location containment — DEFERRED to roadmap (user, 2026-07-24)

The positive place-containment traversal + query-time proximity ("near Rawalpindi lends graded support to a
Nur Khan query") is **deferred**. Rationale: not critical now, and it is **purely additive** — new
place-to-place edges + one new query tool — so deferring costs nothing and it never requires reworking the
rest. **What survives without the build (and must):** the *precision-honest* answer. Because a `Location`
value already carries `precision_class`, ASK can already refuse to overclaim — "we have a district-level
report, not a site fix at Nur Khan" — today. So the **non-negotiable half (never fabricate precision) needs
no new build**; only the *positive cross-precision relevance* (actively surfacing near-evidence for a
site-specific question) is the roadmap item. Nothing in the presence/formation split or the id/decision-log
work depends on it.

### Split IDs — the user is right; only the mechanics need correcting

**Clarifying the confusion (2026-07-24): the word "mint" was overloaded. There are two layers and only ONE
of them mints; the other DERIVES.** Worked on the user's 10-attribute example (one extracted "HQ-9/P"
mention carrying 6 design attrs + 4 instance attrs):

- **Ingest-time minting — once, permanent, layer/identity-BLIND.** At ingest each *claim* (and, with coref,
  each document-local *referent*) gets a stable id written to the append-only log. These are the **atoms**.
  A claim is a claim forever — atoms never split or merge. The 10 attributes become ~10 claim-atoms on
  referent R7; R7 and c31…c40 are minted here, before any layer or identity reasoning.
- **Build-time assembly — every rebuild, deterministic, DERIVED.** The rebuild reads the atoms and *groups*
  them into knowledge nodes. BOTH kinds of split happen here, as grouping decisions:
  - *Layer routing (the §5 straddle split):* the ontology's per-attribute layer tag sends the 6 design
    claims to the shared design node and the 4 instance claims to an instance node. One mention → two
    linked nodes, by sorting its atoms.
  - *Discriminator split (identity):* if two instance referents were grouped but a discriminator conflicts
    (R7=PAF vs R12=PLA), the resolver puts them in two groups instead of one.
  - **The knowledge node's id is a deterministic function of the atoms that grouped into it** (e.g. min
    member-id, or a unique identifier when present) — computed AFTER grouping, never minted before it.

**So the answer to "place the discriminator before minting?":** there is nothing to place it before.
Grouping (layer routing + discriminator checks) happens first; the id is *derived last* from the group. We
never commit a knowledge-id and then have to revoke/re-mint it on a split — that puzzle ("which half keeps
the UUID?") only exists if you assign random ids to groups, which we don't. **Grouping decided first, id
falls out last.** A split is just the atoms landing in two buckets → two fingerprints, each stable and
reproducible across rebuilds.

**Why this also fixes F2:** analyst decisions/walls/observables anchor to the **atoms** (claim/referent
ids — the permanent, minted-once layer), never to the derived node id. So when a grouping re-forms
(merge/split/re-key), the node id may change but the decision still points at real atoms and re-applies —
no silent orphaning. The derived node id may drift; the decision doesn't care because it is anchored below
it. (This supersedes the earlier "mint UUID at the bare-minimum unit, mint two more on split" framing: the
UUID-like stable atom is minted at ingest for the referent; the split needs no new minting.)

After a discriminator split there ARE two distinct knowledge-layer entities with two distinct addresses —
the user's intuition is correct. The only correction: **fresh minting happens once, at ingest**, for each
document-local referent (an opaque stable id written to the append-only log — the "bare-minimum unit we
identify"). The knowledge layer is a **partition of those ingest-ids**; a split is a **re-partition** of
ids that already exist; each resulting entity's address is a deterministic function of its member set
(e.g. min member id, or a unique identifier when present). So:
- you get two IDs after a split — but by **re-grouping existing ingest-ids**, not by minting random UUIDs at
  rebuild (which would break the pure-recompute/determinism gates G1–G2);
- decisions, walls, observables, lens anchors key on the **ingest-ids** → they survive every merge/split/
  re-key by construction (this is the concrete fix for F2/J3's silent-drop).
This *is* the user's UUID proposal, pinned to the one place minting is legal (ingest, in the log).

### BM25 / name — never a verdict, for ANY layer (stricter than doc 13 as written)

User confirms: name similarity is *always* a contributor, *never* a collapse-on-its-own, including the
design layer. This **supersedes D-13.10's "design layer collapses by name"** → **"design layer collapses
*readily* (low corroboration bar) but never on name alone; a name match reaches at most a *possible*
merge."** Even HQ-9 ≡ HQ-9 needs one more signal (shared manufacturer / component / co-citation) — trivially
available, so designs still collapse in practice. **Honest tradeoff to tune with eyes open:** on a bare
corpus where two same-name design mentions share *nothing* else, they sit at *possible* and don't auto-
collapse — mild design-layer fragmentation the use case dislikes. Mitigation: keep the design-layer
corroboration bar genuinely low (one shared component/co-citation clears it) and let the residual sit as a
one-click analyst merge. F3 (one judge, permissive per-layer policy — not a second code path) is unchanged
and now reinforced.

## 5d. observed-at / based-at — code investigation + §5.3 reconciliation (2026-07-24)

User asked what `observed-at`/`based-at` are in the running code, whether based-at is *derived*, and whether
a past confusion caused trouble. Verified (opus agent, receipts):

- **based-at IS derived from observed-at.** `ingest/basing.py` mints `<unit, based-at, site>` as an
  `kind="inference"` claim from an `observed-at` sighting **+** an `inducted-into` formation link, citing
  both as premises, carrying its own lower, **un-promotable** confidence (shares an independence group with
  its premises), tagged `derived_layer="unit-attribution"`. It never relabels the sighting. Gated by
  `_is_locatable_site` (needs a resolved place or coords — blocks provinces/"sectors" from becoming bases)
  and `max_units_per_site: 1`.
- **The past confusion was real and is FIXED.** The imagery VLM lane used to emit `<site, based-at, variant>`
  — wrong type *and* direction — asserting a *formation-basing* fact off a pixel read that only supports an
  *equipment sighting*. Re-laned to `observed-at` (`imagery.py:69-74`, EVAL RCA §2.3 / D-P4.2). Also the
  older "don't extract basing at all" decision (D-2.7) left the edge *unowned*; replaced by this two-layer
  observed/attribution model (D-P4.1/2/3).
- **The derivation is OFFLINE-only.** Runs only via the `python -m chanakya.ingest basing` CLI; NOT in the
  live keyed-ingest route and NOT in `rebuild()` (forbidden by G1 as currently written). based-at appears in
  the running app only because the CLI output is frozen into `__basing.json` seed bundles loaded at boot. A
  freshly-ingested live doc gets its sighting but **no** derived basing. (Matches [[live-tripwire-variance]]
  and [[rca-phase4-audit]].)
- **Functional-key fusion risk (documented, not silent).** `based-at` is functional keyed on the unit alone
  (`instance_key:[from]`), so all of a unit's derived bases collapse onto ONE edge instance — which is what
  makes supersede fire the Rawalpindi→Rahwali relocation. Correct for the single-relocation corpus, but two
  *simultaneous* live sites for one unit would manufacture a false relocation. Flagged as the "sub-scope
  limitation" (`ontology.yaml:40-46`) and pinned by `xfail` (`test_supersede.py:269-279`).

**§5.3 reconciliation (done).** The worked example used "HQ-9/P **based-at** Rahwali" as the *extractor-stated*
trigger that materializes a unit — inconsistent with both the code (extractor emits `observed-at`; based-at is
derived) and the new §3a/D-13.13 (observed-at = presence; based-at = earned formation; never force a formation
from a bare sighting). Rewrote §5.3: a sighting materializes a **presence**; a **formation** (unit) is
materialized only when `inducted-into` evidence earns it, at which point derived based-at binds it — and noted
the replumb makes this a first-class **rebuild-time** derived binding (D-13.6), retiring the offline pre-freeze.

**Consequence worth flagging to the build:** the current relocation demo leans on the functional-key *collapse*
(a mechanism-level trick). The replumb replaces it with the honest §6 ladder (presence chain + formation
continuity + temporal reasoning), which also **dissolves the fusion risk** — two simultaneous presences stay
two presences; a relocation is an earned formation-level inference, not a key collision. So the xfail sub-scope
limitation is *fixed by* the replumb, not merely inherited.

## 5e. Stated vs derived based-at — the ORBAT case (user smell, 2026-07-24)

User flagged: some sources (ORBAT / military-balance / official statements) directly state a *named unit at
a site*, not just equipment — so is based-at only ever derived? Verified (opus agent, receipts):

- **based-at IS extractor-emittable and the stated path already works.** `based-at` is `extractor: true`
  (`ontology.yaml:146`), in the live extraction enum built from `extractor_edges()` (`extract.py:1739-41`).
  A stated unit-at-site is emitted directly as `based-at`, `kind=observation`, premises `[]`. Re-laned to
  `observed-at` only when the subject resolves to *equipment* (a variant/component) rather than a unit
  (`ontology.py relane()`; happened on d21).
- **The corpus already has one** — `d19` states "PAF/Army Air Defence Command HQ-9BE battery … at Rahwali"
  (`kind=observation`). Same site *also* carries a *derived* based-at (`kind=inference`) from its own
  sighting + `inducted-into`. Gap: no crisp numbered-battalion ORBAT ("8th AD Bn garrisoned at Nur Khan"),
  so the stated path is barely exercised — corpus gap, not code gap (filed to doc 12 §B6).
- **Stated vs derived confidence is correctly distinguished.** Same credibility formula, keyed on source
  (`scoring.py:331-342`). A *stated* based-at is its own independent group → can reach *confirmed* with one
  more independent look. A *derived* based-at (`kind=inference`) shares an independence group with its
  premises (`independence.py:16-17`) → one look, capped at *probable*; plus decoy flag carried forward and
  single-pass basing hard-capped (`credibility.yaml:50-53`).
- **"only derived" is a documented ASSUMPTION, not a code rule.** Three comments (`basing.py` docstring,
  `ontology.yaml:147`, `credibility.yaml:154-160`) assert "no source states basing" — the D-2.7 premise,
  superseded by the D-P4 two-layer model. The code never enforces it. → should be corrected to
  "formation-at-site is *usually* unstated, so derivation is a fallback." (Offered to the user; code-surface
  edit, not done unilaterally.)
- **No free pass for "stated."** The grade-E d20 spoof produces only low-grade sighting *events* (no
  relationship claim today), lands at *possible* (below the 0.50 probable floor), and would be walled by the
  supersession floor (`credibility.yaml:60-69`) even if it emitted a based-at. Stated only means "own
  independence group," never "exempt from source grade / deception gates."

**Edits made:** §5.3 broadened to describe BOTH provenance paths (stated stronger, derived fallback, stated
≠ trusted); D-13.13 given the two-provenance clause; doc 12 §B6 records the ORBAT corpus gap. My earlier
§5.3 rewrite had narrowed based-at to the derived path only — this corrects it. **Open (user's call):**
correct the three stale "no source states basing" code/config comments.

## 5f. Implementation plan — drafted; pending one combined revision pass (2026-07-24)

Plan authored at `artifacts/plan/01-replumb-implementation-plan.md` (master-style; 9 sessions RK-SPIKE / RK-BAKEOFF /
RK-ATOMS / RK-LAYER / RK-COREF / RK-NAMECUT / RK-MATERIALITY / RK-DATA; contract-amendments A1–A7; gates G13–G17;
bake-off as an early contract-first stage). Two inputs feed ONE combined revision (do not edit the plan mid-review —
keep the reviewers' basis stable):

1. **Adversarial review findings** — workflow `replumb-plan-review` (5 dimensions: vs-spine-13, vs-locked-decisions,
   implementer-completeness, bake-off-soundness, gates-sequencing). Apply verified findings.
2. **Self-sufficiency requirement (user, 2026-07-24):** the plan must be runnable to KICK OFF a stage with the
   orchestrator+subagent setup, with code + design references as needed. Add in the revision:
   - A **"Running a stage (orchestrator + subagents)"** section: read-first → spin thin `sessions/RK-*.md` → worktree
     `wt-RK-*` → dispatch the three hands as **opus** subagents (implementer corpus-blind, independent test author,
     independent data hand; orchestrator stays lean, reads conclusions not raw files) → verify (abstract unit tests +
     dual-run + predict-then-verify; orchestrator spot-checks) → commit each sub-stage + PROGRESS/DECISIONS + five-beat
     handoff. Plus a kickoff checklist.
   - **Per-stage "Read first (design + code)"** line on every RK-* stage (spine/13 §§, DECISIONS rows, and the concrete
     code files/anchors) — mirroring the repo's session "Design docs to read first" field.
   - **Appendix A — Code reference index**: the enumerated mint sites, name-address sites, atom mint/thread sites, and
     exists-off-vs-build-new lists (from the replumb-surfaces brief), so a subagent has the concrete anchors without
     re-deriving. Source briefs saved at `scratchpad/briefs/` this session.

## 5g. Plan — two review rounds applied; FINAL (2026-07-24)

`artifacts/plan/01-replumb-implementation-plan.md` (735 lines) is drafted, twice-reviewed (5-dimension adversarial
workflow each round), and revised. Round 1 (on the first draft): 7 high / 12 med / 11 low — the load-bearing catches
were basing-into-rebuild violating G17 (3 reviewers converged; verified against `basing.py:357-366`), the abstract
golden NOT surviving the re-key (A5 changes rebuild's id-derivation code; verified golden ids + gates g5/g10/g12),
and per-attribute layer needing a `config_models.py` schema change (`attrs: list[str]`). All folded via the
adjudicated revision spec. Round 2 (on the rewrite): 1 high / 7 med / 14 low — mostly renumbering artifacts from
inserting the new §6, plus two substantive items:
- **D-13.15 amended** (the one high): the plan's A6 (human config anchors on stable handles, not atoms) contradicted
  D-13.15 as written (atoms for everything). The plan's split is the better design, so **D-13.15 + spine/13 §8 were
  amended** to carve out the config-anchor case; A6 now cites "D-13.15 as amended." Logged here; a formal DECISIONS
  entry rides RK-NAMECUT's F0-amendment (A6).
- **G17 non-vacuous:** the golden has no `observed-at`+`inducted-into` pair, so a monkeypatch-and-run G17 never enters
  the derived-basing branch → the gate could pass vacuously. Fixed: the G17 fixture must include such a premise pair
  (or a static call-graph scan); phasing annotated (no-mint clause binds S2, id-from-atoms binds S4).
All other round-2 fixes (§6→§7 cross-ref, "Eight sessions", §3 ownership↔owned-paths reconcile, RK-COREF read-first
+spine/13 §6, RK-LAYER read-first +§3a, ontology.yaml de-contended, A2 S1/S2 split, G13 quote-anchored scan,
Appendix A anchor retarget, §8 stale-meta) applied. Consistency sweep clean.

## 6. Open items I agree are open (no change requested)

- Tier-0 auto-bind threshold (the doc's own top micro-decision) — F5 adds its flip side.
- Discriminator priority for cross-doc clustering — F1/F4 add the cap; ordering itself looks right
  (designation > operator+geo > relational > name-as-recall).
- Characterize-and-cluster of provisional instances as the highest-risk piece — agreed; F6 folds extraction
  quality into it.
