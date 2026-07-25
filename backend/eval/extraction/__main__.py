"""``python -m eval.extraction`` — the operator surface for the bake-off.

Two commands:

* ``preflight`` — evaluate every gate that can be judged **without spending an API call**, and print the
  gate table. Run this first: it is how you find out a candidate is already disqualified (floating model
  id, missing SDK, client not on the shipped ingest path, no key) before paying for N runs of it.
* ``run`` — the real bake-off. Requires the labeled inputs (paths) and a document slice, and *will* spend
  API budget for every candidate that can be exercised.

``run`` deliberately has no "just use defaults" mode for the labeled inputs: the gold and the sub-oracle
are supplied by the data hand, and a harness that silently substituted something else would report a
number for a comparison that did not happen.
"""

from __future__ import annotations

import argparse
import sys

from .policy import load_bakeoff_config
from .runner import preflight


def _cmd_preflight(args: argparse.Namespace) -> int:
    config = load_bakeoff_config(args.config)
    reports = preflight(config, require_key=not args.ignore_keys)
    print(f"RK-BAKEOFF preflight — {len(reports)} declared candidate(s)")
    print(f"replication: {config.replication.runs_per_candidate} runs/candidate "
          f"(ranking refused below {config.replication.min_runs_for_ranking})")
    print(f"margin: max({config.margin.min_absolute}, {config.margin.noise_multiplier} x pooled SD)\n")
    blocked = 0
    for report, candidate in zip(reports, config.candidates, strict=True):
        eligible = "ELIGIBLE" if report.eligible else "BLOCKED"
        if not report.eligible:
            blocked += 1
        print(f"  [{eligible}] {candidate.id}  model={candidate.model_id}")
        for gate in report.gates:
            print(f"      {gate.status:<8} {gate.name}: {gate.detail}")
        print()
    print("NB: the VLM imagery gate can only read UNKNOWN here — nothing was exercised. A gate nobody "
          "ran is not a gate anybody passed.")
    print(f"{blocked}/{len(reports)} candidate(s) cannot win as configured.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.extraction", description=__doc__)
    parser.add_argument("--config", default=None, help="path to bakeoff.yaml (default: config/)")
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight", help="check gates without spending any API budget")
    pre.add_argument("--ignore-keys", action="store_true",
                     help="skip the key-presence gate (inspect the other gates on a keyless machine)")
    pre.set_defaults(func=_cmd_preflight)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
