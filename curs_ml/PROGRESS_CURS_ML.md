# Progres constructie curs_ml -- TERMINAT

Branch: `curs-ml` (din main). Venv ML: `~/ros2_ws/.venv_ml` (numpy/scipy/sklearn/
pandas/matplotlib). Verificare integrala: `cd curs_ml && ./verifica_ml.sh` -> TOTUL VERDE.
Datele sunt SINTETICE, semanate din C1/M (vezi `curs_ml/date_sar.py`).
NEpushuit, NEmerge-uit (Alexandru revizuieste).

## TOATE MODULELE GATA (M00-M22, fiecare cu selftest verde in venv, ASCII curat, comise per modul)
- [x] M00 Algebra liniara aplicata        - [x] M12 Arbori de decizie
- [x] M01 Probabilitate si statistica     - [x] M13 Ensembluri
- [x] M02 Optimizare pentru ML            - [x] M14 Interpretabilitate
- [x] M03 Cadrul invatarii supervizate    - [x] M15 Clustering
- [x] M04 Date si feature engineering     - [x] M16 Reducerea dimensionalitatii (PCA)
- [x] M05 Regresie liniara                - [x] M17 Cuantificarea incertitudinii
- [x] M06 Regularizare (Ridge/Lasso)      - [x] M18 Selectie de model
- [x] M07 Evaluare si validare            - [x] M19 Serii temporale
- [x] M08 Regresie logistica              - [x] M20 Retele neuronale (MLP + backprop)
- [x] M09 Metrici, dezechilibru, calibrare- [x] M21 MDP si Q-learning (puntea C3)
- [x] M10 Naive Bayes                     - [x] M22 Capstone: predictor de link ca nod ROS 2
- [x] M11 k-NN si SVM cu kernel

Fiecare modul = 8 fisiere (teorie.md, *_core.py+selftest, *_sklearn.py, demo_sil.py,
exercitii.md, exercitii.py, solutii.py, README.md). M22 are si __init__.py + nodul ROS.

## RESTUL -- GATA
- [x] PROIECTE_SINTEZA.md: P1-P4 implementate in curs_ml/proiecte/, ruleaza verde in venv.
- [x] setup.py: entry_point `link_predictor_node` (M22) adaugat; M22 e pachet instalabil.
- [x] instaleaza_curs_ml.sh: auto-generat (gen_instalator.py) -- recreeaza arborele (207
      fisiere, fara PNG), testat ca recreeaza identic + selftests verzi pe copie.
- [x] README.md: harta + DAG + trasee + cum rulezi (venv + colcon).
- [x] verifica_ml.sh integral: ASCII curat, toate cele 23 nuclee + utils + date_sar VERZI.

## PENTRU ALEXANDRU
- Verifica si fa merge `curs-ml` in main (NU am pushuit/merge-uit).
- Build ROS (doar nodul capstone M22) -- vezi instructiunile colcon din raportul final /
  README.md (sectiunea "Build ROS"). Restul cursului e pure-Python in venv.
- Date SINTETICE peste tot (marcat); cifrele se confirma cu campania reala/HIL.
