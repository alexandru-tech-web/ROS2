# Documentatie tehnica -- harta pe contributii

Index al documentatiilor pe pachete, mapate pe contributiile tezei (C1-C4) si pe harta
de articole (A1-A5). Fiecare nume trimite la documentatia tehnica a pachetului (README-ul
lui, structurat in 8 sectiuni: scop, context, arhitectura, inventar, date tehnice, sintaxe
de pornire, verificare, igiena datelor). Toate README-urile de pachet sunt ASCII strict.

## C1 -- benchmark de middleware sub retea degradata

Compararea `rmw_zenoh` vs `rmw_cyclonedds_cpp` sub degradare controlata (`tc netem`), pe
doua straturi de masura: transport (RTT) si misiune (metrici operationale).

- [c1_benchmark](c1_benchmark/README.md) -- stratul de transport (microbenchmark RTT pe
  ecou). Pachet-sursa al articolului A1 (SSRR 2026).
- [sar_swarm](sar_swarm/README.md) -- stratul de aplicatie (misiune SAR cu roi de 4 drone;
  acoperire, victime raportate, timp).
- [sar_plugins](sar_plugins/README.md) -- etajul de misiune (degradare dependenta de
  distanta + telemetrie: baterie, acoperire, victime).

Tooling C1 (in `c1_benchmark/`):
- Selector de middleware: `selector_core.py` (nucleu pur + LOCO + regret) cu
  `reproduce_selector.py` (obiective CONTROL si CONSTIENT DE PIERDERE) si
  `reproduce_selector_mission.py` (obiectiv TELEMETRIE); `build_selector_dataset.py`
  reconstruieste dataset-ul din campania reala. Caracterizator ML: `reproduce_pdia.py`.
- [GHID_TESTARE.md](c1_benchmark/GHID_TESTARE.md) -- rulare pas-cu-pas a pipeline-ului si ce iese.
- [HIL_RUNBOOK.md](c1_benchmark/HIL_RUNBOOK.md) -- campanie pe doua masini (PC + RPi);
  `run_campaign.py --mode sil|hil` pastreaza schema de date identica SIL/HIL.
- [paper/](c1_benchmark/paper/) -- schelet articol A1 (DRAFT; cifre PROVIZORII SIL).

## C3 -- adaptare si rezilienta a legaturii

- [link_adaptive](link_adaptive/README.md) -- adaptare link-aware (NOMINAL / DEGRADED /
  CRITICAL, cu histerezis).
- [mesh_plugin](mesh_plugin/README.md) -- retea MESH multi-hop (recuperarea telemetriei
  prin releu hop-by-hop).

## C4 -- tele-impedanta / validare hardware

- [joint_emulator](joint_emulator/README.md) -- banc cu 6 servomotoare; impedanta adaptiva,
  encodere, estimare.
- [rehab_exo_description](rehab_exo_description/README.md) -- exoschelet de reabilitare
  (URDF, launch, failsafe).
- [servo_control](servo_control/README.md) -- demonstrator motor in Gazebo (comanda de la
  tastatura).

## Demonstrator mobil

- [teleop_rover](teleop_rover/README.md) -- rover teleoperat printr-o legatura degradata
  (comparatie drona vs robot mobil).

## Educational / tooling (in afara coloanei C1-C4)

- [curs_ros2](curs_ros2/README.md) -- ecosistem didactic ROS 2 (module de curs).
- [curs_ros2_interfaces](curs_ros2_interfaces/README.md) -- interfete custom (msg/srv/action)
  pentru curs.
- [gen_articol](gen_articol/README.md) -- generator de schelete de articole (infrastructura
  editoriala).

## Note

- Datele experimentale (campanii, rezultate brute, figuri de rulare) NU se versioneaza;
  vezi [.gitignore](.gitignore) si [CONTRIBUTING.md](CONTRIBUTING.md). In git intra codul,
  scripturile de analiza si figurile reprezentative din `*/docs/`.
- Rezultatele SIL (loopback, o singura masina) sunt PROVIZORII: campania de transport C1
  e N=10 pe loopback. HIL (doua masini + legatura reala, PC + RaspberryPi 4B) ramane
  comparatia AUTORITARA -- vezi [HIL_RUNBOOK.md](c1_benchmark/HIL_RUNBOOK.md). Fiecare
  README / figura / caption marcheaza explicit ca cifrele sunt SIL.
- TODO: contributia C2 nu este mapata explicit pe un pachet in sursele curente -- de clarificat.
