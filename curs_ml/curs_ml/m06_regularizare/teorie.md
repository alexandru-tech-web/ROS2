# M06 -- Regularizare

## Antet pedagogic

Obiective de invatare. La final vei putea:
- sa explici de ce regularizarea ajuta la N mic (compromisul bias-varianta);
- sa derivezi solutia inchisa Ridge si sa o calculezi;
- sa implementezi Lasso prin coordinate descent cu soft-thresholding;
- sa alegi intre Ridge (micsorare) si Lasso (selectie de feature) dupa scop.

Prerechizite: M05 (regresie liniara, ecuatii normale), M03 (bias-varianta),
M02 (optimizare). Timp estimat: 3 h. Dificultate: 2/3.

Vocabular cheie (vezi GLOSAR.md): regularizare, Ridge (L2), Lasso (L1), Elastic
Net, micsorare (shrinkage), sparsitate, soft-threshold, multicoliniaritate.

## 1. Intuitie

La putine date sau feature-uri corelate, cele mai mici patrate (OLS) dau
coeficienti mari, instabili, care urmeaza zgomotul (varianta mare -- M03).
Regularizarea adauga o penalizare pe marimea coeficientilor: accepta un bias mic
in schimbul unei variante mult mai mici. Ridge ii micsoreaza neted; Lasso ii poate
aduce la EXACT zero, facand si selectie de feature.

## 2. Formalizare

Minimizam o pierdere penalizata:

    Ridge:  J(w) = ||X w - y||^2 + lam * ||w||_2^2
    Lasso:  J(w) = (1/2) ||X w - y||^2 + lam * ||w||_1

cu lam >= 0 parametrul de regularizare. CONVENTIE in nucleu: X standardizat
(coloane medie 0, abatere 1) si y centrat (medie 0), deci nu penalizam un intercept
si toti coeficientii sunt pe aceeasi scara (altfel penalizarea ar fi nedreapta
intre feature-uri cu unitati diferite).

Elastic Net combina ambele: pen(w) = alpha*||w||_1 + (1-alpha)*||w||_2^2, util cand
feature-urile sunt corelate in grup.

## 3. Derivare

### 3.1 Ridge -- solutie inchisa

J(w) = (Xw - y)^T (Xw - y) + lam w^T w. Gradientul:

    dJ/dw = 2 X^T (X w - y) + 2 lam w = 0
    => (X^T X + lam I) w = X^T y
    => w_ridge = (X^T X + lam I)^{-1} X^T y.

Termenul lam I face matricea STRICT pozitiv definita (inversabila) chiar cand X^T X
e singulara (feature-uri coliniare) -- de aici stabilitatea numerica.

### 3.2 Lasso -- coordinate descent

||w||_1 nu e diferentiabila in 0, deci nu exista forma inchisa. Optimizam pe rand
fiecare coordonata w_j, tinand restul fixate. Notand reziduul partial
r_j = y - X w + w_j x_j si rho_j = x_j^T r_j, subproblema pe w_j este

    min_{w_j} (1/2) (||x_j||^2 w_j^2 - 2 rho_j w_j) + lam |w_j|

a carei solutie e operatorul de prag moale:

    w_j = soft_threshold(rho_j, lam) / ||x_j||^2,
    soft_threshold(z, g) = sign(z) * max(|z| - g, 0).

Pragul moale taie la zero orice corelatie sub lam -> de aici sparsitatea. Geometric:
bila L1 are colturi pe axe, iar contururile pierderii ating intai un colt (un
coeficient = 0), spre deosebire de bila L2 (rotunda, fara colturi).

## 4. Algoritm

```
Ridge(X, y, lam):  rezolva (X^T X + lam I) w = X^T y
Lasso(X, y, lam):  w <- 0
  repeta pana la convergenta:
    pentru fiecare j:
      rho_j <- x_j^T (y - X w + w_j x_j)
      w_j   <- soft_threshold(rho_j, lam) / (x_j^T x_j)
```

## 5. Exemplu lucrat numeric (verifica-l de mana)

(a) Micsorarea Ridge intr-o dimensiune. Fie un singur feature standardizat cu
    x^T x = 10 si x^T y = 20. Atunci:
      OLS:            w = 20 / 10 = 2.0
      Ridge(lam=10):  w = 20 / (10 + 10) = 1.0   (micsorat la jumatate)
      Ridge(lam=90):  w = 20 / (10 + 90) = 0.2   (micsorat puternic)
    Coeficientul scade monoton spre 0 cand lam creste, dar nu atinge EXACT 0.

(b) Soft-threshold (inima Lasso).
      soft_threshold(5, 2)  = sign(5)*max(5-2,0)  = 3
      soft_threshold(-5, 2) = sign(-5)*max(5-2,0) = -3
      soft_threshold(1, 2)  = sign(1)*max(1-2,0)  = 0   (sub prag -> EXACT 0)
    Asa apare sparsitatea: corelatiile mici (sub lam) devin zero exact.

(Selftest-ul nucleului verifica exact aceste valori si contrastul Ridge fara
zerouri vs Lasso cu zerouri.)

## 6. Vizualizare

`demo_sil.py` traseaza coeficientii vs lambda pe feature-uri de latenta
(`fig_trasee_coef.png`): la Ridge toate curbele se apropie neted de 0; la Lasso
curbele ating 0 una cate una (selectie de feature). Date SINTETICE.

## 7. Capcane frecvente

- A regulariza feature-uri NESTANDARDIZATE: penalizarea favorizeaza nedrept
  feature-urile cu valori mari. Standardizeaza intai.
- A penaliza interceptul: deplaseaza predictia; de obicei se exclude (aici y centrat).
- A confunda lam-ul Ridge cu cel Lasso: scari si conventii diferite (vezi maparea
  alpha = lam/n in `regularizare_sklearn.py`).
- A crede ca lam mai mare = mereu mai bun: prea mult bias -> sub-invatare. lam se
  alege prin validare (M07).

## 8. De ce conteaza pentru teza

La N=5 (campania C1), OLS pe multe feature-uri de telemetrie supra-invata.
Regularizarea e indispensabila: Ridge stabilizeaza predictia de latenta, iar Lasso
spune CARE feature-uri de link conteaza cu adevarat (selectie pe care o pot
justifica intr-un articol). Leaga direct de selectia de model din M18.

## Verificare a stapanirii

Bifeaza daca poti:
- [ ] sa derivezi w_ridge = (X^T X + lam I)^{-1} X^T y;
- [ ] sa explici de ce lam I face matricea inversabila;
- [ ] sa calculezi soft_threshold pe un caz mic;
- [ ] sa explici geometric de ce L1 da sparsitate iar L2 nu;
- [ ] sa alegi Ridge vs Lasso dupa scop (stabilitate vs selectie).

## Mergi mai departe

ESL cap. 3.4 (Ridge, Lasso), ISL cap. 6.2. Vezi BIBLIOGRAFIE.md.
