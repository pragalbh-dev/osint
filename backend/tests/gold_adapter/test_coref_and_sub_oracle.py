"""The coref registry (S9) and the sub-oracle exclusions (S11).

Both are places where carrying the source through unthinkingly produces a number that looks measured and
is not: B-cubed over 16 singleton bookkeeping tags, or edge recall over 10 edges the gold says are not
derivable.
"""

from __future__ import annotations

from typing import Any

import pytest

from eval.gold.adapter import ReconciliationError, adapt_sub_oracle, strip_annotator_locator

from .conftest import EXPECTED

# ── the coref registry ────────────────────────────────────────────────────────────────────────────

def _retagged_by_the_repair(raw_gold: dict[str, Any]) -> list[str]:
    """The rows the 2026-07-26 gold repair re-routed off their registry cluster, per the gold's own log.

    Read from the audit log rather than transcribed, so the relationship asserted below is between two
    things the *gold* states, not between two literals a test remembers.
    """
    entries = [e for e in raw_gold["audit_log"] if "anti_coref_routing" in e]
    assert len(entries) == 1, "the gold declares more than one anti-coref routing repair"
    return list(entries[0]["anti_coref_routing"]["retagged_rows"])


def test_registry_carries_the_curated_clusters(adapted: dict[str, Any]) -> None:
    registry = adapted["coref_registry"]
    assert len(registry) == EXPECTED["coref_clusters"] == 32
    assert sum(len(c["mentions"]) for c in registry) == EXPECTED["coref_mentions"] == 120
    assert all(c["licensing_category"] and c["licensing_quote"] for c in registry)


def test_only_curated_clusters_are_scoreable_on_a_claim(
    raw_gold: dict[str, Any], adapted: dict[str, Any],
) -> None:
    """S9: an ad-hoc row tag must not become coref gold — B-cubed over singletons is not a measurement.

    The scoreable count fell 51 → 39 in the 2026-07-26 gold repair, which re-routed twelve rows off the
    two ANTI_COREF registry clusters that had been tagging positive claims. That is asserted as the
    RELATIONSHIP — 39 plus the repair's own list of re-routed rows reproduces the 51 this test froze on
    2026-07-25 — because a bare new literal would say nothing about whether the drop was the repair or a
    silently dropped tag.
    """
    curated = {c["cluster"] for c in adapted["coref_registry"]}
    by_row = {r["row_id"]: r for r in raw_gold["rows"]}
    scoreable = set()
    for claim in adapted["claims"]:
        tag = claim.get("coref_cluster")
        if tag is None:
            continue
        scoreable.add(claim["gold_id"])
        assert tag in curated, f"{claim['gold_id']}: non-registry tag {tag!r} became coref gold"

    retagged = _retagged_by_the_repair(raw_gold)
    assert len(scoreable) == 39
    assert len(scoreable) + len(retagged) == 51, (
        "the drop from the pre-repair 51 is no longer accounted for by the declared retag alone — a tag "
        "moved for some other reason and this filter needs re-measuring, not re-baselining"
    )
    # the retag moved each row's CLUSTER, not the row: all twelve are still scored claims, and none of
    # them is scoreable coref gold any more.
    claim_ids = {c["gold_id"] for c in adapted["claims"]}
    assert set(retagged) <= claim_ids, "a re-routed row left the scored set: that is not a retag"
    assert not (set(retagged) & scoreable), "a re-routed row is still coref gold: the retag did not take"

    # and rows whose tag is NOT in the registry really do exist — otherwise the filter is untested
    non_registry = [r for r in by_row.values()
                    if r.get("coref_cluster") not in (None, "-")
                    and r["coref_cluster"] not in curated]
    assert non_registry, "no non-registry tags in the source: this test would be vacuous"


def test_annotator_locators_are_stripped_from_mentions(adapted: dict[str, Any]) -> None:
    """The gold's ``mention_verbatim_note``, corrected by measurement: **12** locators, not 13.

    A purely syntactic trailing-parenthetical strip fires on 20 of the 120 mentions. Eight of those
    parentheticals are genuine document text (``PORT MUHAMMAD BIN QASIM (PQ)``, ``Baseline imagery
    (2024-11)``) and truncating them would make a correct mention unmatchable, so the strip is conditional
    on the annotated form not occurring in its document.
    """
    mentions = [m for c in adapted["coref_registry"] for m in c["mentions"]]
    assert len(mentions) == EXPECTED["coref_mentions"]
    stripped = [m for m in mentions if m["locator_stripped"]]
    assert len(stripped) == 12
    for m in stripped:
        assert m["text"] != m["annotated"]
        assert not m["text"].endswith(")")
        assert m["verbatim_in_document"], "a strip that leaves an unmatchable mention is the wrong strip"
    kept = [m for m in mentions if not m["locator_stripped"] and m["annotated"].rstrip().endswith(")")]
    assert len(kept) == 8, "the parentheticals that ARE document text must survive"


def test_one_mention_is_not_verbatim_and_says_so(adapted: dict[str, Any]) -> None:
    """119/120, not the 120/120 the gold's note claims — and the odd one is flagged, not hidden.

    ``d17b-AMBIG-1``'s Telegram caption differs from the document only in where the comma sits relative to
    the closing quotation mark. Carrying ``verbatim_in_document: false`` lets an exact-match scorer see
    that the mention is unmatchable instead of charging the miss to a candidate. LABELLING OBSERVATION,
    reported to the data owner and not corrected here.
    """
    mentions = [m for c in adapted["coref_registry"] for m in c["mentions"]]
    non_verbatim = [m for m in mentions if not m["verbatim_in_document"]]
    assert len(non_verbatim) == 1
    assert "imagery pending" in non_verbatim[0]["text"]
    assert adapted["reconciliation"]["coref"]["mentions_verbatim_in_their_document"] == 119


def test_stripping_needs_the_document_to_be_right() -> None:
    doc = "Handle: @faisal_defencewatch\nthe FT-2000 (sometimes rendered FT-2000A) is an older name."
    # a locator the document does not contain → stripped
    assert strip_annotator_locator("@faisal_defencewatch (Post 1)", doc) == "@faisal_defencewatch"
    # a parenthetical the document DOES contain → kept, or an exact-match scorer can never find it
    assert strip_annotator_locator("the FT-2000 (sometimes rendered FT-2000A)", doc) == (
        "the FT-2000 (sometimes rendered FT-2000A)"
    )
    # without a document the rule is shape-only, and over-strips exactly that case
    assert strip_annotator_locator("the FT-2000 (sometimes rendered FT-2000A)") == "the FT-2000"


def test_stripping_only_touches_a_trailing_parenthetical() -> None:
    assert strip_annotator_locator("the HQ9B btry (Post 1)") == "the HQ9B btry"
    assert strip_annotator_locator("a Pakistan Army Air Defence (PAAD) unit") == (
        "a Pakistan Army Air Defence (PAAD) unit"
    ), "an inline parenthetical is document text and must survive"


# ── the sub-oracle ────────────────────────────────────────────────────────────────────────────────

def test_sub_oracle_nothing_lost(raw_sub_oracle: dict[str, Any], adapted_oracle: dict[str, Any]) -> None:
    rec = adapted_oracle["reconciliation"]
    assert rec["scored_nodes"] + rec["excluded_nodes"] == rec["source_nodes"] == len(
        raw_sub_oracle["nodes"])
    assert rec["scored_edges"] + rec["excluded_edges"] == rec["source_edges"] == len(
        raw_sub_oracle["edges"])
    assert (rec["scored_nodes"], rec["scored_edges"]) == (26, 14)


def test_insufficient_evidence_edges_leave_the_denominator(adapted_oracle: dict[str, Any]) -> None:
    """S11: scoring these penalises the refusal the project treats as non-negotiable."""
    excluded = [e for e in adapted_oracle["excluded_edges"]
                if e["excluded_because"].startswith("insufficient-evidence")]
    assert len(excluded) == 5
    assert all(e["status"] == "insufficient-evidence" for e in excluded)
    scored_types = {(e["source"], e["type"], e["target"]) for e in adapted_oracle["edges"]}
    for e in excluded:
        assert (e["source"], e["type"], e["target"]) not in scored_types


def test_insufficient_evidence_nodes_are_kept(
    raw_sub_oracle: dict[str, Any], adapted_oracle: dict[str, Any],
) -> None:
    """A known-gap NODE still exists in the graph; only the un-derivable EDGE is excluded."""
    source_gap_nodes = {n["node_id"] for n in raw_sub_oracle["nodes"]
                        if n.get("status") == "insufficient-evidence"}
    assert source_gap_nodes, "no insufficient-evidence nodes: this test would be vacuous"
    scored = {n["id"] for n in adapted_oracle["nodes"]}
    excluded = {n["id"] for n in adapted_oracle["excluded_nodes"]}
    assert source_gap_nodes <= scored | excluded
    assert source_gap_nodes - excluded, "every gap node was excluded — the distinction was lost"


def test_surface_form_endpoints_are_excluded_and_named(adapted_oracle: dict[str, Any]) -> None:
    excluded = [e for e in adapted_oracle["excluded_edges"] if "surface form" in e["excluded_because"]]
    assert len(excluded) == 5
    declared = {n["id"] for n in adapted_oracle["nodes"]}
    for e in excluded:
        assert not ({e["source"], e["target"]} <= declared)


def test_a_non_type_node_is_excluded_and_named(adapted_oracle: dict[str, Any]) -> None:
    excluded = adapted_oracle["excluded_nodes"]
    assert len(excluded) == 1
    assert excluded[0]["id"] == "sl_family_hq9"
    assert "not an ontology type" in excluded[0]["excluded_because"]
    assert excluded[0]["declared_type"].strip().startswith("(")


def test_every_scored_edge_endpoint_is_a_declared_node(adapted_oracle: dict[str, Any]) -> None:
    """The condition the scorer's loader raises on; if it fails, the whole file is unloadable."""
    declared = {n["id"] for n in adapted_oracle["nodes"]}
    for edge in adapted_oracle["edges"]:
        assert edge["source"] in declared and edge["target"] in declared


def test_node_type_annotations_are_decoded(adapted_oracle: dict[str, Any]) -> None:
    for node in adapted_oracle["node_detail"]:
        assert "(" not in node["type"], f"{node['id']}: annotation leaked into the ontology type"
        assert node["declared_type"]


def test_sub_oracle_wrong_schema_raises(raw_sub_oracle: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="expected schema_version"):
        adapt_sub_oracle(dict(raw_sub_oracle) | {"schema_version": "something-else/1.0"})


def test_a_typeless_node_is_excluded_rather_than_scored(raw_sub_oracle: dict[str, Any]) -> None:
    """A node with no usable ontology type cannot be a scoring target — and cannot vanish either."""
    tampered = dict(raw_sub_oracle)
    tampered["nodes"] = list(raw_sub_oracle["nodes"]) + [
        {"node_id": "sl_bogus", "node_type": "(nothing)", "label": "x"}]
    out = adapt_sub_oracle(tampered)
    assert "sl_bogus" not in {n["id"] for n in out["nodes"]}
    assert "sl_bogus" in {n["id"] for n in out["excluded_nodes"]}
    rec = out["reconciliation"]
    assert rec["scored_nodes"] + rec["excluded_nodes"] == rec["source_nodes"]


def test_an_edge_onto_a_dropped_node_is_excluded_not_silently_scored(
    raw_sub_oracle: dict[str, Any],
) -> None:
    """The failure mode the sub-oracle's accounting exists to catch: an edge losing an endpoint.

    An edge whose endpoint was excluded must move to ``excluded_edges``. Were it kept, the scorer's
    loader would raise on the unresolvable endpoint — and if that raise were ever softened, edge recall
    would be measured over an edge no candidate can satisfy.
    """
    tampered = dict(raw_sub_oracle)
    tampered["edges"] = list(raw_sub_oracle["edges"]) + [
        {"predicate": "observed-at", "frm": raw_sub_oracle["nodes"][0]["node_id"],
         "to": "sl_never_declared", "status": "probable"}]
    out = adapt_sub_oracle(tampered)
    added = [e for e in out["excluded_edges"] if e["target"] == "sl_never_declared"]
    assert len(added) == 1
    assert "surface form" in added[0]["excluded_because"]
    assert not any(e["target"] == "sl_never_declared" for e in out["edges"])
    rec = out["reconciliation"]
    assert rec["scored_edges"] + rec["excluded_edges"] == rec["source_edges"]


def test_reconciliation_error_is_the_declared_failure_type() -> None:
    """The adapter's accounting failures are one named type the harness can catch, not bare ValueErrors."""
    assert issubclass(ReconciliationError, ValueError)
