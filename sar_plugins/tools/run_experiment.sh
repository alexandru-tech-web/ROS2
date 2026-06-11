#!/usr/bin/env bash
# run_experiment.sh — porneste o rulare reproductibila: RMW + manifest + bag.
#
# Folosire:
#   ./run_experiment.sh <scenariu> <rmw> [durata_s]
#   ./run_experiment.sh loss_30 rmw_zenoh_cpp 120
#   ./run_experiment.sh baseline rmw_cyclonedds_cpp
#
# Ce face:
#   1. exporta RMW_IMPLEMENTATION (zenoh sau cyclonedds);
#   2. daca e zenoh, porneste routerul rmw_zenohd in fundal (si il opreste
#      la final, inclusiv la Ctrl+C);
#   3. scrie manifestul JSON al rularii (data, host, rmw, scenariu, git);
#   4. inregistreaza topicurile relevante cu ros2 bag in
#      ~/sar_data/bags/<scenariu>_<rmw>_<timestamp>/;
#   5. la final afiseaza locatia bag-ului.
#
# Nodurile experimentului (launch-ul tau / mission_plugins.launch.py) le
# pornesti in ALT terminal, cu acelasi RMW_IMPLEMENTATION exportat — sau
# adaugi comanda lor mai jos, la sectiunea marcata [OPTIONAL].

set -euo pipefail

SCEN="${1:?folosire: $0 <scenariu> <rmw> [durata_s]}"
RMW="${2:?folosire: $0 <scenariu> <rmw> [durata_s]}"
DUR="${3:-0}"   # 0 = pana la Ctrl+C

export RMW_IMPLEMENTATION="$RMW"
STAMP="$(date +%Y%m%d_%H%M%S)"
DIR="$HOME/sar_data/bags/${SCEN}_${RMW}_${STAMP}"
mkdir -p "$DIR"
HERE="$(cd "$(dirname "$0")" && pwd)"

ZPID=""
cleanup() {
  if [ -n "$ZPID" ] && kill -0 "$ZPID" 2>/dev/null; then
    echo "[info] opresc rmw_zenohd (pid $ZPID)"
    kill "$ZPID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

if [ "$RMW" = "rmw_zenoh_cpp" ]; then
  echo "[info] pornesc routerul rmw_zenohd..."
  ros2 run rmw_zenoh_cpp rmw_zenohd >"$DIR/zenohd.log" 2>&1 &
  ZPID=$!
  sleep 2
fi

python3 "$HERE/manifest.py" --out "$DIR/manifest.json" \
  --scenario "$SCEN" --rmw "$RMW"

# topicurile inregistrate: comenzi+telemetrie teleop, etajul de misiune,
# linkstate-ul radio si starea bateriilor. Adauga/scoate dupa nevoie.
TOPICS=(
  /teleop/cmd /teleop/cmd_safe /teleop/pose /teleop/pose_pred
  /teleop/linkstate /teleop/guard /teleop/video_stats
  /swarm/telemetry /swarm/linkstate /swarm/battery
  /mission/coverage /mission/victims /mission/victims_static
)

echo "[info] inregistrez in $DIR"
if [ "$DUR" -gt 0 ] 2>/dev/null; then
  timeout --signal=INT "$DUR" \
    ros2 bag record -o "$DIR/bag" "${TOPICS[@]}" || true
else
  ros2 bag record -o "$DIR/bag" "${TOPICS[@]}"
fi

# [OPTIONAL] porneste aici si nodurile, daca vrei totul dintr-un script:
# ros2 launch <pachetul_tau> mission_plugins.launch.py &

echo "[ok] rulare incheiata: $DIR"
