# Claude Conversation — Sarvam Chanakya OSINT Assignment (use-case decision)

> **Cleaned transcript.** The original export (`chat.txt`) interleaved Claude's internal reasoning/"thinking" blocks with the actual answers, with no clear tag between them. Those thinking blocks have been removed here — this file keeps only the user's questions and Claude's final answers, **verbatim**, so it's easy to browse. See the note on Q3 below for the one exception.
>
> Attachments provided by the user at the start of this conversation: *Understanding Strategic AI Use Cases.pdf*, *Sarvam AI Assignment for Pragalbh.pdf*, *a3261795-…-Sarvam_Assignment.pdf* — cleaned versions of all three are the other files in this `md/` folder.

---

## Q1

I am working on this assignemnt and this is my contetx so far, I need you to thouroughly analyse this, ine is the assignment doc, one is the chat with another agent, one is my rough planning notes,
I am currently at the stage of deciding which problem statement to chose and then move on ahead with abstraction design and other things,
For that I need more better understanding of problem C, current understanding of that feels like it will be a very complicated problem but idk the agent suggests its easier, it will involve entity deduplication whcih ig all the problems rquire? and then I feel since problem B in its statement explicitly mentions "theatres" which is part of problem A so I have a feeling that I cannot build it without building A, and then it also feels that if I build A it will be easier to extend into B, and then I feel if still the deliverable is best in C then Ig it is beneficial to build C so I need to take a decision, also need ot understand C in more depth and what all will it require and same for A and B so that I can atleast decide quickly.

### Answer

The most useful thing I can do first is dissolve the dependency knot, because it's making the decision look harder than it is.

The three use cases don't stack the way you're picturing. What stacks is a shared spine that all three sit on — and you already named it in your notes (page 9): data generation → ingest → structure with HITL → source credibility → alert/observable → cited multi-hop QnA, all over a designed ontology + queryable graph + cross-source entity resolution. That spine is the assignment. Re-read "what we are really testing": credibility, triage, adaptation, finding the grain in the chaff, HITL, sustaining judgment. None of that is A-, B-, or C-specific. It's the graded core, and you build it exactly once no matter which use case you pick.

Each use case is just a different layer bolted onto that spine. A adds a time-series analytics layer (baseline each location, compute deviation, correlate surges). B adds an intent-reasoning layer (ACH, deception resistance, MLCOA/MDCOA estimate). C adds a graph-depth layer (lifecycle ontology, supply-chain tracing, confirmed-vs-probable, freshness). So the question isn't "must I build A before B." It's: given that I'm building the spine regardless, which single top layer best shows off the spine's graded qualities with the least chance of dying in a live demo?

Your three specific worries, directly:

"B mentions theatres, which is part of A, so I can't build B without A." Red herring. "Theatre" and "front" are just domain words for "a place where military stuff happens." A cares about places; so does B; that's not an architectural dependency, it's both being military-geographic problems. B needs inputs that look like A's outputs ("there's anomalous activity at these locations"), but you can feed those in directly — assert a handful of observed activities and let the reasoning run. B's hard part (reasoning activity→intent under deception) is orthogonal to A's hard part (statistical baselining).

"If I build A, it's easier to extend into B." Marginally true, badly oversold in that Gemini thread. You'd have a feeder, yes — but A's deliverable (a deviation-index map) and B's deliverable (a warning estimate with MLCOA/MDCOA and a dissenting view) are almost entirely different artifacts. All the B-specific work still sits ahead of you after A is done. "A→B is cheap" is not a real reason to pick A.

"Entity dedup — don't all three need it?" Yes, so its mere presence can't be a tiebreaker. But its centrality differs sharply. In A and B it's supporting plumbing (resolve "Base X" = "Airfield Alpha" = coordinates). In C it's the marquee feature — the whole value of C rests on confidently fusing "Factory 404" = "State Research Bureau 404" = a chassis in a geolocated photo into one node, across customs / procurement / academic / social sources full of transliterations and shell-company aliases. C is the one use case where resolution being excellent is the entire game, which matters because the brief explicitly prizes "resolve identity across sources."

**Understanding C properly — and why "complicated" is a surface read**

C feels complicated because the domain is dense (ORBAT, variants, radars, command nodes, supply chains) and the ontology is rich. But the engineering is arguably the most contained of the three, and the split is what matters.

What makes C hard is design work — which is exactly what's being tested and exactly what coding agents can't do for you. You define a lifecycle ontology you can defend: node types (Manufacturer, Component, Variant, Unit/Formation, Basing site, Maintenance/Training node, Radar/Command node) and edges spanning manufacturer → import → component → induction → basing → sustenance. Real intellectual work — but bounded: you pick ONE capability (say, one long-range SAM system), and the entity universe becomes finite and knowable. You're not modeling the world, you're modeling one weapon system's anatomy and lifeline.

What makes C easy relative to A and B is that everything downstream of the ontology is deterministic traversal, not inference under uncertainty. No baselining, no z-scores, no threshold-tuning (A's live-demo landmine: too sensitive and the map screams, too dull and nothing fires on the call). No LLM having to consistently produce a correct judgment about hidden intent (B's reliability problem). And the "hard parts" the brief lists for C — provenance per node, confirmed vs probable, freshness stamps, stated gaps — are metadata discipline, not algorithms. They're about being rigorous, which you control completely.

So the Gemini thread was right that C has the lowest data-generation burden (a static structural corpus of ~10–15 docs; supply chains are snapshots, so you skip the longitudinal history A intrinsically needs) and the lowest tuning friction. But it undersold two real costs: the ontology depth above, and the resolution craft. Both are the right kind of hard — design and judgment, visible and gradeable — not the fragile kind.

Where C is unusually well-matched to what's actually graded, in four points:

First, C's deliverable is the credibility mandate. Its target output — "confirmed vs probable clearly separated, each node linked to its source and timestamp, gaps stated explicitly" — is "lead with credibility, not collection" rendered as a deliverable. In A and B you bolt credibility on; in C it's structural.

Second, C is the hardest to dismiss as an LLM wrapper. The brief explicitly warns that a "re-skinned commercial OSINT tool" or "a system that emits finished intelligence with no analyst in the loop" is not good. C is manifestly a system: an ontology, a graph, resolved entities, auditable nodes. B lives closest to the danger zone — its output is a text estimate an LLM writes, and a sharp interviewer may ask whether the hard system-building is real or you've prompt-engineered a warning memo. You'd spend energy defending B against that; C rebuts it by construction.

Third, the multi-hop query is naturally impressive and reliable. "Trace this deployed battery back to its component supplier and name the chokepoint" hops manufacturer → import → induction → basing along a graph you control — textbook multi-hop, fully auditable, and the "insufficient evidence" trap is trivial to plant (one deployment node with no corroborating source → the agent must say so instead of guessing a position). B's multi-hop is more thrilling but rides on the reasoning being correct every run; A's is the most mechanical.

Fourth, it fits how you're going to work. You said the test is about your process and you'll lean on agents. C concentrates your effort on the graded, agent-proof parts (ontology, resolution strategy, confidence/freshness discipline) and hands the boilerplate (traversal, extraction, the map/graph UI) to agents. B would concentrate effort on prompt-engineering (fickle, invites the wrapper critique); A on statistical tuning (agent-assisted but demo-fragile and least aligned with credibility).

**A and B, mostly their risks:**

A is the analytics play. Its intrinsic difficulty is that baselining requires longitudinal data — you can't show "deviation from baseline" with 15 files, you need a believable time series per base plus machinery whose thresholds you tune. Two live-demo failure modes: the baseline looks arbitrary, or the deviation index doesn't trip cleanly on the call. And "genuine correlation vs coincidence" across areas is real small-n statistics a sharp interviewer will probe. Highest data burden, most demo-fragile, least aligned with the credibility/triage emphasis. Pick it only if statistical anomaly detection is the skill you most want to showcase.

B is the reasoning play. Highest ceiling (deception, ACH, intent) and the most memorable if it works. But it's the hardest to make reliable, the most exposed to the "unsupported leap from activity to intent" failure the brief explicitly names, and counter-deception is research-hard — easy to claim, hard to show surviving an interviewer who says "now plant a fake signal and prove it resists." High variance: best case it's the standout, worst case it looks like a well-prompted memo generator. Pick it only if you're confident you can make the estimate deterministic across runs and rebut the wrapper critique live.

**Decision, and the one thing that flips it**

On the dimensions this test rewards — alignment with what's graded, demo reliability, "manifestly a system," data burden, fit with an agent-heavy workflow — C is the highest expected-value pick, for better reasons than the thread gave you. Its costs are real but front-loaded design costs (the ontology), which is the part you want to be spending judgment on and the part agents can't fake.

What would flip me to B: if your genuine edge, and the thing you most want them to remember, is LLM-reasoning-architecture showmanship, and you're confident you can make the intent estimate reproducible and defend it against a planted-signal probe. If that's you, B's ceiling is higher. If you're optimizing for a demo that works every time and lands squarely on what they said they're testing, it's C.

Two practical notes for whichever you lock. You must include at least one of image/video/social — text alone fails the brief. Your notes flagged social as infeasible; that's fine, imagery is the cleaner non-text modality for all three, and for C a VLM caption on a commercial/satellite image of a deployment site (matched into the supply-chain graph) satisfies the requirement without touching X's API. A frozen curated corpus even makes social feasible if you want it, since you're copying real posts into a static folder, not scraping live. And your "shared spine + pluggable module" instinct is both the right architecture and your best hedge: build the spine cleanly, implement C's module deeply, and in the design note show A's and B's layers plugging into the same spine — that demonstrates the range the brief invites ("or all three if you want to show range") without building all three, and it directly answers "what would you do with four more weeks."

Want me to go a level deeper on C's ontology and the concrete node/edge schema next, or lay out the shared-spine architecture so you can start scoping time per module?

---

## Q2

what does depth look like in each of these, since whatever i piuck i need to go deep and I also need to know that i have gone enough deep and that now I can build the other one probably.

### Answer

Depth here splits into two layers, and keeping them separate is what makes your "have I gone deep enough / can I now build another" question answerable.

**Spine depth vs. layer depth**

Most of the graded depth — call it 70% — lives in the spine you build regardless of use case: unit of analysis, ontology, entity resolution, credibility + corroboration, HITL, cited multi-hop RAG, the insufficient-evidence discipline, traceability. That's not A-depth or B-depth or C-depth; it's the thing the brief says it's really testing. The remaining ~30% is the use-case layer — the analytics layer (A), the reasoning layer (B), or the graph-depth layer (C).

This is the key to your meta-question: "I can now build the other one" is a statement about the spine, not the use case. Once the spine is deep and portable, a second use case costs only its layer. So there are really two "deep enough" gates — a spine gate (which doubles as your pivot signal) and a per-use-case layer gate.

**What spine depth looks like**

The shallow version of the spine is: fixed-size chunking, a flat entity list, exact-string entity matching, a hardcoded per-source credibility number, a decorative "analyst approved" print line, single-hop retrieval with a citation, and a system that always answers.

The deep version — and each of these is a place the brief explicitly points — is: the atomic unit is the claim or event, not the document (one doc holds many claims, one claim spans many docs); the ontology is typed and defensible (you can say which questions each type enables and which it excludes); resolution is multi-signal (alias tables + embeddings + geo-match + LLM disambiguation) with a confidence on every merge and the low-confidence merges routed to a human; credibility is a tunable function of user-defined factors (Module 1's exact wording) that propagates into claim confidence and drops for sources that look too clean or too perfectly placed; the HITL override changes downstream state (the edge, the confidence), not just a log; the agent decomposes a question, traverses 2–3 hops, and cites the exact source behind every claim while separating observed activity from inferred intent; and the insufficient-evidence rule fires correctly on a planted gap, naming what's missing and when coverage is next due.

The pivot gate (your "now I can build another" signal) is met when: the one worked query runs end-to-end every time; the insufficient-evidence rule trips on a deliberately planted gap; every claim/node is one-click traceable to source; the HITL override propagates; and — the portability test — you can point the exact same pipeline at a new subject, new observable, new question by editing config, without touching core code. If you can re-point it, the expensive 70% is done and reusable.

**Layer depth, per use case**

For each, there's a shallow version, a real hard part, and a "deep enough" line — and the cleanest sufficiency signal is whether you can beat that use case's signature rebuttal.

A (analytics layer). Shallow is a hardcoded "activity high" threshold. The climb goes: per-location baseline of tempo/count/logistics → a composite deviation index fusing apron + fuel + NOTAM + runway signals into one traceable per-base number → the real hard part, which is separating genuine cross-area correlation from coincidence when three bases spike at once. Deep enough is: composite deviation from a defensible baseline, a correlation test that distinguishes synchronized from coincidental (even a simple one), and a surge observable that fires and is fully traceable. A's signature rebuttal is "isn't that just coincidence?" — you're deep enough when you can answer that and state where your method breaks (small-n significance is shaky, and admitting that is the senior move). A's depth risk is that this is bottomless statistics; "defensible + limits stated" is the stopping point, not "solved."

B (reasoning layer). Shallow is asking an LLM "is this an attack?" The climb goes: structured competing hypotheses (exercise / signaling / mobilization) scored against evidence → reasoning about diagnosticity rather than counting activity (comms blackout and forward-deployed medical supplies are diagnostic of mobilization; loud media and open-apron parking of signaling) → the real hard part, deception resistance: discounting suspiciously clean sources, treating the absence of expected mobilization indicators as evidence, and being able to say "this looks planted." Deep enough is: an estimate with MLCOA/MDCOA, confidence per judgment, the specific observables that would confirm or deny each course of action with next-coverage timing, and a real dissenting view — plus it withholds a strong verdict when indicators are ambiguous. B's signature rebuttal is "aren't you just leaping from activity to intent — isn't this a prompted memo?" — you're deep enough when you can show it resisting a planted signal live and refusing to over-warn. B's depth risk is reproducibility: "deep enough" also requires the estimate be stable across runs, which is real cost you must budget.

C (graph-depth layer). Shallow is a who-shipped-what graph with exact-match nodes. The climb goes: the full lifecycle ontology instantiated (manufacturer → component → import → variant → unit → basing → sustenance) → resolution across the ugly aliases with confidence and HITL on the ambiguous merges → the real hard part, epistemic honesty: every node and edge carries provenance + confidence + freshness, confirmed is structurally separated from probable, and coverage gaps are stated. Deep enough is: any node is one-click-auditable to its source with confidence and freshness, probable holdings never masquerade as confirmed, one multi-hop trace runs deployment → component supplier → chokepoint, and the insufficient-evidence rule fires on an unsupported holding. C's signature rebuttal is "how do you know that node is real — confirmed or guessed?" — you're deep enough when an interviewer can click anything and get a truthful provenance/confidence/freshness answer. C's depth risk is over-engineering the ontology; the signal is "exactly as rich as the questions require, no richer."

**The unified test**

Spine gate (also the pivot gate): worked query runs reproducibly, insufficient-evidence fires on a planted gap, everything traceable, HITL propagates, pipeline re-points via config. Layer gate: the use case's target-output fields are all present and you can beat its signature rebuttal. When both gates pass, that use case is done to depth, and the spine is portable enough to add a second.

**What the second one actually costs**

Being precise, since "probably build the other one" deserves a real number: the spine and the data-generation skill are reused, the graph view is largely reused, so a second use case costs roughly its layer + its bespoke visualization + a new scenario corpus — call it 25–35% of the first, not zero but heavily amortized.

And the pairs aren't symmetric. B is architecturally the consumer of the other two — it reasons over anomalies (A's output) and over quiet supply-chain shipments as mobilization indicators (C's output, as we covered last turn). So if you want the option of a second use case for the "show range" credit, build A or C first and keep B as the layer you add on top, because B naturally sits above them. That gives you a clean through-line if you go with the earlier recommendation: C deep first (auditable ORBAT + supply-chain graph, which is where the spine's credibility discipline shines), then, if time allows, B bolted on as a reasoning layer that reads C's chokepoint signals to estimate intent. That's a coherent, impressive two-step rather than two disconnected demos — and even if you never build B, the design note gets to describe exactly how it would plug in, which is your "four more weeks" answer.

Want me to turn these gates into an actual scoping checklist with rough day-by-day time allocation across spine vs. layer, so you can see whether one-deep or one-deep-plus-B fits in the seven days?

---

## Q3

> **Note on this question:** the raw export did not contain the verbatim text of this question — only Claude's paraphrase of it (written while reasoning) survived. Reconstructed below from that paraphrase; treat it as close-but-not-guaranteed-exact wording, unlike Q1, Q2, and Q4 which are verbatim.

What do I think about the logic of using generated data instead of hunting real-world data from multiple sources? And how to make each generated data type messy enough to replicate the real world — since that's what they're testing (per the brief's "messy open-source data" language).

### Answer

My take on the logic first, then a per-source messiness recipe.

The logic is half-right, and the half that's wrong is the dangerous half.

Controlling the corpus is the correct instinct, and the brief backs you: it de-prioritizes collection ("lead with credibility, not collection"), demands reproducibility, and — the point most people miss — requires you to guarantee that specific graded scenarios exist in the data. Your credibility logic needs a claim that's single-sourced and one that's contradicted; your HITL demo needs an ambiguous merge; your insufficient-evidence rule needs a real gap; a B-layer would need a planted signal. Random real data won't reliably hand you clean instances of all of those in a week. So generating or curating to engineer those scenarios in isn't cheating — it's test design, and it's the senior move.

Where the logic breaks is "fully LLM-generated," which has two failure modes that would cost you on the call:

Circularity. If you generate the corpus with an LLM that has your ontology in mind, then extract it with an LLM using the same ontology, you've built a closed loop that proves nothing. A sharp interviewer will ask "did your generator know the schema your extractor is looking for?" — and if the answer is yes, the demo deflates. You'd be testing your extractor against your own generator.

Fake messiness. This is the subtler killer. When you tell an LLM "make this messy," it produces a stylized imagination of messiness — deliberate typos, a "poorly translated" line that's still cleanly parseable, a NOTAM that obeys NOTAM format too obediently. Real messiness has structure an LLM doesn't reproduce: true format violations, encoding garbage, half-truncated records, ICAO codes instead of names, HS codes instead of descriptions, transliteration variance that follows real conventions, coincidental near-duplicates that aren't the same entity. LLM-messiness is messiness as a human pictures it, which your extractor (also an LLM) finds suspiciously easy to un-mess. Since "find structure in messy open-source data" is the literal thing being tested, fake-messy data means you pass a test you set too easy.

So: hybrid, with the messiness sourced from reality.

Take real specimens as format templates — one real NOTAM string, a couple of real customs manifest rows, a real tender notice, real tweet phrasings, a real trade-media paragraph. Preserve their structure and noise; vary the entities and values synthetically. Now the messiness is real (real format, real abbreviations, real noise structure) while the content stays controllable.

Then apply messiness as enumerable corruption operators, not free-form "make it messy." Define discrete transforms — alias-substitution, timestamp-drop, date-format-flip, coordinate-fuzz, truncation, transliteration, sarcasm-injection, contradiction-injection, irrelevant-filler — and apply them programmatically. This is your decoupled generation engine, but controlled: you can report exactly which corruptions each scenario contains, which is gold in the design note and hard to break under questioning.

Engineer the scenario structure above the per-doc noise: at least one multi-source corroborated claim, one single-source claim (→ low confidence), one contradicted pair, one too-clean planted source, and one gap no source covers (→ insufficient evidence). That's what gives your credibility, corroboration, and multi-hop logic something to bite on.

Two guardrails kill the circularity objection: keep the generator blind to the ontology (it emits raw text/records only, never your clean fields — the pipeline earns the extraction), and keep a handful of real, uncurated documents in the mix that the pipeline processes cold. Nothing rebuts "does it work on real scrappy data" like pointing it at a real scrappy document live.

How each source type is messy in the real world (lean on the ones your pick uses; the patterns transfer):

Customs / shipping (core to C): HS codes not descriptions ("8517.62", not "radar module"); consignee as a shell or freight forwarder, not the end user; company names transliterated differently across rows; dual-use goods described blandly; missing values. The resolution challenge lives here.

Procurement / tenders (core to C): contract and lot numbers, bureaucratic phrasing, redactions, "as per Annexure III" pointing at a doc you don't have, vendor names that don't match the customs names — and a tender for "spares" that only implies an inducted system (probable, not confirmed).

Academic / trade media (core to C): the same system under three names (S-400 / SA-21 Growler / Triumf) — the biggest entity-resolution trap; hedged language ("reportedly", "believed to"); dated facts printed in a recent paper (freshness).

Satellite / commercial imagery (your image modality): cloud cover and occlusion (the classic insufficient-evidence trap); low resolution and ambiguous objects; capture time ≠ event time; old imagery passed as current; and AI-edited images as your M4 hook.

Social media: slang, no punctuation, colloquial place names ("the old Arakkonam strip"), no coordinates, relative times ("this morning"), hype ("MASSIVE convoy!!!" = three trucks), secondhand rumor, and — the most common real-world misinformation — a real image recycled from an old event under a new false caption (miscaptioning, not deepfakes).

NOTAMs: the unformatted uppercase code string; abbreviations (RWY, MAINT); ICAO codes not names (VOAR, not "Arakkonam"); coordinates buried in the Q-line; "maintenance" as a cover reason; superseding NOTAMs that cancel earlier ones.

Official press releases: euphemism ("routine exercise"), omission, high credibility but incomplete, and framing that contradicts the social-media picture — exactly the corroboration tension you want.

The part that actually scores: own it out loud. In the design note and on the call, state the data strategy and its limits plainly — "I generated frozen scenarios the pipeline had never seen, seeded the messiness from real source specimens rather than an LLM's idea of messy, kept the generator blind to my ontology, and included real uncurated documents; here's where this still differs from production and where it breaks at scale." Naming the tradeoff is the judgment they're grading. A candidate who hides the synthetic nature reads junior; one who architects around its weaknesses reads senior.

Want me to spec the corruption-operator engine — the transform list, the scenario-structure schema, and the generator/pipeline separation — so you can hand it straight to a coding agent?

---

## Q4

hmm now on planting deep fakes: so i fel checking for ai generated/deepfake/misinformatiojn is basically just misinformation judgement because ai generated cant be chefkd since ai can genertte any post of a real person and it might stae facts like donald trump is the president of uda, what it really means is that can i corroborqte this infrmation from any other source, etc : this is what i feel, what do you think

### Answer

You're about 70% right, and the 30% you're missing is the part the assignment cares most about — so worth getting sharp.

Where you're right: trying to detect "was this made by AI" is the wrong target, and you already knew this — your own notes say everything's written with AI now and the point is finding fake content, not AI content. For a text claim, authorship is irrelevant: an AI-written post saying "Trump is president" is true and corroborable; an AI-written post saying something false is misinformation regardless of who typed it. So for text, yes, it collapses into content veracity — credibility plus corroboration. That reframe is mature and it matches the brief, which says "misinformation," not "AI text."

Where the model has a hole: you're collapsing everything into "corroborate the claim," and that misses two things separate from veracity — and it's exactly where OSINT misinformation concentrates. There are three orthogonal axes, not one:

Content veracity — is the claim true? → corroboration + credibility. (Your axis.)

Artifact integrity — is this specific image/video authentic and unmanipulated?

Contextual provenance — is this artifact correctly attributed to the claimed time/place/event, even when the image itself is 100% real and unedited?

Your Trump example is the easy case that makes corroboration look sufficient. Flip it: an AI-generated video of a specific general announcing mobilization. "Corroborating the claim" fails, because the corroboration is other posts of the same fake video — you have to assess the artifact, not the claim. And the single most common real-world "misinformation" isn't a deepfake at all — it's a real, unedited photo of a 2019 convoy reposted today with a false caption. The image is real, the claim might even look "corroborated" by everyone resharing the same recycled photo, but its evidentiary value is zero. Corroboration can't catch that; provenance (first-seen date, reverse image) can.

The dangerous part — and why the assignment cares: corroboration is gameable. This is Use Case B's entire threat model and the brief's counter-deception mandate ("stay resistant to planted or withheld signals; recognise when it's being deceived; a source that feels too clean must drop in credibility"). An adversary running a deception op doesn't plant one fake — they plant the fake image and two "independent" posts referencing it. A corroboration-only system counts three sources and raises confidence on the fabrication. So collapsing M4 into corroboration builds precisely the system the adversary wants you to have. That's the failure they're testing for.

The synthesis — and here your instinct is right, just at the wrong layer: you're correct that it all funnels into one unified trustworthiness judgment (a single confidence per claim/node). What's wrong is treating corroboration as the only input to that score. Integrity and provenance are separate inputs feeding the same score. Output: unified. Inputs: three axes.

What the "credible attempt" looks like in seven days — the brief asks for credible, not a solved deepfake detector, so cheap defensible signals that each apply a credibility penalty rather than a binary fake/real verdict:

VLM caption-vs-image consistency: run a VLM on the image, compare to the text claim. Caption says "S-400 launcher at Base X," VLM sees a civilian truck or 95% cloud → flag. Cheap, and it demos beautifully.

Cross-source physical consistency: satellite reports total cloud cover, but a "clear daylight photo" of the same base the same day exists → suspicious.

Provenance / recency: a first-seen date or reverse-image signal catches the recycled photo. In a sandbox you tag the planted image "first-seen 2019" and the check fires on the date mismatch — the design is what you're demonstrating.

Coordinated inauthenticity (social text, not media): 40 near-identical posts across accounts in a ten-minute window → manufactured consensus, discount it. This is the "too clean" signal, and it's a network signal, not a content one.

If you go with C, this slots straight into your confidence/freshness machinery: a geolocated photo claiming a launcher at a site runs the VLM and provenance checks, and the result decides whether that node lands as confirmed or probable. M4 stops being a bolted-on module and becomes part of the confirmed-vs-probable discipline.

And the demo flex writes itself: plant one fabricated-but-corroborated item, and show the system refusing to be fooled because an integrity signal overrode the corroboration count. That single moment proves you didn't fall into the corroboration-only trap — which is the exact judgment they're grading.
