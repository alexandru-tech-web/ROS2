# M16 -- Reducerea dimensionalitatii (PCA)

Comprima multe feature-uri corelate intr-un spatiu mic pastrand varianta:
derivarea PCA prin maximizarea variantei (Lagrange -> vectori proprii ai
covariantei), legatura cu SVD, varianta explicata, si t-SNE/UMAP conceptual.
Nucleul implementeaza PCA prin SVD pe date centrate (fit / transform /
inverse_transform).

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (derivare PCA + SVD + exemplu numeric pe 4 puncte 2D).
- `pca_core.py` -- nucleu pur numpy + `_selftest()` (ortonormalitate, varianta explicata, reconstructie, directie dominanta).
- `pca_sklearn.py` -- validare incrucisata (sklearn.decomposition.PCA, pana la semn).
- `demo_sil.py` -- PCA 2D pe feature-uri de latenta, separarea conditiilor (figura).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m16_reducere_dimensionalitate
$PY pca_core.py
$PY pca_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
