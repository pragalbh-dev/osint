"""RK-COREF (S3) — the plumbing: both gates flipped, the referent mint, the quote, the contrast lane,
and "fragmentation resolves by **earned** merges".

Authored from the session spec alone. Scope 1, quoted:

    "**Promote Tier-0 coref to a required tier.** ``ingest/coref.py`` from optional to required; the
    doc-local cluster **groups the per-mention claim atoms** and is **where the referent atom is minted**
    (``make_referent_id``, dormant since S1, invoked here). **Two independent gates must both flip** — the
    producer (``config/credibility.yaml`` ``coreference``, currently commented out) *and* the consumer
    (``config/resolution.yaml`` ``coref_authoritative_evidence``, currently ``[]``)."

Scope 4 (decision (b)), quoted: "a **contrastive channel** on coref (``coref-distinct-from``, its own lane —
**never** the stated ``distinct-from`` rail, which is hard, transitive and ungraded: every ORBAT list contains
an enumeration). Same-doc stated contrast ⇒ **band ceiling at ``probable``**, ungraded, **a band name not a
float**. Absence of contrast is **neutral**."

And the acceptance line this file refuses to turn into a number: "**Fragmentation resolves by earned merges,
with no threshold loosened.**" — "If you are tempted to lower a floor to reduce fragmentation, that is the
trap the whole design exists to prevent (it is the name-collapse bug wearing a different hat)." So nothing
here asserts a fragmentation *count*; it asserts that every merge names its earning signal.
"""

from __future__ import annotations

from chanakya.ingest import coref as coref_module
from chanakya.resolve.rconfig import ResolveConfig
from chanakya.schemas import pair_key
from chanakya.view.coverage import identity_coverage
from tests import _rk_atoms as ra
from tests import _rk_coref as rc
from tests import _rk_layer as rk

# ── both switches ───────────────────────────────────────────────────────────────────────────────

def test_the_coreference_producer_is_configured() -> None:
    """The producer half. "``{}`` ⇒ the pass returns ``[]``" — the block is commented out today, so the
    pass is dormant however the consumer is set.
    """
    block = rc.coref_producer_block()
    assert block, (
        "config/credibility.yaml declares no `coreference` block, so ingest/coref.py returns [] and Tier 0 "
        "produces nothing. Scope 1 promotes the pass from optional to REQUIRED — that is this switch."
    )
    categories = coref_module._categories(block)
    assert coref_module.EXPLICIT_EQUIVALENCE in categories, (
        f"the producer emits {categories}, which never includes the one category D-13.17 grades "
        "authoritative — so the consumer switch below could never bind anything."
    )


def test_the_consumer_switch_is_flipped_and_only_for_licensed_categories() -> None:
    """The consumer half — "With it empty, ``_coref_pairs`` routes **every** pair to ``raise_only`` … So
    enabling the producer alone changes nothing."
    """
    allowed = rc.coref_authoritative()
    assert allowed, (
        "config/resolution.yaml still ships `coref_authoritative_evidence: []`, so every cluster is "
        "raise-only and D-13.17's policy is inert. 'Two independent gates must both flip.'"
    )
    assert coref_module.EXPLICIT_EQUIVALENCE in allowed, (
        f"coref_authoritative_evidence={allowed} omits EXPLICIT_EQUIVALENCE — the category the document "
        "itself *states*, and the only one D-13.17 makes unconditionally authoritative."
    )
    unknown = [c for c in allowed if c not in coref_module.EVIDENCE_CATEGORIES]
    assert not unknown, f"coref_authoritative_evidence names categories the producer cannot emit: {unknown}"


def test_the_demo_beat_is_not_a_reason_to_keep_the_switch_off() -> None:
    """The shipped comment gives two reasons for the empty list; the second was overruled.

    `rk-spike-DECISIONS.md`: "*Justification 2* — preserving the d10 'HT-233 (H-200)' orphan-alias beat an
    analyst is meant to earn — is **demo preservation, forbidden as a design input** (working-principles #1).
    **Overruled.**" Recorded as a test because it is the kind of reason that quietly comes back.
    """
    yaml_text = (rk.REPO_ROOT / "config" / "resolution.yaml").read_text(encoding="utf-8")
    block = yaml_text.split("coref_authoritative_evidence")[0].rsplit("\n\n", 1)[-1]
    assert "HT-233" not in block or rc.coref_authoritative(), (
        "the switch is still off and the comment still justifies it with the d10 'HT-233 (H-200)' demo beat. "
        "The policy is decided on general principle; 'the data pass owes a re-carried beat'."
    )


# ── the referent atom is minted at ingest, over the cluster ─────────────────────────────────────

def test_make_referent_id_is_invoked_at_ingest() -> None:
    """Scope 1: ``make_referent_id`` is "dormant since S1, invoked here". A1 puts the mint at ingest, and
    G17 forbids minting anywhere under ``rebuild()``, so the call site must be in the ingest package.
    """
    sites = ra.call_sites("make_referent_id")
    ingest_sites = [s for s in sites if s.startswith("ingest/")]
    assert ingest_sites, (
        f"make_referent_id has no call site under ingest/ (all call sites: {sites}). The referent atom is "
        "still dormant, so the doc-local cluster is not the mint grain and nothing groups the per-mention "
        "claim atoms."
    )


def test_emitted_coref_claims_carry_the_referent_atom() -> None:
    """The mint, observed on the emission rather than by scanning: the cluster's claims must share one
    referent id, because the referent *is* the grouping ("evidence about a grouping").
    """
    mentions = [
        coref_module.Mention(1, "Alpha Precision Machinery", "manufacturer", "c-1"),
        coref_module.Mention(2, "APM", "manufacturer", "c-2"),
        coref_module.Mention(3, "the export agency", coref_module.UNKNOWN_TYPE, None),
    ]
    accepted = [(mentions, coref_module.EXPLICIT_EQUIVALENCE, "Alpha Precision Machinery (APM)")]
    claims = coref_module.coref_claims(
        accepted, claims=[], loaded=_loaded(), source_id="d1", model_id="test",
        report_time=None, ingest_time=None,
    )

    assert claims, "coref_claims emitted nothing for a well-formed accepted cluster"
    referents = {ra.referent_of(c) for c in claims}
    assert referents != {None}, (
        f"the emitted coref claims carry no referent atom ({referents}). S1 added the field dormant "
        "precisely so S3 could mint against the cluster; without it the grouping has no address to be "
        "evidence *about*."
    )
    assert len(referents) == 1, (
        f"one cluster emitted {len(referents)} referent atoms ({referents}). The referent is the grouping, "
        "so a cluster mints ONE — 'the forbidden shape is minting one referent atom per *proposal*'."
    )


def _loaded():
    """A real ``LoadedDoc`` — the production type, so the emission path is the production path."""
    from chanakya.ingest.loaders import LoadedDoc

    return LoadedDoc(
        file="d1.txt", media_type="text/plain", modality="text",
        text="Alpha Precision Machinery (APM) shipped in March.",
    )


# ── the licensing quote must be readable by the analyst ─────────────────────────────────────────

def test_a_raise_only_bind_hands_the_analyst_its_licensing_quote() -> None:
    """D-13.17's required build item: "**The raise-only licensing quote is written but read nowhere.** Both
    analyses justify raise-only by 'the analyst is handed the exact sentence' … **Wire it, or the mitigation
    that makes raise-only acceptable is fictional.**"
    """
    quote = "SINO-GALAXY Trading Co, styled Sinogalaxy Trading Company in the manifest"
    claims = [
        rc.ent("n1", "manufacturer", "SINO-GALAXY Trading Co"),
        rc.ent("n2", "manufacturer", "Sinogalaxy Trading Company"),
        rc.coref("n1", "n2", evidence=rc.NAME_VARIANT, quote=quote, cid="coref-nv"),
    ]
    part = rc.part_of(claims, rc.bundle())

    assert rc.status(part, "n1", "n2") == "probable", (
        f"the raise-only pair is {rc.status(part, 'n1', 'n2')!r} rather than a candidate — raise-only means "
        "'a probable HITL candidate with the merge one click away'."
    )
    reachable = quote in rc.reason(part, "n1", "n2") or "coref-nv" in part.identity_claims.get(
        pair_key("n1", "n2"), []
    )
    assert reachable, (
        "nothing on the candidate reaches the licensing sentence: the reason does not carry it and "
        f"identity_claims does not cite the coref claim ({part.identity_claims.get(pair_key('n1', 'n2'))}). "
        "The quote is stamped onto the claim and never surfaced, which makes the raise-only mitigation "
        "fictional."
    )


# ── the contrastive channel (decision (b)) ──────────────────────────────────────────────────────

def test_the_contrast_lane_is_declared_and_is_not_the_stated_distinct_from_rail() -> None:
    """(b): "its own ``coref-distinct-from`` lane … **Deliberately not the existing stated-``distinct-from``
    rail**: that channel … lands as a **hard, transitive, ungraded** veto. Widening an ungraded transitive
    veto to 'any enumeration' is the single worst thing this spike could have recommended — **every ORBAT
    list contains one**."
    """
    edges = {e["name"]: e for e in rk.shipped_ontology_yaml()["edge_types"]}
    assert rc.CONTRAST_PREDICATE in edges, (
        f"the ontology declares no {rc.CONTRAST_PREDICATE!r} edge ({sorted(edges)}). Coref's mention shape "
        "has no spans and pass 1 collapses one name to one claim per document, so nothing downstream can "
        "re-read the syntax: the contrast is 'not derivable downstream' and needs its own lane."
    )
    assert rc.CONTRAST_PREDICATE != "distinct-from"


def _contrast_fixture(*, contrast: bool, same_doc: bool = True) -> list:
    doc_b = "d1" if same_doc else "d2"
    claims = [
        rc.ent("u1", "unit", "Alpha Battery", doc="d1"),
        rc.ent("u2", "unit", "Alpha Battery", doc=doc_b, sid="mid"),
        *rc.shared_neighbours("u1", "u2", doc_a="d1", doc_b=doc_b, sid_b="mid"),
    ]
    if contrast:
        claims.append(rc.contrast("u1", "u2", doc="d1",
                                 quote="the 8th AD Bn and the separate 12th AD Bn"))
    return claims


def test_a_same_document_stated_contrast_caps_the_pair_at_probable() -> None:
    """(b): "A same-doc **stated-contrast** pair is **capped at ``probable``**: it reaches the analyst with
    its licensing quote and can **never auto-merge**." — "contrast means 'not automatically', never 'not at
    all.'"
    """
    control = rc.part_of(_contrast_fixture(contrast=False), rc.bundle())
    assert rc.fused(control, "u1", "u2"), (
        "the control pair did not fuse, so the ceiling below has nothing to withhold and the test is "
        f"vacuous (status={rc.status(control, 'u1', 'u2')})"
    )

    part = rc.part_of(_contrast_fixture(contrast=True), rc.bundle())
    assert not rc.fused(part, "u1", "u2"), (
        "a document that syntactically distinguishes its two mentions still auto-merged them. "
        f"same_as={part.same_as}"
    )
    assert rc.status(part, "u1", "u2") == "probable", (
        f"the contrasted pair reads {rc.status(part, 'u1', 'u2')!r}. A *ceiling* keeps the pair in the "
        "analyst's queue; a score penalty would drop it two bands out of the queue entirely, which is why "
        "the mechanism is a band name and not a coefficient."
    )
    assert not rc.walled(part, "u1", "u2"), (
        "the contrast landed on the hard, transitive `distinct_from` rail. That is the one thing (b) "
        "rejects outright: a ceiling 'cannot shatter anything', a veto shatters a well-corroborated cluster."
    )


def test_the_contrast_ceiling_is_configured_as_a_band_name() -> None:
    """(b): "**a band name not a float**" — "A band ceiling is threshold-independent … Any coefficient
    carries this hazard and its safe value depends on thresholds that will move."
    """
    keys = [k for k in rc.resolution_keys() if "contrast" in k.lower()]
    assert keys, (
        f"config/resolution.yaml declares no contrast knob (searched every resolution key for 'contrast'; "
        f"keys are {sorted(rc.resolution_keys())})"
    )
    values = {k: rc.resolution_keys()[k] for k in keys}
    floats = {k: v for k, v in values.items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
    assert not floats, (
        f"the contrast ceiling is declared numerically: {floats}. It must be a band NAME — with "
        "auto_merge 0.85 / hitl_low 0.45 a ×0.5 penalty moves a 0.85 pair to 0.425, i.e. below hitl_low, "
        "silently dropping the pair out of the analyst queue."
    )


def test_absence_of_contrast_is_neutral() -> None:
    """(b): "Absence of contrast is **neutral** — never a prior *for* merging either." The control pair must
    not be *helped* by the silence, so the same pair must behave identically whether or not the lane exists.
    """
    same_doc = rc.part_of(_contrast_fixture(contrast=False, same_doc=True), rc.bundle())
    cross_doc = rc.part_of(_contrast_fixture(contrast=False, same_doc=False), rc.bundle())

    assert rc.status(same_doc, "u1", "u2") == rc.status(cross_doc, "u1", "u2"), (
        f"an uncontrasted same-document pair reads {rc.status(same_doc, 'u1', 'u2')!r} while the identical "
        f"cross-document pair reads {rc.status(cross_doc, 'u1', 'u2')!r}. Same-document silence is neither "
        "evidence for nor against identity."
    )


def test_a_contrast_never_leaks_onto_a_cross_document_pair() -> None:
    """Why (b) needs ``Entity.doc_ids``: it "scopes the contrast channel so a doc-local contrast cannot leak
    onto cross-doc pairs through ``_matching_eids``' global name expansion".

    The distinction is deliberate — a *publisher* is not a document, so ``source_ids`` cannot carry it.
    """
    claims = _contrast_fixture(contrast=True, same_doc=True)
    claims.append(rc.ent("u3", "unit", "Alpha Battery", doc="d9", sid="hi"))
    claims += rc.shared_neighbours("u1", "u3", design="d", operator="op", doc_a="d1", doc_b="d9", sid_b="hi")
    part = rc.part_of(claims, rc.bundle())

    assert rc.status(part, "u1", "u3") != "possible" or rc.fused(part, "u1", "u3"), (
        "a contrast stated inside d1 also demoted the d1↔d9 pair, which no document contrasted. The lane "
        f"must be document-scoped. status={rc.status(part, 'u1', 'u3')}"
    )


# ── fragmentation resolves by EARNED merges (never by a loosened floor) ─────────────────────────

def test_every_fused_pair_names_a_signal_other_than_the_name() -> None:
    """The acceptance line, expressed as an invariant rather than a count.

    D-13.10: "design collapses readily but *never on name alone* (name is a rarity-graded contributor,
    capped at *possible*)". So a merge is *earned* when something other than the surface string carried it —
    and a fixture-independent way to say that is: no fused pair may show the name signal as its only
    non-zero identity evidence.

    Deliberately **not** "fragmentation must fall to N": a count target is what pressures an implementer to
    lower a floor, which "is the name-collapse bug wearing a different hat".
    """
    claims = [
        # earned: same composite identifier
        rc.ent("earned_a", "unit", "8th AD Battalion",
               attrs={"service_branch": "PAF", "designator": "8"}, doc="d1"),
        rc.ent("earned_b", "unit", "the 8 AD Bn",
               attrs={"service_branch": "PAF", "designator": "8"}, doc="d2", sid="mid"),
        *rc.shared_neighbours("earned_a", "earned_b"),
        # unearned: an identical descriptor and nothing else
        rc.ent("bare_a", "basing_site", "forward dispersal site", doc="d1"),
        rc.ent("bare_b", "basing_site", "forward dispersal site", doc="d2", sid="mid"),
    ]
    part = rc.part_of(claims, rc.bundle())

    breakdowns = {pair: bd for pair, bd in part.merge_breakdown.items()}
    name_keys = {k for bd in breakdowns.values() for k in bd if "name" in k.lower()}
    assert name_keys, (
        "no stored breakdown names a `name` signal, so 'this merge rests on the name alone' is not even "
        f"expressible and this invariant cannot be checked. Signals seen: "
        f"{sorted({k for bd in breakdowns.values() for k in bd})}"
    )

    unearned = []
    for a, b in part.same_as:
        signals = {k: v for k, v in rc.signals(part, a, b).items() if k != "total" and v}
        if signals and all(k in name_keys for k in signals):
            unearned.append((a, b, signals))

    assert not unearned, (
        f"these merges rest on the name signal alone: {unearned}. Fragmentation must resolve by earning "
        "merges, and a name is 'a rarity-graded contributor, capped at possible' — never a verdict."
    )


def test_residual_fragmentation_is_reported_rather_than_hidden() -> None:
    """Acceptance: "Residual fragmentation reports as a ``/coverage`` gap."

    §6's defence of residual fragmentation only holds if the residue is *visible*: an unresolvable tail is a
    collection signal ("collect more here, not tune the resolver"), and reporting it is what makes refusing
    to fuse honest rather than merely quiet.
    """
    from chanakya.resolve import resolve_with_types

    claims = []
    for i in range(4):
        claims += [
            rc.ent(f"u{i}", "unit", "air defence battery", doc=f"d{i}", sid="mid"),
        ]
    claims += rc.shared_neighbours("u0", "u1", doc_a="d0", doc_b="d1", sid_b="mid")
    claims += [
        rc.rel("r-ind-2", "d", "inducted-into", "u2", doc="d2", iso="2020-04-01", sid="mid"),
        rc.rel("r-ind-3", "d", "inducted-into", "u3", doc="d3", iso="2020-05-01", sid="mid"),
    ]
    cfg = rc.bundle()
    part, types = resolve_with_types(claims, cfg)
    cov = identity_coverage(part, types, ResolveConfig.from_bundle(cfg))

    assert cov.coverage_gap_ratio is not None, (
        "no coverage gap ratio is in force, so an unresolved identity tail is never reported as a "
        "collection gap and residual fragmentation is simply invisible."
    )
    unresolved = len(part.candidates) + len(part.possible)
    assert unresolved == 0 or cov.by_type, (
        f"{unresolved} unresolved identity links exist but the coverage summary reports nothing by type "
        f"({cov}). The honest response to a fragmented type is 'collect more here'."
    )
