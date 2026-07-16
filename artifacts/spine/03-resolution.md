# Spine — Entity Resolution

Covers: how identity is resolved across sources. In C this is the *marquee* graded feature
(`../md/04-claude-chat.md` Q1) — the whole value rests on confidently fusing "Factory 404" =
"State Research Bureau 404" = a chassis in a photo into one node across transliterations and shell aliases.

---

## Decisions

### Resolve like a senior analyst would — relational, not just string/embedding
Resolution is **collective / relational entity resolution**, not attribute similarity alone. The signal
stack, roughly in the order an analyst weighs them:

1. **Attribute match** — name variants, transliteration rules, IDs, HS codes.
2. **Relational match (highest value)** — **shared neighbourhood**: two nodes that both connect to the
   same regiment and the same site are probably the same entity even if names differ. This is the
   "analyst" signal that pure similarity misses.
3. **Contextual/temporal consistency** — can't be in two places at once; timeline coherence.
4. **Corroboration weighting** — a merge asserted by a credible source beats one merely inferred.

### Confidence bands with a HITL middle
Every candidate merge gets a confidence:
- **above high threshold** → auto-merge;
- **below low threshold** → keep separate;
- **in between** → route to HITL for accept / reject / split (via the adjudication service,
  `05-hitl-and-triage.md`).

### HITL merge decisions grow the alias table (learning)
Each analyst merge/split decision is written back and **grows the alias table**, so the same pair
auto-resolves next time. This is one concrete adaptation mechanism (`06-adaptation.md`).

### False-merge discipline
Resolution must be as good at *keeping things apart* as fusing them. C has real false-merge traps (e.g.
**FD-2000 ≠ FT-2000** — different systems the trade press conflates; radar-vs-system conflation like
HT-233 vs FD-2000) catalogued in `../md/05-data-scoping-C.md` §4. A confident wrong merge corrupts the
ORBAT; the middle band exists precisely to surface these to a human.

---

## Open questions
- **Blocking / candidate generation** — how do we propose merge candidates without O(n²) comparison?
  (embedding-nearest-neighbour + attribute blocking keys). Matters at scale, not at demo size.
- **Threshold values** — the high/low band cutoffs. Pick defensible defaults; make configurable; tune
  from HITL decisions over time.
- **Merge representation** — store merges as reversible (a "same-as" edge in the evidence layer) rather
  than destructive node-collapse, so an analyst can split later. Leaning reversible.
- **Transliteration handling** — rule-based normaliser vs learned. C needs Triumf/Triumph/Триумф and
  Hongqi/红旗/紅旗 (see `../md/05-data-scoping-C.md` §4).

## Research directions
- **Collective / relational ER literature** — techniques where resolving one pair informs others
  (relationship-aware ER, graph-based dedup). Candidate research task.
- **IAF/OSINT tradecraft** — what disambiguates units/formations/platforms in practice (designators,
  garrison, equipment fingerprint). Feeds the materiality work in `../C/01-materiality-ontology.md`.
