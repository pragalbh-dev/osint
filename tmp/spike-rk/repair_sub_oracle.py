#!/usr/bin/env python3
"""RK-BAKEOFF sub-oracle repair (2026-07-25) — single-source confirms capped at `probable`.

Directive: tmp/conv/FOR-DATA-C-sub-oracle-single-source-confirm.md (user-ratified 2026-07-25).
Running rule enforced: config/credibility.yaml `min_independent_groups: 2`, applied in
backend/chanakya/credibility/status.py::assign_status against _effective_looks(groups).

Idempotent-ish: asserts every string it replaces in the .md is found exactly once, so a second run
fails loudly rather than silently drifting the two artifacts apart.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
GOLD = ROOT / "tmp" / "spike-rk" / "gold"
JSON_PATH = GOLD / "sub-oracle.json"
MD_PATH = GOLD / "sub-oracle.md"

CAP = (
    "**Capped at `probable` (2026-07-25).** The supporting evidence all sits in ONE document, "
    "which is ONE independent look. The running rule — `config/credibility.yaml` "
    "`min_independent_groups: 2`, enforced in `credibility/status.py::assign_status` — makes "
    "`confirmed` unreachable on a single look regardless of how good that look is. A yardstick that "
    "confirmed here would be more confident than the system it grades."
)

IDENTIFIER_NOTE = (
    "The identifier evidence here is qualitatively the strongest anti-identity/identity signal in the "
    "slice, and it is the case with the best argument for an identifier-licensed bypass of the "
    "two-look rule. That bypass was considered and REFUSED on 2026-07-25 (see `DECISIONS.md`, "
    "\"Identifier-licensed identity does NOT bypass the two-look rule\"): no such rule exists in the "
    "running resolver, so putting one in the yardstick would invert the measurement."
)

# ── (a) the twelve single-source entries ────────────────────────────────────────────────────────
CAPPED: dict[str, dict[str, str | None]] = {
    "sl_org_orient": {
        "proposition": "as an entity (that this filer exists and is one filer), NOT as a supply-chain actor",
        "why": (
            "A customs declaration is the primary record of its own filing, and this entity carries TWO "
            "registry identifiers (NTN 3298761-4, SECP CUIN 0087762) plus an address; the rename is stated "
            "with its registry reference. That is strong identity evidence — and it is all one document. "
            + CAP
        ),
        "missing": (
            "A second, independent look at this entity — a registry extract, a filing in another document, "
            "any non-customs source. Also its role in any military supply chain: **nothing in the slice "
            "states it.**"
        ),
    },
    "sl_org_sinogalaxy": {
        "proposition": "as an entity (that this shipper exists and is one shipper)",
        "why": (
            "Shipper of record on three declarations, with a 'see also' equivalence and a shared invoice "
            "number tying two surfaces together, plus a matching email domain — but all three declarations "
            "are lines of ONE customs extract, i.e. one look, not three. " + CAP
        ),
        "missing": (
            "A second, independent source on this entity. Also whether it manufactures anything (it is a "
            "trading/IMP-EXP entity by its own name)."
        ),
    },
    "sl_org_alnoor": {
        "proposition": "as an entity (that this forwarder exists)",
        "why": (
            "Freight forwarder of record on two declarations with an AEO certificate number (PK-AEO-0231) "
            "— an identifier-backed entity, in a single primary record. " + CAP
        ),
        "missing": (
            "A second, independent source on this entity. Also any connection to the subject beyond "
            "forwarding these consignments."
        ),
    },
    "sl_event_118834": {
        "proposition": "that the declaration exists — NOT that its goods are as described",
        "why": (
            "A customs GD extract is the primary record of the declaration; the GD and B/L numbers are its "
            "identity. One document, therefore one look. " + CAP
        ),
        "missing": (
            "A second, independent look at this declaration. And what was actually in it: the stated "
            "description is a CIVIL end-use ('FOR INDUSTRIAL NAVIGATION AID'), the end-user certificate is "
            "not attached, and no physical exam is recorded for this line."
        ),
    },
    "sl_event_118835": {
        "proposition": "that the declaration exists — NOT that its goods are as described",
        "why": "As 118834: one primary record, one independent look. " + CAP,
        "missing": (
            "A second, independent look. And its contents beyond the filed description — the Annex A "
            "line-item detail is present but the scan is explicitly 'poor' and one designator is truncated."
        ),
    },
    "sl_event_119011": {
        "proposition": "that the declaration exists — NOT that its goods are as described",
        "why": (
            "As 118834. Different vessel, line, container and date — but the same single source document. "
            + CAP
        ),
        "missing": (
            "A second, independent look. And its contents: no physical examination was performed "
            "(GREEN CHANNEL)."
        ),
    },
    "sl_e11": {
        "proposition": "as a NEGATIVE observation for the 2025-06-11 pass window",
        "why": (
            "d17b (satellite/B) looked for TELs, tarped TEL-sized objects, staging and generator trailers, "
            "and reports none of them, with the cloud fraction and the confidence-by-segment stated. A "
            "well-scoped negative from a grade-B source is strong evidence *for the window it covers* — but "
            "it is a single collection pass in a single document. " + CAP + " Independently of the look "
            "count, single-pass imagery is capped at `probable` by the running decoy-risk gate "
            "(`config/credibility.yaml` `gates.decoy_risk.cap_at_probable`), so `probable` is the correct "
            "ceiling here twice over."
        ),
        "missing": (
            "A second pass, or any non-IMINT look at the same window. For the broader question 'is the site "
            "vacated' the document itself names the residual: dispersal, maintenance rotation to an "
            "unobserved facility, or a collection-timing gap. Next coverage: 5-7 days from 2025-06-11."
        ),
    },
    "sl_e15": {
        "proposition": None,
        "why": (
            "Two distinct GD numbers and two distinct B/L numbers in a primary record, plus the document's "
            "own cross-reference treating them as separate lines. Identifier-level anti-identity is the "
            "strongest form available — and it is stated once, in one document. " + CAP
        ),
        "missing": "A second, independent record distinguishing the two declarations.",
    },
    "sl_e16": {
        "proposition": None,
        "why": (
            "Distinct GD/B/L, different vessel, line, container and date — all read off one document. " + CAP
        ),
        "missing": "A second, independent record distinguishing the two declarations.",
    },
    "sl_e17": {
        "proposition": None,
        "why": "As sl_e16: identifier-level anti-identity, stated once in one document. " + CAP,
        "missing": "A second, independent record distinguishing the two declarations.",
    },
    "sl_e20": {
        "proposition": None,
        "why": (
            "A corporate-registry rename cited with its identifier (SECP CUIN 0087762, 2019) in a primary "
            "customs record. One document, one look. " + CAP
        ),
        "missing": (
            "A second, independent source on the rename — an SECP registry extract, or the new name "
            "appearing in any other document."
        ),
    },
    "sl_e21": {
        "proposition": None,
        "why": (
            "An explicit 'see also' plus a shared invoice reference (#SG-20-4471) in a primary record. One "
            "document, one look. " + CAP
        ),
        "missing": "A second, independent source binding the two shipper surfaces.",
    },
}

EXTRA_NOTE = {
    "sl_e15": IDENTIFIER_NOTE,
    "sl_e16": IDENTIFIER_NOTE,
    "sl_e17": IDENTIFIER_NOTE,
    "sl_e20": IDENTIFIER_NOTE,
    "sl_e21": IDENTIFIER_NOTE,
    "sl_org_orient": IDENTIFIER_NOTE,
}

# ── qualified statuses that were NOT single-source: split status from proposition, value unchanged ──
REPHRASE: dict[str, tuple[str, str]] = {
    "sl_family_hq9": ("confirmed", "as a family label — not as a fielded variant"),
    "sl_unit_paad": ("insufficient-evidence", "for a formation IDENTITY"),
    "sl_gap_tel_count": ("confirmed", "the gap is real"),
    "sl_gap_designation": ("confirmed", "the gap is real, and it is corpus-wide"),
    "sl_gap_ht233_maker": ("confirmed", "the gap is real, on this slice"),
    "sl_areas": ("probable", "as areas"),
}

# ── (c) the mis-cited alias entry ───────────────────────────────────────────────────────────────
E03 = {
    "supporting_rows": ["d04-r02"],
    "status": "probable",
    "why": (
        "ONE source states it, and states it cleanly: d04 (trade-media/C) — 'some regional trade reporting "
        "still uses HQ-9P' (`d04-r02`), an unhedged explicit equivalence at variant level. One independent "
        "look, so `probable`. " + CAP
    ),
    "missing": (
        "A second, independent source treating the slash and no-slash forms as one designator — and a "
        "resolution of the transitive counter-evidence recorded as `sl_amb_07`."
    ),
    "notes": (
        "**Citation repaired 2026-07-25.** This entry previously claimed `confirmed` on 'three independent "
        "sources' while citing four rows, only one of which supports the proposition. Dropped: `d02-r07` "
        "(a FAMILY-level parenthetical, 'the Chinese Hongqi-9 (HQ-9P/FD-2000 family)' — and it is the "
        "FD-2000 row, not an HQ-9/P≡HQ-9P statement) and `cs01-r01` (an `ATTR:family` row that does not "
        "contain the string 'HQ-9P' as a separate designator at all). Moved to the tension list: "
        "`d19-r09`, which is COUNTER-evidence rather than support — it asserts HQ-9BE ≡ HQ-9P, which "
        "together with `d04-r07` (HQ-9/P distinct-from HQ-9BE) entails HQ-9/P ≢ HQ-9P, the OPPOSITE "
        "equivalence. It is **not** being overridden; it is held as a live contradiction (`sl_amb_07`)."
    ),
}

AMB_07 = {
    "amb_id": "sl_amb_07",
    "title": "HQ-9/P ≡ HQ-9P (d04) vs the transitive denial of it via HQ-9BE (d19 + d04)",
    "rows": ["d04-r02", "d19-r09", "d04-r07"],
    "verdict": "probable same-as, with a live transitive contradiction that must be surfaced, not resolved",
    "detail": (
        "d04 states HQ-9/P and HQ-9P are the same designator rendered two ways (`d04-r02`, unhedged). d19 "
        "states HQ-9BE is 'sometimes rendered HQ-9P in Pakistani service literature' (`d19-r09`, hedged, "
        "and disclaimed by d19 itself at L19). d04 also states HQ-9/P and HQ-9BE are DISTINCT systems "
        "(`d04-r07`, hedged: 'appear to be genuinely separate procurement lines'). Chain the second and "
        "third and you get HQ-9/P ≢ HQ-9P — the negation of the first. All three rows are in the slice; "
        "none can be preferred on grade alone (C-that-argues vs B-that-disclaims-itself). Missing: an "
        "authoritative designator mapping. Faithful behaviour: keep the alias as `probable` and surface "
        "the transitive conflict for an analyst — never silently merge, never silently wall. Moved here "
        "on 2026-07-25 from `sl_e03`'s supporting rows, where it had been counted as SUPPORT."
    ),
}

REPAIR_LOG = [
    {
        "date": "2026-07-25",
        "by": "DATA hand (RK-BAKEOFF)",
        "directive": "tmp/conv/FOR-DATA-C-sub-oracle-single-source-confirm.md (user-ratified)",
        "change": (
            "Capped all TWELVE single-source entries at `probable`. Measured count: 12 entries rest on "
            "exactly one slice document — 5 carrying a bare `confirmed` (sl_e15/16/17/20/21) and 7 "
            "carrying a QUALIFIED confirm (sl_org_orient, sl_org_sinogalaxy, sl_org_alnoor as "
            "'confirmed (as an entity)'; sl_event_118834/118835/119011 as 'confirmed (that the "
            "declaration exists)'; sl_e11 as 'confirmed as a NEGATIVE observation …')."
        ),
        "ruling_on_qualified_confirms": (
            "A qualified confirm IS a status claim and IS subject to the cap. The parenthetical narrows "
            "the PROPOSITION being asserted, not the STATUS asserted about it — and narrowing a "
            "proposition does not buy a second independent look. Structurally it is also unsafe: the "
            "declared vocabulary has exactly four values, any scorer normalising `status` will read a "
            "leading 'confirmed' as `confirmed`, and a free-text status silently escapes the very rule the "
            "yardstick exists to hold. So the qualifier has been MOVED into a new "
            "`status_proposition` field (its analytic content is preserved verbatim) and `status` now "
            "always holds one of the four vocabulary values."
        ),
        "bypass_ruling": (
            "The identifier-licensed bypass floated in the directive (a shared unique identifier inside "
            "one primary record) was considered and REFUSED. Rationale and scope recorded in DECISIONS.md "
            "under 'Identifier-licensed identity does NOT bypass the two-look rule (2026-07-25)'. Absent "
            "that entry the cap applies; the entry exists and it declines the bypass, so the cap applies."
        ),
        "alias_fix": (
            "sl_e03 re-cited on `d04-r02` alone; `d02-r07` and `cs01-r01` dropped as non-supporting; "
            "`d19-r09` moved to the tension list as `sl_amb_07` (counter-evidence, explicitly NOT "
            "overridden)."
        ),
        "not_changed": (
            "Independence DETECTION was not re-keyed (deferred defect D11). The flagship Rahwali confirm "
            "was not demoted — it is mechanically two independent looks."
        ),
    }
]


def main() -> int:
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    md = MD_PATH.read_text(encoding="utf-8")
    entries = {}
    for e in data["nodes"]:
        entries[e["node_id"]] = e
    for e in data["edges"]:
        entries[e["edge_id"]] = e

    def _section_bounds(eid: str) -> tuple[int, int]:
        marker = f"\n### `{eid}`"
        start = md.find(marker)
        if start < 0:
            raise SystemExit(f"MD section for {eid} not found")
        nxt = md.find("\n### ", start + 1)
        end = nxt if nxt >= 0 else len(md)
        return start, end

    def md_sub(old: str, new: str, label: str, scope: str | None = None) -> None:
        """Exact replacement, optionally scoped to one entry's `### \\`eid\\`` section."""
        nonlocal md
        lo, hi = _section_bounds(scope) if scope else (0, len(md))
        seg = md[lo:hi]
        n = seg.count(old)
        if n != 1:
            raise SystemExit(
                f"MD replacement for {label} matched {n} times in scope {scope!r}, expected 1:\n"
                f"  {old[:160]!r}"
            )
        md = md[:lo] + seg.replace(old, new) + md[hi:]

    # give every entry the new fields up front (stable schema across all rows)
    for e in entries.values():
        e.setdefault("status_proposition", None)

    # --- (a) the cap ---------------------------------------------------------------------------
    for eid, spec in CAPPED.items():
        e = entries[eid]
        old_status = e["status"]
        md_sub(
            f"**Honest status on this slice: `{old_status}`**",
            "**Honest status on this slice: `probable`**"
            + (f" *(status attaches to: {spec['proposition']})*" if spec["proposition"] else ""),
            f"{eid} status",
            scope=eid,
        )
        md_sub(
            f"**Why that status.** {e['why']}",
            f"**Why that status.** {spec['why']}",
            f"{eid} why",
            scope=eid,
        )
        if e.get("missing"):
            md_sub(
                f"**What is missing.** {e['missing']}",
                f"**What is missing.** {spec['missing']}",
                f"{eid} missing",
                scope=eid,
            )
        else:
            # no existing "What is missing" paragraph — insert one after the why paragraph
            anchor = f"**Why that status.** {spec['why']}\n"
            md_sub(
                anchor,
                anchor + f"\n**What is missing.** {spec['missing']}\n",
                f"{eid} missing-insert",
                scope=eid,
            )
        if eid in EXTRA_NOTE:
            note = EXTRA_NOTE[eid]
            e["notes"] = (e.get("notes") + "\n\n" + note) if e.get("notes") else note
            anchor = f"**What is missing.** {spec['missing']}\n"
            md_sub(anchor, anchor + f"\n{note}\n", f"{eid} note-insert", scope=eid)
        e["status"] = "probable"
        e["status_proposition"] = spec["proposition"]
        e["why"] = spec["why"]
        e["missing"] = spec["missing"]

    # --- qualified-but-multi-source statuses: split value from proposition ----------------------
    for eid, (value, prop) in REPHRASE.items():
        e = entries[eid]
        md_sub(
            f"**Honest status on this slice: `{e['status']}`**",
            f"**Honest status on this slice: `{value}`** *(status attaches to: {prop})*",
            f"{eid} status-rephrase",
            scope=eid,
        )
        e["status"] = value
        e["status_proposition"] = prop

    # --- (c) the alias entry -------------------------------------------------------------------
    e = entries["sl_e03"]
    md_sub(
        "**Basis:** stated · **Honest status on this slice: `confirmed`**\n\n"
        "Supporting rows: `d04-r02`, `d02-r07`, `d19-r09`, `cs01-r01`\n\n"
        f"**Why that status.** {e['why']}\n",
        "**Basis:** stated · **Honest status on this slice: `probable`**\n\n"
        "Supporting rows: `d04-r02`\n\n"
        f"**Why that status.** {E03['why']}\n\n"
        f"**What is missing.** {E03['missing']}\n\n"
        f"{E03['notes']}\n",
        "sl_e03 block",
        scope="sl_e03",
    )
    e.update(E03)

    # --- the new tension entry -----------------------------------------------------------------
    if any(a["amb_id"] == "sl_amb_07" for a in data["flagged_ambiguities"]):
        raise SystemExit("sl_amb_07 already present — refusing to duplicate")
    data["flagged_ambiguities"].append(AMB_07)
    md_sub(
        "\n---\n\n## Where this sub-oracle differs from",
        f"\n### `{AMB_07['amb_id']}` — {AMB_07['title']}\n\n"
        f"**Verdict: `{AMB_07['verdict']}`** · rows: `{'`, `'.join(AMB_07['rows'])}`\n\n"
        f"{AMB_07['detail']}\n"
        "\n---\n\n## Where this sub-oracle differs from",
        "amb_07 md block",
    )

    # --- bookkeeping ---------------------------------------------------------------------------
    data["schema_version"] = "rk-spike-sub-oracle/1.1"
    data["counts"]["flagged_ambiguities"] = len(data["flagged_ambiguities"])
    data["status_field_note"] = (
        "`status` holds exactly one of `status_values` — never a free-text qualification. Where the "
        "status attaches to a NARROWED proposition, that narrowing lives in `status_proposition` and is "
        "part of the claim, not part of the label. Added 2026-07-25 with the single-source cap."
    )
    data["repair_log"] = REPAIR_LOG
    data["counts_note"] = data["counts_note"].replace(
        "6 flagged ambiguities", f"{len(data['flagged_ambiguities'])} flagged ambiguities"
    )

    md_sub(
        "**Status semantics used below.**",
        "**Repaired 2026-07-25 (`schema_version` → `rk-spike-sub-oracle/1.1`).** Every entry resting on a "
        "single slice document is capped at `probable`: `config/credibility.yaml` sets "
        "`min_independent_groups: 2`, so one look cannot reach `confirmed` however hard its identifier is. "
        "Qualified confirms (\"confirmed (as an entity)\") were rulings on a NARROWED proposition, not a "
        "different status, so they are capped too — the narrowing now lives in `status_proposition` and "
        "`status` always holds a vocabulary value. `sl_e03` was re-cited on the one row that supports it "
        "and its counter-evidence moved to `sl_amb_07`. Full record in `repair_log`.\n\n"
        "**Status semantics used below.**",
        "md preamble",
    )
    md_sub(
        "· 6 flagged ambiguities.",
        f"· {len(data['flagged_ambiguities'])} flagged ambiguities.",
        "md counts",
    )

    JSON_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    MD_PATH.write_text(md, encoding="utf-8")
    print("repaired", JSON_PATH, MD_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
