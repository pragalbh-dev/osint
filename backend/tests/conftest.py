"""Shared pytest fixtures — expose the golden fixtures to every test/gate.

Everything is built fresh per test (in-memory logs) so tests never share mutable state.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from chanakya import settings
from chanakya.config import ConfigStore
from chanakya.schemas import GraphView
from chanakya.store import DecisionLog, EvidenceLog
from tests.fixtures import loaders

# ── running the suite against a flag-ON deployment (RK-COREF / S3) ─────────────────────────────────
#
# The stage rule (plan §5a-bis) says byte-identity is S1's invariant ONLY: for S2/S3/S4 an *unchanged*
# graph is a FAILURE signal, because those stages change what the graph contains. Verifying that needs a
# run with the stage flag actually on — and doing that by editing ``config/resolution.yaml`` in the tree is
# both un-repeatable and dangerous (a flipped default is one forgotten `git checkout` away from shipping).
#
# So the switch is a pytest option that points the process at a **shadow config dir**: a throwaway copy of
# ``config/`` with the one key flipped, comments and every other file byte-identical. Only ``config_dir`` is
# redirected — not the repo root — because ``repo_root`` also resolves cited *documents*, and a doc path that
# resolved out of a shadow tree would trip the "must not read outside the repo" guard and fail four API
# quote tests for a reason that has nothing to do with the flag. Two consequences that matter:
#
#   * the working tree is never touched, so an assertion about what the repo *ships* (read straight off
#     ``config/resolution.yaml``) stays true in BOTH directions and cannot be spoofed by the run mode;
#   * a test that wants a flag-OFF baseline has to say so explicitly rather than lean on ambient config —
#     which is what a flag-off baseline should have been doing all along.

_FLAG_SECTION = "earned_identity:"
_FLAG_OFF, _FLAG_ON = "enabled: false", "enabled: true"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--earned-identity",
        action="store",
        default="shipped",
        choices=("shipped", "on"),
        help="'on' runs the whole suite against a shadow config dir with the RK-COREF (S3) stage flag "
             "resolution.earned_identity.enabled forced true. The working tree is never modified.",
    )


def _flag_on(resolution_yaml: str) -> str:
    """``earned_identity.enabled: false`` → ``true``, comments and every other key untouched."""
    lines = resolution_yaml.splitlines(keepends=True)
    inside = False
    for i, line in enumerate(lines):
        if line.startswith(_FLAG_SECTION):
            inside = True
            continue
        if inside:
            if line.strip() and not line.startswith((" ", "\t", "#")):
                break  # left the block without finding it
            if line.strip() == _FLAG_OFF:
                lines[i] = line.replace(_FLAG_OFF, _FLAG_ON)
                return "".join(lines)
    raise RuntimeError(
        f"--earned-identity=on could not find '{_FLAG_SECTION} … {_FLAG_OFF}' in config/resolution.yaml; "
        "the flag was renamed or already flipped — fix this hook rather than guessing."
    )


def pytest_configure(config: pytest.Config) -> None:
    """Redirect ``settings.config_dir`` at the flipped copy, before any test module is imported.

    ``pytest_configure`` runs ahead of collection, so the handful of test modules that do
    ``from chanakya.settings import config_dir`` bind the redirected function too — no module is left
    reading the shipped file by accident.
    """
    if config.getoption("--earned-identity") != "on":
        return
    shadow = Path(tempfile.mkdtemp(prefix="chanakya-s3-flag-on-")) / "config"
    shutil.copytree(settings.config_dir(), shadow)
    target = shadow / "resolution.yaml"
    target.write_text(_flag_on(target.read_text(encoding="utf-8")), encoding="utf-8")
    settings.config_dir = lambda: shadow


@pytest.fixture
def golden_evidence() -> EvidenceLog:
    return loaders.golden_evidence_log()


@pytest.fixture
def golden_decision() -> DecisionLog:
    return loaders.golden_decision_log()


@pytest.fixture
def golden_config() -> ConfigStore:
    return loaders.golden_config_store()


@pytest.fixture
def golden_view() -> GraphView:
    return loaders.golden_view()
