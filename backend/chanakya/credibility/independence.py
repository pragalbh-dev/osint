"""Three-axis independence grouping — the anti-false-corroboration machine (spine/04 §3.5).

Corroboration only counts when looks are genuinely independent, so co-referring claims are clustered
into **independence groups** (one group = one independent look; the noisy-OR pools *across* groups).
A pair is independent only if it clears **all three** axes; failing a *hard* axis merges the pair:

* **origin** — different publisher, neither cites/embeds the other; a **shared image fingerprint**, a
  shared ``primary_origin_id``, or an aggregator↔upstream relationship all mean *one* origin (SIPRI +
  the press it compiles = one look). *Hard.*
* **interest** — aligned parties (both drawn from the deal's parties — operator-state ∪ exporter-state)
  are false corroboration (ISPR + Chinese state media). *Hard.*
* **discipline** — IMINT / ELINT / textual: two reads of one collection type are less independent than a
  cross-discipline pair. *Soft* — same-discipline looks still separate but at **half weight** (§3.5
  "same-class-but-passing = 0.5"); cross-discipline looks carry full weight.

**Derivation, not corroboration:** an ``inference`` claim shares its group with the claims in its
``premises`` — "I see a cylinder" + "that cylinder is an HQ-9" is *one* look, never two.
**adversary_denial** claims are **excluded from grouping entirely** (a gate, not a look) — they never
corroborate and never downgrade. **Fail-closed:** a pair is independent only when metadata
affirmatively establishes it; missing metadata ⇒ treated as the same origin (merge).

No scoring literal lives here (gate G6): the aligned-interest set, discipline map, and the same-class
weight are read from ``config.credibility`` (with vocabulary fallbacks).
"""

from __future__ import annotations

from chanakya.schemas import ClaimRecord, ConfigBundle, IndependenceGroup, SourceRegistryEntry

# Config keys (values live in config; these names are vocabulary, not scoring numbers — G6).
_DEFAULT_ALIGNED = ("operator-state", "exporter-state")  # parties to the deal → aligned interest
_DEFAULT_DISCIPLINES = {"satellite": "IMINT"}  # source_type → collection discipline; default textual
_TEXTUAL = "textual"
_ATTR_SHA, _ATTR_PDQ = "sha256", "pdq_hash"


class _UnionFind:
    """Minimal deterministic union-find over claim ids (dependent pairs share a set)."""

    def __init__(self, ids: list[str]) -> None:
        self._parent = {i: i for i in ids}

    def find(self, x: str) -> str:
        root = x
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[x] != root:  # path compression
            self._parent[x], x = root, self._parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:  # attach the larger id under the smaller → deterministic representative
            hi, lo = (ra, rb) if ra > rb else (rb, ra)
            self._parent[hi] = lo


def _aligned_set(config: ConfigBundle) -> set[str]:
    return set(getattr(config.credibility, "aligned_bias_vectors", None) or _DEFAULT_ALIGNED)


def _discipline(source: SourceRegistryEntry | None, config: ConfigBundle) -> str:
    mapping = getattr(config.credibility, "disciplines", None) or _DEFAULT_DISCIPLINES
    if source is None:
        return _TEXTUAL
    return mapping.get(source.source_type, _TEXTUAL)


def _origin_key(claim: ClaimRecord, source: SourceRegistryEntry | None) -> str:
    """The claim's origin identity: its ``primary_origin_id`` if set, else its ``source_id``."""
    if source is not None and source.primary_origin_id:
        return source.primary_origin_id
    return claim.source_id


def _image_fp(claim: ClaimRecord) -> str | None:
    attrs = claim.attributes or {}
    return attrs.get(_ATTR_SHA) or attrs.get(_ATTR_PDQ)


def _origin_dependent(
    a: ClaimRecord, b: ClaimRecord, sources: dict[str, SourceRegistryEntry]
) -> bool:
    """True if the pair shares an origin (same origin id, aggregator link, or same image fingerprint)."""
    sa, sb = sources.get(a.source_id), sources.get(b.source_id)
    if _origin_key(a, sa) == _origin_key(b, sb):
        return True
    fpa, fpb = _image_fp(a), _image_fp(b)
    if fpa is not None and fpa == fpb:  # same picture → one origin (recycled/reshared)
        return True
    # Aggregator inherits its upstreams: SIPRI aggregator_of [press] ⇒ same origin as that press.
    for src, other in ((sa, b), (sb, a)):
        if src is not None and src.aggregator_of:
            other_src = sources.get(other.source_id)
            other_origin = _origin_key(other, other_src)
            if other_origin in src.aggregator_of or other.source_id in src.aggregator_of:
                return True
    return False


def _interest_dependent(
    a: ClaimRecord, b: ClaimRecord, sources: dict[str, SourceRegistryEntry], aligned: set[str]
) -> bool:
    """True if both claims come from aligned parties to the deal (operator/exporter) → false corroboration."""
    sa, sb = sources.get(a.source_id), sources.get(b.source_id)
    ba = sa.bias_vector if sa is not None else None
    bb = sb.bias_vector if sb is not None else None
    return ba in aligned and bb in aligned


def _derivation_linked(a: ClaimRecord, b: ClaimRecord) -> bool:
    """True if one claim is a premise of the other (inference ⇒ not independent of what it derives from)."""
    return a.claim_id in (b.premises or []) or b.claim_id in (a.premises or [])


def group_by_independence(
    claim_ids: list[str],
    claims: dict[str, ClaimRecord],
    sources: dict[str, SourceRegistryEntry],
    config: ConfigBundle,
) -> list[IndependenceGroup]:
    """Cluster co-referring claims into independent looks (hard-merge on origin/interest/derivation)."""
    aligned = _aligned_set(config)
    same_class_weight = getattr(config.credibility, "same_class_weight", None)

    # adversary_denial claims are excluded from grouping entirely (a gate, never a look).
    present = [cid for cid in claim_ids if cid in claims]
    scored_ids = [
        cid for cid in present
        if not (
            (src := sources.get(claims[cid].source_id)) is not None and src.adversary_denial_flag
        )
    ]
    if not scored_ids:
        return []

    uf = _UnionFind(scored_ids)
    for i, a_id in enumerate(scored_ids):
        for b_id in scored_ids[i + 1 :]:
            a, b = claims[a_id], claims[b_id]
            if (
                _derivation_linked(a, b)
                or _origin_dependent(a, b, sources)
                or _interest_dependent(a, b, sources, aligned)
            ):
                uf.union(a_id, b_id)

    # Assemble groups (deterministic order: by representative id, members sorted).
    members: dict[str, list[str]] = {}
    for cid in scored_ids:
        members.setdefault(uf.find(cid), []).append(cid)

    groups: list[IndependenceGroup] = []
    for rep in sorted(members):
        member_ids = sorted(members[rep])
        rep_claim = claims[member_ids[0]]
        rep_src = sources.get(rep_claim.source_id)
        groups.append(
            IndependenceGroup(
                group_id=f"grp:{rep}",
                claim_ids=member_ids,
                axis_key={
                    "origin": _origin_key(rep_claim, rep_src),
                    "discipline": _discipline(rep_src, config),
                    "interest": (rep_src.bias_vector if rep_src is not None else "") or "",
                },
            )
        )

    # Soft discipline axis: the first group of each discipline is a full look; further same-discipline
    # groups are "same-class-but-passing" → half weight (config-driven; default full if unconfigured).
    if same_class_weight is not None:
        seen_disc: set[str] = set()
        for grp in groups:  # groups already in deterministic order
            disc = grp.axis_key.get("discipline", _TEXTUAL)
            if disc in seen_disc:
                grp.weight = same_class_weight
            seen_disc.add(disc)
    return groups
