# T5 — "the whole map looks so empty": why three pins, and what now draws

Branch `qa/t5-map-coverage`. Screenshots: `tmp/qa/t5/map-before.png`, `tmp/qa/t5/map-after.png`,
`tmp/qa/t5/map-after-live-ingest.png` (all captured headless against the real backend, live mode).

**Result: 2 plotted nodes → 12 cold, 15 after the staged live ingest.** One node stays deliberately
unplotted and is now visible as such. Review queue 40 → 34 (six geographically impossible merge cards
vetoed away — see §6).

---

## 1. Why there were three pins

The cold-boot view holds 171 nodes. Twelve carried a `location` object; **two** carried a coordinate.
The other ten were toponyms — `Islamabad`, `Punjab`, `Sindh`, `Kahuta area`, `central Punjab`,
`Haidian District, in western Beijing`, `Army Air Defence Centre, Karachi`, and a relative-bearing form
(`~12 km NNW of Kala Chitta / Attock Cantt area`) — with `wgs84_lat = None` and no geocode candidates.

Three separate things had to line up for that to happen, and all three were doing what they were told:

1. **INGEST's gazetteer geocoder is exact-match only, and only runs at extract time.** The keyless boot
   path injects no geocoder at all, by design (gate G1: no network in the claim path). So a toponym
   arrives at the view with no coordinate and no way to get one.
2. **The gazetteer had seven entries, all point-scale** — two airbases, two seaports, a notional pad,
   two Beijing facilities. Nothing the corpus actually *says* about area-level locations (`Islamabad`,
   `central Punjab`, `Sindh`) had anywhere to land.
3. **RESOLVE's toponym slot could not see the location statement.** `_toponym_of` read the entity's
   *display name*, then INGEST's `proposed_alias` — both filtered by `toponym_descriptive_markers`
   (`,` `~` `/` ` km `). But these entities are named after *things*, not places ("a fenced compound
   near a PAF airbase"), and the actual place statement lives on the frozen `Location`, where every
   candidate string was thrown out for containing a comma or a slash.

## 2. What changed

**Gazetteer (`config/places.yaml`) — eleven new anchors, all area-scale.** `pl_islamabad`,
`pl_kahuta`, `pl_karachi_metro`, `pl_lahore`, `pl_sargodha`, `pl_gujranwala`, `pl_attock`,
`pl_sialkot`, `pl_haidian`, `pl_punjab_pk`, `pl_sindh`. Provenance is stated per the file header:
`real` for the eight city/town centres (public coordinates), `approximate` for the two province
centroids and the Haidian district centroid. **No coordinate is synthetic and none is invented.**
Aliases are the surface forms the corpus actually uses — which is why an ugly string like
`"Kala Chitta / Attock Cantt area"` is curated verbatim: that is the anchor INGEST froze off the
relative-bearing phrase, and curating it is how a human teaches the gazetteer a form it did not know.
Matching stays **exact-normalised only** — no fuzzy, no substring, no proximity — so the deliberately
withheld earned-merge traps ("Chaklala", Rahwali's relative form) remain unearnable by string lookup.

**`pl_karachi_metro` is the parent-city catch-all md/13 §2 asks for.** A bare "Karachi" now resolves to
the metro at city precision, and is `distinct_from` both terminals *and* the Malir pad — so the
geographic FT-2000 trap holds from the ambiguous side too.

**A `province` rung on the precision ladder** (`schemas/values.py`, both radius tables). Sources really
do say "Sindh province, Pakistan"; the alternatives were to call it a `city` (drawing a ~150 km
uncertainty as a 15 km one) or to drop it. Radii: pad 500 m · site 1.5 km · terminal 3 km · district
5 km · city 15 km · province 150 km, all in config.

**RESOLVE reads the location statement (`resolve/places.py`).** `_toponym_of` now tries every string
the entity offers — explicit toponym, display name, `proposed_alias`, and `Location.raw` — and a
candidate that **exactly names a curated anchor** wins outright. The descriptive-marker filter is right
about display strings and wrong about a `Location.raw`, which is a location statement by construction;
an exact normalised match against a name an analyst curated by hand is not an inference from anything.
The legacy path is untouched for everything else, and `raw` earns a hearing *only* by naming a curated
anchor.

**The view adopts the anchor's coordinate, and says so (`view/pipeline.py`).** When a node resolves to
a curated anchor and holds no coordinate of its own, it takes the anchor's `canonical_dd` and
`precision_class`, and gets two new node attrs: `location_source` (`stated-coordinate` vs
`gazetteer-anchor`) and `location_uncertainty_radius_m` (from the config radii). **The frozen claim is
never touched** — the evidence layer still says only "central Punjab"; the knowledge layer says where we
drew it, how wide the doubt is, and which curated anchor it borrowed from. That is the bi-level bargain,
and it is why this is a cited derivation rather than a fabricated coordinate.

**A precision-reconciliation rule.** When a node has *both* its own coordinate and a clean anchor match,
it keeps the **finer** of the two classes. Both are evidence: a 5-digit grid reference is a pad and must
not be blurred to `site` just because it sits on an airbase; a 4-decimal pair the shape classifier read
as a degree-scale DMS must not stay `city` when the analyst has curated that spot as a pad.

## 3. The `precision_class='city'` on `pl_karachi_ad` — confirmed, and it was a parser bug

`"Malir District, Karachi, Sindh Province, Pakistan (24.9012 N, 67.2034 E)"` carries no sexagesimal
glyph, so the *anchored* decimal-degree pattern cannot see it and the shape classifier reads it —
correctly — as a degree-only DMS. Read literally that is a whole-degree fix, so `_dms_precision`
answered `city`. The source stated four decimals, i.e. ~10 m. The most precisely located node in the
corpus was being described as a 15 km blob.

Fixed in `ingest/adapters._dms_precision`: when both DMS components are plain decimal numbers (a
fraction, no minutes, no seconds), the stated decimal places decide — the same rule a bare DD pair gets.
A genuinely degree-only DMS (`33N 73E`) is still `city`. The frozen bundle was brought into line with
`python -m chanakya.ingest renormalize --scenario hq9p_primary --apply`, which is the sanctioned tool for
exactly this (`tests/ingest/test_renormalize.py` demands it, and was red until it was run): one field,
one bundle, `d07 … precision_class: 'city' → 'pad'`. No coordinate, no raw text, no answer-key change.

## 4. How precision is rendered

The map now draws two different **kinds** of thing, because we know two different kinds of thing:

| precision | drawn as |
|---|---|
| `pad` / `site` / `terminal` | the instrument pin — corner ticks, filled status core, reticle on select — plus a very faint envelope at the real radius |
| `district` / `city` / `province`, or an anchor-derived point with no class | **no pin.** A small dashed hollow ring at the centroid, and a dashed envelope circle at the true radius, filled at 6% |

The coordinate readout states both: `24.90°N 67.20°E  DMS  ±500 m` for a pad, `±150 km` for a province.
Legend gained a line: `pin = point fix · ring = located to an area only`.

**Co-located area pins are clustered, not fanned out.** Three entities all reported "in Punjab" resolve
to one centroid. Spreading them around it would invent three positions nobody stated; stacking them
would hide two of the three. They render as one marker reading **"3 entities · located to this area
only · ±150 km"** — which is exactly the state of the evidence. Point pins are never clustered: those
*are* distinguishable positions. (`clusterAreaPins` in `frontend/src/api/adapters.ts`, deterministic.)

Long live node names (`"Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area"`) are clamped
to 26 chars on the pin label with the full string on hover; the pin label is an index, not the record.

## 5. What remains legitimately unplottable

**One node, cold and after ingest:** `garrison in China's western military district` — stated as
"China's western military district". That is a theatre-level military region with no defensible
centroid; there is no honest point and no honest envelope, so it gets neither.

It is **not** silently dropped. A panel at the bottom-left of the map reads
`1 located, not plottable`, expands to name the entity and quote what the source said, and closes with
*"insufficient evidence to place"*. An analyst reading the map has to be able to see what the map is
not showing them, or the absence reads as "there is nothing there".

Also still off the AOI rather than unplottable: `Yongding Road` → `pl_haidian` (Beijing). It plots
correctly; the frame is Pakistan.

## 6. Overlap with T2 — read this part

T2's veto and this work are **complementary, and each is load-bearing for the other.**

**The number T2 asked for.** After geocoding, and *before* I added the non-identity rows below,
**6 of the 92 same-as/candidate pairs gained coordinates on both sides — and all six were >25 km
apart**, from 104 km to 974 km:

```
974 km  Army Air Defence Centre, Karachi  ~  Sargodha
894 km  Army Air Defence Centre, Karachi  ~  Punjab
796 km  Sargodha                          ~  Sindh
712 km  Punjab                            ~  Sindh
191 km  Army Air Defence Centre, Karachi  ~  Sindh
104 km  Punjab                            ~  Sargodha
```

These are exactly the pairs T2 predicted. Their branch note is right that "one toponym-geocoding fix"
arms them — but **T2's veto as written would not have caught these**, because it reads coordinates
frozen on the *claim* and these coordinates live on the *node*, derived at rebuild from the gazetteer.
That was a deliberate choice (§2: never write a lookup back onto the evidence layer), so the two
mechanisms genuinely do not meet.

**What I did about it, without touching T2's files.** `config/places.yaml` now declares the four
colliding area anchors (`pl_karachi_metro`, `pl_sargodha`, `pl_punjab_pk`, `pl_sindh`) mutually
`distinct_from`. That is a hard veto in machinery that already exists (`place_distinct_pairs`, applied
before banding), the statements are simply true (a province is not another province; a city is not the
province it sits in), and it is curated where an analyst can see and revise it. **All six pairs are gone
— zero two-sided-coordinate merge proposals remain**, and the review queue drops 40 → 34.

**Recommended follow-up when the branches reconcile** (I have not done it — it is T2's module): let
`resolve/geo.py`'s coordinate lookup fall back to the `canonical_dd` of the anchor a mention resolved to
when the entity carries no coordinate of its own. `place_matches` already runs before `resolve_entities`
and `place_of` is already threaded through, so the anchor is in hand. That makes the veto general
instead of enumerated, and the config rows above become belt-and-braces.

**Files we both touched — expect conflicts, all small:**

| file | mine | theirs |
|---|---|---|
| `backend/chanakya/resolve/places.py` | `_toponym_of`/`_toponym_candidates`; identity gate in `augment` | moved `location_attr`/`parse_coords` out to `geo.py`, changed the import block |
| `backend/chanakya/resolve/rconfig.py` | `place_identity_precision_classes` property | `geo_conflict_max_km` method |
| `backend/tests/resolve/_helpers.py` | one new `mk_config` kwarg | one new `mk_config` kwarg |
| `config/resolution.yaml` | `province` radius + `place_identity_precision_classes`, inserted right after `place_proximity_hitl_multiplier` | `entity_geo_conflict_max_km` block, inserted in the same spot |

None are semantic conflicts — both sides are additive and the two gates are orthogonal (mine bars *area
anchors* from constituting identity; theirs bars *distant coordinates* from merging).

**T2's standing tripwire, run against this branch.** `tests/acceptance/test_map_position_integrity.py`:
two of its three tests pass unchanged. The third,
`test_every_plotted_node_sits_on_a_coordinate_one_of_its_claims_states`, **goes red** — deliberately, and
it is a real finding about the test's invariant rather than about the code. It requires every drawn point
to equal a coordinate on one of the node's own claims, which forbids *any* gazetteer derivation, however
well cited. Proposed amendment (one clause):

> a plotted coordinate must be either (a) a point one of the node's own claims states, **or** (b) exactly
> the `canonical_dd` of the curated anchor named in `location.resolved_place_ref`, and only when
> `attrs['location_source'] == 'gazetteer-anchor'`.

That still closes the teleport — another entity's coordinate is neither (a) nor (b) — while permitting a
cited lookup. I have written that invariant as a standing test on this branch:
**`backend/tests/acceptance/test_plotted_point_provenance.py`** (3 tests, green cold and after the staged
live ingest). Reconciliation should merge the two files rather than pick one; they ask different
questions ("do this node's coordinates agree?" vs "where did the drawn point come from at all?").

## 7. Overlap with T3b — action needed on their side

T3b is retyping air-defence *sectors*, *belts* and *provinces* off `basing_site`. **Everything here
already refuses to give an area-of-operation a sharp pin** — `province`/`city`/`district` render as a
dashed envelope with a hollow centroid ring and never a pin or a reticle-worthy point, and
`place_identity_precision_classes: [pad, site, terminal]` bars them from ever constituting identity.

But one config key needs their attention: **`place_entity_types` is unset and therefore defaults to
`{basing_site}`**. The moment `Sindh`, `Punjab`, `central Punjab air defence sector` and
`Karachi coastal air defence belt` are retyped, they stop being place-type entities, place resolution
skips them, and they fall back off the map entirely. Whoever lands the retyping should add the new type
names to `place_entity_types` in `config/resolution.yaml` (the seam already exists — it is one line, no
code change). Flagging rather than guessing the type names.

## 8. Tests

* `backend/tests/resolve/test_places.py` (+5) — a stated location binds when the display name is a
  description; an uncurated area still binds to nothing; sharing a province never fuses two entities;
  two mentions of one *site* still do fuse; the identity gate absent ⇒ pre-T5 behaviour (G2).
* `backend/tests/view/test_location_precision.py` (new, 7) — anchor adoption; the derived point is
  labelled as derived; a coarser anchor never downgrades a grid reference; a finer anchor upgrades an
  understated surface form; an uncurated place is left unplotted rather than nudged; empty config ⇒ no
  stamping at all.
* `backend/tests/acceptance/test_plotted_point_provenance.py` (new, 3) — the §6 invariant, over the real
  corpus, cold and after the live ingest.
* `backend/tests/ingest/test_adapters.py` (+2) — the decimal-pair-in-prose precision fix, and the narrow
  exception (`33N 73E` is still `city`). Two pre-existing tests used "Gujranwala" as an example of a
  name the seed does *not* carry; it now does, so they were re-pointed at "Multan".
* `frontend/src/api/adapters.test.ts` (+11) — precision/radius/provenance on every pin; the coord
  readout states both point and doubt; point-vs-area separation; `clusterAreaPins` determinism;
  `unplacedLocations`.

`make check` green (805 passed, 6 skipped, 1 xfailed). Frontend `tsc --noEmit` and `vitest` green (104).
`make beat` still fires the relocation tripwire. Node/edge counts: 171/111 cold (was 171/105 — the six
new edges are the area non-identity vetoes, made visible rather than silent), 180/120 after ingest.

## 9. One contract note for the API↔frontend log

`frontend/src/api/types.ts` — `Location.raw` was typed `string | null`; the backend schema is
`str | list[str]`. Widened the mirror to match. No backend change; the TS type was simply narrower than
the contract.
