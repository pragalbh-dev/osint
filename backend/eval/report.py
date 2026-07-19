"""The acceptance report — a legible pass/fail artifact for the call (markdown + JSON).

The harness + checks produce a flat list of :class:`CheckResult` (one per spine-gate criterion, demo flex,
ground-truth assertion, and the rebuttal) plus a node/edge :class:`StatusDiffRow` table (expected vs
computed status). This module renders them; it holds no assertion logic itself, so the same results back
both the pytest suite (``tests/acceptance``) and the human-readable report (``python -m eval``).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class CheckResult:
    """One graded assertion: did the merged pipeline produce what the brief is graded on?

    ``category`` groups the report (spine-gate · flex · ground-truth · document · rebuttal); ``detail``
    carries the human-legible why (expected vs got), shown on failure and, for headline beats, on pass.
    """

    name: str
    passed: bool
    category: str
    detail: str = ""


@dataclass(frozen=True)
class StatusDiffRow:
    """Expected vs computed status for one node/edge — the status-diff table shown on the call."""

    element: str
    kind: str  # "node" | "edge"
    expected: str
    computed: str

    @property
    def match(self) -> bool:
        return self.expected == self.computed


@dataclass
class AcceptanceReport:
    """The full acceptance result: grouped checks + the status-diff table + run metadata."""

    checks: list[CheckResult] = field(default_factory=list)
    status_diff: list[StatusDiffRow] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    # ── rendering ───────────────────────────────────────────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "summary": self._summary(),
            "meta": self.meta,
            "checks": [asdict(c) for c in self.checks],
            "status_diff": [
                {**asdict(r), "match": r.match} for r in self.status_diff
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    def _summary(self) -> dict:
        cats: dict[str, dict[str, int]] = {}
        for c in self.checks:
            bucket = cats.setdefault(c.category, {"passed": 0, "total": 0})
            bucket["total"] += 1
            bucket["passed"] += int(c.passed)
        return {
            "passed": sum(c.passed for c in self.checks),
            "total": len(self.checks),
            "by_category": cats,
            "status_diff_matches": sum(r.match for r in self.status_diff),
            "status_diff_total": len(self.status_diff),
        }

    def to_markdown(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        s = self._summary()
        lines: list[str] = [
            f"# Acceptance report — {self.meta.get('scenario', '?')}  ·  **{mark}**",
            "",
            f"_{s['passed']}/{s['total']} checks green · "
            f"{s['status_diff_matches']}/{s['status_diff_total']} statuses match · "
            f"{self.meta.get('claim_count', '?')} claims · {self.meta.get('node_count', '?')} nodes · "
            f"{self.meta.get('edge_count', '?')} edges_",
            "",
        ]
        # grouped checks, spine-gate + flexes first (the headline beats)
        order = ["spine-gate", "flex", "rebuttal", "ground-truth", "document"]
        cats = sorted(
            {c.category for c in self.checks},
            key=lambda x: (order.index(x) if x in order else len(order), x),
        )
        for cat in cats:
            b = s["by_category"][cat]
            lines.append(f"## {cat}  ({b['passed']}/{b['total']})")
            lines.append("")
            for c in [c for c in self.checks if c.category == cat]:
                icon = "✅" if c.passed else "❌"
                detail = f" — {c.detail}" if c.detail else ""
                lines.append(f"- {icon} **{c.name}**{detail}")
            lines.append("")
        # status-diff table
        if self.status_diff:
            lines += ["## status diff (expected vs computed)", "",
                      "| element | kind | expected | computed | |",
                      "|---|---|---|---|---|"]
            for r in sorted(self.status_diff, key=lambda r: (r.kind, r.element)):
                icon = "✅" if r.match else "❌"
                lines.append(f"| `{r.element}` | {r.kind} | {r.expected} | {r.computed} | {icon} |")
            lines.append("")
        return "\n".join(lines)
