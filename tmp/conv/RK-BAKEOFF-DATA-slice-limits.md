# RK-BAKEOFF — what the gold slice can and cannot measure

**For the design note and for whoever sets the bake-off scoring weights.** Written 2026-07-25 by the DATA
hand, from a full pass over `tmp/spike-rk/gold/claim-gold.json` (+ `.md`), `sub-oracle.json` (+ `.md`) and
the seven cited corpus documents. Everything below was measured, not recalled.

---

## 1. What the slice is

**Seven documents** out of the frozen corpus's 51 (36 files in `hq9p_primary`, 30 in `hq9p_chaff`;
51 documents once the image/geo sidecars are folded into their parent doc):

| Doc | Class | Grade | Bias | Date | Rows |
|---|---|---|---|---|---|
| `d02_ispr_induction` | official (press release) | B | operator-state | 2021-10-14 | 16 |
| `d04_armyrec_ranges` | trade-media | C | third-party | 2021-10 | 18 |
| `d19_rahwali_confirm` | think-tank / reference | B | third-party | 2025-04-04 | 20 |
| `d05_customs_manifest` | customs-tender (structured/tabular) | C | commercial | 2020-11 | 24 |
| `d17b_withheld_gap` | satellite / IMINT read-out | B | third-party | 2025-06-11 | 15 |
| `d20_supersede_spoof` | named-social (adversary, decoy-flagged) | E | adversary | 2025-06 | 16 |
| `cs01_stale_orbat` | reference, stale-as-current (chaff) | C | third-party | 2015-06 (page 2013-03) | 16 |

**125 hand-labeled claim rows**, which split as follows (corrected 2026-07-25 against the gold adapter's
reconciliation — the earlier "108 positive-gold" line in this section did not sum to 125):

| Bucket | Rows | Scored? |
|---|---|---|
| claim-shaped positive gold (entity / triple / event) | **65** | yes — this is the recall denominator |
| `ATTR:` attribute rows | 22 | no — the scorer's comparison unit has no attribute form |
| `NOT_A_CLAIM:` traps | 11 | yes, inverted — emitting one is a fabrication |
| `UNMODELLED:` (ontology cannot express it) | 19 | no — neutral, a finding about the ontology |
| `ANTI_COREF:` must-not-bind pairs | 6 | binding only, and only once S3 lands |
| `AMBIGUOUS:` unresolved pairs | 2 | identity-assertion only |

27 rows are negative-polarity; 13 rows are polarity `unknown` (all `NOT_A_CLAIM:`/`AMBIGUOUS:`, i.e. never
scored as claims). Every row carries a verbatim span and a line number — verified 125/125 on 2026-07-25,
and re-verified through the adapter: 125/125 spans resolve to char offsets that slice back to the quoted
string (122 byte-exact; the 3 others differ only by whitespace collapse inside `d05`'s fixed-width table),
and 125/125 start on the line the gold states.

**Loading all 125 rows as positive gold would cap a perfect extractor at 65/125 = 0.52 recall.** Measured
through the real scorer (re-derived independently by the integration hand, 2026-07-25): a candidate
emitting exactly the 65 positive-gold claims scores recall **1.0000** via `eval.gold.adapter` and
**0.5200** via a mechanical 125-row load. Anyone re-deriving the denominators must keep the negative gold
typed and out of the recall denominator, or the bake-off charges every candidate **0.48** recall for a
loader artefact.

> **Do not quote 0.6960 as "the" naive ceiling.** That figure is real but describes a *different*
> candidate — one that also emitted the 22 attribute rows (87 = 65 + 22). Those rows are excluded from
> scoring precisely because the pipeline cannot express an attribute as a claim, so 0.696 credits a model
> that cannot exist and understates the artefact by 0.18 recall. Both figures are now asserted separately
> in `tests/gold_adapter/test_negative_gold_semantics.py` so neither can displace the other.

**Six document types, one document each of most of them.** That is the first and largest limit: for five
of the six source classes the slice has **N=1**, so "the model handles social media badly" and "the model
handled *this* social-media document badly" are the same observation.

---

## 2. The headline question: can `coref-binding accuracy` be measured on this slice?

**Yes — within a document, and only there.** This *corrects* the working assumption that the frozen corpus
carries zero coreference annotation. That is true of the corpus and of `answer_key.json` (0 occurrences of
"coref" in either scenario key). It is **not** true of the bake-off gold: the RK-SPIKE data pass hand-built
a coref registry inside `claim-gold.json`. Measured:

- **32 curated clusters, 120 mentions**, spread 5/5/5/5/3/5/4 across the seven documents.
- 30 of the 32 are multi-mention (2 are single-mention, i.e. nothing to bind).
- Each cluster carries a **licensing category** and a **licensing quote**, so a scorer can ask the sharper
  question — did the model bind for the *right reason* — not merely did it bind.

So the highest-weighted scoring line is measurable. But the number it produces is thinner than it looks,
and the thinness is not uniform:

**(a) Per-category N is single-digit.** Pure `UNAMBIGUOUS_ANAPHOR`: 5 clusters / 25 mentions. Pure
`EXPLICIT_EQUIVALENCE`: 5 / 18. Pure `NAME_VARIANT`: 3 / 9. `AMBIGUOUS` (the rows the project cares most
about): 5 / 15. The remaining 14 clusters are compound categories. **A per-category accuracy figure on
three clusters is not a measurement**, and given re-extraction is already confirmed non-deterministic, a
one-cluster swing between runs moves a "NAME_VARIANT accuracy" number by 33 points. Report the aggregate;
do not report per-category rankings.

**(b) The error direction the project fears has the smallest denominator.** Over-binding — fusing two
referents that must stay apart — is scored against **6 `ANTI_COREF:` rows and 2 `AMBIGUOUS:` rows: eight
items total**. Recall of binding is measured on 120 mentions; precision of binding is measured on 8. A
candidate that binds aggressively will look good on this slice out of proportion to how good it is.

**(c) Cross-document coreference is not measured at all — there is no gold for it.** Every one of the 32
clusters is doc-local. The nearest thing is the sub-oracle's node-level `surface_forms` (e.g. `sl_var_hq9p`
lists 11 surfaces across 4 documents), but that is **entity resolution**, a different mechanism owned by a
different stage. If the bake-off calls its cross-document result "coref", it will be mislabelling what it
measured.

**(d) One mechanical trap — and the naive fix for it over-corrects.** Mention strings carry an annotator
locator ("(Post 3)", "(this report's AOI)") and are therefore not byte-verbatim; a scorer doing exact match
without stripping a trailing parenthetical will mark part of the coref gold unmatchable and blame the model.
Documented in `claim-gold.json` → `mention_verbatim_note` (added 2026-07-25). Two numbers in that note are
off, measured through the adapter on 2026-07-25 (**labels unchanged — reported, not fixed**):

- **12 mentions carry a locator, not 13.** A purely syntactic trailing-parenthetical strip fires on 20 of
  the 120, and 8 of those parentheticals are genuine document text — `PORT MUHAMMAD BIN QASIM (PQ)`,
  `the FT-2000 (sometimes rendered FT-2000A)`, `Baseline imagery (2024-11)`. Stripping those truncates a
  correct mention into an unmatchable one, i.e. the same harm the note warns about, pointed the other way.
  `eval.gold.adapter.strip_annotator_locator` therefore strips only when the annotated form does not occur
  in its document.
- **119/120 mentions are verbatim after that strip, not 120/120.** The 13th item the note counts is
  `d17b-AMBIG-1`'s Telegram caption, which is not a locator case at all: it differs from the document only
  in whether the comma sits inside or outside the closing quotation mark (`imagery pending,"` in the
  document vs `imagery pending"` in the label). The adapted registry flags it with
  `verbatim_in_document: false` so an exact-match scorer sees it is unmatchable instead of charging the
  miss to a candidate. 32/32 licensing quotes *are* verbatim — that half of the note checks out.

---

## 3. Mechanisms the slice **cannot** exercise at all

Each of these is a hole, not a weakness — no score on this slice says anything about them.

1. **The VLM imagery path — which is a pass/fail GATING precondition of the bake-off.** All seven slice
   documents are plain text. `d17b_withheld_gap` has a real `.png` beside it and the corpus carries eight
   more images and a PDF (`d25_hq9_site_fingerprint.pdf`), but the gold labels the **text read-out only**.
   So the slice **cannot test the one capability whose loss disqualifies a candidate outright.** That gate
   must be verified by a separate, deliberate imagery check; it must not be inferred from a slice score.
2. **Coreference across documents** — see §2(c).
3. **Serial / registration / tail-number reasoning.** Zero equipment or unit serials anywhere in the seven
   documents (grepped). The **only** hard identifiers in the slice are commercial and all sit in one
   document: `d05`'s NTN, SECP CUIN, AEO certificate, three GD numbers, three B/L numbers, an invoice
   number. Identifier-driven resolution *is* exercisable — in the customs lane, on one document.
4. **Numbered or designated formations.** The `unit` type in the slice holds exactly two things, and
   neither is individuated: an *unnamed* "Pakistan Army Air Defence (PAAD) unit" and a *cardinality* ("two
   operational battalions"). Everything else is a service or a command — "PAF", "Air Defence Command",
   "Central Air Command". So the order-of-battle discriminator lane — the thing that keeps two batteries
   from collapsing into one — is untestable here. Five of the seven documents state the absence explicitly.
5. **Two same-type FORMATION instances that must not merge.** The corpus has the must-not-merge shape at
   *site* level (d19's Sialkot/Pasrur), *event* level (d05's three declarations) and *design* level (d04's
   two variants) — never at formation level. The OOB-undercount trap is not authored.
6. **A stated formation-at-site basing.** No slice document — and, on a corpus-wide check, no document at
   all — names a designated formation and the site it is based at. Every `based-at` is derived.
7. **Corroboration to `confirmed` at instance level.** There are **no two genuinely independent sources on
   one instance** inside the slice. After the 2026-07-25 repair the sub-oracle carries six `confirmed`
   entries and every one is either **design-layer identity** (the HQ-9/P designator, the HQ-9 family, the
   TEL component type) or a **known-gap node**. Not one is a presence, a formation or a site occupancy.
   A bake-off score on this slice therefore says nothing about whether a candidate feeds the
   confirmed/probable machinery correctly on the claims that actually matter operationally.

---

## 4. The honest paragraph (drop-in for the design note)

> The extractor bake-off was scored on a seven-document, 125-claim hand-labeled slice of the frozen corpus,
> chosen for structural difficulty rather than volume: it carries dense within-document coreference, an
> identifier-backed customs table, a stale-as-current chaff reference, an adversary-grade social document
> and a satellite read-out that correctly refuses to resolve its own ambiguity. Because the slice is
> deliberately hard, a score on it is a reasonable proxy for *reading* quality — did the model bind the
> right mentions, quote the right span, and decline to assert what the page does not say. It is **not** a
> proxy for system quality, and three limits are worth stating plainly. First, five of the six source
> classes appear exactly once, so any per-class figure is an anecdote. Second, the slice's coreference gold
> is entirely **within**-document (32 clusters, 120 mentions); cross-document identity is entity
> resolution, a different stage, and is not measured here — and over-binding, the error the system is built
> to fear, is scored against only eight negative-gold items against 120 positive ones. Third, and most
> important, the slice is text-only: it cannot exercise the imagery/VLM path at all, and that path is a
> pass/fail precondition rather than a weighted line, so it was verified separately and never inferred from
> a slice score. Nor can the slice test unit serials, designated formations, formation-level anti-merge or
> corroboration-to-confirmed at instance level, because the frozen corpus contains none of those shapes —
> which is itself an honest finding about the corpus, recorded rather than papered over.

---

## 5. Consequences for the bake-off stage (recommendations, not decisions)

- **Do not let the slice stand in for the VLM gate.** Run the imagery precondition as its own pass/fail
  check on at least `d17b_withheld_gap.png` and `d25_hq9_site_fingerprint.pdf`.
- **Report coref binding as one aggregate number with its variance**, not as a per-licensing-category
  table. N is too small per category for a difference to be called material.
- **Weight binding precision explicitly**, or state that it is measured on eight items. Otherwise an
  aggressive binder wins the line it should lose.
- **State the minimum material margin before running**, in coref points, and hold to it. With N=32 clusters
  and confirmed run-to-run non-determinism, small gaps are jitter and must be reported as
  "no measured difference".
- **Read absolute recall against the slice's own ceiling, not against 1.00.** 16 of the 65 scored claims
  carry a role surface that appears nowhere in their document, because the gold labels a *resolved* subject
  ("HQ-9/P" where the sentence says only "was formally inducted…") or an annotator's composition ("The
  missile itself / the HQ-9/P"). No extractor quoting the document can produce those strings, so those pairs
  live or die on the matcher's fuzzy tolerance. Only 34 of 65 have every role surface quotable from the
  claim's own cited span. Counts are carried in the adapted file as `surface_verbatimness`. The labels are
  defensible for a *claim* gold and were left alone — stripping the annotator sugar would truncate the
  surfaces that genuinely are document text.
- **Three of the four negative classes are declared neutral and are not neutral until the harness wires
  them.** Precision is `matched / extracted`, so any unpaired claim costs the candidate whatever span it
  sits on. That is correct for `NOT_A_CLAIM:` and wrong for the other three. **Measured through the real
  matcher (integration hand, 2026-07-25), not estimated:** a candidate emitting the 65 positive claims
  plus all 27 neutral-class spans scores precision **0.7065** where the wired figure is **1.0000** — an
  unearned loss of **0.2935**, and **0.2262** for the 19 `UNMODELLED:` rows alone. The earlier "up to 11
  precision points" in this note was wrong on every construction; the real number is roughly three times
  that. It also does **not** cancel between candidates: the penalty scales with how much of each document
  a model reads, so an unwired exclusion actively favours the terser extractor — the opposite of what the
  bake-off selects for, and it lands on `surface_f1` (weight 3.0). `eval.gold.adapter` ships the hooks
  (`trap_avoidance`, `identity_over_read`, `precision_exclusions`); nothing calls them, and §5 of the
  rendered scorecard now says so on every run.
- **Do not score a trap by span overlap alone.** Trap `d20-r13`'s span overlaps positive claim `d20-r14`'s,
  so a bare overlap test charges a fabrication to a model that read `d20-r14` correctly. A trap hit requires
  the claim to be *unpaired* against the positive gold as well as overlapping. Separately, the existing
  `extract_only_stated` metric does **not** catch trap emissions (measured: 9 of 11 trap spans read as
  "supported", because the trap text really is in the document) — which is exactly why the typed
  `not_a_claim` class is carried rather than folded into the lexical fabrication line.
