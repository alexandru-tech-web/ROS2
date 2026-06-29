# M04 -- Date si feature engineering

## Antet pedagogic

### Obiective de invatare
La finalul modulului poti:
- sa EXPLICI ce e scurgerea de date si sa CONSTRUIESTI o preprocesare care o evita
  (statistici invatate pe TRAIN, aplicate pe TEST);
- sa ENCODEZI variabile categoriale corect (one-hot pentru nominale, ordinal
  pentru cele cu ordine naturala);
- sa IMPUTEZI valori lipsa cu media de pe train, fara scurgere;
- sa GENEREZI feature-uri polinomiale si sa CALCULEZI numarul de coloane rezultat;
- sa DETECTEZI outlieri cu regula IQR (Tukey) si sa interpretezi rezultatul.

### Prerechizite
- M00 (algebra: matrice, produs), M01 (medii, percentile, distributii).
- numpy de baza; notiunea de train/test din M03.

### Timp si dificultate
- Timp estimat: 90-120 min (citire + exercitii).
- Dificultate: 2 / 3. Conceptual usor, dar capcanele (scurgerea!) sunt subtile.

### Vocabular cheie (vezi GLOSAR.md)
- feature (trasatura) -- variabila de intrare a modelului.
- one-hot encoding -- categorie nominala -> vector indicator cu un singur 1.
- encodare ordinala -- categorie cu ordine -> intreg, dupa o ordine impusa.
- imputare -- inlocuirea valorilor lipsa (aici: cu media coloanei).
- standardizare (z-score) -- (x - medie) / abatere, pe coloane.
- feature polinomial -- termeni de tip x_i, x_i^2, x_i*x_j etc.
- outlier -- valoare extrema fata de masa datelor (aici: regula IQR).
- data leakage (scurgere de date) -- informatie din test ajunge in antrenare.
- Pipeline / ColumnTransformer -- compunere ordonata a pasilor de preprocesare.

ONESTITATE: datele folosite in demo si exercitii sunt SINTETICE, semanate din
campania reala C1 (p95 RTT / pierdere DDS vs Zenoh) si modelul de canal M. NU
sunt masuratori reale -- servesc invatarii, sunt reproductibile (seed fix).

---

## Corp

### 1. Intuitie

Un model nu vede 'middleware = Zenoh' sau 'latenta lipsa'; vede numere. Feature
engineering e traducerea telemetriei brute intr-o matrice numerica X pe care
modelul o poate consuma, FARA sa-i dam din greseala raspunsuri pe care nu le-ar
avea in realitate. Cele trei intrebari practice:
- cum reprezint o categorie (DDS / Zenoh)?  -> one-hot sau ordinal;
- ce fac cu o masuratoare lipsa?            -> imputare;
- cum aduc coloanele la scari comparabile?  -> standardizare.
Si o regula care le leaga pe toate: orice statistica (medie, abatere, vocabular
de categorii) se INVATA pe TRAIN si se APLICA pe TEST. Altfel apare scurgerea.

### 2. Formalizare

Fie X o matrice (n, p): n esantioane, p feature-uri. Notam X_tr / X_te impartirea
in train / test.

One-hot pe o coloana categoriala c cu vocabular {v_1, ..., v_K}: produce o
matrice indicator B in {0,1}^{n x K}, cu B[i, j] = 1 daca c_i = v_j, altfel 0.
Fiecare rand are exact un 1 (suma pe rand = 1). Pentru a evita coliniaritatea
perfecta cu coloana de bias (1 = suma coloanelor one-hot) se poate folosi
drop_first (K-1 coloane).

Encodare ordinala: dat un sir ordonat (v_1 < v_2 < ... < v_K), maparea este
phi(v_j) = j-1. Ordinea NU se deduce din date -- o impune domeniul.

Imputare cu media (fara scurgere): pentru fiecare coloana j,
  mu_j = media valorilor NON-lipsa din X_tr[:, j].
Apoi orice NaN (in train SAU test) se inlocuieste cu mu_j. Cheia: mu_j vine DOAR
din train.

Standardizare (z-score): z_j = (x_j - mu_j) / sigma_j, cu mu_j, sigma_j calculate
pe TRAIN (vezi utils.standardize). Pe test se folosesc ACELEASI mu_j, sigma_j.

Feature-uri polinomiale de grad d: pentru fiecare grad t de la 1 la d, toate
monoamele de forma produsul x_{i_1} * ... * x_{i_t} cu i_1 <= ... <= i_t (combinatii
cu repetitie). Numarul de coloane (fara bias) este
  N(p, d) = sum_{t=1}^{d} C(p + t - 1, t).
Pentru d = 2 asta da N = p + p(p+1)/2 = p (liniar) + p (patrate) + C(p,2) (interactiuni).

Detectie outlieri (IQR, Tukey): cu Q1, Q3 = percentilele 25 si 75 si IQR = Q3 - Q1,
un punct x e outlier daca
  x < Q1 - k*IQR   sau   x > Q3 + k*IQR,    cu k = 1.5 (uzual).

### 3. Derivare pas cu pas: numarul de coloane polinomiale

De ce N(p, d) = sum_{t=1}^{d} C(p + t - 1, t)?

Un monom de grad t se alege ca un multiset de t indici din {1, ..., p} (repetitia
permisa: x_i poate aparea de mai multe ori, dand puteri). Numarul de multiseturi
de marime t dintr-un set de p elemente este combinarea cu repetitie
  C(p + t - 1, t).
Insumand pe toate gradele t de la 1 la d (excludem t=0, care e biasul, daca
include_bias=False) obtinem formula. Exemplu p=2, d=2:
  t=1: C(2,1) = 2  -> x1, x2
  t=2: C(3,2) = 3  -> x1^2, x1*x2, x2^2
  Total = 5.

### 4. Algoritm (pseudocod) -- pipeline fara scurgere

```
intrare: df cu o coloana categoriala 'cat' si numerice 'num', tinta y
1. imparte indicii in TRAIN / TEST (determinist, seed fix)
2. # encoder categoric
   cats <- categorii unice din cat[TRAIN]            # vocabular doar pe TRAIN
   B_tr <- one_hot(cat[TRAIN], cats)
   B_te <- one_hot(cat[TEST],  cats)                 # acelasi vocabular
3. # imputare numerica
   mu_imp <- media_ignora_NaN(num[TRAIN])            # doar pe TRAIN
   num_tr <- umple_NaN(num[TRAIN], mu_imp)
   num_te <- umple_NaN(num[TEST],  mu_imp)
4. # standardizare
   (Z_tr, Z_te, mu, sigma) <- standardize(num_tr, num_te)   # stat pe TRAIN
5. F_tr <- [B_tr | Z_tr] ;  F_te <- [B_te | Z_te]
iesire: F_tr, F_te (si encoderul, ca sa procesezi date noi identic)
```

### 5. EXEMPLU LUCRAT NUMERIC (obligatoriu)

Patru ferestre de telemetrie, o coloana categoriala (middleware) si una numerica
(p95 in ms, cu o valoare lipsa). Split: primele 3 = TRAIN, ultima = TEST.

| i | middleware | p95_ms | set   |
|---|------------|--------|-------|
| 1 | DDS        | 100    | TRAIN |
| 2 | Zenoh      | 200    | TRAIN |
| 3 | DDS        | NaN    | TRAIN |
| 4 | Zenoh      | 300    | TEST  |

Pas 1 -- one-hot pe middleware. Vocabular din TRAIN (sortat): {DDS, Zenoh}.
  rand 1 (DDS)   -> [1, 0]
  rand 2 (Zenoh) -> [0, 1]
  rand 3 (DDS)   -> [1, 0]
  rand 4 (Zenoh, TEST) -> [0, 1]   (acelasi vocabular).
Fiecare rand are exact un 1 -- proprietatea definitorie a one-hot.

Pas 2 -- imputare cu media de pe TRAIN. Valori non-lipsa pe TRAIN: {100, 200}.
  mu_imp = (100 + 200) / 2 = 150.
  rand 3 (NaN) -> 150.
NaN-ul se umple cu 150, NU cu media incluzand testul. Daca am fi inclus si 300,
am fi avut o medie diferita -- aceea ar fi fost scurgere.

Pas 3 -- standardizare cu stat de pe TRAIN. Coloana p95 dupa imputare pe TRAIN:
{100, 200, 150}.
  mu = (100 + 200 + 150) / 3 = 150.
  varianta (populatie) = [(100-150)^2 + (200-150)^2 + (150-150)^2] / 3
                       = [2500 + 2500 + 0] / 3 = 5000/3 = 1666.67.
  sigma = sqrt(1666.67) = 40.825.
  z(TRAIN): (100-150)/40.825 = -1.2247 ; (200-150)/40.825 = +1.2247 ; (150-150)/... = 0.
  z(TEST=300): (300 - 150) / 40.825 = +3.674.
Observa: media z pe TRAIN este 0 (proprietate verificata in demo), iar TESTUL
foloseste mu=150, sigma=40.825 invatate pe TRAIN -- valoarea 300 iese la +3.67
sigma (departe), exact pentru ca testul nu a participat la calculul mediei.

Matricea finala de feature (one-hot | z):
  rand 1: [1, 0, -1.2247]
  rand 2: [0, 1, +1.2247]
  rand 3: [1, 0,  0.0000]   (TRAIN)
  rand 4: [0, 1, +3.6742]   (TEST)

Pas 4 (verificare IQR pe p95 brut {100, 200, 300}): Q1=150, Q3=250, IQR=100,
prag sus = 250 + 1.5*100 = 400; niciun punct > 400 -> niciun outlier aici (set mic).

### 6. Vizualizare (din demo_sil.py)

`demo_sil.py` produce (daca matplotlib exista):
- `fig_rtt_iqr.png` -- histograma rtt_ms cu pragul superior IQR marcat; arata
  coada lunga (degradarea genereaza RTT extrem) si ce taie regula Tukey.
- `fig_feature_matrix.png` -- heatmap al matricei de feature (one-hot middleware
  + numerice standardizate): vizual, coloanele one-hot sunt 0/1, cele z sunt
  centrate in jurul lui 0.

### 7. Capcane

- SCURGEREA prin standardizare/imputare invatata pe tot setul (inclusiv test) --
  greseala numarul unu. Statistici DOAR pe train (PRINCIPII_TRANSVERSALE sec.1).
- One-hot pe categorii cu cardinalitate mare -> matrice uriasa si rara; ia in
  calcul gruparea sau alte encodari.
- Encodare ordinala pe o nominala (ex: a da 0,1 lui DDS/Zenoh) introduce o ordine
  FALSA pe care modelul o exploateaza gresit. Foloseste one-hot pentru nominale.
- Categorii nevazute la fit care apar la test: aici dau rand 0 (semnal explicit);
  decizia trebuie constienta, nu accidentala.
- Polinoamele explodeaza: N(p,d) creste rapid -> coliniaritate si supra-invatare;
  standardizeaza inainte si pereche cu regularizare (M06).
- IQR presupune o distributie rezonabil unimodala; pe distributii puternic
  asimetrice (RTT!) pragul taie legitim coada -- nu sterge orbeste 'outlierii'.

### 8. De ce conteaza pentru teza

Telemetria C1 (RTT, pierdere, jitter, distanta) este exact tipul de date care
cere aceasta pregatire inainte de orice model (selectorul link-aware C3,
predictorul de uzabilitate M08/M09). Middleware-ul (DDS/Zenoh) e o categorie
nominala -> one-hot. RTT are cozi lungi (cozi reale sub degradare) -> outlierii
IQR si transformarile conteaza. Si pentru ca datele mele sunt corelate (repetitii
ale aceleiasi conditii), scurgerea e un risc real: vezi nota LOCO din CLAUDE.md
(split aleator scurge informatie intre repetitii). Acest modul stabileste igiena
pe care se sprijina toate modulele de modelare care urmeaza.

---

## Inchidere

### Checklist de stapanire (bifeaza daca poti...)
- [ ] explici de ce one-hot are exact un 1 per rand si cand folosesti drop_first;
- [ ] argumentezi cand alegi ordinal vs one-hot (ordine naturala vs nominal);
- [ ] imputezi valori lipsa cu media de pe TRAIN si arati ca NU e scurgere;
- [ ] calculezi numarul de coloane ale unui polinom de grad d pe p feature-uri;
- [ ] aplici regula IQR si interpretezi outlierii (mai ales pe RTT cu coada);
- [ ] construiesti un pipeline (encoder + scaler) care invata pe train, aplica pe test.

### Trimiteri la BIBLIOGRAFIE
- Geron, Hands-On ML, cap. 2 (pipeline de preprocesare, ColumnTransformer).
- ISL, cap. 2 (notiuni de baza despre date si feature-uri).
- PRINCIPII_TRANSVERSALE.md sec.1 (scurgerea de date) -- reluat aici cu exemplu.
