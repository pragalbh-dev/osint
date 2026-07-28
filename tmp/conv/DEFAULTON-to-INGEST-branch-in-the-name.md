# For INGEST — a unit's service branch is stated only inside its NAME, so no wall can test it

**From: DEFAULTON-impl (branch `defaulton/rk-impl`). One extraction item; no action needed in RESOLVE.**

## What was measured

On the booted `hq9p_primary` corpus the pair

* `ent:unit:Pakistan Army Air Defence (PAAD) unit`  ↔  `unit_hq9b` (the PAF formation)

reaches the analyst's queue as a candidate merge. It cannot fuse (the co-location cap withholds it at
`probable` and it reaches the queue with that reason), so nothing is fabricated — but the rail that *should*
be the one refusing it, the hard critical-attribute wall on `unit.service_branch`, is silent.

## Why

The wall requires the attribute **stated on both sides** — absence is never a conflict, which is right. The
PAAD mention states **no attributes at all**: its service branch is in its *name* ("Pakistan **Army** Air
Defence"), and nothing reads a branch out of a name.

I checked whether the resolver could recover it from the cluster instead (a fragment inheriting the branch a
sibling mention states) and **it cannot help here**: the PAAD mention is a singleton, so its cluster states
nothing either. Where a sibling *does* state the branch, the wall's transitivity already refuses the union in
both phases — verified on a fixture whose pair reaches the auto band with no branch stated on either side and
still does not fuse. So this is an extraction gap, not a resolution gap, and the cluster-level rail I had
written for it was deleted as redundant machinery.

## TO CLOSE (INGEST)

Have the unit extractor set `service_branch` when the branch is present in the surface name — "Pakistan Army
Air Defence (PAAD) unit" → `service_branch: Pakistan Army`; "PAF air defense units" → `PAF`. The
`value_normalization` classes for `service_branch` already fold both spellings, so a stated value walls
immediately and correctly. Nothing else needs to change: the wall, its credibility floor and its transitivity
are all live and exercised.

Until then the honest state is what ships: the pair is refused, queued, and carries its reason.
