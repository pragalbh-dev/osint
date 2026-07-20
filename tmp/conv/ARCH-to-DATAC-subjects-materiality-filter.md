# ARCH → DATA-C: delete two no-op keys from `config/subjects.yaml` materiality_filter

**From:** ARCH (Phase-4 AR-3, decision D-P4.9)
**To:** DATA-C (owns `config/subjects.yaml`)
**Do not self-fix — this is a frozen-config edit ARCH must not make unilaterally.**

## What to change

In `config/subjects.yaml`, subject `lens-hq9p-pk`, block `materiality_filter`, **delete these two keys**:

1. **`exclude_off_subject: true`** — this label exists **only** in `answer_key.json` (the grading
   oracle). Implementing it in the runtime filter would wire the oracle into production — teaching to the
   test. Per D-P4.9 it is *deleted, not implemented*. Real off-subject/chaff protection is already the
   hop-bound-from-resolved-anchor **plus** `node_types_allow` (both now implemented in
   `view/lens.py::_passes_materiality`).

2. **`materiality_attrs: [...]`** — descriptive prose, not a predicate. Its own comment says it lists
   "what `query_graph` filters on"; it never had an implementation path in the lens filter. (It also lists
   `status`, which lives on `NodeView`, not `MaterialityAttrs` — the tell it was never a real schema.)

**Keep** `node_types_allow` and `never_drop_indeterminate` — both are now consumed by the code.

## Why now

Until Phase-4, `_passes_materiality` read only `min_chokepoint_count` / `chokepoint_status_in` (neither
declared in the shipped block) so the filter was a **total no-op — 100% pass, always**. AR-3 implements
`node_types_allow` + an explicit `never_drop_indeterminate`. Those two remaining keys have no consumer and
would ship as silent no-ops, so they should go rather than lull a reader into thinking they filter.

A **non-raising** CI drift guard now exists (`backend/tests/gates/test_g_materiality_filter_keys.py`): it
asserts every shipped `materiality_filter` key is one the code consumes. The two keys above are currently
whitelisted in that test's `_PENDING_REMOVAL` set so it stays green. **Once you delete them from
subjects.yaml, also delete them from `_PENDING_REMOVAL`** so the guard tightens (a future re-add of an
unrecognised key then fails CI). No raising validator was added — config is `extra="allow"` by design, so
hot-config writes are unaffected.

## Note on `never_drop_indeterminate`

The implemented semantics: a node whose materiality signal is UNKNOWN **and** a node whose *type* is
`unknown` (RESOLVE couldn't type it) are both kept when `never_drop_indeterminate: true` (the default).
This is what keeps the material-but-untyped `HT-233 radar` node in the demo lens (23 nodes / 34 edges
unchanged). If you ever want strict type filtering, set it false — but note it will drop that node.
