# Keyed-mode verification — findings (2026-07-20, docs/readme-and-deploy worktree)

Run as part of the README + EC2 shipping task. Scope: does "keyed mode" work, and does
re-running keyed extraction change the graph ("bundled graph hash deviation")?

## 1. Keyed app boot — works

`docker run --env-file <.env with ANTHROPIC_API_KEY(+GEMINI_API_KEY)> ...` boots clean,
`/health` reports the same 166 nodes / 84 edges as keyless (the seed bundles are always
frozen/keyless regardless of key presence — correct, matches design).

## 2. Re-extraction determinism (`make extract`) — CONFIRMED non-deterministic, breaks the flagship query

Ran `python -m chanakya.ingest extract --scenario hq9p_primary --only d06_spares_tender
d19_rahwali_confirm d03_quwa_analysis` **twice**, independently, against the committed
baseline. All three bundle files hash differently on every run (baseline vs run1 vs run2 —
see `run1/`, `run2/`, `baseline_snapshot/` in this directory, sha256 in each run's shell
history above / re-derivable with `sha256sum tmp/keyed-verification/*/*.json`).

**This is not cosmetic.** `d06_spares_tender`'s "Long Range Surface-to-Air Missile (LR-SAM)
system" alias — flagged in `tmp/conv/RESIDUAL-FIXES.md` #1 as *"the only reason hop 2
resolves at all"* — is present in the committed baseline and in run1, but **absent in
run2**. Rebuilding the graph and asking the hero query against run2's bundles:

- Boot shape: 164 nodes / 83 edges (vs 166/84 committed) — deviates before any ingest.
- Hop 2 of the hero query changes from `unit_hq9b --[equips]--> var_hq9p` (HQ-9/P, the
  actual subject, cites d06) to `unit_hq9b --[inducted-into]--> var_hq9be` (a **different**
  variant, HQ-9BE, cites an unrelated document) and the chain never reaches CASIC.
- The flagship demo answer breaks exactly as RESIDUAL #1 predicted, empirically confirmed.

**Conclusion: nobody should run `make extract` against the graded corpus.** This is already
consistent with the Makefile's own audience split (`make extract` is listed under
"DEVELOPER", not "REVIEWER") — the README will tell instructors to never run it, only
`make run` / the prebuilt image.

Corpus was restored to the committed baseline after this test (`git checkout --
corpus/scenarios/hq9p_primary/claims/{d06_spares_tender,d19_rahwali_confirm,d03_quwa_analysis}.json`).

## 3. Live in-app extraction (the actual instructor-facing keyed feature) — bug found

The "or extract a document" box in the Documents rail (LIVE mode) POSTs to `/ingest` with
raw text, which runs live LLM extraction server-side (`CHANAKYA_ENABLE_EXTRACTION=1`).
Gemini is tried first when `GEMINI_API_KEY` is set (`chanakya/ingest/client.py`), Anthropic
is the fallback.

**Bug: the shipped Docker image does not include the `google-genai` package** (it's an
optional extra, `pip install -e ".[gemini]"`, not pulled into the image's dependency
install). If `GEMINI_API_KEY` is set, live extraction 500s with
`ModuleNotFoundError: No module named 'google'`. Confirmed against the real built image,
not just a dev venv.

**Workaround verified, zero code change:** with `GEMINI_API_KEY` unset/blank and only
`ANTHROPIC_API_KEY` set, live extraction works correctly (200, claims appended, rebuilt).
`GEMINI_API_KEY` has no instructor-relevant purpose anyway per `deploy/README.md`'s own
secrets table — it's only used by `make extract` (dev-only, and per §2 above, must never be
run against the graded corpus regardless).

**README will instruct: give instructors `ANTHROPIC_API_KEY` only.** Filing this bug for a
SHIP-domain fix (bundle `google-genai` in the image, or reorder the client to try Anthropic
first) rather than fixing it myself — out of scope for a README-only task and against the
"no logic changes" instruction for this session.

## Artifacts saved here
- `baseline_snapshot/` — the three committed bundles before any re-extraction.
- `run1/`, `run2/` — two independent keyed re-extractions of the same three documents.
