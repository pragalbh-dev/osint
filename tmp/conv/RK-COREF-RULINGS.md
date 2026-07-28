# RK-COREF (S3) rulings — two gate defects the data hand found before any code was written

Both verified. Both are defects in **my own** C5 / D-13.17 gate design, and both must land in S3.

---

## M1 — the structural gate cannot catch a mislabelled equivalence. Reuse the mark-vs-word test.

**The hole.** The data hand authored a fixture that **passes every conjunct of the structural gate as I specified
it** — the quote occurs verbatim, contains *both* surface forms, and contains a parenthetical marker — while the
equivalence is **wrong**. The shape is a *mark-vs-name collision*: `"<Design> (<Design>/X)"` reads exactly like an
alias declaration but actually distinguishes two variants. Nothing downstream reliably saves us either: the grade
floor cannot (a good source can write it), and the D-13.18 decline only fires if the two members happen to carry a
conflicting critical discriminator — two marks of one design often conflict on nothing.

Its sharper observation: **"a marker vocabulary built as a token list cannot catch it."** True — and that means my
gate was under-specified rather than merely unlucky.

**The fix already exists in config, encoding precisely this distinction** (`config/resolution.yaml:185-187`):
> `containment_min_descriptor_len: 3` — *"HT-233" + "engagement" (a **WORD**) is the same radar described more
> fully; "HQ-9" + "P" (a **MARK**) is a different missile. The knob is the length of the first token the longer
> name adds.*

**Ruling: the structural gate gains a fourth conjunct — the existing mark-vs-word test.** If the longer surface
form differs from the shorter only by a **mark** (a short token below the configured descriptor length), the
equivalence is **not licensed**, regardless of how the sentence is phrased, and the pair goes raise-only with its
quote. Reuse the shipped knob; do **not** introduce a second threshold for the same idea (G6). This also answers
the data hand's note that the raise-only category has no gate of its own to fail: the collision is caught where it
actually arrives — as a **mislabelled** equivalence.

---

## M2 — the licensing evidence is a SET of spans, not one span

**The finding that changes an expectation.** The frozen corpus contains equivalences a document genuinely
*asserts*, whose two surface forms sit **18–58 lines apart, or in different fields of one record** — so **no single
span can contain both**. Under my gate as written, the system would withhold on equivalences documents really do
state.

**Ruling: licensing evidence is a set of verbatim spans from the same document**, which together must contain both
surface forms and the marker. Each span must still occur verbatim, so the whole point is preserved — **any reader
can re-derive the bind** — while a one-contiguous-span requirement is dropped as what it is: an artifact of how the
check was first imagined, not a principle. A document that states an equivalence across two fields **has stated
it**.

**What does not change:** the grade floor, the mark-vs-word conjunct (M1), and C9's document-scoping. Multiple
spans make the evidence *findable*, not *stronger*.

**And carry the data hand's warning forward:** even with M2, this path will be busy, and **the analyst queue is
load-bearing, not a fallback.** That is a design property, not a defect — but it means the raise-only queue's
usability (the licensing quote actually being *surfaced*, which an audit found is written but read nowhere) is on
S3's critical path, not a nice-to-have.

---

## M3 — two declaration sites C6 and D-13.20 need do not exist (for the implementer)

From the same pass, and S3 owns `config/resolution.yaml`:
- **C6's two new `time_role` values have no declaration site for the types that need them** — `constitutive` is
  what lets a **presence** confirm and `identifying` what lets a **place** confirm, yet `attribute_roles` declares
  neither type. Without those declarations C6 is inert and **lever 2 still cannot exist**.
- **The composite identifier has no declaration site in config at all** — D-13.20's `(service_branch, designator)`
  AND-key needs `hard_id_fields.unique`, which does not exist (the spike measured `_shared_unique_id` as always
  False for exactly this reason). Declare it, or the ladder's fast path stays unreachable.

## M4 — recorded: all three of S3's gates are fixture-only on the current corpus
Zero coreference annotations exist anywhere in the frozen bundles, and three fixture families are untestable **in
principle** rather than merely uncovered. So **G16, G18 and G19 are all fixture-only** for now. That is the
§5a-bis *inert-because-the-data-is-sparse* case with the mechanism at full strength — **not** hidden-to-protect-a-
fixture — and it is exactly why the abstract fixtures were mandatory. State it in the handoff and the disclosures.

---

# Round 2 — four silences the test hand surfaced, ruled

## M5 — "presence merge is expected" means PERMITTED, not REQUIRED (correcting my own C2 wording)

The test hand read C2's *"a presence-level merge in the same case is expected and must not fail the gate"* as
**must fuse**. That reading is a reasonable parse of my sentence and it is **wrong** — and dangerously so:
**requiring a presence merge would be forcing density**, which spine/13 §6 names explicitly as "the
name-collapse bug wearing a different hat." Whether two presences fuse depends on their evidence.

**Ruling: a presence merge is PERMITTED and must not fail G16; it is never REQUIRED.** G16's assertions are all
*absences* (no confirmed formation merge · formation count preserved · no drawn relocation · no Known-Gap
deletion / no `insufficient → stale`). Nothing in G16 may assert that a fusion *occurred*. My wording caused
this; the correction is mine.

## M6 — a differing designation VETOES; it does not merely fail to satisfy the cap

Silence: D-13.20 says a shared designation satisfies the perishable cap, but not what happens when two
designations **disagree**. **Ruling: the ladder's own order settles it — differing designation is the TOP rung
and it is a veto.** So disagreement **wins over** any cap-satisfaction or score elsewhere: the pair is walled,
not merely un-confirmed. (Subject to **C7**: the values must be normalizable; an *unnormalizable* pair is the
third state — no wall **and** no fusion, plus a named gap — never a wall on an untested string.)

## M7 — name the coref grade-floor knob: `coref_authoritative_min_grade`

Silence: the floor had no name, so the test hand pinned it behaviourally (A-vs-E), which was the right call.
**Ruling: `coref_authoritative_min_grade`, in `config/resolution.yaml` beside `coref_authoritative_evidence`.**
Its value is chosen on principle, not tuned: it must sit **strictly above** the stated-`same-as` floor, because a
coref bind **fuses uncapped at Phase 1** while a stated `same-as` only *raises*. Mirror
`_critical_attribute_walls`' discipline — above floor ⇒ act; below floor ⇒ **raise**, never silently do nothing.
Keep the behavioural A-vs-E assertion as well: it survives a rename.

## M8 — "rarity-graded name" is DEFERRED, and the design docs must stop claiming it

The test hand reports it is **the one spec item with no observable contract at all**, so it cannot be tested —
and the spike separately measured that it has **no implementation anywhere**, while D-13.2 and D-13.10 both rest
on it.

**Ruling: defer it, and correct the docs rather than rushing it.** Reasons, in order: (i) **nothing depends on
it** — D-13.10's cap is a *ceiling* (name alone never exceeds *possible*), which works whether the name score is
graded or flat, so deferring costs no guard; (ii) S3 already carries 11 items and three gates, and a scoring
refinement no cap depends on is scope creep; (iii) the disciplined move for an unbuilt claim is to **stop
claiming it**, exactly as F9 was accepted-and-disclosed rather than half-built.

**Its observable contract, recorded now so it is testable whenever it is built:** *with name similarity and every
other signal held equal, the `name` component is **monotonically non-increasing in the frequency of the matched
tokens** across the entity inventory* — a rarer name contributes at least as much as a commoner one. That needs
no embeddings (token frequency over the inventory is deterministic and local), so it is a clean later addition.

**Actions:** mark it deferred in D-13.2 and D-13.10 with a pointer to this contract; add it to the design-note
disclosures (name is currently a **flat** contributor, capped, not rarity-graded); and **do not** let S3 assert
it. Also fold the standing correction: **"rarity-graded" must not appear as a shipped property anywhere** until
the contract above is met.

## M9 — the span-set carrier shape is an integration reconcile, not a ruling

The test hand guessed M2's carrier (a list under `source_quote`, a plural sibling, one `DocRef` per span). I am
deliberately **not** fixing the shape by decree — the implementer owns the schema and has better information.
**It reconciles at integration**, like the S2 flag name. What I *do* fix is the behaviour the shape must
support, which the test hand already pinned: multi-span licenses · **two-document spans do not** · span count
relaxes neither the grade floor nor M1 · each span still verbatim.

---

# Round 3 — the two HIGH spec problems the implementer found, ruled

## M10 — the universal name cap vs `identity.relational: false`: honest fragmentation, with a curated escape

**The collision (real).** D-13.10 caps name at *possible* **for every layer**, so a merge needs one more
signal. But a type declaring `identity.relational: false` has its relational term **forced to zero by the
ontology** — so "earn one more signal" demands evidence the ontology forbids from existing, and such types
become **permanently unmergeable**. Measured cost here: 5 area merges.

**And the ontology's own comment appears to promise otherwise** (`config/ontology.yaml:269-272`): *"An area's
identity is its NAME and its geography — never its neighbourhood… Areas can still merge/queue on name + alias
evidence, which is the only honest signal for them."*

**Ruling: the fragmentation is CORRECT, and the comment's promise is the thing that must change.**
1. **Areas must not merge on name.** The very reason `relational: false` exists is that shared neighbourhood
   put `Punjab ↔ Sindh` in the merge queue — a near-fusion of two different provinces. A type whose *only*
   available signal is a name is a type we **cannot honestly individuate**, and the design's own doctrine
   settles that: *"honest fragmentation is the goal, not forced density"* and residual fragmentation must
   surface as a **measured coverage gap**. Exempting such types from the cap would make name a **verdict**
   again for exactly the types most prone to string collision — the bug D-13.1 exists to delete.
2. **The escape is curated identity, not name.** A `relational: false` type may still merge on a **registry /
   `config/entities.yaml` stable-id declaration** or a **replayed analyst decision** — both are *asserted
   equivalences*, not string coincidences, and neither is capped by D-13.10 (which caps *name similarity*).
   That keeps a human able to unify two areas deliberately while the machine never guesses.
3. **Rejected: promoting alias-equivalence to the "one more signal."** Tempting, but it contradicts D-13.20's
   S4 rule that the alias index is **pure recall — a name-class buys a *comparison*, never a merge.** An alias
   entry derived from string similarity is still name evidence wearing a table.
4. **Action:** correct `ontology.yaml:272` — it currently promises a merge path the design forbids, and a
   comment that promises more than the code delivers is the failure mode we have hit three times this session.
   Residual area fragmentation is a `/coverage` item, and it goes in the disclosures.

## M11 — "fragmentation must resolve at S3" was MY error; the criterion moves to RK-DATA

**The finding.** S3 ships the guards, but **the corpus cannot ship the earning material**: there are **zero
coreference annotations and zero referent ids in all 492 frozen claims**, and producing them is a **keyed
re-record**. So the mechanism that resolves fragmentation has *no input*, and my acceptance criterion
("fragmentation must resolve at S3") was **unsatisfiable by construction**.

**What the implementer did is exactly right and worth recording:** faced with an unsatisfiable criterion, it
**did not touch a floor to make the number look better** — it measured, attributed all 14 lost merges by
type-pair, and reported. That is the F8 trap declined under pressure. Fragmentation went **up** (`same_as`
66 → 52, candidates 19 → 43), and every loss is accounted for: 2 cross-type fusions the reflexive-alias hole
had allowed in Phase 1, 2 formation merges the co-location cap withheld, 10 name-only pairs the cap now refuses
**on the fusion path** rather than only in the collection loop (2 of which the shipped config already said
should be a HITL call). `manufacturer` merges held at 16 → 16 — **the cap is a cap, not a ban**, which is the
tell that it is calibrated rather than blunt.

**Ruling:** the acceptance criterion moves to **RK-DATA**, where the re-record with coreference lands. S3's
criterion is instead: *the guards bind, no threshold was loosened, and every lost merge is attributed.* All
three are met. **Rising fragmentation at S3 is the expected, correct signal** — S2 fragmented per-mention (F8)
and S3 additionally withdraws fusions that were never earned. **DATA owes the keyed re-record with
coreference**; until it lands the graph is honestly sparser than it will be, and that is stated, not hidden.

---

# Round 4 — S3 integration triage: 34 failures, two causes (+ my own harness fix)

**First, a harness fix of mine: 66 → 34.** The test fixtures' flag *discovery* is sound, but its token list
predated S3, so it enabled S2's `layer_routing.enabled` and never found `earned_identity.enabled` — every
behavioural test ran against the **flag-off** graph and failed for the wrong reason. Same coupling class as S2's
hand-copied config knob. Fixed, with the standing rule recorded in the token list: **when a stage adds a flag,
add its tokens in the same commit.**

## Cause A — C6/M3 shipped INERT: the values exist, the declarations do not (13 failures)

`test_rk_coref_time_role.py` + parts of the ladder. Verbatim: *"no shipped declaration uses
`['constitutive','identifying']` (roles in use: `['durable','perishable']`)"* · *"no attribute of the presence
citizen … is declared"* · *"no geography attribute is declared in `attribute_roles` at all, so geography has no
time role on any citizen"* · *"`variant.operator_branch` declares no legal `time_role`"*.

So the four-value `time_role` **schema** landed but was **never applied to the types that need it** — which is
precisely the failure M3 was written to prevent (*"without those declarations C6 is inert and **lever 2 still
cannot exist**"*). And the consequence is measurable: *"two presences of the same design, at the same
coordinate, under the same operator, in the same window"* **do not confirm** — because geography has no
`constitutive` role anywhere, so the presence citizen still cannot confirm on the evidence that defines it.
**The test hand is right; this is the real gap, not a fixture artifact.**

## Cause B — the auto-bind gate does not fire, and one conjunct is missing entirely (18 failures)

`test_rk_coref_autobind.py` + `decline` + `plumbing`. The tell is *"the in-document bind itself did not fire, so
the leak assertion below is vacuous (`same_as=[]`)"* — **coref binding produces no merges at all** in these
fixtures. Downstream of that: a **grade-A textbook parenthetical alias** does not bind; **M1's word-extension
mirror** (`RX-9` → `RX-9 engagement radar`, a descriptive *word*, which must license) does not bind; **M2's
two-field equivalence** does not license; **C5's partial bind** does not bind; and a `NAME_VARIANT` cluster is
**dropped rather than queued** with its quote.

**And one is a genuine safety gap, not a wiring gap:** *"a span set containing a sentence the document never
contains was accepted — the verbatim check is what makes the evidence re-derivable."* **M2 relaxed contiguity,
not verifiability.** A span set whose members are not each verbatim is fabricated licensing evidence, which is
the disqualifying class. That one is highest priority regardless of how the wiring is resolved.

**Likely single root cause for the wiring half:** the producer half of coref (the `config/credibility.yaml`
`coreference` block) or the consumer allow-list is not reachable from the fixtures — S3 requires **both** gates
to flip, and a fixture that supplies neither sees an inert pass. Reconcile it the way the flag was reconciled:
the fixtures must **discover** the config keys, and the implementation must be enable-able from a bundle.

---

# Round 5 — three rulings from the user (2026-07-25)

## M12 — the mark-vs-word test is a FILTER with a benign failure direction, never a verdict

**The concern is right: it is a heuristic and it can false-fire in both directions.** A short *word* looks like a
mark (`TX-5 air defence` — "air" is three characters), and a long *mark* looks like a word (`HQ-9 Export` is a
different variant, but "Export" passes any length test). So it **cannot be a decision procedure**, and it must
not be presented as the thing that makes the gate sound.

**Ruling — status, not mechanism, is what changes:**
1. **It demotes to raise-only; it never vetoes.** A false-fire therefore costs **one analyst glance**, not a lost
   merge — the failure direction is benign by construction. That is already how M1 was specified ("goes raise-only
   with its quote"); this states it as the *reason* the heuristic is admissible at all.
2. **It is explicitly incomplete, and we say so.** A long mark will pass. The gate must not claim to catch every
   mislabelled equivalence, and the disclosures should say the structural conjuncts are a **cheap filter over the
   model's own claim**, not a proof of it.
3. **Do NOT add more pattern rules to compensate** — that is the wrong direction, and piling heuristics on a
   fallible test makes it *look* authoritative while staying fallible. The residue is caught by the
   **analyst queue**, which is why surfacing the licensing quote is on the critical path rather than a nicety.
4. Reuse the shipped knob only; **no second threshold for the same idea** (G6).

## M13 — M2 requires a PRODUCER change too; today it cannot express a span set

**Verified.** `ingest/coref.py:98` declares `licensing_quote: str | None` — **one** string — and
`_quote_supported(quote, text)` (`:258-260`) validates exactly one span. So the producer **cannot emit** the span
set M2 licenses, which is why the two-field equivalence fails. The consumer-side ruling was not enough.

**Ruling:** the producer emits an ordered **sequence** of spans per cluster, and **each is validated verbatim
independently** — same predicate, applied per member. This lands in the same code path as the safety gap already
in the failure set (*a span set containing a sentence the document never contains was accepted*): **M2 relaxed
contiguity, not verifiability**, and one un-verified span is fabricated licensing evidence. Fix the shape and the
per-span check **together**, since a sequence with a single-span check is strictly worse than today.

**And note what this does to the coref grain, which is the user's point:** a cluster may now carry evidence drawn
from several places in one document, so the licensing evidence is *per cluster*, while the verbatim check is
*per span*. Do not collapse a set into a concatenated string to reuse the old check — that would let a fabricated
join pass while every part looked present.

## M14 — the keyed re-extraction: after S3 goes green, before S4

Timing is mine to call and this is it, with reasons rather than convenience:
- **Not before S3 closes.** The A7 coref contract is still moving (34 open failures, and M13 changes the
  producer's schema). Re-recording against a moving schema buys bundles we would immediately invalidate —
  working-principles #3: the data follows the design, and the contract must freeze first.
- **Not after S4.** S4 cuts the name-key and re-anchors identity on **earned clusters**. With zero coreference
  annotations in the frozen claims, S4 would land its most consequential change on data that cannot exercise it —
  we would be testing the name-cut against no clusters at all.
- **So: S3 integrates green → freeze the A7 coref contract → keyed re-record → S4 runs on real clusters.**

**Gated as plan §10 already requires** — it re-freezes the graded oracle, the single hardest-to-reverse action in
the plan: a **`DECISIONS.md` entry recording user approval**, EVAL coordination, and the **old oracle archived**
so pre- and post-re-key grading stay comparable. Two known consequences to carry into it: the **32 scripted-client
tests need a second queued response**, and re-extraction is **confirmed non-deterministic** — so freeze once and
version, or KEYLESS≡LIVE breaks.

---

## M14 CORRECTED — the bake-off sits BETWEEN S3 and the re-record, and my sequence omitted it

**The model comparison is not part of S4 and never was.** Plan §2/§8 place **RK-BAKEOFF** in two phases, and both
must finish **before RK-DATA's full regen — because the chosen model is what performs the regen.** My M14
sequence ("S3 green → freeze → re-record → S4") **left it out**. Corrected:

> **S3 green → freeze the A7 coref contract → RK-BAKEOFF (definitive pass) → keyed re-record with the WINNER →
> S4 on real clusters → RK-MATERIALITY / the rest of RK-DATA.**

**Why it must precede the re-record, not follow it.** The re-record *is* the regen: it produces the frozen
bundles the whole system boots from. Re-recording first and choosing the extractor afterwards would mean either
throwing the bundles away or keeping bundles from a model we did not select — and since re-extraction is
**confirmed non-deterministic**, "just re-run it with the winner" is a second full regen, not a cheap redo.

**Why it is unblocked now (and not earlier).** §8 says the bake-off's two **top-weighted** criteria are
substrate-*dependent*: **discriminator capture** needs A7's structured fields (**S1 — done**) and
**coref-binding accuracy** needs the promoted coref tier (**S3 — closing**). So the definitive pass could not
have run before now. The **Wave-0 substrate-independent screen** was scheduled to run early and **did not** —
that is a scheduling debt, not a blocker, and it folds into the definitive pass rather than being run separately
now (its criteria are a subset).

**What it needs, which already exists:** the **claim-gold slice** and the **per-slice sub-oracle** the spike's
data hand built (`tmp/spike-rk/gold/`) — deliberately scored against the *slice* sub-oracle, never the full
answer key, so the result is not dominated by which documents are in the slice. **One repair first:** the
sub-oracle currently grades twelve entries `confirmed` on a single source, which makes the yardstick more
confident than the system it scores (`tmp/conv/FOR-DATA-C-sub-oracle-single-source-confirm.md`). **Fix that
before the bake-off consumes it**, or every candidate is measured against a flattering ruler.

**And the honest posture stands** (§8): the gating preconditions are **pass/fail, not weighted** — the winner must
keep the **VLM imagery path** whole, must be **live-runnable in the shipped image** *and* be the producer that
freezes the seed bundles (so KEYLESS≡LIVE holds **by construction**), and must be a **pinned** model id, never a
floating `-latest` alias. If only the incumbent can actually be exercised, the outcome is **"the incumbent
stays"** — a legitimate result, but **not** a three-way measurement, and the scorecard must say so rather than
imply a comparison that never ran.

---

## M15 — G19's control fixture collides with G16's cap. The FIXTURE changes, not the cap.

**The collision (real).** `test_g19_*_spec`'s **control** — the must-fuse mirror that proves the namespace/type
gate is not over-blocking — is built from `shared_neighbours` over two `unit`s. But that evidence class is, by the
test hand's own docstring, *"the co-location evidence class and nothing else"* — and **G16 forbids exactly that
from confirming a formation merge**. So G19's control cannot fuse while G16 holds, and the two gates contend.

**Ruling: the fixture is wrong, the cap is right.** The implementer kept the cap and escalated rather than
weakening it — correct, and I want that on the record: **weakening G16 to make G19's control go green is the F8
trap wearing G16's clothing.** A gate must never be relaxed to satisfy another gate's fixture.

**The fix:** G19's control must fuse for a reason **no other gate restrains** — either a **design-layer** pair
(G16 governs the *instance* layer, so co-location does not apply), or two units sharing a **composite
`(service_branch, designator)`** identifier, which is a unit-level discriminator and therefore *legitimately*
confirms under G16. Either removes the contention without touching a cap.

**The general lesson, worth carrying to S4:** a gate's **control** must be built from an evidence class that no
*other* gate restrains. Otherwise the two gates contend and the pressure lands on whichever cap is easier to
loosen — which is precisely how a safety property gets traded away to make a test green.

## M14 — third consequence, from the implementer

With the flag on, the coref **producer fires**, and **32 scripted-client tests exhaust their queued responses**.
So the keyed re-record commit must carry those **second queued responses** with it — otherwise turning the flag
on breaks 32 tests for a reason unrelated to identity, and the noise buries whatever the re-record actually did.

---

## M16 — the bake-off is a genuine THREE-WAY measurement (user, 2026-07-25)

**Candidates fixed by the user:** **Opus 5** · **Gemini Flash 3.6** · **GPT 5.6 Sol**. All three keys are in
`osint/.env` (verified present by name only; values never read or printed).

**This retires §8's honest fallback.** §8 said GPT had *no client and no provisioned key* and that
`google-genai` was *absent from the shipped image*, so the stated fallback was **"if only Anthropic can be
exercised, 'the harness decides' collapses to 'the incumbent stays'."** Measured now: **all three SDKs import
cleanly** (`anthropic`, `google.genai`, `openai`) — so that note is **stale** and the fallback no longer applies.
A real three-way comparison is possible, and the scorecard must therefore report one rather than a default.

**Remaining build work, small:** two of the three clients already exist (`AnthropicExtractionClient`,
`GeminiExtractionClient`, behind the `ExtractionClient` Protocol + `build_extraction_client` factory), so
**GPT needs one new client class** — the seam is already abstracted, which is why this is a class and not a
refactor.

**What does NOT relax.** The gating preconditions stay **pass/fail, not weighted** (§8): the winner must keep the
**VLM imagery path** whole, must be **live-runnable in the shipped image** *and* be the producer that **freezes
the seed bundles** (so KEYLESS≡LIVE holds by construction), and must be a **pinned** model id — never a floating
`-latest` alias, which would break both reproducibility and the frozen seed. And the **no-sampling-params** rule
holds across providers.

**Two measurement disciplines that now matter more, because a three-way result invites over-reading:**
**N repeated runs per candidate with variance reported**, and a **minimum margin** before a difference counts as
material — a within-noise gap is reported as **"no measured difference"**, not as a winner. Re-extraction is
**confirmed non-deterministic** on a small slice, so without this a three-way scorecard will manufacture a
ranking out of run-to-run jitter.

**And the ruler must be fixed first** (unchanged from the corrected M14): repair the sub-oracle's twelve
single-source `confirmed` entries before the bake-off consumes it, or all three candidates are measured against a
flattering yardstick.
