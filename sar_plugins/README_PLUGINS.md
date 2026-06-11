# sar_plugins — etajul de misiune si teleop avansat (Zenoh/ROS2/SAR)

Plugin-uri peste cele doua sisteme existente (roiul `sar_swarm` + roverul
`teleop_rover`), pe principiul tezei: **logica pura testata** (55/55) →
**noduri ROS2 subtiri** → **strat Gazebo optional**. Nimic de aici nu
modifica pachetele existente: integrarea e exclusiv prin topicuri si
remapari. Versiunea curenta e adaptata la generatia noua a roiului
(namespace `/sar/*`, failsafe energetic legat de comanda reala `rth`).

## Pornire rapida — trei cai

    # 1) FARA ROS (orice masina): verificare + demo cu figuri
    python3 test_plugins.py          # 55/55
    python3 demo_plugins_sim.py      # demo_*.png + bilant misiune

    # 2) ROIUL (sar_swarm pornit in alt terminal):
    ros2 launch ~/ros2_ws/src/sar_plugins/nodes/mission_sar.launch.py \
        profile:=urban_rubble seed:=42

    # 3) ROVERUL (Gazebo + teleop pornite; robotul cu remaparea cmd_safe):
    ros2 launch ~/ros2_ws/src/sar_plugins/nodes/teleop_addons.launch.py

---

## FISELE APLICATIILOR
Conventie: **persistent** = ruleaza pana il opresti (terminal separat sau
in launch); **one-shot** = ruleaza si iese, nu tine terminal ocupat.
Toate nodurile vorbesc JSON pe std_msgs/String. CSV-urile merg in
`~/sar_data/`.

### nodes/radio_link_node.py — linkul radio dependent de distanta
- **Ce face:** transforma pozitia fiecarei drone (fata de GCS) in stare de
  legatura {ms, jit, loss, down} dupa modelul log-distance (profile:
  `open_field`, `urban_rubble`, `forest`). Inlocuieste scenariile statice
  cu degradare FIZIC plauzibila: dronele departate au legatura proasta.
- **Pornire:**
      python3 nodes/radio_link_node.py --ros-args \
        -p pose_topic:=/sar/telemetry -p linkstate_topic:=/sar/linkstate \
        -p profile:=urban_rubble -p seed:=42
- **Terminal separat:** DA (persistent). De obicei vine din mission_sar.launch.
- **In → Out:** /sar/telemetry → /sar/linkstate (agregat {id:{...}});
  pentru o singura tinta + `flat_compat:=true` publica schema plata
  compatibila /teleop/linkstate.
- **Verificare:** `ros2 topic echo /sar/linkstate --once`
- **ATENTIE:** /sar/linkstate trebuie sa aiba UN SINGUR publisher.
  Acest nod e ALTERNATIVA la fault_injector_node din sar_swarm — porneste
  ori unul, ori celalalt, niciodata ambele.

### nodes/coverage_node.py — acoperirea ariei
- **Ce face:** grila de acoperire din pozele dronelor; procent + jaloanele
  25/50/75/90/95/99% cu timpul atingerii. Metrica principala pentru A3.
- **Pornire:**
      python3 nodes/coverage_node.py --ros-args \
        -p pose_topic:=/sar/telemetry -p sensor_r:=6.0 \
        -p xmin:=-5.0 -p xmax:=65.0 -p ymin:=-5.0 -p ymax:=65.0
- **Terminal separat:** DA (persistent; in launch).
- **In → Out:** /sar/telemetry → /mission/coverage (1 Hz) + coverage.csv
- **Verificare:** `ros2 topic echo /mission/coverage --once`

### nodes/victim_node.py — victime si detectie
- **Ce face:** plaseaza N victime reproducibil (seed, separare minima);
  detectie probabilistica Poisson cand o drona e in raza senzorului.
  Publica evenimente + pozitiile statice (latched, pentru dashboard).
- **Pornire:**
      python3 nodes/victim_node.py --ros-args \
        -p pose_topic:=/sar/telemetry -p n:=6 -p seed:=42 -p sensor_r:=6.0 \
        -p xmin:=0.0 -p xmax:=60.0 -p ymin:=0.0 -p ymax:=60.0
- **Terminal separat:** DA (persistent; in launch).
- **In → Out:** /sar/telemetry → /mission/victims (evenimente),
  /mission/victims_static (latched) + victims.csv
- **Verificare:** `ros2 topic echo /mission/victims_static --once`

### nodes/battery_node.py — baterie + failsafe energetic REAL
- **Ce face:** integreaza consumul P = P_hover + k_v*|v| din pozele
  succesive; praguri RTL (static 30% + dinamic dupa distanta de casa) si
  LAND (10%). La tranzitie publica O comanda pe topicul de failsafe —
  in configuratia curenta, comanda `rth` pe care roiul o INTELEGE:
  drona cu baterie mica pleaca singura acasa.
- **Pornire:**
      python3 nodes/battery_node.py --ros-args \
        -p pose_topic:=/sar/telemetry -p state_topic:=/sar/battery \
        -p failsafe_cmd_topic:=/sar/operator \
        -p 'failsafe_template:={"type":"drone","id":"%ID%","action":"rth"}'
- **Terminal separat:** DA (persistent; in launch).
- **In → Out:** /sar/telemetry → /sar/battery (1 Hz), /sar/operator
  (doar la tranzitii) + battery.csv
- **Verificare:** `ros2 topic echo /sar/battery --once`; failsafe-ul se
  vede in dashboard cand o drona intoarce spre casa sub 30%.

### nodes/obstacle_guard_node.py — garda lidar (rover)
- **Ce face:** PROXY de comanda: citeste /teleop/cmd + /scan, taie
  inaintarea sub d_stop (0.6 m), franeaza progresiv intre d_stop si
  d_slow (1.5 m), histerezis la eliberare; rotatia/mersul inapoi raman
  permise. Robotul asculta IESIREA filtrata.
- **Pornire:**
      python3 nodes/obstacle_guard_node.py --ros-args -p msg:=json
- **Terminal separat:** DA (persistent; vine din teleop_addons.launch).
- **In → Out:** /teleop/cmd + /scan → /teleop/cmd_safe + /teleop/guard (5 Hz)
- **CONDITIE:** robot_node trebuie pornit cu remaparea
  `-r /teleop/cmd:=/teleop/cmd_safe` (o singura schimbare, in launch-ul tau).
- **Verificare:** `ros2 topic echo /teleop/guard --once` (vezi distanta
  minima frontala si daca blocheaza).

### nodes/predictive_display_node.py — afisaj predictiv (operator)
- **Ce face:** la operator, prezice poza CURENTA a roverului din ultima
  poza primita + istoricul comenzilor (dead-reckoning pe arc), compensand
  latenta. Logheaza eroarea predictiei vs naiv — METRICA articolului A2.
- **Pornire:**
      python3 nodes/predictive_display_node.py
- **Terminal separat:** DA (persistent; in teleop_addons.launch).
- **In → Out:** /teleop/pose + /teleop/cmd → /teleop/pose_pred (20 Hz)
  + predict.csv (err_pred vs err_naiv la fiecare poza noua)
- **Verificare:** `ros2 topic echo /teleop/pose_pred --once`

### nodes/video_link_node.py — canal video degradat
- **Ce face:** trece CompressedImage prin canalul degradat (intarziere/
  jitter/pierdere/cadere din linkstate live); publica statistici
  in_fps/out_fps/age_ms. Demonstreaza efectul retelei pe fluxul video.
- **Pornire:**
      python3 nodes/video_link_node.py --ros-args \
        -p in_topic:=/camera/image/compressed -p out_topic:=/teleop/video
- **Terminal separat:** DA (persistent; in teleop_addons.launch).
- **In → Out:** camera + linkstate → /teleop/video + /teleop/video_stats (1 Hz)
- **Verificare:** `ros2 topic echo /teleop/video_stats --once`

### nodes/quad_adapter_node.py — adaptor multicopter (OPTIONAL)
- **Ce face:** traduce comenzile JSON ale roiului in Twist pentru lumea
  oficiala Gazebo `multicopter_velocity_control.sdf` (fizica reala de
  cvadricopter). NU e necesar generatiei curente: drone_node publica
  deja /model/{id}/cmd_vel cand use_gz e activ. Pastrat pentru pasul
  spre fizica de multicopter / PX4.
- **Pornire:** `python3 nodes/quad_adapter_node.py` (persistent)

### Launch-uri (nodes/)
- **mission_sar.launch.py** — CEL CURENT: radio_link + coverage + victims
  + battery pe /sar/*, failsafe pe rth. Un singur terminal pentru tot etajul.
      ros2 launch ~/ros2_ws/src/sar_plugins/nodes/mission_sar.launch.py \
          profile:=urban_rubble seed:=42 n_victims:=6 sensor_r:=6.0
- **teleop_addons.launch.py** — garda + predictiv + video pentru rover.
- **mission_plugins.launch.py** — varianta veche pe /swarm/* (pentru
  generatia drone_swarm de pe Desktop); NU o folosi cu sar_swarm.

### gz/ — stratul Gazebo (toate one-shot sau fragmente)
- **patch_world_sensors.py** (one-shot, nu tine terminal):
      python3 gz/patch_world_sensors.py worlds/teleop_course.sdf \
          worlds/teleop_sensors.sdf --model rover --link chassis --lidar --imu
  Idempotent: rulat de doua ori nu dubleaza nimic.
- **bridge_rover.yaml / bridge_swarm.yaml** — pentru ros_gz_bridge
  (terminal separat, persistent):
      ros2 run ros_gz_bridge parameter_bridge --ros-args \
          -p config_file:=$HOME/ros2_ws/src/sar_plugins/gz/bridge_rover.yaml
- **battery_plugin.sdf.xml / wind_world.sdf.xml** — fragmente de lipit
  manual in SDF (baterie liniara Gazebo; vant). Instructiuni in fisiere.

### tools/
- **run_experiment.sh** (terminal separat, persistent cat inregistreaza):
      ./tools/run_experiment.sh <scenariu> <rmw> [durata_s]
      ./tools/run_experiment.sh baseline rmw_zenoh_cpp 120
  Exporta RMW, porneste rmw_zenohd daca e cazul, scrie manifest JSON si
  inregistreaza cu ros2 bag topicurile /teleop/* /sar/* /mission/*.
  NODURILE le pornesti in alte terminale, cu ACELASI RMW exportat.
- **manifest.py** (one-shot): manifestul reproducibilitatii unei rulari.

---

## Matricea de terminale

**Workflow ROI (SAR cu etaj de misiune):**
| T | Comanda | Rol |
|---|---|---|
| T1 | `cd ~/ros2_ws/src/sar_swarm && python3 sar_launcher.py` (vezi README-ul lui pentru argumente/scenarii) | roiul insusi |
| T2 | `ros2 launch .../mission_sar.launch.py profile:=urban_rubble seed:=42` | etajul de misiune |
| T3 (opt) | `./tools/run_experiment.sh <scenariu> <rmw> 300` | inregistrare bag + manifest |
In T1 NU porni fault_injector daca T2 ruleaza radio_link (un singur
publisher pe /sar/linkstate).

**Workflow ROVER (Gazebo cu senzori):**
| T | Comanda | Rol |
|---|---|---|
| T1 | `gz sim -r worlds/teleop_sensors.sdf` | simulatorul |
| T2 | `ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=.../bridge_rover.yaml` | puntea gz↔ROS |
| T3 | `ros2 launch teleop_rover/launch/teleop_gazebo.launch.py` (robot_node cu `-r /teleop/cmd:=/teleop/cmd_safe`) | teleoperarea |
| T4 | `ros2 launch .../teleop_addons.launch.py` | garda+predictiv+video |
| T5 (opt) | `./tools/run_experiment.sh ...` | inregistrare |

**REGULA C1:** in timpul campaniei de benchmark NU rulezi NIMIC din cele
de mai sus — masuratorile se otravesc. Intai campania, apoi joaca.

---

## Schemele JSON (std_msgs/String)
- linkstate plat: `{"ms":120,"jit":40,"loss":0.15,"down":false}`
- linkstate agregat: `{"d1":{...},"d2":{...}}` (+ diagnostic snr,rssi,d)
- /mission/coverage: `{"t":..,"pct":..,"cells_covered":..,"cells_total":..,"milestones":{"25":t,...}}`
- eveniment victima: `{"victim":i,"t":..,"by":"d2","x":..,"y":..}`
- /sar/battery: `{"d1":{"soc":0.42,"state":"NORMAL","used_wh":..},...}`
- failsafe emis: `{"type":"drone","id":"d3","action":"rth"}` (schema operator_core)
- /teleop/pose_pred: `{"t":..,"x":..,"y":..,"th":..,"age":..,"extrap":bool}`

## Datele si figurile
Toate CSV-urile in `~/sar_data/` (acelasi format ca restul proiectului):
coverage.csv → curba acoperirii; victims.csv → timpii detectiei;
battery.csv → SOC + momentele RTL; predict.csv → castigul predictiei (A2).
Bag-urile + manifestele: `~/sar_data/bags/<scenariu>_<rmw>_<timestamp>/`.

## [DE COMPLETAT DUPA SIMULARE]
Aici intra, dupa primele rulari pe masina reala: pragurile masurate
(distanta la care linkul cade pe fiecare profil), timpii reali 25/50/90%
acoperire, momentul primului rth declansat de baterie si comparatia
rmw_zenoh vs rmw_cyclonedds pe aceleasi metrici.
