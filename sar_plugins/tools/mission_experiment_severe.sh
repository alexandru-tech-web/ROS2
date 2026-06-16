#!/usr/bin/env bash
# mission_experiment_severe.sh - campania de MISIUNE sub degradare SEVERA.
#
# Diferenta fata de mission_experiment.sh: acolo degradarea vine din DISTANTA
# (radio_link_node, profiluri de teren = moderata). Aici degradarea vine din
# SCENARII de fault (fault_injector_node): pierdere mare, partitie, izolare -
# exact unde se asteapta sa apara diferenta Zenoh vs DDS (la reconectare,
# store-and-forward, rezilienta la cadere).
#
# Itereaza: RMW x SCENARII x REPS. fault_injector e SINGURUL pe /sar/linkstate.
#
#   DRY=1 bash mission_experiment_severe.sh     # planul
#   bash mission_experiment_severe.sh           # ruleaza
#
# Variabile: RMWS, SCENARIOS, REPS, DUR, SEED0, OUT
# Rezultate: $OUT/{rmw}/{scenariu}/rep{N}/ cu manifest + CSV-urile.
set -u

RMWS="${RMWS:-cyclonedds zenoh}"
SCENARIOS="${SCENARIOS:-loss_70 partition_2v2}"
REPS="${REPS:-5}"
DUR="${DUR:-300}"
SEED0="${SEED0:-42}"
OUT="${OUT:-$HOME/mission_results_severe}"
DRY="${DRY:-0}"

SRC="$HOME/ros2_ws/src"
SWARM="$SRC/sar_swarm"
PLUG="$SRC/sar_plugins"
SARD="$HOME/sar_data"
SCEN_DIR="$SWARM/scenarios"

impl_of() { case "$1" in
  cyclonedds) echo rmw_cyclonedds_cpp ;;
  zenoh)      echo rmw_zenoh_cpp ;;
  fastdds)    echo rmw_fastrtps_cpp ;;
  *) echo "RMW necunoscut: $1" >&2; exit 1 ;;
esac; }

TOTAL=$(( $(wc -w <<<"$RMWS") * $(wc -w <<<"$SCENARIOS") * REPS ))
EST=$(( TOTAL * (DUR + 25) / 60 ))
echo "== campania SEVERA: $TOTAL rulari x ${DUR}s  (~${EST} min) =="
echo "   RMW: $RMWS | scenarii: $SCENARIOS | reps: $REPS | seed0: $SEED0"
echo "   iesire: $OUT"

if [ "$DRY" = 1 ]; then
  i=0
  for rmw in $RMWS; do for scen in $SCENARIOS; do for rep in $(seq 1 "$REPS"); do
    i=$((i+1))
    echo "[dry] [$i/$TOTAL] $rmw / $scen / rep$rep -> $OUT/$rmw/$scen/rep$rep"
  done; done; done
  echo "[dry] niciun proces pornit."
  exit 0
fi

[ -d "$SWARM" ] || { echo "[eroare] lipseste $SWARM"; exit 1; }
[ -d "$PLUG" ]  || { echo "[eroare] lipseste $PLUG"; exit 1; }
[ -d "$SCEN_DIR" ] || { echo "[eroare] lipseste $SCEN_DIR"; exit 1; }

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

  [ -n "$ZPID" ] && { kill "$ZPID" 2>/dev/null || true; ZPID=""; sleep 1; }
  if [ "$rmw" = zenoh ]; then
    echo "[info] pornesc routerul rmw_zenohd"
    ros2 run rmw_zenoh_cpp rmw_zenohd >/tmp/zenohd_severe.log 2>&1 &
    ZPID=$!
    sleep 2
  fi

  for scen in $SCENARIOS; do
    SCEN_FILE="$SCEN_DIR/${scen}.yaml"
    if [ ! -f "$SCEN_FILE" ]; then
      echo "[eroare] scenariu lipsa: $SCEN_FILE"; continue
    fi
    for rep in $(seq 1 "$REPS"); do
      i=$((i+1)); SEED=$((SEED0+rep))
      DIR="$OUT/$rmw/$scen/rep$rep"; mkdir -p "$DIR"
      echo
      echo "=== [$i/$TOTAL] $rmw / $scen / rep$rep (seed $SEED) ==="

      mkdir -p "$SARD"
      rm -f "$SARD"/{mission_metrics,op_commands,rtt_log,coverage,victims,battery}.csv

      python3 "$PLUG/tools/manifest.py" --out "$DIR/manifest.json" \
        --scenario "${scen}_seed${SEED}" --rmw "$IMPL" || true

      # --- roiul ---
      porneste "$DIR/d1.log" python3 "$SWARM/drone_node.py" --ros-args -p id:=d1 -p x0:=3.5 -p y0:=3.5 -p use_gazebo:=false
      porneste "$DIR/d2.log" python3 "$SWARM/drone_node.py" --ros-args -p id:=d2 -p x0:=3.5 -p y0:=6.5 -p use_gazebo:=false
      porneste "$DIR/d3.log" python3 "$SWARM/drone_node.py" --ros-args -p id:=d3 -p x0:=6.5 -p y0:=3.5 -p use_gazebo:=false
      porneste "$DIR/d4.log" python3 "$SWARM/drone_node.py" --ros-args -p id:=d4 -p x0:=6.5 -p y0:=6.5 -p use_gazebo:=false
      porneste "$DIR/gcs.log" python3 "$SWARM/gcs_node_ros.py" --ros-args -p autostart:=true
      porneste "$DIR/probe.log" python3 "$SWARM/latency_probe.py"

      # --- degradarea SEVERA: fault_injector = SINGURUL pe /sar/linkstate ---
      porneste "$DIR/fault.log" python3 "$SWARM/fault_injector_node.py" --ros-args \
        -p scenario:="$SCEN_FILE"

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
echo "[ok] campania severa incheiata: $OUT"
echo "     urmeaza:"
echo "       python3 $PLUG/tools/analyze_missions.py $OUT"
echo "       python3 $SWARM/analyze_rmw.py $OUT"
