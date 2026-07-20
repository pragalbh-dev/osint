"""T3b QA diagnostic: why does an endpoint surface form stay an untyped `unknown` mention?

Usage: t3b_diag.py [form ...]
"""

import sys

from chanakya.api.state import build_default_state
from chanakya.ontology import EdgeLaneIndex
from chanakya.resolve import aliases as A
from chanakya.resolve import entities as E
from chanakya.resolve import __init__ as R  # noqa: F401
from chanakya.resolve.rconfig import ResolveConfig
import chanakya.resolve as RES

state = build_default_state()
state.boot()
claims = list(state.evidence.replay())
config = state.config.snapshot()
decisions = list(state.decision.replay())

cfg = ResolveConfig.from_bundle(config)
lane = EdgeLaneIndex(config.ontology)
graph = E.build(claims, lane)
RES._seed_registry(graph, cfg)
alias_idx = A.build(cfg.alias_table, cfg.transliteration, decisions, cfg.registry_alias_table)

edge_types = RES._edge_implied_types(graph, lane)
surface_forms = sorted({e.subject for e in graph.edges} | {e.object for e in graph.edges})

forms = sys.argv[1:] or [
    "HT-233",
    "HQ-9/P TEL",
    "TEL",
    "TAS5380",
    "Pakistan",
    "Sindh",
    "Punjab",
    "Karachi air defence sector",
]

for form in forms:
    print(f"\n=== {form!r} ===")
    print("  is endpoint surface form:", form in surface_forms)
    print("  already an entity id:", form in graph.entities)
    matches = RES._matching_eids(form, graph, cfg, alias_idx)
    print("  _matching_eids ->", matches)
    print("  types of matches ->", {graph.entities[m].etype for m in matches})
    print("  edge-implied types ->", edge_types.get(form))
    print("  predicates:", sorted({(e.predicate, "subj" if e.subject == form else "obj")
                                   for e in graph.edges if form in (e.subject, e.object)}))

print("\n--- all endpoint forms that stay unlinked ---")
mention, minted, ambiguous = RES._link_endpoints(graph, cfg, alias_idx, lane, set())
for form in surface_forms:
    if form in graph.entities or form in mention:
        continue
    matches = RES._matching_eids(form, graph, cfg, alias_idx)
    print(f"  {form!r}: matches={matches} types={{{', '.join(sorted({graph.entities[m].etype for m in matches}))}}} "
          f"edge_types={sorted(edge_types.get(form, set()))}")
