# M13 -- Ensembluri

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa explici de ce o MULTIME de modele slabe poate bate orice model individual;
- sa derivi de ce bagging reduce VARIANTA (formula var medie ~ corelatie) si de ce
  boosting reduce BIASUL (corectie aditiva pe reziduuri);
- sa implementezi bagging si gradient boosting peste un ciot de decizie de la zero;
- sa calculezi de mana un pas de gradient boosting (reziduu + actualizare log-odds);
- sa recunosti capcana supra-invatarii la boosting (prea multi pasi).

Prerechizite: M12 (arbori de decizie -- ciotul e un arbore de adancime 1; daca M12
nu e parcurs, ciotul e definit complet aici), M03 (bias-varianta, risc empiric vs
real). Timp estimat: 3-4 h. Dificultate: 3/3.

Vocabular cheie (vezi GLOSAR.md): invatator slab, ensemblu, bagging, bootstrap,
out-of-bag, Random Forest, boosting, gradient boosting, reziduu, log-odds, rata de
invatare, supra-invatare la boosting.

## 1. Intuitie

Un singur ciot de decizie (un prag pe o axa) e un invatator SLAB: greseste des, iar
pe date zgomotoase predictiile lui sar mult de la un esantion la altul (varianta
mare). Ideea de ensemblu: in loc de un model bun, antreneaza MULTE modele slabe si
combina-le. Doua retete opuse:

- BAGGING (paralel): antreneaza modele independente pe versiuni perturbate ale
  datelor si mediaza-le. Mediarea taie varianta -- ca media a N masuratori
  zgomotoase e mai stabila decat una singura.
- BOOSTING (secvential): fiecare model nou repara greselile celui dinainte,
  potrivind ce a ramas (reziduul). Suma lor reduce biasul -- modelul slab devine
  treptat puternic.

Pe date tabulare, gradient boosting cu arbori e in practica cel mai bun predictor
'din raft' -- de aici importanta lui pentru teza (vezi sectiunea 9).

## 2. Formalizare: bagging

Fie un set de antrenare D cu n exemple si un algoritm de baza (ciotul). Bagging
construieste B modele:

- pentru b = 1..B: trage un esantion BOOTSTRAP D_b -- n exemple din D, CU INLOCUIRE
  (unele se repeta, altele lipsesc); antreneaza modelul h_b pe D_b.
- agregare: clasificare -> vot majoritar; regresie -> medie.
  H(x) = majoritate{ h_1(x), ..., h_B(x) }.

Out-of-bag: in fiecare D_b, un exemplu lipseste cu probabilitate (1 - 1/n)^n -> 1/e
~ 0.368 (vezi exercitiul 2). Cele ~37% exemple out-of-bag dau o estimare gratuita a
erorii, fara set de validare separat.

## 3. Random Forest

Random Forest = bagging cu arbori + un truc in plus: la FIECARE split, fiecare arbore
alege cel mai bun prag dintr-un SUBSET aleator de m feature-uri (din cele d), nu din
toate. De ce: daca un feature e foarte tare, toti arborii din bagging il aleg si ies
CORELATI -- iar mediarea modelelor corelate reduce putin varianta (vezi derivarea
din sectiunea 5). Forta-i sa difere (subset de feature-uri) -> arbori decorelati ->
varianta ansamblului scade mai mult. m = sqrt(d) e o alegere uzuala la clasificare.

(In nucleul nostru, baza e un ciot pe o singura axa, deci 'subsetul de feature-uri'
e implicit -- pastram bagging-ul pur ca exemplu didactic minimal; ideea Random Forest
e decorelarea, demonstrata cu sklearn in `ensembluri_sklearn.py`.)

## 4. Boosting si gradient boosting

Boosting construieste un model ADITIV, pas cu pas:

  F_0(x) = constanta ;   F_m(x) = F_{m-1}(x) + lr * h_m(x).

La fiecare pas potrivim un model slab h_m pe ce a ramas de explicat. Gradient
boosting da o reteta generala: h_m aproximeaza GRADIENTUL NEGATIV al pierderii fata
de predictia curenta F (coborare in gradient in spatiul functiilor).

Pentru clasificare binara lucram in spatiul LOG-ODDS F(x), cu probabilitatea
p(x) = sigmoid(F(x)) = 1 / (1 + e^{-F(x)}) si pierderea logistica

  L = - sum_i [ y_i * log p_i + (1 - y_i) * log(1 - p_i) ].

Derivata pierderii fata de F_i este p_i - y_i, deci gradientul NEGATIV (directia de
coborare) este REZIDUUL

  r_i = y_i - p_i.

Algoritmul: incepe cu F_0 = log-odds-ul prior; la fiecare pas calculeaza r_i = y_i -
p_i, potriveste un ciot de REGRESIE pe reziduuri si actualizeaza F cu lr * h_m.
Rata de invatare lr (mica, ex. 0.1-0.3) face pasii prudenti -- mai multi pasi, dar
mai putin supra-invatare.

## 5. Derivare: de ce bagging reduce varianta

Fie B modele cu aceeasi varianta sigma^2, corelate doua cate doua cu coeficientul
rho. Varianta MEDIEI lor este:

  Var( (1/B) sum_b h_b )
    = (1/B^2) [ sum_b Var(h_b) + sum_{b != c} Cov(h_b, h_c) ]
    = (1/B^2) [ B * sigma^2 + B(B-1) * rho * sigma^2 ]
    = rho * sigma^2 + (1 - rho) * sigma^2 / B.

Citeste rezultatul:

  Var_medie = rho * sigma^2  +  (1 - rho) * sigma^2 / B.

- Al doilea termen (1 - rho) sigma^2 / B -> 0 cand B creste: cu cat mai multe modele,
  cu atat mai putina varianta DIN partea necorelata. Asta face bagging-ul.
- Primul termen rho * sigma^2 NU scade cu B: e podeaua impusa de CORELATIA dintre
  modele. De aici trucul Random Forest: scade rho (decoreleaza arborii) ca sa cobori
  podeaua.

Biasul mediei e acelasi cu al unui model individual (mediezi modele nepartinitoare),
deci bagging cumpara reducere de varianta aproape gratis. Boosting face opusul: scade
biasul adaugand corectii, cu riscul de a creste varianta daca pui prea multi pasi.

## 6. Algoritm (pseudocod)

```
BAGGING(D, B):
  pentru b = 1..B:
    D_b = bootstrap(D)            # n exemple cu inlocuire (rng semanat)
    h_b = antreneaza_baza(D_b)    # ciot de decizie
  H(x) = vot_majoritar{ h_1(x), ..., h_B(x) }

GRADIENT_BOOSTING(D = {(x_i, y_i)}, M, lr):
  p_bar = media(y) ; F_0 = log(p_bar / (1 - p_bar))   # log-odds prior
  pentru m = 1..M:
    p_i  = sigmoid(F_{m-1}(x_i))                       # probabilitati curente
    r_i  = y_i - p_i                                   # reziduu = -gradient
    h_m  = ciot_de_REGRESIE pe (x_i, r_i)              # potriveste reziduurile
    F_m(x) = F_{m-1}(x) + lr * h_m(x)                  # actualizare aditiva
  p(x) = sigmoid(F_M(x)) ; eticheta = [ p(x) >= 0.5 ]
```

## 7. Exemplu lucrat numeric (verifica-l de mana)

Un pas de gradient boosting pe 4 puncte, un singur feature x, lr = 0.5.

Date: x = [1, 2, 3, 4], y = [0, 0, 1, 1].

(a) Initializare. p_bar = media(y) = 0.5, deci
    F_0 = log(0.5 / 0.5) = log(1) = 0 pentru toate punctele.
    p_i = sigmoid(0) = 0.5 pentru toate.

(b) Reziduuri (gradientul negativ al pierderii logistice):
    r_i = y_i - p_i = [0-0.5, 0-0.5, 1-0.5, 1-0.5] = [-0.5, -0.5, 0.5, 0.5].

(c) Ciot de REGRESIE pe reziduuri. Pragurile candidate sunt 1.5, 2.5, 3.5. Costul =
    suma erorilor patratice fata de media fiecarei parti (SSE):
      prag 2.5: stanga {x<=2.5}=(-0.5,-0.5) media -0.5 SSE 0; dreapta (0.5,0.5)
                media 0.5 SSE 0 -> total 0 (separare PERFECTA a reziduurilor);
      prag 1.5: total = 0.6667 ; prag 3.5: total = 0.6667.
    Castiga pragul 2.5. Frunze: h(x) = -0.5 pentru x <= 2.5, +0.5 pentru x > 2.5.
    Deci h = [-0.5, -0.5, 0.5, 0.5].

(d) Actualizare log-odds:
    F_1 = F_0 + lr * h = 0 + 0.5 * [-0.5, -0.5, 0.5, 0.5] = [-0.25, -0.25, 0.25, 0.25].

(e) Probabilitati noi:
    sigmoid(-0.25) = 0.4378 ;  sigmoid(0.25) = 0.5622.
    p_1 = [0.4378, 0.4378, 0.5622, 0.5622]. Cu pragul 0.5 -> [0, 0, 1, 1] = y.

(f) Verificare ca pierderea a scazut:
    pierderea logistica inainte = -log(0.5) = 0.6931 ; dupa = 0.5759 < 0.6931.
    Un singur pas a impins probabilitatile in directia corecta.

(Selftest-ul nucleului si exercitiul 4 verifica exact aceste valori: r = y - p si
delta_F = lr * h.)

## 8. Vizualizare

`demo_sil.py` produce `fig_ensembluri.png`, doua panouri pe `mission_complete`:
- stanga: acuratetea CV 5-fold a celor trei modele (un singur ciot < bagging <
  boosting) -- ensemblurile bat invatatorul slab de baza;
- dreapta: eroarea de TRAIN si de TEST a boosting-ului vs numarul de pasi. Eroarea de
  train scade mereu; cea de test scade, apoi se ASEAZA (uneori creste usor) -- semnatura
  supra-invatarii. Numarul de pasi e un hiperparametru de OPRIRE, nu 'cu cat mai multe
  cu atat mai bine'. Date SINTETICE.

## 9. Capcane frecvente

- BOOSTING cu prea multi pasi: continua sa scada eroarea de TRAIN spre 0 dar incepe sa
  invete zgomotul -> eroarea de test creste. Foloseste early stopping (validare) si
  rate de invatare mici. Vezi exercitiul 5.
- BAGGING pe un model STABIL (ex. regresie liniara) aduce putin: bagging ajuta cand
  baza are varianta mare (arbori adanci, ciot pe date zgomotoase). Mediarea unor
  modele aproape identice nu schimba nimic.
- Confuzia bias vs varianta: bagging ataca VARIANTA (lasa biasul neschimbat), boosting
  ataca BIASUL (poate creste varianta). Nu sunt interschimbabile.
- 'Mai multi arbori strica': la BAGGING/Random Forest, mai multi arbori nu supra-invata
  (doar mediezi mai bine) -- B mare e sigur. La BOOSTING, mai multi pasi POT supra-invata.
  Cele doua se comporta opus la cresterea numarului de modele.
- A uita validarea incrucisata: 'ensemblul a iesit mai bun' pe train nu inseamna nimic;
  compara pe falduri (vezi M07), cu N mic mai ales.

## 10. De ce conteaza pentru teza

Tinta `mission_complete` (misiune SAR reusita din fractia de telemetrie livrata,
latenta p95 si numarul de drone) e tabulara, mica si zgomotoasa -- exact terenul unde
gradient boosting domina. In demo, boosting bate clar un singur ciot si bagging-ul pe
acuratetea CV. Pentru un predictor de rezultat al misiunii consumat de selectorul
link-aware (C3), un ensemblu de boosting e candidatul natural -- cu grija la N mic:
valideaza pe grupuri (LOCO, ca la selectorul C1) si opreste pasii din timp. Datele de
aici sunt SINTETICE; pe campanie reala numarul de pasi si lr se aleg prin validare.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa explici de ce mediarea modelelor reduce varianta dar nu biasul;
- [ ] sa derivi formula Var_medie = rho*sigma^2 + (1-rho)*sigma^2/B si sa o citesti;
- [ ] sa calculezi de mana un pas de gradient boosting (reziduu + actualizare);
- [ ] sa spui de ce Random Forest decoreleaza arborii si de ce ajuta;
- [ ] sa recunosti supra-invatarea la boosting pe o curba train/test.

## Mergi mai departe

ESL cap. 8 (bagging), 10 (boosting), 15 (Random Forest); ISL cap. 8. Friedman (2001),
'Greedy Function Approximation: A Gradient Boosting Machine'. Vezi BIBLIOGRAFIE.md.
