"""DEFAULT-ON P1 — **no staging switch survives.** There is no configuration in which identity is off.

Authored from the session spec alone, implementation-blind. The property, quoted:

    "NO STAGING SWITCH SURVIVES. There is no configuration in which the identity machinery is off. Write
    the test that fails if an on/off staging flag for these stages still exists or can be honoured.
    Distinguish a legitimate TUNABLE (a threshold/cap value in config) from a staging switch — tunables
    must remain."

and the standing directive it implements:

    "it must be DEFAULT ON. No backward compatibility — do not add an 'or' branch, a dual path, a
    migration shim, or a compatibility mode."

**Why this is a safety property and not tidiness.** The two staging flags were measured to make the
shipped, flag-OFF deployment *strictly less safe* than the flag-on one — `rconfig`'s own header records it:
flag-off ran S3's coreference *authorisation* with none of S3's caps, walls or document-scoping. A stage
flag that gates the restraints is an anti-safety device, and the only version of that argument that cannot
regress is the one where the flag does not exist.

**Tunable vs staging switch — the rule this file uses, stated so it can be argued with.** Inside the two
stage blocks a *tunable* carries a **value** an operator chooses between (a band name, a grade letter, a
predicate list, a vocabulary, a normalisation map). A **boolean** in one of those blocks carries no value:
it can only mean "run this stage or do not", which is exactly the thing that must stop existing. So the
partition is by *type*, not by spelling — a renamed flag (`active`, `dual_run`, `staged`) is caught by the
same rule, and every declared threshold/cap/list is required to survive by the second half of the same
assertion (a flag deletion that took the ceilings with it must fail too).

**Four independent surfaces, because a flag can hide in any of them:** the shipped config *files*, the
compiled config *objects*, the *code* that reads them, and — the only one that is authoritative —
**behaviour**. A test that only checked the YAML would pass over a hard-coded `if not enabled: return`.

**Fixture-only, deliberately (ruling M4).** The corpus holds one numbered formation and zero coreference
annotations, so these fixtures are abstract on purpose. Principle #4: logic correctness must never depend
on a stale-corpus test.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

import pytest
import yaml

from chanakya.ontology import LayerRouting
from chanakya.resolve.rconfig import EarnedIdentity, ResolveConfig
from tests import _rk_coref as rc
from tests import _rk_layer as rk

#: The two stage blocks, by the names the shipped files use. Read from the *files* rather than a snapshot,
#: because this is a claim about what the repository ships and must stay checkable while the suite is being
#: run against the ``--earned-identity=on`` shadow deployment (which redirects ``settings.config_dir``).
ONTOLOGY_BLOCK = "layer_routing"
RESOLUTION_BLOCK = "earned_identity"

#: Tunables the stage blocks MUST still declare after the flag dies. Deleting a ceiling along with the flag
#: is the opposite failure and it is asserted in the same test, so neither correction can hide the other.
#: (``site_type_vocabulary`` / ``absent_bucket`` are C1's closed vocabulary + its fail-safe third state.)
REQUIRED_ONTOLOGY_TUNABLES = (
    "presence_type", "design_link_edge", "provisional_prefix", "count_attrs",
    "site_type_vocabulary", "absent_bucket",
)
REQUIRED_RESOLUTION_TUNABLES = (
    "authoritative_categories", "bind_min_grade", "equivalence_markers",
    "name_ceiling", "colocation_ceiling", "contrast_ceiling",
    "formation_types", "presence_types", "colocation_predicates", "formation_discriminators",
    "wall_predicates", "wall_scope_attr", "value_normalization", "normalization_required_attrs",
)


def _yaml(name: str) -> dict[str, Any]:
    """A shipped config file as raw YAML, read from the repo — never through the redirectable config dir."""
    path = Path(rk.REPO_ROOT) / "config" / name
    assert path.is_file(), f"config/{name} is missing; this gate reads the shipped files directly"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _block(file: str, key: str) -> dict[str, Any]:
    block = _yaml(file).get(key)
    assert isinstance(block, dict), (
        f"config/{file} declares no '{key}' block. The flag is meant to be deleted; the block that holds "
        f"the stage's ceilings, vocabularies and walls is meant to STAY (a tunable is not a switch)."
    )
    return block


def _switches(block: dict[str, Any], prefix: str) -> dict[str, Any]:
    """Every boolean-valued key in a stage block — i.e. every key that can only mean 'run this or not'."""
    return {f"{prefix}.{k}": v for k, v in block.items() if isinstance(v, bool)}


# ── surface 1: the shipped config files ─────────────────────────────────────────────────────────

def test_neither_stage_block_declares_an_enablement_switch() -> None:
    """The config half of P1, in both directions at once.

    First half: no boolean survives in either stage block — a boolean there is a staging switch by
    construction (it names no value an operator could choose between).

    Second half: every tunable the stage adds is still declared. Asserted here rather than in a separate
    test on purpose: "delete the flag" and "keep the dials" are one change, and splitting them lets an
    over-correction (deleting the whole block) satisfy the first while silently disabling the mechanism a
    different way — the block absent compiles to every field empty, which is inertness under another name.
    """
    ontology, resolution = _block("ontology.yaml", ONTOLOGY_BLOCK), _block("resolution.yaml", RESOLUTION_BLOCK)
    switches = {**_switches(ontology, ONTOLOGY_BLOCK), **_switches(resolution, RESOLUTION_BLOCK)}

    assert not switches, (
        f"the shipped config still declares an on/off staging switch for the identity stages: {switches}. "
        "There must be NO configuration in which the identity machinery is off — the flag-off deployment "
        "was measured STRICTLY LESS SAFE than the flag-on one (it ran the coreference authorisation with "
        "none of the caps, walls or document-scoping that bound it), so 'shipped off' is not a cautious "
        "default, it is the unsafe one. Delete the key; do not add a second key that re-enables it."
    )
    missing = (
        [k for k in REQUIRED_ONTOLOGY_TUNABLES if k not in ontology]
        + [k for k in REQUIRED_RESOLUTION_TUNABLES if k not in resolution]
    )
    assert not missing, (
        f"the stage blocks no longer declare {missing}. Deleting the flag must not take the TUNABLES with "
        "it: a ceiling, a grade floor, a predicate list and a closed vocabulary are values an operator "
        "chooses, and an absent block compiles to every field empty — which switches the stage off by "
        "omission instead of by a flag (gate G6: thresholds live in config, never in code)."
    )


# ── surface 2: the compiled config objects ──────────────────────────────────────────────────────

_SWITCH_FIELD_TOKENS = ("enable", "disabl", "active", "dual_run", "dualrun", "staged", "staging", "flag")


@pytest.mark.parametrize(
    "compiled", [EarnedIdentity, LayerRouting], ids=["earned_identity", "layer_routing"]
)
def test_no_compiled_stage_config_carries_an_enablement_field(compiled: type) -> None:
    """A deleted YAML key means nothing while the reader still *defaults* it.

    ``EarnedIdentity.enabled: bool = False`` and ``LayerRouting.enabled: bool = False`` are the shim that
    would survive a config-only edit: remove the key and every consumer's ``if not …enabled`` early-returns
    exactly as before, silently and everywhere. A default-off field is a compatibility mode with no
    config entry, which the directive forbids by name.
    """
    fields = {
        name: getattr(compiled, "__annotations__", {}).get(name)
        for name in getattr(compiled, "__annotations__", {})
        if any(tok in name.lower() for tok in _SWITCH_FIELD_TOKENS)
    }

    assert not fields, (
        f"{compiled.__name__} still declares the enablement field(s) {sorted(fields)}. Deleting the config "
        "key without deleting the field leaves the switch fully operative at its OFF default — every "
        "consumer that tests it keeps its dual path, and 'default on' becomes 'off unless someone writes "
        "the key back'. No backward compatibility: the field goes with the key."
    )


# ── surface 3: the code that reads them ─────────────────────────────────────────────────────────

#: Attribute names that read as an enablement test. Exact, so ``entailment_judge_enabled`` (a genuinely
#: separate ASK feature, out of scope here) is not swept up.
_SWITCH_ATTRS = frozenset({"enabled", "enable", "disabled", "is_enabled", "active"})
#: Receiver name fragments that mark such a read as belonging to one of the two identity stages.
_STAGE_RECEIVERS = ("earned", "routing", "layer", "identity", "coref")
#: The one accessor whose whole purpose was to be the flag test ("so the boundary is read from one place").
_FLAG_ACCESSOR = "earned_identity_on"
#: Class names that own a stage block.
_STAGE_CLASSES = ("earnedidentity", "layerrouting")
#: Parameter names that thread a stage switch into a callee as an argument.
_SWITCH_PARAMS = frozenset({"layer_routing", "earned_identity", "earned_on", "routing_enabled"})
#: Config keys that are switches by another name: a boolean an operator can set to reopen the path.
_SWITCH_KEY_LITERALS = frozenset({"enabled", "require_earned_identity"})


def _dotted(expr: ast.expr) -> str:
    if isinstance(expr, ast.Name):
        return expr.id
    if isinstance(expr, ast.Attribute):
        return f"{_dotted(expr.value)}.{expr.attr}"
    if isinstance(expr, ast.Call):
        return _dotted(expr.func)
    if isinstance(expr, ast.Subscript):
        return _dotted(expr.value)
    return type(expr).__name__


def _stage_switch_reads() -> dict[str, list[str]]:
    """``what -> ["module.py:lineno", …]`` for every surviving stage-switch declaration, read or thread."""
    root = Path(rk.PKG_ROOT)
    hits: dict[str, list[str]] = {}

    def note(what: str, path: Path, node: ast.AST) -> None:
        hits.setdefault(what, []).append(f"{path.relative_to(root)}:{getattr(node, 'lineno', 0)}")

    for path in sorted(root.rglob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        stage_module = RESOLUTION_BLOCK in source or ONTOLOGY_BLOCK in source
        for node in ast.walk(tree):
            # a) `<stage thing>.enabled`
            if isinstance(node, ast.Attribute):
                if node.attr == _FLAG_ACCESSOR:
                    note(f"read {_FLAG_ACCESSOR}", path, node)
                elif node.attr in _SWITCH_ATTRS:
                    recv = _dotted(node.value).lower()
                    if any(tok in recv for tok in _STAGE_RECEIVERS):
                        note(f"read {_dotted(node.value)}.{node.attr}", path, node)
            # b) the field declaration + `self.enabled` inside the owning class
            elif isinstance(node, ast.ClassDef) and any(t in node.name.lower() for t in _STAGE_CLASSES):
                for sub in ast.walk(node):
                    if isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                        if sub.target.id.lower() in _SWITCH_ATTRS:
                            note(f"field {node.name}.{sub.target.id}", path, sub)
                    elif isinstance(sub, ast.Attribute) and sub.attr in _SWITCH_ATTRS:
                        note(f"read {node.name}.self.{sub.attr}", path, sub)
            # c) a switch threaded in as a parameter
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = node.args
                for arg in [*args.posonlyargs, *args.args, *args.kwonlyargs]:
                    if arg.arg in _SWITCH_PARAMS or arg.arg.lower() in _SWITCH_ATTRS:
                        note(f"param {node.name}({arg.arg}=…)", path, arg)
            # d) the raw key literal, in a module that owns a stage block
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if node.value in _SWITCH_KEY_LITERALS and (stage_module or node.value != "enabled"):
                    note(f"key literal {node.value!r}", path, node)
    return {k: sorted(v) for k, v in hits.items()}


def test_no_module_gates_identity_behaviour_on_a_stage_switch() -> None:
    """The code half. A flag deleted from config but still *read* is the worst of the three states.

    Scans every ``chanakya`` module for the four shapes a surviving switch can take: a read of
    ``<stage>.enabled`` / ``earned_identity_on``, the field declaration on the block's own dataclass, a
    boolean threaded into a callee as a ``layer_routing=`` argument, and the raw key literal in a module
    that owns a stage block. ``require_earned_identity`` is included by name: a boolean an operator can set
    to ``false`` to reopen the fabrication path is a staging switch under a longer name, and if it is *not*
    honoured then it is a validated no-op (P7) — either way it may not survive.

    Naming-tolerant, and it reports every hit with a file:line, so a rename is a readable failure rather
    than a silent pass.
    """
    hits = _stage_switch_reads()

    assert not hits, (
        "the identity machinery is still gated on a stage switch:\n  "
        + "\n  ".join(f"{what} @ {where}" for what, where in sorted(hits.items()))
        + "\nEvery one of these is a dual path. The directive is explicit: no 'or' branch, no dual path, "
        "no migration shim, no compatibility mode — the machinery is unconditional. Where a mechanism "
        "genuinely needs a value, read the value (a ceiling, a predicate list, a grade floor); never a "
        "boolean that decides whether the mechanism runs at all."
    )


# ── surface 4: behaviour — the only authoritative one ───────────────────────────────────────────

#: One name, two stated origin countries, joined by an in-document coreference link. The pair only exists
#: as a candidate BECAUSE of the coref link (namespace is a blocking key, so the two sit in different
#: blocks), which is why the fixture states all three conditions.
_ORG = "Alpha Precision Machinery"
_QUOTE = f"{_ORG}, also known as {_ORG}, per the register"


def _cross_country() -> list:
    return [
        rc.ent("org_cn", "trading_org", _ORG, doc="d1", attrs={"origin_country": "China"}),
        rc.ent("org_pk", "trading_org", _ORG, doc="d1", sid="mid", attrs={"origin_country": "Pakistan"}),
        rc.coref("org_cn", "org_pk", quote=_QUOTE, doc="d1"),
    ]


def _colocated_formations() -> list:
    """Two formation mentions sharing design + operator + one site, and nothing unit-level (D-13.14/G16)."""
    descriptor = "air defence battery"
    return [
        rc.ent("unit_a", "unit", descriptor, doc="d1"),
        rc.ent("unit_b", "unit", descriptor, doc="d2", sid="mid"),
        rc.site("site", "Alpha Cantonment", doc="d1"),
        rc.rel("r-ba-a", "unit_a", "based-at", "site", doc="d1", iso="2021-03-01"),
        rc.rel("r-ba-b", "unit_b", "based-at", "site", doc="d2", iso="2021-03-05", sid="mid"),
        *rc.shared_neighbours("unit_a", "unit_b"),
    ]


def _with_block(**block: Any):
    """The shipped bundle with the resolution stage block replaced wholesale (``None`` ⇒ block absent)."""
    base = rc.bundle(flag_on=False)
    shipped = rc.earned_identity_block()
    return rc.with_resolution(base, earned_identity=({**shipped, **block} if block else None))


#: Every way a deployment can *try* to switch the stage off. All four must behave identically, because a
#: mechanism that is on by default is on in all of them.
OFF_SPELLINGS: dict[str, Any] = {
    "shipped-as-is": {},                    # whatever config/ ships today
    "enabled-false": {"enabled": False},
    "enabled-zero": {"enabled": 0},
    "enabled-null": {"enabled": None},
}


@pytest.mark.parametrize("spelling", sorted(OFF_SPELLINGS))
def test_no_configuration_switches_the_cross_operator_wall_off(spelling: str) -> None:
    """The behavioural half, on the class that most damages an operator-scoped order of battle.

    Two same-named organisations stating two different origin countries may not fuse — *whatever* the
    config says. This refusal reads no list, no ceiling and no vocabulary; it is a property of the pair, so
    there is nothing for a configuration to legitimately turn off.
    """
    cfg = _with_block(**OFF_SPELLINGS[spelling])
    part = rc.part_of(_cross_country(), cfg)

    assert not rc.fused(part, "org_cn", "org_pk"), (
        f"with the stage 'switched off' as {spelling!r}, a China-stated and a Pakistan-stated organisation "
        f"of the same name FUSED into one entity (status={rc.status(part, 'org_cn', 'org_pk')!r}). This is "
        "the costliest over-merge for an operator-scoped ORBAT — it silently moves an asset from one army "
        "to another — and it must not be reachable from any configuration."
    )


def test_the_stage_block_being_absent_entirely_does_not_switch_it_off() -> None:
    """The fifth spelling, kept separate because it is the one an over-correction produces.

    A flag deletion that leaves consumers reading an *absent* block gets inertness for free: every
    compiled field is empty and every mechanism that consults one becomes a no-op. So the refusals that
    are properties of the PAIR (type, namespace) must hold with no stage config at all.
    """
    part = rc.part_of(_cross_country(), _with_block())  # no kwargs ⇒ block replaced with None

    assert not rc.fused(part, "org_cn", "org_pk"), (
        "with the stage block absent entirely, the cross-operator pair fused. An absent block must not be "
        "a way of switching the machinery off: a refusal that is a property of the pair (different "
        "namespaces, different types) cannot be conditional on config being present."
    )


@pytest.mark.parametrize("spelling", ["enabled-false", "enabled-zero", "enabled-null", "shipped-as-is"])
def test_no_configuration_switches_the_co_location_cap_off(spelling: str) -> None:
    """The second behavioural probe, on the cap that is *anti-fabrication machinery* rather than hygiene.

    Fusing two co-located batteries makes their two sites one unit's before-and-after; the supersede path
    then draws a relocation nobody reported and pops the pair off the analyst's desk. The cap that stops
    that reads its ceiling from config — a value — but whether it runs may not be configurable.
    """
    cfg = _with_block(**OFF_SPELLINGS[spelling])
    part = rc.part_of(_colocated_formations(), cfg)

    assert not rc.fused(part, "unit_a", "unit_b"), (
        f"with the stage 'switched off' as {spelling!r}, two formation mentions sharing a base, a design "
        "and an operator — and nothing unit-level — were CONFIRMED as one unit. Every battery at a base "
        "shares exactly that evidence, so this is an order-of-battle undercount by construction, and it is "
        "the first link of the fabricated-relocation chain (D-13.14/G16)."
    )


def test_the_coreference_producer_rides_no_stage_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """The INGEST half: the coreference PRODUCER must not be dormant on the shipped configuration.

    ``config/credibility.yaml`` declares and populates the producer block (its ``categories`` list is the
    operator's real switch), yet the pass returned ``[]`` unless a *second*, unrelated flag in
    ``resolution.yaml`` was also on. That is the dual path in its purest form: the block a reader edits is
    not the block that decides. With the stage unconditional, the producer runs whenever its own block
    authorises a category — and the shipped block authorises three.
    """
    from chanakya.config.store import ConfigStore
    from chanakya.ingest import adapters, coref, loaders
    from chanakya.ingest.client import ScriptedExtractionClient
    from chanakya.ingest.extract import extract_document
    from chanakya.schemas.claim import Triple
    from chanakya.settings import config_dir

    monkeypatch.setattr(adapters, "_default_geocoder", lambda: None)  # offline determinism (G10)
    text = (
        "China Precision Machinery Import-Export Corporation (CPMIEC) signed the contract.\n"
        "The export agency delivered the battery to Rahwali in March.\n"
    )
    fill = {"manufacturers": [
        {"name": "China Precision Machinery Import-Export Corporation",
         "source_quote": "China Precision Machinery Import-Export Corporation (CPMIEC)"},
        {"name": "CPMIEC", "source_quote": "(CPMIEC)"},
    ]}
    clusters = {"clusters": [{
        "member_ids": [1, 2], "evidence": coref.EXPLICIT_EQUIVALENCE,
        "licensing_quotes": ["China Precision Machinery Import-Export Corporation (CPMIEC)"],
    }]}
    config = ConfigStore.seed_from(config_dir()).snapshot()
    producer = getattr(config.credibility, "coreference", None)
    assert isinstance(producer, dict) and producer.get("categories"), (
        f"config/credibility.yaml declares no coreference producer categories ({producer!r}); this test "
        "asserts the pass is live on the SHIPPED config, so it needs the shipped block to authorise one"
    )

    claims = extract_document(
        loaders.load_document(text, file="t.txt"), source_id="d01", source_type="analytic",
        config=config, client=ScriptedExtractionClient([fill, clusters]), format_hint="prose_claim",
    )
    emitted = [
        c for c in claims
        if isinstance(c.payload, Triple) and c.payload.predicate == coref.COREF_PREDICATE
    ]

    assert emitted, (
        "extraction emitted no coreference claim on the SHIPPED configuration, although "
        f"credibility.coreference authorises {producer.get('categories')}. The producer was dormant behind "
        "resolution.earned_identity.enabled — a second switch in a different file — so the block an "
        "operator edits was not the block that decided. With the stage unconditional the producer's own "
        "categories list is the only switch, and an empty list is the honest way to say 'emit nothing'."
    )


def test_the_stage_flag_pin_used_by_the_test_harness_no_longer_resolves() -> None:
    """The harness's own flag-flip hook is a staging switch too, and it must stop having a target.

    ``tests/conftest.py`` implements ``--earned-identity=on`` by rewriting ``earned_identity: … enabled:
    false`` in a shadow copy of ``config/``. That hook exists only to measure a flag-on run against a
    flag-off default; with no default to differ from it is dead scaffolding, and while it still finds its
    target the flag demonstrably still exists.
    """
    resolution = (Path(rk.REPO_ROOT) / "config" / "resolution.yaml").read_text(encoding="utf-8")

    assert "enabled: false" not in resolution, (
        "config/resolution.yaml still contains 'enabled: false' — the exact string tests/conftest.py's "
        "--earned-identity=on hook rewrites. While that pin resolves, the suite can still be run in two "
        "modes, which is the dual path expressed as test infrastructure: delete the key AND the hook."
    )


def test_the_earned_identity_reader_exposes_no_flag_accessor() -> None:
    """``ResolveConfig`` must no longer publish "the one flag test, so the boundary is read from one place".

    A single, well-named accessor is exactly what makes a dual path cheap to keep: every new mechanism
    reaches for it because it is there. Once identity is unconditional there is no boundary to read.
    """
    accessors = [n for n in dir(ResolveConfig) if not n.startswith("_") and n == _FLAG_ACCESSOR]

    assert not accessors, (
        f"ResolveConfig still exposes {accessors} — the flag test as a public API. Every mechanism S3 added "
        "consulted it, and leaving it in place invites the next one to do the same. Delete the accessor "
        "with the field; the ceilings, floors and lists stay."
    )
