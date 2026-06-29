# M04 -- Date si feature engineering

Deseori 80% din munca reala: EDA, scalare/standardizare, encodare (one-hot,
ordinal), valori lipsa, outlieri, transformari si -- esential -- evitarea scurgerii
de date (leakage). Nucleul implementeaza one-hot, imputare cu media de pe TRAIN,
feature-uri polinomiale si detectie de outlieri IQR.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (cu exemplu numeric).
- `date_features_core.py` -- nucleu pur numpy + `_selftest()`.
- `date_features_sklearn.py` -- validare incrucisata (ColumnTransformer + OneHotEncoder + StandardScaler).
- `demo_sil.py` -- pipeline de feature engineering pe latenta + outlieri (figuri).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m04_date_features
$PY date_features_core.py
$PY date_features_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
