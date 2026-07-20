# T6 — the provenance drawer said *how sure*, never *sure of what*

**Branch:** `qa/t6-drawer-semantics` (off `main` @ 8932793). **Not merged, not pushed.**
**Trigger (verbatim):** *"the right drawer as of now open doesnt make much sense to me about this node.
what exactly is confirmed, the replaced by edge is visible between 2 bases on the base, what is
replaced?"*

Both halves of that were right, and they turn out to be the same defect twice: **the UI was rendering
the system's internal keys and enums and calling it provenance.** A status is a verdict; a verdict needs
a proposition; the drawer never showed one. The `replaced by` arrow is the same omission applied to an
edge — the projection was drawn but the thing it is a projection *of* was dropped.

Reproduced live against the real corpus (backend on :8412, SPA `?mode=live`, both withheld docs
ingested). Screenshots are in `tmp/qa/`: `before-PAF_Base_Nur_Khan.png` (the reported state),
`after-PAF_Base_Nur_Khan.png`, `after-Rahwali.png`, `after-supersede-drawer.png`,
`after2-older-basing.png`. The `.png`s are gitignored (`.gitignore:41`); the `after*.txt` files beside
them are the drawer's rendered text at each step and **are** committed, so the after-state is
reviewable without the images.

---

## The headline answer on defect 6: was the base→base arrow a semantic bug?

**The user is right about the data, and the arrow is real — but the copy around it was false.**

* The supersession genuinely lives on the **`based-at` edge**. In the live view after ingesting d18/d19:
  `e:unit_hq9b:based-at:site_rawalpindi` goes **stale** with `superseded_by` pointing at
  `e:unit_hq9b:based-at:site_rahwali`. That is the fact: *the unit's basing moved.*
* The base→base edge is **deliberate**, not an accident. `credibility/supersession.py::_drawn_edge`
  mints `e:site_rahwali:supersedes:site_rawalpindi` on purpose (its docstring: "the way an analyst
  actually narrates a relocation … one node→node fact"), so the relocation is a thing you can see and
  click. It carries `attrs.subject = unit_hq9b`, `attrs.older_edge`, `attrs.newer_edge`.
* **So the bug was not the edge — it was that every consumer threw `attrs.subject` away.** The map
  labelled it `replaced by →` between two bases and captioned the old pin `superseded · 2021`. Read
  literally that says *PAF Base Nur Khan was replaced by Rahwali airfield*, which is false: Nur Khan is
  still there, its occupant left. Worse, opening that edge's drawer showed **"Insufficient evidence"**
  (a `supersedes` edge is status-less by design, and the UI defaulted `null → insufficient`) with **no
  claims at all** — the model only walked `clusters`, and a status-less edge has none, so its three
  citations were silently dropped.

Fixed at the presentation layer, where the loss was. Backend supersede logic is untouched.

---

## Defect by defect

### 1. It never said WHAT is confirmed/probable — **frontend (adapter + drawer)**

*Root cause, two places.* (a) The header printed the node's **name** under a "Proving" kicker — a name
is not a proposition. (b) Each claim row printed `[claim.kind, claim.asserts].join(' · ')`, i.e.
`observation · entity`, which is the claim's **filing category**; the payload that holds what it
actually says was never read.

*Fix.* `drawerSubject()` builds the assertion under assessment from the live view's own names and
types — node → `"PAF Base Nur Khan" exists, as a basing site`; edge → `X — based at → Y`. `
claimProposition()` reads each claim's payload into a sentence (`triple` → *subject is predicate
object*, resolving ids to names; `entity` → *"name" is a type*), and `claimAttrLines()` renders its
scalar attrs. Both are **strictly derivational**: every word comes from the payload or from a fixed
vocabulary map. A payload shape we cannot phrase yields `''` and the row shows the verbatim quote
instead of a guess — tested (`emits no proposition (rather than a guess)…`).

Also added a one-line gloss under the status word (*"Probable — supported, but thinner than confirmed"*)
so the verdict and the proposition can be read together without knowing the rubric.

### 2. Header count contradicted the body — **frontend (rendering, not arithmetic)**

*Root cause.* Both numbers were correct and neither was wrong: 2 distinct `source_id`s, 2 independence
clusters. The body rendered **one chip per claim** and labelled each with its **source id**, so four
chips read as four sources.

*Fix.* Chips are now labelled as claims (§3); the source is stated **once per cluster**; and the header
prints a third term, `N claims on file`, computed from the rows **actually rendered** — so the header
cannot drift from the body even when a cluster references a claim id the response did not carry.
`2 sources · 2 independent looks · 4 claims on file` over four rows now adds up on its face.

### 3. Three identical indistinguishable chips — **frontend (adapter)**

*Root cause.* `label={row.sourceId}` — three different claims from one document produce one string.

*Fix.* The chip is now `{kind} · {locator}` (`Observed · L22`), and where two claims share a line the
adapter falls through to the character span (`Observed · L22 · 1359–1486`). Under each chip the row
prints the claim's proposition and its attributes, so the three d17b rows read as three genuinely
different observations (site identity / TEL absence on 2025-06-11 / the 2024-11 radar-trailer
footprint) rather than three copies of a filename.

### 4. `observation · entity` is meaningless — **frontend (adapter)**

*Fix.* Translated: `Observed | Inferred | Retracted` × `about a thing | about a connection | about an
event`. Unknown tokens fall through to a humanised form of the raw token rather than vanishing, so a
new ontology type degrades to something readable.

### 5. Leaked internal scaffolding — **API + frontend**

*Root cause (the load-bearing half).* `d17b_withheld_gap` is a *filename*, and it was being shown as
the source. The class + reliability grade that make a source weighable live in `config/sources.yaml`,
which **no GET route exposed** (`/config/{section}` is POST-only). The SPA had nothing else to print.

*Fix (API — the one contract change).* `GET /evidence/{id}` gains `sources: {source_id →
SourceRegistryEntry}` for every cited source, returned verbatim. Logged in
`tmp/conv/API-to-FRONTEND-contract-log.md` (2026-07-20 entry) with the alternatives rejected.
The drawer now reads *Commercial satellite imagery / d17b_withheld_gap · reliability B · third party
interest · dated 2025-06-11*, and surfaces the registry's own gate flags (coordinated inauthenticity,
adversary denial) inline. **No publisher name is invented** — the registry does not carry one, and an
unregistered id renders as the bare id explicitly marked "not in the source registry".

*The `site_rawalpindi` subtitle* was already secondary (faint mono, under the headline). Kept — an id
is the handle you need to read a log or a citation — but it is now prefixed with the element's type
(`basing site · site_rawalpindi`), and the primary line is the proposition rather than the name.

### 6. The base→base "replaced by" edge — **frontend (map + adapter + drawer)**

See the headline section above for the verdict. Three fixes:

* **Map connector** — `replaced by →` became `{subject} moved →` (live: *"Pakistan Air Force moved →"*,
  see the data note below). With no subject on the edge it degrades to `basing moved →`, never to
  anything that names a *site* as the thing replaced. The connector is now **clickable** straight into
  the version link's drawer.
* **Map caption** — `superseded · 2021` became `former {subject} basing · 2021`. The subtraction is
  stated about the **occupancy**, which is what changed.
* **Drawer** — a status-less edge no longer renders as "Insufficient evidence"; it says so in words
  ("this link carries no status of its own — it records a change of state, not a fact about the
  world"), and the independent-looks term is dropped from the header rather than printed as `0`. A new
  **What changed** block names what moved, from where, to where, and states plainly that the site
  itself was not replaced — with one-click chips into the two `based-at` assertions the move is made
  of. The same block appears on those two edges too (role `older` / `newer`), so selecting the retired
  assertion explains its own staleness instead of just asserting it.
* **Ungrouped claims** — `evidenceToDrawerModel` now emits a residual bucket for claims no cluster
  contains, explicitly labelled *"Also cited · not counted as an independent look"*. This is what makes
  the version link's three citations visible at all; previously they were dropped on the floor.

---

## Deliberately left alone (with reasons)

* **The `supersedes` edge itself.** It is a documented, intentional projection with an oracle behind it
  (D-P4.11). Deleting it would break the graph story and the answer key; the honest fix was to render
  what it already carries.
* **"To raise this" still shows on the retired `based-at` edge** (*"next coverage due 2026-07-26"* on a
  site the unit has left). That is the backend's own `sufficiency` verdict. Suppressing a computed
  field in the UI would hide the machine's reasoning, and changing how sufficiency treats a superseded
  assertion is SCORE's lane, not a QA copy fix. Flagged here rather than silently patched.
* **The status gloss for `stale`** reads "aged past its shelf life" even when the cause is supersession
  rather than age. The **What changed** block directly beneath it gives the real reason, so the pair
  reads correctly; splitting `stale` into two display variants would need a backend signal for *why*
  it went stale, which does not exist yet.
* **Demo mode's frozen `Drawer.tsx`** — untouched by design. The graded demo must stay byte-identical.
* **Map label collision.** With Nur Khan and Rahwali ~40 km apart the connector label sits close to the
  pin captions at the default AOI zoom. Cosmetic, and the map pans/zooms; not worth a layout rework.

---

## Verification

* `make test` → **788 passed, 6 skipped, 1 xfailed** (2 new API tests for `sources`).
* `make lint` / `make typecheck` → clean.
* `frontend: npm test` → **108 passed** (16 new/rewritten adapter tests covering the proposition
  builder, chip disambiguation, the ungrouped bucket, source cards, status-less subjects and the
  supersession narrative from all three of its elements). `npx tsc --noEmit` → clean.
* Live browser walk, 0 console errors: map → Nur Khan pin → Rahwali pin → the `moved →` connector →
  "the earlier basing (now history)". Transcripts in `tmp/qa/*.txt`.
