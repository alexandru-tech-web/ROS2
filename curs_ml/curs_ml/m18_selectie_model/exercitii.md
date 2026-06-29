# M18 -- Exercitii: Selectie de model si reglare de hiperparametri

Gradat, de la grid search si AIC/BIC la nested CV pe datele mele. Rezolva in
`exercitii.py`; solutiile in `solutii.py`. Refoloseste `selectie_model_core`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- grid search peste gradul polinomului
`ex1_alege_grad(x, y, grid, k, seed)`: foloseste `grid_search_cv` cu adaptorul de
polinom 1D pentru a alege gradul cu RMSE de validare incrucisata minim. Returneaza
gradul ales (int). Asert: pe o cubica zgomotoasa cu `grid=[1,2,3,4,5]` alege `3`.

## Ex. 2 (implementeaza) -- AIC din log-verosimilitate
`ex2_aic(neg2ll, k)`: implementeaza `AIC = 2k - 2 ln L` (primesti direct `-2 ln L`).
Asert: pentru `-2 ln L = 218.0` si `k=3` da `224.0`. (Vezi exemplul lucrat din
`teorie.md`.)

## Ex. 3 (concept) -- AIC/BIC aleg modelul mai simplu la potrivire egala
`ex3_alege_model(rss_a, k_a, rss_b, k_b, n, criteriu)`: calculeaza AIC sau BIC
(`criteriu in {'aic','bic'}`) pentru doua modele gaussiene din RSS si returneaza
`'A'` sau `'B'` (cel cu valoarea mai mica). Asert: cu `n=100`, model A `(RSS=52,k=3)`
si model B `(RSS=50,k=6)` -- potrivire ~egala -- ambele criterii aleg `'A'`.

## Ex. 4 (concept) -- BIC penalizeaza mai tare ca AIC la n mare
`ex4_penalizare_pe_parametru(n)`: returneaza `(pen_aic, pen_bic)`, penalizarea
ADAUGATA per parametru in plus de fiecare criteriu (`2` pentru AIC, `ln n` pentru
BIC). Asert: la `n=100`, `pen_bic > pen_aic` si `pen_aic == 2`.

## Ex. 5 (aplica pe datele mele) -- eroarea onesta cu nested CV
`ex5_eroare_onesta()`: pe `make_latency_dataset`, prezice `log10(rtt_ms)` din
distanta standardizata; alege gradul cu nested CV peste `grid=[1,2,3,4,5,6]`.
Returneaza `(err_selectie, err_onesta)` -- minimul `grid_search_cv` (optimist) si
media `nested_cv`. Asert: `err_onesta >= err_selectie` (selectia e optimista).
Reflectie: de ce nu raportezi NICIODATA in teza minimul CV de selectie ca eroare
de generalizare?
