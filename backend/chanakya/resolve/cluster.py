"""Two-phase iterative collective ER: candidate-gen → bootstrap → relational fixpoint.

Candidate-generation maximises **recall** (blocking + hard-IDs + alias-equivalence + proposals);
the merge decision is **precision-first** (spine/03). A high-precision **bootstrap** pass (shared unique
hard-ID / alias-equivalence / exact name / containment-or-acronym) seeds the partition with no relational
term; then the **relational fixpoint** recomputes ``merge_score`` over the current partition and
auto-merges/HITL/separates, iterating until a full pass fires no new auto-merge. It terminates because
merges are **monotone** — clusters only grow within a rebuild — so a no-new-merge pass *is* the fixed
point. ``distinct_from`` is a **hard veto** applied before any band decision; the *proposal* signals
(frozen LLM proposals, source-asserted ``same-as`` claims) are **raise-only** — they can lift a pair into
the HITL band but never reach auto-merge, which stays reachable by the deterministic terms alone.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from chanakya.schemas import pair_key

from .aliases import AliasIndex
from .entities import Entity, EntityGraph, as_pair, namespace_compatible, unordered_pairs
from .normalize import normalize, tokens
from .rconfig import ATTRIBUTE, RELATIONAL, SIGNALS, SOURCE_ASSERTED, TEMPORAL, ResolveConfig
from .scoring import merge_score

Pair = frozenset[str]


class _UnionFind:
    def __init__(self, ids: list[str]) -> None:
        self.parent = {i: i for i in ids}

    def find(self, x: str) -> str:
        if x not in self.parent:
            return x  # a mention-only ref (a triple endpoint with no entity claim) is its own root
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:  # path compression (deterministic — pointers only)
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            lo, hi = sorted((ra, rb))
            self.parent[hi] = lo  # deterministic root = lexicographically smallest


@dataclass
class ResolveResult:
    canonical: dict[str, str] = field(default_factory=dict)  # merged eid → display canonical id
    same_as: list[tuple[str, str]] = field(default_factory=list)  # (member, canonical)
    candidates: list[tuple[str, str]] = field(default_factory=list)  # HITL-band pairs (sorted)
    distinct_from: list[tuple[str, str]] = field(default_factory=list)  # vetoed pairs surfaced as edges
    merge_confidence: dict[str, float] = field(default_factory=dict)
    merge_breakdown: dict[str, dict[str, float]] = field(default_factory=dict)


def _deterministic_total(bd: dict[str, float], cfg: ResolveConfig) -> float:
    """``merge_score`` minus the source-asserted term — the only total the auto-merge line may be crossed on.

    A ``same-as`` in the claim stream is somebody's *assertion* that two things are one thing, and the
    corpus plants false ones (an Army↔PAF variant cross-wiring that walks straight into a distinct-from
    trap). So the identity term is raise-only in the same structural sense the LLM proposal is: it can
    lift a pair into the analyst's queue, but auto-merge must be earned by name/attribute + neighbourhood
    + temporal coherence alone. Subtracting the term (rather than trusting the clamped total) keeps that
    true whatever the weights are re-tuned to.
    """
    return sum(cfg.weight(sig) * bd[sig] for sig in SIGNALS if sig != SOURCE_ASSERTED)


def _band(bd: dict[str, float], cfg: ResolveConfig, has_raise: bool) -> str:
    """auto ≥ auto_merge (deterministic subtotal) · hitl in [hitl_low, auto_merge) OR raised · else separate.

    Raise-only is structural on **both** raise-only channels: ``has_raise`` (the frozen LLM proposal, and
    now the source-asserted identity pair) can only reach *hitl*, and the source-asserted *score* is
    excluded from the auto test — so neither can push a pair across the auto-merge line (the mandatory
    red-team patch, spine/08 §3.11, extended to identity claims by D-2.5).
    """
    if _deterministic_total(bd, cfg) >= cfg.auto_merge:
        return "auto"
    if bd["total"] >= cfg.hitl_low or has_raise:
        return "hitl"
    return "separate"


def _candidate_pairs(
    graph: EntityGraph,
    cfg: ResolveConfig,
    alias_idx: AliasIndex,
    raise_only: set[Pair],
    toks: dict[str, list[str]],
) -> set[Pair]:
    """Recall-max candidate generation: block on (type, namespace, name-token) + hard-IDs + aliases + proposals."""
    keys = set(cfg.blocking_keys)
    blocks: dict[tuple, set[str]] = {}
    trans = cfg.transliteration

    def add(block: tuple, eid: str) -> None:
        blocks.setdefault(block, set()).add(eid)

    for eid, ent in graph.entities.items():
        etype = ent.etype if "type" in keys else ""
        ns = ent.namespace() if "country_or_domain_namespace" in keys else ""
        if "name_token" in keys:
            for tok in tokens(ent.name, trans):
                add(("nt", etype, ns, tok), eid)
        else:
            add(("blk", etype, ns), eid)
        for kind in ("unique", "categorical"):
            for attr in cfg.hard_id_fields(kind).get(ent.etype, []):
                v = ent.attrs.get(attr)
                if v is not None:
                    add(("hid", attr, str(v)), eid)

    # Relational blocking: same-type entities that share a graph neighbour are candidates — the
    # "different names, same neighbourhood" merge the fixpoint exists to catch (precision comes later).
    shared_nbr: dict[tuple[str, str], set[str]] = {}
    for e in graph.edges:
        for ref, other in ((e.subject, e.object), (e.object, e.subject)):
            ref_ent = graph.entities.get(ref)
            if ref_ent is not None:
                shared_nbr.setdefault((other, ref_ent.etype), set()).add(ref)

    pairs: set[Pair] = set()
    for members in list(blocks.values()) + list(shared_nbr.values()):
        for a, b in unordered_pairs(sorted(members)):
            pairs.add(frozenset((a, b)))

    # Two names can denote one thing while sharing no token at all — an alias (FD-2000 ↔ HQ-9/P) or an
    # acronym (PAAD ↔ Pakistan Army Air Defence). Neither is reachable by token blocking, so add them here.
    eids = sorted(graph.entities)
    for a, b in unordered_pairs(eids):
        if alias_idx.equivalent(
            normalize(graph.entities[a].name, trans), normalize(graph.entities[b].name, trans)
        ) or _name_containment(graph.entities[a], graph.entities[b], cfg, toks):
            pairs.add(frozenset((a, b)))

    return pairs | raise_only


def _shared_unique_id(a: Entity, b: Entity, cfg: ResolveConfig) -> bool:
    for attr in cfg.hard_id_fields("unique").get(a.etype, []):
        va, vb = a.attrs.get(attr), b.attrs.get(attr)
        if va is not None and va == vb:
            return True
    return False


# ── the open-world name trigger (P3.3): containment + acronym expansion ────────────────────────

def _descriptor_extension(short: list[str], long_: list[str], cfg: ResolveConfig) -> bool:
    """True when the longer name is the shorter one plus a *descriptive* word ("HT-233 engagement radar").

    Head-anchored (a prefix, not a bag of tokens) and judged on the **first added token**: a name extended
    by a word is the same thing described more fully; a name extended by a mark or a number is a different
    model (``HQ-9`` → ``HQ-9/P`` is a whole other missile, ``HT-233`` → ``HT-233 (H-200)`` is precisely the
    orphan alias the demo requires an analyst to earn).

    The second gate is on the **short** side: a single bare word ("China", "Pakistan") is a prefix of half
    the graph and bridges things that are not the same — it fused CPMIEC into CASIC and walked "Pakistan"
    straight at the PAAD/PAF unit trap. Such a form is genuinely ambiguous evidence, so it belongs in the
    queue, not in a confidence-1.0 bootstrap. Those two tests together are what make this safe to bootstrap.
    """
    min_len, min_tokens = cfg.containment_min_descriptor_len, cfg.containment_min_short_tokens
    if min_len is None or min_tokens is None or len(short) < min_tokens:
        return False
    if len(short) >= len(long_) or long_[: len(short)] != short:
        return False
    head = long_[len(short)]
    return head.isalpha() and len(head) >= min_len


def _acronym_expansion(short: list[str], long_: list[str], cfg: ResolveConfig) -> bool:
    """True when a one-token name is exactly the initials of a multi-token one (``PAAD`` ⇄ Pakistan Army…).

    Strict initials of *every* token, so a stop-word in the expansion (ARMT ≠ "Academy **of** Rocket…")
    fails closed and stays a scored candidate rather than a silent merge.
    """
    min_len = cfg.acronym_min_len
    if min_len is None or len(short) != 1 or len(long_) < min_len:
        return False
    acronym = short[0]
    if not acronym.isalpha() or len(acronym) < min_len or len(acronym) != len(long_):
        return False
    return acronym == "".join(t[0] for t in long_)


def _token_index(graph: EntityGraph, cfg: ResolveConfig) -> dict[str, list[str]]:
    """``eid → normalised tokens``, computed once: the containment trigger is consulted per candidate pair."""
    return {eid: tokens(ent.name, cfg.transliteration) for eid, ent in graph.entities.items()}


def _name_containment(a: Entity, b: Entity, cfg: ResolveConfig, toks: dict[str, list[str]]) -> bool:
    """High-precision open-world name equivalence: containment or acronym, same type + namespace.

    The registry (P3.0) pre-resolves every surface form we have *already seen*; this is the tail it has
    never seen — a document naming the same thing more verbosely, or by its initials. Type + namespace
    gated, and (in the bootstrap) veto-gated like every other merge, so it can never fuse a trap pair.

    Note it is consulted **twice**: once to *generate* the candidate pair (an acronym shares no name token
    with its expansion, so ordinary blocking would never propose "PAAD" against "Pakistan Army Air
    Defence"), and again to *decide* the bootstrap merge.
    """
    if a.etype != b.etype or not namespace_compatible(a, b):
        return False
    ta, tb = toks.get(a.eid, []), toks.get(b.eid, [])
    if not ta or not tb or ta == tb:
        return False
    short, long_ = (ta, tb) if len(ta) < len(tb) else (tb, ta)
    return _descriptor_extension(short, long_, cfg) or _acronym_expansion(short, long_, cfg)


def resolve_entities(
    graph: EntityGraph,
    cfg: ResolveConfig,
    alias_idx: AliasIndex,
    veto: set[Pair],
    raise_only: set[Pair],
    authoritative: set[Pair] | None = None,
) -> ResolveResult:
    """Run the full two-phase resolution over the entity graph; returns the partition + decisions.

    ``raise_only`` is the union of the *proposal* channels — the frozen offline LLM ``merge_proposal``
    records and the source-asserted ``same-as`` pairs from the claim stream (D-2.5). Both may lift a pair
    into the HITL band and neither may ever reach auto-merge.

    ``authoritative`` is the one channel that may **bootstrap**: in-document coreference whose evidence
    category the operator opted in, already veto-, type-, namespace- and contradiction-gated by
    ``resolve._coref_pairs`` (empty by default). It joins the bootstrap rather than the fixpoint because
    it is the same *kind* of evidence the other bootstrap triggers are — a direct, high-precision
    statement of identity — and it is still subject to the veto checks every bootstrap merge runs.
    """
    authoritative = authoritative or set()
    res = ResolveResult()
    if not cfg.scorable:
        return res  # no bands configured ⇒ inert (identity partition) — no code literal needed

    eids = sorted(graph.entities)
    uf = _UnionFind(eids)
    trans = cfg.transliteration
    toks = _token_index(graph, cfg)
    pairs = sorted(
        tuple(sorted(p))
        for p in _candidate_pairs(graph, cfg, alias_idx, raise_only | authoritative, toks)
    )

    def vetoed(a: str, b: str) -> bool:
        return frozenset((a, b)) in veto or alias_idx.barred(
            normalize(graph.entities[a].name, trans), normalize(graph.entities[b].name, trans)
        )

    def violates_veto_transitively(a: str, b: str) -> bool:
        """Would unioning a,b place any explicitly-vetoed pair into one cluster? (cannot-link, cluster-level)."""
        ra, rb = uf.find(a), uf.find(b)
        for x, y in _veto_eid_pairs(veto, alias_idx, graph, trans):
            rx, ry = uf.find(x), uf.find(y)
            if {rx, ry} == {ra, rb}:  # x,y currently split across exactly these two clusters → the union fuses them
                return True
        return False

    def merge(a: str, b: str, confidence: float, bd: dict[str, float]) -> None:
        res.same_as.append((a, b))  # raw merge pair; _finalise stars it to the cluster canonical
        res.merge_confidence[pair_key(a, b)] = confidence
        res.merge_breakdown[pair_key(a, b)] = bd
        uf.union(a, b)

    # ── Phase 1: high-precision bootstrap (no relational term) ────────────────────────────────
    for a, b in pairs:
        if uf.find(a) == uf.find(b) or vetoed(a, b) or violates_veto_transitively(a, b):
            continue
        ea, eb = graph.entities[a], graph.entities[b]
        na, nb = normalize(ea.name, trans), normalize(eb.name, trans)
        same_ns = ea.namespace() == eb.namespace()
        # exact-name merge is gated on matching namespace + a non-empty name (China ≠ Pakistan; "" ≠ "").
        if (
            _shared_unique_id(ea, eb, cfg)
            or alias_idx.equivalent(na, nb)
            or (bool(na) and na == nb and same_ns)
            or _name_containment(ea, eb, cfg, toks)
            # The document itself stated this equivalence in a quotable span, and the pair cleared the
            # veto/type/namespace/contradiction gates upstream — evidence no string comparison can reach.
            or frozenset((a, b)) in authoritative
        ):
            bd = merge_score(ea, eb, graph, uf.find, cfg, alias_idx)
            merge(a, b, 1.0, bd)  # unambiguous evidence → identity confidence 1.0

    # ── Phase 2: relational fixpoint (iterate to no-new-auto-merge; monotone ⇒ terminates) ────
    changed = True
    while changed:
        changed = False
        for a, b in pairs:
            if uf.find(a) == uf.find(b) or vetoed(a, b) or violates_veto_transitively(a, b):
                continue
            bd = merge_score(graph.entities[a], graph.entities[b], graph, uf.find, cfg, alias_idx)
            if _band(bd, cfg, has_raise=False) == "auto":
                merge(a, b, bd["total"], bd)
                changed = True

    # ── collect HITL candidates from the stable partition ─────────────────────────────────────
    for a, b in pairs:
        if uf.find(a) == uf.find(b) or vetoed(a, b):
            continue
        bd = merge_score(graph.entities[a], graph.entities[b], graph, uf.find, cfg, alias_idx)
        if _band(bd, cfg, has_raise=frozenset((a, b)) in raise_only) == "hitl":
            res.candidates.append((a, b))
            res.merge_confidence[pair_key(a, b)] = bd["total"]
            res.merge_breakdown[pair_key(a, b)] = bd

    # Always surface a configured/​learned distinct-from between two instantiated entities as an edge —
    # the trap is visible even when the pair never became a scored candidate (different blocks).
    for x, y in _veto_eid_pairs(veto, alias_idx, graph, trans):
        res.distinct_from.append((x, y))

    return res


def _veto_eid_pairs(
    veto: set[Pair], alias_idx: AliasIndex, graph: EntityGraph, trans: dict[str, str]
) -> list[tuple[str, str]]:
    """Vetoed pairs (config + learned ``barred``) that are both instantiated entities, as sorted tuples."""
    out: set[tuple[str, str]] = set()
    for pair in veto:
        a, b = sorted(pair)
        if a in graph.entities and b in graph.entities:
            out.add((a, b))
    # learned distinct-from (merge_adjudication reject/split) over instantiated entities
    norm_to_eids: dict[str, list[str]] = {}
    for eid, ent in graph.entities.items():
        norm_to_eids.setdefault(normalize(ent.name, trans), []).append(eid)
    for barred in alias_idx.distinct:
        names = sorted(barred)
        if len(names) != len({*names}):  # a self-pair — ignore
            continue
        na, nb = names
        for a in norm_to_eids.get(na, []):
            for b in norm_to_eids.get(nb, []):
                if a != b:
                    out.add(tuple(sorted((a, b))))  # type: ignore[arg-type]
    return sorted(out)


def finalise(
    res: ResolveResult, graph: EntityGraph, cfg: ResolveConfig, veto: set[Pair], alias_idx: AliasIndex
) -> None:
    """Reconcile ALL merges (entity + place) into one flat canonical map + starred same_as (deterministic).

    Runs *after* place resolution so entity- and place-merges share one union-find, the canonical map is
    fully resolved (no chains — ``_assemble`` does a single-level lookup), and any candidate that ended up
    merged is dropped. Confidence/breakdown for each star edge carries a representative from the raw merges.

    The union here is **veto-guarded**: a same_as edge (e.g. a place-merge that ran after ``resolve_entities``)
    is refused if it would transitively put an explicitly-vetoed pair into one cluster — so the hard veto
    holds across *every* merge source, not just the entity fixpoint (spine/03 false-merge discipline).
    """
    raw_conf, raw_bd = dict(res.merge_confidence), dict(res.merge_breakdown)
    members_seen = {e for pair in res.same_as for e in pair} | set(graph.entities)
    uf = _UnionFind(sorted(members_seen))
    veto_pairs = _veto_eid_pairs(veto, alias_idx, graph, cfg.transliteration)

    def would_violate(a: str, b: str) -> bool:
        ra, rb = uf.find(a), uf.find(b)
        return any({uf.find(x), uf.find(y)} == {ra, rb} for x, y in veto_pairs)

    kept_same_as: list[tuple[str, str]] = []
    for a, b in sorted(res.same_as):
        if would_violate(a, b):
            continue  # a veto beats a merge from any source (entity or place)
        uf.union(a, b)
        kept_same_as.append((a, b))
    res.same_as = kept_same_as

    clusters: dict[str, list[str]] = {}
    for eid in sorted(members_seen):
        clusters.setdefault(uf.find(eid), []).append(eid)

    res.canonical = {}
    same_as: list[tuple[str, str]] = []
    res.merge_confidence = {}
    res.merge_breakdown = {}
    for members in clusters.values():
        if len(members) == 1:
            continue
        canonical = _preferred(members, graph, cfg)
        for m in sorted(members):
            if m == canonical:
                continue
            res.canonical[m] = canonical
            same_as.append((m, canonical))
            key = pair_key(m, canonical)
            res.merge_confidence[key] = _rep(raw_conf, m, key, 1.0)
            res.merge_breakdown[key] = _rep(raw_bd, m, key, {"total": 1.0})

    res.same_as = sorted(same_as)
    # a candidate that later merged, or is now vetoed-apart, is no longer an open question
    distinct = {as_pair(p) for p in res.distinct_from}
    surviving = {as_pair(p) for p in res.candidates if uf.find(p[0]) != uf.find(p[1]) and as_pair(p) not in distinct}
    for a, b in surviving:  # carry each surviving candidate's confidence/breakdown through the reset
        key = pair_key(a, b)
        if key in raw_conf:
            res.merge_confidence[key] = raw_conf[key]
        if key in raw_bd:
            res.merge_breakdown[key] = raw_bd[key]
    res.candidates = sorted(
        {as_pair(p) for p in res.candidates if uf.find(p[0]) != uf.find(p[1]) and as_pair(p) not in distinct}
    )
    res.distinct_from = sorted(distinct)


def _rep[T](raw: dict[str, T], m: str, key: str, default: T) -> T:
    """A representative confidence/breakdown for a star edge: the exact pair if recorded, else any touching m."""
    if key in raw:
        return raw[key]
    for k in sorted(raw):
        if m in k.split("|"):
            return raw[k]
    return default


def _preferred(members: list[str], graph: EntityGraph, cfg: ResolveConfig) -> str:
    """Canonical = registry stable id > alias-table canonical name > most connected > smallest id (stable).

    A cluster that contains a **registry** entry (``config/entities.yaml``) adopts that entry's stable
    ``entity_id`` (P3.0/D-B): it is the same id the subject lenses, the observables and the eval oracle
    use, so electing it is what actually closes the id-namespace split. With no registry seeded every
    entity ranks ``False`` on that key, so the ordering — and the golden view — is unchanged (gate G2).
    """
    alias_canon = {normalize(k, cfg.transliteration) for k in cfg.alias_table}

    def rank(eid: str) -> tuple[bool, bool, int]:
        ent = graph.entities.get(eid)
        is_registry = ent is not None and ent.registry
        is_canon = ent is not None and normalize(ent.name, cfg.transliteration) in alias_canon
        degree = len(graph.incident(eid)) if eid in graph.entities else 0
        return (is_registry, is_canon, degree)

    best = max(rank(e) for e in members)
    return min(e for e in members if rank(e) == best)  # lexicographic-min among the best-ranked


# re-export the signal names for tests / callers
__all__ = [
    "ResolveResult", "resolve_entities", "finalise",
    "ATTRIBUTE", "RELATIONAL", "TEMPORAL", "SOURCE_ASSERTED",
]
