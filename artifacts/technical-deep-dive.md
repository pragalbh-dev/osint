# Chanakya OSINT — How the System Is Wired

A code-grounded walkthrough of the running system: how a line in a raw file becomes a cited, status-bearing
node an analyst can trust, and how each subsystem — ingestion, resolution, credibility, retrieval, HITL,
monitoring — is actually implemented. It is written from the source, so it is precise about what is
load-bearing on the real corpus versus what ships as an extensible seam that is built but not yet
exercised. Those boundaries are called out explicitly rather than glossed: for a system whose whole claim
is calibrated trust, an honest account of where confidence comes from — and where it deliberately stops —
is more useful than a tour of the happy path.

## How to read this in an hour

If you read nothing else, read these five, in this order:

- **01 — Orientation** gives you the one mental model everything else hangs on: two layers (an append-only
  evidence log and a derived view) and a single `rebuild()` that turns one into the other. Ten minutes here
  makes every later chapter faster.
- **06 — Credibility** is the load-bearing chapter. It is the actual arithmetic of confidence and the exact
  conditions for "confirmed" versus "probable." Spend the most time here.
- **07 — The rebuild** is where all the logic is actually sequenced. If credibility is the physics, this is
  the order of operations that makes it happen.
- **14 — Reality check** is the candid inventory: what is load-bearing, what is an extensible seam, and
  what is built but not yet wired. Read it to calibrate everything the earlier chapters told you.
- **13 — The knobs** is your control panel — what you can turn, what actually moves, and
  what looks tunable but has no live reader.

Skim the rest as needed. Chapters **08 (HITL)**, **10 (Refusal)**, and **11 (Retrieval)** are the other
three pillars and reward a full read if you have time. Chapters **02 (Substrate)**, **03 (Ingestion)**,
**04 (Derivation)**, **05 (Resolution)**, **09 (Monitoring)**, **12 (Surface)**, and **15 (Seams)** fill in
the machinery and can be read in any order or skimmed.

## What's in each chapter

| # | Chapter | What you learn here |
|---|---|---|
| 01 | Orientation | The two-layer model, the atomic record, and why every question reduces to "what does rebuild do." |
| 02 | The substrate | What is written down versus regenerated, how identity/IDs are assigned, and what the ontology really constrains. |
| 03 | Ingestion | How a messy file becomes sourced claims — and the sharp line between deterministic parsing and LLM judgement. |
| 04 | Derivation | The facts the system infers for itself (attribution, basing, coref) and whether each keeps clean provenance. |
| 05 | Resolution | How many mentions become one entity, the scoring bands, and how fragmented the real graph actually is. |
| 06 | Credibility | The confidence arithmetic and the exact promotion rules for confirmed / probable / stale / insufficient. |
| 07 | The rebuild | The ordered pipeline that assembles the graph, why the order matters, and where human overrides slot in. |
| 08 | HITL | What actually changes when a human decides, whether it survives rebuild, and where the queue is not wired. |
| 09 | Monitoring | The observable language, the alert lifecycle, and which shipped tripwires actually fire versus sit inert. |
| 10 | Refusal | Every path that yields "insufficient evidence," and the adversarial question of whether a thin assertion can escape. |
| 11 | Retrieval | The bounded agent loop, the graph tools, and exactly what the citation validator checks and does on failure. |
| 12 | The surface | The HTTP endpoints grouped by what they do to the system, and how the UI encodes trust and where it falls back to fixtures. |
| 13 | The knobs | The full configurability inventory — plus the config keys with no live reader and the thresholds fixed in code. |
| 14 | Reality check | Load-bearing versus built-but-not-wired, cold-boot and determinism behaviour, and the current limitations. |
| 15 | Seams | Where a new source, node type, credibility factor, observable, or use case would actually plug in. |

---

## Orientation: the shape of the machine

### Two layers, and only two things are ever written

Everything the system knows lives in two append-only logs, and everything an analyst reads is derived from them. The first is the **evidence log**: one row per sourced assertion, a `ClaimRecord`. The second is the **decision log**: one row per human adjudication or system event, a `DecisionRecord`. Both are the same physical thing — a single SQLite table `events(seq AUTOINCREMENT, record_id, payload JSON)` — and both are genuinely immutable at the storage layer: two `BEFORE UPDATE/DELETE` triggers `RAISE(ABORT)`, so even a hand-written SQL `UPDATE` cannot mutate a committed row. The only writes the schema permits are inserts. Reading a log is one operation, `replay()`, which is `SELECT payload ORDER BY seq ASC` — insertion order, forever. That single ordering rule is load-bearing far downstream: dedup, corroboration counting, and the "first claim wins" tie-breaks in the view all inherit their determinism from the order rows were appended.

The knowledge graph an analyst sees — nodes, edges, events, known-gaps, alerts, each with a status and a confidence breakdown — is **not stored anywhere**. It is a pure function of (evidence log + decision log + a config snapshot), recomputed from scratch on demand. There is no incremental update, no cache, no carry-over from the previous graph. This is the central fact of the architecture: the logs are the truth, the graph is a *view*, and the view is disposable.

One caveat up front, because it colours everything: both logs are in-memory (`:memory:` SQLite). The `CHANAKYA_DATA_DIR` env var and `settings.data_dir()` that would point them at a durable file have no live caller — grep finds zero call sites that construct a log with a path, so every log is process-lifetime only. The Dockerfile provisions `/app/var/data` with correct ownership, though no code path currently writes to it. What survives a restart is only the frozen JSON claim bundles committed under `corpus/`, which are replayed at boot. Every claim ingested live and every HITL decision an analyst makes is not persisted and is lost when the process exits. For a single-analyst demo this is fine; it is not a production persistence story.

### The atomic record

The unit of analysis is not the document and not a text chunk — it is the **sourced claim**: *Source S, dated D, asserts \<subject, predicate, object\>*. A `ClaimRecord`'s payload is a discriminated union on a `form` field (`triple` / `entity` / `event`), and a validator enforces that the asserted relation and the payload form agree. Three timestamps ride on every claim and are kept deliberately distinct — `event_time` (true in the world), `report_time` (when the source published), `ingest_time` (when we received it) — plus a fourth field, `resolved_ref`, which is the extractor's first guess at identity but is overwritten authoritatively by resolution at rebuild time.

Claim IDs are human-readable and content-derived (`d05-row12`, `d18-l3-2`), minted by sorting a document's claims by their earliest provenance span and walking a per-locator counter. Because the ID is a pure function of content, re-extracting the same document mints byte-identical IDs — which is what makes the frozen corpus bundles diffable. The important non-guarantee: there is **no uniqueness constraint** on `record_id`, and `append()` never checks for a pre-existing row. Re-POSTing the same bundle silently appends a duplicate set; downstream code that folds `replay()` into a dict keyed by ID quietly keeps the last and drops the earlier, with no error.

### "Rebuild" is the whole system

`rebuild()` (in `view/pipeline.py`) is the one reduction from logs to graph. It is meant to be pure and deterministic: no clock, no network, no LLM, no randomness. The LLM already ran, upstream, at ingest, and its output is frozen in the log; `rebuild()` only *disposes* — it applies deterministic rules to already-frozen facts. Given identical logs and config, it emits a byte-identical view. This is why nearly every interesting question about the system reduces to "what does rebuild do at stage N?" — status, corroboration, merges, chokepoints, gaps, and supersession are all decided inside this one function, in a fixed order, and the order is itself load-bearing.

Measured, a full boot rebuild over the shipped seed (~29 bundles) takes ~560–600 ms and produces **160 nodes / 73 edges / 66 events / 18 known-gaps from 450 claims** with the two Rahwali documents withheld — the default keyless boot the app shows — or **169 / 80 / 71 / 20 from 492 claims** with nothing withheld. `rebuild()` is triggered on boot and by every write path (`/ingest`, `/hitl`, `/config`) through `AppState.rebuild_and_swap`, which recomputes under one lock and atomically swaps the held view; reads are lock-free. That swap *is* the entire "nothing needs a restart" mechanism — there is no file watcher and no polling.

The stages, in execution order, are the hooks for the rest of this document:

| Stage | Owning module | What it decides |
|---|---|---|
| Pre-filter: retractions, HITL claim-exclusions, `as_of` rewind, edge-canonicalisation | `view/pipeline` + `config/edge_direction` | which claims even enter this rebuild, and their orientation |
| 1. Resolve | `resolve/` | which claims name the same entity; auto-merge vs analyst-queue vs hard veto |
| 2. Assemble | `view/pipeline` | claims → nodes/edges/events; first-claim-wins for attrs and location |
| 3. Score | `credibility/scoring` | per-claim credibility = reliability × integrity × freshness |
| 4. Assertion inputs | `credibility/independence`, `sufficiency/` | independence groups, freshness/stale flags, deception gates, sufficiency |
| 5. Assign status | `credibility/status` | confirmed / probable / possible / insufficient / contradicted / stale |
| 6. Attach + gaps | `view/pipeline` | confidence breakdown, freshness, a `KnownGap` per unmet sufficiency |
| 6b. Supersession floor | `credibility/supersession` | retire an older edge only if the newer one clears the floor |
| 7. Materiality | `materiality/precompute` | sole-source chokepoint status + candidate-chokepoint gaps |
| 8. HITL effects (late) | `hitl/` via `view/pipeline` | `set_status` override wins last; integrity-flag appended |
| 8b. Resolution edges, 9. Sort + meta | `resolve/`, `view/export` | candidate `same-as`/veto edges; deterministic ordering |

Two things that are *not* in this pipeline: the **subject lens** (`view/lens`) is a query-time transform applied per request on `/view` and inside `/ask`, never in `rebuild()`; and **alerts** are filled by the observe subsystem on the (old-view → new-view) delta, not by `rebuild()` itself. Ingestion (`ingest/`) and the retrieval agent (`agent/`) sit outside `rebuild()` entirely — one writes the log before it, one reads the finished view after it.

### The lifecycle of one fact, end to end

A raw file arrives — at boot from a frozen bundle, or live through `POST /ingest`. The loader splits it into regions (one per line, row, page, or image frame) each carrying an exact character span, with no ontology involved yet. A format sniffer picks one of six format lanes purely from the text and the declared `source_type`, never from *who* the document is about. If a key is present, an LLM reads the region and fills a per-format schema of only stated facts, quoting each verbatim — this is the single interpretation point in the whole system, and whatever it declines to fill (a partial "HT233-" designator buried in an annex) is simply gone. A deterministic transform table then maps each filled field to typed claims — trading-org nodes, an import-event node, role edges — and pointedly refuses to invent links no source stated. Provenance stamping locates each quote's character span back to its line so the claim is one-click traceable, and geocoding runs here too. Dedup folds within-document restatements, a content-derived ID is minted, and a single writer appends the claim to the immutable evidence log — the last mutation this fact will ever undergo. On the rebuild that this very ingest triggers, resolution decides whether the claim's entities merge with existing ones, credibility scores it as reliability × integrity × freshness, and the status machine reads how many independent sources corroborate it to label it confirmed or probable. The claim thereby becomes part of a node or edge in the derived graph, carrying its status, a confidence breakdown, its freshness, and the exact claim IDs backing it. An analyst then reads that node on `/view` or via `/ask` and clicks straight back to the original line — or, where the evidence is too thin to assess, sees an explicit "insufficient evidence" gap naming what is missing, never a guess.

### The four decisions that constrain everything downstream

**Append-only logs plus a fully-recomputed pure view.** Nothing is ever edited in place; the graph is rebuilt from zero every time. This is what makes traceability, point-in-time rewind (`as_of`), and "confirmed vs probable" fall out of the architecture rather than being bolted on — but it also means the graph is only as good as one deterministic pass over the log, and any bug in `rebuild()` is a bug in *everything*.

**The LLM runs exactly once, upstream, and its output is frozen.** Interpretation happens at ingest and is recorded as immutable claims; `rebuild()` and every scoring decision are deterministic arithmetic over those claims. This is the source of demo reproducibility (the live query runs identically every time) and the reason the keyless bundle lane can be asserted byte-identical to the keyed live lane.

**The sourced claim is the atom, and confidence is a function of claims.** Because corroboration is defined *across documents* and a node's status is computed from its independent claim-groups, a single-source document (a lone customs manifest) can structurally never rise above "probable" on its own — confirmation must come from a second, independent discipline. Credibility is not a property you attach to a node; it is derived from what backs it.

**Config is live data, read fresh per rebuild; the subject is a query-time lens.** Nine YAML files seed one in-memory config bundle; every rebuild takes a deep-copy snapshot, every hot write bumps a version and takes effect on the next rebuild with no restart — thresholds (confirmed 0.80, probable 0.50), the ontology, and observables are all tunable this way. Ingestion is typed by *source format*, not by use case, and a "subject" (HQ-9/P) is not its own database but a traversal-and-filter lens applied at query time. The cost of this cleanliness: hot config writes are memory-only — nothing serialises back to disk — so a restart reverts every knob an analyst touched.


---

## The substrate: what is written down and what is derived

Everything above this layer — credibility scores, confirmed/probable status, the map, the answer to a
question — is arithmetic performed on two flat logs. What those logs guarantee, and what gets thrown away
and recomputed on every request, is the difference between an audit trail that's architecturally forced
and one that just hasn't been broken yet.

### Two logs, one discipline, and where the discipline stops

There is an evidence log (one row per sourced claim) and a decision log (one row per HITL adjudication or
system event). Both are the same generic append-only table over SQLite, and append-only is not a
convention — it's enforced by two triggers that abort any `UPDATE` or `DELETE` against the table, so the
only verb the schema permits is insert. Reading the log back (`replay`) is "give me every row in the order
it was inserted," and that insertion order is the single most load-bearing fact in the system: it decides
"first claim wins" when two claims disagree on an attribute, it decides corroboration order, it decides
dedup order. Nothing downstream resorts by content until a later stage deliberately does so for a specific
reason (id minting does; node assembly does not).

The append-only guarantee has two real gaps. There is no uniqueness constraint on a record's id — only a
lookup index — so nothing stops the same claim or decision being appended twice under an identical id if a
caller re-submits it (re-POSTing an ingest bundle, double-clicking a HITL disposition); the log doesn't
reject the duplicate, and whatever reads it back into a dictionary keyed by id silently keeps the later row
and drops the earlier one, with no error surfaced. And "append-only" describes the table, not the process
holding it: every production and CLI path constructs both logs with their default in-memory backing store.
A `CHANAKYA_DATA_DIR` variable exists to point them at a persistent path, but nothing ever actually passes
that path — so nothing survives a restart except what was checked in as a JSON bundle and replayed at boot.
The guarantee is real for one running process; durability across a restart is simulated by the corpus
files, not wired.

### What gets minted once versus what gets rebuilt every time

The knowledge graph a user sees — nodes, edges, events, gaps, alerts — is not stored anywhere; it is
recomputed from the two logs plus live config on every rebuild, with nothing carried over from the previous
view. A "previous view" parameter is threaded into resolution specifically so entity merges could stay
stable run to run, but resolution never reads it — every rebuild re-resolves identity from a blank slate,
and gets the same answer only because the inputs are themselves identical. The one place state genuinely
carries forward is the logs: an accepted HITL merge becomes a durable entry that grows the alias table on
every future rebuild, and a rejected merge becomes a durable veto the same way. The logs are the only memory
the system has; the graph is a projection, thrown away and recomputed in full — a little over half a second
for the shipped corpus — every time anything changes.

Claim identity is the one place "recomputed" and "stable" have to coexist, and the trick is that the id is
derived from content, not arrival order. A claim's id is a human-readable `<document>-<locator>` string, but
what decides which claim gets which id is a fixed sort over each claim's earliest provenance span (row,
line, page, image frame, bounding box, then a text offset as last resort), with content as tiebreaker.
Walking that sorted list and counting occurrences per locator produces the id — so re-running extraction
over the same document, even if the model emits claims in a different order, mints an identical set of ids,
which is what makes a frozen bundle diffable against a live re-extraction. Before ids are assigned, a
within-document dedup step folds two claims that agree on subject/predicate/object, event time, premises,
and targets into one — deliberately ignoring when the claim was reported or ingested, so a restatement
collapses — but this never reaches across documents; merging what two different sources say about one fact
is resolution's job, done later. Whenever an id is reassigned, every other claim pointing at it — an
inference's premises, a retraction's target — gets rewritten in the same pass so nothing dangles.
Decision-log ids are minted more casually: deterministically from the review item and chosen action, with
no randomness but also no protection against a duplicate if the same disposition is submitted twice.

Node and edge identity live one layer up and aren't preserved values at all — they're recomputed fresh each
rebuild as an output of resolution (which canonical id a cluster of claims collapses onto) and of
edge-instance grouping (which claims land on the "same" edge). Whether an edge counts as one instance or
many is itself an ontology-declared choice: a functional relationship like a unit being based at a site
keys on just the "from" side, so an old site and a new site for the same unit collapse into one comparable
instance — what makes relocation detectable at all — while a multi-valued relationship like a missile
system equipping several units keys on both ends, so each pairing is its own instance. Nothing here is
hardcoded per relationship type; it's one line of declaration per edge in the ontology, read fresh each
rebuild.

### Time has three faces on the way in, one arbitrated answer on the way out

Every claim carries three timestamps kept deliberately distinct: when the fact was true in the world, when
the source published it, and when the system ingested it. Keeping these separate lets freshness scoring
measure staleness against the right clock (how long ago was this *reported*, not read) and lets a
retroactive rewind distinguish "we didn't know this yet" from "this was already old news."

"Now," for freshness decay and for a point-in-time rewind, resolves through a strict priority: a pinned
`credibility.as_of` config value wins if set; failing that, the latest report or ingest timestamp seen
across the log; if literally nothing is dated, freshness decay is disabled rather than guessed at.
Rewinding to a past `as_of` hides a claim only if its own arrival stamp is provably later than the cutoff —
an undated claim is always kept, so the rewind can under-hide but never over-hide. In practice nothing in
the running system ever writes `as_of` from the wall clock, despite comments describing that as the intended
live-monitoring behavior; the config ships with it unset, so "now" is permanently anchored to the newest
date already in the corpus. The upshot is a freshness story that's calendar-independent — it reads the same
whether opened the day it was built or months later — but that follows from the config being left unset
rather than from a wired feature.

### The ontology constrains connections hard and vocabulary softly

The ontology is read at every rebuild, not compiled in, and does two visibly different jobs depending on
whether the thing in question is a node/event type or a relationship. An entity or event whose declared
type the extractor invented — something outside the live vocabulary — is never blocked: the claim is
written as-is and stamped with a flag noting the type is off-ontology, and nothing downstream reads or
filters on that flag. It exists purely so a human opening the raw claim can see something didn't fit; it
has no teeth.

Relationships get the opposite treatment. Every declared edge type specifies which node types can sit at
its two ends, and — both at ingest time and again as a read-time safety net during rebuild — a claimed
relationship is checked against those declared endpoints regardless of the verb the extractor used: "the
missile equips the unit" and "the unit operates the missile" both get relabeled onto whichever single
declared edge the endpoint types imply, in whichever direction it runs. If the resolved endpoint types fit
no declared edge in either direction, the relationship is rejected outright — never written as a graph edge,
only left as a note that it didn't parse. That asymmetry — soft tagging for what a node *is*, hard rejection
for how two nodes *connect* — is easy to miss from the docs, which describe both as "off-ontology handling"
without distinguishing advisory from gate.

One genuine defect sits at this boundary: the ontology declares a nested block meant to let an operator
override which relationship types count toward a node's chokepoint/sole-supplier computation, and the code
reading that override looks in the wrong place — a top-level attribute of the whole config bundle instead of
the nested one the YAML actually populates. The override is therefore silently ignored and the
computation falls back to a fixed set of relationship types; because that set matches the shipped
ontology, this has no effect today.

### The config store: nine files, one frozen snapshot per rebuild, no memory of its own

All configuration — ontology, sources, credibility, resolution, evidence-requirement templates, subject
lenses, observables, the place gazetteer, the entity registry — is parsed once at boot into a single typed
bundle held in memory. Every other subsystem reads config exclusively through a snapshot of that bundle,
never by touching a file, and a snapshot is a deep copy taken once at the start of a rebuild — the whole
basis of the guarantee that a config change can never half-apply inside a rebuild in progress.

Boot validation is asymmetric on purpose: a missing config file is fine, that section silently falls back
to built-in defaults, so the app can boot against an empty config directory at all; a file that's present
but fails its schema is not tolerated and raises straight out of boot. Exactly one path mutates the live
bundle after boot: a config-write endpoint that replaces one entire named section (never a partial patch — a
shallow-merge convenience exists on the store, but nothing in the API calls it), re-validates it, and bumps
a version counter. That write immediately triggers a full rebuild against the new snapshot and swaps the
served view atomically — no file watcher, no polling; the hot-reload *is* the rebuild. Critically, the
write only ever happens in memory: nothing serializes a mutated section back to its YAML file, so every
knob an analyst tunes through the running app reverts to disk the moment the process restarts. Two
consistency self-checks exist specifically to catch a bad ontology edit — one detects two relationship
types colliding on the same endpoint-type pair, the other a decaying edge with no reachable half-life in the
fallback chain — but neither is invoked automatically, on boot or on a hot write; they only run inside their
own unit test, so a config edit introducing either problem today is accepted silently. In short: missing
config degrades gracefully, malformed config crashes loudly, hot writes take effect instantly but only in
memory, and nothing checks a hot ontology edit for internal consistency before it starts driving the graph.


---

## Ingestion: from a messy file to sourced claims

### The front door: a file becomes regions, purely by extension

The loader makes exactly one decision: what does the file extension say this is. Image extensions go
to an image loader that never reads text — just the raw bytes and one whole-frame region. `.pdf` goes
to the PDF loader. `.html`/`.htm` gets boilerplate stripped to text. Everything else, including no
extension at all, is plain text split into one "region" per non-blank line — a customs-manifest row and
a prose sentence are, at this stage, indistinguishable: both are just lines with a character span and a
line number. There is deliberately no born-digital-vs-scanned heuristic for PDFs (that branch was
removed); instead the PDF loader asks one binary question — is an Azure OCR endpoint configured
(`AZURE_DOCINTEL_ENDPOINT`/`KEY`, or the generic `AZURE_ENDPOINT`/`AZURE_API_KEY`)? If yes, Azure's
"prebuilt-layout" model supplies the text layer, converted into the same region structure everything
else uses (one region per paragraph, one per table cell sorted row-then-column for determinism,
bounding boxes normalized to the unit square, rounded to six decimals, unknown dimensions producing no
bbox rather than a fabricated one). If Azure isn't configured, pymupdf, then `pdftotext`. Either way
every page is *also* rasterized locally to a PNG at a hardcoded 150 DPI (no config override exists),
because the extractor always gets text and page images together — prose and figures are read in one
call, never routed to separate pipelines. Nothing about content — what the document is about, who it
names — enters at this stage; the loader only asks what shape of file this is.

### Choosing an extraction schema: a lookup table, with content as tiebreaker

A loaded document is matched to one of six extraction schemas — prose, NOTAM/navigational-warning,
customs GD/BoL, tender/procurement, social-media post, or imagery/GEOINT caption — by `format_sniffer`,
and the dispatch is almost entirely deterministic. The starting point is not the text but `source_type`,
a label stamped per `source_id` in the curated `config/sources.yaml` registry — the same vocabulary the
credibility config's source-class weighting table keys off directly, with no mapping layer between the
two. A NOTAM-typed source routes straight to NOTAM; "official/press" sources route to NOTAM only if
NOTAM cues appear, else prose; "customs/tender" sources split by content cues, defaulting to customs when
neither set is decisive; social routes to social; satellite to imagery. Only when `source_type` is empty
or unrecognized does the sniffer fall back to a raw-text scan in fixed priority (NOTAM, customs, tender,
social, GEOINT, prose as catch-all). The content scan itself is a cue-count, not a model judgement: a
family is claimed once at least two distinct cue strings from a fixed table hit, with four single-token
exceptions ("NOTAM", "GD NO", "STATUS URL", "GEOSPATIAL INTELLIGENCE") that claim their family outright
on one hit. This is deliberately subject-blind — the same six buckets apply regardless of what the
document is about.

This is also the sharpest seam in the path. `source_type` is curated and trustworthy for the recorded
corpus, because a human assigned it in `sources.yaml`. On the live API it is whatever string the caller
puts in the request body — unvalidated against the registry. Since the same string also drives the
credibility source-class lookup downstream, a live caller can hand a document whatever reliability class
it likes, or land in an unknown class the scorer treats as zero reliability rather than a neutral
default.

### The extraction call: forced tool-calling, a permissive schema, one real constraint

The chosen format's pydantic schema becomes a single tool's JSON schema, and the model is *required* to
call it — Anthropic via a hard `tool_choice`, Gemini via function-calling mode `ANY` with only that tool
whitelisted. No matching call → immediate `RuntimeError`, no retry, no re-prompt. No sampling parameter
— temperature, top_p, top_k — is ever set on either provider; the comments frame this as "Opus 4.8
rejects those params," not as a determinism strategy, and that distinction matters later.

The schemas are deliberately loose: every field optional, no `required` list, no
`additionalProperties:false`. One shared system prompt ("fill only stated facts, never invent or infer,
quote verbatim into `source_quote`") plus a one-line per-format addendum governs the call. The one real
structural constraint is on the `relation` field: narrowed at build time to the ~10 real relationship
edges pulled live from the ontology (identity — "same-as" — is excluded; it flows through dedicated alias
fields). Everything else is taken at face value here and re-checked structurally in the transform step,
never checked for truth — nothing stops a model from returning a relation label outside the narrowed set;
enforcement is best-effort per provider, and the real backstop is downstream re-laning.

Provider choice is decided by key presence, and the shipped production image now backs this for real: the
Docker build installs the `[gemini]` extra (`google-genai`) alongside the core deps, so a Gemini key
actually works in the deployed container, not just in a dev checkout with the extra installed by hand.
Gemini first if `GEMINI_API_KEY` is set (a floating alias, `gemini-flash-latest`), else Anthropic if
`ANTHROPIC_API_KEY` is set (pinned `claude-opus-4-8`, capped at 8192 output tokens — Anthropic-only, never
passed to Gemini), else the builder returns `None` — for the CLI recorder that means no bundle gets
(re)written; for the live `POST /ingest` endpoint it means the caller gets an explicit 400, not a silent
substitution (see the gating below). A last wrinkle: a document is windowed by page only if it both has page
structure and exceeds a fixed 8 pages or 60,000 characters; below that — apparently the whole shipped
corpus — exactly one call runs, and above it, page windows are each their own forced call, merged
afterward (lists concatenated, scalars keep first non-empty) before one transform pass.

### The transform: a fixed lookup table decides what becomes a claim, never inference

What the model filled in is handed to per-format deterministic functions that map fields to typed claims
by a hardcoded lookup table — never by further inference. Three disciplines are enforced mechanically,
not by prompting:

- **Anti-fabrication by construction.** Every field is optional, so a blank field emits nothing; a
  document read as saying nothing yields zero claims. Field accessors are tolerant of noise — a
  wrongly-typed value is silently dropped, never coerced into a guess, never allowed to crash.
- **No unstated linking.** A stated alias becomes a `same-as` claim, but the transform never connects
  entities the document itself doesn't connect — a customs consignee is never wired to a downstream
  depot just because both appear in one document. That inference is resolution's job, at rebuild.
- **Structural provenance on every claim.** `doc_ref` is resolved by finding the exact `source_quote` in
  the assembled text → char span → line/page, falling back through field value → whole first region →
  file if the quote can't be found verbatim — never a fabricated location.

Every claim carries an `Extraction` block: method (`llm`/`vlm`), model/version string, and a `model_conf`
hardcoded to `1.0` on *every* claim regardless of provider or how hedged the model's own language was.
Real confidence isn't assigned here — that's entirely the downstream credibility scorer's job, which
treats extraction-time confidence as a non-signal.

The one place genuine post-extraction judgement is applied is edge re-laning. Once endpoint types are
known, the ontology's edge index decides which real relationship the fact belongs on, relabeling or
reversing it to canonical direction. If the endpoints fit no real edge, the fact is neither forced onto
the nearest one nor dropped — it's rejected as a graph edge and kept only as a tier-3 "rejected relation"
note on the subject node, preserving the as-stated predicate, verbatim quote, and rejection reason.
Partial typing fixes orientation only; no typing flags the predicate unresolved rather than guessing.
Valid-time resolution walks a ladder afterward (stated date → enclosing observation date → document
report time) and is required only for edges the ontology marks perishable/semi-durable; an undated edge
in those classes is flagged, never given a made-up date. Denials, negations, and observed absence are
deliberately never turned into edges, so a "not present" claim doesn't mint a junk node to hang the
negation on.

### Imagery: a subject-blind observation always fires; the variant inference ships frozen, not live

A single overhead frame produces at most two claims on very different footing. The first always fires,
even on an empty read: generic geometry tokens, an occupancy word, a caption note, and a count that is a
range or an explicit abstention — never a fabricated scalar. The governing system prompt actively
forbids naming any weapon system, variant, or country, and forbids stating coordinates. A two-part image
fingerprint (plain hash, perceptual PDQ/pHash, EXIF) is frozen onto tier-3 attributes at the same time,
and an undated frame inherits its date later, in per-document finalize, from its sibling text claim's
most recent observed date (flagged as inherited, tie-broken by claim id).

The second claim — actually naming what the shape suggests, a signature→variant inference — needs a
literature reference passed to the call, a deterministic pre-gate (something observed, an
affirmatively-occupied word, resolution not "insufficient," frame not explicitly non-overhead), and a
second LLM call returning an explicit "consistent" verdict. The inline second call still never fires in
production: every real caller (live ingest, batch recorder, API route) leaves that literature argument at
its default of `None`, so live imagery *ingestion* produces only the subject-blind claim. Corroborating a
shape against a literature fingerprint happens instead in a separate module, the attribution proposer,
which reuses this one's gate and prompt machinery but drives its own orchestration and runs only through a
keyed CLI subcommand. What changed on this branch is that its *output* is now frozen into the corpus: one
`d07_sat_confirm_karachi__attr.json` bundle ships and is globbed in at every keyless boot, so the
VLM-corroboration result reaches the demo even though the proposer itself never runs live (see the
attribution section). A related gap:
the argument meant to carry authoritative text coordinates into an image claim is likewise never
populated by any caller, so an imagery observation's coordinates are always absent on the path that
actually runs.

### Per-document finalize, dedup, and stable IDs

After all of one document's calls return (text plus every co-located image's VLM read, run
concurrently), a fixed sequence runs before anything touches the store: inherit observation time onto
undated image claims → canonicalize every relationship to the ontology's "house direction" using only
this document's own entities → fold within-document duplicates → mint deterministic claim IDs and remap
every reference that pointed at a provisional one.

Within-document dedup is narrow: two claims fold together only if they share an exact signature over
document, kind, polarity, the asserted triple, normalized payload, event time, premises, and targets —
excluding report/ingest time and the claim ID itself, so a verbatim restatement collapses regardless of
timestamp. Two *different* wordings of the same fact in one document, or the same fact across two
documents, are never merged here; both are left to corroboration counting at rebuild, a stricter,
separate notion of independent evidence.

ID minting is what makes the corpus reproducible: claims are sorted by a fixed tuple built from their
earliest provenance locator (row, then line, then page, then frame, then bbox, then region, then file —
first exact match wins) with a content signature as tiebreaker, and IDs are handed out by walking that
list with a per-locator counter. Because the sort key comes purely from content, re-extracting the same
document mints byte-identical IDs — the actual mechanism behind reproducibility, not any property of the
model being deterministic.

### The single-writer boundary, and two things that don't actually connect

The only mutation the append-only evidence log permits is an insert; `BEFORE UPDATE`/`BEFORE DELETE`
triggers abort even a raw SQL attempt to change a row. `ingest_document` can, in principle, rebuild and
fire observables immediately after appending, but both are callables *passed in* by the caller, not
imported directly — and the one production caller, `POST /ingest`, passes neither, doing its own
rebuild-and-swap afterward to avoid a double rebuild. So the in-lane rebuild branch is exercised by
tests, never the deployed endpoint. Append-then-rebuild is never parallelized: the same claims in always
produce byte-identical IDs and a byte-identical view out.

Two things are worth noting. First, there is no cross-document or re-ingestion duplicate
check anywhere: within-document dedup only compares claims already scoped to one `(source_id, file)`,
and the log has no uniqueness constraint on claim ID — replaying the same bundle twice silently
double-inserts every claim under its own identical, deterministically-minted ID. Second, image
fingerprinting doesn't connect end to end: ingest freezes sha256/PDQ/EXIF *nested* inside an
`image_fingerprint` attribute, but both intended consumers — the credibility scorer's recycled-image
check and the independence-scoring module — read those fields as flat top-level attributes. Nothing
flattens the nested dict back up, so on every real imagery claim the pipeline produces, recycled-image
and near-duplicate detection sees nothing; it fires only on hand-built fixtures that happen to place the
fields flat already — a fully implemented feature that is inert on real data because producer and
consumer disagree on shape.

### The keyless path, and how faithful "keyless equals live" really is

A "bundle" is the frozen JSON output of running loader-through-finalize once, for real, against a live
model, with the ingest timestamp hardcoded to one pinned date (2026-07-19) so re-recording is
byte-stable. Booting keyless is a pure glob-and-append of those files in sorted filename order: no model
call, no network, no randomness. The CLI recorder that produces bundles in the first place additionally
threads a two-stage geocoder — gazetteer cache, then optionally live Nominatim — into the location step,
something the live API path never does (its extractor call passes no geocoder at all, so a toponym
submitted through the live endpoint today is frozen with no coordinate, while the identical text run
through the offline recorder gets a real one).

This is the honest caveat at the center of the whole story: "keyless is identical to live" is true only
in the sense that keyless bundles are *recordings* of one past run — not that a fresh live run would
reproduce them. The forced-tool-call schema pins the *shape* of the output, never its content, and with
no sampling parameters pinned (omitted, not zeroed — the provider default governs), a fresh keyed
extraction over the same text can legitimately return different wording, counts, or field selections
each time. ID minting and within-doc dedup are deterministic given a fixed set of claims, but the claims
themselves are only fixed if they come from a frozen bundle — the demo's reproducibility rests on the
checked-in bundles, not on any property of live extraction. The live API is gated on top of that: raw-
text ingestion returns 403 unless `CHANAKYA_ENABLE_EXTRACTION` is explicitly set truthy, and even then a
missing key returns 400 rather than silently falling back. The bundle-submission lane of the same
endpoint always works, keyed or not — pure append, identical to what boot itself does. And the live API
flatly refuses any submission naming a file path rather than raw text or a bundle, so the entire
PDF/OCR/image-file loader path is unreachable through the deployed app at runtime — it only ever executes
offline, through the same CLI recorder that built the corpus.


---

## Derivation: the facts the system infers for itself

Everything in the graph that no document literally stated falls into two families, and the split matters
because one family keeps the audit trail intact and the other quietly frays it.

The first family is the **offline derivation passes**: four routines that run *after* raw extraction and
*outside* the deterministic `rebuild()`. Their shared discipline is "propose upstream of the store,
`rebuild()` disposes" — none of them mutate the graph. Three of them manufacture new claims on dedicated
lanes and the fourth edits frozen claim bundles in place; the next rebuild folds the results in like any
other evidence. Because they emit *claims*, and a derived claim is forced to name its parents, this family
is clean by construction.

The second family is everything `rebuild()` itself conjures that is **not a claim** — nodes that exist
only because an edge pointed at them, coordinates borrowed from a gazetteer file, do-not-merge edges whose
only "source" is a YAML row, a relocation arrow minted from two other edges. These are inferences too, but
they never pass through the claim log, so their provenance does not chain back to anything a source said.
That is where provenance stops short of a source, and this chapter ends there.

### The four offline passes at a glance

| Pass | Live on the shipped demo? | Uses an LLM? | Emits | Marked as derived? |
|---|---|---|---|---|
| Basing | **Yes** (3 frozen bundles booted keyless) | No — pure traversal | `<unit, based-at, site>` claim | `kind=inference` + premises; but `method` mislabelled `llm` |
| Attribution | **Yes** — 1 frozen bundle booted keyless | Yes (one scoped call/triangle, offline) | `observed-at` inference copying an existing presence edge | `kind=inference` + both premises |
| Coreference | **No** — held back pending evaluation | Yes (one forced-tool call/doc) | `coref-same-as` claim | `inference` if a member is declared, else `observation` |
| Renormalisation | **No** — CLI-only, dry-run default | No | rewrites 6 location fields on frozen bundles | edits in place, before→after audit row |

### Basing — the only derivation that ships

Basing manufactures the one fact the order-of-battle question needs but nobody writes down: that a *unit*
is **based at** a *site*. It is a pure graph traversal — no model, keyless, byte-reproducible — and it runs
over occupancy edges swept in sorted order. Per candidate:

- Find an `observed-at` edge where one endpoint is a `basing_site` and the other is observed equipment.
- **Located-site gate** (`require_located_site: true`): the site must carry a resolved gazetteer reference
  *or* a WGS84 lat+lon. A province or an "air-defence sector" is rejected outright — an area of operation
  is not a base.
- **Vacancy gate**: take the site's *most-recently-dated* backing observation that does not state vacancy.
  A reading counts as vacant if its polarity is anything but positive (a negated sighting is treated as
  vacancy), or if it carries an explicit occupancy word that is *not* in the occupied vocabulary
  (`occupied/garrison/active/deployed/manned/present/occupation`). Crucially, an *unstated* occupancy on a
  positive claim is treated as **not vacant** — the sighting itself is the evidence — so an empty-site
  reading can never ground a positive basing claim, nor even win the "latest" tie-break.
- **Formation lookup**: from the equipment node (plus one hop over `equips`) follow `inducted-into` edges to
  units, rank most-evidenced first (by claim count, tie-broken by unit id), and take the top
  `max_units_per_site`, which ships at **1**.
- **Idempotence** (lane-scoped): skip if this observation already backs an inference on the `based-at` lane.

The emitted claim is a `kind=inference` with `premises=[occupancy, formation]` and a `doc_ref` spanning
**both** source documents, so its parents are named at the claim layer. Its `event_time` is inherited
*whole* from the latest premise — date shape and granularity preserved, not flattened — which is exactly
what lets an old base age out and a newer sighting supersede it. Three frozen `*__basing.json` bundles are
checked into the primary scenario and globbed in at every keyless boot, so this is genuinely live: e.g.
`unit_hq9b --based-at--> site_rawalpindi`, dated 2021-10-09, built from a variant occupancy plus an
induction claim.

One honest defect: **the derived basing claim is stamped `method:"llm"`**. The builder never sets an
extraction record, so the default (`method="llm"`, `model_conf=1.0`) mislabels a keyless graph derivation
as an LLM read. This is cosmetic to *confidence* — the credibility engine has no `model_conf` term (that
seam is fixed at 1.0) and prices a claim purely off its source class, freshness and integrity — but it
is a genuine mismatch in the audit trail about how the fact was produced.

### Attribution — elaborate and cited, and now exercised at boot via a frozen bundle

Attribution exists to let an image corroborate a textual "HQ-9 at X" report. It waits for resolution to
co-locate three things at a `basing_site`: **A**, a subject-blind VLM shape observation with geometry
tokens; **C**, a non-VLM relationship claim on a presence edge naming a variant (directly or one hop away);
and **B**, a reference-literature site-geometry fingerprint from a curated register, think-tank or
trade-media source, distinct from C. Each surviving triangle runs **one** scoped, subject-blind
corroboration call (a deterministic pre-gate first drops frames with nothing observed, a non-affirmative
occupancy word — note this is an *allowlist*, the exact opposite polarity of basing's denylist over the
same vocabulary — an "insuff" resolution, or an explicitly non-overhead frame). The inference is emitted
**only if the model returns `consistent == True`**, copies C's exact triple so the two land on one edge,
cites both the image bounding box and the literature span, and stamps `decoy_risk=True` and
`single_pass=True`. The call budget is `max_calls_per_rebuild`, which is **8**.

Where the fact fires its provenance is clean — and on this branch it does fire in the shipped demo. One
frozen `d07_sat_confirm_karachi__attr.json` bundle ships in the primary scenario, and because the boot
seed globs derived bundles (`__attr.json` alongside `__basing.json`) it is replayed at every keyless boot
with no key and no proposer run. The live proposer itself still has no boot/seed/API caller — only the
keyed `ingest attribute` CLI subcommand produces a bundle — but the pre-computed result is now part of the
graph the reviewer sees. Concretely, the inference lands as a cited **Inferred** corroboration: an
`observed-at` edge from `comp_tel_chassis` (the TEL chassis, matched from the bundle's `HQ-9/P TEL` subject
via a registry alias) to the Karachi emplacement, status **possible** (assertion confidence ≈0.11 — below
the probable floor, pulled down by freshness decay on the 2022 report and held under the decoy-risk cap),
cited to both the attribution-bundle claim and the backing satellite source line, and visible in the
evidence drawer at boot. Two footnotes on the mechanism: its `decoy_risk=True` caps the inference at
probable through a **hardcoded** cap-flag in the status machine, not through the
`gates.decoy_risk.cap_at_probable` config key, which (see the credibility chapter) nothing reads — though
on this bundle the confidence floor binds first and the edge lands at *possible*, below even the cap. And
its idempotence guard is *not* lane-scoped: it skips any observation already used as a premise of *any*
inference, so running basing first can suppress a legitimate attribution — an order-dependent coupling
between two passes only one of which now ships a bundle.

### Coreference — built, and deliberately held back pending evaluation

Coreference runs as extraction pass 2. It builds a mention inventory from pass-1 claims (declared entities
first, then undeclared relation endpoints typed from the ontology's edge domain/range), sends the document
plus numbered mentions to one forced-tool call, and asks only for mentions the *document itself* treats as
one entity, each with a licensing quote. It **never merges** — it emits `coref-same-as` claims on their own
lane, `kind=inference` when a member is a declared entity (so there is a real premise to cite) and
`observation` otherwise. Deterministic rails re-check the model: the evidence category must be
explicit-equivalence, name-variant or unambiguous-anaphor; the quote must occur verbatim in the document;
≥2 members; same-type only (one `unknown` endpoint may join a typed cluster); any document-stated
`distinct-from` is a hard veto; overlapping clusters are dropped first-wins.

It is currently **gated off in two independent places, both deliberate**. The producer block in
`credibility.yaml` ships commented out, so the proposer returns an empty list; and even with the producer on,
the downstream consumer key `coref_authoritative_evidence` in `resolution.yaml` ships **empty**, so a
`coref-same-as` claim is raise-only — it can lift a pair into the analyst queue but the module merges nothing
on its own. This is a scoping decision, not a defect. Coreference is the one derivation path that reads
document *discourse* rather than string similarity, and it has not yet been through the offline evaluation
that would justify letting it write to graph state on the real corpus; the deterministic rails around it
(explicit-equivalence / name-variant / unambiguous-anaphor only, verbatim licensing quote, same-type,
document-stated `distinct-from` as a hard veto) are already in place for when it is turned on.

### Renormalisation — coordinate repair, dry-run by default

Renormalisation re-runs the deterministic location canonicaliser (with the geocoder disabled) over
already-frozen bundles, to recover a coordinate an earlier recorder mis-classified — a grid mistaken for a
toponym, say. Only **6** fields may change (`surface_format`, `wgs84_lat/lon`, `precision_class`,
`geocode_candidates`, `proposed_alias`); `raw`, `resolved_place_ref` and everything non-location are left
alone; every edited row is re-validated and every change is written as a before→after audit row; and
`apply` defaults to **False**, so it is a dry run unless the `ingest renormalize --apply` CLI flag is
passed. Nothing at boot or in the API touches it. Its docstring overstates the guarantee: it claims "additive,
never destructive", but `surface_format` and `proposed_alias` are rewritten *unconditionally* on any
successful parse, including cleared to null when a toponym is reclassified as a grid. Only the coordinate is
genuinely protected (a geocode-derived coord is never re-derived, and a disagreeing parse aborts the whole
block at an epsilon of 1e-9).

### The clean bit: a derived claim cannot corroborate itself

All three producers are **raise-only** — they set no status and no confidence; a raw claim record has no
such field. Pricing is left to the credibility layer, which then treats a derived fact exactly like an
ingested one, with one guarantee that *is* wired: the independence grouper puts an inference in the **same
independent look as its premises** (a pair merges if one is in the other's `premises` list). Since confirmed
status requires two independent looks and same-discipline looks are half-weighted, a derived basing or
attribution claim can never bootstrap itself and its own evidence up to "confirmed" — it needs genuinely
separate corroboration. This rule lives in the credibility subsystem, not in the derivation passes, so the
derivation code's own docstrings assert it without exercising it; but it is real.

### Derived-but-unsourced values that rebuild adds

Everything above stays inside the claim log. These do not, and each is a place where "one click to the
exact source" lands somewhere weaker than a source:

- **Dangling-endpoint nodes.** When an edge names an endpoint that no entity claim ever asserted, `rebuild()`
  synthesizes the node anyway, typed from the ontology's domain/range or literally `"unknown"`. It borrows
  the edge's `claim_ids`, so it is traceable-by-borrowing — but no source ever asserted that the entity
  exists. This is an invented node.
- **Gazetteer coordinate adoption.** A node with no coordinate of its own adopts a curated `places.yaml`
  anchor's lat/lon and precision, tagged `location_source = gazetteer-anchor` and drawn on the map as an
  area pin. The plotted point is one no document states. Worse for provenance: the anchor id and the
  match evidence ride on the node object (reachable via `GET /node`), but the evidence drawer
  (`GET /evidence`) renders none of the location fields — so clicking through to "the source of this pin"
  lands on the claims that said "central Punjab", never on the gazetteer row that actually supplied the
  coordinate.
- **`distinct-from` edges.** These are drawn after scoring with **no claim_ids and no status** — their only
  provenance is a `reason` attribute reading "explicit do-not-merge (hard veto)". The veto originates in
  config (registry or gazetteer `distinct_from`), never in an ingested claim, so opening the drawer on one
  yields an empty claims list. They are the visible OSINT traps (Port Qasim ≠ Karachi Port, and the four
  area anchors against each other), but their "source" is a YAML file. Candidate `same-as` edges are
  similarly claim-less unless a source genuinely asserted the identity.
- **The `supersedes` relocation edge.** Minted from two basing edges *after* the status loop, it is never
  scored (status stays null). It does carry the union of both edges' claim_ids, so it is traceable — an
  honest-but-derived arrow, not an assertion.
- **Analyst status overrides.** The one path that writes status outside the machine, `set_status`, sets the
  label straight from the decision log and adds **no marker** — and no read route exposes the decision log.
  So a "confirmed" that is really a human override is, from the element's drawer, indistinguishable from a
  machine confirmed, and its underlying `assertion_confidence` may sit *below* 0.80. Note the asymmetry: an
  integrity-flag override *does* leave a visible flag; a status override does not. It is not derivation in
  the claim sense, but it is the most significant exception to "confirmed is structurally separated from probable."


---

## Resolution: deciding two mentions are one thing

### From mentions to an overlay, recomputed every time

Resolution never touches the claims. Every merge it decides is expressed as an *overlay* — a map from each raw entity id to the canonical id its cluster elected, plus `same_as` star edges — computed fresh on every `rebuild()`. There is no stored resolution state to drift; the partition is a pure function of the claim list plus the append-only decision log. The consequence worth internalising: an analyst never edits the graph directly. An accept or a reject is appended to the log, and the *next* rebuild replays it into the resolver's inputs. Reversal is new evidence plus a rebuild, never an in-place undo.

The raw material is "mentions": every entity-form claim, plus both endpoints of every relationship claim. Entity claims are grouped into profiles keyed by `type:name`, first-claim-wins on each attribute so replay order is deterministic. Relationship claims become directed edges each carrying an `edge_instance` key — and for functional predicates like `based-at` that key is the *subject alone*, so a unit's old and new basing sites land as co-objects of one instance. That single modelling choice is what later lets a relocation be read as *anti-identity* evidence rather than as two entities that happen to share a neighbour.

The config registry (`config/entities.yaml`) is seeded in as *claim-less candidate entities* with stable ids. They are merge targets, not nodes — a seeded entry only becomes a visible node if a real claim resolves onto it, and if its cluster wins it lends the cluster its stable id, unifying the id namespace across graph, lens and oracle.

### Blocking: cast a wide net, then judge

Candidate generation is deliberately recall-biased — it would rather ask a pointless question than miss a real merge. A pair becomes a candidate if it co-occurs in *any* of six blocks: a shared normalised **name token** within the same type and namespace; a shared **hard-id** value (this block ignores type); a **shared graph neighbour** among two same-type entities (the "different name, same neighbourhood" case); membership of one **alias class** even with no shared token (FD-2000 ≡ HQ-9/P); a **containment/acronym** relationship (one name is the other plus a descriptive word, or its initials); and everything already flagged **raise-only** (LLM proposals, source `same-as` claims) or **authoritative** (opted-in coreference).

One subtlety the reader should hold onto, because it governs the China-vs-Pakistan traps. "Namespace" is the first present of country / operator branch / service branch / domain. In *blocking* it is a literal bucket key — a mention with no namespace lands in the `None` bucket and co-blocks only with other no-namespace mentions, never with a China- or Pakistan-stamped one. The "missing namespace = wildcard" behaviour is a *separate* predicate used only in the containment path and the same-as/coref gates. In every mode, two *stated, different* namespaces block each other. So blocking is recall-maximising but not reckless: two things explicitly placed in different countries never even become a question.

### Two phases: high-precision bootstrap, then a relational fixpoint

Phase 1 is the precision floor. For each non-vetoed candidate it *bootstrap-merges at confidence 1.0* if any of these hold: a shared unique id; alias-equivalent names; an exact normalised name with a matching, non-empty namespace; a containment/acronym match; or membership in the authoritative coref set. No scoring, no relational term — these are treated as statements of identity.

Phase 2 is the collective step. It iterates over all candidate pairs, recomputes the merge score against the *current* partition, and bands each pair into one of three identity statuses rather than a merge/no-merge binary: **confirmed** (score clears the auto floor → merged into the cluster), **probable** (≥ `hitl_low` → a candidate for the analyst), or **possible** (≥ `possible_floor` → a latent watch-list link, held in memory, never drawn). It auto-merges the `auto`-band pairs and repeats until a full pass adds nothing; because clusters only ever grow within a rebuild, a no-new-merge pass is the fixed point and termination is guaranteed. Two things shape which pairs clear the auto floor. The floor is now **per type**: it sits at the global 0.85 for identity-sensitive types but drops to 0.37 for `manufacturer` and `trading_org` (`auto_merge_by_type`), where a near-identical name reliably denotes one entity — this is what auto-merges the CPMIEC, SINO-GALAXY and Taian/Wanshan spelling variants the global bar would never reach, while every variant/unit/site trap stays split. And a *bare fuzzy name match* (name similarity alone, no shared neighbourhood, no source-asserted identity) is capped at *possible* by `name_alone_caps_at_possible`, so an over-eager string match never even reaches the analyst's desk — this cap does not touch the exact-name/alias-class 1.0 bootstrap above. The relational signal reading the *live* partition is what makes this collective rather than pairwise: as clusters grow, two entities that share a neighbour can start to look alike even though neither string matched.

### The score and its four signals

The merge score is a weighted sum, clamped to [0,1]:

| Signal | Weight | What it measures |
|---|---|---|
| attribute | 0.40 | token-sorted Jaro–Winkler name similarity (1.0 if alias-equivalent) |
| relational | 0.40 | Jaccard overlap of resolved neighbourhoods, scaled by shared-count |
| temporal_consistency | 0.05 | 1.0 normally; 0.0 if the pair are co-endpoints of one edge-instance |
| source_asserted | 0.15 | max credibility grade among sources asserting `same-as` |

Name and neighbourhood are co-equal at 0.40 each. **attribute** short-circuits to 1.0 whenever the alias index calls the pair equivalent — which also bypasses any conflict penalty. Otherwise it is pure Jaro–Winkler on the token-sorted, transliterated, punctuation-split forms. That normalisation is load-bearing: `HQ-9/P` tokenises to `[hq,9,p]` and `HQ-9` to `[hq,9]`, so they do *not* read as identical — and Jaro–Winkler's prefix reward is exactly why the `FD-2000`/`FT-2000` trap scores high and must be stopped by a veto, not by the metric.

**relational** is Jaccard over each side's *resolved* neighbourhood, scaled by `min(1, shared/support_k)` with `support_k = 2`. This fixes a real artefact: raw Jaccard saturates at 1.0 on a *single* shared neighbour, and eighteen basing-site pairs each hanging off the same unit's one `based-at` edge were reading as "identical neighbourhood" and flooding the analyst's queue. Now one shared hub gives half strength, two give full. Two further gates fire on this corpus: for types whose ontology declares neighbourhood is not identity evidence (`area_of_operations` — sectors and provinces share neighbours by construction), relational is forced to 0.0; and the relocation edge-instance that zeros the temporal signal is *also excluded from both neighbourhoods* before the overlap is taken, so a relocation can't sneak back in as a shared neighbour. One further refinement is now wired: a shared neighbour no longer counts full strength regardless of how solid the link is — each contributes the *bottleneck confidence* of the merge chain that unified the two sides' endpoints, so a neighbour reached only through a weak merge lends proportionally less relational certainty. That is the cascade guard against a shaky merge propagating into new ones. On this corpus almost every unification is a 1.0 bootstrap merge, so the weighting rarely moves a score — but the guard is live.

**temporal** carries only 0.05 — its weight barely moves the total. Its real teeth are the two zeroing effects above, not the arithmetic term.

### The bands and what they actually gate

The banding is a three-status ladder, from `config/resolution.yaml`: at or above `auto_merge` (0.85, or the per-type floor) a pair is **confirmed** and merged; in [`hitl_low` 0.45, auto) it is **probable** and reaches the analyst queue; in [`possible_floor` 0.25, hitl_low) it is **possible** — retained as a latent watch-list link that carries a confidence breakdown but is held in memory only and never drawn as a wire edge, so the view JSON stays byte-identical; below `possible_floor` it drops. That `possible` tier is the deliberate antidote to fragmentation: the unresolved tail is neither a false merge nor a lonely singleton, but an honest link the analyst can query without being pestered by it. (`auto_merge`/`hitl_low` unchanged from before; `possible_floor` is new.)

The critical wrinkle is *what number is compared to the auto floor*. It is not the full total — it is the **deterministic subtotal**, the total minus the `source_asserted` term. Since the three deterministic weights sum to exactly 0.85, at the *global* floor the fuzzy path can auto-merge *only* on simultaneous perfection of name, neighbourhood and timeline — which never happens on real data, so at the global bar every auto-merge comes from a Phase-1 bootstrap rule. The exception is the per-type floor: at 0.37 for `manufacturer`/`trading_org` the fuzzy subtotal genuinely does clear the bar for the org spelling-variant pairs — the one place a Phase-2 fuzzy score auto-merges. The `source_asserted` subtraction is deliberate — it makes source-asserted identity structurally *raise-only* no matter what the weights are set to: a source claiming two things are the same can lift a pair into the analyst queue but can never, by itself, merge it. HITL banding uses the *full* total (≥0.45) or arrival on a raise-only channel; below that a pair drops to the *possible* watch-list (≥0.25) or, lower still, is dropped entirely.

### Vetoes: where geography can kill a merge

Vetoes ("cannot-link") are computed up front and enforced at bootstrap, at the fixpoint, *and* on the HITL queue. They come from curated `distinct_from` pairs, registry distinct pairs, gazetteer place-distinct pairs, source-asserted distinct-from claims, learned `barred` pairs (now grown from HITL rejects — see below), conflicting hard-identifier references, geography, and — new on this branch — a stated conflict on a declared *critical* attribute (credibility-gated; detailed in the redesign section below). A veto propagates transitively: any union that would place a vetoed pair into one cluster is refused outright.

Two *independent* geographic vetoes exist and are easy to conflate. The first works at the raw-entity level: if both entities carry their own frozen WGS84 coordinate and the geodesic separation exceeds the per-type tolerance (`basing_site` 25 km, default 100 km), the pair is refused — no score, no queue, because a geographic impossibility is not a question worth an analyst's time. A side with *no* coordinate is unknown, never "elsewhere," so absence never triggers it. The second works through the gazetteer: place resolution snaps location-bearing entities onto curated places in `config/places.yaml` (by ICAO/LOCODE hard id, then exact toponym, then banded proximity), and pairs of curated places marked `distinct_from` — Port Qasim vs Karachi Port, the four area anchors against each other — veto apart *any* entities that resolved onto them. The raw veto is arithmetic and is not drawn; a curated distinct-from stays drawn as a visible trap edge.

Geography can also *support* identity without being an inference from distance: `places.augment` fuses two entities that resolved to the *same* place only when that place's precision class is in `place_identity_precision_classes` (`pad`, `site`, `terminal`). Two batteries sharing a *province* or *city* are never fused — an area anchor denotes a region, not a thing. This is a curated property of the anchor, not a distance threshold. Note one fragile default: remove that config line and every area anchor becomes fusion-eligible, silently reintroducing a bug the config comments say already bit once.

### Identity as an evidence-backed status — the redesign, mostly waiting on data

The three-status ladder above is the visible half of a larger redesign that treats a *merge* the way the credibility layer treats a *claim*: a hypothesis backed by evidence, not a boolean. Each merge or candidate carries a **merge-corroboration ledger** — one entry per identity signal (name, neighbourhood, timeline, source-asserted) that actually contributed — surfaced on the wire (a confirmed merge's `resolved_from`, a candidate's `merge_confidence` breakdown). This is a *parallel* status machine to the claim-credibility ladder and never crosses it: `merge_confidence` answers "are these two mentions one entity," is never folded into a node's `assertion_confidence`, and identity-confirmed is a different axis from credibility-confirmed. The two even disagree in scale on the corpus — at default boot the resolver reports 62 confirmed identity merges while the credibility machine confirms only 12 node *assessments*. The ledger is recomputed each rebuild rather than banked across rebuilds; durability of a confirmation is enforced separately, by the perishable cap below.

Three further mechanisms are built and wired, and are the clearest instance of this document's built-versus-exercised discipline: they are **byte-inert on the current sparse single-subject corpus** because nothing in it triggers them, and `artifacts/spine/12-data-refresh-calibrations.md` is the standing record of exactly which corpus additions would light each one up.

- **Attribute roles.** Every attribute carries a per-type identity role (`config/resolution.yaml → attribute_roles`): *critical* — a stated disagreement is a hard cannot-link wall no similarity can cross; *supporting* — agreement raises the merge score, disagreement is a soft penalty; *neutral* (the default for anything unlisted) — both values are retained with provenance and identity is unaffected. The critical wall is **credibility-gated** (`critical_veto_min_grade: C`): it only walls when the conflicting value is asserted by a source at STANAG grade A/B/C on *both* sides; a low-grade (D/E/F) source raises the pair to a *probable* HITL candidate instead of walling, so one flaky repost can't shatter a well-supported merge. Exactly one attribute is declared critical (`variant.operator_branch`, the PLA-vs-Pakistan wall), and it is inert today because no claim in the corpus actually *states* `operator_branch` — the China/Pakistan traps are held apart by the registry's `distinct_from` instead. The supporting *agreement* half is live; the supporting *penalty* half needs a `conflict_penalty` knob that ships unset, so it is dormant too.
- **Bridge-across-a-wall alarm.** A candidate whose union would fuse two clusters that a `distinct_from` wall holds apart is never auto-merged; it surfaces as a *probable* candidate flagged "bridge across a wall" so the analyst sees the near-miss. Live and default-on; it fires zero times on this corpus because no in-band pair straddles a wall.
- **Temporal identity.** Claims carry event, report and ingest time, and the resolver classifies a value's history over time as *single* / *ordered* / *contradiction* / *unorderable*: a clean update-over-time (an ordered succession on a perishable attribute) is explicitly *not* a contradiction, a would-be confirmation resting only on a perishable trajectory is capped to *probable*, and a single source that witnessed the change across the succession lifts that cap. All of this is gated behind an attribute declared `perishable: true` — of which the shipped config has none — so the classifier runs but has no live consumer here; the value-timeline it feeds does surface on the wire as a node's `attr_history`.

The honest summary: the identity *substrate* (three statuses, the ledger, the value-timeline, the credibility-gated walls) is fully as-built and running, and its recall-and-precision refinements are wired and unit-tested — but on a corpus that is one weapon family of sparse, mostly single-source mentions the refinements have little to bite on, and the `spine/12` ledger names the additions that would exercise each.

### Clustering, canonicals, and conflicting merges

Resolution is fully clustered via union-find, never pairwise. Entity merges and place merges are reconciled in *one* union pass, veto-guarded again so a place-merge can't smuggle a vetoed pair together. Each cluster elects its canonical by ranked preference: registry stable id, then alias-table canonical name, then highest degree, then lexicographically smallest id. When merges "conflict," there is no arbitration heuristic — the transitive veto simply refuses any union that would co-locate a forbidden pair, and the offending candidates are dropped from the queue rather than resolved by majority.

### Alias-table learning: the accept→auto-merge loop, now wired

An analyst *accept* becomes alias-equivalence — and so an auto-merge — on the next rebuild, and a *reject/split* feeds a learned do-not-merge set the resolver honours transitively. This is a real closed loop on this branch. It was silently broken on an earlier build: the HITL writeback nested the pair under `effects.grow_alias` while the replayer read `decision.pair`/`verdict`, so every live merge record was skipped and the seeded alias table did all the work — the "same pair auto-resolves next time" behaviour fired only in tests. The fix (commit `e868ae3`) aligned the keys *and* made the route carry the candidates' **names**, which the name-keyed alias index actually needs. Now the merge card genuinely mutates resolver state: the writeback copies the chosen verb's structured effect verbatim — `grow_alias` (accept), `record_distinct` (reject), `split_merge` (split), each carrying the pair's names — and resolution's alias builder replays every `merge_adjudication` record, calling `link(a,b)` to grow the alias equivalence class on an accept and `distinct.add` to record a durable veto on a reject/split. The seeded alias table (the HQ-9 family, CASIC, the S-400 transliterations) remains the precision floor; the *learning* layer on top of it now works, and is covered by a test that drives the real producer → writeback → replay path.

Several other resolution refinements ship **built but dormant under the shipped config — deliberately, pending the evaluation that would justify enabling them**: the LLM candidate proposer (`propose.py`) has no runtime caller on the live path (the "recover H-200 → HT-233" recall demo needs `merge_proposal` records already in the log); authoritative coref never bootstraps (empty allow-list *and* commented-off producer); the supporting-attribute *conflict penalty* is real code with no effect while `conflict_penalty` ships unset, so a supporting-attribute disagreement never actually docks a merge (its agreement half does count), and there is no `hard_id_fields` config so the unique-hard-id bootstrap never fires; and `identity_raise_min_weight = 0.0` leaves that gate open so every source `same-as` reaches the queue. These are additive seams, not load-bearing paths — the shipped precision comes from the bootstrap rules and vetoes above. One is worth flagging as a genuine sharp edge rather than a benign seam: bootstrap is namespace-gated but not consistently *type*-gated, so the alias-equivalence and hard-id paths could in principle merge two different-typed entities that share an alias class — the one place a cross-type fusion could slip past the type filter the HITL queue otherwise applies.

### Where resolution precision comes from — and how the type-keyed auto-merge was activated

Precision rests on the Phase-1 bootstrap (alias class / exact name / containment / acronym) plus the vetoes, not on the scored fixpoint — and that is a deliberate design decision, not an accident of tuning. The auto-merge line sits at **0.85**, which is exactly the ceiling the three deterministic signals can reach together (0.40 + 0.40 + 0.05); the `source_asserted` term is subtracted before the comparison, so a fuzzy pair can auto-merge *only* on simultaneous perfection of name, neighbourhood, and timeline. On real data that never happens — which is the intended effect. It keeps source-asserted identity structurally raise-only, and it forces every genuine auto-merge through an exact, auditable rule rather than a soft score.

The threshold cannot simply be lowered, and this was confirmed with a direct experiment over the real corpus. On a **single-subject** corpus — everything is one weapon family — the two fuzzy signals are structurally the wrong instruments. The neighbourhood signal cannot discriminate, because a trap shares as much context as a real match (every entity hangs off the same hub). And the name signal is token-sorted Jaro–Winkler, whose prefix reward actively *favours* the variant-family near-names — `HQ-9`/`HQ-9B`, `S-300`/`S-300PMU`, `FD-2000`/`FD-2000B` — that must stay **separate**. Dumping the score distribution over every candidate pair made this unambiguous: the highest-scoring pairs are traps, not merges — `HQ-9 ↔ HQ-9B` (distinct variants), a Karachi-vs-central-Punjab site pair ~1,000 km apart, and the flagship `PAF ↔ Army Air Defence` unit trap — all of them outscoring the one clean real merge (two spellings of the CNPMIEC manufacturer). No global threshold admits the good ones and keeps the traps out; every setting either misses the real merge or admits a trap first.

The one signal that *does* separate real merges from traps is **entity type**: for organisations a near-name means the same thing (`CPMIEC ≡ China … Precision Machinery`, the `SINO-GALAXY` spellings, `Taian ≡ Taian/Wanshan`); for weapon variants, units, and sites a near-name is a trap. This branch acts on exactly that. `auto_merge_by_type` drops the auto floor to 0.37 for `manufacturer` and `trading_org` only, which admits those organisation spelling-variant merges with margin above every same-type trap (CASIC ≠ its own 23rd Institute at 0.34; ORIENT ≠ SINO-GALAXY at 0.29), while every identity-sensitive type keeps the global 0.85 and `source` handles are deliberately excluded (cross-account personas stay a HITL call). Type was already used throughout resolution to *suppress* merges (the HITL same-type gate, the per-type relational gate, type-gated bootstrap); the type-keyed auto-*activation* is the piece this branch added, and it is pinned by an acceptance test over the real corpus.

A downstream cost remains worth stating plainly. Confirmation is computed *after* resolution and requires two *independent* sources pooled onto one node; when mentions that should be one entity stay split, their corroborating claims never pool and the node cannot promote. The per-type org merges reduce that fragmentation — collapsing the CPMIEC and SINO-GALAXY spellings pools their claims onto one node each — but they do not by themselves lift the confirmed-*status* count. On the real corpus the credibility machine confirms **12 nodes and 2 edges** at default boot (13 nodes on the full corpus, adding `site_rahwali`; the two confirmed edges are both `equips` links), while the large single-source tail stays at probable or below. So confirmation genuinely fires end-to-end on production data — but sparsely: the pipeline is still deliberately biased toward not-merging, and the honest counterweight to the precision the vetoes buy is that the confirmed set stays small. The `/coverage` surface makes exactly this legible, per type.


---

## Credibility: how confidence is computed and how status is earned

Everything in this chapter runs inside the deterministic `rebuild()`, in a fixed four-move order: score
every claim on its own, cluster claims into independent looks, pool the looks into one assertion
confidence and stamp a status, then let a newer fact retire an older one. No clock, no network, no LLM,
no randomness enters any of it — the model already ran upstream and its output is frozen in the claims.

### The per-claim number is a product of three terms

A single sourced claim's credibility is `R(source) × Π(integrity) × freshness`. Three numbers between 0
and 1, multiplied. There is deliberately no fourth term for model/extraction confidence — that seam
exists in the schema but is fixed at 1.0, so extraction quality never touches the score.

**R(source)** is a normalized weighted sum of five analyst-tunable factors, read not from the individual
source but from its *class* row: authority (weight 0.35), process (0.30), directness (0.10),
track_record (0.10), intrinsic_plausibility (0.15). The arithmetic is Σ(weight·factor) ÷ Σ(weight) over
the factors present. Because every class row carries all five factors and the weights already sum to
exactly 1.0, the "normalize by present factors" denominator is always 1.0 — the normalization branch is
real code that never actually does anything. The class outputs land where you'd expect: curated-register
(SIPRI) ≈ 0.85, satellite ≈ 0.86, official (ISPR) ≈ 0.75, think-tank ≈ 0.69, exporter-state-media
(Global Times) ≈ 0.70, trade-media ≈ 0.64, customs-tender ≈ 0.61, named-social ≈ 0.35, anon-social ≈
0.25. Two things worth knowing. First, an **unknown source class returns 0.0** — fail-closed, so an
unrecognized source can never silently score as credible. Second, two of the five factors are inert
knobs: `track_record` is pinned at 0.5 for every class and `intrinsic_plausibility` at 1.0 for every
class, and the promised "per-claim LLM downward override" of plausibility is **not wired anywhere**. So R
is purely a function of source class, with no per-claim variation at all — a truthful curated-register claim and a
false one score identically at the source-reliability step.

**Π(integrity)** is the product of four M4-table lookups, each keyed `<table>.<flag>`, with a missing key
returning 1.0 so an absent signal never zeroes a claim. The tables and their penalties: recycled image
0.30, mismatched caption 0.30, uncheckable caption 0.9, coordinated-inauthenticity suspected 0.5,
too_clean 0.4, edited artifact 0.30, synthetic 0.10, unverifiable artifact 0.85. One of these tables,
`first_seen`, is *computed here* rather than supplied: the scorer runs a fingerprint dedup across the
whole claim set in order — an image whose SHA-256 exactly matches, or whose PDQ perceptual hash falls
within Hamming radius 10 of, an earlier claim is "recycled" (×0.30); the first occurrence is "original".
The coordinated-inauthenticity flag has a precedence chain: an analyst `flag_origin` decision is
strongest and taints *every* claim sharing that origin id, including claims ingested after the flag was
raised; below that, a claim-level stated flag; below that, the source's own inauthenticity boolean; else
"independent". Two honest gaps here. The `artifact_integrity` table has no live producer — nothing in ingest
ever writes that attribute onto a claim, so the "is this image edited/synthetic" penalty never fires on
real data and always contributes 1.0. And the **too_clean (0.4) penalty is built but not yet wired to fire
automatically** — there is no too-clean detector; that attribute is set nowhere in ingest and lives only
inside `answer_key.json`, which the pipeline never reads. On the boot corpus the only integrity penalty
that fires via automation is the 0.5 "suspected" from a source-level flag; too_clean is reachable *only*
if an analyst manually issues a `flag_origin` decision naming it.

**freshness** is `decay_base^(−age ÷ half_life)` with `decay_base = 2`, so credibility halves at exactly
one half-life. `age` is whole days between the claim's event time (falling back to report time, which
gets flagged in provenance) and the evaluation "now". A future-dated or same-day claim clamps to 1.0 —
nothing is fresher than the eval date. If there is no half-life, no base, or no reference date, freshness
is 1.0 (no decay). The half-life lookup is a three-rung fallback: a variant-qualified key like
`based-at.field` (30 days) if the claim carries a `freshness_variant` tag, then the bare edge key, then
the edge's **freshness-class default**. The catch: *no claim is ever tagged with a
`freshness_variant`*, so every dotted variant key is unreachable, and only one edge (`substitutable-by`,
540) has a live bare key. Every other decay rate collapses to the class default. The upshot is that only
two half-lives are actually alive in the running system: **540 days** (everything perishable or
semi-durable) and **1825 days** (force-revalidated); durable edges never decay. The 30-day
"field occupancy" rate that would punish a stale field deployment is unreachable at runtime — no claim
carries the variant tag it keys off. The 540 is not arbitrary: it is tuned so that on the corpus's real dates, the 2021
Rawalpindi position reads stale and the 2025 Rahwali position reads fresh.

### Independent looks, then noisy-OR pooling

A single confident claim is not corroboration. Co-referring claims are clustered by union-find, and each
resulting cluster counts as *one* independent look. Two claims are forced into the same cluster (i.e.
treated as dependent, not two looks) if they fail any hard axis: same **origin** (same source or origin
id, same image fingerprint, or an aggregator-and-its-upstream relationship — SIPRI plus the press it
compiles is one look); aligned **interest** (both sources' bias vectors sit in {operator-state,
exporter-state} — ISPR plus Global Times is one look); or **derivation** (one claim is a premise of the
other — an inference and its evidence are one look). Missing metadata assumes same origin (fail-closed
merge). Adversary-denial sources are excluded from grouping entirely, so a denial can never *add* a
corroborating look. Discipline (IMINT vs textual) is a *soft* axis: it never merges, but the first look
of each discipline gets full weight 1.0 and every later same-discipline look is downweighted to
`same_class_weight` = 0.5.

Pooling then works in two steps. A group's confidence is the strongest claim credibility inside it,
times the group's weight. The assertion's confidence is a **noisy-OR** across groups: `1 − Π(1 − c_g)`.
Echoes (anything that collapsed into one group) add nothing; genuinely independent looks compound. This
is why re-posting the identical document changes nothing — the duplicate shares a source, lands in one
group, and group confidence is a max, not a sum.

### Status is earned through a strict precedence ladder

One clarification up front: this ladder scores an *assertion* — whether a claimed fact is true — and runs
in parallel to, never mixed with, the resolver's own three-status *identity* ladder (possible / probable /
confirmed for "are these two mentions one entity"). A node can be identity-confirmed yet
assertion-probable, and a merge's `merge_confidence` is never fed into an element's `assertion_confidence`.
The status machine reads the pooled confidence plus a set of gate flags assembled elsewhere in the
pipeline, and walks an if/elif chain — the *first* matching rung wins, so the order is the logic:

| Rung | Label | Fires when |
|---|---|---|
| 1 | **stale** | a `superseded` flag is present (a newer fact retired this) — checked first: it is history, not a gap |
| 2 | **insufficient** | sufficiency says a required *kind* of evidence is missing — off the confidence scale |
| 3 | **contradicted** | an unresolved opposing group or a contradiction flag → routed to HITL |
| 4 | **confirmed** | `strong` AND not aging |
| 5 | **stale** | `strong` but the freshest look has aged past one half-life (demoted-from-confirmed) |
| 6 | **probable** | confidence ≥ 0.50 but confirmed not reached |
| 7 | **possible** | confidence < 0.50 |

The `strong` predicate — the eligibility test for confirmed — requires *all* of: confidence ≥ **0.80**;
effective independent looks ≥ **2** (`min_independent_groups`); not capped by a gate; and no gated
attribute left UNKNOWN. Sufficiency is not a term inside `strong`; it blocks confirmed only because rung
2 short-circuits earlier in the same chain. This has a sharp consequence that the arithmetic makes
non-obvious: because same-discipline looks are half-weight, two looks of the *same* discipline sum to only
1.5, which is below 2 — so **confirmed effectively requires two different collection disciplines** (e.g.
imagery + text → 1.0 + 1.0 = 2.0), or else three same-discipline looks (1.0 + 0.5 + 0.5 = 2.0). Two
satellite passes, however clean, cannot confirm anything on their own.

The cap gates are `adversary-denial` and `decoy-risk`, hardcoded as a two-element set in the status
module. Either one sets `capped`, which knocks `strong` false and forces an otherwise-strong assertion
down to probable with a `capped-at-probable` reason. Note the split responsibility: a doctored artifact
is *not* a status gate — integrity only hurts by pulling the confidence number down through its
multiplier, never by flagging a cap. And two freshness gates differ subtly: `aging` (any look past one
half-life) blocks confirmed but does not demote; `stale` (the *freshest* look past one half-life) demotes
confirmed to stale. The 0.50 probable floor is real and hard — an assertion below 0.50 can never be
labelled probable no matter what gates say; the gate reasons (`single-independent-look`,
`aging-not-fresh`) are only annotations on *why* an otherwise-strong assertion was held at probable
instead of promoted.

A word on a config block with no live reader. `credibility.yaml` ships a `gates` block declaring
`exclude_from_grouping` and `cap_at_probable` for adversary-denial and decoy-risk. **No code reads it.**
The behaviour it describes is real but hardcoded — grouping exclusion lives in the independence module
keyed off the source's denial flag, and the probable cap lives in the status module as a literal set.
Editing this block has no effect.

### Supersession: how a newer fact retires an older one

This is split across two points in the pipeline on purpose. Early, before any confidence exists,
`supersede.py` only *orders* two assertions on one edge instance by event time and nominates the newer to
retire the older, leaving the pair as a HITL candidate: strictly-disjoint-older becomes an ordered
candidate pair, same-instant becomes a contradiction (both flagged, cross-linked), and
undated/overlapping stays a plain candidate. Late, after the status machine has run, `promote_supersessions`
applies a quality floor — a question that could only be asked once the newer claim had a confidence. The
newer assertion must clear all of: reach at least its `min_band` (probable); carry a status in
`newer_status_allow` (probable or confirmed); have at least `min_independent_looks` (1) weighted looks;
and carry no blocking deception flag (adversary-denial, decoy-risk, contradiction). If it clears, the
`superseded_by`/`supersedes` links are written, the old edge is re-run through the status machine with the
`superseded` flag so it becomes stale, its "insufficient" Known Gap is dropped (a position the subject has
left is history, not a coverage gap), and a visible node-to-node `supersedes` edge is drawn. If the newer
claim fails the floor — **or if the floor block is simply absent from config** — nothing is retired and
the pair stays a candidate for the analyst. This is what refuses the planted grade-E adversary spoof from
silently retiring a well-evidenced position: being newer is necessary but not sufficient. It fails closed
in both directions.

### What actually advances time — and what does not

This is the most counterintuitive part of the whole subsystem. The evaluation "now" is resolved
**clock-free**. It is the pinned `credibility.as_of` if set, otherwise the newest claim date in the log.
The shipped config pins nothing, so "now" is always the latest claim available. Despite a docstring
claiming the API stamps today's date into `as_of` at request time, **no code does this** — the wall clock
is read only for alert timestamps and decision log entries, never for freshness. Therefore **nothing ever
goes stale by the passage of real time.** A graph left untouched for a year never re-triages itself. Time
advances in exactly two ways: a newer-dated claim arrives and pushes the fallback maximum forward (so
older claims age relative to it), or an operator explicitly edits `credibility.as_of` and triggers a
rebuild. That is the entire mechanism of "monitoring over time."

### What it actually takes to reach confirmed on the real corpus — and why it is harder than it looks

On paper, confirmed requires confidence ≥ 0.80 across two independent, fresh, cross-discipline looks with
sufficiency satisfied and no caps. In practice, almost nothing clears it, for a reason that has little to
do with source quality. The binding constraint is *resolution fragmentation*: the overwhelming majority
of graph nodes resolve to a single claim, so they have one look, so they can never reach the two-effective-look
bar regardless of how authoritative that one source is. The two-different-disciplines requirement then
compounds it — even a node with two looks fails if both are textual (1.0 + 0.5 = 1.5 < 2). And the
credibility ceiling itself bites: a lone satellite image caps at ≈0.86 for one look, but one look can
never be strong, and adding a second same-discipline look only brings 0.5 of weight.

The honest evidence that this fires *sparingly*: the golden view fixture the determinism gates run against
contains **zero confirmed elements** — five probable nodes, and edges that are probable, possible, stale,
or unscored. The confirmed *checker* (gate G7) is validated only against a hand-built synthetic
status-cases fixture, never against a real corpus element, so a pipeline that promotes *nothing* to
confirmed would still leave every determinism test green, and even the flagship worked-query acceptance
test passes on a `probable` terminus because the assertable band includes probable. So the load-bearing
distinction of the whole system — confirmed versus probable — has thin *test* coverage. But it does fire on
the corpus as shipped, just sparsely: **12 nodes and 2 edges** confirm at default boot (13 nodes on the
full corpus), while the graph otherwise lives in the probable/possible band. Confirmation lands where the
evidence genuinely doubles up across disciplines — the two `equips` edges, and a staged imagery-plus-text
beat on a resolved unit — or where an explicit analyst status override forces it. That override,
incidentally, is applied dead-last in the pipeline and can push an element to confirmed *past* the G7
arithmetic gate, which no test re-checks.


---

## The rebuild: how the graph is assembled, in order

Everything a viewer ever sees is the output of one function, `rebuild()`, which reduces the two
append-only logs — evidence (sourced claims) and decision (HITL/agent actions) — plus a frozen config
snapshot into the served graph. It is deliberately pure: no clock, no network, no LLM, no randomness
runs inside it. The LLM already ran upstream and its output is frozen in the evidence log; `rebuild()`
only *disposes* of that frozen material through deterministic rules, emitting a byte-identical view for
identical inputs. That purity frames the stage order below: nothing can "phone a friend," so each
stage's inputs must have been fully manufactured by an earlier stage.

### What triggers it, and what it costs

A rebuild happens on boot (once, with no previous view) and on every single write path — `/ingest`,
every `/hitl/*` decision, and every `/config` section write — routed through one method,
`rebuild_and_swap`, which takes the one process-wide lock, snapshots config, runs `rebuild()`, fires the
observable evaluator on the delta, and atomically swaps the held view. Reads (`GET /view`, `/node`,
`/evidence`) take no lock at all: swapping a Python object reference is atomic under the GIL, so a reader
always sees one whole view, never a half-built one.

There is **no incrementality and no caching whatsoever**. A one-claim ingest replays the entire evidence
log and rebuilds all 160 nodes from scratch. The only cross-rebuild memory is the logs themselves and the
config store. On the shipped keyless seed — roughly 29 claim bundles producing 160 nodes / 73 edges / 66
events / 18 known-gaps at default boot — a full rebuild measures about 560–600 ms, warm or cold; at demo
scale the cost of "recompute everything on every write" is invisible.

One thing that is *not* what the code comments claim: `rebuild()` accepts a `prev_view` argument and
passes it into resolution "for merge stability," but the resolver body never reads it. Every rebuild
re-resolves identity from zero. `prev_view` is genuinely consumed only outside rebuild, by the observable
evaluator, to compute the before/after delta for alerts.

### The pre-scoring filter cascade

Before any scoring happens, the claim list is narrowed by four operations in a fixed order, each
assuming the last has run:

- **Replay** both logs to plain lists.
- **Retractions** — a claim tagged as a retraction names a target claim; both the target and the
  retraction itself are dropped from *this* rebuild. Nothing is deleted from the log; it is simply left
  out on replay.
- **HITL claim exclusions** — any decision carrying an `exclude_claims` effect drops those claim ids
  here, *upstream of scoring*. This is the "reject a look" beat, and its placement is the whole point: by
  removing the look before the status machine runs, a confirmed verdict can legitimately fall back to
  probable because it now rests on fewer independent groups, rather than a label being force-flipped
  after the fact. (Note: no card the app actually ships emits `exclude_claims` — status "reject" was
  wired as a forced demote instead — so this branch is currently reachable only by hand-crafted decision
  records.)
- **`as_of` rewind** — if `credibility.as_of` is pinned, every claim not "available by" that date (judged
  by ingest/report time, not event time) is dropped; undated claims are kept, i.e. it fails open. This is
  the honest point-in-time "what did we know then" view. Default is null, so normally a no-op.
- **Edge canonicalisation** — relationship claims are reoriented to the ontology's declared from/to
  direction so that two oppositely-phrased statements of one fact key to the *same* edge instance and can
  corroborate each other. A no-op when the ontology declares no directions.

The ordering matters: retractions and exclusions must precede the rewind and canonicalisation so the
surviving set is already the truth-relevant one, and canonicalisation must precede resolution so that
edges group correctly by instance.

### The numbered stages

1. **Resolve.** Identity resolution produces a partition: each claim's resolved canonical reference,
   auto-merges, unadjudicated merge candidates, hard "distinct-from" vetoes, and the endpoint-type and
   gazetteer maps. This is also where two human channels land: replayed *accepted* merge adjudications
   grow the alias table (so a past human merge takes effect), and *rejected/split* ones are added as
   learned distinct-from vetoes (so "these are not the same" also propagates). It also reads the offline
   LLM proposer's frozen merge-proposal records as raise-only candidates.

2. **Assemble** nodes, edges, and events. Entity claims collapse to one node per canonical id, with
   **first-claim-wins** for each attribute and for location — deterministic in replay order, but only
   determinism is guaranteed, not correctness. Identity/coref triples are *consumed here, not drawn* —
   they already became a merge or a candidate. Other triples are grouped by edge instance, and this is
   where supersede/contradict **structure** is set (but no status yet): time-ordered assertions of one
   instance become a pending-newer pair; same-instant conflicts become a flagged, cross-linked
   contradiction; indistinguishable ones become an HITL candidate. Place refs adopt a curated anchor's
   coordinate when the node has none, keep the finer of two precisions, and get an uncertainty radius
   from `places.proximity_radius_m`.

3. **Score claims** — per-claim credibility (reliability × integrity × freshness). This is also where the
   `flag_origin` HITL channel bites: an analyst's coordinated-inauthenticity flag taints every claim
   sharing that origin, including claims ingested *after* the flag was raised.

4. **Per-element assertion inputs.** For each node/edge/event: independence groups, a freshness summary
   with aging/stale flags, and the deception gates — `adversary-denial` (any supporting source carries
   the denial flag), `decoy-risk` (only when the element is a lone look, i.e. weighted looks fall below
   `min_independent_groups`, default 2), `gated-attr-unknown` (a `foreign_control`/`readiness` attribute
   literally "UNKNOWN"), and `contradiction`. Crucially, **sufficiency is checked here, before status**,
   so the confirmed gate can require it.

5. **Assign status** (batch) reads sufficiency plus the gate flags and emits confirmed / probable /
   possible / insufficient / contradicted / stale against the shipped cutoffs (confirmed ≥ 0.80,
   probable ≥ 0.50).

6. **Attach** status, the confidence breakdown (assertion confidence being a noisy-OR across independence
   groups), freshness, and sufficiency; and emit a first-class known-gap for every element whose
   sufficiency is unsatisfied.

6b. **Supersession floor.** This runs *here*, after status, precisely because the floor is a question
   about the *newer* edge's confidence — which did not exist at assembly time. A pending-newer pair is
   actually retired (older edge re-run as stale, a visible `supersedes` edge drawn, its stale known-gap
   dropped as "history, not a coverage gap") only if the newer edge clears every floor condition: minimum
   band probable, at least one weighted look, a live status, and none of the blocking gates
   (adversary-denial, decoy-risk, contradiction). **If no `supersede_floor` is configured it fails closed
   and retires nothing** — a missing config key silently disables the entire relocation beat.

7. **Materiality precompute** (below).

8. **HITL decision effects last.** `set_status` overrides the machine's label and `add_integrity_flag`
   appends a flag. This is dead last on purpose (gate G12): the human override must win over whatever the
   machine just computed. A `set_status` applied *before* scoring would simply be overwritten.

8b. **Resolution edges.** Undecided same-as candidates and distinct-from vetoes are drawn *after*
   scoring and are never assigned a truth status — they cite a merge decision, not a claim.

9. **Sort + meta** — deterministic ordering by id, and a meta block carrying the config version and
   counts.

The load-bearing observation for someone tuning this: **human overrides are not one late injection point
— they are five distinct effect keys spread across the pipeline at the stage each belongs to.**
`exclude_claims` enters at the very top; `merge_adjudication` inside resolution; `flag_origin` inside
scoring; `set_status` and `add_integrity_flag` dead last. Of these, only `set_status` reliably fires on
the running app — the merge-adjudication writeback shape does not match what the resolver's replay reader
expects, so an accepted merge from the live `/hitl/merge` endpoint records an audit entry but grows no
alias. That is a real, silent no-op on the highest-value control point.

### Materiality: computed once, subject-agnostic

Materiality is stage 7 — *not* the final stage, despite a docstring that reads that way. It runs a pure
graph computation over the whole graph, unconditionally, regardless of any subject. It tags each node
with a chokepoint verdict by walking six hardcoded sustainment edge types, counting sole-source
dependencies *per function slot* (edge type plus the supplier's `functional_role`, so one radar + one
launcher count as two single points of failure, not one node of in-degree two), and deciding a
three-state verdict: a real alternate → not a chokepoint; explicit `known-sole-source` or an
evidence-backed `foreign_control` → confirmed; otherwise candidate. An all-inferred nomination (every
supporting edge only "possible") is capped at candidate. Each candidate also emits its own known-gap, so
"we don't know if this is a single point of failure" becomes a surfaced, citable admission rather than a
silent omission — which is why the boot's 19 gaps are a mix of sufficiency failures (stage 6) and these
chokepoint candidates.

Because precompute runs at stage 7 and HITL effects at stage 8, **a human `set_status` on an edge can
never change a chokepoint verdict** — precompute has already read that edge's status before the override
lands. The only human lever that reaches materiality is excluding a claim, at the very top. Materiality
is consumed by the answer-assembly text and as a *filter* in the `graph_analyze` supply-chain analysis (chokepoint_status ≠
"none"), but not as a *ranking* input, and it feeds nothing in credibility or freshness. Its own claim
to be config-overridable via a `config.materiality` surface is not wired — no such config section exists — so
it always uses the hardcoded edge list (which happens to match the shipped ontology).

### What a lens does, and what the export carries

A subject lens is a **query-time** transform, applied per request on `GET /view?subject=` and inside
ASK — never in `rebuild()`. It resolves each configured anchor string to a real node id through the same
resolver ladder, takes everything within `max_hops` (default 3, undirected) of any resolved anchor, then
intersects with a materiality filter — but resolved anchors are always kept, and type-indeterminate
`unknown` nodes survive when `never_drop_indeterminate` is set. Edges survive only if both endpoints do;
events if any participant does; gaps and alerts follow their node. An all-miss anchor set returns a
*diagnosed* empty view, never a bare one. Two shipped filter keys, `exclude_off_subject` and
`materiality_attrs`, are declared in config but deliberately unimplemented, so the lens's real chaff
protection is the type allow-list alone. At default boot the flagship lens loses one anchor —
`site_rahwali` is absent from the graph in this config, so the lens reports it under `anchors_missing`
and runs on the single resolved anchor `unit_paad` (160 → 27 nodes / 44 edges / 7 gaps); with the full
corpus both anchors resolve (169 → 30 / 52 / 8).

Each exported node carries its id, refined type, per-type attributes (including place-match band,
distance, uncertainty radius and location source), a per-attribute value **history** (`attr_history`: for
each claim-asserted attribute, the full time-ordered series of every value any claim asserted for it — the
entity's own value-timeline, retained *alongside* the first-claim-wins scalar so a later or conflicting
value is simply another entry and nothing is hidden), a `Location`, the `materiality` block, and the shared
assessment block: cited claim ids, status, the full confidence breakdown (per-claim credibility,
integrity flags, independence groups, freshness factor, noisy-OR assertion confidence), freshness,
grouped supporting claims, opposing claims, and sufficiency. Edges add their edge instance, the
`superseded_by`/`supersedes` links, a `time_interval` (the edge's validity window, derived from its
supporting claims' event times; `None` when nothing is dated), and — for same-as candidates only — a
`merge_confidence` that is about identity, never truth. The view also holds events (never merged — each
event claim becomes its own event, unlike entities and edges), the first-class known-gaps, and an alert
feed filled by the monitoring evaluator, not by rebuild.


---

## The human in the loop: adjudication as a service

The HITL layer is designed as one cross-cutting service that every stage calls the same way: build a review card, let a human pick a verb, append the decision to an immutable log, and let the next rebuild replay it into graph state. That is the intent, and the envelope really is uniform. But in the running app, almost none of the service is reachable, and of the three control points advertised as "wired deep," only one actually changes the graph. This chapter is mostly about that gap — where a human decision becomes real state, and where it becomes an audit entry that nothing downstream ever reads.

### One adjudication function is live; the rest is a callable library

The service exposes two entry points. `enqueue` is the full design — it runs the escalate-vs-auto gate, parks escalated items on a queue, and can auto-dispose safe items. `dispose` is the bare analyst path: validate the chosen verb, append one decision record, done. **Only `dispose` is ever called by the running system.** The API funnels three endpoints — `/hitl/status`, `/hitl/alert`, `/hitl/merge` — straight into it. `enqueue`, the `ReviewQueue` container, `should_escalate`, `order_queue`, `TriageConfig`, the `STAR_TYPES` constant, and the entire eight-entry `CONTROL_POINTS` catalogue have no caller outside their own unit tests. The queue, the triage gate, and the recall-biased escalation are library capabilities, not live behaviour.

The three live endpoints share one discipline, followed everywhere with no exception:

1. Rebuild the review card *from current view state* — there is no server-side pending worklist to go stale; the card is reconstructed fresh on each request from the target element's current status (status), the newest matching fired alert (alert), or a candidate same-as edge (merge).
2. Check the chosen verb is one of that card's offered options — an unknown verb is a hard 400, never silently accepted.
3. Call `dispose`, which appends exactly **one** decision record to the append-only log and returns.
4. Call `rebuild_and_swap()`, which re-runs the full `rebuild()` over the now-longer logs under a lock and atomically swaps the held view, so the endpoint returns the propagated result in a single round-trip.

The load-bearing property is real: **HITL never mutates the view.** It only appends to the decision log (a SQLite append-only store whose `BEFORE UPDATE`/`BEFORE DELETE` triggers `RAISE(ABORT)`), and rebuild replays the whole log every time. One caveat that matters for a reviewer: that decision log is an in-memory `:memory:` database newed up blank on every process boot and never seeded from any baseline. Decisions survive every rebuild within a session — they *are* rebuild's input — but a container restart discards them entirely and returns to the committed-bundle graph.

### The eight control points and their honest depth

The catalogue names eight places a human could take the wheel. Their actual state:

| Control point | Advertised depth | Reality in the running app |
|---|---|---|
| status-override | wired-deep ★ | **Genuinely propagates** — the only one that changes the graph |
| merge | wired-deep ★ | **Genuinely propagates** — accept grows the alias table, reject/split write a durable veto; both replay into the resolver on the next rebuild |
| alert-disposition | wired-deep ★ | **Not wired** — effect unread, and its only reader has no caller |
| integrity-flag | built | Rebuild-side consumers are real, but **no HTTP route produces it** |
| credibility-config | config | Read-only levers; the client-side rubric never writes back |
| observable-definition | config | Config-authored, not a HITL card |
| ontology-extension | roadmap | Named, typed, not built |
| assessment-review | roadmap | Named, typed, not built |

So the honest count is: two control points that work end-to-end (status-override and merge), one that is cosmetic (alert-disposition — its effect is unread), one that is wired downstream but has no door to reach it (integrity-flag), and four that are config or roadmap.

### How an item reaches the analyst — and how it is meant to be triaged

On the request path there is no triage at all: the analyst POSTs a decision and it disposes directly. The escalate-vs-auto gate exists only in `should_escalate`, and it is deterministic and recall-biased by construction — an item auto-proceeds only if it is *provably* safe on every axis: confidence ≥ 0.85 **and** materiality < 0.5 **and** novelty < 0.5, with any missing value (a `None`) treated as unsafe so it escalates. When in doubt, escalate. This is exactly the "keep a human in the loop" logic the brief demands — and it is never invoked, because `enqueue` (its only caller) is never invoked.

Queue ordering (`order_queue`) is likewise built but not wired. It pins ★ items to the top by a fixed `star_priority` (status-override = 0, merge = 1, alert-disposition = 2, then item id), then applies a raise-only `frozen_rank` that structurally cannot drop, inject, or unpin an item, then falls back to insertion order. It is never called live, and `frozen_rank` is never supplied by anything.

What actually orders the queue in the shipped app is the **frontend**. There is no review-queue GET endpoint by design; the client scans the rebuilt view for three patterns — same-as edges (merges), elements carrying opposing claims or a contradicted status (overrides), and undispositioned alerts (tripwire firings) — and orders them by the same star-priority, then materiality (touches a chokepoint), then confidence, where an *unknown* confidence sorts as more urgent, never safer. So "recall-biased triage" and "★ pinned to the top" are real in the running app, but they live in the browser, re-derived every render, and the backend's own triage module is not what enforces them.

### The verbs and the status ladder

Each card offers a fixed verb set: merge → accept / reject / split; status → promote / demote / reject; alert → real / noise / needs-more; integrity → flag. For status, the promote and demote targets are computed from the element's *current* status along a one-step ladder in the route — promote walks possible → probable → confirmed (top fixed), demote walks confirmed → probable → possible (floor fixed). The decision record's effect is copied verbatim from the option the analyst was shown, and its event id is derived deterministically as `dec:<item_id>:<chosen>` with no RNG and no clock, so replay is byte-identical.

Note one designed-in shortcut: **reject is a forced demote.** For status it emits the same `set_status → demote_to` as demote; the intended richer behaviour — drop the underlying claim upstream of scoring so the machine re-derives the verdict from fewer independent looks — was deferred. Rebuild does contain that honest mechanism (an `exclude_claims` effect read at the very top of the pipeline, before scoring), but **no card ever emits `exclude_claims`.** No HITL path reaches that branch. Reject is a relabel, not a re-derivation.

### What actually changes on a decision — per channel

This is the crux. Rebuild spreads decision effects across five different stages, not one late override point, and only some of the channels have a matching reader.

**status-override — works, but it is a leaf-stamp, not a cascade.** The chosen verb maps to `set_status = {element_id: status}`. Rebuild applies this dead last (step 8, `apply_decision_effects`), after resolution, scoring, sufficiency, the status machine, the supersession floor, and materiality precompute — deliberately last, so the human override beats the machine. It walks all decision records in log order and writes `el.status`, indexing nodes, edges, and events alike, so any element type can be overridden. This is genuinely wired and tested. But because it runs *after* everything else and only stamps the one named element, it does not re-run the status machine, does not re-point materiality, does not re-assess incident edges, and does not touch the element's own confidence breakdown, sufficiency, or Known Gap. An element that failed its evidence-sufficiency template still emits an "insufficient evidence" gap at step 6; an override to confirmed at step 8 leaves that gap sitting there — the element can simultaneously read "confirmed" and carry a live insufficiency gap. Propagation is real only for consumers that read *that element's status field* (the confirmed-answer list, the ASK agent's view, the frontend badge).

**merge — now genuinely propagates.** This is the highest-value control point per the design, and on an earlier build it was silently severed: the HITL writeback wrote its verdict under `decision.chosen` and nested the entity pair under `effects.grow_alias`, while resolution's alias replayer looked for the pair under `decision.pair`/`context` and the verdict under `decision.verdict` — none of those keys existed in what the writeback produced, so every live merge record was skipped (accept grew no alias, reject recorded no distinct-from). Two things drifted at once: the key names, and the fact that the alias index is *name*-keyed while the route shipped candidates with ids but no names, so even the right key wouldn't have matched. Both are fixed on this branch (commit `e868ae3`). The merge card now writes structured per-verb effects — `grow_alias` (accept), `record_distinct` (reject), `split_merge` (split), each carrying the pair's **names** — and the route threads node names into the candidates. Resolution's alias builder replays every `merge_adjudication` record through a reader that consumes exactly those keys (names first): an accept calls `link(a, b)` and grows the alias equivalence class, so the same pair auto-resolves on the next rebuild; a reject/split calls `distinct.add`, a durable do-not-merge veto the resolver honours transitively. Live consequence: the analyst accepts a same-as, the next rebuild merges the two nodes into one and the card does not come back; a reject splits them and keeps them apart. The loop is covered by a test that drives the real producer → writeback → replay path, not a hand-shaped fixture.

**alert-disposition — not wired.** Its effect `tune_tripwire` is read nowhere. There is a would-be reader in the observe module, but (a) it has no live caller anywhere, and (b) even if called it reads the verdict from `decision.disposition` / `decision.verdict` — again a mismatch with the writeback's `decision.chosen` — so it returns nothing and drops the record. The only visible effect is a deliberate side exception: the `/hitl/alert` route stamps `disposition` directly onto the in-memory alert object so the UI shows it resolved. That flag is not derived from the log and does not survive a rebuild-from-log — the one place in the whole system where state is not reconstructable by replaying the two logs.

**integrity-flag — the one genuinely origin-wide effect, with no endpoint to reach it.** Its two effects both have real readers. `add_integrity_flag` unions a display label onto the element at step 8 (after the machine, so it is display-only and does not cap status). `flag_origin` is the real one: `score_claims` at step 3 reads it and penalizes the credibility of *every* claim whose source shares the flagged `primary_origin_id`, including claims ingested after the flag — genuinely propagating into per-claim credibility → confidence → status, origin-wide. The penalty is concrete: the effect carries no `flag` field, so the reader defaults to "suspected" and multiplies matching claims by the credibility config's `coordinated_inauthenticity.suspected = 0.5`. **But there is no `/hitl/integrity` endpoint** and nothing else calls the integrity card builder, so an analyst cannot raise this flag in the running app at all. It is correctly wired downstream and completely unreachable upstream — exercisable only from a direct test harness. On the shipped corpus it would also be near-inert: the origins it would match already carry the coordinated-inauthenticity flag and are penalized at 0.5 anyway.

### Reversal

Reversal is always a new appended record, never an edit or delete of the prior one. For status it works cleanly: `apply_decision_effects` applies each `set_status` in log order, so last-write-wins — a later promote overrides an earlier demote on the same element, deterministically. For merge, reversal now works the same way — appended, never edited: a later `record_distinct` veto overrides an earlier `grow_alias` link (a hard do-not-merge always wins over a soft alias-grow), so an analyst who accepts then rejects a pair ends with them separate, deterministically on replay. For integrity, there is **no reversal path at all**: the flag effect only *unions* a label in, there is no remove-flag effect, and the card offers only "flag" — so once an origin flag is somehow appended, no later append can undo it.

### The knobs

| Knob | Default | Actually read live? |
|---|---|---|
| `auto_proceed_min_confidence` | 0.85 | No — only `should_escalate` reads it, never called |
| `material_threshold` / `novelty_threshold` | 0.5 / 0.5 | No — same |
| `gate_on_materiality` / `gate_on_novelty` | true / true | No — same |
| `star_priority` | status-override 0, merge 1, alert 2 | Backend copy dead; the frontend mirrors these numbers |
| `STAR_TYPES` | merge / status-override / alert-disposition | Not wired — defined, re-exported, referenced nowhere |
| `frozen_rank` | (none supplied) | No — never passed |
| status ladder (`_PROMOTE`/`_DEMOTE`) | possible↔probable↔confirmed | Yes — used to compute card targets |
| `coordinated_inauthenticity.suspected` | 0.5 | Yes — but only via the unreachable integrity flag |
| decision log path | `:memory:` | Yes — empty each boot, cleared on restart |

The through-line: the adjudication *envelope* is genuinely uniform and the append-only discipline is genuinely honoured, so status-override is a clean demonstration that a human decision survives rebuild by being replayed rather than by mutating state. Everything richer around it — the triage gate, the prioritised queue, the auto-disposition branch, and one of the three ★ control points (alert-disposition) — still has no live caller or reader. (Merge, the decision-record shape mismatch this chapter once flagged, is fixed on this branch: an accept now grows the alias table and a reject writes a durable veto, both replayed by the resolver.)


---

## Monitoring: observables, tripwires, and adaptation

### What makes this a monitor rather than a one-shot

The monitoring behaviour is an emergent property of two facts about the rebuild loop, not a
subsystem that runs on its own clock. First, every write path — ingesting a document, an analyst
HITL decision, a config edit — funnels through one serialized critical section (`rebuild_and_swap`)
that replays the *entire* evidence log from scratch into a fresh graph view, then immediately diffs
the previous view against the new one and fires tripwires on the delta. Second, there is **no
scheduler anywhere in the backend** — no timer, no cron, no background poll that re-triages a quiet
graph. Observables fire strictly *on rebuild*, and a rebuild happens only because someone wrote
something. The consequence is worth stating plainly: a graph left completely untouched — for a day
or for a year — never re-evaluates itself and never emits an alert. "Monitoring" here means "detect
what changed the last time evidence arrived," plus a freshness model (below) that ages claims
relative to a moving reference date rather than to the wall clock.

Cold boot fires nothing: when there is no previous view, the just-seeded baseline is the reference
point, so the initial graph is never treated as a wave of changes. The evaluator itself touches no
clock, no RNG, no network, and no LLM — it is a pure diff — so firing is fully deterministic. The
only wall-clock read in the whole loop is the `fired_ts` the API stamps on an alert at persist time.

### The observable language and what it can actually express

A tripwire is a declarative condition over attributes that *already exist* on a graph element — raw
node/edge fields, the materiality metrics the scorer precomputes, or a `location` — reached by
dotted-path traversal. A field that isn't there yields a distinct `MISSING` sentinel, deliberately
separate from a stored `None`, so "we looked and it was absent" is never confused with "it was
explicitly null." There are exactly **eight operators**: `eq`, `ne`, `lt`, `le`, `gt`, `ge`,
`exists`, `not_exists`. The four numeric ones coerce both sides to float and refuse to fire on
non-numbers, bools, `None`, or `MISSING` — an unknown value never satisfies a threshold. `eq`/`ne`
treat `MISSING` as not-satisfied; only `exists`/`not_exists` report absence honestly. An unrecognised
operator name **raises** rather than silently passing. One extra primitive, `within_area`, does an
offline great-circle distance check against a `{center, radius_km}` — the geofence seam.

Named triggers are sugar over four firing modes; the compiler maps a trigger's `on:` key to one of them:

| `on:` value | mode | fires when |
|---|---|---|
| `occupancy_state_change`, `state_change`, `geofence_crossing` | CROSSING | a tracked state's value changes between the prior active element and the new one |
| `new_edge`, `new_node` | EXISTS | a grouping key appears in the new view but not the old |
| an operator name (`eq`, `ge`, …) | MATCH | a predicate becomes newly true (held false on the prior element) |
| **anything else** (notably `new_claim`) | **ARM-ONLY** | never — it parses and arms but cannot fire from a view delta |

Two config-only seams keep this from needing per-observable code. `match_on` declares the wire's
grouping key versus its tracked state, drawn from a small fixed vocabulary (`resolved_unit` → an
edge's source, `site_instance` → its target, and so on). And `where_before` / `where_after` /
`where_change` blocks attach arbitrary DSL conditions to the prior state, the new state, or the
delta. Because the config model is permissive (`extra="allow"`, required for hot editing), a typo or
an aspirational key can't be schema-rejected — instead any trigger key the compiler didn't read is
collected as `unconsumed` and surfaced, so a dead key is made visible rather than silently ignored.

The CROSSING detector deserves one detail because the flagship depends on it. For a functional edge
like `based-at`, the compiler groups by the *unit* and treats the *site* as the tracked state
(excluded from the grouping key), so a unit's old and new basing edges land in one group. It picks
the **active** edge per group — the one not superseded, tie-broken toward the one that supersedes
something — and fires only when both the prior and new states are *known* and *differ*. A first
appearance is not a crossing; that is what `new_edge` is for.

### The alert lifecycle

There is no new/acknowledged/suppressed/expired state machine. An alert has exactly two states:

| state | how it's reached | what it does |
|---|---|---|
| fired | evaluator emits it; `disposition` is null | appended to a session feed, attached to the served view |
| dispositioned | analyst posts `real` / `noise` / `needs-more` | sets `disposition` on the feed item, appends an `alert_disposition` record |

That is the whole lifecycle. There is no acknowledge, no suppression, no TTL, no auto-close, and
**no dedup across the session** — the guard against re-firing is only that prior and new states must
differ *within a single diff*, so a state that oscillates A→B→A over successive ingests will emit a
fresh alert each time and the feed grows unbounded (and is memory-only; a restart loses it). The
disposition endpoint has a further sharp edge: it marks only the *most recent* matching alert,
scanning the feed in reverse for the observable id. If a tripwire fired several times, the earlier
firings keep a null disposition forever. And the disposition has **no graph effect** — the record it
writes carries a `tune_tripwire` effect, but rebuild reads only status overrides, integrity flags,
claim exclusions, origin flags, and merge adjudications; `tune_tripwire` is never read. Each alert
also carries a `severity` (default `notify`) that is copied onto the object and **never branched on
anywhere** — there is no escalate-versus-notify routing — and the before/after claim ids plus their
de-duplicated union, which is the one-click-to-evidence target.

### Defining a new observable live

An analyst arms a tripwire by writing the whole `observables` section through the config route.
Nothing is written back to disk — the edit lives only in process memory and reverts on restart — but
the new tripwire takes effect immediately. On save, a back-scan (`arm`) evaluates the newly-added
observable against the *current* view using an empty graph as the "previous," so an EXISTS or MATCH
wire lights up at once if something already trips it; CROSSING and ARM-ONLY wires arm silently. The
subsequent rebuild's diff then sees the same keys in old and new, so the two passes don't
double-count. Two honesty gaps sit here. The arm back-scan appends its matches straight to the feed
and writes *no* decision record — not even the `alert_fired` type that exists in the schema — so
nothing downstream can ever count that it fired. And the plain-English front door — the `explain()`
"here's what this will do and why it can't fire" screen, and the natural-language proposer that
drafts an observable from a sentence like "watch this unit for relocations" — **is not reachable in
the running app**. The proposer exists and is tested, but no API route invokes it, and it is the only
live caller of `explain()`. In the served surface, arming an observable is a raw section write with no
confirm-and-explain step.

### Repeat and contradicting evidence

Re-posting the identical bundle is effectively idempotent. Duplicate rows are inserted (the log has
no unique key), but independence grouping collapses the copies to one look, group confidence is a
`max` not a sum, and cross-group pooling is noisy-OR — so corroboration cannot inflate and status
cannot flip. No second alert fires, because no state changed. Contradicting evidence is the
interesting path: a claim asserting a *different* target on the same edge instance is ordered against
the incumbent by event-time interval, and a strictly-older incumbent is nominated for supersession.
The newer claim must then clear a quality **floor** — reach at least *probable*, on at least one
weighted look, with a live status and a clean deception gate (no adversary-denial, decoy-risk, or
contradiction flag). Only then are the supersede links written, the old edge re-run as *stale*, and
the new edge made active — at which point the tripwire reads the now-active edge and fires the
crossing. If the floor is not cleared, nothing is retired and the pair waits for the analyst. This is
the designed defence against a lone low-grade adversary post silently retiring a confirmed position.

### Freshness and coverage decay — the time-driven half of adaptation

Freshness multiplies into per-claim credibility as `2^(−age/half_life)`, so credibility exactly halves
at one half-life. A `stale` gate demotes a confirmed assertion when its *freshest* supporting look has
aged past one half-life; a separate `aging` gate merely blocks confirmation when *any* look has. The
half-life is resolved by a three-rung fallback — a variant-qualified key, then a bare edge key, then
the edge's freshness-*class* default (`perishable` 540 days, `semi-durable` 540, `force-revalidated`
1825, `durable`/`n/a` no decay). The honest reality: **no claim is ever tagged with a freshness
variant and the load-bearing edges have no bare key**, so every variant-specific number in the config
(including the 30-day "field occupancy" rate one might expect to punish a stale field deployment) is
unreachable at runtime — `based-at`, `observed-at`, and `replenishes` all fall through to the perishable class
default of 540 days. Only two half-lives are actually live: 540 and 1825.

The single most important fact about time here is that the reference "now" is resolved **without the
wall clock**. It is the pinned `as_of` in config if set (shipped as null), otherwise the newest claim
date in the log. Despite a docstring claiming the API stamps today's date at request time, no code
does. So time advances in exactly two ways: a newer-dated claim arrives and pushes the reference
forward (aging everything older relative to it), or an operator edits `as_of` and rebuilds — the
"advance the clock" demo lever. Nothing goes stale by real time passing. On the client, only the armed-
observables catalogue polls (every 30 s, to keep the "Watching" count live against hot edits) and
`/health` (15 s); the view itself is fetched once and re-fetched only after a mutation. Both are pure
reads that never rebuild.

### Honest assessment: what actually fires, and what the learning loop does not do

Three observables ship, and only one can fire on the frozen corpus:

- **`obs-basing-relocation`** (CROSSING on `based-at`, watching the HQ-9 battalion, scope pinned to
  zero hops so a neighbour's address change can't trip it) — **fires**. The two Rahwali documents are
  withheld from the boot seed; ingesting them moves the unit's active basing edge and the crossing
  fires. This is the one live monitoring beat.
- **`obs-followon-interceptor-order`** (EXISTS on a `replenishes` edge) — **inert on the shipped
  scenario**. The edge type is declared and a keyed ingest of a resupply document could in principle
  produce one, but no frozen bundle and neither withheld doc contains a `replenishes` edge, so there
  is nothing to fire on.
- **`obs-spares-tender-probable-induction`** (`on: new_claim`) — **inert by design**: it compiles to
  ARM-ONLY and structurally cannot fire from a view delta, because claims live in the evidence log,
  not the rebuilt view. Its `source_class`, `implies_edge`, and `target_status_ceiling` keys are all
  surfaced as unconsumed and have no effect.

The geofence machinery — the `within_area` primitive, geofence compilation, area scoping — is a built
and tested seam with **no shipped consumer**, and even where scope-area filtering exists it only
filters node candidates; edge candidates ignore it entirely. And the adaptation "learning loop" is,
as shipped, **not wired end to end**. The consumer that would compute which tripwires over-fire
(`read_dispositions`, the per-observable stats, the noise-rate signal) has **no caller** outside
tests. In addition, the stat that would count how often a wire fired reads `alert_fired` decision records,
and **nothing anywhere writes one** — not the evaluator, not the arm back-scan — so that count would
be zero even if the loop were wired. The only records actually written are `alert_disposition`s from
the HITL alert route, and those feed no automatic retune: tightening a noisy tripwire is a manual hot-
config edit that no code prompts for and no signal is surfaced to justify. The round-trip is proven in
a unit test; it is not present in the running app.


---

## Refusal: how the system declines to assess

Refusal is decided in two places that never talk to each other directly. The **rebuild** stamps a
structural `insufficient` status and mints first-class Known-Gap nodes; it runs with no LLM and no wall
clock, so its verdicts are reproducible. The **query-time agent** turns a gap into the prose an analyst
actually reads, and adds its own three kinds of refusal on top. Understanding the guarantee means
tracing every path into each layer and asking, for each, whether it can fire with shipped defaults on
the frozen corpus.

### Path 1 — template-driven insufficiency, decided in the rebuild

The sufficiency checker runs once per graph element (every node, edge, and event) as step 6 of the
rebuild. Its logic is deliberately *not* a confidence check: it asks whether the **kind** of evidence an
assertion's type demands is present, independent of how strong the evidence is. A fully corroborated
claim can be ruled insufficient here for lacking imagery; a thinly sourced one passes if it happens to
carry the right kind.

The decision proceeds in a fixed order. First it identifies the assertion's type by walking the
supporting claims and taking the first one carrying a predicate, event type, or entity type. That string
is looked up in the template map. **If there is no template for that type, the element is declared
assessable with no further checks — and this is the dominant outcome.** Only seven types have templates,
and only three of those (`based-at`, `inducted-into`, `supplies-component`) are real edge predicates that
ever match a live claim. Every node type, every event, and every other edge falls straight through to
`satisfied=True`. The entire "insufficient evidence" machine keys off three edge predicates.

For the three that do match, the require-DSL is evaluated:

- **`based-at`** — `any_of`: recent satellite imagery within 365 days, OR at least two independent text
  groups within 365 days.
- **`inducted-into`** — `all_of`: an official-source announcement AND at least one independent origin
  group within 1825 days.
- **`supplies-component`** — `any_of`: a customs-tender source naming it, OR at least two independent
  origin groups.

Per-slot detection is literal: imagery means a supporting claim from a satellite source inside the
window; official-announcement means any claim from an official source; sanction/tender means a
customs-tender source; the group slots count *independence groups* (not raw claims) with at least one
claim in the window, the text variant excluding satellite-origin groups. Any unrecognised slot name
**fails closed** — an unknown requirement is treated as an unmet gap, never assumed satisfied.

When a slot is unsatisfied, the checker generates the two things the analyst is owed. `missing_slots`
is the set of unmet slots (for `all_of`, every unmet slot; for `any_of`, all slots when none pass).
`next_coverage_due` is *never authored anywhere* — it is computed by looking up which source classes can
supply each missing slot, gathering every registered source of those classes, reading each one's
`cadence`, and taking the earliest revisit as `as_of + min(cadence in days)`. Only numeric `"<N>d"`
cadences count; `event-driven`, `continuous`, `irregular`, and `per-tender` yield no schedule, and if no
provider has a numeric cadence the date is `None` — an untasked gap, stated as such. The evaluation
"now" is the pinned `credibility.as_of` if set, else the newest claim date in scope; the shipped config
pins nothing, so `as_of` is the latest claim date, which keeps both the recency windows and the coverage
date data-driven.

The pipeline then mints a `KnownGap` node (`gap:<element_id>`) whose `what_missing` is the **first**
missing slot, whose ceiling is the template's `observability_ceiling` or `"confirmable"`, carrying the
computed coverage date and the full slot list. Crucially, the pipeline copies only these structured
fields — **it never reads the `refusal_template`.** The prose comes later, from the agent.

The `insufficient` label reaches the element through the status machine's precedence chain:
`superseded → insufficient → contradicted → confirmed → stale → probable → possible`. Sufficiency is
*not* a term inside the confirmed-eligibility arithmetic; it blocks confirmation purely by sitting
earlier in the if/elif chain, so an unsatisfied element short-circuits to `insufficient` before the
`confirmed` branch is ever tested. `superseded` is checked ahead of `insufficient` on purpose: a
retired-by-a-newer-fact position is history, not a gap, and telling an analyst to collect on a position
the subject has already left would be the opposite of honest. Accordingly, after the supersession floor
runs, Known Gaps whose element was retired are dropped.

The never-observable short-circuit is the other structural refusal: four template rows
(`interceptor-depth`, `contract-terms`, `c2-topology`, `true-readiness`) carry `never_observable: true`
and return unsatisfied immediately, with no coverage date and ceiling `never-observable` — a structural
limit, not a lapse. **None of the four fire on the real corpus.** No claim ever carries those strings as its
type, so the short-circuit never fires; and even if one did, the refusal-string matcher (below) keys on
slot-name intersection and these rows have no slots, so their prose is unreachable twice over.

### Path 2 — the materiality chokepoint gap

Materiality precompute emits a *second, independent* family of Known Gaps that bypasses templates
entirely. Any node classified as a candidate chokepoint (sole-source in-degree but UNKNOWN
substitutability) gets a `gap:chokepoint:<node>` with a **hardcoded** ceiling of `probable-max`, fixed
slots `["named_supplier", "substitutability"]`, and **no coverage date at all**. This is the gap the
flagship demo actually leans on.

### Path 3 — self-declared gaps from documents

Ingest can mint `known_gap`-typed graph *nodes* directly from documents that state their own collection
limits. These are ordinary nodes, not template failures, and do not touch the sufficiency path.

### Path 4 — the agent's refusals (what the analyst reads)

The `ask` entry routes **two** ways. With a model key, every question — the flagship included — runs the
bounded ReAct loop: the LLM plans and the deterministic `graph_*` tools (now including the general
`graph_analyze`) compute; no query is special-cased. With no key, `ask` returns a **capability** refusal
immediately — worded to say *no evidence was consulted*, deliberately distinct from an evidence gap so it
never overstates a shortfall in the world. When the specific subject or
site a question names does not resolve in the graph, the agent refuses and **names the missing subject**
rather than adopting a look-alike candidate — a near-match is a different entity, so answering about it
would be a fabricated premise. As shipped, the two Rahwali documents are withheld from the seed, so the
flagship query on a cold boot refuses (naming the missing site) until those documents are ingested.

Refusal prose is rendered by `_render_refusal`, reached through the `check_sufficiency` tool. It builds
the missing-slot list, substitutes the `unscheduled_coverage_phrase` (the shipped file overrides the
default "unscheduled" with a full "no collection is tasked against this gap" sentence) when there is no
date, then **iterates the templates in file order and fires the first one whose required slot names
intersect the missing set** — filling that template's blanks. This is order-sensitive and *type-agnostic*:
because `independent_origin_groups` appears in both `inducted-into` and `supplies-component`, the string
an analyst sees may come from a different template than the assertion's own. If nothing matches, a
hardcoded "Insufficient evidence to assess…" fallback is used. A comment records that this matcher was
once fully broken (string-vs-dict comparison, every template dead); it works now, with that caveat.

Every *positive* agent answer is then validated: each sentence must carry a citation resolving to a real
claim, each hop's citation must be in that hop's claim set, every count must match a count a tool
actually returned, and — if the entailment judge is enabled (opt-in, default off) and a live client is
present — the cited claims must entail the sentence. **Any
single finding withholds the entire answer** and downgrades it to a `kind="withheld"` refusal; there is
no per-sentence pruning.

### Reachability with shipped defaults on the frozen corpus

On a cold default boot, template-driven insufficiency fires on exactly **8 edges** (4 `inducted-into`,
2 `supplies-component`, 2 `based-at`) → 8 Known Gaps, plus **10 candidate-chokepoint gaps**, for **18
total**. The `supplies-component` gap carries a real generated date; the `inducted-into`
gaps come back with `next_coverage_due = None`, because no official-class source declares a numeric
cadence to schedule against. The load-bearing nuance: only **two** edges ever reach *confirmed* — both
`equips` edges (`Pakistan → var_hq9p` and `comp_ht233 → var_hq9p`); the strongest *basing* edge tops out
at *probable* (≈0.79, under the 0.80 cut and short of the two-look gate) and never confirms. **12** nodes
reach confirmed at default boot (13 on the full corpus, which adds `site_rahwali`). So the refusal
machinery is genuinely live and does most of its work through the chokepoint family, while template
refusals cluster on those eight edges.

### The adversarial half — how a confident assertion can still escape thin

Several cracks exist, and they are real:

- **The free-form ReAct path has no assertable-status gate; only the `graph_analyze` supply-chain analysis does.** That analysis filters
  its carried supplier links to the configurable `assertable_status` band (`[confirmed, probable]`, and
  empty/absent fails closed to a refusal) and prints what it weighed and rejected — this is how the
  planted false CPMIEC→HT-233 attribution is surfaced rather than dropped. The free loop walks whatever
  `find_paths` returns, and that is a plain shortest-path BFS that records each hop's status but never
  filters on it. Since no edge is ever confirmed, every free-loop multi-hop answer necessarily rests on
  probable/possible/insufficient edges with no floor.
- **The `query_graph` answer shape drops the confidence qualifier.** The tool result carries a per-match
  status, but the builder renders matched nodes as flat "X matches the criteria [cites]" with no status
  label — unlike the path/neighbour/node builders, which print "— <status>" inline. Driven directly, the
  chokepoint query returns six candidate components rendered as flat cited matches, one of which
  (`comp_ht233`) carries the planted false-attribution document among its refs. Backing is real and
  attached; the *signalling* is lost for that one shape.
- **The frontend under-signals confidence.** The structured hop walk shows only observed/inferred; the
  trailing "Sources" chip row is hardcoded to `confirmed` for every citation; and the `statusBorder`
  default arm falls through to *probable*, so a null/garbage status paints as a live assertion rather
  than a gap. Latent, but wrong-safe.
- **Sufficiency fails open on dates.** An undated claim is never excluded by a `within_days` window, and
  a missing `as_of` disables windows entirely — so a single undated satellite image satisfies
  `imagery_confirmation` (relevant to the recycled-image trap). This is defanged for *confirmed* by the
  separate integrity gates that pull the number down, but sufficiency alone would report the requirement
  met.
- **The HITL override is the one place a refusal becomes an assertion by decision.** An analyst can
  `set_status` to flip an `insufficient` edge to `confirmed`; the override writes status with **no
  on-element marker**, and no route exposes the decision record in the drawer — so a human-set confirmed
  is indistinguishable from a machine confirmed, and its underlying confidence may sit below 0.80.

Finally, some config to name that reads as live but is not: `cross_interest: true` on the `inducted-into` origin slot is
read by nothing; `on_fail` is validated on every template but read by nothing (the insufficient routing
is hardwired to the boolean); and the four never-observable templates never fire. What is *not* a hole:
the assembled prose is deterministic and cannot be fabricated by the model, refusals are dual-guarded
(a payload OR a null answer), and UNKNOWN is never counted as a negative in `query_graph` or observables.


---

## Answering questions: the bounded agent and its citation contract

The load-bearing invariant of this whole subsystem, and the reason it is built the way it is: **the model
only plans; eight deterministic tools do every count, filter, path-walk, materiality lookup, and multi-hop
analysis; and the answer prose is re-derived from the tool results, not from the model's own words.** Citations are a
by-product of that computation. The model's final text is recorded and then thrown away. Everything below
is downstream of that one commitment.

### From HTTP to a decision about how to answer

A question arrives at `/ask`. The route snapshots config, grabs the current rebuilt view, optionally
applies a subject lens (404 if the lens id is unknown), and calls the agent entry point with the question,
the view, the config, and a `claim_id → record` map. That map matters: the served view references claims by
id only, but the agent needs the bodies — source, date, span, and the `kind` field that decides
observed-vs-inferred — so the route replays the evidence log to hand them over. The route adds no reasoning
of its own; it forwards the agent's output verbatim. The request may also carry a `history` field — a list
of prior `{question, answer}` turns — which the route passes through untouched; the ReAct loop seeds them
as prior user/assistant message pairs *before* the current question, so a follow-up ("and where is *that*
based?") resolves against the running thread. The backend stays fully stateless: the client owns the
transcript and re-sends it on every call, nothing is stored server-side, and a refused prior turn is
carried in-context as an explicit marker ("[The previous question could not be answered — insufficient
evidence in the graph.]") rather than a fabricated answer. With `history` empty or omitted the message list
is exactly the single question — the single-shot path is byte-for-byte unchanged. (One honest gap: `/ask`
has no readiness guard, so a call that lands before boot finishes raises and returns a 500 rather than the
honest 503 that `/health` would give.)

The agent first builds a **`ToolContext`** — an in-memory index over the already-rebuilt view: id→node,
id→edge, in/out adjacency, a name index (node names plus attribute aliases plus the config alias-table
equivalence classes), a source registry, the ontology's edge-lane index, the traversable-edge set, display
names, and a **single BM25 index built once** over every searchable surface. This object is pure — no LLM,
no network, no clock — which is what makes every tool result, and therefore every citation, byte-stable
across runs.

Then it resolves an LLM client and routes the question **two** ways:
- **A client resolved (key present) → the bounded ReAct loop.** No query is special-cased — the flagship
  trace is planned by the model like any other.
- **No client (keyless) → an immediate capability refusal** that says explicitly *no evidence was
  consulted* — a capability outage, not an evidence gap.

No query is special-cased: the same ReAct loop serves every keyed question, the flagship included. Client
resolution returns a live Anthropic client **only** if `ANTHROPIC_API_KEY` is set, else nothing. Two limits
are worth stating: there is **no Gemini client class in the agent** (a Gemini-only environment resolves to
nothing and falls to the capability refusal), and the recorded-transcript replay is **not wired into the
default boot path** — `ScriptedClient` exists and `build_default_client(recorded_trace=…)` can return it,
but `ask()` calls `build_default_client()` with no argument, so a keyless boot yields the honest capability
refusal, never a canned answer.

### The eight tools and what they actually return

Every tool returns its matches **with the claim ids that back them**, and every tool that takes an id
raises a lookup error on an unknown id rather than inventing a verdict about a phantom node. Counts,
filters and paths live here, never in the model.

| Tool | What it computes | The rule that matters |
|---|---|---|
| `find_entity` | name → ranked candidates | three tiers: exact name (score 100) → punctuation-squashed on any surface (95, `near_miss`) → blended `0.85·WRatio + 0.15·BM25`, cutoff 60, top 3 |
| `get_node` | one node's attrs + provenance + precomputed materiality | pure lookup |
| `neighbors` | typed, paginated one-hop expansion | default page size 3; stable sort by (edge type, id) |
| `find_paths` | shortest chain between two anchors | deterministic BFS, first shortest path, hop cap `min(max_hops, 4)` |
| `query_graph` | typed constraint filter (the generalist) | three-way verdict; UNKNOWN is never a negative |
| `get_evidence` | the exact claims behind a node/edge | source, date, span, per-claim credibility, corroboration set |
| `check_sufficiency` | is this scope evidenced enough? | unmet → Known Gap with missing slots + next-coverage-due + a templated refusal |
| `analyze` (`graph_analyze`) | one precomputed multi-hop analysis for a resolved subject: `supply_chain` / `chokepoint` / `sole_source` | returns status labels + names + claim ids only — never a confidence number; UNKNOWN always surfaces as a Known Gap, never a "no" |

Three of these carry the real analytical weight. **`find_entity` never auto-binds carelessly**: it binds
the top candidate only when there is exactly one candidate, the resolution is exact or near-miss, and no
`distinct-from` sibling of the winner is also in the candidate set — that last check is the planted
look-alike veto. A fuzzy (tier-3) hit is suggest-only and never binds. **`find_paths` defaults its edge
whitelist to the ontology's traversable lanes** — every declared edge minus those flagged symmetric
(same-as, distinct-from, coref, supersedes, evidenced-by, corroborates, contradicts, and a few more), so a
path is a chain of real relations and cannot shortcut through an identity or provenance edge. **`query_graph`
partitions every node into match / excluded / indeterminate**: `exists`/`not_exists` treat UNKNOWN as
absent, but any value operator against an attribute that is UNKNOWN or missing lands the node in the
*indeterminate* partition — never counted as a negative. That is the disqualifying line, mechanised. Note
that `query_graph` only *reads* the materiality tags (chokepoint status, count, substitutability); those are
precomputed once per rebuild by a separate pure pass, not computed at query time.

Crucially, `run_tool` — the dispatcher the loop calls — **never raises for a tool-level problem**. A bad
name, a missing param, or a no-match becomes an `{error, suggestion}` dict that is recorded and fed back to
the planner, and a single `ok` discriminant keeps error-shaped results from ever being read as successes.

### The execution mode: the bounded ReAct loop

**The ReAct loop** (the keyed path) is a plain think→act→observe cycle bounded at **8 iterations**. Each
turn the model gets a fixed system prompt ("you are a PLANNER; every count/filter/path/materiality lookup
is a tool call; resolve entities first; on empty or indeterminate results call `check_sufficiency` and
return insufficient-evidence, never a confident negative"), the history, and the eight tool schemas. If the
model stops without a tool call, the loop ends (`end_turn`) and its text is recorded. Otherwise every
requested tool runs, each is recorded, and each result is fed back as a JSON tool-result block (keys
sorted). If 8 iterations pass with no natural stop, the loop terminates as `max_iters` — and there is **no
explicit "I ran out of steps" signal** in the payload; the answer is simply assembled from whatever partial
trace was gathered. The stop decision is entirely the model's. Its `final_text` is never read.

**The heavy multi-hop judgement is delegated to `graph_analyze`, not special-cased by query text.** When a
question needs a judgement computed across many hops — an origin/supply trace, a single-point-of-failure
scan, a sole-source split — the planner calls `graph_analyze` with the fitting analysis type and the
computation runs deterministically in Python over the indexed view (`analyses.py`), never in the model. The
flagship "trace the chokepoint" answer is one `supply_chain` call. That analysis is a
`link → gather → query → cite` walk parameterised by the resolved subject: it resolves the variant the
subject belongs to, finds the basing-site anchor by resolved node type, runs `query_graph` for a component
whose `chokepoint_status != none` (pooling matches and indeterminate), and ranks by (highest assessed node
confidence, then longest cited span, then id) — chokepoint status is a filter, not part of the ranking. It
carries a supplier link **only if the claiming edge's status is in the configured assertable band
`[confirmed, probable]`**; everything below is kept and printed as "weighed and not carried" with its status
and citation — this is how a below-threshold attribution (e.g. the planted false CPMIEC supplier claim) is
*named rather than silently dropped*. When the chain cannot be walked it degrades to a scoped refusal that
names the chokepoint, names the supplier gap, and carries the partial trace it could establish.

### Drafting the answer and attaching citations

Assembly turns the trace into an answer deterministically. An explicit refusal set on the trace (for example, an analysis that could not build its chain) wins
outright. Otherwise builders are tried in a fixed order — **analyze → paths → query_graph → neighbors →
get_node → get_evidence** — and the first that yields sentences wins. Each sentence is `text [claim_ids]`; hop wording
comes from analyst-authored `edge_phrasing` config, read in the direction the walk actually traversed
(so a hop entered at the object end reads its inverse phrasing). Confirmed-vs-probable status and
observed-vs-inferred (read structurally from each claim's `kind`) are suffixed onto every hop. An
indeterminate node renders as "INDETERMINATE … a Known Gap, not a negative." If no builder produces
sentences, the path routes to a first-class refusal — reusing any `check_sufficiency` reason if one exists,
else a generic "no supporting path or indicators."

### What the validator checks, and the block

Refusals skip validation. For a positive answer, the validator runs per sentence:

- every content sentence must carry ≥1 citation (else `uncited`);
- every cited id must exist in the claim map (else `citation_missing`);
- a hop sentence — one whose index is below the number of hops — must share a claim with that hop (else
  `not_supporting_hop`);
- any count phrase ("3 components", "2 suppliers") must be a number the tools actually returned — drawn
  from `query_graph`'s match/indeterminate counts and aggregate result, `neighbors`' total, and
  `find_paths`' hop count (else `count_mismatch`);
- and if the entailment judge is enabled (`credibility.entailment_judge_enabled`, **opt-in, default OFF**)
  *and* a live (non-scripted) client is present, the cited claims must entail the sentence (else
  `not_entailed`).

**Any single finding fails the whole answer.** The positive answer is discarded and replaced by a
`withheld` refusal listing up to five failed problems. This is a hard block — no per-sentence pruning, no
downgrade, no annotation. It is worth stating two consequences plainly. First, the entailment judge is **opt-in and off by
default**: the deterministic citation checks always run, but the LLM judge runs only when
`credibility.entailment_judge_enabled` is set and the client is live (a scripted/recorded client is a fixed
replay, never an interactive judge). This is deliberate — the judge "defaults to no if unsure," so enabling
it lets a flaky yes/no withhold an otherwise fully-sourced answer; left off, answers rest on the always-on
deterministic grounding that already forbids naked or fabricated sentences. Second, an indeterminate node
that happens to carry no claim
ids would emit an uncited sentence and thereby withhold the entire answer — a latent failure mode.

### The failure branches, honestly

- **No key (any query, flagship included):** an immediate capability refusal — nothing was consulted, so no
  evidence gap is fabricated.
- **Empty retrieval:** the builders return nothing; the refusal path emits an evidence refusal (a
  `graph_analyze` supply-chain trace that cannot complete emits a *scoped* one — chokepoint named, supplier
  a Known Gap — and carries whatever partial trace it established).
- **Validator rejection:** downgraded to `withheld`.
- **Step bound hit:** `max_iters`, answer assembled from the partial trace, with no explicit exhaustion
  signal reaching the client.
- **Tool error:** never raises; fed back to the planner as `{error, suggestion}`.

### Why agentic traversal rather than vector search

There are **no runtime embeddings anywhere in this path** — entity resolution is alias + BM25 + fuzzy, and
retrieval is a bounded walk over a typed graph driven by tool calls. The payoff is directly aligned with
the non-negotiable: because a deterministic tool performs each count, filter and hop, every number in the
answer is checkable against what a tool returned, every sentence traces to specific claim ids, and each tool result —
including the whole `graph_analyze` computation — is byte-reproducible given the view. A vector retriever would return a similarity-ranked bag of chunks
with no notion of "confirmed vs probable," no per-hop provenance, and no way to prove a count was not
hallucinated. The costs are equally real: the free ReAct loop's tool sequence is chosen by the model and so
is **not reproducible run-to-run**; there is **no total token or wall-clock budget**, only 8 turns of 16384
tokens each, so a pathological plan can burn the whole budget and still return an unusable trace; and
`find_paths` returns the *first shortest* path under a fixed BFS ordering, which can in principle pick a
semantically weaker but shorter chain. The design bets that auditability is worth those costs, and buys it
at the level of the tools rather than the route: every count, filter, hop, and the entire `graph_analyze`
computation is deterministic given the view, so once the planner selects the analysis the answer content is
byte-stable and every number is checkable against a tool result — even though the planner's tool *sequence*
is not reproducible run-to-run.


---

## The surface: API and what the analyst actually sees

### One process, one live object, one lock

The entire deployable application is a single Python process. There is no database server, no queue, no
worker pool. That process holds exactly one live in-memory state object, and every HTTP request either
reads from it or mutates it. The built frontend is served as static files off the same process at `/`, so
the app and its API are same-origin by construction. This shape is worth internalising, because it
explains almost every behaviour on the surface: "the graph" is a single Python object reference, and
"rebuild the graph" is the one operation guarded by a lock.

At boot the process seeds a config store from the nine YAML files, creates two brand-new **in-memory**
SQLite logs (one for evidence claims, one for human decisions), and tries to seed the evidence log from a
committed claim-bundle directory for the default scenario (`hq9p_primary`, overridable by an environment
variable). If no bundles are on disk it seeds zero claims and boots to an *empty* graph rather than
inventing a corpus. Any document named in the `withheld_from_seed` list is deliberately excluded from that
seed — this is the mechanism that makes the monitoring demo honest: the pre-arrival graph genuinely does
not contain the withheld evidence, so when a reviewer later posts it, the alert that fires was not hiding
in the graph all along.

Startup then runs one `rebuild()` in a background thread so the event loop keeps accepting connections. If
that first rebuild throws, the exception is swallowed and logged — the process does not crash, it simply
stays permanently un-ready, and `GET /health` reports 503 forever. Health is the only place the ready flag
is visible from outside.

### The one write discipline: append to a log, then rebuild

Every path that changes anything follows the same three steps, with essentially one exception noted below:

1. append to a log — evidence claims, or a decision record — or mutate the in-memory config bundle;
2. call the locked rebuild-and-swap, which replays the *entire* evidence-plus-decision log from scratch
   (never incrementally), diffs the fresh view against the old one to fire any observables that just
   tripped, stamps a wall-clock timestamp on each new alert, and atomically swaps in the new view;
3. return the freshly rebuilt view (or a summary of what changed) directly in the HTTP response, so the
   caller sees the effect without a second request.

This is the whole of "hot config, no restart." There is no separate apply step. A config edit is followed
by a full graph rebuild in the same request, so changing a credibility weight or arming an observable takes
effect on the next line of the same call. Reads, by contrast, take no lock at all: they just read the
current-view reference, relying on the fact that swapping one Python reference is atomic under the
interpreter lock, so a reader always sees one complete view and never a half-rebuilt one.

### Endpoint by endpoint, grouped by what it does to the system

**Pure reads (no rebuild, no write).** Health returns readiness plus node/edge counts. The main view
endpoint returns the held graph verbatim, or — if a subject is named — applies that subject's lens at
request time (traverse a bounded number of hops out from the anchor entities, intersect with materiality),
which is query-time scoping that never re-derives or persists a per-subject graph. The node endpoint is a
linear scan for a matching id. The evidence endpoint is the provenance drawer's backend: it resolves every
cited claim id for an element (its own, its supporting cluster's, and its opposing claims, de-duplicated),
resolves each claim's source against live config, and then — this is the elegant part — re-reads the actual
cited span out of the on-disk source document *at request time*. The quote is never stored, so it cannot
drift from the append-only claim; it is capped (documents over 4 MB or outside the repo are refused, quotes
truncate at 700 characters on a word boundary), and a claim whose file or span cannot be resolved yields an
empty quote, never a paraphrase. One more pure read is new: `GET /coverage` reports the resolver's
*identity* coverage — how many entity `same-as` links are confirmed, probable (an analyst candidate), and
possible (the in-memory watch-list), overall and per entity type — and names the types whose unresolved
identity load is high relative to confirmed merges (`(probable + possible) / max(confirmed, 1)` past a
configurable ratio) as explicit **collection gaps**. It is deliberately kept out of `/view` so the
drawn-graph JSON stays byte-identical, and it re-reads the same logs and config `rebuild()` does. It is a
first-class gap surface for *identity* — the mirror of the Known-Gap surface for assertions — and it reads
lopsided on the shipped single-subject corpus (at default boot 62 confirmed / 15 probable / 305 possible
links, flagging five types as collection gaps), which is the honest signal that open sources under-corroborate
identity here, not a resolver to re-tune.

**The question endpoint** is a pure read of graph state — no write, no rebuild — but it does call out to the
LLM agent, unless the deployment is keyless, in which case it falls back to the agent's own deterministic
refusal path. Its refusals are first-class payloads forwarded unmodified, not errors. It is also
conversational: the request may carry a `history` of prior `{question, answer}` turns that the agent seeds
ahead of the current question, so an in-session follow-up resolves against the thread — but the server holds
no session state, the client re-sends the whole transcript each call, and an empty/omitted history is the
unchanged single-shot path.

**The ingest endpoint mutates.** Exactly one of two shapes is legal: a pre-extracted claim bundle (keyless,
validated against the claim schema then appended) or raw text for live LLM extraction (keyed). The keyed
path is gated three times over: a `doc_path` submission is rejected outright as a CLI concern; if the
extraction-enable environment flag is not explicitly truthy the whole keyed path is forbidden regardless of
whether a key exists; and only with the flag on *and* a resolvable client does it actually extract. On a
stock hosted deploy the flag is off, so **the only way evidence enters the running app is by posting frozen
bundles** — the entire live extraction lane, including imagery and OCR, does not execute in the default
demo. The route is deliberately declared as a synchronous function so the framework runs it in a worker
thread, because the extraction fan-out would otherwise crash trying to start an event loop inside the
running one.

**The staged hand-off endpoints** list exactly the withheld documents, whether their bundle files exist,
how many claims each carries, and — read off the live log, not guessed — whether each is already ingested.
This exists so a reviewer running the prebuilt image with no repository checkout can still fetch a withheld
bundle and post it to watch the monitoring story play out.

**The adjudication endpoints mutate** — status override, merge, and alert disposition. Each reconstructs
the review card fresh from live view state (there is no server-side pending queue that could go stale),
validates that the submitted decision is one of the card's own offered options, then appends a decision
record and rebuilds. Crucially, these routes do **not** touch graph state directly: the promotion or merge
is applied by the next rebuild reading that decision log, which is what keeps the whole system replayable
from its two logs. The one exception is alert disposition, which also stamps the resolution directly onto
the in-memory alert object so the alert feed updates without waiting for a rebuild to recompute it — and
that one field is therefore *not* recoverable by replaying the logs, a narrow crack in the otherwise
load-bearing "everything is derivable from the logs" guarantee.

**The config endpoints** expose nine sections. A read returns a section; a write **replaces the whole
section**, not a field — which is exactly why the read exists, so a client can read-modify-write one value
without hand-rebuilding the rest. An optional version token gives optimistic concurrency (mismatch → 409;
omitted → last-writer-wins). After a write to the observables section specifically, the route back-scans
the current view against only the newly added tripwires and lights any immediate matches straight onto the
feed, so an observable you just defined can already be lit before any new evidence arrives. Every section
write then rebuilds regardless, since weights, thresholds, and ontology extensions can all change computed
status.

### What the analyst sees, and how trust is drawn

The UI is a single four-zone workbench — a rail, a stage, a panel, and an overlay drawer — with no routing;
the "screens" are just which value the panel currently holds. Everything hangs off one store with a single
master flag, `mode`, that is either **demo** or **live**, and almost every component branches on it. Demo
mode (the default) renders hand-authored constants so the graded walkthrough is byte-identical every run
and never touches the network. Live mode renders data derived from the view endpoint. The golden rule when
switching: fall back to demo fixtures only when live data is genuinely *absent* — a live view that fetched
successfully but is empty renders as empty, never papered over with demo content.

Trust is encoded by one visual rule applied everywhere: **border style carries certainty, hue never does.**
A solid border means settled, a dashed border means provisional. Confirmed draws a solid teal border with
full fill; probable and possible draw the same teal dashed. "Stale" (we know this was overtaken) is solid
grey with reduced fill. "Insufficient" (we do *not* know — a gap) deliberately shares the dashed-grey
gap treatment and is explicitly forbidden from falling through to the probable-teal look, because
conflating "gap" with "probable" is treated as a correctness bug. "Contradicted" (credible sources
disagree) is its own loud coral state, explicitly not allowed to look like a grey gap, because "sources
disagree" and "we don't know" are opposite facts. Supersession arrows follow the same rule: a settled
replacement is solid, an un-adjudicated candidate replacement is the identical arrow but dashed. Numeric
percentages are banned everywhere except the credibility rubric screen, which is declared the one
legitimate place to show a score because there the number *is* the analyst's own instrument, not a false
confidence readout.

Every claim opens through exactly one door: selecting any map pin, graph node, evidence chip, or record
panel opens the same drawer, which fetches the evidence endpoint and renders claims grouped into
"independent looks," each showing its kind (observed / inferred / retracted), its exact locator, and the
verbatim quoted span. An id the graph does not know still opens the drawer and says "insufficient evidence
to assess this element" rather than fabricating content.

### The honest gaps on the surface

Three things a reader should not assume work just because the surface implies them. First, the logs are
**in-memory only** — nothing is persisted to disk despite a documented data directory that no boot path
actually uses, so a container restart silently discards every live ingest, adjudication, and config edit
back to the committed baseline. Second, the **review queue has no backing endpoint**: in live mode the
frontend *derives* the triage queue by scanning the rebuilt graph client-side for merge candidates,
contradicted or opposed elements, and undispositioned alerts, then orders them recall-biased (an
unknown/null confidence sorts as *more* urgent, never safer). Third, the **credibility rubric UI recomputes
in the browser but never writes back** — the config-write client method exists and is simply never called,
and the screen honestly labels itself as not persisting. Several other affordances in the demo drawer
("show the working," "override this verdict") are present but inert links; only their live-mode equivalents
actually navigate. None of these are hidden by the code — the frontend is unusually honest about showing an
em-dash rather than a false zero when a read fails — but they are the difference between what the surface
suggests and what it does.


---

## The knobs: everything you can turn, and what moves

### The one rule that governs every knob

There is a single, blunt line separating what you can change while the app runs from what needs an edit and a restart, and it is worth internalising before any table below: **every YAML config value is hot-swappable; every environment variable and every constant baked into code requires an edit and a restart.** There is no in-between. Nine YAML files under `config/` (ontology, sources, credibility, resolution, templates, subjects, observables, places, entities) are read exactly once at boot into an in-memory config store; after that, *nothing* re-reads the files on disk. Every stage reads config off an immutable deep-copy snapshot taken at the start of each rebuild, which is why a config edit can never half-apply mid-rebuild.

The only way to change a value live is `POST /config/{section}`, which **replaces the whole section** (not a single key — there is a shallow-merge "nudge one weight" helper in the store, but no route calls it, so in practice the SPA must read the whole section, edit it, and write it all back), re-validates it, bumps a version counter, and immediately re-runs the entire rebuild and atomically swaps the served view. That swap *is* the hot reload — no file watcher, no restart. Two consequences worth stamping on your memory: writing the `observables` section additionally back-scans the current view so a new tripwire can fire on existing state; and **hot writes never touch disk** — everything an analyst tunes lives only in process memory and reverts to the files on restart. Status- and materiality-affecting edits take effect on the next rebuild; the subject lens (anchors/hops/filter) is re-applied fresh on every `/ask` and `/view` request, not baked into the rebuild.

### Ingest, extraction, and boot (environment + code — restart-only)

None of these are config; all need an edit and restart.

| Knob | Where | Default | Effect / what moves |
|---|---|---|---|
| `CHANAKYA_ENABLE_EXTRACTION` | env | **off** | Gate on keyed LLM extraction at `POST /ingest`. Off → a raw-doc `POST /ingest` is refused (400/403), pointed at submitting a pre-extracted `bundle` instead; bundle-shaped submissions always append regardless of this flag. |
| `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` | env | unset | Presence selects the live extraction provider (Gemini preferred); neither → frozen-bundle path. `ANTHROPIC_API_KEY` also gates the keyed ASK agent + the entailment judge. |
| `CHANAKYA_SCENARIO` | env | `hq9p_primary` | Which frozen scenario boots. |
| `CHANAKYA_SEED_WITHHOLD` | env | (file value) | Which docs are absent at boot — the most load-bearing knob for *monitoring*, since a withheld doc ingested later is what produces the delta a tripwire fires on. Ships holding `d18_rahwali_pass1` + `d19_rahwali_confirm`. |
| `AZURE_DOCINTEL_ENDPOINT`/`KEY` (or generic `AZURE_ENDPOINT`/`AZURE_API_KEY`) | env | unset | Optional OCR provider for scanned PDFs. |
| Ingest `MODEL` / `DEFAULT_GEMINI_MODEL` / `MAX_TOKENS` | code | `claude-opus-4-8` / `gemini-flash-latest` / `8192` | Extraction model + token cap. `MAX_TOKENS` is passed to Anthropic only, never Gemini. |
| `PDF_CHUNK_MAX_PAGES` / `PDF_CHUNK_MAX_CHARS` | code | `8` / `60000` | When a PDF is windowed page-by-page before extraction. |
| `attribution_proposer` / `basing_proposer` | credibility.yaml (**hot**) | max_calls 8 / max_claims 20 | Budget caps on the two rebuild-time enrichment proposers. |

### Credibility / SCORE (credibility.yaml — all hot)

This is the richest and most consequential knob surface. Per-claim credibility is `R(source) × Π(integrity) × freshness`; the status label is then derived by pooling independent looks and applying gates in strict priority.

| Knob | Default | Effect / what visibly moves |
|---|---|---|
| `factor_weights` | authority .35 / process .30 / directness .10 / track_record .10 / intrinsic_plausibility .15 (sum 1.0) | Re-weights the source-class credibility `R`. Because the weights sum to 1.0 and every class row carries all five factors, the "normalise by present factors" logic never actually kicks in. |
| `source_class_factors` | nine classes | The 0–1 factor scores per class. Sanity outputs: SIPRI ≈ 0.85, satellite ≈ 0.86, ISPR ≈ 0.75, trade-media ≈ 0.64, named-social ≈ 0.35, anon ≈ 0.25. An **unknown class scores R = 0.0** (fail-closed). `track_record` is pinned 0.5 and `intrinsic_plausibility` 1.0 for every class — the promised per-claim plausibility override is not wired. |
| `thresholds.confirmed` / `.probable` | 0.80 / 0.50 | The confidence cutoffs for the two assertable bands. Below 0.50 an assertion can never even reach probable. |
| `min_independent_groups` | 2 | Independent looks required to confirm. **If unset, nothing can ever confirm.** |
| `same_class_weight` | 0.5 | Down-weight applied to every same-discipline look after the first. This is why confirmed effectively needs *two different collection disciplines* (imagery + text) or *three* same-discipline looks. **No code default — delete the key and same-discipline down-weighting silently turns off.** |
| `decay_base` | 2 | Freshness halves at exactly one half-life. |
| `half_life_defaults` | perishable 540d / semi-durable 540d / force-revalidated 1825d / durable = none | The per-freshness-class fallback. **This is what actually drives all decay.** perishable=540 is tuned to keep Rawalpindi-2021 stale and Rahwali-2025 fresh. |
| `half_lives_days` | per-edge/variant | Ostensibly per-edge overrides — but every dotted `<edge>.<variant>` key is unreachable (nothing tags `freshness_variant`), so they all fall through to the class default. Only two half-lives are actually live: 540 and 1825; durable edges never decay. |
| `integrity_penalties` | recycled .30 / mismatched-caption .30 / uncheckable-caption .9 / coord-inauth-suspected .5 / **too_clean .4** / edited .30 / synthetic .10 | Multipliers applied to `Π(integrity)`. A missing signal → 1.0 (never zeroes a claim). Note: the whole `artifact_integrity` table and the too-clean penalty are inert on the real corpus (see call-outs). |
| `pdq_recycled_hamming` | 10 | Perceptual-hash radius for calling an image "recycled". If unset, exact-sha only. |
| `as_of` | **null** | The pinned evaluation date. Shipped null, so "now" is always the newest claim in the corpus — never the wall clock. Set it (via POST) to advance the clock and demote perishable edges to stale. |
| `supersede_floor` | min_band probable, min_looks 1 | Quality bar the *newer* fact must clear to retire an older one. Absent → nothing is ever retired (fail-closed). |
| `assertable_status` | `[confirmed, probable]` | The status band a link may rest on for ASK. Read by the agent, not by SCORE itself. Empty/absent → nothing assertable → refusal. |
| `gated_attrs` | `[foreign_control, readiness]` | Attributes that block confirmed if present-but-UNKNOWN. |

### Resolution (resolution.yaml + entities.yaml + places.yaml — all hot)

Merge score is a weighted sum of four signals, banded into auto-merge / HITL / separate.

| Knob | Default | Effect |
|---|---|---|
| `merge_weights` | attribute .40 / relational .40 / temporal .05 / source_asserted .15 | The deterministic subtotal (everything but source_asserted) tops out at exactly 0.85, so the *fuzzy* path auto-merges only on simultaneous perfect name + neighbourhood + non-relocation; real auto-merges come from the bootstrap rules. |
| `bands.auto_merge` / `.hitl_low` | 0.85 / 0.45 | ≥0.85 auto-merges (identity *confirmed*), [0.45, 0.85) → HITL (identity *probable*). **If either is absent the resolver is inert** (identity partition). |
| `bands.possible_floor` | 0.25 | The three-status floor. A pair in [0.25, 0.45) is retained as a *possible* watch-list link (in-memory `Partition.possible`, **never drawn as a wire edge** — view JSON is byte-unchanged) rather than dropped: the antidote to fragmentation. Absent → the tier is off and sub-HITL pairs drop exactly as before. |
| `auto_merge_by_type` | manufacturer 0.37 / trading_org 0.37 | Per-type auto-merge floor. For these two org types a near-identical name reliably denotes one entity, so a lower floor auto-merges the spelling-variant pairs (CPMIEC ≡ China … Precision Machinery; the SINO-GALAXY spellings; Taian ≡ Taian/Wanshan) the global 0.85 could never reach. Applies only when **both** endpoints carry the listed type; every identity-sensitive type keeps 0.85; `source` is deliberately excluded (persona links stay HITL). Only the auto floor moves — vetoes and `hitl_low` are untouched. Reduces org-node fragmentation; does **not** lift the SCORE-stage confirmed-*status* count. |
| `name_alone_caps_at_possible` | **true** | A *fuzzy* pair whose only nonzero signal is name (`attribute` > 0, relational = 0, source-asserted = 0) is capped at *possible*, never *probable*/HITL — a bare name match must not spend analyst attention. Raise-only channels (source-asserted / LLM-proposed) are exempt. Does **not** touch the exact-name / alias-class 1.0 bootstrap. |
| `attribute_roles` | 1 critical (`variant.operator_branch`), 7 supporting, 0 perishable-true | Per-type identity role of each attribute. *critical* = a stated disagreement is a hard wall; *supporting* = agreement raises the score (the soft-penalty half is inert — `conflict_penalty` is unset); *neutral* (unlisted) = retained with provenance, no identity effect. The one critical wall is **inert on the corpus** (no claim states `operator_branch`); every declared attr is `perishable: false`, so the perishable path is dormant too. |
| `critical_veto_min_grade` | C | Credibility floor on the critical-attribute wall: a stated critical disagreement walls only when both conflicting values come from a source at STANAG grade A/B/C; a D/E/F source *raises* the pair to a *probable* HITL candidate instead of walling, so one flaky low-grade source can't shatter a well-supported merge. Inert today (the wall it gates never fires). |
| `coverage_gap_ratio` | 2.0 | `GET /coverage` flags a type as a collection gap when `(probable + possible) / max(confirmed, 1)` reaches this. Reporting-only — changes no merge decision, draws nothing. Absent → gap detection off. |
| `relational_support_k` | 2 | How many shared neighbours = full relational strength; one shared hub reads as half. |
| `entity_geo_conflict_max_km` | default 100, basing_site 25 | Two entities both stating coordinates farther apart than this are vetoed from merging outright — no score, no HITL. |
| `containment_min_descriptor_len` / `_short_tokens` / `acronym_min_len` | 3 / 2 / 3 | Open-world name-bootstrap triggers; any absent → that trigger off. |
| Place gates | `place_min_geocode_confidence` 0.6 · `place_proximity_hitl_multiplier` 3 · `place_identity_precision_classes` [pad, site, terminal] · `place_bind_on_curated_toponym` true · `place_entity_types` [basing_site, area_of_operations] · `toponym_descriptive_markers` [",","~","/"," km "] | Govern gazetteer matching. `place_identity_precision_classes` is the one to watch: **remove that line and every area anchor (city/district/province) becomes eligible to fuse batteries that merely share a province** — the safe state requires the key to be *present*. |
| `proximity_radius_m` (in **places.yaml**) | pad 500 / site 1500 / terminal 3000 / district 5000 / city 15000 / province 150000 | The live per-precision-class match radii (also the map's drawn uncertainty envelope). |
| `alias_table` / `transliteration` / `distinct_from` | — | Alias equivalence classes, transliteration variants, and hard cannot-link pairs. |
| entities.yaml registry | — | Canonical-id seeds; a surface form equal to a registry alias bootstraps at confidence 1.0. Also carries entity-level `distinct_from` vetoes and seeded `attrs` (e.g. `foreign_control`). |

### Materiality and the subject lens (ontology.yaml + subjects.yaml — hot)

Materiality precompute runs once per rebuild over the whole graph (subject-agnostic). The lens is a query-time scope.

| Knob | Where | Default | Effect |
|---|---|---|---|
| `materiality.function_attr` | ontology.yaml | `functional_role` | The node attr that partitions sole-source counting by function. Read via `config.ontology.materiality`. |
| `supplier_end` (per edge) | ontology.yaml | `from` | Which endpoint is the supplier for chokepoint counting. All six sustainment edges declare it. |
| `anchors` / `max_hops` / `trace_lanes` | subjects.yaml | — / **3** / — | The lens's anchor set, reachability radius, and the ordered edge lanes a trace may walk (fed to the path tool). |
| `materiality_filter.node_types_allow` / `.never_drop_indeterminate` | subjects.yaml | — / true | Which node types survive the lens; indeterminate nodes are kept by default ("absence of evidence ≠ exclusion"). |

### Sufficiency / refusal templates (templates.yaml — hot)

Seven evidence-requirement templates decide whether an assertion is *assessable* at all. Only three (`based-at`, `inducted-into`, `supplies-component`) ever match a real claim; the other four are never-observable and dead on the corpus.

| Knob | Default | Effect |
|---|---|---|
| `require` per template | `any_of` / `all_of` / `never_observable` | The evidence-slot logic. No template for a type → assertion passes trivially (the dominant outcome). |
| slot `within_days` | 365 (based-at), 1825 (inducted-into origin) | Recency window for imagery/group slots. Read only by three slot handlers. |
| slot `min` | 1; based-at 2, supplies-component origin 2 | Minimum independent groups a group-slot needs. |
| `refusal_template` / `unscheduled_coverage_phrase` / `edge_phrasing` | — | The prose an analyst reads. Refusal copy is fill-in-the-blank, never regenerated. |

Source `cadence` (in sources.yaml, e.g. `7d`/`30d`/`365d`) is the *only* input to a gap's "next coverage due" date — non-numeric cadences (`event-driven`, `continuous`) yield no schedule.

### Observables / MONITOR (observables.yaml — hot)

Tripwires diff the previous view against the just-rebuilt one on every write path (ingest, HITL, config) — **there is no scheduler, nothing fires on a timer**.

| Knob | Default | Effect |
|---|---|---|
| `trigger.on` | — | Selects the firing mode: `state_change`/`occupancy_state_change`/`geofence_crossing` → CROSSING; `new_edge`/`new_node` → EXISTS; an operator name → MATCH; **anything else (notably `new_claim`) → arm-only, cannot fire.** |
| `trigger.match_on` | — | The identity/state grouping vocabulary. Unknown tokens are surfaced as `unconsumed`, not silently ignored. |
| `trigger.anchors_within_hops` | lens `max_hops`, else 0 | Scope radius. The flagship pins it to 0 (watch the unit itself). |
| `where_before` / `where_after` / `where_change` | — | Extra DSL gates on prior/new/delta state. |
| `subject` + `watch_instances` | — | Scope inputs. If a named lens resolves no anchors, falls back to explicit instances, else evaluates the *whole graph* (recall-biased). |
| `severity` | `notify` | Copied onto the alert but **never branched on** — no escalate-vs-notify routing exists. |

Of the three shipped observables, only `obs-basing-relocation` fires on the real corpus; the other two are inert (one needs a `replenishes` edge no bundle contains, one is `new_claim` = arm-only).

### The retrieval agent (code constants — restart-only)

The ASK agent's tuning is deliberately *not* under the config layer (the "no magic numbers" gate scopes credibility/resolve/materiality/observe, not the agent).

| Knob | Default | Effect |
|---|---|---|
| `MODEL` / `EFFORT` / `MAX_TOKENS` | `claude-opus-4-8` / `medium` / 16384 | Agent model, reasoning effort, per-turn token cap. No temperature/top_p (400s on Opus 4.8). |
| `HARD_ITERATION_CAP` | 8 | ReAct think→act→observe steps before giving up. No wall-clock or total-token budget exists. |
| `MAX_HOPS_CAP` | 4 | Caps the path tool's hop argument via `min(max_hops, 4)`. Distinct from the lens's own `max_hops`=3 (and 3<4, so the cap never bites the lens). |
| `DEFAULT_TOP_K` / `FUZZY_SUGGEST_CUTOFF` | 3 / 60 | Candidate beam and fuzzy-match floor in entity lookup. BM25 blend (0.85/0.15) and tier scores (100/95) are hardcoded too. |

### Config keys with no live reader

These sit in the YAML looking live and are not. Editing them has no effect.

- **credibility.yaml `gates:` block** (`adversary_denial`/`decoy_risk` with `exclude_from_grouping`/`cap_at_probable`) — the clearest drift between the config surface and the implementation. Zero readers. The cap-at-probable and grouping-exclusion behaviour is real but **hardcoded** in the status and independence machinery off source boolean flags. Editing this block has no effect.
- **credibility.yaml `coreference` block** — commented out/dormant; `coref_authoritative_evidence` ships empty, so in-document coreference bootstraps nothing.
- **credibility.yaml `<edge>.<variant>` half-life keys** — every dotted variant is unreachable; nothing tags `freshness_variant`. The 30-day "field occupancy" rate an analyst might expect is unreachable at runtime.
- **resolution.yaml `place_proximity_radius_m` block** — an unused duplicate; the live radii come from `proximity_radius_m` in *places.yaml*.
- **resolution.yaml `attribute_scoring.conflict_penalty` / `hard_id_fields`** — these have live readers but ship *unset*, so the supporting-attribute soft penalty never docks a merge and the unique-hard-id bootstrap never fires. (The sibling `attribute_roles` block *is* now populated — a per-type critical/supporting taxonomy whose agreement term and one credibility-gated critical wall are wired — but the wall is inert on the corpus, since no claim states the one attribute declared critical.)
- **subjects.yaml `exclude_off_subject` / `materiality_attrs`** — declared but not consumed (an explicit, tracked no-op; wiring `exclude_off_subject` would leak the grading oracle). `min_chokepoint_count` / `chokepoint_status_in` are *implemented* but never set in the shipped config.
- **observables.yaml secondary keys** — `from_type`, `to_type`, `event_subtype`, `source_class`, `implies_edge`, `target_status_ceiling` are all unconsumed (honestly surfaced under `unconsumed_keys`). `severity` is carried but never acted on.
- **templates.yaml `on_fail`** (every template sets it, nothing reads it) and **`cross_interest`** (authored on `inducted-into`, read by nothing).
- **HITL `TriageConfig` / `STAR_TYPES` / `CONTROL_POINTS`** — the escalate-vs-auto gate, the priority queue, and the 8-point catalogue exist but have no live caller; the app uses one function (`dispose`) through three endpoints. The `exclude_claims` effect that a status-`reject` was supposed to emit is unreachable — reject is a forced demote instead.

### Thresholds fixed in code

- **Adversary-denial's cap-at-probable and exclude-from-grouping** — the config block advertises them; the numbers live in code.
- **The six sustainment edge types and the `substitutable-by` constant** in materiality precompute — the comment says "overridable via `config.materiality`", but the reader looks at the wrong attribute (`config.materiality` instead of `config.ontology.materiality`), so any override is silently ignored and it always falls back to the hardcoded 6-edge tuple. Latent today because the tuple matches the ontology; the documented override would have no effect if used.
- **The entire retrieval agent** — model, effort, token cap, iteration cap, hop cap, beam, fuzzy cutoff, BM25 blend — all code constants outside the config layer.
- **All ingest model/chunk constants** — model ids, token cap, PDF windowing thresholds.
- **Geocode-confidence scores** (coord-parse 1.0, gazetteer 0.9, relative-offset 0.5, nominatim 0.4) — a `geocode_confidence` key is *expected* in places.yaml but not present, so these code literals rule.
- **The extraction `model_conf` stamp** is pinned at 1.0 — the per-claim extraction-confidence seam is not wired.
- **Silent-default traps** worth naming: `same_class_weight` (no code default — deleting it disables discipline down-weighting), the resolution `bands` (absent → resolver inert), `min_independent_groups` (unset → nothing confirms), and `place_identity_precision_classes` (removed → area anchors fuse) all change behaviour *by absence* rather than failing loud.

### Cookbook: to change behaviour X, turn knob Y

- **Make more findings reach "confirmed."** Lower `thresholds.confirmed` (0.80) and/or `min_independent_groups` (2→1) in credibility.yaml. But the real blocker is upstream: most corpus nodes are single-claim, and same-discipline looks are half-weight, so two looks of one discipline sum to only 1.5. Two *different* disciplines corroborating is what actually confirms.
- **Advance the clock / age things out.** POST a credibility section with `as_of` set to a future date (it ships null, pinned to the newest claim). Push it past 540 days from a perishable edge's date and that edge demotes to stale.
- **Re-tune what decays how fast.** Edit `half_life_defaults` in credibility.yaml — not the `half_lives_days` dotted keys (those are dead). Only perishable/semi-durable (540) and force-revalidated (1825) are live; durable never decays.
- **Widen or narrow auto-merge vs analyst review.** Move `bands.auto_merge` (0.85) and `bands.hitl_low` (0.45) in resolution.yaml. Lower auto_merge → more silent merges; raise hitl_low → fewer HITL cards but more silent separations. For the two org types (`manufacturer`, `trading_org`) a per-type floor `auto_merge_by_type` (0.37) already sits below the global bar; add types there — or lower the floor — to auto-merge more spelling variants without touching the global 0.85. And `bands.possible_floor` (0.25) governs the *possible* watch-list: lower it to retain more latent identity links off the analyst's desk, raise it to keep only the more-plausible ones.
- **Tighten the "can't be the same place" veto.** Lower `entity_geo_conflict_max_km` (basing_site 25 km) in resolution.yaml — smaller tolerance splits more aggressively. Do *not* delete `place_identity_precision_classes` or area anchors start fusing distinct batteries.
- **Add a tripwire that lights up immediately.** POST `/config/observable` — writing that section back-scans the current view, so an EXISTS/MATCH observable fires on existing state at once. Use `on: new_edge` or an operator predicate; `on: new_claim` compiles to arm-only and never fires from a view delta.
- **Re-weight source credibility.** Edit `factor_weights` and `source_class_factors` in credibility.yaml. Remember an unrecognised source class scores R = 0.0 (fail-closed), so adding a class *row* matters as much as the weights.
- **Change the subject in the view.** Edit `anchors` / `max_hops` / `trace_lanes` in subjects.yaml — but note the flagship "trace the chokepoint" answer is anchored to the `lens-hq9p-pk` lens in code regardless of what subject the request asks for; the lens config only rescopes the general view and the ReAct path.


---

## Reality check: what is load-bearing and what is not yet wired

The system sorts cleanly into four tiers. Tier one is fully wired and exercised against the real
frozen corpus. Tier two is wired but only ever exercised by fixtures or scripted stand-ins — the real
pipeline or the real model never touches it under test. Tier three is built, but inert given the config
and data that actually ship. Tier four is defined and never called. The honest headline: the spine
(provenance, scoring, the status machine, resolution, the pure rebuild) is tier one and solid; almost
everything in the *adaptation* and *HITL-as-triage* pillars, plus the entire live-extraction front
door, is tier three or four.

### Tier one — load-bearing and exercised on the real corpus

The `rebuild()` reduction is the spine, and it is genuinely pure and fully wired. Its fixed order is:
apply retractions, apply HITL claim-exclusions, optional as-of filter, canonicalize edge direction,
resolve (merge partition), assemble nodes/edges/events, stamp merges and place-refs, score claims,
group by independence, run sufficiency, assign status (the *only* status writer), emit Known Gaps,
apply the supersession floor, precompute materiality, apply HITL decision effects, render resolver
decisions as edges, sort. No LLM, no network, no clock, no RNG live inside it — grep finds zero
`random`/`uuid` imports anywhere in the package, and the only clock reads are at the API edge
(timestamps on decisions and alerts). Same logs plus same config produce a byte-identical view.

Riding on that: the credibility → confirmed/probable status machine (reads its thresholds live from
config), provenance/traceability (every node and assertion edge carries claim_ids that the
`/evidence` drawer resolves back to doc spans), the resolution/entity-merge banding (≥0.85
auto-merge/confirmed, 0.45–0.85 probable/HITL, 0.25–0.45 a retained *possible* watch-list, below that
separate), sufficiency checking, materiality/chokepoint precompute, and the request-time lens (169→30
nodes on the full corpus, 160→27 at default boot). The one observable that fires on real data —
`obs-basing-relocation` — is exercised by the eval harness, which stages the two withheld Rahwali docs
and watches the unit's active based-at edge cross from Rawalpindi to Rahwali. Two offline-derived
enrichments also ship *frozen* and are replayed at every keyless boot, so their results are tier-one even
though the passes that produced them are CLI-only: the three `__basing.json` bundles (the `based-at` edges
the ORBAT question needs) and one `__attr.json` bundle (the image-corroboration `observed-at` inference for
`comp_tel_chassis`, a cited *possible* "Inferred" link visible in the drawer at boot). And `GET /coverage`
reports the resolver's confirmed/probable/possible identity tail per type as a first-class collection-gap
surface. And the flagship worked query runs through the *same* live ReAct loop as every other question,
steered to the `graph_analyze` tool — the flagship answer, like any keyed answer, depends on a model key
and a live plan rather than a canned result.

Two load-bearing caveats sit inside tier one. First, the status machine runs, but **confirmation is
almost never reached on the real corpus**: confirmed requires pooled confidence ≥ 0.80 *and* ≥ 2
effective independent looks, and same-discipline looks weigh only 1.0 + 0.5 = 1.5 < 2, so two
*different* collection disciplines are effectively mandatory — while the large majority of corpus
nodes rest on a single claim. The machinery is live; the confirmed *outcome* is near-absent. Second,
the sufficiency machine runs on every element but only ever gates three edge predicates (`based-at`,
`inducted-into`, `supplies-component`); every node, event, and other edge type has no template and
falls straight through to `satisfied=True`. The one Known Gap reliably produced at runtime is the
materiality candidate-chokepoint gap, which bypasses templates entirely.

### Tier two — wired, but tested only by fixtures or scripts

The ReAct agent loop, the entailment judge, the API read routes, and the extraction lane all *exist
and pass tests*, but nothing in the suite exercises them against real pipeline output or a real model.
The agent loop is driven by a `ScriptedClient` replay; the live path self-skips without a key — so **which
tools the agent chooses, and the quality of its answers, is not exercised by the automated suite**. The entailment judge is a scripted yes/no
in tests and is skipped outright when keyless. The API `/ask`, `/view`, `/node`, `/evidence` tests run
against a hand-authored 8-node view whose statuses are *typed in by hand* (the conftest openly notes a
real rebuild "would not reproduce the hand-faked statuses") — they prove the API forwards a known-good
view, not that the pipeline builds one. The extraction acceptance test runs one real doc through the
lane but with a hand-written `_customs_fill()` standing in for the model, so extraction accuracy is
untested. The confirmed-gate checker (G7) is validated only against a synthetic `status_cases.json`
fixture; the golden `expected_view.json` contains *zero* confirmed elements, so the "no invalid
confirmed" assertion is vacuously true on real data.

### Tier three — built but not exercised by the shipped config and data

- **The live LLM extraction lane is off by default.** Keyed raw-text ingest needs both
  `CHANAKYA_ENABLE_EXTRACTION=1` (defaults off, to protect quota) *and* an extraction key; with
  neither it returns 403. On a stock hosted deploy the only way evidence enters is by POSTing frozen
  bundles. PDF/image ingest via `doc_path` is unconditionally rejected by the API (400, "a CLI
  concern") — multimodal extraction runs only through the CLI, never the hosted app.
- **Azure OCR** is a nested gate below that: no `AZURE_DOCINTEL_*` key ships, so it is inactive at
  runtime and silently falls back to pymupdf text.
- **In-document coreference (extraction pass 2)** is dormant twice: the `credibility.coreference`
  config block is commented out (so the proposer returns `[]`), and it rides on the gated extraction
  lane anyway.
- **The `gates:` config block** (adversary-denial / decoy-risk with `cap_at_probable` /
  `exclude_from_grouping`) has **zero readers** — the cap behaviour is a hardcoded frozenset in the
  status module and a hardcoded field check in the independence grouper. Editing that block has no
  effect. This is the clearest divergence between the "every numeric knob lives in config" description and the implementation.
- **`place_proximity_radius_m` in resolution.yaml is an unused duplicate**; the live radii come from
  `places.yaml`. **`exclude_off_subject` and `materiality_attrs`** on the lens are read by nobody and
  land in the "unrecognised" bag. **`attribute_roles`** now ships a populated per-type critical/supporting
  taxonomy — its agreement term and one credibility-gated critical wall are wired — but the critical wall
  is inert on the corpus (no claim states the one attribute declared critical), and the supporting
  soft-penalty (`conflict_penalty`) and `hard_id_fields` remain unset, so those paths never fire.
  **`track_record` (0.50) and `intrinsic_plausibility` (1.0)** are identical for every source class —
  constant priors that never differentiate a source.
- **Two of three observables cannot fire on the shipped data.**
  `obs-followon-interceptor-order` waits on a `replenishes` edge that no bundle produces;
  `obs-spares-tender-probable-induction` compiles to ARM-ONLY and structurally cannot fire from a view
  delta. Their extra keys are all "unconsumed" — honestly surfaced by `explain()`, but with no effect.
- **The geofence seam** (`within_area`, `geofence_crossing`) is compiled and tested but no shipped
  observable uses it, and edge candidates ignore area scoping entirely.
- **`severity` is carried on every alert and branched on nowhere** — there is no
  escalate-vs-notify routing.
- **The M4 integrity loop is half-connected.** The scorer *does* read analyst `flag_origin`
  decisions and taints co-referring claims, but the only producer of such a decision is an item-builder
  with no HTTP route — so no runtime path can write the flag the reader is waiting for.
- **Live "now" is not wired.** Docstrings claim the API stamps today's date into `credibility.as_of`
  at request time; nothing writes it. It stays null, so freshness is always measured against the newest
  claim in the corpus.

### Tier four — defined but not yet called

The HITL attention-triage queue — the design's centrepiece — is not wired: `ReviewQueue`, `should_escalate`,
`order_queue`, `TriageConfig`, and the `enqueue` service have no production caller. Nothing in the
pipeline ever escalates onto a worklist. The learning-loop consumer `read_dispositions` is never
called in production, and it would compute nothing useful anyway: it divides over `alert_fired`
decision records, and **no code path ever writes an `alert_fired` record**. The natural-language
observable proposer (`propose_observable_from_text`) has no API route, and it is the only live caller
of `explain()`, so the "describe a tripwire in plain English" and "here's why this can/can't fire"
screens are absent from the served app. `eval/report.py` (the legible acceptance report) is imported
by nothing. The 66 KB `answer_key.json` oracle is *loaded* but no test compares computed statuses to
its `ground_truth` or the worked-query answer to its `expected_path`, so it currently has no live
consumer. The keyless recorded-transcript replay that some docstrings describe as a
network-safety fallback is not present: `recorded_trace` is never passed and there is no transcript on
disk. The offline enrichment steps (basing derivation, attribution proposer, renormalize) are
CLI-only; the live API lane never derives them — it replays enrichment baked into the bundles offline.

### Determinism, cold boot, and dates

There are exactly two live-model touchpoints: INGEST extraction and the ASK agent (planner + judge +
proposer). Both use forced/strict tool schemas that pin output *shape*, but there is **no
temperature/top-p/seed** on any call (Opus 4.8 rejects those params), so nothing pins *content*. The
frozen bundles are the sole source of reproducibility: a keyed re-extract of the same document will
*not* reproduce a checked-in bundle byte-for-byte, and the live ReAct path is non-reproducible in two
ways — the planner may pick a different tool sequence, and the judge is a fresh yes/no that can flip a
borderline sentence between returned and withheld. Nothing on the keyed path escapes this — the flagship
runs the same live loop as any query. Cold boot with no key seeds the log from 29 committed bundles (minus
the two withheld Rahwali docs), runs one rebuild, and fires no alerts (`prev_view` is None). With no key,
every query — the flagship included — returns a first-class capability refusal, never a fabricated answer.

The date behaviour is benign but not what the docs claim. Because `as_of` is never stamped from the
wall clock, the demo anchors freshness to the newest claim (~2026-07-19) and therefore behaves
identically on any calendar date — good for reproducibility. The one cosmetic artefact:
`next_coverage_due` is computed as that frozen date plus a source cadence, so a reviewer opening a
refusal months later may see a "next coverage due" date already in their past. Internally consistent,
but noticeable.

### What the test suite does not cover

The 810-function suite genuinely proves the structural spine: rebuild purity and cross-process
determinism, append-only enforcement, structural traceability, the two-score separation, the
insufficient-first-class contract, HITL override propagation, the relocation alert firing exactly once
with before/after provenance, and no node plotted >25 km from its own evidence. What a green run does not
cover: nothing on the real corpus is ever asserted to reach *confirmed* (so a pipeline that promotes
nothing passes every test); the model is never really tested (scripted on fixtures, skipped live);
most contract tests run on hand-faked data, not pipeline output; extraction accuracy is untested; the
rich oracle is unused; the corpus-dependent suite silently skips (turning green) if bundles are
absent; the no-magic-numbers scan omits `view/`, `sufficiency/`, and `agent/`; and an HITL override
can force `confirmed` straight past the G7 gate with no test re-checking the invariant.

### Current limitations

1. **Resolution fragmentation limits the headline idea.** Most nodes are single-claim, so most
   never cross the two-independent-look bar; the confirmed/probable distinction — the load-bearing
   credibility idea — does fire but sparsely (12 confirmed nodes and 2 edges at default boot), with the
   graph otherwise sitting in the probable/possible band.
2. **The hosted demo does no live extraction and no document ingest.** The "messy real documents →
   live extraction" narrative is, in the served app, the replay of frozen bundles extracted offline.
3. **HITL collapses to on-demand adjudication.** The triage/queue/escalation abstraction is not wired;
   review happens only via merge-candidate edges plus POST, and a human status override leaves *no*
   on-element provenance marker, so an override-produced "confirmed" is indistinguishable from a
   machine one in the drawer.
4. **The alert-driven adaptation loop is not wired.** Merge and status adjudications now do feed back
   (a merge accept grows the alias table, a reject writes a durable veto), but the *learning-from-alerts*
   loop still is not: the disposition counter it would read is never written — the "monitoring that adapts"
   pillar is built but not yet wired.
5. **The agent's real reasoning is unverified by CI.** The flagship runs the live agent path like any
   query, but tool choice and answer quality are exercised only against scripted/mocked clients in the test
   suite, so live-model behaviour is not covered by the automated tests.
6. **Configurability is overstated in specific, tunable-looking places** — the `gates:` block, the
   attribute-rule keys, the duplicate place radii, and `exclude_off_subject` all read as live knobs but
   have no effect.


---

## Chapter 15: Extension seams: where a new use case or source would plug in

### A new source type

Registering a source that fits an existing document shape (another official press office, another
customs desk) is genuinely config-only: add an entry to the source registry with a `source_type` that
already has a row in the credibility class table, and the pipeline handles it end to end — dispatch,
scoring, everything. The trap is that `source_type` is doing two jobs at once and neither validates
against the other. It is simultaneously the key the format dispatcher uses to narrow which of the six
extraction schemas a document is parsed against, and the key the credibility engine uses to look up the
five-factor score row. If you register a new source with a `source_type` string that has no matching row
in the credibility class table, that source doesn't error — it silently scores `R = 0.0` on every claim it
ever produces (the fail-closed default for an unrecognized class), which reads as "worthless source," not
"missing config." And on the live ingestion API this string is never checked against the registry at
all — a caller can hand `POST /ingest` any `source_type` they like, typo or not, and only find out something
was wrong when that source's claims never confirm anything.

A source whose *documents* don't resemble any of the six existing shapes (prose, NOTAM/navwarning,
customs/BoL, tender, social post, imagery) is a real code change, not config: you need a new pydantic
schema, a new field→claim transform function, and new entries in the cue-keyword table the format sniffer
uses to recognize it — all of that lives in code constants, not YAML. Point of leverage: if the new
source's content is close enough to an existing family, you may only need to add cue words to that
family's bank rather than build a seventh schema.

### A new node or edge type

Adding a node or event type is config-only and low-risk: the ontology's node/event vocabulary is advisory,
not enforced — even a type the live ontology doesn't know about is still written, just tagged
`_offontology_type` for a human to notice later, so there's no failure mode from under-declaring.

Adding an *edge* type is config-only for the mechanics that generalize — declare its `from`/`to` types,
whether it's `symmetric`, its `instance_key` (whether it's a one-at-a-time functional slot like
"based-at" or a multi-valued one like "equips"), and its `freshness_class` — and the direction-canonicalizer,
the extraction relation-enum constraint, and the freshness fallback chain all pick it up automatically at
the next rebuild, no code involved. The one real hardcoding bite here is materiality/chokepoint scoring: the
list of edge types that count as "supply dependencies" for single-point-of-failure detection is a fixed
six-item tuple written directly in the precompute module, not read from the ontology file, because of a
one-line bug — the code looks for an override on the wrong config object (the top-level config bundle
instead of the ontology section it actually lives under). So a new edge type meant to participate in
chokepoint reasoning needs an actual code edit to that tuple (or a fix to the lookup path) — it will not
pick itself up just by being declared in the ontology, however ontology-native it looks. The same is
mostly true of freshness tuning at variant granularity: the per-edge-and-variant half-life keys exist in
config and look overridable, but nothing in the pipeline ever tags a claim with the variant name the
lookup needs, so a new edge type inherits only its freshness *class* default (two live values in practice:
540 days or 1825 days) — finer-grained tuning needs a real tagging step added somewhere in ingest or
resolution, not a YAML edit.

### A new credibility factor

The five-factor R formula (authority, process, directness, track_record, intrinsic_plausibility) is
generic over whatever the weights section lists, so in principle a sixth factor is config-only: add its
weight and a value for every source class. The catch is the normalization only behaves invisibly today
because every class row happens to define all five factors and the weights already sum to 1.0 — add a
factor and forget to backfill even one class row, and that class's denominator quietly shrinks relative to
the others, changing its relative R without anyone touching a number that looks wrong. It's a config-only
edit that still needs a full sweep, not a single line.

A genuinely new integrity *penalty axis* (a new kind of "this looks doctored" signal) is a different
shape of change: the multiplier value itself is config (add a table + values under integrity penalties),
but nothing generic ever writes the flag that table looks up. Every existing M4 flag is stamped by a
specific piece of code — fingerprint-recycling is computed inline in the scoring stage itself; everything
else (edited-artifact, synthetic, too-clean) has no detector at all today and only ever gets set through a
manual HITL flag. A new automatic penalty needs a real detector wired into ingest or scoring that writes
the attribute; the config table by itself does nothing without a writer.

Two related knobs worth knowing as you extend this: the `gates` block that appears to make
adversary-denial's "exclude from corroboration" and "cap at probable" behavior configurable is read by
nothing — that behavior is hardcoded as literal flag-name checks in the status and independence modules,
so touching that block changes nothing and a new denial-like source class needs a code change to those two
modules, not a config edit. And the three-axis independence test itself (same origin / aligned interest /
one-is-inference-of-the-other) is a fixed function, not a configurable rule set — adding a fourth axis for
grouping claims as non-independent (say, "same funding source") is real code in the independence module,
not a new YAML list.

### A new observable

This is the most genuinely config-only seam in the system for the common case. A new tripwire that watches
a field already present on a node or edge (including materiality's precomputed chokepoint fields), using
one of the two comparison modes (a value crossing a threshold or changing state, or a new element
appearing) plus the generic scope/gate vocabulary (`match_on`, `where_before/after/change`,
`anchors_within_hops`), needs zero code — write the YAML, `POST` it, and it back-scans the current graph
immediately. The geofence primitive is a fully wired but currently unused capability in the same
category — nothing ships a geofence observable today, but the code path exists and would work if
configured.

The one structurally impossible case is a tripwire that wants to react to something in the raw evidence
log rather than the rebuilt view — e.g., "alert the moment any claim of type X is ingested, before
resolution." The evaluator only ever diffs two already-built graph views; a trigger of that shape compiles
successfully but is permanently unable to fire (it's the documented "arm-only" dead end). Making that kind
of observable real requires a new detector hooked into the ingest path itself, not a YAML change. Likewise,
a comparison the eight built-in operators can't express (regex, list membership, a custom scoring formula)
needs a new operator added to the comparator code.

### A new subject lens

Also config-only for the ordinary case: a new entry in the subjects file with its own anchors,
hop bound, and edge-type whitelist for path tracing gets full support from the generic reachability and
materiality-filter machinery — including the "only show confirmed chokepoints" and "chokepoint count
above N" filters, which are implemented and tested but simply unused by the shipped lens today, so they're
free to turn on. Two keys in the shipped lens config (`exclude_off_subject`, `materiality_attrs`) look like
they do something but are deliberately inert — one is withheld on purpose because wiring it would leak
grading-oracle information into runtime behavior, the other is just descriptive text — a dedicated test
enforces that they stay unimplemented, so don't spend time trying to activate them.

The flagship "trace the chokepoint" answer is the general `graph_analyze` supply-chain analysis, which
resolves its anchor from the queried subject at runtime. So a brand-new lens is immediately usable end to
end — the general retrieval agent, the view, and the API layer — with no code change, config only.

### A whole new use case

The architecture's promise mostly holds up under inspection: ingestion is source-typed, not use-case-typed,
so nothing in the extraction or dedup path needs to know a new use case exists. Extending the ontology,
adding lenses, and adding observables for the new use case are all config-only by the same seams above.
Where a new use case would earn a real code change: (1) any new document shape its sources bring, per the
source-type section above; (2) anything it wants materiality/chokepoint reasoning to understand about its
own supply or dependency edges, because that reasoning reads a hardcoded edge-type tuple rather than the
ontology, config-only claims to the contrary in the code's own comments notwithstanding; (3) any new
notion of "these two sources don't actually corroborate each other," because independence grouping is a
fixed three-axis function; (4) any genuinely new retrieval capability (a new `graph_*` tool for the ReAct
agent, a different traversal strategy) — the tool set and its iteration/hop caps are code constants, not
config. If a new use case's needs fit inside those four seams, it is close to a pure-config exercise; if it
needs a new axis of "these are/aren't the same evidence" or a new supply-dependency shape, budget for a
small, specific code change rather than assuming the config surface covers it — and check the two
knobs with no live reader (the `gates` block, the `materiality` override) before spending time trying to configure your way
around them.


---

