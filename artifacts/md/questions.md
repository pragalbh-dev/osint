## Questions on the spine:

1. Right unit of analysis: 
    1. Should ontology be discovered? 
    2. Is there one knowledge graph and across statements I keep adding more entities and relationships into the same graph. 
2. HITL: 
    1. What are the control points of human in the loop system for the end user. 
3. 

## Questions to answer in C:

1. Get more into what depth looks like for this. 
2. credibility, triage and adaptation. : how do these 3 map, especially adaptation
3. Finding grain in the chaff? 
4. Sustaining that judgement as sources close and adversary methods change.
5. Right unit of analysis. 
6. What is the use? like it is basically anaysis of supply chain of enemy right? not within nation sleeper cel etc detection right??
7. commercial satellite imagery : how to use this? in procurement?

---

## Resolution map (where each question is now answered)

Worked through in the conversation and written into the design docs:

**Spine questions**
1. Right unit of analysis
   1. Ontology discovered? → **designed schema + extracted instances + human-gated extension** ·
      `../spine/01-graph-and-ontology.md`
   2. One graph, keep adding? → **yes, one graph; subject = lens; bi-level evidence/knowledge model** ·
      `../spine/01-graph-and-ontology.md`
2. HITL control points → **8 control points + HITL-as-a-service; escalate the ambiguous; overrides
   propagate** · `../spine/05-hitl-and-triage.md`

**Use Case C questions**
1. What depth looks like → **depth ladder (7 axes)** · `../C/00-overview.md`
2. Credibility / triage / adaptation mapping (esp. adaptation) → **credibility=scoring, triage=attention
   allocation, adaptation=freshness/coverage + learning loop** · `../spine/04-credibility.md`,
   `../spine/05-hitl-and-triage.md`, `../spine/06-adaptation.md`
3. Grain in the chaff → **a property across relevance/credibility/triage/retrieval/alerting, not one
   component** · `../spine/02-ingestion-and-unit.md`, `../spine/05-hitl-and-triage.md`
4. Sustaining judgement as sources close / adversary methods change → **= the adaptation axis; degrade
   visibly, never silently** · `../spine/06-adaptation.md`
5. Right unit of analysis (C) → **the sourced claim, not the document; materiality derived from target
   queries** · `../spine/02-ingestion-and-unit.md`, `../C/01-materiality-ontology.md`
6. What is the use? → **yes: external adversary-capability supply-chain + ORBAT, planning-level; NOT
   domestic/sleeper-cell, NOT targeting-grade** · `../C/00-overview.md`
7. Commercial satellite imagery → **confirmation/geolocation modality (promotes probable→confirmed); the
   deployment end of the chain the procurement trail predicts; two image tiers (satellite vs social)** ·
   `../spine/04-credibility.md`, `../C/00-overview.md`