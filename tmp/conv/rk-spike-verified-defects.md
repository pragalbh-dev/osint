# RK-SPIKE — verified defect register & the target-correct requirements that follow

**What this is.** Defects in the *current substrate* that the spike verified against code, each paired with
the **target-correct behaviour** the replumb must produce and the **gate clause** that makes the requirement
testable. These are requirements, **not** disclosures: nothing here is "an honest limitation to state in the
design note." Target-first (working-principles #1) — the design is fixed, the data/graph/extraction follow.

**Provenance discipline (working-principles #7).** Items marked **[V]** were verified by the orchestrator
reading the cited code directly. Items marked **[V2]** were reported independently by two hands (recon +
analyst) but not re-read by the orchestrator. Items marked **[R]** are single-source reports still to verify.

---

## D1 — [V] An identity over-merge manufactures a positively-asserted relocation, and removes the analyst

**The most severe finding of the spike.** This is not an order-of-battle hygiene issue; it is a structural
path from an identity error to a **fabricated movement assessment with the human explicitly taken out of the
loop** — the one non-negotiable, breached without any component "lying".

The chain, every link verified:

1. **Co-location makes a formation merge the path of least resistance.** Two independent reports of the same
   design, at the same site, same operator, no designations: `attribute_score` is high (near-identical names —
   `scoring.py:425-437` takes `max(name_sim, agreeing/present)`), `relational` is high (shared design + site
   neighbourhood), and `temporal_score` is **binary 1.0** on any non-relocation pair (`scoring.py:545-547`).
   Every signal points at merge.
2. **Nothing currently resists it.** The perishable cap is short-circuited by name-sameness:
   `confirm_is_durable` returns True immediately when `has_durable_trigger(a, b)` holds, and its own docstring
   says so — *"A name-driven or durable-attribute confirm still autos here… A durable bootstrap trigger
   (name/coref/shared-id) is durable support on its own footing too, so it short-circuits"*
   (`resolve/cluster.py:418-428`). See also D3.
3. **`based-at` is FUNCTIONAL and keyed on the unit alone** — `config/ontology.yaml:146`,
   `instance_key: [from]`, with the comment *"FUNCTIONAL — key the supersede instance on the unit alone so a
   relocation's before/after co-locate (D-P4.4)"*. So the moment two batteries fuse into one unit, their two
   distinct site edges become **one unit's before/after**.
4. **The supersede path then promotes it, retires the older site, drops the analyst, and DRAWS the edge.**
   `credibility/supersession.py:165-209` (`promote_supersessions`, called at `view/pipeline.py:795`): when the
   newer edge clears the credibility floor it sets `older.superseded_by` / `newer.supersedes`, marks both
   `GATE_PROMOTED`, **pops the pair out of the analyst's queue** — the code comment is explicit: *"The pair is
   adjudicated by the machine — it is no longer a question for the analyst"* — and then
   `if newer.target != older.target: outcome.drawn_edges.append(_drawn_edge(older, newer))`, i.e. **because the
   two sites differ, it draws a relocation edge.**

**So:** one identity error ⇒ a drawn, positively-asserted relocation that the analyst is never asked about.
An adversary does not even need to plant a lie — publishing two real, similarly-described co-located units is
enough.

**The ontology already admits the hole and rests it on the corpus** — `config/ontology.yaml:40-44`:
*"Subject-only keying is correct while the corpus has no such simultaneous pair (the relocation beat is one
unit, one site_type: Rawalpindi→Rahwali)."* Working-principles #1 forbids a design resting on what the
current corpus happens to contain. **The sub-scope limitation must be closed in the design, not deferred to a
Tier-4 refinement.**

**Target-correct requirements:**
- **R1.1** The co-location cap (D-13.14) is **anti-fabrication machinery**, not OOB hygiene — it is the thing
  standing between an identity error and a fabricated movement claim. Priority accordingly.
- **R1.2** A formation merge that rests on co-location must never fuse, therefore never create a shared
  supersede instance key.
- **R1.3** `based-at`'s supersede instance key must be tagged by **site_type** (the deferred Tier-4
  refinement), so a unit legitimately at a garrison *and* a forward site is two valid instances rather than a
  relocation.
- **R1.4** A supersede that would **draw** a relocation across differing targets must not be machine-
  adjudicated out of the analyst's queue when the underlying identity is itself sub-confirmed. Machine
  promotion is only legitimate over an identity the system actually earned.
- **Gate clause (G16, amended):** G16 must assert **the absence of a derived `supersedes` / drawn relocation
  edge**, not merely the absence of a confirmed merge. As written it goes green while the harm it exists to
  prevent is realized one stage downstream.

---

## D2 — [V] A second candidate formation is silently discarded: an OOB undercount with no merge at all

`ingest/basing.py:301` — `for unit_id, backing, ftype in formations[:max_units]` with
`max_units_per_site: 1` (`config/credibility.yaml:172`, *"cap the attribution fan-out: the best-evidenced
formation only, not every candidate"*). **Every other rejection path in that function appends a
`SkipRecord`** — `occupancy-edge-has-no-site-endpoint` (`:280`), `site-not-locatable` (`:285`),
`observation-states-vacancy` / `no-backing-observation-claim` (`:292`), `already-derived` (`:295`),
`no-formation-reference` (`:299`) — **and the truncation appends nothing.**

So when two candidate formations are associated with the same observed equipment at a site, the second
vanishes: no skip record, no coverage item, no gap. This undercounts the adversary's order of battle **with
no merge involved**, which means **neither G15 nor G16 can see it**.

**Target-correct requirement (R2.1):** two candidate formations ⇒ **two attributions, or one attribution plus
an explicitly named gap. Never a silent pick.** This is a requirement on **S2's replacement** (the pass itself
is deleted and replaced by a rebuild-derived edge — plan §7 RK-LAYER item 4), so it must be carried forward
rather than patched into a doomed file.
**Gate clause (G15, amended):** G15 as written passes *vacuously* — `find_candidates` already skips when no
`formation_edge_types` link to a `unit` exists (`basing.py:296-300`), so "an `observed-at` never becomes a
`based-at` without organizational evidence" **is current behaviour**. Keep that as a regression guard, and add
the clause that actually bites: *a truncated/ambiguous formation attribution must produce a named gap.*

---

## D3 — [V] Both identity caps are permeable to name-sameness, and one does not bind the path that fuses nodes

**(a) `name_alone_caps_at_possible` does not cover the merge path.** The dial is **on**
(`config/resolution.yaml:154`), but `_name_alone` is consulted **only** in the post-fixpoint collection loop,
where it decides `candidates` vs `possible` (`resolve/cluster.py:558-568`). The **Phase-2 fixpoint that
actually unions nodes never consults it** (`cluster.py:466-496` — it checks `vetoed`,
`violates_veto_transitively`, `raise_walls`, then bands and merges). So the dial demotes pairs that were only
ever going to be *queued*, and cannot stop a fusion.

**Reachability, computed exactly** (weights `attribute 0.40 / relational 0.40 / temporal 0.05`, and
`_deterministic_total` excludes `source_asserted`): `_name_alone` requires `RELATIONAL == 0`, so the maximum
deterministic total is `0.40·attr + 0.05`.
- global `auto_merge: 0.85` ⇒ needs `attr ≥ 2.0` ⇒ **unreachable**;
- `auto_merge_by_type: {manufacturer: 0.37, trading_org: 0.37}` (`config/resolution.yaml:64-66`) ⇒ needs
  `attr ≥ 0.80` ⇒ **reachable**, and a token-sorted Jaro-Winkler of 0.80 is easily met by similar names.

So the hole is real and **scoped to the two types whose floor was lowered** — a guard that did not follow a
lowered floor. Note **G6 cannot catch this**: the numbers *are* in config; the defect is that a policy dial
does not cover a code path.

**(b) The perishable cap is laundered by name-sameness.** Per D1 step 2: `has_durable_trigger` counts
exact-normalized-name + namespace as durable identity support, short-circuiting `confirm_is_durable`
(`cluster.py:418-428`). This directly undercuts D-13.9 guard (a) *and* the co-location cap — a co-located,
same-named pair bypasses the very cap meant to hold it.

**Target-correct requirements:**
- **R3.1** D-13.10's invariant — *name is a contributor, never a verdict, at every layer* — must bind **the
  fusion path**, not only the queue band.
- **R3.2** A name-derived trigger must not count as durable support for the purposes of the perishable or
  co-location caps. Name may buy a *comparison*; it may never buy the thing a cap exists to withhold.
- **R3.3** These require **separating `name` from `attrs`** as distinct components of the stored
  `merge_breakdown` (`cluster.py:625`). They are fused inside `attribute_score` today, which is why
  D-13.10's design-layer story — *"a name match reaches at most possible; one more trivially-available signal
  clears it"* — **cannot function at all** in the current shape.
- **Gate clause (new, or a G16 clause):** assert that a name-only pair does not **fuse**, at *every*
  configured floor including per-type overrides.

---

## D4 — [V2] Namespace is not a wall in the fuzzy fixpoint — a live cross-operator over-merge path

`namespace_compatible` gates only bootstrap-exact-name, `_name_containment` (`cluster.py:261`),
`_identity_pairs` (`resolve/__init__.py:596`) and `_coref_pairs` (`:654`) — **never the Phase-2 loop**
(`cluster.py:466-496`) — and relational blocking emits pairs with **no namespace key**
(`cluster.py:182-187`). So a PLA-side and a PAF-side entity can be scored and auto-merged.

For an **operator-scoped** order-of-battle map this is the single most dangerous over-merge class, and it
directly contradicts spine/13 §3's "never across operators within the instance layer". **No gate names it.**

**Target-correct requirement (R4.1):** RK-COREF owns closing it. Note this also means the ladder's
"designation" rung cannot rely on namespace compatibility as stated (see D5) until it is closed.

---

## D5 — [V] The discriminator ladder's top rung is undeclared, and the operator rung cannot fire

- **`unit.designator` does not appear in `attribute_roles`** (`config/resolution.yaml:326-350`) ⇒ **unlisted
  ⇒ neutral ⇒ zero identity effect**. The top rung of the whole discriminator ladder is not merely unwired, it
  is undeclared.
- **No value normalization exists** — conflict detection is bare `==` on raw attrs (`scoring.py:99-101`);
  `normalize`/`transliterate`/`AliasIndex` apply **only to `Entity.name`**. The config states the consequence
  itself (`resolution.yaml:317-324`): sources state `service_branch` as 'Air Force' / 'PAF' / 'Pakistan Air
  Force', so an exact-match critical wall "SHATTERS legitimate merges" — which is precisely why
  `unit.service_branch` and `trading_org.origin_country` sit at `supporting` instead of `critical`.
- **`supporting` is inert anyway** — `attribute_scoring.conflict_penalty` is unconfigured (grep count 0), so
  the soft-penalty branch (`scoring.py:444-456`) never runs. The declarations are documentation.
- **Per-attribute `perishable` is declared but unconsumed** — `resolution.yaml:309-311` says so outright
  (*"OPTIONAL, SCHEMA ONLY in this stage… Read but NOT yet consumed"*).

**Target-correct requirements:**
- **R5.1** A shared designation is a **non-perishable discriminator, not a unique identifier.** It satisfies
  D-13.9's perishable cap but still requires namespace compatibility **and** independent corroboration; **one
  shared designation string may never confirm a formation merge.** Designations are reused across armies and
  across time. The codebase already embodies exactly this asymmetry for bills of lading — differing
  identifiers veto, shared ones do not confirm (`identity.identifier_patterns`, `_identifier_veto`) — and that
  asymmetry should be preserved, not "fixed".
- **R5.2** Value normalization is a **prerequisite** to promoting any operator/branch attribute to `critical`,
  and must apply before conflict detection **and** before namespace derivation (`resolve/entities.py:114-120`
  reads raw attrs — normalizing only at conflict time would leave namespaces split).
- **R5.3** S3 consumes the already-declared per-attribute `perishable` flag; it is the D-13.9(a) guard.

---

## D6 — [V] D-13.9's source-independence guard is not implemented in the merge path

**Verified.** Source-independence machinery *does* exist in this codebase — the claim-level corroboration
ledger (`credibility/status.py`, `schemas/claim.py`, `view/pipeline.py`, and the spine/04 independence-group
design). **It appears nowhere in `resolve/`.** A grep for `independen` across `resolve/**` returns only
*iteration-order* independence (`cluster.py:282`, `scoring.py:312`, `normalize.py:47`, `entities.py:88`) and
"independent identity **signal**" (`scoring.py:648-650`).

**The precision that matters:** `identity_ledger`'s "one entry per independent identity signal" is about
**signal classes** (attribute / relational / temporal / source_asserted), **not** about source independence.
It is the thing most likely to be mistaken for the guard, and it is a different concept. So two derivative
reprints of one almanac contribute two `source_ids`, can raise attribute/relational agreement, and **nothing
in the merge path notices they are not independent.**

Plan §7 RK-COREF item 5 reads as though this were configuration ("corroboration inherits source-independence").
**It is new code.** Scope it in S3 or disclose it — do not let it be assumed. Two reprints of one almanac must
not confirm an identity merge (D-13.9(b)).

---

## D7 — [V2] `operated-by` does not exist as a predicate, so G18 would test half of itself

No `operated-by` edge is declared in `config/ontology.yaml:146-159` (independently found by both the recon
hand and the failure-first analyst). G18 (relationship-conflict wall) names `based-at` **and** `operated-by`.
Either S3 adds the predicate — in which case the stage scope must say so — or the gate silently tests half of
itself and is marked green.

**Also: G18 does not say *which kind* of wall**, and the two available kinds are not equivalent — membership
in `veto` is hard **and transitive** and re-applied in `finalise` (`cluster.py:363-370`, `:638-648`), whereas
consultation inside `vetoed()` only is hard, pairwise and **invisible** to `finalise`, the D9 bridge alarm and
`res.distinct_from` (how the geo veto is wired, `cluster.py:357-361`). Build the relationship wall like the
geo veto and it will be non-transitive *and unreported* while G18 passes. **The gate must name the channel and
assert an analyst-visible reason.**

---

## D8 — [V] "Capped at probable" is not expressible as written; say "not fused, queued and reported"

There are **three** bands (`cluster.py:96-101`), **no `reject` verdict**, and the
confirmed/probable/possible names are a *derived read of set membership*
(`schemas/stage_io.py:112-118`: `same_as`→confirmed, `candidates`→probable, `possible`→possible) where **only
`same_as` fuses**. spine/13 §6/§7/§13 speak of "capped at *probable*" as though a probable merge existed.

The two cap shapes that do exist, and are proven:
- **cap at probable** = withhold the merge, force into `candidates` with a reason — the `perishable_capped`
  shape (`cluster.py:443, 478-496, 574-576`);
- **cap at possible** = withhold from `candidates`, land in `possible` — the `name_alone` shape
  (`cluster.py:558-568`).

**Target-correct requirement (R8.1):** rewrite the design language as *"not fused; queued and reported"* —
stronger and testable. **The co-location cap (G16) is a third instance of the `perishable_capped` shape**, not
new machinery, and its analyst-facing reason string belongs beside `_perishable_confirm_reason`
(prose-only, no thresholds — G6-clean).

---

## D9 — [V] The referent atom must be evidence about a grouping, never the address of the instance

spine/13 §4 promises coreference stays "a challengeable proposal"; D-13.11 says atoms never split or merge.
Read together with the referent atom as the *address* of the provisional instance, an over-binding coref
cluster becomes **permanent** — which is disqualifying.

The resolution is already the shape the code emits: `ingest/coref.py:385-392` emits a `ClaimRecord` on a
dedicated `coref-same-as` predicate and mints a **claim** id, **never an entity id**. So:
- **rebuild groups claim atoms**; the referent atom is a strong (or authoritative) grouping *signal* the
  grouping step consults — exactly as a coref claim is consulted today;
- a **loose** bind is an injected Tier-1 candidate pair (`_candidate_pairs` already accepts injected pairs,
  `cluster.py:203`; `_coref_pairs` already routes non-authoritative pairs to `raise_only`,
  `resolve/__init__.py:657-660`) — undone by rejecting the candidate;
- a **tight** bind that proves wrong is an analyst split that **re-partitions the claim atoms** — precisely
  D-13.11's own mechanic ("a split is just atoms landing in two buckets"). No atom splits; the derived node id
  changes and the redirect map carries display continuity.

**Target-correct requirement (R9.1):** write this into **D-13.7 / D-13.11 and plan §7 RK-COREF item 1**, all
of which can currently be read either way — and the unsafe reading is disqualifying. The forbidden shape is
minting one referent atom per *proposal* and using it as the instance address.

---

## D10 — [V] A coreference bind is gated *less* than the assertion it most resembles

Neither `ingest/coref.py` nor `_coref_pairs` (`resolve/__init__.py:614-661`) reads a **source grade**. Yet an
opted-in coref pair **bootstraps a merge at hardcoded confidence 1.0** (`cluster.py:465`; `model_conf=1.0` at
`coref.py:396`), whereas a source-stated `same-as` — the closest sibling — is grade-floored *and* structurally
**raise-only** (`_deterministic_total` excludes it, `cluster.py:78`).

That inversion is the sharpest gap in micro-decision (a): the weaker-evidenced channel acts harder. spine/13
§5's doctrine is explicit that **stated ≠ trusted** — a grade-E source stating something still runs through
source grade.

**Target-correct requirement (R10.1):** an authoritative coref bind must clear a source-grade floor set
**strictly above** the stated-`same-as` floor, mirroring `_critical_attribute_walls`' discipline
(credibility-gated at `critical_veto_min_grade: C`, and *raising* rather than acting when below floor —
`resolve/__init__.py:490-529, 499-501`). Note `identity_raise_min_weight: 0.0`
(`config/resolution.yaml:140`) is dialled off today — **do not inherit that value**.

---

## Cross-cutting: what these defects do to the gate set

| Gate | As written | Amendment required |
|---|---|---|
| **G15** presence-not-fused | **passes vacuously** — the behaviour already holds (`basing.py:296-300`) | keep as regression guard; **add** the D2 clause: an ambiguous/truncated formation attribution ⇒ a named gap, never a silent pick |
| **G16** co-location-cap | asserts no confirmed formation merge | **add** the D1 clause: **no derived `supersedes` / drawn relocation edge**; **add** the D3 clause: a name-only pair does not fuse at *any* floor incl. per-type overrides |
| **G18** relationship-conflict-wall | names `operated-by`, which **does not exist**; does not name the wall *channel* | S3 either adds the predicate (scope it) or the gate tests half of itself; the gate must **name the channel** and assert an analyst-visible reason |
| **G17** atom-immutability | fine | ensure the fixture is non-vacuous (plan already flags this) |
| **new** | — | a namespace clause for the Phase-2 fixpoint (D4) — currently **no gate names the most dangerous over-merge class** |

---

## D11 — [DEFECT, by the system's own rule] Independence is keyed on publisher class, not evidential lineage

Raised by the independent data hand while hand-labelling the gold slice. **Recorded here, not resolved** — it
concerns the frozen corpus and the graded oracle, so it belongs to DATA-C / EVAL, and the spike must not
re-adjudicate it.

**The concern.** The Rahwali occupancy confirm rests on `d18_rahwali_pass1` + `d19_rahwali_confirm`, which the
config frames as a *discipline-independent* pair — `config/credibility.yaml:104-105`: *"2025 overhead pass —
first Rahwali occupancy indicator (single-pass → probable)"* / *"2025 discipline-independent confirmation →
confirmed + supersedes Rawalpindi"*. Mechanically they satisfy independence by **construction**: different
`source_id`, different `source_type` (`satellite` vs `think-tank`), both grade B (`config/sources.yaml:41-42`),
and `min_independent_groups: 2` (`config/credibility.yaml:101`).

**But the data hand reports (spans verified byte-for-byte against the corpus) that d19 explicitly reads d18's
report** — *"confirms the … cluster first detected on the single-pass collection reported earlier"* — and that
d19's own claimed second signal is an unnamed vendor via an unnamed intermediary that released no
geolocation, with the desk disowning its own radar identification.

**Why it matters.** If d19 is a second *analysis* of the same collection rather than a second *look at the
phenomenon*, then the independence is nominal (different publisher class) rather than real, and "confirmed"
over-claims. That is the exact failure D-13.9(b) names — *two reprints of one almanac must not confirm* — and
the project's own too-clean / independence machinery exists to catch it. **The system asserting `confirmed`
where the honest verdict is `probable` is the soft edge of the one disqualifying failure**, so it is worth
resolving on its merits regardless of any demo consequence.

**What is NOT yet established** (and why this is `[DATA]`, not `[V]`): whether d19's phrasing means *derivative
of d18* or *independently collected and concurring*. That is an interpretation of the source text, not a code
fact, and it is the crux. **Action: DATA-C / EVAL adjudicate the source text.** If derivative, either the
independence grouping must treat cite-of-a-prior-report as same-group, or the corpus must carry a genuinely
independent second look.

**RECLASSIFIED 2026-07-25 — this is not an open question, and I was wrong to frame it as one.** The system
already states the rule *and* the principle:
- **The rule:** `min_independent_groups: 2` — *"≥2 independent looks required to reach `confirmed`"*
  (`config/credibility.yaml:101`). One source cannot confirm. There is nothing to adjudicate about that.
- **The principle already exists in the config, for inferences:** *"an inference shares an independence group
  with its premises so it can never self-corroborate to confirmed"* (`config/credibility.yaml:160`). That **is**
  the evidential-lineage rule — derived-from-X sits in X's group. It is simply not applied to a **source that
  cites a prior report**, which is the same relationship one level up.

So **C8 extends an existing doctrine rather than inventing one**, and that is the stronger framing: the
independence axis is real and correct in concept; what is wrong is the *key* it groups on. Grouping by
`source_id`/`source_type` makes two documents "independent" because they have different publishers — which is
exactly how a report that reads another report counts as a second look. Under the config's own
premise-sharing logic they are **one** group, so the flagship confirm is **unsupported by the system's own
rule**, not "possibly" unsupported. The remaining work is mechanical (re-key grouping on lineage) plus one
data question for DATA/EVAL: whether the corpus should carry a genuinely independent second look, or the
flagship should honestly read `probable`.

**Two things it reinforces regardless of the outcome:**
- **D6** — the same nominal-vs-real independence problem applies to *identity merges*, where (unlike claim
  corroboration) there is no independence machinery at all.
- The independence check should key on **evidential lineage** (does this source cite / derive from that one),
  not only on publisher class. Discipline-diversity is a *proxy* for independence, and this is the case that
  shows the proxy failing.

## D12 — [DATA, ontology] The schema makes the sourced relation inexpressible and the unsourced one easy

Also from the data hand: the customs document's actual spine — *event ↔ consignee ↔ shipper* — **cannot be
represented**, because no edge type connects `contract_import_event` to `trading_org`; meanwhile the schema
*does* offer `imported-by → unit`, which that document never states.

**A schema that makes the sourced thing inexpressible while making the unsourced thing easy is an
anti-fabrication hazard** — it pressures extraction toward asserting the thing no source said. This is a
genuine ontology gap and a design input (unlike D11, it needs no corpus adjudication).
**Owner: RK-LAYER (S2), which owns `config/ontology.yaml`.** Add the event↔trading_org edge; re-examine
whether `imported-by → unit` should require a stated unit.
