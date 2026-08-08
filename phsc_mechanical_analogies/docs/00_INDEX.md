# PHSC -- Catalog artefacte

Generat: 2026-08-08. Toate fisierele sunt COPII; originalele nu au fost
mutate sau sterse.

**Rezumat: 8 figuri vectoriale (PDF+PNG) + 2 raster, 8 fisiere de date,
14 rapoarte. 42 fisiere, 1.7 MB.**

Toate rezultatele provin din SIMULARE. Nicio validare pe hardware, niciun
operator uman.

---

## 1. Grafice

### 1a. Figuri vectoriale pentru articol (`01_grafice/vectorial/`)

Opt figuri, fiecare in **PDF (vectorial, pentru articol)** si **PNG 300 dpi
(previzualizare)**. Generate de `_genereaza_figuri.py`, inclus alaturi.

Stil: coloana IEEE (3.5 / 7.2 inch), font serif, grila recesiva. Culorile sunt
primele trei sloturi dintr-o paleta categoriala validata, atribuite in ordine
fixa; fiecare serie are IN PLUS un stil de linie si un marker distinct, deci
identitatea nu depinde de culoare (daltonism, tiparire alb-negru).

| Fisier | Ce arata | Sursa datelor |
|---|---|---|
| `fig01_ablation_tau100` | Ablatia in timp la tau=100 ms: theta(t) sus, comanda u(t) jos. Saturatia predictorului naiv la +100 N este mecanismul esecului. | simulare re-rulata |
| `fig02_monte_carlo_praguri` | P(stabil) vs latenta, N=50 perechi, banda Wilson 95%; pragurile 55 / 69 / 265 ms adnotate | `praguri_stabilitate_N50.csv` |
| `fig03_mcnemar_contingency` | Tabelul de contingenta complet, ca bare stivuite. Segmentul "naivul a AJUTAT" lipseste la toate latentele. | `mcnemar_perechi_N50.csv` |
| `fig04_estimator_error_dist` | Urmarirea latentei de catre EWMA (stanga) si distributia erorii fata de pragul critic +/-20% (dreapta) | simulare re-rulata |
| `fig05_mpc_benchmark` | Timp de solve vs orizont, ambele moduri de constrangere, fata de bugetul de 50 ms | masurat la generare |
| `fig06_phase_portrait` | Portret de faza cu lupa pe origine (fara lupa, traiectoria Smith se reduce la un punct) | simulare re-rulata |
| `fig07_system_architecture` | Diagrama de blocuri a lantului PHSC | desenata |
| `fig08_cartpole_schematic` | Schema cart-pole cu conventia de unghi | desenata |

Trei figuri au fost refacute dupa ce le-am privit: `fig03` avea o bara de
valoare zero, deci celula cea mai importanta era invizibila (acum e tabel de
contingenta stivuit); `fig06` ascundea complet seria Smith la scara intreaga
(acum are lupa); `fig07` avea etichetele suprapuse peste blocuri.

### 1b. Figuri raster initiale (`01_grafice/raster/`)

Cele doua PNG produse in timpul sesiunii, pastrate ca referinta. Sunt
inlocuite de variantele vectoriale de mai sus.

| Fisier | Marime |
|---|---|
| `ablatie_tau100ms_none_naiv_smith.png` | 86 KB |
| `monte_carlo_P_stabil_vs_tau_N50.png` | 130 KB |

Fiecare era duplicata in `~/phsc_sim/` si `~/phsc_docs/`; verificat cu
`md5sum` ca duplicatele sunt identice bit cu bit, deci am copiat cate una.

### Ce am gasit dar NU am inclus

Cautarea a returnat 200+ imagini in `~/Pictures/Screenshots/`, plus 8 figuri
si un PDF in `~/Downloads/OLD_/` (`fig_rtt_p95_en.png`, `Articol_C1_v4.pdf`,
s.a.).

**Niciuna nu este PHSC.** Sunt artefacte C1 (benchmark rmw sub netem) si
capturi anterioare inceperii PHSC. Nu am gasit nimic in `~/.ros/` sau
`~/.gazebo/`: Gazebo nu a rulat in sesiunile PHSC.

---

## 2. Date tabelare

Nu existau fisiere JSON sau CSV. Existau doar doua iesiri brute de consola.
Am pastrat brutul si am generat CSV din el cu `_genereaza_csv.py` -- parsare,
nu recalculare si nu transcriere manuala.

| Fisier | Sursa | Continut | Marime |
|---|---|---|---|
| `02_date_tabelare/monte_carlo/monte_carlo_iesire_bruta_N50.txt` | `~/phsc_sim/mc_out.txt` | Iesirea integrala a `monte_carlo_stability.py 50`: 12 valori de tau x 3 conditii, praguri, comparatie pe perechi. Durata rularii: 1119 s. | 3 KB |
| `02_date_tabelare/monte_carlo/praguri_stabilitate_N50.csv` | derivat | 36 randuri: `tau_ms, conditie, p_stabil, wilson_95_jos, wilson_95_sus, n_incercari`. Gata de incarcat intr-un tabel de articol. | 1 KB |
| `02_date_tabelare/mcnemar/mcnemar_iesire_bruta_N50.txt` | `~/phsc_sim/mcnemar_out.txt` | Iesirea `mcnemar_ablation.py`: tabelul de contingenta si p exact. | 927 B |
| `02_date_tabelare/mcnemar/mcnemar_perechi_N50.csv` | derivat | 3 randuri: `tau_ms, ambele_stabile, doar_fara_compensare_b, doar_naiv_c, niciunul, p_o_coada`. | 167 B |
| `02_date_tabelare/benchmark/benchmark_iesire_bruta.txt` | rulare noua | `benchmark_mpc.py`, rulat acum ca sa existe un artefact real (iesirea originala fusese doar in consola). | 1 KB |
| `02_date_tabelare/benchmark/timp_solve_mpc.csv` | derivat | 5 randuri: `orizont_N, mediana_ms, min_ms, max_ms, rata_hz, incape_in_buget`. | 253 B |
| `02_date_tabelare/benchmark/timp_solve_ambele_moduri.csv` | masurat la generarea figurilor | 5 randuri: `orizont_N, fara_constrangere_ms, cu_theta_max_ms`. Ambele serii masurate in aceeasi rulare, deci comparabile intre ele. **Aceasta e varianta de folosit in articol**, nu `timp_solve_mpc.csv`. | 120 B |
| `02_date_tabelare/_genereaza_csv.py` | scris acum | Regenereaza cele trei CSV din fisierele brute. Ruleaza-l daca refaci simularile. | 4 KB |

### ATENTIE: benchmark-ul nu se potriveste cu RESULTS.md, si e corect asa

`timp_solve_mpc.csv` da **971.7 ms** pentru N=20, in timp ce `RESULTS.md`
sec. 2 raporteaza **519 ms**. Nu e o contradictie:

- 519 ms = fara constrangerea de stare `theta_max`
- 971.7 ms = cu constrangerea impusa (`theta_mode='hard'`)

Intre timp valoarea implicita a devenit `hard`, deci rularea noua o include.
`RESULTS.md` listeaza ambele coloane: 519 ms fara, 982 ms cu. Cifra noua
(971.7 ms) cade in aceeasi zona ca 982 ms, deci masuratorile sunt coerente.

Daca folosesti CSV-ul intr-un articol, spune care varianta e: cu sau fara
constrangere. Sunt doua sisteme diferite, nu doua masuratori ale aceluiasi.

---

## 3. Rapoarte

| Fisier | Sursa | Continut |
|---|---|---|
| `METHODOLOGY.md` | `~/phsc_docs/` | Capitol metodologic: derivarea Euler-Lagrange, linearizarea, cele trei strategii de predictie, mecanismul esecului, estimarea latentei, garzile, alegerea arhitecturii, limitari |
| `RESULTS.md` | `~/phsc_docs/` | Toate tabelele numerice cu sursa fiecarei cifre. **Documentul de referinta pentru orice cifra citata.** |
| `ARTICLE_DRAFT.md` | `~/phsc_docs/` | Schelet de articol cu abstract completat. Referintele sunt marcate `[DE VERIFICAT]` -- nu sunt bibliografie validata |
| `PHSC_POSITIONING.md` | `~/phsc_docs/` | Incadrarea in teza, conditii, si cele doua rezerve (originalitate neverificata independent; lipsa hardware si operator) |
| `UR3_MIGRATION.md` | `~/phsc_docs/` | De ce nu exista cod pentru UR3 si ce preconditii de identificare experimentala sunt necesare |
| `FINAL_REPORT.md` | `~/phsc_docs/` | Raport final, stare ON HOLD, conditii de reactivare, integrarea reala in C1-C4 |
| `ARCHITECTURE.md` | repo, tag `v1.0-reproducible` | Decizia de arhitectura: LQR+Smith real-time vs NMPC offline, cu cifrele care o sustin |
| `studies_README.md` | repo, tag `v1.0-reproducible` | Cum se ruleaza scripturile de reproductibilitate |
| `RAPORT_PHSC_RUNDA1.md` ... `RUNDA6.md` | `~/phsc_sim/` | Jurnalul celor sase runde de integrare si verificare: ce s-a gasit, ce s-a masurat, ce s-a corectat |

Cele doua fisiere din repo au fost extrase cu `git show <tag>:<cale>`, fara
`checkout`, deci starea depozitului nu a fost atinsa.

---

## 4. Ce NU se afla in acest folder

**Scripturile de simulare.** Sunt cod si au un loc mai bun: depozitul git.

| ce | unde |
|---|---|
| `monte_carlo_stability.py`, `mcnemar_ablation.py` | repo, ramura `phsc-v1-simulation`, tag **`v1.0-reproducible`**, in `phsc_mechanical_analogies/studies/` |
| `ablation_study.py`, `robustness_smith.py`, `closed_loop_compare.py`, `benchmark_mpc.py`, `lqr_sanity.py`, `test_smith_variable.py`, `test_mpc.py` | `~/phsc_sim/` (neversionate) |
| codul PHSC (4 pachete ROS 2) | repo, tag `v1.0-final` / `v1.0-reproducible` |

Daca trimiti acest folder unui colaborator si articolul revendica
reproductibilitate, trimite si tag-ul `v1.0-reproducible` -- figurile si
tabelele de aici nu pot fi regenerate fara el.

**Scripturile din `~/phsc_sim/` care nu sunt in git** (ablation_study.py in
special, cel care produce figura principala) sunt singurul punct fragil al
arhivei: exista intr-un singur loc, neversionat.

---

## 5. Cifrele principale, pentru orientare rapida

| rezultat | valoare | fisier sursa |
|---|---|---|
| prag stabilitate, fara compensare | 69 ms (P=50%) | `praguri_stabilitate_N50.csv` |
| prag stabilitate, predictie naiva | **55 ms** (P=50%) | idem |
| prag stabilitate, Smith cu buffer | **265 ms** (P=50%) | idem |
| naiv vs fara compensare | `c=0`, p < 2.4e-04 | `mcnemar_perechi_N50.csv` |
| theta rms, tau variabil 50-150 ms | 1.31 grade | `RESULTS.md` sec. 5 |
| eroare estimator tau | +1.06% medie, 14.41% p95 | `RESULTS.md` sec. 6 |
| rata reala nod MPC | 20.03 Hz | `RESULTS.md` sec. 2 |

Rezultatul central: **predictia cu ipoteza gresita despre intrare este mai
rea decat lipsa oricarei compensari.** Pe 150 de incercari perechi, predictia
naiva nu a salvat niciodata o incercare pe care lipsa compensarii o pierdea;
a stricat 62 dintre ele.
