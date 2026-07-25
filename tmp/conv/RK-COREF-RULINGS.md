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
