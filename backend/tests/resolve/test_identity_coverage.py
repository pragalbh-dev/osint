"""Contract tests for Stage 4 — the identity-resolution COVERAGE output (D11).

Independent, corpus-independent, deterministic. We CONSTRUCT :class:`Partition` objects directly with
chosen ``same_as`` / ``candidates`` / ``possible`` pairs (confirmed / probable / possible identity links)
plus a ``type_of`` map, and assert the pure coverage summary against the frozen contract:

    identity_coverage(partition, type_of, cfg) -> IdentityCoverage
      * overall confirmed / probable / possible  (from same_as / candidates / possible)
      * by_type: per entity-type -> {confirmed, probable, possible}  (by the linked entities' type)
      * collection_gaps: types where (probable + possible) / max(confirmed, 1) >= coverage_gap_ratio,
        deterministically ordered
      * policy: the policy-dial values echoed for transparency (incl. coverage_gap_ratio)

The policy dial is driven through config: ``coverage_gap_ratio`` is read off the resolution surface, so
these tests set it via the shared ``mk_config`` bundle (the contract's "for the dial" path) and build the
stage's ``ResolveConfig`` with ``ResolveConfig.from_bundle``. When it is left unset the ratio echoes back
``None`` and gap detection is inert (fails closed) — a behaviour asserted directly below.

The implementation body is NOT read here — only the module's published symbols and the *public* return
shape are used. The resolver itself is never run; every fixture is hand-built.
"""

from __future__ import annotations

import pytest

from chanakya.view.coverage import IdentityCoverage, identity_coverage
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.schemas import Partition, ResolutionConfig
from tests.resolve._helpers import mk_config


# ── type_of: matches the resolve TypeOf convention (Callable[[str], str | None]) AND a plain map ──
class TypeMap(dict):
    """A ``type_of`` that is simultaneously a mapping and a ``Callable[[str], str | None]``.

    The resolve stages type ``type_of`` as a callable (``chanakya.edge_direction.TypeOf``); other code
    treats it as a dict. Subclassing ``dict`` and adding ``__call__`` makes the fixture correct whether
    the impl calls ``type_of(x)``, ``type_of.get(x)`` or ``type_of[x]`` — no assumption smuggled in.
    """

    def __call__(self, key: str) -> str | None:
        return self.get(key)


# ── fixture builders ───────────────────────────────────────────────────────────────────────────
def _build(*, same=None, cand=None, poss=None, orphan_types=()):
    """Build a (Partition, TypeMap) from per-type link counts, one type per pair.

    ``same``/``cand``/``poss`` map an entity-type name -> number of identity links of that tier. Each
    link gets two freshly-minted, tier-unique ids that both carry the link's type, so a link buckets
    unambiguously into exactly one type. ``orphan_types`` seed the type map with entities that appear in
    NO link (a type "with none").
    """
    same, cand, poss = same or {}, cand or {}, poss or {}
    tmap = TypeMap()

    def links(counts: dict[str, int], tag: str) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        for t, n in counts.items():
            for i in range(n):
                a, b = f"{t}:{tag}:{i}:a", f"{t}:{tag}:{i}:b"
                tmap[a] = t
                tmap[b] = t
                out.append((a, b))
        return out

    part = Partition(
        same_as=links(same, "sa"),
        candidates=links(cand, "ca"),
        possible=links(poss, "po"),
    )
    for t in orphan_types:
        tmap[f"{t}:orphan"] = t
    return part, tmap


def _rcfg(ratio: float | None = None) -> ResolveConfig:
    """The stage config the contract passes as ``cfg``, with the policy dial driven through config.

    ``coverage_gap_ratio`` rides the resolution surface (``ResolutionConfig`` is ``extra='allow'``), so we
    set it on the ``mk_config`` bundle and let ``ResolveConfig.from_bundle`` carry it into the policy.
    ``ratio=None`` leaves it unset (the dial echoes ``None`` and gaps are inert).
    """
    bundle = mk_config()
    if ratio is not None:
        res = bundle.resolution.model_dump()
        res["coverage_gap_ratio"] = ratio
        bundle.resolution = ResolutionConfig(**res)
    return ResolveConfig.from_bundle(bundle)


def _cov(part, type_of, *, ratio: float | None = None):
    return identity_coverage(part, type_of, _rcfg(ratio))


# ── result accessors (assert the contract shape; a missing type reads as all-zero) ───────────────
def _overall(result) -> tuple[int, int, int]:
    conf, prob, poss = result.confirmed, result.probable, result.possible
    for v in (conf, prob, poss):
        assert isinstance(v, int) and not isinstance(v, bool), f"overall count not an int: {v!r}"
    return conf, prob, poss


def _counts(result, tname: str) -> tuple[int, int, int]:
    """(confirmed, probable, possible) for one ``by_type`` bucket; a type with no links reads as zero."""
    bucket = result.by_type.get(tname)
    if bucket is None:
        return (0, 0, 0)
    return (bucket.confirmed, bucket.probable, bucket.possible)


def _gaps(result) -> list[str]:
    g = result.collection_gaps
    assert isinstance(g, list), f"collection_gaps must be an ordered list, got {type(g)!r}"
    return list(g)


def _ratio(result) -> float | None:
    return result.policy.coverage_gap_ratio


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# 1. Overall counts == the source list lengths.
def test_overall_counts_match_list_lengths():
    part, tmap = _build(same={"unit": 3}, cand={"unit": 2}, poss={"unit": 4})
    # precondition: the fixture is what we think it is
    assert (len(part.same_as), len(part.candidates), len(part.possible)) == (3, 2, 4)

    result = _cov(part, tmap)

    assert isinstance(result, IdentityCoverage)
    assert _overall(result) == (3, 2, 4)
    # anchored to the exact source lists (the contract's wording)
    assert result.confirmed == len(part.same_as)
    assert result.probable == len(part.candidates)
    assert result.possible == len(part.possible)


# 2. by_type buckets links by the linked entities' type — incl. only-possible, healthy, and none.
def test_by_type_buckets_links_by_entity_type():
    part, tmap = _build(
        same={"unit": 3},                     # unit: healthy confirmed base
        cand={"unit": 1, "component": 1},
        poss={"unit": 1, "sensor": 2, "component": 2},
        orphan_types=("variant",),            # a type present in type_of but in NO link
    )
    # preconditions: the tiers landed where intended, and identity_status agrees with the tier
    assert (len(part.same_as), len(part.candidates), len(part.possible)) == (3, 2, 5)
    assert part.identity_status("unit:sa:0:a", "unit:sa:0:b") == "confirmed"
    assert part.identity_status("component:ca:0:a", "component:ca:0:b") == "probable"
    assert part.identity_status("sensor:po:0:a", "sensor:po:0:b") == "possible"

    result = _cov(part, tmap)

    # a healthy confirmed:unresolved ratio
    assert _counts(result, "unit") == (3, 1, 1)
    # a mix of probable + possible, no confirmed
    assert _counts(result, "component") == (0, 1, 2)
    # a type with ONLY possible links
    assert _counts(result, "sensor") == (0, 0, 2)
    # a type with NONE: absent from by_type (reads as all-zero) and never invented
    assert _counts(result, "variant") == (0, 0, 0)
    assert "variant" not in result.by_type


# 2b. by_type is a partition of the overall counts (sum of buckets == overall).
def test_by_type_sums_to_overall():
    part, tmap = _build(
        same={"unit": 3},
        cand={"unit": 1, "component": 1},
        poss={"unit": 1, "sensor": 2, "component": 2},
        orphan_types=("variant",),
    )
    result = _cov(part, tmap)

    types = ("unit", "component", "sensor", "variant")
    tot = tuple(sum(_counts(result, t)[i] for t in types) for i in range(3))
    assert tot == _overall(result)
    assert _overall(result) == (3, 2, 5)


# 3a. collection_gaps flags high-load types and NOT well-resolved ones (ratio driven via config).
def test_collection_gaps_flags_high_load_not_well_resolved():
    # "gap": 0 confirmed, 10 possible -> 10/max(0,1) = 10.0 (flagged at ratio 1.0).
    # "safe": 4 confirmed, 0 unresolved -> 0.0 (never flagged for any positive ratio).
    part, tmap = _build(same={"safe": 4}, poss={"gap": 10})

    result = _cov(part, tmap, ratio=1.0)
    gaps = _gaps(result)
    assert "gap" in gaps, "0 confirmed vs 10 possible must be a collection gap"
    assert "safe" not in gaps, "a fully-confirmed type must never be a collection gap"
    # deterministically ordered: identical inputs -> identical sequence, no dups
    assert _gaps(_cov(part, tmap, ratio=1.0)) == gaps
    assert len(gaps) == len(set(gaps))


# 3b. The ratio comparison is inclusive: exactly-at is flagged, just-under is not (ratio 2.0).
def test_collection_gaps_boundary_is_inclusive():
    ratio = 2.0
    # atk: conf 1, unresolved 2  -> 2/1 = 2.0 == ratio -> flagged (>= is inclusive)
    # und: conf 2, unresolved 3  -> 3/2 = 1.5 <  ratio -> not flagged (just under)
    # ovr: conf 1, unresolved 3  -> 3/1 = 3.0 >  ratio -> flagged
    # saf: conf 3, unresolved 0  -> 0.0       <  ratio -> not flagged
    part, tmap = _build(
        same={"atk": 1, "und": 2, "ovr": 1, "saf": 3},
        cand={"atk": 1, "und": 1, "ovr": 1},
        poss={"atk": 1, "und": 2, "ovr": 2},
    )
    result = _cov(part, tmap, ratio=ratio)

    # precondition: the per-type shapes are exactly as intended (so the boundary means what we claim)
    assert _counts(result, "atk") == (1, 1, 1)
    assert _counts(result, "und") == (2, 1, 2)
    assert _counts(result, "ovr") == (1, 1, 2)
    assert _counts(result, "saf") == (3, 0, 0)

    gaps = _gaps(result)
    assert "atk" in gaps, "ratio exactly at the threshold must be flagged (inclusive >=)"
    assert "ovr" in gaps, "ratio above the threshold must be flagged"
    assert "und" not in gaps, "ratio just under the threshold must NOT be flagged"
    assert "saf" not in gaps, "a fully-resolved type must NOT be flagged"
    # the dial that produced this verdict is echoed back
    assert _ratio(result) == pytest.approx(ratio)


# 4. A fully-resolved partition (only same_as) has no collection gaps — with the machinery ACTIVE.
def test_fully_resolved_partition_has_no_collection_gaps():
    part, tmap = _build(same={"unit": 2, "component": 2})
    # precondition: nothing unresolved anywhere
    assert part.candidates == [] and part.possible == []

    result = _cov(part, tmap, ratio=1.0)  # ratio configured, so gap detection is live

    assert _overall(result) == (4, 0, 0)
    assert _gaps(result) == [], "with zero unresolved load, collection_gaps must be empty"
    assert _gaps(_cov(part, tmap, ratio=1.0)) == []  # deterministic on repeat


# transparency: the policy dial is echoed; unconfigured -> None and gaps are inert (fails closed).
def test_policy_dial_echoed_and_inert_when_unconfigured():
    # a fixture that WOULD be a gap if the dial were set
    part, tmap = _build(same={"safe": 1}, poss={"gap": 5})

    default = _cov(part, tmap)  # no ratio configured
    assert _ratio(default) is None, "unset coverage_gap_ratio must echo back as None"
    assert _gaps(default) == [], "with no ratio configured, gap detection is inert (fails closed)"

    driven = _cov(part, tmap, ratio=1.75)  # a configured value round-trips into the echoed policy
    assert _ratio(driven) == pytest.approx(1.75)


# 5. (optional) GET /coverage returns the summary and leaves the node/edge view JSON unaffected.
def test_coverage_route_returns_summary_and_view_unaffected():
    from fastapi.testclient import TestClient

    from chanakya.api import create_app
    from tests.api.conftest import build_golden_state

    with TestClient(create_app(build_golden_state())) as client:
        view_before = client.get("/view").json()
        r = client.get("/coverage")
        if r.status_code == 404:
            pytest.skip("GET /coverage not exposed by the implementation")
        assert r.status_code == 200
        body = r.json()
        for key in ("confirmed", "probable", "possible"):
            assert isinstance(body.get(key), int), f"/coverage summary missing int '{key}'"
        assert "by_type" in body
        assert isinstance(body.get("collection_gaps"), list)
        # the coverage read must not mutate the drawn graph
        assert client.get("/view").json() == view_before
