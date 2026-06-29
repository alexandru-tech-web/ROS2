# M10 -- Naive Bayes

Clasificator GENERATIV ieftin: Gaussian Naive Bayes de la zero. Estimeaza
prior-uri si (medie, varianta) per clasa per feature, apoi prezice prin argmax al
log-posteriorului (Bayes + ipoteza de independenta conditionala). Folosit ca
linie de baza pe clasificarea 'link utilizabil' a campaniilor mele.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (generativ vs discriminativ, derivarea MAP + log-posterior, exemplu numeric).
- `naive_bayes_core.py` -- nucleu pur numpy + `_selftest()` (separare, formula manuala, prior dominant, finitudine).
- `naive_bayes_sklearn.py` -- validare incrucisata cu `sklearn.naive_bayes.GaussianNB` (aceleasi estimari/predictii).
- `demo_sil.py` -- NB vs baza triviala pe 'usable' (figura: frontiera de decizie).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m10_naive_bayes
$PY naive_bayes_core.py
$PY naive_bayes_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
