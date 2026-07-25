"""In-document coreference clustering — extraction **pass 2**, the derived overlay
(``tmp/conv/INGEST-RESOLVE-in-document-coreference-clustering-PROPOSAL.md``).

**The leak this closes.** Extraction has one thing RESOLVE will never have: the document's local
discourse context. On one page ``CPMIEC``, ``China Precision Machinery Import-Export Corporation`` and
``the export agency`` can be one actor, and only something reading the prose knows it. RESOLVE is a
context-free attribute scorer over isolated claim strings, so a descriptive or elliptical reference has
no string for it to match — that mention is **orphaned** (today it surfaces as a stray ``unknown`` node
minted from a dangling relation endpoint, ``view.pipeline._assemble``). The signal is free here and
**unrecoverable** downstream.

**Option B — derived overlay, not a physical merge.** Pass 1 is unchanged and every mention stays its own
entity claim, so the atoms remain natively separable. Pass 2 emits, alongside them, an in-document
**coreference cluster**: "these mentions are the same actor — here is the exact text that licenses it."
The merged node is *derived* at rebuild by applying the cluster, so a **split is native** (apply the
cluster to a subset) rather than an un-welding. That matters because RESOLVE is merge-monotonic — it
consolidates and never splits — and in OSINT over-merge is the expensive, adversarially-exploited error
(look-alike names, decoys) while under-merge is cheap and recoverable.

**Why its own predicate.** The cluster rides the append-only evidence log as a relationship claim on a
**dedicated lane** (:data:`COREF_PREDICATE`) rather than as an ordinary ``same-as``. That is load-bearing,
not cosmetic: ``resolve.scoring`` treats ``same-as``/``aka``/… as one *weighted term* of ``merge_score``
(``_IDENTITY_PREDICATES``), so a ``same-as`` here would be silently diluted into a partial score that
attribute-dissimilarity can outvote — i.e. re-deriving, without context, the decision the extractor
already made *with* it. On its own lane the cluster is inert to today's scorer (merge behaviour is
provably unchanged until RESOLVE is reconciled), and the eventual honor policy keys on a signal that
cannot be confused with, or watered down by, ordinary identity scoring.

**Conservative by construction.** Type-restricted, categorical evidence (never a self-reported number),
a verbatim licensing quote required and *checked against the document*, stated ``distinct-from`` pairs as
a hard veto, overlapping clusters dropped, and the model told the cost asymmetry explicitly so it
separates when unsure. Every rail is re-applied deterministically here — the model proposes, this module
disposes. Dormant unless configured; without an extraction key it emits nothing rather than guessing.

**Known limitation (honest).** A "mention" is keyed by its surface form *within one document*, because
pass 1 already collapses same-name mentions per document (``_Emitter._entity_claim_ids``,
``dedup.dedup_within_doc``). So the proposal's per-occurrence mention ids are approximated: one document
using one string for two genuinely different entities ("3rd Battalion" twice) is not separable here. That
is an under-reach, never an over-merge — the two occurrences were already one claim before this pass.

Runs upstream of ``store.append`` (gate G1) and entirely inside one document, so frozen bundles stay
byte-stable and the keyless seed path inherits it unchanged (both paths call ``extract_document``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel

from chanakya import edge_direction
from chanakya.ingest.client import ExtractionClient
from chanakya.ingest.loaders import LoadedDoc
from chanakya.schemas import ClaimRecord, ConfigBundle, make_claim_id
from chanakya.schemas.claim import EntityDescriptor, Extraction, Triple
from chanakya.schemas.ids import make_referent_id
from chanakya.schemas.values import DateValue

# ── the dedicated lane + its tier-3 keys ────────────────────────────────────────────────────────────

#: The relationship predicate in-document coreference is written on. Declared in ``config/ontology.yaml``
#: WITHOUT ``extractor: true`` (the model can never assert it through the ``relations`` slot) and
#: deliberately **absent** from ``resolve.scoring._IDENTITY_PREDICATES`` — see the module docstring.
COREF_PREDICATE = "coref-same-as"

#: Document-local cluster id, so every edge of one cluster is recoverable as a group.
CLUSTER_ATTR = "_coref_cluster"
#: The categorical evidence kind that licensed the grouping (never a numeric confidence).
EVIDENCE_ATTR = "_coref_evidence"
#: A human-readable rendering of the licensing evidence. Reuses the existing provenance key every other
#: claim uses, and stays a STRING so every existing reader keeps working.
QUOTE_ATTR = "source_quote"
#: The licensing evidence itself: the **set of verbatim spans** (ruling M2), each occurring verbatim in the
#: document. This is what a reader — and the resolver's own re-derivation of D-13.17's gate — reads, because
#: the joined display string is not verbatim anything.
QUOTES_ATTR = "_coref_quotes"
#: Separator for the display rendering. Prose, not a threshold (gate G6).
_QUOTE_JOIN = " … "
#: The **referent atom** this link belongs to (``ref:<doc>-<cluster>``, ``schemas.ids.make_referent_id``).
#: One per document-local cluster, minted here (S3) and carried on every member's entity claim as well as on
#: each coref link, so the rebuild can recover the *grouping* — which it may DECLINE (D-13.18) — rather than
#: only the pairs. It is evidence ABOUT a grouping, never an address.
REFERENT_ATTR = "_coref_referent"
#: The two members' verbatim surface forms, in ``[anchor, member]`` order. Load-bearing for the consumer:
#: ``resolve._link_endpoints`` rewrites ``Edge.subject``/``Edge.object`` onto entity ids before
#: ``_coref_pairs`` runs, so without this the resolver cannot re-derive D-13.17's "the quote contains both
#: members' surface forms" gate and would have to take the producer's word for it.
FORMS_ATTR = "_coref_forms"
#: The **per-link** verdict of D-13.17's deterministic gate: ``PASS`` ⇒ this link may be authoritative if its
#: category and its source's grade also allow; ``FAIL`` ⇒ raise-only. Per C5 the gate is evaluated per LINK
#: (anchor→member), not per cluster: a cluster binds only over the links that pass, and each failing link
#: becomes an injected Tier-1 candidate pair — a **partial** bind, which neither discards a well-licensed
#: link nor lets one bad link license the rest.
GATE_ATTR = "_coref_gate"
#: Why the gate reached its verdict, in words — the audit trail for a check the resolver cannot re-run
#: (the anaphor gate needs the document's whole mention inventory, which exists only here).
GATE_DETAIL_ATTR = "_coref_gate_detail"
GATE_PASS = "PASS"
GATE_FAIL = "FAIL"

#: The CONTRASTIVE lane (D-13.19 decision (b)). Deliberately **not** the stated ``distinct-from`` rail: that
#: channel is semantically narrow (an explicit "no interoperability" / "not related") and lands as a hard,
#: transitive, **ungraded** veto — and widening an ungraded transitive veto to "any enumeration" is the worst
#: thing this design could do, because *every ORBAT list contains an enumeration*. On its own lane a
#: same-document syntactic contrast is a **band ceiling**: the pair reaches the analyst with its licensing
#: quote and can never auto-merge. A ceiling cannot shatter an existing cluster; a veto can.
CONTRAST_PREDICATE = "coref-distinct-from"

#: The only evidence kinds a cluster may claim. Anything else is dropped.
EXPLICIT_EQUIVALENCE = "EXPLICIT_EQUIVALENCE"
NAME_VARIANT = "NAME_VARIANT"
UNAMBIGUOUS_ANAPHOR = "UNAMBIGUOUS_ANAPHOR"
EVIDENCE_CATEGORIES: tuple[str, ...] = (EXPLICIT_EQUIVALENCE, NAME_VARIANT, UNAMBIGUOUS_ANAPHOR)

#: Type stamped on a mention the document never declared as an entity (a bare relation endpoint — the
#: descriptive/elliptical reference this pass exists to rescue). It may join a typed cluster; two
#: *differently* typed mentions may never merge.
UNKNOWN_TYPE = "unknown"

#: Stated-identity predicates pass 1 already emits, read here as input signal (not as clusters).
_SAME_AS = "same-as"
_DISTINCT_FROM = "distinct-from"

TOOL_NAME = "cluster_coreferences"


# ── the forced-tool schema ──────────────────────────────────────────────────────────────────────────

class CoreferenceCluster(BaseModel):
    """One group of mentions the document treats as a single entity (multi-member only)."""

    member_ids: list[int] = []
    evidence: str | None = None
    #: **A SET of verbatim spans from this one document** (ruling M2), not a single contiguous span. The
    #: frozen corpus contains equivalences documents genuinely *assert* whose two surface forms sit tens of
    #: lines apart, or in different fields of one record — so no single span can contain both, and a
    #: one-span rule would make the system withhold on equivalences that really are stated. Each span must
    #: still occur verbatim, which is the whole point: any reader can re-derive the bind. Multiple spans make
    #: the evidence *findable*, never *stronger* — the grade floor, the mark-vs-word conjunct and C9's
    #: document-scoping all still apply.
    licensing_quotes: list[str] = []


class CoreferenceContrast(BaseModel):
    """Two mentions this ONE document syntactically **distinguishes** (D-13.19's contrastive channel).

    Optional by design, and absence means ``unknown`` rather than "no contrast": a *required* field would
    push the extractor to invent one. It is not derivable downstream — the mention shape carries no spans
    and pass 1 collapses one name to one claim per document, so nothing later can re-read the syntax.
    """

    left_id: int | None = None
    right_id: int | None = None
    licensing_quote: str | None = None


class CoreferenceClusters(BaseModel):
    """The pass-2 output: only the merges (+ any explicit contrasts). Unnamed mentions stay singletons."""

    clusters: list[CoreferenceCluster] = []
    contrasts: list[CoreferenceContrast] = []


SYSTEM = """\
You decide which of the entity mentions listed below refer to the SAME real-world entity, within this ONE
document. You are not judging the world — only whether this document treats two mentions as the same thing.
You never rename, translate, split, or invent a mention; you only group the ones you are given.

INPUT: the document text, and a numbered list of entity mentions already extracted from it — each with an
id, its entity_type, and the verbatim name/phrase exactly as it appears. You are also given any equivalence
and distinction statements the document made.

TASK: group the mentions into clusters. Every mention belongs to exactly one cluster, and a mention on its
own is a valid cluster — MOST mentions are singletons. Only put two or more mentions in one cluster when the
document gives you positive, quotable evidence that they are the same entity. Only ever cluster mentions of
the SAME entity_type; a mention typed "unknown" is a descriptive reference and may join exactly one typed
cluster when the context leaves no doubt.

MERGE ONLY WHEN one of these holds AND you can quote the exact text that licenses it:
- EXPLICIT_EQUIVALENCE — the document states they are the same: an alias, an apposition, an acronym
  expansion, "also known as", "formerly", or "Full Name (SHORT)".
  e.g. "China Precision Machinery Import-Export Corporation (CPMIEC)".
- NAME_VARIANT — the same proper name in a trivially different surface form: spacing, casing, punctuation,
  or an obvious spelling/transliteration variant of the SAME name (not merely the same family or type).
- UNAMBIGUOUS_ANAPHOR — a back-reference ("the export agency", "the company", "the site", "it") that in
  local context can point to only ONE already-introduced mention: there is no second mention of that type it
  could mean.

NEVER MERGE WHEN:
- Two different proper names with no stated equivalence — even if same family, same role, same country
  (two manufacturers; HQ-9 vs HQ-16; two battalions). Same category is NOT the same entity.
- A descriptor that could refer to more than one introduced mention of that type — leave every such mention
  a singleton; a human will resolve it.
- The document distinguishes them ("not to be confused with", "distinct from", "a separate unit"), or a
  distinction is listed in the input — these MUST stay in different clusters.
- Their stated hard attributes conflict (different origin country, different designator, different
  coordinates). If two mentions look coreferent but an attribute contradicts, do NOT merge — keep them
  separate.

COST RULE — calibrate to this: failing to merge two mentions of the same entity is a SMALL, recoverable
error (a human or a later document can still join them). Merging two DIFFERENT entities is a SERIOUS error
that is hard to undo. When you are not sure, keep them separate.

OUTPUT (fill the tool): report only the clusters with more than one member. For each, give the member
mention-ids, the evidence category (EXPLICIT_EQUIVALENCE / NAME_VARIANT / UNAMBIGUOUS_ANAPHOR), and the
exact verbatim quote(s) from the document that license the grouping. Quote as many spans as it takes: if the
document states the equivalence across two fields or two paragraphs, give BOTH spans rather than paraphrasing
one. Every span must be copied verbatim. If you cannot quote any licensing span, do not report the cluster.
Any mention you do not name stays its own singleton.

ALSO report CONTRASTS: pairs of mentions this document itself sets apart in its own wording — an
enumeration that names both as separate things ("the 8th AD Bn and the separate 12th AD Bn"), a "not to be
confused with", "a second battery", "unlike". Give the two mention ids and the exact verbatim quote. Report
a contrast ONLY where the document's own words do the distinguishing; if the document is merely silent
about whether two mentions are the same, report NOTHING — silence is not a contrast.\
"""


# ── the mention inventory (built from pass 1's own claims — never re-read from the model) ────────────

@dataclass(frozen=True)
class Mention:
    """One clusterable mention: a document-local id, its surface form, its type, and its claim (if any)."""

    local_id: int
    name: str
    entity_type: str
    claim_id: str | None  # None ⇒ a bare relation endpoint the document never declared as an entity


def _endpoints(claim: ClaimRecord, rules: dict[str, Any]) -> list[tuple[str, str]]:
    """The entity-ish endpoints of a relationship claim as ``(name, implied_type)``.

    An endpoint the document never declared still has a type the **ontology** implies: the edge's declared
    domain types its subject and its range types its object (``manufactures`` is manufacturer→variant). That
    matters a lot here — it is what keeps the same-type rail biting on undeclared mentions, which are the
    majority on the real corpus. Without it "CPMIEC" and "HQ-9/P" are both merely ``unknown`` and nothing
    deterministic stops a proposal to merge them. A symmetric/undeclared edge implies nothing (``unknown``);
    an ``object_value`` object is a value, not a node, so it is not an endpoint at all.
    """
    payload = claim.payload
    if not isinstance(payload, Triple):
        return []
    rule = rules.get(payload.predicate)
    subject_type = getattr(rule, "from_type", None) or UNKNOWN_TYPE
    object_type = getattr(rule, "to_type", None) or UNKNOWN_TYPE
    out = [(payload.subject, subject_type)]
    if payload.object_value is None:
        out.append((payload.object, object_type))
    return [(name, etype) for name, etype in out if name]


def inventory(claims: list[ClaimRecord], rules: dict[str, Any] | None = None) -> list[Mention]:
    """Every distinct mention this document offers, in first-appearance order (deterministic).

    Declared entities first-class (typed, with their claim id as the mention id), then any relation
    endpoint the document never declared — the descriptive/elliptical references that are precisely what
    leaks today — typed from the ontology where the edge implies a type. ``rules`` is
    ``edge_direction.direction_map(config)``; omitting it leaves undeclared endpoints ``unknown``.
    Surface-form keyed within the document; see the module docstring's limitation note.
    """
    seen: dict[str, Mention] = {}
    ordered: list[Mention] = []

    def add(name: str, entity_type: str, claim_id: str | None) -> None:
        if name in seen:
            return
        mention = Mention(len(ordered) + 1, name, entity_type, claim_id)
        seen[name] = mention
        ordered.append(mention)

    for claim in claims:
        payload = claim.payload
        if isinstance(payload, EntityDescriptor) and payload.name:
            add(payload.name, payload.entity_type, claim.claim_id)
    for claim in claims:
        if claim.asserts == "relationship":
            for name, entity_type in _endpoints(claim, rules or {}):
                add(name, entity_type, None)
    return ordered


def _stated_pairs(claims: list[ClaimRecord], predicate: str) -> list[tuple[str, str]]:
    """Ordered ``(a, b)`` surface pairs the document itself stated on ``predicate`` (pass 1's own output)."""
    pairs: list[tuple[str, str]] = []
    for claim in claims:
        payload = claim.payload
        if isinstance(payload, Triple) and payload.predicate == predicate:
            if payload.subject and payload.object:
                pairs.append((payload.subject, payload.object))
    return pairs


# ── the prompt ──────────────────────────────────────────────────────────────────────────────────────

def build_prompt(text: str, mentions: list[Mention], equivalences: list[tuple[str, str]],
                 distinctions: list[tuple[str, str]]) -> str:
    """The pass-2 user message: the document, its numbered mentions, and the stated identity signals."""
    lines = [f"{m.local_id}. [{m.entity_type}] {m.name}" for m in mentions]
    parts = [
        "DOCUMENT:",
        text,
        "",
        "MENTIONS (refer to these by id only):",
        "\n".join(lines),
    ]
    if equivalences:
        parts += ["", "THE DOCUMENT STATED THESE ARE THE SAME:",
                  "\n".join(f"- {a} = {b}" for a, b in equivalences)]
    if distinctions:
        parts += ["", "THE DOCUMENT STATED THESE ARE DIFFERENT (never place these in one cluster):",
                  "\n".join(f"- {a} =/= {b}" for a, b in distinctions)]
    return "\n".join(parts)


# ── deterministic guards (the model proposes; these dispose) ─────────────────────────────────────────

def _normalized(text: str) -> str:
    """Whitespace-collapsed text, for checking a quote really occurs in the document."""
    return " ".join(text.split())


def _quote_supported(quote: str, text: str) -> bool:
    """Is the licensing quote actually present in the document? No quotable span ⇒ no merge."""
    return bool(quote.strip()) and _normalized(quote) in _normalized(text)


def supported_spans(raw: Any, text: str) -> list[str]:
    """Every licensing span that occurs **verbatim** in this document, in the order given (ruling M2).

    Accepts a list of spans or a bare string. Each span is checked independently, so one paraphrased span
    does not discard the spans that are genuine — under-reach here is cheap and recoverable, an invented span
    is not. Order-preserving and deduplicated (deterministic).
    """
    values: list[str] = []
    if isinstance(raw, str):
        values = [raw]
    elif isinstance(raw, (list, tuple)):
        values = [v for v in raw if isinstance(v, str)]
    out: list[str] = []
    for span in values:
        if _quote_supported(span, text) and span.strip() not in out:
            out.append(span.strip())
    return out


def _value_tokens(text: str) -> list[str]:
    """Alphanumeric tokens of a surface form, casefolded — a designator's parts, punctuation dropped.

    Local rather than borrowed from ``resolve.normalize`` on purpose: ``ingest`` must not depend on the
    resolver's package for a three-line string split, and the mark-vs-word test below only needs "what are
    the pieces of this name". ``HQ-9/P`` → ``['hq', '9', 'p']``.
    """
    kept = "".join(c.casefold() if c.isalnum() else " " for c in text)
    return kept.split()


def differs_only_by_a_mark(a: str, b: str, min_descriptor_len: int | None) -> bool:
    """Is the longer of two surface forms the shorter plus a **MARK** rather than a WORD? (Ruling M1.)

    **The hole this closes.** A fixture can pass every other conjunct of the structural gate — the span
    occurs verbatim, it contains both surface forms, and it contains a parenthetical marker — while the
    equivalence is **wrong**. The shape is a mark-vs-name collision: ``"<Design> (<Design>/X)"`` reads
    exactly like an alias declaration ("Full Name (SHORT)") but in fact *distinguishes two variants*. Nothing
    downstream reliably saves it: the grade floor cannot (a good source writes exactly that sentence), and
    the D-13.18 decline only fires if the two members happen to carry a conflicting critical discriminator —
    two marks of one design often conflict on nothing at all. And a marker vocabulary built as a token list
    can never catch it, because the marker really is present.

    **The test already exists in config and encodes precisely this distinction** — the containment
    bootstrap's ``containment_min_descriptor_len``: *"HT-233" + "engagement" (a WORD) is the same radar
    described more fully; "HQ-9" + "P" (a MARK) is a different missile.* Reused here rather than duplicated,
    so there is one threshold for one idea (gate G6).

    Returns True — meaning **the equivalence is not licensed** — when the shorter form is a head-anchored
    prefix of the longer and the first token the longer one adds is not a word of at least the configured
    length. Unset knob ⇒ the test cannot run, and it fails **closed**: an ungated conjunct on the strongest
    fusion path in the system would be worse than a missing feature.
    """
    ta, tb = _value_tokens(a), _value_tokens(b)
    if not ta or not tb or ta == tb:
        return False  # identical or empty forms are not a containment relation at all
    short, long_ = (ta, tb) if len(ta) < len(tb) else (tb, ta)
    if len(short) >= len(long_) or long_[: len(short)] != short:
        return False  # not a head-anchored extension ⇒ two genuinely different names, not a mark
    if min_descriptor_len is None:
        return True  # fail CLOSED: unable to test the one thing that separates an alias from a variant
    head = long_[len(short)]
    return not (head.isalpha() and len(head) >= min_descriptor_len)


def _type_compatible(members: list[Mention]) -> bool:
    """Same-type only. ``unknown`` mentions (undeclared endpoints) may join exactly one typed cluster."""
    known = {m.entity_type for m in members if m.entity_type != UNKNOWN_TYPE}
    return len(known) <= 1


def _vetoed(members: list[Mention], distinctions: list[tuple[str, str]]) -> bool:
    """True if the document explicitly separated any pair inside this cluster (a hard veto)."""
    barred = {frozenset((a, b)) for a, b in distinctions}
    names = [m.name for m in members]
    return any(
        frozenset((names[i], names[j])) in barred
        for i in range(len(names)) for j in range(i + 1, len(names))
    )


def valid_clusters(raw: Any, mentions: list[Mention], text: str,
                   distinctions: list[tuple[str, str]],
                   categories: tuple[str, ...] = EVIDENCE_CATEGORIES,
                   ) -> list[tuple[list[Mention], str, list[str]]]:
    """Apply every over-merge rail to the model's proposal → ``(members, evidence, quote)`` triples.

    Dropped: an unknown/!allowed evidence category; a missing quote or one not found in the document; a
    cluster with fewer than two resolvable members; mixed known types; any pair the document explicitly
    distinguished; and any cluster overlapping one already accepted (the partition stays closed — first
    wins, conservatively).

    A cluster of purely *undeclared* mentions is kept: on the real corpus that is the common shape (both
    ``CPMIEC`` and its full expansion reach the graph only as relation endpoints), and it is precisely the
    leak this pass exists to close. :func:`coref_claims` handles the missing premises.
    """
    if not isinstance(raw, dict):
        return []
    by_id = {m.local_id: m for m in mentions}
    accepted: list[tuple[list[Mention], str, list[str]]] = []
    claimed: set[int] = set()

    for entry in raw.get("clusters") or []:
        if not isinstance(entry, dict):
            continue
        evidence = entry.get("evidence")
        if not isinstance(evidence, str) or evidence not in categories:
            continue
        # M2: a SET of verbatim spans from this one document. Each is checked independently, so one
        # paraphrased span never discards the spans that are genuine; zero verbatim spans ⇒ no cluster.
        quotes = supported_spans(entry.get("licensing_quotes"), text)
        if not quotes:
            continue
        ids = entry.get("member_ids")
        if not isinstance(ids, list):
            continue
        members: list[Mention] = []
        for value in ids:
            mention = by_id.get(value) if isinstance(value, int) else None
            if mention is not None and mention not in members:
                members.append(mention)
        if len(members) < 2 or not _type_compatible(members):
            continue
        if _vetoed(members, distinctions):
            continue
        if any(m.local_id in claimed for m in members):
            continue  # overlapping proposals ⇒ keep the first, drop the rest (under-merge is cheap)
        claimed.update(m.local_id for m in members)
        accepted.append((members, evidence, quotes))
    return accepted


# ── D-13.17's per-LINK deterministic gates (C5) ──────────────────────────────────────────────────────
#
# An "authoritative" coref pair is a **Phase-1 bootstrap trigger**: it merges at hardcoded confidence 1.0 and
# BYPASSES BANDING entirely, so no cap restrains it. Authorising a category is therefore authorising an
# uncapped, unbanded fusion on a **model-chosen label** — which is only defensible behind a deterministic,
# code-verified precondition. A model's self-report is not evidence; a self-report plus a structural check is.
#
# The gate is evaluated per LINK (anchor→member) and not per cluster (C5): the ``EXPLICIT_EQUIVALENCE`` rule
# says the quote must contain "both members' surface forms", which is a two-member formulation with no stated
# n-ary quantifier. Per-link conjunction would demote a whole good cluster to n singletons on one bad link;
# per-link disjunction would let one good link license the rest. Per-link **evaluation with a partial bind**
# is strictly better than either.


def _paren_wraps(quote: str, form: str) -> bool:
    """Is ``form`` wrapped in a parenthetical inside ``quote``? — "Full Name (SHORT)", the commonest marker."""
    folded = _normalized(quote).casefold()
    inner = _normalized(form).casefold()
    return any(f"{open_}{inner}{close}" in folded for open_, close in (("(", ")"), ("[", "]"), ("（", "）")))


def explicit_equivalence_gate(
    quotes: list[str], anchor: Mention, member: Mention, markers: tuple[str, ...],
    min_descriptor_len: int | None = None,
) -> tuple[bool, str]:
    """D-13.17's ``EXPLICIT_EQUIVALENCE`` gate — ``(passed, why)``, checkable by any reader.

    **Four** conjuncts, all structural, all re-derivable from what rides the claim:

    1. every licensing span occurs verbatim in the document (enforced upstream by :func:`supported_spans`,
       so it is a precondition here rather than a re-check);
    2. the spans **together** contain both members' surface forms. Ruling M2: the evidence is a *set* of
       spans from one document, not one contiguous span — the corpus contains equivalences documents really
       do assert whose two forms sit tens of lines apart or in different fields of one record, and a
       one-span rule would make the system withhold on those. Multiple spans make the evidence *findable*,
       never *stronger*;
    3. some span carries a **configured equivalence marker** — a term from the declared vocabulary, or a
       parenthetical wrapping one of the two forms. This is what stops the gate collapsing into "the two
       names appear near each other", which is co-occurrence and not equivalence;
    4. **the longer form does not differ from the shorter by only a MARK** (ruling M1,
       :func:`differs_only_by_a_mark`). Conjuncts 1–3 are all satisfiable by a sentence that *distinguishes*
       two variants — ``"<Design> (<Design>/X)"`` reads exactly like an alias declaration — and a marker
       vocabulary built as a token list can never catch that, because the marker genuinely is there.

    Note the deliberate asymmetry with ``NAME_VARIANT``: that category has no gate and is **permanently**
    raise-only, because an authoritative ``NAME_VARIANT`` *is* the exact-normalised-name auto-merge lane
    D-13.1 exists to delete — rebuilt on another predicate and immune to the very cap that replaced it.
    """
    folded = [_normalized(q).casefold() for q in quotes]
    forms = [_normalized(anchor.name).casefold(), _normalized(member.name).casefold()]
    if not all(forms) or any(not any(f in span for span in folded) for f in forms):
        return False, (
            "the licensing spans do not, between them, contain both members' surface forms — a bind whose "
            "own evidence does not name both sides is not re-derivable by any reader"
        )
    marker = next((m for m in markers if any(_normalized(m).casefold() in s for s in folded)), None)
    if marker is None and not any(_paren_wraps(q, m.name) for q in quotes for m in (anchor, member)):
        return False, (
            "the licensing spans name both forms but carry no declared equivalence marker and no "
            "parenthetical wrapping either form — co-occurrence is not a stated equivalence"
        )
    if differs_only_by_a_mark(anchor.name, member.name, min_descriptor_len):
        return False, (
            f"the longer form extends the shorter by a MARK, not a word — '{anchor.name}' vs "
            f"'{member.name}'. A parenthetical mark reads exactly like an alias declaration "
            f"('Full Name (SHORT)') while in fact distinguishing two variants, and no marker vocabulary can "
            f"tell the two apart because the marker really is present. A name extended by a WORD is the same "
            f"thing described more fully; a name extended by a mark or a number is a different model, so the "
            f"equivalence is not licensed however the sentence is phrased (M1)"
        )
    how = f"equivalence marker '{marker}'" if marker else "a parenthetical wrapping one form"
    span_note = f" across {len(quotes)} verbatim spans" if len(quotes) > 1 else ""
    return True, (
        f"the licensing evidence contains both surface forms{span_note} and {how}, and the two forms differ "
        f"by more than a mark"
    )


def unambiguous_anaphor_gate(
    anchor: Mention, member: Mention, mentions: list[Mention]
) -> tuple[bool, str]:
    """D-13.17's ``UNAMBIGUOUS_ANAPHOR`` gate, **reformulated POSITIVELY** — ``(passed, why)``.

    **Why the original formulation had to be reversed.** It was an *absence* test — "the document contains no
    second mention of a compatible type the anaphor could mean" — over a **model-produced,
    surface-form-deduplicated** inventory. So *under-extraction makes the gate PASS*: its failure mode is
    anti-correlated with safety, and it converts a documented extractor under-reach into an over-merge path
    for the strongest fusion in the system. It also contradicted this design's own doctrine one section
    later, where absence of contrast is explicitly declared neutral: same document, opposite doctrines,
    structurally identical inputs.

    The positive form demands things be *present*:

    1. the antecedent is **named** (a non-empty surface form);
    2. the antecedent is **declared** — it carries an entity claim of its own, so something in the document
       actually asserted it rather than it arriving as a bare relation endpoint;
    3. the antecedent is **ontology-typed** (not ``unknown``);
    4. there is **exactly one** type-compatible mention for the anaphor to resolve to, where an
       ``unknown``-typed mention **COUNTS as compatible**. That last clause is the one that makes the test
       bite in the right direction: a second *undeclared* endpoint the extractor could not type is exactly
       the mention an under-reach would hide, so counting it as compatible makes under-extraction FAIL the
       gate instead of passing it.

    Not re-derivable by the resolver — it needs the document's whole mention inventory, which exists only
    here — so the verdict and its reason are stamped on the link for audit. That is a *code* check over the
    model's inventory, not a model self-report, which is the distinction D-13.17 actually rests on.
    """
    if not anchor.name.strip():
        return False, "the antecedent has no surface form (an anaphor needs a NAMED antecedent)"
    if not anchor.claim_id:
        return False, (
            "the antecedent is undeclared — no entity claim asserts it, so nothing in the document states "
            "what the anaphor is being resolved TO"
        )
    if anchor.entity_type == UNKNOWN_TYPE:
        return False, "the antecedent is not ontology-typed (an untyped antecedent cannot be type-unique)"
    compatible = [
        m for m in mentions
        if m.local_id != member.local_id
        and (m.entity_type == anchor.entity_type or m.entity_type == UNKNOWN_TYPE)
    ]
    if len(compatible) != 1:
        return False, (
            f"the anaphor has {len(compatible)} type-compatible antecedents in this document, not exactly "
            f"one (an 'unknown'-typed mention counts as compatible on purpose — a second undeclared endpoint "
            f"is precisely what an extractor under-reach would hide, and it must FAIL the gate, not pass it)"
        )
    if compatible[0].local_id != anchor.local_id:
        return False, "the single type-compatible antecedent is not the one this link binds to"
    return True, (
        f"exactly one type-compatible antecedent ('{anchor.entity_type}'), named and declared by its own "
        f"entity claim"
    )


def link_gate(
    evidence: str, quotes: list[str], anchor: Mention, member: Mention,
    mentions: list[Mention], markers: tuple[str, ...], min_descriptor_len: int | None = None,
) -> tuple[bool, str]:
    """Route one anchor→member link to its category's gate. An ungated category always fails (raise-only)."""
    if evidence == EXPLICIT_EQUIVALENCE:
        return explicit_equivalence_gate(quotes, anchor, member, markers, min_descriptor_len)
    if evidence == UNAMBIGUOUS_ANAPHOR:
        # M1 binds here too: an anaphor whose antecedent differs from it only by a mark is the same
        # collision arriving through the other category, and the positive gate alone cannot see it.
        if differs_only_by_a_mark(anchor.name, member.name, min_descriptor_len):
            return False, (
                f"'{member.name}' extends '{anchor.name}' by a mark, not a word — a mark distinguishes a "
                f"variant rather than naming the same thing, so no anaphoric reading licenses the bind (M1)"
            )
        return unambiguous_anaphor_gate(anchor, member, mentions)
    return False, (
        f"'{evidence}' has no deterministic gate and is raise-only by policy: an authoritative bind bypasses "
        f"banding, so authorising a bare name variant would rebuild the exact-name auto-merge lane on another "
        f"predicate — immune to the very cap that replaced it"
    )


# ── emission ────────────────────────────────────────────────────────────────────────────────────────

def _anchor(members: list[Mention]) -> Mention:
    """The member every coref edge is written from: the first *declared* mention in document order.

    Deterministic, and it prefers a claim-bearing mention so the emitted claim can cite a real premise
    where one exists. Falls back to the first member when the whole cluster is undeclared endpoints.
    """
    for mention in members:
        if mention.claim_id:
            return mention
    return members[0]


def coref_claims(accepted: list[tuple[list[Mention], str, list[str]]], *, claims: list[ClaimRecord],
                 loaded: LoadedDoc, source_id: str, model_id: str,
                 report_time: DateValue | None, ingest_time: DateValue | None,
                 mentions: list[Mention] | None = None, markers: tuple[str, ...] = (),
                 min_descriptor_len: int | None = None,
                 mint_referents: bool = False) -> list[ClaimRecord]:
    """Turn accepted clusters into ``coref-same-as`` claims — a star from the cluster's anchor.

    ``kind`` follows what the claim can actually cite, because an ``inference`` **must** carry premises:

    * **inference** when a member is a declared entity — ``premises`` names those mentions, which also
      earns the cross-reference plumbing for free (every id-reassignment path already remaps ``premises``:
      ``dedup.assign_claim_ids`` and the lane's/seed's chunk-namespacing).
    * **observation** when the whole cluster is undeclared endpoints, so there is no upstream claim to cite.
      The claim then rests on its licensing span exactly like any other observation — which is honest for
      the dominant case here, an equivalence the document *states* verbatim ("… (CPMIEC)"). Inventing a
      premise to keep one uniform kind would be worse than reporting what the claim really stands on.

    Provenance cites the licensing span itself (gate G4), and each edge carries the positional mention refs
    every other relationship claim carries.
    """
    # Local import: keeps this module off ``extract``'s import graph, so neither direction cycles.
    from chanakya.ingest.extract import _resolve_doc_ref, _sanitize_doc_token

    doc_token = _sanitize_doc_token(source_id)
    index = len(claims)  # continue the document's serial so provisional ids never collide with pass 1's
    out: list[ClaimRecord] = []

    inventory_all = mentions or []
    for number, (members, evidence, quotes) in enumerate(accepted, start=1):
        cluster_id = f"c{number}"
        anchor = _anchor(members)
        # M2: every verbatim span becomes a cited DocRef, so the claim's provenance names the whole licensing
        # SET rather than one of its spans — an equivalence stated across two fields is cited across both.
        refs = [_resolve_doc_ref(loaded, q, fallback=anchor.name) for q in quotes]
        ref: Any = refs[0] if len(refs) == 1 else refs
        # THE REFERENT ATOM (A1): one per document-local cluster, minted here and only here. It is a
        # *grouping signal* the rebuild consults and may DECLINE — never the address of a node — which is
        # why it rides the attribute bag and the members' entity claims rather than replacing any id.
        referent = make_referent_id(doc_token, cluster_id) if mint_referents else None
        for member in members:
            if member is anchor:
                continue
            index += 1
            attributes: dict[str, Any] = {
                CLUSTER_ATTR: cluster_id,
                EVIDENCE_ATTR: evidence,
                # A human-readable rendering for the drawer; ``QUOTES_ATTR`` carries the spans VERBATIM,
                # which is what a reader (and the resolver) re-derives the bind from.
                QUOTE_ATTR: _QUOTE_JOIN.join(quotes),
                QUOTES_ATTR: list(quotes),
            }
            if referent is not None:
                attributes[REFERENT_ATTR] = referent
                # C5: the gate is per LINK. Both members' forms and the per-link verdict are stamped so the
                # resolver can re-derive what it is able to (the quote checks) and audit what it cannot (the
                # anaphor gate needs the whole mention inventory, which exists only here).
                attributes[FORMS_ATTR] = [anchor.name, member.name]
                passed, why = link_gate(
                    evidence, quotes, anchor, member, inventory_all or members, markers,
                    min_descriptor_len,
                )
                attributes[GATE_ATTR] = GATE_PASS if passed else GATE_FAIL
                attributes[GATE_DETAIL_ATTR] = why
            if anchor.claim_id:
                attributes[edge_direction.SUBJECT_MENTION_ATTR] = anchor.claim_id
            if member.claim_id:
                attributes[edge_direction.OBJECT_MENTION_ATTR] = member.claim_id
            premises = [cid for cid in (anchor.claim_id, member.claim_id) if cid]
            out.append(ClaimRecord(
                claim_id=make_claim_id(doc_token, _coref_locator(ref), index=index),
                source_id=source_id,
                doc_ref=ref,
                kind="inference" if premises else "observation",
                polarity="positive",
                asserts="relationship",
                payload=Triple(subject=anchor.name, predicate=COREF_PREDICATE, object=member.name),
                report_time=report_time,
                ingest_time=ingest_time,
                premises=premises,
                extraction=Extraction(method="llm", version=model_id, model_conf=1.0),
                attributes=attributes,
            ))
    return out


def stamp_referents(
    claims: list[ClaimRecord], accepted: list[tuple[list[Mention], str, list[str]]], doc_token: str
) -> list[ClaimRecord]:
    """Return pass 1's claims with the referent atom stamped on each clustered member's ENTITY claim (A1).

    The grain is deliberate: *"an entity-form claim carries the referent of the mention it names"*. A
    relationship or event claim has two or more mentions and therefore no single referent, so it is left
    alone — its endpoints' referents are reached through the tier-3 mention refs.

    This is where the S1 field stops being dormant, and it is what makes the referent a **grouping** rather
    than a pile of pairs: the rebuild can recover every claim atom of one cluster and decide about the
    grouping as a whole (D-13.18), instead of only seeing n−1 star links.

    Consequence worth stating, because it is load-bearing and easy to miss: the referent joins
    ``dedup._claim_signature``, so two mentions with *different* referents no longer fold together. That is
    S1's design working as intended (identity is earned at rebuild, never assumed at ingest), not a side
    effect — and it is one more reason the minting rides the stage flag rather than shipping bare.

    Claims are replaced, never mutated: ``model_copy`` keeps the record immutable-in-spirit and leaves any
    claim not in a cluster **identical**, so a document with no accepted cluster is byte-unchanged.
    """
    by_claim: dict[str, str] = {}
    for number, (members, _evidence, _quote) in enumerate(accepted, start=1):
        referent = make_referent_id(doc_token, f"c{number}")
        for member in members:
            if member.claim_id:
                by_claim[member.claim_id] = referent
    if not by_claim:
        return claims
    return [
        c.model_copy(update={"referent_id": by_claim[c.claim_id]})
        if c.claim_id in by_claim and c.payload.form == "entity" and c.referent_id is None
        else c
        for c in claims
    ]


def valid_contrasts(
    raw: Any, mentions: list[Mention], text: str
) -> list[tuple[Mention, Mention, str]]:
    """The model's contrast proposals, quote-checked — D-13.19's contrastive channel.

    Same disposal discipline as the clusters: a contrast with no verbatim licensing span in the document is
    dropped, because the whole point is that *the document's own words* do the distinguishing. **Absence of
    a contrast is neutral** and is never a prior *for* merging — the same "absence is not evidence" doctrine
    the conflict machinery already follows.
    """
    if not isinstance(raw, dict):
        return []
    by_id = {m.local_id: m for m in mentions}
    out: list[tuple[Mention, Mention, str]] = []
    seen: set[frozenset[int]] = set()
    for entry in raw.get("contrasts") or []:
        if not isinstance(entry, dict):
            continue
        quote = entry.get("licensing_quote")
        if not isinstance(quote, str) or not _quote_supported(quote, text):
            continue
        left, right = by_id.get(entry.get("left_id")), by_id.get(entry.get("right_id"))
        if left is None or right is None or left.local_id == right.local_id:
            continue
        key = frozenset((left.local_id, right.local_id))
        if key in seen:
            continue
        seen.add(key)
        out.append((left, right, quote.strip()))
    return out


def contrast_claims(contrasts: list[tuple[Mention, Mention, str]], *, claims: list[ClaimRecord],
                    loaded: LoadedDoc, source_id: str, model_id: str,
                    report_time: DateValue | None, ingest_time: DateValue | None) -> list[ClaimRecord]:
    """Turn quote-checked contrasts into ``coref-distinct-from`` claims on their **own** lane.

    Its own lane, never the stated ``distinct-from`` rail. That rail is a hard, transitive, **ungraded** veto
    for an explicit "not related" — and widening it to "any enumeration" would be the single worst change
    available here, because *every ORBAT list contains an enumeration*: one planted document naming "the 8th
    AD Bn and the separate 12th AD Bn" would shatter a well-corroborated cluster. On this lane the same
    evidence is a **band ceiling**, which withholds one new fusion and cannot retract an existing merge, so
    the harm a grade gate would have defended against does not arise — which is exactly why the ceiling is
    ungraded.
    """
    from chanakya.ingest.extract import _resolve_doc_ref, _sanitize_doc_token

    doc_token = _sanitize_doc_token(source_id)
    index = len(claims)
    out: list[ClaimRecord] = []
    for left, right, quote in contrasts:
        index += 1
        ref = _resolve_doc_ref(loaded, quote, fallback=left.name)
        attributes: dict[str, Any] = {QUOTE_ATTR: quote, FORMS_ATTR: [left.name, right.name]}
        if left.claim_id:
            attributes[edge_direction.SUBJECT_MENTION_ATTR] = left.claim_id
        if right.claim_id:
            attributes[edge_direction.OBJECT_MENTION_ATTR] = right.claim_id
        premises = [cid for cid in (left.claim_id, right.claim_id) if cid]
        out.append(ClaimRecord(
            claim_id=make_claim_id(doc_token, _coref_locator(ref), index=index),
            source_id=source_id,
            doc_ref=ref,
            kind="inference" if premises else "observation",
            polarity="positive",
            asserts="relationship",
            payload=Triple(subject=left.name, predicate=CONTRAST_PREDICATE, object=right.name),
            report_time=report_time,
            ingest_time=ingest_time,
            premises=premises,
            extraction=Extraction(method="llm", version=model_id, model_conf=1.0),
            attributes=attributes,
        ))
    return out


def _coref_locator(ref: Any) -> str:
    """The claim-id locator stem for a coref edge — the licensing span's position, else a stable stem."""
    # Local import: keeps this module off ``extract``'s import graph, so neither direction cycles.
    from chanakya.ingest.extract import _locator

    stem = _locator(ref)
    return stem if stem != "x" else "coref"


# ── config + the public pass ────────────────────────────────────────────────────────────────────────

def _coref_cfg(config: ConfigBundle) -> dict[str, Any]:
    """The pass's knobs from ``credibility.yaml → coreference`` (hot-config). ``{}`` ⇒ dormant.

    **Both switches, one motion — and the S3 stage flag is what turns the motion.** The producer block is now
    declared and populated (it was commented out on the stated condition "turn it on together with that honor
    policy, not before", and S3 *is* that policy), but the pass stays dormant until
    ``resolution.earned_identity.enabled`` is on. Two reasons, and the second is the practical one:

    * it keeps the flag boundary in exactly **one** place, so flag-off is byte-identical on the *ingest* path
      too — a re-extract with the flag off records the same bundles, which is what makes the frozen corpus a
      stable baseline to dual-run against;
    * the pass costs a **second extraction call per document**. That is a real, stated cost, and it should
      not switch on as a side effect of reading a different config file.
    """
    from chanakya.resolve.rconfig import EarnedIdentity

    if not EarnedIdentity.from_resolution(config.resolution).enabled:
        return {}
    return dict(getattr(config.credibility, "coreference", None) or {})


def _categories(cfg: dict[str, Any]) -> tuple[str, ...]:
    """Which evidence kinds this deployment will emit. Unknown names are ignored.

    An *absent* key means "all three" (the documented default). An explicitly **empty** list means the
    deployment allows none — which is dormancy, not a silent fall-back to all of them: a config that says
    "emit nothing" must never be read as "emit everything".
    """
    if "categories" not in cfg:
        return EVIDENCE_CATEGORIES
    configured = cfg.get("categories")
    if not isinstance(configured, list):
        return EVIDENCE_CATEGORIES
    return tuple(c for c in EVIDENCE_CATEGORIES if c in configured)


def propose_coreference(claims: list[ClaimRecord], *, loaded: LoadedDoc, source_id: str,
                        config: ConfigBundle, client: ExtractionClient,
                        report_time: DateValue | None = None,
                        ingest_time: DateValue | None = None) -> list[ClaimRecord]:
    """Pass 2: cluster this document's mentions → extra ``coref-same-as`` claims (never a mutation).

    Returns ``[]`` — an honest refusal, never a guess — when the pass is not configured, the document
    offers fewer than two mentions, the inventory exceeds the configured cost guard, or the model fills
    nothing. Pass 1's claims are returned to the caller untouched; this only ever *adds*.
    """
    cfg = _coref_cfg(config)
    if not cfg:
        return []  # dormant: not configured on this deployment
    categories = _categories(cfg)
    if not categories:
        return []

    mentions = inventory(claims, edge_direction.direction_map(config))
    max_mentions = cfg.get("max_mentions")
    if len(mentions) < 2:
        return []
    if isinstance(max_mentions, int) and len(mentions) > max_mentions:
        return []  # cost guard: an outsized inventory is skipped, never silently truncated

    distinctions = _stated_pairs(claims, _DISTINCT_FROM)
    raw = client.extract(
        tool_name=TOOL_NAME,
        input_schema=CoreferenceClusters.model_json_schema(),
        system=SYSTEM,
        text=build_prompt(loaded.text, mentions, _stated_pairs(claims, _SAME_AS), distinctions),
    )
    accepted = valid_clusters(raw, mentions, loaded.text, distinctions, categories)
    earned = _earned_identity(config)
    contrasts = valid_contrasts(raw, mentions, loaded.text) if earned.enabled else []
    if not accepted and not contrasts:
        return []
    from chanakya.ingest.extract import _sanitize_doc_token

    out = coref_claims(
        accepted, claims=claims, loaded=loaded, source_id=source_id, model_id=client.model_id,
        report_time=report_time, ingest_time=ingest_time, mentions=mentions,
        markers=earned.equivalence_markers, min_descriptor_len=earned.min_descriptor_len,
        mint_referents=earned.enabled,
    ) if accepted else []
    if contrasts:
        out += contrast_claims(
            contrasts, claims=claims, loaded=loaded, source_id=source_id, model_id=client.model_id,
            report_time=report_time, ingest_time=ingest_time,
        )
    if earned.enabled and accepted:
        # The referent atoms are stamped on pass 1's own entity claims IN PLACE of nothing — the returned
        # list is written back by the caller, which is what promotes the cluster from "n−1 star links" to a
        # real GROUPING the rebuild can decline as a whole (D-13.18).
        _stamped[:] = stamp_referents(claims, accepted, _sanitize_doc_token(source_id))
    return out


#: Scratch hand-back for the referent stamping. ``propose_coreference`` keeps its historic signature (a list
#: of *additional* claims) so no caller or test has to change shape; :func:`revised_pass1` reads the stamped
#: pass-1 list the same call produced. Module-level and overwritten per call, which is safe because extraction
#: of one document is a single synchronous call and the value is consumed immediately by ``extract_document``.
_stamped: list[ClaimRecord] = []


def revised_pass1(fallback: list[ClaimRecord]) -> list[ClaimRecord]:
    """Pass 1's claims as the last :func:`propose_coreference` call left them (referents stamped), else as-is."""
    out = list(_stamped) if _stamped else list(fallback)
    _stamped.clear()
    return out


def _earned_identity(config: ConfigBundle) -> Any:
    """The S3 knob block, read through RESOLVE's typed reader so there is one definition of the flag."""
    from chanakya.resolve.rconfig import EarnedIdentity

    return EarnedIdentity.from_resolution(config.resolution)


__all__ = [
    "CLUSTER_ATTR",
    "CONTRAST_PREDICATE",
    "COREF_PREDICATE",
    "EVIDENCE_ATTR",
    "EVIDENCE_CATEGORIES",
    "FORMS_ATTR",
    "GATE_ATTR",
    "GATE_DETAIL_ATTR",
    "GATE_FAIL",
    "GATE_PASS",
    "QUOTES_ATTR",
    "QUOTE_ATTR",
    "REFERENT_ATTR",
    "TOOL_NAME",
    "CoreferenceCluster",
    "CoreferenceClusters",
    "CoreferenceContrast",
    "Mention",
    "build_prompt",
    "contrast_claims",
    "coref_claims",
    "differs_only_by_a_mark",
    "explicit_equivalence_gate",
    "inventory",
    "link_gate",
    "propose_coreference",
    "revised_pass1",
    "stamp_referents",
    "supported_spans",
    "unambiguous_anaphor_gate",
    "valid_clusters",
    "valid_contrasts",
]
