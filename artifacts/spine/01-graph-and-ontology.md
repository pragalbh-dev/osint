# Spine — Graph & Ontology

Covers: is there one graph; the bi-level (evidence vs knowledge) model; is the ontology designed or
discovered; how subjects relate to the graph; extensibility.

---

## Decisions

### One graph; the subject is a lens, not a partition

In the complete system there is **one knowledge graph** that accretes entities/relationships/events from
all sources under the *union* of the use-case ontologies. A "use case" (A/B/C) is an analytic layer over
that graph; a "subject" is a saved **view/filter** — it supplies (a) a set of anchor entities and (b)
which configured pattern (traversal/scoring algorithm) to run, **not** its own database. The
problem-statement algorithm itself stays **subject-generic**: the subject is a parameter to it, not a
different algorithm per subject. This matches the reference build's "one organised corpus → one
queryable graph."

Consequence for building C first: because ingestion is source-typed and the store is schema-flexible (see
below and `02-ingestion-and-unit.md`), C's graph is just this one graph instantiated with C's ontology
subset and corpus. Adding A/B later means adding types + layers, not a new database.

### Bi-level model: evidence layer vs knowledge layer

- **Evidence layer (append-only, immutable).** Every extracted claim: `Source S, dated D, asserts <entity/edge>`. Never destroyed. This is the audit trail / traceability substrate.
- **Knowledge layer (derived, mutable).** The resolved graph of entities and relationships. A node/edge's
status and confidence are **not stored values** — they are **recomputed by `rebuild()`**, a pure function
of (evidence log, decision log, config), whenever a relevant factor changes (an attribute/edge change, or
a new HITL/LLM decision). Recomputing only the affected area is a design-note optimization for later
scale; at demo scale a full rebuild is milliseconds, so this is not a build concern now.
- **Two scores, two objects — never averaged.** A **same-as** edge's `merge_confidence` answers an
*identity* question (are these two mentions the same entity?); a resolved node/edge's
`claim_credibility`/`assertion_confidence` answers a *truth* question (how much do we trust what's
asserted about it?). They're computed independently and never blended into one number — this is what lets
us say "the node is real (resolved) but its basing is only probable (credibility)."

When a new document arrives: **append** claims to the evidence layer, **update** the knowledge layer
(resolve into an existing node or create a new one — resolution is **cross-document**: the same entity or
event is typically asserted by many documents, and disambiguation + edge-creation happens across the
whole corpus, not just within one doc; recompute confidence). More independent credible claims →
confirmed; single source → probable; contradiction → flagged. This separation is exactly what makes
"click node → supporting claims → source doc → exact row/line" work, and what keeps *confirmed vs
probable* honest.

### Ontology: schema designed, instances discovered, extension human-gated

The brief looks contradictory ("discovers an ontology" vs "an ontology you designed and can defend") but
it's talking about two things:

- **Schema (type system) — designed.** Node/edge types are hand-designed and defensible; you can state
which questions each type enables and excludes. Do **not** let an LLM invent the schema — LLM-discovered
schemas are non-reproducible, indefensible, and circular if you also generate the corpus with an LLM.
- **Instances — discovered/extracted.** Within the fixed type system, specific entities/edges are pulled
from documents. This is the runtime "discovery."
- **Extension — human-gated, configurable, and strict.** When extraction hits something that doesn't fit
(new type, unmodeled edge), it **proposes** the extension to the analyst (HITL) rather than silently
dropping or hallucinating a type. The LLM may not suggest extensions arbitrarily: extension is governed by
an **analyst-defined rubric** for what counts as a genuinely new type/edge (vs. a variant of an existing
one), and is **gated to trigger only on necessity** — guarding against flooding the analyst with
non-deadline work. This is also the "adversary methods change" adaptation hook (`06-adaptation.md`).

Defensible one-liner: *"I designed the schema because it's what's graded and what must be reproducible;
the system discovers instances against it and proposes schema extensions to the analyst rather than
inventing structure autonomously."*

### The abstraction rules (why one-graph + extendible subjects are free)

- **Schema-flexible store** — add node/edge types with no migration.
- **Source-typed ingestion** — never use-case-typed.
- **Subject = query parameter** — supplies anchor entities + which configured pattern to run; a lens, not
  a partition.

**Layer contract (a corollary of the three rules above, not a 4th rule):** because ingestion is
source-typed and the subject is a lens, a **use case = read-only graph analytics + a decision rubric +
output adapters over the shared graph** — it adds no storage and no ingestion of its own. This is the
thing the three rules *enable*, not a separate rule to remember.

---

## Open questions

- **Store choice.** Property graph (Neo4j / KùzuDB / in-memory NetworkX) vs RDF/triple store vs a
document store with a graph view. Primary criterion: it must support the **algorithms the problem
statements need across A/B/C** — traversal, relational entity resolution, path-finding, chokepoint
detection — not just what C alone needs. Only then do the existing points apply: at demo scale,
schema-flexibility + easy provenance attachment + reproducibility dominate the choice, not raw scale.
- **Where confidence lives — resolved**, see Decisions → "Bi-level model" above: status/confidence are
derived by `rebuild()`, not stored, and recomputed on any factor change. Full rebuild is cheap enough (ms
at demo scale) to re-run on every update; per-area incremental recompute is deferred to the design note as
a future optimization, not a build requirement now.
- **Claim immutability vs correction** — if a source is later found wrong, do we retract the claim
(append a retraction event) rather than delete? Leaning yes (append-only, retraction is itself a claim).

## Research directions

- Bi-temporal / provenance-tracking graph patterns (valid-time vs transaction-time) — relevant to the
freshness model in `04-credibility.md`.
- "Where it breaks at scale" (design-note material): one unified graph makes **resolution collide harder**
(two unrelated "Factory 404"s in different countries) and the graph gets large. Mitigations to write up:
cost-only relevance prefilter with a recall-preserving deferred lane, resolution **blocking keys**, and
country/domain **namespacing**. None needed for the C demo.

