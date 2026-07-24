# Runbook — sandbox scenarios + the attribution georeference/signature promotion

Working note (not a committed artifact). Captures two reusable things from the attribution-location work
(PR #62, branch `feat/attribution-location`): **(A)** how to safely iterate on frozen claim bundles using a
throwaway *sandbox scenario*, and **(B)** the concrete recipe that made the imagery-corroboration
(attribution) inference fire end-to-end.

---

## A. The sandbox-scenario pattern (safe iteration on frozen bundles)

There is **no special sandbox machinery** — it falls out of the native multi-scenario design:

- A "scenario" is just a parallel folder: `corpus/scenarios/<name>/` with `docs/`, `claims/`,
  `answer_key.json`. Two ship today: `hq9p_primary` (the demo) and `hq9p_chaff`.
- The app picks which one boots from the **`CHANAKYA_SCENARIO`** env var (default `hq9p_primary`;
  see `api/state.py::scenario_bundles_dir`). Boot just globs `claims/*.json` — no extraction.

**The loop** (copy → point → iterate → promote → delete):

```bash
# 1. copy the primary scenario to a throwaway sandbox
cp -r corpus/scenarios/hq9p_primary corpus/scenarios/hq9p_sandbox

# 2. keep it out of git (working artifact only)
echo 'corpus/scenarios/hq9p_sandbox/' >> .gitignore   # (mind the trailing newline)

# 3. do the risky bundle edits against the sandbox (examples in section B)
#    verify against it:
CHANAKYA_SCENARIO=hq9p_sandbox CHANAKYA_ROOT=$(pwd) backend/.venv/bin/python -c \
  "from chanakya.api.state import build_default_state; s=build_default_state(scenario='hq9p_sandbox'); s.boot(); v=s.view(); print(len(v.nodes),'nodes',len(v.edges),'edges')"
# or serve it:  CHANAKYA_SCENARIO=hq9p_sandbox ... uvicorn chanakya.api.app:create_app --factory ...

# 4. once proven, apply the SAME recipe to hq9p_primary (the deliberate promotion)
# 5. delete the sandbox — it has served its purpose
rm -rf corpus/scenarios/hq9p_sandbox   # and drop the .gitignore line
```

Boot parity check: a fresh copy boots to the *identical* node/edge counts as primary — that confirms it's a
faithful twin before you start editing.

Why bother: re-recording or hand-editing the frozen bundles is exactly the kind of change that can corrupt
the answer key / hero demo. The sandbox lets you prove the whole recipe (including a full `pytest` + the
relocation `beat`) before a single byte of `hq9p_primary` moves.

---

## B. The attribution promotion recipe (what actually made it fire)

Goal: an overhead image corroborating a textual "HQ-9 present at X" report. Needs three things co-located at
one `basing_site`: **A** the subject-blind VLM shape observation, **C** a textual variant-presence claim,
**B** a reference-literature site-geometry fingerprint reachable *from the variant*. Three fixes were needed.

### B1. Image carries a georeference (location → the real site node) — DETERMINISTIC

- Drop a sidecar next to the frame: `corpus/scenarios/<sc>/docs/<image>.geo.json`, e.g.
  `{"location_text": "24.9012, 67.2034", "surface_format": "DD", "precision_class": "site"}`
  (any surface form `normalize_location` groks: DD / DMS / MGRS / toponym).
- Stamp it onto the frozen image observation **without re-extraction** (preserves curated structure):

  ```bash
  make georef SCENARIO=<sc>          # == python -m chanakya.ingest georef --scenario <sc>
  ```

  This is `seed.apply_geo_sidecars` → sets the image observation's `coordinates` attr. RESOLVE then **merges
  the frame onto its real basing_site by coordinate** at the next rebuild. Location is declared metadata,
  never inferred from pixels — the VLM stays subject-blind. (The live/record ingest path reads the same
  sidecar via `seed._read_geo_sidecar` in `_extract_source`.)
- **Do NOT** get the coordinate by re-recording the whole doc: a fresh LLM extract drifts/fragments the
  curated structure (observed with d17 — its clean "HQ-9B observed-at" became an untyped "HQ-9B fire unit").

### B2. Reference vs observed signature (so the matcher can reach B) — PROMPT NUDGE

- The matcher hunts for the fingerprint on the **variant** and its `equips`/`inducted-into` neighbours,
  never on sites. A site's *observed* geometry belongs on the site; a system-*type* signature belongs on the
  variant. The extractor only had a `signature_geometry` slot on `SiteMention`, so type signatures were
  always dropped.
- Fix (in `extract.py`): `signature_geometry` field added to `VariantMention`, mapped to the variant's
  `site_signature_geometry` attr at all three variant-construction sites; plus a scoped nudge appended to
  `_SYSTEM_BASE` that records a type signature on the variant **only when a source explicitly generalises**
  ("consistent with prior HQ-9 deployments", "the characteristic X layout") — never promoting one site's
  observation into a fake type signature.
- Apply by **re-extracting a reference-class doc** so its signature lands on the variant. For the demo that
  was `d25_hq9_site_fingerprint` (a curated-register PDF already in the corpus describing the HQ-9 petal
  layout). Gotcha: PDFs route through Azure OCR when `AZURE_*` env is set — **unset the AZURE vars** to use
  the pymupdf text layer (keep the GEMINI/ANTHROPIC key). Every source_id must have a `config/sources.yaml`
  entry or the matcher treats it as non-reference-class and skips it.

### B3. Fire + freeze the inference (visible at boot)

```bash
python -m chanakya.ingest attribute --scenario <sc> --record   # keyed; runs the corroboration call
```

Emits `<source>__attr.json` (e.g. `d07_sat_confirm_karachi__attr.json`), which boot globs like the
`__basing.json` bundles — so the cited, `decoy_risk`-capped inference materialises **at boot, keyless**.

### Verify

- Boot check: the presence edge's `claim_ids` include the `...-attr` inference; `integrity_flags` include
  `decoy-risk`.
- Drawer payload: `GET /evidence/{edge_id}` returns the "Inferred" relationship claim with **both** citations
  (image + literature) and the decoy caveat — this is what the LiveDrawer renders.
- Regression: full `pytest` (from `backend/`, with `CHANAKYA_ROOT`) + `python -m eval beat` (relocation
  tripwire) must stay green.

---

## What was actually promoted to hq9p_primary (PR #62)

- **d07** (a real HQ-9 petal frame, relabeled to Karachi): georeferenced → merged onto the Malir/Karachi
  emplacement.
- **d25** (HQ-9 site-recognition register PDF): re-extracted with the nudge → petal signature on the `HQ-9`
  variant. (Note: 21 → 13 claims, LLM variance; answer key refs d25 at *source* level only, so safe.)
- **d07_sat_confirm_karachi__attr.json**: the frozen inference — *HQ-9/P TEL observed-at Karachi
  emplacement*, 4 features matched, `decoy_risk=True`, cites the d07 image + the d25 reference.
- The corroboration is a genuine model match (petal image vs petal reference) and **declines** on ambiguous
  frames (the Nur Khan/d17 image reads as a generic developed area → "not consistent") — anti-fabrication
  guardrail working.

## Gotchas / honest limitations

- The graph UI opens **node** drawers, not edge drawers; the attribution is an edge inference, so a
  pixel-perfect drawer screenshot via automated canvas clicks was unreliable — verified via `GET /evidence`
  instead. A real interactive click shows it; a small node-side surfacing could make it appear on a node
  drawer too (roadmap).
- Keyed re-extraction needs `google-genai` (Gemini) and, for PDFs, `azure-ai-documentintelligence` installed
  in the venv (both are optional extras).
- Prefer deterministic passes (georef) over full re-records wherever possible — LLM re-extraction is the main
  source of frozen-bundle drift.
