"""INGEST stage — source-typed LLM extraction → ClaimRecord + live-ingest lane (owned by INGEST).

**Source-typed, never use-case-typed (gate G9):** this package must not import subject/ontology-instance
content and must not branch on a subject — a customs doc ingests identically regardless of consumer.
F0 keeps the module import-clean (schemas only) so G9 passes now and stays meaningful.

F0 ships stubs: extraction (the LLM part) raises ``NotImplementedError`` until INGEST builds it; the
keyless bundle-append lane is a thin helper INGEST owns too. INGEST also houses the Date/Location/
Quantity normalization *adapters* (master §4.1/§4.2) — run at extraction, pre-append, never as pydantic
validators.

Frozen signatures: ``extract_claims(raw_text, source_id, config) -> [ClaimRecord]`` (LLM, offline of
rebuild) · ``ingest_bundle(bundle) -> [ClaimRecord]`` (keyless, parse pre-extracted records).
"""

from __future__ import annotations

from typing import Any

from chanakya.schemas import ClaimRecord, ConfigBundle


def extract_claims(raw_text: str, source_id: str, config: ConfigBundle) -> list[ClaimRecord]:
    """STUB: live LLM extraction. INGEST implements it (runs upstream of the append — G1 unaffected)."""
    raise NotImplementedError("INGEST session implements source-typed LLM extraction")


def ingest_bundle(bundle: list[dict[str, Any]]) -> list[ClaimRecord]:
    """Parse a pre-extracted claim bundle (the keyless lane). Pure — no network, no LLM.

    F0 provides this minimal, safe helper so the keyless ingest path is testable now; INGEST extends it
    (dedup, provenance stamping). Kept deliberately trivial and ontology-blind.
    """
    return [ClaimRecord.model_validate(row) for row in bundle]
