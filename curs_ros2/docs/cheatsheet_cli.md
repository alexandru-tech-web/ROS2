# Cheatsheet CLI ROS 2 (Jazzy)

Foaie de comenzi rapide pentru linia de comandă `ros2`. Exemplele folosesc topicele și interfețele din curs: `/temperatura`, `/alarma`, serviciul `/aduna` și acțiunea `/fibonacci`.

> **Înainte de orice** (într-un terminal nou):
> ```bash
> source /opt/ros/jazzy/setup.bash
> source ~/ros2_ws/install/setup.bash
> ```

---

## Noduri

| Comandă                        | Ce face                                  | Exemplu                                         |
|--------------------------------|------------------------------------------|-------------------------------------------------|
| `ros2 run <pachet> <exe>`      | Pornește un nod (executabil din pachet)  | `ros2 run curs_ros2 publisher`                  |
| `ros2 node list`               | Listează nodurile active                 | `ros2 node list`                                |
| `ros2 node info <nod>`         | Detalii: publishers, subscribers, servicii | `ros2 node info /publisher_temperatura`       |

```bash
# Pornesti publisher-ul de temperatura
ros2 run curs_ros2 publisher

# Vezi ce noduri ruleaza acum
ros2 node list
# ex: /publisher_temperatura
#     /subscriber_temperatura

# Inspectezi un nod (ce publica, la ce se aboneaza)
ros2 node info /subscriber_temperatura
```

---

## Topice (Topics)

| Comandă                              | Ce face                                   | Exemplu                                          |
|--------------------------------------|-------------------------------------------|--------------------------------------------------|
| `ros2 topic list`                    | Listează topicele active                  | `ros2 topic list`                                |
| `ros2 topic echo <topic>`            | Afișează mesajele care circulă            | `ros2 topic echo /temperatura`                   |
| `ros2 topic info <topic>`            | Tipul mesajului + nr. de publishers/subs  | `ros2 topic info /temperatura`                   |
| `ros2 topic info <topic> --verbose`  | Inclusiv politicile QoS                    | `ros2 topic info /temperatura --verbose`         |
| `ros2 topic hz <topic>`              | Frecvența de publicare (Hz)               | `ros2 topic hz /temperatura`                     |
| `ros2 topic pub <topic> <tip> <date>`| Publică mesaje manual din terminal        | vezi mai jos                                     |

```bash
# Vezi toate topicele
ros2 topic list

# Asculti valorile de temperatura in timp real
ros2 topic echo /temperatura

# Vezi verdictul publicat de subscriber
ros2 topic echo /alarma

# Afli tipul si cati publica/asculta
ros2 topic info /temperatura

# Verifici cat de des se publica (ar trebui ~1 Hz)
ros2 topic hz /temperatura

# Publici manual o valoare pe /temperatura (o singura data)
ros2 topic pub --once /temperatura std_msgs/msg/Float64 "{data: 55.0}"

# Publici continuu, la 2 Hz
ros2 topic pub --rate 2 /temperatura std_msgs/msg/Float64 "{data: 42.0}"
```

---

## Servicii (Services)

| Comandă                                  | Ce face                              | Exemplu                                  |
|------------------------------------------|--------------------------------------|------------------------------------------|
| `ros2 service list`                      | Listează serviciile disponibile      | `ros2 service list`                      |
| `ros2 service type <serviciu>`           | Tipul `.srv` al serviciului          | `ros2 service type /aduna`               |
| `ros2 service call <serviciu> <tip> <date>` | Apelează serviciul (cerere→răspuns) | vezi mai jos                            |

```bash
# Vezi serviciile active
ros2 service list

# Afli tipul serviciului /aduna
ros2 service type /aduna
# ex: example_interfaces/srv/AddTwoInts

# Apelezi serviciul: trimiti a si b, primesti suma
ros2 service call /aduna example_interfaces/srv/AddTwoInts "{a: 7, b: 5}"
# raspuns asteptat: sum=12
```

---

## Acțiuni (Actions)

| Comandă                                            | Ce face                                | Exemplu                                       |
|----------------------------------------------------|----------------------------------------|-----------------------------------------------|
| `ros2 action list`                                 | Listează acțiunile disponibile         | `ros2 action list`                            |
| `ros2 action info <actiune>`                       | Detalii: server, clienți               | `ros2 action info /fibonacci`                 |
| `ros2 action send_goal <actiune> <tip> <goal>`     | Trimite un goal                        | vezi mai jos                                  |
| `... send_goal ... --feedback`                     | Trimite goal-ul și afișează feedback   | vezi mai jos                                  |

```bash
# Vezi actiunile active
ros2 action list

# Detalii despre actiunea /fibonacci
ros2 action info /fibonacci

# Trimiti un goal (calculeaza primii 10 termeni)
ros2 action send_goal /fibonacci example_interfaces/action/Fibonacci "{order: 10}"

# Acelasi goal, dar urmaresti progresul (feedback) pe parcurs
ros2 action send_goal /fibonacci example_interfaces/action/Fibonacci "{order: 10}" --feedback
```

---

## Parametri (Parameters)

| Comandă                                  | Ce face                                | Exemplu                                          |
|------------------------------------------|----------------------------------------|--------------------------------------------------|
| `ros2 param list`                        | Listează parametrii nodurilor active   | `ros2 param list`                                |
| `ros2 param get <nod> <param>`           | Citește valoarea unui parametru        | `ros2 param get /publisher_temperatura prag`     |
| `ros2 param set <nod> <param> <val>`     | Schimbă valoarea în timpul rulării      | `ros2 param set /publisher_temperatura prag 50.0`|
| `ros2 param dump <nod>`                  | Exportă toți parametrii într-un YAML    | `ros2 param dump /publisher_temperatura`         |
| `ros2 param load <nod> <fisier.yaml>`    | Încarcă parametri dintr-un YAML         | `ros2 param load /publisher_temperatura param.yaml` |

```bash
# Vezi toti parametrii nodului
ros2 param list /publisher_temperatura

# Citesti un parametru
ros2 param get /publisher_temperatura prag

# Il schimbi din mers
ros2 param set /publisher_temperatura prag 45.0

# Salvezi configuratia curenta intr-un fisier
ros2 param dump /publisher_temperatura > param.yaml

# O reincarci mai tarziu
ros2 param load /publisher_temperatura param.yaml
```

---

## Interfețe (Interfaces: msg / srv / action)

| Comandă                          | Ce face                                      | Exemplu                                              |
|----------------------------------|----------------------------------------------|------------------------------------------------------|
| `ros2 interface list`            | Listează toate interfețele disponibile       | `ros2 interface list`                                |
| `ros2 interface show <tip>`      | Arată structura unei interfețe               | `ros2 interface show std_msgs/msg/Float64`           |
| `ros2 interface proto <tip>`     | Generează un „prototip” (șablon) de mesaj    | `ros2 interface proto std_msgs/msg/Float64`          |

```bash
# Structura tipului folosit pe /temperatura
ros2 interface show std_msgs/msg/Float64

# Structura serviciului de adunare
ros2 interface show example_interfaces/srv/AddTwoInts

# Structura actiunii Fibonacci (goal/result/feedback)
ros2 interface show example_interfaces/action/Fibonacci

# Sablon gata de completat (util pentru topic pub / service call)
ros2 interface proto std_msgs/msg/Float64
```

---

## Launch (orchestrare)

| Comandă                              | Ce face                                     | Exemplu                                  |
|--------------------------------------|---------------------------------------------|------------------------------------------|
| `ros2 launch <pachet> <fisier>`      | Pornește mai multe noduri dintr-un fișier   | `ros2 launch curs_ros2 m3_launch.py`     |

```bash
# Porneste publisher + subscriber impreuna (M3)
ros2 launch curs_ros2 m3_launch.py
```

---

## Build & Test (colcon)

| Comandă                                       | Ce face                                       | Exemplu                                          |
|-----------------------------------------------|-----------------------------------------------|--------------------------------------------------|
| `colcon build`                                | Compilează tot workspace-ul                   | `colcon build`                                   |
| `colcon build --packages-select <pachet>`     | Compilează doar un pachet (mai rapid)         | `colcon build --packages-select curs_ros2`       |
| `colcon build --symlink-install`              | Leagă prin symlink (editezi `.py` fără rebuild)| `colcon build --symlink-install`                |
| `colcon test`                                 | Rulează testele                               | `colcon test --packages-select curs_ros2`        |

```bash
# Te muti in radacina workspace-ului
cd ~/ros2_ws

# Compilezi doar pachetul cursului
colcon build --packages-select curs_ros2

# Cu symlink: modifici fisierele .py fara sa reconstruiesti
colcon build --symlink-install

# Dupa build, NU uita sa faci source din nou
source ~/ros2_ws/install/setup.bash

# Rulezi testele pachetului
colcon test --packages-select curs_ros2
colcon test-result --verbose   # vezi rezultatele in detaliu
```

---

## Introspecție grafică

| Comandă                                  | Ce face                                          |
|------------------------------------------|--------------------------------------------------|
| `rqt_graph`                              | Graf vizual cu noduri și topice                  |
| `ros2 run rqt_graph rqt_graph`           | Pornește același graf prin `ros2 run`            |
| `ros2 run tf2_tools view_frames`         | Generează un PDF cu arborele de transformări TF  |

```bash
# Vezi vizual cine publica/asculta pe ce topic
rqt_graph

# Generezi un PDF cu cadrele TF (util in M10)
ros2 run tf2_tools view_frames
# rezulta frames.pdf in folderul curent
```

---

## Bag (înregistrare / redare)

| Comandă                                  | Ce face                                       | Exemplu                                          |
|------------------------------------------|-----------------------------------------------|--------------------------------------------------|
| `ros2 bag record <topice>`               | Înregistrează mesajele de pe topice           | `ros2 bag record /temperatura /alarma`           |
| `ros2 bag record -a`                      | Înregistrează toate topicele                  | `ros2 bag record -a`                             |
| `ros2 bag play <bag>`                     | Redă o înregistrare                           | `ros2 bag play rosbag2_2026_06_11/`              |
| `ros2 bag info <bag>`                     | Detalii despre înregistrare                   | `ros2 bag info rosbag2_2026_06_11/`              |

```bash
# Inregistrezi temperatura si alarma intr-un bag
ros2 bag record /temperatura /alarma

# Vezi ce contine bag-ul (durata, topice, nr. mesaje)
ros2 bag info rosbag2_2026_06_11/

# Il redai (mesajele apar din nou pe topice)
ros2 bag play rosbag2_2026_06_11/
```

---

## De reținut

> **În fiecare terminal nou**, înainte de orice comandă `ros2`, rulează:
> ```bash
> source /opt/ros/jazzy/setup.bash
> source ~/ros2_ws/install/setup.bash
> ```
> Întâi underlay-ul (`/opt/ros/jazzy`), apoi overlay-ul (workspace-ul tău). Fără acest pas, `ros2` nu va găsi pachetul `curs_ros2`.
