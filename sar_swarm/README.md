# sar_swarm

Demonstrator Search & Rescue (SAR) cu un roi de 4 drone autonome (d1-d4) intr-o
lume post-dezastru, cu statie de control la sol (GCS), degradare de retea
injectabila, sonda de latenta si ecran de misiune. In teza este stratul de
APLICATIE: noduri ROS subtiri peste nuclee pure (Python fara ROS), rulate identic
peste mai multe middleware-uri RMW pentru a masura efectul transportului pe
metrici de MISIUNE sub retea degradata.

Pachet "zero-build": NU exista package.xml / setup.py / setup.cfg in arbore.
Nodurile se ruleaza direct cu 'python3 nod.py'; launch-urile cu
'ros2 launch <cale>'. NU exista console_scripts, deci NU se foloseste
'ros2 run sar_swarm ...'. (Confirmat: 'find' nu gaseste niciun fisier de build.)

## Scop

Cuantifica efectul middleware-ului la nivel de misiune SAR sub retea degradata.
Conform docstring-ului din launch/sar_ros.launch.py si din launcher_core.py,
bancul compara explicit rmw_cyclonedds_cpp vs rmw_zenoh_cpp (si FastDDS) pe
ACELASI trafic. README-ul vechi atribuie acest pachet contributiei C1 (comparatie
de middleware sub degradare controlata), ca strat aplicativ peste c1_benchmark.

O echipa de 4 drone exploreaza cooperativ o zona 60x60 m cu ruine (no-fly), fum
(reduce raza senzorului) si victime (din world_config.py: 5 victime, 7 ruine,
3 zone de fum). La pierderea legaturii cu GCS dronele trec autonom prin
comportamente de avarie (LOCAL_EXPLORE -> RETURN_TO_LINK -> LOITER) si tamponeaza
telemetria (store-and-forward) pana la reconectare.

## Arhitectura

Metodologia "nucleu pur -> nod ROS subtire -> SIL" este vizibila in cod:

1. Nuclee pure (fara ROS, fara Tk) -- logica testabila oriunde:
   - sar_core.py (lume, harta, frontiere, A*, fallback),
   - swarm_core.py (cinematica, formatii, failsafe ale roiului),
   - netem_core.py (modelul de degradare a retelei + store-and-forward),
   - operator_core.py (stratul de comanda om-in-bucla),
   - launcher_core.py (logica meniului: RMW x mod x scenariu -> comanda),
   - rf_status_core.py (rezumat RF pentru HMI; singurul cu _selftest() propriu).
2. Noduri ROS subtiri (invelisuri peste nuclee): drone_node.py, gcs_node_ros.py,
   fault_injector_node.py, latency_probe.py, dashboard_node.py.
3. SIL (software-in-the-loop, fara ROS/Gazebo) cu ACELEASI nuclee: sil_run.py,
   orchestrat de run_sil_campaign.py.

drone_node.py si sil_run.py importa swarm_core + sar_core; gcs_node_ros.py importa
sar_core -- adica nodurile si SIL-ul partajeaza acelasi nucleu (verificat prin
grep pe import).

## Fisiere

### Nuclee pure (fara ROS)

| Fisier | Rol (din docstring/cod) |
| --- | --- |
| sar_core.py | Nucleul misiunii SAR: grila de ocupare cu ruine/fum/victime, cartografiere si fuziune cooperativa, alocare de frontiere, drumuri A*, metrici (acoperire, victime, coeziune) si fallback LOCAL_EXPLORE -> RETURN_TO_LINK -> LOITER. |
| swarm_core.py | Logica pura a roiului (cinematica ENU, formatii, cautare, failsafe), separata de transport pentru testabilitate si portabilitate (refolosibila pentru drone reale PX4). Watchdog pe ceas monotonic. |
| netem_core.py | Modelul de degradare a retelei: per legatura latenta+jitter, pierdere, sus/jos (izolare/partitie/ferestre), varfuri de latenta programate, store-and-forward optional si inregistrarea metricilor. Scenariile se incarca din fisiere YAML. |
| operator_core.py | Starea de comanda a operatorului (IDLE/RUNNING/PAUSED/ABORTED; mod drona AUTO/HOLD/GOTO/RTH). handle() traduce comenzile JSON in (drone_id, payload) pe /sar/cmd/{id}. |
| launcher_core.py | Logica pura a meniului de misiune: ce RMW sunt instalate (CycloneDDS/Zenoh/FastDDS) si ce comanda exacta porneste fiecare combinatie middleware x mod x scenariu x optiuni (build_plan). |
| rf_status_core.py | Nucleu pur pentru bara de stare RF a dashboard-ului: din /sar/linkstate (loss, burst_len, interf_db) si /link_adaptive/state -> text + nivel ok/warn/crit + culoare. Are _selftest(). |
| world_config.py | UNICA sursa de adevar a lumii (1 celula = 1 m): WORLD (60x60, 7 ruine, 3 zone de fum, 5 victime), ALT=6.0, SENSE_R=6.0, DRONES d1-d4. Folosit de SIL, noduri, dashboard si gen_world. |

### Noduri ROS 2 (rclpy)

| Fisier | Rol (din docstring/cod) |
| --- | --- |
| drone_node.py | Nodul unei drone SAR (localizare + navigatie + perceptie + comm bridge + health). Acelasi nucleu ca SIL-ul. Mod use_gazebo:=true (odometrie din Gazebo, publica cmd_vel) sau false (cinematica interna). Degradarea se aplica la receptie; telemetria spre GCS cazut intra in store-and-forward. |
| gcs_node_ros.py | Ground Control Station: fuzioneaza hartile dronelor, aloca frontiere (re-planificare la 1 s, doar dronelor vazute recent), confirma harta (ack monoton), publica starea misiunii si scrie ~/sar_data/mission_metrics.csv. Gating-ul legaturilor la receptie. |
| fault_injector_node.py | Injecteaza degradarea retelei din fisierul de scenariu YAML: publica starea legaturilor pe /sar/linkstate; optional (use_tc:=true, iface:=wlan0) aplica tc netem REAL pe interfata, pentru rulari pe masini separate. |
| latency_probe.py | Sonda de latenta/pierdere: GCS trimite ping (2 Hz) catre fiecare drona, pong-ul masoara RTT. Scrie ~/sar_data/rtt_log.csv si publica statistici (RTT mediu/p95, pierdere pe 10 s, per drona) pe /sar/probe/stats. |
| dashboard_node.py | Ecranul cu date al misiunii (Tkinter): harta live (ruine, fum, victime, urme drone, fallback) + panou pe drona (legatura, vechime telemetrie, stare, RTT, pierdere). Surse: /sar/status, /sar/pose/{id}, /sar/probe/stats, /sar/linkstate. Necesita python3-tk. |

### SIL si campanii (fara ROS)

| Fisier | Rol (din docstring/cod) |
| --- | --- |
| sil_run.py | Simulator software-in-the-loop al misiunii SAR multi-drona, fara ROS/Gazebo, cu nuclee identice nodurilor. Ruleaza un scenariu YAML si scrie metrics.csv, summary.json si harta misiunii (PNG). |
| run_sil_campaign.py | Orchestrator de campanie SIL (pur Python): ruleaza bateria de scenarii x N repetitii (seed-uri diferite), aduna metricile in CSV, genereaza figurile de comparatie si ruleaza test_degradation.py ca verdict final. |

### GUI launcher si generare lume

| Fisier | Rol (din docstring/cod) |
| --- | --- |
| sar_launcher.py | Meniul de misiune (Tk, fara ROS in proces): alegi middleware-ul, modul (SIL / ROS pur / ROS+Gazebo), scenariul, optiuni. Construieste comanda prin launcher_core.build_plan, seteaza RMW_IMPLEMENTATION, porneste routerul Zenoh cand e cazul si ruleaza misiunea ca proces-copil. |
| gen_world.py | Genereaza worlds/apocalypse.sdf DIN world_config.py (sursa unica de adevar: ruinele Gazebo = obstacolele A*). Teren 60x60, ruine no-fly, fum, victime, moloz dinamic si 4 drone cu senzori + plugin-uri. Valideaza XML-ul rezultat. |

### Analiza si figuri

| Fisier | Rol (din docstring/cod) |
| --- | --- |
| analyze_disconnect.py | Ce se intampla cand o drona pierde legatura cu GCS: citeste jurnalul per-drona (SIL sau ROS, acelasi format) si produce o cronologie cu 3 panouri (stare de avarie, restanta store-and-forward, distanta) + rezumat in consola. |
| analyze_rmw.py | Figura centrala a tezei: rmw_zenoh vs rmw_cyclonedds pe aceleasi metrici de misiune sub degradare (latenta e2e p50/p95, goodput, timp in fallback). Citeste arborele campaniei si produce figuri + CSV in {OUT}/analysis_rmw/. |
| plot_comparison.py | Figura de comparatie intre scenarii din rezultatele SIL masurate; citeste results/all_summaries.json (cale fixa in cod). |
| analysis/coverage_time_sar.py | Curbele de acoperire in timp, per scenariu SIL (din *_metrics.csv). Iese fig_coverage_time.png. |
| analysis/maps_panel.py | Compune hartile a 3 scenarii intr-un singur panel (implicit baseline / loss_70 / mesh_relay). Iese fig_maps_panel.png. |
| analysis/mission_scenarios.py | Rezultatul de misiune per scenariu (coverage final + victime gasite/total) din *_summary.json. Iese fig_mission_scenarios.png. |

### Teste / validari (rulabile direct)

| Fisier | Rol (din docstring/cod) |
| --- | --- |
| test_sar_core.py | Verificari pe sar_core + netem_core (GridWorld, dezvaluire, acoperire, fallback, canal). |
| test_operator_core.py | Verificari pentru stratul de comanda al operatorului (om-in-bucla). |
| test_launcher_core.py | Verificari pentru logica meniului (rmw_available, build_plan pe combinatii). |
| test_degradation.py | Validare GO/NO-GO: degradarea retelei produce un GRADIENT monoton pe metrici (goodput scade, e2e creste, partitia da timp in fallback > 0). Doar SIL. |
| test_burst_channel.py | Valideaza integrarea rafalelor (rf_interference.BurstProcess) in netem_core: la aceeasi pierdere medie, rafalele dau outage-uri mai lungi. Importa din ../sar_plugins. |

Nota: test_burst_channel.py face 'sys.path.insert(0, ../sar_plugins)' si importa
rf_interference -- dependinta de un pachet vecin (sar_plugins), in afara acestui
pachet.

### Alte fisiere (non-.py)

- launch/sar_ros.launch.py -- misiunea completa FARA Gazebo (cinematica interna).
- launch/sar_gazebo.launch.py -- misiunea completa in Gazebo (lume + bridge-uri).
- scenarios/*.yaml -- scenarii de degradare (baseline, drone_isolation,
  gcs_delay_spike, loss_30, loss_70, mesh_relay, partition_2v2).
- worlds/apocalypse.sdf -- lumea Gazebo generata de gen_world.py.
- config/zenoh_session_config.json5 -- configurare sesiune Zenoh.
- run_all_sar.sh -- re-ruleaza experimentele SAR + C1 (moduri --smoke / complet).
- requirements.txt -- matplotlib, numpy, PyYAML (tkinter din sistem: python3-tk).

## Sintaxe de rulare

Pachet zero-build: nu se ruleaza colcon pentru sar_swarm (nu are package.xml).
Comenzile de mai jos sunt EXTRASE din docstring-uri si din cod.

Selftest offline al nucleului cu _selftest() (rf_status_core.py):

    cd ~/ros2_ws/src/sar_swarm
    python3 rf_status_core.py

SIL pe un scenariu (din docstring sil_run.py; pozitionale: scenariu, apoi
optional '--out <dir>'):

    cd ~/ros2_ws/src/sar_swarm
    python3 sil_run.py scenarios/baseline.yaml
    python3 sil_run.py scenarios/loss_70.yaml --out results/

Campanie SIL completa (argparse din run_sil_campaign.py):

    python3 run_sil_campaign.py [--reps 3] [--scenarios baseline loss_30 ...] \
        [--out ~/sil_campaign] [--seed0 11]
    # numele de scenariu se dau FARA '.yaml' (codul adauga ".yaml" si cauta
    # in scenarios/); implicit: baseline loss_30 loss_70 gcs_delay_spike
    # partition_2v2 drone_isolation (din ALL_SCENARIOS).

Validari / teste (rulate direct cu python3):

    python3 test_sar_core.py
    python3 test_operator_core.py
    python3 test_launcher_core.py
    python3 test_degradation.py [--reps 3] [--out /tmp/degr_results]
    python3 test_burst_channel.py        # cere ../sar_plugins/rf_interference.py

Meniul grafic (necesita python3-tk):

    python3 sar_launcher.py

Generarea lumii Gazebo (scrie worlds/apocalypse.sdf, ruleaza din pachet):

    cd ~/ros2_ws/src/sar_swarm
    python3 gen_world.py

Lansare ROS (zero-build -> 'ros2 launch <cale>', NU 'ros2 launch sar_swarm ...';
forma din docstring-urile launch-urilor):

    # FARA Gazebo:
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp   # sau rmw_zenoh_cpp
    ros2 launch sar_swarm/launch/sar_ros.launch.py scenario:=loss_30.yaml

    # CU Gazebo:
    ros2 launch sar_swarm/launch/sar_gazebo.launch.py scenario:=partition_2v2.yaml

Argumente de launch (DeclareLaunchArgument reali):
- sar_ros.launch.py: autostart (default true), scenario (default baseline.yaml),
  dashboard (default true).
- sar_gazebo.launch.py: autostart (default true), scenario (default baseline.yaml),
  dashboard (default true).

Noduri individuale (rulate direct, fiecare are def main() + __main__):

    python3 fault_injector_node.py
    python3 gcs_node_ros.py
    python3 drone_node.py
    python3 latency_probe.py
    python3 dashboard_node.py

Figuri / analiza (pozitionale / argparse din cod):

    python3 analyze_disconnect.py results/drone_isolation_drone_d2.csv \
        [--down a:b ...] [--out fig.png]   # --down e interval, ex. --down 25:60
    python3 analyze_rmw.py [~/mission_results | --selftest]
    python3 analysis/coverage_time_sar.py <dir_cu_*_metrics.csv>
    python3 analysis/maps_panel.py <dir_cu_harti> [scn1 scn2 scn3]
    python3 analysis/mission_scenarios.py <dir_cu_*_summary.json>
    python3 plot_comparison.py        # citeste results/all_summaries.json

## Parametri si topicuri

Toate mesajele sunt JSON peste std_msgs/String. Parametrii si topicurile de mai
jos sunt extrasi direct din declare_parameter / create_publisher /
create_subscription.

### Parametri ROS (declare_parameter)

- fault_injector_node.py: scenario (default "scenarios/baseline.yaml"),
  use_tc (default False), iface (default "lo").
- drone_node.py: id (default "d1"), x0 (default 3.0), y0 (default 3.0),
  use_gazebo (default False).
- gcs_node_ros.py: autostart (default True).

### Topicuri std_msgs/String (JSON)

- drone_node.py:
  - publica: /sar/telemetry, /sar/probe/pong, /sar/pose/{id};
  - subscrie: /sar/cmd/{id}, /sar/linkstate, /sar/probe/ping, /sar/telemetry;
  - cu use_gazebo: publica geometry_msgs/Twist pe /model/{id}/cmd_vel,
    subscrie nav_msgs/Odometry pe /model/{id}/odometry.
- gcs_node_ros.py:
  - publica: /sar/status, /sar/cmd/{id} (per drona);
  - subscrie: /sar/telemetry, /sar/linkstate, /sar/operator.
- fault_injector_node.py:
  - publica: /sar/linkstate; subscrie: /sar/operator.
- latency_probe.py:
  - publica: /sar/probe/ping, /sar/probe/stats;
  - subscrie: /sar/probe/pong, /sar/linkstate.
- dashboard_node.py:
  - publica: /sar/operator;
  - subscrie: /sar/status, /sar/linkstate, /sar/probe/stats,
    /link_adaptive/state, /sar/pose/{d}.

### Forma mesajelor JSON (vizibila in cod)

- /sar/status (gcs_node_ros.publish_status): {"t", "coverage", "mission",
  "victims", "victims_total", "drones": {id: {"pos", "state", "mode", "age_s",
  "link"}}}.
- /sar/telemetry (drone_node.send_telemetry): {"k":"telemetry", "id", "pos",
  "state", "t", "from", "cells", "victims"}.
- /sar/pose/{id} (drone_node): {"id", "pos", "state"}.
- /sar/probe/ping (latency_probe): {"to", "seq", "t"}.
- /sar/probe/stats (latency_probe.publish_stats): {id: {"rtt_mean_ms",
  "rtt_p95_ms", "loss_10s"}}.
- /sar/linkstate (fault_injector_node): {"scenario", "t", "down", "lat_ms",
  "jit_ms", "loss"}.
- /sar/operator (operator_core, schema din docstring): mesaje cu
  {"type":"mission","action":"start|pause|resume|abort"} sau
  {"type":"drone","id","action":"goto|hold|resume|rth",["cell"]}.
