# DATA / RESOLVE — `unit_hq9b` resolves to the name "Pakistan Air Force"

**From:** QA T6 (drawer semantics). **Not self-fixed** — this is a corpus/resolution question, not a UI one.

## What I saw

On the live `hq9p_primary` graph (boot seed + d18/d19 ingested), the node `unit_hq9b` has
`type: unit` and `name: "Pakistan Air Force"`.

That name is the *operator*, not the unit. Everywhere the UI now (correctly) names the subject of an
assertion instead of printing a raw id, the copy comes out as:

* map connector: **"Pakistan Air Force moved →"**
* map caption on the vacated site: **"former Pakistan Air Force basing · 2021"**
* drawer headline on the version link: **"Pakistan Air Force moved from PAF Base Nur Khan to Rahwali
  airfield"**
* every basing claim row: **"Pakistan Air Force is based at PAF Base Nur Khan"**

Each of those is a faithful render of the graph. They just read wrong, because the graph's name for the
HQ-9B fire unit is the name of the air force that operates it. The intended reading is something like
*"the HQ-9B battery"*.

## Why it matters here

This is the relocation beat — the demo's climactic moment (product/00 §7 beat 7). "Pakistan Air Force
moved from Nur Khan to Rahwali" overstates the claim considerably: an air force did not relocate, one
fire unit did.

## Why I did not fix it

The UI's rule is that it renders the node's **own** name and never invents one; hard-coding a nicer
label for `unit_hq9b` in the frontend would put a paraphrase between the analyst and the graph, which is
exactly what the rest of this work was removing. The fix belongs upstream: either the extraction/
resolution that assigned this name, or the entity's seed name.

## Suggested check

Whether `unit_hq9b`'s name came from a merge (an alias table entry pulling the operator string onto the
unit) or straight from an extraction, and whether a name like *"HQ-9B fire unit"* / *"HQ-9B battery"* is
supportable from the corpus. If no source states a unit designator, the honest answer may be to leave
the node unnamed and let the UI fall back to the id — which it already does — rather than to carry a
name the sources do not support.
