"""T1 QA: coref's MAXIMUM possible reach.

Coref clusters mentions within ONE document only. So for every pair the system itself
already flags as a possible duplicate (the 40 same-as candidates in the HITL queue),
ask: do the two endpoints share a source document? If not, coref can never touch it.
Read-only.
"""
import json
import sys
from collections import defaultdict

from chanakya.api.state import build_default_state

state = build_default_state()
state.boot()
view = state.view()

claims = {}
for c in state.evidence.replay():
    cid = getattr(c, "claim_id", None) or getattr(c, "id", None)
    claims[cid] = c


def doc_of(c):
    for a in ("doc_id", "document_id", "source_doc", "source_id"):
        v = getattr(c, a, None)
        if v:
            return str(v)
    prov = getattr(c, "provenance", None)
    if prov is not None:
        for a in ("doc_id", "document_id", "source_doc"):
            v = getattr(prov, a, None)
            if v:
                return str(v)
    return "?"


docs_of_node = {}
type_of_node = {}
for n in view.nodes:
    cids = getattr(n, "claim_ids", None) or []
    docs_of_node[n.id] = {doc_of(claims[c]) for c in cids if c in claims}
    type_of_node[n.id] = n.type

same_as = [(e.source, e.target) for e in view.edges if e.type == "same-as"]

shared, split, cross_type = [], [], []
for a, b in same_as:
    ov = docs_of_node.get(a, set()) & docs_of_node.get(b, set())
    rec = {"a": a, "b": b, "shared_docs": sorted(ov),
           "type_a": type_of_node.get(a), "type_b": type_of_node.get(b)}
    if type_of_node.get(a) != type_of_node.get(b):
        cross_type.append(rec)
    if ov:
        shared.append(rec)
    else:
        split.append(rec)

# the 11 unknown nodes vs any typed node sharing a document
unknowns = [n.id for n in view.nodes if n.type == "unknown"]
unk_reach = {}
for u in unknowns:
    ud = docs_of_node[u]
    mates = sorted(m for m in docs_of_node
                   if m != u and type_of_node[m] not in ("unknown", "source")
                   and docs_of_node[m] & ud)
    unk_reach[u] = {"docs": sorted(ud), "n_typed_co_mentions_same_doc": len(mates), "sample": mates[:6]}

out = {
    "same_as_candidates_total": len(same_as),
    "IN_document_reachable_by_coref": len(shared),
    "CROSS_document_out_of_coref_reach": len(split),
    "cross_type_pairs_coref_would_refuse": len(cross_type),
    "shared": shared,
    "split_sample": split[:50],
    "unknown_reach": unk_reach,
}
json.dump(out, open(sys.argv[1], "w"), indent=1, default=str)

print(f"same-as candidates (the HITL merge queue): {len(same_as)}")
print(f"  IN-document  (coref could reach):  {len(shared)}")
print(f"  CROSS-document (coref cannot):     {len(split)}")
print(f"  cross-TYPE (coref refuses by rule):{len(cross_type)}")
print()
print("IN-document candidate pairs (coref's entire addressable market):")
for r in shared:
    print(f"  {r['a'][:44]:44s} <-> {r['b'][:44]:44s}  docs={r['shared_docs']}")
print()
print("unknown-node rescue reach:")
for u, r in unk_reach.items():
    print(f"  {u[:38]:38s} docs={r['docs']} typed co-mentions in same doc={r['n_typed_co_mentions_same_doc']}")
