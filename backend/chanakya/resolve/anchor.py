"""View-level anchor resolution for a subject lens — the sibling of ``resolve._matching_eids``.

A subject is a *query-time lens* (spine/01): it centres on **anchor ids** and traverses outward. But an
anchor declared in ``config/subjects.yaml`` is a *config string* — a stable entity id in the common case,
or (after an alias/spelling drift, a hand-authored lens, or a subject picker that passes a surface form) a
name no view node carries verbatim. Mapping that string to the node the analyst *meant* is the same
problem RESOLVE already solves for claim endpoints, so this reuses the **same** machinery — ``normalize``
+ the seeded/registry ``AliasIndex`` + the entity registry — rather than a second, divergent normaliser.
One resolver serves the lens (``view/lens.py``) and the observable watch-scope (``observe/observable.py``),
killing the "lens silently empties / observable watches everything" divergence.

The ladder stops at the first hit, most-certain first:

1. **literal** — the anchor is already a node id in the view (the post-RESOLVE common case);
2. **registry_alias** — the anchor is a registry ``entity_id`` whose canonical_name/aliases match a view
   node's name (+ its ``attrs["aliases"]``), **type-gated** by the registry entry's type — so
   ``site_karachi`` can only bind a ``basing_site``, never a same-named unit;
3. **alias_index** — the anchor's normalised form is alias-equivalent (seeded ∪ registry classes) to a
   view node's name.

A miss is **named, not swallowed**: an anchor that resolves to nothing is returned with ``node_id=None``
so the lens can say "insufficient evidence to scope — anchor X is not in this view" instead of returning a
bare empty graph (the "name what's missing" non-negotiable applied to scoping).

Pure + offline (no clock/RNG/LLM): safe on the rebuild/view path (gate G1). ``config=None`` degrades
gracefully to tier 1 only — exactly today's literal-membership behaviour, byte-for-byte (gate G2).
"""

from __future__ import annotations

from dataclasses import dataclass

from chanakya.schemas import ConfigBundle, EntityEntry, GraphView

from . import aliases
from .aliases import AliasIndex
from .normalize import normalize

LITERAL = "literal"
REGISTRY_ALIAS = "registry_alias"
ALIAS_INDEX = "alias_index"


@dataclass(frozen=True)
class AnchorResolution:
    """How one requested anchor mapped to a view node. ``node_id``/``via`` are ``None`` on a miss."""

    requested: str
    node_id: str | None
    via: str | None  # LITERAL | REGISTRY_ALIAS | ALIAS_INDEX | None


def resolve_anchors(
    anchors: list[str], view: GraphView, config: ConfigBundle | None
) -> list[AnchorResolution]:
    """Resolve each subject anchor to a view node id via the ladder; misses are reported, never dropped.

    Deterministic: candidates are scanned in view-node order, so a form matching two nodes always binds the
    same one. Builds the shared ``AliasIndex`` (seeded ∪ registry classes) **once** for the whole batch.
    """
    node_ids = {n.id for n in view.nodes}
    rules = dict(config.resolution.transliteration) if config is not None else {}

    registry: dict[str, EntityEntry]
    if config is not None:
        alias_idx = aliases.build(
            config.resolution.alias_table,
            config.resolution.transliteration,
            None,
            {e.canonical_name: list(e.aliases) for e in config.entities.entities if e.aliases},
        )
        registry = config.entities.as_map()
    else:
        alias_idx = AliasIndex()  # inert: tier 2/3 need config, so config=None ⇒ tier 1 only
        registry = {}

    # node id → (type, {normalised name/alias forms}); computed once, view order preserved for determinism.
    node_forms: list[tuple[str, str, set[str]]] = []
    for n in view.nodes:
        forms = set()
        if n.name:
            forms.add(normalize(n.name, rules))
        for a in n.attrs.get("aliases", []) or []:
            forms.add(normalize(str(a), rules))
        node_forms.append((n.id, n.type, {f for f in forms if f}))

    return [_resolve_one(a, node_ids, node_forms, registry, alias_idx, rules) for a in anchors]


def _resolve_one(
    anchor: str,
    node_ids: set[str],
    node_forms: list[tuple[str, str, set[str]]],
    registry: dict[str, EntityEntry],
    alias_idx: AliasIndex,
    rules: dict[str, str],
) -> AnchorResolution:
    # (1) literal — already a node id in the view.
    if anchor in node_ids:
        return AnchorResolution(anchor, anchor, LITERAL)

    # (2) registry entity_id → canonical/aliases → type-gated name match on a view node.
    entry = registry.get(anchor)
    if entry is not None:
        wanted = {normalize(entry.canonical_name, rules)}
        wanted |= {normalize(a, rules) for a in entry.aliases}
        wanted = {w for w in wanted if w}
        etype = entry.type
        for nid, ntype, forms in node_forms:
            if ntype == etype and (forms & wanted):
                return AnchorResolution(anchor, nid, REGISTRY_ALIAS)

    # (3) alias-index equivalence class (seeded ∪ registry) — a surface form drift.
    target = normalize(anchor, rules)
    if target:
        for nid, _ntype, forms in node_forms:
            if any(alias_idx.equivalent(f, target) for f in forms):
                return AnchorResolution(anchor, nid, ALIAS_INDEX)

    return AnchorResolution(anchor, None, None)
