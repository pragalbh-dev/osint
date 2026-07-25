"""The comparison unit: a **surface claim** — the model-agnostic shape both sides are reduced to.

A gold label and a live ``ClaimRecord`` are not the same object: the gold is a human's reading of a
document, the record is the pipeline's. Scoring them against each other requires one shape that keeps
only what a *claim* is — its form, its polarity, its predicate, its role surfaces, and where in the
document it was read from — and drops everything that is an artefact of our pipeline (ids, confidences,
resolution, timestamps). Reducing to that shape is what makes the comparison about the model rather than
about our id-minting.

Nothing here scores anything; it only normalises. The scoring policy lives in :mod:`matcher`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from chanakya.schemas import ClaimRecord

#: The four A7 discriminator slots, in a fixed order so reports are stable.
DISCRIMINATOR_SLOTS: tuple[str, ...] = ("operator", "geography", "designation", "time")

_WS = re.compile(r"\s+")
_SEP = re.compile(r"[-_/]+")
_PUNCT = re.compile(r"[^\w\s]+", re.UNICODE)


def normalize_surface(text: str | None) -> str:
    """Casefold, unify separators to spaces, drop punctuation, collapse whitespace.

    Deliberately blunt: it removes only differences no reader would call a different claim. It does not
    stem, lemmatise, expand abbreviations or consult an alias table — an alias-aware normaliser would
    quietly hand the extractor credit for resolution work it did not do.
    """
    if not text:
        return ""
    lowered = str(text).casefold()
    lowered = _SEP.sub(" ", lowered)
    lowered = _PUNCT.sub(" ", lowered)
    return _WS.sub(" ", lowered).strip()


def normalize_predicate(text: str | None) -> str:
    """Predicate normalisation — the same rule as a surface (``supplies-component`` ≡ ``supplies component``)."""
    return normalize_surface(text)


@dataclass(frozen=True)
class SpanRef:
    """Where a claim was read from — one document locator, reduced to what can be compared."""

    file: str
    span: tuple[int, int] | None = None
    page: int | None = None
    row: int | None = None
    line: int | None = None
    region: str | None = None

    @property
    def char_addressable(self) -> bool:
        """Can this ref be sliced out of a text document? (Image/PDF-page refs cannot.)"""
        return self.span is not None

    def iou(self, other: SpanRef) -> float | None:
        """Intersection-over-union of two char spans in the same file; ``None`` if not comparable."""
        if self.file != other.file or self.span is None or other.span is None:
            return None
        a0, a1 = sorted(self.span)
        b0, b1 = sorted(other.span)
        inter = max(0, min(a1, b1) - max(a0, b0))
        union = max(a1, b1) - min(a0, b0)
        if union <= 0:
            return 1.0 if inter == 0 and a0 == b0 else 0.0
        return inter / union


@dataclass(frozen=True)
class SurfaceClaim:
    """One claim reduced to what is comparable across extractors.

    ``roles`` is the heart of it: ``subject``/``object`` for a triple, ``name`` for an entity,
    ``participant:0…`` for an event. Matching compares role-to-role, so a claim that gets the subject
    right and the object wrong is not silently half-credited by a blended string similarity.
    """

    key: str                     # stable identifier for reporting (gold_id, or claim_id)
    source_id: str
    form: str                    # "triple" | "entity" | "event"
    polarity: str
    roles: dict[str, str]
    predicate: str | None = None
    entity_type: str | None = None
    refs: tuple[SpanRef, ...] = ()
    kind: str | None = None
    referent_id: str | None = None
    coref_cluster: str | None = None
    discriminators: dict[str, str | None] = field(default_factory=dict)
    attributes: dict[str, Any] = field(default_factory=dict)

    def role_surfaces(self) -> list[str]:
        return [v for _, v in sorted(self.roles.items())]


# ── from a live ClaimRecord ────────────────────────────────────────────────────────────────────────

def _refs_of(claim: ClaimRecord) -> tuple[SpanRef, ...]:
    out: list[SpanRef] = []
    for ref in claim.doc_refs():
        out.append(SpanRef(
            file=ref.file,
            span=tuple(ref.span) if ref.span else None,  # type: ignore[arg-type]
            page=ref.page, row=ref.row, line=ref.line, region=ref.region,
        ))
    return tuple(out)


def from_claim_record(claim: ClaimRecord) -> SurfaceClaim:
    """Reduce a pipeline ``ClaimRecord`` to a :class:`SurfaceClaim`.

    ``referent_id`` is carried through untouched. RK-COREF (S3) has landed, so it is now filled whenever
    extraction pass 2 ran and a cluster was accepted — and still ``None`` when the pass was dormant or the
    model bound nothing, which is precisely how the coref-binding metric knows its substrate is absent
    rather than scoring an empty clustering as perfect or as zero.
    """
    payload = claim.payload
    roles: dict[str, str] = {}
    predicate: str | None = None
    entity_type: str | None = None

    if payload.form == "triple":
        roles = {"subject": payload.subject or "", "object": payload.object or ""}
        predicate = payload.predicate
    elif payload.form == "entity":
        roles = {"name": payload.name or ""}
        entity_type = payload.entity_type
    else:  # event
        roles = {f"participant:{i}": p for i, p in enumerate(payload.participants or [])}
        predicate = payload.event_type

    return SurfaceClaim(
        key=claim.claim_id,
        source_id=claim.source_id,
        form=payload.form,
        polarity=claim.polarity,
        roles=roles,
        predicate=predicate,
        entity_type=entity_type,
        refs=_refs_of(claim),
        kind=claim.kind,
        referent_id=claim.referent_id,
        attributes=dict(claim.attributes or {}),
    )


__all__ = [
    "DISCRIMINATOR_SLOTS",
    "SpanRef",
    "SurfaceClaim",
    "from_claim_record",
    "normalize_predicate",
    "normalize_surface",
]
