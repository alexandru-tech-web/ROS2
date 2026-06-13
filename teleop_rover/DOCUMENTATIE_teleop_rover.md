# teleop_rover + GCS - documentatie tehnica detaliata

Demonstrator de **teleoperare a unui rover terestru peste o legatura de retea
degradata**, cu pupitru de operator (GCS), perceptie si navigare go-to-goal, in
ROS 2 Jazzy + Gazebo Harmonic. Rolul in teza: stratul **aplicativ** al comparatiei
`rmw_zenoh` vs `rmw_cyclonedds` - masoara efectul middleware-ului pe metrici de
MISIUNE (eroare de traseu, timp pana la tinta, reusita), complementar
microbenchmark-ului de TRANSPORT din `c1_benchmark` (latenta/jitter/pierdere pe
mesaje sintetice).

Pachet "zero-build": nodurile se ruleaza din sursa (`python3 nod.py`), launch-urile
prin cale relativa (`ros2 launch ./launch/...`).

---

## 1. Ideea si bucla completa

Operatorul (GCS) alege un punct pe harta -> comanda calatoreste prin legatura
degradata -> roverul navigheaza autonom spre punct, cu poarta de siguranta si
jurnal. Acelasi RMW (Zenoh sau Cyclone) duce tot traficul, deci putem masura cum
se comporta misiunea sub fiecare middleware si sub diferite grade de degradare.

```
GCS (gcs_console.py)                         Gazebo (teleop_rough.sdf)
  click pe harta                               teren mesh texturat + tinte + statia GCS
      |                                              ^   |
      | PoseStamped /teleop/goal                     |   | /model/rover/cmd_vel
      v                                              |   v
  goto_node  --/teleop/cmd-->  link_node  --(intarziat)-->  robot_node  --> Gazebo
  (operator)                   (lat/jit/loss)               (SafetyGate, jurnal)
      ^                              |                            |
      |   /teleop/pose (intarziat)   |  /teleop/linkstate         | /scan, /camera/image
      +------------------------------+                            v
                                                          detector_node (HSV -> /teleop/target)
```

`goto_node` este OPERATORUL drop-in: vede roverul doar prin pozele care
supravietuiesc legaturii si trimite comenzi pe `/teleop/cmd` exact ca un pilot
uman. Asa, comenzile trec prin link + SafetyGate + RMW NESCHIMBAT, si masuram
navigarea autonoma sub middleware degradat.

---

## 2. Lumea (gen_rough_world.py)

Genereaza `worlds/teleop_rough.sdf` + un teren MESH TEXTURAT din config.

| Element | Detaliu |
|---|---|
| Teren | mesh `.obj` (101x101 vertecsi, ~20000 triunghiuri, 40x40 m, amplitudine `TERR_Z=0.8` m), zgomot fractal cu disc central aplatizat (zona de pornire stabila) |
| Culoare | textura PNG din colormap-ul `terrain` (albastru jos -> verde -> galben -> maro -> alb), mapata UV; legata prin `.mtl` (`map_Kd`) |
| Tinte | 3 cilindri colorati (rosu 8,3 / verde -6,5 / albastru 5,-7), asezati pe teren - adevarul-teren pentru perceptie |
| Statia GCS | model static `gcs_station` (container + catarg + varf rosu) la coltul (-16,-16), pe teren |
| Rover | sasiu cutie + 4 roti skid-steer (`gz-sim-diff-drive-system`, 2 stanga / 2 dreapta), camera + gpu_lidar |

DE CE MESH si nu `<heightmap>`: dartsim nu face coliziune din heightmap (roverul ar
cadea prin teren) si shaderul de heightmap ogre2 crapa pe unele GPU-uri. Mesh-ul
trimesh rezolva ambele.

Rulare: `python3 gen_rough_world.py` (cere numpy + matplotlib). Scrie 3 fisiere in
`worlds/`: `teleop_rough_terrain.obj`, `.mtl`, `.png` - tin impreuna; sunt generate,
deci se pot pune in `.gitignore`.

Reglaj: `TERR_Z` mai mare = mai accidentat dar mai greu de condus (roti 0.12 m);
daca roverul se impotmoleste, scade spre 0.5. Culoarea face mult din impresia de
teren dur, deci amplitudinea poate ramane moderata.

---

## 3. Nodurile

| Nod | Rol | Interfata cheie |
|---|---|---|
| `operator_node.py` | operatorul (pilot automat repetabil sau manual Tk W/A/S/D) | param `mode`; pub `/teleop/cmd` 20 Hz |
| `link_node.py` | legatura degradata | params `lat_ms`, `jit_ms`, `loss`; intarzie ambele sensuri; pub `/teleop/linkstate` (format multi-link `{down:[], lat_ms:{...}, jit_ms, loss}`) |
| `robot_node.py` | robotul + poarta de siguranta | sub `/teleop/cmd` filtrat; SafetyGate (watchdog 0.4 s -> oprire); pub `/teleop/pose`; param `use_gazebo`; jurnal `~/teleop_data/robot_log.csv` |
| `detector_node.py` | perceptia | blob HSV + pinhole sol-plat, refinare lidar optionala; pub `/teleop/target` |
| `goto_node.py` | navigatorul go-to-goal (operator drop-in) | params `goal_source`, `goal_x/goal_y`, `target_class`, `goal_topic`; pub `/teleop/cmd` + `/teleop/goal_marker` |
| `gcs_console.py` | pupitrul de operator cu harta | sub `/teleop/pose`; pub `/teleop/goal` (PoseStamped); GUI Tk |
| `rover_core.py` / `nav_core.py` / `vision_core.py` | nucleele pure (DiffDrive, SafetyGate, PilotModel, navigatie, viziune) | `test_nav_core.py` (11), `test_vision_core.py` (11) |

### 3.1 goto_node - cele trei moduri de tinta

| `goal_source` | De unde vine tinta | Roverul la pornire |
|---|---|---|
| `waypoint` | parametrii ficsi `goal_x`, `goal_y` | porneste imediat spre punct |
| `object` | ultimul obiect de pe `/teleop/target` (ce vede camera) | porneste spre obiectul detectat |
| `gcs` | LIVE de la GCS, pe `goal_topic` (PoseStamped) | **STA OPRIT** pana primeste prima tinta |

In orice mod publica un marker (`visualization_msgs/Marker`) la tinta curenta pe
`/teleop/goal_marker` (vizibil in RViz).

### 3.2 gcs_console.py - pupitrul GCS

Fereastra Tkinter cu harta top-down a terenului [-20,20] m:
- deseneaza grila la 5 m, conturul terenului, punctele de interes (tintele
  colorate), roverul ca sageata orientata (din `/teleop/pose`) si tinta curenta
  (X galben);
- **click pe harta** -> converteste pixel in coordonate lume si publica
  `PoseStamped` pe `/teleop/goal` -> roverul porneste spre punct;
- buton **STOP** (trimite ca tinta pozitia curenta a roverului);
- maparea pixel<->lume e logica pura, testata cu `python3 gcs_console.py --selftest`.

Ruleaza ROS intr-un fir separat (spin in thread) si Tk in firul principal.

---

## 4. Topicuri

| Topic | Tip | Producator -> consumator |
|---|---|---|
| `/teleop/cmd` | `std_msgs/String` (JSON `{v,w,t}`) | operator/goto -> link -> robot |
| `/teleop/pose` | `std_msgs/String` (JSON `{x,y,th,t,stops,...}`) | robot -> link -> operator/goto/GCS |
| `/teleop/linkstate` | `std_msgs/String` (JSON multi-link) | link -> robot/operator/goto |
| `/teleop/target` | `std_msgs/String` (JSON `{class,x,y}`) | detector -> goto |
| `/teleop/goal` | `geometry_msgs/PoseStamped` | GCS (sau CLI/RViz) -> goto |
| `/teleop/goal_marker` | `visualization_msgs/Marker` | goto -> RViz |
| `/model/rover/cmd_vel` | `geometry_msgs/Twist` | robot -> Gazebo (prin ros_gz_bridge) |
| `/model/rover/odometry` | `nav_msgs/Odometry` | Gazebo -> robot |
| `/scan`, `/camera/image` | LaserScan / Image | Gazebo -> detector |

---

## 5. Cum se ruleaza (fluxul GCS complet)

### Pregatire (o data)
```bash
cd ~/ros2_ws/src/teleop_rover
python3 gen_rough_world.py        # lumea + terenul texturat + statia GCS
```

### Curatare inainte de fiecare pornire (un singur launch o data!)
```bash
pkill -f rmw_zenohd ; pkill -f 'gz sim' ; pkill -f 'teleop_' ; sleep 1
ss -ltnp 2>/dev/null | grep -q 7447 && echo "7447 inca ocupat" || echo "7447 liber"
```

### Terminal A - lumea + roverul (porneste OPRIT), sub Zenoh
```bash
cd ~/ros2_ws/src/teleop_rover
ros2 launch ./launch/teleop_perception.launch.py rmw:=zenoh goal_source:=gcs lat:=200 jit:=40
# asteapta linia "Started Zenoh router"
```

### Terminal B - pupitrul GCS, CU ACELASI RMW
```bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp      # cheia: la fel ca launch-ul
source ~/ros2_ws/install/setup.bash
cd ~/ros2_ws/src/teleop_rover
python3 gcs_console.py
# click pe harta = roverul porneste spre acel punct
```

Daca lumea e pe Cyclone (`rmw:=cyclone`), exporta `rmw_cyclonedds_cpp` in terminalul B.

---

## 6. Metrici si analiza (payoff-ul stiintific)

Roverul lasa jurnal in `~/teleop_data/robot_log.csv`. Pentru comparatia RMW:
```bash
# o rulare sub fiecare middleware (acelasi scenariu, acelasi seed de pilot/tinta)
#   -> salveaza jurnalele in directoare separate, ex. ~/teleop_data_cyclone, ~/teleop_data_zenoh
python3 analyze_perception.py --goal 8 3 \
    --run cyclone ~/teleop_data_cyclone \
    --run zenoh   ~/teleop_data_zenoh
```
Metrici de aplicatie: **eroare transversala de traseu (CTE)**, **timp pana la tinta**,
**reusita misiunii**, in functie de `lat/jit/loss`. Astea sunt rezultatul care
transforma demonstratorul din "merge" in "iata cum se comporta Zenoh vs Cyclone".

`sweep_teleop.py` matura parametrii (inclusiv regimul de actuator) si produce figuri
in `results/`.

---

## 7. Rolul in teza

| Strat | Artefact | Ce masoara |
|---|---|---|
| Transport (microbenchmark) | `c1_benchmark` (pub/sub sintetic) | latenta, jitter, pierdere pe mesaje |
| **Aplicatie (acest demonstrator)** | `teleop_rover` + GCS | CTE, timp pana la tinta, reusita misiunii |

Impreuna formeaza dovada pe doua niveluri pentru firul "comparatie de middleware sub
conditii de retea realiste SAR" - golul de cercetare al tezei (nu exista benchmark-uri
`rmw_zenoh` vs CycloneDDS sub conditii degradate, doar in conditii ideale).

---

## 8. Limite oneste

- Proiectia monoculara presupune sol-plat; pe teren accidentat eroarea de distanta
  creste cu panta (de aceea exista refinarea lidar).
- Camera si gpu_lidar cer ogre2/GPU.
- Totul e in SIMULARE - inca nu hardware (validarea hardware e o contributie ulterioara).
- Compromis amplitudine vs traversabilitate: denivelari mari pot impotmoli roverul.
- Markerul de tinta se vede in RViz, nu in Gazebo (in Gazebo se vede stalpul-tinta doar
  in modul `object`, unde tinta e un obiect real).
- Aceeasi implementare RMW trebuie exportata in TOATE terminalele; altfel nodurile nu
  se descopera ("Waiting for matching subscription").

---

## 9. Harta fisierelor

```
teleop_rover/
  operator_node.py         pilot / manual
  link_node.py             legatura degradata
  robot_node.py            robot + SafetyGate + jurnal
  detector_node.py         perceptie HSV (+lidar)
  goto_node.py             navigator go-to-goal (waypoint|object|gcs) + marker
  gcs_console.py           PUPITRU GCS cu harta (click = tinta)
  rover_core.py / nav_core.py / vision_core.py   nuclee pure (+ teste)
  gen_rough_world.py       genereaza lumea + terenul texturat + statia GCS
  sil_teleop.py            misiune SIL fara ROS
  sweep_teleop.py          maturare parametri -> figuri
  analyze_perception.py    metricile Zenoh vs Cyclone (CTE, timp pana la tinta)
  plot_trace.py            traseul din jurnal
  launch/
    teleop.launch.py            fara Gazebo (cinematica interna)
    teleop_gazebo.launch.py     curs plat
    teleop_perception.launch.py teren accidentat + camera + lidar + detector + goto
  worlds/
    teleop_rough.sdf                   (generat)
    teleop_rough_terrain.obj/.mtl/.png (generate; gitignore)
```

---

## 10. Depanare rapida

| Simptom | Cauza | Fix |
|---|---|---|
| `Waiting for at least 1 matching subscription(s)` | RMW diferit intre terminale | `export RMW_IMPLEMENTATION=rmw_zenoh_cpp` peste tot |
| `Address already in use ... 7447` | doua launch-uri / router Zenoh ramas | `pkill -f rmw_zenohd`, apoi un singur launch |
| Roverul pleaca singur in mod gcs | ruleaza `goto_node` vechi | rebuild / inlocuieste fisierul |
| Terenul gri (nu colorat) | calea texturii `map_Kd` nerezolvata | textura langa `.obj`; daca tot nu, cale absoluta in `.mtl` |
| Pupitrul nu arata sageata roverului | alt RMW sau router oprit | acelasi RMW + router pornit |
| `RTPS_TRANSPORT_SHM` (doar Fast DDS) | resturi din procese ucise | `rm -f /dev/shm/fastrtps_*` |
