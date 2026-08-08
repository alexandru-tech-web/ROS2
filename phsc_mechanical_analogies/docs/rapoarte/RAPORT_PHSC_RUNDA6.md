# RAPORT PHSC -- Runda 6 (Monte Carlo si incadrare)

Data: 2026-08-08.

---

## 1. Monte Carlo

N=50 incercari PERECHI per valoare de tau (aceleasi trageri date tuturor celor
trei conditii -- comparatia devine pe perechi, cu mult mai multa putere
statistica decat trei esantioane independente). Durata: 1119 s.

Trei schimbari fata de scriptul propus, toate de fond:

1. **Testez toate cele trei conditii, nu doar Smith.** Afirmatia care are
   nevoie de suport statistic este ABLATIA, nu pragul lui Smith.
2. **Planta are parametrii trasi, controllerul cunoaste doar valorile
   nominale.** In varianta propusa, `model` si `delayed` primeau ACEIASI
   parametri, deci masura variatia punctului de operare, nu nepotrivirea de
   model, si ar fi dat praguri optimiste.
3. **Grila fina intre 20 si 100 ms.** Cu grila propusa (20, 50, 80, ...),
   'none' si 'naiv' sar amandoua de la 100% la 0% intre aceleasi doua puncte
   si diferenta dintre ele devine invizibila. Verificat: la N=3 pe grila
   grosiera, toate cele 8 valori raportau 'egal'.

Corectate si doua erori de calcul din script: `zip(fall_times, [stable_count])`
producea o singura pereche in loc de N (media timpului de cadere era gresita),
iar `np.random.normal(1.0, 0.1)` pentru masa putea da valori spre zero,
adica impartire la zero in dinamica.

### Rezultat

| tau [ms] | fara compensare | naiv (u=0) | Smith (buffer) |
|---|---|---|---|
| 20-40 | 100% [0.93, 1.00] | 100% [0.93, 1.00] | 100% [0.93, 1.00] |
| 50 | 100% [0.93, 1.00] | **76% [0.63, 0.86]** | 100% [0.93, 1.00] |
| 60 | 84% [0.71, 0.92] | **28% [0.17, 0.42]** | 100% [0.93, 1.00] |
| 70 | 46% [0.33, 0.60] | **2% [0.00, 0.10]** | 100% [0.93, 1.00] |
| 80-100 | 0% [0.00, 0.07] | 0% [0.00, 0.07] | 100% [0.93, 1.00] |
| 150 | 0% | 0% | 96% [0.87, 0.99] |
| 200 | 0% | 0% | 94% [0.84, 0.98] |
| 250 | 0% | 0% | 72% [0.58, 0.83] |
| 300 | 0% | 0% | 0% [0.00, 0.07] |

**Raspunsuri directe la intrebarile puse:**

- **P(stabil) > 95%**: fara compensare pana la **50 ms**; naiv pana la
  **40 ms**; Smith pana la **150 ms**.
- **P(stabil) > 50%**: fara compensare pana la **60 ms**; naiv pana la
  **50 ms**; Smith pana la **250 ms**.
- **Prag la P=50%** (interpolare liniara intre punctele grilei):
  fara compensare **69 ms**, naiv **55 ms**, Smith **265 ms**.

Figura: `monte_carlo_stability.png` (P(stabil) vs tau, banda = interval
Wilson 95%).

### Test statistic pereche (adaugat, nu era cerut)

Intervalele Wilson nu se suprapun la 50, 60 si 70 ms, ceea ce e deja
suficient. Dar incercarile fiind perechi, testul corect si mai puternic este
McNemar exact -- si e ce va cere un reviewer.

| tau [ms] | ambele | doar 'none' (b) | doar 'naiv' (c) | niciunul | p (o coada) |
|---|---|---|---|---|---|
| 50 | 38 | 12 | **0** | 0 | 2.4e-04 |
| 60 | 14 | 28 | **0** | 8 | 3.7e-09 |
| 70 | 1 | 22 | **0** | 27 | 2.4e-07 |

**`c = 0` la toate cele trei valori.** Pe 150 de incercari perechi, predictia
naiva nu a salvat NICIODATA o incercare pe care lipsa compensarii o pierdea;
a stricat 62 dintre ele. Rezultatul nu e marginal.

### Cross-check

Pragul Smith de 265 ms de aici (nepotrivire de parametri, tau cunoscut cu
~5-10% eroare) cade intre cele doua cifre din studiul de robustete al rundei
3: 300-400 ms ideal, 100-150 ms cand se adauga si 20% eroare pe tau. Cele doua
studii, facute independent, se confirma reciproc si arata din nou ca eroarea
de estimare a latentei domina, nu nepotrivirea de parametri.

## 2. `ARTICLE_DRAFT.md` -- creat

`~/phsc_docs/ARTICLE_DRAFT.md`, cu abstract completat cu cifrele reale.

Doua abateri de la structura propusa:

**Titlul.** Am propus reincadrarea pe compensarea latentei, nu pe haptica:
*When Prediction Hurts: Input-Assumption Mismatch in Delay Compensation for
Teleoperation*. Titlul initial contine 'Haptic Shared Control', dar bucla de
shared control este deschisa si feedback-ul haptic nu a fost evaluat nici cu
dispozitiv, nici cu operator. Un reviewer de la un venue de haptica ar
observa imediat.

**Citarile.** Toate referintele sunt marcate `[DE VERIFICAT]`. Nu le-am citit
si nu confirm ca exista in forma citata; provin din cautarea facuta de Kimi.
Conform CLAUDE.md sec. 0, nu se transforma in bibliografie pana nu sunt
verificate la sursa.

## 3. `PHSC_POSITIONING.md` -- creat

`~/phsc_docs/PHSC_POSITIONING.md`. Decizia ta (Optiunea A, contributie
proprie) e consemnata ca atare. Am adaugat doua rezerve in scris:

**Rezerva 1: originalitatea se sprijina pe o cautare pe care nu am facut-o
eu.** Nu am acces la rezultatele cautarii si nu am deschis niciuna dintre
lucrari. Intreaga decizie 'contributie vs demonstrator' atarna de acea
singura afirmatie. Recomand sa verifici personal 5-10 lucrari, cautand si
formulari echivalente ('prediction with incorrect input assumption',
'predictor mismatch destabilization', 'open-loop prediction in delay
compensation'). Daca rezultatul exista deja, nu e o pierdere: incadrarea se
muta pe caracterizare cantitativa + implementare reproductibila.

**Rezerva 2: nici hardware, nici operator uman.** Plus bucla de shared
control deschisa. De aici si propunerea de reincadrare a titlului.

Am notat si legatura cu C1, care mi se pare reala si nu cosmetica: C1
caracterizeaza canalul, PHSC arata ce inseamna acea caracterizare pentru o
bucla inchisa peste el, iar cifra de +/-20% da un criteriu concret pentru cat
de bine trebuie sa masoare C1.

## 4. Commit si tag

**Nu am facut commit si nu am pus tag v1.1. Nu exista ce comite.**

`git status` pe `phsc_*` este gol. Tot ce a produs runda 6 se afla, conform
cererii tale din runda 5, in afara depozitului:
- `~/phsc_docs/` -- ARTICLE_DRAFT, PHSC_POSITIONING, RESULTS actualizat, figuri
- `~/phsc_sim/` -- `monte_carlo_stability.py`, `mcnemar_ablation.py`

Un tag `v1.1-monte-carlo` pe un arbore neschimbat ar sugera ca s-a modificat
cod, ceea ce nu s-a intamplat. `v1.0-simulation` descrie corect starea
codului.

**O recomandare totusi:** articolul va revendica reproductibilitate.
`monte_carlo_stability.py` si `mcnemar_ablation.py` sunt cod, nu date, si
sunt exact artefactele de care are nevoie cineva ca sa reproduca tabelele.
Ar merita versionate. Spune-mi daca vrei sa le adaug intr-un
`phsc_mechanical_analogies/studies/` si comit atunci.

## 5. Venue -- evaluare onesta

Ai cerut o recomandare intre IEEE T-Mech, T-RO sau altceva.

**Nu recomand T-RO sau T-Mech in forma actuala.** Ambele sunt reviste de prim
rang care asteapta de regula validare experimentala pe hardware. Aici avem un
singur sistem de test, simulat, fara robot, fara operator uman, si cu bucla de
shared control deschisa desi apare in numele directiei. Riscul de respingere
pe lipsa de validare experimentala e mare, iar un ciclu de review acolo costa
luni pe care, la 5-10 h/saptamana, nu le ai de pierdut.

In ordinea realismului:

1. **Workshop pe teleoperare sau control in retea.** Prima alegere, si nu ca
   varianta de consolare: un rezultat contra-intuitiv beneficiaza de discutie
   inainte de a fi extins, iar feedback-ul vine exact de la oamenii care ar
   sti daca rezultatul e deja publicat. Rezolva si Rezerva 1.
2. **Conferinta cu tematica de teleoperare sau sisteme.** O lucrare de
   caracterizare bine facuta, cu cod reproductibil, e bine primita, si ciclul
   e scurt.
3. **RA-L, dupa adaugarea hardware-ului.** Chiar si o singura articulatie UR3
   ar schimba categoria. Fara ea, nu e competitiva.

Nu dau nume si termene concrete de conferinte: nu le pot verifica de aici, iar
un termen gresit e mai daunator decat unul lipsa.

## 6. Ce as face in ordinea asta

1. Verificarea de originalitate (jumatate de zi). Singurul lucru care poate
   schimba incadrarea articolului.
2. Decizia despre track-uri: PHSC ca al doilea track activ contrazice
   CLAUDE.md sec. 1. Ceva trebuie pus pe pauza.
3. Reincadrarea titlului pe latenta, nu pe haptica.
4. Abia apoi scrisul propriu-zis.
