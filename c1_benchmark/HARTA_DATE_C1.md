# Harta datelor C1 -- unde e fiecare campanie (ca sa NU re-rulezi ce ai deja)

Inventar facut prin scanarea transport_p*_summary.json. NU re-rula tot -- ai
majoritatea datelor. Vezi sectiunea "CE trebuie re-rulat" la final.

## SIL (loopback, o masina) -- ~/c1_data/   [VALID, verificat -- vezi VERDICT_SIL.md]

| Campanie | RMW | Conditii | N | ideal? | Payloads |
|----------|-----|----------|---|--------|----------|
| 01_crossover_20250619 | cyclonedds + zenoh | 8 (complet) | 5 | DA | 64/4096/65536 |
| 02_burst_20250619 | cyclonedds + zenoh | 6 (loss_20/25/30 + _burst) | 5 | nu | 64/4096/65536 |
| 03_var_n10_20250619 | cyclonedds + zenoh | 3 (loss_20/25/30) | 10 | nu | 64/4096/65536 |

- 01_crossover = sweep-ul SIL principal (cu ideal). VERIFICAT CURAT (fara bug watchdog).
- selector_dataset.csv (in c1_benchmark/) e derivat din acestea, N=10.

## HIL (doua masini) -- ~/c1_archive/   [arhivat]

| Campanie | RMW | Transport | Conditii | N | Nota |
|----------|-----|-----------|----------|---|------|
| hil_cyclonedds_20260627_1005 | cyclonedds | (early) | 8 | 5 | valid (DDS nu are router) |
| hil_cyclonedds_20260627_1007 | cyclonedds | (early) | 8 | 5 | valid |
| hil_cyclonedds_switch_20260629_0823 | cyclonedds | switch | 8 | 5 | valid |
| hil_cyclonedds_switch_20260629_0941 | cyclonedds | switch | 8 | 5 | valid |
| hil_cyclonedds_wifi_20260629_1618 | cyclonedds | Wi-Fi | 8 | 5 | valid |
| hil_zenoh_switch_20260629_0941 | zenoh | switch | 8 | 5 | DE REVERIFICAT (bug la loss mare) |
| mixed_backup_0856 | cyclonedds + zenoh | (mixt) | 2 | 5 | partial, backup |

## HIL curent -- ~/ros2_ws/src/c1_benchmark/results_c1/   [de lucru]

| RMW | Transport | Conditii | N | Nota |
|-----|-----------|----------|---|------|
| cyclonedds | Wi-Fi | 8 | 5 | valid (DDS nu are router) |
| zenoh | Wi-Fi | 8 | 5 | COMPROMIS de bug (dinainte de fix 11d7cd9) |

- results_c1/ e gitignorat (date brute). Figurile/sumarele in analysis_hil_wifi_v2/.

## Agregate gata de folosit (in c1_benchmark/)

- selector_dataset.csv -- SIL N=10, 478 randuri (pentru selector; regenerabil).
- results_c1/analysis*/campaign_summary.csv -- sumare per mediu.
- ml_dataset.csv -- extract ORFAN (loss=0), NU-l folosi (vezi CLAUDE.md).

## CE trebuie re-rulat (si ce NU)

NU re-rula (ai date valide):
- TOT SIL-ul (~/c1_data/*) -- verificat curat.
- TOT HIL CycloneDDS (arhiva + results_c1) -- CycloneDDS nu are router, neatins de bug.

DE RE-RULAT (doar Zenoh HIL, contaminat de bug-ul de watchdog router):
- Zenoh HIL Wi-Fi (results_c1/zenoh) -- cu run_campaign.py reparat + routere manuale
  (router_pi.json5 / router_m1.json5, ZENOH_CONFIG_OVERRIDE). Vezi HIL_TRANSPORT_CHEATSHEET.md.
- Zenoh HIL switch (hil_zenoh_switch_20260629_0941) -- reverifica la loss mare (loss_25/30);
  re-ruleaza daca arata anormal.

Deci NU re-rula "toata campania" -- doar Zenoh pe HIL (switch + Wi-Fi). Restul e intact.

## Cum re-rulezi DOAR ce trebuie (cand ai routerele manuale pornite)

    cd ~/ros2_ws/src/c1_benchmark
    # pe M1 + M2: porneste routerele manual (router_m1.json5 / router_pi.json5)
    # apoi doar Zenoh, doar transport:
    ./hil_run_transport.sh <iface> zenoh          # iface: wlp4s0 (Wi-Fi) sau enp2s0 (switch)
    # arhiveaza rezultatul: mv results_c1 ~/c1_archive/hil_zenoh_wifi_$(date +%Y%m%d_%H%M)/
