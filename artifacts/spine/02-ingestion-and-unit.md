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
imported component P on date D." One document → many claims; one claim → corroborated by many documents.
Right because it (a) matches the natural granularity of the sources, (b) carries provenance/confidence/
freshness, (c) enables corroboration (count independent claims on the same edge → confirmed vs probable),
(d) makes traceability work (node → claims → doc → exact line).

**Two granularities:** the **claim** is the *evidence* unit; the **entity** is the *knowledge* unit
(the bi-level model, `01-graph-and-ontology.md`).

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
3. **Credibility at scoring (soft).** Low-credibility/noise claims sink; they are not deleted.

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

---

## Open questions
- **Extraction model & method** — LLM function-calling to the claim schema vs a hybrid (regex/parsers for
  structured sources like NOTAM/customs rows + LLM for prose). Leaning hybrid: structured sources deserve
  real parsers; only prose needs the LLM. TBD.
- **How aggressive is typed extraction at the edges** — do we extract low-salience mentions (a place name
  in passing)? Leaning yes at demo scale; at production scale this is the cost-tiering question below.
- **Claim de-duplication** — the same claim restated in two paragraphs of one doc: one claim with two
  spans, or two claims? Leaning one claim, multiple provenance spans.

## Research directions
- **Cost-only relevance prefilter for scale (design-note "breaks at scale").** At volume, typed extraction
  from *everything* is expensive. A prefilter routes low-signal docs to a cheaper/deferred lane — **never
  deletes** (recall-preserving), so it's an optimization, not a correctness gate. Not needed for the demo
  (extract everything over ~10–15 docs).
- **Structured-source parsers** — real format specs for the C sources (NOTAM/NAVAREA strings, customs BoL
  rows, tender skeletons) are catalogued with real samples in `../md/05-data-scoping-C.md` §2/§6.
