# M10 -- Naive Bayes

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa explici diferenta intre un model GENERATIV (modeleaza P(x, y)) si unul
  DISCRIMINATIV (modeleaza direct P(y|x)), si unde sta NB;
- sa derivi regula de decizie MAP din teorema lui Bayes plus ipoteza de
  independenta conditionala, in spatiul log;
- sa implementezi Gaussian Naive Bayes de la zero (prior-uri + medie/varianta
  per clasa per feature) si sa prezici prin argmax al log-posteriorului;
- sa recunosti capcanele (zero-probabilitate, feature-uri corelate) si sa
  folosesti NB ca linie de baza ieftina pe campaniile mele.

Prerechizite: M01 (probabilitate: Bayes, densitate gaussiana, independenta),
M03 (invatare supervizata: risc, clasificare). Timp estimat: 2-3 h.
Dificultate: 2/3.

Vocabular cheie (vezi GLOSAR.md): model generativ vs discriminativ, prior,
verosimilitate (likelihood), posterior, regula MAP, ipoteza de independenta
conditionala (naive), Gaussian Naive Bayes, log-posterior, var_smoothing,
linie de baza.

## 1. Intuitie: generativ vs discriminativ

Un clasificator DISCRIMINATIV (ex. regresia logistica, M08) invata direct
frontiera P(y|x): unde trece granita intre clase. Un clasificator GENERATIV
invata cum arata fiecare clasa -- modeleaza P(x|y) si P(y) -- apoi INTOARCE cu
Bayes ca sa obtina P(y|x). Naive Bayes e generativ: pentru fiecare clasa retine
'cum se distribuie feature-urile' (la GaussianNB: o medie si o varianta per
feature), plus cat de frecventa e clasa (prior).

Avantajul: e foarte ieftin (nici un pas de optimizare iterativa -- doar medii si
variante), nu are nevoie de multe date ca sa porneasca si da un reper instant.
Pretul: ipoteza 'naiva' ca feature-urile sunt independente in interiorul unei
clase -- aproape niciodata adevarata, dar surprinzator de utila in practica.

## 2. Formalizare: Bayes + ipoteza de independenta conditionala

Vrem clasa cea mai probabila dat fiind vectorul de feature-uri x = (x_1,...,x_d):

    P(y=c | x) = P(x | y=c) * P(y=c) / P(x)            (teorema lui Bayes)

P(x) (evidenta) e aceeasi pentru toate clasele, deci pentru a alege clasa o
putem ignora. Ramane verosimilitatea P(x|y=c) ori prior-ul P(y=c). Problema:
P(x_1,...,x_d | y=c) e greu de estimat in d dimensiuni. Ipoteza NAIVA spune ca,
data fiind clasa, feature-urile sunt INDEPENDENTE:

    P(x_1,...,x_d | y=c) = prod_{j=1}^{d} P(x_j | y=c)

Asa, in loc de o densitate d-dimensionala, estimam d densitati 1D -- mult mai
ieftin si mai stabil la N mic.

La Gaussian Naive Bayes alegem P(x_j | y=c) = N(x_j ; mu_cj, var_cj):

    N(x ; mu, var) = (1 / sqrt(2*pi*var)) * exp( - (x-mu)^2 / (2*var) )

## 3. Derivare: regula MAP cu log-posterior

Estimatorul MAP (maximum a posteriori) alege:

    y_hat = argmax_c  P(y=c) * prod_j P(x_j | y=c)

Produsele de probabilitati subdimensioneaza numeric (underflow) la multe
feature-uri, asa ca lucram in LOG (log e monoton, deci argmax-ul nu se schimba):

    log P(y=c) + sum_j log N(x_j ; mu_cj, var_cj)

Cu densitatea gaussiana, fiecare termen log devine:

    log N(x_j ; mu_cj, var_cj)
        = -0.5*log(2*pi*var_cj) - (x_j - mu_cj)^2 / (2*var_cj)

Deci scorul (log-posteriorul NENORMALIZAT, fara log-evidenta) pentru clasa c e:

    g_c(x) = log P(y=c)
             + sum_j [ -0.5*log(2*pi*var_cj) - (x_j - mu_cj)^2 / (2*var_cj) ]

si regula de decizie e y_hat = argmax_c g_c(x). Daca vrei posteriorul NORMALIZAT
(probabilitati care insumeaza 1), aplici softmax pe (g_0, ..., g_{K-1}):

    P(y=c | x) = exp(g_c) / sum_{c'} exp(g_{c'})

(in cod facem softmax STABIL: scadem max-ul inainte de exp.)

Estimari de antrenare (maxima verosimilitate). Cu n exemple, n_c in clasa c:

    P(y=c)  = n_c / n
    mu_cj   = (1/n_c) sum_{i: y_i=c} x_ij
    var_cj  = (1/n_c) sum_{i: y_i=c} (x_ij - mu_cj)^2        (MLE, ddof=0)

Nota: varianta MLE foloseste 1/n_c, nu 1/(n_c-1). E alegerea de estimare a
verosimilitatii maxime (si cea a sklearn GaussianNB), de aceea testele cer
`ddof=0`.

## 4. Algoritm

```
fit(X, y):
  classes = unice(y)
  pentru fiecare clasa c:
    Xc = randurile lui X cu y == c
    prior[c] = nr_randuri(Xc) / n
    mu[c]    = media pe coloane a lui Xc
    var[c]   = varianta MLE pe coloane a lui Xc + var_smoothing   # podea

predict_log_proba(X):           # scor MAP nenormalizat
  pentru fiecare clasa c:
    g_c = log(prior[c]) + sum_j [ -0.5*log(2*pi*var[c,j])
                                  - (x_j - mu[c,j])^2 / (2*var[c,j]) ]
  intoarce matricea g (n_samples x n_classes)

predict(X): intoarce classes[ argmax_c g_c ]
```

## 5. Exemplu lucrat numeric (verifica-l de mana)

Doua clase, UN singur feature. Antrenare:
- clasa 0: x = [1, 2, 3]  -> mu_0 = 2,  var_0 = ((1-2)^2+(2-2)^2+(3-2)^2)/3 = 2/3
- clasa 1: x = [5, 6, 7]  -> mu_1 = 6,  var_1 = 2/3
- prior: n_0 = n_1 = 3 -> P(y=0) = P(y=1) = 0.5

Clasificam x = 3. Calculam g_0(3) si g_1(3). Cu var = 2/3:
termenul constant -0.5*log(2*pi*var) = -0.5*log(2*pi*0.6667) = -0.71621 (ambele
clase, fiindca var e egala).

g_0(3) = log(0.5) + [ -0.71621 - (3-2)^2 / (2*0.6667) ]
       = -0.69315 + ( -0.71621 - 0.75 )
       = -2.15935

g_1(3) = log(0.5) + [ -0.71621 - (3-6)^2 / (2*0.6667) ]
       = -0.69315 + ( -0.71621 - 6.75 )
       = -8.15935

g_0(3) > g_1(3) => prezice clasa 0 (x=3 e mai aproape de mu_0=2 decat de mu_1=6).
Posterior normalizat: P(y=0|x=3) = exp(g_0)/(exp(g_0)+exp(g_1)) = 0.9975.

Punct de control simetric: la x = 4 (mijloc), (4-2)^2 = (4-6)^2 = 4, deci
g_0(4) = g_1(4) si posteriorul e 0.5/0.5 -- frontiera de decizie. Vezi tema in
`naive_bayes_core.py::_selftest` (verifica EXACT g_0(3), g_1(3) si egalitatea la
x=4) si exercitiul E3.

## 6. Vizualizare

`demo_sil.py` produce `fig_nb_frontiera.png`: frontiera de decizie a lui Gaussian
NB pe doua feature-uri standardizate (p95_ms, loss_frac) ale ferestrelor de link,
cu punctele de antrenare colorate pe clasa (usable / inutilizabil). Frontiera e
patratica (vine din termenul (x-mu)^2/var cu var diferit pe clase). Date
SINTETICE (semanate din C1/M).

## 7. Capcane frecvente

- Zero-probabilitate / varianta nula. Daca un feature e CONSTANT intr-o clasa,
  var_cj = 0 -> impartire la zero -> log-densitate -inf si predictii rupte.
  Remediu: o PODEA de varianta (`var_smoothing` > 0; sklearn adauga
  var_smoothing * max(var)). Pentru feature-uri DISCRETE rare se foloseste
  analogul Laplace (numarare cu +1) -- vezi varianta Multinomial/Bernoulli NB.
- Feature-uri corelate. Ipoteza de independenta e incalcata cand feature-urile
  sunt corelate (ex. p95_ms si loss_frac cresc impreuna la degradare): NB le
  numara de doua ori, deci posteriorul iese SUPRA-increzator (probabilitati
  impinse spre 0/1). Adesea ALEGE corect clasa, dar probabilitatile lui nu sunt
  bine calibrate -- nu le lua ca incertitudine de incredere (vezi M17).
- A confunda log-posteriorul nenormalizat cu o probabilitate. `predict_log_proba`
  de aici NU scade log-evidenta; e bun pentru argmax si comparatii, dar pentru
  probabilitati normalizeaza cu softmax (`predict_proba`).
- A uita standardizarea cand combini feature-uri pe scale diferite cu alti pasi
  ai pipeline-ului -- NB gaussian e invariant la scalarea per feature in teorie,
  dar standardizarea pastreaza coerenta cu restul cursului si stabilitatea
  numerica a podelei de varianta.

## 8. De ce conteaza pentru teza

NB e LINIA DE BAZA ieftina: pe clasificarea 'link utilizabil' (M09) iti da un
reper in cateva milisecunde, fara hiperparametri de reglat si fara optimizare.
Inainte sa pretinzi ca un model invatat (selectorul C1, arbori, ensembluri)
merita complexitatea, trebuie sa bata aceasta baza si baza triviala (clasa
majoritara). La clase dezechilibrate (usable ~30%) judeca NB cu precizie/recall/
F1, nu doar acuratete (M09). Si fiindca porneste bine la N mic, e potrivit
metodologic pentru campaniile mele mici.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa explici diferenta generativ vs discriminativ si unde sta NB;
- [ ] sa scrii ipoteza de independenta conditionala si de ce o folosim;
- [ ] sa derivi g_c(x) = log P(y=c) + sum_j log N(x_j; mu, var) si regula argmax;
- [ ] sa calculezi log-posteriorul de mana pe un caz cu 2 clase si 1 feature;
- [ ] sa explici de ce var_smoothing evita -inf si de ce corelatiile strica
      calibrarea probabilitatilor.

## Mergi mai departe

ESL cap. 6.6 (densitati per clasa); ISL cap. 4.4-4.5 (LDA/QDA, Naive Bayes);
Murphy, Machine Learning: A Probabilistic Perspective, cap. 3. Vezi BIBLIOGRAFIE.md.
