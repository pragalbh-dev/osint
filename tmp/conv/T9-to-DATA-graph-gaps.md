# T9 → DATA-C / SCORE / RESOLVE — four graph gaps found while choosing the flagship query

Filed, not self-fixed (CLAUDE.md: corpus / `answer_key.json` / data-model issues go to the data agent).
Found by enumerating every substantive edge in the rebuilt view while picking a hero query that
terminates on a sourced answer. Context: `tmp/conv/T9-hero-query.md`. Nothing below was changed on
`qa/t9-hero-query` — the graph shape there is byte-identical to `qa/live-fixes` (166 / 84 / 19 / 457).

Ordered by how much each one would improve the demo.

---

## 1. `rebuild()` emits the SAME edge id several times, each row holding a DIFFERENT slice of the claims  ⚠⚠ root cause

Measured on the full rebuilt view (`tmp/qa` probe, reproducible):

```
92 edge rows · 83 distinct ids · 7 ids duplicated · 9 surplus rows · 0 duplicate node ids
```

Every duplicate group splits one assertion's evidence across rows, and **only one row is ever scored** —
the others come back with `status=None`, `confidence=None`, `sufficiency=None`. The worst case is the
corpus's best-corroborated order-of-battle fact:

```
e:var_hq9p:inducted-into:unit_paad   x4
  status=None          claims=['d02-ispr-induction-l11-7']          <- the ISPR OFFICIAL ANNOUNCEMENT
  status=None          claims=['d03-quwa-analysis-l6-3']            <- Quwa, third-party corroboration
  status=None          claims=['d04-armyrec-ranges-l7-2']           <- ArmyRecognition, third-party
  status=insufficient  claims=['d07-sat-confirm-karachi-l31-2',
                               'd23-cpmiec-false-attribution-l8-3'] <- the ONLY row assessed
```

So "HQ-9/P was inducted into Pakistan Army Air Defence" — which the corpus supports with an official
announcement plus two independent third-party looks plus imagery — is assessed off a two-claim row, **one
of which is the planted misinformation document**, and comes back `insufficient` with
`missing: official_announcement`. The official announcement is right there, on a sibling row nothing
scores. The other six duplicated ids behave the same way:

| edge id | rows | unassessed claim(s) stranded |
|---|---|---|
| `e:var_hq9p:inducted-into:unit_paad` | 4 | d02 (ISPR official), d03, d04 |
| `e:var_hq9be:inducted-into:unit_paad` | 2 | d18 |
| `e:var_hq9be:inducted-into:unit_hq9b` | 2 | d04 |
| `e:comp_ht233:equips:var_hq9p` | 2 | d15, d23 |
| `e:mfr_casic:manufactures:var_hq9be` | 2 | d04 |
| `e:comp_tel_chassis:equips:ent:variant:HQ-9` | 2 | d24 |
| `e:Pakistan:equips:var_hq9p` | 2 | d17b |

**This is very likely the root cause of the two symptoms below** (§2 "nothing is confirmed" and the
blanket `inducted-into` insufficiency): claims that should pool into independent-look groups are being
counted as separate assertions, so no assertion ever accumulates the ≥2 independent groups the
`confirmed` gate needs, and template slots are evaluated against a fraction of the available evidence.

**Second-order hazard, not yet biting:** `ToolContext.edges_by_id` is a dict comprehension over
`view.edges`, so it silently keeps the **last** row per id, while `out_edges`/`in_edges` keep all of them.
A path walked through row A can therefore render the status of row B. The current flagship chain is
unaffected (none of its three edges is duplicated) — but it is a live correctness hazard for any other
query, and it would be masked, not fixed, by de-duplicating at the ASK layer.

**Whose call:** the view rebuild / claim-pooling layer (SCORE + RESOLVE), not ASK. Deliberately not
touched on `qa/t9-hero-query`: fixing it changes the graph shape everywhere, which is exactly the kind of
change that needs its own branch, its own measurement and its own regression pass.

## 2. Nothing on the corpus reaches `confirmed`; every `inducted-into` edge is `insufficient`

The strongest status any node or edge carries is `probable`. All eight `inducted-into` edges fail the
same slot (`official_announcement`). C/02's flex #1 — *"the imagery-confirmed basing shows as
**confirmed**"* — therefore does not fire on the built graph, and "confirmed vs probable, on click"
currently reads as "probable vs possible".

Please treat this as **downstream of §1** and re-measure after that is fixed, rather than tuning
thresholds or editing the induction template first. If it survives the fix it is a genuine calibration
question: an all-`probable` graph is a defensible and arguably more truthful outcome for open-source
material, but it is then a **deliberate call to make and disclose in the design note**, not something the
demo should discover live.

**Why it matters for the demo:** the flagship chain has to run its order-of-battle hop on `equips`
(1 claim, a spares tender) rather than `inducted-into` (4 claims, an official announcement), because
`equips` is `probable` and `inducted-into` is not. Fixing §1 would put the better hop in the flagship
answer *and* give the chain a real confirmed-vs-probable contrast inside itself instead of only in the
side flexes.

## 3. The customs / front-company subgraph is structurally disconnected

`ent:contract_import_event:KPQA-HC-2020-118834/118835/119011` connect only to
`SINO-GALAXY IMP/EXP CO. LTD` / `SINO-GALAXY IMPEX CO, LTD` (`exported-by`) and
`ORIENT ELECTRO TRADING (PVT) LTD` (`imported-by`). **No edge joins any of them to `comp_ht233`, to a
variant, or to anything else in the HQ-9 graph.**

md/17 describes d05 as the front-company deception whose payoff is *"relational (not string) resolution
shell → HT-233"*. That relation does not exist in the built graph, so the corpus's most interesting piece
of tradecraft is unreachable from any trace and can only be served as an isolated lookup. This was the
strongest rejected hero candidate (T9 §2 E) and it is the single edge that would unlock it.

**Ask:** should d05's "radar apparatus parts (HS 8526)" line produce a claim tying the shipment to the
HT-233 / to the HQ-9/P programme — and if the *point* is that no source states it outright, should that
be modelled as an explicit inference claim (with premises) rather than as nothing at all?

## 4. Two ontology-expressiveness gaps (design questions, not corpus bugs)

- **No lane for a *candidate* supplier.** d22 (CASI, grade B — the authoritative deep-tier source) says
  the HT-233's maker is **unknown** and names `CASIC's 23rd Research Institute / BIRM` as the *candidate*.
  `mfr_23rd_ri` exists in the graph but carries only a `based-at` edge, because there is no way to say
  "named as a candidate, not asserted". The current handling — no edge at all — is honest but it throws
  away a sourced analytic lead that an analyst would want to see and task collection against. A
  three-state supplier lane (mirroring `substitutable-by`) or a `candidate-supplier` edge would let the
  answer say *"the maker is a Known Gap; the one candidate in open source is the 23rd RI [d22]"* instead
  of just *"Known Gap"*.

- **`design-authority-for` produces no edges.** d21 (`techdata_authority`) is the "invisible dependency"
  chokepoint in `C/00-overview.md`, and the edge type is declared in `config/ontology.yaml`, but the
  view contains zero instances and there is no `techdata_authority`-typed node. Either the extraction is
  not laning it or the document does not name the authority concretely enough to mint one. Worth a look —
  it is a named deliverable of the C layer.

---

**Also noted (already known, repeated only so it is not lost):** `comp_tel_chassis` still renders with
`type: known_gap` and the name `transporter-erector-launchers (TELs)` — T3b §5's documented exact-name
bootstrap artefact, needing a cross-type bootstrap rail. It is why the TEL→Taian chain was not a viable
hero candidate.
