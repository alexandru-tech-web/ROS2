# M13 -- Ensembluri

Multe modele slabe combinate intr-unul puternic: bagging (bootstrap + vot, reduce
varianta), Random Forest (bagging + subset de feature-uri) si gradient boosting
(potriveste reziduuri, reduce biasul). Nucleul implementeaza totul de la zero peste
un invatator de baza propriu (ciot de decizie), AUTO-SUFICIENT (nu importa din M12).

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (bagging/RF/boosting + derivarea reducerii de varianta + exemplu numeric de un pas de boosting).
- `ensembluri_core.py` -- nucleu pur numpy + `_selftest()` (ciot, bagging, gradient boosting).
- `ensembluri_sklearn.py` -- validare incrucisata (RandomForest + GradientBoosting sklearn).
- `demo_sil.py` -- ciot vs bagging vs boosting pe `mission_complete` (figura).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m13_ensembluri
$PY ensembluri_core.py
$PY ensembluri_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
