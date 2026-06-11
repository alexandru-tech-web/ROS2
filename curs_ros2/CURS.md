# Curs complet ROS 2 Jazzy — pachetul `curs_ros2`

Un curs practic, de la zero la proiect integrator, pe **ROS 2 Jazzy** cu **rclpy** (Python 3.12).
Fiecare modul are **cod care ruleaza** + o **lectie** (`docs/`) cu explicatii, comenzi, verificari, exercitii si capcane.

> Filosofia cursului (regula de aur a acestui workspace): **nucleu pur + teste inainte de orice rulare live.**
> Logica importanta sta in [`curs_ros2/logica.py`](curs_ros2/logica.py), are teste in [`test/test_logica.py`](test/test_logica.py),
> si abia apoi e imbracata in noduri ROS. Asa prinzi defectele in milisecunde, nu in Gazebo.

---

## Cum pornesti (o singura data)

```bash
# dependinte (turtlesim, example_interfaces, tf2 sunt de obicei deja instalate cu Jazzy)
sudo apt install -y ros-jazzy-turtlesim ros-jazzy-example-interfaces

cd ~/ros2_ws
colcon build --packages-select curs_ros2_interfaces   # intai interfetele custom
colcon build --packages-select curs_ros2              # apoi cursul
source install/setup.bash
```

În **fiecare terminal nou**:

```bash
source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash
```

---

## Harta cursului

| # | Modul | Ce inveti | Cod / comanda principala | Lectie |
|---|-------|-----------|--------------------------|--------|
| M0 | Introducere & CLI | concepte, workspace, colcon, comenzi `ros2` | — | [00_introducere.md](docs/00_introducere.md) · [cheatsheet](docs/cheatsheet_cli.md) |
| M1 | Noduri | clasa `Node`, logger, timer, `spin` | `ros2 run curs_ros2 nod_simplu` | [01_noduri.md](docs/01_noduri.md) |
| M2 | Topics (pub/sub) | publish/subscribe, tipuri de mesaj | `publisher` + `subscriber` | [02_topics.md](docs/02_topics.md) |
| M3 | Launch & orchestrare | fisiere launch, `Node`, `TimerAction` | `ros2 launch curs_ros2 m3_launch.py` | [03_launch.md](docs/03_launch.md) |
| M4 | Parametri | `declare_parameter`, callback, YAML | `ros2 run curs_ros2 m4_param` | [04_parametri.md](docs/04_parametri.md) |
| M5 | Servicii | cerere/raspuns, client async | `m5_server` + `m5_client` | [05_servicii.md](docs/05_servicii.md) |
| M6 | Actiuni | goal/feedback/result, anulare | `m6_action_server` + `m6_action_client` | [06_actiuni.md](docs/06_actiuni.md) |
| M7 | Interfete custom | `.msg/.srv/.action`, pachet de interfete | `m7_pub` + `m7_sub` | [07_interfete_custom.md](docs/07_interfete_custom.md) |
| M8 | QoS | reliability/durability/history; incompatibilitati | `m8_pub` + `m8_sub` | [08_qos.md](docs/08_qos.md) |
| M9 | Executors | single vs multi-thread, callback groups | `ros2 run curs_ros2 m9_executor` | [09_executors.md](docs/09_executors.md) |
| M10 | TF2 | frame-uri, broadcaster/listener, arbore TF | `ros2 launch curs_ros2 m10_tf_launch.py` | [10_tf2.md](docs/10_tf2.md) |
| M11 | Lifecycle nodes | masina de stari, tranzitii gestionate | `ros2 run curs_ros2 m11_lifecycle` | [11_lifecycle.md](docs/11_lifecycle.md) |
| M12 | Turtlesim (practic) | `cmd_vel`/`pose`, control proportional | `ros2 launch curs_ros2 m12_turtle_launch.py` | [12_turtlesim.md](docs/12_turtlesim.md) |
| M13 | Proiect final | integrare M2+M4+M5+M7 + nucleu testat | `ros2 launch curs_ros2 m13_proiect_launch.py` | [13_proiect_final.md](docs/13_proiect_final.md) |

---

## Structura pachetului

```text
curs_ros2/
├── CURS.md                  <- esti aici (indexul cursului)
├── docs/                    <- o lectie .md per modul + cheatsheet CLI
├── curs_ros2/               <- nodurile (cod Python)
│   ├── logica.py            <- nucleul PUR, testat (folosit de M12 si M13)
│   ├── m1_*.py  m4_*.py  ...  m13_*.py
├── launch/                  <- fisierele de launch (m3, m4, m5, m10, m12, m13)
├── config/                  <- m4_params.yaml
├── test/                    <- test_logica.py + verificarile ament standard
├── setup.py / package.xml   <- entry points si dependinte

curs_ros2_interfaces/        <- pachet ament_cmake separat (M7): Temperatura.msg,
                                AjustareTemperatura.srv, Incalzire.action
```

> Interfetele custom stau intr-un pachet `ament_cmake` separat (`curs_ros2_interfaces`)
> pentru ca generatorul `rosidl` **nu** functioneaza intr-un pachet pur Python. Detalii in [M7](docs/07_interfete_custom.md).

---

## Rulezi testele

```bash
cd ~/ros2_ws
# testele nucleului pur (modul recomandat — rapid si mereu verde):
python3 -m pytest src/curs_ros2/test/test_logica.py -v
```

> Notă: `python3 -m pytest` este modul corect de a rula testele ROS 2 (stil pytest).
> Pe unele instalări `colcon test` apelează `python -m unittest`, care nu descoperă
> testele scrise ca funcții `def test_*()` din `test/` — deci preferă comanda pytest de mai sus.
> Fișierele `test/test_flake8.py`, `test_pep257.py`, `test_copyright.py` sunt linterele
> standard din șablonul ROS 2 (verifică stil/licență pe tot workspace-ul, nu logica cursului).

## Traseu recomandat

M0 → M1 → M2 → M3 (bazele) → M4 → M5 → M6 (comunicare) → M7 (tipuri proprii) →
M8 → M9 → M10 → M11 (avansat) → M12 (practic) → **M13 (capstone)**.
