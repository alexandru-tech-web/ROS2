# curs_ros2_interfaces

Pachet `ament_cmake` care declara trei interfete custom -- mesajul `Temperatura`,
serviciul `AjustareTemperatura` si actiunea `Incalzire` -- si le compileaza prin
`rosidl` in cod Python si C++ utilizabil de noduri. Este o componenta educationala
a ecosistemului didactic ROS 2 (modulul M7); nu face parte din coloana stiintifica
a tezei si nu contine algoritmi de cercetare. Rolul ei este sa arate contractul de
date dintre noduri si modul corect de a-l declara.

## Scop

Pachetul defineste tipurile de date schimbate de nodurile cursului `curs_ros2`:

- `msg/Temperatura` -- o citire de temperatura impreuna cu statusul ei clasificat,
  intr-un singur mesaj coerent;
- `srv/AjustareTemperatura` -- contractul cerere/raspuns pentru schimbarea la cald
  a pragului de atentie al monitorului;
- `action/Incalzire` -- contractul goal/result/feedback pentru o incalzire pana la
  o tinta (definita ca exemplu didactic; vezi nota din sectiunea Arhitectura).

Justificarea tipului de pachet (din `package.xml`): `rosidl` nu poate genera tipuri
intr-un pachet pur Python, deci interfetele custom stau obligatoriu intr-un pachet
`ament_cmake` separat.

## Arhitectura

Pachetul nu contine noduri Python, nu publica topicuri si nu ruleaza nimic. Este o
DECLARATIE de tipuri: trei fisiere de interfata plus reteta de generare din
`CMakeLists.txt`.

Generarea: in `CMakeLists.txt`, apelul `rosidl_generate_interfaces(${PROJECT_NAME}
...)` enumera cele trei fisiere (`msg/Temperatura.msg`, `srv/AjustareTemperatura.srv`,
`action/Incalzire.action`) si lasa `rosidl` sa produca, la build, clasele Python si
C++ corespunzatoare. `package.xml` declara `member_of_group rosidl_interface_packages`,
plus `rosidl_default_generators` (build) si `rosidl_default_runtime` (runtime).

Consumatori reali (verificati prin grep in `curs_ros2/curs_ros2/`):

| Interfata | Nod consumator (fisier) | Import verificat |
|-----------|-------------------------|------------------|
| `msg/Temperatura` | `m7_pub_custom.py`, `m7_sub_custom.py` | `from curs_ros2_interfaces.msg import Temperatura` |
| `srv/AjustareTemperatura` | `m13_monitor.py` | `from curs_ros2_interfaces.srv import AjustareTemperatura` |
| `action/Incalzire` | niciunul | nicio referinta in `curs_ros2/curs_ros2/*.py` |

Nodurile M7 sunt mapate in `curs_ros2/setup.py` la executabilele `m7_pub` si `m7_sub`
(fisierele se numesc `m7_pub_custom.py` / `m7_sub_custom.py`); pentru M13 fisierul si
executabilul coincid (`m13_monitor`).

Nota de onestitate asupra actiunii `Incalzire`: tipul este definit si compilat, dar
niciun nod din `curs_ros2` nu il consuma -- modulul de actiuni al cursului
(`m6_action_server.py` / `m6_action_client.py`) foloseste tipul standard `Fibonacci`,
nu `Incalzire`. `Incalzire` este pastrata ca exemplu didactic. TODO: de confirmat daca
se doreste un demonstrator care chiar foloseste `Incalzire` (ar cere un nod
ActionServer/ActionClient nou in `curs_ros2`).

## Fisiere

| Fisier | Rol (extras din continutul real) |
|--------|----------------------------------|
| `package.xml` | manifest `ament_cmake`; `build_depend` pe `rosidl_default_generators`, `exec_depend` pe `rosidl_default_runtime`, `member_of_group rosidl_interface_packages`; versiune `0.1.0`, licenta `Apache-2.0` |
| `CMakeLists.txt` | reteta de generare: `rosidl_generate_interfaces` cu cele 3 fisiere; `ament_export_dependencies(rosidl_default_runtime)` |
| `msg/Temperatura.msg` | mesaj: `float64 valoare` (grade C), `string status` (NORMAL / ATENTIE / CRITIC) |
| `srv/AjustareTemperatura.srv` | serviciu: cerere `float64 prag_nou`; raspuns `bool succes`, `float64 prag_anterior`, `string mesaj` |
| `action/Incalzire.action` | actiune: goal `float64 tinta`; result `bool atins`, `float64 temperatura_finala`; feedback `float64 temperatura_curenta` |
| `README.md` | acest document |

Pachetul NU are `setup.py`, `setup.cfg`, `launch/`, noduri Python sau teste. In
consecinta NU exista `console_scripts`/entry_points si NU exista
`ros2 run curs_ros2_interfaces ...`.

## Sintaxe de rulare

Un pachet de interfete nu se ruleaza, ci se construieste, iar tipurile sunt apoi
folosite de alte noduri.

```bash
# 1) build-ul interfetelor (INTAI acest pachet, inainte de curs_ros2)
cd ~/ros2_ws
colcon build --packages-select curs_ros2_interfaces --symlink-install
source /opt/ros/jazzy/setup.bash
source install/setup.bash

# 2) introspectie -- confirmi ca tipurile generate exista
ros2 interface list | grep curs_ros2_interfaces
ros2 interface show curs_ros2_interfaces/msg/Temperatura
ros2 interface show curs_ros2_interfaces/srv/AjustareTemperatura
ros2 interface show curs_ros2_interfaces/action/Incalzire

# 3) folosire reala -- din nodurile cursului (necesita si build la curs_ros2)
colcon build --packages-select curs_ros2
source install/setup.bash
ros2 run curs_ros2 m7_pub        # publica msg/Temperatura pe /temperatura_custom
ros2 run curs_ros2 m7_sub        # asculta /temperatura_custom
ros2 run curs_ros2 m13_monitor   # expune serviciul ajusteaza_prag
ros2 service call /ajusteaza_prag curs_ros2_interfaces/srv/AjustareTemperatura "{prag_nou: 35.0}"
```

Capcane (verificate in cod):
- NU exista `ros2 run curs_ros2_interfaces ...`: pachetul nu inregistreaza executabile.
- `from curs_ros2_interfaces.msg import Temperatura` esueaza fara
  `source install/setup.bash` in terminalul curent, sau daca ai construit `curs_ros2`
  inainte de `curs_ros2_interfaces`.
- `action/Incalzire` se poate introspecta, dar nu are nod consumator in curs.

## Parametri si topicuri

Pachetul nu contine noduri, deci nu declara parametri si nu publica/subscrie topicuri
el insusi. Topicurile si serviciul de mai jos apartin nodurilor consumatoare din
`curs_ros2` (citate aici doar ca destinatie a tipurilor):

- topic `/temperatura_custom`, tip `curs_ros2_interfaces/msg/Temperatura` -- publicat de
  `m7_pub_custom.py` (`create_publisher(Temperatura, '/temperatura_custom', 10)`),
  subscris de `m7_sub_custom.py`;
- service `ajusteaza_prag`, tip `curs_ros2_interfaces/srv/AjustareTemperatura` -- expus
  de `m13_monitor.py` (numele serviciului in cod este `ajusteaza_prag`; ROS il prezinta
  ca `/ajusteaza_prag` la rulare).

Definitiile exacte ale campurilor (cu unitatile din comentariile sursei):

`msg/Temperatura`
```
float64 valoare      # temperatura in grade Celsius
string  status       # NORMAL / ATENTIE / CRITIC
```

`srv/AjustareTemperatura`  (cerere `---` raspuns)
```
float64 prag_nou         # noul prag de atentie cerut (grade C)
---
bool    succes           # true daca pragul a fost acceptat
float64 prag_anterior    # ce valoare avea pragul inainte
string  mesaj            # explicatie lizibila (de ce a reusit/esuat)
```

`action/Incalzire`  (goal `---` result `---` feedback)
```
float64 tinta                 # temperatura tinta (grade C)
---
bool    atins                 # true daca tinta a fost atinsa
float64 temperatura_finala    # ultima temperatura masurata
---
float64 temperatura_curenta   # temperatura masurata acum
```
