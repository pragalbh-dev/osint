"""``python -m eval.extraction`` — the operator surface for the bake-off.

Two commands, plus one library entry point:

* ``preflight`` — evaluate every gate that can be judged **without spending an API call**, and print the
  gate table. Run this first: it is how you find out a candidate is already disqualified (floating model
  id, missing SDK, client not on the shipped ingest path, no key) before paying for N runs of it. It
  also reports whether the coreference output channel is live, because the top-weighted criterion cannot
  be measured without it.
* ``vlm-probe`` — the one deliberate experiment the imagery gate needs. Shows every exercisable
  candidate the *same* real corpus image through the *real* imagery lane and records PASS/FAIL per
  candidate. Costs exactly one standalone-image call per candidate. Without it the gate reads UNKNOWN,
  which blocks — deliberately: "we did not check" must never become "it works".
* the real bake-off is :func:`eval.extraction.runner.run_bakeoff`, called from a driver — **not** a
  subcommand here, and deliberately so. It needs the two labeled files *and* the document slice, and it
  has no "just use defaults" mode for either: the gold and the sub-oracle are supplied by the data hand,
  and a CLI that silently substituted something else would print a number for a comparison that did not
  happen. Two things the driver must pass explicitly, because neither can be defaulted honestly:

  - the pipeline ``ConfigBundle`` — and for the top-weighted criterion to be measurable at all it must be
    the flag-on one (:func:`eval.extraction.coref_channel.with_channel_on`), which costs a second
    extraction call per document. ``run_bakeoff`` refuses up front rather than discovering this after N
    paid runs;
  - the imagery evidence, recorded by ``vlm-probe`` — without it the VLM gate reads UNKNOWN and no
    candidate is eligible to win.

Every command loads ``.env`` first (see :mod:`.secrets`) and prints only the **names** it found. A key
value never reaches stdout, a log, or a stored artefact.
"""

from __future__ import annotations

import argparse
import sys

from . import coref_channel, secrets, vlm_probe
from .gates import non_negotiable_gate_names
from .policy import BakeoffConfig, load_bakeoff_config
from .runner import preflight


def _load_keys(config: BakeoffConfig) -> None:
    """Export ``.env`` names, then print which candidate keys are set. Names only, never values."""
    applied = secrets.load_env_file()
    if applied:
        print(f"keys: loaded {len(applied)} name(s) from .env: {', '.join(applied)}")
    else:
        print("keys: nothing loaded from .env (already set in the environment, or no file found)")
    present = secrets.key_names_present([c.key_env for c in config.candidates])
    for name, is_set in sorted(present.items()):
        print(f"       {name}: {'set' if is_set else 'NOT SET'}")
    print()


def _print_coref_channel() -> None:
    """State whether a model could express a coreference decision at all on the shipped config."""
    try:
        from chanakya import settings
        from chanakya.config.store import ConfigStore

        bundle = ConfigStore.seed_from(settings.config_dir()).snapshot()
    except Exception as exc:  # pragma: no cover - config is always loadable in this tree
        print(f"coref channel: could not read the pipeline config ({type(exc).__name__}: {exc})\n")
        return
    channel = coref_channel.inspect(bundle)
    state = "LIVE" if channel.measurable else f"UNAVAILABLE [{channel.cause}]"
    print(f"coref channel: {state} — {channel.detail}")
    if channel.remedy:
        print(f"               remedy: {channel.remedy}")
    print()


def _cmd_preflight(args: argparse.Namespace) -> int:
    config = load_bakeoff_config(args.config)
    _load_keys(config)
    _print_coref_channel()
    evidence = vlm_probe.load_evidence(args.evidence)
    reports = preflight(config, require_key=not args.ignore_keys, evidence=evidence)
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
    if not evidence:
        print("NB: no recorded imagery evidence was found, so the VLM gate reads UNKNOWN for everyone. "
              "Run `vlm-probe` to evidence it. A gate nobody ran is not a gate anybody passed.")
    deferred = non_negotiable_gate_names(config)
    if deferred:
        print("NB: these gates need measured numbers and are judged after the run, not here: "
              + ", ".join(deferred) + ". They are declared non-negotiable, so an unmeasured one blocks a "
              "winner — a candidate ELIGIBLE above still has them ahead of it.")
    print(f"{blocked}/{len(reports)} candidate(s) cannot win as configured, on the gates judgeable "
          "without spending anything.")
    return 0


def _cmd_vlm_probe(args: argparse.Namespace) -> int:
    """Spend one standalone-image call per candidate to turn the VLM gate from UNKNOWN into evidence."""
    from chanakya import settings
    from chanakya.config.store import ConfigStore

    config = load_bakeoff_config(args.config)
    _load_keys(config)
    bundle = ConfigStore.seed_from(settings.config_dir()).snapshot()
    image = args.image or vlm_probe.default_image_path()
    wanted = set(args.candidates) if args.candidates else None

    records = vlm_probe.load_evidence(args.evidence)
    print(f"RK-BAKEOFF VLM imagery probe — image {image}\n")
    for candidate in config.candidates:
        if wanted is not None and candidate.id not in wanted:
            continue
        record = vlm_probe.probe_candidate(candidate, config=bundle, image_path=image)
        if record is None:
            print(f"  [SKIP] {candidate.id}: no client could be built "
                  f"(key env {candidate.key_env}, client "
                  f"{candidate.client_module}.{candidate.client_class}) — NOT probed, so its gate stays "
                  "UNKNOWN")
            continue
        records[candidate.id] = record
        gate, _ = vlm_probe.gate_from_evidence(candidate, records)
        print(f"  [{gate.status}] {candidate.id} (model={record.model_id}): "
              f"{record.calls_ok}/{record.calls_total} standalone-image call(s) returned"
              + (f" — {record.error}" if record.error else ""))
    written = vlm_probe.save_evidence(records, args.evidence)
    print(f"\nrecorded to {written}")
    print("A record is honoured only while its model_id matches the candidate's pinned model_id. "
          "Re-pin a candidate and its evidence goes stale — back to UNKNOWN, never inherited.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.extraction", description=__doc__)
    parser.add_argument("--config", default=None, help="path to bakeoff.yaml (default: config/)")
    sub = parser.add_subparsers(dest="command", required=True)

    pre = sub.add_parser("preflight", help="check gates without spending any API budget")
    pre.add_argument("--ignore-keys", action="store_true",
                     help="skip the key-presence gate (inspect the other gates on a keyless machine)")
    pre.add_argument("--evidence", default=None,
                     help="path to the recorded VLM-gate evidence (default: tmp/rk-bakeoff/)")
    pre.set_defaults(func=_cmd_preflight)

    probe = sub.add_parser("vlm-probe",
                           help="SPENDS BUDGET: one standalone-image call per candidate, to evidence "
                                "the PASS/FAIL imagery gate")
    probe.add_argument("--image", default=None,
                       help="image to show every candidate (default: the frozen corpus frame)")
    probe.add_argument("--evidence", default=None,
                       help="where to record the verdicts (default: tmp/rk-bakeoff/)")
    probe.add_argument("--candidates", nargs="*", default=None,
                       help="restrict to these candidate ids")
    probe.set_defaults(func=_cmd_vlm_probe)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
