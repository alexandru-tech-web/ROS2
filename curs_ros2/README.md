# curs_ros2 -- curs complet ROS 2 Jazzy (rclpy), documentatie tehnica

Pachet EDUCATIONAL si arhiva didactica: 14 module (M0-M13) care demonstreaza
izolat conceptele ROS 2 (noduri, topice, launch, parametri, servicii, actiuni,
interfete custom, QoS, executors, TF2, lifecycle, turtlesim) si un proiect final
integrator. Nu este o contributie de cercetare (nu intra in C1-C4 si nici intr-un
articol A1-A5); rolul lui este sa serveasca drept referinta reproductibila pentru
conceptele rclpy folosite apoi in pachetele de cercetare ale depozitului.
Interfetele custom stau intr-un pachet SEPARAT, `curs_ros2_interfaces`
(ament_cmake), fiindca generatorul rosidl nu poate produce tipuri intr-un pachet
pur Python.

## 1. Scop

Cursul ofera, pentru fiecare concept ROS 2, trei lucruri: o lectie scrisa
(`docs/NN_*.md`), cod functional comentat (`curs_ros2/m*.py`) si o sintaxa de
pornire verificabila din CLI. Filosofia este "regula de aur" a depozitului:
logica importanta se scrie ca functii pure (`curs_ros2/logica.py`), se testeaza
automat (`test/test_logica.py`), si abia apoi e imbracata in noduri ROS. Modulele
practice M12 (control broasca) si M13 (monitor de temperatura) importa EXACT
aceste functii, in loc sa-si rescrie logica inline.

Tinta didactica este ROS 2 Jazzy cu rclpy (Python 3.12). Pachetul nu are
dependinte spre restul depozitului (in afara de pachetul-frate de interfete) si
nu participa la nicio campanie de masurare.

## 2. Context si loc in arhitectura

Depozitul are o coloana de cercetare (benchmark RMW sub degradare de retea,
demonstratoare SAR si exoschelet). `curs_ros2` NU este pe acea coloana: este
materialul de formare care demonstreaza, pe exemple minimale, conceptele rclpy
reutilizate apoi de pachetele de cercetare:

- QoS (M8) -> politicile de reliability/durability din `c1_benchmark`;
- launch si parametri (M3, M4) -> orchestrarea din toate pachetele de misiune;
- TF2 si geometrie (M10) -> arborele de frame-uri din `rehab_exo_description`,
  `joint_emulator`;
- nucleu pur testat + nod subtire (M13) -> metodologia "core pur + selftest ->
  nod ROS" aplicata in intreg depozitul.

Pereche obligatorie: `curs_ros2` (ament_python -- nodurile si lectiile) plus
`curs_ros2_interfaces` (ament_cmake -- tipurile custom). Modulele M7 si M13
importa din pachetul de interfete, deci acesta trebuie construit PRIMUL.

## 3. Arhitectura

### 3.1 Nucleu pur -> nod ROS -> SIL

Tiparul pe care il demonstreaza modulele practice:

```
curs_ros2/logica.py            <- nucleu PUR (fara ROS, fara efecte secundare)
  |  clasifica_temperatura()      4 functii: clasificare + geometrie de control
  |  normalizeaza_unghi()
  |  eroare_distanta()
  |  unghi_spre_tinta()
  v
test/test_logica.py            <- 7 teste pytest care prind defectele in ms
  v
m13_monitor.py / m12_turtle_control.py   <- nodurile ROS importa functiile pure
```

Nucleul nu cunoaste ROS: primeste numere, intoarce numere. Nodul ROS este doar
"imbracamintea" peste functii deja verificate. Acest pachet didactic nu are un
strat SIL propriu de tip campanie (acela apartine pachetelor de cercetare);
echivalentul lui de validare fara ROS este suita `test_logica.py`.

### 3.2 Modulele si artefactele lor

Fiecare modul are o lectie in `docs/`, iar cele cu cod au unul sau mai multe
noduri inregistrate ca executabile (vezi entry_points din `setup.py`). Sase
module au si un fisier de launch.

```
M0  concepte + CLI        docs/00_introducere.md, docs/cheatsheet_cli.md
M1  noduri/timere         nod_simplu
M2  topice pub/sub        publisher, subscriber
M3  launch/orchestrare    launch/m3_launch.py  (publisher + subscriber intarziat 3 s)
M4  parametri             m4_param            launch/m4_param_launch.py, config/m4_params.yaml
M5  servicii              m5_server, m5_client            launch/m5_service_launch.py
M6  actiuni               m6_action_server, m6_action_client
M7  interfete custom      m7_pub, m7_sub      (tip Temperatura din pachetul-frate)
M8  QoS                   m8_pub, m8_sub
M9  executors             m9_executor
M10 TF2                   m10_broadcaster, m10_listener   launch/m10_tf_launch.py
M11 lifecycle             m11_lifecycle
M12 turtlesim aplicat     m12_patrat, m12_control         launch/m12_turtle_launch.py
M13 proiect final         m13_senzor, m13_monitor         launch/m13_proiect_launch.py
```

### 3.3 Topice, servicii, actiuni, frame-uri (extrase din cod)

| Modul | Nod (numele rulat) | Interfata ROS | Detaliu real din cod |
|---|---|---|---|
| M2 | publisher_temperatura / subscriber_temperatura | topic `/temperatura` (Float64), `/alarma` (String) | publisher creste valoarea cu 0.5 grade/s |
| M5 | server_adunare / client_adunare | serviciu `aduna` (example_interfaces/AddTwoInts) | clientul citeste a,b din argv (implicit 2,3) |
| M6 | server_fibonacci / client_fibonacci | actiune `fibonacci` (example_interfaces/Fibonacci) | server pe MultiThreadedExecutor, sleep 0.5 s/pas |
| M7 | publisher_custom / subscriber_custom | topic `/temperatura_custom` (curs_ros2_interfaces/Temperatura) | doua campuri intr-un singur mesaj coerent |
| M8 | qos_publisher / qos_subscriber | topic `/qos_demo` (String) | parametru `profil`: reliable / best_effort / transient |
| M10 | tf_broadcaster / tf_listener | `/tf`: world -> robot, 20 Hz | listener face lookup_transform('world','robot', t=0) |
| M11 | nod_lifecycle | topic `/lc_chatter` (String), servicii lifecycle | publish efectiv DOAR in starea active (lifecycle publisher) |
| M12 | turtle_patrat / turtle_control | `/turtle1/cmd_vel` (Twist), `/turtle1/pose` (turtlesim/Pose) | open-loop vs. proportional cu feedback |
| M13 | senzor_temperatura / monitor_temperatura | `/senzor/temperatura` (Float64), `/senzor/alarma` (String), serviciu `ajusteaza_prag` | monitorul importa clasifica_temperatura din nucleul pur |

Note: numele de serviciu/actiune sunt relative in cod (`aduna`, `fibonacci`,
`ajusteaza_prag`), deci apar in graf ca `/aduna`, `/fibonacci`, `/ajusteaza_prag`.

## 4. Inventar fisiere

| Fisier | Rol | Cum se verifica |
|---|---|---|
| `package.xml` | manifest ament_python; depinde de rclpy, std_msgs, geometry_msgs, sensor_msgs, example_interfaces, curs_ros2_interfaces, tf2_ros, lifecycle_msgs; exec_depend turtlesim | `colcon build --packages-select curs_ros2` |
| `setup.py` | 20 entry_points console_scripts + instalare launch/config/docs in share | `ros2 pkg executables curs_ros2` (20 linii) |
| `setup.cfg` | `script_dir`/`install_scripts` la `lib/curs_ros2` (necesar ca executabilele sa apara) | fara aceasta, lista de executabile e goala |
| `curs_ros2/logica.py` | nucleul PUR: 4 functii (clasificare temperatura + geometrie de control) | `test/test_logica.py` (7) |
| `curs_ros2/m1_nod_simplu.py` | M1: clasa Node, logger, timer la 1 Hz | `ros2 run curs_ros2 nod_simplu` |
| `curs_ros2/m1_publisher.py` / `m1_subscriber.py` | M2: pub `/temperatura`, sub + alarma `/alarma` | `ros2 topic echo /temperatura` |
| `curs_ros2/m4_param_node.py` | M4: declare_parameter, callback de validare (rata > 0), recreare timer | `ros2 param set /nod_parametri rata 5.0` |
| `curs_ros2/m5_service_server.py` / `m5_service_client.py` | M5: serviciu `aduna`, client async | `ros2 service call /aduna ...` |
| `curs_ros2/m6_action_server.py` / `m6_action_client.py` | M6: actiune `fibonacci` cu feedback si anulare | `ros2 action send_goal /fibonacci ... --feedback` |
| `curs_ros2/m7_pub_custom.py` / `m7_sub_custom.py` | M7: tip custom Temperatura pe `/temperatura_custom` | `ros2 interface show curs_ros2_interfaces/msg/Temperatura` |
| `curs_ros2/m8_qos_publisher.py` / `m8_qos_subscriber.py` | M8: profiluri QoS (reliability/durability/history) | `ros2 topic info /qos_demo --verbose` |
| `curs_ros2/m9_executor_demo.py` | M9: MultiThreadedExecutor + doua callback groups (rapid/lent) | rulare directa, observa tic-urile rapide in timpul muncii grele |
| `curs_ros2/m10_tf_broadcaster.py` / `m10_tf_listener.py` | M10: world -> robot la 20 Hz, lookup la timp 0 | `ros2 run tf2_tools view_frames` |
| `curs_ros2/m11_lifecycle_node.py` | M11: LifecycleNode, tranzitii configure/activate/...; publish doar in active | `ros2 lifecycle set /nod_lifecycle configure` |
| `curs_ros2/m12_turtle_patrat.py` | M12: patrat open-loop (masina de stari pe timp) | `ros2 launch curs_ros2 m12_turtle_launch.py` (porneste m12_control) |
| `curs_ros2/m12_turtle_control.py` | M12: go-to-goal proportional cu feedback din `/turtle1/pose` | parametri `x_tinta`, `y_tinta` |
| `curs_ros2/m13_senzor.py` / `m13_monitor.py` | M13: senzor sinusoidal determinist + monitor cu serviciu de prag live | `ros2 launch curs_ros2 m13_proiect_launch.py` |
| `launch/m3_launch.py` | M3: publisher + subscriber intarziat 3 s (TimerAction) | `ros2 launch curs_ros2 m3_launch.py` |
| `launch/m4_param_launch.py` | M4: porneste m4_param cu `config/m4_params.yaml` din share | foloseste get_package_share_directory |
| `launch/m5_service_launch.py` | M5: server + client intarziat 2 s, argumente 5 si 7 | `ros2 launch curs_ros2 m5_service_launch.py` |
| `launch/m10_tf_launch.py` | M10: broadcaster + listener | `ros2 launch curs_ros2 m10_tf_launch.py` |
| `launch/m12_turtle_launch.py` | M12: turtlesim_node + m12_control intarziat 2 s | necesita `turtlesim` instalat |
| `launch/m13_proiect_launch.py` | M13: senzor (amplitudine 30 -> atinge CRITIC) + monitor, parametri inline | `ros2 launch curs_ros2 m13_proiect_launch.py` |
| `config/m4_params.yaml` | parametrii M4 sub `nod_parametri`: `rata: 2.0`, `mesaj: ...` | instalat in share prin data_files |
| `docs/00_introducere.md` ... `docs/13_proiect_final.md`, `docs/cheatsheet_cli.md` | lectiile (15 fisiere): concept, cod comentat, rulare, verificare CLI, exercitii, capcane | citire directa |
| `test/test_logica.py` | 7 teste pytest pe nucleul pur (clasificare + geometrie) | `python3 -m pytest test/test_logica.py -v` |
| `test/test_flake8.py`, `test_pep257.py`, `test_copyright.py` | lintere standard din sablonul ROS 2 (stil/licenta pe workspace, nu logica cursului) | `colcon test` |
| `CURS.md` | indexul cursului (harta modulelor, traseu recomandat) | citire directa |

Note de onestitate fata de inventar: cele 20 de noduri din `setup.py` corespund
exact celor 20 de fisiere `m*.py` si celor 20 de executabile listate de
`ros2 pkg executables curs_ros2`. Doua surse M1 contin caractere non-ASCII in
log-uri: `m1_publisher.py` (simbolul de grad, linia 18) si `m1_subscriber.py`
(simbolul de grad plus o sageata Unicode, linia 30); `m1_nod_simplu.py` este
ASCII curat. Acest README respecta ASCII strict, dar nu modifica acele surse
didactice. TODO: aliniaza `m1_publisher.py` si `m1_subscriber.py` la ASCII daca
se doreste consistenta cu CLAUDE.md sectiunea 3.

## 5. Date tehnice (parametri si valori reale din cod)

| Sursa | Parametru / constanta | Valoare implicita | Unitate / semnificatie |
|---|---|---|---|
| `logica.clasifica_temperatura` | `prag_atentie`, `prag_critic` | 30.0, 50.0 | grade C; sub atentie=NORMAL, sub critic=ATENTIE, altfel CRITIC |
| `logica.normalizeaza_unghi` | -- | -- | aduce unghiul in [-pi, pi] via atan2(sin, cos) |
| `m4_param_node` | `rata`, `mesaj` | 1.0, 'Salut din parametri' | Hz (validat > 0); text de log |
| `config/m4_params.yaml` | `nod_parametri.rata`, `.mesaj` | 2.0, 'Salut din fisierul YAML' | suprascrie implicitele la launch |
| `m8_qos_publisher` | `profil` | 'reliable' | reliable / best_effort / transient; depth=10; publica la 2 Hz |
| `m10_tf_broadcaster` | timer | 0.05 s (20 Hz) | world->robot pe cerc raza 1; yaw = t |
| `m12_turtle_patrat` | viteza_inainte, viteza_rotire, durata_inainte | 2.0, 1.5708, 2.0 | m/s, rad/s, s (open-loop, masina de stari) |
| `m12_turtle_control` | `x_tinta`, `y_tinta`; castiguri | 8.0, 8.0; ang=4.0, lin=1.5 | tinta; prag sosire dist < 0.1, prag aliniere |err| < 0.2 |
| `m13_senzor` | `rata`, `valoare_baza`, `amplitudine` | 2.0, 25.0, 20.0 | Hz, grade; valoare = baza + amplitudine*sin(t), contor determinist |
| `m13_senzor` (launch) | amplitudine inline | 30.0 | la launch oscileaza -5..55 -> atinge CRITIC (50) |
| `m13_monitor` | `prag_atentie`, `prag_critic` | 30.0, 50.0 | grade; prag_atentie schimbabil live, refuza prag <= 0 |

Interfetele custom (din `curs_ros2_interfaces`):

| Interfata | Definitie reala |
|---|---|
| `msg/Temperatura` | `float64 valoare`, `string status` |
| `srv/AjustareTemperatura` | cerere `float64 prag_nou` --- raspuns `bool succes`, `float64 prag_anterior`, `string mesaj` |
| `action/Incalzire` | goal `float64 tinta` --- result `bool atins`, `float64 temperatura_finala` --- feedback `float64 temperatura_curenta` |

Nota: actiunea `Incalzire` este DEFINITA si generata, dar nu este folosita de
niciun nod din `curs_ros2` (M6 demonstreaza actiuni cu tipul standard Fibonacci).
Serviciul `AjustareTemperatura` si mesajul `Temperatura` sunt folosite efectiv in
M13, respectiv M7.

## 6. Sintaxe de pornire

Pachet ament_python inregistrat: comenzile `ros2 run curs_ros2 <executabil>` si
`ros2 launch curs_ros2 <fisier>.launch.py` sunt valide dupa build + source.

```bash
# === Build (ORDINEA conteaza: intai interfetele, apoi nodurile) ===
cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash

colcon build --packages-select curs_ros2_interfaces   # genereaza tipurile custom
source install/setup.bash

colcon build --packages-select curs_ros2              # nodurile si lectiile
source install/setup.bash
# Regula: source install/setup.bash in FIECARE terminal nou, dupa fiecare build.

# === Verificarea fara ROS (rapida, mereu verde) ===
python3 -m pytest src/curs_ros2/test/test_logica.py -v   # 7/7

# === Inventarul executabilelor (asteptat: 20 de linii) ===
ros2 pkg executables curs_ros2
```

Module reprezentative (toate comenzile sunt extrase din entry_points si launch):

```bash
# M1 noduri / M2 topice
ros2 run curs_ros2 nod_simplu
ros2 run curs_ros2 publisher        # + intr-un alt terminal:
ros2 run curs_ros2 subscriber

# M3 launch: publisher + subscriber intarziat 3 s
ros2 launch curs_ros2 m3_launch.py

# M4 parametri (din YAML-ul instalat in share)
ros2 launch curs_ros2 m4_param_launch.py
ros2 param list /nod_parametri
ros2 param set /nod_parametri rata 5.0      # validat: rata > 0

# M5 servicii
ros2 launch curs_ros2 m5_service_launch.py  # server + client cu argumente 5 si 7
ros2 service call /aduna example_interfaces/srv/AddTwoInts "{a: 5, b: 7}"

# M6 actiuni (server pe MultiThreadedExecutor)
ros2 run curs_ros2 m6_action_server         # + alt terminal:
ros2 run curs_ros2 m6_action_client
ros2 action send_goal /fibonacci example_interfaces/action/Fibonacci "{order: 8}" --feedback

# M7 interfete custom
ros2 run curs_ros2 m7_pub
ros2 run curs_ros2 m7_sub
ros2 interface show curs_ros2_interfaces/msg/Temperatura

# M8 QoS (profil ales prin parametru)
ros2 run curs_ros2 m8_pub --ros-args -p profil:=best_effort
ros2 run curs_ros2 m8_sub
ros2 topic info /qos_demo --verbose

# M9 executors (observa tic-urile "rapid" in timpul muncii grele de 3 s)
ros2 run curs_ros2 m9_executor

# M10 TF2
ros2 launch curs_ros2 m10_tf_launch.py
ros2 run tf2_tools view_frames

# M11 lifecycle (porneste in unconfigured; condus din CLI)
ros2 run curs_ros2 m11_lifecycle
ros2 lifecycle set /nod_lifecycle configure
ros2 lifecycle set /nod_lifecycle activate
ros2 topic echo /lc_chatter                 # apar mesaje DOAR dupa activate

# M12 turtlesim (necesita pachetul turtlesim instalat)
ros2 launch curs_ros2 m12_turtle_launch.py  # turtlesim_node + m12_control
# varianta open-loop, manual:
ros2 run turtlesim turtlesim_node
ros2 run curs_ros2 m12_patrat

# M13 proiect final
ros2 launch curs_ros2 m13_proiect_launch.py
ros2 topic echo /senzor/alarma
ros2 service call /ajusteaza_prag curs_ros2_interfaces/srv/AjustareTemperatura "{prag_nou: 35.0}"
ros2 param get /monitor_temperatura prag_atentie
```

Limitari de pornire (verificate in cod):
- M12 cere `turtlesim` instalat (`exec_depend` in package.xml; pe Jazzy de obicei
  prezent, altfel `sudo apt install ros-jazzy-turtlesim`).
- M6 si M11 ruleaza pe MultiThreadedExecutor intentionat: M6 fiindca pasul de
  lucru blocheaza 0.5 s, M11 fiindca raspunsul la tranzitii poate expira pe un
  executor single-threaded.
- M7 si M13 NU pornesc daca `curs_ros2_interfaces` nu a fost construit si
  "source"-uit (ImportError pe tipul custom).

## 7. Verificare

```bash
# nucleul pur (recomandat -- rapid, fara ROS):
cd ~/ros2_ws
python3 -m pytest src/curs_ros2/test/test_logica.py -v
```

Rezultat real masurat in acest mediu: `7 passed in 0.02s` (7 teste pe cele 4
functii din `logica.py` -- clasificare temperatura cu praguri implicite si
custom, normalizare unghi pe interval, eroare de distanta, unghi spre tinta).

Nota privind `colcon test`: pe unele instalari, harness-ul apeleaza
`python -m unittest`, care NU descopera testele scrise ca functii `def test_*()`
din `test/`; de aceea verificarea recomandata este comanda `pytest` de mai sus.
Fisierele `test_flake8.py`, `test_pep257.py`, `test_copyright.py` sunt linterele
standard din sablonul ROS 2 (verifica stil/licenta pe workspace, nu logica
cursului) si nu produc cifre de validare functionala.

Smoke ROS (necesita mediu ROS pornit): pornirea fiecarui launch de mai sus si
inspectia topicelor/serviciilor cu `ros2 topic echo`, `ros2 service call`,
`ros2 lifecycle set`, `ros2 run tf2_tools view_frames`. Aceste verificari sunt
live (necesita daemon/discovery activ) si nu produc un numar de "teste".

## 8. Igiena datelor si reproductibilitate

- Pachet didactic: NU genereaza date brute de campanie, NU contine figuri sau
  CSV de masurare, deci nu pune probleme de igiena a datelor (spre deosebire de
  pachetele de cercetare). Nu intra in arhiva `~/c1_archive/`.
- Reproductibilitate: senzorul M13 este DETERMINIST (contor intern, nu ceasul
  real), deci oricine ruleaza nodul vede aceeasi unda si aceleasi treceri
  NORMAL -> ATENTIE -> CRITIC. Castigurile de control M12 (4.0 pe rotatie,
  1.5 pe deplasare) sunt alese empiric si documentate in sursa.
- `.gitignore` la nivel de workspace exclude `build/`, `install/`, `log/`,
  `__pycache__/`, `*.pyc`. Directoarele `curs_ros2/__pycache__/`,
  `launch/__pycache__/`, `.pytest_cache/` din arbore sunt artefacte locale de
  rulare si nu trebuie comise.
- Dupa orice modificare in `setup.py`/`setup.cfg`: `rm -rf build install &&
  colcon build`, fiindca wrapper-ele de executabile se genereaza la build (vezi
  capcanele din CLAUDE.md). `Package 'curs_ros2' not found` dupa build inseamna
  ca ai uitat `source install/setup.bash`.
