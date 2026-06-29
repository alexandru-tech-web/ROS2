# sar_plugins

Etajul de misiune si add-on-urile de teleoperare peste sistemele existente (roiul
`sar_swarm`, roverul `teleop_rover`): link radio dependent de distanta, acoperire, victime,
baterie cu failsafe energetic, garda de obstacole, afisaj predictiv, link video degradat si
interferenta RF (Gilbert-Elliott). Metodologia tezei: nucleu pur testabil fara ROS ->
nod ROS subtire (JSON pe std_msgs/String), integrarea facandu-se exclusiv prin topicuri,
fara modificari in pachetele existente.

## Scop

Furnizeaza, ca add-on-uri reutilizabile, degradarea dependenta de DISTANTA (canal radio cu
atenuare log-distance) si telemetria de misiune (acoperire, victime, baterie). Conform
README-ului vechi si docstring-urilor, completeaza degradarea uniforma din `sar_swarm` cu
degradare dependenta de distanta / geometrie, alimentand stratul aplicativ al contributiei
C1 (afirmatie scrisa explicit in vechiul README; restul detaliilor de campanie raman TODO).

Atentie operationala (din docstring-uri): topicul de linkstate (`/sar/linkstate` sau
`/swarm/linkstate`) trebuie sa aiba UN SINGUR publisher. `radio_link_node` /
`rf_channel_node` sunt ALTERNATIVE la `fault_injector_node` din `sar_swarm` -- nu rula doua
surse simultan pe acelasi topic.

## Arhitectura

Pachet de tip 'zero-build': NU exista `package.xml` sau `setup.py` in arbore, deci nu exista
entry_points (`console_scripts`) si nicio comanda `ros2 run sar_plugins <...>`. Nodurile se
ruleaza direct cu `python3 <nod>.py --ros-args ...`, iar launch-urile cu `ros2 launch <cale>`.

Trei straturi:

- Nuclee pure (fara ROS), in radacina pachetului: `channel.py`, `radio_link.py`,
  `coverage.py`, `victims.py`, `battery.py`, `guard.py`, `predictor.py`, `rf_interference.py`,
  `campaign_hmi_core.py`, `post_run_core.py`.
- Noduri ROS subtiri, in `nodes/`: impacheteaza nucleele in publisher/subscriber pe JSON
  (std_msgs/String). `nodes/node_utils.py` ofera profilurile QoS (RELIABLE pentru comenzi,
  BEST_EFFORT pentru telemetrie) si parsarea pozelor JSON.
- Strat de mediu / simulare: `gz/` (poduri `ros_gz`, lumi SDF, injector de senzori) si
  `tools/` (campanii, manifest, analiza, verdict).

Verificarea offline a nucleelor pure: `rf_interference.py`, `campaign_hmi_core.py` si
`post_run_core.py` au functie `_selftest()` rulabila cu `python3 <fisier>.py`. Nucleele
clasice (channel, radio_link, coverage, victims, battery, guard, predictor) se verifica prin
suita `test_plugins.py`; `rf_interference` are si suita dedicata `test_rf_interference.py`.

## Fisiere

Nuclee pure (radacina):

| Fisier | Rol (din docstring/cod) |
|---|---|
| `channel.py` | `DegradedChannel`: canal de comunicatie degradat (cadere + pierdere + latenta + jitter la receptie), pur, reutilizabil de link radio / video / proxy. |
| `radio_link.py` | `LogDistanceRadioLink` + `make_link`: degradarea legaturii ca functie de distanta fata de GCS (model log-distance Rappaport). Profiluri: `open_field`, `urban_rubble`, `forest`. |
| `coverage.py` | `CoverageGrid`: grila booleana de acoperire; procent acoperit, timp-pana-la-X%, export CSV. |
| `victims.py` | `VictimField`: victime reproducibile (seed) + detectie probabilistica Poisson in raza senzorului. |
| `battery.py` | `BatteryModel`: energie (P = P_hover + k_v*|v|) + masina de stari NORMAL/RTL/LAND, prag RTL optional dinamic dupa distanta. |
| `guard.py` | `ObstacleGuard`: oprire/franare la obstacol pe sectorul frontal al scanarii lidar, cu histerezis; rotatia si marsarierul raman permise. |
| `predictor.py` | `DeadReckoningPredictor` + `unicycle_step`: predictia pozitiei curente (predictive display) prin integrare uniciclu exacta peste comenzile trimise. |
| `rf_interference.py` | Nucleu pur pentru interferenta RF: pierdere corelata in rafale (`BurstProcess`, Gilbert-Elliott, paritate cu netem `gemodel`) + `cochannel_sinr`. Are `_selftest()`. |
| `campaign_hmi_core.py` | Nucleu pur (fara ROS/Tk) pentru panoul de campanie: construieste/valideaza matricea RMW x conditie x repetitii, formateaza comanda de lansare. Are `_selftest()`. |
| `post_run_core.py` | Nucleu pur pentru vizualizatorul post-rulare: loadere CSV + agregari peste rezultatele unei campanii, cu detectie de schema. Are `_selftest()`. |

Frontend-uri si demo (radacina):

| Fisier | Rol |
|---|---|
| `campaign_panel.py` | GUI Tkinter subtire peste `campaign_hmi_core` (matrice RMW x conditii x reps x mod SIL/HIL). Docstring: nu se poate verifica vizual headless. |
| `post_run_viewer.py` | Vizualizator OFFLINE post-rulare: descopera CSV-urile sub `--root`, le rezuma (`post_run_core`) si produce tabel + figura. |
| `demo_plugins_sim.py` | Demonstratia integrata FARA ROS: 5 drone in lawnmower, link radio log-distance, acoperire din telemetria livrata, victime, baterie. Produce `demo_*.png`. |
| `test_plugins.py` | Verificari automate pentru nucleele pure (fara ROS); iese cu cod != 0 daca ceva pica. |
| `test_rf_interference.py` | Verificari pure pentru `rf_interference` (apeleaza `rf._selftest()`). |
| `requirements.txt` | Dependinte pip externe: `matplotlib`, `numpy` (rclpy / *_msgs / launch vin din ROS). |
| `README_PLUGINS.md` | Fisa detaliata per nod (in/out, `ros2 topic echo`) -- referinta. |

Noduri ROS (`nodes/`):

| Fisier | Rol (din docstring/cod) |
|---|---|
| `radio_link_node.py` | Publisher de linkstate per drona din model log-distance (+ mod proxy optional). Nod `radio_link`. |
| `coverage_node.py` | Acoperirea zonei din pozele dronelor; publica `/mission/coverage` + CSV. Nod `coverage_tracker`. |
| `victim_node.py` | Plaseaza N victime (latched pe `static_topic`) si emite evenimente de detectie la 10 Hz. Nod `victim_field`. |
| `battery_node.py` | Baterie per drona + failsafe RTL/LAND; la tranzitie publica o comanda pe `failsafe_cmd_topic`. Nod `battery_monitor`. |
| `obstacle_guard_node.py` | Proxy de comanda operator->rover, filtreaza inaintarea prin `ObstacleGuard` pe baza `/scan`. Mod `json` sau `twist`. Nod `obstacle_guard`. |
| `predictive_display_node.py` | 'Fantoma' predictiva la operator (20 Hz); logheaza eroarea predictiei vs naiv in CSV. Nod `predictive_display`. |
| `video_link_node.py` | Trece CompressedImage prin `DegradedChannel` cu parametri live din linkstate; publica statistici 1 Hz. Nod `video_link`. |
| `quad_adapter_node.py` | Traduce comenzile JSON ale roiului in geometry_msgs/Twist pe topicul fiecarui model Gazebo. Nod `quad_adapter`. |
| `rf_channel_node.py` | Publica linkstate cu stare RF variabila in timp (Gilbert-Elliott din `rf_interference`); imbogateste aditiv schema. Nod `rf_channel`. |
| `netem_bridge_node.py` | Punte SIL->HIL: din `/sar/linkstate` construieste comanda `tc netem` (dry-run implicit, `enable=true` o executa cu sudo). Foloseste `rf.linkstate_to_netem`. |
| `node_utils.py` | Utilitare comune: profiluri QoS + parsarea flexibila a pozelor JSON. Folosit de toate nodurile. |
| `mission_sar.launch.py` | Etajul de misiune pe topicurile `/sar/*` (generatia noua a roiului). |
| `mission_plugins.launch.py` | Varianta veche a etajului de misiune pe `/swarm/*`. |
| `teleop_addons.launch.py` | Add-on-urile roverului: garda + predictiv + video. |

Strat Gazebo (`gz/`):

| Fisier | Rol |
|---|---|
| `patch_world_sensors.py` | Injecteaza idempotent senzori (gpu_lidar / imu / navsat / camera) intr-un SDF. |
| `bridge_rover.yaml`, `bridge_swarm.yaml` | Configuratii pentru `ros_gz_bridge parameter_bridge`. |
| `wind_world.sdf.xml`, `battery_plugin.sdf.xml` | Fragmente SDF (vant; baterie Gazebo). TODO: de confirmat detaliile interne (fisiere XML, nu citite linie cu linie). |
| `test_world_mini.sdf` | Lume SDF minimala de test. TODO: de confirmat. |

Unelte (`tools/`):

| Fisier | Rol |
|---|---|
| `manifest.py` | Scrie un manifest JSON de reproductibilitate langa bag. CLI: `--out`, `--scenario` (obligatorii), `--rmw`, `--seed`, `--extra`. |
| `analyze_missions.py` | Agregarea campaniei de misiune in `{OUT}/analysis/` (sumar CSV + figuri T90/acoperire/victime/RTL). Suporta `--selftest`. |
| `verdict_misiune.py` | Verdictele M1-M4 din `mission_summary.csv`, tolerant la schema. Suporta `--selftest`. |
| `run_experiment.sh`, `mission_experiment.sh`, `mission_experiment_severe.sh`, `preflight_misiune.sh` | Scripturi shell de campanie/inregistrare. TODO: de confirmat argumentele exacte (scripturi `.sh`, necitite in detaliu). |

## Sintaxe de rulare

Nu exista build colcon pentru acest pachet (fara `package.xml`/`setup.py`); se ruleaza
direct cu Python / `ros2 launch`.

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws/src/sar_plugins

# verificare offline a nucleelor pure
python3 test_plugins.py             # nucleele clasice
python3 test_rf_interference.py     # rf_interference
python3 rf_interference.py          # _selftest direct
python3 campaign_hmi_core.py        # _selftest direct
python3 post_run_core.py            # _selftest direct

# demo integrat fara ROS (produce demo_*.png)
python3 demo_plugins_sim.py

# etajul de misiune pe topicurile /sar/* (generatia noua)
ros2 launch nodes/mission_sar.launch.py profile:=urban_rubble seed:=42 \
    n_victims:=6 sensor_r:=6.0

# add-on-urile roverului (garda + predictiv + video)
ros2 launch nodes/teleop_addons.launch.py d_stop:=0.8 guard_msg:=json

# varianta veche pe /swarm/*
ros2 launch nodes/mission_plugins.launch.py profile:=urban_rubble seed:=7 \
    area:=40.0 pose_topic:=/swarm/telemetry

# un nod izolat (exemplu): linkstate pe /sar/*
python3 nodes/radio_link_node.py --ros-args \
    -p pose_topic:=/sar/telemetry -p linkstate_topic:=/sar/linkstate \
    -p profile:=urban_rubble -p seed:=42

# vizualizator offline al unei campanii
python3 post_run_viewer.py --root <results_dir> [--out <dir>]

# injectarea de senzori intr-o lume Gazebo (one-shot)
python3 gz/patch_world_sensors.py worlds/in.sdf worlds/out.sdf \
    --model rover --link chassis --lidar --imu --navsat --camera
```

Argumente launch (din `DeclareLaunchArgument`):

- `mission_sar.launch.py`: `profile` (`open_field`), `seed` (`42`), `n_victims` (`6`),
  `sensor_r` (`6.0`).
- `mission_plugins.launch.py`: `area` (`30.0`), `pose_topic` (`/swarm/telemetry`),
  `profile` (`open_field`), `seed` (`1`), `sensor_r` (`6.0`).
- `teleop_addons.launch.py`: `d_stop` (`0.6`), `d_slow` (`1.5`), `guard_msg` (`json`),
  `linkstate` (`/teleop/linkstate`).

CLI argparse confirmat: `post_run_viewer.py` (`--root` obligatoriu, `--out`); `manifest.py`
(`--out`, `--scenario` obligatorii; `--rmw`, `--seed`, `--extra`); `patch_world_sensors.py`
(`input`, `output` pozitionale; `--model`=rover, `--link`=chassis, `--lidar`, `--imu`,
`--navsat`, `--camera`).

## Parametri si topicuri

Topicuri si parametri reali din cod (`declare_parameter`, `create_publisher`,
`create_subscription`). Mesajele de telemetrie/stare sunt JSON pe std_msgs/String, in afara
de cele marcate altfel.

`radio_link_node` (nod `radio_link`): sub `pose_topic` (`/swarm/telemetry`), pub
`linkstate_topic` (`/swarm/linkstate`); mod proxy optional `proxy_in` (`""`) -> `proxy_out`
(`/swarm/cmd_degraded`). Parametri: `gcs_x/gcs_y/gcs_z` (`0.0`), `rate_hz` (`5.0`), `profile`
(`open_field`), `seed` (`1`), `shadowed` (`True`), `d_max` (`0.0`), `overrides` (`"{}"`),
`flat_compat` (`True`).

`coverage_node` (nod `coverage_tracker`): sub `pose_topic` (`/swarm/telemetry`), pub
`coverage_topic` (`/mission/coverage`). Parametri: `xmin/xmax/ymin/ymax` (`-30..30`), `cell`
(`1.0`), `sensor_r` (`6.0`), `rate_hz` (`1.0`), `csv_path` (`~/sar_data/coverage.csv`).

`victim_node` (nod `victim_field`): sub `pose_topic` (`/swarm/telemetry`), pub `events_topic`
(`/mission/victims`) si `static_topic` latched (`/mission/victims_static`). Parametri: `n`
(`6`), `seed` (`3`), `min_sep` (`5.0`), `xmin/xmax/ymin/ymax` (`-30..30`), `sensor_r` (`6.0`),
`p_detect` (`2.0`), `csv_path` (`~/sar_data/victims.csv`).

`battery_node` (nod `battery_monitor`): sub `pose_topic` (`/swarm/telemetry`), pub
`state_topic` (`/swarm/battery`); comanda failsafe pe `failsafe_cmd_topic` (`""` = doar
monitorizare, RELIABLE). Parametri: `capacity_wh` (`60.0`), `p_hover_w` (`120.0`), `k_v_w`
(`8.0`), `soc_rtl` (`0.30`), `soc_land` (`0.10`), `v_rtl` (`4.0`), `dynamic` (`True`),
`dynamic_margin` (`1.5`), `home_x/home_y` (`0.0`), `failsafe_template`
(`{"action":"rtl","id":"%ID%"}`), `csv_path` (`~/sar_data/battery.csv`). In
`mission_sar.launch.py` template-ul e suprascris cu
`{"type":"drone","id":"%ID%","action":"rth"}` pe `/sar/operator`.

`obstacle_guard_node` (nod `obstacle_guard`): sub `scan_topic` (`/scan`,
sensor_msgs/LaserScan) si `in_topic` (`/teleop/cmd`); pub `out_topic` (`/teleop/cmd_safe`) si
`status_topic` (`/teleop/guard`). Tipul mesajului de comanda dupa `msg` (`json` =
std_msgs/String, `twist` = geometry_msgs/Twist). Parametri: `d_stop` (`0.6`), `d_slow`
(`1.5`), `sector_deg` (`70.0`), `release_factor` (`1.25`).

`predictive_display_node` (nod `predictive_display`): sub `cmd_topic` (`/teleop/cmd`) si
`pose_topic` (`/teleop/pose`); pub `pred_topic` (`/teleop/pose_pred`). Parametri: `rate_hz`
(`20.0`), `max_extrapolation_s` (`2.0`), chei configurabile `key_t/x/y/th/v/w`, `csv_path`
(`~/sar_data/predict.csv`).

`video_link_node` (nod `video_link`): sub `in_topic` (`/camera/image/compressed`,
sensor_msgs/CompressedImage) si `linkstate_topic` (`/teleop/linkstate`); pub `out_topic`
(`/teleop/video`, CompressedImage) si `stats_topic` (`/teleop/video_stats`). Parametri:
`link_id` (`""`), `seed` (`1`).

`quad_adapter_node` (nod `quad_adapter`): sub `cmd_topic` (`/swarm/cmd_vel`); pub
geometry_msgs/Twist pe topicuri derivate din `out_template` (`/%ID%/gazebo/command/twist`).
Parametri: `key_id` (`id`), `key_vx/vy/vz` (`vx/vy/vz`), `key_wz` (`wz`).

`rf_channel_node` (nod `rf_channel`): pub `topic` (`/sar/linkstate`). Parametri: `rate_hz`
(`5.0`), `lat_ms` (`40.0`), `jit_ms` (`8.0`), `p` (`0.0857`), `r` (`0.2000`), `seed` (`0`).
Mesaj publicat:
`{"down":false,"lat_ms":..,"jit_ms":..,"loss":..,"burst_len":..,"instant_drop":..,"p":..,"r":..}`.

`netem_bridge_node`: sub `topic` (`/sar/linkstate`). Parametri: `iface` (`lo`), `enable`
(`False` = dry-run). NU publica topicuri; aplica (sau logheaza) comenzi `tc netem`.
