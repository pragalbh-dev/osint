# EVAL RCA — evidence bundle (real pipeline over frozen bundles)

- repo root: `/home/synaptic/data-science/research/rough/osint/wt-EVAL`
- claims seeded: **452**
- full view: **258 nodes / 100 edges / 79 events / 37 known_gaps**
- lens view (`lens-hq9p-pk`): **0 nodes / 0 edges**
- oracle: 20 nodes / 22 edges / 7 places

## view node-type histogram
- unknown: 86
- source: 57
- component: 40
- basing_site: 27
- variant: 15
- manufacturer: 12
- unit: 7
- known_gap: 6
- contract_import_event: 4
- trading_org: 4

## view edge-type histogram (ad-hoc predicates reveal ontology non-enforcement)
- same-as: 53
- equips: 11
- imported-by: 7
- inducted-into: 6
- manufactures: 5
- exported-by: 5
- component-of: 5
- distinct-from: 4
- based-at: 2
- design-authority-for: 1
- supplies-component: 1

## known_gap nodes (proliferation check)
- `ent:known_gap:ELINT/SIGINT cross-cue`  status=probable
- `ent:known_gap:SAR cross-check`  status=probable
- `ent:known_gap:SAR pass`  status=probable
- `ent:known_gap:imagery collect between 2022-01-27 and 2022-03-09`  status=probable
- `ent:known_gap:launcher count, reload status, and radar emission state`  status=probable
- `ent:known_gap:repeat EO pass`  status=probable

## ORACLE NODE -> VIEW attribute-match (RESOLVE under-merge evidence)
For each oracle node: view nodes of same type whose name/alias overlaps. >1 hit = fragmented (unmerged).

- **mfr_casic** (manufacturer, want_status=-) [FRAGMENTED-7]
    - ent:manufacturer:CASIC  status=confirmed
    - ent:manufacturer:CASIC's 23rd Research Institute  status=probable
    - ent:manufacturer:CASIC's 4th Academy  status=probable
    - ent:manufacturer:CASIC's Second Academy  status=probable
    - ent:manufacturer:China Aerospace Science and Industry Corporation  status=confirmed
    - ent:manufacturer:China National Precision Machinery Import & Export Corporation  status=probable
    - ent:manufacturer:China Precision Machinery Import-Export Corporation  status=probable
- **comp_ht233** (component, want_status=-) [FRAGMENTED-9]
    - ent:component:Battery/charging modules for engagement radar cabin  status=probable
    - ent:component:HQ-9P fire control radar  status=probable
    - ent:component:HT-233  status=confirmed
    - ent:component:HT-233 (H-200)  status=probable
    - ent:component:HT-233 engagement radar  status=probable
    - ent:component:HT-233 phased-array engagement radar  status=confirmed
    - ent:component:Type 305B (HT-233) fire-control set  status=probable
    - ent:component:engagement radar (possibly HT-233 or a derivative)  status=probable
- **comp_interceptor** (component, want_status=-) [FRAGMENTED-3]
    - ent:component:Calibration/test jigs for missile round check-out  status=probable
    - ent:component:FD-2000/HQ-9P interceptor  status=probable
    - ent:component:Ground support vehicle spares for erector-launcher chassis  status=probable
- **mfr_23rd_ri** (manufacturer, want_status=possible) [FRAGMENTED-5]
    - ent:manufacturer:Beijing Institute of Radio Measurement  status=probable
    - ent:manufacturer:CASIC  status=confirmed
    - ent:manufacturer:CASIC's 23rd Research Institute  status=probable
    - ent:manufacturer:CASIC's 4th Academy  status=probable
    - ent:manufacturer:CASIC's Second Academy  status=probable
- **mfr_4th_academy** (manufacturer, want_status=possible) [FRAGMENTED-4]
    - ent:manufacturer:CASIC  status=confirmed
    - ent:manufacturer:CASIC's 23rd Research Institute  status=probable
    - ent:manufacturer:CASIC's 4th Academy  status=probable
    - ent:manufacturer:CASIC's Second Academy  status=probable
- **mfr_taian** (manufacturer, want_status=confirmed) [FRAGMENTED-2]
    - ent:manufacturer:Taian  status=probable
    - ent:manufacturer:Taian (Wanshan) special-vehicle works  status=probable
- **comp_tel_chassis** (component, want_status=-) [FRAGMENTED-7]
    - ent:component:Ground support vehicle spares for erector-launcher chassis  status=probable
    - ent:component:HQ-9/P TEL  status=probable
    - ent:component:TEL  status=probable
    - ent:component:WS-series heavy 8x8 special wheeled chassis  status=probable
    - ent:component:heavy 8x8 special wheeled chassis  status=probable
    - ent:component:transporter-erector-launcher (TEL) platform  status=probable
    - ent:component:transporter-erector-launchers (TELs)  status=probable
- **gap_ht233_maker** (known_gap, want_status=-) [MISSING]
- **sustain_techdata** (techdata_authority, want_status=probable) [MISSING]
- **sustain_spares** (interceptor_stockpile, want_status=probable) [MISSING]
- **var_hq9p** (variant, want_status=-) [FRAGMENTED-6]
    - ent:variant:FD-2000 long-range surface-to-air missile system  status=probable
    - ent:variant:FD-2000/HQ-9P  status=probable
    - ent:variant:FD-2000B  status=probable
    - ent:variant:HQ-9  status=confirmed
    - ent:variant:HQ-9/P  status=confirmed
    - ent:variant:HQ-9P long-range air defense system  status=probable
- **var_hq9be** (variant, want_status=-) [FRAGMENTED-3]
    - ent:variant:HQ-9  status=confirmed
    - ent:variant:HQ-9B  status=confirmed
    - ent:variant:HQ-9BE  status=confirmed
- **alias_ft2000** (variant, want_status=-) [OK-1]
    - ent:variant:FT-2000  status=probable
- **import_2021** (contract_import_event, want_status=confirmed) [MISSING]
- **unit_paad** (unit, want_status=confirmed) [FRAGMENTED-7]
    - ent:unit:Air Defence Command  status=probable
    - ent:unit:Army Air Defence Command  status=probable
    - ent:unit:Pakistan Air Force  status=confirmed
    - ent:unit:Pakistan Army Air Defence  status=probable
    - ent:unit:Pakistan Army Air Defence Command  status=confirmed
    - ent:unit:Pakistan Army's Army Air Defence Command  status=probable
    - ent:unit:People's Liberation Army Air Force  status=probable
- **unit_hq9b** (unit, want_status=confirmed) [MISSING]
- **site_karachi** (basing_site, want_status=confirmed) [FRAGMENTED-18]
    - ent:basing_site:Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area  status=probable
    - ent:basing_site:Army Air Defence Centre  status=probable
    - ent:basing_site:Karachi air defence sector  status=probable
    - ent:basing_site:Karachi coastal air defence belt  status=probable
    - ent:basing_site:Malir District, Karachi, Sindh Province, Pakistan  status=probable
    - ent:basing_site:Pasrur dispersal sites  status=probable
    - ent:basing_site:Sialkot-area dispersal sites  status=probable
    - ent:basing_site:central Punjab air defence sector  status=probable
- **site_rawalpindi** (basing_site, want_status=stale) [FRAGMENTED-4]
    - ent:basing_site:PAF Base Nur Khan  status=probable
    - ent:basing_site:fenced compound near a PAF airbase  status=probable
    - ent:basing_site:imagery-site:d17_rawalpindi_2021  status=probable
    - ent:basing_site:the old Rawalpindi-area site  status=probable
- **site_rahwali** (basing_site, want_status=confirmed) [FRAGMENTED-2]
    - ent:basing_site:Rahwali airfield  status=confirmed
    - ent:basing_site:imagery-site:d18_rahwali_pass1  status=probable
- **gap_launcher_count** (known_gap, want_status=-) [OK-1]
    - ent:known_gap:launcher count, reload status, and radar emission state  status=probable

## ORACLE EDGE -> VIEW (by type)
- **mfr_casic -manufactures-> var_hq9p** (want confirmed): 5 view edges of type 'manufactures'
- **mfr_casic -manufactures-> var_hq9be** (want confirmed): 5 view edges of type 'manufactures'
- **mfr_casic -manufactures-> comp_ht233** (want confirmed): 5 view edges of type 'manufactures'
- **comp_ht233 -equips-> var_hq9p** (want confirmed): 11 view edges of type 'equips'
- **comp_interceptor -equips-> var_hq9p** (want confirmed): 11 view edges of type 'equips'
- **mfr_23rd_ri -manufactures-> comp_ht233** (want possible): 5 view edges of type 'manufactures'
- **mfr_4th_academy -supplies-component-> comp_interceptor** (want possible): 1 view edges of type 'supplies-component'
- **mfr_taian -supplies-component-> comp_tel_chassis** (want confirmed): 1 view edges of type 'supplies-component'
- **comp_tel_chassis -equips-> var_hq9p** (want confirmed): 11 view edges of type 'equips'
- **sustain_techdata -design-authority-for-> var_hq9p** (want probable): 1 view edges of type 'design-authority-for'
- **var_hq9p -distinct-from-> var_hq9be** (want confirmed): 4 view edges of type 'distinct-from'
- **FD-2000 -same-as-> var_hq9p** (want confirmed): 53 view edges of type 'same-as'
- **alias_ft2000 -distinct-from-> var_hq9p** (want confirmed): 4 view edges of type 'distinct-from'
- **import_2021 -exported-by-> mfr_casic** (want confirmed): 5 view edges of type 'exported-by'
- **import_2021 -imported-by-> unit_paad** (want confirmed): 7 view edges of type 'imported-by'
- **var_hq9p -inducted-into-> unit_paad** (want confirmed): 6 view edges of type 'inducted-into'
- **var_hq9be -inducted-into-> unit_hq9b** (want confirmed): 6 view edges of type 'inducted-into'
- **unit_paad -based-at-> site_karachi** (want confirmed): 2 view edges of type 'based-at'
- **unit_hq9b -based-at-> site_rawalpindi** (want stale): 2 view edges of type 'based-at'
- **unit_hq9b -based-at-> site_rahwali** (want confirmed): 2 view edges of type 'based-at'
- **site_rahwali -supersedes-> site_rawalpindi** (want confirmed): 0 view edges of type 'supersedes'
- **unit_paad -sustained-by-> sustain_spares** (want probable): 0 view edges of type 'sustained-by'

## RESOLVE decisions that FIRED (same-as / distinct-from)
- distinct-from: ent:variant:FT-2000 -> ent:variant:HQ-9/P  (merge_conf=None, status=None)
- distinct-from: ent:variant:HQ-9/P -> ent:variant:HQ-9BE  (merge_conf=None, status=None)
- same-as: 23rd Research Institute -> Beijing Institute of Radio Measurement  (merge_conf=None, status=probable)
- same-as: CASIC's 23rd Research Institute -> BIRM  (merge_conf=None, status=probable)
- same-as: CASIC's 23rd Research Institute -> Beijing Institute of Radio Measurement  (merge_conf=None, status=probable)
- same-as: CASIC's 4th Academy -> 中国航天科工四院  (merge_conf=None, status=probable)
- same-as: CASIC's Second Academy -> 中国航天科工二院  (merge_conf=None, status=probable)
- same-as: CPMIEC -> China Precision Machinery Import-Export Corporation  (merge_conf=None, status=probable)
- same-as: China Aerospace Science and Industry Corporation -> CASIC  (merge_conf=None, status=confirmed)
- same-as: China National Precision Machinery Import & Export Corporation -> CPMIEC  (merge_conf=None, status=probable)
- same-as: China Precision Machinery Import-Export Corporation -> CPMIEC  (merge_conf=None, status=probable)
- same-as: FD-2000 long-range surface-to-air missile system -> FD-2000  (merge_conf=None, status=probable)
- same-as: FD-2000 -> FD-2000  (merge_conf=None, status=probable)
- same-as: FD-2000B -> FD-2000B  (merge_conf=None, status=probable)
- same-as: FT-2000 -> FT-2000  (merge_conf=None, status=probable)
- same-as: FT-2000 -> FT-2000A  (merge_conf=None, status=probable)
- same-as: HQ-16 -> HQ-16  (merge_conf=None, status=probable)
- same-as: HQ-9 family -> Hongqi-9 (红旗-9)  (merge_conf=None, status=probable)
- same-as: HQ-9/P -> FD-2000  (merge_conf=None, status=confirmed)
- same-as: HQ-9/P -> HQ-9  (merge_conf=None, status=probable)
- same-as: HQ-9/P -> HQ-9(P)  (merge_conf=None, status=probable)
- same-as: HQ-9/P -> HQ-9/P  (merge_conf=None, status=confirmed)
- same-as: HQ-9/P -> HQ-9P  (merge_conf=None, status=confirmed)
- same-as: HQ-9 -> HQ-9  (merge_conf=None, status=probable)
- same-as: HQ-9 -> HQ-9/P  (merge_conf=None, status=probable)
- same-as: HQ-9A -> HQ-9A  (merge_conf=None, status=probable)
- same-as: HQ-9B -> HQ-9B  (merge_conf=None, status=confirmed)
- same-as: HQ-9B -> HQ-9BE  (merge_conf=None, status=probable)
- same-as: HQ-9BE -> HQ-9BE  (merge_conf=None, status=probable)
- same-as: HQ-9BE -> HQ-9P  (merge_conf=None, status=probable)
- same-as: HQ-9P -> FD-2000  (merge_conf=None, status=probable)
- same-as: HQ-9P -> HQ-9P  (merge_conf=None, status=probable)
- same-as: HT-233 phased-array engagement radar -> fire-control and guidance radar  (merge_conf=None, status=probable)
- same-as: High to Medium Air Defence System (HIMADS) -> HQ-9/P  (merge_conf=None, status=probable)
- same-as: LY-80 -> HQ-16  (merge_conf=None, status=confirmed)
- same-as: LY-80 -> LY-80  (merge_conf=None, status=probable)
- same-as: Long Range Surface-to-Air Missile (LR-SAM) system -> FD-2000  (merge_conf=None, status=probable)
- same-as: Long Range Surface-to-Air Missile (LR-SAM) system -> HQ-9/P  (merge_conf=None, status=probable)
- same-as: Long Range Surface-to-Air Missile (LR-SAM) system -> HQ-9P  (merge_conf=None, status=probable)
- same-as: Long Range Surface-to-Air Missile (LR-SAM) system -> LR-SAM  (merge_conf=None, status=probable)
- same-as: ORIENT ELECTRO TRADING PVT LTD -> ORIENT ELECTRONIC TRADING CO  (merge_conf=None, status=probable)
- same-as: Pakistan Air Force -> PAF  (merge_conf=None, status=probable)
- same-as: S-300P/PMU-series -> SA-20  (merge_conf=None, status=probable)
- same-as: S-300PMU-2 -> SA-20 Gargoyle  (merge_conf=None, status=probable)
- same-as: S-400 Triumf -> S-400 Triumf  (merge_conf=None, status=probable)
- same-as: S-400 Triumf -> S-400 Triumph  (merge_conf=None, status=probable)
- same-as: S-400 Triumf -> SA-21  (merge_conf=None, status=probable)
- same-as: S-400 Triumf -> SA-21 Growler  (merge_conf=None, status=probable)
- same-as: S-400 Triumf -> Triumph  (merge_conf=None, status=probable)
- same-as: S-400/Triumf -> Triumph  (merge_conf=None, status=probable)
- same-as: SINO-GALAXY IMP/EXP CO. LTD -> SINO-GALAXY IMPEX CO, LTD  (merge_conf=None, status=probable)
- same-as: TAS5380 -> WS2400-series  (merge_conf=None, status=probable)
- same-as: Taian -> Wanshan  (merge_conf=None, status=probable)
- same-as: Type 305B -> HQ-9P fire control radar  (merge_conf=None, status=probable)
- same-as: Type 305B -> HT-233  (merge_conf=None, status=probable)
- distinct-from: the System -> S-300P/PMU-series  (merge_conf=None, status=probable)
- distinct-from: the System -> S-400/Triumf  (merge_conf=None, status=probable)

## HERO QUERY
```
Traceback (most recent call last):
  File "/home/synaptic/data-science/research/rough/osint/wt-EVAL/tmp/conv/eval-rca/rca_evidence.py", line 108, in <module>
    ans = harness.run_hero_query(inp, view)
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/synaptic/data-science/research/rough/osint/wt-EVAL/backend/eval/harness.py", line 180, in run_hero_query
    return ask(question, view, inp.config_store.snapshot(), llm=None, claims=inp.claims)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/synaptic/data-science/research/rough/osint/wt-EVAL/backend/chanakya/agent/__init__.py", line 89, in ask
    answer = assemble_answer(trace, ctx)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/synaptic/data-science/research/rough/osint/wt-EVAL/backend/chanakya/agent/assemble.py", line 212, in assemble_answer
    built = builder(trace, ctx)
            ^^^^^^^^^^^^^^^^^^^
  File "/home/synaptic/data-science/research/rough/osint/wt-EVAL/backend/chanakya/agent/assemble.py", line 149, in _from_get_node
    _sentence(f"{_name(ctx, r['node_id'])} ({r['node_id']}) is a {r.get('type')} (status: {r.get('status')}){extra}", cids)
                            ~^^^^^^^^^^^
KeyError: 'node_id'

```

## RELOCATION OBSERVABLE
- alerts fired: 0
- based-at edges @2021 rewind: []
- based-at edges @now: [('China HQ-9 battery', "garrison in China's western military district", 'insufficient'), ('HQ-9/P', 'Army Air Defence Centre, Karachi', 'insufficient')]

## PLACES (resolved_place_ref present on any view node?)
- resolved_place_refs seen in view: {}
    - oracle place pl_nurkhan (site) used_by=site_rawalpindi
    - oracle place pl_rahwali (site) used_by=site_rahwali
    - oracle place pl_karachi_ad (pad) used_by=site_karachi
    - oracle place pl_port_qasim (terminal) used_by=-
    - oracle place pl_karachi_port (terminal) used_by=-
    - oracle place pl_casic_2nd (district) used_by=mfr_casic
    - oracle place pl_birm (district) used_by=mfr_23rd_ri

