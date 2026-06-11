# joint_emulator — bancul cu 6 servomotoare ABB ca articulatii (C4)

## Ce este
Trei perechi de servomotoare cuplate rigid pe acelasi ax (suportul
albastru = lagarul + cuplajul). In fiecare pereche:
- **motorul A** actioneaza (actuatorul / perturbatia / "exoscheletul");
- **motorul B** citeste encoderul si aplica un cuplu de opozitie dupa o
  lege de **impedanta**: tau_B = -K*(th-th0) - B*om — tine echilibrul si
  "adapteaza forta inversa" exact cum ai descris.
Rolurile se pot inversa din software. 3 perechi = sold / genunchi /
glezna (un picior) — geamanul FIZIC al lui rehab_exo_description; sau
bancul de validare hardware (C4) pentru teleoperarea prin retele
degradate.

## Fisiere (toate fara ROS, rulabile oriunde)
- joint_core.py     legea de impedanta, pacientul virtual (cu "catch"
                    spastic), fizica perechii, DelayLine, EnergyMonitor
                    (pasivitate), SafetyGate (watchdog -> cuplu zero)
- drive_iface.py    contractul unic spre fier + SimBackend (backend-ul
                    real se scrie dupa identificarea drive-urilor)
- test_joint_core.py  21/21 verificari, inclusiv demonstratia-cheie:
                    aceeasi lege, stabila la 0 ms, instabila la 60 ms

## REGULILE DE SIGURANTA (inaintea oricarui test pe fier)
1. Motorul B ruleaza NUMAI in mod cuplu (torque). NICIODATA pozitie
   contra pozitie pe ax rigid — oscilatie + supracurent garantate.
2. Limita software de cuplu la <10-15% din nominal la primele teste,
   PLUS limita de curent setata in drive (doua bariere independente).
3. Watchdog pe masura: encoder mut > 100 ms => cuplu zero (testat).
4. Rampa de cuplu activata (fara salturi); E-stop fizic la indemana.
5. Primele teste pe O SINGURA pereche; nimeni cu mana pe cuplaj.

## Planul etapizat
- **L0 (GATA)** nucleul pur + 21/21 teste — ruleaza oriunde, acum.
- **L1 — identificarea fierului**: modelul drive-urilor decide backend-ul
  (EtherCAT => ros2_control + ethercat_driver; analog +/-10V => alta
  cale). Apoi J si frecarea reale ale perechii dintr-un test de
  coast-down — intra direct in PairSim.
- **L2 — echilibrul pe o pereche reala**: A aplica trepte mici de cuplu,
  B tine echilibrul cu ImpedanceLaw; comparatia masurat vs simulat.
- **L3 — tele-impedanta prin legatura degradata**: masura encoderului
  trece prin DegradedChannel/linkstate (acelasi tipar ca roverul);
  Zenoh vs CycloneDDS PE FIER; apoi pacientul virtual spastic pentru
  articolul de tele-reabilitare (A4). Intrebarea noua de cercetare:
  **impedanta adaptata la calitatea legaturii** (K scade cand latenta
  creste) — masurabila direct pe acest banc.

## Ce lipseste ca sa pornim L1
O poza cu PLACUTA drive-urilor de pe perete (cutiile in care intra
cablurile portocalii de putere si verzi de feedback). Modelul lor
decide tot lantul software.

## Mediul de simulare COMPLET (fara fier, ruleaza acum)
    python3 test_joint_core.py                  # 28/28
    python3 sil_joint.py echilibru              # treapta + impedanta
    python3 sil_joint.py pacient_spastic        # B = membrul cu catch
    python3 sil_joint.py adaptiv_vs_fix --ms 60 # duelul la 60 ms
    python3 sil_joint.py delay_sweep            # tabelul E vs latenta
    python3 plot_joint.py                       # figurile (figs/*.png)
ROS2 (pe masina cu Jazzy): nodul nodes/emulator_node.py expune perechile
pe /joint/state si primeste /joint/cmd_a, /joint/impedance, /joint/estop;
degradarea masurii se injecteaza pe /teleop/linkstate — acelasi tipar ca
roverul.

## LECTIA DE ARHITECTURA (demonstrata in teste si figuri)
Amortizarea pe o viteza intarziata POMPEAZA energie: impedanta
totul-prin-link explodeaza de la ~20-30 ms (E creste la mii de J), iar
inmuierea lui K nu o salveaza. Solutia masurata: **amortizarea LOCALA**
(langa drive) + **rigiditatea adaptiva** prin link — pasiv (E~0) pana la
120 ms, cu pretul corect: articulatia devine mai moale (th=tau/K_ef).
De aceea Raspberry Pi sta LANGA banc (Modbus local, 50-100 Hz), iar prin
Zenoh/DDS calatoresc doar referintele si K — vezi modbus_backend.py.

## Drive-urile ABB "seria 300" + Modbus + Raspberry Pi
modbus_backend.py e scheletul gata de completat: harta de registre
(cuplu/pozitie/viteza/enable + scari) se ia DIN MANUAL dupa citirea
placutei exacte. Pana atunci refuza intentionat sa porneasca. Modbus
RTU = ~50-100 Hz pe registru: perfect pentru bucla LOCALA de pe Pi,
inutilizabil pentru a inchide bucla prin internet — exact concluzia
figurii joint_sweep.

## Pluginul de encodere: viteza, acceleratie, grafice
- encoder_core.py — cuantizarea reala (counts_per_rev) + estimatorul
  alpha-beta-gamma: viteza de 22x mai curata decat derivata bruta
  (RMS 0.026 vs 0.58 rad/s la 4096 cpr / 1 kHz), acceleratie utilizabila.
  Ruleaza si pe Raspberry Pi (fara numpy).
- nodes/encoder_monitor_node.py — sub /joint/state -> pub
  /joint/kinematics {th, om, acc, om_raw} + CSV ~/sar_data/encoders.csv.
  Acelasi nod peste simulare si peste fier. quantize_cpr:=0 cand pozitia
  vine deja cuantizata de la drive.
- plot_encoder.py — graficele de iesire: encoder_traces.png (th/om/acc)
  si encoder_filter.png (brut vs filtrat). Fara argument = demo local;
  cu argument = CSV-ul nodului:  python3 plot_encoder.py ~/sar_data/encoders.csv
ATENTIE pe fier: cand citim viteza direct din drive (registru dedicat),
om_raw devine acela; estimatorul ramane pentru acceleratie si pentru
backup cand registrul de viteza lipseste.

## Vizualizare (RViz + Gazebo) si panoul operatorului
Matricea de terminale (toate cu `source /opt/ros/jazzy/setup.bash`,
din `~/ros2_ws/src/joint_emulator`):

| T | Comanda | Rol |
|---|---|---|
| 1 | `python3 nodes/emulator_node.py --ros-args -p adaptive:=true` | fizica perechilor |
| 2 | `python3 nodes/encoder_monitor_node.py` | viteza/accel din encodere + CSV |
| 3 | `ros2 launch launch/viz_rviz.launch.py` | RViz: bancul se misca (marcaj portocaliu pe ax) |
| 4 | `python3 nodes/operator_panel_node.py` | PANOUL: slidere tau_A/K/B/link, ESTOP, grafice de reactie |

Gazebo (oglinda vizuala, optional — fizica ramane in emulator):
| T | Comanda |
|---|---|
| 5 | `gz sim -r gz/joint_bench_world.sdf` |
| 6 | `ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=gz/bridge_bench.yaml` |
| 7 | `python3 nodes/gz_mirror_node.py` |

Verificari: in RViz, Fixed Frame = base_link; daca modelul nu apare,
adauga manual RobotModel cu Description Topic = /robot_description.
In gz: `gz topic -l | grep cmd_pos` trebuie sa arate cele 3 topicuri.
Decizie de arhitectura: Gazebo e OGLINDA (JointPositionController
urmareste pozitia emulatorului/fierului), nu a doua fizica — o singura
sursa de adevar, aceleasi noduri peste sim si peste banc.
