# 04 · The scenario — concrete entities, alias map & document index

**For:** the design collaborator. **Companion to** `01-entities-and-relationships.md` (which is the
*type-level* vocabulary). This doc is the **actual instances the demo runs on** — the ~15 real entities,
the alias/merge traps, the two site threads, and every source document — so you can design against real
content, not placeholders. Everything here is the **frozen ground truth** for the demo scenario; it won't
change under you.

---

## 1. The entities (the ~15 nodes actually on the graph/map)

| # | Name | Type | Status | Key attributes |
|---|---|---|---|---|
| 1 | **CASIC** (China Aerospace Science & Industry Corp) | Manufacturer | confirmed | export agent = CPMIEC |
| 2 | **HT-233 engagement radar** | Component | confirmed | `functional_role = engagement/fire-control`; **chokepoint = CANDIDATE**; **substitutability = UNKNOWN** |
| 3 | **HQ-9-family interceptor round** | Component | confirmed | `functional_role = interceptor` |
| 4 | **Technical-Data / Software & Calibration Authority** | Sustainment | **probable** | the *invisible* dependency (controls software/calibration); a second **candidate chokepoint** |
| 5 | **Spares / maintenance tender implication** | Sustainment | **probable** | single-source tender → implies, never confirms |
| 6 | **HQ-9/P** | Variant | — | Pakistan **Army**, ~125 km; aliases **HQ-9P, FD-2000** |
| 7 | **HQ-9BE** | Variant | — | Pakistan **Air Force**, ~260 km |
| 8 | **FT-2000** | Variant | — | anti-radiation system — **DISTINCT-FROM HQ-9/P** (the false-merge trap) |
| 9 | **China→Pakistan HQ-9/P transfer** | Contract/Import event | confirmed | 2021 |
| 10 | **Pakistan Army Air Defence — HQ-9/P regiment** | Unit | confirmed | inducted 2021-10-14 |
| 11 | **PAF HQ-9B fire-unit** | Unit | confirmed | the **relocation subject** |
| 12 | **Karachi (Army Air Defence Centre area)** — *"Site K"* | Basing site | **confirmed** | confirmed by imagery (2022); the hero-query battery site |
| 13 | **Rawalpindi garrison site** | Basing site | **stale** | occupied 2021 (confirmed) → stale after the 2025 relocation |
| 14 | **Rahwali site** | Basing site | **confirmed** | 2025 relocation destination: probable (single pass) → confirmed (2nd signal) |
| 15 | **TEL / battery count** | Known Gap | — | `observability_ceiling = probable-max` — never disclosed by Pakistan |

---

## 2. The alias & merge map (design the merge cards around these three)

Full alias set in play: **HQ-9/P · HQ-9P · HQ-9BE · FD-2000 · FT-2000 · HT-233 · HHQ-9 · 红旗-9.**

| Case | Relationship | What the review queue should do |
|---|---|---|
| **FD-2000 ↔ HQ-9/P** | `same-as` (**auto-merge**) | FD-2000 is just the export/marketing name for HQ-9/P → merges automatically, high confidence. |
| **HQ-9/P ↔ HQ-9BE** | `distinct-from` (**flagship trap**) | Look-alike names, *one import, two service variants* (Army ~125 km vs PAF ~260 km) → lands in the HITL band → analyst keeps them **separate**. |
| **FT-2000 ↔ HQ-9/P** | `distinct-from` (**the classic trap**) | FT-2000 is a *different* (anti-radiation) family that shares product-family literature → lands in the HITL band → **do NOT merge**. |

> **On "no FT-2000 source" (design team's note):** there is one — it's in **`d04_armyrec_ranges.txt`**
> (which you didn't have; you only had 3 of the docs). It states FT-2000 is a CASIC anti-radiation
> derivative that Pakistan is *not confirmed* to operate, and is confused with HQ-9 only in trade-family
> literature. `d01_sipri_transfer.txt` also explicitly flags "NOT the same system as the FT-2000." That's
> the raw material for the `distinct-from` trap.

---

## 3. The two threads (the demo has two, and they use different units)

**Thread A — the supply-chain trace (the hero query).** *"Trace the HQ-9/P battery at Karachi back to its
component supplier and name the chokepoint."* Site "K" = **Karachi** (not Kirana Hills — see the note
below). The hop path:

`site_karachi` —(`based-at`, **confirmed**, imagery)→ `unit_paad` —(`inducted-into`/`imported-by`,
**confirmed**)→ `import_2021` —(`exported-by`)→ `CASIC` —(`supplies-component`)→ **`HT-233` radar**.

**The chokepoint answer — this is the Q1 catch, and it's important you get it right:**
The HT-233 is a **CANDIDATE** chokepoint, **not** a confirmed sole-source. Its `substitutability` is
**UNKNOWN** (topology *nominates* it — it's the only supplier visible in open sources — but no evidence
proves no second supplier exists). So the honest demo answer is:

> *"Observed: the battery is at Karachi (imagery, confirmed). Inferred: the HT-233 radar is the **candidate
> chokepoint** — the only supplier visible in open sources — **but whether it is truly sole-source is a
> Known Gap (substitutability UNKNOWN)**, not a confirmed single point of failure."*

Rendering it as a flat "the weak link is the radar" **would break our own rule** (asserting sole-source
from absence of evidence). The candidate-plus-Known-Gap framing is actually the stronger, more on-brand
beat. (There's a *second*, "invisible" candidate chokepoint too: the **Tech-Data/Software Authority**,
`design-authority-for` HQ-9/P, held at **probable** — the dependency the OEM keeps after the sale.)

**Thread B — the relocation tripwire.** A **different** unit (the PAF **HQ-9B** fire-unit, not the Karachi
HQ-9/P regiment) moves **Rawalpindi → Rahwali** in 2025 (Base A = **Rawalpindi**, Base B = **Rahwali** —
note the direction; the design-team note had it reversed):

- `d17` — HQ-9B **confirmed** at Rawalpindi (2021 imagery, multi-source).
- `d18` — a **single** 2025 pass shows the signature at Rahwali → **probable** only (decoy cap on one look).
- `d19` — a second, independent signal → **confirmed** at Rahwali.
- `supersedes` retires the Rawalpindi position → it degrades to **stale** (superseded, *not* contradicted).
- `d20` — a single low-credibility post then claims the unit *left* Rahwali → a spoof the confidence floor
  must resist.

> **Site K vs. Kirana Hills:** "Site K" = **Karachi**, the imagery-confirmed hero-query battery site.
> **Kirana Hills / Sargodha** is a *different* thing — it appears in the `d05` customs annex as the
> supply-chain *end-customer formation* for the radar sub-components, not the hero battery site. Easy to
> conflate; they're distinct.

---

## 4. Document index (the full source corpus, in `reference/corpus/`)

The demo runs on ~23 primary documents (you had 3). Each is one messy open-source "document." **Bold** =
the core demo-scope beats.

| Doc | Source type | What it establishes / its role |
|---|---|---|
| **d01_sipri_transfer** | curated register (SIPRI) | The China→Pakistan HQ-9/P transfer. *Aggregator trap:* SIPRI compiles press, so its apparent multiple sources collapse to **one** origin group. |
| **d02_ispr_induction** | official (ISPR) | HQ-9/P inducted into the Army unit, 2021-10-14. Operator-state bias. |
| d03_quwa_analysis | trade press (Quwa) | Analytic corroboration of the induction/holdings. |
| **d04_armyrec_ranges** | trade press | HQ-9/P ~125 km (Army) vs HQ-9BE ~260 km (PAF); **the FT-2000 distinct-from source**. |
| **d05_customs_manifest** | customs record | Radar (HT-233) sub-components China→Pakistan; end-user Kirana Hills/Sargodha; **entity name-variants** (merge material). ⭐read-first |
| d06_spares_tender | tender (DGDP) | Spares/maintenance → sustainment; single source → stays **probable**. |
| **d07_sat_confirm_karachi** | imagery report | HQ-9/P pad signature at Karachi → `based-at` **confirmed**. ⭐read-first |
| **d08_social_sighting** | social | Claims active convoy near Karachi 2025-05-09 → **contradicts d09** (same time). |
| **d09_official_routine** | official | Frames the same 2025-05-09 activity as "routine training" → **contradicts d08** → HITL. |
| **d10_sat_cloud_gap** | imagery | ~95% cloud → **insufficient evidence** for launcher count; names missing slot + next coverage. |
| **d11_recycled_image** | social | 2019 parade photo reposted as 2025 Rahwali deployment → **integrity/recycled-media**. ⭐read-first |
| **d12_reshare_a** | social | Near-identical reshare of d11 minutes later → **echo-burst**, collapses into d11's origin group. |
| **d13_reshare_b** | social | Second reshare, same burst → coordinated-inauthenticity → **too-clean penalty** on the cluster. |
| d14_stale_holding | reference | A 2016 China-HQ-9 holding printed as current → decays → **probable (stale)**. |
| d15_globaltimes_aligned | state media (aligned) | Aligned-interest with the operator → **fails cross-interest** independence (not real corroboration). |
| **d16_adversary_denial** | official (adversary) | Asserts a fake "second source" + denies the tech-data dependency → **discounted as a gate**, never counted. |
| **d17_rawalpindi_2021** | imagery | HQ-9B **confirmed** at Rawalpindi, 2021 (relocation "before"). |
| d17b_withheld_gap | imagery | No TELs at a suspected forward site → **negative observation** (absence-as-evidence Known Gap). |
| **d18_rahwali_pass1** | imagery | Single 2025 pass at Rahwali → **probable** (decoy cap). |
| **d19_rahwali_confirm** | reference/ELINT | 2nd independent signal → Rahwali **confirmed** → `supersedes` Rawalpindi. |
| **d20_supersede_spoof** | social | Single low-cred post claims the unit *left* Rahwali → the **spoof** the floor must resist. |
| d21_techdata_authority | reference | The Technical-Data/Software authority → the **invisible** chokepoint candidate. |
| d22_deep_tier_supplier | trade-monitoring | A tier-3 TWT module (Nanjing Yuzhi) for the HT-233, on a **single uncorroborated manifest** → stays a candidate. |

**Chaff examples** (a few representative ones are in `reference/corpus/` too, prefixed `cd`/`cs`/`cx`).
The full corpus also has ~27 "chaff" documents — wrong systems (S-400, HQ-16), civilian noise, rumors,
entity collisions — that the system must **down-rank, not delete** ("the grain in the chaff"). You don't
need all of them; the 3 included show the noise types the credibility/filtering UI has to survive.

*(Not shared: the scenario's `answer_key.json` — that's the internal eval ground truth this doc is
distilled from. Ask Pragalbh if you ever want to see it.)*
