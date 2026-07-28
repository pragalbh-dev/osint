# Silent truncated tool payloads — production fix, blast radius, and the eval half

**Branch:** `fix/ingest-payload-validation` (worktree `wt-INGEST-FIX`). Full backend suite green:
1542 passed / 7 skipped / 16 xfailed. Ruff + mypy clean on every file touched (the 6 ruff + 7 mypy
findings that remain in the tree are pre-existing, in `view/pipeline.py`, `view/basing.py`,
`resolve/places.py` — untouched here).

## The defect, reproduced

`AnthropicExtractionClient._call` returned `dict(block.input)` with no validation. On the recorded
three-way extraction run, 2 of 81 forced coreference calls came back with `clusters` filled as a
**truncated JSON string** (265 and 376 chars, ending mid-token) instead of a list. `valid_clusters` does
`for entry in raw.get("clusters") or []`, iterated the *characters*, dropped each on its
`isinstance(entry, dict)` guard, and returned `[]`. No exception, no log line, recorded `error: null`.

Reproduced before touching anything, from the persisted payload:

- `json.loads` on the field raises `Unterminated string starting at: line 1 column 221`.
- `coref.valid_clusters(payload, …)` returns `[]` and logs nothing.
- The discarded cluster is `member_ids [1, 7, 10]` — the gold's `d05-C1-consignee`, whose own note calls
  it "the ONLY identifier-backed equivalence in the slice".

## The fix

New module `chanakya/toolargs.py`: one structural validator over provider-returned tool arguments,
checked against the schema we offered. It enforces **only the container/scalar boundary** —

- declared `array`/`object` with no scalar alternative, observed scalar → violation;
- declared scalar only, observed container → violation;
- `null` → always fine (absence is a first-class state here);
- a union listing both (`["number","string","array"]`, which `query_graph`'s constraint `value` really
  is) → satisfied by either;
- scalar *flavour* (`"7"` for an integer, an unknown enum label, a missing required field) → **not**
  checked. Those are content mismatches the downstream rails already reject one row at a time, visibly.
  Only the container boundary silently becomes character iteration.

Recursion follows `$ref`/`$defs`, `anyOf`/`oneOf`, `properties` and `items`, so a structure serialised
as text is caught at whatever depth it happened.

**Policy per seam** — deliberately different, each matching the discipline already established there:

- **ingest client → raise** (`MalformedToolPayload`, a `RuntimeError` subclass). Not *retry*: retrying a
  returned response is sampling until the answer is liked, and the remedy for a token-budget truncation
  (a bigger budget, or a narrower input) belongs to the caller, not the transport. Not
  *record-and-continue*: that is what we already had, and a document ingested with a pass silently
  missing is exactly the "absent evidence must be explicit" line. A raise is also what this file already
  does when the forced tool call is missing entirely — this is the same principle one level down.
- **agent `run_tool` → `{"error", "suggestion"}`**, the dispatcher's existing actionable-error
  convention, so the planner re-issues the call instead of the answer dying mid-loop.
- **`propose_observable_from_text` → `ObservableProposal(draft=None, reason=…)`**, that path's existing
  honest-refusal shape.

Also added: a forced call whose provider `stop_reason` / `finish_reason` is `max_tokens` is rejected on
that signal alone. A call cut off *between* two complete list entries leaves a payload whose shape is
fine; only the provider's own report reveals it. This is the one behaviour change that can fire on a
payload that looks well-formed — worth it, because today such a call is silently taken as complete.

## Blast radius (every instance of the pattern)

| Site | What it is | Status |
|---|---|---|
| `ingest/client.py` `AnthropicExtractionClient._call` | `dict(block.input)` — the measured defect | **fixed** (validate + stop_reason) |
| `ingest/client.py` `GeminiExtractionClient._call` | `dict(fn_call.args or {})` — same pattern, PRIMARY provider | **fixed** (validate + finish_reason) |
| `ingest/client.py` `ScriptedExtractionClient` | replays frozen bundles = provider answers we kept | **fixed** (validates; `validate=False` opt-out for doubles) |
| `agent/client.py` `AnthropicClient.run_turn` | `dict(block.input)` for ASK tool calls | closed at its two consumers, below |
| `agent/tools.py` `run_tool` → `neighbors` | `allow = set(edge_types)` over a string = a set of characters → empty traversal reported to the analyst as "no path exists" | **fixed** |
| `agent/tools.py` `run_tool` → `find_paths`, `query_graph` | `edge_whitelist`, `constraints` — same | **fixed** (same check, all tools) |
| `agent/propose.py` | `[m for m in payload.get("mentions", []) if isinstance(m, str)]` — characters *pass* the filter, so it resolves `"["`, `"H"`, `"Q"` and drafts a tripwire from punctuation. Worse than silent | **fixed** |
| `agent/loop.py:166`, `agent/assemble.py:382/485` | read scalar params off the recorded trace | not affected |

All five ingest passes (pass-1 per-format extraction, pass-2 coreference, the VLM imagery lane, the
imagery corroboration call, the attribution corroboration call) go through the one `ExtractionClient`
seam, so they are covered by the client fix rather than five patches.

**Measured false-positive check:** the validator was run over all 174 recorded payloads in the persisted
three-way run (81 bundles, 3 models × 5 runs, 6 distinct tools), each against its real schema. It flags
exactly the 2 known-bad calls and nothing else.

## The eval half — NOT applied here

`structured_output_reliability` lives on `bakeoff/rk-impl` (`wt-RK-BAKEOFF-impl`), which is not this
branch and not my worktree. The change is written, tested and shipped as a patch instead:

**`tmp/conv/eval-structured-output-sees-truncation.patch`** — `git apply --check` passes against
`wt-RK-BAKEOFF-impl` HEAD.

- `CallRecord` gains `offered_schema` (the schema is already in hand at record time) + `malformed_fields()`,
  which runs the *same* `chanakya.toolargs` check the client now enforces, so the metric and the pipeline
  agree by construction on what "malformed" means.
- Records written before the schema was captured fall back to the signature the class leaves: a field
  holding text that opens like JSON and does not parse. Narrower, never wider.
- `resume.py` round-trips the schema.
- `structured_output_reliability` counts a call clean only if it returned, invented no top-level field,
  **and** filled every field in the declared shape; `detail` gains `malformed_payloads`.

Re-scoring the persisted run with it: `anthropic-opus-5/run-01` and `run-03` drop **1.0000 → 0.9333**
(14/15), naming the field; the other ten runs stay 1.0000. Both the schema-carrying and the fallback path
give that answer.

**Sequencing:** the patch imports `chanakya.toolargs`, so it can only land after this branch merges.

Verified offline in a scratchpad harness (bakeoff `eval/` + its tests, with this branch's `chanakya` on
the path): 350 → 358 passing, the same 7 pre-existing failures before and after (all of them
`config/bakeoff.yaml` not found — an artefact of the harness's repo root, not the patch).
