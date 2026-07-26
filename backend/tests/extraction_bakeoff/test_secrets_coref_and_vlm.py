"""The three preconditions the bake-off cannot fake: keys, the coref channel, and the imagery gate.

All offline. Nothing here reads the operator's real ``.env``, spends a call, or touches the recorded
evidence file: each test supplies its own path. What is asserted in every case is the same posture the rest
of the harness takes — an unverified thing reports as unverified, and never as a pass.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from chanakya import settings
from chanakya.config.store import ConfigStore
from eval.extraction import coref_channel, secrets, vlm_probe
from eval.extraction.policy import Candidate

from .fixtures import RoutedScriptedClient, bakeoff_config

# ── secrets: names may travel, values may not ─────────────────────────────────────────────────────

def test_a_dotenv_is_parsed_including_export_prefixes_quotes_and_comments() -> None:
    parsed = secrets.parse_env_file(
        "# a comment\n"
        "\n"
        "PLAIN=abc\n"
        "export EXPORTED=def\n"
        'QUOTED="ghi"\n'
        "SINGLE='jkl'\n"
        "SPACED = mno \n"
        "not an assignment at all\n"
        "EMPTY=\n"
    )
    assert parsed == {"PLAIN": "abc", "EXPORTED": "def", "QUOTED": "ghi", "SINGLE": "jkl",
                      "SPACED": "mno", "EMPTY": ""}


def test_loading_returns_only_names_and_the_value_reaches_the_environment(tmp_path, monkeypatch) -> None:
    """The return value is what a report is allowed to print, so it must be names. There is deliberately
    no function in this module that hands back a secret."""
    path = tmp_path / ".env"
    path.write_text("FAKE_PROVIDER_KEY=sk-not-a-real-key\nOTHER_KEY=zzz\n", encoding="utf-8")
    monkeypatch.delenv("FAKE_PROVIDER_KEY", raising=False)
    monkeypatch.delenv("OTHER_KEY", raising=False)

    applied = secrets.load_env_file(path)

    assert applied == ["FAKE_PROVIDER_KEY", "OTHER_KEY"]
    assert not any("sk-not-a-real-key" in name for name in applied)
    import os

    assert os.environ["FAKE_PROVIDER_KEY"] == "sk-not-a-real-key"


def test_an_already_set_variable_wins_over_the_file(tmp_path, monkeypatch) -> None:
    """A shell export is a deliberate act; a file on disk is ambient. Letting the file win is how a
    bake-off ends up measuring a model against a key nobody chose."""
    path = tmp_path / ".env"
    path.write_text("FAKE_PROVIDER_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("FAKE_PROVIDER_KEY", "from-shell")

    assert secrets.load_env_file(path) == []
    import os

    assert os.environ["FAKE_PROVIDER_KEY"] == "from-shell"
    assert secrets.load_env_file(path, override=True) == ["FAKE_PROVIDER_KEY"]
    assert os.environ["FAKE_PROVIDER_KEY"] == "from-file"


def test_an_empty_assignment_is_not_a_key(tmp_path, monkeypatch) -> None:
    """`KEY=` must leave the variable unset, so the exercisable gate keeps reporting the truth."""
    path = tmp_path / ".env"
    path.write_text("FAKE_PROVIDER_KEY=\n", encoding="utf-8")
    monkeypatch.delenv("FAKE_PROVIDER_KEY", raising=False)

    assert secrets.load_env_file(path) == []
    assert secrets.key_names_present(["FAKE_PROVIDER_KEY"]) == {"FAKE_PROVIDER_KEY": False}


def test_a_missing_dotenv_is_a_legitimate_state_not_an_error(tmp_path) -> None:
    assert secrets.load_env_file(tmp_path / "nope.env") == []


def test_the_search_path_reaches_the_main_checkout_from_a_linked_worktree() -> None:
    """Every session here runs in a linked worktree, which is a *sibling* of the main checkout — so
    walking up from the code never finds the ``.env``. If this list stopped including the main worktree,
    every candidate would report "not exercisable" on a machine that has the keys."""
    paths = secrets.candidate_paths()
    assert paths, "no .env location is searched at all"
    assert len(paths) == len(set(paths)), "the same path is searched twice"
    assert all(p.name == ".env" or "env" in p.name.lower() for p in paths)


# ── the coref channel ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def shipped_config():
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


def _suppressed(config: Any) -> Any:
    return coref_channel.without_channel(config)


def test_suppressing_the_channel_is_an_in_memory_edit_that_actually_takes(shipped_config) -> None:
    """The producer block hangs off a nested config model, so the obvious dict-based copy replaces the
    model wholesale and the *whole* credibility config reads back empty — which looks like a much larger
    breakage than the one the operator asked for. ``--no-coref`` is the only cost lever left now that pass
    2 is unconditional, so it has to take precisely and leave the original alone."""
    from chanakya.ingest import coref

    assert coref._coref_cfg(shipped_config)                       # as shipped: pass 2 dispatches
    suppressed = coref_channel.without_channel(shipped_config)
    assert coref._coref_cfg(suppressed) == {}                     # the pipeline itself now declines
    assert coref._coref_cfg(shipped_config)                       # and the original is untouched
    assert suppressed.credibility.source_class_factors            # nothing else was collateral damage
    assert suppressed.credibility.thresholds


def test_the_shipped_config_leaves_the_coref_channel_live(shipped_config) -> None:
    """The staging flags were deleted (design/resolution-redesign), so the shipped config now dispatches
    pass 2 unconditionally and the top-weighted criterion is measurable without any flag flipping.

    This is the assertion that replaced the flag-deletion seam's ``gated_off`` test. It is deliberately
    stated against the SHIPPED config rather than a fixture: what the bake-off must know is whether a real
    run on this deployment can score ``coref_binding``, and nothing else answers that.
    """
    channel = coref_channel.inspect(shipped_config)
    assert channel.tool_name == "cluster_coreferences"        # the channel EXISTS
    assert channel.cluster_field == "clusters[].member_ids"
    assert channel.live and channel.measurable                # and is dispatched
    assert channel.cause == ""
    assert "EXPLICIT_EQUIVALENCE" in channel.categories
    assert "LIVE" in channel.detail


def test_a_suppressed_channel_reads_as_the_config_gap_it_is(shipped_config) -> None:
    """Declining to pay for pass 2 must report as an unconfigured producer, not as a fourth kind of
    dormancy: the harness gained a cost lever, not a new concept, and the remedy names the lever."""
    channel = coref_channel.inspect(_suppressed(shipped_config))
    assert not channel.measurable
    assert channel.cause == coref_channel.PRODUCER_UNCONFIGURED
    assert "--no-coref" in channel.remedy


def test_the_channel_is_read_off_the_real_schema_not_asserted(monkeypatch, shipped_config) -> None:
    """The whole point of the check is that it would go back to "no channel" on its own if S3 were
    reverted — so it reads the shipped pass-2 model, and this proves it by taking the field away."""
    from pydantic import BaseModel

    from chanakya.ingest import coref

    class NoClusters(BaseModel):
        contrasts: list[str] = []

    monkeypatch.setattr(coref, "CoreferenceClusters", NoClusters)
    channel = coref_channel.inspect(shipped_config)
    assert not channel.measurable
    assert "no mention-cluster field" in channel.detail


def test_a_required_coref_metric_refuses_on_a_dormant_channel(shipped_config) -> None:
    config = bakeoff_config(required_metrics=["coref_binding"])
    with pytest.raises(coref_channel.CorefChannelDormant) as excinfo:
        coref_channel.require(_suppressed(shipped_config), config)
    message = str(excinfo.value)
    assert "credibility.coreference" in message
    assert "second extraction call per document" in message
    assert "Do not re-weight it to zero" in message


def test_an_unrequired_coref_metric_does_not_refuse(shipped_config) -> None:
    """Not declaring it required is a *recorded decision to rank without it*, which is allowed. What is
    not allowed is the harness making that decision silently on the operator's behalf."""
    channel = coref_channel.require(_suppressed(shipped_config), bakeoff_config())
    assert not channel.measurable


def test_a_live_channel_satisfies_the_precondition(shipped_config) -> None:
    channel = coref_channel.require(shipped_config,
                                    bakeoff_config(required_metrics=["coref_binding"]))
    assert channel.measurable


def test_a_gold_slice_with_no_cluster_labels_also_refuses_up_front() -> None:
    """Binding needs both sides. A live channel scored against an unlabeled slice is still an impossible
    measurement, and still one nobody should pay N runs to discover."""
    from types import SimpleNamespace

    # the shape `load_claim_gold` returns: a sequence of SurfaceClaim
    unlabeled = [SimpleNamespace(coref_cluster=None)]
    labeled = [SimpleNamespace(coref_cluster="c1")]
    required = bakeoff_config(required_metrics=["coref_binding"])

    with pytest.raises(coref_channel.CorefChannelDormant, match="no coref_cluster labels"):
        coref_channel.require_gold_labels(unlabeled, required)
    coref_channel.require_gold_labels(labeled, required)          # labeled slice: no refusal
    coref_channel.require_gold_labels(unlabeled, bakeoff_config())  # not required: not this check's call


# ── the VLM imagery gate ──────────────────────────────────────────────────────────────────────────

def _candidate(**kw: Any) -> Candidate:
    base: dict[str, Any] = {
        "id": "cand", "label": "Cand", "provider": "test", "model_id": "pinned-1",
        "client_module": "chanakya.ingest.client", "client_class": "ScriptedExtractionClient",
        "sdk_module": "json", "key_env": "BAKEOFF_TEST_KEY_A", "multimodal": "native",
        "freezes_seed": True, "pricing": None,
    }
    base.update(kw)
    return Candidate.model_validate(base)


def _evidence(**kw: Any) -> vlm_probe.ImageryEvidence:
    base: dict[str, Any] = {
        "candidate_id": "cand", "model_id": "pinned-1", "image": "frame.png",
        "calls_ok": 1, "calls_total": 1, "recorded_at": "2026-07-25T00:00:00+00:00",
    }
    base.update(kw)
    return vlm_probe.ImageryEvidence(**base)


def test_no_record_is_unknown_and_unknown_blocks() -> None:
    gate, record = vlm_probe.gate_from_evidence(_candidate(), {})
    assert gate.status == "UNKNOWN" and gate.blocks_winning
    assert record is None


def test_a_returned_image_call_is_the_evidence_that_passes_the_gate() -> None:
    gate, record = vlm_probe.gate_from_evidence(_candidate(), {"cand": _evidence()})
    assert gate.status == "PASS" and record is not None


def test_an_image_call_that_raised_is_a_fail_with_the_providers_own_words() -> None:
    records = {"cand": _evidence(calls_ok=0, calls_total=1, error="BadRequestError: image too large")}
    gate, record = vlm_probe.gate_from_evidence(_candidate(), records)
    assert gate.status == "FAIL"
    assert record is not None and record.error == "BadRequestError: image too large"


def test_evidence_recorded_against_a_different_pin_is_treated_as_absent() -> None:
    """Re-pinning a candidate must not inherit the previous model's imagery evidence — that would let a
    model that was never shown an image pass on another model's result."""
    records = {"cand": _evidence(model_id="the-old-pin")}
    gate, record = vlm_probe.gate_from_evidence(_candidate(model_id="the-new-pin"), records)
    assert gate.status == "UNKNOWN" and record is None


def test_evidence_from_an_older_probe_procedure_is_treated_as_absent() -> None:
    records = {"cand": _evidence(probe_version=vlm_probe.PROBE_VERSION - 1)}
    gate, _ = vlm_probe.gate_from_evidence(_candidate(), records)
    assert gate.status == "UNKNOWN"


def test_a_text_only_candidate_fails_the_gate_whatever_the_evidence_says() -> None:
    """The declaration alone disqualifies: dropping the locked VLM path is not a score deduction."""
    gate, _ = vlm_probe.gate_from_evidence(_candidate(multimodal="none"), {"cand": _evidence()})
    assert gate.status == "FAIL"


def test_evidence_round_trips_through_the_readable_artefact(tmp_path) -> None:
    path = tmp_path / "vlm-gate-evidence.json"
    written = vlm_probe.save_evidence({"cand": _evidence(), "other": _evidence(candidate_id="other")},
                                     path)
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "rk-bakeoff-vlm-evidence/1.0"
    assert [row["candidate_id"] for row in payload["evidence"]] == ["cand", "other"]

    reloaded = vlm_probe.load_evidence(path)
    assert reloaded["cand"] == _evidence()


def test_a_missing_or_corrupt_evidence_file_means_nothing_verified(tmp_path) -> None:
    assert vlm_probe.load_evidence(tmp_path / "absent.json") == {}
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert vlm_probe.load_evidence(broken) == {}


# ── running the probe (offline, injected client) ───────────────────────────────────────────────────

FRAME = b"\x89PNG\r\n\x1a\nnot-a-real-frame"


@pytest.fixture
def frame(tmp_path):
    path = tmp_path / "frame.png"
    path.write_bytes(FRAME)
    return path


def test_the_probe_drives_the_real_imagery_lane_and_records_a_pass(frame, shipped_config) -> None:
    """It calls ``chanakya.ingest.imagery.read_image_document`` — the exact call the ingest lane makes for
    a standalone image. A probe with its own hand-rolled image request would evidence a path the system
    does not use."""
    record = vlm_probe.probe_candidate(
        _candidate(), config=shipped_config, image_path=frame,
        client_factory=lambda cand: RoutedScriptedClient({}, {"frame_kind": "satellite"},
                                                         model_id=cand.model_id),
        now=datetime(2026, 7, 25, tzinfo=UTC),
    )
    assert record is not None
    assert (record.calls_ok, record.calls_total) == (1, 1)
    assert record.error is None
    assert record.model_id == "pinned-1" and record.image == "frame.png"
    gate, _ = vlm_probe.gate_from_evidence(_candidate(), {record.candidate_id: record})
    assert gate.status == "PASS"


def test_a_candidate_with_no_client_is_not_probed_and_stays_unknown(frame, shipped_config) -> None:
    """"No key, so nothing ran" is already a gate of its own; writing a 0/0 record here would look like a
    probe that ran and found nothing."""
    record = vlm_probe.probe_candidate(_candidate(), config=shipped_config, image_path=frame,
                                       client_factory=lambda cand: None)
    assert record is None


def test_a_provider_that_raises_on_the_image_is_a_recorded_fail(frame, shipped_config) -> None:
    class Refuses:
        model_id = "pinned-1"
        last_usage = None

        def extract(self, **kw: Any) -> dict[str, Any]:
            return {}

        def read_image(self, **kw: Any) -> dict[str, Any]:
            raise RuntimeError("this model does not accept images")

    record = vlm_probe.probe_candidate(_candidate(), config=shipped_config, image_path=frame,
                                       client_factory=lambda cand: Refuses())
    assert record is not None
    assert (record.calls_ok, record.calls_total) == (0, 1)
    assert record.error is not None and "does not accept images" in record.error
    gate, _ = vlm_probe.gate_from_evidence(_candidate(), {record.candidate_id: record})
    assert gate.status == "FAIL"


def test_a_failure_upstream_of_the_request_is_unknown_not_a_disqualification(
        frame, shipped_config, monkeypatch) -> None:
    """Every provider-side error lands in the recorder, so an exception with *no* image call attempted
    happened before the request — our problem, not the model's. It must not read as FAIL."""
    from chanakya.ingest import imagery

    def _explode(*a: Any, **kw: Any) -> Any:
        raise ValueError("could not decode the frame")

    monkeypatch.setattr(imagery.loaders, "load_image", _explode)
    record = vlm_probe.probe_candidate(
        _candidate(), config=shipped_config, image_path=frame,
        client_factory=lambda cand: RoutedScriptedClient({}, {}, model_id=cand.model_id),
    )
    assert record is not None
    assert (record.calls_ok, record.calls_total) == (0, 0)
    assert record.error is not None and "could not decode the frame" in record.error
    gate, _ = vlm_probe.gate_from_evidence(_candidate(), {record.candidate_id: record})
    assert gate.status == "UNKNOWN"


def test_the_default_probe_image_is_a_real_corpus_frame_that_exists() -> None:
    """One frame, chosen once, so the comparison is between providers rather than between pictures. If it
    went missing the probe would fail for everyone — better to find that here than mid-run."""
    path = vlm_probe.default_image_path()
    assert path.is_file(), f"the declared probe image is missing: {path}"
    assert path.suffix == ".png"
