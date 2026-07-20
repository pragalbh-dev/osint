
## 2026-07-20 — T5 (map coverage): node attrs for location precision

Additive, node `attrs` only (same pattern as `place_match_*`), emitted by `view/pipeline.py`:

* `location_source` — `"stated-coordinate"` (a source gave the position) or `"gazetteer-anchor"`
  (the node resolved to a curated `config/places.yaml` anchor and borrowed its `canonical_dd`).
  Present only when the node is plotted.
* `location_uncertainty_radius_m` — the honest envelope radius, from `places.proximity_radius_m`
  for the node's `precision_class`. Absent when the precision class is unknown.

`Location.precision_class` gained a `province` rung (`pad|site|terminal|district|city|province`).

TS mirror fix, no backend change: `Location.raw` is `str | list[str]` in `values.py` and was typed
`string | null` in `frontend/src/api/types.ts`; widened to `string | string[] | null`.
