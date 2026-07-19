# EVAL RCA handoff — ASK (grounding follow-on): the hero path still speaks the claim the oracle just removed

## Context

The `answer_key` was grounded to the corpus (D-G1…D-G4, applied on `fix/answer-key-grounding-apply`;
audit: `ANSWER-KEY-GROUNDING-AUDIT.md`, owner handoff: `handoff-answer-key-grounding.md`). D-G1 removed the
un-sourced `mfr_casic --manufactures--> comp_ht233 (confirmed)` edge, because two grade-B sources
(`d22` IISS, `d24` CSIS) state the HT-233 manufacturer is **UNKNOWN** and warn that reading the
export-agent/integrator as the maker is *"a hypothesis wearing a fact's clothing."*

**ASK's deterministic hero path still encodes that removed claim in code.** The graph is now honest; the
answer layer is not. This is ASK's share of the grounding fix — a **separate, later** item from the
original `handoff-ask.md` (Phase 4: crash-guard, honest refusal, anchor resolution), and intended to be
**bundled into that post-Phase-4 ASK work**. It sharpens `handoff-ask.md` TL;DR #2 ("hardcodes fallback ids")
from a *robustness* defect into a *grounding* defect.

**Why an analyst cares.** A knowledge graph that correctly records "this component's maker is unknown" is
worth nothing if the agent that *speaks* for it fills the blank with a plausible name. Attribution is the
single most-abused step in Chinese-SAM OSINT; the scenario exists to punish exactly this. An honest store
plus a confabulating answer layer is still a fabricated assessment — the disqualifying failure.

**Not blocking any current PR:** ASK's tests run against a hand-authored fixture
(`backend/tests/agent/fixtures.py`), not the oracle, so the answer_key edits leave them green. The defect is
**latent against the real rebuilt graph**.

## TL;DR

1. **ASK-G1 (blocks-demo):** the hero path's maker lookup falls back to the literal `"mfr_casic"`, so the
   agent asserts CASIC as the HT-233 maker — the exact un-sourced claim D-G1 deleted.
2. **ASK-G2 (major):** the lookup queries the wrong edge type (`manufactures`); post-D-A a Manufacturer→
   Component link is `supplies-component`, so the query returns empty *by construction* and the fallback
   always fires.
3. **ASK-G3 (major):** the flagship trace destination and the fixture/test triad still encode the old
   4-hop chain ending in the false `manufactures` hop; the oracle's path now terminates at `comp_ht233`.

## Findings

### ASK-G1 — Hero path asserts an un-sourced manufacturer via a hardcoded fallback (blocks-demo)

- **Symptom:** for the flagship query the agent names **CASIC** as the HT-233's manufacturer, regardless of
  what the graph says — including when the graph correctly holds no maker edge at all.
- **Evidence:**
  - `backend/chanakya/agent/loop.py:170-171` —
    `makers = graph_neighbors(comp_id, edge_types=["manufactures"])`;
    `mfr_id = next((n["neighbour_id"] for n in makers.get("neighbours", [])), "mfr_casic")`.
    The `next(..., "mfr_casic")` default is an **unconditional assertion of a specific manufacturer** on the
    empty path.
  - `backend/chanakya/agent/loop.py:128` — `HERO_SUB_QUESTIONS[2]`: *"…and who manufactures it?"* presupposes
    a maker exists (a leading question; there is no "or is it a gap?" branch).
  - `answer_key.json` (post-D-G1) — no `mfr_casic → comp_ht233` edge; `comp_ht233.manufacturer = "unknown"`;
    `gap_ht233_maker` present; the only maker link is `mfr_23rd_ri --supplies-component--> comp_ht233
    (possible)`.
  - Corpus: `d22` *"The manufacturer of the HT-233 should therefore be treated as unconfirmed/unknown"*;
    `d24` *"the manufacturer of the HT-233 engagement radar … cannot be established from open sources."*
- **Root cause:** the fallback was written when the oracle *did* carry a confirmed CASIC→HT-233 edge. With
  that edge gone, the default is no longer a harmless safety net — it manufactures an attribution.
- **Recommended fix:** delete the literal default. When no maker edge resolves, the hero path must
  **surface the Known Gap** rather than name anyone: report *"HT-233 manufacturer: UNKNOWN — Known Gap
  (`gap_ht233_maker`); best open-source candidate CASIC 23rd Research Institute / BIRM, unconfirmed"* and
  reach **CASIC only as the confirmed program prime / design authority** via `var_hq9p`
  (`mfr_casic manufactures var_hq9p`, `sustain_techdata design-authority-for var_hq9p`), explicitly labelled
  as such — never as the radar's maker. Reword `HERO_SUB_QUESTIONS[2]` to *"which component is the
  fire-control chokepoint, and who supplies it — or is that a collection gap?"*
- **Severity:** blocks-demo (fabricated attribution in the spoken answer; the non-negotiable).
- **Cross-service dependencies:** none to start — this is ASK-local. Full end-to-end effect needs RESOLVE's
  RES-G1 (`handoff-resolve-score-grounding.md`) so the real graph carries the `supplies-component` candidate.

### ASK-G2 — Maker lookup uses the wrong edge type post-D-A (major)

- **Symptom:** `graph_neighbors(comp_id, edge_types=["manufactures"])` returns empty for **every** component,
  so ASK-G1's fallback fires 100% of the time.
- **Evidence:** `config/ontology.yaml:83-84` — `manufactures` is tightened to `manufacturer → variant`;
  `supplies-component` is the sole `manufacturer → component` edge (D-A / D-A.1). `loop.py:170` still asks
  for `manufactures` on a **component** node.
- **Root cause:** the hero path predates the Phase-1 edge-vocabulary tightening; it was never re-pointed.
- **Recommended fix:** query `edge_types=["supplies-component"]`, and **carry the edge status through** — a
  `possible` supplier is a *candidate*, not an answer. Only a `confirmed` supply edge may be stated as the
  maker; anything less routes to the Known-Gap phrasing from ASK-G1.
- **Severity:** major (mechanically guarantees ASK-G1).
- **Cross-service dependencies:** none.

### ASK-G3 — Flagship trace destination + fixture/test triad encode the removed chain (major)

- **Symptom:** the hero trace runs `src=site_karachi → dst=<maker>`, and the fixture/tests assert the old
  4-hop chain `based-at → inducted-into → equips → manufactures` terminating at `mfr_casic`.
- **Evidence:**
  - `backend/chanakya/agent/loop.py:174` — `graph_find_paths({"src": site, "dst": mfr_id})`.
  - `answer_key.json` `worked_query` (post-D-G1) — `expected_path` now terminates at **`comp_ht233`**;
    `expected_path_edges` = `based-at`, `inducted-into`, `equips` (3 hops); `expected_path_edges_note`
    states CASIC is reached as program prime via `var_hq9p`, never as the radar maker.
  - Fixture/test coupling (all still green because fixture-based, all now oracle-inconsistent):
    `backend/tests/agent/fixtures.py:9` (docstring chain), `:139` (claim `d21-l2` =
    `mfr_casic manufactures comp_ht233`), `:285` (the edge);
    `backend/tests/agent/test_tools.py:88-97` (`test_find_paths_hero_chain` asserts the 4-hop chain +
    `hop_count == 4`), `:100-104` (hop-cap test assumes a 4-hop chain);
    `backend/tests/api/test_ask.py:20`; `backend/tests/agent/test_fixture.py:26`.
- **Root cause:** two representations of one hero trace (oracle + ASK fixture) drifted when the oracle was
  corrected; only the oracle was updated (deliberately — ASK is a separate owner).
- **Recommended fix:** terminate the flagship trace at the **chokepoint** (`comp_ht233`) per the oracle, and
  render CASIC as a distinctly-labelled program-prime hop off `var_hq9p`. Re-point the fixture edge
  `mfr_casic manufactures comp_ht233` → `mfr_casic manufactures var_hq9p` (and claim `d21-l2` likewise),
  update the docstring, and update the four coupled assertions to the honest trace. Keep `comp_ht233` a
  **candidate** chokepoint with `substitutability_state = UNKNOWN` (the existing
  `test_query_graph_ht233_is_indeterminate_not_match_for_sole_source` invariant must stay green).
- **Severity:** major (demo/oracle divergence; the tests currently certify the wrong narrative).
- **Cross-service dependencies:** none for the fixture/test work; the live trace shape depends on RES-G1.

## Verify

- Hero answer for the flagship query names **no** manufacturer for HT-233; it names the **Known Gap** and
  the unconfirmed 23rd-RI candidate, and labels CASIC as *program design authority*, not maker.
- `grep -n 'mfr_casic' backend/chanakya/agent/loop.py` returns **no** literal-default assignment.
- The maker lookup queries `supplies-component` and respects edge status (`possible` ≠ stated).
- Flagship trace terminates at `comp_ht233`; the four coupled assertions match the oracle's
  `worked_query.expected_path` / `expected_path_edges`.
- `test_query_graph_ht233_is_indeterminate_not_match_for_sole_source` still green (HT-233 must stay in the
  *indeterminate* partition for a `known-sole-source` filter — never a match).
- Cross-check against `answer_key.json` `worked_query.expected_answer` (unchanged and already honest) — the
  spoken answer should now match it verbatim in substance.

## Bundling note

Intended to be folded into the **post-Phase-4 ASK** work alongside `handoff-ask.md` (crash-guard + honest
refusal + anchor resolution) — ASK-G1's "surface the gap instead of naming someone" is the same honest-refusal
machinery that handoff wants, applied to attribution. Decisions: `RCA-FIX-DECISIONS.md` D-G5.
