# Documentație de utilizare — `servo_control`

## 1. Descriere

`servo_control` este un pachet ROS 2 Jazzy pentru controlul din tastatură al
articulației `shaft_joint` a modelului Gazebo `Servomotor`.

Pachetul conține:

- nodul ROS 2 `servo_teleop`;
- lumea Gazebo `lab_world.sdf`;
- modelul `Servomotor` și mesh-urile sale;
- bridge-ul dintre ROS 2 și Gazebo;
- watchdog pentru oprirea comenzii după pierderea inputului;
- teste unitare, teste de stil și verificări pentru resursele Gazebo.

Topic-ul implicit de comandă este:

```text
/model/servo1/joint/shaft_joint/cmd_vel
```

Tipul mesajului ROS este:

```text
std_msgs/msg/Float64
```

Valoarea reprezintă viteza unghiulară în `rad/s`:

- valoare pozitivă: sens orar;
- valoare negativă: sens antiorar;
- `0.0`: oprire.

## 2. Cerințe

Configurația folosită pentru dezvoltare și testare:

- Ubuntu;
- ROS 2 Jazzy;
- Gazebo Sim 8;
- `ros_gz_sim`;
- `ros_gz_bridge`;
- Python 3.12;
- `colcon` și `rosdep`.

Pentru verificarea instalării ROS 2:

```bash
ls /opt/ros/jazzy/setup.bash
ros2 --help
gz sim --versions
```

## 3. Build inițial

Comenzile se rulează într-un terminal Ubuntu deschis cu `Ctrl+Alt+T`:

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select servo_control --symlink-install
source install/setup.bash
```

După orice modificare în cod, model, launch sau configurarea pachetului, se
repetă cel puțin:

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select servo_control --symlink-install
source install/setup.bash
```

Comanda `source install/setup.bash` trebuie executată în fiecare terminal nou.

## 4. Pornirea simulării

### Terminalul 1 — Gazebo și bridge-ul

Deschide un terminal Ubuntu cu `Ctrl+Alt+T` și rulează:

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 launch servo_control servo_launch.py
```

Launch-ul:

1. găsește lumea instalată în `share/servo_control/worlds`;
2. adaugă modelul împachetat în calea de resurse Gazebo;
3. pornește Gazebo Sim;
4. pornește bridge-ul ROS→Gazebo pentru comanda de viteză;
5. închide restul proceselor când Gazebo este închis.

Gazebo trebuie să apară într-o fereastră desktop separată. Fișierul
`servo_launch.py` nu se rulează cu butonul **Run Python** din VS Code și nu se
pornește cu `python3`.

Comanda corectă este întotdeauna:

```bash
ros2 launch servo_control servo_launch.py
```

### Terminalul 2 — controlul din tastatură

Deschide un al doilea terminal Ubuntu:

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
ros2 run servo_control servo_teleop
```

Nodul trebuie rulat într-un terminal real, deoarece citește direct tastele.

## 5. Comenzi din tastatură

| Tastă | Acțiune |
|---|---|
| `DREAPTA` | Selectează sensul orar |
| `STÂNGA` | Selectează sensul antiorar |
| `SUS` | Crește viteza selectată |
| `JOS` | Scade viteza selectată |
| `SPATIU` | Publică imediat viteza zero |
| `Q` | Oprește servoul și închide nodul |
| `Ctrl-C` | Oprește servoul și închide nodul |

Pentru mișcare continuă, ține apăsată săgeata de direcție. Repetarea automată
a tastei reîmprospătează watchdog-ul. După eliberarea tastei, comanda expiră
implicit după `0.75 s`, iar nodul publică viteza `0.0`.

## 6. Parametri ROS 2

| Parametru | Implicit | Semnificație |
|---|---:|---|
| `command_topic` | `/model/servo1/joint/shaft_joint/cmd_vel` | Topic-ul comenzilor |
| `publish_rate` | `20.0` | Frecvența publicării în Hz |
| `initial_speed` | `1.0` | Viteza selectată la pornire, în rad/s |
| `speed_step` | `0.5` | Incrementul modificării vitezei |
| `min_speed` | `0.5` | Limita inferioară a vitezei selectate |
| `max_speed` | `10.0` | Limita superioară a vitezei selectate |
| `command_timeout` | `0.75` | Timeout-ul watchdog-ului, în secunde |

Exemplu de pornire cu parametri personalizați:

```bash
ros2 run servo_control servo_teleop --ros-args \
  -p command_timeout:=1.5 \
  -p publish_rate:=30.0 \
  -p initial_speed:=1.5 \
  -p speed_step:=0.25 \
  -p min_speed:=0.5 \
  -p max_speed:=6.0
```

Pentru afișarea parametrilor nodului pornit:

```bash
ros2 param list /servo_teleop
ros2 param get /servo_teleop command_timeout
ros2 param get /servo_teleop max_speed
```

`command_timeout:=0.0` dezactivează watchdog-ul. Această valoare este
recomandată numai pentru depanare, nu pentru utilizarea normală.

## 7. Monitorizare și diagnostic

### Terminalul 3 — mesajele ROS

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
ros2 topic echo /model/servo1/joint/shaft_joint/cmd_vel
```

În timpul mișcării trebuie observate valori pozitive sau negative. După
expirarea watchdog-ului, apăsarea `SPATIU`, `Q` sau `Ctrl-C`, trebuie observată
valoarea:

```text
data: 0.0
```

### Verificarea conexiunilor și a QoS-ului

```bash
ros2 topic info \
  /model/servo1/joint/shaft_joint/cmd_vel \
  --verbose
```

Când simularea și teleoperarea rulează, sunt așteptate:

- un publisher: `servo_teleop`;
- un subscriber: `servo_bridge`;
- QoS reliable și volatile;
- coadă de publicare cu adâncimea `1`.

### Verificarea topicului Gazebo

```bash
gz topic -e \
  -t /model/servo1/joint/shaft_joint/cmd_vel
```

### Verificarea nodurilor și topicurilor

```bash
ros2 node list
ros2 topic list
gz topic -l
```

## 8. Argumentele launch

Pentru lista argumentelor disponibile:

```bash
ros2 launch servo_control servo_launch.py --show-args
```

Pentru a porni o altă lume SDF:

```bash
ros2 launch servo_control servo_launch.py \
  world:=/cale/absoluta/catre/lume.sdf
```

Pentru schimbarea topicului bridge-ului:

```bash
ros2 launch servo_control servo_launch.py \
  command_topic:=/topic/personalizat
```

În acest caz, nodul de teleoperare trebuie pornit cu același topic:

```bash
ros2 run servo_control servo_teleop --ros-args \
  -p command_topic:=/topic/personalizat
```

## 9. Rularea testelor

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
source install/setup.bash
colcon test \
  --packages-select servo_control \
  --event-handlers console_direct+
colcon test-result --verbose
```

Rezultatul de referință pentru versiunea curentă:

```text
Summary: 19 tests, 0 errors, 0 failures, 0 skipped
```

Testele acoperă:

- schimbarea direcției;
- limitele vitezei;
- păstrarea sensului la modificarea vitezei;
- oprirea și ieșirea;
- expirarea watchdog-ului;
- validarea parametrilor;
- existența lumii, modelului și mesh-urilor;
- copyright, `flake8` și `pep257`.

## 10. Depanare

### `Package 'servo_control' not found`

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select servo_control --symlink-install
source install/setup.bash
ros2 pkg prefix servo_control
```

Ultima comandă trebuie să afișeze o cale din:

```text
/home/ubuntu/ros2_ws/install/servo_control
```

### `servo_launch.py was not found`

Reconstruiește pachetul și încarcă din nou workspace-ul:

```bash
cd ~/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --packages-select servo_control --symlink-install
source install/setup.bash
ros2 launch servo_control servo_launch.py --show-args
```

### Teleoperarea raportează că intrarea nu este un terminal

Nu porni nodul dintr-un task fără TTY și nu folosi butonul Run din VS Code.
Deschide un terminal Ubuntu cu `Ctrl+Alt+T` și rulează `ros2 run` acolo.

### Gazebo nu afișează modelul

Verifică dacă resursele sunt instalate:

```bash
ls ~/ros2_ws/install/servo_control/share/servo_control/worlds
ls ~/ros2_ws/install/servo_control/share/servo_control/models/Servomotor
ls ~/ros2_ws/install/servo_control/share/servo_control/models/Servomotor/meshes
```

Apoi verifică dacă topicul modelului există:

```bash
gz topic -l | grep servo1
```

### Servomotorul nu răspunde la taste

Verifică, în ordine:

```bash
ros2 node list
ros2 topic info /model/servo1/joint/shaft_joint/cmd_vel --verbose
ros2 topic echo /model/servo1/joint/shaft_joint/cmd_vel
gz topic -l | grep shaft_joint
```

Dacă topicul ROS nu are publisher, nodul `servo_teleop` nu rulează. Dacă nu are
subscriber, bridge-ul nu rulează sau topicul launch-ului este diferit.

### Gazebo închis, dar procese rămase active

În mod normal launch-ul le închide automat. Verificare:

```bash
pgrep -af 'gz sim|parameter_bridge|servo_teleop'
```

Oprește nodurile din terminalele în care rulează folosind `Ctrl-C`.

## 11. Siguranță și limitări

La ieșire controlată, nodul publică viteza zero de trei ori înainte de oprire.
Watchdog-ul oprește comanda când inputul de tastatură nu mai este actualizat.

Aceste mecanisme nu pot gestiona un `SIGKILL`, pierderea alimentării sau
căderea completă a calculatorului. Pentru conectarea la un servomotor real
trebuie implementat și un watchdog independent în controllerul hardware.

## 12. Structura principală

```text
servo_control/
├── launch/servo_launch.py
├── models/Servomotor/
│   ├── meshes/
│   ├── model.config
│   └── Servomotor.sdf
├── servo_control/
│   ├── servo_teleop.py
│   └── teleop_core.py
├── test/
├── worlds/lab_world.sdf
├── DOCUMENTATIE_UTILIZARE.md
├── LICENSE
├── package.xml
├── README.md
└── setup.py
```
