# Progres constructie curs_ml

Branch: `curs-ml` (din main). Venv ML: `~/ros2_ws/.venv_ml` (numpy/scipy/sklearn/
pandas/matplotlib instalate). Verificare integrala: `cd curs_ml && ./verifica_ml.sh`.
Datele sunt SINTETICE, semanate din C1/M (vezi `curs_ml/date_sar.py`).

## FACUT (commis, selftest verde in venv, ASCII curat)
- Fundatie: package.xml/setup.py/setup.cfg, requirements.txt, utils.py (15/15),
  date_sar.py (17/17), doc-uri (README/CHARTA/GLOSAR/BIBLIOGRAFIE/PRINCIPII/
  PROIECTE), verifica_ml.sh, tests/run_all_selftests.py, .gitignore (PNG + pycache).
- [x] M00 Algebra liniara aplicata
- [x] M01 Probabilitate si statistica
- [x] M02 Optimizare pentru ML
- [x] M03 Cadrul invatarii supervizate
- [x] M04 Date si feature engineering
- [x] M05 Regresie liniara
- [x] M06 Regularizare
- [x] M07 Evaluare si validare
Fiecare modul = 8 fisiere (teorie.md, *_core.py+selftest, *_sklearn.py, demo_sil.py,
exercitii.md, exercitii.py, solutii.py, README.md). PNG-urile sunt gitignorate.

## DE FACUT (M08-M22, acelasi sablon, selftest verde inainte de commit)
- [ ] M08 Regresie logistica       (sigmoid, entropie incrucisata, gradient derivat)
- [ ] M09 Metrici, dezechilibru, calibrare (PR/ROC, praguri, Platt/isotonic) -- foloseste make_link_usability_dataset
- [ ] M10 Naive Bayes [opt]
- [ ] M11 k-NN si SVM cu kernel
- [ ] M12 Arbori de decizie         -- make_mission_outcome_dataset
- [ ] M13 Ensembluri                (bagging, RF, boosting)
- [ ] M14 Interpretabilitate [rec]  (permutare, PDP, SHAP)
- [ ] M15 Clustering                (k-means/Lloyd, DBSCAN)
- [ ] M16 Reducerea dimensionalitatii (PCA via SVD)
- [ ] M17 Cuantificarea incertitudinii [rec] (bayesian, GP, bootstrap, conformal)
- [ ] M18 Selectie de model         (grid/nested CV, AIC/BIC)
- [ ] M19 Serii temporale           -- make_latency_series
- [ ] M20 Retele neuronale [opt]    (MLP from scratch + backprop)
- [ ] M21 MDP si Q-learning [rec]   (Bellman, Q tabular) -- puntea C3
- [ ] M22 Capstone: predictor de link ca nod ROS 2 [rec] -- entry_point in setup.py,
        JSON pe std_msgs/String, sys.path.insert; pasii colcon/ros2 run ii ruleaza Alexandru.
- [ ] PROIECTE_SINTEZA.md: completeaza P1-P4 dupa ce exista modulele.
- [ ] README.md: revizuieste harta finala; genereaza instaleaza_curs_ml.sh.

## NOTE
- Nucleele *_core.py: numpy PUR (scikit-learn INTERZIS); *_sklearn.py = validare incrucisata.
- Import: sys.path.insert(0, dirname(dirname(__file__))) -> from utils / from date_sar.
- M22 e singurul cu nod ROS; restul ruleaza pure-Python in venv.
- Un workflow paralel mare a lovit limita de sesiune o data -> mai bine loturi mici sau direct.
