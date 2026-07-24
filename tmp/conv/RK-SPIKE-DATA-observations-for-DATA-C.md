# RK-SPIKE data-hand observations → DATA-C / EVAL

From: the independent DATA hand on `spike/rk-data` (RK-SPIKE, 2026-07-24)
Full detail: `tmp/spike-rk/gold/DATA-FINDINGS.md` (§5). Gold slice: `tmp/spike-rk/gold/claim-gold.md`.

**Nothing was changed.** `corpus/**`, `config/*.yaml`, `answer_key.json` and `SCENARIO_MANIFEST.json` are
untouched. These are observations from hand-labeling seven documents claim by claim, filed for your call.

---

## 1. MATERIAL — the oracle carries none of `d05`'s content, and it changes how a slice can be scored

`answer_key.ground_truth` (hq9p_primary) has **no `trading_org` node at all** and **one**
`contract_import_event` (`import_2021`, *"China→Pakistan HQ-9/P transfer"*, `evidence_date: 2021`).

`d05_customs_manifest` states, in a primary record:

- **three** distinct declarations — `KPQA-HC-2020-118834`, `-118835`, `-119011` — dated **November 2020**,
  each with its own waybill number;
- **three** identifier-backed orgs: the consignee `ORIENT ELECTRO TRADING (PVT) LTD` (`NTN 3298761-4`),
  the shipper `SINO-GALAXY IMP/EXP CO. LTD` (four surface forms), the forwarder `AL-NOOR CARGO SERVICES`
  (`AEO Cert No. PK-AEO-0231`);
- a registry-backed **rename**: *"formerly ORIENT ELECTRONIC TRADING CO -- name change ref SECP CUIN
  0087762, 2019"*.

`config/ontology.yaml` documents d05's three bills at length as the hard-attribute rail, and `md/17` lists
d05's demo value as *"relational (not string) resolution shell → HT-233"* — so the corpus and the ontology
both treat this content as load-bearing while the ground truth does not represent it.

**Most likely explanation:** the 18-node oracle is deliberately hero-trace scoped, and this is not an
error. **But the measurement consequence is real:** any bake-off slice containing `d05` scored against the
full oracle counts everything correct an extractor reads out of the manifest as noise, and counts
`import_2021` as a miss on a document that never mentions it. That is the concrete argument for using the
per-slice sub-oracle (`tmp/spike-rk/gold/sub-oracle.json`) for graph-recall rather than
`answer_key.ground_truth`.

**Ask:** confirm whether the omission is intentional scoping. If it is, no change needed — but the
bake-off scorer must not use the full oracle for slice recall.

---

## 2. MATERIAL — the flagship `distinct-from` is `confirmed` on one hedged grade-C source, and the corpus contains a grade-B source blurring it

`answer_key.ground_truth` marks `distinct-from var_hq9p ↔ var_hq9be` as `confirmed`
(*"flagship: ~125km Army vs ~260km PAF"*).

- The **only** evidence is `d04_armyrec_ranges` — `trade_media`, grade **C** — and the source hedges:
  *"the Army and PAF systems appear to be genuinely separate procurement lines rather than a single system
  fielded twice"*.
- Meanwhile `d19_rahwali_confirm`, grade **B**, states *"HQ-9BE (export variant, sometimes rendered HQ-9P
  in Pakistani service literature)"* and warns of *"continuing inconsistency across open sources in how
  Pakistani service designators map to the PLA domestic HQ-9B baseline versus the CASIC export HQ-9BE
  marketing designation"*, adding that the digest uses "HQ-9B" **generically**.

So a higher-grade document blurs precisely the designators the oracle confirms as distinct. A system that
surfaces this as a flagged contradiction held for an analyst is behaving *correctly* against the design and
will read as a failure against the key.

**Ask:** worth a look alongside the earlier answer-key-grounding pass — either soften this edge's status,
or record explicitly that `d19`'s designator language is expected messiness that must not defeat the
flagship wall. Not something the spike should decide.

---

## 3. FYI, no action requested — three observations that look intentional

**3a. Three irreconcilable induction dates for one designator, none reconciled by any document.**
`cs01` says officials called it *"already inducted in limited numbers"* **in 2013**; `d04` (Oct 2021) says
*"Nearly three years after induction was first confirmed by open-source imagery"* (≈2018-19); `d02` says
formally inducted **2021-10-14**. Plausibly three different events (limited delivery / first imagery
confirmation / formal induction), which would be good realistic messiness — but nothing says so, and the
oracle carries a single `evidence_date: 2021`. If it is intended, the design note should own it.

**3b. `d17b`'s location description is internally inconsistent — and should probably stay that way.**
Subject line *"Air Defense Infrastructure, Southern Approaches"*; the site's only name is *"the old
Rawalpindi-area site" near the port road turnoff*. Rawalpindi has no port road, and "port road" is a
Karachi feature elsewhere (`d08`, `cx01`). This looks deliberate: `d17b` is quoting forum reporting, and
`d20` shows the spoof itself conflating *"the old Rawalpindi site"* (post 1) with *"the port road area"*
(post 4, a retweet of post 1). **Flagging it so a later tidy-up pass does not "fix" it into coherence** —
that would destroy the deception beat. The consequence to preserve is that this site's geography
discriminator is *unusable*, not merely coarse.

**3c. `cs01` carries the same CPMIEC-as-manufacturer conflation as `d23`.** *"claimed by the manufacturer,
China Precision Machinery Import-Export Corporation (CPMIEC)"* — a clean apposition binding to a role
`d22` refutes. Presumably intentional (a second instance of the conflation in a *stale* document rather
than a *low-grade* one, so refutation works on a different axis). Recorded because a slice containing
`cs01` without `d22` will carry a claim the full corpus knows to be false.

---

## 4. Coverage recommendations for RK-DATA (findings only — not started here)

These substantiate plan §10's coverage list from the data side. Both are **authoring** tasks; neither was
begun.

**4a. The §B6 ORBAT gap is confirmed, more comprehensively than the plan assumed.** A corpus-wide grep for
numbered formations across all 52 documents returns **one** hit — `11 Signal Regiment`, a British Army
signals unit in the off-subject chaff document `cd07`. A corpus-wide grep for `based at` / `based in` /
`garrisoned at` / `stationed at` returns **the same single hit**. There is **no** stated formation-at-site
basing for HQ-9/P or HQ-9B anywhere. `answer_key.json` agrees in its own words: every `based-at` edge is
`"basis": "derived"`, and the Karachi edge's note reads *"DERIVED edge — no document states a named unit at
a named site."*

When the §B6 document is authored, the corroborating source should **name the same designator**, because
designator continuity is the only non-perishable discriminator in the design's ladder and nothing in the
corpus currently supplies one.

**4b. The OOB-undercount trap needs authoring — two *individuated* same-type formations that must not
merge.** The corpus has that shape at import-event level (`d05`'s three declarations), at site level
(`d19`'s Sialkot + Pasrur, licensed by an explicit *"both"*) and at design level (`d04`), but **never at
formation level**. The nearest approach is `d17`, which raises it as an uncertainty rather than as two
mentions: *"Number of fire units co-located at Nur Khan remains uncertain; only one revetment cluster has
been positively resolved in the current pass set"*. Excellent for the honest-gap surface, useless as an
anti-merge test.

Also worth knowing: **no serial, hull, tail or registration number appears anywhere in the corpus** (grep
returns zero), and five documents state the absence of unit markings/designators explicitly. So the
discriminator ladder's top rung has no data to fire on, and "formation identity unresolved" is currently
the only honest outcome available rather than a conservative choice.
