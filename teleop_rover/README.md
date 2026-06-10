# Teleop Rover — teleoperarea în timp real a unui rover prin legătură degradată

**A doua aplicație de teză, complementară roiului SAR: acolo se măsoară controlul *supervizor* (comenzi discrete: du-te, stai); aici se măsoară cazul dur al „controlului la distanță în timp real" — bucla închisă om→robot→om care trece prin rețeaua degradată DE DOUĂ ORI (comanda la dus, feedback-ul la întors). Metricile sunt de APLICAȚIE: eroarea de urmărire, timpul de parcurs, opririle de siguranță — adică „ce înseamnă 200 ms p95 pentru operator", etajul care lipsea peste benchmarkul de transport (C1).**

![ROS 2](https://img.shields.io/badge/ROS_2-Jazzy-blue) ![Gazebo](https://img.shields.io/badge/Gazebo-Harmonic-orange) ![Teste](https://img.shields.io/badge/teste-17%20trec-green)

## Bucla, pe scurt

```
operator (pilot-model SAU om la tastatură)
   │  comenzi v,ω @ 20 Hz ──▶ [legătura degradată: latență+jitter+pierdere+tăiere]
   │                                  │
   │                                  ▼
   │                        STRATUL DE SIGURANȚĂ al robotului:
   │                        watchdog 0.4 s + respinge comenzile > 1 s vechime
   │                                  │
   ▼                                  ▼
poza ◀── [aceeași legătură degradată] ◀── rover diferențial (intern sau Gazebo)
```

Cheia experimentală: pilotul decide pe **ultima poză care a supraviețuit legăturii** (veche, posibil lipsă) — exact ce vede un operator real. „Operatorul" implicit e un **pilot-model** (pure pursuit), ca rulările să fie perfect repetabile: aceleași N rulări pe fiecare condiție de rețea → curbe comparabile. Modul `manual` (W/A/S/D, fereastră cu traseul + vârstele) îți dă senzația fizică a 500 ms de latență.

## Rezultate măsurate (SIL: 5 rulări/condiție, jitter = 20% din latență)

| Latență (un sens) | pierdere 0% | pierdere 30% |
|---|---|---|
| 0 ms | 29.5 s, CTE p95 0.85 m, 0 opriri | 29.6 s, 0.84 m, 0 opriri |
| 100 ms | 30.2 s, 0.78 m, 0 | 30.7 s, 0.77 m, 0 |
| 200 ms | 34.1 s, 0.79 m, 0 | 35.9 s, 0.83 m, 0 |
| 500 ms | **timeout 120 s**, 1.14 m, 0 | timeout, 1.14 m, 0.8 opriri |
| 1000 ms | timeout, **12.1 m**, 8.2 opriri | timeout, 12.1 m, **35.6 opriri** |

Citirea de teză (figura `results/teleop_sweep.png`): bucla e **stabilă până la ~200 ms** (doar timpul crește ușor), **se rupe între 200 și 500 ms** (pilotul orbitează porțile pe date vechi — misiunea nu se mai termină), iar la **1000 ms** comenzile încalcă pragul de vechime → stratul de siguranță refuză mișcarea (furtună de opriri, amplificată de pierdere: 8 → 35 opriri/rulare). Sistemul **eșuează în siguranță**, nu în instabilitate necontrolată. Pragul de rupere e condus de latență, nu de pierdere — complementar concluziei din SAR (acolo latența de 2 s durea mai mult ca pierderea de 30%).

## Structura

```text
teleop_rover/
├── rover_core.py        nucleul PUR: cinematică, traseu+CTE, pilot, SafetyGate
├── netem_core.py        canalul degradat (copie identică, testată, din sar_swarm)
├── sil_teleop.py        bucla închisă fără ROS + figura unei rulări (--plot)
├── sweep_teleop.py      EXPERIMENTUL: grila latență×pierdere → sweep.csv + figura
├── plot_trace.py        figura unei rulări REALE din jurnalul robotului
├── test_rover_core.py   17 verificări (cinematică, CTE, watchdog, pilot end-to-end)
├── robot_node.py        roverul ROS: gating la recepție + SafetyGate + jurnal-traseu
├── operator_node.py     operatorul ROS: pilot (repetabil) sau manual (fereastră W/A/S/D)
├── link_node.py         legătura: /teleop/linkstate din parametri sau LIVE
├── gen_rover_world.py   lumea Gazebo DIN rover_core (porțile = traseul CTE-ului)
├── launch/teleop.launch.py          fără Gazebo (banc RMW pe metrici de aplicație)
├── launch/teleop_gazebo.launch.py   cu roverul în Gazebo (plugin DiffDrive)
└── worlds/teleop_course.sdf         generată (XML validat)
```

## Rulare

```bash
cd ~/ros2_ws/src/teleop_rover

# 0) verificările + experimentul complet, FĂRĂ ROS (oriunde):
python3 test_rover_core.py
python3 sil_teleop.py --lat 200 --jit 40 --loss 0.1 --plot
python3 sweep_teleop.py            # ~75 rulări → results/teleop_sweep.png

# 1) ROS pur — pilotul-model prin legătura degradată:
source /opt/ros/jazzy/setup.bash
ros2 launch ./launch/teleop.launch.py lat:=200 jit:=40 loss:=0.1 mode:=pilot
#   la final: "TRASEU TERMINAT in ..."; apoi figura rulării reale:
python3 plot_trace.py ~/teleop_data/robot_log.csv

# 2) TU la manșă, cu 500 ms de latență (fereastra W/A/S/D):
ros2 launch ./launch/teleop.launch.py lat:=500 jit:=100 mode:=manual

# 3) același lucru cu roverul în Gazebo:
python3 gen_rover_world.py
ros2 launch ./launch/teleop_gazebo.launch.py lat:=200 mode:=manual

# schimbarea legăturii ÎN TIMPUL rulării:
ros2 topic pub --once /teleop/operator std_msgs/msg/String \
  "{data: '{\"action\": \"set_all\", \"ms\": 800, \"loss\": 0.3}'}"
```

**Comparația RMW pe metrici de aplicație** (etajul nou peste C1): aceeași comandă de la punctul 1, rulată o dată cu `export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` și o dată cu `rmw_zenoh_cpp` (+ `ros2 run rmw_zenoh_cpp rmw_zenohd` în alt terminal); compari `robot_log.csv` între rulări. Pe mașini separate, înlocuiești `link_node` cu **tc netem real** pe interfață — nodurile nu se schimbă.

## Stratul de siguranță (măsurabil, nu doar declarat)

`SafetyGate` (în `rover_core.py`, 6 teste dedicate): robotul **se oprește** dacă n-a primit nicio comandă de 0.4 s (watchdog — opririle sunt numărate și apar în jurnale/figuri) și **ignoră** orice comandă mai veche de 1 s la sosire (o comandă de virare emisă acum 2 secunde e periculoasă, nu utilă). La 1000 ms latență acest strat e cel care transformă instabilitatea în imobilitate sigură — vizibil în panoul 3 al figurii de măturare.

## Onestitate

Nucleul, bucla SIL, măturarea (75 de rulări), analizorul și figurile au **rulat aici** (17 teste trec; cifrele din tabel sunt măsurate). Nodurile ROS, launch-urile și lumea Gazebo sunt verificate sintactic + XML, pe aceleași tipare deja confirmate funcționale la `sar_swarm` — prima rulare e la tine; jurnalul-traseu are exact formatul SIL, deci `plot_trace.py` merge identic pe ambele.

## Legătura cu restul ecosistemului

- `netem_core.py` e aceeași piesă testată din `sar_swarm` (sursă unică de comportament al canalului);
- modelul „nucleu pur + gating la recepție + jurnal local + analizor" e cel validat la SAR;
- același tipar se altoiește direct pe **tele-reabilitare** (sistemul de recuperare): `/exercise_cmd` prin aceeași legătură + SafetyGate pe controlerul de exerciții — direcția următoare naturală.

## Licență

Apache-2.0.
