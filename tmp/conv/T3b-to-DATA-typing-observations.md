# DATA — extraction-typing observations found while fixing fragmentation (T3b)

**From:** QA T3b (`qa/t3b-fragmentation`). **Not self-fixed** — these are corpus / extraction-output
questions, and the frozen bundles are not mine to edit. Each is currently *worked around* in code; the
workaround is defensible on its own merits, but the underlying data is worth a look.

## 1. `HT-233` is extracted as a `variant` in at least one document

The graph contains **both** `ent:component:HT-233` and `ent:variant:HT-233` as entity-form claims. The
HT-233 is an engagement radar — a component. The variant typing is an extraction error.

Consequence before the fix: RESOLVE saw two contradictory readings of one surface form, correctly refused
to guess, and left the string an untyped mention — a nameless `unknown` node that could never resolve,
even though its surface string was *identical* to the registry component's.

**Worked around** by letting the edge's declared domain/range adjudicate (the form is the subject of
`equips`, whose domain is `component`, so `variant` is not admissible there). That rail is worth having
regardless. But the mis-typed claim is still in the log, and the rail only fires where the ontology
happens to admit exactly one reading — a form that only ever appears on a polymorphic edge stays stuck.

**Ask:** confirm the mis-typing at the extraction layer and decide whether the write-time re-lane
(`chanakya.ontology`) should also reject an *entity* claim whose type contradicts the type its own
document's triples imply.

## 2. `comp_tel_chassis` is fused with a `known_gap` and renders as one

`config/entities.yaml` declares `comp_tel_chassis` as a **component**. In the rebuilt view it renders as
`type: known_gap`, name `"transporter-erector-launchers (TELs)"`.

Cause: an entity claim of type `known_gap` with that exact name exists, the exact-name bootstrap merged
it into the registry cluster (that rule checks namespace but not type), and `view.pipeline._assemble`
names/types a node from the first claim that replays onto it.

This predates T3b and is unchanged by it. Two separable questions:
- **Data:** should a `known_gap` claim carry the same literal name as a real component?
- **Code (not mine to land here):** should the exact-name bootstrap be type-gated? It would split
  existing clusters, so it needs a measured pass, not a drive-by.

## 3. Several `basing_site` entities are not places at all

Now typed `area_of_operations` by `config/ontology.yaml`'s refinement rule: `Karachi air defence sector`,
`Karachi coastal air defence belt`, `central Punjab air defence sector`, `Punjab`, `Sindh`.

Others remain `basing_site` and are arguably still not sites, but were left alone because the head-noun
rule does not reach them and inventing a broader rule risks retyping real sites:

- `key PAF main operating bases` — an aggregate, not a site
- `garrison in China's western military district` — head noun is "district", but the *referent* is a garrison
- `air defense node in vicinity of a known PAF forward operating base` — a hedged description
- `fenced compound near a PAF airbase` and `fenced compound near a PAF airbase in central Punjab` —
  two descriptions of what is probably one place, from the same document

**Ask:** whether any of these should be re-emitted with a more specific type/name at extraction time, or
added to the ontology's `named_instances` list — and in particular whether the two "fenced compound"
forms are one place (they are still an open merge candidate, and the one remaining Karachi-cluster
candidate pairs one of them with the Army AD Centre).

## 4. `Pakistan` is an entity endpoint with no admissible node type

`Pakistan` appears as an endpoint of both `equips` (domain `component`) and `imported-by` (range `unit`),
so the ontology admits *neither* reading and it correctly stays an untyped mention. There is no country
node type, by design.

**Ask:** is this an extraction artefact (a country name captured as a participant) worth suppressing at
the source, or does it want a `country` type? Note that inventing a type with no query behind it is
exactly what CLAUDE.md warns against, so "suppress at extraction" is probably the right answer.

## 5. FYI — the T1 pre-conditions for the coreference gate are now met

T1's steps 1–3 (identical-string resolve miss, `basing_site` typing, `contract_import_event` hard rail)
are all landed on `qa/t3b-fragmentation`. If the coref producer is ever re-recorded, it should be
measured against this baseline — the merge queue is 40 → 8, so its marginal value is now much easier to
read honestly.
