# Answer-key grounding audit — `hq9p_primary` (every node + edge vs the corpus)

**Author:** grounding-audit session, 2026-07-19. **Branch:** `fix/answer-key-grounding` (off `origin/main`).
**Scope:** does every assertion in `corpus/scenarios/hq9p_primary/answer_key.json` `ground_truth` (21 nodes,
22 edges) trace to a document that actually says it? Verified by direct read of all 25 primary-scenario
docs. **Extends** `../EVAL-RCA-corpus-grounding-basing-and-materiality.md` and
`../PHASE1-DATAC-EVAL-answer_key-reconciliation.md` — this is the complete node/edge sweep, and it
**corrects** one thing those got half-right (§A: re-laning the CASIC→HT-233 edge does not fix its
grounding) and one factual slip (§D: the key already grades the chokepoint *candidate*, not confirmed).
**Companion:** `handoff-answer-key-grounding.md` (the analyst-perspective owner handoff + exact edit spec).

**Verdict up front:** the answer_key is **not** "haywire." ~85% is cleanly grounded. There is **one
genuinely self-contradictory / un-sourced assertion** (§A), a **cluster of legitimately-derived basing
edges over-flattened to "confirmed stated"** needing honest labelling + calibration (§B), and a handful of
**cosmetic over-resolutions** (§C). Categories: **GROUNDED** (a doc states it) · **DERIVED-OK** (not stated
but a sound knowledge-layer inference the architecture is built to make) · **OVER-STATED** (grounded fact,
but status/label claims more than the evidence) · **UN-SOURCED** (no doc supports it; must fix).

---

## A. The one real defect — `mfr_casic --manufactures--> comp_ht233` (status: confirmed)  [UN-SOURCED]

`answer_key.json` edges L172-177. This is the assertion that "cannot be made from the data," and the
corpus **actively contradicts it**:

- `d22_deep_tier_supplier` (IISS, grade B): *"The manufacturer of the HT-233 should therefore be treated
  as unconfirmed/unknown pending better sourcing. Analysts and journalists who state 'CPMIEC makes the
  HT-233' are … conflating the export/sales agent with the producing entity."*
- `d24_tel_chassis_attribution` (CSIS, grade B): *"the manufacturer of the HT-233 engagement radar …
  cannot be established from open sources … one that fills the radar tier with the chassis tier's
  confidence … is a hypothesis wearing a fact's clothing."*

The answer_key **itself agrees** everywhere else: node `comp_ht233.manufacturer = "unknown"` (L18),
`gap_ht233_maker` exists (L58-63), and the worked-query `expected_answer` says *"the specific HT-233 maker
is a Known Gap."* So this one edge contradicts its own node, its own gap, its own worked answer, and two
grade-B sources. It is the textbook error the whole scenario was built to catch.

**Why re-laning alone (the prior reconciliation doc's Item 1) does not fix it.** That doc proposed
re-laning `mfr_casic manufactures comp_ht233` → `supplies-component`. But `mfr_casic supplies-component
comp_ht233 confirmed` is *still* un-sourced — CASIC still doesn't confirmably make the HT-233. The label was
never the problem; the **confirmed direct-maker claim** is.

**What the corpus *does* support** (so we don't over-correct): CASIC's 2nd Academy is the confirmed
**systems lead / design authority for the HQ-9 program** (d22 §3: *"the Second Academy … responsible for
HQ-9 system integration more broadly"*). That is a **program-level design-authority** fact, not a
**component-maker** fact.

**Decision (ratified with user 2026-07-19): REMOVE the edge (A1).** Delete `mfr_casic → comp_ht233`.
HT-233's only maker edges become `mfr_23rd_ri --supplies-component--> comp_ht233 (possible)` + the
`gap_ht233_maker` node. CASIC is reached from HT-233 via `comp_ht233 equips var_hq9p` + `mfr_casic
manufactures var_hq9p (confirmed)`. Update `worked_query.expected_path` + `expected_path_edges` final hop
accordingly (it currently encodes `mfr_casic manufactures comp_ht233`, contradicting its own
`expected_answer`). Details + exact rewrite in `handoff-answer-key-grounding.md` §Edit-1.

---

## B. Basing / relocation — `based-at` unit→site edges  [DERIVED-OK, but OVER-STATED as "confirmed stated"]

Edges: `unit_paad --based-at--> site_karachi (confirmed)`, `unit_hq9b --based-at--> site_rawalpindi
(stale)`, `unit_hq9b --based-at--> site_rahwali (confirmed)`; plus `supersedes site_rahwali→site_rawalpindi`.

**Corpus reality:** every basing doc states **equipment at a place** (an imagery sighting) + at most a
**hedged formation association** — never a named-unit-at-a-named-site basing fact:
- `d07_sat_confirm_karachi` — HQ-9/P petal pad at Malir/Karachi (multi-pass, 4 collects, MODERATE-HIGH),
  *"reportedly part of Pakistan Army Air Defence Command's continuing … buildout."* System-type ID
  MODERATE; *"possibly not yet fully operational."*
- `d02_ispr_induction` — names a **PAAD unit** and a **Karachi induction ceremony** — but the ceremony
  venue (Army Air Defence Centre) ≠ the operational Malir pad; no site coordinate.
- `d17_rawalpindi_2021` — *"an HQ-9B battery element occupied … at … PAF Base Nur Khan"* (multi-pass;
  equipment read, no unit designator).
- `d18_rahwali_pass1` — single-pass HQ-9B signature, decoy risk, *"consistent with a Pakistan Army Air
  Defence Command … deployment"* → probable.
- `d19_rahwali_confirm` — 2nd independent signal (repeat EO + ELINT); *"first collection cycle to
  **associate** a … HQ-9BE … battery **with** the location, consistent with a recent redeployment."*

**Assessment.** These edges are **legitimate knowledge-layer derivations** (resolve equipment-sighting +
hedged formation → unit, attach to site) — exactly what the bi-level architecture is for; **not
fabrications.** The problem is presentation: the oracle grades them as flat **stated** facts at
**confirmed**, when the honest split is **observed equipment@site (imagery confidence) + unit↔site
attribution (derived, at the confidence the hedge supports).** The corpus's *own* repeated theme — Pakistan
never discloses basing/ORBAT (d01, d02, d03, d17, d19) — means every basing fact here is *meant* to be
earned from imagery, not stated. So **do not enrich the corpus to make basing a stated fact** (that would
contradict the scenario's backbone and re-introduce teaching-to-the-test). **Soften all three** to
observed + derived, at per-edge confidence.

**Decision (ratified with user 2026-07-19): SOFTEN all three (B1), split by confidence not by
enrich-vs-soften.**
- **Karachi** — occupancy confirmed (4 passes) + unit-attribution strong (ISPR unit + hedged "PAAD
  Command" in imagery). Show observed-vs-inferred; type-ID is only MODERATE in d07.
- **Rawalpindi** — confirmed occupancy 2021 (multi-pass) → derived-stale after relocation (no negative
  observation at Rawalpindi exists; stale is inferred from the redeployment narrative).
- **Rahwali** — probable on single pass → confirmed via the 2-independent-signal gate.
- Keep `d20` rumor-grade — must **not** flip a confirmed basing.
Exact per-edge rewrite in `handoff-answer-key-grounding.md` §Edit-2. Downstream: RESOLVE/SCORE own the
*derivation* of these edges (see `handoff-resolve.md`, `handoff-score.md` SC-2/SC-4).

---

## C. Cosmetic over-resolutions  [OVER-STATED, low severity — flag, don't block]

- **`unit_paad.name = "…HQ-9/P regiment"`** — d02 says "unit" / "newly raised/re-equipped unit"; d03 says
  "battalions." "Regiment" is a formation level the corpus never states. → "unit/formation."
- **`unit_hq9b.operator_branch = "Pakistan Air Force"`** — corpus is genuinely **ambiguous/Army-leaning**:
  d18 *"consistent with a Pakistan Army Air Defence Command … deployment,"* d19 *"PAF/Army Air Defence
  Command HQ-9BE,"* d17 site is "PAF Base Nur Khan" but names no operator. The key cleanly assigns PAF
  (inherited from `var_hq9be`). Variant-level Army/PAF split (d04) is solid; the *unit's* branch is
  over-resolved from ambiguous imagery. → hedge the unit's branch or note the ambiguity.
- **`sustained-by unit_paad → sustain_spares`** — the spares tender `d06` is a **PAF Air HQ** tender;
  attaching its sustainment to the **Army** `unit_paad` is a minor operator mismatch. → attach to the PAF
  unit or keep unit-agnostic.

---

## D. Everything that IS cleanly grounded (the ~85% — do not touch)

| Assertion | Status in key | Grounding |
|---|---|---|
| `mfr_casic manufactures var_hq9p` / `var_hq9be` | confirmed | d01/d02/d04/d21/d24 — CASIC develops HQ-9 family |
| `mfr_taian supplies-component comp_tel_chassis` | confirmed | d24 directly names supplier+component+relationship, multiply attested |
| `comp_tel_chassis equips var_hq9p` | confirmed | d24/d25 — TEL chassis integral to HQ-9/P |
| `comp_ht233 equips var_hq9p` (chokepoint candidate) | confirmed / candidate | d07/d17/d21/d23 — HT-233 is HQ-9/P engagement radar; **candidate is honest** |
| `comp_interceptor equips var_hq9p` | confirmed | d21/d22/d23 — the interceptor round |
| `mfr_23rd_ri supplies-component comp_ht233` | possible | d22/d24 — plausible-not-confirmed candidate maker |
| `mfr_4th_academy supplies-component comp_interceptor` | possible | d22 — plausible SRM house, unconfirmed |
| `design-authority-for sustain_techdata → var_hq9p` | probable | d21 — hedged techdata/config-control dependency |
| `distinct-from var_hq9p ↔ var_hq9be` | confirmed | d04 — 125 km Army vs 260 km PAF (flagship) |
| `same-as FD-2000 → var_hq9p` | confirmed | d03 — export alias = HQ-9/P |
| `distinct-from alias_ft2000 ↔ var_hq9p` | confirmed | d04/d23 — FT-2000 anti-radiation, false-merge trap |
| `import_2021` + `exported-by`/`imported-by` | confirmed | d01 (SIPRI) + d05 (customs) + multiple third-party |
| `inducted-into var_hq9p → unit_paad` (2021-10-14) | confirmed | d02 states it directly |
| `gap_ht233_maker`, `gap_launcher_count` | known_gap | d22/d24 (maker unknown) · d01/d02/d17 (count never disclosed) |
| chokepoint = **candidate** (node + edge) | candidate | **already honest** — corpus supports candidacy, not a confirmed sole-source |

**Materiality note (reconciles prior Item 2 + DC-3):** the answer_key **already** grades the chokepoint
`candidate` (node L16 + edge L183) — the honest, corpus-supported status. The corpus never states
sole-source / foreign-control (d22: maker UNKNOWN; d21/d24 support only a *hedged* techdata-authority /
no-open-substitute axis). So **no answer_key change is needed for chokepoint status.** The prior doc's
claim that the key grades HT-233 a "confirmed chokepoint" is a slip — it says candidate. The only
materiality fix is config-side: **do not seed `foreign_control: true` to force CONFIRMED** (already
reversed by D-C.1). If HT-233 should surface as *material* at all, rest it on the hedged techdata-authority
(d21) + no-open-substitute-chassis (d24) axis at **probable**, hedges preserved — never confirmed.

---

## E. Fix ledger (what changes, who owns it)

| # | Item | Category | Fix | Owner | Status |
|---|---|---|---|---|---|
| A | `mfr_casic manufactures comp_ht233 confirmed` | UN-SOURCED | Remove edge; reach CASIC via program; fix worked-query hop | DATA-C + EVAL | ratified → handoff |
| B | 3× `based-at` unit→site "confirmed stated" | DERIVED / OVER-STATED | Soften to observed@site + derived unit-attribution at per-edge confidence | EVAL (oracle) + DATA-C; RESOLVE/SCORE derive | ratified → handoff |
| C | regiment / PAF branch / PAF-tender-on-Army-unit | OVER-STATED (cosmetic) | Hedge labels to what docs state | DATA-C | handoff |
| D | chokepoint = candidate; foreign_control seeds | — | Answer_key already honest; only ensure no foreign_control seed forces confirmed | SCORE config | no change (D-C.1) |
