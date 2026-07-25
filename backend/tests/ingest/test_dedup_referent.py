"""RK-ATOMS S1 items 2 + 3 — the **dormant referent field** and **atom-aware dedup**.

Spec (``artifacts/plan/01-replumb-implementation-plan.md`` §7 RK-ATOMS):

    2. "**Referent field (A1), optional/``None``.** Add an optional referent id (default ``None``) to
       ``ClaimRecord``/payloads (``schemas/claim.py``); add ``make_referent_id`` beside ``make_claim_id``
       (``schemas/ids.py``) **but do not invoke it** — referents are minted in S3. … Optional-default
       keeps ``extra="forbid"`` fixtures loading and S1 non-breaking."
    3. "**Atom-aware dedup.** Extend ``remap_claim_refs`` **and** ``dedup_within_doc``
       (``ingest/dedup.py``) to carry/reconcile the referent field, so a value populated later (S3) is
       never silently orphaned or collapsed — dedup reassigns ``claim_id`` and folds same-signature
       mentions, and today neither carries a referent. **This is the real risk the old plan missed.**"

Item 3 is the stage's real risk, so it is tested hardest: the field must survive the fold, survive the
canonical-id remap, and — in the **fold case**, where two mentions carrying *different* referents
collapse into one — behave in a way that is deterministic, non-fabricating and non-silent. The spec does
**not** say what that fold must produce, so this module asserts only the properties that must hold under
*any* correct choice; the ambiguity is reported to the orchestrator rather than resolved here.

Both directions are covered: the field must exist **and** must not be auto-populated (S3 mints, not S1).
"""

from __future__ import annotations

import json

from chanakya.ingest.dedup import assign_claim_ids, dedup_within_doc, remap_claim_refs
from chanakya.ingest.seed import ingest_bundle
from chanakya.schemas import ClaimRecord, DocRef, Triple
from tests import _rk_atoms as rk

# ── helpers ──────────────────────────────────────────────────────────────────────────────────────


def _triple(
    *,
    pred: str = "based-at",
    span: tuple[int, int] = (0, 10),
    line: int | None = 1,
    claim_id: str = "provisional",
    premises: list[str] | None = None,
    kind: str = "observation",
) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        source_id="src-a",
        doc_ref=DocRef(file="d01.txt", span=span, line=line),
        kind=kind,  # type: ignore[arg-type]
        asserts="relationship",
        payload=Triple(subject="hq-9", predicate=pred, object="site-7"),
        premises=premises or [],
    )


# ── item 2: the field exists, is optional, and defaults to None ────────────────────────────────────

def test_claim_record_declares_an_optional_referent_defaulting_to_none() -> None:
    """§7 item 2: "an optional referent id (default ``None``)" on ``ClaimRecord``."""
    field = rk.referent_field_name()
    assert _triple().model_dump()[field] is None
    assert getattr(_triple(), field) is None


def test_the_referent_field_is_not_required_by_the_schema() -> None:
    """A1: the optional default is what "keeps ``extra="forbid"`` fixtures loading and S1 non-breaking"."""
    field = rk.referent_field_name()
    required = ClaimRecord.model_json_schema().get("required", [])
    assert field not in required, (
        f"{field!r} is a required field — every pre-baked fixture and frozen bundle would stop loading, "
        "and an extractor would be forced to invent a referent (plan §4 A1: optional, default None)"
    )


def test_a_record_that_omits_the_referent_still_validates() -> None:
    """"tolerated-absent on pre-baked fixtures" (session file, Acceptance)."""
    raw = _triple().model_dump()
    raw.pop(rk.referent_field_name())
    assert getattr(ClaimRecord.model_validate(raw), rk.referent_field_name()) is None


def test_a_referent_value_round_trips_through_json() -> None:
    """The evidence log is JSON on disk — a referent that cannot round-trip is not an atom."""
    value = rk.sample_referent("rt")
    claim = rk.constructed_with_referent(_triple(), value)
    reparsed = ClaimRecord.model_validate_json(claim.model_dump_json())
    assert rk.referent_of(reparsed) == value


# ── item 2, negative direction: S1 must NOT populate it ───────────────────────────────────────────

def test_the_ingest_reshape_never_populates_a_referent() -> None:
    """§7 item 2: "**but do not invoke it** — referents are minted in S3."

    The dormancy has to be observable, not just documented: if the reshape started minting referents,
    S3's grouping signal would already be baked into the frozen bundles at the wrong grain.
    """
    claims = [_triple(pred="based-at", span=(0, 10), line=1),
              _triple(pred="equips", span=(20, 30), line=2)]

    for claim in assign_claim_ids(dedup_within_doc(claims), doc_id="d01"):
        assert rk.referent_of(claim) is None, (
            "the ingest reshape populated a referent — S1 is dormant; S3 mints "
            "(plan §4 A1: 'populated only from S3')"
        )


def test_reading_a_bundle_without_a_referent_leaves_it_none(tmp_path) -> None:
    """The keyless boot path must not invent a referent for the frozen corpus bundles."""
    raw = _triple(claim_id="d01-l1").model_dump(mode="json")
    raw.pop(rk.referent_field_name(), None)
    path = tmp_path / "d01.json"
    path.write_text(json.dumps([raw]), encoding="utf-8")

    [claim] = ingest_bundle(path)

    assert rk.referent_of(claim) is None


# ── item 3: the field survives dedup_within_doc ───────────────────────────────────────────────────

def test_referent_survives_dedup_within_doc_untouched() -> None:
    value = rk.sample_referent("keep")
    claim = rk.constructed_with_referent(_triple(span=(0, 10), line=1), value)

    [out] = dedup_within_doc([claim])

    assert rk.referent_of(out) == value, "dedup_within_doc dropped the referent (§7 item 3)"


def test_referent_survives_a_fold_of_two_mentions_sharing_one_referent() -> None:
    """The ordinary S3 shape: a restatement inside one coref cluster. The shared value must survive."""
    value = rk.sample_referent("shared")
    first = rk.constructed_with_referent(_triple(span=(0, 20), line=1, claim_id="a"), value)
    echo = rk.constructed_with_referent(_triple(span=(50, 70), line=3, claim_id="b"), value)

    out = dedup_within_doc([first, echo])

    assert len(out) == 1
    assert rk.referent_of(out[0]) == value


def test_a_shared_referent_never_widens_the_fold_across_documents() -> None:
    """Claims in **different documents** never fold, referent or not — the dedup scope is one doc.

    The referent is *document-local* (A1: "one per **document-local** coreference cluster"), so it must
    never become a cross-document merge signal at ingest — that is RESOLVE's earned decision.
    """
    value = rk.sample_referent("cross")
    a = rk.constructed_with_referent(_triple(span=(0, 10), line=1), value)
    other_doc = ClaimRecord(
        claim_id="provisional-b", source_id="src-b",
        doc_ref=DocRef(file="d02.txt", span=(0, 10), line=1),
        kind="observation", asserts="relationship",
        payload=Triple(subject="hq-9", predicate="based-at", object="site-7"),
    )
    b = rk.constructed_with_referent(other_doc, value)

    assert len(dedup_within_doc([a, b])) == 2


# ── item 3: the field survives remap_claim_refs / assign_claim_ids ─────────────────────────────────

def test_referent_survives_the_canonical_id_remap() -> None:
    """§7 item 3: ``remap_claim_refs`` must carry the referent while the ``claim_id`` is reassigned."""
    value = rk.sample_referent("remap")
    claim = rk.constructed_with_referent(_triple(span=(0, 10), line=7, claim_id="provisional"), value)

    [out] = assign_claim_ids([claim], doc_id="d01")

    assert out.claim_id != "provisional"  # the atom was reassigned …
    assert rk.referent_of(out) == value, "… but the referent did not follow it (§7 item 3)"


def test_remap_claim_refs_does_not_clear_the_referent() -> None:
    """The update dict ``remap_claim_refs`` returns must never blank the referent field."""
    field = rk.referent_field_name()
    value = rk.sample_referent("upd")
    claim = rk.constructed_with_referent(
        _triple(kind="inference", premises=["old-premise"], claim_id="provisional"), value
    )

    update = remap_claim_refs(claim, {"old-premise": "d01-l1"})
    patched = claim.model_copy(update=update)

    assert update.get("premises") == ["d01-l1"]  # the reference did follow
    assert rk.referent_of(patched) == value, f"remap_claim_refs blanked {field!r}"


def test_a_referent_is_never_rewritten_into_a_claim_id() -> None:
    """The negative direction: a referent lives in its own namespace, so the claim-id map must not touch it.

    A referent silently rewritten to a claim id would look like a valid grouping signal while pointing at
    the wrong kind of atom — exactly the "silently orphaned" failure §7 item 3 exists to prevent.
    """
    value = rk.sample_referent("ns")
    claim = rk.constructed_with_referent(_triple(claim_id="provisional"), value)

    # A hostile remap whose keys happen to include the referent's own value.
    patched = claim.model_copy(update=remap_claim_refs(claim, {value: "d01-l1", "provisional": "d01-l1"}))

    assert rk.referent_of(patched) != "d01-l1", (
        "the claim-id remap rewrote the referent — a grouping signal must not be re-pointed at a claim atom"
    )


# ── item 3, the FOLD CASE: two different referents collapsing into one ─────────────────────────────
#
# The spec does not state what this must produce. These three tests assert only what must hold under
# ANY correct choice. Reported as a spec silence in tmp/conv/RK-ATOMS-TEST-NOTES.md.

def _conflicting_fold(order_reversed: bool = False) -> tuple[list[ClaimRecord], str, str]:
    """Two same-signature mentions (identical spans, so nothing but the referent distinguishes them)."""
    left, right = rk.sample_referent("left"), rk.sample_referent("right")
    a = rk.constructed_with_referent(_triple(span=(0, 10), line=1, claim_id="a"), left)
    b = rk.constructed_with_referent(_triple(span=(0, 10), line=1, claim_id="b"), right)
    members = [b, a] if order_reversed else [a, b]
    return dedup_within_doc(members), left, right


def _referent_values(claim: ClaimRecord) -> set[str]:
    """Whatever the fold left behind, flattened — a scalar, a collection, or a tier-3 breadcrumb."""
    found: set[str] = set()
    for value in [rk.referent_of(claim), *(claim.attributes or {}).values()]:
        if isinstance(value, str):
            found.add(value)
        elif isinstance(value, (list, tuple, set, frozenset)):
            found.update(str(v) for v in value)
    return found


def test_fold_of_conflicting_referents_is_deterministic() -> None:
    """Order-independence is not optional: ``rebuild()`` is a pure recompute (G2), and the fold's
    representative is chosen by ``min()`` over equal sort keys — i.e. by **arrival order** — so an
    implementation that simply inherits the representative's referent is nondeterministic here."""
    forward, _, _ = _conflicting_fold()
    backward, _, _ = _conflicting_fold(order_reversed=True)

    assert [c.model_dump_json() for c in forward] == [c.model_dump_json() for c in backward], (
        "folding two conflicting referents depends on input order — the reconciliation must be "
        "content-derived (§7 item 3 'carry/reconcile'; gate G2 determinism)"
    )


def test_fold_of_conflicting_referents_never_fabricates_a_third_value() -> None:
    """The non-negotiable, applied to a grouping signal: no invented atom may appear."""
    out, left, right = _conflicting_fold()

    for claim in out:
        value = rk.referent_of(claim)
        candidates = {value} if isinstance(value, str) else set(value or ())
        invented = {str(v) for v in candidates} - {left, right}
        assert not invented, (
            f"the fold produced referent value(s) {sorted(invented)} that no mention ever carried — "
            "a fabricated atom (CLAUDE.md non-negotiable)"
        )


def test_fold_of_conflicting_referents_loses_nothing_silently() -> None:
    """§7 item 3: a referent must be "**never silently** orphaned or collapsed".

    Any of these outcomes satisfies the requirement, and this test accepts all of them:
      * the two mentions do **not** fold (a differing referent is treated as differing content);
      * the surviving claim retains **both** values (a collection);
      * one value wins and the other is retained as a traceable breadcrumb (e.g. tier-3 ``attributes``).
    What it rejects is the fourth outcome: one value is kept, the other vanishes with no trace.
    """
    out, left, right = _conflicting_fold()

    if len(out) == 2:
        return  # the fold declined — nothing was collapsed
    retained = _referent_values(out[0])
    assert {left, right} <= retained, (
        f"the fold kept {sorted(retained)} and discarded {sorted({left, right} - retained)} with no "
        "trace — a referent was silently collapsed (§7 item 3). Any recorded trace satisfies this; "
        "see 'spec silences' in tmp/conv/RK-ATOMS-TEST-NOTES.md for the outcomes accepted."
    )


# ── item 3 must not cost the existing behaviour ───────────────────────────────────────────────────

def test_carrying_the_referent_does_not_change_the_fold_of_referentless_claims() -> None:
    """Zero behavioural change (the stage's headline invariant) at the dedup boundary."""
    first = _triple(span=(0, 20), line=1, claim_id="a")
    echo = _triple(span=(50, 70), line=3, claim_id="b")

    out = dedup_within_doc([first, echo])

    assert len(out) == 1
    assert [r.span for r in out[0].doc_refs()] == [(0, 20), (50, 70)]
    assert rk.referent_of(out[0]) is None
