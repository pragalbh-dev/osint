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

from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field

from chanakya.schemas import pair_key

from .aliases import AliasIndex
from .entities import Entity, EntityGraph, as_pair, namespace_compatible, unordered_pairs
from .normalize import normalize, tokens
from .rconfig import ATTRIBUTE, RELATIONAL, SIGNALS, SOURCE_ASSERTED, TEMPORAL, ResolveConfig
from .scoring import _shared_unique_id, geo_conflict_km, has_durable_identity_support, merge_score

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
    # pair_key → analyst-facing rationale, only for a candidate RAISED by a below-floor critical conflict
    # (D5 take-care a, Stage 3A). Empty for every ordinary scored candidate — a raise-with-a-reason is a
    # different question ("a critical attribute disagrees, but not credibly enough to wall") than a
    # look-alike, and the analyst needs to see which.
    candidate_reasons: dict[str, str] = field(default_factory=dict)
    possible: list[tuple[str, str]] = field(default_factory=list)  # retained sub-HITL watch-list (D4; NOT drawn)
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


def _band(bd: dict[str, float], cfg: ResolveConfig, has_raise: bool, auto_merge: float | None = None) -> str:
    """auto ≥ auto_merge (deterministic subtotal) · hitl in [hitl_low, auto_merge) OR raised · else separate.

    Raise-only is structural on **both** raise-only channels: ``has_raise`` (the frozen LLM proposal, and
    now the source-asserted identity pair) can only reach *hitl*, and the source-asserted *score* is
    excluded from the auto test — so neither can push a pair across the auto-merge line (the mandatory
    red-team patch, spine/08 §3.11, extended to identity claims by D-2.5).

    ``auto_merge`` overrides the auto floor for this one pair — the caller passes the *per-type* floor
    (``cfg.auto_merge_for_pair``) so a type where a near-identical name reliably means one entity
    (organisation / trading-org spelling variants) can auto-merge at a lower bar than the strict global
    default, while identity-sensitive types (variant, unit, site) keep the strict 0.85. ``None`` ⇒ the
    global ``cfg.auto_merge``, so an absent per-type map is byte-unchanged (gate G2). Only the auto floor
    moves; the ``hitl_low`` review band and the source-asserted exclusion are untouched.
    """
    floor = cfg.auto_merge if auto_merge is None else auto_merge
    if _deterministic_total(bd, cfg) >= floor:
        return "auto"
    if bd["total"] >= cfg.hitl_low or has_raise:
        return "hitl"
    return "separate"


def _bridge_reason(wall: tuple[str, str]) -> str:
    """The analyst-facing rationale for a bridge-across-a-wall candidate (D9, Stage 3A-ii).

    Names the hard wall the straddle would have crossed so the analyst can go straight to it. Prose only —
    no threshold, no code literal (gate G6). Deliberately distinct wording from the below-floor
    critical-conflict raise (``resolve._critical_raise_reason``): a look-alike straddling a wall and a pair
    stating an under-attested critical disagreement are different questions, and the queue must say which.
    """
    x, y = wall
    return (
        f"bridge across a wall: this pair scores as one entity, but merging it would fuse two clusters "
        f"held apart by a hard do-not-merge wall ({x} ≠ {y}). The wall HOLDS — the pair is never "
        f"merged — but a mention that looks like one entity yet straddles a wall means the wall is wrong, "
        f"the pair is a conflation / extraction error, or it is deliberate deception. Analyst adjudication "
        f"required (D9)."
    )


def _perishable_confirm_reason() -> str:
    """Analyst-facing rationale for a perishable-only confirmation capped to ``probable`` (Stage 3B-iii).

    Prose only — no threshold, no code literal (gate G6). Deliberately distinct wording from the below-floor
    critical-conflict raise (``resolve._critical_raise_reason``) and the bridge alarm (:func:`_bridge_reason`): a
    would-be auto-merge that rests only on transient evidence is its own question, and the queue must say
    which.
    """
    return (
        "confirmed only on perishable / transient evidence — this pair scores into the auto-merge band, but "
        "every identity signal that carried it there is a perishable or transient state (a location, a "
        "status, a posture), not a durable identifier or a stable attribute the two sides agree on. A shared "
        "transient state can be one entity, or two entities that passed through the same state — the score "
        "cannot separate the two. The auto-merge is withheld and the pair is raised for analyst confirmation "
        "(Stage 3B-iii)."
    )


def _name_alone(bd: dict[str, float]) -> bool:
    """True when the ONLY nonzero *identity* signal is the name/attribute term (D4 banked correction).

    ``temporal_consistency`` is a near-constant background term (1.0 on any non-relocation pair), not a
    line of identity evidence, so it is deliberately excluded — the test is purely ``relational == 0`` and
    ``source_asserted == 0``. A pair that agrees on nothing but its name has not *earned* an analyst's
    attention; with the policy dial on it caps at ``possible`` rather than reaching the review queue.
    """
    return bd[ATTRIBUTE] > 0 and bd[RELATIONAL] == 0 and bd[SOURCE_ASSERTED] == 0


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


def _bottleneck_confidence(edges: Mapping[Pair, float], x: str, y: str) -> float:
    """Widest-path unification confidence between two already-merged entities (D10 take-care a).

    ``edges`` maps each recorded union ``{u, v}`` → the confidence it was merged at (a bootstrap / confirmed
    merge = 1.0, a fuzzy Phase-2 merge = its total). Two entities that ended up in one cluster were unified
    along some chain of these merges; their unification confidence is the **maximum over all connecting
    chains of the minimum merge confidence along the chain** — the strongest available chain, limited by its
    weakest link. A single direct merge therefore returns that merge's own confidence; a chain returns its
    bottleneck (so a strong chain is not dragged down by an unrelated weak merge elsewhere in the cluster,
    and a weak link anywhere on the chain is not hidden behind a strong one).

    A label-correcting fixpoint over a finite graph: bottleneck labels only rise and are bounded by the edge
    confidences, so it converges to the unique widest-path solution independent of iteration order
    (deterministic — gate G2). Returns 0.0 when no chain connects ``x`` and ``y`` (defensive — a shared
    neighbour's two endpoints always share a cluster). Literal-free beyond the 0/1 bounds of the confidence
    scale the module already uses (gate G6).
    """
    adj: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for pair, conf in edges.items():
        u, v = sorted(pair)
        adj[u].append((v, conf))
        adj[v].append((u, conf))
    best: dict[str, float] = {x: 1.0}
    changed = True
    while changed:
        changed = False
        for u in list(best):
            reach = best[u]
            for v, conf in adj.get(u, ()):
                cand = reach if reach < conf else conf  # min(reach-so-far, this merge) — bottleneck of the chain
                if cand > best.get(v, 0.0):
                    best[v] = cand
                    changed = True
    return best.get(y, 0.0)


def resolve_entities(
    graph: EntityGraph,
    cfg: ResolveConfig,
    alias_idx: AliasIndex,
    veto: set[Pair],
    raise_only: set[Pair],
    authoritative: set[Pair] | None = None,
    raise_walls: Mapping[Pair, str] | None = None,
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

    ``raise_walls`` (D5 take-care a, Stage 3A) is the *below-floor critical-conflict* channel: same-type
    pairs that STATE a different value of a declared-critical attribute but whose conflict is not
    trustworthy enough to wall (the conflicting value on some side comes only from below-floor sources).
    Unlike ``raise_only`` it is a **block-merge-and-review** set: the pair may neither bootstrap nor
    auto-merge (a critical disagreement must not slip through), yet it is guaranteed a place in the HITL
    candidate queue with a reason — never silently walled, never silently merged. Maps each pair → its
    reason string. Empty by default ⇒ no effect.
    """
    authoritative = authoritative or set()
    raise_walls = raise_walls or {}
    res = ResolveResult()
    if not cfg.scorable:
        return res  # no bands configured ⇒ inert (identity partition) — no code literal needed

    eids = sorted(graph.entities)
    uf = _UnionFind(eids)
    trans = cfg.transliteration
    toks = _token_index(graph, cfg)
    pairs = sorted(
        tuple(sorted(p))
        for p in _candidate_pairs(graph, cfg, alias_idx, raise_only | authoritative | set(raise_walls), toks)
    )

    def vetoed(a: str, b: str) -> bool:
        ea, eb = graph.entities[a], graph.entities[b]
        # A geographic impossibility is a veto on the same footing as a curated ``distinct_from``: it
        # blocks the bootstrap, the auto-merge fixpoint AND the candidate queue below, because a pair
        # that cannot be one entity is not a question worth an analyst's attention either. Unlike a
        # curated distinct-from it is NOT drawn as an edge — a geodesic separation is arithmetic, not a
        # finding, and the graph already carries both places on their own coordinates.
        return (
            frozenset((a, b)) in veto
            or alias_idx.barred(normalize(ea.name, trans), normalize(eb.name, trans))
            or geo_conflict_km(ea, eb, cfg) is not None
        )

    def violates_veto_transitively(a: str, b: str) -> bool:
        """Would unioning a,b place any explicitly-vetoed pair into one cluster? (cannot-link, cluster-level)."""
        ra, rb = uf.find(a), uf.find(b)
        for x, y in _veto_eid_pairs(veto, alias_idx, graph, trans):
            rx, ry = uf.find(x), uf.find(y)
            if {rx, ry} == {ra, rb}:  # x,y currently split across exactly these two clusters → the union fuses them
                return True
        return False

    # D10 take-care a: the ACTUAL union edges (kept separate from res.merge_confidence, which the later
    # collection loop also fills with candidate/possible confidences that are NOT merges) → the graph
    # ``pair_confidence`` reads to weight a shared neighbour by how confidently the two sides' neighbours
    # were resolved to one canonical.
    merge_edges: dict[Pair, float] = {}

    def merge(a: str, b: str, confidence: float, bd: dict[str, float]) -> None:
        res.same_as.append((a, b))  # raw merge pair; _finalise stars it to the cluster canonical
        res.merge_confidence[pair_key(a, b)] = confidence
        res.merge_breakdown[pair_key(a, b)] = bd
        merge_edges[frozenset((a, b))] = confidence
        uf.union(a, b)

    def pair_confidence(x: str, y: str) -> float:
        """Confidence at which raw entities x and y were resolved to one canonical (D10 take-care a).

        1.0 when they are the SAME raw entity (identical — no merge needed); else the widest merge-chain's
        bottleneck (:func:`_bottleneck_confidence`) — a bootstrap / confirmed unification is 1.0, a
        low-confidence fuzzy one is < 1.0. 0.0 when they were never unified (defensive — a shared neighbour's
        two endpoints always share a cluster). Reads the LIVE partition + merge edges, so a shared neighbour
        is weighted by the merge it currently rests on and the weight is monotone as clusters grow."""
        if x == y:
            return 1.0
        if uf.find(x) != uf.find(y):
            return 0.0
        return _bottleneck_confidence(merge_edges, x, y)

    def has_durable_trigger(a: str, b: str) -> bool:
        """A DURABLE bootstrap trigger fires for this pair — pair-intrinsic support
        (:func:`has_durable_identity_support`: shared unique id / same-value non-perishable agreement / a
        single-source witnessed transition, D8) PLUS the durable name / coreference triggers the standalone
        helper cannot see (it lacks the alias index and the coref set). Exactly the Phase-1 bootstrap
        disjunction: alias-equivalence, exact name + namespace, name containment, authoritative coref. Each is
        a stable line of identity evidence that does not evaporate when a transient state changes."""
        ea, eb = graph.entities[a], graph.entities[b]
        if has_durable_identity_support(ea, eb, cfg):
            return True
        na, nb = normalize(ea.name, trans), normalize(eb.name, trans)
        same_ns = ea.namespace() == eb.namespace()
        return (
            alias_idx.equivalent(na, nb)
            or (bool(na) and na == nb and same_ns)
            or _name_containment(ea, eb, cfg, toks)
            or frozenset((a, b)) in authoritative
        )

    def confirm_is_durable(a: str, b: str, floor: float) -> bool:
        """Is a would-be auto-merge carried by DURABLE evidence rather than the perishable-succession bonus?

        The decisive gate (Stage 3B-iii refinement): the pair still reaches the auto band on the **durable-only**
        score — ``attribute_score`` recomputed with the perishable ordered-succession-as-agreement bonus removed
        (base name similarity, alias-equivalence, and same-value agreement all still count; ``relational`` /
        ``temporal`` are unchanged). A name-driven or durable-attribute confirm still autos here; a pair carried
        over the line ONLY by a perishable trajectory does not. A durable bootstrap trigger (name/coref/shared-id)
        is durable support on its own footing too, so it short-circuits. Only a confirm that fails BOTH rests
        solely on transient agreement — that is the one the cap withholds."""
        if has_durable_trigger(a, b):
            return True
        bd_durable = merge_score(
            graph.entities[a], graph.entities[b], graph, uf.find, cfg, alias_idx,
            durable_only=True, pair_confidence=pair_confidence,
        )
        return _band(bd_durable, cfg, has_raise=False, auto_merge=floor) == "auto"

    # Stage 3B-iii: pairs that reach the auto band on the FULL score but NOT on the durable-only score — the
    # perishable ordered-succession bonus is the sole thing carrying them to confirm — are blocked from
    # auto-merge and forced to the HITL queue with a reason, the same block-merge-and-review contract as
    # ``raise_walls``. Maintained across the Phase-2 fixpoint (the durable-only band reads the partition-
    # dependent ``relational`` term, so a pair can gain durable support as clusters grow and must be
    # re-evaluated, not permanently pinned); consumed in the candidate-collection loop. Empty ⇒ every
    # auto-band pair confirmed on durable evidence and merged (byte-unchanged).
    perishable_capped: dict[Pair, str] = {}

    # ── Phase 1: high-precision bootstrap (no relational term) ────────────────────────────────
    for a, b in pairs:
        if uf.find(a) == uf.find(b) or vetoed(a, b) or violates_veto_transitively(a, b):
            continue
        if frozenset((a, b)) in raise_walls:
            continue  # a below-floor critical conflict may not bootstrap-merge — it is raised to HITL
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
            bd = merge_score(ea, eb, graph, uf.find, cfg, alias_idx, pair_confidence=pair_confidence)
            merge(a, b, 1.0, bd)  # unambiguous evidence → identity confidence 1.0

    # ── Phase 2: relational fixpoint (iterate to no-new-auto-merge; monotone ⇒ terminates) ────
    changed = True
    while changed:
        changed = False
        for a, b in pairs:
            if uf.find(a) == uf.find(b) or vetoed(a, b) or violates_veto_transitively(a, b):
                continue
            if frozenset((a, b)) in raise_walls:
                continue  # a below-floor critical conflict is the analyst's call — never auto-merged
            bd = merge_score(
                graph.entities[a], graph.entities[b], graph, uf.find, cfg, alias_idx,
                pair_confidence=pair_confidence,
            )
            floor = cfg.auto_merge_for_pair(graph.entities[a].etype, graph.entities[b].etype)
            if _band(bd, cfg, has_raise=False, auto_merge=floor) == "auto":
                # Stage 3B-iii: a would-be auto-merge that still confirms on DURABLE evidence merges; one that
                # only confirms because a perishable ordered succession raised its score rests on a shared
                # transient state — one entity, or two that passed through it — so it is withheld and capped to
                # the review queue. The decision is re-made each pass: the durable-only band reads the
                # partition-dependent relational term, so a pair can EARN durable support as clusters grow.
                if confirm_is_durable(a, b, floor):
                    perishable_capped.pop(frozenset((a, b)), None)  # earned durable support ⇒ no longer capped
                    merge(a, b, bd["total"], bd)
                    changed = True
                else:
                    perishable_capped[frozenset((a, b))] = _perishable_confirm_reason()
            else:
                # No longer a would-be auto-merge (its relational term dropped); it is not a perishable-only
                # confirm any more, so clear any stale cap — the collection loop bands it on its own merits.
                perishable_capped.pop(frozenset((a, b)), None)

    # D9 (Stage 3A-ii): the transitive wall a candidate straddle would cross. Computed once — the
    # partition is stable here (this loop never unions), so the vetoed-entity pairs and cluster roots do
    # not move. Returns the FIRST vetoed pair (sorted, deterministic) whose two endpoints currently sit in
    # exactly the two clusters ``a`` and ``b`` belong to — i.e. the wall the union of (a,b) would fuse.
    # ``None`` ⇔ ``not violates_veto_transitively(a, b)``; this variant also *names* the wall for the alarm.
    veto_eid_pairs = _veto_eid_pairs(veto, alias_idx, graph, trans)

    def bridged_wall(a: str, b: str) -> tuple[str, str] | None:
        ra, rb = uf.find(a), uf.find(b)
        for x, y in veto_eid_pairs:
            if {uf.find(x), uf.find(y)} == {ra, rb}:
                return (x, y)
        return None

    # ── collect HITL candidates from the stable partition ─────────────────────────────────────
    for a, b in pairs:
        if uf.find(a) == uf.find(b) or vetoed(a, b):
            continue
        # T3b-A: two entities of DIFFERENT ontology types are not the same entity, and asking an analyst
        # whether an air-defence *sector* is the same thing as an air-defence *centre* is not triage, it
        # is noise. The same type gate `_identity_pairs`, `_name_containment` and `_coref_pairs` already
        # apply, finally applied to the scored queue as well. The escape hatch is deliberate: if a source
        # or the offline proposer explicitly asserts the identity, the pair is in `raise_only` and still
        # reaches the analyst — a cross-type assertion is exactly the kind of thing a human should see.
        if (
            graph.entities[a].etype != graph.entities[b].etype
            and frozenset((a, b)) not in raise_only
            and frozenset((a, b)) not in perishable_capped  # a capped confirm is guaranteed its queue place
        ):
            continue
        bd = merge_score(
            graph.entities[a], graph.entities[b], graph, uf.find, cfg, alias_idx,
            pair_confidence=pair_confidence,
        )
        floor = cfg.auto_merge_for_pair(graph.entities[a].etype, graph.entities[b].etype)
        has_raise = frozenset((a, b)) in raise_only
        raised_wall = frozenset((a, b)) in raise_walls
        capped_perishable = frozenset((a, b)) in perishable_capped
        band = _band(bd, cfg, has_raise=has_raise or raised_wall or capped_perishable, auto_merge=floor)
        # A below-floor critical conflict, or a perishable-only would-be confirm, is blocked from merge
        # upstream, so a high deterministic score would otherwise band it "auto" and drop it here — force it
        # to the review queue. Both are always the analyst's call: never silently walled/capped, never
        # silently merged.
        if (raised_wall or capped_perishable) and band == "auto":
            band = "hitl"
        # D9 (Stage 3A-ii) — the BRIDGE-ACROSS-A-WALL alarm. This pair cleared ``vetoed`` above (not
        # directly walled), but its union would fuse two clusters a hard wall holds apart (``bridged_wall``)
        # AND it scores as a genuine would-be merge — band ``auto``/``hitl``, real corroboration to both
        # sides, not an incidental low-score ``separate`` touch (the D9 corroboration gate, reusing the
        # existing bands — no new threshold). The wall HOLDS: Phase 1/2 already refused the union and this
        # loop never merges, so a bridge is surfaced to the analyst, never merged. An auto-band straddle
        # (which the fixpoint would otherwise have merged) is forced down to the review queue for the same
        # reason a below-floor critical conflict is — a would-be merge stopped by a wall is the analyst's
        # call, never a silent non-event. OFF ⇒ ``bridged_wall`` is never consulted (pre-D9, byte-unchanged).
        wall = bridged_wall(a, b) if cfg.surface_wall_bridges else None
        is_bridge = wall is not None and band in ("auto", "hitl")
        if is_bridge and band == "auto":
            band = "hitl"
        # D4 banked correction: a name-alone pair may not reach the review queue — it caps at `possible`.
        # Raise pairs AND wall bridges are exempt (an explicit assertion, a stated critical disagreement,
        # or a straddle across a hard wall is *more than a name coincidence*); the cap is a no-op unless
        # the operator turned the dial on (default off ⇒ byte-unchanged).
        capped = (
            cfg.name_alone_caps_at_possible
            and not (has_raise or raised_wall or is_bridge or capped_perishable)
            and _name_alone(bd)
        )
        pfloor = cfg.possible_floor
        if band == "hitl" and not capped:
            res.candidates.append((a, b))
            res.merge_confidence[pair_key(a, b)] = bd["total"]
            res.merge_breakdown[pair_key(a, b)] = bd
            # Reason precedence: a below-floor critical conflict (its own stated disagreement) first, then a
            # perishable-only capped confirm (Stage 3B-iii), then the cluster-level D9 bridge alarm.
            if raised_wall:
                res.candidate_reasons[pair_key(a, b)] = raise_walls[frozenset((a, b))]
            elif capped_perishable:
                res.candidate_reasons[pair_key(a, b)] = perishable_capped[frozenset((a, b))]
            elif is_bridge and wall is not None:
                res.candidate_reasons[pair_key(a, b)] = _bridge_reason(wall)
        # The retained `possible` watch-list (D4): a scored pair in [possible_floor, hitl_low) that today
        # is dropped as `separate`, PLUS any name-alone pair the dial just capped down out of `hitl`. Kept
        # with its identity confidence/breakdown; Partition-only (never drawn — see view/pipeline). Absent
        # `possible_floor` ⇒ the tier is off and the pair drops exactly as before.
        elif pfloor is not None and bd["total"] >= pfloor:
            res.possible.append((a, b))
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
    # Carry a raise reason only for candidates that survived the reset — a raised pair that later merged
    # or was vetoed apart is no longer an open question (keyed by pair_key, matching res.candidate_reasons).
    surviving_keys = {pair_key(a, b) for a, b in res.candidates}
    res.candidate_reasons = {k: v for k, v in res.candidate_reasons.items() if k in surviving_keys}

    # The retained `possible` watch-list (D4) survives the reset on the SAME rule as candidates — a pair
    # that later merged, was vetoed apart, or was promoted to a candidate is no longer merely "possible" —
    # and carries its identity confidence/breakdown through. Partition-only; nothing here is drawn.
    cand_set = set(res.candidates)
    possible_surv = {
        as_pair(p)
        for p in res.possible
        if uf.find(p[0]) != uf.find(p[1]) and as_pair(p) not in distinct and as_pair(p) not in cand_set
    }
    for a, b in sorted(possible_surv):
        key = pair_key(a, b)
        if key in raw_conf:
            res.merge_confidence[key] = raw_conf[key]
        if key in raw_bd:
            res.merge_breakdown[key] = raw_bd[key]
    res.possible = sorted(possible_surv)


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
