"""Seed-lane tests — the keyless bundle path + the frozen recorder + KEYLESS ≡ LIVE + byte-stability.

Everything here is **offline + deterministic** (gate G10): a :class:`ScriptedExtractionClient` replays a
canned tool-dict per document (one shared FIFO across text ``extract`` and image ``read_image``), and the
geocoder is stubbed to ``None`` so no adapter touches the network. All bundles are written under
``tmp_path`` — the checked-in ``corpus/scenarios/*/claims`` files are never touched. The graded beats:

* **recorder writes bundles** — ``extract_corpus`` over a tiny temp scenario writes one JSON bundle per
  cited source, dispatching a ``.png`` citation to the VLM imagery lane.
* **KEYLESS ≡ LIVE** — ``ingest_bundle`` reads a frozen bundle back to the *same* claims a live
  ``extract_document`` → dedup → id-assign of that document produces.
* **seed == the claims** — ``seed_store_from_bundles`` appends exactly the bundles' claims, in order.
* **byte-stability** — two recorder runs with the same pinned ``ingest_time`` produce byte-identical JSON.
* **scenario filter** — a source cited under a different scenario is skipped.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest

from chanakya.ingest import adapters, dedup, extract, loaders, seed
from chanakya.ingest.client import ScriptedExtractionClient
from chanakya.schemas import ClaimRecord, ConfigBundle, SourceRegistryEntry
from chanakya.schemas.config_models import SourcesConfig
from chanakya.store.log import EvidenceLog

# ── fixtures + canned model output ─────────────────────────────────────────────────────────────────

_PROSE_TEXT = "CPMIEC is the manufacturer of the system.\n"

# What the (scripted) model "fills" for the prose doc → exactly one manufacturer entity claim.
_PROSE_FILLED: dict[str, Any] = {
    "manufacturers": [{"name": "CPMIEC", "role": "manufacturer", "source_quote": "CPMIEC"}]
}
# What the (scripted) VLM "reads" for the image doc → one subject-blind observation claim.
_IMAGE_FILLED: dict[str, Any] = {
    "geometry_tokens": ["radial-revetments", "central-radar-berm"],
    "occupancy_state": "occupied",
    "description": "lobed revetments ringing a central berm",
    "frame_kind": "overhead",
    "resolution_sufficiency": "sufficient",
}


@pytest.fixture(autouse=True)
def _offline_geocoder(monkeypatch: pytest.MonkeyPatch) -> None:
    """No adapter may hit Nominatim: the default geocoder resolves to ``None`` (raw preserved, no net)."""
    monkeypatch.setattr(adapters, "_default_geocoder", lambda: None)


def _png(color: tuple[int, int, int] = (40, 90, 160), size: int = 32) -> bytes:
    """A tiny deterministic PNG (real bytes, so the fingerprint's sha256/PDQ actually compute)."""
    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (size, size), color).save(buf, format="PNG")
    return buf.getvalue()


def _scripted() -> ScriptedExtractionClient:
    """A fresh client whose one FIFO feeds the prose ``extract`` then the image ``read_image``, in order."""
    return ScriptedExtractionClient([_PROSE_FILLED, _IMAGE_FILLED])


def _tiny_scenario(tmp_path: Any, *, with_image: bool = True) -> tuple[str, ConfigBundle]:
    """Build a temp scenario on disk (docs under ``scenarios/<name>/docs``) + its source registry."""
    scenario = "tinyscn"
    docs = tmp_path / "scenarios" / scenario / "docs"
    docs.mkdir(parents=True)

    prose = docs / "t01_prose.txt"
    prose.write_text(_PROSE_TEXT, encoding="utf-8")
    sources = [
        SourceRegistryEntry(
            source_id="t01_prose", source_type="trade-media", citation_url=str(prose)
        )
    ]
    if with_image:
        img = docs / "t02_image.png"
        img.write_bytes(_png())
        sources.append(
            SourceRegistryEntry(
                source_id="t02_image", source_type="satellite", citation_url=str(img)
            )
        )
    return scenario, ConfigBundle(sources=SourcesConfig(sources=sources))


def _dumps(claims: list[ClaimRecord]) -> list[dict[str, Any]]:
    return [c.model_dump(mode="json") for c in claims]


def _live_prose_pipeline(config: ConfigBundle, citation_url: str) -> list[ClaimRecord]:
    """Reproduce the live text pipeline independently (load → extract → dedup → id-assign)."""
    loaded = loaders.load_document(Path(citation_url).read_bytes(), file=citation_url)
    claims = extract.extract_document(
        loaded, source_id="t01_prose", source_type="trade-media", config=config,
        client=ScriptedExtractionClient([_PROSE_FILLED]), ingest_time=seed.FROZEN_INGEST_TIME,
    )
    claims = dedup.dedup_within_doc(claims)
    return dedup.assign_claim_ids(claims, doc_id="t01_prose")


# ── the recorder writes a bundle per source (text lane + .png imagery lane) ──────────────────────────

def test_extract_corpus_writes_one_bundle_per_source(tmp_path: Any) -> None:
    scenario, config = _tiny_scenario(tmp_path)
    out = tmp_path / "claims"

    written = seed.extract_corpus(scenario, client=_scripted(), config=config, out_dir=out)

    assert [p.name for p in written] == ["t01_prose.json", "t02_image.json"]
    assert (out / "t01_prose.json").exists() and (out / "t02_image.json").exists()

    prose_claims = seed.ingest_bundle(out / "t01_prose.json")
    assert len(prose_claims) == 1
    assert prose_claims[0].extraction.method == "llm"

    # a .png citation dispatched to the VLM imagery lane → a subject-blind observation claim.
    image_claims = seed.ingest_bundle(out / "t02_image.json")
    assert len(image_claims) == 1
    assert image_claims[0].kind == "observation"
    assert image_claims[0].extraction.method == "vlm"
    assert "image_fingerprint" in (image_claims[0].attributes or {})


# ── KEYLESS ≡ LIVE: a frozen bundle reads back to what a live extract of the doc produces ────────────

def test_ingest_bundle_equals_live_extraction(tmp_path: Any) -> None:
    scenario, config = _tiny_scenario(tmp_path, with_image=False)
    out = tmp_path / "claims"
    citation_url = config.sources.sources[0].citation_url
    assert citation_url is not None

    seed.extract_corpus(scenario, client=_scripted(), config=config, out_dir=out)

    frozen = seed.ingest_bundle(out / "t01_prose.json")
    live = _live_prose_pipeline(config, citation_url)
    assert _dumps(frozen) == _dumps(live)
    # readable, deterministic id derived from the source_id + span locator.
    assert frozen[0].claim_id == "t01-prose-l1"


# ── seeding a store from bundles yields exactly the bundles' claims, in order ────────────────────────

def test_seed_store_from_bundles_matches_claims(tmp_path: Any) -> None:
    scenario, config = _tiny_scenario(tmp_path)
    out = tmp_path / "claims"
    seed.extract_corpus(scenario, client=_scripted(), config=config, out_dir=out)

    expected: list[ClaimRecord] = []
    for path in sorted(out.glob("*.json")):
        expected += seed.ingest_bundle(path)

    store = EvidenceLog()
    count = seed.seed_store_from_bundles(store, out)

    assert count == len(expected)
    assert _dumps(store.replay()) == _dumps(expected)


def test_ingest_bundle_empty_file_is_empty(tmp_path: Any) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text("", encoding="utf-8")
    assert seed.ingest_bundle(empty) == []


# ── byte-stability: same pinned ingest_time → byte-identical bundles ─────────────────────────────────

def test_extract_corpus_is_byte_stable(tmp_path: Any) -> None:
    scenario, config = _tiny_scenario(tmp_path)
    out1 = tmp_path / "run1"
    out2 = tmp_path / "run2"

    seed.extract_corpus(scenario, client=_scripted(), config=config, out_dir=out1)
    seed.extract_corpus(scenario, client=_scripted(), config=config, out_dir=out2)

    for name in ("t01_prose.json", "t02_image.json"):
        assert (out1 / name).read_bytes() == (out2 / name).read_bytes()


# ── scenario filter: a source cited under a different scenario is skipped ─────────────────────────────

def test_extract_corpus_filters_by_scenario(tmp_path: Any) -> None:
    scenario, config = _tiny_scenario(tmp_path, with_image=False)
    # A second source living under a *different* scenario path — must not be recorded for `tinyscn`.
    other_docs = tmp_path / "scenarios" / "otherscn" / "docs"
    other_docs.mkdir(parents=True)
    other = other_docs / "o01_prose.txt"
    other.write_text(_PROSE_TEXT, encoding="utf-8")
    config.sources.sources.append(
        SourceRegistryEntry(source_id="o01_prose", source_type="trade-media", citation_url=str(other))
    )

    out = tmp_path / "claims"
    written = seed.extract_corpus(scenario, client=_scripted(), config=config, out_dir=out)

    assert [p.name for p in written] == ["t01_prose.json"]
    assert not (out / "o01_prose.json").exists()
