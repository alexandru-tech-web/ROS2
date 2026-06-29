# M04 -- Exercitii: Date si feature engineering

Gradat, de la encodare la un pipeline mic FARA scurgere de date. Refoloseste
nucleul `date_features_core` (nu reimplementa ce exista). Rezolva in
`exercitii.py`; solutiile in `solutii.py`.

Reaminteste-ti: datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- one-hot manual
`ex1_one_hot(labels)`: invata vocabularul cu `fit_one_hot`, transforma cu
`transform_one_hot`; matrice indicator (n, 3) in ordinea alfabetica a categoriilor.
Asert: forma corecta, un singur 1 per rand, coloana asteptata aprinsa.

## Ex. 2 (concept cheie) -- imputare FARA scurgere
`ex2_impute_no_leak(Xtr, Xte)`: invata media pe TRAIN (`fit_mean_imputer`) si umple
AMBELE seturi cu ea (`transform_mean_imputer`). Asert: fara NaN, iar TEST e umplut
cu media de pe TRAIN (nu cu a lui). Aceasta e regula anti-scurgere centrala.

## Ex. 3 (numara) -- coloane polinomiale
`ex3_n_poly_cols(p, degree)`: numarul de coloane produse de un polinom de grad
`degree` pe `p` feature-uri, fara bias. Asert: `p=4,degree=2 -> 14`;
`p=2,degree=3 -> 9`. (Formula combinatoriala sau `polynomial_features`.)

## Ex. 4 (aplica pe datele mele) -- fractia de outlieri IQR
`ex4_outlier_fraction()`: pe `make_latency_dataset(n_per_cond=200, seed=0)`,
fractia de randuri marcate outlier de regula IQR (k=1.5) pe `rtt_ms`. Asert: in
(0, 0.5). De ce are `rtt_ms` o coada lunga (multi outlieri pe partea dreapta)?

## Ex. 5 (pipeline integrat) -- one-hot + z-score fara scurgere
`ex5_pipeline(df)`: split 75/25 (seed=0); one-hot pe `middleware` (fit pe TRAIN);
z-score pe `['loss_pct','distance_m']` cu statistici de pe TRAIN; `column_stack`
in ordinea [one-hot..., z(loss_pct), z(distance_m)]. Asert: 4 coloane,
train+test = tot setul, media z pe TRAIN ~ 0. Acesta e scheletul oricarui
preprocesing corect (vezi Pipeline/ColumnTransformer in `date_features_sklearn.py`).
