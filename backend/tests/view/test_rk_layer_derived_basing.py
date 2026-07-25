"""D-13.6 / A4 — basing becomes a **pure rebuild-derived edge**: deleted, not relocated.

Spec (§7 RK-LAYER 4, verbatim):

    "**Basing as a pure rebuild-derived edge (A4/D-13.6) — deleted, not relocated.** The offline pass in
    ``ingest/basing.py`` that **MINTS** a ``kind='inference'`` ``ClaimRecord`` (``make_claim_id``,
    ``basing.py:357-366``) and **appends** it (``store.append_many``) is **DELETED**. In its place,
    ``rebuild()`` materializes a derived-layer ``based-at`` **EDGE** each rebuild, **citing its two premise
    claim-atoms** (the ``observed-at`` claim + the ``inducted-into`` claim) for one-click provenance — with
    **NO ``make_claim_id``/``ClaimRecord`` mint and NO ``store.append`` inside rebuild**. … Consequently the
    **``__basing.json`` derived-claim bundles cease to exist**: the seed loader's
    ``_DERIVED_BUNDLE_SUFFIXES`` glob and the ``pending.py`` references that ride them **drop with the
    deleted pass**."

and spine/13 §5.3: "a derived, premise-cited, lower-confidence ``based-at`` binds U to the site … the
replumb makes it a first-class, **rebuild-time** derived-layer binding per D-13.6, not an offline pre-freeze."

The derivation triangle is built abstractly: equipment observed at a *locatable* site, plus an
``inducted-into`` link tying that equipment to a named unit. That is the same triangle
``ingest/basing.py`` reads today, so the fixture is faithful to the rule rather than to the implementation.
"""

from __future__ import annotations

from chanakya.store import EvidenceLog
from chanakya.view import rebuild, view_to_json
from tests import _rk_atoms as atoms
from tests import _rk_layer as rk

DESIGN, SITE, UNIT = "hq9p", "site_rahwali", "unit_8ad"
OBS, IND = "c-obs", "c-ind"
BASING = "based-at"


def _cfg():
    return rk.fixture_config()


def _triangle(*, unit: str = UNIT, ind_claim: str = IND) -> list:
    """``observed-at`` (equipment → located site) + ``inducted-into`` (equipment → named unit)."""
    return [
        rk.entity_claim(DESIGN, "variant", name="HQ-9/P"),
        rk.entity_claim(SITE, "basing_site", name="Rahwali",
                        attrs=rk.coords(32.28, 74.13, "rahwali") | {"occupancy_state": "occupied"}),
        rk.entity_claim(unit, "unit", name="8th AD Battalion", cid=f"ent-{unit}"),
        rk.rel_claim(OBS, DESIGN, "observed-at", SITE, iso="2025-03-29"),
        rk.rel_claim(ind_claim, DESIGN, "inducted-into", unit, iso="2021-06-01"),
    ]


def _derived_basings(view) -> list:
    return [e for e in rk.edges_of(view, BASING)]


def _provenance(edge) -> set[str]:
    """Every claim id reachable from the edge — its own citations plus anything named in its attrs."""
    out = set(edge.claim_ids)
    for value in (edge.attrs or {}).values():
        if isinstance(value, str):
            out.add(value)
        elif isinstance(value, (list, tuple)):
            out.update(str(v) for v in value)
    return out


def test_rebuild_materializes_the_derived_basing_edge() -> None:
    """§7 RK-LAYER 4: "``rebuild()`` materializes a derived-layer ``based-at`` **EDGE** each rebuild"."""
    view = rk.build_view(_cfg(), _triangle())
    derived = _derived_basings(view)

    assert derived, (
        "rebuild() materialized no `based-at` edge from the derivation triangle (equipment observed at a "
        "located site + an `inducted-into` link to a named unit) — D-13.6 makes this a rebuild-time derived "
        f"binding, not an offline pre-freeze. Edges built: "
        f"{[(e.type, e.source, e.target) for e in view.edges]}. {rk.flag_report()}"
    )
    assert [(e.source, e.target) for e in derived] == [(UNIT, SITE)], (
        f"the derived basing binds {[(e.source, e.target) for e in derived]} — spine/13 §5.3 binds the "
        "*formation* to the *site* (U → site), which is what the relocation beat and the freshness decay "
        "hang on"
    )


def test_the_derived_basing_cites_both_premise_claim_atoms() -> None:
    """§7 RK-LAYER 4: "**citing its two premise claim-atoms** (the ``observed-at`` claim + the
    ``inducted-into`` claim) for one-click provenance" — gate G4's one-click traceability, on a derived edge
    that has no claim of its own to hide behind."""
    view = rk.build_view(_cfg(), _triangle())
    derived = _derived_basings(view)
    assert derived, f"no derived basing to check provenance on. {rk.flag_report()}"

    cited = _provenance(derived[0])
    missing = {OBS, IND} - cited
    assert not missing, (
        f"the derived basing does not cite {sorted(missing)} (reachable: {sorted(cited)}) — the derived edge "
        "must name BOTH premises: without them the attribution asserts a formation at a site with nothing an "
        "analyst can click through to (G4, D-13.6)"
    )


def test_the_derived_basing_is_weaker_than_a_stated_one() -> None:
    """D-13.13: the derived path is "a ``kind=inference`` ``based-at``, premise-tied, capped at *probable*" —
    "the derived path is weaker by construction", and "an inference shares an independence group with its
    premises so it can never self-corroborate to confirmed"."""
    derived_view = rk.build_view(_cfg(), _triangle())
    stated_view = rk.build_view(_cfg(), [
        rk.entity_claim(UNIT, "unit", name="8th AD Battalion"),
        rk.entity_claim(SITE, "basing_site", name="Rahwali", attrs=rk.coords(32.28, 74.13, "rahwali")),
        rk.rel_claim("c-stated", UNIT, BASING, SITE, iso="2025-03-29"),
        rk.rel_claim("c-stated2", UNIT, BASING, SITE, iso="2025-04-02", sid="s2"),
    ])
    derived = _derived_basings(derived_view)
    stated = _derived_basings(stated_view)
    assert derived, f"no derived basing to compare. {rk.flag_report()}"
    assert stated, "fixture broken: the stated basing produced no edge"

    d_conf = derived[0].confidence.assertion_confidence if derived[0].confidence else None
    s_conf = stated[0].confidence.assertion_confidence if stated[0].confidence else None

    assert derived[0].status != "confirmed", (
        f"the derived basing reached {derived[0].status!r} — a premise-tied inference 'can never "
        "self-corroborate to confirmed' (D-13.13; config/credibility.yaml's independence rule)"
    )
    assert d_conf is not None and s_conf is not None and d_conf < s_conf, (
        f"the derived attribution scores {d_conf} against the stated path's {s_conf} — 'the derived path is "
        "weaker by construction' (spine/13 §5.3), which is what keeps 'kit photographed here' apart from "
        "'this formation is stationed here'"
    )


def test_the_derivation_appends_nothing_to_the_evidence_log() -> None:
    """The bi-level invariant: "with **NO** ``make_claim_id``/``ClaimRecord`` mint and **NO**
    ``store.append`` inside rebuild" (§7 RK-LAYER 4); "rebuild never writes evidence" (§1 + DECISIONS)."""
    log = EvidenceLog()
    log.append_many(_triangle())
    before = log.count()

    view = rebuild(log, [], _cfg())

    assert log.count() == before, (
        f"rebuild() grew the append-only evidence log from {before} to {log.count()} claims — the derived "
        "basing must be a knowledge-layer EDGE, not a minted claim (G17, D-13.6)"
    )
    assert _derived_basings(view), (
        "no derived basing was materialized, so this test proves nothing about minting — the fixture must "
        f"exercise the derived branch to be non-vacuous (§5a). {rk.flag_report()}"
    )


def test_two_rebuilds_of_the_derived_basing_are_byte_identical() -> None:
    """G2, extended over the new derivation: "two rebuilds byte-identical; no LLM/network/clock/RNG under
    rebuild" (session Gates). A derivation that keyed on iteration order or a clock would drift here."""
    claims = _triangle()
    first = view_to_json(rk.build_view(_cfg(), claims))
    second = view_to_json(rk.build_view(_cfg(), claims))

    assert first == second, "two rebuilds of the derived-basing fixture disagree — G2"
    assert _derived_basings(rk.build_view(_cfg(), claims)), (
        f"the fixture derives nothing, so the byte-identity above is vacuous. {rk.flag_report()}"
    )


def test_the_offline_minting_pass_no_longer_mints() -> None:
    """§7 RK-LAYER 4: the offline pass "is **DELETED**" — "deleted, not relocated".

    Asserted as *no mint site in that module* rather than as "the file is gone", because the plan's
    requirement is about the mint and the append, and a module that survives as a pure helper breaks nothing.
    """
    sites = atoms.call_sites("make_claim_id", root=rk.PKG_ROOT)
    offenders = [s for s in sites if s.startswith("ingest/basing.py")]

    assert not offenders, (
        f"ingest/basing.py still mints claim atoms at {offenders} — §7 RK-LAYER 4 deletes the minting pass "
        "and replaces it with a rebuild-time derived edge; keeping both means the graph carries the "
        "attribution twice, once as frozen evidence and once as a derivation"
    )


def test_the_basing_derived_bundle_suffix_is_gone() -> None:
    """§7 RK-LAYER 4: "the **``__basing.json`` derived-claim bundles cease to exist**: the seed loader's
    ``_DERIVED_BUNDLE_SUFFIXES`` glob and the ``pending.py`` references that ride them **drop with the
    deleted pass**"."""
    from chanakya.ingest import seed

    suffixes = tuple(getattr(seed, "_DERIVED_BUNDLE_SUFFIXES", ()))
    offenders = [s for s in suffixes if "basing" in s]

    assert not offenders, (
        f"the seed loader still globs derived basing bundles {offenders} — with the pass deleted, such a "
        "bundle would replay a frozen inference the rebuild now derives, so the same attribution would "
        "arrive twice and the frozen copy would never age or re-derive (§7 RK-LAYER 4)"
    )
