"""Stage 2 (D4) — the merge-corroboration ledger: the *merge's own* why.

``merge corroboration, not assertion corroboration`` — a structured account of which independent
identity signals corroborated a merge, derived purely from the stored ``merge_breakdown``. One entry
per signal whose raw value is > 0, in a deterministic signal order. Empty for a degenerate breakdown
(only ``total``), so a caller records it only when there is something to record.
"""

from __future__ import annotations

from chanakya.resolve import identity_ledger


def test_ledger_records_the_corroborating_signals_with_their_values() -> None:
    bd = {
        "attribute": 0.9,
        "relational": 0.1,
        "temporal_consistency": 1.0,
        "source_asserted": 0.0,
        "total": 0.72,
    }
    ledger = identity_ledger(bd)
    # source_asserted (0.0) is excluded; the three that fired are recorded, in signal order.
    assert [e["signal"] for e in ledger] == ["attribute", "relational", "temporal_consistency"]
    assert [e["value"] for e in ledger] == [0.9, 0.1, 1.0]


def test_ledger_is_empty_for_a_degenerate_breakdown() -> None:
    """A breakdown carrying only ``total`` corroborates nothing ⇒ empty ledger (no phantom entries)."""
    assert identity_ledger({"total": 0.91}) == []
    assert identity_ledger({}) == []


def test_ledger_is_deterministic_signal_order_regardless_of_dict_order() -> None:
    bd = {
        "source_asserted": 0.85,
        "temporal_consistency": 1.0,
        "attribute": 0.47,
        "relational": 0.5,
        "total": 0.4,
    }
    assert [e["signal"] for e in identity_ledger(bd)] == [
        "attribute",
        "relational",
        "temporal_consistency",
        "source_asserted",
    ]
