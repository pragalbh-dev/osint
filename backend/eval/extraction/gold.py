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
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .surface import DISCRIMINATOR_SLOTS, SpanRef, SurfaceClaim

CLAIM_GOLD_SCHEMA = "rk-bakeoff-claim-gold/1."
SUB_ORACLE_SCHEMA = "rk-bakeoff-sub-oracle/1."

_FORMS = {"triple", "entity", "event"}
_POLARITIES = {"positive", "negative"}

#: The licensing categories the gold's own vocabulary uses to say "these mentions ARE one referent".
#: A cluster must name one of these to be treated as an identity cluster at all.
IDENTITY_LICENCES: tuple[str, ...] = ("EXPLICIT_EQUIVALENCE", "UNAMBIGUOUS_ANAPHOR", "NAME_VARIANT")

#: Markers that say "these mentions are NOT one referent" — an anti-coreference trap, an unresolved pair,
#: or a contrastive enumeration. Any of these VETOES the identity reading above, whichever licence the
#: cluster also names: ``NAME_VARIANT (n/a — distinct handles)`` names a licence and then withdraws it.
#: Matched against the cluster's licensing category, its referent type **and** its own tag, because the
#: gold states the same fact in all three places and a rule that read only one would go quiet if the
#: wording of that one changed.
#:
#: Matched only AFTER the identity licences have been struck out of the text — see
#: :func:`_licenses_identity`. ``UNAMBIGUOUS_ANAPHOR`` contains the substring ``AMBIGUOUS``, so a naive
#: scan flips the gold's single most common *positive* licence into a veto and reports twenty clusters as
#: traps. That is the failure this ordering exists to prevent, and it is why the licences are removed
#: first rather than the markers being made cleverer.
ANTI_IDENTITY_MARKERS: tuple[str, ...] = (
    "ANTI_COREF", "ANTI-COREF", "ANTICOREF", "AMBIGUOUS", "CONTRASTIVE", "N/A", " VS ",
)

#: Strings a labeled slice may use to mean "the source does not state this". Treated exactly as ``null``.
#: A gold file that writes the absence out as a word instead of a null must not be read as *stating* the
#: word — see the discriminator block in :func:`_parse_claim` for what that inversion costs.
NOT_STATED_SENTINELS = frozenset({"unknown", "not stated", "not-stated", "n/a", "na", "none", "null", ""})


def _is_stated(value: Any) -> bool:
    """Did the source actually state this discriminator? ``null``/absent/sentinel ⇒ no."""
    if value is None:
        return False
    return str(value).strip().casefold() not in NOT_STATED_SENTINELS


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
    # Absent key, explicit null, and a "not stated" SENTINEL string all mean the same thing — the source
    # does not state it — and all are gradable: a model that fills them is fabricating, not recalling.
    #
    # The sentinel matters. The labeled slice writes "unknown" as a string rather than null (349 of its
    # 500 discriminator slots), and reading those as STATED values inverts both A7 metrics at once:
    # `discriminator_capture`'s denominator swells from 151 to 500, so even a perfect model scores ~0.30;
    # and `discriminator_fabrication_avoidance` loses its entire denominator and reports unavailable.
    # Worse, a model that literally emits the word "unknown" would then outscore one that correctly left
    # the slot empty — rewarding exactly the fabrication the metric exists to catch.
    discriminators: dict[str, str | None] = {
        slot: (str(disc_raw[slot]) if _is_stated(disc_raw.get(slot)) else None)
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


# ── the coref registry: what a cluster LABEL means ────────────────────────────────────────────────

@dataclass(frozen=True)
class CorefRegistry:
    """Which of the gold's cluster labels license a *binding*, and which forbid one.

    ``SurfaceClaim.coref_cluster`` is one field carrying two opposite meanings. On most rows it says
    "these mentions are one referent"; on the rows the gold's registry marks ``ANTI_COREF`` or
    ``AMBIGUOUS`` it says the exact opposite — "these mentions must be held APART" — and the registry is
    the only place that distinction is written down.

    Reading the label without the registry is not a small imprecision. Measured on the shipped slice, the
    **only** two clusters carrying more than one entity-form claim are both anti-coreference traps
    (``d05-C4-events``, three separately-identified import events; ``d19-C4-othersites``, two contrastively
    enumerated sites), so a B-cubed metric that treats a shared label as a shared referent pays a model
    **+0.273 / +0.280** for committing the over-merge this project exists to prevent — on the criterion
    weighted highest. Hence the allow-list: a cluster licenses a binding only when the gold says it does.
    """

    #: Cluster tag → does the gold license binding its mentions into one referent?
    licensed: dict[str, bool]
    #: True when the gold file actually declared a ``coref_registry`` block.
    declared: bool = True

    def is_anti_coref(self, cluster: str | None) -> bool:
        """Would binding this cluster's mentions be an over-merge the gold forbids?

        An unknown cluster reads as **not licensed**. That direction is chosen deliberately: the failure
        this guards against is crediting a forbidden bind, and an unknown label is exactly the shape a
        renamed or newly-added anti-coref cluster would arrive in.
        """
        if cluster is None:
            return False
        return not self.licensed.get(cluster, False)

    @property
    def anti_coref_clusters(self) -> frozenset[str]:
        return frozenset(tag for tag, ok in self.licensed.items() if not ok)


def _licenses_identity(cluster: dict[str, Any]) -> bool:
    """Does this registry entry declare its mentions to be ONE referent?

    Allow-list, then veto — never the other way round. A deny-list alone would silently license any
    cluster whose category the gold spells in a way this scorer has not seen, and "silently licensed" is
    the direction that credits an over-merge.
    """
    text = " ".join(str(cluster.get(k) or "") for k in ("licensing_category", "referent_type", "cluster"))
    upper = f" {text.upper()} "
    if not any(licence in upper for licence in IDENTITY_LICENCES):
        return False
    # Strike the licences out before scanning for a veto: `UNAMBIGUOUS_ANAPHOR` *contains* `AMBIGUOUS`,
    # and a scan over the raw text therefore reads the gold's commonest identity licence as its own denial.
    residue = upper
    for licence in IDENTITY_LICENCES:
        residue = residue.replace(licence, " ")
    return not any(marker in residue for marker in ANTI_IDENTITY_MARKERS)


def load_coref_registry(path: str | Path) -> CorefRegistry:
    """Load the gold's ``coref_registry`` and classify every cluster as licensed / anti-coreference.

    A gold file with no registry block loads as ``declared=False`` with an empty mapping, which — by the
    unknown-reads-as-unlicensed rule above — would make *every* cluster anti-coref. That is why
    :func:`eval.extraction.coref_channel.require_gold_labels` refuses such a file up front rather than
    letting the metric quietly report nothing: an absent registry is a missing input, not a result.
    """
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{p}: claim gold must be a JSON object, got {type(raw).__name__}")
    block = raw.get("coref_registry")
    if block is None:
        return CorefRegistry(licensed={}, declared=False)
    if not isinstance(block, list):
        raise ValueError(f"{p}: 'coref_registry' must be an array, got {type(block).__name__}")
    licensed: dict[str, bool] = {}
    for i, cluster in enumerate(block):
        if not isinstance(cluster, dict) or not cluster.get("cluster"):
            raise ValueError(f"{p}: coref_registry[{i}] has no 'cluster' tag, so its licensing decision "
                             "could never be attached to a labeled claim")
        licensed[str(cluster["cluster"])] = _licenses_identity(cluster)
    return CorefRegistry(licensed=licensed, declared=True)


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
    "ANTI_IDENTITY_MARKERS",
    "CLAIM_GOLD_SCHEMA",
    "IDENTITY_LICENCES",
    "SUB_ORACLE_SCHEMA",
    "CorefRegistry",
    "OracleEdge",
    "OracleNode",
    "SubOracle",
    "load_claim_gold",
    "load_coref_registry",
    "load_sub_oracle",
]
