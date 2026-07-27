"""Translate the hand-labeled RK-SPIKE gold into the shape the bake-off scorer declares.

WHY THIS EXISTS
───────────────
Two files describe the same seven-document slice and cannot talk to each other:

* ``tmp/spike-rk/gold/claim-gold.json`` — ``schema_version: rk-spike-claim-gold/1.0``. Authored by hand
  for the RK-SPIKE identity re-key: ``rows`` of ``row_id``/``doc_id``, a ``predicate`` string whose
  *prefix* encodes what kind of thing the row is, and a ``doc_ref_span`` that is a **quoted string**.
* ``backend/eval/extraction/gold.py`` — wants ``rk-bakeoff-claim-gold/1.x``: a ``claims`` array of
  ``gold_id``/``source_id``, an explicit ``form`` field, and ``doc_ref.span`` as **character offsets**.
  It refuses the spike schema outright, by design ("a mis-read gold file scores every model at zero").

This module is the bridge. It is deliberately **not** a rename pass:

* ``form`` is *decoded* from the predicate prefix, not copied — the spike gold has no ``form`` field.
* ``doc_ref_span`` is *resolved* to real character offsets against the cited document, and every
  derived offset is verified to slice back to the quoted string (byte-exact where the quote is
  byte-exact; otherwise exact under the gold's own documented normalisation — see :func:`normalize_text`).
* the **negative gold is separated out and typed**. 38 of the 125 rows are not claims a model should
  produce: 11 are traps it must stay silent at, 6 are about *binding* rather than about claims, 2 are an
  identity the page refuses to state, and 19 are relations the ontology cannot express. Loading them as
  positives blames every candidate for a loader artefact. Measured, on the scorer as built: a model
  emitting exactly the positive gold scores recall **1.0000** through this adapter. Against a mechanical
  125-row load the same model scores **0.5200** (65/125) — and a model that additionally emitted the 22
  attribute rows, which the pipeline cannot express as claims (see ``excluded_from_scoring``), would
  score **0.6960** (87/125). Both are the same artefact; 0.52 is the figure for a candidate emitting
  only what the pipeline can actually produce, so it is the honest statement of what the adapter is worth.
* the four negative classes come with **hooks, not just prose** — :func:`trap_avoidance`,
  :func:`identity_over_read`, :func:`precision_exclusions`. Three of the four classes are declared
  neutral for precision and are **not** neutral until the harness calls them, so the taxonomy says which
  is wired and which is not rather than implying all four are handled.

NOTHING IS DROPPED SILENTLY. Every one of the 125 rows lands in exactly one bucket, the buckets are
reconciled against the gold's own declared counts, and :func:`adapt_claim_gold` raises if they disagree.

THE SEMANTIC CALLS
──────────────────
Each is marked ``SEMANTIC CALL`` at the point it is made, with the reason and, where it could
reasonably go the other way, the alternative. Summary, so a reader does not have to hunt:

S1  ``ENTITY_EXISTS`` → ``form: entity``.                                        (mechanical)
S2  ``ATTR:<attr>`` → **excluded from scoring**, named. The scorer's comparison unit has no attribute
    form, and the pipeline carries attributes inside ``payload.attrs``, which ``from_claim_record``
    drops. Scoring them guarantees 22 false negatives for every candidate.
S3  ``EVENT:<T>`` → ``form: event``; participants parsed out of the ``participants: a; b`` object.
S4  ``same-as`` / ``distinct-from`` → ``form: triple`` with that literal predicate — which is exactly
    what the live pipeline emits for stated identity (``extract.py`` ``triple()``, "identity claims …
    keep the exact predicate they were given").
S5  ``NOT_A_CLAIM``  → negative gold, ``penalise_emission``.
S6  ``ANTI_COREF``   → negative gold, ``penalise_binding`` — NOT emission.
S7  ``AMBIGUOUS``    → negative gold, ``penalise_identity_assertion`` — narrower than either.
S8  ``UNMODELLED``   → **neutral**: excluded from recall AND from precision. Not a model failure.
S9  ``coref_cluster`` is emitted only for the 32 CURATED registry clusters, never for the 16 ad-hoc
    row-bookkeeping tags.
S10 ``kind`` is NOT emitted. The gold does not label it; deriving it from ``evidence_mode`` would
    manufacture a metric that reads ~1.00 for every candidate by construction.
S11 sub-oracle: the 5 ``insufficient-evidence`` edges leave the recall denominator; so do the 5 whose
    endpoint is a surface form rather than a declared node (the scorer's oracle model cannot express
    those), and the one node whose declared type is "NOT a node type".
S12 ``surface_verbatimness`` is REPORTED, not corrected. 16 of the 65 scored claims carry a role surface
    that appears nowhere in their document (a resolved subject, an annotator's slash or locator). The
    tempting fix — strip the annotator sugar, as the coref mentions legitimately do — would truncate the
    surfaces that *are* document text ("transporter-erector-launchers (TELs)"), so the labels stay as
    authored and the ceiling is stated instead. See :func:`_surface_verbatimness`.

DO NOT tune anything here to a result. This module has never seen a candidate's output, and the two
labeled files are read-only inputs — no label is changed, added or removed by any code path below.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The schema this module emits. Must start with ``eval.extraction.gold.CLAIM_GOLD_SCHEMA``.
CLAIM_GOLD_SCHEMA_OUT = "rk-bakeoff-claim-gold/1.0"
SUB_ORACLE_SCHEMA_OUT = "rk-bakeoff-sub-oracle/1.0"

#: The schemas this module accepts as input. Anything else raises rather than being guessed at.
CLAIM_GOLD_SCHEMA_IN = "rk-spike-claim-gold/1."
SUB_ORACLE_SCHEMA_IN = "rk-spike-sub-oracle/1."

#: The A7 discriminator slots, in the scorer's fixed order.
DISCRIMINATOR_SLOTS = ("operator", "geography", "designation", "time")


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Text normalisation — the gold's own, reused verbatim rather than re-invented.
# ══════════════════════════════════════════════════════════════════════════════════════════════════
#
# The DATA hand's 2026-07-25 audit recorded: "125/125 `doc_ref_span` values occur verbatim in their
# cited document (Unicode-normalized: curly quotes, en/em dashes, NBSP, whitespace)". That is the
# normalisation implemented here, and nothing more. It is **character-for-character** (a 1:1 fold) plus
# a whitespace collapse, which is what lets :func:`decode_span` map a normalised offset back onto a raw
# one without guessing.
#
# On this corpus only the whitespace rule actually fires, and it fires on exactly three rows — all in
# ``d05_customs_manifest``, the fixed-width customs table: ``d05-r08`` and ``d05-r20`` (quotes that cross a
# line break / a column gutter, so the document has runs the quote writes as one space) and ``d05-r24``
# (the pasted-email noise block, where the annotator's quote carries runs the document does not). Those
# three are the 122-vs-125 byte-exact gap, and nothing else differs. The Unicode folds are kept anyway:
# they are the documented rule, they are idempotent, and a future re-freeze of a document that
# straightens a dash must not silently unmatch a span.

_UNICODE_FOLD = {
    "‘": "'", "’": "'", "‚": "'", "‛": "'",   # single curly quotes
    "“": '"', "”": '"', "„": '"', "‟": '"',   # double curly quotes
    "‐": "-", "‑": "-", "‒": "-", "–": "-",   # hyphen/figure/en dashes
    "—": "-", "―": "-", "−": "-",                  # em dash, horizontal bar, minus
    " ": " ", " ": " ", " ": " ", " ": " ",   # NBSP and friends
}

_WS_RUN = re.compile(r"\s+")

#: A trailing annotator locator on a curated coref mention — "(Post 3)", "(this report's AOI)". The
#: gold's ``mention_verbatim_note`` states these are annotation, not document text, and that a scorer
#: doing exact match MUST strip them. 13 of the 120 mentions carry one.
_TRAILING_PAREN = re.compile(r"\s*\([^()]*\)\s*$")


def fold_text(text: str) -> str:
    """The 1:1 Unicode fold (curly quotes, dashes, NBSP). Length- and index-preserving."""
    return "".join(_UNICODE_FOLD.get(ch, ch) for ch in text)


def normalize_text(text: str) -> str:
    """The gold's documented span normalisation: Unicode fold, then collapse whitespace, then strip."""
    return _WS_RUN.sub(" ", fold_text(text)).strip()


def strip_annotator_locator(mention: str, document: str | None = None) -> str:
    """Drop a trailing annotator parenthetical from a curated coref mention (``mention_verbatim_note``).

    **Pass the document.** Without it the rule is purely syntactic, and measured against this slice a
    syntactic rule over-strips 8 of the 20 matching mentions — because their trailing parenthetical is
    genuine document text: ``PORT MUHAMMAD BIN QASIM (PQ)``, ``the FT-2000 (sometimes rendered
    FT-2000A)``, ``Baseline imagery (2024-11)``. Truncating those turns a verbatim mention into one no
    exact-match scorer can find, which is the same harm as not stripping the real locators, pointed the
    other way. With the document, the test is factual rather than shape-based: strip only when the mention
    as annotated does **not** occur in its document. On this slice that leaves 12 locators stripped
    (``(Post 3)``, ``(this report's AOI)``) and 8 parentheticals correctly kept.
    """
    if document is not None and normalize_text(mention) in normalize_text(document):
        return mention.strip()
    return _TRAILING_PAREN.sub("", mention).strip()


def _normalized_with_index(text: str) -> tuple[str, list[int]]:
    """``(normalised text, index map)`` where ``map[i]`` is the raw offset normalised char ``i`` came from.

    Whitespace runs collapse to a single space mapped to the run's **first** raw offset. No leading or
    trailing strip happens here — stripping would break the map, and the caller does not need it.
    """
    out: list[str] = []
    index: list[int] = []
    prev_ws = False
    for i, ch in enumerate(text):
        folded = _UNICODE_FOLD.get(ch, ch)
        if folded.isspace():
            if prev_ws:
                continue
            out.append(" ")
            index.append(i)
            prev_ws = True
        else:
            out.append(folded)
            index.append(i)
            prev_ws = False
    return "".join(out), index


class SpanDecodeError(ValueError):
    """A quoted span could not be resolved to character offsets in its cited document."""


def decode_span(doc_text: str, quoted: str, line: int | None = None) -> tuple[int, int]:
    """Resolve a **quoted** gold span to ``(start, end)`` character offsets in ``doc_text``.

    Two occurrences of the same quote exist in this slice (``d02-r01``, ``d05-r14``), so the gold's
    ``doc_ref_line`` — audited as "the line the span starts on" — disambiguates. When ``line`` is given
    and some occurrence starts on it, that occurrence wins; otherwise the first is taken and the
    caller's verification decides whether that is acceptable.

    Raises :class:`SpanDecodeError` rather than returning a wrong-but-plausible offset: an offset that
    slices out the wrong text would show up downstream as a citation-faithfulness failure attributed to
    a model, which is the exact class of silent corruption this bake-off must not commit.
    """
    needle = normalize_text(quoted)
    if not needle:
        raise SpanDecodeError("empty span quote")
    haystack, index = _normalized_with_index(doc_text)

    starts: list[int] = []
    at = haystack.find(needle)
    while at != -1:
        starts.append(at)
        at = haystack.find(needle, at + 1)
    if not starts:
        raise SpanDecodeError(f"span quote does not occur in the cited document: {quoted[:80]!r}")

    def raw_bounds(norm_start: int) -> tuple[int, int]:
        return index[norm_start], index[norm_start + len(needle) - 1] + 1

    chosen = starts[0]
    if line is not None:
        for candidate in starts:
            raw_start, _ = raw_bounds(candidate)
            if doc_text.count("\n", 0, raw_start) + 1 == line:
                chosen = candidate
                break
    start, end = raw_bounds(chosen)

    # The invariant the whole decode exists to guarantee.
    if normalize_text(doc_text[start:end]) != needle:
        raise SpanDecodeError(
            f"derived offsets [{start}:{end}] do not slice back to the quoted span: {quoted[:80]!r}"
        )
    return start, end


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The negative-gold taxonomy — four classes, four different meanings for scoring.
# ══════════════════════════════════════════════════════════════════════════════════════════════════
#
# This is the part that silently corrupts every number if it is got wrong, so it is a declared table
# rather than an if-chain. ``scoring_role`` is the contract the harness consumes; ``how_to_score`` is
# the sentence a human reads in the scorecard.
#
# ``precision_denominator`` used to read as though the exclusions happened by themselves. They do NOT.
# Measured against the scorer as built: precision is ``matched / extracted``, so **every** claim the
# matcher leaves unpaired costs the candidate, whatever span it sits on. That is right for
# ``not_a_claim`` and wrong for the other three — so each class now declares
# ``precision_exclusion_automatic`` (is it already true of the harness?) and ``harness_hook`` (the
# function the harness must call to make it true). Nothing here is asserted as done that is not done.

NEGATIVE_GOLD_SEMANTICS: dict[str, dict[str, str]] = {
    "not_a_claim": {
        # SEMANTIC CALL S5. A span that looks claim-shaped and asserts nothing: a modal about the
        # future, meta-commentary, a refusal, document noise. A model that emits a claim here has
        # fabricated one — the project's cardinal failure. This is the one class that is negative gold
        # in the strict sense: emitting it is WRONG and must cost the candidate something.
        "scoring_role": "penalise_emission",
        "recall_denominator": "excluded",
        "precision_denominator": "included — an emission here is a false positive AND a trap hit",
        "precision_exclusion_automatic": "n/a — this class is meant to cost precision, and does",
        "harness_hook": "eval.gold.adapter.trap_avoidance",
        "how_to_score": (
            "Rate = traps at which the candidate emitted no claim / total traps. A claim hits a trap "
            "when its doc_ref overlaps the trap span AND the matcher left it unpaired against the "
            "positive gold. The unpaired condition is load-bearing, not caution: trap d20-r13's span "
            "overlaps positive claim d20-r14's, so a bare overlap test charges a trap hit to a model "
            "that emitted d20-r14 correctly. Lower is worse; this is the fabrication line at a place "
            "the gold knows the answer."
        ),
    },
    "anti_coref": {
        # SEMANTIC CALL S6. Two mentions that must NOT be bound into one referent, licensed
        # structurally/semantically rather than by a stated distinct-from ("Army Air Defence" the arm
        # vs "a Pakistan Army Air Defence (PAAD) unit" the formation). Emitting a CLAIM over this span
        # is fine — the sentence is real. The error is BINDING. Scoring these as emission traps would
        # punish a model for reading a true sentence.
        "scoring_role": "penalise_binding",
        "recall_denominator": "excluded",
        "precision_denominator": "excluded — emitting a claim here is not an error",
        "precision_exclusion_automatic": (
            "NO — unwired today. The scorer's precision is matched/extracted, so an unpaired claim on "
            "one of these six spans currently costs the candidate. One of the six (d05-r21) overlaps a "
            "positive claim and so is usually paired anyway; the other five are live over-penalties."
        ),
        "harness_hook": "eval.gold.adapter.precision_exclusions",
        "how_to_score": (
            "Over-bind rate = pairs whose two surfaces share a referent_id (or a coref cluster) in the "
            "candidate's output / total pairs. Substrate is S3-dependent, exactly like coref_binding: "
            "report UNAVAILABLE, never 0.00, while referent_id is dormant."
        ),
    },
    "ambiguous": {
        # SEMANTIC CALL S7. The document leaves the pair genuinely unresolved and (in the crown-jewel
        # row d17b-r11) says so in its own voice, naming the missing discriminator. The correct output
        # is the pair surfaced as unresolved — "neither a merge nor a distinct-from". So this is NOT a
        # general emission trap and NOT a plain anti-coref: the specific error is ASSERTING AN IDENTITY
        # EITHER WAY. A model that stays silent on the pair is right; a model that emits `same-as` OR
        # `distinct-from` over the pair has over-read the source.
        #
        # Could go the other way: one could call these unscoreable and exclude them entirely, on the
        # grounds that "surface it as unresolved" is a HITL behaviour with no extraction channel. The
        # narrower reading is kept because the half that IS observable at the extraction layer — did
        # you assert an identity the page refuses to state — is the half the project's non-negotiable
        # rule is about, and it is only 2 rows either way.
        "scoring_role": "penalise_identity_assertion",
        "recall_denominator": "excluded",
        "precision_denominator": "excluded — a non-identity claim over this span is not an error",
        "precision_exclusion_automatic": (
            "NO — unwired today, same as anti_coref: an unpaired non-identity claim on one of these two "
            "spans costs precision until the harness calls the hook."
        ),
        "harness_hook": (
            "eval.gold.adapter.identity_over_read (the penalty) + .precision_exclusions (the exclusion)"
        ),
        "how_to_score": (
            "Over-read rate = pairs over which the candidate emitted a same-as or distinct-from triple "
            "/ total pairs. Silence is the correct answer and scores clean. N=2: report the raw count, "
            "never a rate to two decimals, and never rank on it."
        ),
    },
    "unmodelled": {
        # SEMANTIC CALL S8. The document states a relation or entity the declared ontology cannot
        # express (e.g. "integrated into the CLIAD network" — no C2-network node type, no
        # integrated-into edge). The gold's own vocabulary calls this "a finding, not a failure".
        #
        # So it is NEUTRAL, and neutrality has to be enforced on BOTH sides: excluded from the recall
        # denominator (there is no correct target shape to hit), and excluded from the precision
        # denominator (a model that reads the sentence correctly and emits something off-ontology has
        # not fabricated anything — the pipeline itself has an `_offontology` path for precisely this).
        # Leaving them only out of recall — the tempting half-fix — still charges every candidate a
        # precision penalty for reading correctly.
        "scoring_role": "neutral_exclude",
        "recall_denominator": "excluded",
        "precision_denominator": "excluded — REQUIRES harness wiring; see the report",
        "precision_exclusion_automatic": (
            "NO — unwired today, and this is the class where it bites hardest: 19 rows, of which 11 do "
            "NOT overlap any positive claim, so a model that reads all 19 off-ontology sentences "
            "correctly loses up to 11 precision points for reading correctly."
        ),
        "harness_hook": "eval.gold.adapter.precision_exclusions",
        "how_to_score": (
            "Not scored. Report the count as a coverage finding about the ONTOLOGY, not about any "
            "candidate. If a per-candidate number is wanted, it is 'ontology-gap recognition' and "
            "belongs on the roadmap, not in this bake-off's composite."
        ),
    },
}

#: Identity predicates. Emitting one of these over an ``ambiguous`` pair is the over-read S7 penalises.
IDENTITY_PREDICATES = frozenset({"same-as", "distinct-from"})


@dataclass(frozen=True)
class EmittedSpan:
    """One claim a candidate emitted, reduced to what the negative gold can be checked against.

    Deliberately not the scorer's ``SurfaceClaim``: this module is the gold side and must not import the
    scorer (the scorer already imports nothing from here, and a cycle between the two would let a change
    in one silently redefine the other). The harness builds these from its own claims.

    ``matched`` is the load-bearing field. It is the matcher's verdict — did this claim pair with a
    positive gold claim — and every hook below keys off it, because a claim the matcher paired is
    *explained* by the positive gold and cannot also be a trap hit. See ``how_to_score`` on
    ``not_a_claim`` for the concrete row (d20-r13) that proves the bare-overlap version wrong.
    """

    key: str
    file: str
    span: tuple[int, int] | None = None
    matched: bool = False
    predicate: str | None = None


def _overlaps(span: tuple[int, int] | None, other: Sequence[int]) -> bool:
    if span is None:
        return False
    a0, a1 = sorted(span)
    b0, b1 = sorted((int(other[0]), int(other[1])))
    return min(a1, b1) > max(a0, b0)


def _rows_of(adapted: Mapping[str, Any], bucket: str) -> list[Mapping[str, Any]]:
    return list(adapted["negative_gold"][bucket]["rows"])


def _hits_on(
    adapted: Mapping[str, Any], bucket: str, emitted: Sequence[EmittedSpan],
    *, predicate_filter: frozenset[str] | None = None,
) -> dict[str, list[str]]:
    """``{negative row id: [emitted keys that landed on it]}`` — unpaired emissions only."""
    hits: dict[str, list[str]] = {}
    for row in _rows_of(adapted, bucket):
        ref = row["doc_ref"]
        landed = [
            e.key for e in emitted
            if not e.matched and e.file == ref["file"] and _overlaps(e.span, ref["span"])
            and (predicate_filter is None or (e.predicate or "") in predicate_filter)
        ]
        hits[row["gold_id"]] = sorted(landed)
    return hits


def trap_avoidance(adapted: Mapping[str, Any], emitted: Sequence[EmittedSpan]) -> dict[str, Any]:
    """S5's metric, executable: did the candidate stay silent at the 11 ``not_a_claim`` traps?

    ``rate`` is traps avoided / traps, so higher is better and a fabricator is penalised. Report it as a
    count as well as a rate: N=11, and a rate to two decimals off eleven items reads more precise than it
    is. Returns the per-trap detail so a scorecard can name which trap a candidate fell for.
    """
    hits = _hits_on(adapted, "not_a_claim", emitted)
    fell_for = {k: v for k, v in hits.items() if v}
    total = len(hits)
    return {
        "metric": "trap_avoidance",
        "traps": total,
        "avoided": total - len(fell_for),
        "hit": len(fell_for),
        "rate": (total - len(fell_for)) / total if total else None,
        "hits_by_trap": fell_for,
        "basis": "an unpaired emitted claim whose span overlaps the trap span",
    }


def identity_over_read(adapted: Mapping[str, Any], emitted: Sequence[EmittedSpan]) -> dict[str, Any]:
    """S7's metric, executable: did the candidate assert an identity the page refuses to state?

    Only ``same-as`` / ``distinct-from`` count. A non-identity claim over an ``ambiguous`` span is not an
    error — the sentence is real — so it is filtered out here rather than quietly folded in. N=2: the
    return carries counts, and ``rate`` is ``None`` when there is nothing to divide.
    """
    hits = _hits_on(adapted, "ambiguous", emitted, predicate_filter=IDENTITY_PREDICATES)
    over_read = {k: v for k, v in hits.items() if v}
    total = len(hits)
    return {
        "metric": "identity_over_read",
        "pairs": total,
        "over_read": len(over_read),
        "clean": total - len(over_read),
        "rate": len(over_read) / total if total else None,
        "hits_by_pair": over_read,
        "basis": "an unpaired same-as / distinct-from claim overlapping the ambiguous pair's span",
        "reporting_rule": "N=2 — report the raw count, never a two-decimal rate, and never rank on it",
    }


def precision_exclusions(
    adapted: Mapping[str, Any], emitted: Sequence[EmittedSpan],
) -> dict[str, Any]:
    """The keys the harness must drop from the precision denominator, per class, with the reason.

    Without this call, ``precision = matched / extracted`` charges a candidate for reading an
    off-ontology sentence (``unmodelled``), for reading a true sentence whose two mentions must stay
    apart (``anti_coref``), and for any non-identity claim over an ``ambiguous`` pair. All three are
    declared neutral by the taxonomy above; none of them is neutral until this is wired.

    ``not_a_claim`` is deliberately absent: those emissions SHOULD cost precision. And because the classes
    are annotated on overlapping spans — measured on this slice, 2 ``unmodelled`` spans overlap an
    ``ambiguous`` one, and 8 of the 19 ``unmodelled`` spans overlap a *positive* claim's span — one emitted
    claim can qualify for an exclusion and hit a trap at the same time. **The trap wins:** it is never
    excused here, and it is not double-charged either, because :func:`trap_avoidance` is the one metric
    that scores it.
    """
    penalised = {k for hit in _hits_on(adapted, "not_a_claim", emitted).values() for k in hit}
    excluded: dict[str, list[str]] = {}
    for bucket in ("anti_coref", "unmodelled"):
        keys = {k for hit in _hits_on(adapted, bucket, emitted).values() for k in hit}
        excluded[bucket] = sorted(keys - penalised)
    ambiguous_identity = {
        k for hit in _hits_on(adapted, "ambiguous", emitted,
                              predicate_filter=IDENTITY_PREDICATES).values() for k in hit
    }
    ambiguous_all = {k for hit in _hits_on(adapted, "ambiguous", emitted).values() for k in hit}
    # An identity assertion over an ambiguous pair is penalised by identity_over_read; excluding it from
    # precision as well would be one error scored twice in opposite directions.
    excluded["ambiguous"] = sorted(ambiguous_all - ambiguous_identity - penalised)
    return {
        "exclude_from_precision_denominator": sorted({k for v in excluded.values() for k in v}),
        "by_class": excluded,
        "also_a_trap_hit_so_not_excused": sorted(penalised & {
            k for bucket in ("anti_coref", "unmodelled", "ambiguous")
            for hit in _hits_on(adapted, bucket, emitted).values() for k in hit
        }),
        "note": "not_a_claim is deliberately NOT excluded — those emissions must cost precision.",
    }


#: Predicate prefix → negative-gold bucket.
_NEGATIVE_PREFIX = {
    "NOT_A_CLAIM": "not_a_claim",
    "ANTI_COREF": "anti_coref",
    "AMBIGUOUS": "ambiguous",
    "UNMODELLED": "unmodelled",
}

#: Why the ``ATTR:`` rows are excluded from scoring altogether. SEMANTIC CALL S2.
ATTRIBUTE_EXCLUSION_REASON = (
    "The scorer's comparison unit (SurfaceClaim) has exactly three forms — triple, entity, event — and "
    "the pipeline never emits an attribute as a claim: attributes ride inside payload.attrs on the "
    "entity/event claim they describe, and from_claim_record() drops payload.attrs entirely. So there "
    "is no extracted object these 22 rows could ever pair with. Encoding them as triples (predicate = "
    "the attribute name) would load cleanly and then produce 22 guaranteed false negatives for every "
    "candidate, dragging a perfect model's recall from 1.00 to 0.75 for a representation choice the "
    "harness cannot see. They are excluded and NAMED here rather than scored. This could go the other "
    "way — carrying them as triples costs every candidate the same, so a RANKING would survive — but "
    "the absolute number would be a lie, and attribute capture is partly already measured, on the raw "
    "tool payload, by the A7 discriminator metrics."
)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Row → claim
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _predicate_class(predicate: str) -> str:
    """The part of a gold predicate before the first ``:`` — the structural marker."""
    return predicate.split(":", 1)[0] if ":" in predicate else predicate


def _parse_participants(object_surface: str) -> list[str]:
    """``"participants: A; B"`` → ``["A", "B"]``. The gold's only event encoding (1 row)."""
    body = object_surface.split(":", 1)[1] if ":" in object_surface else object_surface
    return [p.strip() for p in body.split(";") if p.strip()]


def _discriminators(row: Mapping[str, Any]) -> dict[str, Any]:
    """Pass the four A7 slots through untouched.

    The gold writes "unknown" as a *string* where the source does not state the slot; the scorer's
    loader already treats that as a not-stated sentinel (``NOT_STATED_SENTINELS``) and explains at
    length why. Rewriting them to null here would be a second, silent implementation of the same rule —
    if the sentinel list ever changes, one file's meaning would drift from the other's. Passed through.
    """
    raw = row.get("discriminators") or {}
    return {slot: raw.get(slot) for slot in DISCRIMINATOR_SLOTS if slot in raw}


def _doc_ref(row: Mapping[str, Any], doc_path: str, doc_text: str) -> tuple[dict[str, Any], bool]:
    """Build the scorer's ``doc_ref`` from the quoted span. Returns ``(ref, byte_exact)``."""
    quoted = row["doc_ref_span"]
    start, end = decode_span(doc_text, quoted, row.get("doc_ref_line"))
    return (
        {"file": doc_path, "span": [start, end], "line": row.get("doc_ref_line")},
        doc_text[start:end] == quoted,
    )


def _to_claim(
    row: Mapping[str, Any], doc_path: str, doc_text: str, curated_clusters: set[str],
) -> tuple[dict[str, Any], bool]:
    """One positive gold row → one scorer claim. Returns ``(claim, span_was_byte_exact)``."""
    predicate = row["predicate"]
    cls = _predicate_class(predicate)
    ref, byte_exact = _doc_ref(row, doc_path, doc_text)

    claim: dict[str, Any] = {
        "gold_id": row["row_id"],
        "source_id": row["doc_id"],
        "polarity": row["polarity"],
        "doc_ref": ref,
    }

    if cls == "ENTITY_EXISTS":
        # SEMANTIC CALL S1 (mechanical): subject is the surface, object is the declared node type.
        claim["form"] = "entity"
        claim["name"] = row["subject_surface"]
        claim["entity_type"] = row["object_surface"]
    elif cls == "EVENT":
        # SEMANTIC CALL S3: the event type is the suffix; participants are the ";"-joined object.
        claim["form"] = "event"
        claim["event_type"] = predicate.split(":", 1)[1]
        claim["participants"] = _parse_participants(row["object_surface"])
    else:
        # Ontology edges, plus same-as / distinct-from. SEMANTIC CALL S4: identity claims stay
        # triples with their literal predicate, because that is what the live pipeline emits.
        claim["form"] = "triple"
        claim["subject"] = row["subject_surface"]
        claim["predicate"] = predicate
        claim["object"] = row["object_surface"]

    # SEMANTIC CALL S9. Only the 32 CURATED registry clusters are scoreable coref gold. The gold's own
    # cluster_count_note says the other 16 row tags "are row bookkeeping, NOT scoreable coref clusters,
    # and mostly have a single member". B-cubed over singleton bookkeeping tags is not a coref
    # measurement — every item is trivially its own cluster and the number drifts to whatever the
    # system happens to do. Non-registry tags (and "-") become absent, which is how metrics.py's
    # coref_binding knows to leave them out of its denominator.
    tag = row.get("coref_cluster")
    if tag in curated_clusters:
        claim["coref_cluster"] = tag

    disc = _discriminators(row)
    if disc:
        claim["discriminators"] = disc

    # SEMANTIC CALL S10: no ``kind``. The gold labels evidence_mode, not claim kind. Mapping
    # stated/hedged/attributed/negative-observation → "observation" would be defensible, but 488 of the
    # 492 claims in the frozen bundles are already "observation", so the derived metric would read
    # ~1.00 for every candidate — a measured-looking number with no discriminative content, entering
    # the composite at weight 0.5. Omitting it makes kind_tagging report "the gold slice labels no
    # claim kinds", which is literally true.

    # Everything the scorer does not consume is preserved here rather than dropped, so a reader of the
    # adapted file can always get back to the labeled row. The matcher never reads ``attributes``.
    claim["attributes"] = {
        "gold_evidence_mode": row.get("evidence_mode"),
        "gold_predicate": predicate,
        "gold_coref_tag": row.get("coref_cluster"),
        "gold_tier3_attributes": row.get("tier3_attributes") or {},
        "gold_notes": row.get("notes"),
        "span_byte_exact": byte_exact,
    }
    return claim, byte_exact


def _to_negative(
    row: Mapping[str, Any], bucket: str, doc_path: str, doc_text: str,
) -> dict[str, Any]:
    """One negative-gold row → a typed, localisable record (never a scorer ``claim``)."""
    ref, byte_exact = _doc_ref(row, doc_path, doc_text)
    predicate = row["predicate"]
    return {
        "gold_id": row["row_id"],
        "source_id": row["doc_id"],
        "class": bucket,
        "reason": predicate.split(":", 1)[1] if ":" in predicate else "",
        "surfaces": [row["subject_surface"], row["object_surface"]],
        "polarity": row["polarity"],
        "doc_ref": ref,
        "span_byte_exact": byte_exact,
        "gold_coref_tag": row.get("coref_cluster"),
        "evidence_mode": row.get("evidence_mode"),
        "notes": row.get("notes"),
    }


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The coref registry — carried through so its audited invariants stay provable on the OUTPUT.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _adapt_coref_registry(
    documents: Sequence[Mapping[str, Any]], doc_texts: Mapping[str, str],
) -> list[dict[str, Any]]:
    """The 32 curated clusters / 120 mentions, with the annotator locator stripped per the gold's note.

    Each mention carries ``verbatim_in_document`` so a scorer doing exact match knows, per mention,
    whether an exact match is even possible — rather than discovering it as an unexplained miss.
    """
    out: list[dict[str, Any]] = []
    for doc in documents:
        text = doc_texts.get(doc["doc_id"], "")
        normalised_doc = normalize_text(text)
        for cluster in doc.get("coref_clusters") or []:
            mentions = list(cluster.get("mentions") or [])
            adapted_mentions = []
            for mention in mentions:
                resolved = strip_annotator_locator(mention, text)
                adapted_mentions.append({
                    "annotated": mention,
                    "text": resolved,
                    "locator_stripped": resolved != mention.strip(),
                    "verbatim_in_document": normalize_text(resolved) in normalised_doc,
                })
            out.append({
                "cluster": cluster["cluster"],
                "source_id": doc["doc_id"],
                "referent_type": cluster.get("referent_type"),
                "licensing_category": cluster.get("licensing_category"),
                "licensing_quote": cluster.get("licensing_quote"),
                "mentions": adapted_mentions,
                "note": cluster.get("note"),
            })
    return out


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Claim gold
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _role_surfaces(claim: Mapping[str, Any]) -> list[str]:
    """The claim's role strings — what the matcher compares and the grounding proxy looks for."""
    if claim["form"] == "triple":
        values = [claim.get("subject"), claim.get("object")]
    elif claim["form"] == "entity":
        values = [claim.get("name")]
    else:
        values = list(claim.get("participants") or [])
    return [str(v) for v in values if v and str(v).strip() and str(v).strip() != "-"]


def _surface_verbatimness(
    claims: Sequence[Mapping[str, Any]], texts_by_path: Mapping[str, str],
) -> dict[str, Any]:
    """Are the gold's own role surfaces quotable from the document? A measured ceiling, not a score.

    Why this is in the file rather than in a note: the gold labels a claim's **resolved** subject, not
    always the verbatim mention — "HQ-9/P" where the sentence says only "was formally inducted…",
    "The missile itself / the HQ-9/P" with an annotator's slash, "(the suspected forward site)" with an
    annotator's locator. That is defensible labelling for a *claim* gold, and it is not changed here.

    But it puts a ceiling on two things a reader will otherwise read as model defects:

    * **surface recall** — for 16 of the 65 claims no extractor quoting the document can produce the gold
      surface at all, so those pairs live or die on the matcher's fuzzy tolerance;
    * **the grounding proxies** — a candidate that emitted *exactly* this gold scores 0.65 on
      ``citation_faithfulness`` and 0.82 on ``extract_only_stated`` (measured against the scorer at its
      declared 0.85 floor). Those two metrics read the candidate's own claims, not the gold, so a
      candidate quoting verbatim is **not** capped — but "emits the gold" is therefore not the definition
      of a perfect score on those lines, and a scorecard that implies otherwise is misreporting.

    Counts here are exact-substring under the gold's own normalisation — recomputable from this file plus
    the corpus, with no similarity threshold to argue about.
    """
    in_span = 0
    in_document = 0
    not_in_span: list[str] = []
    not_in_document: list[str] = []
    for claim in claims:
        ref = claim["doc_ref"]
        text = texts_by_path[ref["file"]]
        start, end = ref["span"]
        span_norm = normalize_text(text[start:end])
        doc_norm = normalize_text(text)
        surfaces = [normalize_text(s) for s in _role_surfaces(claim)]
        if all(s in span_norm for s in surfaces):
            in_span += 1
        else:
            not_in_span.append(claim["gold_id"])
        if all(s in doc_norm for s in surfaces):
            in_document += 1
        else:
            not_in_document.append(claim["gold_id"])
    return {
        "scored_claims": len(claims),
        "all_role_surfaces_verbatim_in_own_span": in_span,
        "all_role_surfaces_verbatim_somewhere_in_document": in_document,
        "rows_with_a_surface_absent_from_their_span": not_in_span,
        "rows_with_a_surface_absent_from_the_whole_document": not_in_document,
        "reading": (
            "A ceiling on this SLICE, not a defect in any candidate. The gold labels resolved subjects "
            "and annotator-composed surfaces; those rows can only match a verbatim extractor through the "
            "matcher's fuzzy tolerance. Report absolute recall against this ceiling, never against 1.00."
        ),
    }


def _require_schema(raw: Mapping[str, Any], prefix: str, what: str) -> None:
    version = str(raw.get("schema_version", ""))
    if not version.startswith(prefix):
        raise ValueError(
            f"{what}: expected schema_version starting {prefix!r}, got {version!r}. This adapter "
            "translates one declared schema into another and will not guess at a third."
        )


class ReconciliationError(ValueError):
    """The translation lost, duplicated or mis-bucketed a row. Never recoverable — always raised."""


def adapt_claim_gold(
    raw: Mapping[str, Any], doc_texts: Mapping[str, str], *, source_digest: str | None = None,
) -> dict[str, Any]:
    """``rk-spike-claim-gold/1.x`` → ``rk-bakeoff-claim-gold/1.0`` + typed negative gold.

    ``doc_texts`` maps ``doc_id`` → the cited document's raw text (needed to resolve quoted spans to
    offsets). Raises if any row cannot be placed, if a span cannot be decoded, or if the resulting
    buckets do not reconcile against the gold's own declared counts.
    """
    _require_schema(raw, CLAIM_GOLD_SCHEMA_IN, "claim gold")
    documents = list(raw.get("documents") or [])
    rows = list(raw.get("rows") or [])
    doc_paths = {d["doc_id"]: d["path"] for d in documents}
    curated = {c["cluster"] for d in documents for c in (d.get("coref_clusters") or [])}

    claims: list[dict[str, Any]] = []
    negatives: dict[str, list[dict[str, Any]]] = {k: [] for k in NEGATIVE_GOLD_SEMANTICS}
    attribute_rows: list[dict[str, Any]] = []
    byte_exact_spans = 0
    seen: set[str] = set()

    for row in rows:
        row_id = row["row_id"]
        if row_id in seen:
            raise ReconciliationError(f"duplicate row_id {row_id!r} in the source gold")
        seen.add(row_id)
        doc_id = row["doc_id"]
        if doc_id not in doc_paths:
            raise ReconciliationError(f"row {row_id!r} cites document {doc_id!r}, which the gold's "
                                      "`documents` block does not declare")
        text = doc_texts.get(doc_id)
        if text is None:
            raise ReconciliationError(f"no document text supplied for {doc_id!r} (row {row_id!r})")

        cls = _predicate_class(row["predicate"])
        if cls in _NEGATIVE_PREFIX:
            bucket = _NEGATIVE_PREFIX[cls]
            record = _to_negative(row, bucket, doc_paths[doc_id], text)
            negatives[bucket].append(record)
            byte_exact_spans += int(record["span_byte_exact"])
        elif cls == "ATTR":
            ref, byte_exact = _doc_ref(row, doc_paths[doc_id], text)
            attribute_rows.append({
                "gold_id": row_id,
                "source_id": doc_id,
                "subject": row["subject_surface"],
                "attribute": row["predicate"].split(":", 1)[1],
                "value": row["object_surface"],
                "polarity": row["polarity"],
                "doc_ref": ref,
                "span_byte_exact": byte_exact,
                "notes": row.get("notes"),
            })
            byte_exact_spans += int(byte_exact)
        else:
            claim, byte_exact = _to_claim(row, doc_paths[doc_id], text, curated)
            claims.append(claim)
            byte_exact_spans += int(byte_exact)

    registry = _adapt_coref_registry(documents, doc_texts)
    out: dict[str, Any] = {
        "schema_version": CLAIM_GOLD_SCHEMA_OUT,
        "produced_by": {
            "adapter": "eval.gold.adapter",
            "from_schema": str(raw.get("schema_version")),
            "from_digest_sha256": source_digest,
            "note": "Derived file. Edit the labeled gold, then regenerate — never hand-edit this.",
        },
        "docs": [d["doc_id"] for d in documents],
        "doc_paths": doc_paths,
        "claims": claims,
        "negative_gold": {
            bucket: {**NEGATIVE_GOLD_SEMANTICS[bucket], "rows": rows_}
            for bucket, rows_ in negatives.items()
        },
        "excluded_from_scoring": {
            "attribute_rows": {"reason": ATTRIBUTE_EXCLUSION_REASON, "rows": attribute_rows},
        },
        "coref_registry": registry,
        "surface_verbatimness": _surface_verbatimness(
            claims, {doc_paths[doc_id]: text for doc_id, text in doc_texts.items()
                     if doc_id in doc_paths},
        ),
    }
    out["reconciliation"] = _reconcile(raw, out, byte_exact_spans)
    return out


def _reconcile(
    raw: Mapping[str, Any], out: Mapping[str, Any], byte_exact_spans: int,
) -> dict[str, Any]:
    """Prove nothing was lost: every source row lands in exactly one bucket, and counts agree.

    This is the invariant the project keeps failing on — a translation that quietly drops rows — so it
    is checked in code and raises, not asserted in a comment.
    """
    declared = dict(raw.get("counts") or {})
    negatives = out["negative_gold"]
    attribute_rows = out["excluded_from_scoring"]["attribute_rows"]["rows"]

    buckets = {
        "claims": [c["gold_id"] for c in out["claims"]],
        "attribute_rows": [r["gold_id"] for r in attribute_rows],
        **{f"negative:{k}": [r["gold_id"] for r in v["rows"]] for k, v in negatives.items()},
    }
    placed = [gid for ids in buckets.values() for gid in ids]
    source_ids = [r["row_id"] for r in raw.get("rows") or []]

    if sorted(placed) != sorted(source_ids):
        lost = sorted(set(source_ids) - set(placed))
        gained = sorted(set(placed) - set(source_ids))
        raise ReconciliationError(
            f"row accounting broke: {len(source_ids)} source rows → {len(placed)} placed "
            f"(lost={lost}, invented={gained})"
        )
    if len(placed) != len(set(placed)):
        raise ReconciliationError("a row was placed in more than one bucket")

    checks = {
        "documents": (len(out["docs"]), declared.get("documents")),
        "rows": (len(placed), declared.get("rows")),
        "not_a_claim_rows": (len(negatives["not_a_claim"]["rows"]), declared.get("not_a_claim_rows")),
        "anti_coref_rows": (len(negatives["anti_coref"]["rows"]), declared.get("anti_coref_rows")),
        "unmodelled_rows": (len(negatives["unmodelled"]["rows"]), declared.get("unmodelled_rows")),
        "coref_clusters": (len(out["coref_registry"]), declared.get("coref_clusters")),
    }
    mismatched = {k: v for k, v in checks.items() if v[1] is not None and v[0] != v[1]}
    if mismatched:
        raise ReconciliationError(f"declared counts do not reproduce after translation: {mismatched}")

    negative_polarity = sum(
        1 for c in out["claims"] if c["polarity"] == "negative"
    ) + sum(
        1 for v in negatives.values() for r in v["rows"] if r["polarity"] == "negative"
    ) + sum(1 for r in attribute_rows if r["polarity"] == "negative")
    if declared.get("negative_polarity_rows") not in (None, negative_polarity):
        raise ReconciliationError(
            f"negative-polarity rows: {negative_polarity} after translation, "
            f"{declared['negative_polarity_rows']} declared"
        )

    return {
        "source_rows": len(source_ids),
        "placed_rows": len(placed),
        "bucket_sizes": {k: len(v) for k, v in buckets.items()},
        "scored_recall_denominator": len(out["claims"]),
        "declared_counts_reproduced": {k: v[0] for k, v in checks.items()},
        "negative_polarity_rows": negative_polarity,
        "coref": {
            "curated_clusters": len(out["coref_registry"]),
            "curated_mentions": sum(len(c["mentions"]) for c in out["coref_registry"]),
            "mentions_with_locator_stripped": sum(
                1 for c in out["coref_registry"] for m in c["mentions"] if m["locator_stripped"]
            ),
            "mentions_verbatim_in_their_document": sum(
                1 for c in out["coref_registry"] for m in c["mentions"] if m["verbatim_in_document"]
            ),
            "claims_carrying_a_scoreable_cluster": sum(
                1 for c in out["claims"] if c.get("coref_cluster")
            ),
            "distinct_clusters_among_claims": len(
                {c["coref_cluster"] for c in out["claims"] if c.get("coref_cluster")}
            ),
        },
        "spans": {
            "decoded": len(placed),
            "byte_exact": byte_exact_spans,
            "exact_under_gold_normalisation": len(placed),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# Sub-oracle
# ══════════════════════════════════════════════════════════════════════════════════════════════════
#
# Smaller translation, same discipline. ``node_id/node_type/label`` → ``id/type/name``,
# ``predicate/frm/to`` → ``type/source/target``, ``slice_documents`` → ``docs``. Two decodes and three
# exclusions, all named.

#: A trailing parenthetical annotation on a node's declared type — "unit (formation)". Same class of
#: annotator sugar as the coref mention locator; the ontology type is the part before it.
_TYPE_ANNOTATION = re.compile(r"\s*\(.*\)\s*$", re.DOTALL)


def _decode_node_type(node_type: str) -> str:
    """``"unit (formation, as a CARDINALITY)"`` → ``"unit"``. The parenthetical is annotation."""
    return _TYPE_ANNOTATION.sub("", node_type).strip()


def adapt_sub_oracle(raw: Mapping[str, Any], *, source_digest: str | None = None) -> dict[str, Any]:
    """``rk-spike-sub-oracle/1.x`` → ``rk-bakeoff-sub-oracle/1.0``, with the unscoreable named.

    Three exclusions, each of which would otherwise either crash the scorer's loader or penalise a
    candidate for behaving correctly (SEMANTIC CALL S11):

    1. **Nodes whose declared type is not a node type.** ``sl_family_hq9`` carries
       ``node_type: "(family — NOT a node type)"``: the gold is recording that the ontology has no
       family type. Requiring a candidate to produce a node of a non-existent type is not a measurement.
    2. **``insufficient-evidence`` EDGES (5).** The gold states outright that these are "explicitly not
       derivable … with their missing premises named". Keeping them in the denominator scores a
       candidate DOWN for the refusal this project treats as non-negotiable, and scores a fabricator UP.
       ``insufficient-evidence`` NODES are kept: an under-evidenced node still exists in the graph and a
       correct extraction produces it; the status is a downstream credibility label, not a "do not emit".
    3. **Edges whose endpoint is a surface form, not a declared node (5).** ``sl_var_hq9p same-as
       "HQ-9P"`` — the gold deliberately does not mint alias surfaces as nodes. The scorer's oracle
       model has no way to express that endpoint, and its loader raises on it. Minting the surfaces as
       nodes to make them load would invent 5 nodes the gold refused to create and would penalise a
       model that correctly resolved the alias. Excluded and named instead.
    """
    _require_schema(raw, SUB_ORACLE_SCHEMA_IN, "sub-oracle")

    nodes: list[dict[str, Any]] = []
    excluded_nodes: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for node in raw.get("nodes") or []:
        decoded = _decode_node_type(node["node_type"])
        record = {
            "id": node["node_id"],
            "type": decoded,
            "name": node["label"],
            "status": node.get("status"),
            "surface_forms": node.get("surface_forms") or [],
            "declared_type": node["node_type"],
        }
        if not decoded:
            excluded_nodes.append({**record, "excluded_because": "declared type is not an ontology type"})
            continue
        nodes.append(record)
        by_id[node["node_id"]] = record

    edges: list[dict[str, Any]] = []
    excluded_edges: list[dict[str, Any]] = []
    for edge in raw.get("edges") or []:
        record = {
            "type": _TYPE_ANNOTATION.sub("", edge["predicate"]).strip() or edge["predicate"],
            "source": edge["frm"],
            "target": edge["to"],
            "edge_id": edge.get("edge_id"),
            "status": edge.get("status"),
            "basis": edge.get("basis"),
        }
        unresolved = [e for e in (edge["frm"], edge["to"]) if e not in by_id]
        if edge.get("status") == "insufficient-evidence":
            excluded_edges.append({
                **record, "excluded_because": "insufficient-evidence: the gold states this edge is NOT "
                                              "derivable from the slice; a candidate is right not to emit it",
                "missing": edge.get("missing"),
            })
        elif unresolved:
            excluded_edges.append({
                **record, "excluded_because": "endpoint is a surface form, not a declared oracle node "
                                              f"({unresolved}); the scorer's oracle model cannot express it",
            })
        else:
            edges.append(record)

    docs = [d["doc_id"] if isinstance(d, dict) else str(d) for d in (raw.get("slice_documents") or [])]
    reconciliation = {
        "source_nodes": len(raw.get("nodes") or []),
        "source_edges": len(raw.get("edges") or []),
        "scored_nodes": len(nodes),
        "scored_edges": len(edges),
        "excluded_nodes": len(excluded_nodes),
        "excluded_edges": len(excluded_edges),
    }
    out = {
        "schema_version": SUB_ORACLE_SCHEMA_OUT,
        "produced_by": {
            "adapter": "eval.gold.adapter",
            "from_schema": str(raw.get("schema_version")),
            "from_digest_sha256": source_digest,
            "note": "Derived file. Edit the labeled sub-oracle, then regenerate.",
        },
        "docs": docs,
        "nodes": [{"id": n["id"], "type": n["type"], "name": n["name"]} for n in nodes],
        "edges": [{"type": e["type"], "source": e["source"], "target": e["target"]} for e in edges],
        "excluded_nodes": excluded_nodes,
        "excluded_edges": excluded_edges,
        "node_detail": nodes,
        "reconciliation": reconciliation,
    }
    if (reconciliation["scored_nodes"] + reconciliation["excluded_nodes"]
            != reconciliation["source_nodes"]):
        raise ReconciliationError("sub-oracle translation lost a node")
    if (reconciliation["scored_edges"] + reconciliation["excluded_edges"]
            != reconciliation["source_edges"]):
        raise ReconciliationError("sub-oracle translation lost an edge")
    return out


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_doc_texts(documents: Sequence[Mapping[str, Any]], root: Path) -> dict[str, str]:
    return {d["doc_id"]: (root / d["path"]).read_text(encoding="utf-8") for d in documents}


def _dump(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.gold.adapter", description=__doc__)
    root = _repo_root()
    parser.add_argument("--gold", default=str(root / "tmp/spike-rk/gold/claim-gold.json"))
    parser.add_argument("--sub-oracle", default=str(root / "tmp/spike-rk/gold/sub-oracle.json"))
    parser.add_argument("--out-dir", default=str(root / "tmp/spike-rk/gold"))
    parser.add_argument("--repo-root", default=str(root))
    args = parser.parse_args(argv)

    repo = Path(args.repo_root)
    gold_path = Path(args.gold)
    raw_gold = json.loads(gold_path.read_text(encoding="utf-8"))
    texts = _load_doc_texts(raw_gold.get("documents") or [], repo)
    adapted = adapt_claim_gold(raw_gold, texts, source_digest=_digest(gold_path))

    oracle_path = Path(args.sub_oracle)
    raw_oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    adapted_oracle = adapt_sub_oracle(raw_oracle, source_digest=_digest(oracle_path))

    out_dir = Path(args.out_dir)
    _dump(out_dir / "claim-gold.bakeoff.json", adapted)
    _dump(out_dir / "sub-oracle.bakeoff.json", adapted_oracle)

    rec = adapted["reconciliation"]
    print(f"claim gold  : {rec['source_rows']} rows → {rec['scored_recall_denominator']} scored claims")
    for bucket, size in sorted(rec["bucket_sizes"].items()):
        print(f"              {bucket:26s} {size}")
    print(f"              spans byte-exact {rec['spans']['byte_exact']}/{rec['spans']['decoded']}, "
          f"exact under the gold's normalisation {rec['spans']['exact_under_gold_normalisation']}"
          f"/{rec['spans']['decoded']}")
    print(f"              coref {rec['coref']['curated_clusters']} clusters / "
          f"{rec['coref']['curated_mentions']} mentions")
    verb = adapted["surface_verbatimness"]
    print(f"              role surfaces quotable from the doc "
          f"{verb['all_role_surfaces_verbatim_somewhere_in_document']}/{verb['scored_claims']} "
          f"— a SLICE ceiling on absolute recall, not a candidate defect")
    unwired = [b for b, s in NEGATIVE_GOLD_SEMANTICS.items()
               if s["precision_exclusion_automatic"].startswith("NO")]
    print(f"              negative classes needing harness wiring to be neutral: {unwired}")
    orec = adapted_oracle["reconciliation"]
    print(f"sub-oracle  : nodes {orec['scored_nodes']}/{orec['source_nodes']} scored, "
          f"edges {orec['scored_edges']}/{orec['source_edges']} scored")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
