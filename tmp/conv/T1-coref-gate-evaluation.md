# T1 — Is in-document coreference worth turning on?

**Branch:** `qa/t1-coref-gate` · **Base:** `origin/main` @ `8932793` · **Date:** 2026-07-20
**Verdict: KEEP GATED (do not turn on, do not delete).** Config left exactly as shipped.

Reproduce with `tmp/qa/t1_snapshot.py` and `tmp/qa/t1_coref_reach.py` (read-only probes, run under
`cd backend && CHANAKYA_ROOT=<worktree> .venv/bin/python ../tmp/qa/<probe>.py <out.json>`).

---

## 1. Headline

Three independent findings, each sufficient on its own to keep the gate closed:

1. **Flipping the consumer flag is a provable no-op.** The shipped frozen bundles contain **zero**
   `coref-same-as` claims (`grep -c` over all 29 files in
   `corpus/scenarios/hq9p_primary/claims/` → 0). `resolve/__init__.py::_coref_pairs` iterates
   `graph.edges` filtered on `predicate == COREF_PREDICATE`; with no such edges the loop body never
   executes and both returned sets are empty. Verified empirically: gate-on and gate-off snapshots are
   **byte-identical** across every measured dimension.
2. **Turning the producer on breaks the build today.** It costs a *second* extraction call per document.
   Every recorded fixture and every frozen bundle holds exactly one recorded response, so the scripted
   client is exhausted: **31 tests fail** (`RuntimeError: ScriptedExtractionClient exhausted: more
   extraction calls were requested than recorded`). This is the mechanised proof of the residual note's
   "needs an EVAL re-record" — it is not a soft cost, it invalidates the frozen corpus and ~31 fixtures.
3. **Even after a full re-record, the payoff is ~1–3 merges and the blast radius is a wrong merge.**
   Coref is scoped to one document by design. Only **11 of the system's own 40 duplicate candidates**
   are in-document at all — and of those 11, **9 are pairs a human would call clearly different**,
   sitting in the same document with the same type, same namespace, no hard-attribute conflict and
   **no `distinct-from` veto protecting them**.

**Does it fix duplicate-Karachi or the duplicated HQ-9 / HT-233 variants? No — not even in principle.**
Both clusters are overwhelmingly *cross-document*, which is RESOLVE's job, not coref's. Details in §3.

---

## 2. Side-by-side diff

`make build`, then `tmp/qa/t1_snapshot.py`. "Gate on" = `coref_authoritative_evidence:
[EXPLICIT_EQUIVALENCE]` **and** the `coreference:` producer block uncommented in `credibility.yaml`.

| Measure | Gate OFF (shipped) | Gate ON | Δ |
|---|---|---|---|
| Nodes | 171 | 171 | **0** |
| Edges (total) | 105 | 105 | **0** |
| — substantive | 56 | 56 | 0 |
| — `same-as` candidates = **HITL merge queue** | **40** | **40** | **0** |
| — `distinct-from` vetoes | 9 | 9 | 0 |
| Known gaps | 20 | 20 | **0** |
| Events | 66 | 66 | 0 |
| Claims replayed | 457 | 457 | **0** |
| `coref-same-as` claims in the log | **0** | **0** | 0 |
| `unknown`-type nodes | 11 | 11 | **0** |
| Node-id set | — | — | **identical** |
| `same-as` pair set | — | — | **identical** |
| `make test` | **788 passed, 0 failed** | **757 passed, 31 failed** | **−31** |

The UI's "41 pending merge items" measures as **40** `same-as` candidate edges here; the extra item is
likely a non-merge review type counted in the same panel. Either way it is unchanged by the gate.

Isolating the two halves:

| Config | Tests | Graph |
|---|---|---|
| Shipped (both off) | 788 pass | 171/105/20 |
| **Consumer only** (`[EXPLICIT_EQUIVALENCE]`) | **788 pass** | 171/105/20 — unchanged |
| Consumer + producer | **31 fail** | build unchanged; extraction path broken |

So the consumer flag is *safe but useless* on its own; the producer is where all the cost and all the
risk live.

---

## 3. Duplicate-cluster census (gate OFF)

Node census: 171 nodes = 54 `source`, 30 `component`, 27 `basing_site`, 19 `variant`, 11 `unknown`,
11 `manufacturer`, 6 `known_gap`, 5 `contract_import_event`, 5 `unit`, 3 `trading_org`.

Fragmentation is real. But the decisive column is **"same doc?"** — coref can only ever touch a pair
whose two mentions appear in one document.

### Cluster A — the HT-233 engagement radar: **10 nodes across 8 documents**

| Node | Type | Docs | Coref-reachable? |
|---|---|---|---|
| `comp_ht233` (canonical, 8 claims) | component | d15,d17,d21,d22,d23,d24,d25 | — |
| `HT-233` | **unknown** | d15,d23 | ✅ shares d15/d23 |
| `HT-233 phased-array engagement radar` | **unknown** | d21 | ✅ shares d21 |
| `engagement radar` | component | d17 | ✅ shares d17 |
| `PLA's domestic HT-233` | **unknown** | d01 | ❌ canonical absent from d01 |
| `HT-233 (H-200) engagement radar array` | component | d10 | ❌ canonical absent from d10 |
| `HT-233 or derivative` | component | d07 | ❌ |
| `Type 305B` | component | d01 | ❌ |
| `Type 305B (HT-233) fire-control set` | component | d14 | ❌ |
| `HQ-9P fire control radar` | component | d01 | ❌ |

**3 of 10 reachable.** The radar stays fragmented 7 ways after a perfect coref run.

Note on the collision `resolution.yaml` warns about: d10's `"HT-233 (H-200) engagement radar array"` is
live in the corpus and is a textbook apposition (`EXPLICIT_EQUIVALENCE`). It happens **not** to bind
today only because `comp_ht233` carries no d10 claim — an accident of current document coverage, not a
designed guarantee. The warning is sound and should not be treated as retired.

### Cluster B — Karachi: **5 nodes across 4 documents** — *coref cannot help, and merging would be wrong*

| Node | Doc |
|---|---|
| `Army Air Defence Centre, Karachi` | d02 |
| `Karachi air defence sector` | d21 |
| `Karachi coastal air defence belt` | d23 |
| `imagery-site:d07_sat_confirm_karachi` | d07 |
| `Probable Long-Range SAM Emplacement, …` | d07 |

Only the d07 pair is in-document. **More importantly, these are not one thing.** Per `md/13`'s precision
spec an air-defence *sector* or *belt* is an area of operation, **not** a basing site. The actual defect
is upstream typing: administrative areas and sectors are being minted as `basing_site` nodes at all.
Evidence that this is the real bug — the resolver is currently proposing these as merge candidates:

```
Karachi air defence sector   <-> central Punjab air defence sector
Karachi coastal air defence  <-> Sargodha
Punjab                       <-> Sindh
```

`Punjab ↔ Sindh` — two different provinces — is an active pending merge suggestion. Coref would not fix
this; if anything a same-document coref pass over d22 (which contains both) is a chance to *cement* it.

**Port of Karachi vs Port Qasim: neither exists as a node in the graph.** The `distinct_from` pair is
declared in `config/places.yaml` (`pl_karachi_port` ↔ `pl_port_qasim`) but never instantiated, so that
specific veto is **untested on the real corpus**. It is not currently at risk; it is also not currently
proven.

### Cluster C — HQ-9 variant family: mostly *correct*, not duplicated

| Node | Docs | Verdict |
|---|---|---|
| `var_hq9p` (HQ-9/P, 20 claims) | 15 docs | canonical |
| `ent:variant:HQ-9` (7 claims) | 7 docs | China HQ-9 — **legitimately distinct** |
| `var_hq9be` (HQ-9BE) | 6 docs | distinct variant, **active veto** vs `var_hq9p` ✅ |
| `ent:variant:HQ-9A` | 4 docs | distinct variant, **active veto** ✅ |
| `alias_ft2000` | d04 | **active veto** vs `var_hq9p` ✅ (FT-2000 is a different missile) |
| `Chinese Hongqi-9 (HQ-9P/FD-2000 family)` | d02 | genuine fragment — ✅ reachable |
| `Hongqi-9 family` (**unknown**) | d06 | genuine fragment — ✅ reachable |
| `modified export variant` (**unknown**) | d01 | genuine fragment — ✅ reachable, but under an **active veto** vs `PLA's domestic HT-233` |
| `FD-2000B` | d03 | fragment — ❌ not reachable |

The "HQ-9 appears many times in the UI" complaint is **largely the system working correctly**: HQ-9A,
HQ-9BE and FT-2000 are separate things held apart by explicit do-not-merge vetoes. Only ~3 nodes are
genuine fragments, and only those 3 are coref-reachable. Note also `unit_hq9b` (unit) vs `var_hq9be`
(variant) is a correct type distinction — the fielded formation vs the missile variant — not a duplicate.

### Cluster D — genuine, in-document, and actually addressable (the whole payoff)

| Pair | Doc | Category | Auto-merges under `[EXPLICIT_EQUIVALENCE]`? |
|---|---|---|---|
| `LY-80` ↔ `HQ-16` | d01, d14 | d14 writes "LY-80 (HQ-16)" — apposition | ✅ **yes** — the one clean win |
| `SINO-GALAXY IMP/EXP CO. LTD` ↔ `SINO-GALAXY IMPEX CO, LTD` | d05 | NAME_VARIANT | ❌ raise-only |
| `fenced compound near a PAF airbase` ↔ `… in central Punjab` | d01 | NAME_VARIANT | ❌ raise-only |

### Cluster E — out of reach entirely (cross-document)

- **CPMIEC** — `CPMIEC` (d01,d21,d22,d23) vs `China National Precision Machinery Import & Export
  Corporation` (d14). This is the module docstring's *own headline example*, and in this corpus the two
  forms never co-occur in a document. Coref cannot touch it.
- **Taian** — `mfr_taian` (d24) vs `ent:manufacturer:Taian` (d25).
- 29 of the 40 pending merge candidates overall.

### The `unknown` rescue — coref's actual designed purpose

All 11 `unknown` nodes are dangling relation endpoints with empty `name` fields (they render by id).
Every one has typed co-mentions in its own document, so all 11 are *reachable in principle*:

| Unknown node | Doc(s) | Typed co-mentions in same doc |
|---|---|---|
| `HT-233` | d15, d23 | 21 |
| `PLA's domestic HT-233` | d01 | 20 |
| `Pakistan` | d01 | 20 (no country node type exists — unrescuable) |
| `modified export variant` | d01 | 20 |
| `HQ-9B fire unit` | d17 | 13 |
| `Hongqi-9 family` | d06 | 10 |
| `S-300P/PMU-series` | d06 | 10 |
| `TEL` | d25 | 10 |
| `TAS5380` | d24 | 9 |
| `HT-233 phased-array engagement radar` | d21 | 8 |
| `HQ-9/P TEL` | d07 | 5 |

But *reachable* ≠ *merged*. Under the documented `[EXPLICIT_EQUIVALENCE]` opt-in, descriptive and
elliptical references (`TEL`, `modified export variant`, `Hongqi-9 family`, `HT-233 phased-array…`) are
`UNAMBIGUOUS_ANAPHOR` / `NAME_VARIANT` → **raise-only**. They would not merge; they would each add an
item to a merge queue that already has 40. **Recall-biased triage is the design, but 40 → ~50 pending
items with ~1 extra merge is a worse ratio, not a better one.**

One of these is worth flagging separately: `unknown:HT-233` in d15 has the **identical surface string**
to `comp_ht233`, which also has a d15 claim. An identical-string endpoint failing to match a registry
entity is a **RESOLVE / alias-index defect, not a coreference gap**. Turning coref on would paper over
that bug rather than fix it — and would hide the signal that it exists.

---

## 4. The wrong-merge risk (the disqualifying one)

Of the 11 in-document merge candidates, **9 are pairs a human analyst would call clearly different**:

| Pair | Doc | Same type? | Namespace conflict? | Hard-attr conflict? | `distinct-from` veto? |
|---|---|---|---|---|---|
| `Punjab` ↔ `Sindh` | d22 | yes | no | no | **none** |
| `KPQA-HC-2020-118834` ↔ `…118835` | d05 | yes | no | no | **none** |
| `KPQA-HC-2020-118834` ↔ `…119011` | d05 | yes | no | no | **none** |
| `KPQA-HC-2020-118835` ↔ `…119011` | d05 | yes | no | no | **none** |
| `Karachi air defence sector` ↔ `central Punjab air defence sector` | d21 | yes | no | no | **none** |
| `Karachi coastal air defence belt` ↔ `Sargodha` | d23 | yes | no | no | **none** |
| `comp_ht233` ↔ `Type 120` | d15 | yes | no | no | **none** |
| `FD-2000/HQ-9P interceptor` ↔ `Type 120` | d15 | yes | no | no | **none** |
| `HT-233 (H-200) engagement radar array` ↔ `support vehicles` | d10 | yes | no | no | **none** |

`_coref_pairs` demotes a pair to raise-only on **type mismatch, namespace incompatibility, or a hard
attribute conflict**, and drops it on a `distinct-from` veto. **None of those four rails fires on any of
these nine pairs.** Whether they auto-merge depends entirely on an unaudited LLM judgement made at
re-record time, with no deterministic guard behind it.

The three KPQA rows are the sharpest case: three *distinct bills of lading* in one customs manifest.
Merging them would collapse three separate import events into one and silently corrupt the
supply-chain count — in a document type the project treats as high-value evidence. The existing veto set
(9 pairs) protects none of them.

Against the project's own standard — over-merge is "the expensive, adversarially-exploited error", and a
fabricated assessment is disqualifying — accepting an unbounded auto-merge channel to gain ~1 merge is
the wrong trade.

---

## 5. Recommendation: **KEEP GATED**

Not delete, not turn on.

**Why not turn on.** Cost: a second LLM call on every document forever, a keyed re-record of all 29
frozen bundles, ~31 test fixtures re-recorded, and a re-run of the EVAL baseline — against the standing
rule that the frozen corpus is not to be edited unilaterally. Benefit on the measured corpus: **one
reliable merge** (`LY-80` ↔ `HQ-16`), possibly two, plus ~10 extra raise-only items on a 40-item queue.
Risk: nine unguarded same-type in-document pairs that a wrong LLM call would silently merge, including
three distinct customs bills. And it would not fix either problem that motivated the question — Karachi
and the HQ-9/HT-233 variants are cross-document fragmentation.

**Why not delete.** The code is sound, well-documented, correctly architected (dedicated predicate so it
cannot dilute `merge_score`; derived-at-rebuild so a split stays native; every rail re-applied
deterministically after the model proposes), and it is **fully inert** — 788 tests pass with it shipped,
and the consumer flag provably cannot do anything without producer output. It costs nothing to keep and
it is a genuinely good answer to a real design question. On a demo call it is defensible *as a gated
capability*: "we built the in-document discourse channel, measured its reach on the frozen corpus at 11
of 40 candidates with 9 of those 11 unguarded, and chose to leave it raise-only until the veto coverage
earns it." That is a stronger story than either shipping it hot or having never built it.

**What it would cost to make it worth turning on** — in dependency order:

1. **Fix the identical-string endpoint bug first.** `unknown:HT-233` vs `comp_ht233` sharing d15 is a
   RESOLVE/alias-index miss. Fixing it removes 1–2 unknowns with no LLM call at all, and stops coref
   from being credited for masking it.
2. **Fix `basing_site` typing.** Sectors, belts and provinces should not be basing sites (`md/13`). This
   alone would remove the `Punjab↔Sindh`, `Karachi sector↔central Punjab sector` and
   `Karachi belt↔Sargodha` candidates — three of the nine unguarded pairs — and shrink the merge queue.
3. **Give `contract_import_event` a hard-attribute rail** so two distinct bill-of-lading numbers can
   never merge. That kills three more unguarded pairs deterministically, not probabilistically.
4. **Then** re-record with `categories: [EXPLICIT_EQUIVALENCE]` only (drop `NAME_VARIANT` and
   `UNAMBIGUOUS_ANAPHOR` from the *producer*, not just the consumer — no reason to pay for proposals
   that are raise-only by policy), and measure the false-merge rate on the frozen scenarios, as
   `resolution.yaml` itself instructs.
5. Re-confirm the d10 `HT-233 (H-200)` demo beat survives, since it is an `EXPLICIT_EQUIVALENCE`
   apposition whose current safety is accidental.

Steps 1–3 are worth doing **on their own merits** regardless of coref — they attack the cross-document
fragmentation that is the actual duplicate problem. If they land and the queue is still noisy, revisit.

---

## 6. Decisions taken (per CLAUDE.md "record & surface decisions")

- **D-T1.1 — Left the gate closed rather than opting in.** Principle: *borderline-harmful → ask first*
  and *keep the demo deterministic & reproducible*. Turning it on requires re-recording the frozen
  corpus, which is explicitly not a unilateral call. Alternative rejected: shipping
  `coref_authoritative_evidence: [EXPLICIT_EQUIVALENCE]` on the grounds that it is currently inert —
  rejected because it arms a live auto-merge channel that fires the moment anyone enables the producer,
  which is precisely the coupling `resolution.yaml`'s own comment warns against.
- **D-T1.2 — Did not attempt a keyed re-record.** Principle: *data issues → don't self-fix*. Would have
  rewritten all 29 frozen bundles and invalidated the EVAL baseline. Filed as a cost estimate instead.
- **D-T1.3 — Reported the null result as a structural fact, not a measurement.** The consumer flag
  cannot move the graph because no `coref-same-as` claims exist; stating "we turned it on and nothing
  changed" without that mechanism would be misleading.

**Design-doc tails to enrich:** `artifacts/spine/03-resolution.md` (record the measured 11-of-40
in-document reach as the empirical case for coref staying raise-only); `tmp/conv/RESIDUAL-FIXES.md` #13
(replace "needs an EVAL re-record" with the measured cost: 29 bundles + 31 fixtures + one extra LLM call
per doc).

**New observations for the data agent** (not fixed here, per the don't-self-fix rule):
- `basing_site` is absorbing areas of operation (sectors, belts, provinces) against `md/13`'s precision
  spec, producing nonsense merge candidates such as `Punjab ↔ Sindh`.
- Three distinct KPQA bill-of-lading numbers in d05 are proposed as mutual merge candidates with no
  deterministic guard.
- All 11 `unknown` nodes carry an empty `name` and render by raw id in the UI.
- `unknown:HT-233` and `comp_ht233` share document d15 with an identical surface string and still fail
  to resolve — an alias-index / registry-match miss.
