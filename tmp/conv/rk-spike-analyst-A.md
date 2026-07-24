# RK-SPIKE — Analyst A (mechanism-first): the three open micro-decisions

Read-only analysis on `design/resolution-redesign` @ c2a2b68. Grounded in `tmp/conv/rk-spike-code-facts.md`
(treated as ground truth) plus an independent read of `resolve/{rconfig,scoring,cluster,entities,__init__}.py`,
`ingest/coref.py`, `config/{resolution,credibility,ontology}.yaml`, `schemas/ids.py`. Corpus-blind: I did not
open `corpus/**`, `answer_key.json` or `SCENARIO_MANIFEST.json`; every threshold below is argued from a stated
invariant, never from measurement.

---

## Verdict summary (10 lines)

1. **(a) categories:** `coref_authoritative_evidence: [EXPLICIT_EQUIVALENCE, UNAMBIGUOUS_ANAPHOR]`.
   `NAME_VARIANT` stays **raise-only** — promoting it would smuggle the name-verdict back in through the coref
   door at exactly the stage (S3/S4) that removes it.
2. **(a) "held looser" =** *only an authoritative cluster mints a **shared** referent atom*; a looser cluster
   mints **one referent atom per member** plus an injected Tier-1 pair carrying its licensing quote. Option (i).
3. **(a) reversibility:** the shared referent atom is a **grouping proposal the rebuild may decline** — an
   intra-referent critical-discriminator conflict de-groups it to claim-atom granularity and raises. Atoms never
   split; the *grouping* declines. Without this, anaphor-authoritative is disqualifying.
4. **(a) anaphor safety rides on a new deterministic gate**, not on trusting the model: the prompt's own
   licensing condition ("no second mention of that type it could mean") is structurally checkable against
   `coref.inventory()`. Enforce it in code and stamp the result.
5. **(a) principle collision:** target-correct policy binds `EXPLICIT_EQUIVALENCE`; the d10 "HT-233 (H-200)"
   beat is a demo of a **switched-off capability** and must be re-carried by data (split the two designations
   across two documents, or drop the apposition), not by keeping the switch off.
6. **(b) carrier:** Tier-1 *already* compares same-doc pairs — there is no doc filter to remove. The genuine new
   carriers are a **contrastive output channel on coref** (a second list in the forced tool, its own
   `coref-distinct-from` lane) and **`Entity.doc_ids`**, needed because `_matching_eids` expands names globally
   and would otherwise leak a doc-local contrast onto cross-doc pairs.
7. **(b) strength = a band ceiling, not a wall and not a score penalty.** A same-doc *stated-contrast* pair is
   capped at **`probable`** (reaches the analyst with its quote; can never auto-merge). One new config key, and
   its value is a **category name, not a float** — so there is no number to tune.
8. **(c) priority is three shapes, not one dial:** designation = wall + fast path + perishable-cap satisfier;
   operator/geo = wall + score + perishable cap; relational = score + co-location cap; name = blocking key +
   score + hard ceiling at *possible*. Every rung lands in `config/resolution.yaml`.
9. **(c) the two load-bearing code changes:** split `attribute_score` into **two signals** (`name` /
   `discriminator`) — it already computes them independently and meets them at one `max` — and make
   `hard_id_fields.unique` a **list of composite AND-keys** so `(service_branch, designator)` is the identifier
   and a bare designation is not. **F9: accept the gap**, disclose it, roadmap the fix.
10. **Biggest concern:** the three docs' Tier-0 story is *atom-shaped* while the reversibility requirement is
    *claim-shaped*, and neither `spine/13` nor `plan/01` states the decline mechanism — so as written, S3 makes
    intra-document over-merge **permanent**. Second-biggest: `places.augment` runs *after* `resolve_entities`
    (`resolve/__init__.py:181` vs `:177`), so place merges are invisible to `relational_score` — spine/13 §6
    lever 2 names places as a clean anchor, and mechanically it is not one.

---

## (a) Tier-0 auto-bind, graded by coref category

### The three categories, argued separately

The categories are module-level literals (`ingest/coref.py:74-77`), duplicated on the resolve side
(`resolve/scoring.py:43-46`), validated by set-membership only (`coref.py:303-305`) and **chosen by the model**.
There is no structural test behind them and no per-proposal score (`coref.py:69`, `:396` hardcodes
`model_conf=1.0`). So the decision is: which of three model-asserted labels earns a shared atom.

**`EXPLICIT_EQUIVALENCE` → authoritative.** The licensing condition is that *the document states the identity*
— apposition, "also known as", "Full Name (SHORT)" (`coref.py:123-125`). Per spine/13 §4 the source is the sole
authority on its own discourse; there is nothing to corroborate against inside one document. This is the same
class of act as tagging kind. It is also the only category whose evidence is a **verbatim span the document
contains**, machine-checked (`_quote_supported`, `coref.py:258-260`) — the strongest deterministic rail in the
pass. Bind it.

**`NAME_VARIANT` → raise-only.** Two independent arguments, and the second is decisive:
- *Redundant.* "The same proper name in a trivially different surface form: spacing, casing, punctuation, an
  obvious spelling/transliteration variant" (`coref.py:126-127`) is **exactly** what the downstream machinery
  already handles at full strength, cross-document: `normalize` + `transliteration` (`resolve/normalize.py:30-33`,
  `config/resolution.yaml:125-132`), the alias table (`:88-123`), and token-sorted Jaro–Winkler
  (`normalize.py:46-57`). Nothing about a spelling variant is *unrecoverable* downstream — which is the whole
  justification for Tier 0 (`coref.py:8-10`). So it buys nothing the resolver cannot earn.
- *It reintroduces the name-verdict.* An `authoritative` pair is a **Phase-1 bootstrap trigger** that merges at
  hardcoded confidence **1.0** (`cluster.py:462`, `:465`) and **bypasses the bands entirely** — the bootstrap
  does not band at all. It also sets `has_durable_trigger` (`cluster.py:415`), lifting the perishable cap. And
  `name_alone_caps_at_possible` (`config/resolution.yaml:154`) cannot restrain it, because the cap lives in the
  *collection loop* (`cluster.py:560-564`), downstream of the bootstrap. So "authoritative NAME_VARIANT" is
  literally *a name match that merges at 1.0 without banding* — the second stacked lane D-13.1 exists to
  remove, rebuilt on a different predicate. Keeping it raise-only is not conservatism; it is coherence with
  D-13.1/D-13.2/D-13.10.

**`UNAMBIGUOUS_ANAPHOR` → authoritative, conditional on a new deterministic gate.** This is the crux, and it
cuts the other way from the shipped config comment (`config/resolution.yaml:162-163`).

- It is the **only** category that rescues genuinely unrecoverable information. A descriptive reference ("the
  export agency", "the battery", "the site") has **no string for the resolver to match** — it reaches the graph
  only as a bare relation endpoint typed `unknown` (`coref.py:79-82`) and surfaces as a stray `unknown` node
  (`coref.py:6-9`). Tier 0 exists to make provisional instances *rich* (spine/13 §6 lever 1, "biggest lever").
  If anaphora stays raise-only, Tier 0's fragmentation-control value evaporates for precisely the mentions Tier
  0 was built for, and the mint-per-doc-local-cluster grain (D-13.7) buys almost nothing over mint-per-mention.
- It is also the highest-risk category (`config/credibility.yaml:188` says so), and an over-bound anaphor inside
  one document is **not** correctable by cross-document corroboration — there is no second source inside one
  document. That is real and it is why the bind must be *earned by code*, not by the model's label.
- **The gate.** The prompt's licensing condition is *structurally checkable*: "there is no second mention of that
  type it could mean" (`coref.py:128-130`). The mention inventory is already built deterministically, typed from
  the ontology's declared edge endpoints (`coref.inventory`, `:188-215`; `_endpoints`, `:166-185`). So: for an
  `UNAMBIGUOUS_ANAPHOR` cluster, verify that the anaphoric member (an `UNKNOWN_TYPE` mention, or a
  non-proper-name surface) has **exactly one** type-compatible **declared** antecedent in the document. Two
  declared units in the doc ⇒ "the battery" is ambiguous **by definition** ⇒ demote to raise-only. This is the
  answer to "there is no code from which a finer category could be derived": we do not need a finer *category*,
  we need a deterministic *precondition* on the category the model gave — which is the module's own stated
  doctrine ("the model proposes, this module disposes", `coref.py:32`).

**Anaphor risk, both directions, weighed.** Intra-doc *fragmentation* from anaphora is (i) large in volume —
undeclared endpoints are "the majority on the real corpus" (`coref.py:171-173`), (ii) *unrecoverable* by any
downstream mechanism, and (iii) it degrades the whole instance layer, because a thin provisional instance has no
discriminators for Tier 1 to work with. Intra-doc *over-merge* is (i) irreversible by corroboration but (ii)
reversible by three other rails — the deterministic uniqueness gate above, the existing `contradicted` demotion
in `_coref_pairs` (type / namespace / hard-conflict, `resolve/__init__.py:645-650`), and the de-group escape
below — and (iii) always visible to the analyst, because the pair carries a quoted span. With the gate, the
expected-cost comparison favours binding. Without the gate, it does not, and I would flip to raise-only. State
that dependency in the ledger: **the category call is conditional on the gate shipping in the same stage.**

### The crux: what "held looser" means mechanically

A1/D-13.11 mint the referent atom per doc-local coref cluster, and **atoms never split or merge**. So a loose
bind cannot be a weak merge of atoms. Options:

- **(i) One referent atom per *authoritative* cluster only; looser clusters emit one referent atom per member
  plus a Tier-1 proposal pair.** ✅ **Recommended.**
- **(ii) One referent atom per cluster regardless of category, category recorded for a later split.** Rejected
  as *stated* — "a later split" has no referent to split, and if the split is a re-partition of the *claim*
  atoms underneath, then the referent atom was never the grouping unit and the grading collapses to "how hard
  is it to decline." That said, (ii) contains the right insight, which I fold into (i) as the decline mechanism
  below.
- **(iii) Category-graded cluster construction at ingest (transitive closure only over authoritative links).**
  Rejected as *distinct from (i)*: it is not implementable as written, because **the category is per-cluster,
  not per-link**. `coref_claims` emits a star from the anchor to each member (`coref.py:367-398`), every edge of
  one cluster carrying the *same* `_coref_evidence` value (`:377`). A mixed-category cluster cannot be
  expressed, so "closure over authoritative links only" degenerates exactly into (i). (i) is the honest name.

**What (i) mints and proposes, precisely:**

| | authoritative cluster (`EXPLICIT_EQUIVALENCE`, gated `UNAMBIGUOUS_ANAPHOR`) | looser cluster (`NAME_VARIANT`, ungated anaphor) |
|---|---|---|
| minted at ingest | **one** referent atom for the whole cluster (`make_referent_id`, invoked in S3 per plan A1) | **one referent atom per member** |
| carried where | the referent field on every member's `ClaimRecord` (A1, added dormant in S1) | same field, distinct values |
| proposed | nothing — it is bound | the existing `coref-same-as` claim, already emitted with `_coref_cluster` / `_coref_evidence` / `source_quote` (`coref.py:375-379`) |
| consumed by | rebuild's grouping step (the referent is the default grouping unit) | `_coref_pairs` → `raise_only` (`resolve/__init__.py:657-660`) → injected into candidate generation (`cluster.py:203`, `:347`) and `has_raise` (`:533`) → guaranteed a scored pair and an analyst item |

Note this makes the raise-only path *strictly better than today*: the pair is guaranteed to be generated and
banded, and it carries the licensing quote — see residual risk R-a3 on wiring the quote out.

### Is an over-binding cluster still challengeable? (must be — spine/13 §4)

**Not under (i) as literally stated, and that is disqualifying — so (i) ships with a decline mechanism.**

If the shared referent atom is the *minimum* grouping unit, the rebuild can never separate two mentions that
Tier 0 fused, because grouping happens over referents and both mentions now live under one. Over-binding would
be permanent. spine/13 §4 explicitly forbids that ("a coref cluster carrying a conflicting critical
discriminator is the signal it over-bound, and the §5 split fires on it").

**The decline mechanism (concrete):** the referent atom is a **strong grouping proposal**, and the rebuild may
decline it. Before a referent is used as a grouping unit, test its member **claim** atoms for a critical-attribute
conflict; if one fires at the credibility floor, de-group that referent into per-claim-atom provisional
instances and emit a raise. Atoms never split — the *grouping* declines, and the claim atoms re-partition, which
is exactly D-13.11's "both kinds of split are grouping decisions taken here." A5 already provides the fallback
addressing (`claim_id` when no referent is available), so the de-grouped instances key deterministically.

Two mechanism facts make this buildable and one makes it necessary:
- **Buildable:** the adjudication logic exists — `critical_conflict_disposition` (`scoring.py:149-177`) already
  returns `wall` / `raise` / `none` with per-value credibility gating via `_value_meets_grade_floor`
  (`scoring.py:134-146`) reading `Entity.attr_history`. The de-group check calls the same function on the
  member set instead of on a pair.
- **Necessary:** an intra-referent conflict is currently **invisible**. `attrs` is first-claim-wins scalar
  (`entities.py:189` `setdefault`); the losing value goes only to `attr_history` (`:193-199`). So without an
  explicit intra-referent pass, a cluster that fused a PAF mention with a PLA mention presents as a single clean
  entity stating PAF. This is new code, and it is the load-bearing new code of decision (a).

### Mechanism table — (a)

| config file | key | value shape | function touched | exists? |
|---|---|---|---|---|
| `config/resolution.yaml` | `coref_authoritative_evidence` | `[EXPLICIT_EQUIVALENCE, UNAMBIGUOUS_ANAPHOR]` (`list[str]`) | `rconfig.coref_authoritative_evidence` (`rconfig.py:288-301`) → `_coref_pairs` (`resolve/__init__.py:637`) | **exists** — value change only (`resolution.yaml:180`) |
| `config/credibility.yaml` | `coreference` block | uncomment; `categories: [EXPLICIT_EQUIVALENCE, NAME_VARIANT, UNAMBIGUOUS_ANAPHOR]`, `max_mentions: 120` | `coref._coref_cfg` (`:413-415`), `_categories` (`:418-430`) | **exists, dormant** (`credibility.yaml:186-190`) |
| `config/credibility.yaml` | `coreference.anaphor_requires_unique_antecedent` | `bool`, target `true` | **new** check inside `coref.valid_clusters` (`:279-325`), reading `coref.inventory()`'s declared/typed mentions | **new** |
| — (tier-3 attr, not config) | `_coref_antecedent_unique` | `bool` on the emitted claim's `attributes` | written `coref.coref_claims` (`:375-379`); flows `entities.py:212` → `Edge.attributes` → read `resolve/__init__.py:642` | **new value on an existing carrier** |
| `config/resolution.yaml` | `referent_degroup_on_critical_conflict` | `bool`, target `true` | **new** intra-referent pass in `resolve/__init__.py` (before grouping), reusing `scoring.critical_conflict_disposition` (`:149-177`) | **new** |
| — | referent minting rule | *derived*, no key: `make_referent_id` invoked once per **authoritative** cluster, once per **member** otherwise | `ingest/coref.py` emission (`:367-398`) + `schemas/ids.py` (`make_referent_id`, added dormant in S1) | **new (S3)** |

G6: every value above is a boolean or a category list. **No new float.**

### Why the alternatives were rejected

- *Authoritative `NAME_VARIANT`*: rebuilds the name-verdict lane the re-key removes (bootstrap merges at 1.0,
  `cluster.py:465`, un-restrainable by the `possible` cap at `:560-564`), and buys nothing the alias +
  transliteration + Jaro–Winkler path does not already earn cross-document.
- *Raise-only `UNAMBIGUOUS_ANAPHOR`*: gives up the one signal that is unrecoverable downstream, and reduces
  D-13.7's mint grain to mint-per-mention in practice — the fragmentation F8 warns about, made permanent.
- *Option (ii) as stated*: makes the grading meaningless.
- *Option (iii)*: not expressible — the category is a cluster property, not a link property (`coref.py:377`).

### Residual risk — (a)

- **R-a1 (high).** The uniqueness gate needs a definition of "the anaphoric member." `Mention` carries no span,
  no offset, no attrs (`coref.py:156-163`), so "is this surface an anaphor or a proper name?" has no clean
  structural test. My call: treat `entity_type == UNKNOWN_TYPE` (an undeclared relation endpoint) as the anaphor
  proxy — it is the population the pass exists for, it is already computed, and a *declared* mention is by
  construction a named entity. A declared-to-declared "anaphor" cluster should simply be demoted (a declared
  mention is not an anaphor). Uncertain, but this is the best call available without adding spans to `Mention`.
- **R-a2 (medium).** `_coref_pairs` expands both endpoints through `_matching_eids` (`resolve/__init__.py:643-644`),
  which matches by **name/alias globally**. So an authoritative doc-local cluster can expand into a cross-product
  including entities from *other* documents and bootstrap-merge them at 1.0. That is a name-verdict leak on the
  authoritative path. Fix in the same stage: restrict the expansion for coref pairs to eids attested in the
  contributing document (needs `Entity.doc_ids` from decision (b) — the two decisions share this carrier).
- **R-a3 (medium).** `COREF_QUOTE_ATTR = "source_quote"` is written (`coref.py:71`, `:378`) and **never read
  anywhere in `resolve/`** — the only reader of `Edge.attributes` is the evidence-category lookup at
  `resolve/__init__.py:642`. So the config's promise that a raise-only pair "reaches the queue WITH its licensing
  quote" (`resolution.yaml:176-177`) is **not plumbed**. With two of three categories staying raise-only, this
  must be wired (`res.candidate_reasons`, `cluster.py:61` → `Partition.candidate_reasons`,
  `resolve/__init__.py:770`, is the existing channel) or the raise-only story is hollow.
- **R-a4 (low).** Overlapping model proposals resolve first-wins by arrival order (`coref.py:321-322`). Harmless
  for under-merge, but it means the *set* of authoritative clusters depends on model output order — a live-lane
  non-determinism, already accepted for the live path.

---

## (b) Tier-1 same-document comparison + the strength of the contrastive prior (F5)

### First, a finding that shrinks the decision

**Tier 1 already compares same-document pairs. There is nothing to build for that half of F5.** Candidate
generation is five sources of blocks over the whole entity inventory (`cluster._candidate_pairs:151-203`) with
**no document dimension anywhere** — zero code hits for `doc_ref`/`doc_id`/`document` across all of `resolve/**`.
So no filter excludes intra-doc pairs today, and none will after the re-key. F5's "so Tier-0 under-binding can
rejoin" is satisfied by the absence of a filter, not by new code. The plan should stop budgeting for it.

What *is* missing is the **contrast** half, and its carrier.

### The carrier for "same document"

`Entity` has no doc field (`entities.py:96-112`); `eid` is `ent:{type}:{name}` globally (`:180`); the doc ref is
dropped by omission at `entities.py:193-199` (`AttrClaim`) and `:204-213` (`Edge`), both with the `ClaimRecord`
`c` in scope and `c.doc_ref` available (`schemas/claim.py:117`, normaliser `doc_refs()` at `:146-148`).

**Is doc-sameness derivable from atom membership? Verified: partially, and not reliably enough to rely on.**
Referent atoms *are* doc-local by construction, but two provisional instances from the same document have
**different** referent atoms — so referent equality tells you nothing about doc-sameness. The claim atom id does
encode the document: `make_claim_id(doc, locator, index)` produces `<doc>-<locator>[-index]`
(`schemas/ids.py:19-30`), so the doc token is the first kebab segment. Doc-sameness is therefore *string-parseable*
from `Entity.claim_ids` — and I reject that: it makes a load-bearing identity decision depend on parsing an id
format, which is precisely the coupling the re-key exists to remove.

**Recommendation: add `Entity.doc_ids: frozenset[str]`**, populated at the single boundary where the reference is
currently dropped (`entities.py:188-213`, from `c.doc_refs()`). One field, one population site, no new plumbing.

Why it is load-bearing rather than nice-to-have: three consumers need it, and two are correctness, not reporting.
(1) It scopes the contrast channel so a doc-local contrast cannot leak onto cross-doc pairs through
`_matching_eids`' global name expansion (`resolve/__init__.py:232-241`, `:643-644`) — this is R-a2 as well.
(2) `plan/01 §8` requires the bake-off to **measure coref over/under-binding**; intra-doc binding cannot be
measured without a doc axis. (3) D-13.12's coverage surface has to report the intra-doc fragmentation tail.

### The carrier for "stated contrast" — and why it is *not* a stated `distinct-from`

`_claim_distinct_pairs` (`resolve/__init__.py:567-575`) turns source-stated `distinct-from` claims into members
of `veto` — **hard, transitive, ungraded, un-type-gated by design** (`:570-573`; transitivity at
`cluster.py:363-370` and re-applied in `finalise`, `:638-648`).

**A syntactic contrast is strictly weaker than a stated `distinct-from`, so it must not ride that rail.** Three
reasons:
- *Different speech acts.* `distinct-from` is the source asserting a proposition about two named things ("not to
  be confused with", "a separate unit"). An enumeration ("two batteries, one at X, one at Y") or "another
  battery" is the source **individuating referents in its own discourse** — an artefact of how it narrates, not
  a claim about the world. A single document can enumerate two mentions that a *better* source later shows to be
  one thing observed twice.
- *Transitivity is fatal here.* A veto is transitive, so one wrong contrast propagates across a whole cluster
  and shatters legitimate merges. That is the exact failure mode `config/resolution.yaml:319-324` documents for
  exact-match walls ("SHATTERS legitimate merges"). An extractor's reading of "another" is not evidence worth
  transitive authority.
- *It is a model judgement with no numeric confidence.* Same provenance class as a coref category
  (`coref.py:69`) — and coref categories are deliberately kept off the veto rail.

**So the contrast needs its own channel.** Mechanism, reusing coref's architecture rather than inventing one:
extend the forced tool with a second list (`CoreferenceClusters`, `coref.py:101-104`) —
`contrastive_pairs: [{member_ids: [int, int], evidence: str, licensing_quote: str}]` — with the same
deterministic rails as clusters (quote must occur in the document, `_quote_supported:258-260`; same-type only,
`_type_compatible:263-266`; must not contradict an accepted positive cluster). Emit on a **new dedicated lane**
`coref-distinct-from`, declared in `config/ontology.yaml` beside `coref-same-as` (`:164-168`), symmetric,
non-`extractor`. This keeps the *stated* and the *read* anti-identity signals on separate rails, exactly the
reasoning that put `coref-same-as` on its own lane rather than on `same-as` (`coref.py:20-27`).

Note the design's third example, "distinct designations", needs **no** channel at all — under decision (c) it is
a composite hard-ID clash and walls on its own.

### The strength: hard wall vs score penalty vs band cap

- *Hard wall* — rejected. Transitive (`cluster.py:363-370`), so one wrong "another" shatters a cluster; and it
  removes the pair from the analyst's sight entirely (a veto is "not even queued", `resolution.yaml:227`), which
  is wrong for a signal this soft.
- *Score penalty* — rejected. It requires either reviving `attribute_scoring.conflict_penalty` (wrong grain: that
  branch is per-*attribute*, `scoring.py:444-456`, and it is dead because the key is absent) or adding a new
  per-pair penalty into `merge_score`. Both put a **tuned float** between an over-merge and the analyst, in a
  place where the *guarantee* we want ("never auto-merges") must not be reconstructible-away by a high relational
  score. It also pollutes `merge_breakdown`, which is persisted into provenance (`cluster.py:381`, `:569`).
- **Band cap — recommended.** Copy the established in-repo pattern for "a signal class limits the verdict":
  `perishable_capped: dict[Pair, str]` (declared `cluster.py:443`, set `:492`, forced to `hitl` at `:541-542`)
  and the name-alone demotion (`:560-564`). Thread a `contrast_capped: Mapping[Pair, str]` argument into
  `resolve_entities` exactly as `raise_walls: Mapping[Pair, str]` already is (`cluster.py:313`), and demote the
  band.

**Ceiling: `probable`.** A contrasted pair may reach the analyst's desk carrying the enumeration quote; it may
never auto-merge. Defensible on general principle, and note *what the config value is*: **a band name, not a
number.** There is no threshold to tune, no interaction with `merge_weights`, and no way for a strong relational
score to climb past it. Rationale in one line: the machine's authority to *fuse* two referents a source took
care to individuate is exactly what we are unwilling to grant; its authority to *ask* about them is exactly what
recall-biased triage wants.

I deliberately do **not** cap at `possible`: that hides the pair from the analyst (`possible` is explicitly "OFF
the analyst's desk", `resolution.yaml:32`), which converts a live disagreement into silence. And a bare same-doc
pair with *no* stated contrast gets **no** cap — neutral, judged on merits, per F5. Its protection against the
OOB-undercount harm is the separate co-location cap (G16, decision (c)), which is where that harm actually lives.

### Mechanism table — (b)

| config file | key | value shape | function touched | exists? |
|---|---|---|---|---|
| `config/resolution.yaml` | `coref_contrast_ceiling` | `probable` (enum: `confirmed`\|`probable`\|`possible`) | **new** accessor on `ResolveConfig`; consumed in the band step (`cluster.py:533-566`) via a `contrast_capped` demotion map modelled on `perishable_capped` (`:443`,`:492`,`:541`) | **new — the only new key in (b)** |
| `config/ontology.yaml` | `edge_types += {name: coref-distinct-from, symmetric: true}` | YAML row beside `coref-same-as` (`:168`) | `edge_direction.direction_map`; a new `_coref_contrast_pairs()` in `resolve/__init__.py` mirroring `_coref_pairs` (`:616-661`) | **new** |
| — (tool schema) | `CoreferenceClusters.contrastive_pairs` | `list[{member_ids, evidence, licensing_quote}]` | `coref.CoreferenceClusters` (`:101-104`), `SYSTEM` (`:107-151`), new `valid_contrasts()` mirroring `valid_clusters` (`:279-325`), emission in `coref_claims` (`:342-399`) | **new** |
| — (record field) | `Entity.doc_ids: frozenset[str]` | populated from `ClaimRecord.doc_refs()` (`schemas/claim.py:146-148`) | `resolve/entities.py:96-112` (field), `:188-213` (population — the boundary where the ref is dropped today) | **new** |
| `config/credibility.yaml` | `coreference.emit_contrasts` | `bool`, target `true` | `coref.propose_coreference` (`:433-470`) | **new** |

### Residual risk — (b)

- **R-b1 (medium).** An enumeration ("two batteries") individuates referents the extractor may not be able to
  attach to *specific* mention ids — the model must name a pair, and a bare plural has no second mention to
  name. So the contrast channel will fire on "another battery" and on distinct designators, and miss bare
  plurals. Bare plurals then fall back on the co-location cap. Acceptable; state it.
- **R-b2 (medium).** The ceiling is keyed on the original `Pair` and does **not** lapse when a side later gains
  cross-document corroboration. I judge that correct (later evidence that A and B are each real does not unsay
  the enumeration), but it is a deliberate choice with a cost: a genuinely-wrong contrast is permanently capped
  until an analyst overrides it. The override path must therefore be live — and per A6 it keys on atoms.
- **R-b3 (low).** `finalise` (`cluster.py:633-648`) re-unions from scratch over `sorted(res.same_as)` and
  enforces only `_veto_eid_pairs` — **not** the cap maps. Since a capped pair never enters `same_as`, this is
  currently safe, but it is a latent hole: any future path that writes a capped pair into `same_as` would slip
  past `finalise`.

---

## (c) Discriminator priority for cross-doc clustering

### How priority manifests — three shapes, mapped rung by rung

There is **no** cap-by-signal-class mechanism in resolve today; the only precedents are two band demotions
(`perishable_capped`, `cluster.py:443`; `name_alone_caps_at_possible`, `:560-564`) and a 0–1 range clamp
(`scoring.py:641-642`). So "caps" is new machinery, built once and reused by three rungs.

| rung | score weight | cap | wall |
|---|---|---|---|
| **designation** (composite: operator + designator) | — (it should not need a weight; it is a fast path) | *satisfies* the perishable cap (non-perishable ⇒ a confirm may rest on it) via `has_durable_identity_support` (`scoring.py:265`) | **hard-ID clash wall** on differing composites, drawn into `veto` so it is transitive |
| **operator** | `discriminator` weight (post-split) | perishable cap does **not** apply (operator is durable) | **critical-attribute wall**, credibility-gated (`_critical_attribute_walls`, `resolve/__init__.py:490-529`; floor `critical_veto_min_grade: C`, `resolution.yaml:370`) |
| **geography** | `discriminator` weight | **perishable cap: perishable-only evidence ≤ probable** (D-13.9(a)) | **geo veto** (`scoring.geo_conflict_km:49-78`; tolerances `resolution.yaml:238-240`) |
| **relational** | `merge_weights.relational` (0.40); per-type suppression via `ontology.identity.relational: false` (`ontology.yaml:113`) | **co-location cap: shared-anchor-only support ≤ probable for the formation citizen** (D-13.14 / G16) | — (never a wall; a shared neighbourhood is never anti-identity) |
| **name** | `merge_weights.name` (new signal, 0.20), rarity-graded | **hard ceiling at `possible`, every layer** (D-13.10) | — (name is never a wall; only a blocking key) |

### The designation rung — what must exist, and is a designation a unique identifier?

**It is not, on its own. It is a unique identifier only when scoped by operator.** The argument is general, not
data-derived: unit designations are reused across armies (every army has an 8th Battalion), reused across time
(a designation is reassigned when a formation is disbanded and re-raised), and reused across echelons. A bill of
lading is globally unique by issuance; "8th AD Bn" is unique only *within one operator's order of battle at one
time*. So:

- **Bare `unit.designator` = a non-perishable discriminator.** It *satisfies* the perishable cap — a confirm is
  permitted to rest on it (D-13.9(a) demands a non-perishable leg) — but it still has to clear the band on
  corroboration. **One shared designation string can never confirm a formation merge.**
- **`(service_branch, designator)` = a unique identifier.** It earns the fast path to confirmed (D-13.9), the
  hard-ID block, and the clash wall.

This resolves an apparent tension in the working-assumption ladder: designation and operator are not really two
rungs. The top rung is the **composite**, and "designation > operator+geo" means *the composite outranks the
loose conjunction* — not that a bare designator beats an operator.

**Mechanism.** `hard_id_fields` is absent, so `_shared_unique_id` is constant `False` (`scoring.py:207-219`) and
hard-ID blocking never fires (`cluster.py:174-178`, `propose.py:55`,`:71`). Declaring it is a **value-only**
change to a key nothing reads today — zero migration risk — but its *shape* must widen from `list[str]` to
`list[list[str]]` so an inner list is an **AND-key** (all fields stated and equal):

```yaml
hard_id_fields:
  unique:
    unit:                    [[service_branch, designator]]   # composite: operator-scoped designation
    contract_import_event:   [[bol_reference]]                # genuinely globally unique
  categorical:
    unit:                    [[echelon]]                      # blocking only, never identity
```

Three call sites take a small loop each (`scoring.py:215-218`, `cluster.py:174-178`, `propose.py:54-58`/`:70-74`),
and the block key becomes the tuple of stringified values. Note `_shared_unique_id` compares with bare `==` on
raw values (`scoring.py:217`) — so it is **downstream of the normalization below**, not independent of it.

Separately, the **clash wall** is new. `_identifier_veto` (`resolve/__init__.py:460-485`) reads the ontology's
`identifier_patterns` against the entity **name**, not attrs — so an attr-level hard-ID clash wall does not exist.
Add `_attr_identifier_veto()` beside it, unioned into `veto` (`:159-163`) so it is hard **and transitive** —
appropriate here precisely because a composite identifier clash is a structural, not a stylistic, disagreement.

### The operator rung + value normalization

`config/resolution.yaml:319-324` states the blocker outright: `service_branch` appears as 'Air Force' / 'PAF' /
'Pakistan Air Force', `origin_country` as 'CHINA' vs 'China', and because a critical veto compares values
**exactly** (`attribute_is_conflict`, `scoring.py:99-101`), walling on them "SHATTERS legitimate merges". That
is why `variant.operator_branch` is the only `critical` attribute (`:327`) and it walls **zero** pairs. Value
normalization is the prerequisite that makes walling safe — not a nicety.

**Where it lives:** `config/resolution.yaml`, a new `value_normalization` block. Not a new file: the surfaces
that consume it are all in `resolve/`, `resolution.yaml` is already hot-config, `extra="allow"`
(`schemas/base.py:25-28`) means no schema amendment and no loader change, and one file keeps the analyst's
mental model single. **Shape: per-attribute canonical → aliases — deliberately the same shape as the existing
`alias_table`** (`resolution.yaml:88`), so an analyst who can edit one can edit the other:

```yaml
value_normalization_case_fold: true          # 'CHINA' ≡ 'China' needs no enumeration
value_normalization:
  service_branch:
    "Pakistan Air Force": [PAF, "Air Force", "PAF air defence units"]
    "Pakistan Army":      [Army, PA, "Pakistan Army Air Defence", PAAD]
  origin_country:
    China: ["People's Republic of China", PRC, CN]
  operator_branch:
    PLAAF: ["PLA Air Force", "People's Liberation Army Air Force"]
```

Per-attribute, not per-type: 'PAF' means the same thing wherever it appears, and per-type would force the
analyst to repeat every class on every type that carries the attribute.

**Where it must apply — three surfaces, and applying it to only one is worse than applying it to none.** The
recon establishes there is exactly one chokepoint for *conflict* but not for *comparison*:
1. **Conflict:** `attribute_is_conflict` (`scoring.py:99-101`) — one edit covers the critical wall,
   `critical_conflict_disposition`, `has_hard_conflict`, and the agreement loop.
2. **Agreement / identity:** `has_durable_identity_support` (`scoring.py:271`) and `_shared_unique_id`
   (`scoring.py:218`) each do their own bare `==`.
3. **Namespace derivation:** `Entity.namespace()` (`entities.py:114-120`) and `namespace_compatible`
   (`:123-131`).

**Yes — it must apply before conflict detection AND before namespace derivation, and this is not optional.**
Normalizing only the conflict rail produces the worst of both worlds: 'PAF' and 'Pakistan Air Force' would stop
*conflicting* but would still derive **two different namespaces**, and namespace mismatch gates the exact-name
bootstrap (`cluster.py:453`), `_identity_pairs` (`resolve/__init__.py:596`), `_coref_pairs` (`:654`) and
`_name_containment` (`cluster.py:261`) — so the wall would be fixed while blocking and bootstrapping stayed
shattered. G18's current wording ("normalization fires before the wall is tested", `plan/01 §5`) names one
surface and should name three.

**One population point, raw preserved:** add `Entity.attrs_norm: dict[str, Any]` alongside `attrs`, populated in
the same loop at `entities.py:188-200` via a pure `normalize_value(attr, value, cfg)` in `resolve/normalize.py`
(beside the existing name `normalize`, `:30-33`). `attrs` and `attr_history` keep the verbatim surface form for
display and provenance; the three comparison surfaces read `attrs_norm`. This is a single new field with a single
writer — the same discipline as `place_of` being computed once so "every consumer reads this same map, so they
agree by construction" (`resolve/__init__.py` comment at the place pass).

**Extensibility / hot-config:** `rebuild()` reads a live config store per the project's hot-config rule, and
`resolution.yaml` is already in it, so an analyst-added equivalence class takes effect on the next rebuild with
no restart. The natural learning loop — an analyst-confirmed *attribute-value* equivalence growing
`value_normalization` the way a confirmed merge grows `alias_table` — is **roadmap, not build**: it needs a
decision-log key shape, which is A6's territory.

Once normalization ships, promote `unit.service_branch` and `trading_org.origin_country` from `supporting` to
`critical` (`resolution.yaml:333`, `:341`) — the config comment already says that is the intent and names
normalization as the blocker. Note `supporting` is inert today anyway (`attribute_scoring` absent ⇒
`scoring.py:444-461` unreachable), so nothing is lost by moving them.

### The relational rung and F9 — **accept the gap; roadmap the fix**

The naive fix does not work, and this is worth stating precisely because both docs imply it is a weighting
problem. A shared neighbour only becomes a *key* when `canonical(x) == canonical(y)`
(`scoring.py:371`, `:373`). Two endpoints in different clusters therefore produce **two different keys** and
never enter `shared` (`:534`) at all — `pair_confidence` is never consulted for them, so the obvious edit at
`cluster.py:395-396` (return a discounted value instead of `0.0`) is **unreachable code** for sub-confirmed
pairs. A real fix needs (1) a soft-match pass over the non-shared keys at `scoring.py:534`, pairing keys with
equal `(predicate, direction)` whose canonicals are latently linked, and (2) latent links that *exist before
scoring* — they do not: `res.candidates`/`res.possible` are filled in the collection loop (`cluster.py:512-585`)
which runs *after* the Phase-2 fixpoint. So the minimal honest fix is a second scoring stage with its own
determinism argument.

**Recommendation: accept, disclose, roadmap.** Three reasons on general principle: the design's own lever 2
works via anchors that resolve into *real* merges (spine/13 §6 says designs and places resolve cleanly); RK-COREF
is already the heaviest stage in the chain; and a half-fix yields a score that depends on fixpoint iteration
order, which is a determinism risk (G2) traded for a recall gain.

**What is thereby NOT available, in words for the design-note disclosures:** *"Our relational identity signal
counts only anchors that actually merged. Two reports of the same battery whose only connection runs through a
site the resolver rates merely* probable *look relationally unrelated — they get exactly zero relational credit.
So instance-layer fragmentation is systematically worse wherever the anchor layer is itself uncertain. We report
that as a measured coverage gap rather than closing it by loosening a threshold."*

**And a second, sharper instance of the same class, which the docs do not mention at all.** `places.augment` —
the pass that merges two basing_site entities resolving to one gazetteer anchor — runs at
`resolve/__init__.py:181`, **after** `resolve_entities` at `:177-179`. So place merges are absent from
`merge_edges` and from the union-find that `canonical` reads during scoring, and are invisible to
`_bottleneck_confidence` (`cluster.py:270-303`). Two units based at differently-named-but-identical sites do
**not** share a neighbour key while being scored. spine/13 §6 lever 2 names places as one of the two clean
anchors the fuzzy instance layer crystallizes onto; mechanically, they are not one. **This one is worth fixing in
S3, and it is cheap:** seed the union-find with the place-anchor merges *before* the fixpoint (a Phase-0 seed
derived from the `place_of` map already computed at `:126`), rather than appending them to `same_as` afterwards.
Ordering only, fully deterministic, no new score.

### The name rung — capping it requires separating it from attribute agreement

`attribute_score` **fuses** the two: it computes name similarity at `scoring.py:399` and attribute agreement at
`:436-437`, and they meet at exactly **one line** — `sim = max(sim, agreeing / present)` — then get scaled by one
shared `penalty` at `:463`. Consequences:
- The existing `_name_alone` test ("the only nonzero identity signal is `attribute`", `cluster.py:140-148`) is
  **both over- and under-inclusive**: a pair with a perfect name *and* real discriminator agreement is still
  "name alone" (so it is wrongly capped), while a pair with a weak name but perfect discriminator agreement is
  *also* capped (also wrongly — discriminator agreement is not a name).
- So D-13.10's "name capped at possible for every layer" is **not actually enforced today** even with
  `name_alone_caps_at_possible: true` (`resolution.yaml:154`), because what is capped is not "name."

**Mechanism: split the signal.** `attribute_score` returns two numbers (or a small record); `merge_weights` gains
`name` and renames `attribute` → `discriminator`; `rconfig.SIGNALS` (`:25-29`) gains the member. This is a
one-caller change — `attribute_score` has exactly **one** production caller, `scoring.py:632` inside
`merge_score` — and it is safe downstream because `_deterministic_total` (`cluster.py:68-78`) and
`identity_ledger` (`scoring.py:645-663`) both iterate `SIGNALS` explicitly. `_name_alone` then becomes trivially
correct: "`name` is the only nonzero signal."

**Weights, derived from stated invariants rather than measured** — the idiom `resolution.yaml:5-18` already uses:

- I1 name alone must not reach the analyst on its own;
- I2 no single signal class may reach `auto`;
- I3 any two of {name, discriminator, relational} at perfection must reach the analyst;
- I4 the deterministic ceiling (everything except the raise-only identity term) equals `auto_merge` exactly, so
  the fuzzy path auto-merges only on simultaneous perfection (the shipped doctrine, `:10-12`).

`{name: 0.20, discriminator: 0.20, relational: 0.40, temporal_consistency: 0.05, source_asserted: 0.15}` with
bands unchanged (`auto 0.85 / hitl_low 0.45 / possible_floor 0.25`):

| case | deterministic total | band |
|---|---|---|
| name only | 0.20 + 0.05 = **0.25** | `possible` (== `possible_floor`) ✓ I1 |
| discriminator only | 0.25 | `possible` |
| relational only | 0.40 + 0.05 = **0.45** | `hitl` (== `hitl_low`, unchanged from today) ✓ |
| name + discriminator | 0.45 | `hitl` ✓ I3 |
| name + relational / discriminator + relational | 0.65 | `hitl` |
| all three | 0.85 | `auto` ✓ I2, I4 |

The 0.20/0.20 is not a tuned pair: it is the existing 0.40 `attribute` weight split **evenly**, because there is
no principled a-priori reason to rank name above discriminator agreement, and the even split is exactly what
makes I1 land on `possible_floor` and I3 land on `hitl_low`. Every number is the solution to a stated invariant.
Name still keeps its recall role untouched — it remains a `blocking_keys` member (`resolution.yaml:83-86`) and
drives the all-pairs alias/containment sweep (`cluster.py:196-201`).

**Rarity is unimplemented and must be built or the decision reworded.** D-13.2 and D-13.10 both promise a
"rarity-graded" name contribution. `grep -rni "rarity|idf|tfidf"` over `backend/chanakya/` returns **nothing** —
there is no rarity mechanism anywhere. Minimal no-embedding mechanism: a multiplier on the `name` signal derived
from the inverse document frequency of the pair's shared name tokens **over the graph's own entity-name
inventory** — a pure function of the graph, deterministic, no external corpus, no vector. Config:
`name_rarity: {enabled: true, floor: 0.25}` (the multiplier a maximally-common token receives). This is the
general form of a guard the config already hand-codes: `containment_min_short_tokens` exists because "'China' is
a prefix of half the manufacturer list and bridged CPMIEC into CASIC" (`resolution.yaml:188-190`).

### Per-layer profiles — shape, and how it composes

`auto_merge_for_pair` (`rconfig.py:129-148`) is the existing per-type hook, and its per-type-ness is a `float(v)`
coercion at `:148`, not a structural limit. Richer per-type rows are already idiomatic in this file
(`attribute_roles` two-level dict, `geo_conflict_max_km` and `place_allowed_precision_classes` with a `default`
row). So the profile is a new key plus one accessor — no schema amendment (`extra="allow"`), no loader change.

```yaml
layer_policy:
  default:  {auto_merge: 0.85}
  design:   {auto_merge: 0.45}          # collapses readily; one more signal past a name clears it
  instance: {auto_merge: 0.85, require_non_perishable_for_confirm: true}
caps:                                   # categorical ceilings — no floats
  name_alone:        possible           # D-13.10, every layer
  perishable_only:   probable           # D-13.9(a)
  co_location_only:  probable           # D-13.14 / G16 — formation citizen only
  same_doc_contrast: probable           # decision (b)
```

`design: 0.45` is derived, not chosen: under the weights above, a design-layer name match plus **one** shared
component scores `0.20 + 0.40·(1.0·1/2) + 0.05 = 0.45` (the `relational_support_k: 2` discount,
`resolution.yaml:81`, halves a single shared neighbour). So `0.45` is precisely the statement "a name plus one
trivially-available corroborating signal clears the design layer, and a name alone does not" — which is D-13.10's
sentence, arithmetically. Nothing measured.

**Composition, not duplication.** `auto_merge_for_pair` gains one rung, preserving precedence
most-specific-wins: (1) cross-type ⇒ global (`:144-145`, unchanged); (2) `auto_merge_by_type[etype]` (`:146-147`)
— **still wins**; (3) **new** `layer_policy[layer_of(etype)].auto_merge`; (4) global `bands.auto_merge` (`:148`).
The shipped `auto_merge_by_type: {manufacturer: 0.37, trading_org: 0.37}` (`:64-66`) are both design-layer types,
so once `layer_policy.design` lands those two rows become redundant; they should be **deleted** by the config
pass rather than left to shadow the layer rule, so there is one number per statement.

The `caps` block replaces the ad-hoc `name_alone_caps_at_possible` bool (`:154`) and unifies it with
`perishable_capped` (`cluster.py:443`), so all four ceilings run through one demotion map
(`dict[Pair, tuple[str, str]]` — ceiling plus reason) and one band-downgrade step. The `co_location_only`
detector is new: true when the pair's only nonzero non-name signal is `relational` **and** every shared
neighbour key (`scoring.py:371-373`) points at a design / place / operator anchor — computable from the
neighbour keys the scorer already builds plus the A2 layer tag.

**One ordering hole the plan must fix.** `auto_merge_by_type` is applied at three sites (`cluster.py:480`,
`:487`→`:434`, `:532`) but **not in Phase 1** — the bootstrap does not band at all (`:446-465`); it merges at
1.0 on `_shared_unique_id` ∨ `alias_idx.equivalent` ∨ exact-normalized-name ∨ `_name_containment` ∨
`authoritative`. So a per-layer *floor* cannot restrain the strongest lane. `plan/01` puts the per-layer policy
in **S3** and the bootstrap cut in **S4** — meaning D-13.10 is a no-op for one stage. Fix cheaply in S3: make the
bootstrap's two **name** branches (`cluster.py:458-459`) layer-conditional through the same profile, so name can
never bootstrap on the instance layer even before S4 cuts it entirely.

### Mechanism table — (c)

| config file | key | value shape | function touched | exists? |
|---|---|---|---|---|
| `resolution.yaml` | `merge_weights` | `{name: 0.20, discriminator: 0.20, relational: 0.40, temporal_consistency: 0.05, source_asserted: 0.15}` | `rconfig.SIGNALS` (`:25-29`); `scoring.attribute_score` split (`:377-463`); `merge_score` (`:631-638`); `_name_alone` (`cluster.py:140-148`) | **exists — reshaped** + code split (one caller) |
| `resolution.yaml` | `hard_id_fields.unique` / `.categorical` | `{etype: [[attr, attr], ...]}` — inner list = AND-key | `scoring._shared_unique_id` (`:207-219`); `cluster._candidate_pairs` (`:174-178`); `propose.py:55`,`:71` | key **absent** (value + small loop change) |
| `resolution.yaml` | `hard_id_clash_wall: true` | bool | **new** `_attr_identifier_veto()` beside `_identifier_veto` (`resolve/__init__.py:460-485`), unioned into `veto` (`:159-163`) ⇒ hard + transitive | **new** |
| `resolution.yaml` | `value_normalization`, `value_normalization_case_fold` | `{attr: {canonical: [aliases]}}`, bool | **new** `normalize_value()` in `resolve/normalize.py`; **new** `Entity.attrs_norm` populated at `entities.py:188-200`; read by `attribute_is_conflict` (`:99-101`), `has_durable_identity_support` (`:271`), `_shared_unique_id` (`:218`), `Entity.namespace()` (`:114-120`) | **new** |
| `resolution.yaml` | `attribute_roles` promotions | `unit.service_branch → critical`; `trading_org.origin_country → critical`; `unit.designator → {role: critical, perishable: false}` | `rconfig.critical_role_attrs` (`:394-400`) | **exists — value change, unblocked by normalization** |
| `resolution.yaml` | `layer_policy` | `{default|design|instance: {auto_merge: float, require_non_perishable_for_confirm: bool}}` | **new** accessor; `rconfig.auto_merge_for_pair` (`:129-148`) gains a layer rung between type and global | **new** |
| `resolution.yaml` | `caps` | `{name_alone|perishable_only|co_location_only|same_doc_contrast: <band name>}` | unified demotion map generalising `perishable_capped` (`cluster.py:443`,`:492`,`:541`) and the name cap (`:560-564`); **new** `_co_location_only()` in `scoring.py` reading neighbour keys (`:371-373`) + the A2 layer tag | **new (refactor of two existing)** |
| `resolution.yaml` | `name_rarity` | `{enabled: bool, floor: float}` | **new** IDF-over-entity-names multiplier on the `name` signal, computed at rebuild from the graph's own inventory | **new** |
| `ontology.yaml` | per-node-type + per-attribute `layer:` | `design` \| `instance` (A2) | `ontology.NodeTypeIndex` | **new (S2)** |
| — (ordering) | — | — | move place-anchor merges to a **Phase-0 union-find seed** before `resolve_entities` (`resolve/__init__.py:177`) instead of `places.augment` after it (`:181`) | **new (small, deterministic)** |

**No runtime embeddings — confirmed.** Every mechanism above uses only: the alias table + transliteration
(`resolution.yaml:88-132`), token-sorted Jaro–Winkler (`normalize.py:46-57`), an IDF over the graph's *own*
entity-name inventory (no external corpus, no vector), config-declared discriminators and their normalization
classes, relational Jaccard over graph neighbours (`scoring.py:494-542`), gazetteer coordinates
(`resolve/geo.py`, `places.py`), and STANAG source grades. BM25 does not appear in the resolve path at all and I
add no use of it. Nothing here computes or stores a dense vector.

### Residual risk — (c)

- **R-c1 (high).** Promoting operator attributes to `critical` makes the wall live for the first time — and a
  wall is **transitive** (`cluster.py:363-370`, re-enforced in `finalise`, `:638-648`). If a normalization class
  is *incomplete*, an unlisted surface form ('PAF AD') walls transitively and shatters a whole cluster. The
  credibility floor (`critical_veto_min_grade: C`, `:370`) mitigates only *low-grade* sources, not incomplete
  config. Mitigation: the gate fixture for G18 must include a *not-in-the-table* variant and assert the
  behaviour is chosen deliberately — my call is **fall through to `raise`, not `wall`, when either value is
  outside every declared class for that attribute**, i.e. an unrecognised value is `unknown`, not "different".
  That is the same doctrine as absence ≠ conflict (`scoring.py:100-101`).
- **R-c2 (medium).** `succession.py:94-95`,`:101` groups a perishable value series by raw `==`, with an explicit
  comment that normalizing "would be a resolution decision, out of scope". Once `value_normalization` exists that
  comment becomes a *known* inconsistency: a pure re-spelling ('PAF' → 'Pakistan Air Force') reads as an ordered
  succession, i.e. a state *change*. Succession should read `attrs_norm` too. Not in (c)'s scope, but it must be
  ledgered, not left as a stale comment.
- **R-c3 (medium).** The geo veto is **not** transitive and **not** in the `veto` set (`cluster.py:360` vs
  `:363-370`; absent from `finalise`'s `_veto_eid_pairs`, `:638-648`; absent from `res.distinct_from`). So a
  geo-impossible pair still fuses **indirectly** through a third node. D-13.9 calls a geo conflict a "hard wall"
  and the config calls it "not even queued" (`resolution.yaml:227`) — mechanically it is neither, transitively.
  Small fix (materialize geo conflicts into `veto`), but it is a real behaviour change and belongs in the ledger.
- **R-c4 (medium).** The `possible` tier is documented as in-memory-only, "never drawn as a wire edge, so the
  view JSON is byte-unchanged" (`resolution.yaml:32`). Capping four signal classes at `probable`/`possible` moves
  real volume into these tiers. If the coverage surface (`coverage_gap_ratio: 2.0`, `:48`) reads
  `(probable + possible) / max(confirmed, 1)`, every cap I recommend **raises** that ratio and will fire
  collection gaps by construction. That is arguably correct behaviour, but the threshold's meaning changes under
  the caps and should be re-stated (not re-tuned) rather than silently inherited.
- **R-c5 (low).** After the signal split, `merge_breakdown` gains a key and is **persisted**
  (`cluster.py:381`, `:569`, `:585`) into the view/HITL surface — a frontend-visible contract change. Log it to
  the API↔frontend contract log.

---

## What the prototype must demonstrate

Eight input shapes. Each is a *shape*, expressible as tiny fixtures — no corpus needed, none tuned to one.

| # | shape | expected verdict |
|---|---|---|
| 1 | **Stated apposition, one doc.** "China Precision Machinery Import-Export Corporation (CPMIEC)" + a later bare "CPMIEC". | `EXPLICIT_EQUIVALENCE` → **one shared referent atom** → one rich provisional instance. No analyst item. Proves the authoritative bind. |
| 2 | **Unique anaphor to an undeclared endpoint.** One declared `unit` + "the battery" reaching the graph only as a relation endpoint; no second `unit` in the doc. | uniqueness precondition **holds** → shared referent atom; the stray `unknown` node **disappears**. Proves Tier 0's actual value. |
| 3 | **Ambiguous anaphor (the model over-reaches).** Two declared `unit`s in the doc + "the battery"; the model proposes `UNAMBIGUOUS_ANAPHOR`. | precondition **fails** → demoted to raise-only → **two** referent atoms + one queued pair carrying the licensing quote. **Never a merge.** Proves the code disposes of the model's judgement. |
| 4 | **Name variant across scripts, one doc.** "红旗-9" and "Hongqi-9". | `NAME_VARIANT` → raise-only → two referent atoms; the pair **still merges at Tier 1** via `transliteration` + alias (`resolution.yaml:127-128`). Proves the demotion costs nothing. |
| 5 | **Same-doc enumeration (contrastive).** "two HQ-9/P batteries — one at Rahwali, one at Nur Khan". | two referent atoms + a `coref-distinct-from` contrast pair; Tier 1 scores it high on shared design+operator but is **band-capped at `probable`** → analyst item with the enumeration quote, never auto-merged. **OOB count stays 2.** |
| 6 | **Co-location only, cross-doc, no designation.** Doc A and doc B each: "HQ-9/P equipment observed at Rahwali (PAF)". | **presence** merge → confirmed; **formation** not minted (no organizational evidence, D-13.13). Output: *"presence at Rahwali confirmed; formation/unit count unresolved (1–2 candidates); designation coverage needed."* G16. |
| 7 | **Scoped designation, cross-doc, two variants.** (a) doc A "8th AD Bn (PAF), Nur Khan, Jan" + doc B "PAF 8th Air Defence Battalion, Rahwali, Jun". (b) the same two at **overlapping** times. | (a) composite hard-ID `(service_branch, designator)` after normalization → **fast path to confirmed formation**; differing sites at disjoint times → the relocation ladder → *confirmed relocation* on designation continuity. (b) the same composite, but the stated `based-at` conflict at overlapping times **hard-walls** (G18) → **two** formations. Proves designation-vs-operator+geo priority and both directions of the wall. |
| 8 | **THIN CONTEXT — must degrade, not fabricate.** One line, one grade-D source: *"A SAM battery was seen near Sargodha."* No operator, no designation, no design named, city-precision geography. | mint a provisional **presence** with `operator=unknown`, `designation=unknown`, `count=unknown`, `geo_precision=city`. **No merge** with any existing presence: name alone is capped at `possible`; every discriminator is absent so there is nothing to agree on; a coarse anchor never pins to a fine site (`place_identity_precision_classes: [pad, site, terminal]`, `:248`); no formation is minted. Output: **"under-determined — insufficient evidence to attribute this sighting to a known holding; missing: operator, unit designation, site-level geolocation; next coverage due X"**, and it appears in the unresolved-instance tail. It must **not** (a) attach to the nearest HQ-9/P presence on name or proximity, (b) mint a formation, (c) be silently dropped. |

Shape 8 is the non-negotiable's test and the one the prototype exists for; shape 3 is its intra-document twin.

---

## What "characterize" means concretely — the discriminator bag

Facts §C13 are right that no characterization step exists. **Mechanism-first answer: do not add a step — enrich
the record the judge already reads.** `merge_score(a: Entity, b: Entity, graph, canonical, cfg, ...)`
(`scoring.py:597-606`) already takes `Entity` everywhere; a parallel "characterization object" would need a
second plumbing path through five call sites. The bag is `Entity` + **two new fields** + **three derived
accessors that read neighbours** (which the scorer already walks via `graph.incident`, `entities.py:163-164`).

| field | populated from | when the source is silent |
|---|---|---|
| `citizen` / `layer` | the A2 `layer` tag on the node type + which edge materialized it (`observed-at` → presence, `based-at` → formation) | never silent — static from the ontology |
| `designation` | `unit.designator` (`ontology.yaml:76`) via `Entity.attrs` / `attrs_norm` | `unknown`; the instance is flagged **under-individuated**; never a conflict, never a wall (D-13.8) |
| `operator` | `unit.service_branch` (`:76`) / `variant.operator_branch` (`:60`) / `trading_org.origin_country` (`:52`), read from **`attrs_norm`** | `unknown`; `namespace()` stays unstated, and `namespace_compatible` already treats unstated as a wildcard (`entities.py:123-131`) — so absence widens comparison, never blocks it |
| `geo` (derived) | `basing_site.coordinates` (`ontology.yaml:79`) reached through the `observed-at`/`based-at` neighbour, plus `place_ref` | `unknown`; the geo veto never fires — absence ≠ elsewhere, already the rule (`scoring.py:75-77`) |
| `geo_precision` | the gazetteer anchor's `precision_class` (`config/places.yaml`) | `unknown` ⇒ treated as coarsest ⇒ never constitutes identity (`place_identity_precision_classes`, `resolution.yaml:248`) |
| `time_window` | `AttrClaim.event_time` / `report_time` (`entities.py:75-76`) + `Edge.latest_iso` (`:140`) | open-ended; temporal exclusivity untestable ⇒ relocation stays at *possible relocation* (D-13.14's ladder) |
| `count` | a **sourced** attribute (`unit.count_state`, `contract_import_event.quantity`) | `unknown`, default ≥1 — **never** derived from how many reports merged (D-13.13) |
| `design_anchor` (derived) | the `equips` / `inducted-into` / holding neighbour = the shared design node | `unknown` ⇒ the instance loses its strongest relational anchor ⇒ goes to the coverage tail |
| `name` | `Entity.name` (`:100`) | never silent — but demoted to a **label + blocking key**, rarity-graded, capped at `possible` |
| `doc_ids` | **new**: `ClaimRecord.doc_refs()` (`schemas/claim.py:146-148`) at `entities.py:193`/`:204` | never silent |
| `referent_ids` | **new**: the A1 referent field | absent on pre-baked fixtures ⇒ claim-atom fallback (A5) |
| `source_set` / independence | `Entity.source_ids` (`:103`) + `sources.yaml` grades + spine/04 independence groups | unknown source ⇒ `identity_source_weight_default: 1.0` (`resolution.yaml:138`) |
| `attrs_norm` | **new**: `normalize_value()` over `attrs` at `entities.py:188-200` | passthrough of the raw value; an unrecognised value is `unknown`, not "different" (R-c1) |

The uniform silence rule, stated once: **absent ⇒ `unknown` ⇒ recorded as a named gap, never fabricated, never a
conflict, never a wall** (D-13.8). Mechanically this is already the doctrine at three of the four rails
(`scoring.py:100-101` absence ≠ conflict; `:424-425` absence excluded from the agreement ratio; `:75-77` no
coordinate ⇒ no geo veto; `entities.py:123-131` unstated namespace ⇒ wildcard). The new fields must inherit it,
and the *reporting* half — surfacing "under-individuated: operator unknown" as a coverage item — is the piece
that does not exist yet.

---

## Drift — what these facts falsify in `spine/13` / `plan/01`

1. **D-13.9's "unique identifier ⇒ fast path to confirmed" is not wired at all.** `hard_id_fields` is absent from
   `config/resolution.yaml`, so `_shared_unique_id` is constant `False` (`scoring.py:207-219`) and hard-ID
   blocking never adds a block (`cluster.py:174-178`, `propose.py:55`,`:71`). spine/13 §7's "Reuse vs. new" lists
   three missing things and omits this one; it reads as existing machinery.
2. **spine/13 §7's "the machinery for two of the three already exists (the attribute-role wall …)" overstates it.**
   The wall walls **zero** pairs (`variant.operator_branch` is the only `critical` attr and no variant states it,
   `resolution.yaml:328-330`), and its graded half is dead config — `attribute_scoring` is absent, so
   `scoring.py:444-461` is unreachable and every `supporting` role is pure documentation.
3. **The geo veto is neither transitive nor a member of `veto`.** `geo_conflict_km` is consulted only inside
   `vetoed()` (`cluster.py:360`) and never enters the `veto` set, so `violates_veto_transitively` (`:363-370`),
   `finalise`'s guard (`:638-648`), the bridge alarm and `res.distinct_from` all ignore it — a geo-impossible pair
   still fuses through a third node. D-13.9 calls it a hard wall; `resolution.yaml:227` says "not even queued".
   Both overstate it.
4. **There is no document dimension anywhere in `resolve/**`** (zero code hits for `doc_ref`/`doc_id`/`document`;
   all 20 grep hits are prose). spine/13 §6's Tier-1 same-doc comparison presumes one. Two corrections: the
   comparison itself needs *no* new code (no filter exists to remove), but any doc-scoped *policy* needs a new
   carrier — and `Entity` drops the available `ClaimRecord.doc_ref` by omission at `entities.py:193-199`/`:204-213`.
5. **The Tier-0 grading vocabulary in the docs does not exist in code.** spine/13 §10/§13 grade "explicit-
   equivalence / **apposition**" against "a bare **pronoun chain**". There are exactly three model-chosen
   categories (`coref.py:74-77`); apposition is *inside* `EXPLICIT_EQUIVALENCE`'s prompt text (`:123-125`) and
   pronouns are inside `UNAMBIGUOUS_ANAPHOR` (`:128-130`). Also the category is **per-cluster, not per-link**
   (`:377`), so "closure over authoritative links only" is not expressible as written.
6. **The reversibility requirement has no stated mechanism, and as written S3 makes intra-doc over-merge
   permanent.** spine/13 §4 requires a coref cluster to stay challengeable ("the §5 split fires on it"); A1 mints
   the referent atom per cluster and D-13.11 says atoms never split. Neither doc says the rebuild **may decline a
   referent grouping** and fall back to claim-atom granularity. It must, and the check is new code — an
   intra-referent conflict is currently *invisible* because `attrs` is first-claim-wins scalar
   (`entities.py:189`) and the losing value lands only in `attr_history`.
7. **G18's normalization clause names one surface; there are three.** Conflict (`scoring.py:99-101`) is a genuine
   chokepoint, but agreement (`:271`, `:218`) and namespace derivation (`entities.py:114-131`) each do their own
   bare `==`. Normalizing only the wall leaves blocking and the exact-name bootstrap shattered — i.e. G18 could
   pass while the mechanism it guards is half-built.
8. **F9's framing implies a weighting fix; mechanically it is a candidate-key fix.** A sub-confirmed link
   produces **two different neighbour keys** (`scoring.py:371`,`:373`), so it never reaches `shared` (`:534`) and
   `pair_confidence` is never consulted — the obvious edit at `cluster.py:395-396` is unreachable code for exactly
   the pairs it targets.
9. **A second, unmentioned instance of the same class: place merges are invisible during scoring.**
   `places.augment` runs at `resolve/__init__.py:181`, **after** `resolve_entities` (`:177-179`), and appends
   directly to `res.same_as` (`places.py:391`) — so place merges are absent from `merge_edges` and from the
   union-find `canonical` reads, and invisible to `_bottleneck_confidence` (`cluster.py:270-303`). spine/13 §6
   lever 2 names places as one of the two clean anchors the instance layer crystallizes onto. Mechanically they
   are not one. Cheap ordering fix; worth doing in S3.
10. **G16's "co-location cap" has no mechanism to plug into.** `plan/01 §7` says it "plugs into
    `_band`/`auto_merge_for_pair`" — those are a *floor* and a *scalar*, not caps. There is **no** cap-by-signal-class
    anywhere in resolve; the only precedents are two band demotions (`perishable_capped`, `cluster.py:443`;
    `name_alone_caps_at_possible`, `:560-564`). G16 must be built as a demotion map, and the plan should say so.
11. **The per-layer policy is a no-op for one stage as sequenced.** `auto_merge_by_type` is applied at three
    sites (`cluster.py:480`, `:487`→`:434`, `:532`) but **not in Phase 1** — the bootstrap does not band
    (`:446-465`), it merges at 1.0. `plan/01` schedules the per-layer policy in **S3** and the name-verdict
    bootstrap cut in **S4**, so D-13.10 cannot bind on the strongest lane until S4. Gate the bootstrap's two name
    branches (`:458-459`) on the layer profile in S3.
12. **"Rarity-graded name" (D-13.2, D-13.10) is unimplemented — there is no rarity mechanism at all.**
    `grep -rni "rarity|idf|tfidf|inverse_document"` over `backend/chanakya/` returns nothing. Either build the
    IDF-over-own-inventory multiplier proposed above, or reword the decisions to "capped contributor" and drop
    the rarity language.
13. **The raise-only story is not plumbed.** `COREF_QUOTE_ATTR = "source_quote"` is written
    (`coref.py:71`,`:378`) and read **nowhere** in `resolve/` — the only reader of `Edge.attributes` is the
    evidence-category lookup (`resolve/__init__.py:642`). `resolution.yaml:176-177` promises the analyst gets
    "the exact sentence". With two of three categories staying raise-only, that must be wired through
    `res.candidate_reasons` → `Partition.candidate_reasons` (`cluster.py:61`, `resolve/__init__.py:770`).
14. **`_coref_pairs` expands coref endpoints by global name/alias match** (`resolve/__init__.py:643-644` via
    `_matching_eids`, `:232-241`), so an authoritative doc-local cluster can bootstrap-merge entities from *other*
    documents at confidence 1.0. spine/13 §4's "within-doc coref is reading, not resolution" is violated by the
    consumer, not the producer. Must be scoped by `doc_ids` in the same stage that turns the bind on.
15. **Minor:** `resolve()` accepts `prev_view` and never uses it (`resolve/__init__.py:71`/`:82`/`:101`,
    signature-only) — worth knowing before anyone plans incremental rebuild on that seam.
