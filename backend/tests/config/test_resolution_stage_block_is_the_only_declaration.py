"""One dial, one name, one place — the shipped ``config/resolution.yaml`` must not shadow its own stage block.

The RK-COREF (S3) review measured what a second copy costs. The three identity ceilings were declared
**twice**: ``name_ceiling`` / ``colocation_ceiling`` / ``contrast_band_ceiling`` at the top level and
``name_ceiling`` / ``colocation_ceiling`` / ``contrast_ceiling`` inside ``earned_identity``. The reader
consulted the top-level copy first, so setting all three to ``confirmed`` in the stage block — the block
whose own header promises to hold every threshold, cap and floor the stage adds — changed nothing at all.
A reader editing the documented location was editing the copy that does not run.

That is worse than an undocumented knob, because it is a knob that *answers*. So this file asserts the
structural property rather than the three names: **no key declared inside the stage block may also be
declared at the top level**, whichever way a future author adds one. It is deliberately blind to which
location wins — a shadow declaration is a defect even when the two copies happen to agree today, since
agreement is exactly what makes the divergence silent when it arrives.

Corpus-independent: reads only the shipped config schema, like its siblings in this directory.
"""

from __future__ import annotations

from chanakya.config.store import ConfigStore
from chanakya.resolve.rconfig import EarnedIdentity, ResolveConfig
from chanakya.settings import config_dir

#: The stage block's key in the resolution config.
STAGE_BLOCK = "earned_identity"

#: Keys the stage block reads from the TOP level by design, so a top-level declaration is not a shadow.
#: ``merge_weights`` carries the two ``attribute`` sub-signal weights beside the four scored terms, and
#: ``containment_min_descriptor_len`` is ruling M1's "one threshold for one idea" — the stage reuses the
#: shipped containment knob rather than declaring a second one for the same question.
DELIBERATELY_SHARED = frozenset({"merge_weights", "containment_min_descriptor_len"})


def _resolution():
    return ConfigStore.seed_from(config_dir()).snapshot().resolution


def test_no_stage_block_key_is_also_declared_at_the_top_level() -> None:
    """The structural rule. A key means one thing in one place, or it means nothing reliable anywhere."""
    resolution = _resolution()
    block = getattr(resolution, STAGE_BLOCK, None) or {}
    assert block, f"config/resolution.yaml declares no `{STAGE_BLOCK}` block — the stage flag has no home"

    top_level = set(resolution.model_dump()) - {STAGE_BLOCK}
    shadowed = sorted((set(block) & top_level) - DELIBERATELY_SHARED)

    assert not shadowed, (
        f"these keys are declared BOTH inside `{STAGE_BLOCK}` and at the top level of "
        f"config/resolution.yaml: {shadowed}. One of the two copies is dead, and a reader has no way to "
        "tell which — that is how setting all three identity ceilings to `confirmed` in the stage block "
        "became a measured silent no-op. Delete one copy (keep the stage block's, which is what "
        "`EarnedIdentity.from_resolution` reads) rather than keeping them in sync by hand."
    )


def test_the_three_ceilings_are_declared_exactly_once_and_in_the_block_the_code_reads() -> None:
    """The specific case that motivated the rule, pinned by name — including the renamed third one.

    ``contrast_band_ceiling`` was the top-level spelling of ``contrast_ceiling``. Two names for one dial is
    the same defect wearing a disguise: a grep for the stage block's name does not find the live copy.
    """
    resolution = _resolution()
    block = getattr(resolution, STAGE_BLOCK, None) or {}
    top_level = resolution.model_dump()

    for retired in ("name_ceiling", "colocation_ceiling", "contrast_ceiling", "contrast_band_ceiling"):
        assert retired not in top_level, (
            f"`{retired}` is declared at the top level of config/resolution.yaml. The identity ceilings are "
            f"read from `{STAGE_BLOCK}` only; a top-level copy is either dead config or a silent override."
        )

    for name in ("name_ceiling", "colocation_ceiling", "contrast_ceiling"):
        assert block.get(name), f"`{STAGE_BLOCK}.{name}` is unset — the ceiling it declares cannot fire"


def test_editing_the_stage_block_actually_moves_the_ceilings() -> None:
    """The behavioural half: the documented location must be the effective one.

    Asserted through ``ResolveConfig`` rather than by reading the file, because the defect was never in the
    file — both copies were present and correct. It was in which one the reader consulted.
    """
    bundle = ConfigStore.seed_from(config_dir()).snapshot()
    edited = {**(getattr(bundle.resolution, STAGE_BLOCK, None) or {}),
              "name_ceiling": "confirmed", "colocation_ceiling": "confirmed",
              "contrast_ceiling": "confirmed"}
    resolution = bundle.resolution.model_copy(update={STAGE_BLOCK: edited})
    earned: EarnedIdentity = ResolveConfig.from_bundle(
        bundle.model_copy(update={"resolution": resolution})
    ).earned_identity

    got = (earned.name_ceiling, earned.colocation_ceiling, earned.contrast_ceiling)
    assert got == ("confirmed", "confirmed", "confirmed"), (
        f"editing all three ceilings in the `{STAGE_BLOCK}` block produced {got} — the block a reader is "
        "told holds every cap is not the block the reader consults. That was a real, measured no-op."
    )
