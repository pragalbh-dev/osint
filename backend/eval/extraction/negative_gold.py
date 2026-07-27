"""The harness side of the gold's **negative** rows — the one place the scorer consumes them.

WHY THIS MODULE EXISTS
──────────────────────
The labeled slice types its negative rows into four classes, and they do not mean the same thing to a
score:

* ``not_a_claim``  — a span that asserts nothing. Emitting a claim here is **fabrication**: it must cost
  precision *and* it is the substrate of the ``trap_avoidance`` line.
* ``anti_coref``   — a true sentence whose two mentions must not be *bound*. Emitting a claim over it is
  correct reading; the error would be a binding. **Neutral for precision.**
* ``ambiguous``    — the page refuses to resolve a pair. A non-identity claim over the span is correct
  reading; asserting ``same-as``/``distinct-from`` is an over-read. **Neutral for precision** except for
  the identity assertion, which :func:`~eval.gold.adapter.identity_over_read` scores.
* ``unmodelled``   — the document states something the ontology cannot express. The gold's own vocabulary
  calls this "a finding, not a failure". **Neutral for precision.**

Precision is ``matched / extracted``, so *every* unpaired emission costs the candidate whatever span it
sits on. That is right for ``not_a_claim`` and wrong for the other three — and the wrongness **does not
cancel between candidates**: it scales with how much of a document a model reads, so it systematically
favours the terser extractor, on a line (``surface_f1``) that carries weight 3.0. That is the same defect
class as the composite-direction bug this harness already fixed, where a fabricating model outscored a
clean one.

THE ONE RULE THIS MODULE FOLLOWS
────────────────────────────────
**The gold owner defines the semantics; this module only supplies the observations.** Every verdict below
comes from :mod:`eval.gold.adapter`'s declared hooks — :func:`~eval.gold.adapter.precision_exclusions`,
:func:`~eval.gold.adapter.trap_avoidance`, :func:`~eval.gold.adapter.identity_over_read`. Nothing here
re-derives "is this span neutral", because two private copies of that definition would drift and the
drift would be invisible in every number the scorecard prints. The trap rule in particular is *not*
re-implemented: a trap hit requires the emission to be **unpaired against positive gold** as well as
overlapping the trap span, because one trap span overlaps a positive claim's span and a bare-overlap test
charges an honest model for reading it correctly.

THE TWO THINGS THIS MODULE MUST GET RIGHT ITSELF
────────────────────────────────────────────────
1. **The file namespace.** The gold cites documents by their repo-relative *path*; the ingest lane cites
   whatever locator the driver put on ``DocInput.file``. The only component guaranteed common is the file
   name, so that is the join key — one rule, applied to both sides, with no fallback chain. Emitted spans
   are translated into the gold's own file strings before any hook is called, so the hooks keep comparing
   ``e.file == ref["file"]`` exactly as they were written to.
2. **Refusing a vacuous measurement.** If the join finds nothing in common, every hook returns "no hits"
   — which reads as *perfect* trap avoidance and *zero* exclusions. That is the worst possible failure:
   silent, flattering, and indistinguishable from a clean run. :meth:`NegativeGold.alignment` detects it
   and the metric reports ``unavailable``, which (``trap_avoidance`` being a declared non-negotiable)
   blocks any winner until an operator fixes the join.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval.gold.adapter import (
    NEGATIVE_GOLD_SEMANTICS,
    EmittedSpan,
    identity_over_read,
    precision_exclusions,
    trap_avoidance,
)

from .matcher import MatchResult
from .surface import SurfaceClaim

#: The declared classes, in the adapter's own order. Read from the adapter so a new class cannot appear
#: in the gold and be silently ignored here.
NEGATIVE_CLASSES: tuple[str, ...] = tuple(NEGATIVE_GOLD_SEMANTICS)

#: The class whose spans are genuine false positives — the fabrication line. Never excluded.
TRAP_CLASS = "not_a_claim"

#: What a missing negative-gold block means, spelled out where the metric prints it.
NOT_DECLARED = (
    "the labeled slice declares no typed negative gold (no `negative_gold` block), so there are no traps "
    "to stay silent at and nothing is declared neutral for precision. Not a candidate's score and not a "
    "zero — the reference side of this measurement does not exist in this slice."
)

#: What a namespace mismatch means. Loud on purpose: it is the one failure that would otherwise read as a
#: flawless run.
NO_OVERLAP = (
    "NO NEGATIVE-GOLD OVERLAP: not one emitted claim cites a document the labeled negative rows are "
    "annotated on, so every hook would report zero hits — which reads as PERFECT trap avoidance and ZERO "
    "precision exclusions. That is a join failure, not a result. Check that the documents handed to the "
    "runner are the labeled slice and that their `file` locators share a file name with the gold's."
)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The loaded negative gold
# ══════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Alignment:
    """Can the negative gold be consulted against this emission set at all?"""

    usable: bool
    reason: str
    #: File names the two sides agree on — the evidence for ``usable``, printable in a report.
    shared_files: tuple[str, ...] = ()

    @property
    def blocking_reason(self) -> str:
        return "" if self.usable else self.reason


class NegativeGold:
    """The adapted file's typed negative rows, plus the translation into the gold's file namespace.

    Holds the adapted mapping itself rather than a re-modelled copy: the adapter's hooks take
    ``adapted`` and read ``adapted["negative_gold"][bucket]["rows"]``, so keeping the mapping intact is
    what guarantees the scorer and the gold cannot hold two different ideas of what a class means.
    """

    __slots__ = ("_payload", "_by_name", "declared", "absent_reason")

    def __init__(self, payload: Mapping[str, Any], *, declared: bool, absent_reason: str = "") -> None:
        self._payload = payload
        self.declared = declared
        self.absent_reason = absent_reason
        # basename → the file string the gold itself uses. Built once; the join key is the file NAME.
        self._by_name: dict[str, str] = {}
        for bucket in NEGATIVE_CLASSES:
            for row in payload["negative_gold"][bucket]["rows"]:
                gold_file = str(row["doc_ref"]["file"])
                self._by_name.setdefault(Path(gold_file).name, gold_file)

    # ── what the hooks consume ────────────────────────────────────────────────────────────────────

    @property
    def payload(self) -> Mapping[str, Any]:
        """The adapted mapping, exactly as the adapter's hooks expect it."""
        return self._payload

    def rows(self, bucket: str) -> list[Mapping[str, Any]]:
        return list(self._payload["negative_gold"][bucket]["rows"])

    def counts(self) -> dict[str, int]:
        return {bucket: len(self.rows(bucket)) for bucket in NEGATIVE_CLASSES}

    @property
    def gold_files(self) -> tuple[str, ...]:
        return tuple(sorted(set(self._by_name.values())))

    def file_alias(self, file: str) -> str:
        """Translate one of *our* locators into the gold's own file string, by file name.

        Returns the input unchanged when the gold annotates nothing on that file name — which is how a
        namespace mismatch stays *visible* to :meth:`alignment` instead of being papered over.
        """
        return self._by_name.get(Path(file).name, file)

    # ── the guard against a vacuous measurement ───────────────────────────────────────────────────

    def alignment(self, emitted: Sequence[EmittedSpan]) -> Alignment:
        """Do the emitted spans and the negative rows live in the same file namespace?"""
        if not self.declared:
            return Alignment(False, self.absent_reason or NOT_DECLARED)
        if not any(self.counts().values()):
            return Alignment(False, NOT_DECLARED)
        if not emitted:
            return Alignment(False, "the run emitted no claim carrying a document locator, so there is "
                                    "nothing to check against the labeled negative rows")
        ours = {e.file for e in emitted}
        shared = sorted(ours & set(self.gold_files))
        if not shared:
            return Alignment(False, NO_OVERLAP)
        return Alignment(True, "", tuple(shared))

    # ── the three hooks, each consumed and never re-implemented ────────────────────────────────────

    def traps(self, emitted: Sequence[EmittedSpan]) -> dict[str, Any]:
        return trap_avoidance(self._payload, emitted)

    def identity_over_reads(self, emitted: Sequence[EmittedSpan]) -> dict[str, Any]:
        return identity_over_read(self._payload, emitted)

    def exclusions(self, emitted: Sequence[EmittedSpan]) -> dict[str, Any]:
        return precision_exclusions(self._payload, emitted)

    def excluded_keys(self, emitted: Sequence[EmittedSpan]) -> tuple[str, ...]:
        """The emitted keys the gold declares NEUTRAL for precision — the denominator drop.

        Straight from :func:`~eval.gold.adapter.precision_exclusions`, which has already withheld the
        exclusion from anything that also hit a trap ("the trap wins") and from an identity assertion over
        an ``ambiguous`` pair (scored by ``identity_over_read``, so excusing it too would score one error
        twice in opposite directions).
        """
        found = self.exclusions(emitted)["exclude_from_precision_denominator"]
        return tuple(str(k) for k in found)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Loading
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _validate_rows(bucket: str, rows: Any, path: Path) -> list[Mapping[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError(f"{path}: negative_gold.{bucket}.rows must be an array, got {type(rows).__name__}")
    out: list[Mapping[str, Any]] = []
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: negative_gold.{bucket}.rows[{i}] is not an object")
        if not row.get("gold_id"):
            raise ValueError(f"{path}: negative_gold.{bucket}.rows[{i}] has no 'gold_id'")
        ref = row.get("doc_ref")
        if not isinstance(ref, dict) or not ref.get("file"):
            raise ValueError(
                f"{path}: negative row {row['gold_id']!r} has a doc_ref without a 'file' — a negative row "
                "that cannot be localised silently stops penalising anything"
            )
        span = ref.get("span")
        if not (isinstance(span, (list, tuple)) and len(span) == 2):
            raise ValueError(
                f"{path}: negative row {row['gold_id']!r} has span={span!r}; every negative row must "
                "carry [start, end] char offsets or it can never be overlapped by an emission"
            )
        out.append(row)
    return out


def load_negative_gold(path: str | Path) -> NegativeGold:
    """Load the typed negative gold out of the **adapted claim-gold file**.

    The negative rows live in the same file as the positive claims (:func:`eval.gold.adapter.adapt_claim_gold`
    writes both), so this reads the path the runner was already given rather than inventing a second input
    the operator has to remember.

    A file with no ``negative_gold`` block loads as ``declared=False`` and carries the reason. That is not
    a tolerated shape — it is a *reported* one: ``trap_avoidance`` then reports ``unavailable`` with this
    reason, and because the metric is a declared non-negotiable, an unmeasured fabrication line blocks any
    winner. A malformed block, by contrast, raises: a negative row that cannot be localised would quietly
    stop penalising anything.
    """
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{p}: claim gold must be a JSON object, got {type(raw).__name__}")

    block = raw.get("negative_gold")
    if block is None:
        empty = {"negative_gold": {b: {"rows": []} for b in NEGATIVE_CLASSES}}
        return NegativeGold(empty, declared=False, absent_reason=NOT_DECLARED)
    if not isinstance(block, dict):
        raise ValueError(f"{p}: 'negative_gold' must be an object, got {type(block).__name__}")

    unknown = sorted(set(block) - set(NEGATIVE_CLASSES))
    if unknown:
        raise ValueError(
            f"{p}: negative_gold declares class(es) {unknown} the scorer has no semantics for. The four "
            f"classes it consumes are {list(NEGATIVE_CLASSES)}; a fifth would be scored as nothing at "
            "all, which is how a whole class of negative gold goes missing without a single error."
        )
    missing = [b for b in NEGATIVE_CLASSES if b not in block]
    if missing:
        raise ValueError(
            f"{p}: negative_gold is missing class(es) {missing}. The adapter emits all four; a partial "
            "block means the file was hand-edited, and the scorer will not guess which rows were dropped."
        )

    normalised = {
        "negative_gold": {
            bucket: {**{k: v for k, v in block[bucket].items() if k != "rows"},
                     "rows": _validate_rows(bucket, block[bucket].get("rows"), p)}
            for bucket in NEGATIVE_CLASSES
        }
    }
    return NegativeGold(normalised, declared=True)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Our observations, in the shape the hooks take
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def emitted_spans(
    claims: Sequence[SurfaceClaim], match: MatchResult, negative: NegativeGold,
) -> list[EmittedSpan]:
    """Reduce this run's claims to :class:`~eval.gold.adapter.EmittedSpan` records.

    Three details are load-bearing:

    * ``matched`` is the matcher's own verdict, not a re-derivation. A claim the matcher paired with
      positive gold is *explained* by that gold and can never be a trap hit — the condition that keeps the
      one trap span overlapping a positive claim from charging an honest model.
    * one record **per char-addressable citation**, because a claim citing two spans can land on a
      negative row through either of them, and a claim whose only locators are an image region or a PDF
      page can land on none. The latter is emitted with ``span=None`` (which every hook reads as "no
      overlap") rather than dropped, so nothing silently leaves the accounting.
    * ``file`` is translated into the gold's own file string, so the hooks' ``e.file == ref["file"]`` test
      works without the gold side being rewritten.
    """
    matched_keys = {p.extracted.key for p in match.pairs}
    out: list[EmittedSpan] = []
    for claim in claims:
        matched = claim.key in matched_keys
        addressable = [ref for ref in claim.refs if ref.span is not None]
        if not addressable:
            first = claim.refs[0].file if claim.refs else ""
            out.append(EmittedSpan(key=claim.key, file=negative.file_alias(first), span=None,
                                   matched=matched, predicate=claim.predicate))
            continue
        for ref in addressable:
            assert ref.span is not None
            out.append(EmittedSpan(
                key=claim.key, file=negative.file_alias(ref.file),
                span=(int(ref.span[0]), int(ref.span[1])), matched=matched, predicate=claim.predicate,
            ))
    return out


__all__ = [
    "NEGATIVE_CLASSES",
    "NOT_DECLARED",
    "NO_OVERLAP",
    "TRAP_CLASS",
    "Alignment",
    "NegativeGold",
    "emitted_spans",
    "load_negative_gold",
]
