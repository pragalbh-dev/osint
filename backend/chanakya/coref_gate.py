"""D-13.17's **deterministic** coreference gate — pure, and shared by the producer and the consumer.

**Why this module exists, and why it lives at the package root.** An "authoritative" coref pair is a Phase-1
bootstrap trigger: it merges at hardcoded confidence 1.0 and **bypasses banding entirely**, so no cap
restrains it. Authorising a category therefore authorises an uncapped fusion on a **model-chosen label**, and
the only thing that makes that defensible is a *structural precondition any reader can re-derive*.

The first cut of this stage evaluated the gate at ingest and stamped a verdict on the claim, which the resolver
then trusted. That was wrong in a way the independent suite caught immediately: **a fixture (or an operator, or
an auditor) holding a config bundle and a claim log could not turn the policy on**, because the deciding input
was an artifact only the producer knew how to write. A gate whose verdict cannot be recomputed from the
evidence is not a structural check — it is a second self-report, one layer down.

So the conjuncts that *are* re-derivable live here, as pure string predicates over what rides the claim (the
verbatim spans and the two surface forms), and **both** sides call them: ``ingest.coref`` when it stamps its
audit trail, and ``resolve._coref_pairs`` when it decides the bind. One definition, so the producer and the
consumer can never disagree about what licensed a merge.

The one conjunct that genuinely cannot be recomputed downstream is *"each span occurs verbatim in the
document"* — the document is not in the graph. That is enforced at ingest, where the text exists, and a claim
only comes into being if it passed. The anaphor gate is likewise ingest-only (it needs the document's whole
mention inventory), which is why D-13.17 attaches its own conditional: **if the positive gate is not
available, ``UNAMBIGUOUS_ANAPHOR`` reverts to raise-only.**

Pure: no clock, no RNG, no I/O, no config literals (every threshold is passed in). Safe under ``rebuild()``.
"""

from __future__ import annotations

#: The three evidence categories the extractor may claim, named here because this is the module BOTH sides
#: import. The root is the only home that works: ``resolve`` must never import ``ingest`` (``rebuild()``
#: imports ``resolve`` and ``ingest`` reaches the LLM client — gate G1), and ``ingest`` must never import a
#: use-case module such as ``resolve`` (gate G9). A pure predicate module beside ``edge_direction`` satisfies
#: both, which is what keeps this ONE definition instead of two that would drift.
EXPLICIT_EQUIVALENCE = "EXPLICIT_EQUIVALENCE"
NAME_VARIANT = "NAME_VARIANT"
UNAMBIGUOUS_ANAPHOR = "UNAMBIGUOUS_ANAPHOR"


def collapse(text: str) -> str:
    """Whitespace-collapsed text — the one normalisation a verbatim-span check may apply."""
    return " ".join(text.split())


def value_tokens(text: str) -> list[str]:
    """Alphanumeric tokens of a surface form, casefolded. ``HQ-9/P`` → ``['hq', '9', 'p']``."""
    kept = "".join(c.casefold() if c.isalnum() else " " for c in text)
    return kept.split()


def paren_wraps(quote: str, form: str) -> bool:
    """Is ``form`` wrapped in a parenthetical inside ``quote``? — "Full Name (SHORT)", the commonest marker."""
    folded = collapse(quote).casefold()
    inner = collapse(form).casefold()
    return any(f"{open_}{inner}{close}" in folded for open_, close in (("(", ")"), ("[", "]"), ("（", "）")))


def differs_only_by_a_mark(a: str, b: str, min_descriptor_len: int | None) -> bool:
    """Is the longer of two surface forms the shorter plus a **MARK** rather than a WORD? (Ruling M1.)

    **The hole this closes.** A licensing span can satisfy every other conjunct — it occurs verbatim, it names
    both surface forms, and it carries a parenthetical marker — while the equivalence is **wrong**. The shape
    is a mark-vs-name collision: ``"<Design> (<Design>/X)"`` reads exactly like an alias declaration ("Full
    Name (SHORT)") but in fact *distinguishes two variants*. Nothing downstream reliably saves it: the grade
    floor cannot (a good source writes exactly that sentence), and the D-13.18 decline only fires if the two
    members happen to carry a conflicting critical discriminator — two marks of one design often conflict on
    nothing at all. And a marker vocabulary built as a token list can **never** catch it, because the marker
    genuinely is present.

    **The test already exists in config and encodes precisely this distinction** — the containment bootstrap's
    ``containment_min_descriptor_len``: *"HT-233" + "engagement" (a WORD) is the same radar described more
    fully; "HQ-9" + "P" (a MARK) is a different missile.* Reused here rather than duplicated, so there is one
    threshold for one idea (gate G6).

    Returns True — meaning **the equivalence is not licensed** — when the shorter form is a head-anchored
    prefix of the longer and the first token the longer one adds is not a word of at least the configured
    length. Two names that are not in a containment relation at all return False: they are genuinely different
    names, and this conjunct has nothing to say about them.

    Unset knob ⇒ the test cannot run, and it fails **closed**. An ungated conjunct on the strongest fusion
    path in the system would be worse than a missing feature.
    """
    ta, tb = value_tokens(a), value_tokens(b)
    if not ta or not tb or ta == tb:
        return False
    short, long_ = (ta, tb) if len(ta) < len(tb) else (tb, ta)
    if len(short) >= len(long_) or long_[: len(short)] != short:
        return False
    if min_descriptor_len is None:
        return True  # fail CLOSED: unable to test the one thing separating an alias from a variant
    head = long_[len(short)]
    return not (head.isalpha() and len(head) >= min_descriptor_len)


def explicit_equivalence(
    spans: list[str], anchor_name: str, member_name: str, markers: tuple[str, ...],
    min_descriptor_len: int | None = None, documents: int = 1,
) -> tuple[bool, str]:
    """D-13.17's ``EXPLICIT_EQUIVALENCE`` gate — ``(passed, why)``, computable by any holder of the claim.

    **Four** conjuncts, all structural, all re-derivable from what rides the claim:

    1. every licensing span occurs verbatim in the document. Enforced at ingest (the document lives there), so
       here it is a *precondition* — a claim exists only if it held;
    2. the spans **together** contain both members' surface forms. Ruling M2: the evidence is a *set* of spans
       from one document, not one contiguous span — the corpus contains equivalences documents really do
       assert whose two forms sit tens of lines apart or in different fields of one record, and a one-span
       rule would make the system withhold on those. Multiple spans make the evidence *findable*, never
       *stronger*;
    3. some span carries a **configured equivalence marker** — a term from the declared vocabulary, or a
       parenthetical wrapping one of the two forms. This is what stops the gate collapsing into "the two names
       appear near each other", which is co-occurrence and not equivalence;
    4. **the longer form does not differ from the shorter by only a MARK** (ruling M1). Conjuncts 1–3 are all
       satisfiable by a sentence that *distinguishes* two variants.

    Note the deliberate asymmetry with ``NAME_VARIANT``: that category has no gate and is **permanently**
    raise-only, because an authoritative ``NAME_VARIANT`` *is* the exact-normalised-name auto-merge lane
    D-13.1 exists to delete — rebuilt on another predicate and immune to the very cap that replaced it.
    """
    if not spans:
        return False, "no licensing span survived the verbatim check, so nothing licenses this bind"
    if documents > 1:
        # M2 licenses a set of spans "from the SAME document". Assembling an equivalence out of two
        # documents is a cross-document identity decision — that is Tier 1's job and the analyst's, not the
        # extractor's reading of one document's discourse, and it is precisely the authority in-document
        # coreference does NOT have. Raise-only, with the spans attached.
        return False, (
            f"the licensing spans come from {documents} different documents — no single document states this "
            f"equivalence, so nothing here is an in-document reading. A cross-document identity belongs to "
            f"Tier 1 and to the analyst"
        )
    folded = [collapse(s).casefold() for s in spans]
    forms = [collapse(anchor_name).casefold(), collapse(member_name).casefold()]
    if not all(forms) or any(not any(f in span for span in folded) for f in forms):
        return False, (
            "the licensing spans do not, between them, contain both members' surface forms — a bind whose own "
            "evidence does not name both sides cannot be re-derived by any reader"
        )
    marker = next((m for m in markers if any(collapse(m).casefold() in s for s in folded)), None)
    if marker is None and not any(paren_wraps(s, f) for s in spans for f in (anchor_name, member_name)):
        return False, (
            "the licensing spans name both forms but carry no declared equivalence marker and no "
            "parenthetical wrapping either form — co-occurrence is not a stated equivalence"
        )
    if differs_only_by_a_mark(anchor_name, member_name, min_descriptor_len):
        return False, (
            f"the longer form extends the shorter by a MARK, not a word — '{anchor_name}' vs "
            f"'{member_name}'. A parenthetical mark reads exactly like an alias declaration while in fact "
            f"distinguishing two variants, and no marker vocabulary can tell them apart because the marker "
            f"really is present. A name extended by a WORD is the same thing described more fully; a name "
            f"extended by a mark or a number is a different model (M1)"
        )
    how = f"equivalence marker '{marker}'" if marker else "a parenthetical wrapping one form"
    across = f" across {len(spans)} verbatim spans" if len(spans) > 1 else ""
    return True, (
        f"the licensing evidence contains both surface forms{across} and {how}, and the two forms differ by "
        f"more than a mark"
    )
