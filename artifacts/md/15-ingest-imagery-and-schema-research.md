# 15 — Ingest deep-dive: imagery handling & extraction-schema strategy (research reference)

**What this is.** The cited research + design reasoning behind three ingest questions that `plan/sessions/INGEST.md`
now encodes but must not re-argue inline:

1. **Image integrity** — the hash changes when a photo is shared (WhatsApp/X recompress it); what actually
   detects a recycled image, and *why not TinEye*.
2. **Overhead / satellite imagery** — what to extract, how an image *corroborates* a textual HQ-9 sighting,
   and the "how does it know to say *rectangular*?" priming trap (prompt vs a satellite-specific schema).
3. **Generic claim extraction vs source-specific pydantic schemas** — is "one good-enough claim-extraction
   prompt" the right thing for *all* source types, or do we need per-source schemas?

**Provenance / method.** Produced 2026-07-18 by a fan-out deep-research workflow (grounding readers over the
spine/C docs → per-question web research → adversarial refutation + staleness verification → synthesis), then
**revised in discussion with the user** (the design conclusions in §2–§3 reflect that discussion, not the raw
first-pass synthesis). **Every load-bearing external *fact* in §1 was independently re-verified (20/20
CONFIRMED).** §2/§3 facts verified with two tempering caveats, flagged inline. This doc is the audit trail;
`INGEST.md` carries only the resulting rules. It sits with `md/13` (location), `md/14` (retrieval) as an
ingest/reference companion.

---

## §1 — Image integrity: cross-platform hashing + reverse-image search

### 1.1 The user is right: sharing an image changes its hash — and it matters *which* hash

Social platforms **re-encode** every image on the "compressed" send path: WhatsApp downsamples to ~1600 px on
the longest edge (HD mode ~3000 px but **still re-encodes**), re-compresses JPEG at ~**60–75 %** quality, applies
chroma subsampling, and **strips EXIF** (GPS/camera/software) — net file-size drop **80–96 %**. Telegram/X/Facebook
do the same; only Telegram **File/Document** mode preserves original bytes + metadata. *(Sources: WhatsApp image-size
guides; "Which apps strip photo metadata — 2026 guide", dev.to; fast.io metadata-preservation writeup.)*

Consequences:

- **Cryptographic hashes (SHA-256, MD5) do NOT survive *any* recompression.** By the avalanche / strict-avalanche
  property, a one-bit input change flips ~**128 of 256** output bits (mean 128, σ≈8) — a recompressed copy's digest
  is completely unrelated. There is no "close" in crypto-hash space. *(Wikipedia, Avalanche effect; MDPI "Strict
  Avalanche Criterion of SHA-256", 2024.)* → **SHA-256's only correct role is detecting a *bit-identical* reshare
  (same-origin grouping); it can never do recycled-image matching.**
- **A perceptual hash does NOT produce the *same* value after resharing — it produces a *similar* one**, matched by a
  **distance threshold** (Hamming ≤ N), not by identity. It hashes the low-frequency DCT *structure* (the coarse
  shape), which recompression/resize largely preserves. It survives re-encode/mild-resize/format-convert well
  (PDQ matched ~99.96 % of format-converted images); it **fails under heavy crop, rotation (>~5° for PDQ), large
  overlays, mirroring**.

### 1.2 What actually catches a recycled image: a perceptual hash, computed at ingest, indexed locally

- **PDQ (Meta / ThreatExchange) — the chosen hash:** a **256-bit** DCT-based hash (16×16 subimage-average →
  quantized DCT, an evolution of pHash's DCT flavour), with a **0–100 quality score** (discard ≤49) and a documented
  match threshold of **Hamming ≤ 31** ("30 or less"; random pairs ~128). Offline: `pip install pdqhash`. *(facebook/
  ThreatExchange `pdq`; arXiv 1912.07745; PyPI `pdqhash`.)*
- **The lazy-recycle bottleneck (documented limitation, DECIDED to accept).** PDQ reliably catches the **lazy** recycle
  (screenshot / re-upload / format-convert / mild resize) but a determined **crop + rotate(>~5°) + overlay** slips
  the threshold. Heavy manual edits need **learned copy-detection (SSCD, DISC2021; arXiv 2202.10261)** — more robust
  but needs a neural model → **roadmap** (if ever built, compute the embedding *once at ingest* and freeze the vector;
  the no-runtime-embeddings rule forbids *computing* in `rebuild()`, not *comparing* a frozen vector). PDQ stays a
  **penalty + HITL flag, never proof.**
- **The deterministic recycled-parade mechanism (fits G1/G2):** at ingest, **code** computes and freezes **both**
  hashes — `sha256` (exact-dup / same-origin) **and** PDQ (near-dup) + quality score + any EXIF. In `rebuild()`
  (pure, network-free, LLM-free), a `PDQ → earliest-observed-date` index does a Hamming-threshold near-dup lookup;
  `first_seen = recycled` (0.30 penalty) fires when a near-dup cluster's earliest date predates the claim's asserted
  `event_time`. **Failure mode = false-merge of two genuinely-different SAM sites** (near-identical launcher imagery),
  so a near-dup is a **penalty + HITL flag, never an auto entity-merge**; gate on PDQ quality ≤49.

### 1.3 Why *not* TinEye — with the reasoning corrected

TinEye is the **right production tool** (what Bellingcat uses; the only service with a public web-crawl API + a
"sort by oldest crawl_date" first-seen feature). It is **deferred to the roadmap** — but *for the right reasons*:

- **NOT for "determinism/keyless."** *(First-pass synthesis wrongly used this as the gate; corrected here.)* The app
  **is keyed** (live extraction uses `ANTHROPIC_API_KEY`/`GEMINI_API_KEY`); "keyless" in the project docs only means
  the app can *also* boot from the seeded baseline without a key (a reviewer convenience), not that the app avoids
  APIs. And reverse-image would run **at ingest as a frozen proposer, never inside `rebuild()`** — so gate **G1**
  (pure/network-free `rebuild()`) never touches it. If wired, its result is **frozen on the record** like every LLM
  output and replays deterministically.
- **The real reasons to defer:** **(a) build-budget** (~4 days); **(b) TinEye's "first found on" is a crawler-
  discovery date, NOT the true first-appearance** (their own docs show >1-year lags), so even in production it can only
  *propose*, never authoritatively date; **(c)** its index drifts (~5 B → ~77.6 B (Sept 2025) → ~78.7 B (Oct 2025),
  ~1 B/month), so a live call gives different answers across runs unless frozen. *(help.tineye.com "first found on" /
  sorting docs; Wikipedia/TinEye blog — treat sizes as vendor-claimed.)*
- **The other engines are worse for a build:** **Bing Visual Search API retired 11 Aug 2025** (HTTP 410); **Google
  Lens / Yandex** have **no official API** (ToS-fraught scrapers only). *(Microsoft Learn; SerpApi.)*
- **TinEye's own product line validates the split:** **MatchEngine** (search *your own* collection) = the local-index
  pattern; the **Search API** (drifting web index) = the external-proposer pattern.

**Design call:** the **local corpus-internal perceptual + crypto hash index is the deterministic demo authority**
(runs inside `rebuild()`); **reverse-image search is roadmap, analyst-invoked enrichment** behind a **swappable
adapter** (`image → {oldest_match_url, crawl_date, backlinks}`), proposing a frozen candidate upstream. When the
local index can't date an image → `"insufficient evidence to assess — first-appearance not resolvable from indexed
corpus; reverse-image enrichment recommended, coverage due <date>."`

---

## §2 — Overhead / satellite imagery: what to extract, corroboration, and the priming trap

### 2.1 What analysts extract, and the HQ-9 site signature

An imagery analyst reads a SAM site as a **geometry of co-present signatures**, not one object: launcher **pads**
(count + shape), a central **engagement-radar** berm, a **search/acquisition** radar, a **command post**, **access
roads**, **revetments/berms**, **occupancy** (deployed vs garrison vs empty-pads). The **HQ-9 prepared site**:
launcher revetments **arranged radially around a central HT-233 engagement-radar berm, ringed by a circular access
road, with an outer acquisition-radar berm** (per `C/01`, described as a "rectangular TEL-pad ring"; the real Esri
frame `d07` reads as **radial lobed revetments** — a reminder to extract *what is there*, not a hardcoded token).
HQ-9 battery = 1 command vehicle + HT-233 + search/acquisition radar(s) + multiple **4-round TELs**. *(geimint HQ-9
site analysis; Army-Technology / ISW HQ-9 profiles; Bellingcat SAM-revetment geolocation.)*

Resolution is task-tiered (NIIRS / Johnson's): ~**2.5–4.5 m** to *detect*, ~**0.75–1.2 m** to distinguish a TEL,
sub-meter to attempt variant ID. Our corpus uses **Esri ~0.5 m for the confirm frames** and **Sentinel-2 10 m only
for the deliberate cloud/gap low-res beat** (`DECISIONS.md` imagery row already holds "Sentinel must not carry
positive equipment claims"). *(FAS IMINT/NIIRS; eoPortal Pléiades Neo; SkyFi GSD guide.)*

### 2.2 The VLM output: a subject-blind, all-optional *observation* — never a variant leap

**The VLM never asserts "HQ-9" from pixels.** *(Revised in discussion; the first-pass synthesis had the VLM emit a
variant `inference` — dropped.)* The imagery per-source extraction schema (see §3) is **subject-blind and
all-optional**, capturing only what is literally visible:

- `observed_signature` — **generic geometry tokens** (`radial-revetments`, `central-radar-berm`, `circular-access-
  road`, `outer-acquisition-berm`), NOT a system label, plus a **free-text description**.
- `occupancy_state ∈ {occupied, empty-pads, garrison}` — **`empty-pads` → "insufficient evidence to assess
  deployment,"** never a deployment assertion (negation wired into the non-negotiable).
- `count` — a **`Quantity` RANGE with abstention**, never a hard integer (VLM counting is unreliable, catastrophic on
  many-small-similar objects — arXiv 2510.04401; DDFAV).
- `caption_vs_image_consistency` (soft) + frozen `geo`/`gsd`.

Standalone **variant-identification-from-imagery goes to the design note** ("further investigation").

### 2.3 "How does it know to say *rectangular*?" — subject-blind, structured *not forced*

The answer is: **it must NOT be told the subject.**

- **Naming "HQ-9" collapses the VLM onto its memorized prior:** SOTA VLMs score ~**100 %** on canonical images but
  ~**17 %** on counterfactual ones. *("Vision Language Models Are Biased", vlmsarebiased.github.io.)* And VLMs cave to
  leading prompts far more for images than text — the **"sycophantic modality gap"** *(arXiv 2509.16149)* — with
  presuppositional prompts inducing object hallucination *(POPE 2305.10355; MAD-Bench 2402.13220)*. So the prompt names
  only the generic ontology TYPE schema ("describe what is literally visible; if resolution is insufficient, say so").
  This is the imagery-lane enforcement of **G9/G11**, now *empirically* load-bearing.
- **Structured *optional* fields, not a forced enum classification.** A constrained enum guarantees syntax not
  semantics and can degrade reasoning *("Let Me Speak Freely", arXiv 2408.02442 — caveat: it targets restrictive
  JSON-mode; the two-stage describe-then-classify pattern is attested, e.g. IRIS-style pipelines; one first-pass
  citation for the auditability claim was mis-attributed and dropped)*. A schema of **optional feature slots + a
  free-text description** structures the extraction (to make corroboration possible) **without** forcing a variant
  guess — reconciling "structured" with "don't over-claim."

**Disciplining "*anything could be rectangular*"** happens **not** at the VLM but at corroboration (§2.4): it takes
co-present features **plus a literature match** to assert a variant, at *probable*. Plus the deterministic
**resolution-floor gate** on the low-res beat (a variant corroboration on 10 m Sentinel-2 → "insufficient evidence to
identify variant").

### 2.4 Corroboration = a guided-LLM inference against ingested literature (and how image + news assert together)

Instead of a hand-authored `signature_library` config, the signature→variant judgement is a **guided-LLM
corroboration** that emits an **`inference` claim** with `premises: [the VLM observation, the ingested literature-
fingerprint claim]`, asserting `<site, consistent-with / based-at, HQ-9>` at **probable** (`decoy_risk` cap; decoys
like Rusbal mimic shape/colour/RF, so single-pass geometry can't confirm — ResearchGate/GDC). The reference
fingerprint is **discovered from ingested reference text** (Army-Technology / geimint / SIPRI-class describing the
HQ-9 site geometry) — the literature is just another sourced claim, so the inference is **fully traceable to both
premises** (a *better-grounded* inference than a VLM's pixel-leap or a hand-built config).

**How a satellite image corroborates a text "HQ-9 at base X" claim (can the current design do it? Yes):**
1. **News claim:** `<base_X, based-at, HQ-9>` (relationship, text discipline).
2. **VLM observation:** `<site_X, observed_signature, {radial revetments + central radar…}>` + WGS84/gsd — asserts a
   **signature, not identity**, so on its own it is a *different assertion* and would **not** corroborate the news.
3. **The bridge inference** (above): `premises = [observation, HQ-9 literature fingerprint]` → `<site_X, based-at,
   HQ-9>` at probable. *This is what puts the image on the same assertion as the news.*
4. **Resolution** pins `base_X` (news, geocoded) and `site_X` (image WGS84) to the **same `Basing site` node** (the
   geo hinge, `md/13`) — if they don't resolve together, no corroboration, correctly.
5. **Corroboration** (`spine/04`): the two claims now share a `resolved_ref` on edge `<Basing site, based-at, HQ-9>`
   and are grouped by **independence** — satellite-EO vs news-text = discipline-independent → `assertion_confidence`
   rises. Per `C/01:221`, single-pass image = *probable* (decoy penalty); the independent news is the 2nd discipline →
   **confirmed** if decoy is clean.

**Key insight (the whole thing hinges on the bridge inference):** corroboration is an **edge-level (knowledge-layer)
computation over claims that share a `resolved_ref`, grouped by independence** — never a claim-merge (claims never
merge). Without step 3, the raw image (`observed_signature`) and the news (`based-at HQ-9`) are about **different
predicates** and can't corroborate. Caveats: the inference must assert HQ-9 *specifically* (a vague "some SAM site"
won't corroborate the specific claim); image-only, no news → correctly *probable* + a Known Gap.

### 2.5 Does this generalize to Use Case A? Yes (verified against the brief)

Use Case A = "multi-theatre air-posture picture & correlated-surge early warning": apron/shelter activity, aircraft
counts, fuel/munitions logistics, runway works, new platforms, from imagery *(brief, `md/01`)*. The **extraction
mechanism is identical** — a subject-blind, all-optional structured observation of visible features. What differs is
only (a) the *feature vocabulary* (aircraft/aprons/fuel for A vs revetments/radar for C — argues for keeping the
schema generic, not "TEL pads"), and (b) the *corroboration reference* (A compares to a **temporal baseline of the
location** → deviation; C compares to a **literature fingerprint** → identity). Both are "compare `observed_signature`
to a reference," both fit the guided-LLM-corroboration-as-inference-claim pattern. **So the design is general.**

---

## §3 — Per-source extraction schema + transformer (vs generic triples vs one direct schema)

### 3.1 The decision: per-source (all-optional) extraction schema → deterministic transformer → `ClaimRecord`

*(Revised in discussion. The first-pass synthesis argued for one `ClaimRecord` schema the LLM emits into directly;
the user chose the per-source-schema + transformer architecture, and the "wrapper-trap" objection below does not
apply to it.)*

Each `source_type` gets its **own extraction pydantic schema** — **all fields optional**, shaped to the source's
native record (a `CustomsBoL` schema, a `SatelliteObservation` schema, …), which the LLM fills; a **deterministic
transformer** then maps the filled object into the **one F0 `ClaimRecord`**. The extraction schema **carries generic
ontology node/edge TYPES** (never instances/subjects/anchors — **G11**), shaped so the transformer is a **simple
field→type mapping, not inference**.

- **Not bare OpenIE triples** — flattens source-native structure and is noisy *(ACL 2024 OpenIE survey)*; a customs
  BoL row's ~20 native fields are lost in one triple *(arXiv 2305.14336, 2406.11160)*.
- **Not the "wrapper-maintenance trap"** — that trap is about brittle *rule-based parsers* (regex/XPath) that break on
  format changes *(UCI schema-guided wrapper maintenance)*. An **LLM filling an all-optional schema** is not brittle to
  format changes; the real cost is just writing N schemas + N transformers (bounded, and the transformer is explicit
  auditable code). So the first-pass "wrapper trap" objection **does not apply** to this design.
- **G9-safe & more G11-safe:** per-source schemas are *source-typed* (G9 forbids *use-case/subject*-typed branching,
  not source-typed handling); and the LLM fills a source form — it never picks an instance or constructs the s/p/o
  (the transformer does), so it's *more* G11-safe than a subject-aware direct emit.
- **The single-schema direct-emit is the later optimization**, not the demo.

### 3.2 Two invariants on every schema + transformer

1. **All-optional fields = the anti-fabrication mechanism (load-bearing for the non-negotiable).** Rigid *required*
   fields provably force invention ("John Doe"); the documented mitigation is permissive/optional fields *(LangChain4j
   structured-outputs; "Reducing hallucinations extracting from PDF", dev.to)*. The LLM fills only what the source
   *states*; **when a source states nothing, the transformer emits NO claim** (→ "insufficient evidence to assess").
2. **3-tier attribute promotion — where source-native fields land (the transformer decides).** Each extracted field
   routes to one of:
   - **(1) its own node/edge** — a graph citizen the ASK agent traverses (a consignee → `Organization`; an import →
     `Contract/Import event`).
   - **(2) a knowledge-layer attribute** — a property used in computation, e.g. `C/01`'s `functional_role`,
     `equipment_fingerprint` range, `operational_status`, `substitutability`. *(These are the attributes the user
     correctly noted ARE graph citizens — they live on the resolved node/edge and feed materiality/chokepoint/status.)*
   - **(3) a nullable typed `attributes` bag** — source-native context with no ontology home (HS-code, container#,
     BoL#): traceable + queryable, **not** traversed, **promotable** to tier 1/2 later if it turns out material.
   A customs BoL row thus yields **many** typed claims, each keeping the verbatim raw cell on `doc_ref` (**G4**).

**Consequences of the `attributes` bag** (raised by the user): tier-3 attributes are *not* graph citizens (no node/edge,
no resolution/traversal) → a **promotion rule** is required (material → tier 1/2; else tier 3), or a material field gets
buried. "Typed" needs a small per-key **type registry**. Provenance is preserved (each attribute inherits the claim's
`doc_ref`). It is additive + nullable, so it never forces fabrication. It is a small **F0-amendment** (raise-not-widen,
master Rule 3).

### 3.3 Does the `ClaimRecord` carry an entity type? (user question)

**Yes — in the payload, not as a top-level field.** `master §4.2`: `asserts ∈ {entity, relationship, event}`;
`payload = (subject, predicate, object) | entity-descriptor | event-descriptor`; `resolved_ref` is **NULL at
extraction** (RESOLVE fills it). For `asserts: entity`, the payload is an **entity-descriptor carrying the ontology
`node_type` + stated attributes + raw name**; for `relationship`, it's `(subject, predicate, object)` with type tags.
So a claim knows *what type* it asserts, not *which instance* — exactly what makes the transformer's node-typing clean.

---

## §4 — Decisions logged, doc-tail enrichments, resolved forks

### Decisions logged (see `DECISIONS.md` → "Extraction & ingestion" ledger, 2026-07-18)
- **Image integrity = `sha256` (exact/same-origin) + PDQ 256-bit perceptual (recycled/near-dup; lazy-recycle
  bottleneck noted).** Local corpus-internal first-seen index = deterministic authority in `rebuild()`; **reverse-image
  = roadmap proposer**, deferred for budget + crawl-date≠first-appearance (NOT determinism/keyless).
- **Imagery VLM = subject-blind, all-optional structured observation (no variant field).** Signature→variant = a
  **guided-LLM corroboration** `inference` (`premises:[observation, literature-fingerprint]`, capped probable),
  fingerprint **discovered from ingested literature**; this inference is what enables cross-modal (image+news)
  corroboration. Resolution-floor gate scoped to the low-res beat. Generalizes to Use Case A.
- **Extraction = per-source (all-optional) extraction schema + deterministic transformer → `ClaimRecord`.** Transformer
  does node-typing + 3-tier attribute promotion. All-optional = anti-fabrication. Single-schema direct-emit = later
  optimization.

### Design-doc tails to enrich
- **`spine/04` §D** — replace "perceptual/image hash" with **`sha256` + PDQ** (distinct roles); split "first-seen/
  reverse-image" into **local first-seen index (deterministic, in `rebuild()`)** vs **reverse-image (network,
  upstream proposer, roadmap)**; add the resolution-floor gate + specify `decoy_risk_flag` provenance (single-pass
  geometry-only match, no occupancy/activity corroboration → flag set).
- **`spine/08` §3.11 / §3.1** — fix the hash wording to the two roles; state hash+EXIF frozen at ingest vs
  first_seen/etc computed in `rebuild()`; add the all-optional-per-source-schema + transformer + 3-tier-attributes
  model + the `attributes` bag F0-amendment; standardize the extraction sub-schema naming on `model`.
- **`C/01`** — Indicator `first_seen` updated to the local-PDQ-index/reverse-image-roadmap wording (done); note that
  `site_signature_geometry` / `observable_fingerprint` are the **literature-populated** corroboration reference, not
  hand-authored config; add `gsd` + count-as-range to the Basing/Indicator attrs.
- **`spine/02`** — add the per-source-schema+transformer + all-optional + 3-tier rules to the unit-of-analysis section.

### Resolved forks (were open; now decided — `DECISIONS.md` §3)
1. **Perceptual-hash primary → PDQ** (lazy-recycle bottleneck accepted; SSCD roadmap).
2. **Extraction architecture → per-source schema + transformer** (direct-emit = later optimization).
3. **Typed `attributes` bag → adopt** (3-tier promotion; F0-amendment).
4. **Reverse-image search / live TinEye → no** (roadmap proposer only).
5. **Extraction sub-schema naming → `model`** (pending an F0-amendment PR).

### Corpus/status note
The imagery substrate **exists** (16 raster assets incl. `d07/d08/d10/d11/d12/d13/d17/d17b/d18`,
`shared_parade_2019.png`, chaff reshares) and the resolution-tiered strategy is locked (`DECISIONS.md` imagery rows).
The `md/05` §5.2.1 **D3 "zero raster"** flag is **stale** — the VLM/integrity path has real inputs.
