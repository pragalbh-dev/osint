# Session RK-LAYER (S2) — layer typing, endpoint materialization, presence/formation, basing-as-a-rebuild-edge

**Wave 2 · depends on RK-ATOMS (S1, integrated at 707b974) · offline.**
Thin by design. The spec is `../01-replumb-implementation-plan.md` **§7 RK-LAYER**; contracts **A2/A3/A4**
(§4); gates **G15** (amended, §5a) and **G17** (extended). The *why* is
`../../spine/13-type-instance-and-identity-replumb.md` §3a (the two citizens), §5 (split → materialize → bind),
decisions **D-13.3/D-13.5/D-13.6/D-13.13/D-13.14**.

**Read the prior stages' outputs — load-bearing here:**
`../../../tmp/conv/rk-spike-code-facts.md` (verified code baseline — **overrides any doc**) ·
`../../../tmp/conv/rk-spike-verified-defects.md` (**D1, D2, D12** are this stage's business) ·
`../../../tmp/conv/rk-spike-DECISIONS.md` (**C1/C2**) · `../../../tmp/conv/rk-spike-REVIEW-VERDICT.md` ·
`PROGRESS.md`'s RK-ATOMS handoff (four spec gaps S1 found — **#3 says `TypeDef.attrs` has no production
consumer yet, so S2 is its first**).

## THE INVARIANT FLIPS — read this before anything else

S1's headline was *zero behavioural change*. **S2's is not.** This stage changes what the graph contains, so:

- **Flag OFF ⇒ byte-identical to S1.** Golden md5 `bb6f16a516c31eb0846494b62271a601`. **Two different
  real-corpus surfaces exist and BOTH are valid — label which you mean** (resolved 2026-07-25 after the test
  hand measured a different number than the orchestrator; neither was wrong):
  | surface | measurement | what it is |
  |---|---|---|
  | **booted app** | **160 nodes / 73 edges / 18 gaps / 450 claims**, hash `22d668a3…dac3a9` | what the running system serves — and it **deliberately withholds `d18_rahwali_pass1` + `d19_rahwali_confirm`** from the boot seed, to be ingested live for the demo |
  | **full scenario via the test harness** | **169 nodes / 80 edges / 71 events / 20 gaps** | every claim, nothing withheld |
  **Use the full-scenario harness surface for S2's flag-off test.** The reason is load-bearing: the two
  withheld documents are *exactly the flagship relocation pair*, so a flag-off assertion measured on the
  **booted** view is **blind to the relocation/supersede surface S2 most changes** (items 5–7). The booted
  number stays useful as an integration check, not as the gate.
- **Flag ON ⇒ the graph MUST change.** An unchanged graph with the flag on means the stage did nothing (plan
  §5a-bis). Do not report "byte-identical" as success.
- **F8 (load-bearing):** S2 lands *before* the coref mint grain (S3), so instances fragment **per-mention**.
  That is **known, expected, and transient**. **Fragmentation metrics are meaningless until S3 and must NEVER
  be "fixed" by loosening merge thresholds** — they would be far too loose once clustering arrives.

## Scope

1. **Layer tags (A2).** A `layer` (design | instance) on every node-type **and** every attribute entry in
   `config/ontology.yaml` — S1 migrated the file to structured entries, so this **adds one key per entry**,
   nothing is restructured (81 attribute entries, 13 node types). Add the layer accessor in `ontology.py`
   beside `refines`/`identity`. Keep the seam: the ontology entry carries what is **ontological** (`layer`,
   D-13.3's dual-attribute split); identity semantics (`role`, `perishable`) stay in `config/resolution.yaml`.
   **Per C6: `perishable` is per *(type, attribute)*** — geography is perishable for a *formation*,
   constitutive for a *presence*, identifying for a *place*.
2. **Straddle split + endpoint materialization (A4)** in `view/pipeline.py`: design facts → the shared design
   node; instance facts → an instance node; a mention carrying both splits into **two linked nodes**. An
   instance-layer edge whose mention named only the design **materializes a provisional presence**. The split
   trigger is an *instance-layer attribute on a design-layer node* — that mismatch is the signal the extractor
   lumped two things together.
3. **Presence & formation citizens (A3).** The two instance kinds. `count` is a **sourced attribute**, default
   unknown, **never** "= how many reports merged" (k reports ≠ k launchers). A bare sighting **never** forces a
   formation.
4. **Basing as a pure rebuild-derived edge (A4/D-13.6) — DELETED, not relocated.** The offline pass in
   `ingest/basing.py` that **mints** a `kind='inference'` `ClaimRecord` and **appends** it is **deleted**. In
   its place `rebuild()` materializes a derived-layer `based-at` **edge** each rebuild, **citing its two premise
   claim-atoms** (the `observed-at` claim + the `inducted-into` claim) for one-click provenance — with **no
   mint and no append inside rebuild**. Consequently the `__basing.json` derived bundles **cease to exist**;
   the seed loader glob and the `pending.py` references that ride them drop with the pass.
5. **Ontology additions this stage owns** (S2 owns `config/ontology.yaml`; no later stage does):
   - **`operated-by`** — G18 names it and **the predicate does not exist**. Add it, or G18 tests half of itself.
   - **D12's `contract_import_event` ↔ `trading_org` edge** — the customs spine (event ↔ consignee ↔ shipper) is
     currently **unrepresentable** while `imported-by → unit` (which no such document states) is easy. **A schema
     that makes the sourced relation inexpressible and the unsourced one easy pressures extraction toward
     fabrication.** Re-examine whether `imported-by → unit` should require a stated unit.
   - **`based-at`'s supersede `instance_key` tagged by `site_type`** (R1.3 / C1's second consumer) — a unit at a
     garrison *and* a forward site is **two concurrent valid basings, not a relocation**. **State the absent
     `site_type` default and fail safe:** `unknown` ⇒ same bucket (wall fires) or ⇒ raise; **never** ⇒
     de-conflicted, because the evasion direction is over-merge. The ontology currently rests unit-only keying
     on "correct while the corpus has no such simultaneous pair" — forbidden as a design input (#1).
   - **Carry forward the relocation/relational mitigation** (`co_instances`, `resolve/scoring.py:337-350`): a
     dated relationship to the same neighbour at two different times is **not** the same relationship. A naive
     `site_type` re-key changes the `edge_instance` shape and would **silently drop** this, so a confirmed
     relocation would manufacture relational evidence that origin ≡ destination. Gate-fixture it.
6. **The D2 clause — no silent formation pick (R2.1).** Today `formations[:max_units]` discards a second
   candidate formation **recording nothing**, while every other rejection path records a reason — an
   order-of-battle undercount with **no merge involved**, invisible to both G15 and G16. The replacement must
   produce **two attributions, or one plus an explicitly named gap. Never a silent pick.**
7. **R1.4 — the supersede must not remove the analyst over an identity we did not earn.** `promote_supersessions`
   currently promotes, pops the pair out of the analyst's queue ("adjudicated by the machine"), draws the edge,
   **and deletes the retired edge's Known Gap** — turning an honest `insufficient` into `stale`. Machine
   promotion is legitimate **only** over an identity the system actually earned.

## Gates

- **G15 (amended)** — keep the existing clause as a regression guard (it passes *vacuously* today: the pass
  already skips when no formation link exists), and **add the clause that bites**: an ambiguous or truncated
  formation attribution **must produce a named gap**.
- **G17 (extended)** — **no code path under `rebuild()` calls a claim mint or `store.append`**. The fixture must
  be **non-vacuous**: include an `observed-at` + `inducted-into` premise pair so the derived-basing branch
  actually executes, or use an input-independent static call-graph scan of rebuild-reachable modules.
- **G1/G2 unchanged** — basing stays pure; two rebuilds byte-identical; no LLM/network/clock/RNG under rebuild.

## Owned paths

`config/ontology.yaml` · `ontology.py` · `schemas/config_models.py` · `view/pipeline.py` ·
`resolve/__init__.py` (endpoint-layer typing only — contended, see §3) · `ingest/basing.py` ·
`config/credibility.yaml` · `credibility/supersession.py` · `tests/view/**` ·
`tests/gates/test_g15_*`, `test_g17_*`.

## Acceptance

- [ ] A straddling mention splits into linked design + instance nodes.
- [ ] An `observed-at` materializes a **presence**; a **stated** `based-at` binds a formation directly; a
      **derived** one is a rebuild-materialized edge citing its two premise claim-atoms, **minting nothing**.
- [ ] Two candidate formations ⇒ two attributions or one + a **named gap** (never silent).
- [ ] `layer` populated on all 13 node types + 81 attribute entries; accessor reads it.
- [ ] `operated-by` and the event↔trading_org edge exist.
- [ ] `based-at`'s supersede key is `site_type`-tagged with a stated, fail-safe absent default.
- [ ] G15 (both clauses), G17 (extended, non-vacuous), G1/G2 green.
- [ ] **Flag OFF ⇒ byte-identical to S1. Flag ON ⇒ the graph changes** (report the diff and explain each
      delta as target-correct — predict-then-verify, working-principles #4).

## Out of scope

The coref mint grain (S3) · the caps/walls/ladder (S3) · cutting the name-key (S4) · the corpus regen (RK-DATA).
**Do not attempt to fix per-mention fragmentation** — that is F8 and S3 owns it.
