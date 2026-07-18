# DATA-C — corpus & answer_key observations (for the data agent)

**Author:** DATA-C config session (`feat/data-c`). **Date:** 2026-07-18.
**Scope boundary:** These are **data issues** in the frozen corpus / `answer_key.json` / ontology-vs-oracle
alignment. Per the user's direction, the **data agent** resolves them — the config session does **not** edit
the corpus or answer_key itself. This doc is the handoff punch-list.

**Corpus under review:** `corpus/scenarios/hq9p_primary/` + `hq9p_chaff/` as frozen on `origin/main`
(`9f18c07`). Findings come from a full manual verification pass against `answer_key.json` (every `d01`–`d23`
doc text + both scenarios' ground truth) plus an ontology reconciliation against `C/01` and frozen F0 code
(`backend/chanakya/schemas/{view,claim,config_models}.py`).

Priority tags: **[P0]** breaks the graded oracle / a demo flex · **[P1]** correctness/consistency ·
**[P2]** polish/roadmap.

---

## RESOLUTION STATUS (updated 2026-07-18)

The user directed **this session to apply everything**. **Applied + validated** (see
`DATA-C-flex-protection-changelog.md` for the table): §0 F5 (confirmed deep-tier w/ evidence gate), §1
(equips rename, sustainment split), §2 (F1 edges, d16, enums, dangling variant-of, imported-via), §3
(d19/d20 relocation), §6 (d09 official-only, d04 byline) + d20 pseudo-provenance. **Deferred** (documented,
not text-edits): the per-fixture provenance sidecar system (§7), the ingest oracle-boundary guardrail (→
INGEST), and product/04's stale line. **Roadmap** (unchanged): §5 F7 structural cases; the H-200→HT-233
orphan-alias stays out of the resolver seed to be earned/verified.

## 0. Decided direction (from the user)

- **F5 — deep-tier supplier → ADD A CONFIRMED ONE.** The acceptance criterion wants ≥1 *named* deep-tier
  sub-supplier **confirmed**, rest candidate. The frozen corpus currently confirms **none** below the prime
  (CASIC): both named candidates (`mfr_23rd_ri` = CASIC 23rd Research Institute/BIRM, `mfr_4th_academy`) are
  explicitly *unconfirmed* in `d22`, and the earlier named tier-3 instance (Nanjing Yuzhi TWT module) was
  removed in a rewrite (grep `nanjing|yuzhi|TWT` → 0 hits). **Action:** add one real, export-controlled
  deep-tier house (e.g. a TEL-chassis or T/R-module maker named on a **BIS Entity List / sanctions listing**
  — the kind of *hard* source that legitimately confirms), give it a node + a `confirmed` supply edge, and
  leave `mfr_23rd_ri` / `mfr_4th_academy` `candidate`. This demonstrates "confirmed IS reachable with hard
  sourcing" against the candidate rest, while HT-233's own chokepoint stays `candidate`/`UNKNOWN` (F2, which
  is correct and must not change). Couples to the ontology's deep-tier `component-of` + tier-2/3
  `supplies-component` branch.

## 1. Open modeling forks (data agent decides; config session's recommendation noted)

These change the **strings ASK/EVAL bind to**, so they belong to whoever owns the oracle.

1. **[P0] `supplies-component` is overloaded across two node-type pairs.** In `answer_key.json` the *confirmed*
   hero edges are **Component→Variant** (`comp_ht233 --supplies-component--> var_hq9p`, reads as "radar
   equips variant"), while the *candidate* deep-tier edges are **Manufacturer→Component**
   (`candidate-supplies-component`, C/01's original semantics). One edge name means two different things.
   - **Config-session recommendation:** rename the Component→Variant relationship to **`equips`** (or
     `fitted-to`) and reserve `supplies-component`/`candidate-supplies-component` strictly for
     Mfr→Component. Requires editing the ~2 confirmed hero edges in `answer_key.json`.
   - Alternative: keep it overloaded (F0's `TypeDef` has no from/to constraint, so it validates as-is) —
     zero oracle edits, but semantically muddy.

2. **[P0] Sustainment: one merged type vs. two.** `C/01` defines TWO node types with **different freshness**
   (`Interceptor Stockpile & Resupply` = *perishable*; `Technical-Data / Software & Calibration Authority`
   = *durable/force-revalidated*). `answer_key.json` collapsed them into one `"sustainment"` type + a
   `subtype` attr (`interceptor_stockpile | techdata_authority`). A single `TypeDef.freshness_class` can't
   carry two half-life classes cleanly.
   - **Config-session recommendation:** **split** into `interceptor_stockpile` (perishable) +
     `techdata_authority` (durable), matching C/01. Update the 2 sustainment nodes in `answer_key.json`.
   - Alternative: keep merged; carry freshness per-subtype (config becomes ambiguous at the type level).

## 2. Oracle internal-consistency bugs (fix in `answer_key.json`)

3. **[P0] F1 — `worked_query.expected_path_edges` reverses all 4 hops** vs `ground_truth.edges`. E.g.
   `expected_path_edges` asserts `comp_ht233 --manufactures--> mfr_casic` ("the radar manufactures CASIC"),
   while the canonical edge is `mfr_casic --manufactures--> comp_ht233`. Both can't be true of the same
   directed set. **Fix:** rewrite the 4 `expected_path_edges` `from`/`to` to match `ground_truth.edges`'
   direction (store direction is canonical; the trace is a *reverse walk* site→origin, so a code comment
   there noting bidirectional traversal is enough). Full detail in the verification report.

4. **[P1] `d16` mislabelled `source_type: official`.** Its text is an **anonymous defence-forum post**
   (`PAKISTAN DEFENCE FORUM`, handle `SentinelHawk_PK`, quoting an un-nameable "contact"). `official` gets a
   materially higher base R than `social`/anon-social in the rubric. **Fix:** set `registry.source_class` /
   `source_type` → `social` (keep `adversary_denial_flag: true`, `reliability_grade: D`).
   *(Config note: the config session authors `sources.yaml`'s `d16` as `social` regardless — this item is
   only to keep the answer_key's own registry copy internally honest.)*

5. **[P1] Enum casing vs frozen F0 code.**
   - `observability_ceiling: "probable_max"` (underscore) on `gap_ht233_maker` + `gap_launcher_count` →
     frozen `view.py` `Literal` is **`"probable-max"`** (hyphen). Fix to hyphen.
   - Node `status: "candidate"` on `mfr_23rd_ri` + `mfr_4th_academy` → not in frozen `Status` Literal
     (`confirmed|probable|possible|contradicted|stale|insufficient`). The candidate-ness belongs on the
     separate `chokepoint_status` / materiality axis (`Literal["confirmed","candidate","none"]`). **Fix:**
     set node `status` → `possible` (single uncorroborated) and carry `candidate` on `chokepoint_status`.

6. **[P1] `variant-of` dangling target.** `var_hq9p`/`var_hq9be --variant-of--> "HQ-9"`, but `"HQ-9"` is a
   bare string, not a node in `ground_truth.nodes` (17 nodes, none `id: "HQ-9"`). **Fix:** either add a
   lightweight `variant`/family node `HQ-9`, or drop the edge and keep `family` as an attr on the Variant
   (C/01's original design). Also decide `variant-of` direction — answer_key uses **Variant→Family** (more
   intuitive than C/01's Component→Variant); config session will adopt whatever the answer_key ends up using.

## 3. Content contradiction (highest-impact)

7. **[P0] `d19` + `d20` contradict the flagship relocation observable.** The seeded observable is
   `unit_hq9b` at **Rawalpindi (2021)** → relocates to **Rahwali (2025)** (single-pass probable → 2nd signal
   confirmed → `supersedes` retires Rawalpindi → stale). But:
   - `d19_rahwali_confirm.txt`: *"Rahwali has been associated in open reporting with a … HQ-9BE … battery
     **since at least 2021**…"*
   - `d20_supersede_spoof.txt` (a REAL, not-spoof embedded post): *"…HQ-9/P … co-located near Rahwali … —
     **same TEL layout as reported 2023**. No change since then…"*

   If Rahwali independently hosted an HQ-9 battery since 2021/2023, it's not a 2025 relocation and the
   `supersedes` edge is wrong. **Fix:** edit those two lines to remove the pre-2025 Rahwali presence (e.g.
   d19 → "Rahwali has not previously been cited as an HQ-9-family site; this is the first pass to associate
   the type here"; reframe the d20 `@SushantNMehta` line the same way). Text-only; no schema change.

## 4. New edges/attrs the answer_key needs that C/01 doesn't list (ontology reconciliation)

The config session will represent these in `ontology.yaml`; flagging so the data agent keeps the oracle
consistent with whatever it decides in §1:
- **`imported-via`** (Variant→Contract) — appears only in `answer_key.json`, in no design doc.
- **`sustained-by`** (Unit→Sustainment) — used by answer_key; omitted from DATA-C.md's own edge recap.
- **`candidate-supplies-component` / `candidate-manufactures`** — distinct literal strings, always paired
  with `status: candidate` (the deep-tier candidate edges).
- **`manufactures` broadened** to Mfr→{Component, Variant} (answer_key uses it for both; C/01 = Component
  only).
- **`Variant.branch`** attr (`"Pakistan Army"` / `"Pakistan Air Force"`) — not in C/01's Variant attrs
  (C/01 puts `service_branch` on Unit). Harmless redundancy; keep.
- **`functional_role`** needs a 4th value **`interceptor`** (`comp_interceptor`), and the seeded string is
  **`engagement_fire_control`** (underscore), not C/01's `engagement/fire-control` slash form. Pick one
  casing; config session will follow the answer_key's underscore form.

## 5. Structural cases still unseeded (F7 — config session default = ROADMAP unless you prioritize)

`md/05 §5.1`/`C/01` want these; they're **not** in DATA-C's acceptance checklist and are md/05 backlog. The
config session will **represent** them in `ontology.yaml` but **not instantiate** them in the corpus. If you
want them live, the data agent needs to seed:
- **`substitutable-by` — all three states.** Only the `UNKNOWN` scalar exists (`comp_ht233.substitutability`).
  No `known-sole-source` and no `known-alternates` instance → the chokepoint substitutability contrast can't
  be shown. Needs a new component/edge + a supporting doc.
- **Unit multi-valued `designator` / cover-designator (MUCD).** No node carries >1 designator; grep
  `MUCD|cover-designator|bort|tail number` → 0 hits.
- **`operational-status` ordinal + readiness-proxy-vs-gap.** Narrative hints exist (d02/d15/d19) but no
  ordinal attr on `unit_paad`/`unit_hq9b` pairing an observed proxy against an unobservable-manning gap.

## 6. Minor / documentation (P2)

- **`d09` is a compound doc** — an ISPR "routine training" release **+** an embedded Jane's excerpt that
  *leans toward* the relocation reading and hedges whether ISPR even refers to the same activity. This
  muddies the clean d08-vs-d09 "same site+date → CONTRADICTED" contradiction flex (it's really a 3-way
  disagreement). Consider splitting d09 into two doc ids (official-only vs Jane's trade-media) so the
  registry/credibility layer scores them separately, or relabel the flex.
- **`d04` byline mismatch** — filename implies Army Recognition; text byline reads "South Asia Defence
  Monitor" (suspiciously close to d01's masthead). Cosmetic; fix if `primary_origin_id` precision matters.
- **`product/04` stale line** — claims `d01` "explicitly flags NOT the same system as FT-2000"; current d01
  text has no FT-2000 mention (it's only in d04, + an unrelated d16 reference). Fix the product doc, or add
  the line back to d01 if two independent FT-2000 sources were intended.
- **`md/05 §4` alias table** not updated with Type 305B / H-200 / Type 120 (F3) — but the corpus docs
  independently carry these un-seeded (good raw material for the orphan-alias case, see §7).

## 7. Cross-cutting flags for later sessions (not corpus data, but surfaced here)

- **Orphan-alias adaptation demo is unseeded.** `spine/08 §3.11` / `md/05 §5.2.5` want **one planted alias
  not in the seeded resolver table** to exercise the LLM candidate-gen recall path live. No concrete named
  orphan-component instance exists yet. Candidates already latent in the corpus: **Type 305B** (d01/d06/d14),
  **H-200** (d06/d15), **Type 120** (d15/d21). The data agent could designate one as the earned-merge
  orphan.
- **`coordinated_inauthenticity_flag` is a bool in frozen F0** (`schemas/claim.py`), but the credibility
  penalty table wants a **three-state** (`independent | suspected | too-clean`). SCORE/INGEST will need
  either an F0-amendment (3-valued field) or a documented bool→state mapping. **Not a corpus fix** — flag for
  whoever owns F0/SCORE/INGEST next.
