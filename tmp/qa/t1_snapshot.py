"""T1 QA: one-shot snapshot of everything the coref gate could move. Read-only.

Usage: qa_compare.py <out.json>
"""
import json
import sys
from collections import defaultdict

from chanakya.api.state import build_default_state

state = build_default_state()
state.boot()
view = state.view()

claims = list(state.evidence.replay())
coref_claims = [c for c in claims if getattr(c, "predicate", None) == "coref-same-as"
                or "coref-same-as" in str(getattr(c, "triple", ""))]

same_as = [e for e in view.edges if e.type == "same-as"]
distinct = [e for e in view.edges if e.type == "distinct-from"]
real_edges = [e for e in view.edges if e.type not in ("same-as", "distinct-from")]

by_type = defaultdict(int)
for n in view.nodes:
    by_type[n.type] += 1

snap = {
    "nodes": len(view.nodes),
    "edges_total": len(view.edges),
    "edges_substantive": len(real_edges),
    "known_gaps": len(view.known_gaps),
    "events": len(view.events),
    "claims": len(claims),
    "coref_claims_in_log": len(coref_claims),
    "hitl_merge_queue_same_as": len(same_as),
    "distinct_from_vetoes": len(distinct),
    "by_type": dict(sorted(by_type.items(), key=lambda kv: -kv[1])),
    "unknown_nodes": sorted(n.id for n in view.nodes if n.type == "unknown"),
    "node_ids": sorted(n.id for n in view.nodes),
    "same_as_pairs": sorted([e.source, e.target] for e in same_as),
    "distinct_pairs": sorted([e.source, e.target] for e in distinct),
}
json.dump(snap, open(sys.argv[1], "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in snap.items()
                  if k not in ("node_ids", "same_as_pairs", "unknown_nodes", "distinct_pairs", "by_type")}, indent=1))
print("by_type:", snap["by_type"])
