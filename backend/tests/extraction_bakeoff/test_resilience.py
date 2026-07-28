"""The retry wrapper may only rescue a call that never reached the provider.

The whole value of this module is the line it refuses to cross: a returned response — 429, 500, a refusal,
a reply with no forced tool call — is the candidate's own behaviour and is *scored*. Retrying one would
launder reliability into a better number than the model earned, inside the instrument built to expose
exactly that. So most of these tests assert what is NOT retried.
"""

from __future__ import annotations

import httpx
import pytest

from eval.extraction.resilience import MAX_ATTEMPTS, RetryingExtractionClient, is_transport_fault


class _Boom(Exception):
    """An SDK-shaped error that carries a returned response."""

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class APIConnectionError(Exception):  # noqa: N818 - the point IS to carry the SDKs' exact class name
    """Named exactly as the openai/anthropic SDKs name theirs, without importing either.

    The predicate matches transport failures by class name, so this test double is only faithful if it
    carries the real name.
    """


class _Client:
    """Records how many times each lane was called and raises a scripted sequence."""

    def __init__(self, sequence: list[object]) -> None:
        self.sequence = list(sequence)
        self.calls = 0
        self.model_id = "pinned-id"
        self.last_usage = {"input_tokens": 10, "output_tokens": 2}

    def _next(self) -> dict[str, object]:
        self.calls += 1
        item = self.sequence.pop(0)
        if isinstance(item, BaseException):
            raise item
        assert isinstance(item, dict)
        return item

    def extract(self, **_: object) -> dict[str, object]:
        return self._next()

    def read_image(self, **_: object) -> dict[str, object]:
        return self._next()


def _wrap(inner: _Client) -> RetryingExtractionClient:
    return RetryingExtractionClient(inner, sleep=lambda _s: None)


def _extract(client: RetryingExtractionClient) -> dict[str, object]:
    return client.extract(tool_name="t", input_schema={}, system="", text="x")


# ── the predicate ─────────────────────────────────────────────────────────────────────────────────

def test_the_2026_07_26_failure_is_a_transport_fault() -> None:
    """The exact exception that killed the first live run must be the one this rescues."""
    exc = httpx.ReadError("[SSL: DECRYPTION_FAILED_OR_BAD_RECORD_MAC] decryption failed or bad record mac")
    assert is_transport_fault(exc)


@pytest.mark.parametrize("exc", [
    httpx.ConnectError("refused"),
    httpx.ReadTimeout("slow"),
    httpx.RemoteProtocolError("server closed"),
    APIConnectionError("connection dropped"),
    ConnectionError("reset by peer"),
    TimeoutError("timed out"),
])
def test_transport_shaped_failures_are_retryable(exc: Exception) -> None:
    assert is_transport_fault(exc)


@pytest.mark.parametrize("exc", [
    _Boom("rate limited", 429),
    _Boom("server error", 500),
    RuntimeError("Gemini returned no forced function call for tool 'extract_prose_claim'"),
    ValueError("arguments were not an object"),
    KeyError("missing"),
])
def test_a_returned_response_or_a_client_side_refusal_is_never_retried(exc: Exception) -> None:
    """These are the candidate's own behaviour. structured_output_reliability scores them."""
    assert not is_transport_fault(exc)


def test_a_status_code_anywhere_in_the_chain_defeats_a_transport_name() -> None:
    """A provider that answered has told us something about itself — even if the wrapper is misnamed.

    This is the laundering hole the predicate is written to close: an SDK that raised something *named*
    like a transport error but carrying a real response must not be retried.
    """
    exc = APIConnectionError("looks transport-shaped")
    exc.status_code = 503  # type: ignore[attr-defined]
    assert not is_transport_fault(exc)


def test_a_transport_fault_wrapped_by_an_sdk_is_still_seen() -> None:
    """SDKs re-raise transport faults several layers deep; the predicate walks the chain."""
    try:
        try:
            raise httpx.ReadError("bad record mac")
        except httpx.ReadError as inner:
            raise RuntimeError("sdk wrapper") from inner
    except RuntimeError as exc:
        assert is_transport_fault(exc)


# ── the wrapper ───────────────────────────────────────────────────────────────────────────────────

def test_a_blip_is_retried_and_the_call_succeeds() -> None:
    inner = _Client([httpx.ReadError("bad record mac"), {"ok": True}])
    client = _wrap(inner)
    assert _extract(client) == {"ok": True}
    assert inner.calls == 2
    assert len(client.retries) == 1


def test_a_scored_failure_is_raised_on_the_first_attempt_not_retried() -> None:
    inner = _Client([_Boom("rate limited", 429), {"ok": True}])
    client = _wrap(inner)
    with pytest.raises(_Boom):
        _extract(client)
    assert inner.calls == 1, "a returned response must never be re-dialled"
    assert client.retries == []


def test_a_persistent_transport_fault_still_fails_the_run_loudly() -> None:
    """This rides out one corrupted socket. A real outage must not quietly burn the budget re-dialling."""
    inner = _Client([httpx.ConnectError("down")] * (MAX_ATTEMPTS + 2))
    client = _wrap(inner)
    with pytest.raises(httpx.ConnectError):
        _extract(client)
    assert inner.calls == MAX_ATTEMPTS


def test_the_image_lane_is_retried_on_the_same_rule() -> None:
    inner = _Client([httpx.ReadError("bad record mac"), {"observations": []}])
    client = _wrap(inner)
    got = client.read_image(tool_name="t", input_schema={}, system="", image=b"x", media_type="image/png")
    assert got == {"observations": []}
    assert inner.calls == 2


def test_model_id_and_usage_are_proxied_so_the_wrapper_is_transparent() -> None:
    """The recorder reads last_usage off the client it was handed, and claims stamp model_id."""
    inner = _Client([{"ok": True}])
    client = _wrap(inner)
    assert client.model_id == "pinned-id"
    assert client.last_usage == {"input_tokens": 10, "output_tokens": 2}


def test_the_recorder_sees_one_row_per_logical_call_not_per_attempt() -> None:
    """Retries must be invisible to the call log, or reliability would be scored on re-dials."""
    from eval.extraction.recording import RecordingExtractionClient

    inner = _Client([httpx.ReadError("bad record mac"), {"ok": True}])
    recorder = RecordingExtractionClient(_wrap(inner))
    assert recorder.extract(tool_name="t", input_schema={}, system="", text="x") == {"ok": True}
    assert len(recorder.calls) == 1
    assert recorder.calls[0].ok
