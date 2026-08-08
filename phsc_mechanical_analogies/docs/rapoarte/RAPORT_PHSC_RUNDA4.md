# RAPORT PHSC -- Runda 4

Data: 2026-08-08. Build 4/4 OK, 0 stderr, cod 100% ASCII.
5 executabile in `phsc_teleop_mpc`.

---

## 1. `latency_estimator` -- functioneaza?

**DA.** Testat pe loopback local (estimator + echo pe aceeasi masina):

```
/estimated_delay -> data: 0.0013488629211001102     (1.3 ms, corect pe loopback)
/delay_stats     -> [mean 1.46 ms, std 0.27 ms, min 0.75 ms, max 1.95 ms, loss 0.42%]
[INFO] tau_est = 1.1 ms (n=50, pierdere=0.8%)
```

**Am completat implementarea**: in codul primit, `send_ping()` era `pass`
(placeholder), deci nodul nu emitea niciodata un ping si nu putea produce
nicio masuratoare. Am implementat emiterea si am adaugat un nod pereche
`latency_echo` (partea remota, se ruleaza langa robot), fara de care bucla
ping-pong nu se inchide.

**Am corectat si o problema de fond in respingerea de outlieri.** Varianta
initiala respinge orice RTT la peste 3 sigma de medie -- dar o schimbare
REALA si sustinuta a latentei arata exact ca un sir de outlieri, deci
estimatorul ar fi ramas blocat pe regimul vechi la nesfarsit. Intr-o teza
despre latenta variabila, asta e chiar cazul care conteaza. Am adaugat un
contor: dupa `outlier_streak_max` (8) respingeri consecutive, acceptam
schimbarea de regim si repornim fereastra.

Adaugat suplimentar: detectie de legatura cazuta (avertisment daca nu mai vin
pong-uri), clamp pe `tau_max`, si contorizarea pierderilor.

Limitare de raportat: `tau = RTT/2` presupune canal simetric. Pe legaturi
asimetrice estimarea e partinitoare. De verificat pe HIL.

## 2. `safety_watchdog` -- functioneaza?

**DA**, toate cele patru garzi verificate live:

| test | rezultat |
|---|---|
| nicio stare primita de la pornire | `E-STOP: nicio stare primita in 3 s de la pornire`, `/safety_status false` |
| stare care se opreste in timpul functionarii | `E-STOP: stare lipsa de 309 ms`, `/safety_status false` |
| depasire limita de unghi | `E-STOP: theta=28.6 grade peste limita 10` |
| clamp comanda (cerut 500 N, `u_max`=50) | `/robot_cmd_safe` -> `x: 50.0` |
| comanda dupa e-stop | `x: 0.0`, publicata activ si repetat |
| reset explicit pe `/estop_reset` | `E-stop RESETAT (era: stare lipsa de 309 ms)` |

**Modificari fata de codul primit**, toate din cauze gasite la testare:

1. **Watchdog-ul nu declansa daca starea nu venea NICIODATA.** Cu
   `last_state_time = None`, conditia `if self.last_state_time is not None`
   sarea peste verificare, deci un robot care nu publica deloc trecea drept
   'safe' la infinit. Cel mai periculos caz posibil. Am adaugat
   `startup_grace_s`.
2. **La e-stop, nodul doar tacea.** `cmd_callback` facea `return` fara sa
   publice nimic; pe hardware, ultima comanda ramane activa in driver. Acum
   publica activ zero, repetat, cat timp e-stop e activ.
3. **Nu exista resetare.** Am adaugat `/estop_reset` explicit, separat de
   declansare (un e-stop care se auto-reseteaza ar putea reporni bratul).
4. **Fara limitare de rata.** Un salt de la `-u_max` la `+u_max` e o treapta
   pe care hardware-ul o simte ca soc. Am adaugat `slew_max_N_per_s`.
5. **Garda pe NaN** in stare si comanda (declanseaza e-stop, nu ignora tacut).

Un bug l-am gasit in propria implementare, la testare: dupa reset dadeam doar
`state_timeout` (300 ms) pana la re-declansare, dar discovery-ul ROS dureaza
1-2 s, deci resetul parea ca nu functioneaza. Acum resetul reporneste
perioada de gratie completa.

## 3. `test_smith_variable.py` -- rezultat

tau(t) sinusoidal 50-150 ms (perioada 4 s), controller 100 Hz, 10 s:

| scenariu | theta rms | \|theta\|max | verdict |
|---|---|---|---|
| ORACLE (tau cunoscut exact) | **1.14 grade** | **6.56 grade** | tinta atinsa |
| ESTIMAT (EWMA din RTT zgomotos) | **1.31 grade** | **6.58 grade** | tinta atinsa |

Tinta ceruta: `theta_rms < 2` grade, `|theta|max < 15` grade. **Ambele atinse,
cu marja.** Diferenta oracle-vs-estimat este mica (1.14 -> 1.31 grade), deci
estimatorul nu strica bucla.

Acuratetea estimatorului EWMA (dupa 1 s de convergenta, jitter 4 ms pe RTT):

```
eroare medie  : +1.06 %
eroare p95    : 14.41 %
eroare maxima : 18.12 %
prag critic (runda 3): +/-20 %  -> IN LIMITE
```

**Dar marja e subtire: 18.12% maxim fata de un prag de 20%.** Estimatorul
trece, insa nu cu mult. Doua consecinte practice:
- pe o retea reala, cu jitter mai mare decat cei 4 ms simulati aici,
  marja dispare;
- `alpha=0.3` la 20 Hz da o constanta de timp de ~170 ms, comparabila cu
  perioada variatiei latentei. Merita incercat un filtru care urmareste si
  panta (alpha adaptiv sau Kalman de ordinul 2), nu doar nivelul.

## 4. Driver UR3 -- disponibil?

**NU este instalat**, dar exista in apt pentru Jazzy:

```
ros-jazzy-ur                 Metapackage for universal robots
ros-jazzy-ur-robot-driver    (driverul propriu-zis)
ros-jazzy-ur-client-library
ros-jazzy-ur-controllers
ros-jazzy-ur-description
ros-jazzy-ur-calibration
```

Nu l-am instalat: e o schimbare de sistem cu `sudo`, iar decizia e a ta.

```bash
sudo apt install ros-jazzy-ur
```

**Numele articulatiilor UR3** (din conventia `ur_description`, aceeasi pentru
UR3/UR5/UR10): `shoulder_pan_joint`, `shoulder_lift_joint`, `elbow_joint`,
`wrist_1_joint`, `wrist_2_joint`, `wrist_3_joint`.

Le dau ca fiind conventia standard a pachetului, **nu ca verificate pe masina
asta** -- nu pot rula `ros2 topic echo /joint_states` fara driver instalat si
fara robot. Se confirma cu `ros2 topic echo /joint_states --once` dupa
instalare, sau chiar fara robot pornind `ur_description` cu
`use_fake_hardware:=true`.

Recomandarea mea pentru primul contact: **`ur_robot_driver` cu
`use_fake_hardware:=true`**, care expune exact aceleasi topicuri si controllere
ca robotul real, fara risc. Poti valida tot lantul (JointState -> estimator ->
LQR+Smith -> watchdog -> effort) inainte sa alimentezi bratul.

## 5. OK pentru test pe UR3 real?

**Pentru `use_fake_hardware:=true`: da, acum.**
**Pentru bratul real alimentat: inca nu.** Patru lucruri lipsesc.

### 5.1 Nu exista nod de control pentru UR3

Am implementat estimatorul si garzile, dar **nu am scris
`ur3_single_joint_poc.py`**. Codul propus in specificatie are trei probleme
care l-ar face nesigur pe hardware real, si prefer sa le rezolvam constient
decat sa le compilez:

- **Integrare Euler in predictor** (`x = x + x_dot * dt_pred`) in loc de RK4.
  Pe un model instabil, Euler explicit adauga energie artificial. Cu
  `n_steps=20` pe 100 ms, pasul e 5 ms si eroarea e mica, dar pe un pendul
  invers e exact tipul de aproximare care se razbuna.
- **`_predict_state_smith` apeleaza `self.get_clock().now()` in bucla**, deci
  timpul se schimba intre sub-pasi si tinta interpolarii aluneca. Trebuie
  citit o singura data, inainte.
- **Modelul `m*L^2*theta_ddot = tau - m*g*L*sin(theta) - b*theta_dot`
  presupune ca articulatia e un pendul invers liber.** `shoulder_lift_joint`
  pe un UR3 nu este: are gravitatie compensata intern de driver, are frecare
  uscata semnificativa, si nu e instabila in bucla deschisa. Modelul nu se
  potriveste, iar parametrii dati (m=2.0, L=0.3, b=0.5) sunt presupusi, nu
  identificati.

Consecinta: LQR-ul calculat pe acest model ar avea castiguri gresite pe un
sistem care oricum nu e instabil. **Pentru UR3 propun sa inversam ordinea:
intai identificare experimentala pe articulatie (raspuns la treapta, cu
`use_fake_hardware` apoi cu robotul in modul cel mai lent), abia apoi
proiectarea controllerului.** Altfel proiectam pe un model inventat.

### 5.2 Interfata de comanda nu e definita

`/joint_effort` (Float64) nu e o interfata `ros2_control` standard. UR3 sub
`ur_robot_driver` expune `scaled_joint_trajectory_controller` (pozitie) si,
in functie de configuratie, `forward_velocity_controller`. **Control in cuplu
pe UR3 nu e disponibil prin driverul standard.** Deci arhitectura
LQR-pe-cuplu nu se transfera direct; trebuie fie comanda in viteza, fie
pozitie cu bucla interna.

Asta merita clarificat inainte de orice cod: **ce interfata de comanda folosim
pe UR3?** Raspunsul schimba complet nodul.

### 5.3 Watchdog-ul nu e in lantul UR3

Watchdog-ul filtreaza `/robot_cmd` -> `/robot_cmd_safe` in unitati de forta
pe cart-pole. Pentru UR3 are nevoie de limite pe articulatie (pozitie, viteza,
acceleratie), nu pe o forta scalara.

### 5.4 Latenta e masurata pe loopback, nu pe retea

Cei 1.3 ms de mai sus sunt loopback local. Numarul relevant e RTT-ul peste
legatura reala catre robot. Aici se leaga direct de `c1_benchmark`: ai deja
aparatura de masura sub degradare controlata cu `netem`.

### Ordinea pe care o propun

1. `sudo apt install ros-jazzy-ur`; porneste cu `use_fake_hardware:=true`;
   confirma numele articulatiilor si interfetele de comanda disponibile
2. Decizie: comanda in pozitie sau in viteza (nu cuplu)
3. Identificare experimentala pe o articulatie (raspuns la treapta)
4. Nod de control pe modelul identificat, cu watchdog adaptat la limite de
   articulatie
5. Masurare RTT real cu `latency_estimator` peste legatura catre robot
6. Abia apoi brat alimentat, in modul cel mai lent, cu e-stop fizic la indemana

Ce **este** gata si validat: nucleul de control (LQR+Smith), estimatorul de
latenta, garzile de siguranta, si integrarea tau online in MPC (verificat:
nodul consuma `/estimated_delay` si revine elegant la valoarea statica cand
estimarea se invecheste -- `"/estimated_delay vechi de 506 ms; revin la
tau_est static (80 ms)"`).

---

## 6. Ce ramane deschis

Neschimbat fata de runda 3: `/mixed_cmd` si `/robot_cmd_delayed` fara abonati;
Gazebo nepornit din launch (URDF valid, lipsesc world SDF + bridge); `Twist`
folosit pentru forta; `D_h` nefolosit in feedback-ul haptic; lipsa
`_selftest()` conform CLAUDE.md sec.2.

Nou: `/robot_cmd_safe` este publicat de watchdog dar inca nu il consuma nimeni
-- lantul devine util abia cand driverul robotului subscrie la el in locul lui
`/robot_cmd`.

## 7. Fisiere

Cod nou (in repo):
`phsc_teleop_mpc/latency_estimator.py` (+ nod `latency_echo`),
`phsc_teleop_mpc/safety_watchdog.py`, integrare `/estimated_delay` in
`mpc_controller_node.py`.

Simulari (`~/phsc_sim`, in afara git): `test_smith_variable.py`,
`ablation_study.py` + `.png`, `robustness_smith.py`, `closed_loop_compare.py`,
`benchmark_mpc.py`, `lqr_sanity.py`, rapoartele rundelor 1-4.
