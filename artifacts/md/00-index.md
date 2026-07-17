# Sarvam Chanakya OSINT Assignment — Cleaned Source Material

Four source documents from `artifacts/`, converted to Markdown for easy browsing. All content is verbatim from the originals; the only thing removed is Claude's internal "thinking" in file 04 (see the note at the top of that file) and repeated PDF page headers/footers.

1. **[01-assignment.md](01-assignment.md)** — the actual Sarvam AI take-home brief (`Sarvam AI Assignment for Pragalbh.pdf`). The ground truth: the five modules, the three use cases (A/B/C), deliverables, what's really being tested.
2. **[02-gemini-chat.md](02-gemini-chat.md)** — a 13-turn chat with Gemini working through data strategy, ACH/deception reasoning, and how use cases A/B/C relate (`Understanding Strategic AI Use Cases.pdf`).
3. **[03-planning-notes.md](03-planning-notes.md)** — rough personal planning notes (`a3261795-…-Sarvam_Assignment.pdf`): understanding of the brief, open questions, the rough plan, and the "shared abstraction layer" architecture idea.
4. **[04-claude-chat.md](04-claude-chat.md)** — a 4-turn chat with Claude analyzing all of the above to decide between use cases A/B/C, calibrate "depth," and stress-test the data-generation and deepfake-detection strategy (`chat.txt`). **Note:** the raw export of this one interleaved Claude's reasoning with its answers; that reasoning has been stripped so only the questions and final answers remain.
5. **[05-data-scoping-C.md](05-data-scoping-C.md)** — real-world data scoping for Use Case C: per-source-type feasibility (free/paid, format, messiness), a candidate-subject comparison (China HQ-9 vs Pakistan HQ-9/P vs China's S-400 import), the entity-resolution alias tables, and a recommended corpus composition. Concludes: finished SAM systems are invisible in public customs data, so the finished-system spine is SIPRI + imagery + official reporting, and the customs layer is built synthetic-from-real-template.

5. **[05-data-scoping-C.md](05-data-scoping-C.md)** — real-world data scoping for Use Case C: what open-source data is actually gettable per candidate subject, raw record shapes/messiness, alias tables, recommended corpus + graded scenarios. Lands on **HQ-9/P (Pakistan)** as the subject.
6. **[06-preflight-audit.md](06-preflight-audit.md)** · **[07-stack.md](07-stack.md)** · **[08-spine-2.0-review.md](08-spine-2.0-review.md)** · **[09-corpus-sizing.md](09-corpus-sizing.md)** — audit, stack, spine review, and the corpus-sizing decision (~40–50 docs, S≈20/N≈20–30).
7. **[10-data-generation-strategy.md](10-data-generation-strategy.md)** — the concrete plan: reusable config-driven engine (unit = the sourced claim), enumerated **corruption operators** (§3) + **deception operators** (§4, the misinformation-planting plan — 11 ops, each earned-in-text with detector + expected behaviour + a "bypass suite" incl. the supersede-spoof and its fix), per-node testable+refutable corroboration design (§5), the Rawalpindi→Rahwali observable realignment (§6), and reuse for A/B (§7).
8. **[11-data-requirements-from-pragalbh.md](11-data-requirements-from-pragalbh.md)** — what only you can do: decisions (imagery posture, sustainment node, cross-interest scope, calibration sign-off) + prioritized logins (Copernicus, Google Earth, SIPRI export, residential-IP run).

**Tooling** (`../../tools/`): `gather/` (real-corpus gatherer + `manifest.jsonl`) and `generate/` (config-driven generator: `operators.yaml`, `scenarios/hq9p_primary.yaml` [23 signal docs, realigned] + `scenarios/hq9p_chaff.yaml` [27 chaff docs]). Frozen corpus (50 docs) → `../../corpus/scenarios/{hq9p_primary,hq9p_chaff}/docs/` + `answer_key.json` (verification oracle). Build log: **[12-build-log-2026-07-17.md](12-build-log-2026-07-17.md)**.

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
