# Phase-2 verify delta + downstream handoff (post keyed re-record)

**Author:** EVAL Phase-2 session (`fix/phase2-ingest-extraction`). **Date:** 2026-07-19.
**What this is:** the measured before→after from re-recording `hq9p_primary` (26 keyed bundles) over the
Phase-2 extraction, plus what each downstream phase now inherits. Regenerate with
`CHANAKYA_ROOT=<wt> backend/.venv/bin/python tmp/conv/eval-rca/rca_evidence.py`.

## Verified delta (old baseline → post-Phase-2)

| Signal | Before | After | Note |
|---|---|---|---|
| ad-hoc / free-text edge predicates | ~22 | **0** | every edge is now a canonical ontology type (enum + re-lane + denial-drop) |
| `exported-by` | 0 | 5 | ING-2 customs role-edge |
| `imported-by` | 2 | 7 | ING-2 |
| `supplies-component` | 0 | 1 | ING-2 + DC-1 vocab (Taian→chassis lands right) |
| `inducted-into` | 1 | 6 | re-lane |
| `contract_import_event` nodes | 1 | 4 | customs mints the import event |
| `trading_org` nodes | 0 | 4 | ING-3; `manufacturer` 17→12 (shells no longer mis-typed) |
| INGEST `known_gap` sentence-nodes | 14 | 6 | ING-4; slot-keyed, not verbose sentences |
| bundles with `method=vlm` | 0 | 9 | ING-8 image co-load runs the VLM lane |
| bundles carrying `report_time` | 0 | 26 | ING-7 dates flow (24 real, 2 honest-null) |
| full view | 294n/101e | 258n/100e | counts stay high — fragmentation is Phase-3 |

**Read:** Phase-2 cleaned the input and grew the real supply-chain/ORBAT skeleton. The reconnection that
collapses fragmentation and lights up the lens is **Phase-3**, by design (the RCA always said counts move
in P3, not P2).

## Deferred-by-design (NOT Phase-2 regressions — confirmed by this run)
- **`as_of=2021` rewind still returns `[]`.** Correct: we stamped honest `report_time` but did **not**
  backdate `ingest_time`, so the *availability* (transaction-time) rewind honestly still says "received in
  2026." The relocation demo must rewind on **valid-time** (`event_time`) — that is MONITOR **MON-2**, not
  an INGEST fix. This run confirms the axis-mismatch diagnosis.
- Lens `0/0`, hero-query crash, fragmentation — all named downstream items below.

## Reproducibility gotcha (INGEST / keyed-extract workflow)
The keyed re-record (`python -m chanakya.ingest extract --scenario hq9p_primary --offline`) **crashes on
the one corpus PDF (d25)** if `AZURE_*` OCR creds are in the environment but the `azure-ai-documentintelligence`
extra is not installed — the loader selects the Azure OCR path and `ModuleNotFoundError`s. **Fix (used
here):** d25 is *born-digital* (clean 3.1k-char text layer), so withhold `AZURE_*` from the run → the
loader takes the keyless **pymupdf** path (installed) and every page still renders for the VLM lane.
So: to re-record, export only `GEMINI_API_KEY`/`ANTHROPIC_API_KEY` and drop `AZURE_*` — or install the
Azure extra. Captured as decision **D-2.9**.

## What each downstream phase now inherits

**Phase-3 — RESOLVE (`handoff-resolve.md`, RES-1/RES-2):**
- Supply-chain edges now exist but their endpoints are **`trading_org` shells** (customs consignee/shipper).
  Endpoint-linking (RES-1) + `entities.yaml` consumption must resolve shell→real entity so the oracle's
  `import_2021 --exported-by--> mfr_casic` / `--imported-by--> unit_paad` form. **`import_2021` is still
  `[MISSING]`** (the customs event isn't matched to the oracle id) — this is the RES shell-resolution +
  registry job, not an INGEST gap.
- Fragmentation persists (e.g. `mfr_casic` FRAGMENTED-7) — RES-1 endpoint-linking + registry is the fix;
  node count 258 drops when merges collapse.
- `same-as` edges (53) still **render** — the view-skip + consume-as-source-weighted-evidence (decision
  **D-2.5**) is the Phase-3 piece. `distinct-from` should stay rendered + veto.
- `based-at` now appears as **variant/equipment@site** (e.g. "HQ-9/P based-at Army Air Defence Centre,
  Karachi"), the honest stated layer. The **unit→site** derivation is RESOLVE/SCORE (grounding **D-G2**);
  the equipment@site input it derives from is now present in the data.
- 6 slot-keyed `known_gap` nodes remain (oracle wants 2) — RES dedup may merge duplicates further.

**Phase-4 — SCORE (`handoff-score.md`):** the sufficiency engine now emits **37** `gap:*` items (was 14) —
a fragmentation side-effect (many tiny under-evidenced clusters each fire a gap). **Re-measure after Phase-3
merge before any template calibration** — do not tune to 37.

**Phase-4 — ASK (`handoff-ask.md`, AS-1):** the hero query **still crashes** (`KeyError: 'node_id'` at
`agent/assemble.py:149`) — untouched by Phase-2; the crash-guard + honest-refusal work still stands.

**Phase-4 — ARCH / MONITOR:** lens still `0/0` (ARCH lens-anchor **AR-2**); `as_of=2021` rewind empty is
MONITOR **MON-2** (valid-time axis), per Deferred-by-design above.
