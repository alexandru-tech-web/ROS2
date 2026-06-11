# Modulul 0 — Introducere în ROS 2 și CLI

## Ce înveți

- Ce este ROS 2 și la ce folosește.
- Conceptele de bază: Nod, Topic, Serviciu, Acțiune, Parametru și stratul DDS/RMW.
- Ce este un workspace, ce face `colcon` și ce înseamnă „overlay-ul”.
- Cum este structurat un pachet `ament_python`.
- Harta completă a celor 14 module ale cursului (M0–M13).

---

## Ce este ROS 2?

**ROS 2** (Robot Operating System 2) **nu** este un sistem de operare în sensul clasic (precum Linux sau Windows). Este un **middleware** — un set de biblioteci și unelte care îți permit să scrii programe (numite **noduri**) ce comunică între ele într-un mod standardizat, fără să te intereseze pe ce calculator rulează fiecare.

Folosește la a construi roboți și sisteme distribuite: un nod citește datele de la un senzor, altul ia decizii, altul comandă motoarele — și toate vorbesc între ele printr-un „limbaj” comun.

### Analogie: ROS = sistemul nervos al robotului

Gândește-te la un robot ca la un organism:

- **Senzorii** (camere, lasere, termometre) sunt ca **simțurile**.
- **Motoarele și actuatorii** sunt ca **mușchii**.
- **Codul de decizie** este ca **creierul**.

ROS 2 este **sistemul nervos**: rețeaua de „nervi” prin care impulsurile (mesajele) circulă de la simțuri la creier și de la creier la mușchi. Fiecare „nerv” este un **topic** sau un **serviciu**, iar fiecare „organ” care procesează ceva este un **nod**.

---

## Conceptele de bază

### Nod (Node)

Un **nod** este un program mic, cu o singură responsabilitate (un proces). De exemplu: „nodul care citește termometrul” sau „nodul care aprinde alarma”. Un sistem ROS 2 este format din mulți noduri care rulează în paralel și comunică între ei.

### Topic (publish / subscribe)

Un **topic** este un canal cu nume (de ex. `/temperatura`) pe care circulă mesaje într-un singur sens, continuu.

- Un nod **publisher** **publică** mesaje pe topic (nu îi pasă cine ascultă).
- Unul sau mai mulți **subscriber** **se abonează** și primesc fiecare mesaj.

Analogie: ca o **stație de radio**. Stația emite (publisher); oricine pornește un radio pe acea frecvență aude (subscriber). Emițătorul nu știe câți ascultă. Comunicarea este **anonimă și many-to-many**.

> Exemplu din curs: nodul `publisher` emite valori pe `/temperatura`, iar `subscriber` ascultă și publică un verdict pe `/alarma`.

### Serviciu (cerere / răspuns)

Un **serviciu** este o comunicare **bidirecțională, 1-la-1**, de tip **cerere → răspuns**. Clientul trimite o cerere și **așteaptă** un răspuns.

Analogie: ca un **apel telefonic**. Întrebi ceva, celălalt răspunde, gata. Se folosește pentru operații rapide care au nevoie de un rezultat (de ex. serviciul `/aduna` din M5: trimiți două numere, primești suma).

### Acțiune (Action)

O **acțiune** este pentru **task-uri de durată** care trebuie să dea **feedback pe parcurs** și pot fi **anulate**. Are trei părți: `goal` (obiectivul trimis), `feedback` (progres periodic) și `result` (rezultatul final).

Analogie: ca o **comandă la un curier**. Plasezi comanda (goal), primești notificări „pachetul a plecat / e în drum / aproape gata” (feedback), poți anula, iar la final primești pachetul (result). Exemplu din curs: acțiunea `/fibonacci` din M6.

### Parametru (Parameter)

Un **parametru** este o valoare de configurare a unui nod, citită la pornire și (opțional) modificabilă în timpul rulării — de ex. pragul de alarmă sau frecvența de publicare. Te scapă de a „hardcoda” valori în cod.

Analogie: butoanele de **setări** ale unui aparat (volumul, temperatura țintă), pe care le poți schimba fără să reconstruiești aparatul.

### Stratul DDS / RMW (middleware-ul)

Sub capotă, ROS 2 nu inventează propriul protocol de rețea. Folosește **DDS** (Data Distribution Service), un standard industrial de mesagerie. Legătura dintre `rclpy`/`rclcpp` și DDS se face prin **RMW** (ROS MiddleWare interface), un strat de adaptare.

- **DDS** se ocupă de descoperirea automată a nodurilor și de transportul mesajelor (inclusiv pe mai multe calculatoare din aceeași rețea).
- **RMW** permite schimbarea implementării DDS (Fast DDS, Cyclone DDS etc.) fără a-ți rescrie codul.

Analogie: tu vorbești „românește” (API-ul `rclpy`), iar RMW/DDS sunt **traducătorii și poșta** care duc efectiv mesajele de la un nod la altul.

---

## Workspace, colcon și overlay

### Workspace

Un **workspace** este un folder unde îți ții pachetele și unde le compilezi. Structura tipică:

```
ros2_ws/
├── src/          # codul tău sursă (pachetele)
├── build/        # fișiere intermediare de compilare (generat)
├── install/      # rezultatul instalat, gata de rulat (generat)
└── log/          # jurnale de build/test (generat)
```

Tu scrii doar în `src/`. Restul folderelor sunt generate automat de `colcon`.

### colcon

**colcon** este unealta de build a ROS 2. Cele mai folosite comenzi:

```bash
# Compilezi tot workspace-ul
colcon build

# Compilezi doar un pachet (mai rapid)
colcon build --packages-select curs_ros2

# Legi codul prin symlink (modifici .py fara recompilare)
colcon build --symlink-install
```

> Sfat: rulezi `colcon build` **din rădăcina workspace-ului** (`~/ros2_ws`), nu din `src/`.

### Overlay (`source install/setup.bash`)

ROS 2 lucrează prin „straturi” (layers) care se suprapun:

- **Underlay** = instalarea de bază: `source /opt/ros/jazzy/setup.bash`.
- **Overlay** = workspace-ul tău, peste cel de bază: `source ~/ros2_ws/install/setup.bash`.

A face `source` înseamnă a încărca în terminalul curent variabilele de mediu care îi spun lui ROS 2 unde să găsească pachetele tale. **Într-un terminal nou trebuie să faci din nou `source`**, altfel `ros2 run curs_ros2 ...` nu va găsi pachetul.

```bash
# Ordinea corecta intr-un terminal nou:
source /opt/ros/jazzy/setup.bash      # mai intai baza (underlay)
source ~/ros2_ws/install/setup.bash   # apoi workspace-ul tau (overlay)
```

---

## Structura unui pachet `ament_python`

Pachetul nostru `curs_ros2` este de tip **ament_python** (pachet Python pur). Componentele:

```
curs_ros2/
├── package.xml          # manifest: nume, versiune, dependinte, licenta
├── setup.py             # build Python + entry_points (mapeaza comenzile)
├── setup.cfg            # config: unde se instaleaza executabilele
├── resource/
│   └── curs_ros2        # marker gol pentru indexul ament
├── curs_ros2/           # folderul cu noduri (modulul Python)
│   ├── __init__.py
│   ├── m1_nod_simplu.py
│   ├── m1_publisher.py
│   └── m1_subscriber.py
├── launch/              # fisiere de launch (orchestrare)
│   └── m3_launch.py
└── docs/                # materialul de curs (acest folder)
```

Câteva detalii cheie:

- **`package.xml`** declară numele pachetului și **dependențele** (de ex. `rclpy`, `std_msgs`). Tu **nu** îl editezi în acest curs.
- **`setup.py`** conține `entry_points` care leagă o **comandă** de o **funcție `main()`** dintr-un modul. De exemplu:

  ```python
  'publisher = curs_ros2.m1_publisher:main',
  ```

  înseamnă: `ros2 run curs_ros2 publisher` rulează funcția `main()` din `m1_publisher.py`. De aceea numele modulului și al funcției `main()` trebuie să rămână **exact** cum sunt.
- **`resource/curs_ros2`** este un fișier gol (marker) prin care ament „știe” că pachetul există.
- **`launch/`** ține fișierele de orchestrare (pornesc mai multe noduri deodată).

---

## Harta cursului (M0–M13)

| #   | Titlu modul                       | Ce înveți                                                              | Fișiere / comanda principală                          |
|-----|-----------------------------------|-----------------------------------------------------------------------|-------------------------------------------------------|
| M0  | Introducere & CLI                 | Concepte de bază, structura pachetului, comenzile `ros2`              | `docs/00_introducere.md`, `docs/cheatsheet_cli.md`    |
| M1  | Noduri *(are cod)*                | Ce e un nod, ciclul de viață minim, logging                          | `m1_nod_simplu.py` · `ros2 run curs_ros2 nod_simplu`  |
| M2  | Topics (publisher/subscriber) *(are cod)* | Publish/subscribe pe `/temperatura` și `/alarma`             | `m1_publisher.py`, `m1_subscriber.py` · `ros2 run curs_ros2 publisher` |
| M3  | Launch & orchestrare *(are cod)*  | Pornirea mai multor noduri dintr-un fișier de launch                 | `launch/m3_launch.py` · `ros2 launch curs_ros2 m3_launch.py` |
| M4  | Parametri                         | Declararea, citirea și schimbarea parametrilor                       | `ros2 param list / get / set`                         |
| M5  | Servicii                          | Cerere/răspuns sincron pe serviciul `/aduna`                         | `ros2 service call /aduna ...`                        |
| M6  | Acțiuni                           | Task-uri lungi cu feedback și anulare pe `/fibonacci`                | `ros2 action send_goal /fibonacci ... --feedback`     |
| M7  | Interfețe custom                  | Definirea propriilor `.msg`, `.srv`, `.action`                       | `ros2 interface show ...`                             |
| M8  | QoS                               | Politici de calitate a serviciului (reliability, durability)         | `ros2 topic info --verbose`                           |
| M9  | Executors & callback groups       | Cum rulează callback-urile în paralel sau serial                     | `MultiThreadedExecutor`                               |
| M10 | TF2 (transformări)                | Sisteme de coordonate și transformări între cadre                    | `ros2 run tf2_tools view_frames`                      |
| M11 | Lifecycle nodes                   | Noduri cu stări gestionate (configure/activate/...)                  | `ros2 lifecycle set ...`                              |
| M12 | Turtlesim (practic)               | Aplicarea conceptelor pe simulatorul țestoasei                       | `ros2 run turtlesim turtlesim_node`                   |
| M13 | Proiect final (capstone)          | Integrare: noduri + topics + servicii + acțiuni + launch             | proiect propriu                                       |

> **Notă:** Modulele **M1–M3 au deja cod scris în pachet** (fișierele `.py` din `curs_ros2/` și `launch/`). Restul modulelor sunt construite pas cu pas pe parcursul cursului.

---

## Următorul pas

Deschide [`cheatsheet_cli.md`](cheatsheet_cli.md) — foaia de comenzi `ros2` pe care o vei folosi în fiecare modul. Apoi treci la **M1 (Noduri)**.
