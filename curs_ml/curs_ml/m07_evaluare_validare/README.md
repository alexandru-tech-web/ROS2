# M07 -- Evaluare si validare

Raportare onesta pe campanii mici: k-fold, LOOCV (critic la N=5), RMSE/MAE/R2,
curbe de invatare si capcana scurgerii de date in CV. Nucleul implementeaza
faldurile, validarea incrucisata generica si curba de invatare.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (k-fold/LOOCV + exemplu numeric RMSE/MAE).
- `evaluare_validare_core.py` -- nucleu pur numpy + `_selftest()` (acoperire falduri, CV, curba).
- `evaluare_validare_sklearn.py` -- validare incrucisata (KFold + cross_val_score).
- `demo_sil.py` -- curba de invatare pe latenta (figura).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m07_evaluare_validare
$PY evaluare_validare_core.py
$PY evaluare_validare_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
