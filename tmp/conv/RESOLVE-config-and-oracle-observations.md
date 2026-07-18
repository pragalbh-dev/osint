# RESOLVE → DATA-C: config + oracle observations (action items)

Surfaced while onboarding the RESOLVE session (iterative relational entity resolution). Per CLAUDE.md,
RESOLVE does **not** edit the frozen corpus / `answer_key.json` / DATA-C-owned config content
unilaterally — these are logged here for the data agent to adjudicate. Each item notes the decision
already taken (where the user ruled) vs. the open choice.

---

## 1. FT-2000 — remove from the `distinct_from` seed (user decision: score-it → HITL band)

**Decision (user, this session):** the FD-2000 / FT-2000 look-alike must land in the **HITL mid-band**
(0.55–0.85) as a *scoring* trap an analyst adjudicates — **not** be pre-vetoed. This is the marquee
"catch the look-alike, keep a human in the loop" demo (spine/03; spine/08 §3.9; RESOLVE.md AC #1).

- **Action:** in `config/resolution.yaml`, **remove `FT-2000` from `distinct_from["HQ-9/P"]`** (keep
  `HQ-9BE` — that stays the flagship seeded distinct-from). Today the config seeds FT-2000 as a hard
  veto, which short-circuits the scoring judgement and directly contradicts AC #1.
- The resolver will then land FT-2000 in the HITL band on its own via **high attribute similarity +
  conflicting relational/attribute evidence** (different family / anti-radiation role / range), and the
  analyst marks it distinct → replay-derived `distinct-from` from that point on.

**Open (needs data-agent confirmation):** does the corpus actually **instantiate an FT-2000 node**?
`md/05 §4 (D2)` flags FT-2000 may appear in *zero* scenario docs. If it is never a node, neither the
old veto nor the new HITL-band trap fires at runtime — the trap would be answer-key-only.
- Option A: seed one light FT-2000 mention in a doc (e.g. a marketing/analysis line that name-drops
  FT-2000 near HQ-9) so the pair instantiates and the trap is demonstrable live.
- Option B: accept the trap is oracle-only and note it in the design-note as a represented-not-live case.
  *(Recommend A — it's the graded reasoning; a live HITL-band trap is worth one seeded line.)*

## 2. Place gazetteer / oracle drifts (from the gazetteer design review)

- **(a) "bare Karachi → metro" has no target node.** `md/13 §? ` + the `location_normalization` flex +
  `answer_key.json` d02 (`precision: city`, "resolves to the metro") all require a **Karachi
  metro/city node**, but the gazetteer has only `pl_karachi_ad` (pad) + the two terminals. Either add a
  `pl_karachi_metro` (`precision_class: city`) node, **or** restate the flex outcome as
  "→ HITL / insufficient (no terminal/pad-level identity without the coord from d07)".
  *(Recommend adding the city node — makes "resolves to the metro" real + exercises the city radius.)*
- **(b) Oracle contradicts the seed on "Karachi" as an alias.** `answer_key.json`
  `ground_truth.places[pl_karachi_ad].aliases` includes `"Karachi"`, but `config/places.yaml:50`
  deliberately **excludes** it ("bare Karachi is NOT an alias → ambiguous parent-city") and the flex
  says bare Karachi must go to metro/HITL, not the pad. **Action:** drop `"Karachi"` from
  `pl_karachi_ad.aliases` in the answer_key (or move it to the new metro node) — otherwise an
  alias-match grader would score the wrong (snap-to-pad) behaviour as correct.
- **(c) `pl_casic_2nd` and `pl_birm` share the identical coord** `[39.860, 116.283]`. Pure
  coordinate-proximity would **false-merge** two distinct organisations (the inverse of the ports
  trap). RESOLVE will guard via attribute/name mismatch, but please add an explicit **mutual
  `distinct_from`** between them in `config/places.yaml` (cleaner + gives the district-precision trap a
  test), or give them distinct district-level coords.
- **(d) HQ-9BE range figure unreconciled** across docs: `C/01` ~250–300 km, `answer_key` 260,
  `md/05` 260–280 (md/05 F8 already flags this). Does **not** change the distinct-from outcome (the
  veto binds regardless), but pick one value for consistency in the attribute-similarity display.

## 3. Config additions RESOLVE needs authored (DATA-C owns the values)

RESOLVE reads all knobs through the config store (G6, no code constants). These new knobs are
`extra="allow"` on `ResolutionConfig`, so no F0-schema change is needed — just author the content in
`config/resolution.yaml`. Proposed shapes + seed values (tune as you see fit):

- **`attribute_rules`** — per node-type identity vs. hard-conflict attributes + numeric tolerances, so
  the `attribute` term of `merge_score` is type-aware (identity attrs raise similarity; conflict attrs
  lower it → catches look-alikes). Proposed seed:
  ```yaml
  attribute_rules:
    variant:      {identity: [export_designator, base_designator, aliases, family],
                   conflict: [operator_branch], numeric_conflict: {range_km: {rel_tol: 0.15}}}
    component:    {identity: [model_designation, aliases], conflict: [functional_role, radar_band]}
    manufacturer: {identity: [aliases, place_ref], conflict: [role, tier]}
    unit:         {identity: [designator, home_garrison], conflict: [service_branch, parent_unit]}
  ```
- **`hard_id_fields`** — the unique vs. categorical identifiers per type (drives hard-ID blocking +
  bootstrap-merge; user asked for this). Proposed seed:
  ```yaml
  hard_id_fields:
    unique:      {basing_site: [icao], seaport: [locode], place: [icao, locode]}   # shared ⇒ bootstrap-merge
    categorical: {component: [hs_code, radar_band]}                                 # shared ⇒ compare-only (blocking)
  ```
- **Dedup the proximity radii.** Now that `PlacesConfig` loads `config/places.yaml`'s
  `proximity_radius_m` into the live store, the duplicate **`place_proximity_radius_m` in
  `config/resolution.yaml` is redundant** — RESOLVE will read radii from `places.yaml`. Please remove
  `place_proximity_radius_m` from `resolution.yaml` (keep `place_proximity_hitl_multiplier`, or move it
  into `places.yaml`) so there is a single source of truth.

---

*Written by the RESOLVE session. Items 1–2 affect RESOLVE acceptance criteria + the demo; item 3 is
config content RESOLVE consumes. Ping the RESOLVE session on resolution so tests bind to final names.*
