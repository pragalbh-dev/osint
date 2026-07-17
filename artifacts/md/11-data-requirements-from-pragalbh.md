# 11 — Requirements from Pragalbh (data robustness)

**From:** autonomous session, 2026-07-17 · **For:** your ~6h-later review ·
**Companion:** `[10-data-generation-strategy.md](10-data-generation-strategy.md)`

Everything below is a thing **only you can do** (a login, a decision, or a manual grab). I've built and
generated everything that doesn't need you (see the session summary). Nothing sensitive needs to pass
through me — for each credentialed item you either run one step yourself or create a throwaway account and
drop files into `corpus/raw/<class>/`, then `python tools/gather/gather.py --reconcile`.

---

## A. Decisions I need from you (blocking full fidelity; I made a defensible default for each so nothing stalled)


| #   | Decision                                                                                                                                                                                                                                                                                                                               | My default (in effect now)                                                                                                                               | Why it's yours                                                                |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| A1  | **Imagery posture.** Imagery as analyst-report **text** (M4 = coordinated-inauthenticity + first-seen from text/timestamps), or wire ≥1 real VLM call on a real image?                                                                                                                                                                 | **Text posture** (per `H-DEVIATION-1` "lock the honest posture"). VLM = roadmap.                                                                         | Changes whether you must supply real images + a VLM budget.                   |
| A2  | **Which single sustainment node** for the demo: **Interceptor Stockpile & Resupply** (most observable, drives the follow-on-order secondary observable) or **Technical-Data/Software & Calibration Authority** (highest-leverage "invisible dependency")?                                                                              | **Tech-Data Authority** — it's the stronger chokepoint story and the "invisible dependency" is more novel; the stockpile observable is kept config-only. | Decides which secondary observable is live + which deep-tier doc I generate.  |
| A3  | **Cross-interest scope:** require cross-interest independence for **all** claims, or only for interested/contested classes (possession, performance, basing, sustainment-dependency, foreign-control) while neutral durable facts (design attribution, manufacture, lineage) accept 2 origin+discipline-independent aligned-bias refs? | **Contested-classes-only** (the `spine/04 ⚠` recommendation) — otherwise durable facts never confirm.                                                    | A credibility-model policy call with graded implications.                     |
| A4  | **Calibration constants sign-off:** `w_R`/`w_C` tables, `C_raw` 0.40/0.80 thresholds, `s_i≥0.50` floor, half-life defaults, and the **04-vs-08 reconciliations** (three-state+STALE vs five-state; the 0.40–0.50 band; freshness combine-order; conflicting half-lives; ICD-203 0.50-vs-0.55; δ contradiction window).                 | Using **08-canonical** math (cleaner noisy-OR form) with 04's gate list layered on; discrepancies listed in the strategy §2 source brief.                | Form is locked; numbers must be tuned on the frozen corpus and are your call. |
| A5  | **Supersede confidence-floor (D8 fix):** approve adding "a superseding claim must clear ≥1 independent probable-grade look before retiring a confirmed assertion."                                                                                                                                                                     | **Approved by default** and demonstrated both ways (attack succeeds without / held with).                                                                | It's a real design change to the resolver; you may want to see it first.      |
| A6  | **Order of the live-call flexes.**                                                                                                                                                                                                                                                                                                     | Left as the docs' "leaning" order.                                                                                                                       | Presentation call.                                                            |


If you disagree with any default, it's a one-line change in the relevant YAML — nothing is baked so deep
it can't be flipped.

---

## B. Logins / accounts — prioritized (each upgrades a reconstruction to raw real data)


| Pri   | Source                                               | Access                                                                   | Unlocks                                                                                                                                                             | How to hand off                                                                                                                                            |
| ----- | ---------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1** | **Copernicus Data Space**                            | **free signup**                                                          | Real Sentinel-2 optical of Rawalpindi + Rahwali + a **cloud-covered** frame (insufficient-evidence flex); satisfies the non-text-modality rule if you choose A1=VLM | create account → export frames → drop in `corpus/raw/imagery/`; or paste the browser URL and I script the pull                                             |
| **2** | **Google Earth Pro** (desktop)                       | **free**                                                                 | Sub-meter historical frames of **Rawalpindi & Rahwali** (the locked observable) + Karachi; VLM site-typing                                                          | screenshot export → `corpus/raw/imagery/`                                                                                                                  |
| **3** | **SIPRI Trade Register**                             | **no login** (the on-screen register is public; only the API needs auth) | Upgrades d01 from a *reconstruction* to **real register rows**; the China→PK HQ-9/P + China←RU S-400 rows                                                           | run the query in your browser (recipient=Pakistan, supplier=China; and recipient=China, supplier=Russia), export/copy, drop in `corpus/raw/arms_transfer/` |
| **4** | **Run `gather.py` on your machine** (residential IP) | none                                                                     | Auto-unblocks **ISPR, PIB, The Diplomat, NGA NAVAREA** in one pass (they 403 datacenter IPs)                                                                        | `python tools/gather/gather.py` on your laptop, commit the new `corpus/raw/` files                                                                         |
| **5** | **X / Twitter**                                      | free (manual) or paid API                                                | More real 2025 sighting posts → richer coordinated-inauthenticity burst (D2) and the recycled-image thread (D1)                                                     | paste real posts (handles in `05 §2.6`) into `corpus/raw/social/`                                                                                          |
| 6     | **YouTube**                                          | free (I can do it)                                                       | HQ-9 parade/TEL frame for VLM equipment-ID (only if A1=VLM)                                                                                                         | give me 1–2 video URLs; I'll add `yt-dlp` and extract frames                                                                                               |
| 7     | **ImportGenius / Volza / Zauba**                     | trial / paid                                                             | A real *defense-adjacent* BoL lane (electronics→Pakistan) as a richer customs template (D7)                                                                         | one export → `corpus/raw/customs/`                                                                                                                         |
| 8     | **IISS Military Balance**                            | subscription (if you have it)                                            | Real ORBAT unit counts as ground truth for the answer key                                                                                                           | table export/screenshot                                                                                                                                    |


**Highest leverage: #1–#4.** #1/#2 close the only true data gap (imagery). #3/#4 turn the two "MEDIUM"
sources (SIPRI, ISPR) into raw real. Everything text/structured is already real or real-from-template.

---

## C. What I could NOT do autonomously (and why)

- **Real satellite/ground imagery** — Copernicus needs an account; Google Earth is desktop; datacenter IP
can't drive them. → generated realistic analyst-report *text* per the A1 default; swap in real frames anytime.
- **Raw SIPRI register rows** — the export API 401s without a login. → used a sourced reconstruction; #3 fixes it.
- **ISPR / PIB / Diplomat / NGA raw fetch** — 403 to datacenter IPs. → reconstructions/mirrors; #4 fixes it.
- **The subject-proximity view-time filter** — this is a **pipeline build stage**, not data; choosing the
~40–50 corpus **promotes it from optional to required** to keep the canvas legible at ~20–30 chaff. I
built the distractors *low-proximity by design* so they sink even before the filter exists, but **this
belongs on the build ladder** (feed into `06-preflight-audit.md`). Flagging, not fixing (it's not data).

---

## D. Quick-start when you wake

1. Skim `[10-data-generation-strategy.md](10-data-generation-strategy.md)` §4 (the misinformation plan) and §6 (corpus realignment).
2. Answer A1–A2 (they unblock the most) — one line each.
3. Do B#1–#4 when you have 20 minutes (biggest fidelity jump).
4. Re-run: `python tools/gather/gather.py --reconcile && python tools/generate/generate.py <scenario>.yaml`.

