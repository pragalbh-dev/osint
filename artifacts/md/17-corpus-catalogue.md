# 17 — Corpus catalogue (what every generated doc is, and why)

Full per-document walkthrough of the frozen corpus: **51 docs** = **24 signal** (`hq9p_primary`) +
**27 chaff** (`hq9p_chaff`), **12 images**. Generated from real templates, entities varied synthetically
(generator blind to the ontology). This is the map from raw doc → what the pipeline must do with it.

## How to read the two "source" columns

- **Doc type** = `source_class` — the *kind of artifact* the pipeline ingests (what it looks like).
- **KG source** = the ground-truth `registry` the pipeline must **compute** from the raw text (never in the
  doc): `primary_origin_id` (who really originated it), `reliability_grade` (STANAG A–F), `bias_vector`
  (third-party / operator-state / exporter-state / commercial / adversary), plus flags (aggregator_of,
  first_seen, coordinated_inauthenticity, adversary_denial, decoy_risk).

## Class legend (real vs planted)

Every doc is *synthetic-from-real-template*. The distinction that matters is what its **content** is:

- **TRUE-SIGNAL** — accurate claim that *should* build the graph (may carry benign messiness).
- **TRUE + DECEPTION-WRAP** — the underlying fact is true, but it's packaged so a *naive* system
  mis-counts it (aggregator, aligned-interest). The fact is real; the trap is in the provenance.
- **DECEPTION / MISINFO** — the claim itself is false/misleading (recycled image, false attribution,
  supersede spoof, adversary denial, same-time contradiction).
- **GAP** — models absent/insufficient evidence (cloud, negative observation).
- **DISTRACTOR** — realistic doc about *something else*; tests triage/proximity (chaff).
- **STALE** — true-but-old, recirculated as current; tests freshness (chaff).

---

## SIGNAL corpus — `hq9p_primary` (24 docs)

| # | Doc | Type | KG source (grade/bias) | What info it carries | Class → how | Demo / pipeline value |
|---|---|---|---|---|---|---|
| d01 | sipri_transfer | arms_transfer | SIPRI (B / third-party), aggregator_of[2 outlets] | China (CASIC/CPMIEC) supplied HQ-9/P to Pakistan, inducted 2021 | **TRUE + WRAP** — `aggregator_circular` (D3): "3 outlets, all citing SIPRI" | Aggregator-inheritance dedup: 4 apparent sources → **1 origin group**; naive count over-confident |
| d02 | ispr_induction | official | ISPR (B / operator-state) | HQ-9/P inducted into Army AD regt 2021-10-14 at Karachi; HIMADS; range >100 km | **TRUE-SIGNAL** (interested party) | Official-but-interested; anchors the corroboration cluster; "Karachi" = ambiguous parent-city (location demo) |
| d03 | quwa_analysis | trade_media | quwa (C / third-party) | Corroborates induction; calls the system **FD-2000** | **TRUE-SIGNAL** | Alias auto-merge **FD-2000 ≡ HQ-9/P**; the third-party look that *can* lift to confirmed |
| d04 | armyrec_ranges | trade_media | (C / third-party) | HQ-9/P (Army ~125 km) vs **HQ-9BE** (PAF ~260 km); mentions **FT-2000** | **TRUE-SIGNAL** | Flagship **distinct-from** (HQ-9/P ≠ HQ-9BE); **FT-2000 ≠ HQ-9/P** → HITL band, do NOT merge |
| d15 | globaltimes_aligned | trade_media | globaltimes (C / exporter-state) | Chinese state media asserts the *same* holding as ISPR | **TRUE + WRAP** — `aligned_interest` (D4) | Interest-independence axis: ISPR + Chinese state = both parties → stays **PROBABLE**, not confirmed |
| d05 | customs_manifest | customs | customs_bol (C / commercial) | Shell consignee imports "radar apparatus parts" (HS 8526) implying HT-233; port = **Port Muhammad Bin Qasim / Bin Qasim / PQ** | **DECEPTION** — `front_company` (D7) | Relational (not string) resolution shell → HT-233; port **distinct-from** trap (Qasim ≠ Karachi Port); location normalization |
| d21 | techdata_authority | trade_media | (C / third-party) | Software/calibration for the engagement radar controlled by a Chinese technical-data authority | **TRUE-SIGNAL** (single) | The **invisible dependency** chokepoint (`design-authority-for`, probable) |
| d22 | deep_tier_supplier | reference | casi_2025 (B / third-party) | HT-233 maker **UNKNOWN**; CPMIEC = export agent NOT maker; candidate = **23rd RI/BIRM** (Yongding Rd, Haidian, Beijing); deeper tiers = gaps | **TRUE-SIGNAL** (authoritative) | The honest deep-tier → **Known Gap**; district-level location; **contradicts d23** |
| d23 | cpmiec_false_attribution | trade_media | blog_cpmiec_mfr (D / commercial) | "CPMIEC manufactures the HT-233" (conflates export agent with maker) | **MISINFO** — `aggregator_circular` (false attribution) | Low-cred conflation must NOT create a confirmed edge; refuted by d22; export-agent ≠ maker |
| d06 | spares_tender | procurement | dgdp_tender (C / operator-state) | A spares/sustenance tender *implies* an already-inducted SAM | **TRUE-SIGNAL** (single, inference) | **Single source → stays PROBABLE**; tender implies, never confirms; an *inference* claim |
| d07 | sat_confirm_karachi | imagery + **IMG** | (B / third-party, decoy=false) | Petal/ring SAM pad + TEL revetments at Malir, Karachi; DD `24.9012N 67.2034E`; multi-pass | **TRUE-SIGNAL** | **Worked-query anchor**; imagery confirm of basing; the **hero frame** (real Esri, Xi'an relabeled); DD location |
| d08 | social_sighting | social + **IMG** | (D / third-party) | Post claims active HQ-9 convoy movement near Karachi 2025-05-09 | **DECEPTION** — `contradiction_same_time` (D9) vs d09 | Same site+date opposite claim → **CONTRADICTED → HITL**; fabricated convoy image |
| d09 | official_routine | official | (B / operator-state) | Official frames the same 2025-05-09 activity as "routine training" | **DECEPTION-half** — `contradiction_same_time` | The other half of the contradiction → HITL, not auto-resolved |
| d10 | sat_cloud_gap | imagery + **IMG** | (B / third-party) | ~95% cloud over the site 2025-05-10 — cannot confirm launcher count | **GAP** | **Insufficient-evidence**: names missing slot + next coverage due; low-res Sentinel is deliberately the point |
| d17b | withheld_gap | imagery + **IMG** | (B / third-party) | Imagery of a forward site shows **NO TELs** (negative observation) | **GAP** — `withheld_signal` (D11) | **Absence-as-evidence → Known Gap**; the empty-petal frame (real Esri, Lanzhou) |
| d11 | recycled_image | social + **IMG** | (D / third-party), first_seen 2019, origin_parade_img | 2019 parade photo presented as a NEW 2025 Rahwali deployment | **DECEPTION** — `recycled_media` (D1) | **M4 first_seen × caption** → integrity collapses; cannot confirm |
| d12 | reshare_a | social + **IMG** | (E / third-party), origin_parade_img, coord-inauth | Near-identical reshare of d11, new handle, minutes later | **DECEPTION** — `echo_burst` (D2) | Collapses into d11 origin group; **no corroboration boost** |
| d13 | reshare_b | social + **IMG** | (E / third-party), origin_parade_img, coord-inauth | 2nd reshare, same burst window | **DECEPTION** — `echo_burst` (D2) | **Too-clean penalty** on the coordinated cluster |
| d14 | stale_holding | reference | (C / third-party) | A China HQ-9 holding sourced only to 2016 imagery, printed as current | **STALE** — `stale_as_current` (D10) | Freshness decay → confirmed-as-of-2016 → **probable(stale)** |
| d16 | adversary_denial | official | (D / **adversary**), adversary_denial_flag | "A 2nd source confirms HT-233 fully indigenised" (none shown) + denies the techdata dependency | **DECEPTION** — `adversary_denial` (D5) | **GATE**: excluded before grouping; neither corroborates nor downgrades; caps at probable |
| d17 | rawalpindi_2021 | imagery + **IMG** | (B / third-party) | HQ-9B occupied at **Nur Khan (fmr Chaklala)**, 2021; **MGRS 43S CT 23715 21242**; multi-source | **TRUE-SIGNAL** | Relocation **baseline** (confirmed); MGRS + **renamed-base alias** (Chaklala withheld → earned merge); real Esri (Nanjing) |
| d18 | rahwali_pass1 | imagery + **IMG** | (B / third-party), decoy_risk=true | **SINGLE** 2025 pass, HQ-9B signature at Rahwali; **DMS 32°14′20″N 074°07′52″E**; single pass only | **DECEPTION-adjacent** — `decoy_single_pass` (D6) | **Decoy cap → PROBABLE**; DMS location (must unify with d19); real Esri (Crimea, ambiguous — fits probable) |
| d19 | rahwali_confirm | reference | (B / third-party) | Discipline-independent/ELINT confirms HQ-9B at **Rahwali Cantt, ~10 km NW of Gujranwala**; clean decoy check | **TRUE-SIGNAL** | 2nd independent → **CONFIRMED**; `supersedes` retires Rawalpindi → stale; toponym+relative location (unifies w/ d18) |
| d20 | supersede_spoof | social | (E / **adversary**), decoy_risk=true | Fresh 2025-06 single low-cred post: the unit has **LEFT Rahwali** for a different site | **MISINFO** — `supersede_spoof` (D8 ⚔⚔) | **The counter-deception headline**: no floor → wrongly relocates; with floor → candidate-supersede → HITL |

**Deception bypass suite** (engineered to beat a *naive* corroboration count): d01 (D3), d15 (D4),
d16 (D5), d20 (D8). D8 beats even our current design and ships with its fix (confidence-floor on `supersedes`).

---

## CHAFF corpus — `hq9p_chaff` (27 docs) — the triage funnel

| # | Doc | Type | KG source (grade/bias) | What it is | Class → how | Demo / pipeline value |
|---|---|---|---|---|---|---|
| ce01 | reshare_c | social + **IMG** | (E), origin_parade_img | 3rd reshare of the recycled parade image | **DECEPTION** — echo_burst | Extends the burst to 6 posts → **one look**; the "grain in chaff" |
| ce02 | reshare_d | social + **IMG** | (E), origin_parade_img | 4th reshare | **DECEPTION** — echo_burst | Coordination penalty |
| ce03 | reshare_e | social + **IMG** | (E), origin_parade_img | 5th reshare (quote-tweet chain, next day) | **DECEPTION** — echo_burst | 6-post burst (d11-13+ce01-03) = ONE origin group |
| cd01 | s400_china | trade_media | (C / third-party) | China S-400 article | **DISTRACTOR** | S-400 aliases must NOT resolve into HQ-9/P; sinks on proximity |
| cd02 | india_s400 | official | (B / operator-state) | India S-400 induction | **DISTRACTOR** | Wrong country/operator; must not attach to the PK graph |
| cd03 | pak_hq16 | trade_media | (C / third-party) | Pakistan **HQ-16** (LOMADS) | **DISTRACTOR** (hardest) | High proximity, different system → distinct-from |
| cd04 | civ_electronics | customs | (C / commercial) | Civilian electronics, **same HS 8526** as d05 | **DISTRACTOR** | HS-code collision must NOT pull it into the supply chain |
| cd05 | civ_notam | nav_warning | (A / third-party) | Civilian NOTAM | **DISTRACTOR** | High reliability, **zero materiality** → no claim extracted |
| cd06 | entity_collision_factory | reference | (C / third-party) | A name-similar factory | **DISTRACTOR** | Entity-collision → resolver keep-separate (distinct-from) |
| cd07 | unit_collision | reference | (C / third-party) | A designator-string collision (off-subject) | **DISTRACTOR** | Identity resolution, not string; the doc itself isn't about HQ-9 |
| cd08 | turkey_sam | trade_media | (C / third-party) | Turkey SAM program | **DISTRACTOR** | Off-subject; sinks on proximity |
| cd09 | generic_iads | reference | (B / third-party) | Generic IADS backgrounder | **DISTRACTOR** | Tangential; no material claim |
| cd10 | rumor_test | social | (E / third-party) | Low-cred rumor | **DISTRACTOR** | Low-cred + off-subject → sinks below the floor |
| cd11 | drone_deal | trade_media | (C / third-party) | A drone acquisition | **DISTRACTOR** | Off-subject trade noise |
| cs01 | stale_orbat | reference | (C / third-party) | A **2015** HQ-9 ORBAT recirculated as current | **STALE** | Decays → stale; must not stand as a current holding |
| cs02 | stale_deployment | trade_media | (C / third-party) | A **2018** deployment resurfacing in 2025 | **STALE** | Old event, recent recirculation → stale |
| cs03 | stale_customs | customs | (C / commercial) | A **2017** shipment in a recent compilation | **STALE** | Old shipment → not a current supply signal |
| cx01 | spoof_karachi | social | (E / **adversary**), decoy_risk=true | Fresh single low-cred post: HQ-9/P has LEFT Karachi | **MISINFO** — supersede_spoof (D8 #2) | 2nd D8 instance vs the Karachi confirmed basing → floor holds it as candidate → HITL |
| cd12 | turkey_s400 | trade_media | (C / third-party) | Turkey S-400 | **DISTRACTOR** | S-400 aliases must not resolve in |
| cd13 | saudi_patriot | trade_media | (C / third-party) | Saudi Patriot | **DISTRACTOR** | Off-subject; sinks on proximity |
| cd14 | china_hq22 | trade_media | (C / third-party) | China **HQ-22** (same maker, adjacent system) | **DISTRACTOR** | Same-manufacturer adjacent system → distinct-from; proximity decoy |
| cd15 | civ_container | customs | (C / commercial) | Civilian container manifest | **DISTRACTOR** | No ontology-typed claim |
| cd16 | pak_civ_notam | nav_warning | (A / third-party) | Pakistan civil NOTAM | **DISTRACTOR** | Right country, zero materiality → no claim |
| cd17 | academic_radar | reference | (B / third-party) | Academic radar paper | **DISTRACTOR** | Tangential; no material claim |
| cd18 | forwarder_collision | customs | (C / commercial) | Name-similar freight forwarder, civilian cargo | **DISTRACTOR** | Keep-separate; do not attach to the supply chain |
| cd19 | rumor_missile | social | (E / third-party) | Low-cred missile rumor | **DISTRACTOR** | Low-cred off-subject → sinks below floor |
| cd20 | defense_budget | trade_media | (C / operator-state) | Defense budget piece | **DISTRACTOR** | Right country, no material HQ-9 claim → tangential |

---

## The graph this builds (answer-key ground truth)

**18 nodes** (manufacturer/component/variant/unit/basing_site/sustainment/known_gap/import_event) ·
**23 edges** · **7 place nodes** (gazetteer). Worked query: *"Trace the HQ-9/P battery at Karachi back
to its component supplier and name the chokepoint"* → path `site_karachi → unit_paad → var_hq9p →
comp_ht233 → mfr_casic`, answer = **HT-233 = CANDIDATE chokepoint** (maker a Known Gap). Observable =
the HQ-9B **Rawalpindi→Rahwali** relocation (seed docs d17→d18→d19→d20).

## Coverage of the 6 required graded scenarios

1. corroborated → d01/d02/d03 · 2. single-source → d06 · 3. contradiction → d08/d09 ·
4. too-clean/planted → d11-13+ce01-03 · 5. gap/insufficient → d10/d17b · 6. entity-resolution HITL trap
→ d04 (FT-2000) + cd06/cd07/cd18 collisions. **All six present.** Plus the observable, freshness (d14/cs*),
the deception bypass suite (D3/D4/D5/D8), and location normalization (d05/d07/d17/d18/d19/d22).

---

## What's missing (honest gap list)

> **Dispositions (2026-07-18):** #1 explained (candidate to build, see below) · **#2, #3 → TBD/deferred** ·
> **#4 → ACCEPTED** (verbatim real docs not needed; format-fidelity = messy-and-real-looking is the
> requirement, and the templates already deliver that) · **#5 → in verification** (chaff adversarial
> subagent) · **#6 → logged** to `md/16-design-note-disclosures.md` for the design-note agent · #7 →
> pending your decision · #8 → roadmap (A/B by specification).

**Data-side gaps:**
1. **No claim-level extraction gold.** The oracle is doc-level (`asserts` + `expect`); there's no per-claim
   `(subject,predicate,object)` gold list, so extraction precision/recall can't be scored exactly. `asserts`
   is close but not a strict tuple set.
2. **Only one subject/scenario frozen.** Strategy calls for *multiple* scenarios an evaluator picks live;
   we have one subject (HQ-9/P) as signal+chaff. A second independent scenario isn't frozen.
3. **Only one fully-threaded observable.** The relocation has a 4-doc trigger thread; the secondary
   (sustainment tender → probable induction) is config-only (just d06), not a full thread.
4. **No verbatim real seed docs.** All text is synthetic-from-template; the strategy wants a few *real,
   uncurated* documents dropped in. (Imagery IS real — Sentinel/Esri; text is not.) `gather.py` exists;
   the corpus doesn't yet embed real specimens.
5. **Chaff not fully LLM-verified.** The distractor batch was phrase-scanned, not put through the full
   adversarial verifier (low risk — plain distractors have no deception to earn).
6. **Imagery text↔image is relabeled.** d07/d17/d18 text carries Pakistan coords while the frame is a
   real foreign SAM site relabeled (documented in the answer key) — the demo narrative must own this.
7. **Fabricated "leaked high-res" deception item** — proposed (a synthetic SAM overhead the system must
   refuse to confirm on), not built.
8. **No A/B-layer data** — no longitudinal baseline (A) or intent/inference + indicator-battery (B)
   scenario data. By design (roadmap); the engine pre-wires events/inferences for it.
9. **VLM extraction-confidence** held at 1.0 — no low-confidence VLM reads modeled (design-note seam).

**Pipeline-side (not data — the system that consumes this isn't built yet):**
10. Ingest/extract → claims · resolution/`rebuild()` · credibility+status machine · observable evaluator
    (`observe/`) + alert-disposition HITL · the ReAct QnA agent + citation validator · the review-queue UI ·
    the map/graph viz. **The data is frozen and ready; the system that reads it is the build.**
11. **Calibration** — thresholds / weights / half-lives are coarse defaults, uncalibrated on this corpus.
12. **Location-normalization runtime** — the gazetteer + oracle exist (`config/places.yaml`, `md/13`); the
    coordinate-canonicaliser + place-resolution code is a build task.
