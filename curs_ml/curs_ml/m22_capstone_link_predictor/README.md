# M22 -- CAPSTONE: Predictor de stare a linkului ca nod ROS 2

Modulul de SINTEZA care inchide cursul inapoi in teza (contributia C3 /
`link_adaptive`): antreneaza OFFLINE un predictor binar de 'usable' din feature-uri
de link (regresie logistica din M08, numpy pur), il salveaza intr-un `.npz` si il
IMPACHETEAZA intr-un nod ROS 2 subtire care publica predictia pe un topic consumabil
de stratul adaptiv. Politica adaptiva (comuta dupa predictie) bate politica statica.

Datele de antrenare/demonstratie sunt SINTETICE (semanate din C1/M via `date_sar.py`)
-- de inlocuit cu date reale de campanie inainte de orice folosire in misiune.

## Fisiere
- `teorie.md` -- predare completa (antrenare offline, serializare, nod subtire,
  exemplu numeric, legatura cu C3 si cu MDP-ul din M21).
- `link_predictor_core.py` -- nucleu pur numpy + `_selftest()` (train/save/load/predict).
- `link_predictor_node.py` -- nodul ROS 2 subtire (rclpy); se verifica DOAR cu
  `py_compile` in venv-ul ML (nu are rclpy); se ruleaza pe masina cu ROS.
- `demo_sil.py` -- politica adaptiva vs statica pe o cronologie de link (figura).
- `exercitii.md` + `exercitii.py` -- exercitii gradate (stub-uri TODO).
- `solutii.py` -- solutiile complete.

## Cum rulezi nucleul si demo-ul (venv ML, fara ROS)
```bash
PY=~/ros2_ws/.venv_ml/bin/python
cd ~/ros2_ws/src/curs_ml/curs_ml/m22_capstone_link_predictor
$PY link_predictor_core.py            # selftest, exit 0
$PY demo_sil.py                       # adaptiv vs static + figura, exit 0
$PY exercitii.py                      # pica pana rezolvi
$PY solutii.py                        # trece, exit 0
$PY -m py_compile link_predictor_node.py   # doar sintaxa (rclpy lipseste in venv)
```

## Build ROS si rulare

Nodul `link_predictor_node` are nevoie de un mediu cu ROS 2 (rclpy). NU se ruleaza in
venv-ul de ML. Pe masina cu ROS 2 Jazzy:

1. Adauga entry_point-ul in `setup.py` (pachetul `curs_ml`), in `console_scripts`:
   ```python
   'link_predictor_node = curs_ml.m22_capstone_link_predictor.link_predictor_node:main'
   ```
2. Build si source (din `~/ros2_ws`):
   ```bash
   cd ~/ros2_ws
   colcon build --packages-select curs_ml --symlink-install
   source install/setup.bash
   ```
3. Ruleaza nodul (antreneaza pe loc la prima pornire daca nu exista `.npz`):
   ```bash
   ros2 run curs_ml link_predictor_node
   # optional, cu parametri:
   ros2 run curs_ml link_predictor_node --ros-args \
       -p features_topic:=/link/features -p model_path:=/tmp/link_predictor.npz
   ```

Topicuri: asculta `<features_topic>` (`std_msgs/String` JSON cu `{p95_ms, loss_frac,
jitter_ms, base_lat_ms, mw_zenoh, distance_m}`); publica `/link_predictor/state`
(`std_msgs/String` JSON `{usable, prob, label}`), consumabil de `link_adaptive`.

Nota (CLAUDE.md sec.6): daca `ros2 run` zice 'failure 1' desi nodul a mers, verifica
ca `main()` intoarce `None` si REBUILD; daca pachetul nu e gasit, ai uitat
`source install/setup.bash`.
