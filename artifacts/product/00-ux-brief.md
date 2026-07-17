# OSINT Analyst Workbench — UX / Product Brief

**For:** the product/design collaborator. **From:** Pragalbh.
**What I need from you:** the UI/UX — screen layouts, the visual language for "how much do we trust
this," interaction flows, and taste on the open questions marked **OPEN →** throughout.

**Division of labour:** you own the **information architecture, flows, and visual system**; a coding
agent (Claude) implements whatever you design on a real frontend stack. So your output can be rough —
**wireframes and a visual-language tile beat polished mocks.** Everything marked **OPEN →** is
genuinely undecided and yours to propose on; everything else is locked by the system design and
shouldn't be re-fought (the reasoning lives in the repo's design docs).

**Timing:** the demo is submitted **20 Jul, 12:00** — design input is most useful within ~a day.

You do **not** need any military or intelligence background to design this well — everything domain-y
is explained in plain terms below, and the example subject is just a stand-in. What actually makes
this product good is a *design* problem you'll recognise: **making uncertainty legible.** Read §3, it's
the soul of the thing.

Stack note: we're building a **real frontend** (React/Vite SPA), not a notebook/Streamlit throwaway —
so your design will get built more or less as drawn. Scope is a focused analyst *workbench*, not a
big-data dashboard: think ~15 entities on screen, not 15,000. Calm, dense, precise — closer to a
finance terminal or a code editor than a consumer app.

**📁 Context pack:** next to this brief are four short, clean, designer-facing docs —
**`01-entities-and-relationships.md`** (the nouns on the graph/map), **`02-trust-and-credibility.md`** (the
trust model, no formulas), **`03-data-contracts.md`** (what info each surface actually has to display), and
**`04-scenario-entities-and-corpus.md`** (the concrete entities + full document list the demo runs on) —
plus **`00-START-HERE.md`** (a domain primer + glossary) and the full source corpus in
`reference/corpus/`. This brief is self-contained, but wherever a section shows a **📎** line, that's a
pointer to the clean doc with the detail. Start with `00-START-HERE.md` if any term below is unfamiliar.

---

## 1. What this is, in one paragraph

An analyst types in a **subject** they want to understand ("this adversary's air-defence system"). The
system has already ingested a pile of **messy, conflicting open-source documents** — news articles,
official statements, shipping records, satellite images, social-media posts — and pulled them into one
**map of who/what/where and how it all connects**. The analyst's job is not to read all the documents;
it's to **judge what's trustworthy**, correct the machine when it's wrong, and get **cited answers to
hard questions** — every claim traceable back to the exact source line it came from. The product's
entire reason to exist is that last part: *never assert anything the evidence doesn't support, and
always show your work.*

---

## 2. Who uses it & what they're trying to do

**The user is an intelligence analyst.** One person, expert in the subject, drowning in sources, short
on time. They are skeptical by profession — they trust nothing they can't trace. Their pains:

- **Too many sources, too little time.** They can't read everything; they need the system to surface
  the few things worth their attention and let the rest sink.
- **Sources lie, contradict, and go stale.** A photo from 2019 gets reposted as "breaking news." Two
  "independent" reports turn out to be the same rumor. An official statement says "routine exercise"
  while social media shows something else. The analyst needs the system to *flag* these, not paper
  over them.
- **They are accountable.** Whatever they conclude, someone senior will ask "how do you know?" So every
  claim the system makes must click straight through to its source.

**The product's promise to them:** *I'll do the reading and the bookkeeping; you make the judgment
calls; and I'll never pretend to know something I don't.*

The key consequence for design: **the human is always in the loop and always in charge.** The system
proposes; the analyst disposes. This is not an autopilot that emits answers — it's a workbench that
does the grunt work and escalates the hard calls to a person. Several screens exist *only* to let the
analyst review, accept, reject, or override what the machine did.

---

## 3. The core idea that drives every screen (read this one)

> 📎 **Detail:** `02-trust-and-credibility.md` — the full trust model in plain language: the statuses,
> freshness, the 3-axis independence rule, integrity/"too-clean", supersede-vs-contradict, and the
> honest-refusal state. (No formulas.)

**Everything in this product carries a trust status, and that status must be visible everywhere, at a
glance, without clicking.** This is the whole design challenge in one sentence.

Every fact on the map, every connection in the graph, every line in an answer is one of these states:

| Status | Plain meaning | Analyst feeling |
|---|---|---|
| **Confirmed** | Multiple independent, credible sources agree, and the info is recent. | "I can brief this." |
| **Probable** | Some evidence, but thin — one source, or not quite enough to confirm. | "Lean on it, don't bet on it." |
| **Possible** | A weak lead. One low-credibility whisper. | "Noted. Keep an eye out." |
| **Contradicted** | Credible sources disagree *about the same moment in time*. | "Something's off — I need to look." |
| **Stale** | *Was* confirmed, but the info has aged past its shelf life with no fresh confirmation. | "This was true in 2016. Is it still?" |
| **Insufficient evidence** | We were asked something the evidence can't answer. | "Don't guess. Say what's missing." |

**One distinction the design must not blur: contradicted vs. superseded.** These *look* like the same
thing (two sources say different things) but mean opposite things to the analyst:
- **Contradicted** = two sources describe the *same time* and disagree → a genuine conflict → gets
  flagged and sent to the human to resolve. A red-flag treatment.
- **Superseded** = the *world changed* (e.g. a unit relocated from base A to base B). The newer fact
  is right; the old one isn't *wrong*, it's *history* → the old node quietly goes **stale** with a
  "replaced by →" link to the new one. This is a *timeline* relationship, not an alarm. It needs a
  visual that reads as "this moved / this is the previous state," clearly different from a conflict.
  (This is literally the demo's climactic moment — see §7 beat 7.)

Two more dimensions ride *on top of* status and also need visual expression:

- **Freshness** — how old the supporting evidence is. A "confirmed" fact slowly decays toward "stale"
  as it ages. Some facts age fast (where a unit is *right now*), some effectively never (who
  manufactures a part). The UI has to show "confirmed, but aging" distinctly from "confirmed and
  fresh."
- **Source tier** — where a claim came from, on a credibility ladder: official government statement >
  reputable analysis/trade press > a named social account > an anonymous post. A satellite image can
  *confirm*; a random tweet can only ever be a *lead*.

**A "Known Gap" is a first-class thing, not just an error message.** When the system doesn't know
something, that gap can appear as its own object *on the map and in the graph* — a visible "known
unknown" the analyst can see and act on (it doubles as a to-do list of what to go collect). Crucially,
gaps come in two flavours that must look different:
- **Coverage gap** — *we could learn this* with the right data ("no recent satellite pass; next one due
  Tuesday"). Feels like a pending task.
- **Structurally unobservable** — *no open source will ever show this* (e.g. how many missiles are in a
  bunker, secret contract terms). Feels like a permanent boundary, not a to-do. The UI must not make
  this look like something fresh imagery would fix — that would be dishonest.

**The design bar:** an analyst should be able to look at the map or the graph and instantly read the
epistemic temperature of the whole picture — what's solid, what's shaky, what's rotting, what's
disputed — the way a developer reads a diff or a trader reads a heatmap. If confirmed and probable look
even slightly similar, the product has failed its one job.

> **OPEN → the status visual system is the single most important design decision.** How do we encode
> five statuses (+ the superseded & Known-Gap treatments) × freshness × source-tier without it turning
> into a Christmas tree? Color alone won't
> survive colorblindness or a projector on a demo call. Likely need shape/fill/border/opacity working
> together (e.g. fill = status, border texture = freshness, an icon = source tier). This is where I
> most want your eye. A small, disciplined, accessible visual language here carries the entire product.

---

## 4. The mental model (how the machine thinks — simplified)

> 📎 **Detail:** `02-trust-and-credibility.md` §1 — the two layers (evidence vs knowledge), why the unit
> is a **claim**, and why a click always reaches the source.

You don't need the engineering, but this model explains *why* the screens are shaped the way they are:

1. **Evidence layer (the receipts).** Every document gets broken into individual **claims** — "Source
   X, dated Y, says Z." This is an append-only ledger; nothing is ever deleted. It's the audit trail.
2. **Knowledge layer (the picture).** The system fuses those claims into a single **graph** of entities
   (things) and relationships (connections). One graph node might be backed by five claims from five
   documents. **A node's trust status is computed from the claims under it** — more independent
   credible claims → confirmed; one source → probable; conflicting claims → contradicted.
3. **The human edits the picture, not the receipts.** When the analyst overrides something, that
   decision is recorded and the picture is recomputed. Because the picture is *derived* from receipts +
   decisions, clicking any node can always walk back down to the exact source line. **This is why
   "one-click to source" is a lookup, not a feature we bolt on** — and your provenance UI (§5.6) can
   assume it's always available for everything.

The practical UX upshot: **there is always a source behind everything, and always a way to see it.**
Nothing in this product is allowed to be a naked assertion.

---

## 5. The surfaces (screens & panels)

> 📎 The **nouns** on these screens — node types, edge types, map pins, claims — are catalogued in
> **`01-entities-and-relationships.md`**. Read it before designing the Map and Graph.

Here's the functional inventory. Think of these as the rooms of the app; how they're arranged
(tabs? split-panes? one workspace with panels?) is **OPEN → overall layout/navigation is yours to
design.** My instinct is a persistent left rail (subject, alerts, review queue badge) + a main stage
that switches between Map / Graph / Answer, + a right-hand **provenance drawer** that slides in over
any of them. But challenge that.

### 5.1 The Map — "where is everything?"

> 📎 `01-entities-and-relationships.md` (the `Basing site` pin + attributes like decoy-risk) ·
> `03-data-contracts.md` §B (what a node/pin carries: status, freshness, confidence).
A geographic map with **pins for physical locations** (bases, sites). Each pin is **color/shape-coded
by trust status** (§3). This is the "at a glance, what's solid vs shaky" view.
- Click a pin → opens the provenance drawer (§5.6) for that location.
- A pin can visibly **change status live** during the demo (a site flips probable → confirmed when a
  new satellite image arrives — this is a scripted hero moment, see §7).
- **OPEN →** how to show a *stale* location (was confirmed, now aging) on a map without it looking the
  same as "probable." Faded pin? A little clock badge? An age ring?
- **OPEN →** clustering / labels when pins overlap; how much basemap detail vs. how much we mute it so
  the pins pop.

### 5.2 The Graph explorer — "how does it all connect?"

> 📎 `01-entities-and-relationships.md` (node/edge vocabulary) · `03-data-contracts.md` §B (the fields a
> node/edge carries).
A node-link diagram of the supply chain / structure: manufacturer → component → import → unit →
location, etc. Nodes are entities; edges are relationships. **Both nodes and edges carry trust status**
and must show it.
- Click any node or edge → provenance drawer.
- This is where the analyst traces a chain by eye and where a multi-hop answer (§5.4) can be
  **visually highlighted as a path** through the graph.
- **OPEN →** graph readability at ~15–25 nodes: layout (layered? force-directed? manual?), how edges
  show both *type* (manufactures vs. based-at) and *status*, and how we avoid hairball-feel. A
  **chokepoint** node (a single point everything depends on) should be visually emphasizable — that's
  the analytic payoff the analyst is hunting for.
- **OPEN →** do Map and Graph live side-by-side (linked selection — click a pin, its node highlights)
  or as switchable tabs? Linked is more powerful, more work.

### 5.3 The subject / lens control — "what am I looking at?"

> 📎 `01-entities-and-relationships.md` (intro) — "the subject is a saved lens over one shared graph, not a
> separate database."
A control to pick or define the **subject** (the thing under investigation). Switching subjects
re-focuses the whole workbench (map, graph, answers) on a different anchor. For the demo there's one
subject, but the control should exist and imply others are possible.
- **OPEN →** how prominent is this — a top-bar dropdown? a dedicated start screen? For a demo, subtle
  is fine; but it's the entry point conceptually.

### 5.4 The "Ask" view — cited multi-hop answers (arguably the centerpiece)

> 📎 `03-data-contracts.md` §E — the answer's structure: hops, per-hop citations, the observed-vs-inferred
> tag, and the refusal payload · `02-trust-and-credibility.md` §8 (why/how it refuses).
The analyst asks a hard question in natural language ("trace this deployed battery back to its
component supplier and name the weak link"). The system decomposes it, walks the graph, and returns a
**narrative answer where every single claim has an inline citation** you can click to see the source.
This view must do three special things:

1. **Cite everything.** Every factual sentence carries a source chip. No citation = we don't say it.
2. **Separate what we *saw* from what we *reasoned*.** "Observed: the battery is at Site K (satellite
   image, dated)." vs. "Inferred: the radar is the *candidate* chokepoint — the only supplier visible in
   open sources, though whether it's truly sole-source is a Known Gap." These must
   be *visually distinct* — the analyst has to know which parts are fact and which are the machine's
   deduction. **OPEN → how to render observed-vs-inferred** (two-column? tags? a left-margin rail?
   different typographic treatment?). Important and unsolved.
3. **Refuse when it can't answer.** If the question hits a gap in the evidence, the answer is an
   explicit **"insufficient evidence to assess"** that names *what's missing* and *when the next
   relevant data is expected* — not a guess. This "honest refusal" state should feel deliberate and
   trustworthy, almost a *feature to show off*, not an error message. **OPEN → design the
   insufficient-evidence answer** so it reads as rigor, not failure.

- **OPEN →** show the answer's reasoning path lit up on the graph (§5.2) as it's given? Powerful if it
  works.

### 5.5 The Review Queue — the human-in-the-loop inbox

> 📎 `03-data-contracts.md` §D — the reusable card envelope + the three built-deep payloads (merge,
> status-override, alert-disposition), their options, and the priority/sort dimensions.
This is where the system **escalates the hard calls to the analyst.** It's a prioritized list of
decisions only a human should make. Each item shows the context, the options, and a one-click action;
acting on it **changes the picture** (map/graph/answers update). The **queue is one surface that hosts
several item *types***; for the demo we build **three** deeply, and the design should assume more types
(ontology extensions, assessment sign-off, integrity dispositions) plug into the *same* card pattern
later — so design the card as a reusable template, not three bespoke screens. The three now:

- **Merge decisions** — "Are these two names the same thing?" The system is unsure whether, say,
  "FD-2000" and "FT-2000" are the same system (they're *not* — a classic trap) or two spellings of one
  entity. Analyst says merge / keep separate. → the graph changes.
- **Status overrides** — analyst promotes/demotes a fact ("this isn't confirmed, drop it to probable")
  → downstream answers change.
- **Alert dispositions** — a tripwire fired (§5.7); analyst marks it real / noise / needs-more.

A **contradiction** (two sources disagreeing about the same moment — §3) lands here as a hard call. A
**supersession** (the world changed) does *not* — it resolves automatically to a stale-with-successor
state, so we don't waste the analyst on a non-conflict. That distinction should be visible in how (and
whether) each shows up in the queue.

The queue embodies the product's "protect the analyst's attention" promise: the easy 90% flows through
automatically; only the ambiguous 10% lands here. **OPEN → the review-item card design** (how to show
"here's what I think, here's why, here's the evidence, decide") and **queue prioritization** (what's at
the top, how urgency/materiality reads). This screen is where "human in the loop" becomes real or
becomes decorative — it matters a lot.

### 5.6 The Provenance drawer — "how do you know that?"

> 📎 `03-data-contracts.md` §C (every ingredient of the confidence breakdown) · `02-trust-and-credibility.md`
> §4 (the independence idea it visualizes) · a real source in `reference/corpus/`
> (`d11_recycled_image.txt` is exactly the "5 sources, 2 independent looks" case).
The cross-cutting panel that answers the analyst's constant question. Opens over any view when they
click a node/edge/pin/citation. Shows, for the selected thing:
- its current **status + confidence + freshness** (and *why* — the breakdown);
- the **list of supporting claims, grouped into genuinely-independent clusters** (see the independence
  note below — this grouping is the whole point, not a cosmetic list);
- each claim → the **exact source document and the exact line/row/image region** it came from;
- any **contradicting** or **integrity-flagged** evidence (e.g. "this image was first seen in 2019").
- an **action** to override (feeds the review queue / decision log).

**Independence is subtler than "count the sources," and the drawer has to show it.** The system only
treats sources as corroborating if they're independent on three counts: different *publisher*,
different *way of finding out* (a satellite image vs. a written report are two looks; two reposts of
one photo are one look), and different *side* (two sources that both benefit from the same story don't
independently confirm it). So the honest picture is often *"5 sources, but really 2 independent looks"*
— and the drawer must make that legible, because it's exactly how the product avoids being fooled by
manufactured consensus. This is the visual heart of "lead with credibility."

**OPEN → this is the most-used surface in the product; its information hierarchy is critical.** How do
we show a confidence *breakdown* — "*looks* like 5 sources, is really 2 independent looks; here's a
too-clean warning on one of them" — without a wall of numbers? How deep does one click go before it's
too much?

### 5.7 Alerts / Observables — the monitoring pulse

> 📎 `03-data-contracts.md` §F (the tripwire + fired-alert fields) · `02-trust-and-credibility.md` §9
> (coverage decay / "degrade visibly, never silently").
The analyst can define a **tripwire** — a condition that fires an alert when incoming data meets it.
When it trips, an **alert** appears; the analyst dispositions it (→ review queue). This is the "it's a
live monitor, not a one-time report" dimension.
- For the demo there's **one** tripwire, wired end-to-end: **a unit relocating** (its location changes
  — the §7 beat 7 story). The UI should make a firing feel like a meaningful event, then route to
  disposition. (A couple of other tripwires exist in config but aren't part of the demo narrative —
  that's deliberate, to show tripwires are user-definable, not hardcoded.)
- **OPEN →** where alerts live (a bell + panel? a feed on the left rail?) and how a fired alert visually
  connects to the thing that changed on the map/graph.

### 5.8 Credibility settings — "whose word counts for how much?"

> 📎 `03-data-contracts.md` §H (the levers a settings screen exposes) · `02-trust-and-credibility.md` §5
> ("the analyst, not the engineer, owns the trust rules").
A settings surface where the analyst tunes **how much each type of source is trusted** (the weights
behind the status computation). This exists because the product's premise is that *the analyst*, not the
engineer, owns the trust rules. Low-frequency screen; probably a settings panel, not a main stage.
- **OPEN →** how much of this to expose in the demo vs. keep as a "yes, it's configurable" gesture. My
  lean: a clean read-only-ish panel that shows the levers exist, with maybe one live slider. Your call
  on how much interaction is worth the design effort.

---

## 6. The status/visual-language spec (hand this to whoever builds the design system)

> 📎 `02-trust-and-credibility.md` §§2–7 (definitions behind status / freshness / source-tier / supersede /
> Known-Gap) + `01-entities-and-relationships.md` (every node / edge / pin / chip that has to wear this
> visual language).

Consolidated so it's in one place. Every visual element that represents a fact must express:

- **Status** (primary): confirmed / probable / possible / contradicted / stale.
- **Freshness** (secondary overlay): fresh → aging → stale. A continuous decay, binned for display.
- **Source tier** (tertiary, on demand): official / analysis / named-social / anonymous.
- **Node vs. edge vs. pin vs. citation-chip** — the same status language has to work across all four
  form factors.
- **Two relationship treatments** (not statuses, but they need a visual):
  - **Superseded** — old node greyed to stale with a "replaced by →" link to its successor (a
    *timeline* look, calm, not an alarm).
  - **Known Gap** — a first-class "known unknown" object, with two variants that must read
    differently: *coverage gap* (pending — "next pass Tuesday") vs *structurally unobservable*
    (permanent boundary — never resolvable). See §3.
- **Special emphasis:** *chokepoint* nodes (the critical single-points-of-failure) and
  *integrity-flagged* items (possible fakes / recycled media) need their own accent.

**Constraints:** must survive (a) colorblind viewers, (b) a washed-out projector on a live demo call,
(c) dense scenes. So encode status in **more than color** (fill, border, shape, icon). Aim for a
system a viewer can learn in ten seconds and a legend can express in one corner.

> **OPEN → deliver this as a small legend/style tile first** — the five statuses × the freshness
> overlay × source-tier icons, plus the superseded and Known-Gap treatments, shown on a node, an edge,
> a pin, and a citation chip. If that one tile reads cleanly, the whole product will. This is the
> highest-leverage thing you can draw.

---

## 7. The hero flow (the demo storyboard — make *this* feel great)

> 📎 Each beat's data is in `03-data-contracts.md` (the answer §E, the merge card §D, the relocation alert
> §F) and `02-trust-and-credibility.md` §7 (the supersede-vs-contradict climax). The recycled-photo beat is
> real in `reference/corpus/d11_recycled_image.txt`.

On the interview call, one thread is walked end-to-end. This is the sequence the whole UI is optimized
around; everything else is in service of these ~90 seconds feeling effortless and trustworthy. The
concrete scenario is already built into the demo data. The beats:

1. **Ask the hard question.** Analyst types: *"Trace the battery at [Site K] back to its component
   supplier and name the weak link."*
2. **Cited answer returns**, with the reasoning path lighting up across the graph. Every claim has a
   clickable source. **Observed** facts (it's at Site K — satellite image) are visually separated from
   the **inferred** conclusion (the radar is the *candidate* chokepoint — the only supplier visible in open
   sources; whether it's truly sole-source is a Known Gap, not asserted).
3. **Click to prove it.** Analyst clicks a claim → provenance drawer → the exact source line. "One
   click to truth."
4. **Show the honest refusal.** Ask about a location where the evidence is a cloud-covered/old
   satellite frame → system returns *"insufficient evidence, missing overhead confirmation, next
   coverage due [date]"* instead of guessing, and surfaces the **Known Gap** as its own object. **This
   is the money moment** — it proves the product doesn't bluff.
5. **Catch the fake.** A recycled 2019 photo has been reposted as "new deployment" with two
   "independent" reshares. A naive system would count three sources and believe it. Ours **flags it**
   (the photo was first seen in 2019; the reshares aren't really independent) and **refuses to promote
   it to confirmed** — visible in the provenance drawer.
6. **Human overrules the machine.** A merge trap surfaces in the review queue (are these two systems
   the same?). Analyst decides → the graph visibly updates → and the next answer changes accordingly.
   Proves the human is really in control.
7. **The live tripwire — a relocation.** New satellite data arrives showing the unit has *moved* (base A
   → base B). A single new image only lifts the new location to **probable** (one look, and it could be
   a decoy); a second, independent look confirms it. Then the **map animates**: a new pin appears at
   base B, and the old pin at base A quietly greys to **stale** with a "moved →" link — *superseded, not
   contradicted*. An alert fires; the analyst dispositions it. This one beat shows freshness decay, the
   "one look isn't enough" caution, and the world-changed-vs-sources-disagree distinction all at once —
   it's the richest single moment in the demo, so it deserves the most choreography.

**OPEN → the demo choreography is a design deliverable in itself.** Which surface is on screen for each
beat, how transitions feel, whether the graph-path-highlight and the relocation animation (new pin
appears, old pin greys + "moved →" link) are animated. A smooth, legible walk through these seven beats
is worth more than any individual screen being pretty.

---

## 8. Explicitly out of scope (don't design these)

Keeping this tight so we don't over-build:
- No user accounts / login / multi-user / permissions. Single analyst, single session.
- No live data ingestion UI — the corpus is pre-loaded and frozen for the demo. (Documents "arriving"
  in the tripwire beat is a scripted reveal, not an upload flow.)
- No dashboard-of-dashboards, no KPI tiles, no "executive overview." This is a working instrument, not
  a status board.
- No mobile. Desktop, wide screen, demo-on-a-laptop.
- Not a big-data UI. ~15–25 entities, ~14 source documents. Density comes from *depth per item*, not
  volume.

---

## 9. Summary of what I most need from you

In rough priority order:
1. **The status visual language** (§3, §6) — the legend tile. Everything hangs off this.
2. **The provenance drawer** (§5.6) — the most-used surface; nail its hierarchy.
3. **The Ask/answer view** (§5.4) — cited, observed-vs-inferred, and the honest-refusal state.
4. **The review-queue item card** (§5.5) — where "human in the loop" lives or dies.
5. **Overall layout/navigation** (§5) — how the rooms connect.
6. **The demo choreography** (§7) — the seven beats, made to flow.

Every **OPEN →** above is a decision I'd like your product instinct on. Everything *not* marked open is
a settled functional requirement — design freely within it, but if something feels wrong, push back;
these are my calls, not laws of physics.
