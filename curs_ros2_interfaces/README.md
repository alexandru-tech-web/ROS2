# curs_ros2_interfaces -- interfete custom (msg/srv/action) pentru cursul ROS 2 (modulul M7)

Pachet `ament_cmake` care declara trei interfete custom -- mesajul `Temperatura`,
serviciul `AjustareTemperatura` si actiunea `Incalzire` -- si le compileaza prin
`rosidl` in cod Python si C++ utilizabil de noduri. Componenta este pur educationala
(ecosistemul didactic ROS 2), nu face parte din coloana stiintifica C1-C4 si nu
contine algoritmi de cercetare; rolul ei este sa arate contractul de date intre
noduri si modul corect de a-l declara.

## 1. Scop

Pachetul defineste tipurile de date schimbate de nodurile cursului `curs_ros2`:

- `msg/Temperatura` -- o citire de temperatura impreuna cu statusul ei clasificat,
  ca un singur mesaj coerent (nu doua topice separate care s-ar putea desincroniza);
- `srv/AjustareTemperatura` -- contractul cerere/raspuns pentru schimbarea la cald a
  pragului de atentie al monitorului;
- `action/Incalzire` -- contractul goal/result/feedback pentru o incalzire pana la o
  tinta (interfata definita ca exemplu didactic; vezi nota de la sectiunea 3).

Justificarea tipului de pachet: `rosidl` (generatorul de cod din `.msg/.srv/.action`)
nu poate produce tipuri intr-un pachet pur Python, deci interfetele custom stau
obligatoriu intr-un pachet `ament_cmake` separat. Aceasta separare este ea insasi
lectia modulului M7.

## 2. Context si loc in arhitectura

Problema: doua noduri care comunica trebuie sa fie de acord pe EXACT acelasi tip de
date. Tipurile standard (`std_msgs`, `example_interfaces`) acopera cazurile simple,
dar de indata ce vrei un mesaj cu campuri proprii (de exemplu valoare + status intr-un
singur pachet), ai nevoie de un tip custom. Tipul custom traieste intr-un pachet de
interfete dedicat, construit inaintea pachetelor care il consuma.

Locul in arhitectura ecosistemului didactic:

```
curs_ros2_interfaces  (ament_cmake, ACEST pachet)
        |  rosidl_generate_interfaces -> cod Python + C++
        v
curs_ros2  (ament_python)
   |  package.xml:  <depend>curs_ros2_interfaces</depend>
   |
   +-- m7_pub_custom / m7_sub_custom  --(import msg/Temperatura)-->  topic /temperatura_custom
   +-- m13_monitor                    --(import srv/AjustareTemperatura)--> service ajusteaza_prag
```

Lantul de dependenta este strict: `curs_ros2_interfaces` se construieste primul,
apoi `curs_ros2` il importa. Daca ordinea sau `source`-ul lipsesc, importul
`from curs_ros2_interfaces.msg import Temperatura` esueaza la rulare.

## 3. Arhitectura

Pachetul nu contine noduri, nu publica topicuri si nu ruleaza nimic. El este o
DECLARATIE de tipuri: trei fisiere de interfata + reteta de generare din
`CMakeLists.txt`.

### 3.1 Generarea

In `CMakeLists.txt`, apelul `rosidl_generate_interfaces(${PROJECT_NAME} ...)`
enumera cele trei fisiere si lasa `rosidl` sa produca, la build, clasele
corespunzatoare in Python (`curs_ros2_interfaces.msg.Temperatura`,
`curs_ros2_interfaces.srv.AjustareTemperatura`,
`curs_ros2_interfaces.action.Incalzire`) si echivalentele C++. `package.xml`
declara `member_of_group rosidl_interface_packages` (obligatoriu) si dependenta
de `rosidl_default_generators` (build) / `rosidl_default_runtime` (runtime).

### 3.2 Consumatorii reali (din pachetul curs_ros2)

| Interfata | Nod consumator | Punct de atasare | Verificat in cod |
|-----------|----------------|------------------|------------------|
| `msg/Temperatura` | `m7_pub_custom.py`, `m7_sub_custom.py` | topic `/temperatura_custom` | `from curs_ros2_interfaces.msg import Temperatura` |
| `srv/AjustareTemperatura` | `m13_monitor.py` | service `ajusteaza_prag` | `from curs_ros2_interfaces.srv import AjustareTemperatura` |
| `action/Incalzire` | (niciunul) | -- | nicio referinta in `curs_ros2/curs_ros2/*.py` |

Coloana "Nod consumator" da numele FISIERULUI de nod din `curs_ros2/curs_ros2/`.
Numele de executabil inregistrat (cel din `ros2 run`) difera pentru M7: fisierele
`m7_pub_custom.py` / `m7_sub_custom.py` sunt mapate in `setup.py` la executabilele
`m7_pub` / `m7_sub` (verificat: `ros2 pkg executables curs_ros2` listeaza
`m7_pub`, `m7_sub`, `m13_monitor`). Pentru M13 numele fisierului si al
executabilului coincid (`m13_monitor`). De aceea sectiunea 6 ruleaza
`ros2 run curs_ros2 m7_pub`, nu `m7_pub_custom`.

Nota de onestitate asupra actiunii `Incalzire`: tipul este definit, compilat si
introspectabil (`ros2 interface show curs_ros2_interfaces/action/Incalzire`
functioneaza), DAR niciun nod din `curs_ros2` nu il consuma. Modulul de actiuni al
cursului (`m6_action_server` / `m6_action_client`) foloseste tipul standard
`example_interfaces/action/Fibonacci`, nu `Incalzire`. `Incalzire` este pastrata ca
exemplu didactic de scriere a unei actiuni custom (documentat in
`curs_ros2/docs/07_interfete_custom.md`). Marcaj: TODO -- daca se doreste un
demonstrator care chiar foloseste `Incalzire`, trebuie adaugat un nod
ActionServer/ActionClient in `curs_ros2`.

## 4. Inventar fisiere

| Fisier | Rol | Cum se verifica |
|--------|-----|-----------------|
| `package.xml` | manifest `ament_cmake`; declara `rosidl_default_generators`/`_runtime` si `member_of_group rosidl_interface_packages` | `colcon build` reuseste; grep `member_of_group` |
| `CMakeLists.txt` | reteta de generare: `rosidl_generate_interfaces` cu cele 3 fisiere | inspectie; build produce `msg/`, `srv/`, `action/` in `install/` |
| `msg/Temperatura.msg` | mesaj: `float64 valoare`, `string status` | `ros2 interface show curs_ros2_interfaces/msg/Temperatura` |
| `srv/AjustareTemperatura.srv` | serviciu: cerere `float64 prag_nou`; raspuns `bool succes`, `float64 prag_anterior`, `string mesaj` | `ros2 interface show curs_ros2_interfaces/srv/AjustareTemperatura` |
| `action/Incalzire.action` | actiune: goal `float64 tinta`; result `bool atins`, `float64 temperatura_finala`; feedback `float64 temperatura_curenta` | `ros2 interface show curs_ros2_interfaces/action/Incalzire` |
| `README.md` | acest document | -- |

Pachetul NU are `setup.py`, `setup.cfg`, `launch/`, noduri Python sau teste -- este
un pachet `ament_cmake` de interfete pur declarativ. In consecinta NU exista
`console_scripts`/entry_points si NU exista `ros2 run curs_ros2_interfaces ...`.

## 5. Date tehnice

Definitiile exacte ale campurilor (cu unitatile din comentariile sursei):

`msg/Temperatura`
```
float64 valoare      # temperatura in grade Celsius
string  status       # "NORMAL" / "ATENTIE" / "CRITIC"
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

Conventii rosidl folosite mai sus: in `.srv` un singur `---` separa cererea de
raspuns; in `.action` doua linii `---` separa goal / result / feedback. Statusul
clasificat din `Temperatura` ("NORMAL"/"ATENTIE"/"CRITIC") este o conventie de
sir de caractere, NU un enum impus de tip.

Dependinte (din `package.xml` si `CMakeLists.txt`):

| Categorie | Valoare |
|-----------|---------|
| `buildtool_depend` | `ament_cmake` |
| `build_depend` | `rosidl_default_generators` |
| `exec_depend` | `rosidl_default_runtime` |
| `member_of_group` | `rosidl_interface_packages` |
| `build_type` (export) | `ament_cmake` |
| consumat de | `curs_ros2` (declara `<depend>curs_ros2_interfaces</depend>`) |

## 6. Sintaxe de pornire

Un pachet de interfete nu se ruleaza -- se construieste, apoi tipurile sunt folosite
de alte noduri.

```bash
# 1) build-ul interfetelor (intai acest pachet, INAINTE de curs_ros2)
cd ~/ros2_ws
colcon build --packages-select curs_ros2_interfaces
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
ros2 run curs_ros2 m7_pub      # publica msg/Temperatura pe /temperatura_custom
ros2 run curs_ros2 m7_sub      # asculta /temperatura_custom

# serviciul custom (M13): nodul m13_monitor expune service-ul ajusteaza_prag
ros2 run curs_ros2 m13_monitor
ros2 service call /ajusteaza_prag curs_ros2_interfaces/srv/AjustareTemperatura "{prag_nou: 35.0}"
```

Limitari si capcane (verificate):
- NU exista `ros2 run curs_ros2_interfaces ...`: pachetul nu inregistreaza executabile.
- `from curs_ros2_interfaces.msg import Temperatura` esueaza daca nu ai dat
  `source install/setup.bash` in terminalul curent, sau daca ai construit `curs_ros2`
  inainte de `curs_ros2_interfaces`.
- `action/Incalzire` se poate introspecta dar nu are nod consumator in curs (sectiunea 3.2).

## 7. Verificare

Acest pachet nu are selftests sau teste unitare proprii (nu contine cod Python de
nucleu). Verificarea este de tip smoke, prin generare + introspectie:

```bash
cd ~/ros2_ws
colcon build --packages-select curs_ros2_interfaces   # asteptat: Finished <<< curs_ros2_interfaces
source install/setup.bash
ros2 interface list | grep curs_ros2_interfaces        # asteptat: 3 linii (msg, srv, action)
```

Stare verificata in acest mediu (ROS 2 Jazzy): pachetul este deja construit in
`install/`, iar `ros2 interface list` raporteaza toate cele trei tipuri:
`curs_ros2_interfaces/msg/Temperatura`,
`curs_ros2_interfaces/srv/AjustareTemperatura`,
`curs_ros2_interfaces/action/Incalzire`. Codul Python generat exista (de exemplu
`install/curs_ros2_interfaces/.../curs_ros2_interfaces/msg/_temperatura.py`).
Numar de teste automate: 0/0 (pachet declarativ, fara teste).

## 8. Igiena datelor si reproductibilitate

Pachetul nu produce date de campanie, figuri sau artefacte de cercetare -- doar cod
generat de build. Reproductibilitate:

- Sub `git` intra DOAR sursa: `package.xml`, `CMakeLists.txt`, `msg/`, `srv/`,
  `action/`, `README.md`. Artefactele de build (`build/`, `install/`, `log/`) NU
  intra in git si se regenereaza identic prin `colcon build`.
- Versiunea declarata: `0.1.0` (din `package.xml`). Licenta: `Apache-2.0`.
- Orice modificare a unui fisier de interfata cere RECONSTRUIRE
  (`colcon build --packages-select curs_ros2_interfaces`) si un `source` nou in
  fiecare terminal; altfel nodurile consuma tipul vechi sau esueaza la import.
