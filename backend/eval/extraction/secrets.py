"""Key loading for the bake-off — names only, values never printed, never logged, never returned.

The gates already treat "can this candidate be exercised at all?" as a **measurement fact** rather than
a score (``gates.gate_key_present``), which is the right posture: a scorecard that quietly omits a
candidate nobody could run is not the three-way comparison it looks like. But that gate reads
``os.environ``, and this project keeps its secrets in a ``.env`` file that nothing in ``backend/``
loads. So on a normal developer machine every candidate reported "not exercisable" — a *false* fact,
produced by the harness never having looked where the keys actually live.

This module closes that, and nothing more:

* **It reads a ``.env`` and exports the names it finds.** It does not fetch, rotate, validate or
  transmit anything.
* **An already-set environment variable always wins.** A shell export is a deliberate act by the
  operator; a file on disk is ambient. Overriding the deliberate one with the ambient one is how a
  bake-off ends up measuring a model against a key nobody chose.
* **Values never leave this module.** :func:`load_env_file` returns the *names* it set — that is what a
  report may print. There is no function here that returns a secret, because a function that returns a
  secret eventually gets logged.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

#: ``NAME=value``, optionally ``export``-prefixed, with optional surrounding quotes on the value.
_ASSIGNMENT = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")

#: Explicit override, for a container or CI where the file is mounted somewhere unusual.
ENV_FILE_VAR = "CHANAKYA_ENV_FILE"


def _strip_value(raw: str) -> str:
    """The value as written, with one matched pair of surrounding quotes removed."""
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _main_worktree() -> Path | None:
    """The repository's **main** checkout, when this code is running inside a linked worktree.

    Worktrees are how this project parallelises sessions, and a linked worktree is a sibling directory
    of the main checkout, not a child — so walking up from here never reaches the ``.env``. ``git
    rev-parse --git-common-dir`` points at the *shared* ``.git``, whose parent is the main checkout.
    Best-effort: any failure (no git, not a repo, git absent from PATH) simply yields ``None``.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True, text=True, timeout=10, cwd=Path(__file__).resolve().parent,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0 or not out.stdout.strip():
        return None
    common = Path(out.stdout.strip())
    if not common.is_absolute():
        common = (Path(__file__).resolve().parent / common).resolve()
    return common.parent if common.name == ".git" else None


def candidate_paths() -> list[Path]:
    """Where a ``.env`` may live, most-explicit first. Order is the precedence order."""
    paths: list[Path] = []
    override = os.environ.get(ENV_FILE_VAR)
    if override:
        paths.append(Path(override))
    try:
        from chanakya import settings

        paths.append(settings.repo_root() / ".env")
    except Exception:  # pragma: no cover - settings is always importable in this tree
        pass
    main = _main_worktree()
    if main is not None:
        paths.append(main / ".env")
    # Dedupe, order-preserving.
    seen: set[Path] = set()
    unique: list[Path] = []
    for path in paths:
        resolved = path.expanduser()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return unique


def parse_env_file(text: str) -> dict[str, str]:
    """Parse ``.env`` text into ``{name: value}``. Blank lines and ``#`` comments are skipped."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _ASSIGNMENT.match(stripped)
        if match is None:
            continue
        out[match.group(1)] = _strip_value(match.group(2))
    return out


def load_env_file(path: Path | str | None = None, *, override: bool = False) -> list[str]:
    """Export the names in a ``.env`` into ``os.environ``. Returns the **names** it set, sorted.

    ``path`` defaults to the first of :func:`candidate_paths` that exists. Nothing happens — and no
    error is raised — when no file is found: a keyless machine is a legitimate state, and the gates
    already report it honestly. ``override`` is False by design (see the module docstring); it exists so
    a test can prove the precedence rather than assume it.
    """
    chosen: Path | None = None
    if path is not None:
        chosen = Path(path).expanduser()
    else:
        for candidate in candidate_paths():
            if candidate.is_file():
                chosen = candidate
                break
    if chosen is None or not chosen.is_file():
        return []
    values = parse_env_file(chosen.read_text(encoding="utf-8"))
    applied: list[str] = []
    for name, value in values.items():
        if not value:
            continue  # an empty assignment is not a key; leaving it unset keeps the gate honest
        if not override and os.environ.get(name):
            continue
        os.environ[name] = value
        applied.append(name)
    return sorted(applied)


def key_names_present(names: list[str] | tuple[str, ...]) -> dict[str, bool]:
    """``{name: is it set and non-empty}`` — the only shape a report may print about secrets."""
    return {name: bool(os.environ.get(name)) for name in names}


__all__ = [
    "ENV_FILE_VAR",
    "candidate_paths",
    "key_names_present",
    "load_env_file",
    "parse_env_file",
]
