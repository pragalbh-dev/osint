# Chanakya OSINT

An AI-assisted open-source-intelligence (OSINT) analysis and monitoring system. It maps
one adversary air-defence capability (Pakistan's HQ-9/P, sourced entirely from open
documents) into an auditable graph — who operates what, who supplies it, and how
confident we are in each fact — and lets an analyst ask cited, multi-hop questions of it.

Its governing rule: **where the evidence is absent, ambiguous, or contradictory, the
system says so and names what is missing, rather than filling the gap with a guess.**

This README covers running the app and finding your way around it. For *why* it's built
this way, see the [design note](https://github.com/pragalbh-dev/osint/blob/main/artifacts/design-note.md).

**Live demo:** [compliantly-coky-candace.ngrok-free.dev/?mode=live](https://compliantly-coky-candace.ngrok-free.dev/?mode=live)
— a hosted instance, in the same clean starting state described below. Sections 1–3 are
about running your own copy; skip to §4 if you're using the hosted one.

---

## 1. Run it — two identical paths, no setup required

The whole app (backend + the web UI) ships as **one Docker image**. It boots and runs the
entire worked demo — graph, map, ingest, alerts, review, and the flagship question —
**with no API key and no outbound calls**: the corpus, the pre-analysed evidence and the
map tiles are all baked in. A key is needed only to ask **free-form questions of your
own**, which is what §3 covers.

(Building the image, Path A below, does need network access to clone the repo and fetch
dependencies. The running app doesn't.)

**Path A — clone and build it yourself:**

```bash
git clone https://github.com/pragalbh-dev/osint && cd osint
make run                      # builds the image, starts it, waits until it's ready
# → open http://127.0.0.1:8000/?mode=live      (the ?mode=live matters — see §2)
```

**Path B — skip the build, just pull the published image:**

```bash
docker run -d --name chanakya -p 127.0.0.1:8000:8000 ghcr.io/pragalbh-dev/osint:latest
```

Either way you get the identical artifact — `make run` tags the image with the exact
same name it's published under, so there's nothing to keep in sync by hand.

If port 8000 is already used on your machine: `PORT=8010 make run` (Path A), or change
the `-p` mapping (Path B).

**When it's ready:** `curl http://127.0.0.1:8000/health` returns
`{"status":"ok", ...}`. The container needs a few seconds after starting to finish its
first internal rebuild — `make run` waits for this automatically and prints the URL when
it's safe to open.

**Stopping it:** `make stop` (Path A), or `docker rm -f chanakya` (Path B). Nothing is
written outside the container, so there's nothing to clean up afterward — a restart
always comes back to the same clean starting state.

---

## 2. Open it correctly — the one step that isn't obvious

**Open `http://127.0.0.1:8000/?mode=live` — not the bare URL.**

The app has two modes. Without the `?mode=live` part in the address bar, it opens into a
**scripted walkthrough** (a fixed, pre-recorded narration) rather than the live system —
useful for a presenter's rehearsed demo, but every button in it does the same
pre-scripted thing regardless of what you click, which is confusing if you didn't expect
it. **Live mode is the real, running system** — every panel reflects what's actually in
the graph right now and responds to what you do. Bookmark or share the `?mode=live` link.

---

## 3. Running it keyed vs. keyless

**Keyless (the default, nothing to configure) already runs the full worked demo** —
graph, map, citations, ingest, alerts, review, and the flagship multi-hop question.

That question works without a key because the *reasoning steps* for it are replayed from
a recording, so the demo runs the same way every time. **The answer itself is not canned**
— those steps run live against the graph as it stands, which is why the same question
honestly refuses before you ingest the withheld evidence (§5) and traces a full cited
chain afterwards.

**Keyed** additionally unlocks:
- **Free-form questions** — anything you type into the ask bar beyond the flagship
  question, planned and answered live by a model reasoning over the graph. Without a key
  these return an honest "no model key configured" refusal, naming what's missing rather
  than guessing.
- **Extracting a brand-new document live** — pasting in a document's text and having the
  system read it and add it to the graph in real time, instead of only ingesting the
  pre-packaged documents described in §5.

To enable them, supply an Anthropic API key: put one line in a `.env` file at the repo
root before `make run` (or pass `--env-file .env` to `docker run` for Path B):

```
ANTHROPIC_API_KEY=<key>
```

That is the only key the app needs — nothing else goes in that file. It is read at
startup only, never written to the image or logged.

Without any key, nothing breaks — free-form questions get an honest refusal explaining
that a key is needed, never a guess.

---

## 4. How the app is laid out

Four regions, all visible at once (no tabs, no modals except one detail overlay):

- **Left rail** — the subject you're investigating, a **queue of items awaiting your
  review** (see §6), what's currently being watched for change, and a **Documents**
  panel for adding evidence to the graph (see §5).
- **Center stage** — a map and a graph view of the same underlying data (toggle
  between them), showing every entity and connection currently in evidence.
- **Right panel** — whatever you're currently looking at: an answer to a question, a
  node's evidence, a review decision, or a gap in coverage. Always ends in a text box to
  ask the next question.
- **Detail overlay** — opens over everything else when you click any fact, citation, or
  node, and shows the exact source line it came from. This is the one-click traceability
  the whole system is built around: nothing shown in the app should be un-clickable back
  to its source.

**On first open**, the right panel suggests three starting points — click any of them:
- *"Trace the long-range SAM battery now based at Rahwali back to the organisation that
  builds its missile system, and name the fire-control chokepoint."* — the flagship
  question. **On a fresh start this deliberately refuses**, because the evidence it needs
  hasn't been added yet — that refusal is the point, and §5 walks you through making it
  answerable. No key needed either way.
- *"Is this node confirmed or probable — and on what evidence?"* — click any pin on the
  map to see this answered for that specific fact.
- *"What do we not know here?"* — the system naming its own gaps, rather than guessing
  past them.

---

## 5. The "arriving evidence" demo — documents that trip an alert

The graph you see on first boot is **deliberately missing two collected documents** —
they exist and are ready, but haven't been added yet. This is on purpose: it's what lets
you watch the system react to new evidence live, instead of only ever seeing a finished
picture.

In the left rail's **Documents** panel, an **"Awaiting ingest"** box lists these
withheld documents by name. Click **Ingest** next to one — no file to find, no copying
text, it's already loaded and ready. Do this for both:

1. Before ingesting: ask the flagship question above. It gives an honest **"insufficient
   evidence"** refusal — the system won't guess at something it hasn't been shown yet.
2. Ingest the two waiting documents. One of them **fires an alert**: the system notices
   the tracked unit has *relocated* (its basing site changed), and that shows up as a
   flagged item in the left rail's watch list, with both the old and new evidence
   independently checkable.
3. Ask the flagship question again — it now answers in full, every hop cited, tracing
   from the new location all the way back to the manufacturer and naming the
   fire-control component as the open question in the supply chain.

This works identically keyed or keyless — ingesting these two pre-packaged documents
never calls a model, so it's exactly reproducible every time.

---

## 6. Reviewing — the human-in-the-loop queue

The left rail's queue lists things the system isn't sure about and wants a human
decision on. Clicking one opens it in the right panel as one of three question types:

- **"Same system, or two?"** — two records look like they might be the same real-world
  thing; you're shown what matched and what didn't, and choose Merge / Keep separate.
- **"Is this really confirmed?"** — a fact currently marked confirmed has since been
  contradicted; you choose whether it should be demoted, promoted, or the contradiction
  rejected.
- **"A tripwire fired — is it real?"** — you triage a fired alert (like the relocation in
  §5): accept it, dismiss it as noise, or hold it for a second look.

**In live mode these are real decisions** — each one is sent to the server, recorded, and
the graph rebuilt around it before the panel updates; it isn't a UI toggle that forgets
itself.

**One known limitation:** *"Same system, or two?"* does not currently stick. The decision
is recorded, but the two records aren't actually linked, so the same pair can resurface
later in the session. The other two decision types behave as described.

Review decisions live only in the running container and reset on restart, like everything
else you add during a session.

---

## 7. Troubleshooting

- **Stuck on "waiting for /health"** — give it up to 60 seconds on first start (it's
  building an internal index of the whole corpus); `make logs` shows what it's doing.
- **Port already in use** — `PORT=8010 make run`, or change the `docker run -p` mapping.
- **Free-form questions refuse with "need a key"** — expected without
  `ANTHROPIC_API_KEY` set; the one flagship question above always works regardless.
- **A restart resets everything** — by design. Nothing you do in the app (ingesting a
  document, making a review decision) is written outside the container, so
  `docker restart chanakya` is always a guaranteed clean reset back to the starting
  state.
- **The app looks like a fixed slideshow that ignores my clicks** — you're missing
  `?mode=live` in the URL; see §2.

---

## 8. Going deeper

- [`artifacts/design-note.md`](https://github.com/pragalbh-dev/osint/blob/main/artifacts/design-note.md)
  — the design writeup: why the system is built this way.
- `deploy/README.md` — the full operations runbook (publishing the image, hosting it
  with a public URL, rollback) — only relevant if you're standing up your own copy
  rather than using the one already running.
