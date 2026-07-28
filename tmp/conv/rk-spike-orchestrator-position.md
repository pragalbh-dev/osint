# RK-SPIKE — orchestrator's independent position (written BEFORE reading the analysts)

Recorded first, deliberately, so the synthesis is a comparison rather than an echo. Grounded in the code
facts (`rk-spike-code-facts.md`) plus the further verification below. Every mechanism named here **extends an
existing seam** — none is greenfield.

## Further verification done by the orchestrator (beyond the recon)

- **`make_claim_id(doc, locator)` → `"<doc>-<locator>"` kebab** (`schemas/ids.py:19-30`). So **document
  provenance is already encoded in every claim atom's id**, as the first hyphen-delimited segment. Decision
  (b)'s "same document" carrier therefore needs **no new field** — only a documented invariant (doc tokens
  contain no hyphen: `d05`, `d02`, `d07`) plus an accessor, asserted by a test. The referent atom, minted by
  `make_referent_id(doc, …)` in S3, inherits the same property.
- **`_coref_pairs` already implements "authoritative-unless-contradicted"** (`resolve/__init__.py:614-661`):
  a pair in an opted-in category is demoted to raise-only on *entity-type mismatch*, *namespace
  incompatibility*, or `has_hard_conflict`; a **vetoed** pair is dropped outright. So the "coref stays a
  challengeable proposal" property is *already partly built* at the pair level — my post-checks slot in
  beside these three, they do not replace them.
- **`_deterministic_total` already excludes a whole signal class from the auto-merge test**
  (`resolve/cluster.py:78` + docstring): `source_asserted` can lift a pair into the queue but can never cross
  the auto line. This is the **exact precedent for a cap**, already blessed as the red-team patch.
- **The pair score breakdown is already stored** — `Partition.merge_breakdown: dict[str, dict[str, float]]`
  (`resolve/cluster.py:625`) — and `identity_ledger` already derives "which independent identity signals
  contributed" from it (`resolve/scoring.py:645+`). So **caps can be expressed as declarations over the
  stored breakdown**, needing no new scoring math.
- **A per-node-type `identity:` policy block already exists in the ontology** (`config/ontology.yaml:72`
  `identifier_patterns`, `:105-114` `name_head_markers` / `relational: false`). Per-type identity policy is
  therefore an established idiom, not a new concept.
- **A per-attribute identity-role block already exists** — `config/resolution.yaml:326-350` `attribute_roles`,
  carrying `role: critical | supporting` (unlisted ⇒ neutral) **and `perishable: true|false`** ("read but NOT
  yet consumed"). This is the home for the discriminator classification — **not** `ontology.yaml`. The clean
  split: `ontology.yaml` declares *what attributes exist* (+ their layer, per A2); `resolution.yaml` declares
  *how they behave in identity*.
- **There is no `attribute_types` block in `config/ontology.yaml` at all** — attrs are bare string lists per
  node type. This confirms A2's premise and adds a consequence (see "Handoff to S1" below).
- **`unit.designator` is not declared in `attribute_roles` at all** ⇒ it is **neutral, with zero identity
  effect**. The top rung of the discriminator ladder is not merely unwired — it is undeclared.

## (a) Tier-0 auto-bind by coref category

**The crux first — what a "loose bind" can even mean.** A1/D-13.11 say the referent atom is minted at ingest
per doc-local coref cluster and *atoms never split or merge*. Read naively, that makes an over-binding coref
cluster **permanent**, which contradicts spine/13 §4's promise that coref stays a challengeable proposal.
The contradiction dissolves once you notice what spine/13 §8 already says: the **grouping unit at rebuild is
the claim atom**, and the straddle split already re-partitions *one mention's* claim atoms across two nodes.
So:

> **The referent atom is a strong *stated prior* over claim atoms, not a weld.** The atom is immutable (the
> log permanently records that the extractor read these mentions as one referent); the *derived grouping* may
> override it when a critical discriminator conflicts. Over-binding is therefore recoverable at rebuild, and
> the non-negotiable is preserved.

This must be written into spine/13 §8 explicitly — it is currently only implied, and an implementer reading
"atoms never split" would build the irreversible version.

**The policy: all three categories may be authoritative, but each only behind a *deterministic post-check*.**
A model-chosen label is not evidence; a model-chosen label plus a structural verification is. This is the
whole idea, and it is what makes the decision defensible rather than a guessed threshold:

| Category | Deterministic post-check (new, cheap, ingest-side) | Rationale |
|---|---|---|
| `EXPLICIT_EQUIVALENCE` | the licensing quote is present **verbatim** in the document (`coref.py:253-260` already does a whitespace-collapsed substring test — reuse it), **and** the source meets a grade floor | the source is authority on its own reference (§4), but **stated ≠ trusted** (§5): a planted grade-E doc writing "the 8th AD Bn (also known as the 12th AD Bn)" must not weld two units |
| `NAME_VARIANT` | `normalize(a) == normalize(b)` under the **existing** normalizer/transliterator | the category is *defined* as spacing/casing/punctuation only. A correctly-applied one is near-deterministic; a **mislabelled** one is the "HQ-9" vs "HQ-9/P" mark trap the containment config already warns about (`resolution.yaml:183-186`). The check turns a model judgement into a verified one and rejects the mark case to raise-only |
| `UNAMBIGUOUS_ANAPHOR` | **type-unique antecedent**: no second cluster of a compatible entity type exists in the document | the category's own name states the condition; this is the only mechanically checkable reading of it, and it targets exactly the harmful case (two batteries in one document, "it" binding to the wrong one) |

**Why not simply hold anaphora raise-only** (the tempting conservative answer): it would defeat lever 1
(spine/13 §6 calls Tier-0 the *biggest* lever) and manufacture a large class of **nameless orphan fragments**
— an anaphor carries no independent name, so an unbound one becomes an instance whose only content is the
facts hung on it. That is not honest reporting, it is noise, and it is fragmentation *manufactured by our own
grain choice* rather than by the evidence. The type-unique check keeps the lever while removing the harm.

**Config shape** — `coref_authoritative_evidence` changes from a bare list to a map (absent category ⇒
raise-only, preserving the existing "unset ⇒ off" idiom, G6-clean):

```yaml
coref_authoritative_evidence:
  EXPLICIT_EQUIVALENCE: {require_verbatim_quote: true, min_source_grade: C}
  NAME_VARIANT:         {require_normalized_equality: true}
  UNAMBIGUOUS_ANAPHOR:  {require_type_unique_antecedent: true}
```

**Two gates, two places** (a fork the plan does not name): the *ingest* pass decides which links join one
referent atom (using only ingest-verifiable signals — quote, normalized equality, type-uniqueness, source
grade); `_coref_pairs` keeps its existing *resolve*-side demotion (type / namespace / hard-conflict), now
applied to cross-referent proposals. A link failing the ingest check still emits its `coref-same-as` claim,
so the proposal and its quote survive into the queue — **demotion, never deletion**.

**The principle collision, resolved.** `resolution.yaml:170-179` justifies the empty list partly to protect
the d10 "HT-233 (H-200)" beat an analyst is meant to earn. Working-principles #1 forbids that. The
target-correct policy stands; the data pass owes a *replacement* earned-merge beat whose licensing evidence is
genuinely below the bar (e.g. an equivalence stated only by a low-grade source, or one whose quote does not
verify) — which is a **better** demonstration anyway, because the analyst then earns it against a stated
reason rather than against a switch we left off.

## (b) Tier-1 same-doc comparison + the contrastive prior

**Carrier for "same document": already present** — the doc token in the claim/referent atom id (verified
above). No new field; one documented invariant + a test.

**The three things being conflated must be separated — they are not one prior:**

| Signal | Strength | Mechanism |
|---|---|---|
| a **stated `distinct-from`** | hard, transitive veto | **already built** (`_claim_distinct_pairs`, `resolve/__init__.py:567-575`) — leave alone |
| a **syntactic contrast** (an enumeration; "another battery") | **raise-wall** — blocks bootstrap *and* auto-merge, queues the pair with its reason | a new `coref-distinct-from` producer in `ingest/coref.py`, symmetric with the `coref-same-as` it already emits, feeding the **existing** `raise_walls` channel (`resolve/cluster.py:313, 327-334, 449, 474, 573`) |
| **distinct designations** | a discriminator **wall** | belongs to (c), *not* to a syntactic prior — do not conflate |

**Why raise-wall is the right strength.** The three candidate strengths fail or fit as follows: a **score
penalty** is unavailable and undesirable (the soft-penalty branch is dead config, and reviving it buries a
magic number inside the merge score where the harm is asymmetric); a **hard transitive veto** is *exploitable*
— a planted document could manufacture fake contrast and permanently shatter a legitimate identity; a
**raise-wall**'s worst-case outcome is "an analyst reads the sentence." So the raise-wall prevents the
OOB-undercount over-merge (the dominant harm, D-13.14) without ever permanently shattering, and it puts the
human in the loop *with the quote* — which is the graded behaviour, not a workaround. It also needs **no
source-grade gate**, precisely because its failure mode is benign; that is the tell that the strength is right.

**The neutral case stays neutral:** same-doc, no contrast ⇒ judged on merits, no prior in either direction.
And Tier-1 **must** see same-doc pairs, else the grain choice manufactures a permanent fragmentation class
(F5). Note the code fact this depends on: `Entity` is keyed globally by `ent:{type}:{name}`
(`resolve/entities.py:180`) and pass 1 collapses one surface form to one claim per doc
(`ingest/extract.py:839`), so "same string twice in one document" cannot even be represented today — the
same-doc pairs that exist are *different surface forms*, which is exactly the set Tier 1 should compare.

## (c) Discriminator priority

**Priority is not one dial.** It resolves into the three shapes the judge actually has, and each rung uses a
different pair of them:

| Rung | Blocking | Score weight | Cap | Wall |
|---|---|---|---|---|
| **unique identifier** (serial, BoL ref) | yes (hard-ID block) | — | lifts all caps | conflict ⇒ hard veto (**built**: `identifier_patterns` + `_identifier_veto`) |
| **designation** (`unit.designator`) | yes | yes | **lifts the perishable cap**; does **not** alone confirm | conflict ⇒ hard veto (**must be declared — it is not**) |
| **operator / branch** | namespace key | yes | — | conflict ⇒ hard veto, **gated on value normalization** |
| **geography** | — | yes | **perishable ⇒ ≤ probable** | conflict ⇒ veto (**built**, but see the hole below) |
| **relational** | yes (relational block) | yes (0.40) | — | — (F9-limited) |
| **name** | yes (token block) | rarity-graded | **≤ possible alone, every layer** | — |

**The single most important call: a designation is a *non-perishable discriminator*, not a unique
identifier.** Designations are reused across armies and across time — "8th Battalion" exists in every army.
So a shared designation **satisfies D-13.9(a)'s perishable cap** (it is the non-perishable thing a confirm
must rest on) but still requires namespace compatibility *and* independent corroboration to confirm. A serial
or contract reference is the unique identifier; `identity.identifier_patterns` already implements that rail.
Conflating the two is what would let one shared string confirm a formation merge — the OOB-undercount door.

**A hole this exposes, previously unnoticed:** the Phase-2 fuzzy fixpoint **never checks
`namespace_compatible`** (`cluster.py:468-490`), and relational blocking emits pairs with **no namespace key**
(`cluster.py:182-187`). So "designator agreement + namespace compatibility" cannot be relied on as stated —
S3 must close the namespace gap in Phase 2, or designator agreement becomes a cross-army false-merge path.

**Both caps are declarations over the already-stored breakdown**, following the `_deterministic_total`
precedent — no new scoring math, no code literals:
- **name cap** — requires splitting `attribute_score`'s fused output into separate `name` and `attrs`
  components in the breakdown (`bd` is already stored and already drives `identity_ledger`), then: if every
  non-zero contribution is name-derived, the band cannot exceed *possible*.
- **perishable cap** — if every non-name contribution is perishable-classed, the band cannot exceed
  *probable*. `attribute_roles.<type>.<attr>.perishable` **already exists** ("read but NOT yet consumed") —
  S3 consumes it. This *is* the D-13.9(a) guard.
- **co-location cap (G16)** — the same machinery, keyed on citizen: for `formation`, confirmation requires at
  least one contribution from the unique-id or non-perishable class. Presence-merge is unaffected. This is
  the per-layer profile's real shape: **per-citizen `confirm_requires` declarations, not merely different
  floors** — one judge, a policy profile (D-13.10), composing with the existing `auto_merge_by_type` override
  rather than duplicating it.

**Value normalization.** New, and the config *already asks for it* by name
(`resolution.yaml:317-324`: exact-match walling "SHATTERS legitimate merges", which is why
`unit.service_branch` and `trading_org.origin_country` sit at `supporting`). Home: a `value_classes:` block in
`resolution.yaml` (equivalence classes per attribute), applied **before conflict detection *and* before
namespace derivation** (`resolve/entities.py:114-120` reads raw attrs — a normalization applied only at
conflict time would leave namespaces split). Analyst-editable, hot-config. **S3's deliverable is then exactly
what the comment asks: promote those two attributes to `critical` once normalization lands.**

**F9 — accept the gap explicitly, do not fix it in S3.** A graded sub-confirmed relational weight reintroduces
a feedback loop (a probable link raises a score, which creates a merge, which raises the link) that threatens
the monotone termination argument the fixpoint rests on (`cluster.py:6-9`) and therefore G2 determinism —
a bad trade in the middle of a substrate rework. **What must be said out loud** (design-note disclosure +
a `/coverage` line): *relational scaffolding only helps where the anchor actually merges; a merely-probable
anchor lends no support at all.* Without that disclosure a reader would wrongly believe lever 2 degrades
gracefully. It does not — it is a step function.

**The absent discriminator (D-13.8) and the non-negotiable.** Critical-*if-present* means absence is
`unknown`: never a conflict, never a wall, never fabricated. The clause the project is graded on is about the
**output**: an under-individuated instance must *say so, by name*. The honest sentence, roughly —
*"HQ-9/P presence at <site> confirmed (2 independent sources); formation identity under-determined — operator
stated, designation absent; 1–2 candidate formations; designation coverage needed"* — and it must appear as a
first-class `/coverage` item, not merely as a lower number. Silence with a low confidence score is the
failure mode; a named gap is the requirement.

## ADDENDUM — further verification that materially cheapens (c)

Written after the position above, on a closer read of `resolve/cluster.py`'s banding block
(`:440-580`). **Both caps the design asks for are already built**, and the recon's "three bands"
summary understated the machinery. This is a correction in the *helpful* direction and it changes (c)'s
build estimate from "new mechanism" to "configure + one small split + one new instance of a proven pattern".

1. **The name cap exists and is ON.** `cfg.name_alone_caps_at_possible` is **`true`** in
   `config/resolution.yaml:154`, and `_name_alone(bd)` (`cluster.py:140-148`) caps such a pair down out of
   the review queue into `possible`. Raise pairs, wall bridges and perishable-capped pairs are exempt.
   **But it does not yet satisfy D-13.10**, and the reason is precise: `_name_alone` tests
   `ATTRIBUTE > 0 and RELATIONAL == 0 and SOURCE_ASSERTED == 0`, and `attribute_score` **fuses** name
   similarity with attribute agreement into that one `ATTRIBUTE` term. So "name alone" currently means
   "the attribute term alone" — a pair agreeing on a name *and three attributes* is still classified
   name-alone. It over-caps (the safe direction), but D-13.10's design-layer story — *"a name match reaches
   at most possible, and one more trivially-available signal (shared manufacturer / component /
   co-citation) clears it"* — **cannot function at all** until `name` and `attrs` are separate components in
   the breakdown. That is the sharpened, verified requirement for S3, and it is a small refactor of a value
   that is already stored (`merge_breakdown`).
2. **The perishable cap exists and is well-built.** `confirm_is_durable` + `perishable_capped`
   (`cluster.py:443, 478-496`) withhold a would-be auto-merge that confirms *only* on perishable ordered
   succession, force it to the review queue with its own analyst-facing reason
   (`_perishable_confirm_reason`, prose-only, no thresholds — G6-clean), and **re-decide each fixpoint pass**,
   popping the cap when a pair *earns* durable support as clusters grow. This is D-13.9(a) already
   implemented.
3. **Therefore the cap semantics map cleanly onto set membership, and both shapes are proven:**
   - *cap at **probable*** = block the merge, force into `candidates` — the `perishable_capped` shape;
   - *cap at **possible*** = block from `candidates`, land in `possible` — the `name_alone` shape.
   **The co-location cap (G16) is a third instance of the `perishable_capped` shape**, not new machinery:
   withhold the formation confirm, queue it with a reason. Its gate fixture can mirror the existing
   perishable-cap tests, and the analyst-facing sentence lives beside `_perishable_confirm_reason`.

**So (c)'s real gap list, verified:** `unit.designator` undeclared in `attribute_roles` · value normalization
absent · `name`/`attrs` fused in the breakdown (blocks D-13.10) · `namespace_compatible` unchecked in the
Phase-2 fixpoint (a hole, not a design choice) · the co-location cap not yet instantiated · F9 accepted with
disclosure. Nothing here needs a new scoring model.

## Handoff to S1 that follows from the spike (worth deciding once, here)

`config_models.py`'s `TypeDef.attrs` is contended S1→S2 precisely because the same structured entry is
amended twice (plan §3 item 6). The spike should therefore fix the **whole** structured-attribute entry
schema now — `layer` (S2/A2) **plus** the identity/discriminator fields (c) needs — so the field is amended
**once**, not three times. Note that `role`/`perishable` already live in `resolution.yaml`'s
`attribute_roles`, so the ontology entry should carry only what is *ontological* (`layer`, and the
dual-attribute split of D-13.3), while the identity semantics stay in `resolution.yaml`. Getting this seam
wrong is how the two files start duplicating each other.
