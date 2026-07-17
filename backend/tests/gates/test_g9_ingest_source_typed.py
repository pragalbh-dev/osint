"""G9 — ingestion is source-typed, never use-case-typed (master §1 #6, §5; DECISIONS).

Import-boundary check: ``chanakya/ingest`` must not read subject/lens config or branch on a subject —
a customs doc ingests identically regardless of consumer. INGEST extends this module; the boundary
holds now (stub) and must keep holding.
"""

from __future__ import annotations

import re

from tests.gates._srcscan import imported_modules, package_py_files

# Use-case coupling that would make ingestion subject-aware.
_FORBIDDEN_TOKENS = ["SubjectLens", "SubjectsConfig", ".subjects", "materiality"]
_FORBIDDEN_IMPORTS = {"chanakya.view", "chanakya.resolve", "chanakya.materiality", "chanakya.observe"}
_SUBJECT_BRANCH = re.compile(r"\bif\s+subject\b|\bsubject\s*==")


def test_ingest_does_not_read_subject_or_ontology_instance() -> None:
    for path in package_py_files("ingest"):
        text = path.read_text()
        for tok in _FORBIDDEN_TOKENS:
            assert tok not in text, f"{path.name} references {tok!r} — ingestion must be source-typed (G9)"
        assert not _SUBJECT_BRANCH.search(text), f"{path.name} branches on subject (G9)"
        assert not (imported_modules(path) & _FORBIDDEN_IMPORTS), f"{path.name} imports a use-case module (G9)"
