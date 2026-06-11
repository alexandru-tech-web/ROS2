# GHID DE PORNIRE — harta intregului repo ROS2 (PhD Alexandru)

Un singur document care raspunde la: ce pachet, ce face, cu ce comanda
porneste, in ce terminal, in ce ordine. Detaliile fiecarui pachet raman
in README-ul lui; aici e doar ORCHESTRAREA.

## Harta repo-ului (~/ros2_ws/src)
| Pachet | Rol | Referinta detaliata |
|---|---|---|
| `c1_benchmark/` | campania A1: rmw_zenoh vs rmw_cyclonedds sub tc netem real | `c1_benchmark/README.md` + `RUNBOOK.md` |
| `sar_swarm/` | roiul SAR (generatia 10 iunie): drone, GCS, fault injector, probe RTT, dashboard | `sar_swarm/README.md` |
| `sar_plugins/` | etajul de misiune (link radio, acoperire, victime, baterie+rth) + teleop avansat (garda, predictiv, video) | `sar_plugins/README_PLUGINS.md` |
| `teleop_rover/` | roverul teleoperat prin legatura degradata (SIL + Gazebo) | comentariile din fisiere + launch/ |
| `rehab_exo_description/` | exoscheletul de reabilitare + extensiile telerehab v0.3 | README-ul pachetului |
| `servo_control/` | motorul/servo initial din Gazebo (stratul demonstrativ istoric) | fisierele pachetului |
| `curs_ros2/` | materiale de invatare | — |

## REGULILE DE AUR (lectiile platite pe 11 iunie)
1. **O singura campanie C1 odata** si **NIMIC ROS in paralel** pe masina
   in timpul ei — procesele paralele otravesc masuratorile.
2. **Nu inlocui niciodata un folder cat ruleaza ceva din el**
   (rm -rf / unzip = crash garantat). Ctrl+C intai.
3. **Rezultatele in afara pachetului**: `--out ~/c1_results...`
4. Dupa orice incident: `./preflight.sh` inainte de a relua.
5. Tot ce e nou si bun se comite IMEDIAT in git (ce nu e comis, dispare —
   verificat pe pielea noastra).

## WORKFLOW 1 — Campania C1 (PRIORITATEA pana pe 19 iunie)
Un singur terminal. Masina libera. Nimic altceva ROS pornit.

    cd ~/ros2_ws/src/c1_benchmark
    ./preflight.sh                       # trebuie: VERDICT: GO
    python3 test_bench_core.py && python3 analyze_campaign.py --selftest
    sudo -v
    # repetitia generala (~40 min):
    python3 run_campaign.py --iface lo --reps 2 --duration 10 --out ~/c1_results
    python3 analyze_campaign.py ~/c1_results
    #  -> campaign_summary.csv la Claude pentru sanity (ideal: pierdere ~0;
    #     loss_30: ~51% pe ecou). Abia apoi:
    # CAMPANIA COMPLETA (~3-4 h, peste noapte):
    python3 run_campaign.py --iface lo --reps 5 --out ~/c1_results_full
    python3 analyze_campaign.py ~/c1_results_full

Dupa campanie: figurile din `~/c1_results_full/analysis/` intra in
`paper/main.tex`; verdictele H1–H4 se dau pe cifre.

## WORKFLOW 2 — Roiul SAR cu etajul de misiune
| Terminal | Comanda |
|---|---|
| T1 | `source /opt/ros/jazzy/setup.bash && export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` apoi porneste roiul: `cd ~/ros2_ws/src/sar_swarm && python3 sar_launcher.py` (argumente/scenarii: README-ul pachetului sau `--help`) |
| T2 | acelasi export, apoi: `ros2 launch ~/ros2_ws/src/sar_plugins/nodes/mission_sar.launch.py profile:=urban_rubble seed:=42` |
| T3 (optional) | `~/ros2_ws/src/sar_plugins/tools/run_experiment.sh urban_rubble rmw_cyclonedds_cpp 300` — bag + manifest |

Reguli locale: acelasi RMW exportat in toate terminalele; pe
`/sar/linkstate` publica UN SINGUR nod (radio_link din T2 SAU
fault_injector din T1, nu ambele). Verificari rapide:
`ros2 topic echo /mission/coverage --once`, `/sar/battery --once`.
Failsafe-ul energetic e viu: sub 30% baterie, drona primeste `rth`
si se intoarce singura.

## WORKFLOW 3 — Roverul teleoperat in Gazebo cu senzori
| Terminal | Comanda |
|---|---|
| T0 (o data) | `python3 ~/ros2_ws/src/sar_plugins/gz/patch_world_sensors.py worlds/teleop_course.sdf worlds/teleop_sensors.sdf --model rover --link chassis --lidar --imu` |
| T1 | `gz sim -r worlds/teleop_sensors.sdf` |
| T2 | `ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=$HOME/ros2_ws/src/sar_plugins/gz/bridge_rover.yaml` |
| T3 | `ros2 launch ~/ros2_ws/src/teleop_rover/launch/teleop_gazebo.launch.py` — cu robot_node remapat: `-r /teleop/cmd:=/teleop/cmd_safe` |
| T4 | `ros2 launch ~/ros2_ws/src/sar_plugins/nodes/teleop_addons.launch.py` |

Verificari: `/teleop/guard --once` (garda vede lidar-ul),
`/teleop/pose_pred --once` (predictia curge), `/teleop/video_stats --once`.

## Unde ajung datele
- plugin-uri: `~/sar_data/*.csv` + `~/sar_data/bags/...`
- campania C1: `~/c1_results*/` (NICIODATA in pachet)
- rover: `~/teleop_data/robot_log.csv`
Ce trimiti la Claude pentru interpretare: `campaign_summary.csv` (C1),
`coverage.csv`+`battery.csv` (roi), `predict.csv` (A2).

## Dupa campanie (sprintul J4–J8, pe scurt)
J4: figurile finale in paper/ si verdictele H1–H4. J5: sectiunile IV–V pe
cifre. J6: Discussion + abstract. J7: citire integrala, 8 pagini, pdflatex
curat. **J8 (joi 18): SUBMISIE — nu lasa pe 19.**
