# curs_ml -- curs academic de Machine Learning ca pachet ROS 2

Al doilea pilon al ecosistemului educational al tezei, dupa `curs_ros2`. Preda
Machine Learning de la zero, la nivel master/doctorat, cu derivari complete si
exemple lucrate numeric, folosind datele si problemele mele de cercetare
(benchmark rmw_zenoh vs rmw_cyclonedds_cpp pe retele degradate). Culmineaza
intr-un predictor de stare a linkului ca nod ROS 2 -- puntea catre contributia
C3 (`link_adaptive`).

Doua proprietati definesc cursul:
- Auto-suficient pedagogic: fiecare `teorie.md` preda complet conceptul
  (intuitie, formalizare, derivare, exemplu numeric, capcane). Referintele sunt
  pentru aprofundare, nu inlocuitori.
- Relevant pentru teza: fiecare modul foloseste date sintetice semanate din
  numerele campaniilor reale (vezi `curs_ml/date_sar.py`).

ONESTITATE: datele din curs sunt SINTETICE (calibrate pe C1/M), nu masuratori
reale. Vezi nota din fiecare `teorie.md` si din `date_sar.py`.

## Cum rulezi

Dependintele ML stau intr-un venv DEDICAT, ca sa NU strice Python-ul de ROS:

```bash
python3 -m venv ~/ros2_ws/.venv_ml
source ~/ros2_ws/.venv_ml/bin/activate
pip install -r ~/ros2_ws/src/curs_ml/requirements.txt
```

Sanity offline pe un nucleu (fara ROS):

```bash
cd ~/ros2_ws/src/curs_ml/curs_ml
python3 utils.py            # infrastructura partajata (selftest)
python3 date_sar.py         # generatorul de date (selftest)
python3 m05_regresie_liniara/regresie_liniara_core.py   # exemplu de modul
```

Verificare integrala a cursului (ASCII + toate selftest-urile + numar fisiere):

```bash
cd ~/ros2_ws/src/curs_ml
./verifica_ml.sh
```

Build ca pachet ROS 2 (doar pentru nodurile demo, ex. capstone M22). Nodurile ROS
si `colcon` se ruleaza pe masina cu ROS 2 Jazzy:

```bash
cd ~/ros2_ws && colcon build --packages-select curs_ml --symlink-install
source install/setup.bash && ros2 pkg executables curs_ml
```

## Harta cursului (M00-M22)

Legenda: [core] esential, [rec] recomandat (direct pentru teza), [opt] optional.

Partea 0 -- Fundamente: M00 Algebra liniara [core], M01 Probabilitate si
statistica [core], M02 Optimizare [core], M03 Cadrul invatarii supervizate [core].
Partea I -- Date: M04 Date si feature engineering [core].
Partea II -- Regresie: M05 Regresie liniara [core], M06 Regularizare [core],
M07 Evaluare si validare [core].
Partea III -- Clasificare: M08 Regresie logistica [core], M09 Metrici,
dezechilibru, calibrare [core], M10 Naive Bayes [opt], M11 k-NN si SVM [core].
Partea IV -- Arbori si ensembluri: M12 Arbori de decizie [core], M13 Ensembluri
[core], M14 Interpretabilitate [rec].
Partea V -- Nesupervizat: M15 Clustering [core], M16 Reducerea dimensionalitatii [core].
Partea VI -- Incertitudine: M17 Cuantificarea incertitudinii [rec].
Partea VII -- Selectie de model: M18 Selectie si reglare [core].
Partea VIII -- Serii si retele: M19 Serii temporale [core], M20 Retele neuronale [opt].
Partea IX -- RL si capstone: M21 MDP si Q-learning [rec], M22 Capstone:
predictor de link ca nod ROS 2 [rec].

## Harta de dependente (DAG textual)

```
M00 -> M01 -> M02 -> M03 -> M04 -> {restul aplicat}
M04 -> M05 -> M06 -> M07
M04 -> M08 -> M09
M04 -> M12 -> M13 -> M14
M04 -> M15 ; M04 -> M16
M01 + M07 -> M17
M07 -> M18
M05 / M07 -> M19 -> M20  (M20 cere si M02/M08)
M01 -> M21 (standalone)
M05 + M08 + M13 + ROS -> M22 (capstone)
```

## Trasee de invatare

- Rapid (esential): M00-M09, M12-M13, M15-M16.
- Complet: toate [core] + [rec].
- Cercetare (focus teza): M00-M09 + M14 + M17 + M19 + M21-M22. Alimenteaza
  direct contributia C3 (incertitudine la N mic + serii + RL + nod ROS).

## Structura unui modul

Fiecare folder `mXX_*` are: `teorie.md` (predare completa), `<topic>_core.py`
(implementare pura + `_selftest`), `<topic>_sklearn.py` (validare incrucisata),
`demo_sil.py` (demonstratie pe datele mele), `exercitii.md` + `exercitii.py`
(cu stub-uri TODO), `solutii.py`, `README.md`. Vezi CHARTA.md pentru sablonul
pedagogic complet.

## Documente transversale

- `CHARTA.md` -- charter pedagogic: obiective, prerechizite, evaluare, sablon de modul.
- `GLOSAR.md` -- glosar de termeni EN->RO.
- `BIBLIOGRAFIE.md` -- referinte per parte, preferand surse legale gratuite.
- `PRINCIPII_TRANSVERSALE.md` -- scurgere de date, reproductibilitate, cand NU folosi ML, limite.
- `PROIECTE_SINTEZA.md` -- patru proiecte integratoare pe datele mele.

## Stare de constructie

In curs de constructie incrementala (un modul o data, cu selftest verde inainte
de commit). Vezi commit-urile `curs_ml: MXX <titlu>`.
