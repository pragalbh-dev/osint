"""Baseline / after measurement across blockers A,B,C,D,E,J on the REAL booted corpus."""
from __future__ import annotations

import collections
import json
import sys

from fastapi.testclient import TestClient

from chanakya.api import create_app
from chanakya.api.state import build_default_state

FIXED_TS = "2026-07-26T00:00:00+00:00"
HERO = "same-as:ent:unit:Pakistan Army Air Defence (PAAD) unit|unit_hq9b"


def boot():
    state = build_default_state(clock=lambda: FIXED_TS)
    state.boot()
    return state


def sig(view):
    return len(view["nodes"]), len(view["edges"]), len(view.get("known_gaps", []))


def main():
    state = boot()
    with TestClient(create_app(state)) as c:
        v0 = c.get("/view").json()
    n, e, g = sig(v0)
    print(f"BOOT nodes={n} edges={e} known_gaps={g}")
    sames = sorted(x["id"] for x in v0["edges"] if x["type"] == "same-as")
    walls = [x for x in v0["edges"] if x["type"] == "distinct-from"]
    print(f"same-as candidates={len(sames)} distinct-from={len(walls)}")

    # ---- D: next_coverage_due
    gaps = v0.get("known_gaps", [])
    nulls = [x for x in gaps if not x.get("next_coverage_due")]
    print(f"D: known_gaps with null next_coverage_due: {len(nulls)}/{len(gaps)}")
    kinds = collections.Counter(x["id"].split(":")[1] if ":" in x["id"] else x["id"] for x in nulls)
    print("   null gap id-kinds:", dict(kinds))

    # ---- J: duplicate (related_ref, what_missing)
    per_node = collections.Counter((x.get("related_ref"), x["what_missing"]) for x in gaps)
    dupes = {k: v for k, v in per_node.items() if v > 1}
    ident = [x for x in gaps if "identity" in x["id"] or "unsettled" in x["what_missing"].lower()]
    print(f"J: distinct (node,text) pairs = {len(per_node)} across {len(gaps)} gaps; dupes={len(dupes)}")
    if dupes:
        for k, v in list(dupes.items())[:5]:
            print(f"   x{v} {k[0]} :: {k[1][:80]}")
    print(f"   identity-ish gaps: {len(ident)}, distinct (node,text) among them: "
          f"{len({(x.get('related_ref'), x['what_missing']) for x in ident})}")

    # ---- E: coverage withheld coverage of the possible tier
    with TestClient(create_app(state)) as c:
        cov = c.get("/coverage").json()
    print(f"E: coverage possible={cov['possible']} withheld={len(cov['withheld'])} "
          f"unreached={cov['possible'] - len(cov['withheld'])}")

    # ---- C: malformed actor
    with TestClient(create_app(state)) as c:
        try:
            r = c.post("/hitl/merge", json={"item_id": "x", "type": "merge", "subject": HERO,
                                            "decision": "reject", "actor": "audit"})
            print("C: actor=audit ->", r.status_code)
        except Exception as exc:
            print("C: actor=audit -> UNHANDLED", type(exc).__name__)

    # ---- A/B: every reject, on a fresh app each time
    print("\nA/B: per-pair reject outcomes")
    still_drawn = 0
    no_change = 0
    contradictory = 0
    for sid in sames:
        st = boot()
        with TestClient(create_app(st)) as c:
            before = c.get("/view").json()
            r = c.post("/hitl/merge", json={"item_id": f"merge:{sid}", "type": "merge", "subject": sid,
                                            "decision": "reject", "actor": "analyst", "rationale": "no"})
            after = c.get("/view").json()
        same_view = json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True)
        drawn = any(x["id"] == sid for x in after["edges"])
        pair = tuple(sorted((next(x for x in before["edges"] if x["id"] == sid)["source"],
                             next(x for x in before["edges"] if x["id"] == sid)["target"])))
        wall = any(x["type"] == "distinct-from" and tuple(sorted((x["source"], x["target"]))) == pair
                   for x in after["edges"])
        ack = (r.json() or {}).get("adjudication") if r.status_code == 200 else None
        contra = drawn and wall
        still_drawn += drawn
        no_change += same_view
        contradictory += contra
        print(f"  {r.status_code} unchanged={same_view!s:5} still_drawn={drawn!s:5} wall={wall!s:5} "
              f"contradictory={contra!s:5} ack={'yes' if ack else 'NO'}  {sid}")
    print(f"  TOTALS reject: unchanged={no_change}/{len(sames)} still_drawn={still_drawn} "
          f"contradictory={contradictory}")

    print("\nA: per-pair accept outcomes")
    acc_nochange = 0
    for sid in sames:
        st = boot()
        with TestClient(create_app(st)) as c:
            before = c.get("/view").json()
            r = c.post("/hitl/merge", json={"item_id": f"merge:{sid}", "type": "merge", "subject": sid,
                                            "decision": "accept", "actor": "analyst", "rationale": "yes"})
            after = c.get("/view").json()
        same_view = json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True)
        body = r.json() if r.status_code == 200 else {}
        ack = (body or {}).get("adjudication")
        acc_nochange += same_view
        print(f"  {r.status_code} unchanged={same_view!s:5} applied={None if not ack else ack.get('applied')} "
              f"ack={'yes' if ack else 'NO'}  {sid}")
    print(f"  TOTALS accept: unchanged={acc_nochange}/{len(sames)}")


if __name__ == "__main__":
    sys.exit(main())
