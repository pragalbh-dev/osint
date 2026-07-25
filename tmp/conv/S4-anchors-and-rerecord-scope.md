# S4 + RK-DATA — the anchor survey and the re-record's real scope

**Written 2026-07-25.** Two questions answered by probe, ahead of RK-NAMECUT (S4) and the keyed re-record.
Everything below marked VERIFIED was measured by running it, not read off a doc.

---

## 1. Config anchors across a re-key — three files, three different answers

S4 makes every node id a function of claim-atom membership. Three config files carry corpus node ids today.
They do **not** behave alike, and the differences decide what S4 must do.

### `config/entities.yaml` — not a victim; it is the *cause* of stable ids
**VERIFIED:** `resolve/cluster.py:718-736 _preferred()` ranks registry membership first, so any cluster
containing a registry seed adopts that entry's `entity_id` as its node id. Of 169 view nodes, **13 carry
registry ids, 150 carry name-derived `ent:{type}:{name}`, 6 carry bare-name ids.**

So this file is already the *one* mechanism pinning ids against a re-key, and **S4's blast radius is the
other 156 nodes**. → **S4 should exempt registry-elected clusters and not re-key this file at all.** Its
internal `distinct_from:` rows (`:168`, `:183` → `resolve/rconfig.py:449-451`) are entity-id
cross-references: fine if both sides move together, but **a stale one silently no-ops a hard do-not-merge
veto** — and one of them is the PAAD-vs-HQ-9B trap. If any row is re-keyed, rewrite `distinct_from` in the
same pass and assert every target exists.

### `config/observables.yaml` — silent failure, and a phantom that hides it
**This is the flagship tripwire (`watch_instances: [unit_hq9b]`) and the finding is bad enough that it is
being fixed now, separately, on `fix/anchor-resolution-honesty`.**

**VERIFIED by probe** — baseline fires 1 alert (`based-at: site_rawalpindi → site_rahwali`); with the node id
re-keyed: **0 alerts, no exception, nothing logged.** And `observe/observable.py:244` seeds
`reach = set(obs.watch_instances)` from the **raw config strings**, so `resolve_scope` still returns a set
*containing* `unit_hq9b`. **A debugger sees the expected id in scope while the real node is excluded.**

The ladder does not rescue it even with `entities.yaml` untouched: tier 2 needs the registry entry's
`canonical_name`/aliases to match a view node's `name`, and the node's name is `'the PAF HQ-9B fire unit'`
against canonical `'PAF HQ-9B fire-unit (relocation subject)'`. **Rescue-rate over all 14 registry anchors
with every id re-keyed: 9 rescue, 5 do not — `unit_hq9b`, `unit_paad`, `var_hq9p`, `comp_tel_chassis`,
`site_karachi`.** Both flagship-critical anchors are in the failing set. **The ladder's coverage is
accidental** — it works where the elected display name happens to equal a seeded alias — **not designed.**

→ S4 must rewrite `watch_instances` through the redirect map. Independently, the literal seeds and the
missing arm-time check are being closed now.

### `config/subjects.yaml` — same failure, but diagnosed (semi-silent)
`view/lens.py:101-102` resolves anchors and **does** record misses at `:132-134`
(`meta.anchors_resolved` / `anchors_missing` / `anchor_resolution`). **VERIFIED:** re-keying gave
`anchors_missing=['unit_paad']`, `site_rahwali` rescued via `registry_alias`, and the lens quietly shrank
**30→28 nodes / 52→48 edges**. **But nothing reads that meta** — zero consumers across `frontend/` and
`backend/chanakya/api/` outside `lens.py` and its tests. The analyst gets a smaller graph, not a warning.

→ S4 must rewrite the anchors; surfacing `anchors_missing` is in the honesty fix.

---

## 2. The re-record covers `hq9p_primary` only — and my earlier worry was wrong

I had flagged that §10 names no scenario while three exist, and that a primary-only re-record would
desynchronise `hq9p_sandbox` (521 claims). **That concern does not survive contact with the filesystem.**

**VERIFIED:** `git ls-files` returns **68 tracked files for `hq9p_primary`, 32 for `hq9p_chaff`, and 0 for
`hq9p_sandbox`** — `.gitignore:43` ignores the sandbox outright. It exists only in this worktree. Its
`answer_key.json` is **md5-identical to primary's** (`69d826af…`), and **492 of its 521 claims carry
`doc_ref.file` pointing into `hq9p_primary/docs/`** — only 29 cite its own two extra documents. It is a local
byte-copy of primary, not a peer scenario. Nothing reads it: no test, gate, make target, CI job or frontend
loop.

- **`hq9p_primary`** — the whole tracked, graded, boot-loaded corpus. This is the re-record's scope, plus the
  three config files, `answer_key.json`, `SCENARIO_MANIFEST.json`, the golden view and the id-pinned tests.
- **`hq9p_chaff`** — unaffected. No `claims/` dir, empty `ground_truth`, no node-id literals; its docs are
  live-ingested and mint ids under whatever scheme is current.
- **`hq9p_sandbox`** — **delete it or declare it dead; do not re-record it.** After a re-record it becomes a
  stale duplicate that cites primary's *rewritten* documents, and `api/quotes.py:77-80` resolves spans to
  verbatim quotes at request time — so it would **silently mis-quote**.

**One edit §10 needs:** it says `Data: corpus/**` (`:847`) and "re-extract **the corpus**" (`:906`). A glob
and a singular noun, while an unrelated "sandbox" fixture discussion sits at `:575-589`. **Name
`hq9p_primary` explicitly** — that ambiguity is exactly what would make a continuing agent believe two
scenarios are in scope.

### Related, and already disclosed — not a new break
The "evaluators pick a scenario live" promise (`CLAUDE.md:72-73`, `DECISIONS.md:136`) is **already
unimplemented**: `api/state.py:37,122-125,180` reads `CHANAKYA_SCENARIO` once at boot, default
`hq9p_primary`; there is no switch endpoint, no SPA picker, and neither `docker-compose.yml` nor `make run`
sets it. Disclosed at `md/17:128-129` and `md/16:91-92`. A primary-only re-record does not newly break it.
