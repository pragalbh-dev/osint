"""G17 (RK-LAYER extension) — **no code path under ``rebuild()`` writes evidence.**

RK-ATOMS asserted the first half: no rebuild-reachable module *mints* an atom
(``test_g17_atoms_minted_at_ingest``). This file asserts the half RK-LAYER owns: none of them
**appends to the evidence log** either. The two together are the bi-level rule stated as a test — the
evidence layer is written once, at ingest; the knowledge layer is *derived*, recomputed from scratch, and
writes nothing back.

**Why this clause exists now, specifically.** The unit→site basing attribution used to be produced by an
offline pass that minted a ``kind="inference"`` ``ClaimRecord`` and appended it. That is derived output
frozen into an append-only record: the conclusion outlives its premises across a re-record, provenance
depends on when the pass last ran, and the "evidence layer" stops being a record of what sources said.
RK-LAYER deletes that pass and materializes the edge inside ``rebuild()`` instead, citing its two premise
claim-atoms. The danger in doing so is obvious — the derivation now runs *inside* the pure fold, one line
away from being able to persist itself — so the constraint gets a gate rather than a comment.

**Two independent statements, and both non-vacuity halves the plan asks for:**

1. **A static, input-independent scan** of the rebuild import closure for ``store.append`` /
   ``append_many`` calls. Static because a fixture-driven check passes whenever the fixture happens not to
   reach the offending branch, and this branch is *conditional on a flag*.
2. **A behavioural check with a non-vacuous fixture**: an ``observed-at`` + ``inducted-into`` premise pair,
   with layer routing **on**, so the derived-basing branch actually executes — verified by asserting the
   derived edge appears — while a store that **raises on any write** stands in for the evidence log. If any
   code under ``rebuild()`` tried to append, the rebuild would fail loudly instead of passing quietly.

The fixture is abstract (a hand-built ontology + two claims), so it is immune to the re-key's data churn.
"""

from __future__ import annotations

import ast

import pytest

from chanakya.ontology import LayerRouting
from chanakya.schemas import (
    ClaimRecord,
    ConfigBundle,
    CredibilityConfig,
    OntologyConfig,
)
from chanakya.schemas.claim import DocRef, EntityDescriptor, Triple
from chanakya.schemas.values import ExactDate
from chanakya.view.pipeline import rebuild
from tests.gates.test_g17_atoms_minted_at_ingest import rebuild_reachable_modules

#: ``append_many`` is the **discriminating** name: it is the evidence log's protocol method
#: (``ingest.seed.SupportsAppendMany``) and ``list`` has no such method, so any call to it is a write to a
#: log. ``append`` is not discriminating at all — it is overwhelmingly ``list.append``, which the derived
#: layer uses constantly and legitimately — so for that name the **receiver** is what tells an evidence
#: write from a list push. This vocabulary is the store-shaped receivers the codebase actually uses; it is
#: stated here rather than inferred, and :func:`test_the_append_scanner_is_not_vacuous` pins both halves.
STORE_RECEIVERS = frozenset({"store", "evidence", "log", "evidence_log", "_store", "_log", "_evidence"})


def evidence_writes(source: str) -> list[tuple[int, str]]:
    """Every ``(lineno, expression)`` in ``source`` that writes to an evidence log.

    ``<anything>.append_many(...)`` always counts; ``<store-shaped receiver>.append(...)`` counts; a bare
    ``append(...)`` or ``some_list.append(...)`` does not.
    """
    hits: list[tuple[int, str]] = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        attr, value = node.func.attr, node.func.value
        receiver = (
            value.id if isinstance(value, ast.Name)
            else value.attr if isinstance(value, ast.Attribute)
            else None
        )
        if attr == "append_many":
            hits.append((node.lineno, f"{receiver or '?'}.append_many"))
        elif attr == "append" and receiver in STORE_RECEIVERS:
            hits.append((node.lineno, f"{receiver}.append"))
    return sorted(hits)


# ── 1. the static scan ───────────────────────────────────────────────────────────────────────────

def test_no_rebuild_reachable_module_appends_to_the_evidence_log() -> None:
    """Static and input-independent: an unexercised branch cannot hide an append."""
    reachable = rebuild_reachable_modules()
    assert "chanakya.view.pipeline" in reachable, "the closure must contain the module defining rebuild()"
    offenders = [
        f"{module}:{line} calls {expr}()"
        for module, path in sorted(reachable.items())
        for line, expr in evidence_writes(path.read_text())
    ]
    assert not offenders, (
        "rebuild() must never write to the evidence log — a derived conclusion frozen into the "
        "append-only record outlives its premises and makes provenance depend on when you last rebuilt "
        "(G17). Found: " + "; ".join(offenders)
    )


def test_the_append_scanner_is_not_vacuous() -> None:
    """The detector must fire on real evidence writes and stay quiet on list pushes."""
    violating = (
        "def derive(store, edges):\n"
        "    store.append(claim)\n"
        "    store.append_many([claim])\n"
        "    self._store.append(claim)\n"
    )
    assert evidence_writes(violating) == [
        (2, "store.append"), (3, "store.append_many"), (4, "_store.append")
    ]
    # …and the derived layer's own list pushes are NOT evidence writes (no false positive) — which is the
    # whole reason the receiver matters: `append` alone would flag a hundred honest lines.
    assert evidence_writes("edges.append(e)\nout.gaps.append(g)\nappend = 1\n") == []


def test_the_deleted_offline_basing_pass_is_gone() -> None:
    """The pass is **deleted, not relocated** — so there is no second home for the old behaviour.

    Stated as a test because "moved it into the view" and "deleted it and derived the edge instead" look
    identical in a diff summary and are architecturally opposite: the first leaves a minting, appending
    producer alive for someone to call again.
    """
    with pytest.raises(ModuleNotFoundError):
        __import__("chanakya.ingest.basing")


# ── 2. the behavioural check, on a fixture that actually reaches the branch ───────────────────────

class _RaisingStore:
    """An evidence log that replays but refuses to be written to — the behavioural half of the gate."""

    def __init__(self, claims: list[ClaimRecord]) -> None:
        self._claims = claims

    def replay(self) -> list[ClaimRecord]:
        return list(self._claims)

    def append(self, record: ClaimRecord) -> None:  # pragma: no cover - must never run
        raise AssertionError("rebuild() appended a claim to the evidence log (G17)")

    def append_many(self, records: list[ClaimRecord]) -> None:  # pragma: no cover - must never run
        raise AssertionError("rebuild() appended claims to the evidence log (G17)")


def _ontology() -> OntologyConfig:
    """A minimal layer-tagged ontology: equipment, a formation, a site, and the two premise lanes."""
    return OntologyConfig.model_validate(
        {
            "node_types": [
                {"name": "variant", "layer": "design", "attrs": [{"name": "family", "layer": "design"}]},
                {"name": "unit", "layer": "instance", "attrs": [{"name": "designator", "layer": "instance"}]},
                {
                    "name": "basing_site",
                    "layer": "design",
                    "attrs": [
                        {"name": "coordinates", "layer": "design"},
                        {"name": "site_type", "layer": "design"},
                    ],
                },
                {"name": "presence", "layer": "instance", "attrs": [{"name": "count", "layer": "instance"}]},
            ],
            "edge_types": [
                {
                    "name": "observed-at",
                    "from": "variant",
                    "to": "basing_site",
                    "extractor": True,
                    "freshness_class": "perishable",
                    "materializes": {"end": "from", "node_type": "presence", "link": "instance-of"},
                },
                {
                    "name": "inducted-into",
                    "from": "variant",
                    "to": "unit",
                    "extractor": True,
                    "freshness_class": "semi-durable",
                },
                {
                    "name": "based-at",
                    "from": "unit",
                    "to": "basing_site",
                    "extractor": True,
                    "freshness_class": "perishable",
                    "instance_key": ["from"],
                    "instance_key_tag": "site_type",
                },
                {"name": "instance-of", "from": "presence", "to": "variant", "freshness_class": "durable"},
            ],
            "layer_routing": {
                "enabled": True,
                "presence_type": "presence",
                "design_link_edge": "instance-of",
                "provisional_prefix": "presence",
                "count_attrs": ["count"],
                "site_type_vocabulary": ["garrison", "airfield"],
                "absent_bucket": "unknown",
                "superseded_derived_layers": ["unit-attribution"],
            },
        }
    )


def _config() -> ConfigBundle:
    """Config with the derivation configured — otherwise the branch is dormant and the gate is vacuous."""
    return ConfigBundle(
        ontology=_ontology(),
        credibility=CredibilityConfig(
            thresholds={"confirmed": 0.8, "probable": 0.5},
            half_life_defaults={"perishable": 540, "semi-durable": 540, "durable": None},
            basing_proposer={
                "occupancy_edge_types": ["observed-at"],
                "formation_edge_types": ["inducted-into"],
                "equipment_hop_edges": [],
                "derived_edge": "based-at",
                "require_located_site": False,
                "max_units_per_site": 1,
                "occupied_tokens": ["occupied"],
            },
        ),
    )


def _entity(claim_id: str, etype: str, name: str, **attrs: object) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        source_id="s1",
        doc_ref=[DocRef(file="doc1.txt", line=1)],
        kind="observation",
        polarity="positive",
        asserts="entity",
        payload=EntityDescriptor(form="entity", entity_type=etype, name=name, attrs=dict(attrs)),
        report_time=ExactDate(iso_date="2025-01-01"),
    )


def _triple(claim_id: str, subject: str, predicate: str, obj: str, when: str) -> ClaimRecord:
    return ClaimRecord(
        claim_id=claim_id,
        source_id="s1",
        doc_ref=[DocRef(file="doc1.txt", line=1)],
        kind="observation",
        polarity="positive",
        asserts="relationship",
        payload=Triple(subject=subject, predicate=predicate, object=obj),
        event_time=ExactDate(iso_date=when),
        report_time=ExactDate(iso_date=when),
    )


def _premise_pair() -> list[ClaimRecord]:
    """The **non-vacuous** fixture: an ``observed-at`` + an ``inducted-into`` over the same equipment.

    That pair is the whole trigger for the derived-basing branch, and the plan is explicit that a fixture
    without it makes this gate pass vacuously. :func:`test_the_fixture_reaches_the_derived_basing_branch`
    proves the branch really ran, so the no-append assertion below is about executed code.
    """
    return [
        _entity("c-var", "variant", "HQ-X"),
        _entity("c-unit", "unit", "1st Bn", designator="1st Bn"),
        _entity("c-site", "basing_site", "Site A", site_type="garrison"),
        _triple("c-obs", "ent:variant:HQ-X", "observed-at", "ent:basing_site:Site A", "2025-03-01"),
        _triple("c-ind", "ent:variant:HQ-X", "inducted-into", "ent:unit:1st Bn", "2025-02-01"),
    ]


def test_the_fixture_reaches_the_derived_basing_branch() -> None:
    """Non-vacuity for the behavioural half: the derivation must actually have run on this fixture."""
    view = rebuild(_premise_pair(), [], _config())
    derived = [e for e in view.edges if e.type == "based-at"]
    assert derived, (
        "the fixture must exercise the derived-basing branch, or the no-append assertion is vacuous — "
        f"got edge types {sorted({e.type for e in view.edges})}"
    )
    edge = derived[0]
    assert (edge.source, edge.target) == ("ent:unit:1st Bn", "ent:basing_site:Site A")
    # It CITES ITS TWO PREMISE CLAIM-ATOMS rather than a claim of its own — the point of the change: the
    # analyst clicks the attribution and lands on the sighting and the induction.
    assert edge.claim_ids == ["c-ind", "c-obs"]
    assert edge.attrs["premises"] == ["c-obs", "c-ind"]
    # …and no claim was invented to carry it: the log still holds exactly the five fixture claims.
    assert {e.attrs.get("derived_layer") for e in derived} == {"unit-attribution"}


def test_rebuild_never_appends_while_deriving_a_basing() -> None:
    """The same fixture, through a store that raises on any write."""
    view = rebuild(_RaisingStore(_premise_pair()), [], _config())
    assert [e for e in view.edges if e.type == "based-at"], "the derivation must still have run"


def test_the_derived_edge_cannot_reach_confirmed() -> None:
    """A derived attribution is the *weaker* of the formation's two provenance paths (D-13.13).

    It cites its premises directly, so without an explicit cap two independent premise sources would pool
    into two independent looks and the inference would read as better corroborated than the sighting under
    it. The minted form got this ceiling for free by sharing an independence group with its premises.
    """
    view = rebuild(_premise_pair(), [], _config())
    derived = [e for e in view.edges if e.type == "based-at"]
    assert derived
    for edge in derived:
        assert edge.status != "confirmed", (
            "a derived basing must never reach confirmed however well its premises corroborate"
        )
        assert edge.confidence is not None
        assert "derived-inference" in edge.confidence.integrity_flags


def test_the_derivation_is_flag_gated() -> None:
    """With layer routing off, nothing is derived — the flag-off safety property, stated locally."""
    ontology = _ontology().model_dump(by_alias=True)
    ontology["layer_routing"]["enabled"] = False
    config = _config().model_copy(update={"ontology": OntologyConfig.model_validate(ontology)})
    view = rebuild(_premise_pair(), [], config)
    assert not [e for e in view.edges if e.type == "based-at"]
    assert not [n for n in view.nodes if n.type == "presence"]


def test_the_derivation_module_constructs_no_claim_record() -> None:
    """Belt-and-braces on the *shape* of the fix: the derivation builds edges, never claims.

    A ``ClaimRecord`` constructed inside the rebuild would be an evidence-layer object born in the derived
    layer — the architectural error even if nobody appended it, and one the mint scan cannot see because a
    hand-written id string calls no mint function.
    """
    import chanakya.view.basing as module

    src = ast.parse(open(module.__file__).read())
    constructed = [
        node.lineno
        for node in ast.walk(src)
        if isinstance(node, ast.Call)
        and (
            (isinstance(node.func, ast.Name) and node.func.id == "ClaimRecord")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "ClaimRecord")
        )
    ]
    assert not constructed, (
        f"view/basing.py must derive EDGES, not construct ClaimRecords (G17) — lines {constructed}"
    )


def test_layer_routing_is_off_by_default_in_the_shipped_ontology() -> None:
    """The flag ships **off**: the stage's safety property is a property of the config, not of a habit."""
    from chanakya.config.store import ConfigStore
    from chanakya.settings import config_dir

    routing = LayerRouting.from_ontology(ConfigStore.seed_from(config_dir()).snapshot().ontology)
    assert routing.enabled is False
