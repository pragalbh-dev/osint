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
  `provenance: relabeled` + `real_source` recorded in the answer key. Rationale: a fabricated "confirming"
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

---

*(Append new disclosures here as they arise. Keep each one framed as a deliberate, defensible choice.)*
