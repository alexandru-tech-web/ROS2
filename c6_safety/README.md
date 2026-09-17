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

Ce NU e aici: noduri ROS (S3), netem (S3), campania (S4), pericol mobil (S2b).
`entry_points` e gol intentionat; lansarea prin `ros2 run` nu e configurata.
