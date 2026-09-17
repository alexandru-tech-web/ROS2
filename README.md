# Contributii la dezvoltarea sistemelor robotice prin controlul de la distanta in timp real

Depozit de cercetare doctorala (IMSAR). Cod, protocoale experimentale si sumare de
campanie pentru teleoperarea robotilor peste retele degradate. Documentat in romana,
fara diacritice.

> **In English:** doctoral research monorepo, documented in Romanian. For the C1
> artifact (ROS 2 middleware benchmark under network degradation) see
> [`c1_benchmark/README_EN.md`](c1_benchmark/README_EN.md).

Datele si documentele stau in `../DATE`, `../DOC`, `../GRAFICE` (in afara git; structura in `../README_STRUCTURA.md`).

## Rezumat

Teza, intr-o fraza: teleoperarea in timp real peste o retea degradata nu se rezolva
alegand un middleware, ci masurand degradarea, modeland-o, comutand pe ea si
garantand siguranta cu informatia care chiar ajunge la robot.

Drumul contributiilor, pe aceeasi coloana:

    C1 masoara  ->  C2 modeleaza  ->  C3 comuta  ->  C5 arbitreaza  ->  C6 garanteaza

- **C1 masoara**: benchmark `rmw_zenoh_cpp` vs `rmw_cyclonedds_cpp` sub `tc netem`, pe
  loopback (SIL) si pe doua masini (HIL, Raspberry Pi 4 prin Wi-Fi).
- **C2 modeleaza**: pierderi in rafala (Gilbert-Elliott) calibrate din campania HIL.
- **C3 comuta**: gateway si mesh multi-hop care aleg calea in functie de starea legaturii.
- **C5 arbitreaza**: arbitrajul intre operator si automat (stare sigura activa) -- planificat,
  fara cod in depozit.
- **C6 garanteaza**: filtru de siguranta (DT-CBF) pe rover, cu marja din varsta informatiei
  (Age of Information) despre pericol; certificat de rulare pe fiecare episod.
- **C4** (exoschelet de reabilitare, tele-impedanta) este un livrabil in afara coloanei.

## Contributii si stare

| Contributie | Pachet(e) | Stare | Artefact-cheie | Ultimul commit |
|---|---|---|---|---|
| C1 masoara | `c1_benchmark` (+ `sar_swarm`, `sar_plugins` ca strat de misiune) | INGHETAT (cod); articol in revizie, tinta JIRS, submisie 30.11.2026 | `c1_benchmark/paper/campaign_summary.csv`, `paper/main.tex`, taguri `c1-paper-v3.4`, `c1-data-v2` | `88ecc48` 2026-09-01 |
| C2 modeleaza | `c2_analysis`, `c2_planning` | INGHETAT (manuscris V5 canonic, fixat prin amprenta SHA) | `c2_analysis/FAPTE_C2.md`, `MANIFEST_DATE_C2.md`, `c2_planning/CALIBRARE_GE_C2.md` | `2085405` 2026-08-13 |
| C3 comuta | `c3_gateway`, `mesh_plugin` | INGHETAT | `c3_gateway/` (FAPTE_C3, smoke e2e), `mesh_plugin/mesh_core.py` | `604c696` 2026-09-01 |
| C5 arbitreaza | -- | PLANIFICAT | -- | -- |
| C6 garanteaza | `c6_safety` | VIU | `cbf_core.py`, `certif_core.py`, `brate.py`, noduri `operator_node`/`rover_node`, `launch/c6_smoke.launch.py` | `929f6ea` 2026-09-17 |
| C4 (in afara coloanei) | `rehab_exo_description`, `joint_emulator`, `servo_control` | INGHETAT / demonstrator | tag `rehab-v0.3.0`; `docs/material_teza/cm_rmw_mismatch/` | `ad283c9` 2026-08-22 |

## Taxonomia pachetelor (toate folderele din radacina)

Stari: VIU = se lucreaza; INGHETAT = nu se modifica (cod sursa al unui articol sau al unei
decizii); ARHIVAT = pastrat, nemodificat, fara plan; MOSTENIRE = inlocuit de o contributie
ulterioara, pastrat pentru istoric.

| Folder | Tip | Rol | Stare | Ultimul commit | README |
|---|---|---|---|---|---|
| [`c1_benchmark`](c1_benchmark/README.md) | script | benchmark transport + misiune (C1); `selector_core.py` (selector invatat, ISI) | INGHETAT | 2026-09-01 | da |
| `c2_analysis` | script | analiza campaniei C2: metrici de rafala, figuri, tabele, audit (C2) | INGHETAT | 2026-08-13 | nu (`FAPTE_C2.md`, `MANIFEST_DATE_C2.md`) |
| `c2_planning` | doc+script | calibrarea Gilbert-Elliott si runbook-ul campaniei C2 | INGHETAT | 2026-08-01 | nu (`RUNBOOK_CAMPANIE_C2.md`) |
| [`c3_gateway`](c3_gateway/README.md) | ament | gateway-ul de comutare a caii (C3) | INGHETAT | 2026-09-01 | da |
| [`c6_safety`](c6_safety/README.md) | ament_python | garda de siguranta DT-CBF: core-uri pure + noduri subtiri (C6) | VIU | 2026-09-17 | da |
| [`curs_ml`](curs_ml/README.md) | educational | curs ML, 23 module | ARHIVAT | 2026-06-29 | da |
| [`curs_ros2`](curs_ros2/README.md) | educational | curs ROS 2 (11 module cu cod in `curs_ros2/curs_ros2/`) | ARHIVAT | 2026-06-29 | da |
| [`curs_ros2_interfaces`](curs_ros2_interfaces/README.md) | ament | interfete custom pentru curs | ARHIVAT | 2026-06-29 | da |
| `docs` | dovezi | `material_teza/cm_rmw_mismatch/`: jurnale de dovada pentru clasa "RMW nepotrivit" | ARHIVAT (dovada) | 2026-08-21 | nu (are `cm_rmw_mismatch/README.md`) |
| [`joint_emulator`](joint_emulator/README.md) | script | emulatorul bancului cu 6 servomotoare (C4) | INGHETAT | 2026-06-29 | da |
| [`link_adaptive`](link_adaptive/README.md) | ament | strat adaptiv la starea legaturii (NOMINAL/DEGRADED/CRITICAL), precursor al C3 | MOSTENIRE | 2026-06-29 | da |
| `log` | -- | iesire colcon, NEVERSIONAT (`.gitignore`) | -- | -- | -- |
| [`mesh_plugin`](mesh_plugin/README.md) | ament | mesh multi-hop peste roi, relay hop-by-hop (C3) | INGHETAT | 2026-06-29 | da |
| [`rehab_exo_description`](rehab_exo_description/README.md) | ament | exoscheletul de reabilitare: URDF, launch, failsafe (C4) | INGHETAT | 2026-08-22 | da |
| [`sar_plugins`](sar_plugins/README.md) | script | plugin-uri de mediu: canal radio, baterie, acoperire, victime | INGHETAT | 2026-06-29 | da |
| [`sar_swarm`](sar_swarm/README.md) | script | roiul SAR: 4 drone (d1-d4) + GCS, injector, SIL | INGHETAT | 2026-06-29 | da |
| `scratchpad` | temporar | auditul C4 din 2026-08-18 (3 fisiere) | ARHIVAT; propus la mutare in ARHIVA (vezi raport G3) | 2026-08-21 | nu |
| [`servo_control`](servo_control/README.md) | ament | demonstratorul istoric: motor Gazebo cu tastatura | MOSTENIRE | 2026-06-29 | da |
| `stats_out` | -- | figuri/CSV de statistica, NEVERSIONAT (`.gitignore`) | -- | -- | -- |
| [`teleop_rover`](teleop_rover/README.md) | script | roverul teleoperat (4 roti, perceptie, go-to-goal); plantul imprumutat de C6 | INGHETAT | 2026-06-29 | da |

Fisiere in radacina: `CLAUDE.md` (instructiuni de lucru), `CONTRIBUTING.md`, ghiduri
(`GHID_INTERFERENTA_RF.md`, `GHID_INVATARE.md`, `PARAMETRI_SI_TRANSFER_REAL.md`,
`PROIECT_ECOSISTEM_EDUCATIONAL.md`, `TEHNOLOGII.md`), `check_repo.sh`, `smoke_all.sh`.

## Metodologie

- **Bancul.** Degradarea se aplica FIZIC cu `tc qdisc ... netem` pe interfata de test (`lo`
  pentru SIL; Wi-Fi intre laptop si Raspberry Pi 4 pentru HIL). Conditiile poarta acelasi
  nume in toate campaniile (`ideal`, `loss_5`, `loss_15`, `lat200_jit50`, ...). Se raporteaza
  configurat vs masurat (ping) pentru fiecare interfata.
- **Repetitii.** N=5 pe celula in campaniile citate (C1 HIL, planul C6); C2 a folosit 10 repetitii
  per celula (`c2_analysis/FAPTE_C2.md`).
- **Manifeste.** Fiecare rulare scrie un manifest JSON (comanda, git hash + dirty, kernel,
  `tc qdisc show`, amprente SHA256 ale iesirilor). Pentru C1: `c1_benchmark/manifests/`,
  `paper/MANIFEST_SHA256.txt`. Pentru C6: `../DOC/BORD/tools/ruleaza.py` scrie
  `../DATE/campanii/<run_id>/manifest.json` si o linie in registrul de rulari.
- **Adrese.** Orice adresa IP din documentatie este din blocurile RFC 5737 (`192.0.2.0/24`,
  `198.51.100.0/24`, `203.0.113.0/24`); adresele reale nu intra in depozit.
- **Datele brute NU sunt versionate** (`.gitignore`): campaniile stau in `../DATE/campanii/`,
  arhivele in `../ARHIVA/`. In git intra doar cod, sumare CSV, figuri si manifeste.
- **Lantul de dezvoltare.** Nucleu pur cu `_selftest()` -> nod ROS subtire (JSON pe
  `std_msgs/String`) -> SIL -> pachet ament -> verificare pre-push (`smoke_all.sh`).

## Rezultate

Singurul loc citabil pentru C1 este `c1_benchmark/paper/campaign_summary.csv`
(coloane `env,condition,rmw,loss_pct,rtt_p95_ms`; SIL si HIL; HIL agregat pe N=5). Cele
opt cifre-titlu se extrag cu:

    grep -E "^(SIL|HIL),lat200_jit50," c1_benchmark/paper/campaign_summary.csv

adica p95 RTT si pierderea pentru fiecare RMW, pe HIL (7696.9 ms / 96.3 % zenoh vs
635.2 ms / 14.7 % cyclonedds) si pe SIL (475.7 / 1.3 % vs 484.2 / 1.8 %): raportul 12x
apare pe legatura fizica si nu se vede pe loopback.

Campaniile anterioare (loopback N=10, iunie 2026) sunt ARHIVA: tabelul lor sta in
`c1_benchmark/NOTA_METODOLOGICA_C1.md`, sectiunea "Campanii arhivate", si nu se citeaza.

Rezultatele C6 sunt SIL, N=1 pana la campania S4; se citesc din rapoartele de unitate
(`../DOC/RAPOARTE/`), nu de aici.

## Mediu

| Componenta | Versiune |
|---|---|
| Sistem de operare | Ubuntu 24.04 LTS |
| ROS 2 | Jazzy Jalisco |
| Middleware comparat | `rmw_zenoh_cpp`, `rmw_cyclonedds_cpp` |
| Simulator | Gazebo (ros_gz), pornit headless |
| Limbaj | Python 3.12 (`/usr/bin/python3`; C6 in `~/ros2_ws/.venv_c6` cu OSQP) |
| Emulare retea | iproute2 / tc netem |

## Compilare si verificare

    # garda: nu se construieste peste o campanie in mers
    pgrep -af "run_campaign|bench_|rmw_zenohd|c6_smoke" && echo "STOP" || echo "liber"

    cd ~/ros2_ws
    source /opt/ros/jazzy/setup.bash
    colcon build --symlink-install --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3
    source install/setup.bash

    # testul de fum al depozitului (fara ROS)
    cd ~/ros2_ws/src && ./smoke_all.sh

Selftestele C6, fara ROS: `python3 c6_safety/c6_safety/<modul>.py --selftest`
(`rover_dyn`, `cbf_core`, `episode`, `certif_core`, `brate`).

## Conventii

1. Cod, `.md` si `.tex` = ASCII pur (fara diacritice; verificare `grep -nP '[^\x00-\x7F]'`).
2. Logica pura, testata izolat, precede nodul ROS; nodurile nu contin logica.
3. Un singur publisher pe `/sar/linkstate`.
4. `git add` DOAR cu cai explicite; niciodata `git add -A`. Datele brute nu intra in git.
5. Pachetele INGHETATE nu se modifica; corectiile intra ca fisiere-frate sau in pachetul viu.
6. Tagurile sunt imutabile.

## Licenta

Licentierea este pe artefact, nu pe depozit. Artefactul C1 (`c1_benchmark/`) este publicat
sub Apache-2.0 (`c1_benchmark/LICENSE`); `c6_safety` declara Apache-2.0 in `package.xml`.
Restul depozitului (C2, C3, C4, materialele de curs) ramane fara licenta de reutilizare:
toate drepturile rezervate.
