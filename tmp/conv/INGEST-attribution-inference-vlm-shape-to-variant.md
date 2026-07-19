# RESOLVE → INGEST: build the attribution proposer (VLM shape → variant identity)

**Owner:** INGEST (it produces `inference` claims — SCORE only *reads* them; RESOLVE only *wires* the
entities/places). **Status:** not built; spec for a thin, demo-scoped build (one worked beat) + a
roadmap note. **Why this doc:** the shape→"HQ-9" step is an LLM *inference*, and getting *where* it runs
right is the whole trick — it is **not** at single-doc ingest, **not** in `rebuild()`, **not** in SCORE.

---

## The problem it solves

A VLM reads a satellite image and emits a **subject-blind** observation — shape/feature tokens, count,
occupancy, geo — and **deliberately never names the system** ("HQ-9"). (Naming a system from pixels
collapses the VLM to its prior — the sycophancy/modality gap, ~100% canonical vs ~17% counterfactual —
so it is forbidden; DECISIONS 2026-07-18 rows on VLM.) So the graph has an *unattributed shape at a
location*. Turning that into "this is an HQ-9" is a separate, cited **inference** against reference
literature — and that inference is what lets IMINT *corroborate* a textual "HQ-9 at X" claim (a second,
discipline-independent look → SCORE can raise the assertion toward confirmed).

## The hard constraint (why naïve "do it at ingest" fails)

At the moment the image is parsed, it is **isolated** — nothing says "HQ-9" is even the hypothesis, and
you must **not** compare the shape against *all* literature (O(n²), and the LLM would just pattern-match
to its prior). The hypothesis, and the *one* piece of literature to check, only exist **after
resolution connects things**: imagery-location ↔ a news claim naming a variant at that location ↔ that
variant's reference literature. So the inference is **connection-triggered**, and it runs as an
**offline proposer over the previous resolved view** — the exact pattern RESOLVE's merge proposer uses
(spine/03: "the proposer traverses only the evidence-layer claim graph + the previous frozen view,
never the in-progress rebuild"; spine/08 §3.11 selective invocation). The invariant holds: **LLM
proposes upstream, frozen; `rebuild()` disposes deterministically.**

## The loop (two rebuild passes with one offline step between)

1. **Rebuild pass 1 — RESOLVE builds the triangle (already implemented).**
   - VLM observation `A` (shape @ coords) → place-resolves to `site_L`.
   - News `C` ("HQ-9 at <place>") → place-resolves `<place>` to the *same* `site_L`, entity-resolves
     "HQ-9" → `var_hq9p`, yields the variant-present-at-`site_L` assertion.
   - Literature `B` ("the HQ-9 TEL looks like <fingerprint>") is attached to `var_hq9p`.
   - The view now *contains the connection*: `site_L` has an unattributed shape-observation **and** a
     textually-named variant present, and that variant carries a fingerprint.

2. **Between passes — the attribution proposer (BUILD THIS).**
   - **Deterministic candidate rule** (this is what scopes the LLM to one variant — no "all literature"):
     traverse the resolved view for the pattern —
     > a location node that has **(a)** an unattributed IMINT shape observation/indicator, **and**
     > **(b)** a variant asserted present there by a *textual* source, where **(c)** that variant has
     > reference-literature fingerprint claims.
     Each hit is one candidate: *"is A's shape consistent with variant V's fingerprint?"*
   - **Scoped LLM call:** input = A's shape/feature tokens + **V's** fingerprint only (one variant).
     Ask a bounded question ("consistent? which features match/conflict? decoy-plausible?"). Cited to
     A's `doc_ref` (image region) + B's `doc_ref` (the literature line). **Raise-only** — it proposes;
     it never decides the number.
   - **Emit a frozen `inference` claim `D`** (see contract below) if consistent. Skip (logged) otherwise.
   - **Selective invocation** (mirror RESOLVE's proposer): fire only on the candidate pattern above;
     one call per candidate; **budget cap; log skips**. Cost ≈ #(unattributed-shape ∩ named-variant)
     co-locations, not O(images × literature).

3. **Rebuild pass 2 — SCORE reads `D` deterministically (SCORE's job, already speccing).**
   - `D` (IMINT-inference) + `C` (textual) are discipline-independent looks at the same variant-at-`site_L`
     assertion → SCORE can raise it toward confirmed. `D` shares an independence group with its premise
     `A` (an inference never corroborates its own premise). Pixel-derived attribution carries decoy_risk
     and **caps at probable** until independently seen — `C` is that independent look.

## The output claim — contract (this is what you emit)

```yaml
claim_id:   <doc/enrichment id>            # readable, e.g. "enr-d10-img1-hq9p"
kind:       inference                       # NOT observation
asserts:    relationship                    # assert the SAME variant-present-at-site assertion the
                                            #   textual source (C) makes, so they resolve to one edge
                                            #   and corroborate. (Exact predicate = whatever ontology.yaml
                                            #   / answer_key uses for variant-at-site; bind to that.)
payload:    (subject=<site/indicator>, predicate=<...>, object=var_hq9p)
premises:   [<A: vlm_observation_claim_id>, <B: literature_fingerprint_claim_id>]   # REQUIRED for kind=inference
extraction: {method: llm, model: <id>, model_conf: <0..1>}
doc_ref:    [<A image region>, <B literature span>]   # cited to BOTH sources it reasons over
# carry the deception signal for SCORE's gate:
attrs:      {decoy_risk: true, fingerprint_match: <features matched/total>, single_pass: true}
```
Key points: `kind=inference` + non-empty `premises` (the schema validator enforces this); it must resolve
to the **same assertion** the textual claim makes (so RESOLVE co-locates them and SCORE groups them as
independent looks); it is **cited to both** the image region and the literature line ("one click to
truth" holds — G4).

## Boundaries (red-team; do not violate)

- **VLM stays subject-blind.** The variant name enters *only* via this inference against literature,
  never from the VLM's mouth. If your extraction ever has the VLM say "HQ-9" from pixels, that's the bug.
- **Proposer, never authority.** `D` is a cited proposal; SCORE caps it at probable and needs an
  independent look to confirm. Don't emit a "confirmed" flag; don't emit an `assertion_confidence`.
- **Offline + G1.** Runs upstream of the append; lazy-import the LLM; it must never be reachable from
  `rebuild()`. `rebuild()`/SCORE never re-run the shape↔fingerprint comparison — they read `D`.
- **Deterministic disposal.** The comparison happens **once**, frozen into `D`. Re-ingesting the same
  inputs must produce the same `D` for the demo (recorded transcript / pinned inputs).
- **Tested offline.** Recorded/mocked LLM transcripts (`respx`/fixture); an opt-in `@live` marker for
  the real call, like the other LLM-touching sessions.

## Seams you get for free

- **From RESOLVE (merged via #16 / f0-amend #10):** the resolved view where imagery + news + literature
  are already co-located/unified — read `resolved_place_ref`, the variant nodes, and each variant's
  literature claims. RESOLVE does **not** compare shapes (it has no idea what an HQ-9 looks like); it
  only links by location + name/id. The shape→variant leap is *yours*.
- **From SCORE:** it already models `kind=inference` + `premises` (independence grouping puts `D` with
  its premises; variant attribution caps at probable). You just emit a well-formed cited `D`.

## Scope decision (put to the user — don't assume)

Two honest options; recommend the first:
1. **Thin demo beat (recommended):** wire exactly **one** attribution — the HQ-9 imagery beat (a TEL
   shape observed at the relocation site + the textual "HQ-9 relocated to Rahwali" + the HQ-9 TEL
   fingerprint literature) → one cited `D` → SCORE shows IMINT+textual corroboration with the pixel
   read held at probable/decoy-capped. Demonstrates the mechanism end-to-end; everything past it is
   design-note.
2. **General engine (roadmap):** a standing enrichment pass over every rebuild that proposes all
   candidate attributions. More infra (a re-rebuild trigger + budget management); not needed for the demo.

Also flag: this spans INGEST (claim production) **and** an iterative re-rebuild trigger (the enrichment
loop = the "monitoring/adaptation" story, CLAUDE.md idea #4). Coordinate who owns the trigger.

## One-line summary

RESOLVE co-locates the imagery with the news that names the variant and links the variant to its
literature; **you** (offline, connection-triggered, one candidate at a time) run the scoped shape↔
fingerprint check and freeze a cited `inference` claim; SCORE reads it as a second, decoy-capped IMINT
look. The LLM does the real reasoning — as a proposer, upstream, frozen — never inside the deterministic
rebuild.

*— RESOLVE session, 2026-07-19*
