# c6_safety -- nucleul pur al gardei de siguranta C6

Ce e pe disc, tot fara ROS si fara retea (`python3 <fisier> --selftest`):

- `rover_dyn.py`   -- modelul F din nota M0 (clamp pe acceleratie, Euler explicit);
                      tau_act intra ca MARJA prin `d_fr(v)`, optional ca dinamica de test
- `cbf_core.py`    -- filtrul CBF-QP pe OSQP, v0.2: cost ponderat W, marginea de
                      liniarizare eps_lin (Lema 2); `--selftest` 8 cazuri, cod 0
- `c6_params.py`   -- toti parametrii intr-un loc; fiecare camp trimite la sectiunea din caiet
- `models.py`      -- `Unicycle` (peste rover_core) si `SkidSteerAdapter` (imprumuta
                      `SkidSteer4W` din teleop_rover, READ-ONLY, cu izolare de import:
                      ambele pachete au un `rover_core.py`, iar fara izolare se ciocnesc)
- `operator_core.py` -- operator P spre tinta; `react=True` = un viraj de 45 deg la
                      T_react, apoi P (v0.2)
- `channel_core.py`  -- `IdealChannel` si `DelayLossChannel`; canal de TEST pentru
                      core-uri, bancul experimentului e netem pe lo (S3)
- `episode.py`     -- `run_episode()`; metricile V, d_min, J_int, T_G, B, n_inf exact
                      ca in caiet v0.1 sec. 8; `--selftest` ruleaza 6 cazuri
- `io_core.py`     -- trace CSV + metrics JSON

- `brate.py`       -- A0/A1/A2/A3 pe pericol MOBIL (traversare | urmarire), ERATA 3:
                      marja v_o*(A_ef + v/a_max); certificat per rulare; `--selftest` (a)-(i)
- `certif_core.py` -- certificatul M1: (i) h_true, (ii) DT-CBF pe fezabili, (iii) KKT,
                      (iv) re-simulare F; 2 controale negative in selftest

## Nodurile ROS 2 (S3) -- subtiri, fara logica

- `operator_node.py` -- partea GCS: publica `/c6/cmd_op` (20 Hz) si `/c6/hazard` (f_haz),
                        JSON pe `std_msgs/String` cu `t_tx` = ceasul nodului la emitere
                        (rolul lui header.stamp); asculta `/c6/pose` (INTARZIAT prin lo)
- `rover_node.py`    -- plant F + filtru (`brate.filtru_pentru`) + certificat; A_cmd si
                        A_haz = acum - t_tx (acelasi ceas pe loopback, DECLARAT); la final
                        scrie `<outputs>/<eticheta>_{trace.csv,metrics.json,certificate.json}`
                        si iese; timpul de simulare e nominal (k*dt), perioada reala a
                        tick-ului intra in metrics (`tick_ms_mediu/max`)
- `launch/c6_smoke.launch.py` -- ambele noduri sub `~/ros2_ws/.venv_c6/bin/python` (osqp e
                        acolo, nu in /usr/bin/python3), RMW global `rmw_cyclonedds_cpp`,
                        se opreste cand iese rover_node. Argumente: brat, scenariu (S3: doar
                        traversare), v_o_max, seed, react, f_haz, qos (reliable|best_effort),
                        outputs, eticheta, rmw, python

Build: `cd ~/ros2_ws && colcon build --packages-select c6_safety --cmake-args
-DPython3_EXECUTABLE=/usr/bin/python3`. Netem pe lo: `~/PHD/BORD/tools/netem_lo.py`;
smoke complet: `~/PHD/BORD/tools/s3_smoke.py` (prin `ruleaza.py`, urmele in rulare).

Ce NU e aici: campania (S4); scenariul "urmarire" in noduri (cere pozitia roverului la
GCS, care ajunge intarziata -- decizie in S4).
