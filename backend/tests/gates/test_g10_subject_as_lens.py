"""G10 — subject = a query-time lens (master §1 #6, §5). No per-subject table/namespace; core
traversal takes the subject config as a param; re-pointing is a config edit, not new code.

Checks: the chanakya package has no bespoke per-subject module; ``apply_lens`` takes a ``SubjectLens``
param; and two different subject configs scope the *same* view differently (proving the subject is a
parameter, not baked in).
"""

from __future__ import annotations

import inspect

from chanakya.schemas import SubjectLens
from chanakya.view import apply_lens
from tests.fixtures import loaders
from tests.gates._srcscan import PKG_ROOT

# The complete architectural subpackage set — nothing subject-specific may appear here.
_ALLOWED_SUBPACKAGES = {
    "schemas", "config", "store", "view", "resolve", "credibility", "sufficiency",
    "materiality", "observe", "agent", "ingest", "hitl", "api",
}


def test_no_bespoke_per_subject_package() -> None:
    subpackages = {p.name for p in PKG_ROOT.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
    extra = subpackages - _ALLOWED_SUBPACKAGES
    assert not extra, f"unexpected subpackage(s) {extra} — a subject must be config, not a bespoke graph (G10)"


def test_apply_lens_takes_subject_as_param() -> None:
    sig = inspect.signature(apply_lens)
    assert "subject" in sig.parameters
    ann = sig.parameters["subject"].annotation
    assert ann in (SubjectLens, "SubjectLens")


def test_re_pointing_is_a_config_edit() -> None:
    view = loaders.golden_view()
    lens_2hop = SubjectLens(subject_id="s2", anchors=["unit_acme"], max_hops=2)
    lens_1hop = SubjectLens(subject_id="s1", anchors=["unit_acme"], max_hops=1)
    two = {n.id for n in apply_lens(view, lens_2hop).nodes}
    one = {n.id for n in apply_lens(view, lens_1hop).nodes}
    # 2 hops reaches the supplier (unit -fields-> comp -supplies- mfr); 1 hop does not.
    assert "mfr_foundry" in two
    assert "mfr_foundry" not in one
    assert one < two  # strictly smaller — pure re-parameterisation, no code change
