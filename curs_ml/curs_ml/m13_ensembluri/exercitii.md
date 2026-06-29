# M13 -- Exercitii: Ensembluri

Gradat, de la bootstrap si out-of-bag la un pas de gradient boosting calculat de
mana si capcana supra-invatarii. Rezolva in `exercitii.py`; solutiile in
`solutii.py`. Refoloseste `ensembluri_core` (ciotul, bagging, boosting) -- NU
reimplementa ansamblurile.

Datele sunt SINTETICE (semanate din C1/M via `date_sar.py`).

---

## Ex. 1 (implementeaza) -- esantion bootstrap
`ex1_bootstrap_indices(n, seed)`: `n` indici din `0..n-1` trasi CU INLOCUIRE,
determinist (`numpy.random.default_rng(seed).integers`). Asert: pe `n=50` au
repetitii (mai putin de 50 valori unice) si sunt deterministi la aceeasi samanta.

## Ex. 2 (concept + calcul) -- fractia out-of-bag
`ex2_oob_fraction(n, seed)`: fractia exemplelor LASATE AFARA de un bootstrap (cele
care nu apar deloc in indici). Asert: pe `n=3000` da ~`1/e = 0.368`. De ce? Sansa
ca un exemplu sa NU fie ales intr-o tragere e `(1 - 1/n)`; in `n` trageri
`(1 - 1/n)^n -> 1/e`. Aceste exemple out-of-bag dau o estimare gratuita a erorii.

## Ex. 3 (aplica) -- bagging bate ciotul
`ex3_bagging_bate_ciotul()`: pe `_toy_noisy` (train seed 11, test seed 22),
antreneaza un singur `DecisionStump` si un `BaggingClassifier(41)`; intoarce
`(acc_ciot, acc_bagging)` pe test. Asert: `acc_bagging >= acc_ciot`. Mediarea taie
varianta invatatorului instabil.

## Ex. 4 (de mana) -- un pas de gradient boosting
`ex4_un_pas_boosting(y, p, residual_pred, lr)`: dat fiind `y`, probabilitatile
curente `p = sigmoid(F)`, predictia ciotului de regresie pe reziduuri si rata `lr`,
intoarce `(residual, delta_F)` unde reziduul (gradientul negativ al pierderii
logistice) este `r = y - p` si `delta_F = lr * residual_pred`. (Vezi exemplul numeric
din `teorie.md`, sectiunea 6.)

## Ex. 5 (aplica pe datele mele) -- capcana supra-invatarii
`ex5_supra_invatare_boosting()`: pe `make_mission_outcome_dataset(n=600, seed=3)`,
split 75/25, antreneaza `GradientBoostingClassifier(n_estimators=300,
learning_rate=0.5)` si intoarce eroarea de TEST la 120 si la 300 de pasi (cu
`staged_decision_function`). Asert: `err_300 >= err_120 - 0.01` -- coada de pasi NU
mai imbunatateste testul, desi eroarea de TRAIN continua sa scada. Reflectie: de ce
`n_estimators` e un hiperparametru de oprire (early stopping), nu 'cu cat mai multe
cu atat mai bine'?
