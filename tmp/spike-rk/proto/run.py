#!/usr/bin/env python3
"""RK-SPIKE characterize-and-cluster prototype.

    python3 tmp/spike-rk/proto/run.py --cases <input.json> --out <output.json>

Pure standard library. No API key, no network, no app boot, no embeddings.
Deterministic: no clock, no RNG, every collection sorted before emission, so
identical input yields byte-identical output.

Throwaway prototype. Nothing outside `tmp/spike-rk/proto/` is touched.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import characterize as ch          # noqa: E402
import derive                      # noqa: E402
import judge as judging            # noqa: E402
import protoconfig                 # noqa: E402
import strings                     # noqa: E402


def _read_case(case: dict) -> tuple[dict, dict, dict]:
    mentions_by_doc: dict[str, list[ch.Mention]] = {}
    edges_by_doc: dict[str, list[ch.EdgeRec]] = {}
    mention_by: dict[tuple[str, str], ch.Mention] = {}
    for doc in case.get("documents") or []:
        doc_id = str(doc.get("doc_id"))
        grade = str(doc.get("source_grade") or "")
        bucket: list[ch.Mention] = []
        for raw in doc.get("mentions") or []:
            m = ch.Mention(
                doc_id=doc_id,
                local_id=str(raw.get("local_id")),
                surface=str(raw.get("surface") or ""),
                entity_type=str(raw.get("entity_type") or "unknown"),
                # An absent slot stays absent. Never invented, never None-filled.
                attrs={k: str(v) for k, v in (raw.get("attrs") or {}).items() if v is not None},
                coref=raw.get("coref") or None,
                contrast_group=raw.get("contrast_group") or None,
                source_grade=grade,
            )
            bucket.append(m)
            mention_by[(doc_id, m.local_id)] = m
        mentions_by_doc[doc_id] = sorted(bucket, key=lambda m: ch.natkey(m.local_id))
        edges_by_doc[doc_id] = [
            ch.EdgeRec(doc_id=doc_id,
                       subject=str(e.get("subject_local_id")),
                       predicate=str(e.get("predicate") or ""),
                       object=str(e.get("object_local_id")),
                       kind=str(e.get("kind") or "observation"),
                       event_time=(str(e["event_time"]) if e.get("event_time") else None))
            for e in (doc.get("edges") or [])
        ]
    return mentions_by_doc, edges_by_doc, mention_by


def _display(inst: ch.Instance, slot: str, join: str) -> str:
    """Emit the STATED value(s). Comparison uses the normalized form; the analyst
    is shown what the source actually said (provenance discipline)."""
    values = inst.slots.get(slot) or []
    if not values:
        return "unknown"
    return join.join(sorted({stated for stated, _, _ in values}))


def run_case(case: dict, cfg: dict) -> dict:
    builder = ch.Builder(cfg)
    join = cfg["normalization"]["multivalue_join"]
    mentions_by_doc, edges_by_doc, mention_by = _read_case(case)

    # ---- Tier 0 -----------------------------------------------------------
    atoms: list[ch.ReferentAtom] = []
    injected_local: list[dict] = []
    notes: list[dict] = []
    for doc_id in sorted(mentions_by_doc):
        a, inj, nts = builder.referent_atoms(doc_id, mentions_by_doc[doc_id])
        atoms.extend(a)
        injected_local.extend(inj)
        notes.extend(nts)
    atoms.sort(key=lambda a: (a.doc_id,
                              ch.natkey(sorted(a.member_local_ids, key=ch.natkey)[0]),
                              0 if a.declined else 1,
                              tuple(ch.natkey(m) for m in sorted(a.member_local_ids, key=ch.natkey))))
    for index, atom in enumerate(atoms, start=1):
        atom.referent_id = f"r{index}"

    # ---- characterize -----------------------------------------------------
    instances = builder.instances(atoms, edges_by_doc, mention_by)
    instances.sort(key=lambda i: (i.doc_ids[0],
                                  ch.natkey(sorted(i.member_claim_atoms, key=ch.natkey)[0])))
    for index, inst in enumerate(instances, start=1):
        inst.instance_id = f"i{index}"

    inst_of: dict[tuple[str, str], str] = {}
    for inst in instances:
        for key in inst.member_keys:
            inst_of[key] = inst.instance_id
    by_id = {i.instance_id: i for i in instances}
    time_scoped = set(cfg["relational"]["time_scoped_predicates"])
    for doc_id in sorted(edges_by_doc):
        for e in edges_by_doc[doc_id]:
            s = inst_of.get((doc_id, e.subject))
            o = inst_of.get((doc_id, e.object))
            if s is None or o is None:
                continue
            stamp = e.event_time if e.predicate in time_scoped else None
            by_id[s].neighbours.add(("out", e.predicate, o, stamp))
            by_id[o].neighbours.add(("in", e.predicate, s, stamp))

    # ---- Tier 1 -----------------------------------------------------------
    rarity = strings.Rarity(
        [strings.tokens(s, builder.norm.rules) for i in instances for s in i.surfaces],
        float(cfg["name_channel"]["rarity"]["smoothing"]),
    )
    injected = {(inst_of[(p["doc_id"], p["a"])], inst_of[(p["doc_id"], p["b"])])
                for p in injected_local
                if (p["doc_id"], p["a"]) in inst_of and (p["doc_id"], p["b"]) in inst_of}
    verdicts, uf = judging.run_fixpoint(instances, cfg, rarity, injected)

    # ---- derived edges + gaps --------------------------------------------
    edges, gaps = derive.derive(cfg, instances, verdicts, uf, notes)

    out = {
        "case_id": case.get("case_id"),
        "referent_atoms": [
            {
                "referent_id": a.referent_id,
                "doc_id": a.doc_id,
                "member_local_ids": sorted(a.member_local_ids, key=ch.natkey),
                # `authoritative` = the proposal cleared BOTH Tier-0 gates.
                # `declined` = the rebuild refused the grouping anyway (D-13.18).
                # The atom binds as one shared referent iff authoritative AND NOT
                # declined; both flags are reported so "cleared its gates and was
                # still declined" stays readable, which is the whole D-13.18 story.
                "authoritative": bool(a.authoritative),
                "category": a.category,
                "gate_results": dict(sorted(a.gate_results.items())),
                "declined": bool(a.declined),
                "decline_reason": a.decline_reason,
            }
            for a in atoms
        ],
        "instances": [
            {
                "instance_id": i.instance_id,
                "citizen": i.citizen,
                "discriminators": {slot: _display(i, slot, join)
                                   for slot in cfg["discriminators"]["bag"]},
                "doc_ids": sorted(set(i.doc_ids)),
                "member_referent_ids": sorted(i.member_referent_ids, key=ch.natkey),
                "member_claim_atoms": sorted(i.member_claim_atoms, key=ch.natkey),
            }
            for i in instances
        ],
        "pair_verdicts": [
            {
                "a": v.a, "b": v.b, "verdict": v.verdict,
                "signals": v.signals,
                "ceiling": v.ceiling, "ceiling_reason": v.ceiling_reason,
                "walls": sorted(v.walls), "same_doc": v.same_doc,
                "reason": v.reason,
            }
            for v in verdicts
        ],
        "derived_edges": edges,
        "gaps": gaps,
    }
    _assert_postconditions(out, cfg)
    return out


def _assert_postconditions(case_out: dict, cfg: dict) -> None:
    """Re-assert the D1 guard on the finished document, so a violating output
    cannot be written even if the derivation logic were changed."""
    required = cfg["relocation"]["drawn_requires_identity_status"]
    confirmed_pairs = {
        tuple(sorted((p["a"], p["b"])))
        for p in case_out["pair_verdicts"] if p["verdict"] == "confirmed"
    }
    fused = {x for pair in confirmed_pairs for x in pair}
    single = {i["instance_id"] for i in case_out["instances"]
              if len(i["member_claim_atoms"]) == 1}
    authoritative = {a["referent_id"] for a in case_out["referent_atoms"]
                     if a["authoritative"] and not a["declined"]}
    stated_ok = {
        i["instance_id"] for i in case_out["instances"]
        if set(i["member_referent_ids"]) & authoritative
    } | single
    withheld_subjects = {e["subject"] for e in case_out["derived_edges"] if not e["drawn"]}
    gap_subjects = {g["about"] for g in case_out["gaps"]}
    for e in case_out["derived_edges"]:
        if e["kind"] != "relocation":
            continue
        if e["drawn"]:
            subject = e["subject"]
            earned = subject in fused or subject in stated_ok or (
                " + " in subject and tuple(sorted(subject.split(" + "))) in confirmed_pairs)
            if not earned:
                raise AssertionError(
                    f"D1 VIOLATION: relocation drawn for {subject!r} whose identity is not "
                    f"{required}"
                )
        else:
            if not e.get("withheld_reason"):
                raise AssertionError(f"withheld relocation for {e['subject']!r} has no reason")
    for subject in sorted(withheld_subjects):
        if subject not in gap_subjects:
            raise AssertionError(
                f"withheld relocation for {subject!r} has no named gap — silence is the defect"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--config", default=None,
                        help="override the config path (defaults to proto-config.yaml beside run.py)")
    parser.add_argument("--expect", default=None,
                        help="compare the produced output against this file and exit non-zero on any diff")
    args = parser.parse_args(argv)

    cfg = protoconfig.load(args.config)
    with open(args.cases, encoding="utf-8") as fh:
        payload = json.load(fh)
    result = {"cases": [run_case(c, cfg) for c in payload.get("cases") or []]}
    text = json.dumps(result, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)

    if args.expect:
        with open(args.expect, encoding="utf-8") as fh:
            expected = json.load(fh)
        if expected != result:
            print(_first_diff(expected, result), file=sys.stderr)
            return 1
        print(f"OK: {len(result['cases'])} case(s) match {args.expect}")
    return 0


def _first_diff(expected, actual, path: str = "") -> str:
    if type(expected) is not type(actual):
        return f"MISMATCH at {path or '<root>'}: type {type(expected).__name__} != {type(actual).__name__}"
    if isinstance(expected, dict):
        for key in sorted(set(expected) | set(actual)):
            if key not in expected:
                return f"MISMATCH at {path}: unexpected key {key!r}"
            if key not in actual:
                return f"MISMATCH at {path}: missing key {key!r}"
            if expected[key] != actual[key]:
                return _first_diff(expected[key], actual[key], f"{path}.{key}")
        return "no diff found"
    if isinstance(expected, list):
        if len(expected) != len(actual):
            return f"MISMATCH at {path}: length {len(expected)} != {len(actual)}"
        for index, (e, a) in enumerate(zip(expected, actual)):
            if e != a:
                return _first_diff(e, a, f"{path}[{index}]")
        return "no diff found"
    return f"MISMATCH at {path}:\n  expected: {expected!r}\n  actual:   {actual!r}"


if __name__ == "__main__":
    raise SystemExit(main())
