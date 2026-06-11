# Teleop Rover — teleoperarea în timp real a unui rover prin legătură degradată

**A doua aplicație de teză, complementară roiului SAR: acolo se măsoară controlul *supervizor* (comenzi discrete: du-te, stai); aici se măsoară cazul dur al „controlului la distanță în timp real" — bucla închisă om→robot→om care trece prin rețeaua degradată DE DOUĂ ORI (comanda la dus, feedback-ul la întors). Metricile sunt de APLICAȚIE: eroarea de urmărire, timpul de parcurs, opririle de siguranță — adică „ce înseamnă 200 ms p95 pentru operator", etajul care lipsea peste benchmarkul de transport (C1).**

![ROS 2](https://img.shields.io/badge/ROS_2-Jazzy-blue) ![Gazebo](https://img.shields.io/badge/Gazebo-Harmonic-orange) ![Teste](https://img.shields.io/badge/teste-25%20trec-green)

## Bucla, pe scurt

```
operator (pilot-model SAU om la tastatură)
   │  comenzi v,ω @ 20 Hz ──▶ [legătura degradată: latență+jitter+pierdere+tăiere]
   │                                  │
   │                                  ▼
   │                        STRATUL DE SIGURANȚĂ al robotului:
   │                        watchdog 0.4 s + respinge comenzile > 1 s vechime
   │                                  │
   ▼                                  ▼
poza ◀── [aceeași legătură degradată] ◀── rover diferențial (intern sau Gazebo)
```

Cheia experimentală: pilotul decide pe **ultima poză care a supraviețuit legăturii** (veche, posibil lipsă) — exact ce vede un operator real. „Operatorul" implicit e un **pilot-model** (pure pursuit), ca rulările să fie perfect repetabile: aceleași N rulări pe fiecare condiție de rețea → curbe comparabile. Modul `manual` (W/A/S/D, fereastră cu traseul + vârstele) îți dă senzația fizică a 500 ms de latență.

## Rezultate măsurate (SIL: 5 rulări/condiție, jitter = 20% din latență)

| Latență (un sens) | pierdere 0% | pierdere 30% |
|---|---|---|
| 0 ms | 29.5 s, CTE p95 0.85 m, 0 opriri | 29.6 s, 0.84 m, 0 opriri |
| 100 ms | 30.2 s, 0.78 m, 0 | 30.7 s, 0.77 m, 0 |
| 200 ms | 34.1 s, 0.79 m, 0 | 35.9 s, 0.83 m, 0 |
| 500 ms | **timeout 120 s**, 1.14 m, 0 | timeout, 1.14 m, 0.8 opriri |
| 1000 ms | timeout, **12.1 m**, 8.2 opriri | timeout, 12.1 m, **35.6 opriri** |

Citirea de teză (figura `results/teleop_sweep.png`): bucla e **stabilă până la ~200 ms** (doar timpul crește ușor), **se rupe între 200 și 500 ms** (pilotul orbitează porțile pe date vechi — misiunea nu se mai termină), iar la **1000 ms** comenzile încalcă pragul de vechime → stratul de siguranță refuză mișcarea (furtună de opriri, amplificată de pierdere: 8 → 35 opriri/rulare). Sistemul **eșuează în siguranță**, nu în instabilitate necontrolată. Pragul de rupere e condus de latență, nu de pierdere — complementar concluziei din SAR (acolo latența de 2 s durea mai mult ca pierderea de 30%).

## Structura

```text
teleop_rover/
├── rover_core.py        nucleul PUR: cinematică, traseu+CTE, pilot, SafetyGate
├── netem_core.py        canalul degradat (copie identică, testată, din sar_swarm)
├── sil_teleop.py        bucla închisă fără ROS + figura unei rulări (--plot)
├── sweep_teleop.py      EXPERIMENTUL: grila latență×pierdere → sweep.csv + figura
├── plot_trace.py        figura unei rulări REALE din jurnalul robotului
├── test_rover_core.py   17 verificări (cinematică, CTE, watchdog, pilot end-to-end)
├── robot_node.py        roverul ROS: gating la recepție + SafetyGate + jurnal-traseu
├── operator_node.py     operatorul ROS: pilot (repetabil) sau manual (fereastră W/A/S/D)
├── link_node.py         legătura: /teleop/linkstate din parametri sau LIVE
├── gen_rover_world.py   lumea Gazebo DIN rover_core (porțile = traseul CTE-ului)
├── launch/teleop.launch.py          fără Gazebo (banc RMW pe metrici de aplicație)
├── launch/teleop_gazebo.launch.py   cu roverul în Gazebo (plugin DiffDrive)
└── worlds/teleop_course.sdf         generată (XML validat)
```

## Rulare

```bash
cd ~/ros2_ws/src/teleop_rover

# 0) verificările + experimentul complet, FĂRĂ ROS (oriunde):
python3 test_rover_core.py
python3 sil_teleop.py --lat 200 --jit 40 --loss 0.1 --plot
python3 sweep_teleop.py            # ~75 rulări → results/teleop_sweep.png

# 1) ROS pur — pilotul-model prin legătura degradată:
source /opt/ros/jazzy/setup.bash
ros2 launch ./launch/teleop.launch.py lat:=200 jit:=40 loss:=0.1 mode:=pilot
#   la final: "TRASEU TERMINAT in ..."; apoi figura rulării reale:
python3 plot_trace.py ~/teleop_data/robot_log.csv

# 2) TU la manșă, cu 500 ms de latență (fereastra W/A/S/D):
ros2 launch ./launch/teleop.launch.py lat:=500 jit:=100 mode:=manual

# 3) același lucru cu roverul în Gazebo:
python3 gen_rover_world.py
ros2 launch ./launch/teleop_gazebo.launch.py lat:=200 mode:=manual

# schimbarea legăturii ÎN TIMPUL rulării:
ros2 topic pub --once /teleop/operator std_msgs/msg/String \
  "{data: '{\"action\": \"set_all\", \"ms\": 800, \"loss\": 0.3}'}"
```

**Comparația RMW pe metrici de aplicație** (etajul nou peste C1): aceeași comandă de la punctul 1, rulată o dată cu `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` și o dată cu `rmw_zenoh_cpp` (+ `ros2 run rmw_zenoh_cpp rmw_zenohd` în alt terminal); compari `robot_log.csv` între rulări. Pe mașini separate, înlocuiești `link_node` cu **tc netem real** pe interfață — nodurile nu se schimbă.

## Stratul de siguranță (măsurabil, nu doar declarat)

`SafetyGate` (în `rover_core.py`, 6 teste dedicate): robotul **se oprește** dacă n-a primit nicio comandă de 0.4 s (watchdog — opririle sunt numărate și apar în jurnale/figuri) și **ignoră** orice comandă mai veche de 1 s la sosire (o comandă de virare emisă acum 2 secunde e periculoasă, nu utilă). La 1000 ms latență acest strat e cel care transformă instabilitatea în imobilitate sigură — vizibil în panoul 3 al figurii de măturare.

## Hardware-in-the-loop (puntea spre robotul fizic) — NOU

Al treilea backend al roverului, cu **stratul de siguranță rămas în amonte** (pe fir nu pleacă niciodată o comandă veche sau orfană):

```bash
# HIL FĂRĂ hardware (MCU software pe loopback) — totul identic, zero fire:
ros2 launch ./launch/teleop.launch.py lat:=200 mode:=pilot &
# ...dar cu robotul pe puntea hardware:
python3 robot_node.py --ros-args -p use_hardware:=true -p port:=loop

# hardware REAL (ESP32/Arduino cu hil_firmware_reference.ino, pyserial instalat):
python3 robot_node.py --ros-args -p use_hardware:=true -p port:=/dev/ttyUSB0
```

Protocolul (`hw_link.py`, **8 teste**: sume de control, fragmentare, zgomot, buclă loopback): `$CMD,v,w*CK` / `$POS,x,y,th,seq*CK` — lizibil pe sârmă, verificabil cu un logic analyzer. `hil_firmware_reference.ino` e scheletul de microcontroler (cu watchdog propriu de 400 ms — apărare în adâncime); dead-reckoning-ul se înlocuiește cu encodere. Pasul de teză: **același sweep, pe robot fizic, prin tc netem real** — „control la distanță în timp real" demonstrat pe hardware.

## Percepție + navigare go-to-goal pe teren accidentat, sub Zenoh — NOU

Etajul de **autonomie sub middleware degradat**: un rover cu **4 roți skid-steer** pe **teren accidentat** (heightmap procedural) în Gazebo, cu **cameră** + **recunoaștere de obiecte (OpenCV clasic, HSV)**, care **navighează singur la o coordonată** — fie un waypoint dat, fie coordonata obiectului recunoscut — rulabil sub `rmw_zenoh_cpp` vs `rmw_cyclonedds_cpp`. Cheia: navigatorul publică pe `/teleop/cmd` exact ca pilotul, deci e un **operator drop-in** și moștenește legătura degradată + SafetyGate + jurnalul + comutarea RMW.

```
camera ─▶ detector_node (HSV blobs + proiecție pinhole/sol-plat, refinare lidar)
            └─▶ /teleop/target (x,y în lume) ─▶ goto_node (go-to-goal)
                                                   └─▶ /teleop/cmd ─▶ [link] ─▶ SafetyGate ─▶ rover 4 roți (Gazebo)
```

**Nuclee PURE noi (testate, fără ROS/Gazebo):**
- `nav_core.py` — `SkidSteer4W` (cinematică 4 roți cu coeficienți de patinare; `slip=0` ⇒ identic cu `DiffDrive`) + `goto_command(x,y,th,gx,gy)` (pure-pursuit „turn-then-drive" cu rază de sosire). `test_nav_core.py`: **11 verificări** (incl. SIL în buclă închisă până la țintă).
- `vision_core.py` — `detect_blobs` (HSV), `pixel_to_bearing`, `ground_range`, `project_to_world` (pinhole + sol-plat, refinare lidar). `test_vision_core.py`: **11 verificări** pe imagini sintetice.

**Lume generată din config:** `python3 gen_rough_world.py` → `worlds/teleop_rough.sdf` + heightmap PNG, validat `gz sdf -k`. Capcane heightmap respectate: imagine `2^k+1` (129×129), `<uri>` cale **absolută `file://`**, heightmap în **collision ȘI visual**, `Zscale` mic (1 m) ca skid-steer-ul să-l urce, motor `ogre2` + plugin `Sensors` pentru cameră/lidar. Tintele colorate din `OBJECTS` sunt **adevărul-teren** pentru analizor.

**Rulare (Gazebo):**
```bash
python3 gen_rough_world.py
ros2 launch ./launch/teleop_perception.launch.py rmw:=zenoh \
    goal_source:=object target_class:=red lat:=200 jit:=40
# tinta fixa, pe Cyclone:
ros2 launch ./launch/teleop_perception.launch.py rmw:=cyclone \
    goal_source:=waypoint goal_x:=8 goal_y:=3
# metricile (timp->tinta, distanta finala, eroare de localizare) Zenoh vs Cyclone:
python3 analyze_perception.py --goal 8 3 \
    --run cyclone ~/teleop_data_cyclone --run zenoh ~/teleop_data_zenoh
```

**Verificare FĂRĂ Gazebo (lanțul percepție+nav, pe CPU):**
```bash
python3 test_nav_core.py && python3 test_vision_core.py        # nuclee pure
python3 fake_camera_pub.py --ros-args -p color:=red &          # camera sintetica
python3 detector_node.py                                       # -> /teleop/target + detections.csv
# go-to-goal end-to-end pe cinematica interna (proprietatea drop-in-operator):
python3 link_node.py & python3 robot_node.py &
python3 goto_node.py --ros-args -p goal_source:=waypoint -p goal_x:=10 -p goal_y:=4
```

**Limite oneste:** proiecția monoculară presupune **sol-plat** — pe heightmap ipoteza e falsă, eroarea de range crește cu panta; de aceea există refinarea opțională cu **lidar** (`scan_topic:=/scan`). La orizont range-ul diverge (`ground_range` întoarce `None`). Camera/gpu_lidar cer **ogre2/GPU**, deci randarea senzorilor și bucla obiect→țintă în Gazebo sunt „prima rulare la tine".

**În plus — îmbunătățire la sweep:** `sweep_teleop.py` mătură acum și **regimul de actuator** (ideal vs. limite de accelerație realiste, `results/teleop_sweep_accel.png`): actuatorul realist mută pragul de rupere (la 500 ms, CTE p95 ≈ 2.9 m vs 1.1 m ideal) — exact pasul cerut în roadmap.

## Onestitate

Nucleul, bucla SIL, măturarea (75 de rulări), analizorul și figurile au **rulat aici** (17 teste trec; cifrele din tabel sunt măsurate). Nodurile ROS, launch-urile și lumea Gazebo sunt verificate sintactic + XML, pe aceleași tipare deja confirmate funcționale la `sar_swarm` — prima rulare e la tine; jurnalul-traseu are exact formatul SIL, deci `plot_trace.py` merge identic pe ambele.

## Legătura cu restul ecosistemului

- `netem_core.py` e aceeași piesă testată din `sar_swarm` (sursă unică de comportament al canalului);
- modelul „nucleu pur + gating la recepție + jurnal local + analizor" e cel validat la SAR;
- același tipar se altoiește direct pe **tele-reabilitare** (sistemul de recuperare): `/exercise_cmd` prin aceeași legătură + SafetyGate pe controlerul de exerciții — direcția următoare naturală.

## Licență

Apache-2.0.
