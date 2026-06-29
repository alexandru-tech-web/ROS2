# M17 -- Cuantificarea incertitudinii

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa derivezi posteriorul gaussian al regresiei liniare bayesiene (covarianta S si
  media m) si varianta predictiva intr-un punct;
- sa distingi un interval de PREDICTIE (acopera o observatie noua) de unul de
  INCREDERE (acopera media), si sa stii cand folosesti fiecare;
- sa construiesti intervale prin bootstrap (reesantionare) si prin conformal
  prediction split (acoperire garantata);
- sa raportezi o predictie CU bara de eroare si sa-i masori acoperirea empirica.

Prerechizite: M01 (probabilitati, gaussiana, condi-tionare), M05 (regresie liniara,
ecuatii normale), M07 (evaluare, acoperire empirica, scurgere de date). Timp estimat:
3-4 h. Dificultate: 3/3.

Vocabular cheie (vezi GLOSAR.md): posterior, prior, verosimilitate, covarianta
posterioara, varianta predictiva, interval de predictie, interval de incredere,
bootstrap, conformal prediction, acoperire (coverage), nivel de incredere, cuantila.

## 1. Intuitie

La N = 5 o predictie fara bara de eroare e inutila. Daca modelul spune ca RTT-ul
median al lui Zenoh sub o conditie e 690 ms si al lui DDS e 1056 ms, intrebarea care
conteaza pentru teza NU e 'care e mai mic', ci 'e diferenta reala sau e zgomot de la
cinci repetitii?'. Raspunsul cere o masura a incertitudinii: un interval in jurul
predictiei. Un model care da doar un numar te lasa sa confunzi zgomotul cu semnalul.

Exista doua surse de incertitudine. Una vine din faptul ca am putine date, deci nu
stiu exact parametrii (incertitudine pe w; numita epistemica -- se reduce cu mai
multe date). Cealalta vine din zgomotul intrinsec al masuratorii (o observatie noua
e oricum imprastiata in jurul mediei; numita aleatorica -- nu dispare oricat de
multe date ai). Un interval de PREDICTIE le include pe amandoua; unul de INCREDERE
doar pe prima.

## 2. Formalizare

Model liniar cu zgomot gaussian:

    y = phi(x)^T w + eps,   eps ~ N(0, sig2)

unde phi(x) e vectorul de feature-uri (cu un 1 la inceput pentru intercept). In loc
sa cautam UN singur w (ca la OLS in M05), tratam w ca o variabila aleatoare cu un
prior gaussian:

    prior:  w ~ N(0, (1/lam) I)

lam e precizia prior-ului (lam mare = prior strans in jurul lui 0 = regularizare
puternica; lam mic = prior slab, larg). Verosimilitatea datelor, cu Phi matricea de
design (randuri phi(x_i)^T) si y vectorul tintelor:

    p(y | w) = N(y ; Phi w, sig2 I)

Prin Bayes, posteriorul p(w | y) este tot gaussian (priorul gaussian e conjugat cu
verosimilitatea gaussiana).

## 3. Derivare: regresia liniara bayesiana

Posteriorul e proportional cu prior x verosimilitate. In logaritmi (ignoram
constantele in raport cu w):

    log p(w|y) = -1/(2 sig2) (y - Phi w)^T (y - Phi w) - (lam/2) w^T w + const

Desfasuram termenul patratic in w:

    = -1/2 [ w^T ( lam I + (1/sig2) Phi^T Phi ) w - (2/sig2) w^T Phi^T y ] + const

O gaussiana in w are forma -1/2 (w - m)^T S^-1 (w - m), adica
-1/2 [ w^T S^-1 w - 2 w^T S^-1 m ] + const. Identificam termenii:

- termenul patratic da inversa covariantei (precizia posterioara):

      S^-1 = lam I + (1/sig2) Phi^T Phi
      => S = ( lam I + (1/sig2) Phi^T Phi )^-1

- termenul liniar da media: S^-1 m = (1/sig2) Phi^T y, deci

      m = (1/sig2) S Phi^T y

Asadar posteriorul este:

    w | y ~ N( m, S ),   S = (lam I + (1/sig2) Phi^T Phi)^-1,   m = (1/sig2) S Phi^T y

Doua verificari de bun-simt:
- cand lam -> 0 (prior infinit de slab), S^-1 -> (1/sig2) Phi^T Phi si
  m -> (Phi^T Phi)^-1 Phi^T y = solutia OLS. Bayesian cu prior slab REPRODUCE OLS.
- cand adaugi date, Phi^T Phi creste, deci S^-1 creste, deci S SCADE (in sens de
  matrice pozitiv definita): posteriorul se CONTRACTA. Urma lui S scade -> incertitudine
  mai mica pe parametri. Asta verifica selftest-ul nucleului.

### Varianta predictiva

Pentru un punct nou phi* = phi(x*) vrem distributia unei observatii noi
y* = phi*^T w + eps. Doua surse de varianta, independente:
- incertitudinea pe w: Var(phi*^T w) = phi*^T S phi* (propagarea unei gaussiene
  printr-o functie liniara);
- zgomotul observatiei: Var(eps) = sig2.

Deci media si varianta predictiva sunt:

    medie(x*)    = phi*^T m
    var_pred(x*) = sig2 + phi*^T S phi*

Radacina patrata da abaterea standard predictiva, iar intervalul de predictie la
nivel `level` este  medie +/- z * sqrt(var_pred), cu z = cuantila normalei standard
la 0.5 + level/2 (ex. z = 1.645 la 90%, z = 1.96 la 95%).

## 4. Interval de PREDICTIE vs interval de INCREDERE

Distinctia e centrala (si o capcana clasica):
- interval de INCREDERE pe medie: cat de bine cunosc valoarea ASTEPTATA E[y|x*].
  Latimea ~ phi*^T S phi* (doar incertitudinea pe parametri). Se ingusteaza spre 0
  cand N creste.
- interval de PREDICTIE pe o observatie noua: unde va cadea un y* MASURAT.
  Latimea ~ sig2 + phi*^T S phi* (parametri + zgomot). NU se ingusteaza sub un prag
  fixat de sig2, oricat de multe date ai -- masuratoarea ramane zgomotoasa.

Pentru teza: daca vreau sa raportez RTT-ul mediu al unei conditii, vreau interval de
INCREDERE. Daca vreau sa garantez ca urmatorul pachet va sosi in X ms, vreau interval
de PREDICTIE (mai larg). A confunda cele doua subraporteaza riscul.

## 5. Bootstrap

Cand nu vrei ipoteza gaussiana, bootstrap-ul estimeaza incertitudinea pe parametri
prin reesantionare: din cele n puncte de antrenare extragi, cu inlocuire, n puncte (un
'esantion bootstrap'), reantrenezi modelul, prezici in punctul tinta. Repeti de B ori
(ex. B = 200) si iei cuantilele empirice (de ex. 5% si 95%) ale norului de predictii.

Bootstrap-ul surprinde varietatea predictiilor data de varietatea seturilor de
antrenare -- adica incertitudinea pe MEDIE (interval de INCREDERE). NU include zgomotul
unei observatii noi, deci e mai ingust decat un interval de predictie. E neparametric
si simplu, dar costa B reantrenari si subestimeaza la N foarte mic.

## 6. Conformal prediction split (intro)

Bayesian-ul si gaussiana presupun ca modelul si forma zgomotului sunt corecte. Conformal
prediction da o garantie de acoperire FARA aceste ipoteze (cere doar schimbabilitatea
datelor -- mai slab decat i.i.d.). Varianta 'split' (cea mai simpla):

1. imparte datele de antrenare in TRAIN propriu-zis si CALIBRARE;
2. antreneaza modelul pe TRAIN;
3. calculeaza scorurile de neconformitate pe CALIBRARE: r_i = |y_i - pred(x_i)|;
4. ia cuantila ajustata: q = al k-lea cel mai mic reziduu, cu
   k = ceil((n_cal + 1)(1 - alpha));
5. pentru un punct nou: interval = pred(x*) +/- q.

Garantia (marginala, esantion finit): P(y_nou in interval) >= 1 - alpha. E o banda de
latime CONSTANTA (q) -- pretul simplitatii si al lipsei de ipoteze. (Variante
avansate dau benzi adaptive; vezi bibliografia.)

## 7. Algoritm

```
BayesianLinearRegression.fit(Phi, y, lam, sig2):
  S = inv( lam*I + (1/sig2) * Phi^T Phi )
  m = (1/sig2) * S @ (Phi^T y)
predict_interval(phi*, level):
  mean = phi*^T m
  var  = sig2 + phi*^T S phi*
  z    = normal_quantile(0.5 + level/2)
  intoarce mean, mean - z*sqrt(var), mean + z*sqrt(var)

bootstrap_interval(X, y, x*, B, level):
  pentru b = 1..B: idx = esantion cu inlocuire de marime n
                   pred_b = fit_predict(X[idx], y[idx], x*)
  intoarce cuantilele (alpha/2, 1-alpha/2) ale {pred_b}

conformal_split(X_tr, y_tr, X_cal, y_cal, x*, alpha):
  r = |y_cal - fit_predict(X_tr, y_tr, X_cal)|
  q = al ceil((n_cal+1)(1-alpha))-lea cel mai mic r
  intoarce fit_predict(X_tr,y_tr,x*) +/- q
```

## 8. Exemplu lucrat numeric (verifica-l de mana)

Caz 1D fara bias, phi(x) = x (un singur parametru w). Prior w ~ N(0, 1/lam) cu
lam = 1, zgomot sig2 = 1. Formulele se reduc la scalari:

    S = 1 / ( lam + (1/sig2) sum x_i^2 ),   m = (1/sig2) S sum x_i y_i

(a) Dupa UN punct (x1, y1) = (1, 2):
    sum x^2 = 1, sum x*y = 2.
    S1 = 1 / (1 + 1) = 0.5.
    m1 = 1 * 0.5 * 2 = 1.0.
    Posterior dupa un punct: w ~ N(1.0, 0.5). Inca larg (S1 = 0.5).

(b) Adaugam al doilea punct (x2, y2) = (2, 3). Acum pe AMBELE puncte:
    sum x^2 = 1^2 + 2^2 = 5,   sum x*y = 1*2 + 2*3 = 8.
    S2 = 1 / (1 + 5) = 1/6 = 0.1667.
    m2 = 1 * (1/6) * 8 = 8/6 = 1.3333.
    Posterior dupa doua puncte: w ~ N(1.333, 0.167).

    Observa CONTRACTIA: S a scazut de la 0.5 la 0.167 cand am adaugat un punct --
    posteriorul s-a ingustat, exact ce prezice teoria (mai multe date = mai putina
    incertitudine pe parametru).

(c) Varianta predictiva intr-un punct nou x* = 2, dupa cele doua puncte:
    var_pred = sig2 + x*^2 * S2 = 1 + 4 * (1/6) = 1 + 0.6667 = 1.6667.
    std_pred = sqrt(1.6667) = 1.291.
    Predictie: medie = x* * m2 = 2 * 1.333 = 2.667, cu interval 90%
    2.667 +/- 1.645 * 1.291 = 2.667 +/- 2.124, adica [0.54, 4.79]. Banda larga --
    corect, avem doar doua puncte.

(Exercitiul E1 si selftest-ul nucleului verifica exact S1 = 0.5, m1 = 1.0,
S2 = 1/6, m2 = 4/3.)

## 9. Vizualizare

`demo_sil.py` produce `fig_incertitudine.png`: pe datele de latenta prezice
log10(rtt_ms) cu o regresie liniara bayesiana si traseaza predictia (linie), banda
de PREDICTIE 90% (zona umbrita) si adevarul de test (puncte), ordonate dupa predictie.
Cand banda contine ~90% din puncte, acoperirea empirica confirma calibrarea. Demo-ul
mai raporteaza, comparativ: banda de predictie (larga) vs banda de incredere bootstrap
(mult mai ingusta, pentru ca e doar pe medie) vs banda conformal. Date SINTETICE.

## 10. Capcane frecvente

- A confunda intervalul de PREDICTIE cu cel de INCREDERE: cel de incredere e mult mai
  ingust si NU acopera o observatie noua. Daca raportezi increderea ca si cum ar fi
  predictie, subestimezi grav riscul (ex. promiti un deadline de latenta pe care
  pachete reale il vor incalca des).
- A crede ca banda se ingusteaza la zero cu mai multe date: doar partea epistemica
  (phi*^T S phi*) scade; zgomotul sig2 ramane.
- sig2 prost calibrat: daca subestimezi zgomotul, intervalul de predictie iese prea
  ingust si acoperirea empirica cade sub nivelul tinta. Estimeaza sig2 din reziduuri.
- Conformal cu scurgere: punctele de CALIBRARE nu trebuie folosite la antrenare,
  altfel reziduurile sunt optimiste si garantia pica (vezi scurgerea din M07).
- Bootstrap la N foarte mic (N = 5): esantioanele bootstrap se repeta mult, intervalul
  e instabil -- trateaza-l cu prudenta si raporteaza-l ca atare.

## 11. De ce conteaza pentru teza

Acest modul e SEMNATURA tezei. Coloana stiintifica (C1) compara Zenoh vs DDS sub
degradare la N = 5. O comparatie de medii fara bare de eroare nu sustine nicio
concluzie: la N mic, diferentele aparente pot fi zgomot. Cuantificarea incertitudinii
da exact ce trebuie: interval de incredere pe diferenta de RTT (e reala?), interval de
predictie pe latenta urmatorului pachet (pot garanta un deadline de teleoperatie?), si
acoperire empirica ca dovada ca barele de eroare nu sunt decorative. Conformal-ul adauga
o garantie care nu depinde de ipoteza gaussiana -- robust cand modelul e doar aproximativ.
Fara M17, rezultatele C1 raman afirmatii; cu M17 devin masuratori cu marja onesta de
eroare.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa derivezi S si m ale posteriorului pornind de la prior x verosimilitate;
- [ ] sa scrii varianta predictiva si sa explici cei doi termeni (sig2 + phi^T S phi);
- [ ] sa distingi un interval de predictie de unul de incredere si sa spui care e mai larg;
- [ ] sa construiesti un interval bootstrap si unul conformal split;
- [ ] sa masori acoperirea empirica si sa decizi daca un interval e bine calibrat;
- [ ] sa argumentezi de ce la N = 5 (C1) barele de eroare nu sunt optionale.

## Mergi mai departe

Bishop, PRML cap. 3 (regresie liniara bayesiana, varianta predictiva). ESL cap. 7-8
(bootstrap, inferenta). Angelopoulos & Bates, 'A Gentle Introduction to Conformal
Prediction' (2021). Vezi BIBLIOGRAFIE.md.
