"""T9 read-only probe: enumerate the substantive graph and score candidate hero chains."""
from __future__ import annotations
import json, sys, itertools
from collections import defaultdict
from eval import harness

inp = harness.load_scenario()
view = harness.build_view(inp)

nodes = {n.id: n for n in view.nodes}
print(f"== {len(view.nodes)} nodes, {len(view.edges)} edges, {len(view.known_gaps)} gaps")

STRUCT = {"same-as", "distinct-from"}

print("\n== NODES by type ==")
by_type = defaultdict(list)
for n in view.nodes:
    by_type[n.type].append(n)
for t in sorted(by_type):
    print(f"\n--- {t} ({len(by_type[t])})")
    for n in sorted(by_type[t], key=lambda x: x.id):
        st = n.status
        ac = getattr(n.confidence, "assertion_confidence", None) if n.confidence else None
        mat = n.materiality
        ms = f" chokepoint={mat.chokepoint_status}/{mat.chokepoint_count} subst={mat.substitutability_state}" if mat else ""
        print(f"  {n.id!r:60s} name={n.name!r} status={st} conf={ac}{ms} claims={len(n.claim_ids or [])}")

print("\n== EDGES ==")
for e in sorted(view.edges, key=lambda x: (x.type, x.source, x.target)):
    st = e.status
    ac = getattr(e.confidence, "assertion_confidence", None) if e.confidence else None
    print(f"  {e.type:22s} {e.source:55s} -> {e.target:55s} status={st} conf={ac} claims={len(e.claim_ids or [])} id={e.id}")

print("\n== KNOWN GAPS ==")
for g in view.known_gaps:
    print(f"  {g.id} missing={g.what_missing!r} slots={g.missing_slots} ceiling={g.observability_ceiling} next={g.next_coverage_due} rel={g.related_ref}")

# ── duplicate-row check (T9 §5 / tmp/conv/T9-to-DATA-graph-gaps.md §1) ───────────────────────────
# rebuild() emits some edge ids on SEVERAL rows, each holding a different slice of the claims, and only
# one row is ever scored. This prints the groups so the finding is reproducible, not anecdotal.
from collections import Counter, defaultdict  # noqa: E402

counts = Counter(e.id for e in view.edges)
dupes = {k: v for k, v in counts.items() if v > 1}
print(
    f"\n== DUPLICATE EDGE ROWS ==\n{len(view.edges)} edge rows, {len(counts)} distinct ids, "
    f"{len(dupes)} ids duplicated, {sum(dupes.values()) - len(dupes)} surplus rows"
)
grouped = defaultdict(list)
for e in view.edges:
    if e.id in dupes:
        grouped[e.id].append(e)
for eid in sorted(grouped):
    print(f"\n  {eid}  x{len(grouped[eid])}")
    for e in grouped[eid]:
        conf = e.confidence.assertion_confidence if e.confidence else None
        print(f"      status={e.status} conf={conf} claims={list(e.claim_ids)}")
node_dupes = {k: v for k, v in Counter(n.id for n in view.nodes).items() if v > 1}
print(f"\n  duplicate node ids: {node_dupes or 'none'}")
