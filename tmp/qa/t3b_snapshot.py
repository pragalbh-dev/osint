"""T3b QA: snapshot of fragmentation-relevant graph shape. Read-only.

Usage: t3b_snapshot.py <out.json>
"""

import json
import sys
from collections import defaultdict

from chanakya.api.state import build_default_state

state = build_default_state()
state.boot()
view = state.view()

claims = list(state.evidence.replay())

same_as = [e for e in view.edges if e.type == "same-as"]
distinct = [e for e in view.edges if e.type == "distinct-from"]
real_edges = [e for e in view.edges if e.type not in ("same-as", "distinct-from")]

by_type: dict[str, int] = defaultdict(int)
for n in view.nodes:
    by_type[n.type] += 1

names = {n.id: (n.name or "") for n in view.nodes}
types = {n.id: n.type for n in view.nodes}


def label(nid: str) -> str:
    return f"{nid} [{types.get(nid, '?')}] {names.get(nid, '')!r}"


def cluster(sub: str) -> list[str]:
    return sorted(
        label(n.id) for n in view.nodes if sub.lower() in (n.id + " " + (n.name or "")).lower()
    )


snap = {
    "nodes": len(view.nodes),
    "edges_total": len(view.edges),
    "edges_substantive": len(real_edges),
    "known_gaps": len(view.known_gaps),
    "events": len(view.events),
    "claims": len(claims),
    "hitl_merge_queue_same_as": len(same_as),
    "distinct_from_vetoes": len(distinct),
    "by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
    "unknown_nodes": sorted(label(n.id) for n in view.nodes if n.type == "unknown"),
    "nodes_by_type": {
        t: sorted(label(n.id) for n in view.nodes if n.type == t) for t in sorted(by_type)
    },
    "same_as_pairs": sorted(f"{label(e.source)}  <->  {label(e.target)}" for e in same_as),
    "distinct_pairs": sorted(f"{label(e.source)}  <->  {label(e.target)}" for e in distinct),
    "karachi_cluster": cluster("karachi"),
    "ht233_cluster": sorted(set(cluster("ht-233") + cluster("ht233"))),
    "node_ids": sorted(n.id for n in view.nodes),
}
json.dump(snap, open(sys.argv[1], "w"), indent=1, default=str)
print(
    json.dumps(
        {
            k: v
            for k, v in snap.items()
            if k
            not in (
                "node_ids",
                "same_as_pairs",
                "unknown_nodes",
                "distinct_pairs",
                "by_type",
                "nodes_by_type",
                "karachi_cluster",
                "ht233_cluster",
            )
        },
        indent=1,
    )
)
print("\nby_type:", snap["by_type"])
for t in ("basing_site", "contract_import_event"):
    print(f"\n-- {t} --")
    for x in snap["nodes_by_type"].get(t, []):
        print(" ", x)
print("\n-- unknown --")
for x in snap["unknown_nodes"]:
    print(" ", x)
print("\n-- karachi cluster --")
for x in snap["karachi_cluster"]:
    print(" ", x)
print("\n-- ht-233 cluster --")
for x in snap["ht233_cluster"]:
    print(" ", x)
print("\n-- same-as candidates --")
for x in snap["same_as_pairs"]:
    print(" ", x)
