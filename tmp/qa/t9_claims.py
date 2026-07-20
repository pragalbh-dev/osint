from eval import harness
import sys
inp = harness.load_scenario()
for cid in sys.argv[1:]:
    c = inp.claims.get(cid)
    if c is None:
        print(f"{cid}: MISSING"); continue
    print(f"\n=== {cid}  kind={c.kind}")
    print("  " + c.model_dump_json(indent=2)[:1400])
    
    
