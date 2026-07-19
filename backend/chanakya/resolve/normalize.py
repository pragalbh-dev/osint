"""Deterministic name normalisation: transliteration rules + tokenisation + fuzzy similarity.

Rule-based only (spine/03 "rule-based normalizer + seeded alias table; no learned model"). The LLM
may *propose* new transliteration rules offline (``propose.py``), never decide a merge. Pure + offline
— safe on the rebuild path (gate G1). Similarity uses ``rapidfuzz``'s **normalized** (0–1) metric so
no ``/100`` literal is needed (gate G6).
"""

from __future__ import annotations

import re

from rapidfuzz.distance import JaroWinkler

# Keep digits + Latin + CJK + Cyrillic + Arabic/Urdu (the primary theatre's script) + Devanagari;
# strip everything else to a space. A name in an unsupported script (or blank) normalises to "" — and
# empty names are treated as NON-matching everywhere (never a merge signal). See aliases.equivalent.
_NON_ALNUM = re.compile("[^0-9a-z一-鿿Ѐ-ӿ؀-ۿऀ-ॿ]+")


def transliterate(text: str, rules: dict[str, str]) -> str:
    """Apply script→latin substitution rules (longest key first, so subphrases win over chars)."""
    out = text
    for src in sorted(rules, key=len, reverse=True):
        if src in out:
            out = out.replace(src, rules[src])
    return out


def normalize(name: str, rules: dict[str, str]) -> str:
    """Canonical comparison form: transliterate → casefold → collapse punctuation to single spaces."""
    t = transliterate(name, rules).casefold()
    return _NON_ALNUM.sub(" ", t).strip()


def tokens(name: str, rules: dict[str, str]) -> list[str]:
    """Normalised tokens of a name (for blocking keys + token-sorted similarity)."""
    n = normalize(name, rules)
    return [t for t in n.split(" ") if t]


def _sorted_form(name: str, rules: dict[str, str]) -> str:
    return " ".join(sorted(tokens(name, rules)))


def name_similarity(a: str, b: str, rules: dict[str, str]) -> float:
    """Token-sorted Jaro–Winkler similarity in [0, 1] (order-independent, offline, deterministic).

    Token-sorting means "Nur Khan Airbase" ≈ "Airbase Nur Khan"; Jaro–Winkler rewards shared prefixes
    so "FD-2000"/"FT-2000" score high (the false-merge trap) while unrelated names score low.
    """
    fa, fb = _sorted_form(a, rules), _sorted_form(b, rules)
    if not fa or not fb:
        return 0.0
    if fa == fb:
        return 1.0
    return float(JaroWinkler.normalized_similarity(fa, fb))
