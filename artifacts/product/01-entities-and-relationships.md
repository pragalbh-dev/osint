# 01 · Entities & Relationships — the nouns on the graph & map

**For:** the design collaborator. **Read after:** `00-START-HERE.md`. **Pairs with:** `02-trust-and-credibility.md` (how much we believe each of these) and `03-data-contracts.md` (what fields each carries on screen).

This is the vocabulary the **Graph explorer** and the **Map** are made of. A designer needs it to know
what shapes/labels exist, what becomes a map pin, and what the node-inspector has to name. It's a clean
distillation — no military math, no storage detail. Names in `code font` are the literal labels that will
appear in the UI, so they matter for your legend and typography work.

> **Mental model in one line:** everything lives in *one* graph. A "subject" (the thing being
> investigated) is just a **saved lens** over that graph — a set of starting entities + a way of
> traversing them — **not** a separate database. Switching subjects re-focuses the same graph.

---

## Things (node types) — what a node can *be*

The full model has 14 node types. **The demo actually draws the ⭐ subset** — design for those first;
the rest exist so the design extends cleanly.

| Node type | Plain meaning | Appears as |
|---|---|---|
| ⭐ **Manufacturer / design bureau** | A company or plant that designs or builds the weapon or a part. | Graph node (origin end of the supply chain) |
| ⭐ **Component / subsystem** | A physical part: radar, launcher vehicle, missile, command post. Nests (radar → module → chip). Carries a **functional role** — an *engagement radar* is the crown-jewel part (it's what makes a site a live firing unit). | Graph node |
| ⭐ **Variant** | A specific model of the weapon (e.g. HQ-9/P vs HQ-9BE). Holds the confusable aliases — the **merge traps** live here. | Graph node |
| ⭐ **Contract / Import & Support event** | A purchase / delivery / spares deal linking a buyer to a supplier. | Graph node (the bridge from supply chain → the field) |
| ⭐ **Unit / Formation** | A military unit that owns equipment and sits somewhere. Nests (brigade → battalion → battery). | Graph node |
| ⭐ **Basing site** | A physical place a unit occupies (garrison, dispersal field, depot). Modeled **separately** from its occupant, so "unit X is *at* site Y" is a visible connection you can change. Carries a **decoy-risk** flag. | **Map pin** + graph node |
| ⭐ **Interceptor Stockpile / Tech-Data Authority** | The demo's one "sustainment" node — either the missile inventory ("can they reload?") or the software/keys holder (the invisible dependency the maker keeps even after the sale). | Graph node |
| **Maintenance / Depot Echelon** | Where the system is repaired/overhauled. *(full spec; not in demo)* | Graph node |
| **Training Establishment / Pipeline** | Where crews are trained. *(full spec; not in demo)* | Graph node |
| ⭐ **Source** | Where a piece of info came from — a news outlet, a satellite, a social account — with a reliability/bias rating. | Provenance drawer |
| ⭐ **Indicator (a.k.a. "claim")** | A *single* sourced observation — one satellite image, one announcement. The atom of evidence. The brief calls this a **claim**. | Provenance drawer |
| ⭐ **Known Gap / Collection Requirement** | A first-class **"thing we know we don't know."** Its own object, not a footnote — doubles as a to-do list of what to go collect. | Map/graph object + the Ask view's refusal state |
| **Confidence Resolver / Evidence-Requirement Template** | The *rulebook* that computes confirmed/probable/insufficient. Not drawn on the map — it's config behind the badges. | (Credibility settings screen) |

**Attributes that drive visuals.** A few node attributes exist specifically to change how something is
drawn — worth knowing when you design the inspector and the pin/node states:

- **functional role** (on a Component) — acquisition/early-warning vs battle-management vs
  **engagement/fire-control**. An engagement radar is the top chokepoint; it deserves emphasis.
- **decoy-risk flag** (on a Basing site) — a single satellite pass matching the signature *can't* alone
  confirm a live battery (it could be a decoy), so confidence is capped at *probable*. The UI should be
  able to show "confirmed-looking, but single-pass ⇒ held at probable."
- **count state** (on quantities) — numbers are *ranges with a state*: ordered vs delivered; fielded vs
  combat-ready. Not a single number.
- **foreign control** (on origin nodes) — does the maker's country still control this? Drives how severe a
  chokepoint is. Defaults to **UNKNOWN** (+ a Known Gap), never assumed.

---

## Connections (edge types) — how nodes link

Grouped by what they're about. Direction matters for arrowheads. Edges in the **hero-demo trace** are
marked 🎯.

**Supply chain — who makes / supplies what:**
`manufactures` · `design-authority-for` · 🎯 `supplies-component` · `variant-of` ·
`component-of` / `composed-of` (part-of-a-part, for deep-tier weak links) · `exported-by` ·
`analog-of` (this model is a cousin of that one — lets the system borrow a *probable*-capped inference).

**In the field — who has it, where:**
🎯 `imported-by` (this deal went to this unit) · 🎯 `inducted-into` (this model entered service with this
unit) · `subordinate-to` (org hierarchy) · 🎯 `based-at` (**unit is at this site** — the map's core link,
and the *perishable* "where is it *now*" edge that drives the relocation story) · `operates/fields` ·
`operational-status/readiness` (how active a unit looks).

**Sustainment — keeping it running:**
`reloaded-from` · `stocks-round` · `replenishes` (a follow-on order that tops up supply) ·
`resupplied-by` · `overhauled-at` · `trained-by` · `software-controlled-by` (the software/keys dependency).

**Is there a backup? — the chokepoint question:**
`substitutable-by` — three states: **known-sole-source** / **known-alternates** / **UNKNOWN**. UNKNOWN is
the default and is *not* proof of a single point of failure (a designer shouldn't render UNKNOWN as "weak
link confirmed").

**Same-thing-or-not — the merge review:**
`same-as` (a reversible, audited merge of two records that are the same thing) ·
`distinct-from` (an explicit "**do NOT merge these**" — carries the FD-2000 ≠ FT-2000 trap).

**Evidence & trust — the receipts layer:**
🎯 `evidenced-by` (this fact is backed by this observation) · `corroborates` (two *truly independent*
observations agree) · `contradicts` (two observations of the *same thing at the same time* conflict — a
red flag → human review) · `supersedes` (a newer observation replaces an older state — e.g. a unit *moved*
A→B; the old one goes **stale**, *not* contradicted — see brief §3) · `derived-from` (observation → its
source).

---

## How the entities map onto your screens

| Screen | What it's made of |
|---|---|
| **Map** | `Basing site` pins (+ the `based-at` unit), confidence-coded. |
| **Graph explorer** | The supply-chain / ORBAT nodes and edges above. |
| **Provenance drawer** | `Source` + `Indicator`/claim behind whatever you clicked, plus the `corroborates`/`contradicts` links between them. |
| **Review queue** | `same-as` / `distinct-from` decisions (merges), status overrides, alert dispositions. |
| **Ask view** | A path traced along 🎯 edges, each hop citing its `evidenced-by` claims. |
| **Known-Gap object** | The `Known Gap` node + the "insufficient evidence" answer state. |

> **The one confusable pair to internalise:** `contradicts` (two sources fight about the *same moment* →
> alarm → human resolves it) vs `supersedes` (the *world changed* → the old fact quietly goes stale with a
> "moved →" link → no alarm). They look identical ("two sources disagree") but mean opposite things.
> This is brief §3 and the climax of the demo (§7 beat 7).
