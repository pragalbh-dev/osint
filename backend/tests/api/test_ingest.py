"""``POST /ingest`` — keyless bundle append + live-rebuild, and the keyed-extraction guard (API.md 5)."""

from __future__ import annotations

from tests.fixtures import loaders


def _sample_claim_dict(claim_id: str) -> dict:
    row = loaders.golden_claims()[0].model_dump(mode="json")
    row["claim_id"] = claim_id
    return row


def test_ingest_bundle_appends_and_rebuilds_no_restart(golden_client) -> None:
    before = golden_client.get("/view").json()
    r = golden_client.post("/ingest", json={"bundle": [_sample_claim_dict("api-ingest-1")]})
    assert r.status_code == 200
    body = r.json()
    assert body["appended_claim_ids"] == ["api-ingest-1"]
    assert body["rebuilt"] is True
    # The held view rebuilt in-process — still valid and no smaller than before.
    after = golden_client.get("/view").json()
    assert len(after["nodes"]) >= len(before["nodes"])


def test_ingest_rejects_both_modes(golden_client) -> None:
    r = golden_client.post("/ingest", json={"bundle": [_sample_claim_dict("x")], "raw_text": "y"})
    assert r.status_code == 400


def test_ingest_rejects_empty_request(golden_client) -> None:
    assert golden_client.post("/ingest", json={}).status_code == 400


def test_ingest_invalid_bundle_is_422(golden_client) -> None:
    r = golden_client.post("/ingest", json={"bundle": [{"not": "a valid claim"}]})
    assert r.status_code == 422


def test_ingest_raw_doc_blocked_when_extraction_disabled(golden_client, monkeypatch) -> None:
    monkeypatch.delenv("CHANAKYA_ENABLE_EXTRACTION", raising=False)
    r = golden_client.post(
        "/ingest",
        json={"raw_text": "HQ-9 TELs seen at the apron", "source_id": "s-x", "source_type": "social"},
    )
    assert r.status_code == 403  # guarded: steer the public demo to the keyless bundle path


def test_ingest_keyed_needs_key_when_enabled(golden_client, monkeypatch) -> None:
    monkeypatch.setenv("CHANAKYA_ENABLE_EXTRACTION", "1")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    r = golden_client.post(
        "/ingest",
        json={"raw_text": "HQ-9 TELs seen at the apron", "source_id": "s-x", "source_type": "social"},
    )
    assert r.status_code == 400  # enabled but no key → steer to a bundle, never fabricate an extraction
