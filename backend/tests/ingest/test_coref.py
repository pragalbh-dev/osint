"""In-document coreference (extraction pass 2) — the emission contract and every over-merge rail.

Offline + deterministic (gate G10): a :class:`ScriptedExtractionClient` replays the pass-1 fill and then
the pass-2 cluster proposal over a synthetic document whose text we control, so the licensing-quote check
is exercised against real text. The beats asserted here:

* **dormant by default** — the shipped config carries no ``coreference`` block, so extraction makes exactly
  ONE call and emits nothing new (this is what makes the slice a no-op until RESOLVE is reconciled).
* **its own lane** — a cluster is written on ``coref-same-as``, NEVER ``same-as``. That separation is the
  whole point: ``resolve.scoring`` weighs ``same-as`` as one term of ``merge_score``, so writing there would
  dilute a context-licensed decision into a partial score.
* **the rails** — no quotable span, an unknown evidence kind, a cross-type pair, a stated distinction, a
  lone member, an invented mention id, or an overlapping cluster each drop the merge (under-merge is cheap).
* **mention-keyed provenance** — relations carry the mention that named each endpoint, those refs survive
  id reassignment, and they swap when a triple is reoriented.
"""

from __future__ import annotations

from typing import Any

import pytest

from chanakya import edge_direction, settings
from chanakya.config.store import ConfigStore
from chanakya.ingest import adapters, coref, loaders
from chanakya.ingest.client import ScriptedExtractionClient
from chanakya.ingest.dedup import assign_claim_ids
from chanakya.ingest.extract import extract_document
from chanakya.schemas.claim import ClaimRecord, Triple
from chanakya.schemas.config_models import ConfigBundle

_TEXT = (
    "China Precision Machinery Import-Export Corporation (CPMIEC) signed the contract.\n"
    "The export agency delivered the battery to Rahwali in March.\n"
)


# ── fixtures ───────────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _offline_geocoder(monkeypatch: pytest.MonkeyPatch) -> None:
    """No adapter may hit Nominatim (offline determinism)."""
    monkeypatch.setattr(adapters, "_default_geocoder", lambda: None)


@pytest.fixture(scope="module")
def config() -> ConfigBundle:
    """The real shipped config — ``coreference`` is deliberately absent from it (dormant)."""
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _enabled(config: ConfigBundle, **knobs: Any) -> ConfigBundle:
    """The same config with the pass switched on — the one block a deployment adds to opt in.

    An *empty* block reads as dormant (the ``attribution_proposer`` precedent), so the default here spells
    the categories out, exactly as the commented-out block in ``config/credibility.yaml`` does.
    """
    knobs.setdefault("categories", list(coref.EVIDENCE_CATEGORIES))
    credibility = config.credibility.model_copy(update={"coreference": knobs})
    return config.model_copy(update={"credibility": credibility})


def _doc() -> loaders.LoadedDoc:
    return loaders.load_document(_TEXT, file="t.txt")


#: Pass-1 fill: two manufacturer mentions of one actor, plus a relation naming an undeclared endpoint.
_FILL: dict[str, Any] = {
    "manufacturers": [
        {"name": "China Precision Machinery Import-Export Corporation",
         "source_quote": "China Precision Machinery Import-Export Corporation (CPMIEC)"},
        {"name": "CPMIEC", "source_quote": "(CPMIEC)"},
    ],
}


def _cluster(*, members: list[int], evidence: str = coref.EXPLICIT_EQUIVALENCE,
             quote: str = "China Precision Machinery Import-Export Corporation (CPMIEC)") -> dict[str, Any]:
    return {"clusters": [{"member_ids": members, "evidence": evidence, "licensing_quote": quote}]}


def _extract(config: ConfigBundle, *responses: dict[str, Any]) -> list[ClaimRecord]:
    return extract_document(
        _doc(), source_id="d01", source_type="analytic", config=config,
        client=ScriptedExtractionClient(list(responses)), format_hint="prose_claim",
    )


def _coref_edges(claims: list[ClaimRecord]) -> list[ClaimRecord]:
    return [c for c in claims
            if isinstance(c.payload, Triple) and c.payload.predicate == coref.COREF_PREDICATE]


# ── dormancy: the slice changes nothing until a deployment opts in ─────────────────────────────

def test_dormant_by_default_makes_no_second_call(config: ConfigBundle) -> None:
    """The shipped config has no ``coreference`` block ⇒ exactly ONE extraction call, no coref claims.

    A scripted client raises when over-drawn, so a single queued response *is* the assertion that pass 2
    never fired.
    """
    claims = _extract(config, _FILL)
    assert _coref_edges(claims) == []
    assert claims, "pass 1 must still emit normally"


def test_dormant_when_categories_configured_empty(config: ConfigBundle) -> None:
    """A block that allows no evidence kind is dormant too — never a silent fall-back to all of them."""
    assert _extract(_enabled(config, categories=[]), _FILL) == _extract(config, _FILL)


# ── the happy path: a cluster on its own lane, licensed by a quote ─────────────────────────────

def test_emits_coref_edge_on_its_own_lane(config: ConfigBundle) -> None:
    """An explicit equivalence yields one ``coref-same-as`` inference — never ``same-as``."""
    claims = _extract(_enabled(config), _FILL, _cluster(members=[1, 2]))
    edges = _coref_edges(claims)
    assert len(edges) == 1
    edge = edges[0]
    assert edge.kind == "inference"
    assert edge.payload.predicate == coref.COREF_PREDICATE != "same-as"
    assert {edge.payload.subject, edge.payload.object} == {
        "China Precision Machinery Import-Export Corporation", "CPMIEC"}
    assert edge.attributes[coref.EVIDENCE_ATTR] == coref.EXPLICIT_EQUIVALENCE
    assert edge.attributes[coref.QUOTE_ATTR] in _TEXT
    assert edge.attributes[coref.CLUSTER_ATTR] == "c1"


def test_coref_edge_cites_the_licensing_span_and_its_members(config: ConfigBundle) -> None:
    """Provenance (G4): the doc_ref slices back to the licensing text; premises name both mentions."""
    claims = _extract(_enabled(config), _FILL, _cluster(members=[1, 2]))
    edge = _coref_edges(claims)[0]
    ref = edge.doc_refs()[0]
    assert ref.span is not None and _TEXT[ref.span[0]:ref.span[1]] == edge.attributes[coref.QUOTE_ATTR]
    entity_ids = {c.claim_id for c in claims if c.asserts == "entity"}
    assert len(edge.premises) == 2 and set(edge.premises) <= entity_ids


def test_pass_one_claims_are_untouched(config: ConfigBundle) -> None:
    """Additive by construction: enabling pass 2 only ever *adds* claims — it never mutates pass 1's."""
    base = _extract(config, _FILL)
    with_coref = _extract(_enabled(config), _FILL, _cluster(members=[1, 2]))
    assert with_coref[:len(base)] == base


def test_rescues_an_undeclared_descriptive_mention(config: ConfigBundle) -> None:
    """The actual leak: a relation endpoint the document never declared still enters the inventory."""
    fill = {**_FILL, "relations": [
        {"relation": "manufactures", "subject": "the export agency", "object": "HQ-9/P",
         "source_quote": "The export agency delivered the battery to Rahwali in March."}]}
    mentions = coref.inventory(_extract(config, fill))
    undeclared = [m for m in mentions if m.claim_id is None]
    assert "the export agency" in {m.name for m in undeclared}


def test_undeclared_endpoints_are_typed_from_the_ontology(config: ConfigBundle) -> None:
    """The ontology types what the document did not declare, so the same-type rail still bites.

    ``manufactures`` is declared manufacturer→variant, so an undeclared subject/object is typed from the
    edge rather than left ``unknown``. Without this, two undeclared mentions are indistinguishable to the
    type rail and nothing deterministic blocks merging a manufacturer with a missile variant.
    """
    fill = {"relations": [
        {"relation": "manufactures", "subject": "CPMIEC", "object": "HQ-9/P",
         "source_quote": "China Precision Machinery Import-Export Corporation (CPMIEC) signed the contract."}]}
    rules = edge_direction.direction_map(config)
    typed = {m.name: m.entity_type for m in coref.inventory(_extract(config, fill), rules)}
    assert typed["CPMIEC"] == "manufacturer"
    assert typed["HQ-9/P"] == "variant"


def test_ontology_typing_blocks_merging_a_manufacturer_with_a_variant(config: ConfigBundle) -> None:
    """The rail this typing buys: a cross-type merge of two *undeclared* mentions is refused."""
    fill = {"relations": [
        {"relation": "manufactures", "subject": "CPMIEC", "object": "HQ-9/P",
         "source_quote": "China Precision Machinery Import-Export Corporation (CPMIEC) signed the contract."}]}
    edges = _coref_edges(_extract(_enabled(config), fill, _cluster(members=[1, 2])))
    assert edges == []


# ── the over-merge rails (each drops the merge; under-merge is the cheap direction) ────────────

@pytest.mark.parametrize(
    ("response", "why"),
    [
        (_cluster(members=[1, 2], quote="a quote that is nowhere in this document"), "unquotable span"),
        (_cluster(members=[1, 2], evidence="VIBES"), "unknown evidence kind"),
        (_cluster(members=[1]), "a lone member is a singleton, not a merge"),
        (_cluster(members=[1, 99]), "an invented mention id"),
        ({"clusters": [{"member_ids": [1, 2], "evidence": coref.NAME_VARIANT}]}, "no quote at all"),
        ({"clusters": []}, "nothing proposed"),
        ({}, "an empty fill"),
    ],
)
def test_rail_drops_the_merge(config: ConfigBundle, response: dict[str, Any], why: str) -> None:
    assert _coref_edges(_extract(_enabled(config), _FILL, response)) == [], f"should drop: {why}"


def test_categories_config_restricts_what_may_be_emitted(config: ConfigBundle) -> None:
    """Running conservative (no anaphora) must drop an anaphoric cluster, and keep an explicit one."""
    conservative = _enabled(config, categories=[coref.EXPLICIT_EQUIVALENCE])
    anaphor = _cluster(members=[1, 2], evidence=coref.UNAMBIGUOUS_ANAPHOR)
    assert _coref_edges(_extract(conservative, _FILL, anaphor)) == []
    assert len(_coref_edges(_extract(conservative, _FILL, _cluster(members=[1, 2])))) == 1


def test_max_mentions_skips_the_document_whole(config: ConfigBundle) -> None:
    """The cost guard skips an outsized inventory rather than truncating it (no silent partial coverage)."""
    assert _extract(_enabled(config, max_mentions=1), _FILL) == _extract(config, _FILL)


# ── unit-level rails over the inventory (cross-type + stated distinctions) ─────────────────────

def _mentions() -> list[coref.Mention]:
    return [
        coref.Mention(1, "CPMIEC", "manufacturer", "d01-l1-1"),
        coref.Mention(2, "China Precision Machinery Import-Export Corporation", "manufacturer", "d01-l1-2"),
        coref.Mention(3, "Rahwali", "basing_site", "d01-l2-3"),
        coref.Mention(4, "the export agency", coref.UNKNOWN_TYPE, None),
    ]


def _proposal(members: list[int]) -> dict[str, Any]:
    return {"clusters": [{"member_ids": members, "evidence": coref.EXPLICIT_EQUIVALENCE,
                          "licensing_quote": "(CPMIEC)"}]}


def test_never_merges_across_entity_types() -> None:
    """A manufacturer can only merge with a manufacturer — type restriction is enforced here, not trusted."""
    assert coref.valid_clusters(_proposal([1, 3]), _mentions(), _TEXT, []) == []


def test_an_undeclared_mention_may_join_one_typed_cluster() -> None:
    """``unknown`` is the descriptive reference — it may join a typed cluster (that is the whole feature)."""
    assert len(coref.valid_clusters(_proposal([1, 4]), _mentions(), _TEXT, [])) == 1


def test_stated_distinction_is_a_hard_veto() -> None:
    """The document saying two things are different outranks the model saying they are the same."""
    distinct = [("CPMIEC", "China Precision Machinery Import-Export Corporation")]
    assert coref.valid_clusters(_proposal([1, 2]), _mentions(), _TEXT, distinct) == []


def test_overlapping_clusters_keep_only_the_first() -> None:
    """The partition stays closed: a mention lands in exactly one cluster, conservatively the first."""
    raw = {"clusters": [
        {"member_ids": [1, 2], "evidence": coref.EXPLICIT_EQUIVALENCE, "licensing_quote": "(CPMIEC)"},
        {"member_ids": [2, 4], "evidence": coref.EXPLICIT_EQUIVALENCE, "licensing_quote": "(CPMIEC)"},
    ]}
    accepted = coref.valid_clusters(raw, _mentions(), _TEXT, [])
    assert len(accepted) == 1
    members, _evidence, _quote = accepted[0]
    assert [m.local_id for m in members] == [1, 2]


def test_a_wholly_undeclared_cluster_is_kept() -> None:
    """The dominant real-corpus shape: on the frozen view both ``CPMIEC`` and its expansion reach the graph
    only as relation endpoints, so a cluster of purely undeclared mentions is exactly the leak to close."""
    orphans = [coref.Mention(1, "CPMIEC", coref.UNKNOWN_TYPE, None),
               coref.Mention(2, "China Precision Machinery Import-Export Corporation",
                             coref.UNKNOWN_TYPE, None)]
    assert len(coref.valid_clusters(_proposal([1, 2]), orphans, _TEXT, [])) == 1


def test_undeclared_cluster_is_an_observation_not_a_dangling_inference(config: ConfigBundle) -> None:
    """With no upstream claim to cite it must NOT claim to be an inference — kind follows what it can cite."""
    fill = {"relations": [
        {"relation": "manufactures", "subject": "CPMIEC", "object": "HQ-9/P",
         "source_quote": "China Precision Machinery Import-Export Corporation (CPMIEC) signed the contract."},
        {"relation": "manufactures", "subject": "China Precision Machinery Import-Export Corporation",
         "object": "HQ-9/P", "source_quote": "The export agency delivered the battery to Rahwali in March."},
    ]}
    # Inventory order is 1=CPMIEC, 2=HQ-9/P (the shared object), 3=the full expansion — so the two
    # coreferent manufacturer mentions are 1 and 3.
    edges = _coref_edges(_extract(_enabled(config), fill, _cluster(members=[1, 3])))
    assert len(edges) == 1
    assert edges[0].kind == "observation" and edges[0].premises == []
    assert edges[0].attributes[coref.QUOTE_ATTR] in _TEXT
    assert {edges[0].payload.subject, edges[0].payload.object} == {
        "CPMIEC", "China Precision Machinery Import-Export Corporation"}


# ── mention-keyed provenance on ordinary relations ─────────────────────────────────────────────

def test_relations_carry_the_mention_that_named_each_endpoint(config: ConfigBundle) -> None:
    """Each endpoint is anchored to its mention, *in addition to* the verbatim surface string."""
    fill = {
        "manufacturers": [{"name": "CPMIEC", "source_quote": "(CPMIEC)"}],
        "variants": [{"name": "HQ-9/P", "source_quote": "the battery"}],
        "relations": [{"relation": "manufactures", "subject": "CPMIEC", "object": "HQ-9/P",
                       "source_quote": "China Precision Machinery Import-Export Corporation (CPMIEC)"}],
    }
    claims = _extract(config, fill)
    by_name = {c.payload.name: c.claim_id for c in claims if c.asserts == "entity"}
    relation = next(c for c in claims
                    if isinstance(c.payload, Triple) and c.payload.predicate == "manufactures")
    assert relation.attributes[edge_direction.SUBJECT_MENTION_ATTR] == by_name["CPMIEC"]
    assert relation.attributes[edge_direction.OBJECT_MENTION_ATTR] == by_name["HQ-9/P"]
    assert relation.payload.subject == "CPMIEC"  # the surface form is never replaced


def test_mention_refs_survive_id_reassignment(config: ConfigBundle) -> None:
    """The refs are claim ids, so they must follow ``assign_claim_ids`` — never dangle (the remap contract)."""
    claims = _extract(_enabled(config), _FILL, _cluster(members=[1, 2]))
    reassigned = assign_claim_ids(claims, doc_id="d01")
    ids = {c.claim_id for c in reassigned}
    for claim in reassigned:
        for key in (edge_direction.SUBJECT_MENTION_ATTR, edge_direction.OBJECT_MENTION_ATTR):
            ref = (claim.attributes or {}).get(key)
            if ref is not None:
                assert ref in ids, f"{key} dangling after id reassignment"
        assert set(claim.premises) <= ids


# ── the lane separation, proven against the real resolver ──────────────────────────────────────

def test_coref_lane_is_inert_to_the_resolvers_merge_scoring() -> None:
    """The load-bearing separation: ``same-as`` feeds ``source_asserted``; ``coref-same-as`` must not.

    This is why the cluster does not ride the ordinary identity vocabulary. Written on ``same-as`` it would
    become one *weighted term* of ``merge_score`` — a context-licensed extractor decision silently diluted
    into a partial score that attribute-dissimilarity can outvote. On its own lane it is invisible to the
    scorer, so merge behaviour is provably unchanged until the RESOLVE honor policy reads it deliberately.
    """
    from chanakya.resolve.entities import Edge, Entity, EntityGraph
    from chanakya.resolve.scoring import source_asserted_score

    def graph(predicate: str) -> EntityGraph:
        entities = {e: Entity(eid=e, etype="manufacturer", name=e) for e in ("a", "b")}
        return EntityGraph(entities=entities,
                           edges=[Edge("a", predicate, "b", edge_instance=None, latest_iso=None)])

    assert source_asserted_score(graph("same-as"), "a", "b") == 1.0, "precondition: same-as IS scored"
    assert source_asserted_score(graph(coref.COREF_PREDICATE), "a", "b") == 0.0


def test_mention_refs_swap_when_a_triple_is_reoriented() -> None:
    """The refs are positional, so a reorientation must carry them across or they point at the wrong end."""
    attributes = {edge_direction.SUBJECT_MENTION_ATTR: "a", edge_direction.OBJECT_MENTION_ATTR: "b"}
    swapped = edge_direction.swap_mention_refs(attributes)
    assert swapped[edge_direction.SUBJECT_MENTION_ATTR] == "b"
    assert swapped[edge_direction.OBJECT_MENTION_ATTR] == "a"


def test_swap_drops_a_ref_the_other_end_does_not_have() -> None:
    """A one-sided ref must not duplicate onto both ends when the endpoints flip."""
    swapped = edge_direction.swap_mention_refs({edge_direction.SUBJECT_MENTION_ATTR: "a"})
    assert edge_direction.SUBJECT_MENTION_ATTR not in swapped
    assert swapped[edge_direction.OBJECT_MENTION_ATTR] == "a"
