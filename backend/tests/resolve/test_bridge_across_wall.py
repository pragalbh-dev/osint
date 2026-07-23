"""D9 — the "bridge across a wall" alarm, tested from the SPEC (independent test author).

A hard WALL is a curated ``distinct_from`` cannot-link, enforced transitively: two clusters a wall
holds apart may never be fused, even via a chain. A BRIDGE is a pair (a, b) that is *not itself*
directly walled but would, if merged, fuse two clusters a wall holds apart — and that scores as a
GENUINE would-be merge (strong enough that, absent the wall, it would auto-merge or reach the HITL
band). The alarm surfaces such a pair to the analyst (a ``probable`` candidate whose reason names the
crossed wall) but NEVER merges it; the wall holds. A merely *incidental* weak straddle is not alarmed
(the corroboration gate), and the whole behaviour is gated by config ``surface_wall_bridges`` (default
True; False ⇒ a silent non-merge).

These tests are corpus-independent: two same-type families, each internally fused by an in-document
EXPLICIT_EQUIVALENCE coreference (an identity signal orthogonal to the fuzzy scorer, so the families
are single clusters regardless of name), walled apart on their anchors, with a tunable straddling
pair — strong (a name auto-merge under a per-type floor) for the bridge cases, weak for the negative.
Deterministic: no clock, no RNG.
"""

from __future__ import annotations

from chanakya.resolve import resolve
from chanakya.schemas import pair_key
from tests.resolve._helpers import coref, entity, mk_config

T = "manufacturer"  # one type keeps blocking simple; a listed per-type auto-merge floor makes a
#                     near-identical name pair a genuine would-be MERGE (control proves it merges).


def _eid(name: str) -> str:
    # The id an entity claim lands on in production (entities.base_ref): a coref/triple endpoint given
    # the raw surface form resolves to ``ent:<type>:<form>``, so the coreference must point at this id.
    return f"ent:{T}:{name}"


def _ent(name: str, **attrs):
    return entity(_eid(name), T, name, **attrs)


# ── two families, walled apart on their anchors; strong straddling pair (X2 ≈ Y2) ────────────────
# X-anchor / Y-anchor carry the wall. X-bridge / Y-bridge are near-identical names (one distinguishing
# token) so, under a manufacturer auto-merge floor, they are a genuine would-be merge — yet each is
# fused into its own family by coreference, so merging them would cross the anchor wall.
X_ANCHOR = "Northwind Aerospace Bureau"
X_BRIDGE = "Meridian Systems Trading Company North"
Y_ANCHOR = "Southgate Defence Institute"
Y_BRIDGE = "Meridian Systems Trading Company South"


def _bridge_claims() -> list:
    return [
        _ent(X_ANCHOR), _ent(X_BRIDGE), _ent(Y_ANCHOR), _ent(Y_BRIDGE),
        # each family is one cluster via an in-document stated equivalence (distinct coref clusters so
        # the two families do NOT collapse into one). This is the orthogonal joiner: it fuses X_ANCHOR
        # with X_BRIDGE regardless of their dissimilar names, leaving name-similarity free to be the
        # cross-family bridge signal alone.
        coref(X_ANCHOR, X_BRIDGE, cluster="cx"),
        coref(Y_ANCHOR, Y_BRIDGE, cluster="cy"),
    ]


def _bridge_config(*, wall: bool = True, floor: bool = True, surface: bool | None = None):
    kw: dict = {"coref_authoritative_evidence": ["EXPLICIT_EQUIVALENCE"]}
    if wall:
        kw["distinct_from"] = {X_ANCHOR: [Y_ANCHOR]}  # the curated cannot-link between the anchors
    if floor:
        kw["auto_merge_by_type"] = {T: 0.37}  # lets the near-identical bridge names auto-merge
    cfg = mk_config(**kw)
    if surface is not None:
        cfg.resolution.surface_wall_bridges = surface  # ConfigModel allows extra fields (hot-config)
    return cfg


# ── cluster helpers (representation-independent) ─────────────────────────────────────────────────

def _root_fn(part):
    """Union-find over accepted merges + canonical mappings → each entity's cluster representative."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in part.same_as:
        union(a, b)
    for k, v in part.entity_canonical.items():
        union(k, v)
    return find


def _straddling_candidate(part, find, root_x: str, root_y: str):
    """The HITL candidate (if any) whose two endpoints sit in the two walled clusters — the bridge."""
    for a, b in part.candidates:
        if {find(a), find(b)} == {root_x, root_y}:
            return (a, b)
    return None


def _as_frozen(pairs) -> set:
    return {frozenset(p) for p in pairs}


# ── the alarm: a genuine bridge is surfaced (probable) and NEVER merged ──────────────────────────

def test_genuine_bridge_surfaced_as_probable_hitl_candidate_and_never_merged() -> None:
    """SPEC bullet 1: a genuine bridge appears in ``candidates`` with status ``probable`` and a reason
    naming the crossed wall; it is absent from ``same_as`` and the two clusters stay apart."""
    part = resolve(_bridge_claims(), _bridge_config())  # default config ⇒ surface_wall_bridges True
    find = _root_fn(part)
    rx, ry = find(_eid(X_ANCHOR)), find(_eid(Y_ANCHOR))

    # preconditions: each family is a single cluster and the wall holds them apart
    assert find(_eid(X_BRIDGE)) == rx, "family X did not fuse (coref joiner failed) — fixture precondition"
    assert find(_eid(Y_BRIDGE)) == ry, "family Y did not fuse (coref joiner failed) — fixture precondition"
    assert rx != ry, "the wall did not hold: the two clusters fused across a curated distinct_from"

    # the bridge is surfaced as a HITL candidate straddling the two walled clusters
    cand = _straddling_candidate(part, find, rx, ry)
    assert cand is not None, "genuine bridge was not surfaced as a HITL candidate"

    # ...as a PROBABLE identity link
    assert part.identity_status(*cand) == "probable"

    # ...and NEVER merged
    assert frozenset(cand) not in _as_frozen(part.same_as), "bridge was merged — the wall must forbid it"

    # ...with a non-empty reason that names it a bridge across a wall
    reason = part.candidate_reasons.get(pair_key(*cand), "")
    assert reason, "bridge candidate carries no analyst-facing reason"
    lower = reason.lower()
    assert "bridge" in lower and "wall" in lower, f"reason does not name a bridge-across-a-wall: {reason!r}"


def test_bridge_reason_names_the_crossed_wall() -> None:
    """SPEC bullet 1 (reason quality): the rationale identifies the specific wall being crossed —
    it references the walled anchor entities, not just a generic 'bridge' label."""
    part = resolve(_bridge_claims(), _bridge_config())
    find = _root_fn(part)
    cand = _straddling_candidate(part, find, find(_eid(X_ANCHOR)), find(_eid(Y_ANCHOR)))
    assert cand is not None
    reason = part.candidate_reasons[pair_key(*cand)]
    # the reason names BOTH walled anchors (the crossed wall), so an analyst sees which cannot-link fired
    assert X_ANCHOR in reason and Y_ANCHOR in reason, f"reason does not name the crossed wall: {reason!r}"


# ── control: no wall ⇒ that same strong pair DOES merge (it is a real would-be merge) ────────────

def test_control_no_wall_the_same_strong_pair_merges() -> None:
    """SPEC control: identical claims with the wall REMOVED ⇒ the straddling pair merges — proving the
    bridge case is a real would-be merge that only the wall stops."""
    part = resolve(_bridge_claims(), _bridge_config(wall=False))
    find = _root_fn(part)
    # with no wall the whole thing collapses to one cluster; the bridge endpoints share a representative
    assert find(_eid(X_BRIDGE)) == find(_eid(Y_BRIDGE)), "the strong straddling pair did not merge without a wall"
    # sanity: without a wall there is nothing to alarm
    assert part.candidate_reasons == {}
    assert part.distinct_from == []


# ── a directly-walled pair is a WALL, not a bridge ───────────────────────────────────────────────

def test_directly_walled_pair_is_a_wall_not_a_bridge() -> None:
    """SPEC bullet 3: the ``distinct_from`` pair itself — even one that would otherwise auto-merge — is
    drawn in ``distinct_from`` (a hard veto) and is NEITHER a bridge candidate NOR given a bridge reason."""
    a, b = "Vanguard Precision Systems North", "Vanguard Precision Systems South"  # near-identical ⇒ would merge
    part = resolve(
        [_ent(a), _ent(b)],
        mk_config(distinct_from={a: [b]}, auto_merge_by_type={T: 0.37}),
    )
    key = pair_key(_eid(a), _eid(b))
    assert frozenset((_eid(a), _eid(b))) in _as_frozen(part.distinct_from), "the wall pair is not drawn as distinct_from"
    assert frozenset((_eid(a), _eid(b))) not in _as_frozen(part.candidates), "a directly-walled pair became a candidate"
    assert frozenset((_eid(a), _eid(b))) not in _as_frozen(part.same_as), "a walled pair was merged"
    assert "bridge" not in part.candidate_reasons.get(key, "").lower(), "the wall pair was given a bridge reason"
    assert part.identity_status(_eid(a), _eid(b)) is None, "a walled pair carries no confirmed/probable/possible link"


# ── the corroboration gate: an incidental weak straddle is NOT alarmed ───────────────────────────

# Two families walled apart, with a straddling pair that shares only one token (Zenith …): it is
# compared and scored, so it genuinely *touches* across the wall, but scores well below the HITL band —
# it is not a would-be merge. No per-type floor here, so nothing auto-merges.
WX_ANCHOR, WX_BRIDGE = "Falcon Aerospace Bureau", "Zenith Alpha Holdings"
WY_ANCHOR, WY_BRIDGE = "Osprey Defence Institute", "Zenith Omega Ventures"


def test_incidental_low_score_straddle_is_not_surfaced_as_a_bridge() -> None:
    """SPEC bullet 4: a pair that only weakly touches across the wall (not a would-be merge) is retained
    as a watch-list ``possible`` link but is NOT raised as a bridge candidate and carries no bridge reason."""
    claims = [
        _ent(WX_ANCHOR), _ent(WX_BRIDGE), _ent(WY_ANCHOR), _ent(WY_BRIDGE),
        coref(WX_ANCHOR, WX_BRIDGE, cluster="wcx"),
        coref(WY_ANCHOR, WY_BRIDGE, cluster="wcy"),
    ]
    part = resolve(
        claims,
        mk_config(
            coref_authoritative_evidence=["EXPLICIT_EQUIVALENCE"],
            distinct_from={WX_ANCHOR: [WY_ANCHOR]},
            possible_floor=0.05,  # retain a weak link so we can prove it "touched" (yet is not alarmed)
        ),
    )
    find = _root_fn(part)
    rx, ry = find(_eid(WX_ANCHOR)), find(_eid(WY_ANCHOR))
    # preconditions: families fused, walled apart, and the weak pair genuinely straddles
    assert find(_eid(WX_BRIDGE)) == rx and find(_eid(WY_BRIDGE)) == ry
    assert rx != ry

    straddle = frozenset((_eid(WX_BRIDGE), _eid(WY_BRIDGE)))
    # it weakly touched across the wall — retained on the watch-list, NOT dropped silently
    assert straddle in _as_frozen(part.possible), "the weak straddle was not scored/retained — fixture precondition"
    # the corroboration gate: NOT raised as a bridge candidate, no bridge reason, not merged
    assert _straddling_candidate(part, find, rx, ry) is None, "an incidental weak straddle was alarmed as a bridge"
    assert straddle not in _as_frozen(part.candidates)
    assert straddle not in _as_frozen(part.same_as)
    assert "bridge" not in part.candidate_reasons.get(pair_key(_eid(WX_BRIDGE), _eid(WY_BRIDGE)), "").lower()


# ── the config dial: surface_wall_bridges ────────────────────────────────────────────────────────

def test_surface_wall_bridges_false_suppresses_the_candidate_but_still_never_merges() -> None:
    """SPEC bullet 5: with ``surface_wall_bridges`` False the genuine bridge is a SILENT non-merge — not
    raised as a candidate and given no reason, yet still never merged and the clusters stay apart."""
    part = resolve(_bridge_claims(), _bridge_config(surface=False))
    find = _root_fn(part)
    rx, ry = find(_eid(X_ANCHOR)), find(_eid(Y_ANCHOR))

    # not surfaced
    assert _straddling_candidate(part, find, rx, ry) is None, "bridge surfaced despite surface_wall_bridges=False"
    assert part.candidate_reasons == {}, "a bridge reason was emitted despite surface_wall_bridges=False"
    # still never merged, clusters still apart, wall still drawn
    assert rx != ry, "the wall must still hold when bridges are not surfaced"
    assert frozenset((_eid(X_BRIDGE), _eid(Y_BRIDGE))) not in _as_frozen(part.same_as), "silenced bridge was merged"
    assert frozenset((_eid(X_ANCHOR), _eid(Y_ANCHOR))) in _as_frozen(part.distinct_from)


def test_surface_wall_bridges_defaults_to_true() -> None:
    """SPEC bullet 5 (default): the default (field unset) surfaces the bridge, identically to explicit True."""
    part_default = resolve(_bridge_claims(), _bridge_config())            # unset ⇒ default
    part_true = resolve(_bridge_claims(), _bridge_config(surface=True))   # explicit True

    for part in (part_default, part_true):
        find = _root_fn(part)
        cand = _straddling_candidate(part, find, find(_eid(X_ANCHOR)), find(_eid(Y_ANCHOR)))
        assert cand is not None, "default/True did not surface the bridge candidate"
        assert part.identity_status(*cand) == "probable"
        assert "bridge" in part.candidate_reasons.get(pair_key(*cand), "").lower()
