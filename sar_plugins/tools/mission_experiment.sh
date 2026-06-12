#!/usr/bin/env bash
# mission_experiment.sh — campania de MISIUNE: 2 RMW x 2 profiluri x REPS.
#
# Compune roiul MANUAL (fara fault_injector!) ca sa respecte regula unui
# singur publisher pe /sar/linkstate: aici linkstate-ul apartine EXCLUSIV
# nodului radio_link_node (degradare dependenta de distanta, profil de teren).
#
#   DRY=1 tools/mission_experiment.sh     # planul, fara executie
#   tools/mission_experiment.sh           # ~45 min implicit
#
# Variabile: RMWS, PROFILES, REPS, DUR, SEED0, BATT_WH, OUT
# Rezultate: $OUT/{rmw}/{profil}/rep{N}/ cu manifest + CSV-urile recoltate.
set -u

RMWS="${RMWS:-cyclonedds zenoh}"
PROFILES="${PROFILES:-open_field urban_rubble}"
REPS="${REPS:-2}"
DUR="${DUR:-300}"
SEED0="${SEED0:-42}"
BATT_WH="${BATT_WH:-8}"
OUT="${OUT:-$HOME/mission_results}"
DRY="${DRY:-0}"

SRC="$HOME/ros2_ws/src"
SWARM="$SRC/sar_swarm"
PLUG="$SRC/sar_plugins"
SARD="$HOME/sar_data"

impl_of() { case "$1" in
  cyclonedds) echo rmw_cyclonedds_cpp ;;
  zenoh)      echo rmw_zenoh_cpp ;;
  fastdds)    echo rmw_fastrtps_cpp ;;
  *) echo "RMW necunoscut: $1" >&2; exit 1 ;;
esac; }

TOTAL=$(( $(wc -w <<<"$RMWS") * $(wc -w <<<"$PROFILES") * REPS ))
EST=$(( TOTAL * (DUR + 25) / 60 ))
echo "== campania de misiune: $TOTAL rulari x ${DUR}s  (~${EST} min) =="
echo "   RMW: $RMWS | profiluri: $PROFILES | reps: $REPS | seed0: $SEED0"
echo "   iesire: $OUT"

if [ "$DRY" = 1 ]; then
  i=0
  for rmw in $RMWS; do for prof in $PROFILES; do for rep in $(seq 1 "$REPS"); do
    i=$((i+1))
    echo "[dry] [$i/$TOTAL] $rmw / $prof / rep$rep (seed $((SEED0+rep))) -> $OUT/$rmw/$prof/rep$rep"
  done; done; done
  echo "[dry] niciun proces pornit."
  exit 0
fi

[ -d "$SWARM" ] || { echo "[eroare] lipseste $SWARM"; exit 1; }
[ -d "$PLUG" ]  || { echo "[eroare] lipseste $PLUG"; exit 1; }

PIDS=()
ZPID=""
opreste_tot() {
  for p in "${PIDS[@]:-}"; do kill -INT "$p" 2>/dev/null || true; done
  sleep 2
  for p in "${PIDS[@]:-}"; do kill -9 "$p" 2>/dev/null || true; done
  PIDS=()
}
cleanup() {
  opreste_tot
  [ -n "$ZPID" ] && kill "$ZPID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

porneste() {  # porneste <jurnal> <cmd...>
  local log="$1"; shift
  "$@" >"$log" 2>&1 &
  PIDS+=($!)
}

i=0
for rmw in $RMWS; do
  IMPL="$(impl_of "$rmw")"
  export RMW_IMPLEMENTATION="$IMPL"
  export ZENOH_ROUTER_CHECK_ATTEMPTS=10

  # routerul Zenoh: o singura instanta per bloc RMW
  [ -n "$ZPID" ] && { kill "$ZPID" 2>/dev/null || true; ZPID=""; sleep 1; }
  if [ "$rmw" = zenoh ]; then
    echo "[info] pornesc routerul rmw_zenohd"
    ros2 run rmw_zenoh_cpp rmw_zenohd >/tmp/zenohd_misiune.log 2>&1 &
    ZPID=$!
    sleep 2
  fi

  for prof in $PROFILES; do
    for rep in $(seq 1 "$REPS"); do
      i=$((i+1)); SEED=$((SEED0+rep))
      DIR="$OUT/$rmw/$prof/rep$rep"; mkdir -p "$DIR"
      echo
      echo "=== [$i/$TOTAL] $rmw / $prof / rep$rep (seed $SEED) ==="

      # jurnalele proaspete: rularea recolteaza DOAR ce produce ea
      mkdir -p "$SARD"
      rm -f "$SARD"/{mission_metrics,op_commands,rtt_log,coverage,victims,battery}.csv

      python3 "$PLUG/tools/manifest.py" --out "$DIR/manifest.json" \
        --scenario "mission_${prof}_seed${SEED}" --rmw "$IMPL" || true

      # --- roiul (FARA fault_injector) ---
      porneste "$DIR/d1.log" python3 "$SWARM/drone_node.py" --ros-args -p id:=d1 -p x0:=3.5 -p y0:=3.5 -p use_gazebo:=false
      porneste "$DIR/d2.log" python3 "$SWARM/drone_node.py" --ros-args -p id:=d2 -p x0:=3.5 -p y0:=6.5 -p use_gazebo:=false
      porneste "$DIR/d3.log" python3 "$SWARM/drone_node.py" --ros-args -p id:=d3 -p x0:=6.5 -p y0:=3.5 -p use_gazebo:=false
      porneste "$DIR/d4.log" python3 "$SWARM/drone_node.py" --ros-args -p id:=d4 -p x0:=6.5 -p y0:=6.5 -p use_gazebo:=false
      porneste "$DIR/gcs.log" python3 "$SWARM/gcs_node_ros.py" --ros-args -p autostart:=true
      porneste "$DIR/probe.log" python3 "$SWARM/latency_probe.py"

      # --- etajul de misiune (radio_link = SINGURUL pe /sar/linkstate) ---
      porneste "$DIR/radio.log" python3 "$PLUG/nodes/radio_link_node.py" --ros-args \
        -p pose_topic:=/sar/telemetry -p profile:="$prof" -p seed:="$SEED" \
        -p linkstate_topic:=/sar/linkstate
      porneste "$DIR/coverage.log" python3 "$PLUG/nodes/coverage_node.py" --ros-args \
        -p pose_topic:=/sar/telemetry -p sensor_r:=6.0 \
        -p xmin:=-5.0 -p xmax:=65.0 -p ymin:=-5.0 -p ymax:=65.0
      porneste "$DIR/victims.log" python3 "$PLUG/nodes/victim_node.py" --ros-args \
        -p pose_topic:=/sar/telemetry -p n:=6 -p seed:="$SEED" -p sensor_r:=6.0 \
        -p xmin:=0.0 -p xmax:=60.0 -p ymin:=0.0 -p ymax:=60.0
      porneste "$DIR/battery.log" python3 "$PLUG/nodes/battery_node.py" --ros-args \
        -p pose_topic:=/sar/telemetry -p state_topic:=/sar/battery \
        -p capacity_wh:="$BATT_WH" \
        -p failsafe_cmd_topic:=/sar/operator \
        -p 'failsafe_template:={"type":"drone","id":"%ID%","action":"rth"}'

      # --- fereastra de masura ---
      for s in $(seq "$DUR" -30 1); do
        printf "\r    mai sunt %3ds   " "$s"; sleep 30 2>/dev/null || sleep "$s"
      done
      printf "\r    fereastra incheiata           \n"

      opreste_tot
      sleep 1

      # --- recolta ---
      for f in mission_metrics op_commands rtt_log coverage victims battery; do
        [ -f "$SARD/$f.csv" ] && cp "$SARD/$f.csv" "$DIR/"
      done
      echo "[ok] -> $DIR ($(ls "$DIR" | wc -l) fisiere)"
    done
  done
done

echo
echo "[ok] campania incheiata: $OUT"
echo "     urmeaza: python3 tools/analyze_missions.py $OUT"
