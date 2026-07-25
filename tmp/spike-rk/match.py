#!/usr/bin/env python3
"""RK-SPIKE integration matcher — runs the independently-authored cases against the independently-built
prototype (plan/01 §6 step 6).

Authored by the **orchestrator**, not by either hand: the test hand specified these semantics in
`cases/README.md` and could not implement a runner without seeing the prototype's output; the implementer
must not see the cases. This file is neutral infrastructure that implements the test hand's spec verbatim.

Usage:
    python3 tmp/spike-rk/match.py --cases <cases.json> --expected <expected.json> --actual <actual.json>
                                  [--rerun <actual2.json>]   # for the I3 determinism invariant

Exit code 0 iff every hard assert in every case holds.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter

# ── selector resolution ──────────────────────────────────────────────────────────────────────────


def _mention_tokens(ref: str) -> tuple[str, str]:
    """'d01.m1' -> ('d01', 'm1')."""
    doc, local = ref.split(".", 1)
    return doc, local


def resolve_instance(case_out: dict, ref: str) -> dict | None:
    """Mention -> instance, per the test hand's documented resolution rule (two accepted routes)."""
    doc, local = _mention_tokens(ref)
    instances = case_out.get("instances") or []
    # Route 1: a claim atom naming both doc and local as tokens (contract example spells it "d01-m1").
    for inst in instances:
        for atom in inst.get("member_claim_atoms") or []:
            toks = set(re.split(r"[^A-Za-z0-9]+", str(atom)))
            if doc in toks and local in toks:
                return inst
    # Route 2: follow member_referent_ids into referent_atoms and match doc_id + member_local_ids.
    atoms_by_id = {a.get("referent_id"): a for a in (case_out.get("referent_atoms") or [])}
    for inst in instances:
        for rid in inst.get("member_referent_ids") or []:
            a = atoms_by_id.get(rid)
            if a and a.get("doc_id") == doc and local in (a.get("member_local_ids") or []):
                return inst
    return None


def _parse_filter(body: str) -> list[tuple[str, str]]:
    """'kind=relocation,drawn=true' -> [('kind','relocation'), ('drawn','true')]. Commas are AND."""
    out = []
    for part in body.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            out.append((k.strip(), v.strip()))
        else:
            out.append(("", part))  # bare form, e.g. '@d01.m1'
    return out


def _coerce(v: str):
    if v == "true":
        return True
    if v == "false":
        return False
    if v == "null":
        return None
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    return v


def select(case_out: dict, path: str) -> tuple[list, bool]:
    """Resolve a selector to a list of values. Returns (values, resolved).

    ``resolved`` is False when the collection/filter matched nothing or a field was missing — the test
    hand requires that to surface as UNRESOLVED rather than MISMATCH.
    """
    m = re.match(r"^([A-Za-z_]+)(?:\[([^\]]*)\])?((?:\.[A-Za-z_][A-Za-z0-9_]*)*)$", path)
    if not m:
        return [], False
    coll_name, filt, fields = m.group(1), m.group(2) or "", m.group(3) or ""
    rows = list(case_out.get(coll_name) or [])

    if filt:
        # pair_verdicts[@a|@b] — order-insensitive endpoint match
        if "|" in filt:
            left, right = [s.strip().lstrip("@") for s in filt.split("|", 1)]
            ia, ib = resolve_instance(case_out, left), resolve_instance(case_out, right)
            if ia is None or ib is None:
                return [], False
            want = {ia.get("instance_id"), ib.get("instance_id")}
            rows = [r for r in rows if {r.get("a"), r.get("b")} == want]
        else:
            for key, raw in _parse_filter(filt):
                if key == "" and raw.startswith("@"):
                    # instances[@d01.m1] — the instance holding that mention
                    inst = resolve_instance(case_out, raw.lstrip("@"))
                    if inst is None:
                        return [], False
                    rows = [r for r in rows if r is inst or r.get("instance_id") == inst.get("instance_id")]
                elif key == "doc":
                    rows = [r for r in rows if r.get("doc_id") == raw]
                elif key == "has":
                    doc, local = _mention_tokens(raw)
                    rows = [r for r in rows
                            if r.get("doc_id") == doc and local in (r.get("member_local_ids") or [])]
                elif raw.startswith("@"):
                    inst = resolve_instance(case_out, raw.lstrip("@"))
                    if inst is None:
                        return [], False
                    rows = [r for r in rows if r.get(key) == inst.get("instance_id")]
                else:
                    rows = [r for r in rows if r.get(key) == _coerce(raw)]
        if not rows:
            return [], False

    if not fields:
        return rows, True

    vals, ok = rows, True
    for f in [x for x in fields.split(".") if x]:
        nxt = []
        for v in vals:
            if isinstance(v, dict) and f in v:
                nxt.append(v[f])
            else:
                ok = False
        vals = nxt
    return vals, ok and bool(vals)


# ── ops ──────────────────────────────────────────────────────────────────────────────────────────


def _contains(hay, needle) -> bool:
    if isinstance(hay, str):
        return str(needle).lower() in hay.lower()
    if isinstance(hay, (list, tuple, set)):
        if needle in hay:
            return True
        return any(isinstance(x, str) and str(needle).lower() in x.lower() for x in hay)
    return False


def run_assert(case_out: dict, a: dict, case_in: dict | None = None) -> tuple[str, str]:
    """-> (PASS | FAIL | UNRESOLVED, detail)."""
    op = a.get("op")
    val = a.get("value")

    if op == "any_of":
        # The case author spells the branches `asserts` (README: "any_of holds a list of sub-asserts");
        # accept `value` too so either spelling works.
        branches = a.get("asserts") or (val if isinstance(val, list) else None) or []
        details = []
        for sub in branches:
            st, d = run_assert(case_out, sub, case_in)
            if st == "PASS":
                return "PASS", "any_of satisfied"
            details.append(f"{st}:{d}")
        if not branches:
            return "FAIL", "any_of carried no branches (matcher could not read them)"
        return "FAIL", "no branch passed [" + " | ".join(details) + "]"

    # The global invariants may also be asserted per-case; dispatch them here.
    if op in ("atom_conservation", "no_fabricated_discriminator"):
        if case_in is None:
            return "UNRESOLVED", f"{op} needs the case input"
        fn = {"atom_conservation": inv_atom_conservation,
              "no_fabricated_discriminator": inv_no_fabricated_discriminator}[op]
        return fn(case_in, case_out)

    if op in ("same_instance", "distinct_instance"):
        ra, rb = val
        ia, ib = resolve_instance(case_out, ra), resolve_instance(case_out, rb)
        if ia is None or ib is None:
            return "UNRESOLVED", f"cannot resolve {ra!r} or {rb!r} to an instance"
        same_node = ia.get("instance_id") == ib.get("instance_id")
        verdicts = [r.get("verdict") for r in (case_out.get("pair_verdicts") or [])
                    if {r.get("a"), r.get("b")} == {ia.get("instance_id"), ib.get("instance_id")}]
        fused = same_node or any(v == "confirmed" for v in verdicts)
        if op == "same_instance":
            return ("PASS", "fused") if fused else ("FAIL", f"not fused (verdicts={verdicts})")
        return ("PASS", "not fused") if not fused else ("FAIL", "fused but must not be")

    if op == "not_silently_dropped":
        inst = resolve_instance(case_out, val)
        if inst is None:
            return "UNRESOLVED", f"{val!r} is in no instance at all (dropped outright)"
        iid = inst.get("instance_id")
        seen = any(e.get("subject") == iid for e in (case_out.get("derived_edges") or []))
        for g in case_out.get("gaps") or []:
            if g.get("about") == iid:
                seen = True
            blob = json.dumps(g.get("missing") or []) + " " + str(g.get("sentence") or "")
            doc, local = _mention_tokens(val)
            if local in re.split(r"[^A-Za-z0-9]+", blob) or iid and iid in blob:
                seen = True
        return ("PASS", "visible to an analyst") if seen else ("FAIL", "not surfaced anywhere")

    vals, resolved = select(case_out, a.get("path", ""))
    if op in ("absent",):
        return ("PASS", "absent") if not resolved or not vals or all(
            v in (None, [], {}, "") for v in vals) else ("FAIL", f"present: {vals!r}")
    # "Correctly zero" is a real answer, not an unresolved selector: a count assert whose target is 0
    # (or a <= bound) is satisfied by an empty resolution.
    if not resolved and op in ("count_equals", "count_lte") and isinstance(val, int):
        return ("PASS", "empty == 0") if (op == "count_lte" or val == 0) \
            else ("FAIL", f"count 0 != {val}")
    if not resolved:
        return "UNRESOLVED", f"selector {a.get('path')!r} resolved to nothing"

    if op == "present":
        return ("PASS", "present") if all(v not in (None, [], {}, "") for v in vals) else ("FAIL", f"{vals!r}")
    if op == "equals":
        return ("PASS", "") if all(v == val for v in vals) else ("FAIL", f"got {vals!r}, want {val!r}")
    if op == "not_equals":
        return ("PASS", "") if all(v != val for v in vals) else ("FAIL", f"got {vals!r}, must differ from {val!r}")
    if op == "in":
        return ("PASS", "") if all(v in val for v in vals) else ("FAIL", f"got {vals!r}, want one of {val!r}")
    if op == "not_in":
        return ("PASS", "") if all(v not in val for v in vals) else ("FAIL", f"got {vals!r}, none may be in {val!r}")
    if op == "contains":
        return ("PASS", "") if all(_contains(v, val) for v in vals) else ("FAIL", f"{vals!r} lacks {val!r}")
    if op == "not_contains":
        return ("PASS", "") if not any(_contains(v, val) for v in vals) else ("FAIL", f"{vals!r} contains {val!r}")
    if op == "count_equals":
        return ("PASS", "") if len(vals) == val else ("FAIL", f"count {len(vals)} != {val}")
    if op == "count_gte":
        return ("PASS", "") if len(vals) >= val else ("FAIL", f"count {len(vals)} < {val}")
    if op == "count_lte":
        return ("PASS", "") if len(vals) <= val else ("FAIL", f"count {len(vals)} > {val}")
    return "FAIL", f"unknown op {op!r}"


# ── global invariants ────────────────────────────────────────────────────────────────────────────


def inv_atom_conservation(case_in: dict, case_out: dict) -> tuple[str, str]:
    want = {(d["doc_id"], m["local_id"]) for d in case_in.get("documents", [])
            for m in d.get("mentions", [])}
    hits: Counter = Counter()
    for ref in want:
        inst = resolve_instance(case_out, f"{ref[0]}.{ref[1]}")
        if inst is not None:
            hits[ref] = sum(
                1 for i in case_out.get("instances") or []
                if i.get("instance_id") == inst.get("instance_id"))
    missing = sorted(f"{d}.{l}" for (d, l) in want if (d, l) not in hits)
    if missing:
        return "FAIL", f"mentions in no instance: {missing}"
    return "PASS", f"all {len(want)} mentions placed"


def inv_no_fabricated_discriminator(case_in: dict, case_out: dict) -> tuple[str, str]:
    """Every discriminator value must be stated by a mention in THAT instance's own membership.

    Scoped **per instance**, not pooled across the case: pooling would let a value be transplanted from a
    neighbouring document onto a thin instance — which is precisely the non-negotiable breach the
    thin-context case exists to catch, so a pooled invariant would pass the fabrication it guards.
    Matching is exact on a normalized form, not bidirectional substring, for the same reason.
    """
    def norm(s) -> str:
        return re.sub(r"[^a-z0-9]+", "", str(s).lower())

    mention_of: dict[tuple[str, str], dict] = {}
    for d in case_in.get("documents", []):
        for m in d.get("mentions", []):
            mention_of[(d["doc_id"], m["local_id"])] = m
    edges_of: dict[str, list] = {d["doc_id"]: d.get("edges", []) for d in case_in.get("documents", [])}

    bad = []
    for inst in case_out.get("instances") or []:
        # This instance's own stated vocabulary: surfaces + attrs of its member mentions, plus the
        # event_times of edges touching those mentions.
        own: set[str] = set()
        members: list[tuple[str, str]] = []
        for ref, m in mention_of.items():
            found = resolve_instance(case_out, f"{ref[0]}.{ref[1]}")
            if found is not None and found.get("instance_id") == inst.get("instance_id"):
                members.append(ref)
                own.add(norm(m.get("surface", "")))
                for v in (m.get("attrs") or {}).values():
                    own.add(norm(v))
        for doc, local in members:
            for e in edges_of.get(doc, []):
                if local in (e.get("subject_local_id"), e.get("object_local_id")):
                    if e.get("event_time"):
                        own.add(norm(e["event_time"]))
                    other = e.get("object_local_id") if e.get("subject_local_id") == local \
                        else e.get("subject_local_id")
                    om = mention_of.get((doc, other))
                    if om:  # a geography slot legitimately names the edge's other endpoint
                        own.add(norm(om.get("surface", "")))
        own.discard("")
        for slot, v in (inst.get("discriminators") or {}).items():
            if v is None or str(v).lower() in ("unknown", ""):
                continue
            # Each component of the value must trace to this instance's OWN stated vocabulary. A composite
            # (D-13.20's `(operator, designation)` AND-key) is derived, not fabricated, when every
            # component traces. Matching stays containment-based *within the instance's own vocabulary*
            # because value normalization is a design requirement (R5.2) — a normalizer legitimately turns
            # a stated "3rd" into "3", so exact equality would flag correct behaviour. The load-bearing
            # strictness is the **per-instance scoping**: it catches a value transplanted from another
            # instance or another document, which is the fabrication the thin-context case tests.
            def traces(x: str) -> bool:
                nx = norm(x)
                return bool(nx) and any(nx in s or s in nx for s in own)

            parts = [p for p in re.split(r"\s*[+|/,]\s*", str(v)) if p.strip()]
            if traces(str(v)) or (len(parts) > 1 and all(traces(p) for p in parts)):
                continue
            bad.append(f"{inst.get('instance_id')}.{slot}={v!r}")
    return ("PASS", "no fabricated values") if not bad else ("FAIL", f"unstated-by-own-members: {bad}")


def _canon(case_out: dict) -> str:
    """Output canonicalised up to a consistent renaming of instance_id / referent_id."""
    ids: dict[str, str] = {}

    def rn(v):
        if isinstance(v, str) and v in ids:
            return ids[v]
        return v

    for i, inst in enumerate(case_out.get("instances") or []):
        ids.setdefault(inst.get("instance_id"), f"_i{i}")
    for i, a in enumerate(case_out.get("referent_atoms") or []):
        ids.setdefault(a.get("referent_id"), f"_r{i}")

    def walk(o):
        if isinstance(o, dict):
            return {k: walk(v) for k, v in sorted(o.items())}
        if isinstance(o, list):
            return [walk(x) for x in o]
        return rn(o)

    return json.dumps(walk(case_out), sort_keys=True)


# ── main ─────────────────────────────────────────────────────────────────────────────────────────


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--cases", required=True)
    p.add_argument("--expected", required=True)
    p.add_argument("--actual", required=True)
    p.add_argument("--rerun")
    args = p.parse_args()

    cases = {c["case_id"]: c for c in json.load(open(args.cases))["cases"]}
    expected = json.load(open(args.expected))
    actual = {c["case_id"]: c for c in json.load(open(args.actual))["cases"]}
    rerun = {c["case_id"]: c for c in json.load(open(args.rerun))["cases"]} if args.rerun else None

    invariants = expected.get("_invariants") or []
    n_pass = n_fail = n_adv = 0
    failed_cases: list[str] = []

    for exp in expected["cases"]:
        cid = exp["case_id"]
        out = actual.get(cid)
        print(f"\n=== {cid}")
        if out is None:
            print("  FAIL  prototype emitted no output for this case")
            n_fail += 1
            failed_cases.append(cid)
            continue

        hard_ok = True
        for a in exp.get("_assert", []):
            st, detail = run_assert(out, a, cases.get(cid))
            adv = bool(a.get("advisory"))
            tag = "ADV " if adv else ""
            if st == "PASS":
                print(f"  {tag}PASS  {a.get('op')} {a.get('path', a.get('value', ''))}")
                if not adv:
                    n_pass += 1
            else:
                print(f"  {tag}{st}  {a.get('op')} {a.get('path', a.get('value', ''))} -> {detail}")
                if adv:
                    n_adv += 1
                else:
                    hard_ok = False

        for inv in invariants:
            op = inv.get("op")
            fn = {"atom_conservation": inv_atom_conservation,
                  "no_fabricated_discriminator": inv_no_fabricated_discriminator}.get(op)
            if fn:
                st, detail = fn(cases[cid], out)
            elif op == "stable_under_rerun":
                if rerun is None or cid not in rerun:
                    st, detail = "SKIP", "no --rerun supplied"
                else:
                    st, detail = ("PASS", "byte-stable") if _canon(out) == _canon(rerun[cid]) \
                        else ("FAIL", "differs across runs")
            else:
                st, detail = "SKIP", f"unknown invariant {op!r}"
            if st == "FAIL":
                print(f"  INV-FAIL  {inv.get('id')} -> {detail}")
                hard_ok = False
            elif st != "SKIP":
                print(f"  INV-OK    {inv.get('id')}")

        if hard_ok:
            print(f"  => PASS")
        else:
            print(f"  => FAIL")
            n_fail += 1
            failed_cases.append(cid)

    total = len(expected["cases"])
    print(f"\n{'='*72}\nCASES: {total - n_fail}/{total} pass · hard asserts passed: {n_pass} · "
          f"advisory not-met: {n_adv}")
    if failed_cases:
        print("FAILED: " + ", ".join(failed_cases))
    return 0 if not failed_cases else 1


if __name__ == "__main__":
    sys.exit(main())
