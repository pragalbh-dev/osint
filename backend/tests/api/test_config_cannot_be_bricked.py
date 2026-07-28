"""A bad ``POST /config/{section}`` is rejected CLEANLY and leaves the running system untouched.

The failure mode this closes is new, and it is a hot-config regression rather than a validation nicety. The
load-time validators added with the identity re-key (a band ceiling outside the vocabulary, a retired stage
marker on an attribute role, a bad time role) raise when a reader **compiles** a section into its runtime
form — which happens inside ``rebuild()``. The route committed the section first and rebuilt second, with only
the commit inside its ``try``, so an invalid section:

1. was written to the LIVE config store,
2. returned an unhandled 500, and
3. made every subsequent config write **and** every rebuild 500 as well, because they all re-compile the same
   bad section — hot config bricked until someone happened to POST a valid section back.

That inverts the one contract this route exists to keep ("nothing a user does in-app requires a restart"), and
it fails silently in the worst direction: the operator's last action appears to have been rejected while it has
in fact been installed.

The properties asserted here are about the *system after the rejection*, not about the error code alone: the
version, the section content and the served view must all be exactly what they were, and the very next write
must succeed.
"""

from __future__ import annotations

import copy

import pytest

from chanakya.api.state import AppState

#: Three sections × three genuinely-invalid-but-well-formed payloads, one per load-time validator. Each is
#: valid YAML and valid pydantic; each is rejected only by a reader that compiles the section.
INVALID_RESOLUTION = (
    pytest.param(
        {"earned_identity": {"name_ceiling": "probably"}},
        id="ceiling-outside-the-vocabulary",
    ),
    pytest.param(
        {"attribute_roles": {"unit": {"service_branch": {"role": "critical", "perishable": True}}}},
        id="retired-boolean-perishable-key",
    ),
    pytest.param(
        {"attribute_roles": {"unit": {"service_branch": {"role": "critical", "time_role": "eternal"}}}},
        id="unknown-time-role",
    ),
    pytest.param(
        {"attribute_roles": {"unit": {"service_branch": {"role": "critical", "taxonomic": "yes"}}}},
        id="non-boolean-taxonomic",
    ),
    pytest.param(
        {"earned_identity": {"enabled": True}},
        id="retired-stage-switch",
    ),
)


def _resolution_payload(state: AppState, overrides: dict) -> dict:
    """The live resolution section with ``overrides`` merged in — a realistic read-modify-write."""
    value = state.config.snapshot().resolution.model_dump(mode="json")
    merged = copy.deepcopy(value)
    for key, patch in overrides.items():
        if isinstance(patch, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **patch}
        else:
            merged[key] = patch
    return merged


@pytest.mark.parametrize("overrides", INVALID_RESOLUTION)
def test_an_invalid_section_is_rejected_and_never_committed(
    golden_client, golden_state: AppState, overrides: dict
) -> None:
    """422, and the live store still holds the OLD section at the OLD version."""
    before_version = golden_state.config.version
    before_section = golden_state.config.snapshot().resolution.model_dump(mode="json")

    response = golden_client.post(
        "/config/resolution", json={"section": "resolution", "value": _resolution_payload(golden_state, overrides)}
    )

    assert response.status_code == 422, (
        f"an invalid resolution section returned {response.status_code}, not a clean rejection. A 500 here "
        "means the section was committed before it was validated."
    )
    assert golden_state.config.version == before_version, (
        "the rejected write still bumped the config version — a client's optimistic-concurrency token is now "
        "stale because of a write that did not happen."
    )
    assert golden_state.config.snapshot().resolution.model_dump(mode="json") == before_section, (
        "the rejected section was COMMITTED to the live store: the operator was told 'invalid' and the "
        "invalid value is what the system is now running."
    )


@pytest.mark.parametrize("overrides", INVALID_RESOLUTION)
def test_the_running_system_still_serves_and_still_accepts_writes(
    golden_client, golden_state: AppState, overrides: dict
) -> None:
    """The half that matters most: after the rejection, config is still HOT.

    A bricked store made ``/view``, ``/health`` and every later write 500 — a restart-only recovery, which is
    the thing the hot-config rule forbids outright.
    """
    golden_client.post(
        "/config/resolution", json={"section": "resolution", "value": _resolution_payload(golden_state, overrides)}
    )

    assert golden_client.get("/health").status_code == 200, "the app is no longer healthy after a bad POST"
    assert golden_client.get("/view").status_code == 200, "the served view died with the bad POST"

    good = golden_state.config.snapshot().credibility.model_dump(mode="json")
    again = golden_client.post("/config/credibility", json={"section": "credibility", "value": good})
    assert again.status_code == 200, (
        f"the next (valid) config write returned {again.status_code} — hot config is bricked, and only a "
        "restart clears it."
    )


def test_a_valid_write_still_commits_and_rebuilds(golden_client, golden_state: AppState) -> None:
    """The mirror: validating before committing must not stop a good write from taking effect live."""
    before = golden_state.config.version
    value = golden_state.config.snapshot().resolution.model_dump(mode="json")

    response = golden_client.post("/config/resolution", json={"section": "resolution", "value": value})

    assert response.status_code == 200
    assert response.json()["version"] > before
    assert golden_client.get("/health").json()["config_version"] == response.json()["version"]
