"""G17 (RK-ATOMS portion) — **atoms are minted only at ingest, never inside ``rebuild()``.**

The bi-level graph rests on one asymmetry: the evidence layer is *minted* (once, at ingest, append-only)
and the knowledge layer is *derived* (recomputed from scratch on every rebuild, spine/13 §8). If any code
reachable from ``rebuild()`` could mint a claim or referent atom, the evidence layer would become a
function of the derived view — provenance would depend on when you last rebuilt, node ids keyed on atom
membership (A5, S4) would drift for reasons no source explains, and a decision keyed on an atom (A6) could
find its atom re-minted underneath it. So the mint functions must be callable from **ingest only**.

Two independent statements, plus a proof the scanner bites:

1. **Every mint call site lives under ``chanakya/ingest/``** — a whole-package scan, so a mint added in
   ``resolve/`` or ``credibility/`` fails here even if nobody notices it is rebuild-reachable.
2. **No rebuild-reachable module contains a mint call** — the import closure of the module that defines
   ``rebuild()``. This is the clause that states the architecture directly rather than by proxy.
3. **The frozen-bundle reader does not mint.** ``ingest.seed`` is *both* the recorder (which legitimately
   mints, through dedup) and the keyless boot reader. The reader replays frozen bundles verbatim via
   ``model_validate``; minting there would overwrite an atom the bundle already froze — silently breaking
   KEYLESS ≡ LIVE and, once referents exist, discarding a recorded coreference grouping.

The scan is **static and input-independent**, which is deliberate: the plan flags that a fixture-driven
version of this gate passes vacuously whenever the fixture happens not to exercise the offending branch.
A static scan cannot be dodged by an unexercised path — and :func:`test_the_scanner_detects_a_violation`
pins that it is not vacuous in the other direction either, by running the same detector over source that
*does* mint and requiring it to fire.

Scope note: G17's *no-``store.append``-under-rebuild* clause belongs to RK-LAYER (S2) and its
*node-ids-derive-from-atom-membership* clause to RK-NAMECUT (S4); neither is asserted here.
"""

from __future__ import annotations

import ast
from collections import deque
from pathlib import Path

from tests.gates._srcscan import PKG_ROOT

#: The atom constructors. ``schemas.ids`` *defines* these; nothing outside ``chanakya/ingest/`` may *call*
#: them. ``make_referent_id`` has no call site at all yet (referents are minted in S3) — it is listed now
#: so the constraint is already in force when S3 wires it up.
MINT_FUNCTIONS = frozenset({"make_claim_id", "make_referent_id"})

#: The module that defines ``rebuild()`` — the root of the "under rebuild" import closure.
REBUILD_MODULE = "chanakya.view.pipeline"

#: The one subpackage allowed to mint.
INGEST_DIR = PKG_ROOT / "ingest"

#: Where the constructors are *defined*. One constructor composing another (``make_referent_id`` building
#: its stem with ``make_claim_id``, so the two id schemes share one normalisation rule and cannot drift) is
#: not a mint — nobody gets an atom out of it. That composition is exempt, and *only* it: the exemption is
#: scoped to this file **and** to calls lexically inside a mint constructor's own body, so a mint smuggled
#: into any other function here is still caught.
IDS_MODULE = PKG_ROOT / "schemas" / "ids.py"


# ── the detector ─────────────────────────────────────────────────────────────────────────────────

def mint_calls(
    source: str, *, names: frozenset[str] = MINT_FUNCTIONS, exempt_constructor_bodies: bool = False
) -> list[tuple[int, str]]:
    """Every ``(lineno, func_name)`` where ``source`` *calls* one of ``names``.

    Calls only — a ``def``/``import`` of a mint function is not a mint. Both the bare (``make_claim_id(…)``)
    and attribute (``ids.make_claim_id(…)``) call forms are matched, so an import style cannot hide one.
    ``exempt_constructor_bodies`` drops calls made *inside* a mint constructor's own body (see
    :data:`IDS_MODULE`).
    """
    tree = ast.parse(source)
    exempt: set[int] = set()
    if exempt_constructor_bodies:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
                exempt |= {id(inner) for inner in ast.walk(node) if isinstance(inner, ast.Call)}
    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or id(node) in exempt:
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else None
        if name in names:
            hits.append((node.lineno, name))
    return hits


def _mint_calls_in(path: Path) -> list[tuple[int, str]]:
    """:func:`mint_calls` over a package file, applying the :data:`IDS_MODULE` exemption."""
    return mint_calls(path.read_text(), exempt_constructor_bodies=path == IDS_MODULE)


def _module_path(module: str) -> Path | None:
    """The file backing a ``chanakya.*`` module name, or ``None`` if it names something else (a symbol)."""
    if module != "chanakya" and not module.startswith("chanakya."):
        return None
    base = PKG_ROOT.joinpath(*module.split(".")[1:])
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


def _intra_package_imports(module: str, path: Path) -> set[str]:
    """The ``chanakya.*`` module names ``path`` imports, resolving relative imports against ``module``."""
    package = module if path.name == "__init__.py" else module.rsplit(".", 1)[0]
    out: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names if a.name.startswith("chanakya"))
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".")
                base = ".".join(parts[: len(parts) - (node.level - 1)])
                target = f"{base}.{node.module}" if node.module else base
            elif node.module and node.module.startswith("chanakya"):
                target = node.module
            else:
                continue
            out.add(target)
            out.update(f"{target}.{a.name}" for a in node.names)  # `from x import y` where y is a module
    return out


def rebuild_reachable_modules() -> dict[str, Path]:
    """Transitive intra-package import closure of :data:`REBUILD_MODULE` — "the code under ``rebuild()``"."""
    seen: dict[str, Path] = {}
    queue = deque([REBUILD_MODULE])
    while queue:
        module = queue.popleft()
        if module in seen:
            continue
        path = _module_path(module)
        if path is None:  # an imported *symbol*, not a module
            continue
        seen[module] = path
        queue.extend(_intra_package_imports(module, path))
    return seen


# ── the gate ─────────────────────────────────────────────────────────────────────────────────────

def test_every_mint_call_site_is_under_ingest() -> None:
    offenders: list[str] = []
    for path in sorted(PKG_ROOT.rglob("*.py")):
        if INGEST_DIR in path.parents:
            continue
        offenders += [
            f"{path.relative_to(PKG_ROOT)}:{line} calls {name}()"
            for line, name in _mint_calls_in(path)
        ]
    assert not offenders, (
        "atoms may only be minted under chanakya/ingest/ (G17) — found: " + "; ".join(offenders)
    )


def test_no_rebuild_reachable_module_mints_an_atom() -> None:
    reachable = rebuild_reachable_modules()
    assert REBUILD_MODULE in reachable, "the closure must at least contain the module defining rebuild()"
    offenders = [
        f"{module}:{line} calls {name}()"
        for module, path in sorted(reachable.items())
        for line, name in _mint_calls_in(path)
    ]
    assert not offenders, (
        "rebuild() must never mint an atom — the evidence layer would become a function of the derived "
        "view (G17). Found: " + "; ".join(offenders)
    )


def test_the_frozen_bundle_reader_does_not_mint() -> None:
    """``seed`` records *and* replays; only the recorder may mint (KEYLESS ≡ LIVE)."""
    tree = ast.parse((PKG_ROOT / "ingest" / "seed.py").read_text())
    readers = {"ingest_bundle", "seed_store_from_bundles"}
    found = {
        node.name: node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in readers
    }
    assert set(found) == readers, f"expected the bundle readers {sorted(readers)}, found {sorted(found)}"
    for name, node in sorted(found.items()):
        hits = mint_calls(ast.unparse(node))
        assert not hits, (
            f"seed.{name} replays frozen bundles verbatim and must not mint (G17) — minting would "
            f"overwrite an atom the bundle already froze. Found: {hits}"
        )


def test_the_scanner_detects_a_violation() -> None:
    """Non-vacuity: the detector must fire on source that *does* mint, in every call form.

    A gate that cannot fail is a gate that lies, so this pins the detector itself rather than trusting
    that a clean scan means a clean codebase.
    """
    violating = (
        "from chanakya.schemas import make_claim_id\n"
        "from chanakya.schemas import ids\n"
        "def _assemble(view):\n"
        "    a = make_claim_id('d99', 'derived')\n"
        "    b = ids.make_referent_id('d99', 'c1')\n"
        "    return a, b\n"
    )
    assert mint_calls(violating) == [(4, "make_claim_id"), (5, "make_referent_id")]
    # …and a definition / import of a mint function is *not* a mint call (no false positive).
    assert mint_calls("from chanakya.schemas import make_claim_id\ndef make_claim_id(d, l): return d\n") == []
    # The IDS_MODULE exemption is scoped: a constructor composing a constructor is exempt, a mint anywhere
    # else in the same file is not.
    composed = "def make_referent_id(d, c):\n    return 'ref:' + make_claim_id(d, c)\n"
    smuggled = composed + "def helper(d):\n    return make_claim_id(d, 'x')\n"
    assert mint_calls(composed, exempt_constructor_bodies=True) == []
    assert mint_calls(smuggled, exempt_constructor_bodies=True) == [(4, "make_claim_id")]


def test_the_reachable_closure_is_not_trivially_small() -> None:
    """Non-vacuity for the closure walk: a broken import resolver would silently shrink it to nothing.

    Asserted as *shape*, not a tuned count: the rebuild path must reach the modules that actually do the
    derivation, so if the walker regresses the two clauses above stop covering anything.
    """
    reachable = rebuild_reachable_modules()
    for expected in ("chanakya.resolve.cluster", "chanakya.credibility.status", "chanakya.schemas.ids"):
        assert expected in reachable, f"{expected} should be rebuild-reachable — the closure walk regressed"
