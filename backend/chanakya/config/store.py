"""The live config store — seeds from ``config/*.yaml``, then serves read + **hot write**.

The hot-config rule (spine/09, DECISIONS "Hot-config / live-rebuild"): nothing a user does in-app
requires a restart. The store holds the config *in process*; the API writes to it; every write bumps
``version``; ``rebuild()`` reads a **snapshot** of the current bundle each time — so a threshold edit
takes effect on the very next rebuild with no restart. Wave-1 modules read config **through this
store**, never from files directly (master §4.4).

Reading is via an immutable snapshot (a deep copy) so a stage can never accidentally mutate shared
config mid-rebuild — which would also be a G2 (determinism) hazard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from chanakya.schemas import CONFIG_SECTIONS, ConfigBundle


class ConfigStore:
    """In-process config bundle with versioned hot writes."""

    def __init__(self, bundle: ConfigBundle | None = None) -> None:
        self._bundle = bundle or ConfigBundle()

    # ── construction ────────────────────────────────────────────────────────────────────────

    @classmethod
    def seed_from(cls, config_dir: Path | str) -> ConfigStore:
        """Seed a store from the eight ``config/*.yaml`` files. Missing files → section defaults.

        Tolerant by design: F0 ships no config *content* (that's DATA-C), so booting against an empty
        or partial ``config/`` must still yield a valid, usable bundle.
        """
        config_dir = Path(config_dir)
        sections: dict[str, Any] = {}
        for name, model in CONFIG_SECTIONS.items():
            path = config_dir / f"{name}.yaml"
            if path.exists():
                raw = yaml.safe_load(path.read_text()) or {}
                sections[name] = model.model_validate(raw)
        return cls(ConfigBundle(version=1, **sections))

    @classmethod
    def from_bundle(cls, bundle: ConfigBundle) -> ConfigStore:
        return cls(bundle)

    # ── reads ────────────────────────────────────────────────────────────────────────────────

    @property
    def version(self) -> int:
        return self._bundle.version

    def snapshot(self) -> ConfigBundle:
        """An immutable deep copy for a rebuild — mutating it can't affect the store (or determinism)."""
        return self._bundle.model_copy(deep=True)

    def get_section(self, name: str) -> Any:
        if name not in CONFIG_SECTIONS:
            raise KeyError(f"unknown config section {name!r}; expected one of {list(CONFIG_SECTIONS)}")
        return getattr(self._bundle, name)

    # ── hot writes (bump version) ──────────────────────────────────────────────────────────────

    def candidate(self, name: str, value: dict[str, Any] | Any) -> ConfigBundle:
        """The bundle a :meth:`set_section` WOULD commit — parsed and versioned, but **not** stored.

        The pre-commit half of the hot-config contract. Pydantic parsing is only the *first* layer of
        validation: the readers that compile a section into its runtime form (``ResolveConfig`` and the
        load-time validators behind it) raise on a section that is structurally valid YAML and semantically
        impossible. Those raise inside ``rebuild()``, i.e. AFTER the section is already live — so an invalid
        POST used to commit, 500, and leave the store holding a section that made every subsequent config
        write and every rebuild 500 too. Hot config bricked until someone re-POSTed a good section, which is
        the exact opposite of "nothing a user does in-app requires a restart".

        Handing the caller a candidate bundle lets it run the full reduction against it and commit only if
        that succeeds. Deliberately not a rollback: a rollback leaves the version bumped twice and a window
        in which the live store holds a section nobody validated.
        """
        if name not in CONFIG_SECTIONS:
            raise KeyError(f"unknown config section {name!r}; expected one of {list(CONFIG_SECTIONS)}")
        model = CONFIG_SECTIONS[name]
        parsed = value if isinstance(value, model) else model.model_validate(value)
        return self._bundle.model_copy(update={name: parsed, "version": self._bundle.version + 1})

    def set_section(self, name: str, value: dict[str, Any] | Any) -> int:
        """Replace a whole section (hot). Returns the new version. Triggers a rebuild upstream."""
        self._bundle = self.candidate(name, value)
        return self._bundle.version

    def commit(self, bundle: ConfigBundle) -> int:
        """Install an already-validated candidate bundle (see :meth:`candidate`). Returns its version."""
        self._bundle = bundle
        return self._bundle.version

    def update_credibility(self, patch: dict[str, Any]) -> int:
        """Shallow-merge a patch into ``credibility`` (the common hot-tune path: weights/thresholds).

        Convenience over ``set_section`` for the demo's "move a slider → rebuild reflects it" flow.
        """
        current = self._bundle.credibility.model_dump()
        for key, val in patch.items():
            if isinstance(val, dict) and isinstance(current.get(key), dict):
                current[key] = {**current[key], **val}
            else:
                current[key] = val
        return self.set_section("credibility", current)
