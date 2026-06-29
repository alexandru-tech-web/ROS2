# M02 -- Optimizare pentru ML

> ONESTITATE: figurile si demo-ul folosesc date SINTETICE generate de
> `date_sar.make_latency_dataset`, semanate din campania reala C1 (p95 RTT si
> pierdere pentru DDS vs Zenoh sub tc netem). Nu sunt masuratori brute.

## Antet pedagogic

### Obiective de invatare
La finalul modulului poti:
1. **derivamatematic** gradientul unei pierderi patratice si sa il **verifici** cu diferente finite;
2. **implementa** coborarea pe gradient (GD), momentum si Adam in numpy pur;
3. **alege** rata de invatare si sa explici de ce un pas prea mare diverge;
4. **diagnostica** o problema prost conditionata si sa o repari (standardizare, momentum, Adam);
5. **aplica** oprirea timpurie (early stopping) ca regularizare implicita.

### Prerechizite
- M00 (algebra liniara: produs matrice-vector, valori proprii, matrice SPD).
- Calcul diferential elementar (derivate partiale, regula lantului).
- numpy de baza (vezi `utils.py`).

### Timp si dificultate
- Timp estimat: 3-4 ore (teorie + cod + exercitii).
- Dificultate: 2 / 3.

### Vocabular cheie (vezi GLOSAR.md)
- **gradient** -- vectorul derivatelor partiale; arata directia de crestere maxima.
- **convexitate** -- o functie e convexa daca segmentul dintre doua puncte sta deasupra graficului; orice minim local e global.
- **gradient descent (coborare pe gradient)** -- optimizare iterativa in directia -gradient.
- **SGD** -- varianta stochastica: gradient estimat pe un esantion / mini-lot.
- **momentum (moment)** -- inertie care acumuleaza directiile trecute, amortizeaza zigzagul.
- **Adam** -- pas adaptiv pe coordonata, cu momente de ordin 1 si 2 corectate de bias.
- **learning rate (rata de invatare)** -- marimea pasului `eta`.
- **conditionare** -- `kappa = lambda_max / lambda_min` al Hessianei; mare = problema 'dificila'.
- **early stopping (oprire timpurie)** -- opresti antrenarea cand pierderea de validare nu se mai imbunatateste.

---

## 1. Intuitie

Aproape orice model din acest curs se antreneaza la fel: scrii o **pierdere**
`L(w)` care masoara cat de gresit prezice modelul cu parametrii `w`, apoi
**cobori** spre minimul ei. Imagineaza-ti `L` ca un peisaj de dealuri; gradientul
`grad L(w)` arata in sus pe panta cea mai abrupta, deci un pas mic in directia
`-grad L(w)` te coboara. Repeta -> ajungi intr-o vale (un minim).

Cand `L` este **convexa** (o singura vale), coborarea pe gradient cu pas
suficient de mic gaseste minimul **global**. De aceea optimizarea este motorul
din spatele tuturor modelelor antrenate: regresia liniara, logistica, SVM,
retelele neuronale -- toate sunt 'scrie pierderea, calculeaza gradientul, coboara'.

## 2. Formalizare

**Pierderea patratica convexa (bancul de proba).** Lucram pe

    f(w) = 0.5 * w^T A w - b^T w

cu `A` simetrica si **pozitiv definita** (SPD: toate valorile proprii > 0).
Gradientul (vezi derivarea mai jos) este

    grad f(w) = A w - b

iar minimul, unde gradientul se anuleaza, are **forma inchisa**

    w* = A^{-1} b .

Stim raspunsul exact -> putem verifica daca optimizarea iterativa ajunge acolo.

**Coborarea pe gradient (GD).**

    w_{k+1} = w_k - eta * grad f(w_k)

`eta > 0` este rata de invatare. Pe patratica, GD converge daca si numai daca

    0 < eta < 2 / lambda_max(A) ,

iar pasul cel mai rapid este `eta* = 2 / (lambda_max + lambda_min)`.

**Conditionarea.** Numarul de conditionare `kappa = lambda_max(A) / lambda_min(A)`
controleaza viteza: rata de contractie a erorii pe pas (cu eta optim) este
`(kappa - 1) / (kappa + 1)`. La `kappa = 1` (vale rotunda) convergi intr-un pas;
la `kappa` mare (vale alungita) GD zigzagheaza si converge lent.

## 3. Derivare pas cu pas

Pornim de la `f(w) = 0.5 * w^T A w - b^T w`, cu `A = A^T`.

1. Termenul liniar: `d/dw (b^T w) = b`.
2. Termenul patratic: pentru `A` simetrica, `d/dw (0.5 * w^T A w) = A w`.
   (Pe componente: `d/dw_i (0.5 * sum_{jk} w_j A_{jk} w_k) = sum_k A_{ik} w_k = (A w)_i`,
   folosind `A_{ik} = A_{ki}`.)
3. Deci `grad f(w) = A w - b`.
4. La minim `grad f(w*) = 0` => `A w* = b` => `w* = A^{-1} b` (A inversabila fiindca SPD).

**Verificarea gradientului cu diferente finite.** Daca nu esti sigur ca ai
derivat corect, aproximeaza fiecare derivata partiala cu diferenta **centrata**:

    d f / d w_i ~ (f(w + h e_i) - f(w - h e_i)) / (2h)

unde `e_i` e versorul axei i. Eroarea formulei centrate scade ca `O(h^2)`, deci
la `h ~ 1e-5` diferenta fata de gradientul analitic e sub `1e-5`. Acesta este
testul standard de depanare a oricarui gradient scris de mana (folosit in selftest).

## 4. Algoritm (pseudocod)

```
GD(grad, w0, eta, n_iter):
    w <- w0
    repeta n_iter:
        w <- w - eta * grad(w)
    intoarce w

MOMENTUM(grad, w0, eta, mu, n_iter):   # heavy-ball
    w <- w0 ; v <- 0
    repeta n_iter:
        v <- mu * v - eta * grad(w)
        w <- w + v
    intoarce w

ADAM(grad, w0, alpha, b1, b2, eps, n_iter):
    w <- w0 ; m <- 0 ; v <- 0
    pentru t = 1..n_iter:
        g <- grad(w)
        m <- b1*m + (1-b1)*g          # momentul 1 (medie)
        v <- b2*v + (1-b2)*g^2        # momentul 2 (medie patrate)
        m_hat <- m / (1 - b1^t)       # corectie de bias
        v_hat <- v / (1 - b2^t)
        w <- w - alpha * m_hat / (sqrt(v_hat) + eps)
    intoarce w

SGD(grad_i, w0, n, eta, n_epochs):     # gradient pe un esantion
    w <- w0
    pentru fiecare epoca:
        pentru i intr-o permutare a {0..n-1}:
            w <- w - eta * grad_i(w, i)
    intoarce w
```

## 5. EXEMPLU LUCRAT NUMERIC (calculat de mana)

Luam o patratica **diagonala** 2D (asa vedem direct efectul conditionarii):

    A = [[2, 0],        b = [2, 8]
         [0, 8]]

**Minimul analitic.** `w* = A^{-1} b = (b_1 / 2, b_2 / 8) = (1, 1)`.
Valoarea minima: `f(w*) = 0.5 * w*^T A w* - b^T w* = 0.5*(2 + 8) - (2 + 8) = -5`.

**Conditionarea.** Valorile proprii sunt 2 si 8 (diagonala), deci
`kappa = 8 / 2 = 4`. Pasul cel mai rapid ar fi `eta* = 2/(2+8) = 0.2`.

**Verificarea gradientului prin diferente finite** (la un punct oarecare,
`w = (2, 0.5)`, ca sa nu fie chiar minimul). Gradient analitic:
`grad f(w) = A w - b = (2*2 - 2, 8*0.5 - 8) = (2, -4)`.
Cu `h = 1e-4`, `f(w) = -3`:
- componenta 0: `f(2+h, 0.5) = -2.99979999`, `f(2-h, 0.5) = -3.00019999`,
  diferenta centrata `= (-2.99979999 - (-3.00019999)) / (2*1e-4) = 2.0`. Se potriveste.
- componenta 1: `f(2, 0.5+h) = -3.00039996`, `f(2, 0.5-h) = -2.99959996`,
  diferenta centrata `= (-3.00039996 - (-2.99959996)) / (2*1e-4) = -4.0`. Se potriveste.

**Cativa pasi de GD** cu `eta = 0.1`, pornind din `w0 = (0, 0)`:

| iter | w               | grad = A w - b      | f(w)     |
|------|-----------------|---------------------|----------|
| 0    | (0.000, 0.000)  | (-2.00, -8.00)      |  0.00000 |
| 1    | (0.200, 0.800)  | (-1.60, -1.60)      | -4.20000 |
| 2    | (0.360, 0.960)  | (-1.28, -0.32)      | -4.58400 |
| 3    | (0.488, 0.992)  | (-1.024, -0.064)    | -4.73760 |
| 4    | (0.590, 0.998)  | (-0.819, -0.013)    | -4.83222 |

Verificare iteratia 1: `w1 = w0 - 0.1 * grad(w0) = (0,0) - 0.1*(-2,-8) = (0.2, 0.8)`.
Observa **conditionarea in actiune**: coordonata 2 (panta abrupta,
`lambda = 8`) ajunge aproape de 1 din primul pas, dar coordonata 1 (panta lina,
`lambda = 2`) se tarie incet -- exact zigzagul prezis de `kappa = 4`. Dupa 200 de
iteratii `w = (1.000000, 1.000000) = w*`. Momentum si Adam ajung in aceeasi vale,
dar mai repede pe coordonata lenta.

## 6. Vizualizare (referinta la demo_sil)

Ruleaza `demo_sil.py`. Produce:
- **fig_convergenta.png** -- pierderea (scala log) vs iteratie pentru GD si Adam pe
  o regresie de latenta (prezice `log(rtt_ms)`). Vezi cum scade pierderea si compara
  pantele celor doi optimizatori.
- **fig_predictie.png** -- predictie vs adevar pe setul de test.

Demo-ul tipareste si numarul de conditionare al `X^T X / n` **inainte** si **dupa**
standardizare: brut `kappa ~ 1.2e5`, standardizat `kappa ~ 7`. Aceeasi problema,
de zeci de mii de ori mai usoara dupa o simpla scalare -- de aici insistenta din
M04 pe standardizare.

## 7. Capcane

- **Pas prea mare** (`eta > 2/lambda_max`): GD **diverge** (pierderea explodeaza).
  Selftestul nucleului verifica explicit acest caz.
- **Pas prea mic**: converge corect, dar lent (irositi iteratii / timp).
- **Probleme prost conditionate** (`kappa` mare): GD pur zigzagheaza. Remedii:
  standardizeaza trasaturile (scade `kappa`), foloseste momentum sau Adam.
- **Adam nu inseamna 'mereu mai bun'**: pe o patratica bine conditionata, GD cu pas
  optim poate fi mai rapid (vezi demo: la conditionare buna GD ajunge la prag in
  ~5 iteratii). Adam straluceste cand scarile coordonatelor difera mult.
- **Verificarea gradientului**: foloseste diferente **centrate** (O(h^2)), nu
  inainte (O(h)); `h` prea mic -> eroare de rotunjire, prea mare -> eroare de trunchiere.
- **Early stopping**: returneaza CEL MAI BUN `w` de pe validare, nu ultimul.

## 8. De ce conteaza pentru teza

Optimizarea este **motorul comun** al fiecarui model antrenat in restul cursului
si al tezei: selectorul link-aware (C1/C3), regresiile de latenta, clasificatorul
de utilizabilitate a legaturii (M08). Cand un model 'nu invata', cauza e aproape
mereu aici: pas gresit, date nestandardizate (conditionare proasta), sau un
gradient derivat gresit. Verificarea gradientului cu diferente finite si
diagnosticul de conditionare din acest modul sunt uneltele cu care depanezi orice
antrenare ulterioara. Onest: la N mic (C1 are N=5), un optimizator mai sofisticat
NU compenseaza lipsa de date -- el doar gaseste mai repede acelasi minim.

---

## Checklist de stapanire

Bifeaza daca poti:
- [ ] sa derivezi `grad f(w) = A w - b` pentru `f(w) = 0.5 w^T A w - b^T w`;
- [ ] sa verifici un gradient cu diferente finite centrate si sa explici de ce `O(h^2)`;
- [ ] sa scrii GD, momentum si Adam din memorie in numpy;
- [ ] sa spui pragul de convergenta al GD (`eta < 2/lambda_max`) si pasul optim;
- [ ] sa explici ce este conditionarea si cum o repari (standardizare / momentum / Adam);
- [ ] sa implementezi early stopping si sa spui de ce e o forma de regularizare.

## Bibliografie (aprofundare)

- Boyd, Vandenberghe -- *Convex Optimization* (PDF gratuit, Stanford). Convexitate,
  conditii de optimalitate, metode de gradient. Referinta principala M02.
- Deisenroth, Faisal, Ong -- *Mathematics for Machine Learning* (mml-book.com),
  cap. 7 (optimizare continua). Derivari de gradient, pas si conditionare.
- Kingma, Ba -- *Adam: A Method for Stochastic Optimization* (arXiv:1412.6980),
  articolul original Adam.
- Goodfellow, Bengio, Courville -- *Deep Learning* (deeplearningbook.org), cap. 8
  (optimizare pentru antrenarea modelelor), pentru SGD si momentum.
