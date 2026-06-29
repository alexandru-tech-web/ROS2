# M17 -- Cuantificarea incertitudinii

Bare de eroare pentru predictii: regresie liniara bayesiana (posterior pe greutati +
varianta predictiva), bootstrap (interval de incredere pe medie) si conformal
prediction split (interval cu acoperire garantata). Distinctia cheie: interval de
PREDICTIE (acopera o observatie noua) vs interval de INCREDERE (acopera media).

ACCENTUL TEZEI (N mic, C1: N=5): la N=5 o predictie fara bara de eroare e inutila --
nu poti spune daca diferenta Zenoh vs DDS e reala sau zgomot. Acest modul da barele.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (derivarea posteriorului S/m, varianta predictiva,
  predictie vs incredere, bootstrap, conformal + exemplu numeric bayesian 1D).
- `incertitudine_core.py` -- nucleu pur numpy + `_selftest()` (contractia
  posteriorului, media ~ OLS la prior slab, acoperirea intervalelor, conformal).
- `incertitudine_sklearn.py` -- validare incrucisata (Ridge / BayesianRidge).
- `demo_sil.py` -- predictie log10(rtt_ms) cu interval de predictie + acoperire (figura).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m17_incertitudine
$PY incertitudine_core.py
$PY incertitudine_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
