# rehab_exo_description — Exoscheletul de reabilitare

Geamănul virtual al bancului cu 6 servomotoare ABB (`joint_emulator`): 3 articulații = șold / genunchi / gleznă pe un picior. Pachetul ROS2 complet cu URDF, launch-uri, failsafe și interfața de control.

## Structura

```
rehab_exo_description/
├── urdf/
│   └── rehab_exo.urdf          # modelul complet (3 articulații + senzori)
├── launch/
│   ├── display.launch.py       # RViz cu robot_state_publisher
│   ├── telerehab.launch.py     # lansatorul de tele-reabilitare
│   └── failsafe.launch.py      # monitorul de siguranță
├── config/
│   └── joint_limits.yaml       # limitele articulațiilor (grad/Nm)
├── scripts/
│   ├── joint_controller.py     # controlerul de impedanță per articulație
│   ├── failsafe_node.py        # watchdog + limită cuplu + RTH
│   └── teleop_bridge.py        # podul operator → articulații
└── test/
    └── test_failsafe.py        # testul 6a (pending)
```

## Articulațiile

| Articulație | Joint name | Limită unghi | Cuplu max |
|---|---|---|---|
| Șold | `hip_joint` | ±45° | 15 Nm |
| Genunchi | `knee_joint` | 0°–120° | 12 Nm |
| Gleznă | `ankle_joint` | ±30° | 8 Nm |

## Pornire

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws

# vizualizare URDF în RViz
ros2 launch rehab_exo_description display.launch.py

# tele-reabilitare completă
ros2 launch rehab_exo_description telerehab.launch.py

# doar failsafe-ul (monitorizare)
ros2 launch rehab_exo_description failsafe.launch.py
```

## Topicuri principale

| Topic | Descriere |
|---|---|
| `/rehab/joint_cmd` | Comandă de impedanță `{joint, k, b, th0}` |
| `/rehab/joint_state` | Starea articulațiilor (th, om, tau) |
| `/rehab/failsafe` | Starea watchdog-ului (armed/tripped) |
| `/teleop/linkstate` | Degradarea legăturii (același format ca sar_swarm) |

## Legătura cu joint_emulator
`rehab_exo_description` = **stratul de descriere ROS** (URDF, launch, topicuri).
`joint_emulator` = **stratul de fizică și control** (impedanță, encodere, tele-impedanță).
Pe fierul real (bancul ABB), `joint_emulator` rulează pe Raspberry Pi lângă drive-uri, iar `rehab_exo_description` rulează pe laptopul de comandă — exact arhitectura demonstrată de `figs/joint_sweep.png`.

## Testul 6a (pending)
```bash
cd ~/ros2_ws/src/rehab_exo_description
python3 test/test_failsafe.py    # de completat
```
