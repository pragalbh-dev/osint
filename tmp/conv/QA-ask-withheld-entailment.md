# QA diagnosis — post-ingest hero answer withheld (not_entailed ×4)

**From:** live-QA remnant sweep (frontend session, 2026-07-20) · **For:** ASK owner
**Status:** ✅ FIXED (2026-07-20, Option C) — the flagship answer now renders 5/5, verified with a live
keyed re-run. Root cause + the fix below.
**Repro:** boot withheld → ingest all pending bundles → keyed `POST /ask` (hero question), judge
instrumented. Script: session scratchpad `repro_withheld.py`.

## Fix shipped (Option C, user-approved)

Both halves, in `backend/chanakya/agent/{validate,assemble}.py`:

1. **Identity bridge for hop sentences.** The judge is now handed the resolver's OWN recorded
   equivalence: the cited claim's raw surface terms (`"Pakistan Air Force"`, `"LR-SAM system"`) and
   the resolved entities the graph merged them into (`the PAF HQ-9B fire unit`, `HQ-9/P`), with the
   instruction to treat a raw name and its resolved entity as the same and judge only whether the
   RELATION holds. This is auditable graph state, not an invented hint — so the check still catches a
   sentence whose *relation* is unfaithful; it no longer fails a faithful sentence on an alias mismatch.
2. **Sentence-class scoping.** Two sentence classes never reach the NLI judge (they keep deterministic
   validation — cited, citation exists, counts real): `DERIVED_METRIC_PREFIX` (`Chokepoint: …`, a
   rebuild-computed value no claim can entail) and `WEIGHED_NOT_CARRIED_PREFIX` (a link reported as
   *rejected* — a claim can't entail its own dismissal). Prefixes are owned by `assemble.py` (where the
   sentences are built) and imported by the validator.

Live re-run after the fix: refusal `None`; hops 1–3 entailed; chokepoint + weighed sentences exempt;
the honest `HT-233 candidate / UNKNOWN` gap and the refuted CPMIEC attribution both preserved.

Tests: `tests/agent/test_validate.py` gains `test_derived_and_weighed_sentences_are_not_sent_to_the_nli_judge`
and `test_identity_line_carries_the_resolved_endpoints_to_the_judge`; the adversarial
`test_rejects_cited_but_not_entailed_sentence` still holds (identity bridges only identity, never the
assertion). 134 backend agent+api tests green, ruff + mypy clean.

---

## Original diagnosis (retained)

## What happens

The agent finds and assembles the full 4-hop answer. The entailment judge (`agent/validate.py`,
live LLM, "default to no if unsure") then rejects 4 of 5 sentences, and `agent/__init__` downgrades
the whole answer to the `withheld` refusal. The UI faithfully renders "Failed on — not_entailed ×4".

Assembled answer (before withhold), with judge verdicts:

| # | Sentence (gist) | Cited claim text shown to the judge | Verdict |
|---|---|---|---|
| 1 | Rahwali is the basing site of the PAF HQ-9B fire unit | `unit_hq9b based-at site_rahwali` (d18, d19) | **entailed** ✓ |
| 2 | The PAF HQ-9B fire unit fields HQ-9/P | `Pakistan Air Force equips Long Range Surface-to-Air Missile (LR-SAM) system` (d06) | not_entailed |
| 3 | HQ-9/P is manufactured by CASIC | `CASIC manufactures FD-2000` (d03) | not_entailed |
| 4 | Chokepoint: HT-233 — candidate, substitutability UNKNOWN… | `HT-233 equips HQ-9B` ×4 (d19/d24/d25) | not_entailed |
| 5 | Weighed and not carried: HT-233 supplied by CPMIEC — insufficient | `CPMIEC supplies-component HT-233` (d23) | not_entailed |

## Root cause — the judge is shown the wrong altitude, so it is *correctly* saying no

`_claim_text()` renders each cited claim as its **raw surface form** (`subject predicate object` as
extracted). But the answer speaks at the **resolved-knowledge layer**. Three distinct failure classes:

1. **Alias-resolved sentences (2, 3).** "CASIC manufactures FD-2000" cannot entail "…manufactures
   HQ-9/P" unless you know FD-2000 ≡ HQ-9/P — which is the alias-table merge the resolver made,
   auditable graph state the judge never sees. Same for LR-SAM ≡ HQ-9/P (the d06 designator-free
   tender — the corpus's own trap, working as designed at ingest and then failing at validation).
   **These two are the corpus's two engineered alias traps** — so on this corpus the judge rejects
   exactly the sentences the resolution layer exists to enable.
2. **Derived-metric sentence (4).** `chokepoint_status=candidate` is computed at `rebuild()`; its
   citations are the *contributing evidence*, not statements of the metric. No claim can entail a
   derived number; NLI is the wrong check for this sentence class.
3. **Meta-sentence (5).** "Weighed and not carried" *reports the rejection* of the claim it cites.
   The claim can never entail its own dismissal; the citation is there for audit, not support.

Sentence 1 passes only because its claim text happens to read like the sentence.

## Options (user's call — this changes flagship demo behaviour)

A. **Show the judge the resolution context** — render cited claims with canonical resolved names +
   the alias binding that resolution recorded ("FD-2000 — resolved same-as HQ-9/P, alias-table
   merge, decision <id>"). Fixes class 1 honestly: the judge is being asked to check the *system's*
   cited reasoning, and the merge IS cited reasoning. ~`_claim_text` + ctx plumbing.
B. **Scope NLI to hop-assertion sentences** — classes 2 and 3 get deterministic validation only
   (citations exist, in the right hop/claim sets — already checked today) and are tagged derived /
   weighed-and-rejected so the validator knows not to NLI them. `assemble.py` knows which sentences
   are which; it can tag them.
C. **A + B** (recommended shape): alias context fixes the two alias sentences; scoping fixes the
   two structural ones. After C, this corpus's hero answer should pass 5/5 — and a *genuinely*
   unfaithful sentence still gets withheld.
D. **Demo fallback: deterministic-only validation** (judge documented as optional, keyless parity).
   Zero risk, but weakens the graded "entailment citation validator" story to a disclosure.

Note either way: the `withheld` refusal is the non-negotiable behaving correctly given what the
judge saw — the bug is the evidence fed to the judge, not the withholding. Worth saying on the call
even if unfixed.
