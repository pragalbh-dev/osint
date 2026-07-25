"""S1's headline invariant — **the derived graph is byte-identical after RK-ATOMS**.

Spec (``artifacts/plan/sessions/RK-ATOMS.md``, Goal + Acceptance):

    "Formalize the **claim atom** … and land the **A7 structured-discriminator schema** — with **zero
    behavioural change**. The derived graph must be **byte-identical** after S1."
    "- [ ] **The golden view is byte-identical to pre-S1** (the stage's headline invariant)."

``tests/gates/test_g2_determinism.py`` and ``tests/view/test_rebuild.py`` already assert that a rebuild of
the golden evidence log reproduces ``expected_view.json``. Both of those compare the *rebuild output*
against the *committed fixture* — so they stay green if the fixture is **regenerated** to match changed
behaviour. That is precisely the failure this stage has to exclude: S1 may add schema, and may not move the
graph, so the fixture itself must not be re-recorded.

Hence the content hash below. It is a **deliberate pin, not a checksum ritual**: it is the one assertion
that fails when the golden view is regenerated rather than preserved. It is expected to be updated — with
a ledger entry — by RK-NAMECUT (S4), which regenerates the golden by design (plan §7 RK-NAMECUT).
"""

from __future__ import annotations

import hashlib

from tests.fixtures import loaders

#: md5 of ``backend/tests/fixtures/golden/expected_view.json`` as recorded at the RK-ATOMS baseline
#: (``design/resolution-redesign``, pre-S1). Recorded in ``artifacts/plan/sessions/RK-ATOMS.md``'s
#: kickoff brief alongside the suite baseline "1026 passed, 7 skipped, 1 xfailed".
PRE_S1_EXPECTED_VIEW_MD5 = "bb6f16a516c31eb0846494b62271a601"


def test_golden_view_fixture_is_byte_identical_to_pre_s1() -> None:
    digest = hashlib.md5(loaders.expected_view_json().encode("utf-8")).hexdigest()

    assert digest == PRE_S1_EXPECTED_VIEW_MD5, (
        "expected_view.json changed during S1 — the stage is schema-only and must not move the derived "
        f"graph (got {digest}, want {PRE_S1_EXPECTED_VIEW_MD5}). If a rebuild genuinely no longer matches "
        "the fixture, the bug is in the change, not in the fixture: do NOT re-record the golden here. "
        "Regenerating it is RK-NAMECUT's (S4) job, with a ledger entry."
    )
