# curs_ros2_interfaces -- interfete custom (msg/srv/action) pentru cursul ROS 2 (modulul M7)

## Ce face

Pachet `ament_cmake` care defineste trei interfete custom folosite in cursul ROS 2:
mesajul `Temperatura`, serviciul `AjustareTemperatura` si actiunea `Incalzire`.
Prin `rosidl_generate_interfaces` (din `CMakeLists.txt`), generatorul rosidl produce
din fisierele `.msg/.srv/.action` cod Python si C++ utilizabil de noduri. Este pachet
`ament_cmake`, nu Python pur, fiindca rosidl nu poate genera tipuri intr-un pachet pur
Python. Tipurile sunt consumate de nodurile din pachetul `curs_ros2` (M7: pub/sub
custom; M13: serviciul de ajustare a pragului).

## Cum rulezi

Un pachet de interfete nu se "ruleaza" -- se construieste, apoi tipurile sunt folosite
de alte noduri.

```bash
# 1) build-ul interfetelor
cd ~/ros2_ws
colcon build --packages-select curs_ros2_interfaces
source install/setup.bash

# 2) introspectie (verifici ca tipurile exista)
ros2 interface show curs_ros2_interfaces/msg/Temperatura
ros2 interface list | grep curs_ros2

# 3) folosire din nodurile cursului (dupa ce ai construit si curs_ros2)
ros2 run curs_ros2 m7_pub      # publica Temperatura
ros2 run curs_ros2 m7_sub      # asculta Temperatura
```

> Fiecare terminal trebuie sa fi dat `source /opt/ros/jazzy/setup.bash` si
> `source install/setup.bash` ca sa "vada" tipurile generate.

## Ce produce

Nu contine noduri si nu publica topicuri. La build produce tipurile generate
(Python + C++) in `install/`, disponibile altor pachete:

- `curs_ros2_interfaces/msg/Temperatura` -- `float64 valoare`, `string status`
  ("NORMAL" / "ATENTIE" / "CRITIC")
- `curs_ros2_interfaces/srv/AjustareTemperatura` -- cerere: `float64 prag_nou`;
  raspuns: `bool succes`, `float64 prag_anterior`, `string mesaj`
- `curs_ros2_interfaces/action/Incalzire` -- goal: `float64 tinta`;
  result: `bool atins`, `float64 temperatura_finala`; feedback: `float64 temperatura_curenta`

## Dependinte

Din `package.xml` si `CMakeLists.txt`:

- build: `ament_cmake`, `rosidl_default_generators`
- runtime: `rosidl_default_runtime`
- `member_of_group`: `rosidl_interface_packages`
- consumat de: pachetul `curs_ros2` (nodurile `m7_pub`, `m7_sub`, `m13_monitor`)
