# M19 -- Exercitii: Serii temporale

Gradat, de la fereastra de lag-uri si phi de mana la prognoza AR vs persistenta pe
seria mea de latenta. Rezolva in `exercitii.py`; solutiile in `solutii.py`.
Refoloseste `serii_temporale_core`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- fereastra glisanta de lag-uri
`ex1_lag_features(series, p)`: construieste de mana matricea de lag-uri FARA a
folosi `make_lag_features`. Pentru `x_0..x_{n-1}` si ordin `p`, randul `t` este
`[x_{t-1}, x_{t-2}, ..., x_{t-p}]` cu tinta `x_t`. Asert: pe `x=0..7`, `p=2`,
forma `X=(6,2)`, primul rand `[1,0]`, tinta `2`. (Vezi sectiunea 3 din `teorie.md`.)

## Ex. 2 (deriva si implementeaza) -- phi pentru AR(1) de mana
`ex2_phi_ar1_de_mana(x4)`: estimeaza panta AR(1) FARA intercept din perechi
consecutive: `phi = sum(x_{t-1} x_t) / sum(x_{t-1}^2)`. Asert: pe un AR(1) cu
phi=0.8, estimarea cade in `|d| < 0.05`. (Reproduce exemplul numeric din `teorie.md`.)

## Ex. 3 (concept) -- split fara look-ahead
`ex3_split_fara_lookahead(series, train_frac)`: foloseste `temporal_split` si
intoarce `(max_idx_train, min_idx_test)`. Asert: `max_idx_train < min_idx_test`.
Reflectie: de ce ar fi gresit sa amesteci seria inainte de split?

## Ex. 4 (aplica) -- AR bate persistenta
`ex4_ar_bate_persistenta(series, p, train_frac)`: split temporal, `fit_ar` pe
train, prognoza un-pas pe test, intoarce `(rmse_ar, rmse_persistenta)`. Asert: pe
un proces AR, `rmse_ar < rmse_persistenta`.

## Ex. 5 (aplica pe datele mele) -- RMSE pe latenta
`ex5_rmse_pe_latenta_mea(cond, p)`: pe `make_latency_series(cond, length=300,
seed=4)`, split temporal 70/30, AR(p) pe train, prognoza un-pas pe test. Intoarce
`(rmse_ar, rmse_persistenta)`. Asert: `rmse_ar <= rmse_persistenta`. Reflectie:
cum ar ajuta anticiparea latentei la adaptarea proactiva a mesh-ului din teza?
