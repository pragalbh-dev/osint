# T4 — Graph stage legibility

**Branch:** `qa/t4-graph-legibility` · **Scope:** `frontend/src/components/stage/GraphView.tsx` +
new `graphLayout.ts` (+ a small additive change to `api/adapters.ts` / `demo/scenario.ts`, see
§6). **Not merged, not pushed.**

Screenshots (gitignored by repo policy — on disk in the worktree):
`tmp/qa/t4/T4-before-live-graph.png` · `T4-after-01-knowledge-layer.png` ·
`T4-after-02-focus-2hop.png` · `T4-after-03-focus-1hop.png` · `T4-after-04-identity-overlay.png` ·
`T4-after-05-unconnected-tray.png` · `T4-after-06-evidence-layer.png` ·
`T4-after-07-tray-pick-isolated.png` · `T4-after-08-demo-unchanged.png`.

---

## 1. The complaint, and what was actually wrong

> "the graph looks super cluttered as shit right now… maybe also try out selected display of graph
> based on entity selection."

The cold-boot live graph is **171 nodes / 105 edges**. Profiled:

| | |
|---|---|
| isolated nodes (degree 0) | **113 of 171** — `source` 54, `component` 20, `basing_site` 14, `variant` 10, `known_gap` 6, `manufacturer` 5, `unit` 3, `contract_import_event` 1 |
| connected components | 121; the largest has 37 nodes, the rest are singletons and pairs |
| edges that are resolution bookkeeping | **49 of 105** (`same-as` 40, `distinct-from` 9) — ~47% |
| real domain edges | 56 (`equips` 16, `observed-at` 14, `inducted-into` 9, `exported-by` 4, `imported-by` 4, `manufactures` 4, `supplies-component` 2, `based-at` 2, `component-of` 1) |

So the "tangle at the top" was ~48 entities plus 49 bookkeeping edges drawn as if they were domain
knowledge, and the "marching rows" underneath were the 113 orphans that `cose` had nothing to pull
on. **The diagnosis is not "the layout is bad" — it is that three different things were being drawn
as one thing.** The repo's headline architecture (`spine/01`) is a **bi-level graph**: an
append-only *evidence* layer and a derived *knowledge* layer, with entity resolution sitting between
them. The graph view was flattening all three onto one canvas.

## 2. What I built

### Three layers, drawn as three layers

| layer | default | what it is |
|---|---|---|
| **Knowledge** | **on** (locked) | domain entities joined by domain relationships — the derived picture. 48 connected entities, 56 edges. |
| **Identity links** | off, one chip | `same-as` / `distinct-from`. Bookkeeping about **our records**, not about the world. Turning it on adds 49 links and pulls **10 more entities** onto the canvas that nothing but an identity edge connects. |
| **Sources** | off, one chip | the 54 evidence-layer `source` records. One-click-to-source already lives in the provenance drawer; a `source` node on the canvas is that same fact drawn twice. |

Each chip carries its own count, so the analyst can see what is being withheld before deciding to
look at it. The identity overlay is deliberately *discoverable rather than default*: when
adjudicating a merge it is the most interesting thing on screen, and the rest of the time it is 47%
of the ink for 0% of the domain content.

### Entity-selection focus (the ego-graph)

Selecting any entity focuses its **ego-graph at a controllable hop depth (1 / 2 / 3)**; everything
else is hidden, the viewport re-frames, and **edge type labels turn on** (`equips`, `observed-at`,
`manufactures`, …) so a multi-hop trace is readable hop by hop rather than as anonymous lines. A
`show all ×` chip returns to the overview, and a live readout says `27 of 48 connected entities
shown`.

**Positions never move when focusing** — the ego-graph is a filter over a fixed layout, not a
re-layout. That preserves spatial memory (the analyst learns where the component column is) and it
means a focused chain still reads left-to-right along the supply chain.

I chose **hide, not dim,** for out-of-focus elements. At ~50 nodes a 16%-opacity ghost layer is
still a tangle to read past, and the whole point of focusing is to be able to read one chain.

### The isolated-node dump, killed honestly

Orphans are **off the canvas but never dropped**. A tray at the bottom of the stage reads
`69 entities have no asserted relationship — show`, and expands into a compact type-grouped,
named, clickable list with the line:

> *Known to the graph, but no relationship has been asserted about them yet — a collection gap, not
> a rendering one. Click any to open its provenance.*

That is the CLAUDE.md non-negotiable applied to a rendering decision: **a known entity with no
relationships is a finding, not an artifact.** Clicking one focuses it (alone, correctly) and opens
its provenance drawer, and the readout switches to *"no relationship has been asserted about this
entity — its provenance is still one click away"* rather than lying with "1 of 48". The worked
example in `T4-after-07`: `HT-233` the *component* is **confirmed on 7 sources / 7 independent
looks** and has **zero modelled relationships** — visible now, invisible before.

Known Gaps get a dashed grey chip in the tray (they are all degree-0 today), so "we do not know"
still does not look like "we know".

### Layout: role columns, deterministic by construction

Nodes are banded into **columns by ontology role, left → right along the supply chain**:
`manufacturer → trading org → component → import event → variant → unit → basing site →
unresolved type`, each column captioned. Within a column, hubs first (degree desc, then id asc).

This does three things at once: the x-axis carries the analytic story C exists to tell; the column
caption removes the `\ntype` second line from every node label (shorter labels, bigger type); and
the layout is a **pure function of the node/edge sets** — no physics, no seeded randomness, no
`cose`. Same graph in, same pixels out, every run, which is what CLAUDE.md requires of the demo. It
is unit-tested as such (`graphLayout.test.ts` reverses both input arrays and asserts identical
positions).

Empty role bands take no column slot, so a layer toggle never opens a hole in the middle of the
chain.

### Status visual language: reused, not reinvented

No new visual channel. Status stays **border style + fill** off the existing
`design/tokens.ts` (`solid = confirmed`, `dashed = probable`, solid grey = stale, dashed grey
unfilled = gap, coral = contradicted), the chokepoint halo stays a dashed ring, `supersedes` keeps
its grey arrow. Node **type** is carried by *column position*, not by hue — which is the only way
to add a second dimension without breaking "status is never hue" or building a Christmas tree.
The legend grew to spell out the column axis, the identity-link treatment (only when that layer is
on) and the click affordance.

### Zoom / pan, and re-framing

DEMO keeps the mockup's locked framing. LIVE enables zoom + pan (nodes stay ungrabbable, so the
*layout* is still deterministic — only the viewport moves) plus a `fit` chip. Re-framing is deferred
to the next animation frame: fitting in the same tick measures the *pre-change* visible set, which
silently left focus mode framed for the whole graph. While the 560px provenance drawer is open the
fit frames into the uncovered part of the stage — but only when that leaves ≥620px and ≥55% of the
width, because on a laptop-width stage insetting the full drawer squeezes the graph into ~45% of
the canvas, and *partly covered and readable* beats *fully visible and tiny*.

## 3. DEMO mode is untouched — verified, not asserted

The graded hero thread renders **pixel-identical to `origin/main`**. Verified by screenshotting the
demo Graph stage on stashed vs. applied working trees and diffing:
`ImageChops.difference(...).getbbox() → None`. (The first pass was off by an 11px band — a
`line-height` 1.4→1.5 drift in the legend — which is exactly why this was checked rather than
reasoned about.)

All the new machinery is gated on `mode === 'live' && liveView != null`, so the *live-before-first-
`/view`* fallback (which serves the demo fixtures verbatim) also keeps its hand-placed preset
instead of having positions re-derived for nodes that carry no ontology type.

## 4. What I rejected

- **A force layout with a fixed seed.** Cytoscape's `cose` has no seed parameter; "deterministic
  physics" would have meant vendoring a layout. And a force layout on a graph with 121 components
  spends its whole budget separating singletons. Rejected in favour of computing positions myself.
- **Dimming instead of hiding out-of-focus elements.** See above — at this density it does not buy
  legibility.
- **Compound/parent nodes per type.** Cytoscape compounds would draw a box around each role band.
  Tried mentally against the data: with 56 edges the boxes would carry more ink than the edges do,
  and the column caption already says the same thing for free.
- **Re-laying-out on focus (concentric rings around the selected node).** Reads well in isolation,
  but destroys spatial stability across selections and makes the supply chain unreadable as a chain.
- **Putting orphans on the canvas in type-clustered blocks.** Honest, but it re-imports the exact
  noise the complaint was about; 69–123 boxes with no edges is a wall. The tray keeps them
  enumerable and one click from provenance without spending canvas on them.
- **Silently filtering orphans.** Disqualifying under CLAUDE.md.
- **Colour-coding node type.** Breaks "status is never hue" and the colourblind/projector constraint
  in `product/00-ux-brief.md` §6.
- **Changing the DEMO preset** to match the new live layout. The mockup fidelity is graded; the
  complaint is about live. Two layouts is the right answer here, not one compromised one.

## 5. What an analyst can do now that they could not before

1. **Read the supply chain.** Before: an undifferentiated tangle. Now: manufacturer → trading org →
   component → import → variant → unit → basing site, captioned, hub-first.
2. **Trace one entity.** Select it, pick a hop depth, read the labelled hops. This is the natural
   surface for the multi-hop answer path.
3. **Tell knowledge from bookkeeping.** 47% of the edges were identity records pretending to be
   domain facts. Now they are an overlay you turn on when you are adjudicating identity.
4. **See the collection gaps.** 69 entities we know exist and have learned nothing relational
   about — previously indistinguishable from a rendering bug, now an enumerable list with
   provenance behind each one. `HT-233` (confirmed, 7 independent looks, 0 relationships) is the
   headline example.
5. **Reach the evidence layer deliberately** rather than tripping over 54 source records.

## 6. Shared-file changes other agents should know about

All **additive and backward compatible**; nothing existing changed shape.

- `frontend/src/demo/scenario.ts` — `GraphNodeDef` gains optional `type` (ontology type, e.g.
  `basing_site`) and `name` (the bare name, without the `\ntype` suffix baked into `label`);
  `GraphEdgeDef` gains optional `type` (ontology type, e.g. `same-as`). Both optional, so the
  frozen demo fixtures stay assignable untouched.
- `frontend/src/api/adapters.ts` — `viewToGraphNodes` / `viewToGraphEdges` now populate those three
  fields off the live `/view`. **Why it was needed:** the visual `kind` collapses information the
  graph stage has to have back — `e-link` is *both* `same-as` and `distinct-from`, and nothing in
  the old shape distinguished a `source` node from a `unit`.
- `frontend/src/api/adapters.test.ts` — the `viewToGraphEdges` strict-equality expectation gained
  the `type` field, plus one new assertion that the ontology type survives the collapse into `kind`.
- **No store (`store/workbench.ts`) change** — layer state, hop depth and tray state are local to
  the graph component. **No API/backend change**, so nothing to log in
  `tmp/conv/API-to-FRONTEND-contract-log.md`.
- `GraphView.tsx` exposes `window.__cy` **under `import.meta.env.DEV` only**. The graph draws to a
  `<canvas>`, so headless QA has no DOM to assert against; this is the only way to check what is
  actually on screen. Stripped from the production build.
- New files, owned by this work: `frontend/src/components/stage/graphLayout.ts` (+ `.test.ts`) —
  the pure layer/visibility/layout/ego-graph functions.

Boundaries respected: no edits to `components/drawer/**` or `stage/MapView.tsx`.

## 7. Test status

`make test` → 788 passed, 6 skipped, 1 xfailed. `npx tsc --noEmit` clean. `npx vitest run` →
114 passed (94 existing + 20 new in `graphLayout.test.ts`). `npm run build` clean.

## 8. Open follow-ups (not done here)

- **`source` nodes carry no edges at all** — all 54 are degree 0 in the live graph. That is a
  data-model observation, not a rendering one; filed separately as
  `tmp/conv/T4-to-DATA-source-nodes-carry-no-edges.md`.
- The role order is a constant (`ROLE_ORDER` in `graphLayout.ts`). If the ontology grows a type, it
  falls into an "unresolved type" column rather than breaking — but the ordering itself is not yet
  config-driven the way the rest of the system is. Worth folding into the ontology config if the
  ontology-extension path is built out.
