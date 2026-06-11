# sar_plugins — etajul de misiune si teleop avansat (Zenoh/ROS2/SAR)

Pachet de plugin-uri pentru cele doua proiecte existente (roi de drone +
rover teleoperat), construit pe acelasi principiu ca restul tezei:
**logica pura, testabila fara ROS** + **noduri ROS2 subtiri** + **strat
Gazebo optional**. Nimic de aici nu modifica codul existent — integrarea
se face exclusiv prin topicuri si remapari in launch.

## Ce e verificat si unde

| Strat | Fisiere | Verificare |
|---|---|---|
| Logica pura | `channel.py, radio_link.py, coverage.py, victims.py, battery.py, guard.py, predictor.py` | `test_plugins.py` — **55/55 verificari trec** (rulat aici) |
| Demo integrat | `demo_plugins_sim.py` | rulat aici; 4 figuri PNG + bilant; 4 asertii de sanatate trec |
| Noduri ROS2 | `nodes/*.py` (9 noduri + 2 launch) | `py_compile` aici; rularea propriu-zisa cere masina ta cu ROS2 Jazzy |
| Strat Gazebo | `gz/*` | `patch_world_sensors.py` testat pe o lume-mini (XML valid, idempotent); fragmentele SDF si bridge-urile YAML validate sintactic |
| Tooling | `tools/manifest.py, tools/run_experiment.sh` | manifestul rulat aici; scriptul bash verificat cu `bash -n` |

## Harta modulelor

| Modul / nod | Rol | Topicuri (in -> out) | Articol |
|---|---|---|---|
| `radio_link.py` + `nodes/radio_link_node.py` | link radio log-distance: distanta -> {ms,jit,loss,down}; profile `open_field`/`urban_rubble`/`forest`; mod proxy optional | `/swarm/telemetry` -> `/swarm/linkstate` (sau schema plata compatibila `/teleop/linkstate`) | A1, A3 |
| `coverage.py` + `nodes/coverage_node.py` | grila de acoperire, procent + jaloane 25/50/.../99% | `/swarm/telemetry` -> `/mission/coverage` (1 Hz) + `~/sar_data/coverage.csv` | A3 |
| `victims.py` + `nodes/victim_node.py` | victime reproducibile (seed), detectie Poisson in raza senzorului | `/swarm/telemetry` -> `/mission/victims` (evenimente) + `/mission/victims_static` (latched) + CSV | A3 |
| `battery.py` + `nodes/battery_node.py` | consum P=P_hover+k_v*|v|, praguri RTL static+dinamic, LAND | `/swarm/telemetry` -> `/swarm/battery` (1 Hz) + o comanda failsafe pe `failsafe_cmd_topic` (sablon cu `%ID%`/`%STATE%`) + CSV | A3 |
| `guard.py` + `nodes/obstacle_guard_node.py` | oprire/franare la obstacol din lidar, histerezis; **proxy** intre operator si rover | `/teleop/cmd` + `/scan` -> `/teleop/cmd_safe` + `/teleop/guard` | A2 |
| `predictor.py` + `nodes/predictive_display_node.py` | afisaj predictiv dead-reckoning la operator; logheaza eroarea predictiei vs naiv | `/teleop/pose` + `/teleop/cmd` -> `/teleop/pose_pred` (20 Hz) + `~/sar_data/predict.csv` | A2 |
| `channel.py` + `nodes/video_link_node.py` | canal video prin legatura degradata (drop/intarziere cadre) | `/camera/image/compressed` + linkstate -> `/teleop/video` + `/teleop/video_stats` | A2 |
| `nodes/quad_adapter_node.py` | adaptor JSON roi -> Twist pentru MulticopterVelocityControl (lumea oficiala gz `multicopter_velocity_control.sdf`) | `/swarm/cmd_vel` -> `/%ID%/gazebo/command/twist` | A3 |
| `gz/patch_world_sensors.py` | injecteaza idempotent in SDF: Sensors+gpu_lidar, Imu, NavSat+coordonate Bucuresti | `world.sdf -> world_patched.sdf` | A2, A3 |
| `gz/battery_plugin.sdf.xml`, `gz/wind_world.sdf.xml` | fragmente gata de lipit: LinearBatteryPlugin, WindEffects | — | A3 |
| `gz/bridge_rover.yaml`, `gz/bridge_swarm.yaml` | ros_gz_bridge: scan/imu/navsat/camera/cmd_vel/odometry; 5 drone d1..d5 | gz <-> ROS2 | A2, A3 |
| `tools/run_experiment.sh` + `tools/manifest.py` | rulare reproductibila: export RMW, porneste `rmw_zenohd` daca e cazul, manifest JSON, `ros2 bag record` | — | A1 |

## Schemele JSON (std_msgs/String)

- linkstate plat (identic cu `/teleop/linkstate` existent):
  `{"ms":120,"jit":40,"loss":0.15,"down":false}`
- linkstate agregat roi: `{"d1":{...},"d2":{...}}` (+ diagnostic `snr,rssi,d`)
- `/mission/coverage`: `{"t":..,"pct":..,"cells_covered":..,"cells_total":..,"milestones":{"25":t,...}}`
- eveniment victima: `{"victim":i,"t":..,"by":"d2","x":..,"y":..}`
- `/swarm/battery`: `{"d1":{"soc":0.42,"state":"NORMAL","used_wh":..},...}`
- `/teleop/pose_pred`: `{"t":..,"x":..,"y":..,"th":..,"age":..,"extrap":bool}`
- comanda prin garda: JSON-ul tau `{"v":..,"w":..}` nemodificat in chei,
  cu `v` limitat la nevoie si campul `guard_blocked` adaugat.

## Integrare fara modificari de cod (doar remapari)

1) **Roi (etajul de misiune)** — porneste-ti sistemul existent, apoi:
```
ros2 launch nodes/mission_plugins.launch.py profile:=urban_rubble seed:=42
```
Totul asculta `/swarm/telemetry` pe care il publici deja. Pentru failsafe,
seteaza `failsafe_cmd_topic`/`failsafe_template` pe schema ta de comanda.

2) **Rover (garda + predictiv + video)** — singura schimbare: robotul
asculta comanda FILTRATA. In launch-ul tau, la `robot_node.py` adaugi
remaparea `-r /teleop/cmd:=/teleop/cmd_safe`, apoi:
```
ros2 launch nodes/teleop_addons.launch.py
```

3) **Gazebo cu senzori** — pe lumea ta existenta:
```
python3 gz/patch_world_sensors.py worlds/teleop_course.sdf worlds/teleop_sensors.sdf \
        --model rover --link chassis --lidar --imu --navsat
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=gz/bridge_rover.yaml
```
Fragmentul de baterie/vant se lipeste manual in SDF unde indica comentariile.

4) **Experiment A1 (Zenoh vs CycloneDDS)**:
```
./tools/run_experiment.sh loss_30 rmw_zenoh_cpp 120
./tools/run_experiment.sh loss_30 rmw_cyclonedds_cpp 120
```
Fiecare rulare primeste manifest JSON + bag in `~/sar_data/bags/...`.

## Demo fara ROS (verificare rapida oriunde)

```
python3 test_plugins.py        # 55/55
python3 demo_plugins_sim.py    # figuri demo_*.png + bilant misiune
```

Toate CSV-urile merg in `~/sar_data/` — acelasi loc si format ca restul
proiectului, deci analizoarele existente le pot citi direct.
