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
from chanakya.ingest import seed
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
    written = seed.extract_corpus(
        args.scenario, client=client, config=_load_config(), ingest_time=seed.FROZEN_INGEST_TIME
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


def main(argv: list[str] | None = None) -> int:
    """Parse args and dispatch. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        prog="python -m chanakya.ingest",
        description="INGEST corpus recorder + keyless seed loader.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_extract = sub.add_parser("extract", help="re-record frozen claim bundles for a scenario (keyed)")
    p_extract.add_argument("--scenario", required=True, help="scenario name, e.g. hq9p_primary")
    p_extract.set_defaults(func=_cmd_extract)

    p_seed = sub.add_parser("seed", help="load a scenario's frozen bundles into a store (keyless)")
    p_seed.add_argument("--scenario", required=True, help="scenario name, e.g. hq9p_primary")
    p_seed.set_defaults(func=_cmd_seed)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
