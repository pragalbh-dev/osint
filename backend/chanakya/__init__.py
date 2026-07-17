"""Chanakya OSINT — the shared spine + C-layer backend.

Boot context lives in ``CLAUDE.md``; the frozen inter-module contracts this package
implements are in ``artifacts/plan/00-master-plan.md`` §4. Package layout (master §4.1):

    schemas/      records + value objects + config/view/API models   (F0, frozen)
    config/       live, writable, versioned config store              (F0, frozen)
    store/        append-only SQLite evidence + decision logs         (F0, frozen)
    view/         rebuild() orchestration + lens + JSON export        (F0, frozen)
    resolve/ credibility/ sufficiency/ materiality/ observe/          (Wave-1 stubs here)
    agent/ ingest/ hitl/ api/                                         (Wave-1 stubs here)

Load-bearing invariant: ``rebuild(evidence, decision, config) -> view`` is a *pure,
deterministic* function — no LLM, network, clock, or RNG inside it (master §1, gate G1).
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
