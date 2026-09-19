# servo_control

Pachet ROS 2 Jazzy pentru teleoperarea din tastatura a articulatiei
`shaft_joint` din modelul Gazebo `Servomotor`. Pachetul include lumea, modelul,
mesh-urile, bridge-ul ROS-Gazebo si un nod cu oprire fail-safe.

Ghidul complet de instalare, rulare și depanare este disponibil în
[`DOCUMENTATIE_UTILIZARE.md`](DOCUMENTATIE_UTILIZARE.md).

## Functionalitati

- comanda semnata de viteza pe
  `/model/servo1/joint/shaft_joint/cmd_vel`;
- watchdog de inactivitate, implicit `0.75 s`;
- trei publicari cu viteza zero la iesire normala, `Ctrl-C` sau `SIGTERM`;
- QoS `KEEP_LAST(1)`, reliable si volatile;
- parametri ROS pentru topic, frecventa si limitele vitezei;
- lume si model Gazebo instalate in `share/servo_control`;
- logica tastelor separata de ROS si acoperita prin teste unitare.

## Build si teste

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select servo_control --symlink-install
source install/setup.bash
colcon test --packages-select servo_control --event-handlers console_direct+
colcon test-result --verbose
```

## Rulare si vizualizare

Terminalul 1 porneste Gazebo si bridge-ul:

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch servo_control servo_launch.py
```

Launch-ul elimina automat variabilele GUI mostenite de la aplicatii Snap
(de exemplu VS Code Snap), care pot incarca biblioteci incompatibile in Gazebo.

Terminalul 2 porneste teleoperarea intr-un TTY real:

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run servo_control servo_teleop
```

Taste:

- `STANGA` / `DREAPTA`: sens antiorar / orar;
- `SUS` / `JOS`: crestere / scadere viteza;
- `SPATIU`: stop imediat;
- `Q` sau `Ctrl-C`: stop si iesire.

Pentru miscare continua se tine apasata sageata de directie. La eliberare,
watchdog-ul publica viteza zero dupa timeout.

## Parametri

```bash
ros2 run servo_control servo_teleop --ros-args \
  -p command_timeout:=1.0 \
  -p publish_rate:=30.0 \
  -p initial_speed:=1.5 \
  -p speed_step:=0.25 \
  -p min_speed:=0.5 \
  -p max_speed:=8.0
```

`command_timeout:=0.0` dezactiveaza watchdog-ul si este recomandat numai
pentru depanare. Parametrii sunt cititi la pornirea nodului.

Watchdog-ul din acest pachet acopera lipsa inputului, `Ctrl-C`, `SIGTERM` si
iesirile controlabile. Un `SIGKILL`, pierderea alimentarii sau caderea completa
a calculatorului nu pot fi tratate de acelasi proces; pentru hardware real este
necesar si un watchdog in controllerul servomotorului.

## Diagnostic

Intr-un al treilea terminal se poate observa comanda publicata:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 topic echo /model/servo1/joint/shaft_joint/cmd_vel
```

Lista argumentelor launch:

```bash
ros2 launch servo_control servo_launch.py --show-args
```
