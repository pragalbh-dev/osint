"""Human-readable ID schemes — **the two atom levels of the evidence layer** (plan §4 A1).

Claim IDs are human-readable by design, not UUIDs: Anthropic notes readable IDs measurably cut
hallucination in tool-calling, and they double as the one-click provenance label in the UI
(spine/09 tool hygiene; master §4.2). Canonical form is ``<doc>-<locator>`` — e.g. ``d05-row12``
(customs manifest row 12), ``d02-l3`` (ISPR PR line 3), ``d07-img1`` (satellite image region 1).

**Atoms are minted here and only at ingest** (spine/13 §8: "only one layer mints, the other derives";
gate G17). Two levels exist, and they are *different kinds of thing*:

* **The claim atom** — the per-mention addressing bedrock. It is the **canonical ``claim_id``**, the one
  assigned by :func:`chanakya.ingest.dedup.assign_claim_ids`; the ids stamped at ``ClaimRecord``
  construction are *provisional* (unique only within one extraction call) and are reassigned there. A
  claim atom is immutable once appended and **never splits or merges**: a correction is an appended
  retraction, not an edit. Everything downstream that must survive a re-key — analyst decisions, walls,
  node identity (S4) — addresses a claim atom, never a derived node id and never a name.
* **The referent atom** — one per **document-local coreference cluster**, minted at ingest in **S3** when
  coreference becomes a required tier. It is a *grouping signal* the rebuild consults and **may decline**
  (D-13.18), never the address of a node: a knowledge node is a derived grouping of **claim** atoms
  (A1/A5, claim-atom-primary). Declining a referent grouping de-groups to claim-atom granularity and
  raises for an analyst — no atom ever splits.

The two namespaces are **disjoint by construction**: a referent id carries the ``ref:`` prefix and a
claim id may not contain ``:``, so one can never be silently passed where the other is expected (the
same reason ``ent:`` / ``event:`` are prefixed). Both share one normalisation rule — :func:`make_claim_id`
builds the stem for both — so the two schemes cannot drift apart.

These are *constructors/validators*, pure and offline. INGEST uses them when it mints atoms;
F0 fixtures use them so the golden data reads like real data.
"""

from __future__ import annotations

import re

#: The prefix that separates the referent-atom namespace from the claim-atom namespace.
REFERENT_PREFIX = "ref:"

_CLAIM_ID_RE = re.compile(r"^[a-z0-9]+-[a-z0-9]+(-[a-z0-9]+)*$")
_REFERENT_ID_RE = re.compile(rf"^{re.escape(REFERENT_PREFIX)}[a-z0-9]+-[a-z0-9]+(-[a-z0-9]+)*$")


# ── the claim atom ───────────────────────────────────────────────────────────────────────────────

def make_claim_id(doc: str, locator: str, *, index: int | None = None) -> str:
    """Build a readable claim ID, e.g. ``make_claim_id("d05", "row12") -> 'd05-row12'``.

    ``index`` disambiguates multiple claims sharing one locator (``d02-l3-2``).

    The **canonical** value this produces inside :func:`chanakya.ingest.dedup.assign_claim_ids` is *the
    claim atom*; the same function called at ``ClaimRecord`` construction produces a provisional id that
    dedup later reassigns. Callers must live under ``chanakya/ingest/`` — minting inside ``rebuild()``
    would make the evidence layer a function of the derived view (gate G17).
    """
    parts = [doc, locator]
    if index is not None:
        parts.append(str(index))
    cid = "-".join(p.strip().lower().replace("_", "-") for p in parts if p)
    if not _CLAIM_ID_RE.match(cid):
        raise ValueError(f"malformed claim_id {cid!r} (expect '<doc>-<locator>' kebab, e.g. 'd05-row12')")
    return cid


def is_claim_id(value: str) -> bool:
    """True if ``value`` matches the readable claim-id shape (and is therefore *not* a referent id)."""
    return bool(_CLAIM_ID_RE.match(value))


# ── the referent atom (minted in S3; the constructor lands here in S1, uninvoked) ────────────────

def make_referent_id(doc: str, cluster: str, *, index: int | None = None) -> str:
    """Build a readable referent-atom ID for one document-local coreference cluster.

    ``make_referent_id("d10", "c1") -> 'ref:d10-c1'``. The stem is built by :func:`make_claim_id`, so the
    two schemes share one normalisation rule and cannot drift; the ``ref:`` prefix keeps the namespaces
    disjoint (``is_claim_id`` is False for every referent id, and vice versa).

    **Not invoked anywhere yet.** Referents are minted at ingest in RK-COREF (S3), when the coreference
    pass becomes a required tier and there is a cluster grain to mint against; S1 only freezes the
    constructor and the (dormant) ``ClaimRecord.referent_id`` field it will populate. Like a claim atom,
    a referent atom is minted **once**, at ingest, and never re-minted (D-13.11).
    """
    return f"{REFERENT_PREFIX}{make_claim_id(doc, cluster, index=index)}"


def is_referent_id(value: str) -> bool:
    """True if ``value`` matches the referent-atom shape (``ref:<doc>-<cluster>``)."""
    return bool(_REFERENT_ID_RE.match(value))
