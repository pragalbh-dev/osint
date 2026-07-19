export const meta = {
  name: 'eval-rca',
  description: 'Root-cause the EVAL end-to-end pipeline divergence; produce verified per-service handoffs',
  phases: [
    { title: 'Investigate', detail: 'one deep investigator per service, grounded in evidence + code' },
    { title: 'Verify', detail: 'adversarial check of each finding: correct? attributed to the right service?' },
    { title: 'Synthesize', detail: 'resolve attribution conflicts, dedup, build fix-order' },
    { title: 'Author', detail: 'write a self-contained handoff MD per service' },
  ],
}

const ROOT = '/home/synaptic/data-science/research/rough/osint/wt-EVAL'
const EVID = ROOT + '/tmp/conv/eval-rca'
const VENV = ROOT + '/backend/.venv/bin/python'

const CONTEXT = `
You are diagnosing an OSINT knowledge-graph pipeline that was run END-TO-END for the FIRST TIME over a real
LLM-extracted corpus (26 docs), and produces a graph FAR from the curated ground-truth oracle
(answer_key.json). This is a ROOT-CAUSE ANALYSIS — a different agent will later FIX each service, so your job
is to explain WHY, with hard evidence, and recommend concrete fixes. Attribute each root cause to the ONE
service that must own the fix (many symptoms are downstream of another service's defect — do not blame the
symptom-carrier).

PIPELINE: INGEST (LLM extraction of raw docs -> ClaimRecord bundles) -> rebuild() [ RESOLVE entity/place
resolution -> SCORE credibility/status/sufficiency/materiality -> knowledge view ] -> ASK (cited multi-hop
query) / MONITOR (declarative observables over view deltas). All merged Wave-1 code lives on this branch.

EVIDENCE (read before concluding):
- ${EVID}/00-evidence-summary.md  — histograms, oracle->view attribute-match (fragmentation), fired
  merges, the hero crash traceback, the observable result, the places result.
- ${EVID}/view_full.json          — the ACTUAL rebuilt view (294 nodes / 101 edges) the pipeline produced.
- ${EVID}/view_lens.json          — the lens-scoped view (empty).
- ${ROOT}/corpus/scenarios/hq9p_primary/claims/*.json  — the real extracted claim bundles (extraction output).
- ${ROOT}/corpus/scenarios/hq9p_primary/answer_key.json — the ORACLE (target: 20 nodes / 22 edges / 7 places).
- ${ROOT}/config/*.yaml           — the 8 config sections.
- ${ROOT}/backend/chanakya/<service>/  — the service source.
- To RE-PROBE the live pipeline yourself: run  \`export CHANAKYA_ROOT=${ROOT}; ${VENV} - <<'PY' ... PY\`
  (import 'eval.harness' after sys.path.insert(0,'${ROOT}/backend'); harness.load_scenario()/build_view()).
  A ready diagnostic is at /tmp/diagnose_eval.py and /tmp/gen_evidence.py — reuse or adapt. If you write a
  probe, name it /tmp/probe_<yourservice>.py to avoid collisions.

ESTABLISHED TOP-LEVEL SYMPTOMS (verify + explain; find more):
1. 452 claims -> 294 nodes (types: 109 'unknown', 51 source, 45 component, 29 variant, 19 basing_site, 17
   manufacturer, 14 known_gap, 9 unit, 1 contract_import_event) vs the oracle's 20 curated nodes.
2. Node ids are NAME-DERIVED (ent:<type>:<name>), never the oracle's canonical ids (mfr_casic, unit_paad...).
3. Entities FRAGMENTED (surface forms of one real entity not merged): comp_ht233->9 view nodes, unit_paad->8,
   site_karachi->9, mfr_casic->6, comp_tel_chassis->8.
4. ~25 AD-HOC edge predicates (e.g. "issued a formal press release confirming", "was unable to locate",
   "cannot be established from open sources", "has not acknowledged") instead of ontology edge types; the
   canonical relations supplies-component / exported-by / supersedes / sustained-by are emitted ZERO times.
5. Subject lens (anchors unit_paad, site_karachi) returns 0 nodes.
6. Statuses almost all 'probable'; 'confirmed' only for exact-single-name nodes.
7. Hero query CRASHES: KeyError 'node_id' at chanakya/agent/assemble.py:149 (_from_get_node).
8. Relocation observable fires 0 alerts; based-at@2021-rewind = [] (empty!); based-at@now =
   [('BIRM','Yongding Road','insufficient')] — the unit_hq9b->rawalpindi/rahwali basing edges + the
   supersedes edge are absent.
9. resolved_place_ref is EMPTY on ALL 294 nodes (place resolution produced nothing).

IMPORTANT: resolution DOES partially work — FD-2000 same-as HQ-9/P fired, FT-2000 & HQ-9BE distinct-from
fired, CASIC/BIRM/CPMIEC/Taian same-as fired. So credit what works; isolate what does not.
`

const SERVICES = [
  { key: 'ingest', name: 'INGEST (extraction)', code: 'backend/chanakya/ingest', model: 'opus',
    mandate: `Explain the EXTRACTION-side root causes. Specifically: (a) 109 nodes typed 'unknown' — is
    extraction emitting entity_type='unknown', or is view assembly defaulting an unrecognised type? trace it
    to source. (b) ~25 ad-hoc edge predicates instead of ontology edge types — does the extraction tool
    schema constrain predicates to ontology.yaml's edge types, or is it free-text? (c) the canonical relations
    supplies-component / exported-by / supersedes / sustained-by are NEVER emitted — why (schema? prompt?
    node-typing?). (d) 14 known_gap ENTITY nodes minted from "No SAR pass"-type sentences — is extraction
    emitting entity_type=known_gap per sentence? should gaps be claims/sufficiency, not entities? (e)
    sub-component granularity (every technical noun -> a component node). (f) resolved_place_ref empty on all
    nodes — did the geocoder freeze wgs84/geocode_candidates onto claim Location fields? inspect a real bundle
    (d07/d17/d18). (g) image docs cite .txt sidecars (not .png), so the imagery VLM lane never ran and
    'attribute --record' proposed 0 (all 'no-vlm-shape-observation'); does the oracle's attribution_inference
    require the .png/VLM lane? Read chanakya/ingest/{extract,schemas,transform,node_typing,adapters,imagery,
    attribute,dedup}.py (whatever exists) + 3-4 real bundles.` },
  { key: 'resolve', name: 'RESOLVE (entity + place resolution)', code: 'backend/chanakya/resolve', model: 'opus',
    mandate: `Explain the RESOLUTION-side root causes. (a) Massive UNDER-MERGE: why aren't surface forms of one
    entity collapsed — "HT-233" vs "HT-233 engagement radar" vs "engagement radar"; "Pakistan Army Air Defence
    (PAAD)" vs "...Command"; "Taian (Wanshan)" vs "Taian (Wanshan) special-vehicle works"? Examine blocking
    keys, name normalization/tokenization, attribute+relational scoring, and the auto_merge/hitl thresholds
    against these real pairs. (b) Wrong/weak merges: unit_hq9b attribute-matched only 'PAF'; check for a bad
    or missing merge. (c) resolved_place_ref EMPTY on all nodes — is resolve_place running at all? does it need
    coords frozen on claims (INGEST) or should it also match toponyms/aliases to the gazetteer? trace place
    resolution end-to-end and say exactly where it drops. (d) canonical id scheme: nodes get ent:<type>:<name>
    ids — is that RESOLVE's choice; can/should RESOLVE assign stable canonical ids, or is attribute-matching
    the agreed EVAL contract? (e) lens anchors unit_paad/site_karachi don't exist -> lens empty; how should
    anchors resolve? Read chanakya/resolve/*, config/resolution.yaml, config/places.yaml.` },
  { key: 'score', name: 'SCORE (credibility/status/sufficiency/materiality)', code: 'backend/chanakya/credibility', model: 'opus',
    mandate: `Explain the SCORING-side root causes, carefully separating SCORE-owned defects from downstream
    symptoms of RESOLVE fragmentation. (a) Statuses almost all 'probable' — is the confirmed gate failing
    because corroboration is split across fragmented duplicate nodes (RESOLVE's fault), or a SCORE/config
    issue? Prove it: would a correctly-merged entity (all its claims on one node) reach confirmed under the
    current gate + credibility.yaml? (b) Are the 14 known_gap nodes SCORE sufficiency output or INGEST
    extraction entities? the oracle models gap_ht233_maker/gap_launcher_count as known_gaps — what SHOULD
    produce them? (c) materiality/chokepoint: does any HT-233-ish node get chokepoint_status /
    substitutability_state computed? (d) contradiction/supersede/stale status handling. Read
    chanakya/{credibility,sufficiency,materiality}/*, config/credibility.yaml, config/templates.yaml.` },
  { key: 'data-c', name: 'DATA-C (config + corpus + oracle)', code: 'config', model: 'opus',
    mandate: `Explain the CONFIG/DATA root causes and enumerate concrete config changes. (a) resolution.yaml
    alias_table is too SPARSE for the real extraction surface forms — list the specific missing aliases needed
    to collapse the fragments (e.g. 'HT-233 engagement radar'/'engagement radar'->HT-233; 'Pakistan Army Air
    Defence Command'/'PAAD'->unit_paad; 'Taian (Wanshan) special-vehicle works'->Taian; 'HQ-9P long-range air
    defense system'->HQ-9/P). (b) ontology.yaml: does it declare the node types (contract_import_event,
    techdata_authority, interceptor_stockpile, known_gap) + edge types (supplies-component, exported-by,
    supersedes, sustained-by, equips, design-authority-for) the oracle uses? is 'unknown' a fallback? does the
    extraction get the ontology's allowed types/predicates to constrain output? (c) subjects.yaml lens anchors
    are canonical ids (unit_paad, site_karachi) the pipeline cannot mint -> lens empty; propose how anchors
    should be specified so the lens works on the real graph. (d) sources.yaml: image docs cite .txt not .png
    (imagery lane skipped) — intended? (e) the oracle uses hand-assigned canonical ids; does DATA-C need to
    ship a name->canonical-id/alias contract so the graph reaches those ids, or is attribute-match the agreed
    approach? (f) credibility.yaml knobs bearing on the everywhere-probable status. Read config/*.yaml +
    answer_key.json + a few corpus docs.` },
  { key: 'ask', name: 'ASK (query agent)', code: 'backend/chanakya/agent', model: 'opus',
    mandate: `Explain the ASK-side defects. (a) HARD BUG: hero query CRASHES with KeyError 'node_id' at
    chanakya/agent/assemble.py:149 (_from_get_node): r['node_id'] is missing from a get_node tool result.
    Trace exactly what the get_node tool returns vs what _from_get_node expects, and give the precise fix. (b)
    Robustness: the fixed hero path assumes canonical anchors + a clean chain exist; on the real (messy,
    name-derived-id, empty-lens) graph it must DEGRADE GRACEFULLY (reasoned refusal, never a crash). What must
    ASK receive from upstream (a working lens / resolved chain) to actually run the hero trace, and what should
    it do when that's absent? Read chanakya/agent/{__init__,assemble,loop,tools,context,validate}.py.` },
  { key: 'monitor', name: 'MONITOR (observables)', code: 'backend/chanakya/observe', model: 'opus',
    mandate: `Explain why the relocation observable fires 0 alerts, separating MONITOR-owned from upstream
    causes. Evidence: based-at@2021-rewind = [] (NO based-at edges at the 2021 epoch at all); based-at@now =
    [('BIRM','Yongding Road','insufficient')]; the unit_hq9b->site_rawalpindi/site_rahwali basing edges and the
    supersedes edge are absent. (a) Is this purely upstream (INGEST/RESOLVE never produce based-at edges with a
    stable edge_instance + a supersedes edge), or does the observable spec / evaluator also need work? (b) Why
    is based-at@2021 rewind EMPTY — is the as_of rewind filter (config.credibility.as_of + rebuild) hiding
    edges because claims lack report_time? investigate the rewind/timeref interaction. Read
    chanakya/observe/*, config/observables.yaml, and the as_of/rewind path in chanakya/view/pipeline.py +
    chanakya/timeref.py.` },
  { key: 'arch', name: 'ARCH / F0 / lens (cross-cutting id + lens design)', code: 'backend/chanakya/view', model: 'opus',
    mandate: `Resolve the CROSS-CUTTING architecture question. The pipeline mints name-derived ids
    (ent:<type>:<name>); the oracle, the subject lens, and the observables all reference hand-assigned
    canonical ids (unit_paad, mfr_casic, site_rawalpindi). (a) Is there ANY intended mechanism to produce
    canonical ids? If not, the fix spans config (subjects/observables anchors) + EVAL matching + possibly
    RESOLVE — say who owns each part. (b) apply_lens matches anchors by LITERAL id (chanakya/view/lens.py) ->
    empty on the real graph; right fix: lens resolves anchors by attribute/alias, or upstream provides
    canonical ids? (c) 'unknown' node type on 109 nodes: is there a fallback in view assembly / schema when an
    extracted type isn't an ontology node type? where? (d) Recommend THE canonical design decision (likely an
    F0-amendment or a RESOLVE/DATA-C contract) and precisely who owns it. Read chanakya/view/{pipeline,lens,
    export}.py, chanakya/schemas/*, chanakya/config/*.` },
]

const FINDINGS_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['service', 'findings'],
  properties: {
    service: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false,
        required: ['id', 'symptom', 'evidence_refs', 'root_cause', 'attributed_to', 'fix_direction', 'severity', 'confidence'],
        properties: {
          id: { type: 'string', description: 'short kebab slug' },
          symptom: { type: 'string' },
          evidence_refs: { type: 'array', items: { type: 'string' }, description: 'exact refs: file:line, view node/edge examples, config lines, evidence-summary section' },
          root_cause: { type: 'string' },
          attributed_to: { type: 'string', description: 'the ONE service key that owns the fix' },
          also_involves: { type: 'array', items: { type: 'string' } },
          fix_direction: { type: 'string', description: 'concrete recommended change' },
          severity: { type: 'string', enum: ['blocks-demo', 'major', 'minor'] },
          confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
      },
    },
    notes: { type: 'string' },
  },
}

const VERDICT_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['service', 'verdicts'],
  properties: {
    service: { type: 'string' },
    verdicts: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['finding_id', 'root_cause_correct', 'attribution_correct'],
        properties: {
          finding_id: { type: 'string' },
          root_cause_correct: { type: 'boolean' },
          attribution_correct: { type: 'boolean' },
          corrected_attribution: { type: 'string' },
          note: { type: 'string' },
        },
      },
    },
    missed: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['symptom', 'root_cause', 'attributed_to'],
        properties: {
          symptom: { type: 'string' }, root_cause: { type: 'string' },
          attributed_to: { type: 'string' }, evidence_refs: { type: 'array', items: { type: 'string' } },
        },
      },
    },
  },
}

const SYNTH_SCHEMA = {
  type: 'object', additionalProperties: false, required: ['fix_order', 'cross_service', 'services'],
  properties: {
    fix_order: { type: 'array', items: { type: 'string' }, description: 'ordered fix steps (service: what), dependency-first' },
    cross_service: { type: 'string', description: 'narrative of the dependency chain between fixes' },
    services: {
      type: 'array',
      items: {
        type: 'object', additionalProperties: false, required: ['service', 'confirmed_findings'],
        properties: {
          service: { type: 'string' },
          confirmed_findings: {
            type: 'array',
            items: {
              type: 'object', additionalProperties: false,
              required: ['id', 'symptom', 'root_cause', 'fix_direction', 'severity', 'evidence_refs'],
              properties: {
                id: { type: 'string' }, symptom: { type: 'string' }, root_cause: { type: 'string' },
                fix_direction: { type: 'string' }, severity: { type: 'string' },
                evidence_refs: { type: 'array', items: { type: 'string' } },
                depends_on: { type: 'array', items: { type: 'string' } },
              },
            },
          },
          reattributed_away: { type: 'array', items: { type: 'string' } },
        },
      },
    },
  },
}

// ── Phase 1+2: investigate then adversarially verify, per service (pipeline, no barrier) ──────────
phase('Investigate')
const investigated = await pipeline(
  SERVICES,
  (svc) => agent(
    `${CONTEXT}\n\n=== YOUR SERVICE: ${svc.name} (key: ${svc.key}; code: ${svc.code}) ===\n${svc.mandate}\n\n` +
    `Return structured findings. Every finding MUST carry concrete evidence_refs (exact file:line, exact view ` +
    `node/edge ids from view_full.json, exact config lines, or an evidence-summary section). Attribute each to ` +
    `the ONE service that owns the fix (use keys: ingest, resolve, score, data-c, ask, monitor, arch). Be ` +
    `exhaustive but precise; verify claims against the real files/probe before asserting.`,
    { label: `rca:${svc.key}`, phase: 'Investigate', schema: FINDINGS_SCHEMA, agentType: 'general-purpose', model: svc.model, effort: 'high' },
  ),
  (findings, svc) => agent(
    `${CONTEXT}\n\n=== ADVERSARIAL VERIFICATION for service ${svc.name} (key: ${svc.key}) ===\n` +
    `An investigator produced these findings. Independently CHECK each: (1) is the root_cause actually correct ` +
    `(re-read the code/evidence/probe — do not take it on faith)? (2) is attribution_correct — does the named ` +
    `service truly OWN the fix, or is this a downstream SYMPTOM of another service's defect (e.g. ` +
    `'everything probable' is likely caused by RESOLVE fragmentation, not SCORE)? If misattributed, give ` +
    `corrected_attribution. Also list any root causes the investigator MISSED for this service's area.\n\n` +
    `FINDINGS:\n${JSON.stringify(findings, null, 2)}`,
    { label: `verify:${svc.key}`, phase: 'Verify', schema: VERDICT_SCHEMA, agentType: 'general-purpose', model: 'opus', effort: 'high' },
  ).then((v) => ({ svc: svc.key, name: svc.name, findings, verdicts: v })),
)

const ok = investigated.filter(Boolean)
log(`investigated+verified ${ok.length}/${SERVICES.length} services`)

// ── Phase 3: synthesize — resolve attribution, dedup, fix-order (needs ALL findings → barrier) ────
phase('Synthesize')
const synthesis = await agent(
  `${CONTEXT}\n\n=== SYNTHESIS ===\nHere are all per-service investigator findings + adversarial verdicts. ` +
  `Produce the consolidated RCA: (1) drop or re-attribute findings the verifier flagged as wrong/misattributed ` +
  `(move a finding to the service that truly owns the fix); (2) dedup cross-service overlaps into one owner; ` +
  `(3) add any 'missed' root causes; (4) build a dependency-first FIX ORDER (which fixes unblock others — e.g. ` +
  `ontology/extraction constraints + alias seeds must precede resolution merge, which precedes status, which ` +
  `precedes lens/hero/observable). For each service list its confirmed_findings with evidence_refs + depends_on. ` +
  `Preserve every concrete evidence_ref.\n\nDATA:\n${JSON.stringify(ok, null, 2)}`,
  { label: 'synthesize', phase: 'Synthesize', schema: SYNTH_SCHEMA, model: 'opus', effort: 'high' },
)

// ── Phase 4: author one self-contained handoff MD per service ─────────────────────────────────────
phase('Author')
const svcMap = {}
for (const s of synthesis.services) svcMap[s.service] = s
await parallel(SERVICES.map((svc) => () => {
  const mine = svcMap[svc.key] || { service: svc.key, confirmed_findings: [] }
  return agent(
    `You are writing a SELF-CONTAINED root-cause HANDOFF for the ${svc.name} agent, who will fix these issues ` +
    `in a fresh worktree with no prior context. Write clean, skimmable Markdown to the file ` +
    `${EVID}/handoff-${svc.key}.md via the Write tool.\n\n` +
    `Structure:\n` +
    `# EVAL RCA handoff — ${svc.name}\n` +
    `- **Context** (2-3 sentences): the pipeline was run end-to-end for the first time over real extracted ` +
    `bundles; the graph diverges from the oracle; this handoff is your service's share of the fix. Reference ` +
    `the evidence bundle at tmp/conv/eval-rca/ (00-evidence-summary.md, view_full.json) + the generated ` +
    `bundles at corpus/scenarios/hq9p_primary/claims/.\n` +
    `- **TL;DR**: the 1-3 highest-severity things to fix.\n` +
    `- **Findings** (one section each, ordered by severity): Symptom -> Evidence (exact refs) -> Root cause -> ` +
    `Recommended fix -> Severity -> Cross-service dependencies (what must be fixed first / what this unblocks).\n` +
    `- **How to reproduce + verify your fix**: export CHANAKYA_ROOT=${ROOT}; use ${VENV} with ` +
    `/tmp/gen_evidence.py (regenerates the evidence bundle) after your change, and confirm the specific ` +
    `symptom is gone.\n\n` +
    `Keep every concrete evidence_ref (file:line, view node/edge ids, config lines). Do NOT invent findings ` +
    `beyond the data below. If confirmed_findings is empty for you, write a short note saying no independent ` +
    `defects were confirmed for this service (only downstream symptoms) and point to the owning services.\n\n` +
    `FIX ORDER (shared): ${JSON.stringify(synthesis.fix_order)}\n` +
    `CROSS-SERVICE: ${synthesis.cross_service}\n\n` +
    `YOUR CONFIRMED FINDINGS:\n${JSON.stringify(mine, null, 2)}\n\n` +
    `Return just the path you wrote.`,
    { label: `author:${svc.key}`, phase: 'Author', agentType: 'general-purpose', model: 'sonnet', effort: 'medium' },
  )
}))

return { services: ok.length, fix_order: synthesis.fix_order, synthesis }
