# RK-SPIKE — adversarial review verdict & the closures it forces

**Status: reviewed (2026-07-25).** A multi-agent adversarial review of the spike's own output: 12 blind-case
triage verdicts (each attacked by an independent skeptic — **3 overturned**), plus six review dimensions
(decisions · defect register · case suite · gold slice · docs · the implementer's challenges), with every
high/critical finding put through a refutation pass. 39 review agents completed; the synthesis below is the
orchestrator's, written from the run journal.

**Headline: the spike achieved its purpose, and the review's most valuable output is that it broke three of
the orchestrator's own artifacts.** The three micro-decisions are closed and hold up. But the review found
(i) **three bugs in the orchestrator's own matcher** — one of which made the reported score wrong, (ii) that
the four spec closures **never reached any document a stage actually reads**, and (iii) that a frozen contract
S1 is about to freeze **encodes the exact ordering D-13.18 calls disqualifying**. Those are process failures
in my own work, not in the hands'.

---

## 1. Verdict

1. **The design holds.** No decision was overturned on its merits. Two need amendment (D-13.17's scope, and
   D-13.20's independence rule), and one — the anaphor gate — needs **reformulating or reversing**.
2. **The corrected score is 15/24, not 13/24.** Two cases were failed by my matcher, not by the prototype.
3. **Of the 9 real failures: 5 are prototype bugs, 3 are NEW spec gaps, 1 is a harness limit.** The NEW spec
   gaps are the spike's highest-value output — each is a fork S3 would otherwise have hit blind.
4. **Two critical findings survive that the spike itself missed**, both raising the severity of what we
   already knew: the D1 chain **also silently deletes an honest refusal**, and name-as-verdict **bypasses the
   caps entirely in Phase 1, at every type** — not just at the two lowered floors.
5. **Fix first:** propagate C1–C4 + the new closures into the durable docs, and correct A1/A5 **before S1
   freezes them**. Everything else is downstream of that.

---

## 2. The blind-case scoreboard, corrected

Score **15/24** (hard asserts 99). Verified by re-run after the matcher fixes; `tmp/spike-rk/match-report.txt`.

| Case | Final classification | Sev | Action (owner) |
|---|---|---|---|
| rk-19 thin-context | **PROTO_BUG** | **critical** | Citizen is routed off the *mention's* `entity_type` instead of the **edge's layer**. spine/13 §3a/§5.3 are explicit: an `observed-at` on a design-typed mention **materializes a provisional presence**. (impl → S2/S3) |
| rk-14 probe (cross-operator) | **PROTO_BUG** | **critical** | The prototype **names the missing operator gap and then asserts the assessment anyway**, drawing a cross-army relocation. A gap that does not bind the fusion path is decoration. (S3) |
| rk-10 co-located presence | **PROTO_BUG** | high | Same root cause as rk-19; also invents `design`/`anchor` citizen values outside §3a's two citizens. (impl → S2/S3) |
| rk-17 design + one signal | **PROTO_BUG** | high | D-13.10's per-layer profile is unimplemented, so designs never collapse — the "one more trivially-available signal clears it" path does not exist. (S3) |
| rk-22 garrison + forward site | **PROTO_BUG** | high | Implemented R1.4 (draw only over earned identity) but **not R1.3** (only comparable placements enter a supersede series), so the D1 guard is one-dimensional. (impl → C1's second consumer) |
| rk-20 co-location relocation | **SPEC_GAP_NEW** | high | The spec points both ways: co-located reports "collapse into one presence" vs "shared anchors top out at probable". Needs the per-layer confirm rule. → **C6** |
| rk-14 designation/operator | **SPEC_GAP_NEW** | high | Normalization-as-prerequisite vs operator-conflict-as-hard-wall are both spec'd and conflict when the value is unnormalizable. → **C7** |
| rk-07 decline | **SPEC_GAP_NEW** | high | The gate is specified per-*pair* ("**both** members' surface forms") but categories are per-*cluster*; the n-ary quantifier is unstated. → **C5** |
| rk-24 reprint independence | HARNESS_LIMIT | medium | Already disclosed in C4 (no `source_id` slot). **But it exposed a real defect** — see §3 C8. (S3) |
| rk-09 enumeration | ~~fail~~ **PASS** | — | Matcher bug (`any_of`). Overturned. |
| rk-23 two candidate formations | ~~fail~~ **PASS** | — | Matcher bug (`any_of` + count-0). Overturned. |
| rk-18 unnormalized operator | HARNESS_LIMIT | low | No config slot in the contract; the case can't supply an equivalence table. |

**No prototype cheating was found** — no hardcoded case ids, no input pattern-matching. It self-verifies with
six sabotage tests and is byte-identical across randomized hash seeds.

---

## 3. New closures — C5…C10 (these must land before S3)

- **C5 — the n-ary gate quantifier (from rk-07).** The `EXPLICIT_EQUIVALENCE` gate says the quote must contain
  "**both** members' surface forms" — a two-member formulation. For an n-member cluster the quantifier is
  unstated; the implementer chose per-link conjunction and flagged the cost (one bad link demotes a good
  cluster to *n* singletons). **Closure: the gate is evaluated per *link* (anchor→member), and the cluster
  binds only over links that pass; failing links become injected Tier-1 candidate pairs** — i.e. a partial
  bind, not an all-or-nothing. This is strictly better than both options considered: it neither discards a
  well-licensed link nor lets one bad link license the rest. Also declare the seed equivalence-marker
  vocabulary in config, including verb forms.
- **C6 — the per-layer/per-citizen confirm rule (from rk-20, and the implementer's Ch.3).** The spec says
  co-located reports "collapse into one presence" *and* that shared anchors "top out at probable" — of one
  pair. **Closure: `perishable` is declared per *(type, attribute)*, not per attribute.** Geography is
  perishable for a **formation** (a unit moves) but **constitutive** for a **presence** (a presence *is*
  operator+design+site+window) and **identifying** for a **place** (coordinates). The shipped config schema
  already supports this shape (`attribute_roles.<type>.<attr>.perishable`), so it is one declaration, not new
  machinery. This simultaneously fixes the implementer's Ch.3 (no confirm trigger an anchor could satisfy) —
  and the review is right that this is a *missing rung*, **in addition to** the `places.augment` ordering bug
  I recorded. Both are true; both need fixing.
- **C7 — the third state for an untestable discriminator (from rk-14).** R5.2 makes normalization a
  prerequisite for walling on **operator**; D-13.20 gives **designation** the strongest wall with no
  normalization table at all — so `3rd` vs `III` is permanently unmergeable. spine/13 §7 already states the
  prerequisite generally ("an attribute or relationship"), so the narrowing to operator was a drafting slip.
  **Closure: normalization is a prerequisite for walling on ANY slot, and an unnormalizable stated value
  yields a third state — `unnormalized` ⇒ no wall AND no fusion; raise a named gap.** The prototype was right
  that a false wall must not shatter a merge; it was wrong to let the pair confirm instead. **A gap must bind
  the fusion path, not merely annotate it** — that is the rk-14-probe critical bug, and it generalises.
- **C8 — the independence predicate is evidential lineage, not document count.** The prototype used "≥2
  distinct documents" and therefore confirmed the reprint case: two verbatim reprints are two `doc_id`s.
  **Closure: the identity path inherits the claim-level corroboration ledger's independence groups
  (spine/04), and a cite-of-a-prior-report is same-group.** This is **new code in S3** (D6), and it is the same
  root cause as the flagship-independence question (D11) — *nominal* independence (different publisher/discipline)
  is not *real* independence (independent look at the phenomenon). One predicate fixes both.
- **C9 — the authoritative bind must be document-scoped in effect, not just in licence.** D-13.17 gates the
  bind on a *document-scoped* precondition, but the bind instantiates through `_matching_eids`' **global**
  name/alias expansion — so the precondition does not bound the effect. **Closure: an authoritative coref pair
  may only instantiate over entity ids attested in the contributing document.** Decisions (a) and (b)
  therefore **share the `Entity.doc_ids` carrier**, and (a) must not ship without it.
- **C10 — rule the single-source relocation fork.** `allow_single_source_authoritative_identity` is a real
  unnamed fork, and the prototype's version is wider than its own rationale claims (it admits *any*
  single-member instance, ungated by grade). **Closure: a relocation may be drawn from one source only when
  that source authoritatively co-refers its own mentions AND clears the authoritative bind's grade floor;
  a bare single-member instance never licenses one.** Option "always require two sources" is rejected: it
  refuses a source authority over its own referent, which spine/13 §5 grants.

**Rejected — the implementer's central architectural claim.** *"Fusion is licensed by a structural trigger,
never by a score"* is **invented, and stronger than the spec**. D-13.9 says the opposite in terms: confirmed
identity is reached by a **graded** path that two guards constrain. Converting a *negative cap* into a
*positive whitelist of three triggers* changes the system in both directions — and it is what produced rk-17
(designs can never collapse) and the anchor-layer dead end. **Keep the half that is right:** the guard must be
a hard **precondition on the fusion path**, not a score contributor — which is exactly R3.1. **Reject the
whitelist.**

---

## 4. Confirmed findings the spike itself missed

- **D1 is understated (critical).** The chain holds at every link, but it stops one consequence short: the
  over-merge does not merely *add* a fabricated relocation — it **silently removes an existing honest
  refusal**, turning an edge correctly labelled `insufficient` (with a Known Gap naming the missing
  corroboration) into `stale` **with no gap at all**. So the same identity bug both fabricates a claim and
  deletes the system's own admission of ignorance. **G16 must assert three things:** no confirmed formation
  merge · no drawn relocation · **no Known-Gap deletion and no `insufficient → stale` transition** on the
  retired edge.
- **Name is a verdict in Phase 1, at every type (high→critical).** My D3 said the name-only fusion hole was
  "scoped to the two types whose floor was lowered." **That is wrong.** The widest path **bypasses the bands
  entirely** via the Phase-1 bootstrap disjunction, and applies to `unit`, `variant`, `basing_site` and every
  other type. Likewise D1 step 2's "nothing resists it — `confirm_is_durable` short-circuits" names a
  resistor **the demonstrated path never reaches**. Restate: *name is a verdict in Phase 1 at every type, and
  the caps exist only in Phase 2.* R1.2/R3.1/R3.2 must bind **the bootstrap disjunction** explicitly.
- **Alias self-equivalence bypasses both the namespace and the type gate (critical, MISS).** `AliasIndex`
  equivalence is reflexive where its own docstring promises a real alias link, so the namespace-gated
  exact-name branch is never reached — making cross-operator **and cross-type** fusion reachable in **Phase
  1**. D4's remedy (add a namespace key to the Phase-2 loop) would have left this wide open. Two fixes: make
  equivalence non-reflexive, and type/namespace-gate the alias branch.

---

## 5. The anaphor decision must be reformulated — and I got the argument wrong

Three findings converge on D-13.17's `UNAMBIGUOUS_ANAPHOR` call, and together they overturn **my reasoning**
even where they leave the conclusion available:

1. **The gate fails open.** It is an *absence* test ("no second compatible-type mention") over a
   **model-produced, surface-form-deduplicated** inventory. So **under-extraction makes the gate PASS** — its
   failure mode is *anti-correlated with safety*, and it converts a documented under-reach into an over-merge
   path.
2. **A doctrinal contradiction of my own making.** Decision (b) forbids treating absence as evidence
   ("absence of contrast is neutral"); decision (a) makes **absence the licensing condition for the strongest
   fusion in the system**. Same document, opposite doctrines, structurally identical inputs.
3. **My decisive argument mischaracterised the alternative.** I overruled analyst B partly because raise-only
   "manufactures nameless orphans." It does not: raise-only produces a **`probable` HITL candidate with the
   merge one click away**. And the decision itself concedes the raise-only mitigation is currently fictional
   because *the licensing quote is written but read nowhere*.

**Closure: reformulate the gate as a POSITIVE requirement** — require a named, declared, ontology-typed
antecedent, exactly one type-compatible mention **where `unknown`-typed endpoints COUNT as compatible** (so
any second undeclared endpoint fails the gate). If that positive gate is not built, **the decision reverts to
raise-only** — which was the conditional I attached originally, and analyst B's position is the safe default.

---

## 6. The process failures (mine)

- **Three matcher bugs, one score-changing.** `any_of` read the wrong key so it could *never* pass;
  `count_equals … 0` was structurally unpassable (scoring UNRESOLVED exactly when the implementation was
  right — including on the suite's most important assertion); per-case invariant ops were undispatched. **All
  three fixed; re-scored 13/24 → 15/24.** The lesson is the one this project already knows: *a check that
  cannot fail is a check that lies* — and I shipped two that could not pass.
- **My anti-fabrication invariant did not catch fabrication.** I2 pooled stated values across **all**
  documents in a case and matched by loose substring, so transplanting a value from a neighbouring document
  onto a thin instance — the exact non-negotiable breach rk-19 exists to catch — **passed**. Now scoped
  **per instance**; verified with a negative control (a transplanted designation now fires it) and calibrated
  so legitimate normalization (`3rd`→`3`) and composite AND-keys still pass.
- **C1–C4 never left `tmp/conv`.** No document a stage reads carries them, so S1–S4 would be run from files
  that still contain the contradiction C1 was written to resolve. **This is the top action.**
- **A1/A5 encode the forbidden ordering.** They make the **referent atom the primary id key with the claim
  atom as a fallback** — the inverted order D-13.18 calls disqualifying. **A1/A5 are frozen at S1, which is
  the next stage**, so this must be corrected first. Likewise §7, D-13.9 and D-13.14 still call a bare
  designation a unique identifier — the precise thing D-13.20 forbids.
- **The new gates were never wired.** G19 exists only in the §5a appendix — in no gate table, no stage's gate
  list, no owned test path; the G15/G16/G18 amendments likewise never reached the stage scopes. Since the
  hands are deliberately restricted to the stage spec, **an amendment that lives only in an appendix will
  never reach the test author.** Also: `config/resolution.yaml` — where nearly every new knob lives — is owned
  by **no stage**, and `operated-by` is assigned to a stage that neither owns the file nor lists the work.

---

## 7. Case-suite and gold-slice findings

- **The suite cannot fail an over-raiser.** All twelve gap assertions are `present`/`count_gte`; there is not
  one `absent`-gap assertion. An implementation that raises "insufficient evidence" on *every* instance passes
  the entire suite — and over-raising **mis-tasks the analyst**, the operational face of the thing the
  non-negotiable forbids. **Add the rk-19 mirror** (same shape with organizational evidence present, assert
  *no* gap). Cheapest missing case in the suite.
- **G15's positive half has no case:** nothing asserts that a sighting **plus** organizational evidence *does*
  produce a formation attribution, so the derived-basing branch is never exercised in the positive direction.
- **rk-07's selector over-quantifies:** `referent_atoms[has=…].declined` is universally quantified, so an
  implementation emitting *both* the declined grouping row and the de-grouped per-member atoms — the literal
  reading of D-13.18 — is scored FAIL. Assert on the grouping record specifically.
- **Gold slice: the sub-oracle over-confirms.** Twelve entries are graded `confirmed` on a **single** source
  document, contradicting the running system's own two-independent-groups rule — so the yardstick is more
  confident than the system it scores. And one alias entry rests on one hedged grade-C source while citing a
  row that implies the opposite. **Owner: DATA.** Either cap them at `probable` or record the single-record
  bypass as an explicit ledger entry with its rationale.

---

## 8. Ordered actions

| # | Action | Owner |
|---|---|---|
| 1 | Propagate **C1–C10** into spine/13 §13, plan §5/§5a/§7, DECISIONS.md, disclosures — the appendix does not reach the hands | spec |
| 2 | **Correct A1/A5 to claim-atom-primary** + fix §7, D-13.7, D-13.9, D-13.14, §10 body text | spec, **before S1 freezes** |
| 3 | Wire G19 + the G15/G16/G18 amendments into the gate table, stage gate lists, owned test paths, acceptance | spec |
| 4 | Amend **G16** to assert no Known-Gap deletion / no `insufficient → stale` | spec + RK-LAYER |
| 5 | Assign `config/resolution.yaml`, `config/credibility.yaml`, `credibility/supersession.py` to stages; move `operated-by` + D12's event↔trading_org edge to **RK-LAYER/S2** | spec |
| 6 | Reformulate the anaphor gate positively, or revert to raise-only | spec |
| 7 | Bind the caps to the **Phase-1 bootstrap disjunction**; make alias equivalence non-reflexive + type/namespace-gated | RK-COREF |
| 8 | Route citizen by **edge layer**, not mention type (rk-19/rk-10); make relocation candidacy `site_type`-aware (rk-22) | RK-COREF / RK-LAYER |
| 9 | Add the rk-19 no-gap mirror + G15's positive case; fix rk-07's selector | test hand |
| 10 | Resolve the sub-oracle's single-source `confirmed` entries; adjudicate D11 | DATA / EVAL |

## 9. What the spike did NOT establish

Unchanged from C4, plus: the review's **completeness critic never ran** (session limit), so "what did all
three blind hands never get asked" remains partly open — the two questions it was to answer were whether an
existing test already contradicts a defect claim, and whether S1 has everything it needs. Item 2 above is the
answer to the second: **it does not.** Also still unverified: source-independence (D6/C8), the licensing quote
end-to-end, the sourced `count`, design-layer arithmetic, and that the production knobs are wired.

---

## C6 re-specified, and C11 added — the two S3 blockers, closed 2026-07-25

S2's implementer reported C6 unimplementable as written and `operated-by` producerless. Both verified. S3 owns
`config/resolution.yaml` and the A7 extraction schema, so these must be settled **before** S3 starts.

### C6 (re-specified) — `perishable` becomes a named **time-role**, not a boolean

**The defect.** C6 says geography is *perishable* for a **formation**, **constitutive** for a **presence**, and
**identifying** for a **place**. That is **three** states; the shipped field is a boolean
(`config/resolution.yaml:330-346`, `perishable: true|false`, read by `rconfig.attribute_perishable` and
documented there as "SCHEMA ONLY … not yet consumed"). A boolean cannot carry three, so the closure as written
could not be built. *(The per-`(type, attribute)` half was never the problem — `attribute_roles.<type>.<attr>`
is already keyed that way.)*

**Closure: replace the boolean with a declared `time_role`**, four values, each earning its own behaviour:

| value | meaning | identity consequence |
|---|---|---|
| `durable` | a stable spec (was `perishable: false`) | agreement supports identity normally |
| `perishable` | expected to change over time (was `perishable: true`) | **perishable-only evidence cannot confirm** — the D-13.9(a) cap |
| `constitutive` | the attribute **is part of what this instance is** (a presence *is* operator+design+site+window) | it cannot "change" without being a *different* instance ⇒ a difference is a **distinctness** signal, not staleness |
| `identifying` | the attribute identifies the entity (a place's coordinates) | strong identity evidence; **satisfies the non-perishable requirement for a confirm** |

**No backward compatibility** (standing directive — no migration shim outlives its stage): S3 migrates the
existing declarations and a bare `perishable:` key becomes a **loud validation error**, exactly as S1 did for
`attrs`. `constitutive` is what lets a **presence** confirm at all (its geography is definitional, not
perishable), and `identifying` is what lets a **place** confirm — which together are the missing rung C6 was
created to supply, and without which spine/13 §6 lever 2 cannot exist.

### C11 (new) — `operated-by` must get a producer, or G18 half-lies

**The defect.** S2 declared the predicate (G18 names it) but left it **non-extractor**, so **nothing can emit a
*stated* `operated-by`**. G18's `based-at` half works; its `operated-by` half can only ever fire on fixtures.

**Closure: S3 adds `operated-by` to the extractor contract.** S3 already amends the A7 mention schemas for the
coref half, so this is one field in a file it owns, not new capability. The alternative — leave it
fixture-only — is rejected because **a declared predicate with no producer makes the gate lie**: G18 would go
green while half the behaviour it names is unreachable, which is precisely the failure §5a was written to stop.
If S3 finds the extraction change genuinely out of scope, the fallback is **not** silence: G18 must then declare
in the gate itself that its `operated-by` arm is fixture-only, and it goes in the design-note disclosures.
