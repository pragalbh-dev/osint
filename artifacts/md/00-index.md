# Sarvam Chanakya OSINT Assignment — Cleaned Source Material

Four source documents from `artifacts/`, converted to Markdown for easy browsing. All content is verbatim from the originals; the only thing removed is Claude's internal "thinking" in file 04 (see the note at the top of that file) and repeated PDF page headers/footers.

1. **[01-assignment.md](01-assignment.md)** — the actual Sarvam AI take-home brief (`Sarvam AI Assignment for Pragalbh.pdf`). The ground truth: the five modules, the three use cases (A/B/C), deliverables, what's really being tested.
2. **[02-gemini-chat.md](02-gemini-chat.md)** — a 13-turn chat with Gemini working through data strategy, ACH/deception reasoning, and how use cases A/B/C relate (`Understanding Strategic AI Use Cases.pdf`).
3. **[03-planning-notes.md](03-planning-notes.md)** — rough personal planning notes (`a3261795-…-Sarvam_Assignment.pdf`): understanding of the brief, open questions, the rough plan, and the "shared abstraction layer" architecture idea.
4. **[04-claude-chat.md](04-claude-chat.md)** — a 4-turn chat with Claude analyzing all of the above to decide between use cases A/B/C, calibrate "depth," and stress-test the data-generation and deepfake-detection strategy (`chat.txt`). **Note:** the raw export of this one interleaved Claude's reasoning with its answers; that reasoning has been stripped so only the questions and final answers remain.
5. **[05-data-scoping-C.md](05-data-scoping-C.md)** — real-world data scoping for Use Case C: per-source-type feasibility (free/paid, format, messiness), a candidate-subject comparison (China HQ-9 vs Pakistan HQ-9/P vs China's S-400 import), the entity-resolution alias tables, and a recommended corpus composition. Concludes: finished SAM systems are invisible in public customs data, so the finished-system spine is SIPRI + imagery + official reporting, and the customs layer is built synthetic-from-real-template.

5. **[05-data-scoping-C.md](05-data-scoping-C.md)** — real-world data scoping for Use Case C: what open-source data is actually gettable per candidate subject, raw record shapes/messiness, alias tables, recommended corpus + graded scenarios. Lands on **HQ-9/P (Pakistan)** as the subject.

The original files (`chat.txt` and the three `.pdf`s) are untouched in the parent `artifacts/` folder.

---

## Design docs (working)

Decisions/design derived from the above now live in two sibling folders (each doc carries a
**Decisions · Open questions · Research directions** tail):

- **`../spine/`** — the reusable core all three use cases sit on (the ~70% that's graded). Start at
  [`../spine/00-overview.md`](../spine/00-overview.md): the four load-bearing ideas, the pipeline
  abstraction, and gates. Then graph/ontology, ingestion/unit-of-analysis, resolution, credibility,
  HITL/triage, adaptation, monitoring/retrieval/viz.
- **`../C/`** — Use Case C specifics (the ~30% layer). Start at [`../C/00-overview.md`](../C/00-overview.md):
  scope, subject, target queries, depth ladder. Then materiality/ontology and the demo thread.

Open conceptual questions that seeded these docs are in [`questions.md`](questions.md) (with a resolution
map to where each is now answered).
