"""Tier 0 + characterize: mentions -> referent atoms -> provisional instances.

Two things happen here, in this order:

1. **The Tier-0 grouping decision (D-13.17 / D-13.18).** A coref proposal is a
   *model self-report*, so it may only mint one shared referent atom behind a
   deterministic, re-derivable gate **and** a source-grade floor. A grouping the
   rebuild cannot stand behind is **declined** — de-grouped to claim-atom
   granularity and raised. Nothing splits; the *grouping* declines.

2. **Characterization.** Each effective atom becomes a provisional instance with
   a **discriminator bag**. The bag keeps the **full set** of member values per
   slot, which is the whole point: production's ``Entity.attrs`` is
   first-claim-wins scalar (``resolve/entities.py:189`` ``setdefault``), so an
   intra-referent conflict is invisible there and only survives in
   ``attr_history``. The decline check below reads the set, never a collapsed
   scalar.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import strings

_PAREN = re.compile(r"\(([^)]*)\)")


def natkey(s: str) -> tuple:
    """Natural sort key so m2 sorts before m10 (determinism, not cosmetics)."""
    out = []
    for part in re.split(r"(\d+)", s):
        if part == "":
            continue
        if part.isdigit():
            out.append((0, int(part), ""))
        else:
            out.append((1, 0, part))
    return tuple(out)


# --------------------------------------------------------------------------
# input records
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Mention:
    doc_id: str
    local_id: str
    surface: str
    entity_type: str
    attrs: dict
    coref: dict | None
    contrast_group: str | None
    source_grade: str

    @property
    def atom_id(self) -> str:
        return f"{self.doc_id}-{self.local_id}"

    @property
    def key(self) -> tuple[str, str]:
        return (self.doc_id, self.local_id)


@dataclass(frozen=True)
class EdgeRec:
    doc_id: str
    subject: str
    predicate: str
    object: str
    kind: str
    event_time: str | None


@dataclass
class ReferentAtom:
    referent_id: str
    doc_id: str
    member_local_ids: list[str]
    authoritative: bool
    category: str | None
    gate_results: dict
    declined: bool
    decline_reason: str | None
    quote: str | None = None
    effective: bool = True          # False for the declined record itself


@dataclass
class Instance:
    instance_id: str = ""
    citizen: str = ""
    layer: str = ""
    etypes: tuple = ()
    doc_ids: tuple = ()
    grades: tuple = ()
    member_referent_ids: list = field(default_factory=list)
    member_claim_atoms: list = field(default_factory=list)
    member_keys: list = field(default_factory=list)
    surfaces: list = field(default_factory=list)
    # slot -> list of (stated, canonical, normalization_known)
    slots: dict = field(default_factory=dict)
    placements: list = field(default_factory=list)  # (canon, stated, time, predicate)
    neighbours: set = field(default_factory=set)
    contrast_groups: set = field(default_factory=set)
    authoritative_atom: bool = False
    formation_evidence: bool = False


# --------------------------------------------------------------------------
# value normalization (R5.2 — before conflict detection AND before key derivation)
# --------------------------------------------------------------------------

class Normalizer:
    def __init__(self, cfg: dict) -> None:
        n = cfg["normalization"]
        self.rules = n.get("transliteration") or {}
        self.ordinals = {k.casefold(): v for k, v in (n.get("designator_ordinals") or {}).items()}
        self.classes: dict[str, dict[str, str]] = {}
        for slot, groups in (n.get("equivalence_classes") or {}).items():
            table: dict[str, str] = {}
            for group in groups:
                canonical = strings.normalize(str(group[0]), self.rules)
                for member in group:
                    table[strings.normalize(str(member), self.rules)] = canonical
            self.classes[slot] = table

    def canonical(self, slot: str, stated: str) -> tuple[str, bool]:
        """(canonical form, was the value resolvable through the config table?).

        The boolean is load-bearing: R5.2 forbids walling on a value we could not
        normalize, because we cannot tell 'PAF' from 'Pakistan Air Force' and a
        wall on an untested string comparison shatters legitimate merges.
        """
        base = strings.normalize(stated, self.rules)
        if slot == "designation":
            parts = [self.ordinals.get(p, p) for p in base.split(" ") if p]
            return " ".join(parts), True
        table = self.classes.get(slot)
        if table is None:
            return base, True
        if base in table:
            return table[base], True
        return base, False


# --------------------------------------------------------------------------
# time
# --------------------------------------------------------------------------

def time_window(value: str | None) -> tuple[date, date] | None:
    """Parse a stated date at its stated precision into a closed day range."""
    if not value:
        return None
    v = value.strip()
    try:
        if len(v) == 4:
            y = int(v)
            return date(y, 1, 1), date(y, 12, 31)
        if len(v) == 7:
            y, m = int(v[:4]), int(v[5:7])
            next_month = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
            return date(y, m, 1), date.fromordinal(next_month.toordinal() - 1)
        y, m, d = int(v[:4]), int(v[5:7]), int(v[8:10])
        return date(y, m, d), date(y, m, d)
    except (ValueError, IndexError):
        return None


def windows_overlap(a: str | None, b: str | None, tolerance_days: int) -> bool | None:
    """True/False when both dates parse; None when either is unstated.

    ``None`` is not ``False``: an unstated date means we *cannot test* overlap, and
    absence is never a conflict. Callers must not coerce it.
    """
    wa, wb = time_window(a), time_window(b)
    if wa is None or wb is None:
        return None
    lo_a, hi_a = wa
    lo_b, hi_b = wb
    return (lo_a.toordinal() - tolerance_days) <= hi_b.toordinal() and \
           (lo_b.toordinal() - tolerance_days) <= hi_a.toordinal()


# --------------------------------------------------------------------------
# Tier-0 gates
# --------------------------------------------------------------------------

class Tier0:
    def __init__(self, cfg: dict, norm: Normalizer) -> None:
        self.cfg = cfg
        self.norm = norm
        c = cfg["coref"]
        self.authoritative_categories = set(c["authoritative_categories"])
        self.markers = [strings.normalize(m) for m in c["equivalence_markers"]]
        self.paren_marker = bool(c["parenthetical_counts_as_marker"])
        self.classes = [set(g) for g in c["type_compatibility_classes"]]
        grades = cfg["grades"]["order"]
        self.grade_rank = {g: i for i, g in enumerate(grades)}
        self.grade_floor = self.grade_rank[cfg["grades"]["coref_authoritative_min_grade"]]

    def types_compatible(self, a: str, b: str) -> bool:
        if a == b:
            return True
        return any(a in g and b in g for g in self.classes)

    def grade_ok(self, grade: str) -> bool:
        rank = self.grade_rank.get(grade)
        return rank is not None and rank <= self.grade_floor

    # -- EXPLICIT_EQUIVALENCE -------------------------------------------------
    def _quote_has_marker(self, quote: str, form_a: str, form_b: str) -> bool:
        nq = strings.normalize(quote)
        padded = f" {nq} "
        if any(f" {m} " in padded for m in self.markers if m):
            return True
        if self.paren_marker:
            for inner in _PAREN.findall(quote):
                ni = strings.normalize(inner)
                if not ni:
                    continue
                if ni in (form_a, form_b) or form_a in ni or form_b in ni:
                    return True
        return False

    def equivalence_gate(self, anchor: Mention, member: Mention) -> bool:
        quote = (member.coref or {}).get("quote") or ""
        if not quote.strip():
            return False
        nq = strings.normalize(quote)
        fa = strings.normalize(anchor.surface)
        fb = strings.normalize(member.surface)
        if not fa or not fb:
            return False
        if fa not in nq or fb not in nq:
            return False
        return self._quote_has_marker(quote, fa, fb)

    # -- UNAMBIGUOUS_ANAPHOR --------------------------------------------------
    def anaphor_gate(self, anchor: Mention, members: list[Mention], doc_mentions: list[Mention]) -> bool:
        inside = {m.local_id for m in members}
        for other in doc_mentions:
            if other.local_id in inside:
                continue
            if self.types_compatible(other.entity_type, anchor.entity_type):
                return False   # a second thing the anaphor could mean
        return True


# --------------------------------------------------------------------------
# building
# --------------------------------------------------------------------------

def _anchor(members: list[Mention]) -> Mention:
    """First *declared* member (one carrying stated attributes), else first by id.

    Mirrors ``ingest/coref.py:330``'s "first claim-bearing member else members[0]";
    the prototype's stand-in for "declared" is "the source stated attributes on it",
    since the input contract carries no claim ids.
    """
    declared = [m for m in members if m.attrs]
    pool = declared or members
    return sorted(pool, key=lambda m: natkey(m.local_id))[0]


def _slot_values(slot: str, spec: dict, members: list[Mention], edges: list[EdgeRec],
                 mention_by: dict, norm: Normalizer) -> list[tuple[str, str, bool]]:
    """The FULL set of stated values for one slot, deduped, order-stable."""
    out: list[tuple[str, str, bool]] = []
    seen = set()

    def add(stated: str) -> None:
        canonical, known = norm.canonical(slot, stated)
        if not canonical or canonical in seen:
            return
        seen.add(canonical)
        out.append((stated, canonical, known))

    for member in sorted(members, key=lambda m: natkey(m.local_id)):
        for attr in spec.get("attrs") or []:
            if attr in member.attrs:
                add(str(member.attrs[attr]))
    for predicate_slot in spec.get("from_predicates") or []:
        for edge in edges:
            if edge.predicate != predicate_slot:
                continue
            obj = mention_by.get((edge.doc_id, edge.object))
            if obj is not None:
                add(obj.surface)
    if spec.get("from_edge_field") == "event_time":
        for edge in edges:
            if edge.event_time:
                add(edge.event_time)
    return out


def _composite_state(spec: dict, slots: dict) -> list[tuple[str, ...]]:
    """The composite AND-keys this instance can actually form.

    A key exists only when *every* component is present — that is D-13.20's whole
    point: a bare designator is not an identifier, ``(operator, designation)`` is.
    """
    keys: list[tuple[str, ...]] = []
    for components in spec.get("composite_keys") or []:
        values = []
        for component in components:
            vals = slots.get(component) or []
            if len(vals) != 1:
                values = []
                break
            values.append(vals[0][1])
        if values:
            keys.append(tuple(values))
    return keys


class Builder:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.norm = Normalizer(cfg)
        self.tier0 = Tier0(cfg, self.norm)

    # ---------------------------------------------------------------- atoms
    def referent_atoms(self, doc_id: str, mentions: list[Mention]) -> tuple[list[ReferentAtom], list[dict], list[dict]]:
        """Returns (atoms, injected_pairs, notes). Atoms include declined records."""
        atoms: list[ReferentAtom] = []
        injected: list[dict] = []
        notes: list[dict] = []
        clusters: dict[str, list[Mention]] = {}
        loose: list[Mention] = []
        for m in mentions:
            cid = (m.coref or {}).get("cluster")
            if cid:
                clusters.setdefault(str(cid), []).append(m)
            else:
                loose.append(m)

        for cid in sorted(clusters, key=natkey):
            members = sorted(clusters[cid], key=lambda m: natkey(m.local_id))
            if len(members) == 1:
                # A one-member "cluster" is not a grouping; treat as a bare mention.
                loose.extend(members)
                continue
            category = sorted({(m.coref or {}).get("category") or "" for m in members})[-1] or None
            anchor = _anchor(members)
            grade = members[0].source_grade
            eligible = category in self.tier0.authoritative_categories
            if not eligible:
                structural = False
            elif category == "EXPLICIT_EQUIVALENCE":
                structural = all(
                    self.tier0.equivalence_gate(anchor, m)
                    for m in members if m.local_id != anchor.local_id
                )
            else:  # UNAMBIGUOUS_ANAPHOR
                structural = self.tier0.anaphor_gate(anchor, members, mentions)
            grade_ok = self.tier0.grade_ok(grade)
            gates = {
                "structural": "pass" if structural else "fail",
                "grade": "pass" if grade_ok else "fail",
            }
            quote = next(
                ((m.coref or {}).get("quote") for m in members if (m.coref or {}).get("quote")),
                None,
            )
            authoritative = bool(eligible and structural and grade_ok)

            if authoritative:
                reason = self._decline_reason(members)
                if reason is None:
                    atoms.append(ReferentAtom(
                        referent_id="", doc_id=doc_id,
                        member_local_ids=[m.local_id for m in members],
                        authoritative=True, category=category, gate_results=gates,
                        declined=False, decline_reason=None, quote=quote,
                    ))
                    continue
                # D-13.18: the rebuild DECLINES the grouping. Record the declined
                # grouping *and* fall through to claim-atom granularity.
                atoms.append(ReferentAtom(
                    referent_id="", doc_id=doc_id,
                    member_local_ids=[m.local_id for m in members],
                    authoritative=True, category=category, gate_results=gates,
                    declined=True, decline_reason=reason, quote=quote, effective=False,
                ))
                notes.append({"kind": "grouping-declined", "doc_id": doc_id,
                              "members": [m.local_id for m in members],
                              "detail": reason, "quote": quote})
            else:
                notes.append({"kind": "coref-held-loose", "doc_id": doc_id,
                              "members": [m.local_id for m in members],
                              "detail": "structural" if not structural else "source-grade",
                              "quote": quote, "category": category})
                for m in members:
                    if m.local_id == anchor.local_id:
                        continue
                    injected.append({"doc_id": doc_id, "a": anchor.local_id, "b": m.local_id,
                                     "quote": quote, "category": category})
            for m in members:
                atoms.append(ReferentAtom(
                    referent_id="", doc_id=doc_id, member_local_ids=[m.local_id],
                    authoritative=False, category=category, gate_results=gates,
                    declined=False, decline_reason=None, quote=quote,
                ))

        for m in sorted(loose, key=lambda x: natkey(x.local_id)):
            atoms.append(ReferentAtom(
                referent_id="", doc_id=doc_id, member_local_ids=[m.local_id],
                authoritative=False, category=(m.coref or {}).get("category"),
                gate_results={}, declined=False, decline_reason=None,
                quote=(m.coref or {}).get("quote"),
            ))
        return atoms, injected, notes

    def _decline_reason(self, members: list[Mention]) -> str | None:
        """An intra-referent critical-discriminator conflict, read off the FULL
        member value set (never a first-claim-wins scalar)."""
        groups: dict[str, list[str]] = {}
        for m in members:
            if m.contrast_group:
                groups.setdefault(m.contrast_group, []).append(m.local_id)
        for gid, ids in sorted(groups.items()):
            if len(ids) > 1:
                return (f"stated-contrast-within-cluster: the source enumerated "
                        f"{', '.join(sorted(ids, key=natkey))} as siblings (contrast group "
                        f"{gid}) yet the proposal equates them")
        slots_cfg = self.cfg["discriminators"]["slots"]
        for slot in sorted(slots_cfg):
            spec = slots_cfg[slot]
            if not spec.get("wall_on_conflict") or spec.get("multivalued"):
                continue
            values: dict[str, list[str]] = {}
            unknown = False
            for m in members:
                for attr in spec.get("attrs") or []:
                    if attr in m.attrs:
                        canonical, known = self.norm.canonical(slot, str(m.attrs[attr]))
                        unknown = unknown or not known
                        values.setdefault(canonical, []).append(f"{m.local_id}={m.attrs[attr]}")
            if len(values) > 1:
                if spec.get("require_normalization_to_wall") and unknown:
                    continue   # untested string comparison — a gap, never a decline
                detail = "; ".join(f"{k} <- {', '.join(v)}" for k, v in sorted(values.items()))
                return (f"critical-discriminator-conflict on {slot}: the members carry "
                        f"{len(values)} incompatible stated values [{detail}]")
        return None

    # ------------------------------------------------------------ instances
    def instances(self, atoms: list[ReferentAtom], edges_by_doc: dict,
                  mention_by: dict) -> list[Instance]:
        cfg = self.cfg
        slots_cfg = cfg["discriminators"]["slots"]
        layer_by_type = cfg["citizens"]["layer_by_type"]
        default_layer = cfg["citizens"]["default_layer"]
        citizen_by_layer = cfg["citizens"]["citizen_by_layer"]
        formation_attrs = set(cfg["citizens"]["formation_evidence"]["attrs"])
        formation_predicates = set(cfg["citizens"]["formation_evidence"]["predicates"])
        geo_predicates = set(slots_cfg["geography"].get("from_predicates") or [])

        out: list[Instance] = []
        for atom in atoms:
            if not atom.effective:
                continue
            members = [mention_by[(atom.doc_id, lid)] for lid in atom.member_local_ids]
            member_ids = {m.local_id for m in members}
            edges = [e for e in edges_by_doc.get(atom.doc_id, [])
                     if e.subject in member_ids or e.object in member_ids]
            own_edges = [e for e in edges if e.subject in member_ids]

            inst = Instance()
            inst.etypes = tuple(sorted({m.entity_type for m in members}))
            inst.doc_ids = (atom.doc_id,)
            inst.grades = tuple(sorted({m.source_grade for m in members}))
            inst.member_referent_ids = [atom.referent_id]
            inst.member_claim_atoms = sorted((m.atom_id for m in members), key=natkey)
            inst.member_keys = [m.key for m in members]
            inst.surfaces = [m.surface for m in sorted(members, key=lambda m: natkey(m.local_id))]
            inst.authoritative_atom = atom.authoritative and not atom.declined
            inst.contrast_groups = {m.contrast_group for m in members if m.contrast_group}

            # layer: instance > design > anchor. The conservative rule — the
            # instance layer carries the STRICTER identity policy, so an
            # ambiguous type gets the stricter one, never the permissive one.
            layers = {layer_by_type.get(t, default_layer) for t in inst.etypes}
            inst.layer = "instance" if "instance" in layers else (
                "design" if "design" in layers else layers.pop())

            inst.formation_evidence = any(
                a in formation_attrs for m in members for a in m.attrs
            ) or any(e.predicate in formation_predicates for e in own_edges)
            if inst.layer == "instance":
                inst.citizen = "formation" if inst.formation_evidence else "presence"
            else:
                inst.citizen = citizen_by_layer.get(inst.layer, inst.layer)

            for slot in sorted(slots_cfg):
                spec = slots_cfg[slot]
                if slot == "unique_id":
                    continue
                inst.slots[slot] = _slot_values(slot, spec, members, own_edges,
                                                mention_by, self.norm)
            inst.slots["unique_id"] = [
                (" + ".join(k), " + ".join(k), True)
                for k in _composite_state(slots_cfg["unique_id"], inst.slots)
            ]

            for e in own_edges:
                if e.predicate not in geo_predicates:
                    continue
                obj = mention_by.get((e.doc_id, e.object))
                if obj is None:
                    continue
                inst.placements.append(
                    (strings.normalize(obj.surface, self.norm.rules), obj.surface,
                     e.event_time, e.predicate)
                )
            inst.placements.sort(key=lambda p: (p[2] or "", p[0], p[3]))
            out.append(inst)
        return out
