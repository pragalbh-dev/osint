"""What actually reaches the model — the system prompt and the tool schema — and what we then score.

Everything a model can act on arrives through exactly two surfaces: the system prompt, and the JSON schema
of the forced tool. Pydantic ships every class docstring and ``Field(description=…)`` **verbatim** inside
that schema, so those strings are not developer notes — they are instructions to a reader who has never seen
this codebase. Three defects of that kind were measured in the extractor bake-off and are locked shut here:

* **the four discriminators were scored but never asked for.** They reached the model only as field
  descriptions on an optional nested block whose own docstring ended "Populated by the model from S1; read by
  nothing yet" — 13.4% of the composite weight on a field the prompt never requested and the schema described
  as inert. Both candidates scored a perfect 1.000 on structured-output compliance: they filled exactly what
  we asked for.
* **the coreference evidence enum lived only in the prompt.** ``evidence`` shipped as a bare nullable string,
  so a correct answer in a slightly different shape (the label with its reasoning appended) was dropped
  without a trace — 7 clusters for one candidate.
* **internal cross-references leaked into the schema** — Sphinx roles, decision ids, doc section numbers.

These tests assert the *ask*, never a phrasing the gold happens to use. Asking for what we grade is the
precondition for the measurement meaning anything; wording the ask to match one answer key is overfitting,
so nothing here checks a value, a vocabulary, or a count.
"""

from __future__ import annotations

import json
import logging

from chanakya.ingest import coref
from chanakya.ingest.extract import _SYSTEM_BASE, _SYSTEM_PROMPTS, SCHEMAS

#: Markup and internal references that mean nothing to a model reading the tool schema cold.
_CODEBASE_ONLY = (
    ":class:", ":func:", ":meth:", ":mod:", ":data:", "``",
    "spine/", "plan §", "EVAL RCA", "D-P4", "D-13", "read by nothing",
)


def _model_facing_text(schema: dict) -> str:
    """Every description string in a tool schema — the prose the provider actually shows the model."""
    out: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {"description", "title"} and isinstance(value, str):
                    out.append(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(schema)
    return "\n".join(out)


# ── defect 1: ask for the discriminators, in the prompt ────────────────────────────────────────────

def test_the_prompt_asks_for_the_discriminator_block() -> None:
    """The prompt must *request* the context block, not merely leave one available in the schema.

    Verified by string count over the whole prompt block, the bake-off diagnosis found **zero** occurrences
    of ``context``, ``discriminat*``, ``operator``, ``individuat*``, ``geography`` or "tell apart".
    """
    assert "`context`" in _SYSTEM_BASE, (
        "the system prompt never names the `context` block, so the four discriminators are available in the "
        "schema and unrequested in the instruction — which is the state that scored 13.4% of the composite "
        "on a field we never asked for"
    )
    lowered = _SYSTEM_BASE.lower()
    assert "tell that thing apart" in lowered or "tell it apart" in lowered, (
        "the prompt asks for the block without saying what a discriminator is FOR. The purpose is what "
        "generalises to a document no annotator has touched: it is the detail that lets a reader tell two "
        "similar things apart"
    )


def test_the_prompt_names_all_four_discriminator_slots_by_their_meaning() -> None:
    """Each of the four slots must be recognisable from the prompt alone — who, where, what-called, when."""
    lowered = _SYSTEM_BASE.lower()
    for slot, cue in (
        ("operator", "operates or owns"),
        ("geography", "where it is"),
        ("designation", "designator or reference number"),
        ("time", "that description held"),
    ):
        assert cue in lowered, f"the prompt does not ask for the {slot} discriminator (looked for {cue!r})"


def test_the_prompt_forbids_inventing_a_discriminator_in_the_same_breath() -> None:
    """Asking harder for a field must not buy capture at the cost of fabrication.

    There is a separately scored line for exactly this trade (``discriminator_fabrication_avoidance``), and
    an invented discriminator is worse than a missing one: it manufactures identity evidence about a thing.
    So the ask and the absence rule ship together, not in different paragraphs.
    """
    lowered = _SYSTEM_BASE.lower()
    assert "leave the rest empty" in lowered, "the prompt never says an unstated slot stays empty"
    assert "manufactures identity evidence" in lowered, (
        "the prompt asks for discriminators without stating the cost of guessing one — the one place where "
        "asking harder for a scored field could make the extraction worse"
    )


# ── defect 3: the unit of analysis ─────────────────────────────────────────────────────────────────

def test_the_prompt_states_the_unit_of_analysis() -> None:
    """One item = one stated fact. Unstated, two reasonable extractors differ severalfold on claim count.

    Measured: ~208 claims/run against ~149 for the other candidate, and one model's own count swung 174→227
    across five runs of the *same* documents. This asserts the *grain* is stated — never that the count is
    lower, which would be optimising for extracting less from a document.
    """
    lowered = _SYSTEM_BASE.lower()
    assert "one item per stated fact" in lowered, "the prompt never says what one item IS"
    assert "one item per mention" in lowered and "subject-relation-object" in lowered, (
        "the grain rule must cover both halves — a thing named repeatedly is one item, and a relationship is "
        "one item per stated subject-relation-object"
    )
    for terse in ("be concise", "be brief", "at most", "no more than", "limit the number"):
        assert terse not in lowered, (
            f"the prompt contains {terse!r}. Capping emissions raises precision against a curated gold and "
            "optimises for extracting LESS from a document, which is the opposite of what an OSINT "
            "extractor is for"
        )


def test_the_grain_rule_cannot_be_read_as_a_licence_to_over_merge() -> None:
    """The one way a grain rule could do harm — and the archetypal harm in this system.

    "One item per thing" read loosely says "CPMIEC and China Precision Machinery Import-Export Corporation
    are obviously one thing, so make them one item" — which pre-empts the licensed coreference pass, discards
    the alias evidence, and is an over-merge performed by the extractor. The rule is therefore keyed to the
    same *name*, and the exception is stated inside the same sentence rather than relying on the
    identity paragraph above it.
    """
    lowered = _SYSTEM_BASE.lower()
    assert "the same name appears several times" in lowered, (
        "the grain rule is keyed to a THING rather than to a repeated NAME, so it can be read as permission "
        "to fold two differently-named mentions into one item — an over-merge, at extraction, uninvited"
    )
    assert "two different names always stay two items" in lowered, (
        "the grain rule does not carry its own exception. The identity paragraph above it says the same "
        "thing, but a rule about collapsing repeats must name the limit where the reader will be applying it"
    )


# ── defect 2: the enum lives where the model can see it ────────────────────────────────────────────

def test_the_coreference_evidence_enum_is_in_the_schema() -> None:
    """The three legal labels must be offered, not just enforced. They used to live only in the prompt."""
    schema = coref.CoreferenceClusters.model_json_schema()
    evidence = schema["$defs"]["CoreferenceCluster"]["properties"]["evidence"]
    offered = [
        value
        for branch in evidence.get("anyOf", [evidence])
        for value in branch.get("enum", [])
    ]
    assert offered == list(coref.EVIDENCE_CATEGORIES), (
        f"the schema offers {offered} but the code accepts {list(coref.EVIDENCE_CATEGORIES)}. A model can "
        "only answer in a shape it was shown; anything else it emits is a correct answer we refuse."
    )
    assert evidence.get("description"), (
        "the enum has no description, so the labels are named without being explained — the model has to "
        "guess which reading each one covers"
    )


def test_an_uninterpretable_evidence_label_is_loud(caplog) -> None:
    """A dropped cluster is a discarded answer. Silence here cost one candidate 7 of them, unrecorded."""
    mentions = [
        coref.Mention(1, "China Precision Machinery Import-Export Corporation", "manufacturer", "c-1"),
        coref.Mention(2, "CPMIEC", "manufacturer", "c-2"),
    ]
    text = "China Precision Machinery Import-Export Corporation (CPMIEC) shipped it."
    payload = {"clusters": [{
        "member_ids": [1, 2],
        "evidence": "EXPLICIT_EQUIVALENCE — CPMIEC is the parenthetical acronym for the full name",
        "licensing_quotes": ["China Precision Machinery Import-Export Corporation (CPMIEC)"],
    }]}

    with caplog.at_level(logging.WARNING, logger="chanakya.ingest.coref"):
        assert coref.valid_clusters(payload, mentions, text, []) == [], (
            "an evidence label outside the three the schema names must still be refused — the rail is not "
            "loosened, it is made audible"
        )
    assert caplog.records, (
        "the cluster was dropped in silence. The label is decorated, but the *answer* was right; nothing "
        "downstream, and no reliability metric, can see that we threw it away."
    )


def test_a_legal_but_disabled_category_says_which_switch_dropped_it(caplog) -> None:
    """Deployment policy is a different event from a payload we cannot read, and it says so separately."""
    mentions = [
        coref.Mention(1, "8 AD Bn", "unit", "c-1"),
        coref.Mention(2, "8 Air Defence Battalion", "unit", "c-2"),
    ]
    text = "8 AD Bn, written elsewhere as 8 Air Defence Battalion."
    payload = {"clusters": [{"member_ids": [1, 2], "evidence": coref.NAME_VARIANT,
                             "licensing_quotes": ["8 AD Bn, written elsewhere as 8 Air Defence Battalion."]}]}

    with caplog.at_level(logging.INFO, logger="chanakya.ingest.coref"):
        accepted = coref.valid_clusters(payload, mentions, text, [],
                                        categories=(coref.EXPLICIT_EQUIVALENCE,))
    assert accepted == [], "a category this deployment disabled must not bind"
    assert any("not enabled on this deployment" in r.message for r in caplog.records), (
        "a cluster refused by configuration must name the switch that refused it, or a deployment looks "
        "broken rather than conservative"
    )
    assert not any(r.levelno >= logging.WARNING for r in caplog.records), (
        "configured policy working as configured is not a warning — conflating the two makes the real "
        "payload defect invisible in the noise"
    )


# ── the whole model-facing surface: no codebase-only text ───────────────────────────────────────────

def test_no_internal_cross_reference_reaches_the_model() -> None:
    """Sphinx roles, decision ids and doc sections in a docstring are shipped to the model verbatim.

    They cost tokens, they explain nothing to a reader who has never seen this repo, and in one measured
    case the shipped text told the model the field it was filling was read by nothing. Internal reasoning
    belongs in ``#`` comments, which pydantic does not ship.
    """
    surfaces = {**SCHEMAS, "cluster_coreferences": coref.CoreferenceClusters}
    for name, model in surfaces.items():
        text = _model_facing_text(model.model_json_schema())
        leaked = sorted({token for token in _CODEBASE_ONLY if token in text})
        assert not leaked, (
            f"the {name} tool schema ships codebase-only text to the model: {leaked}. Move the reasoning "
            "into a comment above the class — a docstring here is model-facing text."
        )


def test_every_format_prompt_inherits_the_shared_base() -> None:
    """One base, six formats. A per-format prompt that forked would silently drop the shared asks.

    The prompt is also shared by every extraction candidate, which is what makes a change here a change to
    the instrument rather than an advantage for one model.
    """
    for fmt, prompt in _SYSTEM_PROMPTS.items():
        assert prompt.startswith(_SYSTEM_BASE), f"{fmt} no longer builds on the shared base prompt"


def test_the_schema_stayed_lean_while_the_prompt_grew() -> None:
    """A longer prompt spends compliance, so the additions must not also bloat the schema.

    Both candidates score a perfect 1.000 on structured-output reliability — they do exactly what we ask,
    and that is an asset. Cleaning the internal prose out of the schema paid for the instruction we added:
    this is a floor against the next person adding an essay to a field description.
    """
    for fmt, model in SCHEMAS.items():
        size = len(json.dumps(model.model_json_schema()))
        assert size < 14_000, (
            f"the {fmt} tool schema is {size} bytes of model-facing JSON. It was ~15k when a third of it "
            "was internal commentary; keep the descriptions instructional and short."
        )
