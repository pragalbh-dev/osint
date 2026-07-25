"""Discovery helpers for the RK-ATOMS (S1) suite — authored from the spec, not from the code.

The S1 spec (``artifacts/plan/01-replumb-implementation-plan.md`` §4 **A1**/**A7** + §7 **RK-ATOMS**,
``artifacts/plan/sessions/RK-ATOMS.md``) fixes the *concepts* the stage must land —

* "The field is added to ``ClaimRecord`` in S1 as **optional, default ``None``**" (§4 A1);
* "``make_referent_id`` lives beside ``make_claim_id`` in ``schemas/ids.py``" (§4 A1);
* "**Discriminators** — emit operator, geography, unit designation, time as **structured claim
  context**" (spine/13 §10, plan §4 A7);
* "``TypeDef.attrs`` moves from a bare ``list[str]`` to structured entries" (session file, item 4)

— but it never fixes the *identifiers*. This suite was written independently of the implementation, so
it **discovers** the implementation's chosen names on the schema surface and then asserts the specified
behaviour. Every discovery miss raises a loud, explanatory failure quoting the spec line it comes from;
none of them can pass for want of a guessed spelling.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from typing import Any, get_args

from pydantic import BaseModel

import chanakya
from chanakya.schemas import ClaimRecord

PKG_ROOT = Path(chanakya.__file__).parent
REPO_ROOT = PKG_ROOT.parents[1]  # backend/chanakya -> repo root


# ── A1: the referent field on ClaimRecord ───────────────────────────────────────────────────────

#: Every plausible spelling of A1's referent field shares this token; the spec never fixes the rest.
REFERENT_TOKEN = "referent"

_A1_QUOTE = (
    "plan §4 A1: 'The field is added to ClaimRecord in S1 as optional, default None "
    "(so extra=\"forbid\" fixtures still load and S1 stays non-breaking)'"
)


def referent_field_name() -> str:
    """The name ``ClaimRecord`` gave A1's referent field. Fails loudly when the field is absent."""
    names = sorted(n for n in ClaimRecord.model_fields if REFERENT_TOKEN in n.lower())
    assert names, (
        f"ClaimRecord declares no referent field ({_A1_QUOTE}). "
        f"Declared fields: {sorted(ClaimRecord.model_fields)}"
    )
    if len(names) == 1:
        return names[0]
    for preferred in ("referent_id", "referent", "referent_atom", "referent_atom_id"):
        if preferred in names:
            return preferred
    raise AssertionError(
        f"ambiguous referent field on ClaimRecord: {names} — S1 adds exactly one ({_A1_QUOTE})"
    )


def referent_of(claim: ClaimRecord) -> Any:
    """Read A1's referent field off a claim."""
    return getattr(claim, referent_field_name())


def constructed_with_referent(claim: ClaimRecord, value: Any) -> ClaimRecord:
    """``claim`` re-validated with the referent field set — exercises real schema validation."""
    return ClaimRecord.model_validate({**claim.model_dump(), referent_field_name(): value})


def referent_ids_module() -> Any:
    from chanakya.schemas import ids as ids_module

    return ids_module


def make_referent_id_fn() -> Any:
    """A1's ``make_referent_id`` constructor. Fails loudly when it is absent."""
    fn = getattr(referent_ids_module(), "make_referent_id", None)
    assert callable(fn), (
        "chanakya.schemas.ids declares no make_referent_id — plan §4 A1: 'make_referent_id lives "
        "beside make_claim_id in schemas/ids.py'. Public names found: "
        f"{sorted(n for n in vars(referent_ids_module()) if not n.startswith('_'))}"
    )
    return fn


def _string_call(fn: Any, tag: str) -> Any:
    """Call ``fn`` filling every required parameter with a distinct kebab-safe string."""
    sig = inspect.signature(fn)
    args: list[str] = []
    kwargs: dict[str, str] = {}
    for i, param in enumerate(sig.parameters.values()):
        if param.default is not inspect.Parameter.empty:
            continue
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        filler = "d01" if i == 0 else f"{tag}{i}"
        if param.kind is param.KEYWORD_ONLY:
            kwargs[param.name] = filler
        else:
            args.append(filler)
    return fn(*args, **kwargs)


def sample_referent(tag: str) -> str:
    """A referent value the implementation's own constructor accepts, when that constructor exists.

    Falls back to a plain opaque string so the dedup tests still run before ``make_referent_id`` lands
    (they must fail on the *behaviour*, not on an unrelated import).
    """
    try:
        fn = make_referent_id_fn()
    except AssertionError:
        return f"ref-{tag}"
    try:
        return str(_string_call(fn, tag))
    except Exception:  # an unguessable signature must not mask the behaviour under test
        return f"ref-{tag}"


# ── A7: the four structured discriminator dimensions ────────────────────────────────────────────

#: Substrings that identify a field as carrying one of A7's four discriminator dimensions. Generous by
#: design — the spec names the *dimensions* (spine/13 §10: "operator, geography, unit designation,
#: time"), never the field names, so a miss here is reported as a naming ambiguity, not a silent pass.
DISCRIMINATOR_DIMENSIONS: dict[str, tuple[str, ...]] = {
    "operator": ("operator", "operated", "service_branch", "branch", "custodian", "force_element",
                 "owner", "operating"),
    "geography": ("geo", "location", "place", "site", "coordinate", "coord", "garrison", "lat", "lon",
                  "province", "district", "region", "country", "toponym"),
    "designation": ("designat", "serial", "hull", "tail", "pennant"),
    "time": ("time", "date", "when", "as_of", "asof", "epoch", "period", "observed_on", "valid_from"),
}

#: Provenance/plumbing fields that must never be counted as a discriminator.
_NON_DISCRIMINATOR_LEAVES = frozenset({"source_quote"})


def _nested_models(annotation: Any) -> list[type[BaseModel]]:
    """Every ``BaseModel`` reachable inside a (possibly optional/generic) annotation."""
    found: list[type[BaseModel]] = []
    stack: list[Any] = [annotation]
    while stack:
        current = stack.pop()
        if isinstance(current, type) and issubclass(current, BaseModel):
            found.append(current)
        stack.extend(get_args(current))
    return found


def reachable_fields(model: type[BaseModel]) -> dict[str, Any]:
    """``"Model.field" -> FieldInfo`` for ``model`` and every nested ``BaseModel`` it declares.

    Recursive so a discriminator carried on a *nested* structured-context model counts exactly as much
    as one declared flat on the mention — the spec asks for structure, not a particular nesting depth.
    """
    out: dict[str, Any] = {}
    seen: set[type[BaseModel]] = set()
    stack: list[type[BaseModel]] = [model]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        for fname, finfo in current.model_fields.items():
            out[f"{current.__name__}.{fname}"] = finfo
            stack.extend(_nested_models(finfo.annotation))
    return out


def dimensions_covered(model: type[BaseModel]) -> dict[str, list[str]]:
    """Which of A7's four dimensions ``model`` declares a structured field for, and where."""
    hits: dict[str, list[str]] = {dim: [] for dim in DISCRIMINATOR_DIMENSIONS}
    for qualified in reachable_fields(model):
        leaf = qualified.rsplit(".", 1)[1].lower()
        if leaf in _NON_DISCRIMINATOR_LEAVES:
            continue
        for dim, tokens in DISCRIMINATOR_DIMENSIONS.items():
            if any(token in leaf for token in tokens):
                hits[dim].append(qualified)
    return hits


# ── structured TypeDef.attrs (A7's config half) ─────────────────────────────────────────────────

def attr_names(typedef: Any) -> list[str]:
    """The attribute *names* a ``TypeDef`` declares, from either the bare-string or structured form.

    Prefers an accessor the implementation may expose; otherwise reads each entry's name. A structured
    entry with no recoverable name is a failure: nothing downstream could read the vocabulary.
    """
    for accessor in ("attr_names", "attribute_names", "attrs_names", "attribute_vocabulary"):
        fn = getattr(typedef, accessor, None)
        if callable(fn):
            return [str(n) for n in fn()]
    out: list[str] = []
    for entry in typedef.attrs:
        if isinstance(entry, str):
            out.append(entry)
        elif isinstance(entry, dict):
            assert "name" in entry, (
                f"structured attrs entry {entry!r} exposes no attribute name — the per-type attribute "
                "vocabulary would be unreadable (session file item 4)"
            )
            out.append(str(entry["name"]))
        else:
            name = getattr(entry, "name", None)
            assert isinstance(name, str), (
                f"structured attrs entry {entry!r} exposes no `.name` — the per-type attribute "
                "vocabulary would be unreadable (session file item 4)"
            )
            out.append(name)
    return out


# ── static call-site scanning (G17) ─────────────────────────────────────────────────────────────

def _callee_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def py_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts)


def call_sites(func_name: str, *, root: Path | None = None) -> list[str]:
    """``"relative/path.py:lineno"`` for every syntactic call to ``func_name`` under ``root``.

    AST-based on purpose: a text grep would count the many docstring mentions of ``make_claim_id`` and
    turn the gate into noise (or, worse, into a gate that always "finds" a violation).
    """
    base = root or PKG_ROOT
    hits: list[str] = []
    for path in py_files(base):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover — a broken source file is its own failure elsewhere
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node.func) == func_name:
                hits.append(f"{path.relative_to(base)}:{node.lineno}")
    return sorted(hits)


def callees_in_function(path: Path, func_name: str) -> set[str]:
    """Every callee name appearing syntactically inside ``func_name``'s body in ``path``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return {
                name
                for inner in ast.walk(node)
                if isinstance(inner, ast.Call) and (name := _callee_name(inner.func)) is not None
            }
    raise AssertionError(f"{path.name} declares no function {func_name!r}")
