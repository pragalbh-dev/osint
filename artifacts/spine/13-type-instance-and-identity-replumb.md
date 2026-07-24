# Type/instance model and the identity re-key — the substrate D1–D3 always needed

**Status: PROPOSED design (2026-07-24), refined per the 2026-07-24 design-review alignment. Not implemented;
not started.** This realizes decisions **D1–D3**
of `10-resolution-real-world-redesign.md` — the three the shipped redesign (D4–D11) built *on top of* but
never actually laid down. It spans four surfaces — the ontology, the extractor contract, resolution, and
materiality — deliberately, because the type/instance distinction, earned identity, layered chokepoints, and
fragmentation control are **one piece of work, not four**. Roadmap-scale, not a stage: the whole graph
currently *addresses* entities by name, so re-keying identity off names is foundational. This version folds
in the full co-design session (the five forks, the fragmentation/two-tier architecture, and the extraction
contract).

---

## 1. Why — the substrate contradicts the headline

The redesign's headline is *"identity is evidence, not string-matching."* **At the substrate it isn't.**

An entity's identity is its `type + name`, and name-as-identity is enforced in **two stacked lanes**. First,
two mentions that share an *exact* (byte-identical) name and type collapse into one node at profile-build
time — a dictionary-key collision (`entities[eid]`, `eid = ent:<type>:<name>`) — **upstream of the resolver
entirely.** There is never a candidate *pair*, so the graded possible/probable/confirmed model, the
credibility-gated critical wall, and the namespace/country gate — all of which adjudicate *pairs* — never get
a vote. Second, mentions that are *normalized*-equal but differently spelled *do* form candidate pairs, but
the resolver's bootstrap then auto-merges them at identity confidence **1.0** on the normalized name alone — a
name *verdict* rule that over-rides the same judgment layer from the other side. A conflicting discriminator
(a different operator on a same-named unit) is absorbed first-value-wins; the loser is parked in attribute
history and is not the value the graph uses. So the evidence-judgment layer is real for the **ambiguous
middle** (fuzzy candidates) and structurally **bypassed for the strong name signal** — short-circuited
underneath it in the first lane, over-ridden by a name-verdict in the second. **The re-key must remove *both*
lanes, not just the dict key.**

D1 (a name is a clue, not a verdict), D2 (certainty only for unique identifiers), D3 (grade names by rarity)
were never built — not by oversight of judgment, but because they require re-keying identity off names, and
the entire graph addresses entities by name (edge subjects/objects are names; references are names; the alias
index is name-keyed). That is foundational rework, not a stage-in-a-PR, and it was descoped in favour of
building the judgment layer where it *could* be built. This doc is the substrate that layer always needed.

## 2. The deeper reason it matters — a name can't tell a type from its instances

"HQ-9" names two different kinds of thing at once:

- a **design** (the model/family: HQ-9, the HQ-9/P export version, HQ-9BE, HQ-9A) — its manufacturer,
  components, engagement radar and chokepoints are properties of the *design*, shared by everyone who fields
  it; geography-agnostic; legitimately **singular**.
- an **instance** (a holding/deployment: "Pakistan's HQ-9/P", "the battery at Rahwali") — an *individual*
  with an operator, a location, a readiness, a time. **Many** of them; not each other.

Keying identity on the name forces these into one node. The information that individuates instances —
**operator, geography, unit designation, time** — is exactly what `type:name` discards, and it discards it
*before* the machinery designed to use it (the namespace gate, the critical wall) ever runs. On the current
corpus this is masked only because the demo's names happen to differ by operator (HQ-9 vs HQ-9/P). Rely on
that and one identically-named source silently fuses two countries' holdings — the exact failure the redesign
promised to prevent.

**The reframe that shrinks the problem:** we are *not* trying to stop designs from collapsing. There is one
HQ-9 design, and a supply-chain/chokepoint query *wants* it to be one node. China's, Pakistan's and a
hypothetical Dubai's HQ-9 should share the *design* node — that sharing is the point of the use case. The bug
is narrower and splits three ways: (a) two mentions of the **design** collapsing → correct, keep it; (b) two
**instances** collapsing on name → the bug; (c) an **instance mis-typed as the design**, so it lands on the
shared node and drags its operator in → a *kind/routing* error. So the whole job reduces to two things:
**individuate the instance layer**, and **route each fact to the correct layer.**

## 3. The two-layer model

Identity, and everything downstream of it, is organised in two layers with a small hierarchy between them:

**base design → variant → operator's holding → unit/battery → equipment-seen-at-a-site**

- **Type / design layer** — variant, component, radar, manufacturer. Abstract, geography-agnostic,
  legitimately shared. One HQ-9 design node, whoever fields it; HQ-9/P a `variant-of` it.
- **Instance / individual layer** — concrete, operator-bound, located, timed individuals. This layer has
  **two citizens, defined by the evidence that creates them** (not two arbitrary grains) — a *presence* and a
  *formation*, developed in §3a below. Many, one per operator (and below).
- **Other kinds** — places, sources, events — are their own kinds, not "instances of a design."
- **Binding relations** — `instance-of` / `fields` / `operated-by` / `based-at` link the layers but are
  **never merged across**. China's holding and Pakistan's holding both point at the shared (or lineage-
  linked) design; they are not the same holding.

**Rule:** collapse only ever happens *within* a layer, when the discriminators genuinely match; never
*across* layers, and never across operators within the instance layer.

### 3a. The instance layer has two citizens — presence (workhorse) and formation (earned)

The individual layer is not one kind of thing; it splits by *what evidence brought it into being*:

- **Presence** — the workhorse. *"Operator's <design> observed at <site> during <time-window>."* Born from
  **observation** evidence: imagery, a NOTAM/NAVAREA, a geolocated photo, a news sighting. Concrete, sourced,
  individuated by operator + site + time — and almost always what open sources actually give you. Its `count`
  (how many launchers/TELs/rounds) is an **attribute of the presence with its own sourced evidence** (an
  imagery TEL count, a stated OOB figure), default `unknown`/≥1 — **never derived from how many reports
  merged** (k reports ≠ k launchers).
- **Formation** — the rare, earned citizen. The *organizational individual*: a designation-bearing
  battalion/battery with a command chain that **persists through moves**. Minted **only when organizational
  evidence exists** — a stated designation ("8th AD Bn"), an order-of-battle reference, an order or logistics
  document. We do **not** force a formation node: reifying an organizational individual we cannot source would
  violate the non-negotiable. A formation *threads* presences across time and space.

So "is a unit just a count?" — no: count is an *attribute of a presence*; a formation is the organizational
thread. Equipment counts come from imagery (real, per-presence); formation counts come from
OOB/white-paper/logistics sources (sparse, lower-confidence) — both sourced claims defaulting to `unknown`,
never fabricated.

**This is not new architecture — it names and elevates a distinction the ontology already draws.** Two edge
types are already separated deliberately (`config/ontology.yaml`):
- **`observed-at`** (`[variant, component] → basing_site`) **is the presence citizen** — "equipment was seen
  at site Y." The ontology comment already says it: a satellite frame *"can honestly state that equipment is
  at a place, not that a named formation is based there,"* and it is non-functional (equipment can be at many
  sites at once).
- **`based-at`** (`unit → basing_site`, functional, keyed on the unit) **is the formation citizen** — a named
  formation based at a site; the ontology comment already flags that *"attributing the occupancy to a unit is
  a derived inference … that keeps its own, lower confidence — never fused."*

The reframe's job is therefore to *name and elevate* an implicit code distinction and to make formation
minting **explicitly evidence-gated** — derive `based-at` from `observed-at` only where organizational
evidence exists — rather than a quiet ingest-side heuristic.

**The layer-routing test, in one question:** *does the fact change if a different operator fields the same
design?* No → it is a **design** fact (shared). Yes → it is an **instance** fact (operator-scoped: a presence,
or, when earned, a formation). This is the operational form of §5's per-fact layer routing.

## 4. The seam — kind and within-document coreference are *stated*; cross-document identity is *earned*

The design falls on a clean seam between what a source *states* and what must be *earned* across sources:

- **Stated (the extractor's job):** the *kind* of each mention (already tagged: `variant` vs `fire_unit`),
  the discriminating context the source gives (operator, geography, unit designation, time), and
  **within-document coreference** — that "the battery… it… the unit…" in one document are one referent.
- **Earned (the resolver's job):** *cross-document* identity — that document A's unit is document B's unit.

Why within-document coreference is *reading*, not the forbidden resolution: within one source there is
nothing to corroborate against; the source is the sole authority on what its own "it" refers to. Recording it
is recording what the source states, in the same class as tagging kind. What must stay earned is *combining
independent sources* — the judgment that has to be corroborated, reversible and config-dependent. (Within-doc
coref is still a *challengeable proposal*: a coref cluster carrying a conflicting critical discriminator is
the signal it over-bound, and the §5 split fires on it. Coref is a strong prior; the walls and cross-doc
resolution are backstops.)

**A consequence worth stating:** because §5 routes facts by their declared layer rather than by the
extractor's kind call, the extractor does **not** have to get kind right. It can lump everything under one
entity type; the build self-corrects. The extractor's entity-type is a hint; the per-fact layer tag is the
authority. This *relaxes* the extractor requirement **for *kind* only** — §10/§13 (F6) note the load-bearing
extraction burden **moves** onto coreference + discriminator capture rather than lifting away.

## 5. The unified build pipeline — split, materialize, bind

Forks 1 and 2 collapse into a single build-time mechanism. In order:

1. **The ontology tags every fact with a layer (static).** Each node-type gets a layer (`variant` →
   design; `fire_unit` → instance). Each *attribute-type* gets a layer too — and this is the non-obvious
   part: per-attribute layers are needed because the **split trigger is a mismatch**. An `operator`
   attribute (instance-layer) sitting on a `variant`-typed (design) node is exactly the signal that the
   extractor lumped two things together. If attributes only inherited their host node's layer, the
   misplacement would be invisible. Edge-types already declare their endpoint node-types
   (`based-at`: `fire_unit → basing_site`), so endpoint *layers* fall out of the endpoint *types* — no new
   declaration. **Layer is a property of the type, uniform**; if an attribute is genuinely dual (a design's
   nominal range vs a deployment's effective range), it is *split into two attribute types* rather than made
   contextual.

2. **The build routes each fact to its layer and splits straddlers.** Design-level facts attach to the
   (shared) design node; instance-level facts attach to an instance node. A single extracted mention carrying
   both is **split into two linked nodes** (design + instance), even if the extractor emitted it as one.

3. **An instance-layer edge *implies* — and materializes — an instance node, at the right citizen (§3a).**
   Worked example: a source states **"HQ-9/P at Rahwali,"** which the extractor emits as an **`observed-at`**
   sighting (`variant → basing_site` — the honest thing a frame supports: equipment seen at a place, not a
   named formation based there). It needs an *instance* endpoint but the mention named only the *design*, so
   the build does **not** point it at the shared design node — it materializes a provisional **presence** P:
   **P is a provisional presence at Rahwali · P `instance-of`/`fields` HQ-9/P(design) · P to be resolved.**
   The design name becomes the link to the shared design node; the sighting binds to P. A **formation**
   (unit U) is materialized **only when organizational evidence earns it** — an `inducted-into` link tying
   the sighted equipment to a *named* unit — at which point a derived, premise-cited, lower-confidence
   `based-at` binds U to the site. (This is exactly the `observed-at` + `inducted-into` → `based-at`
   derivation the code already performs in `ingest/basing.py`; the replumb makes it a first-class,
   rebuild-time derived-layer binding per D-13.6, not an offline pre-freeze.) A bare sighting never forces a
   formation (D-13.13/D-13.14).

   **A formation has two provenance paths, and the stated one is stronger — derivation is the fallback, not
   the only route.** When a source *names the formation at a site directly* (an ORBAT reference, a
   military-balance yearbook, an official statement — "the 8th AD Battalion at Nur Khan"), that is a
   **stated** `based-at` (`kind=observation`): the source is authority on its own assertion (§4), the
   extractor emits it directly (`based-at` is `extractor: true`, re-laned to `observed-at` only if the
   subject resolves to *equipment* rather than a unit), it binds the formation with **normal source
   credibility**, and it can reach *confirmed* with independent corroboration. The `observed-at` +
   `inducted-into` → `based-at` *derivation* above is the **fallback** for the usual open-source case where
   no source states formation-at-site — a premise-cited, capped, un-promotable `kind=inference`. Both feed
   the formation citizen (both are the "organizational evidence" of D-13.13); the derived path is weaker by
   construction. Crucially **stated ≠ trusted**: a stated basing runs through source grade and the deception
   gates like any claim — a grade-E spoof naming a unit at a site lands at *possible* and is walled by the
   supersession floor, never waved through for being "stated." (The running code already implements both
   paths and this credibility treatment; the three "no source states basing" comments in
   `basing.py`/`ontology.yaml`/`credibility.yaml` are a stale corpus assumption the code has outgrown, and
   should be corrected to "formation-at-site is *usually* unstated, so derivation is a fallback.")

   Contrast: **"Pakistan equips HQ-9/P"** is a `operator → design` *holding*
   edge — neither endpoint instance-typed — so it mints **no** presence and **no** unit; it stays a holding
   edge to the shared design. Country-level holdings, site presences, and named formations stay cleanly
   separate, driven entirely by the ontology tags.

4. **Endpoint layer is static; endpoint identity is resolved at rebuild, and must be.** The endpoint's
   *layer* is free — a declared property of the edge type, never computed. The endpoint's specific *identity*
   (which unit) is resolved during rebuild, materialized into the view, and read cheaply by every query — it
   is **not** re-resolved per query, and it is **not** baked into the immutable claim. The reason is the
   bi-level invariant: which instance an endpoint binds to is a *resolution decision* — reversible,
   config-dependent, changeable by a new merge or a reweighting. Freezing it into the append-only claim would
   put a derived, mutable decision into the immutable evidence layer and break the architecture. Binding is
   earned, in the derived layer, every rebuild. (At real scale this is exactly what the incremental-rebuild /
   graph-store path is for; the *semantics* stay "resolved in the derived layer.")

## 6. Two-tier resolution and fragmentation control

Minting one provisional instance per mention or per edge would fragment the graph badly — especially with
within-document coreference off. The fix is to make the **unit of minting the document-local coreference
cluster**, which splits resolution into two tiers that are different problems solved in different places:

- **Tier 0 — within-document coreference, at ingest (source-grounded).** All mentions of one referent inside
  a single document collapse into **one rich provisional instance** before cross-document resolution runs.
  This is where "the HQ-9/P battery at Rahwali… it… the unit… its HT-233… operated by the PAF" becomes a
  single provisional unit carrying every fact the document gave. The `ingest-coref` work is largely **built
  but currently off**; this design promotes it to a required tier.
- **Tier 1 — cross-document resolution, earned.** The resolver clusters *per-document instances* — each
  already information-rich — rather than bare mentions, so cross-document identity has real signal to work
  with (§7). **Tier 1 compares *all* provisional-instance pairs, including same-document ones:** if Tier 0
  under-binds (misses that two same-doc mentions co-refer), those intra-doc fragments can only ever rejoin if
  Tier 1 is allowed to compare them — otherwise the grain choice manufactures a permanent fragmentation class.
  A same-doc pair carries a prior *against* merging **only** when the source syntactically contrasts them (an
  enumeration, "another battery", distinct designations) — stated anti-identity evidence; otherwise the pair
  is neutral and judged on its merits.

**Three levers keep the graph from going sparse:**

1. **Within-doc coref (Tier 0)** kills intra-document fragmentation and makes each provisional instance rich
   enough to resolve across documents. Biggest lever.
2. **Clean anchor layers as relational scaffolding.** A formation is barely identifiable by its own name, but
   very identifiable by what it hangs off — the HQ-9/P design and the Rahwali site, both in layers that
   resolve *cleanly* (designs collapse readily — never on name alone, §7; places have coordinates and a
   gazetteer). So the fuzzy instance layer does not resolve in isolation; it resolves *by its connections to
   well-resolved anchors*. Two co-located reports of HQ-9/P at Rahwali by the same operator collapse into one
   **presence** — safe, because a presence asserts only presence, which co-location evidence genuinely
   supports. What they must **not** do is collapse into one **formation** on that shared neighbourhood alone:
   a garrison can host two batteries of the same system, so merging co-located reports into one unit would
   *undercount the order of battle* — the harmful direction of error for this use case (see §7's cap). The
   clean layers are the lattice the fuzzy layer crystallizes onto — the more resolvable the *other end* of a
   relation, the less fragmentation it produces — but they buy **recall and presence**, not formation
   identity.
3. **Discriminators + temporal succession on the cross-doc merge.** "Unit at XYZ" and "unit at LMN" is not
   obviously two units: same operator + design at two sites at the *same time* is two presences (or an error);
   the same at *different times* is either **rotation** through a base or one **formation** that relocated —
   and telling those apart is a formation-level question that needs a unit-level discriminator, not a shared
   site. So relocation is never a single "relocated" fact; it is a **chain of presence observations plus
   (maybe) a continuity signal** — a dated imagery sequence (present at A → absent → present at B), a shifting
   NOTAM/airspace pattern, news of a redeployment, or a designation re-appearing at a new site. The honest
   ladder, which lives at the **formation** level:
   - two presences (presence-ended-at-A + presence-began-at-B) → **always expressible**;
   - *possible relocation* → same operator + design + temporal exclusivity, **formation unresolved**;
   - *confirmed relocation* → **+** designation continuity or an explicit transition claim (credibility-gated).

   This is the discriminator + relational + *temporal* reasoning already built (doc 10 D7/D8 succession) — the
   relocation beat is a special case of exactly this, degrading honestly to *"possible relocation, formation
   unresolved"* when continuity isn't earned.

**Honest fragmentation is the goal, not forced density.** Some residual fragmentation is *correct*: when two
documents genuinely cannot be correlated — no shared anchor, no discriminator overlap — the honest outcome is
that they stay separate or sit as a *possible* merge held for a human. Forcing density to look tidy would
just be the name-collapse bug wearing a different hat. What makes residual fragmentation safe rather than
silent is that the coverage surface **reports the unresolved-instance tail as a measured gap** — so sparsity
becomes a *diagnostic* ("these units are under-corroborated; here's where more collection or better coref
helps"), not invisible sprawl.

**Build-order consequence:** resolve the anchors (designs, places, operators) well *first*, do within-doc
coref, and the instance layer largely clusters itself — held together by the clean layers around it, not by
heroic cross-doc matching of bare unit names. Design-layer cleanliness is therefore load-bearing for
instance-layer density, not just correctness hygiene.

## 7. What earns identity — the evidence model

**Per-layer identity policy — one judge, not a second code path.** Every layer runs through the **same**
earned-identity judge (bands, credibility-gated critical wall, geo veto, monotone fixpoint); the only thing
that varies per layer is a **policy profile** — how permissive the corroboration bar is — never a separate
name-key path (F3).
- **Design layer** — collapses *readily* (a genuinely low corroboration bar) but **never on name alone**. A
  name match reaches at most a *possible* merge; one more signal — a shared manufacturer, component or
  co-citation — clears it, and such a signal is trivially available, so designs still collapse in practice
  into one HQ-9 node. A manufacturer or country-of-origin conflict still **walls** the merge. *Honest
  tradeoff:* on a bare corpus where two same-name design mentions share *nothing* else they sit at *possible*
  and don't auto-collapse (mild design-layer fragmentation the use case dislikes) — mitigation: keep the
  design-layer bar low (one shared component/co-citation clears it) and let the residual sit as a one-click
  analyst merge.
- **Instance layer** — a name is **never** sufficient; identity is fully earned, and co-location (shared
  design + site + operator) is *recall and presence support only*, capped below formation identity (the cap
  below).

**What earns an instance merge (roughly in priority order):**
- a shared **unique identifier** (serial, registration, unambiguous designation) → the fast path to confirmed
  identity;
- **discriminator agreement** (same operator + compatible geography + same designation, consistent over time)
  → graded; reaches *probable*, and *confirmed* only subject to the two guards below;
- **relational** (shared neighbourhood, via the clean anchors) → graded contribution (already built — but see
  §13/F9: today only *completed* merges contribute weight, so lean on it only where the anchors resolve into
  real merges);
- **name** → a blocking/recall key plus a rarity-graded score contribution, capped so it never reaches
  probable alone (for *every* layer, §11 D-13.10);
- a **discriminator conflict** (different operator, incompatible geo at overlapping times) → **hard wall**.

**Co-location is not a formation unifier — the OOB-critical cap.** Shared anchors alone (design + site +
operator) are **recall plus graded support that tops out at *probable***. Confirming a **formation** identity
merge requires a **unit-level discriminator** — a designation, a serial, temporally-witnessed continuity, or
analyst confirmation. Merging co-located reports into one *presence* is safe (a presence asserts only
presence); merging them into one *formation* on co-location alone would **undercount the adversary's order of
battle** — the harmful direction of error for this use case. The residual is a **first-class coverage item**:
*"HQ-9/P presence at Rahwali confirmed; formation/unit count unresolved (1–2 candidates); designation coverage
needed"* — the honest OOB answer, and a better demonstration of the non-negotiable than a tidy merge.

**Confirmed identity does not require a unique id** — real order-of-battle rarely carries serials, so
corroborated discriminator + relational agreement can reach confirmed; the unique id is merely the fast path.
Two guards keep this from confirming on weak evidence:
- **Geography is perishable.** "Operator + geo agreement" is perishable-heavy, so by the perishable cap
  (perishable-only evidence ≤ *probable*) a confirm must rest on a **non-perishable** discriminator (a
  designation), a temporally-witnessed continuity, or an analyst — geo agreement alone cannot confirm a
  formation.
- **Independence.** "Enough independent corroboration" explicitly inherits the corroboration ledger's
  source-independence / too-clean machinery (`spine/04`): two derivative reprints of one almanac must not
  confirm an instance merge.

**Discriminators are attributes + relationships + derived geo, and critical-*if-present*.** Not attributes
only: geography is usually a `based-at` relationship or derived coordinates, and operator is sometimes an
attribute and sometimes an `operated-by` edge. The machinery for two of the three already exists (the
attribute-role wall and the geo-coordinate veto); the addition is **critical relationships** (two units at
different sites at overlapping times are different units). *Critical-if-present* means: a discriminator is
identity-critical when the source states it, but its **absence is `unknown`, not a conflict** — an absent
operator can never wall a merge, only leave the instance under-individuated and flagged as a gap. A **value
normalization** step (PAF vs "Pakistan Air Force"; CHINA vs China) is a prerequisite before an attribute or
relationship can wall reliably — otherwise it either misfires or fails to fire.

**Flag-then-split is a normal outcome, not a rare corner.** Because instances are *materialized*, a
discriminator can become visible only *after* a merge — a presence acquires derived geo via an anchor merge
and then conflicts with a sibling at overlapping time. The behaviour is unchanged from the built wall (flag
the conflict now, split on the next rebuild), but with materialized instances this path is an ordinary
steady-state outcome, not an edge case; the monotone-within-rebuild guarantee still holds because the split
lands on the next recompute.

**Reuse vs. new.** The *judge* is built — the credibility-gated critical wall, the geo veto, the graded
scorer, and the collective fixpoint. What is missing: (1) **pairs** — the judge adjudicates candidate pairs,
and instances never form pairs today; the re-key is what *feeds* it (the big one); (2) a **relationship
discriminator** (a `based-at`/`operated-by` conflict as a wall, not just a relational score); (3) **config +
normalization** (declaring operator/branch critical per instance-type, and normalizing values). Reuse the
judge; feed it via the re-key; extend it; configure it.

## 8. The identifier — two layers, and only one of them mints

The word "mint" was overloaded. There are two layers, and only **one** mints; the other **derives**.

- **Ingest-time minting — once, permanent, layer/identity-BLIND.** At ingest, each **claim** (and, with Tier-0
  coreference, each document-local **referent**) is given a stable opaque id, written to the append-only
  evidence log. These are the **atoms**. A claim is a claim forever; **atoms never split or merge.** A mention
  carrying ten attributes becomes ~ten claim-atoms hung on one referent atom — all minted here, *before* any
  layer or identity reasoning runs.
- **Build-time assembly — every rebuild, deterministic, DERIVED.** The rebuild *reads* the atoms and
  **groups** them into knowledge nodes. **Both** kinds of split are grouping decisions taken here, never
  re-mintings:
  - *layer routing (the §5 straddle split)* — the per-attribute layer tags send a straddling mention's design
    atoms to the shared design node and its instance atoms to an instance node (one mention → two linked
    nodes, by sorting its atoms);
  - *discriminator split (identity)* — if two referents were grouped but a discriminator conflicts (R7 = PAF
    vs R12 = PLA), the resolver puts them in two groups instead of one.
  A knowledge node's id is a **deterministic function of its member atoms** — the minimum member-id, or a
  unique identifier when the cluster has one — **computed *after* grouping, never assigned before it.**

**So there is nothing to "place the discriminator before."** Grouping (layer routing + discriminator checks)
happens first; the id falls out last. We never commit a knowledge-id and then have to revoke or re-mint it on
a split — the "which half keeps the UUID?" puzzle only exists if you assign random ids to groups, which we do
not. A split is just atoms landing in two buckets → two fingerprints, each stable and reproducible across
rebuilds; a merge is atoms landing in one. (This **supersedes** the earlier "mint a UUID at the bare-minimum
unit, mint two more on split" framing: the stable opaque id is minted once, at ingest, for the referent; the
split needs no new minting.)

The **human-readable label** — "HQ-9/P (PAF, Rahwali)" — is *derived* for display from the name plus key
discriminators. Name becomes a *label*, not an *address*, which is the whole point. The canonical display id
may **drift** as cluster membership changes across rebuilds; the rebuild emits an **old→new redirect map** so
display and provenance stay continuous.

**This is the fix for the decision-log durability problem.** Analyst decisions and walls must key on the
**atoms** (claim / referent ids — the permanent, minted-once evidence layer), **never** on the derived node id.
(Human-authored config anchors — observables watch-lists and subject-lens anchors — instead stay on **stable
handles**, not atoms; see D-13.15 as amended.) Today they do not: merge accept/reject/split
decisions replay by **name** (which the re-key demotes from identity to recall — silently degrading analyst
authority from *verdict* to *hint*), while status overrides and integrity flags replay by **node-id** and are
**silently dropped** when the id dangles. Both must move to atom-keys, so a decision survives every merge /
split / re-key by construction — the node id may change, but the decision still points at real atoms and
re-applies. (The silent-drop replay path is replaced by **loud failure** during migration; see §12.)

## 9. Chokepoints as a two-layer, operator-scoped property (ontology + materiality)

A chokepoint is a *materiality* property of a **dependency** — a link whose in-degree is one and whose
substitutability is absent or unknown. Dependencies live at **both** layers, so chokepoint analysis is
inherently layered. ("Chokepoint = design layer" was too clean.)

- **Design-inherent chokepoints** — sole-source parts baked into the design (the HT-233 engagement radar, a
  seeker, the design authority). Every operator who fields the design **inherits** them. Shared by
  construction.
- **Operator/instance chokepoints** — how a *particular operator* sustains its fleet: round/battery resupply
  from one logistics partner, the crew-training pipeline, depot maintenance, spares, technical-data
  authority. **Per-operator**, and can differ entirely for the same design across operators (Pakistan
  sustains HQ-9/P differently from how China sustains its own fleet).

Distinguishing property: a **design chokepoint is inherent and shared**; an **operator chokepoint is
per-operator and shared only by coincidence** — if two operators happen to use the same provider it is a
chokepoint for both, but that is *discovered* from each operator's own edges, never read off the design.

**How it computes.** The same materiality test runs over dependency edges at *both* layers — design layer
(`variant → requires-component → component → supplied-by → manufacturer`) and operator layer (`operator/unit
→ resupplied-by → logistics_partner`, `→ trained-by → training_provider`, `→ maintained-at → depot`, `→
spares-from → supplier`). A chokepoint assessment **for an operator** is a layer-*crossing* traversal scoped
by the subject lens: walk that operator's instance layer for its operator-specific chokepoints, and down into
the shared design layer for the inherited ones, and **take the union, scoped to the operator**. An instance
dependency can bottom out in a design chokepoint (Pakistan's resupply of rounds ultimately depends on the
design's sole-source cell maker), so the traversal threads operator → units → sustainment providers → and
sometimes back into the shared bill-of-materials.

**Two consequences that make this load-bearing:**
1. **It requires the individuation.** Operator-scoping the instance chokepoints is only possible if instances
   are individuated by operator. If Pakistan's logistics partner and China's collapse onto one name-keyed
   node, you either misattribute Pakistan's chokepoint to China or lose the operator boundary and cannot
   answer *"where does Pakistan's capability break"* at all — every chokepoint answer is forced up to the
   design layer, which is precisely the flattening we are fixing.
2. **It honours the non-negotiable at the instance layer.** The operator chokepoints — training, resupply,
   maintenance, spares — are exactly the **sustainment tier that is declared in the ontology and carries zero
   instances** today (fielded-SAM sustainment leaves little open-source trace). So for many of them the
   honest output is not a confident edge but a **named gap** (*"Pakistan's crew-training dependency is a
   candidate chokepoint, under-observed, next coverage due X"*) — never a fabricated provider, never a silent
   miss. Only expressible once instances are individuated enough to say *whose* dependency is missing.

## 10. The extraction contract

Re-extraction is *free* here (new data is being built in parallel), so the contract is chosen for
correctness, not migration thrift:
- **Kind** — keep tagging it (a hint, not the authority; the build routes by layer, §5).
- **Discriminators** — emit operator, geography, unit designation, time as **structured claim context**, not
  buried in prose, so the build-time binding and the resolver can use them. **Optional**, never required: a
  required field would force the extractor to fabricate a value the source didn't state (violating the
  non-negotiable) or drop the claim. Absence is recorded and treated as `unknown` (§7).
- **Within-document coreference handles** — emit them, so Tier 0 can mint one provisional instance per
  document-local referent (§6). Largely already produced by the built-but-off coref work.
- **No cross-document identity** — the extractor never decides that two documents' mentions are the same
  thing.

**The extraction burden *moves*, it does not shrink (F6).** §4's "relaxes the extractor requirement" is true
only for **kind** — layer routing self-corrects a mis-tagged kind. But the two biggest fragmentation levers,
**Tier-0 coreference** and **structured discriminators**, are *both* extractor outputs, so the load-bearing
extraction quality shifts *from* kind-tagging (easy) *onto* coref + discriminator capture (harder) — it
concentrates rather than lifts. Two consequences: the replumb eval must **measure coref over/under-binding**
on seeded docs, and **Tier-0 auto-bind is graded by coref category** — an explicit-equivalence or apposition
link binds tightly; a bare pronoun chain is held looser as a proposal. (That grading *is* the open
auto-bind-threshold micro-decision, §13.)

## 11. Decisions

- **D-13.1** Identity is not keyed by `type+name`. Name+type is a recall/blocking gate that guarantees
  *comparison*; the merge is *earned*. Name-as-identity runs in **two stacked lanes** today — an exact-string
  dict-key collision at profile build **and** an exact-normalized-name auto-merge at confidence 1.0 in the
  resolver's bootstrap — so the re-key must remove **both**, not just the dict key. (Realizes D1.)
- **D-13.2** Certainty is reserved for unique identifiers; name similarity contributes a *rarity-graded
  score*. (Realizes D2/D3.)
- **D-13.3** The type/instance layer split is a first-class structural property in the ontology: node-types
  *and* attribute-types are layer-tagged; edge endpoint-layers derive from declared endpoint types. Layer is
  a property of the type (uniform); a genuinely dual attribute is split into two types.
- **D-13.4** The seam: *kind* and *within-document coreference* are **stated** (extractor); *cross-document
  identity* is **earned** (resolver). Within-doc coref is reading, not resolution, and remains a challengeable
  proposal.
- **D-13.5** Build-time split by fact: each fact routes to its declared layer; a straddling mention is split
  into linked design + instance nodes; driven by per-fact layer tags, so the extractor may stay blind to kind
  and the split self-corrects on a misplaced attribute.
- **D-13.6** Edge endpoints: layer is static (ontology); specific identity is resolved at *rebuild* and
  materialized into the view — never per-query, never baked into the immutable claim (bi-level invariant). An
  instance-layer edge *materializes* the instance it implies; a cross-layer holding edge (e.g. `equips`) does
  not.
- **D-13.7** Mint per **document-local coreference cluster**, not per mention/edge. Two-tier resolution: Tier
  0 within-doc coref (source-grounded); Tier 1 cross-doc earned. Edges and attributes of a referent attach to
  its one provisional instance.
- **D-13.8** Discriminators are attributes + relationships + derived geo, declared per instance-type, and
  **critical-if-present**: absent → `unknown` (under-individuated + named gap), never fabricated, never
  rejected, never a wall. Operator/branch is *optional* in the extraction schema, *critical-if-present* in
  resolution. Value normalization is a prerequisite to walling on a discriminator. (Geography is a
  discriminator but **perishable** — it cannot confirm on its own; see D-13.9's cap.)
- **D-13.9** Confirmed identity does **not** require a unique id; corroborated discriminator + relational
  agreement can reach confirmed (unique id = fast path) — subject to two guards from the shipped ledger: (a)
  **geography is perishable**, so "operator + geo agreement" is perishable-heavy and by the perishable cap
  reaches at most *probable*; a confirm must rest on a **non-perishable** discriminator (designation),
  temporally-witnessed continuity, or an analyst; (b) **source-independence** — "enough independent
  corroboration" inherits the corroboration ledger's independence / too-clean machinery (`spine/04`), so two
  reprints of one almanac cannot confirm. A discriminator/geo conflict at overlapping times is a **hard wall**
  (reuses the built wall + geo veto). Priority: designation > operator+geo > relational > name-as-recall.
- **D-13.10** Per-layer identity policy is **one judge with a permissive per-layer profile, never a second
  code path** (F3). **Name is a contributor, never a verdict — for *every* layer**, including design. The
  design layer collapses *readily* (a low corroboration bar) but **never on name alone**: a name match reaches
  at most a *possible* merge, and one more trivially-available signal (shared manufacturer / component /
  co-citation) clears it, so designs still collapse into one node in practice; a manufacturer / origin
  conflict still walls it. The instance layer is fully earned. (Supersedes the earlier "design layer collapses
  by name.") *Honest tradeoff:* two same-name design mentions sharing nothing else sit at *possible* — mild
  design-layer fragmentation, mitigated by a low design bar + a one-click analyst merge.
- **D-13.11** **Two layers, one mints.** Ingest **mints** a stable opaque id — once, permanently,
  identity-blind — for every claim and (with Tier-0 coref) every document-local referent, written to the
  append-only log: these are the **atoms**, which never split or merge. Rebuild **derives**: knowledge nodes
  are deterministic *groupings* of atoms, and a node's canonical id is a function of its member atoms (min
  member-id, or a unique identifier when present), **computed after grouping, never assigned before it**. Both
  a layer-routing split and a discriminator split are just atoms re-partitioning → two fingerprints; no
  re-minting, no "which half keeps the UUID" puzzle. The display id may drift on membership change (rebuild
  emits an old→new redirect map). (Supersedes the earlier "mint a UUID at the bare-minimum unit, mint two more
  on split" framing; determinism / G1–G2 preserved because nothing is minted at rebuild.)
- **D-13.12** Fragmentation is *contained* (within-doc coref + clean-anchor relational scaffolding + earned
  cross-doc merge) and *made honest* (residual fragmentation reflects genuine evidential uncertainty and is
  surfaced as a measured gap via `/coverage`). The architecture never forces density — forced density is the
  name-collapse bug returning.
- **D-13.13** The instance layer has **two citizens defined by their creating evidence**: a **presence**
  (operator's design observed at a site during a time-window; born from observation evidence; the default
  workhorse instance; `count` is a *sourced attribute*, default unknown, never `= reports merged`) and a
  **formation** (the organizational, designation-bearing individual that persists through moves; minted
  **only** when organizational evidence exists — we never force an unsourced formation, on pain of the
  non-negotiable; a formation *threads* presences over time/space). **A formation is evidenced two ways:
  *stated* (a source directly names the unit at a site → an extractor `based-at`, `kind=observation`, normal
  source credibility, can reach *confirmed* — the stronger path) or *derived* (equipment sighting +
  `inducted-into` membership → a `kind=inference` `based-at`, premise-tied, capped at *probable*). Both are
  organizational evidence; neither bypasses source grade or the deception gates (a grade-E stated basing
  still lands at *possible*). Derivation is the fallback for the common open-source case, not the only
  route.** This names and elevates a distinction the ontology already draws — `observed-at` = presence,
  `based-at` (functional, unit-keyed) = formation — and makes formation minting explicitly evidence-gated.
  Layer-routing test: *does the fact change if a different operator fields the design?* No → design; yes →
  instance.
- **D-13.14** **Co-location is not a formation unifier.** Shared anchors (design + site + operator) give
  recall + graded support that tops out at *probable*; confirming a **formation** merge requires a unit-level
  discriminator (designation, serial, temporally-witnessed continuity, analyst). Merging co-located reports
  into one **presence** is safe; merging them into one **formation** on co-location alone would **undercount
  the order of battle** — the harmful error for this use case. Relocation lives at the formation level as an
  honest ladder (two presences → *possible relocation* → *confirmed relocation* on designation continuity /
  explicit transition, credibility-gated). The residual is a first-class coverage item ("presence confirmed;
  formation count unresolved; designation coverage needed").
- **D-13.15** *(amended 2026-07-24 — split into two cases during implementation planning; realized by plan A6.)*
  **Analyst decisions and walls** (merge accept/reject/split, status/integrity overrides) key on the **atom ids**
  (claim / referent ids — the permanent, minted-once evidence layer), **never** the derived node id, so they
  survive every merge / split / re-key by construction; migration replays with **loud failure** on any dangling
  reference, never a silent skip. (Today merge decisions replay by *name* — the re-key demotes that to recall,
  silently degrading analyst authority — and status/integrity overrides replay by *node-id* and are **silently
  dropped** on a dangling id; both move to atom-keys.) **Human-authored config anchors** — `observables.yaml`
  watch-lists, subject-lens anchors — instead stay on **stable handles** (registry entity ids, or names resolved
  through the resolver's string→node ladder), **not** the drifting derived node id and **not** an atom: a watch-list
  over a *whole cluster* has no single natural atom, and a human authors it by name/designation. Loud-fail scopes to
  decisions only; applying it to config anchors would break lenses/observables on every re-key — the opposite of
  durability.
- **D-13.16** **Location containment / query-time proximity is DEFERRED to roadmap.** The positive
  place-to-place containment traversal + a "near X" query operator (so "near Rawalpindi" lends graded,
  area-labelled support to a Nur-Khan question) is *purely additive* — new place-to-place edges + one query
  tool — so deferring costs nothing and forces no rework. **The non-negotiable half is already available and
  must be stated:** because a `Location` value already carries `precision_class`, ASK can already refuse to
  overclaim ("we have a district-level report, not a site fix at Nur Khan"). Only the *positive cross-precision
  relevance* is the roadmap item; nothing in the presence/formation or id/decision-log work depends on it.
  Resolution-time doctrine is unchanged: a coarse mention never pins/merges to a fine site.

## 12. Migration

Staged, never big-bang; each stage independently verifiable; old vs new dual-run on the frozen corpus before
cutover:
1. **Split id from label / mint atoms at ingest** (non-breaking) — establish the append-only claim/referent
   ids as the stable anchors everything else will key on.
2. **Add layer typing + edge-endpoint resolution** behind a flag (the §5 pipeline). **Note (F8):** endpoint
   materialization *before* Tier 0 lands (stage 3) means per-edge / per-mention provisional instances —
   exactly the fragmentation §6 exists to prevent. This is a **known, transient** interim for dual-run
   verification only: **fragmentation metrics are meaningless until stage 3** and must **not** be "fixed" by
   loosening merge thresholds (which would then be far too loose once coref clustering lands).
3. **Flip instance minting** to per-document-coref-cluster (Tiers 0/1) — the first stage at which
   fragmentation metrics are meaningful.
4. **Cut the name-key** — entity address stops being the name; the atom→entity indirection replaces it across
   the edge model, alias index, and reference resolver. **Migrate the decision log to atom-keys** (both halves
   — name-keyed merge decisions and id-keyed status/integrity overrides), **re-anchor** user-defined
   observables and subject-lens anchor lists, and make decision replay **fail loudly** on any dangling
   reference (never the current silent skip).

**Cost accepted (per the user):** node ids, the partition, the golden view and the answer key all change →
full regen, and the hero demo thread is re-verified against new ids/citations. Re-extraction is free (data
built in parallel), so the extractor contract (§10) changes with it. This is a multi-week substrate rework,
post-deadline — the real-system build, not a demo fix.

## 13. Relation to prior work, status, and open items

Realizes **D1–D3** of `10-resolution-real-world-redesign.md`; the shipped D4–D11 (graded identity, walls,
temporal/succession, status-weighted relational, coverage) sit *on top of* this substrate and become fully
effective once it exists — the re-key *feeds the already-built judge the pairs it was built for*. Complements
`12-data-refresh-calibrations.md` (§B1's operator/branch critical-wall + value-normalization is a special
case of D-13.8/13.9). **One drift to note (F9):** the shipped status-weighted relational signal is **weaker
than doc 10 D10 intended** — only *completed* merges contribute weight; a sub-review (probable/possible) link
contributes exactly **0**. So §6 lever 2's anchor-scaffolding must **not** assume graded sub-confirmed
relational weight exists; the lever still works because designs/places resolve into *real* merges, but the
graded-sub-confirmed part is aspirational until fixed. **Not started.**

**Highest-risk piece:** §5 step 3 + §6 — the *characterize-and-cluster* of provisional instances: how a
provisional instance is described richly enough to cluster (which discriminators, in what priority), and how
a thin-context bind degrades to "under-determined + gap" instead of either fabricating a unit or collapsing
two. The risk **concentrates in extraction quality, not just resolution** (F6): the two biggest levers —
Tier-0 coreference and structured discriminators — are both extractor outputs, so the load-bearing quality
moves *onto* coref + discriminator capture, and the replumb eval **must measure coref over/under-binding** on
seeded docs. Everything else is tractable; this is where the design attention and the engineering risk
concentrate.

**Decided (this alignment, 2026-07-24):** provisional-instance **mint grain = the doc-local coreference
cluster** (edge endpoints and attribute mentions of one referent attach to it; supersedes any per-edge
minting).

**Micro-decisions — CLOSED by RK-SPIKE (2026-07-24).** Full rationale, the mechanism tables, and the
three-way disagreements and how they resolved: `../../tmp/conv/rk-spike-DECISIONS.md`. The verified code
baseline the decisions rest on: `../../tmp/conv/rk-spike-code-facts.md`. The defects they must design around:
`../../tmp/conv/rk-spike-verified-defects.md`.

**The mechanical fact that governs all of them.** An "authoritative" coref pair is a Phase-1 **bootstrap
trigger**: it merges at hardcoded confidence `1.0` and **bypasses banding entirely** (`resolve/cluster.py:462-465`).
No cap restrains it — not the name cap, not the perishable cap, not a band ceiling. So authorizing a category
authorizes an *uncapped, unbanded fusion on a model-chosen label*, and a category may only be authoritative
behind **both** a deterministic code-verified precondition **and** a source-grade floor.

- **D-13.17 — Tier-0 auto-bind by coref category.** `EXPLICIT_EQUIVALENCE` and `UNAMBIGUOUS_ANAPHOR` are
  **authoritative**, each behind a deterministic gate (equivalence: the licensing quote contains *both*
  surface forms *and* a configured equivalence marker; anaphor: a **type-unique antecedent** — no second
  compatible-type mention in the document it could mean) **and** a source-grade floor set *strictly above* the
  stated-`same-as` floor. `NAME_VARIANT` is **raise-only, permanently** — because an authoritative bind bypasses
  banding, "authoritative name-variant" *is* the exact-normalized-name lane D-13.1 exists to delete, rebuilt on
  another predicate and immune to D-13.10's cap. A coref bind today acts **harder** than a source-stated
  `same-as` (which is grade-floored *and* raise-only) while reading **no grade at all** — that inversion is the
  sharpest gap in the substrate, and **stated ≠ trusted** (§5) closes it.
- **D-13.18 — "held looser", and the grouping the rebuild may DECLINE.** Only an authoritative cluster mints
  **one shared referent atom**; a looser cluster mints **one referent atom per member** plus an injected Tier-1
  candidate pair carrying its licensing quote. **The referent atom is *evidence about a grouping*, never the
  address of the provisional instance** — rebuild groups **claim atoms**, and an intra-referent
  critical-discriminator conflict makes the rebuild **decline** the grouping, de-grouping to claim-atom
  granularity and raising. *No atom splits; the grouping declines.* This is what makes §4's "challengeable
  proposal" true; **without it S3 would make intra-document over-merge permanent**, which is disqualifying.
  (D-13.7/D-13.11 and plan §7 RK-COREF item 1 currently read either way — they must be written the safe way
  before S3 starts. The decline check must read `attr_history`, not `attrs`: first-claim-wins scalar storage
  makes an intra-referent conflict invisible.) *Not implementable:* a per-link authoritative closure — the
  coref category is stamped per **cluster**, not per link.
- **D-13.19 — Tier-1 same-document comparison + the contrastive prior (closes F5).** Tier 1 **already** compares
  same-doc pairs — there is **no document filter anywhere** in `resolve/**`, so that half of F5 needs no code.
  A same-doc **stated-contrast** pair is **capped at *probable*** (reaches the analyst with its quote; can never
  auto-merge); absence of contrast is **neutral**, never a prior *for* merging. The config value is a **band
  name, not a float** — a coefficient is rejected because at the shipped thresholds a ×0.5 penalty drops a pair
  *two* bands, silently out of the analyst's queue. The ceiling is **ungraded**, because unlike a veto it
  **cannot shatter** an existing cluster — it withholds one new fusion. Carriers: **`Entity.doc_ids`** (populated
  where the doc ref is currently dropped; *not* by parsing a claim-id format, and *not* `source_ids`, which is the
  publisher) and a **new contrastive channel on coref** on its own `coref-distinct-from` lane — *never* the stated
  `distinct-from` rail, which is hard, transitive and ungraded (every ORBAT list contains an enumeration).
  Separately: a source saying *"two batteries"* is **stating the OOB figure** — capture it as a sourced `count`
  attribute on the presence (D-13.13). "Distinct designations" is **not** a syntactic contrast and moves to
  D-13.20.
- **D-13.20 — Discriminator priority.** **differing designation (veto) > composite unique identifier >
  temporally-witnessed continuity > shared designation > operator (post-normalization) > geography (perishable)
  > relational (F9-limited) > name (ceiling at *possible*)**. Priority manifests in **three shapes — blocking,
  score, cap/wall — not one dial.** The load-bearing call: **a shared designation is NOT a unique identifier**
  (designations are reused across armies and across time), so `hard_id_fields.unique` is a list of **composite
  AND-keys** — `(service_branch, designator)` identifies; a bare `designator` does not. This makes the operator
  requirement *structural in the identifier declaration* rather than dependent on a namespace check that is
  **broken in the Phase-2 fixpoint**. One shared designation string may never confirm a formation merge. The
  codebase already embodies this asymmetry for bills of lading (differing identifiers veto; shared ones do not
  confirm) — preserve it. Enabling change: **split `attribute_score` into two signals (`name` / `discriminator`)**
  — already computed independently and fused at one `max`, so a small change, and **without it D-13.10 cannot
  function at all.**

**Corrections this forces on the text above.** (i) "Capped at *probable*" is **not expressible as written** —
there are three bands, no `reject` verdict, and only `same_as` fuses; read every such phrase as **"not fused;
queued and reported."** (ii) **Lever 2 is weaker than §6 claims, in two independent ways**: F9 (only *completed*
merges carry relational weight) *and* `places.augment` running **after** `resolve_entities`
(`resolve/__init__.py:181` vs `:177`), so place merges are invisible to `relational_score` — places are
mechanically **not** the clean anchor the design names. (iii) **"Rarity-graded name" has no implementation
anywhere**, yet D-13.2 and D-13.10 both rest on it. (iv) The raise-only **licensing quote is written but read
nowhere** — the mitigation that makes raise-only acceptable does not yet exist.
