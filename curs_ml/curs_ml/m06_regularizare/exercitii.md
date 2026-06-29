# M06 -- Exercitii: Regularizare

Gradat, de la forma inchisa Ridge la sparsitatea Lasso pe datele mele. Rezolva in
`exercitii.py`; solutiile in `solutii.py`. Refoloseste nucleul `regularizare_core`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- Ridge in forma inchisa
`ex1_ridge_de_mana(X, y, lam)` = `(X^T X + lam I)^{-1} X^T y` via
`numpy.linalg.solve`, fara a apela `ridge_fit`. Asert: coincide cu `ridge_fit`.

## Ex. 2 (implementeaza) -- soft-threshold
`ex2_soft_threshold(z, gamma)` = `sign(z) * max(|z| - gamma, 0)`, vectorizat.
Asert: `(5,2)->3`, `(-1,2)->0`. Acesta e mecanismul care creeaza zerouri in Lasso.

## Ex. 3 (experiment) -- micsorarea Ridge
`ex3_norme_ridge(X, y, lams)`: lista normelor L2 ale coeficientilor Ridge pentru
fiecare lambda. Asert: norma scade monoton cu lam. De ce nu atinge niciodata 0?

## Ex. 4 (experiment) -- sparsitatea Lasso
`ex4_nenule_lasso(X, y, lams)`: numarul de coeficienti Lasso nenuli la fiecare
lambda. Asert: scade cu lam (mai multa sparsitate). Contrast cu Ex.3.

## Ex. 5 (aplica pe datele mele) -- Ridge vs OLS
`ex5_ridge_vs_ols_pe_date()`: pe `make_latency_dataset`, feature-uri
standardizate -> `log10(rtt_ms)` centrat, intoarce `(norma_ols, norma_ridge_lam10)`.
Asert: `norma_ridge < norma_ols`. Reflectie: de ce conteaza asta la N mic (C1, N=5)?
