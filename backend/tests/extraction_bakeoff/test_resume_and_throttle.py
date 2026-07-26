"""Resume and per-provider pacing — the two mechanisms that make a re-run survivable.

Both exist because of one day. On 2026-07-26 a live three-way run was attempted three times and died
three times: twice on a concurrency race in the Gemini client, once on ``openai.RateLimitError`` from an
account capped at 3 requests a minute. ``anthropic-opus-5`` completed all five of its runs on **every**
attempt and was billed for all three, because the harness held everything in memory and one exception
discarded ~225 already-bought calls. Nothing was scored.

So this file pins two properties and the correctness rules attached to each:

* **resume** — a document already paid for is not re-bought, a resumed run is *honest about being one*
  (``determinism`` is a measured line, so runs stitched across sittings must say so), and a bundle whose
  inputs changed is never reused.
* **pacing** — a provider's declared cap slows **its own lane** and not the run, and pacing is never
  allowed to become retrying, because a rate-limit response is a *returned* response and re-issuing one
  would launder ``structured_output_reliability`` inside the instrument built to expose it.

Entirely offline: the client is injected, no key is read and no API call is made.
"""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from chanakya import settings
from chanakya.config.store import ConfigStore
from chanakya.ingest import adapters
from chanakya.ingest.lane import DocInput
from eval.extraction import resume as R
from eval.extraction.policy import RateLimit, load_bakeoff_config
from eval.extraction.recording import CallRecord, RecordingExtractionClient
from eval.extraction.runner import BakeoffInputs, run_bakeoff
from eval.extraction.throttle import (
    RequestPacer,
    ThrottledExtractionClient,
    projected_seconds,
    virtual_pacer,
)

from .fixtures import RoutedScriptedClient, bakeoff_config, write_claim_gold, write_sub_oracle

DOC_TEXT = (
    "North Ridge Foundry supplies the Type-7 Coupler to the Eastvale Pumping Station.\n"
    "The station is operated by the Regional Water Board.\n"
)

PAYLOAD = {
    "manufacturers": [{"name": "North Ridge Foundry",
                       "source_quote": "North Ridge Foundry supplies the Type-7 Coupler"}],
    "components": [{"name": "Type-7 Coupler", "component_class": "coupler",
                    "source_quote": "the Type-7 Coupler"}],
    "relations": [{"relation": "supplies-component", "subject": "North Ridge Foundry",
                   "object": "Type-7 Coupler",
                   "source_quote": "North Ridge Foundry supplies the Type-7 Coupler"}],
}


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapters, "_default_geocoder", lambda: None)


@pytest.fixture
def pipeline_config():
    return ConfigStore.seed_from(settings.config_dir()).snapshot()


@pytest.fixture
def docs() -> list[DocInput]:
    return [
        DocInput(raw=DOC_TEXT, source_id="doc1", source_type="curated-register", file="doc1.txt",
                 format_hint="prose_claim"),
        DocInput(raw=b"\x89PNG\r\n\x1a\nnot-a-real-frame", source_id="frame1",
                 source_type="geoint-imagery", file="frame1.png"),
    ]


@pytest.fixture
def inputs(tmp_path, pipeline_config, docs) -> BakeoffInputs:
    gold = write_claim_gold(tmp_path / "gold.json", [
        {"gold_id": "g1", "source_id": "doc1", "form": "entity", "entity_type": "manufacturer",
         "name": "North Ridge Foundry", "doc_ref": {"file": "doc1.txt", "span": [0, 47]},
         "kind": "observation"},
    ])
    oracle = write_sub_oracle(
        tmp_path / "oracle.json",
        [{"id": "n1", "type": "manufacturer", "name": "North Ridge Foundry"}], [])
    return BakeoffInputs(docs=docs, config=pipeline_config, gold_path=gold, sub_oracle_path=oracle,
                         out_dir=tmp_path / "bundles", concurrency=2)


class CountingFactory:
    """A client factory that counts how many extraction calls the whole bake-off actually makes."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self, candidate, run_index):
        outer = self

        class Counting(RoutedScriptedClient):
            def extract(self, **kw):
                outer.calls += 1
                return super().extract(**kw)

            def read_image(self, **kw):
                outer.calls += 1
                return super().read_image(**kw)

        return Counting(PAYLOAD, {}, model_id=candidate.model_id)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# RESUME — a call bought once is not bought twice.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def test_a_second_invocation_buys_nothing_and_scores_the_same(inputs) -> None:
    """The whole point. Three attempts at the same run should cost one run, not three."""
    config = bakeoff_config(candidates=[_candidate("alpha")])

    first = CountingFactory()
    a = run_bakeoff(inputs, config, first, require_key=False, invocation="inv-one")
    assert first.calls > 0

    second = CountingFactory()
    b = run_bakeoff(inputs, config, second, require_key=False, invocation="inv-two")
    assert second.calls == 0, "a fully cached run re-bought calls"

    # And it is the same measurement, not merely a cheap one.
    assert (a.scores[0].series["surface_recall"].values
            == b.scores[0].series["surface_recall"].values)
    assert b.scores[0].series["structured_output_reliability"].status == "measured", (
        "the call records did not survive the round trip, so a measured-at-the-call criterion "
        "silently went missing on the resumed run"
    )


def test_a_partial_run_keeps_the_documents_it_already_paid_for(inputs, tmp_path) -> None:
    """The failure mode that cost ~225 Opus calls: an exception mid-run discarding completed work.

    Here the first invocation dies on the image document after the text document has come back. The
    text document must survive on disk, and the retry must buy only what is actually missing.
    """
    config = bakeoff_config(candidates=[_candidate("alpha")],
                            replication={"runs_per_candidate": 1, "min_runs_for_ranking": 2})

    class DiesOnImage(RoutedScriptedClient):
        def read_image(self, **kw):
            raise RuntimeError("provider fell over")

    with pytest.raises(RuntimeError, match="provider fell over"):
        run_bakeoff(inputs, config, lambda c, i: DiesOnImage(PAYLOAD, {}, model_id=c.model_id),
                    require_key=False, invocation="inv-died")

    bundle = tmp_path / "bundles" / "alpha" / "run-01" / "doc1.json"
    assert bundle.exists(), "the document that DID complete was not persisted before the run died"

    retry = CountingFactory()
    run_bakeoff(inputs, config, retry, require_key=False, invocation="inv-retry")
    assert retry.calls == 1, f"expected only the missing image call to be re-bought, got {retry.calls}"


def test_no_resume_refuses_to_reuse_but_still_records(inputs) -> None:
    """``--no-resume`` is the honest way to buy a single-sitting ``determinism``, not a cache wipe."""
    config = bakeoff_config(candidates=[_candidate("alpha")])
    run_bakeoff(inputs, config, CountingFactory(), require_key=False, invocation="inv-one")

    again = CountingFactory()
    result = run_bakeoff(inputs, config, again, require_key=False, invocation="inv-two",
                         resume_enabled=False)
    assert again.calls > 0
    assert result.scores[0].provenance.documents_reused == 0
    assert result.scores[0].provenance.invocations == ("inv-two",)


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# RESUME — a bundle whose inputs changed is never reused.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def test_repinning_the_model_invalidates_every_cached_bundle(inputs) -> None:
    """A re-pin makes every stored bundle a result about a different model. Re-buy it."""
    run_bakeoff(inputs, bakeoff_config(candidates=[_candidate("alpha", model_id="m-1")]),
                CountingFactory(), require_key=False, invocation="inv-one")

    after = CountingFactory()
    run_bakeoff(inputs, bakeoff_config(candidates=[_candidate("alpha", model_id="m-2")]),
                after, require_key=False, invocation="inv-two")
    assert after.calls > 0, "a re-pinned candidate reused bundles produced by the OLD model id"


def test_editing_a_document_invalidates_every_cached_bundle(inputs) -> None:
    """A slice that changed under a half-reused run is a different measurement wearing old numbers."""
    config = bakeoff_config(candidates=[_candidate("alpha")])
    run_bakeoff(inputs, config, CountingFactory(), require_key=False, invocation="inv-one")

    edited = replace(inputs, docs=[
        replace(inputs.docs[0], raw=DOC_TEXT + "A sentence the cached bundle never saw.\n"),
        inputs.docs[1],
    ])
    after = CountingFactory()
    run_bakeoff(edited, config, after, require_key=False, invocation="inv-two")
    assert after.calls > 0, "an edited document set reused bundles extracted from the old text"


def test_changing_a_prompt_or_a_tool_schema_invalidates_the_cache(monkeypatch, docs) -> None:
    """The digest is DERIVED from the shipped prompts and schemas, never a hand-bumped constant.

    A version constant is one somebody forgets on the commit where it mattered, and the consequence is a
    bundle produced by a prompt that no longer exists being scored as current.
    """
    from chanakya.ingest import extract

    before = R.fingerprint(model_id="m", docs=docs)
    prompts = dict(extract._SYSTEM_PROMPTS)
    prompts["prose_claim"] = prompts["prose_claim"] + " And one more instruction."
    monkeypatch.setattr(extract, "_SYSTEM_PROMPTS", prompts)
    assert R.fingerprint(model_id="m", docs=docs) != before


def test_a_dry_run_bundle_can_never_satisfy_a_live_lookup(docs) -> None:
    """``--dry-run`` walks the identical path with a scripted double reporting the REAL model id.

    Without the producer kind in the key, every dry run would leave bundles a live run would happily
    reuse, and a scorecard would rank three models on invented text with every gate green.
    """
    assert (R.fingerprint(model_id="m", docs=docs, producer=R.DRY)
            != R.fingerprint(model_id="m", docs=docs, producer=R.LIVE))


def test_a_half_written_or_unreadable_artefact_is_a_miss_not_a_hit(tmp_path, docs) -> None:
    """Every doubt resolves to re-buying. A wrong hit is a benchmark number about inputs that are gone."""
    store = R.ResumeStore(root=tmp_path, invocation="inv-one")
    fp = R.fingerprint(model_id="m", docs=docs)
    store.save("alpha", 1, docs[0], [], [], fp)
    assert store.load("alpha", 1, "doc1", fp) is not None

    # a bundle with no sidecar (e.g. the pre-resume artefacts a previous paid run left behind)
    (tmp_path / "alpha" / "run-01" / R.SIDECAR_DIR / "doc1.json").unlink()
    assert store.load("alpha", 1, "doc1", fp) is None

    # a sidecar that is not valid JSON
    store.save("alpha", 2, docs[0], [], [], fp)
    (tmp_path / "alpha" / "run-02" / R.SIDECAR_DIR / "doc1.json").write_text("{ truncated",
                                                                            encoding="utf-8")
    assert store.load("alpha", 2, "doc1", fp) is None

    # a sidecar from a schema this code does not know
    store.save("alpha", 3, docs[0], [], [], fp)
    path = tmp_path / "alpha" / "run-03" / R.SIDECAR_DIR / "doc1.json"
    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["schema"] = "rk-bakeoff-resume/99"
    path.write_text(json.dumps(meta), encoding="utf-8")
    assert store.load("alpha", 3, "doc1", fp) is None


def test_the_call_records_survive_the_round_trip(tmp_path, docs) -> None:
    """Three criteria are measured at the CALL and never reach a ``ClaimRecord``. A cache that stored
    only claims would resume into a run whose reliability line was silently unmeasured."""
    store = R.ResumeStore(root=tmp_path, invocation="inv-one")
    fp = R.fingerprint(model_id="m", docs=docs)
    call = CallRecord(lane="text", tool_name="extract_prose_claim",
                      offered_fields=("manufacturers",), payload={"manufacturers": []},
                      latency_s=1.25, usage={"input_tokens": 10, "output_tokens": 2})
    store.save("alpha", 1, docs[0], [], [call], fp)

    recovered = store.load("alpha", 1, "doc1", fp)
    assert recovered is not None
    assert recovered.calls[0].tool_name == "extract_prose_claim"
    assert recovered.calls[0].offered_fields == ("manufacturers",)
    assert recovered.calls[0].usage == {"input_tokens": 10, "output_tokens": 2}
    replayed = RecordingExtractionClient.replay(recovered.calls)
    assert replayed.total_usage() == {"input_tokens": 10, "output_tokens": 2,
                                      "calls_reporting_usage": 1}


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# RESUME — honesty about what a resumed run is.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def test_runs_stitched_across_invocations_are_declared_on_the_scorecard(inputs, tmp_path) -> None:
    """``determinism`` is a measured, weighted line. Runs assembled across sittings are a different
    sample from runs taken in one, and printing them identically would be a corrupted measurement."""
    from eval.extraction.render import render_markdown

    config = bakeoff_config(candidates=[_candidate("alpha")])
    run_bakeoff(inputs, config, CountingFactory(), require_key=False, invocation="inv-one")
    # Lose exactly one run, the way a mid-flight death would.
    for path in (tmp_path / "bundles" / "alpha" / "run-02").rglob("*.json"):
        path.unlink()

    result = run_bakeoff(inputs, config, CountingFactory(), require_key=False, invocation="inv-two")
    prov = result.scores[0].provenance
    assert not prov.single_invocation
    assert set(prov.invocations) == {"inv-one", "inv-two"}
    assert prov.documents_reused and prov.documents_bought

    markdown = render_markdown(result.scores, result.verdict, result.comparisons, result.config,
                               result.composite)
    assert "RESUMED — this scorecard is not one sitting" in markdown
    assert "cross-invocation" in markdown          # stamped on the determinism row itself
    assert "--no-resume" in markdown               # and the remedy is named


def test_a_run_taken_in_one_sitting_carries_no_warning(inputs) -> None:
    """The disclosure has to mean something, so it must not fire on the ordinary case."""
    from eval.extraction.render import render_markdown

    config = bakeoff_config(candidates=[_candidate("alpha")])
    result = run_bakeoff(inputs, config, CountingFactory(), require_key=False, invocation="inv-one")
    assert result.scores[0].provenance.single_invocation
    markdown = render_markdown(result.scores, result.verdict, result.comparisons, result.config,
                               result.composite)
    assert "not one sitting" not in markdown
    assert "cross-invocation" not in markdown


def test_a_wholly_replayed_scorecard_says_it_describes_another_session(inputs) -> None:
    """Not a stitching warning — those runs WERE one sitting — but the reader is still told the numbers
    are somebody else's receipts, not this invocation's."""
    from eval.extraction.render import render_markdown

    config = bakeoff_config(candidates=[_candidate("alpha")])
    run_bakeoff(inputs, config, CountingFactory(), require_key=False, invocation="inv-one")
    result = run_bakeoff(inputs, config, CountingFactory(), require_key=False, invocation="inv-two")

    assert result.scores[0].provenance.single_invocation      # so no stitching warning
    assert all(r.calls_bought == 0 for r in result.scores[0].runs)
    markdown = render_markdown(result.scores, result.verdict, result.comparisons, result.config,
                               result.composite)
    assert "Replayed, not re-run" in markdown
    assert "not one sitting" not in markdown


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# PACING — a capped provider slows its OWN lane.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def test_the_shipped_config_paces_openai_and_leaves_the_others_alone() -> None:
    """The cap that killed the run is declared in config, not in code — it is an account property."""
    cfg = load_bakeoff_config(settings.config_dir() / "bakeoff.yaml")
    assert cfg.rate_limit("openai").requests_per_minute == 3
    assert cfg.rate_limit("anthropic").requests_per_minute is None
    assert cfg.rate_limit("google").requests_per_minute is None


def test_a_pacer_spaces_request_starts_and_never_bursts() -> None:
    """Interval pacing, not a token bucket: a bucket empties its whole allowance into the first instant
    of every window, which is the exact shape that trips a cap whose window is not ours."""
    slept: list[float] = []
    clock = [0.0]

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        clock[0] += seconds

    pacer = RequestPacer(limit=RateLimit(requests_per_minute=3), sleep=sleep, clock=lambda: clock[0])
    for _ in range(4):
        pacer.acquire()
        pacer.release()

    assert slept == [20.0, 20.0, 20.0], "calls were not spaced at 60/3 seconds"
    assert pacer.waited_s == pytest.approx(60.0)


def test_an_unpaced_provider_never_waits() -> None:
    """A provider the config does not name must run at full speed — inventing a cap nobody has hit
    would slow a lane for a fact not in evidence."""
    slept: list[float] = []
    pacer = RequestPacer(limit=RateLimit(), sleep=slept.append)
    for _ in range(10):
        pacer.acquire()
        pacer.release()
    assert slept == []
    assert projected_seconds(RateLimit(), 100, concurrency=8) == 0.0


def test_each_candidate_holds_its_own_pacer_so_a_slow_lane_is_only_its_own(inputs) -> None:
    """The property the whole design turns on: one capped provider must not throttle the run."""
    from eval.extraction.runner import _pacer_for

    config = bakeoff_config(candidates=[
        _candidate("alpha", provider="openai"), _candidate("beta", provider="anthropic")])
    config = config.model_copy(update={"rate_limits": {"openai": RateLimit(requests_per_minute=3)}})

    alpha = _pacer_for(config.candidate("alpha"), config, pace=True)
    beta = _pacer_for(config.candidate("beta"), config, pace=True)
    assert alpha is not beta
    assert alpha.limit.min_interval_s == 20.0
    assert beta.limit.min_interval_s == 0.0


def test_the_throttle_is_transparent_and_wraps_outside_the_recorder() -> None:
    """The wait must not land inside ``latency_s``: a latency inflated by our own queue says nothing
    about the model. So the throttle sits OUTSIDE the recorder, and proxies what the pipeline reads."""
    slept: list[float] = []
    inner = RoutedScriptedClient(PAYLOAD, {}, model_id="m-1")
    recorder = RecordingExtractionClient(inner)
    client = ThrottledExtractionClient(
        recorder, RequestPacer(limit=RateLimit(requests_per_minute=60), sleep=slept.append))

    assert client.model_id == "m-1"
    client.extract(tool_name="extract_prose_claim", input_schema={"properties": {}}, system="s",
                   text="t")
    client.extract(tool_name="extract_prose_claim", input_schema={"properties": {}}, system="s",
                   text="t")
    assert len(slept) == 1 and slept[0] == pytest.approx(1.0, abs=0.05)  # #2 waited
    assert len(recorder.calls) == 2                         # both were recorded
    assert recorder.total_latency_s() < 1.0                 # and the wait is NOT in the latency


def test_a_dry_run_still_exercises_the_pacer_and_reports_its_wall_clock() -> None:
    """A dry run that skipped pacing would leave the one mechanism added to prevent a rate-limit death
    completely unexercised. The virtual pacer runs the same arithmetic against a clock that only moves
    when something sleeps on it, so nothing blocks and the projection is the harness's, not arithmetic
    done on paper."""
    pacer = virtual_pacer(RateLimit(requests_per_minute=3))
    for _ in range(4):
        pacer.acquire()
        pacer.release()
    assert pacer.waited_s == pytest.approx(60.0)


def test_pacing_is_not_retrying(inputs) -> None:
    """The line the retry discipline draws, restated where it could be eroded. A rate-limit response is
    a RETURNED response: it is the provider's own behaviour, ``structured_output_reliability`` exists to
    score it, and re-issuing one would launder that number inside the instrument built to expose it.
    So the throttle must pass a 429 straight through — the cap is avoided by pacing, never by retrying.
    """
    from eval.extraction.resilience import is_transport_fault

    class RateLimited(Exception):
        status_code = 429

    assert not is_transport_fault(RateLimited("rate limited")), (
        "a 429 was classified as a transport fault, which would make the retry wrapper re-issue it"
    )

    attempts = {"n": 0}

    class Limited(RoutedScriptedClient):
        def extract(self, **kw):
            attempts["n"] += 1
            raise RateLimited("429")

    with pytest.raises(RateLimited):
        run_bakeoff(inputs, bakeoff_config(candidates=[_candidate("alpha")]),
                    lambda c, i: Limited(PAYLOAD, {}, model_id=c.model_id), require_key=False,
                    invocation="inv-429")
    assert attempts["n"] == 1, "a returned 429 was retried"


# ── helpers ───────────────────────────────────────────────────────────────────────────────────────

def _candidate(cid: str, *, model_id: str = "m-1", provider: str = "testprovider") -> dict:
    return {
        "id": cid, "label": cid, "provider": provider, "model_id": model_id,
        "client_module": "chanakya.ingest.client", "client_class": "AnthropicExtractionClient",
        "sdk_module": "json", "key_env": "FAKE_KEY_ENV", "multimodal": "native",
        "freezes_seed": True, "pricing": None,
    }
