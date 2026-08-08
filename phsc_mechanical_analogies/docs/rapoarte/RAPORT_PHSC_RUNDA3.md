# RAPORT PHSC -- Runda 3 (finala)

Data: 2026-08-08. Toate cifrele sunt MASURATE pe aceasta masina.
Build: 4/4 pachete OK, 0 stderr. Cod: 100% ASCII (CLAUDE.md sec.3).

---

## 1. Confirmare ablatie: #2 (naiv) e mai rea decat #1 (fara compensare)?

**DA, confirmat.** LQR pe cart-pole, tau = 100 ms constant, controller 100 Hz:

| conditie | \|theta\|max | theta rms | u rms | verdict |
|---|---|---|---|---|
| 1. Fara compensare | 5954.75 grade | 3149.60 grade | 93.16 N | cade la **0.88 s** |
| 2. Predictie naiva (u=0) | 5115.43 grade | 2801.47 grade | 96.71 N | cade la **0.53 s** |
| 3. Predictie Smith (buffer) | **6.43 grade** | **1.56 grade** | **1.06 N** | **STABIL** |

Predictia naiva cade cu **345 ms mai devreme** decat lipsa oricarei compensari.

Rezultatul se vede si in praguri, nu doar la o singura valoare de tau:

| tau [ms] | fara compensare | naiv (u=0) | Smith (buffer) |
|---|---|---|---|
| 20 | STABIL (5.8d) | STABIL (5.8d) | STABIL (5.8d) |
| 50 | STABIL (5.9d) | **NESTAB (17d)** | STABIL (5.9d) |
| 80 | cazut 1.25s | cazut 0.65s | STABIL (6.2d) |
| 100 | cazut 0.88s | cazut 0.53s | STABIL (6.4d) |
| 120 | cazut 0.71s | cazut 0.54s | STABIL (6.7d) |
| 150 | cazut 0.78s | cazut 0.70s | STABIL (7.3d) |
| 200 | cazut 0.63s | cazut 0.48s | STABIL (8.6d) |

Praguri: fara compensare **50-80 ms**, predictie naiva **20-50 ms**,
Smith **peste 200 ms**. Predictia naiva injumatateste pragul fata de a nu face
nimic.

Figura: `~/phsc_sim/ablation_study.png` (theta si u, cele trei conditii).

Mecanismul, vizibil in graficul de comanda: predictorul naiv presupune ca
nimic nu actioneaza pe fereastra, deci supraestimeaza cat de mult cade
pendulul si cere corectie maxima; comanda satureaza la +100 N in 0.35 s si
ramane acolo. Adauga faza in loc sa o compenseze.

## 2. Tabel final: prag de stabilitate LQR+Smith

Aici este partea pe care o consider cea mai importanta din runda 3.
Pragul de peste 200 ms de mai sus este obtinut cu un predictor care foloseste
EXACT acelasi model si aceeasi interpolare ca planta. Pe hardware asta nu se
intampla niciodata. Am masurat cat se pierde din marja la fiecare sursa de
nepotrivire:

| conditie | 50 | 100 | 150 | 200 | 250 | 300 | 400 | 500 ms | prag |
|---|---|---|---|---|---|---|---|---|---|
| 0. ideal (predictor = planta) | 5.9d | 6.4d | 7.3d | 8.6d | 10.3d | 12.7d | cazut | cazut | **300-400 ms** |
| A. canal ZOH (pachete discrete) | 5.9d | 6.4d | 7.3d | 8.6d | cazut | cazut | cazut | cazut | 200-250 ms |
| B1. tau subestimat 20% | 5.9d | 6.4d | cazut | cazut | cazut | cazut | cazut | cazut | 100-150 ms |
| B2. tau supraestimat 20% | 5.9d | 6.4d | cazut | cazut | cazut | cazut | cazut | cazut | 100-150 ms |
| B3. tau subestimat 50% | 5.9d | cazut | cazut | cazut | cazut | cazut | cazut | cazut | 50-100 ms |
| C. parametri fizici +30% M | 5.9d | 6.4d | cazut | cazut | cazut | cazut | cazut | cazut | 100-150 ms |
| **D. combinat (realist)** | 5.9d | 6.4d | cazut | cazut | cazut | cazut | cazut | cazut | **100-150 ms** |

**Concluzia critica: sensibilitatea dominanta este la eroarea de estimare a
latentei, nu la parametrii fizici si nu la forma canalului.** O eroare de doar
+/-20% pe tau taie pragul de la 300-400 ms la 100-150 ms -- acelasi efect ca o
eroare de 30% pe masa. Estimarea online a lui tau nu este un detaliu de
implementare, ci o componenta critica a buclei.

Interesant si contra-intuitiv: supraestimarea lui tau strica la fel de mult ca
subestimarea. Nu poti sa fii 'conservator' marind tau_est.

## 3. Status build ROS 2

**DA.** 4/4 pachete, 0 stderr, de la zero.
```
Finished <<< phsc_mechanical_analogies [1.98s]
Finished <<< phsc_teleop_mpc [2.05s]
Finished <<< phsc_gazebo_plugins [0.52s]
Finished <<< phsc_bringup [2.04s]
Summary: 4 packages finished
```
`ros2 pkg executables phsc_teleop_mpc` -> `mpc_controller_node`,
`shared_control_mixer`.

**Nodul atinge acum 20 Hz real** cu constrangerea in varianta soft:
```
ros2 run phsc_teleop_mpc mpc_controller_node --ros-args -p theta_mode:=soft -p N:=7
ros2 topic hz /robot_cmd -> average rate: 20.031  (min 0.047s, max 0.052s)
```
Fata de 1.99 Hz in runda 1. Cele trei schimbari care au facut diferenta:
N=20 -> 7, constrangerea theta_max in varianta soft, si predictorul corect.

## 4. Alte bug-uri descoperite

### 4.1 Varianta soft a constrangerii (propunerea ta) e mai buna decat a mea

In runda 2 implementasem theta_max ca `NonlinearConstraint` SLSQP. Corecta,
dar cere un rollout separat la fiecare evaluare -> **dubleaza** timpul de solve
(N=7: 39 -> 74 ms). Varianta ta cu penalizare in cost refoloseste rollout-ul
existent din `_cost_function`, deci e aproape gratis. Am implementat ambele,
comutabile prin `theta_mode` (`hard` | `soft` | `none`), cu `soft` folosit
pentru a atinge 20 Hz.

Am corectat totusi o scapare din snippet-ul tau: bucla evalua `abs(x[2])`
INAINTE de propagare, deci verifica x_0..x_{N-1} si niciodata x_N, iar `x` era
deja avansat de bucla de cost de dinainte (dubla propagare). Varianta din cod
evalueaza pe x_{k+1}, in interiorul buclei existente.

### 4.2 Interpolare vs zero-order hold in predictor: nu e neutru

Specificatia ta cere `np.interp` in `_interp_control`. Am implementat asa. Dar
canalul real livreaza pachete discrete, deci predictorul corect fizic ar fi
ZOH. Diferenta e masurabila: prag 300-400 ms cu interpolare potrivita cu
planta, 200-250 ms cu ZOH. Adica **o parte din performanta raportata vine din
faptul ca predictorul si planta impart acelasi model de canal**, nu din
metoda. Am pastrat ambele variante in `robustness_smith.py`; pentru articol,
cifra onesta este cea cu ZOH.

### 4.3 Ce am respins din specificatia rundei 3

- `sys.path.insert(0, '/home/USER/...')` din scripturi: cale placeholder care
  nu exista. Scripturile ruleaza din `~/phsc_sim`, unde stau copiile.
- Rescrierea plugin-ului: era deja facuta in runda 2 cu `priority_queue` +
  simTime pe ambele capete. Varianta ta cu `std::greater<>` si `operator>` e
  echivalenta functional; am pastrat comparatorul explicit.

---

## 5. OK pentru hardware UR3?

**Nucleul de control: DA. Integrarea ROS pentru UR3: inca NU.** Trei lucruri
lipsesc, si primul e blocant.

### Blocant: nu exista estimare de latenta

Sec.2 arata ca +/-20% eroare pe tau injumatateste marja. Momentan `tau_est`
este un parametru STATIC din YAML (0.08 s), iar `tau_func` din nod este un
placeholder (`tau_est + tau_var*sin(2t)`) care nu masoara nimic. Pe UR3 peste
retea, latenta reala variaza si nu e cunoscuta.

Necesar inainte de hardware:
1. Mesaje cu timestamp (`WrenchStamped` / `JointState` au `header.stamp`);
   fara ele latenta end-to-end nu e observabila.
2. Un estimator online de tau (media alunecatoare + percentila pe RTT), care
   sa alimenteze `tau_func`.
3. Un test care sa arate ca estimatorul ramane in +/-20% sub trafic real.

Aici se leaga natural de infrastructura ta din `c1_benchmark` (RTT p95 sub
degradare controlata cu netem) -- ai deja aparatura de masura.

### Al doilea: modelul cart-pole nu se transfera pe UR3

`u_max` este forta pe carucior, starea e un vector plat de 4 elemente, iar UR3
publica `sensor_msgs/JointState` cu 6 articulatii. Doua variante:
- **PoC pe o singura articulatie** (recomandat ca prim pas): masa/inertie
  echivalenta pe un joint, acelasi LQR+Smith, risc mic.
- Model dinamic 6-DOF complet: corect, dar e un proiect in sine.

### Al treilea: siguranta pe hardware real

Pe cart-pole simulat, o comanda gresita inseamna un pendul cazut. Pe UR3
inseamna un brat real in miscare. Inainte de prima rulare:
- limite de viteza/acceleratie pe joint, nu doar pe forta
- watchdog pe `/robot_state`: daca starea lipseste > 100 ms, comanda -> 0
  (acum nodul pur si simplu nu publica, iar planta ramane pe ultima comanda)
- comportament definit la esec de solver, altul decat fallback LQR tacut

### Recomandarea mea de ordine

1. Timestamps + estimator de tau, validat in simulare (1 sesiune)
2. Inchide buclele: cine consuma `/mixed_cmd` si `/robot_cmd_delayed`
3. PoC pe o singura articulatie UR3, cu watchdog si limite
4. Abia apoi teleoperare completa + interfata haptica

Ce **este** gata: nucleul de control (LQR + Smith), validat numeric si in
bucla inchisa, cu praguri masurate si studiu de sensibilitate. Nodul ruleaza
la 20 Hz real. Plugin-ul de delay e corect pe timp simulat, fara head-of-line
blocking.

---

## 6. Ce ramane deschis (neschimbat fata de runda 2)

- `/mixed_cmd` si `/robot_cmd_delayed` nu au abonati: bucla de shared control
  e deschisa, `alpha` nu are efect pe planta.
- `cartpole_sim.launch.py` nu porneste Gazebo. URDF-ul exista si e valid
  (`check_urdf` OK), dar lipsesc world SDF + `ros_gz_sim` + `ros_gz_bridge`.
- `/robot_cmd` ramane `Twist` cu forta in `linear.x`.
- `D_h` din feedback-ul haptic inca nefolosit (arc pur, fara amortizare).
- Nucleul nu are `_selftest()` conform CLAUDE.md sec.2.

## 7. Fisiere

Cod (in repo): `phsc_bringup/ARCHITECTURE.md`, `phsc_bringup/models/cartpole.urdf`.
Simulari (in `~/phsc_sim`, in afara git): `ablation_study.py` + `.png`,
`robustness_smith.py`, `closed_loop_compare.py`, `benchmark_mpc.py`,
`lqr_sanity.py`, `test_mpc.py`, rapoartele rundelor 1-3.
