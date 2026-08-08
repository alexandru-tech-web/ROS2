# PHSC -- Rezultate numerice

Mediu: Ubuntu 24.04, ROS 2 Jazzy, Gazebo Harmonic (gz-sim8 8.13.0),
Python 3.12 sistem (numpy 1.26.4, scipy 1.11.4).
Masina: laptop, CPU nededicat, fara izolare de nuclee.

**Statut al datelor: SIMULARE.** Sectiunea 3b (Monte Carlo) are acum N=50
incercari perechi cu interval de incredere; restul sectiunilor raman cu o
singura rulare determinista (N=1) si sunt marcate ca atare. Timpii de calcul
depind de masina si de incarcarea ei (laptop, CPU nededicat). Nicio validare
pe hardware. Inainte de submisie, sec. 2 trebuie repetata pe masina dedicata,
iar sec. 4-6 reluate pe HIL.

---

## 1. Validare de model

| verificare | rezultat | sursa |
|---|---|---|
| `A[3][3]` analitic vs Jacobian numeric | `0.0` vs `0.0`; diferenta max pe A: `5.8e-12` | `cartpole_model.py` |
| toate cele 16 intrari ale lui A + 4 ale lui B | potrivire exacta | idem |
| valori proprii `A - B K` (LQR) | `-7.59 +/- 3.43j`, `-1.33 +/- 1.02j` | idem |
| stabilitate bucla inchisa linearizata | toate `Re < 0` | idem |
| castig LQR `K` | `[-10.00, -11.72, -72.16, -14.74]` | idem |
| pol instabil bucla deschisa | `4.64 rad/s` (constanta de timp `215 ms`) | idem |
| orizont de predictie vs RK4 fin | eroare `1e-7` (era trunchiere de 37.5%) | `mpc_controller.py` |
| control optim la `x0 = [0,0,0.1,0]` | `3.1556 N`, `success=True` | `test_mpc.py` |

## 2. Benchmark de calcul

MPC neliniar (SLSQP, gradiente prin diferente finite), mediana pe 10 rulari:

| N | fara constrangere de stare | cu `theta_max` tare |
|---|---|---|
| 20 | 519 ms (1.9 Hz) | 982 ms (1.0 Hz) |
| 15 | 252 ms (4.0 Hz) | -- |
| 10 | 87 ms (11.5 Hz) | 170 ms (5.9 Hz) |
| 7 | **39 ms (25.6 Hz)** | 74 ms (13.5 Hz) |
| 5 | 15 ms (68 Hz) | -- |

Alternative real-time (mediana pe 1000 rulari):

| metoda | timp | rata |
|---|---|---|
| LQR (castig precalculat) | 1.73 us | 576 kHz |
| LQR + predictie RK4, 20 pasi | 740 us | 1352 Hz |
| LQR + predictie RK4, 4 pasi | 152 us | 6597 Hz |

Rata reala masurata in nodul ROS (`ros2 topic hz /robot_cmd`):

| configuratie | rata |
|---|---|
| N=20, `theta_mode=hard` (implicit initial) | **1.99 Hz** |
| N=7, `theta_mode=soft` | **20.03 Hz** (min 0.047 s, max 0.052 s) |

## 3. Ablatie: compensarea latentei

LQR pe cart-pole, `tau = 100 ms` constant, controller 100 Hz, `theta0 = 5.7`
grade, 5 s de simulare. Figura: `ablation_study.png`.

| conditie | \|theta\|max | theta rms | u rms | verdict |
|---|---|---|---|---|
| 1. fara compensare | 5954.75 grade | 3149.60 grade | 93.16 N | cade la **0.88 s** |
| 2. predictie naiva (`u=0`) | 5115.43 grade | 2801.47 grade | 96.71 N | cade la **0.53 s** |
| 3. predictie Smith (buffer) | **6.43 grade** | **1.56 grade** | **1.06 N** | **stabil** |

Praguri, prin baleiaj pe `tau`:

| tau [ms] | fara compensare | naiv (`u=0`) | Smith (buffer) |
|---|---|---|---|
| 20 | stabil (5.8 grade) | stabil (5.8 grade) | stabil (5.8 grade) |
| 50 | stabil (5.9 grade) | nestabilizat (17 grade) | stabil (5.9 grade) |
| 80 | cade 1.25 s | cade 0.65 s | stabil (6.2 grade) |
| 100 | cade 0.88 s | cade 0.53 s | stabil (6.4 grade) |
| 120 | cade 0.71 s | cade 0.54 s | stabil (6.7 grade) |
| 150 | cade 0.78 s | cade 0.70 s | stabil (7.3 grade) |
| 200 | cade 0.63 s | cade 0.48 s | stabil (8.6 grade) |

**Prag: fara compensare 50-80 ms, predictie naiva 20-50 ms, Smith > 200 ms.**

## 3b. Monte Carlo: P(stabil) vs latenta, cu bare de eroare

N=50 incercari PERECHI per valoare de tau (aceleasi trageri date tuturor
celor trei conditii). Planta cu parametri trasi, controllerul pe modelul
NOMINAL -- deci exista nepotrivire reala de model, nu doar variatie de punct
de operare. `theta0 ~ U(0.05, 0.15)` rad; `M, m, L, b` normale cu 10%
deviatie, limitate la valori fizice; jitter 2 ms pe latenta. Planta la 1 ms,
controller la 100 Hz, 5 s. Interval Wilson 95%. Durata: 1119 s.
Figura: `monte_carlo_stability.png`.

| tau [ms] | fara compensare | naiv (u=0) | Smith (buffer) |
|---|---|---|---|
| 20 | 100% [0.93, 1.00] | 100% [0.93, 1.00] | 100% [0.93, 1.00] |
| 30 | 100% [0.93, 1.00] | 100% [0.93, 1.00] | 100% [0.93, 1.00] |
| 40 | 100% [0.93, 1.00] | 100% [0.93, 1.00] | 100% [0.93, 1.00] |
| 50 | 100% [0.93, 1.00] | **76% [0.63, 0.86]** | 100% [0.93, 1.00] |
| 60 | 84% [0.71, 0.92] | **28% [0.17, 0.42]** | 100% [0.93, 1.00] |
| 70 | 46% [0.33, 0.60] | **2% [0.00, 0.10]** | 100% [0.93, 1.00] |
| 80 | 0% [0.00, 0.07] | 0% [0.00, 0.07] | 100% [0.93, 1.00] |
| 100 | 0% [0.00, 0.07] | 0% [0.00, 0.07] | 100% [0.93, 1.00] |
| 150 | 0% [0.00, 0.07] | 0% [0.00, 0.07] | 96% [0.87, 0.99] |
| 200 | 0% [0.00, 0.07] | 0% [0.00, 0.07] | 94% [0.84, 0.98] |
| 250 | 0% [0.00, 0.07] | 0% [0.00, 0.07] | 72% [0.58, 0.83] |
| 300 | 0% [0.00, 0.07] | 0% [0.00, 0.07] | 0% [0.00, 0.07] |

Praguri:

| conditie | P >= 95% pana la | P >= 50% pana la | incrucisare P = 50% |
|---|---|---|---|
| fara compensare | 50 ms | 60 ms | **69 ms** |
| naiv (u=0) | 40 ms | 50 ms | **55 ms** |
| Smith (buffer) | 150 ms | 250 ms | **265 ms** |

**Ablatia se sustine statistic.** La 50, 60 si 70 ms intervalele Wilson
pentru 'fara compensare' si 'naiv' NU se suprapun, iar naivul este de fiecare
data mai prost. Vezi sec. 3c pentru testul pereche.

Cross-check de consistenta: pragul Smith de 265 ms obtinut aici (nepotrivire
de parametri, dar tau cunoscut cu ~5-10% eroare) este intre cele doua cifre
din sec. 4: 300-400 ms ideal si 100-150 ms cand se adauga si 20% eroare pe
tau. Cele doua studii se confirma reciproc si arata din nou ca eroarea de
estimare a latentei domina, nu nepotrivirea de parametri.

## 3c. Test statistic pereche (McNemar exact)

Incercarile fiind perechi, testul corect este McNemar, nu chi-patrat pentru
esantioane independente: acesta din urma ar ignora tocmai informatia care da
putere comparatiei. Varianta exacta (binomiala), pentru ca numerele sunt mici.
`b` = incercari unde doar 'fara compensare' a fost stabil (naivul a stricat);
`c` = incercari unde doar 'naiv' a fost stabil (naivul a ajutat).
Ipoteza alternativa: `b > c`.

| tau [ms] | ambele | doar 'none' (b) | doar 'naiv' (c) | niciunul | p (o coada) |
|---|---|---|---|---|---|
| 50 | 38 | 12 | **0** | 0 | 2.4e-04 |
| 60 | 14 | 28 | **0** | 8 | 3.7e-09 |
| 70 | 1 | 22 | **0** | 27 | 2.4e-07 |

**`c = 0` la toate cele trei valori de tau.** Pe 150 de incercari perechi,
predictia naiva nu a salvat NICIODATA o incercare pe care lipsa compensarii o
pierdea; a stricat in 62 de cazuri. Rezultatul nu e marginal.

Formularea prudenta pentru articol: aceasta este o afirmatie despre ACEST
sistem, in ACEST regim de latenta. Nu am testat alte plante si nici alte legi
de comanda; generalizarea trebuie formulata ca ipoteza, nu ca rezultat.

## 4. Robustete a predictorului Smith

Cat din performanta este metoda si cat este potrivirea artificiala dintre
predictor si planta:

| conditie | prag de stabilitate |
|---|---|
| ideal (predictor = planta, interpolare identica) | 300-400 ms |
| canal ZOH (pachete discrete) | **200-250 ms** |
| `tau` subestimat cu 20% | 100-150 ms |
| `tau` supraestimat cu 20% | 100-150 ms |
| `tau` subestimat cu 50% | 50-100 ms |
| parametri fizici gresiti (+30% masa) | 100-150 ms |
| combinat: ZOH + `tau` -20% + parametri gresiti | **100-150 ms** |

**Cifra de raportat in articol: 200-250 ms** (ZOH). Cei 300-400 ms sunt
limita teoretica ce presupune potrivire perfecta predictor-planta.
**Marja de design pentru hardware: 100-150 ms.**

## 5. Bucla inchisa cu latenta variabila

`tau(t)` sinusoidal 50-150 ms (perioada 4 s), controller 100 Hz, 10 s:

| scenariu | theta rms | \|theta\|max | verdict |
|---|---|---|---|
| ORACLE (`tau` cunoscut exact) | 1.14 grade | 6.56 grade | tinta atinsa |
| ESTIMAT (EWMA din RTT zgomotos) | 1.31 grade | 6.58 grade | tinta atinsa |

Tinta: `theta_rms < 2` grade, `|theta|max < 15` grade. Ambele atinse.

## 6. Estimator de latenta

Simulare, `tau(t)` 50-150 ms, jitter gaussian 4 ms pe RTT, EWMA `alpha=0.3`
la 20 Hz:

| metrica | valoare |
|---|---|
| eroare medie | +1.06 % |
| eroare p95 | 14.41 % |
| eroare maxima | 18.12 % |
| prag critic (sec. 4) | +/- 20 % |

Masurat live pe loopback ROS (estimator + echo pe aceeasi masina):

| metrica | valoare |
|---|---|
| `tau` estimat | 1.1 - 1.3 ms |
| medie / std | 1.46 ms / 0.27 ms |
| min / max | 0.75 ms / 1.95 ms |
| pierdere de pachete | 0.4 - 0.8 % |

Loopback-ul nu este reprezentativ pentru o legatura reala; serveste doar la
validarea functionala a lantului ping-pong.

## 7. Garzi de siguranta (verificate live)

| test | rezultat observat |
|---|---|
| nicio stare de la pornire | `E-STOP: nicio stare primita in 3 s de la pornire` |
| stare oprita in functionare | `E-STOP: stare lipsa de 309 ms` |
| depasire limita de unghi | `E-STOP: theta=28.6 grade peste limita 10` |
| clamp comanda (500 N cerut, `u_max`=50) | `/robot_cmd_safe -> 50.0` |
| comanda dupa e-stop | `0.0`, publicata activ si repetat |
| resetare explicita | `E-stop RESETAT (era: stare lipsa de 309 ms)` |

## 8. Integrare `tau` online in MPC

| test | rezultat |
|---|---|
| nod consuma `/estimated_delay` | da |
| degradare la estimare veche | `"/estimated_delay vechi de 506 ms; revin la tau_est static (80 ms)"` |
| validare valoare | valori non-finite sau in afara `[0, 1] s` respinse |

## 9. Build

| pachet | stare |
|---|---|
| `phsc_mechanical_analogies` | OK |
| `phsc_teleop_mpc` | OK (5 executabile) |
| `phsc_gazebo_plugins` | OK |
| `phsc_bringup` | OK |

4/4, 0 stderr, de la zero. `rosdep install`: toate dependintele rezolvate.
Cod 100% ASCII (CLAUDE.md sec. 3).
URDF cart-pole validat cu `check_urdf`. Plugin Gazebo verificat cu
`gz plugin --info`: `Found 1 plugin: phsc::VariableDelayPlugin`, 3 interfete.
