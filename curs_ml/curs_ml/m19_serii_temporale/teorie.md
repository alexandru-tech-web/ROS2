# M19 -- Serii temporale

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa formalizezi un proces autoregresiv AR(p) si sa explici de ce e o regresie
  liniara pe lag-uri;
- sa derivezi si sa implementezi potrivirea AR prin cele mai mici patrate pe o
  matrice de feature-uri din fereastra glisanta;
- sa faci un split TEMPORAL corect (fara look-ahead, fara amestecare) si sa
  evaluezi cauzal o prognoza;
- sa compari onest un model AR cu baza de persistenta (random walk) si sa
  recunosti capcanele (scurgere temporala, nestationaritate).

Prerechizite: M05 (regresie liniara, cele mai mici patrate), M07 (evaluare si
validare, scurgere de date). Timp estimat: 2-3 h. Dificultate: 2/3.

Vocabular cheie (vezi GLOSAR.md): serie temporala, autoregresie AR(p),
coeficient phi, lag, fereastra glisanta, persistenta (random walk), split
temporal, look-ahead / scurgere temporala, prognoza un-pas / multi-pas,
stationaritate.

## 1. Intuitie (anticiparea traiectoriei)

O serie temporala e o secventa de valori ordonate in timp: x_0, x_1, ..., x_{n-1}.
Spre deosebire de un set de exemple independente (i.i.d.), aici ordinea conteaza
si valorile invecinate sunt corelate -- ce s-a intamplat adineauri spune ceva
despre ce urmeaza. RTT-ul unei legaturi de retea nu sare aleator: daca ultima
intarziere a fost mare, urmatoarea tinde sa fie tot mare (cozile se golesc
treptat). A anticipa traiectoria inseamna a folosi trecutul RECENT ca sa prezici
viitorul imediat.

Cel mai simplu mod de a 'anticipa' e persistenta: ghiceste ca x_t = x_{t-1}
(maine ca azi). E o baza surprinzator de tare. Un model util trebuie sa o BATA.
Autoregresia o generalizeaza: in loc sa copieze ultima valoare, invata o
combinatie liniara a ultimelor p valori.

## 2. Formalizare: AR(p)

Un proces autoregresiv de ordin p:

    x_t = c + phi_1 x_{t-1} + phi_2 x_{t-2} + ... + phi_p x_{t-p} + eps_t

unde c este interceptul (nivelul), phi_1..phi_p sunt coeficientii de
autoregresie, iar eps_t este zgomot (medie zero, varianta sigma^2). p este cat
de departe in trecut ne uitam (memoria modelului).

Cazuri particulare:
- AR(1): x_t = c + phi_1 x_{t-1} + eps_t. Daca |phi_1| < 1, procesul e stationar
  si revine spre media c / (1 - phi_1). phi_1 -> 1 inseamna persistenta puternica
  (random walk in limita phi_1 = 1, c = 0).
- Persistenta (random walk) e cazul degenerat c = 0, phi_1 = 1, restul 0:
  prognoza = ultima valoare.

## 3. Fereastra glisanta de feature-uri

Transformam seria intr-o problema de regresie supervizata obisnuita. Pentru
fiecare moment t >= p construim un rand de feature-uri din ultimele p valori si
o tinta:

    rand t:   x_t  <-  [ x_{t-1}, x_{t-2}, ..., x_{t-p} ]   (cel mai recent lag pe coloana 0)

Asezate, dau matricea de design X de forma (n - p, p) si vectorul tinta y de
lungime n - p. CRUCIAL: fiecare rand foloseste DOAR valori STRICT anterioare
tintei sale -- niciun feature din viitor. Asta e codul din `make_lag_features`.

Exemplu de forme: serie de lungime n = 10, p = 3 -> X are 7 randuri si 3 coloane,
y are 7 elemente. Primul rand (t = 3) e [x_2, x_1, x_0] cu tinta x_3.

## 4. Derivare: potrivirea AR prin cele mai mici patrate

Adaugam o coloana de 1 (interceptul) la X, obtinand matricea Phi = [1 | lag-uri],
si parametrul beta = [c, phi_1, ..., phi_p]^T. Cautam beta care minimizeaza suma
patratelor reziduurilor:

    J(beta) = || y - Phi beta ||^2 = sum_t ( x_t - c - sum_i phi_i x_{t-i} )^2

Aceasta e EXACT problema celor mai mici patrate din M05, doar ca feature-urile
sunt lag-uri ale aceleiasi serii. Derivand si anuland gradientul:

    d J / d beta = -2 Phi^T (y - Phi beta) = 0
    =>  Phi^T Phi beta = Phi^T y                 (ecuatiile normale)
    =>  beta_hat = (Phi^T Phi)^{-1} Phi^T y

In cod rezolvam stabil cu `np.linalg.lstsq` (nu inversam explicit). Asta e tot ce
face `fit_ar`: o regresie liniara pe lag-uri. (Pentru AR(1) FARA intercept, panta
se reduce la phi = sum(x_{t-1} x_t) / sum(x_{t-1}^2) -- vezi exemplul numeric.)

## 5. Validare incrucisata TEMPORALA (fara look-ahead, fara amestecare)

La date i.i.d. (M07) amestecam si impartim k-fold. La serii temporale asta e
GRESIT: a amesteca inseamna a antrena pe viitor si a testa pe trecut (scurgere
temporala / look-ahead), iar scorul iese fals de bun. Regula de fier:

- NU amesteca. Pastreaza ordinea cronologica.
- Antreneaza pe un PREFIX (primele train_frac), testeaza pe SUFIXul de dupa.
- Garanteaza max(index_train) < min(index_test): tot ce e in test e STRICT dupa
  tot ce e in train.

`temporal_split` face exact asta. Pentru mai multe falduri (rolling / expanding
window) sklearn ofera TimeSeriesSplit, care respecta aceeasi regula
(verificat in `serii_temporale_sklearn.py`).

## 6. Evaluare cauzala

Prognoza un-pas: pentru fiecare punct de test x_t prezicem din valorile REALE
anterioare (nu din propriile noastre predictii). RMSE-ul peste test masoara cat
de bine anticipam pasul urmator. Comparam mereu cu PERSISTENTA: daca AR nu bate
random walk-ul, modelul nu si-a meritat complexitatea.

Prognoza multi-pas (orizont > 1) e RECURSIVA: rebagam valorile prezise ca lag-uri
pentru pasii urmatori. Eroarea se acumuleaza cu orizontul -- onestitate: prognoza
la 10 pasi e mult mai slaba decat la 1 pas.

## 7. Algoritm (pseudocod)

```
make_lag_features(x, p):
  pentru t = p..n-1: rand = [x[t-1], x[t-2], ..., x[t-p]] ; tinta = x[t]
  intoarce X (n-p, p), y (n-p)

fit_ar(x, p):
  X, y = make_lag_features(x, p)
  Phi  = [coloana de 1 | X]
  beta = lstsq(Phi, y)            # ecuatiile normale, stabil
  intoarce c = beta[0], phi = beta[1:]

evaluare(x, p, train_frac):
  train, test = temporal_split(x, train_frac)   # max(idx_train) < min(idx_test)
  c, phi = fit_ar(train, p)
  pentru fiecare t in test: pred = c + phi . [valori reale anterioare]
  RMSE_AR = rmse(test, pred)
  RMSE_persistenta = rmse(test, valoarea reala anterioara)
  AR e util daca RMSE_AR < RMSE_persistenta
```

## 8. Exemplu lucrat numeric (verifica-l de mana)

Serie scurta de 5 puncte (descrestere geometrica curata, deci AR(1) cu phi = 0.8,
fara intercept):

    x = [10.00, 8.00, 6.40, 5.12, 4.10]

(a) Estimam phi pentru AR(1) FARA intercept din cele 4 perechi consecutive
    (x_{t-1}, x_t):

    (10.00, 8.00), (8.00, 6.40), (6.40, 5.12), (5.12, 4.10)

    Formula celor mai mici patrate fara intercept:
        phi = sum(x_{t-1} x_t) / sum(x_{t-1}^2)

    Numarator: 10*8 + 8*6.4 + 6.4*5.12 + 5.12*4.10
             = 80 + 51.20 + 32.768 + 20.992 = 184.96
    Numitor:   10^2 + 8^2 + 6.4^2 + 5.12^2
             = 100 + 64 + 40.96 + 26.2144 = 231.1744
    phi = 184.96 / 231.1744 = 0.8001

    Recuperam phi ~ 0.80, exact panta de generare (descresterea cu 20% pe pas).

(b) Prognoza un-pas pentru x_5 din x_4 = 4.10:
        x_5_hat = phi * x_4 = 0.8001 * 4.10 = 3.28

(c) Persistenta ar fi prezis x_5_hat = x_4 = 4.10. Valoarea reala continua
    seria spre 4.10 * 0.8 = 3.28, deci AR (3.28) bate persistenta (4.10):
    eroarea AR e ~0, a persistentei ~0.82.

(Selftest-ul nucleului recupereaza phi pe procese AR(1)/AR(2) lungi sub toleranta
0.05; exercitiul E2 reproduce formula de mana de mai sus.)

## 9. Vizualizare

`demo_sil.py` produce `fig_prognoza_rtt.png`: seria reala de RTT (train + test) cu
prognoza AR un-pas si baza de persistenta suprapuse pe portiunea de test. AR
urmareste seria cu un decalaj mic; persistenta intarzie un pas intreg. Pe seria de
latenta (conditie loss_15) AR bate persistenta cu ~11% RMSE. Date SINTETICE.

## 10. Capcane frecvente

- Look-ahead / scurgere temporala: a amesteca seria sau a standardiza pe tot setul
  inainte de split baga viitorul in train. Foloseste split temporal, statistici
  doar de pe train. (Greseala clasica reluata din M07, dar mortala la serii.)
- A nu compara cu persistenta: o prognoza poate parea buna in absolut, dar daca nu
  bate random walk-ul nu spune nimic. Persistenta e baza obligatorie.
- Nestationaritate: AR presupune statistici stabile in timp (medie, varianta). Daca
  seria are trend sau salturi de regim (un spike de pierdere care muta nivelul),
  un AR fix se potriveste prost. Remediu uzual: diferentiere (modeleaza x_t -
  x_{t-1}) sau ferestre care se re-potrivesc.
- Prognoza multi-pas vazuta ca un-pas: eroarea se acumuleaza recursiv; nu raporta
  un RMSE de orizont 1 ca si cum ar tine la orizont 10.

## 11. De ce conteaza pentru teza

Latenta in mesh-ul de teleoperare nu e statica: variaza in timp cu cozile,
distanta si evenimentele de pierdere. A ANTICIPA latenta urmatorului interval (nu
doar a o masura post-factum) deschide adaptarea proactiva: comuta RMW, ajusteaza
rata de telemetrie sau previne o incalcare de deadline INAINTE sa se intample.
Un AR un-pas peste o fereastra de RTT e cel mai simplu predictor onest -- iar
metodologia (split temporal, comparatie cu persistenta) e exact disciplina pe
care campaniile mele o cer ca sa nu raportez optimist.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa scrii ecuatia AR(p) si sa explici fiecare termen;
- [ ] sa construiesti matricea de lag-uri din fereastra glisanta (formele corecte);
- [ ] sa derivezi ecuatiile normale ale potrivirii AR si sa estimezi phi de mana;
- [ ] sa faci un split temporal fara look-ahead si sa argumentezi de ce amestecarea e gresita;
- [ ] sa compari AR cu persistenta si sa decizi daca modelul e util.

## Mergi mai departe

Hamilton, Time Series Analysis, cap. 1-3 (AR/MA/ARMA). Hyndman & Athanasopoulos,
Forecasting: Principles and Practice (cap. despre regresie pe lag-uri si
backtesting). Vezi BIBLIOGRAFIE.md.
