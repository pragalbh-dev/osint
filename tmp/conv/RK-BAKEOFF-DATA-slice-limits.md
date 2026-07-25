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

**125 hand-labeled claim rows.** 108 positive-gold, plus 17 negative-gold (11 `NOT_A_CLAIM:`, 6
`ANTI_COREF:`), plus 19 `UNMODELLED:` rows recording things the ontology cannot express, plus 2
`AMBIGUOUS:` pairs. 27 rows are negative-polarity. Every row carries a verbatim span and a line number —
verified 125/125 on 2026-07-25.

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

**(d) One mechanical trap.** 13 of the 120 mention strings carry an annotator locator — "(Post 3)",
"(this report's AOI)" — and are therefore not byte-verbatim. A scorer doing exact-match without stripping a
trailing parenthetical will mark 11% of the coref gold unmatchable and blame the model. Documented in
`claim-gold.json` → `mention_verbatim_note` (added 2026-07-25). With that one normalization, 120/120
mentions and 120/120 licensing quotes are verbatim.

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
