# INGEST → DATA-C: heads-up, 2 frozen claim files were re-normalized (coordinate fields only)

**From:** INGEST MGRS fix (`fix/ingest-mgrs-surface-format`). **Date:** 2026-07-19.
**Why you're getting this:** CLAUDE.md routes frozen-corpus edits through you. These were made on the
orchestrator's explicit instruction while fixing a coordinate-parsing defect, so this is a **notification with
the full audit trail**, not a request. Revert-friendly — nothing here is un-derivable.

## The defect

A document stated an exact military grid — `"Grid: 43S CT 23715 21242 (MGRS, WGS84)"` — and the pipeline threw
it away. **Two stacked bugs:**
1. the extractor labelled the string's `surface_format` as `"toponym"` (a place *name*), so the MGRS branch was
   never selected; and
2. the MGRS regex was anchored (`^…$`), so even a *correctly* labelled grid embedded in prose would have failed
   to parse.

Fix: format detection is now **shape-first and verified by parsing** — the model's declared label is a hint, the
string's shape is authoritative (the same principle the edge re-lane already uses for endpoints vs verbs).

## What changed in the corpus (8 fields, 2 files — the complete list)

`claims/d17_rawalpindi_2021.json` → claim `d17-rawalpindi-2021-l4` → `payload.attrs.coordinates`:

| field | before | after |
|---|---|---|
| `surface_format` | `"toponym"` | `"MGRS"` |
| `wgs84_lat` | `null` | `33.61638816251397` |
| `wgs84_lon` | `null` | `73.09971192513768` |
| `precision_class` | `null` | `"pad"` |
| `geocode_candidates` | `[]` | `[{lat, lon, source: "coord-parse", confidence: 1.0}]` |
| `proposed_alias` | the grid string | `null` |

`claims/d07_sat_confirm_karachi.json` → claim `d07-sat-confirm-karachi-l6` → `payload.attrs.coordinates`:

| field | before | after |
|---|---|---|
| `surface_format` | `"DMS"` | `"DD"` |
| `precision_class` | `"city"` | `"pad"` |

`"24.9012 N, 67.2034 E"` is decimal degrees, not DMS. **The coordinates themselves are byte-identical** — only
the precision reading changes, from city-level to pad-level, which matches `pl_karachi_ad`'s own `pad` class.

## Guarantees

- **Derived only from text already in the corpus** — no geocoder ran, no network, no LLM, no invention. The
  re-normaliser deliberately runs with **no geocoder at all**, so the only thing that can produce a coordinate is
  parsing a string already in the file.
- **Additive-only:** an existing geocoded coordinate is never re-derived or dropped; a parse that *disagrees*
  with a frozen coordinate is reported, never applied.
- **Swept all 57 location objects** in the scenario; exactly these 2 changed. No genuine toponym was misread as
  a coordinate (six real corpus-style toponyms are pinned by test, as are six malformed grids that must be
  rejected rather than coerced).
- `answer_key.json`, `config/places.yaml` and every other claim file are **untouched**.
- Reproducible any time: `python -m chanakya.ingest renormalize --scenario hq9p_primary [--apply]`
  (dry-run by default). A guard test asserts the shipped corpus is already fully normalized, so it fails loudly
  if the canonicaliser ever drifts ahead of the frozen bundles again.

## Validation that this is right, not merely consistent

`43S CT 23715 21242` decodes to **33.61638816, 73.09971193** — **0.78 m** from `pl_nurkhan`'s seeded anchor
`[33.61639, 73.09972]`. The grid is a deliberate exact encoding of the real Nur Khan coordinate. Downstream,
`site_rawalpindi` now earns its gazetteer binding **by proximity from the document's own coordinate**, not only
by name — which is what lets the origin end of the Rawalpindi→Rahwali relocation actually plot on the map.

## One open item for you (deliberately not done)

Pre-existing geocoded candidates elsewhere in the corpus still carry `confidence: null` (e.g. d05's gazetteer
hits). Those numbers come from **config**, not from the corpus, so backfilling them would have gone beyond
"derive only from data already present". Consequence: a future keyed re-record will stamp them (gazetteer `0.9`,
Nominatim `0.4`, etc.) and diff against today's baseline. If you want *keyless ≡ live* fully closed, it's a
one-flag extension to the same pass — your call, and low priority (RESOLVE treats an unstated confidence as
UNKNOWN, not as low, so nothing is currently mis-gated).
