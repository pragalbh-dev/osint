#!/usr/bin/env python3
"""``make ingest`` / ``make ask`` client — talks to the **running app**, stdlib only.

Why HTTP and not an in-process call: the app is a single always-on process holding the append-only
logs and the rebuilt view in memory (``chanakya.api.state``). A live ingest is only meaningful *against
that process* — it appends, rebuilds, and re-evaluates the armed observables in place, which is exactly
the "new evidence arrived and the tripwire tripped" beat. A separate host process would rebuild its own
throwaway graph and exit, demonstrating nothing.

Stdlib only, on purpose: a reviewer who ran ``make run`` has Docker and nothing else — no virtualenv,
no installed backend. This must work for them.

    python3 deploy/chanakya-cli.py ingest --url http://127.0.0.1:8000 --doc corpus/.../d18.json
    python3 deploy/chanakya-cli.py ask    --url http://127.0.0.1:8000 --question "..."
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

TIMEOUT = 300  # a keyed extraction round-trip can be slow; a keyless bundle append is instant


def _post(url: str, path: str, payload: dict) -> dict:
    """POST JSON and return the decoded body, surfacing the server's error detail rather than a stack."""
    req = urllib.request.Request(
        url.rstrip("/") + path,
        data=json.dumps(payload).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        try:
            detail = json.loads(body).get("detail", body)
        except json.JSONDecodeError:
            detail = body
        print(f"error: the app returned HTTP {exc.code}: {detail}", file=sys.stderr)
        raise SystemExit(1) from None
    except urllib.error.URLError as exc:
        print(
            f"error: could not reach the app at {url} ({exc.reason}). Is it running? Try `make run`.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None


def _cmd_ingest(args: argparse.Namespace) -> int:
    """Ingest one document into the running app: a frozen claim bundle (keyless) or a raw doc (keyed).

    A ``.json`` file that parses as a list of claim records is sent down the **keyless** bundle lane —
    the reviewer default, and byte-for-byte what live extraction over that document produces. Anything
    else is sent as ``raw_text`` down the **keyed** lane, which the deployment must have enabled
    (``CHANAKYA_ENABLE_EXTRACTION=1`` plus a model key).
    """
    doc = Path(args.doc)
    if not doc.is_file():
        print(f"error: no such document: {doc}", file=sys.stderr)
        return 2

    payload: dict
    if doc.suffix == ".json":
        parsed = json.loads(doc.read_text())
        if not isinstance(parsed, list):
            print(f"error: {doc} is JSON but not a claim bundle (expected a list)", file=sys.stderr)
            return 2
        payload = {"bundle": parsed}
        lane = f"keyless bundle ({len(parsed)} claims)"
    else:
        payload = {
            "raw_text": doc.read_text(errors="replace"),
            "source_id": args.source_id or doc.stem,
            "source_type": args.source_type,
        }
        lane = f"keyed extraction (source_type={args.source_type})"

    print(f"ingesting {doc} via {lane} → {args.url}")
    result = _post(args.url, "/ingest", payload)
    print(f"  appended {len(result.get('appended_claim_ids', []))} claim(s); rebuilt={result.get('rebuilt')}")
    fired = result.get("alerts_fired") or []
    print(f"  ALERTS FIRED: {len(fired)}" + (f" → {', '.join(fired)}" if fired else ""))
    return 0


def _cmd_ask(args: argparse.Namespace) -> int:
    """Ask the running app a question and print the cited hop chain — or the honest refusal."""
    payload: dict = {"question": args.question}
    if args.subject:
        payload["subject"] = args.subject
    answer = _post(args.url, "/ask", payload)

    refusal = answer.get("refusal")
    if refusal:
        # A refusal is a first-class result, not an error: print it in full and exit 0.
        print("INSUFFICIENT EVIDENCE / CAPABILITY GAP")
        print(f"  kind:    {refusal.get('kind')}")
        print(f"  missing: {', '.join(refusal.get('missing') or []) or '-'}")
        print(f"  due:     {refusal.get('next_coverage_due') or 'unscheduled'}")
        print(f"  reason:  {refusal.get('reason')}")
        return 0

    for sub in answer.get("sub_questions") or []:
        print(f"  · {sub}")
    print()
    for hop in answer.get("hops") or []:
        print(
            f"  hop {hop.get('step')}: {hop.get('src')} --[{hop.get('edge')}]--> {hop.get('dst')}"
            f"   [{hop.get('observed_or_inferred')}]  cites {', '.join(hop.get('claim_ids') or [])}"
        )
    print()
    print(answer.get("answer") or "(no answer body)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="chanakya-cli", description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="base URL of the running app")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ing = sub.add_parser("ingest", help="ingest one document into the running app")
    p_ing.add_argument("--doc", required=True, help="path to a frozen claim bundle (.json) or a raw doc")
    p_ing.add_argument("--source-id", default=None, help="raw docs only; defaults to the filename stem")
    p_ing.add_argument("--source-type", default="osint_report", help="raw docs only (config/sources.yaml)")
    p_ing.set_defaults(func=_cmd_ingest)

    p_ask = sub.add_parser("ask", help="ask the running app a cited multi-hop question")
    p_ask.add_argument("--question", required=True)
    p_ask.add_argument("--subject", default="lens-hq9p-pk", help="subject lens (config/subjects.yaml)")
    p_ask.set_defaults(func=_cmd_ask)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
