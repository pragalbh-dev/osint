# T11 — a read side for the config layer, and a rail that stops underclaiming

**Branch:** `qa/t11-config-read` (off `qa/live-fixes`, the integrated QA branch) · **not merged, not pushed**
**Owns:** `backend/chanakya/api/routes/config.py`, `backend/chanakya/schemas/api_models.py`,
`frontend/src/components/rail/Rail.tsx`, `frontend/src/api/client.ts`, `frontend/src/api/hooks.ts`
**Also touched (declared):** `frontend/src/api/types.ts` (two additive interfaces + one optional field),
`backend/chanakya/schemas/__init__.py` (one export), `backend/tests/api/test_config.py`.
**Did not touch:** `frontend/src/api/adapters.ts` — **zero changes**. Nor `MergeCard.tsx` / `LiveCard.tsx`
(T10), nor `WatchView.tsx` (see "left undone").

---

## The bug, and why it was the wrong kind of wrong

The left rail read **"Watching 0 — indicators & warning — none fired"**. Three observables *are* armed in
`config/observables.yaml` and *are* evaluated on every rebuild — it is the same machinery `make beat`
fires. The rail said 0 because it derived its count from the **alert feed**: what has *fired*. On a cold
boot nothing has fired, so it printed 0.

The comment in `Rail.tsx` was explicit that it reported the feed "rather than claiming an armed catalogue
it cannot read". That instinct — never assert what you cannot source — is the right one and it is the
house rule. But it inverted: refusing to overclaim produced a confident **underclaim**, and "0" is not a
refusal, it is a number. On a system whose entire pitch is monitoring, "nothing is being monitored" is the
single most damaging false sentence it could print about itself.

The root cause was not the rail. It was that **the API had no way to read the armed set**:
`/config/{section}` was POST-only, and `/view` carries only alerts. The rail was being as honest as its
data allowed.

---

## What I exposed

### `GET /config/{section}` → `{section, version, value}`

* **The mirror of the POST, not a new vocabulary.** Same path, same `_resolve_section` alias table
  (`observable→observables`, `source→sources`, `place→places`, `subject→subjects`,
  `template→templates`), same 404 body listing the available sections. Read and write agree by
  construction rather than by discipline; a test asserts `/config/observable` and `/config/observables`
  return identical bodies.
* **`value` is the stored model dumped verbatim** — no bespoke per-section DTO. The pydantic sections
  already serialise cleanly, and a DTO is the thing that drifts from the write shape the first time a
  section grows a field. Verbatim also means a GET round-trips straight back into a POST.
* **Served from the live `ConfigStore`, never from disk.** This is the hot-config rule: an in-app edit
  must be visible to the next read with no restart. `test_config_get_reflects_a_post_with_no_restart`
  is the test that proves the seam is real — POST a new observable, GET it back in the same process,
  and the version the read reports is the one the write returned.
* **`version`** is the store version at read time — the read-modify-write handle.

### `ConfigWrite.if_version` (optional) → 409 on a stale write

I checked what the POST expects before adding this: it expected **nothing** — no version, no ETag,
last-writer-wins. That makes read-modify-write *possible* but not *safe*, so the handle is worth having;
making it **required** would break every existing caller for a single-analyst demo, so it is **opt-in**.
Pass back the `version` your GET returned and a write against a moved store 409s with
`{expected, current}`; omit it and behaviour is byte-for-byte what it was.

### What I deliberately did **not** do

* **No `/observables` endpoint.** It would have fixed the rail and left the config-editor blocker
  standing. The general read closes both, plus the T6-shaped "the SPA can't read section X" gap.
* **No per-section read models, no field filtering, no pagination.** Sections are small and the store
  is generic; anything else re-introduces the drift the generic route removes.
* **No section withheld from reads — and I checked rather than assumed.** All nine (`ontology`,
  `sources`, `credibility`, `resolution`, `templates`, `subjects`, `observables`, `places`, `entities`)
  are readable. Evidence: `config/*.yaml` greps clean for key/secret/token/password/credential (the only
  hits are `name_token` and prose about name tokens); `ConfigBundle` has no env-sourced field —
  secrets live in `.env` and are read through `chanakya.settings`, which never reaches the config store.
  A withheld section would also be an un-editable section, since editing is read-modify-write. Note for
  whoever hardens this later: **the rule to preserve is "config carries no secrets", not "this endpoint
  is safe today"** — if a section ever gains a credential-shaped field, the fix is to keep it out of
  `ConfigBundle`, not to special-case the route.
* **No auth on the read.** There is none anywhere on this API; adding it here alone would be theatre.
* **No `GET /config` index.** The 404 already lists every available section, which is the same
  information at the moment you need it.

---

## How the rail derives its two numbers

Extracted into `frontend/src/components/rail/watchSummary.ts` — a pure function, so the honesty rules
are unit-testable rather than trapped inside a component (7 vitest tests).

| source | number | where from | at cold boot |
|---|---|---|---|
| **armed** | catalogue size | `GET /config/observables` → live config store | **3** |
| **fired** | firings on this view | `/view.alerts` → `viewToTripwires` | **0** |

* badge = the **armed** count; caption = `"{armed} armed · {fired-state}"`. Armed is repeated in the
  caption on purpose — the whole defect was a number whose meaning was ambiguous.
* fired-state keeps the existing three-way distinction untouched: `"{n} fired"` while any firing is
  un-adjudicated, `"fired · all decided"` once the analyst has dispositioned them all, `"none fired"`
  when there are none.
* **degrade rule** — if the catalogue read fails or returns nothing, `armed` is `null`, *never* `0`. The
  badge shows the fired count when there is one (a real number, correctly labelled) and an **em-dash**
  when there is not, and the caption names the missing half: `"none fired · armed count unavailable"`.
  An empty catalogue that *was* read is a genuine `0 armed` and reads differently. Not-known and
  known-to-be-zero are different statements and the row makes them look different.
* **demo mode is byte-identical** — no live feed at all still means the frozen `TRIPWIRES` constant,
  `3 · armed`.
* **Zustand:** `useArmedObservables()` subscribes to the `mode` primitive only and gets its data from
  TanStack Query; it returns react-query's own cached array, so no fresh reference per render and no
  `useSyncExternalStore` loop (the `ModeToggle.tsx` hazard). Console was clean of React errors in every
  browser run below. The hook refetches every 30 s because the catalogue is **hot** — an observable
  armed in-app must show up without a reload.

---

## Verified in a real browser (`?mode=live`, production build)

Backend on `:8041` / `:8042` (a fresh cold instance for the degraded run), SPA built and served
same-origin. `166 nodes / 84 edges` confirmed on `/health` for both — the baseline. Driver:
`tmp/qa/t11-rail-check.cjs`.

| state | rail says | screenshot |
|---|---|---|
| **cold boot** (nothing fired) | `Watching 3` · *indicators & warning — 3 armed · none fired* | `tmp/qa/t11-rail-cold-boot.png`, `t11-app-cold-boot.png` |
| **after a tripwire fires** — ingested the withheld `d18_rahwali_pass1` + `d19_rahwali_confirm` through the SPA's own "Awaiting ingest" buttons | `Watching 3` · *3 armed · 1 fired* (Review 8→9) | `tmp/qa/t11-rail-fired.png`, `t11-app-fired.png` |
| **catalogue unreadable** (`/config/**` aborted at the network layer, cold server) | `Watching —` · *none fired · armed count unavailable* | `tmp/qa/t11-rail-degraded.png` |
| **demo mode** (no `?mode=live`) | `Watching 3` · *indicators & warning — armed* (unchanged) | `tmp/qa/t11-rail-demo.png` |
| **hot-arm, no restart, no reload** — POSTed a 4th observable by read-modify-write (`if_version` guarded) and left the page alone | `Watching 3` → **`Watching 4`** · *4 armed · none fired* after the 30 s refetch | `tmp/qa/t11-rail-hot-armed.png` |

That last row is the hot-config rule demonstrated end to end in the product, not just in a test: define a
tripwire over HTTP, and the analyst's screen tells the truth about it without anyone touching the process.

---

## Does this clear the config read-modify-write blocker? — **Yes.**

`tmp/conv/FRONTEND-to-API-config-readmodifywrite.md` asked for one of three fixes and named **option 1**
(`GET /config/{section}`) as preferred and sufficient — *"If you add (1), I need nothing else."* That is
what landed, plus the `if_version` guard it did not ask for. Both parked surfaces are unblocked:

* **Credibility rubric** — GET `/config/credibility`, change one `factor_weights` entry, POST the whole
  section back. `test_config_read_modify_write_round_trip_of_one_credibility_weight` walks exactly that
  flow and asserts every other key (`source_class_factors`, `integrity_penalties`, `gates`, `thresholds`,
  `half_lives_days`) is untouched — the clobbering the note feared is now a red test if it ever returns.
* **Define-a-tripwire** — GET `/config/observables`, append the new `ObservableDef`, POST the list back.
  The seeded three survive; `_arm_new_observables` back-scans only the new id and arms it on save.

Neither needs a hardcoded copy of the config in the client, which was the frontend's stated reason for
refusing to wire them. **FRONTEND: this is yours to pick up.**

## Left undone, deliberately (for whoever owns these files)

* **`WatchView.tsx`** carries a now-stale note — *"the armed catalogue has no read endpoint yet"* — and
  still lists only tripwires that have fired. It can now list armed-but-quiet ones, and the rail's `3`
  currently opens a panel showing none of them. I stayed out on file-ownership grounds (T10 is live in
  that directory). It is a small change against `useArmedObservables()`.
* **`useArmedObservables()` is not invalidated on a config write** — nothing in the SPA writes config
  yet, so there is no writer to invalidate from; the 30 s refetch covers the gap meanwhile. Whoever
  wires the two config editors should add a `queryClient.invalidateQueries(['config','observables'])`.

## Baseline

`make test` **852 passed** (843 + 9 new), 6 skipped, 1 xfailed · ruff clean · mypy clean (96 files) ·
`tsc --noEmit` clean · vitest **162** (155 + 7 new; the 134 in `QA-INTEGRATION.md` is stale — measured
155 on `qa/live-fixes` itself). Graph unchanged at 166 / 84.
