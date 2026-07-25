"""Gold-side tooling owned by the DATA hand.

The labeled slice (``tmp/spike-rk/gold/claim-gold.json``, ``sub-oracle.json``) was authored for the
RK-SPIKE identity re-key, in a schema of its own. The bake-off scorer declares a different one and
refuses to guess. :mod:`eval.gold.adapter` is the translation between them — and, because the gold
encodes several things structurally that the scorer expects as fields, it is a *decode*, not a rename.

The two ``.bakeoff.json`` files it produces are **derived artefacts**, regenerated with::

    cd backend && python -m eval.gold        # → tmp/spike-rk/gold/*.bakeoff.json, byte-identical

so a reviewer never has to trust the committed copies. Nothing here imports the scorer: the negative-gold
hooks (:func:`~eval.gold.adapter.trap_avoidance`, :func:`~eval.gold.adapter.identity_over_read`,
:func:`~eval.gold.adapter.precision_exclusions`) take plain :class:`~eval.gold.adapter.EmittedSpan`
records, so the gold side and the scoring side cannot silently redefine each other.
"""

from .adapter import (
    EmittedSpan,
    adapt_claim_gold,
    adapt_sub_oracle,
    decode_span,
    identity_over_read,
    normalize_text,
    precision_exclusions,
    strip_annotator_locator,
    trap_avoidance,
)

__all__ = [
    "EmittedSpan",
    "adapt_claim_gold",
    "adapt_sub_oracle",
    "decode_span",
    "identity_over_read",
    "normalize_text",
    "precision_exclusions",
    "strip_annotator_locator",
    "trap_avoidance",
]
