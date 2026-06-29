# M05 -- Regresie liniara

Primul model complet: predictia `rtt_ms` din feature-uri de netem/distanta.
Derivarea ecuatiilor normale din `||Xw - y||^2`, solutia inchisa
`w = (X^T X)^{-1} X^T y`, gradient descent, ipoteze si conditionare. Nucleul
implementeaza ambele cai si arata ca dau acelasi rezultat.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (cu exemplu numeric: `x=[1,2,3,4]`, `y=[2,2,4,4]`).
- `regresie_liniara_core.py` -- nucleu pur numpy + `_selftest()` (ecuatii normale == GD).
- `regresie_liniara_sklearn.py` -- validare incrucisata (LinearRegression).
- `demo_sil.py` -- predictie vs real pe latenta, RMSE/R^2 vs baza (figura).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m05_regresie_liniara
$PY regresie_liniara_core.py
$PY regresie_liniara_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
