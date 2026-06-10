# ROS2 — Workspace de doctorat (ROS 2 Jazzy)

Workspace-ul complet al proiectelor de cercetare: control în timp real al sistemelor robotice (ROS 2 Jazzy, Ubuntu 24.04). Acest depozit corespunde directorului `ros2_ws/src/` — artefactele de build (`build/`, `install/`, `log/`) se regenerează local și nu se versionează.

## Pachetele

| Pachet | Conținut | Detalii |
|---|---|---|
| [`rehab_exo_description/`](rehab_exo_description/) | **Sistem robotic de recuperare locomotorie**: scaun medical cu 6 servomotoare (șold/genunchi/gleznă), pacient integrat, 12 exerciții + 4 sesiuni, control prin traiectorii cosinus, RViz + Gazebo (ros2_control) | vezi [README-ul propriu](rehab_exo_description/README.md) — documentația completă |
| [`servo_control/`](servo_control/) | Motor simulat în Gazebo cu comenzi din tastatură (rotație și viteză) — prima aplicație a proiectului | `ros2 launch servo_control servo_launch.py` |
| [`curs_ros2/`](curs_ros2/) | Pachetul de lucru din cursul ROS 2 Jazzy + Gazebo Harmonic (noduri, launch, parametri) | material de învățare |

## Structura

```text
ROS2/  (= ros2_ws/src)
├── rehab_exo_description/   sistemul de reabilitare (URDF + control + launch + Gazebo)
├── servo_control/           motorul simulat (comenzi tastatură)
└── curs_ros2/               exercițiile cursului ROS 2
```

## Instalare pe o mașină nouă

```bash
# cerințe: Ubuntu 24.04 + ROS 2 Jazzy (https://docs.ros.org/en/jazzy/Installation.html)
mkdir -p ~/ros2_ws && cd ~/ros2_ws
git clone https://github.com/alexandru-tech-web/ROS2.git src

# dependințele pachetelor:
sudo apt install -y ros-jazzy-joint-state-publisher-gui ros-jazzy-rviz2 ros-jazzy-xacro \
                    ros-jazzy-ros-gz ros-jazzy-gz-ros2-control \
                    ros-jazzy-ros2-control ros-jazzy-ros2-controllers

colcon build
source install/setup.bash
```

## Demo rapid

```bash
# sesiune completă de exerciții pe sistemul de reabilitare (RViz):
ros2 launch rehab_exo_description exercitii_combinat.launch.py

# aceeași mișcare, cu fizică, în Gazebo:
ros2 launch rehab_exo_description gazebo.launch.py
```

## Context

Depozit dezvoltat în cadrul cercetării doctorale privind **controlul la distanță în timp real al sistemelor robotice** (middleware ROS 2 / Zenoh, robotică SAR și de reabilitare). Licență: Apache-2.0 (per pachet).
