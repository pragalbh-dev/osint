# RK-SPIKE — verified code facts (recon, 2026-07-24)

Established by an independent read of the **current code** on `design/resolution-redesign` @ ef22e68
(working-principles #6: docs drift, the code is the fact). Every claim below was quoted from source with a
line anchor by the recon hand; the orchestrator spot-verified the load-bearing ones. **These facts override
any contrary statement in `spine/13` or `plan/01`** — where they differ, note the drift, don't re-litigate
the design.

## A. Within-document coreference (`backend/chanakya/ingest/coref.py`)

1. **It is a prompt, not a matcher.** The only coreference signal is one forced-tool LLM call. The three
   licensing patterns live as *prose in the system prompt* (`coref.py:124-130`), not as code. There are **no
   reusable alias/apposition/acronym detectors** in the ingest pass — the sole string operation is a
   whitespace-collapsed substring test (`coref.py:253-260`). Inputs include pass-1 stated `same-as` /
   `distinct-from` pairs (`coref.py:218-226`).
2. **It emits real `ClaimRecord`s**, a star from the cluster anchor to each other member on a dedicated
   `coref-same-as` predicate, and **mints a claim id** (`make_claim_id`, `coref.py:385-392`) — never an
   entity id. Tier-3 attrs carry `_coref_cluster` (doc-local cluster id), `_coref_evidence` (category), and
   `source_quote`. `kind=inference` when a member is a declared entity (premises = those claim ids), else
   `observation`. Anchor = first *declared* member in doc order.
3. **Two independent off-switches; the second is the sharp one.**
   - Producer: `config.credibility.coreference` — the whole block is **commented out**
     (`config/credibility.yaml:186-190`), and `{}` ⇒ the pass returns `[]` (`coref.py:413-415, 443-444`).
   - Consumer: `config/resolution.yaml:180` `coref_authoritative_evidence: []`, read at
     `resolve/rconfig.py:288-301`. With it empty, `_coref_pairs` routes **every** pair to `raise_only`,
     never `authoritative` (`resolve/__init__.py:657-660`). So enabling the producer alone changes nothing.
   - Call site is inside `extract_document` (`ingest/extract.py:1758-1762`), so live *and* keyless-seed
     paths inherit both gates.
4. **Coref categories already exist — three of them**, as module-level literals
   (`coref.py:74-77`): `EXPLICIT_EQUIVALENCE`, `NAME_VARIANT`, `UNAMBIGUOUS_ANAPHOR`. They are
   **duplicated, not imported**, on the resolve side (`resolve/scoring.py:43-46`), validated by
   set-membership only (`coref.py:303-305`), and **chosen by the model**, not derived from a structural
   test. There is **no** separate apposition / pronoun-chain / repeated-designator category: apposition and
   acronym-expansion are collapsed inside `EXPLICIT_EQUIVALENCE`'s prompt text; pronouns fall under
   `UNAMBIGUOUS_ANAPHOR`. A finer category has **no code to derive it from** — nothing parses the licensing
   quote.
5. **No per-proposal score.** By design (`coref.py:69`: "the categorical evidence kind … never a numeric
   confidence"). The emitted claim hardcodes `model_conf=1.0` (`coref.py:396`), and a bootstrapped coref
   merge is assigned a flat `1.0` (`resolve/cluster.py:465`). Overlapping clusters resolve **first-wins**
   by arrival order (`coref.py:321-322`).

## B. The earned-identity judge (`resolve/{cluster,scoring,__init__,rconfig}.py`)

6. **Four scored signals, all weights in config.** `merge_score` (`scoring.py:631-638`) sums
   `attribute` (0.40) · `relational` (0.40) · `temporal_consistency` (0.05) · `source_asserted` (0.15)
   from `config/resolution.yaml:19-23` via `rconfig.py:103-106` (absent ⇒ 0.0).
   - `attribute_score` (`scoring.py:377-463`): alias-equivalence ⇒ 1.0, else token-sorted Jaro-Winkler
     name similarity, raised by `agreeing/present` over identity+critical+supporting attrs, × a conflict
     penalty.
   - `relational_score` (`scoring.py:494-542`): support-discounted, confidence-weighted Jaccard.
   - `temporal_score` (`scoring.py:545-547`): **binary** 1.0/0.0.
   - `source_asserted_score` (`scoring.py:550-566`): max source grade.
   **DEAD CONFIG (grep count 0 in `config/resolution.yaml`):** `attribute_scoring:`, `attribute_rules:`,
   `hard_id_fields:`. Consequences: the soft conflict-penalty branch (`scoring.py:444-456`) **never runs**;
   the legacy identity/conflict/numeric-conflict lists are empty; **`_shared_unique_id` is always False**
   (`scoring.py:215-219`) — i.e. **the "shared unique identifier ⇒ fast path to confirmed" mechanism is
   not wired**.
7. **Three bands, not five.** `_band` (`cluster.py:96-101`): `auto` if `_deterministic_total ≥ floor`;
   else `hitl` if `total ≥ hitl_low` or a raise fired; else `separate`. `_deterministic_total`
   (`cluster.py:78`) is `merge_score` **minus** `source_asserted` — so the identity/source term is
   structurally **raise-only**. Thresholds: `auto_merge: 0.85`, `hitl_low: 0.45`
   (`config/resolution.yaml:26-27`), `possible_floor: 0.25` (`:36`), per-type override
   `auto_merge_by_type: {manufacturer: 0.37, trading_org: 0.37}` (`:64-66`), applied only when both etypes
   match (`rconfig.py:145-148`). The verdict *names* `confirmed`/`probable`/`possible` are a **derived read
   of set membership** (`schemas/stage_io.py:112-118`: `same_as`→confirmed, `candidates`→probable,
   `possible`→possible), **not** a band. **There is no `reject` verdict** — vetoes are set membership.
8. **Walls / vetoes.** The pairwise gate (`cluster.py:357-361`) is
   `frozenset((a,b)) in veto` OR `alias_idx.barred(...)` OR `geo_conflict_km(...) is not None`.
   The `veto` set (`resolve/__init__.py:134-139, 159-163`) is composed of: configured `distinct_from` by
   name (`:244-254`; data at `config/resolution.yaml:374`), registry entity-id `distinct_from` (`:215-226`),
   gazetteer place-distinct pairs, source-stated `distinct-from` claims (`:567-575`, **ungraded and
   un-type-gated by design**), hard-identifier clash (`_identifier_veto`, `:460-485`), and
   credibility-gated critical-attribute walls (`_critical_attribute_walls`, `:490-529`; floor
   `critical_veto_min_grade: C` at `config/resolution.yaml:370`).
   - **Hard AND transitive:** only members of `veto` (`violates_veto_transitively`, `cluster.py:363-370`;
     re-applied in `finalise`, `cluster.py:638-648`).
   - **Hard but pairwise-only, NOT transitive, never drawn into `veto`:** `alias_idx.barred` (learned) and
     **the geographic veto** — `geo_conflict_km` is consulted only inside `vetoed()` (`cluster.py:360`) and
     is absent from the `veto` set, so `violates_veto_transitively`, `finalise`'s guard, the D9 bridge alarm
     and `res.distinct_from` all ignore it. Tolerances `config/resolution.yaml:238-240`
     (`default: 100`, `basing_site: 25`).
   - **Not walls at all:** cross-type is a *skip* in candidate collection with an escape hatch
     (`cluster.py:522-527`); `namespace_compatible` gates only bootstrap-exact-name, `_name_containment`
     (`cluster.py:261`), `_identity_pairs` (`__init__.py:596`) and `_coref_pairs` (`__init__.py:654`) —
     **the Phase-2 fuzzy fixpoint never checks namespace**, and relational blocking
     (`cluster.py:182-187`) generates pairs with **no namespace key**, so cross-namespace pairs can be
     scored and auto-merged.
9. **No relationship discriminator exists.** `relational_score` is a Jaccard over neighbour keys
   `(predicate, direction, canonical(other))` (`scoring.py:371-373`) where `canonical` is `uf.find`, and
   `uf.union` is called **only** inside `merge()` (`cluster.py:378-384`), reached only from Phase-1
   bootstrap and Phase-2 auto-merge. **Confirmed: `probable` (candidates) and `possible` links contribute
   exactly ZERO weight** — a candidate never unions, so its two neighbours never collapse to one key
   (this is **F9**, and it is real). `pair_confidence` reads `merge_edges`, filled only by `merge()`, so
   weight is a widest-path bottleneck over *actual unions* (`_bottleneck_confidence`, `cluster.py:270-303`).
   There is **no** comparison of two candidates' `based-at` / operator edge *values*; the only edge-derived
   anti-identity signal is the co-instance relocation exclusion (`scoring.py:337-350, 618-619`), which
   zeroes `temporal` and drops that neighbour. **There is no `operated-by` predicate in
   `config/ontology.yaml:146-159` at all.**
10. **No value normalization for attribute values; the judge sees RAW.** Conflict detection is bare `==`
    on raw attrs (`scoring.py:99-101`). `normalize` / `transliterate` / `AliasIndex` apply **only to
    `Entity.name`** (`resolve/normalize.py:30-33`, `scoring.py:395-399`). Namespace derivation also reads
    raw attrs (`resolve/entities.py:114-120`; keys `country`, `operator_branch`, `service_branch`,
    `domain`). The config states the gap outright (`config/resolution.yaml:319-321`): sources state
    `service_branch` as 'Air Force' / 'PAF' / 'Pakistan Air Force' and `origin_country` as 'CHINA' vs
    'China', and because a critical veto compares values **exactly**, walling them "SHATTERS legitimate
    merges". Consequently only `variant.operator_branch` is `critical` (`:327`), while `unit.service_branch`
    (`:333`) and `trading_org.origin_country` (`:341`) are demoted to `supporting` — **and `supporting` is
    inert** because `conflict_penalty` is unconfigured (see 6).
11. **Candidate generation (blocking) is a union of five sources** (`_candidate_pairs`,
    `cluster.py:151-203`): token/type/namespace blocks (`:166-173`; keys `type`,
    `country_or_domain_namespace`, `name_token` from `config/resolution.yaml:83-86`); hard-ID blocks
    (`:174-178`, **inert** — `hard_id_fields` absent); **relational blocking** — same-type entities sharing
    any graph neighbour, with **no namespace key** (`:182-187`); an all-pairs alias-equivalence /
    containment / acronym sweep (`:196-202`); plus injected pairs (`:203`).
12. **Fixpoint: yes.** Phase 2 loops `while changed` (`cluster.py:468-490`); terminates because merges are
    monotone (clusters only grow — rationale at `cluster.py:6-9`). `_bottleneck_confidence`
    (`cluster.py:287-303`) is a second nested label-correcting fixpoint (labels only rise). The whole
    resolver short-circuits to identity if bands are unset (`cluster.py:338-339`).

## C. Provisional-instance readiness

13. **No characterization step exists; the comparison surface is name + a flat scalar attr bag.** The judge
    compares two `Entity` objects whose entire surface is (`resolve/entities.py:97-112`):
    `eid, etype, name, attrs, claim_ids, source_ids, registry, attr_history` (+ derived `namespace()`).
    `attrs` is **first-claim-wins scalar** (`entities.py:189` `setdefault`). No operator / geography /
    designation / time bag is assembled: **geography** reaches the judge only as `attrs["coordinates"]` via
    `separation_km` inside the geo veto (`scoring.py:71-78`); **time** only as the binary relocation flag
    (`scoring.py:545-547`) plus per-value `AttrClaim.event_time/report_time` used exclusively by
    succession/credibility; **operator** only as whichever of `country / operator_branch / service_branch /
    domain` happens to be set. Everything relational is reduced to a single Jaccard number.
14. **Fields that already exist and could feed a discriminator bag.**
    - `Entity` (`entities.py:98-112`): `eid, etype, name, attrs, claim_ids, source_ids, registry,
      attr_history`.
    - `AttrClaim` (`entities.py:73-81`): `value, claim_id, event_time, report_time, source_id`.
    - `Edge` (`entities.py:135-155`): `subject, predicate, object, edge_instance, latest_iso, source_id,
      claim_id, attributes` (the verbatim tier-3 bag — already the carrier for `_coref_evidence` /
      `source_quote`).
    - Claim (`schemas/claim.py:66-72`): `EntityDescriptor{form, entity_type, name, attrs}`; provenance
      `doc_ref, source_id, kind, polarity, premises, report_time, ingest_time, attributes`.
    - Per-type attr vocabularies (`config/ontology.yaml:47-79`), e.g.
      `variant: [family, base_designator, export_designator, aliases, range_class, range_km,
      operator_branch, associated_rounds, associated_radars]`;
      `unit: [echelon, designator, service_branch, parent_unit, equipment_fingerprint, count_state,
      home_garrison]`;
      `basing_site: [coordinates, site_type, …, occupancy_state, occupancy_observed_date,
      decoy_risk_flag]`.
    - Coref's mention shape (`coref.py:156-163`): `Mention{local_id, name, entity_type, claim_id}` — **no
      attrs, no span, no doc offset**.

## D. The six traps (things a design or prototype would get wrong by trusting the docs)

1. **`coref.py` is a prompt, not a matcher** — there is no reusable structural detector to lean on, and no
   code from which a finer coref category could be derived.
2. **Two off-switches, and the consumer one is decisive** — flipping the producer alone is a no-op.
3. **The geo veto is neither transitive nor drawn into `veto`** — unlike the docs' framing of it as a veto
   "on the same footing as a curated `distinct_from`".
4. **Namespace is not a wall in the fuzzy fixpoint**, and relational blocking emits pairs with no namespace
   key — so cross-namespace auto-merges are reachable today.
5. **Half the declared scoring machinery is dead config** — `attribute_rules`, `attribute_scoring`,
   `hard_id_fields` are all absent, so the unique-id fast path, the soft conflict penalty and the
   supporting-role penalty are all inert. `variant.operator_branch` is the only `critical` attribute, and
   **no variant states it**, so the critical wall walls **zero** pairs today.
6. **There is no document dimension anywhere downstream, and no per-mention identity.** `Entity` keys on
   `ent:{type}:{name}` globally (`entities.py:180`) and pass 1 already collapses one name to one claim per
   doc (`extract.py:839` `_entity_claim_ids.setdefault(name, cid)`; plus `dedup.dedup_within_doc`,
   `dedup.py:201-228`). **"Two mentions of the same string in one document" cannot be represented today** —
   `coref.py:36-39` admits this; design docs describing per-occurrence mention ids do not.

## E. Orchestrator's reading of what these facts do to the plan

- **Micro-decision (a)** is *not* an abstract grading exercise: it is a concrete decision about which of the
  **three real categories** go into `coref_authoritative_evidence`, plus what "held looser" means mechanically
  once the referent atom is minted at ingest (atoms never merge — so a loose bind cannot be a weak merge).
- **Micro-decision (b)** has no carrier: nothing downstream knows which document a mention came from, and
  same-string same-doc mentions are pre-collapsed upstream. Any same-doc comparison or contrastive prior
  needs a new carrier decided here.
- **Micro-decision (c)**'s working-assumption ladder (designation > operator+geo > relational >
  name-as-recall) currently has: the designation rung **unwired** (`hard_id_fields` absent), the operator
  rung **unable to fire** (no value normalization), the relational rung **sub-confirmed-blind** (F9), and
  the name rung **over-powered** (name similarity is the bulk of `attribute_score`, and exact-normalized
  name auto-merges at 1.0 in bootstrap).
- **A live principle collision to resolve, not inherit:** `config/resolution.yaml:170-179` justifies
  `coref_authoritative_evidence: []` partly to *protect a demo beat* (the d10 "HT-233 (H-200)" orphan alias
  is meant to be earned by an analyst). Working-principles #1 forbids curbing a target-correct capability to
  preserve demo data — so the category policy must be decided on general principle and the beat re-carried
  by the data pass if it is lost.
