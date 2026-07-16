# Corpus tooling — gather + generate (Use Case C)

Two stages that get you from "the internet" to a frozen, messy, multi-scenario
corpus the rest of the system ingests cold. You spend time on **judgement + one
config file**; the tooling does the collection and freezing.

```
tools/
  gather/    sources.yaml   gather.py       # Stage 1 — pull real OSINT (automated)
  generate/  generate.py    scenarios/*.yaml# Stage 2 — you configure; emits frozen corpus
corpus/
  raw/       manifest.jsonl <class>/...      # gathered real material (provenance-stamped)
  scenarios/ <name>/docs/   answer_key.json  # generated frozen corpora (per scenario)
```

Design source of truth: `../artifacts/md/05-data-scoping-C.md` (what's gettable + formats),
`../artifacts/C/` and `../artifacts/spine/` (ontology, credibility, flexes, observable).

---

## Stage 1 — Gather (automated)

```bash
python tools/gather/gather.py --list      # show the plan + what's auto-fetchable here
python tools/gather/gather.py             # fetch all auto-reachable; record the rest
python tools/gather/gather.py --subject hq9p
python tools/gather/gather.py --only wikipedia_hq9 quwa_hq9p --force
```

- Every source in `sources.yaml` gets a `corpus/raw/manifest.jsonl` row with url,
  fetch time, source class, sha256, and **status**. Nothing is silently skipped.
- `status: ok` — fetched here. `needs_residential_ip` / `needs_credentials` /
  `needs_manual` / `needs_manual_export` — real, free, but blocked from a datacenter
  IP, or needs an account / desktop tool / copy-paste.

**What you finish on your own machine** (residential IP unblocks most): SIPRI export
(`sipri_transfers`), ISPR + PIB (`proxy`), The Diplomat, NGA NAVAREA, a Copernicus
Sentinel-2 frame (incl. one cloud-covered), a Google Earth site frame, a YouTube
parade frame, an ImportYeti BoL row, and a handful of real X posts. Drop each into
`corpus/raw/<source_class>/` and re-run gather — the manifest tracks the rest.

To add a source: append an entry to `sources.yaml` (`method`, `source_class`, `url`/`title`).

---

## Stage 2 — Generate (you configure one YAML)

The config surface is a **scenario spec** — see `generate/scenarios/hq9p_primary.yaml`.
It encodes: the ground-truth answer-key graph, ~14 documents (each bound to a real
format template in `corpus/raw/`), and the six demo flexes + the observable.

```bash
python tools/generate/generate.py tools/generate/scenarios/hq9p_primary.yaml --check   # coverage only
python tools/generate/generate.py tools/generate/scenarios/hq9p_primary.yaml           # freeze the corpus
```

Output per scenario: `corpus/scenarios/<name>/docs/*.txt` (frozen, ingested cold) +
`answer_key.json` (eval only — **never fed to the pipeline**) + a coverage report of
which flexes have real seed material yet.

**Wire your model:** the one place to edit is `render_document()` in `generate.py`.
Its contract — in: the doc's `asserts` (intent), the real template text, the alias
ground-truth, the named `messy` operators; out: a raw messy document that *implies*
the intent and contains **no clean ontology fields** (the pipeline earns extraction).
Until you wire it, a deterministic stub keeps the skeleton runnable.

**Multiple scenarios:** copy the YAML, change `meta.name` + retune docs/flexes, run
again → a second frozen folder. That's the "point it at an unseen scenario on the
call" flex, with zero live-generation risk.

---

## The two guardrails (keep the demo credible)

1. **Generator blind to the ontology** — emits raw docs, never your schema fields.
2. **Real messiness, not imagined** — corruption operators are seeded from real
   specimens (ImportYeti rows, India MTD tender, NOTAM/NAVAREA strings, the real
   alias set), and every applied operator is named in the scenario spec, so you can
   say exactly what's in each doc. Keep ≥1 real uncurated doc from `corpus/raw` in
   the mix and process it cold.
