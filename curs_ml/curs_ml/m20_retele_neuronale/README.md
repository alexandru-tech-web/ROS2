# M20 -- Retele neuronale

Perceptron multistrat (MLP) cu un strat ascuns, scris de la zero in numpy pur:
forward, backpropagation derivat cu regula lantului, gradient descent si gradient
check cu diferente finite. Pentru regresie (MSE) si, optional, clasificare binara
(sigmoid + entropie incrucisata). Nota onesta: la N mic / semnal aproape liniar,
MLP-ul NU bate un model liniar -- modelul simplu castiga.

Datele de demonstratie sunt SINTETICE (XOR, sin, latenta semanata din C1/M via
`date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (derivare backprop + exemplu numeric forward/backward de mana).
- `mlp_core.py` -- nucleu pur numpy + `_selftest()` (gradient check pe W1/b1/W2/b2, XOR, sin, weight decay).
- `mlp_sklearn.py` -- validare incrucisata cu `sklearn.neural_network.MLPRegressor`.
- `demo_sil.py` -- MLP vs regresie liniara pe latenta (figura + nota onesta).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m20_retele_neuronale
$PY mlp_core.py        # gradient check + invatare XOR/sin
$PY mlp_sklearn.py     # comparatie cu sklearn MLPRegressor
$PY demo_sil.py        # MLP vs liniar pe latenta (figura)
$PY exercitii.py       # pica pana rezolvi; $PY solutii.py trece
```
