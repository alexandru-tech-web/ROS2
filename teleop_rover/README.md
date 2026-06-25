# teleop_rover -- teleoperare in bucla inchisa a unui rover terestru peste o legatura degradata (demonstrator de aplicatie pentru comparatia rmw_zenoh vs rmw_cyclonedds, alaturi de C1)

Demonstrator al tezei la nivel de MISIUNE: un rover terestru condus prin retea
(operator-model sau pupitru GCS) sub degradare controlata (latenta, jitter,
pierdere, cadere). Spre deosebire de microbenchmarkul de TRANSPORT din
c1_benchmark (RTT pe mesaje sintetice), aici acelasi middleware (Zenoh sau
CycloneDDS) duce TOT traficul unei misiuni go-to-goal, iar masuratorile sunt
metrici de aplicatie (reusita, timp pana la tinta, eroare de traseu, latenta
end-to-end). Pachetul respecta metodologia de proiect: nucleu pur testabil
(rover_core, nav_core, vision_core, avoidance_core, hw_link, netem_core) -> nod
ROS subtire -> SIL (sil_teleop) -> campanie.

Gasire-cheie a demonstratorului: pe traseu simplu, eroarea transversala (CTE)
NU creste cu degradarea (roverul merge mai lent, deci mai pe linie dreapta); de
aceea jurnalul si analiza folosesc metrici care cresc monoton cu degradarea
(latenta end-to-end, rata de pierdere, opriri de watchdog). Pragul de breakdown
al buclei de teleop apare cand intarzierea feedback-ului devine comparabila cu
dinamica roverului (vezi SIL: la 500 ms / jitter 100 ms / pierdere 10% misiunea
NU se mai inchide in bugetul de timp).

## 1. Scop

Inchide bucla pilot -> comanda -> [legatura degradata] -> rover -> poza ->
[legatura degradata] -> pilot si masoara, sub fiecare RMW si fiecare conditie de
retea, cum se comporta o MISIUNE (nu un mesaj izolat). Roluri:

- arata efectul middleware-ului la nivel de aplicatie (complementar transportului
  din c1_benchmark);
- ofera un al treilea demonstrator al tezei (control in bucla inchisa, nu doar
  telemetrie unidirectionala ca in roi/SAR);
- pastreaza acelasi tipar nucleu-pur testabil ca restul repo-ului, deci e
  reproductibil headless (fara Gazebo) la nivel SIL si de teste.

## 2. Context si loc in arhitectura

Teza compara rmw_zenoh_cpp vs rmw_cyclonedds_cpp sub degradare controlata. Dovada
e pe doua niveluri:

| Strat | Artefact | Ce masoara |
|---|---|---|
| Transport (microbenchmark) | c1_benchmark (pub/sub sintetic) | RTT, jitter, pierdere pe mesaje |
| Aplicatie (acest pachet) | teleop_rover | reusita, timp pana la tinta, CTE, latenta end-to-end pe misiune |

Problema atacata: comanda si feedback-ul circula AMBELE prin legatura degradata,
deci intarzierea se aduna de doua ori si bucla de control se poate destabiliza
peste un prag de latenta -- fenomen absent din telemetria intr-un singur sens.
roverul terestru ofera si termenul de comparatie "dinamica lenta" fata de drona
(o drona la 15 m/s nu "inghite" 400 ms de latenta cum o face un rover la ~1 m/s),
ceea ce motiveaza directia ulterioara spre roi/drone.

Pachetul este ZERO-BUILD: nu exista package.xml / setup.py / setup.cfg, deci NU e
un pachet ament inregistrat. Nodurile se ruleaza din sursa (python3 nod.py), iar
launch-urile prin cale relativa (ros2 launch ./launch/...). Importul nucleelor
merge si standalone si din launch fiindca fiecare nod face
sys.path.insert(0, dirname).

## 3. Arhitectura

### 3.1 Structura nucleu pur -> nod -> SIL

Logica algoritmica sta in module FARA ROS, testate izolat:

| Nucleu pur | Continut | Folosit de |
|---|---|---|
| rover_core.py | DiffDrive (cinematica diferentiala), Course (traseu-slalom + CTE), PilotModel (pure pursuit pe feedback intarziat), SafetyGate (watchdog + comenzi invechite), summarize | operator_node, robot_node, sil_teleop, hw_link, gen_rover_world |
| nav_core.py | SkidSteer4W (4 roti, cu patinare), goto_command (go-to-goal pur), goal_reached | goto_node |
| vision_core.py | detect_blobs (HSV), pixel_to_bearing, ground_range, project_to_world (pinhole + sol-plat, refinare lidar) | detector_node, analyze_perception |
| avoidance_core.py | repulsion_vector, attraction_vector, front_blocked, avoid_command, AvoidParams (potential-fields + VFH) | goto_node (evitare la distanta), robot_node (siguranta locala) |
| hw_link.py | protocol serial NMEA cu checksum XOR (encode/parse), LoopbackRover (HIL software), HwLink | robot_node (use_hardware) |
| netem_core.py | Channel / LinkState: latenta + jitter + pierdere + cadere + store-and-forward (canal determinist cu seed) | sil_teleop |

Peste fiecare nucleu stau noduri ROS subtiri (zero-build), iar sil_teleop ruleaza
bucla completa FARA ROS folosind netem_core drept canal.

### 3.2 Noduri si graficul de topicuri

```
operator_node / goto_node                         Gazebo (teleop_rough.sdf)
  (pilot-model | manual | go-to-goal)               teren mesh + tinte + statie GCS
        |                                                ^    |
        | /teleop/cmd (JSON v,w,t)                       |    | /model/rover/cmd_vel
        v                                                |    v
   link_node  -- /teleop/linkstate -->  robot_node  ---(odom / dynamic_pose)---
   (degradare)                          (gating la receptie + SafetyGate + jurnal)
        ^                                     |
        | /teleop/pose (JSON, intarziat)      | /scan (lidar local, FARA link)
        +-------------------------------------+
                                              v
   gcs_console (PoseStamped /teleop/goal)   detector_node (HSV -> /teleop/target)
```

| Nod | Aboneaza | Publica | Rol |
|---|---|---|---|
| operator_node.py | /teleop/pose, /teleop/linkstate | /teleop/cmd | operator de la distanta: pilot-model (repetabil) sau manual Tk (W/A/S/D) |
| goto_node.py | /teleop/pose, /teleop/linkstate, /scan*, /teleop/target*, /teleop/goal* | /teleop/cmd, /teleop/goal_marker | navigator go-to-goal (operator drop-in), evitare la distanta prin link |
| link_node.py | /teleop/operator | /teleop/linkstate | publica parametrii de degradare (5 Hz), setabili la pornire sau LIVE |
| robot_node.py | /teleop/cmd, /teleop/linkstate, /model/rover/odometry*, dynamic_pose/info*, /scan* | /teleop/pose, /model/rover/cmd_vel* | roverul: gating la receptie + SafetyGate + siguranta locala lidar + jurnal CSV |
| detector_node.py | /camera/image/compressed, /teleop/pose, /scan* | /teleop/target | recunoastere HSV + proiectie in lume (pinhole, refinare lidar) |
| gcs_console.py | /teleop/pose | /teleop/goal (PoseStamped) | pupitru Tk cu harta: click pe harta = tinta roverului |
| fake_camera_pub.py | -- | /camera/image/compressed | camera sintetica pentru a testa detector_node fara Gazebo |

(* = abonari/publicari conditionate de parametri: use_gazebo, use_avoidance,
goal_source, safety_lidar, scan_topic non-gol.)

Gating la receptie: link_node NU intarzie efectiv mesajele; publica starea
legaturii, iar fiecare nod consumator (operator/goto/robot) aplica singur
pierderea (random < loss), caderea (down) si latenta+jitter la RECEPTIE,
amanand mesajul in propriul "inbox". Cheia LINK este "op-rob".

### 3.3 Cele trei (patru) straturi de siguranta pe rover

1. gating la receptie din /teleop/linkstate (pierdere + cadere + latenta): modeleaza
   pierderea reala de comenzi pe link;
2. respingerea comenzilor invechite (STALE_S = 1.0 s la sosire): o comanda care a
   stat prea mult in retea nu mai e relevanta -> ignorata (SafetyGate.on_command);
3. watchdog (WATCHDOG_S = 0.4 s): fara comanda proaspata -> STOP, cu numararea
   tranzitiilor activ->oprit (SafetyGate.output);
4. (optional) siguranta LOCALA pe lidarul de bord (FARA link): front_blocked sub
   d_crit suprascrie comanda cu STOP, indiferent de operator (robot_node,
   safety_lidar:=true). Numara safety_stops.

## 4. Inventar fisiere

| Fisier | Rol | Cum se verifica |
|---|---|---|
| rover_core.py | nucleu pur: DiffDrive, Course, PilotModel, SafetyGate, summarize | test_rover_core.py (19) |
| nav_core.py | nucleu pur: SkidSteer4W, goto_command, goal_reached | test_nav_core.py (11) |
| vision_core.py | nucleu pur: HSV blobs + proiectie pinhole/sol-plat | test_vision_core.py (11) |
| avoidance_core.py | nucleu pur: potential-fields + VFH (atractie + repulsie) | importat de goto_node/robot_node; nu are test dedicat (TODO) |
| hw_link.py | nucleu pur: protocol serial NMEA + HIL loopback | test_hw_link.py (8) |
| netem_core.py | nucleu pur: canal degradat determinist (latenta/jitter/pierdere/cadere/SAF) | folosit de sil_teleop; Channel testat in sar_swarm/test_sar_core.py, niciun test/selftest aici (TODO) |
| operator_node.py | nod ROS: operator pilot-model / manual Tk | ros2 launch / python3 (cere ROS) |
| goto_node.py | nod ROS: navigator go-to-goal (waypoint / object / gcs) + marker | ros2 launch / python3 (cere ROS) |
| link_node.py | nod ROS: publica /teleop/linkstate (5 Hz) | ros2 launch / python3 (cere ROS) |
| robot_node.py | nod ROS: rover + SafetyGate + siguranta locala + jurnal | ros2 launch / python3 (cere ROS) |
| detector_node.py | nod ROS: recunoastere HSV -> /teleop/target | python3 + fake_camera_pub (fara Gazebo) |
| gcs_console.py | nod ROS + Tk: pupitru GCS cu harta (click = tinta) | python3 gcs_console.py --selftest (mapare pixel<->lume) |
| fake_camera_pub.py | nod ROS: camera sintetica pentru testarea detectorului | python3 (cere ROS) |
| sil_teleop.py | misiunea completa in BUCLA INCHISA, FARA ROS (canal netem_core) | python3 sil_teleop.py --lat ... |
| sweep_teleop.py | matura grila latenta x pierdere x actuator (5 seminte/celula) -> figuri | python3 sweep_teleop.py |
| run_rmw_campaign.sh | campanie RMW x conditii x repetari (mod waypoint, fara om) | bash (cere ROS+Gazebo) |
| analyze_campaign.py | agregare campanie -> summary.csv + fig_reusita/fig_timp/fig_cte | python3 analyze_campaign.py --camp ... --goal gx gy |
| analyze_perception.py | compara doua rulari (timp->tinta, dist finala, eroare de localizare) + figura | python3 analyze_perception.py --run ... |
| plot_trace.py | figura traiectoriei dintr-un robot_log.csv real | python3 plot_trace.py <log.csv> |
| gen_rough_world.py | genereaza teleop_rough.sdf + teren mesh texturat (.obj/.mtl/.png) + tinte + statie GCS | python3 gen_rough_world.py (cere numpy+matplotlib) |
| gen_rover_world.py | genereaza teleop_course.sdf (curs plat, porti din rover_core.COURSE) | python3 gen_rover_world.py |
| hil_firmware_reference.ino | referinta firmware Arduino/ESP32 pentru protocolul hw_link | NETESTAT pe hardware (schelet) |
| test_rover_core.py / test_nav_core.py / test_vision_core.py / test_hw_link.py | teste pure (fara ROS) ale nucleelor | python3 test_*.py |
| requirements.txt | dependinte pip (matplotlib, numpy, opencv-python, pyserial, PyYAML) | pip install -r requirements.txt |
| launch/teleop.launch.py | bucla fara Gazebo (cinematica interna): link + robot + operator | ros2 launch ./launch/teleop.launch.py |
| launch/teleop_gazebo.launch.py | bucla pe curs plat in Gazebo (gen_rover_world) | ros2 launch ./launch/teleop_gazebo.launch.py |
| launch/teleop_perception.launch.py | teren accidentat + camera + lidar + detector + goto (rmw la alegere) | ros2 launch ./launch/teleop_perception.launch.py |
| worlds/teleop_course.sdf | lumea plata (generata de gen_rover_world.py) | gz sim |
| worlds/teleop_rough.sdf + teleop_rough_terrain.obj/.mtl/.png | lumea accidentata (generate de gen_rough_world.py) | gz sim |
| DOCUMENTATIE_teleop_rover.md | document tehnic extins (istoric de dezvoltare, learnings) | -- |
| results/ | iesirile rularilor (figuri, summary.csv, robot_log.csv) -- date, nu cod | -- |

Nota privind generatele: teleop_rough_terrain.{obj,mtl,png} si fisierele .sdf sunt
generate de scripturile gen_*; pot intra in .gitignore.

## 5. Date tehnice

### 5.1 Limite si praguri ale roverului (rover_core.py)

| Constanta | Valoare | Unitate | Semnificatie |
|---|---|---|---|
| V_MAX | 1.2 | m/s | viteza liniara maxima |
| W_MAX | 2.2 | rad/s | viteza unghiulara maxima |
| WATCHDOG_S | 0.4 | s | fara comanda proaspata -> STOP |
| STALE_S | 1.0 | s | comenzile mai vechi de atat se ignora la sosire |
| WP_RADIUS | 1.0 | m | punct de traseu atins sub aceasta distanta |
| COURSE | 7 porti slalom | m | (4,0),(8,2.5),(12,-2.5),(16,2.5),(20,-2.5),(24,0),(28,0) |

DiffDrive si SkidSteer4W accepta limite optionale de acceleratie (a_max [m/s^2],
w_acc [rad/s^2]); implicit None = raspuns instantaneu. SkidSteer4W adauga
coeficienti de patinare slip, w_slip in [0,1) (implicit 0 = identic cu DiffDrive).

### 5.2 Parametri ai nodurilor (din declare_parameter)

- link_node: lat_ms (0.0), jit_ms (0.0), loss (0.0), down (False) -- toate cu
  dynamic_typing (accepta 200 si 200.0). LIVE pe /teleop/operator cu
  {"action":"set_all","ms":..,"jit":..,"loss":..,"down":..}.
- robot_node: use_gazebo (False), use_world_pose (True), model_name ("rover"),
  world_name ("teleop_rough"), pose_min_dist (2.0), safety_lidar (True),
  scan_topic ("/scan"), d_crit (0.5), use_hardware (False), port ("loop").
- goto_node: goal_source ("waypoint"; valori: waypoint | object | gcs),
  goal_x (8.0), goal_y (3.0), target_class (""), arrive_r (0.5),
  goal_topic ("/teleop/goal"), frame ("map"), use_avoidance (True),
  scan_topic ("/scan").
- operator_node: mode ("pilot"; valori: pilot | manual).
- detector_node: image_topic (/camera/image/compressed), scan_topic ("" = fara
  refinare), target_class (""), min_area (120), intrinseci camera hfov (1.0472),
  vfov (0.818), cam_h (0.35), pitch (0.2), width (320), height (240).
- gcs_console: goal_topic (/teleop/goal), pose_topic (/teleop/pose), frame ("map"),
  terrain_half (20.0).

Nota: goal_source:=gcs e o valoare valida acceptata de goto_node (in care roverul
sta OPRIT pana primeste prima tinta de la GCS), chiar daca descrierea argumentului
din teleop_perception.launch.py mentioneaza doar "object | waypoint"; argumentul e
pasat verbatim catre nod, deci gcs functioneaza si prin launch.

### 5.3 Parametri de evitare (avoidance_core.py)

| Parametru | Valoare | Unitate | Rol |
|---|---|---|---|
| D_SAFE | 2.5 | m | sub atata un obstacol incepe sa respinga |
| D_CRIT | 0.6 | m | coliziune iminenta -> front_blocked |
| K_REP | 3.0 | -- | castig repulsie |
| K_ATT | 1.0 | -- | castig atractie spre tinta |
| FRONT_CONE | 45 | grade | conul frontal verificat pentru blocaj |
| GOAL_CLEAR_R | 4.0 | m | sub atata de tinta, ignora repulsia (tinta != obstacol) |

GOAL_CLEAR_R rezolva capcana "tinta fizica vazuta ca obstacol": turnul-tinta e un
cilindru, deci lidarul il vede; aproape de tinta repulsia se ignora, altfel roverul
ar orbita in jurul propriului obiectiv.

### 5.4 Topicuri si formate de mesaj

| Topic | Tip | Continut |
|---|---|---|
| /teleop/cmd | std_msgs/String | JSON {v, w, t} |
| /teleop/pose | std_msgs/String | JSON {x, y, th, t, cmd_age, stopped, done, stops} |
| /teleop/linkstate | std_msgs/String | JSON {down:[], lat_ms:{LINK:..}, jit_ms:{..}, loss:{..}} |
| /teleop/operator | std_msgs/String | JSON {action:"set_all", ms, jit, loss, down} (degradare LIVE) |
| /teleop/target | std_msgs/String | JSON {x, y, t, class, conf} |
| /teleop/goal | geometry_msgs/PoseStamped | tinta data de GCS / CLI / RViz |
| /teleop/goal_marker | visualization_msgs/Marker | stalp galben la tinta curenta (RViz) |
| /model/rover/cmd_vel | geometry_msgs/Twist | comanda spre Gazebo (use_gazebo) |
| /model/rover/odometry | nav_msgs/Odometry | odometrie din Gazebo (fallback de poza) |
| /world/<world>/dynamic_pose/info | tf2_msgs/TFMessage | poza-LUME absoluta (Pose_V din Gazebo) |
| /scan | sensor_msgs/LaserScan | lidar (degradat prin link la goto; local la robot) |
| /camera/image/compressed | sensor_msgs/CompressedImage | camera (gz image_bridge) catre detector |

### 5.5 Jurnale produse de robot_node (~/teleop_data/robot_log.csv)

Antet (13 coloane, scris de robot_node.py):
t_s, x, y, cte, cmd_age, fb_age, stopped, e2e_lat, cmd_jitter, cmd_gap, stops,
drop_rate, safety_stops.

- e2e_lat: now_exec - t_emis [ms], latenta reala comanda->executie (link+jitter+coada);
- cmd_jitter: variatia intervalului real intre comenzi executate [ms];
- cmd_gap: timp de la ultima comanda executata [ms] (creste sub pierdere);
- stops: tranzitii activ->oprit (watchdog);
- drop_rate: pierdute / (primite + pierdute), cumulativ;
- safety_stops: override-uri ale lidarului local.

Ceasul: t_emis (goto/operator) si now_exec (robot) sunt time.time() din procese
diferite pe ACEEASI masina -> ceas comun, diferenta valida. Pe hardware separat ar
cere NTP/PTP.

## 6. Sintaxe de pornire

Pachetul e ZERO-BUILD: nu se face colcon build pentru el (nu are package.xml /
setup.py), deci NU exista "ros2 run teleop_rover ...". Nodurile se ruleaza cu
python3, launch-urile cu cale relativa.

### 6.1 Verificari fara ROS (orice masina)

```bash
cd ~/ros2_ws/src/teleop_rover

# nucleele pure (numere reale, vezi sectiunea 7)
python3 test_rover_core.py       # 19 verificari
python3 test_nav_core.py         # 11 verificari
python3 test_vision_core.py      # 11 verificari (cere opencv-python + numpy)
python3 test_hw_link.py          # 8 verificari

# maparea pupitrului GCS (pixel <-> lume), fara Tk
python3 gcs_console.py --selftest

# misiunea completa in BUCLA INCHISA, FARA ROS (canal degradat)
python3 sil_teleop.py --lat 0   --jit 0   --loss 0.0           # ideal
python3 sil_teleop.py --lat 500 --jit 100 --loss 0.1 --plot    # degradat
# sweep complet pe latenta x pierdere x actuator -> results/*.png
python3 sweep_teleop.py
```

### 6.2 Bucla in ROS, fara Gazebo (cinematica interna)

```bash
cd ~/ros2_ws/src/teleop_rover
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp    # sau rmw_zenoh_cpp
ros2 launch ./launch/teleop.launch.py lat:=200 jit:=40 loss:=0.1 mode:=pilot

# degradare LIVE din alt terminal (acelasi RMW):
ros2 topic pub --once /teleop/operator std_msgs/msg/String \
  'data: "{\"action\":\"set_all\",\"ms\":300,\"jit\":50,\"loss\":0.1}"'
```

### 6.3 Bucla in Gazebo (curs plat)

```bash
cd ~/ros2_ws/src/teleop_rover
python3 gen_rover_world.py                       # scrie worlds/teleop_course.sdf
ros2 launch ./launch/teleop_gazebo.launch.py lat:=500 jit:=100 mode:=manual
```

### 6.4 Teren accidentat + camera + lidar + navigare (lantul complet)

```bash
cd ~/ros2_ws/src/teleop_rover
python3 gen_rough_world.py                       # lumea + terenul texturat + statia GCS

# tinta = obiect detectat (camera), sub Cyclone (implicit):
ros2 launch ./launch/teleop_perception.launch.py \
    goal_source:=object target_class:=red lat:=200 jit:=40

# tinta fixa (waypoint), sub Zenoh (porneste si routerul rmw_zenohd):
ros2 launch ./launch/teleop_perception.launch.py rmw:=zenoh \
    goal_source:=waypoint goal_x:=8.0 goal_y:=3.0 lat:=200 jit:=40
```

Pupitrul GCS (alt terminal, ACELASI RMW ca launch-ul) cu goal_source:=gcs:

```bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp          # la fel ca launch-ul
source ~/ros2_ws/install/setup.bash
cd ~/ros2_ws/src/teleop_rover
python3 gcs_console.py                            # click pe harta = tinta roverului
```

Testarea detectorului fara Gazebo:

```bash
python3 fake_camera_pub.py --ros-args -p color:=red -p cx:=170 &
python3 detector_node.py
ros2 topic echo /teleop/target
```

### 6.5 Campania RMW (mod waypoint, fara om in bucla)

```bash
cd ~/ros2_ws/src/teleop_rover
REPS=1 DURATION=70 GOAL_X=8.0 GOAL_Y=3.0 bash run_rmw_campaign.sh   # test rapid
# campania completa N=5:
REPS=5 DURATION=90 GOAL_X=8.0 GOAL_Y=3.0 bash run_rmw_campaign.sh
# (scriptul cheama la final analyze_campaign.py si scoate summary.csv + figuri)
```

Limitari de mediu:
- folositi ZECIMALE pentru parametrii float (goal_x:=8.0, nu 8), altfel
  InvalidParameterTypeException;
- exportati ACEEASI implementare RMW in TOATE terminalele (altfel
  "Waiting for matching subscription");
- la rmw:=zenoh, portul 7447 trebuie liber (pkill -f rmw_zenohd inainte);
- camera/lidar Gazebo cer ogre2/GPU; SIL-ul si testele NU au nevoie de GPU.

## 7. Verificare

Teste pure rulate in acest mediu (toate au trecut):

| Suita | Verificari | Acopera |
|---|---|---|
| test_rover_core.py | 19/19 | cinematica DiffDrive, rampa de acceleratie, Course+CTE, SafetyGate (watchdog + invechite), bucla pilot end-to-end ideala, summarize |
| test_nav_core.py | 11/11 | SkidSteer4W (cu/fara patinare, limite, rampa), goto_command (pivot/decelerare/sosire), bucla SIL pana la tinta |
| test_vision_core.py | 11/11 | detect_blobs HSV (sintetic), filtru de arie, pixel_to_bearing, ground_range, project_to_world (mono + refinare lidar) |
| test_hw_link.py | 8/8 | checksum, roundtrip CMD/POS, fragmentare, respingerea zgomotului/CK gresit, HIL loopback |
| gcs_console.py --selftest | ok | maparea pixel<->lume (round-trip + colturi) |

Smoke SIL (rulat aici): la lat=0/jit=0/loss=0 misiunea se inchide (time_s ~ 29.5 s,
completed=true, stops=0); la lat=500/jit=100/loss=0.1 misiunea NU se inchide in
buget (time_s = 120.0, completed=false, fb_age_mean ~ 0.49 s) -- ilustreaza
breakdown-ul buclei sub feedback invechit.

Nodurile ROS si campania Gazebo cer ROS 2 Jazzy + Gazebo (+ GPU pentru
perceptie) si NU pot fi rulate in acest mediu; sunt descrise prin comenzi, nu prin
cifre inventate. avoidance_core.py si netem_core.py nu au teste dedicate in acest
pachet (TODO: test pur de avoidance cu scanuri sintetice; netem_core e exercitat
indirect prin sil_teleop, iar Channel are test dedicat in
sar_swarm/test_sar_core.py).

## 8. Igiena datelor si reproductibilitate

- Datele brute de campanie NU intra in git (CLAUDE.md sectiunea 5); in repo intra
  doar sumarele (summary.csv) si figurile. Arhivati robot_log.csv per rulare in
  ~/c1_archive/<data>/ sau echivalent.
- Canalul SIL (netem_core.Channel) e determinist cu seed, deci sweep_teleop.py si
  sil_teleop.py sunt reproductibile bit-cu-bit la acelasi seed.
- Mesh-ul si .sdf-urile sunt GENERATE de gen_*; pot fi excluse din git si refacute
  (python3 gen_rough_world.py / gen_rover_world.py).
- Rezultatele din results/ sunt provizorii: campania existenta
  (results/campaign_20260614_215209) este SIL la nivel de N=1 (n=1 in summary.csv)
  -- de inlocuit cu N=5 inainte de orice submisie (SIL, N=1 -- de inlocuit cu N=5).

Corecturi de onestitate fata de documentatia anterioara:
- test_rover_core.py are 19 verificari (nu 17, cum apare in comentariul stale din
  nav_core.py si in numararile vechi);
- analyze_campaign.py, in versiunea CURENTA din sursa, produce DOAR summary.csv (8
  coloane: rmw, conditie, n, reusita, timp_med_s, timp_std_s, cte_med_m, cte_max_m)
  si figurile fig_reusita.png / fig_timp.png / fig_cte.png. Coloanele extinse
  (e2e_lat, jitter, gap, opriri, drop_rate, opriri_siguranta) si figurile
  fig_e2e_lat / fig_jitter / fig_opriri / fig_opriri_siguranta din
  results/campaign_20260614_215209/ au fost produse de o versiune ANTERIOARA a
  scriptului; robot_log.csv inca LOGHEAZA aceste coloane brute (robot_node scrie 13
  coloane), dar analizorul curent nu le agrega (TODO: a re-include agregarea
  metricilor end-to-end in analyze_campaign.py daca se doreste paritate cu
  DOCUMENTATIE_teleop_rover.md sectiunea 6.1).
