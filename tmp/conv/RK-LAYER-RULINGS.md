# RK-LAYER (S2) rulings — three gaps the data hand found, verified and closed

The independent data hand's fixture pass surfaced structural gaps that S2's spec assumed away. **Verified by
the orchestrator against the shipped config before ruling.** Two of them change the design; one corrects a
ruling of my own.

---

## L1 — `site_type` cannot key anything as a raw string. C1 inherits C7.

**Verified.** `site_type` is **unenumerated free text**: no `enum`, no allowed-values list anywhere in
`config/`. The 15 distinct values in the frozen claims conflate **four different concepts**:

| concept | example values |
|---|---|
| kind of place | `airfield`, `dispersal site`, `centre`, `air defence belt` |
| **how we learned about it** | `observed-imagery-site`, `stated_destination` |
| the equipment at it | `HQ-9/P site` |
| area class / operator | `candidate coverage area`, `Pakistan Army/PAF joint-use facility` |

**Why this breaks C1 in both directions — the finding that matters.** C1 says the relationship wall fires
within one `site_type` and a *differing* `site_type` is not a conflict.
- **Over-merge direction:** two basings at genuinely the same kind of site carrying different strings
  (`airfield` vs `…joint-use facility`) read as *different* ⇒ no conflict ⇒ **the wall does not fire** ⇒ the
  over-merge C1 exists to prevent is allowed.
- **Silent-failure direction:** the two ends of the flagship relocation carry **unrelated** strings
  (`observed-imagery-site` vs `stated_destination`). A supersede key built on the raw string gives them
  **different instance keys**, so they never co-locate ⇒ **the relocation silently stops firing** while the
  code still looks deterministic.

**Ruling: C1 is not wrong, it is incomplete — it inherits C7.** C7 already states the general rule:
*normalization is a prerequisite for walling on **any** slot, and an unnormalizable stated value yields the
third state — no wall **and** no fusion, plus a named gap.* `site_type` is such a slot. Therefore:
1. **S2 declares a closed `site_type` vocabulary** in config (the *kind of place* axis only — the other three
   concepts are different fields and must not be smuggled into it).
2. **The raw stated string is NEVER the key.** Keying happens on the normalized class.
3. **An unmappable stated value ⇒ the third state**: no de-confliction, no fusion, and a **named gap**. It must
   never silently de-conflict (the evasion direction is over-merge) and must never silently kill a supersede.
4. **Mapping the 15 existing values is DATA's job**, not S2's — S2 declares the vocabulary and the fail-safe;
   the data pass supplies the mapping. Until it lands, the third state is the correct, honest behaviour.

---

## L2 — the **presence** citizen has no node type. S2 must create one.

**Verified.** The 13 declared node types are `manufacturer, trading_org, component, variant,
contract_import_event, unit, basing_site, area_of_operations, interceptor_stockpile, techdata_authority,
source, indicator, known_gap`. And `observed-at` is `[variant, component] → basing_site` — **both subject
types are design-layer**. So A3's *"materialize a provisional presence"* has **nothing to materialize as**:
`unit` is the **formation** citizen, and a presence is deliberately a *weaker* assertion than a formation.

**Ruling: add a new instance-layer node type for the presence citizen.** Rejected alternatives, with reasons:
- **Reuse `unit` with a "citizen" discriminator attribute** — **rejected.** It fuses the two citizens into one
  type, which is exactly what D-13.13 separates and what **G15 exists to guard**. The gate would then be
  asserting a distinction the type system denies.
- **Make presence a `refines: unit` refinement** (the mechanism `area_of_operations` uses for `basing_site`) —
  **rejected.** A presence is **not a kind of unit**; it asserts *less* (equipment seen at a place), and
  refining `unit` would inherit the organizational semantics a presence must not carry. Refinement models
  *narrower*, not *weaker*.

**Note for the implementer — this does not change the edge declarations.** Per **A4/D-13.6** the endpoint
*layer* is static (ontology) while endpoint *identity* is resolved at rebuild and materialized into the view.
So `observed-at` keeps describing **what the source states** (equipment → site), and the presence is
materialized in the **derived** layer. Do not rewrite the edge domain to point at the new type.

---

## L3 — `layer` cannot classify 5 of 13 node types. Do not force it.

`source`, `indicator`, `known_gap` (and arguably `techdata_authority`, `area_of_operations`) are **neither**
design nor instance — they are system/meta kinds. A2 says "every node_type gains a `layer` tag", which as
written forces a false choice.

**Ruling:** give `layer` a third value (or an explicit exemption) for kinds that are neither. **Forcing a
meta type into `design` or `instance` would corrupt the straddle-split trigger**, which fires precisely on a
layer *mismatch* — a mis-tagged meta type would generate phantom splits. State the third value in config; do
not leave it implicit.

---

## L4 — recorded, already in scope or owned elsewhere

- **`trading_org` is named by NO edge type at all**, so a correctly-typed consignee can only be an orphan.
  This is **D12's shape and worse than D12 as filed** — S2 already owns adding the event↔trading_org edge; this
  is the reason it matters.
- **No carrier for a stated refutation** — all 492 frozen claims are `polarity: positive`, so refutation
  handling is testable only on fixtures. Record as a coverage gap; do not build new capability for it in S2.
- **No numeric equipment-count attribute** anywhere, though sourced figures exist on sighting events. This is
  A3's `count`-as-a-sourced-attribute requirement having no home. **S2 owns the ontology, so S2 declares it** —
  and its default is `unknown`, never "how many reports merged".
- **Doc drift:** `spine/13` names the formation type `fire_unit`; the ontology has `unit`. Fix the doc; the
  code is the fact (working-principles #6).
