# M02 -- Optimizare pentru ML

Motorul din spatele tuturor modelelor antrenate: gradient, convexitate, gradient
descent, moment, Adam, rata de invatare, conditionare, oprire timpurie. Nucleul
implementeaza GD/moment/Adam pe o patratica convexa cu optim analitic cunoscut si
verifica gradientul cu diferente finite.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (cu exemplu numeric).
- `optimizare_core.py` -- nucleu pur numpy + `_selftest()` (GD == solutie analitica).
- `optimizare_sklearn.py` -- validare incrucisata (SGDRegressor).
- `demo_sil.py` -- convergenta GD vs Adam pe o regresie de latenta (figuri).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m02_optimizare
$PY optimizare_core.py
$PY optimizare_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
