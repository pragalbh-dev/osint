# BAKEOFF → GOLD hand: `coref_binding` has no positive substrate, and one field carries two meanings

**From:** the RK-BAKEOFF scorer repair (2026-07-26). **Nothing in the gold was edited.** Everything below
was measured offline against the recorded runs under `tmp/rk-bakeoff/run/`, with zero API calls.

The scorer has been fixed so it no longer credits the harm. Two things remain that only the gold owner
can decide, and neither blocks anything today except the verdict — which is the honest outcome.

---

## 1. `coref_cluster` carries two opposite meanings, and only `coref_registry` says which

On most rows `coref_cluster` means "these mentions are one referent". On the rows whose registry entry is
`ANTI_COREF` or `AMBIGUOUS` it means the exact opposite — "these must be held APART". Both live in the
**positive `claims`** array, so a scorer reading the label alone treats a trap as a licensed identity.

Measured consequence before the fix: the only two clusters carrying more than one entity-form claim are

| cluster | licensing_category | entity claims |
|---|---|---|
| `d05-C4-events` | `ANTI_COREF (distinct stated identifiers)` | `d05-r01`, `d05-r02`, `d05-r03` |
| `d19-C4-othersites` | `ANTI_COREF (stated enumeration)` | `d19-r14`, `d19-r15` |

…and **both are anti-coreference traps**. A system that merged both scored **+0.273 (opus) / +0.280
(gemini)** on `coref_binding`, a criterion weighted 5.0 — about **29×** the composite gap (0.0095) that
produced the NO_MEASURED_DIFFERENCE verdict. The instrument paid nearly double for the over-merge.

**Scorer-side fix (done, not yours):** `eval/extraction/gold.py` now loads `coref_registry` and classifies
each cluster as licensed / anti-coref from its own `licensing_category`, `referent_type` and tag; a cluster
the gold does not license is expanded into per-claim singletons before B-cubed, so holding the mentions
apart is correct and binding them costs precision. An unregistered tag reads as **unlicensed** (fail-safe),
and `coref_channel.require_gold_labels` now refuses up front if the gold carries labels but no registry, or
uses a tag the registry does not declare.

**What is yours to decide.** The scorer inferred the licensing decision from prose fields. That works
today (it classifies all 32 clusters correctly, including the `UNAMBIGUOUS_ANAPHOR` / `AMBIGUOUS` substring
trap) but it is inference over free text. **A single explicit boolean per registry entry — e.g.
`"licenses_binding": true|false`, or reuse of the existing negative-gold vocabulary
`scoring_role: penalise_binding` — would make it a declaration instead.** The gold's own adapter already
declares exactly this semantics for the `anti_coref` bucket; the positive-side clusters are the ones with
no machine-readable equivalent.

Separately: consider whether the two `ANTI_COREF` clusters' rows belong in `claims` at all, or whether the
cluster tag on them should be namespaced so no consumer can mistake it for an identity label. That is a
placement question, and it is yours.

---

## 2. After the fix, `coref_binding` has an EMPTY positive denominator — it is UNMEASURED, and it blocks

This is the part that needs gold work to lift, and it is filed as a request, not a complaint.

The gold clusters **mentions**. The system indexes **claims**. `chanakya/ingest/coref.py` stamps
`referent_id` onto **entity-form claims only**, by explicit design — a relationship claim names two
mentions and has no single referent. Therefore:

* 36 of the 51 cluster-tagged gold rows are `triple`- or `event`-form and are **structurally unscoreable**;
* of the entity-form rows, the only two clusters with 2+ of them are the anti-coref traps above;
* so once traps stop being credited, **every remaining licensed cluster holds exactly one scoreable claim**,
  and B-cubed over singletons is **1.000 by construction for every candidate, whatever it did**.

The scorer now reports `UNMEASURED` with that reason rather than printing the 1.000. Because
`coref_binding` is in `required_metrics`, the verdict is `INSUFFICIENT_CRITERIA` — no winner. That is the
correct posture (it is this project's own "insufficient evidence to assess" rule turned on its own
instrument) and it is deliberately **not** being papered over by re-weighting the criterion.

**What would lift it:** at least one licensed identity cluster containing **two or more `ENTITY`-form
claims** — i.e. the same referent labeled as an entity claim at two of its surfaces. Today the gold labels
one entity row per cluster and expresses the rest of the chain as triples. Examples that already have the
mentions and just lack a second entity row: `d02-C1-system` (7 mentions, 1 entity claim), `d17b-C1-site`
(5 mentions, 1 entity claim), `d19-C2-presence` (4 mentions, 0 entity claims), `d05-C2-shipper`
(5 mentions, 1 entity claim).

Roughly two or three clusters with a second entity-form row would give the top-weighted criterion a real
denominator. Fewer than that and it stays a coin-flip.

---

## 3. Smaller, reported not requested

* `kind_tagging` is `UNMEASURED` on every run — the slice labels no `kind`. That is the adapter's own
  SEMANTIC CALL S10 working as intended; noted only so nobody reads the blank as a scorer bug.
* `surface_precision`: the gold curates 65 claims; the runs emit 150–210 each, and **94.8% / 97.9%** of the
  emissions charged as false positives are stated by the document they cite under the harness's own
  grounding test. The scorer now measures and prints that alongside the number, and `surface_f1` /
  `surface_precision` carry no composite weight. **No exclusion was invented for them** — excusing an
  unlabeled-but-grounded emission would assume the gold is incomplete and drive precision toward 1.0, which
  is tuning to the benchmark. If gold coverage is ever widened, that is where it would pay.
