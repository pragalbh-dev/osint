# Session INGEST — Source-typed LLM Extraction + Live-Ingest Lane + Seed Bundles

**Wave 1 · depends F0 (merged) · soft-depends DATA-C `sources.yaml`/`ontology.yaml` (config content) and
F0's real store (for the committed seed only) · parallel-safe (disjoint ownership).**
Read `../00-master-plan.md` §4.2 (ClaimRecord + Source registry — the record you emit), §4.3 (rebuild stage
order + live trigger), §1 invariant #2 (LLM proposes *upstream* of the append), §5 gates **G9/G11**, §7
(keyless boot). This session owns the **ingest lane that feeds the store**; keep it THIN — one extraction
call per doc (a per-source all-optional extraction schema + transformer — item 2a), one `ClaimRecord` output,
one append→rebuild→observe path. All real stage logic (resolve/score/observe) is
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
is **EVAL-ONLY**, never ingested; the generator stays ontology-blind, **G11**) · `md/15` (the *why* behind
items 2a/6 — two-hash recycled-image detection & reverse-image-as-roadmap; subject-blind VLM observe→map;
one-ClaimRecord nullable-payload — cited research, this session).

## Scope (build these)

1. **Source-typed extractor framework** (`chanakya/ingest/extract.py`) — a dispatcher keyed on `source_type`
   where **every** `source_type` (customs GD, tender, NOTAM string, SIPRI register, ISPR PR, social post,
   analyst-report imagery text, …) routes through **its own all-optional LLM extraction schema** (the tool's
   `input_schema`, carrying generic ontology TYPES) → a **deterministic transformer** → the **one F0
   `ClaimRecord`** (structured feeds + prose alike) — see **item 2a** (`md/15` §3); the single-schema
   direct-emit is the later optimization. **No per-source *parsers*** (regex/format engineering = roadmap; the
   LLM fills a schema and the transformer maps it — neither is a parser). Ingestion is **source-typed, never
   use-case-typed** (**G9**): a customs doc ingests identically regardless of consumer; **no hard relevance
   gate, no branch keyed on subject/anchors**. Typed extraction is guided by the **ontology TYPE schema**
   (generic node/edge/event types from the config store) — never by subject anchors or ontology *instances*
   (**G11**). **Source binding
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
2a. **Per-source extraction schema + transformer → the one `ClaimRecord`** (the "generic claim vs source-specific
   schema" resolution — `md/15` §3; **DECIDED 2026-07-18**). Bare OpenIE triples are too noisy, and a *single*
   all-purpose emit-claims call asks too much of the LLM on structured rows. So each `source_type` gets its own
   **extraction pydantic schema** — **all fields optional** (optionality is the anti-fabrication lever, below),
   shaped to the source's native record — which the LLM fills, and a **deterministic transformer** maps that
   filled object into the **one F0 `ClaimRecord`**. The extraction schema **carries generic ontology node/edge
   TYPES** (never instances/subjects/anchors — **G11**), arranged so the transformer is a **simple field→type
   mapping, not inference**; the transformer also does node-typing (the claim's entity-descriptor `payload`
   carries `node_type`; the record already declares `asserts ∈ {entity, relationship, event}`) and the 3-tier
   attribute promotion below. Per-source *schemas* are source-typed, so this is **G9-safe** (source-typed ≠
   use-case-typed) and *more* G11-safe than a subject-aware direct emit (the LLM fills a source form; it never
   picks an instance or constructs the s/p/o). The single-schema **direct-emit is the later optimization**, not
   the demo. Two invariants on every schema + transformer:
   - **All-optional extraction fields = the anti-fabrication mechanism.** Rigid *required* fields provably force
     invention ("John Doe"); every extraction field is optional, the LLM fills only what the source *states*,
     and **when a source states nothing, the transformer emits NO claim** (→ feeds "insufficient evidence to
     assess"). *(The "format-restriction degrades reasoning" finding is about restrictive JSON-mode/instructions,
     not this design — a per-source schema of optional fields is permissive, and s/p/o construction is
     deterministic transformer code, not the prompt.)*
   - **3-tier attribute promotion (where source-native fields land — the transformer decides).** Each extracted
     field routes to one of: **(1) its own node/edge** (a consignee → `Organization`; an import → `Contract/
     Import event` — a graph citizen the ASK agent traverses); **(2) a knowledge-layer attribute** on a node
     used in computation (a declared quantity → `equipment_fingerprint` range; a role → `functional_role`); or
     **(3) a nullable typed `attributes` bag** on the claim for source-native context with no ontology home
     (HS-code, container#, BoL#) — traceable + queryable, *not* traversed, promotable to tier 1/2 later if it
     turns out material. So a customs BoL row yields **many** typed claims (consignee, ports-as-`Location`,
     date-as-`Date`, value-as-`Quantity`), each keeping the **verbatim raw cell on `doc_ref`** (**G4**). *(The
     typed `attributes` field is a small F0-amendment — nullable, raise-not-widen per master Rule 3.)*
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
   Provider abstraction — **DECIDED 2026-07-17** (DECISIONS.md "Extraction & ingestion"): **provider-native
   function-calling, NO DSPy / NO litellm** — one strict **per-source extraction tool** (`input_schema` = the
   source's **all-optional** extraction schema carrying generic ontology TYPES; a deterministic transformer maps
   its output → the one `ClaimRecord`, item 2a), forced `tool_choice`, behind a thin 2-method `LLMClient`
   protocol. **Extraction provider = Gemini**
   (native `google-genai` function-calling — the frozen bundles are Gemini output); **Anthropic
   `claude-opus-4-8` is the ASK-agent provider + an optional 2nd extraction impl** behind the same protocol.
   **No `temperature`/`top_p`/`top_k`** (HTTP 400 on Opus 4.8; never pass sampling params to Gemini either);
   `extraction.model` (Gemini id — verify for the key/region) + `extraction.model_conf` held at **1.0** live in
   config; optional OCR via `AZURE_DOCINTEL_*` (item 1a).
   **`method ∈ {llm, vlm}` — same output, different modality.** The claim OUTPUT is source-agnostic (one
   ClaimRecord schema); only the *loader* + *modality* differ (never the graph schema — G9). **Posture
   (md/11 A1, updated 2026-07-17): an imagery doc emits BOTH — the analyst-report `.txt` runs the normal text
   path AND the `.png` is read by the VLM** (additive; the two are separate evidence objects the oracle keeps
   apart — the relabeled-real pixel-vs-attribution boundary). **VLM path (IN SCOPE — DECIDED 2026-07-17;
   build additive, text path + integrity stack first; SAME claim path):** a VLM
   reads the pixels and emits **(a)** an **observation** claim (`kind: observation, method: vlm`) of what is
   literally seen — e.g. `<site_S, occupancy_state, occupied>` or `<site_S, observed_signature,
   rectangular-tel-pad-ring>`, a `count` as a `Quantity` — filling the observed content + the **soft VLM
   field `caption_vs_image_consistency`** only. **The structural M4 detectors are DETERMINISTIC, not the
   VLM** (`spine/04` §D, fail-closed; full analysis + citations in `md/15` §1): at ingest **code computes and
   freezes TWO hashes with opposite jobs** — a **`sha256`** (exact-byte; catches only a *bit-identical* reshare
   → same-origin grouping; useless for recycled detection, since any platform recompression flips ~half its
   bits — the avalanche effect) and a **perceptual hash** (**PDQ 256-bit primary**, or 64-bit DCT `pHash`
   fallback; near-dup by **Hamming ≤ threshold** [config] + a PDQ quality gate) — plus any EXIF
   capture-date/`resolution`/`geo` (often stripped after one platform hop). **`first_seen` / coordinated-
   timestamp / aggregator are then determined deterministically inside SCORE's `rebuild()`** (never LLM) over
   the frozen hashes against a **local corpus-internal `perceptual-hash → earliest-observed-date` index** —
   `first_seen = recycled` when a near-dup cluster's earliest observed date predates the claim's asserted
   `event_time`, catching a *real, correctly-captioned, but past* image. PDQ catches the **lazy** recycle (screenshot / re-upload /
   format-convert / mild resize); a determined **crop + rotate (>~5°) + overlay** adversary slips the threshold —
   the **lazy-recycle bottleneck** — so heavy edits need learned copy-detection (SSCD, roadmap). A near-dup is a
   **penalty + HITL flag, never proof and never an auto entity-merge** (false-merge of two genuinely-different
   SAM sites is the dominant risk here). **Reverse-image search (TinEye et al.)** is the strong *production*
   first-seen tool (Bellingcat's first move) but stays **roadmap** — deferred **not** for determinism/keyless
   (the app *is* keyed; reverse-image would run at ingest as a frozen **proposer**, never inside `rebuild()`, so
   G1 doesn't touch it) but for **build-budget + the crawl-date≠first-appearance limitation**; if wired, its
   result is frozen on the record like any proposer, behind a swappable adapter. When the local index cannot date
   an image → **"insufficient evidence to assess — first-appearance not resolvable from indexed corpus."**
   `decoy_risk` is the single-pass signature flag SCORE gates on. And
   **(b) The signature→variant leap is NOT a VLM output — it is a guided-LLM CORROBORATION** (`md/15` §2;
   **REVISED 2026-07-18**). The VLM never asserts "HQ-9" from pixels (standalone variant-ID-from-imagery → the
   **design note**, "further investigation"). Instead a **guided LLM call corroborates the observed signature
   against the ingested reference literature** and emits an `inference` claim, `premises: [the observation
   claim_id, the literature-fingerprint claim_id]`, asserting `<site, consistent-with / based-at, HQ-9>` at
   **probable** (`decoy_risk` cap; confirmation needs a 2nd discipline-independent look — the locked Rahwali
   beat). The reference fingerprint is **discovered from ingested reference text** (Army-Technology / geimint /
   SIPRI-class describing the HQ-9 site geometry) — *not* a hand-authored `signature_library` config; the
   literature is just another sourced claim, so the inference is fully traceable to **both** premises. **This
   same inference is what lets a satellite image corroborate a text/news "HQ-9 at base X" claim:** the raw
   observation asserts only a *signature* (a different predicate), so the bridge inference is what puts the image
   and the news on the **same resolved `based-at HQ-9` edge**, where SCORE's independence-grouped corroboration
   (EO-discipline vs text-discipline) promotes it — the join is geo-resolution of both to one `Basing site` node
   (`md/13`).
   **Subject-blind structured observation (the "how does it know to say *rectangular*?" discipline; `md/15`
   §2).** The imagery per-source extraction schema (item 2a) is **subject-blind and all-optional**: it captures
   **generic observable features** — geometry/layout tokens (`radial-revetments`, `central-radar-berm`,
   `circular-access-road`), `occupancy_state`, `count` as a **`Quantity` RANGE with abstention** (never a
   fabricated integer — VLM counting is unreliable), a **free-text description**, plus `caption_vs_image_
   consistency` and frozen `geo`/`gsd` — **never a variant field** ("which HQ-9?" is not askable). This is the
   imagery-lane enforcement of **G9/G11** and is *empirically* load-bearing: naming "HQ-9" collapses the VLM onto
   its memorized prior (SOTA VLMs ~100% on canonical vs ~17% on counterfactual images; a "sycophantic modality
   gap" makes them cave to leading prompts far more for images than text). Structuring with *optional* fields + a
   free-text slot (not a forced enum classification) keeps extraction reliable without the reasoning degradation
   of rigid formats. The "*anything is rectangular*" trap is disciplined by the guided-LLM corroboration above —
   it takes co-present features + a **literature match** to assert a variant, at probable — **not** the VLM
   guessing. A deterministic **resolution-floor gate** applies on the **deliberate low-res beat** (Sentinel-2
   10 m; the main confirm frames are **Esri ~0.5 m**, e.g. `d07`): a variant corroboration on a coarse frame →
   "insufficient evidence to identify variant"; **`occupancy_state = empty-pads` → "insufficient evidence to
   assess deployment,"** never a deployment assertion.
   **Social post = image + caption is the same lane**, at the opposite trust tier: the *caption* yields a
   **stated observation** claim at the **social source-tier** (low-provenance lead — raises to *probable*,
   **never confirms alone**, `spine/04`), while the *image* feeds the deterministic **integrity stack**
   (SCORE) — the **local first-seen hash-index** (recycled-parade detection; reverse-image search = roadmap
   enrichment, `md/15` §1) + VLM `caption_vs_image_consistency`
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
      tender, register, official PR, analyst-report imagery text, social, NOTAM/nav-warning) — via a per-source
      all-optional extraction schema + deterministic transformer (item 2a); no per-source *parser*, no
      subject-keyed branch.
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
- [ ] **Per-source schema + transformer:** each `source_type` has an all-optional extraction schema; a
      deterministic transformer maps the filled object → `ClaimRecord`(s); the LLM never constructs the s/p/o
      and never names a subject/instance/anchor (**G9/G11**).
- [ ] **All-optional = no fabrication:** a sparse source fills only what it states; a source stating nothing
      yields **zero** claims (not an invented one).
- [ ] **Many-claims-per-row + 3-tier attributes:** one customs BoL row → multiple typed claims; each extracted
      field lands in its own node/edge, a knowledge-layer attribute, OR the nullable typed `attributes` bag,
      each keeping the verbatim raw cell on `doc_ref`.
- [ ] **Two-hash integrity:** every image record carries a frozen `sha256` (exact) + **PDQ** perceptual hash
      (near-dup); recycled `first_seen` is computed in `rebuild()` from the local hash-index — **no reverse-image
      call inside `rebuild()`**.
- [ ] **Subject-blind structured observation:** the recorded VLM transcript contains no subject/anchor/variant
      name; the observation claim carries only generic feature tokens + occupancy + count-as-`Quantity`-range +
      free-text + geo/`gsd` — **no variant field**.
- [ ] **Imagery corroboration is a guided-LLM inference, not a VLM leap:** signature→variant is an `inference`
      claim `premises:[observation, literature-fingerprint]`, capped at probable; it puts an image + a text
      "HQ-9 at base X" claim on the same resolved edge (geo-resolution to one `Basing site`). Empty-pads /
      coarse frame → insufficient-evidence, never a fabricated assertion.
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
(EVAL-only, never ingested) · **reverse-image-search enrichment** (TinEye/Yandex/Lens adapter — roadmap;
INGEST computes only the *local* hash + freezes it, `md/15` §1) · **learned copy-detection embeddings**
(SSCD/DINOv2 — roadmap; if ever built, computed once at ingest and frozen, never in `rebuild()`).

## Worktree lifecycle
`git worktree add ../wt-INGEST -b feat/ingest` → implement inside owned paths only → PR `[INGEST]` → you
review & merge → `git worktree remove ../wt-INGEST`.
