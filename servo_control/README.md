# servo_control

Nod ROS 2 de teleoperare a unui servomotor: comanda din tastatura (sens si viteza)
o articulatie rotativa a unui model Gazebo. Pachet ament_python (build_type
`ament_python`, vezi package.xml), demonstrator istoric pentru linia de actuatoare
C4 a tezei (teleoperare in timp real peste retele degradate). Statut: arhiva / demo.

## Scop

Nodul `servo_teleop` publica o comanda de viteza unghiulara catre articulatia
`shaft_joint` a modelului `servo1`, citita de la tastatura (sageti, SPATIU, Q) si
republicata periodic la 20 Hz. Scopul este demonstrarea reproductibila a lantului
operator -> rclpy -> punte -> simulator, nu o solutie production-grade.

Nota: pachetul NU urmeaza tiparul de fier al proiectului (nucleu pur + `_selftest`
-> nod ROS subtire -> SIL). Nu exista un modul-nucleu fara ROS si nici `_selftest`;
intregul cod (citire tastatura, stare, publicare ROS) sta in `servo_teleop.py`.

## Fisiere

- `servo_control/servo_teleop.py` -- nod (clasa `ServoTeleop(Node)`) care citeste
  tastatura si publica viteza pe topic. Constante din cod: `SPEED_STEP=0.5`,
  `MAX_SPEED=10.0`, `MIN_SPEED=0.5` rad/s; timer la 0.05 s (20 Hz).
- `launch/servo_launch.py` -- porneste `gz sim` pe lumea
  `~/.gz/worlds/lab_world.sdf`, apoi `ros_gz_bridge/parameter_bridge` la +5 s,
  apoi `servo_teleop` intr-o fereastra `xterm` la +6 s.
- `worlds/lab_world.sdf` -- lumea Gazebo folosita de launch.

## Sintaxe de rulare

```bash
# build
cd ~/ros2_ws && colcon build --packages-select servo_control --symlink-install
source install/setup.bash

# rulare nod (entry_point real din setup.py)
ros2 run servo_control servo_teleop

# rulare integrata (gz sim + punte + teleop in xterm)
ros2 launch servo_control servo_launch.py
```

Comenzi tastatura (din docstring si cod): sageata DREAPTA = sens orar, sageata
STANGA = sens antiorar, sageata SUS = creste viteza, sageata JOS = scade viteza,
SPATIU = stop, Q = iesire. Nodul nu accepta argumente CLI (fara argparse).

## Parametri si topicuri

- Publisher: topic `/model/servo1/joint/shaft_joint/cmd_vel`, tip
  `std_msgs/msg/Float64`, coada 10 (servo_teleop.py, linia 56). Mesajul poarta un
  singur camp `data` (viteza, rad/s): pozitiv = orar, negativ = antiorar.
- Fara subscriberi, fara servicii, fara `declare_parameter` (verificat in cod).

Nota: launch-ul citeste lumea din `~/.gz/worlds/lab_world.sdf` (cale fixa via
`os.path.expanduser`), nu din `share/`; copierea fisierului acolo este necesara.
TODO: de confirmat modelul `model://Servomotor` inclus de lume -- nu se afla in
acest pachet si nu e declarat ca dependenta.
