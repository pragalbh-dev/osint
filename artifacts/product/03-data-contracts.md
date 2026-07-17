# 03 · Data Contracts — what info each surface actually has

**For:** the design collaborator. **Read after:** `01-entities-and-relationships.md` and
`02-trust-and-credibility.md`. **Purpose:** so you never have to guess what data a card, panel, or answer
has to work with. For each surface below, this is **the fields that exist to display** — think of it as
the palette of information you're arranging.

> **Two caveats, then it's all practical:**
> 1. These are distilled from the system's *proposed* detailed design. Exact field **names** may shift and
>    a few values are still being tuned (noted inline) — but the **inventory** (what information exists) is
>    stable enough to design against now.
> 2. You do **not** need to know how it's stored. One thing is worth knowing because it explains the whole
>    product: the picture is **rebuilt from two append-only logs** — a log of *claims* (evidence) and a log
>    of *decisions* (every system + analyst action). That's *why* everything traces to a source and *why*
>    an override propagates to later answers. You just design against the field lists below.

---

## A. A Claim (the evidence atom)

The thing a provenance drawer lists, and the thing every fact is ultimately built from.

| Field | What it holds | Design use |
|---|---|---|
| **source** | Who/what it came from — with the source's reliability grade, **side/bias**, and **tier** (official / analysis / named-social / anonymous). | Source chip + tier icon |
| **exact reference** | The precise **line / table row / image region** in the document. | "One click to truth" — the drawer jumps here |
| **assertion** | What it actually says (a subject–predicate–object, e.g. *unit → based-at → site*). | The claim's one-line text |
| **kind** | **observation** vs **inference** vs **retraction**. | ⚑ This is the **observed-vs-inferred badge** (brief §5.4). It's a real field, not something you infer. |
| **polarity** | positive, or **negative = an observed *absence*** ("looked, saw nothing there"). | Lets you show "confirmed *absence*", not just missing data |
| **three dates** | **event time** (when it was true in the world) · **report time** (when published) · **ingest time** (when we got it). | Freshness math uses event time; the gap between event & report time is a staleness/recycling tell |
| **extraction** | How it was pulled (a **parser** vs an **LLM/VLM**) + a model-confidence. | Optionally surface "machine-read, low confidence" |
| **integrity flags** | Any of: failed artifact-integrity · **recycled / first-seen mismatch** · coordinated-inauthenticity · too-clean · adversary-denial · **decoy-risk**. | The ⚠ treatments on a claim |

---

## B. A Node or Edge (a thing / connection on the graph or map)

What the **node inspector** and a map pin have to show. Status/confidence/freshness are **computed**, not
stored on the node — but they're always available for display.

| Field | What it holds |
|---|---|
| **id + type** | Its identity and its ontology type (from `01-entities-and-relationships.md`). |
| **status** | confirmed / probable / possible / contradicted / stale. |
| **confidence breakdown** | The "why" behind the status — see **C** below. |
| **freshness** | Three parts you can render: **last-support date**, the fact's **half-life** (how fast this *kind* ages), and the current **decay** → lets you draw "confirmed as of DATE / aging / stale." |
| **supporting claims, grouped by independence** | The claims behind it, **already clustered into independent groups** (the "5 sources → 2 looks" grouping). |
| **opposing claims** | Anything that contradicts it. |
| **latest sufficiency check** | Whether it currently meets its evidence requirement (feeds the Known-Gap state). |
| **per-type attributes** | e.g. a Component's **functional role**, a Basing site's **decoy-risk**, a quantity's **count-state range**, an origin's **foreign-control**. |

---

## C. The Provenance drawer / confidence breakdown

The most-used surface (brief §5.6). It answers "how do you know that?" The breakdown is **persisted and
replayable** — you can show every ingredient of the status:

- **the claim clusters** — supporting claims grouped into **independent origin-groups** (this is the
  centerpiece: render *"5 sources · 2 independent looks"*, not a flat list of 5);
- **per source:** its tier + reliability + which independence axis it shares/differs on;
- **integrity flags / penalties** on any claim (e.g. "this image was first seen in 2019");
- **freshness factor** — how much age has discounted it;
- **the resulting status** + any **contradicting** evidence;
- **an override action** → sends a status-override item to the review queue (see **D**).

> The hard part is hierarchy, not data availability: *everything above exists*. Your job (the OPEN → in
> brief §5.6) is showing "looks-like-5, is-really-2, with a too-clean warning on one" without a wall of
> numbers.

---

## D. The Review-queue item (the HITL card) — the one you asked about

**Every** queue item — merge, override, alert, and the later types — is the **same envelope with a
different payload.** So design **one reusable card** with these common slots, then specialize the middle:

**Common envelope (every card has these):**

| Slot | What it holds |
|---|---|
| **type** | merge · status-override · alert-disposition · (later: ontology-extension, assessment sign-off, integrity-flag). |
| **subject** | What it's about (a node / edge / merge / alert). |
| **context** | **The snapshot shown to the decider — "here's what I think and why."** This is where the machine's reasoning, the relevant evidence, and *why it's escalating* (its confidence, plus how *material* and how *novel* it is) live. |
| **options** | The exact choices offered (differs by type — below). |
| **effects** | **What will change if you decide X** — the downstream state changes. Lets you show a "this will update the graph / change the next answer" preview. |
| **actor + timestamps** | Who/when (system vs analyst vs agent). |

**The three built-deep payloads:**

**1 · Merge card** — "Are these two the same thing?"
- the **two candidate entities**, side by side, with their comparable attributes;
- the **match signals** with their relative weight: name/attribute similarity · **shared-neighbourhood**
  (do they connect to the same things?) · timeline consistency · whether a source outright says they're
  the same;
- a **score** and which **band** it's in (auto-merge / **needs-you** / keep-separate) — items only reach
  you when they land in the uncertain middle (this is *by design*: the FD-2000 ≠ FT-2000 trap is tuned to
  land here);
- **options: accept / reject / split.** The decision is remembered (grows the alias table) and is
  reversible.

**2 · Status-override card** — "Is this really confirmed?"
- the claim/node and its **current status**;
- the **confidence breakdown** behind it (the same data as **C**);
- **options: promote / demote / reject**;
- **effect:** propagates on rebuild — e.g. reject a claim → the node drops confirmed→probable → **a later
  answer changes.** (Great to visualize as the payoff of "human in control," brief §7 beat 6.)

**3 · Alert-disposition card** — "A tripwire fired — is it real?"
- the **fired tripwire** and **what changed** (the before → after state, e.g. *occupied @ site A →
  occupied @ site B*);
- **options: real / noise / needs-more** (the choice tunes the tripwire over time).

> **Priority / sorting** (the OPEN → in brief §5.5) is driven by three things the context carries:
> **confidence** (how unsure), **materiality** (does it touch a chokepoint?), and **novelty** (is this a
> never-seen entity/alias?). Those are your ranking/badge dimensions.

---

## E. The Ask / answer

What a cited multi-hop answer is made of (brief §5.4):

- the question **decomposed** into sub-questions;
- a **path of hops** — each hop is one edge traversed (manufacturer → component → import → unit → site);
- **per-hop citations** — every claim in the answer is a real claim ID, and a validator **rejects any
  sentence without one** ("no naked assertions" is enforced, not aspirational);
- **observed-vs-inferred tags** come straight from each claim's **kind** field — so grouping/​badging
  "Observed: …" vs "Inferred: …" is reading a field, not guessing;
- **the refusal payload** (when evidence is insufficient): a **what's-missing list** + a **next-coverage-due
  date**, and it surfaces the **Known Gap** object (see **G**).

Example questions the view must handle (the demo's target queries):
- *"Trace this deployed battery back to its component supplier and name the weak link."* (multi-hop trace)
- *"Is this node confirmed or probable — and on what evidence?"* (→ opens the breakdown, **C**)
- *"What do we NOT know here?"* (→ the refusal / Known-Gap state)

---

## F. The Alert / Observable (tripwire)

A tripwire **definition** (analyst-declared) carries:

- an **id** and the **subject/lens** it watches;
- a **trigger** — *what event* (e.g. an occupancy change), *on which edge type* (e.g. `based-at`),
  **matched on resolved entities, not name strings** (so a spelling variant doesn't fool it), within N
  hops of the subject;
- a **severity**;
- the allowed **dispositions** (real / noise / needs-more).

A **fired alert** carries what changed (the before→after) and routes to an alert-disposition card (**D-3**).
For the demo there's one tripwire wired end-to-end: **a unit relocating** (brief §7 beat 7).

---

## G. The Known Gap

A first-class "known unknown" object (brief §3):

- **what's missing** — the unmet evidence requirement;
- **observability ceiling** — **confirmable** (a coverage gap we could close) vs **probable-max** vs
  **never-observable** (a permanent boundary). This is the coverage-gap-vs-structurally-unobservable
  distinction the UI must render differently;
- **next-coverage-due** — when relevant data is next expected (only meaningful for the *confirmable* kind);
- doubles as a **collection task** ("what to go get").

---

## H. Config surfaces (Credibility settings, brief §5.8)

The tunable rulebook — what a settings screen exposes:

- the **credibility factor rubric**: four factors (**authority, editorial process, directness, track
  record**) and their weights;
- **integrity penalties** and **status thresholds**;
- **freshness half-lives** per kind of fact (durable → perishable);
- **evidence-requirement templates** per assertion type ("to confirm a basing, require …").

*Values here are analyst-owned and still being calibrated — for the demo, treat it as a mostly read-only
panel that proves the levers exist, maybe with one live slider (brief §5.8's lean).*

---

## What's explicitly still open (so you don't over-commit)

These are flagged "TBD" in the design and shouldn't be treated as locked pixels: the exact **estimative
wording** for confidence bands, the precise **freshness half-life values**, the merge **thresholds**, and
whether the queue **groups similar items** for bulk action. The *shapes* above are stable; these *numbers/
labels* may still move.
