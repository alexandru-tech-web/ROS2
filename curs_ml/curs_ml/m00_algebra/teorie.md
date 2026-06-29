# M00 -- Algebra liniara aplicata

> ONESTITATE: exemplele pe telemetrie din acest modul folosesc date SINTETICE,
> semanate din campania reala C1/M (vezi `date_sar.py`). Nu sunt masuratori brute;
> servesc invatarii (semnal realist, reproductibil). Inlocuieste-le cu date de
> campanie (N=5, eventual HIL) inainte de orice afirmatie din teza.

## 1. Antet pedagogic

### Obiective de invatare
La finalul modulului poti:
1. **calcula** norme (L1, L2, Linf), produse scalare si proiectii ortogonale de mana si in numpy;
2. **deriva** proiectia ortogonala a unui vector pe o directie si demonstra ca reziduul e perpendicular;
3. **ortonormaliza** un set de vectori cu Gram-Schmidt si **interpreta** rangul ca numar de directii independente;
4. **explica** ce sunt valorile/vectorii proprii ai unei matrice simetrice si SVD-ul (la nivel de intuitie);
5. **aplica** iteratia puterii ca sa gasesti directia principala de variatie a unor feature-uri de telemetrie.

### Prerechizite
- Python + numpy de baza (vectori, matrice, indexare, `@` pentru produs matriceal).
- Matematica de liceu: vectori in plan, sistem de coordonate, radacina patrata.

### Timp si dificultate
- Timp estimat: 120-150 min (citire + exemplu numeric de mana + exercitii).
- Dificultate: 1/3 (modul de fundament; nimic din ML inca, doar limbajul lui).

### Vocabular cheie (trimitere la GLOSAR.md)
- **vector / matrice** -- lista ordonata de numere / tablou dreptunghiular de numere.
- **norma** (`||x||`) -- lungimea unui vector; mai multe variante (L1, L2, Linf).
- **produs scalar** (`<x, y>`) -- masura de aliniere a doi vectori; baza unghiurilor.
- **proiectie ortogonala** -- umbra unui vector pe o directie, cazuta perpendicular.
- **baza ortonormala** -- vectori unitari, perpendiculari doi cate doi.
- **rang** -- numarul de directii liniar independente dintr-o matrice.
- **valoare / vector propriu** -- scalar/directie cu `A v = lambda v` (directie pe care A doar scaleaza).
- **matrice de covarianta** -- tablou simetric al covariatiilor dintre feature-uri (vezi `feature` in GLOSAR).
- **SVD** -- descompunere `A = U S V^T`; generalizeaza valorile proprii la matrice nepatratice.
- **iteratia puterii** -- algoritm iterativ pentru vectorul propriu dominant.

---

## 2. Corp

### 2.1 Intuitie
Tot machine learning-ul vorbeste limba algebrei liniare: datele sunt **matrice**
(randuri = esantioane, coloane = feature-uri), un model liniar e un **produs
scalar**, iar 'cat de mari' / 'cat de aliniate' sunt lucrurile se masoara cu
**norme** si **proiectii**. Cand ai multe feature-uri corelate (ex: latenta,
pierderea, jitterul unei legaturi radio variaza adesea impreuna), structura lor
de co-variatie se citeste in **valorile/vectorii proprii** ai matricei de
covarianta: vectorul propriu dominant e directia in care datele se 'intind' cel
mai mult. Acesta e exact mecanismul pe care se bazeaza PCA (M16).

### 2.2 Formalizare (notatia intregului curs)
- Vectori coloana `x in R^n`; matrice `A in R^{m x n}`; `A^T` = transpusa.
- Produs scalar: `<x, y> = x^T y = sum_i x_i y_i`.
- Norme:
  - `||x||_1   = sum_i |x_i|`            (L1, 'taxi/Manhattan')
  - `||x||_2   = sqrt(sum_i x_i^2)`      (L2, euclidiana)
  - `||x||_inf = max_i |x_i|`            (Linf, sup)
  - relatie utila pe `R^d`: `||x||_inf <= ||x||_2 <= ||x||_1`.
- Proiectia lui `x` pe directia `u`: `proj_u(x) = (<x, u> / <u, u>) u`.
- Reziduu: `r = x - proj_u(x)`, cu proprietatea cheie `<r, u> = 0`.
- Matrice simetrica `A = A^T`; valoare/vector propriu: `A v = lambda v`, `v != 0`.
- Cat Rayleigh (recupereaza valoarea proprie dintr-un vector normat): `lambda = (v^T A v) / (v^T v)`.
- Covarianta coloanelor lui `X in R^{n x d}`: cu `Xc = X - media_coloane`,
  `C = (1/(n-1)) Xc^T Xc` (simetrica, pozitiv semidefinita).
- SVD (intuitie): orice `A = U S V^T`, cu `U, V` ortogonale si `S` diagonala cu
  valori singulare `sigma_i >= 0`. Rangul = numarul de `sigma_i > 0`. Pentru `A`
  simetrica pozitiv semidefinita, valorile singulare coincid cu valorile proprii.

### 2.3 Derivare pas cu pas: proiectia ortogonala
Vrem scalarul `a` astfel incat `p = a u` sa fie cel mai apropiat punct de `x` pe
dreapta generata de `u`. Reziduul `r = x - a u` trebuie sa fie perpendicular pe
`u` (altfel l-am putea micsora):
```
<x - a u, u> = 0
<x, u> - a <u, u> = 0
a = <x, u> / <u, u>
```
Deci `proj_u(x) = (<x, u> / <u, u>) u`, iar prin constructie `<r, u> = 0`.
Consecinta (Pitagora): `||x||^2 = ||proj_u(x)||^2 + ||r||^2`.

### 2.4 Derivare: iteratia puterii (vectorul propriu dominant)
Fie `A` simetrica cu valori proprii `|lambda_1| > |lambda_2| >= ...` si vectori
proprii ortonormali `v_1, ..., v_d`. Orice `v_0` se scrie `v_0 = sum_i c_i v_i`.
Aplicand `A` de `k` ori:
```
A^k v_0 = sum_i c_i lambda_i^k v_i = lambda_1^k ( c_1 v_1 + sum_{i>1} c_i (lambda_i/lambda_1)^k v_i )
```
Cum `|lambda_i/lambda_1| < 1` pentru `i>1`, termenii `i>1` se sting; ramane
directia lui `v_1`. Normand la fiecare pas (`v <- A v / ||A v||`) evitam
explozia/anularea numerica. Valoarea proprie iese din catul Rayleigh.

### 2.5 Algoritm (pseudocod)
```
ITERATIA PUTERII(A simetrica, num_iter, tol):
  v <- vector aleator normat        # ||v|| = 1
  lam_prev <- 0
  repeta de num_iter ori:
    w   <- A v
    v   <- w / ||w||_2              # normare
    lam <- v^T A v                  # cat Rayleigh (v normat)
    daca |lam - lam_prev| < tol: opreste
    lam_prev <- lam
  intoarce (lam, v)
```

```
GRAM-SCHMIDT(coloane a_1..a_n):
  Q <- []
  pentru j = 1..n:
    u <- a_j
    pentru fiecare q deja in Q:
      u <- u - <u, q> q             # scade proiectia pe directiile fixate
    daca ||u|| > eps:
      adauga u/||u|| in Q          # directie noua, ortonormala
  intoarce Q                        # numarul de coloane = rangul
```

### 2.6 EXEMPLU LUCRAT NUMERIC (de mana)
Luam patru puncte 2D (un mini-set de feature-uri telemetrie, latenta vs pierdere,
deja centrate ca media pe coloane sa fie 0):
```
x1 = ( 2,  1)
x2 = ( 1,  1)
x3 = (-1, -1)
x4 = (-2, -1)
```
Matricea `X` (4x2) are media coloanelor `(0, 0)` (verifica: (2+1-1-2)/4 = 0,
(1+1-1-1)/4 = 0), deci `Xc = X`.

**(a) Norme pe `x1 = (2, 1)`**:
- `||x1||_1 = |2| + |1| = 3`
- `||x1||_2 = sqrt(2^2 + 1^2) = sqrt(5) ~ 2.2360679...`
- `||x1||_inf = max(2, 1) = 2`
- coerenta: `2 <= 2.236 <= 3`. Corect.

**(b) Produs scalar si proiectie**: proiectam `x1 = (2,1)` pe `u = (1,1)`.
- `<x1, u> = 2*1 + 1*1 = 3`; `<u, u> = 1 + 1 = 2`.
- `a = 3/2 = 1.5`; `proj_u(x1) = 1.5*(1,1) = (1.5, 1.5)`.
- reziduu `r = (2,1) - (1.5,1.5) = (0.5, -0.5)`.
- verificare ortogonalitate: `<r, u> = 0.5*1 + (-0.5)*1 = 0`. Corect.
- Pitagora: `||x1||^2 = 5`; `||proj||^2 = 1.5^2 + 1.5^2 = 4.5`; `||r||^2 = 0.25 + 0.25 = 0.5`; `4.5 + 0.5 = 5`. Corect.

**(c) Matricea de covarianta** `C = (1/(n-1)) Xc^T Xc`, cu `n = 4`:
```
Xc^T Xc = [ sum x^2 , sum xy ; sum xy , sum y^2 ]
sum x^2 = 4 + 1 + 1 + 4 = 10
sum y^2 = 1 + 1 + 1 + 1 = 4
sum xy  = 2*1 + 1*1 + (-1)*(-1) + (-2)*(-1) = 2 + 1 + 1 + 2 = 6
C = (1/3) * [10, 6 ; 6, 4] = [ 3.3333, 2.0 ; 2.0, 1.3333 ]
```

**(d) Valori/vectori proprii ai `C`** (matrice 2x2 simetrica). Rezolvam
`det(C - lambda I) = 0`. Cu `M = Xc^T Xc = [10, 6; 6, 4]` (proportionala cu `C`,
acelasi vector propriu), avem urma `tr = 14` si determinant `det = 10*4 - 6*6 = 4`:
```
lambda^2 - 14 lambda + 4 = 0
lambda = (14 +- sqrt(196 - 16)) / 2 = (14 +- sqrt(180)) / 2 = 7 +- sqrt(45)
sqrt(45) ~ 6.7082039
lambda_max(M) ~ 13.7082 ;  lambda_min(M) ~ 0.2918
```
Impartind la `(n-1) = 3` (pentru `C`): `lambda_max(C) ~ 4.5694`, `lambda_min(C) ~ 0.0973`.
Vectorul propriu dominant rezolva `(M - lambda_max I) v = 0`:
```
(10 - 13.7082) v_x + 6 v_y = 0  ->  -3.7082 v_x + 6 v_y = 0  ->  v_y = 0.61803 v_x
v ~ (1, 0.618), normat: v ~ (0.851, 0.526)
```
Directia dominanta `~ (0.851, 0.526)`: feature-urile cresc IMPREUNA (semn comun),
adica latenta si pierderea co-variaza pozitiv in acest mini-set. Fractia de
varianta pe axa dominanta: `13.708 / (13.708 + 0.292) = 13.708 / 14 ~ 0.979`,
adica ~98% din variatie sta pe o singura directie.

**(e) Verificare cu iteratia puterii (de mana, 2 pasi pe `M`)**, pornind din `v0 = (1, 0)`:
```
w = M v0 = (10, 6);  ||w|| = sqrt(136) ~ 11.6619;  v1 = (0.8575, 0.5145)
w = M v1 = (10*0.8575 + 6*0.5145, 6*0.8575 + 4*0.5145) = (11.662, 7.203)
||w|| ~ 13.7095;  v2 = (0.8507, 0.5256)
```
Dupa doi pasi `v2 ~ (0.851, 0.526)` -- coincide deja cu vectorul propriu calculat
analitic, iar `||w|| ~ 13.71` aproximeaza `lambda_max`. Asta valideaza algoritmul
implementat in `algebra_liniara_core.power_iteration`.

### 2.7 Vizualizare (referinta la demo_sil)
`demo_sil.py` produce (daca matplotlib exista):
- `fig_covarianta.png` -- heatmap-ul matricei de covarianta a feature-urilor de
  telemetrie standardizate (`loss_pct`, `base_lat_ms`, `jitter_ms`, `distance_m`,
  `rtt_ms`); culorile arata ce feature-uri co-variaza.
- `fig_axa_dominanta.png` -- incarcarile (loadings) vectorului propriu dominant pe
  fiecare feature: directia principala de variatie a telemetriei.
Daca matplotlib lipseste, demo-ul tipareste aceleasi numere in consola.

### 2.8 Capcane
- **Norma gresita pentru context**: L2 penalizeaza outlierii mai tare decat L1;
  alegerea normei schimba rezultatul (vezi M06 regularizare L1 vs L2).
- **Proiectie cu `u` ne-normat**: nu uita numitorul `<u, u>`; daca `u` e deja
  unitar, `proj = <x, u> u`, dar in general trebuie impartit.
- **Iteratia puterii esueaza** daca `|lambda_1| = |lambda_2|` (valori proprii
  egale ca modul) sau daca `v0` e ortogonal pe `v1` (probabilitate 0 cu `v0` aleator).
- **Scale diferite**: covarianta pe feature-uri ne-standardizate e dominata de
  feature-ul cu unitatile cele mai mari (ms vs procente). Standardizeaza intai
  (vezi `utils.standardize`) daca vrei structura de CORELATIE, nu de covarianta bruta.
- **Semnul vectorului propriu** nu e unic: `v` si `-v` sunt ambele valide; compara
  directii (`|cos|`), nu componente cu semn.

### 2.9 De ce conteaza pentru teza
- **Notatie**: acest modul fixeaza notatia (vectori, norme, `<.,.>`, covarianta)
  reutilizata in tot cursul si in capitolele de modelare ale tezei.
- **Structura de covarianta a telemetriei**: feature-urile de legatura (RTT,
  pierdere, jitter, distanta) sunt corelate; intelegerea axelor de variatie (a)
  ghideaza selectia de feature pentru selectorul de middleware (C1/C3) si (b) e
  fundamentul reducerii de dimensionalitate (M16) folosita la vizualizarea
  conditiilor de retea.

---

## 3. Inchidere

### Checklist de stapanire (bifeaza daca poti...)
- [ ] calcula L1, L2, Linf pentru un vector dat si verifica `inf <= 2 <= 1`;
- [ ] proiecta un vector pe o directie si arata ca reziduul e ortogonal (`<r,u>=0`);
- [ ] ortonormaliza doua-trei coloane cu Gram-Schmidt si spune care e rangul;
- [ ] explica de ce iteratia puterii converge la vectorul propriu dominant;
- [ ] construi matricea de covarianta a unor feature-uri si interpreta axa dominanta;
- [ ] explica intuitia SVD (`A = U S V^T`) si legatura cu valorile proprii.

### Trimiteri la BIBLIOGRAFIE.md
- Deisenroth, Faisal, Ong -- *Mathematics for Machine Learning* (MML), cap. 2-4
  (algebra liniara, geometrie analitica, descompuneri matriceale). Sursa principala M00.
- Hastie, Tibshirani, Friedman -- *ESL*, cap. 14 (covarianta, PCA) pentru legatura cu M16.
