# T4 → DATA / INGEST — every `source` node in the live graph is degree 0

**Observation only — nothing changed on my side.** Filed per CLAUDE.md ("data issues → `tmp/conv/`,
don't self-fix"). Found while rebuilding the Graph stage (`tmp/conv/T4-graph-legibility.md`).

## What I see

Cold-boot `GET /view` (`171` nodes / `105` edges, `config_version 1`, scenario `hq9p_primary`):

- **54 of the 171 nodes have `type: "source"`.**
- **Not one of them is an endpoint of any edge.** All 54 are degree 0. They are ~48% of the node
  count and 0% of the edge count.

Examples of what these nodes are: `@ArmchairGeneral_IN`, `@ISPR_Watch`, `@IndoPacGuardian`,
`Jane's`, `Global Times`, `Chinese state media`, `Inter-Services Public Relations`,
`International Institute for Strategic Studies`, `CSIS Missile Threat`, `AirDef_Analyst09`.

They read like **source records / publishers**, i.e. evidence-layer objects, and they are correct
and useful as such — every one of them turns up properly attributed inside
`GET /evidence/{id}` as the origin of a claim. The provenance drawer works. The question is only
whether they belong in the **knowledge layer's node list** at all.

## Why it matters (and what I did about it in the meantime)

`spine/01` splits the graph in two: an append-only **evidence** layer of sourced claims, and a
derived **knowledge** layer of resolved entities and relationships. `GET /view`'s `nodes` array
currently mixes both. Any consumer that treats `/view.nodes` as "the entities" therefore
over-counts by ~46%, and any consumer that draws them gets 54 unconnected boxes — which is
literally what the Graph stage was doing and what the complaint was about.

I have **not** touched the corpus, the answer key, or the API. On the frontend I put source nodes
behind an off-by-default "sources" layer chip, and when it is on they are listed (not drawn) with
the honest line *"Source records carry claims, not relationships, so they are all listed here."*
That is a correct description of today's data, not a workaround pretending otherwise.

## The question for you

Three readings, and I don't think it's mine to pick:

1. **Intended.** Sources genuinely are knowledge-layer entities in this ontology (a publisher *is*
   a thing you can assert about — ownership, alignment, track record — and the `d23_cpmiec_false_attribution`
   / `d15_globaltimes_aligned` material suggests source *alignment* is analytically live). If so,
   they are simply not yet joined up, and the gap is missing `published-by` / `aligned-with` /
   `operated-by` edges. This is the most interesting version: source-alignment edges would make the
   independence story visible on the graph instead of only inside the drawer.
2. **Leakage.** Evidence-layer objects are being emitted into `/view.nodes` when they should only
   be reachable through `GET /evidence/{id}`. Then the fix is at the view builder, and 54 nodes
   should disappear from the node count.
3. **Extraction artifact.** Source handles are being extracted as entities by the claim extractor.
   Then it is an INGEST issue and the fix is upstream.

Whichever it is, one thing is worth confirming either way: **is `node_count` in `/health` and
`/view.meta` meant to include the evidence layer?** Anything that reports "171 entities" to a
reviewer is currently reporting 117 domain entities plus 54 source records.

## Also worth a look while you're in there

- **11 nodes have `type: "unknown"`** (e.g. `HT-233`, `Pakistan`, `TAS5380`, `TEL`, `HQ-9/P TEL`,
  `HQ-9B fire unit`, `HT-233 phased-array engagement radar`, `Hongqi-9 family`,
  `PLA's domestic HT-233`, `S-300P/PMU-series`, `modified export variant`). Several of these look
  like they should be `component` or `variant` and have a near-duplicate that already is —
  `HT-233` exists as both an `unknown` and a `component`. The Graph stage gives them their own
  "unresolved type" column rather than guessing, but they look like resolution/typing misses.
- **`known_gap` nodes (6) are all degree 0 too.** For gaps that is arguably correct (a gap is an
  absence), but `product/00-ux-brief.md` §3 wants a Known Gap to be a first-class object *on* the
  graph — which needs an edge from the entity whose gap it is (the demo fixture models exactly
  this: `paad --e-gap--> tel`). Live has no such edges, so no gap is attached to anything.

— T4 (`qa/t4-graph-legibility`)
