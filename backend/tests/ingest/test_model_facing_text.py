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

**The guards below are written to hold over the WHOLE surface, not over the handful of strings that happened
to be fixed.** Five docstrings were rewritten when this rule was found; dumping every description in every
schema then turned up more of the same kind, in the two imagery tools nobody had thought to look at. So the
checks are properties of *every* description on *every* surface — it exists, and it does not talk about our
own machinery — rather than assertions pinned to the five. ``_surfaces`` is the one place that has to stay
current; everything else follows from it.
"""

from __future__ import annotations

import json
import logging
import re

from chanakya.ingest import coref, imagery
from chanakya.ingest.dedup import dedup_within_doc
from chanakya.ingest.extract import _SYSTEM_BASE, _SYSTEM_PROMPTS, SCHEMAS
from chanakya.schemas import ClaimRecord, DocRef, Triple

#: Markup and internal references that mean nothing to a model reading the tool schema cold.
_CODEBASE_ONLY = (
    ":class:", ":func:", ":meth:", ":mod:", ":data:", "``",
    "spine/", "plan §", "EVAL RCA", "D-P4", "D-13", "read by nothing",
)

#: Names of **our own machinery**. A description that reaches for one of these is describing what the
#: pipeline does with the value instead of what the document must say — the general form of the defect that
#: shipped "read by nothing yet" to the model, and of the over-merge licence that told the extractor what the
#: resolver would do if a field came back blank. The model cannot act on any of it, and where it *can*, the
#: action is to game a downstream consequence. Word-boundary matched, case-insensitive.
_PIPELINE_INTERNAL = (
    r"same-as", r"distinct-from", r"polarit\w*", r"\bnodes?\b", r"\bedges?\b", r"\breferents?\b",
    r"\bresolver\b", r"\bontolog\w+", r"\bdownstream\b", r"\bpipeline\b", r"\bschema\b",
    r"the graph\b", r"pass[- ]2", r"read by nothing",
    # "claim" is this project's unit of analysis, not a word the model needs; it is also how the two
    # taxonomy-flavoured descriptions gave themselves away ("the many-claims-per-row unit"). The model-facing
    # verb for what a document does is "states".
    r"\bclaims?\b",
)

#: Ways of asking a model to rank the spans it cites. There is no such choice to make: a within-document
#: restatement folds in ``dedup_within_doc``, which keeps the **union** of every span cited — asserted for
#: real in ``test_the_pipeline_keeps_every_cited_span_so_the_prompt_never_ranks_them``. An instruction to pick
#: the best one invites the model to paraphrase or splice, against two quote-grounded floor metrics.
_QUOTE_RANKING = ("clearest quote", "best quote", "most representative quote", "single best", "strongest quote")


def _descriptions(schema: dict) -> list[tuple[str, str]]:
    """Every ``description`` in a tool schema, with the JSON path it sits on.

    Titles are excluded: pydantic derives those from the class/field name, so they are not prose anyone wrote.
    """
    out: list[tuple[str, str]] = []

    def walk(node: object, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "description" and isinstance(value, str):
                    out.append((path or "/", value))
                else:
                    walk(value, f"{path}/{key}")
        elif isinstance(node, list):
            for item in node:
                walk(item, path)

    walk(schema, "")
    return out


def _model_facing_text(schema: dict) -> str:
    """Every description *and title* in a tool schema — the prose the provider actually shows the model."""
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


def _surfaces() -> dict[str, type]:
    """**Every** schema a model is ever shown — the audit is only as wide as this function.

    The six extraction tools, the coreference tool, and the two imagery tools. The imagery pair was missed on
    the first pass of this rule (the audit stopped at the seven text schemas) and was carrying exactly the
    same defects: doubled-backtick markup, and a docstring explaining which *stage* owns identification to a
    model that has only a picture. Any new forced tool belongs here on the day it is written.
    """
    return {
        **SCHEMAS,
        "cluster_coreferences": coref.CoreferenceClusters,
        "read_overhead_image": imagery.ImageryObservation,
        "corroborate_signature": imagery.SignatureCorroboration,
    }


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


def test_the_ask_never_tells_the_model_what_a_blank_field_will_cause() -> None:
    """No downstream consequence, in either direction — that is what turns an ask into an incentive.

    The first draft of this paragraph read "two same-named things stay two things only if their context is on
    the record", one sentence from "leave the rest empty". As an instruction that says: *leave it blank and
    they get merged* — a standing reason to fill a field we also forbid guessing at, pointed straight at the
    archetypal harm (fabricated identity evidence, offered as the way to prevent a wrong fusion). The
    extractor reports what the document says; what a sparse record implies is the resolver's problem, and a
    model told about that consequence can act on it.
    """
    lowered = _SYSTEM_BASE.lower()
    assert "not a judgement about whether two things are the same" in lowered, (
        "the prompt asks for identity context without saying that judging identity is NOT the extractor's "
        "job here. Without that, 'fill the context' reads as 'influence the merge'"
    )
    for consequence in (
        "stay two things only if", "only if their context", "unless their context",
        "if you leave it empty", "if the context is blank", "will be merged", "will be treated as the same",
    ):
        assert consequence not in lowered, (
            f"the prompt tells the model what happens downstream when a context slot is blank ({consequence!r}). "
            "Any such clause is a reason to fill a field the next sentence forbids guessing at."
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


def test_the_identity_paragraph_and_the_grain_rule_cover_disjoint_cases() -> None:
    """Two adjacent rules, one shared case — a repeated name. They must not answer it differently.

    The identity paragraph is about WHAT IS THE SAME THING; the grain rule is about HOW MANY ITEMS to emit.
    Left unscoped they collide on the same sentence of a document: "two same-named things can be two things"
    against "a repeated name is ONE item". A model handed that conflict resolves it differently run to run,
    which surfaces as claim-count instability — the exact metric the grain rule was added to improve. So the
    grain rule names its own scope, and it states the case where a document keeps two same-named things apart.
    """
    lowered = _SYSTEM_BASE.lower()
    assert "about how many items to emit, not about which things are the same" in lowered, (
        "the grain rule does not say what it is about, so it reads as an identity rule that contradicts the "
        "identity paragraph one sentence above it"
    )
    assert "holds two same-named things apart" in lowered, (
        "the grain rule collapses every repeat of a name, with no exception for the document that itself "
        "separates two things of the same name — the one case where the two rules genuinely disagree"
    )


def test_the_pipeline_keeps_every_cited_span_so_the_prompt_never_ranks_them() -> None:
    """The grain rule must not ask for a "clearest" quote — nothing in this system chooses between spans.

    ``dedup_within_doc`` folds a within-document restatement into one claim carrying the **union** of the
    spans cited, precisely so no cited span is discarded. So "one item carrying its clearest quote" described
    something the pipeline does not do, and asked a model to rank spans against two quote-grounded floor
    metrics (``extract_only_stated``, ``citation_faithfulness``) — where the cheapest way to make one span
    cover a whole fact is to splice or paraphrase it. This test asserts both halves: the behaviour, and the
    absence of the ask.
    """
    def restatement(span: tuple[int, int]) -> ClaimRecord:
        return ClaimRecord(
            claim_id="tmp",
            source_id="src-a",
            doc_ref=DocRef(file="d01.txt", span=span, line=1),
            kind="observation",  # type: ignore[arg-type]
            polarity="positive",  # type: ignore[arg-type]
            asserts="relationship",
            payload=Triple(subject="hq-9", predicate="based-at", object="site-7"),
        )

    folded = dedup_within_doc([restatement((0, 10)), restatement((40, 50))])
    assert len(folded) == 1 and [r.span for r in folded[0].doc_refs()] == [(0, 10), (40, 50)], (
        "the fold no longer keeps every stated span, so a prompt clause telling the model to choose one "
        "would now be describing real behaviour — re-read this test's reasoning before changing the prompt"
    )
    lowered = _SYSTEM_BASE.lower()
    for ranking in _QUOTE_RANKING:
        assert ranking not in lowered, (
            f"the prompt asks the model to rank the spans it cites ({ranking!r}). There is no such choice: "
            "the fold above keeps them all, and asking for a best one invites a spliced quote"
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
    for name, model in _surfaces().items():
        text = _model_facing_text(model.model_json_schema())
        leaked = sorted({token for token in _CODEBASE_ONLY if token in text})
        assert not leaked, (
            f"the {name} tool schema ships codebase-only text to the model: {leaked}. Move the reasoning "
            "into a comment above the class — a docstring here is model-facing text."
        )


def test_no_description_describes_our_own_machinery() -> None:
    """The general form of the defect — and the check that catches the ones nobody happened to rewrite.

    Five docstrings were rewritten when this rule was found; dumping all seven schemas turned up more of the
    same kind ("the many-claims-per-row unit", "the perishable sustainment node", "→ a negative-polarity
    observation claim", "the pass-2 output"). None of it is actionable by a reader who has only the document
    in front of them, and where it *is* actionable — a description of what the pipeline will do with the value
    — it invites the model to aim at that outcome instead of at the document. So this is asserted as a
    property of every description on the surface rather than of the five that were noticed.
    """
    for name, model in _surfaces().items():
        for path, text in _descriptions(model.model_json_schema()):
            hits = sorted({
                match.group(0)
                for pattern in _PIPELINE_INTERNAL
                for match in re.finditer(pattern, text, flags=re.IGNORECASE)
            })
            assert not hits, (
                f"{name}{path} describes our machinery to the model: {hits}\n  {text!r}\n"
                "Say what the document must state for this field to be filled. What the pipeline then does "
                "with it belongs in a `#` comment, which pydantic does not ship."
            )


def test_every_object_on_the_surface_carries_a_usable_description() -> None:
    """A class added with no docstring ships to the model as a bare title. Nothing warns you.

    The defect this file exists for was a description that said the wrong thing; the adjacent one is a
    description that says nothing, which is how a field ends up scored and unexplained. Every object in every
    tool schema must carry a description, and it must be an instruction rather than a stub.
    """
    for name, model in _surfaces().items():
        schema = model.model_json_schema()
        objects = {"": schema, **{f"/$defs/{k}": v for k, v in schema.get("$defs", {}).items()}}
        for path, node in objects.items():
            described = (node.get("description") or "").strip()
            assert len(described) > 30, (
                f"{name}{path or ' (the tool itself)'} reaches the model with no usable description "
                f"({described!r}). A model fills what it can read; an undescribed object is a guess we then "
                "score."
            )


def test_the_two_alias_lanes_cannot_be_confused_for_each_other() -> None:
    """``aliases`` and ``distinctions`` share ONE shape and say opposite things. Only the field name differs.

    ``distinctions`` is the veto rail: it is what stops two same-named, co-located things being fused into one
    unit's before-and-after — a fabricated movement, machine-adjudicated off the analyst's queue. A pair
    misfiled into ``aliases`` does not merely lose the veto, it asserts the reverse of what the document said.
    So the direction cannot live only in the shared class docstring, where neither field can be told from the
    other: each field states its own direction, and the shared docstring says the field is what decides.
    """
    lanes: list[tuple[str, dict]] = []
    for name, model in _surfaces().items():
        schema = model.model_json_schema()
        # Both levels: a lane hangs off the tool itself (prose, tender) and off a nested row (customs).
        for where, node in [(name, schema), *[(f"{name}/{k}", v) for k, v in schema.get("$defs", {}).items()]]:
            props = node.get("properties", {})
            if "aliases" in props or "distinctions" in props:
                lanes.append((where, props))
    assert len(lanes) >= 3, (
        f"only {len(lanes)} alias lanes found on the whole surface — the walk has stopped seeing the nested "
        "ones, so this guard would pass while a lane went undescribed"
    )

    for name, props in lanes:
        for field in ("aliases", "distinctions"):
            if field not in props:
                continue
            described = (props[field].get("description") or "")
            assert len(described.strip()) > 30, (
                f"{name}.{field} reaches the model with no direction of its own ({described!r}). Both fields "
                "hold the same shape; the field description is the ONLY thing that says which way the "
                "link runs"
            )
        if "distinctions" in props:
            assert props["aliases"]["description"] != props["distinctions"]["description"], (
                f"{name} gives its same-as and its not-the-same lane identical descriptions, so the veto rail "
                "is indistinguishable from its opposite"
            )
            assert "NOT the same" in props["distinctions"]["description"], (
                f"{name}.distinctions never says it records a NON-identity. It is the veto rail; it has to "
                "read as the opposite of the field beside it"
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

    **The ceiling was 14,000 and is now 17,000, and the reason is a change of contents, not a slipped budget.**
    The original number was set against a ~15k schema *a third of which was internal commentary* — text a
    model cannot act on, which is why deleting it was free. What has been added since is the opposite kind of
    text and had a measured defect behind it: each mention class reached the model as a bare one-line label
    over generic slots, so every type boundary was the model's to guess, and the guesses were wrong in the
    expensive direction — an entire air-defence command recorded as the thing emplaced at a dispersal pad when
    the answer was the battery on it. Each class now states what it IS here and which neighbouring type it is
    confused with, and the three identity-bearing slots say what they identify. That is instruction, and a byte
    of instruction is not interchangeable with a byte of commentary.

    So the size assertion is deliberately no longer the *only* thing standing between a field description and
    an essay — it never could distinguish the two. The guards that actually encode the original defect are
    ``test_no_internal_cross_reference_reaches_the_model`` and
    ``test_no_description_describes_our_own_machinery``, both of which run over every description on the whole
    surface and neither of which was touched. This one stays as a coarse backstop: at 39-41% prose the schemas
    are still mostly structure, and 17k leaves ~600 bytes over the largest of them — enough for a genuine
    addition, not enough for an essay, and it must not be raised again without the same kind of reason.
    """
    for fmt, model in SCHEMAS.items():
        size = len(json.dumps(model.model_json_schema()))
        assert size < 17_000, (
            f"the {fmt} tool schema is {size} bytes of model-facing JSON. Read this test's reasoning before "
            "raising the ceiling: it moved once, for per-type definitions that fixed a measured "
            "type-confusion, and 'my text is useful too' is not that argument. Keep descriptions "
            "instructional and short."
        )
