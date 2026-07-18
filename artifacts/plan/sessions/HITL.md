# Session HITL — Adjudication Service + Decision-Log Writeback + 3 Card Payloads

**Wave 1 · depends F0 only · conflict-free (own dir).**
Read `../00-master-plan.md` §4.7 (the adjudication service + review-queue envelope + the 3 card payloads —
you implement this section), §4.2 (the `DecisionRecord` schema you emit, verbatim; you do **not** redefine
it), §4.8 (the `POST /hitl/{merge|status|alert}` writeback shapes API binds to — you provide the callable),
and §5 gate **G12** (HITL-propagation — the gate your writeback must keep green). This session is the proof
that "override changes downstream state" is *structural*, not a special code path: you only ever **append a
`DecisionRecord`**; `rebuild()` (F0-owned) applies its `effects`. No LLM ever runs in the disposing path.

## Goal

Build the **one cross-cutting adjudication service** every spine stage (and the analyst) calls to escalate
an ambiguous/high-stakes item, and the **writeback** that turns each disposition into an appended
`DecisionRecord`. Because the record's `effects` are applied by the next `rebuild()` and not by any bespoke
per-stage code, propagation *falls out of the event-sourcing architecture*: reject a claim → the node drops
confirmed→probable → the multi-hop answer changes, with zero fan-out logic. Ship the **three ★ card payloads
wired deep** (merge, status-override, alert-disposition) + the **analyst-initiated integrity-flag** caller,
with all eight control points present in the one service as differently-shaped `enqueue` calls.

## Design docs to read first
`spine/05` (the whole doc — HITL as one cross-cutting service; system-proposes/analyst-disposes;
overrides-propagate-not-log; the 8 control points; **recall-biased triage**; **LLM raise-only** in triage) ·
`spine/08` **§3.2** (decision/trace record — the one schema for HITL + learning + audit), **§3.10** (the 8
control points, 3 ★ wired deep vs 5 config/roadmap), **§3.11** (LLM proposer-vs-authority: raise-only in
triage; the **analyst-initiated integrity flag** as a new caller of the same service) · `product/03` **D**
(the review-queue envelope + the three built-deep card payloads — the shape-of-record for the UI) ·
`DECISIONS.md` HITL rows ("HITL is one cross-cutting adjudication service … all 8 … 3 wired deep";
"LLM is proposer, never authority — escalation is raise-only"; "Analyst-initiated integrity flag").

## Scope (build these)

1. **The one service, one signature** (`chanakya/hitl/service.py`) —
   `enqueue(item, context, options, writeback) -> Decision`, then `Decision → writeback → mutate view + emit
   trace`. It builds the review-queue item, applies the deterministic triage gate (item 7), and on
   disposition calls `writeback`. **No LLM, no network, no clock/RNG-dependent branch on the disposing
   path** (keeps G1 true through the API too — the writeback only *appends*).
2. **The reusable review-queue envelope** (`chanakya/hitl/queue.py`, pydantic over F0 schemas) —
   `{type, subject, context{confidence, materiality, novelty}, options, effects, actor, ts}`. `effects` is a
   **downstream state-change preview** (what the graph/answer becomes if you choose X). One envelope; the
   card is the middle (`payload`) specialised per `type`. Field↔`DecisionRecord` (§4.2) map:
   `type→type`, `subject→subject_ref`, `context→context`, `options→options`, `effects→effects`,
   `actor→actor`, `ts→ts`; the chosen `decision` and `stage` are filled at writeback.
3. **Writeback = append a `DecisionRecord`** (`chanakya/hitl/writeback.py`) — one function per card that
   constructs the §4.2 record (correct `type`/`stage`) and calls the F0 store's append. It **never** mutates
   the view directly; the next `rebuild()` reads the decision log and applies `effects`. Structural
   propagation, not a code path. Reversibility is another appended record (a `split`, a re-promote), never an
   edit/delete of the prior one (G3).
4. **Merge card** ★ (`type: merge_adjudication`, `stage: resolution`) — payload = the **two candidate
   entities side-by-side** with comparable attributes; the **match signals with their relative weight**
   (name/attribute · shared-neighbourhood · timeline · source-asserted); the **score** + which **band**
   (auto-merge / needs-you / keep-separate). **Options: accept / reject / split.** Accept/reject grows the
   **alias table** (reversible) as an `effects` payload RESOLVE consumes on the next rebuild. HITL **renders**
   the signals/score/band it is handed; it does **not** compute them (that is RESOLVE — out of scope).
5. **Status-override card** ★ (`type: status_override`, `stage: credibility`) — payload = the claim/node,
   its **current status**, and the **confidence breakdown** (same data as `product/03` C). **Options:
   promote / demote / reject.** A **reject-claim** effect excludes the claim (like a retraction) so the
   assertion loses a supporting independent group; on rebuild the status machine drops the node
   confirmed→probable and the downstream answer changes. This is the **G12** demonstrator.
6. **Alert-disposition card** ★ (`type: alert_disposition`, `stage: alerting`) — payload = the **fired
   tripwire** + **what changed** (`before → after`, e.g. *occupied@Rawalpindi → occupied@Rahwali*).
   **Options: real / noise / needs-more**; the disposition is appended as an effect that **tunes the
   tripwire** (MONITOR consumes it; HITL does not fire or re-evaluate alerts — out of scope).
7. **Recall-biased triage** (`chanakya/hitl/triage.py`) — a **deterministic** escalate-vs-auto gate keyed on
   `context{confidence band, materiality, novelty}`: tune the **precision** of auto-proceed, but **hold the
   recall of escalation ≈ 1.0** (when in doubt, escalate — never silently drop). The **★ marquee items are
   deterministically pinned to the top** of the queue regardless of rank. A **config-versioned NL triage
   rubric** LLM may rank/raise items *inside* the queue — but it is **raise-only, offline, applied to a
   frozen rubric version and replayed** (never recomputed live), and it can **never remove an item nor move
   the escalate-vs-auto boundary** (that gate is deterministic). The disposing path stays LLM-free.
8. **All 8 control points exist in the one service** (`chanakya/hitl/controlpoints.py` — one `enqueue`
   call per point, different payload = the portability flex): credibility-config *(read-only panel now)* ·
   **merge ★** · ontology-extension *(roadmap)* · **confirmed↔probable override ★** · observable-definition
   *(config-authored now)* · **alert-disposition ★** · assessment-review *(roadmap)* · integrity-flag. The
   3 ★ are wired to real writeback + propagation; the other 5 are typed payloads with config/roadmap depth
   (named, not built) — nothing new architecturally, the same `enqueue` with a different payload.
9. **Analyst-initiated integrity flag** (`type: integrity_flag`, `stage: integrity`) — a **new caller of the
   same service**: an analyst flags a source/origin fake by its `primary_origin_id`. Because dedup groups
   claims by `primary_origin_id`, the flag propagates **automatically** to every co-referring claim sharing
   that origin on the next `rebuild()` — no per-claim fan-out. HITL appends the one record; propagation is
   structural.

## Contracts implemented
Master **§4.7** (the adjudication service you *are*), **§4.2** (`DecisionRecord` — emitted verbatim, never
redefined), **§4.8** (`POST /hitl/{merge|status|alert}` — you expose the callable service+writeback; API
wraps it), **§5 G12** (kept green). Card payload shapes follow `product/03` D (shape-of-record; reconcile
field *names* against F0's API/view models). HITL **freezes no shared surface**; if a `DecisionRecord` field
or an `effects` shape must change to make propagation work, **stop and file an F0-amendment PR** (Rule 3) —
do not edit F0's files in this PR.

## Acceptance criteria
> Tests run against **F0's golden fixtures + store + `rebuild()`** (not sibling code). Where a stub stage
> (RESOLVE/SCORE) means HITL cannot verify the *recompute* itself, the test asserts the **decision-log
> state + the `effects` shape** the sibling will consume; full RESOLVE-consumption / SCORE-recompute is
> re-verified end-to-end at EVAL.
- [ ] **G12** — a `status_override` **reject-claim** decision appended via writeback makes the node drop
      **confirmed→probable** on the next `rebuild()` **and** changes a downstream query answer (extend the
      F0-seeded G12 fixture; keep the gate green).
- [ ] A **merge accept** grows the **alias table** — the appended `merge_adjudication` record's `effects`
      carry the same-as + alias pair in the shape RESOLVE reads on the next rebuild; a later **split**
      appends the reversing record (no edit/delete of the prior).
- [ ] **Decision replay is deterministic** — replaying the decision log yields a byte-identical view across
      two runs (G2-style, over the HITL fixtures).
- [ ] An **analyst integrity flag** on a `primary_origin_id` propagates to **all echoes of that origin**
      (every co-referring claim carries the gate/penalty) on the next rebuild — asserted with a fixture that
      has ≥2 co-referring claims sharing one origin.
- [ ] **★ items are pinned** to the top of the queue **regardless of** any LLM rank (feed a hostile rank
      that would bury a ★ item; assert it stays pinned; assert the LLM can neither remove an item nor move
      the escalate-vs-auto boundary).
- [ ] **Gates + hygiene:** G1 (no LLM/network on the disposing path; `chanakya/hitl` must not import
      `anthropic`/`httpx`/`requests` on the writeback path), G3 (append-only — decisions never mutate/delete
      a prior record), G4 (traceability preserved) all green; `ruff`/`mypy`/`pytest` green.

## Owned paths (nothing else)
`chanakya/hitl/**`, `tests/hitl/**`. **Depends on:** F0 (merged). **LLM:** **no** on the disposing path; the
triage-rank rubric LLM is **raise-only, offline/optional**, its output frozen + replayed — never invoked in
`enqueue → decision → writeback → rebuild`.

## Out of scope
The **merge scoring** — signals, `merge_score`, bands, the alias-table *materialization/consumption* (RESOLVE;
HITL only appends the growth *effect*). The **credibility/status recompute** — the status machine that turns
a reject into confirmed→probable on rebuild (SCORE; HITL only appends the effect). The **alert firing /
re-evaluation** (MONITOR; HITL only disposes a fired alert). The **review-queue UI** and any rendering
(frontend — HITL exposes the service + the writeback the API endpoints call). Editing the live
credibility-config or authoring observables (read-only / config-authored for the demo).

## Worktree lifecycle
`git worktree add ../wt-HITL -b feat/hitl` → implement inside owned paths only → PR `[HITL]` → **you review &
merge** → `git worktree remove ../wt-HITL`. Rebase onto `main` on any sibling
merge (always clean given disjoint ownership); the agent never self-merges.
