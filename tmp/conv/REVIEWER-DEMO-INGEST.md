# Fire the alert yourself — the live ingest demo

**No API key. No network. No configuration.** Everything below runs against files that ship with the app.

---

## Why the graph starts incomplete

A monitoring system earns its keep by warning an analyst **when new evidence arrives**. You cannot see
that happen if the evidence is already in the picture when you open it.

So two documents are deliberately **held back** from the graph you first see:

| Withheld document | What it is |
|---|---|
| `d18_rahwali_pass1` | A 2025 commercial satellite pass over Rahwali airfield — the first sign the battery moved |
| `d19_rahwali_confirm` | A second, independent 2025 assessment of the same thing |

They are collected. They are shipped with the app. They are simply **not yet in the graph** — exactly as
if they had just landed in the analyst's inbox. Anything the system had *inferred* from them is held back
with them, so the starting picture contains no conclusion whose premises are missing.

This is declared, not hidden: the list lives in `config/sources.yaml` under `withheld_from_seed`, and the
app will tell you what it is holding at any time (`GET /pending`).

---

## What you do

1. Open the app and switch it to **live** mode — append `?mode=live` to the URL.
2. In the left rail, under **Documents**, find **Awaiting ingest**. It lists the two withheld documents.
3. Click **Ingest** on `d18_rahwali_pass1`.
4. Click **Ingest** on `d19_rahwali_confirm`.
5. Click **Watching** in the left rail to open Indicators & warning.
6. In the fired alert's **Evidence** block, click any reference chip.

That is the whole demo. Each ingest is a real append into the live system — the same path a keyed
extraction would end in, just with the model's output already recorded rather than recomputed.

---

## What you should see

**Before you ingest.** The unit sits at **PAF Base Nur Khan (Rawalpindi)**. There is no Rahwali pin.
**Watching** reads `0 — none fired`, and the Watch panel says, plainly, *"No tripwire has fired on the
current view."* Nothing is stale: nothing has displaced that assessment yet, so it reads as what we
currently know — not as history.

**After the first ingest.** The map grows a **Rahwali airfield** pin. Nur Khan is marked **superseded**,
with a *replaced by →* link drawn between them. **Watching** flips to `1 fired`, and the **Basing
relocation** tripwire appears with `based-at: site_rawalpindi → based-at: site_rahwali`.

The new assessment reads **probable**, not confirmed — one satellite pass cannot rule out a decoy. That
restraint is the system working, not a gap.

**After the second ingest.** The independent confirmation lands and strengthens the case. No second alert
fires: the move was already reported, and reporting it twice would be noise.

**When you click a reference chip.** The provenance drawer opens on that exact element and shows the
**verbatim sentence** from the source document, with the file and line it came from. Both sides of the
alert trace separately — click the "before" chip and you get the 2021 Rawalpindi evidence, its
**stale** and **superseded** flags, what would be needed to raise it again, and when the next coverage is
due. "What changed" is only auditable if the before and the after can each be checked on their own.

---

## If you would rather not click

Same thing from a terminal, against a running instance:

```
curl -s localhost:8080/pending                                   # what is being withheld
curl -s localhost:8080/pending/d18_rahwali_pass1 \
  | python -c 'import json,sys; print(json.dumps({"bundle": json.load(sys.stdin)["bundle"]}))' \
  | curl -s -X POST localhost:8080/ingest -H 'content-type: application/json' -d @-
```

Or, from a checkout, `make beat` runs the same before → ingest → after → alert sequence and prints the
resulting alert as JSON.

---

## Want the complete picture instead?

Start the app with `CHANAKYA_SEED_WITHHOLD=""` and nothing is held back — the full corpus loads at once.
The relocation is then already settled in the graph on first paint, and there is no arrival left to
detect. That is the point of withholding.

---

## Two things worth knowing

- **Same inputs, same result, every time.** Ingesting these documents produces the identical graph and the
  identical alert on every run. Nothing here is scripted or replayed; it is recomputed.
- **Re-clicking is harmless.** Ingesting a document twice changes nothing and fires nothing — the button
  simply reads *ingested* once its claims are in the record.
