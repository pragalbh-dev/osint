"""G17 (RK-LAYER's extension) — **no claim mint and no ``store.append`` under ``rebuild()``**.

The gate row (plan §5, G17): "Atoms are minted only at ingest and never inside ``rebuild()``; **no code path
under ``rebuild()`` calls ``make_claim_id`` or ``store.append``** (the basing derivation must be a pure edge,
not a minted claim) … *Phasing:* the no-mint/no-append clause binds from **S2**".

And the non-vacuity requirement, verbatim: "*Fixture must be non-vacuous:* include an
``observed-at``+``inducted-into`` premise pair so the derived-basing branch actually executes under
``rebuild()`` (else it passes vacuously), or use an input-independent static call-graph scan of
rebuild-reachable modules for ``make_claim_id(``/``store.append``".

Both accepted forms are implemented, because they fail on different mistakes: the **behavioural** form
catches a mint on the path actually taken, and the **static** form catches a mint on a path this fixture
happens not to reach. Neither can pass vacuously:

* the behavioural test asserts the derived branch *executed* (a derived ``based-at`` exists) before claiming
  anything about minting — that assertion fails today, which is what makes the gate bite from S2;
* the static scan is self-checked twice — it must find the real mint definitions, and it must flag a planted
  violation written to ``tmp_path``.

``tests/gates/test_g17_atom_mint.py`` (S1) keeps the *atoms-minted-only-at-ingest* half; this file adds only
S2's clause and deliberately does not restate S1's.
"""

from __future__ import annotations

import pytest

from chanakya.store import EvidenceLog
from chanakya.view import rebuild, view_to_json
from tests import _rk_layer as rk

DESIGN, SITE, UNIT = "hq9p", "site_rahwali", "unit_8ad"
BASING = "based-at"

#: ``schemas/ids.py`` *defines* the constructors; a definition is not a mint site, and the S1 gate already
#: proved the module is **incapable** of appending an atom (``test_the_exempt_id_module_cannot_mint``).
#: Narrow to the defining module — never widen it to a package.
_MINT_DEFINING_MODULE = "schemas/ids.py"


def _premise_pair() -> list:
    """The non-vacuous fixture the plan asks for: an ``observed-at`` + ``inducted-into`` premise pair."""
    return [
        rk.entity_claim(DESIGN, "variant", name="HQ-9/P"),
        rk.entity_claim(SITE, "basing_site", name="Rahwali",
                        attrs=rk.coords(32.28, 74.13, "rahwali") | {"occupancy_state": "occupied"}),
        rk.entity_claim(UNIT, "unit", name="8th AD Battalion"),
        rk.rel_claim("c-obs", DESIGN, "observed-at", SITE, iso="2025-03-29"),
        rk.rel_claim("c-ind", DESIGN, "inducted-into", UNIT, iso="2021-06-01"),
    ]


def _cfg():
    return rk.fixture_config()


# ── non-vacuity: the derived branch must actually execute ────────────────────────────────────────

def test_the_derived_basing_branch_executes_under_rebuild() -> None:
    """Without this, everything below passes because nothing derives anything (§5a: "a gate that cannot fail
    is a gate that lies")."""
    view = rk.build_view(_cfg(), _premise_pair())

    assert rk.edges_of(view, BASING), (
        "the premise pair derived no `based-at` edge, so the no-mint clauses below are vacuous — the "
        "fixture exists precisely so 'the derived-basing branch actually executes under rebuild()' "
        f"(§5 G17). {rk.flag_report()}"
    )


# ── behavioural: the write path is unreachable from rebuild ──────────────────────────────────────

def test_rebuild_completes_with_the_evidence_log_write_path_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G17: "no code path under ``rebuild()`` calls … ``store.append``".

    Asserted the way G1 asserts purity — by making the forbidden facility explode and rebuilding anyway. The
    same view must come out, so the derivation cannot be "pure" only when it is skipped.
    """
    log = EvidenceLog()
    log.append_many(_premise_pair())
    expected = view_to_json(rebuild(log, [], _cfg()))

    def boom(*_args, **_kwargs):
        raise AssertionError(
            "rebuild() wrote to the append-only evidence log — G17 forbids `store.append` under rebuild; "
            "the derived basing must be a knowledge-layer edge, not a minted claim"
        )

    monkeypatch.setattr(EvidenceLog, "append", boom)
    monkeypatch.setattr(EvidenceLog, "append_many", boom)

    again = rebuild(log, [], _cfg())

    assert view_to_json(again) == expected, (
        "rebuild() produced a different view once the evidence-log write path was disabled — some part of "
        "the derivation depends on writing evidence (G17 / the bi-level invariant)"
    )


def test_rebuild_completes_with_the_claim_mint_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """G17: "no code path under ``rebuild()`` calls ``make_claim_id``".

    Patched on ``chanakya.schemas`` *and* ``chanakya.schemas.ids`` so a module that imported the name either
    way is covered; a caller that bound it at import time is caught by the static scan below instead.
    """
    log = EvidenceLog()
    log.append_many(_premise_pair())
    expected = view_to_json(rebuild(log, [], _cfg()))

    def boom(*_args, **_kwargs):
        raise AssertionError(
            "rebuild() minted a claim atom — atoms are minted once, at ingest (G17/D-13.11); a rebuild-time "
            "mint puts a derived, reversible decision into the immutable evidence layer"
        )

    import chanakya.schemas as schemas
    import chanakya.schemas.ids as ids

    monkeypatch.setattr(ids, "make_claim_id", boom)
    monkeypatch.setattr(schemas, "make_claim_id", boom, raising=False)

    again = rebuild(log, [], _cfg())

    assert view_to_json(again) == expected, (
        "rebuild() produced a different view once the claim mint was disabled — the derivation is minting "
        "(G17)"
    )


# ── static: the input-independent call-graph scan ────────────────────────────────────────────────

def test_no_mint_or_evidence_append_in_any_rebuild_reachable_module() -> None:
    """The plan's second accepted form: "an input-independent static call-graph scan of rebuild-reachable
    modules for ``make_claim_id(``/``store.append``".

    Static because the behavioural test can only see the path *this* fixture takes; a derivation that mints
    on a branch the fixture misses would still be a G17 violation.
    """
    modules = rk.rebuild_reachable_modules()
    assert len(modules) > 5, (
        f"the reachability walk found only {len(modules)} module(s) — a broken walk would pass this gate "
        "vacuously (§5a)"
    )

    hits = rk.forbidden_writes_in(modules)
    offenders = {
        what: [w for w in where if not w.startswith(_MINT_DEFINING_MODULE)]
        for what, where in hits.items()
    }
    offenders = {what: where for what, where in offenders.items() if where}

    assert not offenders, (
        f"rebuild-reachable module(s) mint a claim atom or append to the evidence log: {offenders} — G17's "
        "no-mint/no-append clause binds from S2, and the basing derivation is the specific case it names "
        "('the basing derivation must be a pure edge, not a minted claim')"
    )


def test_the_reachability_walk_sees_the_real_rebuild_path() -> None:
    """A self-check on the scan surface: the modules the derivation would live in must be *in* it."""
    reachable = {str(p.relative_to(rk.PKG_ROOT)) for p in rk.rebuild_reachable_modules()}

    for expected in ("view/pipeline.py", "view/supersede.py", "resolve/__init__.py",
                     "credibility/supersession.py"):
        assert expected in reachable, (
            f"{expected} is not in the rebuild-reachable set {sorted(reachable)} — the scan would miss a "
            "mint placed there, which is exactly where the derivation lands"
        )


def test_the_write_scanner_flags_a_planted_violation(tmp_path) -> None:
    """The negative control that makes the static scan non-vacuous.

    Mirrors ``tests/gates/test_g17_atom_mint.py::test_the_mint_scanner_flags_a_planted_violation``: a scanner
    that silently found nothing would turn this gate green for the worst possible reason.
    """
    pkg = tmp_path / "chanakya"
    (pkg / "view").mkdir(parents=True)
    (pkg / "view" / "pipeline.py").write_text(
        "from chanakya.schemas import make_claim_id\n"
        "from . import helper\n"
        "def rebuild(store):\n"
        "    cid = make_claim_id('d01', 'x')\n"
        "    store.append(cid)\n",
        encoding="utf-8",
    )
    (pkg / "view" / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "view" / "helper.py").write_text(
        "def derive(evidence_log, rows):\n"
        "    evidence_log.append_many(rows)\n"
        "    plain = []\n"
        "    plain.append('not an evidence write')\n"
        "    return plain\n",
        encoding="utf-8",
    )

    modules = rk.rebuild_reachable_modules(root=pkg)
    hits = rk.forbidden_writes_in(modules, root=pkg)

    assert {p.name for p in modules} >= {"pipeline.py", "helper.py"}, (
        f"the walk did not follow the relative import into the helper: {[p.name for p in modules]} — the "
        "real rebuild path is written with relative imports, so a walk that misses them scans almost nothing"
    )
    assert "make_claim_id" in hits, f"the scanner missed a planted claim mint: {hits}"
    assert any("append" in what for what in hits), f"the scanner missed a planted evidence append: {hits}"
    assert not any(
        "plain.append" in what for what in hits
    ), f"the scanner flagged a plain list append as an evidence write: {hits}"
