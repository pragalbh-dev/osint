"""The bake-off driver — the caller :func:`eval.extraction.runner.run_bakeoff` never had.

``run_bakeoff`` is a library entry point that deliberately refuses to default its inputs: the labeled
files come from the data hand, and a CLI that silently substituted something else would print a number
for a comparison that did not happen. This module supplies those inputs *honestly* — every one of them
derived from a declared artefact rather than typed in here — and nothing else:

* **the document slice comes from the gold itself.** The adapted gold declares which documents it labels
  (``docs`` + ``doc_paths``), so :func:`build_slice` reads the slice off the answer file rather than a
  hard-coded list. A document the gold does not label cannot silently enter the comparison, and a document
  the gold labels cannot silently leave it — which is the failure mode that makes a recall number a lie.
* **every document's source type comes from the pipeline's own source registry**, not from a mapping
  invented here, and its co-located frames come from the registry's ``images``. That is what puts the real
  corpus image in front of every candidate: ``d17b_withheld_gap`` is registered with
  ``d17b_withheld_gap.png`` beside it, so the imagery lane fires on a real frame through the real lane. It
  matters that this is not a special case bolted onto the driver — the seed recorder loads the same
  registry the same way (``chanakya.ingest.seed._extract_source``), so what the bake-off shows a model is
  what the pipeline shows it.
* **the spend is stated before it is incurred.** :class:`SpendPlan` is printed first, every time, and it
  reports a floor and a ceiling rather than one confident number, because one of the three call classes is
  genuinely conditional (see below). A driver that printed a single estimate would be wrong in one
  direction or the other and would teach an operator to ignore it.

WHAT A RUN COSTS, AND WHY IT IS A RANGE
───────────────────────────────────────
Per document, per run, per candidate:

* **pass 1** — exactly one text-lane call per text document. There is no chunking on this path, and the
  slice's documents are 3–5 KB, so this is one call and not "one or more".
* **the imagery lane** — one standalone-image call per co-located frame. Unconditional.
* **pass 2 (coreference)** — *at most* one further call per text document, and this is the conditional
  one: :func:`chanakya.ingest.coref.propose_coreference` returns without calling anything when pass 1
  yielded fewer than two mentions, so a document a candidate reads poorly costs less than one it reads
  well. Cheapness here is a symptom of a weak extraction, never a saving.

So the floor assumes pass 2 never dispatches and the ceiling assumes it always does. The truth is in
between and is reported exactly by ``--dry-run``, which walks the identical path with a scripted client.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chanakya import settings
from chanakya.ingest import coref
from chanakya.ingest.lane import DocInput
from chanakya.schemas import ConfigBundle

_IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The document slice — read off the gold, resolved through the source registry.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

def _resolve(path: str) -> Path:
    """The on-disk path a repo-relative reference names (the convention ``citation_url`` already uses)."""
    p = Path(path)
    return p if p.is_absolute() else settings.repo_root() / p


def build_slice(gold_path: Path | str, bundle: ConfigBundle) -> list[DocInput]:
    """The documents the gold labels, as the ingest lane's own input type.

    ``file`` is set to the **repo-relative path**, which is the same string the gold cites and the same
    convention ``SourceRegistryEntry.citation_url`` uses. That alignment is load-bearing: the negative
    gold's span hooks match an emitted claim's ``file`` against the gold's, so a driver that put a bare
    basename or an absolute path here would silently match nothing — and "nothing excluded, no traps hit"
    is indistinguishable from a clean run. (:mod:`.negative_gold` also translates by file name for exactly
    this reason; this keeps it from having to.)

    Raises rather than skipping when a labeled document is absent from the registry or from disk. A slice
    quietly one document short would understate recall for every candidate equally and invisibly.
    """
    payload = json.loads(Path(gold_path).read_text(encoding="utf-8"))
    doc_ids: list[str] = list(payload.get("docs") or [])
    doc_paths: dict[str, str] = dict(payload.get("doc_paths") or {})
    if not doc_ids:
        raise ValueError(
            f"{gold_path} declares no documents, so there is no slice to run. The bake-off's document set "
            "is the gold's own `docs` list; it is never defaulted here."
        )

    registry = bundle.sources.as_map()
    docs: list[DocInput] = []
    for doc_id in doc_ids:
        entry = registry.get(doc_id)
        if entry is None:
            raise ValueError(
                f"the gold labels document {doc_id!r} but it is not in the pipeline's source registry, so "
                "its source type and any co-located frames are unknown. Refusing to guess a source type: "
                "it selects the extraction tool, so guessing it would measure the guess."
            )
        rel = doc_paths.get(doc_id) or entry.citation_url or ""
        path = _resolve(rel)
        if not path.exists():
            raise FileNotFoundError(f"labeled document {doc_id!r} is missing from disk at {path}")

        raw: str | bytes
        if path.suffix.lower() in _IMAGE_SUFFIXES:
            raw = path.read_bytes()
        else:
            raw = path.read_text(encoding="utf-8")

        images: list[tuple[bytes, str]] = []
        for image_rel in entry.images:
            image_path = _resolve(image_rel)
            if not image_path.exists():
                raise FileNotFoundError(
                    f"{doc_id!r} registers a co-located frame at {image_path} which is missing. The "
                    "imagery gate is judged on a real image call, so a missing frame would read as "
                    "UNKNOWN and disqualify every candidate."
                )
            images.append((image_path.read_bytes(), image_rel))

        docs.append(DocInput(
            raw=raw, source_id=entry.source_id, source_type=entry.source_type, file=rel,
            images=tuple(images),
        ))
    return docs


def image_frames(docs: list[DocInput]) -> list[str]:
    """Every standalone-image call the slice will make — the imagery gate's whole basis."""
    frames = [f for doc in docs for _, f in doc.images]
    frames += [doc.file for doc in docs if Path(doc.file).suffix.lower() in _IMAGE_SUFFIXES]
    return frames


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The spend plan — printed before anything is spent.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LanePlan:
    """One candidate's lane: its provider's declared pacing and the wall-clock floor that imposes.

    A lane, not a run, because that is the unit pacing applies to. Each candidate holds its own limiter,
    so a provider capped at 3 requests a minute makes its OWN lane long and leaves the others at full
    speed — and the run's wall-clock is therefore the *slowest* lane, not the sum of them.
    """

    candidate_id: str
    provider: str
    limit: Any
    calls_floor: int
    calls_ceiling: int

    def seconds_floor(self) -> float:
        from .throttle import projected_seconds

        return projected_seconds(self.limit, self.calls_floor, concurrency=1)

    def seconds_ceiling(self) -> float:
        from .throttle import projected_seconds

        return projected_seconds(self.limit, self.calls_ceiling, concurrency=1)


def _hms(seconds: float) -> str:
    if seconds <= 0:
        return "—"
    minutes, sec = divmod(int(round(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m" if hours else f"{minutes}m{sec:02d}s"


@dataclass(frozen=True)
class SpendPlan:
    """Exactly what a run is about to cost, as a floor and a ceiling. See the module docstring."""

    candidates: tuple[str, ...]
    text_docs: int
    frames: tuple[str, ...]
    runs_per_candidate: int
    coref_pass: bool
    dry: bool
    #: Per-candidate pacing, so the plan states wall-clock as well as call count. Empty = nothing paced.
    lanes: tuple[LanePlan, ...] = ()

    @property
    def calls_per_run_floor(self) -> int:
        return self.text_docs + len(self.frames)

    @property
    def calls_per_run_ceiling(self) -> int:
        return self.calls_per_run_floor + (self.text_docs if self.coref_pass else 0)

    @property
    def total_floor(self) -> int:
        return self.calls_per_run_floor * self.runs_per_candidate * len(self.candidates)

    @property
    def total_ceiling(self) -> int:
        return self.calls_per_run_ceiling * self.runs_per_candidate * len(self.candidates)

    def render(self) -> str:
        n = len(self.candidates)
        head = "DRY RUN — scripted client, ZERO API calls" if self.dry else "LIVE RUN — THIS SPENDS BUDGET"
        lines = [
            f"── {head} ──",
            f"  candidates ({n}): {', '.join(self.candidates) or '(none)'}",
            f"  documents:  {self.text_docs} text + {len(self.frames)} standalone image frame(s)",
        ]
        for frame in self.frames:
            lines.append(f"      image: {frame}")
        lines += [
            f"  runs:       {self.runs_per_candidate} per candidate",
            f"  passes:     pass 1 (text) {'+ pass 2 (coreference)' if self.coref_pass else 'only'}"
            + ("" if self.coref_pass else "  — coref channel OFF, coref_binding will be UNMEASURED"),
            "",
            f"  calls per run:  {self.calls_per_run_floor} – {self.calls_per_run_ceiling}",
            f"  TOTAL CALLS:    {self.total_floor} – {self.total_ceiling}"
            f"   ({self.calls_per_run_floor}–{self.calls_per_run_ceiling}"
            f" x {self.runs_per_candidate} runs x {n} candidate(s))",
        ]
        if self.coref_pass:
            lines.append("  the range is pass 2: it does not dispatch on a document that yielded fewer "
                         "than two mentions,")
            lines.append("  so a candidate that reads a document poorly costs less for it. --dry-run "
                         "reports the exact count.")
        if self.lanes:
            lines.append("")
            lines.append("  per-provider pacing (config/bakeoff.yaml -> rate_limits), and the WALL-CLOCK")
            lines.append("  FLOOR it imposes on each lane. Lanes run concurrently, so the run takes the")
            lines.append("  SLOWEST lane, not the sum:")
            for lane in self.lanes:
                paced = lane.limit.describe(lane.provider)
                floor, ceiling = lane.seconds_floor(), lane.seconds_ceiling()
                window = (f"  >= {_hms(floor)}–{_hms(ceiling)} of pacing alone"
                          if ceiling > 0 else "  no pacing delay")
                lines.append(f"      {lane.candidate_id}: {paced}")
                lines.append(f"          {lane.calls_floor}–{lane.calls_ceiling} calls,{window}")
            worst = max((lane.seconds_ceiling() for lane in self.lanes), default=0.0)
            if worst > 0:
                lines.append(f"      RUN WALL-CLOCK FLOOR (slowest lane, pacing only, provider latency "
                             f"on top): {_hms(worst)}")
        if self.dry:
            lines.append("  nothing is billed: no key is read and no client is built.")
        return "\n".join(lines)


def blocked_before_spending(
    config: Any, *, candidate_ids: list[str], evidence: Any = None, require_key: bool = True,
) -> dict[str, str]:
    """``candidate id -> why`` for every candidate already disqualified on a gate judged without a run.

    A gate is pass/fail to win, so a candidate that fails one cannot be named winner at any score, and
    every call spent on it buys nothing that can change the outcome. On the shipped config that is a third
    of the budget. UNKNOWN counts as blocked here for the same reason it blocks everywhere else: an
    unverified precondition is not a satisfied one.

    Deliberately reuses :func:`eval.extraction.gates.dry_gates` — the exact function ``preflight`` prints —
    so the driver can never skip a candidate preflight called fine, or spend on one it called blocked.
    """
    from .gates import dry_gates
    from .vlm_probe import observations_for

    out: dict[str, str] = {}
    for candidate in config.candidates:
        if candidate.id not in candidate_ids:
            continue
        imagery, _ = observations_for(candidate, evidence=evidence)
        report = dry_gates(candidate, config, imagery=imagery, require_key=require_key)
        failing = [g for g in report.gates if g.status != "PASS"]
        if failing:
            out[candidate.id] = "; ".join(f"{g.status} {g.name} — {g.detail}" for g in failing)
    return out


def plan_spend(docs: list[DocInput], *, candidate_ids: list[str], runs_per_candidate: int,
               coref_pass: bool, dry: bool, config: Any = None) -> SpendPlan:
    frames = tuple(image_frames(docs))
    text = sum(1 for d in docs if Path(d.file).suffix.lower() not in _IMAGE_SUFFIXES)
    plan = SpendPlan(candidates=tuple(candidate_ids), text_docs=text, frames=frames,
                     runs_per_candidate=runs_per_candidate, coref_pass=coref_pass, dry=dry)
    if config is None:
        return plan
    lanes: list[LanePlan] = []
    for cid in candidate_ids:
        candidate = config.candidate(cid)
        lanes.append(LanePlan(
            candidate_id=cid, provider=candidate.provider,
            limit=config.rate_limit(candidate.provider),
            calls_floor=plan.calls_per_run_floor * runs_per_candidate,
            calls_ceiling=plan.calls_per_run_ceiling * runs_per_candidate,
        ))
    return SpendPlan(candidates=plan.candidates, text_docs=text, frames=frames,
                     runs_per_candidate=runs_per_candidate, coref_pass=coref_pass, dry=dry,
                     lanes=tuple(lanes))


def resume_preview(config: Any, docs: list[DocInput], bundles_root: Path, *,
                   candidate_ids: list[str], enabled: bool, producer: str = "live") -> str:
    """What is already on disk and will NOT be re-bought — stated before the run, like the spend.

    Read through the same :class:`~eval.extraction.resume.ResumeStore` the run uses, with the same
    fingerprint, so this cannot report a hit the run then misses. A number here is money the previous
    invocations already spent and this one keeps.
    """
    from . import resume as R

    store = R.ResumeStore(root=bundles_root, invocation="preview", enabled=enabled)
    if not enabled:
        return ("resume:      DISABLED (--no-resume) — every document will be bought fresh, so "
                "`determinism` is sampled in one sitting")
    lines: list[str] = []
    total_hits = total_slots = 0
    for cid in candidate_ids:
        candidate = config.candidate(cid)
        fp = R.fingerprint(model_id=candidate.model_id, docs=docs, producer=producer)
        hits = 0
        for run_index in range(1, config.replication.runs_per_candidate + 1):
            for doc in docs:
                total_slots += 1
                if store.load(cid, run_index, doc.source_id, fp) is not None:
                    hits += 1
        total_hits += hits
        lines.append(f"      {cid}: {hits}/{config.replication.runs_per_candidate * len(docs)} "
                     "document-extraction(s) already on disk and valid")
    head = (f"resume:      ENABLED — {total_hits}/{total_slots} document-extraction(s) reusable "
            "(fingerprint = pinned model id + document set + prompt/schema version; anything else is "
            "re-bought)")
    if total_hits:
        head += ("\n             NB: reusing them means these runs were NOT all sampled in one sitting. "
                 "The scorecard says so, and marks `determinism`.")
    return "\n".join([head, *lines])


# ══════════════════════════════════════════════════════════════════════════════════════════════════
# The dry-run client — the whole path, none of the spend.
# ══════════════════════════════════════════════════════════════════════════════════════════════════

#: Capitalised words and alphanumeric designators, in document order. Used only to make the dry client's
#: mention names *verbatim substrings of the document it was handed*, so the pipeline's quote-support
#: checks pass and pass 2 actually dispatches. Nothing here reads the gold.
_NAME = re.compile(r"\b(?:[A-Z][A-Za-z]{2,}|[A-Z]{2,}[-/]?\d[\dA-Za-z/-]*)\b")


def _mentions_from(text: str, count: int = 3) -> list[str]:
    """The first few distinct capitalised/designator surfaces in the text, in order of appearance."""
    seen: list[str] = []
    for match in _NAME.finditer(text):
        token = match.group(0)
        if token not in seen:
            seen.append(token)
        if len(seen) >= count:
            break
    return seen


class DryRunClient:
    """A deterministic ``ExtractionClient`` double: real call shapes, no network, no key, no cost.

    It exists so the driver's whole path — assembly, both extraction passes, the imagery lane, the
    rebuild, every metric, the gates and the verdict — can be exercised and *shown* before any budget is
    committed. It routes on the tool name it is handed, because the extraction tool varies per document
    format and a double that answered every tool identically would not exercise the real lanes.

    Its mention names are lifted verbatim from the document it is given, for one mechanical reason: the
    pipeline drops a claim whose surface its quote does not support, and a dropped claim yields no
    mentions, and no mentions means pass 2 never dispatches — so a double emitting invented names would
    quietly under-exercise the very pass that doubles the bill. It never reads the gold, so its *scores*
    are meaningless by construction; only the path it proves is meaningful.
    """

    def __init__(self, *, model_id: str) -> None:
        self.model_id = model_id
        self.last_usage: dict[str, int] | None = {"input_tokens": 900, "output_tokens": 120}

    # ── the text lane ─────────────────────────────────────────────────────────────────────────────
    def extract(self, *, tool_name: str, input_schema: dict[str, Any], system: str, text: str,
                images: Any = ()) -> dict[str, Any]:
        del input_schema, system, images
        if tool_name == coref.TOOL_NAME:
            # Pass 2 declines to cluster. A dry run must not invent a coreference decision — that would
            # make the top-weighted criterion read as measured on a number no model produced.
            return {}
        names = _mentions_from(text)
        if len(names) < 2:
            return {}
        quote = text[:200]
        first, second = names[0], names[1]
        if tool_name == "extract_customs_gd_bol":
            return {"rows": [{"consignee": {"name": first, "source_quote": quote},
                              "description": second, "source_quote": quote}]}
        if tool_name == "extract_social_post":
            return {"posts": [{"handle": first, "body": quote, "source_quote": quote,
                               "sightings": [{"system": second, "source_quote": quote}]}]}
        if tool_name == "extract_tender_procurement":
            return {"procuring_org": {"name": first, "source_quote": quote},
                    "system": {"name": second, "source_quote": quote},
                    "source_quote": quote}
        if tool_name == "extract_notam_navwarning":
            return {"notices": [{"notice_id": first, "activity": second, "source_quote": quote}]}
        # prose_claim and anything else offering the general shape
        return {
            "manufacturers": [{"name": first, "source_quote": quote}],
            "components": [{"name": second, "source_quote": quote}],
            "relations": [{"relation": "supplies-component", "subject": first, "object": second,
                           "source_quote": quote}],
        }

    # ── the imagery lane ──────────────────────────────────────────────────────────────────────────
    def read_image(self, *, tool_name: str, input_schema: dict[str, Any], system: str, image: bytes,
                   media_type: str) -> dict[str, Any]:
        """Returns an empty observation, and that is enough for the gate it evidences.

        The imagery gate asks whether a standalone-image call *returned*, never what it said — it is a
        capability gate, not a scored metric. So an honest empty read both evidences the gate and invents
        no observation about a real corpus frame.
        """
        del tool_name, input_schema, system, image, media_type
        return {}


def dry_client_factory(candidate: Any, run_index: int) -> DryRunClient:
    """A ``ClientFactory`` that never builds a real client, reads a key, or touches the network."""
    del run_index
    return DryRunClient(model_id=candidate.model_id)


__all__ = ["DryRunClient", "LanePlan", "SpendPlan", "blocked_before_spending", "build_slice",
           "dry_client_factory", "image_frames", "plan_spend", "resume_preview"]
