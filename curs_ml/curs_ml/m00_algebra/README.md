# M00 -- Algebra liniara aplicata

Fundamentul notational al intregului curs: vectori, matrice, norme, produs scalar,
proiectii, valori/vectori proprii si covarianta. Nucleul implementeaza de la zero
norme, proiectie ortogonala, Gram-Schmidt si iteratia puterii (vector propriu
dominant), validate fata de numpy.linalg.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (intuitie, derivari, exemplu numeric).
- `algebra_liniara_core.py` -- nucleu pur numpy + `_selftest()`.
- `algebra_liniara_sklearn.py` -- validare incrucisata (PCA via SVD).
- `demo_sil.py` -- covarianta feature-urilor de latenta + axa dominanta (figuri).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m00_algebra
$PY algebra_liniara_core.py      # selftest -> exit 0
$PY algebra_liniara_sklearn.py   # validare incrucisata
$PY demo_sil.py                  # demonstratie headless
$PY exercitii.py                 # pica pana rezolvi; $PY solutii.py trece
```
