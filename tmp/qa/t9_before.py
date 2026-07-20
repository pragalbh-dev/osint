from eval import harness
from chanakya.agent import ask
inp = harness.load_scenario(exclude_docs=harness.STAGED_RELOCATION_DOCS)
view = harness.build_view(inp)
cfg = inp.config_store.snapshot()
print(f"BEFORE-ingest view: {len(view.nodes)} nodes, {len(view.edges)} edges")
ids = {n.id for n in view.nodes}
for k in ("site_rahwali","unit_hq9b","var_hq9p","mfr_casic","comp_ht233"):
    print(" ", k, "present" if k in ids else "ABSENT")
for e in view.edges:
    if e.source in ("site_rahwali","unit_hq9b") or e.target in ("site_rahwali",):
        print("   edge", e.type, e.source, "->", e.target, e.status)
lens = cfg.subjects.as_map()["lens-hq9p-pk"]
a = ask(lens.target_queries[0], view, cfg, llm=None, claims=inp.claims)
print("\nANSWER:", a.answer)
print("REFUSAL:", a.refusal)
print("HOPS:", [(h.step,h.edge,h.src,h.dst) for h in a.hops])
