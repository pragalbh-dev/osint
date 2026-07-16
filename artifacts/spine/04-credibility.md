# Spine — Credibility, Confidence, Freshness, Sufficiency, Integrity

The load-bearing doc. "Lead with credibility, not collection." Covers how a claim earns a confidence, how
freshness modulates it, how confirmed/probable/stale is decided, how insufficient-evidence is detected,
and how manipulated/miscaptioned media (Module 4) feeds the same score.

---

## Decisions

### Credibility = a tunable function of user-defined factors (Module 1)
Module 1 is literally "credibility based on user-defined factors / criterion," so credibility is a
**configurable** function, not a hardcoded per-source number. Inputs:
- **Source-class reliability** — official > trade media > anonymous social (analyst-configurable weights).
- **Corroboration** — count of *independent* claims supporting the same edge.
- **Integrity signals** — is the artifact authentic and correctly attributed (see M4 below).
- **"Too-clean" penalty** — a source that is suspiciously perfect / perfectly placed drops in credibility
  (deception resistance; see `06-adaptation.md`).

Output: a **confidence per claim** that propagates to node/edge confidence → **confirmed vs probable**.

### Corroboration alone is not enough — it's gameable
Corroboration counts *independent* sources. An adversary plants one fake plus two "independent" posts
referencing it; a corroboration-only system raises confidence on the fabrication. So corroboration is one
input, not the whole score. Independence itself must be assessed (coordinated-inauthenticity check, M4).

### Confidence → status, with freshness as a per-edge-type modifier
**Freshness-sensitivity is a property of the edge type**, because facts perish at different rates:
- **Durable** (manufacturer→component, variant lineage) — effectively no decay.
- **Perishable** (basing, disposition, unit readiness) — decays fast.

Model: give each edge type a **half-life**; effective confidence =
`corroborated_confidence × decay(age, half_life_of_type)`.

**State machine:**
- **Confirmed** = multi-source corroboration **AND** freshness above threshold.
- freshness lapses → **Confirmed-as-of-DATE / coverage-lapsed** →
- → **Probable (stale)**.

A node **never silently stays "confirmed"** as it ages. This single rule operationalises both freshness
*and* the "sources close" half of adaptation (`06-adaptation.md`).

### Insufficient-evidence via evidence-requirement templates
The non-negotiable ("return 'insufficient evidence', name what's missing, when next coverage is due")
is made demonstrable by a **configurable evidence-requirement template per assertion type**. Example:

> *confirm a basing* = (overhead imagery **OR** ≥2 independent textual sources) within the freshness window

Check which slots are filled. Empty slots → *"insufficient evidence; missing: overhead confirmation; next
coverage due DATE."* Because the template is explicit, the **gap statement is generated, not hand-written.**
This is the highest-leverage single pattern in the spine — it turns the non-negotiable into a checkable,
defensible mechanism. It's also configurable, satisfying "sufficiency should be a configurable decision."

### Module 4 (manipulated / AI-generated media / misinformation) — three orthogonal axes, one score
From `../md/04-claude-chat.md` Q4. Do **not** collapse M4 into "corroborate the claim." Three axes feed
the *same* unified confidence:
1. **Content veracity** — is the claim true? → corroboration + credibility.
2. **Artifact integrity** — is this image/video authentic and unmanipulated?
3. **Contextual provenance** — is a *real* artifact correctly attributed to the claimed time/place/event?
   (The recycled-2019-photo-with-new-caption case — corroboration can't catch it; first-seen/reverse-image
   can.)

**Cheap, defensible signals** (each applies a *credibility penalty*, not a binary fake/real verdict):
- **VLM caption-vs-image consistency** — caption says "launcher at Base X," VLM sees a civilian truck or
  95% cloud → flag.
- **Cross-source physical consistency** — satellite reports total cloud cover, but a "clear daylight photo"
  of the same base the same day exists → suspicious.
- **Provenance / recency** — first-seen date / reverse-image catches the recycled photo.
- **Coordinated inauthenticity** — N near-identical posts in a tight window → manufactured consensus,
  discount (this is the "too-clean"/independence signal; a network signal, not a content one).

### Image trust is source-tiered (satellite vs social)
- **Commercial satellite imagery — high-provenance confirmation.** Known provider/timestamp/geo. Job:
  confirm basing/disposition + geolocate → **promotes probable → confirmed**. Failure modes: staleness
  (old imagery as current) and occlusion (cloud → insufficient evidence).
- **Social-media images — low-provenance lead.** High volume; where misinformation concentrates. Job:
  tip-off only → can raise a node to *probable*, **never confirm it alone**; must run the full integrity
  stack.

The M4 demo flex: plant one **fabricated-but-corroborated** item and show an integrity signal overriding
the corroboration count — the single moment that proves you didn't fall into the corroboration-only trap.

---

## Open questions
- **Score combination** — how exactly do source-class, corroboration, integrity, and freshness combine
  into one confidence? (weighted function vs a small rule set vs Bayesian-ish update). Pick a transparent,
  explainable form; auditability > sophistication.
- **Half-life values per edge type** — defensible defaults, configurable. Decide the C set in
  `../C/01-materiality-ontology.md`.
- **Confirmed/probable thresholds** — the exact corroboration count + freshness cutoff. Configurable.
- **"Independence" definition** — when do two sources count as independent? (different source class,
  different origin, not citing each other). Needs a concrete, defensible rule.

## Research directions
- Structured-analytic-technique grounding for confidence language (e.g. words-of-estimative-probability /
  ICD-203-style probability bands) so "confirmed/probable/possible" map to defensible ranges.
- Practical, cheap deepfake/manipulation signals that survive a demo (ELA, metadata, reverse-image APIs) —
  scope the "credible attempt," not a solved detector.
- Freshness / bi-temporal modelling patterns (cross-ref `01-graph-and-ontology.md`).
