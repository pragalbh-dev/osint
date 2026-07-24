"""Deterministic string machinery: normalization, Jaro-Winkler, rarity (IDF).

**No embeddings** (locked project decision). Everything here is alias/rarity +
string similarity + lexical term weighting — the sanctioned signal set.

Two notes on reuse:

* ``normalize`` / ``tokens`` / ``sorted_form`` / ``name_similarity`` mirror
  ``backend/chanakya/resolve/normalize.py`` (transliterate -> casefold -> collapse
  non-alnum -> token-sort -> Jaro-Winkler; empty side => 0.0; identical
  sorted-form => 1.0). In production that file is reusable **as-is**; it is
  re-implemented here only because it imports ``rapidfuzz``
  (``resolve/normalize.py:13``) and this prototype must run with nothing
  installed. The Jaro-Winkler below is the reference algorithm, so it agrees with
  ``rapidfuzz.distance.JaroWinkler.normalized_similarity`` on the same inputs.

* ``Rarity`` is **new code**: there is no rarity-/IDF-weighted name scoring
  anywhere in ``backend/chanakya`` (verified by grep), yet D-13.2 and D-13.10 both
  rest on "name contributes a *rarity-graded* score". This is the smallest honest
  implementation of that claim.
"""

from __future__ import annotations

import math
import re

_NON_ALNUM = re.compile(r"[^0-9a-z一-鿿Ѐ-ӿ؀-ۿऀ-ॿ]+")


def transliterate(text: str, rules: dict[str, str]) -> str:
    out = text
    for src in sorted(rules, key=len, reverse=True):
        if src in out:
            out = out.replace(src, rules[src])
    return out


def normalize(name: str, rules: dict[str, str] | None = None) -> str:
    t = transliterate(name, rules or {}).casefold()
    return _NON_ALNUM.sub(" ", t).strip()


def tokens(name: str, rules: dict[str, str] | None = None) -> list[str]:
    return [t for t in normalize(name, rules).split(" ") if t]


def sorted_form(name: str, rules: dict[str, str] | None = None) -> str:
    return " ".join(sorted(tokens(name, rules)))


def _jaro(a: str, b: str) -> float:
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    if la == 0 or lb == 0:
        return 0.0
    window = max(0, max(la, lb) // 2 - 1)
    fa = [False] * la
    fb = [False] * lb
    matches = 0
    for i in range(la):
        lo = max(0, i - window)
        hi = min(i + window + 1, lb)
        for j in range(lo, hi):
            if fb[j] or a[i] != b[j]:
                continue
            fa[i] = fb[j] = True
            matches += 1
            break
    if matches == 0:
        return 0.0
    k = 0
    transpositions = 0
    for i in range(la):
        if not fa[i]:
            continue
        while not fb[k]:
            k += 1
        if a[i] != b[k]:
            transpositions += 1
        k += 1
    transpositions //= 2
    return (matches / la + matches / lb + (matches - transpositions) / matches) / 3.0


def jaro_winkler(a: str, b: str, scale: float, cap: int) -> float:
    j = _jaro(a, b)
    if j == 0.0:
        return 0.0
    prefix = 0
    for x, y in zip(a, b):
        if x != y:
            break
        prefix += 1
        if prefix == cap:
            break
    return j + prefix * scale * (1.0 - j)


def name_similarity(a: str, b: str, rules: dict[str, str], scale: float, cap: int) -> float:
    fa, fb = sorted_form(a, rules), sorted_form(b, rules)
    if not fa or not fb:
        return 0.0
    if fa == fb:
        return 1.0
    return jaro_winkler(fa, fb, scale, cap)


class Rarity:
    """IDF over the token inventory of the *case currently being judged*.

    Scoped to the case on purpose: a corpus-blind hand must not import a
    frequency table derived from data it has not seen, and an in-case table is
    self-contained and deterministic. The consequence — that rarity is measured
    against a small denominator — is listed in the README's "not modelled".
    """

    def __init__(self, docs: list[list[str]], smoothing: float) -> None:
        self.n = len(docs)
        self.smoothing = smoothing
        self.df: dict[str, int] = {}
        for toks in docs:
            for tok in set(toks):
                self.df[tok] = self.df.get(tok, 0) + 1

    def weight(self, token: str) -> float:
        s = self.smoothing
        return math.log((self.n + s) / (self.df.get(token, 0) + s)) + 1.0

    def dice(self, a: list[str], b: list[str]) -> float:
        """Rarity-weighted Dice overlap of two token lists (the BM25-style
        term-weighting core: rare tokens carry the match, common ones do not)."""
        sa, sb = set(a), set(b)
        if not sa or not sb:
            return 0.0
        shared = sum(self.weight(t) for t in sorted(sa & sb))
        total = sum(self.weight(t) for t in sorted(sa)) + sum(self.weight(t) for t in sorted(sb))
        if total <= 0.0:
            return 0.0
        return 2.0 * shared / total
