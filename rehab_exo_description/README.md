# rehab_exo_description

Descrierea URDF/xacro a unui robot medical de recuperare locomotorie cu 6 GDL
(sold/genunchi/glezna x2, 0-180 grade), plus configurarea ros2_control, scripturi
de control si fisiere de lansare pentru RViz si Gazebo (gz). Este demonstratorul
exoschelet din teza (track C4 conform CLAUDE.md), peste care se monteaza extensiile
de telereabilitare (heartbeat, supervizor de siguranta, model de pacient) ce
folosesc aceeasi metodologie de retea degradata ca benchmark-ul rmw_zenoh vs
CycloneDDS. Model de dezvoltare/simulare, NU controller medical certificat (sursa:
package.xml, docstring-uri).

## Scop

Ofera un model robotic complet (geometrie + control + simulare) pe care se pot
demonstra exercitii de recuperare si, prin extensiile de telereabilitare, masura
calitatea legaturii operator-robot peste retea degradata (netem). Docstring-ul din
operator_heartbeat.py spune explicit ca datele de retea publicate sunt 'exact
datele de care ai nevoie pentru graficele comparative rmw_zenoh vs CycloneDDS din
articol', iar netem_profiles.sh declara profilurile 'identice cu metodologia
benchmark-ului rmw_zenoh vs CycloneDDS'. Legatura cu o contributie numerotata
(C1-C4) nu e scrisa literal in cod; vezi CLAUDE.md (sec. 7) care plaseaza
pachetul la C4 (exoschelet + motor).

## Arhitectura

Pachetul este de tip ament_cmake (package.xml: build_type ament_cmake;
CMakeLists.txt instaleaza resursele in share/ si scripturile in lib/). Nu are
structura ament_python cu entry_points; scripturile se lanseaza ca executabile
(ros2 run / Node) sau direct cu python3.

Singurul strat 'nucleu pur fara ROS' clar identificabil este exercise_core.py
(docstring: 'Nucleul procesului de control ... FARA dependinte ROS'). El este
importat de nodul subtire exercise_controller.py (`import exercise_core as core`).
ATENTIE la metodologia nucleu pur + `_selftest`: exercise_core.py NU contine
nicio functie `_selftest` si nici bloc `if __name__ == "__main__"` (verificat prin
grep) -- deci nu este auto-testabil prin rulare directa in forma actuala.

Alte scripturi pur offline (fara ROS): plot_recording.py si session_report.py
(docstring-uri: 'Nu necesita ROS' / 'Nu este nod ROS'). patch_urdf_extensions.py
este un utilitar XML offline.

## Fisiere

Scripturi Python (scripts/):

| Fisier | Rol (din docstring/cod) |
| --- | --- |
| exercise_core.py | Nucleu fara ROS: repertoriu de 12 exercitii atomice + 4 sesiuni; genereaza traiectorii cosinus (viteza zero la capete) cu siguranta (clamp + validare viteza) si Player.sample(t). Contine si clamp_adjust() pentru cele 5 axe de ajustare (regula shank_ext <= seat_lift + 0.03). FARA `_selftest`. |
| exercise_controller.py | Nod ROS subtire (v3) peste exercise_core. Comanda 6 servomotoare de exercitiu + 5 axe de ajustare. Backend `joint_states` (publica 11 articulatii pe /joint_states la 50 Hz pentru RViz) sau `trajectory` (JointTrajectory + Float64MultiArray pentru ros2_control/Gazebo). |
| operator_panel.py | Interfata grafica Tkinter a operatorului: zona exercitii, zona ajustare la pacient, zona inregistrare. Publica pe exercise_cmd, adjust_cmd, record_cmd. Necesita python3-tk. |
| telemetry_display.py | Afisaj LIVE Tkinter/matplotlib: pozitie/viteza/torque pentru cele 6 servomotoare (ultimele ~12 s); citeste doar /joint_states. Necesita python3-tk. |
| sensor_recorder.py | Nod ROS care inregistreaza /joint_states in CSV in ~/rehab_data/; comenzi start / start nume_fisier / stop pe /record_cmd. |
| plot_recording.py | Offline (fara ROS): transforma un CSV din sensor_recorder intr-o figura cu 3 panouri (pozitie, viteza, torque) + statistici in consola. Necesita matplotlib. |
| session_report.py | Offline (fara ROS): calculeaza metrici de recuperare (ROM, simetrie SI, SPARC, repetari, cuplu, urmarire RMS) dintr-un CSV si produce raport PDF. Are argparse (vezi mai jos). |
| safety_supervisor.py | Nod ROS pe partea robotului: vegheaza cupluri, viteze si (optional) heartbeat-ul operatorului; la depasire publica comanda de STOP lin pe /exercise_cmd. Raspunde la heartbeat (echo). |
| operator_heartbeat.py | Nod ROS pe partea operatorului: heartbeat numerotat + echo, masoara RTT (EMA) si pierderea de pachete; publica starea legaturii pe /telerehab/network_health si optional scrie CSV in ~/rehab_data/. |
| patient_model.py | Nod ROS: simuleaza pacientul ca sarcina dinamica (arc-amortizor + tremor optional) si aplica cupluri prin ApplyJointForce/ros_gz_bridge. Citeste /joint_states, publica /rehab/patient_force/<joint> (Float64). |
| patch_urdf_extensions.py | Utilitar offline: insereaza in rehab_exo.urdf plugin-urile gz ApplyJointForce (6 articulatii) + 3 senzori IMU, inainte de </robot>. Idempotent, face backup .bak, valideaza XML-ul. |
| netem_profiles.sh | Script bash (sudo): aplica profiluri tc netem de degradare a retelei (loss5/loss15/loss30/sar/wifi_slab/clear/status) pe interfata lo, identic cu metodologia benchmark-ului. |

Resurse (instalate in share/ prin CMakeLists.txt): urdf/ (rehab_exo.urdf,
rehab_exo.xacro), launch/ (10 fisiere .launch.py), config/ (controllers.yaml,
gz_patient_bridge.yaml, patient_demo.yaml, safety_limits.yaml), rviz/ (rehab.rviz),
worlds/ (rehab_world.sdf). Documentatie suplimentara: docs/INSTALL_EXTENSII.md.

## Sintaxe de rulare

Build:

    cd ~/ros2_ws && colcon build --packages-select rehab_exo_description --symlink-install
    source install/setup.bash

Scripturi offline (fara ROS):

    python3 scripts/session_report.py ~/rehab_data/sesiune.csv
    python3 scripts/session_report.py sesiune.csv --out ~/rehab_data/rapoarte
    python3 scripts/session_report.py sesiune.csv --inspect
    python3 scripts/plot_recording.py ~/rehab_data/sesiune_X.csv [iesire.png]
    python3 scripts/patch_urdf_extensions.py ~/ros2_ws/src/rehab_exo_description/urdf/rehab_exo.urdf

Argumente session_report.py (din argparse, sursa reala):
  csv (pozitional)  fisierul CSV inregistrat de sensor_recorder
  --out             director de iesire (implicit ~/rehab_data/rapoarte)
  --inspect         doar listeaza coloanele, nu genereaza raport

NOTA: exercise_core.py NU expune `_selftest` si nici bloc `__main__`, deci nu se
ruleaza standalone pentru verificare offline (verificat in cod).

Rulare noduri (scripturile se instaleaza in lib/<pkg>, deci se cheama cu .py):

    ros2 run rehab_exo_description exercise_controller.py
    ros2 run rehab_exo_description operator_panel.py
    ros2 run rehab_exo_description telemetry_display.py
    ros2 run rehab_exo_description sensor_recorder.py
    ros2 run rehab_exo_description safety_supervisor.py
    ros2 run rehab_exo_description operator_heartbeat.py
    ros2 run rehab_exo_description patient_model.py

Launch (din docstring-urile fisierelor din launch/):

    ros2 launch rehab_exo_description display.launch.py
    ros2 launch rehab_exo_description demo.launch.py
    ros2 launch rehab_exo_description demo_all.launch.py
    ros2 launch rehab_exo_description operator.launch.py
    ros2 launch rehab_exo_description gazebo.launch.py
    ros2 launch rehab_exo_description exercitii_glezna.launch.py [reps:=2]
    ros2 launch rehab_exo_description exercitii_genunchi.launch.py [reps:=2]
    ros2 launch rehab_exo_description exercitii_sold.launch.py [reps:=2]
    ros2 launch rehab_exo_description exercitii_combinat.launch.py [reps:=2]
    ros2 launch rehab_exo_description telerehab.launch.py \
        [telerehab:=true] [with_patient:=true] [profile:=<cale.yaml>] \
        [limits:=<cale.yaml>] [stop_command:=<txt>]

(Argumentele de launch de mai sus sunt verificate in corpul fisierelor prin
DeclareLaunchArgument. telerehab.launch.py declara exact: telerehab
(implicit false), with_patient (implicit false), profile, limits, stop_command
(implicit neutral). demo_all.launch.py declara in plus argumentul exercise
(implicit full_extension) pe langa reps (implicit 3); fisierele exercitii_*.launch.py
si demo_all.launch.py accepta reps (implicit 3).)

## Parametri si topicuri

exercise_controller.py
  Parametri: exercise (implicit "neutral"), reps (3), backend ("joint_states"),
             rate_hz (50.0), loop (False).
  Sub: exercise_cmd (std_msgs/String), adjust_cmd (std_msgs/Float64MultiArray),
       joint_states (sensor_msgs/JointState, doar backend trajectory ca feedback).
  Pub: joint_states (backend joint_states) SAU
       /leg_trajectory_controller/joint_trajectory +
       /adjust_position_controller/commands (backend trajectory).
  Mesaj /exercise_cmd: nume simplu ("ankle_pump", "knee_session", "neutral") sau
  JSON {"exercise": "...", "reps": N} (cod: json.loads, d.get("exercise"/"reps")).
  adjust_cmd: [seat_lift, left_thigh_ext, right_thigh_ext, left_shank_ext,
              right_shank_ext] in metri.

operator_panel.py
  Pub: exercise_cmd (String), adjust_cmd (Float64MultiArray), record_cmd (String).

sensor_recorder.py
  Sub: joint_states (JointState), record_cmd (String -> "start"/"start nume"/"stop").

telemetry_display.py
  Sub: joint_states (JointState).

safety_supervisor.py
  Parametri: limits_file (""), stop_command ("neutral"), enable_heartbeat (False),
             heartbeat_timeout (0.6), startup_grace (2.0), rate (50.0).
  Sub: /joint_states (JointState), /telerehab/heartbeat (String, "seq;t_ns"),
       /safety/reset (std_msgs/Empty).
  Pub: /telerehab/heartbeat_echo (String), /exercise_cmd (String, comanda STOP),
       /safety/status (String, "OK"/"TRIPPED:<motiv>"), /safety/event (String).

operator_heartbeat.py
  Parametri: hb_rate (20.0), loss_timeout (1.0), window (100), rtt_warn (150.0),
             rtt_crit (400.0), loss_warn (5.0), loss_crit (20.0), log_csv (True),
             label (implicit $RMW_IMPLEMENTATION sau "necunoscut").
  Pub: /telerehab/heartbeat (String), /telerehab/network_health (String,
       format "cheie=valoare ..." conform docstring).
  Sub: /telerehab/heartbeat_echo (String).

patient_model.py
  Parametri: profile_file (""), rate (100.0), scale (1.0).
  Sub: /joint_states (JointState), /patient_model/scale (std_msgs/Float64).
  Pub: /rehab/patient_force/<joint> (std_msgs/Float64), cate unul pentru fiecare
       din cele 6 articulatii motorizate.

Conventia de semn URDF (din exercise_core.py): hip + ridica coapsa
[-0.45..+0.70] rad; knee + extensie [0.00..+1.75] rad; ankle + dorsiflexie
[-0.60..+0.60] rad. NOTA MEDICALA (din cod): valorile sunt de demonstratie, nu
prescriptii clinice.
