# M14 -- Exercitii: Interpretabilitate

Gradat, de la valori Shapley de mana la importanta prin permutare pe datele mele de
link. Rezolva in `exercitii.py`; solutiile in `solutii.py`. Refoloseste
`interpretabilitate_core`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- valoare Shapley liniara de mana
`ex1_shapley_manual(w, x, x_mean)`: pentru un model liniar, contributia feature-ului
j este `w_j*(x_j - E[x_j])`. Implementeaza formula element cu element, FARA
`shapley_linear`. Asert: pe `w=[2,-3]`, `x=[1,4]`, `E[x]=[0,5]` da `phi=[2,3]`.
(Vezi exemplul lucrat din `teorie.md`.)

## Ex. 2 (verifica) -- proprietatea de eficienta
`ex2_eficienta(w, x, x_mean, w0)`: intoarce `(suma_phi, fx_minus_baza)`, unde
`fx = w0 + w.x` si `baza = w0 + w.E[x]`. Foloseste `shapley_linear`. Asert: cele doua
sunt egale (suma contributiilor = predictie - baza). De ce se anuleaza interceptul w0?

## Ex. 3 (concept) -- panta PDP = coeficientul
`ex3_pdp_panta(coef)`: pentru `f(x)=coef[0]*x0 + coef[1]*x1` (fara intercept), profilul
PDP pe feature 0 e o dreapta de panta `coef[0]`. Construieste intern un X aleator si un
grid, calculeaza PDP cu `partial_dependence` si intoarce panta empirica. Asert: pe
`coef=[2,-1]` panta ~ 2.0.

## Ex. 4 (aplica) -- importanta unui feature de zgomot
`ex4_importanta_zgomot()`: pe date unde DOAR feature 0 conteaza (feature 1 pur zgomot),
antreneaza modelul liniar auxiliar (`_linfit` -> `_make_predict`) si intoarce
`(imp0, imp1)` din `permutation_importance`. Asert: `imp0 > 0.5`, `|imp1| < 0.02`.
De ce ramane importanta zgomotului aproape de zero?

## Ex. 5 (aplica pe datele mele) -- feature-ul de link decisiv
`ex5_top_feature_link()`: pe `make_link_usability_dataset(n_per_cond=200, seed=1)`,
feature-uri standardizate, model liniar care prezice `usable`, intoarce NUMELE
feature-ului cel mai important dupa importanta prin permutare. Asert: este `p95_ms`.
Reflectie: ce variabila de link ai justifica in articol ca fiind decisiva, si ce
capcana (corelatii) ai mentiona?
