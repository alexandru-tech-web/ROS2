# M18 -- Selectie de model si reglare de hiperparametri

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa reglezi un hiperparametru prin grid / random search peste validare incrucisata;
- sa explici DE CE eroarea CV pe care optimizezi e optimista si sa o corectezi cu nested CV;
- sa aplici criteriul Occam si criteriile de informatie AIC/BIC (cu derivarea formulei);
- sa calculezi AIC si BIC de mana pentru doua modele si sa argumentezi alegerea;
- sa raportezi onest eroarea de generalizare a unei PROCEDURI de selectie.

Prerechizite: M06 (regularizare, hiperparametrul lambda), M07 (k-fold, LOOCV,
scurgere in CV, curbe de invatare). Timp estimat: 3-4 h. Dificultate: 3/3.

Vocabular cheie (vezi GLOSAR.md): hiperparametru, grid search, random search,
nested (imbricata) cross-validation, supra-optimizare pe validare, criteriul Occam,
verosimilitate, AIC, BIC, parcimonie.

## 1. Intuitie -- alegerea onesta a modelului

In M06 ai vazut ca un model are doua tipuri de numere: PARAMETRI (invatati din date,
ex. coeficientii w) si HIPERPARAMETRI (alesi de tine inainte, ex. lambda din ridge,
gradul polinomului, k din k-NN). Reglarea de hiperparametri = alegerea celor din urma.

Tentatia naiva: incearca multe valori, masoara eroarea de validare incrucisata pentru
fiecare, pastreaza minimul, si raporteaza acel minim ca eroare de generalizare. Aici e
capcana. Daca incerci destule valori, una dintre ele va parea buna DOAR fiindca s-a
potrivit zgomotului din faldurile tale -- exact ca un student care, dand acelasi examen
de zece ori, retine intrebarile in loc sa invete materia. Minimul peste multe incercari
e o statistica optimist partinita.

Selectia onesta separa doua intrebari care se confunda usor:
1. CARE hiperparametru? (selectie) -- aici ai voie sa te uiti la validare cat vrei;
2. CAT de bine generalizeaza procedura care alege singura? (evaluare) -- aici trebuie
   date pe care selectia NU le-a atins. Nested CV face exact aceasta separare.

## 2. Formalizare -- grid search si random search

Fie un model cu hiperparametru `h` (scalar sau vector) si o procedura de potrivire
care, dat `h`, invata parametrii pe antrenare. Definim scorul de selectie:

  CV(h) = (1/k) sum_{f=1..k} L( y_{test_f}, model_h(train_f)(X_{test_f}) )

unde L e o eroare (RMSE la regresie). Alegem:

  h* = argmin_h CV(h).

- GRID SEARCH: parcurgi o multime FINITA, prestabilita, de valori (produsul cartezian
  pe fiecare axa de hiperparametri). Exhaustiv si reproductibil, dar costul creste
  exponential cu numarul de axe (blestemul dimensionalitatii pe hiperparametri).
- RANDOM SEARCH: tragi `T` configuratii la intamplare din distributii pe fiecare axa.
  La buget egal, exploreaza mai multe valori DISTINCTE pe fiecare axa decat un grid
  (Bergstra & Bengio 2012): daca doar 2 din 5 hiperparametri conteaza, grid-ul
  iroseste incercari pe combinatii ale celor irelevanti, random search nu. Determinist
  prin `numpy.random.default_rng(seed)`.

Pentru un singur hiperparametru (cazul nucleului acestui modul: gradul polinomului sau
lambda ridge), grid search pe o lista mica e suficient si transparent.

## 3. Nested CV -- de ce CV-ul pe care optimizezi e optimist

Eroarea de selectie `CV(h*)` SUBESTIMEAZA eroarea reala. Intuitia: `h*` a fost ales
TOCMAI fiindca arata bine pe ACELE falduri; minimul peste un grid include o doza de
noroc (potrivirea zgomotului), iar norocul nu se repeta pe date noi.

Nested CV (validare incrucisata imbricata) repara asta cu doua bucle:
- bucla EXTERNA (k_out falduri): doar EVALUARE. Fiecare fald extern de test e dat
  deoparte si nu participa la nicio selectie;
- bucla INTERNA (k_in falduri, doar pe antrenarea externa): SELECTIE. Ruleaza grid
  search aici si alege `h*_fald` folosind EXCLUSIV datele de antrenare ale faldului
  extern. Apoi potrivesti cu `h*_fald` si masori pe faldul extern de test -- nevazut.

Eroarea onesta = media scorurilor externe. Observa: `h*` poate diferi de la un fald
extern la altul -- e in regula, evaluam PROCEDURA de selectie, nu o valoare fixa.

### Derivare: de ce nested CV e ~ nepartinitoare

Notam cu A() procedura completa de selectie+antrenare: primeste un set de antrenare S,
ruleaza grid search intern pe S, alege `h*(S)`, potriveste modelul si intoarce un
predictor `g_S = A(S)`. Eroarea de generalizare a PROCEDURII este

  Err(A) = E_{S, (x,y)} [ L( y, A(S)(x) ) ],   media peste seturi de antrenare S
                                                 si peste un punct nou (x,y).

In nested CV, pentru faldul extern f:
- antrenam pe S_f = restul faldurilor externe (un esantion de seturi de antrenare);
- testam pe test_f, care e DISJUNCT de S_f, deci joaca rolul punctului nou (x,y);
- crucial: selectia interna foloseste numai S_f, deci `h*(S_f)` NU a vazut test_f.

Asadar scorul faldului extern, L(y_{test_f}, A(S_f)(X_{test_f})), este o estimare
nepartinitoare a lui E_{(x,y)}[ L(y, A(S_f)(x)) ] (test independent de antrenare).
Mediind peste cele k_out falduri externe, mediem si peste mai multe S_f, aproximand
Err(A). Singura partinire reziduala vine din faptul ca |S_f| < n (antrenam pe
fractiunea (k_out-1)/k_out din date), deci nested CV e USOR PESIMISTA -- supraestimeaza
putin, exact opusul optimismului periculos al lui CV(h*). De aceea regula este:

  Err_reala  ~<  Err_nested   si   CV(h*)  <  Err_reala   (in medie).

Selftest-ul verifica inegalitatea practica `Err_nested >= CV(h*)` pe date zgomotoase.

### Capcana centrala (de retinut)

`CV(h*)` NU e o estimare a generalizarii -- e doar criteriul prin care ai ALES. A-l
raporta ca "eroarea modelului meu" e supra-optimizare pe validare. Daca nu vrei nested
CV (e scump), tine un set de TEST separat, atins O SINGURA data, dupa ce selectia s-a
incheiat.

## 4. Criteriul Occam si criteriile de informatie (AIC/BIC)

Criteriul Occam (parcimonie): la putere explicativa ~egala, prefera modelul mai SIMPLU.
Modelul mai complex are mai multe sanse sa potriveasca zgomotul (varianta mare,
generalizare slaba). AIC si BIC formalizeaza acest compromis, penalizand explicit
numarul de parametri `k`. Spre deosebire de CV, NU au nevoie de re-antrenari multiple --
doar de log-verosimilitatea la maxim si de `k`.

- AIC (Akaike):    AIC = 2k - 2 ln L
- BIC (bayesian):  BIC = k ln n - 2 ln L

unde `L` = verosimilitatea maxima a modelului, `k` = numarul de parametri liberi,
`n` = numarul de observatii. Mai MIC = mai bun. Ambele scad cand potrivirea creste
(`-2 ln L` scade) si cresc cu complexitatea (termenul cu `k`).

Pentru un model gaussian cu varianta estimata prin maxima verosimilitate
(sigma^2_hat = RSS/n), log-verosimilitatea profilata da:

  -2 ln L = n ln(2 pi) + n ln(RSS / n) + n.

Constanta `n ln(2 pi) + n` e aceeasi pentru orice model pe acelasi `n`, deci se ANULEAZA
cand compari doua modele; o pastram doar pentru valori absolute corecte.

Diferenta cheie AIC vs BIC: penalizarea per parametru in plus este `2` la AIC si `ln n`
la BIC. Pentru `n > e^2 ~ 7.39`, avem `ln n > 2`, deci BIC penalizeaza complexitatea mai
TARE decat AIC, si cu cat `n` e mai mare cu atat mai mult. Consecinta: BIC e PARCIMONIOS
(consistent -- alege modelul adevarat cand n -> infinit daca acesta e in lista), AIC e
mai permisiv (optimizeaza eroarea de predictie, tinde sa supra-aleaga usor la n mare).

## 5. Algoritm (pseudocod)

```
grid_search_cv(X, y, fit_predict, grid, k):
  pentru fiecare h in grid:
    pentru fiecare fald (train, test) din k-fold(X, k):
      pred = fit_predict(X[train], y[train], X[test], h)
      scor_fald = metric(y[test], pred)
    CV[h] = media scorurilor pe falduri
  intoarce argmin_h CV[h], min CV[h], CV   (h* este OPTIMIST)

nested_cv(X, y, fit_predict, grid, k_out, k_in):
  pentru fiecare (train_ext, test_ext) din k_out-fold(X):
    h_fald = grid_search_cv(X[train_ext], y[train_ext], grid, k_in)[0]   # SELECTIE interna
    pred   = fit_predict(X[train_ext], y[train_ext], X[test_ext], h_fald) # EVALUARE externa
    scor_ext = metric(y[test_ext], pred)
  intoarce media scorurilor externe   # eroare ONESTA a procedurii

aic(neg2ll, k)        = 2*k + neg2ll
bic(neg2ll, k, n)     = k*ln(n) + neg2ll
neg2ll_gaussian(RSS,n)= n*ln(2*pi) + n*ln(RSS/n) + n
```

## 6. Exemplu lucrat numeric (verifica-l de mana)

Doua modele potrivite pe `n = 100` observatii, eroare gaussiana:
- Model A (simplu): `k_A = 3` parametri, `RSS_A = 52`;
- Model B (complex): `k_B = 6` parametri, `RSS_B = 50` (potriveste PUTIN mai bine).

Pas 1 -- log-verosimilitatea (`-2 ln L = n ln(2 pi) + n ln(RSS/n) + n`,
cu `n ln(2 pi) = 100 * 1.837877 = 183.7877` si `+n = +100`, deci constanta = 283.7877):

  -2 ln L_A = 283.7877 + 100 * ln(52/100) = 283.7877 + 100 * (-0.653926) = 218.3951
  -2 ln L_B = 283.7877 + 100 * ln(50/100) = 283.7877 + 100 * (-0.693147) = 214.4730

(B are `-2 ln L` mai mic: potriveste mai bine, cum era de asteptat.)

Pas 2 -- AIC = 2k + (-2 ln L):

  AIC_A = 2*3 + 218.3951 = 6  + 218.3951 = 224.3951
  AIC_B = 2*6 + 214.4730 = 12 + 214.4730 = 226.4730
  dAIC = AIC_B - AIC_A = +2.078  > 0  ->  AIC alege A (modelul SIMPLU).

Pas 3 -- BIC = k ln(n) + (-2 ln L), cu `ln(100) = 4.60517`:

  BIC_A = 3*4.60517 + 218.3951 = 13.8155 + 218.3951 = 232.2106
  BIC_B = 6*4.60517 + 214.4730 = 27.6310 + 214.4730 = 242.1040
  dBIC = BIC_B - BIC_A = +9.893 > 0  ->  BIC alege tot A.

Pas 4 -- interpretare. Castigul de potrivire al lui B (`-2 ln L` mai mic cu 3.922) NU
acopera costul celor 3 parametri in plus: AIC cere 2*3 = 6 (6 - 3.922 = +2.078 > 0),
BIC cere 4.60517*3 = 13.815 (13.815 - 3.922 = +9.893 > 0). BIC penalizeaza de ~4.8 ori
mai tare (9.893 / 2.078) -- la `n = 100`, `ln n / 2 = 2.30`. Ambele aleg parcimonia;
BIC ar fi respins B chiar daca acesta potrivea sensibil mai bine.

(Selftest-ul nucleului si exercitiile verifica EXACT aceste valori: 224.3951,
232.2106, dAIC > 0, dBIC > dAIC > 0.)

## 7. Vizualizare

`demo_sil.py` produce `fig_selectie_model.png`: RMSE de validare incrucisata vs gradul
polinomului pe datele de latenta, cu gradul ales marcat si o linie orizontala la
eroarea ONESTA (nested CV). Acolo unde curba de selectie coboara sub linia onesta se
vede direct optimismul selectiei. Date SINTETICE (semanate din C1/M).

## 8. Capcane frecvente

- SUPRA-OPTIMIZAREA PE VALIDARE: a raporta `CV(h*)` ca eroare de generalizare. Cu cat
  gridul e mai mare, cu atat minimul e mai optimist. Foloseste nested CV sau un test
  atins o singura data.
- Scurgere de selectie in CV: a alege hiperparametrii PE TOT setul si abia apoi a face
  CV-ul de evaluare -- selectia a vazut deja testul. Selectia trebuie INAUNTRUL buclei
  externe (vezi M07, scurgerea de preprocesare e acelasi defect).
- Grid prea grosier/prea fin: prea grosier rateaza optimul; prea fin pe multe axe explodeaza
  combinatoric -- treci pe random search.
- AIC/BIC aplicate gresit: cer ACELASI `n` si modele pe ACELEASI date; `k` trebuie sa
  numere TOTI parametrii liberi (inclusiv varianta estimata, daca o numeri consecvent).
  Nu compara AIC intre seturi de date diferite.
- Date corelate (repetitii ale aceleiasi conditii): split-ul aleator scurge informatie
  intre falduri si face selectia inca mai optimista; foloseste leave-one-group-out
  (validare LOCO, ca la selectorul C1).

## 9. De ce conteaza pentru teza

Selectorul C1 ESTE o problema de selectie de model: alegem ce middleware / regula sub o
conditie de retea. Doua lectii din acest modul intra direct in metodologie:
1. nu raporta scorul pe care l-ai OPTIMIZAT ca rezultat -- validarea pe grupuri (LOCO) +
   o estimare onesta (analog nested CV) impiedica concluzia ca "selectorul invatat bate
   baseline-ul" cand de fapt s-a potrivit zgomotului. Exact aici a fost concluzia onesta
   DEPENDENTA DE DEADLINE (selectorul merita doar la D mare) -- ar fi parut mai bun daca
   raportam minimul de selectie.
2. parcimonia: la potrivire ~egala intre always-CycloneDDS si un selector invatat (mai
   multi parametri), Occam / BIC impun baseline-ul simplu pana cand castigul e clar si
   robust. AIC/BIC ofera un argument cantitativ, ieftin, pentru "modelul simplu e
   suficient" -- de raportat alaturi de CV-ul pe grupuri.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa explici de ce minimul CV peste un grid e o estimare optimista;
- [ ] sa descrii cele doua bucle ale nested CV si ce rol are fiecare;
- [ ] sa argumentezi de ce nested CV e ~ nepartinitoare (chiar usor pesimista);
- [ ] sa scrii formulele AIC si BIC si sa spui care penalizeaza complexitatea mai tare;
- [ ] sa calculezi AIC/BIC de mana pentru doua modele si sa motivezi alegerea.

## Mergi mai departe

ESL cap. 7 (evaluarea modelului, AIC/BIC/criterii de informatie); ISL cap. 5-6
(validare, selectie de subset, criterii). Bergstra & Bengio 2012 (random search).
Vezi BIBLIOGRAFIE.md.
