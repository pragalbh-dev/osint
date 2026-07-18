"""The effective alias table = **derived state**, never a stored table (spine/03, spine/06).

``effective = seeded aliases (config) ∪ aliases replayed from decision-log merge_adjudication(accept)``.
So "the same pair auto-resolves next time" falls out of *replay* — appending an accept to the decision
log makes that pair alias-equivalent on the next ``rebuild()`` with no HITL. Symmetric merge-adjudication
*reject*/*split* records feed the learned distinct-from set (a do-not-merge that also grows from the log).

An alias equivalence class is the transitive closure of {canonical} ∪ {aliases} ∪ {accepted pairs},
compared on the **normalised** form so transliteration folds in (红旗-9 ≡ Hongqi-9 ≡ HQ-9).
"""

from __future__ import annotations

from chanakya.schemas import DecisionRecord

from .normalize import normalize


class AliasIndex:
    """Normalised-name → equivalence-class-id, plus the learned distinct-from pairs (also normalised)."""

    def __init__(self) -> None:
        self._class_of: dict[str, str] = {}  # normalised name → class root (a normalised name)
        self.distinct: set[frozenset[str]] = set()  # learned do-not-merge {normA, normB}

    def _root(self, key: str) -> str:
        root = key
        while self._class_of.get(root, root) != root:
            root = self._class_of[root]
        return root

    def link(self, a: str, b: str) -> None:
        """Union two normalised names into one alias equivalence class (deterministic root = min)."""
        ra, rb = self._root(a), self._root(b)
        if ra == rb:
            return
        lo, hi = sorted((ra, rb))
        self._class_of[hi] = lo
        self._class_of.setdefault(lo, lo)

    def equivalent(self, a: str, b: str) -> bool:
        """True iff two *normalised* names are in the same alias class via a real alias LINK.

        Deliberately NOT ``a == b``: identical surface strings are handled by the exact-name bootstrap
        rule (which also checks the namespace), and an empty/unknown name is never alias-equivalent to
        anything — otherwise two blank or same-named-but-different-country entities would silently fuse.
        """
        if not a or not b:
            return False
        if a not in self._class_of or b not in self._class_of:
            return False
        return self._root(a) == self._root(b)

    def barred(self, a: str, b: str) -> bool:
        """True if a learned merge_adjudication(reject/split) explicitly separated this pair."""
        return frozenset((a, b)) in self.distinct


def build(
    alias_table: dict[str, list[str]],
    transliteration: dict[str, str],
    decisions: list[DecisionRecord] | None,
) -> AliasIndex:
    """Seed ∪ replayed accepts → an :class:`AliasIndex`. ``reject``/``split`` accepts feed distinct."""
    idx = AliasIndex()

    def norm(s: str) -> str:
        return normalize(s, transliteration)

    # 1. seeded alias table: every alias is equivalent to its canonical.
    for canonical, aliases in alias_table.items():
        c = norm(canonical)
        for alias in aliases:
            idx.link(c, norm(alias))

    # 2. replay decision-log merge adjudications (learning): accept ⇒ equivalence, reject/split ⇒ barred.
    for d in decisions or []:
        if d.type != "merge_adjudication":
            continue
        pair = _pair(d)
        if pair is None:
            continue
        a, b = norm(pair[0]), norm(pair[1])
        if _accepted(d):
            idx.link(a, b)
        elif _separated(d):
            idx.distinct.add(frozenset((a, b)))
    return idx


def _pair(d: DecisionRecord) -> tuple[str, str] | None:
    """Extract the (a, b) name/id pair a merge adjudication concerns, from decision or context."""
    src: dict = d.decision if isinstance(d.decision, dict) else {}
    for key in ("pair", "members", "same_as"):
        val = src.get(key) or d.context.get(key)
        if isinstance(val, (list, tuple)):
            try:
                x, y = val
            except ValueError:
                continue
            return str(x), str(y)
    a, b = src.get("a") or d.context.get("a"), src.get("b") or d.context.get("b")
    if a is not None and b is not None:
        return str(a), str(b)
    return None


def _accepted(d: DecisionRecord) -> bool:
    src = d.decision if isinstance(d.decision, dict) else {"verdict": d.decision}
    verdict = str(src.get("verdict") or src.get("action") or "").casefold()
    return bool(src.get("accept")) or verdict in {"accept", "accepted", "merge", "same"}


def _separated(d: DecisionRecord) -> bool:
    src = d.decision if isinstance(d.decision, dict) else {"verdict": d.decision}
    verdict = str(src.get("verdict") or src.get("action") or "").casefold()
    return src.get("accept") is False or verdict in {"reject", "rejected", "split", "distinct", "separate"}
