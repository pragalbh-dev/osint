"""RESOLVE honours in-document coreference — "authoritative-unless-contradicted", narrowly.

The reconciliation of INGEST extraction pass 2 (``ingest/coref.py``) with the Phase-3 resolver. The
policy, and what each test pins:

* **Opt-in, not on by default.** Phase 3 made every identity signal raise-only and enforced it
  structurally (D-2.5). Coreference may cross that line only for evidence categories an operator names in
  ``resolution.yaml``; with none named, a cluster behaves exactly like a source-asserted ``same-as``.
* **Only what the document *states*.** ``EXPLICIT_EQUIVALENCE`` — an apposition/acronym expansion with a
  quotable span — may bootstrap. ``NAME_VARIANT`` and ``UNAMBIGUOUS_ANAPHOR`` are the extractor
  *interpreting*, so they stay raise-only however the config is set.
* **Authoritative is never unconditional.** A stated ``distinct-from`` drops the pair outright; a type,
  namespace or hard-attribute contradiction **demotes** it to the analyst queue rather than deleting it —
  the evidence still reaches a human.
"""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.schemas import ConfigBundle
from tests.resolve._helpers import coref, entity, mk_config, triple

_EXPLICIT = "EXPLICIT_EQUIVALENCE"
_VARIANT = "NAME_VARIANT"
_ANAPHOR = "UNAMBIGUOUS_ANAPHOR"


def _cluster_of(part, eid: str) -> set[str]:
    members = {eid}
    for a, b in part.same_as:
        if a in members or b in members:
            members |= {a, b}
    for k, v in part.entity_canonical.items():
        if k in members or v in members:
            members |= {k, v}
    return members


def _merged(part, a: str, b: str) -> bool:
    return b in _cluster_of(part, a)


def _queued(part, a: str, b: str) -> bool:
    return any({x, y} == {a, b} for x, y in part.candidates)


def _authoritative(**kw) -> ConfigBundle:
    return mk_config(coref_authoritative_evidence=[_EXPLICIT], **kw)


def _eid(etype: str, name: str) -> str:
    """The id an entity claim actually lands on in production (``entities.base_ref``).

    Tests must use it rather than a synthetic id: a triple endpoint is resolved to ``ent:<type>:<form>``
    (``resolve._link_endpoints``), so a synthetic id would leave the coreference edge pointing at freshly
    minted, attribute-less twins — and every rail that reads attributes would silently pass.
    """
    return f"ent:{etype}:{name}"


def _ent(etype: str, name: str, **attrs):
    return entity(_eid(etype, name), etype, name, **attrs)


#: Two mentions of one exporter that share no token — unreachable by containment, acronym or alias.
_CPMIEC = _eid("manufacturer", "CPMIEC")
_AGENCY = _eid("manufacturer", "the export agency")


def _two_mentions() -> list:
    return [_ent("manufacturer", "CPMIEC"), _ent("manufacturer", "the export agency")]


# ── opt-in ─────────────────────────────────────────────────────────────────────────────────────

def test_coreference_does_not_auto_merge_when_no_category_is_opted_in() -> None:
    """Default config ⇒ Phase-3's raise-only discipline is untouched: queued for an analyst, not merged."""
    part = resolve([*_two_mentions(), coref("CPMIEC", "the export agency")], mk_config())
    assert not _merged(part, _CPMIEC, _AGENCY)
    assert _queued(part, _CPMIEC, _AGENCY)


def test_explicit_equivalence_auto_merges_when_opted_in() -> None:
    """The whole point: a quotable stated equivalence merges two names no string method can connect."""
    part = resolve([*_two_mentions(), coref("CPMIEC", "the export agency")], _authoritative())
    assert _merged(part, _CPMIEC, _AGENCY)


def test_interpretive_categories_stay_raise_only_even_when_explicit_is_opted_in() -> None:
    """Opting in to what a document *states* must not also opt in to what the extractor *inferred*."""
    for evidence in (_VARIANT, _ANAPHOR):
        claims = [*_two_mentions(), coref("CPMIEC", "the export agency", evidence=evidence)]
        part = resolve(claims, _authoritative())
        assert not _merged(part, _CPMIEC, _AGENCY), evidence
        assert _queued(part, _CPMIEC, _AGENCY), evidence


def test_unknown_evidence_category_is_never_authoritative() -> None:
    """An unrecognised category is not a licence to merge — it falls back to the queue."""
    claims = [*_two_mentions(), coref("CPMIEC", "the export agency", evidence="VIBES")]
    assert not _merged(resolve(claims, _authoritative()), _CPMIEC, _AGENCY)


# ── the rails: contradiction demotes, veto drops ───────────────────────────────────────────────

def test_stated_distinct_from_outranks_an_authoritative_cluster() -> None:
    """A do-not-merge the corpus states beats any reading of the prose — and is not even queued."""
    claims = [
        *_two_mentions(),
        triple("CPMIEC", "distinct-from", "the export agency"),
        coref("CPMIEC", "the export agency"),
    ]
    part = resolve(claims, _authoritative())
    assert not _merged(part, _CPMIEC, _AGENCY)
    assert not _queued(part, _CPMIEC, _AGENCY)


def test_configured_distinct_from_trap_survives_an_authoritative_cluster() -> None:
    """The flagship traps must hold however a document phrases things (FD-2000 ≠ FT-2000)."""
    claims = [
        _ent("variant", "FD-2000"),
        _ent("variant", "FT-2000"),
        coref("FD-2000", "FT-2000"),
    ]
    part = resolve(claims, _authoritative(distinct_from={"FD-2000": ["FT-2000"]}))
    assert not _merged(part, _eid("variant", "FD-2000"), _eid("variant", "FT-2000"))


def test_hard_attribute_contradiction_demotes_to_the_analyst_queue() -> None:
    """Looks coreferent but the stated origin countries disagree ⇒ a human decides, and still sees it."""
    claims = [
        _ent("manufacturer", "CPMIEC", origin_country="China"),
        _ent("manufacturer", "the export agency", origin_country="Pakistan"),
        coref("CPMIEC", "the export agency"),
    ]
    cfg = _authoritative(attribute_rules={"manufacturer": {"conflict": ["origin_country"]}})
    part = resolve(claims, cfg)
    assert not _merged(part, _CPMIEC, _AGENCY)
    assert _queued(part, _CPMIEC, _AGENCY)


def test_incompatible_namespace_demotes_to_the_analyst_queue() -> None:
    """Two *stated* and different namespaces are a contradiction the document's prose cannot settle."""
    claims = [
        _ent("manufacturer", "CPMIEC", country="China"),
        _ent("manufacturer", "the export agency", country="Pakistan"),
        coref("CPMIEC", "the export agency"),
    ]
    part = resolve(claims, _authoritative())
    assert not _merged(part, _CPMIEC, _AGENCY)


def test_cross_type_coreference_never_merges() -> None:
    """A manufacturer and a variant are not one entity, whatever the extractor proposed."""
    claims = [
        _ent("manufacturer", "CPMIEC"),
        _ent("variant", "HQ-9/P"),
        coref("CPMIEC", "HQ-9/P"),
    ]
    assert not _merged(resolve(claims, _authoritative()), _CPMIEC, _eid("variant", "HQ-9/P"))


def test_an_absent_attribute_is_not_a_contradiction() -> None:
    """Absence is not disagreement — a one-sided attribute must not block a stated equivalence."""
    claims = [
        _ent("manufacturer", "CPMIEC", origin_country="China"),
        _ent("manufacturer", "the export agency"),
        coref("CPMIEC", "the export agency"),
    ]
    cfg = _authoritative(attribute_rules={"manufacturer": {"conflict": ["origin_country"]}})
    assert _merged(resolve(claims, cfg), _CPMIEC, _AGENCY)


# ── the view: consumed, not drawn ──────────────────────────────────────────────────────────────

def test_coreference_is_consumed_not_drawn_as_an_edge() -> None:
    """Like ``same-as`` (D-2.5/P3.2): identity is answered by merging, never by a parallel edge."""
    from chanakya.store import EvidenceLog
    from chanakya.view import rebuild

    log = EvidenceLog(":memory:")
    log.append_many([*_two_mentions(), coref("CPMIEC", "the export agency")])
    view = rebuild(log, [], _authoritative())
    assert [e for e in view.edges if e.type == "coref-same-as"] == []
