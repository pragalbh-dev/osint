# Session INGEST — Source-typed LLM Extraction + Live-Ingest Lane + Seed Bundles

**Wave 1 · depends F0 (merged) · soft-depends DATA-C `sources.yaml`/`ontology.yaml` (config content) and
F0's real store (for the committed seed only) · parallel-safe (disjoint ownership).**
Read `../00-master-plan.md` §4.2 (ClaimRecord + Source registry — the record you emit), §4.3 (rebuild stage
order + live trigger), §1 invariant #2 (LLM proposes *upstream* of the append), §5 gates **G9/G11**, §7
(keyless boot). This session owns the **ingest lane that feeds the store**; keep it THIN — one extraction
call, one claim schema, one append→rebuild→observe path. All real stage logic (resolve/score/observe) is
someone else's.

## Goal

Stand up the **ingest lane**: any raw doc of any `source_type` → one LLM function-calling extraction to the
**one** ClaimRecord schema → append to the evidence log → hot `rebuild()` → observable-eval. Extraction runs
**upstream of the append** (invariant #2), so `rebuild()` stays LLM-free/pure. Ship two front-ends over the
same lane: **live extraction** (keyed) and **pre-extracted claim bundles** (keyless), and produce the
**frozen seed baseline** so the app boots and runs the hero query with no key. The graded axis this makes
real is **monitoring** — ingest→rebuild→alert running for real, not a scripted reveal.

## Design docs to read first
`spine/02` (unit = sourced claim; three-layer relevance / **no hard relevance gate at ingest**; extract-raw
guardrail; dedup rule; reusable Dates/Locations base objects) · `spine/08` §3.1 (claim record) / §4 row 02
(extraction = LLM-only, live at ingest) / §3.11 (LLM proposer-vs-authority invariant) · `spine/09` "Live
ingestion (always available) vs extraction (optional front-end)" + hot-config/live-rebuild · `DECISIONS.md`
"Extraction = LLM-only, live at ingest (not frozen-only)" + the extract-raw guardrail row · `md/13`
(location standardization — the coord-canonicaliser/place-resolution seam that RESOLVE, not INGEST, owns) ·
`md/10` (the generator contract — what ingestion RECEIVES: raw `docs/*.txt` + co-located `*.png`; `answer_key.json`
is **EVAL-ONLY**, never ingested; the generator stays ontology-blind, **G11**).

## Scope (build these)

1. **Source-typed extractor framework** (`chanakya/ingest/extract.py`) — a dispatcher keyed on `source_type`
   where **every** `source_type` (customs GD, tender, NOTAM string, SIPRI register, ISPR PR, social post,
   analyst-report imagery text, …) routes through the **SAME** single LLM function-calling call to the one
   ClaimRecord schema (structured feeds + prose alike). **No per-source parsers** (parsers = roadmap; the
   dispatcher *is* the seam where they'd slot later). Ingestion is **source-typed, never use-case-typed**
   (**G9**): a customs doc ingests identically regardless of consumer; **no hard relevance gate, no branch
   keyed on subject/anchors**. Typed extraction is guided by the **ontology TYPE schema** (generic node/edge/
   event types from the config store) — never by subject anchors or ontology *instances*. **Source binding
   is collection metadata**, supplied by the caller (`source_id` → `sources.yaml` registry entry for
   `source_type`+`cadence`), never inferred from `answer_key`; for the offline seed batch it comes from a
   collection manifest / the `dNN_<sourcekey>_…` filename convention.
1a. **Source-typed document loader** (`chanakya/ingest/loaders.py`) — normalise any raw input to *text
   (+ optional regions)* **before** the single extraction call, keyed on file type: `.txt` direct; `.html`
   → boilerplate-stripped text; **`.pdf` incl. multi-page/scanned → OCR via Azure AI Document Intelligence**
   (text + layout + tables + per-line **page/bbox**) so customs GDs / tenders / scanned specimens ingest with
   precise provenance; **imagery `.png/.jpg` → VLM read** (item 6) *or* attach-as-provenance. The loader
   returns `(text, regions[])`; a region's `page`/`bbox`/`row` becomes the claim's **`doc_ref` span**
   (traceability, **G4**). OCR is an **optional env-gated provider** (`AZURE_DOCINTEL_ENDPOINT`/`_KEY`) like
   the LLM key — born-digital PDFs may skip it (`pdftotext`); keyless reviewers use the pre-extracted bundles
   (item 6), so OCR is never on the keyless path. The loader is where per-source **input** handling lives; the
   **output** is always the one ClaimRecord schema (source-agnostic — **G9**).
2. **The extract-raw guardrail** (replaces parser-first anti-circularity, `spine/02` / `08` §3.11). The LLM
   extracts the claims a source *states* — **including any alias / `same-as` / equivalence a source
   explicitly asserts** (e.g. "formerly ORIENT ELECTRONIC TRADING", "FD-2000 is the export designation of
   the HQ-9") → a sourced same-as claim that **feeds `source_asserted` in RESOLVE**, never an auto-merge. It
   must **never resolve/normalize the *unstated*** — never decide two differently-named entities are the
   same, never un-mess a front-company cover story, never clean up hedged language. **Stated → extract it;
   unstated resolution → the pipeline's job.**
3. **Normalization adapters** (`chanakya/ingest/adapters.py`) over the **F0-frozen value objects
   `Date`/`Location`/`Quantity`** (master §4.2 — the *shapes* live in `schemas/`, NOT redefined here). The
   adapters run **at extraction, pre-append**, and are **invoked explicitly — never pydantic
   on-instantiation validators** (a validator would fire on every reload during `rebuild()` → a network/parse
   call in the rebuild path → breaks **G1**; the adapter runs once, its output is persisted, reload does
   nothing).
   - **`Date`** — the deterministic derivation over F0's `Date`/`DateSpec`/`Period` shape (adapted from
     `financial.py`, master §4.2): exact strings → `ExactDate` (with the ISO sanitizer), labels ("Oct 2021",
     "Q2 2025", "2021") → `LabelDate` → derived ISO boundaries, intervals → `Period(range)`, and **relative
     expressions ("last week", "recently") → resolved against the claim's `report_time`** into a dated
     `Period` + an `approximate` flag; nullable+flagged when unresolvable. **Calendar only** (no fiscal).
     Deterministic — no LLM in the derivation; the LLM only supplied `raw` + the label at extraction.
   - **`Location` — normalize DURING extraction** (locked, master §4.2): the canonical stored form is the
     geocode (WGS84), but **most docs state only a place name or a relative ref, not a coord** — so the
     adapter does deterministic multi-format coord-canonicalisation (DD/DMS/MGRS/UTM/URL → WGS84) *for the
     docs that give a coord* **and Nominatim geocoding of names/relative refs** for the ones that don't,
     freezing the WGS84 form + `geocode_candidates` onto the record; an LLM disambiguation pass **PROPOSES
     aliases only** (raise-only) for what Nominatim can't resolve. Frozen upstream → keyless bundles + a
     network-free `rebuild()` (**G1**). The deterministic **place-resolution** (gazetteer match +
     `distinct-from` traps) stays in **RESOLVE**. Tune precision/misses/ambiguity→HITL empirically on the
     real strings here.
   - **`Quantity`** — parse counts/ranges/measures ("~125 km", "a battalion of ~6 TELs", magazine depth)
     into the `Quantity` value object (`min|max|value`, `unit`, `count_state`, `approx`).
   *(If a needed slot is missing from F0's frozen value objects — e.g. `geocode_candidates`/`proposed_alias`
   on `Location` — that is a small **F0-amendment** (master Rule 3), raised not silently widened.)*
4. **Claim-dedup + ID/span discipline** (`chanakya/ingest/dedup.py`). Same assertion **restated within one
   doc** = **ONE claim + multiple `doc_ref` spans** (lexical grouping on `(kind, polarity, asserts,
   normalized stated s/p/o strings)` — a within-doc match on *stated* strings, **never** entity resolution).
   Same assertion **across docs** = **SEPARATE claims** (never merged — corroboration/independence need them
   separate; dedup is strictly scoped to one doc's extraction batch). Human-readable `claim_id`
   (`d05-row12`, `d03-c4`) assigned **post-extraction in a deterministic order** (span offset, then stable
   counter) so IDs are stable despite LLM ordering. `doc_ref = {file, span|row|frame}` carries the exact
   cited quote/offset (feeds **G4** traceability + the ASK entailment validator).
5. **The live-ingest lane** (`chanakya/ingest/lane.py`) — the always-available path: raw doc → `extract` →
   `store.append(claims)` → hot `view.rebuild()` → `observe.evaluate(view)`. Exposed as a **callable**
   (`ingest_document(raw, source_id, *, images=[], live_rebuild=True) -> IngestResult`); the `/ingest` HTTP
   endpoint is API's. The LLM runs **upstream of the append**, so the LLM-free-`rebuild()` invariant holds.
   `observe.evaluate` is F0's stub until MONITOR merges (composes at Wave 2); `rebuild()` is F0-real.
6. **Two front-ends over one lane.** **Extraction is the optional, keyed part:** with `ANTHROPIC_API_KEY`
   (or `GEMINI_API_KEY`) a *raw* doc is extracted **live**. **Without a key, reviewers ingest PRE-EXTRACTED
   claim bundles** (`ingest_bundle(path)` reads `corpus/scenarios/<name>/claims/<doc_id>.json` and appends —
   no LLM) and still fire observables + run the hero query keyless. The bundles are the **frozen output of
   live extraction over the same doc**, so the keyless path appends the *same* claims as the live path.
   Provider abstraction: Anthropic default, Gemini optional; **no `temperature`/`top_p`/`top_k`** (HTTP 400
   on Opus 4.8); `extraction.model_conf` held at **1.0**; optional OCR via `AZURE_DOCINTEL_*` (item 1a).
   **`method ∈ {llm, vlm}` — same output, different modality.** The claim OUTPUT is source-agnostic (one
   ClaimRecord schema); only the *loader* + *modality* differ (never the graph schema — G9). **Demo posture
   (md/11 A1): satellite imagery is ingested as IMINT analyst-report TEXT** (the `.png` rides as a provenance
   attachment) → the normal text path emits the claims. **VLM path (built-if-time, SAME claim path):** a VLM
   reads the pixels and emits **(a)** an **observation** claim (`kind: observation, method: vlm`) of what is
   literally seen — e.g. `<site_S, occupancy_state, occupied>` or `<site_S, observed_signature,
   rectangular-tel-pad-ring>`, a `count` as a `Quantity` — filling the imagery evidence fields (`geo`,
   capture-time→`event_time`, `resolution`, `first_seen`, `caption_vs_image_consistency`, `decoy_risk`); and
   **(b)** a **separate `inference`** claim (`kind: inference, premises: [the observation claim_id]`) for the
   diagnostic leap ("rectangular TEL-pad-ring ⇒ HQ-9 site"). The inference **never confirms alone**: the
   single-pass `decoy_risk` gate caps it at **probable** (SCORE); confirmation needs a 2nd
   discipline-independent look (repeat pass / ELINT / text) — exactly the locked Rahwali beat. The
   signature→variant vocabulary is **ontology config** (`Basing site.site_signature_geometry` + a
   signature-library map), never hardcoded.
   **Social post = image + caption is the same lane**, at the opposite trust tier: the *caption* yields a
   **stated observation** claim at the **social source-tier** (low-provenance lead — raises to *probable*,
   **never confirms alone**, `spine/04`), while the *image* feeds the deterministic **integrity stack**
   (SCORE) — `first_seen`/reverse-image (recycled-parade detection) + VLM `caption_vs_image_consistency`
   (miscaption). That stack is the **M4 override** flex: a fabricated-but-"corroborated" post (d11 + the d12/d13
   reshares) is killed by an integrity penalty **overriding the corroboration count**, so the node does *not*
   become confirmed — the single most memorable demo moment.
7. **The frozen SEED BASELINE** (`chanakya/ingest/seed.py` + a CLI entrypoint SHIP wires to `make extract`).
   Offline extraction over the frozen corpus → the committed claim bundles (item 6) → seed F0's store
   (`store.seed_from(bundles)`) → the SQLite evidence-log baseline SHIP bakes into the image (keyless boot,
   §7). Offline extraction **pins `ingest_time`** to a fixed freeze value so bundles are byte-stable;
   *reproducibility* is of the **seed-from-bundles** step (the bundles are frozen artifacts checked in), not
   of re-running the LLM — consistent with the frozen-log determinism story (`08` §1 property 5). This same
   corpus-extraction entrypoint **doubles as the reviewer's optional "extract-at-initial-run" mode** (master
   §7 mode 2): a keyed batch over the corpus through the live lane, producing the *same* claims as the
   committed bundles — so "boot from baseline" (mode 1) and "extract from raw at startup" (mode 2) converge on
   one graph.

## Contracts you consume (F0 froze these; do not edit)
Master §4.2 (`ClaimRecord` fields — you fill `source_id`, `doc_ref`, `kind`, `polarity`, `asserts`,
`payload` [stated s/p/o + ontology-type tags], `event_time`/`report_time`/`ingest_time`, `extraction`,
`premises`; leave `resolved_ref` **null** for RESOLVE; Source registry read via config store) · §4.3
(`rebuild()` + the observable-eval trigger you call) · §1 invariant #2 (LLM upstream) · §4.4 (read
`ontology` types + `sources` registry through F0's **config store**, never files) · F0's store `append`
(append-only; **no UPDATE/DELETE**, G3) + `seed_from`. If any must change → **F0-amendment PR** (master
Rule 3), logged in `PROGRESS.md` + `DECISIONS.md`.

## Acceptance criteria
- [ ] Extraction produces **valid `ClaimRecord`s for each `source_type`** present in the corpus (customs GD,
      tender, register, official PR, analyst-report imagery text, social, NOTAM/nav-warning) — one schema,
      one call, no per-source branch.
- [ ] **Guardrail:** on d05 (customs) the extractor emits the *stated* alias claim ("formerly ORIENT
      ELECTRONIC TRADING" / the SINO-GALAXY spelling variants) **and does NOT** emit a resolved edge
      connecting the shell consignee to the SAM end-user (the *unstated* front-company relationship).
- [ ] **One-claim-multi-span within a doc:** a doc restating one assertion twice → one `claim_id`, two
      `doc_ref` spans.
- [ ] **Separate claims across docs:** the same (s,p,o) in two docs (e.g. the 2021 import in d01 + d03) →
      two distinct `claim_id`s (never merged).
- [ ] **Keyless == live:** `ingest_bundle` appends the **same** claims as live extraction over the same doc.
- [ ] **Frozen seed baseline reproducible:** seeding the store from the committed bundles yields identical
      claims/store state across runs (byte-stable bundles; pinned `ingest_time`).
- [ ] **Live ingest triggers rebuild + observable-eval:** a live ingest calls `rebuild()` then
      `observe.evaluate` (asserted against F0's stub at Wave 1; real alert at Wave 2 integration).
- [ ] **G9** (ingest imports no `subjects`/ontology-instance content; no subject-keyed branch) and **G11**
      (generator stays ontology-blind — not regressed) stay green.
- [ ] `ruff` + `mypy` + `pytest` green, incl. all §5 gates. LLM-touching tests use **recorded/mocked**
      transcripts (`respx`/fixtures) — offline + deterministic; **one opt-in `@live` test** exercises the
      real API when a key is present.

## Owned paths (nothing else)
`chanakya/ingest/**`, `tests/ingest/**`, `corpus/scenarios/**/claims/**` (the committed pre-extracted
bundles). The `make extract` *target* is SHIP's; INGEST ships the CLI entrypoint (`python -m chanakya.ingest`)
it invokes.

## Out of scope
Location/place **resolution** — gazetteer match + `distinct-from` traps (RESOLVE); INGEST *does* the
coord-canonicalisation + Nominatim geocode at extraction and emits the **frozen canonical WGS84 + candidates** · the **scoring** (credibility/status/independence/first-seen/decoy/aggregator
detectors — SCORE) · the `/ingest` **HTTP endpoint** (API — INGEST exposes a callable) · **generating the
corpus** itself (DATA-C / `tools/`, ontology-blind, upstream of ingestion) · reading `answer_key.json`
(EVAL-only, never ingested).

## Worktree lifecycle
`git worktree add ../wt-INGEST -b feat/ingest` → implement inside owned paths only → PR `[INGEST]` → you
review & merge → you update `PROGRESS.md` → `git worktree remove ../wt-INGEST`.
