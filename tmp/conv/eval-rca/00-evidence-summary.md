# EVAL RCA — evidence bundle (real pipeline over frozen bundles)

- repo root: `/home/synaptic/data-science/research/rough/osint/wt-EVAL`
- claims seeded: **452**
- full view: **162 nodes / 57 edges / 79 events / 23 known_gaps**
- lens view (`lens-hq9p-pk`): **23 nodes / 34 edges**
- oracle: 20 nodes / 21 edges / 7 places

## view node-type histogram
- source: 56
- component: 36
- basing_site: 26
- variant: 11
- manufacturer: 9
- unit: 7
- known_gap: 6
- contract_import_event: 5
- unknown: 3
- trading_org: 3

## view edge-type histogram (ad-hoc predicates reveal ontology non-enforcement)
- equips: 11
- same-as: 9
- imported-by: 7
- inducted-into: 6
- distinct-from: 5
- component-of: 5
- exported-by: 5
- manufactures: 5
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

- **mfr_casic** (manufacturer, want_status=-) [FRAGMENTED-5]
    - ent:manufacturer:China  status=probable
    - ent:manufacturer:China National Precision Machinery Import & Export Corporation  status=probable
    - mfr_23rd_ri  status=probable
    - mfr_4th_academy  status=probable
    - mfr_casic  status=confirmed
- **comp_ht233** (component, want_status=-) [FRAGMENTED-7]
    - comp_ht233  status=confirmed
    - ent:component:Battery/charging modules for engagement radar cabin  status=probable
    - ent:component:HQ-9P fire control radar  status=probable
    - ent:component:HT-233 (H-200)  status=probable
    - ent:component:Type 305B (HT-233) fire-control set  status=probable
    - ent:component:engagement radar (possibly HT-233 or a derivative)  status=probable
    - ent:component:radar trailer  status=probable
- **comp_interceptor** (component, want_status=-) [FRAGMENTED-3]
    - ent:component:Calibration/test jigs for missile round check-out  status=probable
    - ent:component:FD-2000/HQ-9P interceptor  status=probable
    - ent:component:Ground support vehicle spares for erector-launcher chassis  status=probable
- **mfr_23rd_ri** (manufacturer, want_status=possible) [FRAGMENTED-2]
    - mfr_23rd_ri  status=probable
    - mfr_4th_academy  status=probable
- **mfr_4th_academy** (manufacturer, want_status=possible) [FRAGMENTED-2]
    - mfr_23rd_ri  status=probable
    - mfr_4th_academy  status=probable
- **mfr_taian** (manufacturer, want_status=confirmed) [FRAGMENTED-2]
    - ent:manufacturer:Taian  status=probable
    - mfr_taian  status=probable
- **comp_tel_chassis** (component, want_status=-) [FRAGMENTED-4]
    - comp_tel_chassis  status=confirmed
    - ent:component:Ground support vehicle spares for erector-launcher chassis  status=probable
    - ent:component:WS-series heavy 8x8 special wheeled chassis  status=probable
    - ent:component:transporter-erector-launcher (TEL) platform  status=probable
- **gap_ht233_maker** (known_gap, want_status=-) [MISSING]
- **sustain_techdata** (techdata_authority, want_status=probable) [MISSING]
- **sustain_spares** (interceptor_stockpile, want_status=probable) [MISSING]
- **var_hq9p** (variant, want_status=-) [FRAGMENTED-3]
    - ent:variant:FD-2000B  status=probable
    - ent:variant:HQ-9  status=confirmed
    - var_hq9p  status=confirmed
- **var_hq9be** (variant, want_status=-) [FRAGMENTED-2]
    - ent:variant:HQ-9  status=confirmed
    - var_hq9be  status=confirmed
- **alias_ft2000** (variant, want_status=-) [OK-1]
    - alias_ft2000  status=probable
- **import_2021** (contract_import_event, want_status=confirmed) [MISSING]
- **unit_paad** (unit, want_status=confirmed) [FRAGMENTED-5]
    - ent:unit:Pakistan  status=probable
    - ent:unit:Pakistan Army's Army Air Defence Command  status=probable
    - ent:unit:People's Liberation Army Air Force  status=probable
    - unit_hq9b  status=confirmed
    - unit_paad  status=confirmed
- **unit_hq9b** (unit, want_status=confirmed) [MISSING]
- **site_karachi** (basing_site, want_status=confirmed) [FRAGMENTED-17]
    - ent:basing_site:Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area  status=probable
    - ent:basing_site:Army Air Defence Centre, Karachi  status=probable
    - ent:basing_site:Karachi air defence sector  status=probable
    - ent:basing_site:Karachi coastal air defence belt  status=probable
    - ent:basing_site:Pasrur dispersal sites  status=probable
    - ent:basing_site:Sialkot-area dispersal sites  status=probable
    - ent:basing_site:central Punjab air defence sector  status=probable
    - ent:basing_site:imagery-site:d07_sat_confirm_karachi  status=probable
- **site_rawalpindi** (basing_site, want_status=stale) [FRAGMENTED-3]
    - ent:basing_site:fenced compound near a PAF airbase  status=probable
    - ent:basing_site:imagery-site:d17_rawalpindi_2021  status=probable
    - site_rawalpindi  status=probable
- **site_rahwali** (basing_site, want_status=confirmed) [FRAGMENTED-2]
    - ent:basing_site:imagery-site:d18_rahwali_pass1  status=probable
    - site_rahwali  status=confirmed
- **gap_launcher_count** (known_gap, want_status=-) [OK-1]
    - ent:known_gap:launcher count, reload status, and radar emission state  status=probable

## ORACLE EDGE -> VIEW (by type)
- **mfr_casic -manufactures-> var_hq9p** (want confirmed): 5 view edges of type 'manufactures'
- **mfr_casic -manufactures-> var_hq9be** (want confirmed): 5 view edges of type 'manufactures'
- **comp_ht233 -equips-> var_hq9p** (want confirmed): 11 view edges of type 'equips'
- **comp_interceptor -equips-> var_hq9p** (want confirmed): 11 view edges of type 'equips'
- **mfr_23rd_ri -supplies-component-> comp_ht233** (want possible): 1 view edges of type 'supplies-component'
- **mfr_4th_academy -supplies-component-> comp_interceptor** (want possible): 1 view edges of type 'supplies-component'
- **mfr_taian -supplies-component-> comp_tel_chassis** (want confirmed): 1 view edges of type 'supplies-component'
- **comp_tel_chassis -equips-> var_hq9p** (want confirmed): 11 view edges of type 'equips'
- **sustain_techdata -design-authority-for-> var_hq9p** (want probable): 1 view edges of type 'design-authority-for'
- **var_hq9p -distinct-from-> var_hq9be** (want confirmed): 5 view edges of type 'distinct-from'
- **FD-2000 -same-as-> var_hq9p** (want confirmed): 9 view edges of type 'same-as'
- **alias_ft2000 -distinct-from-> var_hq9p** (want confirmed): 5 view edges of type 'distinct-from'
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
- distinct-from: alias_ft2000 -> var_hq9p  (merge_conf=None, status=None)
- distinct-from: unit_hq9b -> unit_paad  (merge_conf=None, status=None)
- distinct-from: var_hq9be -> var_hq9p  (merge_conf=None, status=None)
- distinct-from: ent:component:the System -> S-300P/PMU-series  (merge_conf=None, status=probable)
- distinct-from: ent:component:the System -> ent:variant:S-400 Triumf  (merge_conf=None, status=probable)
- same-as: ent:component:HQ-9P fire control radar -> ent:component:Type 305B  (merge_conf=0.3586064814814815, status=None)
- same-as: ent:component:WS-series heavy 8x8 special wheeled chassis -> ent:component:transporter-erector-launcher (TEL) platform  (merge_conf=0.4503894876158064, status=None)
- same-as: ent:contract_import_event:KPQA-HC-2020-118834 -> ent:contract_import_event:KPQA-HC-2020-118835  (merge_conf=0.8415789473684211, status=None)
- same-as: ent:contract_import_event:KPQA-HC-2020-118834 -> ent:contract_import_event:KPQA-HC-2020-119011  (merge_conf=0.5241988304093568, status=None)
- same-as: ent:contract_import_event:KPQA-HC-2020-118835 -> ent:contract_import_event:KPQA-HC-2020-119011  (merge_conf=0.5241988304093568, status=None)
- same-as: ent:manufacturer:CPMIEC -> ent:manufacturer:China National Precision Machinery Import & Export Corporation  (merge_conf=0.4808055555555556, status=None)
- same-as: ent:trading_org:SINO-GALAXY IMP/EXP CO. LTD -> ent:trading_org:SINO-GALAXY IMPEX CO, LTD  (merge_conf=0.5035844017094018, status=None)
- same-as: ent:unit:Turkmenistan -> ent:unit:Uzbekistan  (merge_conf=0.7288888888888889, status=None)
- same-as: ent:variant:HQ-16 -> ent:variant:LY-80  (merge_conf=0.497125, status=None)

## HERO QUERY
- answer: <REFUSAL>
- hops: []
- citations: []
- refusal: missing=['named_supplier', 'substitutability'] next_coverage_due=None known_gap=KnownGap(id='gap:chokepoint:comp_ht233', what_missing='confirmed sole-source supplier / substitutability for HT-233', observability_ceiling='probable-max', next_coverage_due=None, related_ref='comp_ht233', missing_slots=['named_supplier', 'substitutability']) reason='Insufficient evidence to assess comp_ht233: missing named_supplier, substitutability. Next coverage due unscheduled.'

## RELOCATION OBSERVABLE
- alerts fired: 0
- based-at edges @2021 rewind: []
- based-at edges @now: [('China HQ-9 battery', "ent:basing_site:garrison in China's western military district", 'insufficient'), ('var_hq9p', 'ent:basing_site:Army Air Defence Centre, Karachi', 'insufficient')]

## PLACES (resolved_place_ref present on any view node?)
- resolved_place_refs seen in view: {'pl_karachi_ad': 1, 'pl_rahwali': 1, 'pl_nurkhan': 1}
    - oracle place pl_nurkhan (site) used_by=site_rawalpindi
    - oracle place pl_rahwali (site) used_by=site_rahwali
    - oracle place pl_karachi_ad (pad) used_by=site_karachi
    - oracle place pl_port_qasim (terminal) used_by=-
    - oracle place pl_karachi_port (terminal) used_by=-
    - oracle place pl_casic_2nd (district) used_by=mfr_casic
    - oracle place pl_birm (district) used_by=mfr_23rd_ri

