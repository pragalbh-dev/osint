"""CREDIBILITY stage — the Confidence Resolver + independence grouping + status machine (owned by SCORE).

Three pure, config-driven stages of ``rebuild()`` (master §4.3), split across submodules and re-exported
here so the pipeline's frozen ``from chanakya.credibility import …`` keeps working:

* ``scoring.score_claims`` — per-claim ``R(source) × Π(integrity) × freshness`` (spine/04 §C).
* ``independence.group_by_independence`` — three-axis (origin/discipline/interest) clustering (§3.5).
* ``status.assign_status`` — noisy-OR pooling + the confirmed/probable/possible/insufficient/
  contradicted/stale gate machine (§3.4).

**No scoring literal lives in this package (gate G6):** every weight, penalty, threshold, half-life,
decay base, and look-count comes from ``config.credibility`` through F0's live store. **No LLM / network /
clock / RNG (gate G1):** freshness reads the clock-free ``as_of`` (``chanakya.timeref``); the soft
"too-clean" narrative is produced upstream at ingest, not here.
"""

from __future__ import annotations

from .independence import group_by_independence
from .scoring import assertion_freshness, score_claims
from .status import assign_status

__all__ = ["assertion_freshness", "assign_status", "group_by_independence", "score_claims"]
