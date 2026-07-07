# AUDIT CIFRE -- Draft_Articol_C1_2coloane_v2.docx (Pas 1)

Branch: paper/audit-v2. Read-only pe date brute (~/DATE_CAMPANIE/) si pe pipeline
(c1_benchmark/*.py). Recalcul canonic prin RULAREA (nu modificarea) make_tables.py.

SURSA DE ADEVAR: SURSA_DATELOR_C1.md nu exista in sistem. Am folosit documentatia
canonica din chiar directorul-sursa: ~/DATE_CAMPANIE/README_SIL.md si README_HIL_WIFI.md
(nu am ghicit cai). Fisiere canonice: <env>/date/<rmw>/<cond>/rep<N>/transport_p<P>_summary.json.

VERDICT GLOBAL PAS 1: PASS INTEGRAL. Zero valori picate dincolo de rotunjire.
Un singur caveat de FORMULARE (nu de cifra) la Sec. 4.1, mai jos.

================================================================================
## 1a. Trei raspunsuri de onestitate (din cod, cu fisier:linie)
================================================================================

### Q1 -- Ce definitie a jitter-ului calculeaza pipeline-ul?
NICIUNA. Pipeline-ul NU calculeaza o statistica de jitter (nici std de RTT, nici
IPDV/RFC3393). Nucleul de statistici `rtt_stats` (bench_core.py:48-60) produce doar:
n, sent, received, loss, mean_ms, p50_ms, p95_ms, p99_ms, min_ms, max_ms.
"jitter" apare EXCLUSIV ca parametru netem aplicat la intrare: `jitter_ms`
(bench_core.py:22-40; ex. lat200_jit50 => `delay 200ms 50ms`, bench_core.py:81-83).
Singurul `pstdev` din pipeline (make_tables.py:54) e folosit pentru `loss_std`
(make_tables.py:62) = abaterea standard a PIERDERII intre repetitii (bara de eroare),
NU jitter de RTT.
=> Draftul (Sec. 3.2, ec. 1) descrie CORECT jitter-ul ca model de intrare netem
   (`d_i = DELAY + x_i*JITTER`, x_i ~ normala discretizata). NU exista in articol o
   valoare de "jitter masurat"; daca s-ar adauga una, ar fi [NEVERIFICABIL].

### Q2 -- RTT sau one-way? Un ceas sau doua?
RTT, UN SINGUR CEAS. Clientul stampileaza plecarea si intoarcerea pe ACELASI ceas
(`time.time()`): bench_client.py:34 `self.sent[seq] = time.time()` (plecare),
bench_client.py:43 `(time.time() - t0) * 1000.0` (RTT pe ecou ping->pong).
Serverul de ecou doar reflecta mesajul; nu se compara ceasuri intre masini, deci
masuratoarea e imuna la offset-ul de ceas laptop<->Pi.
=> Sec. 3.3 "RTT uses a single clock" = PASS (confirmat in cod).

### Q3 -- Metoda de agregare per conditie (TODO Sec. 3.3)
MEDIA PE REPETITII a metricilor PER-REP (loss, mean_ms, p95_ms). NU se concateneaza
esantioanele brute intre repetitii. Sursa: make_tables.py:8-12 (docstring explicit)
+ `aggregate_reps` (make_tables.py:37-64): `rtt_p95_ms = avg(per-rep p95s)` (linia 63),
`loss_mean = avg(per-rep losses)` (linia 62). N se raporteaza.
=> Draftul afirma DEJA corect, Sec. 3.3 linia: "condition-level figures aggregate
   per-repetition summaries". PASS. (Fraza gata de folosit e la finalul acestui raport.)

================================================================================
## 1b. N efectiv per mediu x conditie x rmw
================================================================================
Numarat din rep*/ pe toate cele 8 conditii x 2 RMW x 2 medii (payload 4096):
- SIL      : N=10 pe TOATE cele 16 celule (cyclonedds x8, zenoh x8). 8/8 conditii.
- HIL Wi-Fi: N=5  pe TOATE cele 16 celule. 8/8 conditii.
Confirmat SIL N=10 / HIL N=5. selftest make_tables.py: 16/16.

================================================================================
## 1c. Recalcul canonic vs draft (PASS/FAIL, toleranta = rotunjirea afisata)
================================================================================

### TABEL II -- pierdere (%), payload 4 KB -- 32 celule -> PASS INTEGRAL (32/32)
Comparatie celula-cu-celula (canonic == draft, |diff| <= 0.05):
  conditie      | SIL_CDDS SIL_Zenoh HIL_CDDS HIL_Zenoh
  ideal         |   0.0      0.0       0.0      0.0     PASS
  loss_5        |   0.0      0.0       0.0      0.0     PASS
  loss_15       |   1.4      8.5      20.8     61.6     PASS
  loss_20       |   7.7     16.9      53.5     93.7     PASS
  loss_25       |  26.5     34.1      70.4     98.8     PASS
  loss_30       |  41.0     57.8      80.5     99.2     PASS
  lat200_jit50  |   1.8      1.3      14.7     96.3     PASS
  lat200_l15    |  36.0     20.8      72.4    100.0     PASS

### TABEL III -- RTT p95 (ms) + loss (%) la lat200_jit50, 4 KB -> PASS (8/8)
  Env RMW         | p95 draft | p95 canonic | loss draft | loss canonic | verdict
  SIL CycloneDDS  |   484     |   484.2     |   1.8      |   1.8        | PASS
  SIL Zenoh       |   476     |   475.7     |   1.3      |   1.3        | PASS
  HIL CycloneDDS  |   635     |   635.2     |  14.7      |  14.7        | PASS
  HIL Zenoh       | 7,697     |  7696.9     |  96.3      |  96.3        | PASS

### Sec. 4.5 -- rularea reprezentativa -> PASS (localizata exact, NU [NEVERIFICABIL])
Toate din lat200_jit50 / payload 4096 / rep1:
  CDDS 962/989, mean 469, min 402, max 543
    -> DATE_CAMPANIE/HIL_WIFI/date/cyclonedds/lat200_jit50/rep1/transport_p4096_summary.json
       (received=962, sent=989, mean_ms=469, min_ms=402, max_ms=543)  EXACT
  Zenoh 184/989, mean 6185, min 1591, max 7872
    -> DATE_CAMPANIE/HIL_WIFI/date/zenoh/lat200_jit50/rep1/transport_p4096_summary.json
       (184, 989, 6185, 1591, 7872)  EXACT
  loopback Zenoh 977/989, mean 427, max 636
    -> DATE_CAMPANIE/SIL/date/zenoh/lat200_jit50/rep1/transport_p4096_summary.json
       (977, 989, 427, 636)  EXACT
  Nota: rep1 e singura repetitie HIL Zenoh lat200_jit50 cu date (rep2-5: received=0);
  agregatul 96.3% = media per-rep loss [81.4, 100, 100, 100, 100]/5 = 96.28 -> 96.3. Coerent.

### Sec. 4.1 -> PASS pe cifre; un caveat de FORMULARE
  - "1.1-1.4 ms" (SIL ideal, mean RTT): canonic SIL ideal mean = CDDS 1.1-1.2, Zenoh 1.3-1.4. PASS.
  - "0% loss" loopback ideal + "clean la 64 B si 4 KB" HIL: canonic loss = 0.0 peste tot. PASS.
  - "58% pierdere Zenoh la 64 KB ideal (HIL), CycloneDDS 0": canonic HIL ideal p65536 =
    Zenoh 57.8% (-> 58), CDDS 0.0%. PASS.
  - "reprodus identic in trei campanii separate": README_HIL_WIFI.md confirma "3 re-rulari
    identice" + copii 2056/2058/2059 in ~/c1_archive/. PASS (existenta celor 3 confirmata).
  - CAVEAT (formulare, nu cifra): fraza "clean at 64 B and 4 KB (mean RTT of 11-13 ms)"
    leaga "11-13 ms" de AMBELE payload-uri, dar 11-13 ms se verifica doar la 4 KB
    (HIL p4096: CDDS 11.3, Zenoh 12.9). La 64 B, HIL mean = CDDS 4.0, Zenoh 18.1 (in afara
    11-13). RECOMANDARE pentru Alexandru: restrange la "mean RTT 11-13 ms at 4 KB" (0% loss
    ramane valabil si la 64 B). Nu afecteaza nicio figura/tabel -> nu blocheaza Pasii 2-3.

### Fig. 4 (efect payload, 64 B vs 64 KB, ideal) -- zecimale exacte
  Singura valoare nenula: HIL Zenoh 64 KB ideal = 57.8% (afisat 58% in figura).
  Restul (HIL CDDS 64B/64KB, HIL Zenoh 64B, tot SIL la 64B, SIL 64KB CDDS/Zenoh) = 0.0%.
  => pentru Pas 2d (bloc PAYLOAD_LOSS din make_figures_c1_en.py): HIL Zenoh 65536 = 57.8.

### Abstract -> toate coerente cu canonicul/rularea reprezentativa
  96% (=96.3 agregat) PASS; 6.2 s (=6185 ms) PASS; 13x (=6185/469=13.2) PASS;
  469 ms (rep reprezentativa CDDS) PASS; 2.7% (=1-962/989=2.73, loss RULARE CDDS) PASS;
  14.7% (loss AGREGAT HIL CDDS) PASS; 1.3% / 1.8% (SIL Zenoh/CDDS lat200_jit50) PASS.

================================================================================
## 1d. Comanda tc netem lat200_jit50 + distributia jitter-ului
================================================================================
Comanda EXACTA (bench_core.py:69-83, netem_cmd pentru lat200_jit50:
base_ms=200, jitter_ms=50, loss=0.00), VERBATIM:

  tc qdisc replace dev <IFACE> root netem delay 200ms 50ms loss 0.0%

Contine 'distribution normal'? NU. Nu apare niciun cuvant 'distribution'.

CONSECINTA: fara keyword-ul 'distribution', kernelul aplica distributia UNIFORMA
(sch_netem.c, tabledist cu tabel NULL -> valoare uniforma in [-sigma, +sigma]), desi
man page-ul tc-netem spune "default is Normal" (neconcordanta documentatie<->kernel
cunoscuta). Deci jitter-ul REALIZAT la lat200_jit50 e UNIFORM, nu normal.

IMPACT ASUPRA DRAFTULUI (report-only, TEXT NEEDITAT):
- Sec. 3.2: "delay variation (jitter) uses netem's default normal distribution" -> UNIFORM.
- ec. (1): "x_i ~ N_tab(0,1)" + "N_tab denotes netem's discretized normal table" -> UNIFORM.
- Limitation (6): "normal-distributed jitter" -> "uniform-distributed jitter".
  (Limitation 6 deja admite ca distributia realizata n-a fost verificata pe kernel;
   corectia la uniform o INTARESTE, nu o slabeste.)
Nu am rulat tc. Recomandarea de rewording (formulata, neaplicata) e in sectiunea FRAZE.

================================================================================
## FRAZE GATA DE FOLOSIT (pentru Alexandru; le scrie el cu vocea lui)
================================================================================
- REWORDING 3.2 / ec.(1) / Lim.6 la distributie UNIFORMA (comanda tc a rulat FARA
  'distribution normal', deci datele reflecta uniform -- vezi 1d):
  * Sec. 3.2: "delay variation (jitter) uses netem's uniform distribution: no
    distribution table is loaded, so per the kernel (sch_netem.c) the jitter is drawn
    uniformly, despite the man page's nominal 'Normal' default."
  * ec. (1): "d_i = DELAY + x_i * JITTER,   x_i ~ U(-1, 1)"  (U = uniform pe [-1,1]).
  * Limitation (6): "uniform-distributed jitter".
  (Alternativ, daca preferi modelul normal: incarca explicit `distribution normal` in tc
   si RE-RULEAZA -- dar campania curenta e uniform; nu schimba concluziile, doar forma
   distributiei jitter-ului.)
- Agregare (Sec. 3.3, deja prezenta -- confirmata corecta):
  "condition-level figures aggregate per-repetition summaries" (media pe repetitii a
   loss/mean/p95 per-rep; NU concatenare de esantioane). N raportat: SIL 10, HIL 5.
- Fig. 4 (zecimale exacte pentru caption/text): la ideal, 64 KB pe Wi-Fi, Zenoh pierde
  57.8% (rotunjit 58%), CycloneDDS 0%.
- Caveat 4.1 de restrans: "mean RTT of 11-13 ms at 4 KB" (nu "at 64 B and 4 KB").

## DECIZII care raman la Alexandru
1. Restrange fraza 4.1 la "11-13 ms at 4 KB" (mai sus).
2. Sec. 3.1 versiuni exacte (kernel/ROS/rmw) -- vezi Pas 5 (de rulat de pe masinile tale).
3. Fig. 7 provizorie (etichete RO) -- de regenerat EN la Pas 2/3.
