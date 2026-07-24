"""Derived edges and gaps — where the non-negotiable is mechanised.

**The D1 guard, and why it cannot be bypassed.** Defect D1 is a verified chain
from one identity over-merge to a *drawn, positively-asserted relocation with the
analyst removed from the loop*. Two properties here make that unreachable:

1. ``drawn`` is assigned in exactly **one** place — ``_drawable()`` at the top of
   ``relocation_edge()`` — from exactly one input (the subject identity status),
   compared against a config **status name** (``relocation.drawn_requires_identity_status``),
   not a score. There is no override argument and no second assignment, so no
   caller can produce a drawn edge by any other route.
2. The withheld branch constructs the edge **and** its gap in the same statement.
   A withheld relocation therefore cannot exist without a named, analyst-facing
   gap. ``run.py`` re-asserts both post-conditions on the finished output and
   raises if either is violated, so a violating document cannot even be written.

Everything else here is the "degrade to a named gap" surface: when the evidence
does not earn an assessment, something is *said* about what is missing, never
nothing.
"""

from __future__ import annotations

from characterize import Instance, natkey
from protoconfig import BAND_ORDER

# Analyst-facing labels for slot names. Labels, not policy — no thresholds here.
SLOT_LABEL = {
    "designation": "unit designation",
    "operator": "operating organisation",
    "geography": "location",
    "time": "observation date",
    "echelon": "echelon",
    "unique_id": "composite identifier",
}


def one_band_below(band: str) -> str:
    """The highest band reachable when `band` is out of reach.

    Derived from the contract's band order rather than configured, so a gap's
    ceiling can never drift out of step with the status it reports on.
    """
    index = BAND_ORDER.index(band)
    return BAND_ORDER[max(0, index - 1)]


def _drawable(status: str, cfg: dict) -> bool:
    """THE D1 GUARD. The only place `drawn` is decided."""
    return status == cfg["relocation"]["drawn_requires_identity_status"]


def _sentence(cfg: dict, kind: str, **fields) -> str:
    template = cfg["gaps"]["sentences"][kind]
    return template.format(**{k: ("unknown" if v in (None, "", []) else v)
                              for k, v in fields.items()})


def gap(cfg: dict, about: str, kind: str, missing: list[str], ceiling: str, **fields) -> dict:
    return {
        "about": about,
        "kind": kind,
        "missing": missing,
        "ceiling": ceiling,
        "sentence": _sentence(cfg, kind, about=about, missing=", ".join(missing) or "nothing",
                              ceiling=ceiling, **fields),
    }


def relocation_edge(cfg: dict, subject: str, frm: str, to: str, status: str,
                    missing: list[str], gaps: list[dict]) -> dict:
    """Emit a relocation, drawn only if the identity was earned.

    The withheld branch emits the gap in the same statement as the edge — that
    coupling is the structural guarantee, not a convention.
    """
    drawn = _drawable(status, cfg)
    if drawn:
        return {"kind": "relocation", "subject": subject, "from": frm, "to": to,
                "drawn": True, "withheld_reason": None}
    gaps.append(gap(cfg, subject, "relocation-unconfirmed", missing,
                    one_band_below(cfg["relocation"]["drawn_requires_identity_status"]),
                    frm=frm, to=to, status=f"identity {status}"))
    return {"kind": "relocation", "subject": subject, "from": frm, "to": to,
            "drawn": False, "withheld_reason": f"identity {status}"}


# --------------------------------------------------------------------------
# candidate detection
# --------------------------------------------------------------------------

def _dated(inst: Instance, predicates: set) -> list[tuple[str, str, str]]:
    return sorted((t, p, s) for p, s, t, pred in inst.placements
                  if t and pred in predicates)


def instance_relocation(inst: Instance, predicates: set) -> tuple[str, str] | None:
    """One instance already carrying a dated move between two places."""
    dated = _dated(inst, predicates)
    if len(dated) < 2 or dated[0][1] == dated[-1][1]:
        return None
    return dated[0][2], dated[-1][2]


def pair_relocation(a: Instance, b: Instance, predicates: set) -> tuple[str, str] | None:
    """A move that would only exist *if* the two instances were one referent.

    This is defect D1's exact shape: two co-located-or-nearby formation reports
    whose fusion turns two distinct site edges into one unit's before/after.
    Restricted to the **formation** citizen because that is the citizen whose
    basing edge is functional and therefore supersedes; a presence asserts only
    presence, so merging presences cannot manufacture a movement (spine/13 §6).
    """
    if a.citizen != "formation" or b.citizen != "formation":
        return None
    da, db = _dated(a, predicates), _dated(b, predicates)
    if not da or not db:
        return None
    if {p for _, p, _ in da} == {p for _, p, _ in db}:
        return None
    combined = sorted(da + db)
    if combined[0][1] == combined[-1][1]:
        return None
    return combined[0][2], combined[-1][2]


# --------------------------------------------------------------------------
# identity status
# --------------------------------------------------------------------------

def identity_status(inst: Instance, fused: set, cfg: dict) -> str:
    """`confirmed` only where the system actually earned the identity.

    Two routes, both explicit:
      * the instance fused with another instance — cross-source earned identity;
      * every placement belongs to **one source's own referent** (a single mention,
        or an authoritative, grade-passing, non-declined coref grouping), which is
        the source asserting a transition about its own referent (spine/13 §4/§5) —
        and only when the audit switch permits it.
    Anything else is `sub-confirmed` and withholds the edge.
    """
    if inst.instance_id in fused:
        return "confirmed"
    if cfg["relocation"]["allow_single_source_authoritative_identity"] and \
            (len(inst.member_keys) == 1 or inst.authoritative_atom):
        return "confirmed"
    return "sub-confirmed"


# --------------------------------------------------------------------------
# the whole derived surface
# --------------------------------------------------------------------------

def derive(cfg: dict, instances: list[Instance], verdicts: list, uf, notes: list[dict]) -> tuple[list[dict], list[dict]]:
    predicates = set(cfg["relocation"]["predicates"])
    gap_slots = list(cfg["discriminators"]["gap_on_unknown_slots"])
    by_id = {i.instance_id: i for i in instances}
    fused = {v.a for v in verdicts if v.verdict == "confirmed"} | \
            {v.b for v in verdicts if v.verdict == "confirmed"}
    edges: list[dict] = []
    gaps: list[dict] = []

    # -- Tier-0 grouping decisions that need an analyst -----------------------
    for note in sorted(notes, key=lambda n: (n["doc_id"], natkey(n["members"][0]))):
        about = ", ".join(f"{note['doc_id']}-{m}" for m in note["members"])
        if note["kind"] == "grouping-declined":
            gaps.append(gap(cfg, about, "grouping-declined", ["an analyst decision on the grouping"],
                            one_band_below("confirmed"), detail=note["detail"]))
        else:
            gaps.append(gap(cfg, about, "coref-held-loose",
                            ["a corroborating source, or an analyst decision"],
                            one_band_below("confirmed"),
                            detail=note["detail"], quote=note.get("quote") or "none recorded"))

    # -- per-instance: unstated critical discriminators -----------------------
    for inst in instances:
        if inst.citizen not in ("presence", "formation"):
            continue
        for slot in gap_slots:
            if inst.slots.get(slot):
                continue
            gaps.append(gap(cfg, inst.instance_id, "discriminator-unstated",
                            [SLOT_LABEL.get(slot, slot)], one_band_below("confirmed")))

    # -- per-pair: caps and untestable comparisons ---------------------------
    for v in verdicts:
        a, b = by_id[v.a], by_id[v.b]
        pair = f"{v.a} + {v.b}"
        missing = [SLOT_LABEL.get(s, s) for s in gap_slots
                   if not a.slots.get(s) or not b.slots.get(s)]
        if "co_location_formation" in v.caps_fired:
            geography = a.slots.get("geography") or b.slots.get("geography") or [("unstated",)*3]
            gaps.append(gap(cfg, pair, "formation-unresolved",
                            missing + ["a unit-level discriminator"], v.ceiling or "probable",
                            a=v.a, b=v.b, geography=geography[0][0]))
        if v.slot_states.get("operator") == "unnormalized":
            stated = sorted({s for s, _, _ in (a.slots.get("operator") or [])} |
                            {s for s, _, _ in (b.slots.get("operator") or [])})
            gaps.append(gap(cfg, pair, "operator-unnormalized",
                            ["an operator normalization rule"], one_band_below("confirmed"),
                            detail=", ".join(repr(s) for s in stated)))
        if v.contrast and v.composite == "match":
            gaps.append(gap(cfg, pair, "contrast-vs-identifier",
                            ["an analyst decision on a self-contradictory source"],
                            one_band_below("confirmed"), a=v.a, b=v.b))

    # -- per-site: candidate formation count (R2.1 — never a silent pick) ----
    sites: dict[str, list[str]] = {}
    for inst in instances:
        if inst.citizen != "formation":
            continue
        for canon, stated, _t, pred in inst.placements:
            if pred in predicates:
                sites.setdefault(stated, []).append(inst.instance_id)
    for stated in sorted(sites):
        roots = {uf.find(i) for i in sites[stated]}
        if len(roots) < 2:
            continue
        candidates = sorted(set(sites[stated]), key=natkey)
        missing = sorted({SLOT_LABEL.get(s, s) for i in candidates for s in gap_slots
                          if not by_id[i].slots.get(s)})
        gaps.append(gap(cfg, ", ".join(candidates), "formation-count-unresolved",
                        missing or ["independent corroboration of identity"],
                        one_band_below("confirmed"), geography=stated, n=len(roots)))

    # -- relocations ---------------------------------------------------------
    for inst in instances:
        move = instance_relocation(inst, predicates)
        if move is None:
            continue
        status = identity_status(inst, fused, cfg)
        edges.append(relocation_edge(cfg, inst.instance_id, move[0], move[1], status,
                                     ["a unit-level discriminator or analyst confirmation"], gaps))
    for v in verdicts:
        if v.walls:
            continue
        a, b = by_id[v.a], by_id[v.b]
        move = pair_relocation(a, b, predicates)
        if move is None:
            continue
        status = "confirmed" if v.verdict == "confirmed" else "sub-confirmed"
        missing = [SLOT_LABEL.get(s, s) for s in gap_slots
                   if not a.slots.get(s) or not b.slots.get(s)] or \
                  ["independent corroboration of identity"]
        edges.append(relocation_edge(cfg, f"{v.a} + {v.b}", move[0], move[1], status,
                                     missing, gaps))

    edges.sort(key=lambda e: (e["kind"], natkey(e["subject"]), e["from"], e["to"]))
    gaps.sort(key=lambda g: (g["kind"], natkey(g["about"]), tuple(g["missing"])))
    return edges, gaps
