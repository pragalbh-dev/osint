"""Invented fixtures for the bake-off tests — a fictional infrastructure domain, no real entities.

Deliberately not the project corpus: the scorer is corpus-blind by design, so its tests are too. If a
number here matched a real document it would be a leak, not a convenience.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eval.extraction.policy import BakeoffConfig, MatchPolicy
from eval.extraction.surface import SpanRef, SurfaceClaim

POLICY = MatchPolicy(
    similarity="token_sort_ratio",
    require_same_form=True,
    require_same_polarity=True,
    predicate_policy="normalized",
    entity_type_policy="normalized",
    role_min_similarity=0.70,
    pair_min_similarity=0.80,
    span_policy="bonus",
    span_iou_floor=0.30,
    span_bonus_weight=0.15,
    grounding_similarity=0.85,
)


def triple(key: str, subject: str, obj: str, predicate: str = "supplies-component", *,
           polarity: str = "positive", file: str = "doc1.txt",
           span: tuple[int, int] | None = None, **kw: Any) -> SurfaceClaim:
    return SurfaceClaim(
        key=key, source_id="doc1", form="triple", polarity=polarity,
        roles={"subject": subject, "object": obj}, predicate=predicate,
        refs=(SpanRef(file=file, span=span),) if file else (), **kw,
    )


def entity(key: str, name: str, entity_type: str = "manufacturer", *, file: str = "doc1.txt",
           span: tuple[int, int] | None = None, **kw: Any) -> SurfaceClaim:
    return SurfaceClaim(
        key=key, source_id="doc1", form="entity", polarity="positive", roles={"name": name},
        entity_type=entity_type, refs=(SpanRef(file=file, span=span),) if file else (), **kw,
    )


class RoutedScriptedClient:
    """A deterministic ``ExtractionClient`` double that routes by lane instead of a shared FIFO.

    ``ScriptedExtractionClient`` replays one queue, and ``extract_many`` fans documents out concurrently,
    so which document gets which canned payload is not fixed. The bake-off runs N repetitions and then
    measures the *spread*, so a test double whose own ordering wobbles would show up as model variance.
    This one answers the text lane and the image lane from named payloads, whatever order they arrive in.
    """

    def __init__(self, text_payload: dict[str, Any], image_payload: dict[str, Any] | None = None,
                 *, model_id: str = "routed-test") -> None:
        self._text = text_payload
        self._image = image_payload if image_payload is not None else {}
        self.model_id = model_id
        self.last_usage: dict[str, int] | None = {"input_tokens": 100, "output_tokens": 20}

    def extract(self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
                images: Any = ()) -> dict[str, Any]:
        return dict(self._text)

    def read_image(self, *, tool_name: str, input_schema: dict[str, Any], system: str, image: bytes,
                   media_type: str) -> dict[str, Any]:
        return dict(self._image)


def bakeoff_config(**overrides: Any) -> BakeoffConfig:
    """A minimal two-candidate bake-off config, both candidates gate-clean by default."""
    raw: dict[str, Any] = {
        "schema_version": "rk-bakeoff/1.0",
        "replication": {"runs_per_candidate": 3, "min_runs_for_ranking": 3},
        "margin": {"min_absolute": 0.03, "noise_multiplier": 2.0, "per_metric_min_absolute": {}},
        "gates": {
            "floating_alias_patterns": ["-latest"],
            "production_client_package": "chanakya.ingest",
            "non_negotiable_floors": {},
        },
        "weights": {"surface_f1": 1.0},
        "match_policy": POLICY.model_dump(),
        "candidates": [
            {
                "id": "alpha", "label": "Alpha", "provider": "test", "model_id": "alpha-2026-01-01",
                "client_module": "chanakya.ingest.client", "client_class": "ScriptedExtractionClient",
                "sdk_module": "json", "key_env": "BAKEOFF_TEST_KEY_A", "multimodal": "native",
                "freezes_seed": True, "pricing": None,
            },
            {
                "id": "beta", "label": "Beta", "provider": "test", "model_id": "beta-2026-01-01",
                "client_module": "chanakya.ingest.client", "client_class": "ScriptedExtractionClient",
                "sdk_module": "json", "key_env": "BAKEOFF_TEST_KEY_B", "multimodal": "native",
                "freezes_seed": True, "pricing": None,
            },
        ],
    }
    raw.update(overrides)
    return BakeoffConfig.model_validate(raw)


# ── the labeled inputs, written to disk in the declared schemas ────────────────────────────────────

def write_claim_gold(path: Path, claims: list[dict[str, Any]]) -> Path:
    path.write_text(json.dumps(
        {"schema_version": "rk-bakeoff-claim-gold/1.0", "claims": claims}, indent=2), encoding="utf-8")
    return path


#: The four typed negative classes, empty — the shape ``load_negative_gold`` requires to be complete. A
#: partial block raises, because a silently-missing class stops penalising anything.
EMPTY_NEGATIVE: dict[str, list[dict[str, Any]]] = {
    "not_a_claim": [], "anti_coref": [], "ambiguous": [], "unmodelled": [],
}


def negative_row(gold_id: str, span: tuple[int, int], *, file: str = "doc1.txt") -> dict[str, Any]:
    """One negative-gold row in the adapter's output shape (what the harness consumes)."""
    return {"gold_id": gold_id, "source_id": "doc1", "class": "", "reason": "fixture",
            "doc_ref": {"file": file, "span": [span[0], span[1]]}}


def write_adapted_gold(path: Path, claims: list[dict[str, Any]],
                       negative: dict[str, list[dict[str, Any]]] | None = None) -> Path:
    """The **adapted** claim gold: positive claims plus the four typed negative buckets.

    This is the shape ``eval.gold.adapter`` emits and the shape the runner reads for both halves — the
    positive claims through ``load_claim_gold`` and the typed negatives through ``load_negative_gold`` — so
    a fixture that carries only ``claims`` is a slice with no fabrication line, not a slice with a clean one.
    """
    buckets = {**EMPTY_NEGATIVE, **(negative or {})}
    path.write_text(json.dumps({
        "schema_version": "rk-bakeoff-claim-gold/1.0",
        "claims": claims,
        "negative_gold": {name: {"rows": rows} for name, rows in buckets.items()},
    }, indent=2), encoding="utf-8")
    return path


def write_sub_oracle(path: Path, nodes: list[dict[str, Any]], edges: list[dict[str, Any]],
                     docs: list[str] | None = None) -> Path:
    path.write_text(json.dumps({
        "schema_version": "rk-bakeoff-sub-oracle/1.0",
        "docs": docs or ["doc1"],
        "nodes": nodes,
        "edges": edges,
    }, indent=2), encoding="utf-8")
    return path
