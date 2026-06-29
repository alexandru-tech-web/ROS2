# M11 -- k-NN si SVM cu kernel

Doua clasificatoare clasice de la zero: k-NN (vecini + vot majoritar pe distante
euclidiene) si SVM liniar antrenat cu Pegasos (subgradient stocastic pe pierderea
hinge), plus kernelul RBF pentru granite neliniare. Nucleul implementeaza distantele
vectorizate, clasificatorul k-NN, Pegasos si matricea kernel RBF.

Datele de demonstratie/exercitii sunt SINTETICE (cluster-e si inele semanate aici,
sau ferestre de link din `date_sar.py`).

## Fisiere
- `teorie.md` -- predare completa (k-NN + derivarea hinge/Pegasos + truc kernel/RBF, exemplu numeric).
- `knn_svm_core.py` -- nucleu pur numpy + `_selftest()` (k-NN k=1 perfect, cluster-e separate, Pegasos separabil, RBF simetric/=1 pe diagonala).
- `knn_svm_sklearn.py` -- validare incrucisata (KNeighborsClassifier + SVC linear).
- `demo_sil.py` -- k-NN vs SVM liniar pe o granita neliniara (inele), figura.
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m11_knn_svm
$PY knn_svm_core.py
$PY knn_svm_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
