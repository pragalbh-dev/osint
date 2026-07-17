# Corpus Sizing — HQ-9/P OSINT Demo

**PURPOSE.** Derive a defensible total document count for the HQ-9/P demo corpus from coverage
requirements, a triage-realistic signal/noise model, and the UI-legibility + build-cost ceilings — and
state exactly what re-derives the number if scenarios or the noise ratio change.

*Working design doc. Dated 2026-07-16. Supersedes an earlier draft that recommended ~38 docs; that draft's
method survives, its headline does not — see §8.*

---

## 0. DECISION (2026-07-16) — target ≈ 40–50, above the computed floor

**Chosen: a ~40–50-doc corpus** (S ≈ 20 signal, N ≈ 20–30 chaff), selected over the ~24 mechanism-minimum
floor this document derives below. Rationale: the extra chaff is a **deliberate triage-depth choice** — it
makes "finding the grain in the chaff" non-trivial and turns the **relevance funnel itself into a
demonstrated graded capability** (the system ingesting ~2× more than it surfaces, with the proximity +
credibility layers visibly filtering the assessed view down to ~15–30 entities). This is the "richer triage
realism" option, not the minimalist floor.

**How to read the rest of this doc under the decision:**
- **§1–§8 derive the floor (~24) and remain valid as the *minimum core*.** Build that core first (14 frozen
  + the ~8–12 audit-mandated signal/relocation/structural docs) — it is **batch 1** and alone yields a
  complete, legible demo.
- **The gap ~24 → 40–50 is a batch-2 distractor/echo/stale *depth layer*** (~16–26 net-new noise docs),
  added deliberately to stress the triage funnel — **not** because coverage requires it. Signal (S) does
  **not** grow; only chaff does.
- **This deliberately overrides the doc's own noise rule:** §4 sizes chaff mechanism-first (~2/class ⇒
  ~9–11) and reports S/N ≈ 2:1. The decision moves *above* that minimum toward a volume-leaning S/N ≈
  1:1–2:3, re-accepting the "signal-proportional" framing for the batch-2 layer specifically — as a
  showcase choice, eyes open.

**Consequence the decision makes load-bearing (important):** §5 flags that the assessed-view legibility
guarantee at higher doc counts is **conditional on the subject-proximity view-time filter**, which is *not
yet a scheduled build stage*, and it caps distractors at 2–3 precisely to avoid depending on it. **Choosing
~40–50 promotes that filter from optional to a required build item** — with ~20–30 chaff you cannot keep
the canvas legible by hand-construction; the proximity + credibility funnel must actually work. Net: the
relevance funnel moves onto the critical build path (feed this into `06-preflight-audit.md`'s build ladder),
and every added sustainment-touching doc still needs the §5 chokepoint-topology check against the cached
hero trace before freezing.

---

## 1. Question + answer

**Q: How many documents should the frozen HQ-9/P corpus contain?**

**A: ≈ 22–26 total, headline ≈ 24** — built from the corpus that already exists (14 docs, `corpus/scenarios/hq9p_primary/docs/d01–d14`) plus a bounded, audit-gated expansion. This is a **net-new addition of roughly 8–12 docs**, not a from-scratch build, and not the ~38 a naive signal-proportional noise rule would produce (§4, §8).

---

## 2. The algorithmic sizing rule

```
corpus_size = S + N
S = coverage-driven signal count      # every scenario/query/flex requirement-cell needs
                                       # ≥1 supporting doc, after hub-doc sharing (§3)
N = mechanism-driven chaff count      # ≈ 2 examples × {echo, distractor, stale} classes,
                                       # NOT a fraction of S (§4)
```

**Correction adopted from the adversarial critique (adopted in full):** the model draft's original rule,
`corpus_size = S / φ` with target signal fraction `φ ≈ 0.60` (equivalently `N = S·(1−φ)/φ`), is rejected.
That rule treats noise as *signal-proportional* — appropriate for real-world S/N framing, wrong for a
demo whose chaff exists to **demonstrate specific triage mechanisms**, not to simulate realistic volume. A
100-signal-doc corpus needs the same handful of chaff examples as a 20-signal-doc corpus to prove the
too-clean detector, the proximity filter, and the freshness decay each fire once. **N is therefore sized
per-mechanism (≈2 examples/class ⇒ N ≈ 7–9), then the resulting ratio is *reported*, not asserted as a
target.** This is the single largest correction in this document; everything below follows from it.

---

## 3. Signal-doc derivation

Signal count is **coverage-driven**: every scenario, worked query, demo flex, and structural-case
requirement-cell needs at least one supporting document, but hub documents are reused across many cells
(SIPRI-1 / ISPR-1 / QUWA-1 each answer 3–4 cells), so signal count stays far below a naive
one-doc-per-cell sum.

**Correction adopted:** the model draft's S = 21–26 counted several docs as "fixed baseline" that do not
exist and that `06-preflight-audit.md` explicitly flags as unstarted or mis-scoped:

| Doc cited as baseline | Actual status (per `06-preflight-audit.md`) | Disposition |
|---|---|---|
| `FT2000-1` | Appears in **zero** of 14 docs; audit (H-CONSIST-3) recommends demoting to a **design-note example**, not authoring a doc | Dropped from signal count |
| `DEEPTIER-1`, `ALT-SUPPLY-1`, `ADV-DENIAL-1`, `UNIT-ALIAS-1`, `READINESS-1` | Conceptual only — "name a concrete instance" is unstarted work (audit F5/F7) | Only counted where the `[needs Pragalbh]` decision to build them is affirmed |
| `RUSI-1`, `JANES-1` | Live in `corpus/raw/reference/` as **template PDFs**, not extracted scenario docs | Not counted as corpus docs (they're generator templates) |
| `CPMIEC-BROCHURE-1` | CASIC/CPMIEC has **no real source entry** yet (audit F4) | Counted only once authored |

**Corrected signal table:**

| Bucket | Docs | Status | Basis |
|---|---|---|---|
| Existing signal core | **8** | Frozen (d01–d08) | SIPRI transfer, ISPR induction, Quwa analysis, ArmyRec ranges, customs manifest, spares tender, sat-confirm Karachi, social sighting |
| Existing triage substrate (dual-purpose: also signal for their own scenarios) | **6** | Frozen (d09–d14) | Contradictor, cloud/stale gap, M4 parade origin + 2 echoes, stale holding — these already carry corroboration/staleness/deception material, not pure filler |
| Relocation observable (Rawalpindi→Rahwali) | **+2 to 3** | `[needs Pragalbh]` — audit H-CONSIST-2, locked as marquee but unseeded | 2021 occupied-Rawalpindi doc + single-pass probable Rahwali doc [+ optional 2nd-independent confirmer] |
| Deep-tier / sustainment / structural-case docs | **+1 to 2** | `[needs Pragalbh]` — audit F5/F7, gated on whether these are affirmed for build | Tech-Data-Authority or one named tier-2/3 supplier, if kept |
| **Signal subtotal (S)** | **18–22** (headline **20**) | | Existing 14 + audit-mandated additions only |

Signal remains **heavily shared, not additive**: the 14-doc frozen core already answers all six graded
scenarios plus the worked query plus the spares tender and social-sighting flexes — the audit confirms
"every one of the 6 graded scenarios + the worked query + spares tender + social sighting is already
exercised at n=14." The marginal signal docs above exist to seed the **relocation observable** (currently
zero seed data per H-CONSIST-2) and to close a small number of `[needs Pragalbh]`-gated structural gaps —
not to re-cover material the corpus already handles.

---

## 4. Noise model + chosen ratio

### Why chaff exists (unchanged from the model draft)

The brief grades "finding the grain in the chaff" and keeping an analyst in the loop. A 100%-signal corpus
gives the credibility soft-filter, the subject-proximity layer, the too-clean/M4 detector, and the HITL
alert-disposition queue nothing to act on — chaff is the substrate these mechanisms demonstrate against,
not optional realism.

### Correction adopted: chaff count is mechanism-driven, not ratio-driven

The model draft sized noise as `N = S·(1−φ)/φ` at `φ≈0.60`, yielding **N≈15** at S=23. The adversarial
critique's correction is adopted: **the number of noise docs needed is set by how many mechanisms must be
shown non-trivial, roughly 2 worked examples per class, and is largely independent of S.** A larger signal
set would need the *same* handful of chaff docs, not a proportionally larger pile.

**Second correction adopted: most of the needed chaff already exists.** The frozen 14-doc corpus already
contains its own triage substrate — d09 (contradictor), d10 (cloud/stale gap), d11 (M4 parade origin),
d12+d13 (echo reshares), d14 (stale holding). The honest accounting is "~7–9 chaff docs needed per
mechanism, of which **6 are already frozen**":

| Class | Mechanism it exercises | Already frozen | Net-new needed | Headline net-new |
|---|---|---|---|---|
| **Echoes** (coordinated-inauthenticity) | Too-clean penalty / corroboration-collapse (M4) | d12, d13 (2 reshares of d11) | +1–2 (push the surface-count a bit further, not to the model draft's 5–6) | **+2** |
| **Distractors** (off-topic / low-cred) | Subject-proximity filter + credibility floor | **0** — audit confirms zero pure off-subject distractors exist today | +2–3 (enough to show the filter fire twice, not 8) | **+2 to 3** |
| **Stale** (superseded) | Freshness decay | d14 (stale holding), d10 (cloud/stale gap) | +0–1 (mostly covered) | **+0 to 1** |
| **Noise total (N)** | | **6 existing** | **+3 to 5** net-new | **≈ +4** net-new |

**Resulting ratio (reported, not targeted):** at S≈20 (headline) and N≈9–11 total chaff (existing +
net-new), the corpus lands at S/N ≈ 2:1, φ ≈ 0.65–0.70 — near, not identical to, the model draft's 0.60,
and arrived at from the opposite direction (mechanism coverage first, ratio observed after).

### The 8-distractor line item is dropped

The model draft's 6–9 distractors (headline 8) is the single most over-provisioned line: it triples an
empty class, taxes 4-day authoring/verification hardest, and — per the legibility argument below — leans
on a filter stage that is not yet a scheduled build item. 2–3 net-new distractors is enough to demonstrate
the mechanism once and hold one in reserve; it is not enough to demonstrate it *repeatedly*, which is an
acceptable minor under-provisioning for a demo (show once, one spare).

---

## 5. UI-legibility argument

Corpus size can grow ahead of the visible canvas because three relevance layers (`spine/02`) sit between
raw docs and the subject-lens view:

1. **Ontology-typing at extraction (hard)** — a doc with none of the ontology's types yields no claims.
2. **Subject-proximity at scoping (soft, view-time)** — entities >N hops from the HQ-9/P anchors exist in
   the graph but sit outside the subject lens, off-canvas.
3. **Credibility at scoring (soft)** — low-credibility/un-corroborated claims sink below the confidence
   floor; they render as sunk evidence, not confirmed/probable nodes.

Echoes resolve onto their origin claim (raising a source count, adding zero nodes); stale docs attach as
`supersedes`-retired evidence on existing nodes. Net: chaff mostly does **not** inflate the visible
knowledge layer.

**Estimated visible entities at corrected S≈20:** manufacturers/design bureaus (2–3) + components (3–5) +
variants (2–3) + contract/import events (2) + units (2) + basing sites (2–4, incl. the relocation pair) +
sustainment node (0–1) + Known Gaps (2–3) ≈ **16–24 visible entities** — inside, not at the ceiling of,
`07-stack.md`'s **~15–25 entity** NetworkX-rebuild target for the "calm, dense finance-terminal" aesthetic.

**Correction adopted — the legibility guarantee is conditional, and this document says so plainly.** The
adversarial critique identifies that step 2 above (subject-proximity **view-time filtering**) is **not
currently a scheduled build stage** in `07-stack.md`'s ladder (render raw scored graph → drawer → Ask →
HITL → relocation). Until that filter is built, any distractor entity that extracts either (a) lands on
the canvas, pushing past the entity budget, or (b) must be manually excluded from the corpus, in which
case it demonstrates nothing. **This is why net-new distractors are capped at 2–3, not 8**: at 2–3, a
canvas leak is a tolerable, easily-hidden edge case; at 8, it is a visible legibility failure and an
unanswerable "show me the filter" question on the call. Building the proximity-lens filter (or explicitly
descoping it and keeping distractors off-canvas by corpus design, not by mechanism) is a prerequisite this
document surfaces but does not resolve — it belongs with the `[needs Pragalbh]` build-ladder items in
`06-preflight-audit.md`.

Chokepoint-topology caveat carried from the critique: adding any doc that introduces a second supplier
path for HT-233 changes the marquee chokepoint finding (currently CANDIDATE per `M-INCONSIST-1`'s
correction), not just canvas size. New signal or noise docs touching the sustainment subgraph must be
checked against the cached hero trace before freezing.

---

## 6. Build / runtime / timeline sanity

- **Extraction is offline and frozen** (`07-stack.md`; audit M-BUILD-3) — a one-time build-time pass per
  doc, then the claims log is loaded verbatim. Corpus size is a data-prep cost incurred once, never a
  runtime cost.
- **`rebuild()` is in-memory NetworkX**, sub-millisecond at ~20–25 entities regardless of whether the
  underlying doc count is 14 or 26. Corpus size imposes no runtime latency ceiling.
- **The binding constraint is 4-day solo authoring + verification**, not runtime. Per `06-preflight-audit.md`,
  every doc — signal or noise — needs a `manifest.jsonl` row, a corruption-operator audit, extraction P/R
  against `answer_key`, and (for chaff specifically) *verified* downstream behavior: echoes must actually
  collapse in corroboration-counting, distractors must actually sink or fall off-canvas. **Noise is not
  free; each unit taxes the exact mechanisms being graded.** This is why the correction in §4 matters at
  the authoring-hours level, not just the ratio level: 15 noise docs at ~2.7x the verification surface of
  the corrected ~9–11 is a materially different 4-day budget.
- **Net-new work is ~8–12 docs against an already-frozen 14**, not a 24-doc expansion against zero — a
  fraction of the model draft's implied authoring load, and consistent with the audit's #5 cross-cutting
  theme ("breadth is competing with depth under a ~3.5-day clock").
- Several of the additions here (relocation thread, deep-tier/sustainment docs) are **not this document's
  call** — they are `[needs Pragalbh]` items in `06-preflight-audit.md` §"Close before writing code" (items
  4, 6, 7). This sizing assumes they are affirmed; if any is declined, S drops accordingly and the total
  moves down, never up (§8).

---

## 7. Breakdown table

| Bucket | Range | Headline | Role |
|---|---|---|---|
| **Existing frozen corpus** | 14 | 14 | d01–d14, already covers all 6 scenarios + worked query + spares/social flexes |
| — of which existing signal | 8 | 8 | d01–d08 |
| — of which existing triage substrate | 6 | 6 | d09–d14 (contradictor, stale gap, M4 origin + 2 echoes, stale holding) |
| **Net-new signal** | +4 to 8 | **+6** | relocation observable (2–3, `[needs Pragalbh]`) + deep-tier/sustainment (1–2, `[needs Pragalbh]`) + structural-case closure |
| **Net-new echoes** | +1 to 2 | **+2** | deepen the M4 too-clean cluster past the existing 2 reshares |
| **Net-new distractors** | +2 to 3 | **+2 to 3** | first pure off-subject filler — currently zero exist |
| **Net-new stale** | +0 to 1 | **+0 to 1** | mostly covered by d10/d14 already |
| **Net-new total** | +8 to 12 | **+10** | |
| **TOTAL corpus** | **22–26** | **≈ 24** | |
| Signal (S) total | 18–22 | 20 | |
| Noise (N) total | 6–13 | ~9–11 (existing 6 + net-new ~4) | |
| S/N (reported, not targeted) | — | ≈ 2:1 | derived after mechanism-driven sizing, not asserted upfront |

---

## 8. Caveats + re-derivation triggers

**What re-derives this number:**

- **Scenario/query set changes** → S recomputes from the requirement-cells (§3); total moves with it,
  roughly 1:1 (chaff does not scale with S — see next point).
- **Chaff need is re-scoped** → re-derive N from mechanism count (≈2 examples × class count), **never**
  from a ratio applied to S. If a new triage mechanism is added to the demo (a 4th class beyond
  echo/distractor/stale), add ~2 docs for it; do not multiply existing chaff.
- **The `[needs Pragalbh]` gates resolve differently** → if the relocation thread is de-locked back to the
  simpler Karachi flip (H-CONSIST-2's stated fallback), or deep-tier/sustainment docs are declined, S drops
  by the corresponding 2–5 docs and the total falls toward the low end of 22, not below the existing 14.
- **The proximity-lens filter question (§5) is resolved** → if it is built, net-new distractors can safely
  rise toward the model draft's higher counts without a legibility risk; if it is explicitly descoped,
  cap net-new distractors at 2 and keep them hand-verified off-canvas by corpus construction.

**What does NOT re-derive the number:**

- Runtime/latency considerations (§6) — corpus size never enters the request path at any size discussed
  here.
- A desire for "more realistic" S/N — real OSINT ratios (1:100+) are explicitly out of scope; the demo's
  job is legible triage, not volume realism (model draft's framing on this point stands, only the
  generating rule was wrong).

**Open dependency this document does not resolve:** whether the subject-proximity view-time filter (§5) is
added to the build ladder is a `06-preflight-audit.md` build-ordering decision, not a corpus-sizing one.
This document sizes distractors assuming that decision lands either way without breaking legibility (2–3
net-new is small enough to hide either way); it does not make that decision.
