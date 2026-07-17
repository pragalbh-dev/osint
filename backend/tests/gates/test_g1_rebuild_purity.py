"""G1 — rebuild-purity. No LLM/network/clock/RNG runs inside the ``rebuild()`` call-path (master §1 #1).

Primary guard is **behavioural**: patch ``socket``, ``anthropic``, ``time``, and ``random`` to raise,
then rebuild over the golden fixtures — it must still run to completion and produce the identical view.
This is what lets the seeded baseline replay identically and keeps the LLM a *proposer upstream of the
log*, never an authority inside the reduction.
"""

from __future__ import annotations

import sys
import types

import pytest

from chanakya.view import rebuild, view_to_json
from tests.fixtures import loaders


def _boom(*_args, **_kwargs):
    raise AssertionError("rebuild() reached a forbidden facility (LLM/network/clock/RNG) — G1 violation")


class _RaisingModule(types.ModuleType):
    def __getattr__(self, _name: str):  # any attribute access explodes
        _boom()


def test_rebuild_is_pure(monkeypatch: pytest.MonkeyPatch) -> None:
    # Baseline (un-patched) output to compare against.
    expected = view_to_json(loaders.golden_view())

    # A raising `anthropic` — importing/using the LLM anywhere in the path would explode.
    monkeypatch.setitem(sys.modules, "anthropic", _RaisingModule("anthropic"))

    # Network, clock, and RNG all raise on use.
    monkeypatch.setattr("socket.socket", _boom)
    monkeypatch.setattr("time.time", _boom)
    monkeypatch.setattr("time.monotonic", _boom)
    monkeypatch.setattr("time.sleep", _boom)
    monkeypatch.setattr("random.random", _boom)
    monkeypatch.setattr("random.randint", _boom)
    monkeypatch.setattr("random.choice", _boom)

    # Fresh logs/config built AFTER patching, so even fixture construction stays pure.
    view = rebuild(loaders.golden_evidence_log(), loaders.golden_decision_log(), loaders.golden_config_store().snapshot())
    assert view_to_json(view) == expected


def test_stage_functions_do_not_import_llm_in_call_path() -> None:
    """Structural companion: the five stage functions rebuild calls must be importable without anthropic.

    (An offline ``propose_*``/``extract`` entrypoint may live in the same package and import anthropic —
    G1 only forbids reaching it from the rebuild call-path; master §1 #2 / PROGRESS amendment.)
    """
    # These imports are exactly what rebuild() pulls in; none may hard-require anthropic at import time.
    monkeypatch_modules = {"anthropic": _RaisingModule("anthropic")}
    saved = {k: sys.modules.get(k) for k in monkeypatch_modules}
    sys.modules.update(monkeypatch_modules)
    try:
        import importlib

        for mod in ("chanakya.resolve", "chanakya.credibility", "chanakya.sufficiency",
                    "chanakya.materiality", "chanakya.view.pipeline"):
            importlib.import_module(mod)  # must not raise
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
