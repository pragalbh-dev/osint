# 10 — Data-Generation Strategy (Use Case C, reusable to A/B)

**Status:** proposed for review · **Author:** agent (autonomous session, 2026-07-17) · **Reviewer:** Pragalbh
**Companion:** [`11-data-requirements-from-pragalbh.md`](11-data-requirements-from-pragalbh.md) (what I need from you) ·
grounds on [`05-data-scoping-C.md`](05-data-scoping-C.md), [`09-corpus-sizing.md`](09-corpus-sizing.md),
`spine/04`, `spine/08`, `C/01`, `C/02`, `06-preflight-audit.md`.

> **What this doc is.** The concrete plan for manufacturing the corpus: how to make data realistically
> messy, how to **plant misinformation** so the credibility/corroboration/counter-deception machinery has
> something real to catch, how to fabricate **testable *and* refutable** evidence per node, how to
> manufacture data that **bypasses** naive corroboration (and the one-line fixes that close each bypass),
> and how the whole engine is **config-driven so it re-serves A and B**. Written to be defensible on the
> call, line by line.

---

## 0. The three-sentence version

1. Every document is a **raw artifact** carrying **claims**; messiness and deception are applied as
   **enumerable operators** whose signal is **earned from the text**, never a hidden flag (this is the fix
   to audit `H-DEFENSIBILITY-1` — "deception is configured, not computed").
2. Each graph node/edge gets a **claim-set** engineered to make the credibility machine *discriminate*:
   at least one **testable** (corroborating) path and at least one **refutable** element (single-source,
   contradiction, decoy-cap, stale, or gap), so confirmed-vs-probable-vs-insufficient is a *computed*
   outcome, not a label.
3. A **bypass suite** manufactures data that defeats a naive corroboration *count* — and, in one case
   (supersede-spoof), defeats even our *current* design — each paired with the exact fix that closes it.
   That pair ("here's the attack, here's the patch") is the counter-deception demo.

---

## 1. Principles (what governs every generation choice)

| # | Principle | Why (grounded) |
|---|---|---|
| P1 | **Raw artifact only.** Generate the document as it appears in the wild — no provenance header, no `Notes:`, no answer-key fields in the text. | The pipeline must *earn* extraction. Fixes the annotation-leakage defect + `H-DEFENSIBILITY-1`. |
| P2 | **Signal earned, not flagged.** Any deception must be *computable from the raw content* (near-duplicate text, an explicit "per SIPRI" citation, a shared image reference, an aligned source identity, a "a second source confirms" sentence). The ground-truth flag is the **answer key**, never the input. | `H-DEFENSIBILITY-1`: "every independence/too-clean input is hand-populated, not computed." Planting the signal in the text is what makes detection real. |
| P3 | **Messiness sourced from reality.** Corruption operators seed from real specimens (SIPRI row, ImportYeti BoL, India MTD tender, NOTAM/NAVAREA strings, real alias set) — never "LLM, make it messy." | `05 §0`; avoids fake-messy that the extractor un-messes too easily. |
| P4 | **Enumerable & reportable.** Every operator applied to every doc is recorded in `manifest.jsonl` so it's stateable on the call ("this doc carries operators X, Y; here's the pipeline behaviour it forces"). | `M-DATA-1` (operators are prompt labels today, unaudited). |
| P5 | **Each unit must demonstrate its mechanism.** A chaff doc that doesn't actually sink, an echo that doesn't actually collapse, a stale that doesn't actually decay = a doc that costs verification and proves nothing. Every doc is verified for *downstream behaviour*, not just extraction. | `09 §6`, `H-*`. |
| P6 | **Don't over-clean the mess.** Preserve genuine ambiguity; do not pre-resolve cover stories (strip d05's in-line resolution). "Messiness should be maintained." | Pragalbh's steer; `M-DATA-1`. |
| P7 | **Config-driven & use-case-agnostic.** The engine touches only YAML (`ontology / sources / credibility / templates / subjects / observables` + a new `operators` + `scenario/chaff` spec). A/B ride the same engine. | `spine/08` reuse contract. |

---

## 2. The reusable engine (unit = the sourced claim)

The generator is three layers over one atomic unit — the **sourced claim** (`Source S, dated D, asserts
<subject, predicate, object>`), which is the spine's unit of analysis and therefore the natural unit of
*generation* too. This is what makes it reusable across A/B/C.

```
scenario spec (YAML)                      ← what facts exist, which are signal/chaff/planted
   │  ground-truth graph (answer key: nodes, edges, status, evidence dates)
   │  per-document: source, asserts (intent), corruption ops, deception ops, dates
   ▼
generator (render_document, Claude Sonnet 5, blind to ontology)
   │  emits ONE raw artifact per doc + a manifest row (ops applied, source-registry fields)
   ▼
frozen corpus  →  ingestion/extraction (offline)  →  bi-level graph  →  credibility resolver
```

**Two sidecars accompany every generated doc (never inside the doc text):**
- **`manifest.jsonl` row** — provenance + which corruption/deception operators landed (P4).
- **`answer_key` entry** — the ground-truth claim(s) the doc *should* yield, the source-registry fields
  the pipeline should *compute* (`primary_origin_id`, `aggregator_of`, `bias_vector`, `reliability_grade`,
  `adversary_denial_flag`, `first_seen`, `decoy_risk_flag`, `coordinated_inauthenticity_flag`), and the
  **expected pipeline behaviour** (confirmed/probable/insufficient/contradicted/stale). This is the
  verification oracle (P5) — the pipeline must *reproduce* these from the raw text.

Why this generalizes to A and B: the unit (claim), the sidecars (independence + bi-temporal stamps +
expected behaviour), and the operator families are use-case-independent. A and B add **new source/template
configs and new asserted claim-types**, not new engine code (see §7).

---

## 3. Corruption operators (format / messiness) — enumerated

These make a *true* artifact realistically hard to parse. Applied per-source; recorded per-doc. Seeded
from real specimens (P3). This is the enumerable list that was missing (`M-DATA-1`).

| Op | What it does | Real basis | Applies to |
|---|---|---|---|
| `alias_substitution` | swap in a designator variant (HQ-9/P ↔ HQ-9P ↔ FD-2000; Triumf ↔ Triumph ↔ SA-21) | real trade-press variance | all text |
| `transliteration_drift` | Hongqi/红旗/紅旗; Cyrillic С-400; consignee spelled 2 ways across rows | real customs/academic | reference, customs, social |
| `hs_code_masking` | goods as bland HS (8526 "radar apparatus parts") not description | real dual-use trade | customs |
| `front_company_consignee` | consignee = trading house/freight-forwarder, not end-user | real BoL | customs |
| `redaction` | `[REDACTED]` contract nos., `as per Annexure-B`, "name withheld" | real DGDP/MTD tender | procurement |
| `ocr_garble` | broken word-wrap, mid-word case breaks, fax/email leakage in a field | real ImportYeti row | customs, scanned |
| `date_format_flip` / `relative_time` | "07 Feb 2023" vs "this morning" vs "last night" | real social/press | social, press |
| `coordinate_absence` / `coordinate_fuzz` | "near the port road", no pin; or rounded coords | real OSINT posts | social, imagery-caption |
| `hedging` | "reportedly / believed to be / estimated / may employ / likely" | real analyst prose | media, reference |
| `code_string_noise` | raw uppercase NOTAM/NAVAREA (Q-line, DTG windows, polygon vertices) | real FAA/NGA strings | nav-warning |
| `truncation` | cut-off record, "first 200 words only (paywalled)" | real cached fetches | reference, media |
| `unit_count_absence` | capability stated, battery/TEL count "not disclosed" | real (Pakistan never disclosed) | all signal |

**Guardrail (P6):** operators add *noise*, never *resolve* it. A dual-use contradiction is left standing
for the pipeline to surface — the generator must not write the answer.

---

## 4. Deception operators — the misinformation-planting plan

This is the core ask: a **concrete, real-world plan to plant false information** so the counter-deception
machinery is exercised, not asserted. Eleven operators. Each carries: the **detectable signal** (what
appears in the raw text — P2), the **ground-truth flag** (answer key), the **detector** it exercises
(from `spine/04`/`08`), the **expected pipeline behaviour**, and the **refutation path**. Operators
marked **⚔ BYPASS** are engineered to defeat a *naive* system; `D8` defeats even our *current* design and
ships with its fix.

> Framing: this is synthetic, clearly-labelled test data about a **weapons system** (not a person/org),
> built to *harden a defensive counter-deception system*. It is corpus material, not deployable
> disinformation.

### The eleven

**D1 · Recycled / miscaptioned media.** A real older image (e.g. a 2019 parade photo) reposted as a new
2025 deployment.
- *Signal in text:* the post/caption dates the image to 2025 while describing a scene whose details match
  an older event; a reply notes "isn't this the 2019 parade?".
- *Ground truth:* `first_seen = 2019`, `caption = mismatched`.
- *Detector:* M4 `first_seen{recycled 0.30} × caption{mismatched 0.30}`.
- *Behaviour:* the item's `m` collapses; cannot lift a node past probable. *Refutation:* provenance/first-seen.
- *Have:* d11 (strip its give-away verdict line — `H-DEVIATION-1`).

**D2 · Coordinated inauthenticity (echo burst).** N near-identical posts, tight window, different handles,
one origin.
- *Signal:* near-duplicate wording + burst timestamps + shared phrase/image; handles cross-@ each other.
- *Ground truth:* shared `primary_origin_id`, `coordinated_inauthenticity_flag`.
- *Detector:* coordination check + origin-group collapse (the *one* deception detector kept per `spine/08 §2.3`).
- *Behaviour:* all reshares collapse into **one** origin group (noisy-OR sees one `c_g`, no boost) **and**
  `coordinated_inauthenticity{too-clean 0.4}` penalty. *Refutation:* count origins, not posts.
- *Have:* d12/d13; **deepen to a 4–6-post burst** so collapse is visible (the "grain" is that 6 posts = 1 look).

**D3 · Aggregator / circular reporting. ⚔ BYPASS(naive).** A tracker that presents "multiple sources"
(SIPRI *and* the three press pieces that cite SIPRI) as independent corroboration.
- *Signal:* explicit "per SIPRI / as reported by X / citing the SIPRI register" chains — all traceable to
  one upstream.
- *Ground truth:* `aggregator_of = [press1, press2]`, `primary_origin_id = SIPRI`.
- *Detector:* aggregator-inheritance dedup (independence axis 1).
- *Behaviour:* a naive *count* sees 4 sources → over-confident; the group system collapses to **one origin
  group**. *Refutation:* "confidence is high because three sources corroborate — but they share one origin"
  (`spine/08 §2.2 #6`).
- *Build:* this is the realigned **d01** (defence-journal procurement tracker) — make the citation chain explicit.

**D4 · Aligned-interest false corroboration. ⚔ BYPASS(naive).** Two independent-bylined sources that
share a `bias_vector` (ISPR + Chinese state media — both **parties to the transfer**) both assert the same
capability/holding.
- *Signal:* the two sources are identifiable as operator-state and exporter-state respectively.
- *Ground truth:* `bias_vector` aligned (both interested parties).
- *Detector:* interest-independence axis. "Two aligned-interest sources are **not** cross-interest
  corroboration however independent their bylines."
- *Behaviour:* naive count sees 2 independent → confirmed; the 3-axis test refuses → stays **probable**
  until a *third-party / non-aligned* source appears. *Refutation:* demand cross-interest.
- *Build:* a new signal pair (ISPR statement + Global Times item) asserting the same range/holding.

**D5 · Adversary denial / fake-second-source claim. ⚔ BYPASS(naive).** A planted claim that *asserts*
corroboration ("a second, independent source confirms the battery at X") or *denies* a known dependency.
- *Signal:* the claim asserts a second source that is never itself resolvable; source is an
  interested/adversary channel.
- *Ground truth:* `adversary_denial_flag = true`.
- *Detector:* **adversary_denial is a GATE, not a multiplier** — discounted *before* it enters a group.
- *Behaviour:* naive count treats it as corroboration/downgrade; the gate makes it "neither corroborate
  nor downgrade." *Refutation:* discard the unresolvable second-source assertion.
- *Build:* `05 §5.1` seed — one adversary-denial doc.

**D6 · Decoy / single-pass imagery cap.** A single satellite pass matches a site signature that could be a
decoy/inflatable.
- *Signal:* single pass, signature-only, no repeat, no second discipline.
- *Ground truth:* `decoy_risk_flag = true`.
- *Detector:* decoy cap → **probable** (criterion 5/7).
- *Behaviour:* cannot confirm on one pass; needs a discipline-independent confirm (repeat pass / ELINT).
  *Refutation:* the cap itself. **This is the engine of the observable's probable step (§6).**

**D7 · Front-company / dual-use relabelling.** A customs BoL where a shell/forwarder consignee and a bland
HS description hide the military end-user; a declared-civil-vs-invoice-line contradiction sits unresolved.
- *Signal:* shell consignee + HS 8526 "radar apparatus parts" + a line-item/annex that implies the SAM
  radar; the civil vs military tension is *present but not resolved in the doc* (P6).
- *Ground truth:* `front_company`, `dual_use_relabel`.
- *Detector:* resolution (the shell connects to the end-user only via **relational** match, not string) +
  subject-proximity soft filter. (Front-company *detection* is roadmap; the corpus seeds it as a
  **resolution challenge**.)
- *Behaviour:* the shell is off-subject until resolution links it — the "grain the analysis exists to
  find" (`spine/02`). *Refutation:* relational resolution surfaces it; the contradiction routes to HITL.
- *Build:* fix **d05** per `M-DATA-1` (strip the in-line cover-story resolution).

**D8 · Supersede-spoof. ⚔⚔ BYPASS(current design) + FIX.** The marquee counter-deception item. An
adversary plants a **fresh-dated, single-source, low-credibility** relocation report to make a false
position *supersede* a confirmed one — **routing around the contradiction flag**, because `supersedes`
keys on `event_time` with **no confidence floor** (`H-DEFENSIBILITY-1`, verbatim).
- *Signal:* a 2025-dated single low-cred claim ("unit has left Rahwali, now at <false site>") that, by
  date alone, would retire a confirmed `based-at`.
- *Ground truth:* single-source, below-floor, fresh-dated; **this is the attack**.
- *Detector (current):* **NONE** — the spoof succeeds against the current spec. That's the point.
- *FIX (ship it):* add a **confidence floor to `supersedes`** — *a superseding claim must clear ≥1
  independent probable-grade look before retiring a confirmed assertion.* With the fix, the spoof is held
  as a **candidate-supersede → contradiction → HITL**, not an auto-overwrite.
- *Demo:* run it once **without** the floor (system wrongly relocates the unit), once **with** (held for
  the analyst). "Here's the attack; here's the one-line patch." This is the strongest thing on the call.

**D9 · Contradiction (same valid_time).** Two credible-looking sources disagree at the same
`event_time` about the same resolved entity×edge-instance.
- *Signal:* same site/date, opposite polarity/value; both plausibly sourced.
- *Ground truth:* `contradicts`.
- *Detector:* contradiction status (not supersession — dates equal) → flagged, routed to HITL.
- *Behaviour:* **not** auto-resolved. *Refutation:* HITL adjudication. *Have:* d08 vs d09 (formalize as
  same-`event_time`).

**D10 · Stale-as-current.** A dated fact printed in a recent document as if current (NTI chronology; CSIS
"last imaged 2016").
- *Signal:* `report_time` recent, `event_time`/`valid_time` old; hedged.
- *Ground truth:* stale.
- *Detector:* freshness decay `eff = conf × 2^(−age/half_life)` → below floor → **stale → demote**.
- *Behaviour:* "confirmed-as-of-2016 → probable(stale)". *Refutation:* the decay. *Have:* d14.

**D11 · Withheld signal / absence-as-evidence.** The expected corroborating indicator is conspicuously
absent — or a negative-polarity observation ("imagery of site S on date D shows **no** TELs").
- *Signal:* a sufficiency-template slot with no supporting claim; or an explicit negative observation.
- *Ground truth:* structured absence (negative-polarity claim).
- *Detector:* absence-as-evidence / evidence-requirement template → insufficient-evidence with
  `missing_slots` + `next_coverage_due`.
- *Behaviour:* returns **"insufficient evidence to assess"**, names what's missing. *Refutation:* the
  Known Gap node. *Build:* one negative-polarity imagery-caption doc + one "no sustainment activity where
  induction would show it" gap.

### Deception operator → detector → outcome (summary)

| Op | Detector (spine/04·08) | Naive outcome | Correct outcome |
|---|---|---|---|
| D1 recycled | M4 first_seen×caption | boosts | m collapses → ≤ probable |
| D2 echo burst | coordination + origin-group | 6 sources → confirmed | 1 group + too-clean → no boost |
| D3 aggregator ⚔ | aggregator-inheritance | 4 sources → confirmed | 1 origin group |
| D4 aligned-interest ⚔ | interest axis | 2 sources → confirmed | probable (no cross-interest) |
| D5 adversary-denial ⚔ | GATE | corroborates/downgrades | discounted (neither) |
| D6 decoy single-pass | decoy cap | confirmed | probable until 2nd discipline |
| D7 front-company | relational resolution | off-subject/dropped | surfaced via resolution |
| D8 supersede-spoof ⚔⚔ | **none → add floor** | **wrongly relocates** | candidate-supersede → HITL |
| D9 contradiction | contradiction status | auto-picks one | flagged → HITL |
| D10 stale | freshness decay | stays confirmed | stale → demote |
| D11 withheld | absence template | silent | insufficient-evidence |

---

## 5. Corroboration / refutability test design (per-node)

The corroboration layer is only "shown" if each node forces a *computed* discrimination. Rule: **every
material node/edge gets ≥1 testable path and ≥1 refutable element.** Using the 08-canonical math
(`c = R × Π(integrity) × model_conf`; `conf = 1 − Π_g(1−c_g)`, `c_g` = max in independence group;
`eff = conf × 2^(−age/half_life)`; confirmed ≥ 0.80, probable 0.50–0.80, possible < 0.50):

| Node / edge | Testable (corroborating) | Refutable element | Computed outcome |
|---|---|---|---|
| Import (China→PK HQ-9/P) | SIPRI register + ISPR + Quwa, cross-interest after D4 handled | D4 aligned-interest pair alone | **confirmed** (once a third-party source lands) |
| Induction → PA unit | ISPR (official) + Quwa | single-source spares tender (D-implication) | **confirmed** (multi) vs spares alone → **probable** |
| Basing @ Karachi | imagery-caption + social sighting | D6 decoy single-pass; D9 contradiction (routine-vs-sighting) | **probable** → **confirmed** on 2nd discipline |
| **Relocation Rawalpindi→Rahwali** | 2021 imagery (confirmed) + 2025 pass ×2 (independent) | D6 decoy cap; **D8 supersede-spoof** | **the observable** (see §6) |
| HT-233 chokepoint | supplies-component edge on critical path | **no naming indicator** (`M-INCONSIST-1`) | **CANDIDATE** chokepoint + `substitutability:UNKNOWN` + Known Gap |
| Deep-tier supplier | one named tier-2/3 source | rest are candidates | one confirmed edge, rest candidate |
| Any distractor entity | — | off-subject, low-cred | sinks below floor / off-canvas |

The **bypass suite** (D3, D4, D5, D8) is the explicit "manufacture data that bypasses corroboration"
deliverable: each is data a naive counter would accept; three are caught by the 3-axis independence + gate
design; the fourth (D8) is caught only after the confidence-floor fix — which is the headline.

---

## 6. Corpus composition & the observable realignment (→ ~40–50 docs)

**Operative target (`09 §0`):** ~40–50 docs, **S≈20 signal / N≈20–30 chaff**, built in two batches.
Signal does not grow; chaff does. Assessed view ~15–30 entities via the relevance funnel.

### 6a. Realign the frozen 14 first (fix the audit gaps)
1. **Relocation seed (`H-CONSIST-2`):** add `site_rawalpindi` (occupied@2021, confirmed), retarget the
   orphan `site_second → site_rahwali`, seed the 3-doc thread (below), add `supersedes`, set
   `observable.primary = basing_relocation`.
2. **Worked-query path (`H-CONSIST-1`):** rewire `answer_key.expected_path` so every consecutive hop is
   edge-connected (`based-at → inducted-into → imported-by → supplies-component/manufactures → chokepoint`);
   add an acceptance check.
3. **Flagship merge (`H-CONSIST-3`):** lock **HQ-9/P vs HQ-9BE** as the `distinct-from`; add `same-as`
   (FD-2000 → HQ-9/P); either seed FT-2000 in one doc or drop it from the flex; rewrite `alias_merge_trap`.
4. **Chokepoint (`M-INCONSIST-1`):** HT-233 = `chokepoint:'candidate'` + `substitutability:'UNKNOWN'` + Known Gap.
5. **Imagery posture (`H-DEVIATION-1`):** imagery enters as **analyst-report TEXT**; M4 = coordinated-
   inauthenticity + first-seen from text+timestamps; strip d11's verdict line; VLM/EXIF/reverse-image = roadmap.
6. **d05 (`M-DATA-1`):** strip the in-line cover-story resolution (D7).
7. **Type-string cleanup (`L-CONSIST-1`):** fix off-ontology strings (`radar_command_node` etc.); add the
   missing `official_routine_framing` manifest row.

### 6b. The observable thread (the locked tripwire — 3 signal docs)
- **R1 — 2021 baseline:** analyst-report imagery text: *occupied @ Rawalpindi*, HQ-9B fire-unit, confirmed,
  aging under garrison half-life.
- **R2 — 2025 single pass:** imagery text: *occupied @ Rahwali*, single pass, signature-only → **probable**
  (D6 decoy cap).
- **R3 — 2025 second signal:** discipline-independent + cross-interest confirm (repeat pass OR ELINT
  emitter-active OR non-aligned statement), clean decoy check → **confirmed**; `supersedes` retires
  Rawalpindi → **stale**. Matched on resolved unit×site instance, never designator.
- **R4 — the spoof (D8):** a fresh-dated single low-cred "unit left Rahwali" report → demonstrate the
  bypass and the confidence-floor fix.

### 6c. Batch-1 net-new signal (~+6, → S≈20)
relocation thread R1–R3 (+R4 as planted); deep-tier supplier **or** Tech-Data Authority (1–2, §9 OPEN);
aligned-interest pair (D4); adversary-denial (D5); withheld-signal/gap (D11); aggregator realigned d01 (D3).

### 6d. Batch-2 chaff (~+20–26 → N≈20–30) — mechanism-first (`09 §4`)
| Class | Mechanism | Count | Content |
|---|---|---|---|
| **Echoes (D2)** | coordination collapse | +2–4 | extend the burst to 4–6 near-dup posts |
| **Distractors** | proximity + credibility floor | +8–12 | other SAMs (S-400 China, HQ-16/LY-80), other countries, civilian trade, unrelated NOTAMs, **coincidental entity collisions** (a second unrelated "Factory 404" / "Unit 106" the resolver must **keep separate**) |
| **Stale (D10)** | freshness decay | +3–5 | dated-as-current reference/media |
| **Supersede-spoof (D8)** | the bypass | +1–2 | planted fresh-dated false relocation |

> **Legibility caveat (load-bearing, `09 §5/§0`):** at 40–50 docs the assessed-view legibility guarantee
> becomes **conditional on the subject-proximity view-time filter**, which is *not yet a scheduled build
> stage*. Generating the chaff is a data step (my job); **the proximity + credibility funnel must actually
> exist to keep the canvas legible** (their build path). I construct distractors to be *low-proximity by
> design* so they sink via credibility even before the filter is built — but this **promotes the proximity
> filter to a required build item** (flagged in `11-...` and to feed the build ladder).
> **Chokepoint-topology caveat:** no distractor may introduce a second supplier path for HT-233 (it would
> flip the marquee chokepoint finding). Check every sustainment-touching doc against the cached hero trace
> before freezing.

---

## 7. Reuse for A and B (same engine, config only)

The engine is use-case-agnostic because the **unit (claim)**, the **sidecars** (independence + bi-temporal
stamps + expected-behaviour oracle), and the **operator families** are shared. What each adds is *config +
claim-types*, not code (`spine/08 §2` — the six pre-wirings are paid now):

- **B (escalation / intent):** reuses corruption + **all** deception operators directly (deception *is* B's
  threat model). Adds: event-typed claims (`{event_type, interval, participants}`), **inference claims**
  (`kind:inference, premises:[...]` — the ACH substrate), **diagnostic-indicator** asserts (comms-blackout,
  blood-bank, EMCON), and a `templates.yaml` for MLCOA/MDCOA. The withheld-signal op (D11) and the
  aligned-interest/adversary-denial ops (D4/D5) are *especially* B-relevant. **No engine change.**
- **A (air-posture / surge):** reuses corruption + D2/D6/D10 (echoes, decoy, stale). Adds the one thing C
  doesn't need: a **longitudinal baseline** — repeated `event_time`-stamped observation claims across a
  window so a surge scores as a deviation. The generator emits a *time-series of claims per location*
  (a new scenario spec shape: `baseline_window`, `cadence`, `surge_injection`), not new engine code.
  *(No baseline-window/threshold constants exist in the docs yet — flagged in `11-...`.)*

Concretely, the reusable generator adds two config files: **`operators.yaml`** (the §3+§4 catalogue) and a
**`scenario/*.yaml`** shape that already carries `documents[]`; A adds `baseline[]`, B adds
`events[]`+`inferences[]`. That's the whole extension surface.

---

## 8. Verification protocol (each unit demonstrates its mechanism — P5)

Every doc is verified on three axes before it's "frozen":
1. **Extraction P/R** — does the pipeline extract the ground-truth claim(s) from the raw text? (score vs `answer_key`.)
2. **Operator audit** — did the intended corruption/deception operators actually land? (recorded in manifest.)
3. **Downstream behaviour** — does the *credibility resolver* produce the expected outcome?
   - echoes actually collapse to one origin group (no boost);
   - distractors actually sink below the confidence floor / fall off subject-proximity;
   - stale actually decays past the freshness floor;
   - the observable actually fires (probable → confirmed → supersede→stale);
   - **the bypass suite:** D3/D4/D5 are caught by the 3-axis test; D8 succeeds without the floor and is
     held with it (both runs recorded).

Adversarial check (ultracode): a red-team pass tries to make each planted item *un-earned* (detectable only
from the hidden flag, not the text) — any such doc is regenerated per P2.

---

## 9. What's built vs what needs you

Built autonomously (this session): the operator taxonomies (§3, §4), the realignment plan (§6a), the
observable thread + spoof design (§6b), the corpus map (§6c/d), the reuse contract (§7), and the tooling +
generated corpus at volume (see the session summary + `tools/`). **Decisions/logins that need you** are in
[`11-data-requirements-from-pragalbh.md`](11-data-requirements-from-pragalbh.md) — headline items:
imagery posture sign-off, the one sustainment node to build (Interceptor Stockpile vs Tech-Data Authority),
cross-interest scope, calibration-constant sign-off, and the credential/login list (Copernicus, Google
Earth, SIPRI export, X, residential-IP run) that upgrades reconstructions to raw real sources.
