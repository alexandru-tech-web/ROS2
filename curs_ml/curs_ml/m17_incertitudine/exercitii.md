# M17 -- Exercitii: Cuantificarea incertitudinii

Gradat, de la posteriorul bayesian de mana la barele de eroare pe datele mele.
Rezolva in `exercitii.py`; solutiile in `solutii.py`. Refoloseste `incertitudine_core`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- posterior bayesian 1D de mana
`ex1_posterior_1d(x, y, lam, sig2)`: regresie liniara bayesiana 1D FARA bias
(un singur parametru w, phi(x)=x). Aplica formulele scalare din `teorie.md` sec. 8:
`S = 1/(lam + (1/sig2) sum x_i^2)` si `m = (1/sig2) S sum x_i y_i`. Intoarce `(m, S)`.
NU folosi `BayesianLinearRegression`. Asert: pe `x=[1,2]`, `y=[2,4]`, `lam=0`,
`sig2=1` da `S=1/5`, `m=2.0` (verifica-l de mana inainte).

## Ex. 2 (aplica) -- contractia posteriorului
`ex2_contractie_posterior(lam, sig2)`: antreneaza `BayesianLinearRegression` pe 10
puncte si pe 500 (datele sunt date in stub) si intoarce `(trace_mic, trace_mare)` =
urma covariantei posterioare in cele doua cazuri (`cov_trace()`). Asert:
`trace_mare < trace_mic`. Reflectie: de ce SCADE urma cand cresc datele? Leaga de
`S^-1 = lam I + (1/sig2) Phi^T Phi`.

## Ex. 3 (aplica) -- acoperirea intervalului de predictie
`ex3_acoperire_predictie(level)`: pe date liniare 1D (date in stub), antreneaza un
model bayesian, cere `predict_interval` la `level` pe test si intoarce acoperirea
empirica (`empirical_coverage`). Asert: `>= level - 0.05`. De ce poate fi usor sub
nivel daca subestimezi `sig2`?

## Ex. 4 (aplica) -- acoperirea conformal
`ex4_conformal_acoperire(alpha)`: imparte trainul in train + calibrare (jumatate-
jumatate, deja pregatit in stub), aplica `conformal_split` cu `_ols_fit_predict` si
intoarce acoperirea empirica pe test. Asert: `>= 1 - alpha - 0.03`. Ce ipoteza ceri
ca garantia sa tina (vezi sec. 6)?

## Ex. 5 (aplica pe datele mele) -- predictie vs incredere
`ex5_predictie_vs_incredere()`: pe `make_latency_dataset(n_per_cond=80, seed=0)`,
feature-uri standardizate -> `log10(rtt_ms)`, calculeaza latimea medie a intervalului
de PREDICTIE bayesian (level 0.90) si a intervalului de INCREDERE bootstrap (level
0.90). Intoarce `(latime_predictie, latime_incredere)`. Asert:
`latime_predictie > latime_incredere`. Reflectie: de ce e banda de predictie mai
larga? (Leaga de `sig2 + phi^T S phi` vs doar incertitudinea pe medie.) Cum arata
asta de ce la C1 (N=5) trebuie raportata bara de eroare?
