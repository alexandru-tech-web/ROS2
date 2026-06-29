# M10 -- Exercitii: Naive Bayes

Gradat, de la log-densitatea gaussiana si estimarile MLE pana la NB ca linie de
baza pe datele mele. Rezolva in `exercitii.py`; solutiile in `solutii.py`.
Refoloseste `naive_bayes_core`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- log-densitate gaussiana 1D
`ex1_log_gaussian(x, mu, var)`: intoarce `log N(x; mu, var) = -0.5*log(2*pi*var)
- (x-mu)^2/(2*var)`. Asert: `log N(0; 0, 1) = -0.5*log(2*pi)`. (Acesta e termenul
care se sumeaza pe feature-uri in log-posterior -- vezi `teorie.md` sec.2-3.)

## Ex. 2 (implementeaza) -- estimari MLE per clasa
`ex2_estimari(X, y)` pe un feature unic, pentru clasa `c=1`: intoarce
`(prior, mu, var)` cu `prior = n_1/n`, `mu` = media feature-ului pe clasa 1,
`var` = varianta MLE (`ddof=0`) pe clasa 1. Asert: pe clasa `[5,6,7]` da
`prior=0.5, mu=6, var=2/3`. De ce `ddof=0` si nu `ddof=1`?

## Ex. 3 (aplica) -- log-posterior pe cazul mic
`ex3_log_posterior(x)`: pe cazul din `teorie.md` (clasa 0: `[1,2,3]`; clasa 1:
`[5,6,7]`; prior 0.5/0.5), antreneaza `GaussianNaiveBayes(var_smoothing=0.0)` si
intoarce `[lp0, lp1]` pentru scalarul `x`. Asert: pe `x=3` se potriveste cu
formula calculata de mana. Verifica si ca la `x=4` (mijloc) `lp0 == lp1`.

## Ex. 4 (concept) -- prior dominant
`ex4_prior_dominant()`: construieste un caz unde ambele clase trag din `N(0,1)`
(feature-ul NU distinge) dar clasa 0 e majoritara (90 vs 10); antreneaza NB si
intoarce predictia pentru `x=0.0`. Asert: `== 0`. Cand verosimilitatea e egala,
ce decide MAP-ul?

## Ex. 5 (aplica pe datele mele) -- NB vs baza triviala
`ex5_nb_vs_baza()`: pe `make_link_usability_dataset(n_per_cond=120, seed=1)`, cu
`FEATURES` standardizate (split `test_frac=0.25, seed=0`), antreneaza Gaussian NB
si intoarce `(acc_nb, acc_maj)`, unde `acc_maj` e baza triviala 'mereu clasa
majoritara de pe train'. Asert: `acc_nb > acc_maj`. Reflectie: la clase
dezechilibrate (usable ~30%), de ce e acuratetea singura inselatoare? (vezi M09)
