# c4_platforma -- C4: sonda de incredere la bordul roverului (P0-HIL, 19.09.2026)

- `c4_platforma/confidence_core.py`: nucleu FARA ROS. `Fereastra(T_dead, W)`: alpha = decise-OK / decise pe ultimele W (probele
  neintoarse mai tinere decat T_dead sunt in asteptare, nu pierdute); `age_sonda` = RTT_ultim/2 + (t_now - t_rx_ultim) pe ceasul
  monoton local (NU cere ceasuri comune); `age_stamp` = t_wall - stamp (DOAR jurnal). `--selftest` 5 cazuri.
- `c4_platforma/confidence_node.py` (rover): /c4/ping -> /c4/pong; publica Float32 /network_confidence (alpha) si /network_age (age_sonda).
  Parametri: T_dead 0.25, W 20, hz 10, jurnal (CSV: t, seq_ultim, alpha, age_sonda, age_stamp, rtt_ultim).
- `c4_platforma/ecou_node.py` (operator): intoarce ping-ul; `deviatie_s` se aduna la stamp (deviatie de ceas injectata software).
- Specificatia: DOC/CAIETE/P0_SPEC_RECONSTRUIT.md (originalul PHDV3_P0_NETWORK_CONFIDENCE.md nu e pe disc; RECONSTRUIT).
- Launch-urile pe roluri: c7_sistem (v0_operator / v0_rover). Build: `colcon build --packages-select c4_platforma --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3`.
