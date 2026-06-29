# M05 -- Regresie liniara

## Antet pedagogic

### Obiective de invatare
La finalul modulului poti:
- **deriva** ecuatiile normale `w = (X^T X)^{-1} X^T y` din minimizarea lui `||Xw - y||^2`;
- **implementa** regresia liniara de la zero, in numpy, prin solutie inchisa SI prin coborare pe gradient;
- **explica** ipotezele modelului liniar si ce se intampla cand sunt incalcate;
- **diagnostica** problemele de conditionare (coliniaritate, scari diferite) si a le repara prin standardizare;
- **evalua** un model de regresie cu RMSE si R^2 fata de o baza si a-l aplica la predictia `rtt_ms` din feature-uri de retea.

### Prerechizite
- M00 (algebra liniara: produs matriceal, transpusa, inversa, valori singulare).
- M02 (optimizare: gradient, conditie de optim, coborare pe gradient).
- M03 (invatare supervizata: risc empiric, train/test, supra-/sub-invatare).

### Timp si dificultate
- Timp estimat: 90-120 min (citire + exemplul numeric de mana + exercitii).
- Dificultate: 2 / 3.

### Vocabular cheie (vezi GLOSAR.md)
- **feature** (trasatura) -- variabila de intrare; aici `base_lat_ms`, `loss_pct`, `distance_m`, middleware.
- **target / label** (tinta) -- variabila prezisa; aici `rtt_ms` (sau `log10(rtt_ms)`).
- **loss function** (functie de pierdere) -- aici eroarea patratica `||Xw - y||^2`.
- **empirical risk** (risc empiric) -- pierderea medie pe datele observate; o minimizam (ERM).
- **gradient descent** (coborare pe gradient) -- optimizare iterativa in directia `-gradient`.
- **learning rate** (rata de invatare) -- marimea pasului `alpha` in coborarea pe gradient.
- **regularization** (regularizare) -- termen ridge mic care stabilizeaza solutia (detaliat in M06).
- Termeni proprii acestui modul (nu inca in GLOSAR):
  - **ecuatii normale** -- sistemul liniar `(X^T X) w = X^T y` care da minimul patratic;
  - **matrice de design** `X` -- randuri = exemple, coloane = feature-uri (+ coloana de bias);
  - **numar de conditie** -- `cond(X^T X) = (sigma_max / sigma_min)^2`; mare = problema instabila.

---

## Corp

### 1. Intuitie
Vrem o linie (in mai multe dimensiuni, un hiperplan) care trece cat mai aproape de
nori de puncte `(x_i, y_i)`. 'Cat mai aproape' inseamna: suma patratelor distantelor
verticale (rezidualele) sa fie minima. De ce patrate si nu valoare absoluta? Pentru
ca patratul e neted (derivabil peste tot) si duce la o solutie inchisa, eleganta,
printr-un singur sistem liniar. Geometric, predictia `Xw` este **proiectia
ortogonala** a lui `y` pe subspatiul generat de coloanele lui `X`; rezidualul
`y - Xw` este perpendicular pe acel subspatiu -- exact ce spun ecuatiile normale.

### 2. Formalizare
Avem `n` exemple, fiecare cu `d` feature-uri. Matricea de design `X` are forma
`(n, d+1)`: prima coloana e plina de `1` (interceptul / bias), restul sunt feature-urile.
Vectorul de parametri este `w` de lungime `d+1`. Predictia:

    y_hat = X w        (y_hat are forma (n,))

Functia de pierdere (suma patratelor reziduurilor), in notatie de norma euclidiana:

    J(w) = || X w - y ||^2 = (X w - y)^T (X w - y)

Cautam `w* = argmin_w J(w)`. Este o functie patratica convexa in `w`, deci are un
minim global unic (cand `X^T X` e inversabila).

### 3. Derivare pas cu pas (ecuatiile normale)
Dezvoltam patratul:

    J(w) = w^T X^T X w - 2 y^T X w + y^T y

Gradientul fata de `w` (folosind `d/dw (w^T A w) = 2 A w` pentru `A` simetrica si
`d/dw (b^T w) = b`):

    nabla_w J = 2 X^T X w - 2 X^T y

Conditia de optim `nabla_w J = 0`:

    2 X^T X w - 2 X^T y = 0
    (X^T X) w = X^T y                 <-- ECUATIILE NORMALE
    w = (X^T X)^{-1} X^T y            <-- solutia inchisa (daca X^T X inversabila)

Nota practica: NU calculam inversa explicit. Rezolvam direct sistemul
`(X^T X) w = X^T y` (in cod: `numpy.linalg.solve`), mai stabil si mai rapid.

### 4. Derivare pas cu pas (coborare pe gradient)
Cand `d` e mare sau `X^T X` e prost conditionata, iteram in loc sa rezolvam direct.
Pe pierderea **medie** patratica `(1/n) ||Xw - y||^2`, gradientul este

    grad = (2/n) X^T (X w - y)

si actualizam

    w <- w - alpha * grad

unde `alpha` e rata de invatare. Pe feature-uri standardizate (z-score), curbura e
echilibrata si `alpha ~ 0.1-0.3` converge in cateva mii de pasi spre ACEEASI
solutie ca ecuatiile normale. Oprire: `||grad|| < tol` sau dupa un numar maxim de pasi.

### 5. Algoritm (pseudocod)
```
ECUATII NORMALE:
  intrare: X (n, d+1) cu bias, y (n,)
  A <- X^T X ;  b <- X^T y
  w <- solve(A, b)            # NU inversa explicita
  intoarce w

GRADIENT DESCENT:
  intrare: X, y, alpha, n_iter, tol
  w <- 0
  repeta de n_iter ori:
    resid <- X w - y
    grad  <- (2/n) X^T resid
    daca ||grad|| < tol: opreste
    w <- w - alpha * grad
  intoarce w
```

### 6. EXEMPLU LUCRAT NUMERIC (de mana)
Patru puncte, un singur feature `x`. Vrem `y_hat = w0 + w1 * x`.

    x: [1, 2, 3, 4]
    y: [2, 2, 4, 4]

Matricea de design cu bias si tinta:

    X = [[1, 1],      y = [2,
         [1, 2],           2,
         [1, 3],           4,
         [1, 4]]           4]

Pasul 1 -- `X^T X` (matrice 2x2):

    X^T X = [[ sum 1 ,  sum x  ],   = [[ 4 , 10 ],
             [ sum x ,  sum x^2 ]]      [ 10 , 30 ]]

  (sum 1 = 4; sum x = 1+2+3+4 = 10; sum x^2 = 1+4+9+16 = 30).

Pasul 2 -- `X^T y`:

    X^T y = [ sum y , sum x*y ] = [ 12 , 34 ]

  (sum y = 2+2+4+4 = 12; sum x*y = 1*2 + 2*2 + 3*4 + 4*4 = 2+4+12+16 = 34).

Pasul 3 -- rezolva `(X^T X) w = X^T y`. Determinantul:

    det = 4*30 - 10*10 = 120 - 100 = 20

Inversa:

    (X^T X)^{-1} = (1/20) * [[ 30 , -10 ],
                             [ -10 ,  4 ]]

Pasul 4 -- `w = (X^T X)^{-1} X^T y`:

    w0 = (1/20) * ( 30*12 + (-10)*34 ) = (1/20) * (360 - 340) = 20/20 = 1.0
    w1 = (1/20) * ( -10*12 +   4 *34 ) = (1/20) * (-120 + 136) = 16/20 = 0.8

Deci `y_hat = 1.0 + 0.8 * x`. Verificare: predictiile sunt `[1.8, 2.6, 3.4, 4.2]`,
reziduurile `[0.2, -0.6, 0.6, -0.2]`. Suma reziduurilor = 0 (proprietate cu intercept)
si suma `x_i * resid_i = 1*0.2 + 2*(-0.6) + 3*0.6 + 4*(-0.2) = 0.2 -1.2 +1.8 -0.8 = 0`
-- exact ortogonalitatea pe care o cer ecuatiile normale. SS_res = 0.2^2 + 0.6^2 +
0.6^2 + 0.2^2 = 0.8; media lui y = 3, SS_tot = 1+1+1+1 = 4, deci
R^2 = 1 - 0.8/4 = 0.8.

Acest caz e codificat in `_selftest()` din `regresie_liniara_core.py` (cazul
`y = 1 + 2x` fara zgomot da `w = [1, 2]` exact; tot acolo se verifica si
echivalenta cu gradient descent).

### 7. Vizualizare
`demo_sil.py` produce `fig_pred_vs_real.png` cu doua panouri:
- **stanga**: prezis vs real pe scara `log10(rtt_ms)`, cu dreapta identitate -- cat
  de aproape cad punctele de diagonala arata cat de bun e modelul (R^2_log raportat);
- **dreapta**: bare RMSE [ms], model liniar vs baza (prezice media) -- modelul trebuie
  sa fie clar mai jos decat baza.

### 8. Capcane
- **Inversa explicita**: `np.linalg.inv(X.T @ X)` e instabila si lenta; foloseste `solve`.
- **Scari diferite intre feature-uri**: fac `X^T X` prost conditionata; GD oscileaza.
  Remediu: standardizare (in demo: numar de conditie scade de la ~1e5 la ~1.4).
- **Coliniaritate** (feature-uri aproape dependente): `X^T X` aproape singulara,
  coeficienti uriasi si instabili. Un termen ridge mic (M06) o repara.
- **Tinta puternic ne-gaussiana**: `rtt_ms` are cozi lungi; pe scara liniara un model
  liniar se potriveste prost. Prezicem `log10(rtt_ms)` -- pierderea patratica e mult
  mai potrivita pe scara logaritmica. (In demo, R^2 pe scara log >> R^2 pe scara ms.)
- **Scurgere de date**: standardizeaza cu media/abaterea de pe TRAIN, niciodata pe tot
  setul. `utils.standardize(Xtr, Xte)` face exact asta.

### 9. De ce conteaza pentru teza
Vrem sa anticipam calitatea legaturii: cat de mare va fi `rtt_ms` sub o anumita
degradare `netem` (latenta de baza, pierdere) si la o anumita distanta, pentru fiecare
middleware (DDS vs Zenoh). Un model liniar pe `log10(rtt_ms)` da o prima regula
interpretabila: semnul si marimea coeficientilor standardizati spun ce feature
imping RTT-ul in sus (pierderea domina, apoi latenta de baza). Este baza peste care
modulele urmatoare adauga regularizare (M06), validare corecta la N mic (M07) si,
pentru decizia binara 'link utilizabil', regresia logistica (M08).

---

## Inchidere

### Checklist de stapanire (bifeaza daca poti...)
- [ ] sa derivezi ecuatiile normale din `nabla_w ||Xw - y||^2 = 0`;
- [ ] sa explici de ce rezolvam sistemul in loc sa inversam explicit;
- [ ] sa scrii pasul de gradient descent si sa spui de ce standardizarea il accelereaza;
- [ ] sa calculezi de mana `w` pentru un caz mic (exemplul cu 4 puncte);
- [ ] sa interpretezi numarul de conditie si sa spui ce-l reduce;
- [ ] sa raportezi RMSE si R^2 fata de o baza si sa decizi daca modelul ajuta.

### Trimiteri (vezi BIBLIOGRAFIE.md)
- ESL (Hastie, Tibshirani, Friedman), cap. 3 -- metode liniare pentru regresie.
- ISL (James et al.), cap. 3 -- regresie liniara cu laburi.
- MML (Deisenroth et al.) -- algebra liniara si minime patratice (fundament M00-M02).

> ONESTITATE: toate datele folosite in demo si exercitii sunt SINTETICE, semanate
> din campania reala C1/M prin `date_sar.py`. Nu sunt masuratori brute -- servesc
> invatarii (semnal realist, reproductibil). Inainte de orice cifra in teza,
> reface pe date de campanie reale.
