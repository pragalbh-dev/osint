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
#: The verbatim licensing span. Reuses the existing provenance key every other claim uses.
QUOTE_ATTR = "source_quote"

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
    licensing_quote: str | None = None


class CoreferenceClusters(BaseModel):
    """The pass-2 output: only the merges. Any mention not named stays its own singleton."""

    clusters: list[CoreferenceCluster] = []


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
exact verbatim quote from the document that licenses the grouping. If you cannot quote a licensing span, do
not report the cluster. Any mention you do not name stays its own singleton.\
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
                   ) -> list[tuple[list[Mention], str, str]]:
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
    accepted: list[tuple[list[Mention], str, str]] = []
    claimed: set[int] = set()

    for entry in raw.get("clusters") or []:
        if not isinstance(entry, dict):
            continue
        evidence = entry.get("evidence")
        if not isinstance(evidence, str) or evidence not in categories:
            continue
        quote = entry.get("licensing_quote")
        if not isinstance(quote, str) or not _quote_supported(quote, text):
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
        accepted.append((members, evidence, quote.strip()))
    return accepted


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


def coref_claims(accepted: list[tuple[list[Mention], str, str]], *, claims: list[ClaimRecord],
                 loaded: LoadedDoc, source_id: str, model_id: str,
                 report_time: DateValue | None, ingest_time: DateValue | None) -> list[ClaimRecord]:
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

    for number, (members, evidence, quote) in enumerate(accepted, start=1):
        cluster_id = f"c{number}"
        anchor = _anchor(members)
        ref = _resolve_doc_ref(loaded, quote, fallback=anchor.name)
        for member in members:
            if member is anchor:
                continue
            index += 1
            attributes: dict[str, Any] = {
                CLUSTER_ATTR: cluster_id,
                EVIDENCE_ATTR: evidence,
                QUOTE_ATTR: quote,
            }
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


def _coref_locator(ref: Any) -> str:
    """The claim-id locator stem for a coref edge — the licensing span's position, else a stable stem."""
    # Local import: keeps this module off ``extract``'s import graph, so neither direction cycles.
    from chanakya.ingest.extract import _locator

    stem = _locator(ref)
    return stem if stem != "x" else "coref"


# ── config + the public pass ────────────────────────────────────────────────────────────────────────

def _coref_cfg(config: ConfigBundle) -> dict[str, Any]:
    """The pass's knobs from ``credibility.yaml → coreference`` (hot-config). ``{}`` ⇒ dormant."""
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
    if not accepted:
        return []
    return coref_claims(
        accepted, claims=claims, loaded=loaded, source_id=source_id, model_id=client.model_id,
        report_time=report_time, ingest_time=ingest_time,
    )


__all__ = [
    "CLUSTER_ATTR",
    "COREF_PREDICATE",
    "EVIDENCE_ATTR",
    "EVIDENCE_CATEGORIES",
    "QUOTE_ATTR",
    "TOOL_NAME",
    "CoreferenceCluster",
    "CoreferenceClusters",
    "Mention",
    "build_prompt",
    "coref_claims",
    "inventory",
    "propose_coreference",
    "valid_clusters",
]
