# Extensii rehab_exo — instalare și testare

Pachet de extensii pentru `rehab_exo_description` (ROS2 Jazzy + Gazebo Harmonic).
Nimic din ce există nu se modifică, cu o singură excepție controlată: patch-ul
URDF (cu backup `.bak` și verificare XML). Fiecare modul funcționează independent.

## Conținut

```
rehab_exo_description/
├── scripts/
│   ├── safety_supervisor.py      # watchdog cupluri/viteze + failsafe la pierderea legăturii
│   ├── operator_heartbeat.py     # stația operatorului: RTT, pierdere pachete, jurnal CSV
│   ├── patient_model.py          # pacient simulat: rezistență arc-amortizor + tremor
│   ├── session_report.py         # CSV → ROM, simetrie, SPARC, repetări → raport PDF
│   ├── patch_urdf_extensions.py  # inserează ApplyJointForce ×6 + IMU ×3 în URDF
│   └── netem_profiles.sh         # profiluri tc netem (0/5/15/30% + scenarii SAR/WiFi)
├── config/
│   ├── safety_limits.yaml        # limite de cuplu/viteză per articulație
│   ├── patient_demo.yaml         # profil demonstrativ de pacient
│   └── gz_patient_bridge.yaml    # punte ros_gz pentru cupluri + IMU
├── launch/
│   └── telerehab.launch.py       # supervizor [+ pacient + punte], cu argumente
└── worlds/
    └── rehab_world.sdf           # lume cu sistemele de senzori (IMU/FT/contact)
```

## 1. Instalare

```bash
# copiați fișierele în pachet (păstrând structura de mai sus)
cp scripts/*   ~/ros2_ws/src/rehab_exo_description/scripts/
cp config/*    ~/ros2_ws/src/rehab_exo_description/config/
cp launch/*    ~/ros2_ws/src/rehab_exo_description/launch/
mkdir -p       ~/ros2_ws/src/rehab_exo_description/worlds
cp worlds/*    ~/ros2_ws/src/rehab_exo_description/worlds/
chmod +x       ~/ros2_ws/src/rehab_exo_description/scripts/*.py \
               ~/ros2_ws/src/rehab_exo_description/scripts/netem_profiles.sh
```

În `CMakeLists.txt`, la blocul `install(PROGRAMS ...)` existent, adăugați:

```cmake
    scripts/safety_supervisor.py
    scripts/operator_heartbeat.py
    scripts/patient_model.py
    scripts/session_report.py
```

și asigurați-vă că directoarele noi se instalează (dacă nu există deja linia):

```cmake
install(DIRECTORY launch config worlds DESTINATION share/${PROJECT_NAME})
```

Dependență nouă în `package.xml` (doar pentru modelul de pacient):

```xml
<exec_depend>ros_gz_bridge</exec_depend>
```

Apoi:

```bash
cd ~/ros2_ws && colcon build --packages-select rehab_exo_description
source install/setup.bash
```

## 2. Supervizorul de siguranță (5 minute)

```bash
# T1: simularea, ca până acum
ros2 launch rehab_exo_description gazebo.launch.py
# T2: supervizorul (mod local, fără heartbeat)
ros2 launch rehab_exo_description telerehab.launch.py
# T3: panoul — porniți un exercițiu
ros2 run rehab_exo_description operator_panel.py
```

Verificare: `ros2 topic echo /safety/status` arată `OK`. Forțați o declanșare
coborând temporar o limită în `config/safety_limits.yaml` (ex. `velocity_max: 0.05`
la genunchi) și porniți `full_extension` — supervizorul publică `neutral` pe
`/exercise_cmd`, robotul revine lin la șezut, `/safety/event` explică motivul.
Rearmare: `ros2 topic pub --once /safety/reset std_msgs/msg/Empty "{}"`.

## 3. Telereabilitare (legătura operator ↔ robot)

Pe **stația robotului**:

```bash
ros2 launch rehab_exo_description telerehab.launch.py telerehab:=true
```

Pe **stația operatorului** (a doua mașină sau al doilea terminal):

```bash
ros2 run rehab_exo_description operator_heartbeat.py --ros-args -p label:=zenoh_loss15
ros2 run rehab_exo_description operator_panel.py
```

Degradați legătura și observați comportamentul:

```bash
sudo ./netem_profiles.sh loss15        # apoi loss30, sar, wifi_slab...
ros2 topic echo /telerehab/network_health
sudo ./netem_profiles.sh clear
```

La întreruperea heartbeat-ului peste `heartbeat_timeout` (0.6 s implicit),
supervizorul oprește exercițiul în siguranță — acesta este rezultatul
demonstrabil „failsafe la degradarea rețelei".

**Comparația de middleware** (miezul tezei): repetați aceeași sesiune cu

```bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp      # apoi rmw_cyclonedds_cpp
```

pe ambele stații; `operator_heartbeat` scrie automat eticheta și măsurătorile
în `~/rehab_data/network_health_*.csv` — datele brute pentru graficele
comparative din articol.

## 4. Pacientul simulat (necesită patch-ul URDF)

```bash
python3 scripts/patch_urdf_extensions.py \
    ~/ros2_ws/src/rehab_exo_description/urdf/rehab_exo.urdf
cd ~/ros2_ws && colcon build --packages-select rehab_exo_description && source install/setup.bash
```

Pentru IMU, porniți Gazebo cu lumea nouă — fie editați `gz_args` în
`gazebo.launch.py` ca să indice `worlds/rehab_world.sdf`, fie, dacă launch-ul
expune deja argumentul:

```bash
ros2 launch rehab_exo_description gazebo.launch.py \
    gz_args:="-r $(ros2 pkg prefix rehab_exo_description)/share/rehab_exo_description/worlds/rehab_world.sdf"
```

Apoi:

```bash
ros2 launch rehab_exo_description telerehab.launch.py with_patient:=true
```

Verificări: `ros2 topic echo /rehab/imu/left_foot` (IMU prin punte) și, în
telemetrie, cuplurile cresc vizibil față de rularea „fără pacient". Dacă nu se
simte nimic, confirmați numele modelului în Gazebo: `gz topic -l | grep cmd_force`
trebuie să arate `/model/rehab_exo/joint/...` (dacă spawn-ul folosește alt nume,
actualizați-l în `gz_patient_bridge.yaml`). Sarcina se
ajustează live: `ros2 topic pub --once /patient_model/scale std_msgs/msg/Float64 "{data: 0.5}"`.
Profiluri per pacient: copiați `patient_demo.yaml` și porniți cu `profile:=<cale>`.

## 5. Raportul de sesiune

```bash
# întâi inspectați antetul CSV-ului vostru:
python3 scripts/session_report.py ~/rehab_data/<sesiune>.csv --inspect
# apoi raportul:
python3 scripts/session_report.py ~/rehab_data/<sesiune>.csv
# => ~/rehab_data/rapoarte/raport_<sesiune>.pdf
```

## Două presupuneri de verificat (singurele puncte de adaptare)

1. **Formatul comenzii de STOP.** Supervizorul publică `String "neutral"` pe
   `/exercise_cmd`, replicând butonul STOP. Dacă `exercise_controller` așteaptă
   alt format (ex. JSON `{"exercise":"neutral"}`), setați
   `stop_command:='<textul corect>'` la lansare — nu e nevoie de cod.
2. **Antetul CSV.** `session_report.py` detectează automat coloanele de tip
   `<joint>_pos/_vel/_eff` și timpul `t/time/stamp`. Dacă `sensor_recorder`
   folosește alte nume, rulați `--inspect` și fie redenumiți antetul, fie
   adăugați sufixele voastre în dicționarul `JOINT_SUFFIXES` (o linie).

Dacă îmi trimiteți `exercise_controller.py` (partea de parsare a comenzii) și
primele 2 rânduri dintr-un CSV real, calibrez ambele puncte exact.
