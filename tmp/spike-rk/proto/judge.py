"""Tier 1: the D-13.20 discriminator ladder, judged pair by pair.

The ladder manifests in **three shapes, not one dial** — blocking, score, and
cap-or-wall — and ``name`` is a **separate signal** from ``discriminator``. That
split is the whole point of this module: production fuses the two at a single
``max`` (``resolve/scoring.py:437`` ``sim = max(sim, agreeing / present)``), and
D-13.10's rule — "a name match reaches at most *possible*, and one more
trivially-available signal clears it" — is unexpressible while they live in one
number.

**The one structural guarantee.** A pair fuses (``verdict == "confirmed"``) only
when it holds a *durable confirm trigger* — a composite AND-key match, a
temporally-witnessed continuity, or a corroborated designation. The score can
never fuse a pair: ``band_from_score`` returns ``probable`` at most, by
construction. So co-location, name similarity and relational overlap — the exact
signals in defect D1's chain — cannot reach ``confirmed`` no matter how high they
score.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import protoconfig
import strings
from characterize import Instance, windows_overlap


@dataclass
class Verdict:
    a: str
    b: str
    verdict: str
    signals: dict
    ceiling: str | None
    ceiling_reason: str | None
    walls: list = field(default_factory=list)
    same_doc: bool = False
    reason: str = ""
    triggers: list = field(default_factory=list)
    slot_states: dict = field(default_factory=dict)
    composite: str = "incomplete"
    caps_fired: list = field(default_factory=list)
    contrast: bool = False
    injected: bool = False


class UnionFind:
    def __init__(self, items: list[str]) -> None:
        self.parent = {i: i for i in sorted(items)}

    def find(self, x: str) -> str:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: str, b: str) -> bool:
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        lo, hi = sorted((ra, rb))
        self.parent[hi] = lo
        return True


class Judge:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.slots_cfg = cfg["discriminators"]["slots"]
        self.bag = list(cfg["discriminators"]["bag"])
        self.tol = int(cfg["discriminators"]["time_overlap_tolerance_days"])
        self.weights = cfg["scoring"]["weights"]
        self.bands = cfg["scoring"]["bands"]
        self.round_digits = int(cfg["scoring"]["round_digits"])
        self.caps = cfg["caps"]
        self.liftable = set(cfg["caps"]["lifted_by_composite_unique_id"])
        self.triggers_cfg = cfg["confirm"]["triggers"]
        self.classes = [set(g) for g in cfg["coref"]["type_compatibility_classes"]]
        nc = cfg["name_channel"]
        self.jw_scale = float(nc["jaro_winkler_prefix_scale"])
        self.jw_cap = int(nc["jaro_winkler_prefix_cap"])
        self.rarity_on = bool(nc["rarity"]["enabled"])
        self.rules = cfg["normalization"].get("transliteration") or {}

    # ---------------------------------------------------------------- shapes
    def types_compatible(self, a: Instance, b: Instance) -> bool:
        for ta in a.etypes:
            for tb in b.etypes:
                if ta == tb or any(ta in g and tb in g for g in self.classes):
                    return True
        return False

    def slot_state(self, a: Instance, b: Instance, slot: str) -> str:
        """agree | conflict | unnormalized | differ | absent."""
        spec = self.slots_cfg[slot]
        va, vb = a.slots.get(slot) or [], b.slots.get(slot) or []
        if not va or not vb:
            return "absent"
        if slot == "time":
            for sa, _, _ in va:
                for sb, _, _ in vb:
                    if windows_overlap(sa, sb, self.tol) is True:
                        return "agree"
            return "differ"
        ca = {c for _, c, _ in va}
        cb = {c for _, c, _ in vb}
        if ca & cb:
            return "agree"
        if spec.get("multivalued"):
            # No overlap on a legitimately multi-valued slot is not a conflict.
            # Its wall (different place, overlapping time) is tested on placements.
            return "differ"
        if spec.get("require_normalization_to_wall"):
            known = all(k for _, _, k in va) and all(k for _, _, k in vb)
            if not known:
                return "unnormalized"
        return "conflict" if spec.get("wall_on_conflict") else "differ"

    def composite_state(self, states: dict) -> str:
        keys = self.slots_cfg["unique_id"].get("composite_keys") or []
        for components in keys:
            if all(states.get(c) == "agree" for c in components):
                return "match"
        for components in keys:
            component_states = [states.get(c) for c in components]
            if all(s in ("agree", "conflict") for s in component_states) and \
                    any(s == "conflict" for s in component_states):
                return "conflict"
        return "incomplete"

    def geo_wall(self, a: Instance, b: Instance) -> tuple[str, str, str] | None:
        for pa, sa, ta, _ in a.placements:
            for pb, sb, tb, _ in b.placements:
                if pa == pb:
                    continue
                if windows_overlap(ta, tb, self.tol) is True:
                    return (sa, sb, ta or "")
        return None

    # --------------------------------------------------------------- signals
    def name_signal(self, a: Instance, b: Instance, rarity) -> float:
        best = 0.0
        for sa in a.surfaces:
            for sb in b.surfaces:
                sim = strings.name_similarity(sa, sb, self.rules, self.jw_scale, self.jw_cap)
                if self.rarity_on and rarity is not None:
                    sim = max(sim, rarity.dice(strings.tokens(sa, self.rules),
                                               strings.tokens(sb, self.rules)))
                best = max(best, sim)
        return best

    def discriminator_signal(self, states: dict) -> tuple[float, list[str]]:
        agreeing, total, names = 0.0, 0.0, []
        for slot in self.bag:
            weight = float(self.slots_cfg[slot]["weight"])
            total += weight
            if states.get(slot) == "agree":
                agreeing += weight
                names.append(slot)
        return (agreeing / total if total else 0.0), sorted(names)

    def relational_signal(self, a: Instance, b: Instance, uf: UnionFind) -> float:
        def canon(keys: set) -> set:
            return {(d, p, uf.find(o) if o in uf.parent else o, t) for d, p, o, t in keys}
        ka, kb = canon(a.neighbours), canon(b.neighbours)
        if not ka or not kb:
            return 0.0
        union = ka | kb
        return len(ka & kb) / len(union) if union else 0.0

    # -------------------------------------------------------------- triggers
    def temporal_continuity(self, a: Instance, b: Instance, states: dict) -> bool:
        if states.get("designation") != "agree":
            return False
        if self.geo_wall(a, b) is not None:
            return False
        for pa, _, ta, _pr in a.placements:
            for pb, _, tb, _pr2 in b.placements:
                if pa != pb and windows_overlap(ta, tb, self.tol) is False:
                    return True
        return False

    def confirm_triggers(self, a: Instance, b: Instance, states: dict, composite: str) -> list[str]:
        out = []
        if composite == "match":
            out.append("composite_unique_id_match")
        if self.temporal_continuity(a, b, states):
            out.append("temporal_continuity")
        if states.get("designation") == "agree" and states.get("operator") == "agree":
            out.append("corroborated_designation")
        return sorted(out)

    # ------------------------------------------------------------------ main
    def judge(self, a: Instance, b: Instance, uf: UnionFind, rarity) -> Verdict:
        same_doc = bool(set(a.doc_ids) & set(b.doc_ids))
        zero = {"name": 0.0, "discriminator": 0.0, "relational": 0.0}

        if not self.types_compatible(a, b):
            return Verdict(
                a=a.instance_id, b=b.instance_id, verdict="separate", signals=dict(zero),
                ceiling=None, ceiling_reason=None, walls=["type-incompatible"],
                same_doc=same_doc,
                reason=(f"entity types {'/'.join(a.etypes)} and {'/'.join(b.etypes)} are not in a "
                        "compatible class, so the pair was never compared. Surfaced as a named wall "
                        "rather than a silent skip."),
            )

        states = {slot: self.slot_state(a, b, slot) for slot in self.bag if slot != "unique_id"}
        composite = self.composite_state(states)
        states["unique_id"] = {"match": "agree", "conflict": "conflict"}.get(composite, "absent")

        walls: list[str] = []
        wall_notes: list[str] = []
        if states.get("designation") == "conflict":
            walls.append("designation-conflict")
            wall_notes.append("the two sides state different formation designations")
        if composite == "conflict":
            walls.append("identifier-conflict")
            wall_notes.append("every component of a composite identity key is stated and they differ")
        if states.get("operator") == "conflict":
            walls.append("operator-conflict")
            wall_notes.append("the two sides state different operators after normalization")
        geo = self.geo_wall(a, b)
        if geo is not None:
            walls.append("geography-conflict-overlapping-time")
            wall_notes.append(f"stated at both {geo[0]} and {geo[1]} over overlapping time "
                              f"({geo[2] or 'undated'}); this wall is pairwise, never transitive")

        name = self.name_signal(a, b, rarity)
        disc, agreeing = self.discriminator_signal(states)
        rel = self.relational_signal(a, b, uf)
        signals = {
            "name": round(name, self.round_digits),
            "discriminator": round(disc, self.round_digits),
            "relational": round(rel, self.round_digits),
        }
        contrast = bool(same_doc and (a.contrast_groups & b.contrast_groups))

        if walls:
            return Verdict(
                a=a.instance_id, b=b.instance_id, verdict="separate", signals=signals,
                ceiling=None, ceiling_reason=None, walls=sorted(walls), same_doc=same_doc,
                reason="Walled, so no band applies: " + "; ".join(wall_notes) + ".",
                slot_states=states, composite=composite, contrast=contrast,
            )

        triggers = self.confirm_triggers(a, b, states, composite)
        independent_sources = len(set(a.doc_ids) | set(b.doc_ids))
        eligible = [
            t for t in triggers
            if independent_sources >= int(self.triggers_cfg[t]["min_independent_sources"])
        ]

        caps_fired: list[tuple[str, str, str]] = []
        if name > 0.0 and disc == 0.0 and rel == 0.0:
            caps_fired.append(("name_alone", self.caps["name_alone"],
                               "the only agreement between the two sides is their names"))
        perishable_agreeing = [s for s in agreeing if self.slots_cfg[s].get("perishable")]
        if agreeing and len(perishable_agreeing) == len(agreeing) and not triggers:
            caps_fired.append(("perishable_only", self.caps["perishable_only"],
                               "every agreeing discriminator is perishable ("
                               + ", ".join(perishable_agreeing) +
                               "), which is evidence about a moment, not about a referent"))
        unit_level = bool(triggers)
        if a.citizen == "formation" and b.citizen == "formation" and not unit_level and \
                (rel > 0.0 or states.get("geography") == "agree"):
            caps_fired.append(("co_location_formation", self.caps["co_location_formation"],
                               "the pair agrees only on shared design, site and operator, which "
                               "cannot tell one formation from two co-located ones; a unit-level "
                               "discriminator (designation, identifier, witnessed continuity or an "
                               "analyst) is required"))
        if contrast:
            caps_fired.append(("same_doc_stated_contrast", self.caps["same_doc_stated_contrast"],
                               "the source itself enumerated these as sibling referents in one "
                               "document, which is stated anti-identity evidence"))

        lifted = [c for c in caps_fired if composite == "match" and c[0] in self.liftable]
        effective = [c for c in caps_fired if c not in lifted]
        ceiling = None
        for _, band, _ in effective:
            ceiling = protoconfig.lower_band(ceiling, band)
        ceiling_reason = None
        if effective:
            ceiling_reason = "; ".join(f"{n}: {why}" for n, _, why in sorted(effective))

        total = (self.weights["name"] * name + self.weights["discriminator"] * disc
                 + self.weights["relational"] * rel)
        band = self.band_from_score(total)
        if eligible:
            # A durable trigger lifts the pair to whatever its ceiling allows; the
            # score never lifts it past `probable` on its own.
            band = max((band, ceiling or "confirmed"), key=protoconfig.BAND_ORDER.index)
        verdict = protoconfig.band_at_most(band, ceiling)

        parts = []
        if eligible:
            parts.append("durable confirm trigger(s): " + ", ".join(eligible))
        elif triggers:
            parts.append("trigger(s) " + ", ".join(triggers) +
                         " present but source-independence not met (" +
                         f"{independent_sources} distinct document(s))")
        else:
            parts.append("no durable confirm trigger, so fusion is unavailable regardless of score")
        parts.append("agreeing discriminators: " + (", ".join(agreeing) or "none"))
        parts.append(f"weighted total {round(total, self.round_digits)}")
        if lifted:
            parts.append("caps lifted by a composite identifier match: " +
                         ", ".join(sorted(n for n, _, _ in lifted)))
        if effective:
            parts.append("held at " + str(ceiling) + " by " +
                         ", ".join(sorted(n for n, _, _ in effective)))
        reason = "; ".join(parts) + "."

        return Verdict(
            a=a.instance_id, b=b.instance_id, verdict=verdict, signals=signals,
            ceiling=ceiling, ceiling_reason=ceiling_reason, walls=[], same_doc=same_doc,
            reason=reason, triggers=eligible, slot_states=states, composite=composite,
            caps_fired=[n for n, _, _ in effective], contrast=contrast,
        )

    def band_from_score(self, total: float) -> str:
        """The score decides the analyst queue, never a fusion — it tops out at
        `probable` by construction (D-13.20: the top rungs are shapes, not scores)."""
        if total >= float(self.bands["probable_floor"]):
            return "probable"
        if total >= float(self.bands["possible_floor"]):
            return "possible"
        return "separate"


def run_fixpoint(instances: list[Instance], cfg: dict, rarity, injected: set) -> tuple[list[Verdict], UnionFind]:
    """Monotone fixpoint: judge every pair, union the fused ones, repeat.

    Monotone because clusters only grow (walls are pairwise over stated values and
    do not depend on union state), so it terminates — the same argument
    ``resolve/cluster.py:6-9`` rests on. Iteration order is sorted, so the result
    is order-independent and byte-reproducible.
    """
    judge = Judge(cfg)
    ids = [i.instance_id for i in instances]
    uf = UnionFind(ids)
    by_id = {i.instance_id: i for i in instances}
    pairs = [(x, y) for k, x in enumerate(sorted(ids, key=_idkey))
             for y in sorted(ids, key=_idkey)[k + 1:]]
    verdicts: dict[tuple[str, str], Verdict] = {}
    changed = True
    while changed:
        changed = False
        for x, y in pairs:
            v = judge.judge(by_id[x], by_id[y], uf, rarity)
            verdicts[(x, y)] = v
            if v.verdict == "confirmed" and uf.union(x, y):
                changed = True
    out = [verdicts[p] for p in pairs]
    for v in out:
        v.injected = (v.a, v.b) in injected or (v.b, v.a) in injected
    return out, uf


def _idkey(instance_id: str) -> tuple:
    from characterize import natkey
    return natkey(instance_id)
