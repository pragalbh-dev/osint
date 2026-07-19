# Phase-1 Entity Registry — Draft (HQ-9/P scenario)

Status: DRAFT for review. Gathering/bucketing only — no config edited, no code touched.

Sources consulted (in order): `corpus/scenarios/hq9p_primary/answer_key.json` (ground_truth skeleton),
`tmp/conv/eval-rca/00-evidence-summary.md` (fragmentation heuristic), `tmp/conv/eval-rca/view_full.json`
(all 294 raw view nodes + 101 edges, read in full — not just the heuristic's matches),
`corpus/scenarios/hq9p_primary/claims/*.json` (per-claim payloads for disambiguation), raw docs under
`corpus/scenarios/hq9p_primary/docs/*.txt` (read where a claim/node string needed sentence-level context),
`config/resolution.yaml` (seeded alias_table), `config/places.yaml` (gazetteer pattern + place entries).

Every alias below is tagged with its evidence: a claim_id / doc id (corpus), "view fragment" (a raw
`ent:type:name` or bare-string node in `view_full.json` with no corresponding claim citation checked
individually), or "config seed" (`resolution.yaml`/`places.yaml`).

Where the evidence-summary's type-matching heuristic proposed a fragment, I re-verified it against the
underlying claim/doc text rather than trusting the heuristic outright — several of its candidates turned
out to be **mis-bucketed** or **not aliases at all** (sub-components, evidence-for-a-relationship, or
off-subject noise). Those corrections are called out inline and in §3.

---

## 1. Confirmed registry entries

### 1.1 Manufacturers

#### `mfr_casic` | manufacturer | CASIC (2nd Academy / China Academy of Defence Technology / CCFG)
Oracle name: "CASIC — HQ-9 design authority = 2nd Academy / China Academy of Defence Technology / China
Changfeng Group (CCFG)." Per `places.yaml`, `pl_casic_2nd` (the 2nd Academy campus) is `used_by: mfr_casic`
— i.e. the oracle treats "2nd Academy / CCFG" as CASIC's own HQ-9 design-authority identity, not a separate
manufacturer. That reading is load-bearing for the aliases below.

- "CASIC" — confirmed, view fragment `ent:manufacturer:CASIC` (also bare `CASIC` under the mistyped
  `unknown` bucket); claims across d01, d03, d04, d14, d15, d19, d21, d23, d24, d25.
- "China Aerospace Science and Industry Corporation" — confirmed, view fragment
  `ent:manufacturer:China Aerospace Science and Industry Corporation`; same-as edge to CASIC already fires
  in-view (`China Aerospace Science and Industry Corporation -> CASIC`, status=confirmed) — d01, d04, d21.
- "CASIC's Second Academy" / "CASIC Second Academy" — confirmed alias of `mfr_casic` (not a separate
  entity), per `places.yaml` used_by + `resolution.yaml`'s own seeded canonical key. View fragment
  `ent:manufacturer:CASIC's Second Academy`, d22.
- "2nd Academy", "Second Academy" — config seed (`resolution.yaml`, `places.yaml`).
- "China Academy of Defense Technology" — config seed; not independently seen verbatim in a claim, but
  matches d22's institutional framing of the "Second Academy... systems lead on the HQ-9 line."
- "China Changfeng Group", "CCFG" — config seed only; not seen as a literal corpus surface form in any doc
  read (d01–d25). Carry the seed, but flag as **unattested in this corpus** (see §4).
- "航天科工二院" (Chinese, "CASIC Second Academy") — config seed (transliteration table) + view fragment
  `中国航天科工二院` (d22, same-as `CASIC's Second Academy`).
- "中国航天科工二院" — view fragment, d22-deep-tier-supplier-l18-6/7, same-as edge to "CASIC's Second Academy".

**Explicitly NOT an alias of `mfr_casic`:** CPMIEC and its variant spellings. The oracle's own field says
CPMIEC is CASIC's "export_agent (export/marketing only... NOT the manufacturer)". The view correctly keeps
CPMIEC un-merged with CASIC (no same-as edge between them was found), but CPMIEC has **no oracle
ground_truth id of its own** — see §4 for its full alias cluster and why that's a gap worth closing.

#### `mfr_23rd_ri` | manufacturer (status=possible) | CASIC 23rd Research Institute (BIRM)
- "Beijing Institute of Radio Measurement" — confirmed, view fragment
  `ent:manufacturer:Beijing Institute of Radio Measurement`, d22-deep-tier-supplier-l18-2; config seed.
- "BIRM" — config seed + view fragment (bare, under `unknown` bucket), d22.
- "23rd Research Institute" — view fragment (bare `23rd Research Institute`, under `unknown`), d24-tel-
  chassis-attribution-l23-2; config seed.
- "CASIC's 23rd Research Institute" — view fragment (bare, under `unknown`), d22-l18; same-as edge to
  "Beijing Institute of Radio Measurement" fires in-view.
- "23rd Institute" — config seed; not independently seen as a literal corpus string in docs read.
- "北京无线电测量研究所" (Chinese) — config seed + view fragment `北京无线电测量研究所`, d22-l18-4;
  same-as edge to "Beijing Institute of Radio Measurement" fires in-view.
- "中国航天科工四院" is NOT this entity — see `mfr_4th_academy` below; do not cross-wire the two Chinese
  strings, they attach to different institutes in the same-as edge list.

#### `mfr_4th_academy` | manufacturer (status=possible) | CASIC 4th Academy / ARMT
- "CASIC's 4th Academy" — confirmed, view fragment `ent:manufacturer:CASIC's 4th Academy`,
  d22-deep-tier-supplier-l24.
- "4th Academy" (bare) — implied by the above within d22's own text ("CASIC's 4th Academy... is CASIC's
  principal solid-rocket-motor house"); not separately extracted as its own node.
- "中国航天科工四院" (Chinese) — view fragment `中国航天科工四院`, d22-l24-2, same-as edge to
  "CASIC's 4th Academy" fires in-view.
- "Academy of Rocket Motors Technology" / "ARMT" — appear **only** in the oracle's own `name` field
  (answer_key.json), never as a literal string in any corpus doc read (d01–d25). Carry them as the oracle's
  official long-form name, but they are **not corpus-attested** — do not expect a resolver to ever see this
  string in the wild for this scenario.

#### `mfr_taian` | manufacturer (status=confirmed) | Taian / Wanshan special-vehicle works
- "Taian (Wanshan) special-vehicle works" — confirmed, view fragment
  `ent:manufacturer:Taian (Wanshan) special-vehicle works`, d24-tel-chassis-attribution-l13; oracle's own
  name field matches nearly verbatim.
- "Taian (Wanshan)" — confirmed, view fragment `ent:manufacturer:Taian (Wanshan)`, d25-hq9-site-
  fingerprint-l27-3.
- "Taian/Wanshan" — confirmed, view fragment (bare, under `unknown`), d24-l13-3; same-as edge
  "Taian (Wanshan) special-vehicle works -> Taian/Wanshan" fires in-view.
- "the Taian (Wanshan) special-vehicle works of the WS-series lineage" (d24 full phrase) — same entity,
  fuller quote for provenance.

---

### 1.2 Components

#### `comp_ht233` | component | HT-233 engagement radar
- "HT-233" (bare) — confirmed, view fragment `ent:component:HT-233` (status=confirmed in-view), claims
  across d14, d15, d17, d19, d24, d25.
- "HT-233 engagement radar" — confirmed, view fragment `ent:component:HT-233 engagement radar`, d22-deep-
  tier-supplier-l10, d24-tel-chassis-attribution-l21.
- "HT-233 phased-array engagement radar" — confirmed, view fragment
  `ent:component:HT-233 phased-array engagement radar`, d21-techdata-authority-l8-3, d23-cpmiec-false-
  attribution-l10.
- "HT-233 fire control radar" — confirmed, view fragment (bare, under `unknown`, status=possible), d16-
  adversary-denial-l15.
- "engagement/fire-control radar pallet" — confirmed (imagery description of the HT-233 hardstand item),
  view fragment `ent:component:engagement/fire-control radar pallet`, d18-rahwali-pass1-l20.
- "fire-control and guidance radar" — confirmed, **explicit in-text alias declaration**: d21 says the HT-233
  is "alternatively referenced in some Pakistani service literature simply as the 'fire-control and guidance
  radar'." View fragment (bare, under `unknown`), same-as edge to "HT-233 phased-array engagement radar"
  fires in-view.
- "30N6E 'Flap Lid'" is **NOT** an alias of comp_ht233 — it is the Russian S-300 analogue radar cited only
  for comparison in d21 ("analysts continue to compare [HT-233] to the Russian 30N6E 'Flap Lid' family").
  The view correctly keeps it as its own same-as pair (`30N6E -> Flap Lid`) without merging into HT-233.
  Flagging here only so nobody merges it later.

**Corrected out of the evidence-summary's FRAGMENTED-9 list (do NOT treat as comp_ht233 aliases):**
- "HT-233 (H-200) engagement radar array" — the H-200 portion is an **unverified candidate mapping**, not
  a confirmed alias; see §2. Do not seed this whole string as an alias.
- "Type 305B (HT-233 derivative)" and bare "Type 305B" — likewise unverified; see §2.
- "Battery/charging modules for engagement radar cabin" — a sub-component of the HT-233 cabin (a spares
  line item from d06), not another name for the radar itself. See §3.
- "engagement radar" (bare) — deliberately NOT bucketed here; see §3 (task's own flagged example).

#### `comp_interceptor` | component | HQ-9-family interceptor round
No confirmed proper-noun alias was found anywhere in the corpus. This entity is referenced only by generic
descriptive phrases, never by a distinct name:
- "the missile itself" (d21, describing the interceptor's two-stage guidance design) — descriptive only.
- "missile round" / "missile canister(s)" (d06 tender items (e) and (f)) — descriptive/packaging terms, not
  a name for the round.
- "the HQ-9A or the further-refined HQ-9P configuration" missile inventory (d01) — describes the round only
  by borrowing the *system* variant name, not a distinct interceptor-round name.

The evidence-summary's FRAGMENTED-2 candidates for this id ("Calibration/test jigs for missile round
check-out...", "Ground support vehicle spares for erector-launcher chassis") are **not aliases** — see §3;
the second one is actually about the TEL chassis, not the interceptor, and was mis-bucketed here by the
type+string heuristic.

**Bottom line: comp_interceptor has zero corpus-attested aliases.** This is a real coverage gap worth
surfacing to DATA/INGEST, not a bucketing failure on my part (see §4).

#### `comp_tel_chassis` | component | HQ-9/P TEL transporter-erector-launcher chassis (WS-series)
- "TEL (transporter-erector-launcher)" — confirmed, view fragment
  `ent:component:TEL (transporter-erector-launcher)`, d18-rahwali-pass1-l21.
- "transporter-erector-launcher" — confirmed, view fragment (bare, under `unknown` and under
  `ent:component:`), d25-hq9-site-fingerprint-l9-2; same-as edge "transporter-erector-launcher -> TEL"
  fires in-view.
- "transporter-erector-launcher (TEL)" — confirmed, view fragment
  `ent:component:transporter-erector-launcher (TEL)`, d07-sat-confirm-karachi-l13-2.
- "transporter-erector-launchers (TELs)" — confirmed, view fragment
  `ent:component:transporter-erector-launchers (TELs)`, d10-sat-cloud-gap-l14-2, d17b-withheld-gap-l22.
- "transporter erector launchers" (no hyphens) — confirmed, view fragment (bare, under `unknown`), d23-
  cpmiec-false-attribution-l12.
- "HQ-9/P TEL" — confirmed, view fragment `ent:component:HQ-9/P TEL`, d01-sipri-transfer-l12-2.
- "heavy 8x8 special wheeled chassis" — confirmed, view fragment
  `ent:component:heavy 8x8 special wheeled chassis`, d24-tel-chassis-attribution-l1/l13-2 (ASCII "x").
- "heavy 8×8 special wheeled chassis" — confirmed, view fragment (Unicode "×"),
  d25-hq9-site-fingerprint-l27/l27-2. Same entity as above, different multiplication-sign glyph — a
  literal Unicode-vs-ASCII fragmentation pair.
- "TAS5380" — confirmed, view fragment `ent:component:TAS5380`, d24-tel-chassis-attribution-l14. d24: "the
  WS-series chassis... variously rendered TAS5380 / WS2400-series in trade and vehicle-registry literature."
- "WS2400-series" — confirmed, view fragment `ent:component:WS2400-series`, d24-l14-2. Same d24 sentence
  as TAS5380, both explicitly glossed as alternate renderings of the same WS-series chassis product.
- "canisterized launchers" — confirmed with lower confidence; d17's "HQ-9/HQ-9B canisterized launchers"
  describes the visible TEL/launcher objects on imagery, i.e. the chassis+launcher assembly, not the round
  inside. View fragment `ent:component:canisterized launchers`, d17-rawalpindi-2021-l22-2.
- "TEL" (bare) — confirmed via same-as edge fired in-view (`transporter-erector-launcher -> TEL`).

**Corrected out of the evidence-summary's FRAGMENTED-8 list:**
- "Ground support vehicle spares for erector-launcher chassis" (d06 item b) — this is a *spares/support-
  equipment* line item referencing the chassis, not another name for the chassis component. It is evidence
  for `sustain_spares`, not an alias. The evidence-summary double-counted this same string under BOTH
  comp_interceptor and comp_tel_chassis fragmentation lists — neither is really correct; see §3.

---

### 1.3 Variants

#### `var_hq9p` | variant | HQ-9/P (export designator; Pakistan Army; ~125 km)
- "HQ-9P" (no slash) — confirmed, config seed (`resolution.yaml`) + view fragment
  `ent:variant:HQ-9/P` claim set includes d03's explicit note "some Pakistani officers... have referred to
  it simply as HQ-9P without the slash."
- "FD-2000" — confirmed, config seed (explicit "auto-merge; the seeded merge card") + same-as edge
  `HQ-9/P -> FD-2000` fires in-view (status=probable); claims d03, d04, d15.
- "HIMADS" — confirmed, config seed ("Pakistani service nickname") + corpus: d02 "High to Medium Air
  Defence System (HIMADS)"; d20 "HQ-9/P (HIMADS) battery".
- "FD-2000/HQ-9P" — confirmed, view fragment `ent:variant:FD-2000/HQ-9P`, d15-globaltimes-aligned-l13.
- "HQ-9P long-range air defense system" — confirmed, view fragment
  `ent:variant:HQ-9P long-range air defense system`, d17b-withheld-gap-l9.
- "Long Range Surface-to-Air Missile (LR-SAM) system" — confirmed alias **within the d06 tender's own
  framing** ("the export configuration of the Hongqi-9 family... variously referred to... as HQ-9/P, HQ-9P,
  or... FD-2000"); view fragment `ent:variant:Long Range Surface-to-Air Missile (LR-SAM) system`,
  d06-spares-tender-l15-2.
- "the System" (d06, capitalized, defined term) — confirmed **only inside d06's own defined-term scope**
  (d06 explicitly defines "the System" = the LR-SAM/HQ-9P/FD-2000 in ¶1.1–2.1); still, because it is a bare
  generic noun-phrase rather than a proper name, I also list it in §3 as a caution against blind reuse
  across other documents.

**Corrected / unverified — do NOT treat as confirmed aliases of var_hq9p:**
- "FD-2000B" (d03) — explicitly hedged in the same sentence as a possibly *different, newer* variant
  ("it is not established whether Pakistan's batch corresponds to this improved variant or the earlier
  baseline"). Moved to §2 as a third candidate-to-verify alongside H-200 and Type 305B.
- "Hongqi-9" / "HQ-9" / "红旗-9" / "紅旗-9" (bare, no `/P` suffix) — these denote the **parent Chinese
  HQ-9 family**, not the Pakistan-Army-specific export variant. The view itself keeps this distinction via
  a `derived-from` edge (`HQ-9/P -> HQ-9`), not a same-as edge — i.e. the pipeline is already treating "HQ-9"
  as a separate (parent) node, correctly. There is **no oracle ground_truth id for "plain HQ-9"** at all.
  See §4 — this is a structural gap, not a bucketing call I can make unilaterally.
- "Hongqi-9 family" — same parent-family sense; view same-as edges chain it to both FD-2000 and HQ-9/P
  (`Hongqi-9 family -> FD-2000`, `Hongqi-9 family -> HQ-9/P`, `Hongqi-9 family -> HQ-9P`), which is *itself*
  evidence of the fragmentation problem (the pipeline is conflating "the whole HQ-9 lineage" with "the
  specific Pakistan Army export variant"). Flagging, not fixing.
- "CH-SA-9" — appears in raw doc text only (d17: "CASIC HQ-9B (export/derivative of the HQ-9, CH-SA-9 per
  NATO reporting)"; d07: "HQ-9/P (export variant of the CASIC HQ-9, NATO CH-SA-9)") but was **never
  extracted into any claim or view node** in either document. The two occurrences don't even agree on
  which variant it modifies (d17 ties it to HQ-9B, d07 ties it to HQ-9/CASIC-generic). See §3 (ambiguity)
  — not confidently bucketable to var_hq9p, var_hq9be, or the missing "parent HQ-9" concept, and it's an
  extraction miss besides.

#### `var_hq9be` | variant | HQ-9BE (export designator; Pakistan Air Force; ~260 km)
- "HQ-9B" — confirmed, view fragment `ent:variant:HQ-9B` (status=confirmed), claims d14, d17, d19, d22,
  d24, d25; same-as edge `HQ-9BE -> HQ-9B` fires in-view.
- "HQ-9BE" — confirmed, view fragment `ent:variant:HQ-9BE` (status=confirmed), claims d04, d19, d24, d25.
- "HQ-9B (export)" — confirmed, view fragment `ent:variant:HQ-9B (export)`, d18-rahwali-pass1-l5.
- "HQ9B" (no hyphen) — confirmed, corpus text only (not independently extracted as its own node): d20's
  social posts repeatedly use "HQ9B" / "HQ9 btry" (e.g. "the HQ9B btry that was sitting at Rahwali").
- Note the **d19 self-reported inconsistency**: d19 states outright "readers tracking the
  HQ-9/HQ-9B/HQ-9BE/HQ-9P designator family should note continuing inconsistency across open sources in how
  Pakistani service designators map to the PLA domestic HQ-9B baseline versus the CASIC export HQ-9BE
  marketing designation; this digest uses 'HQ-9B' generically." I.e. the corpus author is *telling you* not
  to trust "HQ-9B" as unambiguous — treat the above aliases as high-confidence but not absolute.

#### `alias_ft2000` | variant | FT-2000 / FT-2000A (anti-radiation variant, DISTINCT-FROM HQ-9/P)
- "FT-2000" — confirmed, view fragment `ent:variant:FT-2000`, d04-armyrec-ranges-l13.
- "FT-2000A" — confirmed, view fragment `ent:variant:FT-2000A`, d04-l13-3; same-as edge
  `FT-2000 -> FT-2000A` fires in-view.
- distinct-from edges (`alias_ft2000 -> var_hq9p`, `FT-2000 -> HQ-9/P`) already fire correctly in-view —
  the do-not-merge trap is currently holding.

---

### 1.4 Contract / import event

#### `import_2021` | contract_import_event | China→Pakistan HQ-9/P transfer (confirmed, 2021)
**Zero matching view nodes** — see §4 Coverage note. No `contract_import_event`-typed node exists for the
actual 2021 transfer; the induction is represented only via bare `inducted-into` / `imported-by` edges
directly between the variant/unit nodes, with no event node to hang them off of. Descriptive phrases that
narrate this event across docs (informational, not proper-noun aliases, since there is no named event
entity to alias):
- "China–Pakistan HQ-9/P transfer, SIPRI" (d01, literal quoted bulletin phrase).
- "the Pakistan HQ-9/P order" (d23, referencing the SIPRI entry).
- "AHQ/AD-PROC/[REDACTED]/2023" — this IS a `contract_import_event`-typed view node
  (`ent:contract_import_event:AHQ/AD-PROC/[REDACTED]/2023`), but it is the **wrong entity** — it's the 2023
  *spares/sustainment* tender (d06), which the tender's own text explicitly says "does NOT constitute
  procurement of a new weapon system." This looks like a genuine mistyping: the one
  `contract_import_event` node in the whole view is actually sustainment evidence that belongs near
  `sustain_spares`, not a fresh import. Flagged prominently in §4 — this is likely the more actionable
  finding than the "missing" node itself.

---

### 1.5 Units

#### `unit_paad` | unit (confirmed) | Pakistan Army Air Defence — HQ-9/P regiment
- "Pakistan Army Air Defence (PAAD)" — confirmed, view fragment
  `ent:unit:Pakistan Army Air Defence (PAAD)`, d02-ispr-induction-l11-4 ("...formally inducted into service
  with a Pakistan Army Air Defence (PAAD) unit").
- "Pakistan Army Air Defence Command" — confirmed, view fragment
  `ent:unit:Pakistan Army Air Defence Command` (status=confirmed in-view), d09, d14, d23.
- "Army Air Defence Command" — confirmed for the d03 and d04 occurrences (both explicitly "the Pakistan
  Army's Army Air Defence Command" / "the Pakistan Army's Air Defence Command"). **Caution on the d19
  occurrence** — see §3, d19 uses this string in a Rahwali/PAF joint-use context where it may actually be
  gesturing at `unit_hq9b`, not `unit_paad`. Same view-node id (`ent:unit:Army Air Defence Command`) is
  backed by claim_ids from both d03 and d19 — they are not equally trustworthy for this bucket.
- "Air Defence Command" (bare, Army's) — confirmed for d04 ("The Pakistan Army's Air Defence Command
  operates a battery-level deployment reportedly designated HQ-9/P"). View fragment (bare, under
  `unknown`), d04-armyrec-ranges-l7-2/l7-3.
- "Pakistan Army" (bare, as parent service in a PAAD context) — confirmed for d02/d03/d09 usages. **Caution**
  on the d19 occurrence (see §3 — extracted from "Pakistan Army/PAF joint-use facility" language describing
  Rahwali, not a direct PAAD assertion).
- "Army Air Defence Centre, Karachi" — d02's literal phrase ("COAS VISITS ARMY AIR DEFENCE CENTRE,
  KARACHI"). The view typed this as a **basing_site** node (`ent:basing_site:Army Air Defence Centre`,
  d02-ispr-induction-l11), not a unit — flagging here as the induction-ceremony venue, but see §3 for
  whether it's the same physical place as `site_karachi`.

**Explicitly NOT aliases of `unit_paad`** (do not co-list): "Pakistan Air Force", "PAF", "PAF air defence
squadrons" — these belong to `unit_hq9b`'s side (see below). Two of these ("Pakistan Air Force", "Pakistan
Army") were additionally found **mistyped as `entity_type: "manufacturer"`** in the raw claims for d04
(claim_ids d04-armyrec-ranges-l7 and l9, both `attrs.role: "operator"` but typed manufacturer) — a genuine
extraction bug that fragments these units across a type the evidence-summary's heuristic never searched.
See §4.

#### `unit_hq9b` | unit (confirmed) | PAF HQ-9B fire-unit (relocation subject)
- "PAF" (bare) — confirmed, view fragment `ent:unit:PAF`, d19-rahwali-confirm-l11-3 — **with the caveat**
  that this specific occurrence comes from "Rahwali airfield (Pakistan Army/PAF joint-use facility...)",
  i.e. describing the *site* as joint-use, not unambiguously asserting PAF as the operating unit at that
  moment. Still the best-attested short form for this id.
- "Pakistan Air Force" — confirmed generically as unit_hq9b's parent service, e.g. d01 ("Pakistan Air Force
  having taken delivery of the HQ-9/P..." — note this d01 usage itself blurs Army/PAF, see §3), d21
  ("Pakistan Air Force's (PAF) HQ-9/P... battalions").
- "PAF air defence squadrons" — confirmed, view fragment `ent:unit:PAF air defence squadrons`,
  d21-techdata-authority-l6-9 (d21: "...reportedly equips at least two, and possibly three, PAF air defence
  squadrons").
- "PAF HQ-9B fire-unit" — oracle's own name; not independently seen as a literal string in corpus, but
  matches d17/d18/d19's descriptive language for the fire unit at Rawalpindi/Rahwali.

---

### 1.6 Basing sites

#### `site_karachi` | basing_site (confirmed, imagery, 2022) | Karachi AAD site (Malir area)
- "Malir District, Karachi, Sindh Province, Pakistan" — confirmed, view fragment
  `ent:basing_site:Malir District, Karachi, Sindh Province, Pakistan`, d07-sat-confirm-karachi-l6.
- "Malir AD area" — config seed (`places.yaml` alias for `pl_karachi_ad`).
- "Malir" (bare, as used in d08 social posts: "same unit that was near Malir couple months back") —
  corpus-attested, consistent with the above.
- coordinate form "24.9012 N, 67.2034 E" (DD) — confirmed, matches `pl_karachi_ad.canonical_dd` exactly,
  d07-sat-confirm-karachi.

**Bare "Karachi" is explicitly flagged AMBIGUOUS by the oracle itself** (see d02's own
`expect.location.note`: "AMBIGUOUS parent-city form -> resolves to the metro, not to a specific pad/
terminal"). I am following that instruction and NOT listing bare "Karachi" as a confirmed alias of
`site_karachi` — it's a city-level reference that could equally point at `pl_port_qasim` or
`pl_karachi_port`. View fragment `ent:basing_site:Karachi` (d09) and node `Karachi area` (d09) should stay
unresolved-to-metro, not auto-merged to the pad.

**Explicitly NOT aliases of `site_karachi`** (do not merge — see §3 for full reasoning):
- "Army Air Defence Centre" / "Army Air Defence Centre, Karachi" (d02) — plausibly the same broad
  Malir-area installation, but could be the AAD training establishment rather than the tactical SAM pad.
- "Karachi coastal air defence belt" (d23) — vague, plural, possibly a different site.
- "bases in the Karachi and central Punjab air defence sectors" (d21) — spans multiple sites, can't isolate.
- "Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area" (d05, customs broker delivery note) —
  Attock is nowhere near Karachi; this is a **different, uncorroborated 4th location**, not Malir. This one
  matters: the evidence-summary's type-heuristic put it in `site_karachi`'s FRAGMENTED-9 list purely
  because both are `basing_site`-typed strings — that pairing is wrong and should not be seeded.
- "Karsaz-Korangi belt / port road area", "the usual site near the port road" (d08 social posts) — Karachi-
  adjacent but not confirmed as the same pad; treat as loose-locale chatter, not a site_karachi alias.

#### `site_rawalpindi` | basing_site (stale) | PAF Base Nur Khan (fmr Chaklala), Rawalpindi
- "PAF Base Nur Khan" — confirmed, view fragment `ent:basing_site:PAF Base Nur Khan`, d17-rawalpindi-2021-
  l4; config seed (`places.yaml`).
- "PAF Base Chaklala" / "Chaklala" — confirmed, corpus text (d17: "the installation historically known as
  PAF Base Chaklala, now designated PAF Base Nur Khan"). **Deliberately WITHHELD from the seed gazetteer**
  per `places.yaml`'s own comment — this is the earned-merge demo, not an oversight. Do not seed it without
  triggering the intended "earn the merge" behaviour.
- "RAF Chaklala" — config seed (`places.yaml` alias list for `pl_nurkhan`), historical name, not
  independently seen as a literal corpus string in docs read.
- "the old Rawalpindi-area site" — confirmed, view fragment
  `ent:basing_site:the old Rawalpindi-area site`, d17b-withheld-gap-l9-2.
- "Rawalpindi Cantonment" — confirmed, corpus text, d17 ("the eastern margin of Rawalpindi Cantonment").
- "the old Rawalpindi site" (d20, the spoof post's claimed relocation destination) — same physical
  referent, but sourced from the deliberately low-credibility D8 spoof post; include with that caveat.
- MGRS "43S CT 23715 21242" — confirmed, d17, matches `pl_nurkhan`'s canonical coordinate class.
- "fenced compound near a PAF airbase in central Punjab" (d01) — weak/generic but contextually consistent;
  include as a low-confidence corroborating description, not a strong alias.

#### `site_rahwali` | basing_site (confirmed, 2025) | Rahwali airfield/cantonment, Gujranwala
- "Rahwali airfield" — confirmed, view fragment `ent:basing_site:Rahwali airfield` (status=confirmed
  in-view), d18-rahwali-pass1-l5-3, d19-rahwali-confirm-l11.
- "Rahwali Cantonment" — confirmed, corpus text + config seed, d19 ("the Rahwali Cantonment airfield").
- "Rahwali Cantt", "Rahwali Air Base", "Rahwali" (bare) — config seed (`places.yaml`).
- "Rahwali airbase, Gujranwala" — confirmed, view fragment `Rahwali airbase, Gujranwala` (bare, under
  `unknown`), d20-supersede-spoof-l14-3 (again, sourced from the D8 spoof post — same physical site, low-
  credibility source).
- "Gujranwala Cantonment area" — confirmed, corpus text, d18 ("Rahwali airfield (Gujranwala Cantonment
  area)").
- "~10 km NW of Gujranwala along the GT Road corridor" — confirmed, relative-bearing form, d19; this is the
  form that must resolve to the SAME node as d18's DMS coordinate for the 2nd-signal corroboration to fire
  (the scenario's own load-bearing point, per answer_key `flexes.location_normalization`).
- DMS "32°14′20″N 074°07′52″E" — confirmed, d18.

---

### 1.7 Sustainment / techdata

#### `sustain_techdata` | techdata_authority (probable) | Technical-Data / Software & Calibration Authority
**No confirmed alias found.** d21 (the only doc that discusses this dependency) never gives it a proper
noun — it is described only descriptively: "a Chinese state technical-data authority," "the broader
CASIC/CPMIEC export administrative chain." This is consistent with the oracle's own framing of it as "the
invisible dependency." See §4 — genuinely zero surface forms, not a bucketing miss.

#### `sustain_spares` | interceptor_stockpile (probable) | spares/maintenance tender implication
**No node of the correct type exists in the view at all** (0 `interceptor_stockpile`-typed nodes). The
evidentiary basis is d06 (the 2023 spares tender), whose line items got extracted as individual
`component`-typed nodes instead of being attached as evidence under a `sustain_spares` node:
- "TVM (track-via-missile) uplink/downlink test sets" (d06 item a)
- "Ground support vehicle spares for erector-launcher chassis" (item b)
- "Battery/charging modules for engagement radar cabin" (item c)
- "Waveguide assemblies and RF connectors, various" (item d)
- "Calibration/test jigs for missile round check-out prior to captive-carry/loading drills" (item e)
- "Consumable seals, gaskets, desiccant cartridges for missile canister environmental control" (item f)

These six are **evidence supporting the `sustained-by` relationship**, not aliases of `sustain_spares`
itself (there is nothing here that is literally "another name for" the sustainment-implication concept) —
see §3. Do not seed any of them as aliases of `sustain_spares`, `comp_interceptor`, `comp_ht233`, or
`comp_tel_chassis`.

---

### 1.8 Known gaps (listed separately, not alias-grouped, per instructions)

- `gap_ht233_maker` | known_gap | "HT-233 manufacturer + substitutability" — **zero matching view nodes**
  (no `known_gap` node text corresponds to this concept). See §4.
- `gap_launcher_count` | known_gap | "TEL/battery count" — matched one view node:
  `ent:known_gap:Collection over the primary AOI on 10 May was severely degraded by persistent
  cumulus/stratocumulus cover... unable to confirm the current count of transporter-erector-launchers
  (TELs) present at the site` (d10-sat-cloud-gap-l14). This is a legitimate instance-level match (one
  specific occasion the launcher count couldn't be confirmed), not a generic alias — treat it as **one
  supporting instance** of the gap, not interchangeable with the gap concept itself.

### 1.9 Places (already gazetteered — noted, not touched)

All 7 oracle places (`pl_nurkhan`, `pl_rahwali`, `pl_karachi_ad`, `pl_port_qasim`, `pl_karachi_port`,
`pl_casic_2nd`, `pl_birm`) already have canonical entries + alias lists in `config/places.yaml`, which is
the authoritative pattern this whole registry mirrors. One additional real-corpus surface form worth
noting for whoever next touches the gazetteer (not acting on it here): d05's customs manifest also uses
"Karachi International Container Terminal / QICT PQ" for the Port Qasim terminal — "QICT" is not currently
in `pl_port_qasim`'s alias list.

---

## 2. Candidate aliases to VERIFY (do not seed as auto-merge)

These are surface forms the corpus itself hedges as *possibly* the same component/variant, never
confirmed. Per the task's hard constraint, keep these OUT of the confirmed lists above.

1. **"H-200" → `comp_ht233` (HT-233)**
   - Evidence: d10-sat-cloud-gap, view node `ent:component:HT-233 (H-200) engagement radar array`; raw
     text: "a HT-233 (H-200) engagement radar array" (d10 l16).
   - Also echoed in d06's tender text: "believed by open-source observers to be a derivative of the Type
     305B / H-200 family, though PAF does not confirm or deny specific radar nomenclature" (d06 §4.1) —
     note this sentence itself hedges H-200 *and* Type 305B together as one disputed cluster.
   - Per `resolution.yaml`'s own comment: explicitly withheld from the seed table — "'H-200' -> 'HT-233' ->
     ORPHAN alias to VERIFY (a candidate, not an assumption)." My reading agrees with that existing design
     decision; I am not overriding it.

2. **"Type 305B" / "Type 305B (HT-233 derivative)" → `comp_ht233` (HT-233)**
   - Evidence: d01 ("the Type 305B (HT-233 derivative)"), d14 ("tentatively assessed as a Type 305B
     (HT-233) fire-control set"; "also rendered Type 305B in some translations"), d06 (see above).
   - Both d01 and d14 explicitly hedge: "terminology is not standardized across sources, and it is not
     clear whether the unit fielded is identical to the PLA's domestic HT-233 or a modified export
     variant" (d01); "tentatively assessed" (d14). This is deliberate corpus messiness, not a typo.

3. **"FD-2000B" → `var_hq9p` (HQ-9/P)**
   - Evidence: d03 — "CASIC's own promotional material for the newer FD-2000B has claimed ranges as high
     as 250 km, though it is not established whether Pakistan's batch corresponds to this improved variant
     or the earlier baseline."
   - This reads as the *same* hedge pattern as #1/#2 above (an enhanced/derivative product name the corpus
     explicitly declines to equate with the fielded system) — flagging it alongside them rather than
     letting it slip into var_hq9p's confirmed list, where it currently sits as an unmerged view fragment
     (`ent:variant:FD-2000B`, d03-quwa-analysis-l10-2).

4. **"extended-range round" → `comp_interceptor`**
   - Evidence: d01 — "at least one Pakistani parliamentary aside (unconfirmed, secondhand) put the figure
     closer to 200 km for an unspecified 'extended-range' round; this desk treats the longer figure as
     unverified pending a primary source." View fragment `ent:variant:extended-range round`,
     d01-sipri-transfer-l18-2.
   - Whether this is the *same* interceptor round as `comp_interceptor` or a distinct enhanced sub-variant
     is exactly as unresolved in-corpus as #1–#3; given `comp_interceptor` otherwise has zero corpus
     aliases (§1.2), this is worth flagging even though it's typed `variant` in the view, not `component`.

---

## 3. Ambiguities I could not confidently bucket

1. **Bare "engagement radar"** — appears in d07 ("a raised circular foundation... is consistent with an
   emplaced engagement radar (possibly HT-233 or derivative, NATO association tentative)") and elsewhere.
   Candidates: `comp_ht233`. Why unsure: it's a functional-role common noun, not a proper name, and d01
   itself explicitly refuses to equate "the engagement radar associated with the system" with HT-233
   specifically ("it is not clear whether the unit fielded is identical to the PLA's domestic HT-233 or a
   modified export variant"). Bucketing it to comp_ht233 by default would silently resolve a distinction
   the corpus deliberately leaves open.

2. **"the System"** (bare, capitalized, d06) — Candidates: `var_hq9p`. d06 does define this term for its
   own tender scope, so within-document it's about as confirmed as a defined term gets — but it's a bare
   pronoun/placeholder, not a proper noun, so treat any *other* document's use of "the System" (there
   wasn't one found here, but a future doc could reuse the string) as needing its own check, not an
   automatic merge into var_hq9p.

3. **"bases in the Karachi and central Punjab air defence sectors"** (d21) — Candidates: `site_karachi`,
   `site_rawalpindi`, `site_rahwali` (Rahwali is also Punjab). Why unsure: the phrase is explicitly plural
   and regional, spanning at least two provinces' worth of sites; there is no way to isolate which specific
   oracle site(s) it refers to from this sentence alone.

4. **"Army Air Defence Centre, Karachi"** (d02) vs `site_karachi` — Candidates: `site_karachi` (same Malir/
   Karachi area) or a distinct AAD training/school establishment. Why unsure: the real-world Pakistan Army
   Air Defence Centre & School is a known institution in the Malir area, which makes a merge plausible, but
   d02's context is a COAS visit/induction ceremony venue, which could be the training establishment rather
   than the operational SAM pad the imagery docs (d07) describe. The view typed it as its own
   `basing_site` node rather than resolving it either way.

5. **"CH-SA-9"** — appears twice in raw doc text (d17, tied to HQ-9B; d07, tied to "CASIC HQ-9"/HQ-9/P) but
   was never extracted into any claim in either document, and the two occurrences don't even agree with
   each other on which variant it names. Candidates: `var_hq9p`, `var_hq9be`, or the un-modeled "parent
   HQ-9" concept (§4). Why unsure: three-way ambiguity plus zero extraction — nothing to anchor a decision
   on beyond the raw prose.

6. **"Army Air Defence Command" / "Pakistan Army" at d19-rahwali-confirm-l15-2 / l11-2** — Candidates:
   `unit_paad` (default reading) or `unit_hq9b` (given the sentence's own "Pakistan Army/PAF joint-use
   facility" framing for Rahwali). Why unsure: every OTHER occurrence of "Army Air Defence Command" (d03,
   d04) is unambiguously unit_paad in an Army-only context; this one occurrence sits inside a sentence
   explicitly describing a *joint* Army/PAF facility, which is precisely the kind of context the task's
   hard constraint (don't co-list PAF forms under unit_paad) warns about. I did not merge it, but the
   existing view node conflates claim_ids from both the clean d03 case and this ambiguous d19 case under
   one string.

7. **PAF/HQ-9P cross-wiring in d21** — d21 describes "PAF air defence squadrons" as operating a system it
   calls "HQ-9/P" throughout (the Army-designated variant name), rather than "HQ-9BE" (the PAF-designated
   name the oracle uses for `var_hq9be`/`unit_hq9b`). Candidates for what d21's "HQ-9/P" claims actually
   attach to: `var_hq9p`+`unit_paad` (oracle-clean reading) or `var_hq9be`+`unit_hq9b` (matching d21's own
   PAF framing). This is the flagship Army-vs-PAF distinct-from trap the scenario is built around
   (`var_hq9p` ~125 km Army vs `var_hq9be` ~260 km PAF) showing up as a genuine source-level conflation, not
   just a naming variant — flagging rather than picking a side.

8. **"missile canisters"** (d23: "up to 6-8 transporter erector launchers (TELs) each with 4 missile
   canisters") — Candidates: `comp_tel_chassis` (the launcher's canister tubes) or `comp_interceptor` (the
   round stored inside). Why unsure: the sentence describes canister count per launcher, which is a
   TEL-hardware fact, but "canister" could also stand in for "round" in casual usage. Given
   `comp_interceptor` has no other corpus aliases at all (§1.2), I did not want to manufacture one here on
   a genuinely 50/50 read.

9. **The d06 sustainment sub-items** (the 6 line items listed under §1.7) — technically these are
   "component"-typed view nodes, which is why the evidence-summary's heuristic offered them as fragments of
   comp_ht233/comp_interceptor/comp_tel_chassis. I judged them to be evidence-for-`sustain_spares`, not
   aliases of any of the three components — but flagging the call itself as a judgment, not a certainty,
   in case a future reviewer reads d06 differently (e.g. "Battery/charging modules for engagement radar
   cabin" could arguably be modeled as a comp_ht233 sub-part with its own id rather than pure sustainment
   evidence).

---

## 4. Coverage note

**Oracle ids with zero matching view/corpus surface forms (genuinely missing from extraction):**

- `gap_ht233_maker` (known_gap) — no corresponding `known_gap` node text in the view at all.
- `sustain_techdata` (techdata_authority) — no proper-noun node; the one doc that discusses it (d21) never
  names it, by design ("the invisible dependency").
- `import_2021` (contract_import_event) — no `contract_import_event`-typed node represents the actual 2021
  transfer; the induction is only visible via bare edges with no event node behind them.
- `comp_interceptor` (component) — no corpus-attested proper-noun alias of any kind (see §1.2); only
  generic descriptive phrases and one unverified candidate (§2.4).

**Related but out-of-scope findings surfaced along the way (not oracle ids — no id invented here):**

- **CPMIEC** has a large, real, currently-unmerged alias cluster in the view ("CPMIEC", "China National
  Precision Machinery Import & Export Corporation", "China Precision Machinery Import-Export Corporation")
  and is central to the scenario's flagship false-attribution trap (d23: "CPMIEC manufactures the HT-233"),
  yet has **no oracle ground_truth id of its own** — it only exists as `mfr_casic.export_agent` metadata.
  Whoever designs the eventual CPMIEC entity (if one gets added) can reuse this alias list directly.
- **Front-company / shell consignee cluster from d05** ("ORIENT ELECTRO TRADING (PVT) LTD" / "ORIENT
  ELECTRONIC TRADING CO", "SINO-GALAXY IMP/EXP CO. LTD" / "SINO-GALAXY IMPEX CO, LTD" / "SINO GALAXY IMP. &
  EXP. CO.") — deliberately unresolved-to-any-subject-entity per the scenario's D7 design (civil-vs-
  military contradiction, relational not string resolution). No oracle id exists or should be invented for
  these; flagging only so nobody accidentally merges them into `comp_ht233` on HS-code proximity.
- **"HQ-9" parent-family cluster** ("HQ-9", "Hongqi-9", "红旗-9", "紅旗-9", "Hongqi-9 family") — denotes the
  Chinese domestic base system distinct from both `var_hq9p` and `var_hq9be`; the view already keeps it
  separate via a `derived-from` edge rather than same-as, which looks correct, but there is **no oracle
  ground_truth node for "plain HQ-9"** to register aliases against. This is the single largest structural
  gap I found — a real, load-bearing entity concept with no id.

**Extraction-typing bugs found that widen fragmentation beyond what the evidence-summary's heuristic could
see** (its heuristic only compared nodes of the *same* type, so it structurally cannot catch these):

- "Pakistan Army" and "Pakistan Air Force" were extracted with `entity_type: "manufacturer"` (not `"unit"`)
  in d04 (claim_ids `d04-armyrec-ranges-l7`, `d04-armyrec-ranges-l9`, both carrying `attrs.role: "operator"`
  — i.e. the extractor itself tagged them as operators but still filed them under the manufacturer type).
  This means unit_paad/unit_hq9b are fragmented across **two node types** in the current view, not one —
  worth confirming whether other unit-typed oracle entities have similar cross-type escapees before Phase 2
  seeds a fix.
- The sole `contract_import_event`-typed node in the whole view (`AHQ/AD-PROC/[REDACTED]/2023`) is the 2023
  *sustainment* tender (d06), which is arguably mistyped — d06's own text says it is explicitly NOT a new
  import ("does NOT constitute procurement of a new weapon system"). The actual `import_2021` event has no
  node of its own type at all. This looks like more than a fragmentation issue — it may be a genuine
  ontology-application bug worth a separate ticket, not just an alias-merge fix.
