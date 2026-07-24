"""Config loading for the RK-SPIKE prototype.

Two jobs, both deliberate:

1. **Zero-dependency YAML.** A restricted YAML dialect (block maps, block
   sequences, flow sequences, scalars) is parsed here in ~120 lines so the
   prototype runs on a clean checkout with nothing installed. PyYAML is *not*
   imported even though the repo depends on it.

2. **Rationales are enforced, not decorative.** The parser attaches the comment
   block immediately above every leaf key to that key's dotted path, and
   ``load()`` refuses to return a config where a leaf key has no rationale. That
   is the project's G6 no-magic-numbers gate expressed as a load-time check
   rather than a convention. A small, named exemption list covers pure data
   tables and analyst prose (see ``RATIONALE_EXEMPT``).

Also here: the machine-checked ``scoring.invariants``. Every float in the config
is pinned by one of those invariants rather than by observed behaviour, so a
later edit that breaks D-13.10's name ceiling fails loudly at load time instead
of quietly at judgement time.
"""

from __future__ import annotations

import os
from typing import Any

# Paths whose leaves are data tables or analyst prose rather than policy knobs.
# A rationale per row would be noise; the *table* carries one at its parent key.
RATIONALE_EXEMPT = (
    "normalization.equivalence_classes",
    "normalization.designator_ordinals",
    "citizens.layer_by_type",
    "citizens.citizen_by_layer",
    "gaps.sentences",
)

# The verdict vocabulary, weakest first. This is the output contract's own
# vocabulary, not a tunable, so it lives in code.
BAND_ORDER = ("separate", "possible", "probable", "confirmed")


class ConfigError(RuntimeError):
    pass


# --------------------------------------------------------------------------
# scalar / flow parsing
# --------------------------------------------------------------------------

def _strip_comment(line: str) -> tuple[str, str | None]:
    """Split a line into (content, comment) honouring quotes."""
    quote = None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            return line[:i], line[i + 1:].strip()
    return line, None


def _split_flow(body: str) -> list[str]:
    """Split a flow-sequence body on top-level commas."""
    out: list[str] = []
    depth = 0
    quote = None
    cur = ""
    for ch in body:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            cur += ch
            continue
        if ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
            continue
        cur += ch
    if cur.strip():
        out.append(cur)
    return out


def _scalar(raw: str) -> Any:
    s = raw.strip()
    if s.startswith("[") and s.endswith("]"):
        return [_scalar(p) for p in _split_flow(s[1:-1])]
    if s.startswith("{") and s.endswith("}"):
        if not s[1:-1].strip():
            return {}
        raise ConfigError(f"non-empty flow mappings are not supported: {s!r}")
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    low = s.lower()
    if low in ("", "null", "~"):
        return None
    if low == "true":
        return True
    if low == "false":
        return False
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def _unquote_key(k: str) -> str:
    k = k.strip()
    if len(k) >= 2 and k[0] == k[-1] and k[0] in "\"'":
        return k[1:-1]
    return k


# --------------------------------------------------------------------------
# the block parser
# --------------------------------------------------------------------------

class _Node:
    __slots__ = ("indent", "text", "rationale")

    def __init__(self, indent: int, text: str, rationale: str) -> None:
        self.indent = indent
        self.text = text
        self.rationale = rationale


def _lex(text: str) -> list[_Node]:
    nodes: list[_Node] = []
    pending: list[str] = []
    for raw in text.splitlines():
        content, comment = _strip_comment(raw)
        if not content.strip():
            if comment:
                pending.append(comment)
            else:
                pending.clear()  # a blank line ends a rationale block
            continue
        indent = len(content) - len(content.lstrip(" "))
        nodes.append(_Node(indent, content.strip(), " ".join(pending).strip()))
        pending.clear()
    return nodes


class _Parser:
    def __init__(self, nodes: list[_Node]) -> None:
        self.nodes = nodes
        self.i = 0
        self.rationales: dict[str, str] = {}

    def parse(self) -> Any:
        return self._block(0, "")

    def _block(self, indent: int, path: str) -> Any:
        if self.i >= len(self.nodes):
            return {}
        if self.nodes[self.i].text.startswith("- "):
            return self._seq(indent, path)
        return self._map(indent, path)

    def _seq(self, indent: int, path: str) -> list[Any]:
        out: list[Any] = []
        while self.i < len(self.nodes):
            node = self.nodes[self.i]
            if node.indent < indent or not node.text.startswith("- "):
                break
            self.i += 1
            out.append(_scalar(node.text[2:]))
        return out

    def _map(self, indent: int, path: str) -> dict[str, Any]:
        out: dict[str, Any] = {}
        while self.i < len(self.nodes):
            node = self.nodes[self.i]
            if node.indent < indent:
                break
            if ":" not in node.text:
                raise ConfigError(f"expected 'key: value', got {node.text!r}")
            key_part, _, value_part = node.text.partition(":")
            key = _unquote_key(key_part)
            here = f"{path}.{key}" if path else key
            self.i += 1
            if value_part.strip():
                out[key] = _scalar(value_part)
                self.rationales[here] = node.rationale
            else:
                child_indent = self.nodes[self.i].indent if self.i < len(self.nodes) else indent
                if child_indent <= node.indent:
                    out[key] = {}
                    self.rationales[here] = node.rationale
                else:
                    out[key] = self._block(child_indent, here)
                    if isinstance(out[key], list):
                        self.rationales[here] = node.rationale
        return out


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def _leaf_paths(node: Any, path: str = "") -> list[str]:
    if isinstance(node, dict) and node:
        out: list[str] = []
        for k in sorted(node):
            out.extend(_leaf_paths(node[k], f"{path}.{k}" if path else k))
        return out
    return [path]


def _check_rationales(cfg: dict, rationales: dict[str, str]) -> None:
    missing = [
        p for p in _leaf_paths(cfg)
        if not p.startswith(RATIONALE_EXEMPT) and not rationales.get(p)
    ]
    if missing:
        raise ConfigError(
            "every config leaf needs a one-line rationale comment above it "
            f"(G6). Missing for: {', '.join(missing)}"
        )


def _check_invariants(cfg: dict) -> None:
    """The floats are pinned by these statements, not by observed behaviour."""
    w = cfg["scoring"]["weights"]
    b = cfg["scoring"]["bands"]
    inv = cfg["scoring"]["invariants"]
    fails = []
    if inv.get("name_alone_below_probable") and not (w["name"] < b["probable_floor"]):
        fails.append(
            f"name_alone_below_probable: name weight {w['name']} must be < "
            f"probable_floor {b['probable_floor']} (D-13.10: a name match may "
            "never reach probable)"
        )
    if inv.get("name_alone_reaches_possible") and not (w["name"] >= b["possible_floor"]):
        fails.append(
            f"name_alone_reaches_possible: name weight {w['name']} must be >= "
            f"possible_floor {b['possible_floor']} (name is a recall channel, "
            "capped not muted)"
        )
    if inv.get("full_discriminator_reaches_probable") and not (
        w["discriminator"] >= b["probable_floor"]
    ):
        fails.append(
            f"full_discriminator_reaches_probable: discriminator weight "
            f"{w['discriminator']} must be >= probable_floor {b['probable_floor']}"
        )
    caps = cfg["caps"]
    if "same_doc_stated_contrast" in caps["lifted_by_composite_unique_id"]:
        fails.append(
            "same_doc_stated_contrast must never be liftable: a stated contrast "
            "is positive anti-identity evidence, not an absence-of-evidence cap"
        )
    if cfg["confirm"].get("name_derived_triggers_allowed"):
        fails.append(
            "name_derived_triggers_allowed must stay false (R3.2: name may buy a "
            "comparison, never the thing a cap withholds)"
        )
    for name in (*caps["lifted_by_composite_unique_id"], "name_alone",
                 "perishable_only", "co_location_formation",
                 "same_doc_stated_contrast"):
        band = caps.get(name)
        if band is not None and band not in BAND_ORDER:
            fails.append(f"caps.{name} must be a band name, got {band!r}")
    if fails:
        raise ConfigError("config invariant violation:\n  - " + "\n  - ".join(fails))


DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "proto-config.yaml")


def load(path: str | None = None) -> dict[str, Any]:
    with open(path or DEFAULT_PATH, encoding="utf-8") as fh:
        text = fh.read()
    parser = _Parser(_lex(text))
    cfg = parser.parse()
    _check_rationales(cfg, parser.rationales)
    _check_invariants(cfg)
    cfg["_rationales"] = parser.rationales
    return cfg


def band_at_most(band: str, ceiling: str | None) -> str:
    """Clamp `band` to `ceiling` using the contract's band order."""
    if ceiling is None:
        return band
    return band if BAND_ORDER.index(band) <= BAND_ORDER.index(ceiling) else ceiling


def lower_band(a: str | None, b: str | None) -> str | None:
    """The more restrictive of two ceilings (None = no ceiling)."""
    if a is None:
        return b
    if b is None:
        return a
    return a if BAND_ORDER.index(a) <= BAND_ORDER.index(b) else b
