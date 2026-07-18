# Session ASK — Bounded ReAct Agent + Citation Validator

**Wave 1 · depends F0 (merged) only · runtime LLM · builds against F0's golden view fixture, never sibling code.**
Read `../00-master-plan.md` §4.5 (the agent tool surface + bounds + entailment citation validator — this
session *is* that section), §4.3 (the precomputed materiality attrs the tools *read* off the view; SCORE
computes them, ASK only filters on them), §1 invariant #2 (LLM proposes/plans *downstream* of `rebuild()`;
this is the one query-time place LLM lives, and it never touches the pure rebuild path — so ASK is exempt
from G1 and *may* import `anthropic`), §6 (offline testing with recorded/mocked LLM), §8 (worktree/PR).

## Goal

Stand up the **cited multi-hop QnA agent** as a **callable** (`answer(question, view, config, llm) →
AskAnswer`): a plain deterministic ReAct loop in which the LLM plans/decomposes a question and orchestrates
tool calls, **seven deterministic `graph_*` tools do every set operation / count / filter / materiality
lookup**, an **entailment** citation validator proves every sentence, and a **first-class refusal** path
returns a reasoned Known Gap instead of a guess. The agent runs over an *already-rebuilt* view (it reads the
graph + provenance + precomputed attrs); the API wiring (`/ask`) is a separate session. This is where the
non-negotiable is enforced at query time.

## Design docs to read first
`spine/09` (**THE primary doc** — tool surface, the one principle "LLM plans, tools compute", the bounded
loop, entailment validator, query taxonomy, the worked hard-case end-to-end) · `spine/07` (the thin
overview: decompose → 2–3 hops → cite each hop, observed-vs-inferred, insufficient-on-planted-gap) ·
`C/02-demo-thread` (the hero query + the exact chokepoint rendering expected) · `product/03` **E** (the
Ask/answer shape: decomposition, per-hop citations, observed-vs-inferred from `kind`, refusal payload) ·
`C/01` (the materiality attrs the tools filter on: `chokepoint_status`, `substitutability_state`) · skim
`md/14-multihop-retrieval-research` for the research basis (ReAct, ToG, BYOKG-RAG, Trust-Score, "correctness
≠ faithfulness").

## Scope (build these)

1. **Bounded ReAct loop — no framework** (`chanakya/agent/`). A plain deterministic think→act→observe loop
   in Python (no LangGraph/LlamaIndex): the LLM decomposes the question into sub-goals and emits tool calls;
   a deterministic dispatcher runs the tool and feeds back the structured return; the LLM reads it and does
   only trivial comparison. **All counting/aggregation/filtering/intersection/materiality lives in the
   tools — the model never tallies chokepoints or judges substitutability in its head** (spine/09's one
   load-bearing principle). Bounds: **hop ≤ 4, top-k ≈ 3, a hard iteration cap, explicit LLM
   sufficiency-check termination**. Deterministic top-k by default; LLM-scored pruning *only* where the
   frontier is genuinely ambiguous.
2. **The seven namespaced `graph_*` tools** (signatures frozen in master §4.5):
   - `find_entity(text, type_hint?)` — alias table + BM25 + `rapidfuzz` → ranked candidate node IDs;
     **surfaces `distinct-from` siblings** so HQ-9/P vs HQ-9BE is an explicit disambiguation, never a silent
     wrong bind.
   - `get_node(node_id)` — attrs + provenance + **precomputed materiality attrs** + status/freshness.
   - `neighbors(node_id, edge_types[], direction, limit, offset)` — typed, **paginated top-k** expansion;
     returns neighbours **+ supporting claim IDs per edge** + edge freshness.
   - `find_paths(src, dst, edge_whitelist?, max_hops≈4)` — bounded multi-hop; returns the ordered
     triple+claim chain (the flagship trace).
   - `query_graph(anchor?, pattern, constraints[], aggregate?)` — typed constraints
     (`<, ≤, =, exists, not_exists`) over **raw + materiality** attrs, deterministic count/filter/intersect;
     returns matches **with claim IDs** + a **separate `indeterminate` partition** (UNKNOWN is never silently
     dropped and never counted as a negative). `input_examples` required (its constraint list is
     nested/format-sensitive).
   - `get_evidence(node_or_edge_id)` — the exact indicator(s): source, date, span, credibility, corroboration
     set — one-click-to-source; feeds citations.
   - `check_sufficiency(scope)` — the non-negotiable: **empty ≠ "no"** → Known Gap + `missing_slots` +
     `next_coverage_due`.
3. **Execution modes.** **Fixed `link → gather → query_graph → cite` hero path is primary** (also the
   reproducibility story); a **free loop** handles live follow-ups; a **recorded hero-trace** (transcript of
   decomposition + tool calls + citations) **replays deterministically** as the network-safety fallback for
   the graded Ask beat.
4. **Entailment citation validator** (not mere existence). A mandatory post-hoc check with two parts: a
   **deterministic** part — every cited claim ID exists, supports the hop it is cited on, and every
   count/metric in the answer **matches the tool's returned evidence set**; and an **LLM-judge/NLI** part —
   the cited claim **entails** the sentence it is cited for (cheap judge over the claim span). A sentence with
   no citation, a citation that doesn't support its hop, or a cited-but-not-entailed sentence is **rejected**.
5. **Refusal as a first-class output state.** An empty `query_graph`/`neighbors` result routes to
   `check_sufficiency` → a **reasoned insufficiency** naming the missing coverage + `next_coverage_due`,
   surfacing the **Known Gap** object — **never a confident negative or a fabrication** (disqualifying line).
6. **Observed-vs-inferred + tool hygiene.** Observed-vs-inferred is read **structurally from each claim's
   `kind`** field, not guessed. All tools: `strict: true`; 3–4-sentence descriptions **with a when-NOT-to-use
   clause**; typed params (`node_id`, not `node`); **human-readable claim IDs** (`d05-row12`); **actionable
   errors** (`find_entity` → *"no match for 'HQ9P' — did you mean 'HQ-9/P'?"*, native to the alias table).
7. **Assemble the `AskAnswer`** (populate F0's model / `product/03` E): the **decomposition**, the **path of
   hops** (one edge each), **per-hop citations**, **observed-vs-inferred tags** from `kind`, and the
   **refusal payload** (missing-list + next-coverage-due + Known Gap). ASK produces the object; its visual
   rendering is the frontend's job.
8. **LLM client config.** Anthropic `claude-opus-4-8` direct (optional Gemini), **no `temperature`/`top_p`/
   `top_k`** (HTTP 400 on Opus 4.8), **reasoning effort low**. Keyless boot runs the recorded hero-trace;
   live runs need `ANTHROPIC_API_KEY`.
9. **Query coverage — few tools, WIDE surface (extend, never restrict).** The 7-tool cap is a *reliability*
   constraint (Anthropic: few capable tools beat many overlapping ones), **not a limit on what a reviewer may
   ask.** Breadth comes from **composition**, not a narrow tool per question: `query_graph`'s typed-constraint
   + `aggregate` surface over **raw *and* precomputed materiality attrs** is the load-bearing generalist
   (covers spine/09 taxonomy shapes 5/6/8/9/10 — structural predicate, status/corroboration, temporal/as-of,
   dependency-inversion, comparative/ranking), while `find_entity`/`get_node`/`neighbors`/`find_paths` cover
   point/1-hop/multi-hop/filtered. **When a query class isn't yet servable, EXTEND the capable surface — do
   NOT restrict the question:** add a constraint operator or `aggregate` to `query_graph`, expose one more
   precomputed materiality attr (a config-driven SCORE/`rebuild()` change), or widen an edge-whitelist — and
   add a *new* `graph_*` tool only if a whole shape-class is genuinely uncomposable (a deliberate, rare call
   that keeps the set small). **The right surface is found empirically in THIS session:** run a **wide query
   battery** (all 10 taxonomy shapes + adversarial/edge phrasings), watch what the planner can and can't
   compose, and settle the operator/`aggregate`/attr set, the fixed-vs-free-loop boundary, and where LLM
   pruning earns its cost. Record the battery + the coverage verdict (and any surface extension) in the
   handoff. *(Guidance from Pragalbh: don't cap what can be asked to fit a tool budget — extend the surface.)*

## Contracts implemented
Master **§4.5** (7-tool surface, bounds, execution modes, entailment validator, refusal). ASK **reads**
§4.3's precomputed materiality attrs off the view as opaque node attributes (it never computes them — SCORE
does), and **emits** the §4.8 / `product/03` E `AskAnswer` model (F0-frozen). Honours invariant #2 (LLM lives
only in the query-time agent, downstream of `rebuild()`). No F0-frozen surface is edited; a needed tool-arg
or `AskAnswer` field change is an **F0-amendment PR** (Rule 3), not a silent edit.

## Acceptance criteria
- [ ] The **citation validator rejects an uncited sentence** (deterministic) **and a cited-but-not-entailed
      sentence** (LLM-judge mocked to "not entailed"), and rejects a count that doesn't match the tool's
      evidence set.
- [ ] The **hero query** traces `based-at → inducted-into → imported-by → exported-by → supplies-component`
      (C/02's hop chain), **citing a real claim ID at each hop**, on the golden view fixture.
- [ ] **HT-233 renders as a CANDIDATE chokepoint** (`substitutability_state = UNKNOWN` → the `indeterminate`
      partition), **NOT a confirmed sole-source** — the disqualifying line is not crossed.
- [ ] The **planted-gap query** returns a **reasoned "insufficient evidence"** with `missing_slots` +
      `next_coverage_due` (a Known Gap), **not a guess** and not a confident negative.
- [ ] Tool hygiene verified: `strict:true`, when-NOT-to-use descriptions, `input_examples` on `query_graph`,
      readable claim IDs, and the `find_entity` "did you mean" error fires on `HQ9P`.
- [ ] A **wide query battery** (≥ the 10 spine/09 taxonomy shapes + edge/adversarial phrasings) is run: each
      query is either **answered with per-hop citations** or **refused as insufficient** — never fabricated;
      the coverage result + any surface extension (new constraint/`aggregate`/attr, or a justified new tool)
      is recorded in the handoff. Breadth is served by composition, not by narrowing what may be asked.
- [ ] **Tool layer is deterministic** (stable-sorted top-k, `indeterminate` partitioning) so citations are
      invariant across runs; LLM-touching paths are tested with **recorded/mocked** responses (offline);
      one **opt-in `@live`** test exercises the real API when a key is present.

## Owned paths (nothing else)
`chanakya/agent/**`, `tests/agent/**` (incl. a hand-authored agent view fixture carrying the hero subgraph +
materiality attrs — HT-233 UNKNOWN, the planted gap — as *test input*, since SCORE computing them is out of
scope). **Depends on:** F0. **LLM:** runtime (agent + entailment judge; offline via recorded/mocked).

## Out of scope
Producing the view / materiality attrs (**SCORE** computes `chokepoint_status`/`substitutability_state`; ASK
only reads them); the HTTP `/ask` endpoint and request/response wiring (**API** — ASK exposes a *callable*);
the answer's visual rendering / observed-vs-inferred UX (**frontend**); runtime embeddings (rejected in
spine/09 — offline resolution candidate-gen is a roadmap item, RESOLVE's if any); loop-parameter calibration
on the *real* corpus (a build-time tune once DATA-C/INGEST land — not blocking here).

## Worktree lifecycle
`git worktree add ../wt-ASK -b feat/ask` → implement e2e inside owned paths → keep `ruff`/`mypy`/`pytest` +
all §5 gates green locally → PR `[ASK]` → **you review & merge** → append handoff notes → `git worktree remove ../wt-ASK`. Starts only after F0 is on `main`; runs concurrently with
any other Wave-1 session (disjoint ownership → clean rebase, any merge order).
