#!/bin/bash
# v0_smoke.sh -- porneste graficul V0 60 s, face capturile obligatorii si scrie verificarile in <out>/.
# Utilizare: v0_smoke.sh <out_dir> [durata_s=60]. Cod de iesire 0 daca graficul a pornit; 1 altfel.
set -u
OUT="${1:?out_dir}"; DUR="${2:-60}"; mkdir -p "$OUT/c6" "$OUT/c3_jurnal"
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp ROS_DOMAIN_ID=76     # acelasi domain ca launch-ul; capturile fara daemon
SECONDS=0
# grup de procese propriu: la sfarsit se opreste TOT graficul (nu doar ros2 launch), altfel copiii raman orfani (V0 smoke2)
setsid ros2 launch c7_sistem v0_sistem.launch.py jurnal:="$OUT/c3_jurnal" c6_outputs:="$OUT/c6" durata_app:="$DUR" > "$OUT/launch.log" 2>&1 &
LP=$!
sleep 12
ros2 node list --no-daemon > "$OUT/node_list.txt" 2>&1
ros2 topic list --no-daemon > "$OUT/topic_list.txt" 2>&1
for t in /network_confidence /c6/cmd_op /c6/pose /teleop/cmd /teleop/pose /sar/telemetry /mesh/relay /mesh/beacon /c3/app /c3/tx; do
  timeout 12 ros2 topic hz -w 20 "$t" > "$OUT/hz_$(echo $t | tr '/' '_').txt" 2>&1 || true
done
# c6: comanda filtrata = /c6/pose (iesirea plantului dupa filtru); comanda operatorului = /c6/cmd_op
while [ "$SECONDS" -lt "$DUR" ]; do sleep 2; done          # graficul ramane pornit cel putin DUR secunde
kill -INT $LP 2>/dev/null; for i in $(seq 1 25); do kill -0 $LP 2>/dev/null || break; sleep 1; done   # ros2 launch propaga SIGINT ordonat
kill -TERM -- -$LP 2>/dev/null; sleep 2; kill -KILL -- -$LP 2>/dev/null; wait $LP 2>/dev/null
echo "procese ramase din grafic: $(pgrep -f "ros2_ws/(src|install)/(sar_swarm|mesh_plugin|teleop_rover|c3_gateway|c7_sistem|c6_safety)/" | wc -l)" >> "$OUT/launch.log"
# ultimele 20 de linii per proces (prefixul [nume-N] din launch.log)
for p in $(/usr/bin/grep -oE "^\[[a-zA-Z0-9_.-]+-[0-9]+\]" "$OUT/launch.log" | sort -u); do
  n=$(echo "$p" | tr -d '[]'); /usr/bin/grep -F "$p" "$OUT/launch.log" | tail -20 > "$OUT/log_$n.txt"
done
ERR=$(/usr/bin/grep -c "\[ERROR\]\|Traceback\|error while\|process has died" "$OUT/launch.log")
echo "erori_in_log=$ERR" > "$OUT/rezumat.txt"
echo "noduri=$(/usr/bin/grep -c . "$OUT/node_list.txt")" >> "$OUT/rezumat.txt"
echo "topicuri=$(/usr/bin/grep -c . "$OUT/topic_list.txt")" >> "$OUT/rezumat.txt"
for f in "$OUT"/hz_*.txt; do echo "$(basename $f .txt)=$(/usr/bin/grep -m1 'average rate' $f | awk '{print $3}')" >> "$OUT/rezumat.txt"; done
[ -f "$OUT/c6/v0_A2_metrics.json" ] && echo "c6_metrics=$(tr -d '\n ' < "$OUT/c6/v0_A2_metrics.json")" >> "$OUT/rezumat.txt"
echo "gateway_sonda=$(/usr/bin/grep -c 'sonda' "$OUT/launch.log")" >> "$OUT/rezumat.txt"
cat "$OUT/rezumat.txt"
[ "$(/usr/bin/grep -c . "$OUT/node_list.txt")" -gt 5 ] && exit 0 || exit 1
