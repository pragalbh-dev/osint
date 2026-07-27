"""The instrumented client wrapper — transparent to the pipeline, and honest about failures.

Three of the scored criteria only exist at the call: tool-call reliability, the A7 discriminators (which
never reach a ``ClaimRecord``), and cost/latency. So the wrapper must record faithfully — including
recording a failure and then still letting it propagate, because reliability is a measurement, not a
rescue.
"""

from __future__ import annotations

import threading

import pytest

from eval.extraction.recording import RecordingExtractionClient

SCHEMA = {"type": "object", "properties": {"orgs": {}, "relations": {}}}


class _Inner:
    model_id = "inner-model-1"

    def __init__(self, payload=None, boom: Exception | None = None) -> None:
        self.payload = payload if payload is not None else {"orgs": []}
        self.boom = boom
        self.last_usage = {"input_tokens": 10, "output_tokens": 4}
        self.seen: list[str] = []

    def extract(self, *, tool_name, input_schema, system, text, images=()):
        self.seen.append(f"text:{text}")
        if self.boom:
            raise self.boom
        return dict(self.payload)

    def read_image(self, *, tool_name, input_schema, system, image, media_type):
        self.seen.append("image")
        if self.boom:
            raise self.boom
        return dict(self.payload)


def test_it_proxies_the_model_id_so_provenance_still_stamps_the_real_model() -> None:
    assert RecordingExtractionClient(_Inner()).model_id == "inner-model-1"


def test_it_passes_the_call_through_unchanged() -> None:
    inner = _Inner({"orgs": [{"name": "X"}]})
    wrapper = RecordingExtractionClient(inner)
    out = wrapper.extract(tool_name="t", input_schema=SCHEMA, system="s", text="body")
    assert out == {"orgs": [{"name": "X"}]}
    assert inner.seen == ["text:body"]


def test_it_records_latency_usage_and_lane() -> None:
    wrapper = RecordingExtractionClient(_Inner())
    wrapper.extract(tool_name="t", input_schema=SCHEMA, system="s", text="b")
    wrapper.read_image(tool_name="t", input_schema=SCHEMA, system="s", image=b"x",
                       media_type="image/png")
    assert [c.lane for c in wrapper.calls] == ["text", "image"]
    assert all(c.latency_s >= 0 for c in wrapper.calls)
    assert wrapper.total_usage() == {"input_tokens": 20, "output_tokens": 8,
                                     "calls_reporting_usage": 2}
    assert len(wrapper.image_calls()) == 1


def test_a_failure_is_recorded_and_still_raised() -> None:
    wrapper = RecordingExtractionClient(_Inner(boom=RuntimeError("no forced tool call")))
    with pytest.raises(RuntimeError):
        wrapper.extract(tool_name="t", input_schema=SCHEMA, system="s", text="b")
    assert len(wrapper.calls) == 1
    assert wrapper.calls[0].ok is False
    assert "no forced tool call" in (wrapper.calls[0].error or "")


def test_invented_top_level_fields_are_detected() -> None:
    wrapper = RecordingExtractionClient(_Inner({"orgs": [], "not_in_the_schema": 1}))
    wrapper.extract(tool_name="t", input_schema=SCHEMA, system="s", text="b")
    assert wrapper.calls[0].invented_fields() == ("not_in_the_schema",)


def test_usage_is_none_when_the_inner_client_reports_none() -> None:
    inner = _Inner()
    inner.last_usage = None
    wrapper = RecordingExtractionClient(inner)
    wrapper.extract(tool_name="t", input_schema=SCHEMA, system="s", text="b")
    assert wrapper.total_usage() is None


def test_it_is_thread_safe_because_extract_many_fans_out() -> None:
    wrapper = RecordingExtractionClient(_Inner())

    def work(i: int) -> None:
        wrapper.extract(tool_name="t", input_schema=SCHEMA, system="s", text=f"b{i}")

    threads = [threading.Thread(target=work, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(wrapper.calls) == 20
