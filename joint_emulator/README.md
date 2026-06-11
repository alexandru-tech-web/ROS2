# joint_emulator — Bancul cu 6 servomotoare ABB (C4)

Geamănul software al standului fizic: 3 perechi de motoare cuplate rigid = 3 articulații. Motorul A acționează; motorul B citește encoderul și aplică **impedanță** (forța inversă de opunere), adaptată la calitatea legăturii.

## Structura

```
joint_emulator/
├── joint_core.py              # impedanță, pacient virtual (catch spastic),
│                              # fizica perechii, DelayLine, SafetyGate (34 teste)
├── teleimpedance.py           # canal degradat + legea adaptivă K_ef(latență)
├── encoder_core.py            # cuantizare 4096 cpr + filtru alpha-beta-gamma
│                              # (viteză de 22× mai curată, accelerație utilizabilă)
├── drive_iface.py             # interfața unică spre fier (SimBackend azi,
│                              # ModbusBackend după identificarea drive-urilor)
├── modbus_backend.py          # schelet pymodbus pentru ABB seria 300
│                              # (CONFIG gol intenționat — din manual!)
├── sil_joint.py               # scenarii SIL: echilibru, pacient_spastic,
│                              # delay_sweep, adaptiv_vs_fix
├── plot_joint.py              # figurile principale (joint_sweep + joint_duel)
├── plot_encoder.py            # graficele encoderelor (traces + filter)
├── test_joint_core.py         # 34/34 verificări
├── nodes/
│   ├── emulator_node.py       # nodul ROS2 (pub /joint/state, sub /joint/cmd_a)
│   ├── encoder_monitor_node.py# pub /joint/kinematics + CSV ~/sar_data/encoders.csv
│   ├── operator_panel_node.py # PANOUL: slidere tau_A/K/B/link, ESTOP, grafice live
│   ├── state_to_jointstate_node.py # pod /joint/state → /joint_states (RViz)
│   └── gz_mirror_node.py      # oglinda Gazebo (publică pozițiile spre gz)
├── urdf/joint_bench.urdf      # modelul 3D al bancului
├── rviz/joint_bench.rviz      # configurația RViz
├── launch/viz_rviz.launch.py  # RViz + robot_state_publisher + pod
├── gz/
│   ├── joint_bench_world.sdf  # lumea Gazebo (model static, ancorat)
│   └── bridge_bench.yaml      # podul ROS ↔ Gazebo
├── tools/gen_bench_model.py   # generatorul de geometrie (URDF + SDF dintr-un tabel)
└── figs/                      # figuri generate
```

## Pornire completă (4 terminale)

Fiecare terminal: `source /opt/ros/jazzy/setup.bash && cd ~/ros2_ws/src/joint_emulator`

| Terminal | Comandă | Rol |
|---|---|---|
| T1 | `python3 nodes/emulator_node.py --ros-args -p adaptive:=true` | Fizica perechilor |
| T2 | `python3 nodes/encoder_monitor_node.py` | Viteză/accel + CSV |
| T3 | `ros2 launch launch/viz_rviz.launch.py` | RViz — modelul 3D se mișcă |
| T4 | `python3 nodes/operator_panel_node.py` | Panou: slidere + grafice live |

## Oglinda Gazebo (opțional, T5–T7)

```bash
# T5
gz sim -r gz/joint_bench_world.sdf
# T6
ros2 run ros_gz_bridge parameter_bridge --ros-args -p config_file:=gz/bridge_bench.yaml
# T7
python3 nodes/gz_mirror_node.py
```

## Simulare fără ROS (oricând, instant)

```bash
python3 test_joint_core.py                         # 34/34
python3 sil_joint.py echilibru                     # th=0.05 rad = tau/K
python3 sil_joint.py delay_sweep                   # tabelul E vs latență
python3 sil_joint.py adaptiv_vs_fix --ms 60        # FIX: 1242 J / ADAPTIV: 0 J
python3 plot_joint.py                              # figs/joint_sweep.png
python3 plot_encoder.py                            # figs/encoder_filter.png
```

## Lecția de arhitectură (demonstrată în figs/joint_sweep.png)

Amortizarea pe o viteză **întârziată** pompează energie → impedanța fixă explodează de la ~10 ms. Soluția: **amortizare LOCALĂ** (pe Pi, lângă drive) + **rigiditate adaptivă** prin link → pasiv (E≈0) până la 120 ms.

De aceea Raspberry Pi stă **lângă banc** (Modbus local 50–100 Hz), iar prin Zenoh/DDS călătoresc doar referințele și K.

## Reguli de siguranță pentru fier

1. Motorul B: **NUMAI mod cuplu** (torque) — niciodată poziție vs poziție pe ax rigid
2. Limită software < 10–15% din cuplul nominal + limită curent în drive
3. Watchdog 100 ms: encoder mut → cuplu zero automat
4. Primele teste pe **o singură pereche**, cu mâna departe de cuplaj
5. E-stop fizic la îndemână

## Drumul spre fier (după 19 iunie)

```
L0 (gata): nucleul pur + 34 teste
L1: poză placuță drive → CONFIG în modbus_backend.py → coast-down → J și frecarea reale
L2: echilibru pe O pereche (cuplu < 10–15%)
L3: tele-impedanță Zenoh vs DDS PE FIER → rezultatul C4
```
