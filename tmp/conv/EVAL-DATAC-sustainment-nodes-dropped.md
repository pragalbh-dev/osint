# EVAL → DATA-C: the two sustainment oracle items are removed from `hq9p_primary` answer_key

**Status:** applied on branch `fix/phase4-derived-and-surfaces` (worktree `wt-EVAL`), **uncommitted**.
**Scope of edit:** `corpus/scenarios/hq9p_primary/answer_key.json` only. `config/ontology.yaml` and
`config/subjects.yaml` were deliberately **not** touched — see §5.

Ratified by the orchestrator after investigation. The two items failed for **opposite** reasons and the
fixes are different: one is a corrected over-claim in the key, the other is a real (deferred) code gap.

---

## 1. What was removed

**Nodes**

| id | type | why removed |
|---|---|---|
| `sustain_spares` | `interceptor_stockpile` | the corpus **explicitly denies** it (§2) |
| `sustain_techdata` | `techdata_authority` | the corpus **states** it; we don't extract it (§3) |

**Edges**

| edge | why removed |
|---|---|
| `unit_paad --sustained-by--> sustain_spares` | object node gone; also a cross-service attachment (PAF tender → Army unit), which the key's own note already called "nominal" |
| `sustain_techdata --design-authority-for--> var_hq9p` | subject node gone; also wider than the source supports (§3) |

**Other references rewritten (no dangling ids anywhere in the file):**

- `worked_query.expected_path_edges_note` — struck the `+ sustain_techdata design-authority-for var_hq9p`
  clause. CASIC-as-program-prime via `mfr_casic manufactures var_hq9p` is grounded and stays.
- `flexes.single_source` — **re-pointed** from `d06_spares_tender` to `d17_rawalpindi_2021` (§4).
- `flexes.adversary_denial_bypass` and `documents[d16_adversary_denial].expect.note` — both said the denial
  fails to "downgrade the techdata dependency". Reworded to the generic form (an adversary-bias denial
  corroborates nothing and moves no standing assessment) so nothing points at a removed id.
- `documents[d21_techdata_authority].expect` — rewritten to what d21 actually contributes, plus a
  `known_limitation` (§3).
- `documents[d06_spares_tender].expect` — rewritten to the contract_import_event + line items, with the
  explicit "does NOT establish a stockpile" note carrying the verbatim tender language (§2).

**Verification run after editing:** `json.load` parses; `grep sustain_spares|sustain_techdata` over the whole
file returns nothing; every `edges[].from/to` resolves to a declared node id **except** the pre-existing
`same-as` edge whose `from` is the literal string `"FD-2000"` rather than a node id — that predates this
change and is untouched.

---

## 2. `interceptor_stockpile` — the extractor was RIGHT, the key over-claimed

Verbatim from `corpus/scenarios/hq9p_primary/docs/d06_spares_tender.txt`:

> §1.1 "The requirement pertains solely to sustenance/repair-and-overhaul (R&O) support of equipment
> already fielded and **does NOT constitute procurement of a new weapon system, launcher, missile round, or
> fire-control radar**."

> §2.3 "It is reiterated that this tender is raised under the recurring Annual Maintenance Support Contract
> framework and pertains to sustenance of equipment already inducted into service. **No new launcher units,
> radar sets, or missile rounds form part of this requirement.**"

Verbatim from `docs/d01_sipri_transfer.txt` (the only other mention in the corpus):

> "However, force-level specifics (unit count, **missile stockpile**, precise siting, contract value)
> **remain unconfirmed in the open literature and should not be treated as established fact** pending an
> authoritative primary disclosure."

None of the `StockpileMention` attrs (`stocked_round`, `magazine_depth`, `consumption_rate`,
`days_of_supply`, `resupply_lead_time`) appears anywhere in the corpus. The tender-lane emitter
(`extract.py`, the `stock = _obj(filled, "stockpile")` block) gates on exactly those fields, so it correctly
emits nothing.

**Conclusion: no code change. Do not "fix" this.** Minting a stockpile node from a maintenance contract is
inferring force posture from an R&O requirement — the fabrication the non-negotiable forbids. The extractor
declining is the system working. The oracle was the thing that was wrong.

---

## 3. `techdata_authority` — a real, mundane extraction gap (deferred)

`docs/d21_techdata_authority.txt` **does** state it:

> "…radar mode libraries, waveform parameters and calibration tables are not locally modifiable by end-user
> technical staff; rather, updates and re-certification **are said to be routed through a Chinese state
> technical-data authority, understood to sit within the broader CASIC/CPMIEC export administrative chain,
> which retains configuration control over the underlying software baseline**."

d21 routes to the `prose_claim` lane (`classify_form` default for analytic prose). `TechDataMention` exists
in `backend/chanakya/ingest/extract.py:319`, but it is only reachable from `TenderProcurement` — `ProseClaim`
(`extract.py:247`) has no such field. The model had **nowhere to put the fact**, so nothing is emitted.

### The exact 3-step fix

1. **Schema** — `backend/chanakya/ingest/extract.py`, `class ProseClaim` (~:247): add
   `techdata_authority: TechDataMention | None = None` alongside `denials`. `TechDataMention` is already
   defined above it (`name`, `holds`, `foreign_control`, `source_quote`), so no new model is needed.
2. **Prompt** — `_SYSTEM_PROMPTS["prose_claim"]` (`extract.py:463`) is currently just
   `_SYSTEM_BASE + " This is analytic or official prose."`. Append a clause in the same
   record-what-the-source-states register, e.g.: *"When the source states that software, firmware,
   calibration tables, technical data packages or configuration control for the system are held or
   controlled by a named external/foreign authority, record that authority in `techdata_authority` — its
   name as stated, what it holds, and the stated control arrangement. Record it only when the source
   asserts it; do not infer it from the presence of a foreign OEM."*
3. **Emitter** — `transform_prose_claim` (`extract.py:1071`): copy the `td = _obj(filled,
   "techdata_authority")` block verbatim from the tender transform (`extract.py:~1355`), placing it before
   the `_emit_relations(...)` call, unchanged:

   ```python
   td = _obj(filled, "techdata_authority")
   if td and (_str(td, "name") or _str(td, "holds")):
       tname = _str(td, "name") or "technical-data / calibration authority"
       tref = _resolve_doc_ref(loaded, _str(td, "source_quote"), fallback=tname)
       em.entity("techdata_authority", tname, tref, attrs={
           "holds": _str(td, "holds"), "foreign_control": _str(td, "foreign_control"),
       })
   ```

   Note the Phase-4 boundary comment on the tender block still applies: **nodes only**, no `sustained-by` /
   `design-authority-for` edge is minted at ingest — the rollup is SCORE's derived synthesis.

### Re-record

The fix is deferred because it needs a keyed re-record of a frozen bundle:

```
python -m chanakya.ingest extract --scenario hq9p_primary --only d21_techdata_authority
```

Run from the repo root with the extraction keys loaded from `osint/.env` (`GEMINI_API_KEY` /
`ANTHROPIC_API_KEY`). **Withhold `AZURE_*` from the environment for this run** — the recorder resolves
whichever client the environment offers, and the frozen bundles must stay on the pinned
`gemini-flash-latest` lane to remain byte-stable/diffable against the checked-in baseline. The CLI exits
non-zero rather than fabricating if no key is present. Diff the regenerated
`corpus/scenarios/hq9p_primary/claims/d21_techdata_authority.json` before accepting it — a re-record can
move unrelated claims in the same bundle.

### Caveat — do NOT restore the oracle edge on faith

Even with the fix landed, `sustain_techdata --design-authority-for--> var_hq9p` **may still not
materialise**, for two independent reasons:

- **Scope mismatch.** d21 scopes the configuration control to the **HT-233 engagement radar**, but
  `config/ontology.yaml:109` types `design-authority-for` as `techdata_authority -> variant`. The oracle
  edge is *wider than the source supports*. A faithful record needs a component-scoped lane
  (`techdata_authority -> component`), which is an ontology change, not an extraction change.
- **Edge ownership.** The edge is a SCORE-side rollup, not an INGEST emission. A `techdata_authority` node
  appearing does not by itself produce the edge.

So: **land the fix, re-record, then look at what the view actually contains, and only then decide whether an
oracle entry is warranted — and at what scope.** Do not re-add the removed edge pre-emptively. Adding an
expectation the pipeline cannot satisfy is exactly the failure mode this change is correcting.

---

## 4. The `single_source` flex re-point

It expected "`sustain_spares` stays PROBABLE (single source)", which is unreachable now. Rather than delete
the flex (single-source-does-not-confirm is a genuine graded behaviour worth demonstrating), it was
re-pointed to **`d17_rawalpindi_2021`**, verified single-source by claim support:

Across all 29 bundles in `corpus/scenarios/hq9p_primary/claims/`, the triple
`unit_hq9b --based-at--> site_rawalpindi` is asserted by exactly **one** bundle
(`d17_rawalpindi_2021__basing.json`), and the supporting observations `HQ-9B observed-at PAF Base Nur Khan`
/ `HQ-9B fire unit observed-at PAF Base Nur Khan` come only from `d17_rawalpindi_2021.json`. (Contrast
`unit_hq9b --based-at--> site_rahwali`, which has two: d18 + d19.)

New expectation: d17's **observed** layer is confirmed-as-of-2021 on a multi-pass read, while the
**attribution** layer (that `unit_hq9b` operates it — d17 reads equipment and names no unit designator)
stays **PROBABLE** and cannot be raised on this document alone. Same principle, actually reachable, and it
reuses the observed/attribution split the key already models on that edge.

Candidates considered and rejected: `mfr_4th_academy --supplies-component--> comp_interceptor` and
`mfr_23rd_ri --supplies-component--> comp_ht233` (neither appears as an extracted relationship claim
anywhere — re-pointing there would repeat the same over-claim); `mfr_taian --supplies-component-->
comp_tel_chassis` (genuinely single-doc/d24, but the key marks it **confirmed**, so it demonstrates the
opposite of the flex).

**Side observation for DATA-C, not fixed here:** the `deep_tier_confirmed` flex describes the Taian/Wanshan
chassis link as "multiply attested", but `Taian (Wanshan) special-vehicle works --supplies-component-->
TAS5380` appears in exactly one bundle (d24). The *confirmed* status is defensible on the evidence-gate
argument (one source directly naming supplier + component + relationship), but the "multiply attested"
wording is not supported by the claim data. Worth a look.

---

## 5. Why the two node TYPES stay declared

`config/ontology.yaml` still declares `interceptor_stockpile` and `techdata_authority`, and
`config/subjects.yaml` is untouched. This is deliberate and should not be "cleaned up":

The types are **schema designed, instances discovered** — correctly unpopulated because no source in this
corpus supports an instance. That is the extensible-ontology argument working as intended, and a declared
type with zero instances is a *stronger* demonstration than a type that was quietly deleted when the data
didn't cooperate. Removing them would weaken the claim.

---

## 6. Reviewer-facing counterpart

A disclosure was appended to `artifacts/md/16-design-note-disclosures.md` under **Analytic honesty**. That
text is written for the design note and therefore describes only **the system against the corpus** — it
makes no reference to the answer key, the oracle, ground truth, or eval scoring, which are internal
scaffolding reviewers have never seen. Keep that separation if the entry is edited: this note says
everything; the disclosure says only what the corpus supports and what the system does with it.
