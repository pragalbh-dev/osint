"""Basing proposer — the derived unit-attribution layer (``ingest/basing.py``, EVAL RCA D-P4.1/2/3).

The scene is the relocation beat in miniature: one variant observed at two sites on two dates
(``observed-at``, the observed layer) plus one ``inducted-into`` formation reference. The proposer must
turn that into two ``<unit, based-at, site>`` inference claims with the SAME subject — which is what makes
the pair one edge instance under the ontology's functional ``instance_key: [from]``, and therefore what
makes a supersede reachable at all.

Load-bearing invariants asserted here:

* **two layers, never fused** — the derived claim is its own claim, ``kind="inference"``, with the
  observed occupancy as a premise; it sets no status and no confidence (SCORE prices it);
* **traceability (G4)** — ``premises`` are both grounding claim ids and ``doc_ref`` spans both documents;
* **inherited valid time** — the derived fact carries the observation's ``event_time``, unflattened, so a
  2021 basing can age out and a 2025 one can supersede it;
* **one subject across sites** — the same equipment attributes to the same formation everywhere;
* **deterministic, keyless, idempotent, budgeted** — no model call, byte-identical re-runs, a second pass
  proposes nothing, and every non-firing occupancy edge is logged with a reason.
"""

from __future__ import annotations

from typing import Any

from chanakya.ingest import basing
from chanakya.schemas.claim import ClaimRecord, DocRef, Extraction, Triple
from chanakya.schemas.config_models import ConfigBundle, CredibilityConfig
from chanakya.schemas.values import ExactDate, LabelDate, Location
from chanakya.schemas.view import EdgeView, GraphView, NodeView

_UNIT = "unit_hq9b"
_VARIANT = "var_hq9be"
_RAWALPINDI = "site_rawalpindi"
_RAHWALI = "site_rahwali"


# ── fixtures ─────────────────────────────────────────────────────────────────────────────────────

def _occupancy(cid: str, source: str, site: str, when: Any, *,
               attributes: dict[str, Any] | None = None) -> ClaimRecord:
    """An OBSERVED-occupancy claim: this equipment was seen at this site on this date."""
    return ClaimRecord(
        claim_id=cid, source_id=source,
        doc_ref=DocRef(file=f"corpus/scenarios/hq9p_primary/docs/{source}.txt", line=7),
        kind="observation", polarity="positive", asserts="relationship",
        payload=Triple(subject=_VARIANT, predicate="observed-at", object=site),
        event_time=when, extraction=Extraction(method="llm", version="scripted"),
        attributes=attributes,
    )


def _formation(cid: str = "b-d19-induct") -> ClaimRecord:
    """The formation reference: this equipment serves with this named unit."""
    return ClaimRecord(
        claim_id=cid, source_id="d19_rahwali_confirm",
        doc_ref=DocRef(file="corpus/scenarios/hq9p_primary/docs/d19_rahwali_confirm.txt", line=21),
        kind="observation", polarity="positive", asserts="relationship",
        payload=Triple(subject=_VARIANT, predicate="inducted-into", object=_UNIT),
        extraction=Extraction(method="llm", version="scripted"),
    )


def _config(*, configured: bool = True, budget: int | None = 20,
            max_units: int = 1) -> ConfigBundle:
    if not configured:
        return ConfigBundle(credibility=CredibilityConfig())
    proposer: dict[str, Any] = {
        "occupancy_edge_types": ["observed-at"],
        "formation_edge_types": ["inducted-into"],
        "equipment_hop_edges": ["equips"],
        "derived_edge": "based-at",
        "max_units_per_site": max_units,
    }
    if budget is not None:
        proposer["max_claims_per_pass"] = budget
    return ConfigBundle(credibility=CredibilityConfig(basing_proposer=proposer))


_D17 = ExactDate(iso_date="2021-10-09", raw="09 OCT 2021")
_D18 = LabelDate(granularity="year", year=2025, raw="2025")


def _located(name: str) -> Location:
    """A site you can point to — the admission test the derived basing layer applies (md/13)."""
    return Location(raw=name, wgs84_lat=32.2, wgs84_lon=74.1)


def _scene(*, with_formation: bool = True, dated: bool = True, derived_already: bool = False,
           decoy: bool = False, vacated: bool = False,
           located: bool = True) -> tuple[GraphView, dict[str, ClaimRecord]]:
    """The relocation shape: one variant observed at Rawalpindi (2021) and Rahwali (2025)."""
    old = _occupancy("a-d17-occ", "d17_rawalpindi_2021", _RAWALPINDI, _D17 if dated else None,
                     attributes={"occupancy_state": "empty-pads"} if vacated else None)
    new = _occupancy("a-d18-occ", "d18_rahwali_pass1", _RAHWALI, _D18 if dated else None,
                     attributes={"decoy_risk_flag": True} if decoy else None)
    claims: dict[str, ClaimRecord] = {c.claim_id: c for c in (old, new)}
    formation_cids: list[str] = []
    if with_formation:
        f = _formation()
        claims[f.claim_id] = f
        formation_cids.append(f.claim_id)
    if derived_already:
        prior = ClaimRecord(
            claim_id="d-prior-basing", source_id=old.source_id, doc_ref=old.doc_ref,
            kind="inference", polarity="positive", asserts="relationship",
            payload=Triple(subject=_UNIT, predicate="based-at", object=_RAWALPINDI),
            premises=[old.claim_id, "b-d19-induct"],
            extraction=Extraction(method="llm", version="scripted"),
        )
        claims[prior.claim_id] = prior
    view = GraphView(
        nodes=[
            NodeView(id=_RAWALPINDI, type="basing_site", name="PAF Base Nur Khan",
                     location=_located("Nur Khan") if located else None),
            NodeView(id=_RAHWALI, type="basing_site", name="Rahwali airfield",
                     location=_located("Rahwali") if located else None),
            NodeView(id=_VARIANT, type="variant", name="HQ-9BE"),
            NodeView(id=_UNIT, type="unit", name="Army Air Defence Command"),
        ],
        edges=[
            EdgeView(id="e_old", type="observed-at", source=_VARIANT, target=_RAWALPINDI,
                     claim_ids=[old.claim_id]),
            EdgeView(id="e_new", type="observed-at", source=_VARIANT, target=_RAHWALI,
                     claim_ids=[new.claim_id]),
            EdgeView(id="e_ind", type="inducted-into", source=_VARIANT, target=_UNIT,
                     claim_ids=formation_cids),
        ],
    )
    return view, claims


def _run(**kw: Any) -> basing.BasingRun:
    view, claims = _scene(**{k: v for k, v in kw.items() if k in
                             {"with_formation", "dated", "derived_already", "decoy", "vacated",
                              "located"}})
    cfg = _config(**{k: v for k, v in kw.items() if k in {"configured", "budget", "max_units"}})
    return basing.propose_basing(view, claims, cfg)


def _by_site(run: basing.BasingRun) -> dict[str, ClaimRecord]:
    out: dict[str, ClaimRecord] = {}
    for c in run.claims:
        assert isinstance(c.payload, Triple)
        out[c.payload.object] = c
    return out


# ── the derivation ───────────────────────────────────────────────────────────────────────────────

def test_derives_unit_to_site_basing_from_occupancy_plus_formation() -> None:
    run = _run()
    derived = _by_site(run)
    assert set(derived) == {_RAWALPINDI, _RAHWALI}
    for site, claim in derived.items():
        assert isinstance(claim.payload, Triple)
        assert claim.payload.subject == _UNIT       # the formation, not the equipment
        assert claim.payload.predicate == "based-at"
        assert claim.payload.object == site
        assert claim.kind == "inference"


def test_both_sites_attribute_to_one_subject_so_the_pair_is_one_edge_instance() -> None:
    """The property the whole relocation beat rests on: two targets, one subject → one instance."""
    subjects = {c.payload.subject for c in _run().claims if isinstance(c.payload, Triple)}
    assert subjects == {_UNIT}


def test_premises_and_doc_ref_span_both_grounding_documents() -> None:
    """G4 — one click reaches the sighting AND the formation reference, not a bare assertion."""
    claim = _by_site(_run())[_RAHWALI]
    assert claim.premises == ["a-d18-occ", "b-d19-induct"]
    files = {r.file for r in claim.doc_refs()}
    assert files == {
        "corpus/scenarios/hq9p_primary/docs/d18_rahwali_pass1.txt",
        "corpus/scenarios/hq9p_primary/docs/d19_rahwali_confirm.txt",
    }


def test_event_time_is_inherited_from_the_grounding_observation() -> None:
    """The derived fact ages on the SIGHTING's date — this is what lets 2021 go stale and 2025 supersede."""
    derived = _by_site(_run())
    assert derived[_RAWALPINDI].event_time == _D17
    assert derived[_RAHWALI].event_time == _D18


def test_inherited_time_keeps_the_premise_granularity_unflattened() -> None:
    """A vague '2025' stays a year label — a derived fact must never read as better-dated than its premise."""
    when = _by_site(_run())[_RAHWALI].event_time
    assert isinstance(when, LabelDate) and when.granularity == "year"


def test_undated_observation_yields_an_undated_derivation_not_a_guessed_date() -> None:
    run = _run(dated=False)
    assert run.claims and all(c.event_time is None for c in run.claims)


def test_derived_claim_sets_no_status_or_confidence() -> None:
    """Raise-only: the proposer proposes, SCORE prices. A raw claim carries no status field at all."""
    claim = _by_site(_run())[_RAHWALI]
    assert not hasattr(claim, "status")
    assert not hasattr(claim, "confidence")
    assert claim.attributes is not None
    assert claim.attributes["derived_layer"] == "unit-attribution"


def test_decoy_flag_on_the_sighting_rides_the_attribution() -> None:
    """An attribution can never be firmer than the sighting it rests on (the d11/d20 traps)."""
    derived = _by_site(_run(decoy=True))
    assert derived[_RAHWALI].attributes is not None
    assert derived[_RAHWALI].attributes["decoy_risk_flag"] is True
    assert "decoy_risk_flag" not in (derived[_RAWALPINDI].attributes or {})


# ── the negatives: nothing is invented ───────────────────────────────────────────────────────────

def test_an_explicitly_empty_site_never_grounds_a_positive_basing_claim() -> None:
    """An absence is not a presence. The corpus's own follow-up read of the old Rawalpindi position says
    the launchers are gone — deriving a basing fact from it would put the unit at the one place the
    source says it left, and (being the newest reading) would invert the whole relocation."""
    run = _run(vacated=True)
    assert [c.payload.object for c in run.claims if isinstance(c.payload, Triple)] == [_RAHWALI]
    assert ("observation-states-vacancy", _RAWALPINDI) in {(s.reason, s.site_id) for s in run.skipped}


def test_a_region_is_not_a_base() -> None:
    """A province or an "air defence sector" is an area of operation, not a site a unit can be based at —
    and without this gate one formation acquires a derived "base" for every region its kit is discussed in."""
    run = _run(located=False)
    assert run.claims == []
    assert {s.reason for s in run.skipped} == {"site-not-locatable"}


def test_no_formation_reference_derives_nothing_and_says_why() -> None:
    run = _run(with_formation=False)
    assert run.claims == []
    assert {s.reason for s in run.skipped} == {"no-formation-reference"}
    assert {s.site_id for s in run.skipped} == {_RAWALPINDI, _RAHWALI}


def test_unconfigured_proposer_is_dormant() -> None:
    run = _run(configured=False)
    assert run.claims == [] and run.skipped == []


def test_already_derived_observation_is_skipped_so_reruns_converge() -> None:
    run = _run(derived_already=True)
    assert [c.payload.object for c in run.claims if isinstance(c.payload, Triple)] == [_RAHWALI]
    assert ("already-derived", _RAWALPINDI) in {(s.reason, s.site_id) for s in run.skipped}


def test_budget_caps_the_pass_and_logs_the_overflow() -> None:
    run = _run(budget=1)
    assert len(run.claims) == 1
    assert any(s.reason == "over-budget" for s in run.skipped)


def test_deterministic_across_runs() -> None:
    a, b = _run(), _run()
    assert [c.model_dump(mode="json") for c in a.claims] == [c.model_dump(mode="json") for c in b.claims]


def test_enrich_appends_and_rebuilds_without_a_model_call() -> None:
    """Keyless by construction: the derivation is a graph step, so no extraction client is involved."""
    from chanakya.store.log import EvidenceLog

    view, claims = _scene()
    store = EvidenceLog()
    store.append_many(list(claims.values()))
    rebuilds: list[int] = []

    def _rebuild(_store: Any, _decisions: Any, _config: Any) -> GraphView:
        rebuilds.append(1)
        return view

    run = basing.enrich(store, _config(), rebuild_fn=_rebuild)
    assert len(run.claims) == 2
    assert len(rebuilds) == 2  # rebuild → propose → append → rebuild
    appended = [c for c in store.replay() if c.kind == "inference"]
    assert len(appended) == 2
