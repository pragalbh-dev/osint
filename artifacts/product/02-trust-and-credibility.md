# 02 · Trust & Credibility — the model, in plain language

**For:** the design collaborator. **Read after:** `00-START-HERE.md`. This is the *soul* of the product
(brief §3) explained with **zero formulas or storage detail** — just the concepts you need to design the
status visual language, the provenance drawer, and the honest-refusal state. Everything here has a precise
mechanism behind it in the engineering docs; you don't need those, and I've left them out on purpose.

---

## 1. Two layers: the receipts and the picture

- **Evidence layer (the receipts).** Every document is shredded into individual **claims** — "*this
  source, on this date, says this specific thing*." This is an append-only ledger: nothing is ever edited
  or deleted. It's the permanent audit trail.
- **Knowledge layer (the picture).** The system fuses those claims into the one **graph** of things and
  connections the analyst actually looks at. One node can be backed by many claims from many documents.

The key consequence for you: **the picture is computed *from* the receipts.** A node's trust status isn't
typed in by anyone — it's derived from the claims underneath it. That's *why* you can always click any
node and walk down to the exact source line: it's a lookup, not a feature bolted on. And it's why an
analyst's override recomputes the picture rather than just editing text.

**A claim is the unit of everything.** Not the document, not a paragraph — the single sourced assertion.
"5 documents mention this base" really means "5 claims point at this one node," and the drawer's whole job
is to show you *how independent those 5 really are* (see §4).

---

## 2. The trust statuses

Every fact — every node, edge, and line in an answer — wears exactly one status. Keeping **confirmed** and
**probable** visually far apart is the product's #1 job.

| Status | Plain meaning (the entry condition, no math) | Analyst feeling |
|---|---|---|
| **Confirmed** | **Two or more *independent* credible sources** agree, the evidence is recent, there's no unresolved conflict, and nothing looks faked. | "I can brief this." |
| **Probable** | Some real evidence, but thin — one source, or corroboration that *fails* the independence test, or any integrity/decoy/denial flag caps it here. **One source can never confirm alone.** | "Lean on it, don't bet on it." |
| **Possible** | A weak lead. One low-credibility whisper. | "Noted. Keep an eye out." |
| **Contradicted** | Credible sources disagree **about the same moment in time** → a genuine conflict → flagged and sent to a human. | "Something's off — I need to look." |
| **Stale** | *Was* confirmed, but the evidence has aged past its shelf life with no fresh confirmation. An *overlay* that demotes any status as it ages. | "This was true in 2019. Is it still?" |
| **Insufficient evidence** | We were asked something the evidence can't answer. Names what's missing + when data is next due. | "Don't guess. Say what's missing." |

Two things ride *on top of* status and also need visual expression: **freshness** (§3) and **source tier**
(§5).

---

## 3. Freshness — facts age, at very different speeds

A "confirmed" fact never silently stays confirmed forever. As the newest supporting evidence ages, the
fact **decays toward stale**. Crucially, different *kinds* of facts age at wildly different rates:

| Kind of fact | How fast it ages | Example |
|---|---|---|
| **Durable** | Effectively never | Who *manufactures* a part; which model a component belongs to |
| **Semi-durable** | Years | Which unit a system was *inducted into* |
| **Perishable** | Weeks–months | **Where a unit is *right now*** (~12 months) · readiness/activity (~60 days) |

So the UI has to distinguish "**confirmed and fresh**" from "**confirmed, but aging**" from "**stale**" —
and a *perishable* fact should visibly age much faster than a durable one. (The exact half-lives are
analyst-configurable numbers; you just need the three visual bins.)

> **Design cue:** think "confirmed *as of* DATE." A confirmed-but-old perishable fact is the honest,
> slightly-alarming state that the relocation demo (brief §7 beat 7) turns on.

---

## 4. Independence — why "5 sources" can really be "2 looks"

This is the sharpest idea in the product, and the provenance drawer has to make it legible. **Counting
sources is not enough — corroboration only counts when sources are genuinely independent on three axes:**

1. **Different publisher** (origin) — two outlets, neither citing the other. An **aggregator inherits its
   upstream origins**, so it doesn't add a new look ("echoes never stack" — reposts of one photo are one
   look).
2. **Different method** (discipline) — a satellite *image* and a written *report* are two different ways
   of finding out. Two written reports of the same rumor are one way.
3. **Different side** (interest) — two sources that both *benefit* from the same story don't independently
   confirm it (e.g. an operator's own military PR + that operator's ally's state media are the same side).

So the honest picture is often **"5 sources, but really 2 independent looks."** Making that legible — not
a raw count of 5 — is exactly how the product avoids being fooled by manufactured consensus. This is the
visual heart of "lead with credibility." (`reference/corpus/d11_recycled_image.txt` is this case in the
raw: several accounts "confirm" one recycled photo.)

---

## 5. Source tier — where a claim sits on the credibility ladder

Not all sources carry equal weight. Roughly: **official government statement > reputable analysis / trade
press > a named social account > an anonymous post.** For imagery specifically:

- **Commercial satellite imagery** is high-provenance — it can *promote* something to **confirmed**.
- **A social-media image** is low-provenance — it can only ever be a **lead** (probable at best), never a
  confirmation on its own.

Important: these tiers are **outputs of an analyst-tunable rubric**, not hardcoded per-source numbers.
The analyst — not the engineer — owns the trust rules (that's what the Credibility Settings screen is for,
brief §5.8). You may see four factors named behind a source's rating: *authority, editorial process,
directness, track record.*

---

## 6. Integrity — is the media even real, and is it what it claims to be?

Separate from "is the claim true," the system asks "is this artifact authentic and correctly attributed?"
Three orthogonal checks, each of which applies a **penalty** (not a binary real/fake verdict):

- **Content veracity** — is the underlying claim plausible / corroborated?
- **Artifact integrity** — has the image/video been manipulated?
- **Contextual provenance** — is a *real* artifact being passed off as something it isn't? This is the
  **recycled-2019-photo-with-a-new-caption** case (reverse-image / first-seen catches it).

Related deception signals a designer should have a treatment for:

- **"Too-clean" penalty** — a source that's suspiciously perfect or perfectly placed is *discounted*, not
  trusted more.
- **Coordinated inauthenticity** — many near-identical posts in a tight window = manufactured consensus →
  discounted.
- **Adversary denial** — an adversary asserting a fake corroboration or denying a known fact is *discounted
  as a signal*, never counted as evidence.

The demo's most memorable beat (brief §7 beat 5) is integrity **overriding** a corroboration count: three
"sources" for a recycled photo, but the first-seen check refuses to let it become confirmed.

---

## 7. Supersede vs. contradict — the distinction the design must not blur

Both look like "two sources disagree." They mean opposite things:

- **Contradicted** — two claims about the **same real-world time** disagree → a genuine conflict → **red
  flag**, routed to a human to resolve.
- **Superseded** — the claims are about **different times**; the *world changed* (a unit relocated A→B).
  The newer fact is right; the old one isn't *wrong*, it's *history* → the old node quietly goes **stale**
  with a "**replaced by →**" link. This is a *timeline* relationship, **not** an alarm.

Give these clearly different visual treatments (brief §3, §6). When the system isn't sure whether it's the
same thing that moved, it flags a *candidate* supersession rather than silently overwriting.

---

## 8. Insufficient evidence & Known Gaps — the honest refusal

When the evidence can't answer a question, the system **says so** rather than guessing — this is the
disqualifying-if-broken promise, and it should read as *rigor, a feature to show off*, not an error.

Behind it is a simple idea: each kind of assertion has an **evidence requirement** ("to confirm a basing,
you need overhead imagery *or* two independent textual sources, within the freshness window"). If the
requirement isn't met, the system emits a first-class **Known Gap** that names:

- **what's missing** (the unmet requirement), and
- **when the next relevant data is due** (from each source's known refresh cadence).

Known Gaps come in two flavours that **must look different** (brief §3):

- **Coverage gap** — *we could learn this* ("no recent satellite pass; next one due Tuesday"). Feels like
  a pending task.
- **Structurally unobservable** — *no open source will ever show this* (missiles in a bunker, secret
  contract terms). Feels like a permanent boundary. **The UI must never make this look like fresh imagery
  would fix it** — that would be dishonest.

(The system tracks this as an "observability ceiling": *confirmable* / *probable-max* / *never-observable*.)

---

## 9. It's a monitor, not a one-shot report

Trust **changes over time**, and the product's job is to make that change **visible, never silent**:

- **Sources close.** A customs portal stops publishing, an account is deleted. The system flags the
  affected part of the map/graph as **degrading coverage** and states "next coverage due." A region can
  visibly *go blind*.
- **The system learns.** When an analyst makes a call (e.g. "these two *are* the same entity"), the
  decision is remembered so the same case resolves automatically next time. A source that's repeatedly
  right earns more trust over time. (For the demo, the merge-decision memory is the loop to show.)

The meta-rule, and your north star for the staleness/coverage visuals: **degrade gracefully and visibly,
never silently.** The system must never keep confidently asserting a fact it can no longer see.

---

### Where this shows up in the UI

| Concept here | Screen it drives |
|---|---|
| Statuses (§2) + freshness (§3) + tiers (§5) | The **status visual language** (brief §3, §6) — the legend tile |
| Independence (§4) + integrity (§6) | The **provenance drawer's** confidence breakdown (brief §5.6) |
| Insufficient evidence (§8) | The **Ask view's** honest-refusal state + the **Known Gap** object (brief §5.4) |
| Supersede vs contradict (§7) | Map relocation treatment + what lands in the **review queue** (brief §5.5, §7) |
| Tunable rubric (§5) | **Credibility settings** (brief §5.8) |
| Monitoring / decay (§9) | **Alerts** + coverage visuals (brief §5.7) |

Exactly *which fields* each of these surfaces has to display is in `03-data-contracts.md`.
