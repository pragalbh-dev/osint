"""``answer_key.json`` is EVAL-only — the pipeline is never tuned to the oracle it is graded against.

The acceptance harness feeds the pipeline **only** corpus docs / pre-extracted bundles + ``config/*.yaml``.
``answer_key.json`` is opened solely under ``tests/acceptance/`` and ``eval/``. If any pipeline module
(``chanakya/``), any ``config/*.yaml``, or any frozen claim bundle referenced the oracle, the whole
acceptance result would be circular — so this guard fails loudly on the first such reference (master §,
``sessions/EVAL.md`` scope #3). This test needs no recorded bundles; it always runs.
"""

from __future__ import annotations

from pathlib import Path

from chanakya import settings

_NEEDLE = "answer_key"


def _files(root: Path, *suffixes: str) -> list[Path]:
    return [p for p in root.rglob("*") if p.is_file() and p.suffix in suffixes]


def _strip_yaml_comment(line: str) -> str:
    """Drop a YAML line's trailing/whole-line ``#`` comment (a ``#`` is a comment at line start or after
    whitespace; a ``#`` mid-token is not). Config *values* must stay oracle-free, but a comment may
    legitimately cross-reference the oracle for provenance — the invariant is that nothing *opens* it."""
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return ""
    idx = line.find(" #")
    return line if idx == -1 else line[:idx]


def _offenders(files: list[Path], *, strip_comments: bool = False) -> list[str]:
    hits: list[str] = []
    for path in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if strip_comments:
            text = "\n".join(_strip_yaml_comment(ln) for ln in text.splitlines())
        if _NEEDLE in text:
            hits.append(str(path))
    return hits


def test_pipeline_never_references_answer_key() -> None:
    """No module under ``chanakya/`` may reference the oracle (import-boundary + path grep)."""
    chanakya_src = settings.repo_root() / "backend" / "chanakya"
    offenders = _offenders(_files(chanakya_src, ".py"))
    assert not offenders, (
        f"pipeline modules reference '{_NEEDLE}' (would make acceptance circular): {offenders}"
    )


def test_config_never_references_answer_key() -> None:
    """No ``config/*.yaml`` may *functionally* reference the oracle (comment cross-refs excluded).

    A config value that named ``answer_key.json`` would let the pipeline load the graded verdicts; a
    provenance comment (e.g. "value sourced from answer_key.json") does not open the file, so comments are
    stripped before the check — the invariant is that the oracle is never *read* by the pipeline.
    """
    config_src = settings.config_dir()
    offenders = _offenders(_files(config_src, ".yaml", ".yml"), strip_comments=True)
    assert not offenders, f"config values reference '{_NEEDLE}': {offenders}"


def test_frozen_bundles_never_reference_answer_key() -> None:
    """The pre-extracted claim bundles (pipeline input) must not carry the oracle either."""
    claims_root = settings.corpus_dir() / "scenarios"
    bundles = [p for p in claims_root.rglob("claims/*.json") if p.is_file()]
    offenders = _offenders(bundles)
    assert not offenders, f"frozen claim bundles reference '{_NEEDLE}': {offenders}"


def test_answer_key_is_read_only_where_allowed() -> None:
    """Sanity floor: the oracle *is* referenced under the two EVAL-owned trees (guard is not vacuous)."""
    backend = settings.repo_root() / "backend"
    readers = _offenders(_files(backend / "eval", ".py") + _files(backend / "tests" / "acceptance", ".py"))
    assert readers, "expected eval/ or tests/acceptance/ to reference the oracle — guard would be vacuous"
