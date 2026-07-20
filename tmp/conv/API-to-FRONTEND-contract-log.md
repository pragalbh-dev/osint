# API ⇄ FRONTEND — contract change log

**Purpose.** The frontend builds against the **F0-frozen contract** (`backend/chanakya/schemas/` —
`api_models.py` + `view.py`; endpoints per master §4.8). That contract is authoritative **in code**, and
the live OpenAPI spec the API serves (`GET /openapi.json`, browsable at `/docs`) is generated directly
from those same shapes — so the frontend should generate its types from the live spec and cannot drift.

**How to use this file.** The API session appends an entry here **every time it locks or changes a
contract** the frontend consumes: what changed, the decision + why, and a code reference. The frontend
agent watches this file and reconciles. Additive/optional changes need no frontend change to keep working
(fields are just newly available); breaking changes are called out explicitly with a **BREAKING** tag.

Newest entries on top.

---

## 2026-07-20 · new `GET /pending` + `GET /pending/{doc_id}` (additive, non-breaking)

**Endpoints:** `GET /pending`, `GET /pending/{doc_id}` (new; read-only, keyless, offline).

**Change:** the boot seed can now deliberately **withhold** documents (`config/sources.yaml` →
`SourcesConfig.withheld_from_seed`, env override `CHANAKYA_SEED_WITHHOLD`). These two endpoints expose
that withheld set and hand out the claim bundles that release it:

* `GET /pending` → `{scenario, documents: [{doc_id, source_type, citation_url, bundles[], claim_count,
  available, ingested}]}`. `ingested` is read off the live evidence log, not a client guess.
* `GET /pending/{doc_id}` → `{doc_id, bundles[], bundle: [ClaimRecord dicts]}` — post straight back as
  `POST /ingest {"bundle": …}`. 404 for any doc not on the declared withheld list.

**Why:** the relocation tripwire's whole claim is that an analyst is warned when evidence **arrives** —
undemonstrable if the evidence is in the graph at boot. Withholding `d18_rahwali_pass1` +
`d19_rahwali_confirm` makes the reviewer's own click the arrival. The endpoints exist because the
prebuilt image gives a reviewer no local files to drag into the drop zone.

**Impact on frontend:** **additive.** `LiveIngest` gained an "Awaiting ingest" list that renders
`GET /pending` and posts `GET /pending/{doc_id}` through the existing `ingestLive` → `POST /ingest` lane
(no second ingest path). Types: `PendingDocument` / `PendingResponse` / `PendingBundle` in
`frontend/src/api/types.ts`; `api.pending()` / `api.pendingBundle()` in `client.ts`. `/pending` added to
the Vite dev proxy list. A deployment that withholds nothing returns an empty `documents` and the panel
renders nothing — no frontend change needed to keep working.

**Decision (principle → choice → alternative rejected):** *config-driven & extensible, not hardcoded* +
*keep the demo deterministic* → **declare the withheld set in `config/sources.yaml`** so it is auditable
in the same file that registers the sources, with an env escape hatch. Rejected: (a) env-var-only — the
withholding would be invisible to anyone reading the repo; (b) deleting the bundles from the seed
directory — that destroys the frozen baseline and breaks `make beat`. Holding a doc back also holds back
its derived `__basing` bundle, reusing `ingest.seed.bundle_belongs_to_doc` (EVAL's copy deleted, now one
definition shared by the boot seed and the harness).

**Refs:** `backend/chanakya/api/routes/pending.py`; `backend/chanakya/api/state.py`
(`resolve_withheld_docs`, `seed_evidence_keyless(withheld_docs=)`); `backend/chanakya/ingest/seed.py`
(`bundle_belongs_to_doc`, `bundles_for_doc`, `seed_store_from_bundles(exclude_docs=)`);
`backend/tests/api/test_withheld_seed.py`. Reviewer walkthrough: `tmp/conv/REVIEWER-DEMO-INGEST.md`.

---## 2026-07-19 · `IngestRequest` gains `source_type` (additive, non-breaking)

**Endpoint:** `POST /ingest`.

**Change:** `IngestRequest` (in `backend/chanakya/schemas/api_models.py`) gains an optional field
**`source_type: str | None = None`**.

**Why:** the **keyed** live-extraction path (raw doc → extract → append) needs the source's credibility
class to route extraction and score the resulting claims — INGEST's `ingest_document(source_type=…)`
requires it. The **keyless** bundle path ignores it (the bundle already carries per-claim provenance).

**Impact on frontend:** **non-breaking, additive.** Only relevant to the keyed raw-doc form: when you POST
`raw_text`, also send `source_id` + `source_type` (one of the `sources.yaml` `source_type` vocabulary
values). Bundle uploads are unaffected.

**Also note (behaviour, not a shape change):** the keyed raw-doc path is **guarded** by the server env
`CHANAKYA_ENABLE_EXTRACTION` (default **off**) so a public deployment doesn't burn model quota per visitor.
When off, a raw-doc POST returns **403** steering to the keyless `bundle` path; enabled-but-no-key → **400**.
The keyless bundle path is always available. `doc_path` is rejected (a CLI/SHIP concern, not a hosted read).

**Refs:** `backend/chanakya/schemas/api_models.py` (`IngestRequest.source_type`);
`backend/chanakya/api/routes/ingest.py`. In-PR F0-amendment on `feat/api` (additive/optional; no rebase).

---

## 2026-07-19 · `ProvenanceDrawer` gains `claims` (additive, non-breaking)

**Endpoint:** `GET /evidence/{id}` (the provenance drawer, product/03 C).

**Change:** `ProvenanceDrawer` (in `backend/chanakya/schemas/api_models.py`) gains an optional field
**`claims: list[ClaimRecord] = []`**.

**Why:** the drawer's `clusters` + `opposing_claims` referenced backing claims **by id only**, but the
frozen shape carried no way to reach each claim's **exact source location** (`doc_ref` = file + line /
table row / PDF page+bbox / image region / video frame). The graded non-negotiable is "one click jumps to
the exact source." So the drawer now embeds the **resolved evidence atoms** it references — each
`ClaimRecord` is product/03 **A** in full (source id, `doc_ref`, `kind` = observed/inferred/retraction,
the assertion payload, the three dates, extraction method+confidence, integrity flags). The frontend
indexes `claims` by `claim_id` to render each cluster row and wire its "jump to source" link.

**Impact on frontend:** **non-breaking, additive.** Existing bindings keep working; `claims` is simply now
available. Recommended: render the cluster rows from `claims` (each has `doc_ref` for the deep link) rather
than from the bare id lists.

**Decision (principle → choice → alternative rejected):** *one-click-to-source non-negotiable + "response
bodies validate against frozen models" (no ad-hoc composite)* → **embed the full existing evidence-atom
shape** (`ClaimRecord`, which already equals product/03 A) as an additive optional drawer field. Rejected:
(a) a new lean display-only claim projection — a second shape both sides must adopt, for no extra signal;
(b) a separate per-claim endpoint — N+1 round-trips + an endpoint beyond the frozen §4.8 list. *(User
approved "take the best decision; frontend can adapt and be informed via this log," 2026-07-19.)*

**Refs:** `backend/chanakya/schemas/api_models.py` (`ProvenanceDrawer.claims`);
`backend/chanakya/api/routes/node.py` (`GET /evidence/{id}` resolves the ids → atoms).
Filed as an in-PR F0-amendment on `feat/api` (additive/optional; siblings need no rebase).

---

## 2026-07-20 · `ProvenanceDrawer` gains `sources` (additive, non-breaking) — QA T6

**Endpoint:** `GET /evidence/{id}` (the provenance drawer, product/03 C).

**Change:** `ProvenanceDrawer` gains an optional field
**`sources: dict[str, SourceRegistryEntry] = {}`** — `source_id` → its `config/sources.yaml` registry
entry, for every source cited by the response's `claims`.

**Why:** the drawer was rendering the raw `source_id` as if it were an attribution. On the live corpus
that put the string **`d17b_withheld_gap`** in front of an analyst as the name of a source — it is a
filename, and one that reads like internal scaffolding. "Who says so?" is answered by the source's
**class** (satellite / official / think-tank / named-social …) and its **reliability grade**, and both
live only in `config/sources.yaml`. No GET route exposed that section (`/config/{section}` is
POST-only), so the SPA had no way to reach it and no honest alternative to printing the key.

**What is NOT in it:** a publisher/display **name**. The registry does not carry one, so none is
returned and none may be invented — the frontend renders the class label (a fixed vocabulary map) with
the id demoted to the technical line beneath it. A cited id the registry does not know is **omitted**
from `sources` entirely, and the UI then shows the bare id and says it is unregistered, rather than
describing a source it cannot vouch for.

**Impact on frontend:** **non-breaking, additive.** `SourceCard` added to `src/api/types.ts`;
`evidenceToDrawerModel` folds it into each cluster's `sources[]`. Consumers that ignore the field are
unaffected.

**Decision (principle → choice → alternative rejected):** *nothing is asserted without provenance +
"never show the analyst an internal key as if it were content"* → **return the frozen
`SourceRegistryEntry` verbatim on the drawer that needs it**. Rejected: (a) a `GET /config/sources`
route — a new endpoint outside the frozen §4.8 list, and it would ship the whole 51-source registry to
render two chips; (b) synthesising a display string server-side — puts the API in the copywriting
business and hard-codes English into the contract; (c) bundling a copy of `sources.yaml` into the SPA
build — silently drifts from the live hot-config store the moment a source is edited in-app.

**Refs:** `backend/chanakya/schemas/api_models.py` (`ProvenanceDrawer.sources`);
`backend/chanakya/api/routes/node.py`; `backend/tests/api/test_node_evidence.py`;
`frontend/src/api/types.ts` (`SourceCard`). Branch `qa/t6-drawer-semantics`.


## 2026-07-20 — T5 (map coverage): node attrs for location precision

Additive, node `attrs` only (same pattern as `place_match_*`), emitted by `view/pipeline.py`:

* `location_source` — `"stated-coordinate"` (a source gave the position) or `"gazetteer-anchor"`
  (the node resolved to a curated `config/places.yaml` anchor and borrowed its `canonical_dd`).
  Present only when the node is plotted.
* `location_uncertainty_radius_m` — the honest envelope radius, from `places.proximity_radius_m`
  for the node's `precision_class`. Absent when the precision class is unknown.

`Location.precision_class` gained a `province` rung (`pad|site|terminal|district|city|province`).

TS mirror fix, no backend change: `Location.raw` is `str | list[str]` in `values.py` and was typed
`string | null` in `frontend/src/api/types.ts`; widened to `string | string[] | null`.


## 2026-07-20 — T10 (merge-card traceability): candidate `same-as` edges now cite their identity claims

**Change:** `EdgeView.claim_ids` is now **populated on candidate `same-as` edges** with the claim ids in
which a source asserts the identity — i.e. the evidence *behind* the `source_asserted` term of the
`attrs.breakdown` already on that edge. Previously always `[]`.

* Populated only where a source really spoke: a pair scored on name + neighbourhood alone still carries
  `claim_ids: []`. The two are kept in lockstep by construction (`resolve.scoring.identity_claim_ids`
  uses the same pair/predicate test as `source_asserted_score`), and pinned by an acceptance test in
  both directions.
* Only the `same-as`/`aka`/`marketed-as`/… lane. In-document coreference (`coref-same-as`) is a separate
  raise-only lane that does **not** feed `source_asserted`, so it is deliberately excluded — including it
  would make the citation over-claim what the score counted.
* **No new route.** `GET /evidence/{element_id}` already resolves an edge id, so it now serves those
  claims (with `quotes` + `sources`) for `same-as:<a>|<b>` with no API surface change.

**Why:** an identity assertion is *consumed* as a merge signal rather than drawn as an edge (D-2.5), so
before this the only trace of who said two records are one was a number on the review card. The merge
card asked an analyst to weigh "a source calls them the same · 0.70" with no way to see which source,
saying what, or how credible. That is the one-click-to-source non-negotiable, on the ★ marquee control
point.

**Impact on frontend:** **non-breaking, additive.** `EdgeView.claim_ids` was already optional in
`src/api/types.ts` and nothing read it for `same-as`. `viewToReviewQueue` now reads it to hang an
evidence handle on the `source_asserted` signal row only.

**Also additive (frontend-internal, no API):** `LiveReviewSide.evidenceId`, `MergeSignalRow.evidenceId`
/`.evidenceCount`, `LiveMergeEvidence.differs` (`MergeDiffRow[]`, the attributed form of the existing
`differsOn: string[]`, which is kept as its plain-text projection), and `LiveDrawerSubject.edgeType`.

**Decision (principle → choice → alternative rejected):** *every claim is one-click traceable to its
exact source* → **thread the asserting claim ids onto the edge that proposes the merge, and reuse the
existing evidence route**. Rejected: (a) a new `GET /identity-evidence/{pair}` route — a second
provenance surface for the same object, outside the frozen route list; (b) drawing the identity claims
as graph edges so they'd be reachable — that is exactly the twin-node/self-loop picture D-2.5 removed;
(c) leaving the score uncitable and telling the analyst to go find the document — the failure being fixed.

**Refs:** `backend/chanakya/resolve/{entities,scoring,__init__}.py`;
`backend/chanakya/schemas/stage_io.py` (`Partition.identity_claims`);
`backend/chanakya/view/pipeline.py` (`_resolution_edges`);
`backend/tests/view/test_resolution_edges.py`, `backend/tests/resolve/test_entity_resolution.py`,
`backend/tests/acceptance/test_merge_candidate_provenance.py`. Branch `qa/t10-merge-card-evidence`.
