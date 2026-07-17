"""G11 — the generator stays blind to the ontology (master §5; DECISIONS data strategy).

``tools/generate`` emits only raw text/records; it must not import the ontology/schemas or emit clean
structured fields. This kills the circularity objection ("the pipeline earns its extractions").
"""

from __future__ import annotations

import ast

import pytest

from tests.gates._srcscan import REPO_ROOT

_GEN_DIR = REPO_ROOT / "tools" / "generate"


def _gen_py_files():
    if not _GEN_DIR.exists():
        pytest.skip("tools/generate not present in this checkout")
    return [p for p in _GEN_DIR.rglob("*.py") if "__pycache__" not in p.parts]


def test_generator_does_not_import_the_ontology() -> None:
    for path in _gen_py_files():
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for name in names:
                assert not name.startswith("chanakya"), (
                    f"{path.name} imports {name!r} — the generator must stay ontology-blind (G11)"
                )
