#!/usr/bin/env bash
# smoke_all.sh — testul de fum al INTREGULUI repo (nivelul 0, FARA ROS).
# Raspunde la intrebarea: "ce am si ce functioneaza?" — per proiect.
# SIGUR de rulat oricand, inclusiv in timpul campaniei C1: nu porneste
# niciun nod ROS, nu atinge reteaua, nu scrie in pachete.
#
#   ./smoke_all.sh            # rapid (~1-2 min): testele automate
#   FULL=1 ./smoke_all.sh     # + rularile SIL mai lungi (sil_run, demo)
#
# Nivelurile urmatoare (cu ROS / cu Gazebo) sunt in GHID_PORNIRE.md.
set -u
SRC="${SRC:-$HOME/ros2_ws/src}"
FULL="${FULL:-0}"
declare -A REZ
TOT_OK=0; TOT_FAIL=0

pas() {  # pas <proiect> <descriere> <comanda...>
  local pr="$1" desc="$2"; shift 2
  printf "  %-44s" "$desc"
  if ( cd "$SRC/$pr" 2>/dev/null && "$@" ) >"/tmp/smoke_${pr//\//_}.log" 2>&1; then
    echo "[ok]"; TOT_OK=$((TOT_OK+1))
  else
    echo "[FAIL]  -> /tmp/smoke_${pr//\//_}.log"
    REZ[$pr]="FAIL"; TOT_FAIL=$((TOT_FAIL+1))
  fi
}
sectiune() { echo; echo "== $1 =="; REZ[$2]="${REZ[$2]:-PASS}"; }

sectiune "sar_plugins — etajul de misiune + teleop avansat" sar_plugins
pas sar_plugins "55 verificari logica pura" python3 test_plugins.py
[ "$FULL" = 1 ] && pas sar_plugins "demo integrat cu figuri" python3 demo_plugins_sim.py

sectiune "sar_swarm — roiul SAR" sar_swarm
pas sar_swarm "nucleul SAR (25+41 verificari)" python3 test_sar_core.py
pas sar_swarm "operatorul om-in-bucla (24)" python3 test_operator_core.py
pas sar_swarm "launcher-ul (11)" python3 test_launcher_core.py
[ "$FULL" = 1 ] && pas sar_swarm "misiune SIL completa (partition_2v2)" \
  python3 sil_run.py scenarios/partition_2v2.yaml

sectiune "c1_benchmark — campania de transport" c1_benchmark
pas c1_benchmark "nucleul C1 (11 verificari)" python3 test_bench_core.py
pas c1_benchmark "analizorul pe date sintetice" python3 analyze_campaign.py --selftest
pas c1_benchmark "planul campaniei (dry)" python3 run_campaign.py --dry --reps 1

sectiune "teleop_rover — roverul teleoperat" teleop_rover
pas teleop_rover "compilarea tuturor nodurilor" \
  bash -c 'python3 -m py_compile *.py launch/*.py'
pas teleop_rover "SIL: misiune sub 200ms/10% pierdere" \
  python3 sil_teleop.py --lat 200 --jit 40 --loss 0.1 --trace /tmp/tr_smoke.csv

sectiune "rehab_exo_description — exoscheletul" rehab_exo_description
pas rehab_exo_description "compilarea scripturilor" \
  bash -c 'python3 -m py_compile scripts/*.py'

sectiune "servo_control — motorul istoric" servo_control
pas servo_control "compilarea fisierelor python" \
  bash -c 'f=$(find . -name "*.py" | head -20); [ -z "$f" ] || python3 -m py_compile $f'

echo; echo "================= BILANT ================="
for pr in sar_plugins sar_swarm c1_benchmark teleop_rover rehab_exo_description servo_control; do
  printf "  %-26s %s\n" "$pr" "${REZ[$pr]:-PASS}"
done
echo "  pasi: $TOT_OK ok, $TOT_FAIL fail"
if [ "$TOT_FAIL" = 0 ]; then
  echo "  VERDICT: tot nivelul 0 e VERDE. Urmatorul nivel (cu ROS):"
  echo "    GHID_PORNIRE.md -> Workflow 2/3, sau README-ul fiecarui pachet."
else
  echo "  VERDICT: vezi log-urile /tmp/smoke_*.log pentru [FAIL]-uri."
fi
