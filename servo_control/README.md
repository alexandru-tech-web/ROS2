# servo_control — Motorul demonstrator în Gazebo

Stratul de **demonstrație aplicativă** al tezei: motor ROS2 cu control de rotație și viteză prin tastatură, rulând în Gazebo. Rol în articol: *application demonstration layer* (distinct de microbenchmark-ul din `c1_benchmark`).

## Structura

```
servo_control/
├── urdf/
│   └── servo.urdf              # modelul motorului (cilindru + ax rotitor)
├── launch/
│   └── servo_gazebo.launch.py  # Gazebo + robot_state_publisher + teleop
├── scripts/
│   ├── servo_node.py           # nodul de control (viteza + rotatie)
│   └── keyboard_teleop.py      # controlul prin tastatura
└── worlds/
    └── servo_world.sdf         # lumea Gazebo simplă
```

## Pornire

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws

# porneste Gazebo cu motorul
ros2 launch servo_control servo_gazebo.launch.py

# intr-un terminal separat — controlul prin tastatura
ros2 run servo_control keyboard_teleop.py
```

## Taste de control

| Tasta | Acțiune |
|---|---|
| `W` / `S` | Crește / scade viteza |
| `A` / `D` | Rotație stânga / dreapta |
| `SPACE` | Stop (viteză zero) |
| `Q` | Ieșire |

## Topicuri

| Topic | Tip | Descriere |
|---|---|---|
| `/servo/cmd_vel` | Twist | Comanda de viteză/rotație |
| `/servo/joint_state` | JointState | Starea motorului (poziție, viteză) |

## Relația cu restul proiectului

```
keyboard_teleop → /servo/cmd_vel → servo_node → Gazebo
                                              ↓
                                     /servo/joint_state
```

Motorul din `servo_control` = demonstratorul vizual al conceptului. Fizica detaliată de impedanță și tele-impedanță trăiește în `joint_emulator`. Benchmarkul middleware trăiește în `c1_benchmark`.

## Build

```bash
cd ~/ros2_ws
colcon build --packages-select servo_control --symlink-install
source install/setup.bash
```
