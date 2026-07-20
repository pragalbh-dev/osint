"""T9: probe candidate hero chains — find_paths under different lane whitelists."""
from __future__ import annotations
from eval import harness
from chanakya.agent.context import ToolContext
from chanakya.agent.tools import find_paths, ToolError

inp = harness.load_scenario()
view = harness.build_view(inp)
cfg = inp.config_store.snapshot()
ctx = ToolContext.build(view, inp.claims, cfg)

ORIGIN_LANES = ["based-at", "inducted-into", "equips", "manufactures", "supplies-component", "operates", "fields"]
CASES = [
    ("site_rahwali", "mfr_casic", None),
    ("site_rahwali", "mfr_casic", ORIGIN_LANES),
    ("site_rahwali", "comp_ht233", ORIGIN_LANES),
    ("site_rahwali", "ent:manufacturer:CPMIEC", ORIGIN_LANES),
    ("site_rahwali", "mfr_taian", ORIGIN_LANES),
    ("site_rahwali", "comp_tel_chassis", ORIGIN_LANES),
    ("site_rahwali", "mfr_23rd_ri", None),
    ("unit_hq9b", "mfr_casic", ORIGIN_LANES),
    ("site_rahwali", "ent:manufacturer:China", None),
    ("ent:basing_site:Army Air Defence Centre, Karachi", "mfr_casic", None),
]
for src, dst, wl in CASES:
    try:
        r = find_paths(ctx, src, dst, edge_whitelist=wl)
        print(f"\n### {src} -> {dst}  wl={'ORIGIN' if wl else 'default'}  hops={r['hop_count']}")
        for h in r["hops"]:
            e = ctx.edges_by_id.get(h["edge_id"])
            print(f"    {h['src']}  --{h['edge']} [{h['status']}]-->  {h['dst']}   claims={h['claim_ids']}")
    except ToolError as ex:
        print(f"\n### {src} -> {dst}  wl={'ORIGIN' if wl else 'default'}  ERROR: {ex}")
