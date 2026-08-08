# RAPORT PHSC -- Runda 5 (consolidare)

Data: 2026-08-08.

---

## 1. Test final integrat -- toate nodurile simultan

**DA.** Cinci noduri pornite simultan, alimentate cu stare (20 Hz) si comanda
umana (10 Hz), 20 s de rulare:

```
/latency_echo  /latency_estimator  /safety_watchdog
/shared_control_mixer  /mpc_controller_node
```

| topic | publisheri | rata masurata |
|---|---|---|
| `/robot_cmd` | 1 | 20.033 Hz |
| `/haptic_feedback` | 1 | 20.097 Hz |
| `/estimated_delay` | 1 | 19.996 Hz |
| `/safety_status` | 1 | 50.013 Hz |
| `/mixed_cmd` | 1 | 20.001 Hz |

Valori: `/safety_status: true`, `/estimated_delay: 0.89 ms` (loopback),
`/robot_cmd: 2.7768 N` -> `/robot_cmd_safe: 2.7785 N` (sub limite, trece).
Mixerul: `0.5*0.2 + 0.5*2.777 = 1.488`, exact ce publica.

**Zero erori, zero traceback-uri, zero exceptii in toate cele 5 loguri.**

Nota de metoda: prima rulare a acestui test a dat rezultate false (4 instante
de `safety_watchdog`, `/safety_status: false`, 200 Hz) din cauza unor noduri
ramase din testele rundelor anterioare. Cifrele de mai sus sunt din rularea
curata, dupa oprirea lor.

## 2. Cod mort eliminat

| element | ce era | actiune |
|---|---|---|
| `DelayedCartPole.state_history` | lista initializata si resetata, niciodata scrisa sau citita | eliminata |
| `MPCController.solve(tau_current=...)` | parametru primit si aruncat | folosit: se salveaza in `solve_taus`, ca sa se poata corela timpul de solve cu latenta |
| `MPCController._constraints()` | reconstruia bounds-urile de control, nu era apelata niciodata (runda 2) | inlocuita cu `_theta_margin()`, constrangere reala |
| `_inflight_at()` | inlocuita de `predict_state_smith()` (runda 3) | eliminata |
| `compute_alpha_adaptive()` | intorcea `alpha` fix, dar numele sugera adaptare | pastrata, dar documentata explicit ca NEIMPLEMENTATA + avertisment la pornire daca `alpha_mode='adaptive'` |

Topicuri fara abonati, acum documentate ca atare in loc sa para functionale:
`/mixed_cmd` (mixerul avertizeaza la pornire ca bucla e deschisa),
`/robot_cmd_safe`, `/haptic_feedback`, `/delay_stats`, `/robot_cmd_delayed`.

Ce **nu** am eliminat, desi nu e apelat din cod: `DelayedCartPole.simulate_step()`
si `predict_state_openloop()`. Sunt API public coerent, folosit din scripturile
de simulare, nu resturi.

## 3. Documentare

Creata in `~/phsc_docs/` (in afara git, cum ai cerut):

| fisier | continut |
|---|---|
| `METHODOLOGY.md` | model + derivare, analiza de stabilitate, mecanismul esecului predictiei naive, estimare de latenta, garzi, alegerea arhitecturii, limitari metodologice |
| `RESULTS.md` | toate tabelele numerice cu sursa fiecarei cifre, marcate PROVIZORIU (N=1) |
| `UR3_MIGRATION.md` | de ce nu exista cod pentru UR3, preconditii de identificare, inventar de interfata, ordinea recomandata |
| `ablation_study.png` | figura ablatiei |

`ARCHITECTURE.md` a ramas in repo (`phsc_bringup/`), fiind document de decizie
tehnica legat de cod.

## 4. Commit si tag

**DA, dar pe ramura, nu pe `main`.**

```
ramura : phsc-v1-simulation
commit : 154dca3  "PHSC v1.0 simulare: LQR+Smith, estimator latenta, garzi de siguranta"
tag    : v1.0-simulation
30 files changed, 2382 insertions(+)
```

Doua abateri fata de comanda propusa, ambele deliberate:

1. **`git add .` ar fi maturat munca nelegata de PHSC.** In `src/` erau
   necomise: stergerea a 3 fisiere din `gen_articol/` si 3 fisiere noi in
   `c1_benchmark/` si `c2_analysis/`. Am adaugat explicit doar cele 4
   directoare `phsc_*`. Restul a ramas neatins, exact cum era.
2. **Nu am comis pe `main`.** Sunt 30 de fisiere provenite dintr-un cod
   extern, revizuit dar nu de tine. Pe ramura poti citi diff-ul inainte.

Merge cand esti de acord:
```bash
cd ~/ros2_ws/src && git checkout main && git merge phsc-v1-simulation
```
Niciun push. Verificat: `main` a ramas neschimbat.

## 5. Suntem gata pentru primul articol?

**Pentru un articol complet: nu inca. Pentru un abstract sau o lucrare scurta
de conferinta: aproape, cu trei conditii.**

### Ce este solid

Caracterizarea este masurata, reproductibila si onesta despre propriile
limite: praguri de latenta pe trei strategii, studiu de sensibilitate care
separa metoda de artefactul de simulare (300-400 ms ideal vs 200-250 ms ZOH),
estimator validat, implementare ROS 2 care ruleaza la rata declarata. Figura
de ablatie spune povestea dintr-o privire.

### Ce lipseste, in ordinea importantei

**1. Nu am facut cautare de literatura. Nu pot sustine ca rezultatul e nou.**

Asta e cea mai importanta rezerva si tine de sec. 0 din CLAUDE.md. Predictorul
Smith e din 1957 si compensarea de latenta in teleoperare e un domeniu cu zeci
de ani de lucrari. Observatia ca o predictie cu model gresit al intrarii poate
fi mai rea decat lipsa compensarii este, odata explicata, destul de intuitiva
-- ceea ce inseamna ca e probabil sa fie deja documentata undeva, poate sub
alt nume (de exemplu ca instabilitate indusa de nepotrivirea predictorului).

Inainte de a numi asta contributie: cautare tintita pe Smith predictor
mismatch, model-mismatch instability in teleoperation, delay compensation
failure modes. Daca rezultatul exista deja, valoarea ramane in
caracterizarea cantitativa si in implementarea ROS 2 reproductibila -- ceea ce
inca justifica o lucrare, dar cu alta incadrare.

**2. N=1. Toate cifrele sunt dintr-o singura rulare determinista.**

Per CLAUDE.md sec. 0, datele SIL cu N=1 trebuie inlocuite inainte de orice
submisie. Pentru o simulare determinista, 'N=5' inseamna Monte Carlo peste
ceea ce chiar variaza: stare initiala, seed-ul de jitter pe RTT, parametrii
fizici trasi dintr-o distributie. Pragurile ar deveni intervale, nu puncte, si
tabelele ar avea bare de eroare. Este munca de cateva ore, si transforma
tabelele din indicative in publicabile.

**3. Nicio validare pe hardware.**

Vezi `UR3_MIGRATION.md`. Nu blocheaza o lucrare de simulare, dar limiteaza
locurile unde poate merge.

### Recomandarea mea

Ordinea cu cel mai bun raport efort/rezultat:
1. Cautarea de literatura (jumatate de zi) -- decide daca e contributie sau
   replicare, si deci ce fel de lucrare scrii
2. Monte Carlo N>=5 pe conditiile din `RESULTS.md` (cateva ore)
3. Abia apoi decizi tinta: daca rezultatul e nou, o lucrare de metoda; daca nu,
   o lucrare de tip 'reproducible implementation and characterization', care e
   perfect publicabila la un workshop sau la o conferinta de robotica aplicata

Si o observatie de incadrare: PHSC nu apare in harta C1-C4 din CLAUDE.md.
Inainte de a investi intr-un articol, merita decis daca devine o contributie
proprie a tezei sau ramane demonstrator -- altfel deschide un al doilea track
de cod in paralel, ceea ce sec. 1 din CLAUDE.md descurajeaza explicit.
