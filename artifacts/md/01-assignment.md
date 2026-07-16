# Sarvam AI · Chanakya · Take-Home Assignment

**AI-Based OSINT Analysis & Monitoring System | For Pragalbh**
Build a working demo — one week | Timeline – 20th July 12PM | CONFIDENTIAL

*(Converted from `Sarvam AI Assignment for Pragalbh.pdf`, verbatim.)*

---

This is a take-home for a Senior Data Scientist role on Chanakya, Sarvam's strategic-sector (defence and public-sector) team. The ask is simple to state and hard to do well: build a working demo of an OSINT analysis and monitoring system — something that runs, not a slide deck or a demo. We are testing how you find structure in messy open-source data, how you reason about what to build, and how far you can push a real system in seven days. Treat it the way you would treat a live problem landing on your desk.

## The public problem statement

The Indian Air Force has published this challenge under the iDEX ADITI 4.0 scheme (Ministry of Defence / Defence Innovation Organisation), as Problem Statement 18. Verbatim:

> "To develop an AI-Powered OSINT Analysis and Monitoring system that can apply advanced and state of the art AI and statistical Algorithms to undertake analysis and real time monitoring of user defined subjects / topics / information domain through sifting of vast amount of global OSINT Data."

The stated need: traditional data handling cannot keep up with the volume of open-source data, limited manpower, and time-sensitive intelligence. The PS calls for NLP, LLMs, web scraping, computer vision and clustering to automate extraction, analysis and interpretation; for identifying and weeding out artificially generated / deep-fake content ("misinformation"); and for intuitive presentation of actionable intelligence through an interactive application. The broad plan is a five-module application:

| Module | PS 18 definition (verbatim) |
|---|---|
| Module 1 | Source credibility check — definition of credibility based on user defined factors / criterion. |
| Module 2 | Open-Source content analysis. |
| Module 3 | Social media content analysis. |
| Module 4 | Images & video analysis. |
| Module 5 | Report extraction and GIS based outputs (intuitive visualisation) based on open source LLMs. |

Application, verbatim: "the tool would be utilised as one of the inputs to the overall Intelligence architecture of IAF." Project outcome: "Development of AI powered OSINT tool capable of analysis & real time monitoring of user defined subject & social media stacks."

Sarvam AI has already built a system and applied to this challenge. What we want from you is independent: a working demo built off this public problem statement and your own design.

## The capability bar — what "good" looks like

We have a working reference build of this system. At a high level, the reference platform:

- Ingests heterogeneous open sources — satellite imagery (analysed by a vision-language model), social media / X / YouTube, official government news, diplomatic and press releases, procurement and tender records, aviation NOTAMs and nav-warnings — into one organised corpus.
- Discovers an ontology from that corpus (entity types, relationships, identity keys) and builds a queryable knowledge graph over it.
- Resolves entities across sources and scores source credibility, enforces a multi-source corroboration rule, keeps a human analyst in the loop (accept / reject / override), and traces every claim back to the exact source file.
- Monitors user-defined subjects in near-real-time via a live signal feed and analyst-defined "observable" tripwires that fire when a condition is met (e.g. a logistics surge, a comms blackout, a sustained fuel build-up).
- Visualises intuitively — an entity / ORBAT layer on a geospatial (Bhuvan / ISRO) basemap with confidence-coded status, plus a graph explorer.
- Answers hard questions through a multi-agent deep-research step that decomposes a question into sub-questions, traverses the graph, and returns a cited answer separating observed activity from inferred intent — and rolls findings into a structured report with confidence levels and inline citations.

Notice how this maps onto the five PS modules: credibility + corroboration (M1), open-source and social analysis (M2, M3), VLM on imagery and video (M4), and the cited report plus geospatial visualisation (M5).

## The assignment — build a working demo (one week)

Build a working vertical slice that runs end-to-end for one user-defined subject over a small, messy, multi-source open-source corpus (text plus at least one of image / video / social). Depth over coverage. Concretely, it should:

- Ingest and organise the corpus from at least two source types, and find the right unit of analysis rather than blindly chunking.
- Structure it into entities, relationships and events under an ontology you designed and can defend; build a queryable graph; resolve identity across sources.
- Score source credibility and require corroboration (Module 1); make a credible attempt at flagging manipulated / AI-generated media or misinformation (Module 4).
- Define at least one "observable" that fires an alert on a condition, to show the real-time-monitoring idea.
- Answer one non-trivial, multi-hop question through an agent, returning an answer that cites the exact source evidence behind every claim.
- Present the result intuitively — a short cited assessment (Module 5) plus at least one visualisation (geospatial or graph).

Architecture, storage, retrieval strategy, models and resolution logic are all your call. We care far more about judgment and the quality of the working system than about any specific stack.

## Deliverables

- A working demo — code we can run, or a short recorded run if setup is heavy. Reproducibility matters.
- A 2–3 page design note: your ontology, ingestion / resolution / retrieval design, credibility and corroboration logic, key tradeoffs, what you'd do with four more weeks, and where it breaks at scale.
- One worked query, shown end-to-end, with cited evidence — this will happen on call.

## What we are really testing

Beneath the five modules, the hard part of this problem is credibility, triage and adaptation. Finding the grain in the chaff, keeping a human analyst in the loop, and sustaining that judgement as sources close and adversary methods change. Lead with credibility, not collection. A re-skinned commercial OSINT tool, a social-media-only monitor, or a system that emits finished intelligence with no analyst in the loop is explicitly not what good looks like.

> **Non-negotiable:** where evidence is absent, ambiguous or contradictory, the system must return an explicit "insufficient evidence to assess" — stating what is missing and when the next coverage is expected. Fabricated or hallucinated assessments in evidence-sparse cases are disqualifying.

For whichever use case you pick, aim to show one thread end-to-end — source → credibility → triage → analyst → geo-tagged output. We are looking for someone who understands the problem, not a dashboard.

## Three use cases — pick one, or all three

Below are three problem shapes the system should be able to handle. Two are strategic; one is a focused operational task. Pick one to go deep on, or take on all three if you want to show range — we would far rather see one done with real depth than three done shallowly. Framings are illustrative and the specific subject is your choice.

### A · Multi-theatre air-posture picture & correlated-surge early warning — strategic

- **The shape.** Build and maintain a fused, longitudinal picture of air-posture across several areas of interest, and surface correlated surge indicators — apron / shelter activity, fuel and munitions logistics, runway works, airspace / NOTAM activations, sortie tempo, new platforms — from optical / SAR imagery, flight-tracking, procurement disclosures, state and regional media, and geolocated social media.
- **The hard part.** Baseline each location, flag deviation from baseline, and distinguish genuine cross-area correlation from coincidence.
- **Target output.** A geo-tagged, GIS-displayable picture per area and fused across areas, with baseline-vs-current status, a composite deviation index, and correlated-surge alerts — every data point one-click traceable to source, confidence grounded in corroboration, no synthetic gap-filling.

### B · Collusive multi-front escalation warning / anticipatory I&W — strategic

- **The shape.** The hard question is not what happened but what is about to happen — and whether adversary activity is routine exercise, coercive signalling, or genuine pre-conflict mobilisation. Fuse every source type across theatres to detect synchronisation across fronts, and reason from observed activity to probable intent without over-reaching.
- **The hard part.** Separate exercise and signalling from real mobilisation; stay resistant to planted or withheld signals; recognise when the system is being deceived rather than confidently mis-warn.
- **Target output.** A strategic warning estimate — current posture, the most-likely and most-dangerous courses of action, explicit confidence per judgement, the specific observable indicators that would confirm or deny each course of action and when next coverage is due, and a clearly marked alternative / dissenting view. Every judgement traceable to source; no unsupported leap from activity to intent.

### C · Order-of-battle & supply-chain map of an adversary capability — operational

- **The shape.** From open sources only — procurement and contract disclosures, customs / shipping / trade data, official and trade media, exercise reporting, technical and academic literature, commercial satellite imagery and geolocated social media — assemble a fragmented picture into one auditable order-of-battle for a chosen adversary capability (say, a long-range air-defence system): types and variants, units and formations, dispositions, radars and command nodes. Then trace the full chain from manufacturer → import → induction → basing → sustenance (spares, resupply, maintenance, training), flagging dependencies and chokepoints.
- **The hard part.** Every entity carries source provenance and a confidence / freshness stamp; confirmed is separated from probable; coverage gaps are stated; unsupported holdings return "insufficient evidence" rather than a guessed position. Planning-awareness, not targeting-grade.
- **Target output.** A geo-referenced, one-click-auditable ORBAT and supply-chain map, confirmed vs probable clearly separated, each node linked to its source and timestamp, gaps stated explicitly.
