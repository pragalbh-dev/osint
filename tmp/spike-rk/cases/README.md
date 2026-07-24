# RK-SPIKE acceptance cases — how to run them, and what "match" means

Authored from the specification only, by the independent test hand. **No implementation was read** —
not `spike/rk-impl`, not `wt-RK-SPIKE-impl`, not `tmp/spike-rk/proto/**`. Every expectation is
derived from a quoted spec line; the citations are in `RATIONALE.md`.

## Files

| File | What it is |
|---|---|
| `cases.json` | 24 case inputs, in the spike's input contract, verbatim. Nothing but `case_id` + `documents`. |
| `expected.json` | Per case: an `intent` line and an `_assert` list. **Assert-only by design** — anything not asserted is free. Plus three `_invariants` that apply to every case. |
| `RATIONALE.md` | Per case: shape · decision/defect under test · the tempting-but-wrong outcome · the correct outcome · the spec line that makes it correct. Plus the open questions where the spec is silent. |

## Running

```bash
python3 tmp/spike-rk/proto/run.py \
  --cases tmp/spike-rk/cases/cases.json \
  --out   tmp/spike-rk/cases/actual.json
```

Then check `actual.json` against `expected.json` using the semantics below. Cases are independent —
each is a fresh corpus of 1–3 documents; run order does not matter.

## Matching semantics

**Only the asserted paths are compared.** The prototype may emit any additional fields, any extra
`pair_verdicts` rows, any ids it likes. An over-pinned case fails for the wrong reason and teaches
nothing, so unasserted values are deliberately unconstrained.

**Ids are never pinned.** `instance_id` / `referent_id` are the implementation's to choose. Every
selector resolves through *membership* instead.

### Selectors

`<collection>[<filter>](.field)*`

| Form | Resolves to |
|---|---|
| `referent_atoms[doc=d01]` | all referent atoms with `doc_id == "d01"` |
| `referent_atoms[has=d01.m1]` | the referent atom(s) with `doc_id == "d01"` whose `member_local_ids` contains `"m1"` |
| `instances[@d01.m1]` | the instance holding mention `m1` of doc `d01` (see resolution rule) |
| `instances[citizen=formation]` | filter on a literal field value |
| `pair_verdicts[@d01.m1\|@d02.m1]` | the row whose `{a,b}` equals the two resolved instance ids, **order-insensitive** |
| `derived_edges[kind=relocation,drawn=true]` | filter, comma = AND |
| `gaps[about=@d01.m1]`, `gaps[kind=formation-unresolved]` | filter |

**Mention → instance resolution** (`@doc.local`): find the instance whose `member_claim_atoms`
contains an element mentioning both the doc id and the local id as tokens (the contract's own
example spells a claim atom `"d01-m1"`); failing that, follow `member_referent_ids` into
`referent_atoms` and match `doc_id` + `member_local_ids`. Either route is accepted, so no id
*format* is load-bearing.

A projection over a list is **universally quantified** — `referent_atoms[doc=d01].authoritative`
equals `false` means every matching atom is `false`. `count_*` ops apply to the list itself.

### Ops

`equals` · `not_equals` · `in` · `not_in` · `contains` (case-insensitive substring for strings, membership
for lists) · `not_contains` · `present` (exists, non-null, non-empty) · `absent` (missing, null, or empty
list) · `count_equals` · `count_gte` · `count_lte`.

Three purpose-built ops, because they express the load-bearing behaviour and nothing else does:

- **`same_instance: [a, b]`** — a and b are **fused**: either they sit in one instance, or their pair
  row has `verdict == "confirmed"` (the contract defines `confirmed` as "the pair FUSED").
- **`distinct_instance: [a, b]`** — a and b are **not fused**: they sit in different instances **and**
  their pair row's verdict is not `confirmed`.
- **`not_silently_dropped: a`** — the instance holding `a` appears somewhere an analyst would see it:
  as a `derived_edges[].subject`, as a `gaps[].about`, or named in a `gaps[].missing` / `gaps[].sentence`.
  This is the D2 assertion.

`any_of` holds a list of sub-asserts and passes if **any** passes — used only where two different
target-correct mechanisms could legitimately produce the outcome.

### Advisory asserts

An assert with `"advisory": true` is **reported but does not fail the case**. Advisory is used for
exactly three situations, never as hedging:

1. The behaviour the spec requires has **no slot in the I/O contract** (the sourced `count`, the
   licensing quote, the coverage-due date).
2. The spec fixes the *outcome* but not the **vocabulary** (a wall's name, a gap's `kind`).
3. The spec is **genuinely contested or contradictory** — recorded so the run tells us which reading
   the implementation took (`rk-22`).

Every other assert is hard. A case's verdict is: **PASS** if all hard asserts hold, **FAIL** otherwise.

### Unresolved vs mismatched

If a selector resolves to nothing (empty collection, missing field), report the assert as
**UNRESOLVED**, not **MISMATCH**, and count it as a failure. This keeps "the prototype does not model
this layer at all" distinguishable from "the prototype answered wrongly" — the former is a scope
finding, the latter a correctness finding.

### Global invariants

`expected.json._invariants` applies to every case:

- **I1 atom conservation** — every input mention appears in exactly one instance's membership.
  A dropped mention *is* the D2 defect.
- **I2 no fabricated discriminator** — every value in `instances[].discriminators` either occurs in
  the `attrs` of one of that instance's member mentions, or is the literal `"unknown"`.
- **I3 determinism** — two runs on identical input give identical output up to a consistent renaming
  of `instance_id` / `referent_id`.

## Case series worth reading as pairs

Every case has a mirror; a suite that only tests refusal tests timidity. The tightest pairs:

- `rk-01` / `rk-02` — the same sentence at grade E and grade B. One variable: the source grade.
- `rk-10` / `rk-11` / `rk-12` — the same three-mention document, no-contrast → contrast → contrast at
  grade E. One variable per step, so the contrast ceiling is fully isolated from every other mechanism.
- `rk-07` / `rk-08` — decline on a conflicting discriminator vs. do **not** decline on a merely absent one.
- `rk-14` / `rk-15` — a bare designation vs. the `(operator, designation)` composite key.
- `rk-16` / `rk-17` — name-only never fuses; name plus one more signal must.
- `rk-20` / `rk-21` — the fabricated relocation must not be drawn; the earned one must.
