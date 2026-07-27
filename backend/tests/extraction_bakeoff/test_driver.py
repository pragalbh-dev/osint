"""The driver: the slice it assembles, the spend it declares, and the dry run that costs nothing.

The driver is where a bake-off silently becomes a different experiment than the one it reports — a document
quietly dropped, an image never shown, a cost understated. So the things pinned here are the ones whose
failure would be invisible on the scorecard.

Entirely offline: no candidate client is built, no key is read, no API call is made.
"""

from __future__ import annotations

import json

import pytest

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest.lane import DocInput
from eval.extraction import driver


@pytest.fixture(scope="module")
def bundle():
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _gold(tmp_path, docs, doc_paths):
    path = tmp_path / "claim-gold.bakeoff.json"
    path.write_text(json.dumps({"docs": docs, "doc_paths": doc_paths, "claims": []}), encoding="utf-8")
    return path


# ── the slice comes from the gold, and it is complete or it raises ─────────────────────────────────

def test_the_slice_is_read_off_the_gold_not_hardcoded(tmp_path, bundle) -> None:
    """One document in the gold's `docs` list → exactly one document in the run."""
    path = _gold(tmp_path, ["d02_ispr_induction"],
                 {"d02_ispr_induction": "corpus/scenarios/hq9p_primary/docs/d02_ispr_induction.txt"})
    docs = driver.build_slice(path, bundle)
    assert [d.source_id for d in docs] == ["d02_ispr_induction"]
    # The source type is the registry's, never a guess: it selects the extraction tool.
    assert docs[0].source_type == bundle.sources.as_map()["d02_ispr_induction"].source_type


def test_a_gold_with_no_documents_refuses_rather_than_running_an_empty_comparison(tmp_path,
                                                                                 bundle) -> None:
    with pytest.raises(ValueError, match="declares no documents"):
        driver.build_slice(_gold(tmp_path, [], {}), bundle)


def test_a_labeled_document_absent_from_the_registry_raises(tmp_path, bundle) -> None:
    """Guessing a source type would measure the guess — it picks the extraction tool."""
    with pytest.raises(ValueError, match="not in the pipeline's source registry"):
        driver.build_slice(_gold(tmp_path, ["not_a_real_doc"], {"not_a_real_doc": "x.txt"}), bundle)


def test_a_labeled_document_missing_from_disk_raises(tmp_path, bundle) -> None:
    """A slice one document short would understate recall for everyone, equally and invisibly."""
    path = _gold(tmp_path, ["d02_ispr_induction"], {"d02_ispr_induction": "corpus/nope/missing.txt"})
    with pytest.raises(FileNotFoundError):
        driver.build_slice(path, bundle)


def test_the_file_string_is_the_repo_relative_path_the_gold_cites(tmp_path, bundle) -> None:
    """Load-bearing: the negative gold's span hooks match on this string. A basename or an absolute path
    would match nothing, and "nothing excluded, no traps hit" looks exactly like a clean run."""
    rel = "corpus/scenarios/hq9p_primary/docs/d02_ispr_induction.txt"
    docs = driver.build_slice(_gold(tmp_path, ["d02_ispr_induction"], {"d02_ispr_induction": rel}),
                              bundle)
    assert docs[0].file == rel


# ── the image: without it every candidate is disqualified ─────────────────────────────────────────

def test_the_real_corpus_image_rides_along_with_its_write_up(tmp_path, bundle) -> None:
    """The imagery gate is judged on a real standalone-image call. The frame is not bolted on here — it is
    registered as a co-located image of d17b, exactly as the seed recorder loads it."""
    rel = "corpus/scenarios/hq9p_primary/docs/d17b_withheld_gap.txt"
    docs = driver.build_slice(_gold(tmp_path, ["d17b_withheld_gap"], {"d17b_withheld_gap": rel}), bundle)
    frames = driver.image_frames(docs)
    assert frames == ["corpus/scenarios/hq9p_primary/docs/d17b_withheld_gap.png"]
    assert docs[0].images and isinstance(docs[0].images[0][0], bytes)
    assert docs[0].images[0][0][:4] == b"\x89PNG"          # a real frame, not a placeholder


def test_the_full_slice_carries_exactly_one_image(tmp_path, bundle) -> None:
    gold = settings.repo_root() / "tmp/spike-rk/gold/claim-gold.bakeoff.json"
    if not gold.exists():
        pytest.skip("the adapted gold is not present in this checkout")
    docs = driver.build_slice(gold, bundle)
    assert len(docs) == 7
    assert driver.image_frames(docs) == [
        "corpus/scenarios/hq9p_primary/docs/d17b_withheld_gap.png"]


# ── the spend plan ────────────────────────────────────────────────────────────────────────────────

def _plan(**kw):
    docs = [DocInput(raw="text", source_id=f"d{i}", source_type="official", file=f"d{i}.txt")
            for i in range(7)]
    docs[0] = DocInput(raw="text", source_id="d0", source_type="satellite", file="d0.txt",
                       images=((b"\x89PNG", "frame.png"),))
    defaults = dict(candidate_ids=["a", "b", "c"], runs_per_candidate=5, coref_pass=True, dry=False)
    return driver.plan_spend(docs, **{**defaults, **kw})


def test_the_plan_states_a_floor_and_a_ceiling_because_pass_two_is_conditional() -> None:
    """7 text docs + 1 frame = 8 with no pass 2; + 7 more when pass 2 dispatches on every document."""
    plan = _plan()
    assert (plan.calls_per_run_floor, plan.calls_per_run_ceiling) == (8, 15)
    assert (plan.total_floor, plan.total_ceiling) == (8 * 5 * 3, 15 * 5 * 3)
    assert (plan.total_floor, plan.total_ceiling) == (120, 225)


def test_turning_the_coref_pass_off_halves_the_ceiling() -> None:
    plan = _plan(coref_pass=False)
    assert plan.calls_per_run_ceiling == plan.calls_per_run_floor == 8
    assert "coref_binding will be UNMEASURED" in plan.render()


def test_the_plan_names_the_image_it_will_show() -> None:
    assert "frame.png" in _plan().render()


def test_a_dry_plan_says_nothing_is_billed_and_a_live_plan_says_it_spends() -> None:
    assert "ZERO API calls" in _plan(dry=True).render()
    assert "nothing is billed" in _plan(dry=True).render()
    assert "THIS SPENDS BUDGET" in _plan(dry=False).render()


def test_restricting_candidates_reduces_the_projected_spend() -> None:
    assert _plan(candidate_ids=["a"]).total_ceiling == 15 * 5


# ── not spending on a candidate that cannot win ───────────────────────────────────────────────────

def test_a_candidate_failing_a_dry_gate_is_named_before_anything_is_spent() -> None:
    """A gate is pass/fail to win, so calls spent on a gate-failing candidate buy nothing that can change
    the outcome. On the shipped config this is a third of the budget."""
    from .fixtures import bakeoff_config

    config = bakeoff_config(candidates=[
        {"id": "clean", "label": "Clean", "provider": "test", "model_id": "clean-2026-01-01",
         "client_module": "chanakya.ingest.client", "client_class": "ScriptedExtractionClient",
         "sdk_module": "json", "key_env": "K", "multimodal": "native", "freezes_seed": True,
         "pricing": None},
        {"id": "floating", "label": "Floating", "provider": "test", "model_id": "some-model-latest",
         "client_module": "chanakya.ingest.client", "client_class": "ScriptedExtractionClient",
         "sdk_module": "json", "key_env": "K", "multimodal": "native", "freezes_seed": True,
         "pricing": None},
    ])
    blocked = driver.blocked_before_spending(
        config, candidate_ids=["clean", "floating"],
        evidence={c.id: None for c in config.candidates}, require_key=False)
    assert "floating" in blocked and "pinned_model_id" in blocked["floating"]


def test_an_unknown_imagery_gate_counts_as_blocked_not_as_unproven() -> None:
    """UNKNOWN blocks everywhere else, so it must block here — otherwise the driver spends a full budget
    on candidates whose imagery gate will disqualify every one of them at the end."""
    from .fixtures import bakeoff_config

    config = bakeoff_config()
    blocked = driver.blocked_before_spending(
        config, candidate_ids=[c.id for c in config.candidates], evidence={}, require_key=False)
    assert set(blocked) == {c.id for c in config.candidates}
    assert all("vlm_imagery_path" in why for why in blocked.values())


# ── the dry-run client ────────────────────────────────────────────────────────────────────────────

def test_the_dry_client_names_mentions_verbatim_from_the_document_it_was_given() -> None:
    """Not cosmetic: the pipeline drops a claim whose quote does not support its surface, a dropped claim
    yields no mentions, and fewer than two mentions means pass 2 never dispatches — so a double emitting
    invented names would quietly under-exercise the pass that doubles the bill."""
    text = "North Ridge Foundry supplies the Type-7 Coupler to the Eastvale Pumping Station."
    payload = driver.DryRunClient(model_id="m").extract(
        tool_name="extract_prose_claim", input_schema={}, system="", text=text)
    names = [payload["manufacturers"][0]["name"], payload["components"][0]["name"]]
    assert all(name in text for name in names)
    assert payload["manufacturers"][0]["source_quote"] in text


def test_the_dry_client_declines_to_invent_a_coreference_decision() -> None:
    """A dry run must not make the top-weighted criterion read as measured on a number no model produced."""
    from chanakya.ingest import coref

    assert driver.DryRunClient(model_id="m").extract(
        tool_name=coref.TOOL_NAME, input_schema={}, system="", text="A and B.") == {}


def test_the_dry_client_answers_the_image_lane_so_the_gate_has_evidence() -> None:
    """The imagery gate asks whether a standalone-image call returned, never what it said."""
    assert driver.DryRunClient(model_id="m").read_image(
        tool_name="t", input_schema={}, system="", image=b"\x89PNG", media_type="image/png") == {}


def test_the_dry_factory_never_reads_a_key_or_builds_a_real_client() -> None:
    class Candidate:
        model_id = "pinned-1"
        key_env = "SHOULD_NEVER_BE_READ"

    client = driver.dry_client_factory(Candidate(), 1)
    assert isinstance(client, driver.DryRunClient) and client.model_id == "pinned-1"


def test_a_document_with_too_few_mentions_yields_nothing_rather_than_an_invention() -> None:
    assert driver.DryRunClient(model_id="m").extract(
        tool_name="extract_prose_claim", input_schema={}, system="", text="the.") == {}
