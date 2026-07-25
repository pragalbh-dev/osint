# Session RK-ATOMS (S1) — claim atom, dormant referent field, atom-aware dedup, A7 discriminator schema

**Wave 1 · depends on RK-SPIKE (merged) · offline + live.**
Thin by design (plan §6 step 2). The spec is `../01-replumb-implementation-plan.md` **§7 RK-ATOMS**, with
contracts **A1** and **A7** (§4) and gate **G17** (§5). The *why* is
`../../spine/13-type-instance-and-identity-replumb.md` §8 (mint grain / atoms) + §12 (migration), decisions
**D-13.7 / D-13.11 / D-13.18**.

**Read the spike's outputs first — they are load-bearing for this stage:**
`../../../tmp/conv/rk-spike-code-facts.md` (verified code baseline — **overrides any doc**) ·
`../../../tmp/conv/rk-spike-DECISIONS.md` (D-13.17…D-13.20 + closures C1–C4) ·
`../../../tmp/conv/rk-spike-REVIEW-VERDICT.md` (closures C5–C10 + what the spike did *not* establish).

## Goal

Formalize the **claim atom** as the stable addressing bedrock, add the **dormant** referent field, make dedup
atom-aware, and land the **A7 structured-discriminator schema** — with **zero behavioural change**. The
derived graph must be **byte-identical** after S1.

## Scope (plan §7 RK-ATOMS items 1–5)

1. **Claim atom = the post-dedup `claim_id`** (assigned in `dedup.assign_claim_ids`, *not* at construction).
   Name and freeze what already exists; mint no new id.
2. **Referent field (A1), optional, default `None`** on `ClaimRecord`/payloads; add `make_referent_id` beside
   `make_claim_id` **but do not invoke it** (referents are minted in S3). `resolved_ref` stays derived.
3. **Atom-aware dedup** — `remap_claim_refs` **and** `dedup_within_doc` must carry/reconcile the referent
   field, so a value populated later (S3) is never silently orphaned or collapsed. *This is the real risk the
   stage exists to close.*
4. **A7 structured discriminators** — operator / geography / designation / time as structured claim context on
   the `extract.py` mention schemas, plus the structured-attrs representation in `config_models.py`
   (`TypeDef.attrs` moves from a bare `list[str]` to structured entries). **All optional; absence is
   `unknown`, never fabricated.**
5. **Confirm the mint/remap sites at stage start** (`grep 'ClaimRecord('`). Verified at kickoff:
   **constructed** in `ingest/{extract,coref,basing,attribute,imagery}.py` (+ the `schemas/claim.py`
   definition); **canonical id remapped** in `ingest/dedup.py` (`assign_claim_ids` / `remap_claim_refs`),
   `ingest/lane.py` (chunk-namespacing), `ingest/seed.py` (recorder). `seed.py`-as-bundle-reader must **not**
   mint — it reads frozen bundles, and minting there would overwrite a frozen referent.

## Corrections from the spike that bind this stage

- **A1/A5 are claim-atom-primary.** A knowledge node is a derived grouping of **claim** atoms; the referent
  atom is a **grouping signal the rebuild may decline** (D-13.18), never the node's address. The earlier
  "referent primary, claim-atom fallback" wording was the inverted ordering and has been corrected in the
  plan — **do not reintroduce it**.
- **Settle the structured-attribute entry schema ONCE.** `config_models.py`'s `TypeDef.attrs` is contended S1→S2
  (plan §3 item 6): S1 restructures it, S2 adds `layer`. Design the entry so S2 adds a field and nothing else
  is reshaped. Keep the seam clean: the **ontology** entry carries what is *ontological* (`layer`, D-13.3's
  dual-attribute split); identity semantics (`role`, `perishable`, and per-**(type, attribute)** perishability
  per **C6**) stay in `config/resolution.yaml`'s `attribute_roles`. Getting this wrong is how the two files
  start duplicating each other.

## Gates

- **G17** — this stage authors the *atoms-minted-only-at-ingest* portion. (The no-mint/no-append-under
  `rebuild()` clause is S2's; the id-from-atoms clause is S4's.)
- **G1/G2 unchanged**; the abstract golden must stay byte-identical.

## Owned paths

`schemas/{claim,ids,config_models}.py` · `ingest/**` (extract, dedup, coref, basing, attribute, imagery) ·
`tests/ingest/**` · `tests/gates/test_g17_*`.

## Acceptance

- [ ] The claim atom (post-dedup `claim_id`) is named and stable.
- [ ] The referent field is present-and-`None` on ingest-minted claims, tolerated-absent on pre-baked fixtures.
- [ ] Dedup carries the referent field through both `dedup_within_doc` and `remap_claim_refs`.
- [ ] The A7 discriminator fields are present and optional; absence reads `unknown`.
- [ ] **The golden view is byte-identical to pre-S1** (the stage's headline invariant).
- [ ] G17 green, with a **non-vacuous** fixture.
- [ ] Independently-authored tests (separate branch) pass against independently-authored code.

## Out of scope

Minting referents (S3) · using the atom for addressing (S4) · layer tags (S2) · anything in C5–C10 (S3).
