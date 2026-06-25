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
- Rezultatele SIL sunt provizorii (N=1, deterministe pe seed) si trebuie inlocuite cu date
  de campanie (N=5) inainte de orice submisie; fiecare README marcheaza explicit aceste cifre.
- TODO: contributia C2 nu este mapata explicit pe un pachet in sursele curente -- de clarificat.
