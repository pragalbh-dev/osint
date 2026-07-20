# EVAL RCA — evidence bundle (real pipeline over frozen bundles)

- repo root: `/home/synaptic/data-science/research/rough/osint/wt-EVAL`
- claims seeded: **499**
- full view: **180 nodes / 113 edges / 71 events / 23 known_gaps**
- lens view (`lens-hq9p-pk`): **35 nodes / 89 edges**
- oracle: 20 nodes / 21 edges / 7 places

## view node-type histogram
- source: 57
- basing_site: 31
- component: 30
- variant: 19
- unknown: 11
- manufacturer: 11
- known_gap: 7
- unit: 6
- contract_import_event: 5
- trading_org: 3

## view edge-type histogram (ad-hoc predicates reveal ontology non-enforcement)
- same-as: 41
- observed-at: 16
- equips: 16
- inducted-into: 12
- distinct-from: 9
- exported-by: 4
- imported-by: 4
- based-at: 4
- manufactures: 4
- supplies-component: 2
- component-of: 1

## known_gap nodes (proliferation check)
- `comp_tel_chassis`  status=confirmed
- `ent:known_gap:additional dispersed elements`  status=probable
- `ent:known_gap:northern tree line`  status=probable
- `ent:known_gap:perimeter`  status=probable
- `ent:known_gap:radar repositioning confirmation`  status=probable
- `ent:known_gap:radar type identification`  status=probable
- `ent:known_gap:repeat EO pass`  status=probable

## ORACLE NODE -> VIEW attribute-match (RESOLVE under-merge evidence)
For each oracle node: view nodes of same type whose name/alias overlaps. >1 hit = fragmented (unmerged).

- **mfr_casic** (manufacturer, want_status=-) [FRAGMENTED-5]
    - ent:manufacturer:China  status=probable
    - ent:manufacturer:China National Precision Machinery Import & Export Corporation  status=probable
    - mfr_23rd_ri  status=probable
    - mfr_4th_academy  status=probable
    - mfr_casic  status=confirmed
- **comp_ht233** (component, want_status=-) [FRAGMENTED-8]
    - comp_ht233  status=confirmed
    - ent:component:Battery/charging modules for engagement radar cabin  status=probable
    - ent:component:HQ-9P fire control radar  status=probable
    - ent:component:HT-233 (H-200) engagement radar array  status=probable
    - ent:component:HT-233 or derivative  status=probable
    - ent:component:Type 305B (HT-233) fire-control set  status=probable
    - ent:component:engagement radar  status=probable
    - ent:component:possible radar trailer footprint  status=probable
- **comp_interceptor** (component, want_status=-) [FRAGMENTED-3]
    - ent:component:Calibration/test jigs for missile round check-out prior to captive-carry/loading drills  status=probable
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
- **comp_tel_chassis** (component, want_status=-) [FRAGMENTED-3]
    - ent:component:Ground support vehicle spares for erector-launcher chassis  status=probable
    - ent:component:HQ-9/P TEL canister  status=probable
    - ent:component:heavy 8×8 special wheeled chassis of the Taian (Wanshan) WS-series lineage  status=probable
- **gap_ht233_maker** (known_gap, want_status=-) [MISSING]
- **sustain_techdata** (techdata_authority, want_status=probable) [MISSING]
- **sustain_spares** (interceptor_stockpile, want_status=probable) [MISSING]
- **var_hq9p** (variant, want_status=-) [FRAGMENTED-3]
    - ent:variant:Chinese Hongqi-9 (HQ-9P/FD-2000 family)  status=probable
    - ent:variant:FD-2000B  status=probable
    - var_hq9p  status=confirmed
- **var_hq9be** (variant, want_status=-) [OK-1]
    - var_hq9be  status=confirmed
- **alias_ft2000** (variant, want_status=-) [OK-1]
    - alias_ft2000  status=probable
- **import_2021** (contract_import_event, want_status=confirmed) [MISSING]
- **unit_paad** (unit, want_status=confirmed) [FRAGMENTED-4]
    - ent:unit:PAF/Army Air Defence Command HQ-9BE battery  status=insufficient
    - ent:unit:People's Liberation Army Air Force  status=probable
    - unit_hq9b  status=confirmed
    - unit_paad  status=confirmed
- **unit_hq9b** (unit, want_status=confirmed) [OK-1]
    - ent:unit:PAF/Army Air Defence Command HQ-9BE battery  status=insufficient
- **site_karachi** (basing_site, want_status=confirmed) [FRAGMENTED-16]
    - ent:basing_site:Air Defence Depot, ~12 km NNW of Kala Chitta / Attock Cantt area  status=probable
    - ent:basing_site:Army Air Defence Centre, Karachi  status=probable
    - ent:basing_site:Karachi air defence sector  status=probable
    - ent:basing_site:Karachi coastal air defence belt  status=probable
    - ent:basing_site:Pasrur dispersal site  status=probable
    - ent:basing_site:Sialkot-area dispersal site  status=probable
    - ent:basing_site:central Punjab air defence sector  status=probable
    - ent:basing_site:imagery-site:d07_sat_confirm_karachi  status=probable
- **site_rawalpindi** (basing_site, want_status=stale) [FRAGMENTED-6]
    - ent:basing_site:air defense node in vicinity of a known PAF forward operating base  status=probable
    - ent:basing_site:fenced compound near a PAF airbase  status=probable
    - ent:basing_site:fenced compound near a PAF airbase in central Punjab  status=possible
    - ent:basing_site:imagery-site:d17_rawalpindi_2021  status=probable
    - ent:basing_site:key PAF main operating bases  status=probable
    - site_rawalpindi  status=probable
- **site_rahwali** (basing_site, want_status=confirmed) [FRAGMENTED-2]
    - ent:basing_site:imagery-site:d18_rahwali_pass1  status=probable
    - site_rahwali  status=confirmed
- **gap_launcher_count** (known_gap, want_status=-) [MISSING]

## ORACLE EDGE -> VIEW (by type)
- **mfr_casic -manufactures-> var_hq9p** (want confirmed): 4 view edges of type 'manufactures'
- **mfr_casic -manufactures-> var_hq9be** (want confirmed): 4 view edges of type 'manufactures'
- **comp_ht233 -equips-> var_hq9p** (want confirmed): 16 view edges of type 'equips'
- **comp_interceptor -equips-> var_hq9p** (want confirmed): 16 view edges of type 'equips'
- **mfr_23rd_ri -supplies-component-> comp_ht233** (want possible): 2 view edges of type 'supplies-component'
- **mfr_4th_academy -supplies-component-> comp_interceptor** (want possible): 2 view edges of type 'supplies-component'
- **mfr_taian -supplies-component-> comp_tel_chassis** (want confirmed): 2 view edges of type 'supplies-component'
- **comp_tel_chassis -equips-> var_hq9p** (want confirmed): 16 view edges of type 'equips'
- **sustain_techdata -design-authority-for-> var_hq9p** (want probable): 0 view edges of type 'design-authority-for'
- **var_hq9p -distinct-from-> var_hq9be** (want confirmed): 9 view edges of type 'distinct-from'
- **FD-2000 -same-as-> var_hq9p** (want confirmed): 41 view edges of type 'same-as'
- **alias_ft2000 -distinct-from-> var_hq9p** (want confirmed): 9 view edges of type 'distinct-from'
- **import_2021 -exported-by-> mfr_casic** (want confirmed): 4 view edges of type 'exported-by'
- **import_2021 -imported-by-> unit_paad** (want confirmed): 4 view edges of type 'imported-by'
- **var_hq9p -inducted-into-> unit_paad** (want confirmed): 12 view edges of type 'inducted-into'
- **var_hq9be -inducted-into-> unit_hq9b** (want confirmed): 12 view edges of type 'inducted-into'
- **unit_paad -based-at-> site_karachi** (want confirmed): 4 view edges of type 'based-at'
- **unit_hq9b -based-at-> site_rawalpindi** (want stale): 4 view edges of type 'based-at'
- **unit_hq9b -based-at-> site_rahwali** (want confirmed): 4 view edges of type 'based-at'
- **site_rahwali -supersedes-> site_rawalpindi** (want confirmed): 0 view edges of type 'supersedes'
- **unit_paad -sustained-by-> sustain_spares** (want probable): 0 view edges of type 'sustained-by'

## RESOLVE decisions that FIRED (same-as / distinct-from)
- distinct-from: alias_ft2000 -> var_hq9p  (merge_conf=None, status=None)
- distinct-from: ent:variant:HQ-9A -> var_hq9p  (merge_conf=None, status=None)
- distinct-from: unit_hq9b -> unit_paad  (merge_conf=None, status=None)
- distinct-from: var_hq9be -> var_hq9p  (merge_conf=None, status=None)
- distinct-from: Hongqi-9 family -> S-300P/PMU-series  (merge_conf=None, status=probable)
- distinct-from: Hongqi-9 family -> ent:variant:S-400 Triumf  (merge_conf=None, status=probable)
- distinct-from: PLA's domestic HT-233 -> modified export variant  (merge_conf=None, status=probable)
- distinct-from: ent:variant:HQ-9A -> var_hq9p  (merge_conf=None, status=probable)
- distinct-from: var_hq9p -> var_hq9be  (merge_conf=None, status=probable)
- same-as: comp_ht233 -> ent:component:Type 120  (merge_conf=0.23985507246376808, status=None)
- same-as: comp_ht233 -> ent:component:Type 305B  (merge_conf=0.23244766505636072, status=None)
- same-as: ent:basing_site:Army Air Defence Centre, Karachi -> ent:basing_site:Karachi air defence sector  (merge_conf=0.7957816377171217, status=None)
- same-as: ent:basing_site:Army Air Defence Centre, Karachi -> ent:basing_site:Karachi coastal air defence belt  (merge_conf=0.7946161290322581, status=None)
- same-as: ent:basing_site:Army Air Defence Centre, Karachi -> ent:basing_site:Punjab  (merge_conf=0.5697132616487456, status=None)
- same-as: ent:basing_site:Army Air Defence Centre, Karachi -> ent:basing_site:Sargodha  (merge_conf=0.6338709677419355, status=None)
- same-as: ent:basing_site:Army Air Defence Centre, Karachi -> ent:basing_site:Sindh  (merge_conf=0.676236559139785, status=None)
- same-as: ent:basing_site:Army Air Defence Centre, Karachi -> ent:basing_site:central Punjab air defence sector  (merge_conf=0.780117302052786, status=None)
- same-as: ent:basing_site:Army Air Defence Centre, Karachi -> ent:basing_site:fenced compound near a PAF airbase in central Punjab  (merge_conf=0.7193104187727845, status=None)
- same-as: ent:basing_site:Karachi air defence sector -> ent:basing_site:Karachi coastal air defence belt  (merge_conf=0.797423076923077, status=None)
- same-as: ent:basing_site:Karachi air defence sector -> ent:basing_site:Punjab  (merge_conf=0.5713675213675214, status=None)
- same-as: ent:basing_site:Karachi air defence sector -> ent:basing_site:Sargodha  (merge_conf=0.6656410256410257, status=None)
- same-as: ent:basing_site:Karachi air defence sector -> ent:basing_site:Sindh  (merge_conf=0.6342735042735043, status=None)
- same-as: ent:basing_site:Karachi air defence sector -> ent:basing_site:central Punjab air defence sector  (merge_conf=0.7956572413094153, status=None)
- same-as: ent:basing_site:Karachi air defence sector -> ent:basing_site:fenced compound near a PAF airbase in central Punjab  (merge_conf=0.7290598290598291, status=None)
- same-as: ent:basing_site:Karachi coastal air defence belt -> ent:basing_site:Punjab  (merge_conf=0.6361111111111111, status=None)
- same-as: ent:basing_site:Karachi coastal air defence belt -> ent:basing_site:Sargodha  (merge_conf=0.6416666666666667, status=None)
- same-as: ent:basing_site:Karachi coastal air defence belt -> ent:basing_site:Sindh  (merge_conf=0.631388888888889, status=None)
- same-as: ent:basing_site:Karachi coastal air defence belt -> ent:basing_site:central Punjab air defence sector  (merge_conf=0.7257191480017567, status=None)
- same-as: ent:basing_site:Karachi coastal air defence belt -> ent:basing_site:fenced compound near a PAF airbase in central Punjab  (merge_conf=0.7098901098901099, status=None)
- same-as: ent:basing_site:Punjab -> ent:basing_site:Sargodha  (merge_conf=0.6222222222222222, status=None)
- same-as: ent:basing_site:Punjab -> ent:basing_site:Sindh  (merge_conf=0.6322222222222222, status=None)
- same-as: ent:basing_site:Punjab -> ent:basing_site:central Punjab air defence sector  (merge_conf=0.5691919191919192, status=None)
- same-as: ent:basing_site:Punjab -> ent:basing_site:fenced compound near a PAF airbase in central Punjab  (merge_conf=0.653931623931624, status=None)
- same-as: ent:basing_site:Sargodha -> ent:basing_site:Sindh  (merge_conf=0.7133333333333334, status=None)
- same-as: ent:basing_site:Sargodha -> ent:basing_site:central Punjab air defence sector  (merge_conf=0.6328282828282829, status=None)
- same-as: ent:basing_site:Sargodha -> ent:basing_site:fenced compound near a PAF airbase in central Punjab  (merge_conf=0.6542735042735043, status=None)
- same-as: ent:basing_site:Sindh -> ent:basing_site:central Punjab air defence sector  (merge_conf=0.6754545454545455, status=None)
- same-as: ent:basing_site:Sindh -> ent:basing_site:fenced compound near a PAF airbase in central Punjab  (merge_conf=0.666923076923077, status=None)
- same-as: ent:basing_site:central Punjab air defence sector -> ent:basing_site:fenced compound near a PAF airbase in central Punjab  (merge_conf=0.7278579843095973, status=None)
- same-as: ent:component:FD-2000/HQ-9P interceptor -> ent:component:HQ-9P fire control radar  (merge_conf=0.6844444444444445, status=None)
- same-as: ent:component:FD-2000/HQ-9P interceptor -> ent:component:Type 120  (merge_conf=0.49333333333333335, status=None)
- same-as: ent:component:HT-233 (H-200) engagement radar array -> ent:component:support vehicles  (merge_conf=0.5907142857142857, status=None)
- same-as: ent:component:Type 120 -> ent:component:Type 305B  (merge_conf=0.4722222222222222, status=None)
- same-as: ent:contract_import_event:KPQA-HC-2020-118834 -> ent:contract_import_event:KPQA-HC-2020-118835  (merge_conf=0.8415789473684211, status=None)
- same-as: ent:contract_import_event:KPQA-HC-2020-118834 -> ent:contract_import_event:KPQA-HC-2020-119011  (merge_conf=0.5241988304093568, status=None)
- same-as: ent:contract_import_event:KPQA-HC-2020-118835 -> ent:contract_import_event:KPQA-HC-2020-119011  (merge_conf=0.5241988304093568, status=None)
- same-as: ent:manufacturer:CPMIEC -> ent:manufacturer:China National Precision Machinery Import & Export Corporation  (merge_conf=0.4808055555555556, status=None)
- same-as: ent:trading_org:SINO-GALAXY IMP/EXP CO. LTD -> ent:trading_org:SINO-GALAXY IMPEX CO, LTD  (merge_conf=0.5035844017094018, status=None)
- same-as: ent:unit:PAF/Army Air Defence Command HQ-9BE battery -> unit_hq9b  (merge_conf=0.5005720114239087, status=None)
- same-as: ent:variant:HQ-16 -> ent:variant:LY-80  (merge_conf=0.4437916666666667, status=None)

## HERO QUERY
- answer: <REFUSAL>
- hops: []
- citations: []
- refusal: missing=['site_karachi'] next_coverage_due=None known_gap=None reason="The subject lens 'lens-hq9p-pk' has no basing_site anchor present in the rebuilt view (anchors ['unit_paad', 'site_karachi'] → unresolved ['site_karachi']); cannot anchor the basing→origin trace."

## RELOCATION OBSERVABLE
- alerts fired: 0
- based-at edges @2021 rewind: []
- based-at edges @now: [('ent:unit:PAF/Army Air Defence Command HQ-9BE battery', 'site_rahwali', 'insufficient'), ('mfr_23rd_ri', 'ent:basing_site:Yongding Road', 'insufficient'), ('unit_hq9b', 'site_rahwali', 'probable'), ('unit_hq9b', 'site_rawalpindi', 'insufficient')]

## PLACES (resolved_place_ref present on any view node?)
- resolved_place_refs seen in view: {'pl_karachi_ad': 1, 'pl_rahwali': 1, 'pl_nurkhan': 1}
    - oracle place pl_nurkhan (site) used_by=site_rawalpindi
    - oracle place pl_rahwali (site) used_by=site_rahwali
    - oracle place pl_karachi_ad (pad) used_by=site_karachi
    - oracle place pl_port_qasim (terminal) used_by=-
    - oracle place pl_karachi_port (terminal) used_by=-
    - oracle place pl_casic_2nd (district) used_by=mfr_casic
    - oracle place pl_birm (district) used_by=mfr_23rd_ri

