"""Stage 3B-iii-B — the explicit-transition WITNESS as durable identity support.

Written **purely against the published contract**, blind to the implementation: ``resolve/scoring.py``
and ``resolve/cluster.py`` are deliberately NOT read (only ``has_transition_witness`` and
``has_durable_identity_support`` are *imported* from ``scoring``). These tests assert what *correct*
behaviour IS, not what any observed output happens to be. Every fixture asserts its own precondition
(this really is an ordered succession / a contradiction / a single-source-authored transition) so a
mis-built fixture cannot pass silently.

Contract under test (two bullets):

1. **``has_transition_witness(a, b, cfg)``** is True **iff**, for some identity-relevant
   (critical/supporting-role) attribute, the two sides' *combined* ``attr_history`` classifies as an
   ``ordered`` succession AND a SINGLE ``source_id`` asserted ≥2 DIFFERENT values within that succession
   (one source witnessed old→new). It is False when the transition is split across TWO sources (no single
   witness), when the combined series is a ``contradiction`` (not ordered), when no distinct-value change
   occurred, and when the attribute is NEUTRAL (not identity-relevant).
       → ``test_transition_witness_true_for_single_source_ordered_succession``
       → ``test_transition_witness_false_when_two_sources_split_the_transition``
       → ``test_transition_witness_false_when_series_is_a_contradiction``
       → ``test_transition_witness_false_when_no_distinct_value_change``
       → ``test_transition_witness_false_for_neutral_attribute``

2. **A witnessed transition is DURABLE identity support; an unwitnessed one is not.** So
   ``has_durable_identity_support`` becomes True for a WITNESSED perishable succession (the new channel)
   and stays False for its UNWITNESSED counterpart (the 3B-iii-A behaviour). Downstream, via ``resolve``:
   a would-be-confirm carried by a WITNESSED perishable transition CONFIRMS (lands in ``same_as``, NOT
   capped); its UNWITNESSED counterpart — the old and new values asserted by DIFFERENT sources — is still
   CAPPED to ``probable`` (lands in ``candidates`` with a perishable/transient ``candidate_reasons`` entry).
       → ``test_durable_support_true_for_witnessed_transition_false_for_unwitnessed``
       → ``test_witnessed_transition_confirms_while_unwitnessed_caps_to_probable``

Corpus-independent; real ``AttrClaim`` + real date value types; deterministic (fixed dates, no clock/RNG).
"""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.resolve.entities import AttrClaim, Entity
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.resolve.scoring import has_durable_identity_support, has_transition_witness
from chanakya.resolve.succession import classify_succession
from chanakya.schemas import (
    ClaimRecord,
    DocRef,
    EntityDescriptor,
    ExactDate,
    ResolvedRef,
    pair_key,
)
from tests.resolve._helpers import mk_config

# A perishable, identity-relevant attribute whose value legitimately changes over time. Deliberately NOT
# a namespace field (``namespace()`` reads country/operator_branch/service_branch/domain), so nothing we
# observe is the older namespace/blocking behaviour — only the trajectory/witness lever is in play.
ATTR = "status"
OLD, NEW = "active", "standby"  # two DISTINCT values ⇒ a genuine transition (not an agreement)


# ── builders (real value types; no parsing / clock / RNG) ─────────────────────────────────────────


def _exact(iso: str) -> ExactDate:
    return ExactDate(iso_date=iso)


def _ac(value: object, cid: str, *, source: str, iso: str | None = None) -> AttrClaim:
    """One asserted attribute value, stamped with the SOURCE that asserted it (+ an optional event time)."""
    return AttrClaim(value=value, claim_id=cid, event_time=_exact(iso) if iso else None, source_id=source)


def _gadget(eid: str, name: str, history: list[AttrClaim]) -> Entity:
    """A ``gadget`` stating ``ATTR`` via an ``AttrClaim`` series. ``attrs`` is the first-claim-wins scalar
    every resolve reader depends on; ``attr_history`` is the time-ordered, source-stamped series the
    succession core + the witness detector consume. An empty series ⇒ the attribute is absent."""
    attrs = {ATTR: history[0].value} if history else {}
    hist = {ATTR: list(history)} if history else {}
    return Entity(eid=eid, etype="gadget", name=name, attrs=attrs, attr_history=hist)


def _cfg(*, role: str = "supporting", perishable: bool = True) -> ResolveConfig:
    return ResolveConfig.from_bundle(
        mk_config(attribute_roles={"gadget": {ATTR: {"role": role, "perishable": perishable}}})
    )


def _combined_status(a: Entity, b: Entity, attr: str = ATTR) -> str:
    """Succession status of the two sides' COMBINED series — the temporal shape the witness keys on."""
    return classify_succession(a.attr_history.get(attr, []) + b.attr_history.get(attr, [])).status


def _witness_sources(a: Entity, b: Entity, attr: str = ATTR) -> set[str | None]:
    """The ``source_id``s that asserted ≥2 DISTINCT values across the two sides' combined series — i.e.
    the sources that (on their own) witnessed a value change. Empty ⇒ no single source saw old→new."""
    by_src: dict[str | None, set[object]] = {}
    for c in a.attr_history.get(attr, []) + b.attr_history.get(attr, []):
        by_src.setdefault(c.source_id, set()).add(c.value)
    return {s for s, vals in by_src.items() if len(vals) >= 2}


def _same_as(part: object) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.same_as}


def _candidates(part: object) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.candidates}


# ── (1) has_transition_witness ────────────────────────────────────────────────────────────────────


def test_transition_witness_true_for_single_source_ordered_succession() -> None:
    """(1) One source asserted an OLDER value and (later) a DIFFERENT newer value, forming a clean ordered
    succession across the two sides ⇒ that source WITNESSED the transition ⇒ True.
    """
    cfg = _cfg(role="supporting", perishable=True)
    a = _gadget("a", "Alpha", [_ac(OLD, "a1", source="src-W", iso="2019-01-01")])
    b = _gadget("b", "Beta", [_ac(NEW, "b1", source="src-W", iso="2023-01-01")])

    # fixture preconditions: identity-relevant + perishable attr; a genuine ordered succession; and ONE
    # source (src-W) is the single author of BOTH distinct values.
    assert ATTR in cfg.supporting_role_attrs("gadget")
    assert cfg.attribute_perishable("gadget", ATTR) is True
    assert _combined_status(a, b) == "ordered"
    assert _witness_sources(a, b) == {"src-W"}

    assert has_transition_witness(a, b, cfg) is True


def test_transition_witness_false_when_two_sources_split_the_transition() -> None:
    """(1) The old and new values are asserted by TWO DIFFERENT sources — no single source saw the change.

    The combined series is still a clean ORDERED succession (identical shape to the witnessed case); the
    ONLY difference is that no one source authored both values. So there is no witness ⇒ False.
    """
    cfg = _cfg(role="supporting", perishable=True)
    a = _gadget("a", "Alpha", [_ac(OLD, "a1", source="src-1", iso="2019-01-01")])
    b = _gadget("b", "Beta", [_ac(NEW, "b1", source="src-2", iso="2023-01-01")])

    # fixture preconditions: a genuine ordered succession, but the two values come from DIFFERENT sources.
    assert _combined_status(a, b) == "ordered"
    assert a.attr_history[ATTR][0].source_id != b.attr_history[ATTR][0].source_id
    assert _witness_sources(a, b) == set()  # NO single source asserted both values

    assert has_transition_witness(a, b, cfg) is False


def test_transition_witness_false_when_series_is_a_contradiction() -> None:
    """(1) A single source asserts two DIFFERENT values at the SAME time ⇒ a contradiction, not an ordered
    succession ⇒ False — even though the witness sub-condition (one source, ≥2 distinct values) is met.

    This isolates the ``ordered`` precondition: the value-witness clause alone would pass, so the False
    verdict must be the succession-shape gate doing its job.
    """
    cfg = _cfg(role="supporting", perishable=True)
    a = _gadget("a", "Alpha", [_ac(OLD, "a1", source="src-W", iso="2022-06-01")])
    b = _gadget("b", "Beta", [_ac(NEW, "b1", source="src-W", iso="2022-06-01")])  # same date ⇒ contradiction

    # fixture preconditions: NOT ordered (simultaneous distinct values), yet a single source did author both
    assert _combined_status(a, b) == "contradiction"
    assert _witness_sources(a, b) == {"src-W"}

    assert has_transition_witness(a, b, cfg) is False


def test_transition_witness_false_when_no_distinct_value_change() -> None:
    """(1) A source that asserted the SAME value twice never witnessed a change ⇒ no transition ⇒ False.

    Both sides state the identical value at distinct times: one distinct value ⇒ the succession is
    ``single`` (an agreement, not a succession), so there is nothing for a witness to have witnessed.
    """
    cfg = _cfg(role="supporting", perishable=True)
    a = _gadget("a", "Alpha", [_ac(OLD, "a1", source="src-W", iso="2019-01-01")])
    b = _gadget("b", "Beta", [_ac(OLD, "b1", source="src-W", iso="2023-01-01")])  # SAME value

    # fixture preconditions: one distinct value ⇒ not a succession, and no source saw ≥2 distinct values
    assert _combined_status(a, b) == "single"
    assert _witness_sources(a, b) == set()

    assert has_transition_witness(a, b, cfg) is False


def test_transition_witness_false_for_neutral_attribute() -> None:
    """(1) A NEUTRAL attribute is not identity-relevant ⇒ even a genuine single-source ordered transition
    on it is NOT a witness ⇒ False.
    """
    cfg = ResolveConfig.from_bundle(
        mk_config(attribute_roles={"gadget": {ATTR: {"role": "neutral", "perishable": True}}})
    )
    a = _gadget("a", "Alpha", [_ac(OLD, "a1", source="src-W", iso="2019-01-01")])
    b = _gadget("b", "Beta", [_ac(NEW, "b1", source="src-W", iso="2023-01-01")])

    # fixture preconditions: a real single-source ordered transition, but on a NON-identity-relevant attr
    assert _combined_status(a, b) == "ordered"
    assert _witness_sources(a, b) == {"src-W"}
    assert ATTR not in cfg.supporting_role_attrs("gadget")
    assert ATTR not in cfg.critical_role_attrs("gadget")

    assert has_transition_witness(a, b, cfg) is False


# ── (2) witness ⇒ durable support; and the downstream confirm-vs-cap via resolve ──────────────────


def test_durable_support_true_for_witnessed_transition_false_for_unwitnessed() -> None:
    """(2) The witness is a NEW durable-identity-support channel.

    A WITNESSED perishable ordered succession (one source authored old→new) is durable support — it can
    license a confirmed merge. Its UNWITNESSED counterpart (the identical succession, but with the two
    values split across two sources) is NOT durable — the 3B-iii-A behaviour, preserved. The two sub-cases
    differ ONLY in whether one source authored both values, so the witness is the sole cause of the flip.
    """
    cfg = _cfg(role="supporting", perishable=True)
    assert cfg.hard_id_fields("unique") == {}  # shared precondition: no other durable channel

    # WITNESSED — one source (src-W) authored both values ⇒ durable
    aw = _gadget("a", "Alpha", [_ac(OLD, "a1", source="src-W", iso="2019-01-01")])
    bw = _gadget("b", "Beta", [_ac(NEW, "b1", source="src-W", iso="2023-01-01")])
    assert _combined_status(aw, bw) == "ordered"
    assert _witness_sources(aw, bw) == {"src-W"}
    assert has_transition_witness(aw, bw, cfg) is True
    assert has_durable_identity_support(aw, bw, cfg) is True  # the witness makes the succession durable

    # UNWITNESSED — two sources, one value each ⇒ NOT durable (transient, 3B-iii-A behaviour)
    au = _gadget("a", "Alpha", [_ac(OLD, "a1", source="src-1", iso="2019-01-01")])
    bu = _gadget("b", "Beta", [_ac(NEW, "b1", source="src-2", iso="2023-01-01")])
    assert _combined_status(au, bu) == "ordered"
    assert _witness_sources(au, bu) == set()
    assert has_transition_witness(au, bu, cfg) is False
    assert has_durable_identity_support(au, bu, cfg) is False  # unwitnessed perishable succession is transient


def _claim(
    eid: str,
    *,
    name: str,
    source: str = "src-t",
    event_iso: str | None = None,
    **attrs: object,
) -> ClaimRecord:
    """An entity-form claim carrying a ``source_id`` AND an optional ``event_time`` (the ``entity()`` helper
    omits the latter), so ``build()`` stamps each attribute's ``AttrClaim`` with the asserting source and a
    real date — the two axes the succession core + witness detector need."""
    return ClaimRecord(
        claim_id=f"clm-{eid}",
        source_id=source,
        doc_ref=DocRef(file="d.txt", span=(0, 1)),
        kind="observation",
        asserts="entity",
        payload=EntityDescriptor(entity_type="gadget", name=name, attrs=dict(attrs)),
        event_time=_exact(event_iso) if event_iso else None,
        resolved_ref=ResolvedRef(entity_id=eid),
    )


def test_witnessed_transition_confirms_while_unwitnessed_caps_to_probable() -> None:
    """(2) The downstream behaviour, via ``resolve``.

    Two dissimilar-named gadgets ("Kilo Node" / "Zulu Node", sharing only the generic token "Node") whose
    ``status`` forms a perishable ORDERED succession (active@2019 → standby@2023). A low per-type
    auto-merge floor (0.35) sits ABOVE the name-only subtotal but BELOW the trajectory-boosted total, so the
    perishable succession is the SOLE lever carrying the pair to would-confirm. Three runs:

    * name-only (no ``status``) — proves NAME alone does not clear the bar (not in ``same_as``), so any
      merge is trajectory-driven, not name-driven.
    * WITNESSED (one source authors both values) — the succession is durable ⇒ the pair CONFIRMS
      (``same_as`` / ``confirmed``), NOT capped. This also PROVES the score reaches auto-confirm at this
      floor (else this assertion fails loudly).
    * UNWITNESSED (two sources, one value each) — IDENTICAL merge score, but the transition has no single
      witness ⇒ NOT durable ⇒ CAPPED to ``probable``: it lands in ``candidates`` (not ``same_as``) with a
      ``candidate_reasons`` entry naming the perishable/transient nature (the 3B-iii-A behaviour, preserved).

    The witnessed and unwitnessed runs differ ONLY in whether one source authored both values, so the
    witness — not a threshold quirk — is the sole cause of the confirm-vs-cap difference.
    """
    pair = frozenset({"g_a", "g_b"})
    key = pair_key("g_a", "g_b")
    name_a, name_b = "Kilo Node", "Zulu Node"  # share only the generic token "Node" ⇒ blockable, low sim
    floor = 0.35
    old_iso, new_iso = "2019-01-01", "2023-01-01"

    cfg = mk_config(
        attribute_roles={"gadget": {ATTR: {"role": "supporting", "perishable": True}}},
        auto_merge_by_type={"gadget": floor},
    )
    rc = ResolveConfig.from_bundle(cfg)

    def _run(src_old: str, src_new: str) -> object:
        return resolve(
            [
                _claim("g_a", name=name_a, source=src_old, event_iso=old_iso, **{ATTR: OLD}),
                _claim("g_b", name=name_b, source=src_new, event_iso=new_iso, **{ATTR: NEW}),
            ],
            cfg,
        )

    name_only = [_claim("g_a", name=name_a), _claim("g_b", name=name_b)]  # no status at all

    # fixture preconditions
    assert rc.attribute_perishable("gadget", ATTR) is True
    assert ATTR in rc.supporting_role_attrs("gadget")
    assert rc.auto_merge_for_pair("gadget", "gadget") == floor
    # the two status claims really form a clean, orderable, DISTINCT-value succession (as build() will stamp)
    witnessed_series = [
        AttrClaim(value=OLD, claim_id="s1", event_time=_exact(old_iso), source_id="src-W"),
        AttrClaim(value=NEW, claim_id="s2", event_time=_exact(new_iso), source_id="src-W"),
    ]
    assert classify_succession(witnessed_series).status == "ordered"
    assert OLD != NEW

    # GUARD — NAME alone does not clear the floor (so any merge below is trajectory-driven, not name-driven)
    assert pair not in _same_as(resolve(name_only, cfg))

    # WITNESSED — one source (src-W) authored BOTH values ⇒ durable ⇒ CONFIRMS (also proves floor reachable)
    part_w = _run("src-W", "src-W")
    assert pair in _same_as(part_w)
    assert part_w.identity_status("g_a", "g_b") == "confirmed"
    assert key not in part_w.candidate_reasons  # a durable confirm is not a capped candidate

    # UNWITNESSED — two sources, one value each ⇒ NOT durable ⇒ CAPPED to probable (identical score)
    part_u = _run("src-1", "src-2")
    assert pair not in _same_as(part_u)  # NOT merged, despite the identical merge score
    assert pair in _candidates(part_u)
    assert part_u.identity_status("g_a", "g_b") == "probable"
    assert key in part_u.candidate_reasons
    reason = part_u.candidate_reasons[key].lower()
    assert "perishable" in reason or "transient" in reason  # naming why it was capped
