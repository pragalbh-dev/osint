#!/usr/bin/env python3
"""Data-generation pipeline for Use Case C — turns a scenario spec + gathered
real material into a FROZEN, messy corpus the rest of the system ingests cold.

This is a SCAFFOLD. The one place you wire your model is `render_document()`.
Everything around it — spec loading, template resolution, answer-key emission,
flex-coverage checking, freezing — is done.

Contract for render_document (keep the generator BLIND to the ontology):
    in :  doc spec `asserts` (intent), the REAL template text to imitate,
          the alias ground truth, and the named `messy` operators to apply.
    out:  a raw document string (record/prose/caption) that *implies* the asserts
          via real-looking messiness — and contains NONE of your clean ontology
          fields. The pipeline must earn the extraction.

Usage
-----
    python tools/generate/generate.py tools/generate/scenarios/hq9p_primary.yaml
    python tools/generate/generate.py <spec>.yaml --check   # coverage report only
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
RAW = ROOT / "corpus" / "raw"
MANIFEST = RAW / "manifest.jsonl"
TEMPLATE_SNIPPET_CHARS = 2500


def load_manifest() -> dict[str, dict]:
    if not MANIFEST.exists():
        return {}
    rows = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["id"]] = r
    return rows


def pdf_text(p: pathlib.Path) -> str | None:
    """Extract text via pdftotext (poppler) if available, else pypdf."""
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


def resolve_template(pattern: str) -> tuple[str | None, str]:
    """Return (template_text, status). Reads a .text.txt / .txt if present,
    extracts PDFs, else flags that you still need to gather it."""
    hits = [pathlib.Path(p) for p in glob.glob(str(ROOT / pattern))]
    # prefer a readable text extract over raw html/pdf
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
        return None, f"binary_only:{hits[0].name}"      # present but no extractor
    return None, "missing"                              # not gathered yet -> falls back to 05 §2/§6


def alias_ground_truth() -> str:
    p = RAW / "reference" / "wikipedia_hq9.txt"
    return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""


def render_document(doc: dict, template_text: str | None, aliases: str) -> str:
    """<<< WIRE YOUR MODEL HERE >>>

    Replace the deterministic stub below with an LLM call, e.g.:

        prompt = build_prompt(asserts=doc['asserts'], template=template_text,
                              messy=doc['messy'], aliases=aliases,
                              source_class=doc['source_class'], date=doc['date'])
        return llm(prompt)            # anthropic / openai / local — your choice + keys

    The stub keeps the skeleton runnable and shows the exact structure the model
    should fill: real format on top, intent implied, messiness named — no clean
    ontology fields.
    """
    tmpl = (template_text or "(template not yet gathered — fall back to the real "
            "format sample in artifacts/md/05-data-scoping-C.md §2/§6)")
    return (
        f"[{doc['source_class'].upper()} | {doc['date']}]  (STUB — replace via render_document)\n"
        f"intent (hidden from pipeline): {'; '.join(doc['asserts'])}\n"
        f"messiness to apply: {', '.join(doc.get('messy', []) or ['—'])}\n"
        f"--- real format to imitate (excerpt) ---\n{tmpl[:600].strip()}\n"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("spec")
    ap.add_argument("--check", action="store_true", help="coverage report only; write nothing")
    args = ap.parse_args()

    spec = yaml.safe_load(pathlib.Path(args.spec).read_text(encoding="utf-8"))
    name = spec["meta"]["name"]
    out = ROOT / "corpus" / "scenarios" / name
    manifest = load_manifest()
    aliases = alias_ground_truth()

    # --- template resolution + coverage ---
    print(f"scenario: {name}  ({spec['meta']['subject']})")
    resolved, gaps = {}, []
    for d in spec["documents"]:
        text, status = resolve_template(d["template"])
        resolved[d["id"]] = text
        mark = {"ok": "✓"}.get(status, "·")
        if status != "ok":
            gaps.append((d["id"], d["template"], status))
        print(f"  {mark} {d['id']:<24} template={status}")

    # --- flex coverage: every flex needs all its docs to have usable seed ---
    print("\nflex coverage:")
    for fx, cfg in spec["flexes"].items():
        docs = cfg.get("docs", []) or ([cfg["trigger_doc"]] if "trigger_doc" in cfg else [])
        missing = [d for d in docs if resolved.get(d) is None]
        state = "READY" if not missing else f"needs: {', '.join(missing)}"
        print(f"  {'✓' if not missing else '·'} {fx:<28} {state}")

    if args.check:
        return 0

    # --- freeze: answer key + rendered docs ---
    out.mkdir(parents=True, exist_ok=True)
    (out / "answer_key.json").write_text(
        json.dumps({"ground_truth": spec["ground_truth"],
                    "worked_query": spec["worked_query"],
                    "flexes": spec["flexes"]}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    docs_dir = out / "docs"
    docs_dir.mkdir(exist_ok=True)
    for d in spec["documents"]:
        body = render_document(d, resolved[d["id"]], aliases)
        (docs_dir / f"{d['id']}.txt").write_text(body, encoding="utf-8")

    (out / "SCENARIO_MANIFEST.json").write_text(
        json.dumps({"name": name, "n_docs": len(spec["documents"]),
                    "observable": spec["meta"]["observable"],
                    "template_gaps": [{"doc": g[0], "template": g[1], "status": g[2]} for g in gaps]},
                   indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nfroze {len(spec['documents'])} docs -> {out.relative_to(ROOT)}/docs/")
    print(f"answer key (eval-only, NOT ingested) -> {(out/'answer_key.json').relative_to(ROOT)}")
    if gaps:
        print(f"\n{len(gaps)} docs used STUB/fallback templates (gather those sources on your "
              f"machine, re-run gather, then regenerate for real messiness).")
    print("\nNEXT: wire your model in render_document(), then re-run to get real messy docs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
