# PHSC -- Raport final

Data: 2026-08-08. Stare: **ON HOLD** ca track independent.

---

## Rezultate validate

| rezultat | valoare | metoda |
|---|---|---|
| prag stabilitate Smith | **265 ms** (P=50%) | Monte Carlo N=50 perechi |
| prag fara compensare | 69 ms (P=50%) | idem |
| prag predictie naiva | 55 ms (P=50%) | idem |
| naiv vs fara compensare | `c=0`, p < 2.4e-04 | McNemar exact, 150 perechi |
| estimator tau | +1.06% medie, 14.41% p95 | simulare, jitter 4 ms |
| theta rms, tau variabil 50-150 ms | 1.31 grade | bucla inchisa 100 Hz |
| rata nod MPC | 20.03 Hz masurat | `ros2 topic hz` |
| garzi de siguranta | watchdog, limite, e-stop | verificate live |

Toate din SIMULARE. Nicio validare pe hardware, niciun operator uman.

## Artefacte

| ce | unde |
|---|---|
| cod | ramura `phsc-v1-simulation`, tag **`v1.0-final`** |
| documentatie | `~/phsc_docs/` (METHODOLOGY, RESULTS, ARTICLE_DRAFT, PHSC_POSITIONING, UR3_MIGRATION) |
| simulari si figuri | `~/phsc_sim/` (monte_carlo_stability.py, mcnemar_ablation.py, ablation_study.py, ...) |
| decizie de arhitectura | `phsc_bringup/ARCHITECTURE.md` (in repo) |

`main` nu a fost atins. Merge cand vrei:
`git checkout main && git merge phsc-v1-simulation`.

---

## Integrarea in C1-C4: ce am facut si ce NU am facut

**Nu am copiat cod in C1-C4.** Doua motive verificate, nu presupuse.

### Motivul 1: maparea propusa nu corespunde cu ce sunt C1-C4

Maparea din cererea de integrare a fost: C1 = retea degradata, C2 = control
predictiv, C3/C4 = haptic shared control. Conform CLAUDE.md sec. 1 si 7,
contributiile sunt de fapt:

| | ce este in realitate | directoare |
|---|---|---|
| C1 | benchmark rmw_zenoh vs rmw_cyclonedds_cpp sub degradare controlata (netem) | `c1_benchmark/` |
| C2 | analiza pierderilor in rafala (Gilbert-Elliott) | `c2_analysis/`, `c2_planning/` |
| C3 | mesh multi-hop, selector link-aware | `mesh_plugin/`, `link_adaptive/`, `c3_gateway/` |
| C4 | exoschelet de reabilitare + motor | `rehab_exo_description/`, `servo_control/`, `joint_emulator/` |

Nu exista un 'C2 = control predictiv' si nici un 'C3/C4 = haptic shared
control'. Daca as fi copiat dupa maparea propusa, codul PHSC ar fi ajuns in
proiecte care fac cu totul altceva.

### Motivul 2: mecanismul de copiere e gresit oricum

- `c1_benchmark/` **nu este pachet ROS** (fara `package.xml`, fara `setup.py`)
  -- e un director de scripturi Python pure, conform metodologiei din
  CLAUDE.md sec. 2. Un nod rclpy precum `latency_estimator.py` copiat acolo
  nu ar putea fi pornit cu `ros2 run` si nu ar avea ce cauta in acel context.
- `phsc_mechanical_analogies` este deja un pachet ament instalabil. In ROS 2,
  un alt pachet il foloseste declarand `<depend>` in `package.xml`, **nu
  copiindu-i fisierele**. O copie ar diverge de original la prima corectie,
  si am fi in situatia de a avea doua `predict_state_smith` diferite.
- 'adapteaza `latency_estimator` la modulul tau de masurare RTT' cere sa
  cunosc interfata acelui modul. `bench_core.rtt_stats(rtts_ms, sent,
  received)` este o functie pura care primeste o lista de esantioane si
  intoarce statistici -- nu o sursa live de tau. Adaptarea nu e o copiere, e
  o proiectare, si nu o fac orbeste. Este acelasi motiv pentru care nu am
  scris cod pentru UR3.

### Ce integrare chiar are sens

Trei punti reale, in ordinea valorii:

**C1 -> PHSC (cea mai puternica).** C1 masoara distributii de RTT sub
degradare controlata. PHSC foloseste momentan un model de latenta inventat
(sinusoida + zgomot gaussian). Inlocuirea acelui model cu distributii
MASURATE din campaniile C1 ar transforma pragurile PHSC din 'praguri fata de
o latenta presupusa' in 'praguri fata de latenta reala a stivei'. Asta e o
imbunatatire de fond a rezultatului, nu o mutare de fisiere.

**PHSC -> C1 (reciproca).** Sensibilitatea masurata (+/-20% eroare pe tau
injumatateste marja de stabilitate) da C1 un criteriu de proiectare
cuantificat: cat de precis trebuie sa estimeze canalul ca o bucla inchisa
peste el sa ramana stabila. C1 raspunde momentan la 'cat de mare e RTT-ul';
asta ii adauga 'cat de bine trebuie sa-l stim'.

**C2 -> PHSC.** C2 studiaza pierderi in RAFALA. Modelul de latenta din PHSC
nu are rafale -- e neted. Un profil de intarziere de tip Gilbert-Elliott ar
testa predictorul Smith exact acolo unde ar trebui sa doara: cand bufferul de
comenzi in zbor are goluri. Este, cred, cel mai interesant experiment
ramas nefacut, si leaga doua contributii care acum nu se ating.

**C4** este singurul loc unde 'haptic shared control' se potriveste tematic
(exoschelet = sistem cu om in bucla si interactiune de forta). Dar C4 are
propriul model si propria conventie de articulatie (CLAUDE.md sec. 6:
'rotatie pozitiva pe axa Y = extensie'). Transferul cere aceeasi identificare
experimentala ca UR3, nu o copiere.

Niciuna dintre acestea nu e o mutare de fisiere. Toate sunt lucru de
proiectare pe care nu il incep fara decizia ta, mai ales ca punctul urmator
spune ca PHSC intra in pauza.

---

## Conditii de reactivare

- [ ] Verificare personala a literaturii (5-10 lucrari citite, nu doar
      titluri). Cuvinte-cheie: *predictor mismatch destabilization*,
      *open-loop prediction in delay compensation*, *Smith predictor input
      assumption*
- [ ] Confirmarea originalitatii ablatiei si a mecanismului 'naiv < none'
- [ ] Identificare experimentala pe hardware (UR3 sau articulatie de
      exoschelet), conform `UR3_MIGRATION.md`
- [ ] Decizia despre ce track se pune pe pauza in schimb (CLAUDE.md sec. 1:
      un singur track activ o data)

Daca originalitatea NU se confirma: PHSC ramane demonstrator, iar valoarea se
muta pe caracterizarea cantitativa si implementarea reproductibila. Cifrele
raman valabile in ambele cazuri.

## Ce ramane deschis in cod

Neschimbat: `/mixed_cmd` si `/robot_cmd_safe` fara abonati (bucla de shared
control deschisa); Gazebo nepornit din launch (URDF valid, lipsesc world SDF
si bridge); `Twist` folosit pentru forta; `D_h` nefolosit in feedback-ul
haptic; lipsa `_selftest()` conform CLAUDE.md sec. 2.

Recomandare separata: `monte_carlo_stability.py` si `mcnemar_ablation.py`
sunt cod, nu date, si sunt artefactele de care are nevoie cineva ca sa
reproduca tabelele dintr-un articol. Momentan sunt in afara depozitului.
Merita versionate daca articolul revendica reproductibilitate.
