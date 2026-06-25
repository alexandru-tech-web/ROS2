# HIL_RUNBOOK -- campania C1 pe doua masini (PC + RPi)

Procedura pentru a rula benchmark-ul C1 (CycloneDDS vs Zenoh sub `tc netem`) pe HARDWARE
REAL: doua masini + link real, cu defecte injectate pe legatura fizica. HIL e comparatia
AUTORITARA; SIL (loopback, o masina) ramane bucla de dezvoltare.

Cheia: schema de date si pipeline-ul de analiza sunt IDENTICE SIL/HIL. Dupa ce colectezi
`results_c1/` pe masina-client, `analyze_campaign.py` si selectorul (transport / loss-aware /
telemetrie) ruleaza fara nicio modificare de cod -- vezi GHID_TESTARE.md.

## Topologie

```
  [M1 = PC]  client bench + tc netem + GCS          [M2 = RPi]  echo bench + drone
      |  RMW_IMPLEMENTATION = cyclonedds | zenoh         |  acelasi RMW, acelasi ROS_DOMAIN_ID
      +------------------ LAN / AP Wi-Fi ----------------+
                     (degradare reala pe acest link)
```

## 0. Preconditii (pe AMBELE masini)

- ROS 2 Jazzy, ACEEASI versiune; acelasi workspace (`~/ros2_ws`), `colcon build` + `source`.
- Acelasi `ROS_DOMAIN_ID` exportat in fiecare terminal (ex. `export ROS_DOMAIN_ID=7`).
- Ceasuri: RTT-ul e masurat dus-intors pe ceasul clientului (M1), deci NU cere sincronizare.
  DOAR daca masori latenta e2e de telemetrie cross-masina ai nevoie de chrony/PTP -- noteaza-l.
- Pe M1 (unde aplici netem): `sudo -v` (netem cere privilegii).

## 1. Reteaua

- Ambele masini pe acelasi LAN / acelasi AP. Noteaza interfata reala pe M1: `ip -br addr`
  (ex. `wlan0` sau `eth0`) -- o folosesti la `--iface`.
- Verifica conectivitatea ROS inainte de orice masuratoare:
  ```bash
  # M2: porneste un talker; M1: vezi daca apare
  ros2 run demo_nodes_cpp talker        # pe M2
  ros2 topic list                       # pe M1 -> trebuie sa vezi /chatter
  ```
- Daca nu se descopera: verifica ROS_DOMAIN_ID identic, firewall, si (pt Zenoh) routerul.

## 2. Roluri

| Masina | Strat transport | Strat mission |
|--------|-----------------|----------------|
| M1 (PC)  | `run_campaign.py --mode hil` (clientul + netem) | GCS / operator |
| M2 (RPi) | `bench_echo_server.py` (ecoul) | dronele (swarm) |

## 3. RMW si routerul Zenoh

- Compari un RMW o data: seteaza ACELASI pe ambele masini, in fiecare terminal:
  ```bash
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp   # sau rmw_zenoh_cpp
  ```
- Pentru Zenoh: porneste UN router (`ros2 run rmw_zenoh_cpp rmw_zenohd`) accesibil ambelor
  masini (de obicei pe M1) si configureaza endpoint-ul pe M2 daca discovery-ul nu il gaseste.
  In SIL, `run_campaign.py` porneste un router local; in HIL il gestionezi explicit.

## 4. Degradarea (netem pe linkul fizic)

- `run_campaign.py --mode hil --iface <iface_real>` aplica `tc netem` pe EGRESS-ul interfetei
  de pe M1 (degradeaza traficul M1->M2). Conditiile vin din `bench_core.CONDITIONS` (aceleasi
  ca SIL), deci comparatia e direct comparabila cu SIL.
- ATENTIE la directie: netem pe M1 degradeaza doar sensul M1->M2. Pentru degradare SIMETRICA,
  aplica aceeasi regula si pe interfata de pe M2 (manual). Documenteaza explicit ce ai ales --
  defineste experimentul.
- La final (si la Ctrl+C) scriptul curata `tc` pe interfata. Verifica: `tc qdisc show dev <iface>`.

## 5. Rulare TRANSPORT HIL (recomandat sa incepi de aici)

```bash
# --- pe M2 (RPi): porneste ecoul, lasa-l sa ruleze ---
export ROS_DOMAIN_ID=7
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp        # acelasi ca pe M1
source ~/ros2_ws/install/setup.bash
python3 ~/ros2_ws/src/c1_benchmark/bench_echo_server.py

# --- pe M1 (PC): clientul + netem, doar stratul transport ---
export ROS_DOMAIN_ID=7
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
source ~/ros2_ws/install/setup.bash
sudo -v
python3 ~/ros2_ws/src/c1_benchmark/run_campaign.py \
    --mode hil --iface <iface_real> --layers transport --reps 5 \
    --rmws cyclonedds        # ruleaza pe rand cyclonedds, apoi zenoh
```
Repeta blocul pentru `--rmws zenoh` (cu `RMW_IMPLEMENTATION=rmw_zenoh_cpp` + router pe ambele).
Banner-ul `mod: HIL` confirma ca nu se porneste ecoul local.

## 6. Rulare MISSION HIL (avansat, manual)

Stratul `mission` e DISTRIBUIT (drone pe M2, GCS pe M1) -- `--mode hil` il sare si iti cere
sa-l pornesti manual. Lanseaza swarm-ul pe M2 si GCS-ul pe M1 (vezi sar_swarm/launch), apoi
copiaza `~/sar_data/mission_metrics.csv` in `results_c1/{rmw}/{cond}/rep{N}/`. Recomandare:
valideaza intai stratul transport pe HIL; misiunea distribuita e un pas separat.

## 7. Colectare + arhivare date (NU in git)

- Rezultatele brute stau in `results_c1/` pe M1. NU intra in git (vezi .gitignore).
- Arhiveaza-le: `mv results_c1 ~/c1_archive/hil_$(data)/` (data = AAAALLZZ). In repo intra
  DOAR sumarele (`campaign_summary.csv`) + figurile, daca decizi sa le versionezi.

## 8. Analiza (identica cu SIL)

```bash
python3 ~/ros2_ws/src/c1_benchmark/analyze_campaign.py <results_c1/>
python3 ~/ros2_ws/src/c1_benchmark/build_selector_dataset.py <results_c1/> -o selector_dataset.csv
python3 ~/ros2_ws/src/c1_benchmark/reproduce_selector.py selector_dataset.csv
# daca ai rulat si mission:
python3 ~/ros2_ws/src/c1_benchmark/reproduce_selector_mission.py <results_c1/analysis/campaign_summary.csv>
```

## 9. Checklist de validare (SIL vs HIL)

- [ ] Aceleasi conditii netem ca in SIL (`bench_core.CONDITIONS`).
- [ ] Acelasi N (repetitii) declarat explicit; >= cel din SIL.
- [ ] Ambele RMW-uri rulate cu acelasi `ROS_DOMAIN_ID` si aceeasi versiune ROS pe ambele masini.
- [ ] Directia netem documentata (M1->M2 sau simetric).
- [ ] `tc` curatat la final (`tc qdisc show`).
- [ ] Comparatie EXPLICITA SIL vs HIL in raport (acelasi grafic / tabel, etichetat clar).
- [ ] Nimic etichetat HIL daca de fapt e SIL.

## Note oneste / capcane

- RTT-ul e dus-intors pe ceasul M1 -> nu cere sincronizare de ceas. Latenta e2e cross-masina,
  da -> chrony/PTP.
- netem degradeaza un singur sens; alege si documenteaza simetria.
- Zenoh: plasarea routerului conteaza; daca discovery-ul esueaza, verifica routerul si firewall-ul.
- Pe RPi resursele sunt limitate -- ruleaza ecoul/dronele acolo, analiza pe PC.
- HIL e standardul autoritar; pana cand rulezi, toate cifrele din repo sunt SIL (loopback).
