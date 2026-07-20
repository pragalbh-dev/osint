# T2 — "Karachi appears as a node in Gujrat on the map"

**Branch:** `qa/t2-karachi-coords` (worktree `wt-T2`, off `origin/main` @ `8932793`)
**Status:** root-caused; the structural rail that was missing is now in place; `make check` green (798 passed).
**Headline:** the *literal* symptom is **not reproducible on `main`** — every pin the app draws today sits
exactly where its evidence puts it. What is real is the mechanism one step upstream: **entity resolution has
no geographic compatibility gate at all**, so it proposes `same-as` merges between sites ~1,100 km apart, and
a merged node silently inherits whichever coordinate its first claim carried. That is the teleport, and it is
one analyst click — or one toponym-geocoding fix — away from being visible.

---

## 1. Reproduction — what the app actually draws

Everything below was measured on `qa/t2-karachi-coords` (= `origin/main`), keyless, offline.

**Data.** Cold boot: 171 nodes / 105 edges / 457 claims. After the live ingest of the withheld
`d18_rahwali_pass1` + `d19_rahwali_confirm` (both through the real `POST /ingest` lane, and separately via a
full-corpus rebuild with `CHANAKYA_SEED_WITHHOLD=""`): 180 / 114. Exactly **three** nodes carry a plottable
coordinate, in both paths:

| node | name shown on the pin | lat, lon | place ref | correct? |
|---|---|---|---|---|
| `ent:basing_site:Probable Long-Range SAM Emplacement, Malir District, Karachi, …` | Probable Long-Range SAM Emplacement | 24.9012, 67.2034 | `pl_karachi_ad` | ✅ Malir, Karachi |
| `site_rahwali` | Rahwali airfield | 32.2389, 74.1311 | `pl_rahwali` | ✅ Rahwali, Gujranwala |
| `site_rawalpindi` | PAF Base Nur Khan | 33.6164, 73.0997 | `pl_nurkhan` | ✅ Rawalpindi |

**Rendering.** I drove the running app headlessly (Chromium) and, rather than eyeballing the screenshot,
derived the geographic position of each marker **from the vendored tile grid itself** — read every
`img.leaflet-tile`'s `z/x/y` and screen rect, rebuilt the Web-Mercator transform from them, and inverted each
marker's pixel centre through it. That compares the pin against the *drawn geography*, not against the
number we already believe.

* **Demo mode** (5 frozen pins): Karachi pin resolves to `24.847 N, 67.017 E`; the projection says Karachi
  (24.86, 67.01) lands at exactly that pixel. Rahwali → `32.287 N, 74.136 E`; Sargodha → `32.064 N, 72.861 E`;
  Rawalpindi → `33.615 N, 73.081 E`. All correct to ~1–2 px.
* **Live mode** (3 pins): Karachi emplacement → `24.886 N, 67.192 E`; Rahwali airfield → `32.250 N, 74.136 E`;
  Nur Khan → `33.615 N, 73.081 E` (greyed, with the "replaced by →" connector). All correct.

**Also checked and cleared:** the basemap tiles are not mis-vendored or offset (the inversion above proves the
grid and the projection agree); `MapView.tsx` plots `L.marker([pin.lat, pin.lon])` straight off
`node.location.wgs84_lat/lon` with no fallback position and no id-keyed coordinate table; no two pins share a
marker; no node's own claims disagree about where it is (scanned every node × every claim in the evidence log
— zero conflicts); and accepting a merge card through `POST /hitl/merge` does not move any pin today.

**So:** the wrong-position symptom is not in the shipped data, not in the API payload, and not in the renderer.
The user was almost certainly reacting to the *system asserting* Karachi ≡ a Punjab site — see §2 — which is
the same fault before it reaches the map.

## 2. Root cause — the missing rail

`resolve/scoring.py::merge_score` weighs exactly four signals: **name/attribute**, **shared neighbourhood**,
**temporal consistency**, **source-asserted identity**. Not one of them knows *where anything is*. The
geographic gates that do exist (`config/resolution.yaml` → `place_allowed_precision_classes`,
`place_min_geocode_confidence`, the `distinct_from` traps) guard only the **place** path — which gazetteer node
a mention snaps to. The **entity** path had no geographic check whatsoever.

On the frozen corpus that produces 18 `same-as` proposals among seven `basing_site` nodes, all raise-only
(`status=None`, routed to HITL), including:

```
Army Air Defence Centre, Karachi  ↔  central Punjab air defence sector          0.780
Army Air Defence Centre, Karachi  ↔  fenced compound near a PAF airbase …       0.719
Army Air Defence Centre, Karachi  ↔  Sindh                                      0.676
Army Air Defence Centre, Karachi  ↔  Sargodha                                   0.634
Karachi air defence sector        ↔  central Punjab air defence sector          0.796
```

The stored breakdowns show what drives them:

```
attribute 0.83 · relational 1.00 · temporal 1.00 · source_asserted 0.00  → 0.780
```

Two compounding faults:

1. **`relational` saturates at a perfect 1.0.** Every one of these sites has a *single* neighbour — one
   `based-at` edge from the same unit — so the Jaccard overlap of their neighbourhoods is 1.0 for every pair.
   A unit's sites are by construction *different* sites, so "we hang off the same unit" is being read as
   near-proof of identity. Without that 1.0 none of these pairs would clear `hitl_low` (0.45): attribute alone,
   at weight 0.40, tops out at 0.34. **This is the over-proposal fault and I have deliberately left it alone —
   it is T3's fragmentation/review-card scope.** Flagging it here because it is the same 18 edges.
2. **No geographic veto.** Karachi ↔ Sargodha is ~1,100 km. Nothing in the resolver can say so.

**How that becomes the reported picture.** `view/pipeline.py::_assemble` gives a merged node the location of
whichever of its claims came **first** (`if node.location is None: node.location = _node_location(...)`), and
its name likewise. Fuse a Karachi-named site with a Punjab-located one and you get a node **named Karachi,
drawn in Gujranwala** — precisely the report. Today those particular nodes carry no coordinates, so the pin
does not move; the moment either (a) an analyst accepts one of the 41 review cards, or (b) the parallel
toponym-geocoding work gives "Karachi" and "Sargodha" real coordinates, the teleport becomes visible. A map
that lies about *where* something is is worse than one that omits it: a missing pin says "we don't know", a
wrong pin says "we know, and here it is".

## 3. The fix

A **geographic compatibility veto on entity `same-as`**, config-driven, at the resolver layer.

* `config/resolution.yaml` → new `entity_geo_conflict_max_km` (`default: 100`, `basing_site: 25`), documented
  next to the existing RES-5 place gates it complements. 25 km for a basing site is far beyond any plausible
  disagreement between two reports of one site (the gazetteer's coarsest snap radius is 15 km, for a whole
  city) and far below the scale at which two different sites get confused. **Unset ⇒ the gate is off** — the
  same convention every other gate here uses, and no numeric literal lands in code (gate G6).
* `resolve/scoring.py::geo_conflict_km(a, b, cfg)` — returns the geodesic separation **when it is a conflict**,
  else `None`. Deliberately narrow: it reads only coordinates INGEST already froze onto the claims; it does not
  geocode, does not consult the gazetteer, and treats a side with **no** coordinate as *unknown*, never as
  "somewhere else" (absence is not disagreement — the same rule `has_hard_conflict` follows).
* `resolve/cluster.py::resolve_entities` — folded into `vetoed(a, b)`, so it blocks the high-precision
  bootstrap, the auto-merge fixpoint **and** the candidate queue. A geographic impossibility is not a question
  worth an analyst's attention, so it does not generate a card. Unlike a curated `distinct_from` it is **not**
  drawn as an edge: a geodesic separation is arithmetic, not a finding, and both places are already on the
  graph at their own coordinates.
* `resolve/scoring.py::has_hard_conflict` also reads it, so an *authoritative in-document coreference* cannot
  bootstrap the very merge the cluster-level veto exists to refuse.
* `resolve/geo.py` (new) — `LOCATION_ATTRS` / `location_attr` / `parse_coords` moved here from
  `resolve/places.py` (which imports `cluster`, which imports `scoring`: the scorer could not reach them
  without an import cycle), plus `entity_coords` / `separation_km`. `places.py` re-exports them, so every
  existing reader is unchanged and "where the coordinate lives" is still stated exactly once.

**Blast radius on the real corpus: none.** Rebuild before and after is byte-identical in shape — 171/105/40
`same-as` cold, 180/114/41 full — because no *currently proposed* pair has a coordinate on both sides. The rail
lands **before** the geocoding work that would make it bite, which is the point.

## 4. Regression tests

`backend/tests/resolve/test_geo_conflict.py` (7 tests) — the unit-level rail. The key one,
`test_karachi_and_punjab_sites_are_never_merged_or_queued`, builds the exact corpus shape (two similarly-worded
basing sites, one shared unit neighbour, real `pl_karachi_ad` and `pl_rahwali` coordinates) and asserts no
merge and no card. **Verified it fails on the pre-fix code** (`part.candidates` contains the pair) and passes
after. Siblings pin: the pre-fix behaviour with the gate unset; that ~600 m jitter still merges; that a
toponym-only mention is never vetoed by distance (this is what keeps the veto out of the geocoding lane); that
the per-type row and the `default` fallback both work; and that `has_hard_conflict` sees it.

`backend/tests/acceptance/test_map_position_integrity.py` (3 tests) — the standing tripwire over the real
frozen corpus, deliberately end-of-pipeline and mechanism-agnostic:

1. every node's own claims agree on one place, within the configured tolerance (read from config, so the test
   cannot drift from the gate);
2. every plotted node sits on a coordinate one of **its own claims actually states** — not merely a plausible
   one;
3. both hold after the staged live ingest that releases the Rahwali passes.

## 5. What else the same fault could affect

* **Any merged node's `name`/`attrs`, not just its location** — `_assemble`'s "first claim wins" applies to all
  of them, so a bad merge also mislabels. The veto removes the bad merge; the first-wins policy itself is
  untouched and remains a latent sharp edge worth a look if merges ever get more aggressive.
* **`observe/dsl.py`'s `near()`** reads `location.wgs84_lat/lon`, so a teleported node would have silently
  fired (or suppressed) a geofenced tripwire — an alerting failure, not just a cosmetic one.
* **`agent/tools.py`** hands the node's `location` to the ASK agent, so a wrong coordinate would have been
  cited in a sourced answer.
* **HITL merge accept** (`POST /hitl/merge` → `grow_alias`) now cannot force a geographically impossible merge
  either. That is intentional — the pair never surfaces as a card, and a geodesic impossibility is not an
  analyst judgement call — but it is a place where the system overrides a human, so it is called out here.

## 6. Overlap / hand-offs

* **T3 (fragmentation + the 41 review cards):** the `relational = 1.0` saturation in §2.1 is the shared root of
  those cards and is **untouched by me**. Fixing it (e.g. discounting a Jaccard computed over a one-element
  neighbourhood, or treating a shared *hub* neighbour as weak evidence) would drop most of the 18 Karachi
  meta-edges on its own. My veto is complementary: it is the rail that must hold even when the score is high.
* **The map-coverage / toponym-geocoding agent:** no overlap in code — the veto reads only already-frozen
  coordinates and never geocodes. But it is *load-bearing for their change*: the moment "Karachi", "Sargodha",
  "central Punjab" get real coordinates, those seven cross-country `same-as` pairs become one-click teleports.
  This gate should land **before or with** that work.
* **No corpus / answer-key change was needed**, so there is no data-agent note.

## 7. Decisions leaning on a guiding principle (for `DECISIONS.md`)

| Decision | Principle | Alternative rejected |
|---|---|---|
| Fix at the resolver, not at the renderer or the view assembler | "not a display-time patch over a data bug"; fix the deepest correct layer | Clamping/hiding suspicious pins in `MapView` (hides a real data fault) |
| Tolerances in `config/resolution.yaml`, per entity type, unset ⇒ off | config-driven & extensible, no magic numbers (G6) | A constant in `scoring.py` |
| A geographic conflict is a **silent** veto, not a drawn `distinct-from` | the repo's own rule that curated vetoes stay visible, mechanical rails do not (`has_hard_conflict` precedent) | Emitting 18 more `distinct-from` edges into an already-cluttered graph |
| A side with no coordinate is *unknown*, never "elsewhere" | "absence is not disagreement"; escalate, don't guess | Vetoing on toponym-string difference (heuristic, and steps into the geocoding lane) |
| Left the `relational` saturation alone and reported it | don't silently expand scope; avoid colliding with T3 | Fixing it here and forcing a merge conflict with T3 |
