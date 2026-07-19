"""Canonical edge direction — the write/read-side orientation of relationship claims.

Covers the pure canonicalizer (:mod:`chanakya.edge_direction`) and the acceptance requirement from
``tmp/conv/INGEST-canonical-edge-direction-at-write.md`` §7: two oppositely-phrased sources of one fact
must land on **one** edge and corroborate after canonicalization.
"""

from __future__ import annotations

from chanakya.edge_direction import (
    DirectionRule,
    canonicalize_claim,
    canonicalize_claims,
    direction_map,
    type_index,
)
from chanakya.schemas import ClaimRecord, ConfigBundle, DocRef, EntityDescriptor, Triple
from chanakya.schemas.config_models import OntologyConfig, TypeDef
from chanakya.schemas.values import Quantity
from chanakya.store import EvidenceLog
from chanakya.view import rebuild

# ── config builders ──────────────────────────────────────────────────────────────────────────────

def _onto(*edges: dict[str, object]) -> ConfigBundle:
    """A ConfigBundle whose ontology declares the given edge types (from/to/symmetric ride as extras)."""
    return ConfigBundle(ontology=OntologyConfig(edge_types=[TypeDef(**e) for e in edges]))


# The C-flavoured directional edges the tests key on.
_BASED_AT = {"name": "based-at", "from": "unit", "to": "basing_site"}
_MANUFACTURES = {"name": "manufactures", "from": "manufacturer"}  # polymorphic object → `from` only
_COMPONENT_OF = {"name": "component-of", "from": "component", "to": "component"}  # same-type
_SAME_AS = {"name": "same-as", "symmetric": True}


# ── claim builders ─────────────────────────────────────────────────────────────────────────────

def _rel(cid: str, subj: str, pred: str, obj: str, **kw: object) -> ClaimRecord:
    return ClaimRecord(
        claim_id=cid, source_id="s", doc_ref=DocRef(file=cid),
        kind="observation", asserts="relationship",
        payload=Triple(subject=subj, predicate=pred, object=obj, **kw),
    )


def _ent(cid: str, entity_type: str, name: str) -> ClaimRecord:
    return ClaimRecord(
        claim_id=cid, source_id="s", doc_ref=DocRef(file=cid),
        kind="observation", asserts="entity",
        payload=EntityDescriptor(entity_type=entity_type, name=name),
    )


# ── direction_map: the ontology reader ────────────────────────────────────────────────────────

def test_direction_map_reads_from_to_and_skips_symmetric_and_undeclared() -> None:
    cfg = _onto(_BASED_AT, _MANUFACTURES, _SAME_AS, {"name": "substitutable-by"})
    rules = direction_map(cfg)
    assert rules["based-at"] == DirectionRule(from_type="unit", to_type="basing_site")
    assert rules["manufactures"] == DirectionRule(from_type="manufacturer", to_type=None)
    assert "same-as" not in rules          # symmetric → excluded
    assert "substitutable-by" not in rules  # declares neither from nor to → excluded


def test_direction_map_empty_when_no_directions_declared() -> None:
    assert direction_map(ConfigBundle()) == {}


# ── type_index: endpoint typing from entities + gazetteer ─────────────────────────────────────

def test_type_index_prefers_entity_claims_then_gazetteer() -> None:
    cfg = _onto(_BASED_AT)
    idx = type_index([_ent("e1", "unit", "8th Bn"), _ent("e2", "basing_site", "Rahwali")], cfg)
    assert idx == {"8th Bn": "unit", "Rahwali": "basing_site"}


# ── canonicalize_claim: the per-claim decision ────────────────────────────────────────────────

_RULES = {"based-at": DirectionRule("unit", "basing_site"),
          "manufactures": DirectionRule("manufacturer", None),
          "component-of": DirectionRule("component", "component")}
_TYPE_OF = {"8th Bn": "unit", "Rahwali": "basing_site",
            "CPMIEC": "manufacturer", "HQ-9": "variant",
            "comp_seeker": "component", "comp_radar": "component"}.get


def test_reversed_edge_is_flipped() -> None:
    claim = _rel("c1", "Rahwali", "based-at", "8th Bn")  # site->unit (reversed)
    out = canonicalize_claim(claim, _RULES, _TYPE_OF)
    assert (out.payload.subject, out.payload.object) == ("8th Bn", "Rahwali")
    assert out.payload.predicate == "based-at"  # label never changes
    assert out.claim_id == "c1" and out.doc_ref == claim.doc_ref  # provenance intact


def test_canonical_edge_is_untouched_same_object() -> None:
    claim = _rel("c2", "8th Bn", "based-at", "Rahwali")  # already canonical
    assert canonicalize_claim(claim, _RULES, _TYPE_OF) is claim


def test_polymorphic_object_edge_flips_on_the_fixed_end() -> None:
    # manufactures declares only `from: manufacturer`; a reversed claim has the manufacturer in the object.
    rev = _rel("c3", "HQ-9", "manufactures", "CPMIEC")
    out = canonicalize_claim(rev, _RULES, _TYPE_OF)
    assert (out.payload.subject, out.payload.object) == ("CPMIEC", "HQ-9")
    ok = _rel("c4", "CPMIEC", "manufactures", "HQ-9")
    assert canonicalize_claim(ok, _RULES, _TYPE_OF) is ok


def test_same_type_edge_never_flipped() -> None:
    claim = _rel("c5", "comp_radar", "component-of", "comp_seeker")
    assert canonicalize_claim(claim, _RULES, _TYPE_OF) is claim  # type cannot disambiguate direction


def test_object_value_triple_never_flipped() -> None:
    # object is a structured value, not a typed node → no direction to fix, even if types would suggest one.
    claim = _rel("c6", "Rahwali", "based-at", "8th Bn", object_value=Quantity(min=1, max=2))
    assert canonicalize_claim(claim, _RULES, _TYPE_OF) is claim


def test_untypable_endpoints_left_as_written() -> None:
    claim = _rel("c7", "mystery", "based-at", "unknown")
    assert canonicalize_claim(claim, _RULES, {}.get) is claim


def test_symmetric_predicate_left_as_written() -> None:
    claim = _rel("c8", "b", "same-as", "a")
    assert canonicalize_claim(claim, {}, _TYPE_OF) is claim  # not in the rule map → untouched


# ── canonicalize_claims: the batch no-op guarantee ────────────────────────────────────────────

def test_batch_no_op_when_no_directions_declared_returns_same_list() -> None:
    claims = [_rel("c1", "Rahwali", "based-at", "8th Bn")]
    assert canonicalize_claims(claims, ConfigBundle()) is claims  # byte-stable on an un-adopted ontology


def test_batch_types_from_its_own_entity_claims() -> None:
    cfg = _onto(_BASED_AT)
    claims = [
        _ent("e1", "unit", "8th Bn"), _ent("e2", "basing_site", "Rahwali"),
        _rel("r1", "Rahwali", "based-at", "8th Bn"),  # reversed → should flip
    ]
    out = {c.claim_id: c for c in canonicalize_claims(claims, cfg)}
    assert (out["r1"].payload.subject, out["r1"].payload.object) == ("8th Bn", "Rahwali")


# ── acceptance: oppositely-phrased sources co-locate on one edge (spec §7.2) ───────────────────

def test_opposite_phrasings_corroborate_on_one_edge_after_rebuild() -> None:
    cfg = _onto(_BASED_AT)
    log = EvidenceLog()
    log.append_many([
        _ent("e1", "unit", "8th Bn"), _ent("e2", "basing_site", "Rahwali"),
        _rel("src_a", "8th Bn", "based-at", "Rahwali"),   # "unit at site"
        _rel("src_b", "Rahwali", "based-at", "8th Bn"),   # "site hosts unit" — flipped phrasing, same fact
    ])
    view = rebuild(log, [], cfg)
    based_at = [e for e in view.edges if e.type == "based-at"]
    assert len(based_at) == 1, "the two phrasings must resolve to a single edge"
    assert set(based_at[0].claim_ids) == {"src_a", "src_b"}  # one edge, two corroborating looks
    # Canonical direction is unit -> site. Assert it by NODE TYPE, not by designator string: RESOLVE
    # inducts each endpoint as a mention and rewrites it to the resolved entity id (RES-1), so the edge
    # now carries ids rather than the raw text — the direction is the invariant, the spelling is not.
    by_id = {n.id: n for n in view.nodes}
    assert by_id[based_at[0].source].type == "unit"
    assert by_id[based_at[0].target].type == "basing_site"
    assert (by_id[based_at[0].source].name, by_id[based_at[0].target].name) == ("8th Bn", "Rahwali")


def test_without_the_convention_phrasings_split_into_two_edges() -> None:
    # Guardrail: an ontology that does NOT declare direction leaves the two phrasings on two edges — the
    # exact silent failure the convention closes (proves the acceptance test above isn't vacuous).
    cfg = ConfigBundle(ontology=OntologyConfig(edge_types=[TypeDef(name="based-at")]))
    log = EvidenceLog()
    log.append_many([
        _rel("src_a", "8th Bn", "based-at", "Rahwali"),
        _rel("src_b", "Rahwali", "based-at", "8th Bn"),
    ])
    view = rebuild(log, [], cfg)
    assert len([e for e in view.edges if e.type == "based-at"]) == 2
