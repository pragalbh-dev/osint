# Handoff → PHASE 3 (RESOLVE): candidate aliases to verify + unbucketable ambiguities

**Source:** Phase-1 entity-registry compilation pass. Full evidence in
`tmp/conv/eval-rca/phase1-entity-registry-draft.md` §2 (candidates) and §3 (ambiguities). These were
deliberately kept OUT of the confirmed alias seed — they are candidates/ambiguities RESOLVE adjudicates,
not facts DATA-C hardcodes.

## Candidate aliases to VERIFY — do NOT seed as auto-merge (RESOLVE orphan candidate-gen → HITL)
- `H-200` → `HT-233`  (the withheld orphan-alias demo case; verify, don't assume)
- `Type 305B` → `HT-233`  (hedged in-corpus as "derivative")
- `FD-2000B` → `HQ-9/P`  (variant-suffix ambiguity vs the FD-2000 export designator)
- `"extended-range round"` → `comp_interceptor`  (generic descriptor, needs corroboration)

These are exactly the raise-only merge candidates for RESOLVE's LLM candidate-gen + HITL band — the recall
demo. Keep them as proposals; a HITL accept replays into the growing alias table.

## Ambiguities — surface forms that could NOT be confidently bucketed (RESOLVE / HITL adjudication)
- Bare `"engagement radar"` — generic; could be `comp_ht233` or a distinct component.
- `"the System"` — anaphoric; probably `var_hq9p` but context-dependent.
- `"bases in the Karachi ... air defence sectors"` — vague multi-site descriptor, not one basing_site.
- Army/PAF **joint-use conflation at Rahwali** — one doc blurs operator; keep `unit_paad`/`unit_hq9b` distinct.
- Unresolved `"CH-SA-9"` designator — no confident canonical target.
- Army-vs-PAF **variant cross-wiring** in one source doc — a source-asserted link that crosses the
  distinct-from trap; route through RESOLVE veto/HITL, do not auto-merge.

**Action:** RESOLVE consumes these as candidate/veto inputs (Phase 3), not as seeded aliases. The
distinct-from traps (var_hq9p≠var_hq9be≠alias_ft2000; unit_paad≠PAF) must survive all of the above.
