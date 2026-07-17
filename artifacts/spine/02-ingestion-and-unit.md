# Spine — Ingestion & Unit of Analysis

Covers: the "right unit of analysis rather than blindly chunking" requirement; claim normalization; where
relevance lives; extendible subjects. This is where three of the questions in `../md/questions.md`
collapse into one decision.

---

## Decisions

### Unit of analysis = the sourced claim, not the document
The wrong unit is the **document** (chunk into 512-token windows and embed) — that destroys structure. A
customs manifest has *rows*; a tender has *lots/line-items*; the meaningful atom is not a text window.

The right unit is the **sourced claim about an entity/edge**:
`Source S, dated D, asserts <subject, predicate, object>` — e.g. "customs row R asserts consignee C
imported component P on date D." One document → many claims; each document's assertion is its own claim —
claims are never merged across documents — and once resolution pins a shared `resolved_ref`, those separate
claims corroborate one another. Right because it (a) matches the natural granularity of the sources, (b)
carries provenance/confidence/freshness, (c) enables corroboration (independent resolved claims sharing a
`resolved_ref` → confirmed vs probable, per `04-credibility.md`), (d) makes traceability work (node →
claims → doc → exact span).

**Two granularities, bridged by one concept:** the **claim** is the *evidence* unit (raw, immutable,
one per source-doc assertion); the **entity/edge** is the *knowledge* unit. The bridge is the **resolved
claim** — the same claim plus a `resolved_ref` (which real entity/edge its subject/object point at) once
resolution runs; corroboration and `assertion_confidence` are computed over resolved claims, never raw
ones (the bi-level model, `01-graph-and-ontology.md`).

### The normalization step is the "right unit" work
Turning a customs row, a tender lot, and an academic sentence all into one
`(subject, predicate, object, source, date, confidence)` claim schema **is** the "find the right unit
rather than blindly chunking" requirement. This normalization is the graded work, not the chunking.

### Relevance is encoded at three layers — there is no standalone hard relevance gate
Direct answer to `../md/questions.md` ("is relevance a pipeline stage, or encoded in extraction/
disambiguation?"): **encoded, at three layers of decreasing hardness.**

1. **Ontology-typing at extraction (hard).** Extract *all* entities/claims matching the ontology types
   from *every* ingested doc. A doc with nothing of your types yields nothing. "Relevance to the domain"
   *is* the ontology. Subject-agnostic, bottom-up.
2. **Subject-proximity at scoping (soft, at view/query time).** An entity is material to a subject if
   within N hops of the subject's anchors, or matches a materiality criterion (chokepoint-relevant type).
   Computed *after* resolution.
3. **Credibility at scoring (soft).** Per-resolved-claim `claim_credibility` and the pooled
   `assertion_confidence` (see `04-credibility.md`) sink low-trust material in ranking/status; nothing is
   deleted.

**Why relevance must NOT be a hard ingestion gate** (the alias worry): the shell company that imports the
radar is not visibly "about the subject" until resolution connects it. Filter at ingestion on "mentions
the subject" and you delete the very thing the analysis exists to find. **Resolution is the mechanism that
rescues "looks irrelevant → is actually material."**

### One decision produces four properties
Bottom-up typed extraction into one graph gives you, all at once: **one graph**, **subject-agnostic
ingestion**, **emergent relevance**, and **extendible subjects**. They are the same decision.

### Extendible subjects come for free ("edge of time")
Because extraction is subject-agnostic, adding a subject does **not** trigger re-extraction — it drops a
new anchor set onto a graph that already has historical depth, and future docs get typed-extracted
regardless of subjects, so the new subject picks them up automatically. A subject added this morning
instantly has back-history *and* live coverage. Had we subject-filtered at ingestion, every new subject
would start from zero — the opposite of what intelligence work at the edge of time needs.

### Materiality criterion (an axis of depth)
"Capture any entity material for chokepoint detection." What counts as *material* must be defined and
defensible — derived backward from the target queries + domain doctrine. This is a research task; see
`../C/01-materiality-ontology.md`. The defense: *"I modeled exactly what the chokepoint/ORBAT questions
require, no more."*

### Extraction = everything via LLM, live at ingest (seeded baseline, not frozen-only)
**Decided** (see `08-spine-2.0-review.md` §D, updated 2026-07-17 in `09-retrieval-and-tools.md`): extraction
is **everything via LLM**, no per-source-type engineering (parsers, regex, format-specific pipelines) — a
time-gated demo, not an optimization exercise; Gemini is an optional 2nd provider. Structured sources
(customs rows, tender lots, NOTAM strings) and prose alike go through the same LLM claim-extraction call
against the claim schema. Extraction runs **at ingest time, once per doc**; its output is a cited, versioned
record appended to the evidence log. A **seeded baseline** of pre-extracted claims ships for a keyless boot
+ reproducible graded beats, **but extraction is a live runtime capability, not frozen-only**: `make ingest`
/ a UI action extracts a new doc live and appends it, driving `rebuild()` → observable-eval
(`09-retrieval-and-tools.md`). The LLM runs **upstream of the append**, so **nothing about extraction
re-runs inside `rebuild()`** — the LLM-free-`rebuild()` invariant holds and the view stays deterministic.
(Real per-source parsers as a later cost/precision optimization stay a design-note item — see Research
directions below, not the demo build.)

**Extract-raw guardrail (what LLM-only must and must not do).** The LLM extracts the claims a source
*states* — **including any alias / `same-as` / equivalence relationship the source explicitly asserts**
(e.g. a doc saying "FD-2000 is the export designation of the HQ-9" → a sourced `same-as`/alias claim).
Such a stated-equivalence claim is extracted like any other, and then feeds resolution as the
`source_asserted` merge signal (`03`, `08` §3.9) — but the merge *decision* still runs through the
deterministic `merge_score` + bands + HITL, never the extractor. What the LLM must **not** do is resolve
or normalize what the source leaves *unstated*: it never decides two differently-named entities are the
same on its own, never silently collapses a front-company cover story, never "cleans up" hedged language.
**Stated relationship → extract it; unstated resolution → the pipeline's job.** This is the
anti-circularity / messiness-preservation guarantee that replaces parser-first extraction (cf.
`../md/06-preflight-audit.md` M-DATA-1, the d05 cover-story case).

### Provenance span, defined — and the claim de-duplication rule
A **provenance span** is the exact location inside a source document where a claim is stated: a
paragraph, a line, a table row, a frame — whichever unit is native to that source. De-duplication rule:
**one claim with one-or-more spans within the same document** (the doc restates the same assertion twice
→ one claim, an extra span), but **a separate claim per document**, even when two documents assert the
identical fact — separateness across documents is what lets corroboration count them (claims are never
merged; only entities merge — see `08-spine-2.0-review.md` §B).

### Location standardization and reusable base extraction objects
Locations extracted from prose/records are **standardized through Nominatim (geocoding) plus an LLM
disambiguation pass** for what Nominatim can't resolve alone (partial names, transliterations, informal
place references) before they become entity attributes. Dates and locations are each modeled as a
**reusable base extraction object, built once with Pydantic and reused across every source type and every
claim** — not re-specified per ingestion path.

---

## Open questions
- **How aggressive is typed extraction at the edges** — do we extract low-salience mentions (a place name
  in passing)? Leaning yes at demo scale; at production scale this is the cost-tiering question below.

(Extraction model/method and claim de-duplication/provenance-span are now **decided** — see the Decisions
section above.)

## Research directions
- **Cost-only relevance prefilter for scale (design-note "breaks at scale").** At volume, typed extraction
  from *everything* is expensive. A prefilter routes low-signal docs to a cheaper/deferred lane — **never
  deletes** (recall-preserving), so it's an optimization, not a correctness gate. Not needed for the demo
  (extract everything, LLM-only, over the ~40–50 doc corpus — see `09-corpus-sizing.md`).
- **Structured-source parsers (future/production only, not the demo).** Real format specs for the C
  sources (NOTAM/NAVAREA strings, customs BoL rows, tender skeletons) are catalogued with real samples in
  `../md/05-data-scoping-C.md` §2/§6 — useful as a later per-source-type optimization on top of the
  LLM-only demo extraction, not a substitute for it.
