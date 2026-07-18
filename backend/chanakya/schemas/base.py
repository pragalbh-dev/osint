"""Shared pydantic base classes.

Two base configs, deliberately different (master §4.2 "shape vs. normalization"):

* ``Record`` — evidence/decision-log + view records. **Frozen shapes.** Extra fields are
  *forbidden* so a typo or a drifted contract fails loudly rather than silently. **No network,
  parse, clock, or RNG in any validator** — validators here are pure structural checks only, so
  that ``rebuild()`` re-instantiating records from the log stays LLM/network-free (gate G1).
* ``ConfigModel`` — the eight config surfaces. Extra fields are *allowed*: DATA-C authors the
  content and may add knobs without an F0-amendment, as long as the load-bearing typed fields
  below stay put. All numeric knobs live in config, never in code (gate G6).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class Record(BaseModel):
    """Base for immutable log records + derived view elements. Strict: no unknown fields."""

    model_config = ConfigDict(extra="forbid", frozen=False, populate_by_name=True)


class ConfigModel(BaseModel):
    """Base for the config surfaces. Permissive: DATA-C may add fields (hot-config, master §4.4)."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)
