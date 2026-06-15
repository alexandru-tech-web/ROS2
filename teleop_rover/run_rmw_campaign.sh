#!/usr/bin/env bash
# run_rmw_campaign.sh - campanie de comparatie RMW pe teleop_rover (strat aplicativ).
# Ruleaza misiunea go-to-goal (mod waypoint, repetabil, fara om in bucla) sub
# fiecare RMW x fiecare conditie de retea x REPS repetari, strange jurnalul fiecarei
# rulari si apoi cheama analyze_campaign.py care scoate figurile.
#
# IMPORTANT: containerul de chat nu are ROS; scriptul e pentru masina ta.
# RULEAZA INTAI UN TEST: REPS=1 si lasa o singura conditie (vezi mai jos).
#
# Reglaje prin variabile de mediu:
#   REPS=3 DURATION=70 GOAL_X=8.0 GOAL_Y=3.0 ./run_rmw_campaign.sh

set -u
RMWS=(zenoh cyclone)
# conditii: "eticheta lat_ms jit_ms loss" (prefix numeric => sortare corecta in figuri)
CONDS=(
  "1_baseline 0 0 0.0"
  "2_usor 100 20 0.05"
  "3_mediu 200 40 0.15"
  "4_greu 400 80 0.30"
)
REPS=${REPS:-3}
DURATION=${DURATION:-70}
GOAL_X=${GOAL_X:-8.0}
GOAL_Y=${GOAL_Y:-3.0}

WS="$HOME/ros2_ws"
PKG="$WS/src/teleop_rover"
LOG="$HOME/teleop_data/robot_log.csv"
OUT=${OUT:-"$PKG/results/campaign_$(date +%Y%m%d_%H%M%S)"}

rmw_pkg() { case "$1" in
  zenoh) echo rmw_zenoh_cpp;;
  cyclone) echo rmw_cyclonedds_cpp;;
  *) echo "$1";; esac; }

cleanup() {
  pkill -f rmw_zenohd      >/dev/null 2>&1
  pkill -f 'gz sim'        >/dev/null 2>&1
  pkill -f teleop_         >/dev/null 2>&1
  pkill -f ros_gz_bridge   >/dev/null 2>&1
  pkill -f ros_gz_image    >/dev/null 2>&1
  rm -f /dev/shm/fastrtps_* >/dev/null 2>&1
  sleep 2
}

wait_port_free() {
  for _ in $(seq 1 10); do
    ss -ltnp 2>/dev/null | grep -q 7447 || return 0
    sleep 1
  done
  echo "  ATENTIE: portul 7447 inca ocupat (router ramas?)"
}

mkdir -p "$OUT"
# shellcheck disable=SC1090
source "$WS/install/setup.bash" 2>/dev/null || true
cd "$PKG" || { echo "Nu gasesc $PKG"; exit 1; }

echo "Campanie -> $OUT"
echo "RMW: ${RMWS[*]} | conditii: ${#CONDS[@]} | repetari: $REPS | durata/rulare: ${DURATION}s | tinta: ($GOAL_X,$GOAL_Y)"
echo

for rmw in "${RMWS[@]}"; do
  export RMW_IMPLEMENTATION="$(rmw_pkg "$rmw")"
  for cond in "${CONDS[@]}"; do
    read -r label lat jit loss <<< "$cond"
    for k in $(seq 1 "$REPS"); do
      echo "=== $rmw / $label (lat=$lat jit=$jit loss=$loss) rep $k/$REPS [RMW=$RMW_IMPLEMENTATION] ==="
      cleanup
      wait_port_free
      rm -f "$LOG"
      dst="$OUT/$rmw/$label/rep$k"
      mkdir -p "$dst"
      # ruleaza misiunea cu timp limitat; SIGINT ca un Ctrl-C curat
      timeout -s INT "$DURATION" ros2 launch ./launch/teleop_perception.launch.py \
        rmw:="$rmw" goal_source:=waypoint goal_x:="$GOAL_X" goal_y:="$GOAL_Y" \
        lat:="$lat" jit:="$jit" loss:="$loss" \
        > "$dst/launch.log" 2>&1
      if [ -f "$LOG" ]; then
        cp "$LOG" "$dst/robot_log.csv"
        echo "  salvat: $dst/robot_log.csv ($(wc -l < "$dst/robot_log.csv") linii)"
      else
        echo "  ATENTIE: fara jurnal (vezi $dst/launch.log)"
      fi
      cleanup
    done
  done
done

echo
echo "=== analiza ==="
python3 analyze_campaign.py --camp "$OUT" --goal "$GOAL_X" "$GOAL_Y"
echo
echo "Gata. Figuri + summary.csv in: $OUT"
