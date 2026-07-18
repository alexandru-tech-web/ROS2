# Verdict: datele SIL Zenoh -- valide sau contaminate de watchdog?

Sarcina de verificare (READ-ONLY). Nu am modificat cod, nu am rulat campanii/ROS.

## Date inspectate

Sursa SIL principala: `~/c1_data/01_crossover_20250619/` (loopback, o masina).
- 8 conditii: ideal, loss_5, loss_15, loss_20, loss_25, loss_30, lat200_jit50, lat200_l15.
- ambele RMW (cyclonedds + zenoh), N=5 repetitii per conditie, payload-uri 64/4096/65536 B.

Alte campanii SIL (context; NU au conditia 'ideal', deci irelevante pentru semnatura la ideal):
- `~/c1_data/03_var_n10_20250619/` -- N=10, DOAR loss_20/25/30 (studiu de varianta).
- `~/c1_data/02_burst_20250619/` -- loss_20/25/30 + variante _burst.
- `selector_dataset.csv` (SIL N=10) e derivat din aceste campanii.

NU am confundat cu HIL: datele HIL sunt separate -- `results_c1/` (Wi-Fi, recent) si
`~/c1_archive/hil_*`. `Analiza_ML_18.06.2026/` contine DOAR figuri/CSV de analiza ML,
nu date brute. `ml_dataset.csv` e extractul orfan (loss=0, per CLAUDE.md) -- ignorat.

## Semnatura bug-ului -- rezultate (SIL crossover, agregat pe N=5)

(A) loss la IDEAL (Zenoh SIL): p64 = 0.0, p4096 = 0.0, p65536 = 0.0
    -> CURAT. Bug-ul HIL dadea 63-67% loss la ideal p65536; aici 0% pe TOATE
       payload-urile, inclusiv 65536. Verificat si rep-cu-rep: 0 din 15 rep-uri
       zenoh/ideal au loss > 10%.

(B) RTT la IDEAL (Zenoh SIL): mean_ms = 1.4 / 1.5 / 2.2 ; max_ms = 2.1 / 12.1 / 4.9
    (p64 / p4096 / p65536)
    -> STABIL. Sub-3 ms mediu, maxim ~12 ms. NICIUN spike de secunde (semnatura bug-ului
       ar fi RTT de secunde chiar la ideal).

(C) comparatie cu CycloneDDS SIL la IDEAL: DDS mean_ms = 1.1 / 1.2 / 1.8, loss = 0.
    -> COMPARABIL. Zenoh ~ identic cu CycloneDDS la ideal (ambele loopback, sub-ms).
       CycloneDDS nu are router (neatins de bug); daca bug-ul ar fi lovit Zenoh, ar fi
       divergent la ideal -- NU e.

(D) tipar de degradare (Zenoh, payload 4096):
    ideal 0% -> loss_5 0% -> loss_15 7.7% -> loss_20 9.4% -> loss_25 37% -> loss_30 45%.
    lat200_jit50 1.7%, lat200_l15 20%.
    -> GRADUAL si ordonat (loss creste cu severitatea netem). NU haotic la conditii usoare.

## VERDICT: SIL VALID

Datele SIL Zenoh NU arata semnatura bug-ului de watchdog router:
- ideal curat (0% loss pe toate payload-urile),
- RTT stabil la ideal (max ~12 ms, fara spike-uri de secunde),
- comparabil cu CycloneDDS la ideal,
- degradare graduala cu severitatea.

Confirma EMPIRIC rationamentul: pe SIL (loopback, o masina), routerul local + nodurile
pe localhost NU au nevoie de ZENOH_CONFIG_OVERRIDE, deci pornirea routerului fara
override (si watchdog-ul care il reporneste) sunt INOFENSIVE pe loopback. Bug-ul se
manifesta DOAR pe HIL (cross-machine), unde lipsa override-ului rupea mesh-ul.

## Nota N=

- Campania crossover (sweep complet, cu ideal): N=5 per conditie.
- Campania var_n10 (doar loss_20/25/30): N=10.
- Ambele > N=1 -- NU sunt provizorii de tip N=1. DAR raman SIL (loopback): per
  metodologia tezei (CLAUDE.md), SIL e bucla de dezvoltare, iar comparatia AUTORITARA
  este HIL. Marcheaza cifrele SIL ca 'loopback' in articol si confirma tendintele pe HIL
  (N>=5) inainte de submisie.

## Recomandare

1. FOLOSESTE datele SIL asa cum sunt in raport cu bug-ul -- NU necesita re-rulare
   (nu sunt contaminate). N=5 (sweep) / N=10 (loss mari) sunt adecvate pentru SIL.
2. NU confunda cu HIL: pe HIL, datele Zenoh de DINAINTE de fix-ul 11d7cd9 sunt
   COMPROMISE (vezi PROGRESS_FIX.md) si trebuie re-rulate cu run_campaign.py reparat.
3. Separat (in afara acestei sarcini, de departajat la HIL): loss-ul de ~58% la ideal
   p65536 din HIL Wi-Fi (results_c1) merita o privire -- poate fi banda Wi-Fi reala la
   payload mare, SAU un rest de contaminare. NU afecteaza verdictul SIL (SIL are 0% acolo,
   fiind loopback fara limita de banda).

## ADDENDUM -- validarea datelor Wi-Fi din CAMPANII (doua masini)

Datele mutate in ~/ros2_ws/src/c1_benchmark/CAMPANII/{cyclonedds,zenoh} sunt HIL Wi-Fi
(RTT ideal 4-481 ms, NU loopback). Verificat rep-cu-rep daca loss-ul de 58% la ideal
p65536 (Zenoh) e bug-ul de watchdog SAU banda Wi-Fi reala. CONCLUZIE: banda reala, NU bug.

Dovezi (toate impotriva bug-ului):
- CONSISTENTA rep-cu-rep: zenoh ideal p65536 loss = 58/57/59/53/62% (strans, determinist).
  Bug-ul (router murind aleator) ar da valori haotice; aici e stabil -> saturatie de banda.
- DEPENDENTA DE PAYLOAD: zenoh ideal loss p64=0%, p4096=0%, p65536=58%. Bug-ul ar rupe
  mesh-ul pentru TOATE payload-urile; doar cel mare pica -> banda, nu router.
- CONTRAST CycloneDDS: DDS ideal p65536 loss=0% dar doar ~364 trimise din 989 (back-pressure,
  incetineste emitatorul). Zenoh trimite full-rate (989) si pierde -> diferenta REALA de
  protocol (Zenoh nu are back-pressure), nu bug.
- MESH FUNCTIONAL + GRADUAL: ideal p64/p4096 = 0% loss; zenoh p64 pe conditii:
  0 -> 5.6 -> 39.5 -> 60.6 -> 80.8 -> 81.3% (ordonat). Bug-ul ar rupe mesh-ul de la ideal.

VERDICT Wi-Fi: datele NU arata semnatura bug-ului -- arata fizica reala (Wi-Fi saturat la
payload mare). Par UTILIZABILE. CycloneDDS Wi-Fi: valid (nu are router).

REZERVA (onestitate): bug-ul EXISTA in cod la generarea acestor date; datele nu-l arata, dar
nu pot confirma din date provenienta (routere corecte). RECOMAND o rulare de CONFIRMARE
Zenoh (ideal + 1-2 conditii) cu run_campaign reparat + routere manuale: daca cifrele se
reproduc -> validate, foloseste-le; daca scad -> ruleaza complet Zenoh HIL.
