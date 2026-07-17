"""The executable abstraction-gate suite (master §5) — G1–G12.

Each gate maps to a load-bearing invariant (master §1) / DECISIONS rule. They run in CI on every PR;
a shortcut that bypasses the structure **fails CI, not review**. F0 seeds each gate with fixtures and
its assertion logic; a Wave-1 session that adds behaviour *extends* the relevant gate fixture but
**never weakens a gate**.
"""
