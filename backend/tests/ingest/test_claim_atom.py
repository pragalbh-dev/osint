"""RK-ATOMS S1 item 1 — the **claim atom is the post-dedup ``claim_id``**, and it is the addressing bedrock.

Spec (``artifacts/plan/01-replumb-implementation-plan.md`` §4 A1):

    "**Claim atom** = the per-mention bedrock = the **post-dedup ``claim_id``** (canonicalised in
    ``dedup.assign_claim_ids``, not at construction). S1 formalizes it as the stable addressing bedrock;
    no new id is minted — this names and freezes what already exists."

So three properties are asserted here, and they are the whole of item 1:

1. the atom is minted **post-dedup**, not at construction — a construction-time id is provisional;
2. the atom is **stable**: derived from content, identical across input order and across reruns
   (nothing may key it on arrival order, a clock or an RNG);
3. the atom is **what downstream references point at** — after the ingest reshape no cross-claim
   reference names a provisional id, i.e. the reference closure over atoms is complete. An orphaned
   reference is the failure mode that makes the "bedrock" claim false.

Every test is pure and offline (no LLM/geocoder/clock/RNG), mirroring ``tests/ingest/test_dedup.py``.
"""

from __future__ import annotations

import pytest

from chanakya.edge_direction import OBJECT_MENTION_ATTR, SUBJECT_MENTION_ATTR
from chanakya.ingest.dedup import assign_claim_ids, dedup_within_doc
from chanakya.schemas import ClaimRecord, DocRef, EntityDescriptor, Triple

# ── helpers ──────────────────────────────────────────────────────────────────────────────────────


def _triple(
    *,
    subj: str = "hq-9",
    pred: str = "based-at",
    obj: str = "site-7",
    span: tuple[int, int] = (0, 10),
    line: int | None = 1,
    kind: str = "observation",
    premises: list[str] | None = None,
    targets: str | None = None,
    attributes: dict[str, object] | None = None,
    claim_id: str = "provisional",
    source_id: str = "src-a",
    file: str = "d01.txt",
) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        source_id=source_id,
        doc_ref=DocRef(file=file, span=span, line=line),
        kind=kind,  # type: ignore[arg-type]
        asserts="relationship",
        payload=Triple(subject=subj, predicate=pred, object=obj),
        premises=premises or [],
        targets=targets,
        attributes=attributes,
    )


def _entity(name: str, *, span: tuple[int, int], line: int, claim_id: str) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        source_id="src-a",
        doc_ref=DocRef(file="d01.txt", span=span, line=line),
        kind="observation",
        asserts="entity",
        payload=EntityDescriptor(entity_type="unit", name=name),
    )


def _references(claim: ClaimRecord) -> set[str]:
    """Every claim-id-valued reference a claim carries (premises, targets, tier-3 mention refs)."""
    refs = set(claim.premises)
    if claim.targets:
        refs.add(claim.targets)
    for key in (SUBJECT_MENTION_ATTR, OBJECT_MENTION_ATTR):
        value = (claim.attributes or {}).get(key)
        if isinstance(value, str):
            refs.add(value)
    return refs


def _reshape(claims: list[ClaimRecord], *, doc_id: str = "d01") -> list[ClaimRecord]:
    """The pure ingest reshape the lane and the seed both run: fold restatements, then mint the atoms."""
    return assign_claim_ids(dedup_within_doc(claims), doc_id=doc_id)


# ── 1. the atom is post-dedup, not construction-time ──────────────────────────────────────────────

def test_construction_time_claim_id_is_provisional_not_the_atom() -> None:
    """A1: the claim atom is "canonicalised in ``dedup.assign_claim_ids``, **not at construction**"."""
    built = _triple(claim_id="whatever-the-extractor-guessed", line=3)

    atoms = _reshape([built])

    assert len(atoms) == 1
    assert atoms[0].claim_id != "whatever-the-extractor-guessed"
    assert atoms[0].claim_id == "d01-l3"  # derived from the doc + the cited locator, not from the input
    assert built.claim_id == "whatever-the-extractor-guessed"  # the input is never mutated


def test_the_atom_is_minted_from_the_folded_claim_not_per_restatement() -> None:
    """One assertion restated twice is **one** atom carrying both spans — the atom is per-*mention-fold*."""
    first = _triple(span=(0, 20), line=1, claim_id="a")
    echo = _triple(span=(50, 70), line=3, claim_id="b")

    atoms = _reshape([first, echo])

    assert len(atoms) == 1, "a within-doc restatement must not mint two claim atoms"
    assert len(atoms[0].doc_refs()) == 2


# ── 2. the atom is stable (the "bedrock" clause) ──────────────────────────────────────────────────

def test_atoms_are_byte_identical_across_input_order() -> None:
    claims = [
        _triple(pred="based-at", span=(0, 10), line=1),
        _triple(pred="inducted-into", span=(20, 30), line=2),
        _triple(pred="equips", span=(40, 50), line=3),
    ]

    forward = [c.claim_id for c in _reshape(claims)]
    backward = [c.claim_id for c in _reshape(list(reversed(claims)))]

    assert forward == backward, "the claim atom must be content-derived, never arrival-order-derived"
    assert len(set(forward)) == len(forward)


def test_atoms_are_byte_identical_across_reruns() -> None:
    claims = [_triple(pred=p, span=(i * 10, i * 10 + 5), line=i + 1)
              for i, p in enumerate(["based-at", "equips", "supplies-component"])]

    assert [c.claim_id for c in _reshape(claims)] == [c.claim_id for c in _reshape(claims)]


# ── 3. the atom is what downstream references point at ────────────────────────────────────────────

def test_no_reference_survives_pointing_at_a_provisional_id() -> None:
    """The closure property: after the reshape, every reference names an **atom**, never a provisional id.

    This is what "stable addressing bedrock" means operationally — an id nothing can address is not a
    bedrock. Ids that were never in the input (an external premise) are legitimately left alone.
    """
    obs = _entity("34 sam battery", span=(0, 15), line=1, claim_id="obs-provisional")
    inference = _triple(
        subj="34 sam battery", pred="based-at", obj="site-7", span=(20, 40), line=2,
        kind="inference", premises=["obs-provisional", "external-literature"],
        attributes={SUBJECT_MENTION_ATTR: "obs-provisional"},
        claim_id="inf-provisional",
    )

    atoms = _reshape([obs, inference])
    minted = {c.claim_id for c in atoms}
    provisional = {"obs-provisional", "inf-provisional"}

    for claim in atoms:
        dangling = _references(claim) & provisional
        assert not dangling, (
            f"{claim.claim_id} still references the provisional id(s) {sorted(dangling)} — "
            "the reference did not follow the claim atom"
        )
        unresolved = _references(claim) - minted - {"external-literature"}
        assert not unresolved, f"{claim.claim_id} references non-atoms {sorted(unresolved)}"


def test_tier3_mention_refs_follow_the_atom() -> None:
    """The endpoint mention refs are claim ids too (``dedup._REF_ATTRS``), so they must be remapped."""
    subject = _entity("34 sam battery", span=(0, 15), line=1, claim_id="subj-provisional")
    obj = _entity("rahwali", span=(16, 24), line=2, claim_id="obj-provisional")
    relation = _triple(
        span=(30, 60), line=3, claim_id="rel-provisional",
        attributes={SUBJECT_MENTION_ATTR: "subj-provisional", OBJECT_MENTION_ATTR: "obj-provisional"},
    )

    atoms = _reshape([subject, obj, relation])
    by_line = {c.doc_refs()[0].line: c for c in atoms}
    rel = by_line[3]

    assert rel.attributes is not None
    assert rel.attributes[SUBJECT_MENTION_ATTR] == by_line[1].claim_id
    assert rel.attributes[OBJECT_MENTION_ATTR] == by_line[2].claim_id


def test_retraction_target_points_at_an_atom() -> None:
    original = _triple(span=(0, 10), line=1, claim_id="orig-provisional")
    retraction = _triple(span=(20, 30), line=2, kind="retraction", targets="orig-provisional",
                         claim_id="ret-provisional")

    atoms = _reshape([original, retraction])
    minted = {c.claim_id for c in atoms}
    ret = next(c for c in atoms if c.kind == "retraction")

    assert ret.targets in minted


@pytest.mark.xfail(
    strict=False,
    reason=(
        "SPEC SILENCE (reported to the orchestrator): `dedup_within_doc` drops the non-representative "
        "members of a fold without publishing an old->new map, so a reference to a folded-away mention "
        "dangles. Item 3's principle — 'a value populated later is never silently orphaned or collapsed' "
        "— reads on the referent field; the spec never says whether the same must hold for a claim-id "
        "reference across the fold. Recorded as a latent hole, NOT as an S1 requirement."
    ),
)
def test_fold_does_not_orphan_a_reference_to_the_folded_mention() -> None:
    kept = _entity("34 sam battery", span=(0, 15), line=1, claim_id="kept")
    folded = _entity("34 sam battery", span=(0, 15), line=1, claim_id="folded")  # same signature
    dependent = _triple(span=(40, 60), line=4, kind="inference", premises=["folded"],
                        claim_id="dep-provisional")

    atoms = _reshape([kept, folded, dependent])
    minted = {c.claim_id for c in atoms}
    dep = next(c for c in atoms if c.kind == "inference")

    assert set(dep.premises) <= minted, (
        f"premise {dep.premises} points at a mention the fold discarded — an orphaned atom reference"
    )
