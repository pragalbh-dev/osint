"""AH-1 — a tripwire that is watching nothing must SAY it is watching nothing.

The defect these cover, measured on the real corpus before the fix:

* the flagship ``obs-basing-relocation`` fired **1** alert (``unit_hq9b``: ``site_rawalpindi`` →
  ``site_rahwali``);
* re-pointing its ``watch_instances`` at an id no node carries produced **0** alerts, **no exception**,
  and nothing in any log or surface — an absence presented as an all-clear, the exact inverse of this
  system's one non-negotiable;
* worse, ``resolve_scope`` seeded itself with the RAW CONFIG STRINGS, so the returned scope still
  contained ``unit_hq9b_TYPO`` — a phantom that made the broken anchor look present while the real node
  was excluded, masking the fault from anyone debugging it.

So the assertions are in two families: the scope must stop lying about what it contains, and the
unresolved anchor must be *named* on the analyst-facing output.

The scope **semantics are deliberately unchanged** and one test pins that: an observable whose anchors
all miss keeps returning its (non-matching) ``watch_instances`` set rather than ``None``, because
``None`` means *unscoped* to ``_in_scope`` — i.e. match everything. Collapsing to ``None`` would turn
"silently fires nothing" into "silently fires on the whole graph", a louder lie, not a fix.
"""

from __future__ import annotations

from chanakya.observe import anchor_diagnostics, evaluate, explain, resolve_scope, resolve_scope_detail
from chanakya.schemas import SubjectLens, SubjectsConfig

from .conftest import config_with, relocation_observable, view

# ── a two-site relocation the tripwire should catch ──────────────────────────────────────────────

_NODES = [
    {"id": "unit_alpha", "type": "unit", "name": "Alpha Battery"},
    {"id": "site_a", "type": "basing_site", "name": "Site A"},
    {"id": "site_b", "type": "basing_site", "name": "Site B"},
]


def _before():
    return view(nodes=_NODES, edges=[
        {"id": "e-a", "type": "based-at", "source": "unit_alpha", "target": "site_a",
         "edge_instance": "ei-1", "claim_ids": ["c1"]},
    ])


def _after():
    return view(nodes=_NODES, edges=[
        {"id": "e-b", "type": "based-at", "source": "unit_alpha", "target": "site_b",
         "edge_instance": "ei-2", "claim_ids": ["c2"]},
    ])


def _config(*observables):
    """Config carrying the given observables and NO lens the observables can fall back onto."""
    cfg = config_with(*observables)
    return cfg.model_copy(update={"subjects": SubjectsConfig(subjects=[])})


# ── the working path is untouched ────────────────────────────────────────────────────────────────

def test_good_anchor_still_fires_exactly_as_before() -> None:
    """The regression guard: a resolvable anchor fires the same single alert it always did."""
    obs = relocation_observable(watch_instances=["unit_alpha"])
    alerts = evaluate(_before(), _after(), _config(obs))
    assert len(alerts) == 1
    assert alerts[0].subject == "unit_alpha"
    assert alerts[0].before == {"based-at": "site_a"} and alerts[0].after == {"based-at": "site_b"}


def test_good_anchor_reports_no_complaint() -> None:
    """A healthy tripwire must not cry wolf — no warning, nothing on the diagnostics list."""
    obs = relocation_observable(watch_instances=["unit_alpha"])
    cfg = _config(obs)
    detail = resolve_scope_detail(obs, _after(), cfg)
    assert detail.missing == ()
    assert detail.warning is None
    assert detail.watching_nothing is False
    assert anchor_diagnostics(cfg, _after()) == []


def test_good_anchor_scope_is_unchanged_by_the_diagnosis() -> None:
    """``resolve_scope`` still returns exactly the reachable set — diagnosis is additive, not a rewrite."""
    obs = relocation_observable(watch_instances=["unit_alpha"])
    assert resolve_scope(obs, _after(), _config(obs)) == {"unit_alpha"}


# ── a broken anchor is loud ──────────────────────────────────────────────────────────────────────

def test_broken_anchor_is_not_a_phantom_in_the_scope() -> None:
    """The masking bug: the raw config string used to sit in the returned scope as if it had resolved."""
    obs = relocation_observable(watch_instances=["unit_alpha_TYPO"])
    scope = resolve_scope(obs, _after(), _config(obs))
    assert scope is not None
    assert not (scope & {n["id"] for n in _NODES}), "no real node is in scope — the tripwire is blind"


def test_broken_anchor_names_itself_on_the_scope_resolution() -> None:
    obs = relocation_observable(watch_instances=["unit_alpha_TYPO"])
    detail = resolve_scope_detail(obs, _after(), _config(obs))
    assert detail.missing == ("unit_alpha_TYPO",)
    assert detail.watching_nothing is True
    assert detail.watched_node_count == 0
    assert detail.warning is not None
    assert "unit_alpha_TYPO" in detail.warning
    assert "all-clear" in detail.warning  # it refuses to let the silence read as one


def test_broken_anchor_fires_nothing_but_says_so() -> None:
    """The whole point: still 0 alerts (scope semantics preserved) — but no longer silent about it."""
    obs = relocation_observable(watch_instances=["unit_alpha_TYPO"])
    cfg = _config(obs)
    assert evaluate(_before(), _after(), cfg) == []

    problems = anchor_diagnostics(cfg, _after())
    assert len(problems) == 1
    assert problems[0]["observable_id"] == obs.observable_id
    assert problems[0]["unresolved_anchors"] == ["unit_alpha_TYPO"]
    assert problems[0]["watching_nothing"] is True
    assert "unit_alpha_TYPO" in problems[0]["warning"]


def test_explain_names_the_unresolved_anchor() -> None:
    """``explain()`` echoed ``watch_instances`` verbatim and never said whether they resolved."""
    obs = relocation_observable(watch_instances=["unit_alpha_TYPO"])
    out = explain(obs, _after(), _config(obs))
    assert out["unresolved_anchors"] == ["unit_alpha_TYPO"]
    assert out["watching_nothing"] is True
    assert out["anchor_check"] != "ok"
    assert "unit_alpha_TYPO" in out["anchor_warning"]


def test_explain_without_a_view_refuses_to_imply_a_pass() -> None:
    """An unperformed check is never reported as a clean bill of health."""
    out = explain(relocation_observable(watch_instances=["unit_alpha_TYPO"]))
    assert out["unresolved_anchors"] is None
    assert "not performed" in out["anchor_check"]


# ── the partially-broken case: part of what it claims to watch is unwatched ──────────────────────

def test_partial_miss_is_reported_even_though_the_tripwire_still_works() -> None:
    """One good anchor must not launder a bad one — this is how the fault stayed hidden in the field."""
    obs = relocation_observable(watch_instances=["unit_alpha", "unit_bravo_TYPO"])
    cfg = _config(obs)
    detail = resolve_scope_detail(obs, _after(), cfg)
    assert detail.missing == ("unit_bravo_TYPO",)
    assert detail.watching_nothing is False  # it IS still watching something …
    assert detail.watched_node_count == 1
    assert "unit_bravo_TYPO" in (detail.warning or "")  # … and it still says what it is not watching
    assert len(evaluate(_before(), _after(), cfg)) == 1  # the working half is untouched


# ── the opposite failure: a lens-only observable silently widens to the whole graph ──────────────

def test_lens_only_observable_that_loses_its_anchors_says_it_went_unscoped() -> None:
    """``None`` scope means MATCH EVERYTHING. That fallback is preserved — but it must be stated.

    Left silent, an analyst reads a firing as being about the declared subject when it is really about
    any element in the graph. This is the reason the fix does not simply delete the literal seed.
    """
    obs = relocation_observable(subject="lens-x", watch_instances=[])
    cfg = config_with(obs).model_copy(
        update={"subjects": SubjectsConfig(
            subjects=[SubjectLens(subject_id="lens-x", anchors=["nothing_here"], max_hops=2)]
        )}
    )
    detail = resolve_scope_detail(obs, _after(), cfg)
    assert detail.node_ids is None, "unscoped fallback preserved — the recall-biased behaviour"
    assert detail.missing == ("nothing_here",)
    assert "UNSCOPED" in (detail.warning or "")
    # and it does fire, on the whole graph — which is exactly why the warning has to exist
    assert len(evaluate(_before(), _after(), cfg)) == 1


def test_all_anchors_missing_keeps_the_non_matching_scope_not_unscoped() -> None:
    """Pins the semantics choice: declared ``watch_instances`` never collapse to "match everything"."""
    obs = relocation_observable(watch_instances=["unit_alpha_TYPO"])
    scope = resolve_scope(obs, _after(), _config(obs))
    assert scope is not None, (
        "returning None here would convert a silent-no-alerts bug into a silent-ALL-alerts bug"
    )
