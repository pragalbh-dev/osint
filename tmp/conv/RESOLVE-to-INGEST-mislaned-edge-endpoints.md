# RESOLVE → INGEST/DATA-C: mis-laned edge endpoints now mint typed-but-wrong nodes

**From:** RESOLVE, Phase-3 P3.0/P3.1 (`fix/phase3-resolve`). **Date:** 2026-07-19.
**Status:** observation for the owning agent — **not** self-fixed here (per CLAUDE.md "data issues → `tmp/conv/`").

## What changed on our side

P3.1 (RES-1 endpoint-as-mention) now types every triple endpoint. Resolution order is:

1. the endpoint's type comes from the **entity it matches** (an entity-form claim or a
   `config/entities.yaml` registry entry) — authoritative, and this protects every known entity;
2. only when *nothing* knows the surface form does it fall back to the **edge's declared domain/range**
   (`config/ontology.yaml` `from:`/`to:`);
3. un-typable endpoints stay untyped mentions.

Step 2 is the guard we were asked to implement ("a minted endpoint node is a TYPED node, never `unknown`").
It faithfully applies the ontology — which means it also **faithfully propagates a mis-laned edge**.

## The symptom

Several frozen bundles carry `exported-by` / `imported-by` edges whose endpoints do not fit the declared
domain/range (`exported-by`: `contract_import_event → manufacturer`; `imported-by`:
`contract_import_event → unit`). Because the endpoint is an unknown surface form, it inherits the
declared range and mints a typed node that is semantically wrong:

| claim | edge as written | node RESOLVE now mints | should be |
|---|---|---|---|
| `d01-sipri-transfer-l8-3` | `HQ-9/P -exported-by-> China` | `ent:manufacturer:China` | a country, not a manufacturer |
| `d22-deep-tier-supplier-l10-5`, `d24-tel-chassis-attribution-l17-3` | `HQ-9/P -imported-by-> Pakistan` | `ent:unit:Pakistan` | a country, not a unit |
| `d21-techdata-authority-l10-3/-4` | `FD-2000 -imported-by-> Turkmenistan / Uzbekistan` | `ent:unit:Turkmenistan`, `ent:unit:Uzbekistan` | countries, not units |
| `d03-quwa-analysis-l8` | `FD-2000/HQ-9 family -exported-by-> China` | `ent:contract_import_event:FD-2000/HQ-9 family` | a variant, not a contract event |

Related endpoint mis-types from the same cause (subject/object don't fit the edge):
`ent:component:India`, `ent:component:Pakistan Army Air Defence (PAAD) unit`,
`ent:variant:Air Defence squadrons`.

**~8 artifact nodes total.** They are claim-backed (traceable, gate G4 holds) — just wrongly typed.

## Root cause (not RESOLVE's to fix)

The subject of these edges is a **variant**, but both edges are ranged at `contract_import_event → …`.
`EdgeLaneIndex.relane()` is supposed to **reject** a fact whose endpoints fit no edge rather than keep it;
these survived. Either the re-lane did not run on these triples, or a variant→country transfer statement
is being forced onto `exported-by`/`imported-by` when it is really a **TransferEvent** (which d01 *also*
emits correctly, e.g. `d01-sipri-transfer-l8-2` with participants `[HQ-9/P, China, Pakistan Air Force]`).

## What we deliberately did NOT do

We did **not** special-case countries or add a suppression list in RESOLVE. Doing so would make RESOLVE
second-guess the ontology it is supposed to read (gate G6, config-driven), and would hide a real upstream
defect. RESOLVE types what the ontology declares; the vocabulary/lane fix belongs at write time.

## Suggested fix (INGEST)

Drop or re-lane these variant→country triples at extraction: a "X was exported by / imported by
<country>" statement is a `TransferEvent` participant fact, not a `contract_import_event` role edge.
Re-recording the bundles after that removes all ~8 artifacts with no RESOLVE change.
