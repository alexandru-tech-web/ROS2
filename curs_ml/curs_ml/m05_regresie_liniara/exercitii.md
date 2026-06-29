# M05 -- Exercitii: Regresie liniara

Gradat, de la rulare/interpretare la implementare la transfer pe alta conditie.
Rezolva in `exercitii.py` (stub-uri cu TODO). Aserturile pica pana completezi.
Solutiile complete sunt in `solutii.py` (ruleaza-l ca sa verifici).

Reaminteste-ti: datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).
Determinism: foloseste `rng(seed)` / `numpy.random.default_rng(seed)`.

---

## Ex. 1 (ruleaza si interpreteaza) -- baza vs model
Ruleaza `demo_sil.py`. In `exercitii.py`, functia `ex1_castig_fata_de_baza()`
trebuie sa antreneze regresia liniara (ecuatii normale) pe `make_latency_dataset`
prezicand `log10(rtt_ms)` din cele patru feature-uri, si sa intoarca reducerea
procentuala a RMSE [ms] fata de baza (prezice media). Asert: castig > 20%.
Intrebare de reflectie (raspunde in comentariu): de ce R^2 pe scara log e mai mare
decat pe scara ms?

## Ex. 2 (calcul de mana verificat in cod) -- exemplul numeric
Reproduce exemplul din `teorie.md` sectiunea 6: `x=[1,2,3,4]`, `y=[2,2,4,4]`.
Implementeaza `ex2_ecuatii_normale_de_mana()` care construieste `X` cu bias,
rezolva ecuatiile normale si intoarce `(w0, w1)`. Asert: `(w0, w1) ~ (1.0, 0.8)`.

## Ex. 3 (implementeaza X) -- gradient descent de la zero
Completeaza `ex3_gradient_descent(X, y, alpha, n_iter)` care implementeaza pasul
`w <- w - alpha * (2/n) X^T (Xw - y)` pornind din `w = 0`. Pe date standardizate,
rezultatul trebuie sa coincida cu ecuatiile normale. Asert: `||w_gd - w_ne|| < 1e-3`.

## Ex. 4 (diagnostic) -- conditionare
Completeaza `ex4_conditionare()` care ia feature-urile din `make_latency_dataset`,
calculeaza numarul de conditie al `X^T X` cu bias pe feature-uri brute si pe
feature-uri standardizate, si intoarce `(cond_brut, cond_std)`. Asert:
`cond_std < cond_brut / 100` (standardizarea reduce conditionarea cu peste 2 ordine).

## Ex. 5 (transfer pe alta conditie) -- per middleware
Completeaza `ex5_r2_per_middleware()` care antreneaza CATE un model pe subsetul
DDS si pe subsetul Zenoh (acelasi tip de tinta `log10(rtt_ms)`, feature-uri fara
`mw_zenoh`) si intoarce `{'DDS': r2_dds, 'Zenoh': r2_zen}` pe propriul test split.
Asert: ambele R^2 (pe scara log) > 0.3.

## Ex. 6 (extindere) -- feature polinomial
Completeaza `ex6_feature_distanta_patrat()` care adauga `distance_m^2` ca feature
suplimentar si verifica daca R^2 (pe scara log, test) NU scade fata de modelul
fara acel feature. Asert: `r2_extins >= r2_baza - 0.01`. Reflectie: de ce un
feature in plus aproape nu strica pe TRAIN dar poate strica pe TEST (preludiu la M06/M07)?
