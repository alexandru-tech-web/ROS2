# c6_safety -- nucleul pur al gardei de siguranta C6

Ce e pe disc, tot fara ROS si fara retea (`python3 <fisier> --selftest`):

- `rover_core.py`  -- uniciclu cu a_max si intarziere de actuator; `step()` pur, `d_fr(v)`
- `c6_params.py`   -- toti parametrii intr-un loc; fiecare camp trimite la sectiunea din caiet
- `models.py`      -- `Unicycle` (peste rover_core) si `SkidSteerAdapter` (imprumuta
                      `SkidSteer4W` din teleop_rover, READ-ONLY, cu izolare de import:
                      ambele pachete au un `rover_core.py`, iar fara izolare se ciocnesc)
- `operator_core.py` -- operatorul P spre tinta, care NU vede obstacolul (intentionat)
- `channel_core.py`  -- `IdealChannel` si `DelayLossChannel`; canal de TEST pentru
                      core-uri, bancul experimentului e netem pe lo (S3)
- `episode.py`     -- `run_episode()`; metricile V, d_min, J_int, T_G, B, n_inf exact
                      ca in caiet v0.1 sec. 8; `--selftest` ruleaza 6 cazuri
- `io_core.py`     -- trace CSV + metrics JSON

Ce NU e aici: filtrul QP (S2), noduri ROS (S3), netem (S3), campania (S4).
`entry_points` e gol intentionat; lansarea prin `ros2 run` nu e configurata.
