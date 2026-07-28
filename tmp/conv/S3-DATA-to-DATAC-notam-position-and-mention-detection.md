# S3 DATA → DATA-C: two frozen-data observations from the identity pass (nothing changed)

From the independent DATA hand for **RK-COREF (S3)**, 2026-07-25, on `s3/rk-data`. Companion to
`tmp/spike-rk/s3-fixtures/S3-DATA-FINDINGS.md` §4f–§4g.

**I changed nothing.** `corpus/**`, `answer_key.json` and `SCENARIO_MANIFEST.json` are untouched. Both items below I
verified directly in the frozen text before writing this, and where a first pass overstated something I have said so.
Neither is a blocker for S3 — the fixtures work around both — so treat this as information, not a request.

---

## 1. GENUINELY MATERIAL — entity names are split mid-token across line boundaries in the fixed-width documents

A mention detector that works line-by-line over these documents will systematically under-detect **exactly the entity
names that matter**, and coreference operates on the mention inventory, so this is upstream of everything the identity
re-plumb does with those documents.

Verified instances:

| Where | What the text does |
|---|---|
| `hq9p_chaff/docs/cd04…:28-29` | `… FOR HOME  th` / `EATRE & DIRECT-TO-HOME …` — "home theatre" split **inside the word**, across the line break |
| `hq9p_chaff/docs/cs03…:30-31` | `… FOR GROUND` / `-BASED USE, SPARE AND ANCILL RY ITEMS …` — a compound split across the line **and** a letter dropped from the middle of "ANCILLARY" |
| `hq9p_chaff/docs/cs03…:56` | `Declared Descriptio n:` — the field label itself is split |
| `hq9p_chaff/docs/cd15…:48, :64` | a shipper's name line-wrapped, plus the `KHAIBER AGENCIES / KHYBER AGENCIES` alt-spelling pair |
| **`hq9p_primary/docs/d05…:73-74`** | `ORIENT ELECTRO TRADING PVT LTD (formerly ORIENT ELECTRONIC` / `TRADING CO -- name change ref SECP CUIN 0087762, 2019)` — **primary side**, and the split runs straight through a *stated name-change equivalence* with a company-registry reference |

That last row is the one I would look at first. It is a genuine, sourced identity relation between two company names,
backed by a registry number — the strongest identity evidence of its kind in the corpus — and the two forms are
separated by a line break inside the parenthetical that licenses them. Anything that extracts a licensing span
line-by-line loses it.

Related, same document family: **`cs03…:60` buries the subject's designator inside an opaque contract reference** —
`DP contract Ref# DPA/AD/HQ9-ph2/2010`. It is the **only** place in that document where the subject appears at all. A
tokenizer that splits on `/` surfaces it; one that does not never sees it. So whether that document contributes to the
subject at all depends on a tokenization detail.

**No fix proposed.** This is a property of faithfully rendered fixed-width customs output, not an error — the point is
that it constrains extraction rather than that it should be smoothed away. If the corpus is ever regenerated, knowing
that these splits are load-bearing (they are what the OCR-garble corruption class is *for*) is worth having in front of
you.

---

## 2. REPORTED WITH A CAVEAT — one aerodrome identifier is filed at two positions ~1,100 km apart

- `hq9p_chaff/docs/cd05_civ_notam.txt` files `OPKC` at `2452N06718E` (≈24.87 N, 67.30 E — Karachi) on four separate
  Q-lines.
- `hq9p_chaff/docs/cd16_pak_civ_notam.txt` files the **same** `OPKC` at `3358N07324E` (≈33.97 N, 73.40 E — the
  Islamabad/Rawalpindi area), lines 2 and 11 — and its `OPIS` fix (line 32, `3352N07323E`) sits ~11 km from that.

The wrong position lands in *the other of the two cities the subject's relocation question turns on*, so a geo-keyed
place resolver reading these Q-lines would place a Karachi aerodrome in Rawalpindi.

**The caveat, and it matters.** `cd16` is tagged in the answer key with `"corruption": ["code_string_noise"]`, is marked
`off_subject: true`, and its stated expectation is *"right country, zero materiality → no claim"*. So it is genuinely
ambiguous whether this mismatch **is** the intended noise or an unnoticed error — and while that expectation holds the
mismatch cannot reach the graph through claims at all. A first pass over this called it an untagged genuine error; that
was wrong, and I am correcting it here rather than filing an escalation.

**What is left worth knowing:** the risk is narrow and specific — any pass that reads chaff navigation-warning position
fixes as *place evidence* (rather than discarding the document as immaterial) inherits a 1,100 km place error into
exactly the geography the flagship question is about. Also worth noting alongside it: **zero of the 27 chaff documents
gives a grid, MGRS or decimal coordinate for any military object** — every chaff military site is a bare toponym, so
site resolution on that half has no geometric fallback, and one chaff post says why that hurts ("which village exactly,
it is a big district").

---

## Not filed, because already filed

- `site_type` free-text vocabulary → `S2-DATA-to-DATAC-site-type-vocabulary.md`. One update worth knowing: it now has a
  **second consumer**, since `based-at` carries `instance_key_tag: site_type` and S3's relationship wall fires *within
  one `site_type`*. Same field, two load-bearing readers, still no enumeration.
- Sub-oracle entries confirmed on a single source → `FOR-DATA-C-sub-oracle-single-source-confirm.md`.
- All 492 frozen claims are `polarity: "positive"` while several documents state refutations — unchangeable while the
  corpus is frozen; recorded in the S2 and S3 findings, not a request.
