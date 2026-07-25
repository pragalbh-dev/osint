"""G17 (RK-ATOMS half) — **atoms are minted only at ingest**, and the referent mint is **dormant in S1**.

Spec (``artifacts/plan/01-replumb-implementation-plan.md`` §5, G17): "Atoms are minted only at ingest and
never inside ``rebuild()``"; §7 RK-ATOMS: "**Gates:** G17 — RK-ATOMS authors the *atoms-minted-only-at-
ingest* portion; the no-mint/no-append-under-``rebuild()`` clause is RK-LAYER's (§7) and the id-from-atoms
clause is S4's (A5)."

So this gate asserts exactly S1's portion, and deliberately **not** S2's or S4's:
  * both atom constructors live in ``schemas/ids.py`` and are called **only from the ingest package**;
  * ``make_referent_id`` **exists** (A1) and is **called nowhere** — "add ``make_referent_id`` … **but do
    not invoke it** — referents are minted in S3" (§7 item 2);
  * the mint stays deterministic and offline (a random/clock-derived atom would break pure recompute);
  * ``seed.py``-as-bundle-reader does **not** mint — §7 item 5: "seed reads frozen bundles via
    ``model_validate`` — minting there would overwrite a frozen referent and break KEYLESS≡LIVE."

**Non-vacuity.** A gate that cannot fail is a gate that lies (§5a). The static scan is therefore
self-checked twice: it must *find* the real mint sites (so a broken scanner cannot pass by finding
nothing), and it must *flag a planted violation* written to ``tmp_path``.
"""

from __future__ import annotations

import json

from chanakya.ingest.seed import ingest_bundle
from chanakya.schemas import ClaimRecord, DocRef, Triple
from tests import _rk_atoms as rk
from tests.gates._srcscan import PKG_ROOT, imported_modules

_CLAIM_MINT = "make_claim_id"
_REFERENT_MINT = "make_referent_id"

#: The only package allowed to mint an atom — ingest is the append-only log's write side.
_MINT_PACKAGE = "ingest"

#: ``schemas/ids.py`` defines the constructors; a *definition* is not a mint site.
_IDS_MODULE = PKG_ROOT / "schemas" / "ids.py"


# ── the referent constructor exists (A1) ─────────────────────────────────────────────────────────

def test_make_referent_id_exists_beside_make_claim_id() -> None:
    """A1: "``make_referent_id`` lives beside ``make_claim_id`` in ``schemas/ids.py``"."""
    fn = rk.make_referent_id_fn()

    assert fn.__module__ == "chanakya.schemas.ids", (
        f"make_referent_id is defined in {fn.__module__} — A1 places it beside make_claim_id in "
        "chanakya/schemas/ids.py (G17)"
    )


def test_the_referent_mint_is_deterministic() -> None:
    """Two calls with the same input must agree — an atom minted from an RNG breaks pure recompute (G2)."""
    rk.make_referent_id_fn()  # must exist: otherwise ``sample_referent`` falls back and this is vacuous
    first, second = rk.sample_referent("det"), rk.sample_referent("det")

    assert first == second, "make_referent_id is not deterministic for identical input (G17/G2)"
    assert isinstance(first, str) and first, "a referent atom must be a non-empty opaque string"


def test_the_id_constructors_are_rng_and_clock_free() -> None:
    """``schemas/ids.py`` is documented "pure and offline"; a UUID4 / timestamped atom would not be.

    Asserted statically rather than by call, because the point is that the *module* has no such capability
    — an atom minted from a clock or an RNG is not reproducible, and a frozen bundle would drift on every
    re-extract (KEYLESS ≡ LIVE).
    """
    forbidden = {"random", "uuid", "secrets", "time", "datetime"}
    modules = {name.split(".")[0] for name in imported_modules(_IDS_MODULE)}

    assert not (modules & forbidden), (
        f"chanakya/schemas/ids.py imports {sorted(modules & forbidden)} — the atom mint must stay "
        "deterministic and offline (G17)"
    )


# ── minted only at ingest ────────────────────────────────────────────────────────────────────────

#: The module that DEFINES the id constructors is exempt from the "called only from ingest" rule, because a
#: constructor composing a sibling constructor is **not a mint** — it builds a string and appends nothing.
#: (Orchestrator ruling, 2026-07-25, after this gate flagged it: ``make_referent_id`` composes
#: ``make_claim_id`` so the two schemes share one normalisation rule and cannot drift — good design, not a
#: G17 violation.) The exemption is **earned, not assumed**: ``test_the_exempt_id_module_cannot_mint`` proves
#: the module has no store access, so it is *incapable* of writing an atom. Narrow to the defining module —
#: never widen it to the whole package.
_MINT_DEFINING_MODULE = "schemas/ids.py"


def test_the_claim_atom_mint_is_called_only_from_the_ingest_package() -> None:
    """G17's S1 clause: atoms are minted **only at ingest**."""
    sites = rk.call_sites(_CLAIM_MINT, root=PKG_ROOT)

    assert sites, (
        f"the scanner found no call to {_CLAIM_MINT} anywhere in chanakya/ — the scan is broken, and a "
        "broken scan would pass this gate vacuously (§5a: a gate that cannot fail is a gate that lies)"
    )
    outside = [
        s for s in sites
        if not s.startswith(f"{_MINT_PACKAGE}/") and not s.startswith(_MINT_DEFINING_MODULE)
    ]
    assert not outside, (
        f"{_CLAIM_MINT} is called outside chanakya/{_MINT_PACKAGE}/: {outside} — atoms are minted only at "
        "ingest (G17)"
    )


def test_the_exempt_id_module_cannot_mint() -> None:
    """The exemption above is legitimate only while the id module is incapable of *writing* an atom.

    A mint is a call **plus** an append to the evidence log; the constructor module does the first and must
    never be able to do the second. Asserted on *capability* (no store import), not on behaviour, so the
    exemption cannot quietly become a hole: give ``schemas/ids.py`` store access and this fails.
    """
    modules = imported_modules(_IDS_MODULE)
    store_ish = sorted(m for m in modules if "store" in m or "sqlite" in m)

    assert not store_ish, (
        f"chanakya/{_MINT_DEFINING_MODULE} imports {store_ish} — it is exempt from the mint-site rule only "
        "because it cannot append an atom; with store access that exemption becomes a G17 hole"
    )


def test_the_referent_mint_is_dormant_in_s1() -> None:
    """§7 item 2: "add ``make_referent_id`` … **but do not invoke it** — referents are minted in S3"."""
    rk.make_referent_id_fn()  # the constructor must exist before dormancy means anything
    sites = rk.call_sites(_REFERENT_MINT, root=PKG_ROOT)

    assert not sites, (
        f"{_REFERENT_MINT} is invoked at {sites} — S1 lands the constructor dormant; minting referents is "
        "S3's, and minting one now would freeze a grouping at the wrong grain (G17)"
    )


def test_the_mint_scanner_flags_a_planted_violation(tmp_path) -> None:
    """The negative control that makes the two scans above non-vacuous."""
    (tmp_path / "innocent.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "offender.py").write_text(
        "from chanakya.schemas import make_claim_id\n"
        "def f():\n"
        "    return make_claim_id('d01', 'l1')\n",
        encoding="utf-8",
    )
    (tmp_path / "attribute_offender.py").write_text(
        "import chanakya.schemas as s\n"
        "def g():\n"
        "    return s.make_claim_id('d01', 'l1')\n",
        encoding="utf-8",
    )
    (tmp_path / "docstring_only.py").write_text('"""mentions make_claim_id( in prose only."""\n',
                                                encoding="utf-8")

    hits = rk.call_sites(_CLAIM_MINT, root=tmp_path)

    assert hits == ["attribute_offender.py:3", "offender.py:3"], (
        f"the mint scanner is unreliable: {hits} (it must catch both a bare and an attribute call, and "
        "must not fire on a docstring mention)"
    )


# ── the bundle reader must not mint ──────────────────────────────────────────────────────────────

def test_the_bundle_reader_does_not_mint() -> None:
    """§7 item 5: "minting there would overwrite a frozen referent and break KEYLESS≡LIVE"."""
    seed = PKG_ROOT / _MINT_PACKAGE / "seed.py"
    for reader in ("ingest_bundle", "seed_store_from_bundles"):
        callees = rk.callees_in_function(seed, reader)
        offending = callees & {_CLAIM_MINT, _REFERENT_MINT, "assign_claim_ids", "dedup_within_doc"}
        assert not offending, (
            f"seed.{reader} calls {sorted(offending)} — the bundle reader replays frozen atoms verbatim; "
            "re-minting would overwrite a frozen claim id or referent (G17, KEYLESS ≡ LIVE)"
        )


def test_the_bundle_reader_replays_a_frozen_atom_verbatim(tmp_path) -> None:
    """The behavioural half: an id the deterministic pass would never have produced must survive intact."""
    frozen = ClaimRecord(
        claim_id="dfrozen-l9",  # not what assign_claim_ids would mint for this span
        source_id="src-a",
        doc_ref=DocRef(file="d01.txt", span=(0, 10), line=1),
        kind="observation",
        asserts="relationship",
        payload=Triple(subject="hq-9", predicate="based-at", object="site-7"),
    )
    value = rk.sample_referent("frozen")
    raw = rk.constructed_with_referent(frozen, value).model_dump(mode="json")
    path = tmp_path / "d01.json"
    path.write_text(json.dumps([raw]), encoding="utf-8")

    [replayed] = ingest_bundle(path)

    assert replayed.claim_id == "dfrozen-l9", "the bundle reader re-minted a frozen claim atom"
    assert rk.referent_of(replayed) == value, "the bundle reader dropped or overwrote a frozen referent"
