# 16 — Design-note disclosures (own-the-tradeoffs list)

**Purpose.** A running list of honest limitations / design choices to **state out loud in the 2–3 page
design note** (guiding principle #7: naming synthetic-data limits is the senior move; hiding them reads
junior). When an agent curates the design note, it reads this file and folds these in — framed as
deliberate, defensible choices, not apologies.

---

## Data & imagery

- **All text docs are synthetic-from-real-template.** Real specimens (SIPRI row, ISPR PR, ImportYeti/Zauba
  BoL, India MTD tender, NOTAM/NAVAREA) supply *format + messiness*; entities/values are varied
  synthetically. The generator is **blind to the ontology** (emits raw artifacts, never clean fields) — this
  kills the "you extracted what you planted" circularity objection. Messiness is applied as **enumerable
  corruption operators**, not "LLM make it messy."
- **The customs/tender layer is synthetic by necessity, not convenience.** Finished SAM systems are
  genuinely invisible in public customs data (Russia classified 2022, China aggregate-only, Pakistan no
  feed, India MoD carve-out). So the customs file is synthetic-from-real-template — defensible, and we say so.
- **"Confirm" satellite frames are REAL imagery of genuine SAM sites, RELABELED to the scenario location.**
  d07 (Karachi) ← HQ-9 nr Xi'an; d17 (Rawalpindi) ← PLA garrison nr Nanjing; d18 (Rahwali) ← S-400 nr
  Feodosia; d17b (empty) ← empty HQ-9 petal nr Lanzhou. Each is `integrity: real`, unaltered pixels, with
  `provenance: relabeled` + `real_source` recorded in the scenario's provenance metadata. Rationale: a fabricated "confirming"
  image is exactly what the system should *catch*, so the confirm frames use real SAM-site morphology; we do
  **not** publish novel geolocations of live batteries (the specific pad coords in the doc text are
  synthetic). The VLM caption is neutral (describes only pixels), so the petal/launcher shape genuinely being
  present is what makes the claim supportable.
- **Sentinel-2 (10 m) cannot resolve launchers** (a TEL ≈ 1 px). We use it only for the deliberately-low-res
  beat (cloud gap → insufficient-evidence); sub-meter Esri World Imagery carries the frames that must *show*
  a site. Resolution honesty is a feature: an image never claims more than its pixels show.
- **Fabricated images are JPEG-encoded with a `.png` name** (the image model returns JPEG). Valid, browser-
  renders; a cosmetic wrinkle only.
- **The attribution *fingerprint* (d25) is a deterministically-drawn schematic, not a real overhead frame.**
  The reference the imagery inference matches against is a labelled top-view *recognition schematic* (reportlab,
  no RNG/network — reproducible), the genuine genre of SAM-site recognition literature (cf. ausairpower /
  ResearchGate battery-layout figures). Chosen over a real Esri petal deliberately: reusing a real HQ-9 frame
  (Xi'an/Lanzhou) would collide with d07/d17b under the recycled-image (PDQ) detector and falsely fire the M4
  recycled-image trap reserved for the parade chain; an ambiguous fresh frame wouldn't show the geometry
  cleanly. The schematic is honest reference literature *about* HQ-9 (subject-blindness applies only to the
  target-imagery leg, never to reference literature) and encodes the real published geometry.

## Analytic honesty

- **The chokepoint (HT-233 engagement radar) is a CANDIDATE, not a confirmed sole-source.** The authoritative
  open-source study (CASI/BluePath 2025) marks the HT-233 *manufacturer* UNKNOWN and debunks the common
  "CPMIEC makes it" claim (CPMIEC is the export agent). We model this as a **Known Gap** with a best-candidate
  (CASIC 23rd RI, inferred) — deliberately NOT a fabricated confirmed edge. This is the non-negotiable in action.
- **Confirmed vs probable vs insufficient are structurally separated**, and "insufficient evidence to assess"
  is a first-class output (with missing slots + next-coverage-due), not a failure.
- **Two sustainment node types — an interceptor stockpile and a technical-data authority — are declared in the
  ontology but carry zero instances in this corpus**, so the `sustained-by` rollup they feed is never
  synthesized. They are empty for opposite reasons, and both are informative.
  - **Interceptor stockpile — the sources deny it.** The only candidate document is a spares tender that
    states its requirement "pertains solely to sustenance/repair-and-overhaul (R&O) support of equipment
    already fielded and does NOT constitute procurement of a new weapon system, launcher, missile round, or
    fire-control radar", and separately that "No new launcher units, radar sets, or missile rounds form part
    of this requirement." The corpus's only other reference lists missile stockpile among force-level
    specifics that "remain unconfirmed in the open literature and should not be treated as established fact."
    None of the attributes the type calls for — magazine depth, days of supply, resupply lead time — is
    stated anywhere. Asserting a stockpile here would mean inferring force posture from a maintenance
    contract, which is precisely the inference this system is built to refuse. The node stays empty by design.
  - **Technical-data authority — the source states it and we do not yet capture it.** A trade-media report
    describes radar mode libraries, waveform parameters and calibration tables as being "routed through a
    Chinese state technical-data authority, understood to sit within the broader CASIC/CPMIEC export
    administrative chain, which retains configuration control over the underlying software baseline." Our
    extraction schema offers a slot for this on the procurement-tender form but not on the analytic-prose
    form, so the model had nowhere to record it — a known, mundane gap rather than a judgement call. The
    source also scopes that control to the engagement radar specifically, whereas our dependency edge is
    typed authority-to-system; recording it faithfully would need a component-scoped relation.

  We would rather ship two honestly empty node types than two invented ones.

## Scope & calibration

- **One frozen subject/scenario for the demo** (HQ-9/P, as signal + chaff). The strategy supports multiple
  frozen scenarios an evaluator picks live; a second independent scenario is roadmap (TBD).
- **One fully-threaded observable** (the Rawalpindi→Rahwali relocation). Secondary observables (spares tender
  → probable induction) ship config-only — proving observables are declarative, not hardcoded.
- **Calibration constants** (credibility weights, thresholds, freshness half-lives) are coarse, sensible
  defaults, uncalibrated on the frozen corpus — analyst-tunable by design; calibration is a next step.
- **LLM-only extraction, frozen and replayed** for demo determinism (Opus 4.8 has no temperature knob);
  VLM/extraction confidence is held at 1.0 (the seam for non-uniform extractor confidence is pre-wired).

## Extensibility claims (state as "cheap because pre-wired", not "built")

- **A and B fall out of the spine by specification** — events and inference are first-class in the schema, so
  A (longitudinal baseline) and B (intent / I&W estimate) are new config + one scoring module, not core
  rework. We build C; we *describe* plugging in A/B.

## Sub-question decomposition (multi-part answers)

- **A question that asks two-plus distinct things is answered in parts.** When the planner decomposes a
  question into several `graph_analyze` calls (e.g. an origin/supply trace AND a separate sole-source
  assessment), the assembler renders each as its own cited section rather than picking one tool for the
  whole thing or dropping a half. A single-intent question is unchanged and is never split.
- **Section headers are uncited structural labels, by design.** A multi-part answer prefixes each section
  with a short label ("HQ-9/P — supply chain"). That label asserts nothing about the world's evidence, so
  it carries no citation and is exempt from the citation/entailment validator — the same principle already
  used for the derived-metric and weighed-and-not-carried sentence classes. Every *assertion* in each
  section is still cited to a real claim; only the navigation label is exempt.
- **A decomposed answer shows its hops as cited prose, not as a single numbered timeline.** Two independent
  traces have no one coherent walk, so the multi-section answer renders every hop line as a cited prose line
  instead of a merged timeline (which would be misleading). Limitation: with the *optional* entailment judge
  enabled (off by default), those prose-rendered hop lines lack the per-hop resolved-identity bridge the
  single-shape path gives the judge, so a faithful multi-section answer could be withheld under the judge.
  Off by default; single-intent answers (including the worked-query demo) are unaffected.
- **Only multiple `graph_analyze` calls combine.** Combining multiple bare `find_paths` calls the same way
  was deliberately skipped: the path builder pulls in shared state from other tool calls (node materiality,
  neighbour "weighed-and-not-carried") that does not partition cleanly per path, so it would add risk for
  little gain — the prompt steers multi-part questions to `graph_analyze`, which is self-contained per call.

---

*(Append new disclosures here as they arise. Keep each one framed as a deliberate, defensible choice.)*
