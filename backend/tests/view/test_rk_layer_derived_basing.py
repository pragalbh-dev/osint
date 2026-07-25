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


#: A frozen derived-basing bundle, of the shape the deleted offline pass used to freeze.
_FROZEN_BASING_BUNDLE = "d99__basing.json"
_FROZEN_DOC_BUNDLE = "d99.json"


def _write_bundles(root) -> None:
    """One ordinary bundle plus one frozen ``__basing.json`` inference beside it."""
    import json

    ordinary = rk.rel_claim("c-obs", DESIGN, "observed-at", SITE, iso="2025-03-29")
    derived = rk.rel_claim(
        "c-frozen-basing", UNIT, BASING, SITE, iso="2025-03-29", kind="inference",
        premises=["c-obs", "c-ind"], attributes={"derived_via": "observed-at+inducted-into"},
    )
    (root / _FROZEN_DOC_BUNDLE).write_text(
        json.dumps([ordinary.model_dump(mode="json")]), encoding="utf-8")
    (root / _FROZEN_BASING_BUNDLE).write_text(
        json.dumps([derived.model_dump(mode="json")]), encoding="utf-8")


class _Collector:
    """The minimal ``SupportsAppendMany`` the seed loader writes into."""

    def __init__(self) -> None:
        self.claim_ids: list[str] = []

    def append_many(self, records) -> None:
        self.claim_ids.extend(r.claim_id for r in records)


def _seed(root, config) -> _Collector:
    """Run the seed loader, threading ``config`` through whichever keyword it accepts.

    The flag has to reach the glob somehow and the spec does not fix the parameter's name, so it is
    discovered. A loader that accepts no config at all cannot be flag-gated — reported as the failure it is.
    """
    import inspect

    from chanakya.ingest.seed import seed_store_from_bundles

    sink = _Collector()
    params = inspect.signature(seed_store_from_bundles).parameters
    for name in ("config", "config_bundle", "bundle", "cfg", "configuration"):
        if name in params:
            seed_store_from_bundles(sink, root, **{name: config})
            return sink
    seed_store_from_bundles(sink, root)
    return sink


def test_the_derived_basing_bundle_is_skipped_with_the_flag_on(tmp_path) -> None:
    """§7 RK-LAYER 4 as **ruled 2026-07-25** (reconciling both hands): "**Flag-gate the glob** … flag **on** ⇒
    the glob is **skipped**, so a frozen bundle cannot replay an inference the rebuild now derives (the same
    attribution would arrive twice and the frozen copy would never age or re-derive). The bundles themselves
    still die with RK-DATA."

    Asserted on the loader's **behaviour**, not on the absence of a module constant: the constant is an
    implementation detail, while "does a frozen derived attribution still enter the log?" is the property —
    and the behavioural form survives RK-DATA finally deleting the bundles, because this fixture writes its
    own. (The earlier version of this test asserted the constant was gone *unconditionally*, which would have
    demanded the very flag-off byte-identity break the implementer was right to refuse.)
    """
    _write_bundles(tmp_path)

    loaded = _seed(tmp_path, rk.fixture_config(flag_on=True))

    assert "c-obs" in loaded.claim_ids, (
        f"the ordinary bundle was not seeded at all ({loaded.claim_ids}) — the fixture is broken, not the code"
    )
    assert "c-frozen-basing" not in loaded.claim_ids, (
        f"with the flag ON the frozen {_FROZEN_BASING_BUNDLE} was still seeded ({loaded.claim_ids}) — the "
        "rebuild now derives that attribution itself, so seeding the frozen copy makes the same attribution "
        f"arrive twice and the frozen one never ages or re-derives. {rk.flag_report()}"
    )


def test_the_derived_basing_bundle_still_loads_with_the_flag_off(tmp_path) -> None:
    """The other half of the same ruling: "flag **off** ⇒ the glob stays, so flag-off byte-identity holds".

    The mirror matters as much as the skip: dropping the glob unconditionally *is* the flag-off byte-identity
    break, so this is the assertion that stops the fix over-reaching.
    """
    _write_bundles(tmp_path)

    loaded = _seed(tmp_path, rk.fixture_config(flag_on=False))

    assert "c-frozen-basing" in loaded.claim_ids, (
        f"with the flag OFF the frozen {_FROZEN_BASING_BUNDLE} was skipped ({loaded.claim_ids}) — the bundles "
        "die with RK-DATA, not here; skipping them now breaks S2's own safety property"
    )


def test_the_superseded_bundle_suffix_is_config_declared() -> None:
    """G6: which frozen bundles the rebuild has taken over is a statement about *data*, so it belongs in
    config rather than a code literal — and an analyst should be able to see the list.

    Discovered by **value**, not by key name, so a rename cannot fail a test that is really about the suffix
    being declared at all.
    """
    declared: dict[str, list[str]] = {}

    def walk(prefix: str, value) -> None:
        if isinstance(value, dict):
            for key, sub in value.items():
                walk(f"{prefix}.{key}" if prefix else str(key), sub)
        elif isinstance(value, (list, tuple)) and value and all(isinstance(v, str) for v in value):
            # A *bundle suffix*, not merely a string mentioning basing: `basing_site` appears in blocking
            # keys and trace lanes throughout the config, and matching those would pass this test for the
            # wrong reason (it did, on first run).
            if any("basing" in v and (v.endswith(".json") or "__" in v) for v in value):
                declared[prefix] = list(value)

    walk("", rk.shipped_bundle().model_dump())

    assert declared, (
        "no config surface declares the derived-bundle SUFFIX the flag gates (searched every list-of-strings "
        "for one naming a basing *bundle* — `…__basing.json`-shaped, not merely the string 'basing_site') — "
        "the flag-gated glob should read a config-declared list so the takeover is auditable and hot-editable "
        "(G6: no magic strings in code)"
    )
