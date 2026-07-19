# RESOLVE → DATA-C / EVAL: the customs shells stay unresolved (by design), and `import_2021` is a naming mismatch

**From:** Phase-3 RESOLVE session (`fix/phase3-resolve`). **Date:** 2026-07-19.
**Why you're getting this:** two things surfaced during the RES-1 endpoint-linking build that are *not*
RESOLVE's to fix, and one of them is a **correction to a handoff line that would have caused a fabrication**.

---

## 1. Correction — `PHASE2-VERIFY-DELTA-AND-HANDOFF.md` is wrong about the shells

That handoff says (Phase-3 inheritance section):

> "Supply-chain edges now exist but their endpoints are `trading_org` shells (customs consignee/shipper).
> Endpoint-linking (RES-1) + `entities.yaml` consumption **must resolve shell→real entity** so the oracle's
> `import_2021 --exported-by--> mfr_casic` / `--imported-by--> unit_paad` form."

**That instruction is incorrect and was not followed.** It contradicts the scenario design, recorded in
`tmp/conv/eval-rca/phase1-entity-registry-draft.md` §4:

> "**Front-company / shell consignee cluster from d05** ("ORIENT ELECTRO TRADING (PVT) LTD" / "ORIENT
> ELECTRONIC TRADING CO", "SINO-GALAXY IMP/EXP CO. LTD" / …) — **deliberately unresolved-to-any-subject-entity
> per the scenario's D7 design** (civil-vs-military contradiction, relational not string resolution).
> **No oracle id exists or should be invented for these.**"

Corroborating evidence from the build: there is **no corpus signal** linking SINO-GALAXY→CASIC or
ORIENT→PAAD (no alias, no `same-as` assertion, no shared graph neighbour), and `trading_org`→`manufacturer`
is type-incompatible anyway. Forcing the link would have breached the "never force-link a mention to the
nearest name" guard and asserted an attribution **the corpus never states** — i.e. exactly the fabricated-
assessment failure the project treats as disqualifying.

**Resolution:** the shells now resolve to honest, typed `trading_org` nodes and stop there. That is the
correct behaviour and the D7 trap remains intact (the analyst is *supposed* to be unable to close that link
from open sources without relational evidence). **Please strike or amend that line** in the Phase-2 handoff
so the next reader doesn't act on it.

---

## 2. `import_2021` is still `[MISSING]` — but it is a naming/id mismatch, not a resolution failure

The oracle node is:

| field | value |
|---|---|
| `id` | `import_2021` |
| `type` | `contract_import_event` |
| `name` | `China->Pakistan HQ-9/P transfer` |

The corpus's actual customs events are named `KPQA-HC-2020-*`. `backend/eval/report.py` matches oracle
nodes to view nodes by **name/type overlap**, so `import_2021` cannot match *regardless of how well RESOLVE
performs* — the strings share nothing. RESOLVE does now mint typed `contract_import_event` nodes from the
customs transforms; they simply don't carry the oracle's editorial name.

**This is the already-open id-unification item** (`PHASE1-DATAC-EVAL-answer_key-reconciliation.md`), not a
Phase-3 defect. **Your call, DATA-C/EVAL** — roughly three options:
1. Give the oracle's `import_2021` an alias/`aka` list containing the corpus event designators
   (`KPQA-HC-2020-*`) so name-overlap matching can bind it. *(Least invasive; mirrors how aliases work
   elsewhere.)*
2. Rename the oracle node to the corpus designator and keep "China→Pakistan HQ-9/P transfer" as a
   description rather than the match key.
3. Match `contract_import_event` nodes in `report.py` on a structural key (participants + period) instead of
   name overlap, since an event's "name" is editorial rather than corpus-attested.

Option 1 or 3 look right to me; 3 is the more general fix if other event-type nodes have the same problem —
worth checking before choosing. **Do not** "fix" this by having RESOLVE rename nodes to oracle strings; that
would make the graph fit the answer key rather than the evidence.

---

## 3. Related (already filed separately)

Upstream mis-laned `variant→country` `exported-by`/`imported-by` edges are minting a handful of wrong-typed
artifact nodes (`ent:manufacturer:China`, `ent:unit:Pakistan`, …). RESOLVE deliberately did **not**
special-case them — that would hide a real ontology/extraction defect. Written up for INGEST at
`tmp/conv/RESOLVE-to-INGEST-mislaned-edge-endpoints.md`.
