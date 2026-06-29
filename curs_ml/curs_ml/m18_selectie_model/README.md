# M18 -- Selectie de model si reglare hiperparametri

Alegerea ONESTA a unui model: grid search / random search peste hiperparametri,
nested CV pentru o estimare nepartinitoare a erorii unei proceduri de selectie, si
criteriile de informatie AIC/BIC (compromis fit vs complexitate, Occam). Nucleul
implementeaza grid_search_cv, nested_cv si aic/bic din log-verosimilitatea gaussiana.

Mesajul central: CV-ul pe care OPTIMIZEZI hiperparametrii este optimist; raporteaza
eroarea de generalizare cu nested CV (sau cu un set de test atins o singura data).

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (grid/random search, nested CV, Occam, AIC/BIC + exemplu numeric).
- `selectie_model_core.py` -- nucleu pur numpy + `_selftest()` (grid search, nested CV, AIC/BIC).
- `selectie_model_sklearn.py` -- validare incrucisata cu `GridSearchCV` (acelasi grad, aceleasi falduri).
- `demo_sil.py` -- selectie de grad pe latenta cu nested CV (figura `fig_selectie_model.png`).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m18_selectie_model
$PY selectie_model_core.py
$PY selectie_model_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
