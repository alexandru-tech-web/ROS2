# M08 -- Regresie logistica

Primul clasificator probabilistic al cursului: modelam P(y=1 | x) cu o sigmoida pe
un scor liniar, antrenam prin coborare pe gradient minimizand entropia incrucisata,
si decidem cu un prag. Nucleul implementeaza sigmoid stabil numeric, log-loss,
gradientul analitic si modelul `LogisticRegressionGD`.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`):
utilizabilitatea unei legaturi de teleoperatie (clase DEZECHILIBRATE, ~30% usable).

## Fisiere
- `teorie.md` -- predare completa (sigmoid, log-loss, DERIVAREA gradientului + exemplu numeric).
- `regresie_logistica_core.py` -- nucleu pur numpy + `_selftest()` (gradient vs diferente finite, convergenta, log-loss monoton).
- `regresie_logistica_sklearn.py` -- validare incrucisata cu `LogisticRegression` (acuratete + coeficienti).
- `demo_sil.py` -- regresie logistica pe utilizabilitatea legaturii (acuratete/precizie/recall + figura granitei de decizie).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m08_regresie_logistica
$PY regresie_logistica_core.py
$PY regresie_logistica_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
