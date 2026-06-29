# M15 -- Clustering

Invatare nesupervizata: descopera grupuri (regimuri) in date FARA etichete. Nucleul
implementeaza k-means via algoritmul Lloyd (cu k-means++ si reporniri n_init pentru a
evita minimele locale), scorul silhouette de la zero si un DBSCAN simplu bazat pe
densitate.

Datele de demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (obiectiv k-means, derivarea Lloyd, DBSCAN,
  silhouette + exemplu numeric: o iteratie Lloyd cu inertia 10 -> 4).
- `clustering_core.py` -- nucleu pur numpy + `_selftest()` (recuperare gaussiene sub
  permutare, inertie monotona, silhouette, determinism, DBSCAN).
- `clustering_sklearn.py` -- validare incrucisata (KMeans + silhouette_score sklearn).
- `demo_sil.py` -- regimuri de canal + silhouette vs k pe datele de canal (figura).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m15_clustering
$PY clustering_core.py
$PY clustering_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
