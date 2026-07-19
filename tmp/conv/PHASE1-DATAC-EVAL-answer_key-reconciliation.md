# Handoff → DATA-C + EVAL: answer_key reconciliation (separate task, not Phase-1 code)

**From:** Phase-1 fix. **Owns:** DATA-C (answer_key content) + EVAL (oracle assertions).
**Decisions:** DECISIONS §6 "EVAL" D-A / D-C; `tmp/conv/eval-rca/RCA-FIX-DECISIONS.md` D-A.1 / D-C.1.
Referenced from `config/ontology.yaml` (edge_types header). Do NOT let a code agent edit the answer_key —
this is the deliberate DATA/EVAL reconciliation the user agreed to keep as its own thing.

## 1. `manufactures` → `supplies-component` for Manufacturer→Component  (D-A consequence)
D-A tightens `manufactures` to Manufacturer→**Variant** so every Manufacturer→Component link is
unambiguously `supplies-component` (the sole Mfr→Component edge; this is what lets the chokepoint fire).
The oracle currently uses `manufactures` for two Mfr→Component edges:
- `mfr_casic --manufactures--> comp_ht233` (want confirmed)
- `mfr_23rd_ri --manufactures--> comp_ht233` (want possible)
**Action:** re-lane these two oracle edges to `supplies-component` (or explicitly ratify keeping
`manufactures` for prime-maker→component as a separate tier — but then the ontology needs a tier attribute,
not two colliding edges; D-A chose the former). Verify against all six graded scenarios, not just the hero.

## 2. Id unification  (D-C target)
`config/entities.yaml` now uses the oracle's canonical ids as its `entity_id`s. Eval matches view→oracle by
name+type **today** (the bridge). Target: adopt the registry canonical ids in `answer_key.json` so the
graph, lenses, observables, and oracle share one id namespace — then eval can switch to id-exact and the
bridge retires (D-C). This is the "make the answer_key its own thing" task.

## 3. Materiality / foreign_control grounding  (D-C.1 — the Phase-1 catch)
Phase 1 **removed** the `foreign_control` seeds a registry-authoring pass had added — the corpus never
states a sole-source/foreign-control fact for HT-233 (its maker is graded UNKNOWN, `gap_ht233_maker`), so
seeding it to force a CONFIRMED chokepoint is un-sourced and violates the traceability non-negotiable.
`tmp/conv/EVAL-RCA-corpus-grounding-basing-and-materiality.md` (Item 2) grounds this in verbatim corpus
reads and recommends resting the chokepoint on the **hedged techdata-authority configuration-control**
(d21) + **no-open-substitute chassis** (d24) at **PROBABLE**, hedges preserved — or enriching the corpus
with a plausibly-stated dependency. Same doc, Item 1, does the equivalent reconciliation for the
`based-at` edges (stated equipment@site + derived unit↔site association at probable, owned by RESOLVE/SCORE
— not an INGEST stated-fact). **Action:** DATA+EVAL settle the oracle's expected chokepoint/basing statuses
to what the hedged evidence supports; do not hand-seed to hit the oracle.
