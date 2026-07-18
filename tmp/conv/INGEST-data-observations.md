# INGEST → DATA-C handoff: corpus/answer_key observations

Written by the INGEST session (feat/ingest) during onboarding. Per CLAUDE.md, INGEST does **not**
self-fix the frozen corpus / `answer_key.json`; these are routed to the data agent. Items INGEST will
handle itself are listed at the bottom so there's no double-work.

## For the data agent to resolve

1. **Doc-count inconsistency (51 vs 52).** `md/17-corpus-catalogue.md` and the `sources.yaml` header say
   "51 docs = 24 signal + 27 chaff" and "hq9p_primary (24)", but `d17b_withheld_gap` exists as a real
   doc (+ its `.png`), which reads as a 25th primary / 52nd overall. Please reconcile the count (and
   whether `d17b` is meant to be counted, since it's the withheld-coverage gap beat) so INGEST's seed
   batch manifest and EVAL's expected counts agree.

2. **No claim-level extraction gold.** `answer_key.json` `documents[].asserts` is a prose summary, not a
   normalized `(subject, predicate, object)` tuple set. That's fine for the graph-level acceptance, but
   it means INGEST cannot measure extraction precision/recall against a gold tuple set. INGEST will test
   extraction against **its own hand-authored fixtures** instead. Flagging in case a small per-doc
   gold-tuple sidecar is cheap to add later (would strengthen EVAL); **not** a blocker.

3. **Recycled-image cluster is exact-duplicate only.** The six reshare PNGs
   (`d11/d12/d13/ce01/ce02/ce03`) are **byte-identical** (same md5). The two-hash integrity story
   (sha256 exact-dup + PDQ near-dup) is built and correct, but the demo cluster only exercises the
   **sha256/exact** path — PDQ's near-dup Hamming match is never triggered by the current corpus. If you
   want the PDQ (lazy-recycle: screenshot / recompress / mild resize) beat to actually fire in the demo,
   add **one recompressed/resized variant** of the parade image as a separate reshare. INGEST computes
   and freezes both hashes regardless; this is about which detector the demo visibly exercises.

## Handled inside INGEST (no data-agent action — noted so it isn't double-worked)

- **Text-vs-image relabel rule.** Satellite docs (`d07/d10/d17/d17b/d18`) carry Pakistan coords in the
  `.txt` while the co-located `.png` is a relabeled real foreign SAM site. INGEST enforces
  **"text coordinates are authoritative; the VLM must never geolocate from pixels"** as a hard rule in
  the imagery extractor/prompt (the observation claim carries only generic features + occupancy + count,
  never a coordinate derived from the image).
- **Runtime format routing.** `sources.yaml source_type` (credibility axis) and `answer_key source_class`
  (native-format axis) are not 1:1. INGEST authors a deterministic raw-text **format sniffer** (official→
  PR|NOTAM, customs-tender→BoL|tender) + documents the routing spec; no corpus change needed.
