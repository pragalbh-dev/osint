#!/usr/bin/env python3
"""Automated OSINT corpus gatherer for Use Case C (HQ-9/P + China HQ-9).

Reads tools/gather/sources.yaml, fetches everything programmatically reachable,
and records provenance for *every* source (fetched or not) into
corpus/raw/manifest.jsonl.

Principles
----------
- Provenance-first: every artifact carries url, fetch time, source class, sha256.
- Honest about reach: sources that block datacenter IPs, need creds, a desktop
  tool, or manual copy-paste are NOT silently skipped. They get a manifest entry
  with status != "ok" and the instruction from sources.yaml, so you can finish
  them on your own (residential) machine.
- Idempotent: re-running skips artifacts already fetched "ok" unless --force.

Usage
-----
    python tools/gather/gather.py                 # gather all auto-reachable sources
    python tools/gather/gather.py --only wikipedia_hq9 csis_amti_woody
    python tools/gather/gather.py --subject hq9p  # only sources touching a subject
    python tools/gather/gather.py --force         # re-fetch even if already ok
    python tools/gather/gather.py --list          # show plan + reachability, fetch nothing
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys

import requests
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]          # .../osint/osint
RAW = ROOT / "corpus" / "raw"
MANIFEST = RAW / "manifest.jsonl"
SOURCES_YAML = pathlib.Path(__file__).resolve().parent / "sources.yaml"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 30

# Methods the script can execute here. Everything else is recorded as "needs you".
AUTO_METHODS = {"wikipedia", "auto_http"}
DEFERRED_STATUS = {  # method -> manifest status when we can't fetch it here
    "proxy":    "needs_residential_ip",
    "creds":    "needs_credentials",
    "manual":   "needs_manual",
    "download": "needs_manual_export",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_manifest(rows: list[dict]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with MANIFEST.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_manifest() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    out = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            out[r["id"]] = r
    return out


def ext_for(content_type: str, url: str) -> str:
    ct = (content_type or "").lower()
    if "pdf" in ct or url.lower().endswith(".pdf"):
        return "pdf"
    if "json" in ct:
        return "json"
    if "html" in ct:
        return "html"
    return "txt"


def save(source_class: str, sid: str, data: bytes, ext: str) -> pathlib.Path:
    d = RAW / source_class
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{sid}.{ext}"
    p.write_bytes(data)
    return p


def html_to_text(html: bytes) -> bytes:
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = "\n".join(t.strip() for t in soup.get_text("\n").splitlines() if t.strip())
        return text.encode("utf-8")
    except Exception:
        return html


# ---------- adapters ----------

def fetch_wikipedia(src: dict) -> dict:
    """Plain-text extract + last-revision timestamp (the freshness stamp)."""
    api = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query", "format": "json", "titles": src["title"],
        "prop": "extracts|revisions", "explaintext": 1,
        "rvprop": "timestamp|ids", "redirects": 1,
    }
    r = requests.get(api, params=params, headers={"User-Agent": UA}, timeout=TIMEOUT)
    r.raise_for_status()
    pages = r.json()["query"]["pages"]
    page = next(iter(pages.values()))
    extract = page.get("extract", "")
    rev_ts = page.get("revisions", [{}])[0].get("timestamp", "")
    body = f"# {page.get('title', src['title'])}\n# wikipedia revision: {rev_ts}\n\n{extract}"
    data = body.encode("utf-8")
    path = save(src["source_class"], src["id"], data, "txt")
    return {"status": "ok", "path": str(path.relative_to(ROOT)), "sha256": sha256(data),
            "http_status": 200, "source_rev": rev_ts, "bytes": len(data)}


def fetch_http(src: dict) -> dict:
    r = requests.get(src["url"], headers={"User-Agent": UA}, timeout=TIMEOUT)
    ext = ext_for(r.headers.get("content-type", ""), src["url"])
    if r.status_code != 200:
        return {"status": "error", "http_status": r.status_code,
                "note": f"HTTP {r.status_code} from datacenter IP; try method: proxy on your machine."}
    path = save(src["source_class"], src["id"], r.content, ext)
    row = {"status": "ok", "path": str(path.relative_to(ROOT)), "sha256": sha256(r.content),
           "http_status": 200, "bytes": len(r.content), "content_type": r.headers.get("content-type", "")}
    if ext == "html":  # also drop a readable text extract alongside the raw html
        txt = html_to_text(r.content)
        tp = save(src["source_class"], src["id"] + ".text", txt, "txt")
        row["text_path"] = str(tp.relative_to(ROOT))
    return row


def gather_one(src: dict) -> dict:
    method = src["method"]
    base = {"id": src["id"], "subjects": src.get("subjects", []),
            "source_class": src["source_class"], "method": method,
            "url": src.get("url", ""), "fetched_at": now_iso(),
            "notes": (src.get("notes") or "").strip()}
    try:
        if method == "wikipedia":
            base.update(fetch_wikipedia(src))
        elif method == "auto_http":
            base.update(fetch_http(src))
        else:  # deferred: record what you must do, fetch nothing
            base.update({"status": DEFERRED_STATUS.get(method, "needs_manual"),
                         "path": "", "sha256": "", "http_status": None})
    except Exception as e:  # noqa: BLE001
        base.update({"status": "error", "path": "", "sha256": "",
                     "note": f"{type(e).__name__}: {e}"})
    return base


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", nargs="*", help="source ids to gather")
    ap.add_argument("--subject", help="only sources touching this subject id")
    ap.add_argument("--force", action="store_true", help="re-fetch even if already ok")
    ap.add_argument("--list", action="store_true", help="print plan, fetch nothing")
    args = ap.parse_args()

    cfg = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))
    sources = cfg["sources"]
    if args.only:
        sources = [s for s in sources if s["id"] in set(args.only)]
    if args.subject:
        sources = [s for s in sources if args.subject in s.get("subjects", [])]

    prior = load_manifest()

    if args.list:
        for s in sources:
            auto = "AUTO " if s["method"] in AUTO_METHODS else "you  "
            print(f"  [{auto}] {s['id']:<28} {s['method']:<10} {s['source_class']}")
        print(f"\n{len(sources)} sources "
              f"({sum(s['method'] in AUTO_METHODS for s in sources)} auto-fetchable here).")
        return 0

    rows = dict(prior)  # keep entries for sources not in this run
    for s in sources:
        if not args.force and prior.get(s["id"], {}).get("status") == "ok":
            print(f"  skip (cached ok)   {s['id']}")
            continue
        row = gather_one(s)
        rows[s["id"]] = row
        flag = {"ok": "✓"}.get(row["status"], "·")
        print(f"  {flag} {row['status']:<22} {s['id']:<28} {row.get('note', row.get('path',''))}")

    write_manifest(list(rows.values()))

    ok = sum(r["status"] == "ok" for r in rows.values())
    todo = sum(r["status"].startswith("needs") for r in rows.values())
    err = sum(r["status"] == "error" for r in rows.values())
    print(f"\nmanifest: {MANIFEST.relative_to(ROOT)}  |  ok={ok}  needs-you={todo}  error={err}")
    if todo:
        print("Run the `needs_*` sources on your own machine (residential IP / creds / desktop),")
        print("drop files into corpus/raw/<source_class>/, and this manifest tracks the rest.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
