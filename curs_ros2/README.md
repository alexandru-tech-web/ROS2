# curs_ros2 + curs_ros2_interfaces — Documentatie tehnica

Cursul complet ROS 2 Jazzy (rclpy), structurat in 14 module (M0–M13), cu material
de lectie in `docs/`, cod functional pentru fiecare concept si un proiect final
integrator. Doua pachete: `curs_ros2` (ament_python — nodurile si lectiile) si
`curs_ros2_interfaces` (ament_cmake — interfetele custom, fiindca rosidl nu poate
genera tipuri intr-un pachet pur Python).

## 1. Compilare (ordinea conteaza)

```bash
cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash

# 1) INTAI interfetele (genereaza tipurile), apoi source
colcon build --packages-select curs_ros2_interfaces
source install/setup.bash

# 2) apoi pachetul de noduri
colcon build --packages-select curs_ros2
source install/setup.bash
```

Regula: `source install/setup.bash` in FIECARE terminal nou, dupa fiecare build.

## 2. Harta modulelor si sintaxele de pornire

| Modul | Tema | Sintaxa de pornire / verificare |
|---|---|---|
| M0 | concepte + CLI | `docs/00_introducere.md`, `docs/cheatsheet_cli.md` |
| M1 | noduri, timere, logging | `ros2 run curs_ros2 nod_simplu` |
| M2 | topicuri pub/sub (`/temperatura` Float64, `/alarma` String) | `ros2 run curs_ros2 publisher` + `ros2 run curs_ros2 subscriber` |
| M3 | launch (publisher + subscriber intarziat 3 s) | `ros2 launch curs_ros2 m3_launch.py` |
| M4 | parametri | `ros2 run curs_ros2 m4_param` apoi `ros2 param list/get/set` |
| M5 | servicii (`/aduna`) | `ros2 run curs_ros2 m5_server` + `ros2 run curs_ros2 m5_client`; manual: `ros2 service call /aduna ...` |
| M6 | actiuni (`/fibonacci`, cu feedback) | `ros2 run curs_ros2 m6_action_server` + `ros2 run curs_ros2 m6_action_client`; manual: `ros2 action send_goal /fibonacci ... --feedback` |
| M7 | interfete custom (`/temperatura_custom`) | `ros2 run curs_ros2 m7_pub` + `ros2 run curs_ros2 m7_sub` |
| M8 | QoS (reliability/durability) | `ros2 run curs_ros2 m8_pub` + `ros2 run curs_ros2 m8_sub`; `ros2 topic info /... --verbose` |
| M9 | executors si callback groups | `ros2 run curs_ros2 m9_executor` |
| M10 | TF2 (broadcaster + listener) | `ros2 run curs_ros2 m10_broadcaster` + `ros2 run curs_ros2 m10_listener`; `ros2 run tf2_tools view_frames` |
| M11 | lifecycle nodes | `ros2 run curs_ros2 m11_lifecycle`; `ros2 lifecycle set /... configure` |
| M12 | turtlesim aplicat | `ros2 run turtlesim turtlesim_node` + `ros2 run curs_ros2 m12_patrat` (sau `m12_control`) |
| M13 | proiect final integrator | `ros2 launch curs_ros2 m13_proiect_launch.py` |

Fiecare modul are lectia lui in `docs/NN_*.md`: concept, cod comentat, rulare,
verificare din CLI, exercitii si capcane frecvente.

## 3. Interfetele custom (curs_ros2_interfaces)

| Interfata | Definitie |
|---|---|
| `msg/Temperatura` | `float64 valoare`, `string status` |
| `srv/AjustareTemperatura` | cerere `float64 prag_nou` -> raspuns `bool succes`, `float64 prag_anterior`, `string mesaj` |
| `action/Incalzire` | goal `float64 tinta` -> result `bool atins`, `float64 temperatura_finala`; feedback `float64 temperatura_curenta` |

```bash
ros2 interface show curs_ros2_interfaces/msg/Temperatura
ros2 interface list | grep curs_ros2
```

Esentialul mecanismului rosidl (detaliat in `docs/07_interfete_custom.md`):
pachet SEPARAT ament_cmake; `rosidl_generate_interfaces` in CMakeLists;
`<member_of_group>rosidl_interface_packages</member_of_group>` in package.xml
(cea mai des uitata linie); build interfete -> source -> build noduri.

## 4. Proiectul final (M13)

Senzor sinusoidal + monitor cu praguri, parametri live si serviciu custom:

```bash
# T1 — sistemul complet
ros2 launch curs_ros2 m13_proiect_launch.py

# T2 — alarma interpretata
ros2 topic echo /senzor/alarma

# T3 — schimbarea pragului LIVE, fara repornire
ros2 service call /ajusteaza_prag curs_ros2_interfaces/srv/AjustareTemperatura "{prag_nou: 35.0}"
ros2 param get /monitor_temperatura prag_atentie

# testele nucleului pur (inainte de rularea live)
python3 -m pytest src/curs_ros2/test/test_logica.py -v
```

Combina M2 (topicuri) + M4 (parametri) + M5 (servicii) + M7 (interfata custom).

## 5. Rolul in depozit

Pachet de FORMARE si arhiva didactica: aici sunt demonstrate izolat conceptele
folosite apoi in pachetele de cercetare (QoS si RMW -> `c1_benchmark`; launch si
parametri -> toate; TF2 si URDF -> `rehab_exo_description`, `joint_emulator`).
Nu intra in campanii si nu are dependinte spre restul depozitului.
