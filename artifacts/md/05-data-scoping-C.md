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
