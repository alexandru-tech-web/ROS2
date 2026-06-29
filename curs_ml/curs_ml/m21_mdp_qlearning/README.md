# M21 -- Procese de decizie Markov (MDP) si Q-learning

Decizie secventiala sub incertitudine: MDP (stari, actiuni, tranzitii P,
recompense R, discount gamma), ecuatia Bellman de optimalitate, iteratia pe valoare
(referinta optima cu model) si Q-learning tabular epsilon-greedy (model-free).
Firul rosu: comutarea adaptiva QoS/middleware (DDS vs Zenoh) ca MDP -- PUNTEA catre
contributia C3 a tezei.

Mediul de comutare (stari = conditii de link GOOD/DEGRADED/BAD, actiuni = DDS/Zenoh,
recompensa = valoare de misiune) e un MODEL SINTETIC, calibrat dupa intuitia
campaniei C1, NU masurat. De inlocuit cu un MDP estimat din date HIL inainte de
orice articol.

## Fisiere
- `teorie.md` -- predare completa (MDP, Bellman, derivarea Q-learning + exemplu numeric).
- `qlearning_core.py` -- nucleu pur numpy + `_selftest()` (convergenta la politica
  optima, reziduu Bellman, recompensa crescatoare, vizitarea actiunilor).
- `qlearning_sklearn.py` -- validare incrucisata fata de programare dinamica
  (sklearn nu are RL tabular; documentat in fisier).
- `demo_sil.py` -- Q-learning pe mediul de comutare; invatat vs static (figura).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi (venv ML)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m21_mdp_qlearning
$PY qlearning_core.py
$PY qlearning_sklearn.py
$PY demo_sil.py
$PY exercitii.py     # pica pana rezolvi; $PY solutii.py trece
```
