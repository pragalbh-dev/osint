"""Static-analysis helpers shared by the structural gates (G6/G9/G10/G11)."""

from __future__ import annotations

import ast
from pathlib import Path

import chanakya

PKG_ROOT = Path(chanakya.__file__).parent
REPO_ROOT = PKG_ROOT.parents[1]  # backend/chanakya -> repo root


def package_py_files(subpackage: str) -> list[Path]:
    """All ``.py`` files under ``chanakya/<subpackage>`` (recursively)."""
    return sorted((PKG_ROOT / subpackage).rglob("*.py"))


def imported_modules(path: Path) -> set[str]:
    """The set of module names imported by a source file (``import x`` / ``from x import …``)."""
    tree = ast.parse(path.read_text())
    mods: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module)
    return mods


def numeric_literals(path: Path, *, allow: set[float]) -> list[tuple[int, float]]:
    """Numeric constant literals in a file, excluding an allowlist — used by G6 (no magic numbers)."""
    tree = ast.parse(path.read_text())
    hits: list[tuple[int, float]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            if float(node.value) not in allow:
                hits.append((node.lineno, node.value))
    return hits
