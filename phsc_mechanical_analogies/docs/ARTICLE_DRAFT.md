# Schelet de articol

**Titlu de lucru (varianta recomandata, reincadrata pe latenta):**
When Prediction Hurts: Input-Assumption Mismatch in Delay Compensation for
Teleoperation

Varianta initiala propusa era 'Predictive Haptic Shared Control with Smith
Predictor for Teleoperation Under Variable Latency'. Nu o recomand pentru
primul articol: contine 'Haptic Shared Control', dar bucla de shared control
este deschisa si feedback-ul haptic nu a fost evaluat nici cu dispozitiv, nici
cu operator. Vezi `PHSC_POSITIONING.md`, Rezerva 2.

---

## AVERTISMENT PRIVIND CITARILE

Numele de referinte care apar mai jos provin dintr-o cautare de literatura pe
care **nu am facut-o si nu am verificat-o eu**. Sunt marcate `[DE VERIFICAT]`.
Conform CLAUDE.md sec. 0, nu se transforma in bibliografie pana nu sunt citite
la sursa. Nu completa un `.bib` prin copiere din acest fisier.

---

## Abstract (schita)

Teleoperation over networks with variable latency commonly relies on
state prediction to compensate transport delay. We show that the assumption a
predictor makes about the *input* acting during the delay window is as
consequential as the accuracy of its plant model: a predictor that propagates
the plant under a zero-input assumption destabilizes the loop at lower
latencies than applying no compensation at all. On a cart-pole benchmark with
a 215 ms open-loop instability time constant, we measure 50%-stability thresholds
of 69 ms with no compensation, 55 ms with zero-input prediction, and 265 ms
with a Smith-type predictor driven by the buffered in-flight command history
(N=50 paired Monte Carlo trials per latency, plant-model mismatch included).
Across 150 paired trials at the three latencies where the conditions separate,
zero-input prediction never rescued a trial that no-compensation lost, while
degrading 62 of them (exact McNemar, p < 2.4e-04). We identify
the failure mechanism as overestimation of the predicted excursion leading to
actuator saturation, which adds rather than removes phase. We further quantify
the sensitivity of the compensated loop to latency-estimation error and report
a complete, reproducible ROS 2 Jazzy implementation including online latency
estimation.

Cifrele sunt completate din `RESULTS.md` sec. 3b si 3c (Monte Carlo N=50 si
McNemar exact). Pragurile deterministe din sec. 3 difera usor (50-80 / 20-50 /
>200 ms) pentru ca nu includ nepotrivirea de parametri; de raportat cele
Monte Carlo, care sunt mai conservatoare si au interval de incredere.

## 1. Introduction

- Context: teleoperare peste retele cu latenta variabila; compensarea
  predictiva e practica standard
- Observatia din care porneste lucrarea: literatura pe predictoare se
  concentreaza pe acuratetea modelului plantei si pe robustetea la eroarea de
  estimare a timpului mort `[DE VERIFICAT: Krstic 2008, Bresch-Pietri 2012]`.
  Ipoteza despre INTRAREA care actioneaza pe fereastra de predictie primeste
  mai putina atentie explicita.
- Contributii declarate:
  1. ablatie sistematica in trei conditii, cu praguri cantitative si bare de
     eroare
  2. rezultatul ca predictia cu intrare nula este mai rea decat lipsa
     compensarii, cu mecanismul explicat
  3. cuantificarea sensibilitatii la eroarea de estimare a latentei
  4. implementare ROS 2 completa si reproductibila

Nota de onestitate pentru introducere: formuleaza contributia 1 ca
'systematic ablation with quantified thresholds', nu ca 'first to observe'.
A doua formulare cere o cautare exhaustiva pe care nu am facut-o.

## 2. Background

- Smith predictor `[DE VERIFICAT: Smith 1959]`
- Control predictiv pentru sisteme cu timp mort
  `[DE VERIFICAT: Artstein 1982, Krstic 2008, Bekiaris-Liberis & Krstic 2013]`
- Robustete la nepotrivire de model si la eroarea de timp mort
  `[DE VERIFICAT: Bresch-Pietri 2012]`
- Compensarea intarzierii in teleoperare: variabile de unda, scattering
  `[DE VERIFICAT: Anderson & Spong, Niemeyer & Slotine]`
- Saturatie in predictoare `[DE VERIFICAT: Zheng et al.]`
- Model-mediated teleoperation `[DE VERIFICAT: Lima et al., Vakharia et al.]`

## 3. Methodology

### 3.1 Plant and delay channel
Cart-pole neliniar, ecuatii Euler-Lagrange, linearizare, polul instabil la
4.64 rad/s (constanta de timp 215 ms). Canal: `u(t - tau(t))`, livrare cu
retinere de ordin zero. Detalii in `METHODOLOGY.md` sec. 1.

### 3.2 Three prediction strategies
Aceeasi lege de comanda (`u = -K x_hat`), aceeasi rata (100 Hz), aceeasi
planta. Singura variabila: cum se obtine `x_hat`.
- `none`: `x_hat = x`
- `naive`: propagare `tau` inainte cu intrare nula
- `smith`: propagare `tau` inainte cu comenzile in zbor, din buffer

Aceasta e constructia experimentala care izoleaza ipoteza despre intrare de
orice alt factor.

### 3.3 Online latency estimation
Ping-pong cu timestamp, `tau ~ RTT/2`, EWMA `alpha=0.3` la 20 Hz. Respingere
de outlieri cu clauza de schimbare de regim (necesara: o schimbare reala si
sustinuta a latentei arata ca un sir de outlieri). `METHODOLOGY.md` sec. 3.

### 3.4 Haptic feedback (secundar in aceasta lucrare)
Forta haptica proportionala cu eroarea de predictie, ca tensiune intr-un arc
virtual. **De prezentat ca element de arhitectura, nu ca rezultat evaluat.**

## 4. Ablation study

- tabelul cu cele trei conditii la `tau` fix (determinist)
- baleiaj pe `tau`, praguri
- Monte Carlo N=50, incercari perechi, interval Wilson 95%, nepotrivire
  planta-model inclusa
- figura: `ablation_study.png` (traiectorii) si `monte_carlo_stability.png`
  (P(stabil) vs `tau` cu banda de incredere)

### 4.1 Failure mechanism
Predictorul cu intrare nula propaga un pendul in cadere libera, conchide ca
starea viitoare e mult mai rea decat va fi, si cere o corectie
supradimensionata. Comanda satureaza si ramane saturata. Rezultatul: faza
adaugata in bucla, nu eliminata. De sustinut cu subgraficul de comanda din
`ablation_study.png`, unde saturatia la +100 N e vizibila la 0.35 s.

## 5. Results

Din `RESULTS.md`:
- praguri deterministe si Monte Carlo, pe cele trei conditii
- `theta` rms si maxim cu `tau` variabil 50-150 ms: 1.14 grade (oracol),
  1.31 grade (estimat)
- acuratetea estimatorului: +1.06% medie, 14.41% p95
- studiul de sensibilitate: ideal 300-400 ms, ZOH 200-250 ms, cu nepotrivire
  100-150 ms
- cost de calcul: LQR+Smith 152 us vs NMPC N=7 39 ms vs NMPC N=20 519 ms

## 6. Discussion

- **De ce cifra raportata e cea cu ZOH.** Cu interpolare identica intre
  predictor si planta, pragul urca la 300-400 ms; diferenta e artefact de
  simulare, nu metoda. Aceasta transparenta e un punct forte, nu o slabiciune.
- Sensibilitatea dominanta la eroarea de estimare a latentei, si faptul ca
  supraestimarea strica la fel de mult ca subestimarea (deci nu exista
  conservatorism prin marirea lui `tau_est`).
- De ce LQR+Smith si nu NMPC in timp real, cu cifrele de cost.
- **Limitari, de scris explicit:** simulare, fara hardware; fara operator
  uman; bucla de shared control deschisa; canal simetric presupus in
  `tau = RTT/2`; un singur sistem de test (cart-pole).

## 7. Conclusion

## Reproducibility
Cod: `phsc_*` in monorepo, tag `v1.0-simulation`. Scripturi de simulare si
figuri: `~/phsc_sim`. Stack: ROS 2 Jazzy, Gazebo Harmonic, Python 3.12.

---

## Alegerea venue-ului -- evaluare onesta

Ceruta a fost o recomandare intre IEEE T-Mech, T-RO sau altceva.

**Nu recomand T-RO sau T-Mech pentru aceasta lucrare, in forma actuala.**
Ambele sunt reviste de prim rang care asteapta, de regula, validare
experimentala pe hardware. Aici avem: un singur sistem de test, simulat, fara
robot, fara operator uman, si cu bucla de shared control deschisa desi apare
in titlul directiei. Probabilitatea de respingere pe lipsa de validare
experimentala este mare, iar un ciclu de review la aceste reviste costa luni.

Ce recomand, in ordinea realismului:

1. **Conferinta cu tematica de teleoperare sau sisteme** -- unde o lucrare
   de caracterizare bine facuta, cu cod reproductibil, este bine primita si
   ciclul e scurt. Se potriveste si cu ritmul tau de lucru (5-10 h/saptamana).
2. **Workshop** pe teleoperare sau control in retea -- ideal pentru un
   rezultat contra-intuitiv care merita discutat inainte de a fi extins.
   Feedback rapid de la exact oamenii care ar sti daca rezultatul e deja
   cunoscut -- ceea ce rezolva si Rezerva 1 din `PHSC_POSITIONING.md`.
3. **RA-L, dupa adaugarea hardware-ului** (UR3, chiar si o singura
   articulatie). Cu validare pe robot, lucrarea devine competitiva; fara ea,
   nu.

Observatie de context: ai deja SSRR 2026 ca tinta pentru A1 din `c1_benchmark`.
Daca PHSC devine al doilea articol in paralel, verifica intai regula de 'un
singur track activ' din CLAUDE.md sec. 1.

Nu dau nume si termene concrete de conferinte: nu le pot verifica de aici, iar
un termen gresit e mai daunator decat unul lipsa.
