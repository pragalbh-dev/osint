# DATA-C — flex-protection changelog

Running log of DATA-C changes and the demo flex / acceptance item each protects. Kept per the ratified
decision record's handoff ("DATA-C: apply fixes and keep a flex-protection changelog"). Pending corpus/
answer_key/text fixes are tracked in `DATA-C-corpus-and-oracle-observations.md`.

## 2026-07-18 · Session `feat/data-c` (config authoring + generator reconcile)

### Generator reconcile (PART A items 2 & 4)
- **`tools/generate/generate.py`, `tools/generate/test_gemini_image.py`** — dropped `CLAUDE_API_KEY`; key on
  `ANTHROPIC_API_KEY` only (stack lock, master §1). Gemini/imagery paths intact.
  - *Protects:* keyless-boot + the reviewer run-modes (single secret name); **gate G11 stays green**
    (generator still imports no ontology; verified).

### Config authored — all 7 validate + hot-config round-trip through F0's config store (version 1→seed OK)
| File | What it protects (flex / acceptance) |
|---|---|
| `ontology.yaml` | Hero-trace chokepoint path (equips + supplies-component + manufactures); merge traps (`same-as`/`distinct-from`); Known-Gap + `observability_ceiling`. Represents every C/01 demo-subset type. |
| `sources.yaml` | Aggregator collapse (d01 SIPRI), aligned-interest (d02+d15), adversary-denial gate (d16), coordinated-inauthenticity cluster (d11-13/ce01-03), freshness (cadence). |
| `credibility.yaml` | confirmed-vs-probable separation (0.80/0.50), R rubric (Module 1), integrity/M4 penalties, adversary-denial + decoy-risk gates, per-edge freshness half-lives. |
| `resolution.yaml` | Alias/transliteration merges (FD-2000, Триумф); **withheld** Chaklala + H-200 orphan (earned-merge/adaptation beats); distinct-from traps (FT-2000, HQ-9BE). |
| `templates.yaml` | Insufficient-evidence / Known-Gap (the disqualifier): based-at sufficiency + never-observable classes (magazine depth, contract terms, C2, true readiness). |
| `subjects.yaml` | Subject-as-lens (G10); the 3 verbatim target queries; materiality scoping so chaff doesn't leak. |
| `observables.yaml` | Flagship relocation tripwire (Rawalpindi→Rahwali 2025); 2 config-only secondaries proving observables are declarative. |

### Ratified decisions applied in config (from the decision record)
- `supplies-component` reserved Mfr→Component; **`equips`** = Component→Variant hero edge.
- sustainment **split**: `interceptor_stockpile` (perishable) + `techdata_authority` (force-revalidated).
- **No** `candidate-*` edge types — candidate-ness is a computed edge status (ontology omits them).
- `variant-of` / `imported-via` **dropped**; `functional_role` identifiers; `operator_branch`.
- F7 structural cases **represented not instantiated** (roadmap): `substitutable-by` edge exists, only the
  UNKNOWN case is live.
- `source_type` vocabulary == `credibility.source_class_factors` keys (direct R lookup, no mapping layer).

### Alignment decisions logged (principle → choice → alt rejected)
- *Config-driven, no magic numbers (G6)* → all weights/thresholds/half-lives in `credibility.yaml`;
  integrity tables flattened `"<table>.<flag>"` (frozen field is flat `dict[str,float]`), gates as an extra
  `gates:` field — rejected: nested dicts (would break the typed field) / hardcoding in SCORE.
- *Two-scores separation* → `resolution.yaml` (identity) and `credibility.yaml` (truth) are disjoint files.

## 2026-07-18 (cont.) · Corpus / oracle / text fixes APPLIED (user directed "this session applies everything")

All edits below validate: `answer_key.json` parses; every ground_truth node type + edge rel ∈ `ontology.yaml`;
every document id ∈ `sources.yaml`; config store reseeds (52 sources). HT-233 chokepoint stays
`candidate`/`UNKNOWN` (F2 preserved); node statuses ∈ frozen `Status` Literal (no `candidate`).

| Fix | Files | Flex/acceptance protected |
|---|---|---|
| **F1** expected_path_edges → canonical direction + `equips` rename + `_note` | answer_key | hero-trace self-consistency |
| **equips rename** (Component→Variant); `supplies-component` reserved Mfr→Component | answer_key edges | hero chokepoint edge = config |
| **candidate-\*** edges → ordinary `manufactures`/`supplies-component` with `status: possible` | answer_key | candidate-ness = computed status, not edge type |
| **sustainment split** → `techdata_authority` + `interceptor_stockpile` node types | answer_key nodes | freshness semantics |
| **operator_branch** + **family** attrs; dropped dangling `variant-of` + `imported-via` | answer_key | ontology alignment |
| **enum casing** `probable_max`→`probable-max`; deep-tier nodes `candidate`→`possible` | answer_key | frozen F0 `Status`/`ObservabilityCeiling` |
| **d16** `source_class` official→social (keeps adversary-denial gate + grade D) | answer_key | adversary-denial-bypass flex honesty |
| **F5 confirmed deep-tier** — `mfr_taian`→`comp_tel_chassis` (supplies-component, confirmed) + `equips` var_hq9p; new **d24** doc; `deep_tier_confirmed` flex; 23rd RI/4th Academy stay `possible` | answer_key + `docs/d24…txt` + sources.yaml + manifest | F5 (evidence gate: source directly names supplier+component+relationship, not a bare sanctions listing) |
| **d19/d20 relocation contradiction** removed (Rahwali not pre-2025) | docs d19, d20 | flagship relocation observable |
| **d09** made official-only (removed embedded Jane's excerpt) | doc d09 | clean d08↔d09 CONTRADICTED flex |
| **d04** byline → Army Recognition (was "South Asia Defence Monitor", near-collision with d01) | doc d04 | entity-collision hygiene |
| **d20** pseudo-provenance "Verbatim (REAL…)" → "Text:" | doc d20 | oracle-boundary honesty |
| manifest `n_docs` 24→25 | SCENARIO_MANIFEST | corpus count |

### Deferred (documented, NOT applied — larger than a text edit / other session's ownership)
- **Per-fixture provenance sidecar** (content hash · origin kind · template lineage/hash · generator/version/
  spec hash · render time · image lineage) — a **generator/manifest-schema** task (tools/ + manifest.jsonl),
  not a corpus text edit. Images already carry `sha256_16`/`source`/`integrity`/`provenance`/`real_source`
  in the answer_key; a full non-ingested sidecar is a scoped follow-up.
- **Oracle-boundary ingest guardrail** (runtime accepts only `docs/**`; rejects scenario YAML/answer_key/
  manifest) → **INGEST** session (cross-session handoff).
- **product/04 §** stale line (FT-2000 distinctness supported by d04 not d01) — design-doc drift, outside
  DATA-C owned paths; left as a note for the doc owner (the corpus itself is correct — d04 carries it).
