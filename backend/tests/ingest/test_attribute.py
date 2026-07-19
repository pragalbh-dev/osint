"""Attribution-proposer tests — the offline VLM-shape → variant-identity inference (``ingest/attribute.py``).

All offline + deterministic (gate G10): a :class:`ScriptedExtractionClient` replays the canned corroboration
judgement; the candidate rule runs over a hand-authored frozen ``GraphView`` (a Rahwali-shaped triangle:
subject-blind VLM shape A at a site, a textual variant-present claim C, an HQ-9 site-geometry fingerprint B).

The load-bearing invariants asserted here:

* **the bridge inference** — D is ``kind="inference"`` with ``premises=[A, B]`` (validator-enforced), a
  ``Triple`` copying C's exact ``(subject, predicate, object)`` (so RESOLVE co-locates D and C on one edge —
  SCORE's "second look"), cited to **both** the image region and the literature line (G4);
* **the decoy signal** — ``decoy_risk`` / ``decoy_risk_flag`` / ``single_pass`` ride D's attrs (the SCORE gate);
* **subject-blind** — the observation side of the scoped prompt never carries a variant token (G11);
* **deterministic + budgeted + convergent** — same inputs → byte-identical D; a budget cap logs over-budget
  skips; an already-attributed observation is skipped (idempotent re-runs);
* **raise-only / honest refusal** — D sets no status field; keyless / unconfigured ⇒ an empty run, never a guess.
"""

from __future__ import annotations

from typing import Any

import pytest

from chanakya.ingest import attribute
from chanakya.ingest.client import ScriptedExtractionClient
from chanakya.schemas.claim import (
    ClaimRecord,
    DocRef,
    EntityDescriptor,
    Extraction,
    SourceRegistryEntry,
    Triple,
)
from chanakya.schemas.config_models import ConfigBundle, CredibilityConfig, SourcesConfig
from chanakya.schemas.view import EdgeView, GraphView, NodeView

_VARIANT_TOKENS = ("hq-9", "hq9", "hq-9be", "hq9be", "s-400", "ht-233")

_CONSISTENT: dict[str, Any] = {
    "consistent": True,
    "matched_features": ["radial-revetments", "central-radar-berm"],
    "confidence_language": "consistent with",
    "rationale": "the observed radial revetment ring matches the reference HQ-9 battery site geometry",
}


# ── fixture builders (a Rahwali-shaped triangle; params toggle each clause for the negatives) ────────

def _obs(cid: str = "a-d18-obs", *, occupancy: str = "occupied") -> ClaimRecord:
    """Claim A — the subject-blind VLM shape observation (no variant token anywhere in it)."""
    return ClaimRecord(
        claim_id=cid, source_id="d18_rahwali_pass1",
        doc_ref=DocRef(file="corpus/scenarios/hq9p_primary/docs/d18_rahwali_pass1.png", region="full"),
        kind="observation", polarity="positive", asserts="entity",
        payload=EntityDescriptor(entity_type="basing_site", name="imagery-site:d18_rahwali_pass1", attrs={
            "geometry_tokens": ["ring-road", "linear-object-arrays", "dispersed-clusters"],
            "observed_features": [{"feature": "object cluster", "shape": "elongated",
                                   "arrangement": "linear arrays and small clusters"}],
            "occupancy_state": occupancy,
            "resolution_sufficiency": "sufficient",
            "frame_kind": "overhead",
            "description": "an unpaved ring road encloses ~20-25 dark elongated objects in linear arrays",
        }),
        extraction=Extraction(method="vlm", version="scripted"),
    )


def _text(cid: str = "c-d19-text", *, subject: str = "var_hq9be", object: str = "site_rahwali") -> ClaimRecord:
    """Claim C — the textual variant-present-at-site relationship claim whose triple D copies verbatim."""
    return ClaimRecord(
        claim_id=cid, source_id="d19_rahwali_confirm",
        doc_ref=DocRef(file="corpus/scenarios/hq9p_primary/docs/d19_rahwali_confirm.txt", line=15),
        kind="observation", polarity="positive", asserts="relationship",
        payload=Triple(subject=subject, predicate="based-at", object=object),
        extraction=Extraction(method="llm", version="scripted"),
    )


def _fp(cid: str = "b-d24-fp") -> ClaimRecord:
    """Claim B — the reference-literature HQ-9 site-geometry fingerprint (D's second premise)."""
    return ClaimRecord(
        claim_id=cid, source_id="d24_tel_chassis_attribution",
        doc_ref=DocRef(file="corpus/scenarios/hq9p_primary/docs/d24_tel_chassis_attribution.txt", line=12),
        kind="observation", polarity="positive", asserts="entity",
        payload=EntityDescriptor(entity_type="variant", name="HQ-9BE", attrs={
            "site_signature_geometry": ("petal/ring pad; ~6 radial TEL revetments around a central HT-233 "
                                        "berm; circular perimeter access road; ~8-9 m canisterized objects"),
        }),
        extraction=Extraction(method="llm", version="scripted"),
    )


def _config(*, budget: int | None = 8, ref_classes: list[str] | None = None,
            configured: bool = True) -> ConfigBundle:
    sources = SourcesConfig(sources=[
        SourceRegistryEntry(source_id="d18_rahwali_pass1", source_type="satellite", reliability_grade="B"),
        SourceRegistryEntry(source_id="d19_rahwali_confirm", source_type="think-tank", reliability_grade="B"),
        SourceRegistryEntry(source_id="d24_tel_chassis_attribution", source_type="think-tank", reliability_grade="B"),
    ])
    if not configured:
        return ConfigBundle(sources=sources, credibility=CredibilityConfig())
    proposer: dict[str, Any] = {
        "log_skips": True,
        "candidate": {
            "presence_edge_types": ["based-at"],
            "reference_source_classes": ref_classes or ["curated-register", "think-tank", "trade-media"],
            "fingerprint_attrs": ["site_signature_geometry", "observable_fingerprint", "equipment_fingerprint"],
            "variant_hop_edges": ["inducted-into", "equips"],
        },
    }
    if budget is not None:
        proposer["max_calls_per_rebuild"] = budget
    return ConfigBundle(sources=sources, credibility=CredibilityConfig(attribution_proposer=proposer))


def _scene(*, occupancy: str = "occupied", with_obs: bool = True, with_text: bool = True,
           with_fp: bool = True, attributed: bool = False,
           **cfg: Any) -> tuple[GraphView, dict[str, ClaimRecord], ConfigBundle]:
    """One Rahwali triangle; toggles drop a clause (for the candidate-negative tests)."""
    site, variant = "site_rahwali", "var_hq9be"
    claims: dict[str, ClaimRecord] = {}
    site_cids: list[str] = []
    var_cids: list[str] = []
    edge_cids: list[str] = []
    obs = _obs(occupancy=occupancy)
    if with_obs:
        claims[obs.claim_id] = obs
        site_cids.append(obs.claim_id)
    fp = _fp()
    if with_fp:
        claims[fp.claim_id] = fp
        var_cids.append(fp.claim_id)
    text = _text(subject=variant, object=site)
    if with_text:
        claims[text.claim_id] = text
        edge_cids.append(text.claim_id)
    if attributed:  # a prior inference already used A as a premise → convergence gate skips it
        prior = ClaimRecord(
            claim_id="d-prior-attr", source_id="d18_rahwali_pass1", doc_ref=obs.doc_ref,
            kind="inference", polarity="positive", asserts="relationship",
            payload=Triple(subject=variant, predicate="based-at", object=site),
            premises=[obs.claim_id, fp.claim_id], extraction=Extraction(method="llm", version="scripted"),
        )
        claims[prior.claim_id] = prior
    view = GraphView(
        nodes=[
            NodeView(id=site, type="basing_site", name="Rahwali", claim_ids=site_cids),
            NodeView(id=variant, type="variant", name="HQ-9BE", claim_ids=var_cids),
        ],
        edges=[EdgeView(id="e1", type="based-at", source=variant, target=site, claim_ids=edge_cids)],
    )
    return view, claims, _config(**cfg)


def _run(view: GraphView, claims: dict[str, ClaimRecord], config: ConfigBundle,
         responses: list[dict[str, Any]]) -> attribute.AttributionRun:
    return attribute.propose_attributions(view, claims, config, client=ScriptedExtractionClient(responses))


# ── the happy path: a well-formed, co-locating, cited bridge inference ───────────────────────────────

def test_emits_bridge_inference_with_both_premises() -> None:
    run = _run(*_scene(), [_CONSISTENT])
    assert run.fired == ["site_rahwali"]
    assert len(run.claims) == 1
    d = run.claims[0]
    assert d.kind == "inference" and d.asserts == "relationship"
    assert d.premises == ["a-d18-obs", "b-d24-fp"]  # [A, B], non-empty (validator enforces)
    assert d.extraction.method == "llm"


def test_copies_textual_triple_verbatim() -> None:
    """D must assert C's exact (subject, predicate, object) so RESOLVE co-locates them on one edge."""
    view, claims, config = _scene()
    d = _run(view, claims, config, [_CONSISTENT]).claims[0]
    c = claims["c-d19-text"].payload
    assert isinstance(d.payload, Triple)
    assert (d.payload.subject, d.payload.predicate, d.payload.object) == (c.subject, c.predicate, c.object)


def test_cites_both_image_and_literature() -> None:
    d = _run(*_scene(), [_CONSISTENT]).claims[0]
    refs = d.doc_refs()
    assert len(refs) == 2
    assert any(r.region == "full" and r.file.endswith(".png") for r in refs)          # the image region
    assert any(r.line == 12 and r.file.endswith("d24_tel_chassis_attribution.txt") for r in refs)  # the literature line


def test_attrs_carry_decoy_and_provenance() -> None:
    d = _run(*_scene(), [_CONSISTENT]).claims[0]
    a = d.attributes or {}
    assert a["decoy_risk"] is True and a["decoy_risk_flag"] is True and a["single_pass"] is True
    assert a["fingerprint_match"]  # matched features (or True)
    assert a["corroborated_against"] == "b-d24-fp"
    assert a["attributed_variant"] == "var_hq9be"


def test_raise_only_no_status_fields() -> None:
    """Structurally raise-only: a raw claim has no status/confidence — nothing to accidentally set."""
    d = _run(*_scene(), [_CONSISTENT]).claims[0]
    dumped = d.model_dump()
    for forbidden in ("status", "assertion_confidence", "confirmed", "confidence"):
        assert forbidden not in dumped
    assert d.extraction.model_conf == 1.0


def test_deterministic() -> None:
    """Same inputs + same recorded transcript → byte-identical D (gate G2)."""
    d1 = _run(*_scene(), [_CONSISTENT]).claims[0]
    d2 = _run(*_scene(), [_CONSISTENT]).claims[0]
    assert d1.model_dump(mode="json") == d2.model_dump(mode="json")


def test_subject_blind_observation_side() -> None:
    """The observation half of the scoped prompt carries no variant token; the name enters only as literature."""
    class _Capturing(ScriptedExtractionClient):
        prompts: list[str]

        def __init__(self, responses: list[dict[str, Any]]) -> None:
            super().__init__(responses)
            self.prompts = []

        def extract(self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
                    images: Any = ()) -> dict[str, Any]:
            self.prompts.append(text)
            return super().extract(tool_name=tool_name, input_schema=input_schema, system=system, text=text)

    view, claims, config = _scene()
    client = _Capturing([_CONSISTENT])
    attribute.propose_attributions(view, claims, config, client=client)
    prompt = client.prompts[0]
    observed = prompt.split("REFERENCE SITE-GEOMETRY")[0].lower()  # the observation half only
    assert not any(tok in observed for tok in _VARIANT_TOKENS)
    assert "REFERENCE SITE-GEOMETRY" in prompt and "radial TEL revetments" in prompt  # reference IS present


# ── candidate-rule negatives: each ⇒ no LLM call (empty queue would raise), no D, a skip logged ──────

@pytest.mark.parametrize("kwargs,reason", [
    ({"with_obs": False}, "no-vlm-shape-observation"),
    ({"attributed": True}, "already-attributed"),
    ({"with_text": False}, "no-textual-variant"),
    ({"with_fp": False}, "no-fingerprint-literature"),
    ({"occupancy": "empty-pads"}, "ineligible-frame"),
])
def test_candidate_negatives_skip_without_calling_llm(kwargs: dict[str, Any], reason: str) -> None:
    view, claims, config = _scene(**kwargs)
    run = attribute.propose_attributions(view, claims, config, client=ScriptedExtractionClient([]))  # empty → raises if called
    assert run.claims == [] and run.fired == []
    assert reason in [s.reason for s in run.skipped]


def test_source_class_filter_excludes_nonreference_fingerprint() -> None:
    """A fingerprint from a source outside reference_source_classes does not satisfy clause (c)."""
    view, claims, _ = _scene()
    config = _config(ref_classes=["curated-register"])  # excludes the think-tank fingerprint source
    run = attribute.propose_attributions(view, claims, config, client=ScriptedExtractionClient([]))
    assert run.claims == []
    assert "no-fingerprint-literature" in [s.reason for s in run.skipped]


def test_not_consistent_fires_but_emits_nothing() -> None:
    run = _run(*_scene(), [{"consistent": False}])
    assert run.fired == ["site_rahwali"] and run.claims == []
    assert "not-consistent" in [s.reason for s in run.skipped]


# ── budget, dormancy, keyless ────────────────────────────────────────────────────────────────────

def test_budget_cap_logs_over_budget() -> None:
    """Two triangles, budget 1 → one D fires, the other is logged over-budget."""
    variant = "var_hq9be"
    fp = _fp()
    obs1 = _obs("a1")
    obs2 = ClaimRecord(  # a second site's VLM shape (distinct source/id)
        claim_id="a2", source_id="d17_rawalpindi_2021",
        doc_ref=DocRef(file="corpus/scenarios/hq9p_primary/docs/d17_rawalpindi_2021.png", region="full"),
        kind="observation", polarity="positive", asserts="entity",
        payload=EntityDescriptor(entity_type="basing_site", name="imagery-site:d17_rawalpindi_2021", attrs={
            "geometry_tokens": ["semi-radial-objects", "central-hardstand"],
            "occupancy_state": "occupied", "resolution_sufficiency": "sufficient", "frame_kind": "overhead",
            "description": "six elongated objects in a semi-radial pattern about a central hardstand",
        }),
        extraction=Extraction(method="vlm", version="scripted"),
    )
    c1 = _text("c1", subject=variant, object="site_a")
    c2 = _text("c2", subject=variant, object="site_b")
    claims = {c.claim_id: c for c in (obs1, obs2, fp, c1, c2)}
    view = GraphView(
        nodes=[
            NodeView(id="site_a", type="basing_site", name="A", claim_ids=["a1"]),
            NodeView(id="site_b", type="basing_site", name="B", claim_ids=["a2"]),
            NodeView(id=variant, type="variant", name="HQ-9BE", claim_ids=["b-d24-fp"]),
        ],
        edges=[
            EdgeView(id="e_a", type="based-at", source=variant, target="site_a", claim_ids=["c1"]),
            EdgeView(id="e_b", type="based-at", source=variant, target="site_b", claim_ids=["c2"]),
        ],
    )
    config = _config(budget=1)
    # need to register the 2nd site's source so clause-(c)/eligibility resolve
    config.sources.sources.append(
        SourceRegistryEntry(source_id="d17_rawalpindi_2021", source_type="satellite", reliability_grade="B"))
    run = attribute.propose_attributions(view, claims, config, client=ScriptedExtractionClient([_CONSISTENT]))
    assert len(run.claims) == 1
    assert "over-budget" in [s.reason for s in run.skipped]


def test_dormant_when_unconfigured() -> None:
    view, claims, _ = _scene()
    config = _config(configured=False)
    run = attribute.propose_attributions(view, claims, config, client=ScriptedExtractionClient([_CONSISTENT]))
    assert run.claims == [] and run.fired == [] and run.skipped == []


def test_keyless_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """No client + no key → an empty run (honest refusal); the frozen-bundle path materialises D instead."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    view, claims, config = _scene()
    run = attribute.propose_attributions(view, claims, config, client=None)
    assert run.claims == []


# ── orchestration: enrich (rebuild → propose → append → rebuild) + the frozen-bundle recorder ──────

def test_enrich_appends_and_converges() -> None:
    """enrich() rebuilds→proposes→appends→re-rebuilds; a second pass is a no-op (idempotent, convergent)."""
    from chanakya.store.log import EvidenceLog

    view, claims, config = _scene()
    store = EvidenceLog()
    store.append_many(list(claims.values()))
    n0 = store.count()

    def rebuild_fn(evidence: Any, decision: Any, cfg: Any) -> GraphView:
        return view  # the frozen resolved view (D is read back from the store, not this stub)

    run1 = attribute.enrich(store, config, client=ScriptedExtractionClient([_CONSISTENT]), rebuild_fn=rebuild_fn)
    assert len(run1.claims) == 1 and store.count() == n0 + 1  # D appended upstream of the next rebuild

    run2 = attribute.enrich(store, config, client=ScriptedExtractionClient([_CONSISTENT]), rebuild_fn=rebuild_fn)
    assert run2.claims == []  # A is now a premise of the appended D → already-attributed → convergent


def test_freeze_bundles_roundtrip(tmp_path: Any) -> None:
    """freeze_bundles writes a *__attr.json bundle that round-trips back to the same claim (KEYLESS ≡ LIVE)."""
    from chanakya.ingest import seed

    run = _run(*_scene(), [_CONSISTENT])
    written = attribute.freeze_bundles(run, tmp_path)
    assert len(written) == 1 and written[0].name.endswith("__attr.json")
    back = seed.ingest_bundle(written[0])
    assert [c.model_dump(mode="json") for c in back] == [c.model_dump(mode="json") for c in run.claims]


# ── one opt-in live smoke (skipped without a key) ────────────────────────────────────────────────

@pytest.mark.live
def test_live_corroboration_smoke() -> None:
    import os

    from chanakya.ingest.client import build_extraction_client

    if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("GEMINI_API_KEY")):
        pytest.skip("no extraction key")
    view, claims, config = _scene()
    run = attribute.propose_attributions(view, claims, config, client=build_extraction_client())
    # invariant only: a valid D or an honest skip — never a crash, never a malformed claim.
    for d in run.claims:
        assert d.kind == "inference" and d.premises == ["a-d18-obs", "b-d24-fp"] and len(d.doc_refs()) == 2
