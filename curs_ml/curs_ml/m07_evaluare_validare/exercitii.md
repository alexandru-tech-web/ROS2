# M07 -- Exercitii: Evaluare si validare

Gradat, de la falduri si metrici la curba de invatare pe datele mele. Rezolva in
`exercitii.py`; solutiile in `solutii.py`. Refoloseste `evaluare_validare_core`.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- k-fold manual contiguu
`ex1_kfold_manual(n, k)`: imparte `0..n-1` in `k` blocuri contigue (cu
`numpy.array_split`), intoarce lista indicilor de TEST per fald. Asert: `n=10,k=3`
acopera totul o data. (Vezi exemplul numeric din `teorie.md`.)

## Ex. 2 (implementeaza) -- RMSE si MAE de la zero
`ex2_rmse_mae(y_true, y_pred)` fara `utils`. Asert: pe `y=[1,2,3]`, `p=[1,4,3]` da
`rmse=sqrt(4/3)`, `mae=2/3`. De ce e RMSE > MAE aici?

## Ex. 3 (concept) -- k pentru LOOCV
`ex3_k_pentru_loocv(n)`: ce `k` face k-fold identic cu LOOCV? Asert: `n=7 -> 7`.

## Ex. 4 (aplica) -- media RMSE de validare incrucisata
`ex4_cv_mean_rmse(X, y, k, seed)`: media RMSE 5-fold a modelului liniar auxiliar
(`cross_val_score` + `_ols_fit_predict`). Asert: < 0.2 pe date liniare.

## Ex. 5 (aplica pe datele mele) -- golul curbei de invatare
`ex5_gol_invatare()`: pe latenta standardizata -> `log10(rtt_ms)`, eroarea de
VALIDARE la set mic (10) si la set mare (600) cu `learning_curve`. Asert:
`val_mare <= val_mic`. Reflectie: cum arata asta de ce N mic (C1, N=5) e greu?
