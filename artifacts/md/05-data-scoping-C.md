# Use Case C — Real-World Data Scoping

**Question this answers:** for Use Case C (auditable ORBAT + supply-chain map of an adversary
long-range air-defence capability), *what real open-source data can I actually get* — free vs paid,
what the raw records look like, how messy they are — and *which candidate subject* has the richest
real trail, so subject choice can be driven by data availability (per the plan in `03-planning-notes.md`).

Candidate subjects scoped: **(a) China HQ-9 / HQ-9B** (domestic), **(b) Pakistan HQ-9/P + HQ-9BE**
(import from China), **(c) China's S-400** (import from Russia).

> **Provenance note.** Compiled from four parallel source-scoping passes (2026-07-16). Verbatim quotes
> and URLs were pulled from live pages; the SIPRI *record layout* is verified but its figures are
> illustrative — **re-verify specific numbers against the live DB before they enter the build or design
> note.** Several government sites (PIB, PLA `weain.mil.cn`, `eng.mod.gov.cn`, PPRA, NGA MSI) block
> datacenter IPs and need a real browser / in-country proxy even though the pages are public.

---

## 0. The load-bearing finding (read this first)

**Finished SAM systems are essentially invisible in public customs / shipment data — for every one of
these adversaries.**

- **Russia classified all customs/import-export data in April 2022** (Federal Customs Service). The
  Russia→China S-400 transfer sits entirely inside that blackout, and even pre-2022 it moved by G2G
  contract, not reported commercial trade.
- **China** publishes only *aggregate* customs statistics — no partner-level or shipment-level detail
  with consignee names; PLA/defence-SOE procurement never surfaces.
- **Pakistan** has **no public bill-of-lading / manifest feed** at all.
- **India** publishes rich shipment-level bill-of-entry data (why Zauba/ImportGenius work there) **but
  carves out MoD / defence-force imports** via blanket customs-duty/IGST exemptions — they don't appear
  as ordinary importers.
- Even where a shipment *is* in the data, defence goods appear under **bland dual-use HS codes**
  (8526 "radar apparatus", 8517 "communication apparatus", 8471/8479 electronics/machines) consigned to
  **trading houses, freight forwarders, or front companies** — never the end-user unit, and never as a
  whole "system".

**Two consequences that shape the whole build:**

1. **Customs data is a *component / sub-tier* layer, not a system-detection layer.** The finished-system
   ORBAT spine comes from **SIPRI + imagery + official/analyst reporting**, not customs.
2. **The "customs manifest" file in your corpus should be built *synthetic-from-real-template*** — take
   real ImportYeti/Zauba BoL rows as the *format & messiness template*, swap in your entities. This is
   exactly the hybrid strategy already reasoned toward in `04-claude-chat.md` (Q3): real messiness,
   controlled content, generator blind to the ontology. It is *defensible*, not a cop-out — and you can
   say so on the call, because the real data genuinely doesn't exist for these lanes.

---

## 1. Source-type feasibility matrix

Verdict key: **YES** = real samples freely gettable · **PARTIAL** = gettable with limits (paywall,
component-tier-only, needs verification) · Template = usable mainly as a *format/messiness* template.

| # | Source type | Best free source(s) | Access | What the raw record looks like / messiness | Verdict |
|---|---|---|---|---|---|
| 1 | **Arms-transfer register** | **SIPRI Arms Transfers DB** | Free, downloadable (RTF/CSV) | Analyst-coded deal rows: supplier, recipient, qty ordered, designation, description, year of order, years of delivery, qty delivered, comments, TIV. *Not* customs. | **YES** — the ORBAT/transfer spine |
| 2 | **Aggregate trade stats** | UN Comtrade; ITC TradeMap | Free (Comtrade guest 500 recs/call; TradeMap free w/ reg.) | HS 2/4/6-digit reporter×partner×year aggregates. No company names, no shipments. Systems absent; dual-use codes (8526/8517/9306) only. | **PARTIAL** — component-flow trends only |
| 3 | **Shipment-level bill-of-lading** | ImportYeti (US ocean, free); Zauba (India, now gated); Panjiva/Volza/ImportGenius (paid) | Free for US-import & (historically) India; **none for CN/RU/PK** | Date, consignee, shipper, origin→dest port, HS code, *bland* description, qty, weight, B/L no. | **PARTIAL / Template** — real rows only on US/India lanes; use as format template |
| 4 | **Procurement / tenders** | Pakistan PPRA (English); India GeM/CPPP + MTD PDF (English); Russia zakupki bulk-FTP (Russian) | Civilian portals free; **system contracts closed / PLA portal IP-blocked & Chinese-only** | Contract/lot nos., "as per Annexure III" pointer chains, NTN/registration reqs, corrigenda, redactions. India MTD PDF = cleanest bureaucratic-messiness template. | **PARTIAL / Template** — sustainment/spares yes; system buy no |
| 5 | **Manufacturer disclosures** | Rosoboronexport (roe.ru), Almaz-Antey (S-400); CASIC/CPMIEC (HQ-9) | Free English PDFs (RU firms); HQ-9 only airshow brochures | Corporate press releases / export catalogues naming "S-400 Triumf"; HQ-9 export marketed as "FD-2000". | **PARTIAL** — S-400 best; HQ-9 = marketing only |
| 6 | **Official / MoD statements** | ISPR (PK), TASS (RU), PIB (IN), China MND | Free, English | Induction/contract announcements (dates, service, capability phrasing) — **but not contract internals**. | **YES** |
| 7 | **Think-tank / academic / trade media** | CSIS Missile Threat, SIPRI fact sheets, RAND, NTI, ORF, RUSI (Bronk PDF), Quwa, The Diplomat, Janes (free tier), Army Recognition, Defense News | Mostly free (IISS ORBAT tables paywalled; Quwa/Janes freemium) | ORBAT counts, variant/lineage, supply-chain narrative, **the alias mess**, hedged language, dated facts. | **YES** — richest narrative layer |
| 8 | **Satellite / commercial imagery** | Copernicus Sentinel-2/1; USGS EarthExplorer; Google Earth Pro; ESRI Wayback | Free | S-2 10 m shows *site footprint* (cleared ring/petal pad, revetments), not the launcher. Sub-meter (Google Earth/Wayback) resolves vehicles *if* a good historical frame exists. Cloud/occlusion; capture≠event time; ambiguous objects. | **PARTIAL** — site-level free; launcher-level needs luck |
| 9 | **Existing OSINT deployment maps** | **CSIS AMTI** (HQ-9 on Woody Island — dated, sourced imagery); Missile Threat; IMINT&Analysis (site coords); ClimateViewer SAM layer; GeoConfirmed; Wikimapia | Free | Coordinate-level site catalogues; AMTI is authoritative & dated, blogs/KMZ mix confirmed+speculative. | **YES** — esp. China HQ-9; S-400-in-China sparse |
| 10 | **Geolocated social media** | Manual copy-paste from X OSINT accounts, Telegram channels, YouTube | X API paywalled; manual is free & legal | Slang, colloquial place names, no coords, relative times, hype, **recycled/miscaptioned images**. YouTube parade/exercise = clear ground-level launcher shots (great VLM input). | **PARTIAL** — manual feasible; automation paywalled; needs verification |
| 11 | **NOTAMs / nav-warnings** | FAA NOTAM Search; **NGA NAVAREA** (.txt) | Free, no login | Uppercase code strings, DTG windows (`DDHHMMZ MON`), lat/long polygons, `CANCEL THIS MSG` lines. Excellent messiness template. National AIS (CN/PK/RU) non-English. | **YES** — best raw-format templates |

---

## 2. Source detail (URLs + real snippets)

### 2.1 SIPRI Arms Transfers Database — the transfer spine
- Register: `https://armstransfers.sipri.org/ArmsTransfer/TransferRegister` · TIV tool: `https://armstransfers.sipri.org/`
- Free, no login, downloadable. Curated register of *major conventional weapons* since 1950.
- Covers **(c) China←Russia S-400** (order ~2014–15, deliveries 2018–20) and **(b) Pakistan←China HQ-9/P**
  (deliveries ~2021+). Does **not** cover **(a) China domestic HQ-9** (only cross-border transfers).
- Illustrative record layout (columns verified; figures to re-check live):
  ```
  Recipient: China | Supplier: Russia
  No. ordered: 6 | Weapon designation: S-400 Triumf (SA-21) | Description: SAM system
  Year of order: 2014 | Delivery: 2018–2020 | No. delivered: 6
  Comments: deal ~US$3bn; part of larger package (launcher & interceptor split into separate rows)
  ```

### 2.2 Trade data (Comtrade / TradeMap / shipment providers)
- UN Comtrade `https://comtradeplus.un.org/` — free key ⇒ 500 calls/day, 100k recs/call. Dual-use codes:
  `8526` radar/nav apparatus (the useful one for SAM radars), `8517` comms, `9301`/`9306` arms/ammo.
- ITC TradeMap `https://www.trademap.org/` — free w/ registration; aggregated only, friendlier UI.
- ImportYeti `https://www.importyeti.com/` — **best free BoL** (US ocean imports, 2015→, from CBP FOIA).
  Rows: consignee, shipper, supplier country, product description, HS code, weight, ports, date.
- Zauba `https://www.zauba.com/` (India, now largely gated), Panjiva/Volza/ImportGenius/Export Genius (paid).
- Illustrative BoL row (real field set): `Date | Consignee | Shipper/Origin CN→Dest port (e.g. Nhava
  Sheva) | HS 85269190 | "RADAR APPARATUS PARTS / ELECTRONIC ASSEMBLY" | Qty | Weight | B/L no.`
- Key refs: Russia data classification `https://www.themoscowtimes.com/2022/04/22/russia-classifies-customs-data-as-sanctions-expected-to-bite-a77457`;
  US manifest confidentiality (19 CFR 103.31) `https://www.cbp.gov/trade/automated/electronic-vessel-manifest-confidentiality`.

### 2.3 Procurement / tenders
- **India MTD (best format template):** `https://eprocure.gov.in/cppp/sites/default/files/standard_biddingdocs/MTD%20Goods%20NIC.pdf`
  — sectioned skeleton (AITB, Schedule of Requirements, Qualification Criteria), cross-referenced Forms
  1/1.3/4/4.1/8, detachable Formats 1.1/1.2, sample BOQs. Exactly the "as per Form 4, Annexure to Section
  VIII" pointer-chain messiness to imitate. Live messy notices: `defproc.gov.in`, `eprocure.gov.in`.
- **Pakistan PPRA (real defence sustainment tenders, English):** `https://ppra.gov.pk`,
  `https://epms.ppra.gov.pk/public/tenders/active-tenders` — DGP(Army)/DGDP notices; phrasing e.g.
  *"Sealed tenders are invited from reputed firms… possessing valid NTN certificate… per PPRA Rules."*
- **China CCGP** `https://www.ccgp.gov.cn` (civilian, Chinese-only) · **PLA procurement** `weain.mil.cn` /
  `plap.mil.cn` (military, Chinese-only, IP-blocked — closest to an HQ-9 paper trail, hardest to reach).
- **Russia** `https://zakupki.gov.ru` — free bulk FTP `ftp://free:free@ftp.zakupki.gov.ru` (best raw grab;
  but S-400/Almaz-Antey contracts sit in the closed State Defence Order).

### 2.4 Manufacturer / official
- Rosoboronexport `https://roe.ru` — real English press-release PDFs naming S-400 Triumf (e.g.
  `https://roe.ru/upload/pdf/11386_post.pdf`, 2024). Almaz-Antey `https://almaz-antey.ru`.
- CPMIEC markets HQ-9 export as **FD-2000** (Zhuhai 2012, AAD Cape Town 2009) — brochures only.
- **ISPR (best direct HQ-9/P source):** `https://www.ispr.gov.pk` — induction PR **14 Oct 2021**, Army Air
  Defence Centre Karachi: HQ-9/P as **HIMADS** engaging *"at ranges over 100 km with Single Shot Kill
  Probability,"* part of Pakistan's **CLIAD** shield.
- TASS (S-400 delivery record), PIB (India S-400, PRID 1777612 — contract signed 05 Oct 2018), China MND
  `eng.mod.gov.cn` (denial/deflection source).

### 2.5 Think-tank / academic / trade media
- CSIS Missile Threat: S-400 `https://missilethreat.csis.org/defsys/s-400-triumf/`
  (*"In 2015, China signed an agreement with Russia to purchase six battalions"*); HQ-9 tag
  `https://missilethreat.csis.org/tag/hq-9/`.
- **CSIS AMTI** (imagery-backed HQ-9 ORBAT): `https://amti.csis.org/island-tracker/china/`,
  `https://amti.csis.org/woody-island/` — **the gold-standard geolocated, dated imagery layer**.
- RAND RR-1414 `https://www.rand.org/pubs/research_reports/RR1414.html` (free PDF; battalion counts:
  HQ-9 "32+"). NTI China Missile Chronology `https://media.nti.org/pdfs/china_missile.pdf` (dated).
- **RUSI — Bronk, *Modern Russian and Chinese Integrated Air Defence Systems* (2020):**
  `https://static.rusi.org/20191118_iads_bronk_web_final.pdf` — single most useful open doc; covers both.
- Quwa `https://quwa.org/pakistan/air-defence-pk/hq-9-long-range-air-defence-system/` (freemium, richest
  Pakistan framing). The Diplomat — regiment-by-regiment S-400 delivery series (free, but Cloudflare-blocks
  bots). Janes free OSINT tier (HQ-9B uses *"modified HT-233 target engagement radar"*). Army Recognition,
  Defense News, ORF, Carnegie, Global Times, Naval News. IISS Military Balance — ORBAT tables paywalled.
- Academic peer-review is **thin** and only strategic/proliferation-level (e.g. Arduino & Shuja 2021 on
  S-400 diplomacy; Meijer et al. 2018 "Arming China"). No peer-reviewed *technical/ORBAT* literature names
  these systems — the granularity lives in gray lit + datasets.

### 2.6 Imagery + deployment maps + social
- Copernicus `https://browser.dataspace.copernicus.eu/` (S-2 10 m optical, S-1 SAR). USGS EarthExplorer
  `https://earthexplorer.usgs.gov/` (Landsat + declassified CORONA). **Google Earth Pro** (sub-meter
  historical slider — best single free tool for a named site). ESRI Wayback
  `https://livingatlas.arcgis.com/wayback/` (1 m, 150+ dated versions — change detection). Umbra open SAR
  `https://open-data.umbra.space/` (hi-res but fixed AOIs). Maxar open data (disaster events only).
  *Planet NICFI ended 2025; Planet Edu needs a university email — ineligible on a corporate address.*
- Deployment maps: CSIS AMTI (above); IMINT&Analysis `http://geimint.blogspot.com/2007/10/hq-9-sam-system-site-analysis.html`
  (real HQ-9 site coords); ClimateViewer SAM-sites layer; GeoConfirmed `https://geoconfirmed.org/`;
  Wikimapia. Pakistan HQ-9/P geolocated at Karachi Cantonment by the OSINT community (Quwa/PakDefense).
- Social: X has **no free API** (manual copy-paste is the path). Harvest handles: `@detresfa_`,
  `@rajfortyseven`, `@AuroraIntel`, `@sentdefender`, `@MT_Anderson`, `@Nrg8000`, AMTI/CSIS. Telegram open
  channels scrapeable; **YouTube parade/exercise footage = clearest ground-level launcher imagery for the
  VLM step.** The 2025 India–Pakistan tensions produced the richest HQ-9/P social stream.

### 2.7 NOTAMs / nav-warnings (format templates)
- FAA NOTAM Search `https://notams.aim.faa.gov/notamSearch/`. NGA NAVAREA `https://msi.nga.mil/NavWarnings`
  (free .txt; mirror `sealagom.com`). Real ICAO NOTAM string:
  `A1234/06 NOTAMR A1212/06 Q) EGTT/QMXLC/IV/NBO/A/000/999/5129N00028W005 A) EGLL B) 0609050500 C) 0704300500 E) DUE WIP TWY B SOUTH CLSD...`
  Real NAVAREA rocket-launch hazard: `HAZARDOUS OPERATIONS, ROCKET LAUNCHING: A. 181400Z TO 181825Z JUL...
  IN AREA BOUND BY: 34-29.00N 120-29.00W, ... 2. CANCEL THIS MSG 241943Z JUL 26.`

---

## 3. Candidate-subject comparison

| Dimension | (a) China HQ-9/HQ-9B | (b) Pakistan HQ-9/P | (c) China ← Russia S-400 |
|---|---|---|---|
| SIPRI transfer record | ✗ (domestic) | ✓ single clean transfer | ✓ well-documented |
| Supply-chain shape | domestic production (hard to map as transfer) | **one traceable import** (CN→PK): mfr→export→import→induction | import (RU→CN); provenance rich but Russia data dark |
| Official confirmation | China MND (deflects) | **ISPR — direct, dated (14 Oct 2021)** | TASS + Rosoboronexport/Almaz-Antey |
| Think-tank / trade media | richest technical/ORBAT (RAND, Janes, CSIS) | strong (Quwa, Army Recognition) | richest supply-chain *timeline* (The Diplomat regiment-by-regiment) |
| Imagery / deployment maps | **best** (AMTI Woody Island, coord seeds) | good (Karachi geolocations) | sparse (S-400-in-China) |
| Social media | moderate | **best** (2025 India–Pak conflict) | thin |
| Entity-resolution messiness | high (dense alias tree) | **maximal** (HQ-9/P vs HQ-9BE vs FD-2000 vs HIMADS) | high (Triumf/Triumph/SA-21 + component suffixes) |
| Procurement paper trail | worst (Chinese-only, IP-blocked PLA portal) | partial (PPRA sustainment tenders, English) | closed (State Defence Order) |
| Language friction | high (Chinese) | **low (English)** | high (Russian) |

**Recommendation — anchor on the HQ-9 family, primary subject = Pakistan HQ-9/P, enriched with China HQ-9.**

Why HQ-9/P leads for *this* use case:
- **A single, bounded, traceable import** (China → Pakistan) makes the manufacturer→export→import→
  induction→basing→sustenance chain clean and demonstrable — exactly C's target output.
- **Maximal entity-resolution messiness** (HQ-9/P · HQ-9BE · FD-2000 · HT-233 radar · HIMADS · 红旗-9),
  which is C's *graded marquee* per `04-claude-chat.md`.
- **English-language, quotable, real** sources across the board (SIPRI, ISPR, Quwa, Army Recognition,
  Defense News) — low collection friction.
- **Freshest reporting** (2025 combat-use) → a natural freshness-discipline demo.
- **Best social stream** → satisfies the non-text-modality requirement with real material.

Enrich with **China HQ-9** for the *manufacturer-side ORBAT + imagery/VLM* (AMTI Woody Island imagery,
RAND battalion counts, Janes HQ-9B/HT-233) — it's the same capability family, so this is depth, not
scope-creep. Keep **S-400** as an adjacent/comparative reference in the design note (shows the ontology
generalises across systems). Both alternatives remain fully viable if you'd rather lead with imagery
(→ China HQ-9) or a textbook end-to-end supply chain (→ S-400).

---

## 4. Entity-resolution alias tables (the graded marquee)

All drawn from live, free, quotable pages.

### S-400 system
| Alias/form | Type |
|---|---|
| S-400 Triumf | Russian designation |
| **Triumph** (vs Triumf) | transliteration variant |
| С-400 Триумф | Cyrillic (search-normalisation trap) |
| SA-21 Growler | NATO reporting name |
| S-300PMU-3 | former/developmental designation |

### S-400 components (harder)
| Component | Aliases |
|---|---|
| 91N6 / **91N6E** | "Big Bird" acquisition radar (upgrade of 64N6E "Tombstone") |
| 92N6 / 92N6E | "Grave Stone" engagement radar |
| 96L6 / 96L6E | "Cheese Board" detector |
| Missiles | 48N6 / **48N6E** / DM; 40N6 / 40N6E; 9M96 / 9M96E / E2; 77N6 (bare vs "E" export suffix = routine dedup trap) |

### HQ-9 family
| Alias/form | Type |
|---|---|
| HQ-9 / Hongqi-9 / 红旗-9 / 紅旗-9 | designation / romanisation / simplified / traditional |
| HHQ-9 (海红旗-9) | naval variant |
| **FD-2000** (防盾-2000) | export designation (trade press often labels the whole system this) |
| **FT-2000** | ⚠️ **NOT the same** — separate anti-radiation variant (FAS wrongly lumps "HQ-9/FT-2000") — classic false-merge trap |
| HT-233 / Type 233 | engagement radar (trade press conflates radar ↔ system) |
| CH-SA-9 / CH-SA-N-9 / CH-SA-21 / CH-SA-N-21 | NATO reporting names |
| HQ-9/P (a.k.a. HQ-9P) | Pakistan **Army** variant (~125 km) |
| HQ-9BE | Pakistan **Air Force** extended-range variant (260–280 km) |
| HIMADS | Pakistani service nickname |

**Hazards to encode:** transliteration (Triumf/Triumph/Триумф; Hongqi/红旗); export-vs-domestic split of
the *same* hardware (FD-2000=HQ-9; 48N6E=48N6); **false merges** (FD-2000 ≠ FT-2000); radar-vs-system
conflation (HT-233 vs FD-2000); service-branch variant fork (one PK import → HQ-9/P Army + HQ-9BE PAF).

**Freshness / hedging traps (real):** *"reportedly"* (ORF: S-400 on China–India border, Hotan/Nyingchi,
2021), *"believed to be"* (NTI HQ-9), *"estimated"* ranges (Army Recognition), *"may employ"* (Janes
seeker), *"likely… remains classified"* (Quwa battery counts); CSIS HQ-9 Woody Island *"last imaged… May
20"* (2016) — a dated fact printed as current; NTI chronology predates both S-400 delivery and 2021 PK
induction.

---

## 5. Recommended corpus composition (HQ-9/P anchor)

Satisfies the assignment's *text + ≥1 of image/video/social* rule with margin, and lets you engineer the
five graded scenarios into real-sourced material.

> **Exploratory — constant-supplier realism (2026-07-16).** The China→Pakistan finished-system import is a
> *single constant supplier*, which could look like it flattens the supply-chain / dedup problem. Verdict:
> it does **not** — it's the *confirmed backbone* by design, and the graded difficulty (alias/variant
> resolution, deep-tier uncertainty, credibility/freshness/gaps) is orthogonal to it; a lone importer being
> dependent on one OEM is also the *real* dependency structure, which is exactly what the analysis exposes.
> **Condition:** to keep the chokepoint analysis non-trivial (not "everything depends on China —
> obviously"), the corpus MUST **branch below the prime** (≥1 deep-tier sub-supplier) and include **≥1
> genuine substitutability story** (a component with an alternate source, or the real
> S-400-under-sanctions re-sourcing analog) so `substitutable-by` has known-sole-source vs known-alternates
> vs UNKNOWN cases to distinguish. Generator cases in §5.1; ontology in `../C/01-materiality-ontology.md`.

**Modalities**
- **Text:** SIPRI transfer row; ISPR induction PR; Quwa/Army Recognition/Defense News articles;
  synthetic-from-real customs manifest (ImportYeti/Zauba row as template); synthetic-from-real tender
  (India MTD as bureaucratic-messiness template); real NAVAREA/NOTAM strings for exercise/test tempo.
- **Image:** Google Earth / ESRI Wayback frame of a known site (VLM → *site-typing*); YouTube/parade frame
  of an HQ-9 TEL or HT-233 radar (VLM → *equipment ID*); AMTI-published hi-res for the China-side node.
- **Social:** hand-copied real 2025 sighting posts (X/Telegram) with the native slang/colloquial-name mess.

**Graded scenarios → which real material seeds each** (from `04-claude-chat.md` Q3):
1. *Multi-source corroborated claim* → SIPRI + ISPR + Quwa all confirm the HQ-9/P induction.
2. *Single-source (→ low confidence)* → one hedged *"reportedly"* deployment claim (ORF-style) with no
   corroboration.
3. *Contradicted pair* → official *"routine"* framing vs a social sighting of movement.
4. *Too-clean / provenance trap* → a recycled/miscaptioned parade image reposted as a "new deployment"
   (defeats corroboration-only; provenance/first-seen catches it — see `04-claude-chat.md` Q4).
5. *Gap → "insufficient evidence"* → cloud-covered / stale satellite frame over a site the social post
   claims is active.
6. *Entity-resolution HITL trap* → the **FD-2000 ≠ FT-2000** false-merge, or HQ-9/P↔HQ-9BE↔FD-2000
   ambiguity, surfaced at a confidence threshold for analyst accept/reject.

### 5.1 Supply-chain & entity structure the generator must engineer

Beyond the six credibility scenarios above, the ontology (`../C/01-materiality-ontology.md`) needs these
**structural** cases seeded so the chokepoint + resolution logic has something to bite on. Most deep
instances are legitimately *Known-Gap candidates* (OSINT can't see them) — but seed **at least one concrete
instance of each** so the mechanism demonstrably fires, and make the generator emit each as an explicit,
**labelled** case so we can report exactly which structural cases the corpus contains.

- **Deep-tier / BOM branch (≥1):** one named sub-component chain below the prime — e.g. HT-233 → T/R module
  → foundry (via `component-of` / tier-2 `supplies-component`). Seed **one** deep-tier supplier NAMED by a
  sanctions/export-control listing or tender (→ a *confirmed* deep-tier chokepoint) and leave the rest as
  candidates (→ collection tasks). This is what stops "everything depends on China" being the only finding.
- **Substitutability story (≥1):** at least one component with a **known-alternate** source (→ *not* a
  chokepoint) AND one **known-sole-source** (→ *confirmed* chokepoint), plus the default **UNKNOWN** (→
  candidate). The real **S-400-under-sanctions re-sourcing** narrative is a ready analog; for HQ-9 a
  domestic-vs-import sourcing choice works. Also seed one **adversary-denial** case — a planted "a second
  source exists" claim that must be *discounted*, not treated as a chokepoint downgrade.
- **Unit aliasing (≥1):** one unit carrying multiple designators (official + **cover-designator/MUCD** +
  bort/vehicle numbers) so *unit-level* `same-as`/`distinct-from` resolution is exercised — distinct from
  the system/variant resolution trap in scenario 6.
- **Readiness proxy vs gap:** for one unit, seed observed readiness *proxies* (ELINT emitter-active /
  exercise or parade footage) → an ordinal `operational-status`; leave true serviceability/manning
  unobservable → a **Known Gap**. Demonstrates *possession ≠ combat-ready*.
- **Alt-part (optional, design-note):** a different component that could do the same job (e.g. an
  alternative radar/round) as a Component-level substitute.

### 5.2 Data-generation handoff — gaps to close before freezing the corpus (exploratory, 2026-07-16)

> **Why this block exists.** The C problem-scoping docs (`../C/00-overview.md`, `../C/01-materiality-ontology.md`,
> `../C/02-demo-thread.md`) and this data-scoping doc have **drifted**, because data generation hasn't been
> properly reworked yet — the docs describe a demo the current corpus can't source. This block is the build
> backlog for the data-generation agent. It consolidates (i) the **C↔data divergences** and (ii) the
> **doc↔data-drift** findings from the pre-flight audit (`06-preflight-audit.md` §1 — H-CONSIST-1/2/3,
> H-DEVIATION-1, M-INCONSIST-1, M-DATA-1, L-CONSIST-1). Owner tags: **[needs Pragalbh]** = a scoping decision
> to lock *first*; **[agent]** = follows mechanically once the decision above it is locked. **Nothing here is
> decided** — §1–§5.1 above are unchanged; this is where the next agent picks up.

**5.2.1 — Decisions to lock before extraction freezes** `[needs Pragalbh]`

| # | Divergence | Where it bites | Options / audit-recommended direction |
|---|---|---|---|
| D1 | **Marquee observable has zero seed data.** The locked primary observable is the **HQ-9B Rawalpindi→Rahwali (2025)** occupancy state-change with a `supersedes` retirement — but neither site nor the 2025 event appears anywhere in `05` (grep-empty), and the corpus instead ships a weaker "bare status flip" at an orphan `site_second`. Only **Karachi Cantonment** (`05:148`) has real grounding today. | `C/02` flex 6 (LOCKED, Q1); `06` H-CONSIST-2 | **(a)** regenerate the corpus with the full relocation + `supersedes` thread (add `site_rawalpindi`, retarget `site_second`→`site_rahwali`, seed a decoy-capped probable single pass + an independent confirmer, set `observable.primary=basing_relocation`); **(b)** formally de-lock to the Karachi status flip and strip all Rahwali/supersede language. Audit prefers **(a)**. *Timeline-gated.* |
| D2 | **Flagship merge pair unfixed + un-seeded.** Docs disagree — `C/01` = **HQ-9/P vs HQ-9BE** (`distinct-from`), FD-2000/FT-2000 the "easy secondary"; `08`/`C/02` flex 4 = **FD-2000 ≠ FT-2000** as marquee. Corpus instantiates neither: FT-2000 is in **zero** of 14 docs; **zero** `same-as`/`distinct-from` edges exist. Scenario 6 (`05:276`) still offers both. | `C/01`; `C/02` flex 4; `06` H-CONSIST-3 | Lock ONE flagship (audit: HQ-9/P vs HQ-9BE, seeded by d04), then seed a real `distinct-from` (variant↔variant) + a `same-as`/alias (FD-2000→HQ-9/P) so both merge mechanisms have write-back targets; demote FT-2000 to a design-note example (or add a node + doc if it must appear on screen). |
| D3 | **Imagery/VLM has no substrate.** Zero raster/video in the corpus; imagery "docs" are prose satellite-product text and the M4 social doc narrates the verdict outright. The design commits to a live VLM extractor + computed image-integrity signals that can't run on text. Governs whether the **Image** modality (`05:263-264`) needs real specimens. | `06` H-DEVIATION-1 | **(a)** lock the honest posture — imagery enters as analyst-report **TEXT**; M4 = coordinated-inauthenticity + first-seen from text+timestamps; VLM/EXIF/reverse-image → roadmap; strip the give-away lines so the signal is *earned* from a near-duplicate/burst cluster; **(b)** gather 3–4 real assets and wire one genuine VLM call. |
| D4 | **Demo sustainment node undecided, no source either way.** `C/01`/`C/02` leave the demo sustainment node open (Interceptor Stockpile *or* Tech-Data/Software Authority); `05` sources **neither** (grep-empty), so the "follow-on order via `replenishes`" / TDP-authority beat has nothing to seed. PPRA tenders (`05:103-105`) are generic, not interceptor-specific. | `C/01` sustainment nodes; `C/02` open Q | Pick one node, then source (or synthesize-from-template) one concrete instance — a real follow-on interceptor order / spares tender — to seed it. |
| D5 | **Woody Island may violate C's own enrichment bound.** `05` pushes **CSIS AMTI Woody Island** as *the* China-side imagery enrichment (×4), but `C/00`'s locked out-of-scope list excludes PLA reef/island basing and naval HHQ-9 — Woody Island (Paracels) is arguably exactly that. | `C/00` out-of-scope; `05:65,125-126,171,189-190` | Confirm whether Woody Island imagery is in-bound (capability-family depth) or out (naval/reef site); if out, name a replacement China-side imagery anchor before relying on it. |

**5.2.2 — Mechanical corpus/data fixes** `[agent]` (some gated on 5.2.1)

| # | Fix | Finding |
|---|---|---|
| F1 | **Repair the worked-query ground truth.** Rewire `answer_key.json` + generator edges to `C/01`'s grammar so every consecutive pair in `expected_path` is edge-connected (`manufactures` mfr→component, `variant-of` component→variant, `exported-by` import→mfr, keep `imported-by`/`based-at`); add an acceptance check that the path is fully traversable. Two of four hops don't exist today. | `06` H-CONSIST-1 |
| F2 | **Relabel HT-233 as chokepoint CANDIDATE** (`substitutability:'UNKNOWN'` + attached Known Gap); keep the `supplies-component` edge sourced, but move the sole-source *conclusion* onto a separate candidate overlay. In-degree-1 in a 14-doc hand-built graph is a coverage artifact, and confirming it contradicts `C/01`'s own sole-source honesty rule. Same edit pass as F1. | `06` M-INCONSIST-1 |
| F3 | **Add missing named designations to the §4 alias tables.** HQ-9 side: **Type 120, Type 305A/B, YLC-2V** (only HT-233/Type 233 present, `05:225`). S-400 side: **55K6E** (command post), **5P85** (TEL) — absent from `05:210-216`. `C/01` requires all as `model_designation` values. | divergence |
| F4 | **Give CASIC 2nd Academy a real §2 source entry.** It's the named `design-authority-for` anchor but appears only as a bare "CASIC/CPMIEC" label (`05:61`) with no URL/quote (contrast CPMIEC at `05:114`), and no `exported-by`/`design-authority-for` edge wires it into the graph. Source it, then wire the edges (part of F1). | divergence; `06` H-CONSIST-1 |
| F5 | **Name a real deep-tier sub-supplier + sub-tier parts.** `05:287-291` requires "one deep-tier supplier NAMED by a sanctions/export-control listing or tender" but names none; `C/00` cites **Taian/Wanshan** chassis and **seeker / GaN T/R modules / propellant / ICs / ceramics** as the sub-tier set — none in `05` (grep-empty). Pick a real named instance for the *confirmed* deep-tier chokepoint; leave the rest as candidates. | divergence; `05:287-291` |
| F6 | **Fix the corruption-operator claim + audit + d05.** Reword `05` §5 / generator header (and `DECISIONS.md`) from "applied programmatically / deterministic" to "named operators, prompt-steered from real specimens and manually audited post-freeze"; hand-audit the 14 frozen docs recording which operators landed per doc; lightly edit d05 to delete the in-line cover-story resolution so the declared-civil-vs-invoice contradiction is surfaced by the pipeline, not pre-resolved. | `06` M-DATA-1 |
| F7 | **Ground §5.1's other structural cases.** The substitutability story, adversary-denial case, unit-aliasing/MUCD case, and readiness-proxy case (`05:291-301`) are conceptual only — name a concrete instance/document for each, since `C/01`'s demo-scope subset requires one firing instance of each. | divergence |
| F8 | **Reconcile the HQ-9BE range figure.** `C/01` says ~250–300 km; `05:228` says 260–280 km. Pick one. | divergence |

**5.2.3 — Scenario ↔ flex bookkeeping** (reconcile the counting; do NOT change the body until picked)

- **§5 intro says "five graded scenarios" (`05:245`) but §5 lists six (`05:268-277`)**, and `C/02` counts the Rawalpindi observable as flex #6-of-6 while `DECISIONS.md` counts it separately — so "six" means two different things across docs. Pick one canonical statement (`06` L-CONSIST-1 suggests "8 seeded moments staged as 6 flexes").
- **Scenario 3 (contradicted pair) is orphaned** — no `C/02` flex cites it (flexes cite Scenarios 1,2,4,5,6). Stage it or drop it.
- **Flex 5 (freshness/stale) cites no scenario** — earmark a §5 scenario for the "2019/2016 imagery gone stale" beat (only Scenario 5's "gap" framing is near, and flex 2 already claims that).

**5.2.4 — Orphans: `05` content with no C home** (demote to "background / collection-context only" so the generator isn't tempted to seed from them)

- **Comtrade / TradeMap aggregate stats** (`05:58,87-89`) — no C node cites it; component-flow trend background only.
- **Russia zakupki + Rosoboronexport / Almaz-Antey S-400 procurement** (`05:108-113`) — supports S-400, which is design-note-reference only.
- **China CCGP / PLA portals** (`05:106-107`) — 05 itself flags these unreachable; `C/00` already predicts tier-2/3 naming stays open.
- **X / Telegram handle list** (`05:149-152`) — generic; tied to the orphaned Scenario 3.
- **NOTAM / NAVAREA strings** (`05:154-159`) — no C node consumes "exercise/test tempo" as a typed fact (nearest is `operational-status` readiness proxy, never wired).
- **§6 collection gotchas** (`05:307-316`) — ingestion-tooling notes; belong to `spine/02`, not C scoping.

> **Also corpus-level (handled at generation, not in this doc):** `06` L-CONSIST-1's cleanup sweep — off-ontology / misspelled type strings (`radar_command_node`, `sustenance_node`, `contract_import`), a stray third temporal field name (`evidence_date`), and a corpus doc missing its `manifest.jsonl` row.

**5.2.5 — Corpus needs from the resolution/assertion design** `[agent]` (per `08-spine-2.0-review.md` Part 2 §F;
scenario *needs*, not prescribed content — generator stays blind to the ontology, messiness preserved)

- **Orphan/thin-block alias case:** one component reported under a differently-worded name **not** in the
  seeded §4 alias table, so the LLM candidate-gen recall path (selective, offline proposer — spine/03) has a
  real orphan to demonstrate recovering.
- **Deterministically-detectable deception cluster:** near-duplicate text + timestamp ordering (the reshare
  cluster already at Scenario 4, `05:272-273`) so structural M4 detection fires off hash/timestamp/first-seen
  signals alone — no LLM, and the doc must not narrate the verdict (ties to D3/F6 above).
- **Adversary-denial case:** a claim denying a known dependency, or asserting a fake second source, to
  exercise the discount **gate** (adversary-denial excludes the claim from grouping — it is not a credibility
  multiplier); already tracked as part of §5.1's substitutability story (`05:294-295`) and F7's open
  grounding gap — this is the same instance, framed for the gate mechanism rather than duplicated.

---

## 6. Collection gotchas (for tooling)

- **Bot/geo-blocking:** The Diplomat, Stimson, Carnegie (Cloudflare/CloudFront), PIB, PPRA,
  `eng.mod.gov.cn`, `weain.mil.cn`, NGA MSI all `403`'d datacenter IPs → use a real headless browser +
  residential/in-country proxy, or capture manually.
- **Language:** CCGP, zakupki, `weain.mil.cn`, national AIS are native-language only → budget MT + a
  native-reader QA pass.
- **Best free raw grabs:** SIPRI (transfers), Russian zakupki FTP, NGA NAVAREA `.txt`, ImportYeti (US
  BoL). **Best format templates:** India MTD PDF (tenders) + NAVAREA/NOTAM strings (nav-warnings) +
  ImportYeti rows (customs).

---

## 7. One-line answer to "what can I actually get?"

For an **HQ-9/P (Pakistan)** anchor: **free & real** — SIPRI transfer record, ISPR/Quwa/Army-Recognition
text, CSIS AMTI + Google Earth/Wayback imagery, YouTube launcher footage, hand-copied 2025 social posts,
real NOTAM/NAVAREA strings, and the full alias mess. **Real-as-template** — customs manifests (ImportYeti
rows) and tenders (India MTD). **Not gettable (build synthetic, and say so):** the finished-system customs
trail for CN/RU/PK, and unit-level ORBAT tables (IISS paywall) — which is fine, because *the graded work
is the resolution, credibility, and confidence discipline, not the collection.*
