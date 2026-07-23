# Resolution redesign for the real world — decisions, reasoning, and the one open fork

**Status:** design proposal, not implemented. Captures the decisions from the "resolving-the-real-world"
design conversation. Grounded in the *verified* current behaviour of `backend/chanakya/resolve/` (read
from code, not from the older design MDs, which are stale in places). Nothing here changes the running
system yet; it is the agreed target we plan *toward*.

**How to read this:** §0 is the north star — the abstract why that every decision below serves. §1 is the
decision ledger; each entry states the decision, the abstract why, the backbone reasoning, the examples we
cited and how they play out under the new model, and what to take care of. §2 is the single decision we
left open (the Support-5 fixpoint question) with a recommendation and the reasoning behind it. §3 is the
list of things deliberately parked for implementation planning so they don't get lost.

---

## 0. North star / agenda

**Resolve identity the way an intelligence analyst does** — from evidence, held to the same evidentiary
standard as any other assessment, with a human in the loop, traceable to source, reversible by new
evidence, and honest about what it does not yet know. **Design the mechanism for that discipline, not for
the corpus currently in hand.**

Five commitments fall out of that, and they are the yardstick for every decision:

1. **Identity is an evidence problem, not a string-matching problem.** A merge is an assessment. It earns
   the same *confirmed / probable / insufficient* treatment the system already applies to facts. A name is
   a weak clue, never a verdict.
2. **Certainty is reserved for signals that genuinely carry it.** A globally-unique identifier or a
   human's confirmation can be decisive; a name, an acronym, a fuzzy string match cannot — they are graded
   evidence that must be corroborated.
3. **Hard constraints are mechanism, not tuning.** Two things that provably cannot be one entity must be
   kept apart by a rule that no similarity score can cross — and that rule should be *declared over
   attributes and computed from data*, not maintained as a hand-listed set of forbidden pairs.
4. **The data model must carry time.** Most "contradictions" in open-source intelligence are stale facts
   under fresh datelines, not two different entities. Without a notion of *when a fact was true* (distinct
   from *when it was reported*), the system cannot tell an update from a disagreement, and will
   systematically shatter entities that merely changed.
5. **Policy is the operator's, not the algorithm's.** How aggressively to merge, and how much corroboration
   to demand, depends on how much data the organisation can get and how much risk it will accept. The
   algorithm exposes those as dials and *surfaces the cost of each setting*; it does not bake one choice in.
   Where identity is unresolved, that is a **collection gap to report**, not a failure to hide.

Two architectural invariants underpin all of it: resolution is a **pure function of the accumulated
evidence log plus the decision log, recomputed on each rebuild** (so every partition is explainable and
reversal is just "new evidence + recompute"); and **persistence and scale are separate, deferrable concerns**
that must not shape the algorithm.

---

## 1. Decision ledger

### D1 — The alias table is a recall device, not an identity verdict

**Decision.** The alias-name surface becomes a way to *guarantee two mentions get compared* (a recall /
blocking device). The entity **registry** — keyed by stable ids — is the identity store. Scored resolution
is the bridge between them, and a *confirmed* merge writes its elected id back into the registry, growing
it. Membership in an alias class buys a comparison; it never buys a merge.

**Why (abstract).** Recall and precision are different jobs and must not be fused. "Worth comparing" should
be generous; "decided identical" should be earned.

**Backbone.** Today the alias index is a *normalised-name equivalence closure* that is treated as **certain
identity**: being in the same name-class both triggers a confidence-1.0 merge and forces the name sub-score
to a perfect 1.0, bypassing everything else. That is the conflation. Splitting it means the name-class only
feeds candidate generation; the merge decision comes from the graded score and the corroboration ledger
(D4).

**Examples.** *FD-2000 ≡ HQ-9/P*: under the new model, alias membership still guarantees the pair is
compared, but the merge is earned by the evidence, not granted by the membership. A human-confirmed
id-alias (someone vouched for it) may still be near-certain — it is a *decision*, not a string coincidence.

**Take care.** Preserve the legitimate strong case: analyst-confirmed and curated id-level equivalences are
allowed to stay high-confidence, because a human or curator stood behind them. It is *name-equivalence-as-
automatic-certainty* that is demoted, not the registry's authority.

---

### D2 — Certainty is reserved for high-discriminating keys; names are graded evidence

**Decision.** Only two things can drive a merge to **confirmed** on their own: a shared **unique typed
identifier** (each entity type declares its identifier kinds — hull number, ICAO, LOCODE, contract number,
serial), or a human-confirmed id-alias. Name similarity, containment, and acronym expansion become weighted
*contributors* to the score, never verdicts.

**Why (abstract).** Discriminating power should determine how much a signal is allowed to conclude. A key
that is globally unique to one entity can conclude; a name that thousands of entities can share cannot.

**Backbone.** Names are the least discriminating and most collision-prone signal, and they get worse at
scale. Containment and acronym are the sharpest offenders — acronyms collide across many organisations, and
"one name is the other plus a descriptive word" catches endless near-misses. The current code defends this
only by *hand-excluding* dangerous generic names from the seed; hand-exclusion does not scale, so the
grading has to be structural.

**Examples.** *"3rd Battalion" ⊂ "3rd Battalion, Signals"* and *acronym collisions* stop being certain
merges and become weak positive evidence that must be corroborated. *A shared hull/ICAO/contract number*
stays decisive. *PAAD ⊂ "Pakistan Army Air Defence"* still generates the comparison (an acronym shares no
token with its expansion, so blocking must still propose it) but now has to clear the evidence bar to merge.

**Take care.** Per-type declaration of identifier kinds needs building (the machinery exists in code but is
switched off). **Absence of an identifier is never a conflict** — a mention that simply doesn't state an id
is *unknown*, not *different*.

---

### D3 — BM25 over indexed names for specificity-weighted name similarity

**Decision.** Use BM25 across all indexed names as the name-similarity contributor. Its IDF term
auto-weights by rarity: a shared rare designator scores high, a shared generic word scores near zero.
Alias-membership and exact-name still *guarantee the comparison* regardless of the score they then add.

**Why (abstract).** "How discriminating is this shared token?" should be measured from the corpus, not
curated by hand. BM25's IDF is exactly that measurement.

**Backbone.** It is deterministic, needs no hand-tuned stop-lists, and fits the stack (BM25 is already the
retrieval primitive; no runtime embeddings). It operationalises D2's "grade names by discriminating power"
for free.

**Examples.** A rare shared designator → strong contribution; a shared *"Command"*, *"Battery"*, *"Corp"* →
near-zero, so two unrelated units that merely share a generic word do not accumulate spurious name support.

**Take care.** Keep the two roles distinct in the implementation: *membership/exact-name → triggers the
look*; *BM25 → contributes to the decision*.

---

### D4 — Identity is an evidence-backed hypothesis (the spine)

**Decision.** A merge is a **hypothesis with its own corroboration ledger**, resolved the same way facts
are (the bi-level architecture — evidence layer → knowledge layer — applied to identity itself). Three
statuses:

- **possible** — compared and scored, held as a latent link, *kept off the analyst's desk*;
- **probable** — enough corroboration to be worth a human — a candidate `same-as` edge (HITL);
- **confirmed** — independently corroborated — a strong `same-as` edge that also collapses the view, with
  the edge retained underneath for audit.

**Why (abstract).** The system already knows how to say "one source = probable, two independent sources =
confirmed" for facts. Identity deserves the same discipline. This is **merge corroboration, not assertion
corroboration**: the merge accumulates *its own* evidence that two profiles co-refer, separate from whether
any fact about them is true.

**Backbone.** Making identity graded is also the antidote to fragmentation: the unresolved tail no longer
has to be either a false merge or a lonely singleton — it lives as honest **possible** links the analyst
can see but isn't pestered by.

**Correction banked (important).** A name match alone reaches only **possible**, *never* probable. If name
matches went to HITL, every name collision would flood the analyst and destroy triage. Probable must be
earned by more than a name.

**Examples.** *Two clusters of what is really one unit* stay apart until a **bridge** mention shares
identity-evidence with both; the bridge raises the *merge hypothesis*, and its strength decides
possible/probable/confirmed.

**Take care.** **Cluster size/strength is never identity evidence.** A big, well-corroborated cluster is
not thereby more likely to be the same as another cluster. Growth only increases the *surface area* for a
future bridge to match against; the merge still keys on the bridge, not the growth.

---

### D5 — Cannot-links as declarative attribute-incompatibility (hard walls by mechanism)

**Decision.** A **stated** conflict on a **declared-critical attribute** (e.g. country, entity type, a
unique identifier) is a hard veto: computed from the data, enforced *before* any scoring, and transitively
(it blocks A–C–B fusion, not just A–B). It replaces the hand-listed forbidden-pair lists as the primary
mechanism.

**Why (abstract).** Two things that provably cannot be one entity should be kept apart by a rule no score
can cross — and that rule should generalise from declared attributes, not be maintained pair by pair
(pair-lists don't scale).

**Backbone.** The current hard-wall mechanism is genuinely solid — the veto guard runs before scoring at
every stage and beats a perfect name match, an alias hit, an analyst-accepted merge, and even a source's
own `same-as` claim, and it is transitive. But the only *attribute-driven* walls today are geographic
coordinates and one name-pattern identifier; **a stated country difference is not a wall** (it only stops
co-comparison), and neither is a type difference. Generalising the wall to declared critical attributes is
the missing piece.

**Examples.** *China HQ-9 vs Pakistan HQ-9/P* becomes a genuine wall (stated different countries → cannot
be one entity), not merely two things that never get compared. *Two points 1000 km apart* is already walled
by the geographic veto — this decision generalises that instinct to non-geographic critical attributes.
*Port Qasim vs Karachi Port* (curated distinct places) is the pattern being generalised away from hand
curation.

**Take care.** (a) A **credibility floor** on the vetoing claim — one flaky low-grade source must not be
able to shatter a well-corroborated merge; below the floor it only raises a flag, it does not wall. (b)
**Absence ≠ conflict** — a silent side never triggers the wall. (c) The *bridge-across-a-wall* case is its
own decision, D9.

---

### D6 — Attribute roles: critical / supporting / neutral

**Decision.** Every attribute is declared (per entity type) into one of three roles:

- **critical** — a stated disagreement is a hard veto (feeds D5);
- **supporting** — agreement raises identity confidence; disagreement is soft negative evidence or a
  reason to route to a human, never fatal;
- **neutral** — no bearing on identity; and when neutral values conflict, **both are retained with
  provenance** rather than one being silently dropped.

**Why (abstract).** This is exactly the "identity-critical vs identity-neutral" whitelist/blacklist idea —
made explicit, per type, and configurable.

**Backbone.** The framework for this already exists in the code (attribute-level identity / conflict rules,
a conflict penalty) but is **populated in no config file, so it is inert on the real corpus**. So this is
largely *turn-on + policy + harden the one soft path into a real wall for the critical subset*, not
build-from-scratch. The neutral-conflict-retained rule also fixes a current bug: today a later conflicting
value is silently dropped (first-claim-wins) and never even shows on the node.

**Examples.** *Manufacturer / range-class* as supporting: a disagreement lowers confidence and can prompt
review but doesn't wall. *Country / type / serial* as critical. *A nickname or free-text descriptor* as
neutral: keep both, never let it affect identity.

**Take care.** A rigorous, per-type definition of what is critical vs supporting vs neutral — and of what
counts as **non-perishable** — is deliberately parked for implementation (§3); it is not global and likely
not strictly binary.

---

### D7 — Temporal validity + value history (the enabling primitive)

**Decision.** Every attribute and relationship value carries **both** a *reporting date* (always available
— when the source said it) and, where stated, a *validity interval* (when the fact was actually true).
Reporting date is treated as an **upper bound** on validity, not as the truth. Nothing is overwritten —
prior values are **retained**, so the knowledge graph becomes a timeline of the entity.

**Why (abstract).** Without time, "conflict" and "update" are indistinguishable, and the system will
over-split every entity that simply changed. Reporting-≠-validity is precisely what lets a disagreement be
read as *possible staleness* instead of *contradiction*.

**Backbone.** Generalises the one place the system already does this — the relocation trick, where a unit's
old and new basing sites are modelled as co-objects of a single relationship instance so a move reads as
anti-identity evidence rather than two entities — to attributes in general. Retained history is also a more
valuable intelligence product in its own right (you can ask *where was this unit in 2019 vs 2023*).

**Examples.** *"Based at X (2019), based at Y (2023)"* → one unit relocating, an update, not two units. *A
2024 reference almanac listing a 2021 location it never re-verified* → a stale field under a fresh dateline,
not a contradiction with a 2023 imagery report.

**Take care.** The reporting-vs-validity distinction is load-bearing for the entire update/stale framework
(D8). Building it half-way (dates but no validity intervals) would quietly collapse back into "reporting
date = truth," which is the bug.

---

### D8 — The update / stale two-cluster decision framework

**Decision.** When two clusters look like one entity split across time:

- Distinguish **perishable** attributes (location, status, posture — expected to change) from
  **non-perishable** ones (designation, maker, serial — shouldn't).
- The **overlap window** (the period both clusters are observed) is a **signal, not a gate**:
  - overlap *agreement* → positive corroboration;
  - overlap *disagreement on a non-critical attribute* → **soft negative evidence, weighed against the
    commonality**, never a standalone separator (it is very often just a stale field);
  - overlap disagreement on a **critical** attribute → the D5 hard veto (unchanged).
- A **bridge** mention that carries a stale-side value *and* a fresh-side value:
  - if it is **temporally aligned per attribute** (its stale field dated to the older cluster's era, its
    fresh field to the newer) it internally witnesses the transition → toward **confirmed**
    (credibility-gated);
  - if it is all under a **single current dateline** with mixed values → genuinely ambiguous → **probable /
    HITL**, with the exact posture left to operator policy.
- **Non-perishable agreement, or an explicit transition claim, can reach confirmed.** **Perishable-only
  overlap can at most reach probable/HITL** — it must not auto-confirm.

**Why (abstract).** Real sources report at different latencies and mix fresh and stale content under one
dateline. A disagreement is therefore weak evidence about identity, not proof of difference; and a single
source that witnesses a *transition* is unusually strong evidence of continuity.

**Backbone.** The discriminator is not "is there a contradiction" but **"is the contradiction on a critical
attribute (→ hard) or a perishable one (→ soft, possibly stale)"** — which is why this decision needs D6
(roles) and D7 (time) underneath it. Perishable-only cannot confirm because *"two distinct entities that
passed through the same states at different times"* is a real and common false-merge mode (a base hosting
different units over the years).

**Examples and how they play out.**
- *Stale field, fresh dateline* (2024 almanac location vs 2023 imagery): heavy commonality dominates; the
  location disagreement is a small negative and actually flags the almanac as stale. → stays merged /
  toward confirmed.
- *Genuine two entities* (two "3rd Battalion" in different corps): the disagreement is on **parent
  formation / a stable identifier** (critical) → the D5 wall holds. → separate.
- *Source update-lag* (fast news vs slow registry): soft negative, ultimately a *source-latency* property,
  not an identity one. → weighed, not decisive.
- *Deception* (deliberately false current location): credibility floor + HITL — a low-trust contradicting
  claim moves the merge little and surfaces to a human.

**Take care.** Keep the **explicit-transition claim (strong)** distinct from a **mere perishable
coincidence (weak)** — they have very different reliability. Everything ambiguous is credibility-gated and,
where policy-dependent, configurable (D11).

---

### D9 — A bridge across a wall is a top-priority HITL alarm

**Decision.** A mention that bridges two clusters which are **vetoed apart** can never auto-merge them —
the wall holds — but the bridge itself is **actively surfaced as a high-value analyst signal**.

**Why (abstract).** A wall shouldn't merely mean "silently don't merge." Something trying to cross a hard
wall is exactly what a human should see: either the wall is wrong, or the bridging mention is a conflation /
extraction error, or it is deliberate deception. Turn the wall into an alarm.

**Backbone.** The transitivity machinery already refuses the union; this decision adds the *surfacing* —
the refused straddle becomes an adjudication item rather than a silent non-event.

**Take care.** This is the one place a hard veto produces analyst work by design; keep it rare and
high-signal (gate it on the bridge carrying real corroboration to both sides, not on any incidental
touch).

---

### D10 — Staged, confidence-ordered resolution, run to a fixpoint

**Decision.** Resolve in evidence-strength order, iterated to a fixpoint: **walls first → unique-id merges
→ strong anchors (e.g. location) → the collective/relational step over the now-trusted core → the residual
left as graded `possible` hypotheses.** The whole pipeline loops until a full pass changes nothing (merges
beget merges, because a new merge can create the shared neighbour that licenses the next).

**Why (abstract).** Establish the confident core from the most reliable evidence first, then attach the
ambiguous tail against a partition you can trust. This mimics how an intelligence association team works —
nail the certain core, keep the ambiguous rest on a watch-list.

**Backbone.** It also fixes a latent bug in today's design: the relational/collective step recomputes
"do these share neighbours" against the *current* partition, which was seeded by the name/alias bootstraps
— so if those over-merged, the relational signal is computed against a polluted graph and errors cascade.
Seeding the core with reliable evidence first makes the relational signal trustworthy at the moment it is
used.

**Examples.** *Location* is a strong **separator** (different confirmed coordinates → not the same — the
existing geo veto) but a weak **unifier** (a base hosts many distinct units), so it is used to *partition
and anchor*, not to merge by itself.

**Take care.** Two things. (a) **Weight the relational signal by link status** — a `confirmed` link carries
full relational weight, `probable` less, `possible` least — so a weak over-merge can't cascade certainty it
didn't earn. (b) The fixpoint's termination guarantee is the open decision in §2.

---

### D11 — Operator-configurable policy + coverage-gap output

**Decision.** The possible/probable/confirmed thresholds and the overall merge-aggressiveness are **policy
dials** that encode the organisation's data richness and risk tolerance. Unresolved identity is surfaced as
a **collection gap** ("we need more data on these entity types"), and the **cost of each dial setting is
made visible** (how many links left at possible, how many confirmed merges a stricter operator would have
questioned).

**Why (abstract).** A large agency with broad collection (think RAW) can afford to demand more corroboration
before merging; a smaller shop with thin data cannot. The algorithm must not bake one posture in. And a
system that *reports what it can't yet resolve* is doing an intelligence job (driving collection tasking),
not failing.

**Backbone.** This ties into the system's existing "adaptation = freshness / coverage" idea: unresolved
identity is a freshness/coverage signal, not noise. **Retraction banked:** the earlier framing of
fragmentation as "a problem to fix by merging more" was letting the current sparse corpus dictate the
algorithm — it is withdrawn. Strictness is a dial; the design's job is to make its cost legible.

**Take care.** Enumerate the full set of analyst-driven knobs worth exposing during implementation (§3);
don't invent dials without a decision behind them.

---

### D12 — Architecture invariant: pure-recompute semantics; persistence orthogonal; scale deferred

**Decision.** Resolution **semantics** are a pure function of the accumulated evidence log plus the decision
log, recomputed on each rebuild. **Persistence** (saving the grown state to disk for the next boot vs.
rebooting from a seed) is an orthogonal concern — a demo/infrastructure limitation, not an algorithm one.
**Scale** (making the recompute incremental so it doesn't re-resolve the whole graph per ingest) is a real
but **separable** concern, deferred until we are near that problem.

**Why (abstract).** Capability first. Deferring scale is *safe precisely because* we keep pure-function
semantics now: the later incremental implementation is then a drop-in optimisation that must produce
bit-identical results — never a redesign.

**Backbone.** The one discipline to hold while building capability: **do not let any capability depend on
mutable, in-place cluster state that a from-scratch recompute couldn't regenerate.** Hold that line and
scale stays a later, independent problem. Reversal is always "append new evidence / a decision, then
recompute," never an in-place undo.

**Take care.** When scale work eventually happens, keep "incremental" strictly a performance optimisation
(bounded re-resolution blast radius, deterministic, identical result) — never stateful online mutation.

---

## 2. The open fork (Support 5): what a merge-revealed contradiction does inside a rebuild

The staged pipeline (D10) loops to a fixpoint. The question we left open: when a merge, *after it happens*,
reveals a contradiction, does the loop **undo that merge mid-pass (within-rebuild backtracking)**, or does
it stay **monotone within a rebuild** — merges only grow, and a revealed contradiction becomes a *flag* now
and a *split on the next rebuild*?

**Recommendation: monotone within a rebuild, with no general backtracking.** Reasoning, against the north
star:

- **The hard case can't actually arise, so backtracking buys almost nothing.** All hard walls (D5) are
  computed up front from the full claim set and enforced *transitively before any soft merge* — so a merge
  can never place a wall-violating pair into one cluster in the first place (the union is refused, including
  the A-silent-B, C-conflicts-A straddle). That means the only contradiction a merge can *reveal* mid-loop
  is a **soft** one (a perishable or supporting-attribute disagreement) — and by D8 those are never
  separators anyway, just negative evidence. There is no case that *requires* an undo.

- **Monotone guarantees termination and determinism for free.** Clusters only grow and statuses only
  strengthen within a rebuild, so the fixpoint is a finite monotone climb — it always terminates, and it
  terminates at the same place regardless of evaluation order. Backtracking turns resolution into a search
  that can oscillate (merge A-B enables C; C reveals tension; undo A-B; C loses support; redo…), which then
  needs a strictly-decreasing energy function or a priority order to converge — the territory of approximate,
  often stochastic, joint inference.

- **The properties we'd sacrifice are the load-bearing ones.** Within-rebuild backtracking makes the final
  partition the output of a search-with-undo, so "why are these merged / not merged" can no longer be
  explained by *listing the evidence* — you'd have to replay the search. That directly threatens the
  non-negotiable (one-click traceability to source) and the clean confirmed/probable separation, and it
  fights the keyless-deterministic invariant. A marginal, automatic gain (resolving a soft contradiction one
  rebuild-cycle sooner) is not worth eroding auditability, determinism, and reversal-by-evidence — the exact
  properties an intelligence system is judged on.

- **The monotone behaviour is the *right* behaviour, not a compromise.** A merge that later looks tense
  becomes a **visible flag on the cluster** and routes to a human; the split, when warranted, happens on the
  next recompute driven by new evidence or the analyst's decision — which is precisely
  reversal-by-evidence. A flagged, human-visible tension is honest and in-the-loop; a silent automatic undo
  is neither.

- **The real cascade safeguard is status-weighting, not backtracking.** The thing to actually protect
  against — a weak over-merge lending false strength to the next merge — is handled by D10's rule that the
  relational signal is weighted by link status (`possible` links carry little weight). That contains
  cascades at their source, without any undo machinery.

**Net:** adopt monotone-within-a-rebuild. If a genuine need for late correction ever appears, the only
principled exception would be a narrow, deterministic un-merge that fires *solely* to enforce a hard wall
(a monotone constraint that cannot oscillate) — but the analysis above says even that can't be triggered
mid-loop given up-front transitive veto enforcement, so we should not build it speculatively.

---

## 3. Parked for implementation planning (so it isn't lost)

- **A rigorous taxonomy of attribute roles and perishability** — critical / supporting / neutral, and
  perishable / non-perishable — defined **per entity type** (not global, likely not strictly binary; some
  attributes change only monotonically).
- **Richer trajectory intelligence** on perishable attributes (using an entity's own history and typical
  change rates) beyond the "stitch into one consistent trajectory" rule.
- **Source latency / freshness priors** — modelling that a "slow" source's *current* data may be stale (the
  update-lag scenario), so overlap disagreement can be discounted by source type.
- **The full analyst-knob inventory** for D11 — which policy dials to expose, with a decision behind each.
- **The scale/incremental recompute design** (D12) — bounding the re-resolution blast radius while keeping
  identical, deterministic results — when we are near that problem.
- **Turning on and hardening** the dormant attribute-conflict framework (D6) — populate config, and promote
  the critical subset from a soft score penalty to a real wall.
