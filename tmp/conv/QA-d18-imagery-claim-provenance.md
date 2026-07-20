# QA observation — d18 "satellite image" claims carry text-only provenance

> **⚠️ SUPERSEDED (2026-07-20)** by `DATA-C-d18-imagery-orphan-node.md`. This note framed the issue as
> display-only. On the running graph the imagery claim IS present but orphans onto a separate node —
> the real fix is a resolve/merge, not a card-rendering tweak. Use the newer note as the spec.

**From:** live-QA remnant sweep (frontend session, 2026-07-20) · **For:** DATA-C / INGEST
**Status:** observation + options — not fixed here (frozen corpus; any re-record is a keyed risk).

## What the user saw

After ingesting the withheld `d18_rahwali_pass1` ("satellite image" pass), the claim form reads as an
ordinary text claim:

> "Rahwali airfield" is a basing site · site type — airfield · Observed · about a thing · L16
> "Site sits on the northern perimeter apron/dispersal area…" → `docs/d18_rahwali_pass1.txt · L16 · 1092–…`

Their question: *why doesn't a satellite claim look like one?*

## Why it is this way (verified in the bundle)

- The corpus ships d18 as a **pair**: `d18_rahwali_pass1.png` (the overhead — the relabeled-Esri
  specimen, per `md/16` disclosures) **and** `d18_rahwali_pass1.txt` (an IMAGERY ANALYSIS SUMMARY —
  the analyst-report artifact a real single-pass tasking produces).
- The frozen claim bundle (`claims/d18_rahwali_pass1.json`, 12 claims) was extracted from the **.txt
  only**. Every `doc_ref` points at the text; the imagery locator slots the schema already has
  (`bbox`, `frame`, `region`) are `null` on every claim. The `.png` was never machine-read in the
  recorded extraction (the VLM/attribution lane exists in design but is not in this bundle).
- So the rendering is **faithful**: one-click-to-source lands on the exact line of the imagery
  analysis summary, because that genuinely is the source of the assertion. Not a rendering bug.

## Why it still reads wrong

The claim card surfaces the *file + line* but not the **source class** — nothing on the card says
"imagery-derived (grade B)". `config/sources.yaml` knows it; the provenance drawer's `sources` map
(T6) serves it; the ingest-preview claim form doesn't show it, and nothing links the paired `.png`.

## Options (cheapest first)

1. **Surface the source class on claim cards** (ingest preview + drawer): a small chip — "imagery ·
   B / third-party" — read from the sources registry. No data change, no re-record. Frontend + maybe
   a field pass-through on `/pending/{doc}`.
2. **Show the paired image as display context** when a doc has a sibling `.png` — clearly labeled as
   the specimen the summary describes, NOT as the claim's provenance (the claim cites the text).
3. **Re-record d18 through the VLM lane** so imagery claims carry real `bbox`/`frame` refs.
   Keyed re-record of a frozen bundle → same risk class as the d06 alias-binding warning in
   `RESIDUAL-FIXES.md` §1. Not before the deadline.

Options 1–2 fit the design-note disclosure honestly: "imagery enters as analyst-summary text; the
image is a specimen; machine-read imagery is the roadmap." Option 3 changes the disclosure.
