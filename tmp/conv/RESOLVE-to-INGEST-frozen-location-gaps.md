# RESOLVE → INGEST / DATA-C — two frozen-location gaps found while wiring the place-ref write-back (P3.4/P3.5)

**From:** RESOLVE (`fix/phase3-resolve`, Wave 3 — RES-3 place-ref write-back + RES-5 place gates)
**Status:** observations only — RESOLVE has **not** touched the corpus, `answer_key.json`, or `config/places.yaml`.

RESOLVE now persists its gazetteer match onto the node (`Location.resolved_place_ref` + the distance/band
that earned it). With that writer in place, two upstream gaps became visible. Neither is RESOLVE's to fix.

---

## 1. An MGRS grid was frozen as a toponym, so `site_rawalpindi` never gets its coordinate

`corpus/scenarios/hq9p_primary/claims/d17_rawalpindi_2021.json` — entity `PAF Base Nur Khan`:

- `coordinates.raw` = `"Grid: 43S CT 23715 21242 (MGRS, WGS84)"`
- `coordinates.surface_format` = `"toponym"` (it is an **MGRS** string)
- `coordinates.wgs84_lat` / `wgs84_lon` = `null`, `geocode_candidates` = `[]`
- `coordinates.proposed_alias` = the grid string itself

So the coord-canonicaliser's MGRS branch never ran. Consequence downstream: `site_rawalpindi` carries a
`Location` with no point, matches **no** gazetteer anchor, and therefore no `resolved_place_ref` — even
though `pl_nurkhan` is seeded with the real coordinate and the oracle says `pl_nurkhan used_by=site_rawalpindi`.
That is one of the two ends of the flagship **Rawalpindi → Rahwali relocation** story, so the map will show
the destination anchored and the origin unanchored.

**Ask (INGEST):** route a `surface_format` detection pass over the raw string (an `NNS XX NNNNN NNNNN`
shape is MGRS, not a toponym) so the existing MGRS branch fires and freezes `wgs84_lat/lon`.

**UPDATE (P3.6) — half of this is now worked around, the ask still stands.** RESOLVE now lets a mention
bind to a gazetteer anchor whose curated name it states *exactly*, even with no coordinate
(`place_bind_on_curated_toponym`). The entity's display name is `"PAF Base Nur Khan"`, a seeded alias of
`pl_nurkhan`, so `site_rawalpindi` now carries `resolved_place_ref = pl_nurkhan` (band `auto`, via
`toponym`, distance `None`). **It still has no coordinate of its own** — RESOLVE will not back-fill one
from the anchor, because a gazetteer coordinate is the *anchor's* provenance, not the document's, and
copying it would silently launder a claim the source never made. So anything plotting `wgs84_lat/lon`
(the map) still sees an origin with no point. Fixing the MGRS parse is what closes that.

---

## 2. The frozen bundles contain **no** Nominatim geocodes at all

Every `basing_site` in the frozen bundles except two (`d07` Malir, `d18` Rahwali — both `source: "coord-parse"`)
has `wgs84_lat/lon = null` and `geocode_candidates = []`. The EVAL-RCA's RES-5 symptom (`Army Air Defence
Centre` proximity-snapping to `pl_karachi_port` at 4478 m, and `fenced compound near a PAF airbase`
geocoding to a Bahawalpur mosque via "central Punjab") is therefore **not reproducible against the current
bundles** — those were recorded from a run with Nominatim geocoding enabled.

This is not a defect per se, but it matters for QA: RESOLVE's two new place gates (class compatibility +
geocode confidence) are **latent** against these bundles and are covered by unit tests instead. When the
keyed re-record lands with geocoding on, please make sure INGEST stamps a `confidence` on every
`geocode_candidate` — the RESOLVE gate reads it, and it treats an *unstated* confidence as UNKNOWN
(not blocked), so an unlabelled fuzzy geocode would still be eligible for proximity snapping.

**Ask (INGEST):** always populate `GeocodeCandidate.confidence`, and keep it genuinely lower for a
Nominatim hit on a vague regional phrase ("central Punjab", "Punjab province") than for a parsed coordinate.
