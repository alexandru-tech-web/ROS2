# M12 -- Arbori de decizie

Arbore de decizie CART de la zero pentru clasificare binara: impuritate (Gini,
entropie), castig de informatie / reducere de impuritate, crestere recursiva greedy
cu max_depth si min_samples_split, predictie si reguli interpretabile. Forta
arborilor: explicabili -- reguli citibile pentru decizii ca mission_complete.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (impuritate, derivarea castigului + exemplu numeric lucrat).
- `arbori_decizie_core.py` -- nucleu pur numpy + `_selftest()` (gini/entropie, best_split, arbore, max_depth, supra-invatare).
- `arbori_decizie_sklearn.py` -- validare incrucisata cu `DecisionTreeClassifier` (acuratete egala).
- `demo_sil.py` -- arbore pentru mission_complete: acuratete, reguli, importanta feature-urilor (figura).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m12_arbori
$PY arbori_decizie_core.py
$PY arbori_decizie_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
