# Spine — Graph & Ontology

Covers: is there one graph; the bi-level (evidence vs knowledge) model; is the ontology designed or
discovered; how subjects relate to the graph; extensibility.

---

## Decisions

### One graph; the subject is a lens, not a partition
In the complete system there is **one knowledge graph** that accretes entities/relationships/events from
all sources under the *union* of the use-case ontologies. A "use case" (A/B/C) is an analytic layer over
that graph; a "subject" is a saved **view/filter** (a set of anchor entities + a traversal/scoring
pattern), **not** its own database. This matches the reference build's "one organised corpus → one
queryable graph."

Consequence for building C first: because ingestion is source-typed and the store is schema-flexible (see
below and `02-ingestion-and-unit.md`), C's graph is just this one graph instantiated with C's ontology
subset and corpus. Adding A/B later means adding types + layers, not a new database.

### Bi-level model: evidence layer vs knowledge layer
- **Evidence layer (append-only, immutable).** Every extracted claim: `Source S, dated D, asserts
  <entity/edge>`. Never destroyed. This is the audit trail / traceability substrate.
- **Knowledge layer (derived, mutable).** The resolved graph of entities and relationships. A node/edge's
  confidence is a **function of the claims supporting it** in the evidence layer.

When a new document arrives: **append** claims to the evidence layer, **update** the knowledge layer
(resolve into an existing node or create a new one; recompute confidence). More independent credible
claims → confirmed; single source → probable; contradiction → flagged. This separation is exactly what
makes "click node → supporting claims → source doc → exact row/line" work, and what keeps *confirmed vs
probable* honest.

### Ontology: schema designed, instances discovered, extension human-gated
The brief looks contradictory ("discovers an ontology" vs "an ontology you designed and can defend") but
it's talking about two things:
- **Schema (type system) — designed.** Node/edge types are hand-designed and defensible; you can state
  which questions each type enables and excludes. Do **not** let an LLM invent the schema — LLM-discovered
  schemas are non-reproducible, indefensible, and circular if you also generate the corpus with an LLM.
- **Instances — discovered/extracted.** Within the fixed type system, specific entities/edges are pulled
  from documents. This is the runtime "discovery."
- **Extension — human-gated.** When extraction hits something that doesn't fit (new type, unmodeled edge),
  it **proposes** the extension to the analyst (HITL) rather than silently dropping or hallucinating a
  type. This is also the "adversary methods change" adaptation hook (`06-adaptation.md`).

Defensible one-liner: *"I designed the schema because it's what's graded and what must be reproducible;
the system discovers instances against it and proposes schema extensions to the analyst rather than
inventing structure autonomously."*

### The abstraction rules (why one-graph + extendible subjects are free)
- **Schema-flexible store** — add node/edge types with no migration.
- **Source-typed ingestion** — never use-case-typed.
- **Subject = query parameter** — a lens, not a partition.

---

## Open questions
- **Store choice.** Property graph (Neo4j / KùzuDB / in-memory NetworkX) vs RDF/triple store vs a
  document store with a graph view. Decision deferred; demo scale (~10–15 docs) makes almost anything fine
  — pick for schema-flexibility + easy traversal + easy provenance attachment, not scale.
- **Where confidence lives** — on the knowledge-layer node/edge (recomputed), with the evidence-layer
  claims as inputs. Confirm the recompute is cheap/deterministic enough to re-run on every update.
- **Claim immutability vs correction** — if a source is later found wrong, do we retract the claim
  (append a retraction event) rather than delete? Leaning yes (append-only, retraction is itself a claim).

## Research directions
- Bi-temporal / provenance-tracking graph patterns (valid-time vs transaction-time) — relevant to the
  freshness model in `04-credibility.md`.
- "Where it breaks at scale" (design-note material): one unified graph makes **resolution collide harder**
  (two unrelated "Factory 404"s in different countries) and the graph gets large. Mitigations to write up:
  cost-only relevance prefilter with a recall-preserving deferred lane, resolution **blocking keys**, and
  country/domain **namespacing**. None needed for the C demo.
