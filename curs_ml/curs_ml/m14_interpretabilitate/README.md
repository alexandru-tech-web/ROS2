# M14 -- Interpretabilitate

Explicabilitate model-agnostica pe campanii mici: importanta prin permutare (ce feature
conteaza global), dependenta partiala (PDP, forma efectului mediu) si valori Shapley
(explicatie locala, exacta pentru un model liniar). Nucleul implementeaza cele trei
unelte in numpy pur, fara sa stie nimic despre cum e antrenat modelul (callback
`model_predict`).

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (permutare + PDP + Shapley, cu derivare si exemplu
  numeric lucrat: valori Shapley pe un model liniar cu 2 feature-uri).
- `interpretabilitate_core.py` -- nucleu pur numpy + `_selftest()` (importanta zgomot ~0,
  PDP monoton, eficienta Shapley).
- `interpretabilitate_sklearn.py` -- validare incrucisata vs
  `sklearn.inspection.permutation_importance` (acelasi clasament si semn).
- `demo_sil.py` -- ce feature de link conteaza pentru `usable` (clasament + PDP + figura).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m14_interpretabilitate
$PY interpretabilitate_core.py
$PY interpretabilitate_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
