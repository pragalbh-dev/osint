# T9 — the flagship worked query: enumeration, choice, verbatim answer, and the defect underneath

**Branch:** `qa/t9-hero-query` · **Base:** `qa/live-fixes` @ `0ed164a` (the eight-branch QA integration)
**Date:** 2026-07-20 · **Predecessor:** T3b §5, which flagged the problem and the defect but scoped both out.

Reproduce with `tmp/qa/t9_probe.py` (full node/edge/status/gap dump) and `tmp/qa/t9_paths.py` (candidate
chains under different lane whitelists) — read-only probes, run under
`cd backend && PYTHONPATH=$PWD CHANAKYA_ROOT=<worktree> .venv/bin/python ../tmp/qa/<probe>.py`.

---

## 1. Headline

The flagship query now **answers**. Three hops, every one `probable` and cited, terminating on a real,
well-corroborated organisation — and the planted misinformation is still in the answer, rated, cited, and
explicitly *not* carried.

```
BEFORE (T3b)   site_rahwali --observed-at--> comp_ht233 --supplies-component--> CPMIEC
               2 hops · terminal edge INSUFFICIENT · answer closes on a refusal

AFTER  (T9)    site_rahwali --based-at--> unit_hq9b --equips--> var_hq9p --manufactures--> mfr_casic
               3 hops · every hop PROBABLE · terminates on CASIC · chokepoint named · trap reported
```

| | `qa/live-fixes` | this branch |
|---|---|---|
| hops in the flagship answer | 2 | **3** |
| status of the terminal hop | `insufficient` | **`probable`** |
| terminal node | `ent:manufacturer:CPMIEC` (1 claim, planted) | **`mfr_casic`** (12 claims, conf 0.998) |
| answer / refusal | positive answer closing on an insufficiency | positive answer, gap stated separately |
| CPMIEC attribution | the answer's terminus | **printed as "weighed and not carried"** |
| `make test` | 843 passed | **845 passed** (+3 new, −1 replaced) |
| `ruff` / `mypy` / frontend `tsc` / vitest | clean · clean · clean · 155 | unchanged |
| graph shape (`make build`) | 166 / 84 / 19 gaps / 457 claims | unchanged — **no data was touched** |

---

## 2. What the graph can actually answer — the enumeration

Full dump: 175 nodes / 92 edges after the live-ingest beat (166 / 84 at boot). Stripping `same-as`,
`distinct-from`, `supersedes` and the 57 `source` nodes leaves **~40 substantive edges**. Two facts
dominate every candidate below and are worth stating plainly:

* **Nothing on this corpus reaches `confirmed`.** The best status any edge carries is `probable`.
* **Every `inducted-into` edge scores `insufficient`** — the induction template's `official_announcement`
  slot never closes. That single fact is why the ORBAT hop below runs on `equips` and not on the
  semantically preferable `inducted-into`.

Chasing the second of those turned up what looks like the **root cause of both**, and it is not a data
problem: `rebuild()` emits the same edge id on **several rows**, each holding a *different slice* of the
claims, and only one row is ever scored. `e:var_hq9p:inducted-into:unit_paad` appears **four times** — the
ISPR official announcement (d02), Quwa (d03) and ArmyRecognition (d04) each sit on their own unassessed
row, while the row that *is* assessed carries only d07 and the planted d23, and duly comes back
`insufficient · missing: official_announcement`. 7 ids duplicated, 9 surplus rows, 0 duplicate node ids.
Filed for SCORE/RESOLVE in `tmp/conv/T9-to-DATA-graph-gaps.md` §1 and **not** self-fixed — repairing it
changes the graph shape everywhere and needs its own branch and its own measurement. None of the three
edges in the chosen chain is duplicated, so the flagship answer is unaffected.

Candidates, scored against the brief's four criteria (terminates on a real cited answer · genuinely
multi-hop · passes a place the system shows judgement · deterministic):

### A — Rahwali → PAF HQ-9B fire unit → HQ-9/P → CASIC  ★ **CHOSEN**
3 hops, all `probable`, all cited. Terminus `mfr_casic` — 12 claims, assertion confidence 0.998, the
system's genuine origin/design authority. Passes through three *different* graded capabilities (§4).
Cost: the ORBAT hop is `equips` (from a procurement tender), not `inducted-into`.

### B — Rahwali → HQ-9BE → CASIC
2 hops, both `probable` (`observed-at` d18 + `manufactures` d04). **Rejected:** it is what an unconstrained
shortest-path returns, and it hops the *sighting* lane straight past the formation — so it cannot answer
"which unit operates it", the second of the four sub-questions. Shorter, and a weaker demonstration of
multi-hop retrieval. This is the path the lens's new `trace_lanes` deliberately steers off.

### C — Rahwali → unit → HQ-9BE → TEL chassis → Taian (Wanshan) special-vehicle works
4 hops and it names a real supplier. **Rejected:** the terminal `supplies-component` edge is
`insufficient` (single claim, open gap `named_in_sanction_or_tender`) — the identical failure mode we are
fixing. It also runs through `comp_tel_chassis`, which renders with `type: known_gap` (a pre-existing
bootstrap artefact T3b documented and left).

### D — Rahwali → unit → HQ-9/P → HT-233 → CPMIEC
The T3b chain, 4 hops when walked on the ORBAT lanes. **Rejected as flagship** for the reason this task
exists; **retained inside the answer** as the weighed-and-not-carried line, so the trap is still shown.

### E — the customs / front-company subgraph
`KPQA-HC-2020-118834 —exported-by→ SINO-GALAXY IMP/EXP CO. LTD` and `—imported-by→ ORIENT ELECTRO TRADING
(PVT) LTD`, both `probable`; three bills held apart by hard identifier vetoes; two SINO-GALAXY spellings
sitting in the merge queue as a genuine analyst question. Intelligence-wise this is the most interesting
material in the corpus. **Rejected:** it is a structurally disconnected **island** — no edge joins any
`contract_import_event` to `comp_ht233` or to a variant, so it is not reachable from any basing anchor and
can only be served as a lookup, not a trace. Filed for the data agent as the highest-value missing link.

### F — Rahwali → HQ-9BE → Pakistan → the HQ-9(P) transfer contract → "China"
4 hops, all `probable`, from d01 (SIPRI). **Rejected:** it routes through the untyped `Pakistan` node
(`type: unknown`) and terminates on a *country* typed as a manufacturer — "China builds it" is a weaker
finding than "CASIC builds it", off the same evidence.

### G — the 23rd Research Institute (the corpus's honest candidate HT-233 maker, d22)
`mfr_23rd_ri` exists in the graph but carries **only** a `based-at` edge to Yongding Road; there is no
supplier edge to `comp_ht233`, so it is unreachable from any trace. This is arguably *correct* — d22 offers
it as a candidate, not an assertion, and the ontology has no `candidate-supplier` lane to express that
distinction. Noted as a disclosure, not a bug.

---

## 3. The verbatim end-to-end answer

Produced through the **real HTTP app** (`create_app()` → boot → `POST /ask` → 4× `POST /ingest` →
`POST /ask`), keyless, no LLM — the deterministic fixed hero path. Not a fixture.

**Question** (`config/subjects.yaml → lens-hq9p-pk → target_queries[0]`, byte-identical to the SPA's first
affordance):

> Trace the long-range SAM battery now based at Rahwali back to the organisation that builds its missile
> system, and name the fire-control chokepoint.

**Before the withheld evidence is ingested** (boot state, 166 nodes / 84 edges):

```
refusal: The current subject lens has no basing site to anchor the basing→origin trace —
         these anchors are not present in the rebuilt view: site_rahwali.
```

**The two 2025 Rahwali passes arrive** (`d18_rahwali_pass1`, `d19_rahwali_confirm` + their derived basing
bundles) → `alerts_fired: ['obs-basing-relocation']`.

**After the ingest:**

```
Rahwali airfield is the basing site of the PAF HQ-9B fire unit — probable, inferred
  [d18-rahwali-pass1-unit-hq9b-site-rahwali-basing, d19-rahwali-confirm-unit-hq9b-site-rahwali-basing]
The PAF HQ-9B fire unit fields HQ-9/P — probable, observed
  [d06-spares-tender-l15-5]
HQ-9/P is manufactured by China Aerospace Science and Industry Corporation — probable, observed
  [d03-quwa-analysis-l6-10]
Chokepoint: HT-233 — chokepoint_status=candidate, substitutability=UNKNOWN. Insufficient evidence to
  assess HT-233: missing named_supplier, substitutability. Next coverage due unscheduled — no collection
  is tasked against this gap; it stands as an open collection requirement.
  [d19-rahwali-confirm-l11-11, d24-tel-chassis-attribution-l21-2, d25-hq9-site-fingerprint-l12-2,
   d25-hq9-site-fingerprint-l12-3]
Weighed and not carried: HT-233 is supplied by CPMIEC — insufficient; below the assertable band, so the
  assessment above does not rest on it
  [d23-cpmiec-false-attribution-l10-4]
```

Structured hops: `(1, site_rahwali, based-at, unit_hq9b)`, `(2, unit_hq9b, equips, var_hq9p)`,
`(3, var_hq9p, manufactures, mfr_casic)`. Nine citations, all resolving to real claims in the evidence log;
two of them tagged `inferred`, seven `observed`.

---

## 4. What the thread demonstrates, hop by hop

**Hop 1 — `Rahwali airfield is the basing site of the PAF HQ-9B fire unit` · probable · inferred · d18+d19.**
This is the whole monitoring loop in one hop. The 2025 relocation resolves to *probable*, not confirmed,
because the first pass (d18) carries `decoy_risk_flag` and a single-pass signature match is capped; a
second, discipline-independent look (d19, ELINT) is what lifts it. A `supersedes` edge retires the
Rawalpindi position, whose own `based-at` decays to `stale`. And the hop is tagged **inferred**, not
observed — what the frame shows is *equipment at a place*; attributing it to a named formation is a derived
inference that keeps its own lower confidence. Clicking the citation lands on the two overhead reads.

**Hop 2 — `The PAF HQ-9B fire unit fields HQ-9/P` · probable · observed · d06.**
A **procurement tender implies an induction**. The cited span is a real-shaped Pakistan Air Force spares
notification — *"in support of the in-service Long Range Surface-to-Air Missile (LR-SAM) system"* — which
names no designator at all. The system reaches HQ-9/P by resolution, and a single interested-party source
holds the assertion at *probable*: a tender implies, it never confirms. This is graded scenario 2
(single-source ceiling) sitting inside the flagship chain rather than in a side demo.

**Hop 3 — `HQ-9/P is manufactured by CASIC` · probable · observed · d03.**
The cited quote is *"CASIC export brand FD-2000"*. The maker edge lands on HQ-9/P **only because the system
earned the FD-2000 ≡ HQ-9/P alias merge** — the marquee entity-resolution moment (d03), with FT-2000 held
`distinct-from` HQ-9/P a few nodes away so the merge is visibly discriminating and not indiscriminate. If
that merge had not been made, the origin of the system would be unreachable and this answer would not
exist. It is the clearest available demonstration that resolution is load-bearing on the analysis.

**The close — `Chokepoint: HT-233 — candidate, substitutability UNKNOWN` + the insufficiency template.**
The question's second half. HT-233 is nominated by precomputed materiality, is honestly labelled a
*candidate* (not confirmed), and its own supplier and substitutability are stated as an open Known Gap with
the missing slots named and the coverage honestly reported as unscheduled. Absence of evidence is not
printed as evidence of absence.

**The trap — `Weighed and not carried: HT-233 is supplied by CPMIEC — insufficient`.**
The corpus's planted false attribution (d23, a grade-D trade blog conflating the export agent with the
maker, refuted by d22/CASI). The system traversed it, rated it, printed it with its citation, and told the
analyst the assessment does not rest on it. This is the deliberate design point of §5.

---

## 5. The defect underneath, and why the fix reports rather than filters

T3b: *"`agent/loop.run_fixed_hero_path` picks the first `manufacturer` neighbour with no regard for edge
status, which is how it walked an `insufficient` edge."* Confirmed. The old code asked the graph for
neighbours, checked the **node** type, and threw the **edge** away — so the pipeline's own verdict on the
link never reached the decision that used it.

**The temptation is to filter, and filtering is the wrong fix.** A supplier attribution dropped at the
gather step is indistinguishable, *in the answer the analyst reads*, from one that was never published.
That is precisely how a planted false attribution wins: it is not refuted, it is invisible, and the analyst
has no idea a low-credibility source is asserting it. Suppression would also violate the project's own
non-negotiable in spirit — the system exists to say what it knows *and* what it is discounting.

**So the fix keeps status with the candidate and splits the decision in two.** A new `SupplierLink` carries
`(node, edge, status, confidence, claims)` together. Links whose status is inside the configured band are
*carried* — the trace may rest on them. Links outside it are **kept, and reported**: `assemble.py` renders
each one as a `Weighed and not carried: … — <status>` sentence with its own citation, generically, off the
recorded `neighbors` results (nothing in that code names a node, an edge or a document).

**The band is config, and it fails closed.** `credibility.assertable_status: [confirmed, probable]` — a
status list, deliberately the same shape and doctrine as the existing `supersede_floor.newer_status_allow`,
never a second copy of a threshold number. Delete it and nothing is assertable: the trace degrades to the
honest scoped refusal rather than silently reverting to "walk whatever is there".

**When no component-level supplier clears the band, the trace climbs one level** — from the *part* to the
*system*: `Manufacturer→Variant` on the resolved variant, derived from the ontology's canonical lane, not a
literal. This is not a substitute answer to the first question. "Who supplies this radar" remains
unanswered and is reported as a Known Gap in the same breath; "who builds the system it sits in" is a
different, better-evidenced assertion, and it is the next honest link in the same dependency chain.

**And the lens now declares its traversal lanes.** `subjects.yaml → trace_lanes` is handed to `find_paths`
as its `edge_whitelist` — the other half of "a subject is a query-time lens (anchors + a traversal
pattern)". Without it the shortest walk from a site to a maker takes the *sighting* lane (`observed-at`)
straight past the formation; with it, the walk is an order-of-battle one. Omit the key and it falls back to
the ontology's full traversable set, so a lens that declares none still traces. The alternative — an edge
list literal in `agent/loop.py` — was rejected under the config-driven rule.

---

## 6. Files changed

| File | What changed |
|---|---|
| `config/credibility.yaml` | **+** `assertable_status: [confirmed, probable]` + the doctrine comment |
| `config/subjects.yaml` | **+** `trace_lanes` (7 lanes); **new** `target_queries[0]`; old wording retained as `[1]` |
| `backend/chanakya/schemas/config_models.py` | **+** `CredibilityConfig.assertable_status`, **+** `SubjectLens.trace_lanes` |
| `backend/chanakya/agent/loop.py` | **+** `assertable_statuses`, `SupplierLink`, `_supplier_links`; **modified** `run_fixed_hero_path` (maker selection, the origin-lane climb, `edge_whitelist`, the refusal wording), `HERO_SUB_QUESTIONS` |
| `backend/chanakya/agent/assemble.py` | **+** `_weighed_not_carried`; **modified** `_from_paths` (appends the rejected-link lines after the hops, preserving sentence↔hop index alignment for the citation validator) |
| `backend/tests/acceptance/test_worked_query.py` | `MIN_HOPS` 2 → **3** with the three-entry history; **−1** terminus test, **+3** (assertable terminus · chokepoint+gap still named · below-band link reported and cited) |
| `backend/tests/agent/fixtures.py` | **+** `assertable_status` on the hand-authored config (the band fails closed, so an undeclared band would have broken the fixture's supplier hop for the wrong reason) |
| `frontend/src/demo/scenario.ts` | `TARGET_QUERIES.hero` — kept byte-identical to `target_queries[0]` |
| `deploy/README.md`, `deploy/verify.sh` | the hero string in the documented beat + the acceptance check |
| `artifacts/C/02-demo-thread.md`, `DECISIONS.md` | the amended thread + the decision ledger |

New probes: `tmp/qa/t9_probe.py`, `tmp/qa/t9_paths.py`, `tmp/qa/t9_claims.py`. **No corpus, bundle or
`answer_key.json` file was touched.**

---

## 7. Deliberately left

- **The flagship refuses on a cold boot.** `site_rahwali` exists only after the two withheld 2025 passes
  are ingested, so the SPA's first affordance returns a refusal until the beat runs. This is the *designed*
  choreography (`deploy/README.md`: ask → refuse → ingest → alert → ask again) and it is a genuine
  adaptation demo — but it is a demo-sequencing risk worth knowing about, and the refusal copy
  (*"the current subject lens has no basing site to anchor the basing→origin trace"*) is engineer-shaped
  rather than analyst-shaped. Not changed here: rewording it is presentation work with its own review.
- **The duplicated-edge-row defect (§2) and its two symptoms — nothing `confirmed`, every `inducted-into`
  `insufficient`.** SCORE/RESOLVE's call, filed rather than self-fixed: it changes the graph shape
  everywhere and would invalidate this branch's "no data was touched" property. It is nonetheless the
  single change that would most improve the thread — it would put the ORBAT hop on `inducted-into`
  (4 claims, incl. the ISPR announcement) instead of `equips` (1, a tender), and give the demo a genuine
  confirmed-vs-probable contrast *inside* the flagship chain instead of only in the side flexes.
- **The old query wording is kept as `target_queries[1]`**, so the previous phrasing still routes to the
  same deterministic path and answers. Its old value — closing on a well-reasoned refusal — is preserved
  *inside* the flagship answer (the weighed-and-not-carried line plus the HT-233 insufficiency close),
  which is strictly more informative than a dead end. A dedicated terminal-refusal flex would need its own
  scripted path; not built.
- **Demo-mode's scripted `HERO_HOPS`** (`frontend/src/demo/scenario.ts`) is still the Karachi-anchored
  4-hop narrative and now diverges further from the live answer's anchor. Pre-existing; a frontend call.
- **`comp_tel_chassis` still renders with `type: known_gap`** (T3b's documented bootstrap artefact). It is
  why candidate C was not pursued, but fixing it is a resolution change, not an ASK one.

## 8. New observations for the data agent

Filed, not self-fixed, per CLAUDE.md → `tmp/conv/T9-to-DATA-graph-gaps.md`.
