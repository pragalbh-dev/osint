"""Structural validation of **provider-returned tool arguments** against the schema we offered.

Every model-facing seam in this system is a *forced tool call*: we hand the provider one strict schema
and take back its filled arguments. Both live seams used to do that with a bare ``dict(block.input)`` /
``dict(fn_call.args)`` and no check at all — and that is a silent-failure factory, because Python's
container-shaped consumers degrade quietly:

    ``for entry in filled.get("clusters") or []``

If ``clusters`` came back as a **string** rather than a list (a truncated tool call, or a provider that
serialised a structured value as text), that loop iterates *characters*, every ``isinstance(entry, dict)``
guard drops one, and the pass emits nothing — with no exception, no log line and no recorded error. That
is exactly the failure mode this project exists to prevent: an extraction that *found something* becomes
an extraction that "found nothing", and nothing downstream can tell the difference. Measured on a real
recorded run, 2 of 81 forced calls came back this way and destroyed the single best coreference answer
either model produced, while the reliability metric watching those calls reported a perfect score.

**What is checked: the container/scalar boundary, and nothing else.**

* declared ``array``/``object`` (and no scalar alternative), observed scalar → violation
* declared scalar only, observed ``array``/``object`` → violation
* a union that lists both (``["number","string","array"]``, which one real tool schema does) accepts
  either — a union is satisfied by any one of its branches
* ``null`` observed → always fine. Absence is a first-class state in this system ("insufficient
  evidence"), and providers legitimately null out optional fields; flagging it would manufacture errors.
* anything else (a declared ``integer`` filled with ``"7"``, an unknown enum label, a missing required
  field) → **not** our business. Those are *content* mismatches, and the downstream rails already reject
  them one row at a time, visibly and boundedly. Only the container boundary silently turns into
  character iteration, so only the container boundary is enforced here.

That rule is deliberately narrow enough that it cannot fire on a well-formed payload, and general enough
that it closes the whole class — every provider, every pass, at every depth of the schema — rather than
the one site where it was caught.

**What callers do with a violation is a per-seam policy, not this module's business.** The two seams
answer differently, each following the discipline already established there:

* :mod:`chanakya.ingest.client` — one forced call, no conversation to correct in, and the output is
  frozen onto a ``ClaimRecord`` as provenance. It **raises** (:class:`MalformedToolPayload`), exactly as
  it already raises when the forced tool call is missing entirely.
* :mod:`chanakya.agent.tools` — a ReAct loop whose planner already reads ``{"error", "suggestion"}``
  results and adapts. It returns that actionable error, so the model can re-issue the call.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

__all__ = [
    "MalformedToolPayload",
    "Violation",
    "structural_violations",
    "validate_tool_arguments",
    "describe_violations",
]

#: JSON Schema types that hold other values. A scalar arriving in one of these slots (or a container
#: arriving in a scalar slot) is the structural defect this module exists to catch.
CONTAINER_TYPES = frozenset({"array", "object"})


class MalformedToolPayload(RuntimeError):
    """A forced tool call came back in a shape the offered schema does not permit.

    ``RuntimeError`` on purpose: the extraction seam's existing "no forced tool call" failure is a
    ``RuntimeError`` too, so anything already catching that keeps working.
    """

    def __init__(self, message: str, *, tool_name: str = "", provider: str = "",
                 violations: tuple[Violation, ...] = ()) -> None:
        super().__init__(message)
        self.tool_name = tool_name
        self.provider = provider
        self.violations = violations


@dataclass(frozen=True)
class Violation:
    """One place where the returned value's *shape* contradicts the schema we offered."""

    path: str  # dotted/indexed path into the arguments, e.g. "clusters" or "rows[3].sources"
    declared: tuple[str, ...]  # the JSON types the schema allows there
    observed: str  # the JSON type actually returned
    #: Set when a container slot was filled with text that *looks* like JSON. ``True`` when that text
    #: does not parse — the signature of a tool call truncated mid-token (usually a token-budget hit),
    #: which is diagnostically different from a provider that serialised a whole structure as a string.
    truncated: bool = False
    length: int | None = None  # length of the offending string, when observed is a string

    def describe(self) -> str:
        allowed = "|".join(self.declared) or "?"
        out = f"{self.path or '<root>'}: schema declares {allowed}, provider returned {self.observed}"
        if self.length is not None:
            out += f" of length {self.length}"
        if self.truncated:
            out += " — unparseable JSON text, i.e. the tool call was cut off mid-token"
        return out


# ── schema walking ────────────────────────────────────────────────────────────────────────────────
#
# A deliberately small JSON-Schema reader: enough to follow what our two schema producers actually emit
# (pydantic ``model_json_schema()`` with ``$defs``/``$ref``/``anyOf``, and the hand-built dict schemas in
# ``extract.py`` / ``tool_specs.py``). Anything it does not understand it treats as *unconstrained* and
# skips — an unknown schema construct must never be reported as a model failure.


def _resolve(schema: Any, root: dict[str, Any], _seen: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Follow ``$ref`` (local ``#/$defs/...`` only) to the schema it names; cycles resolve to ``{}``."""
    if not isinstance(schema, dict):
        return {}
    ref = schema.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/") or ref in _seen:
        return schema
    node: Any = root
    for part in ref[2:].split("/"):
        if not isinstance(node, dict):
            return {}
        node = node.get(part)
    return _resolve(node, root, _seen | {ref}) if isinstance(node, dict) else {}


def _declared_types(schema: dict[str, Any]) -> tuple[str, ...]:
    """The JSON types this schema node allows, or ``()`` when it constrains nothing we understand."""
    raw = schema.get("type")
    if isinstance(raw, str):
        return (raw,)
    if isinstance(raw, list):
        return tuple(t for t in raw if isinstance(t, str))
    # No explicit ``type`` — infer only from unambiguous structural keywords, never guess.
    if "properties" in schema or "additionalProperties" in schema:
        return ("object",)
    if "items" in schema or "prefixItems" in schema:
        return ("array",)
    return ()


def _observed_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, (list, tuple)):
        return "array"
    if isinstance(value, (str, bytes)):
        return "string"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return type(value).__name__


def _looks_like_unparsed_json(value: Any) -> tuple[bool, int | None]:
    """``(truncated?, length)`` for a string that was handed to a container slot."""
    if not isinstance(value, str):
        return False, None
    stripped = value.strip()
    if stripped[:1] not in ("[", "{"):
        return False, len(value)
    try:
        json.loads(stripped)
    except ValueError:
        return True, len(value)
    return False, len(value)


def _branches(schema: dict[str, Any]) -> list[Any]:
    """The ``anyOf``/``oneOf`` alternatives, if this node is a union."""
    for key in ("anyOf", "oneOf"):
        branch = schema.get(key)
        if isinstance(branch, list) and branch:
            return branch
    return []


def structural_violations(value: Any, schema: Any, *, root: dict[str, Any] | None = None,
                          path: str = "") -> list[Violation]:
    """Every container/scalar contradiction between ``value`` and the schema we offered.

    Returns ``[]`` for a well-formed payload, for ``null`` anywhere, and for any part of the schema that
    declares nothing this reader understands. Recurses through declared ``properties`` and ``items`` so a
    structure serialised as text is caught at whatever depth the provider produced it.
    """
    root = root if root is not None else (schema if isinstance(schema, dict) else {})
    node = _resolve(schema, root)
    if not node:
        return []

    # A union is satisfied if ANY branch is structurally satisfied — that is what ``anyOf`` means, and it
    # is how pydantic spells ``X | None``.
    alternatives = _branches(node)
    if alternatives:
        if any(not structural_violations(value, alt, root=root, path=path) for alt in alternatives):
            return []
        declared = tuple(dict.fromkeys(
            t for alt in alternatives for t in _declared_types(_resolve(alt, root))
        ))
        truncated, length = _looks_like_unparsed_json(value)
        return [Violation(path=path, declared=declared, observed=_observed_type(value),
                          truncated=truncated, length=length)]

    declared = _declared_types(node)
    if not declared:
        return []
    observed = _observed_type(value)
    if observed == "null":
        return []  # absence is a legitimate answer everywhere in this system

    # A union of types is satisfied if the observed shape fits ANY of them. Containers must match
    # exactly (an object is not an array); scalars are accepted as a class, since the *flavour* of a
    # scalar is content, not structure — see this module's docstring.
    allowed_containers = set(declared) & CONTAINER_TYPES
    if observed in CONTAINER_TYPES:
        bad = observed not in allowed_containers
    else:
        bad = not (set(declared) - CONTAINER_TYPES)
    if bad:
        truncated, length = _looks_like_unparsed_json(value)
        return [Violation(path=path, declared=declared, observed=observed,
                          truncated=truncated, length=length)]

    out: list[Violation] = []
    if observed == "object" and isinstance(node.get("properties"), dict):
        for key, sub in node["properties"].items():
            if key in value:
                out += structural_violations(value[key], sub, root=root,
                                             path=f"{path}.{key}" if path else str(key))
    elif observed == "array" and node.get("items") is not None:
        for i, item in enumerate(value):
            out += structural_violations(item, node["items"], root=root, path=f"{path}[{i}]")
    return out


# ── the caller-facing surface ─────────────────────────────────────────────────────────────────────


def describe_violations(violations: tuple[Violation, ...] | list[Violation]) -> str:
    return "; ".join(v.describe() for v in violations)


def validate_tool_arguments(arguments: Any, *, input_schema: dict[str, Any], tool_name: str,
                            provider: str, stop_reason: str | None = None) -> dict[str, Any]:
    """The forced call's filled arguments, or :class:`MalformedToolPayload` — never a coerced shape.

    ``stop_reason`` is the provider's own report of *why* generation ended. A forced tool call that ended
    because the token budget ran out is a **truncated** answer whether or not the fragment it left behind
    happens to parse, so it is rejected on that signal alone — that is the only way to catch a tool call
    cut off between two complete list entries, which is otherwise indistinguishable from a short answer.

    Repair is deliberately not offered. Re-parsing a JSON-ish string back into the shape we asked for
    would turn a provider defect into a plausible-looking extraction, and the extraction seam's rule is
    already that a malformed reply raises rather than being coerced into an empty (or invented) result.
    """
    if not isinstance(arguments, dict):
        raise MalformedToolPayload(
            f"{provider} returned non-object arguments for tool {tool_name!r}: "
            f"{_observed_type(arguments)}",
            tool_name=tool_name, provider=provider,
        )
    if stop_reason and str(stop_reason).lower() in {"max_tokens", "length", "max_output_tokens"}:
        raise MalformedToolPayload(
            f"{provider} truncated the forced tool call {tool_name!r} at the token budget "
            f"(stop_reason={stop_reason!r}); its arguments are an incomplete answer, not a short one. "
            f"Raise the max-tokens budget or narrow the input — do not re-roll the response.",
            tool_name=tool_name, provider=provider,
        )
    violations = tuple(structural_violations(arguments, input_schema))
    if violations:
        raise MalformedToolPayload(
            f"{provider} returned a structurally invalid payload for tool {tool_name!r}: "
            f"{describe_violations(violations)}",
            tool_name=tool_name, provider=provider, violations=violations,
        )
    return arguments
