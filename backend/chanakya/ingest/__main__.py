"""``python -m chanakya.ingest`` — the INGEST command line (SHIP wires ``make extract`` to it).

Two subcommands, one per side of the KEYLESS ≡ LIVE split (see :mod:`chanakya.ingest.seed`):

* ``extract --scenario <name>`` — the **keyed recorder.** Resolve a live extraction client from the
  environment (``GEMINI_API_KEY`` / ``ANTHROPIC_API_KEY``); if none is present, exit non-zero rather than
  fabricate — the frozen bundles can only be *re*-recorded with a real model. Re-freezes every bundle for
  the scenario in place under ``corpus/scenarios/<scenario>/claims`` with the pinned ingest time, so the
  output is byte-stable and diffable against the checked-in baseline.
* ``seed --scenario <name>`` — the **keyless boot check.** Append the scenario's frozen bundles into a
  fresh in-memory evidence log and report the claim count — a fast, side-effect-free validation that the
  keyless path parses and loads (the same path the app boot runs).
"""

from __future__ import annotations

import argparse
import sys

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest import adapters, seed
from chanakya.ingest.client import build_extraction_client
from chanakya.schemas import ConfigBundle
from chanakya.store.log import EvidenceLog


def _load_config() -> ConfigBundle:
    """Snapshot the live config bundle from ``config/*.yaml`` (offline yaml read; no secrets)."""
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _cmd_extract(args: argparse.Namespace) -> int:
    """Re-record the frozen bundles for a scenario (needs an extraction key)."""
    client = build_extraction_client()
    if client is None:
        print(
            "no extraction client: set GEMINI_API_KEY or ANTHROPIC_API_KEY to (re)record bundles",
            file=sys.stderr,
        )
        return 2
    config = _load_config()
    # The keyed recorder geocodes live: gazetteer coord-cache (offline, byte-stable for the anchors) →
    # Nominatim (open world). ``--offline`` restricts to the gazetteer for a fully-deterministic re-record.
    geocoder = adapters.build_geocoder(config, online=not args.offline)
    written = seed.extract_corpus(
        args.scenario, client=client, config=config, ingest_time=seed.FROZEN_INGEST_TIME,
        geocoder=geocoder,
    )
    for path in written:
        print(f"wrote {path}")
    print(f"recorded {len(written)} bundle(s) for scenario {args.scenario!r}")
    return 0


def _cmd_seed(args: argparse.Namespace) -> int:
    """Validate the keyless boot path: append a scenario's frozen bundles and report the count."""
    bundles_dir = settings.corpus_dir() / "scenarios" / args.scenario / "claims"
    if not bundles_dir.is_dir():
        print(f"no claim bundles at {bundles_dir}", file=sys.stderr)
        return 2
    count = seed.seed_store_from_bundles(EvidenceLog(), bundles_dir)
    print(f"seeded {count} claim(s) from {bundles_dir}")
    return 0


def _cmd_attribute(args: argparse.Namespace) -> int:
    """Propose attribution inferences over the frozen resolved view for a scenario (offline enrichment).

    Seeds the scenario's frozen claims, rebuilds the resolved view, and runs the connection-triggered
    proposer over it. ``--record`` freezes the proposed inferences as ``*__attr.json`` bundles (keyless boot
    then materialises them); otherwise the inferences are appended and the view re-rebuilt to show them
    co-located. Needs an extraction key (like ``extract``) — keyless boot already loads any frozen bundles.
    """
    bundles_dir = settings.corpus_dir() / "scenarios" / args.scenario / "claims"
    if not bundles_dir.is_dir():
        print(f"no claim bundles at {bundles_dir}", file=sys.stderr)
        return 2
    client = build_extraction_client()
    if client is None:
        print(
            "no extraction client: set GEMINI_API_KEY or ANTHROPIC_API_KEY to propose attributions "
            "(keyless boot already materialises any frozen *__attr.json inference bundles)",
            file=sys.stderr,
        )
        return 2
    config = _load_config()
    store = EvidenceLog()
    seed.seed_store_from_bundles(store, bundles_dir)

    from chanakya.ingest import attribute
    from chanakya.view.pipeline import rebuild

    if args.record:
        prev = rebuild(store, [], config)
        run = attribute.propose_attributions(
            prev, {c.claim_id: c for c in store.replay()}, config, client=client)
        for path in attribute.freeze_bundles(run, bundles_dir):
            print(f"wrote {path}")
    else:
        run = attribute.enrich(store, config, client=client)
    for skip in run.skipped:
        print(f"skip {skip.site_id}: {skip.reason}", file=sys.stderr)
    print(f"proposed {len(run.claims)} attribution(s); fired {len(run.fired)}, skipped {len(run.skipped)}")
    return 0


def _cmd_renormalize(args: argparse.Namespace) -> int:
    """Re-run the deterministic location canonicaliser over a scenario's frozen bundles.

    Offline and key-free by construction (no geocoder is injected), so it can only recover coordinates
    the source's own ``raw`` string already states — the recovery path for a coordinate an earlier
    recorder mis-classified. Dry-run by default; ``--apply`` writes, and either way every field edit is
    printed as a ``before -> after`` audit row.
    """
    bundles_dir = settings.corpus_dir() / "scenarios" / args.scenario / "claims"
    if not bundles_dir.is_dir():
        print(f"no claim bundles at {bundles_dir}", file=sys.stderr)
        return 2
    from chanakya.ingest import renormalize

    changes = renormalize.renormalize_bundles(bundles_dir, apply=args.apply)
    for change in changes:
        print(change)
    verb = "rewrote" if args.apply else "would rewrite (dry run; pass --apply)"
    print(f"{verb} {len({c.bundle for c in changes})} bundle(s), {len(changes)} field(s)")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse args and dispatch. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="python -m chanakya.ingest",
        description="INGEST corpus recorder + keyless seed loader.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="re-record frozen claim bundles for a scenario (keyed)")
    p_extract.add_argument("--scenario", required=True, help="scenario name, e.g. hq9p_primary")
    p_extract.add_argument("--offline", action="store_true",
                           help="geocode from the gazetteer only (no Nominatim) — deterministic re-record")
    p_extract.set_defaults(func=_cmd_extract)

    p_seed = sub.add_parser("seed", help="load a scenario's frozen bundles into a store (keyless)")
    p_seed.add_argument("--scenario", required=True, help="scenario name, e.g. hq9p_primary")
    p_seed.set_defaults(func=_cmd_seed)

    p_attr = sub.add_parser(
        "attribute", help="propose attribution inferences over the frozen resolved view (offline, keyed)")
    p_attr.add_argument("--scenario", required=True, help="scenario name, e.g. hq9p_primary")
    p_attr.add_argument("--record", action="store_true",
                        help="freeze proposed inferences as *__attr.json bundles; else append + re-rebuild")
    p_attr.set_defaults(func=_cmd_attribute)

    p_renorm = sub.add_parser(
        "renormalize",
        help="re-canonicalise locations in a scenario's frozen bundles (offline, keyless, auditable)")
    p_renorm.add_argument("--scenario", required=True, help="scenario name, e.g. hq9p_primary")
    p_renorm.add_argument("--apply", action="store_true",
                          help="write the bundles; without it the pass only reports what would change")
    p_renorm.set_defaults(func=_cmd_renormalize)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
