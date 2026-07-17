"""Path + runtime settings resolution.

The app resolves ``config/`` and ``corpus/`` via a repo-root path defaulting to the actual
repository root (master §4.1 rooting convention); the Docker build COPYs them into the image.
Override with ``CHANAKYA_ROOT`` (deploy) so the same code works in a container where the layout
differs. Nothing here reads secrets — those live in ``.env`` and are read by INGEST/agent only.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

# backend/chanakya/settings.py -> parents[2] == repo root (…/osint)
_DEFAULT_ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def repo_root() -> Path:
    """Repository root; ``CHANAKYA_ROOT`` overrides for containerised layouts."""
    override = os.environ.get("CHANAKYA_ROOT")
    return Path(override).resolve() if override else _DEFAULT_ROOT


def config_dir() -> Path:
    """Directory holding the seven pipeline YAML files (DATA-C content)."""
    return repo_root() / "config"


def corpus_dir() -> Path:
    """Directory holding the frozen scenario corpus + pre-extracted claim bundles."""
    return repo_root() / "corpus"


def data_dir() -> Path:
    """Writable runtime dir for the SQLite logs (container-local copy at runtime)."""
    override = os.environ.get("CHANAKYA_DATA_DIR")
    return Path(override).resolve() if override else repo_root() / "backend" / ".data"
