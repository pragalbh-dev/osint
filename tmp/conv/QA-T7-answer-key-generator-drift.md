# QA-T7 → DATA-C: the scenario spec and the frozen answer key have diverged

**Raised by:** QA-T7 (Phase-4 residual #8), 2026-07-20, branch `qa/t7-phase4-residuals`.
**Status:** partially closed. The four dropped sustainment items are gone from the spec; the rest is a
DATA-C reconciliation job and is **not** fixed here.

---

## The mechanism, so the risk is concrete

`tools/generate/generate.py` builds `answer_key.json` as a **straight copy** of four blocks of the
scenario spec (`ground_truth`, `worked_query`, `observable`, `flexes`) plus a per-document projection.
It is not a merge and it does not preserve anything already in the file except a per-document `image`
key. So **any run of the generator overwrites the whole answer key with whatever the spec says**, even
`--only d06_spares_tender` (the key is rebuilt from the *full* spec by design, "so it stays complete").

The key has been hand-curated repeatedly since Phase 1. The spec has not been kept in step. That makes
the generator a loaded trap rather than a live defect: nothing is wrong today, and a single regeneration
silently undoes four phases of oracle work.

## Closed here

Removed from `tools/generate/scenarios/hq9p_primary.yaml`, with the reason recorded inline:

| Item | Kind |
|---|---|
| `sustain_techdata` | ground-truth node |
| `sustain_spares` | ground-truth node |
| `design-authority-for: sustain_techdata → var_hq9p` | ground-truth edge |
| `sustained-by: unit_paad → sustain_spares` | ground-truth edge |
| `single_source` flex | re-pointed off `sustain_spares` onto d17, matching the key verbatim |

Stale prose references to the same two nodes were also corrected in `artifacts/plan/sessions/EVAL.md`
(the "6 demo flexes" list) and `config/entities.yaml` (the not-seeded-entities note).

## NOT closed — what a regeneration would still destroy

Measured by diffing the spec against `corpus/scenarios/hq9p_primary/answer_key.json` after the above:

1. **The Phase-1 lane renames revert.** The key uses `supplies-component` for manufacturer→component and
   `equips` for component→variant. The spec still says `manufactures` / `candidate-manufactures` for the
   first and `supplies-component` for the second, and still carries `variant-of … "HQ-9"` and
   `imported-via` edges the key dropped.
2. **The deep tier disappears.** `mfr_taian` and `comp_tel_chassis` (and their two edges) exist only in
   the key.
3. **The `deep_tier_confirmed` flex disappears** — it exists only in the key.
4. **Documents d24 and d25 disappear from the key's document registry** — they exist only in the key.
5. **The whole `attribution_inference` block disappears.** `answer_key()` does not emit that field at
   all, so there is no spec edit that can preserve it — the generator itself needs a new field.
6. **Two flex wordings revert** — `single_source` (now aligned) and `adversary_denial_bypass`.

Node/edge counts after the sustainment removal: spec 16/21, key 18/19.

## Ask

Either (a) bring the spec up to the key and teach `answer_key()` to emit `attribution_inference`, then
prove it by regenerating into a scratch path and diffing to zero; or (b) decide the key is now the
hand-maintained artifact of record and make `generate.py` refuse to overwrite an existing
`answer_key.json` without an explicit `--force-key`. (b) is cheap and removes the trap outright; (a) is
the honest fix but is a real data pass. Until one of them lands: **regenerate documents only, and
restore `answer_key.json` from git afterwards.** A warning block saying exactly this now sits above
`ground_truth:` in the spec.
