# c7_sistem -- C7: sistemul rover + roi, DOAR launch-uri si remapari (V0, 18.09.2026)

- `launch/v0_sistem.launch.py`: graficul comun pe loopback, fara degradare: rmw_zenohd, c3_gateway (agenti + reflector + gateway,
  procesele replicate din launch-ul lui, fara handler-ele OnProcessExit fara tinta), C4 SUBSTITUT, c6_safety (A2), sar_swarm fara Gazebo
  (4 drone + GCS + injector 'none' + sonda), mesh_plugin (ingest), teleop_rover fara Gazebo. RMW cyclonedds global, ROS_DOMAIN_ID=76.
- `launch/v0_operator.launch.py` / `launch/v0_rover.launch.py` (P0-HIL): graficul taiat pe roluri (operator: ecou C4 + c6 operator_node
  [+ gateway optional]; rover: c4 confidence_node + c6 rover_node A2); `tools/split_smoke.sh <out> [DUR] [dom_op] [dom_rover] [deviatie_s] [cu_gateway]`.
- `c7_sistem/substitut_c4_node.py`: SUBSTITUT, NU MASURATOARE -- /network_confidence=1.0 si /network_age=0.0 constante, pana la P0.
- `tools/v0_smoke.sh <out> [60]`: porneste graficul, face capturile (node/topic list fara daemon, hz), opreste ordonat, scrie rezumat.txt.
- Rulare: `DOC/BORD/tools/ruleaza.py --unit V0 --tag smoke --contributie C7 --campanie v0_<data>_VALIDARE --iface lo -- bash src/c7_sistem/tools/v0_smoke.sh {run}/out 60`.
- Nu contine logica; pachetele inghetate nu se modifica. Ce lipseste ca sa fie sistem (nu doar grafic): DOC/CAIETE/V0_SISTEM.md.
- Build: `colcon build --packages-select c7_sistem --cmake-args -DPython3_EXECUTABLE=/usr/bin/python3`.
