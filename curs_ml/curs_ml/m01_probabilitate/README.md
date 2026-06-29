# M01 -- Probabilitate si statistica pentru ML

Variabile aleatoare, distributii (Bernoulli, Gauss, lognormal), MLE/MAP, intervale
de incredere si bootstrap. Motivatia centrala: la N mic (campania C1 are N=5) orice
estimare cere o bara de eroare. Nucleul implementeaza pdf-uri, estimatori MLE si
bootstrap, validate fata de scipy.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (cu exemplu numeric).
- `probabilitate_core.py` -- nucleu pur numpy + `_selftest()`.
- `probabilitate_sklearn.py` -- validare incrucisata (scipy.stats).
- `demo_sil.py` -- fit lognormal pe RTT + interval bootstrap (figuri).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m01_probabilitate
$PY probabilitate_core.py
$PY probabilitate_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
