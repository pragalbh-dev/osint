# EVAL RCA handoff → DATA-C + EVAL: ground the answer_key to the corpus (analyst reasoning + exact edits)

> **STATUS — APPLIED to `answer_key.json` on branch `fix/answer-key-grounding-apply` (2026-07-19).**
> The DATA-C/EVAL edits below were executed by the grounding session at the user's direction (the
> ratified DATA/EVAL reconciliation — no *code* agent touched the oracle). What actually changed:
> - **D-G1 → decision A1 (remove).** Deleted the `mfr_casic --manufactures--> comp_ht233 (confirmed)`
>   edge. Chosen over re-typing to `design-authority-for` because the ontology locks that edge to
>   `techdata_authority → variant` — a manufacturer→component design-authority edge would be an ontology
>   contract change (widening domain/range, re-opening Phase-1 edge-uniqueness, pulling in INGEST). Removal
>   is ontology-clean: a manufacturer reaches a *component* only via `supplies-component` (a maker claim),
>   and CASIC isn't a confirmable maker — so it correctly has no direct radar edge. Also re-laned
>   `mfr_23rd_ri manufactures comp_ht233 (possible)` → `supplies-component (possible)`, and rewrote
>   `worked_query.expected_path` to **terminate at `comp_ht233`** (the chokepoint), with CASIC reached as
>   the program prime via `var_hq9p`. `expected_answer` was already honest → unchanged.
> - **D-G2 → applied.** The three `based-at` edges now carry `basis: "derived"` + explicit
>   `observed_layer` (equipment@site, imagery confidence) and `attribution_layer` (unit↔site, probable),
>   with notes. Graded `status` kept (Karachi confirmed-occupancy, Rawalpindi derived-stale, Rahwali
>   probable→confirmed) so the hero anchor + observable still work; `supersedes` marked derived-with-floor.
> - **D-G3 → applied.** `unit_paad` "regiment"→"unit/formation"; `unit_hq9b` name de-PAF'd + hedged
>   `operator_branch` note; `sustained-by` note flagging d06 is a PAF/system-level tender, not unit-specific.
> - **D-G4 → verified, no change.** Chokepoint stays `candidate`; confirmed no `foreign_control: true`
>   seed exists (`config/entities.yaml` explicitly defers it; `credibility.yaml` `gated_attrs` is the
>   mechanism, not a seed). Chaff scenario has 0 edges — nothing to change there.
>
> **DOWNSTREAM still open (this is what remains):** RESOLVE + SCORE must be able to *derive* what the
> softened oracle now expects — see `handoff-resolve-score-grounding.md`. **NEW coupling found:** the ASK
> hero-path **code** (`backend/chanakya/agent/loop.py::run_fixed_hero_path`, L167-174) is itself coded to
> the false narrative — it finds the chokepoint's maker via a `manufactures` edge and *defaults* `mfr_id`
> to `"mfr_casic"`, i.e. it will assert CASIC as the HT-233 maker. The ASK unit tests run against a
> self-contained fixture (`backend/tests/agent/fixtures.py`), not the oracle, so this edit does **not**
> break them — but ASK needs its own fix (find the maker via `supplies-component`, surface the Known Gap
> honestly, reach CASIC as prime). This overlaps the existing `handoff-ask.md` (Phase 4). Flagged there +
> in `handoff-resolve-score-grounding.md` §ASK-coupling.

**From:** grounding-audit session, 2026-07-19 (`fix/answer-key-grounding`, off `origin/main`).
**Owns:** **DATA-C** (answer_key content + corpus) and **EVAL** (oracle assertions). Per the working rule
and D-C, **a code agent must not edit `answer_key.json`** — this is the deliberate DATA/EVAL reconciliation.
**Reads:** `ANSWER-KEY-GROUNDING-AUDIT.md` (the full node/edge sweep this handoff acts on),
`../EVAL-RCA-corpus-grounding-basing-and-materiality.md`, `../PHASE1-DATAC-EVAL-answer_key-reconciliation.md`
(this handoff **supersedes** that doc's Item 1 — see Edit-1). **Decisions:** ratified with the user
2026-07-19; logged in `RCA-FIX-DECISIONS.md` (D-G1…D-G4).

**Why this exists.** The first end-to-end run flagged that some oracle expectations "cannot be made from
the data." That is **true for one edge and half-true for the basing cluster** — not for the key as a whole
(~85% is cleanly sourced). The fixes below are not cosmetic answer-tuning; they align the oracle with what
an intelligence analyst could *defensibly write down from these exact sources*. Do them, and the oracle
stops teaching the machine to make the very mistakes the scenario was designed to punish.

---

## 0. The analyst frame — the six tradecraft principles every edit below obeys

Read these first; each edit is just one of these applied to a specific claim. State them out loud on the
call — they *are* the "credibility, triage, adaptation" the take-home grades.

1. **Confirmed vs probable is a *sourcing* judgment, not a *plausibility* judgment.** A claim is
   "confirmed" when ≥2 **independent, cross-interest, discipline-diverse** sources carry it — not when it
   *sounds* right or an authority is *plausibly* responsible. "CASIC obviously makes the whole system, so
   it makes the radar" is plausibility masquerading as sourcing. That is the disqualifying failure mode.

2. **Export-agent ≠ manufacturer.** The single most common error in Chinese-SAM OSINT (d22, d23, d24 all
   call it out by name) is reading the entity that *sells/markets/integrates* a system as the entity that
   *builds* a sub-component. CPMIEC markets; CASIC/2nd Academy integrates; the HT-233's actual *maker* is
   **unknown**. An oracle that confirms "CASIC manufactures HT-233" commits this error in the gold data.

3. **Observed ≠ inferred.** Imagery yields *equipment at a place*. Attaching that equipment to a *named
   unit* is a **separate inferential hop** that must carry its **own, lower** confidence. Collapsing the
   two into one "confirmed" edge hides exactly the reasoning step a human analyst is supposed to audit.

4. **In this target set, basing is *never disclosed* — so it is *earned*, not *stated*.** d01, d02, d03,
   d17, d19 all say Pakistan publishes no ORBAT/basing. That is a *designed feature* of the scenario: every
   basing fact must be reconstructed from imagery + hedged formation hints. An oracle that demands a
   *stated* "unit based-at site" fact forces a fabrication — either the corpus grows a fake ORBAT line, or
   the machine invents the edge. Both are the failure we are removing.

5. **Absence of evidence ≠ evidence of absence.** d24's *"no open indication of a substitute chassis"*
   is **not** an assertion that no substitute exists — it is a collection gap. Confidence must not be
   manufactured from silence (this is why `foreign_control`/sole-source must not be hand-seeded).

6. **Corroboration must be independent.** Single-source, single-pass, aggregator-echoed, and
   aligned-interest signals do **not** confirm (d01 aggregator collapse, d15 aligned-interest, d18
   single-pass decoy cap, d20 rumor). The 2nd signal must be a *different discipline and a different
   interest* (d19's repeat-EO + ELINT is why Rahwali clears).

---

## Edit-1 — Remove the un-sourced `mfr_casic → comp_ht233` maker edge  [D-G1; supersedes prior Item 1]

**Analyst reasoning.** Principles **1 + 2**. The corpus does not merely *fail to state* that CASIC makes
the HT-233 — two grade-B references (d22 IISS, d24 CSIS) go out of their way to say the maker is **unknown**
and that asserting otherwise is "a hypothesis wearing a fact's clothing." What *is* sourced is that CASIC's
2nd Academy is the **program design authority / systems integrator** for the HQ-9 line. Those are different
claims at different tiers. The oracle currently states the *un-sourced* one at *confirmed*, and does so
while — three fields away — grading the same maker `unknown` and minting a `gap_ht233_maker`. Re-laning the
edge to `supplies-component` (the old Item-1 proposal) does **not** cure this: a *confirmed* CASIC→HT-233
supply edge under any name is still the export-agent/integrator being read as the component maker.

**Exact change (`answer_key.json`):**
- **Delete** the edge (currently L172-177):
  `{ "rel": "manufactures", "from": "mfr_casic", "to": "comp_ht233", "status": "confirmed" }`.
- **Keep** `mfr_23rd_ri --supplies-component--> comp_ht233 (possible)` and `gap_ht233_maker` — they already
  carry the "maker = candidate/gap" truth correctly. *(Note: the prior Item-1 also asked to re-lane
  `mfr_23rd_ri manufactures comp_ht233` → `supplies-component`; do that one — 23rd RI *is* a
  component-maker candidate, so `supplies-component (possible)` is the right lane + status.)*
- **Worked query** (L489-520): the final hop must no longer be `mfr_casic manufactures comp_ht233`. Rewrite
  the path so CASIC is reached as the *program* authority, and the HT-233 *maker* resolves to the gap:
  - `expected_path`: `[site_karachi, unit_paad, var_hq9p, comp_ht233]` then branch — the chokepoint
    terminates at `comp_ht233` (candidate); the "who makes it" answer resolves to `gap_ht233_maker`
    (candidate `mfr_23rd_ri`, possible), while `mfr_casic` is reached via `var_hq9p`
    (`comp_ht233 equips var_hq9p`, `mfr_casic manufactures var_hq9p`).
  - `expected_path_edges`: replace `{from: mfr_casic, rel: manufactures, to: comp_ht233}` with the
    program-authority hop `{from: mfr_casic, rel: manufactures, to: var_hq9p}` (confirmed) and, if you want
    the maker leg explicit, `{from: mfr_23rd_ri, rel: supplies-component, to: comp_ht233}` (possible).
  - `expected_answer` **already says this in prose** ("CASIC/2nd Academy is the confirmed program design
    authority; the specific HT-233 maker is a Known Gap") — no wording change needed; the path just has to
    stop contradicting it.

**Why this is *better analysis*, not just a fix:** the worked query's headline flex is "name the chokepoint
*and* be honest that its maker is a collection gap." Removing the edge is what lets the system *demonstrate*
that discipline instead of undercutting it.

---

## Edit-2 — Re-status the three `based-at` edges: observed-occupancy + derived unit-attribution  [D-G2]

**Analyst reasoning.** Principles **3 + 4 + 6**. No document states a *named unit at a named site*. Each
basing fact is a two-layer inference: (a) **equipment observed at a place** — a real imagery claim, at the
imagery's confidence; (b) **that equipment belongs to unit X** — a separate attribution off a *hedged*
formation reference ("reportedly part of PAAD Command"; "consistent with a PAAD deployment"). The oracle
must represent both layers, not collapse them into one "confirmed stated" edge. **Do not enrich the corpus
to make basing stated** (Principle 4 — it would contradict the scenario's own "basing never disclosed"
backbone). Soften the oracle; let RESOLVE/SCORE *derive* the unit→site edge (see `handoff-resolve.md`,
`handoff-score.md` SC-2/SC-4).

**Per-edge target (the "split" is in confidence, because all three are derived):**

- **`unit_paad --based-at--> site_karachi`** — d02 (ISPR names a PAAD unit + Karachi induction) + d07
  (HQ-9/P pad at Malir, multi-pass, "reportedly PAAD Command").
  → **occupancy: confirmed** (equipment@site, 4 passes). **unit-attribution: probable→confirmed** (strong:
  named unit + hedged imagery tie), but carried as a **derived** edge, not a stated one. Note d07's
  system-type ID is only MODERATE and "possibly not yet fully operational" — the *site's occupancy* is
  confirmed, the *"this is unit_paad's operational HQ-9/P battery"* is the inferred layer.
  → Add to the edge: `derivation: "equipment@site (d07 imagery) + formation-hint (d02 ISPR / d07 'reportedly
  PAAD')"`, and keep `confirmed_by: imagery`. Represent observed-vs-inferred explicitly (a `basis` field or
  a `note`), so the grader can see the two layers.

- **`unit_hq9b --based-at--> site_rawalpindi`** — d17 (multi-pass 2021, "HQ-9B battery element occupied").
  → **occupancy: confirmed (2021)** then **derived-stale** after the 2025 relocation. Keep `status: stale`,
  but annotate that stale is **inferred from the redeployment narrative (d19)** + freshness decay, **not**
  from any negative observation at Rawalpindi (no 2025 imagery shows Rawalpindi empty). This matters: the
  demo's honesty is that we degrade on *inference of movement elsewhere*, held against a spoofed reverse
  claim (d20), not on a confirmed vacancy.

- **`unit_hq9b --based-at--> site_rahwali`** — d18 (single-pass, decoy-flagged → **probable**) → d19
  (repeat-EO **+** ELINT emitter fix, distinct discipline + distinct interest → **confirmed**).
  → Keep the `probable → confirmed` arc; this is the flagship 2-independent-signal beat and is correctly
  grounded. Ensure the edge/observable records that the lift comes from a **discipline-independent**
  second signal (Principle 6), not a second look at the same pass.

- **`supersedes site_rahwali → site_rawalpindi`** — keep, but annotate it is a **derived state-change** off
  d19's *hedged* "recent redeployment," held at a **confidence floor** so the d20 single-source reverse
  rumor cannot flip it. This is already the `supersede_spoof` flex — just make sure the oracle's note frames
  supersede as derived-with-floor, not a stated fact.

- **`d20_supersede_spoof`** — no change; it must stay rumor-grade and must **not** downgrade a confirmed
  basing. (Already correct.)

**Net:** the three basing edges stay in the graph (the hero traversal still works — traversal is by node id,
bidirectional), but each now honestly shows *observed equipment* separated from *inferred unit-attribution*
at the confidence the sources support. The worked-query `must` ("separate observed from inferred") now
applies to basing, not only to chokepoint candidacy.

---

## Edit-3 — Cosmetic over-resolutions (hedge to what the docs state)  [D-G3]

Principle **3**, small scale. Grounded facts, over-precise labels:
- `unit_paad.name`: drop "regiment" → "Pakistan Army Air Defence — HQ-9/P **unit/formation**" (d02 says
  "unit"; d03 says "battalions"; no source says regiment).
- `unit_hq9b.operator_branch`: the imagery is Army-leaning/ambiguous (d18 "Pakistan Army Air Defence
  Command"; d19 "PAF/Army Air Defence Command"; d17 names no operator). Either hedge to
  `"PAF/Army (ambiguous in sources)"` or add a `note` recording the ambiguity. Keep the **variant** split
  (HQ-9/P→Army, HQ-9BE→PAF, d04) — that one is solidly sourced.
- `sustained-by unit_paad → sustain_spares`: d06 is a **PAF Air HQ** tender. Attach sustainment to the PAF
  unit (or leave unit-agnostic), not the Army `unit_paad`.

---

## Edit-4 — Materiality / chokepoint: NO answer_key change (config-side only)  [D-G4]

Principle **5**. The key **already** grades the chokepoint `candidate` (node L16, edge L183) — the honest,
corpus-supported status. Leave it. The only action is to **not** hand-seed `foreign_control: true` /
`SOLE_SOURCE` to force a CONFIRMED chokepoint (already reversed in D-C.1). If HT-233 should surface as
*material* at all, rest it on the **hedged** techdata-authority (d21) + no-open-substitute-chassis (d24)
axis at **probable**, hedges preserved. Owner for the config side: SCORE (`handoff-score.md` — do not retune
credibility). This handoff records it only so DATA-C/EVAL don't "fix" a status that is already right.

---

## Downstream coordination (so the softened oracle is actually *producible*)

Softening the oracle is only half the loop — the pipeline must be able to *derive* what the oracle now
expects, or the graph still won't match:
- **RESOLVE** (`handoff-resolve.md`, RES-1): must derive `unit --based-at--> site` from
  equipment@site + formation-hint claims, populating the unit-attribution as a derived edge with its own
  confidence. Must resolve the CASIC-via-program path (no direct CASIC→HT-233 edge to lean on anymore).
- **SCORE** (`handoff-score.md`, SC-2/SC-4): `based-at` half-life so Rawalpindi can go stale; synthesize
  `supersedes` with a confidence floor (d20 resistance); keep the 2-independent-signal gate for Rahwali.
- **EVAL harness:** switch the basing assertions to check *observed-occupancy status* and
  *derived-attribution status* as two fields (not one flat status). The `answer_key`-separation guard
  already passes; keep it green. Verify all edits against **all six graded scenarios**, not just the hero.

## Verification checklist for the owner
- [ ] `mfr_casic → comp_ht233` edge gone; `mfr_23rd_ri → comp_ht233` is `supplies-component (possible)`;
      `gap_ht233_maker` intact.
- [ ] Worked-query path no longer contains `mfr_casic manufactures comp_ht233`; prose `expected_answer`
      unchanged and now consistent with the path.
- [ ] Each `based-at` edge records observed-occupancy vs derived-unit-attribution at the confidences above;
      `d20` still rumor-grade; `supersedes` framed as derived-with-floor.
- [ ] Cosmetic labels hedged (regiment / unit_hq9b branch / PAF-tender-on-Army-unit).
- [ ] Chokepoint left at `candidate`; no `foreign_control` seed added.
- [ ] Re-run `rca_evidence.py`; re-check the six scenarios; `answer_key`-separation guard still green.
