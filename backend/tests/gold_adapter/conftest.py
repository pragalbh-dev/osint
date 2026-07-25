"""Fixtures for the gold-adapter tests: the labeled inputs, the documents, and the adapted output.

The labeled gold and the seven corpus documents are read-only inputs. The adapted output is **rebuilt in
the test**, never read from the committed ``.bakeoff.json`` — a test that asserted against the committed
artefact would pass forever after the adapter broke. One test (``test_reproducible``) does the opposite
comparison on purpose.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from eval.gold.adapter import adapt_claim_gold, adapt_sub_oracle

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLD_DIR = REPO_ROOT / "tmp/spike-rk/gold"
CLAIM_GOLD = GOLD_DIR / "claim-gold.json"
SUB_ORACLE = GOLD_DIR / "sub-oracle.json"

#: The labeled slice's own declared shape. Hard-coded so a change to the gold breaks a test loudly
#: instead of silently re-baselining every count in this directory.
EXPECTED = {
    "documents": 7,
    "rows": 125,
    "claims": 65,
    "attribute_rows": 22,
    "not_a_claim": 11,
    "anti_coref": 6,
    "ambiguous": 2,
    "unmodelled": 19,
    "coref_clusters": 32,
    "coref_mentions": 120,
    "negative_polarity_rows": 27,
    "spans_byte_exact": 122,
}

pytestmark = pytest.mark.skipif(
    not CLAIM_GOLD.exists(),
    reason="the RK-SPIKE labeled gold is not present in this checkout",
)


@pytest.fixture(scope="session")
def raw_gold() -> dict[str, Any]:
    return json.loads(CLAIM_GOLD.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def raw_sub_oracle() -> dict[str, Any]:
    return json.loads(SUB_ORACLE.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def doc_texts(raw_gold: dict[str, Any]) -> dict[str, str]:
    """``doc_id`` → raw document text, straight off the frozen corpus."""
    return {d["doc_id"]: (REPO_ROOT / d["path"]).read_text(encoding="utf-8")
            for d in raw_gold["documents"]}


@pytest.fixture(scope="session")
def texts_by_path(raw_gold: dict[str, Any], doc_texts: dict[str, str]) -> dict[str, str]:
    return {d["path"]: doc_texts[d["doc_id"]] for d in raw_gold["documents"]}


@pytest.fixture(scope="session")
def adapted(raw_gold: dict[str, Any], doc_texts: dict[str, str]) -> dict[str, Any]:
    return adapt_claim_gold(raw_gold, doc_texts)


@pytest.fixture(scope="session")
def adapted_oracle(raw_sub_oracle: dict[str, Any]) -> dict[str, Any]:
    return adapt_sub_oracle(raw_sub_oracle)
