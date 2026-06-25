# servo_control -- demonstratorul istoric al actuatorului rotativ (C4)

Un servomotor in Gazebo comandat din tastatura (sens si viteza), pe ROS 2 Jazzy.
Prima validare a lantului complet operator -> rclpy -> RMW/DDS -> ros_gz_bridge ->
simulator, pe masina de lucru. Material de demonstratie pentru linia C4
(actuator / exoschelet); functia de cercetare a fost preluata ulterior de pachete
dedicate (a se vedea sectiunea 2). Pachet ament_python, construit de colcon.

## 1. Scop

Servo_control ofera un singur nod de teleoperare (`servo_teleop`) care publica o
comanda de viteza unghiulara catre o articulatie rotativa (`shaft_joint`) a unui
model Gazebo (`servo1`). Comanda este transmisa de la tastatura (sageti, SPATIU, Q)
si republicata periodic la 20 Hz, astfel incat articulatia primeste o referinta
continua chiar in absenta apasarilor de taste. Scopul nu este production-grade, ci
demonstrarea reproductibila a lantului operator-simulator si pastrarea ca reper
istoric pentru linia de actuatoare C4.

## 2. Context si loc in arhitectura

In economia tezei (teleoperare in timp real peste retele degradate), servo_control
este nodul de pornire al liniei C4 (exoschelet de reabilitare + motor): cel mai
simplu actuator rotativ comandat de un operator uman printr-un singur grad de
libertate. El a servit drept proba de concept pentru lantul de comanda inainte ca
preocuparile sa se mute pe:

- `teleop_rover` -- teleoperare cu link degradat (robot mobil);
- `sar_swarm` -- roiul SAR (demonstratorul aerian);
- `joint_emulator` -- emularea de impedanta pe banc (linia C4 propriu-zisa);
- `rehab_exo_description` -- descrierea URDF a exoscheletului (linia C4).

Statut: arhiva activa. Nu se mai dezvolta; se pastreaza pentru ca documenteaza cel
mai scurt drum functional comanda-simulator validat pe acest mediu.

Limitare de proiectare fata de regula de fier a proiectului (core pur +
`_selftest()` -> nod ROS subtire -> SIL): servo_control NU respecta acest tipar.
Nodul `servo_teleop` amesteca citirea tastaturii, logica de stare (viteza/sens) si
publicarea ROS in aceeasi clasa; nu exista un modul-nucleu fara ROS si nu exista
selftest. Acest pachet precede metodologia si nu a fost refactorizat la ea.

## 3. Arhitectura

### 3.1 Graful lantului de comanda

```
[tastatura]                [Gazebo: lab_world.sdf]
 sageti, SPATIU, Q          model servo1 (Servomotor)
      |                       joint: shaft_joint (revolute, axa Y)
      v                       plugin JointController (p_gain=10, velocity)
 +--------------+                    ^
 | servo_teleop |                    |
 | Float64,20Hz |                    | gz.msgs.Double
 +--------------+                    |
      |                       +--------------------+
      | /model/servo1/joint/  | ros_gz_bridge      |
      | shaft_joint/cmd_vel   | parameter_bridge   |
      | (std_msgs/Float64)    | ROS -> GZ (']')    |
      +---------------------->|                    |
                              +--------------------+
```

Fluxul este unidirectional operator -> simulator. Nodul publica pe topicul ROS
`/model/servo1/joint/shaft_joint/cmd_vel` (tip `std_msgs/msg/Float64`); puntea
`ros_gz_bridge/parameter_bridge` converteste mesajul in `gz.msgs.Double` si il
livreaza pluginului `JointController` al modelului, care interpreteaza valoarea ca
viteza unghiulara tinta a articulatiei `shaft_joint`. Semnul valorii da sensul de
rotatie (pozitiv = orar, negativ = antiorar in conventia nodului).

### 3.2 Topologia ROS

- Nod: `servo_teleop` (clasa `ServoTeleop`, mostenire din `rclpy.node.Node`).
- Publisher: topic `/model/servo1/joint/shaft_joint/cmd_vel`, tip
  `std_msgs/msg/Float64`, coada (QoS depth) 10.
- Timer: perioada 0.05 s (20 Hz) -> `publish_vel()` republica ultima valoare.
- Fara subscriberi, servicii sau actiuni.
- Citirea tastaturii ruleaza pe firul principal (`run_keyboard()`); `rclpy.spin`
  ruleaza pe un fir daemon separat, ca tastatura sa nu blocheze publicarea.

### 3.3 Specificul puntii (directia bridge)

In launch, argumentul puntii este
`/model/servo1/joint/shaft_joint/cmd_vel@std_msgs/msg/Float64]gz.msgs.Double`.
Caracterul `]` cere o punte ROS -> GZ (numai dinspre ROS spre Gazebo), potrivit
sensului comenzii. (`@` ar fi bidirectional, `[` ar fi GZ -> ROS.) Nodul fiind
exclusiv publisher, directia unidirectionala este suficienta.

## 4. Inventar fisiere

| Fisier | Rol | Cum se verifica |
|---|---|---|
| `servo_control/servo_teleop.py` | nodul de teleoperare din tastatura; executabilul `servo_teleop` (entry point `:main`) | `ros2 pkg executables servo_control` listeaza `servo_teleop` |
| `servo_control/__init__.py` | marcheaza directorul ca pachet Python (fara cod) | import implicit la build |
| `launch/servo_launch.py` | porneste `gz sim`, apoi puntea la +5 s, apoi teleopul intr-o fereastra `xterm` la +6 s | `ros2 launch servo_control servo_launch.py` |
| `worlds/lab_world.sdf` | lumea `servo_lab`: camera 6x6 m (pereti la +/-3 m pe X si Y), masa, lumini, `include model://Servomotor` ca `servo1` | instalata in `share/servo_control/worlds/`; lansata din `~/.gz/worlds/` |
| `package.xml` | manifest ament_python; depinde de `rclpy`, `std_msgs` | `colcon build --packages-select servo_control` |
| `setup.py` | entry_points + data_files (launch, world) | build colcon |
| `setup.cfg` | `script_dir`/`install_scripts` la `lib/servo_control` (necesar pentru `ros2 run`) | `ros2 pkg executables` nevid |
| `resource/servo_control` | marker ament_index (fisier gol) | prezenta in `share/ament_index/...` |
| `test/test_flake8.py` | lint stil de cod (ament_flake8) | `python3 -m pytest test/` (vezi sectiunea 7) |
| `test/test_pep257.py` | lint docstring (ament_pep257) | idem |
| `test/test_copyright.py` | verificare antet copyright (marcat `skip`) | idem |

Dependenta externa nedeclarata in pachet: modelul `model://Servomotor`. El NU se
afla in acest pachet, ci in `~/.gz/models/Servomotor/Servomotor.sdf` (cale gasita
pe acest mediu). Lumea `lab_world.sdf` il include prin `<uri>model://Servomotor</uri>`;
fara acest model in calea de resurse Gazebo, lumea nu incarca servomotorul.
TODO: pachetul nu instaleaza si nici nu declara dependenta de modelul Servomotor;
calea `~/.gz/models/Servomotor` este implicita pentru acest mediu.

## 5. Date tehnice

Constante si parametri reali, citite din cod si din modelul SDF:

| Marime | Valoare | Sursa | Unitate |
|---|---|---|---|
| Topic comanda | `/model/servo1/joint/shaft_joint/cmd_vel` | `servo_teleop.py:22` | -- |
| Tip mesaj ROS | `std_msgs/msg/Float64` | `servo_teleop.py:16,56` | -- |
| Frecventa de publicare | 20 (timer 0.05 s) | `servo_teleop.py:60` | Hz |
| Pas de viteza (`SPEED_STEP`) | 0.5 | `servo_teleop.py:24` | rad/s per apasare |
| Viteza maxima (`MAX_SPEED`) | 10.0 | `servo_teleop.py:25` | rad/s |
| Viteza minima (`MIN_SPEED`) | 0.5 | `servo_teleop.py:26` | rad/s |
| Viteza initiala (`self.speed`) | 1.0 | `servo_teleop.py:57` | rad/s |
| Coada publisher (QoS depth) | 10 | `servo_teleop.py:56` | mesaje |

Parametrii articulatiei tinta (din `~/.gz/models/Servomotor/Servomotor.sdf`):

| Marime | Valoare | Unitate |
|---|---|---|
| Tip articulatie | revolute | -- |
| Axa de rotatie | 0 1 0 (Y) | -- |
| Limita de efort | 5.0 | N.m |
| Limita de viteza | 10.0 | rad/s |
| Damping / friction | 0.01 / 0.001 | -- |
| Plugin | `gz-sim-joint-controller-system`, `use_force_commands=false`, `p_gain=10.0` | -- |

Observatie de coerenta: `MAX_SPEED=10.0` rad/s din nod coincide cu limita de viteza
a articulatiei (10.0 rad/s), iar pluginul lucreaza in mod viteza
(`use_force_commands=false`), deci comanda `Float64` este interpretata ca viteza
tinta a articulatiei.

Lumea `lab_world.sdf` (parametri de scena, nu de control): pas de fizica 0.001 s,
factor de timp real 1.0, camera de 6x6 m (pereti `wall_north/south` la y=+/-3.0 si
`wall_west/east` la x=+/-3.0, fiecare cu deschidere de 6 m), blatul mesei cu
suprafata la Z=0.75 m (model `table_top` la Z=0.725 m, grosime 0.05 m), servomotorul
plasat la `pose 0 0 0.79  1.5707963 0 0` (rotit pi/2 pe X).

## 6. Sintaxe de pornire

```bash
# 0) build (pachet ament_python)
cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash
colcon build --packages-select servo_control --symlink-install
source install/setup.bash

# 1) pregatirea lumii: launch-ul o cauta in ~/.gz/worlds/
mkdir -p ~/.gz/worlds
cp ~/ros2_ws/src/servo_control/worlds/lab_world.sdf ~/.gz/worlds/
# modelul servomotor trebuie sa fie vizibil pentru Gazebo, de exemplu in
# ~/.gz/models/Servomotor/  (vezi sectiunea 4: dependenta externa Servomotor)

# 2) varianta integrata -- un singur launch (necesita xterm)
sudo apt install -y xterm          # o singura data, daca lipseste
ros2 launch servo_control servo_launch.py
#   porneste gz sim, apoi puntea la +5 s, apoi teleopul in xterm la +6 s

# 3) varianta manuala -- trei terminale
gz sim -r ~/.gz/worlds/lab_world.sdf
ros2 run ros_gz_bridge parameter_bridge \
  "/model/servo1/joint/shaft_joint/cmd_vel@std_msgs/msg/Float64]gz.msgs.Double"
ros2 run servo_control servo_teleop
```

Comenzile din tastatura (in fereastra teleopului):

| Tasta | Actiune |
|---|---|
| sageata DREAPTA | rotire in sens orar (viteza = `self.speed`) |
| sageata STANGA | rotire in sens antiorar (viteza = -`self.speed`) |
| sageata SUS | creste viteza curenta cu 0.5 rad/s (pana la 10.0) |
| sageata JOS | scade viteza curenta cu 0.5 rad/s (pana la 0.5) |
| SPATIU | stop imediat (viteza = 0) |
| Q | iesire (publica 0, apoi inchide) |

Verificare a lantului fara tastatura (publicare manuala a unei comenzi):

```bash
ros2 topic pub --once /model/servo1/joint/shaft_joint/cmd_vel \
  std_msgs/msg/Float64 "data: 2.0"
```

Limitari de pornire:
- launch-ul foloseste `prefix='xterm -e'`; fara `xterm` instalat, fereastra de
  teleop nu apare.
- launch-ul citeste lumea din `~/.gz/worlds/lab_world.sdf` (cale fixa,
  `os.path.expanduser`), nu din `share/`; copierea de la pasul 1 este obligatorie.
- temporizarile fixe (+5 s punte, +6 s teleop) presupun ca `gz sim` a pornit in
  acest interval; pe masini lente puntea poate aparea inainte de simulator.

## 7. Verificare

Pachetul NU are un nucleu pur cu `_selftest()` si nici teste functionale; singurele
teste sunt cele trei lint-uri standard generate de `ament_python`. Rulate direct
(fara colcon, care pe acest mediu colecteaza 0 teste din cauza wrapper-ului
setup.py si raporteaza NO TESTS RAN):

```bash
cd ~/ros2_ws/src/servo_control && source /opt/ros/jazzy/setup.bash
python3 -m pytest test/ -v
```

Rezultat real masurat pe acest mediu (2 failed, 1 skipped din 3):

| Test | Rezultat | Detaliu |
|---|---|---|
| `test_flake8` | FAILED | 36 avertismente de stil (I100/I201 ordine/grupare importuri, E221 spatii multiple, E302 linii goale lipsa, E501 linie prea lunga, W292 fara newline final, D205/D400 docstring) |
| `test_pep257` | FAILED | 3 erori D205/D400/D415 pe docstringul modulului `servo_teleop.py` |
| `test_copyright` | SKIPPED | marcat `@pytest.mark.skip` (lipsa antet copyright in sursa) |

Aceste esecuri sunt pe stil/documentatie, nu pe functionalitate: nodul porneste,
inregistreaza executabilul (`ros2 pkg executables servo_control` -> `servo_teleop`)
si publica la 20 Hz. TODO: daca pachetul ar fi reactivat, lint-urile trebuie
trecute pe verde (sau testele eliminate explicit) inainte de orice declaratie de
"teste OK".

Build: `colcon build --packages-select servo_control` se finalizeaza cu
`Finished <<< servo_control`. Avertismentul de la `pytest-repeat` (unbuilt egg) si
mesajul "1 package had stderr output" sunt cosmetice (a se vedea CLAUDE.md, sect. 6).

Inconsistenta de versiune (TODO): `package.xml` declara `<version>0.0.0`, iar
`setup.py` declara `version="1.0.0"`. De aliniat cele doua amprente de versiune.
La fel, `package.xml` pastreaza `description`, `maintainer` si `license` cu valori
sablon ("TODO: ...", `ubuntu@todo.todo`); `setup.py` declara `license="MIT"`.

## 8. Igiena datelor si reproductibilitate

Servo_control nu produce date de campanie: este un demonstrator interactiv, fara
inregistrari, fara CSV, fara figuri. Nu intra sub regula de arhivare a datelor
brute. Artefacte de mediu care NU trebuie comise:

```bash
# generate de build / rulare, raman in afara depozitului
#   build/  install/  log/  __pycache__/  *.pyc  .pytest_cache/
```

Reproductibilitate: lantul depinde de doua artefacte externe pachetului, plasate
manual pe masina:
- `~/.gz/worlds/lab_world.sdf` -- copie a lumii (instalata si in
  `share/servo_control/worlds/`, dar launch-ul citeste din `~/.gz/worlds/`);
- `~/.gz/models/Servomotor/` -- modelul inclus de lume; nu este versionat in acest
  pachet.

TODO de reproductibilitate: pentru o reluare curata, modelul Servomotor si calea de
resurse Gazebo (`GZ_SIM_RESOURCE_PATH`) ar trebui documentate sau vandorizate in
pachet; in forma actuala, pornirea presupune mediul de lucru existent.
