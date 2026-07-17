# Spine — Retrieval, Multi-hop QnA & Tool Surface

Covers **how the cited multi-hop QnA agent actually works**: the retrieval approach (and the ones
deliberately rejected), the concrete tool surface, the bounded traversal loop, the citation validator, and
the **hot-config / live-rebuild** model that makes ingestion and analyst-defined observables take effect
with no app restart. This is the detailed design behind the thin overview in `07-monitoring-retrieval-viz.md`;
the store/rebuild plumbing it assumes lives in `08-detailed-design.md`; the materiality attributes it
filters on are defined in `../C/01-materiality-ontology.md`. **Research basis (authoritative sources) is
distilled in `../md/14-multihop-retrieval-research.md`.**

---

## Decisions

### Multi-hop = a bounded, agentic tool-calling loop over the resolved graph — no framework, no embeddings
The agent is a **plain deterministic ReAct-style loop** (think → act → observe) in Python, no LangGraph/
LlamaIndex. It plans a question into sub-goals, calls typed graph tools, reads their structured returns,
does only trivial comparisons itself, and assembles a cited answer. This is the dominant research direction
for entity-anchored multi-hop over a curated graph (ReAct, Think-on-Graph, BYOKG-RAG — see `../md/14`), and
for our hard constraints it is not a compromise but the best fit.

**The one principle everything hangs on:** *the LLM is a query planner/orchestrator; all set operations,
counting, aggregation, filtering, and materiality logic live in deterministic tools.* The model never
counts chokepoints or judges substitutability "in its head" — LLMs are unreliable at exactly that
(Toolformer), and offloading it is what makes the search both **powerful and auditable**.

**Rejected, with reasons** (full landscape in `../md/14`):
- **Microsoft GraphRAG** — answers flow `answer → LLM community summary → entities → source`, which
  structurally defeats one-click-to-exact-source; its headline "global search" answers corpus *themes*, not
  entity-anchored paths; indexing is 3–5× and opaque. Overkill and provenance-corrosive at our scale. *We
  cite it in the design note as the large-corpus approach we deliberately did not use.*
- **Vector / classic RAG** — single-pass top-k can't chain "battery → operator → supplier"; provenance is
  chunk-level, can't separate "says" from "corroborates." A full-text tool only, never the mechanism.
- **Free-form Text2Cypher/SPARQL generation** — brittle on our schema; a query returns rows-or-empty and
  can't distinguish "no data" from "insufficient-to-*assess*." Kept only as a *constrained, parameterized*
  query tool (`query_graph`), never free-form generation (CypherBench).
- **Embeddings in the runtime** — **not load-bearing** at a few hundred curated nodes: alias table + BM25 +
  fuzzy (`rapidfuzz`) cover entity lookup, and the discriminating OSINT signal is **relational, not
  semantic** (a front company is *designed* not to look like its parent). The only defensible use is
  *offline* resolution candidate-gen as one signal — roadmap, not built. **This is a scale + signal
  argument, not a determinism argument** (embeddings are perfectly deterministic).

### The tool surface — ~7 capable, namespaced `graph_*` tools (not a primitive per operation)
Anthropic's guidance is *few, capable, high-impact tools*; too many/overlapping tools distract the agent.
BYOKG-RAG's entire graph surface is 5 tools. Ours:

| Tool | Role |
|---|---|
| `find_entity(text, type_hint?)` | entity linking via **alias table + BM25 + fuzzy** → ranked candidate node IDs; surfaces `distinct-from` siblings so HQ-9/P vs HQ-9BE becomes explicit disambiguation, not a silent wrong bind |
| `get_node(id)` | attrs + provenance + **precomputed materiality attrs** + status/freshness |
| `neighbors(id, edge_types[], direction, limit, offset)` | typed, **paginated, top-k** expansion; returns neighbours **+ supporting claim IDs per edge** + edge freshness |
| `find_paths(src, dst, edge_whitelist?, max_hops≈4)` | bounded multi-hop between anchors; returns the ordered triple+claim chain (the flagship trace) |
| **`query_graph(anchor?, pattern, constraints[], aggregate?)`** | the load-bearing one: typed constraints (`<,≤,=,exists,not_exists`) over raw **and materiality** attrs, deterministic count/filter/intersect; returns matches **with claim IDs** + a separate **`indeterminate` partition** (never silently drops UNKNOWN) |
| `get_evidence(node_or_edge_id)` | the exact indicator(s): source, date, span, credibility, corroboration set — one-click-to-source; feeds citations |
| `check_sufficiency(scope)` | the non-negotiable: empty ≠ "no" → Known Gap + `next_coverage_due` |

### Materiality is precomputed inside `rebuild()`, not computed in query-time tools
Rather than many narrow analytical tools (count-chokepoints, check-substitutability, corroboration-status —
the "overlapping tools" anti-pattern), the **materiality logic runs in `rebuild()`** and materialises
**filterable node attributes**: `chokepoint_count` / `chokepoint_status` (criteria #1/#4/#6 from
`../C/01`), `substitutability_state` (the three-state `substitutable-by` edge), and `status`
(confirmed/probable/possible, already computed per `04-credibility.md`). `query_graph` then filters on them
like any attribute. This (a) honours the "few capable tools" rule, (b) keeps all materiality logic
**deterministic, versioned, config-driven** (the chokepoint criteria/gates are config — principle 9), and
(c) is computed **once per rebuild**, so a config change recomputes it automatically (see hot-config
below). It does **not** violate the LLM-free-`rebuild()` invariant: this is pure graph computation, no LLM.
The precomputed attribute keeps references to its contributing claim/edge IDs so answers still cite them.

### The traversal loop is bounded and mostly-fixed
- **Bounds:** hop cap ≈ 4 (our chain is basing → induction → import → component → origin), beam/top-k ≈ 3,
  a hard iteration cap, and an **explicit LLM sufficiency-check termination** (Think-on-Graph N=3/D=3;
  BYOKG-RAG self-terminates on no-new-entities). Combinatorial blow-up is unlikely at our scale, but a
  single high-degree hub still demands top-k + pagination on `neighbors`.
- **Deterministic top-k by default; LLM-scored pruning only where the frontier is genuinely ambiguous** —
  ToG's ablation shows LLM pruning beats BM25 by 8–15%, so we reserve that cost for ambiguous hops rather
  than paying it everywhere.
- **Fixed workflow primary, agentic fallback.** The hero query runs a near-fixed
  `link → gather → query_graph → cite` path (also the reproducibility story); the free loop is reserved for
  live follow-ups. (Anthropic "simplest thing that works.")

### Citation validator = entailment, not existence
A mandatory post-hoc validator checks that **every claim ID in the answer exists, supports its hop, and
entails the statement it's cited for** (a cheap NLI / LLM-judge over the claim span) — not merely that the
citation exists ("correctness ≠ faithfulness"; up to ~57% of citations can be post-hoc). Counts/metrics in
the answer must match the tool's returned evidence set. **Refusal is a first-class output state, scored on
its own axis** (Trust-Score F1_GR/F1_GC): an empty `query_graph`/`neighbors` result routes to
`check_sufficiency` → a *reasoned* insufficiency naming the missing coverage, **never** a confident negative
or a fabricated answer. "Answer only from retrieved evidence" is enforced, not assumed.

### Tool hygiene (reliable tool-calling)
Per Anthropic's tool-use docs: 3–4-sentence descriptions with **when-NOT-to-use**; unambiguous typed params
(`node_id`, not `node`); `input_examples` on `query_graph` (its constraint list is nested/format-sensitive);
`strict: true`; **namespacing** (`graph_*`); **actionable errors** (`find_entity` → *"no match for 'HQ9P' —
did you mean 'HQ-9/P'?"*, native to our alias table); and **human-readable claim IDs** (`d05-row12`, not a
UUID) — Anthropic notes readable IDs measurably cut hallucination, and it doubles as the one-click label.

### Query taxonomy (the coverage proof)
Organised by *computation shape* (shape dictates the serving tool). C examples are real; B (intent/I&W)
shown to prove the same surface generalises — a B use case swaps the ontology + materiality attrs, not the
retrieval architecture (the layer-contract corollary, `01-graph-and-ontology.md`).

| # | Shape | C example | Served by |
|---|---|---|---|
| 1 | Point lookup | "What is HT-233?" | `find_entity`, `get_node` |
| 2 | 1-hop neighbourhood | "Who supplies HT-233?" | `neighbors` |
| 3 | Multi-hop path (flagship) | "Trace this battery → supplier → origin, name the chokepoint" | `find_paths`, `neighbors`, `get_evidence` |
| 4 | Filtered / spatial | "Components of HQ-9/P at site QWE" | `neighbors` + filters |
| 5 | Structural predicate + aggregation | "Components with < 3 chokepoints and no substitute" | `query_graph` (over precomputed attrs) |
| 6 | Status / corroboration | "Confirmed or probable, on what evidence?" | `get_node`/`query_graph`, `get_evidence` |
| 7 | Gap / insufficiency | "What do we NOT know here?" (planted gap) | `check_sufficiency` + Known-Gap nodes |
| 8 | Temporal / change (monitoring) | "Did occupancy at QWE change? relocation?" | `query_graph` (as-of-T over the event log) |
| 9 | Reverse / dependency-inversion | "Given this supplier, what fielded systems depend on it?" | `neighbors` (reverse) + precomputed attrs |
| 10 | Comparative / ranking | "Which chokepoint is most critical / least substitutable?" | `query_graph` aggregate + rank |

B's ACH-style reasoning frameworks sit *on top* of the same tools (the tools surface cited evidence; the
framework scores hypotheses).

### Worked example — the hard case, end to end
*"For HQ-9/P, at basing site QWE, which components have < 3 chokepoints and no substitute?"*
1. `find_entity` → `var:hq9p` (+ `var:hq9be` flagged distinct), `site:qwe`.
2. Gather candidates: `neighbors(site:qwe,[based-at],in)` → units → `neighbors(unit,[operates/fields],filter variant=hq9p)` → component set.
3. **One** `query_graph` with `constraints=[chokepoint_count < 3, substitutability_state = known-sole-source]` → matches **+ claim IDs**, and a separate **`indeterminate`** partition for components whose `substitutability_state = UNKNOWN` (**never** counted as "no substitute" — absence of evidence ≠ evidence of absence, the disqualifying line, encoded in the three-state edge).
4. `check_sufficiency` renders the indeterminate set as *"could not assess c7 — supply chain UNKNOWN, Known Gap, next customs release due D"*; basing freshness checked.
5. Citation validator runs (entailment).

The "hard" query is a **query plan over analytical tools**; intelligence lives in (a) the plan and (b) the
tools + precomputed materiality — never in the model aggregating raw nodes.

---

## Hot-config & live-rebuild (no restart, ever, for user configuration)

The product rule: **nothing an analyst/reviewer does in-app requires an app/container restart.** The key
distinction is *recompute the view (`rebuild()`, an in-process function, milliseconds at demo scale)* vs
*restart the app (a redeploy)*. `rebuild()` is a **live runtime operation** triggered by any change, and
user configuration lives in a **live config store the process reads on each rebuild** (the UI writes to it;
it is never a file baked into the image).

| What the user does in-app | What happens | Restart? |
|---|---|---|
| **Define / edit an observable** | register + evaluate against the current graph immediately (read-only pass; no graph rebuild needed) | **No** |
| **Change credibility weights / thresholds / half-lives / chokepoint criteria** | hot `rebuild()` — recomputes the view *and* the precomputed materiality attrs | **No** |
| **Ingest a document** | append claims → hot `rebuild()` → re-evaluate all armed observables → fire alerts | **No** |
| **Extend the ontology (new node/edge type)** | type registry is config → hot reload → `rebuild()` (NetworkX is schemaless — no migration) | **No** |

The only thing needing a redeploy is **new code** (a brand-new metric or detector). Honest boundary:
*anything a user composes from existing attributes/metrics is hot; writing new Python is a deploy.*
Precompute-in-`rebuild()` is therefore the opposite of freezing — because `rebuild()` runs live, config
changes take effect instantly.

### Analyst-defined observables (not just the seeded one)
An observable is a condition in a **small DSL over existing node/edge attributes + precomputed metrics** —
e.g. *"any Unit's `based-at` crossing to `occupancy_state = confirmed`"*, *"any Component with
`chokepoint_count ≥ 1` and `substitutability_state = known-sole-source`"*, *"a new `replenishes` Contract
appears."* Because it references only fields that already exist, it needs no new code. Flow: **define** in
the UI → **arm immediately** (evaluated against the current graph on save; optional back-scan for existing
matches) → **fires live** on the next `rebuild()` (ingest/decision/config) → **disposition**
(real/noise/needs-more) feeds tripwire tuning (`06-adaptation.md`). The locked HQ-9B Rawalpindi→Rahwali
occupancy tripwire (`../C/02-demo-thread.md`) is just the **seeded example** shipped in
`config/observables.yaml`; reviewers add their own the same way.

### Live ingestion (always available) vs extraction (optional front-end)
- **Ingestion is always available** — the append → `rebuild()` → observable-eval path is always live; this
  is what makes the monitoring axis *real* rather than a scripted reveal.
- **Extraction is the optional part, the reviewer's choice.** With a key (`ANTHROPIC_API_KEY`, or
  `GEMINI_API_KEY`) a *raw* doc is extracted **live** and ingested; without a key, reviewers ingest
  **pre-extracted claim bundles** (the corpus ships in both raw and pre-extracted form) and still fire the
  observable, and the frozen baseline lets them see the whole system + run the hero query keyless.
- The **LLM-free-`rebuild()` invariant holds**: extraction (LLM) runs *upstream* of the append; `rebuild()`
  over the log stays pure/deterministic.

### Determinism posture (de-prioritised)
Determinism is no longer a design constraint that cuts capability. Two lanes: the **frozen baseline + tested
queries reproduce** (graded read/Ask beats; recorded hero-trace as the network-safety fallback on the
call), while the **live-ingestion lane is fresh by design** (the point of monitoring). A tight extraction
prompt gets us "deterministic enough"; it is the reviewer's option to run with or without live extraction.

---

## Open questions
- **The chokepoint-count honesty fork** — does the "< N chokepoints" predicate count *confirmed only* or
  *confirmed + candidate*? A candidate is a known-*unknown*, not a chokepoint; collapsing them prints
  ignorance as a finding (criterion #10). *Leaning: `query_graph` returns both, the answer reports both, the
  analyst picks the predicate basis.*
- **Loop-parameter calibration** — hop cap, beam width, and where LLM-pruning is worth it — tune on the
  frozen corpus at build time.
- **Observable-DSL surface** — which operators/fields to expose in the UI first (start with equality /
  threshold / crossing / exists over the demo's node types).

## Research directions / basis
Authoritative sources (distilled in `../md/14-multihop-retrieval-research.md`): **Anthropic** — *Writing
effective tools*, *Define tools*, *Building effective agents*; **ReAct** (ICLR'23); **Think-on-Graph**
(ICLR'24); **Toolformer** (NeurIPS'23); **BYOKG-RAG** (EMNLP'25); **CypherBench**; **GRASP** (ISWC'25);
**Trust-Score/Trust-Align**; "**Correctness is not Faithfulness in RAG Attributions**"; **Microsoft
GraphRAG** docs. Roadmap: offline embedding candidate-gen for resolution; a KùzuDB-backed `query_graph` for
scale; incremental (non-full) `rebuild()` when the graph outgrows in-memory recompute.
