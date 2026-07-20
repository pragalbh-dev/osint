"""``python -m eval`` — the operator-facing runners for the acceptance harness.

One command today:

* ``beat [--scenario …] [--stage <doc_id> …]`` — drive the **relocation tripwire off a staged live
  ingest**. The named documents are held out of the evidence log, the graph is rebuilt, then they are
  ingested and the graph is rebuilt again; MONITOR's delta evaluator runs over that before/after pair and
  the fired alerts are printed with their provenance. This is the transaction-time shape of an alert —
  "new evidence arrived and the tripwire tripped" — not a scripted reveal and not a date rewind
  (``eval.harness.staged_ingest_views``, RCA D-P4.5). Keyless, offline, byte-identical on every run.
"""

from __future__ import annotations

import argparse
import json
import sys

from eval import harness


def _basing_rows(view: object) -> list[str]:
    """One line per ``based-at`` edge in a view — the operator's before/after eyeball check."""
    rows = []
    for edge in sorted(getattr(view, "edges", []), key=lambda e: e.id):
        if edge.type == "based-at":
            flag = f"  superseded_by={edge.superseded_by}" if edge.superseded_by else ""
            rows.append(f"    {edge.source} -> {edge.target}  [{edge.status}]{flag}")
    return rows


def _cmd_beat(args: argparse.Namespace) -> int:
    """Stage the relocation evidence in, print the before/after basing state and the fired alerts."""
    staged = tuple(args.stage) or harness.STAGED_RELOCATION_DOCS
    inp = harness.load_scenario(args.scenario)
    before, after = harness.staged_ingest_views(inp, staged_docs=staged)

    print(f"staged ingest: holding back {', '.join(staged)} ({inp.claim_count} claims in the full log)")
    print("\n  BEFORE (that evidence not yet ingested):")
    print("\n".join(_basing_rows(before)) or "    (no based-at edges)")
    print("\n  AFTER (evidence ingested):")
    print("\n".join(_basing_rows(after)) or "    (no based-at edges)")

    alerts = harness.fire_relocation_observable(inp, staged_docs=staged)
    print(f"\n  ALERTS FIRED: {len(alerts)}")
    for alert in alerts:
        print(json.dumps(alert.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse args and dispatch. Returns a process exit code (0 = ran; non-zero = bad invocation)."""
    parser = argparse.ArgumentParser(prog="python -m eval", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_beat = sub.add_parser("beat", help="run the relocation tripwire off a staged live ingest")
    p_beat.add_argument("--scenario", default=harness.DEFAULT_SCENARIO)
    p_beat.add_argument(
        "--stage", action="append", default=[],
        help=f"source doc to stage in (repeatable; default: {' '.join(harness.STAGED_RELOCATION_DOCS)})",
    )
    p_beat.set_defaults(func=_cmd_beat)
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover - process entry point
    sys.exit(main())
