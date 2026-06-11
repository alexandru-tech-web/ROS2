# Modulul 7 — Interfețe custom (msg / srv / action)

## Ce înveți
- De ce tipurile **standard** (`std_msgs/Float64`, `example_interfaces/srv/AddTwoInts`) nu îți ajung mereu și când ai nevoie de un **tip propriu**.
- De ce un pachet de interfețe trebuie să fie **separat** și de tip **`ament_cmake`**, nu un pachet Python pur.
- Cum se scrie un fișier `.msg`, un `.srv` și un `.action`.
- Liniile-cheie din `CMakeLists.txt` și `package.xml` care fac ca `rosidl` să genereze codul.
- Cum construiești pachetul de interfețe, cum dai `source` și cum îl folosești dintr-un nod Python (`curs_ros2`).

## Conceptul, pe scurt
Un tip de mesaj e ca un **formular tipizat**: are câmpuri cu nume și tip fixe, iar amândouă capetele (cine completează și cine citește) folosesc **exact același formular**. `Float64` e un formular cu o singură căsuță (un număr). Dar dacă vrei să trimiți **o valoare ȘI un status împreună**, ai nevoie de un formular cu două căsuțe — adică de un tip **definit de tine**.

În acest modul folosim tipul `curs_ros2_interfaces/msg/Temperatura`, cu câmpurile `float64 valoare` și `string status`. Avantajul față de două topice separate: cele două câmpuri călătoresc **împreună**, într-un mesaj coerent — nu poți primi vreodată o valoare fără statusul ei.

## De ce un pachet SEPARAT și de tip `ament_cmake`?
Codul Python al claselor de mesaje (`Temperatura()`, `Temperatura.Request()` etc.) **nu îl scriem noi de mână** — îl **generează automat** unealta `rosidl` în timpul build-ului, din fișierele `.msg` / `.srv` / `.action`.

Problema: `rosidl` rulează prin **CMake** (generează cod C, C++, Python și fișiere de tip). Un pachet **pur Python** (`ament_python`, cum e `curs_ros2`) **nu are pas de CMake**, deci **nu poate genera interfețe**. De aceea:

- Interfețele stau **într-un pachet separat**, de tip **`ament_cmake`** (la noi: `curs_ros2_interfaces`).
- Pachetul tău Python (`curs_ros2`) doar **depinde** de pachetul de interfețe și **importă** tipul generat.

> Regula de aur: **un singur pachet de interfețe `ament_cmake`** pe care îl folosesc toate celelalte pachete. Nu amesteca definiții de interfețe cu noduri Python în același pachet — nu se poate.

## Fișierele de interfață

### `msg/Temperatura.msg`
Un `.msg` e o simplă listă de câmpuri (`tip nume`):

```
# Valoarea masurata, in grade Celsius
float64 valoare
# Eticheta de stare: "NORMAL" / "ATENTIE" / "CRITIC"
string status
```

### `srv/AjustareTemperatura.srv`
Un `.srv` are **cerere** și **răspuns**, despărțite prin `---`:

```
# CEREREA (request) — ce trimite clientul
float64 prag_nou
---
# RASPUNSUL (response) — ce intoarce serverul
bool succes
float64 prag_anterior
string mesaj
```

### `action/Incalzire.action`
Un `.action` are **trei** secțiuni, despărțite prin câte un `---`: **goal**, **result** și **feedback**:

```
# GOAL — tinta pe care o cere clientul
float64 tinta
---
# RESULT — rezultatul final, trimis o singura data la sfarsit
bool atins
float64 temperatura_finala
---
# FEEDBACK — progres trimis periodic in timpul executiei
float64 temperatura_curenta
```

> În acest modul **folosim** doar tipul `msg/Temperatura` în noduri. `srv` și `action` sunt arătate aici doar ca să vezi cum se scriu — le folosim în modulele de servicii și acțiuni.

## Liniile-cheie din `CMakeLists.txt`
În `curs_ros2_interfaces/CMakeLists.txt`, partea care contează pentru generare:

```cmake
# Aducem generatorul de interfete:
find_package(rosidl_default_generators REQUIRED)

# Generam clasele pentru TOATE fisierele noastre .msg / .srv / .action.
# Numele proiectului (${PROJECT_NAME}) devine numele pachetului de interfete.
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Temperatura.msg"
  "srv/AjustareTemperatura.srv"
  "action/Incalzire.action"
)

# Necesar ca dependintele declarate in package.xml sa fie exportate corect:
ament_export_dependencies(rosidl_default_runtime)
```

## Liniile-cheie din `package.xml`
În `curs_ros2_interfaces/package.xml`:

```xml
<!-- Pachet de tip ament_cmake (NU ament_python): -->
<buildtool_depend>ament_cmake</buildtool_depend>

<!-- Necesar la BUILD ca rosidl sa genereze codul: -->
<build_depend>rosidl_default_generators</build_depend>

<!-- Necesar la RULARE pentru codul generat: -->
<exec_depend>rosidl_default_runtime</exec_depend>

<!-- OBLIGATORIU: marcheaza pachetul ca fiind unul de interfete.
     Fara aceasta linie, rosidl NU stie ca trebuie sa proceseze fisierele. -->
<member_of_group>rosidl_interface_packages</member_of_group>
```

> Câmpul `<member_of_group>rosidl_interface_packages</member_of_group>` este cel mai des uitat — fără el build-ul "trece", dar tipurile **nu se generează** și importul în Python eșuează.

## Cum se construiește pachetul de interfețe
Din rădăcina workspace-ului (`~/ros2_ws`):

```bash
# Construim DOAR pachetul de interfete (mai rapid, izolam erorile):
colcon build --packages-select curs_ros2_interfaces
```

```bash
# OBLIGATORIU dupa build: dam "source" ca shell-ul sa "vada" noul tip.
# Fara acest pas, importul "from curs_ros2_interfaces.msg import Temperatura" esueaza.
source install/setup.bash
```

După ce ai construit și ai dat `source`, poți reconstrui și pachetul tău Python care folosește tipul:

```bash
colcon build --packages-select curs_ros2
source install/setup.bash
```

## Cum rulezi nodurile
**T1 — publisher-ul custom:**
```bash
ros2 run curs_ros2 m7_pub
```

**T2 — subscriber-ul custom:**
```bash
ros2 run curs_ros2 m7_sub
```

În T1 vei vedea cum valoarea crește și statusul trece `NORMAL → ATENTIE → CRITIC`, iar în T2 vei vedea aceleași perechi `valoare/status` primite.

> Nu uita: **fiecare terminal** trebuie să fi dat `source install/setup.bash` (și `source /opt/ros/jazzy/setup.bash`) ca să găsească atât `curs_ros2`, cât și tipul `Temperatura`.

## Verificare
Inspectează tipul și topicul fără să scrii cod:

```bash
# Vezi structura tipului nostru (campuri + tipuri):
ros2 interface show curs_ros2_interfaces/msg/Temperatura
# ->
# float64 valoare
# string status
```

```bash
# Listeaza toate interfetele pachetului nostru (msg + srv + action):
ros2 interface list | grep curs_ros2
# -> curs_ros2_interfaces/msg/Temperatura
#    curs_ros2_interfaces/srv/AjustareTemperatura
#    curs_ros2_interfaces/action/Incalzire
```

```bash
# Cu publisher-ul pornit, asculta mesajele de pe topic:
ros2 topic echo /temperatura_custom
# ->
# valoare: 20.0
# status: NORMAL
# ---
```

```bash
# Confirma si TIPUL topicului:
ros2 topic type /temperatura_custom
# -> curs_ros2_interfaces/msg/Temperatura
```

## Exerciții
1. **Câmp nou în mesaj.** Adaugă în `Temperatura.msg` un câmp `int64 id_senzor`, reconstruiește pachetul de interfețe, dă `source`, apoi completează-l în publisher și loghează-l în subscriber.
2. **Prag configurabil.** Mută cele două praguri (`30.0` și `50.0`) din publisher în **parametri** ROS 2 (vezi modulul 4), ca să poți schimba comportamentul fără să modifici codul.
3. **Folosește `srv`-ul.** Pornind de la `AjustareTemperatura.srv`, scrie un mic server care primește `prag_nou`, întoarce `prag_anterior` și `succes=True`, apoi confirmă cu `ros2 service call`.

## Capcane frecvente
- **Uiți `<member_of_group>rosidl_interface_packages</member_of_group>`** în `package.xml`-ul pachetului de interfețe. Build-ul pare să meargă, dar tipurile **nu se generează**, iar importul în Python dă `ModuleNotFoundError` / `No module named ...msg`.
- **Uiți să adaugi dependința în `package.xml` al pachetului care folosește tipul.** În `curs_ros2/package.xml` trebuie să existe `<depend>curs_ros2_interfaces</depend>`, altfel nodul nu găsește tipul la rulare (chiar dacă importul "merge" pe mașina ta de dezvoltare).
- **Nu ai dat `source` după build.** Cel mai frecvent motiv pentru `ImportError` la `from curs_ros2_interfaces.msg import Temperatura`: ai construit pachetul, dar shell-ul curent nu "vede" încă tipul. Rulează `source install/setup.bash` în **fiecare** terminal.
- **Pui interfețele într-un pachet `ament_python`.** Nu funcționează: fără pasul de CMake, `rosidl` nu rulează. Interfețele se pun **obligatoriu** într-un pachet `ament_cmake`.
- **Tip diferit la publisher și subscriber.** Dacă unul folosește `Temperatura` și celălalt alt tip pe același topic, nu se conectează niciodată. Verifică cu `ros2 topic type`.
- **Numele câmpurilor greșit.** Câmpurile sunt exact `valoare` și `status`. O greșeală de scriere (`valore`, `Status`) dă `AttributeError` la rulare.
