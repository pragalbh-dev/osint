# START HERE — context pack for the design collaborator

**For:** the product/design collaborator (and their AI agent). **From:** Pragalbh.

Everything in this `product/` folder is written **for a designer** — plain language, no engineering, no
military background needed. The subject (a Pakistani air-defence missile system) is just a realistic
stand-in; every domain term you need is glossed below.

---

## The folder, and the reading order

1. **`00-ux-brief.md`** — **the brief. Start here.** What to design: the screens, the flows, and the
   **OPEN →** questions I want your eye on. It's self-contained; you could design from it alone.
2. **This file** — a 10-minute domain primer + glossary, so the nouns in the brief make sense.
3. Four short, clean reference docs — read when the brief points you to one (it links each section):
   - **`01-entities-and-relationships.md`** — the **nouns on the graph & map**: every node type and edge
     type, in plain language. Read before designing the Map and Graph.
   - **`02-trust-and-credibility.md`** — the **trust model** (statuses, freshness, independence,
     integrity, honest-refusal). This is the *soul* of the product — read it closely. **Zero formulas.**
   - **`03-data-contracts.md`** — **what info each surface actually has to display** (the fields on a HITL
     card, the provenance drawer, an answer, an alert…). Read it when you're laying out a specific panel.
   - **`04-scenario-entities-and-corpus.md`** — the **concrete entities** the demo runs on (the real ~15
     nodes, the alias/merge traps, the two site threads) + an index of every source document.
4. **`reference/corpus/`** — the **full source corpus** (~23 real, messy documents; what each one is, is
   in doc `04`). Start with `d05`, `d07`, `d11`; they make the abstract stuff ("a claim traces to an exact
   source line", "5 sources but 2 independent looks") concrete.

> These three docs are clean distillations of the deeper engineering design — I've deliberately stripped
> the formulas, storage, and jargon so nothing here is noise. If a field name or number looks provisional,
> that's called out inline; the *shapes* are stable enough to design against.

**Locked vs. yours:** anything in the brief *not* marked **OPEN →** is a settled requirement; the **OPEN →**
items are genuinely yours to propose on. If a locked thing feels wrong, push back — but it was a
deliberate call.

**What to share back / who reads what:** you (human) need the brief + this primer. Your **agent** can read
this whole `product/` folder — it's all plain prose, no code.

---

## The 60-second domain primer

An intelligence analyst wants to understand one enemy weapon system — where its pieces are, who supplies
them, and where the **single weak link** (chokepoint) is. The evidence is a pile of **messy, contradictory
open-source documents**: news, official statements, shipping/customs records, satellite-image reports,
social-media posts. Some are wrong, stale, or deliberately faked.

The product does the reading and turns every document into small **claims** ("*this source, on this date,
says X*"), fuses them into one **map/graph** of things and connections, and — this is the whole point —
**never asserts anything without showing the receipts, and openly says "insufficient evidence" instead of
guessing.** The human stays in charge: the machine proposes, the analyst decides.

Everything you design serves one idea: **make *how much we trust each thing* visible at a glance** (brief
§3, and `02-trust-and-credibility.md`).

---

## The five terms that unlock everything

- **Claim / evidence layer** — every document is shredded into small sourced assertions, kept forever as
  an audit trail. The clean map you see is *computed from* these.
- **Confirmed vs. probable** — the machine never says "confirmed" off one source; that needs multiple
  *independent* credible looks. Keeping these two visually far apart is the product's #1 job.
- **Independence (the 3-axis rule)** — sources only corroborate if they differ in *publisher*, *method*
  (satellite image vs. written report), and *side* (two sources that both benefit from the story don't
  count). "5 sources, 2 independent looks."
- **Freshness / stale** — facts age. A "confirmed" fact decays toward "stale" if nothing re-confirms it;
  some facts age in weeks, some effectively never.
- **Insufficient evidence / Known Gap** — when evidence can't answer, the system *says so* (naming what's
  missing + when data is next due) instead of guessing. An honest refusal — a feature to show off.

### Glossary

| Term | Plain meaning |
|---|---|
| **OSINT** | Open-source intelligence — analysis built only from publicly available info. |
| **Analyst** | The single expert user; skeptical, time-poor, accountable. |
| **Claim / Indicator** | One sourced assertion — the atomic unit of the whole system. |
| **Evidence layer** | The permanent, never-edited ledger of every claim. The receipts. |
| **Knowledge layer** | The clean, resolved map of things & connections, *derived from* the evidence. |
| **Entity resolution / merge** | Deciding when two differently-named records are the same real thing. |
| **Corroboration** | Independent claims agreeing — raises confidence (only if *truly* independent). |
| **Confirmed / Probable / Possible** | Trust ladder: solid / thin / weak-lead. |
| **Contradicted** | Two credible sources disagree about the *same moment* → conflict → human review. |
| **Superseded** | The *world changed* (a unit relocated); the old fact goes **stale**, not "wrong." |
| **Stale** | *Was* confirmed, but has aged past its shelf life with no fresh confirmation. |
| **Freshness / half-life** | How fast a given *kind* of fact ages. |
| **Source tier** | Credibility ladder: official > reputable analysis > named social > anonymous. |
| **Integrity** | Checks whether media is faked or *miscaptioned* (e.g. a real old photo, new caption). |
| **"Too-clean" penalty** | A suspiciously perfect / perfectly-placed source is *discounted*, not trusted. |
| **HITL** | Human-in-the-loop — the machine escalates hard calls to the analyst. |
| **Review queue** | The inbox where those escalations land (merges, overrides, alerts). |
| **Observable / tripwire** | An analyst-defined condition that fires an **alert** when data meets it. |
| **Chokepoint** | The single weak link the whole system depends on — the analytic payoff. |
| **Known Gap** | A first-class "known unknown" object; also a collection to-do. |
| **Coverage gap vs. structurally unobservable** | "We *could* learn this (next pass Tuesday)" vs. "no open source will *ever* show this." Must look different. |
| **ORBAT** | Order of battle — the inventory of what units/equipment an enemy has and where. |
| **Subject / lens** | The thing under investigation; a saved *view* over one shared graph, not its own database. |

---

## reference/corpus/ — the full source corpus (~23 documents)

The demo runs on these. **Doc `04-scenario-entities-and-corpus.md` indexes every one** (what it is, what
it establishes). Start with these three to feel what "a claim traces to an exact source line" means —
great fuel for the provenance-drawer design:

- **`d07_sat_confirm_karachi.txt`** — a satellite imagery-analysis report. Note the *hedged* language
  ("moderate-to-high confidence", "count uncertain"). This is what a **confirming** source looks like, and
  why confidence is a spectrum.
- **`d11_recycled_image.txt`** — a Reddit-style thread arguing over a photo. The **recycled-2019-photo-as-
  breaking-news** case (brief §7 beat 5): several accounts "confirm" it, but they're not independent, and
  it's old. The heart of "5 sources, 2 real looks."
- **`d05_customs_manifest.txt`** — a customs declaration. Note the *name variants* for one company
  ("TRANS-INDUS" vs "TRANS INDUS") — raw material for the **merge decision** (brief §5.5) and the
  supply-chain trace.

The folder also includes 3 `cd*`-prefixed **chaff** examples — noise (wrong systems, rumors, civilian
traffic) the system must down-rank, not delete.
