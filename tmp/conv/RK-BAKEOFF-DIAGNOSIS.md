# RK-BAKEOFF — diagnosis of the NO_MEASURED_DIFFERENCE verdict

**Status:** synthesis of three independent metric investigations, every load-bearing number
re-verified by the author against the persisted bundles under `tmp/rk-bakeoff/run/`. **Zero API
calls were made.** The offline replay reproduces `scorecard.json` exactly (coref_binding,
surface_f1, surface_precision/recall, citation_faithfulness, extract_only_stated,
trap_avoidance, discriminator tallies all match to 4 dp), so every figure below is the shipped
scorer's own arithmetic.

**No prompt, schema, matcher, gold or config file was changed by this task.**

---

## 1. Did the bake-off measure the models, or measure our instrument?

**It measured our instrument.** Roughly 60% of the composite weight sits on metrics that are
structurally incapable of separating two models on this gold, and the 0.0095 composite gap is
not evidence of similarity — it is four genuinely separating lines pointing in opposite
directions being averaged into silence by a composite whose largest terms are broken.

That is the finding, and it must not be softened. `NO_MEASURED_DIFFERENCE` is a correct
statement about the composite and a misleading statement about the models.

Two things make it so:

**(a) The dominant metrics have no working denominator.** Of 33.5 points of composite weight:

| metric | weight | share | why it cannot measure a model |
|---|---|---|---|
| `coref_binding` | 5.0 | 14.9% | Zero gold clusters in the graded slice contain two system-indexable claims that *should* bind. Its only non-empty positive denominator is two planted **anti**-coref traps, so the sign is inverted. |
| `discriminator_capture` | 4.5 | 13.4% | The prompt never asks for the field, and the denominator is chosen by the candidate (opus graded on 21 slots, gemini on 15–17, different sets). |
| `citation_faithfulness` | 4.5 | 13.4% | 79–91% of its failures are span-locality artefacts; strip the locality window and it *is* `extract_only_stated` to three decimals. |
| `surface_f1` | 3.0 | 9.0% | Precision's denominator is "how much of the document did the model read that our 65-row curated gold happens not to enumerate". The F1 ceiling is candidate-dependent (opus 0.548, gemini 0.689) and penalises the more thorough reader. |
| `structured_output_reliability` | 3.0 | 9.0% | Reported 1.0000 ± 0.0 on runs where a typed list field arrived as truncated unparseable text. It is blind to the one structured-output failure that actually occurred. |
| **subtotal** | **20.0** | **59.7%** | |
| `discriminator_fabrication_avoidance` | 4.0 | 11.9% | Rides the same candidate-chosen alignment gate as `discriminator_capture`. |
| **subtotal incl. the above** | **24.0** | **71.6%** | |

**(b) The separations that *did* exist cancelled.** Four lines cleared their own margin rule
(`max(0.03, 2 × pooled sd)`):

| line | weight | opus | gemini | gap | margin | favours |
|---|---|---|---|---|---|---|
| `graph_recall` | 3.0 | 0.5050 | 0.4550 | +0.0500 | 0.0418 | opus |
| `citation_faithfulness` | 4.5 | 0.7891 | 0.8331 | −0.0440 | 0.0300 | gemini |
| `extract_only_stated` | 4.5 | 0.9550 | 0.9852 | −0.0302 | 0.0300 | gemini |
| `surface_recall` | **0.0** | 0.3662 | 0.2985 | +0.0677 | 0.0458 | opus |
| `graph_node_recall` | **0.0** | 0.6000 | 0.5308 | +0.0692 | 0.0383 | opus |

The composite is 0.62521 (opus) vs 0.61574 (gemini). The verdict is not "these models are
alike"; it is "opus reads more and gemini asserts less, and our weighting cancels the two to
within a hundredth."

Note also that the two lines that most cleanly separate the candidates — `surface_recall` and
`graph_node_recall` — carry **weight 0**, while `surface_f1`, which mathematically destroys
that signal by harmonic-meaning it against an artefactual precision, carries 3.0.

**Would a re-run with better models change the verdict?** No. Two architecturally different
models fail the *identical* 28 gold rows in the *identical* four buckets in all 10 runs, and
the union of rows either model ever reaches differs by three rows out of 65. That is the
signature of a ceiling, not of comparable capability.

---

## 2. Attribution of the shortfall, metric by metric

Categories: **PROMPT** (we never asked) · **SCHEMA** (no field to put it in) · **GOLD** (labels
no extractor could match) · **MATCHER** (rejects correct answers) · **CLIENT** (our code lost
the answer) · **MODEL** (a real difference).

### coref_binding — 0.3511 / 0.3658, weight 5.0

Verified attribution ladder (each rung changes only *our* scorer, never a model output):

| rung | opus | gemini |
|---|---|---|
| L0 as shipped | 0.3511 ± 0.0881 | 0.3658 ± 0.0243 |
| L2 + absent referent = its own singleton (standard B³ convention) | 0.7993 ± 0.0134 | 0.7765 ± 0.0322 |
| L3 + drop the ANTI_COREF / AMBIGUOUS gold clusters | 0.8407 ± 0.0168 | 0.8247 ± 0.0433 |
| L4 + score only entity-form claims (what the system can index) | **1.0000 ± 0.0000** | **1.0000 ± 0.0000** |

- **~68% METRIC.** `metrics.py:588` builds B³ items as `(gold.coref_cluster,
  extracted.referent_id)` and compares by equality. `referent_id` is `None` for every claim the
  model correctly left a singleton, and `None == None`, so all of them collapse into one shared
  system cluster. Verified: 18 of 19 graded items are `None` in opus run-01. B³ **recall** is
  already 0.87–1.00 for both models; **precision** is 0.146–0.277 and *all* of the precision
  loss is that one bucket. The prompt explicitly instructs "report only the clusters with more
  than one member … Any mention you do not name stays its own singleton." We asked for X and
  scored ¬X.
- **~25% GOLD/SYSTEM OBJECT MISMATCH.** 35 of the 51 registry-tagged gold claims are triple-form
  and 1 is event-form. `coref.stamp_referents` writes `referent_id` on entity-form claims only,
  by explicit and defensible design ("a relationship claim names two mentions and therefore has
  no single referent"). 36 of 51 tagged gold rows are unscoreable by construction. The gold
  labels *mention* clusters; the system's referent is a *claim*-level grouping; the metric routes
  one through the claim matcher to compare against the other.
- **The remainder is empty, and this is the deepest defect.** At L4 both models score exactly
  1.0000 with sd 0.0000 on n≈5 items — because every registry-backed positive cluster contains
  exactly **one** entity-form claim. There is not a single gold cluster in the slice where two
  system-indexable claims *should* share a referent. The top-weighted criterion has an empty
  positive denominator.
- **SIGN INVERSION — verified.** The only two registry clusters with ≥2 entity-form claims are
  `d05-C4-events` (3, "ANTI_COREF (distinct stated identifiers)", annotator note: "**THE
  over-merge trap**") and `d19-C4-othersites` (2, "ANTI_COREF (stated enumeration)"). Both sit in
  positive `claims`, not in `negative_gold`. Simulating a system identical to the real one except
  that it merges both traps: opus 0.3511 → **0.6241** (+0.2730), gemini 0.3658 → **0.6462**
  (+0.2803). The metric pays ~29× the observed composite gap for committing exactly the failure
  the project exists to prevent. The adapter's own S6 rule (`ANTI_COREF → negative gold,
  penalise_binding`) routes gold *rows* by predicate class and never sees registry-level
  ANTI_COREF *cluster* tags, so these leak into positive gold.
- **CLIENT — 100% of opus's excess variance.** 2 of 35 opus coref calls (`d05_customs_manifest`,
  run-01 and run-03) returned `clusters` as a **truncated JSON string**, not a list — 265 and 376
  chars, ending mid-token. `valid_clusters` does `for entry in raw.get("clusters") or []`,
  iterates the *characters*, drops each on the `isinstance(entry, dict)` guard, and returns
  nothing. The recorded `error` is `null`; `AnthropicExtractionClient._call` returns
  `dict(block.input)` with no validation. Those are exactly the two runs scoring 0.2551, against
  0.4014/0.4220/0.4220 for the other three. What was discarded is the gold's `d05-C1-consignee`,
  whose own note calls it "The ONLY identifier-backed equivalence in the slice." Opus had it
  right, twice, and our client threw it away silently — and `structured_output_reliability`
  scored 1.0000 on those very runs, because it checks only that the call returned and invented no
  *top-level* key.
- **SCHEMA.** `CoreferenceCluster.evidence` ships as `{"anyOf":[{"type":"string"},{"type":"null"}],
  "default":null,"title":"Evidence"}` — a bare nullable string, no enum, no description. The three
  legal categories live only in the system prompt. This cost GPT-5.6 **7** silently-dropped
  clusters (labels like `EXPLICIT_EQUIVALENCE — CLIAD is the parenthetical acronym for…`); it cost
  opus and gemini **0**, so it is a real schema defect but not part of the shared floor.
- **GOLD (known 16-row defect): ~0% here.** 13 of the 16 non-verbatim rows carry a coref tag, but
  they are unreachable by the matcher, so they never enter the denominator. They cost statistical
  power (51 tagged → ~17 graded per run), not score.
- **MODEL: none measurable on binding quality.** Every rung of the ladder leaves the gap inside
  the margin.

**Correction to the coref investigation:** the verbatim licensing-span rail killed **0** clusters
for *all three* candidates (I re-ran `cluster_spans` over all 199 proposals), not 4/35 for GPT.
GPT's 7 losses were entirely the missing `evidence` enum. The rail is completely inert on this
slice.

### surface_f1 — 0.2006 / 0.2059, weight 3.0

- **~45 of the 80 missing points are structural GOLD COVERAGE.** Precision denominator averages
  **172.4** (opus) / **123.8** (gemini) against **65** scored gold rows. A model that emitted at
  this volume and matched *all 65* would score F1 = **0.548** (opus) / **0.689** (gemini). F1 = 1.00
  requires emitting the 65 gold claims and nothing else. Because the ceiling falls as emissions
  rise, the metric systematically rewards the terser extractor — the exact bias the negative-gold
  precision-exclusion machinery was built to prevent, applied to 28 declared rows while ~120
  unlabeled-but-grounded spans per run go uncovered.
- **The 94.8% contradiction, verified.** Of the 148.6 charged false positives per opus run,
  **94.8%** are grounded in their own cited document under the harness's own `_lexically_grounded`
  test (gemini 104.4 FPs, **97.9%** grounded). That is the *identical* test that produces
  `extract_only_stated` = 0.9550 / 0.9852, a 4.5-weight VETO line. Two metrics in one scorecard
  score the same emissions with the same grounding notion and disagree by ~7×. The delta is
  entirely "the gold did not label it", not fabrication.
- **~14 pts GOLD REPRESENTATION.** 39 of 65 gold rows are never matched by *either* model in *any*
  of 10 runs. Four buckets score exactly 0.00 for both in all 10 runs: `triple:observed-at`
  **0/15**, `entity:known_gap` **0/7**, `entity:variant` **0/4**, `triple:equips` **0/2** — 28 rows,
  43% of the gold. Where the representations agree, both models do well
  (`contract_import_event` 3.0/3.0 of 3, `inducted-into` 1.0/1.0 of 1, `basing_site` 4.8/4.2 of 6,
  `same-as` 6.4/5.4 of 8).
- **~11 pts the known 16-row verbatimness confound.** The gold documents its own ceiling:
  `all_role_surfaces_verbatim_somewhere_in_document` = 49/65 = **0.754**. 13 of the 16 never match;
  3 (`d19-r07`, `d19-r14`, `d20-r15`) do, carried by the fuzzy kernel.
- **~3 pts SELF-INFLICTED.** Measuring `coref_binding` at all requires
  `resolution.earned_identity.enabled: true`, which turns on extraction pass 2 and adds **29.6**
  (opus) / **16.6** (gemini) `coref-*` claims per run to the precision denominator — 19.9% / 15.9%
  of all charged FPs — in a form the gold cannot express. Excluding them (recall untouched):
  F1 0.2006 → **0.2290** and 0.2059 → **0.2259**. A flag turned on to measure the top-weighted
  metric silently degrades a 3.0-weighted one. `matcher.py` already makes exactly this argument for
  `unmodelled` spans and does not apply it here.
- **MATCHER — real but smaller than claimed.** `token_sort_ratio` decays on length ratio even when
  the short string is 100% contained: `HQ-9/P` vs the gold's `a battery-level deployment reportedly
  designated HQ-9/P` scores 0.20 under token_sort, 1.00 under token_set. The gold labels *mention
  spans*; the tool schema asks for *names* (`name: str | None`, "A named weapon-system / variant the
  source states"). Switching the kernel to `token_set_ratio` moves matched claims 23.8 → 35.0 (opus)
  and 19.4 → 31.2 (gemini). The leniency knobs are *not* the constraint: `role_min` 0.70→0.55 buys
  **+0**, `pair_min` 0.80→0.65 buys **+1.0**, `entity_type_policy=ignore` buys **+0**,
  `require_same_form=False` buys **+0**.
- **~7 pts GENUINE MODEL RECALL FAILURE**, and it is identical across both models
  (`d05-r12 AL-NOOR CARGO SERVICES`, `d05-r19 End-user certificate` are verbatim in d05 and neither
  model produced them).

**Correction to the surface investigation — the `observed-at` mechanism is misattributed.** The
report says the 15 `observed-at` rows fail because the pipeline emits a `SightingEvent` in EVENT
form and `require_same_form` rules it inadmissible. **Relaxing `require_same_form` recovers zero
rows.** Even relaxing *everything simultaneously* (token_set kernel, form ignored, predicate
ignored, entity type ignored, `role_min` and `pair_min` at 0.50) recovers only **5 of 15**. The
pipeline already emits `observed-at` (4/run) *alongside* `SightingEvent` (13/run), so the
suggested follow-up — "check whether the ontology wants `observed-at` and the extractor emits
`SightingEvent`" — is a non-issue. The real cause is that these gold rows are annotator-composed
pseudo-triples: `d19-r08` is `<"a repeat optical pass on 29 March", observed-at, "the radar
hardstand occupied and TEL count u…">`, `d20-r09` is `<"whole btry", observed-at, "Rahwali site
basically empty now allegedly">`. Seven of the 15 are in the non-verbatim-16 list. **No matcher
change reaches these. It is a gold-authoring problem and it belongs to the corpus work.**

### discriminator_capture — 0.2952 / 0.1882, weight 4.5

- **PROMPT — the largest single defect in the whole scorecard, and it is category 1.**
  `_SYSTEM_BASE` (`extract.py:541`) is ~350 words. It instructs at paragraph length on
  `signature_geometry` and explicitly on `source_quote`, `date_text` and alias handling. Verified by
  string count over the full prompt block: it contains **zero** occurrences of `context`,
  `discriminat*`, `operator`, `individuat*`, `geography`, or "tell apart". The four slots reach the
  model only as field descriptions on a nested optional sub-object, `MentionContext`, whose class
  docstring — which I confirmed **is shipped verbatim inside the tool schema**, Sphinx markup and
  all — contains `` :class:`chanakya.schemas.AttrDef` ``, "spine/13 §10, plan §4 A7", and the
  sentence "**Populated by the model from S1; read by nothing yet.**" We put 13.4% of the composite
  on a field our prompt never requests and our own schema tells the model is inert. Both models
  scored `structured_output_reliability` 1.000 — they filled exactly what we asked for.
- **METRIC — the denominator is chosen by the candidate.** `tally_discriminators`
  (`metrics.py:451`) greedily 1-1 aligns gold entity claims to raw-payload mentions on a ≥0.70 fuzzy
  **name** match, then grades only the aligned ones. Verified per run: opus `aligned=11,
  stated_total=21` in all five runs; gemini `aligned=8–9, stated_total=17/17/17/17/15`. The gold
  labels **47** stated slots across **28** entity claims, so opus sat a 21-question exam and gemini a
  15–17-question exam, on non-identical questions, and over half the discriminator gold was never
  reached by either. **Any comparative claim on this metric is invalid as constructed.**
- **GOLD — decoration scored as model error.** 10 of the 47 gold discriminator values are annotator
  constructions, violating the gold's own contract ("Values are the source's own words, copied").
  `d02-r05` geography is `Karachi (city precision only)`; both models extracted `Karachi` — the exact
  correct surface — and both were scored WRONG at similarity 0.41, and a WRONG stays in the
  denominator. `d19-r01` operator is `Pakistan Army/PAF joint-use (DISJUNCTIVE)`: opus's
  `…joint-use facility` squeaked in at 0.80, gemini's `Pakistan Army/PAF` failed at 0.61 — the
  pass/fail hinged on an annotator's parenthetical.
- **The one raw behavioural indicator runs the other way.** Context-fill rate over emitted mentions,
  verified: **gemini 0.567** (0.64/0.53/0.68/0.47/0.52), **opus 0.374** (0.38/0.39/0.40/0.30/0.40).
  Gemini engages the field ~50% *more* and scores lower, because its fills land on mentions the
  name-alignment gate discards and because it gives the source's bare surface where the gold wants
  the annotator's decorated form.
- **MODEL: none. Report as UNMEASURED.**

### citation_faithfulness — 0.7891 / 0.8331, weight 4.5, VETO

- It ran the **lexical proxy**, never the `EntailmentJudge` the signature supports
  (`detail['method']` says so). `_lexically_grounded` requires *every* role surface of a claim to
  appear at ≥0.85 partial-ratio inside the **cited span**.
- Verified: opus 207.4 graded/run, 43.8 failures — **78.5% are grounded elsewhere in the same
  document**. Gemini 147.6 graded, 24.6 failures — **91.1%**. Genuinely ungrounded anywhere:
  **4.53%** (opus) / **1.49%** (gemini).
- **CF minus the locality penalty IS `extract_only_stated`**, verified to three decimals: opus
  0.9547 vs measured EOS 0.9550; gemini 0.9851 vs 0.9852. **Two of the three VETO lines, carrying
  9.0 of 33.5 composite weight (26.9%), are one lexical string test at two window widths. The
  composite double-counts.**
- **SCHEMA.** `RelationMention` exposes one `source_quote`, so a relation whose endpoints are named
  on different lines has no way to cite both. Opus fails `imported-by` **15/15** and `exported-by`
  **15/15** across 5 runs on this mechanism alone — even though the persisted payloads show it
  supplied a perfect quote for each endpoint on the sub-mention. It also cannot pass a correctly
  cited anaphoric relationship: opus fails `coref-distinct-from` 29/49, `observed-at` 19/22,
  `TransferEvent` 22/25. **The line penalises precisely the discourse-level binding that
  `coref_binding` at weight 5.0 is supposed to reward.**
- **MODEL: none at the reported magnitude.**

### trap_avoidance — 0.8727 / 0.7455, VETO gate (weight 0 in the composite)

This was the finding most likely to survive. **It does not, and the sign reverses.**

The basis string in `adapter.py:396` admits the problem: *"an unpaired emitted claim whose span
overlaps the trap span"* — no test that the claim asserts anything about the trap's content.
Recomputed over all 11 `not_a_claim` traps, 10 runs:

| basis | opus | gemini | gap |
|---|---|---|---|
| span overlap (as shipped) | 0.8727 | 0.7455 | **+0.1273** (> the 0.091 margin → "separated") |
| exclude bare entity-existence hits | 0.9455 | 0.9273 | +0.0182 (separation gone) |
| require a role surface *inside* the trap span | 0.9455 | **1.0000** | **−0.0545 (ordering reverses)** |

I inspected every hit across 10 runs. **Not one is a fabricated assertion.**
- Gemini's 10 `d20` hits (5/5 runs on both traps) are entity claims naming `@IndoPacSentry` and
  `@SushantNMehta` whose citation span is the post *body*. Gemini named the source and correctly
  declined to mint a relocation claim — the desired behaviour on a trap whose entire point is "this
  post asserts nothing" — and was charged with fabrication for it.
- Gemini's `d05-r24` hits are correct `imported-by` / `TransferEvent` claims cited against a
  1438-char whole-record span that happens to include a pasted-email noise block.
- Opus's `d17b-r10`/`d17b-r15` hits are bare `known_gap` entities, 0/4 with a role surface inside
  the trap.
- Opus's surviving `d05-r23` hits are a `same-as` between `ORIENT ELECTRO TRADING (PVT) LTD` and
  `ORIENT ELECTRONIC TRADING CO`, which `d05_customs_manifest.txt` lines 73–74 state **in full**
  ("formerly ORIENT ELECTRONIC TRADING CO -- name change ref SECP CUIN 0087762, 2019"). Opus cites
  that span *and* the cross-reference note as corroboration; the trap fires on the second citation.
  Trap row `d05-r23`'s own rationale — "the one place the document begins to state an identity-match
  is cut off mid-token" — is factually wrong about its own corpus.

**Correction to the discriminator/veto investigation — the trap mechanism is misattributed to our
transform.** That report says "our transform attaches the post body, not the byline, as the
provenance for a social-media author entity", and proposes fixing the transform. That is wrong.
Opus, through the *identical* transform, attaches the **byline**. Verified from the raw payloads:
for `@IndoPacSentry`, opus's own `source_quote` is `"Handle: @IndoPacSentry (OSINT hobby account,
~4,200 followers)\nDate: …\nStatus URL: …"` (span 838–984, before the body); gemini's is the post
body itself, `"per the Rahwali 'left the base' claim going around — cannot confirm…"` (span
992–1156, the trap). **This is the model's own citation choice, passed through faithfully.** The
metric defect stands unchanged — span overlap is not fabrication — but the proposed fix targets
the wrong component and would change nothing.

**MODEL: a real behavioural difference, mislabelled.** Opus cites the byline for "this account
exists"; gemini cites the body. Opus's is the better provenance. That is a citation-granularity
difference worth knowing about, and `trap_avoidance` converts it into a 0.127 "fabrication" gap
on a VETO gate.

### extract_only_stated — 0.9550 / 0.9852, weight 4.5, VETO

The only line carrying real, inspectable model signal — and both the verdict language and the
investigation's framing of it need correcting.

- **The margin is meaningless.** Pooled sd gives 0.017, so the binding floor is the fixed 0.03 and
  the gap is 0.0302 — clearing an absolute floor by 0.0002 on a metric compressed against 1.0, where
  opus's entire remaining headroom is 0.045. The same 0.03 floor applied to `coref_binding` at 0.35
  means something completely different. Rare-event lines should be decided on the error rate.
- **As an error rate the difference is real and stable** — opus 47 failures / 1037 graded = **4.53%**;
  gemini 11 / 738 = **1.49%**; per-run opus 8/14/9/9/7, gemini 2/1/2/3/3.
- **But it shrinks substantially once our own defects are peeled, and the investigation overstates
  it.** 18 of opus's 47 failures are `known_gap` entities. Inspecting `d17b_withheld_gap.txt`:
  opus's `'obscured tree-line segment / perimeter coverage'` composes L22 ("partial obscuration …
  roughly 20% of the perimeter") with L39 ("low along obscured tree-line segment");
  `'pixel-level baseline comparison'` is L41 ("direct pixel-level comparison not performed").
  These are **faithful composite labels for gaps the document explicitly states**, not
  fabrications. A `known_gap` node has no verbatim name in *any* document by construction — a gap
  is described, not named — which is why `entity:known_gap` also scores 0/7 on recall, and why the
  gold's own `d02-r11` (`'the exact number of batteries/launchers (TELs) inducted'`) sits in the
  non-verbatim-16. One root cause, two metrics.

  | peel | opus | gemini | ratio |
  |---|---|---|---|
  | as scored | 4.53% | 1.49% | 3.0× |
  | minus `known_gap` (an unnameable type) | 2.80% | 1.22% | 2.3× |
  | minus `known_gap` and rows the matcher scored **correct** | 2.31% | 0.54% | 4.3× |

- **The harness contradicts itself on the same claim.** `d19-r14` (`'Sialkot-area dispersal site'`,
  in the non-verbatim-16) is scored as a **correct gold match** by the matcher and as a
  **fabrication** by `extract_only_stated`, in the same run, for both models. Verified: 5 of
  gemini's 11 EOS failures (**45%** of its entire fabrication score) and 5 of opus's 47 (11%).
  The known gold defect lands directly on a VETO line and hurts the terser model far more in
  proportional terms.

### structured_output_reliability — 1.0000 / 1.0000, weight 3.0

`CallRecord.ok` checks only that `error is None` and `payload` is a dict; `invented_fields()`
checks only **top-level** keys. A typed list field arriving as truncated unparseable text passes
both. It reported 1.0000 ± 0.0 on the two runs where opus's coref payload was destroyed. Its
1.000 is not evidence of clean payloads; it is 3.0 weight of guaranteed tie.

---

## 3. Ranked fixes

### A. Fixes that make the instrument honest — do these

Ranked by measurement validity bought per unit of effort.

1. **Report `coref_binding` as UNMEASURABLE on this gold, with the four defects named.** Not
   re-weighted to zero — `coref_channel.py` says why: *"Do not re-weight it to zero — that turns an
   honest gap into a silent one."* This is the single most important action, because 14.9% of the
   composite is currently a number with an empty positive denominator and an inverted sign.
2. **Fail loudly on an unparseable tool payload** (`chanakya/ingest/client.py`, and/or count it
   against `structured_output_reliability`). One-line class of fix; it silently destroyed the
   single best coref answer either model produced, twice, and inflated the pooled noise floor ~3×.
   *Also extend `invented_fields`/`ok` to validate field types, not just top-level key names.*
3. **Adopt the standard B³ singleton convention** (absent referent = its own singleton) **only in
   combination with (1).** On its own it moves 0.3511 → 0.7993 and would look like a fix; on this
   gold it is degenerate, because at L4 a model that clusters nothing scores 1.000. The convention
   is correct; the gold cannot exercise it.
4. **Exclude the `coref-*` pass-2 channel from `surface_precision`'s denominator**, on exactly the
   argument `matcher.py` already makes for `unmodelled` spans. F1 0.2006 → 0.2290 / 0.2059 → 0.2259,
   recall untouched. A correctness fix, not a leniency knob.
5. **Give `trap_avoidance` an assertion-bearing basis** — a hit requires a role surface located
   inside the trap span, not merely a byte-range that touches it. As shipped it rewards a model for
   *not* naming its sources and for citing narrowly, which is the opposite of this project's
   provenance doctrine. It should not be functioning as a veto gate in its current state.
6. **Grade citation faithfulness over the claim's evidential neighbourhood** — every quote the model
   supplied for the mentions involved, or the enclosing record/paragraph — rather than one contiguous
   span; and give `RelationMention` a second quote slot so a two-endpoint relation can cite both
   endpoints. Then decide deliberately whether CF and EOS both belong in the composite, since they
   are currently the same test twice for 26.9% of the weight.
7. **Fix `discriminator_capture`'s denominator to all 47 gold slots** (a slot the model's naming
   failed to reach is a *miss*, not an exclusion), and mark the 10 annotator-decorated gold values
   UNGRADABLE. Until then the two candidates are sitting different exams.
8. **Promote `surface_recall` and `graph_node_recall` out of weight 0**, or stop reporting
   precision-based F1 on a curated gold. Report recall against the stated 49/65 ceiling. F1 here
   mathematically destroys the one component that separates the candidates.
9. **Persist per-metric `detail` in the scorecard.** Every finding in this document required
   re-running the scorer offline. `NO_MEASURED_DIFFERENCE` shipped without anyone seeing that
   `trap_avoidance` was 10/14 social-media handles.

### B. Changes that would raise scores without improving extraction — named, and rejected

These are the tempting ones. Each would move a number; none would help an analyst reading a real
document. Applying the test — *would this help a real analyst, or only help us score against these
125 labeled rows?*

- **Switch the similarity kernel to `token_set_ratio` / `partial_ratio`.** One config line, the
  single biggest measured win (matched 23.8 → 35.0 opus, 19.4 → 31.2 gemini; F1 0.201 → 0.293).
  **REJECTED.** The config's stated reasoning survives scrutiny: token_set compares the shared-token
  intersection, so an invented org name sharing one token with the truth reads as a near-match, and
  the identifier veto covers alphanumeric designators only — it does nothing for prose org and site
  names, which is where this corpus's fabrication risk lives. This would report fabrication as
  recall on the one line the project cannot get wrong.
- **Make the model emit explicit singleton clusters so `referent_id` is never `None`.** The most
  tempting fix of all — 0.35 → ~0.80 without touching the scorer. **REJECTED.** It is worse
  extraction: it multiplies output tokens by the mention count, and it destroys the distinction
  between "the model declined to bind" and "the model bound a singleton" — the abstention signal
  this system is built on. The defect is in how the scorer reads absence.
- **Stamp `referent_id` onto relationship claims via their endpoints**, making the 35 triple-form
  gold rows scoreable. **REJECTED.** It asserts that a two-mention claim has one referent, which the
  design explicitly and correctly refuses, and it would make the ANTI_COREF sign inversion bite far
  harder since the trap clusters are triple-heavy. It buys score by weakening the data model.
- **Rewrite the prompt so `name` carries the full mention noun phrase** ("a battery-level deployment
  reportedly designated HQ-9/P" instead of "HQ-9/P"). Would take `entity:variant` 0/4 → 4/4.
  **REJECTED**, and this is the clearest case: the bare designator is the *better* answer for every
  downstream consumer — entity resolution, the graph, the node label an analyst reads. This trades
  product quality for benchmark score.
- **Teach the model the gold's vocabulary** — the registry's licensing-category names
  (`ANTI_COREF (stated enumeration)`), the discriminator phrasing conventions (`"Origin: Tianjin
  Xingang"`, `"Karachi (city precision only)"`), or "prefer `observed-at` over `SightingEvent`".
  **REJECTED.** These are annotator bookkeeping labels. Teaching our label taxonomy raises agreement
  without improving one binding or extraction decision on a document no annotator has touched.
- **Lower `role_min_similarity` / `pair_min_similarity`, or the 0.85 grounding floor.**
  **REJECTED on measurement alone**: 0.70→0.55 buys **+0** matches, 0.80→0.65 buys **+1**. It is
  threshold-shopping against observed near-misses and it weakens the kernel's fabrication resistance
  for essentially nothing. Show anyone reaching for this those two numbers.
- **Cap emissions / instruct the model to be terse.** Raises precision directly; fastest route to a
  better F1. **REJECTED emphatically** — it optimises for extracting *less* from a document, which is
  the opposite of what an OSINT extractor is for, and `matcher.py`'s own docstring names this bias
  as the reason precision exclusions exist.
- **Narrow the ref span for social-media author entities so it stops overlapping `d20-r12/r13`.**
  Would move gemini 0.745 → 0.927. **REJECTED as stated** — "stop overlapping the traps" is fitting
  to the trap coordinates. (And per my correction above, the span comes from the *model's*
  `source_quote`, not our transform, so there is nothing on our side to narrow.)
- **Delete the 16 non-verbatim rows, or the two `d19` Sialkot rows, from the gold.** Tempting because
  the defect is already acknowledged. **REJECTED as a fix to any score** — it raises the reported
  number without changing anything about extraction, addresses ~14% of the surface gap while leaving
  the 45-point denominator problem untouched, and deleting the rows that expose the
  matcher/EOS contradiction hides it. State the 49/65 ceiling alongside the number.
- **Re-weight the composite now that we know which lines favour which model.** The CF/EOS
  double-count is real and worth fixing, but choosing new weights after seeing the outcome is
  result-fitting. Any re-weighting must be justified structurally (one grounding check, one weight)
  and fixed *before* the next run.
- **Add "do not create entities from abstract nominalizations" to the system prompt.** This is a
  *legitimate product improvement* — but shipping it between measurement rounds converts the next
  bake-off into a measurement of our prompt patch. If it goes in, both candidates must be
  re-baselined and the change declared. (And see §2: on inspection those nominalizations are mostly
  faithful, so the case for it is weaker than it looked.)
- **Regenerate the two truncated opus `d05` calls and splice them in.** **REJECTED as a scoring
  action** — that is repairing one candidate's data after seeing its score. The repair belongs in the
  client; the effect belongs in this report as a measured counterfactual.

### C. Genuinely the gold's problem — belongs to the corpus authoring already in flight

Filed for the data agent; **not** actioned here, and the frozen corpus was not touched.

1. **The 15 `observed-at` rows are annotator-composed pseudo-triples**, several truncated mid-word
   (`d19-r08` object: `"the radar hardstand occupied and TEL count u…"`). Unreachable under *total*
   matcher relaxation (5/15 recovered with every knob at maximum leniency). This is the largest
   single unreachable bucket, 23% of the gold.
2. **`entity:known_gap` (7 rows) is an unnameable type.** A collection gap is described, not named;
   the gold composes labels and so do both models, and no lexical matcher can pair them. Either give
   the type a matching convention or exclude it from surface scoring and from `extract_only_stated`
   consistently.
3. **The two ANTI_COREF registry clusters sit in positive `claims`.** `d05-C4-events` and
   `d19-C4-othersites` must be routed to `negative_gold` under S6, or the S6 rule must learn to read
   registry-level cluster categories and not only row predicate class.
4. **`d05-r04/05/06` require an assertion the document does not make** — pairwise `distinct-from`
   between three GD numbers listed as three separate rows, never stated as distinct. The prompt
   forbids exactly this and so does the project's one hard rule. Both models correctly emitted the
   three `contract_import_event` entities (1.00 recall on that bucket) and correctly declined the
   unstated distinctness — and lost 3 gold rows for it. **Any model that scored these rows would be
   fabricating.**
5. **Trap `d05-r23`'s rationale is factually wrong about its own corpus** (the ORIENT identity-match
   is stated in full at lines 73–74).
6. **10 of 47 discriminator values carry annotator meta-annotation, column labels or joined field
   pairs**, violating the gold's own "the source's own words, copied" contract.
7. **The gold has no positive coref cluster with two entity-form claims.** If `coref_binding` is to
   be measured at all, the gold needs at least one cluster where a correct positive bind between two
   system-indexable claims can earn credit.
8. **65 curated rows cannot serve as a precision denominator.** Either exhaustively label the 7
   documents, or stop reporting precision-based F1 against them. This is a data investment and it is
   the honest answer.

---

## 4. What survives

**Almost nothing on the metrics as reported; three things on inspection.**

**Does not survive:**
- `coref_binding` — both models are trivially perfect at L4 on an empty denominator. UNMEASURABLE.
- `discriminator_capture` — different exams (21 vs 15–17 slots), on a field the prompt never
  requests. UNMEASURED. The one raw behavioural indicator that does not pass through our alignment
  gate — context fill rate — runs the *other* way (gemini 0.567, opus 0.374).
- `citation_faithfulness` — 79–91% locality artefact; strip it and it is `extract_only_stated`.
- `surface_f1` — the harmonic mean cancels a genuine recall difference against an artefactual
  precision one.
- `structured_output_reliability` — 1.000 for both, and blind to the failure that occurred.
- **`trap_avoidance` — the candidate finding, and it does not survive.** All 25 hits across 10 runs
  are span-overlap artefacts; **zero** are fabricated assertions. Under an assertion-bearing basis
  the gap falls from 0.127 to 0.018, and under a containment basis the ordering **reverses** to
  gemini 1.000 / opus 0.945. It should not have been functioning as a veto gate in this state.

**Survives, in descending order of confidence:**

1. **Opus reads more of each document; gemini is more conservative.** This is the most robust
   finding in the run and it is visible on four independent lines: `surface_recall` 0.3662 vs 0.2985
   (gap 0.068 vs margin 0.046), `graph_node_recall` 0.6000 vs 0.5308 (gap 0.069 vs margin 0.038),
   `graph_recall` 0.5050 vs 0.4550 (gap 0.050 vs margin 0.042), and raw emission volume 208 vs 149
   claims per run. Two of the four carry weight 0 and the composite cancels the rest against
   precision-shaped artefacts. **Whether "more" is "better" is a human judgement about whether you
   would rather triage extra grounded claims or miss them — this bake-off did not measure it, and
   should not pretend to.**

2. **Opus asserts more surfaces its cited document does not lexically contain.** Real, stable across
   all five runs, and inspectable — but roughly half of it is our instrument. 4.53% vs 1.49% as
   scored; 2.80% vs 1.22% once the unnameable `known_gap` type is removed; 2.31% vs 0.54% once the
   rows our own matcher scored *correct* are also removed. The direction holds at every peel. The
   residual mechanism is opus minting composite nominal labels out of analytic prose — mostly
   faithful on inspection, but they become junk nodes an analyst has to triage away, so it is worth
   knowing even though the metric as reported exaggerates it.

3. **Opus's coreference channel is materially more productive and has more range.** Over 35 pass-2
   calls each: opus proposed **99** clusters using all three licensing categories
   (EXPLICIT_EQUIVALENCE 62 / NAME_VARIANT 27 / UNAMBIGUOUS_ANAPHOR 10); gemini proposed **65** using
   effectively one (63 / 2 / **0**). Gemini attempted **zero** anaphoric binds — "the site", "the
   export agency" — which is precisely the descriptive/elliptical reference this pass exists to
   rescue and that RESOLVE can never recover downstream. On the real corpus that is a meaningful
   capability gap in opus's favour, and it is completely invisible at 0.3511 vs 0.3658.

4. **A minor but clean provenance difference:** opus cites the byline for a social-media author
   entity, gemini cites the post body. Opus's is the better provenance. `trap_avoidance` currently
   scores this as fabrication and gets the sign wrong.

**One strong positive result the shipped scorecard completely conceals:** once the singleton
convention is applied, B³ **precision is exactly 1.000 for both models in all 10 runs**. Neither
over-merged a single graded pair — including on the two planted over-merge traps. Both models
behaved exactly as the prompt's COST RULE asks. The scorecard reports that as 0.35.

**And a false finding avoided.** The one place a model difference surfaced in the raw numbers —
opus's ±0.088 variance on the top-weighted metric against gemini's ±0.024 — was not a model
difference at all. It was our client swallowing two truncated payloads. Reported as-is it would
have become a claim about opus's stability.

**Bottom line for the next round:** re-running models against this instrument would measure our
scorer. Fix §3A first, hand §3C to the corpus work, and refuse every item in §3B.
