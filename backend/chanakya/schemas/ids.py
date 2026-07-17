"""Human-readable ID schemes.

Claim IDs are human-readable by design, not UUIDs: Anthropic notes readable IDs measurably cut
hallucination in tool-calling, and they double as the one-click provenance label in the UI
(spine/09 tool hygiene; master §4.2). Canonical form is ``<doc>-<locator>`` — e.g. ``d05-row12``
(customs manifest row 12), ``d02-l3`` (ISPR PR line 3), ``d07-img1`` (satellite image region 1).

These are *constructors/validators*, pure and offline. INGEST uses them when it mints claim IDs;
F0 fixtures use them so the golden data reads like real data.
"""

from __future__ import annotations

import re

_CLAIM_ID_RE = re.compile(r"^[a-z0-9]+-[a-z0-9]+(-[a-z0-9]+)*$")


def make_claim_id(doc: str, locator: str, *, index: int | None = None) -> str:
    """Build a readable claim ID, e.g. ``make_claim_id("d05", "row12") -> 'd05-row12'``.

    ``index`` disambiguates multiple claims sharing one locator (``d02-l3-2``).
    """
    parts = [doc, locator]
    if index is not None:
        parts.append(str(index))
    cid = "-".join(p.strip().lower().replace("_", "-") for p in parts if p)
    if not _CLAIM_ID_RE.match(cid):
        raise ValueError(f"malformed claim_id {cid!r} (expect '<doc>-<locator>' kebab, e.g. 'd05-row12')")
    return cid


def is_claim_id(value: str) -> bool:
    """True if ``value`` matches the readable claim-id shape."""
    return bool(_CLAIM_ID_RE.match(value))
