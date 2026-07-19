> **✅ DONE (2026-07-19, branch `feat/ingest-pdf-geo`, stacked on #17).** Both workstreams built + tested
> (403 pass / 6 skip, gates green, ruff+mypy clean) + validated LIVE (real Azure OCR + Gemini multimodal).
> Notes: (1) "keyless" clarified — the pymupdf fallback is the *no-OCR-key* path, still keyed for the LLM;
> only frozen-bundle boot is truly keyless. (2) RESOLVE's `normalize()` is UNMERGED (RESOLVE not-started),
> so the gazetteer normaliser is a byte-identical **local copy**, test-pinned (dedupe when RESOLVE lands).
> (3) Default Gemini model fixed to `gemini-flash-latest` (`gemini-2.5-flash` now new-user-404). Full
> write-up: `DECISIONS.md` §6 INGEST "PDF-multimodal + geocoding follow-up" + `PROGRESS.md` INGEST follow-up.

# INGEST follow-ups handoff — PDF handling, geocoding wiring, keyless framing

**For:** a future agent continuing the INGEST lane after PR #17 merges. **Self-sufficient:** everything you
need is below or referenced by path. **Status of INGEST:** the source-typed extraction + live lane + keyless
seed are built, reviewed, CI-green (PR #17, `feat/ingest`, ~4.3k LOC, 379 tests). These are the *known,
deliberately-deferred* follow-ups — none block the PR; all improve real capability.

Owned code you'll touch: `backend/chanakya/ingest/{loaders,adapters,extract,client,imagery,seed}.py`. Read
`loaders.py` (the `(text, regions[])` contract) + `__init__.py` (public surface) + `client.py` (the extraction
client) first. Governing docs: `sessions/INGEST.md` + `spine/02` + `md/13` (location) + `md/15` (imagery).
Gates it must not break: `tests/gates/test_g{1,2,4,9,11}_*`.

---

## 0. Framing correction: what "keyless" actually requires (read first)

**Keyless is an ADD-ON for the reviewer demo, not a capability constraint.** It means one thing: the app must
**boot and run the hero query from frozen artifacts** (seeded SQLite + committed pre-extracted bundles)
**without an API key** (master §7 run-mode 1; `SHIP.md`; `API.md`). That is the *only* strong keyless
requirement.

It does **NOT** mean extraction / geocoding / VLM / OCR must be avoided or crippled. Those are the **optional
keyed front-end** — they run at *extraction / build time* (keyed), and keylessness is achieved by **freezing
their output into the committed bundles**, which a keyless reviewer replays. So: adding a capable PDF library,
calling Nominatim, running a multimodal read on a page — **all fine.** The only load-bearing invariant is
**G1/G2**: nothing keyed/networked/random may run *inside* `rebuild()`; extraction is *upstream* of the append
so it may do anything. (`md/15` §4 already says this: *"'keyless' in the project docs only means the app boots
+ runs the hero query without a key."*)

**Where the strong keyless requirement lives (do NOT weaken these):** `CLAUDE.md` (stack line),
`00-master-plan.md` §7 (run-modes), `sessions/SHIP.md` (boot from seeded baseline), `sessions/API.md` (keyless
bundle body), `sessions/INGEST.md` items 6–7. Everywhere else "keyless" is descriptive. The line you must not
cross: keyless BOOT needing a key. Making extraction richer is not that.

---

## 1. PDF handling — DECIDED (render every page → multimodal per-page extraction)

**Current state (wrong model for real PDFs):** `loaders.load_pdf` runs `pdftotext` (text only), assembles the
whole doc, and `extract_document` sends the **entire doc text in ONE call**. Embedded figures are dropped;
scanned pages need a separate OCR branch gated on a brittle "no page returned any text" heuristic. Three
problems: (a) no images, (b) brittle born-digital/scanned detection, (c) no per-page context / no chunking for
large docs.

**Decision — one capable, non-brittle path:**

1. **OCR every PDF — no born-digital detection (it was a premature optimization; drop it).** When an OCR key
   is present, run **Azure Document Intelligence** (the `ally-pipelines/.../ai_extraction_v2/dump/file_processor.py`
   pattern you sent) on the **whole document in ONE call** — Azure returns text + tables + layout + figure
   regions **already split by page**; there is no per-page loop and no born-digital/scanned question.
   **Fallback to `pymupdf` (fitz)
   only when no OCR key is available** (the keyless-extract path): pymupdf yields the text layer + renders
   every page to an image locally, no key, no network. Either way the loader emits, per page, **the page's
   text + the page's image**. One branch, one decision — `AZURE_DOCINTEL_*` configured? → OCR : pymupdf — and
   **no text-density heuristic anywhere.**
2. **One multimodal extraction call over the document — NOT a separate VLM call, and NOT a per-page loop.**
   The single OCR call already returns the whole doc's text + figures **paged**; feed that text + the page
   images to **one** multimodal extraction call (Gemini `contents=[text, inline_data,…]`; Claude
   `content=[text, image,…]`) so the model reads prose + tables + diagrams together with full context, and
   carry **per-page provenance** (`DocRef.page`/`bbox`) from the OCR's paging. **Chunk (windowed by page) ONLY
   when a document is too large for one call** — a size guard, not the default. This removes the separate
   VLM-call-for-figures step entirely.
3. **Client change:** extend the extraction seam to carry images on the *extract* call —
   `extract(*, tool_name, input_schema, system, text, images: list[(bytes, media_type)] = [])` — instead of a
   separate `read_image`. (Keep `read_image` only for the adversarial standalone-imagery lane below.)

**The ONE guardrail that stays (decided, not optional):** the **subject-blind separate VLM lane remains for
ADVERSARIAL standalone imagery** — satellite `.png`, social `.png` — where the image's *identity* is the
contested claim and feeding the subject name to the model is the documented failure mode (`md/15`: the
"sycophantic modality gap"; empirically ~17% on counterfactual images when led). PDF / reference-literature /
trade-media figures are **explanatory** — the surrounding text is legitimate context — so they go multimodal
per §1.2. **Route by source:** reference/trade-media/customs/tender/official docs → multimodal page read;
`satellite`/`named-social`/`anon-social` imagery sources → the existing subject-blind `imagery.py` lane. This
split is what keeps the credibility story intact while making document reading fully capable.

**Deps:** `pymupdf` (AGPL-3.0 — fine for the take-home, flag it in the design note; permissive alt =
`pdfminer.six` + `pypdf`, but you lose one-lib page rendering). Thresholds (figure min-size, render DPI) in
config (G6).

**Acceptance:** a figure-bearing PDF fixture yields per-page claims that reference both prose and figures from
one multimodal call, with `DocRef.page`/`bbox` provenance; a scanned PDF is read via the rendered page image
(no separate OCR needed for the demo); adversarial satellite/social imagery still goes through the subject-
blind lane (no subject leak); `test_imagery.py` invariants hold.

---

## 2. Geocoding wiring — DECIDED (gazetteer-first exact-match, Nominatim fallback)

**Source of truth:** `wt-RESOLVE/tmp/conv/INGEST-locations-gazetteer-vs-nominatim.md` (RESOLVE, 2026-07-19),
summarised here so this is self-sufficient.

**The split (locked):** INGEST produces **coordinates** (at extraction, upstream — network OK); RESOLVE
produces **identity** (inside `rebuild()`, pure/offline — G1). One `Location` carries both: INGEST fills
`wgs84_lat/lon` + `geocode_candidates` + `precision_class` and **leaves `resolved_place_ref = None`**; RESOLVE
fills identity later. Geocoding is frozen once at ingest because Nominatim drifts run-to-run and `rebuild()`
must be byte-deterministic (G2).

**Current state:** the geocoding code is wired + tested in `adapters.py` (`_default_geocoder()` = geopy
Nominatim; `normalize_location` → `_resolve_toponym` + `_resolve_relative_location`, incl. the Rahwali
bearing+distance offset). After the review fix it is **opt-in** (no injected geocoder → offline) and **the
extract path does not pass a geocoder yet**. Your job: build the resolver + thread it.

**Build a two-stage `Geocoder`:**
1. **`GazetteerGeocoder(places_config)` — offline, EXACT match only.** Return a node's `canonical_dd` iff the
   *normalised* mention exactly equals its `canonical_name`, a seeded `alias`, or a hard-ID (`icao`/`locode`).
   **Reuse RESOLVE's normaliser** (`chanakya/resolve/normalize.normalize()`, post-#16 — coordinate with
   RESOLVE so keys can't drift): transliteration → casefold → collapse non-alnum runs → strip. **No fuzzy, no
   proximity, no nearest.** Read ONLY `canonical_name`/`aliases`/`icao`/`locode`/`canonical_dd`; do NOT read
   `proximity_radius_m`/`distinct_from`/`place_proximity_hitl_multiplier` (RESOLVE-only).
2. **Nominatim fallback** for the open world → `ChainedGeocoder([gazetteer, nominatim])`.

**Withheld-alias trap:** "Chaklala" is deliberately NOT in the seed (the earned-merge demo). Exact-match-on-
seeded-forms-only means it won't hit the gazetteer → falls to Nominatim / stays raw → RESOLVE earns it. **Do
not add withheld forms.**

**Thread it:** `extract_document(..., geocoder=None)` → each `transform_*` → `_Emitter.geocoder` →
`em.location(raw)` → `normalize_location(raw, geocoder=…)` (7 call-sites; centralise via `em.location`).
Default `None` = offline (tests + keyless). `seed.extract_corpus` / the `python -m chanakya.ingest extract`
CLI build the `ChainedGeocoder` and pass it, so live `make extract` geocodes + freezes coords into bundles;
keyless boot reads them. Nominatim etiquette: 1 req/s, real `user_agent`, cache within a run.

**Acceptance:** a seeded name (Nur Khan/Rahwali/a Karachi port) resolves offline to its `canonical_dd`
(`source="gazetteer"`); an unseeded name falls to (mockable) Nominatim; "Chaklala" does NOT hit the gazetteer;
the Rahwali offset still computes; `resolved_place_ref` stays `None`; tests default `geocoder=None` + stay
byte-stable.

---

## 3. Quick reference index

- Loader + PDF: `backend/chanakya/ingest/loaders.py` (`load_pdf`, `_pdf_page_texts`, `OcrProvider`); OCR
  provider `ocr_azure.py`; the external OCR *pattern*: `ally-pipelines/.../ai_extraction_v2/dump/file_processor.py`.
- Geocoding: `adapters.py` (`normalize_location`, `_resolve_toponym`, `_resolve_relative_location`, `Geocoder`
  protocol, `_default_geocoder`).
- Multimodal client seam: `client.py` (`ExtractionClient.extract`/`read_image`, Gemini/Anthropic impls — add
  `images=` to `extract`). Imagery lane (adversarial): `imagery.py` (`read_image_document`,
  `ImageryObservation`, `SignatureCorroboration`).
- Extraction threading points: `extract.py` (`_Emitter`, `_emitter`, 6 `transform_*`, `extract_document`);
  seed/CLI `seed.py` + `__main__.py`.
- Gazetteer `config/places.yaml`; RESOLVE normaliser `chanakya/resolve/normalize.py` (post-#16).
- Design refs: `md/13` (location), `md/15` (imagery/multimodal + keyless clarification), `spine/02`,
  `00-master-plan.md` §7 (keyless run-modes), the RESOLVE geocoding note.
- Already logged: `PROGRESS.md` "INGEST" note, `DECISIONS.md` §6 "INGEST".

*— INGEST session, 2026-07-19. None of this blocks PR #17; decided, deferred to a follow-up agent.*
