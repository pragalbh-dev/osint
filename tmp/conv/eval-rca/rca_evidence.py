"""Portable EVAL-RCA evidence regenerator — run it from ANY worktree to evaluate THAT worktree's pipeline.

Usage (from a fixing agent's worktree, after branching off feat/eval so the frozen bundles are present):

    <worktree>/backend/.venv/bin/python <worktree>/tmp/conv/eval-rca/rca_evidence.py

It resolves the repo root from its own location (…/tmp/conv/eval-rca/ -> repo root), points CHANAKYA_ROOT +
sys.path at that worktree, rebuilds the view from the frozen bundles at corpus/scenarios/hq9p_primary/claims/,
and (re)writes the evidence bundle in-place: 00-evidence-summary.md, view_full.json, view_lens.json. Run it
once before your change to confirm the baseline symptom, then again after to confirm it cleared.
"""
import io
import os
import sys
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(os.environ.get("CHANAKYA_ROOT") or Path(__file__).resolve().parents[3])
os.environ.setdefault("CHANAKYA_ROOT", str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from chanakya.view import view_to_json  # noqa: E402
from eval import harness  # noqa: E402

OUT = ROOT / "tmp" / "conv" / "eval-rca"
OUT.mkdir(parents=True, exist_ok=True)

inp = harness.load_scenario()
view = harness.build_view(inp)
lens_view = harness.build_view(inp, lens=harness.DEFAULT_LENS)
ak = inp.answer_key

(OUT / "view_full.json").write_text(view_to_json(view), encoding="utf-8")
(OUT / "view_lens.json").write_text(view_to_json(lens_view), encoding="utf-8")

buf = io.StringIO()
def w(*a):
    print(*a, file=buf)

w("# EVAL RCA — evidence bundle (real pipeline over frozen bundles)")
w()
w(f"- repo root: `{ROOT}`")
w(f"- claims seeded: **{inp.claim_count}**")
w(f"- full view: **{len(view.nodes)} nodes / {len(view.edges)} edges / {len(view.events)} events / "
  f"{len(view.known_gaps)} known_gaps**")
w(f"- lens view (`{harness.DEFAULT_LENS}`): **{len(lens_view.nodes)} nodes / {len(lens_view.edges)} edges**")
w(f"- oracle: {len(ak['ground_truth']['nodes'])} nodes / {len(ak['ground_truth']['edges'])} edges / "
  f"{len(ak['ground_truth']['places'])} places")
w()

w("## view node-type histogram")
for t, c in sorted(Counter(n.type for n in view.nodes).items(), key=lambda x: -x[1]):
    w(f"- {t}: {c}")
w()
w("## view edge-type histogram (ad-hoc predicates reveal ontology non-enforcement)")
for t, c in sorted(Counter(e.type for e in view.edges).items(), key=lambda x: -x[1]):
    w(f"- {t}: {c}")
w()
w("## known_gap nodes (proliferation check)")
for g in view.nodes:
    if g.type == "known_gap":
        w(f"- `{g.id}`  status={g.status}")
w()

def norm(s):
    return (s or "").lower()

def name_keys(gn):
    keys = [gn.get("name", ""), gn.get("export_designator", ""), gn.get("canonical_name", "")]
    keys += gn.get("aliases", [])
    return [k for k in keys if k]

w("## ORACLE NODE -> VIEW attribute-match (RESOLVE under-merge evidence)")
w("For each oracle node: view nodes of same type whose name/alias overlaps. >1 hit = fragmented (unmerged).")
w()
for gn in ak["ground_truth"]["nodes"]:
    gtype = gn["type"]; keys = [norm(k) for k in name_keys(gn)]
    hits = []
    for vn in view.nodes:
        if vn.type != gtype:
            continue
        vname = norm(vn.name)
        if any(k and (k in vname or vname in k) for k in keys) or any(
            k and any(tok in vname for tok in k.split() if len(tok) > 3) for k in keys):
            hits.append((vn.id, vn.status))
    tag = "MISSING" if not hits else ("OK-1" if len(hits) == 1 else f"FRAGMENTED-{len(hits)}")
    w(f"- **{gn['id']}** ({gtype}, want_status={gn.get('status', '-')}) [{tag}]")
    for hid, hs in hits[:8]:
        w(f"    - {hid}  status={hs}")
w()

w("## ORACLE EDGE -> VIEW (by type)")
for ge in ak["ground_truth"]["edges"]:
    rel = ge["rel"]
    matches = [e for e in view.edges if e.type == rel]
    w(f"- **{ge['from']} -{rel}-> {ge['to']}** (want {ge.get('status', '-')}): {len(matches)} view edges of type '{rel}'")
w()

w("## RESOLVE decisions that FIRED (same-as / distinct-from)")
for e in view.edges:
    if e.type in ("same-as", "distinct-from"):
        w(f"- {e.type}: {e.source} -> {e.target}  (merge_conf={getattr(e, 'merge_confidence', None)}, status={e.status})")
w()

w("## HERO QUERY")
try:
    ans = harness.run_hero_query(inp, view)
    w(f"- answer: {(ans.answer or '<REFUSAL>')[:600]}")
    w(f"- hops: {[(h.src, h.edge, h.dst) for h in ans.hops]}")
    w(f"- citations: {ans.citations[:15]}")
    w(f"- refusal: {ans.refusal}")
except Exception:
    w("```"); w(traceback.format_exc()); w("```")
w()

w("## RELOCATION OBSERVABLE")
try:
    alerts = harness.fire_relocation_observable(inp)
    w(f"- staged ingest: {list(harness.STAGED_RELOCATION_DOCS)}")
    w(f"- alerts fired: {len(alerts)}")
    for a in alerts:
        w(f"    - {a.observable_id} subj={a.subject} before={a.before} after={a.after}")
        if a.provenance:
            w(f"      provenance before={a.provenance.before_claim_ids} after={a.provenance.after_claim_ids}")
    spoof = harness.fire_relocation_observable(inp, staged_docs=("d20_supersede_spoof",))
    w(f"- alerts when the d20 spoof is the staged arrival instead: {len(spoof)}")
    prev, _ = harness.staged_ingest_views(inp)
    w(f"- based-at edges BEFORE the staged ingest: {[(e.source, e.target, e.status) for e in prev.edges if e.type == 'based-at']}")
    w(f"- based-at edges AFTER: {[(e.source, e.target, e.status) for e in view.edges if e.type == 'based-at']}")
except Exception:
    w("```"); w(traceback.format_exc()); w("```")
w()

w("## PLACES (resolved_place_ref present on any view node?)")
place_refs = Counter()
for n in view.nodes:
    rp = getattr(getattr(n, "location", None), "resolved_place_ref", None)
    if rp:
        place_refs[rp] += 1
w(f"- resolved_place_refs seen in view: {dict(place_refs)}")
for p in ak["ground_truth"]["places"]:
    w(f"    - oracle place {p['place_id']} ({p.get('precision_class')}) used_by={p.get('used_by', '-')}")
w()

(OUT / "00-evidence-summary.md").write_text(buf.getvalue(), encoding="utf-8")
print(f"wrote evidence to {OUT}")
print(buf.getvalue()[:1500])
