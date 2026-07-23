# Data-refresh calibrations — handoff for the corpus/answer-key regeneration pass

**Purpose.** The resolution redesign (`10-*`, `11-*`) is built *target-first*: mechanisms ship at full
strength with corpus-independent unit tests, and the synthetic corpus (`corpus/scenarios/hq9p_primary`,
`answer_key.json`) — which is **regenerable demo data**, not ground truth — is expected to bend to the
design. This ledger is the running list the data pass consumes. It has two kinds of entry:

- **§A Stale expectations** — a target-correct change that legitimately alters the frozen partition /
  answer-key, so the corresponding expectation must be regenerated. (The redesign never edits the
  fixtures/answer-key itself; it records the change here.)
- **§B Coverage gaps** — capabilities built + unit-tested but which the *current* corpus doesn't exercise
  (they came out byte-inert), so the data pass should add cases that make them live and demonstrable.

Each stage's real behavior is pinned by corpus-independent unit tests regardless of this ledger; nothing
here gates correctness — it's about making the demo corpus exercise the new machinery.

---

## §A — Stale expectations (regenerate these)

**None yet.** Every stage through 3B-ii verified **byte-identical** on `hq9p_primary`
(`same_as` / `candidates` / `distinct_from` / `entity_canonical` unchanged; the golden view JSON
unchanged). The new machinery is additive and, on the current corpus, dormant — so no frozen expectation
has moved. This section will populate when a partition-moving stage (e.g. cluster-level 3B-iii, or 3C's
staged/relational reordering) actually changes the resolved graph.

---

## §B — Coverage gaps (add cases so these go live)

The current corpus is single-subject and sparse; several target mechanisms have nothing to bite on. To
*demonstrate* them (not to make them correct — the unit tests already do that), the data pass should add:

1. **Attribute-role critical wall (1A / 3A-i).** No `variant` states `operator_branch` (the one wired
   critical attribute), so the country/branch wall fires on zero pairs. *Add:* a variant (or two) that
   STATE `operator_branch` with a genuine cross-branch conflict (e.g. a PLA-operated HQ-9 vs the
   Pakistan-operated export line stated as distinct branches), so the declarative critical wall is
   exercised on real data. Note the **value-normalization** prerequisite recorded in `config/resolution.yaml`:
   `unit.service_branch` / `trading_org.origin_country` are natural walls but the corpus states them
   unnormalised (`PAF` vs `Pakistan Air Force`; `CHINA` vs `China`) — a value-normalization step is needed
   before those can be promoted to `critical` without shattering legitimate merges.

2. **Credibility floor on the critical wall (3A-i).** Once (1) exists, add the same critical conflict
   asserted (a) by a source graded at/above `critical_veto_min_grade` (C) — must WALL — and (b) only by a
   below-floor source (grade D/E) — must RAISE to HITL, not wall. This demonstrates D5 take-care (a): a
   flaky low-grade source can't shatter a well-supported merge.

3. **Bridge-across-a-wall alarm (3A-ii).** No straddling pair currently scores in the merge band across a
   trap. *Add:* a mention/pair with real corroboration (name + shared-neighbourhood, or a shared id) that
   would fuse two clusters held apart by a `distinct_from` wall (e.g. something that looks like one entity
   yet bridges the HQ-9/P vs HQ-9BE trap). It must surface as a `probable` candidate with the
   "bridge across a wall" reason and never merge — the D9 analyst alarm.

4. **Time-aware conflict / perishable succession (3B-ii).** No attribute is declared `perishable: true`,
   so the update-vs-contradiction waiver never fires. *Add:* (a) a taxonomy decision — declare which
   attributes are perishable (a unit's posture / readiness / status; a variant's deployment status), and
   (b) a claim series exercising both shapes: one attribute asserted with different values at *distinct*
   times (a clean `ordered` succession → must NOT count as a conflict / must not wall or penalize), and
   one with different values at the *same* time (a `contradiction` → still a conflict). This makes the
   "an update is not a contradiction" behavior visible end-to-end.

5. **Trajectory-aware support + perishable-only confirmation cap (3B-iii-A).** Attribute *agreement* now
   raises identity scores, and a would-be-confirm resting SOLELY on a perishable trajectory caps to
   `probable`. Dormant on the corpus (agreement crosses no band boundary for any primary pair; no
   `perishable:true` attribute exists). Full recipe to make it live + demonstrable (from a sandbox
   exercise that was then removed): for a chosen perishable attribute (e.g. `unit.readiness_state` /
   `alert_posture` — a unit's transient posture): **(a)** declare it
   `attribute_roles.unit.<attr>: {role: supporting, perishable: true}`; **(b)** declare a durable
   counterpart (e.g. `unit.oob_designation` as a non-perishable attr or a hard-id) so the
   confirm-vs-cap split is exercisable; **(c)** a low `auto_merge_by_type.unit` floor (~0.35) so a
   perishable-agreement pair can reach the auto band at all — at the 0.85 global floor it tops out at 0.45
   and is never a would-be-confirm; **(d)** *the key finding* — the perishable attribute must ALSO be a
   **blocking key** (a `hard_id_fields.categorical` entry, or the two mentions must share a name token),
   because a perishable-only pair is only compared (hence only cappable) if blocking generates it as a
   candidate. So the cap is meaningful precisely for pairs that block together yet share only a transient
   state.

---

*Maintained by the redesign work (branch `design/resolution-redesign`). Append new entries as later stages
land; move an item from §B to §A if it starts moving the frozen partition.*
