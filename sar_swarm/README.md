# sar_swarm — Roiul SAR cu middleware degradat

Roiul de drone pentru Search and Rescue: simulare completă cu 3 drone + GCS + injectare de defecte + probe de latență + dashboard. Stratul de aplicație al articolului A1 — misiunile rulează live peste `c1_benchmark`.

## Structura

```
sar_swarm/
├── drone_node.py          # drona autonomă (waypoints, telemetrie, failsafe baterie)
├── gcs_node_ros.py        # Ground Control Station (comenzi operatori)
├── sar_launcher.py        # lansatorul roiului (3 drone + GCS)
├── fault_injector_node.py # injectare de defecte controlată pe /sar/linkstate
├── latency_probe.py       # probe ping/pong pe /sar/probe/*
├── netem_core.py          # wrapper tc netem pentru roiu
├── dashboard_node.py      # dashboard text în terminal
├── sil_run.py             # simulare Software-in-the-Loop (fără ROS)
├── gen_world.py           # generator lume Gazebo pentru scenarii SAR
├── worlds/apocalypse.sdf  # lumea de test
├── scenarios/             # YAML-uri: ideal, loss_5, loss_15, loss_30, lat200_*
├── config/zenoh_session_config.json5
└── launch/
    ├── sar_ros.launch.py    # roiul complet (fără Gazebo)
    └── sar_gazebo.launch.py # roiul + Gazebo
```

## Topicuri ROS2

| Topic | Tip | Descriere |
|---|---|---|
| `/sar/telemetry` | String (JSON) | Telemetria dronelor (poziție, baterie, stare) |
| `/sar/linkstate` | String (JSON) | Starea legăturii `{ms, jit, loss, down}` |
| `/sar/operator` | String (JSON) | Comenzi operator `{type, id, action}` |
| `/sar/status` | String (JSON) | Starea misiunii (acoperire, victime, timp) |
| `/sar/probe/ping` | String | Ping pentru măsurarea latenței |
| `/sar/probe/pong` | String | Pong (răspuns la ping) |
| `/sar/probe/stats` | String | Statistici RTT live |
| `/sar/cmd/{id}` | String | Comandă individuală per dronă |
| `/sar/pose/{id}` | String | Poza dronei în Gazebo |

## Pornire rapidă

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws/src/sar_swarm

# L1 — roiul fără Gazebo (scenariul implicit = ideal)
ros2 launch launch/sar_ros.launch.py scenario:=ideal.yaml

# L1 — cu degradare
ros2 launch launch/sar_ros.launch.py scenario:=loss_30.yaml

# L2 — cu Gazebo
ros2 launch launch/sar_gazebo.launch.py scenario:=ideal.yaml

# Zenoh (două terminale)
# T1: ros2 run rmw_zenoh_cpp rmw_zenohd
# T2: export RMW_IMPLEMENTATION=rmw_zenoh_cpp && ros2 launch ...
```

## Comenzi operator

```bash
# trimite drona 2 la o pozitie
ros2 topic pub --once /sar/operator std_msgs/String \
  "data: '{\"type\":\"drone\",\"id\":\"d2\",\"action\":\"goto\"}'"

# pauza misiune
ros2 topic pub --once /sar/operator std_msgs/String \
  "data: '{\"type\":\"mission\",\"action\":\"pause\"}'"

# RTH manual (Return to Home)
ros2 topic pub --once /sar/operator std_msgs/String \
  "data: '{\"type\":\"drone\",\"id\":\"d1\",\"action\":\"rth\"}'"
```

## Failsafe baterie
Drona cu baterie < 30% publică automat comanda RTH pe `/sar/operator`. Pragul și topicul sunt configurabile din `sar_plugins/launch/mission_sar.launch.py`.

## Teste
```bash
cd ~/ros2_ws/src/sar_swarm
python3 sil_run.py          # SIL complet (toate scenariile, fără ROS)
```
