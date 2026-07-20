"""T3b — the fragmentation / merge-noise defects, each pinned so it stays fixed.

Six defects, one theme: the resolver was being asked to decide identity questions the *designed schema*
should never have posed. An air-defence sector and an air-defence centre were the same node type; a
Jaccard over a one-element neighbourhood read as a perfect match; three distinct bills of lading had no
hard rail; a surface form two documents typed differently was abandoned untyped and rendered nameless.

Each test states the invariant in the form the design docs use, not a transcript of the current corpus.
"""

from __future__ import annotations

from chanakya.ontology import NodeTypeIndex
from chanakya.resolve import resolve
from chanakya.resolve.entities import build as build_entity_graph
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.resolve.scoring import merge_score
from chanakya.schemas import OntologyConfig, TypeDef
from tests.resolve._helpers import entity, mk_config, triple

# ── the ontology under test: the two node-type identity blocks T3b adds ────────────────────────
#
# Mirrors config/ontology.yaml's shape (extra="allow" fields on a TypeDef) without importing it, so the
# tests pin the MECHANISM and stay readable if the authored marker list grows.

AREA_ONTOLOGY = OntologyConfig(
    node_types=[
        TypeDef(name="basing_site"),
        TypeDef(
            name="area_of_operations",
            refines="basing_site",
            identity={
                "name_head_markers": ["sector", "belt", "zone", "province"],
                "named_instances": ["Punjab", "Sindh"],
                "relational": False,
            },
        ),
        TypeDef(
            name="contract_import_event",
            identity={"identifier_patterns": [r"[A-Za-z0-9\[\]]+(?:[-/][A-Za-z0-9\[\]]+){2,}"]},
        ),
        TypeDef(name="component"),
        TypeDef(name="variant"),
    ],
    edge_types=[
        TypeDef(name="based-at", **{"from": "unit", "to": "basing_site"}, extractor=True),
        TypeDef(name="observed-at", **{"from": ["variant", "component"], "to": "basing_site"}, extractor=True),
        TypeDef(name="equips", **{"from": "component", "to": "variant"}, extractor=True),
    ],
)


def _candidate_pairs(part) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.candidates}


def _veto_pairs(part) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.distinct_from}


def _cluster_of(part, eid: str) -> set[str]:
    members = {eid}
    for a, b in part.same_as:
        if a in members or b in members:
            members |= {a, b}
    for k, v in part.entity_canonical.items():
        if k in members or v in members:
            members |= {k, v}
    return members


# ── A. an area of operations is not a basing site ──────────────────────────────────────────────

def test_area_markers_retype_only_head_nouns() -> None:
    """A name whose HEAD is an area word is an area; one that merely mentions a province is not.

    The distinction matters because the corpus's real emplacement carries a full admin hierarchy in its
    name ("…, Malir District, Karachi, Sindh Province, Pakistan"). A substring rule would retype the one
    genuinely pad-precise site in the graph into an area — the exact opposite of md/13's precision spec.
    """
    ntx = NodeTypeIndex(AREA_ONTOLOGY)
    assert ntx.refine("basing_site", "Karachi air defence sector") == "area_of_operations"
    assert ntx.refine("basing_site", "Karachi coastal air defence belt") == "area_of_operations"
    assert ntx.refine("basing_site", "Punjab") == "area_of_operations"  # bare admin polity
    assert ntx.refine("basing_site", "Sargodha") == "basing_site"
    assert (
        ntx.refine(
            "basing_site",
            "Probable Long-Range SAM Emplacement, Malir District, Karachi, Sindh Province, Pakistan",
        )
        == "basing_site"
    )
    # a refinement only ever applies to its declared base type
    assert ntx.refine("component", "Karachi air defence sector") == "component"


def test_an_area_and_a_site_are_never_offered_as_duplicates() -> None:
    """The user-visible defect: an AD Centre, a sector and a coastal belt proposed as one another.

    They are three different kinds of thing, so the pair is not an open identity question at all — it is
    a type error that should never have reached the analyst's queue.
    """
    cfg = mk_config(ontology=AREA_ONTOLOGY, relational_support_k=2)
    claims = [
        entity("centre", "basing_site", "Army Air Defence Centre, Karachi"),
        entity("sector", "basing_site", "Karachi air defence sector"),
        entity("belt", "basing_site", "Karachi coastal air defence belt"),
        # they all sit under the same equipment, which is what made them look identical
        entity("tel", "component", "TEL"),
        triple("tel", "observed-at", "centre"),
        triple("tel", "observed-at", "sector"),
        triple("tel", "observed-at", "belt"),
    ]
    part = resolve(claims, cfg)
    pairs = _candidate_pairs(part)
    assert frozenset({"centre", "sector"}) not in pairs
    assert frozenset({"centre", "belt"}) not in pairs
    # ...and none of them were silently merged either
    assert _cluster_of(part, "centre") == {"centre"}


def test_two_areas_sharing_one_neighbour_are_not_a_merge_candidate() -> None:
    """`Punjab <-> Sindh` — two provinces — was an active pending merge suggestion.

    Nothing about the names agreed; the pair reached the queue purely because both are objects of the
    same `observed-at`. For an AREA that shared neighbour is a fact about the equipment's dispersal.
    """
    cfg = mk_config(ontology=AREA_ONTOLOGY, relational_support_k=2)
    claims = [
        entity("punjab", "basing_site", "Punjab"),
        entity("sindh", "basing_site", "Sindh"),
        entity("tel", "component", "TEL"),
        triple("tel", "observed-at", "punjab"),
        triple("tel", "observed-at", "sindh"),
    ]
    part = resolve(claims, cfg)
    assert frozenset({"punjab", "sindh"}) not in _candidate_pairs(part)
    assert _cluster_of(part, "punjab") == {"punjab"}


# ── B. an identical surface string must not be abandoned as an untyped mention ──────────────────

def test_ontology_settles_a_contradictorily_typed_endpoint() -> None:
    """One document calls HT-233 a component, another a variant — so the mention resolved to nothing.

    The predicate settles it without a guess: the form is the SUBJECT of `equips`, whose domain is
    `component`, so `variant` is not an admissible reading here. The endpoint reaches the component it
    was always identical to, with no LLM call and no coreference pass.
    """
    cfg = mk_config(ontology=AREA_ONTOLOGY, relational_support_k=2)
    claims = [
        entity("ent:component:HT-233", "component", "HT-233"),
        entity("ent:variant:HT-233", "variant", "HT-233"),  # the mis-typed twin
        entity("var", "variant", "HQ-9/P"),
        triple("HT-233", "equips", "var"),  # a raw endpoint, not an entity id
    ]
    part = resolve(claims, cfg)
    assert part.entity_canonical.get("HT-233") is not None, "the endpoint stayed an untyped mention"
    assert "ent:component:HT-233" in _cluster_of(part, part.entity_canonical["HT-233"])


def test_the_refusal_stands_when_the_ontology_admits_both_readings() -> None:
    """`observed-at` ranges over variant AND component, so it cannot break that particular tie.

    Refusing is the designed behaviour — the mention stays a tier-3 mention rather than acquiring an
    invented type. The narrowing rail must never turn "we don't know" into a coin flip.
    """
    cfg = mk_config(ontology=AREA_ONTOLOGY, relational_support_k=2)
    claims = [
        entity("ent:component:Widget", "component", "Widget"),
        entity("ent:variant:Widget", "variant", "Widget"),
        entity("site", "basing_site", "Sargodha"),
        triple("Widget", "observed-at", "site"),  # from: [variant, component] — both still admissible
    ]
    part = resolve(claims, cfg)
    assert "Widget" not in part.entity_canonical


def test_the_narrowing_rail_never_mints_a_new_designator() -> None:
    """Attach-only: the tie-break may adopt an existing entity, never create a fresh short name.

    Minting `ent:component:HQ-9/P TEL` handed the containment bootstrap a new short hook, which promptly
    read "HQ-9/P TEL canister" as the same part described more fully and fused a canister into a chassis.
    Over-merge is the expensive error, so the rail resolves onto something that already exists or not at all.
    """
    cfg = mk_config(ontology=AREA_ONTOLOGY, relational_support_k=2)
    claims = [
        # "Gizmo" is typed two ways, but neither declaration is under the surviving type's exact form
        entity("ent:component:Gizmo mount", "component", "Gizmo mount"),
        entity("ent:variant:Gizmo", "variant", "Gizmo"),
        entity("var", "variant", "HQ-9/P"),
        triple("Gizmo", "equips", "var"),
    ]
    part = resolve(claims, cfg)
    assert "ent:component:Gizmo" not in part.endpoint_node_types
    assert not any(k.startswith("ent:component:Gizmo") for k in part.endpoint_node_types)


# ── C. two distinct bills of lading can never merge ────────────────────────────────────────────

def test_distinct_bill_of_lading_numbers_can_never_merge() -> None:
    """The sharpest unguarded pair in the corpus: three separate bills in one customs manifest.

    They are the same type, the same namespace, share a consignee and have no `distinct-from` between
    them, so every existing rail passed them straight through to a shared-neighbourhood score. Merging
    any two collapses two import events into one and silently corrupts the supply-chain count.
    """
    cfg = mk_config(ontology=AREA_ONTOLOGY, relational_support_k=2)
    bols = ["KPQA-HC-2020-118834", "KPQA-HC-2020-118835", "KPQA-HC-2020-119011"]
    claims = [entity(b, "contract_import_event", b) for b in bols]
    # give them every merge signal short of an identical name: one shared consignee each
    claims += [entity("unit", "unit", "PAAD")] + [triple(b, "imported-by", "unit") for b in bols]
    # ...and a source that flatly asserts they are the same thing
    claims += [triple(bols[0], "same-as", bols[1])]
    part = resolve(claims, cfg)

    merged = {frozenset(p) for p in part.same_as}
    for i, a in enumerate(bols):
        for b in bols[i + 1 :]:
            assert frozenset({a, b}) not in merged, f"{a} merged with {b}"
            assert _cluster_of(part, a) == {a}
            assert frozenset({a, b}) not in _candidate_pairs(part), "a hard conflict is not an open question"
            assert frozenset({a, b}) in _veto_pairs(part), "the veto must stay DRAWN, not be invisible"


def test_a_contract_with_no_stated_reference_is_not_vetoed() -> None:
    """Absence is not disagreement — the same doctrine `has_hard_conflict` already applies to attrs."""
    cfg = mk_config(ontology=AREA_ONTOLOGY, relational_support_k=2)
    claims = [
        entity("prose_a", "contract_import_event", "HQ-9(P) SAM system"),
        entity("prose_b", "contract_import_event", "HQ-9(P) SAM system procurement"),
        entity("bol", "contract_import_event", "KPQA-HC-2020-118834"),
    ]
    part = resolve(claims, cfg)
    assert frozenset({"prose_a", "prose_b"}) not in _veto_pairs(part)
    assert frozenset({"prose_a", "bol"}) not in _veto_pairs(part)


# ── F. a Jaccard over a one-element neighbourhood is not a perfect match ────────────────────────

_HUB_CLAIMS = [
    entity("site_a", "basing_site", "Sargodha"),
    entity("site_b", "basing_site", "Quetta"),
    entity("unit", "unit", "PAAD"),
    triple("unit", "based-at", "site_a"),
    triple("unit", "based-at", "site_b"),
]


def _hub_breakdown(**cfg_kwargs) -> dict[str, float]:
    """``merge_score`` for two sites whose ONLY edge is a `based-at` from the same unit."""
    cfg = ResolveConfig.from_bundle(mk_config(ontology=AREA_ONTOLOGY, **cfg_kwargs))
    graph = build_entity_graph(_HUB_CLAIMS)
    return merge_score(graph.entities["site_a"], graph.entities["site_b"], graph, lambda x: x, cfg)


def test_one_shared_neighbour_does_not_saturate_the_relational_term() -> None:
    """A one-element neighbourhood scored a perfect relational 1.0 — the strongest term in merge_score.

    That single artefact was what lifted eighteen unrelated site pairs to exactly hitl_low and filled the
    analyst's merge queue. Pinned on the *breakdown* rather than the band, so the invariant is about the
    signal and not about how similar two particular place names happen to look.
    """
    discounted = _hub_breakdown(relational_support_k=2)
    raw = _hub_breakdown()
    assert raw["relational"] == 1.0, "the pre-fix behaviour must be preserved when the knob is unset"
    assert discounted["relational"] == raw["relational"] / 2
    assert discounted["total"] < raw["total"]


def test_one_shared_neighbour_does_not_reach_the_analyst_on_its_own() -> None:
    """...and the band moves with it: shared-hub-only is no longer an open identity question."""
    part = resolve(_HUB_CLAIMS, mk_config(ontology=AREA_ONTOLOGY, relational_support_k=2))
    assert frozenset({"site_a", "site_b"}) not in _candidate_pairs(part)
    assert frozenset({"site_a", "site_b"}) in _candidate_pairs(resolve(_HUB_CLAIMS, mk_config()))


def test_two_shared_neighbours_still_reach_the_analyst() -> None:
    """The other half of the invariant: the discount must not silence genuine relational evidence.

    ``relational_support_k`` states where full strength begins; at or above it the collective-ER signal
    is untouched, so a pair with real shared neighbourhood still reaches the queue exactly as before.
    """
    cfg = mk_config(ontology=AREA_ONTOLOGY, relational_support_k=2)
    claims = [
        entity("site_a", "basing_site", "Sargodha"),
        entity("site_b", "basing_site", "Kahuta area"),
        entity("unit_x", "unit", "PAAD"),
        entity("unit_y", "unit", "PAF"),
        triple("unit_x", "based-at", "site_a"),
        triple("unit_x", "based-at", "site_b"),
        triple("unit_y", "based-at", "site_a"),
        triple("unit_y", "based-at", "site_b"),
    ]
    part = resolve(claims, cfg)
    assert frozenset({"site_a", "site_b"}) in _candidate_pairs(part)


def test_the_support_discount_only_ever_lowers_a_score() -> None:
    """It can never create an auto-merge — the one property that makes it safe to ship (gate G2/G6)."""
    discounted = _hub_breakdown(relational_support_k=2)
    raw = _hub_breakdown()
    for signal in ("attribute", "temporal_consistency", "source_asserted"):
        assert discounted[signal] == raw[signal], f"{signal} must be untouched"
    assert discounted["relational"] <= raw["relational"]
