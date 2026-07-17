# Multi-hop Retrieval & Tool-Calling — Research Reference (2025–2026)

**What this is.** The distilled, source-cited research behind the retrieval design in
`../spine/09-retrieval-and-tools.md`. Two passes: (1) the multi-hop QA / GraphRAG landscape, (2) engineering
best practices for LLM tool-calling over a knowledge graph. Source-quality flagged: **[AUTH]** = official
vendor doc or peer-reviewed/well-cited paper; **[PREPRINT]** = credible arXiv, not yet canonical. Tailored
to *our* system — a small (~40–100 doc, hundreds of nodes) provenance-critical curated OSINT graph, no
embeddings, alias + BM25 + fuzzy lookup, mandatory exact citation and an "insufficient evidence" path.

---

## Pass 1 — Multi-hop QA landscape

**Bottom line.** For a small, provenance-critical, curated-graph system the most defensible approach is
**agentic graph traversal via typed tool-calling**: the LLM plans hops and calls deterministic tools, every
returned node/edge carries the claim IDs it came from, provenance and "insufficient evidence" fall out of
the architecture (empty tool result = first-class signal). **Microsoft GraphRAG is overkill and
counterproductive** — its LLM community summaries sit *between* the answer and the source (defeating
one-click provenance) and are re-derived nondeterministically, and its global/thematic search answers
corpus-wide "themes," not entity-anchored hops. **Embeddings are not load-bearing** at hundreds of curated
nodes; if used at all, confine to *offline candidate-generation*, locally (small sentence-transformer +
sqlite-vec), never as the arbiter. Engineer determinism into the **retrieval layer** (frozen data,
deterministic/stable-sorted tools) so citations are invariant even when wording drifts.

### Approaches, ranked for our constraints
- **(a) Agentic traversal / tool-calling loop** — the dominant research line: Think-on-Graph, Plan-on-Graph,
  KG-Agent, GraphWalk, GraphSearch, GRASP. Best-in-class provenance (tools return claim IDs; each hop a
  citable edge) and native insufficiency (empty result). Failure modes: linking errors propagate;
  aggregation/counting error-prone if the LLM does it; unbounded loops hard to reproduce. **Best fit.**
- **(f) Path/subgraph retrieval** — SubgraphRAG (ICLR'25), RoG, Paths-over-Graph. Faithful, interpretable;
  a close cousin of agentic traversal. At our scale exact traversal is affordable, so its trainable
  approximations buy nothing.
- **(d) Text2Cypher/SPARQL** — auditable when the query is right, but execution accuracy is unreliable on
  complex/unseen schemas (Neo4j Text2Cypher, CypherBench). Keep as *one constrained/parameterized* tool,
  never free-form generation.
- **(c) LightRAG / nano-graphrag** — embedding-retrieval-driven; a threshold, not a traversal, decides what
  returns. Harder to audit/determinize. Unneeded at our scale.
- **(e) Vector/classic RAG** — single-pass, weak on chaining; chunk-level provenance can't separate "says"
  from "corroborates." Full-text fallback tool only.
- **(b) Microsoft GraphRAG** — corpus-scale thematic sensemaking; ~3–5× indexing; opaque, nondeterministic
  community summaries; provenance runs answer→summary→source. **Do not adopt**; cite in the design note as
  the approach we deliberately rejected (and note LazyGraphRAG/DRIFT as where the field itself moved).

### Comparison
| Approach | Multi-hop | Embeddings? | Provenance | Determinism | Setup | Fit (~100 docs) |
|---|---|---|---|---|---|---|
| **Agentic traversal (typed tools)** | LLM plans hops, calls tools | No (optional for linking) | **Excellent** — claim IDs, empty=insufficient | High retrieval; hop-choice logged | Low–mod | **Best** |
| Path/subgraph retrieval | retrieve path, then read | Sometimes | High | High if retriever deterministic | Mod | Good, redundant here |
| Text2Cypher (parameterized) | NL→query | No | Excellent if correct | High once fixed | Mod | One tool, not the mechanism |
| LightRAG / nano-graphrag | dual-level + vector | **Yes** | Medium | Medium | Mod | Overkill |
| Microsoft GraphRAG | local fan-out / global map-reduce | **Yes** + summaries | **Poor for us** | **Low** | **High** | **Counterproductive** |
| Vector RAG | single-pass top-k | **Yes** | Chunk-level | High | Low | Fallback only |

### Embeddings — the honest reason to skip
Not determinism (embeddings *are* deterministic). Two real reasons: (1) at hundreds of curated nodes with an
alias table there's nothing to fuzzily recall that alias + `rapidfuzz` + BM25 don't cover; (2) the
discriminating OSINT signal is **relational** (shared consignee/port/timing), not semantic — a front company
is designed *not* to be semantically near its parent. BYOKG-RAG uses fuzzy-string **and** `bge-m3`
complementarily for candidate-gen (top-3 proposals), never as the decider — the pattern to copy *if* we
ever add embeddings (offline resolution candidate-gen only).

### Key sources (Pass 1)
Think-on-Graph ([2307.07697](https://arxiv.org/abs/2307.07697)); BYOKG-RAG ([2507.04127](https://arxiv.org/abs/2507.04127));
GRASP ([2507.08107](https://arxiv.org/abs/2507.08107)); SubgraphRAG (ICLR 2025); RoG; CypherBench
([2412.18702](https://arxiv.org/abs/2412.18702)); Microsoft GraphRAG ([docs](https://microsoft.github.io/graphrag/),
[From Local to Global](https://www.microsoft.com/en-us/research/publication/from-local-to-global-a-graph-rag-approach-to-query-focused-summarization/));
Thinking Machines, *Defeating Nondeterminism in LLM Inference* ([link](https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/));
attribution survey ([2601.19927](https://arxiv.org/html/2601.19927v1)); multi-hop benchmarks HotpotQA / MuSiQue / 2WikiMultiHopQA.

---

## Pass 2 — Tool-calling & traversal best practices

### 8 guidelines we follow (each + its authoritative source)
1. **Ship ~5–8 capable, purpose-built tools, not one wrapper per primitive; consolidate related ops.**
   Anthropic: "too many tools or overlapping tools can distract agents"; BYOKG-RAG's graph surface is 5
   tools. [AUTH] ([Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents); [BYOKG-RAG](https://arxiv.org/abs/2507.04127))
2. **Push all counting/aggregation/filtering into deterministic tools; never let the LLM tally in its
   head.** Toolformer: LLMs "struggle with basic functionality such as arithmetic." [AUTH]
   ([2302.04761](https://arxiv.org/abs/2302.04761))
3. **Expose a constrained, parameterized query/filter tool, not free-form Cypher/SPARQL generation.**
   [AUTH/PREPRINT] ([CypherBench](https://arxiv.org/abs/2412.18702); [GRASP](https://arxiv.org/abs/2507.08107))
4. **Run a bounded ReAct think→act→observe loop with explicit hop/beam limits + LLM-judged early
   termination.** ToG defaults N=3, D_max=3. [AUTH] ([ReAct 2210.03629](https://arxiv.org/abs/2210.03629);
   [ToG](https://arxiv.org/abs/2307.07697))
5. **Every tool return carries source-claim IDs and returns the traversed path** → attributable by
   construction. [AUTH] ([ToG](https://arxiv.org/abs/2307.07697); [Anthropic Define tools](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools))
6. **Paginate/rank/top-k every neighbour return; keep any single tool output well under ~25k tokens.**
   [AUTH] ([Writing effective tools](https://www.anthropic.com/engineering/writing-tools-for-agents))
7. **Post-hoc grounding check (citation recall/precision via entailment) + a first-class refuse path
   structurally distinct from an empty result.** Trust-Score separates over-responsiveness vs excessive
   refusal (F1_GR / F1_GC). [PREPRINT] ([2409.11242](https://arxiv.org/abs/2409.11242))
8. **Invest disproportionately in tool descriptions/schemas:** 3–4+ sentence descriptions with
   when-NOT-to-use, typed params (`node_id` not `node`), `input_examples`, `strict: true`, actionable
   errors. Anthropic: descriptions are "by far the most important factor in tool performance." [AUTH]
   ([Define tools](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools))

### Notable specifics
- **BYOKG-RAG** (EMNLP'25, Amazon Science) — the strongest concrete template: a KG-Linker LLM emits
  entities + relation paths + a query + a draft answer; **5 complementary tools** ground them (entity
  linking via fuzzy-string + embeddings, path retrieval, Cypher query, agentic triplet traversal,
  scoring-based retrieval); default 2 refine iterations, self-terminate on no-new-entities. *No single
  retrieval strategy wins — combine typed tools and let the LLM orchestrate.* Code:
  [awslabs/graphrag-toolkit](https://github.com/awslabs/graphrag-toolkit).
- **GRASP** — "triple extraction is lossy"; propositions/claims can be more discriminative than KG triples
  (validates our *unit = sourced claim*). Agentic decomposition beats one-shot on multi-hop.
- **Think-on-Graph** — iterative beam search, prune-at-each-hop; LLM pruning beats BM25/SentenceBERT
  pruning by ~8–15% (so reserve LLM pruning for ambiguous frontiers, deterministic top-k elsewhere).
- **Determinism** — no LLM call is bit-deterministic even at temp 0 (FP non-associativity, GPU kernel/MoE
  ordering, load-balancing; Anthropic documents this). Engineer determinism into the retrieval/citation
  layer, not the LLM.
- **Correctness ≠ faithfulness** — up to ~57% of citations can be post-hoc; validate that the cited claim
  *entails* the statement, not that the citation merely exists. [PREPRINT — single-study, directional]
  ([2412.18004](https://arxiv.org/pdf/2412.18004))

### Anti-patterns (documented)
LLM counting in its head (Toolformer); unbounded/free-roaming traversal (ToG's bounds are the
counter-pattern); too many overlapping tools (Anthropic); free-form query generation over an unseen/large
schema (CypherBench/GRASP); treating an empty result as "answer is no" instead of "insufficient evidence"
(Trust-Score); trusting citations that merely exist rather than entail.

### Source-quality summary
Highest confidence: Anthropic engineering + Claude Platform docs; ReAct (ICLR'23); Think-on-Graph
(ICLR'24); Toolformer (NeurIPS'23); BYOKG-RAG (EMNLP'25); GRASP (ISWC'25); Microsoft GraphRAG. Credible
preprints (flagged): CypherBench, Trust-Score/Trust-Align, "Correctness is not Faithfulness." Deliberately
not cited as authority: Medium re-summaries, CiteGuard (very recent, low-citation).
