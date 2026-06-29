# M01 -- Probabilitate si statistica pentru ML

## Antet pedagogic

### Obiective de invatare
La finalul modulului poti:
- sa DEFINESTI o variabila aleatoare si sa calculezi asteptarea si varianta ei;
- sa DERIVI densitatile Bernoulli, gaussiana si lognormala si sa explici cand
  fiecare modeleaza bine un fenomen din teza (pierdere de pachete vs RTT);
- sa DEDUCI estimatorul de maxima verosimilitate (MLE) pentru Gauss si Bernoulli;
- sa CONSTRUIESTI un interval de incredere prin bootstrap nonparametric;
- sa ARGUMENTEZI de ce N=5 (campaniile C1) cere grija statistica explicita.

### Prerechizite
- M00 (algebra liniara de baza: vectori, sume, produs scalar).
- Calcul diferential elementar (derivate, logaritm natural, maximizare prin
  anularea derivatei).
- Python + numpy de baza.

### Timp si dificultate
- Timp estimat: 2.5 - 3 ore (citire + exemplul numeric + exercitii).
- Dificultate: 2 / 3.

### Vocabular cheie (vezi GLOSAR.md)
- variabila aleatoare -- marime cu valori incerte, descrisa de o distributie.
- pdf (functie de densitate) -- f(x) >= 0 cu integrala 1; probabilitatea pe un
  interval e aria de sub f.
- asteptare (medie) E[X] -- centrul de masa al distributiei.
- varianta Var[X] -- imprastierea in jurul mediei; abaterea standard = sqrt(Var).
- Bernoulli(p) -- variabila 0/1 cu P(X=1)=p (model de pierdere/livrare pachet).
- gaussiana N(mu, sigma^2) -- clopotul simetric; suma de multe efecte mici.
- lognormala -- X cu log(X) gaussian; coada lunga la dreapta (model de RTT).
- MLE (maxima verosimilitate) -- parametrii care fac datele cel mai probabile.
- MAP (maxim a posteriori) -- MLE plus un prior bayesian (regularizare).
- teorema lui Bayes -- actualizarea credintei: posterior ~ verosimilitate x prior.
- interval de incredere -- interval care prinde parametrul cu o probabilitate data.
- bootstrap -- reesantionare cu inlocuire pentru a estima incertitudinea.

---

## Corp

### 1. Intuitie

Un benchmark de retea nu da un numar, ci o DISTRIBUTIE. Cand masor RTT-ul de
dus-intors al unui pachet pe o legatura degradata, valorile nu sunt simetrice in
jurul mediei: cele mai multe pachete vin repede, dar o coada de pachete intarziate
trage media in sus. Asta e semnatura unei LOGNORMALE, nu a unei gaussiene.

Separat, fiecare pachet fie ajunge, fie se pierde: un experiment 0/1, adica o
BERNOULLI cu parametrul p = rata de pierdere.

Probabilitatea ne da limbajul pentru a descrie aceste fenomene; STATISTICA ne da
uneltele pentru a estima parametrii (mu, sigma, p) din date FINITE si pentru a
spune CAT DE SIGURI suntem pe estimari. La N=5 a doua parte nu e un lux, e
obligatorie: o medie din 5 rulari poate fi vizibil departe de adevar.

### 2. Formalizare

O variabila aleatoare continua X are densitatea f(x) >= 0 cu integral(f) = 1.
Asteptarea si varianta:

    E[X]   = integral( x * f(x) dx )
    Var[X] = E[(X - E[X])^2] = E[X^2] - (E[X])^2

Distributiile folosite in modul:

- Bernoulli(p), x in {0, 1}:
      P(X = x) = p^x * (1-p)^(1-x)
      E[X] = p,      Var[X] = p*(1-p)

- Gaussiana N(mu, sigma^2):
      f(x) = 1/sqrt(2*pi*sigma^2) * exp( -(x-mu)^2 / (2*sigma^2) )
      E[X] = mu,     Var[X] = sigma^2

- Lognormala (log(X) ~ N(mu, sigma^2)), x > 0:
      f(x) = 1/(x*sigma*sqrt(2*pi)) * exp( -(log(x)-mu)^2 / (2*sigma^2) )
      E[X] = exp(mu + sigma^2/2)
  Atentie: mu, sigma sunt parametrii NORMALEI subiacente (pe scala log), NU media
  si abaterea lui X.

Teorema lui Bayes (actualizarea credintei despre un parametru theta dat datele D):

    posterior(theta | D) = verosimilitate(D | theta) * prior(theta) / evidenta(D)

### 3. Derivare pas cu pas: MLE pentru Gauss

Datele x_1..x_n sunt presupuse independente, fiecare N(mu, sigma^2). Verosimili-
tatea e produsul densitatilor; lucram cu LOG-verosimilitatea (suma, mai usor):

    log L(mu, sigma^2) = sum_i [ -0.5*log(2*pi) - 0.5*log(sigma^2)
                                 - (x_i - mu)^2 / (2*sigma^2) ]

Derivam si anulam. In raport cu mu:

    d/dmu log L = (1/sigma^2) * sum_i (x_i - mu) = 0
    => sum_i x_i = n*mu
    => mu_hat = (1/n) * sum_i x_i            (media esantionului)

In raport cu sigma^2 (notam v = sigma^2):

    d/dv log L = sum_i [ -1/(2v) + (x_i - mu)^2 / (2v^2) ] = 0
    => n*v = sum_i (x_i - mu)^2
    => sigma2_hat = (1/n) * sum_i (x_i - mu_hat)^2

Observatie cheie: numitorul e n, NU n-1. Estimatorul MLE al variantei e BIASAT in
jos (subestimeaza imprastierea) cu factorul (n-1)/n. La N=5 acest factor e 4/5 =
0.8 -- o subestimare de 20%, deloc neglijabila. (Varianta nedeplasata foloseste
n-1; vezi capcane.)

Pentru Bernoulli, aceeasi reteta da p_hat = (1/n)*sum_i x_i (fractia de 1).

MAP pe scurt: daca adaugam un prior pe theta, maximizam log-verosimilitate +
log-prior. Un prior gaussian pe coeficienti devine penalizare patratica (L2) --
exact regularizarea Ridge de la M06. Deci MAP = MLE + regularizare.

### 4. Algoritm (pseudocod)

    MLE_Gauss(x_1..x_n):
        mu_hat     = medie(x)
        sigma2_hat = medie( (x - mu_hat)^2 )      # numitor n
        return mu_hat, sigma2_hat

    Bootstrap_CI_medie(x_1..x_n, B, alpha, seed):
        pentru b = 1..B:
            x* = esantion de marime n din x, CU inlocuire (rng semanat)
            m_b = medie(x*)
        sorteaza m_1..m_B
        lo = cuantila(alpha/2),  hi = cuantila(1 - alpha/2)
        return (lo, hi)

### 5. EXEMPLU LUCRAT NUMERIC (de mana)

Cinci masuratori RTT [ms] dintr-o mini-campanie (N=5, ca in C1):

    x = [120, 100, 140, 160, 80]

Pas 1 -- MLE Gauss, media:
    suma = 120+100+140+160+80 = 600
    mu_hat = 600 / 5 = 120.0 ms

Pas 2 -- abaterile fata de medie si patratele lor:
    (120-120)=0     -> 0
    (100-120)=-20   -> 400
    (140-120)=20    -> 400
    (160-120)=40    -> 1600
    (80-120)=-40    -> 1600
    suma patratelor = 0+400+400+1600+1600 = 4000

Pas 3 -- varianta MLE (numitor n=5) vs nedeplasata (numitor n-1=4):
    sigma2_hat (MLE)        = 4000 / 5 = 800   -> sigma_hat = 28.28 ms
    s2 (nedeplasata, n-1)   = 4000 / 4 = 1000  -> s = 31.62 ms
    MLE subestimeaza imprastierea: 800 vs 1000 (factorul 4/5 = 0.8).

Pas 4 -- Bernoulli pe pierderi. Daca din cele 5 pachete 1 s-a pierdut:
    p_hat = 1/5 = 0.20

Pas 5 -- de ce N=5 e fragil (interval normal aproximativ pentru medie):
    eroarea standard a mediei ~ s / sqrt(n) = 31.62 / sqrt(5) = 14.14 ms
    interval 95% aprox = mu_hat +- 1.96 * 14.14 = 120 +- 27.7
                       = [92.3, 147.7] ms
    Largimea ~55 ms pentru o medie de 120 ms: incertitudine de ~+-23%. Cu N=5 NU
    poti distinge doua middleware-uri ale caror medii difera cu mai putin de atat.

Pas 6 -- ce face bootstrap-ul aici. In loc de formula normala (care presupune
distributie simetrica), reesantionam cele 5 valori cu inlocuire de B ori, luam
media fiecarui reesantion si citim cuantilele 2.5% si 97.5%. Pentru N=5 doar
5^5 = 3125 combinatii distincte exista, deci intervalul bootstrap e GRANULAR --
inca un semn ca 5 puncte spun putin. Codul (probabilitate_core.bootstrap_mean_ci)
face exact asta; demo_sil.py il ruleaza pe ~300 de pachete, unde intervalul e
ingust, ca sa se vada contrastul cu cazul N=5.

### 6. Vizualizare

`demo_sil.py` produce `fig_m01_lognormal_rtt.png` (daca matplotlib exista):
- panoul stang: histograma RTT (conditia loss_15 / DDS) cu densitatea lognormala
  fit-ata prin MLE suprapusa -- se vede coada lunga la dreapta si potrivirea;
- panoul drept: distributia bootstrap a mediei RTT cu marginile intervalului 95%.

### 7. Capcane

- Confunzi parametrii lognormalei: mu, sigma sunt pe scala log; media lui X e
  exp(mu+sigma^2/2), NU exp(mu) (acela e MEDIANA).
- Folosesti varianta MLE (/n) cand vrei estimatorul nedeplasat (/(n-1)). La N mare
  conteaza putin; la N=5 diferenta e ~20%.
- Tratezi RTT ca gaussian: media si intervalele simetrice mint pe o coada lunga.
  Fit pe log(RTT) sau bootstrap, nu formula normala.
- Confunzi intervalul de incredere (pe parametru) cu intervalul de predictie (pe
  o observatie noua) -- al doilea e mult mai larg.
- Bootstrap nu inventeaza informatie: la N=5 ramane granular si larg. Nu il citi
  ca pe o garantie; il citi ca pe o masura ONESTA a cat de putin stii.

### 8. De ce conteaza pentru teza

Coloana stiintifica a tezei compara rmw_zenoh vs rmw_cyclonedds sub degradare, la
N=5 repetitii per conditie. Exemplul numeric arata direct: un interval de ~+-23%
pe medie inseamna ca multe diferente raportate pot fi zgomot. De aceea modulul
insista pe (a) modelul corect al RTT (lognormal, nu gaussian), (b) MLE cu
constiinta biasului la N mic, si (c) bootstrap pentru a pune bare de eroare pe
fiecare cifra. Concluziile selectorului C1 (vezi CLAUDE.md) sunt deja formulate cu
aceasta prudenta: o diferenta isi merita locul doar daca depaseste incertitudinea.

ONESTITATE: toate datele din demo si exercitii sunt SINTETICE, semanate din
campania reala C1/M (vezi date_sar.py). Nu inlocuiesc masuratorile finale.

---

## Inchidere

### Checklist de stapanire (bifeaza daca poti...)
- [ ] sa scrii densitatile Bernoulli, gaussiana, lognormala fara sa le cauti;
- [ ] sa derivezi mu_hat si sigma2_hat prin anularea derivatei log-verosimilitatii;
- [ ] sa explici de ce numitorul MLE e n si cand preferi n-1;
- [ ] sa calculezi de mana media, varianta si un interval ~95% pe 5 numere;
- [ ] sa explici ce face bootstrap-ul si de ce ramane larg la N=5;
- [ ] sa legi MAP de regularizare (prior gaussian -> penalizare L2).

### Bibliografie (aprofundare, vezi BIBLIOGRAFIE.md)
- Bishop, PRML, cap. 1-2 (probabilitate, MLE, perspectiva bayesiana).
- Murphy, Probabilistic Machine Learning: Introduction, cap. 2-4.
- Deisenroth, Faisal, Ong, Mathematics for Machine Learning, cap. 6 (probabilitate).
- Efron & Tibshirani, An Introduction to the Bootstrap (referinta clasica bootstrap).
