# Ghid de migrare PHSC -> UR3

Stare: **cod NEscris intentionat.** Motivul e in sec. 1: modelul propus
initial pentru UR3 descria un sistem care nu exista pe robotul real, iar un
controller proiectat pe el ar fi fost gresit indiferent de calitatea
implementarii.

---

## 1. De ce nu exista inca cod pentru UR3

Propunerea initiala era sa tratam `shoulder_lift_joint` ca pendul invers:

```
m L^2 theta_ddot = tau - m g L sin(theta) - b theta_dot
```

Trei probleme, in ordinea gravitatii:

**1.1 Sistemul nu e cel modelat.** Un pendul invers e instabil in bucla
deschisa -- de aici vine toata problema de control si toata valoarea
compensarii de latenta. `shoulder_lift_joint` pe un UR3 are gravitatia
compensata intern de controllerul de articulatie, are frecare uscata
semnificativa, si **nu este instabil**. Modelul descrie o problema pe care
robotul nu o are.

**1.2 Interfata de comanda nu exista.** `/joint_effort` (`std_msgs/Float64`)
nu este o interfata `ros2_control`. `ur_robot_driver` expune
`scaled_joint_trajectory_controller` (pozitie) si, in functie de
configuratie, controllere de viteza. **Control in cuplu nu este disponibil
prin driverul standard.** Arhitectura LQR-pe-cuplu nu se transfera direct.

**1.3 Parametrii erau presupusi.** `m=2.0, L=0.3, b=0.5` nu provin din nicio
masuratoare. Un LQR calculat din ei ar avea castiguri arbitrare.

Concluzie: pe simulare am putut proiecta intai si valida dupa, pentru ca
modelul plantei era cunoscut prin constructie. Pe hardware ordinea se
inverseaza: **intai identificare, apoi proiectare.**

## 2. Preconditii obligatorii

### 2.1 Inventar de interfata (fara robot alimentat)

```bash
sudo apt install ros-jazzy-ur
ros2 launch ur_robot_driver ur_control.launch.py \
     ur_type:=ur3 robot_ip:=0.0.0.0 use_fake_hardware:=true
```

De confirmat, cu robotul simulat:
- numele exacte ale articulatiilor din `/joint_states`
  (conventia `ur_description`: `shoulder_pan_joint`, `shoulder_lift_joint`,
  `elbow_joint`, `wrist_1_joint`, `wrist_2_joint`, `wrist_3_joint`)
- lista de controllere: `ros2 control list_controllers`
- interfetele de comanda disponibile: `ros2 control list_hardware_interfaces`
- limitele din URDF: pozitie, viteza, efort per articulatie

`use_fake_hardware:=true` expune exact aceleasi topicuri si controllere ca
robotul real, deci tot lantul software poate fi validat fara niciun risc.

### 2.2 Identificare experimentala

Articulatie tinta: una singura, aleasa dupa inventar.

Semnale de excitatie, in ordinea riscului:
1. treapta mica de pozitie (cel mai simplu, cel mai sigur)
2. sinusoidal cu frecventa variabila (chirp), pentru raspuns in frecventa
3. PRBS, daca e nevoie de identificare parametrica riguroasa

Model tinta, de ordinul 2 cu frecare:
```
J theta_ddot + F_v theta_dot + F_c sign(theta_dot) = tau_cmd - tau_grav(theta)
```
Parametri de identificat: inertia `J`, frecarea vascoasa `F_v`, frecarea
uscata `F_c`. `tau_grav` este, probabil, deja compensat de driver -- de
verificat experimental, nu de presupus.

Criteriu de acceptare: modelul identificat trebuie sa prezica raspunsul la un
semnal de validare (diferit de cel de identificare) cu o eroare acceptabila,
altfel nu se trece mai departe.

### 2.3 Reproiectarea controllerului

Abia dupa 2.2:
- LQR (sau PI + feedforward, daca sistemul e stabil si bine amortizat) pe
  modelul identificat
- predictor Smith adaptat: aceeasi structura, dar propagand modelul
  identificat, nu cart-pole
- maparea iesirii controllerului la interfata reala disponibila
  (pozitie sau viteza), nu la cuplu

Atentie: daca articulatia este stabila si bine amortizata, **compensarea de
latenta ramane relevanta pentru precizia de urmarire si pentru feedback-ul
haptic, dar nu mai e o chestiune de stabilitate.** Asta schimba ce se poate
sustine in teza pe baza experimentului pe UR3: nu 'stabilizam un sistem
instabil peste retea', ci 'imbunatatim urmarirea si transparenta haptica sub
latenta'. E o afirmatie mai slaba, dar aparabila.

### 2.4 Garzi de siguranta adaptate

`safety_watchdog` actual lucreaza pe o forta scalara. Pentru UR3 are nevoie
de limite pe articulatie:
- pozitie in limitele din URDF
- viteza maxima (mult sub nominal la primele rulari)
- acceleratie / rata de variatie a comenzii
- watchdog pe `/joint_states`, nu pe `/robot_state`
- comutare la oprire controlata la esec de estimator sau pierdere de legatura

E-stop fizic la indemana, indiferent de ce garzi software exista.

### 2.5 Masurare de latenta reala

Cei 1.3 ms masurati pana acum sunt loopback local. Numarul relevant este
RTT-ul peste legatura reala catre robot, masurat cu `latency_estimator` in
conditii de trafic realiste. Aici exista deja aparatura in proiect:
`c1_benchmark` masoara RTT sub degradare controlata cu `netem`.

## 3. Arhitectura propusa (post-identificare)

```
[Operator] --> [Shared Control Mixer] --> [Controller + predictor Smith]
                                                    |
                                                    v
                              [ros2_control: pozitie sau viteza]
                                                    |
                                                    v
                                   [ur_robot_driver] --> [UR3]
                                                    |
        [Latency Estimator] <---- RTT ping/pong ----+
                                                    |
        [Safety Watchdog] <------ /joint_states ----+
```

Diferente fata de lantul de simulare:
- `/robot_state` (Float64MultiArray, 4 elemente) devine `/joint_states`
  (`sensor_msgs/JointState`)
- `/robot_cmd` (Twist cu forta in `linear.x`) devine o comanda
  `ros2_control` in pozitie sau viteza
- watchdog-ul filtreaza comenzi de articulatie, nu o forta scalara
- toate mesajele trebuie sa aiba `header.stamp`; fara timestamp latenta
  end-to-end nu este observabila

## 4. Ordinea recomandata

1. `sudo apt install ros-jazzy-ur`; pornire cu `use_fake_hardware:=true`
2. Inventar de interfata (sec. 2.1) -- decizie: pozitie sau viteza
3. Identificare experimentala pe o articulatie (sec. 2.2)
4. Reproiectare controller pe modelul identificat (sec. 2.3)
5. Adaptarea garzilor (sec. 2.4), validate tot pe `use_fake_hardware`
6. Masurare RTT real (sec. 2.5)
7. Prima rulare cu brat alimentat: viteza minima, e-stop fizic la indemana,
   o singura articulatie, amplitudine mica

Pasii 1-6 nu au niciun risc fizic si pot fi facuti oricand. Pasul 7 nu ar
trebui inceput inainte ca 1-6 sa fie complete.

## 5. Ce se poate scrie in teza inainte de hardware

Simularea este un capitol complet in sine: model, analiza de stabilitate,
ablatie, estimare de latenta, garzi de siguranta, praguri masurate. Extensia
pe hardware poate fi formulata onest ca:

> Extensia pe hardware industrial (UR3) necesita identificarea parametrilor
> dinamici ai articulatiei si adaptarea interfetei de comanda la arhitectura
> `ros2_control`, intrucat controlul direct in cuplu nu este expus de
> driverul standard. Metodologia de identificare si rezultatele preliminare
> sunt prezentate in capitolul X.
