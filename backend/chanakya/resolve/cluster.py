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
from typing import Any

from chanakya.schemas import pair_key

from .aliases import AliasIndex
from .entities import Entity, EntityGraph, as_pair, namespace_compatible, unordered_pairs
from .normalize import normalize, tokens
from .rconfig import (
    ATTRIBUTE,
    BAND_POSSIBLE,
    BAND_PROBABLE,
    DISCRIMINATOR,
    NAME,
    RELATIONAL,
    SIGNALS,
    SOURCE_ASSERTED,
    TEMPORAL,
    ResolveConfig,
    ceiling_withholds,
)
from .scoring import (
    _shared_unique_id,
    agreeing_discriminators,
    co_instances,
    geo_conflict_km,
    has_durable_identity_support,
    merge_score,
    shared_neighbour_predicates,
)

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
    # pair_key → the analyst-facing reason a HARD WALL holds this pair apart (G18/S3). A wall built the
    # geo-veto way would be non-transitive AND invisible while the gate still passed, which is the failure
    # §5a was written to stop — so a wall this stage adds must both join ``veto`` (hard + transitive +
    # drawn) and say WHY, on the drawn edge, in words an analyst can act on.
    wall_reasons: dict[str, str] = field(default_factory=dict)
    # pair_key → what is MISSING before the identity of a pair the evidence otherwise fused can be settled
    # (G19). The escalate half of the non-negotiable for a refusal that reaches nobody otherwise: the
    # cross-type wall un-fuses a pair and then routes *neither* half anywhere — both mentions end up with no
    # edge between them and, before this, no gap record either, which is indistinguishable from the two
    # never having looked alike. ``rebuild()`` renders one Known Gap **per endpoint** so each node says, in
    # its own drawer, what could not be decided about it and what would settle it.
    identity_refusals: dict[str, str] = field(default_factory=dict)
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

    The test is on the NAME sub-signal, never on the fused ``attribute`` term — and that is a correction,
    not a refinement. Fused, ``attribute`` is ``max(name, discriminator)``, so a pair agreeing on a declared
    *discriminator* and nothing else read as "name alone" and was capped out of the analyst's queue, while a
    pair with a strong name and a weak-but-present discriminator read the same as a bare coincidence. The cap
    was firing on the wrong pairs in both directions. ``merge_score`` always records the split, so there is
    one test and no fused fallback to fall through to.
    """
    return bd[NAME] > 0 and bd[DISCRIMINATOR] == 0 and bd[RELATIONAL] == 0 and bd[SOURCE_ASSERTED] == 0


# ── the Phase-1 bootstrap triggers, NAMED (S3 item 10 / review §4) ───────────────────────────────
#
# The bootstrap disjunction merges at a hardcoded 1.0 and **bypasses banding entirely**, so no cap
# restrains it. The review's finding: *name is a verdict in Phase 1 at every type, and the caps exist only
# in Phase 2* — the widest fusion path in the system is the one nothing guards, and it never reaches
# ``confirm_is_durable`` at all. Naming each trigger is what lets the caps bind the disjunction rather than
# only the collection loop (R1.2/R3.1/R3.2).
TRIGGER_UNIQUE_ID = "shared-unique-identifier"
TRIGGER_ALIAS = "alias-equivalence"
TRIGGER_EXACT_NAME = "exact-normalised-name"
TRIGGER_CONTAINMENT = "name-containment-or-acronym"
TRIGGER_COREF = "authoritative-coreference"
TRIGGER_PLACE = "curated-gazetteer-anchor"
#: The triggers that are *nothing but a name*. D-13.20 puts name at the bottom of the discriminator ladder,
#: ceiling ``possible``.
NAME_TRIGGERS = frozenset({TRIGGER_EXACT_NAME, TRIGGER_CONTAINMENT})
#: The triggers the name cap does **not** touch, because none of them is a name coincidence: a shared unique
#: identifier is the top of the ladder; an ALIAS link is a curated (or analyst-accepted) *statement* of
#: equivalence one rung up from a string match — and the mechanism by which an analyst's earned merge sticks
#: across rebuilds; an authoritative coref bind has passed its own deterministic gate and grade floor.
#: Everything else — including the Phase-2 fuzzy path, which has no trigger at all — is capped. That last
#: clause is D3: the cap used to be consulted **only** in the post-fixpoint collection loop, so the Phase-2
#: fixpoint that actually unions never saw it, and a near-identical name auto-merged at a lowered per-type
#: floor without anything else agreeing.
EARNED_TRIGGERS = frozenset({TRIGGER_UNIQUE_ID, TRIGGER_ALIAS, TRIGGER_COREF, TRIGGER_PLACE})


def _name_cap_reason(trigger: str | None, ceiling: str) -> str:
    """Analyst-facing rationale for a name-only pair the cap withheld from FUSION (D-13.10, S3 item 10).

    Prose only — no threshold, no code literal (gate G6). Distinct wording from every other reason in this
    module because it is a distinct question: not "a critical attribute disagrees" and not "a wall is in the
    way", but "the only thing saying these are one entity is what they are called".
    """
    how = trigger or "similarity of the two names"
    return (
        f"name-only identity, capped at '{ceiling}' — the sole line of evidence joining this pair is the "
        f"{how}: the two sides share no neighbour, no stated discriminator and no source assertion of "
        f"identity. Designations and organisation names are reused across armies and across time, so a name "
        f"match is recall evidence, not a verdict. ONE more trivially-available signal (a shared neighbour, "
        f"an agreeing stated attribute, a source saying so) clears the cap; until then the merge is withheld "
        f"and the link is retained for the analyst rather than asserted (D-13.10)."
    )


def _colocation_cap_reason(
    shared: tuple[str, ...], discriminators: tuple[str, ...], ceiling: str
) -> str:
    """Analyst-facing rationale for a formation merge the co-location cap withheld (D-13.14 / G16).

    Says what would lift it, because the cap is not a refusal to decide — it is a statement of *what is
    missing*. Prose only (gate G6).

    ``ceiling`` is the band the caller ACTUALLY applied, threaded in rather than assumed. It used to be the
    literal ``BAND_PROBABLE``, so an operator who declared ``colocation_ceiling: possible`` — a legal value
    this reader honours — got a pair on the watch-list whose own stated rationale said it was in the review
    queue. Two costs, both of them the analyst's:

    * the surfaced reason disagreed with the decision the system computed, which is exactly the defect the
      "a reason must name its real ground" property exists to catch, wearing the clothes of a specific reason;
    * ``probable`` and ``possible`` produced the *identical* rationale, so the one channel that tells an
      analyst how much attention a pair has earned said nothing — a fixed default with three legal spellings.

    The sibling :func:`_name_cap_reason` always took its ceiling as an argument; this one did not, and that
    asymmetry is how the hard-coded band survived the ``ceiling_withholds`` fix one layer down.
    """
    on = ", ".join(shared) if shared else "a shared design, site and operator"
    want = ", ".join(discriminators) if discriminators else "a unit-level identifier"
    return (
        f"co-location is not identity, capped at '{ceiling}' — everything these two formations agree "
        f"on is where they are standing ({on}). Two batteries at one airfield, running one design, under one "
        f"branch share all of that BY CONSTRUCTION, so the shared neighbourhood is evidence of dispersal, "
        f"not of identity. Confirming a FORMATION needs a unit-level discriminator ({want}); none is stated "
        f"on both sides. The merge is withheld — and deliberately so: `based-at` is functional and "
        f"unit-keyed, so fusing these two would make their two sites one unit's before-and-after, the "
        f"supersede path would then DRAW a relocation nobody reported, pop the pair out of this queue as "
        f"'machine-adjudicated', and delete the retired edge's Known Gap. A presence-level merge is a "
        f"different and weaker claim, and is not capped here (D-13.14)."
    )


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
    # C7: the namespace BLOCKING key is normalised too, not only the wall's comparison. Normalising at
    # conflict time alone would fix the wall and leave the blocking split — 'PAF' and 'Pakistan Air Force'
    # in two different blocks — which is the half of D4 the remedy would otherwise have missed.
    nsn = cfg.namespace_normaliser

    def add(block: tuple, eid: str) -> None:
        blocks.setdefault(block, set()).add(eid)

    for eid, ent in graph.entities.items():
        etype = ent.etype if "type" in keys else ""
        ns = ent.namespace(nsn) if "country_or_domain_namespace" in keys else ""
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
        # D-13.20's composite AND-keys block on the whole tuple of values, so two records sharing a
        # designation but not a branch never land in one block — the same asymmetry the decision rests on,
        # applied to recall as well as to the verdict. A key with any component unstated blocks on nothing.
        for key in cfg.unique_id_keys(ent.etype):
            values = [ent.attrs.get(attr) for attr in key]
            if all(v is not None for v in values):
                add(("hidk", key, tuple(str(v) for v in values)), eid)

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
        ) or _name_containment(graph.entities[a], graph.entities[b], cfg, toks, nsn):
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


def _name_containment(
    a: Entity, b: Entity, cfg: ResolveConfig, toks: dict[str, list[str]], normalise: Any = None
) -> bool:
    """High-precision open-world name equivalence: containment or acronym, same type + namespace.

    The registry (P3.0) pre-resolves every surface form we have *already seen*; this is the tail it has
    never seen — a document naming the same thing more verbosely, or by its initials. Type + namespace
    gated, and (in the bootstrap) veto-gated like every other merge, so it can never fuse a trap pair.

    Note it is consulted **twice**: once to *generate* the candidate pair (an acronym shares no name token
    with its expansion, so ordinary blocking would never propose "PAAD" against "Pakistan Army Air
    Defence"), and again to *decide* the bootstrap merge.
    """
    if a.etype != b.etype or not namespace_compatible(a, b, normalise):
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
    raise_ceilings: Mapping[Pair, str] | None = None,
    place_identity: set[Pair] | None = None,
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

    ``raise_ceilings`` says, per raise-wall pair, WHICH band that channel's caller declared — the band the
    pair may reach, not the fact that it is blocked. An unlisted pair means ``probable``, which is the
    channel's original and still-dominant promise (a stated critical disagreement is the analyst's call, so
    it is guaranteed a queue place).

    It exists because one rail on this channel carries a **configured** ceiling rather than a fixed one. A
    same-document stated contrast is a *cap* — its own analyst-facing reason literally says "Capped at
    '<contrast_ceiling>'" — but the channel was band-blind, so an operator who declared
    ``contrast_ceiling: possible`` got a pair in the review QUEUE whose rationale told the analyst it was on
    the watch-list. That is the surfaced reason disagreeing with the computed decision, and it made
    ``possible`` and ``probable`` behave identically on that dial: a declared value that does not mean what
    it says, which is the same defect class as the truthiness read of ``ceiling_withholds`` one layer down.

    The ceiling is honoured for the *band* only. Blocking bootstrap and auto-merge is unconditional on this
    channel and stays that way, because that half is not a matter of how much attention a pair has earned.
    """
    authoritative = authoritative or set()
    raise_walls = raise_walls or {}
    raise_ceilings = raise_ceilings or {}
    # RK-COREF item 11: place identity decided BEFORE the fixpoint (``places.place_merge_pairs``) so a place
    # merge is visible to ``relational_score``. Its own bootstrap channel rather than folded into
    # ``authoritative``, because labelling a curated-gazetteer anchor "authoritative coreference" in an
    # analyst-facing reason would be a lie about where the evidence came from.
    place_identity = place_identity or set()
    res = ResolveResult()
    if not cfg.scorable:
        return res  # no bands configured ⇒ inert (identity partition) — no code literal needed

    eids = sorted(graph.entities)
    uf = _UnionFind(eids)
    trans = cfg.transliteration
    toks = _token_index(graph, cfg)
    pairs = sorted(
        tuple(sorted(p))
        for p in _candidate_pairs(
            graph, cfg, alias_idx, raise_only | authoritative | place_identity | set(raise_walls), toks
        )
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

    nsn = cfg.namespace_normaliser  # C7: fold 'PAF' ≡ 'Pakistan Air Force' BEFORE it becomes a namespace key
    earned = cfg.earned_identity

    def bootstrap_trigger(a: str, b: str) -> str | None:
        """Which Phase-1 trigger licenses this pair — **named** — or ``None``.

        Exactly the historic disjunction, unchanged in membership and in order; naming the winner is what
        lets a cap bind the bootstrap (review §4: *name is a verdict in Phase 1 at every type, and the caps
        exist only in Phase 2*). Flag off ⇒ the caller only asks "is it non-None", i.e. the old ``if`` (G2).
        """
        ea, eb = graph.entities[a], graph.entities[b]
        na, nb = normalize(ea.name, trans), normalize(eb.name, trans)
        pair = frozenset((a, b))
        # ORDERED BY LADDER STRENGTH, and the order is load-bearing — not cosmetic. The disjunction returns
        # the FIRST match, and the caps then read the trigger to decide whether the pair is "nothing but a
        # name". Checked name-first (as it originally was), a pair the document *authoritatively co-refers*
        # was reported as a name-containment match whenever a name rule happened to fire too — so the name
        # cap withheld a merge that coreference had earned, and the whole auto-bind policy went silently
        # inert. (Measured: "Alpha Precision Machinery" / "APM" is an acronym expansion AND an explicit
        # equivalence; the acronym rule won the race and the bind never happened.) A pair licensed by a
        # stronger rung must be reported at that rung, so the strongest is tested first.
        if _shared_unique_id(ea, eb, cfg):
            return TRIGGER_UNIQUE_ID
        # The document itself stated this equivalence in a quotable span, and the pair cleared the
        # veto/type/namespace/contradiction/grade gates upstream — evidence no string comparison can reach.
        if pair in authoritative:
            return TRIGGER_COREF
        if pair in place_identity:
            return TRIGGER_PLACE
        if alias_idx.equivalent(na, nb):
            return TRIGGER_ALIAS
        if bool(na) and na == nb and ea.namespace(nsn) == eb.namespace(nsn):
            return TRIGGER_EXACT_NAME
        if _name_containment(ea, eb, cfg, toks, nsn):
            return TRIGGER_CONTAINMENT
        return None

    def cross_namespace_or_type(a: str, b: str) -> tuple[str, str, str] | None:
        """G19: is this pair unfusable on TYPE or NAMESPACE? ``(ceiling, reason, what_missing)`` or ``None``.

        The single most dangerous over-merge class for an operator-scoped order of battle, and it was guarded
        nowhere that mattered: ``namespace_compatible`` gated only the bootstrap's exact-name branch,
        ``_name_containment``, ``_identity_pairs`` and ``_coref_pairs`` — **never the Phase-2 fuzzy
        fixpoint** — and relational blocking emits pairs with no namespace key at all, so a PLA-side and a
        PAF-side instance could be scored and auto-merged. Cross-type was only ever a *skip in candidate
        collection*, so the bootstrap could fuse a component into a variant on an identical name. The whole
        refusal then sat behind a staging flag that shipped off, which is how two same-named, coref-linked
        trading orgs whose stated ``origin_country`` was CHINA on one side and Pakistan on the other fused at
        ``confirmed`` in the shipped build.

        A hard **precondition on the fusion path** in BOTH phases (R3.1), never a score contributor — and
        deliberately not a *veto*: two things in different namespaces are not a do-not-merge *finding* to
        draw, they are simply not fusable, and a source or proposer that explicitly asserts the identity still
        reaches the analyst through the existing cross-type escape hatch.

        **The two halves get different ceilings, and the asymmetry is deliberate.** A type mismatch is not a
        merge question: T3b-A decided that asking an analyst whether an air-defence *sector* is the same thing
        as an air-defence *centre* "is not triage, it is noise", and that stands — the fusion closes and the
        merge queue does not change. A namespace mismatch between two entities of the SAME type is the
        opposite: a PLA-side and a PAF-side unit that look alike is precisely the adversarial conflation an
        analyst must see, so it caps at ``probable`` **with the reason**.

        **Both halves owe a NAMED GAP, and that is the third element.** The ceiling is only the refuse-to-
        assert half. The escalate half was missing outright on the cross-type side: the wall un-fused the pair
        and routed neither mention anywhere — no edge, no queue item, no gap — which reads exactly like two
        mentions that never resembled each other. ``what_missing`` is what the analyst is owed instead, and
        :func:`fusion_blocked` records it only where the evidence *otherwise fused the pair*, so a low-scoring
        cross-type coincidence still earns nothing (T3b-A's noise argument, intact).
        """
        ea, eb = graph.entities[a], graph.entities[b]
        if ea.etype != eb.etype:
            return BAND_POSSIBLE, (
                f"not fusable: cross-type ({ea.etype} vs {eb.etype}). Two entities of different ontology "
                f"types are not one entity however alike their names look — and this used to be only a "
                f"*skip* in candidate collection, so the Phase-1 bootstrap could still fuse them on an "
                f"identical name (G19)."
            ), (
                f"the entity TYPE of this mention is contradicted: the evidence otherwise says it is the "
                f"same thing as '{b if a == ea.eid else a}', but the two are typed '{ea.etype}' and "
                f"'{eb.etype}' by different sources. Two sources disagreeing about what kind of thing this "
                f"is is an evidentiary contradiction, not a merge decision — fusing them would assert a type "
                f"neither source states, and dropping the resemblance silently would hide the disagreement. "
                f"Needed: a source that states the type unambiguously, or an analyst adjudication of which "
                f"typing is right; the identity cannot be settled before that (G19)"
            )
        if not namespace_compatible(ea, eb, nsn):
            return BAND_PROBABLE, (
                f"not fusable: cross-namespace ({ea.namespace(nsn)} vs {eb.namespace(nsn)}). These two "
                f"profiles are scoped to different operators, and for an operator-scoped order of battle a "
                f"cross-operator fusion is the costliest over-merge there is — it silently moves an asset "
                f"from one army to another. The merge is refused; the resemblance is real and is raised, "
                f"because a look-alike straddling two operators is either an extraction error or deliberate "
                f"conflation, and both are the analyst's call (G19)."
            ), (
                f"the OPERATOR scope of this mention is contradicted: the evidence otherwise says it is the "
                f"same thing as '{b if a == ea.eid else a}', but the two are scoped to "
                f"'{ea.namespace(nsn)}' and '{eb.namespace(nsn)}'. The merge is refused and the pair is in "
                f"the review queue. Needed: a source that states one operator for both mentions, or an "
                f"analyst adjudication — until then this profile's operator is an open question (G19)"
            )
        return None

    def colocation_only(a: str, b: str, bd: dict[str, float]) -> tuple[str, ...] | None:
        """D-13.14/G16: the shared predicates, when a FORMATION pair agrees on nothing but co-location.

        ``None`` ⇒ the cap does not apply (not a formation pair, or a unit-level discriminator agrees, or
        the pair has some non-co-location evidence). A tuple ⇒ the cap applies and these are the shared
        predicates to name. Presence types are deliberately outside the cap: a presence-level merge in the
        same case is *expected* (C2), because a presence asserts only "this kit was seen here", which is
        exactly what two co-located reports do corroborate.
        """
        ea, eb = graph.entities[a], graph.entities[b]
        # The presence exemption, read from the key that CLAIMS to grant it. ``presence_types`` documents
        # itself as "the two citizens S2 created. A presence-level merge in a co-location case is EXPECTED and
        # must not be capped", and nothing read it: the exemption fell out of presence types not appearing in
        # ``formation_types``, i.e. it was granted by a *different* key's contents. That is a dial with a label
        # and no shaft, and it is fragile in the direction that matters — the day an operator adds a presence
        # type to ``formation_types`` (to cap something else) the documented exemption vanishes silently and
        # co-located sightings of one design start capping each other. Stated explicitly, it holds either way.
        if ea.etype in earned.presence_types or eb.etype in earned.presence_types:
            return None
        if ea.etype not in earned.formation_types or eb.etype not in earned.formation_types:
            return None
        if bd[RELATIONAL] <= 0.0:
            return None  # nothing shared ⇒ nothing for co-location to explain
        shared = shared_neighbour_predicates(graph, a, b, uf.find, co_instances(graph, a, b))
        if not shared or not shared.issubset(set(earned.colocation_predicates)):
            return None  # some shared link is NOT a co-location link ⇒ real relational evidence
        if _shared_unique_id(ea, eb, cfg):
            return None  # the ladder's TOP rung — a shared COMPLETE composite AND-key lifts every cap
        if agreeing_discriminators(ea, eb, earned.formation_discriminators, cfg):
            return None  # a unit-level discriminator agrees ⇒ more than co-location ⇒ the cap lifts
        return tuple(sorted(shared))

    def fusion_blocked(
        a: str, b: str, bd: dict[str, float], trigger: str | None, *, would_fuse: bool
    ) -> tuple[str, str] | None:
        """The ONE fusion precondition both phases consult — ``(ceiling, reason)`` or ``None`` (R3.1).

        A hard precondition on the fusion path, never a positive whitelist of triggers: D-13.9 specifies a
        **graded** path constrained by guards, and converting a negative cap into a whitelist changes the
        system in both directions (it is what made designs unable to collapse at all in the spike). So every
        pair still earns its way up the ordinary scored path; this only says which pairs may not cross the
        *fusion* line, and at what ceiling they stop.

        Ceiling ``possible`` ⇒ withheld from the analyst's queue as well (it has not earned attention), but
        **retained with its reason** on the watch-list. Ceiling ``probable`` ⇒ withheld from fusion but
        GUARANTEED a queue place with this reason — the analyst is exactly who should decide. Ceiling
        ``confirmed`` ⇒ the declared cap permits the fusion and does not fire at all: a ceiling's value means
        what it says (:func:`~chanakya.resolve.rconfig.ceiling_withholds`), where it used to be read as a
        truthiness test that made ``confirmed`` behave exactly like ``probable``.

        ``would_fuse`` says whether the evidence *otherwise* fused this pair — a Phase-1 bootstrap trigger
        fired, or the Phase-2 score reached the auto band. It is what makes an identity **refusal gap** a
        finding rather than noise: a pair the evidence says is one thing, refused by a type or namespace
        contradiction, is an evidentiary contradiction the analyst must be told about; a low-scoring cross-type
        coincidence is not.
        """
        incompatible = cross_namespace_or_type(a, b)
        if incompatible is not None:
            ceiling, reason, what_missing = incompatible
            if would_fuse:
                res.identity_refusals[pair_key(a, b)] = what_missing
            return ceiling, reason
        if (
            ceiling_withholds(earned.name_ceiling)
            and trigger not in EARNED_TRIGGERS
            and _name_alone(bd)
        ):
            return earned.name_ceiling, _name_cap_reason(trigger, earned.name_ceiling)
        if ceiling_withholds(earned.colocation_ceiling):
            shared = colocation_only(a, b, bd)
            if shared is not None:
                return earned.colocation_ceiling, _colocation_cap_reason(
                    shared, earned.formation_discriminators, earned.colocation_ceiling
                )
        return None

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

    # S3: pairs a CAP refused fusion to, at ceiling ``probable`` — the same block-merge-and-review contract
    # as ``perishable_capped`` and ``raise_walls`` (the third and fourth instances of one proven shape, not
    # new machinery). Ceiling ``possible`` pairs are recorded separately: those have not earned attention.
    capped_probable: dict[Pair, str] = {}
    capped_possible: dict[Pair, str] = {}

    def record_cap(pair: Pair, ceiling: str, reason: str) -> None:
        if ceiling == BAND_POSSIBLE:
            capped_possible[pair] = reason
            capped_probable.pop(pair, None)
        else:
            capped_probable[pair] = reason
            capped_possible.pop(pair, None)

    def clear_cap(pair: Pair) -> None:
        """A pair that EARNED its way out of a cap is no longer capped — re-decided every pass, like the
        perishable cap, because the relational term is partition-dependent and a cap must never be pinned."""
        capped_probable.pop(pair, None)
        capped_possible.pop(pair, None)

    # ── Phase 1: high-precision bootstrap (no relational term) ────────────────────────────────
    for a, b in pairs:
        if uf.find(a) == uf.find(b) or vetoed(a, b) or violates_veto_transitively(a, b):
            continue
        if frozenset((a, b)) in raise_walls:
            continue  # a below-floor critical conflict may not bootstrap-merge — it is raised to HITL
        trigger = bootstrap_trigger(a, b)
        if trigger is None:
            continue
        ea, eb = graph.entities[a], graph.entities[b]
        bd = merge_score(ea, eb, graph, uf.find, cfg, alias_idx, pair_confidence=pair_confidence)
        # S3 (review §4, R1.2/R3.1/R3.2): the caps bind the BOOTSTRAP DISJUNCTION, not merely the Phase-2
        # collection loop. A bootstrap merge lands at a hardcoded 1.0 and never touches ``_band``, so a cap
        # that lives downstream of banding is a cap on a path this one does not take. A blocked pair is not
        # discarded — it falls through to the scored path and is banded on its merits, which is what makes
        # this a cap and not a ban. Flag off ⇒ ``fusion_blocked`` is always None (byte-unchanged, gate G2).
        # ``would_fuse=True``: reaching here means the bootstrap disjunction licensed this fusion, so a
        # type/namespace refusal below is a contradiction between the evidence and the schema, not noise.
        blocked = fusion_blocked(a, b, bd, trigger, would_fuse=True)
        if blocked is not None:
            record_cap(frozenset((a, b)), *blocked)
            continue
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
            auto = _band(bd, cfg, has_raise=False, auto_merge=floor) == "auto"
            # The same precondition Phase 1 consults, on the loop that ACTUALLY UNIONS (D3/D4). Re-decided
            # every pass: a pair can earn its way out of the name cap as clusters grow and it gains a shared
            # neighbour, exactly as it can earn durable support out of the perishable cap.
            blocked = fusion_blocked(a, b, bd, None, would_fuse=auto)
            if blocked is not None:
                record_cap(frozenset((a, b)), *blocked)
                continue
            clear_cap(frozenset((a, b)))
            if auto:
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
            and frozenset((a, b)) not in capped_probable
        ):
            continue
        bd = merge_score(
            graph.entities[a], graph.entities[b], graph, uf.find, cfg, alias_idx,
            pair_confidence=pair_confidence,
        )
        floor = cfg.auto_merge_for_pair(graph.entities[a].etype, graph.entities[b].etype)
        has_raise = frozenset((a, b)) in raise_only
        raised_wall = frozenset((a, b)) in raise_walls
        # …and at which band. A raise-wall pair earns a QUEUE place unless its caller declared the ceiling
        # ``possible``, in which case it earns the watch-list instead — with its reason either way. Unlisted
        # ⇒ ``probable`` ⇒ ``raised_wall_queued`` is exactly the old ``raised_wall``, so every rail that does
        # not declare a ceiling (and the shipped ``contrast_ceiling: probable``) is byte-unchanged.
        raised_wall_poss = raised_wall and raise_ceilings.get(frozenset((a, b))) == BAND_POSSIBLE
        raised_wall_queued = raised_wall and not raised_wall_poss
        capped_perishable = frozenset((a, b)) in perishable_capped
        # S3: a cap that refused FUSION at ceiling ``probable`` is guaranteed a queue place with its reason —
        # the third instance of the block-merge-and-review contract. A cap at ceiling ``possible`` is the
        # opposite promise: it has not earned attention, so it is withheld from the queue and retained on the
        # watch-list (the ``name_alone`` shape). Both empty with the flag off (gate G2).
        capped_prob = frozenset((a, b)) in capped_probable
        capped_poss = frozenset((a, b)) in capped_possible
        band = _band(
            bd, cfg,
            has_raise=has_raise or raised_wall_queued or capped_perishable or capped_prob,
            auto_merge=floor,
        )
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
        # ``raised_wall_queued`` rather than ``raised_wall``: a raise-wall pair whose caller declared the
        # ceiling ``possible`` is *asking* to be withheld from the queue, so it must not also be listed as an
        # exemption from being withheld — that reading is what made the two bands identical on that dial.
        capped = (
            cfg.name_alone_caps_at_possible
            and not (has_raise or raised_wall_queued or is_bridge or capped_perishable or capped_prob)
            and _name_alone(bd)
        ) or ((capped_poss or raised_wall_poss) and not (has_raise or raised_wall_queued or is_bridge))
        # EVERY pair reaching this loop was refused a merge upstream — Phase 1 and Phase 2 already ran and did
        # not union it — so an "auto" band here never means "merge it", it means "something blocked it". Unless
        # a cap has explicitly withheld it from the queue, that makes it a REVIEW ITEM, and it must not fall
        # through to the watch-list.
        #
        # This replaces an enumeration of three specific blockers (a below-floor critical conflict, a
        # perishable-only confirm, an S3 probable-cap), and the enumeration is what produced the bug: a
        # ``NAME_VARIANT`` cluster — raise-only *permanently*, whose whole justification is that the analyst
        # receives it WITH the licensing quote — scored into the auto band, matched none of the three, and
        # landed in ``possible``. Retained but never surfaced, i.e. raise-only had become a quiet drop rather
        # than a referral. Deriving the demotion from "was it capped?" cannot go stale as blockers are added.
        # …with one exception, and it is a deliberate operator choice rather than a gap: a pair refused ONLY
        # by the transitive wall is a D9 *bridge*, and an operator may switch that alarm off
        # (``surface_wall_bridges: false``) to revert to the pre-D9 silent non-merge. Suppressed means
        # suppressed — promoting it here would re-surface the alarm the operator turned off.
        suppressed_bridge = not cfg.surface_wall_bridges and violates_veto_transitively(a, b)
        if band == "auto" and not capped and not suppressed_bridge:
            band = "hitl"
        pfloor = cfg.possible_floor
        # WHY the pair is here, computed ONCE for both tiers. It used to be written only on the ``hitl``
        # branch, so a pair a cap withheld at ceiling ``possible`` was retained with its confidence and its
        # breakdown and **without its reason** — and for a type whose only honest identity signal is its name
        # (``area_of_operations``) that is the common case, not an edge case. A retained link nobody can read
        # the grounds for is a quiet drop: the analyst gets a number and never the quote. Reason precedence: a
        # below-floor critical conflict (its own stated disagreement) first, then a perishable-only capped
        # confirm (Stage 3B-iii), then a cap that refused fusion, then the cluster-level D9 bridge alarm.
        pair = frozenset((a, b))
        if raised_wall:
            reason = raise_walls[pair]
        elif capped_perishable:
            reason = perishable_capped[pair]
        elif capped_prob:
            reason = capped_probable[pair]
        elif capped_poss:
            reason = capped_possible[pair]
        elif is_bridge and wall is not None:
            reason = _bridge_reason(wall)
        else:
            reason = ""
        if band == "hitl" and not capped:
            res.candidates.append((a, b))
            res.merge_confidence[pair_key(a, b)] = bd["total"]
            res.merge_breakdown[pair_key(a, b)] = bd
            if reason:
                res.candidate_reasons[pair_key(a, b)] = reason
        # The retained `possible` watch-list (D4): a scored pair in [possible_floor, hitl_low) that would
        # otherwise be dropped as `separate`, PLUS any pair a cap withheld from the queue. Kept with its
        # identity confidence/breakdown AND its reason; Partition-only (never drawn — see view/pipeline).
        #
        # A CAPPED pair is retained irrespective of ``possible_floor``: the cap is a stated decision about a
        # pair the machinery had an opinion on, not a low score, so letting it fall through the floor would
        # discard the decision and the reason with it. Absent floor + no cap ⇒ the pair drops as before.
        elif capped or (pfloor is not None and bd["total"] >= pfloor):
            res.possible.append((a, b))
            res.merge_confidence[pair_key(a, b)] = bd["total"]
            res.merge_breakdown[pair_key(a, b)] = bd
            if reason:
                res.candidate_reasons[pair_key(a, b)] = reason

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
    # Carry a reason only for links that survived the reset — a raised pair that later merged or was vetoed
    # apart is no longer an open question (keyed by pair_key, matching res.candidate_reasons).
    surviving_keys = {pair_key(a, b) for a, b in res.candidates}

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
    # …and the retained ``possible`` tier is included in that survival set. Filtering the reasons on the
    # candidate queue alone deleted every reason a cap had just written for a withheld pair — the pair was
    # retained, its reason was not, which is the "quiet drop" this tier exists to avoid.
    surviving_keys |= {pair_key(a, b) for a, b in res.possible}
    res.candidate_reasons = {k: v for k, v in res.candidate_reasons.items() if k in surviving_keys}
    # An identity refusal that no longer holds two mentions apart is moot: if the endpoints ended up in one
    # cluster along some other chain there is nothing left to escalate.
    def _still_apart(key: str) -> bool:
        a, _sep, b = key.partition("|")
        return bool(b) and uf.find(a) != uf.find(b)

    res.identity_refusals = {
        key: what for key, what in res.identity_refusals.items() if _still_apart(key)
    }


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
