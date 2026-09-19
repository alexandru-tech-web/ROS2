#!/bin/bash
# split_smoke.sh -- doua launch-uri separate (rol operator / rol rover), ca doua terminale, DUR secunde.
# Utilizare: split_smoke.sh <out> [DUR=60] [domain_op=76] [domain_rover=76] [deviatie_s=0.0] [cu_gateway=true]
# Scrie: launch_operator.log, launch_rover.log, c4_jurnal.csv, node_list_{op,rover}.txt, rezumat.txt. Oprire pe grup, ordonata.
set -u
OUT="${1:?out}"; DUR="${2:-60}"; DOP="${3:-76}"; DRV="${4:-76}"; DEV="${5:-0.0}"; CUG="${6:-true}"
mkdir -p "$OUT/c6" "$OUT/c3_jurnal"; export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
SECONDS=0
setsid ros2 launch c7_sistem v0_operator.launch.py rol:=operator pereche:=127.0.0.1 domain:="$DOP" jurnal:="$OUT/c3_jurnal" deviatie_s:="$DEV" cu_gateway:="$CUG" > "$OUT/launch_operator.log" 2>&1 &
LO=$!
sleep 3
setsid ros2 launch c7_sistem v0_rover.launch.py rol:=rover pereche:=127.0.0.1 domain:="$DRV" c6_outputs:="$OUT/c6" jurnal_c4:="$OUT/c4_jurnal.csv" > "$OUT/launch_rover.log" 2>&1 &
LR=$!
sleep 15
ROS_DOMAIN_ID=$DOP ros2 node list --no-daemon > "$OUT/node_list_op.txt" 2>&1
ROS_DOMAIN_ID=$DRV ros2 node list --no-daemon > "$OUT/node_list_rover.txt" 2>&1
ROS_DOMAIN_ID=$DRV timeout 12 ros2 topic hz -w 20 /network_confidence > "$OUT/hz_network_confidence.txt" 2>&1 || true
ROS_DOMAIN_ID=$DRV timeout 8 ros2 topic echo --once /network_age > "$OUT/age_once.txt" 2>&1 || true
while [ "$SECONDS" -lt "$DUR" ]; do sleep 2; done
for P in $LR $LO; do kill -INT $P 2>/dev/null; done
for i in $(seq 1 25); do (kill -0 $LR 2>/dev/null || kill -0 $LO 2>/dev/null) || break; sleep 1; done
for P in $LR $LO; do kill -TERM -- -$P 2>/dev/null; done; sleep 2; for P in $LR $LO; do kill -KILL -- -$P 2>/dev/null; done; wait 2>/dev/null
E=$(cat "$OUT"/launch_*.log | /usr/bin/grep -c "\[ERROR\]\|Traceback\|process has died")
{ echo "erori_in_loguri=$E"; echo "noduri_op=$(/usr/bin/grep -c '^/' "$OUT/node_list_op.txt")"; echo "noduri_rover=$(/usr/bin/grep -c '^/' "$OUT/node_list_rover.txt")"
  echo "hz_network_confidence=$(/usr/bin/grep -m1 'average rate' "$OUT/hz_network_confidence.txt" | awk '{print $3}')"
  echo "pong_primite=$(/usr/bin/grep -o 'pong=[0-9]*' "$OUT/launch_rover.log" | tail -1)"
  [ -f "$OUT/c6/rover_A2_metrics.json" ] && echo "c6_metrics=$(tr -d '\n ' < "$OUT/c6/rover_A2_metrics.json" | cut -c1-200)" || echo "c6_metrics=LIPSA (roverul nu a primit cmd+hazard)"
  /usr/bin/python3 - "$OUT/c4_jurnal.csv" <<'PY'
import csv, sys, statistics
try:
    r=[x for x in csv.DictReader(open(sys.argv[1])) if x["age_sonda"]]
    a=[float(x["alpha"]) for x in r]; b=[float(x["age_sonda"]) for x in r]; s=[float(x["age_stamp"]) for x in r if x["age_stamp"]]
    print("c4_linii=%d alpha_med=%.3f age_sonda_med=%.4f age_sonda_p95=%.4f age_stamp_med=%s age_stamp_p95=%s" % (len(r), statistics.median(a), statistics.median(b), sorted(b)[int(0.95*len(b))-1] if b else -1, ("%.4f" % statistics.median(s)) if s else "-", ("%.4f" % sorted(s)[int(0.95*len(s))-1]) if s else "-"))
except Exception as e: print("c4_linii=0 (%s)" % e)
PY
} > "$OUT/rezumat.txt"; cat "$OUT/rezumat.txt"
[ "$E" = "0" ] && exit 0 || exit 1
