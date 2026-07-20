"""Hand-authored agent view fixture — the ASK session's *test input* (sessions/ASK.md → Owned paths).

SCORE normally computes status / confidence / freshness / materiality inside ``rebuild()``; that is out
of scope for ASK, so this module fakes those as **already-computed test input** and hands the agent a
``(view, claims, config)`` triple shaped exactly like the runtime one. It carries, deliberately:

* **the hero subgraph** (C/02 / DATA-C answer_key names) — 5 nodes, 4 edges, traced from the deployed
  Karachi battery back to the component maker:
  ``site_karachi ←based-at– unit_paad ←inducted-into– var_hq9p ←equips– comp_ht233 ←supplies-component– mfr_casic``
  (edges stored **origin-ward**: ``unit_paad —based-at→ site_karachi`` etc.; the agent traverses either way).
  The Mfr→Component hero edge is ``supplies-component`` (Phase-1 tightened ``manufactures`` to
  Mfr→Variant); ``var_hq9p`` is deliberately **named ``HQ-9P``** while the query anchor is ``HQ-9/P`` so
  the punctuation-squashed near-miss resolution has a real regression to bite on (spine/09 AS-6);
* **HT-233 as a CANDIDATE chokepoint** — ``substitutability_state = UNKNOWN`` → it must land in
  ``query_graph``'s ``indeterminate`` partition, **never** a confirmed sole-source (the disqualifying line);
* **a planted gap** — the sole-source question for HT-233 is unmet → a ``KnownGap`` with ``missing_slots`` +
  ``next_coverage_due`` (the honest-refusal path);
* **confirmed vs probable vs stale** statuses and a **``distinct-from``** sibling (HQ-9/P vs HQ-9BE) so
  ``find_entity`` disambiguation and the freshness/observed-vs-inferred flexes have something to bite on.

Everything reads like real data (readable claim IDs, real-shaped sources/dates) but is synthetic.
"""

from __future__ import annotations

from chanakya.schemas import (
    ClaimRecord,
    ConfidenceBreakdown,
    ConfigBundle,
    CredibilityConfig,
    DocRef,
    EdgeView,
    EntityDescriptor,
    EvidenceTemplate,
    ExactDate,
    Freshness,
    GraphView,
    IndependenceGroup,
    KnownGap,
    Location,
    MaterialityAttrs,
    NodeView,
    OntologyConfig,
    ResolutionConfig,
    SourceRegistryEntry,
    SourcesConfig,
    SubjectLens,
    SubjectsConfig,
    TemplatesConfig,
    Triple,
    TypeDef,
)

# ── claims (evidence log bodies) ──────────────────────────────────────────────────────────────
# The view references these by ``claim_id``; ``get_evidence`` + the observed-vs-inferred tag read the
# bodies here (kind / doc_ref / source / dates). Inference claims carry ``premises`` (validator-required).


def _triple(subj: str, pred: str, obj: str) -> Triple:
    return Triple(subject=subj, predicate=pred, object=obj)


def hero_claims() -> dict[str, ClaimRecord]:
    """``claim_id → ClaimRecord`` for the hero subgraph + the flex cases."""
    records = [
        # based-at (imagery observation — confirmed, fresh)
        ClaimRecord(
            claim_id="d17-img1",
            source_id="src-imagery-2024",
            doc_ref=DocRef(file="d17_planet_karachi_2024.txt", region="Malir AD compound"),
            kind="observation",
            asserts="relationship",
            payload=_triple("unit_paad", "based-at", "site_karachi"),
            event_time=ExactDate(iso_date="2024-03-12", raw="12 Mar 2024"),
            report_time=ExactDate(iso_date="2024-03-15"),
        ),
        # inducted-into (single official statement — probable, tender-implied)
        ClaimRecord(
            claim_id="d02-l3",
            source_id="src-ispr-2021",
            doc_ref=DocRef(file="d02_ispr_2021_10_14.txt", span=(210, 318)),
            kind="observation",
            asserts="relationship",
            payload=_triple("var_hq9p", "inducted-into", "unit_paad"),
            event_time=ExactDate(iso_date="2021-10-14", raw="14 October 2021"),
            report_time=ExactDate(iso_date="2021-10-14"),
        ),
        # specs premise for the equips inference (Jane's observation)
        ClaimRecord(
            claim_id="d09-l5",
            source_id="src-janes-2023",
            doc_ref=DocRef(file="d09_janes_hq9_2023.txt", span=(1440, 1602)),
            kind="observation",
            asserts="entity",
            payload=EntityDescriptor(
                entity_type="component",
                name="HT-233",
                attrs={"functional_role": "engagement/fire-control", "radar_band": "C-band"},
            ),
            report_time=ExactDate(iso_date="2023-06-01"),
        ),
        # equips (inference from architecture — probable)
        ClaimRecord(
            claim_id="d09-l7",
            source_id="src-janes-2023",
            doc_ref=DocRef(file="d09_janes_hq9_2023.txt", span=(1610, 1740)),
            kind="inference",
            asserts="relationship",
            payload=_triple("comp_ht233", "equips", "var_hq9p"),
            premises=["d09-l5"],
            report_time=ExactDate(iso_date="2023-06-01"),
        ),
        # distinct-from sibling note (HQ-9BE is the export variant, distinct from HQ-9/P)
        ClaimRecord(
            claim_id="d09-l9",
            source_id="src-janes-2023",
            doc_ref=DocRef(file="d09_janes_hq9_2023.txt", span=(1990, 2110)),
            kind="observation",
            asserts="relationship",
            payload=_triple("var_hq9p", "distinct-from", "var_hq9be"),
            report_time=ExactDate(iso_date="2023-06-01"),
        ),
        # attribution premise (SIPRI aggregator observation)
        ClaimRecord(
            claim_id="d21-l1",
            source_id="src-sipri-2022",
            doc_ref=DocRef(file="d21_sipri_trades_2022.txt", row=44),
            kind="observation",
            asserts="entity",
            payload=EntityDescriptor(
                entity_type="manufacturer",
                name="CASIC",
                attrs={"role": "prime/system-house", "foreign_control": "UNKNOWN"},
            ),
            report_time=ExactDate(iso_date="2022-11-20"),
        ),
        # supplies-component (inference — probable; the sole-source question stays UNKNOWN → the planted
        # gap). Mfr→Component is `supplies-component`, NOT `manufactures` (Phase-1 D-A.1 tightened the
        # latter to Mfr→Variant) — the fixture mirrors the shipped ontology's re-laned reality.
        ClaimRecord(
            claim_id="d21-l2",
            source_id="src-sipri-2022",
            doc_ref=DocRef(file="d21_sipri_trades_2022.txt", row=45),
            kind="inference",
            asserts="relationship",
            payload=_triple("mfr_casic", "supplies-component", "comp_ht233"),
            premises=["d21-l1", "d09-l5"],
            report_time=ExactDate(iso_date="2022-11-20"),
        ),
        # stale basing (2019 imagery, coverage lapsed → stale)
        ClaimRecord(
            claim_id="d33-img2",
            source_id="src-imagery-2019",
            doc_ref=DocRef(file="d33_imagery_rahwali_2019.txt", region="north apron"),
            kind="observation",
            asserts="relationship",
            payload=_triple("unit_hq9b", "based-at", "site_rahwali"),
            event_time=ExactDate(iso_date="2019-05-01", raw="May 2019"),
            report_time=ExactDate(iso_date="2019-05-10"),
        ),
    ]
    return {c.claim_id: c for c in records}


# ── the knowledge view (as if rebuild() had run) ────────────────────────────────────────────────


def _group(claim_ids: list[str]) -> list[IndependenceGroup]:
    return [IndependenceGroup(group_id=f"grp:{claim_ids[0]}", claim_ids=list(claim_ids))]


def _conf(claim_ids: list[str], confidence: float, flags: list[str] | None = None) -> ConfidenceBreakdown:
    return ConfidenceBreakdown(
        per_claim_credibility={cid: round(confidence, 2) for cid in claim_ids},
        independence_groups=_group(claim_ids),
        integrity_flags=flags or [],
        assertion_confidence=confidence,
    )


def _fresh(last: str, half_life_days: float, decay: float) -> Freshness:
    return Freshness(
        last_support_time=last, half_life=f"{half_life_days:g}d", half_life_days=half_life_days, decay_factor=decay
    )


def hero_view() -> GraphView:
    """The rebuilt-looking view: nodes/edges with status + materiality + freshness set as test input."""
    nodes = [
        NodeView(
            id="site_karachi",
            type="basing_site",
            name="Karachi Army Air Defence Site (Malir)",
            attrs={"occupancy_state": "confirmed", "site_type": "prepared-battery"},
            location=Location(raw="Malir, Karachi", wgs84_lat=24.93, wgs84_lon=67.20, precision_class="site"),
            claim_ids=["d17-img1"],
            status="confirmed",
            confidence=_conf(["d17-img1"], 0.86),
            freshness=_fresh("2024-03-12", 365.0, 0.96),
            supporting_claims=_group(["d17-img1"]),
        ),
        NodeView(
            id="unit_paad",
            type="unit",
            name="Pakistan Army Air Defence — HQ-9/P Regiment",
            attrs={"echelon": "regiment", "service_branch": "Pakistan Army", "count_state": "fielded"},
            claim_ids=["d02-l3", "d17-img1"],
            status="confirmed",
            confidence=_conf(["d02-l3", "d17-img1"], 0.83),
            supporting_claims=[IndependenceGroup(group_id="grp:unit_paad", claim_ids=["d02-l3", "d17-img1"])],
        ),
        NodeView(
            id="var_hq9p",
            # NB: named "HQ-9P" (as an extractor would mint it), NOT "HQ-9/P" — so the query "HQ-9/P"
            # exercises the punctuation-squashed near-miss path, not a trivial exact-name hit (AS-6).
            type="variant",
            name="HQ-9P",
            attrs={"family": "HQ-9", "export_designator": "HQ-9/P", "aliases": ["HQ-9P"], "range_class": "long"},
            claim_ids=["d02-l3", "d09-l5"],
            status="confirmed",
            confidence=_conf(["d02-l3"], 0.81),
            supporting_claims=_group(["d02-l3"]),
        ),
        NodeView(
            id="var_hq9be",
            type="variant",
            name="HQ-9BE",
            attrs={"family": "HQ-9", "export_designator": "HQ-9BE", "range_class": "long"},
            claim_ids=["d09-l9"],
            status="probable",
            confidence=_conf(["d09-l9"], 0.62),
            supporting_claims=_group(["d09-l9"]),
        ),
        NodeView(
            id="comp_ht233",
            type="component",
            name="HT-233",
            attrs={
                "functional_role": "engagement/fire-control",
                "model_designation": "HT-233",
                "radar_band": "C-band",
            },
            claim_ids=["d09-l5", "d09-l7"],
            status="confirmed",
            confidence=_conf(["d09-l5", "d09-l7"], 0.80),
            supporting_claims=_group(["d09-l5"]),
            # THE load-bearing case: candidate (not confirmed) chokepoint; substitutability UNKNOWN.
            materiality=MaterialityAttrs(
                chokepoint_count=1,
                chokepoint_status="candidate",
                substitutability_state="UNKNOWN",
                contributing_refs=["d09-l7", "d21-l2"],
            ),
        ),
        NodeView(
            id="mfr_casic",
            type="manufacturer",
            name="CASIC",
            attrs={"role": "prime/system-house", "tier": "prime", "foreign_control": "UNKNOWN"},
            claim_ids=["d21-l1", "d21-l2"],
            status="probable",
            confidence=_conf(["d21-l2"], 0.58),
            supporting_claims=_group(["d21-l2"]),
        ),
        # stale-coverage flex
        NodeView(
            id="site_rahwali",
            type="basing_site",
            name="Rahwali (PAF) Air Defence Site",
            attrs={"occupancy_state": "confirmed-as-of", "site_type": "prepared-battery"},
            claim_ids=["d33-img2"],
            status="stale",
            confidence=_conf(["d33-img2"], 0.72),
            freshness=_fresh("2019-05-01", 365.0, 0.19),
            supporting_claims=_group(["d33-img2"]),
        ),
        NodeView(
            id="unit_hq9b",
            type="unit",
            name="PAF HQ-9B Squadron",
            attrs={"echelon": "squadron", "service_branch": "Pakistan Air Force"},
            claim_ids=["d33-img2"],
            status="probable",
            confidence=_conf(["d33-img2"], 0.6),
            supporting_claims=_group(["d33-img2"]),
        ),
    ]

    edges = [
        _edge("unit_paad", "based-at", "site_karachi", ["d17-img1"], "confirmed", 0.86,
              fresh=_fresh("2024-03-12", 365.0, 0.96)),
        _edge("var_hq9p", "inducted-into", "unit_paad", ["d02-l3"], "probable", 0.64),
        _edge("comp_ht233", "equips", "var_hq9p", ["d09-l7"], "probable", 0.66),
        _edge("mfr_casic", "supplies-component", "comp_ht233", ["d21-l2"], "probable", 0.58),
        _edge("var_hq9p", "distinct-from", "var_hq9be", ["d09-l9"], "confirmed", 0.9),
        _edge("unit_hq9b", "based-at", "site_rahwali", ["d33-img2"], "stale", 0.72,
              fresh=_fresh("2019-05-01", 365.0, 0.19)),
    ]

    known_gaps = [
        KnownGap(
            id="gap:comp_ht233:sole_source",
            related_ref="comp_ht233",
            what_missing="sole-source / alternate-supplier confirmation for HT-233",
            observability_ceiling="confirmable",
            next_coverage_due="2026-09-01",
            missing_slots=["customs_bill_of_lading", "sanctions_or_tender_naming_supplier"],
        ),
        KnownGap(
            id="gap:var_hq9p:interceptor_stockpile",
            related_ref="var_hq9p",
            what_missing="interceptor magazine depth / stockpile for the HQ-9/P holding",
            observability_ceiling="never-observable",
            next_coverage_due=None,
            missing_slots=["magazine_depth"],
        ),
    ]

    view = GraphView(nodes=nodes, edges=edges, known_gaps=known_gaps)
    view.meta = {
        "config_version": 1,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "known_gap_count": len(known_gaps),
        "subject_lens": "lens-hq9p-pk",
    }
    return view


def _edge(
    src: str,
    etype: str,
    tgt: str,
    claim_ids: list[str],
    status: str,
    confidence: float,
    fresh: Freshness | None = None,
) -> EdgeView:
    return EdgeView(
        id=f"e:{src}:{etype}:{tgt}",
        type=etype,
        source=src,
        target=tgt,
        edge_instance=f"{etype}:{src}",
        claim_ids=list(claim_ids),
        status=status,
        confidence=_conf(claim_ids, confidence),
        freshness=fresh,
        supporting_claims=_group(claim_ids),
    )


# ── config (minimal, real-shaped; decoupled from DATA-C's YAML) ─────────────────────────────────


def hero_config() -> ConfigBundle:
    """A minimal ConfigBundle: sources registry (for get_evidence), alias table (find_entity),
    the hero subject lens, a sufficiency template (check_sufficiency refusal rendering), and the edge
    ontology the tools read (canonical Mfr→Component lane + the traversable-lane whitelist)."""
    # Edge ontology mirror (subset): directional relations + the symmetric distinct-from resolution lane,
    # so EdgeLaneIndex.canonical_edge('manufacturer','component')='supplies-component' and
    # traversable_edges() excludes distinct-from (AS-2 / AS-4).
    ontology = OntologyConfig(
        edge_types=[
            TypeDef(name="based-at", from_type="unit", to_type="basing_site", extractor=True, freshness_class="perishable"),
            TypeDef(name="inducted-into", from_type="variant", to_type="unit", extractor=True, freshness_class="semi-durable"),
            TypeDef(name="equips", from_type="component", to_type="variant", extractor=True, freshness_class="durable"),
            TypeDef(name="supplies-component", from_type="manufacturer", to_type="component", extractor=True, freshness_class="durable"),
            TypeDef(name="manufactures", from_type="manufacturer", to_type="variant", extractor=True, freshness_class="durable"),
            TypeDef(name="distinct-from", symmetric=True, freshness_class="n/a"),
        ]
    )
    sources = SourcesConfig(
        sources=[
            SourceRegistryEntry(
                source_id="src-imagery-2024", source_type="satellite", reliability_grade="B",
                bias_vector="third-party", cadence="P30D", citation_url="https://example.org/planet/karachi-2024",
            ),
            SourceRegistryEntry(
                source_id="src-imagery-2019", source_type="satellite", reliability_grade="B",
                bias_vector="third-party", cadence="P30D", citation_url="https://example.org/imagery/rahwali-2019",
            ),
            SourceRegistryEntry(
                source_id="src-ispr-2021", source_type="official-statement", reliability_grade="C",
                bias_vector="operator-state", cadence="event-driven", citation_url="https://example.org/ispr/2021",
            ),
            SourceRegistryEntry(
                source_id="src-janes-2023", source_type="curated-register", reliability_grade="B",
                bias_vector="third-party", cadence="P365D", citation_url="https://example.org/janes/hq9",
            ),
            SourceRegistryEntry(
                source_id="src-sipri-2022", source_type="curated-register", reliability_grade="B",
                bias_vector="third-party", aggregator_of=["src-ispr-2021"], cadence="P365D",
                citation_url="https://example.org/sipri/trades",
            ),
            SourceRegistryEntry(
                source_id="src-customs-2026", source_type="commercial", reliability_grade="C",
                bias_vector="commercial", cadence="P90D", citation_url="https://example.org/customs",
            ),
        ]
    )
    resolution = ResolutionConfig(
        alias_table={
            "HQ-9/P": ["HQ-9P", "HQ 9 P", "FD-2000"],
            "HQ-9BE": ["HQ-9 BE", "HQ9BE"],
            "HT-233": ["HT233", "Type 305B"],
            "CASIC": ["China Aerospace Science and Industry Corporation", "2nd Academy"],
            "Karachi Army Air Defence Site (Malir)": ["Malir AD site", "Karachi AD site"],
        }
    )
    credibility = CredibilityConfig(
        thresholds={"confirmed": 0.80, "probable": 0.50},
        half_lives_days={"based-at": 365.0, "inducted-into": 1825.0, "supplies-component": 3650.0},
        # The band an answer may rest a link on (mirrors config/credibility.yaml). Declared here because
        # the band FAILS CLOSED when absent: an undeclared band means nothing is assertable, which is the
        # safe default but would make this fixture's supplier hop untraceable for the wrong reason.
        assertable_status=["confirmed", "probable"],
    )
    subjects = SubjectsConfig(
        subjects=[
            SubjectLens(
                subject_id="lens-hq9p-pk",
                anchors=["unit_paad", "site_karachi"],
                max_hops=3,
                materiality_filter={
                    "materiality_attrs": ["chokepoint_status", "chokepoint_count", "substitutability_state", "status"],
                    "never_drop_indeterminate": True,
                },
                target_queries=[
                    "trace this deployed HQ-9/P battery back to its component supplier and name the chokepoint",
                    "is this holding confirmed or probable, and on what evidence?",
                    "what do we NOT know here?",
                ],
            )
        ]
    )
    templates = TemplatesConfig(
        # mirrors config/templates.yaml's edge_phrasing so the fixture hero renders through the SAME
        # answer-prose path as the shipped one (a hop reads as a clause, not as its edge identifier);
        # an edge with no entry falls back to the bare edge name.
        edge_phrasing={
            "based-at": {"forward": "is based at", "inverse": "is the basing site of"},
            "inducted-into": {"forward": "is in service with", "inverse": "operates"},
            "equips": {
                "forward": "is fitted to", "inverse": "is equipped with",
                "by_from_type": {"unit": {"forward": "fields", "inverse": "is fielded by"}},
            },
            "supplies-component": {"forward": "supplies", "inverse": "is supplied by"},
            "manufactures": {"forward": "manufactures", "inverse": "is manufactured by"},
        },
        templates=[
            EvidenceTemplate(
                assertion_type="sole-source",
                require={"all_of": ["customs_bill_of_lading", "sanctions_or_tender_naming_supplier"]},
                on_fail="insufficient_evidence",
                refusal_template=(
                    "Insufficient evidence to assess sole-source status for {subject}: missing {missing}. "
                    "Next coverage due {next_coverage_due}."
                ),
            ),
            EvidenceTemplate(
                assertion_type="based-at",
                require={"any_of": ["imagery_confirmation", "official_statement"]},
                on_fail="insufficient_evidence",
                refusal_template=(
                    "Insufficient evidence to confirm basing for {subject}: missing {missing}. "
                    "Next coverage due {next_coverage_due}."
                ),
            ),
        ]
    )
    return ConfigBundle(
        version=1,
        ontology=ontology,
        sources=sources,
        resolution=resolution,
        credibility=credibility,
        subjects=subjects,
        templates=templates,
    )
