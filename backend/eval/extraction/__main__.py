"""``python -m eval.extraction`` — the operator surface for the bake-off.

Three commands:

* ``preflight`` — evaluate every gate that can be judged **without spending an API call**, and print the
  gate table. Run this first: it is how you find out a candidate is already disqualified (floating model
  id, missing SDK, client not on the shipped ingest path, no key) before paying for N runs of it. It
  also reports whether the coreference output channel is live, because the top-weighted criterion cannot
  be measured without it.
* ``vlm-probe`` — the one deliberate experiment the imagery gate needs. Shows every exercisable
  candidate the *same* real corpus image through the *real* imagery lane and records PASS/FAIL per
  candidate. Costs exactly one standalone-image call per candidate. Without it the gate reads UNKNOWN,
  which blocks — deliberately: "we did not check" must never become "it works".
* ``run`` — **the bake-off itself.** Assembles the document slice, resolves the coref channel, runs N runs
  per candidate and renders the scorecard. It always prints the spend plan *before* spending, and
  ``--dry-run`` walks the identical path with a scripted client for zero calls, which is how you verify the
  whole thing works without paying for it.

  ``run_bakeoff`` remains a library function that defaults none of its inputs, and this command supplies
  them from declared artefacts rather than from constants typed into a CLI (see :mod:`.driver`): the
  document slice is read off the gold's own ``docs`` list, each document's source type and co-located
  frames come from the pipeline's source registry, and the imagery evidence comes from ``vlm-probe``'s
  recorded artefact. The one thing it must actively arrange is the pipeline ``ConfigBundle``: the
  top-weighted criterion is unmeasurable while extraction pass 2 is dormant, so the command switches it on
  for the bundle it hands the runner (:func:`eval.extraction.coref_channel.with_channel_on`) — in memory,
  never on disk — and reports that it did, because it roughly doubles the call count.

Every command loads ``.env`` first (see :mod:`.secrets`) and prints only the **names** it found. A key
value never reaches stdout, a log, or a stored artefact.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import coref_channel, driver, secrets, vlm_probe
from .gates import non_negotiable_gate_names
from .policy import BakeoffConfig, load_bakeoff_config
from .render import render_markdown, to_json
from .runner import BakeoffInputs, live_client_factory, preflight, run_bakeoff

#: Where the data hand's adapted artefacts live. Defaults, not fallbacks: if a file is absent the command
#: says so and stops, because substituting a different answer file would print a number for a comparison
#: that did not happen.
DEFAULT_GOLD = Path("tmp/spike-rk/gold/claim-gold.bakeoff.json")
DEFAULT_SUB_ORACLE = Path("tmp/spike-rk/gold/sub-oracle.bakeoff.json")


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


def _resolve_input(path: str | None, default: Path, what: str) -> Path:
    """A labeled input path — explicit, or the declared default. Absent is an error, never a substitution."""
    from chanakya import settings

    resolved = Path(path) if path else settings.repo_root() / default
    if not resolved.exists():
        raise SystemExit(
            f"the {what} is not at {resolved}. The bake-off will not run without it and will not "
            f"substitute anything else — pass --{what.replace(' ', '-')} explicitly, or ask the data hand "
            "to produce it."
        )
    return resolved


def _cmd_run(args: argparse.Namespace) -> int:
    """The bake-off. Prints the spend plan first, every time; ``--dry-run`` spends nothing."""
    from chanakya import settings
    from chanakya.config.store import ConfigStore

    config = load_bakeoff_config(args.config)
    if not args.dry_run:
        _load_keys(config)

    gold_path = _resolve_input(args.gold, DEFAULT_GOLD, "gold")
    oracle_path = _resolve_input(args.sub_oracle, DEFAULT_SUB_ORACLE, "sub oracle")

    # ── the pipeline config, and the coref channel decision ───────────────────────────────────────
    bundle = ConfigStore.seed_from(settings.config_dir()).snapshot()
    shipped = coref_channel.inspect(bundle)
    coref_on = not args.no_coref
    if coref_on and not shipped.measurable:
        bundle = coref_channel.with_channel_on(bundle)
    channel = coref_channel.inspect(bundle)
    coref_on = channel.measurable
    print(f"coref channel: {'LIVE' if channel.measurable else f'UNAVAILABLE [{channel.cause}]'}"
          f" — {channel.detail}")
    if not channel.measurable:
        print(f"               remedy: {channel.remedy}")
    elif not shipped.measurable:
        print("               switched on for THIS RUN'S bundle only (in memory; config/ untouched). "
              "It costs a second extraction call per document — that is the range in the plan below.")
    print()

    # ── the slice, and the plan ───────────────────────────────────────────────────────────────────
    docs = driver.build_slice(gold_path, bundle)
    wanted = list(args.candidates) if args.candidates else [c.id for c in config.candidates]

    # A candidate failing a gate judgeable WITHOUT a run cannot win at any score, so every call spent on
    # it buys nothing decision-relevant. Skipping it by default is not hiding it: `run_bakeoff` records a
    # candidate that was not exercised, and the scorecard prints why, so the comparison still reports
    # itself as narrowed. --include-blocked buys their numbers anyway as a diagnostic.
    evidence = vlm_probe.load_evidence(args.evidence) if args.evidence else None
    blocked = driver.blocked_before_spending(
        config, candidate_ids=wanted, evidence=evidence, require_key=not args.dry_run)
    if blocked:
        print("already disqualified on gates judgeable without a run:")
        for cid, why in blocked.items():
            print(f"  [BLOCKED] {cid}: {why}")
        if args.include_blocked:
            print("  --include-blocked: running them anyway. Their calls cannot change the winner.\n")
        else:
            wanted = [c for c in wanted if c not in blocked]
            print("  skipped, so no budget is spent on a candidate that cannot win "
                  "(--include-blocked to override).\n")
    if not wanted:
        raise SystemExit(
            "every requested candidate is disqualified on a gate judgeable without a run, so there is "
            "nothing left to compare and nothing worth spending. Fix a gate or pass --include-blocked to "
            "buy the diagnostic numbers anyway."
        )

    plan = driver.plan_spend(
        docs, candidate_ids=wanted, runs_per_candidate=config.replication.runs_per_candidate,
        coref_pass=coref_on, dry=args.dry_run,
    )
    print(f"gold:        {gold_path}")
    print(f"sub-oracle:  {oracle_path}")
    print(plan.render())
    print()
    if not plan.frames:
        raise SystemExit(
            "the slice contains no image, so the imagery gate would read UNKNOWN and every candidate "
            "would be disqualified. That is the gate working, not a bug — but it makes the run worthless, "
            "so this refuses before spending. The slice's image rides on a source registry entry's "
            "`images`; check the registry and the corpus frame."
        )

    if not args.dry_run and not args.yes:
        reply = input("proceed and spend the above? [y/N] ").strip().lower()
        if reply not in ("y", "yes"):
            print("aborted; nothing spent.")
            return 1

    out_dir = Path(args.out) if args.out else settings.repo_root() / "tmp/rk-bakeoff/run"
    inputs = BakeoffInputs(
        docs=docs, config=bundle, gold_path=gold_path, sub_oracle_path=oracle_path,
        out_dir=out_dir / "bundles", concurrency=args.concurrency,
    )
    factory = driver.dry_client_factory if args.dry_run else live_client_factory
    result = run_bakeoff(
        inputs, config, factory,
        candidates=wanted,
        require_key=not args.dry_run,
        evidence=evidence,
    )

    # ── the scorecard ─────────────────────────────────────────────────────────────────────────────
    markdown = render_markdown(result.scores, result.verdict, result.comparisons, result.config,
                               result.composite)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "scorecard.md").write_text(markdown, encoding="utf-8")
    (out_dir / "scorecard.json").write_text(
        to_json(result.scores, result.verdict, result.comparisons, result.config), encoding="utf-8")
    print(markdown)
    print(f"\nscorecard: {out_dir / 'scorecard.md'}  (+ .json, + per-run bundles under "
          f"{out_dir / 'bundles'})")
    # The spend actually incurred, against the range projected before it was. Pass 2 is conditional, so
    # this is the only number that closes the loop on the estimate.
    spent = sum(r.calls_total for s in result.scores for r in s.runs)
    images = sum(r.image_calls_total for s in result.scores for r in s.runs)
    print(f"\nCALLS ACTUALLY MADE: {spent}  (projected {plan.total_floor}–{plan.total_ceiling}; "
          f"of these {images} were standalone-image calls)")
    if not plan.total_floor <= spent <= plan.total_ceiling:
        print("  NB: the actual count fell OUTSIDE the projected range — the plan's model of the call "
              "pattern is wrong and should be corrected before it is used to budget a live run.")
    if args.dry_run:
        print("DRY RUN — every score above came from a scripted client and means nothing about any model. "
              "What it demonstrates is the path: assembly, both passes, the imagery lane, the rebuild, "
              "the gates and the verdict.")
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

    run = sub.add_parser("run", help="SPENDS BUDGET unless --dry-run: the bake-off itself — N runs per "
                                     "candidate over the labeled slice, then the scorecard")
    run.add_argument("--dry-run", action="store_true",
                     help="exercise the entire path with a scripted client and ZERO API calls")
    run.add_argument("--yes", action="store_true",
                     help="skip the confirmation prompt (for a live run in a non-interactive shell)")
    run.add_argument("--gold", default=None, help=f"adapted claim gold (default: {DEFAULT_GOLD})")
    run.add_argument("--sub-oracle", default=None,
                     help=f"adapted sub-oracle (default: {DEFAULT_SUB_ORACLE})")
    run.add_argument("--out", default=None,
                     help="where the scorecard and per-run bundles go (default: tmp/rk-bakeoff/run)")
    run.add_argument("--evidence", default=None,
                     help="recorded VLM-gate evidence (default: the recorded artefact)")
    run.add_argument("--candidates", nargs="*", default=None, help="restrict to these candidate ids")
    run.add_argument("--concurrency", type=int, default=8, help="parallel extraction calls (default 8)")
    run.add_argument("--include-blocked", action="store_true",
                     help="run candidates already disqualified on a dry gate. Buys their diagnostic "
                          "numbers; cannot change the winner")
    run.add_argument("--no-coref", action="store_true",
                     help="do NOT switch extraction pass 2 on. Halves the call count and leaves the "
                          "top-weighted criterion unmeasured, which blocks a winner — a deliberate, "
                          "recorded choice, not a shortcut")
    run.set_defaults(func=_cmd_run)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
