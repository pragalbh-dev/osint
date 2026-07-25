"""AH-2 — an anchor that is *awaiting coverage* is not a *broken* anchor, and must not read like one.

AH-1 made an unresolved anchor loud. Measured on the shipped default boot state, it was loud about the
wrong thing: ``config/sources.yaml`` withholds ``d18``/``d19`` from the seed **on purpose** so a reviewer
can ingest them live and watch the flagship tripwire fire, which means ``site_rahwali`` legitimately has
no node at first paint. Every armed observable therefore reported "…is NOT being watched, and silence
about it is not an all-clear" on a perfectly healthy system, and went quiet the moment the demo alert
fired — the alarm was loudest while nothing was wrong.

A monitoring surface that cries wolf while healthy teaches its analyst to ignore it. That is the same
failure as silence, reached from the other side, so these tests pin both directions:

* a miss that names a **declared registry entity** is a coverage statement, severity
  ``pending_coverage``, and carries no "correct the anchor id" advice — there is nothing to correct;
* a miss that names **nothing anywhere** is still a fault, still loud, still says "correct the anchor id".

The rest pin the silences AH-1 left behind: an ``arm-only`` observable whose scope is provably never
consulted, a subject reference that names no lens, and a lens that declares no anchors at all.
"""

from __future__ import annotations

from chanakya.observe import anchor_diagnostics, resolve_scope_detail
from chanakya.schemas import EntitiesConfig, EntityEntry, SubjectLens, SubjectsConfig

from .conftest import config_with, relocation_observable, view

#: The registry is what tells a *declared but uncovered* entity apart from an id nobody has heard of.
#: The golden test bundle ships an empty registry, so these tests declare the one entry they reason
#: about — mirroring ``config/entities.yaml``, where ``site_rahwali`` really is declared.
REGISTRY = EntitiesConfig(
    entities=[
        EntityEntry(
            entity_id="site_rahwali",
            type="basing_site",
            canonical_name="Rahwali airfield/cantonment, Gujranwala",
            aliases=["Rahwali"],
        )
    ]
)

# ── a view holding the unit but NOT the site (the shipped withheld-seed boot state in miniature) ──
BOOT_VIEW = view(
    nodes=[
        {"id": "unit_hq9b", "type": "unit", "name": "43 Air Defence Regiment"},
        {"id": "unit_paad", "type": "unit", "name": "Pakistan Army Air Defence"},
    ],
    edges=[],
)


def _config(*observables, anchors=("unit_paad", "site_rahwali")):
    """Golden config + a declared registry + a lens declaring ``anchors``."""
    bundle = config_with(*observables)
    lens = SubjectLens(subject_id="lens-hq9p-pk", anchors=list(anchors), max_hops=3)
    return bundle.model_copy(
        update={"subjects": SubjectsConfig(subjects=[lens]), "entities": REGISTRY}
    )


def test_declared_entity_awaiting_coverage_is_not_reported_as_a_broken_anchor() -> None:
    """``site_rahwali`` IS in ``config/entities.yaml`` — it is uncovered, not misspelled."""
    obs = relocation_observable(subject="lens-hq9p-pk", watch_instances=["unit_hq9b"])
    detail = resolve_scope_detail(obs, BOOT_VIEW, _config(obs))

    assert detail.missing == ("site_rahwali",)
    assert detail.pending_coverage == ("site_rahwali",)
    assert detail.dangling == ()
    assert detail.severity == "pending_coverage"
    # The load-bearing assertion: no remedy is offered, because there is nothing to fix.
    assert "correct the anchor id" not in (detail.warning or "").lower()
    assert "coverage gap rather than a config fault" in (detail.warning or "")
    # It still SAYS what is uncovered — quieter, not silent.
    assert "site_rahwali" in (detail.warning or "")


def test_an_id_nothing_has_ever_heard_of_is_still_loud() -> None:
    """The re-keying threat model AH-1 exists for: not a node, not a registry entity, not an alias."""
    obs = relocation_observable(subject="lens-hq9p-pk", watch_instances=["unit_hq9b"])
    detail = resolve_scope_detail(obs, BOOT_VIEW, _config(obs, anchors=("unit_paad", "site_NOPE_9x")))

    assert detail.dangling == ("site_NOPE_9x",)
    assert detail.pending_coverage == ()
    assert detail.severity == "dangling"
    assert "correct the anchor id" in (detail.warning or "").lower()
    assert "not an all-clear" in (detail.warning or "")


def test_a_broken_anchor_is_not_laundered_by_a_pending_one_beside_it() -> None:
    """One of each: the fault must survive being mixed with a benign miss, and be named separately."""
    obs = relocation_observable(subject="lens-hq9p-pk", watch_instances=["unit_hq9b"])
    cfg = _config(obs, anchors=("unit_paad", "site_rahwali", "site_NOPE_9x"))
    detail = resolve_scope_detail(obs, BOOT_VIEW, cfg)

    assert detail.pending_coverage == ("site_rahwali",)
    assert detail.dangling == ("site_NOPE_9x",)
    assert detail.severity == "dangling"  # the fault wins the severity
    assert "site_NOPE_9x" in (detail.warning or "")
    assert "will bind themselves when coverage arrives" in (detail.warning or "")


def test_the_warning_names_the_config_object_that_actually_declared_the_anchor() -> None:
    """Two of the three shipped observables own no anchors — blaming them sends the analyst to the
    wrong file. The remedy must point at the lens that declared the id."""
    obs = relocation_observable(subject="lens-hq9p-pk", watch_instances=[])
    detail = resolve_scope_detail(obs, BOOT_VIEW, _config(obs, anchors=("unit_paad", "site_NOPE_9x")))

    assert detail.declared_in == {"unit_paad": "subject:lens-hq9p-pk", "site_NOPE_9x": "subject:lens-hq9p-pk"}
    assert "subject lens 'lens-hq9p-pk'" in (detail.warning or "")
    assert "config/subjects.yaml" in (detail.warning or "")
    assert "not by this observable" in (detail.warning or "")


def test_an_observables_own_watch_instance_is_attributed_to_the_observable() -> None:
    obs = relocation_observable(watch_instances=["unit_NOPE_9x"])
    detail = resolve_scope_detail(obs, BOOT_VIEW, config_with(obs))

    assert detail.declared_in == {"unit_NOPE_9x": "watch_instances"}
    assert "config/observables.yaml" in (detail.warning or "")


# ── the silences AH-1 left behind ────────────────────────────────────────────────────────────────


def test_arm_only_observable_is_not_blamed_for_a_silence_its_mode_already_explains() -> None:
    """``_fire``/``arm`` both return on ARM_ONLY *before* resolving scope, so its scope is provably
    never consulted. Reporting an anchor fault there is a false alarm about an unused value."""
    armed = relocation_observable(observable_id="obs-arm-only", subject="lens-hq9p-pk",
                                  trigger={"on": "new_claim"})
    cfg = _config(armed, anchors=("unit_paad", "site_NOPE_9x"))

    assert anchor_diagnostics(cfg, BOOT_VIEW) == []
    # …and it is not hidden: explain() still reports the anchors when asked directly.
    detail = resolve_scope_detail(armed, BOOT_VIEW, cfg)
    assert detail.dangling == ("site_NOPE_9x",)


def test_a_subject_naming_no_lens_no_longer_unscopes_in_silence() -> None:
    """A dangling ``subject:`` yields ``lens=None`` with no error — the observable then evaluates the
    WHOLE graph while claiming to be scoped to a subject. Scope is unchanged; the silence is not."""
    obs = relocation_observable(subject="lens-TYPO", watch_instances=[])
    detail = resolve_scope_detail(obs, BOOT_VIEW, _config(obs))

    assert detail.node_ids is None  # scope semantics deliberately preserved
    assert detail.severity == "unscoped"
    assert "no subject lens by that id exists" in (detail.warning or "")
    assert "config/subjects.yaml" in (detail.warning or "")


def test_a_lens_declaring_no_anchors_no_longer_unscopes_in_silence() -> None:
    """``anchors: []`` is legal config with no ``min_length``; it scoped nothing and said nothing."""
    obs = relocation_observable(subject="lens-hq9p-pk", watch_instances=[])
    detail = resolve_scope_detail(obs, BOOT_VIEW, _config(obs, anchors=()))

    assert detail.node_ids is None
    assert detail.severity == "unscoped"
    assert "declares NO anchors" in (detail.warning or "")
    assert "about the whole graph, not that subject" in (detail.warning or "")


def test_a_deliberately_global_tripwire_stays_silent() -> None:
    """No subject and no watch_instances = the config asked for a global tripwire. Not a fault."""
    obs = relocation_observable(subject=None, watch_instances=[])
    detail = resolve_scope_detail(obs, BOOT_VIEW, config_with(obs))

    assert detail.node_ids is None
    assert detail.warning is None
    assert detail.severity == "ok"
