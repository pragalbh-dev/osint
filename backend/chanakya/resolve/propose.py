"""The offline, raise-only LLM candidate proposer (spine/03, spine/08 §3.11).

**Off the rebuild path.** This entrypoint runs *upstream* of the append (like INGEST's extractor): it
emits frozen, cited ``merge_proposal`` decision records that the deterministic ``rebuild()`` later
*consumes* as a raise-only signal. It is never called by ``resolve()`` — so ``rebuild()`` stays
LLM-free (gate G1). ``anthropic`` is imported **lazily inside** the call, so ``import chanakya.resolve``
succeeds even with ``anthropic`` patched-to-raise (the G1 structural companion).

**Selective invocation** (the LLM must earn its place): fire only on entities that are **(i)** a
high-alias-risk type (variant/component/unit/manufacturer, per config) **and (ii)** orphan/thin-block
(``deterministic_candidate_count < k``). One batched call per orphan; **budget cap**; **skips logged**.
Cost ≈ #orphan-risky-entities, not O(n²). The demo target is recovering one planted alias not in the
seed (H-200 → HT-233) — a candidate to *verify*, never an assumption: it is **raise-only** and
hard-clamped below auto-merge, so it can only ever reach the analyst's HITL queue.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Protocol

from chanakya.schemas import ClaimRecord, ConfigBundle, DecisionRecord, GraphView

from . import entities
from .entities import Entity, EntityGraph
from .normalize import tokens
from .rconfig import ResolveConfig


class LLMProposer(Protocol):
    """Injectable transport (mocked in tests). Returns the ids/names the orphan is proposed same-as."""

    def __call__(self, orphan: Entity, shortlist: list[Entity]) -> list[str]: ...


@dataclass
class ProposalRun:
    records: list[DecisionRecord] = field(default_factory=list)
    fired: list[str] = field(default_factory=list)  # orphan eids the LLM was called on
    skipped: list[str] = field(default_factory=list)  # eids skipped (not risky / not orphan / over budget)


def _deterministic_candidate_count(eid: str, graph: EntityGraph, cfg: ResolveConfig) -> int:
    """How many other entities share a deterministic block (name-token within type+ns, or hard-id) with e."""
    ent = graph.entities[eid]
    keys = set(cfg.blocking_keys)
    my_blocks: set[tuple] = set()
    etype = ent.etype if "type" in keys else ""
    ns = ent.namespace() if "country_or_domain_namespace" in keys else ""
    if "name_token" in keys:
        for tok in tokens(ent.name, cfg.transliteration):
            my_blocks.add(("nt", etype, ns, tok))
    for kind in ("unique", "categorical"):
        for attr in cfg.hard_id_fields(kind).get(ent.etype, []):
            v = ent.attrs.get(attr)
            if v is not None:
                my_blocks.add(("hid", attr, str(v)))

    others: set[str] = set()
    for other_id, other in graph.entities.items():
        if other_id == eid:
            continue
        o_etype = other.etype if "type" in keys else ""
        o_ns = other.namespace() if "country_or_domain_namespace" in keys else ""
        blocks: set[tuple] = set()
        if "name_token" in keys:
            for tok in tokens(other.name, cfg.transliteration):
                blocks.add(("nt", o_etype, o_ns, tok))
        for kind in ("unique", "categorical"):
            for attr in cfg.hard_id_fields(kind).get(other.etype, []):
                v = other.attrs.get(attr)
                if v is not None:
                    blocks.add(("hid", attr, str(v)))
        if my_blocks & blocks:
            others.add(other_id)
    return len(others)


def propose_candidates(
    claims: list[ClaimRecord],
    config: ConfigBundle,
    prev_view: GraphView | None = None,
    *,
    now: str,
    llm: LLMProposer,
) -> ProposalRun:
    """Run the gated, raise-only proposer over orphan high-alias-risk entities. ``llm`` is injectable."""
    cfg = ResolveConfig.from_bundle(config)
    graph = entities.build(claims)
    run = ProposalRun()

    risky = cfg.high_alias_risk_types
    k = cfg.orphan_block_threshold_k
    budget = cfg.llm_candidate_gen.get("max_calls_per_rebuild")
    if not risky or k is None:
        return run  # not configured → the proposer stays dormant (no code default)

    calls = 0
    for eid in sorted(graph.entities):
        ent = graph.entities[eid]
        if ent.etype not in risky:
            run.skipped.append(eid)
            continue
        if _deterministic_candidate_count(eid, graph, cfg) >= k:
            run.skipped.append(eid)  # well-covered by deterministic blocking → LLM adds nothing
            continue
        if budget is not None and calls >= int(budget):
            run.skipped.append(eid)  # budget exhausted (logged, not silently dropped)
            continue

        shortlist = [graph.entities[o] for o in sorted(graph.entities) if o != eid]
        proposed = llm(ent, shortlist)
        calls += 1
        run.fired.append(eid)
        for target in proposed:
            run.records.append(_proposal_record(ent, target, now, event_index=len(run.records)))
    return run


def _proposal_record(orphan: Entity, target: str, now: str, event_index: int) -> DecisionRecord:
    """A frozen, cited, raise-only merge_proposal (consumed by resolve() → HITL band, never auto)."""
    context: dict[str, Any] = {
        "pair": [orphan.eid, target],
        "orphan_name": orphan.name,
        "cited_claims": sorted(orphan.claim_ids),
        "raise_only": True,
    }
    return DecisionRecord(
        event_id=f"mp:{orphan.eid}:{event_index}",
        ts=now,
        actor="agent",
        stage="resolution",
        type="merge_proposal",
        subject_ref=orphan.eid,
        context=context,
        decision={"pair": [orphan.eid, target], "raise_only": True},
    )


def by_block(graph: EntityGraph) -> dict[str, list[str]]:
    """Debug helper: entity ids grouped by type (used in tests/inspection)."""
    out: dict[str, list[str]] = defaultdict(list)
    for eid, ent in graph.entities.items():
        out[ent.etype].append(eid)
    return out
