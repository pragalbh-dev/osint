"""Gate — no silent no-op keys in a shipped ``materiality_filter`` (AR-3 drift guard).

``ConfigModel`` is ``extra="allow"`` by documented design (``schemas/base.py``) so DATA-C can add knobs
without an F0 amendment — which is exactly why a filter key the code never reads ships silently as a
100%-pass no-op (the AR-3 defect). This gate is the **non-raising** counterpart: it does not touch
config-write validation (that would break hot-config), it just asserts at CI time that every key the
shipped ``config/subjects.yaml`` declares under ``materiality_filter`` is one ``_passes_materiality``
actually consumes. Mirrors ``test_g6_no_magic_numbers.py``: a drift is caught here, not in review.
"""

from __future__ import annotations

import yaml

from chanakya.view.lens import CONSUMED_FILTER_KEYS
from tests.gates._srcscan import REPO_ROOT

# Keys shipped today that the code deliberately does NOT implement and DATA-C is removing
# (tmp/conv/ARCH-to-DATAC-subjects-materiality-filter.md): ``exclude_off_subject`` would wire the grading
# oracle into the runtime (D-P4.9); ``materiality_attrs`` is descriptive prose, not a predicate. Listed
# here so the guard is GREEN today yet still fails on any *new* unrecognised key; delete from this set once
# the subjects.yaml edit lands and the guard tightens automatically.
_PENDING_REMOVAL = {"exclude_off_subject", "materiality_attrs"}

_SUBJECTS_YAML = REPO_ROOT / "config" / "subjects.yaml"


def test_shipped_materiality_filter_keys_are_consumed() -> None:
    if not _SUBJECTS_YAML.exists():
        return  # no shipped config in this env (F0 ships no content) — nothing to guard
    raw = yaml.safe_load(_SUBJECTS_YAML.read_text()) or {}
    known = CONSUMED_FILTER_KEYS | _PENDING_REMOVAL
    offenders: list[str] = []
    for subj in raw.get("subjects", []) or []:
        filt = subj.get("materiality_filter") or {}
        for key in filt:
            if key not in known:
                offenders.append(f"{subj.get('subject_id')}: {key}")
    assert not offenders, (
        "materiality_filter key(s) the runtime never reads (a silent no-op filter) — implement them in "
        "view/lens.py::_passes_materiality or delete from config/subjects.yaml: " + "; ".join(offenders)
    )
