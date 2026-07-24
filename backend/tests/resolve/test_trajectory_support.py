"""Stage 3B-iii-A — trajectory-aware attribute SUPPORT + perishable-only confirmation cap.

Written **purely against the published contract**, blind to the implementation: ``resolve/scoring.py``
and ``resolve/cluster.py`` are deliberately NOT read (only ``attribute_score`` and
``has_durable_identity_support`` are *imported* from ``scoring``). These tests assert what *correct*
behaviour IS, not what any observed output happens to be. Every fixture asserts its own precondition
(this really is an ordered succession / an agreement / a would-confirm pair) so a mis-built fixture
cannot pass silently.

Contract under test (three bullets):

1. **Agreement raises identity similarity.** Two same-type entities that AGREE (equal value) on a
   declared critical/supporting attribute score HIGHER on ``attribute_score`` than two that don't state
   it — and higher than a disagreeing pair. A PERISHABLE attribute whose two sides form a clean ORDERED
   succession (different values at distinct times) counts as AGREEMENT/consistency for this (raises the
   score like an agreement), NOT as a disagreement.
       → ``test_agreement_beats_no_mention_beats_disagreement``
       → ``test_perishable_ordered_succession_scores_like_agreement``

2. **``has_durable_identity_support(a, b, cfg)``** is True when the pair shares a unique/hard id OR
   agrees (equal) on ≥1 NON-perishable identity-relevant (critical/supporting) attribute; False when the
   only agreement/consistency is on PERISHABLE attributes (or there is none at all).
       → ``test_durable_support_true_for_shared_hard_id``
       → ``test_durable_support_true_for_nonperishable_agreement``
       → ``test_durable_support_false_for_perishable_only_agreement``
       → ``test_durable_support_false_for_perishable_ordered_succession``
       → ``test_durable_support_false_without_durable_agreement``

3. **Perishable-only confirmation cap** (via ``resolve``): a pair carried to would-be-``confirm`` SOLELY
   by a perishable trajectory (a perishable ordered succession / perishable agreement, with no durable
   evidence) is CAPPED to ``probable`` — it lands in ``candidates`` (not ``same_as``),
   ``identity_status == "probable"``, with a ``candidate_reasons`` entry mentioning perishable/transient.
   A pair with DURABLE support still ``confirm``s (merges) as normal — where durable support includes a
   shared id, a non-perishable attribute agreement, OR a sufficiently similar NAME (a name-driven merge is
   NOT capped, per the coordinator refinement). So the cap fires only when the name is dissimilar enough
   that name alone would not reach the auto-confirm bar and the perishable bonus is the sole lever.
       → ``test_perishable_only_would_confirm_caps_to_probable``
       → ``test_name_bootstrap_still_confirms_not_capped``

Corpus-independent; real ``AttrClaim`` + real date value types; deterministic (fixed dates, no clock/RNG).
"""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.resolve.entities import AttrClaim, Entity
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.resolve.scoring import attribute_score, has_durable_identity_support
from chanakya.resolve.succession import classify_succession
from chanakya.schemas import ExactDate, pair_key
from tests.resolve._helpers import entity, mk_config

# ── builders (real value types; no parsing / clock / RNG) ─────────────────────────────────────────


def _exact(iso: str) -> ExactDate:
    return ExactDate(iso_date=iso)


def _ac(value: object, cid: str, iso: str | None = None) -> AttrClaim:
    """One asserted attribute value, optionally anchored in time (``event_time``)."""
    return AttrClaim(value=value, claim_id=cid, event_time=_exact(iso) if iso else None)


def _gadget(
    eid: str,
    name: str,
    *,
    attrs: dict[str, object] | None = None,
    history: dict[str, list[AttrClaim]] | None = None,
) -> Entity:
    """A ``gadget`` entity. ``attrs`` is the first-claim-wins scalar view every resolve reader depends on;
    ``history`` is the role-agnostic time-ordered series the succession core consumes."""
    return Entity(
        eid=eid,
        etype="gadget",
        name=name,
        attrs=dict(attrs or {}),
        attr_history={k: list(v) for k, v in (history or {}).items()},
    )


def _cfg(**kw: object) -> ResolveConfig:
    return ResolveConfig.from_bundle(mk_config(**kw))


def _combined_status(a: Entity, b: Entity, attr: str) -> str:
    """Succession status of the two sides' combined series — the temporal shape the exception keys on."""
    return classify_succession(a.attr_history.get(attr, []) + b.attr_history.get(attr, [])).status


def _same_as(part: object) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.same_as}


def _candidates(part: object) -> set[frozenset[str]]:
    return {frozenset(p) for p in part.candidates}


# ── (1) agreement raises identity similarity ──────────────────────────────────────────────────────


def test_agreement_beats_no_mention_beats_disagreement() -> None:
    """(1) A declared SUPPORTING attribute: AGREEMENT > NO-MENTION > DISAGREEMENT on ``attribute_score``.

    Names are held identical across the three pairs ("Ranger Alpha" / "Ranger Bravo", a shared-token but
    NON-identical pair so there is headroom above the name-only baseline) — the ONLY thing that varies is
    the attribute state, so any difference in the score is attributable to it. Agreement raises the score
    above the pair that states nothing; a stated (non-perishable) disagreement is a soft penalty that
    lowers it below that baseline.
    """
    cfg = _cfg(
        attribute_roles={"gadget": {"config": {"role": "supporting", "perishable": False}}},
        attribute_scoring={"conflict_penalty": 0.5},
    )
    a_agree = _gadget("a", "Ranger Alpha", attrs={"config": "cfg-X"})
    b_agree = _gadget("b", "Ranger Bravo", attrs={"config": "cfg-X"})
    a_none = _gadget("a", "Ranger Alpha")
    b_none = _gadget("b", "Ranger Bravo")
    a_dis = _gadget("a", "Ranger Alpha", attrs={"config": "cfg-X"})
    b_dis = _gadget("b", "Ranger Bravo", attrs={"config": "cfg-Y"})

    # fixture preconditions: really agree / really silent / really disagree, on a declared supporting attr
    assert a_agree.attrs["config"] == b_agree.attrs["config"]
    assert "config" not in a_none.attrs and "config" not in b_none.attrs
    assert a_dis.attrs["config"] != b_dis.attrs["config"]
    assert cfg.supporting_role_attrs("gadget") == ["config"]

    s_agree = attribute_score(a_agree, b_agree, cfg)
    s_none = attribute_score(a_none, b_none, cfg)
    s_dis = attribute_score(a_dis, b_dis, cfg)

    assert s_agree > s_none  # agreement RAISES the similarity above stating nothing
    assert s_none > s_dis  # a stated disagreement is a soft penalty below the no-mention baseline
    assert s_agree > s_dis  # ...so agreement is strictly the strongest of the three


def test_perishable_ordered_succession_scores_like_agreement() -> None:
    """(1) A PERISHABLE attribute whose two sides form a clean ORDERED succession scores like AGREEMENT.

    Same held-constant names as above. Four states of the same declared supporting+perishable attribute:
    agreement (equal value), no-mention, an ordered succession (different values at DISTINCT times), and a
    contradiction (different values at the SAME time). The ordered succession is a benign update, so it
    raises the score exactly like an agreement — above no-mention, above the contradiction — and is NOT
    counted as negative evidence.
    """
    cfg = _cfg(
        attribute_roles={"gadget": {"config": {"role": "supporting", "perishable": True}}},
        attribute_scoring={"conflict_penalty": 0.5},
    )
    a_agree = _gadget("a", "Ranger Alpha", attrs={"config": "cfg-A"},
                      history={"config": [_ac("cfg-A", "g1", "2019-01-01")]})
    b_agree = _gadget("b", "Ranger Bravo", attrs={"config": "cfg-A"},
                      history={"config": [_ac("cfg-A", "g2", "2023-01-01")]})
    a_none = _gadget("a", "Ranger Alpha")
    b_none = _gadget("b", "Ranger Bravo")
    a_ord = _gadget("a", "Ranger Alpha", attrs={"config": "cfg-A"},
                    history={"config": [_ac("cfg-A", "o1", "2019-01-01")]})
    b_ord = _gadget("b", "Ranger Bravo", attrs={"config": "cfg-B"},
                    history={"config": [_ac("cfg-B", "o2", "2023-01-01")]})
    a_contra = _gadget("a", "Ranger Alpha", attrs={"config": "cfg-A"},
                       history={"config": [_ac("cfg-A", "c1", "2022-06-01")]})
    b_contra = _gadget("b", "Ranger Bravo", attrs={"config": "cfg-B"},
                       history={"config": [_ac("cfg-B", "c2", "2022-06-01")]})  # same date ⇒ contradiction

    # fixture preconditions: the temporal shapes are exactly what the exception keys on
    assert cfg.attribute_perishable("gadget", "config") is True
    assert cfg.supporting_role_attrs("gadget") == ["config"]
    assert _combined_status(a_agree, b_agree, "config") == "single"  # one distinct value ⇒ agreement
    assert _combined_status(a_ord, b_ord, "config") == "ordered"  # a clean succession
    assert _combined_status(a_contra, b_contra, "config") == "contradiction"  # simultaneous distinct

    s_agree = attribute_score(a_agree, b_agree, cfg)
    s_none = attribute_score(a_none, b_none, cfg)
    s_ord = attribute_score(a_ord, b_ord, cfg)
    s_contra = attribute_score(a_contra, b_contra, cfg)

    assert s_agree > s_none  # (baseline) agreement raises the score
    assert s_none > s_contra  # (baseline) a real (contradiction) conflict is penalised below no-mention
    assert s_ord > s_none  # the ordered succession RAISES the score, like an agreement
    assert s_ord > s_contra  # ...and is NOT penalised like the genuine conflict
    assert s_ord == s_agree  # it is counted AS agreement/consistency, not merely un-penalised


# ── (2) has_durable_identity_support ────────────────────────────────────────────────────────────


def test_durable_support_true_for_shared_hard_id() -> None:
    """(2) A shared unique/hard id is durable identity support — True, even with dissimilar names."""
    cfg = _cfg(hard_id_fields={"unique": {"gadget": ["serial"]}})
    a = _gadget("a", "Alpha", attrs={"serial": "SN-1"})
    b = _gadget("b", "Beta", attrs={"serial": "SN-1"})

    # fixture preconditions
    assert cfg.hard_id_fields("unique") == {"gadget": ["serial"]}
    assert a.attrs["serial"] == b.attrs["serial"]  # the hard id genuinely matches

    assert has_durable_identity_support(a, b, cfg) is True


def test_durable_support_true_for_nonperishable_agreement() -> None:
    """(2) Agreement on ≥1 NON-perishable identity-relevant attribute is durable support — True."""
    cfg = _cfg(attribute_roles={"gadget": {"designator": {"role": "supporting", "perishable": False}}})
    a = _gadget("a", "Alpha", attrs={"designator": "X-1"})
    b = _gadget("b", "Beta", attrs={"designator": "X-1"})

    # fixture preconditions: an identity-relevant, explicitly NON-perishable attribute they truly agree on,
    # and NOT via a hard id (isolates the non-perishable-agreement path)
    assert "designator" in cfg.supporting_role_attrs("gadget")
    assert cfg.attribute_perishable("gadget", "designator") is False
    assert a.attrs["designator"] == b.attrs["designator"]
    assert cfg.hard_id_fields("unique") == {}

    assert has_durable_identity_support(a, b, cfg) is True


def test_durable_support_false_for_perishable_only_agreement() -> None:
    """(2) Agreement ONLY on a PERISHABLE attribute (no hard id, no durable agreement) is NOT durable — False."""
    cfg = _cfg(attribute_roles={"gadget": {"status": {"role": "supporting", "perishable": True}}})
    a = _gadget("a", "Alpha", attrs={"status": "active"})
    b = _gadget("b", "Beta", attrs={"status": "active"})

    # fixture preconditions: they DO agree, but the attribute is perishable and there is no durable channel
    assert cfg.attribute_perishable("gadget", "status") is True
    assert a.attrs["status"] == b.attrs["status"]
    assert cfg.hard_id_fields("unique") == {}

    assert has_durable_identity_support(a, b, cfg) is False


def test_durable_support_false_for_perishable_ordered_succession() -> None:
    """(2) A PERISHABLE ordered succession is temporal consistency, not durable support — False.

    A clean update over time keeps identity *plausible* (it does not disagree), but it is transient
    evidence: it cannot, on its own, license a confirmed merge. So the durable-support gate is False.
    """
    cfg = _cfg(attribute_roles={"gadget": {"status": {"role": "supporting", "perishable": True}}})
    a = _gadget("a", "Alpha", attrs={"status": "active"},
                history={"status": [_ac("active", "s1", "2019-01-01")]})
    b = _gadget("b", "Beta", attrs={"status": "standby"},
                history={"status": [_ac("standby", "s2", "2023-01-01")]})

    # fixture preconditions: this really is a perishable ORDERED succession (not an agreement, not a wall)
    assert cfg.attribute_perishable("gadget", "status") is True
    assert _combined_status(a, b, "status") == "ordered"
    assert cfg.hard_id_fields("unique") == {}

    assert has_durable_identity_support(a, b, cfg) is False


def test_durable_support_false_without_durable_agreement() -> None:
    """(2) No durable channel at all ⇒ False: disjoint attrs, a durable DISAGREEMENT, and a NEUTRAL agreement.

    Three sub-cases the durable gate must reject: (a) the pair shares nothing; (b) they both state a
    durable identity attribute but with DIFFERENT values (presence is not agreement); (c) they agree only
    on a NEUTRAL attribute, which carries no identity bearing (not identity-relevant).
    """
    cfg = _cfg(attribute_roles={
        "gadget": {
            "designator": {"role": "supporting", "perishable": False},
            "colour": {"role": "neutral"},
        }
    })
    assert cfg.hard_id_fields("unique") == {}  # shared precondition: no hard-id channel

    # (a) nothing shared (both attrs undeclared ⇒ neutral, and disjoint anyway)
    a1 = _gadget("a", "Alpha", attrs={"nickname": "foo"})
    b1 = _gadget("b", "Beta", attrs={"tag": "bar"})
    assert has_durable_identity_support(a1, b1, cfg) is False

    # (b) a durable attribute is present on both sides but DISAGREES ⇒ not an agreement
    a2 = _gadget("a", "Alpha", attrs={"designator": "X-1"})
    b2 = _gadget("b", "Beta", attrs={"designator": "X-2"})
    assert a2.attrs["designator"] != b2.attrs["designator"]  # precondition: genuine disagreement
    assert has_durable_identity_support(a2, b2, cfg) is False

    # (c) they agree, but only on a NEUTRAL attribute ⇒ not identity-relevant
    a3 = _gadget("a", "Alpha", attrs={"colour": "red"})
    b3 = _gadget("b", "Beta", attrs={"colour": "red"})
    assert a3.attrs["colour"] == b3.attrs["colour"]  # precondition: they do agree on colour
    assert "colour" not in cfg.supporting_role_attrs("gadget")
    assert "colour" not in cfg.critical_role_attrs("gadget")  # colour bears no identity role
    assert has_durable_identity_support(a3, b3, cfg) is False


# ── (3) perishable-only confirmation cap (via resolve) ───────────────────────────────────────────


def test_perishable_only_would_confirm_caps_to_probable() -> None:
    """(3) A would-confirm pair carried SOLELY by a perishable agreement is CAPPED to ``probable``.

    The pair agrees on a perishable ``status`` and shares only a generic name token ("Kilo Node" /
    "Zulu Node") — DISSIMILAR enough that name alone does not reach the auto-confirm bar, so the perishable
    bonus is the sole lever (a fuzzy-name-driven merge is durable and would NOT cap — the coordinator
    refinement). A low per-type auto-merge floor (0.35) sits ABOVE the name-only subtotal but BELOW the
    perishable-boosted total. Three runs:

    * name-only (no ``status``) — proves NAME alone does not clear the bar (not in ``same_as``), so the
      merge is genuinely perishable-driven, not name-driven; this is the guard against the earlier fixture
      flaw where near-identical names carried the merge themselves.
    * ``perishable: False`` — the same agreement is now DURABLE, so the pair CONFIRMS (``same_as``). This
      PROVES the pair genuinely reaches auto-confirm at this floor — the cap has nothing to intercept unless
      a confirm would happen.
    * ``perishable: True`` — identical merge score, but the sole lever is perishable, so the pair caps to
      ``probable``: it lands in ``candidates`` (not ``same_as``) with a ``candidate_reasons`` entry naming
      the perishable/transient nature.

    The perishable and durable runs differ only in the ``perishable`` flag, so the cap — not a threshold
    quirk — is the sole cause of the difference, and a cap that never fired would fail loudly.
    """
    pair = frozenset({"g_a", "g_b"})
    key = pair_key("g_a", "g_b")
    name_a, name_b = "Kilo Node", "Zulu Node"  # share only the generic token "Node" ⇒ blockable but low sim
    floor = 0.35
    claims = [
        entity("g_a", "gadget", name_a, status="active"),
        entity("g_b", "gadget", name_b, status="active"),  # same status value, dissimilar name
    ]
    name_only_claims = [entity("g_a", "gadget", name_a), entity("g_b", "gadget", name_b)]  # no status

    cfg_durable = mk_config(
        attribute_roles={"gadget": {"status": {"role": "supporting", "perishable": False}}},
        auto_merge_by_type={"gadget": floor},
    )
    cfg_perishable = mk_config(
        attribute_roles={"gadget": {"status": {"role": "supporting", "perishable": True}}},
        auto_merge_by_type={"gadget": floor},
    )

    # fixture preconditions: the two configs differ ONLY in perishability, on the same per-type auto floor
    rc_d, rc_p = ResolveConfig.from_bundle(cfg_durable), ResolveConfig.from_bundle(cfg_perishable)
    assert rc_d.attribute_perishable("gadget", "status") is False
    assert rc_p.attribute_perishable("gadget", "status") is True
    assert rc_p.auto_merge_for_pair("gadget", "gadget") == floor
    assert claims[0].payload.attrs["status"] == claims[1].payload.attrs["status"]  # they truly agree

    # GUARD — NAME alone does not clear the auto-confirm bar (so the merge is perishable-driven, not
    # name-driven). This is exactly what a near-identical-name fixture would fail: name would carry it.
    part_name_only = resolve(name_only_claims, cfg_perishable)
    assert pair not in _same_as(part_name_only)  # dissimilar names ⇒ name is NOT the lever

    # DURABLE run — proves the pair reaches auto-confirm at this floor (else this assertion fails loudly)
    part_durable = resolve(claims, cfg_durable)
    assert pair in _same_as(part_durable)  # a durable agreement confirms as normal
    assert key not in part_durable.candidate_reasons  # ...and is not a raised/capped candidate

    # PERISHABLE run — identical score, but the sole lever is perishable ⇒ capped to probable
    part_perishable = resolve(claims, cfg_perishable)
    assert pair not in _same_as(part_perishable)  # NOT merged
    assert pair in _candidates(part_perishable)  # ...held as a probable candidate
    assert part_perishable.identity_status("g_a", "g_b") == "probable"
    assert key in part_perishable.candidate_reasons  # with an analyst-facing reason
    reason = part_perishable.candidate_reasons[key].lower()
    assert "perishable" in reason or "transient" in reason  # naming why it was capped


def test_name_bootstrap_still_confirms_not_capped() -> None:
    """(3) A name/alias BOOTSTRAP is durable support — a perishable-only pair that bootstraps still confirms.

    Two gadgets with the IDENTICAL name ("Falcon Prime") whose only stated attribute is a perishable
    ``status`` agreement. The exact-name bootstrap is durable identity support, so the perishable-only cap
    does NOT fire: the pair merges (``same_as`` / ``confirmed``) and carries no capped-candidate reason.
    """
    pair = frozenset({"g_a", "g_b"})
    key = pair_key("g_a", "g_b")
    claims = [
        entity("g_a", "gadget", "Falcon Prime", status="active"),
        entity("g_b", "gadget", "Falcon Prime", status="active"),  # identical name ⇒ bootstrap
    ]
    cfg = mk_config(attribute_roles={"gadget": {"status": {"role": "supporting", "perishable": True}}})

    # fixture preconditions: identical names (the bootstrap), and the only attribute is perishable
    assert claims[0].payload.name == claims[1].payload.name
    assert ResolveConfig.from_bundle(cfg).attribute_perishable("gadget", "status") is True

    part = resolve(claims, cfg)
    assert pair in _same_as(part)  # the name bootstrap merges despite perishable-only attribute support
    assert part.identity_status("g_a", "g_b") == "confirmed"
    assert key not in part.candidate_reasons  # a bootstrap is durable ⇒ the cap does not fire
