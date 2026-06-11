# Modul 3 — Launch & orchestrare

## Ce înveți

- Ce este un **launch file** scris în Python și de ce îl folosim.
- Cum funcționează `generate_launch_description()` și ce returnează.
- Cum pornești un nod cu acțiunea `Node` din `launch_ros`, plus rolul lui `output="screen"`.
- Cum întârzii pornirea unui nod cu `TimerAction`.
- Cum parametrizezi un launch cu `DeclareLaunchArgument` și `LaunchConfiguration` (extensie).
- Cum verifici că ambele noduri rulează (`ros2 node list`, `rqt_graph`).

---

## Conceptul, pe scurt

Până acum porneai fiecare nod manual, într-un terminal separat: un `ros2 run` pentru publisher, alt `ros2 run` pentru subscriber. Asta merge pentru 2 noduri, dar un robot real are 10–20 de procese (driver de motoare, senzor LIDAR, localizare, planificare, RViz...). Să le pornești pe rând, în ordinea corectă, devine imposibil.

> **Analogie:** un launch file este ca lista de verificare a unui pilot înainte de decolare. În loc să apeși fiecare buton din memorie, ai o procedură scrisă care pornește totul, în ordinea bună, cu setările corecte — de fiecare dată la fel.

Un **launch file** este, practic, un script Python care **descrie** ce procese trebuie pornite și cu ce configurație. Tu nu pornești nodurile direct din el; tu construiești o "rețetă" (un obiect `LaunchDescription`), iar sistemul de launch al ROS 2 o execută.

---

## Codul-cheie comentat

Fișierul nostru este `launch/m3_launch.py`. El pornește publisher-ul imediat și subscriber-ul după 3 secunde.

```python
from launch import LaunchDescription
from launch_ros.actions import Node          # acțiunea care pornește un nod ROS 2
from launch.actions import TimerAction       # acțiune care întârzie alte acțiuni

# Sistemul de launch caută EXACT această funcție, cu acest nume.
# Ea trebuie sa returneze un obiect LaunchDescription.
def generate_launch_description():

    # Node = "pornește un executabil ROS 2".
    # package    -> numele pachetului (cel din package.xml / setup.py)
    # executable -> entry point-ul din setup.py (NU numele fișierului .py)
    # name       -> redenumește nodul la rulare (suprascrie numele din cod)
    # output     -> 'screen' trimite log-urile în terminal, ca să le vezi live
    publisher = Node(
        package='curs_ros2',
        executable='publisher',
        name='publisher_temperatura',
        output='screen'
    )

    # Vrem ca subscriber-ul să pornească DUPĂ publisher, ca topicul /temperatura
    # să existe deja. TimerAction amână acțiunile din 'actions' cu 'period' secunde.
    subscriber = TimerAction(
        period=3.0,                 # întârziere de 3 secunde
        actions=[
            Node(
                package='curs_ros2',
                executable='subscriber',
                name='subscriber_temperatura',
                output='screen'
            )
        ]
    )

    # Ordinea din listă NU garantează ordinea în timp (procesele pornesc în paralel).
    # Întârzierea temporală o dă TimerAction, nu poziția în listă.
    return LaunchDescription([publisher, subscriber])
```

Câteva idei importante de reținut:

- `executable='publisher'` se referă la **entry point-ul** definit în `setup.py`
  (`'publisher = curs_ros2.m1_publisher:main'`), nu la fișierul `m1_publisher.py`.
- `output='screen'` este motivul pentru care vezi mesajele `self.get_logger().info(...)`
  direct în terminalul de launch. Fără el, log-urile ajung doar în fișierele de jurnal.
- `TimerAction` nu blochează nimic: publisher-ul rulează deja, iar subscriber-ul este
  doar programat să pornească mai târziu.

### Extensie: argumente de launch (`DeclareLaunchArgument` + `LaunchConfiguration`)

Valorile "hard-codate" (ca `period=3.0`) sunt comode, dar inflexibile. Dacă vrei să schimbi întârzierea fără să modifici fișierul, o transformi într-un **argument de launch**:

```python
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import TimerAction, DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():

    # 1) Declari un argument cu o valoare implicită (text!).
    arg_intarziere = DeclareLaunchArgument(
        'intarziere',
        default_value='3.0',
        description='Cate secunde sa astepte pana porneste subscriber-ul'
    )

    # 2) LaunchConfiguration este o "referință" la valoarea argumentului,
    #    rezolvată abia la rulare (nu este un float Python obișnuit acum).
    intarziere = LaunchConfiguration('intarziere')

    publisher = Node(
        package='curs_ros2', executable='publisher',
        name='publisher_temperatura', output='screen'
    )

    subscriber = TimerAction(
        period=intarziere,          # acceptă și o substituție, nu doar un număr
        actions=[Node(
            package='curs_ros2', executable='subscriber',
            name='subscriber_temperatura', output='screen'
        )]
    )

    return LaunchDescription([arg_intarziere, publisher, subscriber])
```

Apoi îl rulezi cu o valoare la alegere:

```bash
ros2 launch curs_ros2 m3_launch.py intarziere:=5.0
```

> Reține: argumentele de launch sunt mereu **șiruri de caractere**. De aceea `default_value` este `'3.0'` (cu ghilimele), nu `3.0`.

---

## Cum rulezi

Lucrăm dintr-un singur terminal pentru launch (el pornește ambele noduri).

**T1 — construiește pachetul și pornește launch-ul:**

```bash
cd ~/ros2_ws
colcon build --packages-select curs_ros2
source install/setup.bash
ros2 launch curs_ros2 m3_launch.py
```

Ar trebui să vezi întâi log-urile publisher-ului, iar după ~3 secunde apar și cele ale subscriber-ului (`Subscriber pornit, ascult /temperatura...` urmat de liniile cu temperatura).

> Oprire: `Ctrl+C` în T1. Launch-ul oprește **toate** procesele pe care le-a pornit.

---

## Verificare

Lasă launch-ul pornit în T1 și deschide un terminal nou.

**T2 — verifică nodurile și topicurile:**

```bash
source ~/ros2_ws/install/setup.bash

# Ambele noduri trebuie să apară:
ros2 node list
# Așteptat:
#   /publisher_temperatura
#   /subscriber_temperatura

# Topicul de date trebuie să existe:
ros2 topic list
# Așteptat (printre altele): /temperatura  și  /alarma

# Confirmă că circulă mesaje:
ros2 topic echo /temperatura
```

**T3 — graful de noduri (vizual):**

```bash
source ~/ros2_ws/install/setup.bash
rqt_graph
```

În fereastra `rqt_graph` ar trebui să vezi `publisher_temperatura` legat prin `/temperatura` de `subscriber_temperatura`. Dacă nu apare săgeata, apasă butonul de refresh și asigură-te că este selectat "Nodes/Topics (all)".

---

## Exerciții

1. **Remapare de topic.** Adaugă la nodul publisher (sau subscriber) un argument `remappings` ca să redenumești topicul:
   ```python
   Node(
       package='curs_ros2',
       executable='publisher',
       name='publisher_temperatura',
       output='screen',
       remappings=[('/temperatura', '/temp2')]
   )
   ```
   Remapează în AMBELE noduri ca să rămână conectate, apoi confirmă cu `ros2 topic list` că acum apare `/temp2`.

2. **Al treilea nod.** Pornește în același launch și nodul `nod_simplu` (entry point-ul există deja în `setup.py`). Verifică cu `ros2 node list` că ai acum trei noduri active.

3. **Întârziere parametrizabilă.** Transformă valoarea `period=3.0` într-un argument de launch folosind `DeclareLaunchArgument` + `LaunchConfiguration` (vezi secțiunea de extensie) și pornește-l cu `ros2 launch curs_ros2 m3_launch.py intarziere:=1.0`.

---

## Capcane frecvente

- **Ai uitat să instalezi folderul `launch/` în `setup.py`.** Dacă `ros2 launch` spune că nu găsește `m3_launch.py`, înseamnă că `data_files` nu copiază fișierele de launch în `share/`. Trebuie să existe linia:
  ```python
  (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
  ```
  (în pachetul nostru este deja adăugată).

- **Ai uitat să reconstruiești după modificări.** Launch-ul rulează din `install/`, nu din `src/`. După ce modifici `m3_launch.py` (sau orice nod), rulează din nou:
  ```bash
  colcon build --packages-select curs_ros2 && source install/setup.bash
  ```
  Altfel rulezi versiunea veche și pari să "nu se schimbe nimic".

- **`executable` greșit.** Valoarea de la `executable=` este **entry point-ul** din `setup.py`, nu numele fișierului `.py`. Folosește `publisher`, nu `m1_publisher`.

- **Te aștepți ca ordinea din listă să dea ordinea în timp.** Acțiunile dintr-un `LaunchDescription` pornesc în paralel. Singurul lucru care întârzie subscriber-ul este `TimerAction`, nu poziția lui în listă.

- **`output='screen'` lipsă.** Dacă "nu vezi niciun log", probabil ai uitat `output='screen'`; mesajele există, dar merg doar în fișierele de jurnal.

- **Nu ai dat `source install/setup.bash` în terminalul nou.** În T2/T3, fără `source`, comenzile `ros2 node list` / `rqt_graph` nu văd pachetul și par să nu găsească nimic.
