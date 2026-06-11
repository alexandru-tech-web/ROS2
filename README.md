# Repo principal — `~/ros2_ws/src/`
## Harta pachetelor

| Pachet | Rol | Stare |
|---|---|---|
| `c1_benchmark` | Benchmarking rmw_zenoh vs CycloneDDS sub degradare tc netem — articolul A1 (SSRR 2026) | ✅ date colectate |
| `sar_swarm` | Roiul SAR: drone + GCS + fault injector + latency probe + dashboard | ✅ complet |
| `sar_plugins` | Plugin-uri de canal radio, baterie, acoperire, victime, predictor SAR | ✅ complet |
| `joint_emulator` | Bancul cu 6 servomotoare ABB — impedanță, tele-impedanță, encodere, vizualizare | ✅ complet |
| `rehab_exo_description` | Exoscheletul de reabilitare — URDF, launch-uri, failsafe | ✅ complet |
| `servo_control` | Motorul din Gazebo cu control tastatură (demonstrator) | ✅ complet |
| `curs_ros2` / `curs_ros2_interfaces` | Exerciții de curs ROS2 | arhiva |

## Reguli de aur (nu le încălca niciodată)
1. **Nu construi peste o campanie în mers** — `pgrep -af "run_campaign|bench_|rmw_zenohd"` înainte de orice `colcon build`
2. **Rezultatele brute NU intră în git** — merg în `~/c1_archive/`; în repo doar sumarele CSV și figurile
3. **`./smoke_all.sh` înainte de orice push** — rulează din `~/ros2_ws/src/`
4. **Motorul B al bancului NUMAI în mod cuplu** — niciodată poziție-contra-poziție pe ax rigid
5. **Îngheț de cod pe `c1_benchmark` + `sar_swarm`** până la submisia articolului (18 iunie 2026)

## Comenzi de bază

```bash
# build complet
cd ~/ros2_ws && source /opt/ros/jazzy/setup.bash && colcon build --symlink-install && source install/setup.bash

# smoke test (fără ROS, sigur oricând)
cd ~/ros2_ws/src && ./smoke_all.sh

# commit + push
cd ~/ros2_ws/src && git add -A && git commit -m "..." && git pull --rebase && git push
```
