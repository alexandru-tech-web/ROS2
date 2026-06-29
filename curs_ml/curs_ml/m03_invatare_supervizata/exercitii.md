# M03 -- Exercitii: Cadrul invatarii supervizate

Gradat, de la riscul empiric la echilibrul bias-varianta. Rezolva in
`exercitii.py` (stub-uri cu TODO); aserturile pica pana completezi. Solutiile
complete in `solutii.py`. Refoloseste nucleul `invatare_supervizata_core`.

Datele/procesul sunt SINTETICE (proces controlat f(x)+zgomot). Determinism:
`numpy.random.default_rng(seed)`.

---

## Ex. 1 (implementeaza) -- riscul empiric patratic
`ex1_risc_empiric_patratic(y_true, y_pred)` = media lui `squared_loss`. Asert: pe
`y=[3,0,-2]`, `p=[1,0,1]` da `13/3` (vezi exemplul numeric din `teorie.md`).

## Ex. 2 (implementeaza) -- eroarea 0-1 cu prag
`ex2_eroare_clasificator_prag(scores, y_true, threshold)`: prezice 1 daca
`score > threshold`, intoarce fractia de clasificari gresite. Asert: 0.25 pe cazul
dat. De ce e 0-1 greu de optimizat direct?

## Ex. 3 (interpreteaza) -- surogate la un scor
`ex3_compara_surogate(score)` intoarce `(hinge, logistica)` pentru clasa pozitiva.
Asert: la score 0, `hinge=1`, `logistica=log(2)`. Compara cum penalizeaza cele doua
scorurile gresite mari (linear vs ...).

## Ex. 4 (experiment) -- gradul optim (echilibrul bias-varianta)
`ex4_grad_optim_biasvar(...)`: ruleaza `bias_variance_decomposition` pentru fiecare
grad si intoarce gradul cu EROAREA TOTALA minima. Asert: optimul e interior
(1 <= d* <= 8), nu la extreme -- exact forma de U.

## Ex. 5 (experiment) -- efectul lui n_train asupra variantei
`ex5_efect_n_train_variance(...)`: pentru un grad fix si o lista de marimi de set,
intoarce variantele. Asert: varianta SCADE cand creste n_train (mai multe date
stabilizeaza modelul). Legatura cu N=5 din campaniile mele.

## Ex. 6 (sinteza) -- underfit vs overfit pe un set
`ex6_polinom_underfit_overfit(...)`: pe UN set de antrenare, potriveste grad 1
(rigid) si grad 12 (flexibil), intoarce `(rmse_grad1, rmse_grad12)` fata de `f_true`
fara zgomot pe un grid dens. Reflectie: care domina la N mic -- bias-ul gradului 1
sau varianta gradului 12?
