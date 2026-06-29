# joint_emulator

Emulator de articulatie pe banc: doua servomotoare cuplate rigid pe acelasi
ax formeaza o articulatie -- motorul A actioneaza, motorul B citeste encoderul
si aplica un cuplu de opozitie dupa o lege de impedanta (din docstring-ul
`joint_core.py`). Rolul in teza: carligul este intarzierea de masura/comanda --
aceeasi lege de impedanta devine instabila cand bucla trece printr-o legatura
cu latenta (teleoperare degradata), iar impedanta adaptiva incearca sa tina
bucla stabila acolo unde impedanta fixa explodeaza.

## Scop

Problema: cum tii o bucla de impedanta stabila pe o articulatie reala cand
masura encoderului ajunge cu latenta/jitter/pierdere la controler. Solutia
explorata de banc: amortizarea + watchdog + limita de cuplu raman LOCAL (langa
banc), iar legatura degradata transporta doar K, th0 si comenzile (din
docstring-ul `modbus_backend.py`). Contributia este C4 -- marcata in titlul
`README_JOINT.md` ('joint_emulator -- bancul cu 6 servomotoare ABB ca
articulatii (C4)') si sustinuta de docstring-ul `plot_joint.py`, care numeste
`figs/joint_sweep.png` (E_max vs latenta, fix-total-remote vs adaptiv+amortizare
locala) ca FIGURA-CHEIE pentru C4.

## Arhitectura

Pachetul urmeaza metodologia nucleu pur + verificari -> nod ROS subtire -> SIL,
dar atentie: NU exista `package.xml` / `setup.py` / `setup.cfg` in acest
director, deci nu este un pachet ament_python instalabil cu entry_points.
Scripturile se ruleaza direct cu `python3 <fisier>` (nodurile fac
`sys.path.insert` ca importurile core sa mearga standalone -- vezi nota din
CLAUDE.md sectiunea 6).

- Nucleu pur (fara ROS, fara fier): `joint_core.py`, `encoder_core.py`,
  `teleimpedance.py`, `drive_iface.py` (cu `SimBackend`), schema de backend
  real `modbus_backend.py`.
- Verificari nucleu: `test_joint_core.py` (bateria de assert-uri ruleaza la
  executia fisierului).
- Noduri ROS subtiri (JSON pe `std_msgs/String`): `nodes/emulator_node.py`,
  `nodes/encoder_monitor_node.py`, `nodes/operator_panel_node.py`,
  `nodes/gz_mirror_node.py`, `nodes/state_to_jointstate_node.py`.
- SIL (mediul de simulare complet, fara ROS): `sil_joint.py`.
- Figuri / vizualizare / geometrie: `plot_joint.py`, `plot_encoder.py`,
  `tools/gen_bench_model.py`, `launch/viz_rviz.launch.py`.

## Fisiere

| Fisier | Ce face (din docstring / cod) |
| --- | --- |
| `joint_core.py` | Nucleul pur al emulatorului: `ImpedanceLaw`, `VirtualLimb` (membrul emulat de B, cu optional 'catch' spastic), `PairSim` (fizica perechii pe ax comun), `DelayLine`, `EnergyMonitor`, `SafetyGate`. SI, integrare semi-implicita Euler. |
| `encoder_core.py` | Stratul de encoder: `EncoderModel` (cuantizare la counts_per_rev + zgomot optional), `NaiveDiff` (derivata bruta), `KinematicEstimator` (filtru alpha-beta-gamma pentru pozitie/viteza/acceleratie), `EncoderLogger` (CSV t,pair,th_raw,th,om,acc). |
| `teleimpedance.py` | Stratul de tele-impedanta: `DegradedMeasure` (canal de masura cu ms/jit/loss/down, livrare monotona), `AdaptiveImpedance` (K scade si B creste cand masura imbatraneste). |
| `drive_iface.py` | Interfata unica drive (`enable/disable/read/set_torque/estop`) intre logica si fier; contine `SimBackend`, perechea simulata in spatele aceleiasi interfete ca fierul. |
| `modbus_backend.py` | Schelet (NU functional inca) de backend real pentru drive-uri ABB prin Modbus RTU/TCP; harta de registre din CONFIG se completeaza din manualul drive-ului. Aceeasi interfata ca `SimBackend`. |
| `test_joint_core.py` | Bateria de verificari a emulatorului (fara ROS/fier); ruleaza assert-uri si tipareste `=== N/N verificari trecute ===`. |
| `sil_joint.py` | Mediul de simulare complet fara ROS: scenarii numite, urme CSV, bilant in consola. |
| `nodes/emulator_node.py` | Nodul ROS2 al bancului peste `SimBackend`; A primeste comenzi de cuplu, B ruleaza legea de impedanta (fixa sau adaptiva) cu amortizare locala. |
| `nodes/encoder_monitor_node.py` | Pluginul de cinematica: ia pozitia din `/joint/state`, o trece prin estimatorul alpha-beta-gamma, publica viteza+acceleratie curate, jurnal CSV. |
| `nodes/operator_panel_node.py` | Panoul operatorului (GUI desktop): slidere de cuplu A, impedanta (K,B), degradare (ms), ESTOP, si graficele de reactie din encoderele B. Necesita desktop; emulatorul + monitorul pornite separat. |
| `nodes/gz_mirror_node.py` | Oglinda Gazebo: citeste `/joint/state` si publica pozitiile spre controllerele din lumea gz (prin ros_gz_bridge); Gazebo doar urmareste, nu simuleaza fizica. |
| `nodes/state_to_jointstate_node.py` | Podul spre lumea ROS standard: traduce `/joint/state` (JSON) in `sensor_msgs/JointState` pe `/joint_states`, pentru robot_state_publisher + RViz. |
| `plot_joint.py` | Genereaza `figs/joint_sweep.png` (E_max vs latenta, figura-cheie C4) si `figs/joint_duel.png` (pozitia in timp la 60 ms: fix vs adaptiv). |
| `plot_encoder.py` | Genereaza `figs/encoder_traces.png` si `figs/encoder_filter.png` din CSV-ul encoderelor sau, fara argument, dintr-un demo generat local. |
| `tools/gen_bench_model.py` | Generatorul geometriei bancului: o tabela de geometrie -> `urdf/joint_bench.urdf` (RViz) si `gz/joint_bench_world.sdf` (Gazebo). |
| `launch/viz_rviz.launch.py` | Lanseaza robot_state_publisher (URDF) + `state_to_jointstate_node.py` + RViz. Emulatorul se porneste SEPARAT. |

Resurse non-`.py`: `urdf/joint_bench.urdf`, `gz/joint_bench_world.sdf`,
`gz/bridge_bench.yaml`, `rviz/joint_bench.rviz`, `figs/*.png`,
`requirements.txt`, `README_JOINT.md`.

## Sintaxe de rulare

Acest director NU contine `package.xml`/`setup.py`, deci colcon NU il construieste
ca pachet si nu exista entry_points pentru `ros2 run`. Toate scripturile (inclusiv
nodurile din `nodes/`) se ruleaza DIRECT cu `python3 <fisier>` din radacina pachetului.

Verificari nucleu offline (fara ROS/fier):

    cd ~/ros2_ws/src/joint_emulator
    python3 test_joint_core.py

SIL (scenarii din `sil_joint.py`, alegerile reale din argparse):

    python3 sil_joint.py echilibru
    python3 sil_joint.py pacient_spastic
    python3 sil_joint.py delay_sweep
    python3 sil_joint.py adaptiv_vs_fix --ms 60

Argumente CLI `sil_joint.py` (din argparse): pozitional `scenariu` cu choices
`echilibru | pacient_spastic | delay_sweep | adaptiv_vs_fix`; optiuni `--ms`
(implicit 60.0), `--jit` (0.0), `--loss` (0.0), `--t_end` (3.0), `--seed` (42),
`--trace` (implicit None). Nota: nu exista flag `--down` in `sil_joint.py` (nici
in argparse, nici in docstring-ul lui). Token-ul `down` apare in alta parte:
in schema canalului degradat `{ms, jit, loss, down}` din `teleimpedance.py`
(`DegradedMeasure`) si in mesajul `/teleop/linkstate` al `emulator_node.py`.

Figuri:

    python3 plot_joint.py
    python3 plot_encoder.py                       # demo generat local
    python3 plot_encoder.py ~/sar_data/encoders.csv

Geometrie URDF/SDF:

    python3 tools/gen_bench_model.py

Noduri ROS (rulate direct, din docstring-uri):

    python3 nodes/emulator_node.py
    python3 nodes/encoder_monitor_node.py
    python3 nodes/operator_panel_node.py          # necesita desktop
    python3 nodes/gz_mirror_node.py
    python3 nodes/state_to_jointstate_node.py

Launch (vizualizare RViz; emulatorul se porneste separat):

    ros2 launch launch/viz_rviz.launch.py

## Parametri si topicuri

`emulator_node.py` (`declare_parameter` reali): `backend` (sim; alt backend
ridica SystemExit), `n_pairs` (3), `rate_hz` (200.0), `k` (20.0), `b` (0.8),
`tau_max` (2.0), `adaptive` (False), `state_hz` (50.0), `estop_energy` (0.0;
>0 activeaza auto-ESTOP pe energie pe fereastra de 1s).

- sub `/joint/cmd_a` (`std_msgs/String`) -- JSON `{"pair":0,"tau":0.5}`
- sub `/joint/impedance` -- JSON `{"pair":0,"k":20,"b":0.8,"th0":0,"adaptive":true}`
- sub `/joint/estop` -- orice mesaj => cuplu zero pe tot
- sub `/teleop/linkstate` -- JSON `{"ms":..,"jit":..,"loss":..,"down":..}`
- pub `/joint/state` -- JSON per pereche; din cod, fiecare pereche `k` are
  `{"t","th","om","tau_b","k_ef","win_energy","estopped"}`.

`encoder_monitor_node.py` (`declare_parameter` reali): `state_topic`
(`/joint/state`), `out_topic` (`/joint/kinematics`), `rate_hz` (50.0),
`csv_path` (`~/sar_data/encoders.csv`), `alpha` (0.25), `beta` (0.02),
`gamma` (0.0005), `quantize_cpr` (4096).

- sub `state_topic` (implicit `/joint/state`, `std_msgs/String`)
- pub `out_topic` (implicit `/joint/kinematics`, `std_msgs/String`) -- JSON cu
  `th, om, acc, om_raw` per pereche (din docstring)

`operator_panel_node.py` (topicuri din cod, fara parametri declarati):

- pub `/joint/cmd_a`, `/joint/impedance`, `/teleop/linkstate`, `/joint/estop`
- sub `/joint/state`, `/joint/kinematics`

`gz_mirror_node.py`: sub `/joint/state`; pub `/bench/pair{k}_cmd_pos`
(`std_msgs/Float64`, k in 0..2). Fara parametri declarati.

`state_to_jointstate_node.py` (`declare_parameter`): `state_topic`
(`/joint/state`). sub `state_topic` (`std_msgs/String`); pub `/joint_states`
(`sensor_msgs/JointState`).
