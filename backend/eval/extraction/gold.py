"""Loaders for the two labeled inputs — the claim gold and the per-slice sub-oracle.

**Both are INPUT PATHS.** This module defines the contract and reads whatever file it is handed; the
scorer's author never opens the real labels. That separation is the point: a matcher tuned by someone who
has read the answers measures the tuning, not the models.

Because the contract is declared here rather than reverse-engineered from a file, a mismatch has to be
*loud*. Every loader raises with the offending field named. A tolerant loader that shrugged off an
unrecognised shape would report a real model as scoring zero, which is worse than not running.

────────────────────────────────────────────────────────────────────────────────────────────────────
CLAIM GOLD  ``schema_version: "rk-bakeoff-claim-gold/1.x"``
────────────────────────────────────────────────────────────────────────────────────────────────────
::

    {
      "schema_version": "rk-bakeoff-claim-gold/1.0",
      "claims": [
        {
          "gold_id":     "g001",              # unique within the file
          "source_id":   "d05_example",       # the document this was read from
          "form":        "triple",            # triple | entity | event
          "polarity":    "positive",          # positive | negative
          "kind":        "observation",       # optional — omit if not labeled
          "subject":     "<surface>",         # form=triple
          "predicate":   "supplies-component",# form=triple; event_type for form=event
          "object":      "<surface>",         # form=triple
          "entity_type": "manufacturer",      # form=entity
          "name":        "<surface>",         # form=entity
          "participants": ["<surface>", …],   # form=event
          "doc_ref":     {"file": "…", "span": [12, 88]},   # or a list of the same
          "coref_cluster": "c1",              # optional; document-local cluster label (S3 metric)
          "discriminators": {                 # optional; A7. null/absent value = the SOURCE DOES NOT
            "operator": "the PAF",            # STATE IT, which is a gradable expectation of its own:
            "geography": null,                # filling an absent slot is fabrication, not recall.
            "designation": null,
            "time": null
          },
          "attributes": {}                    # optional; tier-3 source-native context
        }
      ]
    }

────────────────────────────────────────────────────────────────────────────────────────────────────
SUB-ORACLE  ``schema_version: "rk-bakeoff-sub-oracle/1.x"``
────────────────────────────────────────────────────────────────────────────────────────────────────
The node/edge subgraph derivable from *exactly* the labeled documents — never the full answer key, whose
score would be dominated by which documents fell in the slice (identical noise for every candidate)::

    {
      "schema_version": "rk-bakeoff-sub-oracle/1.0",
      "docs": ["d05_example", …],
      "nodes": [ {"id": "n1", "type": "manufacturer", "name": "<surface>"} , … ],
      "edges": [ {"type": "supplies-component", "source": "n1", "target": "n2"} , … ]
    }

An edge endpoint is either a node ``id`` declared above or an inline ``{"type": …, "name": …}`` object.
An endpoint that resolves to neither raises — a silently dropped edge is a silently inflated recall.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .surface import DISCRIMINATOR_SLOTS, SpanRef, SurfaceClaim

CLAIM_GOLD_SCHEMA = "rk-bakeoff-claim-gold/1."
SUB_ORACLE_SCHEMA = "rk-bakeoff-sub-oracle/1."

_FORMS = {"triple", "entity", "event"}
_POLARITIES = {"positive", "negative"}


def _require_version(raw: dict[str, Any], prefix: str, path: Path) -> None:
    version = str(raw.get("schema_version", ""))
    if not version.startswith(prefix):
        raise ValueError(
            f"{path}: expected schema_version starting {prefix!r}, got {version!r}. Refusing to guess "
            "the shape of a labeled input — a mis-read gold file scores every model at zero."
        )


def _parse_ref(raw: Any, path: Path, gold_id: str) -> SpanRef:
    if not isinstance(raw, dict) or not raw.get("file"):
        raise ValueError(f"{path}: gold claim {gold_id!r} has a doc_ref without a 'file'")
    span = raw.get("span")
    if span is not None:
        if not (isinstance(span, (list, tuple)) and len(span) == 2):
            raise ValueError(f"{path}: gold claim {gold_id!r} span must be [start, end], got {span!r}")
        span = (int(span[0]), int(span[1]))
    return SpanRef(
        file=str(raw["file"]), span=span, page=raw.get("page"), row=raw.get("row"),
        line=raw.get("line"), region=raw.get("region"),
    )


def _parse_gold_claim(raw: dict[str, Any], path: Path) -> SurfaceClaim:
    gold_id = str(raw.get("gold_id") or "")
    if not gold_id:
        raise ValueError(f"{path}: a gold claim is missing 'gold_id'")
    form = str(raw.get("form") or "")
    if form not in _FORMS:
        raise ValueError(f"{path}: gold claim {gold_id!r} has form={form!r}, expected one of {sorted(_FORMS)}")
    polarity = str(raw.get("polarity") or "positive")
    if polarity not in _POLARITIES:
        raise ValueError(f"{path}: gold claim {gold_id!r} has polarity={polarity!r}")

    roles: dict[str, str] = {}
    predicate: str | None = None
    entity_type: str | None = None
    if form == "triple":
        roles = {"subject": str(raw.get("subject") or ""), "object": str(raw.get("object") or "")}
        predicate = raw.get("predicate")
    elif form == "entity":
        roles = {"name": str(raw.get("name") or "")}
        entity_type = raw.get("entity_type")
    else:
        parts = raw.get("participants") or []
        if not isinstance(parts, list):
            raise ValueError(f"{path}: gold claim {gold_id!r} participants must be a list")
        roles = {f"participant:{i}": str(p) for i, p in enumerate(parts)}
        predicate = raw.get("event_type") or raw.get("predicate")

    ref_raw = raw.get("doc_ref")
    refs: tuple[SpanRef, ...]
    if ref_raw is None:
        refs = ()
    elif isinstance(ref_raw, list):
        refs = tuple(_parse_ref(r, path, gold_id) for r in ref_raw)
    else:
        refs = (_parse_ref(ref_raw, path, gold_id),)

    disc_raw = raw.get("discriminators") or {}
    if not isinstance(disc_raw, dict):
        raise ValueError(f"{path}: gold claim {gold_id!r} discriminators must be an object")
    unknown = sorted(set(disc_raw) - set(DISCRIMINATOR_SLOTS))
    if unknown:
        raise ValueError(
            f"{path}: gold claim {gold_id!r} names discriminator slot(s) {unknown} outside A7's four: "
            f"{list(DISCRIMINATOR_SLOTS)}"
        )
    # Absent key and explicit null mean the same thing — the source does not state it — and both are
    # gradable: a model that fills them is fabricating, not recalling.
    discriminators: dict[str, str | None] = {
        slot: (str(disc_raw[slot]) if disc_raw.get(slot) is not None else None)
        for slot in DISCRIMINATOR_SLOTS
    }

    return SurfaceClaim(
        key=gold_id,
        source_id=str(raw.get("source_id") or ""),
        form=form,
        polarity=polarity,
        roles=roles,
        predicate=predicate,
        entity_type=entity_type,
        refs=refs,
        kind=raw.get("kind"),
        coref_cluster=raw.get("coref_cluster"),
        discriminators=discriminators,
        attributes=dict(raw.get("attributes") or {}),
    )


def load_claim_gold(path: str | Path) -> list[SurfaceClaim]:
    """Load the labeled claim slice. Raises on an unrecognised schema or a malformed claim."""
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{p}: claim gold must be a JSON object, got {type(raw).__name__}")
    _require_version(raw, CLAIM_GOLD_SCHEMA, p)
    claims_raw = raw.get("claims")
    if not isinstance(claims_raw, list):
        raise ValueError(f"{p}: claim gold needs a 'claims' array")
    claims = [_parse_gold_claim(c, p) for c in claims_raw]
    seen: set[str] = set()
    for c in claims:
        if c.key in seen:
            raise ValueError(f"{p}: duplicate gold_id {c.key!r}")
        seen.add(c.key)
    return claims


# ── the sub-oracle ────────────────────────────────────────────────────────────────────────────────

class OracleNode:
    """One expected node: a type plus a surface name. No id semantics — ids differ per extraction."""

    __slots__ = ("key", "type", "name")

    def __init__(self, key: str, node_type: str, name: str) -> None:
        self.key = key
        self.type = node_type
        self.name = name

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"OracleNode({self.key!r}, {self.type!r}, {self.name!r})"


class OracleEdge:
    """One expected edge: a type plus its two endpoint nodes (by oracle key)."""

    __slots__ = ("type", "source", "target")

    def __init__(self, edge_type: str, source: OracleNode, target: OracleNode) -> None:
        self.type = edge_type
        self.source = source
        self.target = target

    @property
    def key(self) -> str:
        return f"{self.source.key}|{self.type}|{self.target.key}"

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"OracleEdge({self.type!r}, {self.source.key!r} -> {self.target.key!r})"


class SubOracle:
    """The per-slice expected subgraph — nodes + edges derivable from exactly the labeled docs."""

    def __init__(self, docs: list[str], nodes: list[OracleNode], edges: list[OracleEdge]) -> None:
        self.docs = docs
        self.nodes = nodes
        self.edges = edges


def load_sub_oracle(path: str | Path) -> SubOracle:
    """Load the per-slice sub-oracle. Raises on an unrecognised schema or an unresolvable endpoint."""
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{p}: sub-oracle must be a JSON object, got {type(raw).__name__}")
    _require_version(raw, SUB_ORACLE_SCHEMA, p)

    nodes_raw = raw.get("nodes")
    if not isinstance(nodes_raw, list):
        raise ValueError(f"{p}: sub-oracle needs a 'nodes' array")

    by_id: dict[str, OracleNode] = {}
    nodes: list[OracleNode] = []
    for i, item in enumerate(nodes_raw):
        if not isinstance(item, dict) or not item.get("type"):
            raise ValueError(f"{p}: sub-oracle node #{i} needs a 'type'")
        key = str(item.get("id") or f"{item['type']}::{item.get('name', '')}")
        node = OracleNode(key, str(item["type"]), str(item.get("name") or ""))
        nodes.append(node)
        # Registered under both addresses so an edge may name the node by its declared id *or* by its
        # ``{type, name}`` shape; the two are the same node either way.
        by_id[key] = node
        by_id.setdefault(f"{node.type}::{node.name}", node)

    def _endpoint(value: Any, where: str) -> OracleNode:
        if isinstance(value, str):
            if value in by_id:
                return by_id[value]
            raise ValueError(f"{p}: {where} references node {value!r}, which is not declared in 'nodes'")
        if isinstance(value, dict) and value.get("type"):
            key = f"{value['type']}::{value.get('name', '')}"
            if key in by_id:
                return by_id[key]
            raise ValueError(
                f"{p}: {where} declares inline endpoint {key!r} that is not among the declared nodes — "
                "an endpoint outside the sub-oracle's node set would inflate edge recall"
            )
        raise ValueError(f"{p}: {where} has an endpoint that is neither a node id nor {{type, name}}")

    edges: list[OracleEdge] = []
    for i, item in enumerate(raw.get("edges") or []):
        if not isinstance(item, dict) or not item.get("type"):
            raise ValueError(f"{p}: sub-oracle edge #{i} needs a 'type'")
        edges.append(OracleEdge(
            str(item["type"]),
            _endpoint(item.get("source"), f"edge #{i}"),
            _endpoint(item.get("target"), f"edge #{i}"),
        ))

    docs = [str(d) for d in (raw.get("docs") or [])]
    return SubOracle(docs=docs, nodes=nodes, edges=edges)


__all__ = [
    "CLAIM_GOLD_SCHEMA",
    "SUB_ORACLE_SCHEMA",
    "OracleEdge",
    "OracleNode",
    "SubOracle",
    "load_claim_gold",
    "load_sub_oracle",
]
