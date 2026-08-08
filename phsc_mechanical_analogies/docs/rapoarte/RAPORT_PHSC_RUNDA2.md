# RAPORT PHSC -- Runda 2

Data: 2026-08-08. Toate cifrele sunt MASURATE pe aceasta masina.
Stare: 4/4 pachete build OK, 0 stderr, nodurile ruleaza, URDF se parseaza.

---

## RASPUNSURI DIRECTE LA CELE 6 INTREBARI

### 1. `python3 cartpole_model.py` -- A[3][3] = ?

```
A[3][3] = 0.0 (asteptat: 0.0)
LQR K: [-10.  -11.72401214  -72.15630632  -14.73718429]
Valori proprii LQR: [-7.59+3.43j -7.59-3.43j -1.33+1.02j -1.33-1.02j]
Toate stabile (Re < 0): True
```
Confirmat. (Fixul fusese deja aplicat in runda 1; A se potriveste acum cu
Jacobianul numeric la 5.8e-12.)

### 2. `benchmark_mpc.py` -- mediana in ms

| N | fara constrangere theta_max | cu theta_max impus |
|---|---|---|
| 20 | **519 ms** (1.9 Hz) | **982 ms** (1.0 Hz) |
| 15 | 252 ms (4.0 Hz) | -- |
| 10 | 87 ms (11.5 Hz) | 170 ms (5.9 Hz) |
| **7** | **39 ms (25.6 Hz)** | **74 ms (13.5 Hz)** |
| 5 | 15 ms (68 Hz) | -- |

Alternative real-time, aceeasi masina:
```
LQR (K precalculat):              1.73 us  -> 576 kHz
LQR + predictie RK4 (20 pasi):  740    us  -> 1352 Hz
LQR + predictie RK4 (4 pasi):   152    us  -> 6597 Hz
```
NMPC este cu **3 ordine de marime** mai scump decat LQR+predictie.

Observatie importanta: **N=20 nu e o limita a metodei, e o alegere de tuning.**
La N=7 NMPC intra in buget pentru 20 Hz (39 ms) daca theta_max NU e impus, si
la ~13 Hz daca e impus.

### 3. `ros2 pkg executables phsc_teleop_mpc`

```
phsc_teleop_mpc mpc_controller_node
phsc_teleop_mpc shared_control_mixer
```

### 4. Nodul MPC porneste fara crash?

**DA.** Publica pe `/robot_cmd` (2.087 N) si `/haptic_feedback`. Garda de timp
real raporteaza onest ce se intampla:
```
[WARN] DEPASIRE timp real: ciclul MPC a durat 991 ms > perioada 50 ms
       (rata efectiva ~1.0 Hz; 1/1 cicluri depasite)
```

URDF-ul se parseaza corect:
```
robot name is: cartpole
root Link: world has 1 child(ren)
    child(1): rail -> cart -> pole
```

---

## 5. BUG-URI NOI DESCOPERITE

### 5.1 CEL MAI IMPORTANT: predictia cu comanda gresita e MAI REA decat lipsa ei

Am construit un experiment de bucla inchisa care respecta constrangerea de timp
real (fiecare controller se actualizeaza doar la rata pe care si-o permite
efectiv; intre actualizari comanda e tinuta, ca in nodul ROS).
Planta: cart-pole neliniar integrat la 1 ms. Canal: tau(t) = 80 +/- 20 ms.

```
controller                      rata   upd  |theta|max  theta rms   u rms   verdict
NMPC N=20 (real-time)          1.0Hz     7    319.21d    242.52d   91.45N   CAZUT la 0.73s
NMPC N=10 (real-time)          5.1Hz    31     28.77d     12.05d   10.63N   NESTABILIZAT
NMPC N=7  (real-time)         10.6Hz    64      6.59d      2.30d    0.73N   STABIL
LQR + predictie naiva        100.0Hz   573   9012.70d   4905.86d   96.78N   CAZUT la 0.70s
LQR + predictie Smith        100.0Hz   573      6.22d      1.31d    0.93N   STABIL
LQR fara compensare          100.0Hz   573   5742.51d   3064.97d   94.27N   CAZUT la 0.81s
```

Verificare de sanitate a implementarii LQR, in trepte (ca sa nu dam vina pe
arhitectura cand de fapt bancul de test e stricat):
```
1. LQR, FARA latenta (100 Hz)                    |theta|max=   5.73d  STABIL
2. LQR, latenta 80+/-20 ms, fara compensare      |theta|max=5742.51d  CAZUT la 0.81s
3. LQR + predictie naiva (u=0 pe fereastra)      |theta|max=9012.70d  CAZUT la 0.70s
4. LQR + predictie Smith (comenzi in zbor)       |theta|max=   6.22d  STABIL
```

**Rezultatul central: o predictie care presupune u=0 pe fereastra de latenta
este mai rea decat lipsa oricarei compensari (cadere la 0.70 s vs 0.81 s).**
Compensarea functioneaza doar daca propaga starea folosind comenzile REALE
aflate in zbor pe canal.

Exact asta era bug-ul semnalat in runda 1: `control_buffer` era scris si
niciodata citit. **Codul v2 pastreaza acest bug**: semnatura noua
`predict_state_delay(x0, u, tau)` primeste un scalar (`u_guess = self.u_prev`),
deci tine o singura comanda pe toata fereastra -- mai bine decat u=0, dar nu
predictia corecta. Am implementat varianta corecta (`_inflight_at()`).

Prag de latenta pentru LQR + Smith la 100 Hz (masurat):
```
tau =  20..100 ms  -> STABIL (|theta|max creste lin de la 5.76d la 6.43d)
tau = 150 ms       -> STABIL, dar la limita (|theta|max = 19.95d)
tau = 200 ms       -> CAZUT la 1.90s
```
Deci exista un **prag de latenta masurabil intre 150 si 200 ms** -- un rezultat
publicabil in sine, si un candidat bun de figura pentru articol.

### 5.2 Bug-uri pe care v2 le declara rezolvate, dar nu le rezolva

- **#8 theta_max**: v2 sterge `_constraints()` (era cod mort), dar **nu impune
  nicaieri** constrangerea. Am implementat-o ca `NonlinearConstraint` reala.
  Verificat pe caz fezabil: fara impunere `|theta|max = 0.4572 rad` (limita
  0.12, INCALCATA); cu impunere `0.1200 rad` exact (RESPECTATA, activa).
  Cost: **dubleaza timpul de solve** (N=7: 39 -> 74 ms). Am lasat-o comutabila
  prin `enforce_theta_max`.
- **#9 head-of-line blocking**: v2 modifica doar ceasul, dar pastreaza
  `std::queue` + `break`. Am trecut pe `std::priority_queue` ordonata dupa
  momentul de livrare, cu golirea tuturor mesajelor expirate.

### 5.3 Bug NOU introdus de v2: amestec de doua ceasuri in plugin

Patch-ul v2 pentru `PreUpdate` calculeaza `now` din `_info.simTime`, dar
`receive_time` ramane stampilat cu `ros_node_->now()` (**ceas de perete**) in
callback-ul de subscriptie. Scaderea `(now - front.receive_time)` compara
~5 s de timp simulat cu ~1.79e9 s de timp de perete -> rezultat masiv negativ,
deci **niciun mesaj nu ar mai fi livrat vreodata**; iar `rclcpp::Time` cu surse
de ceas diferite poate arunca exceptie direct.

Corect: **ambele** stampile pe ceasul simularii. Am pus `sim_now_` actualizat in
`PreUpdate` si folosit si in callback.

### 5.4 Regresii daca s-ar aplica v2 literal

Codul v2 pentru `mpc_controller_node.py` si `cartpole_sim.launch.py` ar sterge
fixuri deja verificate in runda 1:
- ar reintroduce `rclpy.shutdown()` in loc de `try_shutdown()`. **Verificat:
  prinderea `ExternalShutdownException` singura NU e suficienta** -- contextul e
  deja inchis de handler-ul de semnal, deci `shutdown()` arunca
  `RCLError: rcl_shutdown already called` si `ros2 run` iese cu cod 1. Am
  masurat: exit=1 cu varianta v2, exit=0 cu `try_shutdown()`.
- ar sterge garda de NaN (NaN pe `/robot_state` -> forta NaN publicata)
- ar sterge parametrii `theta_max`, `tau_var`, `R_du`, `max_iter`, `ftol`
  (redevin intrari YAML ignorate silentios)
- ar readuce `arguments=['-d', 'config/phsc.rviz']` -- fisier care nu exista --
  si `use_rviz` fara `IfCondition`, deci rviz porneste mereu si esueaza mereu
- ar folosi `print()` in loc de logger-ul ROS pentru avertismentul de performanta

Le-am **pastrat pe cele din runda 1** si am aplicat doar partile bune din v2.

### 5.5 URDF-ul din v2 nu ar fi trecut de parser

`<inertia ixx=".." iyy=".." izz=".."/>` -- parserul URDF cere toate sase
(`ixx ixy ixz iyy iyz izz`) si respinge fisierul altfel. In plus lipseau
`<gazebo>`, deci modelul s-ar incarca fara sa comunice nimic cu ROS. Am scris o
varianta valida (verificata cu `check_urdf`), cu `JointStatePublisher` si
`ApplyJointForce`, si cu centrul de masa al pendulului la L (nu L/2), ca sa
corespunda modelului analitic.

---

## 6. RECOMANDARE DE ARHITECTURA

**LQR + predictie Smith pentru timp real. NMPC pentru analiza offline.**
Dar cu o nuanta importanta fata de propunerea initiala.

Datele sustin asta pe trei axe:

1. **Performanta de reglare**: LQR+Smith are cel mai bun `theta rms` din tot
   tabelul (1.31d, fata de 2.30d pentru NMPC N=7) si efort comparabil.
2. **Cost**: 152 us fata de 74 ms. Trei ordine de marime. Lasa procesorul liber
   pentru perceptie, haptica si retea -- exact ce are nevoie teleoperarea.
3. **Marja**: la 100 Hz ai 30 de esantioane per constanta de timp a
   instabilitatii (215 ms). NMPC N=7 la 13 Hz iti da 2.8. Prima varianta
   supravietuieste unui jitter de planificare, a doua nu.

**Nuanta:** afirmatia "nonlinear MPC e imposibil in timp real" e prea tare si
nu o sustin. Masurat, NMPC N=7 ruleaza la 25.6 Hz fara constrangerea de stare
si **stabilizeaza** planta la 10.6 Hz. Deci formularea onesta pentru teza este:

> NMPC cu orizont lung (N=20) nu este realizabil in timp real cu SLSQP si
> gradiente prin diferente finite (519-982 ms/solve, adica 10-20x peste
> bugetul de 50 ms). Cu orizont scurt (N=7) devine realizabil, dar cu marja
> mica si performanta de reglare inferioara unui LQR cu predictie corecta a
> starii, la un cost de calcul de ~500x mai mare.

Asta e mai puternic decat "e imposibil": ai o comparatie cantitativa, nu o
renuntare.

**Ce as pune in teza:**
- Capitol de metoda: NMPC ca instrument de proiectare/analiza (tuning, studiu
  de stabilitate, generare de traiectorii de referinta) -- offline.
- Capitol de implementare: LQR + predictie Smith neliniara, 100 Hz, cu pragul
  de latenta masurat (150-200 ms) ca rezultat experimental principal.
- Un experiment de ablatie care e, cred, contributia cea mai interesanta:
  **fara compensare vs predictie naiva vs predictie cu comenzi in zbor**.
  Faptul ca predictia naiva e mai rea decat lipsa compensarii e
  contra-intuitiv, usor de reprodus, si spune ceva real despre de ce esueaza
  compensarile de latenta implementate neglijent.

Linear MPC (QP/OSQP) merita adaugat DOAR daca ai nevoie de constrangeri active
pe stare/comanda in timp real. LQR nu poate impune `|theta| <= theta_max`; un
QP poate, la ~1 ms. Daca constrangerile nu sunt esentiale pentru poveste, LQR+
predictie e suficient si mai simplu de aparat metodologic.

---

## 7. CE RAMANE NEREZOLVAT

- `/mixed_cmd` si `/robot_cmd_delayed` inca nu au niciun abonat: bucla de shared
  control ramane deschisa, deci `alpha` nu are efect pe planta.
- `cartpole_sim.launch.py` inca nu porneste Gazebo. Exista acum URDF-ul valid,
  dar lipsesc world-ul SDF, `ros_gz_sim/gz_sim.launch.py` si `ros_gz_bridge`.
- `/robot_cmd` ramane `Twist` cu forta in `linear.x`, iar mixerul aduna o viteza
  cu o forta. Recomand `WrenchStamped` + mesaje cu timestamp (fara timestamp nu
  se poate masura latenta end-to-end).
- `D_h` din `compute_haptic_feedback` inca nu e folosit (feedback-ul e arc pur).
- Nucleul nu are inca `_selftest()` conform CLAUDE.md sec.2. Ar fi prins singur
  4 din bug-urile de pana acum.
