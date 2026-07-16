# Sarvam Assignment

Status: In progress

[Tasks Tracker](https://app.notion.com/p/39ecebc56f6d805b9e14e5ce25ca7030?pvs=21)

# Understanding of the problem statement:

***A working demo of an OSINT analysis and monitoring system.*** 

### What is being tested

How I find structure in messy open-source data. 

How I reason about what to build. 

How far you can push a real system in seven days. 

Depth Over coverage.

We care far more about judgment and the quality of the working system than about any specific stack.

hard parts : to pay more attention to while building : 

credibility, triage and adaptation.

Finding the grain in the chaff,

keeping a human analyst in the loop,

Sustaining that judgement as sources close and adversary methods change.

Directions: 

Treat it the way you would treat a live problem landing on your desk.

The Product requirement: 

Blanket: 

“To develop an ***AI-Powered OSINT Analysis and Monitoring system*** that can apply advanced and state of the art AI and statistical Algorithms to undertake analysis and real time monitoring of user defined subjects / topics / information domain through sifting of vast amount of global OSINT Data.” 

Be able to analyse and scale with the Volume of open source data to provide time sensitive intelligence. 

Weed out Deep Fake content. 

Intuitive presentation of actionable intelligence through an interactive application. 

Actual Assignment: 

***A Vertical slice***

***Runs e2e***

For one user-defined subject

Over a small, messy, multi-source open-source corpus (text plus at least one of image / video / social).

Bare minimum for the product:

Ingests heterogeneous open sources

Discovers an ontology

Resolves entities across sources and scores source credibility

Monitors user-defined subjects in near-real-time

Visualises intuitively

Answers hard questions

Bare min for the assignment: 

Ingest and organise the corpus from at least two source types, and ***find the right unit of analysis*** rather than blindly chunking.

Structure it into ***entities, relationships and events*** under an ***ontology you designed and can defend***; build a ***queryable graph***; ***resolve identity across sources.***

***Score source credibility*** and ***require corroboration*** (Module 1); make a credible attempt at ***flagging*** manipulated / AI-generated media or ***misinformation*** (Module 4).

Define at least one ***“observable”*** that fires an alert on a condition, to show the real-time-monitoring idea. 

Answer ***one non-trivial, multi-hop question*** ***through an agent***, returning an answer that ***cites the exact source evidence behind every claim.***

***Present the result intuitively*** — a short cited assessment (Module 5) plus at least one visualisation (geospatial or graph).

Credibility, triage and adaptation.

Lead with credibility, not collection.

Technical emphasis: 

Framings are illustrative and the specific subject is your
choice.

Building a good knowledge graph and ingestion system . 

Good ontology. 

Right unit of analysis. 

Deduplication. 

Source credebility. 

HITL. (hence can assume that the actual information graph that we are building is certainly correct to the extent it is designed to be.)

Cited multi-hop RAG. 

Since it is a goal oriented project: 

How well it functions matters a lot. 

So put more time into encoding good workflows in the system. 

Good decision making. 

Runnable code seems weird way to put it. 

See if you can have it hosted with a frontend built. 

Note:

Design note importance and vertical slice and “what looks good components”:

ontology, ingestion / resolution / retrieval design, credibility and
corroboration logic, key tradeoffs, what you’d do with four more weeks, and where it breaks at scale.

I don’t see them giving any emphasis on figuring out how to get data. 

So the data part ultimately is only important for the goal of showing that the algorithm works on messy data. That’s all. 

Main importance is on the system and design. 

### Individual problem statements:

#### Multi-theatre air-posture picture & correlated-surge early warning — strategic

Keep an Eye on multiple airbases and related areas of interest. 

Surface correlated surge indicators. 

#### Collusive multi-front escalation warning / anticipatory I&W — strategic

Indications and Warnings system: 

This is a standard system : need to figure out how it works in the military. 

#### Order-of-battle & supply-chain map of an adversary capability — operational

The rough plan: 

First figure out all the data sources that can be used in each problem statement. 

Figure out the which statement can you tackle by actually being able to ingest real data. 

Then figure out how will you use this data to actually make sure there are observable scenarios that trip etc. 

Questions to answer before

See if real data is even feasible and if not then why not | Need solid reasoning for doing anything. 

What seems feasible so far: 

Satellite imagery

Official government news

Diplomatic and press releases

Procurement and Tender records

Aviation NOTAMs

Nav-warnings

What doesn’t seem feasible for various reasons including feasibility: 

Social media / X / YouTube

And if so make your best effort to show that it will work on real data. 

Need to seed in real data maybe or something. 

Define Deep fake: 

We don’t want to detect anything written with AI,

Everything will be written with AI ultimately and even today. 

What we need is to basically find fake content. | This is more of like detecting bad information. 

What does Runs e2e mean: 

For one user-defined subject : when will user define the subject ? 

What does the Right unit of analysis mean

How to fire an observable? 

Finding the grain in the chaff,: what does this refer to? 

like is this referring to RAG? 

or the alert system? 

Sustaining that judgement as sources close and adversary methods change. : what does this mean. 

What does “user defined subject” mean here? 

Pick a vertical slice based on which one seems the fastest to build in depth. 

Main decision pointers: 

Data feasibility. 

What does depth look like for this vertical. 

Maybe more subjects? 

Maybe more strategies for that subject? 

Choose the “subject” for your vertical. 

[Based on what is important and is being thoroughly tested:](https://app.notion.com/p/Sarvam-Assignment-39ecebc56f6d802ab08feebd553e7321?pvs=21) 

Figure out what all to take care of in the designing, planning, scoping of the chosen vertical slice. 

Figure put how much time to give each step in the process. 

This is gonna be a very challenging decision

Make sure you stay true to the problem statement and end user and what is being tested. 

Scoping 

Data generation 

Logic development 

Design and Frontend 

Presentation, design doc, deployment instructions. 

Create a raw data generation strategy. 

Figure out how much raw data to generate. 

Seeding required? 

Create a suitable reusable parametered skill or way of data generation with claude and have it call the models for generation of such data. 

This should be automated enough to require your input in very minimum frequency. 

## Decision making

Do not get too into what is the best stack, just choose any stack to make demo feasible, because demos are not about scale. 

Note down all the decisions so that you are able to later prepare a doc of those quickly. 

### Development:

Since all problems statements have a outer abstraction layer of 

Data generation → Ingest → structure with HITL → Source credibility → Alert system → QnA 

HENCE : The first time you are setting things up, take care of this abstraction layer so that: extending to the next system is super fast and almost automated, all you should have to do is make each step’s/module’s specification. 

Ingest the decision making context into the builder’s memory/context