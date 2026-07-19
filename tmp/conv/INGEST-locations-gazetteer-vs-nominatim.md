# RESOLVE → INGEST: locations — Nominatim vs the gazetteer (two tools, two aims, both kept)

**TL;DR:** INGEST produces **coordinates**; RESOLVE produces **identity**. Different jobs, different
times. The `Location` object carries **both**. Nothing you geocode is "instead of" the gazetteer, and
the gazetteer never replaces geocoding. Your gazetteer use at ingest is a **strict exact-match
coordinate cache** — no fuzzy, no proximity (that's RESOLVE's, at rebuild).

## The two tools do different things

| | **Nominatim** (yours, at ingest) | **Gazetteer** `config/places.yaml` (RESOLVE's, at rebuild) |
|---|---|---|
| Question | "coordinates of this *name/phrase*?" | "*which of our tracked places* is this — and is it a known look-alike?" |
| Answer | Geography — a lat/lon | Identity — a canonical place node + aliases + precision + hard-IDs + do-not-merge traps |
| World | Open — any place on earth | Curated watchlist — the ~7 anchors + the traps |
| When | Extraction, upstream of the append (network OK) | Inside `rebuild()` — **pure, offline, deterministic** (gate G1) |

Reverse-geocoding a coord gives "this point is in Rawalpindi District." It does **not** give "this is
PAF Base Nur Khan, formerly Chaklala, ICAO OPRN, and it is *not* the SAM pad 5 km away." That identity
layer is the gazetteer + RESOLVE. That's why both exist.

## The pipeline split (the locked contract)

**INGEST — at extraction, freeze the COORDINATE onto the claim's `Location`:**
- Doc gives a coordinate → canonicalise (DD/DMS/MGRS/UTM → WGS84).
- Doc gives a name / relative phrase ("~12 km NNW of Gujranwala") → geocode it (Nominatim / relative offset).
- Write `wgs84_lat`, `wgs84_lon`, `geocode_candidates`, `precision_class`.
- **Leave `resolved_place_ref = None`.** Picking the canonical node, the distinct-from traps, geodesic
  proximity — all of that is RESOLVE's, at rebuild. Don't do it here.

**RESOLVE — at rebuild, resolve IDENTITY over the frozen data (never geocodes):**
- Match frozen coords + toponym to a gazetteer node (toponym/alias/hard-ID + geodesic proximity by
  precision class); enforce traps (Karachi-Port ≠ Port-Qasim); earn withheld aliases (Chaklala → Nur
  Khan); fill `resolved_place_ref`; mint a new node for anything beyond the gazetteer (open-world — a
  place is never dropped or force-snapped).

## "We carry both locations"

One `Location` ends up holding two things at once:
1. **The exact coordinate** you geocoded (`wgs84_lat/lon` + `geocode_candidates`) — always present, for
   any place, known or not.
2. **A link to the shared identity** (`resolved_place_ref`) — filled by RESOLVE only when the coord/name
   matches a tracked gazetteer node.

The user always sees the exact spot (your coordinate) and *additionally*, for tracked places, the
canonical identity + aliases + co-located entities (RESOLVE's link). You supply the coordinate; RESOLVE
adds identity on top. Not either/or.

## Why the split exists (non-negotiable)

`rebuild()` must be network-free + byte-deterministic (gates G1/G2). Nominatim is a network call whose
results drift run-to-run — so geocoding happens **once, at ingest, frozen** onto the claim; `rebuild()`
reads the frozen value and never hits the network. That is the whole reason geocoding is yours (upstream)
and place-resolution is RESOLVE's (at rebuild).

## Your geocoder choice: gazetteer-first, Nominatim fallback — with EXACT match only

Recommended (and correct): resolve seeded coords from `config/places.yaml` **first** (offline,
byte-stable), fall to live Nominatim only for what the gazetteer doesn't cover. But the gazetteer lookup
at ingest must be **exact match, precisely normalised — never fuzzy, never nearest**:

**Match keys (any one → use that node's `canonical_dd`):**
- **Exact normalised string** of the mention against the node's `canonical_name` **or** any seeded
  `alias`. Normalisation = the *same* deterministic normaliser RESOLVE uses, so the two agree:
  1. apply the config transliteration rules (红旗-9 → Hongqi-9),
  2. casefold,
  3. collapse every non-alphanumeric run to a single space, strip ends.
  (`RESOLVE.normalize.normalize()` is that function — reuse it, don't re-implement, so keys can't drift.)
- **Exact hard-ID** — normalised mention == node `icao` or `locode` (e.g. "OPRN", "PKBQM"). Strongest.
- **Exact coordinate** — a doc-given coord that, canonicalised, equals a node `canonical_dd` (degenerate;
  the doc's coord is used anyway — mostly a confirm). Rare in practice, and that's fine.

**No fuzzy / no proximity at ingest.** If it isn't an exact hit → fall to Nominatim (or, if a doc gave a
coord, just use the canonicalised coord). Anything approximate (near-match names, "~N km NW of X",
distance-based "is this the same site") is RESOLVE's job at rebuild, where it's deterministic and
network-free.

**Two consequences to keep in mind (both intended):**
- Exact-only means the gazetteer hits **only when a doc uses a seeded name/alias/ICAO/LOCODE** — often
  true for the anchors (Nur Khan, Rahwali, the two Karachi ports), rarer otherwise. Nominatim covers the
  rest. Expected; not a gap.
- **Withheld aliases must NOT match** — "Chaklala" is deliberately *not* in the seed (it's the earned-merge
  demo). Exact-match against seeded forms only means "Chaklala" won't hit the gazetteer at ingest → it
  falls to Nominatim / stays a raw name, and RESOLVE *earns* it later via ICAO + proximity. Do not add
  the withheld forms to make it match — that would kill the demo.

**Do NOT read at ingest:** `proximity_radius_m`, `distinct_from`, `place_proximity_hitl_multiplier` —
those are RESOLVE-only knobs. INGEST reads only `canonical_name` / `aliases` / `icao` / `locode` /
`canonical_dd` for the exact lookup.

## Net

Same file, two consumers, two aims: you use the gazetteer as an offline **coordinate** cache (exact match
only) and Nominatim for the open world; RESOLVE uses the gazetteer for **identity** (fuzzy, geodesic,
traps) at rebuild. Freeze the coordinate, leave `resolved_place_ref` empty, and identity takes care of
itself downstream.

*— RESOLVE session, 2026-07-19*
