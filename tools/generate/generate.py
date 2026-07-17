#!/usr/bin/env python3
"""Data-generation pipeline for Use Case C (reusable to A/B) — turns a scenario spec +
gathered real material + an operator catalogue into a FROZEN, messy, deception-laced corpus
the rest of the system ingests cold.

Design (see artifacts/md/10-data-generation-strategy.md):
  * unit of generation = the sourced CLAIM; the doc is a raw artifact carrying claims.
  * messiness = enumerable CORRUPTION operators; misinformation = enumerable DECEPTION operators
    (operators.yaml). Every operator's signal is EARNED IN THE TEXT, never a hidden flag (P2).
  * the generator stays BLIND to the ontology — it emits raw artifacts only.
  * per-doc source-registry + expected-behaviour go to answer_key.json (the verification oracle),
    NEVER into the doc text.
  * chaff docs (mode: chaff) are off-subject / echo / stale / spoof noise for the triage funnel.

Usage
-----
  python tools/generate/generate.py <scenario>.yaml            # generate (concurrent)
  python tools/generate/generate.py <scenario>.yaml --check    # coverage only, write nothing
  python tools/generate/generate.py <scenario>.yaml --only d01 d02
  python tools/generate/generate.py <scenario>.yaml --workers 8
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import glob
import json
import os
import pathlib
import sys
from functools import lru_cache

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "corpus" / "raw"
MANIFEST = RAW / "manifest.jsonl"
OPERATORS_YAML = pathlib.Path(__file__).resolve().parent / "operators.yaml"
TEMPLATE_SNIPPET_CHARS = 2500

MODEL = "claude-sonnet-5"   # user chose "use sonnet"
GEN_MAX_TOKENS = 2200
DEFAULT_WORKERS = 6


# ----------------------------------------------------------------------------- config/IO
def load_manifest() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    rows = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["id"]] = r
    return rows


@lru_cache(maxsize=1)
def load_operators() -> dict:
    if OPERATORS_YAML.exists():
        return yaml.safe_load(OPERATORS_YAML.read_text(encoding="utf-8")) or {}
    return {"corruption": {}, "deception": {}}


def pdf_text(p: pathlib.Path) -> str | None:
    import shutil
    import subprocess
    if shutil.which("pdftotext"):
        try:
            r = subprocess.run(["pdftotext", "-q", "-l", "6", str(p), "-"],
                               capture_output=True, text=True, timeout=60)
            if r.stdout.strip():
                return r.stdout
        except Exception:  # noqa: BLE001
            pass
    try:
        import pypdf
        reader = pypdf.PdfReader(str(p))
        return "\n".join((pg.extract_text() or "") for pg in reader.pages[:6])
    except Exception:  # noqa: BLE001
        return None


def resolve_template(pattern: str | None) -> tuple[str | None, str]:
    if not pattern:
        return None, "none"
    hits = [pathlib.Path(p) for p in glob.glob(str(ROOT / pattern))]
    hits.sort(key=lambda p: (".text.txt" not in p.name, p.suffix != ".txt", len(p.name)))
    for p in hits:
        if p.suffix in {".txt", ".csv", ".json"} or ".text.txt" in p.name:
            return p.read_text(encoding="utf-8", errors="ignore")[:TEMPLATE_SNIPPET_CHARS], "ok"
    for p in hits:
        if p.suffix == ".pdf":
            txt = pdf_text(p)
            if txt and txt.strip():
                return txt[:TEMPLATE_SNIPPET_CHARS], "ok"
    if hits:
        return None, f"binary_only:{hits[0].name}"
    return None, "missing"


def alias_ground_truth() -> str:
    p = RAW / "reference" / "wikipedia_hq9.txt"
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""


# ----------------------------------------------------------------------------- model
API_KEY_NAMES = ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY")


def _api_key() -> str | None:
    for name in API_KEY_NAMES:
        if os.environ.get(name):
            return os.environ[name]
    envf = ROOT / ".env"
    if envf.exists():
        env = {}
        for line in envf.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
        for name in API_KEY_NAMES:
            if env.get(name):
                return env[name]
    return None


@lru_cache(maxsize=1)
def _client():
    key = _api_key()
    if not key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=key)


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


# ----------------------------------------------------------------------------- prompt
def _op_signal(family: str, op: str) -> str:
    """Look up an operator's in-text signal instruction; fall back to the raw string
    (so free-text `messy:` entries still work)."""
    ops = load_operators().get(family, {}) or {}
    entry = ops.get(op)
    if isinstance(entry, dict):
        return entry.get("signal", op)
    return op  # free-text operator: use the string verbatim as guidance


def build_prompt(doc: dict, template_text: str | None, aliases: str) -> str:
    src = doc["source_class"]
    mode = doc.get("mode", "signal")
    corruption = list(doc.get("corruption") or doc.get("messy") or [])
    deception = list(doc.get("deception") or [])

    tmpl = (template_text
            or f"(no real specimen gathered yet — invent a plausible, real-looking {src} artifact format)")

    if mode == "chaff" and doc.get("off_subject"):
        head = (
            "You are generating ONE realistic OFF-SUBJECT NOISE document for a defense-OSINT TEST "
            "corpus whose main subject is Pakistan's HQ-9/P SAM. This document is CHAFF: it must be "
            "plausibly in the same collection stream but must NOT be about the HQ-9/P — a good triage "
            "system should recognise it as off-subject / low-relevance and sink it.\n\n"
            f"What this noise document is about: {doc.get('intent', 'unrelated defense/trade material')}\n\n"
        )
    else:
        head = (
            "You are generating ONE realistic open-source document for a defense-OSINT TEST corpus about "
            "Pakistan's HQ-9/P long-range surface-to-air missile system (a Chinese export). Synthetic data "
            "for testing an extraction + credibility pipeline.\n\n"
        )

    parts = [
        head,
        f"Emit ONLY the raw document text — the exact artifact a real '{src}' source would produce, in that "
        "real format. Do NOT output clean structured/ontology fields, JSON, analyst headers like 'Entities:', "
        "provenance blocks, bracketed flags, 'Notes:' lines, or any commentary — the pipeline must extract "
        "and judge everything itself. No preamble, no markdown fences.\n\n"
        "CRITICAL — a raw artifact does not debunk or resolve itself. Do NOT append any 'Note', 'Analyst "
        "note', 'Editor's note', 'Note on …', continuator, 'as of …' summary, disambiguation paragraph, or "
        "any sentence that RESOLVES, disambiguates, corroborates-away, or states a conclusion about the "
        "content — e.g. 'not to be confused with', 'unrelated / coincidental', 'traces back to one origin', "
        "'classic bot pattern', 'treat as provisional', 'still limited to', 'no additional entries located', "
        "'worth flagging for due diligence'. Those are the PIPELINE's job. Leave every ambiguity, collision, "
        "staleness, and duplication standing for the reader to infer from the facts (dates, names, wording, "
        "citations) alone.\n\n",
        f"Dateline / as-of date: {doc['date']}.\n\n",
    ]

    asserts = list(doc.get("asserts") or [])
    if asserts:
        parts.append("The document must naturally IMPLY these facts (never state them as tidy fields):\n"
                     + "\n".join("- " + a for a in asserts) + "\n\n")

    if corruption:
        parts.append("Apply these real-world MESSINESS patterns — authentic, not caricatured:\n"
                     + "\n".join("- " + _op_signal("corruption", c) for c in corruption) + "\n\n")

    if deception:
        parts.append(
            "Plant these DECEPTION signals directly in the raw text. CRITICAL: each must be DETECTABLE from "
            "the content itself (wording, timestamps, citations, source identity, near-duplication) — never "
            "stated as a flag, label, or explanation, and never resolved/debunked in the document. Leave the "
            "deception standing for the pipeline to catch:\n"
            + "\n".join("- " + _op_signal("deception", d) for d in deception) + "\n\n")

    parts.append(
        "Below is a real specimen to imitate for FORMAT, tone, and noise (copy its shape, NOT its entities). "
        "The specimen may carry a collector's provenance header / source-URLs / [flags] / 'Notes:' — that "
        "wrapper is NOT part of the artifact; reproduce ONLY the raw artifact(s), as they'd appear in the "
        "wild. If it's a feed of items, emit a comparable raw feed.\n---\n"
        f"{tmpl[:1800]}\n---\n\n")

    if aliases and mode != "chaff":
        parts.append(
            "Where entity names appear, use realistic naming variance from this ground-truth alias set as "
            "appropriate (transliterations, export vs domestic designators, radar-vs-system names):\n"
            f"{aliases[:1000]}\n\n")

    parts.append("Output only the document.")
    return "".join(parts)


def _stub(doc: dict, template_text: str | None) -> str:
    tmpl = template_text or "(no template)"
    return (f"[{doc['source_class'].upper()} | {doc['date']}]  (STUB — no API key)\n"
            f"intent: {'; '.join(doc.get('asserts') or [doc.get('intent', '')])}\n"
            f"--- format ---\n{tmpl[:400].strip()}\n")


def render_document(doc: dict, template_text: str | None, aliases: str) -> str:
    client = _client()
    if client is None:
        return _stub(doc, template_text)
    msg = client.messages.create(
        model=MODEL,
        max_tokens=GEN_MAX_TOKENS,
        thinking={"type": "disabled"},
        messages=[{"role": "user", "content": build_prompt(doc, template_text, aliases)}],
    )
    return _strip_fences("".join(b.text for b in msg.content if b.type == "text"))


# ----------------------------------------------------------------------------- answer key
def answer_key(spec: dict) -> dict:
    docs = []
    for d in spec["documents"]:
        docs.append({
            "id": d["id"],
            "source_class": d["source_class"],
            "date": d["date"],
            "mode": d.get("mode", "signal"),
            "asserts": d.get("asserts") or [],
            "off_subject": d.get("off_subject", False),
            "corruption": list(d.get("corruption") or d.get("messy") or []),
            "deception": list(d.get("deception") or []),
            "registry": d.get("registry", {}),          # ground-truth source-registry fields
            "expect": d.get("expect", {}),              # expected pipeline behaviour (verification oracle)
        })
    return {
        "ground_truth": spec.get("ground_truth", {}),
        "worked_query": spec.get("worked_query", {}),
        "observable": spec.get("observable", {}),
        "flexes": spec.get("flexes", {}),
        "documents": docs,
    }


# ----------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec")
    ap.add_argument("--check", action="store_true", help="coverage report only; write nothing")
    ap.add_argument("--only", nargs="*", help="only these doc ids")
    ap.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    args = ap.parse_args()

    spec = yaml.safe_load(pathlib.Path(args.spec).read_text(encoding="utf-8"))
    name = spec["meta"]["name"]
    out = ROOT / "corpus" / "scenarios" / name
    aliases = alias_ground_truth()

    documents = spec["documents"]
    if args.only:
        documents = [d for d in documents if d["id"] in set(args.only)]

    # resolve templates + coverage report
    print(f"scenario: {name}  ({spec['meta'].get('subject', '')})  [{len(documents)} docs]")
    resolved = {}
    for d in documents:
        text, status = resolve_template(d.get("template"))
        resolved[d["id"]] = text
        mark = {"ok": "✓", "none": "∅"}.get(status, "·")
        tags = []
        if d.get("mode") == "chaff":
            tags.append("chaff")
        if d.get("deception"):
            tags.append("dec:" + ",".join(d["deception"]))
        print(f"  {mark} {d['id']:<26} tmpl={status:<18} {' '.join(tags)}")

    if args.check:
        return 0

    out.mkdir(parents=True, exist_ok=True)
    docs_dir = out / "docs"
    docs_dir.mkdir(exist_ok=True)

    # concurrent render
    errors = {}

    def _one(d):
        try:
            return d["id"], render_document(d, resolved[d["id"]], aliases), None
        except Exception as e:  # noqa: BLE001
            return d["id"], None, f"{type(e).__name__}: {e}"

    done = 0
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for did, body, err in ex.map(_one, documents):
            done += 1
            if err:
                errors[did] = err
                print(f"  ✗ {did}: {err}")
                continue
            (docs_dir / f"{did}.txt").write_text(body, encoding="utf-8")
            print(f"  ✓ [{done}/{len(documents)}] {did} ({len(body)} chars)")

    # answer key over the FULL spec (not just the subset), so it stays complete.
    # Preserve any `image` metadata a prior attach_images pass wrote, so text-regen
    # doesn't clobber images (the two passes compose in any order).
    ak = answer_key(spec)
    ak_path = out / "answer_key.json"
    if ak_path.exists():
        try:
            prior = {d["id"]: d for d in json.loads(ak_path.read_text(encoding="utf-8")).get("documents", [])}
            for d in ak["documents"]:
                if "image" in prior.get(d["id"], {}):
                    d["image"] = prior[d["id"]]["image"]
        except Exception:  # noqa: BLE001
            pass
    ak_path.write_text(json.dumps(ak, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "SCENARIO_MANIFEST.json").write_text(
        json.dumps({"name": name, "n_docs": len(spec["documents"]),
                    "rendered_this_run": len(documents) - len(errors),
                    "observable": spec.get("observable", spec["meta"].get("observable")),
                    "errors": errors}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nfroze {len(documents) - len(errors)}/{len(documents)} docs -> {docs_dir.relative_to(ROOT)}/")
    print(f"answer key (eval-only) -> {(out/'answer_key.json').relative_to(ROOT)}")
    if errors:
        print(f"{len(errors)} error(s): {list(errors)}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
